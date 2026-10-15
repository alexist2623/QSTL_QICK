"""Shared physical DAC selection must retain the editor's generator role."""
import pytest
from PyQt5 import QtCore, QtWidgets
import DCWaveform_Generator as gui
from qick_front_panel import identify_qick_front_panel
from test_qick_front_panel import _live_config


def configuration(version=3, include_type=True):
    cfg = _live_config()
    cfg['gens'] = []
    for pair in range(3):
        for kind in ('axis_signal_gen_v6', f'axis_awg_tuning_v{version}'):
            gen = dict(dac=f'1{pair}', fullpath=f'{kind}_{pair}',
                       output_sum_version=1, output_sum_role='awg' if 'awg' in kind else 'rf')
            if include_type:
                gen['type'] = kind
            cfg['gens'].append(gen)
    cfg['gens'].extend([
        dict(dac='00', type='axis_signal_gen_v6', fullpath='axis_signal_gen_v6_3'),
        dict(dac='13', type='axis_square_pulse_v1', fullpath='axis_square_pulse_v1_0'),
    ])
    return identify_qick_front_panel(cfg)


@pytest.fixture
def window():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win = gui.MainWindow()
    yield win
    win._qick_front_panel_dialog.close()
    win.close()
    win.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    app.processEvents()


@pytest.mark.parametrize('pair', range(3))
@pytest.mark.parametrize('version', [1, 2, 3])
def test_click_shared_dac_applies_awg_generator(window, pair, version):
    window._on_qick_configuration_identified(configuration(version))
    window._show_qick_front_panel('output', window._multi_ctrl)
    panel = window._qick_front_panel
    panel.canvas.select_port('output', 4 + pair)
    assert panel.output_channel.count() == 1
    assert panel.output_channel.currentData() == 2 * pair + 1
    assert panel.output_channel.findData(2 * pair) == -1
    assert panel.apply_button.isEnabled()
    panel.apply_settings()
    assert window._qick_awg_channels == (2 * pair + 1,)


def test_stale_rf_preference_and_legacy_path_identity(window):
    window._on_qick_configuration_identified(configuration(include_type=False))
    window._show_qick_front_panel('output', window._multi_ctrl)
    panel = window._qick_front_panel
    panel.set_path_values({'output_ch': 2})
    assert panel.selected_settings()['output_ch'] == 3
    # RF-only and Square DACs cannot be forced through a saved preference.
    for invalid in (6, 7):
        panel.set_path_values({'output_ch': invalid})
        assert panel.output_channel.count() == 0
        assert not panel.apply_button.isEnabled()


def test_stability_uses_awg_and_rf_mode_retains_rf(window):
    window._on_qick_configuration_identified(configuration())
    window._show_qick_front_panel('output', window._stability_panel.x_axis)
    panel = window._qick_front_panel
    panel.canvas.select_port('output', 5)
    assert panel.selected_settings()['output_ch'] == 3
    panel.set_awg_output_mode(False)
    panel.set_path_values({'output_ch': 2})
    assert panel.selected_settings()['output_ch'] == 2
    panel.set_awg_output_mode(True)
    assert panel.selected_settings()['output_ch'] == 3
