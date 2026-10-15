"""Pure model and generated-code coverage for T2 endpoints and named delays."""

from dataclasses import asdict, replace

import pytest

from dc_waveform_core import (
    PulseSequence,
    QickDdrReadoutSpec,
    QickRfAmplitudeParameterSpec,
    QickRfCompositeItemSpec,
    QickRfDelayParameterSpec,
    QickRfDurationParameterSpec,
    QickRfFrequencyParameterSpec,
    QickRfPhaseParameterSpec,
    QickRfPulseSpec,
    build_qick_sequence,
    generate_qick_program_code,
)


def composite(**changes):
    options = dict(
        gen_ch=0, segment_name="set_0", delay_us=0.1, duration_us=1.0,
        frequency_mhz=50.0, gain=20000, att1_db=0.0, att2_db=0.0,
        pulse_mode="composite", segment_length_mode="extend_by_rf_duration",
        frequency_parameters=(QickRfFrequencyParameterSpec("f0", 50.0),),
        duration_parameters=(QickRfDurationParameterSpec("d0", 0.2),),
        composite_items=(
            QickRfCompositeItemSpec("pulse", "X", 0.2, "f0", duration_parameter="d0"),
            QickRfCompositeItemSpec("delay", "wait", 1.0),
        ),
        predefined_n=2, predefined_tau_us=1.0,
    )
    options.update(changes)
    return QickRfPulseSpec(**options)


@pytest.mark.parametrize("template", ["custom", "cpmg", "udd", "hahn_echo"])
@pytest.mark.parametrize("initial,final", [(False, False), (True, False), (False, True), (True, True)])
def test_t2_endpoints_are_independent_half_width_wrappers(template, initial, final):
    body = composite(predefined_template=template)
    spec = replace(body, t2_initial_pi2=initial, t2_final_pi2=final,
                   t2_initial_phase_degrees=90.0, t2_final_phase_degrees=-90.0)
    assert spec.composite_items == body.composite_items
    assert len(spec.pulse_events) == len(body.pulse_events) + initial + final
    assert spec.segment_extension_duration_us == pytest.approx(
        body.segment_extension_duration_us + 0.1 * (initial + final))
    if initial:
        assert spec.pulse_events[0].name == "T2_initial_pi2"
        assert spec.pulse_events[0].delay_us == pytest.approx(0.1)
        assert spec.pulse_events[0].duration_us == pytest.approx(0.1)
        assert spec.pulse_events[0].phase_degrees == 90.0
    if final:
        assert spec.pulse_events[-1].name == "T2_final_pi2"
        assert spec.pulse_events[-1].duration_us == pytest.approx(0.1)
        assert spec.pulse_events[-1].phase_degrees == -90.0
        assert spec.pulse_events[-1].delay_us == pytest.approx(
            body.segment_extension_duration_us + initial * 0.1)
    restored = QickRfPulseSpec(**asdict(QickRfPulseSpec(**asdict(spec))))
    assert restored == spec
    assert restored.pulse_events == spec.pulse_events
    assert all("" not in event.preceding_duration_parameters for event in spec.pulse_events)


def test_t2_endpoint_names_do_not_collide_with_custom_body_names():
    spec = composite(t2_initial_pi2=True, t2_final_pi2=True, composite_items=(
        QickRfCompositeItemSpec("pulse", "T2_initial_pi2", 0.2, "f0", duration_parameter="d0"),
        QickRfCompositeItemSpec("delay", "T2_final_pi2", 1.0),
    ))
    names = [item.name for item in spec.effective_composite_items]
    assert len(names) == len(set(names))
    assert names[0] == "T2_initial_pi2_2"
    assert names[-1] == "T2_final_pi2_2"


def test_t2_references_are_required_only_when_an_endpoint_is_enabled():
    composite(t2_duration_parameter="unused", t2_frequency_parameter="unused")
    with pytest.raises(ValueError, match="unknown duration parameter"):
        composite(t2_initial_pi2=True, t2_duration_parameter="unused")
    with pytest.raises(ValueError, match="unknown frequency parameter"):
        composite(t2_final_pi2=True, t2_frequency_parameter="unused")


def test_t2_pi_duration_host_sweep_preserves_other_hardware_axes():
    spec = composite(
        t2_initial_pi2=True, t2_final_pi2=True, t2_frequency_parameter="f90",
        frequency_parameters=(QickRfFrequencyParameterSpec("f0", 50.0),
                              QickRfFrequencyParameterSpec("f90", 70.0, True, 70.0, 80.0, 2)),
        duration_parameters=(QickRfDurationParameterSpec("d0", 0.2, True, 0.4, 0.8, 3),
                             QickRfDurationParameterSpec("d1", 0.3, True, 0.3, 0.6, 2)),
        composite_items=(
            QickRfCompositeItemSpec("pulse", "X", 0.2, "f0", duration_parameter="d0"),
            QickRfCompositeItemSpec("pulse", "other", 0.3, "f0", duration_parameter="d1"),
        ),
    )
    assert [(axis.axis_kind, axis.parameter_name) for axis in spec.sweep_axes] == [
        ("rf_duration", "d1"), ("rf_frequency", "f90")]
    assert [(axis.axis_kind, axis.parameter_name) for axis in spec.software_sweep_axes] == [
        ("rf_t2_duration", "d0")]
    assert spec.duration_parameter_reference_counts == (("d1", 1),)
    assert [event.duration_us for event in spec.pulse_events] == pytest.approx([0.2, 0.4, 0.3, 0.2])
    point = spec.with_duration_parameters({"d0": 0.8})
    assert point.software_sweep_axes == ()
    assert point.sweep_axes == spec.sweep_axes
    assert [event.duration_us for event in point.pulse_events] == pytest.approx([0.4, 0.8, 0.3, 0.4])
    assert [event.delay_us for event in point.pulse_events] == pytest.approx([0.1, 0.5, 1.3, 1.6])
    assert point.segment_extension_duration_us == pytest.approx(2.0)


def test_named_delay_sweep_resolves_repeated_references_and_separate_namespace():
    spec = composite(delay_parameters=(
        QickRfDurationParameterSpec("d0", 9.0, True, 1.0, 3.0, 3),
        QickRfDurationParameterSpec("unused", 10.0, True, 2.0, 5.0, 4),
    ), composite_items=(
        QickRfCompositeItemSpec("delay", "lead", 99.0, delay_parameter="d0"),
        QickRfCompositeItemSpec("pulse", "X", 0.2, "f0", duration_parameter="d0"),
        QickRfCompositeItemSpec("delay", "tail", 99.0, delay_parameter="d0"),
    ), t2_final_pi2=True)
    assert [(axis.axis_kind, axis.parameter_name) for axis in spec.software_sweep_axes] == [("rf_delay", "d0")]
    assert spec.sweep_axes == ()
    assert [event.delay_us for event in spec.pulse_events] == pytest.approx([1.1, 2.3])
    point = spec.with_delay_parameters({"d0": 3.0})
    assert [event.delay_us for event in point.pulse_events] == pytest.approx([3.1, 6.3])
    assert point.segment_extension_duration_us == pytest.approx(6.4)
    assert point.duration_parameters == spec.duration_parameters
    assert point.delay_parameters[1].sweep_enabled is True
    assert point.software_sweep_axes == ()
    with pytest.raises(ValueError, match="unknown RF delay"):
        spec.with_delay_parameters({"missing": 1.0})
    with pytest.raises(ValueError, match="nonnegative"):
        spec.with_delay_parameters({"d0": -1.0})


def test_invalid_named_delay_references_fail_before_runtime():
    with pytest.raises(ValueError, match="unknown delay parameter"):
        composite(composite_items=(QickRfCompositeItemSpec("delay", "wait", 1.0, delay_parameter="missing"),),
                  t2_initial_pi2=True)
    with pytest.raises(ValueError, match="only for delays"):
        QickRfCompositeItemSpec("pulse", "X", 0.2, "f0", delay_parameter="tau")
    with pytest.raises(ValueError, match="names must be unique"):
        composite(delay_parameters=(QickRfDurationParameterSpec("tau", 1.0),
                                    QickRfDurationParameterSpec("tau", 2.0)))


def exported(spec, *, with_readout=True):
    source = generate_qick_program_code(
        (PulseSequence(0.0, initial_duration_ns=10000.0),),
        output_names=("awg_0",), awg_channels=(1,), tproc_mhz=300.0,
        rf_pulse_specs=(spec,),
        ddr_readout_spec=QickDdrReadoutSpec(0, "set_0", 0.0, 128, nqz=2) if with_readout else None,
    )
    namespace = {}
    exec(compile(source, "<t2-delay-export>", "exec"), namespace)
    return namespace


@pytest.mark.parametrize("template", ["custom", "cpmg", "udd", "hahn_echo"])
def test_export_preserves_full_rf_model_and_routes_host_sweeps(template):
    spec = composite(
        predefined_template=template, predefined_tau_sweep_enabled=True,
        predefined_tau_sweep_start_us=1.0, predefined_tau_sweep_stop_us=2.0,
        t2_initial_pi2=True, t2_final_pi2=True,
        duration_parameters=(QickRfDurationParameterSpec("d0", 0.2, True, 0.2, 0.4, 2),),
        delay_parameters=(QickRfDurationParameterSpec("tau", 1.0, True, 1.0, 3.0, 3),),
        composite_items=(QickRfCompositeItemSpec("delay", "wait", 1.0, delay_parameter="tau"),),
    )
    namespace = exported(spec)
    assert QickRfPulseSpec(**namespace["RF_CONFIGS"][0]) == spec
    calls = []
    namespace["execute_qick_sequence"] = lambda *args, **kwargs: calls.append((args, kwargs)) or "acquired"
    assert namespace["run_experiment"](object(), {}, progress=False) == "acquired"
    _args, kwargs = calls[0]
    assert kwargs["rf_specs"] == (spec,)
    assert kwargs["awg_channels"] == (1,)
    assert kwargs["readout_spec"].nqz == 2
    assert kwargs["progress"] is False
    assert callable(namespace["build_program"])
    with pytest.raises(ValueError, match="configure_rf=True"):
        namespace["run_experiment"](object(), {}, configure_rf=False)


def test_export_host_sweep_requires_readout_without_hardware_actions():
    namespace = exported(composite(t2_initial_pi2=True,
        duration_parameters=(QickRfDurationParameterSpec("d0", 0.2, True, 0.2, 0.4, 2),)), with_readout=False)
    with pytest.raises(ValueError, match="configured readout"):
        namespace["run_experiment"](object(), {})


def test_hahn_echo_has_one_pi_and_tau_is_total_free_evolution():
    spec = composite(predefined_template="hahn_echo", predefined_n=99,
                     predefined_n_sweep_enabled=True, predefined_tau_us=8.0)
    assert spec.predefined_n == 1
    assert not spec.predefined_n_sweep_enabled
    assert [item.name for item in spec.composite_items] == [
        "Hahn_delay_0", "Hahn_X1", "Hahn_delay_1"]
    assert [item.duration_us for item in spec.composite_items if item.kind == "delay"] == [4.0, 4.0]
    assert len(spec.pulse_events) == 1
    assert spec.pulse_events[0].delay_us == pytest.approx(4.1)
    assert spec.segment_extension_duration_us == pytest.approx(8.3)
    assert spec.software_sweep_axes == ()


def test_hahn_tau_sweep_rebuilds_both_delays_and_retains_independent_endpoints():
    spec = composite(predefined_template="hahn_echo", t2_initial_pi2=True, t2_final_pi2=True,
        predefined_tau_sweep_enabled=True, predefined_tau_sweep_start_us=2.0,
        predefined_tau_sweep_stop_us=6.0, predefined_tau_sweep_count=3)
    axis, = spec.software_sweep_axes
    assert axis.axis_kind == "rf_template_tau"
    assert axis.output_name == "rf_gen_0_hahn_echo_tau"
    for tau in axis.points:
        point = spec.with_predefined_parameters(tau_us=tau)
        assert not point.software_sweep_axes
        assert point.predefined_n == 1
        assert [item.duration_us for item in point.composite_items if item.kind == "delay"] == [tau / 2] * 2
        assert [event.delay_us for event in point.pulse_events] == pytest.approx([
            0.1, 0.2 + tau / 2, 0.4 + tau])
        assert point.segment_extension_duration_us == pytest.approx(0.5 + tau)
        assert QickRfPulseSpec(**asdict(point)) == point


def multitone_composite(**changes):
    options = dict(
        frequency_parameters=(QickRfFrequencyParameterSpec("f0", 50.0, True, 50.0, 60.0, 3),
                              QickRfFrequencyParameterSpec("f1", 70.0, True, 70.0, 80.0, 2)),
        composite_items=(
            QickRfCompositeItemSpec("pulse", "calibrated", 0.2, "f0", gain=1234,
                phase_degrees=30.0, duration_parameter="d0", power_calibration_enabled=True,
                power_calibration_database_path="saved-calibration.db"),
            QickRfCompositeItemSpec("delay", "wait", 1.0),
            QickRfCompositeItemSpec("pulse", "manual", 0.2, "f1", gain=-2345,
                phase_degrees=-60.0, duration_parameter="d0"),
        ),
        t2_initial_pi2=True, t2_final_pi2=True, t2_gain=5678,
    )
    options.update(changes)
    return composite(**options)


def test_legacy_global_sentinels_keep_per_pulse_frequency_gain_and_calibration():
    spec = multitone_composite()
    assert spec.global_frequency_parameter == "" and spec.global_gain is None
    assert [event.frequency_mhz for event in spec.pulse_events] == [50.0, 50.0, 70.0, 50.0]
    assert [event.gain for event in spec.pulse_events] == [5678, 1234, -2345, 5678]
    assert [event.power_calibration_enabled for event in spec.pulse_events] == [False, True, False, False]
    assert QickRfPulseSpec(**asdict(spec)) == spec


def test_explicit_global_settings_override_every_body_and_t2_pulse_without_mutating_rows():
    legacy = multitone_composite()
    spec = replace(legacy, global_frequency_parameter="f1", global_gain=0)
    assert spec.composite_items == legacy.composite_items
    assert {event.frequency_mhz for event in spec.pulse_events} == {70.0}
    assert {event.gain for event in spec.pulse_events} == {0}
    assert not any(event.power_calibration_enabled for event in spec.pulse_events)
    assert [event.phase_degrees for event in spec.pulse_events] == [0.0, 30.0, -60.0, 0.0]
    assert [event.duration_us for event in spec.pulse_events] == [0.1, 0.2, 0.2, 0.1]
    assert spec.composite_items[0].power_calibration_enabled
    assert spec.composite_items[0].power_calibration_database_path == "saved-calibration.db"
    # The saved calibration file is deliberately absent: global raw gain must
    # bypass calibration loading during actual runtime conversion as well.
    runtime = runtime_pulses(spec)
    assert {pulse.gain for pulse in runtime} == {0}
    assert {pulse.freq_mhz for pulse in runtime} == {70.0}
    assert replace(spec, output_board_type="DC_Out").pulse_events == spec.pulse_events
    assert replace(spec, global_frequency_parameter="", global_gain=None) == legacy


def test_global_frequency_sweep_reference_replaces_inactive_local_frequency_axes():
    spec = multitone_composite(global_frequency_parameter="f1")
    assert [(axis.axis_kind, axis.parameter_name) for axis in spec.sweep_axes] == [("rf_frequency", "f1")]
    assert spec.pulse_events[1].power_calibration_enabled  # frequency alone keeps calibration
    assert spec.pulse_events[1].gain == 1234
    with pytest.raises(ValueError, match="global RF frequency.*unknown"):
        replace(spec, global_frequency_parameter="missing")
    with pytest.raises(ValueError, match="global RF gain"):
        replace(spec, global_gain=32768)


def test_global_override_is_valid_without_references_to_inactive_t2_and_template_frequencies():
    spec = composite(predefined_template="hahn_echo", t2_initial_pi2=True, t2_final_pi2=True,
        frequency_parameters=(QickRfFrequencyParameterSpec("global_f", 120.0),),
        global_frequency_parameter="global_f", global_gain=4321)
    assert {event.frequency_mhz for event in spec.pulse_events} == {120.0}
    assert {event.gain for event in spec.pulse_events} == {4321}
    assert QickRfPulseSpec(**exported(spec)["RF_CONFIGS"][0]) == spec


@pytest.mark.parametrize("template", ["cpmg", "udd", "hahn_echo"])
def test_switching_to_custom_keeps_derived_half_duration_and_global_overrides(template):
    original = composite(predefined_template=template, t2_initial_pi2=True, t2_final_pi2=True,
        duration_parameters=(QickRfDurationParameterSpec("d0", 0.2, True, 0.2, 0.6, 3),),
        global_frequency_parameter="f0", global_gain=1111)
    custom = replace(original, predefined_template="custom")
    assert custom.composite_items == original.composite_items
    assert len(custom.effective_composite_items) == len(custom.composite_items) + 2
    assert custom.t2_duration_parameter == "d0"
    for duration in (0.2, 0.4, 0.6):
        events = custom.with_duration_parameters({"d0": duration}).pulse_events
        assert events[0].duration_us == pytest.approx(duration / 2)
        assert events[-1].duration_us == pytest.approx(duration / 2)
        assert all(event.gain == 1111 for event in events)
    assert QickRfPulseSpec(**asdict(custom)) == custom


def runtime_pulses(spec, *, gen_mhz=300.0, tproc_mhz=300.0):
    from qick_qcodes_experiment import build_runtime_rf_pulses
    return build_runtime_rf_pulses(
        {"gens": [{"f_fabric": gen_mhz}], "tprocs": [{"f_time": tproc_mhz}]},
        (spec,),
    )


def test_quantized_t2_overlap_fails_before_a_runtime_program_can_be_built():
    spec = composite(t2_initial_pi2=True, t2_final_pi2=True,
        duration_parameters=(QickRfDurationParameterSpec("d0", 7.5 / 300),),
        composite_items=tuple(QickRfCompositeItemSpec(
            "pulse", f"pi_{index}", 0.1, "f0", duration_parameter="d0")
            for index in range(2)))
    with pytest.raises(ValueError, match="T2_final_pi2.*pi_1.*quantization.*1 tProcessor"):
        runtime_pulses(spec)


def test_quantized_ordinary_composite_overlap_is_also_rejected():
    spec = composite(duration_parameters=(QickRfDurationParameterSpec("d0", 7.5 / 300),),
        composite_items=tuple(QickRfCompositeItemSpec(
            "pulse", f"pi_{index}", 0.1, "f0", duration_parameter="d0")
            for index in range(3)))
    with pytest.raises(ValueError, match="pi_2.*pi_1.*add an inter-pulse delay"):
        runtime_pulses(spec)


def test_clock_aligned_t2_intervals_and_delayed_fractional_widths_are_accepted():
    body = tuple(QickRfCompositeItemSpec(
        "pulse", f"pi_{index}", 0.1, "f0", duration_parameter="d0")
        for index in range(2))
    aligned = composite(t2_initial_pi2=True, t2_final_pi2=True,
        duration_parameters=(QickRfDurationParameterSpec("d0", 8 / 300),),
        composite_items=body)
    assert [(pulse.delay_tproc_cycles, pulse.length_cycles) for pulse in runtime_pulses(aligned)] == [
        (30, 4), (34, 8), (42, 8), (50, 4)]
    delayed = replace(aligned,
        duration_parameters=(QickRfDurationParameterSpec("d0", 7.5 / 300),),
        composite_items=body + (QickRfCompositeItemSpec("delay", "settle", 1 / 300),))
    assert [(pulse.delay_tproc_cycles, pulse.length_cycles) for pulse in runtime_pulses(delayed)] == [
        (30, 4), (34, 8), (42, 8), (50, 4)]


def test_unequal_clock_ratios_accept_exact_touching_and_reject_real_overlap():
    body = tuple(QickRfCompositeItemSpec(
        "pulse", f"pi_{index}", 0.1, "f0", duration_parameter="d0")
        for index in range(2))
    spec = composite(delay_us=0.0, duration_parameters=(QickRfDurationParameterSpec("d0", 0.04),),
                     composite_items=body)
    # Five 125-MHz generator cycles equal exactly twelve 300-MHz tProcessor cycles.
    assert [(pulse.delay_tproc_cycles, pulse.length_cycles) for pulse in runtime_pulses(
        spec, gen_mhz=125.0, tproc_mhz=300.0)] == [(0, 5), (12, 5)]
    assert len(runtime_pulses(spec, gen_mhz=124.99999999999999, tproc_mhz=300.0)) == 2
    overlapping = replace(spec, duration_parameters=(QickRfDurationParameterSpec("d0", 0.025),))
    with pytest.raises(ValueError, match="quantization by 1.6 tProcessor"):
        runtime_pulses(overlapping, gen_mhz=125.0, tproc_mhz=300.0)


def named_controls(**changes):
    options = dict(
        global_amplitude_mode="manual",
        amplitude_parameters=(QickRfAmplitudeParameterSpec("a0", 1200),
                              QickRfAmplitudeParameterSpec("a90", -2400)),
        phase_parameters=(QickRfPhaseParameterSpec("p0", 30.0),
                          QickRfPhaseParameterSpec("p90", 90.0)),
        composite_items=(QickRfCompositeItemSpec("pulse", "X", 0.2, "f0",
            duration_parameter="d0", gain=777, phase_degrees=11.0,
            amplitude_parameter="a0", phase_parameter="p0"),),
        t2_initial_pi2=True, t2_final_pi2=True, t2_amplitude_parameter="a90",
        t2_initial_phase_parameter="p90", t2_final_phase_parameter="p0",
    )
    options.update(changes)
    return composite(**options)


def test_named_manual_amplitude_and_phase_resolve_body_and_t2_without_changing_saved_literals():
    spec = named_controls()
    assert [event.gain for event in spec.pulse_events] == [-2400, 1200, -2400]
    assert [event.phase_degrees for event in spec.pulse_events] == [90.0, 30.0, 30.0]
    assert [event.duration_us for event in spec.pulse_events] == [0.1, 0.2, 0.1]
    assert spec.composite_items[0].gain == 777
    assert spec.composite_items[0].phase_degrees == 11.0
    assert not any(event.power_calibration_enabled for event in spec.pulse_events)
    assert QickRfPulseSpec(**asdict(spec)) == spec


def test_named_calibration_uses_dbm_targets_and_shared_database_for_body_and_t2():
    spec = named_controls(global_amplitude_mode="calibration", global_gain=123,
        global_calibration_database_path="shared.db", global_calibration_run_id=7,
        amplitude_parameters=(QickRfAmplitudeParameterSpec("a0", -19.5),
                              QickRfAmplitudeParameterSpec("a90", -25.25)))
    assert [event.target_output_power_dbm for event in spec.pulse_events] == [-25.25, -19.5, -25.25]
    assert [event.gain for event in spec.pulse_events] == [20000, 777, 20000]
    assert all(event.power_calibration_enabled for event in spec.pulse_events)
    assert {event.power_calibration_database_path for event in spec.pulse_events} == {"shared.db"}
    assert {event.power_calibration_run_id for event in spec.pulse_events} == {7}
    assert not spec.composite_items[0].power_calibration_enabled
    assert QickRfPulseSpec(**asdict(spec)).pulse_events == spec.pulse_events


@pytest.mark.parametrize("mode,value,expected_unit", [("manual", -1000, "gain"), ("calibration", -17.5, "dBm")])
def test_global_amplitude_reference_overrides_all_local_refs_and_sweep_discovery(mode, value, expected_unit):
    spec = named_controls(global_amplitude_mode=mode, global_amplitude_parameter="shared",
        global_calibration_database_path="shared.db",
        amplitude_parameters=(QickRfAmplitudeParameterSpec("shared", value, True, value, value + 4, 3),
                              QickRfAmplitudeParameterSpec("unused", value, True, value, value + 2, 3)))
    axis, = spec.software_sweep_axes
    assert (axis.axis_kind, axis.parameter_name, axis.coordinate_unit) == ("rf_amplitude", "shared", expected_unit)
    assert axis.points.tolist() == [value, value + 2, value + 4]
    point = spec.with_amplitude_parameters({"shared": value + 4})
    assert not point.software_sweep_axes
    assert point.amplitude_parameters[1].sweep_enabled
    values = [event.gain if mode == "manual" else event.target_output_power_dbm for event in point.pulse_events]
    assert values == [value + 4] * 3


def test_named_phase_and_amplitude_sweeps_are_host_axes_and_keep_frequency_duration_axes():
    spec = named_controls(
        amplitude_parameters=(QickRfAmplitudeParameterSpec("a0", 100, True, -2, 3, 4),
                              QickRfAmplitudeParameterSpec("a90", 200)),
        phase_parameters=(QickRfPhaseParameterSpec("p0", 30, True, -90, 450, 4),
                          QickRfPhaseParameterSpec("p90", 90)),
        frequency_parameters=(QickRfFrequencyParameterSpec("f0", 50, True, 50, 60, 2),),
        duration_parameters=(QickRfDurationParameterSpec("d0", 0.2, True, 0.2, 0.4, 2),))
    assert [(axis.axis_kind, axis.parameter_name) for axis in spec.software_sweep_axes] == [
        ("rf_t2_duration", "d0"), ("rf_amplitude", "a0"), ("rf_phase", "p0")]
    assert spec.software_sweep_axes[1].points.tolist() == [-2, 0, 1, 3]
    point = spec.with_amplitude_parameters({"a0": 1}).with_phase_parameters({"p0": 450})
    assert [event.gain for event in point.pulse_events] == [200, 1, 200]
    assert [event.phase_degrees for event in point.pulse_events] == [90, 450, 450]
    assert point.sweep_axes == spec.sweep_axes
    assert [(axis.axis_kind, axis.parameter_name) for axis in point.software_sweep_axes] == [("rf_t2_duration", "d0")]
    assert [event.duration_us for event in point.pulse_events] == [0.1, 0.2, 0.1]


@pytest.mark.parametrize("value", [0.5, -32769, 32768])
def test_manual_named_amplitudes_require_valid_integer_gain_codes(value):
    with pytest.raises(ValueError, match="RF amplitude"):
        named_controls(amplitude_parameters=(QickRfAmplitudeParameterSpec("a0", value),
                                             QickRfAmplitudeParameterSpec("a90", 0)))


def test_named_control_validation_precedes_hardware_execution():
    with pytest.raises(ValueError, match="unique integer gain"):
        named_controls(global_amplitude_parameter="a0", amplitude_parameters=(
            QickRfAmplitudeParameterSpec("a0", 0, True, 0, 1, 3),))
    with pytest.raises(ValueError, match="unknown amplitude"):
        named_controls(global_amplitude_parameter="missing")
    with pytest.raises(ValueError, match="unknown phase"):
        named_controls(t2_final_phase_parameter="missing")
    with pytest.raises(ValueError, match="calibration database"):
        named_controls(global_amplitude_mode="calibration")
    with pytest.raises(ValueError, match="RF_Out"):
        named_controls(global_amplitude_mode="calibration", global_calibration_database_path="x.db", output_board_type="DC_Out")
    with pytest.raises(ValueError, match="manual or calibration"):
        named_controls(global_amplitude_mode="legacy")
    with pytest.raises(ValueError, match="unknown RF amplitude"):
        named_controls().with_amplitude_parameters({"missing": 0})
    with pytest.raises(ValueError, match="unknown RF phase"):
        named_controls().with_phase_parameters({"missing": 0})


def test_named_phase_is_allowed_in_legacy_mode_and_disabled_t2_refs_are_ignored():
    legacy = multitone_composite(t2_initial_pi2=False, t2_final_pi2=False)
    spec = replace(legacy,
        phase_parameters=(QickRfPhaseParameterSpec("p0", -90),),
        composite_items=tuple(replace(item, phase_parameter="p0") if item.kind == "pulse" else item
                              for item in legacy.composite_items),
        t2_amplitude_parameter="unused", t2_initial_phase_parameter="unused", t2_final_phase_parameter="unused")
    assert [event.phase_degrees for event in spec.pulse_events] == [-90, -90]
    assert [event.gain for event in spec.pulse_events] == [1234, -2345]
    assert [event.power_calibration_enabled for event in spec.pulse_events] == [True, False]


@pytest.mark.parametrize("template", ["cpmg", "udd", "hahn_echo"])
def test_presets_regenerate_named_amplitude_and_phase_and_export_host_execution(template):
    spec = named_controls(predefined_template=template,
        predefined_amplitude_parameter="a0", predefined_phase_parameter="p0",
        amplitude_parameters=(QickRfAmplitudeParameterSpec("a0", 100, True, 100, 200, 2),
                              QickRfAmplitudeParameterSpec("a90", 300)))
    point = spec.with_predefined_parameters(tau_us=2).with_amplitude_parameters({"a0": 200})
    assert all(item.amplitude_parameter == "a0" and item.phase_parameter == "p0"
               for item in point.composite_items if item.kind == "pulse")
    assert [event.gain for event in point.pulse_events] == [300] + [200] * point.predefined_n + [300]
    assert replace(point, predefined_template="custom").pulse_events == point.pulse_events
    namespace = exported(spec)
    assert QickRfPulseSpec(**namespace["RF_CONFIGS"][0]) == spec
    calls = []
    namespace["execute_qick_sequence"] = lambda *args, **kwargs: calls.append(kwargs) or "ok"
    assert namespace["run_experiment"](object(), {}) == "ok"
    assert calls[0]["rf_specs"] == (spec,)


def test_named_zero_delay_roundtrip_sweep_and_extension_add_no_clock_cycle():
    spec = composite(delay_us=0, delay_parameters=(QickRfDelayParameterSpec("tau", 0, True, 0, 0.1, 2),),
        composite_items=(QickRfCompositeItemSpec("delay", "wait", 0, delay_parameter="tau"),
                         QickRfCompositeItemSpec("pulse", "X", 0.2, "f0", duration_parameter="d0")))
    assert spec.software_sweep_axes[0].points.tolist() == [0, 0.1]
    assert spec.segment_extension_components_us == (0.2,)
    assert spec.pulse_events[0].delay_us == 0
    assert QickRfPulseSpec(**asdict(spec)) == spec
    assert QickRfPulseSpec(**exported(spec)["RF_CONFIGS"][0]) == spec
    point = spec.with_delay_parameters({"tau": 0.1})
    assert point.pulse_events[0].delay_us == 0.1
    assert point.with_delay_parameters({"tau": 0}).segment_extension_components_us == (0.2,)
    assert runtime_pulses(spec)[0].delay_tproc_cycles == 0
    old = replace(spec, delay_parameters=(QickRfDurationParameterSpec("tau", 0.1),))
    assert old.with_delay_parameters({"tau": 0}).pulse_events == spec.pulse_events
    assert QickRfDelayParameterSpec("tau", 0.1) == QickRfDurationParameterSpec("tau", 0.1)
    with pytest.raises(ValueError, match="duration parameter d0.*positive"):
        composite(duration_parameters=(QickRfDelayParameterSpec("d0", 0),))
