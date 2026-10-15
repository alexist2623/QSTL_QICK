"""Wrapped/unwrapped phase, optional persistence, and legacy DB compatibility."""
import json
import os
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np
import pytest
from PyQt5 import QtWidgets

import qick_sparameter_sweep as sweep
from qick_qcodes_experiment import QcodesRunConfig, QickConnectionConfig, QCODES_STAGING_ENV


def response(*, source="fir_ddr", gain=100):
    angle = np.radians([170.0, -170.0, -160.0])
    iq = np.stack((np.cos(angle), np.sin(angle)), axis=-1)[:, None, :] * gain
    return sweep.SParameterSweepResult.from_iq(
        [189, 190, 191], [189, 190, 191], iq,
        acquisition_source=source, integration_time_us=4.0 if source == "avg_buffer" else None,
        accumulation_repetitions=10 if source == "avg_buffer" else 1,
    )


def test_wrapped_phase_comes_from_iq_and_keeps_undefined_points():
    result = response()
    np.testing.assert_allclose(result.phase_wrapped_deg, [170, -170, -160])
    np.testing.assert_allclose(result.phase_unwrapped_deg, [170, 190, 200])
    # Changing the unwrapped display array cannot change the I/Q-derived phase.
    altered = replace(result, phase_unwrapped_deg=np.zeros(3))
    np.testing.assert_allclose(altered.phase_wrapped_deg, [170, -170, -160])
    combined = sweep.SParameterPowerSweepResult.from_sweeps([100, 200], [result, result])
    np.testing.assert_allclose(combined.phase_wrapped_deg, [[170, -170, -160]] * 2)
    np.testing.assert_allclose(
        sweep.wrapped_phase_degrees([0, 0, np.nan, np.inf, -1], [0, 1, 1, 1, 0]),
        [np.nan, 90, np.nan, np.nan, 180], equal_nan=True,
    )


@pytest.mark.parametrize("save", [False, True])
@pytest.mark.parametrize("power_sweep", [False, True])
@pytest.mark.parametrize("source", ["fir_ddr", "avg_buffer"])
def test_run_save_switch_and_both_phase_parameters(tmp_path, monkeypatch, save, power_sweep, source):
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging"))
    path = tmp_path / "new_directory" / "results.db"
    config = sweep.SParameterSweepConfig(
        frequency_start_mhz=189, frequency_end_mhz=191, frequency_points=3,
        power_sweep_enabled=power_sweep, power_points=2, power_start_gain=100,
        power_end_gain=200, acquisition_source=source, save_to_qcodes=save,
        phase_display="wrapped", settle_seconds=0,
    )
    class Program:
        def __init__(self, config):
            self.config = config
        def acquire_iq(self, soc, counter_progress=None):
            return response(source=source, gain=self.config.gain)
        def summary(self):
            return {"gain": self.config.gain}
    monkeypatch.setattr(sweep, "configure_sparameter_rf_board", lambda *a: {"output": {}, "readout": {}})
    monkeypatch.setattr(sweep, "build_sparameter_program", lambda cfg, config, **k: Program(config))
    if not save:
        def forbidden(*args, **kwargs):
            pytest.fail("DB writer invoked while saving was disabled")
        monkeypatch.setattr(sweep, "store_sparameter_result", forbidden)
        monkeypatch.setattr(sweep, "_SParameterPowerRunWriter", forbidden)
    partial = []
    stored = sweep.run_sparameter_sweep(
        connection_config=QickConnectionConfig("192.0.2.1"), sweep_config=config,
        run_config=QcodesRunConfig(str(path)) if save else None,
        connector=lambda **k: (object(), object()), partial_callback=partial.append,
    )
    assert len(partial) == (2 if power_sweep else 0)
    expected = [[170, -170, -160]] * 2 if power_sweep else [170, -170, -160]
    np.testing.assert_allclose(stored.result.phase_wrapped_deg, expected)
    if not save:
        assert stored.run_id is None and stored.database_path is None and stored.dataset is None
        assert not path.parent.exists() and not (tmp_path / "staging").exists()
        assert all(item.run_id is None for item in partial)
        return
    dataset = stored.dataset
    for name, values in (
        (sweep.PHASE_WRAPPED_DEG_PARAMETER, stored.result.phase_wrapped_deg),
        (sweep.PHASE_DEG_PARAMETER, stored.result.phase_unwrapped_deg),
    ):
        actual = dataset.get_parameter_data(name)[name][name]
        np.testing.assert_allclose(np.asarray(actual).reshape(-1), values.reshape(-1))
    payload = json.loads(dataset.get_metadata("sparameter_result_json"))
    np.testing.assert_allclose(payload["phase_wrapped_deg"], expected)
    loaded = sweep.load_sparameter_run(path, stored.run_id).result
    np.testing.assert_array_equal(loaded.iq_traces, stored.result.iq_traces)
    np.testing.assert_allclose(loaded.phase_wrapped_deg, stored.result.phase_wrapped_deg)
    np.testing.assert_allclose(loaded.phase_unwrapped_deg, stored.result.phase_unwrapped_deg)


def test_legacy_database_without_wrapped_phase_can_still_load(tmp_path):
    from qcodes import Measurement, Parameter, initialise_or_create_database_at, load_or_create_experiment
    path = tmp_path / "legacy.db"
    initialise_or_create_database_at(str(path))
    measurement = Measurement(exp=load_or_create_experiment("legacy", "phase"))
    frequency = Parameter(sweep.FREQUENCY_PARAMETER)
    i_trace, q_trace = Parameter(sweep.I_TRACE_PARAMETER), Parameter(sweep.Q_TRACE_PARAMETER)
    measurement.register_parameter(frequency)
    for parameter in (i_trace, q_trace):
        measurement.register_parameter(parameter, setpoints=(frequency,), paramtype="array")
    result = response()
    with measurement.run() as saver:
        saver.dataset.add_metadata("sparameter_result_json", json.dumps({
            "frequencies_mhz": result.frequencies_mhz.tolist(),
            "phase_unwrapped_deg": result.phase_unwrapped_deg.tolist(),
            "sample_rate_hz": 1e6,
        }))
        for index, freq in enumerate(result.frequencies_mhz):
            saver.add_result((frequency, freq), (i_trace, result.iq_traces[index, :, 0]),
                             (q_trace, result.iq_traces[index, :, 1]))
    loaded = sweep.load_sparameter_run(path, saver.dataset.run_id).result
    np.testing.assert_allclose(loaded.phase_wrapped_deg, [170, -170, -160])
    np.testing.assert_allclose(loaded.phase_unwrapped_deg, [170, 190, 200])


def test_gui_phase_toggle_settings_and_unsaved_result():
    import DCWaveform_Generator as gui
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = gui.MainWindow()
    panel, plot = window._sparameter_panel, window._sparameter_plot
    try:
        result = response()
        plot.set_result(result)
        np.testing.assert_allclose(plot._phase_display, [[170, 190, 200]])
        panel.phase_display.setCurrentIndex(panel.phase_display.findData("wrapped"))
        np.testing.assert_allclose(plot._phase_display, [[170, -170, -160]])
        assert not plot.phase_subtract_button.isEnabled()
        plot.subtract_phase_fit()
        np.testing.assert_allclose(plot._phase_display, [[170, -170, -160]])
        curve = plot._phase_curves[0]
        actual = curve.getData()[1] if hasattr(curve, "getData") else curve.get_ydata()
        np.testing.assert_allclose(actual, [170, -170, -160])
        panel.save_to_qcodes.setChecked(False)
        panel.database_path.clear()
        arguments = window._sparameter_run_arguments()
        assert arguments["run_config"] is None
        payload = window._settings_to_dict()
        decoded = window._decode_settings(payload)
        window._apply_decoded_settings(decoded)
        assert not panel.save_to_qcodes.isChecked()
        assert panel.phase_display.currentData() == "wrapped"
        assert panel.database_path.text() == ""
        unsaved = sweep.StoredSParameterSweep(None, "", None, 0, result)
        window._on_sparameter_partial(unsaved)
        window._on_sparameter_finished(unsaved)
        assert "saving off" in panel.status.text()
        assert "Run None" not in panel.status.text()
        np.testing.assert_allclose(plot._phase_display, [[170, -170, -160]])
        panel.phase_display.setCurrentIndex(panel.phase_display.findData("unwrapped"))
        np.testing.assert_allclose(plot._phase_display, [[170, 190, 200]])
        assert plot.phase_subtract_button.isEnabled()
        old_settings = {"database_path": str(__file__) + ".db"}
        panel.load_settings(old_settings)
        assert panel.save_to_qcodes.isChecked()
        assert panel.phase_display.currentData() == "unwrapped"
    finally:
        window.close()
        app.processEvents()


def test_matplotlib_fallback_supports_phase_selection(monkeypatch):
    import builtins
    import importlib.util
    import sparameter_gui
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    original_import = builtins.__import__
    def without_pyqtgraph(name, *args, **kwargs):
        if name == "pyqtgraph":
            raise ImportError("Exercise the supported Matplotlib fallback")
        return original_import(name, *args, **kwargs)
    spec = importlib.util.spec_from_file_location("_phase_matplotlib_test", sparameter_gui.__file__)
    module = importlib.util.module_from_spec(spec)
    with monkeypatch.context() as context:
        context.setattr(builtins, "__import__", without_pyqtgraph)
        spec.loader.exec_module(module)
    plot = module.SParameterPlotWidget()
    try:
        plot.set_result(response())
        plot.set_phase_display("wrapped")
        np.testing.assert_allclose(plot._phase_curves[0].get_ydata(), [170, -170, -160])
        assert plot.phase_plot.get_ylabel() == "Wrapped phase [deg]"
        assert not plot.phase_subtract_button.isEnabled()
        plot.set_phase_display("unwrapped")
        np.testing.assert_allclose(plot._phase_curves[0].get_ydata(), [170, 190, 200])
    finally:
        plot._span_selector.disconnect_events()
        for callbacks in list(plot.canvas.callbacks.callbacks.values()):
            for callback_id in list(callbacks):
                plot.canvas.mpl_disconnect(callback_id)
        plot.figure.clear()
        plot.close()
        plot.deleteLater()
        from PyQt5 import QtCore
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
        app.processEvents()


@pytest.mark.parametrize("values", [{"phase_display": "invalid"}, {"save_to_qcodes": "false"}])
def test_invalid_new_settings_are_rejected(values):
    with pytest.raises((ValueError, TypeError)):
        sweep.SParameterSweepConfig(**values)
