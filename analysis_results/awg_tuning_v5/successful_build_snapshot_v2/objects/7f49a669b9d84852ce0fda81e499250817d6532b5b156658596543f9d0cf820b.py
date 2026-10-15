"""Tests for the AWG Cartesian two-dimensional result map.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from itertools import product
import json
import os
import sqlite3
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt5 import QtWidgets
import pytest

import awg_sweep_map as awg_map
import DCWaveform_Generator as gui
from dc_waveform_core import QickRampRateSweepSpec, QickSweepSpec
from qick_fine_tune_sweep import (
    AmplitudeSweep,
    FineTuneDdrResult,
    RampDurationSweep,
)
from qick_qcodes_experiment import (
    QCODES_STAGING_ENV,
    IQ_STORAGE_MEAN_IQ,
    QcodesRunConfig,
    QickConnectionConfig,
    store_qick_result,
)


def _application():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _axis(output_name, segment_name, points):
    return SimpleNamespace(
        output_name=output_name,
        segment_name=segment_name,
        start=float(points[0]),
        stop=float(points[-1]),
        count=len(points),
    )


def _two_axis_result():
    x_points = (-0.5, 0.5)
    y_points = (-0.25, 0.0, 0.25)
    coordinates = np.asarray(tuple(product(x_points, y_points)), dtype=float)
    iq = np.empty((coordinates.shape[0], 2, 2, 2), dtype=np.int32)
    for point_index, (x_value, y_value) in enumerate(coordinates):
        base_i = int(100 * x_value + 20 * y_value)
        base_q = int(-40 * x_value + 80 * y_value)
        for repetition in range(2):
            for sample in range(2):
                iq[point_index, repetition, sample, 0] = (
                    base_i + repetition + sample
                )
                iq[point_index, repetition, sample, 1] = (
                    base_q - repetition - sample
                )
    return SimpleNamespace(
        sweep_axes=(
            _axis("awg_0", "set_1", x_points),
            _axis("awg_1", "set_2", y_points),
        ),
        sweep_points=coordinates,
        iq=iq,
        sample_rate_hz=50_000.0,
    )


def _four_axis_result():
    x_points = (-1.0, 1.0)
    y_points = (-0.5, 0.5)
    z_points = (-0.25, 0.25)
    w_points = (-1.0, 1.0)
    coordinates = np.asarray(
        tuple(product(x_points, y_points, z_points, w_points)),
        dtype=float,
    )
    iq = np.empty((coordinates.shape[0], 2, 2, 2), dtype=np.float64)
    for point_index, (x_value, y_value, z_value, w_value) in enumerate(
        coordinates
    ):
        iq[point_index, ..., 0] = (
            100.0 * x_value
            + 40.0 * y_value
            + 20.0 * z_value
            + 8.0 * w_value
        )
        iq[point_index, ..., 1] = (
            -80.0 * x_value
            + 30.0 * y_value
            - 12.0 * z_value
            + 4.0 * w_value
        )
    return SimpleNamespace(
        sweep_axes=(
            _axis("awg_0", "set_x", x_points),
            _axis("awg_1", "set_y", y_points),
            _axis("awg_2", "set_z", z_points),
            _axis("awg_3", "set_w", w_points),
        ),
        sweep_points=coordinates,
        iq=iq,
        sample_rate_hz=50_000.0,
    )


def test_reduce_two_axis_awg_map_and_axis_swap():
    ddr_result = _two_axis_result()
    result = awg_map.reduce_awg_sweep_map(
        ddr_result,
        x_axis_key=("awg_0", "set_1"),
        y_axis_key=("awg_1", "set_2"),
        full_scale_mv=800.0,
    )

    np.testing.assert_allclose(result.x_values_mv, (-400.0, 400.0))
    np.testing.assert_allclose(result.y_values_mv, (-200.0, 0.0, 200.0))
    assert result.i_mean.shape == (3, 2)
    assert result.q_mean.shape == (3, 2)
    assert result.repetition_count == 2
    assert result.samples_per_trace == 2
    assert result.sample_rate_hz == 50_000.0
    assert result.source_points_per_cell == 1
    assert result.averaged_axis_labels == ()

    expected_i = np.asarray(
        (
            (-54.0, 46.0),
            (-49.0, 51.0),
            (-44.0, 56.0),
        )
    )
    expected_q = np.asarray(
        (
            (-1.0, -41.0),
            (19.0, -21.0),
            (39.0, -1.0),
        )
    )
    np.testing.assert_allclose(result.i_mean, expected_i)
    np.testing.assert_allclose(result.q_mean, expected_q)
    np.testing.assert_allclose(
        result.magnitude,
        np.hypot(expected_i, expected_q),
    )
    np.testing.assert_allclose(
        result.angle_deg,
        np.degrees(np.arctan2(expected_q, expected_i)),
    )

    swapped = awg_map.reduce_awg_sweep_map(
        ddr_result,
        x_axis_key=("awg_1", "set_2"),
        y_axis_key=("awg_0", "set_1"),
        full_scale_mv=800.0,
    )
    np.testing.assert_allclose(swapped.i_mean, expected_i.T)
    np.testing.assert_allclose(swapped.q_mean, expected_q.T)


def test_reduce_map_preserves_rf_duration_axis_in_microseconds():
    voltage_points = (-0.5, 0.5)
    duration_points = (1.0, 2.0, 3.0)
    coordinates = np.asarray(
        tuple(product(voltage_points, duration_points)),
        dtype=float,
    )
    iq = np.zeros((coordinates.shape[0], 1, 2, 2), dtype=np.int16)
    for point_index, (voltage, duration_us) in enumerate(coordinates):
        iq[point_index, ..., 0] = int(100 * voltage + duration_us)
        iq[point_index, ..., 1] = int(-100 * voltage + duration_us)
    result = awg_map.reduce_awg_sweep_map(
        SimpleNamespace(
            sweep_axes=(
                _axis("awg_0", "gate", voltage_points),
                SimpleNamespace(
                    output_name="rf_gen_0",
                    segment_name="gate",
                    start=duration_points[0],
                    stop=duration_points[-1],
                    count=len(duration_points),
                    axis_kind="rf_duration",
                    segment_length_mode="fixed",
                ),
            ),
            sweep_points=coordinates,
            iq=iq,
            sample_rate_hz=50_000.0,
        ),
        x_axis_key=("rf_gen_0", "gate"),
        y_axis_key=("awg_0", "gate"),
        full_scale_mv=800.0,
    )

    np.testing.assert_allclose(result.x_values, duration_points)
    np.testing.assert_allclose(result.y_values, (-400.0, 400.0))
    assert result.x_unit == "us"
    assert result.y_unit == "mV"
    assert result.x_axis_label == "rf_gen_0 / gate RF duration"
    assert result.y_axis_label == "awg_0 / gate"


def test_reduce_map_preserves_predefined_rf_n_and_tau_axes():
    n_points = (2.0, 3.0, 4.0)
    tau_points = (5.0, 10.0)
    coordinates = np.asarray(
        tuple(product(n_points, tau_points)),
        dtype=float,
    )
    iq = np.zeros((coordinates.shape[0], 1, 1, 2), dtype=np.int16)
    result = awg_map.reduce_awg_sweep_map(
        SimpleNamespace(
            sweep_axes=(
                SimpleNamespace(
                    output_name="rf_gen_0_cpmg_N",
                    segment_name="gate",
                    start=2.0,
                    stop=4.0,
                    count=3,
                    axis_kind="rf_template_n",
                ),
                SimpleNamespace(
                    output_name="rf_gen_0_cpmg_tau",
                    segment_name="gate",
                    start=5.0,
                    stop=10.0,
                    count=2,
                    axis_kind="rf_template_tau",
                ),
            ),
            sweep_points=coordinates,
            iq=iq,
            sample_rate_hz=50_000.0,
        ),
        x_axis_key=("rf_gen_0_cpmg_N", "gate"),
        y_axis_key=("rf_gen_0_cpmg_tau", "gate"),
        full_scale_mv=800.0,
    )

    np.testing.assert_allclose(result.x_values, n_points)
    np.testing.assert_allclose(result.y_values, tau_points)
    assert result.x_unit == "count"
    assert result.y_unit == "us"
    assert result.x_axis_label.endswith("template N")
    assert result.y_axis_label.endswith("template tau")

    np.testing.assert_allclose(
        awg_map._stored_axis_native_values(
            n_points,
            {"axis_kind": "rf_template_n", "unit": ""},
            full_scale_mv=800.0,
        ),
        n_points,
    )
    np.testing.assert_allclose(
        awg_map._stored_axis_native_values(
            (5000.0, 10000.0),
            {"axis_kind": "rf_template_tau", "unit": "ns"},
            full_scale_mv=800.0,
        ),
        tau_points,
    )


def test_reduce_map_preserves_ramp_duration_axis_and_derived_rate_label():
    duration_points = (0.08, 0.10, 0.12)
    voltage_points = (-0.5, 0.5)
    coordinates = np.asarray(
        tuple(product(duration_points, voltage_points)),
        dtype=float,
    )
    iq = np.zeros((coordinates.shape[0], 1, 2, 2), dtype=np.int16)
    for point_index, (duration_us, voltage) in enumerate(coordinates):
        iq[point_index, ..., 0] = int(100 * voltage + 10 * duration_us)
        iq[point_index, ..., 1] = int(-100 * voltage + 10 * duration_us)
    result = awg_map.reduce_awg_sweep_map(
        SimpleNamespace(
            sweep_axes=(
                SimpleNamespace(
                    output_name="all_awg_outputs",
                    segment_name="ramp_0_to_1",
                    start=duration_points[0],
                    stop=duration_points[-1],
                    count=len(duration_points),
                    axis_kind="ramp_duration",
                ),
                _axis("awg_0", "set_1", voltage_points),
            ),
            sweep_points=coordinates,
            iq=iq,
            sample_rate_hz=50_000.0,
        ),
        x_axis_key=("all_awg_outputs", "ramp_0_to_1"),
        y_axis_key=("awg_0", "set_1"),
        full_scale_mv=800.0,
    )

    np.testing.assert_allclose(result.x_values, duration_points)
    np.testing.assert_allclose(result.y_values, (-400.0, 400.0))
    assert result.x_unit == "us"
    assert result.y_unit == "mV"
    assert result.x_axis_label == (
        "ramp_0_to_1 RAMP duration (rate derived)"
    )


def test_reduce_map_supports_two_independent_ramp_duration_axes():
    first_points = (0.08, 0.10, 0.12)
    second_points = (0.10, 0.12, 0.14, 0.16)
    coordinates = np.asarray(
        tuple(product(first_points, second_points)),
        dtype=float,
    )
    iq = np.zeros((coordinates.shape[0], 1, 1, 2), dtype=np.int32)
    for point_index, (first, second) in enumerate(coordinates):
        iq[point_index, 0, 0, 0] = int(first * 1000 + second * 100)
        iq[point_index, 0, 0, 1] = int(first * 200 - second * 500)
    result = awg_map.reduce_awg_sweep_map(
        SimpleNamespace(
            sweep_axes=(
                SimpleNamespace(
                    output_name="all_awg_outputs",
                    segment_name="ramp_0_to_1",
                    start=first_points[0],
                    stop=first_points[-1],
                    count=len(first_points),
                    axis_kind="ramp_duration",
                ),
                SimpleNamespace(
                    output_name="all_awg_outputs",
                    segment_name="ramp_1_to_2",
                    start=second_points[0],
                    stop=second_points[-1],
                    count=len(second_points),
                    axis_kind="ramp_duration",
                ),
            ),
            sweep_points=coordinates,
            iq=iq,
            sample_rate_hz=50_000.0,
        ),
        x_axis_key=("all_awg_outputs", "ramp_0_to_1"),
        y_axis_key=("all_awg_outputs", "ramp_1_to_2"),
        full_scale_mv=800.0,
    )

    np.testing.assert_allclose(result.x_values, first_points)
    np.testing.assert_allclose(result.y_values, second_points)
    assert result.x_unit == "us"
    assert result.y_unit == "us"
    assert result.x_axis_label == (
        "ramp_0_to_1 RAMP duration (rate derived)"
    )
    assert result.y_axis_label == (
        "ramp_1_to_2 RAMP duration (rate derived)"
    )


def test_reduce_three_axes_averages_unselected_axis():
    x_points = (-1.0, 1.0)
    y_points = (-0.5, 0.5)
    z_points = (-0.25, 0.25)
    coordinates = np.asarray(
        tuple(product(x_points, y_points, z_points)),
        dtype=float,
    )
    iq = np.empty((coordinates.shape[0], 1, 1, 2), dtype=np.int32)
    for point_index, (x_value, y_value, z_value) in enumerate(coordinates):
        iq[point_index, 0, 0, 0] = int(10 * x_value + 4 * z_value)
        iq[point_index, 0, 0, 1] = int(20 * y_value - 4 * z_value)
    ddr_result = SimpleNamespace(
        sweep_axes=(
            _axis("awg_0", "set_0", x_points),
            _axis("awg_1", "set_0", y_points),
            _axis("awg_2", "set_3", z_points),
        ),
        sweep_points=coordinates,
        iq=iq,
    )

    result = awg_map.reduce_awg_sweep_map(
        ddr_result,
        x_axis_key=("awg_0", "set_0"),
        y_axis_key=("awg_1", "set_0"),
        full_scale_mv=100.0,
    )

    np.testing.assert_allclose(result.i_mean, ((-10.0, 10.0),) * 2)
    np.testing.assert_allclose(
        result.q_mean,
        ((-10.0, -10.0), (10.0, 10.0)),
    )
    assert result.source_points_per_cell == 2
    assert result.averaged_axis_labels == ("awg_2 / set_3",)


def test_reduce_four_axes_supports_fixed_and_averaged_axes_independently():
    ddr_result = _four_axis_result()
    result = awg_map.reduce_awg_sweep_map(
        ddr_result,
        x_axis_key=("awg_0", "set_x"),
        y_axis_key=("awg_1", "set_y"),
        full_scale_mv=100.0,
        fixed_axis_values={("awg_2", "set_z"): 0.25},
    )

    np.testing.assert_allclose(result.x_values, (-100.0, 100.0))
    np.testing.assert_allclose(result.y_values, (-50.0, 50.0))
    np.testing.assert_allclose(
        result.i_mean,
        ((-115.0, 85.0), (-75.0, 125.0)),
    )
    np.testing.assert_allclose(
        result.q_mean,
        ((62.0, -98.0), (92.0, -68.0)),
    )
    assert result.source_points_per_cell == 2
    assert result.fixed_axis_values == ((("awg_2", "set_z"), 0.25),)
    assert result.fixed_axis_labels == ("awg_2 / set_z = 25 mV",)
    assert result.averaged_axis_labels == ("awg_3 / set_w",)
    assert result.source is not None

    fully_sliced = awg_map.reduce_awg_sweep_source(
        result.source,
        x_axis_key=("awg_0", "set_x"),
        y_axis_key=("awg_1", "set_y"),
        fixed_axis_values={
            ("awg_2", "set_z"): 0.25,
            ("awg_3", "set_w"): 1.0,
        },
    )
    assert fully_sliced.source_points_per_cell == 1
    assert fully_sliced.averaged_axis_labels == ()
    assert len(fully_sliced.fixed_axis_labels) == 2


def test_reduce_awg_map_auto_scales_current_to_nanoamps():
    ddr_result = _two_axis_result()
    current_iq = ddr_result.iq.astype(np.float64) * 1.0e-9
    result = awg_map.reduce_awg_sweep_map(
        ddr_result,
        x_axis_key=("awg_0", "set_1"),
        y_axis_key=("awg_1", "set_2"),
        full_scale_mv=800.0,
        iq_values=current_iq,
        value_unit="A",
        measurement_mode="dc_current_iq",
    )

    assert result.value_unit == "nA"
    assert result.base_value_unit == "A"
    assert result.display_scale == 1.0e9
    np.testing.assert_allclose(
        result.i_mean,
        awg_map.reduce_awg_sweep_map(
            ddr_result,
            x_axis_key=("awg_0", "set_1"),
            y_axis_key=("awg_1", "set_2"),
            full_scale_mv=800.0,
        ).i_mean,
    )


def test_reduce_awg_map_rejects_duplicate_or_unknown_axes():
    ddr_result = _two_axis_result()
    with pytest.raises(ValueError, match="different"):
        awg_map.reduce_awg_sweep_map(
            ddr_result,
            x_axis_key=("awg_0", "set_1"),
            y_axis_key=("awg_0", "set_1"),
            full_scale_mv=800.0,
        )
    with pytest.raises(ValueError, match="not present"):
        awg_map.reduce_awg_sweep_map(
            ddr_result,
            x_axis_key=("awg_0", "set_1"),
            y_axis_key=("awg_7", "set_7"),
            full_scale_mv=800.0,
        )


def _stored_awg_metadata():
    return {
        "created_at_utc": "2026-07-27T13:45:00+00:00",
        "gui_settings": {
            "qick": {
                "full_scale_mv": 800.0,
                "fir_rate_profile": "50_ksps",
            },
            "experiment": {
                "sweep_map": {
                    "x_axis": {
                        "output_name": "all_awg_outputs",
                        "segment_name": "ramp_0_to_1",
                    },
                    "y_axis": {
                        "output_name": "awg_0",
                        "segment_name": "set_1",
                    },
                },
            },
        },
        "measurement_layout": {
            "iq_shape": [12, 2, 3, 2],
            "iq_unit": "ADC units",
            "measurement_mode": "raw_iq",
            "sample_rate_hz": 50_000.0,
            "sample_period_us": 20.0,
            "sweep_axes": [
                {
                    "parameter": "awg_0_set_1_voltage_mv",
                    "output_name": "awg_0",
                    "segment_name": "set_1",
                    "axis_kind": "amplitude",
                    "unit": "mV",
                    "count": 2,
                },
                {
                    "parameter": "awg_1_set_2_voltage_mv",
                    "output_name": "awg_1",
                    "segment_name": "set_2",
                    "axis_kind": "amplitude",
                    "unit": "mV",
                    "count": 2,
                },
                {
                    "parameter": "ramp_0_to_1_duration_us",
                    "output_name": "all_awg_outputs",
                    "segment_name": "ramp_0_to_1",
                    "axis_kind": "ramp_duration",
                    "unit": "us",
                    "count": 3,
                },
            ],
        },
    }


def test_saved_awg_run_listing_filters_stability_and_uses_saved_axes(tmp_path):
    database_path = tmp_path / "awg_sweeps.db"
    metadata = _stored_awg_metadata()
    stability_metadata = json.loads(json.dumps(metadata))
    stability_metadata["gui_settings"]["qick"][
        "fir_stability_capture_mode"
    ] = "immediate_continuous_fir_output"
    programmable_stability_metadata = json.loads(json.dumps(metadata))
    programmable_stability_metadata["gui_settings"]["qick"][
        "fir_stability_capture_mode"
    ] = "programmable_fpga_delay"
    one_axis_metadata = json.loads(json.dumps(metadata))
    one_axis_metadata["measurement_layout"]["sweep_axes"] = (
        one_axis_metadata["measurement_layout"]["sweep_axes"][:1]
    )
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE runs ("
            "run_id INTEGER PRIMARY KEY, "
            "qick_experiment_json TEXT)"
        )
        connection.execute(
            "INSERT INTO runs VALUES (?, ?)",
            (20, json.dumps(stability_metadata)),
        )
        connection.execute(
            "INSERT INTO runs VALUES (?, ?)",
            (21, json.dumps(one_axis_metadata)),
        )
        connection.execute(
            "INSERT INTO runs VALUES (?, ?)",
            (22, json.dumps(metadata)),
        )
        connection.execute(
            "INSERT INTO runs VALUES (?, ?)",
            (23, json.dumps(programmable_stability_metadata)),
        )

    summaries = awg_map.list_awg_sweep_runs(database_path)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.run_id == 22
    assert summary.x_axis_label == (
        "ramp_0_to_1 RAMP duration (rate derived)"
    )
    assert summary.y_axis_label == "awg_0 / set_1"
    assert summary.x_points == 3
    assert summary.y_points == 2
    assert summary.sweep_axis_count == 3
    assert "Run 22" in summary.display_label
    assert "+1 averaged axis" in summary.display_label
    assert "50 kSPS" in summary.display_label


def test_saved_awg_arrays_restore_selected_axes_and_average_other_axis(
    tmp_path,
):
    metadata = _stored_awg_metadata()
    voltage_x = (-400.0, 400.0)
    voltage_other = (-200.0, 200.0)
    ramp_duration = (0.08, 0.10, 0.12)
    coordinates = np.asarray(
        tuple(product(voltage_x, voltage_other, ramp_duration)),
        dtype=np.float64,
    )
    iq = np.empty((coordinates.shape[0], 2, 3, 2), dtype=np.int32)
    for point_index, (voltage, other, duration_us) in enumerate(coordinates):
        iq[point_index, ..., 0] = int(voltage / 10 + other / 20)
        iq[point_index, ..., 1] = int(duration_us * 1000 + other / 20)
    arrays = {
        "metadata": metadata,
        "iq": iq,
        "iq_unit": "ADC units",
        "measurement_mode": "raw_iq",
        "sweep_coordinates": {
            "awg_0_set_1_voltage_mv": np.repeat(
                coordinates[:, 0, None],
                2,
                axis=1,
            ),
            "awg_1_set_2_voltage_mv": np.repeat(
                coordinates[:, 1, None],
                2,
                axis=1,
            ),
            "ramp_0_to_1_duration_us": np.repeat(
                coordinates[:, 2, None],
                2,
                axis=1,
            ),
        },
    }

    result = awg_map.awg_sweep_result_from_stored_arrays(
        arrays,
        database_path=tmp_path / "awg_sweeps.db",
        run_id=37,
    )

    np.testing.assert_allclose(result.x_values, ramp_duration)
    np.testing.assert_allclose(result.y_values, voltage_x)
    assert result.x_unit == "us"
    assert result.y_unit == "mV"
    assert result.i_mean.shape == (2, 3)
    assert result.q_mean.shape == (2, 3)
    np.testing.assert_allclose(result.i_mean, [[-40.0] * 3, [40.0] * 3])
    np.testing.assert_allclose(
        result.q_mean,
        [[80.0, 100.0, 120.0], [80.0, 100.0, 120.0]],
    )
    assert result.source_points_per_cell == 2
    assert result.averaged_axis_labels == ("awg_1 / set_2",)
    assert result.source_label == "QCoDeS Run 37"
    assert result.run_id == 37
    assert result.sample_rate_hz == 50_000.0
    assert result.source is not None
    sliced = awg_map.reduce_awg_sweep_source(
        result.source,
        x_axis_key=("all_awg_outputs", "ramp_0_to_1"),
        y_axis_key=("awg_0", "set_1"),
        fixed_axis_values={("awg_1", "set_2"): 0.25},
    )
    assert sliced.source_points_per_cell == 1
    assert sliced.database_path == str(
        (tmp_path / "awg_sweeps.db").resolve()
    )
    assert sliced.run_id == 37


def test_saved_awg_arrays_restore_rf_frequency_power_and_hold_units(
    tmp_path,
):
    metadata = _stored_awg_metadata()
    metadata["gui_settings"]["experiment"]["sweep_map"] = {
        "x_axis": {
            "output_name": "rf_gen_0",
            "segment_name": "set_1",
        },
        "y_axis": {
            "output_name": "rf_gen_0",
            "segment_name": "set_1_power",
        },
    }
    metadata["measurement_layout"]["sweep_axes"] = [
        {
            "parameter": "rf_gen_0_set_1_frequency_mhz",
            "output_name": "rf_gen_0",
            "segment_name": "set_1",
            "axis_kind": "rf_frequency",
            "unit": "MHz",
            "count": 2,
        },
        {
            "parameter": "rf_gen_0_set_1_output_power_dbm",
            "output_name": "rf_gen_0",
            "segment_name": "set_1_power",
            "axis_kind": "rf_power",
            "unit": "dBm",
            "count": 2,
        },
        {
            "parameter": "all_awg_outputs_set_2_hold_duration_us",
            "output_name": "all_awg_outputs",
            "segment_name": "set_2",
            "axis_kind": "hold_duration",
            "unit": "us",
            "count": 2,
        },
    ]
    frequencies_mhz = (100.0, 250.0)
    powers_dbm = (-30.0, -20.0)
    hold_durations_us = (1.0, 4.0)
    coordinates = np.asarray(
        tuple(product(frequencies_mhz, powers_dbm, hold_durations_us)),
        dtype=np.float64,
    )
    iq = np.empty((coordinates.shape[0], 1, 2, 2), dtype=np.int32)
    for point_index, (frequency, power, hold_us) in enumerate(coordinates):
        iq[point_index, ..., 0] = int(frequency + hold_us)
        iq[point_index, ..., 1] = int(10.0 * power)
    arrays = {
        "metadata": metadata,
        "iq": iq,
        "iq_unit": "ADC units",
        "measurement_mode": "raw_iq",
        "sweep_coordinates": {
            axis["parameter"]: np.repeat(
                coordinates[:, column, None],
                iq.shape[1],
                axis=1,
            )
            for column, axis in enumerate(
                metadata["measurement_layout"]["sweep_axes"]
            )
        },
    }

    result = awg_map.awg_sweep_result_from_stored_arrays(
        arrays,
        database_path=tmp_path / "rf_awg_sweeps.db",
        run_id=41,
    )

    np.testing.assert_allclose(result.x_values, frequencies_mhz)
    np.testing.assert_allclose(result.y_values, powers_dbm)
    assert result.x_unit == "MHz"
    assert result.y_unit == "dBm"
    assert result.x_axis_label == "rf_gen_0 / set_1 RF frequency"
    assert result.y_axis_label == "rf_gen_0 / set_1_power RF power"
    assert result.averaged_axis_labels == ("set_2 SET hold duration",)
    assert result.source_points_per_cell == 2
    assert result.source is not None

    hold_map = awg_map.reduce_awg_sweep_source(
        result.source,
        x_axis_key=("all_awg_outputs", "set_2"),
        y_axis_key=("rf_gen_0", "set_1"),
        fixed_axis_values={("rf_gen_0", "set_1_power"): -30.0},
    )
    np.testing.assert_allclose(hold_map.x_values, hold_durations_us)
    np.testing.assert_allclose(hold_map.y_values, frequencies_mhz)
    assert hold_map.x_unit == "us"
    assert hold_map.y_unit == "MHz"
    assert hold_map.fixed_axis_labels == (
        "rf_gen_0 / set_1_power RF power = -30 dBm",
    )


def test_awg_sweep_selector_lists_run_and_emits_selection(tmp_path):
    app = _application()
    database_path = tmp_path / "awg_sweeps.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE runs ("
            "run_id INTEGER PRIMARY KEY, "
            "qick_experiment_json TEXT)"
        )
        connection.execute(
            "INSERT INTO runs VALUES (?, ?)",
            (42, json.dumps(_stored_awg_metadata())),
        )

    selector = awg_map.AwgSweepRunSelector(
        default_database_path=str(database_path)
    )
    selector.refresh_runs()
    emitted = []
    selector.load_requested.connect(
        lambda path, run_id: emitted.append((path, run_id))
    )
    selector.load_button.click()
    app.processEvents()

    assert selector.run_combo.count() == 1
    assert selector.run_combo.currentData() == 42
    assert emitted == [(str(database_path), 42)]
    selector.set_loading(True, run_id=42)
    assert selector.database_path.isEnabled() is False
    assert selector.load_button.isEnabled() is False
    selector.set_loading(False)
    assert selector.database_path.isEnabled() is True
    assert selector.load_button.isEnabled() is True
    selector.close()


def test_saved_awg_run_loads_from_real_qcodes_database(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "awg_qcodes.db"
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging"))
    axes = (
        AmplitudeSweep("set_1", "awg_0", -0.5, 0.5, 2),
        RampDurationSweep(
            "ramp_0_to_1",
            0.08,
            0.12,
            3,
            sequence_fabric_mhz=300.0,
        ),
    )
    coordinates = np.asarray(
        tuple(product((-0.5, 0.5), (0.08, 0.10, 0.12))),
        dtype=np.float64,
    )
    iq = np.empty((coordinates.shape[0], 2, 2, 2), dtype=np.int32)
    for point_index, (voltage, duration_us) in enumerate(coordinates):
        iq[point_index, ..., 0] = int(voltage * 100)
        iq[point_index, ..., 1] = int(duration_us * 1000)
    ddr_result = FineTuneDdrResult(
        sweep_points=coordinates,
        iq=iq,
        sweep_axes=axes,
        sweep_shape=(2, 3),
        cross_capacitance=np.eye(1),
        sample_rate_hz=50_000.0,
        fir_rate_profile="50_ksps",
    )
    gui_settings = {
        "qick": {
            "fabric_mhz": 300.0,
            "tproc_mhz": 300.0,
            "full_scale_mv": 800.0,
            "fir_rate_profile": "50_ksps",
        },
        "experiment": {
            "sweep_map": {
                "x_axis": {
                    "output_name": "all_awg_outputs",
                    "segment_name": "ramp_0_to_1",
                },
                "y_axis": {
                    "output_name": "awg_0",
                    "segment_name": "set_1",
                },
            },
        },
        "awg": {"cross_capacitance": np.eye(1).tolist()},
    }
    dataset, _row_count = store_qick_result(
        ddr_result,
        run_config=QcodesRunConfig(
            database_path=str(database_path),
            experiment_name="AWG loader test",
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

    summaries = awg_map.list_awg_sweep_runs(database_path)
    result = awg_map.load_awg_sweep_run(database_path, dataset.run_id)

    assert [summary.run_id for summary in summaries] == [dataset.run_id]
    np.testing.assert_allclose(result.x_values, [0.08, 0.10, 0.12])
    np.testing.assert_allclose(result.y_values, [-400.0, 400.0])
    np.testing.assert_allclose(
        result.i_mean,
        [[-50.0, -50.0, -50.0], [50.0, 50.0, 50.0]],
    )
    np.testing.assert_allclose(
        result.q_mean,
        [[80.0, 100.0, 120.0], [80.0, 100.0, 120.0]],
    )
    assert result.source_label == f"QCoDeS Run {dataset.run_id}"
    assert result.sample_rate_hz == 50_000.0
    assert result.repetition_count == 2
    assert result.samples_per_trace == 2


def test_experiment_panel_axis_selection_and_result_plot():
    app = _application()
    window = gui.MainWindow()
    window._sweep_specs = [
        QickSweepSpec("set_1", "awg_0", -0.5, 0.5, 2),
        QickSweepSpec("set_2", "awg_1", -0.25, 0.25, 3),
    ]
    window._refresh_sweep_overlay()
    panel = window._experiment_panel

    assert panel.sweep_map_group.isHidden() is True
    assert panel.sweep_map_x.count() == 2
    assert panel.sweep_map_y.count() == 2
    assert panel.selected_sweep_axis_keys() == (
        ("awg_0", "set_1"),
        ("awg_1", "set_2"),
    )
    panel.sweep_map_x.setCurrentIndex(1)
    app.processEvents()
    assert panel.selected_sweep_axis_keys() == (
        ("awg_1", "set_2"),
        ("awg_0", "set_1"),
    )

    ddr_result = _two_axis_result()
    stored = SimpleNamespace(
        run_id=123,
        row_count=12,
        database_path="test.db",
        ddr_result=ddr_result,
        rf_settings={},
    )
    window._on_experiment_finished(stored)
    app.processEvents()
    if hasattr(window._awg_sweep_plot, "_result"):
        plotted = window._awg_sweep_plot._result
        assert plotted is not None
        assert plotted.i_mean.shape == (2, 3)
        assert set(window._awg_sweep_plot.images) == {
            "i",
            "q",
            "magnitude",
            "angle",
        }
        assert set(window._awg_sweep_plot.color_bars) == {
            "i",
            "q",
            "magnitude",
            "angle",
        }
        assert all(
            color_bar is not None
            for color_bar in window._awg_sweep_plot.color_bars.values()
        )
        assert window._awg_sweep_plot.visible_data() == (
            "i",
            "q",
            "magnitude",
            "angle",
        )
        window._awg_sweep_plot.load_visible_data(["q", "magnitude"])
        app.processEvents()
        assert window._awg_sweep_plot.visible_data() == ("q", "magnitude")
        assert window._awg_sweep_plot.plot_cells["i"].isHidden() is True
        assert window._awg_sweep_plot.plot_cells["q"].isHidden() is False
        assert (
            window._awg_sweep_plot.plot_cells["magnitude"].isHidden()
            is False
        )
        assert window._awg_sweep_plot.plot_cells["angle"].isHidden() is True
        magnitude_bar = window._awg_sweep_plot.color_bars["magnitude"]
        assert magnitude_bar.interactive is True
        magnitude_bar.setLevels((2.5, 25.0))
        magnitude_bar.sigLevelsChanged.emit(magnitude_bar)
        app.processEvents()
        magnitude_control = window._awg_sweep_plot.range_controls["magnitude"]
        assert magnitude_control.auto_range.isChecked() is False
        np.testing.assert_allclose(
            (
                magnitude_control.minimum.value(),
                magnitude_control.maximum.value(),
            ),
            (2.5, 25.0),
        )
        np.testing.assert_allclose(
            window._awg_sweep_plot.images["magnitude"].getLevels(),
            (2.5, 25.0),
        )
    window.close()


def test_plot_widget_reprojects_axes_and_slices_without_reacquisition():
    app = _application()
    ddr_result = _four_axis_result()
    result = awg_map.reduce_awg_sweep_map(
        ddr_result,
        x_axis_key=("awg_0", "set_x"),
        y_axis_key=("awg_1", "set_y"),
        full_scale_mv=100.0,
    )
    widget = awg_map.AwgSweepMapPlotWidget()
    widget.set_result(result)
    app.processEvents()

    if not hasattr(widget, "axis_x"):
        widget.close()
        pytest.skip("pyqtgraph is unavailable")
    angle_control = widget.range_controls["angle"]
    assert angle_control.auto_range.isChecked() is False
    angle_control.auto_range.setChecked(True)
    app.processEvents()
    np.testing.assert_allclose(
        widget.images["angle"].getLevels(),
        widget._levels(widget._result.angle_deg),
    )
    assert widget.axis_x.count() == 4
    assert widget.axis_y.count() == 4
    assert set(widget.slice_controls) == {
        ("awg_2", "set_z"),
        ("awg_3", "set_w"),
    }
    assert all(
        combo.currentText() == "Average all"
        for combo in widget.slice_controls.values()
    )

    z_combo = widget.slice_controls[("awg_2", "set_z")]
    z_combo.setCurrentIndex(2)
    app.processEvents()
    assert widget._result.fixed_axis_values == (
        (("awg_2", "set_z"), 0.25),
    )
    assert widget._result.averaged_axis_labels == ("awg_3 / set_w",)
    assert widget._result.source_points_per_cell == 2

    widget.axis_x.setCurrentIndex(
        widget._axis_index(widget.axis_x, ("awg_2", "set_z"))
    )
    app.processEvents()
    assert widget._result.x_axis_key == ("awg_2", "set_z")
    assert widget._result.y_axis_key == ("awg_1", "set_y")
    assert ("awg_0", "set_x") in widget.slice_controls
    assert ("awg_3", "set_w") in widget.slice_controls
    assert widget._result.i_mean.shape == (2, 2)
    widget.close()


def test_plot_axis_and_slice_settings_restore_before_data_arrives():
    app = _application()
    source_result = awg_map.reduce_awg_sweep_map(
        _four_axis_result(),
        x_axis_key=("awg_0", "set_x"),
        y_axis_key=("awg_1", "set_y"),
        full_scale_mv=100.0,
    )
    settings = {
        "x_axis": {
            "output_name": "awg_2",
            "segment_name": "set_z",
        },
        "y_axis": {
            "output_name": "awg_0",
            "segment_name": "set_x",
        },
        "slice_axes": [
            {
                "output_name": "awg_1",
                "segment_name": "set_y",
                "mode": "value",
                "value": 0.5,
            },
            {
                "output_name": "awg_3",
                "segment_name": "set_w",
                "mode": "average",
            },
        ],
    }
    widget = awg_map.AwgSweepMapPlotWidget()
    if not hasattr(widget, "axis_x"):
        widget.close()
        pytest.skip("pyqtgraph is unavailable")
    widget.load_axis_selection_settings(settings)
    widget.set_result(source_result)
    app.processEvents()

    assert widget._result.x_axis_key == ("awg_2", "set_z")
    assert widget._result.y_axis_key == ("awg_0", "set_x")
    assert widget._result.fixed_axis_values == (
        (("awg_1", "set_y"), 0.5),
    )
    assert widget._result.averaged_axis_labels == ("awg_3 / set_w",)
    assert widget.axis_selection_settings() == settings
    widget.close()


def test_experiment_panel_lists_ramp_rate_axis_for_2d_map():
    app = _application()
    window = gui.MainWindow()
    window._sweep_specs = [
        QickRampRateSweepSpec("ramp_0_to_1", 0.08, 0.12, 3),
        QickSweepSpec("set_1", "awg_0", -0.5, 0.5, 2),
    ]
    window._refresh_sweep_overlay()
    panel = window._experiment_panel

    assert panel.sweep_map_x.count() == 2
    assert "RAMP duration (rate derived)" in panel.sweep_map_x.itemText(0)
    assert panel.selected_sweep_axis_keys() == (
        ("all_awg_outputs", "ramp_0_to_1"),
        ("awg_0", "set_1"),
    )
    app.processEvents()
    window.close()


def test_awg_map_axis_selection_round_trips_in_settings(tmp_path):
    app = _application()
    window = gui.MainWindow()
    window._add_port()
    window._add_port()
    window._sweep_specs = [
        QickSweepSpec("set_0", "awg_0", -0.5, 0.5, 2),
        QickSweepSpec("set_0", "awg_1", -0.25, 0.25, 3),
        QickSweepSpec("set_0", "awg_2", -0.1, 0.1, 2),
    ]
    window._refresh_sweep_overlay()
    axis_settings = {
        "x_axis": {
            "output_name": "awg_1",
            "segment_name": "set_0",
        },
        "y_axis": {
            "output_name": "awg_0",
            "segment_name": "set_0",
        },
        "slice_axes": [
            {
                "output_name": "awg_2",
                "segment_name": "set_0",
                "mode": "value",
                "value": 0.1,
            },
        ],
    }
    window._awg_sweep_plot.load_axis_selection_settings(axis_settings)
    window._awg_sweep_plot.load_color_range_settings({
        "i": {"auto": False, "minimum": -4.0, "maximum": 5.0},
        "q": {"auto": True, "minimum": -1.0, "maximum": 1.0},
        "magnitude": {"auto": False, "minimum": 0.0, "maximum": 8.0},
        "angle": {"auto": False, "minimum": -90.0, "maximum": 90.0},
    })
    window._awg_sweep_plot.load_visible_data(["i", "angle"])
    app.processEvents()
    assert window._awg_sweep_plot.axis_selection_settings() == axis_settings

    path = window._save_settings_json(tmp_path / "awg_map_axes.json")
    restored = gui.MainWindow()
    restored._load_settings_json(path)
    app.processEvents()
    assert restored._experiment_panel.selected_sweep_axis_keys() == (
        ("awg_1", "set_0"),
        ("awg_0", "set_0"),
    )
    assert restored._awg_sweep_plot.axis_selection_settings() == axis_settings
    assert restored._awg_sweep_plot.color_range_settings() == {
        "i": {"auto": False, "minimum": -4.0, "maximum": 5.0},
        "q": {"auto": True, "minimum": -1.0, "maximum": 1.0},
        "magnitude": {"auto": False, "minimum": 0.0, "maximum": 8.0},
        "angle": {"auto": False, "minimum": -90.0, "maximum": 90.0},
    }
    assert restored._awg_sweep_plot.visible_data() == ("i", "angle")

    restored.close()
    window.close()
    restored.deleteLater()
    window.deleteLater()
    app.processEvents()
