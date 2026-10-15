"""Validated quantum circuit document and ideal pulse timeline.

Channel numbers are one-based editor labels, not hardware mappings.  This
module deliberately imports no compiler, instrument, Qt, or hardware code.
AWG settings change the held channel value; a gate ending does not restore it.
"""
from __future__ import annotations

import math
try:
    from .quantum_circuit_loops import normalize_loops, _expand_validated
except ImportError:
    from quantum_circuit_loops import normalize_loops, _expand_validated


MAX_QUBITS = 32
MAX_GATES = 512
MAX_CHANNEL = 64
MAX_ACTIONS = 4096


def default_document() -> dict:
    """Return a fresh circuit with one qubit and a zero AWG 1 baseline."""
    return {"version": 1, "shots": 1, "qubits": [{"id": "q1", "name": "q1"}],
            "awg_baselines": [{"channel": 1, "voltage_mv": 0.0}], "gates": []}


def _object(value, where, required, optional=()):
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object.")
    missing = set(required) - value.keys()
    unknown = value.keys() - set(required) - set(optional)
    if missing:
        raise ValueError(f"{where} is missing {', '.join(sorted(missing))}.")
    if unknown:
        raise ValueError(f"{where} has unknown fields: {', '.join(map(str, unknown))}.")
    return value


def _list(value, where, maximum, minimum=0):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError(f"{where} must be a list with {minimum}–{maximum} entries.")
    return value


def _text(value, where):
    if not isinstance(value, str) or not value.strip() or len(value) > 80:
        raise ValueError(f"{where} must contain 1–80 characters.")
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"{where} cannot contain control characters.")
    return value.strip()


def _number(value, where, *, minimum=None, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{where} must be a finite number.")
    try:
        result = float(value)
    except (OverflowError, ValueError):
        raise ValueError(f"{where} must be a finite number.") from None
    if not math.isfinite(result):
        raise ValueError(f"{where} must be a finite number.")
    if minimum is not None and result < minimum:
        raise ValueError(f"{where} must be at least {minimum}.")
    if positive and result <= 0:
        raise ValueError(f"{where} must be greater than zero.")
    return result


def _integer(value, where, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{where} must be an integer from {minimum} to {maximum}.")
    return value


def _channel(value, where):
    return _integer(value, where, 1, MAX_CHANNEL)


def _exceeds(value, bound):
    # Four floating-point ULPs admit decimal boundaries such as .1 + .2 == .3,
    # without admitting a fixed absolute timing tolerance or real overlaps.
    return value > bound and value - bound > 4 * max(math.ulp(value), math.ulp(bound))


def _end(start, duration, where):
    end = start + duration
    if not math.isfinite(end) or end <= start:
        raise ValueError(f"{where} end time must be finite and later than its start.")
    return end


def _window(value, where, gate_duration, extra=()):
    value = _object(value, where, ("delay_us", "duration_us", *extra))
    delay = _number(value["delay_us"], f"{where}.delay_us", minimum=0)
    duration = _number(value["duration_us"], f"{where}.duration_us", positive=True)
    end = _end(delay, duration, where)
    if _exceeds(end, gate_duration):
        raise ValueError(f"{where} must lie within the gate duration.")
    if end > gate_duration:
        duration = gate_duration - delay
    return {"delay_us": delay, "duration_us": duration}


def _check_overlaps(intervals, label):
    for resource, entries in intervals.items():
        previous_end = None
        previous_id = None
        for start, end, gate_id in sorted(entries):
            if previous_end is not None and _exceeds(previous_end, start):
                raise ValueError(f"{label} {resource}: gates {previous_id} and {gate_id} overlap.")
            previous_end, previous_id = end, gate_id


def _awg_events(document):
    values = {row["channel"]: row["voltage_mv"] for row in document["awg_baselines"]}
    events = {}
    for gate in sorted(document["gates"], key=lambda row: (row["start_us"], row["id"])):
        for setting in gate["awg"]:
            channel = setting["channel"]
            initial = values.get(channel, 0.0)
            target = (initial + setting["value_mv"] if setting["mode"] == "relative"
                      else setting["value_mv"])
            if not math.isfinite(target):
                raise ValueError(f"Gate {gate['id']} resolves AWG {channel} to a non-finite voltage.")
            events.setdefault(channel, []).append({
                "gate_id": gate["id"], "start_us": gate["start_us"],
                "end_us": gate["start_us"] + gate["duration_us"],
                "start_mv": initial, "target_mv": target,
                "mode": setting["mode"], "value_mv": setting["value_mv"],
                "ramp_us": setting["ramp_us"],
            })
            values[channel] = target
    return events


def validate_document(data) -> dict:
    """Validate a circuit transaction and return an independent normalized copy.

    Gates occupy each selected qubit and AWG channel for their full duration.
    RF channels occupy only their pulse intervals.  Touching intervals are
    allowed.  Input order is retained for editing; AWG values resolve by time.
    """
    data = _object(data, "Circuit", ("version", "qubits", "gates"), ("awg_baselines", "shots", "loops"))
    version = _integer(data["version"], "Circuit version", 1, 2)
    if version == 1 and data.get('loops'):
        raise ValueError('Loops require circuit version 2.')
    shots = _integer(data.get("shots", 1), "Shots", 1, 1_000_000)
    qubits = []
    qubit_ids = set()
    for index, row in enumerate(_list(data["qubits"], "Qubits", MAX_QUBITS, 1)):
        where = f"Qubit {index + 1}"
        row = _object(row, where, ("id", "name"))
        identifier = _text(row["id"], f"{where}.id")
        if identifier in qubit_ids:
            raise ValueError(f"Duplicate qubit ID: {identifier}.")
        qubit_ids.add(identifier)
        qubits.append({"id": identifier, "name": _text(row["name"], f"{where}.name")})

    baselines = []
    baseline_channels = set()
    for row in _list(data.get("awg_baselines", []), "AWG baselines", MAX_CHANNEL):
        row = _object(row, "AWG baseline", ("channel", "voltage_mv"))
        channel = _channel(row["channel"], "AWG baseline channel")
        if channel in baseline_channels:
            raise ValueError(f"Duplicate baseline for AWG {channel}.")
        baseline_channels.add(channel)
        baselines.append({"channel": channel, "voltage_mv": _number(row["voltage_mv"], "Baseline voltage")})

    gates = []
    gate_ids = set()
    qubit_intervals, awg_intervals, rf_intervals = {}, {}, {}
    action_count = 0
    for index, row in enumerate(_list(data["gates"], "Gates", MAX_GATES)):
        where = f"Gate {index + 1}"
        row = _object(row, where, ("id", "name", "qubits", "start_us", "duration_us"),
                      ("awg", "rf", "acquisition"))
        identifier = _text(row["id"], f"{where}.id")
        if identifier in gate_ids:
            raise ValueError(f"Duplicate gate ID: {identifier}.")
        gate_ids.add(identifier)
        selected = [_text(item, f"{where}.qubits") for item in
                    _list(row["qubits"], f"{where}.qubits", MAX_QUBITS, 1)]
        if len(set(selected)) != len(selected):
            raise ValueError(f"{where} lists the same qubit more than once.")
        if not set(selected) <= qubit_ids:
            raise ValueError(f"{where} refers to an unknown qubit.")
        start = _number(row["start_us"], f"{where}.start_us", minimum=0)
        duration = _number(row["duration_us"], f"{where}.duration_us", positive=True)
        end = _end(start, duration, where)
        gate = {"id": identifier, "name": _text(row["name"], f"{where}.name"),
                "qubits": selected, "start_us": start, "duration_us": duration,
                "awg": [], "rf": [], "acquisition": None}
        for qubit in selected:
            qubit_intervals.setdefault(qubit, []).append((start, end, identifier))
        awg_channels = set()
        for setting in _list(row.get("awg", []), f"{where}.awg", MAX_CHANNEL):
            setting = _object(setting, f"{where} AWG", ("channel", "mode", "value_mv"), ("ramp_us",))
            channel = _channel(setting["channel"], f"{where} AWG channel")
            if channel in awg_channels:
                raise ValueError(f"{where} has multiple settings for AWG {channel}.")
            awg_channels.add(channel)
            mode = setting["mode"]
            if mode not in ("relative", "absolute"):
                raise ValueError(f"{where} AWG mode must be relative or absolute.")
            ramp = _number(setting.get("ramp_us", 0), f"{where} AWG ramp", minimum=0)
            if _exceeds(ramp, duration):
                raise ValueError(f"{where} AWG ramp must lie within the gate duration.")
            if ramp > 0:
                _end(start, ramp, f"{where} AWG ramp")
            gate["awg"].append({"channel": channel, "mode": mode,
                "value_mv": _number(setting["value_mv"], f"{where} AWG voltage"),
                "ramp_us": min(ramp, duration)})
            awg_intervals.setdefault(channel, []).append((start, end, identifier))
        for setting in _list(row.get("rf", []), f"{where}.rf", MAX_CHANNEL):
            rf_where = f"{where} RF"
            normalized = _window(setting, rf_where, duration,
                ("channel", "frequency_mhz", "phase_deg", "gain"))
            channel = _channel(setting["channel"], f"{rf_where} channel")
            normalized.update(channel=channel,
                frequency_mhz=_number(setting["frequency_mhz"], f"{rf_where} frequency", minimum=0),
                phase_deg=_number(setting["phase_deg"], f"{rf_where} phase"),
                gain=_integer(setting["gain"], f"{rf_where} gain", -32768, 32767))
            gate["rf"].append(normalized)
            rf_start = start + normalized["delay_us"]
            rf_end = _end(rf_start, normalized["duration_us"], rf_where)
            rf_intervals.setdefault(channel, []).append((rf_start, rf_end, identifier))
        if row.get("acquisition") is not None:
            gate["acquisition"] = _window(row["acquisition"], f"{where} acquisition", duration)
            _end(start + gate["acquisition"]["delay_us"], gate["acquisition"]["duration_us"],
                 f"{where} acquisition")
        action_count += len(gate["awg"]) + len(gate["rf"]) + (gate["acquisition"] is not None)
        if action_count > MAX_ACTIONS:
            raise ValueError(f"Circuit supports at most {MAX_ACTIONS} pulse settings.")
        gates.append(gate)
    _check_overlaps(qubit_intervals, "Qubit")
    _check_overlaps(awg_intervals, "AWG")
    _check_overlaps(rf_intervals, "RF")
    result = {"version": version, "shots": shots, "qubits": qubits, "awg_baselines": baselines, "gates": gates}
    if version == 2:
        result['loops'] = normalize_loops(data.get('loops', []), gates)
    _awg_events({**result, 'gates': _expand_validated(result)['gates']})
    return result


def build_timeline(document) -> dict:
    """Build an ideal, unquantized pulse preview from a validated copy."""
    document = validate_document(document)
    expanded = _expand_validated(document)
    gates = expanded['gates']
    duration = expanded.get('duration_us', max((gate["start_us"] + gate["duration_us"] for gate in gates), default=0.0))
    baseline = {row["channel"]: row["voltage_mv"] for row in document["awg_baselines"]}
    awg_events = _awg_events({**document, 'gates': gates})
    awg = []
    for channel in sorted(baseline.keys() | awg_events.keys()):
        points = [[0.0, baseline.get(channel, 0.0)]]
        for event in awg_events.get(channel, []):
            # Accepted decimal-touch boundaries may differ by a few ULPs.
            # Keep the rendered polyline monotonic at those shared boundaries.
            start = max(event["start_us"], points[-1][0])
            initial = [start, event["start_mv"]]
            if points[-1] != initial:
                points.append(initial)
            target = [max(start, event["start_us"] + event["ramp_us"]), event["target_mv"]]
            if points[-1] != target:
                points.append(target)
        if points[-1][0] != duration:
            points.append([duration, points[-1][1]])
        awg.append({"channel": channel, "points": points, "events": awg_events.get(channel, [])})
    rf_events = {}
    acquisition = []
    for gate in sorted(gates, key=lambda row: (row["start_us"], row["id"])):
        for pulse in gate["rf"]:
            start = gate["start_us"] + pulse["delay_us"]
            rf_events.setdefault(pulse["channel"], []).append({
                "gate_id": gate["id"], "start_us": start, "end_us": start + pulse["duration_us"],
                "frequency_mhz": pulse["frequency_mhz"], "phase_deg": pulse["phase_deg"], "gain": pulse["gain"]})
        if gate["acquisition"] is not None:
            window = gate["acquisition"]
            start = gate["start_us"] + window["delay_us"]
            acquisition.append({"gate_id": gate["id"], "start_us": start, "end_us": start + window["duration_us"]})
    result = {"duration_us": duration, "awg": awg,
            "rf": [{"channel": channel, "events": sorted(events, key=lambda item: (item["start_us"], item["gate_id"]))}
                   for channel, events in sorted(rf_events.items())],
            "acquisition": sorted(acquisition, key=lambda item: (item["start_us"], item["gate_id"])),
            "gates": gates}
    if document.get('loops'):
        result.update(loops=expanded['regions'], gate_origins=expanded['origins'])
    return result
