"""Validation-only DSO-X 6004A single-acquisition capture adapter.

No resource is opened and no instrument is contacted on import. The caller owns
an already-open PyVISA message resource and exclusive instrument access. Call
preflight(), archive_backup(), configure(), arm(), start the DUT, then
wait_and_read(); ALWAYS call restore() in finally (or use the context manager).

Official 6000 X-Series Programmer's Guide:
https://www.keysight.com/cf/en/assets/9018-07124/programming-guides/9018-07124.pdf
Pages 266, 286-287, 300, 303, 1414-1415, 1465, 1524-1551.
Firmware 07.31 does NOT support :RSTate? or :ADER? on this actual instrument.
Use :OPERegister:CONDition? (NOT :OPERation:CONDition?), RUN bit 3.

Restoration covers setup and running/stopped state, not the old acquisition
memory or consumed AER/TER events. RUN bit cannot distinguish an originally
armed SINGLE from continuous RUN; this limitation is recorded in the snapshot.
WORD transfer preserves the instrument's codes, not extra ADC resolution.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time
import uuid

import numpy as np


RUN_MASK = 1 << 3
REMOTE_ENABLED_MASK = 1 << 4
STATE_QUERY = ":OPERegister:CONDition?"
GUIDE_URL = "https://www.keysight.com/cf/en/assets/9018-07124/programming-guides/9018-07124.pdf"


class ScopeCaptureError(RuntimeError):
    pass


class CapabilityError(ScopeCaptureError):
    """Read-only preflight failed; no setup/acquisition mutation was attempted."""


class CaptureTimeout(ScopeCaptureError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_definite_block(raw: bytes, *, max_payload: int = 100_000_000) -> bytes:
    """Require a complete IEEE 488.2 definite block, with optional final LF/CRLF.

    Embedded newlines belong to the payload. Never accept truncated read_raw()
    data or an unframed response as if it were a waveform/setup backup.
    """
    if len(raw) < 2 or raw[:1] != b"#" or raw[1:2] not in b"123456789":
        raise ScopeCaptureError("Expected a definite IEEE block (#1 through #9)")
    digits = int(raw[1:2])
    if len(raw) < 2 + digits or not raw[2:2 + digits].isdigit():
        raise ScopeCaptureError("Incomplete/invalid IEEE block length header")
    length = int(raw[2:2 + digits])
    if not 0 < length <= max_payload:
        raise ScopeCaptureError(f"Unexpected IEEE payload size: {length}")
    end = 2 + digits + length
    if len(raw) < end:
        raise ScopeCaptureError(f"Truncated IEEE block: {len(raw)} bytes, need {end}")
    if raw[end:] not in (b"", b"\n", b"\r\n"):
        raise ScopeCaptureError("Unexpected bytes after IEEE block payload")
    return raw[2 + digits:end]


def make_definite_block(payload: bytes) -> bytes:
    length = str(len(payload)).encode("ascii")
    if not payload or len(length) > 9:
        raise ScopeCaptureError("Invalid payload length")
    return b"#" + str(len(length)).encode("ascii") + length + payload


def parse_preamble(text: str) -> dict:
    fields = text.strip().split(",")
    if len(fields) != 10:
        raise ScopeCaptureError(f"Expected 10 preamble fields, got {len(fields)}")
    values = [float(x) for x in fields]
    if not all(math.isfinite(x) for x in values):
        raise ScopeCaptureError("Nonfinite preamble value")
    if any(x != int(x) for x in values[:4]):
        raise ScopeCaptureError("Noninteger format/type/points/count in preamble")
    keys = ("format", "type", "points", "count", "x_increment", "x_origin",
            "x_reference", "y_increment", "y_origin", "y_reference")
    result = dict(zip(keys, [int(x) for x in values[:4]] + values[4:]))
    if result["format"] != 1 or result["type"] != 0:
        raise ScopeCaptureError("Capture requires WORD format and NORMAL acquisition")
    if result["points"] <= 0 or result["x_increment"] <= 0 or result["y_increment"] <= 0:
        raise ScopeCaptureError("Invalid preamble size/increments")
    return result


def decode_word_waveform(raw: bytes, preamble_text: str, queried_points: int) -> dict:
    p = parse_preamble(preamble_text)
    payload = parse_definite_block(raw)
    if len(payload) != 2 * p["points"] or queried_points != p["points"]:
        raise ScopeCaptureError("Payload, preamble, and WAVeform:POINts? counts disagree")
    codes = np.frombuffer(payload, dtype="<u2").copy()
    # Documented unsigned WORD special codes. Keep the codes and explicit mask;
    # do not silently interpret an unacquired/clipped code as a measured voltage.
    holes, low, high = codes == 0x0000, codes == 0x0100, codes == 0xFF00
    invalid = holes | low | high
    volts = (codes.astype(np.float64) - p["y_reference"]) * p["y_increment"] + p["y_origin"]
    volts[invalid] = np.nan
    seconds = (np.arange(p["points"], dtype=np.float64) - p["x_reference"]) * p["x_increment"] + p["x_origin"]
    return {"preamble": p, "preamble_text": preamble_text, "raw_block": raw,
            "raw_sha256": sha256(raw), "payload_sha256": sha256(payload),
            "codes": codes, "raw_codes": codes, "time_s": seconds, "voltage_v": volts,
            "invalid": invalid, "special_codes": {"hole": int(holes.sum()),
            "clipped_low": int(low.sum()), "clipped_high": int(high.sum())}}


class ScopeCapture:
    """Bounded SINGLE + frozen RAW CH1/CH2 readout; no force/auto triggering.

    The caller must not use the front panel/another VISA session during capture.
    Context exit restores setup even on timeout or DUT callback failure.
    Successful restoration is recorded separately from successful acquisition.
    """
    BASE_QUERIES = (
        ":TIMebase:MODE?", ":TIMebase:REFerence?", ":TIMebase:RANGe?", ":TIMebase:POSition?",
        ":TRIGger:MODE?", ":TRIGger:SWEep?", ":TRIGger:EDGE:SOURce?",
        ":TRIGger:EDGE:SLOPe?", ":TRIGger:EDGE:COUPling?", ":TRIGger:EDGE:REJect?",
        ":TRIGger:EDGE:LEVel? CHANnel1", ":TRIGger:EDGE:LEVel? CHANnel2",
        ":ACQuire:TYPE?", ":ACQuire:MODE?", ":WAVeform:SOURce?",
        ":WAVeform:FORMat?", ":WAVeform:BYTeorder?", ":WAVeform:UNSigned?",
        ":WAVeform:POINts:MODE?", ":WAVeform:POINts?",
    ) + tuple(f":CHANnel{ch}:{setting}?" for ch in (1, 2)
              for setting in ("DISPlay", "COUPling", "IMPedance", "PROBe", "RANGe", "OFFSet"))

    def __init__(self, resource, *, expected_serial="MY60101437", io_timeout_s=5.0,
                 raw_archive_directory=None, max_origin_skew_samples=0.0):
        self.resource = resource
        self.expected_serial = expected_serial
        self.io_timeout_s = float(io_timeout_s)
        if not math.isfinite(self.io_timeout_s) or self.io_timeout_s <= 0:
            raise ValueError("io_timeout_s must be finite and positive")
        self.snapshot = None
        self.setup_block = None
        self.setup_payload = None
        self.backup_archived = False
        self.mutated = False
        self.configured = False
        self.armed = False
        self.completed = False
        self.restored = False
        self.capture_id = str(uuid.uuid4())
        self.events = []
        self.restore_result = None
        self.configured_readback = None
        self.raw_archive_directory = raw_archive_directory
        self.partial_channels = {}
        self.partial_preambles = {}
        self.time_grid_comparison = None
        self.max_origin_skew_samples = float(max_origin_skew_samples)
        if not math.isfinite(self.max_origin_skew_samples) or self.max_origin_skew_samples < 0:
            raise ValueError("max_origin_skew_samples must be finite and nonnegative")

    def _event(self, operation, **detail):
        self.events.append({"utc": datetime.now(timezone.utc).isoformat(),
                            "operation": operation, **detail})

    @contextmanager
    def _io(self, *, binary=False, deadline=None):
        r = self.resource
        original_timeout, original_term = r.timeout, r.read_termination
        seconds = self.io_timeout_s
        if deadline is not None:
            seconds = min(seconds, deadline - time.monotonic())
            if seconds <= 0:
                raise CaptureTimeout("Scope operation deadline expired")
        try:
            r.timeout = max(1, int(seconds * 1000))
            r.read_termination = None if binary else "\n"
            yield
        finally:
            r.timeout, r.read_termination = original_timeout, original_term

    def _query(self, command, *, deadline=None):
        with self._io(deadline=deadline):
            answer = str(self.resource.query(command)).strip()
        if not answer:
            raise ScopeCaptureError(f"Empty reply to {command}")
        return answer

    def _integer(self, command, *, deadline=None):
        answer = self._query(command, deadline=deadline)
        try:
            return int(answer)
        except ValueError as exc:
            raise ScopeCaptureError(f"Invalid integer response to {command}: {answer!r}") from exc

    def _binary_query(self, command, *, archive_path=None):
        # read_raw() reads the whole VISA message through EOI/END, with termchar
        # disabled. Strict declared-length parsing below rejects any short read.
        # Avoid a speculative extra read when an instrument omits final LF.
        with self._io(binary=True):
            self.resource.write(command)
            raw = bytes(self.resource.read_raw())
        # Persist the exact response BEFORE parsing/validation. A failed format
        # or length check must not discard the evidence needed to diagnose it.
        if archive_path is not None:
            with Path(archive_path).open("xb") as output:
                output.write(raw)
        parse_definite_block(raw)
        return raw

    def _write(self, command):
        if self.snapshot is None or not self.backup_archived:
            raise ScopeCaptureError("Complete preflight and archive_backup before any mutation")
        self.mutated = True  # A failed write may still reach the instrument.
        with self._io():
            self.resource.write(command)
        self._event("write", command=command)

    def _check_error(self):
        answer = self._query(":SYSTem:ERRor?")
        try:
            number = int(answer.split(",", 1)[0])
        except ValueError as exc:
            raise ScopeCaptureError(f"Invalid error queue reply: {answer!r}") from exc
        if number:
            raise ScopeCaptureError(f"Instrument error: {answer}")

    def _condition(self, *, deadline=None):
        condition = self._integer(STATE_QUERY, deadline=deadline)
        if condition < 0 or condition > 65535:
            raise ScopeCaptureError(f"Invalid operation condition register: {condition}")
        return condition

    def preflight(self):
        """Read-only capability checks, setup backup, and run-state snapshot.

        AER?/TER? consume their event latches; no setup/acquisition write occurs.
        A failed query is not retried and no fallback command is guessed.
        """
        if self.snapshot is not None or self.mutated:
            raise ScopeCaptureError("Use a new adapter for a new capture")
        command = "*IDN?"
        try:
            idn = self._query(command)
            if "DSO-X 6004A" not in idn or (self.expected_serial and self.expected_serial not in idn):
                raise ScopeCaptureError(f"Unexpected instrument: {idn}")
            command = STATE_QUERY
            condition = self._condition()
            if not condition & REMOTE_ENABLED_MASK:
                raise ScopeCaptureError("Remote interface disabled (operation bit 4 is zero)")
            queries = {}
            for command in self.BASE_QUERIES:
                queries[command] = self._query(command)
            for command in (":AER?", ":TER?"):
                event = self._integer(command)
                if event not in (0, 1):
                    raise ScopeCaptureError(f"Invalid event register: {event}")
                queries[command] = str(event)
            command = "*OPC?"
            if self._integer(command) != 1:
                raise ScopeCaptureError("*OPC? did not return 1")
            command = ":SYSTem:SETup?"
            block = self._binary_query(command)
            payload = parse_definite_block(block)
            command = ":SYSTem:ERRor?"
            self._check_error()
            command = STATE_QUERY
            final_condition = self._condition()
            if bool(condition & RUN_MASK) != bool(final_condition & RUN_MASK):
                raise ScopeCaptureError("Run state changed during preflight; repeat with stable instrument")
            self.setup_block, self.setup_payload = block, payload
            self.snapshot = {"utc": datetime.now(timezone.utc).isoformat(), "idn": idn,
                "capture_id": self.capture_id, "operation_condition": condition,
                "initial_running": bool(condition & RUN_MASK), "queries": queries,
                "setup_block_sha256": sha256(block), "setup_payload_sha256": sha256(payload),
                "setup_payload_bytes": len(payload), "guide_url": GUIDE_URL,
                "run_state_limitation": "RUN bit distinguishes running/stopped, not continuous RUN/armed SINGLE",
                "restoration_limitation": "Old acquisition memory and consumed AER/TER events cannot be restored"}
            self._event("preflight_complete")
            return self.snapshot
        except Exception as exc:
            self._event("preflight_failed", command=command, error=str(exc), mutated=self.mutated)
            raise CapabilityError(f"Preflight failed at {command}; no setup mutation: {exc}") from exc

    def archive_backup(self, directory):
        """Persist complete backup before first mutation; never overwrite files."""
        if self.snapshot is None:
            raise ScopeCaptureError("Preflight has not succeeded")
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        for name, data in (("setup_block.bin", self.setup_block), ("setup_payload.bin", self.setup_payload),
                           ("snapshot.json", json.dumps(self.snapshot, indent=2).encode("utf-8"))):
            with (path / name).open("xb") as output:
                output.write(data)
        if sha256((path / "setup_payload.bin").read_bytes()) != self.snapshot["setup_payload_sha256"]:
            raise ScopeCaptureError("Archived setup backup hash mismatch")
        self.backup_archived = True
        if self.raw_archive_directory is None:
            self.raw_archive_directory = path.parent / f"scope_raw_{self.capture_id}"
        return str(path)

    def configure(self, *, time_range_s, time_position_s, channel_range_v,
                  channel_offset_v, trigger_channel=2, trigger_level_v=0.1,
                  waveform_points=1_000_000):
        """Explicit caller-selected settings; keeps input impedance/probe factors."""
        if self.mutated:
            raise ScopeCaptureError("configure() may be called only once")
        values = [time_range_s, time_position_s, trigger_level_v]
        values += [channel_range_v[ch] for ch in (1, 2)]
        values += [channel_offset_v[ch] for ch in (1, 2)]
        if not all(math.isfinite(float(v)) for v in values):
            raise ValueError("Capture settings must be finite")
        if time_range_s <= 0 or any(channel_range_v[ch] <= 0 for ch in (1, 2)):
            raise ValueError("Time/voltage ranges must be positive")
        if trigger_channel not in (1, 2) or not 1 <= int(waveform_points) <= 10_000_000:
            raise ValueError("Invalid trigger channel/point request")
        self.waveform_points = int(waveform_points)
        self._write(":STOP")
        if self._integer("*OPC?") != 1 or self._condition() & RUN_MASK:
            raise ScopeCaptureError("STOP did not complete")
        for command in (":TIMebase:MODE MAIN", ":TIMebase:REFerence CENTer",
                        f":TIMebase:RANGe {time_range_s:.12g}", f":TIMebase:POSition {time_position_s:.12g}",
                        ":ACQuire:MODE RTIMe", ":ACQuire:TYPE NORMal"):
            self._write(command)
        for ch in (1, 2):
            for command in (f":CHANnel{ch}:DISPlay 1", f":CHANnel{ch}:COUPling DC",
                            f":CHANnel{ch}:RANGe {channel_range_v[ch]:.12g}",
                            f":CHANnel{ch}:OFFSet {channel_offset_v[ch]:.12g}"):
                self._write(command)
        for command in (":TRIGger:MODE EDGE", ":TRIGger:SWEep NORMal",
                        f":TRIGger:EDGE:SOURce CHANnel{trigger_channel}", ":TRIGger:EDGE:SLOPe POSitive",
                        ":TRIGger:EDGE:REJect OFF", ":TRIGger:EDGE:COUPling DC",
                        f":TRIGger:EDGE:LEVel {trigger_level_v:.12g},CHANnel{trigger_channel}"):
            self._write(command)
        self._check_error()
        self.configured_readback = {q: self._query(q) for q in self.BASE_QUERIES
                                   if not q.startswith(":WAVeform:")}
        expected = {":TIMebase:MODE?": "MAIN", ":ACQuire:MODE?": "RTIM", ":ACQuire:TYPE?": "NORM",
                    ":TRIGger:MODE?": "EDGE", ":TRIGger:SWEep?": "NORM",
                    ":TRIGger:EDGE:SOURce?": f"CHAN{trigger_channel}", ":TRIGger:EDGE:SLOPe?": "POS"}
        for query, value in expected.items():
            if self.configured_readback[query] != value:
                raise ScopeCaptureError(f"Setup readback mismatch: {query}")
        numeric_expected = {":TIMebase:RANGe?": time_range_s, ":TIMebase:POSition?": time_position_s,
                            f":TRIGger:EDGE:LEVel? CHANnel{trigger_channel}": trigger_level_v}
        for ch in (1, 2):
            numeric_expected.update({f":CHANnel{ch}:RANGe?": channel_range_v[ch],
                                     f":CHANnel{ch}:OFFSet?": channel_offset_v[ch]})
            if self.configured_readback[f":CHANnel{ch}:DISPlay?"] != "1" or self.configured_readback[f":CHANnel{ch}:COUPling?"] != "DC":
                raise ScopeCaptureError(f"Channel {ch} is not displayed with DC coupling")
        for query, value in numeric_expected.items():
            # Instrument decimal replies may round at their published resolution;
            # this checks setup values, not the accuracy of a voltage measurement.
            if not math.isclose(float(self.configured_readback[query]), float(value), rel_tol=1e-6, abs_tol=1e-12):
                raise ScopeCaptureError(f"Numeric setup readback differs from requested setting: {query}")
        for ch in (1, 2):
            for setting in ("IMPedance", "PROBe"):
                q = f":CHANnel{ch}:{setting}?"
                if not self._equivalent(self.configured_readback[q], self.snapshot["queries"][q]):
                    raise ScopeCaptureError(f"Preserved input setting changed: {q}")
        self.configured = True
        self._event("configured", readback=self.configured_readback, waveform_points_requested=self.waveform_points)

    def arm(self, *, timeout_s=5.0, poll_s=0.05):
        if not self.configured or self.armed or self.completed:
            raise ScopeCaptureError("Capture is not in the configured, unarmed state")
        deadline = time.monotonic() + self._positive_timeout(timeout_s)
        poll_s = self._positive_timeout(poll_s)
        if self.raw_archive_directory is None:
            raise ScopeCaptureError("A raw archive directory is required before acquisition")
        raw_directory = Path(self.raw_archive_directory)
        raw_directory.mkdir(parents=True, exist_ok=True)
        # Fail before acquiring if this location contains an earlier capture.
        if any(raw_directory.iterdir()):
            raise ScopeCaptureError(f"Raw archive directory is not empty: {raw_directory}")
        self._integer(":AER?", deadline=deadline)  # clear pre-existing event latches
        self._integer(":TER?", deadline=deadline)
        self._write(":SINGle")
        while time.monotonic() < deadline:
            armed_event = self._integer(":AER?", deadline=deadline)
            running = bool(self._condition(deadline=deadline) & RUN_MASK)
            if not running:
                raise ScopeCaptureError("SINGLE already stopped before DUT start; unexpected early trigger")
            if armed_event == 1:
                self.armed = True
                self._event("armed")
                return
            time.sleep(min(poll_s, max(0, deadline - time.monotonic())))
        raise CaptureTimeout("SINGLE did not arm before deadline")

    @staticmethod
    def _positive_timeout(value):
        value = float(value)
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Timeout must be finite and positive")
        return value

    def wait_and_read(self, *, timeout_s=10.0, poll_s=0.05):
        """Wait for triggered STOP, then read both channels without re-acquiring."""
        if not self.armed or self.completed:
            raise ScopeCaptureError("Arm once and start the DUT before waiting")
        deadline = time.monotonic() + self._positive_timeout(timeout_s)
        poll_s = self._positive_timeout(poll_s)
        while self._condition(deadline=deadline) & RUN_MASK:
            time.sleep(min(poll_s, max(0, deadline - time.monotonic())))
        if self._integer(":TER?", deadline=deadline) != 1:
            raise ScopeCaptureError("Scope stopped without a fresh trigger event")
        self.completed = True
        self._event("triggered_acquisition_complete")
        channels = self.partial_channels
        raw_directory = Path(self.raw_archive_directory)
        for ch in (1, 2):
            if self._condition() & RUN_MASK:
                raise ScopeCaptureError("Unexpected acquisition restart during readout")
            for command in (f":WAVeform:SOURce CHANnel{ch}", ":WAVeform:FORMat WORD",
                            ":WAVeform:BYTeorder LSBF", ":WAVeform:UNSigned 1",
                            ":WAVeform:POINts:MODE RAW", f":WAVeform:POINts {self.waveform_points}"):
                self._write(command)
            for query, expected in ((":WAVeform:FORMat?", "WORD"), (":WAVeform:BYTeorder?", "LSBF"),
                                    (":WAVeform:UNSigned?", "1"), (":WAVeform:POINts:MODE?", "RAW")):
                if self._query(query) != expected:
                    raise ScopeCaptureError(f"Waveform transfer setting mismatch: {query}")
            preamble = self._query(":WAVeform:PREamble?")
            points = self._integer(":WAVeform:POINts?")
            self.partial_preambles[ch] = {"preamble_text": preamble, "queried_points": points}
            with (raw_directory / f"ch{ch}.preamble.json").open("x", encoding="utf-8") as output:
                json.dump({"capture_id": self.capture_id, "channel": ch,
                           **self.partial_preambles[ch]}, output, indent=2)
            raw = self._binary_query(":WAVeform:DATA?",
                                     archive_path=raw_directory / f"ch{ch}.ieee_block.bin")
            # Available to the caller even if the independent decode fails.
            channels[ch] = {"raw_block": raw, **self.partial_preambles[ch]}
            payload = parse_definite_block(raw)
            with (raw_directory / f"ch{ch}.payload.bin").open("xb") as output:
                output.write(payload)
            channels[ch] = decode_word_waveform(raw, preamble, points)
            self._event("channel_raw_archived", channel=ch, points=points,
                        raw_sha256=sha256(raw), payload_sha256=sha256(payload),
                        archive_directory=str(raw_directory))
            if self._condition() & RUN_MASK:
                raise ScopeCaptureError("Scope restarted during channel transfer")
        self.time_grid_comparison = {
            key: {"ch1": channels[1]["preamble"][key], "ch2": channels[2]["preamble"][key],
                  "delta_ch2_minus_ch1": channels[2]["preamble"][key] - channels[1]["preamble"][key],
                  "exact_equal": channels[1]["preamble"][key] == channels[2]["preamble"][key]}
            for key in ("points", "x_increment", "x_origin", "x_reference")}
        # This is an explicit voltage-only analysis policy, not an assumption
        # that channel origins or physical delays are identical. Actual run02
        # recovered preambles differed by 11.5 ps at an 8 ns sample interval.
        # Keep both native time arrays; never resample or subtract this delta.
        # Points, increment and reference remain exact comparisons.
        origin = self.time_grid_comparison["x_origin"]
        origin["delta_samples"] = origin["delta_ch2_minus_ch1"] / channels[1]["preamble"]["x_increment"]
        origin["allowed_skew_samples"] = self.max_origin_skew_samples
        origin["accepted"] = abs(origin["delta_samples"]) <= self.max_origin_skew_samples
        for key in ("points", "x_increment", "x_reference"):
            self.time_grid_comparison[key]["accepted"] = self.time_grid_comparison[key]["exact_equal"]
        with (raw_directory / "time_grid_comparison.json").open("x", encoding="utf-8") as output:
            json.dump(self.time_grid_comparison, output, indent=2)
        self._event("time_grid_comparison", values=self.time_grid_comparison)
        mismatches = {key: row for key, row in self.time_grid_comparison.items() if not row["accepted"]}
        if mismatches:
            raise ScopeCaptureError(f"CH1/CH2 acquisition time grids disagree: {mismatches}; "
                                    f"raw/preamble evidence preserved at {raw_directory}")
        final_config = {q: self._query(q) for q in self.configured_readback}
        if any(not self._equivalent(final_config[q], self.configured_readback[q]) for q in final_config):
            raise ScopeCaptureError("Acquisition settings changed between configure and readout")
        self._check_error()
        self._event("two_channel_readout_complete", points=channels[1]["preamble"]["points"])
        return {"capture_id": self.capture_id, "same_acquisition": True,
                "same_acquisition_basis": "One SINGLE, fresh AER/TER, STOP maintained across both RAW reads; exclusive access required",
                "configured_readback": self.configured_readback, "channels": channels,
                "time_grid_comparison": self.time_grid_comparison,
                "time_grid_policy": {"max_origin_skew_samples": self.max_origin_skew_samples,
                    "native_time_arrays_preserved": True, "resampled": False,
                    "precision_timing_or_zero_channel_skew_claimed": False},
                "events": list(self.events), "measurement_kind": "physical oscilloscope acquisition"}

    @staticmethod
    def _equivalent(a, b):
        if a == b:
            return True
        try:
            return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-14)
        except ValueError:
            return False

    def restore(self):
        """Restore complete saved setup and original RUN/STOP; verify readback."""
        if self.restored:
            return self.restore_result
        if not self.mutated:
            self.restore_result = {"needed": False, "passed": True}
            return self.restore_result
        if self.setup_payload is None or self.snapshot is None:
            raise ScopeCaptureError("Cannot restore: no complete setup backup")
        try:
            self._write(":STOP")
            with self._io(binary=True):
                self.resource.write_raw(b":SYSTem:SETup " + make_definite_block(self.setup_payload) + b"\n")
            if self._integer("*OPC?") != 1:
                raise ScopeCaptureError("Setup restoration did not complete")
            # Setup restoration can affect acquisition state; explicitly restore it.
            self._write(":RUN" if self.snapshot["initial_running"] else ":STOP")
            if self._integer("*OPC?") != 1:
                raise ScopeCaptureError("Restored run state did not complete")
            running = bool(self._condition() & RUN_MASK)
            if running != self.snapshot["initial_running"]:
                raise ScopeCaptureError("Original RUN/STOP state was not restored")
            actual = {q: self._query(q) for q in self.BASE_QUERIES}
            # Effective waveform point count depends on the newly acquired
            # record; restoring setup cannot restore the old acquisition buffer.
            dynamic_queries = {":WAVeform:POINts?"}
            mismatches = {q: {"before": self.snapshot["queries"][q], "after": actual[q]}
                          for q in actual if q not in dynamic_queries and not self._equivalent(actual[q], self.snapshot["queries"][q])}
            self._check_error()
            if mismatches:
                raise ScopeCaptureError(f"Restoration readback mismatch: {mismatches}")
            self.restored = True
            self.restore_result = {"needed": True, "passed": True, "running": running, "readback": actual,
                                   "dynamic_not_compared": sorted(dynamic_queries)}
            self._event("restored")
            return self.restore_result
        except Exception as exc:
            self.restore_result = {"needed": True, "passed": False, "error": str(exc)}
            self._event("restore_failed", error=str(exc))
            raise ScopeCaptureError(f"Scope restoration unconfirmed: {exc}") from exc

    def __enter__(self):
        self.preflight()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.restore()
        except Exception as restore_error:
            if exc_value is not None:
                raise ScopeCaptureError(f"Capture failed ({exc_value}); restoration also failed ({restore_error})") from exc_value
            raise
        return False


def save_capture(record, directory):
    """Lossless raw blocks + NPZ codes/scaling + JSON metadata, no overwrites."""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    metadata = {key: value for key, value in record.items() if key != "channels"}
    metadata["channels"] = {}
    for ch, waveform in record["channels"].items():
        raw_path = path / f"ch{ch}.ieee_block.bin"
        with raw_path.open("xb") as output:
            output.write(waveform["raw_block"])
        payload_path = path / f"ch{ch}.payload.bin"
        with payload_path.open("xb") as output:
            output.write(parse_definite_block(waveform["raw_block"]))
        npz_path = path / f"ch{ch}.npz"
        arrays = {key: waveform[key] for key in ("raw_codes", "time_s", "voltage_v", "invalid")}
        with npz_path.open("xb") as output:
            np.savez_compressed(output, **arrays)
        with np.load(npz_path, allow_pickle=False) as loaded:
            if not all(np.array_equal(loaded[key], value, equal_nan=True) for key, value in arrays.items()):
                raise ScopeCaptureError("Saved waveform reload mismatch")
        if sha256(raw_path.read_bytes()) != waveform["raw_sha256"]:
            raise ScopeCaptureError("Saved raw block reload hash mismatch")
        metadata["channels"][str(ch)] = {key: waveform[key] for key in
            ("preamble", "preamble_text", "raw_sha256", "payload_sha256", "special_codes")}
        metadata["channels"][str(ch)].update({"npz_sha256": sha256(npz_path.read_bytes()), "archive_verified": True})
    with (path / "capture.json").open("x", encoding="utf-8") as output:
        json.dump(metadata, output, indent=2)
    return metadata
