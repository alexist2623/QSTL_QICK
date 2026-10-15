"""Gain/power calibration DB and DMEM schedule tests.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

import json
import sqlite3

import numpy as np
import pytest

from power_calibration import (
    CalibrationDatabase,
    GAIN_DMEM_BASE_ADDRESS,
    MAX_DMEM_GAIN_ENTRIES,
)


def _calibration_database(path):
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE experiments (
            exp_id INTEGER PRIMARY KEY,
            name TEXT,
            sample_name TEXT
        );
        CREATE TABLE runs (
            run_id INTEGER PRIMARY KEY,
            exp_id INTEGER,
            result_table_name TEXT,
            is_completed INTEGER,
            Attenuation TEXT
        );
        CREATE TABLE layouts (
            layout_id INTEGER PRIMARY KEY,
            run_id INTEGER,
            parameter TEXT,
            label TEXT,
            unit TEXT,
            inferred_from TEXT
        );
        """
    )

    def output_run(exp_id, run_id, board, frequencies, power_offset=0.0):
        table = f"results-{exp_id}-{run_id}"
        connection.execute(
            "INSERT INTO experiments VALUES (?, 'calibration', ?)",
            (exp_id, board),
        )
        connection.execute(
            "INSERT INTO runs VALUES (?, ?, ?, 1, ?)",
            (run_id, exp_id, table, json.dumps({"att1": 0, "att2": 0})),
        )
        connection.execute(
            "INSERT INTO layouts VALUES (?, ?, 'freq', 'freq', 'MHz', '')",
            (run_id, run_id),
        )
        connection.execute(
            f'CREATE TABLE "{table}" (id INTEGER PRIMARY KEY, gain REAL, freq REAL, pwr REAL)'
        )
        row_id = 1
        for frequency in frequencies:
            for gain, power in ((100, -30), (1000, -10), (10000, 10)):
                connection.execute(
                    f'INSERT INTO "{table}" VALUES (?, ?, ?, ?)',
                    (
                        row_id,
                        gain,
                        frequency,
                        power + power_offset + 0.01 * (frequency - frequencies[0]),
                    ),
                )
                row_id += 1

    output_run(1, 1, "RF_Out_200MHz", [180.0, 200.0, 220.0])
    output_run(2, 2, "RF_Out_400MHz", [400.0, 450.0, 500.0])
    output_run(3, 3, "DC_Out_400MHz", [400.0, 450.0, 500.0], 3.0)

    connection.execute(
        "INSERT INTO experiments VALUES (4, 'calibration', 'DC_In_400MHz')"
    )
    connection.execute(
        "INSERT INTO runs VALUES (4, 4, 'results-4-4', 1, NULL)"
    )
    connection.execute(
        "INSERT INTO layouts VALUES (4, 4, 'freq', 'freq', 'MHz', '')"
    )
    connection.execute(
        'CREATE TABLE "results-4-4" '
        '(id INTEGER PRIMARY KEY, freq REAL, measured_value REAL, '
        'meas_in_pwr REAL, meas_slope REAL, meas_intercept REAL)'
    )
    row_id = 1
    for frequency in (400.0, 450.0, 500.0):
        for measured_value in (-20.0, -10.0):
            connection.execute(
                'INSERT INTO "results-4-4" VALUES (?, ?, ?, ?, NULL, NULL)',
                (row_id, frequency, measured_value, measured_value - 60.0),
            )
            row_id += 1
        connection.execute(
            'INSERT INTO "results-4-4" VALUES (?, ?, NULL, NULL, 1, NULL)',
            (row_id, frequency),
        )
        row_id += 1
        connection.execute(
            'INSERT INTO "results-4-4" VALUES (?, ?, NULL, NULL, NULL, -60)',
            (row_id, frequency),
        )
        row_id += 1
    connection.commit()
    connection.close()


def _add_input_calibration_run(path, run_id, board_type, input_attenuation_db):
    connection = sqlite3.connect(path)
    table = f"results-input-{run_id}"
    connection.execute(
        "INSERT INTO experiments VALUES (?, 'input calibration', ?)",
        (run_id, f"{board_type}_400MHz"),
    )
    connection.execute(
        "INSERT INTO runs "
        "(run_id, exp_id, result_table_name, is_completed, Attenuation, "
        "Calibration_Config) VALUES (?, ?, ?, 1, NULL, ?)",
        (
            run_id,
            run_id,
            table,
            json.dumps({"input_attenuation_db": input_attenuation_db}),
        ),
    )
    connection.execute(
        "INSERT INTO layouts VALUES (?, ?, 'freq', 'freq', 'MHz', '')",
        (run_id, run_id),
    )
    connection.execute(
        f'CREATE TABLE "{table}" '
        "(id INTEGER PRIMARY KEY, freq REAL, measured_value REAL, "
        "meas_in_pwr REAL, meas_slope REAL, meas_intercept REAL)"
    )
    row_id = 1
    for frequency in (400.0, 450.0, 500.0):
        for measured_value in (-20.0, -10.0):
            connection.execute(
                f'INSERT INTO "{table}" VALUES (?, ?, ?, ?, NULL, NULL)',
                (row_id, frequency, measured_value, measured_value - 60.0),
            )
            row_id += 1
    connection.commit()
    connection.close()


def test_selects_same_board_and_covering_frequency_run(tmp_path):
    path = tmp_path / "gain_pwr_calb.db"
    _calibration_database(path)
    catalog = CalibrationDatabase(path)

    rf = catalog.output_calibration("RF_Out", [410.0, 490.0])
    dc = catalog.output_calibration("DC_Out", [410.0, 490.0])

    assert rf.summary.run_id == 2
    assert rf.summary.sample_name == "RF_Out_400MHz"
    assert dc.summary.run_id == 3
    assert catalog.matching_input_run("DC_In", [410.0, 490.0]).run_id == 4
    assert catalog.matching_input_run("RF_In", [410.0, 490.0]) is None


def test_output_calibration_requires_matching_nyquist_and_filter_settings(
    tmp_path,
):
    path = tmp_path / "gain_pwr_calb.db"
    _calibration_database(path)
    metadata = {
        "schema": "qstl-qick-output-power-calibration-v2",
        "configuration": {
            "nqz": 1,
            "output_filter_type": "lowpass",
            "output_filter_cutoff_ghz": 2.5,
            "output_filter_bandwidth_ghz": 1.0,
        },
        "rf_settings_actual": {
            "filter_type": "lowpass",
            "filter_cutoff_ghz": 2.5,
            "filter_bandwidth_ghz": 1.0,
        },
    }
    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE runs ADD COLUMN Calibration_Config TEXT")
        connection.execute(
            "UPDATE runs SET Calibration_Config = ? WHERE run_id = 2",
            (json.dumps(metadata),),
        )

    catalog = CalibrationDatabase(path)
    calibration = catalog.output_calibration(
        "RF_Out",
        [450.0],
        run_id=2,
        nqz=1,
        output_filter_type="lowpass",
        output_filter_cutoff_ghz=2.5,
        output_filter_bandwidth_ghz=1.0,
    )
    assert calibration.summary.run_id == 2
    assert calibration.summary.output_nqz == 1
    assert calibration.summary.output_filter_type == "lowpass"
    candidates = catalog.output_calibration_candidates(
        "RF_Out",
        [450.0],
        nqz=1,
        output_filter_type="lowpass",
        output_filter_cutoff_ghz=2.5,
        output_filter_bandwidth_ghz=1.0,
    )
    assert candidates[0].summary.run_id == 2
    assert candidates[0].exact_match is True
    assert "PCB RF_Out" in candidates[0].display_label
    assert "NQZ 1" in candidates[0].display_label
    assert "lowpass" in candidates[0].display_label

    no_exact_candidates = catalog.output_calibration_candidates(
        "RF_Out",
        [450.0],
        nqz=2,
        output_filter_type="highpass",
        output_filter_cutoff_ghz=1.5,
        output_filter_bandwidth_ghz=0.5,
    )
    assert no_exact_candidates
    assert not any(
        candidate.exact_match for candidate in no_exact_candidates
    )
    assert any(
        "PCB DC_Out" in candidate.display_label
        for candidate in no_exact_candidates
    )
    assert any(
        "Nyquist zone 1 != 2" in candidate.detail_text
        for candidate in no_exact_candidates
    )

    response = float(calibration.frequency_response_dbm([450.0])[0])
    attenuated_power = float(
        calibration.output_power_dbm(
            [450.0],
            [1000],
            output_att1_db=10.0,
        )[0]
    )
    assert calibration.nominal_gain_for_power(
        attenuated_power,
        reference_response_dbm=response,
        output_att1_db=10.0,
    ) == 1000

    with pytest.raises(LookupError, match="Nyquist zone 1 != 2"):
        catalog.output_calibration(
            "RF_Out",
            [450.0],
            run_id=2,
            nqz=2,
            output_filter_type="lowpass",
            output_filter_cutoff_ghz=2.5,
            output_filter_bandwidth_ghz=1.0,
        )
    with pytest.raises(LookupError, match="filter lowpass != highpass"):
        catalog.output_calibration(
            "RF_Out",
            [450.0],
            run_id=2,
            nqz=1,
            output_filter_type="highpass",
            output_filter_cutoff_ghz=2.5,
            output_filter_bandwidth_ghz=1.0,
        )


def test_schedule_uses_linear_nominal_gain_and_relative_frequency_correction(
    tmp_path,
):
    path = tmp_path / "gain_pwr_calb.db"
    _calibration_database(path)
    calibration = CalibrationDatabase(path).output_calibration(
        "RF_Out", [400.0, 500.0]
    )

    frequencies = np.asarray([400.0, 450.0, 500.0])
    schedule = calibration.build_gain_schedule(frequencies, -10.0)
    attenuated = calibration.build_gain_schedule(
        frequencies,
        -30.0,
        output_att1_db=10.0,
        output_att2_db=10.0,
    )
    low_power = calibration.build_gain_schedule(
        frequencies,
        -80.0,
        output_att1_db=30.0,
        output_att2_db=30.0,
    )

    assert schedule.nominal_gain_code == 1000
    np.testing.assert_allclose(schedule.correction_db, [0.0, -0.5, -1.0])
    np.testing.assert_array_equal(schedule.gain_codes, [1000, 944, 891])
    assert np.all(schedule.gain_codes <= schedule.nominal_gain_code)
    assert attenuated.nominal_gain_code == 1000
    np.testing.assert_array_equal(attenuated.gain_codes, schedule.gain_codes)
    assert low_power.nominal_gain_code == 316
    assert np.all(low_power.gain_codes >= 1)
    with pytest.raises(ValueError, match="outside linear gain range"):
        calibration.build_gain_schedule(frequencies, 21.0)


def test_output_and_input_power_calibration_use_physical_dbm(tmp_path):
    path = tmp_path / "gain_pwr_calb.db"
    _calibration_database(path)
    catalog = CalibrationDatabase(path)
    output = catalog.output_calibration("RF_Out", [400.0, 500.0])
    input_calibration = catalog.input_calibration("DC_In", [400.0, 500.0])

    output_power = output.output_power_dbm(
        [400.0, 450.0, 500.0],
        [1000, 1000, 1000],
    )
    np.testing.assert_allclose(output_power, [-10.0, -9.5, -9.0])
    input_power = input_calibration.input_power_dbm(
        [400.0, 450.0, 500.0],
        [-20.0, -15.0, -10.0],
    )
    np.testing.assert_allclose(input_power, [-80.0, -75.0, -70.0])
    attenuated_measurement = input_calibration.input_power_dbm(
        [400.0],
        [-30.0],
        input_attenuation_db=10.0,
    )
    np.testing.assert_allclose(attenuated_measurement, [-80.0])
    extrapolated_below_calibration_range = input_calibration.input_power_dbm(
        [400.0],
        [-30.0],
    )
    np.testing.assert_allclose(extrapolated_below_calibration_range, [-90.0])


def test_input_calibration_selects_manual_run_or_latest_same_attenuation(tmp_path):
    path = tmp_path / "gain_pwr_calb.db"
    _calibration_database(path)
    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE runs ADD COLUMN Calibration_Config TEXT")
    _add_input_calibration_run(path, 10, "RF_In", 20.0)
    _add_input_calibration_run(path, 11, "RF_In", 10.0)
    _add_input_calibration_run(path, 12, "RF_In", 20.0)
    catalog = CalibrationDatabase(path)

    latest_20_db = catalog.input_calibration(
        "RF_In",
        [410.0, 490.0],
        input_attenuation_db=20.0,
    )
    latest_10_db = catalog.input_calibration(
        "RF_In",
        [410.0, 490.0],
        input_attenuation_db=10.0,
    )
    manual = catalog.input_calibration(
        "RF_In",
        [410.0, 490.0],
        run_id=10,
        input_attenuation_db=10.0,
    )

    assert latest_20_db.summary.run_id == 12
    assert latest_10_db.summary.run_id == 11
    assert manual.summary.run_id == 10
    with pytest.raises(LookupError, match="available covering runs"):
        catalog.input_calibration(
            "RF_In",
            [410.0, 490.0],
            input_attenuation_db=15.0,
        )
    with pytest.raises(LookupError, match="Run 99"):
        catalog.input_calibration(
            "RF_In",
            [410.0, 490.0],
            run_id=99,
        )


def test_schedule_uses_one_entry_per_point_up_to_dmem_limit(tmp_path):
    path = tmp_path / "gain_pwr_calb.db"
    _calibration_database(path)
    calibration = CalibrationDatabase(path).output_calibration(
        "RF_Out", [400.0, 500.0]
    )
    frequencies = np.linspace(400.0, 500.0, 101)

    schedule = calibration.build_gain_schedule(frequencies, -10.0)

    assert schedule.table_count == frequencies.size
    assert not schedule.compressed
    assert schedule.dmem_base_address == GAIN_DMEM_BASE_ADDRESS
    np.testing.assert_array_equal(
        schedule.point_table_indices,
        np.arange(frequencies.size),
    )


def test_software_power_points_reuse_response_shape_with_scaled_nominal_gain(
    tmp_path,
):
    path = tmp_path / "gain_pwr_calb.db"
    _calibration_database(path)
    calibration = CalibrationDatabase(path).output_calibration(
        "RF_Out", [400.0, 500.0]
    )
    frequencies = np.linspace(400.0, 500.0, 101)

    low_power = calibration.build_gain_schedule(frequencies, -20.0)
    high_power = calibration.build_gain_schedule(frequencies, -10.0)

    np.testing.assert_allclose(low_power.correction_db, high_power.correction_db)
    assert low_power.nominal_gain_code == 316
    assert high_power.nominal_gain_code == 1000
    np.testing.assert_allclose(
        high_power.gain_codes / low_power.gain_codes,
        high_power.nominal_gain_code / low_power.nominal_gain_code,
        rtol=0.005,
    )


def test_more_than_4000_frequencies_share_adjacent_representative_gains(tmp_path):
    path = tmp_path / "gain_pwr_calb.db"
    _calibration_database(path)
    calibration = CalibrationDatabase(path).output_calibration(
        "RF_Out", [400.0, 500.0]
    )
    frequencies = np.linspace(400.0, 500.0, 10_001)

    schedule = calibration.build_gain_schedule(frequencies, -10.0)
    indices = schedule.point_table_indices

    assert schedule.table_count == MAX_DMEM_GAIN_ENTRIES
    assert schedule.compressed
    assert schedule.expanded_gain_codes.size == frequencies.size
    assert indices[0] == 0
    assert indices[-1] == MAX_DMEM_GAIN_ENTRIES - 1
    assert np.all(np.diff(indices) >= 0)
    assert np.max(np.diff(indices)) == 1
    assert schedule.dmem_base_address + schedule.table_count <= 4096


def test_partial_frequency_overlap_is_reported_not_extrapolated(tmp_path):
    path = tmp_path / "gain_pwr_calb.db"
    _calibration_database(path)

    with pytest.raises(LookupError, match="fully covers"):
        CalibrationDatabase(path).output_calibration(
            "RF_Out", [350.0, 450.0]
        )
