"""Main-window integration for composite T2 and named host delays."""
from dataclasses import asdict
import copy
import pytest
from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg
import DCWaveform_Generator as gui
from dc_waveform_core import QickRfPulseSpec, QickDdrReadoutSpec

_APP = None
@pytest.fixture
def window():
    global _APP
    _APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    widget = gui.MainWindow()
    yield widget
    widget.close()
    widget.deleteLater()
    _APP.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    _APP.processEvents()


def load_composite(window, *, pi_sweep=False, template='custom'):
    settings = dict(gui.DEFAULT_RF_OUTPUT_SETTINGS, enabled=True,
        pulse_mode='composite', segment_length_mode='extend_by_rf_duration',
        predefined_template=template, predefined_n=2,
        predefined_tau_sweep_enabled=(template != 'custom'),
        predefined_tau_sweep_start_us=2., predefined_tau_sweep_stop_us=4.,
        predefined_tau_sweep_count=2,
        t2_initial_pi2=True, t2_final_pi2=True, t2_duration_parameter='d0',
        duration_parameters=[dict(name='d0',duration_us=.4,sweep_enabled=pi_sweep,
                                  sweep_start_us=.4,sweep_stop_us=.8,sweep_count=2)],
        delay_parameters=[dict(name='tau',duration_us=1.,sweep_enabled=True,
                               sweep_start_us=1.,sweep_stop_us=3.,sweep_count=3)],
        composite_items=[dict(kind='pulse',name='pi',duration_us=.4,frequency_parameter='f0',
                             duration_parameter='d0'),
                         dict(kind='delay',name='evolve',duration_us=1.,delay_parameter='tau')])
    panel=window._rf_ports_panel._panels[0]
    panel.load_settings(settings)
    QtWidgets.QApplication.processEvents()
    return panel


@pytest.mark.parametrize('template', ['custom','cpmg','udd','hahn_echo'])
def test_main_window_decoders_keep_t2_and_delay_variables(window,template):
    panel=load_composite(window,template=template)
    expected=panel.configured_spec()
    saved=window._settings_to_dict()
    decoded=window._decode_settings(copy.deepcopy(saved))['rf_outputs'][0]
    enabled=decoded.pop('enabled')
    assert enabled
    assert QickRfPulseSpec(**decoded)==expected
    other=window._decode_rf_output_entries([panel.settings_dict()],set_names={'set_0'},label='Test RF')[0]
    other.pop('enabled')
    assert QickRfPulseSpec(**other)==expected


@pytest.mark.parametrize('kind', ['rf_delay','rf_t2_duration'])
def test_host_tau_and_pi_sweep_edit_remove_from_experiment(window,kind):
    panel=load_composite(window,pi_sweep=True)
    axis=next(a for a in window._active_map_sweep_specs() if a.axis_kind==kind)
    assert 'software' in window._experiment_panel._sweep_axis_label(axis)
    assert window._experiment_panel._sweep_parameter_values(axis)[-1]=='us'
    window._update_sweep_parameter(axis,.6,1.2,4)
    updated=next(a for a in window._active_map_sweep_specs() if a.axis_kind==kind)
    assert updated.count==4
    assert updated.points.tolist()==pytest.approx([.6,.8,1.,1.2])
    window._remove_sweep_parameter(updated)
    assert not any(a.axis_kind==kind for a in panel.configured_spec().software_sweep_axes)


@pytest.mark.parametrize('template', ['custom','cpmg','udd','hahn_echo'])
def test_host_selected_point_changes_rf_and_awg_preview_together(window,template):
    load_composite(window,pi_sweep=True,template=template)
    saved=copy.deepcopy(window._settings_to_dict())
    count=window._waveform_point_index.maximum()+1
    assert count==(6 if template=='custom' else 4)
    initial=window._waveform_preview_rf_specs[0]
    start_duration=initial.pulse_events[0].duration_us
    window._waveform_point_index.setValue(count-1)
    QtWidgets.QApplication.processEvents()
    concrete=window._waveform_preview_rf_specs[0]
    assert not concrete.software_sweep_axes
    assert concrete.pulse_events[0].duration_us==pytest.approx(.4)
    assert concrete.pulse_events[-1].duration_us==pytest.approx(.4)
    assert concrete.pulse_events[0].duration_us>start_duration
    assert window._waveform_preview_hardware_index==0
    assert window._waveform_preview_sequence is not None
    assert window._rf_timelines[0].pulse_names[0]=='T2_initial_pi2'
    current=window._settings_to_dict()
    assert current['display']['waveform_point_index']==count-1
    saved['display']['waveform_point_index']=count-1
    assert current==saved


def test_composite_envelopes_all_use_one_color(window):
    load_composite(window)
    timeline=window._rf_timelines[0]
    colors={item.opts['pen'].color().name() for item in timeline.getPlotItem().items
            if isinstance(item,pg.PlotDataItem) and item.opts.get('pen') is not None}
    assert len(colors)==1


def test_host_delay_ddr_usage_reuses_memory(window):
    load_composite(window,pi_sweep=True)
    panel=window._experiment_panel
    panel._ddr_readout_spec=QickDdrReadoutSpec(0,'set_0',0.,16)
    panel._refresh_ddr_usage()
    assert '6 host software point(s)' in panel.ddr_usage_summary.text()
    assert '1 hardware point(s)' in panel.ddr_usage_summary.text()


@pytest.mark.parametrize('template', ['custom','hahn_echo'])
def test_global_values_survive_both_decoders_and_apply_to_preview(window,template):
    panel=load_composite(window,pi_sweep=True,template=template)
    settings=panel.settings_dict()
    settings.update(global_frequency_parameter='shared',global_gain=4321,
        frequency_parameters=[dict(name='f0',frequency_mhz=100.),
                              dict(name='shared',frequency_mhz=123.)])
    panel.load_settings(settings)
    QtWidgets.QApplication.processEvents()
    expected=panel.configured_spec()
    assert expected.global_frequency_parameter=='shared'
    assert expected.global_gain==4321
    for decoded in (
        window._decode_settings(copy.deepcopy(window._settings_to_dict()))['rf_outputs'][0],
        window._decode_rf_output_entries([panel.settings_dict()],set_names={'set_0'},label='Global RF')[0],
    ):
        decoded.pop('enabled')
        assert QickRfPulseSpec(**decoded)==expected
    window._waveform_point_index.setValue(window._waveform_point_index.maximum())
    QtWidgets.QApplication.processEvents()
    events=window._waveform_preview_rf_specs[0].pulse_events
    assert len(events)==3
    assert all(event.frequency_mhz==123. and event.gain==4321 for event in events)
    assert events[0].duration_us==pytest.approx(.4)
    assert events[-1].duration_us==pytest.approx(.4)
    assert panel.t2_duration_parameter.currentText()=='d0/2'
    assert panel.t2_duration_parameter.currentData()=='d0'
