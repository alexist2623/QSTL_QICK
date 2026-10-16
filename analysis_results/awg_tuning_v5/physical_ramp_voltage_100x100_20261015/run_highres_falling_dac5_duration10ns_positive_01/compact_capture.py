"""Compact physical voltage capture; no instrument access on import.

Reuse the reviewed 3x3 adapter's preflight/setup/arm/restore unchanged. Only the
readout/archive is specialized: save each complete IEEE WORD block once as gzip
and its preamble as JSON, including failed validations. Codes remain in memory;
time/voltage arrays are reconstructed on demand, never duplicated on disk.

API: CompactScopeCapture(resource, raw_archive_directory=unique_directory,
max_origin_skew_samples=1.0, max_sample_interval_s=5e-7). All other methods and
configure arguments are those of ScopeCapture. wait_and_read() writes compact
capture.json and returns channels with raw_codes, preamble, and archive paths.
Do not call the older save_capture(), which deliberately stores expanded arrays.

Official guide: https://www.keysight.com/cf/en/assets/9018-07124/programming-guides/9018-07124.pdf
RAW/WORD/scaling: pp1524-1555; source-specific XORigin: p1554. No claim of channel
skew being zero or precision timing is made. The caller owns all device access.
"""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import time

import numpy as np


def _find_base():
    sibling = Path(__file__).resolve().parent / "scope_capture.py"
    if sibling.is_file():
        return sibling
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "physical_voltage_2axis_20261015" / "scope_capture.py"
        if candidate.is_file():
            return candidate
    raise ImportError("Cannot find preserved physical_voltage_2axis scope adapter")


BASE_PATH = _find_base()
BASE_SHA256 = hashlib.sha256(BASE_PATH.read_bytes()).hexdigest()
EXPECTED_BASE_SHA256 = "f01b8e861eef7dc71b34219c861acc52ecaf2796d3c5ae6da94cfdc498ef39e8"
if BASE_SHA256 != EXPECTED_BASE_SHA256:
    raise ImportError("Preserved base scope adapter changed; review before using compact capture")
_spec = importlib.util.spec_from_file_location("_voltage_scope_preserved", BASE_PATH)
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
ScopeCaptureError = base.ScopeCaptureError


def _json_exclusive(path, value):
    with Path(path).open("x", encoding="utf-8") as output:
        json.dump(value, output, indent=2)


def _gzip_exclusive(path, raw):
    """Archive/reload every byte, including header and LF, before validation."""
    path = Path(path)
    with path.open("xb") as output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0, compresslevel=6) as stream:
            stream.write(raw)
    expected = hashlib.sha256(raw).hexdigest()
    digest, count = hashlib.sha256(), 0
    with gzip.open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            count += len(chunk)
    if count != len(raw) or digest.hexdigest() != expected:
        raise ScopeCaptureError("Raw gzip archive reload mismatch")
    return {"path": str(path), "raw_bytes": len(raw), "raw_sha256": expected,
            "gzip_bytes": path.stat().st_size,
            "gzip_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "archive_verified": True}


def decode_codes(raw, preamble_text, queried_points):
    p = base.parse_preamble(preamble_text)
    payload = base.parse_definite_block(raw)
    if len(payload) != 2 * p["points"] or queried_points != p["points"]:
        raise ScopeCaptureError("Payload/preamble/query point counts disagree")
    codes = np.frombuffer(payload, dtype="<u2")
    special = {"hole": int(np.count_nonzero(codes == 0)),
               "clipped_low": int(np.count_nonzero(codes == 0x0100)),
               "clipped_high": int(np.count_nonzero(codes == 0xff00))}
    return {"preamble": p, "preamble_text": preamble_text,
            "raw_codes": codes, "codes": codes,
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "special_codes": special, "record_span_s": (p["points"] - 1) * p["x_increment"]}


def reload_channel(preamble_path, raw_gzip_path):
    """Offline reconstruction from exactly two files; no instrument required."""
    preamble = json.loads(Path(preamble_path).read_text(encoding="utf-8"))
    with gzip.open(raw_gzip_path, "rb") as stream:
        raw = stream.read()
    result = decode_codes(raw, preamble["preamble_text"], preamble["queried_points"])
    result["raw_sha256"] = hashlib.sha256(raw).hexdigest()
    return result


def scaled_slice(channel, start=0, stop=None):
    """Construct only the requested slice, preserving each channel's time axis."""
    p = channel["preamble"]
    if stop is None:
        stop = p["points"]
    if not 0 <= start <= stop <= p["points"]:
        raise ValueError("Invalid waveform slice")
    codes = channel["raw_codes"][start:stop]
    invalid = (codes == 0) | (codes == 0x0100) | (codes == 0xff00)
    voltage = (codes.astype(np.float64) - p["y_reference"]) * p["y_increment"] + p["y_origin"]
    voltage[invalid] = np.nan
    seconds = (np.arange(start, stop, dtype=np.float64) - p["x_reference"]) * p["x_increment"] + p["x_origin"]
    return seconds, voltage, invalid


def save_capture(record, directory):
    """Compatibility API: verify already-written compact files, no duplicates.

    wait_and_read has archived the bytes before any validation. Saving to a
    different path is rejected to avoid accidentally producing a second copy.
    Returns JSON-compatible capture metadata, like the prior save_capture API.
    """
    directory = Path(directory).resolve()
    if directory != Path(record["archive_directory"]).resolve():
        raise ScopeCaptureError("Use the same raw_archive_directory with save_capture")
    metadata = json.loads((directory / "capture.json").read_text(encoding="utf-8"))
    if metadata["capture_id"] != record["capture_id"]:
        raise ScopeCaptureError("Capture metadata identity mismatch")
    for ch, info in metadata["channels"].items():
        archive = info["archive"]
        raw_path = directory / Path(archive["path"]).name
        preamble_path = directory / Path(archive["preamble_path"]).name
        if hashlib.sha256(raw_path.read_bytes()).hexdigest() != archive["gzip_sha256"]:
            raise ScopeCaptureError("Compact waveform archive hash mismatch")
        if hashlib.sha256(preamble_path.read_bytes()).hexdigest() != archive["preamble_sha256"]:
            raise ScopeCaptureError("Compact preamble hash mismatch")
        reloaded = reload_channel(preamble_path, raw_path)
        if reloaded["raw_sha256"] != archive["raw_sha256"] or reloaded["payload_sha256"] != info["payload_sha256"]:
            raise ScopeCaptureError("Compact waveform reload hash mismatch")
        if not np.array_equal(reloaded["raw_codes"], record["channels"][int(ch)]["raw_codes"]):
            raise ScopeCaptureError("Compact waveform reload code mismatch")
    return metadata


class CompactScopeCapture(base.ScopeCapture):
    def __init__(self, resource, *, max_sample_interval_s=5e-7, **kwargs):
        super().__init__(resource, **kwargs)
        self.max_sample_interval_s = float(max_sample_interval_s)
        if not math.isfinite(self.max_sample_interval_s) or self.max_sample_interval_s <= 0:
            raise ValueError("max_sample_interval_s must be finite and positive")
        self.partial_archives = {}

    def _binary_query(self, command, *, archive_path=None):
        if archive_path is None:
            return super()._binary_query(command)
        with self._io(binary=True):
            self.resource.write(command)
            raw = bytes(self.resource.read_raw())
        # Save exact failed binary responses, too. Parsing occurs after reload.
        archive = _gzip_exclusive(archive_path, raw)
        self.partial_archives[str(archive_path)] = archive
        base.parse_definite_block(raw)
        return raw

    def wait_and_read(self, *, timeout_s=10.0, poll_s=0.05):
        """Same SINGLE/STOP invariant as base; compact evidence saved before checks."""
        if not self.armed or self.completed:
            raise ScopeCaptureError("Arm once and start the DUT before waiting")
        deadline = time.monotonic() + self._positive_timeout(timeout_s)
        poll_s = self._positive_timeout(poll_s)
        while self._condition(deadline=deadline) & base.RUN_MASK:
            time.sleep(min(poll_s, max(0, deadline - time.monotonic())))
        if self._integer(":TER?", deadline=deadline) != 1:
            raise ScopeCaptureError("Scope stopped without a fresh trigger event")
        self.completed = True
        self._event("triggered_acquisition_complete")
        directory = Path(self.raw_archive_directory)
        channels = self.partial_channels
        for ch in (1, 2):
            if self._condition() & base.RUN_MASK:
                raise ScopeCaptureError("Unexpected acquisition restart during readout")
            for command in (f":WAVeform:SOURce CHANnel{ch}", ":WAVeform:FORMat WORD",
                            ":WAVeform:BYTeorder LSBF", ":WAVeform:UNSigned 1",
                            ":WAVeform:POINts:MODE RAW", f":WAVeform:POINts {self.waveform_points}"):
                self._write(command)
            for query, expected in ((":WAVeform:FORMat?", "WORD"), (":WAVeform:BYTeorder?", "LSBF"),
                                    (":WAVeform:UNSigned?", "1"), (":WAVeform:POINts:MODE?", "RAW")):
                if self._query(query) != expected:
                    raise ScopeCaptureError(f"Waveform transfer setting mismatch: {query}")
            text = self._query(":WAVeform:PREamble?")
            points = self._integer(":WAVeform:POINts?")
            self.partial_preambles[ch] = {"capture_id": self.capture_id, "channel": ch,
                "preamble_text": text, "queried_points": points}
            preamble_path = directory / f"ch{ch}.preamble.json"
            _json_exclusive(preamble_path, self.partial_preambles[ch])
            raw_path = directory / f"ch{ch}.ieee_block.bin.gz"
            raw = self._binary_query(":WAVeform:DATA?", archive_path=raw_path)
            channels[ch] = decode_codes(raw, text, points)
            channels[ch]["archive"] = {**self.partial_archives[str(raw_path)],
                "preamble_path": str(preamble_path),
                "preamble_sha256": hashlib.sha256(preamble_path.read_bytes()).hexdigest()}
            self._event("channel_raw_archived", channel=ch, **channels[ch]["archive"])
            if self._condition() & base.RUN_MASK:
                raise ScopeCaptureError("Scope restarted during channel transfer")
        comparison = {
            key: {"ch1": channels[1]["preamble"][key], "ch2": channels[2]["preamble"][key],
                "delta_ch2_minus_ch1": channels[2]["preamble"][key] - channels[1]["preamble"][key],
                "exact_equal": channels[1]["preamble"][key] == channels[2]["preamble"][key]}
            for key in ("points", "x_increment", "x_origin", "x_reference")}
        origin = comparison["x_origin"]
        origin["delta_samples"] = origin["delta_ch2_minus_ch1"] / channels[1]["preamble"]["x_increment"]
        origin["allowed_skew_samples"] = self.max_origin_skew_samples
        origin["accepted"] = abs(origin["delta_samples"]) <= self.max_origin_skew_samples
        for key in ("points", "x_increment", "x_reference"):
            comparison[key]["accepted"] = comparison[key]["exact_equal"]
        sampling = {str(ch): {"x_increment_s": channels[ch]["preamble"]["x_increment"],
            "sample_rate_sa_s": 1.0 / channels[ch]["preamble"]["x_increment"],
            "record_span_s": channels[ch]["record_span_s"],
            "max_sample_interval_s": self.max_sample_interval_s,
            "accepted": channels[ch]["preamble"]["x_increment"] <= self.max_sample_interval_s}
            for ch in (1, 2)}
        self.time_grid_comparison = comparison
        _json_exclusive(directory / "time_grid_comparison.json", comparison)
        _json_exclusive(directory / "sampling_check.json", sampling)
        self._event("time_grid_comparison", values=comparison, sampling=sampling)
        metadata = {"capture_id": self.capture_id,
            "same_acquisition": False, "validation_passed": False,
            "configured_readback": self.configured_readback,
            "time_grid_comparison": comparison, "sampling_check": sampling,
            "time_grid_policy": {"max_origin_skew_samples": self.max_origin_skew_samples,
                "native_time_axes_preserved": True, "resampled": False,
                "precision_timing_or_zero_channel_skew_claimed": False},
            "adapter_source": {"base_path": str(BASE_PATH), "base_sha256": BASE_SHA256,
                "compact_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
            "channels": {str(ch): {key: value for key, value in channels[ch].items()
                if key not in ("codes", "raw_codes")} for ch in (1, 2)},
            "measurement_kind": "physical oscilloscope acquisition"}
        try:
            mismatches = {key: row for key, row in comparison.items() if not row["accepted"]}
            if mismatches:
                raise ScopeCaptureError(f"Time grids disagree: {mismatches}")
            if not all(row["accepted"] for row in sampling.values()):
                raise ScopeCaptureError(f"Insufficient recorded sample rate: {sampling}")
            final_config = {q: self._query(q) for q in self.configured_readback}
            if any(not self._equivalent(final_config[q], self.configured_readback[q]) for q in final_config):
                raise ScopeCaptureError("Acquisition settings changed between configure and readout")
            self._check_error()
            metadata["same_acquisition"] = True
            metadata["validation_passed"] = True
            metadata["same_acquisition_basis"] = "One SINGLE, fresh AER/TER, STOP during both RAW reads; exclusive access required"
            self._event("compact_readout_complete")
        except Exception as exc:
            metadata["error"] = str(exc)
            raise
        finally:
            metadata["events"] = list(self.events)
            _json_exclusive(directory / "capture.json", metadata)
        return {**metadata, "channels": channels, "archive_directory": str(directory)}
