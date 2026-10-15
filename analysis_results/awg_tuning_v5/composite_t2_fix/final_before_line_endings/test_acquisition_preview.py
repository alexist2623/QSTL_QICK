"""Measurement coverage, sweep alignment and display-only GUI regressions."""
from dataclasses import asdict, replace
import copy

import numpy as np
import pytest
from PyQt5 import QtWidgets

from acquisition_preview import acquisition_window, selected_rf_events
from dc_waveform_core import (QickDdrReadoutSpec, QickHoldDurationSweepSpec,
                              QickRfPulseSpec)
from fir_ddr_profile import resolve_fir_ddr_profile
from qick_fine_tune_sweep import FineTuneSequence
from qick_front_panel import identify_qick_front_panel
from qick_qcodes_experiment import build_runtime_ddr_readout
from test_qick_fine_tune_sweep import _fir_soccfg
from test_rc_precompensation import upgraded
from test_square_awg_exclusion import window, firmware


def current_profile():
    # Same FIR/DDRx clock units as the v3 300 MHz / decimate-by-300 image.
    config = _fir_soccfg()
    config['ddr4_buf'].update(
        supports_trigger_delay=True, trigger_delay_units='s_axis_aclk_cycles',
        trigger_delay_default_cycles=8712, filter_state_continuous=True,
        decimation_phase_continuous=True)
    return resolve_fir_ddr_profile(config)


@pytest.mark.parametrize('mode', ['legacy', 'clock_cycles', 'valid_samples'])
@pytest.mark.parametrize('point', [0, 1, 2])
def test_input_window_matches_compiled_fir_offsets(mode, point):
    cfg = upgraded(_fir_soccfg(fir_rate_profile='1_msps' if mode == 'legacy' else '50_ksps'))
    if mode == 'valid_samples':
        cfg['ddr4_buf'].update(trigger_delay_units='valid_input_samples',
                               trigger_delay_default_samples=51)
    profile = resolve_fir_ddr_profile(cfg)
    seq = FineTuneSequence(('awg_0',))
    seq.add_set('before', .01, 3000).add_set('capture', -.01, 6000)
    seq.add_hold_duration_sweep('before', 3000, 9000, 3)
    spec = QickDdrReadoutSpec(0, 'capture', .001, 7, margin_input_samples=37)
    program = seq.make_program(cfg, awg_channels=(0,), repetitions_per_sweep=2,
                               ddr_readout=build_runtime_ddr_readout(cfg, spec))
    actual = acquisition_window(seq, point, spec, profile, 300., program.tproc_mhz)
    compiled = program.fir_dc_timing_preview(point)
    origin = program.timing['segment_starts'][0] / program.tproc_mhz
    for preview_key, compiled_key in (
            ('trigger_us', 'trigger_us'), ('storage_start_us', 'storage_start_us'),
            ('storage_end_us', 'storage_end_us'),
            ('input_start_us', 'group_delay_referenced_input_start_us'),
            ('input_end_us', 'group_delay_referenced_input_end_us')):
        assert actual[preview_key] == pytest.approx(compiled[compiled_key] - origin)
    assert actual['duration_us'] == 7 * profile.sample_period_us


def test_source_clock_delay_override_and_margin_are_not_measurement_duration():
    seq = FineTuneSequence(('awg_0',)).add_set('hold', .01, 300)
    spec = QickDdrReadoutSpec(0, 'hold', .001, 4, margin_input_samples=9999,
                             fpga_trigger_delay_us=.0101, post_run_read_delay_seconds=3)
    result = acquisition_window(seq, 0, spec, current_profile(), 300., 300.)
    assert result['trigger_us'] == pytest.approx(1 / 300)
    assert result['storage_start_us'] == pytest.approx(4 / 300)
    assert result['input_start_us'] == pytest.approx((4 - 8677) / 300)
    assert result['duration_us'] == 4
    assert acquisition_window(seq, 0, replace(spec, margin_input_samples=0,
        post_run_read_delay_seconds=0), current_profile(), 300., 300.) == result


def test_legacy_trigger_rounds_up_in_tprocessor_clock():
    seq = FineTuneSequence(('awg_0',)).add_set('hold', .01, 300)
    profile = resolve_fir_ddr_profile(_fir_soccfg())
    result = acquisition_window(seq, 0, QickDdrReadoutSpec(0, 'hold', 0, 1),
                                profile, 300., 250.)
    assert result['trigger_us'] == pytest.approx(6998 / 250)
    assert result['duration_us'] == 1


def configure_window(window, *, samples=64):
    profile = current_profile()
    configuration = replace(firmware(), fir_profile=profile,
        fir_sample_rate_hz=profile.sample_rate_hz,
        fir_sample_period_us=profile.sample_period_us,
        fir_trigger_delay_samples=profile.trigger_delay_samples,
        fir_trigger_delay_units=profile.trigger_delay_units,
        fir_trigger_delay_us=profile.trigger_delay_us)
    window._on_qick_configuration_identified(configuration)
    window._pulse[0].edit_flat(0, 10000.)
    window._add_segment(1000., 20000., -50.)
    window._sweep_specs = [QickHoldDurationSweepSpec('set_0', 10., 30., 3)]
    rf = QickRfPulseSpec(
        gen_ch=0, segment_name='set_1', delay_us=2., duration_us=3.,
        frequency_mhz=50., gain=1000, phase_degrees=0., att1_db=0., att2_db=0.)
    window._rf_ports_panel._panels[0].load_settings(dict(asdict(rf), enabled=True))
    window._refresh_physical_waveforms()
    spec = QickDdrReadoutSpec(0, 'set_1', 2., samples)
    window._rf_readout_panel.load_settings(dict(asdict(spec), enabled=True))
    window._on_readout_spec_changed(spec)
    return spec


def test_gui_selected_hold_translates_rf_and_acquisition_without_mutating_settings(window):
    # Linked ViewBoxes need realized screen geometry for zoom/unit assertions.
    window.show()
    QtWidgets.QApplication.processEvents()
    configure_window(window)
    settings = copy.deepcopy(window._settings_to_dict())
    waveform = window._pulse[0].t.copy()
    sequence = window._waveform_preview_sequence
    model = copy.deepcopy(sequence.__dict__)
    data0 = dict(window._acquisition_timeline.window)
    rf0 = window._rf_timelines[0].start_ns
    window._waveform_point_index.setValue(2)
    data2 = window._acquisition_timeline.window
    for key in ('trigger_us', 'input_start_us', 'input_end_us', 'storage_start_us', 'storage_end_us'):
        assert data2[key] - data0[key] == pytest.approx(20.)
    assert window._rf_timelines[0].start_ns - rf0 == pytest.approx(20000.)
    assert data2['duration_us'] == 64
    # Display refresh, point selection and Fit cannot write run settings.
    window._fit_view()
    window._plot.setXRange(0, 400, padding=0)
    QtWidgets.QApplication.processEvents()
    assert window._acquisition_timeline._time_unit == 'ns'
    window._plot.setXRange(0, 5e6, padding=0)
    QtWidgets.QApplication.processEvents()
    assert window._acquisition_timeline._time_unit == 'ms'
    np.testing.assert_array_equal(window._pulse[0].t, waveform)
    settings['display']['waveform_point_index'] = 2  # The requested display selection is saved.
    assert window._settings_to_dict() == settings
    assert sequence.__dict__ == model


def test_gui_own_anchor_hold_changes_do_not_translate_capture(window):
    configure_window(window)
    window._sweep_specs = [QickHoldDurationSweepSpec('set_1', 20., 40., 3)]
    window._refresh_physical_waveforms()
    before = window._acquisition_timeline.window
    window._waveform_point_index.setValue(2)
    after = window._acquisition_timeline.window
    assert after['trigger_us'] == before['trigger_us']
    assert after['input_start_us'] == before['input_start_us']


def test_gui_sample_count_spillover_fit_and_disable(window):
    spec = configure_window(window, samples=1000)
    window._fit_view()
    timeline = window._acquisition_timeline
    assert len(timeline._graphics) == 1  # Acquisition interval only.
    assert timeline.getPlotItem().titleLabel.text == 'Acquisition'
    assert not timeline.getPlotItem().getAxis('left').isVisible()
    assert timeline.start_ns == timeline.window['input_start_us'] * 1000
    assert timeline.end_ns == timeline.window['input_end_us'] * 1000
    assert 'DDR writes:' not in timeline.toolTip()
    xmin, xmax = window._plot.getPlotItem().vb.viewRange()[0]
    assert xmin <= timeline.start_ns and xmax >= timeline.end_ns
    window._rf_readout_panel.samples.setValue(2000)
    assert timeline.window['samples'] == 2000
    assert timeline.window['duration_us'] == 2000
    window._rf_readout_panel.setChecked(False)
    assert timeline.isHidden() and timeline.window is None
    assert not timeline.toolTip()
    window._rf_readout_panel.load_settings(dict(asdict(spec), enabled=True))
    window._on_readout_spec_changed(spec)
    assert not timeline.isHidden()


def test_missing_or_changed_hwh_never_reuses_stale_measurement_window(window):
    assert firmware().fir_profile is None
    spec = configure_window(window)
    timeline = window._acquisition_timeline
    window._on_qick_configuration_identified(firmware())
    assert timeline.window is None
    assert timeline.getPlotItem().titleLabel.text == 'Acquisition'
    assert 'Identify QICK' in timeline.toolTip()
    configure_window(window)
    connection = window._shared_qick_connection()
    window._apply_shared_qick_setup(replace(connection, ns_port=connection.ns_port + 1), 300., 300.)
    assert timeline.window is None
    assert 'Identify QICK' in timeline.toolTip()


def test_front_panel_keeps_full_resolved_profile():
    cfg = _fir_soccfg()
    cfg._cfg.update(board='ZCU216')
    configuration = identify_qick_front_panel(cfg)
    assert configuration.fir_profile.group_delay_input_samples == 8677.
    assert configuration.fir_profile.input_rate_mhz == 300.


def test_gui_restored_point_and_negative_input_window_fit(window):
    spec = configure_window(window)
    window._waveform_point_index.setValue(2)
    settings = window._settings_to_dict()
    expected = dict(window._acquisition_timeline.window)
    window._waveform_point_index.setValue(0)
    window._apply_decoded_settings(window._decode_settings(settings))
    assert window._acquisition_timeline.window == expected
    spec = replace(spec, segment_name='set_0', delay_us=0, fpga_trigger_delay_us=0)
    window._rf_readout_panel.load_settings(dict(asdict(spec), enabled=True))
    window._fit_view()
    assert window._acquisition_timeline.window['input_start_us'] < 0
    assert window._plot.getPlotItem().vb.viewRange()[0][0] < window._acquisition_timeline.start_ns


def test_gui_hwh_rate_refresh_changes_duration(window):
    configure_window(window, samples=10)
    assert window._acquisition_timeline.window['duration_us'] == 10
    profile = resolve_fir_ddr_profile(_fir_soccfg(fir_rate_profile='50_ksps'))
    window._on_qick_configuration_identified(replace(
        window._qick_configuration, fir_profile=profile,
        fir_sample_rate_hz=profile.sample_rate_hz,
        fir_sample_period_us=profile.sample_period_us,
        fir_trigger_delay_us=profile.trigger_delay_us))
    assert window._acquisition_timeline.window['duration_us'] == 200


def test_rf_duration_uses_selected_coordinate_and_moves_following_anchor():
    seq = FineTuneSequence(('awg_0',))
    seq.add_set('set_0', .01, 3000).add_set('set_1', .02, 3000)
    seq.add_rf_duration_sweep('set_0', 0, 1., 3., 3,
                              segment_length_mode='extend_by_rf_duration',
                              sequence_fabric_mhz=300.)
    spec = QickRfPulseSpec(gen_ch=0, segment_name='set_0', delay_us=0,
                           duration_us=1, frequency_mhz=50, gain=1000, phase_degrees=0,
                           att1_db=0., att2_db=0.)
    assert selected_rf_events(seq, 2, spec, 300.)[0][2] == pytest.approx(3.)
    capture = QickDdrReadoutSpec(0, 'set_1', 0, 4)
    before = acquisition_window(seq, 0, capture, current_profile(), 300., 300.)
    after = acquisition_window(seq, 2, capture, current_profile(), 300., 300.)
    assert after['trigger_us'] - before['trigger_us'] == pytest.approx(2.)
