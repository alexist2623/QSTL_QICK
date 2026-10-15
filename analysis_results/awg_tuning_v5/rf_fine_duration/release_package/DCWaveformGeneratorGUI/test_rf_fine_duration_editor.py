"""Offline opt-in DAC-sample duration editor and persistence checks."""
from copy import deepcopy
from dataclasses import replace

import pytest
from PyQt5 import QtCore, QtWidgets

import DCWaveform_Generator as gui
from dc_waveform_core import QickRfPulseSpec


@pytest.fixture
def window():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    widget = gui.MainWindow()
    yield widget
    widget.close()
    widget.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    app.processEvents()


def panel_for(window, **settings):
    panel = window._rf_ports_panel._panels[0]
    panel.load_settings({**gui.DEFAULT_RF_OUTPUT_SETTINGS, "enabled": True,
                         "gain": 10000, **settings})
    return panel


def test_old_settings_keep_coarse_behavior_and_nyquist_hidden(window):
    old = deepcopy(gui.DEFAULT_RF_OUTPUT_SETTINGS)
    old.pop("fine_duration")
    panel = panel_for(window, **old)
    assert not panel.fine_duration.isChecked()
    assert panel.configured_spec().fine_duration is False
    assert panel.settings_dict()["fine_duration"] is False
    assert panel.nqz.isHidden()


@pytest.mark.parametrize("mode", ["single", "composite"])
def test_fine_flag_survives_both_json_decoders_clone_and_editor_reload(window, mode):
    panel = panel_for(window, pulse_mode=mode, fine_duration=True)
    expected = panel.configured_spec()
    assert expected.fine_duration is True
    saved = panel.settings_dict()
    panel.load_settings(deepcopy(saved))
    assert panel.settings_dict() == saved
    assert replace(expected, delay_us=0.123).fine_duration is True
    decoded = window._decode_rf_output_entries([saved], set_names={"set_0"}, label="RF test")[0]
    decoded.pop("enabled")
    assert QickRfPulseSpec(**decoded) == expected
    decoded = window._decode_settings(deepcopy(window._settings_to_dict()))["rf_outputs"][0]
    decoded.pop("enabled")
    assert QickRfPulseSpec(**decoded) == expected


def test_fine_flag_survives_preset_custom_and_single_mode_switches(window):
    panel = panel_for(window, pulse_mode="composite", fine_duration=True)
    panel.predefined_template.setCurrentIndex(panel.predefined_template.findData("hahn_echo"))
    panel.global_gain.setValue(10000)
    panel.t2_initial_pi2.setChecked(True)
    panel.t2_final_pi2.setChecked(True)
    panel.predefined_template.setCurrentIndex(panel.predefined_template.findData("custom"))
    spec = panel.configured_spec()
    assert spec.fine_duration and len(spec.pulse_events) == 3
    panel.single_mode.setChecked(True)
    assert panel.configured_spec().fine_duration
    panel.composite_mode.setChecked(True)
    assert panel.configured_spec().fine_duration


@pytest.mark.parametrize("named", [False, True])
def test_duration_sweeps_remain_hardware_axes_without_new_host_loop(window, named):
    panel = panel_for(window, pulse_mode="composite" if named else "single")
    if named:
        table = panel.duration_parameter_table
        table.cellWidget(0, 3).setValue(0.010000000)
        table.cellWidget(0, 4).setValue(0.013125000)
        table.cellWidget(0, 5).setValue(16)
        table.cellWidget(0, 2).setChecked(True)
    else:
        panel.duration_sweep_start.setValue(0.010000000)
        panel.duration_sweep_stop.setValue(0.013125000)
        panel.duration_sweep_count.setValue(16)
        panel.duration_sweep_enabled.setChecked(True)
    coarse = panel.configured_spec()
    panel.fine_duration.setChecked(True)
    fine = panel.configured_spec()
    assert fine.sweep_axes == coarse.sweep_axes
    assert len(fine.sweep_axes) == 1
    assert fine.sweep_axes[0].count == 16
    assert not fine.software_sweep_axes


def test_subnanosecond_duration_input_and_unit_changes_preserve_requested_value(window):
    panel = panel_for(window, fine_duration=True)
    panel.set_time_unit("ns")
    requested_ns = 50.0 + 1000.0 / (300.0 * 16.0)
    panel.duration.setValue(requested_ns)
    assert panel.configured_spec().duration_us * 1000 == pytest.approx(requested_ns, abs=1e-9)
    panel.set_time_unit("us")
    assert panel.configured_spec().duration_us * 1000 == pytest.approx(requested_ns, abs=1e-6)
    panel.composite_mode.setChecked(True)
    panel.set_time_unit("ns")
    panel.duration_parameter_table.cellWidget(0, 1).setValue(requested_ns)
    assert panel.configured_spec().pulse_events[0].duration_us * 1000 == pytest.approx(requested_ns, abs=1e-9)


@pytest.mark.parametrize("named", [False, True])
def test_all_sixteen_sample_endings_survive_widgets_json_and_hardware_axes(window, named):
    """Nine-decimal us controls must not ceil a rounded grid point one sample late."""
    from qick_rf_fine_duration import samples_from_us

    panel = panel_for(window, pulse_mode="composite" if named else "single",
                      fine_duration=True)
    panel.set_time_unit("us")
    for sample_count in range(81, 97):
        if named:
            table = panel.duration_parameter_table
            table.cellWidget(0, 1).setValue(sample_count / 4800.0)
        else:
            panel.duration.setValue(sample_count / 4800.0)
        saved = panel.settings_dict()
        panel.load_settings(deepcopy(saved))
        decoded = window._decode_rf_output_entries(
            [panel.settings_dict()], set_names={"set_0"}, label="RF sample test")[0]
        decoded.pop("enabled")
        restored = QickRfPulseSpec(**decoded)
        assert restored.fine_duration
        assert samples_from_us(restored.pulse_events[0].duration_us, 300.0) == sample_count

    if named:
        table = panel.duration_parameter_table
        table.cellWidget(0, 3).setValue(81 / 4800.0)
        table.cellWidget(0, 4).setValue(96 / 4800.0)
        table.cellWidget(0, 5).setValue(16)
        table.cellWidget(0, 2).setChecked(True)
    else:
        panel.duration_sweep_start.setValue(81 / 4800.0)
        panel.duration_sweep_stop.setValue(96 / 4800.0)
        panel.duration_sweep_count.setValue(16)
        panel.duration_sweep_enabled.setChecked(True)
    panel.load_settings(deepcopy(panel.settings_dict()))
    spec = panel.configured_spec()
    assert not spec.software_sweep_axes
    assert len(spec.sweep_axes) == 1
    axis = spec.sweep_axes[0]
    points = [axis.start + (axis.stop - axis.start) * index / (axis.count - 1)
              for index in range(axis.count)]
    assert [samples_from_us(value, 300.0) for value in points] == list(range(81, 97))


def test_duration_axis_label_preserves_distinct_sample_steps_on_long_pulses(window):
    panel = panel_for(window, fine_duration=True)
    panel.set_time_unit("us")
    panel.duration_sweep_start.setValue(1000.0)
    panel.duration_sweep_stop.setValue(1000.0 + 1 / 4800.0)
    panel.duration_sweep_count.setValue(2)
    panel.duration_sweep_enabled.setChecked(True)
    axis = panel.configured_spec().sweep_axes[0]
    text = gui.ExperimentPanel._sweep_axis_label(None, axis)
    assert "1000 to 1000.00020833 us" in text
    assert "2 points" in text


def test_tooltip_derives_only_known_clock_and_does_not_claim_rise_time(window):
    panel = panel_for(window)
    tooltip = panel.fine_duration.toolTip()
    assert "Current firmware example" in tooltip and "0.208333 ns" in tooltip
    assert "not analog rise time or start-time resolution" in tooltip
    assert "|gain| <= 16383" in tooltip
    assert "Calibrated gain is checked" in tooltip
    generators = [{} for _ in range(panel.gen_ch.value() + 1)]
    generators[panel.gen_ch.value()] = {"f_fabric": 250.0, "samps_per_clk": 8}
    panel.set_generator_timings(generators)
    assert "Selected generator duration step: 0.5 ns" in panel.fine_duration.toolTip()
    panel.set_generator_timings([])
    assert "Current firmware example" in panel.fine_duration.toolTip()


@pytest.mark.parametrize("invalid", [1, "true", None])
def test_fine_duration_rejects_nonboolean_settings(window, invalid):
    panel = panel_for(window)
    with pytest.raises(TypeError, match="fine_duration must be bool"):
        replace(panel.configured_spec(), fine_duration=invalid)
