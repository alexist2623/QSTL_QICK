"""Headless tests for two-electrode stability-diagram acquisition.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
import sqlite3
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt5 import QtWidgets
import pytest

from qick_fine_tune_sweep import AmplitudeSweep, FineTuneDdrResult
from qick_qcodes_experiment import (
    QCODES_STAGING_ENV,
    IQ_STORAGE_MEAN_IQ,
    QcodesRunConfig,
    QickConnectionConfig,
    store_qick_result,
)
import stability_diagram as stability
from fir_ddr_profile import FirDdrProfile


def _application():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _fir_profile(*, is_50_ksps: bool = False):
    sample_rate_hz = 50_000.0 if is_50_ksps else 1_000_000.0
    trigger_delay_samples = 50 if is_50_ksps else 0
    sample_period_us = 1_000_000.0 / sample_rate_hz
    return FirDdrProfile(
        name="50_ksps" if is_50_ksps else "1_msps",
        sample_rate_hz=sample_rate_hz,
        sample_rate_msps=sample_rate_hz / 1_000_000.0,
        sample_period_us=sample_period_us,
        decimation=6000 if is_50_ksps else 300,
        input_rate_mhz=300.0,
        group_delay_input_samples=296_677.0 if is_50_ksps else 8_677.0,
        uses_fpga_trigger_delay=is_50_ksps,
        trigger_delay_samples=trigger_delay_samples,
        software_warmup_compensation=not is_50_ksps,
        config={},
        trigger_delay_units=(
            "valid_input_samples" if is_50_ksps else "none"
        ),
    )


def _config() -> stability.StabilityDiagramConfig:
    return stability.StabilityDiagramConfig(
        x_axis=stability.StabilitySweepAxis(
            "awg_0", -100.0, 100.0, 2
        ),
        y_axis=stability.StabilitySweepAxis(
            "awg_1", -50.0, 50.0, 2
        ),
        repetitions_per_point=2,
        trace_samples_per_point=3,
    )


def _ddr_result():
    axes = (
        SimpleNamespace(
            output_name="awg_0",
            segment_name=stability.STABILITY_HOLD_SEGMENT,
            start=-1.0,
            stop=1.0,
            count=2,
        ),
        SimpleNamespace(
            output_name="awg_1",
            segment_name=stability.STABILITY_HOLD_SEGMENT,
            start=-0.5,
            stop=0.5,
            count=2,
        ),
    )
    coordinates = np.asarray(
        (
            (-1.0, -0.5),
            (-1.0, 0.5),
            (1.0, -0.5),
            (1.0, 0.5),
        ),
        dtype=float,
    )
    iq = np.empty((4, 2, 3, 2), dtype=np.int32)
    for point in range(4):
        for repetition in range(2):
            for sample in range(3):
                iq[point, repetition, sample, 0] = (
                    10 * (point + 1) + repetition + sample
                )
                iq[point, repetition, sample, 1] = (
                    -5 * (point + 1) - repetition - sample
                )
    return SimpleNamespace(
        sweep_points=coordinates,
        sweep_axes=axes,
        iq=iq,
    )


@dataclass(frozen=True)
class _FakeReadoutSpec:
    ro_ch: int = 0
    fpga_trigger_delay_samples: int = 50
    fpga_trigger_delay_us: float | None = None


def _worker_kwargs(tmp_path=None):
    return {
        "connection_config": QickConnectionConfig(
            host="127.0.0.1",
            ns_port=8888,
            proxy_name="testqick",
        ),
        "run_config": (
            None
            if tmp_path is None
            else QcodesRunConfig(database_path=str(tmp_path / "stability.db"))
        ),
        "gui_settings": (
            None
            if tmp_path is None
            else {
                "qick": {"fabric_mhz": 300.0, "full_scale_mv": 100.0},
                "awg": {"outputs": []},
            }
        ),
        "stability_config": _config(),
        "full_scale_mv": 100.0,
        "sequence": SimpleNamespace(),
        "awg_channels": (1, 3),
        "repetitions_per_sweep": 2,
        "tproc_mhz": 300.0,
        "rf_specs": (),
        "readout_spec": _FakeReadoutSpec(),
        "progress": False,
    }


def test_stability_config_requires_two_outputs_and_respects_full_scale():
    with pytest.raises(ValueError, match="different AWG outputs"):
        stability.StabilityDiagramConfig(
            x_axis=stability.StabilitySweepAxis(
                "awg_0", -10.0, 10.0, 2
            ),
            y_axis=stability.StabilitySweepAxis(
                "awg_0", -10.0, 10.0, 2
            ),
        )

    config = _config()
    config.validate_full_scale(100.0)
    with pytest.raises(ValueError, match="stability sweep exceeds"):
        config.validate_full_scale(49.0)

    compensated = stability.StabilityDiagramConfig(
        x_axis=stability.StabilitySweepAxis(
            "awg_0", -100.0, 100.0, 2
        ),
        y_axis=stability.StabilitySweepAxis(
            "awg_1", -50.0, 50.0, 2
        ),
        bias_t_compensation_enabled=True,
        bias_t_compensation_voltage_mv=125.0,
    )
    with pytest.raises(ValueError, match="compensation voltage exceeds"):
        compensated.validate_full_scale(100.0)


def test_stability_settings_add_backward_compatible_bias_t_defaults():
    legacy = stability.default_stability_settings(("awg_0", "awg_1"), ("set_0",))
    legacy.pop("bias_t_compensation")
    legacy.pop("color_ranges")
    legacy.pop("visible_data")
    legacy.pop("saved_plot_database_path")
    legacy.pop("saved_plot_run_id")
    legacy.pop("saved_plot_data")
    legacy.pop("iq_storage_mode")
    legacy.pop("modulation_power_calibration")
    legacy.pop("acquisition_source")
    legacy.pop("sweep_mode")
    legacy.pop("hardware_rep_delay_us")

    normalized = stability.normalize_stability_settings(
        legacy,
        output_names=("awg_0", "awg_1"),
        segment_names=("set_0",),
    )

    assert normalized["bias_t_compensation"] == {
        "enabled": False,
        "type": "dc",
        "mode": "fixed_voltage",
        "voltage_mv": stability.DEFAULT_STABILITY_BIAS_T_COMPENSATION_MV,
        "duration_us": 1.0,
        "filter_tau_us": 100.0,
    }
    assert normalized["settle_time_us"] == stability.DEFAULT_STABILITY_SETTLE_US
    assert normalized["acquisition_source"] == "fir_ddr"
    assert normalized["sweep_mode"] == "hardware"
    assert normalized["hardware_rep_delay_us"] == 0.0
    assert "segment_name" not in normalized["x_axis"]
    assert normalized["color_ranges"] == {
        "i": {
            "auto": True,
            "minimum": -1.0,
            "maximum": 1.0,
        },
        "q": {
            "auto": True,
            "minimum": -1.0,
            "maximum": 1.0,
        },
        "magnitude": {
            "auto": True,
            "minimum": 0.0,
            "maximum": 1.0,
        },
        "phase": {
            "auto": False,
            "minimum": -180.0,
            "maximum": 180.0,
        },
    }
    assert normalized["visible_data"] == ["magnitude", "phase"]
    assert normalized["iq_storage_mode"] == "full_traces"
    assert normalized["saved_plot_database_path"] == normalized["database_path"]
    assert normalized["saved_plot_run_id"] == 0
    assert normalized["saved_plot_data"] == "magnitude"
    assert normalized["modulation_power_calibration"] == {
        "enabled": False,
        "database_path": (
            stability.DEFAULT_STABILITY_POWER_CALIBRATION_DB_PATH
        ),
        "run_id": 0,
        "target_power_dbm": stability.DEFAULT_STABILITY_TARGET_POWER_DBM,
    }

    invalid = dict(normalized)
    invalid["color_ranges"] = {
        "magnitude": {
            "auto": False,
            "minimum": 10.0,
            "maximum": 10.0,
        },
        "phase": normalized["color_ranges"]["phase"],
    }
    with pytest.raises(ValueError, match="minimum must be below maximum"):
        stability.normalize_stability_settings(
            invalid,
            output_names=("awg_0", "awg_1"),
        )


def test_stability_builds_dedicated_set_hold_sequence_without_awg_waveform():
    config = _config()
    sequence = stability.build_stability_hold_sequence(
        config,
        output_names=("awg_0", "awg_1", "awg_2"),
        fabric_mhz=300.0,
        full_scale_mv=100.0,
        cross_capacitance=np.eye(3),
    )

    assert len(sequence.segments) == 1
    segment = sequence.segments[0]
    assert segment.name == stability.STABILITY_HOLD_SEGMENT
    assert segment.kind == "set"
    assert segment.amplitudes == (0.0, 0.0, 0.0)
    assert segment.duration_cycles == int(
        np.ceil(
            (
                config.settle_time_us
                + config.trace_samples_per_point
                + stability.DEFAULT_STABILITY_POINT_GUARD_US
            )
            * 300.0
        )
    )
    assert [item.segment_name for item in sequence.sweeps] == ["set_0", "set_0"]
    assert [item.output_name for item in sequence.sweeps] == ["awg_0", "awg_1"]


def test_stability_50ksps_hold_covers_only_immediate_trace():
    config = _config()
    sequence = stability.build_stability_hold_sequence(
        config,
        output_names=("awg_0", "awg_1"),
        fabric_mhz=300.0,
        full_scale_mv=100.0,
        sample_period_us=20.0,
    )

    expected_hold_us = (
        config.settle_time_us
        + config.trace_samples_per_point * 20.0
        + stability.DEFAULT_STABILITY_POINT_GUARD_US
    )
    assert sequence.segments[0].duration_cycles == int(
        np.ceil(expected_hold_us * 300.0)
    )


def test_reduce_fir_result_restores_voltage_grid_and_coherent_iq_mean():
    raw = _ddr_result()
    result = stability.reduce_fir_stability_result(
        raw,
        _config(),
        full_scale_mv=100.0,
        iteration=7,
    )

    expected_per_point = raw.iq.astype(float).mean(axis=(1, 2))
    assert result.x_voltage_mv.tolist() == [-100.0, 100.0]
    assert result.y_voltage_mv.tolist() == [-50.0, 50.0]
    assert result.i_mean.tolist() == [
        [expected_per_point[0, 0], expected_per_point[2, 0]],
        [expected_per_point[1, 0], expected_per_point[3, 0]],
    ]
    assert result.q_mean.tolist() == [
        [expected_per_point[0, 1], expected_per_point[2, 1]],
        [expected_per_point[1, 1], expected_per_point[3, 1]],
    ]
    assert np.allclose(result.magnitude, np.hypot(result.i_mean, result.q_mean))
    assert np.allclose(
        result.phase_deg,
        np.degrees(np.arctan2(result.q_mean, result.i_mean)),
    )
    assert result.iteration == 7
    assert result.x_axis_label == "awg_0"
    assert result.y_axis_label == "awg_1"
    assert result.repetition_count == 2
    assert result.samples_per_trace == 3
    assert result.value_unit == "ADC units"
    assert result.measurement_mode == "raw_iq"


@pytest.mark.skipif(stability.pg is None, reason="pyqtgraph is not installed")
def test_stability_plot_exposes_and_applies_color_ranges():
    app = _application()
    result = stability.reduce_fir_stability_result(
        _ddr_result(),
        _config(),
        full_scale_mv=100.0,
        iteration=3,
    )
    plot = stability.StabilityDiagramPlotWidget()
    plot.set_result(result)
    app.processEvents()

    magnitude_levels = plot._levels(result.magnitude)
    np.testing.assert_allclose(
        plot.magnitude_image.getLevels(),
        magnitude_levels,
    )
    np.testing.assert_allclose(
        plot.phase_image.getLevels(),
        (-180.0, 180.0),
    )
    assert plot.magnitude_range_control.auto_range.isChecked() is True
    assert plot.phase_range_control.auto_range.isChecked() is False
    plot.phase_range_control.auto_range.setChecked(True)
    app.processEvents()
    np.testing.assert_allclose(
        plot.phase_image.getLevels(),
        plot._levels(result.phase_deg),
    )
    assert plot.magnitude_color_bar is not None
    assert plot.phase_color_bar is not None
    assert plot.magnitude_color_bar.interactive is True
    assert plot.phase_color_bar.interactive is True
    assert plot.visible_data() == ("magnitude", "phase")
    assert plot.plot_cells["i"].isHidden() is True
    assert plot.plot_cells["q"].isHidden() is True
    assert plot.plot_cells["magnitude"].isHidden() is False
    assert plot.plot_cells["phase"].isHidden() is False
    assert "Applied:" in plot.magnitude_range_control.range_status.text()
    assert "Data:" in plot.magnitude_range_control.range_status.text()

    plot.magnitude_color_bar.setLevels((7.5, 42.5))
    plot.magnitude_color_bar.sigLevelsChanged.emit(plot.magnitude_color_bar)
    app.processEvents()
    assert plot.magnitude_range_control.auto_range.isChecked() is False
    np.testing.assert_allclose(
        (
            plot.magnitude_range_control.minimum.value(),
            plot.magnitude_range_control.maximum.value(),
        ),
        (7.5, 42.5),
    )
    np.testing.assert_allclose(
        plot.magnitude_image.getLevels(),
        (7.5, 42.5),
    )

    plot.load_color_range_settings({
        "magnitude": {
            "auto": False,
            "minimum": 5.0,
            "maximum": 50.0,
        },
        "phase": {
            "auto": False,
            "minimum": -45.0,
            "maximum": 90.0,
        },
    })
    app.processEvents()
    np.testing.assert_allclose(plot.magnitude_image.getLevels(), (5.0, 50.0))
    np.testing.assert_allclose(plot.phase_image.getLevels(), (-45.0, 90.0))
    assert plot.color_range_settings() == {
        "i": {
            "auto": True,
            "minimum": plot._symmetric_levels(result.i_mean)[0],
            "maximum": plot._symmetric_levels(result.i_mean)[1],
        },
        "q": {
            "auto": True,
            "minimum": plot._symmetric_levels(result.q_mean)[0],
            "maximum": plot._symmetric_levels(result.q_mean)[1],
        },
        "magnitude": {
            "auto": False,
            "minimum": 5.0,
            "maximum": 50.0,
        },
        "phase": {
            "auto": False,
            "minimum": -45.0,
            "maximum": 90.0,
        },
    }
    plot.load_visible_data(["i", "angle"])
    app.processEvents()
    assert plot.visible_data() == ("i", "phase")
    assert plot.plot_cells["i"].isHidden() is False
    assert plot.plot_cells["q"].isHidden() is True
    assert plot.plot_cells["magnitude"].isHidden() is True
    assert plot.plot_cells["phase"].isHidden() is False
    np.testing.assert_allclose(plot.images["i"].image, result.i_mean)
    np.testing.assert_allclose(plot.images["phase"].image, result.phase_deg)

    plot.data_selectors["i"].setChecked(False)
    plot.data_selectors["phase"].setChecked(False)
    app.processEvents()
    assert len(plot.visible_data()) == 1

    plot.close()
    plot.deleteLater()
    app.processEvents()


def test_reduce_fir_result_converts_dc_input_iq_to_current():
    raw = _ddr_result()
    raw_result = stability.reduce_fir_stability_result(
        raw,
        _config(),
        full_scale_mv=100.0,
    )
    current_result = stability.reduce_fir_stability_result(
        raw,
        _config(),
        full_scale_mv=100.0,
        readout_spec=SimpleNamespace(
            input_board_type="DC_In",
            dc_measure_mode=True,
            dc_measure_gain_v_per_a=2.0,
        ),
    )

    np.testing.assert_allclose(current_result.i_mean, raw_result.i_mean / 2.0)
    np.testing.assert_allclose(current_result.q_mean, raw_result.q_mean / 2.0)
    np.testing.assert_allclose(
        current_result.magnitude,
        raw_result.magnitude / 2.0,
    )
    np.testing.assert_allclose(current_result.phase_deg, raw_result.phase_deg)
    assert current_result.value_unit == "A"
    assert current_result.measurement_mode == "dc_current_iq"


def test_reduce_fir_result_auto_scales_nanoamp_current():
    raw = _ddr_result()
    raw.iq = raw.iq.astype(np.float64) * 1.0e-9
    current_result = stability.reduce_fir_stability_result(
        raw,
        _config(),
        full_scale_mv=100.0,
        readout_spec=SimpleNamespace(
            input_board_type="DC_In",
            effective_measurement_representation="current",
            dc_measure_gain_v_per_a=1.0,
            dc_voltage_calibration_enabled=False,
        ),
    )

    assert current_result.value_unit == "nA"
    assert current_result.base_value_unit == "A"
    assert current_result.display_scale == 1.0e9
    assert current_result.measurement_mode == "dc_current_iq"
    assert np.nanmax(np.abs(current_result.i_mean)) > 1.0


def test_stability_panel_measurement_representation_round_trip():
    app = _application()
    panel = stability.StabilityDiagramPanel()
    panel.refresh_targets(("awg_0", "awg_1"), (1, 3))
    panel.apply_path_settings({
        **stability.DEFAULT_STABILITY_RF_PATH,
        "input_board_type": "DC_In",
    })
    panel.measurement_unit.setCurrentIndex(
        panel.measurement_unit.findData("current")
    )
    panel.dc_measure_gain_v_per_a.setValue(1.0e8)
    settings = panel.settings_dict()

    assert settings["measurement_representation"] == "current"
    assert panel.dc_measure_mode.isChecked() is True
    restored = stability.StabilityDiagramPanel()
    restored.refresh_targets(("awg_0", "awg_1"), (1, 3))
    restored.load_settings(settings)
    app.processEvents()
    assert restored.measurement_unit.currentData() == "current"
    assert restored.dc_measure_mode.isChecked() is True
    assert restored.dc_measure_gain_v_per_a.value() == 1.0e8

    restored.close()
    panel.close()


def test_continuous_worker_repeats_without_qcodes_storage(monkeypatch):
    calls = {"execute": 0, "store": 0}

    monkeypatch.setattr(
        stability,
        "connect_qick",
        lambda *_args, **_kwargs: (object(), object()),
    )
    monkeypatch.setattr(
        stability,
        "resolve_fir_ddr_profile",
        lambda *_args, **_kwargs: _fir_profile(),
    )

    class FakeProgram:
        def summary(self):
            return {}

    def fake_execute(*_args, **_kwargs):
        calls["execute"] += 1
        return FakeProgram(), _ddr_result(), {}

    def forbidden_store(*_args, **_kwargs):
        calls["store"] += 1
        raise AssertionError("continuous mode must not write QCoDeS")

    monkeypatch.setattr(stability, "execute_qick_sequence", fake_execute)
    monkeypatch.setattr(stability, "store_qick_result", forbidden_store)
    worker = stability.StabilityDiagramWorker(
        _worker_kwargs(),
        continuous=True,
    )
    scans = []
    stopped = []
    worker.scan_ready.connect(
        lambda result: (scans.append(result), worker.request_stop())
    )
    worker.stopped.connect(lambda: stopped.append(True))

    worker.run()

    assert calls == {"execute": 1, "store": 0}
    assert len(scans) == 1
    assert stopped == [True]


def test_avg_hardware_worker_keeps_cartesian_and_repetition_loops(monkeypatch):
    calls = []
    config = replace(
        _config(),
        acquisition_source="avg_buffer",
        sweep_mode="hardware",
        hardware_rep_delay_us=2.5,
    )
    kwargs = _worker_kwargs()
    kwargs["stability_config"] = config
    kwargs["sequence"] = SimpleNamespace(
        output_names=("awg_0", "awg_1"),
        cross_capacitance=np.eye(2),
    )
    monkeypatch.setattr(
        stability,
        "connect_qick",
        lambda *_args, **_kwargs: (
            object(),
            {"readouts": [{"f_output": 300.0}]},
        ),
    )
    monkeypatch.setattr(
        stability,
        "resolve_fir_ddr_profile",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("AVG mode must not resolve the FIR DDR profile")
        ),
    )

    class FakeProgram:
        def summary(self):
            return {"cartesian_point_count": 4}

    def fake_execute(*_args, **runtime_kwargs):
        calls.append(runtime_kwargs)
        return FakeProgram(), _ddr_result(), {}

    monkeypatch.setattr(stability, "execute_qick_sequence", fake_execute)
    worker = stability.StabilityDiagramWorker(kwargs, continuous=True)
    scans = []
    worker.scan_ready.connect(
        lambda result: (scans.append(result), worker.request_stop())
    )
    worker.run()

    assert len(calls) == 1
    assert calls[0]["sequence"].sweep_shape == (2, 2)
    assert len(calls[0]["sequence"].sweep_axes) == 2
    assert calls[0]["repetitions_per_sweep"] == 2
    assert calls[0]["acquisition_source"] == "avg_buffer"
    assert calls[0]["hardware_rep_delay_us"] == 2.5
    assert len(scans) == 1
    assert scans[0].magnitude.shape == (2, 2)


def test_avg_software_worker_runs_one_fixed_program_per_cartesian_point(
    monkeypatch,
):
    config = replace(
        _config(),
        acquisition_source="avg_buffer",
        sweep_mode="software",
        hardware_rep_delay_us=9.0,
    )
    kwargs = _worker_kwargs()
    kwargs["stability_config"] = config
    kwargs["sequence"] = SimpleNamespace(
        output_names=("awg_0", "awg_1"),
        cross_capacitance=np.eye(2),
    )
    monkeypatch.setattr(
        stability,
        "connect_qick",
        lambda *_args, **_kwargs: (
            object(),
            {"readouts": [{"f_output": 300.0}]},
        ),
    )
    monkeypatch.setattr(
        stability,
        "resolve_fir_ddr_profile",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("AVG mode must not resolve the FIR DDR profile")
        ),
    )
    raw = _ddr_result()
    calls = []

    class FakeProgram:
        def summary(self):
            return {"cartesian_point_count": 1}

    def fake_execute(*_args, **runtime_kwargs):
        point_index = len(calls)
        calls.append(runtime_kwargs)
        point_sequence = runtime_kwargs["sequence"]
        result = FineTuneDdrResult(
            sweep_points=np.asarray([0.0]),
            iq=np.asarray(raw.iq[point_index : point_index + 1]),
            sweep_shape=(1,),
            cross_capacitance=np.eye(2),
            sample_rate_hz=300_000_000.0,
            fir_rate_profile="avg_buffer",
            acquisition_source="avg_buffer",
            accumulation_repetitions=2,
        )
        assert point_sequence.sweep_point_count == 1
        assert point_sequence.sweep_axes == ()
        return FakeProgram(), result, {}

    monkeypatch.setattr(stability, "execute_qick_sequence", fake_execute)
    worker = stability.StabilityDiagramWorker(kwargs, continuous=True)
    scans = []
    worker.scan_ready.connect(
        lambda result: (scans.append(result), worker.request_stop())
    )
    worker.run()

    expected_levels = (
        (-1.0, -0.5),
        (-1.0, 0.5),
        (1.0, -0.5),
        (1.0, 0.5),
    )
    assert len(calls) == 4
    assert tuple(
        tuple(call["sequence"].segments[0].amplitudes)
        for call in calls
    ) == expected_levels
    assert all(call["repetitions_per_sweep"] == 2 for call in calls)
    assert all(call["acquisition_source"] == "avg_buffer" for call in calls)
    assert all(call["hardware_rep_delay_us"] == 0.0 for call in calls)
    assert len(scans) == 1
    assert scans[0].repetition_count == 2
    assert scans[0].magnitude.shape == (2, 2)


def test_worker_rebuilds_50ksps_sequence_and_rf_hold(monkeypatch):
    profile = _fir_profile(is_50_ksps=True)
    monkeypatch.setattr(
        stability,
        "connect_qick",
        lambda *_args, **_kwargs: (object(), object()),
    )
    monkeypatch.setattr(
        stability,
        "resolve_fir_ddr_profile",
        lambda *_args, **_kwargs: profile,
    )

    template = SimpleNamespace(
        output_names=("awg_0", "awg_1"),
        cross_capacitance=np.eye(2),
    )
    kwargs = _worker_kwargs()
    kwargs["sequence"] = template
    kwargs["stability_fabric_mhz"] = 300.0
    @dataclass(frozen=True)
    class FakeRfSpec:
        duration_us: float
        delay_us: float

    kwargs["rf_specs"] = (
        FakeRfSpec(duration_us=1.0, delay_us=1.0 / 300.0),
    )
    captured = {}

    class FakeProgram:
        def summary(self):
            return {}

    def fake_execute(*_args, **runtime_kwargs):
        captured.update(runtime_kwargs)
        worker.request_stop()
        return FakeProgram(), _ddr_result(), {}

    monkeypatch.setattr(stability, "execute_qick_sequence", fake_execute)
    monkeypatch.setattr(
        stability,
        "store_qick_result",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("continuous mode must not store")
        ),
    )
    worker = stability.StabilityDiagramWorker(kwargs, continuous=True)
    worker.run()

    sequence = captured["sequence"]
    expected_hold_us = (
        _config().settle_time_us
        + _config().trace_samples_per_point * profile.sample_period_us
        + stability.DEFAULT_STABILITY_POINT_GUARD_US
    )
    assert sequence.segments[0].duration_cycles == int(
        np.ceil(expected_hold_us * 300.0)
    )
    assert captured["rf_specs"][0].duration_us == (
        _config().settle_time_us
        + _config().trace_samples_per_point * profile.sample_period_us
    )
    assert captured["rf_specs"][0].delay_us == pytest.approx(1.0 / 300.0)
    assert captured["readout_spec"].fpga_trigger_delay_samples is None
    assert captured["readout_spec"].fpga_trigger_delay_us is None


def test_single_shot_worker_saves_exactly_once(monkeypatch, tmp_path):
    calls = {"store": 0, "storage_mode": None}

    monkeypatch.setattr(
        stability,
        "connect_qick",
        lambda *_args, **_kwargs: (object(), object()),
    )
    monkeypatch.setattr(
        stability,
        "resolve_fir_ddr_profile",
        lambda *_args, **_kwargs: _fir_profile(),
    )

    class FakeProgram:
        def summary(self):
            return {"cartesian_point_count": 4}

    monkeypatch.setattr(
        stability,
        "execute_qick_sequence",
        lambda *_args, **_kwargs: (FakeProgram(), _ddr_result(), {"rf": "ok"}),
    )

    dataset = SimpleNamespace(run_id=23, guid="test-guid")

    def fake_store(*_args, **_kwargs):
        calls["store"] += 1
        calls["storage_mode"] = _kwargs["iq_storage_mode"]
        return dataset, 24

    monkeypatch.setattr(stability, "store_qick_result", fake_store)
    worker_kwargs = _worker_kwargs(tmp_path)
    worker_kwargs["iq_storage_mode"] = IQ_STORAGE_MEAN_IQ
    worker = stability.StabilityDiagramWorker(
        worker_kwargs,
        continuous=False,
    )
    finished = []
    worker.single_finished.connect(finished.append)

    worker.run()

    assert calls["store"] == 1
    assert calls["storage_mode"] == IQ_STORAGE_MEAN_IQ
    assert len(finished) == 1
    assert finished[0].run_id == 23
    assert finished[0].experiment.row_count == 24
    assert finished[0].diagram.magnitude.shape == (2, 2)


def test_stability_front_panel_remains_visible_while_controls_scroll():
    app = _application()
    panel = stability.StabilityDiagramPanel()
    panel.resize(640, 900)
    panel.show()
    app.processEvents()
    app.processEvents()

    scrollbar = panel.controls_scroll.verticalScrollBar()
    scrollbar.setValue(scrollbar.maximum())
    assert scrollbar.value() > 0
    app.processEvents()

    assert panel.front_panel_preview is panel.path_diagram.front_panel_preview
    assert panel.front_panel_preview.parentWidget() is panel
    assert panel.front_panel_preview.isVisible()
    assert panel.front_panel_preview.y() < panel.controls_scroll.y()
    panel.close()


def test_stability_panel_controls_and_settings_round_trip(tmp_path):
    app = _application()
    panel = stability.StabilityDiagramPanel()
    panel.refresh_targets(
        ("awg_0", "awg_1", "awg_2"),
        (1, 3, 5),
        ("set_0", "set_1"),
    )
    panel.x_axis.output.setCurrentIndex(panel.x_axis.output.findData("awg_0"))
    panel.y_axis.output.setCurrentIndex(panel.y_axis.output.findData("awg_2"))
    panel.x_axis.start_mv.setValue(-250.0)
    panel.x_axis.stop_mv.setValue(125.0)
    panel.x_axis.points.setValue(11)
    panel.y_axis.points.setValue(7)
    panel.repetitions.setValue(4)
    panel.trace_samples.setValue(321)
    panel.settle_time_us.setValue(75.5)
    panel.acquisition_source.setCurrentIndex(
        panel.acquisition_source.findData("avg_buffer")
    )
    panel.sweep_mode.setCurrentIndex(panel.sweep_mode.findData("software"))
    panel.hardware_rep_delay_us.setValue(12.5)
    panel.modulation_frequency_mhz.setValue(12.5)
    panel.modulation_gain.setValue(12345)
    panel.modulation_power_calibration_group.setChecked(True)
    panel.modulation_power_calibration_path.setText(
        str(tmp_path / "gain_power.db")
    )
    panel.modulation_power_calibration_run_id.setValue(17)
    panel.modulation_target_power_dbm.setValue(-37.25)
    panel.plot.magnitude_range_control.set_manual_levels(10.0, 100.0)
    panel.plot.phase_range_control.set_manual_levels(-90.0, 45.0)
    panel.plot.load_visible_data(["i", "q", "magnitude"])
    panel.bias_t_group.setChecked(True)
    panel.bias_t_mode.setCurrentIndex(
        panel.bias_t_mode.findData("fixed_time")
    )
    panel.bias_t_duration_us.setValue(2.5)
    database_path = tmp_path / "stability_single_shot.db"
    saved_plot_path = tmp_path / "saved_stability.db"
    panel.database_path.setText(str(database_path))
    panel.saved_database_path.setText(str(saved_plot_path))
    panel._preferred_saved_run_id = 29
    panel.saved_plot_data.setCurrentIndex(
        panel.saved_plot_data.findData("q")
    )
    panel.iq_storage_mode.setCurrentIndex(
        panel.iq_storage_mode.findData(IQ_STORAGE_MEAN_IQ)
    )
    app.processEvents()

    config = panel.config(full_scale_mv=2500.0)
    assert config.x_axis.output_name == "awg_0"
    assert config.x_axis.segment_name == stability.STABILITY_HOLD_SEGMENT
    assert config.y_axis.output_name == "awg_2"
    assert config.point_count == 77
    assert config.trace_samples_per_point == 321
    assert config.settle_time_us == 75.5
    assert config.acquisition_source == "avg_buffer"
    assert config.sweep_mode == "software"
    assert config.hardware_rep_delay_us == 12.5
    assert config.modulation_frequency_mhz == 12.5
    assert config.modulation_gain == 12345
    assert config.modulation_power_calibration_enabled is True
    assert config.modulation_power_calibration_run_id == 17
    assert config.modulation_target_power_dbm == -37.25
    assert config.bias_t_compensation_enabled is True
    assert config.bias_t_compensation_type == "dc"
    assert config.bias_t_compensation_mode == "fixed_time"
    assert config.bias_t_compensation_duration_us == 2.5
    assert panel.bias_t_compensation_mv.isEnabled() is False
    assert panel.bias_t_duration_us.isEnabled() is True
    assert panel.point_count.text() == "77"
    assert not hasattr(panel.x_axis, "segment")
    assert "segment_name" not in panel.x_axis.settings_dict()
    assert not hasattr(panel, "rf_editor_tabs")
    assert panel.database_path_value() == str(database_path)
    assert panel.iq_storage_mode_value() == IQ_STORAGE_MEAN_IQ
    assert panel.saved_database_path_value() == str(saved_plot_path)
    assert panel.layout().indexOf(panel.controls_scroll) >= 0

    saved = panel.settings_dict()
    restored = stability.StabilityDiagramPanel()
    restored.refresh_targets(
        ("awg_0", "awg_1", "awg_2"),
        (1, 3, 5),
        ("set_0", "set_1"),
    )
    restored.load_settings(saved)
    assert restored.settings_dict() == saved
    assert restored.bias_t_group.isChecked() is True
    assert restored.bias_t_mode.currentData() == "fixed_time"
    assert restored.bias_t_duration_us.value() == 2.5
    assert restored.settle_time_us.value() == 75.5
    assert restored.acquisition_source.currentData() == "avg_buffer"
    assert restored.sweep_mode.currentData() == "software"
    assert restored.hardware_rep_delay_us.value() == 12.5
    assert restored.plot.color_range_settings() == {
        "i": {
            "auto": True,
            "minimum": -1.0,
            "maximum": 1.0,
        },
        "q": {
            "auto": True,
            "minimum": -1.0,
            "maximum": 1.0,
        },
        "magnitude": {
            "auto": False,
            "minimum": 10.0,
            "maximum": 100.0,
        },
        "phase": {
            "auto": False,
            "minimum": -90.0,
            "maximum": 45.0,
        },
    }
    assert restored.plot.visible_data() == ("i", "q", "magnitude")
    assert restored.saved_database_path.text() == str(saved_plot_path)
    assert restored.iq_storage_mode_value() == IQ_STORAGE_MEAN_IQ
    assert restored._preferred_saved_run_id == 29
    assert restored.saved_plot_data.currentData() == "q"
    assert restored.modulation_power_calibration_group.isChecked() is True
    assert restored.modulation_power_calibration_run_id.value() == 17
    assert restored.modulation_target_power_dbm.value() == -37.25

    dc_changes = []
    calibration_changes = []
    panel.dc_measure_changed.connect(
        lambda enabled, gain: dc_changes.append((enabled, gain))
    )
    panel.dc_calibration_changed.connect(
        lambda enabled, path, run_id: calibration_changes.append(
            (enabled, path, run_id)
        )
    )
    panel.set_dc_measure_context(
        "DC_In",
        True,
        2.0e6,
        True,
        "dc_calibration.db",
        4,
    )
    assert panel.dc_measure_mode.isChecked() is True
    assert panel.dc_measure_mode.isEnabled() is True
    assert panel.dc_measure_gain_v_per_a.isEnabled() is True
    assert panel.dc_calibration_group.isChecked() is True
    assert panel.dc_calibration_group.isEnabled() is True
    assert panel.dc_calibration_path.text() == "dc_calibration.db"
    assert panel.dc_calibration_run_id.value() == 4
    panel.dc_measure_gain_v_per_a.setValue(3.0e6)
    panel.dc_calibration_run_id.setValue(5)
    app.processEvents()
    assert dc_changes[-1] == (True, 3.0e6)
    assert calibration_changes[-1] == (True, "dc_calibration.db", 5)
    calibrated_settings = panel.settings_dict()
    restored.load_settings(calibrated_settings)
    assert restored.settings_dict() == calibrated_settings
    panel.set_dc_measure_context("RF_In", True, 4.0e6)
    assert panel.dc_measure_mode.isChecked() is False
    assert panel.dc_measure_mode.isEnabled() is False
    assert panel.dc_measure_gain_v_per_a.isEnabled() is False
    assert panel.dc_calibration_group.isChecked() is False
    assert panel.dc_calibration_group.isEnabled() is False

    panel.set_running(True, "running")
    assert panel.start_button.isEnabled() is False
    assert panel.stop_button.isEnabled() is True
    assert panel.single_shot_button.isEnabled() is False
    assert panel.trace_samples.isEnabled() is False
    assert panel.settle_time_us.isEnabled() is False
    assert panel.modulation_frequency_mhz.isEnabled() is False
    assert panel.bias_t_group.isEnabled() is False
    panel.set_stopping()
    assert panel.stop_button.isEnabled() is False
    panel.set_running(False, "ready")
    assert panel.start_button.isEnabled() is True
    assert panel.trace_samples.isEnabled() is True
    assert panel.settle_time_us.isEnabled() is True
    assert panel.modulation_frequency_mhz.isEnabled() is True
    assert panel.bias_t_group.isEnabled() is True
    panel.close()
    restored.close()


def test_stability_modulation_power_calibration_resolves_gain(monkeypatch):
    app = _application()
    calls = []

    class FakeCalibration:
        summary = SimpleNamespace(run_id=73)

        def build_gain_schedule(
            self,
            frequencies,
            target_power_dbm,
            **kwargs,
        ):
            calls.append(("schedule", tuple(frequencies), target_power_dbm, kwargs))
            return SimpleNamespace(gain_codes=np.asarray([4567], dtype=np.int32))

        def output_power_dbm(self, frequencies, gains, **kwargs):
            calls.append(("power", tuple(frequencies), tuple(gains), kwargs))
            return np.asarray([-31.125], dtype=np.float64)

    class FakeCalibrationDatabase:
        def __init__(self, path):
            calls.append(("database", str(path)))

        def output_calibration(self, board_type, frequencies, **kwargs):
            calls.append(("calibration", board_type, tuple(frequencies), kwargs))
            return FakeCalibration()

    monkeypatch.setattr(stability, "CalibrationDatabase", FakeCalibrationDatabase)
    panel = stability.StabilityDiagramPanel()
    panel.refresh_targets(("awg_0", "awg_1"), (1, 3))
    panel.apply_path_settings({
        **stability.DEFAULT_STABILITY_RF_PATH,
        "output_ch": 2,
        "output_board_type": "RF_Out",
        "output_nqz": 2,
        "output_att1_db": 7.25,
        "output_att2_db": 4.5,
        "output_filter_type": "bandpass",
        "output_filter_cutoff_ghz": 0.45,
        "output_filter_bandwidth_ghz": 0.1,
    })
    panel.modulation_frequency_mhz.setValue(450.0)
    panel.modulation_power_calibration_path.setText("gain_power.db")
    panel.modulation_power_calibration_run_id.setValue(0)
    panel.modulation_target_power_dbm.setValue(-31.0)
    panel.modulation_power_calibration_group.setChecked(True)
    app.processEvents()

    assert panel.resolve_modulation_gain(raise_on_error=True) == 4567
    assert panel.modulation_gain.value() == 4567
    assert panel._resolved_modulation_power_run_id == 73
    assert "Run 73" in panel.modulation_power_calibration_status.text()
    assert "gain 4567" in panel.modulation_power_calibration_status.text()
    assert calls[1] == (
        "calibration",
        "RF_Out",
        (450.0,),
        {
            "run_id": None,
            "nqz": 2,
            "output_filter_type": "bandpass",
            "output_filter_cutoff_ghz": 0.45,
            "output_filter_bandwidth_ghz": 0.1,
        },
    )
    assert calls[2][3] == {
        "output_att1_db": 7.25,
        "output_att2_db": 4.5,
        "max_entries": 1,
    }

    panel.modulation_target_power_dbm.setValue(-30.0)
    app.processEvents()
    assert panel._resolved_modulation_power_run_id is None
    assert "Settings changed" in panel.modulation_power_calibration_status.text()
    panel.close()


def test_stability_modulation_power_calibration_reports_lookup_failure(monkeypatch):
    app = _application()

    class MissingCalibrationDatabase:
        def __init__(self, path):
            self.path = path

        def output_calibration(self, *_args, **_kwargs):
            raise LookupError("no compatible RF_Out calibration run")

    monkeypatch.setattr(
        stability,
        "CalibrationDatabase",
        MissingCalibrationDatabase,
    )
    panel = stability.StabilityDiagramPanel()
    panel.apply_path_settings({
        **stability.DEFAULT_STABILITY_RF_PATH,
        "output_board_type": "RF_Out",
    })
    panel.modulation_power_calibration_path.setText("missing.db")
    panel.modulation_power_calibration_group.setChecked(True)
    app.processEvents()

    with pytest.raises(ValueError, match="no compatible RF_Out calibration run"):
        panel.resolve_modulation_gain(raise_on_error=True)

    assert "no compatible RF_Out calibration run" in (
        panel.modulation_power_calibration_status.text()
    )
    panel.close()


def _stored_stability_metadata():
    return {
        "created_at_utc": "2026-07-27T12:34:56+00:00",
        "gui_settings": {
            "qick": {
                "full_scale_mv": 800.0,
                "fir_rate_profile": "50_ksps",
                "fir_stability_capture_mode": (
                    "immediate_continuous_fir_output"
                ),
            },
            "stability_diagram": {
                "x_axis": {"output_name": "awg_0"},
                "y_axis": {"output_name": "awg_1"},
            },
        },
        "measurement_layout": {
            "iq_shape": [4, 2, 3, 2],
            "iq_unit": "ADC units",
            "measurement_mode": "raw_iq",
            "sample_rate_hz": 50_000.0,
            "sample_period_us": 20.0,
            "sweep_axes": [
                {
                    "parameter": "awg_0_set_0_voltage_mv",
                    "output_name": "awg_0",
                    "segment_name": stability.STABILITY_HOLD_SEGMENT,
                    "axis_kind": "amplitude",
                    "unit": "mV",
                    "count": 2,
                },
                {
                    "parameter": "awg_1_set_0_voltage_mv",
                    "output_name": "awg_1",
                    "segment_name": stability.STABILITY_HOLD_SEGMENT,
                    "axis_kind": "amplitude",
                    "unit": "mV",
                    "count": 2,
                },
            ],
        },
    }


def test_saved_stability_run_listing_filters_other_qick_runs(tmp_path):
    database_path = tmp_path / "stability.db"
    metadata = _stored_stability_metadata()
    programmable_delay = json.loads(json.dumps(metadata))
    programmable_delay["gui_settings"]["qick"][
        "fir_stability_capture_mode"
    ] = "programmable_fpga_delay"
    non_stability = json.loads(json.dumps(metadata))
    non_stability["gui_settings"]["qick"].pop("fir_stability_capture_mode")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE runs ("
            "run_id INTEGER PRIMARY KEY, "
            "qick_experiment_json TEXT)"
        )
        connection.execute(
            "INSERT INTO runs VALUES (?, ?)",
            (10, json.dumps(non_stability)),
        )
        connection.execute(
            "INSERT INTO runs VALUES (?, ?)",
            (11, json.dumps(metadata)),
        )
        connection.execute(
            "INSERT INTO runs VALUES (?, ?)",
            (12, json.dumps(programmable_delay)),
        )

    summaries = stability.list_stability_runs(database_path)

    assert [summary.run_id for summary in summaries] == [12, 11]
    assert summaries[0].x_axis_label == "awg_0"
    assert summaries[0].y_axis_label == "awg_1"
    assert summaries[0].sample_rate_hz == 50_000.0
    assert "Run 12" in summaries[0].display_label
    assert "50 kSPS" in summaries[0].display_label


def test_saved_stability_iq_arrays_restore_cartesian_grid(tmp_path):
    metadata = _stored_stability_metadata()
    metadata["gui_settings"]["qick"][
        "fir_stability_capture_mode"
    ] = "programmable_fpga_delay"
    iq = np.empty((4, 2, 3, 2), dtype=np.int32)
    for point_index in range(4):
        iq[point_index, :, :, 0] = point_index + 1
        iq[point_index, :, :, 1] = -(point_index + 1)
    arrays = {
        "metadata": metadata,
        "iq": iq,
        "iq_unit": "ADC units",
        "measurement_mode": "raw_iq",
        "sweep_coordinates": {
            "awg_0_set_0_voltage_mv": np.asarray(
                [
                    [-100.0, -100.0],
                    [-100.0, -100.0],
                    [100.0, 100.0],
                    [100.0, 100.0],
                ]
            ),
            "awg_1_set_0_voltage_mv": np.asarray(
                [
                    [-50.0, -50.0],
                    [50.0, 50.0],
                    [-50.0, -50.0],
                    [50.0, 50.0],
                ]
            ),
        },
    }

    result = stability.stability_result_from_stored_arrays(
        arrays,
        database_path=tmp_path / "stability.db",
        run_id=23,
    )

    np.testing.assert_allclose(result.x_voltage_mv, [-100.0, 100.0])
    np.testing.assert_allclose(result.y_voltage_mv, [-50.0, 50.0])
    np.testing.assert_allclose(result.i_mean, [[1.0, 3.0], [2.0, 4.0]])
    np.testing.assert_allclose(result.q_mean, [[-1.0, -3.0], [-2.0, -4.0]])
    assert result.repetition_count == 2
    assert result.samples_per_trace == 3
    assert result.sample_rate_hz == 50_000.0
    assert result.fir_rate_profile == "50_ksps"
    assert result.source_label == "QCoDeS Run 23"
    assert result.run_id == 23


def test_stability_overlay_selector_lists_run_and_emits_selection(tmp_path):
    app = _application()
    database_path = tmp_path / "stability.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE runs ("
            "run_id INTEGER PRIMARY KEY, "
            "qick_experiment_json TEXT)"
        )
        connection.execute(
            "INSERT INTO runs VALUES (?, ?)",
            (31, json.dumps(_stored_stability_metadata())),
        )

    selector = stability.StabilityOverlaySelector()
    selector.database_path.setText(str(database_path))
    selector.refresh_runs()
    emitted = []
    selector.load_requested.connect(
        lambda path, run_id, quantity: emitted.append(
            (path, run_id, quantity)
        )
    )
    selector.quantity_combo.setCurrentIndex(
        selector.quantity_combo.findData("phase")
    )
    selector.load_button.click()
    app.processEvents()

    assert selector.run_combo.count() == 1
    assert selector.run_combo.currentData() == 31
    assert emitted == [(str(database_path), 31, "phase")]
    selector.close()


def test_stability_panel_selects_and_requests_saved_diagram(tmp_path):
    app = _application()
    database_path = tmp_path / "stability.db"
    save_database_path = tmp_path / "new_stability.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE runs ("
            "run_id INTEGER PRIMARY KEY, "
            "qick_experiment_json TEXT)"
        )
        connection.execute(
            "INSERT INTO runs VALUES (?, ?)",
            (41, json.dumps(_stored_stability_metadata())),
        )

    panel = stability.StabilityDiagramPanel()
    panel.database_path.setText(str(save_database_path))
    panel.saved_database_path.setText(str(database_path))
    requested = []
    panel.saved_run_requested.connect(
        lambda path, run_id: requested.append((path, run_id))
    )
    panel.refresh_saved_runs()
    panel.saved_plot_data.setCurrentIndex(
        panel.saved_plot_data.findData("phase")
    )
    panel.load_saved_run_button.click()
    app.processEvents()

    assert panel.saved_run_combo.count() == 1
    assert panel.saved_run_combo.currentData() == 41
    assert requested == [(str(database_path), 41)]
    assert panel.database_path_value() == str(save_database_path)
    assert panel.plot.visible_data() == ("phase",)

    panel.set_saved_run_loading(True, run_id=41)
    assert panel.database_path.isEnabled() is True
    assert panel.saved_database_path.isEnabled() is False
    assert panel.refresh_saved_runs_button.isEnabled() is False
    assert panel.load_saved_run_button.isEnabled() is False
    panel.set_saved_run_loading(False)
    assert panel.database_path.isEnabled() is True
    assert panel.saved_database_path.isEnabled() is True
    assert panel.refresh_saved_runs_button.isEnabled() is True
    assert panel.load_saved_run_button.isEnabled() is True
    panel.close()


def test_saved_stability_run_loads_from_real_qcodes_database(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "stability_qcodes.db"
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging"))
    axes = (
        AmplitudeSweep(
            stability.STABILITY_HOLD_SEGMENT,
            "awg_0",
            -0.5,
            0.5,
            2,
        ),
        AmplitudeSweep(
            stability.STABILITY_HOLD_SEGMENT,
            "awg_1",
            -0.25,
            0.25,
            2,
        ),
    )
    iq = np.empty((4, 1, 2, 2), dtype=np.int32)
    for point_index in range(4):
        iq[point_index, :, :, 0] = 10 + point_index
        iq[point_index, :, :, 1] = -20 - point_index
    ddr_result = FineTuneDdrResult(
        sweep_points=np.asarray(
            [
                [-0.5, -0.25],
                [-0.5, 0.25],
                [0.5, -0.25],
                [0.5, 0.25],
            ]
        ),
        iq=iq,
        sweep_axes=axes,
        sweep_shape=(2, 2),
        cross_capacitance=np.eye(2),
    )
    gui_settings = {
        "qick": {
            "fabric_mhz": 300.0,
            "tproc_mhz": 300.0,
            "full_scale_mv": 800.0,
            "fir_rate_profile": "50_ksps",
            "fir_stability_capture_mode": (
                "programmable_fpga_delay"
            ),
        },
        "stability_diagram": {
            "x_axis": {"output_name": "awg_0"},
            "y_axis": {"output_name": "awg_1"},
        },
        "awg": {"cross_capacitance": np.eye(2).tolist()},
    }
    dataset, _row_count = store_qick_result(
        ddr_result,
        run_config=QcodesRunConfig(
            database_path=str(database_path),
            experiment_name="Stability loader test",
            sample_name="simulated device",
            sample_rate_hz=50_000.0,
        ),
        connection_config=QickConnectionConfig(
            "192.0.2.10",
            8888,
            "myqick",
        ),
        program_summary={},
        gui_settings=gui_settings,
        rf_settings={},
        iq_storage_mode=IQ_STORAGE_MEAN_IQ,
    )

    summaries = stability.list_stability_runs(database_path)
    result = stability.load_stability_diagram_run(
        database_path,
        dataset.run_id,
    )

    assert [summary.run_id for summary in summaries] == [dataset.run_id]
    np.testing.assert_allclose(result.x_voltage_mv, [-400.0, 400.0])
    np.testing.assert_allclose(result.y_voltage_mv, [-200.0, 200.0])
    np.testing.assert_allclose(result.i_mean, [[10.0, 12.0], [11.0, 13.0]])
    np.testing.assert_allclose(result.q_mean, [[-20.0, -22.0], [-21.0, -23.0]])
    assert result.source_label == f"QCoDeS Run {dataset.run_id}"
    assert result.sample_rate_hz == 50_000.0
    assert result.repetition_count == 1
    assert result.samples_per_trace == 2
