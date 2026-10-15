"""Tests for live HWH-to-front-panel channel discovery and GUI synchronization.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5 import QtCore, QtTest, QtWidgets
import pytest

import DCWaveform_Generator as gui
from qick_front_panel import (
    QickFrontPanelControl,
    QickFrontPanelPreview,
    identify_qick_front_panel,
)


def _application():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _live_config():
    return {
        "board": "ZCU216",
        "fw_timestamp": "2026-07-19 12:34:56",
        "extra_description": [
            "\nQICK box daughter cards detected:",
            "\tDAC slot 0: RF Out card has ports [0, 1, 2, 3]",
            "\tDAC slot 1: DC Out card has ports [4, 5, 6, 7]",
            "\tDAC slot 2: No card detected",
            "\tDAC slot 3: RF Out card has ports [12, 13, 14, 15]",
            "\tADC slot 0: DC In card has ports [0, 1]",
            "\tADC slot 1: RF In card has ports [2, 3]",
            "\tADC slot 2: No card detected",
            "\tADC slot 3: RF In card has ports [6, 7]",
        ],
        "gens": [
            {"dac": "00", "fullpath": "axis_signal_gen_v6_0"},
            {"dac": "10", "fullpath": "axis_awg_tuning_v1_0"},
            {"dac": "33", "fullpath": "axis_signal_gen_v6_15"},
            {"dac": "11", "fullpath": "axis_awg_tuning_v1_1"},
        ],
        "readouts": [
            {"adc": "10", "avgbuf_fullpath": "axis_avg_buffer_0"},
            {"adc": "12", "avgbuf_fullpath": "axis_avg_buffer_2"},
            {"adc": "23", "avgbuf_fullpath": "axis_avg_buffer_7"},
        ],
    }


def test_hwh_and_card_detection_build_zcu216_physical_port_map():
    configuration = identify_qick_front_panel(_live_config())

    assert configuration.board == "ZCU216"
    assert configuration.firmware_timestamp == "2026-07-19 12:34:56"
    assert configuration.port("output", 0).qick_channels == (0,)
    assert configuration.port("output", 0).converter_id == "00"
    assert configuration.port("output", 0).board_type == "RF_Out"
    assert configuration.port("output", 4).qick_channels == (1,)
    assert configuration.port("output", 4).converter_id == "10"
    assert configuration.port("output", 4).board_type == "DC_Out"
    assert configuration.port("output", 15).qick_channels == (2,)
    assert configuration.port("output", 8).board_type is None

    assert configuration.port("input", 0).qick_channels == (0,)
    assert configuration.port("input", 0).converter_id == "10"
    assert configuration.port("input", 0).board_type == "DC_In"
    assert configuration.port("input", 2).qick_channels == (1,)
    assert configuration.port("input", 2).converter_id == "12"
    assert configuration.port("input", 2).board_type == "RF_In"
    assert configuration.port("input", 7).qick_channels == (2,)


def test_hwh_identification_reports_runtime_pl_ddr_capacity():
    config = _live_config()
    config["ddr4_buf"] = {
        "maxlen": 1 << 30,
        "samples_per_axi_word": 8,
    }

    configuration = identify_qick_front_panel(config)

    assert configuration.ddr_capacity_words_32b == 1 << 30
    assert configuration.ddr_samples_per_axi_word == 8


@pytest.mark.parametrize(
    (
        "rate_profile",
        "rate_hz",
        "decimation",
        "supports_delay",
        "delay_samples",
        "delay_units",
        "expected_delay_us",
        "expected_label",
    ),
    (
        (
            "1_msps",
            1_000_000.0,
            300,
            False,
            0,
            "valid_input_samples",
            0.0,
            "1 MSPS",
        ),
        (
            "50_ksps",
            50_000.0,
            6000,
            True,
            50,
            "s_axis_aclk_cycles",
            50.0 / 300.0,
            "50 kSPS",
        ),
    ),
)
def test_hwh_identification_reports_fir_ddr_profile(
    rate_profile,
    rate_hz,
    decimation,
    supports_delay,
    delay_samples,
    delay_units,
    expected_delay_us,
    expected_label,
):
    config = _live_config()
    config["ddr4_buf"] = {
        "sample_capture": True,
        "fir_enabled": True,
        "fir_rate_profile": rate_profile,
        "stored_sample_rate_hz": rate_hz,
        "fir_decimation": decimation,
        "fir_input_fs_mhz": 300.0,
        "fir_group_delay_input_samples": 296_677.0,
        "supports_trigger_delay": supports_delay,
        "trigger_delay_units": delay_units,
        "trigger_delay_default_samples": (
            delay_samples if delay_units == "valid_input_samples" else 0
        ),
        "trigger_delay_default_cycles": (
            delay_samples if delay_units == "s_axis_aclk_cycles" else 0
        ),
    }

    configuration = identify_qick_front_panel(config)

    assert configuration.fir_rate_profile == rate_profile
    assert configuration.fir_sample_rate_hz == rate_hz
    assert expected_label in configuration.fir_rate_label
    assert configuration.fir_trigger_delay_samples == delay_samples
    assert configuration.fir_trigger_delay_units == (
        delay_units if supports_delay else "none"
    )
    assert configuration.fir_trigger_delay_us == pytest.approx(
        expected_delay_us
    )


def test_front_panel_control_selects_smas_and_reports_channel_attenuation():
    app = _application()
    panel = QickFrontPanelControl()
    panel.set_path_values(
        {
            "output_ch": 1,
            "readout_ch": 1,
            "output_att1_db": 3.25,
            "output_att2_db": 4.5,
            "output_nqz": 2,
            "readout_nqz": 2,
            "readout_attenuation_db": 7.25,
            "readout_dc_gain_db": 12.0,
        }
    )
    panel.set_configuration(identify_qick_front_panel(_live_config()))
    app.processEvents()

    assert panel.output_sma.text() == "DAC4"
    assert panel.output_channel.currentData() == 1
    assert panel.output_board.text() == "DC Out"
    assert panel.output_att1_db.isEnabled() is False
    assert panel.input_sma.text() == "ADC2"
    assert panel.input_channel.currentData() == 1
    assert panel.input_board.text() == "RF In"
    assert panel.input_condition_stack.currentWidget() is panel.input_attenuation_db
    assert panel.output_nqz.value() == 2
    assert panel.input_nqz.value() == 2
    assert "QICK gen 1" in panel.summary.text()
    assert "ATT 7.25 dB" in panel.summary.text()

    panel.canvas.select_port("output", 0)
    app.processEvents()
    assert panel.output_sma.text() == "DAC0"
    assert panel.output_channel.currentData() == 0
    assert panel.output_att1_db.isEnabled() is True

    applied = []
    panel.settings_applied.connect(applied.append)
    panel.apply_button.click()
    app.processEvents()
    assert applied[0]["output_ch"] == 0
    assert applied[0]["readout_ch"] == 1
    assert applied[0]["output_board_type"] == "RF_Out"
    assert applied[0]["input_board_type"] == "RF_In"
    assert applied[0]["readout_attenuation_db"] == 7.25
    assert applied[0]["output_nqz"] == 2
    assert applied[0]["readout_nqz"] == 2
    panel.close()


def test_graphical_path_updates_only_requesting_sparameter_tab():
    app = _application()
    window = gui.MainWindow()
    panel = window._qick_front_panel
    assert window._control_tabs.indexOf(panel) == -1
    assert window._control_tabs.currentWidget() is window._awg_tuning_page
    assert window._awg_tuning_tabs.currentWidget() is window._multi_ctrl

    configuration = identify_qick_front_panel(_live_config())
    window._on_qick_configuration_identified(configuration)
    window._show_qick_front_panel("path", window._sparameter_panel)
    panel.canvas.select_port("output", 0)
    panel.canvas.select_port("input", 2)
    panel.output_att1_db.setValue(6.25)
    panel.output_att2_db.setValue(8.5)
    panel.input_attenuation_db.setValue(11.75)
    panel.output_nqz.setValue(2)
    panel.input_nqz.setValue(2)
    panel.apply_button.click()
    app.processEvents()

    sparameter = window._sparameter_panel.config()
    assert sparameter.output_ch == 0
    assert sparameter.readout_ch == 1
    assert sparameter.output_board_type == "RF_Out"
    assert sparameter.input_board_type == "RF_In"
    assert sparameter.output_att1_db == 6.25
    assert sparameter.output_att2_db == 8.5
    assert sparameter.readout_attenuation_db == 11.75
    assert sparameter.nqz == 2
    assert sparameter.readout_nqz == 2

    experiment_output = window._rf_ports_panel._panels[0]
    assert experiment_output.att1_db.value() == 0.0
    assert window._rf_readout_panel.ro_ch.value() == 0
    assert window._rf_readout_panel.attenuation_db.value() == 20.0
    assert window._rf_readout_panel.nqz.value() == 1

    calibration = window._calibration_panel
    assert calibration.output_ch.value() == 0
    assert calibration.output_att1.value() == 0.0
    assert calibration.input_output_ch.value() == 0
    assert calibration.input_readout_ch.value() == 0
    assert calibration.input_attenuation.value() == 0.0
    stability_path = window._stability_panel.front_panel_values()
    assert stability_path["readout_ch"] == 0
    assert stability_path["readout_attenuation_db"] == 20.0
    window.close()


def test_front_panel_visual_order_is_physical_descending_order():
    app = _application()
    preview = QickFrontPanelPreview()
    preview.set_configuration(identify_qick_front_panel(_live_config()))
    preview.show()
    app.processEvents()

    assert preview._port_centers[("output", 15)].x() < preview._port_centers[("output", 0)].x()
    assert preview._port_centers[("input", 7)].x() < preview._port_centers[("input", 0)].x()
    activated = []
    preview.activated.connect(lambda: activated.append(True))
    QtTest.QTest.mouseClick(preview, QtCore.Qt.LeftButton)
    assert activated == [True]
    preview.close()


def test_front_panel_preview_height_tracks_available_width():
    _application()
    preview = QickFrontPanelPreview()

    assert preview.heightForWidth(300) == 102
    assert preview.heightForWidth(600) == 205
    assert preview.heightForWidth(900) == 308
    assert preview.heightForWidth(1400) == 410
    assert preview.sizePolicy().verticalPolicy() == QtWidgets.QSizePolicy.Preferred
    assert preview.maximumHeight() == 410


def test_front_panel_preview_tracks_enclosing_scroll_viewport():
    app = _application()
    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    content = QtWidgets.QWidget(scroll)
    content.setMinimumWidth(1600)
    layout = QtWidgets.QVBoxLayout(content)
    preview = QickFrontPanelPreview(content)
    layout.addWidget(preview)
    layout.addStretch(1)
    scroll.setWidget(content)
    scroll.resize(640, 420)
    scroll.show()
    app.processEvents()
    app.processEvents()

    expected_width = scroll.viewport().width() - 36
    assert preview.width() == expected_width
    assert preview.height() == preview.heightForWidth(expected_width)

    scroll.resize(760, 420)
    app.processEvents()
    app.processEvents()
    expected_width = scroll.viewport().width() - 36
    assert preview.width() == expected_width
    assert preview.height() == preview.heightForWidth(expected_width)
    scroll.close()


def test_output_preview_opens_scoped_dialog_and_applies_hwh_board_settings(
    monkeypatch,
):
    app = _application()
    window = gui.MainWindow()
    hardware_updates = []
    monkeypatch.setattr(
        window,
        "_start_rf_output_hardware_update",
        lambda connection, spec: hardware_updates.append((connection, spec)),
    )
    configuration = identify_qick_front_panel(_live_config())
    window._on_qick_configuration_identified(configuration)
    output = window._rf_ports_panel._panels[0]
    output.gen_ch.setValue(1)
    app.processEvents()

    assert output.output_board_type.currentText() == "DC_Out"
    assert output.filter_type.isEnabled() is False

    output.gen_ch.setValue(0)
    window._show_qick_front_panel("output", output)
    app.processEvents()
    panel = window._qick_front_panel
    assert panel.scope == "output"
    assert panel.canvas._scope == "output"
    assert panel.output_group.isVisible()
    assert panel.input_group.isVisible() is False
    panel.canvas.select_port("output", 0)
    panel.output_att1_db.setValue(5.25)
    panel.output_att2_db.setValue(7.5)
    panel.output_filter_type.setCurrentText("lowpass")
    panel.output_nqz.setValue(2)
    panel.apply_button.click()
    app.processEvents()

    assert output.gen_ch.value() == 0
    assert output.output_board_type.currentText() == "RF_Out"
    assert output.att1_db.value() == 5.25
    assert output.att2_db.value() == 7.5
    assert output.filter_type.currentText() == "lowpass"
    assert output.nqz.isHidden()
    assert output.layout().indexOf(output.nqz) == -1
    assert output.configured_spec().nqz == 2
    saved_output = output.settings_dict()
    assert saved_output["nqz"] == 2
    output.load_settings(saved_output)
    assert output.configured_spec().nqz == 2
    assert output.nqz.isHidden()
    assert hardware_updates[-1][1].nqz == 2
    assert len(hardware_updates) == 1
    assert hardware_updates[0][1].gen_ch == 0
    assert hardware_updates[0][1].att1_db == 5.25
    assert hardware_updates[0][1].att2_db == 7.5
    assert hardware_updates[0][1].filter_type == "lowpass"
    assert window._qick_front_panel_dialog.isVisible() is False
    window.close()


def test_scoped_front_panel_hides_and_disables_opposite_connector_direction():
    app = _application()
    panel = QickFrontPanelControl()
    panel.set_configuration(identify_qick_front_panel(_live_config()))
    clicked = []
    panel.canvas.port_clicked.connect(
        lambda direction, index: clicked.append((direction, index))
    )

    panel.set_scope("output")
    panel.show()
    app.processEvents()
    assert panel.output_group.isVisible() is True
    assert panel.input_group.isVisible() is False
    panel.canvas.select_port("input", 2)
    panel.canvas.select_port("output", 0)
    assert clicked == [("output", 0)]
    assert panel.canvas._direction_is_visible("input") is False

    clicked.clear()
    panel.set_scope("input")
    app.processEvents()
    assert panel.output_group.isVisible() is False
    assert panel.input_group.isVisible() is True
    panel.canvas.select_port("output", 0)
    panel.canvas.select_port("input", 2)
    assert clicked == [("input", 2)]
    assert panel.canvas._direction_is_visible("output") is False

    panel.set_scope("path")
    app.processEvents()
    assert panel.output_group.isVisible() is True
    assert panel.input_group.isVisible() is True
    assert panel.canvas._direction_is_visible("output") is True
    assert panel.canvas._direction_is_visible("input") is True
    panel.close()


def test_stability_front_panel_path_is_independent_from_other_tabs():
    app = _application()
    window = gui.MainWindow()
    configuration = identify_qick_front_panel(_live_config())
    window._on_qick_configuration_identified(configuration)
    awg_output = window._rf_ports_panel._panels[0]
    awg_output.att1_db.setValue(1.25)
    window._rf_readout_panel.attenuation_db.setValue(3.0)

    window._show_qick_front_panel("path", window._stability_panel)
    panel = window._qick_front_panel
    panel.canvas.select_port("output", 0)
    panel.canvas.select_port("input", 2)
    panel.output_att1_db.setValue(4.5)
    panel.output_att2_db.setValue(6.75)
    panel.input_attenuation_db.setValue(8.25)
    panel.apply_button.click()
    app.processEvents()

    stability_path = window._stability_panel.front_panel_values()
    assert stability_path["output_ch"] == 0
    assert stability_path["output_att1_db"] == 4.5
    assert stability_path["output_att2_db"] == 6.75
    assert stability_path["readout_ch"] == 1
    assert stability_path["readout_attenuation_db"] == 8.25
    assert awg_output.att1_db.value() == 1.25
    assert window._rf_readout_panel.attenuation_db.value() == 3.0
    assert window._sparameter_panel.output_att1_db.value() == 10.0
    assert window._calibration_panel.output_att1.value() == 0.0
    window.close()


def test_calibration_front_panel_path_is_independent_from_other_tabs():
    app = _application()
    window = gui.MainWindow()
    configuration = identify_qick_front_panel(_live_config())
    window._on_qick_configuration_identified(configuration)
    window._show_qick_front_panel("path", window._calibration_panel)
    panel = window._qick_front_panel
    panel.canvas.select_port("output", 0)
    panel.canvas.select_port("input", 2)
    panel.output_att1_db.setValue(2.75)
    panel.output_att2_db.setValue(5.0)
    panel.input_attenuation_db.setValue(7.25)
    panel.apply_button.click()
    app.processEvents()

    calibration = window._calibration_panel
    assert calibration.output_att1.value() == 2.75
    assert calibration.output_att2.value() == 5.0
    assert calibration.input_output_att1.value() == 0.0
    assert calibration.input_readout_ch.value() == 0
    assert calibration.input_attenuation.value() == 0.0
    assert calibration.dc_voltage_output_ch.value() == 1

    calibration.tabs.setCurrentIndex(1)
    window._show_qick_front_panel("path", calibration)
    panel.canvas.select_port("output", 0)
    panel.canvas.select_port("input", 2)
    panel.output_att1_db.setValue(8.5)
    panel.input_attenuation_db.setValue(7.25)
    panel.apply_button.click()
    app.processEvents()
    assert calibration.input_output_att1.value() == 8.5
    assert calibration.input_readout_ch.value() == 1
    assert calibration.input_attenuation.value() == 7.25
    assert calibration.output_att1.value() == 2.75
    assert calibration.dc_voltage_output_ch.value() == 1
    assert window._rf_ports_panel._panels[0].att1_db.value() == 0.0
    assert window._rf_readout_panel.attenuation_db.value() == 20.0
    assert window._sparameter_panel.output_att1_db.value() == 10.0
    assert window._stability_panel.front_panel_values()["output_att1_db"] == 10.0
    window.close()


def test_calibration_places_an_independent_front_panel_in_every_subtab():
    _application()
    window = gui.MainWindow()
    calibration = window._calibration_panel
    diagrams = [
        calibration.path_diagram_for(mode)
        for mode in ("output", "input", "dc_voltage")
    ]

    assert len({id(diagram) for diagram in diagrams}) == 3
    for index, diagram in enumerate(diagrams):
        tab = calibration.tabs.widget(index)
        assert tab.isAncestorOf(diagram)
    window.close()


def test_stability_electrodes_are_selected_from_front_panel_dac_smas():
    app = _application()
    window = gui.MainWindow()
    window._add_port()
    configuration = identify_qick_front_panel(_live_config())
    window._on_qick_configuration_identified(configuration)

    x_axis = window._stability_panel.x_axis
    y_axis = window._stability_panel.y_axis
    window._show_qick_front_panel("output", x_axis)
    panel = window._qick_front_panel
    panel.canvas.select_port("output", 4)
    panel.apply_button.click()
    app.processEvents()
    assert x_axis.current_gen_ch() == 1
    assert "DAC4" in x_axis.front_panel_status.text()

    window._show_qick_front_panel("output", y_axis)
    panel.canvas.select_port("output", 5)
    panel.apply_button.click()
    app.processEvents()
    assert y_axis.current_gen_ch() == 3
    assert "DAC5" in y_axis.front_panel_status.text()
    assert not hasattr(x_axis, "segment")
    window.close()


def test_sparameter_path_places_preview_above_two_column_path():
    _application()
    window = gui.MainWindow()
    path = window._sparameter_panel.path_diagram
    layout = path.layout()
    update_position = layout.getItemPosition(layout.indexOf(path.update_button))
    preview_position = layout.getItemPosition(layout.indexOf(path.front_panel_preview))
    input_position = layout.getItemPosition(layout.indexOf(path.input_endpoint))
    output_position = layout.getItemPosition(layout.indexOf(path.output_endpoint))
    dut_position = layout.getItemPosition(layout.indexOf(path.dut_component))

    assert not hasattr(path, "summary")
    assert layout.horizontalSpacing() == 10
    assert layout.columnCount() == 2
    assert preview_position == (0, 0, 1, 2)
    assert input_position == (1, 0, 1, 1)
    assert output_position == (1, 1, 1, 1)
    assert dut_position == (5, 0, 1, 2)
    assert update_position == (6, 0, 1, 2)
    window.close()


def test_configuration_worker_uses_live_qick_config(monkeypatch):
    app = _application()
    monkeypatch.setattr(gui, "connect_qick", lambda _connection: (object(), _live_config()))
    worker = gui.QickConfigurationWorker(object())
    finished = []
    failed = []
    worker.finished.connect(finished.append)
    worker.failed.connect(failed.append)
    worker.run()
    app.processEvents()

    assert failed == []
    assert finished[0].mapped_output_count == 4
    assert finished[0].mapped_input_count == 3


def test_front_panel_rejects_non_zcu216_mapping():
    with pytest.raises(ValueError, match="supports ZCU216"):
        identify_qick_front_panel({"board": "ZCU111"})
