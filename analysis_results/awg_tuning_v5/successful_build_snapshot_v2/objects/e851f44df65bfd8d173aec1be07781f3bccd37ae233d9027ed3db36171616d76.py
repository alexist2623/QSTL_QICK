"""Physical port restrictions, persisted mute choice, and exported execution."""
from types import SimpleNamespace
import pytest
from PyQt5 import QtCore, QtTest, QtWidgets
import DCWaveform_Generator as gui
from dc_waveform_core import generate_qick_program_code
from qick_square_dds import decode_square_settings
from test_square_awg_exclusion import firmware


@pytest.fixture
def window():
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w=gui.MainWindow()
    yield w
    w.close(); w.deleteLater()
    app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete); app.processEvents()


@pytest.mark.parametrize('channel',[3,7])
def test_both_square_editors_use_physical_port_and_reject_awg(window,channel):
    window._on_qick_configuration_identified(firmware(channel))
    for editor in (window._square_dds_panel,window._square_wave_panel):
        assert editor.output_selector.channel.value()==channel
        window._show_qick_front_panel('output',editor)
        panel=window._qick_front_panel
        rejected=QtTest.QSignalSpy(panel.canvas.port_clicked)
        panel.canvas.select_port('output',4)  # ordinary AWG generator 1
        assert len(rejected)==0
        assert panel.output_channel.currentData()==channel
        with pytest.raises(ValueError,match='supported square-wave'):
            editor.apply_front_panel_settings({'output_ch':1})
        panel.canvas.select_port('output',4+channel//2)
        assert panel.selected_settings()['output_ch']==channel
        panel.apply_button.click()
        assert editor.output_selector.channel.value()==channel
    # The shared filter must not leak into the ordinary AWG selector.
    window._show_qick_front_panel('output',window._multi_ctrl)
    window._qick_front_panel.canvas.select_port('output',4)
    assert window._qick_front_panel.selected_settings()['output_ch']==1


def test_old_firmware_cannot_start_square_tab(window):
    window._on_qick_configuration_identified(firmware(None))
    panel=window._square_wave_panel
    assert not panel.start_button.isEnabled()
    assert not panel.stop_button.isEnabled()
    with pytest.raises(ValueError,match='supported square-wave'):
        panel.resolved_config()
    assert not window._square_dds_panel.enabled.isEnabled()


@pytest.mark.parametrize('mute',[True,False])
def test_mute_roundtrip_and_export_runner(window,mute,tmp_path):
    panel=window._square_dds_panel
    panel.enabled.setChecked(True)
    panel.mute_on_finish.setChecked(mute)
    path=window._save_settings_json(tmp_path/'square')
    panel.mute_on_finish.setChecked(not mute)
    window._load_settings_json(path)
    assert panel.mute_on_finish.isChecked()==mute
    config,_=decode_square_settings(panel.settings_dict())
    assert config.mute_on_finish==mute
    code=generate_qick_program_code(window._pulse,awg_channels=(1,),
                                    square_pulse_settings=panel.settings_dict())
    ns={};exec(code,ns)
    assert ns['build_sequence']().square_pulse_config.mute_on_finish==mute
    calls=[]
    soc=SimpleNamespace(stop_square_pulse=lambda ch:calls.append(('mute',ch)))
    program=SimpleNamespace(square_pulse_config=config,
                            run_rounds=lambda *args,**kwargs:calls.append(('run',)))
    ns['build_program']=lambda _:program
    # The exported runner must honor the same choice as the live GUI runner.
    run=ns['run_experiment']
    run(soc,None,configure_rf=False)
    assert calls==[('run',)]+([('mute',config.gen_ch)] if mute else [])
    calls.clear()
    def fail(*args,**kwargs):raise RuntimeError('test failure')
    program.run_rounds=fail
    with pytest.raises(RuntimeError,match='test failure'):
        run(soc,None,configure_rf=False)
    assert calls==[('mute',config.gen_ch)]


def test_old_settings_keep_default_mute():
    config,_=decode_square_settings(dict(enabled=True))
    assert config.mute_on_finish is True
    with pytest.raises(ValueError,match='must be boolean'):
        decode_square_settings(dict(enabled=True,mute_on_finish='false'))
