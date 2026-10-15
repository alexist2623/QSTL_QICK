"""ADC units, logarithmic axes, marker values, and calibrated result display."""

import builtins
import importlib.util
from types import SimpleNamespace

import numpy as np
import pytest
from PyQt5 import QtCore, QtWidgets

import sparameter_gui
from qick_sparameter_sweep import SParameterSweepConfig, SParameterSweepResult, SParameterPowerSweepResult


@pytest.fixture(params=["pyqtgraph", "matplotlib"])
def plot(request, monkeypatch):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    module = sparameter_gui
    if request.param == "matplotlib":
        original_import = builtins.__import__
        def without_pyqtgraph(name, *args, **kwargs):
            if name == "pyqtgraph":
                raise ImportError("Test Matplotlib fallback")
            return original_import(name, *args, **kwargs)
        spec = importlib.util.spec_from_file_location("_magnitude_matplotlib", sparameter_gui.__file__)
        module = importlib.util.module_from_spec(spec)
        with monkeypatch.context() as context:
            context.setattr(builtins, "__import__", without_pyqtgraph)
            spec.loader.exec_module(module)
    widget = module.SParameterPlotWidget()
    widget.resize(1000, 700)
    widget.show()
    app.processEvents()
    yield widget
    if hasattr(widget, "figure"):
        widget._span_selector.disconnect_events()
        for callbacks in list(widget.canvas.callbacks.callbacks.values()):
            for callback_id in list(callbacks):
                widget.canvas.mpl_disconnect(callback_id)
        widget.figure.clear()
    widget.close()
    widget.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    app.processEvents()


def _result(scale, power):
    frequency = np.array([180., 185., 190., 195.])
    iq = np.array([[[0, 0]], [[3, 4]], [[12, -5]], [[30, 40]]], dtype=np.int64 if scale else np.int16)
    iq = iq * (2 ** scale)
    if power:
        return SParameterPowerSweepResult.from_iq([100, 1000], frequency, frequency,
            np.stack([iq, iq * 10]), iq_scale_log2=scale,
            actual_output_powers_dbm=np.full((2, 4), -30), input_powers_dbm=np.full((2, 4), -50))
    return SParameterSweepResult.from_iq(frequency, frequency, iq, iq_scale_log2=scale,
        actual_output_powers_dbm=np.full(4, -30), input_powers_dbm=np.full(4, -50))


@pytest.mark.parametrize("scale,power", [(0, False), (46, True)])
def test_adc_modes_preserve_iq_power_selection_phase_and_marker_units(plot, scale, power):
    app = QtWidgets.QApplication.instance()
    result = _result(scale, power)
    original_iq = result.iq_traces.copy()
    plot.set_result(result)
    if power:
        plot.power_selector.setCurrentIndex(2)
    expected = np.array([0., 5., 13., 50.]) * (10 if power else 1)
    selected = 1 if power else 0
    plot.subtract_phase_fit()
    phase_before = plot._phase_display.copy()
    fit_before = plot._phase_fit_applied
    plot.set_magnitude_display("adc_linear")
    np.testing.assert_allclose(plot._magnitude_values[selected], expected)
    assert "ADC units" in plot._marker_text("Magnitude", selected, 190, expected[2])
    plot.set_magnitude_display("adc_log")
    app.processEvents()
    assert np.isnan(plot._magnitude_values[selected, 0])
    curve = plot._magnitude_curves[0]
    if hasattr(curve, "getData"):
        np.testing.assert_allclose(curve.getData()[1][1:], np.log10(expected[1:]))
        coordinate = plot.magnitude_plot.vb.mapViewToScene(QtCore.QPointF(190, np.log10(expected[2])))
        plot._on_mouse_moved((coordinate,))
        event = SimpleNamespace(button=lambda: QtCore.Qt.LeftButton, scenePos=lambda: coordinate)
        plot._on_mouse_clicked(event)
        marker = plot._pinned_markers[-1][1]
        np.testing.assert_allclose(marker.getData()[1], [np.log10(expected[2])])
    else:
        assert plot.magnitude_plot.get_yscale() == "log"
        np.testing.assert_allclose(curve.get_ydata()[1:], expected[1:])
        event = SimpleNamespace(inaxes=plot.magnitude_plot, xdata=190, ydata=expected[2], button=1)
        plot._on_mouse_moved(event)
        plot._on_mouse_clicked(event)
        np.testing.assert_allclose(plot._pinned_markers[-1][0].get_ydata(), [expected[2]])
    assert f"Magnitude {expected[2]:g} ADC units" in plot.plot_status.text()
    plot.set_magnitude_display("adc_db")
    assert plot._pinned_markers == []
    np.testing.assert_allclose(plot._magnitude_values[selected, 1:], 20 * np.log10(expected[1:]))
    plot.set_magnitude_display("response_db")
    np.testing.assert_allclose(plot._magnitude_values, -20)
    np.testing.assert_array_equal(plot._phase_display, phase_before)
    assert plot._phase_fit_applied == fit_before
    plot.set_magnitude_display("adc_linear")
    plot.set_result(result)
    assert plot._magnitude_mode == "adc_linear"
    np.testing.assert_array_equal(result.iq_traces, original_iq)
    np.testing.assert_allclose(result.magnitude_db, -20)


def test_zero_adc_data_remains_zero_and_log_has_no_artificial_floor(plot):
    result = SParameterSweepResult.from_iq([190, 191], [190, 191], np.zeros((2, 1, 2), np.int16))
    plot.set_magnitude_display("adc_log")
    plot.set_result(result)
    assert np.isnan(plot._magnitude_values).all()
    plot.set_magnitude_display("adc_linear")
    np.testing.assert_array_equal(plot._magnitude_values, [[0, 0]])


def test_magnitude_selection_main_window_settings_and_old_defaults():
    import DCWaveform_Generator as gui
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = gui.MainWindow()
    panel, plot = window._sparameter_panel, window._sparameter_plot
    try:
        plot.set_result(_result(0, False))
        panel.magnitude_display.setCurrentIndex(panel.magnitude_display.findData("adc_log"))
        assert plot._magnitude_mode == "adc_log"
        settings = panel.settings_dict()
        panel.magnitude_display.setCurrentIndex(0)
        panel.load_settings(settings)
        assert plot._magnitude_mode == "adc_log"
        assert panel.config().magnitude_display == "adc_log"
        panel.load_settings({"database_path": "legacy.db"})
        assert panel.config().magnitude_display == "response_db"
        assert plot._magnitude_mode == "response_db"
    finally:
        window.close()
        app.processEvents()
    with pytest.raises(ValueError, match="magnitude_display"):
        SParameterSweepConfig(magnitude_display="invalid")
