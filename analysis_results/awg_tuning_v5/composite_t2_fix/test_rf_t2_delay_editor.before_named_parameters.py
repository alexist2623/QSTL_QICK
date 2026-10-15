"""Offline RF editor checks for T2 endpoints and named delay sweeps."""
from dataclasses import asdict

import pytest
from PyQt5 import QtCore, QtWidgets

import DCWaveform_Generator as gui
from dc_waveform_core import QickRfCompositeItemSpec, QickRfDurationParameterSpec, QickRfFrequencyParameterSpec


@pytest.fixture
def editor():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = gui.MainWindow()
    panel = window._rf_ports_panel._panels[0]
    panel.load_settings({
        **gui.DEFAULT_RF_OUTPUT_SETTINGS,
        "enabled": True,
        "pulse_mode": "composite",
        "duration_parameters": [asdict(QickRfDurationParameterSpec("d0", 2.0))],
        "composite_items": [
            asdict(QickRfCompositeItemSpec("pulse", "X", 2.0, "f0", duration_parameter="d0")),
            asdict(QickRfCompositeItemSpec("delay", "wait", 3.0)),
        ],
    })
    yield panel
    window.close()
    window.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    app.processEvents()


@pytest.mark.parametrize("initial,final", [(False, False), (True, False), (False, True), (True, True)])
def test_t2_endpoint_choices_and_half_duration_roundtrip(editor, initial, final):
    editor.t2_initial_pi2.setChecked(initial)
    editor.t2_final_pi2.setChecked(final)
    editor.t2_initial_phase.setValue(90)
    editor.t2_final_phase.setValue(-90)
    spec = editor.configured_spec()
    events = spec.pulse_events
    assert len(events) == 1 + int(initial) + int(final)
    if initial:
        assert events[0].duration_us == 1.0
        assert events[0].phase_degrees == 90
    if final:
        assert events[-1].duration_us == 1.0
        assert events[-1].phase_degrees == -90
    assert len(spec.composite_items) == 2  # endpoints aren't saved into the body
    saved = editor.settings_dict()
    editor.load_settings(saved)
    assert editor.configured_spec() == spec
    editor.duration_parameter_table.cellWidget(0, 1).setValue(4.0)
    changed = editor.configured_spec().pulse_events
    if initial:
        assert changed[0].duration_us == 2.0
    if final:
        assert changed[-1].duration_us == 2.0


def test_named_tau_shared_delay_sweep_roundtrip_units_and_rename(editor):
    editor._add_delay_parameter(QickRfDurationParameterSpec("tau", 3.0, True, 2.0, 4.0, 3))
    editor.composite_item_table.cellWidget(1, 8).setCurrentText("tau")
    editor._add_composite_item("delay")
    editor.composite_item_table.cellWidget(2, 8).setCurrentText("tau")
    editor.t2_final_pi2.setChecked(True)
    spec = editor.configured_spec()
    axes = [axis for axis in spec.software_sweep_axes if axis.axis_kind == "rf_delay"]
    assert len(axes) == 1
    assert axes[0].parameter_name == "tau"
    assert list(axes[0].points) == [2.0, 3.0, 4.0]
    # Both references share each coordinate and move the final endpoint.
    assert spec.with_delay_parameters({"tau": 4.0}).pulse_events[-1].delay_us == 10.0
    assert not editor.composite_item_table.cellWidget(1, 2).isEnabled()
    editor.set_time_unit("ns")
    assert editor.delay_parameter_table.cellWidget(0, 1).value() == 3000.0
    assert editor.configured_spec() == spec
    name = editor.delay_parameter_table.cellWidget(0, 0)
    name.setText("free_evolution")
    assert editor.configured_spec() == spec  # transactional until editingFinished
    name.editingFinished.emit()
    renamed = editor.configured_spec()
    assert renamed.delay_parameters[0].name == "free_evolution"
    assert [item.delay_parameter for item in renamed.composite_items[1:]] == ["free_evolution"] * 2
    editor.load_settings(editor.settings_dict())
    assert editor.configured_spec() == renamed


def test_removing_tau_reference_disables_orphan_sweep_and_remove_preserves_fixed_value(editor):
    editor._add_delay_parameter(QickRfDurationParameterSpec("tau", 3.0, True, 2.0, 4.0, 3))
    editor.composite_item_table.cellWidget(1, 8).setCurrentText("tau")
    editor.composite_item_table.cellWidget(1, 8).setCurrentText("Fixed")
    assert not editor.delay_parameter_table.cellWidget(0, 2).isChecked()
    editor.composite_item_table.cellWidget(1, 8).setCurrentText("tau")
    editor._remove_delay_parameter()
    assert editor.composite_item_table.cellWidget(1, 8).currentData() == ""
    assert editor.composite_item_table.cellWidget(1, 2).isEnabled()
    assert editor.configured_spec().composite_items[1].duration_us == 3.0


def test_duration_name_is_atomic_with_live_editor_callbacks(editor):
    editor.t2_initial_pi2.setChecked(True)
    name = editor.duration_parameter_table.cellWidget(0, 0)
    name.setText("pi_time")
    # Other live controls may refresh the preview while the name has focus.
    editor.t2_gain.setValue(12345)
    assert editor.configured_spec().duration_parameters[0].name == "d0"
    name.editingFinished.emit()
    spec = editor.configured_spec()
    assert spec.t2_duration_parameter == "pi_time"
    assert spec.composite_items[0].duration_parameter == "pi_time"
    assert spec.pulse_events[0].duration_us == 1.0
    name.setText("invalid name")
    name.editingFinished.emit()
    assert name.text() == "pi_time"
    assert editor.configured_spec() == spec


def test_t2_pi_duration_sweep_is_host_axis_and_halves_each_point(editor):
    editor.t2_initial_pi2.setChecked(True)
    editor.t2_final_pi2.setChecked(True)
    table = editor.duration_parameter_table
    table.cellWidget(0, 3).setValue(2.0)
    table.cellWidget(0, 4).setValue(6.0)
    table.cellWidget(0, 5).setValue(3)
    table.cellWidget(0, 2).setChecked(True)
    spec = editor.configured_spec()
    axes = [axis for axis in spec.software_sweep_axes if axis.axis_kind == "rf_t2_duration"]
    assert len(axes) == 1
    assert list(axes[0].points) == [2.0, 4.0, 6.0]
    assert not [axis for axis in spec.sweep_axes if axis.parameter_name == "d0"]
    for duration in axes[0].points:
        events = spec.with_duration_parameters({"d0": duration}).pulse_events
        assert [event.duration_us for event in events] == [duration / 2, duration, duration / 2]


def test_t2_last_parameter_reference_disables_orphan_sweep(editor):
    editor._add_duration_parameter(QickRfDurationParameterSpec("d1", 3.0, True, 2.0, 4.0, 3))
    editor.t2_initial_pi2.setChecked(True)
    editor._set_t2_duration_parameter("d1")
    assert editor.duration_parameter_table.cellWidget(1, 2).isChecked()
    editor._set_t2_duration_parameter("d0")
    assert not editor.duration_parameter_table.cellWidget(1, 2).isChecked()


def test_disabled_t2_roundtrip_preserves_selected_pi_parameter(editor):
    editor._add_duration_parameter(QickRfDurationParameterSpec("d1", 3.0))
    editor.t2_initial_pi2.setChecked(True)
    editor._set_t2_duration_parameter("d1")
    editor.t2_initial_pi2.setChecked(False)
    saved = editor.settings_dict()
    editor.load_settings(saved)
    editor.t2_final_pi2.setChecked(True)
    assert editor.configured_spec().t2_duration_parameter == "d1"
    assert editor.configured_spec().pulse_events[-1].duration_us == 1.5


@pytest.mark.parametrize("template", ["custom", "cpmg", "udd", "hahn_echo"])
def test_single_mode_omits_t2_and_switching_back_restores_editor_options(editor, template):
    editor.predefined_template.setCurrentIndex(editor.predefined_template.findData(template))
    editor.t2_initial_pi2.setChecked(True)
    editor.t2_final_pi2.setChecked(True)
    expected_count = len(editor.configured_spec().pulse_events)
    editor.single_mode.setChecked(True)
    single = editor.configured_spec()
    assert single.pulse_mode == "single"
    assert not single.t2_initial_pi2 and not single.t2_final_pi2
    assert len(single.pulse_events) == 1
    editor.composite_mode.setChecked(True)
    restored = editor.configured_spec()
    assert restored.t2_initial_pi2 and restored.t2_final_pi2
    assert restored.predefined_template == template
    assert len(restored.pulse_events) == expected_count


@pytest.mark.parametrize("initial,final", [(True, False), (False, True), (True, True)])
def test_custom_switch_displays_half_reference_without_duplicating_endpoints(editor, initial, final):
    editor.predefined_template.setCurrentIndex(editor.predefined_template.findData("hahn_echo"))
    editor.t2_initial_pi2.setChecked(initial)
    editor.t2_final_pi2.setChecked(final)
    editor.predefined_template.setCurrentIndex(editor.predefined_template.findData("custom"))
    assert editor.t2_duration_parameter.currentText() == "d0/2"
    assert editor.t2_duration_parameter.currentData() == "d0"
    spec = editor.configured_spec()
    assert len(spec.composite_items) == 3
    assert len(spec.pulse_events) == 1 + int(initial) + int(final)
    assert spec.composite_items[1].duration_parameter == "d0"
    editor.duration_parameter_table.cellWidget(0, 1).setValue(6.0)
    events = editor.configured_spec().pulse_events
    if initial:
        assert events[0].duration_us == 3.0
    if final:
        assert events[-1].duration_us == 3.0
    name = editor.duration_parameter_table.cellWidget(0, 0)
    name.setText("pi_length")
    name.editingFinished.emit()
    assert editor.t2_duration_parameter.currentText() == "pi_length/2"
    assert editor.t2_duration_parameter.currentData() == "pi_length"
    saved = editor.settings_dict()
    editor.load_settings(saved)
    assert editor.settings_dict() == saved


def test_tau_named_fixed_uses_item_data_and_emits_when_label_is_unchanged(editor):
    editor._add_delay_parameter(QickRfDurationParameterSpec("Fixed", 7.0, True, 6.0, 8.0, 3))
    selector = editor.composite_item_table.cellWidget(1, 8)
    updates = []
    editor.changed.connect(lambda: updates.append(editor.configured_spec()))
    selector.setCurrentIndex(selector.findData("Fixed"))
    assert updates[-1].composite_items[1].delay_parameter == "Fixed"
    assert not editor.composite_item_table.cellWidget(1, 2).isEnabled()
    assert editor.delay_parameter_table.cellWidget(0, 2).isChecked()
    selector.setCurrentIndex(selector.findData(""))
    assert updates[-1].composite_items[1].delay_parameter == ""
    assert editor.composite_item_table.cellWidget(1, 2).isEnabled()
    assert not editor.delay_parameter_table.cellWidget(0, 2).isChecked()


def test_global_frequency_and_gain_override_body_and_t2_endpoints(editor):
    editor._add_frequency_parameter(QickRfFrequencyParameterSpec("shared", 135.0))
    editor.t2_initial_pi2.setChecked(True)
    editor.t2_final_pi2.setChecked(True)
    assert editor.global_rf_group.isChecked()
    editor.global_frequency_parameter.setCurrentText("shared")
    editor.global_gain.setValue(-12345)
    editor.t2_initial_phase.setValue(90)
    editor.t2_final_phase.setValue(-90)
    events = editor.configured_spec().pulse_events
    assert [event.frequency_mhz for event in events] == [135.0] * 3
    assert [event.gain for event in events] == [-12345] * 3
    assert [event.phase_degrees for event in events] == [90, 0, -90]
    assert not editor.composite_item_table.cellWidget(0, 4).isEnabled()
    assert not editor.composite_item_table.cellWidget(0, 5).isEnabled()
    assert not editor.composite_item_table.cellWidget(0, 6).isEnabled()
    assert editor.t2_frequency_parameter.isHidden()
    assert editor.t2_gain.isHidden()
    saved = editor.settings_dict()
    editor.load_settings(saved)
    assert editor.settings_dict() == saved


def test_legacy_loaded_composite_preserves_individual_frequency_and_gain(editor):
    saved = editor.settings_dict()
    saved.pop("global_frequency_parameter", None)
    saved.pop("global_gain", None)
    saved["t2_initial_pi2"] = True
    saved["t2_final_pi2"] = True
    saved["t2_gain"] = 7654
    saved["composite_items"][0]["gain"] = 1234
    editor.load_settings(saved)
    assert not editor.global_rf_group.isChecked()
    assert [event.gain for event in editor.configured_spec().pulse_events] == [7654, 1234, 7654]
    assert editor.composite_item_table.cellWidget(0, 4).isEnabled()
    assert editor.composite_item_table.cellWidget(0, 5).isEnabled()
    assert not editor.t2_gain.isHidden()
    editor.global_rf_group.setChecked(True)
    editor.global_gain.setValue(2345)
    assert [event.gain for event in editor.configured_spec().pulse_events] == [2345] * 3
    editor.global_rf_group.setChecked(False)
    assert [event.gain for event in editor.configured_spec().pulse_events] == [7654, 1234, 7654]


def test_hahn_echo_fixes_n_and_sweeps_total_free_evolution_tau(editor):
    editor.predefined_n_sweep_enabled.setChecked(True)
    editor.predefined_n.setValue(5)
    editor.predefined_template.setCurrentIndex(editor.predefined_template.findData("hahn_echo"))
    editor.predefined_tau.setValue(12.0)
    editor.predefined_tau_sweep_start.setValue(6.0)
    editor.predefined_tau_sweep_stop.setValue(12.0)
    editor.predefined_tau_sweep_count.setValue(3)
    editor.predefined_tau_sweep_enabled.setChecked(True)
    spec = editor.configured_spec()
    assert spec.predefined_n == 1
    assert not spec.predefined_n_sweep_enabled
    assert not editor.predefined_n.isEnabled()
    assert not editor.predefined_n_sweep_enabled.isEnabled()
    assert [item.kind for item in spec.composite_items] == ["delay", "pulse", "delay"]
    assert [item.duration_us for item in spec.composite_items if item.kind == "delay"] == [6.0, 6.0]
    assert [axis.axis_kind for axis in spec.software_sweep_axes] == ["rf_template_tau"]
    assert editor.global_rf_group.isChecked()
    assert not any("π/2 pulses bracket" in label.text() for label in editor.findChildren(QtWidgets.QLabel))
