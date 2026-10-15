"""Regression extrapolation, power selection, hardware tables, and GUI checks."""

import json
from pathlib import Path

import numpy as np
import pytest

from calibration_gui import CalibrationPanel
from input_power_estimate import OutputGainRegression
from power_calibration import CalibrationDatabase, CalibrationRunSummary, GainPowerCalibration
from qick_power_calibration import InputPowerCalibrationConfig, prepare_input_power_plan, run_input_power_calibration
from qick_qcodes_experiment import QickConnectionConfig
from qick_sparameter_sweep import SParameterSweepResult, build_sparameter_program
from test_qick_power_calibration import _application, _create_output_calibration, _FakeSoc
from test_qick_sparameter_sweep import _mock_soccfg


def _model(slope=1.08, count=5):
    gains = np.geomspace(2000, 16000, count)
    summary = CalibrationRunSummary(Path("test.db"), 1, 1, "RF_Out", "RF_Out", "result", 190, 200, 2, 2 * count)
    curves = {f: (gains, slope * 20 * np.log10(gains / 32767) - 10 - (f - 190) / 10) for f in (190.0, 200.0)}
    return GainPowerCalibration(summary, curves)


def test_regression_predicts_unmeasured_low_gains_and_interpolated_frequency():
    calibration = _model()
    fit = OutputGainRegression(calibration)
    frequencies = np.array([190., 195., 200.])
    gains = np.array([10, 100, 1000])
    powers = fit.output_power_dbm(frequencies, gains, output_att1_db=3, output_att2_db=2)
    expected = 1.08 * 20 * np.log10(gains / 32767) - 10 - (frequencies - 190) / 10 - 5
    np.testing.assert_allclose(powers, expected, atol=1e-12)
    np.testing.assert_array_equal(fit.gains_for_power(frequencies, powers, output_att1_db=3, output_att2_db=2), gains)
    assert any("extrapolate" in text for text in fit.warnings(frequencies, gains))
    assert not any("extrapolate" in text for text in fit.warnings(195, 4000))
    assert all(item["r_squared"] == 1.0 for item in fit.fits)
    # Existing calibrated power users keep the original amplitude model.
    assert not np.allclose(calibration.output_power_dbm(frequencies, gains), fit.output_power_dbm(frequencies, gains))


def test_regression_does_not_fit_low_gain_noise_floor():
    calibration = _model()
    for f, (g, p) in calibration._curves.items():
        calibration._curves[f] = (np.r_[1, 5, 10, g], np.r_[-45, -45, -45, p])
    fit = OutputGainRegression(calibration)
    assert fit.fits[0]["point_count"] == 5
    assert fit.fits[0]["slope"] == pytest.approx(1.08)


@pytest.mark.parametrize("slope,count", [(0, 5), (-1, 5), (1, 1)])
def test_impossible_regression_is_not_silently_used(slope, count):
    with pytest.raises(ValueError):
        OutputGainRegression(_model(slope, count))


def test_regression_limits_and_two_point_warning():
    model = OutputGainRegression(_model(count=2))
    assert any("two points" in text for text in model.warnings(190, 3000))
    with pytest.raises(ValueError, match="coverage"):
        model.output_power_dbm(189, 1000)
    with pytest.raises(ValueError, match="DAC gain range"):
        model.gains_for_power(190, 40)
    with pytest.raises(ValueError, match="DAC gain range"):
        model.gains_for_power(190, -200)


@pytest.mark.parametrize("source", ["fir_ddr", "avg_buffer"])
@pytest.mark.parametrize("power_mode", [False, True])
def test_regression_calibration_acquires_selected_gains_and_stores_provenance(tmp_path, monkeypatch, source, power_mode):
    path, output = _create_output_calibration(tmp_path, monkeypatch)
    config = InputPowerCalibrationConfig(
        str(path), frequency_start_mhz=400, frequency_end_mhz=420, frequency_points=3,
        gain_start=100, gain_end=900, gain_points=3, use_gain_regression=True,
        power_sweep_enabled=power_mode, power_start_dbm=-65, power_end_dbm=-45, power_points=3,
        output_att1_db=2, path_loss_db=3, acquisition_source=source, settle_seconds=0,
    )
    preview = prepare_input_power_plan(config)
    soccfg = _mock_soccfg()
    for channel in (soccfg["gens"][0], soccfg["readouts"][0]):
        channel["f_dds"] = 1200.0
        channel["fs_mult"] = 4
    captured = []
    expected_slopes = np.array([1., 1.05, 1.1])
    expected_intercepts = np.array([-60., -61., -62.])

    def acquire(_soc, program):
        program.compile()
        assert program.binprog
        gains = program._expanded_gain_codes() if power_mode else np.full(3, program.sweep.gain)
        captured.append(gains)
        if power_mode:
            assert any("calibrated gain" in str(instruction) for instruction in program.prog_list)
        fit = preview["regression"]
        known = fit.output_power_dbm(program.frequencies_mhz, gains, output_att1_db=2) - 3
        adc = (known - expected_intercepts) / expected_slopes
        iq = np.zeros((3, 1, 2))
        iq[:, 0, 0] = 10 ** (adc / 20)
        return SParameterSweepResult.from_iq(
            program.frequencies_mhz, program.frequencies_mhz, iq,
            acquisition_source=source, integration_time_us=config.scan_time_us,
        )

    progress = []
    stored = run_input_power_calibration(
        connection_config=QickConnectionConfig(host="127.0.0.1"), calibration_config=config,
        connector=lambda **kwargs: (_FakeSoc(), soccfg), program_factory=build_sparameter_program,
        acquisition_callback=acquire, progress_callback=lambda percent, msg: progress.append((percent, msg)),
    )
    applied = np.asarray(captured)
    np.testing.assert_array_equal(stored.result["gain_codes"], applied)
    np.testing.assert_array_equal(applied, preview["gain_codes"])
    np.testing.assert_allclose(stored.result["slopes"], expected_slopes, atol=1e-10)
    np.testing.assert_allclose(stored.result["intercepts_dbm"], expected_intercepts, atol=1e-9)
    assert any("extrapolate" in msg for _, msg in progress)
    assert [p for p, _ in progress] == sorted(p for p, _ in progress)
    metadata = json.loads(stored.dataset.get_metadata("Calibration_Config"))["output_power_estimation"]
    assert metadata["model"] == "gain_regression"
    np.testing.assert_array_equal(metadata["gain_codes"], applied)
    data = stored.dataset.get_parameter_data("meas_in_pwr")["meas_in_pwr"]
    np.testing.assert_array_equal(data["gain"].reshape(applied.shape), applied)
    np.testing.assert_allclose(data["meas_in_pwr"].reshape(applied.shape), np.asarray(metadata["output_power_dbm"]) - 3)
    loaded = CalibrationDatabase(path).input_calibration("RF_In", [400, 410, 420], run_id=stored.run_id)
    assert loaded.summary.source_output_run_id == output.run_id
    if power_mode:
        assert np.any(applied[:, 0] != applied[:, -1])
        # Integer gain quantization is recorded as achieved power, not the target.
        assert np.max(np.abs(np.asarray(metadata["output_power_dbm"]) - config.target_powers_dbm[:, None])) < 0.1
    stored.dataset.conn.close()


def test_gain_power_gui_preview_warning_selection_and_settings(tmp_path, monkeypatch):
    app = _application()
    path, _ = _create_output_calibration(tmp_path, monkeypatch)
    panel = CalibrationPanel()
    panel.database_path.setText(str(path))
    panel.input_frequency_start.setValue(400)
    panel.input_frequency_end.setValue(420)
    panel.input_frequency_points.setValue(3)
    panel.input_power_start.setValue(-65)
    panel.input_power_end.setValue(-45)
    panel.input_power_points.setValue(3)
    panel.input_sweep_mode.setCurrentIndex(1)
    assert panel.input_gain_regression.isChecked()
    assert not panel.input_gain_start.isEnabled()
    panel.check_input_output_power.click()
    app.processEvents()
    assert "extrapolate" in panel.input_output_power_status.text()
    assert panel.run_input_button.isEnabled()
    plot = panel.input_output_power_plot
    assert len(plot.displayed_series) == 3
    np.testing.assert_array_equal(plot.displayed_series[-1][0], plot.plan["gain_codes"][:, 0])
    plot.frequency_selector.setCurrentIndex(2)
    np.testing.assert_array_equal(plot.displayed_series[-1][0], plot.plan["gain_codes"][:, 2])
    assert plot.plot_item is not None
    restored = CalibrationPanel()
    restored.load_settings(panel.settings_dict())
    assert restored.input_config() == panel.input_config()
    restored.load_settings({"database_path": str(path)})
    assert not restored.input_config().power_sweep_enabled
    assert not restored.input_config().use_gain_regression
    panel.input_power_end.setValue(-46)
    assert not plot.isEnabled()
    panel.prepare_input_output_power()
    panel.set_running(True, "Running")
    assert not panel.check_input_output_power.isEnabled()
    assert not panel.input_power_end.isEnabled()
    panel.set_running(False, "Ready")
    assert panel.input_power_end.isEnabled()
    panel.close()
    restored.close()


def test_power_plan_rejects_duplicate_gain_codes(tmp_path, monkeypatch):
    path, _ = _create_output_calibration(tmp_path, monkeypatch)
    config = InputPowerCalibrationConfig(str(path), frequency_start_mhz=400, frequency_end_mhz=420,
        power_sweep_enabled=True, power_start_dbm=-65, power_end_dbm=-64.999, power_points=3)
    with pytest.raises(ValueError, match="duplicate"):
        prepare_input_power_plan(config)
