"""Named composite delays use host coordinates without changing tProc timing."""
from dataclasses import asdict
from types import SimpleNamespace

import numpy as np
import pytest

import qick.sim  # Desktop bootstrap: these tests never connect to a board.
import awg_sweep_map as sweep_map
import qick_qcodes_experiment as runtime
from acquisition_preview import selected_rf_events
from dc_waveform_core import (
    QickDdrReadoutSpec, QickRfCompositeItemSpec, QickRfDurationParameterSpec,
    QickRfFrequencyParameterSpec, QickRfPulseSpec,
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
