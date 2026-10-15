"""Regression checks for displayed segment labels and independent stability DACs."""
import numpy as np
import pytest
from PyQt5 import QtCore

import DCWaveform_Generator as gui
from test_square_awg_exclusion import firmware, window  # noqa: F401


def test_acquisition_segment_labels_refresh_without_changing_anchor(window):
    pulse = window._pulse[0]
    pulse.add_flat_ramp(10, 1000, 20)
    window._refresh_rf_editor()
    readout = window._rf_readout_panel
    readout.segment.setCurrentIndex(1)
    readout.setChecked(True)
    pulse.rename_segment(0, 'Initialize')
    pulse.rename_segment(1, 'Read charge')
    window._on_segment_name_changed(0, 1)
    assert [readout.segment.itemText(i) for i in range(2)] == ['Initialize', 'Read charge']
    assert readout.configured_spec().segment_name == 'set_1'
    saved = window._settings_to_dict()
    window._apply_decoded_settings(window._decode_settings(saved))
    assert readout.segment.currentText() == 'Read charge'
    assert readout.configured_spec().segment_name == 'set_1'


def select_electrodes(window, x=5, y=8):
    window._on_qick_configuration_identified(firmware())
    panel = window._stability_panel
    for axis, channel in ((panel.x_axis, x), (panel.y_axis, y)):
        axis.apply_front_panel_settings({'output_ch': channel})
        axis.start_mv.setValue(5)
        axis.stop_mv.setValue(10)
        axis.points.setValue(2)
    return panel


def test_stability_selects_unassigned_dacs_and_passes_them_to_compiler(window):
    panel = select_electrodes(window)
    assert window._qick_awg_channels == (1,)
    assert len(window._pulse) == 1
    args = window._stability_run_arguments(save=False)
    assert args['awg_channels'] == (1, 5, 8)
    assert args['sequence'].output_names == ('awg_0', 'gen_5', 'gen_8')
    assert [axis.output_name for axis in args['sequence'].sweep_axes] == ['gen_5', 'gen_8']
    np.testing.assert_array_equal(args['sequence'].cross_capacitance, np.eye(3))
    assert window._qick_awg_channels == (1,)
    assert panel.x_axis.current_gen_ch() == 5
    assert panel.y_axis.current_gen_ch() == 8


def test_independent_electrodes_roundtrip_offline_and_reidentify(window):
    select_electrodes(window)
    saved = window._settings_to_dict()
    restored = gui.MainWindow()
    try:
        restored._apply_decoded_settings(restored._decode_settings(saved))
        for identified in (False, True):
            if identified:
                restored._on_qick_configuration_identified(firmware())
            panel = restored._stability_panel
            assert (panel.x_axis.current_gen_ch(), panel.y_axis.current_gen_ch()) == (5, 8)
            assert restored._stability_run_arguments(save=False)['awg_channels'] == (1, 5, 8)
    finally:
        restored.close()
        restored.deleteLater()


def test_stability_keeps_selected_dacs_when_tuning_assignment_changes(window):
    panel = select_electrodes(window)
    window._set_awg_output_channel(0, 5)
    assert panel.x_axis.current_gen_ch() == 5
    assert panel.y_axis.current_gen_ch() == 8
    assert window._stability_run_arguments(save=False)['awg_channels'] == (5, 8)


def test_stability_preserves_existing_virtual_gate_matrix(window):
    window._add_port()
    matrix = np.array([[1., .2], [-.1, 1.]])
    window._cross_capacitance = matrix.copy()
    select_electrodes(window, x=1, y=8)
    args = window._stability_run_arguments(save=False)
    assert args['awg_channels'] == (1, 3, 8)
    expected = np.eye(3)
    expected[:2, :2] = matrix
    np.testing.assert_array_equal(args['sequence'].cross_capacitance, expected)


def test_stability_rejects_square_rf_and_duplicate_dac_selections(window):
    panel = select_electrodes(window)
    with pytest.raises(ValueError, match='SquarePulse'):
        panel.x_axis.apply_front_panel_settings({'output_ch': 7})
    with pytest.raises(ValueError, match='not an available AWG'):
        panel.x_axis.apply_front_panel_settings({'output_ch': 0})
    panel.y_axis.apply_front_panel_settings({'output_ch': 5})
    with pytest.raises(ValueError, match='different'):
        panel.run_output_mapping()


def test_identified_stability_defaults_work_with_one_tuning_output(window):
    window._on_qick_configuration_identified(firmware())
    panel = window._stability_panel
    assert panel._targets_available
    assert (panel.x_axis.current_gen_ch(), panel.y_axis.current_gen_ch()) == (1, 3)
    assert panel.run_output_mapping() == (('awg_0', 'gen_3'), (1, 3))
    assert 7 not in [panel.x_axis.output.itemData(i, QtCore.Qt.UserRole + 1)
                     for i in range(panel.x_axis.output.count())]
