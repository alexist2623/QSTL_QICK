"""Offline RF editor checks for T2 endpoints and named delay sweeps."""
from dataclasses import asdict

import pytest
from PyQt5 import QtCore, QtWidgets

import DCWaveform_Generator as gui
from dc_waveform_core import (QickRfCompositeItemSpec, QickRfDurationParameterSpec,
    QickRfFrequencyParameterSpec, QickRfDelayParameterSpec, QickRfAmplitudeParameterSpec,
    QickRfPhaseParameterSpec)


def parameter_row(editor, kind, name):
    return list(getattr(editor, f"_{kind}_parameter_names")() if kind == "delay"
                else editor._numeric_parameter_names(kind)).index(name)


def set_parameter(editor, kind, selector, value):
    row = parameter_row(editor, kind, selector.currentData())
    getattr(editor, f"{kind}_parameter_table").cellWidget(row, 1).setValue(value)


def select(selector, name):
    index = selector.findData(name)
    assert index >= 0
    selector.setCurrentIndex(index)


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
    set_parameter(editor, "phase", editor.t2_initial_phase_parameter, 90)
    set_parameter(editor, "phase", editor.t2_final_phase_parameter, -90)
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
    row = parameter_row(editor, "delay", "tau")
    assert editor.delay_parameter_table.cellWidget(row, 1).value() == 3000.0
    assert editor.configured_spec() == spec
    name = editor.delay_parameter_table.cellWidget(row, 0)
    name.setText("free_evolution")
    assert editor.configured_spec() == spec  # transactional until editingFinished
    name.editingFinished.emit()
    renamed = editor.configured_spec()
    assert renamed.delay_parameters[row].name == "free_evolution"
    assert [item.delay_parameter for item in renamed.composite_items[1:]] == ["free_evolution"] * 2
    editor.load_settings(editor.settings_dict())
    assert editor.configured_spec() == renamed


def test_removing_tau_reference_disables_orphan_sweep(editor):
    editor._add_delay_parameter(QickRfDurationParameterSpec("tau", 3.0, True, 2.0, 4.0, 3))
    editor.composite_item_table.cellWidget(1, 8).setCurrentText("tau")
    editor.composite_item_table.cellWidget(1, 8).setCurrentText("tau_wait")
    row = parameter_row(editor, "delay", "tau")
    assert not editor.delay_parameter_table.cellWidget(row, 2).isChecked()
    editor.composite_item_table.cellWidget(1, 8).setCurrentText("tau")
    editor._remove_delay_parameter()
    assert editor.composite_item_table.cellWidget(1, 8).currentData() == "tau_fixed"
    assert not editor.composite_item_table.cellWidget(1, 2).isEnabled()
    assert editor.configured_spec().effective_composite_items[1].duration_us == 3.0


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
    row = parameter_row(editor, "delay", "Fixed")
    assert editor.delay_parameter_table.cellWidget(row, 2).isChecked()
    select(selector, "tau_wait")
    assert updates[-1].composite_items[1].delay_parameter == "tau_wait"
    assert not editor.composite_item_table.cellWidget(1, 2).isEnabled()
    assert not editor.delay_parameter_table.cellWidget(row, 2).isChecked()


def test_global_frequency_and_gain_override_body_and_t2_endpoints(editor):
    editor._add_frequency_parameter(QickRfFrequencyParameterSpec("shared", 135.0))
    select(editor.predefined_template, "hahn_echo")
    editor.t2_initial_pi2.setChecked(True)
    editor.t2_final_pi2.setChecked(True)
    assert editor.global_rf_group.isChecked()
    editor.global_frequency_parameter.setCurrentText("shared")
    editor.global_gain.setValue(-12345)
    set_parameter(editor, "phase", editor.t2_initial_phase_parameter, 90)
    set_parameter(editor, "phase", editor.t2_final_phase_parameter, -90)
    events = editor.configured_spec().pulse_events
    assert [event.frequency_mhz for event in events] == [135.0] * 3
    assert [event.gain for event in events] == [-12345] * 3
    assert [event.phase_degrees for event in events] == [90, 0, -90]
    assert not editor.composite_item_table.cellWidget(1, 4).isEnabled()
    assert not editor.composite_item_table.cellWidget(1, 5).isEnabled()
    assert not editor.composite_item_table.cellWidget(1, 6).isEnabled()
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
    assert not editor.composite_item_table.cellWidget(0, 5).isEnabled()  # explicit legacy mode
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


def test_custom_named_amplitude_phase_and_zero_delay(editor):
    editor.amplitude_mode_group.setChecked(True)
    editor._add_numeric_parameter("amplitude", QickRfAmplitudeParameterSpec("a1", 4321))
    editor._add_numeric_parameter("phase", QickRfPhaseParameterSpec("p1", 90))
    editor._add_composite_item("pulse")
    select(editor.composite_item_table.cellWidget(2, 5), "a1")
    select(editor.composite_item_table.cellWidget(2, 7), "p1")
    editor._add_delay_parameter(QickRfDelayParameterSpec("tau_zero", 0, True, 0, 2, 3))
    select(editor.composite_item_table.cellWidget(1, 8), "tau_zero")
    spec = editor.configured_spec()
    assert spec.global_amplitude_mode == "manual"
    assert spec.global_amplitude_parameter == spec.global_frequency_parameter == ""
    assert [event.gain for event in spec.pulse_events] == [20000, 4321]
    assert [event.phase_degrees for event in spec.pulse_events] == [0, 90]
    assert spec.pulse_events[1].delay_us == 2
    assert editor.composite_item_table.cellWidget(0, 5).isEnabled()
    assert editor.composite_item_table.cellWidget(2, 5).isEnabled()
    assert editor.composite_item_table.cellWidget(2, 7).isEnabled()
    saved = editor.settings_dict()
    editor.load_settings(saved)
    assert editor.configured_spec() == spec


def test_explicit_manual_migration_preserves_independent_legacy_values(editor):
    saved = editor.settings_dict()
    saved["composite_items"] = [
        asdict(QickRfCompositeItemSpec("pulse", "X a", 2, "f0", gain=1234, phase_degrees=10, duration_parameter="d0")),
        asdict(QickRfCompositeItemSpec("delay", "wait a", 3)),
        asdict(QickRfCompositeItemSpec("pulse", "X_a", 2, "f0", gain=-5678, phase_degrees=20, duration_parameter="d0")),
        asdict(QickRfCompositeItemSpec("delay", "wait_a", 7)),
    ]
    saved["phase_parameters"] = [asdict(QickRfPhaseParameterSpec("phase_initial", 45))]
    saved["t2_initial_phase_parameter"] = ""
    saved["t2_initial_phase_degrees"] = 90
    saved["t2_initial_pi2"] = True
    saved["t2_gain"] = 8765
    editor.load_settings(saved)
    before = editor.configured_spec().pulse_events
    assert [event.gain for event in before] == [8765, 1234, -5678]
    assert [event.phase_degrees for event in before] == [90, 10, 20]
    assert [item.duration_us for item in editor.configured_spec().effective_composite_items if item.kind == "delay"] == [3, 7]
    editor.amplitude_mode_group.setChecked(True)
    after = editor.configured_spec()
    assert [event.gain for event in after.pulse_events] == [8765, 1234, -5678]
    assert [event.phase_degrees for event in after.pulse_events] == [90, 10, 20]
    assert len({item.amplitude_parameter for item in after.composite_items if item.kind == "pulse"}) == 2
    editor.load_settings(editor.settings_dict())
    assert editor.configured_spec() == after


def test_manual_calibration_mode_keeps_separate_parameter_banks(editor):
    editor.amplitude_mode_group.setChecked(True)
    selector = editor.composite_item_table.cellWidget(0, 5)
    row = parameter_row(editor, "amplitude", selector.currentData())
    table = editor.amplitude_parameter_table
    table.cellWidget(row, 1).setValue(1234)
    table.cellWidget(row, 3).setValue(-1000)
    table.cellWidget(row, 4).setValue(1000)
    table.cellWidget(row, 5).setValue(3)
    table.cellWidget(row, 2).setChecked(True)
    manual = editor._numeric_parameters("amplitude")
    editor.amplitude_calibration_enabled.setChecked(True)
    assert editor._amplitude_mode == "calibration"
    assert table.cellWidget(row, 1).value() == -20
    assert not table.cellWidget(row, 2).isChecked()
    table.cellWidget(row, 1).setValue(-35)
    editor.global_calibration_database_path.setText("missing-offline-calibration.db")
    editor.global_calibration_run_id.setValue(12)
    saved = editor.settings_dict()
    assert saved["global_calibration_database_path"] == "missing-offline-calibration.db"
    assert saved["global_calibration_run_id"] == 12
    editor.amplitude_calibration_enabled.setChecked(False)
    assert editor._numeric_parameters("amplitude") == manual
    editor.amplitude_calibration_enabled.setChecked(True)
    assert table.cellWidget(row, 1).value() == -35
    editor.load_settings(saved)
    assert editor.settings_dict() == saved


@pytest.mark.parametrize("kind,axis_kind", [("amplitude", "rf_amplitude"), ("phase", "rf_phase")])
def test_named_parameter_sweep_atomic_rename_and_roundtrip(editor, kind, axis_kind):
    editor.amplitude_mode_group.setChecked(True)
    selector = editor.composite_item_table.cellWidget(0, 5 if kind == "amplitude" else 7)
    row = parameter_row(editor, kind, selector.currentData())
    table = getattr(editor, f"{kind}_parameter_table")
    for column, value in ((3, -90), (4, 90), (5, 3)):
        table.cellWidget(row, column).setValue(value)
    table.cellWidget(row, 2).setChecked(True)
    spec = editor.configured_spec()
    axes = [axis for axis in spec.software_sweep_axes if axis.axis_kind == axis_kind]
    assert len(axes) == 1 and tuple(axes[0].points) == (-90, 0, 90)
    name = table.cellWidget(row, 0)
    name.setText("renamed")
    assert editor.configured_spec() == spec
    name.editingFinished.emit()
    assert selector.currentData() == "renamed"
    saved = editor.settings_dict()
    editor.load_settings(saved)
    assert editor.settings_dict() == saved


@pytest.mark.parametrize("template", ["custom", "hahn_echo"])
def test_previous_global_format_preserves_waveform_on_custom_conversion(editor, template):
    select(editor.predefined_template, "hahn_echo")
    editor.t2_initial_pi2.setChecked(True)
    editor.t2_final_pi2.setChecked(True)
    editor._add_frequency_parameter(QickRfFrequencyParameterSpec("shared", 123))
    saved = editor.settings_dict()
    saved.update(predefined_template=template, global_frequency_parameter="shared", global_gain=4321)
    editor.load_settings(saved)
    select(editor.predefined_template, "custom")
    spec = editor.configured_spec()
    assert [event.frequency_mhz for event in spec.pulse_events] == [123] * 3
    assert [event.gain for event in spec.pulse_events] == [4321] * 3
    assert [event.duration_us for event in spec.pulse_events] == [1, 2, 1]
    assert spec.global_frequency_parameter == "" and spec.global_gain is None


@pytest.mark.parametrize("frequency,gain", [("f1", None), ("", 4321)])
def test_legacy_independent_global_sentinels(editor, frequency, gain):
    saved = editor.settings_dict()
    saved.update(global_frequency_parameter=frequency, global_gain=gain)
    saved["frequency_parameters"] += [asdict(QickRfFrequencyParameterSpec("f1", 135))]
    saved["composite_items"] = [
        asdict(QickRfCompositeItemSpec("pulse", "first", 2, "f0", gain=1234, duration_parameter="d0")),
        asdict(QickRfCompositeItemSpec("pulse", "second", 2, "f1", gain=-2345, duration_parameter="d0")),
    ]
    editor.load_settings(saved)
    events = editor.configured_spec().pulse_events
    assert [event.gain for event in events] == ([1234, -2345] if gain is None else [4321, 4321])
    assert [event.frequency_mhz for event in events] == ([135, 135] if frequency else [50, 135])


def test_multiple_delay_reload_and_delete_preserve_actual_timing(editor):
    saved = editor.settings_dict()
    saved["delay_parameters"] = [asdict(QickRfDelayParameterSpec("zero", 0)), asdict(QickRfDelayParameterSpec("five", 5))]
    saved["composite_items"] = [
        asdict(QickRfCompositeItemSpec("delay", "wait", 0, delay_parameter="zero")),
        asdict(QickRfCompositeItemSpec("pulse", "after", 2, "f0", duration_parameter="d0")),
    ]
    editor.load_settings(saved)
    assert editor.configured_spec().pulse_events[0].delay_us == 0
    editor.delay_parameter_table.selectRow(0)
    editor._remove_delay_parameter()
    assert editor.configured_spec().pulse_events[0].delay_us == 0
    assert editor.composite_item_table.cellWidget(0, 8).currentData() == "zero_fixed"


def test_unicode_legacy_names_create_valid_distinct_parameter_names(editor):
    saved = editor.settings_dict()
    saved["composite_items"] = [
        asdict(QickRfCompositeItemSpec("delay", "대기", 3)),
        asdict(QickRfCompositeItemSpec("pulse", "π pulse", 2, "f0", phase_degrees=45, duration_parameter="d0")),
    ]
    editor.load_settings(saved)
    event = editor.configured_spec().pulse_events[0]
    assert event.delay_us == 3 and event.phase_degrees == 45


def test_new_custom_to_preset_and_back_has_expected_amplitude_controls(editor):
    editor.amplitude_mode_group.setChecked(True)
    select(editor.predefined_template, "hahn_echo")
    assert editor._amplitude_mode == "legacy"
    assert not editor.global_gain.isHidden()
    editor.global_gain.setValue(4321)
    editor.t2_initial_pi2.setChecked(True)
    select(editor.predefined_template, "custom")
    spec = editor.configured_spec()
    assert spec.global_amplitude_mode == "manual"
    assert [event.gain for event in spec.pulse_events] == [4321, 4321]
    assert editor.composite_item_table.cellWidget(1, 5).isEnabled()
    assert editor.t2_duration_parameter.currentText() == "d0/2"
