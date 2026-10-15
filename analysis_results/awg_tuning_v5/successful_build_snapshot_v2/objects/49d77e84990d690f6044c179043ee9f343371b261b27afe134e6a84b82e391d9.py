"""Named composite delays use host coordinates without changing tProc timing."""
from dataclasses import asdict
from types import SimpleNamespace

import numpy as np
import pytest

import qick.sim  # Desktop bootstrap: these tests never connect to a board.
import awg_sweep_map as sweep_map
import qick_qcodes_experiment as runtime
from acquisition_preview import calibrated_rf_preview_events, selected_rf_events
from dc_waveform_core import (
    QickDdrReadoutSpec, QickRfCompositeItemSpec, QickRfDurationParameterSpec,
    QickRfFrequencyParameterSpec, QickRfPulseSpec,
    QickRfAmplitudeParameterSpec, QickRfPhaseParameterSpec,
)
from qick_fine_tune_sweep import FineTuneDdrResult, FineTuneSequence
from test_qick_fine_tune_sweep import _shared_tmux_soccfg


def custom_spec(**changes):
    defaults = dict(
        gen_ch=0, segment_name="hold", delay_us=.1, duration_us=.2,
        frequency_mhz=50., gain=1000, att1_db=0., att2_db=0.,
        pulse_mode="composite",
        frequency_parameters=(QickRfFrequencyParameterSpec("f0", 50.),),
        duration_parameters=(QickRfDurationParameterSpec("pi", .2),),
        delay_parameters=(
            QickRfDurationParameterSpec("tau", 1., True, 1., 3., 3),
        ),
        composite_items=(
            QickRfCompositeItemSpec("pulse", "a", .2, "f0", duration_parameter="pi"),
            QickRfCompositeItemSpec("delay", "wait_a", 1., delay_parameter="tau"),
            QickRfCompositeItemSpec("pulse", "b", .2, "f0", duration_parameter="pi"),
            QickRfCompositeItemSpec("delay", "wait_b", 1., delay_parameter="tau"),
            QickRfCompositeItemSpec("pulse", "c", .2, "f0", duration_parameter="pi"),
        ),
    )
    defaults.update(changes)
    return QickRfPulseSpec(**defaults)


def test_shared_tau_resolves_all_references_and_compiles_real_program():
    spec = custom_spec()
    bindings = runtime._rf_software_sweep_bindings((spec,))
    sequence = FineTuneSequence(("awg_0",)).add_set("hold", .01, 6000)
    programs = []
    for coordinate in runtime._software_sweep_coordinates(bindings):
        concrete, = runtime._rf_specs_at_software_coordinate((spec,), bindings, coordinate)
        tau = coordinate[0]
        assert not concrete.software_sweep_axes
        assert [event.delay_us for event in concrete.pulse_events] == pytest.approx(
            [.1, .3 + tau, .5 + 2 * tau])
        pulses = runtime.build_runtime_rf_pulses(_shared_tmux_soccfg(), (concrete,))
        assert [pulse.delay_tproc_cycles for pulse in pulses] == [
            30, round((.3 + tau) * 300), round((.5 + 2 * tau) * 300)]
        program = sequence.make_program(_shared_tmux_soccfg(), awg_channels=(1,),
                                        repetitions_per_sweep=1, rf_pulses=pulses)
        program.compile()
        programs.append(program.asm())
    assert len(programs) == 3
    assert programs[0] != programs[-1]
    assert spec.delay_parameters[0].sweep_enabled


def test_host_tau_cartesian_preserves_hardware_axis_and_combined_coordinates(monkeypatch):
    spec = custom_spec()
    sequence = FineTuneSequence(("awg_0",)).add_set("hold", .01, 6000)
    sequence.add_amplitude_sweep("hold", "awg_0", .01, .02, 2)
    calls = []

    def execute(_soc, _cfg, concrete_sequence, **kwargs):
        concrete, = kwargs["rf_specs"]
        tau = concrete.delay_parameters[0].duration_us
        calls.append(tau)
        assert concrete_sequence.sweep_axes == sequence.sweep_axes
        result = FineTuneDdrResult(
            sweep_points=np.array([.01, .02]),
            iq=np.full((2, 1, 1, 2), round(tau), dtype=np.int32),
            reserved_physical_words=128, sweep_axes=sequence.sweep_axes, sweep_shape=(2,),
        )
        return SimpleNamespace(summary=lambda: {}), result, {"outputs": []}

    monkeypatch.setattr(runtime, "_execute_qick_sequence_once", execute)
    bundle, result, settings = runtime.execute_qick_sequence(
        object(), object(), sequence, awg_channels=(1,), repetitions_per_sweep=1,
        rf_specs=(spec,), readout_spec=QickDdrReadoutSpec(0, "hold", 0., 1))
    assert calls == [1., 2., 3.]
    assert [axis.axis_kind for axis in result.sweep_axes] == ["rf_delay", "amplitude"]
    np.testing.assert_allclose(result.sweep_points, [
        [1., .01], [1., .02], [2., .01], [2., .02], [3., .01], [3., .02]])
    assert result.sweep_shape == (3, 2)
    assert bundle.summary()["software_sweep_program_count"] == 3
    assert settings["software_sweep"]["axes"][0]["parameter_name"] == "tau"
    assert settings["software_sweep"]["coordinates"] == [[1.], [2.], [3.]]


def test_named_tau_changes_segment_extension_and_selected_preview():
    spec = custom_spec(segment_length_mode="extend_by_rf_duration")
    sequence = FineTuneSequence(("awg_0",)).add_set("hold", .01, 300)
    resolved = spec.with_delay_parameters({"tau": 3.})
    concrete = runtime._sequence_at_rf_software_coordinate(sequence, (resolved,), fabric_mhz=300.)
    assert concrete.segment_duration_cycles_at(0, 0) == 300 + round(6.7 * 300)
    selected = selected_rf_events(concrete, 0, spec, 300., software_values={("rf_delay", "tau"): 3.})
    assert [start for _event, start, _end in selected] == pytest.approx([.1, 3.3, 6.5])
    assert sequence.segment_duration_cycles_at(0, 0) == 300


def test_t2_pi_sweep_resolves_half_width_endpoints_without_hardware_axis():
    spec = custom_spec(
        duration_parameters=(QickRfDurationParameterSpec("pi", .2, True, .2, .4, 2),),
        t2_initial_pi2=True, t2_final_pi2=True, t2_duration_parameter="pi",
        t2_frequency_parameter="f0", t2_initial_phase_degrees=90., t2_final_phase_degrees=-90.)
    bindings = runtime._rf_software_sweep_bindings((spec,))
    assert [axis.axis_kind for _index, axis in bindings] == ["rf_delay", "rf_t2_duration"]
    assert not spec.sweep_axes
    assert runtime._software_sweep_coordinates(bindings).shape == (6, 2)
    sequence = FineTuneSequence(("awg_0",)).add_set("hold", .01, 6000)
    for tau, pi in runtime._software_sweep_coordinates(bindings):
        concrete, = runtime._rf_specs_at_software_coordinate((spec,), bindings, (tau, pi))
        assert not concrete.sweep_axes and not concrete.software_sweep_axes
        events = concrete.pulse_events
        assert [event.duration_us for event in events] == pytest.approx([pi / 2, pi, pi, pi, pi / 2])
        assert [event.phase_degrees for event in (events[0], events[-1])] == [90., -90.]
        assert events[-1].delay_us == pytest.approx(.1 + 3.5 * pi + 2 * tau)
        pulses = runtime.build_runtime_rf_pulses(_shared_tmux_soccfg(), (concrete,))
        assert [pulses[0].length_cycles, pulses[-1].length_cycles] == [round(pi * 150)] * 2
        program = sequence.make_program(_shared_tmux_soccfg(), awg_channels=(1,),
                                        repetitions_per_sweep=1, rf_pulses=pulses)
        program.compile()
        preview = selected_rf_events(sequence, 0, spec, 300., software_values={
            ("rf_delay", "tau"): tau, ("rf_t2_duration", "pi"): pi})
        assert [event.duration_us for event, _start, _end in preview] == pytest.approx(
            [pi / 2, pi, pi, pi, pi / 2])


def test_tau_axis_metadata_and_map_keep_microseconds(tmp_path):
    axis, = custom_spec().software_sweep_axes
    assert runtime._sweep_parameter_names((axis,)) == ("rf_gen_0_tau_delay_hold_delay_us",)
    assert runtime._sweep_axis_display(axis, 800.) == ("RF delay tau", "us", 1.)
    assert "all references share" in runtime._sweep_axis_meaning(axis)
    assert sweep_map.sweep_axis_label(axis).endswith("RF delay tau")
    values, unit = sweep_map._axis_display_values(np.array([1., 3.]), axis, 800.)
    np.testing.assert_allclose(values, [1., 3.])
    assert unit == "us"
    stored = dict(asdict(axis), unit="ns")
    np.testing.assert_allclose(sweep_map._stored_axis_native_values(
        [1000., 3000.], stored, full_scale_mv=800.), [1., 3.])
    assert sweep_map._stored_axis_label(stored) == sweep_map.sweep_axis_label(axis)
    result = FineTuneDdrResult(sweep_points=np.array([1., 2., 3.]),
        iq=np.ones((3, 1, 1, 2), dtype=np.int32), reserved_physical_words=128,
        sweep_axes=(axis,), sweep_shape=(3,))
    dataset, rows = runtime.store_qick_result(
        result, run_config=runtime.QcodesRunConfig(str(tmp_path / "tau.db")),
        connection_config=runtime.QickConnectionConfig("not-connected", 8888, "qick"),
        program_summary={}, gui_settings={"rf_outputs": [asdict(custom_spec())]}, rf_settings={})
    import json
    metadata = json.loads(dataset.get_metadata("qick_experiment_json"))
    stored_axis, = metadata["measurement_layout"]["sweep_axes"]
    assert rows == 3
    assert stored_axis["axis_kind"] == "rf_delay"
    assert stored_axis["parameter_name"] == "tau"
    assert stored_axis["unit"] == "us"
    assert "host software sweep" in stored_axis["execution"]
    assert metadata["gui_settings"]["rf_outputs"][0]["delay_parameters"][0]["name"] == "tau"
    dataset.conn.close()


def test_saved_two_dimensional_tau_map_restores_parameter_names(tmp_path):
    tau = custom_spec().software_sweep_axes[0]
    axes = [dict(asdict(tau), parameter="tau_values", unit="us"),
            dict(asdict(tau), parameter="other_values", output_name="rf_other",
                 parameter_name="idle", start=4., stop=5., count=2, unit="us")]
    coordinates = np.array([[tau, other] for tau in (1., 2., 3.) for other in (4., 5.)])
    result = sweep_map.awg_sweep_result_from_stored_arrays({
        "metadata": {"gui_settings": {}, "measurement_layout": {
            "sweep_axes": axes, "sample_rate_hz": 1e6}},
        "iq": np.ones((6, 1, 1, 2), dtype=np.int32),
        "iq_unit": "ADC units", "measurement_mode": "raw_iq",
        "sweep_coordinates": {"tau_values": coordinates[:, 0, None],
                              "other_values": coordinates[:, 1, None]},
    }, database_path=tmp_path / "restored.db", run_id=1)
    assert {result.x_axis_label, result.y_axis_label} == {
        "rf_gen_0_tau_delay / hold RF delay tau", "rf_other / hold RF delay idle"}
    assert result.x_unit == result.y_unit == "us"


def named_amplitude_phase_spec(**changes):
    defaults = dict(delay_parameters=(),
        composite_items=(QickRfCompositeItemSpec("pulse", "pi", .2, "f0",
            duration_parameter="pi", amplitude_parameter="a0", phase_parameter="p0"),),
        amplitude_parameters=(QickRfAmplitudeParameterSpec("a0", 1000., True, 1000., 2000., 2),),
        phase_parameters=(QickRfPhaseParameterSpec("p0", 0., True, 0., 90., 2),),
        global_amplitude_mode="manual", global_amplitude_parameter="a0",
        t2_initial_pi2=True, t2_final_pi2=True, t2_duration_parameter="pi",
        t2_frequency_parameter="f0", t2_amplitude_parameter="a0",
        t2_initial_phase_parameter="p0", t2_final_phase_parameter="p0")
    defaults.update(changes)
    return custom_spec(**defaults)


def test_named_amplitude_phase_host_points_compile_body_and_both_t2_endpoints():
    spec = named_amplitude_phase_spec()
    bindings = runtime._rf_software_sweep_bindings((spec,))
    assert [axis.axis_kind for _, axis in bindings] == ["rf_amplitude", "rf_phase"]
    sequence = FineTuneSequence(("awg_0",)).add_set("hold", .01, 6000)
    for gain, phase in runtime._software_sweep_coordinates(bindings):
        concrete, = runtime._rf_specs_at_software_coordinate((spec,), bindings, (gain, phase))
        assert not concrete.software_sweep_axes
        assert [event.gain for event in concrete.pulse_events] == [int(gain)] * 3
        assert [event.phase_degrees for event in concrete.pulse_events] == [phase] * 3
        assert [event.duration_us for event in concrete.pulse_events] == pytest.approx([.1, .2, .1])
        pulses = runtime.build_runtime_rf_pulses(_shared_tmux_soccfg(), (concrete,))
        assert [pulse.gain for pulse in pulses] == [int(gain)] * 3
        assert [pulse.phase_degrees for pulse in pulses] == [phase] * 3
        program = sequence.make_program(_shared_tmux_soccfg(), awg_channels=(1,),
                                        repetitions_per_sweep=1, rf_pulses=pulses)
        program.compile()
        preview = selected_rf_events(sequence, 0, spec, 300., software_values={
            ("rf_amplitude", "a0"): gain, ("rf_phase", "p0"): phase})
        assert [event.gain for event, _, _ in preview] == [int(gain)] * 3
        assert [event.phase_degrees for event, _, _ in preview] == [phase] * 3


def test_calibrated_named_amplitude_uses_known_database_and_shared_phase(tmp_path):
    import json
    import sqlite3
    from test_power_calibration import _calibration_database
    path = tmp_path / "known_calibration.db"
    _calibration_database(path)
    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE runs ADD COLUMN Calibration_Config TEXT")
        connection.execute("UPDATE runs SET Calibration_Config = ? WHERE run_id = 1", (json.dumps({
            "configuration": {"nqz": 1, "output_filter_type": "bypass",
                              "output_filter_cutoff_ghz": 2.5, "output_filter_bandwidth_ghz": 1.0}}),))
    spec = named_amplitude_phase_spec(
        frequency_parameters=(QickRfFrequencyParameterSpec("f0", 180.),),
        amplitude_parameters=(QickRfAmplitudeParameterSpec("a0", -30., True, -30., -10., 2),),
        global_amplitude_mode="calibration", global_calibration_database_path=str(path),
        global_calibration_run_id=1)
    bindings = runtime._rf_software_sweep_bindings((spec,))
    assert bindings[0][1].coordinate_unit == "dBm"
    sequence = FineTuneSequence(("awg_0",)).add_set("hold", .01, 6000)
    for power, phase in runtime._software_sweep_coordinates(bindings):
        concrete, = runtime._rf_specs_at_software_coordinate((spec,), bindings, (power, phase))
        assert all(event.power_calibration_enabled for event in concrete.pulse_events)
        assert [event.target_output_power_dbm for event in concrete.pulse_events] == [power] * 3
        pulses = runtime.build_runtime_rf_pulses(_shared_tmux_soccfg(), (concrete,))
        # The independent fixture has 100 codes at -30 dBm and 1000 at -10 dBm,
        # at 180 MHz with zero attenuation. No production conversion is used
        # to calculate these expected integer gains.
        assert [pulse.gain for pulse in pulses] == [{-30.: 100, -10.: 1000}[power]] * 3
        assert [pulse.phase_degrees for pulse in pulses] == [phase] * 3
        assert [pulse.power_calibration_run_id for pulse in pulses] == [1] * 3
        selected = selected_rf_events(sequence, 0, concrete, 300.)
        preview = calibrated_rf_preview_events(concrete, selected)
        assert [event.gain for event, _, _ in preview] == [{-30.: 100, -10.: 1000}[power]] * 3
        assert [event.target_output_power_dbm for event, _, _ in preview] == [power] * 3
        assert [event.power_calibration_database_path for event, _, _ in preview] == [str(path)] * 3
        assert [(start, end) for _, start, end in preview] == [(start, end) for _, start, end in selected]
        program = sequence.make_program(_shared_tmux_soccfg(), awg_channels=(1,),
                                        repetitions_per_sweep=1, rf_pulses=pulses)
        program.compile()


def test_named_amplitude_phase_host_product_preserves_existing_hardware_sweep(monkeypatch):
    spec = named_amplitude_phase_spec()
    sequence = FineTuneSequence(("awg_0",)).add_set("hold", .01, 6000)
    sequence.add_amplitude_sweep("hold", "awg_0", .01, .02, 2)
    calls = []

    def execute(_soc, _cfg, concrete_sequence, **kwargs):
        concrete, = kwargs["rf_specs"]
        gain = concrete.pulse_events[0].gain
        phase = concrete.pulse_events[0].phase_degrees
        calls.append((gain, phase))
        assert all(event.gain == gain and event.phase_degrees == phase
                   for event in concrete.pulse_events)
        assert concrete_sequence.sweep_axes == sequence.sweep_axes
        result = FineTuneDdrResult(sweep_points=np.array([.01, .02]),
            iq=np.full((2, 1, 1, 2), gain, dtype=np.int32), reserved_physical_words=128,
            sweep_axes=sequence.sweep_axes, sweep_shape=(2,))
        return SimpleNamespace(summary=lambda: {}), result, {"outputs": []}

    monkeypatch.setattr(runtime, "_execute_qick_sequence_once", execute)
    bundle, result, settings = runtime.execute_qick_sequence(
        object(), object(), sequence, awg_channels=(1,), repetitions_per_sweep=1,
        rf_specs=(spec,), readout_spec=QickDdrReadoutSpec(0, "hold", 0., 1))
    assert calls == [(1000, 0.), (1000, 90.), (2000, 0.), (2000, 90.)]
    assert [axis.axis_kind for axis in result.sweep_axes] == ["rf_amplitude", "rf_phase", "amplitude"]
    np.testing.assert_allclose(result.sweep_points,
        [[gain, phase, awg] for gain, phase in calls for awg in (.01, .02)])
    assert result.sweep_shape == (2, 2, 2)
    assert bundle.summary()["software_sweep_program_count"] == 4
    assert [axis["parameter_name"] for axis in settings["software_sweep"]["axes"]] == ["a0", "p0"]


def test_calibrated_preview_rejects_missing_database_instead_of_using_manual_gain(tmp_path):
    spec = named_amplitude_phase_spec(global_amplitude_mode="calibration",
        amplitude_parameters=(QickRfAmplitudeParameterSpec("a0", -10.),),
        global_calibration_database_path=str(tmp_path / "absent.db"))
    sequence = FineTuneSequence(("awg_0",)).add_set("hold", .01, 6000)
    selected = selected_rf_events(sequence, 0, spec, 300.)
    with pytest.raises(ValueError, match="RF preview calibration failed"):
        calibrated_rf_preview_events(spec, selected)


def test_named_calibration_keeps_v4_summed_output_rejection():
    spec = named_amplitude_phase_spec(global_amplitude_mode="calibration",
        amplitude_parameters=(QickRfAmplitudeParameterSpec("a0", -10.),),
        global_calibration_database_path="synthetic_not_needed.db")
    cfg = _shared_tmux_soccfg()
    cfg["gens"][0]["output_sum_role"] = "rf"
    with pytest.raises(ValueError, match="RF connector power calibration cannot be used"):
        runtime.build_runtime_rf_pulses(cfg, (spec,))


def test_calibrated_preview_auto_run_uses_full_frequency_sweep_like_execution(tmp_path):
    import json
    import sqlite3
    from test_power_calibration import _calibration_database
    path = tmp_path / "two_coverage_runs.db"
    _calibration_database(path)
    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE runs ADD COLUMN Calibration_Config TEXT")
        connection.execute("INSERT INTO experiments VALUES (5, 'new narrow calibration', 'RF_Out_200MHz')")
        connection.execute("INSERT INTO runs VALUES (5, 5, 'narrow', 1, ?, NULL)",
                           (json.dumps({"att1": 0, "att2": 0}),))
        connection.execute("INSERT INTO layouts VALUES (5, 5, 'freq', 'freq', 'MHz', '')")
        connection.execute('CREATE TABLE narrow AS SELECT id,gain,freq,pwr+10 AS pwr FROM "results-1-1" WHERE freq=200')
        metadata = json.dumps({"configuration": {"nqz": 1, "output_filter_type": "bypass",
            "output_filter_cutoff_ghz": 2.5, "output_filter_bandwidth_ghz": 1.0}})
        connection.execute("UPDATE runs SET Calibration_Config=? WHERE run_id IN (1,5)", (metadata,))
    spec = named_amplitude_phase_spec(global_amplitude_mode="calibration",
        global_calibration_database_path=str(path), global_calibration_run_id=0,
        frequency_parameters=(QickRfFrequencyParameterSpec("f0", 180., True, 180., 220., 3),),
        amplitude_parameters=(QickRfAmplitudeParameterSpec("a0", -10.),),
        phase_parameters=(QickRfPhaseParameterSpec("p0", 0.),))
    sequence = FineTuneSequence(("awg_0",)).add_set("hold", .01, 6000)
    sequence.add_rf_frequency_sweep("hold", 0, 180., 220., 3, parameter_name="f0")
    pulses = runtime.build_runtime_rf_pulses(_shared_tmux_soccfg(), (spec,))
    assert [pulse.power_calibration_run_id for pulse in pulses] == [1] * 3
    assert pulses[0].sweep_gain_codes == (1000, 977, 955)
    selected = selected_rf_events(sequence, 1, spec, 300.)
    assert all(event.frequency_mhz == 200. for event, _, _ in selected)
    preview = calibrated_rf_preview_events(spec, selected)
    assert [event.gain for event, _, _ in preview] == [977] * 3


@pytest.mark.parametrize("mode,unit,values", [("manual", "gain", (1000., 2000.)),
                                              ("calibration", "dBm", (-30., -10.))])
def test_named_amplitude_phase_metadata_and_saved_map_preserve_units(tmp_path, mode, unit, values):
    spec = named_amplitude_phase_spec(global_amplitude_mode=mode,
        global_calibration_database_path="fixture.db" if mode == "calibration" else "",
        amplitude_parameters=(QickRfAmplitudeParameterSpec("a0", values[0], True, *values, 2),))
    amplitude, phase = spec.software_sweep_axes
    assert runtime._sweep_axis_display(amplitude, 800.)[1:] == (unit, 1.)
    assert runtime._sweep_axis_display(phase, 800.)[1:] == ("deg", 1.)
    assert "host software run" in runtime._sweep_axis_meaning(amplitude)
    assert "time-referenced carrier" in runtime._sweep_axis_meaning(phase)
    suffix = "output_power_dbm" if mode == "calibration" else "gain"
    assert runtime._sweep_parameter_names((amplitude, phase))[0].endswith(suffix)
    coordinates = np.asarray([[amp, ph] for amp in values for ph in (0., 90.)])
    result = FineTuneDdrResult(sweep_points=coordinates,
        iq=np.ones((4, 1, 1, 2), dtype=np.int32), reserved_physical_words=128,
        sweep_axes=(amplitude, phase), sweep_shape=(2, 2))
    dataset, rows = runtime.store_qick_result(result,
        run_config=runtime.QcodesRunConfig(str(tmp_path / "named.db")),
        connection_config=runtime.QickConnectionConfig("not-connected", 8888, "qick"),
        program_summary={}, gui_settings={"rf_outputs": [asdict(spec)]}, rf_settings={})
    import json
    metadata = json.loads(dataset.get_metadata("qick_experiment_json"))
    axes = metadata["measurement_layout"]["sweep_axes"]
    assert rows == 4
    assert [axis["parameter_name"] for axis in axes] == ["a0", "p0"]
    assert [axis["unit"] for axis in axes] == [unit, "deg"]
    restored = sweep_map.awg_sweep_result_from_stored_arrays({
        "metadata": metadata, "iq": result.iq, "iq_unit": "ADC units",
        "measurement_mode": "raw_iq", "sweep_coordinates": {
            axis["parameter"]: coordinates[:, index, None] for index, axis in enumerate(axes)}},
        database_path=tmp_path / "named.db", run_id=dataset.run_id)
    assert {restored.x_unit, restored.y_unit} == {unit, "deg"}
    assert "a0" in restored.x_axis_label + restored.y_axis_label
    assert "p0" in restored.x_axis_label + restored.y_axis_label
    dataset.conn.close()
