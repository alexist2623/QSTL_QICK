"""Regression coverage for waveform drag feedback and RF label placement."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PyQt5 import QtCore, QtGui, QtWidgets

import DCWaveform_Generator as gui
from dc_waveform_core import PulseSequence
from dc_waveform_widgets import RfPulseTimelineWidget, WaveformPlotWidget


_APP = None


@pytest.fixture
def app():
    global _APP
    _APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _APP


@pytest.fixture
def plot(app):
    pulse = PulseSequence(initial_voltage=100.0, initial_duration_ns=1000.0)
    pulse.add_flat_ramp(500.0, 1000.0, -50.0)
    widget = WaveformPlotWidget(pulse)
    widget.resize(800, 360)
    widget.show()
    widget.setXRange(-100.0, 2800.0, padding=0.0)
    widget.setYRange(-400.0, 400.0, padding=0.0)
    app.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()


def _mouse(plot, event_type, x, y, *, button=QtCore.Qt.NoButton,
           buttons=QtCore.Qt.NoButton):
    """Send a real Qt pointer event through the viewport event filter."""
    scene_position = plot.getPlotItem().vb.mapViewToScene(QtCore.QPointF(x, y))
    local_position = plot.mapFromScene(scene_position)
    global_position = plot.viewport().mapToGlobal(local_position)
    event = QtGui.QMouseEvent(
        event_type,
        QtCore.QPointF(local_position),
        QtCore.QPointF(global_position),
        button,
        buttons,
        QtCore.Qt.NoModifier,
    )
    QtWidgets.QApplication.sendEvent(plot.viewport(), event)


def _press(plot, kind="flat"):
    x = 500.0 if kind == "flat" else 1000.0
    _mouse(plot, QtCore.QEvent.MouseButtonPress, x, 100.0,
           button=QtCore.Qt.LeftButton, buttons=QtCore.Qt.LeftButton)
    assert (plot._drag_flat if kind == "flat" else plot._drag_point) is not None


def _move(plot, kind="flat", *, second=False, buttons=QtCore.Qt.LeftButton):
    x = 500.0 if kind == "flat" else (1350.0 if second else 1200.0)
    y = (230.0 if second else 160.0) if kind == "flat" else 100.0
    _mouse(plot, QtCore.QEvent.MouseMove, x, y, buttons=buttons)
    return x, y


def _release(plot, position=(500.0, 160.0)):
    _mouse(plot, QtCore.QEvent.MouseButtonRelease, *position,
           button=QtCore.Qt.LeftButton)


def _assert_finished(plot):
    assert plot._drag_flat is None
    assert plot._drag_point is None
    assert not plot._annotation.isVisible()
    assert plot.cursor().shape() not in {
        QtCore.Qt.SizeHorCursor, QtCore.Qt.SizeVerCursor,
    }


@pytest.mark.parametrize("kind", ["flat", "point"])
def test_drag_continues_across_base_preview_refresh_and_cleans_up_on_release(plot, kind):
    _press(plot, kind)
    _move(plot, kind)
    assert plot._annotation.isVisible()
    pulse = plot._pulses[0]
    first_value = float(pulse.v[0] if kind == "flat" else pulse.t[1])

    # MainWindow refreshes this base preview while the mouse is still held.
    plot.set_virtual_preview()
    position = _move(plot, kind, second=True)
    second_value = float(pulse.v[0] if kind == "flat" else pulse.t[1])
    assert second_value > first_value
    assert plot._annotation.isVisible()

    _release(plot, position)
    _assert_finished(plot)


def test_release_clears_feedback_even_if_another_refresh_already_cleared_drag_state(plot):
    _press(plot)
    _move(plot)
    assert plot._annotation.isVisible()
    plot._drag_flat = None
    plot._drag_point = None

    _release(plot)

    _assert_finished(plot)


@pytest.mark.parametrize("transition", ["sweep_preview", "physical_view"])
def test_changing_to_a_noneditable_view_cancels_drag_and_feedback(plot, transition):
    _press(plot)
    _move(plot)
    pulse = plot._pulses[0]
    before = pulse.v.copy()

    if transition == "sweep_preview":
        plot.set_virtual_preview(pulse.t, np.asarray([pulse.v]))
    else:
        plot.set_voltage_view("physical")

    _assert_finished(plot)
    _move(plot, second=True)
    np.testing.assert_array_equal(pulse.v, before)
    assert not plot._annotation.isVisible()
    _release(plot)


def test_leaving_viewport_hides_feedback_without_interrupting_a_held_drag(plot):
    _press(plot)
    _move(plot)
    before = plot._pulses[0].v.copy()

    QtWidgets.QApplication.sendEvent(plot.viewport(), QtCore.QEvent(QtCore.QEvent.Leave))

    assert not plot._annotation.isVisible()
    assert plot._drag_flat is not None
    position = _move(plot, second=True)
    assert plot._pulses[0].v[0] > before[0]
    assert plot._annotation.isVisible()
    _release(plot, position)
    _assert_finished(plot)


@pytest.mark.parametrize("interruption", ["hide", "window_deactivate", "ungrab_mouse"])
def test_hiding_or_deactivating_the_plot_cancels_a_drag(plot, interruption):
    _press(plot)
    _move(plot)
    before = plot._pulses[0].v.copy()

    if interruption == "hide":
        plot.hide()
    elif interruption == "ungrab_mouse":
        QtWidgets.QApplication.sendEvent(
            plot.viewport(), QtCore.QEvent(QtCore.QEvent.UngrabMouse))
    else:
        QtWidgets.QApplication.sendEvent(
            plot, QtCore.QEvent(QtCore.QEvent.WindowDeactivate))

    _assert_finished(plot)
    plot.show()
    _move(plot, second=True)
    np.testing.assert_array_equal(plot._pulses[0].v, before)
    assert not plot._annotation.isVisible()


@pytest.mark.parametrize("kind", ["flat", "point"])
def test_move_without_left_button_recovers_a_lost_release_without_editing(plot, kind):
    _press(plot, kind)
    _move(plot, kind)
    pulse = plot._pulses[0]
    before_times, before_voltages = pulse.t.copy(), pulse.v.copy()

    _move(plot, kind, second=True, buttons=QtCore.Qt.NoButton)

    _assert_finished(plot)
    np.testing.assert_array_equal(pulse.t, before_times)
    np.testing.assert_array_equal(pulse.v, before_voltages)


def test_view_switch_from_drag_callback_does_not_restore_cancelled_feedback(plot):
    plot.flat_moved.connect(lambda *_args: plot.set_voltage_view("physical"))
    _press(plot)

    _move(plot)

    _assert_finished(plot)
    assert plot.voltage_view == "physical"


@pytest.mark.parametrize("selected_port", [0, 1])
def test_main_window_voltage_drag_updates_selected_hold_table_and_run_sequence(app, selected_port):
    window = gui.MainWindow()
    try:
        window._pulse[0].add_flat_ramp(500.0, 1000.0, -100.0)
        window._add_port()
        other_port = 1 - selected_port
        assert window._pulse[other_port].edit_voltage(0, -75.0)
        window._port_select(selected_port)
        window._multi_ctrl.refresh_table()
        window._refresh_physical_waveforms()
        window.resize(1500, 950)
        window.show()
        window._dock_plot.show()
        window._dock_plot.raise_()
        plot = window._plot
        plot.setXRange(-100.0, 2800.0, padding=0.0)
        plot.setYRange(-400.0, 400.0, padding=0.0)
        app.processEvents()
        original_times = [pulse.t.copy() for pulse in window._pulse]
        original_voltages = [pulse.v.copy() for pulse in window._pulse]
        assert plot.get_selected_port_idx() == selected_port

        # The HOLD middle selects voltage editing, while its ends edit time.
        _press(plot)
        assert plot._drag_point is None
        _move(plot)
        assert window._pending_table_refresh
        first_voltage = float(window._pulse[selected_port].v[0])
        assert first_voltage > original_voltages[selected_port][0]

        # Deterministically execute the real timer callback between mouse moves.
        window._refresh_timer.stop()
        window._flush_deferred_refresh()
        selected_table = window._multi_ctrl._ctrl_pannels[selected_port].table
        assert float(selected_table.item(0, 4).text()) == pytest.approx(
            first_voltage, rel=1.0e-5)
        position = _move(plot, second=True)

        final_voltage = float(window._pulse[selected_port].v[0])
        assert final_voltage > first_voltage
        assert plot._annotation.isVisible()
        _release(plot, position)
        _assert_finished(plot)
        window._refresh_timer.stop()
        window._flush_deferred_refresh()

        for index, pulse in enumerate(window._pulse):
            np.testing.assert_array_equal(pulse.t, original_times[index])
            expected_voltages = original_voltages[index].copy()
            if index == selected_port:
                expected_voltages[:2] = final_voltage
            np.testing.assert_array_equal(pulse.v, expected_voltages)
            table = window._multi_ctrl._ctrl_pannels[index].table
            for row, value in enumerate(expected_voltages[::2]):
                assert float(table.item(row, 4).text()) == pytest.approx(value, rel=1.0e-5)

        sequence = window._experiment_run_arguments(
            require_readout=False, require_run_config=False)["sequence"]
        expected_amplitudes = np.asarray([
            pulse.v[0] / sequence.output_full_scales_mv[index]
            for index, pulse in enumerate(window._pulse)
        ])
        np.testing.assert_allclose(sequence.amplitudes_at(0, 0), expected_amplitudes)
    finally:
        window._refresh_timer.stop()
        window.close()
        window.deleteLater()
        app.processEvents()


@pytest.mark.parametrize("frequency_mhz, mode", [(1.0, "carrier"), (250.0, "envelope")])
def test_rf_names_stay_centered_inside_pulses_at_minimum_lane_height(app, frequency_mhz, mode):
    timeline = RfPulseTimelineWidget()
    pulses = [
        {"pulse_name": "prepare", "start_ns": 100.0, "duration_ns": 900.0,
         "frequency_mhz": frequency_mhz, "gain": 12000, "phase_degrees": 0.0},
        {"pulse_name": "read", "start_ns": 1200.0, "duration_ns": 900.0,
         "frequency_mhz": frequency_mhz, "gain": 9000, "phase_degrees": 90.0},
    ]
    try:
        timeline.resize(800, timeline.minimumHeight())
        timeline.set_pulses(gen_ch=0, pulses=pulses, att1_db=0.0, att2_db=0.0)
        timeline.setXRange(0.0, 2300.0, padding=0.0)
        timeline.show()
        app.processEvents()

        assert timeline.height() == timeline.minimumHeight()
        assert timeline.preview_mode == mode
        view_box = timeline.getPlotItem().vb
        for pulse, label in zip(pulses, timeline._pulse_labels):
            assert label.textItem.toPlainText() == pulse["pulse_name"]
            assert label.pos().x() == pulse["start_ns"] + pulse["duration_ns"] / 2.0
            assert label.pos().y() == 0.0
            assert (label.anchor.x(), label.anchor.y()) == (0.5, 0.5)
            label_rect = label.sceneBoundingRect()
            assert view_box.sceneBoundingRect().contains(label_rect)
            pulse_rect = QtCore.QRectF(
                view_box.mapViewToScene(QtCore.QPointF(pulse["start_ns"], pulse["gain"])),
                view_box.mapViewToScene(QtCore.QPointF(
                    pulse["start_ns"] + pulse["duration_ns"], -pulse["gain"])),
            ).normalized()
            assert pulse_rect.contains(label_rect)
    finally:
        timeline.close()
        timeline.deleteLater()
        app.processEvents()
