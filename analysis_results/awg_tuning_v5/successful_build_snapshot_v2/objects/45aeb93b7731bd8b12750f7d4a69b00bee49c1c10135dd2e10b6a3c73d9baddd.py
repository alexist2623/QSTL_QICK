"""Circuit bridge tests use the real compiler; no hardware writes or Verilog."""
from copy import deepcopy
from dataclasses import replace
import json
import numpy as np
import pytest
from qick.sim import QickSim  # PYNQ desktop stubs before driver imports
from qick.qick_asm import QickConfig
from test_qick_fine_tune_sweep import _fir_soccfg, _shared_tmux_soccfg
from dc_waveform_core import QickDdrReadoutSpec, QickRfPulseSpec
from qick_qcodes_experiment import QickConnectionConfig, QcodesRunConfig
from qick_fine_tune_sweep import FineTuneDdrResult
import quantum_circuit_execution as bridge


def config(profile="1_msps"):
    cfg = deepcopy(_fir_soccfg(fir_rate_profile=profile)._cfg)
    pair = deepcopy(_shared_tmux_soccfg()["gens"])
    cfg["gens"] = pair + deepcopy(pair)
    for index, gen in enumerate(cfg["gens"]):
        gen.update(tproc_ch=index // 2, dac=f"{index}0")
        if index % 2 == 0:
            gen.update(revision=6)
        if index % 2:
            gen.update(type="axis_awg_tuning_v3", step_width=32, frac=18,
                       dc_area_version=1, dc_area_bits=48, output_latency_cycles=16,
                       rc_precomp_version=1, dc_start_cycles=17)
    cfg["readouts"][0]["tproc_ctrl"] = 2
    return QickConfig(cfg)


def gate(identifier, start, duration, *, awg=(), rf=(), acquisition=None, qubits=("q1",)):
    return dict(id=identifier, name=identifier, qubits=list(qubits), start_us=start,
                duration_us=duration, awg=list(awg), rf=list(rf), acquisition=acquisition)


def awg(channel=1, value=100, mode="absolute", ramp=0):
    return dict(channel=channel, mode=mode, value_mv=value, ramp_us=ramp)


def rf(delay=1, duration=2, freq=50, gain=1000):
    return dict(channel=1, delay_us=delay, duration_us=duration,
                frequency_mhz=freq, phase_deg=90, gain=gain)


def document():
    return dict(version=1, shots=3, qubits=[dict(id="q1", name="Q1"), dict(id="q2", name="Q2")],
                awg_baselines=[dict(channel=1, voltage_mv=10), dict(channel=2, voltage_mv=-20)],
                gates=[gate("prepare", 0, 10, awg=[awg(value=100), awg(2, -100)],
                            rf=[rf(), rf(5, 2, 70, 2000)]),
                       gate("ramp", 10, 30, awg=[awg(value=20, mode="relative", ramp=5),
                                                awg(2, 50, "relative", 5)],
                            acquisition=dict(delay_us=10, duration_us=20))])


def arguments():
    template = QickRfPulseSpec(gen_ch=0, segment_name="old", delay_us=0, duration_us=1,
                              frequency_mhz=10, gain=99, att1_db=7, att2_db=13,
                              frequency_sweep_enabled=True, frequency_sweep_count=10)
    return dict(readout_template=QickDdrReadoutSpec(ro_ch=0, segment_name="old", delay_us=20,
                                                  samples_per_trigger=8, attenuation_db=17),
                output_full_scales_mv={1:800, 3:400},
                rf_templates=(template,))


def compile_doc(doc=None, cfg=None, **changes):
    kwargs = arguments()
    kwargs.update(changes)
    return bridge.build_circuit_execution(document() if doc is None else doc,
                                          config() if cfg is None else cfg, **kwargs)


@pytest.mark.parametrize("profile", ["1_msps", "50_ksps"])
def test_real_compiler_absolute_relative_simultaneous_ramp_and_multiple_rf(profile):
    doc = document()
    before = deepcopy(doc)
    result = compile_doc(doc, config(profile))
    assert doc == before
    assert result.awg_channels == (1, 3)
    assert result.repetitions_per_sweep == 3
    result.program.compile()
    assert len(result.program.binprog) > 0
    assert result.sequence.sweeps == []
    assert result.sequence.bias_t_compensation is None
    assert result.sequence.rc_compensation is None
    # 100+20 and -100+50, each normalized to its own calibrated full scale.
    points = result.program.compiled_points[0]
    commands = points.segment_commands[-1]
    assert [c.target_code for c in commands] == [4916, -4096]
    origin = result.metadata["circuit_origin_us"]
    # The existing pipeline guard is removed from the following hold.
    ramps = [i for i, s in enumerate(result.sequence.segments) if s.kind == "ramp"]
    assert len(ramps) == 1
    assert result.program.timing["segment_starts"][ramps[0]] / 300 - origin == pytest.approx(10)
    assert result.sequence.segments[ramps[0]].duration_cycles == 1500
    assert result.program.timing["segment_ends"][-1] / 300 - origin == pytest.approx(40)
    assert len(result.rf_specs) == 1
    assert [x.frequency_mhz for x in result.rf_specs[0].pulse_events] == [50, 70]
    assert [x.gain for x in result.rf_specs[0].pulse_events] == [1000, 2000]
    assert all(x.att1_db == 7 and x.att2_db == 13 for x in result.rf_specs)
    assert all(not x.frequency_sweep_enabled for x in result.rf_specs)
    for entry, expected in zip(result.program.aux_timing["rf_pulses"], (1, 5)):
        # RF waveform output occurs after the verified digital generator path,
        # distinct from the earlier RF command timestamp.
        assert (entry["start"] + 42) / 300 - origin == pytest.approx(expected)
        assert (entry["end"] - entry["start"]) / 300 == pytest.approx(2)
    preview = result.program.fir_dc_timing_preview()
    assert preview["group_delay_referenced_input_start_us"] - origin == pytest.approx(20)
    assert preview["group_delay_referenced_input_end_us"] - origin == pytest.approx(40)
    assert result.readout_spec.attenuation_db == 17


def test_legacy_delayed_trigger_and_fpga_override_align_input_start():
    template = replace(arguments()["readout_template"], fpga_trigger_delay_us=2000)
    result = compile_doc(cfg=config("50_ksps"), readout_template=template)
    assert result.metadata["startup_pre_roll_us"] > 900
    actual = result.program.fir_dc_timing_preview()
    assert actual["group_delay_referenced_input_start_us"] - result.metadata["circuit_origin_us"] == pytest.approx(20)


def test_only_rc_compensation_is_carried_without_dc():
    result = compile_doc(compensation={"bias_t_compensation_enabled": True,
                                      "bias_t_compensation_type": "filter",
                                      "bias_t_filter_tau_us": 1000})
    assert result.sequence.rc_compensation.tau_us == 1000
    assert result.sequence.bias_t_compensation is None
    assert not result.program.summary()["hardware_dc_area"]


@pytest.mark.parametrize("mode", ["fixed_time", "fixed_voltage"])
def test_existing_dc_compensation_compiles_in_v3_without_core_changes(mode):
    result = compile_doc(compensation={"bias_t_compensation_enabled": True,
                                      "bias_t_compensation_type": "dc_rc",
                                      "bias_t_compensation_mode": mode,
                                      "bias_t_compensation_voltage_mv": 20,
                                      "bias_t_compensation_duration_us": 100,
                                      "bias_t_filter_tau_us": 1000})
    assert result.program.summary()["hardware_dc_area"]
    assert result.sequence.bias_t_compensation.mode == mode


def test_ramp_at_zero_gets_common_preroll_and_explicit_terminal_hold():
    doc = document()
    doc["gates"] = [gate("ramp", 0, 20, awg=[awg(ramp=20)],
                         acquisition=dict(delay_us=0, duration_us=20))]
    result = compile_doc(doc)
    start = result.program.timing["segment_starts"][1] / 300
    assert start == pytest.approx(result.metadata["circuit_origin_us"])
    assert result.metadata["terminal_hold_extension_us"] == pytest.approx(4 / 300)


@pytest.mark.parametrize("change, match", [
    (lambda d: d["gates"][1].update(acquisition=None), "exactly one"),
    (lambda d: d["gates"][0].update(acquisition=dict(delay_us=0, duration_us=2)), "exactly one"),
    (lambda d: d["gates"][1]["acquisition"].update(duration_us=.5), "whole number"),
    (lambda d: d["gates"][0]["awg"][0].update(value_mv=900), "full scale"),
    (lambda d: d["gates"][0]["awg"][0].update(channel=9), "mapping"),
    (lambda d: d["gates"][0]["rf"][0].update(delay_us=.001), "multiple"),
    (lambda d: d["gates"][1]["awg"][1].update(ramp_us=4), "ramps must share"),
    (lambda d: d["gates"][1]["awg"][1].update(ramp_us=0), "ramps must share"),
])
def test_unsupported_conditions_are_rejected(change, match):
    doc = document()
    change(doc)
    with pytest.raises(ValueError, match=match):
        compile_doc(doc)


def test_short_awg_set_is_rejected_not_stretched():
    doc = document()
    doc["gates"] = [gate("a", 0, 2 / 300, awg=[awg()]),
                    gate("b", 2 / 300, 20, awg=[awg(value=200)],
                         acquisition=dict(delay_us=0, duration_us=20))]
    with pytest.raises(ValueError, match="3-clock"):
        compile_doc(doc)


def test_short_hold_before_ramp_accounts_for_startup_lead():
    doc = document()
    doc["gates"] = [gate("a", 0, 8 / 300, awg=[awg()]),
                    gate("b", 8 / 300, 20, awg=[awg(value=200, ramp=10)],
                         acquisition=dict(delay_us=0, duration_us=20))]
    with pytest.raises(ValueError, match="less than 3 clocks"):
        compile_doc(doc)


def test_shared_awg_ports_are_rejected_instead_of_delayed():
    cfg = config()
    cfg["gens"][3]["tproc_ch"] = 0
    with pytest.raises(ValueError, match="share a tProcessor port"):
        compile_doc(cfg=cfg)


def test_rf_collision_is_rejected_before_execution():
    doc = document()
    # First AWG SET is dispatched 16 clocks before its physical edge.
    doc["gates"][0]["rf"] = []
    doc["gates"][1]["rf"] = [rf((42 - 16) / 300, 3 / 300)]
    doc["gates"][1]["awg"] = [awg(value=20), awg(2, 50)]
    with pytest.raises(ValueError, match="collides"):
        compile_doc(doc)


def test_missing_live_fir_metadata_rejects():
    cfg = config()
    del cfg._cfg["ddr4_buf"]
    with pytest.raises((ValueError, RuntimeError), match="FIR|DDR|HWH"):
        compile_doc(cfg=cfg)


def test_wrong_generator_type_rejects():
    cfg = config()
    cfg["gens"][1].update(type="axis_square_pulse", gen_type="square_pulse")
    with pytest.raises(ValueError, match="not an AWG"):
        compile_doc(cfg=cfg)


def test_template_is_required_and_no_existing_editor_state_is_changed():
    args = arguments()
    before = deepcopy(args)
    compile_doc(**args)
    assert args == before
    with pytest.raises(ValueError, match="Configure RF"):
        compile_doc(rf_templates=())


def test_wrapper_connects_once_precompiles_and_stores_actual_provenance(monkeypatch):
    connections, calls = [], []
    soc, cfg = object(), config()
    def connector(**kwargs):
        connections.append(kwargs)
        return soc, cfg
    sentinel = object()
    def run(**kwargs):
        assert kwargs["connector"]() == (soc, cfg)
        assert kwargs["sequence"].sweeps == []
        calls.append(kwargs)
        return sentinel
    monkeypatch.setattr(bridge.experiment, "run_qick_qcodes_experiment", run)
    settings = dict(awg=dict(outputs=["unrelated"], sweeps=["old"]),
                    qick=dict(tproc_mhz=111, awg_channels=[9], repetitions_per_sweep=17),
                    square_pulse=dict(enabled=True))
    before = deepcopy(settings)
    result = bridge.run_quantum_circuit_experiment(
        document=document(), connection_config=QickConnectionConfig(),
        run_config=object(), gui_settings=settings, connector=connector, **arguments())
    assert result is sentinel and len(connections) == len(calls) == 1
    stored = calls[0]["gui_settings"]
    assert stored["source"] == "quantum_circuit"
    assert stored["editor_snapshot"] == before
    assert stored["qick"]["awg_channels"] == [1, 3]
    assert stored["qick"]["repetitions_per_sweep"] == 3
    assert stored["qick"]["tproc_mhz"] == 300
    assert stored["awg"]["sweeps"] == []
    assert "square_pulse" not in stored
    assert settings == before


def test_wrapper_invalid_circuit_never_calls_runner(monkeypatch):
    monkeypatch.setattr(bridge.experiment, "run_qick_qcodes_experiment",
                        lambda **kwargs: pytest.fail("Hardware runner must not start"))
    doc = document()
    doc["gates"][1]["acquisition"] = None
    with pytest.raises(ValueError, match="exactly one"):
        bridge.run_quantum_circuit_experiment(
            document=doc, connection_config=QickConnectionConfig(), run_config=object(),
            gui_settings={}, connector=lambda **kwargs: (object(), config()), **arguments())


def test_unconfigured_gate_rejects_but_intentional_wait_is_allowed():
    doc = document()
    doc["gates"].append(gate("X", 40, 5))
    with pytest.raises(ValueError, match="has no pulse"):
        compile_doc(doc)
    doc["gates"][-1]["name"] = "Wait"
    assert compile_doc(doc).metadata["circuit_duration_us"] == 45


def test_invalid_storage_mode_rejects_before_connection():
    with pytest.raises(ValueError, match="storage mode"):
        bridge.run_quantum_circuit_experiment(
            document=document(), connection_config=QickConnectionConfig(), run_config=object(),
            gui_settings={}, iq_storage_mode="raw", connector=lambda **kwargs: pytest.fail("connected"),
            **arguments())


def test_duplicate_rf_template_rejects():
    template = arguments()["rf_templates"][0]
    with pytest.raises(ValueError, match="More than one RF template"):
        compile_doc(rf_templates=(template, replace(template, att1_db=20)))


def test_existing_runner_and_real_qcodes_save_with_mock_acquisition(tmp_path, monkeypatch):
    """Only the hardware acquisition boundary is mocked, not the runner/save."""
    monkeypatch.setenv(bridge.experiment.QCODES_STAGING_ENV, str(tmp_path / "staging"))
    cfg = config()
    expected = compile_doc(cfg=cfg)
    connections, acquisitions = [], []
    def connector(**kwargs):
        connections.append(kwargs)
        return object(), cfg
    def execute(soc, soccfg, sequence, **kwargs):
        program = bridge.experiment.build_qick_program(
            soccfg, sequence, awg_channels=kwargs["awg_channels"],
            repetitions_per_sweep=kwargs["repetitions_per_sweep"],
            tproc_mhz=kwargs["tproc_mhz"], rf_specs=kwargs["rf_specs"],
            readout_spec=kwargs["readout_spec"],
            compile_validation_mode=kwargs["compile_validation_mode"])
        program.compile()
        assert program.binprog == expected.program.binprog
        acquisitions.append(program)
        return program, FineTuneDdrResult(
            sweep_points=np.asarray([0.0]), iq=np.zeros((1, 3, 20, 2), dtype=np.int32),
            cross_capacitance=np.eye(2)), {}
    monkeypatch.setattr(bridge.experiment, "execute_qick_sequence", execute)
    result = bridge.run_quantum_circuit_experiment(
        document=document(), connection_config=QickConnectionConfig(),
        run_config=QcodesRunConfig(str(tmp_path / "quantum.db"),
                                  experiment_name="Circuit bridge", sample_name="Mock acquisition"),
        gui_settings={"qick": {"awg_metadata_mode": "parametric"},
                      "awg": {"outputs": ["old waveform"], "sweeps": ["old sweep"]}},
        connector=connector, **arguments())
    assert len(connections) == len(acquisitions) == 1
    assert result.database_path.exists()
    stored = json.loads(result.dataset.get_metadata("qick_experiment_json"))
    assert stored["gui_settings"]["source"] == "quantum_circuit"
    assert stored["gui_settings"]["awg_waveform_recipe"]["point_count"] == 1
    assert stored["gui_settings"]["qick"]["repetitions_per_sweep"] == 3
    assert stored["gui_settings"]["quantum_circuit_execution"]["rf_pulse_count"] == 2
    result.detach_dataset()


def test_cancel_after_live_connection_prevents_runner(monkeypatch):
    connected = []
    def connector(**kwargs):
        connected.append(True)
        return object(), config()
    def cancel():
        if connected:
            raise bridge.experiment.ExperimentCancelled("cancelled")
    monkeypatch.setattr(bridge.experiment, "run_qick_qcodes_experiment",
                        lambda **kwargs: pytest.fail("Hardware runner started after cancellation"))
    with pytest.raises(bridge.experiment.ExperimentCancelled):
        bridge.run_quantum_circuit_experiment(
            document=document(), connection_config=QickConnectionConfig(), run_config=object(),
            gui_settings={}, connector=connector, cancel_check=cancel, **arguments())


def test_periodic_rf_duration_requires_exact_word_boundary():
    doc = document()
    doc["gates"] = [gate("long", 0, 300, awg=[awg()],
                         rf=[rf(1, 65536 / 300)],
                         acquisition=dict(delay_us=0, duration_us=20))]
    with pytest.raises(ValueError, match="periodic-word"):
        compile_doc(doc)
    doc["gates"][0]["rf"][0]["duration_us"] = 65538 / 300
    assert compile_doc(doc).program.aux_timing["rf_pulses"][0]["mode"] == "periodic_timed_stop"


def test_rf_start_at_zero_advances_command_and_extends_common_preroll():
    doc = document()
    doc["gates"][0]["rf"][0]["delay_us"] = 0
    result = compile_doc(doc)
    assert result.metadata["startup_pre_roll_us"] >= 45 / 300
    first = result.program.aux_timing["rf_pulses"][0]
    assert first["start"] / 300 + 42 / 300 == pytest.approx(result.metadata["circuit_origin_us"])


def test_unknown_rf_profile_rejects_unless_explicit_latency_provided():
    cfg = config()
    cfg["gens"][0]["revision"] = 7
    with pytest.raises(ValueError, match="output latency is unknown"):
        compile_doc(cfg=cfg)
    result = compile_doc(cfg=cfg, rf_output_latency_tproc_cycles={0:51})
    assert result.metadata["rf_output_latency_profiles"][0] == "caller_verified_digital_latency"
    first = result.program.aux_timing["rf_pulses"][0]
    assert (first["start"] + 51) / 300 - result.metadata["circuit_origin_us"] == pytest.approx(1)
