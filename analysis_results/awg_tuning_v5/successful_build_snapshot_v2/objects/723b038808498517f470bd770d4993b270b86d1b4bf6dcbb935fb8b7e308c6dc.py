"""Square DDS channels must never be assigned to ordinary AWG electrodes."""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5 import QtCore, QtTest, QtWidgets

import DCWaveform_Generator as gui
from qick_front_panel import identify_qick_front_panel
from test_qick_front_panel import _live_config


def firmware(square_channel=7):
    config = _live_config()
    config["gens"] = []
    for index in range(4):
        config["gens"].extend([
            dict(dac=f"0{index}", type="axis_signal_gen_v6",
                 fullpath=f"axis_signal_gen_v6_{index}"),
            dict(dac=f"1{index}", type="axis_awg_tuning_v1",
                 fullpath=f"axis_awg_tuning_v1_{2 * index + 1}"),
        ])
    config["gens"].extend(
        dict(dac=f"2{index}", type="axis_awg_tuning_v1",
             fullpath=f"axis_awg_tuning_v1_{index + 8}") for index in range(4)
    )
    if square_channel is not None:
        config["gens"][square_channel].update(
            type="axis_square_pulse_v1", fullpath="axis_square_pulse_v1_0"
        )
    return identify_qick_front_panel(config)


@pytest.fixture
def window():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = gui.MainWindow()
    yield window
    app.processEvents()
    window.close()
    window.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    app.processEvents()


@pytest.mark.parametrize("square_channel, expected", [
    (7, (1, 3, 5, 8)),
    (3, (1, 5, 7, 8)),
    (None, (1, 3, 5, 7)),
])
def test_new_awg_outputs_follow_firmware_identity(window, square_channel, expected):
    window._on_qick_configuration_identified(firmware(square_channel))
    for _ in range(3):
        window._add_port()
    assert window._qick_awg_channels == expected
    assert window._experiment_panel._parse_awg_channels(4) == expected
    for axis in (window._stability_panel.x_axis, window._stability_panel.y_axis):
        assert set(axis.output.itemData(i, QtCore.Qt.UserRole + 1)
                   for i in range(axis.output.count())) == set(firmware(square_channel).awg_tuning_channels)


def test_manual_and_direct_awg_assignment_rejected(window):
    configuration = firmware()
    window._on_qick_configuration_identified(configuration)
    panel = window._experiment_panel
    panel.awg_channels.setText("7")
    assert "SquarePulse" in panel.awg_channels.toolTip()
    with pytest.raises(ValueError, match="SquarePulse.*7"):
        panel._parse_awg_channels(1)
    with pytest.raises(ValueError, match="SquarePulse.*7"):
        window._set_awg_output_channel(0, 7)
    with pytest.raises(ValueError, match="SquarePulse.*7"):
        window._multi_ctrl.apply_front_panel_settings({"output_ch": 7})
    assert window._qick_awg_channels == (1,)
    panel.awg_channels.setText("5")
    assert panel._parse_awg_channels(1) == (5,)
    assert not panel.awg_channels.toolTip()

    dialog = gui.QickExportDialog(1, ("hold",), parent=window,
                                 initial_awg_channels=(7,),
                                 front_panel_configuration=configuration)
    with pytest.raises(ValueError, match="SquarePulse.*7"):
        dialog.values()
    dialog.awg_channels.setText("5")
    assert dialog.values()["awg_channels"] == (5,)
    dialog.close()


def test_front_panel_disables_square_only_for_awg_and_stability(window):
    window._on_qick_configuration_identified(firmware())
    window._add_port()
    panel = window._qick_front_panel
    for target in (window._multi_ctrl, window._stability_panel.y_axis):
        window._show_qick_front_panel("output", target)
        before = panel.output_channel.currentData()
        clicked = QtTest.QSignalSpy(panel.canvas.port_clicked)
        panel.canvas.select_port("output", 7)
        assert len(clicked) == 0
        assert panel.output_channel.currentData() == before
        # A saved preferred channel cannot bypass the graphical restriction.
        panel.set_path_values({"output_ch": 7})
        assert panel.output_channel.count() == 0
        assert not panel.apply_button.isEnabled()
        with pytest.raises(ValueError, match="required mapped"):
            panel.selected_settings()
        panel.canvas.select_port("output", 4)
        assert panel.selected_settings()["output_ch"] == 1

    # Changing the shared dialog's purpose must remove the AWG-only filter.
    panel.set_awg_output_mode(False)
    panel.canvas.select_port("output", 7)
    assert panel.output_channel.currentData() == 7
    window._show_qick_front_panel("output", window._multi_ctrl)
    panel.canvas.select_port("output", 7)
    assert panel.output_channel.currentData() == window._multi_ctrl.front_panel_values()["output_ch"]
    assert panel.output_channel.findData(7) == -1


def test_identification_removes_stale_stability_targets_without_remapping(window):
    for _ in range(3):
        window._add_port()
    assert window._qick_awg_channels == (1, 3, 5, 7)
    window._stability_panel.y_axis.apply_front_panel_settings({"output_ch": 7})
    window._on_qick_configuration_identified(firmware())
    assert window._qick_awg_channels == (1, 3, 5, 7)
    assert "SquarePulse" in window._experiment_panel.awg_channels.toolTip()
    for axis in (window._stability_panel.x_axis, window._stability_panel.y_axis):
        assert 7 not in [axis.output.itemData(i, QtCore.Qt.UserRole + 1)
                         for i in range(axis.output.count())]
        with pytest.raises(ValueError, match="SquarePulse.*7"):
            axis.apply_front_panel_settings({"output_ch": 7})
    with pytest.raises(ValueError, match="SquarePulse.*7"):
        window._experiment_panel._parse_awg_channels(4)
    # Loading older firmware makes generator 7 an ordinary AWG again.
    window._on_qick_configuration_identified(firmware(None))
    assert window._experiment_panel._parse_awg_channels(4) == (1, 3, 5, 7)
    assert not window._experiment_panel.awg_channels.toolTip()
    window._stability_panel.y_axis.apply_front_panel_settings({"output_ch": 7})
    assert window._stability_panel.y_axis.current_gen_ch() == 7


def test_saved_awg_mapping_is_rejected_before_mutating_window(window, tmp_path):
    document = window._settings_to_dict()
    document["qick"]["awg_channels"] = [7]
    path = tmp_path / "old_awg_assignment.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    # Settings may be prepared offline; firmware knowledge is checked on load.
    decoded = window._decode_settings(document)
    window._on_qick_configuration_identified(firmware())
    before = window._qick_awg_channels
    with pytest.raises(ValueError, match="SquarePulse.*7"):
        window._load_settings_json(path)
    with pytest.raises(ValueError, match="SquarePulse.*7"):
        window._apply_decoded_settings(decoded)
    assert window._qick_awg_channels == before
    assert len(window._pulse) == 1
    window._on_qick_configuration_identified(firmware(None))
    window._load_settings_json(path)
    assert window._qick_awg_channels == (7,)


def test_stability_uses_unassigned_awgs_when_tuning_contains_square_channel(window):
    window._add_port()
    window._set_awg_output_channel(1, 7)
    window._on_qick_configuration_identified(firmware())
    panel = window._stability_panel
    assert panel.x_axis.output.count() == panel.y_axis.output.count() == 7
    assert panel._targets_available
    assert 7 not in panel.run_output_mapping()[1]
