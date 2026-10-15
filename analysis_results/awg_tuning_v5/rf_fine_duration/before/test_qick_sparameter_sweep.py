"""RF-only hardware S-parameter sweep, storage, and GUI tests.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

import json
import os
import sqlite3
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PyQt5 import QtCore, QtWidgets

# Desktop imports need the PYNQ stubs installed before regular QICK modules.
from qick.sim import QickSim  # noqa: F401
from qick.qick_asm import QickConfig

import DCWaveform_Generator as gui
import qick_sparameter_sweep as sparameter_module
import sparameter_gui as sparameter_gui_module
from sparameter_gui import nearest_sparameter_point, subtract_phase_linear_fit
from qick_qcodes_experiment import (
    QCODES_STAGING_ENV,
    QcodesRunConfig,
    QickConnectionConfig,
    _json_text,
)
from qick_sparameter_sweep import (
    CALIBRATED_GAIN_PARAMETER,
    MAGNITUDE_DB_PARAMETER,
    MAX_RF_OUTPUT_GAIN,
    POWER_GAIN_PARAMETER,
    SParameterPowerSweepResult,
    SParameterSweepConfig,
    SParameterSweepProgram,
    SParameterSweepResult,
    configure_sparameter_rf_board,
    load_sparameter_run,
    run_sparameter_sweep,
    store_sparameter_result,
)


def _application():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _mock_soccfg(
    *,
    generator_type="axis_signal_gen_v6",
    fir_rate_profile="1_msps",
):
    awg = generator_type == "axis_awg_tuning_v1"
    is_50_ksps = fir_rate_profile == "50_ksps"
    return QickConfig(
        {
            "sw_version": "0.2.357",
            "refclk_freq": 300.0,
            "tprocs": [
                {
                    "type": "axis_tproc64x32_x8",
                    "f_time": 300.0,
                    "pmem_size": 65536,
                    "dmem_size": 4096,
                    "output_pins": [],
                }
            ],
            "gens": [
                {
                    "type": generator_type,
                    "gen_type": "awg_tuning" if awg else "signal_generator",
                    "tproc_ch": 0,
                    "tmux_ch": 0,
                    "f_fabric": 300.0,
                    "f_dds": 300.0,
                    "fs_mult": 1,
                    "fs_div": 1,
                    "fdds_div": 1,
                    "samps_per_clk": 16,
                    "maxlen": 16384,
                    "maxv": 32764 if awg else 32766,
                    "maxv_scale": 1.0,
                    "complex_env": not awg,
                    "has_mixer": False,
                    "has_dds": not awg,
                    "b_dds": 32,
                    "b_phase": 32,
                    "dac": "00",
                    "interpolation": 1,
                    **(
                        {
                            "n_pts": 16,
                            "frac": 16,
                            "cmd_width": 160,
                            "step_width": 24,
                            "duration_width": 23,
                            "fixed_width": 48,
                        }
                        if awg
                        else {}
                    ),
                }
            ],
            "readouts": [
                {
                    "type": "axis_dyn_readout_v1",
                    "ro_type": "axis_dyn_readout_v1",
                    "tproc_ctrl": 1,
                    "tmux_ch": 0,
                    "f_fabric": 300.0,
                    "f_output": 300.0,
                    "f_dds": 300.0,
                    "fs_mult": 1,
                    "fs_div": 1,
                    "fdds_div": 1,
                    "b_dds": 32,
                    "b_phase": 32,
                    "adc": "00",
                    "buf_maxlen": 16384,
                    "has_weights": False,
                    "has_edge_counter": False,
                    "trigger_type": "dport",
                    "trigger_port": 0,
                    "trigger_bit": 0,
                }
            ],
            "ddr4_buf": {
                "sample_capture": True,
                "fir_enabled": True,
                "fir_rate_profile": fir_rate_profile,
                "stored_sample_rate_hz": (
                    50_000.0 if is_50_ksps else 1_000_000.0
                ),
                "fir_output_fs_mhz": 0.05 if is_50_ksps else 1.0,
                "fir_decimation": 6000 if is_50_ksps else 300,
                "fir_group_delay_input_samples": (
                    296_677.0 if is_50_ksps else 8677.0
                ),
                "fir_input_fs_mhz": 300.0,
                "supports_trigger_delay": is_50_ksps,
                "trigger_delay_units": (
                    "s_axis_aclk_cycles"
                    if is_50_ksps
                    else "valid_input_samples"
                ),
                "trigger_delay_default_cycles": 50 if is_50_ksps else 0,
                "trigger_delay_default_samples": 0,
                "trigger_type": "dport",
                "trigger_port": 0,
                "trigger_bit": 1,
            },
        }
    )


def _config(**updates):
    values = {
        "frequency_start_mhz": 10.0,
        "frequency_end_mhz": 20.0,
        "frequency_points": 11,
        "scan_time_us": 4.0,
        "minimum_coherent_samples": 1,
        "settle_seconds": 0.0,
    }
    values.update(updates)
    return SParameterSweepConfig(**values)


def _result():
    frequencies = np.asarray([10.0, 11.0, 12.0])
    iq = np.asarray(
        [
            [[3, 4], [3, 4], [3, 4], [3, 4]],
            [[-3, 1], [-3, 1], [-3, 1], [-3, 1]],
            [[-3, -1], [-3, -1], [-3, -1], [-3, -1]],
        ],
        dtype=np.int32,
    )
    return SParameterSweepResult.from_iq(frequencies, frequencies, iq)


def _power_result():
    frequencies = np.asarray([10.0, 11.0, 12.0])
    gains = np.asarray([1000, 2000, 3000])
    iq = np.zeros((gains.size, frequencies.size, 2, 2), dtype=float)
    for power_index in range(gains.size):
        iq[power_index, :, :, 0] = (
            10.0 * (power_index + 1) + np.arange(frequencies.size)
        )[:, np.newaxis]
    frequency_gain_codes = np.repeat(gains[:, np.newaxis], frequencies.size, axis=1)
    return SParameterPowerSweepResult.from_iq(
        gains,
        frequencies,
        frequencies,
        iq,
        output_powers_dbm=[-30.0, -20.0, -10.0],
        frequency_gain_codes=frequency_gain_codes,
    )


def test_result_uses_mean_iq_db_magnitude_and_unwrapped_phase():
    result = _result()

    expected_complex = result.mean_i + 1j * result.mean_q
    np.testing.assert_allclose(
        result.magnitude_db,
        20.0 * np.log10(np.abs(expected_complex)),
    )
    np.testing.assert_allclose(
        result.phase_unwrapped_deg,
        np.degrees(np.unwrap(np.angle(expected_complex))),
    )
    assert result.mean_i[0] == 3.0
    assert result.mean_q[0] == 4.0


def test_zero_mean_iq_is_unmeasurable_instead_of_minus_6000_db():
    frequencies = np.asarray([10.0, 11.0, 12.0, 13.0])
    iq = np.asarray(
        [
            [[1, 0], [1, 0]],
            [[4, -2], [-4, 2]],
            [[-1, 0], [-1, 0]],
            [[0, -1], [0, -1]],
        ],
        dtype=np.int32,
    )

    result = SParameterSweepResult.from_iq(frequencies, frequencies, iq)

    np.testing.assert_allclose(
        result.magnitude_db[[0, 2, 3]],
        [0.0, 0.0, 0.0],
    )
    assert np.isnan(result.magnitude_db[1])
    assert np.isnan(result.adc_magnitude_db[1])
    assert np.isnan(result.phase_unwrapped_deg[1])
    np.testing.assert_allclose(
        result.phase_unwrapped_deg[[0, 2, 3]],
        [0.0, 180.0, 270.0],
    )


def test_zero_mean_diagnostics_distinguish_empty_and_noisy_traces():
    frequencies = np.asarray([10.0, 11.0])
    iq = np.asarray(
        [
            [[0, 0], [0, 0]],
            [[5, -3], [-5, 3]],
        ],
        dtype=np.int32,
    )
    result = SParameterSweepResult.from_iq(frequencies, frequencies, iq)

    diagnostics = sparameter_module._response_diagnostics(result)

    assert diagnostics == {
        "zero_mean_iq_points": 2,
        "all_zero_fir_trace_points": 1,
        "nonzero_trace_zero_mean_points": 1,
        "other_nonfinite_response_points": 0,
    }


def test_strict_json_serialization_replaces_nested_nonfinite_values_with_null():
    payload = json.loads(
        _json_text(
            {
                "scalar": np.float64(np.nan),
                "array": np.asarray([1.0, np.inf, -np.inf, np.nan]),
            }
        )
    )

    assert payload == {"scalar": None, "array": [1.0, None, None, None]}


def test_power_sweep_zero_mean_iq_is_unmeasurable():
    frequencies = np.asarray([10.0, 11.0])
    gains = np.asarray([1000, 2000])
    iq = np.ones((2, 2, 2, 2), dtype=np.int32)
    iq[1, 0] = 0

    result = SParameterPowerSweepResult.from_iq(
        gains,
        frequencies,
        frequencies,
        iq,
    )

    assert np.isnan(result.magnitude_db[1, 0])
    assert np.isnan(result.phase_unwrapped_deg[1, 0])
    assert np.isfinite(result.magnitude_db[1, 1])


def test_phase_linear_fit_subtracts_each_trace_without_changing_shape():
    frequency = np.linspace(100.0, 110.0, 11)
    phase = np.vstack((2.5 * frequency + 30.0, -0.75 * frequency - 12.0))

    corrected, slopes, intercepts = subtract_phase_linear_fit(
        frequency,
        phase,
        102.0,
        108.0,
    )

    assert corrected.shape == phase.shape
    np.testing.assert_allclose(corrected, 0.0, atol=1.0e-10)
    np.testing.assert_allclose(slopes, [2.5, -0.75])
    np.testing.assert_allclose(intercepts, [30.0, -12.0])


def test_phase_linear_fit_ignores_unmeasurable_points():
    frequency = np.linspace(100.0, 110.0, 11)
    phase = 2.0 * frequency + 5.0
    phase[5] = np.nan

    corrected, slopes, intercepts = subtract_phase_linear_fit(
        frequency,
        phase,
        100.0,
        110.0,
    )

    assert np.isnan(corrected[5])
    np.testing.assert_allclose(corrected[np.isfinite(corrected)], 0.0, atol=1.0e-10)
    np.testing.assert_allclose(slopes, [2.0])
    np.testing.assert_allclose(intercepts, [5.0])


def test_nearest_marker_selects_frequency_and_closest_trace():
    frequency = np.asarray([100.0, 101.0, 102.0])
    values = np.asarray([[1.0, 2.0, 3.0], [10.0, 20.0, 30.0]])

    curve, point, selected_frequency, selected_value = nearest_sparameter_point(
        frequency,
        values,
        101.2,
        18.0,
    )

    assert (curve, point) == (1, 1)
    assert selected_frequency == 101.0
    assert selected_value == 20.0


def test_nearest_marker_skips_unmeasurable_points():
    frequency = np.asarray([100.0, 101.0, 102.0])
    values = np.asarray([[1.0, np.nan, 3.0], [10.0, np.nan, 30.0]])

    curve, point, selected_frequency, selected_value = nearest_sparameter_point(
        frequency,
        values,
        101.0,
        2.0,
    )

    assert (curve, point) == (0, 0)
    assert selected_frequency == 100.0
    assert selected_value == 1.0


def test_sparameter_plot_phase_fit_is_display_only_and_resettable():
    app = _application()
    frequency = np.linspace(10.0, 20.0, 11)
    original_phase = 4.0 * frequency + 7.0
    result = SimpleNamespace(
        frequencies_mhz=frequency,
        magnitude_db=np.linspace(-30.0, -20.0, frequency.size),
        phase_unwrapped_deg=original_phase.copy(),
        output_power_dbm=None,
        physical_power_calibrated=False,
    )
    plot = gui.SParameterPlotWidget()
    plot.resize(900, 600)
    plot.set_result(result)
    plot.show()
    app.processEvents()
    if hasattr(plot.magnitude_plot, "vb"):
        hover_position = plot.magnitude_plot.vb.mapViewToScene(
            QtCore.QPointF(15.1, -25.0)
        )
        plot._on_mouse_moved((hover_position,))
        app.processEvents()
        assert "MHz" in plot.plot_status.text()
        assert "Magnitude" in plot.plot_status.text()
        assert plot._hover_items["Magnitude"][0].isVisible()
    if hasattr(plot, "_phase_region"):
        plot._phase_region.setRegion((12.0, 18.0))
    else:
        plot._phase_fit_region = (12.0, 18.0)

    plot.subtract_phase_fit()
    app.processEvents()

    assert plot._phase_fit_applied is True
    np.testing.assert_allclose(plot._phase_display, 0.0, atol=1.0e-10)
    np.testing.assert_array_equal(result.phase_unwrapped_deg, original_phase)
    assert "deg/MHz" in plot.plot_status.text()

    plot.reset_phase()
    app.processEvents()
    assert plot._phase_fit_applied is False
    np.testing.assert_array_equal(plot._phase_display[0], original_phase)
    plot.close()


def test_sparameter_power_plot_uses_lines_and_can_select_one_power():
    app = _application()
    plot = gui.SParameterPlotWidget()
    plot.resize(900, 600)
    plot.set_result(_power_result())
    plot.show()
    app.processEvents()

    assert plot.power_selector.isEnabled()
    assert plot.power_selector.count() == 4
    assert plot.power_selector.itemText(0) == "All powers"
    assert plot.power_selector.itemText(2) == "-20 dBm"
    np.testing.assert_array_equal(plot._visible_curve_indices, [0, 1, 2])
    assert len(plot._magnitude_curves) == 3
    if hasattr(plot._magnitude_curves[0], "opts"):
        assert plot._magnitude_curves[0].opts.get("symbol") is None
    else:
        assert plot._magnitude_curves[0].get_marker() == "None"

    plot.power_selector.setCurrentIndex(2)
    app.processEvents()

    np.testing.assert_array_equal(plot._visible_curve_indices, [1])
    assert len(plot._magnitude_curves) == 1
    assert len(plot._phase_curves) == 1
    assert "-20 dBm" in plot.plot_status.text()
    if hasattr(plot._magnitude_curves[0], "opts"):
        assert plot._magnitude_curves[0].opts.get("symbol") is None
    else:
        assert plot._magnitude_curves[0].get_marker() == "None"

    plot.power_selector.setCurrentIndex(0)
    app.processEvents()
    np.testing.assert_array_equal(plot._visible_curve_indices, [0, 1, 2])
    assert len(plot._magnitude_curves) == 3
    plot.close()


def test_gain_has_hard_limit():
    assert SParameterSweepConfig(gain=MAX_RF_OUTPUT_GAIN).gain == 32766
    with pytest.raises(ValueError, match="must not exceed"):
        SParameterSweepConfig(gain=MAX_RF_OUTPUT_GAIN + 1)


def test_manual_input_calibration_requires_a_positive_run_id():
    with pytest.raises(ValueError, match="requires a Run ID"):
        _config(
            power_calibration_enabled=True,
            calibration_database_path="calibration.db",
            input_calibration_selection="manual_run_id",
        )


def test_power_calibration_manual_run_warns_on_input_attenuation_mismatch(
    monkeypatch,
):
    input_summary = SimpleNamespace(input_attenuation_db=10.0, run_id=73)
    input_calibration = SimpleNamespace(summary=input_summary)
    calls = []

    class FakeCatalog:
        def __init__(self, database_path):
            assert database_path == "calibration.db"

        def output_calibration(self, board_type, frequencies):
            del board_type, frequencies
            return SimpleNamespace(summary=SimpleNamespace(run_id=11))

        def input_calibration(self, board_type, frequencies, **kwargs):
            del board_type, frequencies
            calls.append(kwargs)
            return input_calibration

    probe = SimpleNamespace(frequencies_mhz=np.asarray([10.0, 20.0]))
    monkeypatch.setattr(sparameter_module, "CalibrationDatabase", FakeCatalog)
    monkeypatch.setattr(
        sparameter_module,
        "build_sparameter_program",
        lambda *_args, **_kwargs: probe,
    )
    messages = []
    config = _config(
        frequency_points=2,
        power_calibration_enabled=True,
        calibration_database_path="calibration.db",
        input_board_type="RF_In",
        readout_attenuation_db=20.0,
        input_calibration_selection="manual_run_id",
        requested_input_calibration_run_id=73,
    )

    *_, selected_input = sparameter_module._prepare_power_calibration(
        object(),
        config,
        tproc_mhz=None,
        warning_callback=messages.append,
    )

    assert selected_input is input_calibration
    assert calls == [{"run_id": 73}]
    assert len(messages) == 1
    assert "sweep 20 dB, calibration 10 dB" in messages[0]


def test_power_calibration_auto_mode_requests_same_input_attenuation(
    monkeypatch,
):
    calls = []

    class FakeCatalog:
        def __init__(self, _database_path):
            pass

        def output_calibration(self, board_type, frequencies):
            del board_type, frequencies
            return SimpleNamespace(summary=SimpleNamespace(run_id=11))

        def input_calibration(self, board_type, frequencies, **kwargs):
            del board_type, frequencies
            calls.append(kwargs)
            raise LookupError("no same-attenuation input run")

    probe = SimpleNamespace(frequencies_mhz=np.asarray([10.0, 20.0]))
    monkeypatch.setattr(sparameter_module, "CalibrationDatabase", FakeCatalog)
    monkeypatch.setattr(
        sparameter_module,
        "build_sparameter_program",
        lambda *_args, **_kwargs: probe,
    )
    messages = []
    config = _config(
        frequency_points=2,
        power_calibration_enabled=True,
        calibration_database_path="calibration.db",
        input_board_type="RF_In",
        readout_attenuation_db=20.0,
    )

    *_, selected_input = sparameter_module._prepare_power_calibration(
        object(),
        config,
        tproc_mhz=None,
        warning_callback=messages.append,
    )

    assert selected_input is None
    assert calls[0]["input_attenuation_db"] == 20.0
    assert len(messages) == 1
    assert "was not applied" in messages[0]


def test_sparameter_worker_forwards_calibration_warnings(monkeypatch):
    app = _application()
    stored = object()

    def fake_run_sparameter_sweep(**kwargs):
        kwargs["warning_callback"]("calibration attenuation mismatch")
        return stored

    monkeypatch.setattr(
        sparameter_gui_module,
        "run_sparameter_sweep",
        fake_run_sparameter_sweep,
    )
    worker = sparameter_gui_module.SParameterSweepWorker({})
    messages = []
    results = []
    worker.warning_raised.connect(messages.append)
    worker.finished.connect(results.append)

    worker.run()
    app.processEvents()

    assert messages == ["calibration attenuation mismatch"]
    assert results == [stored]


def test_power_gain_grid_supports_linear_and_log_spacing():
    linear = SParameterSweepConfig(
        power_sweep_enabled=True,
        power_start_gain=1000,
        power_end_gain=20000,
        power_points=5,
        power_scale="linear",
    )
    logarithmic = SParameterSweepConfig(
        power_sweep_enabled=True,
        power_start_gain=100,
        power_end_gain=10000,
        power_points=5,
        power_scale="log",
    )

    np.testing.assert_array_equal(
        linear.power_gains,
        [1000, 5750, 10500, 15250, 20000],
    )
    np.testing.assert_array_equal(
        logarithmic.power_gains,
        [100, 316, 1000, 3162, 10000],
    )
    with pytest.raises(ValueError, match="greater than zero"):
        SParameterSweepConfig(
            power_sweep_enabled=True,
            power_start_gain=0,
            power_end_gain=100,
            power_points=3,
            power_scale="log",
        )
    with pytest.raises(ValueError, match="duplicate integer gain"):
        SParameterSweepConfig(
            power_sweep_enabled=True,
            power_start_gain=1,
            power_end_gain=2,
            power_points=3,
            power_scale="linear",
        )


def test_program_is_fixed_size_hardware_sweep_and_updates_both_dds_registers():
    short = SParameterSweepProgram(_mock_soccfg(), _config(frequency_points=3))
    long = SParameterSweepProgram(_mock_soccfg(), _config(frequency_points=1001))
    short.compile()
    long.compile()

    assert len(short.prog_list) == len(long.prog_list)
    assert sum(inst["name"] == "math" for inst in long.prog_list) == 2
    assert sum(inst["name"] == "loopnz" for inst in long.prog_list) == 2
    assert long.summary()["sweep_execution"] == "tproc_hardware_register_add"
    assert long.summary()["awg_tuning_used"] is False
    assert long.scan_samples == 4
    assert long.loop_dims == [1001, 1]


def test_avg_buffer_program_works_without_fir_ddr_metadata():
    soccfg = _mock_soccfg()
    del soccfg._cfg["ddr4_buf"]
    program = SParameterSweepProgram(
        soccfg,
        _config(
            acquisition_source="avg_buffer",
            frequency_points=3,
            scan_time_us=4.0,
            avg_repetitions=7,
            avg_sweep_mode="hardware",
            avg_hardware_rep_delay_us=2.5,
        ),
    )
    program.compile()

    summary = program.summary()
    assert program.loop_dims == [3, 7]
    assert program.rounds == 1
    assert program.ro_chs[0]["trigs"] == 1
    assert program.avg_integration_samples == 1200
    assert program.ddr_trigger_time is None
    assert summary["acquisition_source"] == "avg_buffer"
    assert summary["avg_repetitions"] == 7
    assert summary["avg_sweep_mode"] == "hardware"
    assert summary["avg_hardware_rep_delay_tproc_cycles"] == 750
    assert summary["avg_integration_time_us"] == pytest.approx(4.0)
    assert summary["fir_rate_profile"] is None
    assert summary["fir_output_rate_msps"] is None


def test_avg_buffer_configuration_rejects_invalid_source_and_repetitions():
    with pytest.raises(ValueError, match="acquisition_source"):
        _config(acquisition_source="unknown")
    with pytest.raises(ValueError, match="avg_repetitions"):
        _config(acquisition_source="avg_buffer", avg_repetitions=0)
    with pytest.raises(ValueError, match="avg_sweep_mode"):
        _config(acquisition_source="avg_buffer", avg_sweep_mode="unknown")
    with pytest.raises(ValueError, match="avg_hardware_rep_delay_us"):
        _config(
            acquisition_source="avg_buffer",
            avg_hardware_rep_delay_us=-1.0,
        )


def test_avg_buffer_software_mode_repeats_complete_hardware_frequency_sweep():
    program = SParameterSweepProgram(
        _mock_soccfg(),
        _config(
            acquisition_source="avg_buffer",
            frequency_points=3,
            scan_time_us=4.0,
            avg_repetitions=7,
            avg_sweep_mode="software",
            avg_hardware_rep_delay_us=2.5,
        ),
    )
    program.compile()

    summary = program.summary()
    assert program.loop_dims == [3, 1]
    assert program.rounds == 7
    assert summary["avg_sweep_mode"] == "software"
    assert summary["avg_repetitions"] == 7
    assert summary["avg_hardware_rep_delay_tproc_cycles"] == 0
    assert summary["sweep_execution"] == "tproc_hardware_register_add"


def test_avg_buffer_acquisition_returns_one_iq_value_per_frequency(monkeypatch):
    program = SParameterSweepProgram(
        _mock_soccfg(),
        _config(
            acquisition_source="avg_buffer",
            frequency_points=3,
            scan_time_us=4.0,
            avg_repetitions=7,
        ),
    )
    progress_updates = []

    def fake_acquire(_program, _soc, *, progress=False, **_kwargs):
        assert progress is False
        return (
            np.asarray([10.0, 15.0, 20.0]),
            [np.asarray([[1.25, 2.5, 3.75]])],
            [np.asarray([[-4.0, -5.0, -6.0]])],
        )

    monkeypatch.setattr(sparameter_module.RAveragerProgram, "acquire", fake_acquire)
    result = program.acquire_avg_buffer(
        object(),
        counter_progress=lambda completed, total: progress_updates.append(
            (completed, total)
        ),
    )

    assert progress_updates == [(0, 21), (21, 21)]
    assert result.acquisition_source == "avg_buffer"
    assert result.accumulation_repetitions == 7
    assert result.integration_time_us == pytest.approx(4.0)
    assert result.iq_traces.shape == (3, 1, 2)
    np.testing.assert_allclose(result.mean_i, [1.25, 2.5, 3.75])
    np.testing.assert_allclose(result.mean_q, [-4.0, -5.0, -6.0])


def test_calibrated_program_reads_gain_table_from_dmem_and_compresses_addresses():
    gain_table = tuple(1000 + index for index in range(4000))
    config = _config(
        frequency_points=5001,
        frequency_start_mhz=10.0,
        frequency_end_mhz=20.0,
        power_calibration_enabled=True,
        calibration_database_path="calibration.db",
        output_power_dbm=-20.0,
        calibrated_gain_table=gain_table,
        calibrated_frequency_point_count=5001,
        calibrated_output_power_dbm=-20.0,
        calibrated_nominal_gain_code=5000,
        calibrated_reference_response_dbm=10.0,
        calibrated_correction_min_db=-1.0,
        calibrated_correction_max_db=0.0,
        calibration_output_run_id=31,
    )
    program = SParameterSweepProgram(_mock_soccfg(), config)
    program.compile()

    assert program.summary()["gain_source"] == "tproc_dmem_frequency_table"
    assert program.summary()["gain_dmem_entry_count"] == 4000
    assert program.summary()["gain_table_compressed"] is True
    assert sum(inst["name"] == "memr" for inst in program.prog_list) == 1
    assert any(
        inst["name"] == "condj"
        and "reuse adjacent calibrated gain" in inst.get("comment", "")
        for inst in program.prog_list
    )
    np.testing.assert_array_equal(
        program._expanded_gain_codes()[:4],
        [1000, 1000, 1001, 1002],
    )

    calls = []

    class FakeSoc:
        def reload_mem(self):
            calls.append(("reload",))

        def load_mem(self, data, mem_sel, addr):
            calls.append(("load", data, mem_sel, addr))

    program._load_runtime_dmem(FakeSoc())
    assert calls[0] == ("reload",)
    assert calls[1][2:] == ("dmem", 16)
    assert isinstance(calls[1][1], list)
    assert all(type(value) is int for value in calls[1][1])
    np.testing.assert_array_equal(calls[1][1], gain_table)


def test_program_quantizes_from_channel_metadata_when_refclk_is_missing():
    soccfg = _mock_soccfg()
    del soccfg._cfg["refclk_freq"]
    program = SParameterSweepProgram(soccfg, _config())
    program.compile()

    assert program.frequency_quantum_mhz > 0.0
    assert sum(inst["name"] == "math" for inst in program.prog_list) == 2


@pytest.mark.parametrize("scan_time_us", [1000.0, 1_000_000.0])
def test_long_scan_uses_periodic_start_and_timed_zero_stop(scan_time_us):
    program = SParameterSweepProgram(
        _mock_soccfg(),
        _config(scan_time_us=scan_time_us),
    )
    program.compile()

    summary = program.summary()
    assert summary["scan_time_requested_us"] == scan_time_us
    assert summary["rf_output_mode"] == "periodic_start_timed_zero_stop"
    assert summary["rf_periodic_word_fabric_cycles"] == 3
    assert summary["rf_stop_word_fabric_cycles"] == 3
    assert summary["readout_period_fabric_cycles"] == 3
    assert summary["rf_stop_command_tproc_cycle"] > 65535

    gain_writes = [
        inst["args"][2]
        for inst in program.prog_list
        if inst.get("comment", "").startswith("gain =")
    ]
    assert gain_writes == [program.sweep.gain, 0]

    generator_modes = [
        inst["args"][2]
        for inst in program.prog_list
        if inst.get("comment", "").startswith("phrst|")
    ]
    assert len(generator_modes) == 2
    start_mode, stop_mode = generator_modes
    assert start_mode & 0xFFFF == 3
    assert stop_mode & 0xFFFF == 3
    assert (start_mode >> 16) & 0b00100
    assert not ((stop_mode >> 16) & 0b00100)

    initial_frequency_writes = [
        inst
        for inst in program.prog_list
        if inst.get("comment", "").startswith("freq =")
    ]
    assert len(initial_frequency_writes) == 2


def test_program_rejects_awg_tuning_as_rf_sweep_output():
    with pytest.raises(ValueError, match="not an AWG tuning generator"):
        SParameterSweepProgram(
            _mock_soccfg(generator_type="axis_awg_tuning_v1"),
            _config(),
        )


def test_fir_ddr_acquisition_keeps_one_trace_per_frequency(monkeypatch):
    program = SParameterSweepProgram(
        _mock_soccfg(), _config(frequency_points=3, scan_time_us=4.0)
    )
    raw = np.arange(3 * 4 * 2, dtype=np.int32).reshape(12, 2)

    class FakeSoc:
        def arm_ddr4_fir_samples(self, **kwargs):
            self.arm_kwargs = kwargs
            return 24

        def get_ddr4_fir_samples(self, **kwargs):
            self.read_kwargs = kwargs
            return raw

    soc = FakeSoc()
    monkeypatch.setattr(program, "run_rounds", lambda *_args, **_kwargs: None)
    result = program.acquire_fir_ddr(soc)

    assert soc.arm_kwargs["n_triggers"] == 3
    assert soc.arm_kwargs["n_samples"] == 4
    assert result.iq_traces.shape == (3, 4, 2)
    np.testing.assert_array_equal(result.iq_traces.reshape(12, 2), raw)
    np.testing.assert_allclose(result.mean_i, raw.reshape(3, 4, 2)[:, :, 0].mean(1))


def test_counter_progress_cancellation_stops_tprocessor(monkeypatch):
    program = SParameterSweepProgram(
        _mock_soccfg(), _config(frequency_points=3, scan_time_us=4.0)
    )
    calls = []

    class CalibrationStopped(RuntimeError):
        pass

    class FakeSoc:
        def clear_tproc_counter(self, *, addr):
            calls.append(("clear", addr))

        def start_src(self, source):
            calls.append(("source", source))

        def start_tproc(self):
            calls.append(("start",))

        def stop_tproc(self):
            calls.append(("stop",))

        def get_tproc_counter(self, *, addr):
            calls.append(("counter", addr))
            return 0

    monkeypatch.setattr(program, "config_all", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(program, "_load_runtime_dmem", lambda *_args: None)
    checks = 0

    def cancel_check():
        nonlocal checks
        checks += 1
        if checks >= 2:
            raise CalibrationStopped("stopped")

    with pytest.raises(CalibrationStopped, match="stopped"):
        program._run_with_counter_progress(
            FakeSoc(),
            lambda _completed, _total: None,
            cancel_check=cancel_check,
        )

    assert ("start",) in calls
    assert ("stop",) in calls
    assert calls[-1] == ("source", "internal")


def test_50_ksps_uses_v2_trigger_delay_without_tproc_fir_compensation(
    monkeypatch,
):
    program = SParameterSweepProgram(
        _mock_soccfg(fir_rate_profile="50_ksps"),
        _config(frequency_points=3, scan_time_us=1000.0),
    )
    raw = np.arange(3 * 50 * 2, dtype=np.int32).reshape(150, 2)

    class FakeSoc:
        def arm_ddr4_fir_samples(self, **kwargs):
            self.arm_kwargs = kwargs
            return 300

        def get_ddr4_fir_samples(self, **kwargs):
            return raw

    soc = FakeSoc()
    monkeypatch.setattr(program, "run_rounds", lambda *_args, **_kwargs: None)
    result = program.acquire_fir_ddr(soc)

    assert program.scan_samples == 50
    assert program.fir_warmup_tproc_cycles == 0
    assert program.ddr_trigger_time == program.output_command_time
    assert program.summary()["fir_rate_profile"] == "50_ksps"
    assert program.summary()["fir_software_warmup_compensation"] is False
    assert soc.arm_kwargs["trigger_delay_cycles"] == 50
    assert result.sample_rate_hz == 50_000.0
    assert result.iq_traces.shape == (3, 50, 2)


def test_1_msps_delays_the_ddr_trigger_without_double_counting_capture_time():
    program = SParameterSweepProgram(
        _mock_soccfg(fir_rate_profile="1_msps"),
        _config(frequency_points=3, scan_time_us=4.0),
    )

    assert program.fir_software_trigger_delay_tproc_cycles == 8397
    assert program.ddr_trigger_time - program.output_command_time == 8397
    assert program.fir_feed_input_samples == (
        program.scan_samples * 300
        + 8677
        + program.sweep.margin_input_samples
    )
    summary = program.summary()
    assert summary["fir_software_trigger_delay_output_samples"] == 28
    assert summary["fir_software_trigger_delay_input_samples"] == 8397
    assert summary["fir_software_trigger_delay_tproc_cycles"] == 8397


def test_legacy_minimum_coherent_samples_does_not_expand_capture():
    program = SParameterSweepProgram(
        _mock_soccfg(fir_rate_profile="50_ksps"),
        _config(
            frequency_points=3,
            scan_time_us=100.0,
            minimum_coherent_samples=100,
        ),
    )

    summary = program.summary()
    assert program.requested_scan_samples == 5
    assert program.scan_samples == 5
    assert summary["scan_samples_requested"] == 5
    assert "minimum_coherent_samples" not in summary
    assert "minimum_coherent_samples_enforced" not in summary
    assert summary["scan_time_actual_us"] == pytest.approx(100.0)


def test_rf_board_output_and_readout_controls_are_applied():
    calls = []

    class FakeSoc:
        def rfb_set_gen_rf(self, *args):
            calls.append(("gen_rf", args))
            return args[1], args[2]

        def rfb_set_gen_filter(self, *args, **kwargs):
            calls.append(("gen_filter", args, kwargs))

        def rfb_set_ro_rf(self, *args):
            calls.append(("ro_rf", args))
            return args[1]

        def rfb_set_ro_filter(self, *args, **kwargs):
            calls.append(("ro_filter", args, kwargs))

    actual = configure_sparameter_rf_board(
        FakeSoc(),
        _config(output_board_type="RF_Out", input_board_type="RF_In"),
    )

    assert [call[0] for call in calls] == ["gen_rf", "gen_filter", "ro_rf", "ro_filter"]
    assert actual["output"]["commanded_att1_db"] == 10.0
    assert actual["readout"]["commanded_attenuation_db"] == 20.0


def test_dc_board_selection_uses_dc_apis_without_nonexistent_attenuators():
    calls = []

    class FakeSoc:
        def rfb_set_gen_dc(self, *args):
            calls.append(("gen_dc", args))

        def rfb_set_gen_filter(self, *args, **kwargs):
            calls.append(("gen_filter", args, kwargs))

        def rfb_set_ro_dc(self, *args):
            calls.append(("ro_dc", args))
            return args[1]

        def rfb_set_ro_filter(self, *args, **kwargs):
            calls.append(("ro_filter", args, kwargs))

    actual = configure_sparameter_rf_board(
        FakeSoc(),
        _config(
            output_board_type="DC_Out",
            input_board_type="DC_In",
            readout_dc_gain_db=5.0,
        ),
    )

    assert [call[0] for call in calls] == ["gen_dc", "ro_dc"]
    assert actual["output"]["attenuators_present"] is False
    assert actual["output"]["commanded_att1_db"] == 0.0
    assert actual["output"]["commanded_att2_db"] == 0.0
    assert actual["readout"]["attenuator_present"] is False
    assert actual["readout"]["commanded_attenuation_db"] == 0.0
    assert actual["readout"]["commanded_dc_gain_db"] == 5.0


def test_adc_nyquist_zone_is_applied_through_qick_soc_api():
    calls = []

    class FakeSoc:
        def set_nyquist(self, *args, **kwargs):
            calls.append((args, kwargs))

        def rfb_set_gen_dc(self, *_args):
            return None

        def rfb_set_ro_dc(self, *_args):
            return 0.0

    actual = configure_sparameter_rf_board(
        FakeSoc(),
        _config(
            output_board_type="DC_Out",
            input_board_type="DC_In",
            readout_nqz=2,
        ),
    )

    assert calls == [((0, 2), {"blocktype": "adc"})]
    assert actual["readout"]["nyquist_zone"] == 2


def test_qcodes_round_trip_stores_split_traces_and_derived_response(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "sparameter.db"
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging"))
    connection = QickConnectionConfig(host="127.0.0.1")
    run = QcodesRunConfig(
        database_path=str(database_path),
        experiment_name="RF tank response",
        sample_name="unit-test",
    )
    result = _result()
    dataset, row_count = store_sparameter_result(
        result,
        config=_config(frequency_points=3),
        connection_config=connection,
        run_config=run,
        program_summary={"sweep_execution": "tproc_hardware_register_add"},
        rf_settings={"output": {}, "readout": {}},
    )

    assert database_path.exists()
    assert row_count == 12
    loaded = load_sparameter_run(database_path, dataset.run_id)
    np.testing.assert_array_equal(loaded.result.iq_traces, result.iq_traces)
    np.testing.assert_allclose(loaded.result.magnitude_db, result.magnitude_db)
    np.testing.assert_allclose(
        loaded.result.phase_unwrapped_deg, result.phase_unwrapped_deg
    )

    from qcodes import (
        Measurement,
        Parameter,
        initialise_or_create_database_at,
        load_or_create_experiment,
    )

    initialise_or_create_database_at(str(database_path))
    unrelated_measurement = Measurement(
        exp=load_or_create_experiment("unrelated", "unit-test")
    )
    unrelated = Parameter("unrelated_scalar")
    unrelated_measurement.register_parameter(unrelated)
    with unrelated_measurement.run() as datasaver:
        datasaver.add_result((unrelated, 1.0))

    latest_sparameter = load_sparameter_run(database_path, 0)
    assert latest_sparameter.run_id == dataset.run_id


def test_qcodes_round_trip_preserves_avg_buffer_acquisition_metadata(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "avg_sparameter.db"
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging-avg"))
    frequencies = np.asarray([10.0, 11.0, 12.0])
    iq = np.asarray(
        [[[10.5, -2.0]], [[11.5, -3.0]], [[12.5, -4.0]]],
        dtype=float,
    )
    result = SParameterSweepResult.from_iq(
        frequencies,
        frequencies,
        iq,
        sample_rate_hz=300_000_000.0,
        acquisition_source="avg_buffer",
        integration_time_us=4.0,
        accumulation_repetitions=25,
    )
    dataset, row_count = store_sparameter_result(
        result,
        config=_config(
            acquisition_source="avg_buffer",
            frequency_points=3,
            scan_time_us=4.0,
            avg_repetitions=25,
        ),
        connection_config=QickConnectionConfig(host="127.0.0.1"),
        run_config=QcodesRunConfig(
            database_path=str(database_path),
            experiment_name="AVG RF response",
            sample_name="unit-test",
        ),
        program_summary={"acquisition_source": "avg_buffer"},
        rf_settings={"output": {}, "readout": {}},
    )

    assert row_count == 3
    loaded = load_sparameter_run(database_path, dataset.run_id)
    assert loaded.result.acquisition_source == "avg_buffer"
    assert loaded.result.integration_time_us == pytest.approx(4.0)
    assert loaded.result.accumulation_repetitions == 25
    assert loaded.result.iq_traces.shape == (3, 1, 2)
    np.testing.assert_allclose(loaded.result.iq_traces, iq)


def test_qcodes_round_trip_keeps_noisy_trace_with_zero_coherent_mean(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "zero_mean_sparameter.db"
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging-zero-mean"))
    frequencies = np.asarray([10.0, 11.0])
    iq = np.asarray(
        [
            [[8, -4], [-8, 4]],
            [[3, 4], [3, 4]],
        ],
        dtype=np.int32,
    )
    result = SParameterSweepResult.from_iq(frequencies, frequencies, iq)

    dataset, _row_count = store_sparameter_result(
        result,
        config=_config(frequency_points=2),
        connection_config=QickConnectionConfig(host="127.0.0.1"),
        run_config=QcodesRunConfig(
            database_path=str(database_path),
            experiment_name="Zero coherent mean",
            sample_name="unit-test",
        ),
        program_summary={"sweep_execution": "tproc_hardware_register_add"},
        rf_settings={"output": {}, "readout": {}},
    )

    with sqlite3.connect(database_path) as connection_db:
        payload_text = connection_db.execute(
            "SELECT sparameter_result_json FROM runs WHERE run_id = ?",
            (dataset.run_id,),
        ).fetchone()[0]
    payload = json.loads(payload_text)
    assert payload["adc_magnitude_db"][0] is None
    assert payload["phase_unwrapped_deg"][0] is None
    assert payload["response_diagnostics"] == {
        "zero_mean_iq_points": 1,
        "all_zero_fir_trace_points": 0,
        "nonzero_trace_zero_mean_points": 1,
        "other_nonfinite_response_points": 0,
    }

    loaded = load_sparameter_run(database_path, dataset.run_id)
    np.testing.assert_array_equal(loaded.result.iq_traces, iq)
    assert np.any(loaded.result.iq_traces[0] != 0)
    assert np.isnan(loaded.result.magnitude_db[0])
    assert np.isnan(loaded.result.phase_unwrapped_deg[0])


def test_calibrated_single_power_round_trip_stores_applied_gain_per_frequency(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "calibrated_sparameter.db"
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging-calibrated"))
    connection = QickConnectionConfig(host="127.0.0.1")
    run = QcodesRunConfig(
        database_path=str(database_path),
        experiment_name="Calibrated RF response",
        sample_name="unit-test",
    )
    base = _result()
    result = SParameterSweepResult.from_iq(
        base.requested_frequencies_mhz,
        base.frequencies_mhz,
        base.iq_traces,
        output_power_dbm=-20.0,
        nominal_gain_code=1200,
        frequency_gain_codes=[1000, 1100, 1200],
        actual_output_powers_dbm=[-30.0, -29.0, -28.0],
        input_powers_dbm=[-50.0, -48.0, -46.0],
    )
    config = _config(
        frequency_points=3,
        power_calibration_enabled=True,
        calibration_database_path=str(tmp_path / "gain_pwr_calb.db"),
        output_power_dbm=-20.0,
    )

    dataset, _row_count = store_sparameter_result(
        result,
        config=config,
        connection_config=connection,
        run_config=run,
        program_summary={"gain_source": "tproc_dmem_frequency_table"},
        rf_settings={"power_calibration": {"output_run": {"run_id": 31}}},
    )
    loaded = load_sparameter_run(database_path, dataset.run_id)

    assert loaded.result.output_power_dbm == -20.0
    assert loaded.result.nominal_gain_code == 1200
    np.testing.assert_array_equal(
        loaded.result.frequency_gain_codes,
        [1000, 1100, 1200],
    )
    assert loaded.result.physical_power_calibrated
    np.testing.assert_allclose(
        loaded.result.actual_output_powers_dbm,
        [-30.0, -29.0, -28.0],
    )
    np.testing.assert_allclose(
        loaded.result.input_powers_dbm,
        [-50.0, -48.0, -46.0],
    )
    np.testing.assert_allclose(loaded.result.magnitude_db, [-20.0, -19.0, -18.0])
    gain_data = dataset.get_parameter_data(CALIBRATED_GAIN_PARAMETER)[
        CALIBRATED_GAIN_PARAMETER
    ]
    np.testing.assert_array_equal(
        gain_data[CALIBRATED_GAIN_PARAMETER],
        [1000, 1100, 1200],
    )


def test_software_power_sweep_publishes_one_live_db_run_per_power(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "power_sparameter.db"
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging"))
    connection = QickConnectionConfig(host="127.0.0.1")
    run = QcodesRunConfig(
        database_path=str(database_path),
        experiment_name="RF power dependence",
        sample_name="unit-test",
    )
    config = _config(
        frequency_points=3,
        scan_time_us=4.0,
        power_sweep_enabled=True,
        power_start_gain=100,
        power_end_gain=10000,
        power_points=3,
        power_scale="log",
        settle_seconds=0.0,
    )

    class FakeProgram:
        def __init__(self, point_config):
            self.sweep = point_config

        def acquire_iq(self, _soc, counter_progress=None):
            if counter_progress is not None:
                counter_progress(0, self.sweep.frequency_points)
                counter_progress(
                    self.sweep.frequency_points,
                    self.sweep.frequency_points,
                )
            frequencies = self.sweep.requested_frequencies_mhz
            iq = np.zeros((frequencies.size, 4, 2), dtype=np.int32)
            iq[:, :, 0] = self.sweep.gain
            iq[:, :, 1] = np.arange(frequencies.size)[:, np.newaxis]
            return SParameterSweepResult.from_iq(
                frequencies,
                frequencies,
                iq,
            )

        def summary(self):
            return {
                "gain": self.sweep.gain,
                "sweep_execution": "tproc_hardware_register_add",
            }

    monkeypatch.setattr(
        sparameter_module,
        "configure_sparameter_rf_board",
        lambda _soc, _config: {"output": {}, "readout": {}},
    )
    monkeypatch.setattr(
        sparameter_module,
        "build_sparameter_program",
        lambda _soccfg, point_config, tproc_mhz=None: FakeProgram(point_config),
    )
    live_updates = []
    progress_updates = []

    def capture_partial(stored):
        with sqlite3.connect(database_path) as connection_db:
            payload_text = connection_db.execute(
                "SELECT sparameter_result_json FROM runs WHERE run_id = ?",
                (stored.run_id,),
            ).fetchone()[0]
        payload = json.loads(payload_text)
        live_updates.append(
            (
                stored.run_id,
                stored.result.power_count,
                payload["completed_power_points"],
                tuple(payload["power_gains"]),
            )
        )

    stored = run_sparameter_sweep(
        connection_config=connection,
        run_config=run,
        sweep_config=config,
        connector=lambda **_kwargs: (object(), object()),
        partial_callback=capture_partial,
        progress_callback=lambda percent, _message: progress_updates.append(percent),
    )

    assert [update[1] for update in live_updates] == [1, 2, 3]
    assert [update[2] for update in live_updates] == [1, 2, 3]
    assert len({update[0] for update in live_updates}) == 1
    assert live_updates[-1][3] == (100, 1000, 10000)
    assert progress_updates == sorted(progress_updates)
    assert progress_updates[-1] == 100
    assert isinstance(stored.result, SParameterPowerSweepResult)
    assert stored.result.iq_traces.shape == (3, 3, 4, 2)
    assert stored.row_count == 3 * 3 * 4
    loaded = load_sparameter_run(database_path, stored.run_id)
    assert isinstance(loaded.result, SParameterPowerSweepResult)
    np.testing.assert_array_equal(loaded.result.power_gains, [100, 1000, 10000])
    np.testing.assert_array_equal(
        loaded.result.iq_traces,
        stored.result.iq_traces,
    )
    magnitude_data = loaded.dataset.get_parameter_data(MAGNITUDE_DB_PARAMETER)[
        MAGNITUDE_DB_PARAMETER
    ]
    assert POWER_GAIN_PARAMETER in magnitude_data
    np.testing.assert_array_equal(
        magnitude_data[POWER_GAIN_PARAMETER],
        np.repeat([100, 1000, 10000], 3),
    )


def test_compensated_power_sweep_builds_one_frequency_gain_table_per_power(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "compensated_power_sparameter.db"
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging-compensated"))
    connection = QickConnectionConfig(host="127.0.0.1")
    run = QcodesRunConfig(
        database_path=str(database_path),
        experiment_name="Compensated RF power dependence",
        sample_name="unit-test",
    )
    calibration_path = tmp_path / "gain_pwr_calb.db"
    calibration_path.touch()
    config = _config(
        frequency_points=3,
        scan_time_us=4.0,
        power_calibration_enabled=True,
        calibration_database_path=str(calibration_path),
        output_power_dbm=-30.0,
        power_sweep_enabled=True,
        power_start_dbm=-30.0,
        power_end_dbm=-20.0,
        power_points=2,
        power_scale="log",
        settle_seconds=0.0,
    )

    class Summary:
        run_id = 31
        sample_name = "RF_Out_400MHz"

        def as_dict(self):
            return {"run_id": self.run_id, "sample_name": self.sample_name}

    class FakeOutputCalibration:
        def output_power_dbm(self, frequencies, gains, **_kwargs):
            return -20.0 + np.zeros_like(frequencies, dtype=float)

    class FakeInputCalibration:
        summary = Summary()

        def input_power_dbm(self, frequencies, adc_magnitude_db, **_kwargs):
            del frequencies
            return np.asarray(adc_magnitude_db, dtype=float) - 40.0

    built_tables = []

    class FakeProgram:
        def __init__(self, target_power_dbm, nominal_gain, gains):
            self.target_power_dbm = target_power_dbm
            self.nominal_gain = nominal_gain
            self.gains = np.asarray(gains, dtype=np.int64)
            self.frequencies_mhz = config.requested_frequencies_mhz

        def acquire_iq(self, _soc, counter_progress=None):
            if counter_progress is not None:
                counter_progress(config.frequency_points, config.frequency_points)
            iq = np.zeros((config.frequency_points, 4, 2), dtype=np.int32)
            iq[:, :, 0] = self.gains[:, np.newaxis]
            return SParameterSweepResult.from_iq(
                self.frequencies_mhz,
                self.frequencies_mhz,
                iq,
                output_power_dbm=self.target_power_dbm,
                nominal_gain_code=self.nominal_gain,
                frequency_gain_codes=self.gains,
            )

        def summary(self):
            return {
                "gain_source": "tproc_dmem_frequency_table",
                "nominal_gain": self.nominal_gain,
            }

    def build_for_power(
        _soccfg,
        _config_value,
        *,
        target_power_dbm,
        **_kwargs,
    ):
        nominal_gain = int(round((target_power_dbm + 40.0) * 100.0))
        gains = np.asarray(
            [nominal_gain, nominal_gain - 10, nominal_gain - 20],
            dtype=np.int64,
        )
        built_tables.append((float(target_power_dbm), gains.copy()))
        return FakeProgram(target_power_dbm, nominal_gain, gains), object()

    monkeypatch.setattr(
        sparameter_module,
        "configure_sparameter_rf_board",
        lambda _soc, _config: {"output": {}, "readout": {}},
    )
    monkeypatch.setattr(
        sparameter_module,
        "_prepare_power_calibration",
        lambda *_args, **_kwargs: (
            object(),
            FakeOutputCalibration(),
            Summary(),
            FakeInputCalibration(),
        ),
    )
    monkeypatch.setattr(
        sparameter_module,
        "_build_calibrated_program",
        build_for_power,
    )

    stored = run_sparameter_sweep(
        connection_config=connection,
        run_config=run,
        sweep_config=config,
        connector=lambda **_kwargs: (object(), object()),
    )

    assert [entry[0] for entry in built_tables] == [-30.0, -20.0]
    np.testing.assert_array_equal(built_tables[0][1], [1000, 990, 980])
    np.testing.assert_array_equal(built_tables[1][1], [2000, 1990, 1980])
    np.testing.assert_array_equal(stored.result.power_gains, [1000, 2000])
    np.testing.assert_array_equal(stored.result.output_powers_dbm, [-30.0, -20.0])
    np.testing.assert_array_equal(
        stored.result.frequency_gain_codes,
        [[1000, 990, 980], [2000, 1990, 1980]],
    )


def test_gui_has_independent_sparameter_tab_gain_limit_and_settings_round_trip(
    tmp_path,
):
    app = _application()
    window = gui.MainWindow()
    panel = window._sparameter_panel
    calibration_panel = window._calibration_panel

    assert window._control_tabs.indexOf(panel) >= 0
    assert window._control_tabs.indexOf(calibration_panel) >= 0
    assert panel.gain.maximum() == MAX_RF_OUTPUT_GAIN
    panel.frequency_start_mhz.setValue(42.0)
    panel.frequency_end_mhz.setValue(84.0)
    panel.frequency_points.setValue(33)
    panel.acquisition_source.setCurrentIndex(
        panel.acquisition_source.findData("avg_buffer")
    )
    panel.avg_repetitions.setValue(17)
    panel.avg_sweep_mode.setCurrentIndex(
        panel.avg_sweep_mode.findData("software")
    )
    panel.avg_hardware_rep_delay_us.setValue(12.5)
    panel.power_sweep_enabled.setChecked(True)
    panel.power_start_gain.setValue(100)
    panel.power_end_gain.setValue(10000)
    panel.power_points.setValue(3)
    panel.power_scale.setCurrentIndex(panel.power_scale.findData("log"))
    experiment_database = tmp_path / "experiment.db"
    sparameter_database = tmp_path / "sparameter.db"
    window._experiment_panel.database_path.setText(str(experiment_database))
    panel.database_path.setText(str(sparameter_database))
    panel.output_filter_type.setCurrentText("lowpass")
    panel.readout_filter_type.setCurrentText("bandpass")
    calibration_database = tmp_path / "gain_pwr_calb.db"
    calibration_panel.database_path.setText(str(calibration_database))
    calibration_panel.scope_resource.setText("USB::MOCK")
    calibration_panel.input_board.setCurrentText("RF_In")
    calibration_panel.input_path_loss.setValue(3.5)
    calibration_panel.input_response_plot.set_axis_scales("linear", "log")
    settings = window._settings_to_dict()
    decoded = window._decode_settings(settings)
    assert decoded["s_parameter"]["frequency_start_mhz"] == 42.0
    assert decoded["s_parameter"]["frequency_points"] == 33
    assert decoded["s_parameter"]["acquisition_source"] == "avg_buffer"
    assert decoded["s_parameter"]["avg_repetitions"] == 17
    assert decoded["s_parameter"]["avg_sweep_mode"] == "software"
    assert decoded["s_parameter"]["avg_hardware_rep_delay_us"] == 12.5
    assert panel.margin_input_samples.isEnabled() is False
    assert panel.address.isEnabled() is False

    legacy_sparameter = dict(decoded["s_parameter"])
    legacy_sparameter.pop("acquisition_source")
    legacy_sparameter.pop("avg_repetitions")
    legacy_sparameter.pop("avg_sweep_mode")
    legacy_sparameter.pop("avg_hardware_rep_delay_us")
    panel.load_settings(legacy_sparameter)
    assert panel.acquisition_source.currentData() == "fir_ddr"
    assert panel.avg_repetitions.value() == 100
    assert panel.avg_sweep_mode.currentData() == "hardware"
    assert panel.avg_hardware_rep_delay_us.value() == 0.0
    assert panel.margin_input_samples.isEnabled() is True
    assert panel.address.isEnabled() is True
    assert decoded["s_parameter"]["power_sweep_enabled"] is True
    assert decoded["s_parameter"]["power_start_gain"] == 100
    assert decoded["s_parameter"]["power_end_gain"] == 10000
    assert decoded["s_parameter"]["power_points"] == 3
    assert decoded["s_parameter"]["power_scale"] == "log"
    assert decoded["s_parameter"]["database_path"] == str(sparameter_database)
    assert decoded["run_config"].database_path == str(experiment_database)
    assert decoded["s_parameter"]["output_filter_type"] == "lowpass"
    assert decoded["s_parameter"]["readout_filter_type"] == "bandpass"
    assert decoded["calibration"]["database_path"] == str(calibration_database)
    assert (
        decoded["calibration"]["output"]["oscilloscope"]["visa_resource"] == "USB::MOCK"
    )
    assert decoded["calibration"]["input"]["input_board_type"] == "RF_In"
    assert decoded["calibration"]["input"]["path_loss_db"] == 3.5
    assert decoded["calibration"]["input_plot"] == {
        "x_scale": "linear",
        "y_scale": "log",
    }

    legacy_settings = dict(settings)
    legacy_settings["version"] = 8
    legacy_settings.pop("calibration")
    legacy_decoded = window._decode_settings(legacy_settings)
    assert legacy_decoded["calibration"]["output"]["output_board_type"] == "RF_Out"
    assert legacy_decoded["calibration"]["input"]["input_board_type"] == "RF_In"
    assert legacy_decoded["calibration"]["input_plot"] == {
        "x_scale": "log",
        "y_scale": "log",
    }

    run_arguments = window._sparameter_run_arguments()
    assert run_arguments["run_config"].database_path == str(sparameter_database)
    window._experiment_panel.database_path.setText(str(tmp_path / "changed.db"))
    assert window._sparameter_run_arguments()["run_config"].database_path == str(
        sparameter_database
    )
    window._experiment_panel.database_path.clear()
    assert window._sparameter_run_arguments()["run_config"].database_path == str(
        sparameter_database
    )

    window._sparameter_plot.set_result(_result())
    window._sparameter_plot.set_result(
        SParameterPowerSweepResult.from_sweeps(
            [100, 1000],
            [_result(), _result()],
        )
    )
    app.processEvents()
    window.close()


def test_gui_round_trips_board_types_calibration_database_and_dbm_power(tmp_path):
    app = _application()
    window = gui.MainWindow()
    panel = window._sparameter_panel
    calibration_path = tmp_path / "gain_pwr_calb.db"

    panel.power_calibration_enabled.setChecked(True)
    panel.calibration_database_path.setText(str(calibration_path))
    panel.input_calibration_selection.setCurrentIndex(
        panel.input_calibration_selection.findData("manual_run_id")
    )
    panel.requested_input_calibration_run_id.setValue(81)
    panel.output_board_type.setCurrentText("DC_Out")
    panel.input_board_type.setCurrentText("RF_In")
    panel.loss1_db.setValue(1.25)
    panel.loss2_db.setValue(2.5)
    panel.amplifier_gain_db.setValue(18.0)
    panel.output_power_dbm.setValue(-23.5)
    panel.power_sweep_enabled.setChecked(True)
    panel.power_start_dbm.setValue(-40.0)
    panel.power_end_dbm.setValue(-10.0)
    panel.power_points.setValue(7)
    panel.power_scale.setCurrentIndex(panel.power_scale.findData("log"))
    panel.path_diagram.update_button.click()

    settings = window._settings_to_dict()
    decoded = window._decode_settings(settings)["s_parameter"]

    assert decoded["power_calibration_enabled"] is True
    assert decoded["calibration_database_path"] == str(calibration_path)
    assert decoded["input_calibration_selection"] == "manual_run_id"
    assert decoded["requested_input_calibration_run_id"] == 81
    assert decoded["output_board_type"] == "DC_Out"
    assert decoded["input_board_type"] == "RF_In"
    assert decoded["loss1_db"] == 1.25
    assert decoded["loss2_db"] == 2.5
    assert decoded["amplifier_gain_db"] == 18.0
    assert decoded["output_power_dbm"] == -23.5
    assert decoded["power_start_dbm"] == -40.0
    assert decoded["power_end_dbm"] == -10.0
    assert panel.gain.isEnabled() is False
    assert panel.power_start_gain.isEnabled() is False
    assert panel.power_start_dbm.isEnabled() is True
    assert panel.path_diagram.output_att1_component.isHidden()
    assert panel.path_diagram.output_att2_component.isHidden()
    assert (
        panel.path_diagram.input_condition_stack.currentWidget()
        is panel.readout_attenuation_db
    )
    panel.input_board_type.setCurrentText("DC_In")
    assert (
        panel.path_diagram.input_condition_stack.currentWidget()
        is panel.readout_dc_gain_db
    )
    app.processEvents()
    window.close()


def test_gui_displays_dbm_to_frequency_gain_preview(monkeypatch, tmp_path):
    app = _application()

    class FakeOutputCalibration:
        summary = SimpleNamespace(run_id=91)

        def build_gain_schedule(
            self,
            frequencies,
            target_power_dbm,
            *,
            output_att1_db,
            output_att2_db,
        ):
            assert np.asarray(frequencies).size == 101
            assert target_power_dbm == -75.0
            assert output_att1_db == 10.0
            assert output_att2_db == 10.0
            return SimpleNamespace(
                nominal_gain_code=1392,
                gain_codes=np.asarray([1210, 1392, 1584], dtype=np.int32),
            )

    class FakeCalibrationDatabase:
        def __init__(self, path):
            assert path == str(tmp_path / "gain_pwr_calb.db")

        def output_calibration(self, board_type, frequencies):
            assert board_type == "RF_Out"
            return FakeOutputCalibration()

    monkeypatch.setattr(
        sparameter_gui_module,
        "CalibrationDatabase",
        FakeCalibrationDatabase,
    )
    window = gui.MainWindow()
    panel = window._sparameter_panel
    panel.calibration_database_path.setText(str(tmp_path / "gain_pwr_calb.db"))
    panel.frequency_start_mhz.setValue(400.0)
    panel.frequency_end_mhz.setValue(500.0)
    panel.frequency_points.setValue(101)
    panel.output_power_dbm.setValue(-75.0)
    panel.power_calibration_enabled.setChecked(True)
    panel._gain_preview_timer.stop()
    panel._update_calibrated_gain_preview()

    assert panel.gain.isEnabled() is False
    assert panel.calculated_gain_status.text() == (
        "Nominal 1,392; applied 1,210-1,584 / 32,766 "
        "(calibration Run 91)"
    )

    window.close()
    app.processEvents()


def test_rf_path_update_commits_only_sparameter_values():
    app = _application()
    window = gui.MainWindow()
    panel = window._sparameter_panel
    original = panel.config()

    panel.output_ch.setValue(6)
    panel.readout_ch.setValue(3)
    panel.output_board_type.setCurrentText("DC_Out")
    panel.input_board_type.setCurrentText("DC_In")
    panel.output_att1_db.setValue(7.0)
    panel.output_att2_db.setValue(8.0)
    panel.readout_dc_gain_db.setValue(12.0)
    panel.loss1_db.setValue(1.5)
    panel.loss2_db.setValue(2.5)
    panel.amplifier_gain_db.setValue(10.0)
    panel.output_filter_type.setCurrentText("lowpass")
    panel.output_filter_cutoff_ghz.setValue(2.2)
    panel.readout_filter_type.setCurrentText("bandpass")
    panel.readout_filter_cutoff_ghz.setValue(1.8)
    panel.readout_filter_bandwidth_ghz.setValue(0.4)

    assert panel.path_diagram.update_button.isEnabled()
    assert panel.config().output_ch == original.output_ch
    assert panel.config().output_board_type == original.output_board_type

    panel.path_diagram.update_button.click()
    app.processEvents()

    committed = panel.config()
    assert committed.output_ch == 6
    assert committed.readout_ch == 3
    assert committed.output_board_type == "DC_Out"
    assert committed.input_board_type == "DC_In"
    assert committed.readout_dc_gain_db == 12.0
    assert committed.loss1_db == 1.5
    assert committed.loss2_db == 2.5
    assert committed.amplifier_gain_db == 10.0
    assert panel.path_diagram.update_button.isEnabled() is False

    experiment_output = window._rf_ports_panel._panels[0]
    assert experiment_output.gen_ch.value() == 0
    assert experiment_output.output_board_type.currentText() == "RF_Out"
    assert experiment_output.att1_db.value() == 0.0
    assert experiment_output.att2_db.value() == 0.0
    assert experiment_output.filter_type.currentText() == "bypass"
    assert experiment_output.filter_cutoff.value() == 2.5

    experiment_input = window._rf_readout_panel
    assert experiment_input.ro_ch.value() == 0
    assert experiment_input.input_board_type.currentText() == "RF_In"
    assert experiment_input.dc_gain_db.value() == 0.0
    assert experiment_input.filter_type.currentText() == "bypass"
    assert experiment_input.filter_cutoff.value() == 2.5
    assert experiment_input.filter_bandwidth.value() == 1.0
    window.close()
