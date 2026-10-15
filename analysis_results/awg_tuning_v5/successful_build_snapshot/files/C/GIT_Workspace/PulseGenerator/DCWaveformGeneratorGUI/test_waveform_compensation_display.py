"""Live channel editing limits and independent compensation display controls."""
from dataclasses import replace

import numpy as np
import pytest

from qick_waveform_preview import rc_precompensated_vertices
from test_square_awg_exclusion import window, firmware
from test_dac_current import records
from dc_waveform_core import QickSweepSpec, QickHoldDurationSweepSpec, QickRampRateSweepSpec, QickRfPulseSpec


def test_rc_integrates_steps_zero_holds_and_balanced_dc_pulse():
    # 100 mV for 100 us; wait at zero for 50 us; -50 mV for 200 us.
    t = np.array([0, 100, 100, 150, 150, 350, 350]) * 1000.
    values = np.array([[100, 100, 0, 0, -50, -50, 0.]])
    times, actual = rc_precompensated_vertices(t, values, 300)
    np.testing.assert_array_equal(times, t)
    np.testing.assert_allclose(actual[0], [100, 100+100/3, 100/3, 100/3,
                                         -50+100/3, -50, 0], atol=1e-12)


def test_rc_ramp_is_quadratic_and_includes_interior_extrema():
    times, result = rc_precompensated_vertices([0, 20000], [[100, -100]], 10)
    us = times / 1000
    np.testing.assert_allclose(result[0], 100 - 10*us + (100*us-5*us**2)/10)
    assert len(times) <= 34
    # A second slope puts an extremum inside the ramp at 5 us.
    times, result = rc_precompensated_vertices([0, 20000], [[150, -50]], 10, 4)
    assert 5000 in times
    assert max(result[0]) == pytest.approx(162.5)


def test_preview_bounded_memory_for_long_hold_and_independent_channels():
    times, result = rc_precompensated_vertices([0, 1e12], [[1, 1], [-2, -2]], 1e6)
    assert len(times) == 2
    np.testing.assert_allclose(result[:, -1], [1001, -2002])


@pytest.mark.parametrize('tau', [0, -1, float('nan'), float('inf')])
def test_invalid_tau_rejected(tau):
    with pytest.raises(ValueError):
        rc_precompensated_vertices([0, 10], [[1, 1]], tau)


def test_editor_limits_follow_current_channel_remapping_and_added_ports(window):
    window._on_qick_configuration_identified(replace(
        firmware(), dac_current_settings=records((32000, 10000, 20000))))
    assert window._pulse[0].v_bounds == (-1280, 1280)
    # Use the real editor model, not direct array assignment (the old bug).
    window._pulse[0].edit_voltage(0, 1000)
    assert window._pulse[0].v[0] == 1000
    seq = window._experiment_run_arguments(require_readout=False, require_run_config=False)['sequence']
    assert seq.amplitudes_at(0, 0)[0] == pytest.approx(1000/1280)
    window._add_port()
    assert window._pulse[1].v_bounds == (-400, 400)
    window._set_awg_output_channel(0, 3)
    assert window._pulse[0].v_bounds == (-400, 400)
    assert window._pulse[1].v_bounds == (-1280, 1280)
    assert window._pulse[0].v[0] == 1000  # Never silently rewrite existing volts.
    window._pulse[0].edit_voltage(0, 300)
    window._pulse[1].edit_voltage(0, -1000)
    assert window._pulse[1].v[0] == -1000
    assert 'gen 3: +/-400 mV' in window._waveform_scale_label.text()
    assert 'gen 1: +/-1280 mV' in window._waveform_scale_label.text()


def configure_compensated_pulse(window):
    window._pulse[0].t = np.array([0., 100000.])
    window._pulse[0].v = np.array([100., 100.])
    panel = window._experiment_panel
    panel.bias_t_compensation_mv.setValue(100)
    panel.bias_t_filter_tau_us.setValue(300)
    panel.bias_t_type.dc_checkbox.setChecked(True)
    panel.bias_t_type.rc_checkbox.setChecked(True)
    window._refresh_physical_waveforms(fit_view=True)


def test_display_switches_do_not_change_rc_history_or_experiment(window):
    configure_compensated_pulse(window)
    plot = window._plot
    assert plot._physical_time_ns[-1] > 200000
    assert np.max(plot._rc_values_mv) == pytest.approx(100+100/3)
    assert plot._rc_values_mv[0, -1] == pytest.approx(0, abs=1e-10)
    original = plot._rc_values_mv.copy()
    args_before = window._experiment_run_arguments(require_readout=False, require_run_config=False)
    window._show_dc_compensation.setChecked(False)
    assert plot._physical_time_ns[-1] == 100000
    np.testing.assert_array_equal(plot._rc_values_mv, original)
    window._show_rc_compensation.setChecked(False)
    assert not plot._rc_time_ns.size
    assert all(not curve.isVisible() for curve in plot._rc_line)
    args_after = window._experiment_run_arguments(require_readout=False, require_run_config=False)
    assert args_after['sequence'].bias_t_compensation == args_before['sequence'].bias_t_compensation
    assert args_after['sequence'].rc_compensation == args_before['sequence'].rc_compensation
    window._show_rc_compensation.setChecked(True)
    np.testing.assert_array_equal(plot._rc_values_mv, original)
    window._experiment_panel.bias_t_type.rc_checkbox.setChecked(False)
    assert not plot._rc_time_ns.size


def test_out_of_range_rc_still_plotted_but_execution_is_rejected(window):
    configure_compensated_pulse(window)
    window._experiment_panel.bias_t_filter_tau_us.setValue(10)
    assert np.max(window._plot._rc_values_mv) > 800
    assert 'exceeds range' in window._waveform_preview_note.text()
    with pytest.raises(ValueError, match='RC-compensated DAC output exceeds range'):
        window._experiment_run_arguments(require_readout=False, require_run_config=False)


def test_display_settings_roundtrip_and_stale_file_bounds(window):
    configure_compensated_pulse(window)
    window._on_qick_configuration_identified(replace(
        firmware(), dac_current_settings=records((32000, 10000, 20000))))
    window._show_dc_compensation.setChecked(False)
    window._show_rc_compensation.setChecked(False)
    data = window._settings_to_dict()
    data['awg']['outputs'][0]['voltage_bounds_mv'] = [-800, 800]
    window._apply_decoded_settings(window._decode_settings(data))
    assert window._pulse[0].v_bounds == (-1280, 1280)
    assert not window._show_dc_compensation.isChecked()
    assert not window._show_rc_compensation.isChecked()
    assert window._experiment_panel.bias_t_type.dc_checkbox.isChecked()
    assert window._experiment_panel.bias_t_type.rc_checkbox.isChecked()
    del data['display']['show_dc_compensation']
    del data['display']['show_rc_compensation']
    legacy = window._decode_settings(data)
    assert legacy['show_dc_compensation'] and legacy['show_rc_compensation']


def test_two_channel_rc_preview_preserves_voltage_when_current_changes(window):
    window._add_port()
    for pulse, level in zip(window._pulse, (100., -50.)):
        pulse.t = np.array([0., 100000.])
        pulse.v = np.array([level, level])
    window._cross_capacitance = np.array([[1., .2], [-.1, 1.]])
    panel = window._experiment_panel
    panel.bias_t_compensation_mv.setValue(100)
    panel.bias_t_filter_tau_us.setValue(300)
    panel.bias_t_type.dc_checkbox.setChecked(True)
    panel.bias_t_type.rc_checkbox.setChecked(True)
    window._refresh_physical_waveforms()
    before_t = window._plot._rc_time_ns.copy()
    before_v = window._plot._rc_values_mv.copy()
    np.testing.assert_allclose(before_v[:, 0], [90, -60])
    window._on_qick_configuration_identified(replace(
        firmware(), dac_current_settings=records((32000, 10000, 20000))))
    np.testing.assert_array_equal(window._plot._rc_time_ns, before_t)
    np.testing.assert_allclose(window._plot._rc_values_mv, before_v, atol=1e-12)
    window._set_voltage_view('virtual')
    assert all(not curve.isVisible() for curve in window._plot._rc_line)
    window._set_voltage_view('physical')
    assert all(curve.isVisible() for curve in window._plot._rc_line)


def test_rc_curve_auto_fit_and_port_deletion(window):
    configure_compensated_pulse(window)
    window._add_port()
    assert len(window._plot._rc_line) == 2
    window._delete_port(1)
    assert len(window._plot._rc_line) == 1
    window._plot.fit_view()
    assert window._plot.getViewBox().viewRange()[1][1] > np.max(window._plot._rc_values_mv)


@pytest.mark.parametrize('dc,rc', [(False, False), (True, False), (False, True), (True, True)])
def test_virtual_physical_rc_use_one_selected_sweep_point(window, dc, rc):
    window._add_port()
    for pulse, level in zip(window._pulse, (200., 50.)):
        pulse.t = np.array([0., 100000.])
        pulse.v = np.array([level, level])
    before = [p.v.copy() for p in window._pulse]
    window._cross_capacitance = np.array([[1., .2], [-.1, 1.]])
    window._sweep_specs = [
        QickSweepSpec('set_0', 'awg_0', -200/800, -100/800, 3),
        QickSweepSpec('set_0', 'awg_1', 10/800, 30/800, 3)]
    panel = window._experiment_panel
    panel.bias_t_compensation_mv.setValue(100)
    panel.bias_t_filter_tau_us.setValue(300)
    panel.bias_t_type.dc_checkbox.setChecked(dc)
    panel.bias_t_type.rc_checkbox.setChecked(rc)
    window._refresh_sweep_overlay()
    assert window._waveform_point_index.maximum() == 8
    for point, target in [(0, [-200, 10]), (4, [-150, 20]), (8, [-100, 30])]:
        window._waveform_point_index.setValue(point)
        seq = window._waveform_preview_sequence
        virtual = np.array([line.yData[0] for line in window._plot._line])
        np.testing.assert_allclose(virtual, target)
        np.testing.assert_allclose(window._plot._physical_values_mv[:, 0],
                                   window._cross_capacitance @ virtual)
        assert f'Point {point}:' in window._waveform_preview_note.text()
        if rc:
            cycles, values, _ = seq.compensated_waveform_vertices(point)
            physical = np.vstack([values[n] for n in seq.output_names]) * np.array(seq.output_full_scales_mv)[:, None]
            times = cycles * 1000 / window._qick_fabric_mhz
            if np.any(physical[:, -1]):
                times = np.append(times, times[-1])
                physical = np.column_stack((physical, np.zeros(2)))
            expected_t, expected_v = rc_precompensated_vertices(times, physical, 300)
            np.testing.assert_array_equal(window._plot._rc_time_ns, expected_t)
            np.testing.assert_allclose(window._plot._rc_values_mv, expected_v)
        else:
            assert not window._plot._rc_time_ns.size
    for pulse, base in zip(window._pulse, before):
        np.testing.assert_array_equal(pulse.v, base)
    # Removing the sweep restores the editable base, not the last preview.
    window._clear_sweep()
    assert window._plot._virtual_preview is None
    assert window._waveform_point_index.value() == 0
    np.testing.assert_array_equal(window._plot._line[0].yData, before[0])


@pytest.mark.parametrize('kind', ['hold', 'ramp'])
def test_duration_and_voltage_preview_share_point_and_settings(window, kind):
    pulse = window._pulse[0]
    pulse.t = np.array([0., 10000., 20000., 30000.])
    pulse.v = np.array([0., 0., 100., 100.])
    duration = (QickHoldDurationSweepSpec('set_1', 10, 50, 3) if kind == 'hold'
                else QickRampRateSweepSpec('ramp_0_to_1', 10, 50, 3))
    window._sweep_specs = [duration, QickSweepSpec('set_1', 'awg_0', -.25, .25, 3)]
    window._refresh_sweep_overlay()
    window._waveform_point_index.setValue(7)
    assert window._waveform_preview_sequence is not None
    virtual_t, virtual_v = window._plot._virtual_preview
    np.testing.assert_array_equal(virtual_t, window._plot._physical_time_ns)
    np.testing.assert_allclose(virtual_v, window._plot._physical_values_mv)
    assert virtual_t[-1] == 70000
    state = window._decode_settings(window._settings_to_dict())
    window._waveform_point_index.setValue(0)
    window._apply_decoded_settings(state)
    assert window._waveform_point_index.value() == 7
    np.testing.assert_array_equal(window._plot._virtual_preview[0], virtual_t)


def test_zoom_ticks_follow_view_and_time_units_without_changing_snap(window):
    plot = window._plot
    plot.set_grid(time_step_ns=1000, voltage_step_mv=100, snap_enabled=True, visible=True)
    settings = plot.grid_settings
    plot.set_time_unit('us')
    plot.setXRange(110000, 130000, padding=0)
    plot.setYRange(-198, -185, padding=0)
    for name, limits, span in [('bottom', (110000, 130000), 20), ('left', (-198, -185), 13)]:
        axis = plot.getAxis(name)
        levels = axis.tickValues(*limits, 650)
        ticks = [v for _, values in levels for v in values]
        assert len(ticks) >= 4
        assert levels[0][0] * axis.scale < span
        strings = axis.tickStrings(levels[0][1], axis.scale, levels[0][0])
        assert len(set(strings)) == len(strings)
    assert plot.grid_settings == settings
    assert plot._snap_voltage(-194, window._pulse[0]) == -200


@pytest.mark.parametrize('span_ns, unit, ns_per_unit', [
    (500., 'ns', 1.),
    (20000., 'us', 1000.),
    (5000000., 'ms', 1000000.),
    (2000000000., 's', 1000000000.),
])
def test_zoom_time_units_keep_all_waveforms_and_input_timing(window, span_ns, unit, ns_per_unit):
    configure_compensated_pulse(window)
    window._sweep_specs = [QickSweepSpec('set_0', 'awg_0', 50/800, 100/800, 3)]
    window._refresh_sweep_overlay()
    window._waveform_point_index.setValue(2)
    plot = window._plot
    plot.set_grid(time_step_ns=1000, voltage_step_mv=100, snap_enabled=True, visible=True)
    curves = (plot._line + plot._physical_line + plot._rc_line +
              [plot._sweep_lower_curve, plot._sweep_upper_curve])
    before = [(curve.xData.copy(), curve.yData.copy()) for curve in curves]
    pulse_times = window._pulse[0].t.copy()
    sequence = window._waveform_preview_sequence
    settings = plot.grid_settings

    # A late absolute timestamp must not prevent selection of nanoseconds.
    lower = 1000000000.
    plot.setXRange(lower, lower + span_ns, padding=0)
    axis = plot.getAxis('bottom')
    assert plot._time_unit == unit
    assert axis.labelText == f'time [{unit}]'
    assert axis.labelUnits == ''
    assert axis.scale == pytest.approx(1/ns_per_unit)
    spacing, ticks = axis.tickValues(lower, lower + span_ns, 650)[0]
    assert len(ticks) >= 2
    labels = axis.tickStrings(ticks, axis.scale, spacing)
    assert len(set(labels)) == len(labels)
    np.testing.assert_allclose(np.array(labels, dtype=float) * ns_per_unit, ticks,
                               rtol=0, atol=spacing/1000)

    # Editor unit changes and settings notifications must not override zoom.
    window._set_time_unit('ms' if unit != 'ms' else 'ns')
    assert plot._time_unit == unit
    np.testing.assert_array_equal(window._pulse[0].t, pulse_times)
    assert window._waveform_preview_sequence is sequence
    assert plot.grid_settings == settings
    assert plot._snap_time(100123, window._pulse[0], 1) == 100000
    for curve, (x, y) in zip(curves, before):
        np.testing.assert_array_equal(curve.xData, x)
        np.testing.assert_array_equal(curve.yData, y)

    plot.fit_view()
    assert plot._time_unit == 'us'
    assert axis.labelText == 'time [us]'
    limits = plot.viewRange()[0]
    assert limits[0] <= min(x[0] for x, _ in before)
    assert limits[1] >= max(x[-1] for x, _ in before)


@pytest.mark.parametrize('boundary, smaller, larger', [
    (1000., 'ns', 'us'), (1000000., 'us', 'ms'), (1000000000., 'ms', 's'),
])
def test_time_unit_boundaries_remain_stable_on_pan_y_zoom_and_refresh(window, boundary, smaller, larger):
    plot = window._plot
    for span, expected in [(boundary*.99, smaller), (boundary*1.01, larger),
                           (boundary, larger), (boundary*.99, smaller)]:
        for offset in [0., boundary*2, -boundary*3]:
            plot.setXRange(offset, offset + span, padding=0)
            for _ in range(3):
                plot.setYRange(-200, 200, padding=0)
                plot._refresh_grid_tick_spacing()
                assert plot._time_unit == expected
                assert plot.getAxis('bottom').labelText == f'time [{expected}]'


def test_rf_duration_changes_same_virtual_physical_and_rc_time_grid(window):
    configure_compensated_pulse(window)
    window._sweep_specs = [QickSweepSpec('set_0', 'awg_0', 50/800, 100/800, 3)]
    window._rf_pulse_specs = [QickRfPulseSpec(
        0, 'set_0', 0, 1, 190, 12000, 0, 0,
        duration_sweep_enabled=True, duration_sweep_start_us=1,
        duration_sweep_stop_us=4, duration_sweep_count=4,
        segment_length_mode='extend_by_rf_duration')]
    window._refresh_sweep_overlay()
    assert window._waveform_point_index.maximum() == 11
    window._waveform_point_index.setValue(11)
    seq = window._waveform_preview_sequence
    expected_end = seq.waveform_vertices(11)[0][-1] * 1000/window._qick_fabric_mhz
    assert window._plot._virtual_preview[0][-1] == expected_end
    assert expected_end in window._plot._physical_time_ns
    assert expected_end in window._plot._rc_time_ns
    assert window._plot._line[0].yData[0] == 100


def test_large_preview_selects_one_point_without_cartesian_materialization(window):
    window._sweep_specs = [QickSweepSpec('set_0', 'awg_0', .01, .02, 200),
                          QickHoldDurationSweepSpec('set_0', 10, 20, 200)]
    window._refresh_sweep_overlay()
    window._waveform_point_index.setValue(39999)
    assert window._waveform_preview_sequence.sweep_point_count == 40000
    assert window._waveform_preview_sequence._sweep_coordinate_cache is None
    assert window._plot._virtual_preview[0].size < 20
    np.testing.assert_array_equal(window._plot._line[0].yData, [16, 16])
    window._sweep_specs = [QickSweepSpec('set_0', 'awg_0', .01, .02, 3)]
    window._refresh_sweep_overlay()
    assert window._waveform_point_index.value() == 2


def test_dc_calibration_uses_shared_current_and_keeps_other_channels_independent(window):
    window._on_qick_configuration_identified(replace(
        firmware(), dac_current_settings=records((31981, 10000, 20000))))
    panel = window._calibration_panel
    assert panel.dc_voltage_full_scale_mv.isReadOnly()
    assert panel.dc_voltage_full_scale_mv.value() == pytest.approx(1279.24)
    assert panel.dc_voltage_config().output_full_scale_mv == pytest.approx(1279.24)
    path = dict(panel.path_diagram_for('dc_voltage').applied_values())
    path['output_ch'] = 3
    panel.apply_path_settings(path, mode='dc_voltage')
    assert panel.dc_voltage_full_scale_mv.value() == 400
    # Keep invalid endpoints editable/savable after a scale decrease; refuse
    # calibration until they fit, without blocking unrelated experiments.
    assert panel.dc_voltage_start_mv.value() == -800
    with pytest.raises(ValueError, match='output full scale'):
        panel.dc_voltage_config()
    saved = window._settings_to_dict()
    window._apply_decoded_settings(window._decode_settings(saved))
    assert panel.dc_voltage_full_scale_mv.value() == 400
    assert window._dac_current_state.scale(1) == pytest.approx(1279.24)
    panel.dc_voltage_start_mv.setValue(-300)
    panel.dc_voltage_stop_mv.setValue(300)
    config = panel.dc_voltage_config()
    assert config.output_full_scale_mv == 400
    assert config.dac_current_settings['11']['current_ua'] == 10000
    window._dac_current_state.update(records((31981, 20000, 20000)))
    assert panel.dc_voltage_full_scale_mv.value() == 800
    assert window._dac_current_state.scale(1) == pytest.approx(1279.24)
