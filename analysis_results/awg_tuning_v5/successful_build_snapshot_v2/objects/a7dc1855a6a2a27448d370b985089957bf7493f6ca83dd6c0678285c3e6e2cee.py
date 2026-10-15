"""Circuit transactions and independent ideal timing/state expectations."""
import copy
import math

import pytest

from quantum_circuit_model import (
    MAX_ACTIONS, MAX_CHANNEL, MAX_GATES, MAX_QUBITS,
    build_timeline, default_document, validate_document,
)


def gate(identifier="g1", start=0.0, duration=1.0, qubit="q1", **settings):
    result = {"id": identifier, "name": "X", "qubits": [qubit],
              "start_us": start, "duration_us": duration,
              "awg": [], "rf": [], "acquisition": None}
    result.update(settings)
    return result


def awg(value, mode="relative", channel=1, ramp=0.0):
    return {"channel": channel, "mode": mode, "value_mv": value, "ramp_us": ramp}


def rf(channel=1, delay=0.0, duration=1.0):
    return {"channel": channel, "delay_us": delay, "duration_us": duration,
            "frequency_mhz": 100.0, "phase_deg": 90.0, "gain": 1234}


def document(*gates, second_qubit=False):
    result = default_document()
    result["gates"] = list(gates)
    if second_qubit:
        result["qubits"].append({"id": "q2", "name": "Second qubit"})
    return result


def test_empty_circuit_fresh_defaults_and_baseline():
    first, second = default_document(), default_document()
    first["qubits"][0]["name"] = "changed"
    assert second["qubits"][0]["name"] == "q1"
    assert second["shots"] == 1
    timeline = build_timeline(second)
    assert timeline == {"duration_us": 0.0,
        "awg": [{"channel": 1, "points": [[0.0, 0.0]], "events": []}],
        "rf": [], "acquisition": [], "gates": []}


def test_relative_absolute_chain_resolves_by_time_and_holds_between_gates():
    first = gate("a", 2, 2, awg=[awg(5, ramp=1)])
    second = gate("b", 5, 1, awg=[awg(-5)])
    third = gate("c", 7, 2, awg=[awg(-2, "absolute", ramp=.5)])
    value = document(third, first, second)
    value["awg_baselines"][0]["voltage_mv"] = 10
    before = copy.deepcopy(value)
    timeline = build_timeline(value)
    assert value == before
    assert [row["id"] for row in timeline["gates"]] == ["c", "a", "b"]
    channel = timeline["awg"][0]
    assert channel["points"] == [[0, 10], [2, 10], [3, 15], [5, 15],
                                 [5, 10], [7, 10], [7.5, -2], [9, -2]]
    assert [(row["gate_id"], row["start_mv"], row["target_mv"])
            for row in channel["events"]] == [("a", 10, 15), ("b", 15, 10), ("c", 10, -2)]


def test_simultaneous_different_channels_and_qubits_are_independent():
    value = document(gate("b", 0, 2, "q2", awg=[awg(15, channel=2)]),
                     gate("a", 0, 1, awg=[awg(30)]), second_qubit=True)
    channels = build_timeline(value)["awg"]
    assert [row["channel"] for row in channels] == [1, 2]
    assert channels[0]["points"] == [[0, 0], [0, 30], [2, 30]]
    assert channels[1]["points"] == [[0, 0], [0, 15], [2, 15]]
    assert channels[1]["events"][0]["start_mv"] == 0  # Missing baseline.


def test_zero_delta_keeps_held_value_and_absolute_zero_is_an_explicit_step():
    value = document(gate("a", 0, awg=[awg(20)]), gate("b", 1, awg=[awg(0)]),
                     gate("c", 2, awg=[awg(0, "absolute")]))
    channel = build_timeline(value)["awg"][0]
    assert [row["target_mv"] for row in channel["events"]] == [20, 20, 0]
    assert [2.0, 20.0] in channel["points"]
    assert [2.0, 0.0] in channel["points"]
    assert channel["points"][-1] == [3.0, 0.0]


def test_rf_acquisition_absolute_windows_and_deterministic_order():
    value = document(gate("later", 8, 4, rf=[rf(3, 1, 2)],
                          acquisition={"delay_us": .5, "duration_us": 3}),
                     gate("early", 0, 4, rf=[rf(3, 2, 1)]))
    timeline = build_timeline(value)
    assert timeline["duration_us"] == 12
    assert timeline["rf"] == [{"channel": 3, "events": [
        {"gate_id": "early", "start_us": 2.0, "end_us": 3.0,
         "frequency_mhz": 100.0, "phase_deg": 90.0, "gain": 1234},
        {"gate_id": "later", "start_us": 9.0, "end_us": 11.0,
         "frequency_mhz": 100.0, "phase_deg": 90.0, "gain": 1234}]}]
    assert timeline["acquisition"] == [{"gate_id": "later", "start_us": 8.5, "end_us": 11.5}]


def test_touching_full_gate_intervals_allow_ramp_and_held_handoff():
    value = document(gate("a", 0, 1, awg=[awg(2, ramp=1)]),
                     gate("b", 1, 1, awg=[awg(3)]))
    assert build_timeline(value)["awg"][0]["points"] == [
        [0, 0], [1, 2], [1, 5], [2, 5]]


def test_decimal_touching_intervals_are_not_false_overlaps():
    value = document(gate("a", .1, .2, awg=[awg(1, ramp=.2)]),
                     gate("b", .3, .2, awg=[awg(1)]))
    assert len(validate_document(value)["gates"]) == 2
    times = [point[0] for point in build_timeline(value)["awg"][0]["points"]]
    assert times == sorted(times)
    bounded = document(gate(duration=.3, rf=[rf(delay=.1, duration=.2)]))
    assert build_timeline(bounded)["rf"][0]["events"][0]["end_us"] <= .3


@pytest.mark.parametrize("kind", ["qubit", "awg", "rf"])
def test_resource_conflicts_are_rejected_without_mutating_original(kind):
    first = gate("a", 0, 4)
    second = gate("b", 2, 4, "q1" if kind == "qubit" else "q2")
    if kind == "awg":
        first["awg"], second["awg"] = [awg(1)], [awg(2)]
    elif kind == "rf":
        first["rf"], second["rf"] = [rf(duration=3)], [rf(duration=1)]
    value = document(first, second, second_qubit=True)
    before = copy.deepcopy(value)
    with pytest.raises(ValueError, match="overlap"):
        validate_document(value)
    assert value == before


def test_rf_resource_is_only_occupied_for_pulse_not_full_gate():
    value = document(gate("a", 0, 4, rf=[rf(duration=1)]),
                     gate("b", 0, 4, "q2", rf=[rf(delay=1, duration=1)]),
                     second_qubit=True)
    assert len(build_timeline(value)["rf"][0]["events"]) == 2


def test_repeated_nonoverlapping_rf_pulses_on_same_channel_are_allowed():
    value = document(gate(duration=3, rf=[rf(delay=2), rf(delay=0)]))
    assert [row["start_us"] for row in build_timeline(value)["rf"][0]["events"]] == [0, 2]


def test_normalized_copy_is_independent_and_idempotent():
    value = document(gate(awg=[awg(10)], rf=[rf()],
                          acquisition={"delay_us": 0, "duration_us": 1}))
    value["shots"] = 20
    normalized = validate_document(value)
    assert normalized == validate_document(normalized)
    normalized["gates"][0]["awg"][0]["value_mv"] = 999
    normalized["gates"][0]["qubits"].append("another")
    normalized["awg_baselines"][0]["voltage_mv"] = 200
    assert value["gates"][0]["awg"][0]["value_mv"] == 10
    assert value["gates"][0]["qubits"] == ["q1"]
    assert value["awg_baselines"][0]["voltage_mv"] == 0


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), True, "1", 10**400])
@pytest.mark.parametrize("field", ["start_us", "duration_us"])
def test_invalid_gate_numeric_fields(bad, field):
    value = document(gate())
    value["gates"][0][field] = bad
    with pytest.raises(ValueError):
        validate_document(value)


@pytest.mark.parametrize("setting", [
    awg(float("nan")), awg(float("inf")), awg(1, ramp=-1), awg(1, ramp=2),
    awg(1, mode="delta"), awg(1, channel=0), awg(1, channel=1.0), awg(1, channel=True),
])
def test_invalid_awg_settings(setting):
    with pytest.raises(ValueError):
        validate_document(document(gate(awg=[setting])))


@pytest.mark.parametrize("change", [
    {"duration_us": 0}, {"duration_us": 2}, {"delay_us": -1}, {"delay_us": .5},
    {"frequency_mhz": -1}, {"frequency_mhz": float("nan")},
    {"phase_deg": float("inf")}, {"gain": 1.0}, {"gain": True}, {"gain": 32768},
])
def test_invalid_rf_settings(change):
    setting = rf()
    setting.update(change)
    with pytest.raises(ValueError):
        validate_document(document(gate(rf=[setting])))


@pytest.mark.parametrize("window", [
    {"delay_us": 0, "duration_us": 0}, {"delay_us": 0, "duration_us": 2},
    {"delay_us": -1, "duration_us": 1}, {"delay_us": 0, "duration_us": math.inf},
])
def test_invalid_acquisition_windows(window):
    with pytest.raises(ValueError):
        validate_document(document(gate(acquisition=window)))


@pytest.mark.parametrize("mutate", [
    lambda value: value.update(version=True),
    lambda value: value.update(version=3),
    lambda value: value.update(shots=1.0),
    lambda value: value.update(shots=0),
    lambda value: value.update(shots=1_000_001),
    lambda value: value.update(extra="bad"),
    lambda value: value["gates"][0].update(qubits=["unknown"]),
    lambda value: value["gates"][0].update(qubits=["q1", "q1"]),
    lambda value: value["gates"][0].update(name=""),
    lambda value: value["gates"][0].update(name="X\nY"),
    lambda value: value["gates"][0].update(unknown=5),
    lambda value: value["gates"].append(gate(start=3)),
    lambda value: value["qubits"].append({"id": "q1", "name": "duplicate"}),
    lambda value: value["awg_baselines"].append({"channel": 1, "voltage_mv": 10}),
    lambda value: value["gates"][0].update(awg=[awg(1), awg(2)]),
])
def test_schema_identity_and_reference_errors(mutate):
    value = document(gate())
    mutate(value)
    with pytest.raises(ValueError):
        validate_document(value)


def test_relative_overflow_is_rejected_during_edit_validation():
    value = document(gate("a", 0, awg=[awg(1e308)]), gate("b", 2, awg=[awg(1e308)]))
    with pytest.raises(ValueError, match="non-finite voltage"):
        validate_document(value)


@pytest.mark.parametrize("start,duration", [(1e308, 1e308), (1e100, 1e-10)])
def test_time_addition_overflow_or_unrepresentable_duration_is_rejected(start, duration):
    with pytest.raises(ValueError, match="end time"):
        validate_document(document(gate(start=start, duration=duration)))


def test_editor_size_bounds():
    value = default_document()
    value["qubits"] = [{"id": str(index), "name": str(index)} for index in range(MAX_QUBITS + 1)]
    with pytest.raises(ValueError, match="Qubits"):
        validate_document(value)
    with pytest.raises(ValueError, match="Gates"):
        validate_document(document(*[gate(str(index), index) for index in range(MAX_GATES + 1)]))
    with pytest.raises(ValueError, match="pulse settings"):
        validate_document(document(*[gate(str(index), index, awg=[awg(0, channel=channel + 1)
            for channel in range(MAX_CHANNEL)]) for index in range(MAX_ACTIONS // MAX_CHANNEL + 1)]))


def test_old_editor_document_without_optional_fields_gains_safe_defaults():
    value = {"version": 1, "qubits": [{"id": "q1", "name": "q1"}],
             "gates": [{"id": "g1", "name": "Idle", "qubits": ["q1"], "start_us": 0, "duration_us": 1}]}
    canonical = validate_document(value)
    assert canonical["shots"] == 1
    assert canonical["awg_baselines"] == []
    assert canonical["gates"][0]["awg"] == []
    assert canonical["gates"][0]["rf"] == []
    assert canonical["gates"][0]["acquisition"] is None
