from types import SimpleNamespace
import ast
import numpy as np
from PyQt5 import QtWidgets, QtTest
from test_dc_waveform_gui_rf import _application
import DCWaveform_Generator as gui
from dc_waveform_core import generate_qick_program_code
from qick_square_dds import decode_square_settings
from awg_sweep_map import _axis_display_values, _stored_axis_native_values


def test_front_panel_identifies_firmware_capabilities():
    from qick_front_panel import identify_qick_front_panel
    from test_qick_front_panel import _live_config
    cfg=_live_config()
    cfg['gens'][3].update(type='axis_square_pulse_v1',dac='13')
    cfg['tprocs']=[dict(output_pins=[('output',7,6,'SPARE1_1V8')])]
    identified=identify_qick_front_panel(cfg)
    assert identified.square_pulse_channels==(3,)
    assert identified.output_trigger_pins==('SPARE1_1V8',)
    assert identified.port('output',7).qick_channels==(3,)
    cfg['gens'][3]['type']='axis_awg_tuning_v1'
    cfg['tprocs']=[]
    identified=identify_qick_front_panel(cfg)
    assert identified.square_pulse_channels==identified.output_trigger_pins==()


def test_enabled_sweep_uses_start_instead_of_inactive_fixed_value():
    from qick_square_dds import OutputTriggerConfig
    from qick_fine_tune_sweep import FineTuneSequence
    app=_application(); window=gui.MainWindow()
    panel=window._square_dds_panel
    panel.enabled.setChecked(True)
    row=panel.rows['amplitude']
    row['value'].setValue(10)
    row['start'].setValue(1); row['stop'].setValue(2); row['sweep'].setChecked(True)
    config,axes=decode_square_settings(panel.settings_dict(),full_scale_mv=5)
    assert config.amplitude_mv==1 and axes[0].stop==2
    seq=FineTuneSequence(('gate',)).add_set('measure',0.0,300)
    panel.attach_to_sequence(seq,5,OutputTriggerConfig())
    assert seq.square_pulse_config.amplitude_mv==1
    window.close(); app.processEvents()


def test_tabs_settings_export_and_old_firmware(tmp_path):
    app=_application(); window=gui.MainWindow()
    square=window._square_dds_panel
    square.set_configuration(SimpleNamespace(square_pulse_channels=(7,)))
    square.enabled.setChecked(True)
    square.rows['frequency']['sweep'].setChecked(True)
    square.rows['frequency']['start'].setValue(100)
    square.rows['frequency']['stop'].setValue(190)
    square.rows['frequency']['count'].setValue(4)
    square.rows['phase']['sweep'].setChecked(True)
    square.rows['phase']['stop'].setValue(180)
    trigger=window._experiment_panel.triggering_panel
    trigger.enabled.setChecked(True); trigger.edge.setCurrentIndex(2); trigger.width.setValue(0.1)
    assert window._experiment_panel.measurement_tabs.tabText(1)=='Triggering'
    assert len(window._active_map_sweep_specs())==2
    assert 'MHz' in window._experiment_panel._sweep_axis_label(window._active_map_sweep_specs()[0])
    path=window._save_settings_json(tmp_path/'square')
    restored=gui.MainWindow(); restored._load_settings_json(path)
    assert restored._square_dds_panel.settings_dict()==square.settings_dict()
    assert restored._experiment_panel.triggering_panel.settings_dict()==trigger.settings_dict()
    config,axes=decode_square_settings(square.settings_dict())
    assert config.gen_ch==7 and len(axes)==2
    code=generate_qick_program_code(window._pulse,awg_channels=(1,),
        square_pulse_settings=square.settings_dict(),output_trigger_settings=trigger.settings_dict())
    ast.parse(code); namespace={}; exec(code,namespace)
    sequence=namespace['build_sequence']()
    assert sequence.square_pulse_config.gen_ch==7
    assert len(sequence.sweep_axes)==2
    assert sequence.output_trigger_config.edge=='both'
    square.set_configuration(SimpleNamespace(square_pulse_channels=()))
    assert not square.enabled.isChecked() and not square.enabled.isEnabled()
    square.load_settings(restored._square_dds_panel.settings_dict())
    assert not square.enabled.isChecked()
    trigger.set_configuration(SimpleNamespace(output_trigger_pins=()))
    trigger.load_settings(restored._experiment_panel.triggering_panel.settings_dict())
    assert not trigger.enabled.isChecked()
    restored.close(); window.close(); app.processEvents()


def test_square_units_are_not_scaled_like_awg_voltage():
    for kind,unit in (('frequency','MHz'),('phase','deg'),('amplitude','mV')):
        axis=SimpleNamespace(axis_kind='square_'+kind)
        values,label=_axis_display_values(np.array([1.,2.]),axis,800)
        np.testing.assert_array_equal(values,[1.,2.]); assert label==unit
        values=_stored_axis_native_values(np.array([1.,2.]),dict(axis_kind='square_'+kind,unit=unit),full_scale_mv=800)
        np.testing.assert_array_equal(values,[1.,2.])
