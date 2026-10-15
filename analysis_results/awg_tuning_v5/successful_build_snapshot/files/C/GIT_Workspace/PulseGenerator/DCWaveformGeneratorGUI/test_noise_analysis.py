"""Noise-analysis numerical and headless GUI tests.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

import os
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt5 import QtWidgets
import pytest

import noise_analysis as noise_module
from dc_voltage_calibration import DcVoltageCalibration
from noise_analysis import (
    DEFAULT_NOISE_ANALYSIS_SETTINGS,
    NoiseAnalysisConfig,
    NoiseAnalysisPanel,
    NoiseTraceCollection,
    analyze_i_trace,
    normalize_noise_analysis_settings,
)


def _application():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_voltage_trace_is_divided_by_transimpedance_gain():
    sample_rate = 100_000.0
    sample_count = 10_000
    frequency = 10_000.0
    time = np.arange(sample_count) / sample_rate
    expected_current = 2.5e-9 * np.sin(2.0 * np.pi * frequency * time)
    voltage_trace = expected_current * 1.0e8

    result = analyze_i_trace(
        voltage_trace,
        NoiseAnalysisConfig(
            input_mode="voltage",
            transimpedance_gain_v_per_a=1.0e8,
            sample_rate_hz=sample_rate,
            window="flattop",
        ),
    )

    np.testing.assert_allclose(result.current_a, expected_current, atol=1.0e-20)
    peak_index = int(np.argmax(result.asd_a_per_sqrt_hz[1:]) + 1)
    assert abs(result.frequency_hz[peak_index] - frequency) <= (
        sample_rate / sample_count
    )
    assert result.time_s[-1] == (sample_count - 1) / sample_rate


def test_adc_trace_uses_volts_per_unit_before_gain_conversion():
    adc_trace = np.asarray([0.0, 1000.0, -500.0, 250.0])
    result = analyze_i_trace(
        adc_trace,
        NoiseAnalysisConfig(
            input_mode="adc",
            input_scale_v_per_unit=2.0e-6,
            transimpedance_gain_v_per_a=1.0e6,
            sample_rate_hz=1.0e6,
            window="boxcar",
            detrend="none",
        ),
    )
    np.testing.assert_allclose(
        result.current_a,
        adc_trace * 2.0e-12,
    )


def test_noise_settings_fill_defaults_and_validate_modes():
    settings = normalize_noise_analysis_settings({"run_id": 7})
    assert settings["run_id"] == 7
    assert settings["window"] == "flattop"
    assert settings["transimpedance_gain_v_per_a"] == 1.0e8
    assert set(DEFAULT_NOISE_ANALYSIS_SETTINGS).issubset(settings)

    try:
        normalize_noise_analysis_settings({"input_mode": "magnitude"})
    except ValueError as exc:
        assert "input_mode" in str(exc)
    else:
        raise AssertionError("invalid noise-analysis input mode was accepted")


def test_latest_noise_run_skips_incompatible_database_runs(tmp_path):
    database_path = tmp_path / "mixed-runs.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE runs ("
            "run_id INTEGER PRIMARY KEY, qick_experiment_json TEXT)"
        )
        connection.executemany(
            "INSERT INTO runs(run_id, qick_experiment_json) VALUES (?, ?)",
            (
                (1, '{"measurement_layout": {}}'),
                (2, None),
                (3, ""),
                (4, '{"measurement_layout": {}}'),
                (5, None),
            ),
        )
    assert noise_module._latest_run_id(database_path) == 4

    incompatible_path = tmp_path / "other-runs.db"
    with sqlite3.connect(incompatible_path) as connection:
        connection.execute("CREATE TABLE runs (run_id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO runs(run_id) VALUES (9)")
    with pytest.raises(ValueError, match="no compatible QICK I-trace runs"):
        noise_module._latest_run_id(incompatible_path)


def test_noise_saved_run_loader_matches_sparameter_selection_flow():
    app = _application()
    panel = NoiseAnalysisPanel(default_database_path="saved-noise.db")
    panel.resize(720, 900)
    panel.show()
    app.processEvents()

    assert panel.run_id.specialValueText() == "Latest saved I-trace run"
    assert panel.load_button.text() == "Load Saved Run"
    assert abs(panel.run_id.geometry().center().y() - panel.load_button.geometry().center().y()) <= 2

    emitted = []
    panel.load_requested.connect(lambda path, run_id: emitted.append((path, run_id)))
    panel.run_id.setValue(17)
    panel.load_button.click()
    assert emitted == [("saved-noise.db", 17)]

    panel.set_loading(True, "Loading saved run")
    assert panel.run_id.isEnabled() is False
    assert panel.database_path.isEnabled() is False
    assert panel.browse_database.isEnabled() is False
    panel.set_loading(False)
    assert panel.run_id.isEnabled() is True
    assert panel.database_path.isEnabled() is True
    assert panel.browse_database.isEnabled() is True
    panel.close()


def test_noise_panel_selects_point_and_repetition_and_round_trips_settings():
    app = _application()
    panel = NoiseAnalysisPanel(default_database_path="noise.db")
    traces = np.arange(2 * 3 * 64, dtype=float).reshape(2, 3, 64)
    panel.set_collection(NoiseTraceCollection(
        i_traces=traces,
        sample_rate_hz=1.0e6,
        unit="V",
        source="test source",
        run_id=4,
        database_path="noise.db",
    ))
    panel.point_index.setValue(1)
    panel.repetition_index.setValue(2)
    panel.transimpedance_gain.setValue(1.0e7)
    panel.window.setCurrentText("hann")
    result = panel.analyze_selected_trace()

    assert result is not None
    np.testing.assert_allclose(
        result.input_trace,
        traces[1, 2],
    )
    settings = panel.settings_dict()
    restored = NoiseAnalysisPanel(default_database_path="other.db")
    restored.load_settings(settings)
    assert restored.settings_dict() == settings
    app.processEvents()
    panel.close()
    restored.close()


def test_noise_panel_direct_acquisition_settings_are_self_contained():
    app = _application()
    panel = NoiseAnalysisPanel(default_database_path="noise.db")
    panel.acquisition_host.setText("noise-only-host")
    panel.acquisition_port.setValue(9444)
    panel.acquisition_proxy.setText("noise-only-proxy")
    panel.readout_channel.setValue(3)
    panel.input_board.setCurrentText("DC_In")
    panel.input_nqz.setValue(2)
    panel.fir_samples.setValue(10_000_000)
    panel.readout_frequency.setValue(1.25)
    panel.input_dc_gain.setValue(8.0)
    emitted = []
    panel.acquire_requested.connect(emitted.append)
    panel.acquire_button.click()

    assert len(emitted) == 1
    config = emitted[0]
    assert config.connection_config.host == "noise-only-host"
    assert config.connection_config.ns_port == 9444
    assert config.connection_config.proxy_name == "noise-only-proxy"
    assert config.ro_ch == 3
    assert config.input_board_type == "DC_In"
    assert config.nqz == 2
    assert config.fir_samples == 10_000_000
    assert config.readout_frequency_mhz == 1.25
    assert config.dc_gain_db == 8.0
    assert panel.capture_duration.text() == "10 s at 1 MSPS"
    panel.sample_rate.setValue(50_000.0)
    assert panel.capture_duration.text() == "200 s at 50 kSPS"
    assert panel.database_path.text() == "noise.db"
    app.processEvents()
    panel.close()


def test_noise_panel_front_panel_preview_uses_control_panel_width():
    app = _application()
    panel = NoiseAnalysisPanel(default_database_path="noise.db")
    panel.resize(640, 900)
    panel.show()
    app.processEvents()

    viewport_width = panel._control_scroll.viewport().width()
    assert viewport_width - 48 <= panel.front_panel_preview.width() <= viewport_width
    assert panel.front_panel_preview.height() >= 180
    panel.close()


def test_noise_panel_front_panel_selection_updates_only_direct_input():
    app = _application()
    panel = NoiseAnalysisPanel(default_database_path="saved-traces.db")
    panel.database_path.setText("do-not-change.db")
    panel.apply_front_panel_settings({
        "readout_ch": 2,
        "input_board_type": "RF_In",
        "readout_nqz": 2,
        "readout_attenuation_db": 17.25,
        "readout_dc_gain_db": 3.0,
        "readout_filter_type": "highpass",
        "readout_filter_cutoff_ghz": 1.75,
        "readout_filter_bandwidth_ghz": 0.5,
    })

    assert panel.readout_channel.value() == 2
    assert panel.input_board.currentText() == "RF_In"
    assert panel.input_nqz.value() == 2
    assert panel.input_attenuation.value() == 17.25
    assert panel.input_filter.currentText() == "highpass"
    assert panel.filter_cutoff.value() == 1.75
    assert panel.database_path.text() == "do-not-change.db"
    assert panel.configured_spec().ro_ch == 2
    app.processEvents()
    panel.close()


def test_noise_panel_applies_dc_calibration_offset_before_current_conversion(
    monkeypatch,
    tmp_path,
):
    app = _application()
    calibration_path = tmp_path / "dc_calibration.db"
    calibration = DcVoltageCalibration(
        database_path=calibration_path,
        run_id=12,
        output_ch=1,
        readout_ch=2,
        input_dc_gain_db=6.0,
        voltage_min_mv=-800.0,
        voltage_max_mv=800.0,
        voltage_points=33,
        offset_adc=120.0,
        response_adc_per_v=400.0,
        rmse_adc=0.0,
        r_squared=1.0,
    )
    calls = []

    def fake_load(path, *, readout_ch, input_dc_gain_db, run_id):
        calls.append((str(path), readout_ch, input_dc_gain_db, run_id))
        return calibration

    monkeypatch.setattr(
        noise_module,
        "load_dc_voltage_calibration",
        fake_load,
    )
    adc_trace = 120.0 + 400.0 * np.linspace(-0.25, 0.25, 64)
    panel = NoiseAnalysisPanel(default_database_path="noise.db")
    panel.set_collection(NoiseTraceCollection(
        i_traces=adc_trace.reshape(1, 1, -1),
        sample_rate_hz=1.0e6,
        unit="ADC units",
        source="raw DC input",
    ))
    panel.transimpedance_gain.setValue(2.0)
    panel.dc_calibration_path.setText(str(calibration_path))
    panel.dc_calibration_run_id.setValue(12)
    panel.dc_calibration_readout_ch.setValue(2)
    panel.dc_calibration_input_gain.setValue(6.0)
    panel.dc_calibration_group.setChecked(True)
    result = panel.analyze_selected_trace()

    assert result is not None
    expected_voltage = (adc_trace - 120.0) / 400.0
    np.testing.assert_allclose(result.input_trace, expected_voltage)
    np.testing.assert_allclose(result.current_a, expected_voltage / 2.0)
    assert result.input_unit == "V (DC calibration Run 12)"
    assert "subtract offset 120" in panel.dc_calibration_status.text()
    assert calls[-1] == (str(calibration_path), 2, 6.0, 12)
    settings = panel.settings_dict()
    assert settings["dc_voltage_calibration_enabled"] is True
    restored = NoiseAnalysisPanel(default_database_path="other.db")
    restored.load_settings(settings)
    assert restored.settings_dict() == settings
    app.processEvents()
    panel.close()
    restored.close()


def test_noise_panel_does_not_double_calibrate_saved_voltage_trace(monkeypatch):
    app = _application()
    panel = NoiseAnalysisPanel(default_database_path="noise.db")
    panel.dc_calibration_path.setText("unused.db")
    panel.dc_calibration_group.setChecked(True)
    monkeypatch.setattr(
        noise_module,
        "load_dc_voltage_calibration",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("calibration loader must not be called")
        ),
    )
    voltage = np.linspace(-0.1, 0.1, 64)
    panel.set_collection(NoiseTraceCollection(
        i_traces=voltage.reshape(1, 1, -1),
        sample_rate_hz=1.0e6,
        unit="V",
        source="already calibrated",
    ))
    result = panel.analyze_selected_trace()

    assert result is not None
    np.testing.assert_allclose(result.input_trace, voltage)
    assert "already stored in V" in panel.dc_calibration_status.text()
    app.processEvents()
    panel.close()
