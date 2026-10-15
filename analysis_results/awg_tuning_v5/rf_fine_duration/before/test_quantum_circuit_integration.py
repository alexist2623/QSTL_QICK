"""MainWindow circuit integration, persistence and asynchronous Run/Stop wiring.

The worker executes a controlled fake at the execution-bridge boundary.  These
tests never connect to QICK, compile a hardware program or create a database.
"""
import copy
import json
import sys
import threading
from types import SimpleNamespace

import pytest
from PyQt5 import QtCore, QtWidgets

import DCWaveform_Generator as gui
from dc_waveform_core import QickHoldDurationSweepSpec
from quantum_circuit_model import default_document, validate_document
from test_square_awg_exclusion import window


def circuit():
    result = default_document()
    result["shots"] = 9
    result["qubits"].append({"id": "q2", "name": "Spin 2"})
    result["gates"] = [
        {"id": "init", "name": "Init", "qubits": ["q1", "q2"],
         "start_us": 0., "duration_us": 3.,
         "awg": [{"channel": 1, "mode": "absolute", "value_mv": 10., "ramp_us": .5}],
         "rf": [], "acquisition": None},
        {"id": "read", "name": "Readout", "qubits": ["q1", "q2"],
         "start_us": 3., "duration_us": 4.,
         "awg": [{"channel": 1, "mode": "relative", "value_mv": -2., "ramp_us": 0.}],
         "rf": [{"channel": 1, "delay_us": .5, "duration_us": 1.,
                 "frequency_mhz": 150., "phase_deg": 90., "gain": 1500}],
         "acquisition": {"delay_us": 1., "duration_us": 2.}},
    ]
    return validate_document(result)


def enable_readout(window):
    settings = window._rf_readout_panel.settings_dict()
    settings.update(enabled=True, segment_name="set_0")
    window._rf_readout_panel.load_settings(settings)


def configure(window):
    window._quantum_circuit_panel.load_document(circuit())
    enable_readout(window)
    return window._quantum_circuit_panel


def wait_until(condition, timeout_ms=5000):
    timer = QtCore.QElapsedTimer()
    timer.start()
    app = QtWidgets.QApplication.instance()
    while not condition():
        assert timer.elapsed() < timeout_ms, "Qt worker did not complete within the test timeout"
        app.processEvents(QtCore.QEventLoop.AllEvents, 10)
        QtCore.QThread.msleep(2)
    app.processEvents(QtCore.QEventLoop.AllEvents, 10)


def install_bridge(monkeypatch, function):
    monkeypatch.setitem(sys.modules, "quantum_circuit_execution", SimpleNamespace(
        run_quantum_circuit_experiment=function))


def test_loop_sweep_settings_round_trip_and_run_ignores_preview_selection(window, tmp_path):
    from test_quantum_circuit_loops import loop_document
    document = loop_document(3, sweep=dict(start=0, stop=4, step=2))
    panel = window._quantum_circuit_panel
    panel.load_document(document)
    enable_readout(window)
    panel.preview_combo.setCurrentIndex(2)
    assert window._quantum_circuit_view._document['loops'][0]['count'] == 4
    arguments = window._quantum_circuit_run_arguments()
    assert arguments['document']['loops'][0]['count'] == 3
    assert arguments['document']['loops'][0]['sweep'] == dict(start=0, stop=4, step=2)
    path = tmp_path / 'loops.json'
    window._save_settings_json(path)
    panel.delete_loop('loop1')
    window._load_settings_json(path)
    assert panel.document() == validate_document(document)


def test_loop_view_edit_signal_opens_same_loop_in_panel(window, monkeypatch):
    from test_quantum_circuit_loops import loop_document
    from quantum_circuit_widgets import LoopEditor
    panel = window._quantum_circuit_panel
    panel.load_document(loop_document(3))
    def accept_edit(dialog):
        dialog.count_spin.setValue(7)
        dialog.accept()
        return dialog.result()
    monkeypatch.setattr(LoopEditor, 'exec_', accept_edit)
    window._quantum_circuit_view.loop_edit_requested.emit('loop1')
    assert panel.document()['loops'][0]['count'] == 7


def test_circuit_tab_appended_and_view_tabifies_with_results(window):
    tabs = window._control_tabs
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "AWG Tuning", "Stability Diagram", "RF S-Parameter", "Calibration",
        "Noise Analysis", "Bias", "Square Wave", "Quantum Circuit"]
    assert tabs.widget(tabs.count() - 1) is window._quantum_circuit_panel
    assert window._dock_quantum_circuit.widget() is window._quantum_circuit_view
    assert window._dock_quantum_circuit in window.tabifiedDockWidgets(window._dock_trace)
    assert window._dock_quantum_circuit not in window.tabifiedDockWidgets(window._dock_plot)
    tabs.setCurrentWidget(window._quantum_circuit_panel)
    assert not window._dock_quantum_circuit.isHidden()


def test_all_control_tabs_keep_circuit_and_result_views_accessible(window):
    docks = (window._dock_trace, window._dock_stability, window._dock_awg_sweep,
             window._dock_sparameter, window._dock_noise, window._dock_quantum_circuit)
    window.show()
    app = QtWidgets.QApplication.instance()
    # Start at Circuit, then visit every control tab and return to Circuit.
    tabs = window._control_tabs
    for index in [tabs.count() - 1, *range(tabs.count())]:
        tabs.setCurrentIndex(index)
        app.processEvents()
        assert all(not dock.isHidden() for dock in docks)
        assert not window._dock_plot.isHidden()
        # Each right-hand view remains selectable, including Circuit when
        # another control tab is selected and result plots within Circuit.
        for dock in docks:
            dock.raise_()
            app.processEvents()
            assert not dock.visibleRegion().isEmpty(), dock.windowTitle()


def test_settings_round_trip_preserves_existing_waveforms_sweeps_and_rf(window, tmp_path):
    window._pulse[0].edit_flat(0, 10000.)
    window._sweep_specs = [QickHoldDurationSweepSpec("set_0", 10., 20., 7)]
    rf_settings = list(window._rf_ports_panel.settings())
    rf_settings[0].update(enabled=True, segment_name="set_0", phase_deg=45.)
    window._rf_ports_panel.load_settings(rf_settings)
    configure(window)
    window._control_tabs.setCurrentWidget(window._quantum_circuit_panel)
    saved = window._settings_to_dict()
    assert saved["version"] == 45
    path = tmp_path / "circuit_settings.json"
    window._save_settings_json(path)
    window._quantum_circuit_panel.load_document(default_document())
    window._sweep_specs = []
    window._pulse[0].edit_flat(0, 2000.)
    window._load_settings_json(path)
    restored = window._settings_to_dict()
    for field in ("quantum_circuit", "awg", "qick", "rf_outputs", "rf_readout", "experiment"):
        assert restored[field] == saved[field], field
    assert window._control_tabs.currentWidget() is window._quantum_circuit_panel


@pytest.mark.parametrize("selected_name", ["Experiment", "SquarePulse"])
def test_v43_without_circuit_loads_empty_default_and_restores_tab_by_name(window, tmp_path, selected_name):
    original = window._settings_to_dict()
    original["version"] = 43
    original.pop("quantum_circuit")
    original["display"]["selected_control_tab"] = 0
    original["display"]["selected_awg_tuning_tab_name"] = selected_name
    original["display"]["selected_awg_tuning_tab"] = 0  # Name wins over a stale index.
    path = tmp_path / "v43_settings.json"
    path.write_text(json.dumps(original), encoding="utf-8")
    window._quantum_circuit_panel.load_document(circuit())
    window._load_settings_json(path)
    assert window._quantum_circuit_panel.document() == default_document()
    tabs = window._awg_tuning_tabs
    assert tabs.tabText(tabs.currentIndex()) == selected_name
    assert window._control_tabs.currentWidget() is window._awg_tuning_page


def test_invalid_circuit_json_is_rejected_before_existing_state_mutates(window, tmp_path):
    configure(window)
    before = window._settings_to_dict()
    invalid = copy.deepcopy(before)
    invalid["quantum_circuit"]["gates"][0]["qubits"] = ["missing_qubit"]
    invalid["experiment"]["sample_name"] = "MUST NOT APPLY"
    invalid["qick"]["repetitions_per_sweep"] = 123
    path = tmp_path / "invalid_circuit.json"
    path.write_text(json.dumps(invalid), encoding="utf-8")
    previous_path = window._settings_path
    with pytest.raises(ValueError, match="unknown qubit"):
        window._load_settings_json(path)
    assert window._settings_to_dict() == before
    assert window._settings_path == previous_path


def test_run_arguments_snapshot_does_not_replace_awg_state(window):
    configure(window)
    window._sweep_specs = [QickHoldDurationSweepSpec("set_0", 10., 20., 5)]
    before = window._settings_to_dict()
    arguments = window._quantum_circuit_run_arguments()
    assert arguments["document"] == circuit()
    assert arguments["readout_template"] == window._rf_readout_panel.spec()
    assert tuple(arguments["awg_channel_map"]) == gui.DEFAULT_QSTL_AWG_CHANNELS
    assert tuple(arguments["rf_channel_map"]) == gui.DEFAULT_QSTL_RF_CHANNELS
    assert arguments["gui_settings"] == before
    assert window._settings_to_dict() == before
    arguments["document"]["gates"][0]["awg"][0]["value_mv"] = 999.
    arguments["gui_settings"]["quantum_circuit"]["shots"] = 100
    assert window._quantum_circuit_panel.document() == circuit()
    assert window._settings_to_dict() == before


def test_circuit_rf_uses_configured_front_panel_path_without_enabling_old_rf_editor(window):
    configure(window)
    editor = window._rf_ports_panel._panels[0]
    settings = editor.settings_dict()
    settings.update(enabled=False, att1_db=7.5, att2_db=12.)
    editor.load_settings(settings)
    assert not editor.isChecked()
    expected = editor.configured_spec()
    arguments = window._quantum_circuit_run_arguments()
    assert arguments["rf_templates"] == (expected,)
    assert arguments["rf_templates"][0].att1_db == 7.5
    assert arguments["rf_templates"][0].att2_db == 12.
    assert not editor.isChecked()


def test_run_rejects_empty_circuit_and_disabled_readout_before_starting_thread(window, monkeypatch):
    warnings = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", lambda *args: warnings.append(args[2]))
    window._run_quantum_circuit()
    assert "Add and configure gates" in warnings[-1]
    assert window._experiment_thread is None
    window._quantum_circuit_panel.load_document(circuit())
    window._rf_readout_panel.setChecked(False)
    window._run_quantum_circuit()
    assert "RF Readout" in warnings[-1]
    assert window._experiment_thread is None


def test_execution_settings_signal_selects_existing_experiment_controls(window):
    window._control_tabs.setCurrentWidget(window._quantum_circuit_panel)
    window._quantum_circuit_panel.execution_settings_requested.emit()
    assert window._control_tabs.currentWidget() is window._awg_tuning_page
    assert window._awg_tuning_tabs.currentWidget() is window._experiment_panel


def test_async_run_worker_progress_success_and_duplicate_run_guard(window, monkeypatch, tmp_path):
    panel = configure(window)
    calls, info, detached = [], [], []
    entered, release = threading.Event(), threading.Event()
    main_thread = threading.get_ident()
    result = SimpleNamespace(run_id=71, database_path=str(tmp_path / "fake.db"), rf_settings={},
                             row_count=18, detach_dataset=lambda: detached.append(threading.get_ident()))

    def fake_run(**kwargs):
        calls.append((threading.get_ident(), kwargs))
        kwargs["progress_callback"](35, "mock acquisition")
        kwargs["event_callback"]("acquire", "started", "mock acquisition started")
        entered.set()
        while not release.wait(.01):
            kwargs["cancel_check"]()
        return result

    install_bridge(monkeypatch, fake_run)
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *args: info.append(args[2]))
    try:
        panel.run_button.click()
        wait_until(entered.is_set)
        wait_until(lambda: window._experiment_panel.progress.value() == 35)
        assert "mock acquisition" in panel.status_label.text()
        assert panel.stop_button.isEnabled() and not panel.run_button.isEnabled()
        window._run_quantum_circuit()
        assert len(info) == 1 and "current QICK operation" in info[0]
        window._run_qick_experiment()
        assert len(info) == 2 and "current QICK experiment" in info[1]
        assert len(calls) == 1 and calls[0][0] != main_thread
        assert calls[0][1]["document"] == circuit()
        release.set()
        wait_until(lambda: window._experiment_thread is None)
        assert window._last_circuit_result is result
        assert detached == [calls[0][0]]
        assert "Run 71 saved" in panel.status_label.text()
        assert panel.run_button.isEnabled() and not panel.stop_button.isEnabled()
        assert not (tmp_path / "fake.db").exists()
    finally:
        release.set()
        if window._experiment_thread is not None:
            wait_until(lambda: window._experiment_thread is None)


def test_async_worker_failure_is_reported_and_controls_recover(window, monkeypatch):
    panel = configure(window)
    dialogs = []

    def fake_run(**kwargs):
        raise ValueError("Mock timing validation failed")

    install_bridge(monkeypatch, fake_run)
    monkeypatch.setattr(gui.DetailedErrorMessageBox, "exec_", lambda self: dialogs.append(self.windowTitle()))
    panel.run_button.click()
    wait_until(lambda: window._experiment_thread is None)
    assert "Mock timing validation failed" in panel.status_label.text()
    assert dialogs == ["QICK experiment failed"]
    assert panel.run_button.isEnabled() and not panel.stop_button.isEnabled()


def test_async_stop_signal_requests_cooperative_worker_cancellation(window, monkeypatch):
    panel = configure(window)
    entered = threading.Event()
    release = threading.Event()

    def fake_run(**kwargs):
        entered.set()
        while not release.wait(.01):
            kwargs["cancel_check"]()
        raise AssertionError("Test released worker without cancellation")

    install_bridge(monkeypatch, fake_run)
    try:
        panel.run_button.click()
        wait_until(entered.is_set)
        panel.stop_button.click()
        wait_until(lambda: window._experiment_thread is None)
        assert "stopped by user" in panel.status_label.text()
        assert panel.run_button.isEnabled() and not panel.stop_button.isEnabled()
        assert window._experiment_panel.run_status.text().startswith("Stopped:")
    finally:
        if window._experiment_worker is not None:
            window._experiment_worker.request_cancel()
        if window._experiment_thread is not None:
            wait_until(lambda: window._experiment_thread is None)
        release.set()
