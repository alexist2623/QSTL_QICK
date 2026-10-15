"""QCoDeS persistence and injected QICK execution tests.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tracemalloc
from types import SimpleNamespace

import numpy as np
import pytest
from plottr.data.qcodes_dataset import ds_to_datadicts

import qick_qcodes_experiment as experiment_module
from dc_waveform_core import (
    QickDdrReadoutSpec,
    QickRfCompositeItemSpec,
    QickRfDurationParameterSpec,
    QickRfFrequencyParameterSpec,
    QickRfPulseSpec,
)
from qick_fine_tune_sweep import (
    AmplitudeSweep,
    FineTuneDdrResult,
    FineTuneSequence,
    HoldDurationSweep,
    RampDurationSweep,
    RfDurationSweep,
)
from qick_qcodes_experiment import (
    AWG_METADATA_MODE_EXPANDED,
    AWG_METADATA_MODE_PARAMETRIC,
    COMPILE_VALIDATION_BOUNDARY,
    DEFAULT_COMPILE_VALIDATION_MODE,
    DEFAULT_AWG_METADATA_MODE,
    I_MEAN_PARAMETER,
    ExperimentCancelled,
    I_TRACE_PARAMETER,
    IQ_TRACE_PARAMETER,
    IQ_STORAGE_MEAN_IQ,
    Q_MEAN_PARAMETER,
    Q_TRACE_PARAMETER,
    SAMPLE_INDEX_PARAMETER,
    QCODES_STAGING_ENV,
    QcodesRunConfig,
    QickConnectionConfig,
    StoredQickExperiment,
    _sweep_parameter_names,
    build_awg_vertex_record,
    build_awg_vertex_metadata,
    build_awg_waveform_recipe,
    build_qick_program,
    build_runtime_ddr_readout,
    build_runtime_rf_pulses,
    configure_rf_board,
    configure_rf_output,
    connect_qick,
    execute_qick_sequence,
    load_qick_iq_arrays,
    normalize_compile_validation_mode,
    run_qick_qcodes_experiment,
    store_qick_result,
    write_awg_vertex_metadata_jsonl,
)


def test_stored_experiment_detaches_thread_bound_dataset_connection():
    closed = []
    dataset = SimpleNamespace(
        conn=SimpleNamespace(close=lambda: closed.append(True)),
    )
    stored = StoredQickExperiment(
        run_id=1,
        guid="guid",
        database_path=Path("experiment.db"),
        row_count=1,
        dataset=dataset,
        program=None,
        ddr_result=None,
        rf_settings={},
        iq_storage_mode=IQ_STORAGE_MEAN_IQ,
    )

    assert stored.detach_dataset() is stored
    assert stored.dataset is None
    assert closed == [True]
    stored.detach_dataset()
    assert closed == [True]


def test_predefined_rf_n_tau_software_sweep_executes_cartesian_programs(
    monkeypatch,
):
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("set_0", (0.0,), 300)
    rf_spec = QickRfPulseSpec(
        gen_ch=1,
        segment_name="set_0",
        delay_us=0.0,
        duration_us=1.0,
        frequency_mhz=50.0,
        gain=20000,
        att1_db=0.0,
        att2_db=0.0,
        pulse_mode="composite",
        frequency_parameters=(
            QickRfFrequencyParameterSpec("f0", 50.0),
        ),
        duration_parameters=(
            QickRfDurationParameterSpec("d0", 0.1),
        ),
        predefined_template="cpmg",
        predefined_n=2,
        predefined_tau_us=5.0,
        predefined_n_sweep_enabled=True,
        predefined_n_sweep_start=2,
        predefined_n_sweep_stop=3,
        predefined_n_sweep_count=2,
        predefined_tau_sweep_enabled=True,
        predefined_tau_sweep_start_us=5.0,
        predefined_tau_sweep_stop_us=10.0,
        predefined_tau_sweep_count=2,
    )
    calls = []

    def fake_execute(_soc, _soccfg, _sequence, **kwargs):
        concrete = kwargs["rf_specs"][0]
        calls.append((concrete.predefined_n, concrete.predefined_tau_us))
        iq = np.asarray([[[[
            concrete.predefined_n,
            round(concrete.predefined_tau_us),
        ]]]], dtype=np.int32)
        result = FineTuneDdrResult(
            sweep_points=np.asarray([0.0]),
            iq=iq,
            reserved_physical_words=128,
            sweep_axes=(),
            sweep_shape=(1,),
        )
        program = SimpleNamespace(
            summary=lambda: {"concrete_n": concrete.predefined_n}
        )
        return program, result, {"outputs": []}

    monkeypatch.setattr(
        experiment_module,
        "_execute_qick_sequence_once",
        fake_execute,
    )
    program, result, rf_settings = execute_qick_sequence(
        object(),
        object(),
        sequence,
        awg_channels=(0,),
        repetitions_per_sweep=1,
        rf_specs=(rf_spec,),
        readout_spec=QickDdrReadoutSpec(0, "set_0", 0.0, 1),
    )

    assert calls == [(2, 5.0), (2, 10.0), (3, 5.0), (3, 10.0)]
    assert [axis.axis_kind for axis in result.sweep_axes] == [
        "rf_template_n",
        "rf_template_tau",
    ]
    np.testing.assert_allclose(
        result.sweep_points,
        [[2, 5], [2, 10], [3, 5], [3, 10]],
    )
    assert result.sweep_shape == (2, 2)
    assert result.iq.shape == (4, 1, 1, 2)
    assert result.reserved_physical_words == 128
    assert program.summary()["software_sweep_program_count"] == 4
    assert rf_settings["predefined_software_sweep"]["program_count"] == 4


def test_sweep_parameter_names_identify_output_segment_and_voltage_unit():
    axes = (
        AmplitudeSweep("set_1", "awg_0", -0.5, 0.5, 3),
        AmplitudeSweep("gate hold", "awg-3", -0.25, 0.25, 5),
    )

    assert _sweep_parameter_names(axes) == (
        "awg_0_set_1_voltage_mv",
        "awg_3_gate_hold_voltage_mv",
    )


def test_compile_validation_mode_normalization():
    assert normalize_compile_validation_mode(None) == DEFAULT_COMPILE_VALIDATION_MODE
    assert normalize_compile_validation_mode(" BOUNDARY ") == (
        COMPILE_VALIDATION_BOUNDARY
    )
    with pytest.raises(ValueError, match="compile validation mode"):
        normalize_compile_validation_mode("sampled")


def test_experiment_cancellation_is_checked_before_connection(tmp_path):
    connector_calls = []

    def connector(**kwargs):
        connector_calls.append(kwargs)
        raise AssertionError("connector must not run after cancellation")

    def cancel_check():
        raise ExperimentCancelled("stopped")

    with pytest.raises(ExperimentCancelled, match="stopped"):
        run_qick_qcodes_experiment(
            connection_config=QickConnectionConfig(
                "198.51.100.9",
                9999,
                "testqick",
            ),
            run_config=QcodesRunConfig(str(tmp_path / "cancelled.db")),
            sequence=object(),
            awg_channels=(0,),
            repetitions_per_sweep=1,
            rf_specs=(),
            readout_spec=QickDdrReadoutSpec(0, "set_0", 0.0, 1),
            gui_settings={},
            connector=connector,
            cancel_check=cancel_check,
        )

    assert connector_calls == []
    assert not (tmp_path / "cancelled.db").exists()


def test_sweep_parameter_names_preserve_rf_duration_units():
    axes = (
        AmplitudeSweep("gate", "awg_0", -0.5, 0.5, 3),
        RfDurationSweep(
            segment_name="gate",
            output_name="rf_gen_2",
            gen_ch=2,
            start=1.0,
            stop=5.0,
            count=5,
            segment_length_mode="extend_by_rf_duration",
            sequence_fabric_mhz=300.0,
        ),
    )

    assert _sweep_parameter_names(axes) == (
        "awg_0_gate_voltage_mv",
        "rf_gen_2_gate_duration_us",
    )


def test_sweep_parameter_names_preserve_ramp_duration_units():
    axes = (
        RampDurationSweep(
            segment_name="ramp_0_to_1",
            start=0.08,
            stop=0.12,
            count=3,
            sequence_fabric_mhz=300.0,
        ),
        RampDurationSweep(
            segment_name="ramp_1_to_2",
            start=0.10,
            stop=0.16,
            count=4,
            sequence_fabric_mhz=300.0,
        ),
        AmplitudeSweep("gate", "awg_0", -0.5, 0.5, 3),
    )

    assert _sweep_parameter_names(axes) == (
        "all_awg_outputs_ramp_0_to_1_ramp_duration_us",
        "all_awg_outputs_ramp_1_to_2_ramp_duration_us",
        "awg_0_gate_voltage_mv",
    )


def test_sweep_parameter_names_preserve_hold_duration_units():
    axes = (
        HoldDurationSweep(
            segment_name="readout hold",
            start=1.0,
            stop=5.0,
            count=5,
            sequence_fabric_mhz=300.0,
        ),
        AmplitudeSweep("gate", "awg_0", -0.5, 0.5, 3),
    )

    assert _sweep_parameter_names(axes) == (
        "all_awg_outputs_readout_hold_hold_duration_us",
        "awg_0_gate_voltage_mv",
    )


def _ddr_result():
    iq = np.asarray(
        [
            [
                [[1, -1], [2, -2], [3, -3]],
                [[4, -4], [5, -5], [6, -6]],
            ],
            [
                [[10, 20], [11, 21], [12, 22]],
                [[13, 23], [14, 24], [15, 25]],
            ],
        ],
        dtype=np.int32,
    )
    return FineTuneDdrResult(
        sweep_points=np.asarray([-0.5, 0.5]),
        iq=iq,
        sweep_axes=(AmplitudeSweep("set_1", "awg_0", -0.5, 0.5, 2),),
        sweep_shape=(2,),
        cross_capacitance=np.eye(1),
    )


def _gui_metadata():
    return {
        "waveforms": {
            "time_ns": [0.0, 1000.0],
            "virtual_mv": [[100.0, 100.0]],
            "physical_mv": [[100.0, 100.0]],
        },
        "awg": {"cross_capacitance": [[1.0]]},
        "qick": {
            "fabric_mhz": 300.0,
            "tproc_mhz": 300.0,
            "full_scale_mv": 100.0,
        },
        "rf_outputs": [{"frequency_mhz": 50.0, "gain": 12000}],
        "rf_readout": {"readout_frequency_mhz": 25.0},
    }


def test_qcodes_save_cancellation_discards_staging_database(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "cancelled_trace.db"
    staging_root = tmp_path / "staging"
    monkeypatch.setenv(QCODES_STAGING_ENV, str(staging_root))
    checks = 0

    def cancel_check():
        nonlocal checks
        checks += 1
        if checks >= 7:
            raise ExperimentCancelled("save stopped")

    with pytest.raises(ExperimentCancelled, match="save stopped"):
        store_qick_result(
            _ddr_result(),
            run_config=QcodesRunConfig(str(database_path)),
            connection_config=QickConnectionConfig(),
            program_summary={},
            gui_settings=_gui_metadata(),
            rf_settings={},
            cancel_check=cancel_check,
        )

    assert not database_path.exists()
    assert list(staging_root.glob("qick_qcodes_*")) == []


def test_store_qick_result_writes_iq_and_awg_vertices_as_data(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "qick_trace.db"
    staging_root = tmp_path / "staging"
    monkeypatch.setenv(QCODES_STAGING_ENV, str(staging_root))
    progress_updates = []
    sequence = FineTuneSequence(("awg_0", "awg_1"))
    sequence.add_set("start", (0.0, 0.25), 10)
    sequence.set_amplitude_sweep("start", "awg_0", -0.5, 0.5, 2)
    gui_metadata = _gui_metadata()
    gui_metadata["awg_waveform_vertices"] = build_awg_vertex_metadata(
        sequence,
        fabric_mhz=300.0,
        full_scale_mv=100.0,
    )
    dataset, row_count = store_qick_result(
        _ddr_result(),
        run_config=QcodesRunConfig(
            str(database_path),
            experiment_name="QICK test",
            sample_name="simulated device",
            notes="headless persistence test",
        ),
        connection_config=QickConnectionConfig("192.0.2.10", 8888, "myqick"),
        program_summary={"program_instructions": 42},
        gui_settings=gui_metadata,
        rf_settings={"outputs": [[10.0, 12.0]], "readout": 20.0},
        progress_callback=lambda percent, message: progress_updates.append(
            (percent, message)
        ),
        batch_rows=5,
    )

    assert database_path.exists()
    assert row_count == 12
    # Four traces produce eight split I/Q arrays. Virtual/physical vertex
    # arrays add eight more dependent results across two points and channels.
    assert dataset.number_of_results == 16
    sweep_parameter = "awg_0_set_1_voltage_mv"
    dataset_parameters = {
        parameter.strip() for parameter in dataset.parameters.split(",")
    }
    assert I_TRACE_PARAMETER in dataset_parameters
    assert Q_TRACE_PARAMETER in dataset_parameters
    assert SAMPLE_INDEX_PARAMETER in dataset_parameters
    assert IQ_TRACE_PARAMETER not in dataset_parameters
    assert sweep_parameter in dataset_parameters
    assert "awg_0_vertex_time_us" in dataset_parameters
    assert "awg_1_vertex_time_us" in dataset_parameters
    for removed_parameter in (
        "point_index",
        "time_us",
        "i",
        "q",
        "magnitude",
        "phase_deg",
        "awg_output_index",
        "awg_vertex_index",
        "awg_vertex_time_us",
        "awg_virtual_vertex_mv",
        "awg_physical_vertex_mv",
    ):
        assert removed_parameter not in dataset_parameters

    i_trace_data = dataset.get_parameter_data(I_TRACE_PARAMETER)[
        I_TRACE_PARAMETER
    ]
    q_trace_data = dataset.get_parameter_data(Q_TRACE_PARAMETER)[
        Q_TRACE_PARAMETER
    ]
    expected_flat_i = _ddr_result().iq[..., 0].reshape(4, 3)
    expected_flat_q = _ddr_result().iq[..., 1].reshape(4, 3)
    assert i_trace_data[I_TRACE_PARAMETER].shape == (4, 3)
    assert q_trace_data[Q_TRACE_PARAMETER].shape == (4, 3)
    np.testing.assert_array_equal(
        i_trace_data[I_TRACE_PARAMETER],
        expected_flat_i,
    )
    np.testing.assert_array_equal(
        q_trace_data[Q_TRACE_PARAMETER],
        expected_flat_q,
    )
    np.testing.assert_allclose(
        i_trace_data[sweep_parameter][:, 0],
        [-50.0, -50.0, 50.0, 50.0],
    )
    np.testing.assert_array_equal(
        i_trace_data["repetition_index"][:, 0],
        [0, 1, 0, 1],
    )
    np.testing.assert_allclose(
        i_trace_data[SAMPLE_INDEX_PARAMETER],
        np.tile([0, 1, 2], (4, 1)),
    )

    loaded = load_qick_iq_arrays(dataset)
    np.testing.assert_array_equal(loaded["iq"], _ddr_result().iq)
    np.testing.assert_array_equal(loaded["i"], _ddr_result().iq[..., 0])
    np.testing.assert_array_equal(loaded["q"], _ddr_result().iq[..., 1])
    np.testing.assert_array_equal(loaded["sample_index"], [0, 1, 2])
    np.testing.assert_allclose(loaded["time_us"], [0.0, 1.0, 2.0])
    np.testing.assert_allclose(
        loaded["magnitude"],
        np.hypot(_ddr_result().iq[..., 0], _ddr_result().iq[..., 1]),
    )

    awg_0_virtual = dataset.get_parameter_data(
        "awg_0_virtual_vertices_mv"
    )["awg_0_virtual_vertices_mv"]
    awg_0_physical = dataset.get_parameter_data(
        "awg_0_physical_vertices_mv"
    )["awg_0_physical_vertices_mv"]
    awg_1_virtual = dataset.get_parameter_data(
        "awg_1_virtual_vertices_mv"
    )["awg_1_virtual_vertices_mv"]
    awg_1_physical = dataset.get_parameter_data(
        "awg_1_physical_vertices_mv"
    )["awg_1_physical_vertices_mv"]
    np.testing.assert_allclose(
        awg_0_virtual["awg_0_virtual_vertices_mv"],
        [[-50.0, -50.0], [50.0, 50.0]],
    )
    np.testing.assert_allclose(
        awg_0_physical["awg_0_physical_vertices_mv"],
        [[-50.0, -50.0], [50.0, 50.0]],
    )
    np.testing.assert_allclose(
        awg_1_virtual["awg_1_virtual_vertices_mv"],
        [[25.0, 25.0], [25.0, 25.0]],
    )
    np.testing.assert_allclose(
        awg_1_physical["awg_1_physical_vertices_mv"],
        [[25.0, 25.0], [25.0, 25.0]],
    )
    np.testing.assert_allclose(
        awg_0_virtual[sweep_parameter][:, 0],
        [-50.0, 50.0],
    )
    np.testing.assert_allclose(
        awg_0_virtual["awg_0_vertex_time_us"],
        [[0.0, 10 / 300], [0.0, 10 / 300]],
    )
    np.testing.assert_allclose(
        awg_0_physical["awg_0_vertex_time_us"],
        [[0.0, 10 / 300], [0.0, 10 / 300]],
    )
    np.testing.assert_allclose(
        awg_1_virtual["awg_1_vertex_time_us"],
        [[0.0, 10 / 300], [0.0, 10 / 300]],
    )
    np.testing.assert_allclose(
        awg_1_physical["awg_1_vertex_time_us"],
        [[0.0, 10 / 300], [0.0, 10 / 300]],
    )
    plottr_data = ds_to_datadicts(dataset)
    assert plottr_data[I_TRACE_PARAMETER].axes(I_TRACE_PARAMETER) == [
        sweep_parameter,
        "repetition_index",
        SAMPLE_INDEX_PARAMETER,
    ]
    assert plottr_data[Q_TRACE_PARAMETER].axes(Q_TRACE_PARAMETER) == [
        sweep_parameter,
        "repetition_index",
        SAMPLE_INDEX_PARAMETER,
    ]
    assert plottr_data[I_TRACE_PARAMETER].data_vals(
        SAMPLE_INDEX_PARAMETER
    ).shape == (4, 3)
    for channel in ("awg_0", "awg_1"):
        time_parameter = f"{channel}_vertex_time_us"
        for space in ("virtual", "physical"):
            voltage_parameter = f"{channel}_{space}_vertices_mv"
            assert plottr_data[voltage_parameter].axes(voltage_parameter) == [
                sweep_parameter,
                time_parameter,
            ]
            assert plottr_data[voltage_parameter].data_vals(
                time_parameter
            ).shape == (2, 2)
    metadata = json.loads(dataset.get_metadata("qick_experiment_json"))
    assert metadata["qick_connection"]["host"] == "192.0.2.10"
    assert metadata["measurement_layout"]["iq_shape"] == [2, 2, 3, 2]
    assert metadata["measurement_layout"]["awg_vertex_shape"] == [2, 2, 2]
    assert "awg_waveform_vertices" not in metadata["gui_settings"]
    layout = metadata["measurement_layout"]
    assert layout["sample_period_us"] == 1.0
    assert layout["storage_format"] == "qcodes_split_array_per_trace_v3"
    assert layout["iq_trace_parameters"] == {
        "i": I_TRACE_PARAMETER,
        "q": Q_TRACE_PARAMETER,
    }
    assert layout["iq_trace_shape"] == [3]
    assert layout["sql_rows_per_trace"] == 2
    assert layout["sample_index_parameter"] == SAMPLE_INDEX_PARAMETER
    assert layout["time_reconstruction"].startswith(SAMPLE_INDEX_PARAMETER)
    assert layout["sweep_axes"][0]["parameter"] == sweep_parameter
    assert layout["sweep_axes"][0]["voltage_start_mv"] == -50.0
    assert layout["sweep_axes"][0]["voltage_stop_mv"] == 50.0
    assert "point_index" not in layout["setpoint_meanings"]
    assert "time_us" not in layout["setpoint_meanings"]
    assert layout["awg_vertex_channels"] == {
        "awg_0": {
            "time_parameter": "awg_0_vertex_time_us",
            "virtual_parameter": "awg_0_virtual_vertices_mv",
            "physical_parameter": "awg_0_physical_vertices_mv",
            "time_us": [0.0, 10 / 300],
            "vertex_count": 2,
        },
        "awg_1": {
            "time_parameter": "awg_1_vertex_time_us",
            "virtual_parameter": "awg_1_virtual_vertices_mv",
            "physical_parameter": "awg_1_physical_vertices_mv",
            "time_us": [0.0, 10 / 300],
            "vertex_count": 2,
        },
    }
    assert json.loads(dataset.get_metadata("cross_capacitance_json")) == [[1.0]]
    assert progress_updates[0][0] == 65
    assert progress_updates[-1][0] == 99
    assert [item[0] for item in progress_updates] == sorted(
        item[0] for item in progress_updates
    )
    assert not list(staging_root.glob("qick_qcodes_*"))


def test_store_qick_result_mean_iq_mode_reduces_repetitions_and_samples(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "qick_mean_iq.db"
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging"))

    dataset, row_count = store_qick_result(
        _ddr_result(),
        run_config=QcodesRunConfig(
            str(database_path),
            experiment_name="Mean IQ storage test",
            sample_name="simulated device",
        ),
        connection_config=QickConnectionConfig(),
        program_summary={"program_instructions": 4},
        gui_settings=_gui_metadata(),
        rf_settings={},
        iq_storage_mode=IQ_STORAGE_MEAN_IQ,
    )

    assert row_count == 2
    assert dataset.number_of_results == 4
    parameter_names = {
        parameter.strip() for parameter in dataset.parameters.split(",")
    }
    assert I_MEAN_PARAMETER in parameter_names
    assert Q_MEAN_PARAMETER in parameter_names
    assert I_TRACE_PARAMETER not in parameter_names
    assert Q_TRACE_PARAMETER not in parameter_names
    assert SAMPLE_INDEX_PARAMETER not in parameter_names
    assert "repetition_index" not in parameter_names

    expected = _ddr_result().iq.astype(np.float64).mean(axis=(1, 2))
    i_data = dataset.get_parameter_data(I_MEAN_PARAMETER)[I_MEAN_PARAMETER]
    q_data = dataset.get_parameter_data(Q_MEAN_PARAMETER)[Q_MEAN_PARAMETER]
    np.testing.assert_allclose(i_data[I_MEAN_PARAMETER], expected[:, 0])
    np.testing.assert_allclose(q_data[Q_MEAN_PARAMETER], expected[:, 1])
    np.testing.assert_allclose(
        i_data["awg_0_set_1_voltage_mv"],
        [-50.0, 50.0],
    )

    metadata = json.loads(dataset.get_metadata("qick_experiment_json"))
    layout = metadata["measurement_layout"]
    assert layout["iq_storage_mode"] == IQ_STORAGE_MEAN_IQ
    assert metadata["gui_settings"]["qick"]["iq_storage_mode"] == IQ_STORAGE_MEAN_IQ
    assert layout["storage_format"] == "qcodes_mean_iq_per_point_v1"
    assert layout["iq_shape"] == [2, 1, 1, 2]
    assert layout["source_iq_shape"] == [2, 2, 3, 2]
    assert layout["source_repetition_count"] == 2
    assert layout["source_sample_count"] == 3

    restored = load_qick_iq_arrays(dataset)
    assert restored["storage_mode"] == IQ_STORAGE_MEAN_IQ
    assert restored["source_repetition_count"] == 2
    assert restored["source_sample_count"] == 3
    assert restored["iq"].shape == (2, 1, 1, 2)
    np.testing.assert_allclose(restored["iq"][:, 0, 0, :], expected)
    np.testing.assert_allclose(
        restored["sweep_coordinates"]["awg_0_set_1_voltage_mv"][:, 0],
        [-50.0, 50.0],
    )
def test_store_qick_result_converts_dc_input_iq_to_current(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging"))
    dataset, _row_count = store_qick_result(
        _ddr_result(),
        run_config=QcodesRunConfig(
            str(tmp_path / "dc_current.db"),
            experiment_name="DC current trace test",
            sample_name="identity ADC voltage model",
        ),
        connection_config=QickConnectionConfig(
            "192.0.2.10",
            8888,
            "myqick",
        ),
        program_summary={},
        gui_settings=_gui_metadata(),
        rf_settings={
            "readout_details": {
                "board_type": "DC_In",
                "dc_measure_mode": True,
                "dc_measure_gain_v_per_a": 2.0,
            }
        },
    )

    loaded = load_qick_iq_arrays(dataset)
    np.testing.assert_allclose(loaded["iq"], _ddr_result().iq / 2.0)
    assert loaded["iq_unit"] == "A"
    assert loaded["measurement_mode"] == "dc_current_iq"
    metadata = json.loads(dataset.get_metadata("qick_experiment_json"))
    layout = metadata["measurement_layout"]
    assert layout["iq_unit"] == "A"
    assert layout["measurement_mode"] == "dc_current_iq"
    assert layout["measurement_conversion"] == {
        "adc_to_voltage": "identity",
        "voltage_to_current": "current_a = voltage_v / gain_v_per_a",
        "gain_v_per_a": 2.0,
    }


def test_store_qick_result_keeps_cartesian_sweeps_and_repetitions_grouped(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging"))
    axis_0 = AmplitudeSweep("set_1", "awg_0", 0.1, 0.3, 5)
    axis_1 = AmplitudeSweep("set_1", "awg_1", -0.1, -0.2, 5)
    coordinates = np.asarray([
        (voltage_0, voltage_1)
        for voltage_0 in np.linspace(axis_0.start, axis_0.stop, axis_0.count)
        for voltage_1 in np.linspace(axis_1.start, axis_1.stop, axis_1.count)
    ])
    iq = np.arange(25 * 2 * 128 * 2, dtype=np.int32).reshape(25, 2, 128, 2)
    result = FineTuneDdrResult(
        sweep_points=coordinates,
        iq=iq,
        sweep_axes=(axis_0, axis_1),
        sweep_shape=(5, 5),
        cross_capacitance=np.eye(2),
    )
    database_path = tmp_path / "cartesian_traces.db"
    dataset, row_count = store_qick_result(
        result,
        run_config=QcodesRunConfig(
            str(database_path),
            experiment_name="Cartesian trace test",
            sample_name="two AWG outputs",
        ),
        connection_config=QickConnectionConfig("192.0.2.10", 8888, "myqick"),
        program_summary={"program_instructions": 100},
        gui_settings={
            "qick": {"fabric_mhz": 300.0, "full_scale_mv": 800.0},
        },
        rf_settings={},
        batch_rows=512,
    )

    assert row_count == 25 * 2 * 128
    assert dataset.number_of_results == 100
    with sqlite3.connect(database_path) as connection:
        sql_row_count = connection.execute(
            f'SELECT COUNT(*) FROM "{dataset.table_name}"'
        ).fetchone()[0]
    assert sql_row_count == 100

    i_trace_data = dataset.get_parameter_data(I_TRACE_PARAMETER)[
        I_TRACE_PARAMETER
    ]
    q_trace_data = dataset.get_parameter_data(Q_TRACE_PARAMETER)[
        Q_TRACE_PARAMETER
    ]
    assert i_trace_data[I_TRACE_PARAMETER].shape == (50, 128)
    assert q_trace_data[Q_TRACE_PARAMETER].shape == (50, 128)
    assert i_trace_data[SAMPLE_INDEX_PARAMETER].shape == (50, 128)
    np.testing.assert_array_equal(
        i_trace_data[I_TRACE_PARAMETER],
        iq[..., 0].reshape(50, 128),
    )
    np.testing.assert_array_equal(
        q_trace_data[Q_TRACE_PARAMETER],
        iq[..., 1].reshape(50, 128),
    )
    np.testing.assert_allclose(
        i_trace_data["awg_0_set_1_voltage_mv"][:, 0],
        np.repeat(coordinates[:, 0] * 800.0, 2),
    )
    np.testing.assert_allclose(
        i_trace_data["awg_1_set_1_voltage_mv"][:, 0],
        np.repeat(coordinates[:, 1] * 800.0, 2),
    )
    np.testing.assert_array_equal(
        i_trace_data["repetition_index"][:, 0],
        np.tile([0, 1], 25),
    )
    np.testing.assert_allclose(
        i_trace_data[SAMPLE_INDEX_PARAMETER][0],
        np.arange(128, dtype=np.int32),
    )
    loaded = load_qick_iq_arrays(dataset)
    np.testing.assert_array_equal(loaded["iq"], iq)
    assert loaded["iq"].shape == (25, 2, 128, 2)
    plottr_data = ds_to_datadicts(dataset)
    assert plottr_data[I_TRACE_PARAMETER].axes(I_TRACE_PARAMETER) == [
        "awg_0_set_1_voltage_mv",
        "awg_1_set_1_voltage_mv",
        "repetition_index",
        SAMPLE_INDEX_PARAMETER,
    ]
    dataset_parameters = {
        parameter.strip() for parameter in dataset.parameters.split(",")
    }
    for unstored_parameter in (
        "time_us",
        "i",
        "q",
        "magnitude",
        "phase_deg",
        "awg_vertex_time_us",
        IQ_TRACE_PARAMETER,
    ):
        assert unstored_parameter not in dataset_parameters


def test_plottr_vertex_traces_keep_cartesian_sweeps_and_channel_time(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging"))
    sequence = FineTuneSequence(("awg_0", "awg_1"))
    sequence.add_set("start", (0.0, 0.0), 10)
    sequence.set_amplitude_sweep("start", "awg_0", -0.5, 0.5, 2)
    sequence.set_amplitude_sweep("start", "awg_1", -0.25, 0.25, 2)
    point_count = sequence.sweep_point_count
    result = FineTuneDdrResult(
        sweep_points=np.asarray(sequence.sweep_coordinates),
        iq=np.zeros((point_count, 1, 4, 2), dtype=np.int16),
        sweep_axes=tuple(sequence.sweep_axes),
        sweep_shape=tuple(sequence.sweep_shape),
        cross_capacitance=np.eye(2),
    )
    gui_metadata = {
        "qick": {"fabric_mhz": 300.0, "full_scale_mv": 100.0},
        "awg_waveform_vertices": build_awg_vertex_metadata(
            sequence,
            fabric_mhz=300.0,
            full_scale_mv=100.0,
        ),
    }
    dataset, _ = store_qick_result(
        result,
        run_config=QcodesRunConfig(str(tmp_path / "plottr_vertices.db")),
        connection_config=QickConnectionConfig("192.0.2.10", 8888, "myqick"),
        program_summary={},
        gui_settings=gui_metadata,
        rf_settings={},
    )

    sweep_parameters = list(_sweep_parameter_names(sequence.sweep_axes))
    plottr_data = ds_to_datadicts(dataset)
    for channel in ("awg_0", "awg_1"):
        time_parameter = f"{channel}_vertex_time_us"
        for space in ("virtual", "physical"):
            voltage_parameter = f"{channel}_{space}_vertices_mv"
            trace = plottr_data[voltage_parameter]
            assert trace.axes(voltage_parameter) == [
                *sweep_parameters,
                time_parameter,
            ]
            assert trace.data_vals(voltage_parameter).shape == (
                point_count,
                2,
            )
            assert trace.data_vals(time_parameter).shape == (point_count, 2)


def test_local_staging_preserves_existing_database_runs(tmp_path, monkeypatch):
    staging_root = tmp_path / "staging"
    monkeypatch.setenv(QCODES_STAGING_ENV, str(staging_root))
    database_path = tmp_path / "cumulative.db"
    run_config = QcodesRunConfig(
        str(database_path),
        experiment_name="Cumulative trace test",
        sample_name="same database",
    )
    common_arguments = {
        "run_config": run_config,
        "connection_config": QickConnectionConfig(
            "192.0.2.10", 8888, "myqick"
        ),
        "program_summary": {"program_instructions": 42},
        "gui_settings": _gui_metadata(),
        "rf_settings": {},
    }

    first_dataset, _ = store_qick_result(_ddr_result(), **common_arguments)
    first_guid = first_dataset.guid
    first_dataset.conn.close()
    second_dataset, _ = store_qick_result(_ddr_result(), **common_arguments)

    with sqlite3.connect(database_path) as connection:
        runs = connection.execute(
            "SELECT guid FROM runs ORDER BY run_id"
        ).fetchall()
    assert len(runs) == 2
    assert runs[0][0] == first_guid
    assert runs[1][0] == second_dataset.guid
    assert not list(staging_root.glob("qick_qcodes_*"))


def test_awg_vertex_metadata_stores_all_sweep_points_in_both_spaces():
    sequence = FineTuneSequence(("awg_0", "awg_1"))
    sequence.set_cross_capacitance(((1.0, 0.0), (0.5, 1.0)))
    sequence.add_set("start", (0.0, 0.0), 10)
    sequence.add_ramp("to_gate", 5)
    sequence.add_set("gate", (0.2, -0.1), 15)
    sequence.set_amplitude_sweep("gate", "awg_0", -0.2, 0.2, 3)

    metadata = build_awg_vertex_metadata(
        sequence,
        fabric_mhz=300.0,
        full_scale_mv=100.0,
    )
    virtual = metadata["virtual"]
    physical = metadata["physical"]
    assert virtual["time_cycles"] == [0.0, 10.0, 15.0, 30.0]
    assert virtual["time_us"] == [0.0, 10 / 300, 15 / 300, 30 / 300]
    assert virtual["value_shape"] == [3, 2, 4]
    assert virtual["values_mv"][0][0] == [0.0, 0.0, -20.0, -20.0]
    assert physical["values_mv"][0][1] == [0.0, 0.0, -20.0, -20.0]


def test_awg_vertex_metadata_tracks_segment_extension_per_rf_duration():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("gate", (0.25,), 300)
    sequence.add_ramp("to_end", 30)
    sequence.add_set("end", (0.0,), 30)
    sequence.add_rf_duration_sweep(
        "gate",
        0,
        1.0,
        3.0,
        3,
        segment_length_mode="extend_by_rf_duration",
        sequence_fabric_mhz=300.0,
    )

    metadata = build_awg_vertex_metadata(
        sequence,
        fabric_mhz=300.0,
        full_scale_mv=800.0,
    )
    virtual = metadata["virtual"]
    assert virtual["schema"] == "qick-awg-waveform-vertices-v2"
    assert virtual["time_cycles"] == [
        [0.0, 600.0, 630.0, 660.0],
        [0.0, 900.0, 930.0, 960.0],
        [0.0, 1200.0, 1230.0, 1260.0],
    ]
    np.testing.assert_allclose(
        virtual["time_us"],
        [
            [0.0, 2.0, 2.1, 2.2],
            [0.0, 3.0, 3.1, 3.2],
            [0.0, 4.0, 4.1, 4.2],
        ],
    )


def test_awg_vertex_metadata_tracks_ramp_duration_rate_sweep():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (0.0,), 18)
    sequence.add_ramp("ramp_0_to_1", 30)
    sequence.add_set("gate", (0.4,), 60)
    sequence.add_ramp_duration_sweep(
        "ramp_0_to_1",
        0.08,
        0.12,
        3,
        sequence_fabric_mhz=300.0,
    )

    metadata = build_awg_vertex_metadata(
        sequence,
        fabric_mhz=300.0,
        full_scale_mv=800.0,
    )
    virtual = metadata["virtual"]
    assert virtual["time_cycles"] == [
        [0.0, 18.0, 42.0, 102.0],
        [0.0, 18.0, 48.0, 108.0],
        [0.0, 18.0, 54.0, 114.0],
    ]
    np.testing.assert_allclose(
        virtual["time_us"],
        np.asarray(virtual["time_cycles"]) / 300.0,
    )


def test_awg_waveform_recipe_keeps_base_waveform_and_sweeps_parametric():
    sequence = FineTuneSequence(("awg_0", "awg_1"))
    sequence.set_cross_capacitance(((1.0, 0.25), (0.0, 1.0)))
    sequence.add_set("start", (0.0, 0.1), 10)
    sequence.add_ramp("to_gate", 5)
    sequence.add_set("gate", (0.2, -0.1), 15)
    sequence.set_amplitude_sweep("gate", "awg_0", -0.2, 0.2, 101)
    sequence.add_hold_duration_sweep(
        "gate",
        0.04,
        0.08,
        11,
        sequence_fabric_mhz=300.0,
    )

    recipe = build_awg_waveform_recipe(
        sequence,
        fabric_mhz=300.0,
        full_scale_mv=800.0,
    )

    assert recipe["schema"] == "qick-awg-waveform-recipe-v1"
    assert recipe["metadata_mode"] == AWG_METADATA_MODE_PARAMETRIC
    assert recipe["output_names"] == ["awg_0", "awg_1"]
    assert recipe["sweep_shape"] == list(sequence.sweep_shape)
    assert recipe["point_count"] == 1111
    assert len(recipe["segments"]) == 3
    assert recipe["cross_capacitance"] == [[1.0, 0.25], [0.0, 1.0]]
    assert "values_mv" not in recipe
    assert len(json.dumps(recipe)) < 20_000


def test_awg_vertex_expansion_can_select_one_point_without_expanding_all():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("gate", (0.0,), 10)
    sequence.set_amplitude_sweep("gate", "awg_0", -0.5, 0.5, 1001)

    metadata = build_awg_vertex_metadata(
        sequence,
        fabric_mhz=300.0,
        full_scale_mv=800.0,
        point_indices=(500,),
    )
    record = build_awg_vertex_record(
        sequence,
        500,
        fabric_mhz=300.0,
        full_scale_mv=800.0,
    )

    assert metadata["virtual"]["point_index"] == [500]
    assert metadata["virtual"]["value_shape"] == [1, 1, 2]
    assert metadata["virtual"]["sweep_coordinates"] == [[0.0]]
    assert record["point_index"] == 500
    assert record["sweep_coordinate"] == [0.0]
    assert record["virtual_values_mv"]["awg_0"] == [0.0, 0.0]


def test_awg_vertex_jsonl_export_streams_header_and_point_records(tmp_path):
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("gate", (0.0,), 10)
    sequence.set_amplitude_sweep("gate", "awg_0", -0.5, 0.5, 3)
    progress = []

    output_path = write_awg_vertex_metadata_jsonl(
        sequence,
        tmp_path / "expanded_vertices",
        fabric_mhz=300.0,
        full_scale_mv=800.0,
        progress_callback=lambda completed, total: (
            progress.append((completed, total)) or True
        ),
    )
    records = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    ]

    assert output_path.suffix == ".jsonl"
    assert records[0]["record_type"] == "header"
    assert records[0]["recipe"]["point_count"] == 3
    assert [record["point_index"] for record in records[1:]] == [0, 1, 2]
    assert progress[-1] == (3, 3)


def test_parametric_preview_does_not_materialize_multi_million_point_grid():
    sequence = FineTuneSequence(("awg_0", "awg_1"))
    sequence.add_set("gate", (0.0, 0.0), 100)
    sequence.set_amplitude_sweep("gate", "awg_0", -0.5, 0.5, 101)
    sequence.add_amplitude_sweep("gate", "awg_1", -0.5, 0.5, 101)
    sequence.add_rf_frequency_sweep("gate", 0, 800.0, 1200.0, 401)

    tracemalloc.start()
    try:
        recipe = build_awg_waveform_recipe(
            sequence,
            fabric_mhz=300.0,
            full_scale_mv=800.0,
        )
        record = build_awg_vertex_record(
            sequence,
            recipe["point_count"] - 1,
            fabric_mhz=300.0,
            full_scale_mv=800.0,
        )
        _current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert recipe["point_count"] == 4_090_601
    assert record["sweep_coordinate"] == [0.5, 0.5, 1200.0]
    assert peak_bytes < 5_000_000


def test_run_defaults_to_parametric_awg_metadata(tmp_path, monkeypatch):
    captured = {}
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("gate", (0.0,), 10)
    sequence.set_amplitude_sweep("gate", "awg_0", -0.5, 0.5, 2)
    soccfg = {
        "tprocs": [{"f_time": 300.0}],
        "gens": [{"f_fabric": 300.0}],
        "ddr4_buf": {
            "sample_capture": True,
            "fir_enabled": True,
            "fir_rate_profile": "1_msps",
            "stored_sample_rate_hz": 1_000_000.0,
            "fir_decimation": 300,
            "fir_input_fs_mhz": 300.0,
            "fir_group_delay_input_samples": 8677.0,
        },
    }

    class FakeProgram:
        def summary(self):
            return {}

    monkeypatch.setattr(
        experiment_module,
        "connect_qick",
        lambda *_args, **_kwargs: (object(), soccfg),
    )
    monkeypatch.setattr(
        experiment_module,
        "execute_qick_sequence",
        lambda *_args, **_kwargs: (FakeProgram(), _ddr_result(), {}),
    )
    monkeypatch.setattr(
        experiment_module,
        "build_awg_vertex_metadata",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("default metadata mode expanded all vertices")
        ),
    )

    def fake_store(_ddr_result, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(run_id=92, guid="recipe-guid"), 1

    monkeypatch.setattr(experiment_module, "store_qick_result", fake_store)
    result = run_qick_qcodes_experiment(
        connection_config=QickConnectionConfig("host", 8888, "proxy"),
        run_config=QcodesRunConfig(str(tmp_path / "recipe.db")),
        sequence=sequence,
        awg_channels=(0,),
        repetitions_per_sweep=1,
        rf_specs=(),
        readout_spec=QickDdrReadoutSpec(0, "gate", 0.0, 3),
        gui_settings={"qick": {"fabric_mhz": 300.0, "full_scale_mv": 800.0}},
    )

    stored = captured["gui_settings"]
    assert result.guid == "recipe-guid"
    assert stored["qick"]["awg_metadata_mode"] == DEFAULT_AWG_METADATA_MODE
    assert (
        stored["qick"]["compile_validation_mode"]
        == DEFAULT_COMPILE_VALIDATION_MODE
    )
    assert stored["awg_waveform_recipe"]["point_count"] == 2
    assert "awg_waveform_vertices" not in stored


def test_run_expanded_mode_builds_awg_vertex_metadata(tmp_path, monkeypatch):
    captured = {}
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("gate", (0.0,), 10)
    sequence.set_amplitude_sweep("gate", "awg_0", -0.5, 0.5, 2)
    soccfg = {
        "tprocs": [{"f_time": 300.0}],
        "gens": [{"f_fabric": 300.0}],
        "ddr4_buf": {
            "sample_capture": True,
            "fir_enabled": True,
            "fir_rate_profile": "1_msps",
            "stored_sample_rate_hz": 1_000_000.0,
            "fir_decimation": 300,
            "fir_input_fs_mhz": 300.0,
            "fir_group_delay_input_samples": 8677.0,
        },
    }

    class FakeProgram:
        def summary(self):
            return {}

    monkeypatch.setattr(
        experiment_module,
        "connect_qick",
        lambda *_args, **_kwargs: (object(), soccfg),
    )
    monkeypatch.setattr(
        experiment_module,
        "execute_qick_sequence",
        lambda *_args, **_kwargs: (FakeProgram(), _ddr_result(), {}),
    )

    def fake_store(_ddr_result, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(run_id=93, guid="expanded-guid"), 1

    monkeypatch.setattr(experiment_module, "store_qick_result", fake_store)
    run_qick_qcodes_experiment(
        connection_config=QickConnectionConfig("host", 8888, "proxy"),
        run_config=QcodesRunConfig(str(tmp_path / "expanded.db")),
        sequence=sequence,
        awg_channels=(0,),
        repetitions_per_sweep=1,
        rf_specs=(),
        readout_spec=QickDdrReadoutSpec(0, "gate", 0.0, 3),
        gui_settings={
            "qick": {
                "fabric_mhz": 300.0,
                "full_scale_mv": 800.0,
                "awg_metadata_mode": AWG_METADATA_MODE_EXPANDED,
            }
        },
    )

    stored = captured["gui_settings"]
    assert stored["qick"]["awg_metadata_mode"] == AWG_METADATA_MODE_EXPANDED
    assert stored["awg_waveform_vertices"]["virtual"]["value_shape"] == [2, 1, 2]


def test_runtime_configs_accept_manual_tproc_clock_override():
    soccfg = {
        "tprocs": [{"f_time": 400.0}],
        "gens": [{"f_fabric": 250.0}],
    }
    rf = QickRfPulseSpec(
        0, "set_0", 0.2, 0.4, 43.5, 10000, 6.0, 7.0
    )
    ddr = QickDdrReadoutSpec(
        0,
        "set_0",
        0.25,
        16,
        12.5,
        post_run_read_delay_seconds=0.375,
    )
    runtime_rf = build_runtime_rf_pulses(
        soccfg, (rf,), tproc_mhz=300.0
    )[0]
    runtime_ddr = build_runtime_ddr_readout(
        soccfg, ddr, tproc_mhz=300.0
    )

    assert runtime_rf.length_cycles == 100
    assert runtime_rf.delay_tproc_cycles == 60
    assert runtime_ddr.trigger_delay_tproc_cycles == 75
    assert runtime_ddr.samples_per_trigger == 16
    assert runtime_ddr.settle_seconds == 0.375

    # Direct callers retain the HWH fallback when no override is supplied.
    assert build_runtime_rf_pulses(
        soccfg, (rf,)
    )[0].delay_tproc_cycles == 80
    assert build_runtime_ddr_readout(
        soccfg, ddr
    ).trigger_delay_tproc_cycles == 100


def test_composite_runtime_expands_pulses_and_resolves_shared_frequency():
    spec = QickRfPulseSpec(
        0,
        "set_0",
        0.1,
        1.0,
        50.0,
        20000,
        0.0,
        0.0,
        pulse_mode="composite",
        frequency_parameters=(
            QickRfFrequencyParameterSpec(
                "f0", 100.0, True, 100.0, 120.0, 3
            ),
        ),
        duration_parameters=(
            QickRfDurationParameterSpec(
                "d0", 0.2, True, 0.2, 0.4, 3
            ),
            QickRfDurationParameterSpec("d1", 0.1),
        ),
        composite_items=(
            QickRfCompositeItemSpec(
                "pulse", "prepare", 0.2, "f0", 12000, 15.0,
                duration_parameter="d0",
            ),
            QickRfCompositeItemSpec("delay", "wait", 0.05),
            QickRfCompositeItemSpec(
                "pulse", "read", 0.1, "f0", 8000, -30.0,
                duration_parameter="d1",
            ),
        ),
    )
    runtime = build_runtime_rf_pulses(
        {
            "tprocs": [{"f_time": 300.0}],
            "gens": [{"f_fabric": 300.0}],
        },
        (spec,),
    )

    assert len(runtime) == 2
    assert [pulse.pulse_name for pulse in runtime] == ["prepare", "read"]
    assert [pulse.event_id for pulse in runtime] == [
        "rf_gen_0_composite_0",
        "rf_gen_0_composite_1",
    ]
    assert [pulse.frequency_parameter for pulse in runtime] == ["f0", "f0"]
    assert [pulse.duration_parameter for pulse in runtime] == ["d0", "d1"]
    assert runtime[1].preceding_duration_parameters == ("d0",)
    assert [pulse.delay_tproc_cycles for pulse in runtime] == [30, 105]
    assert [pulse.length_cycles for pulse in runtime] == [60, 30]
    assert [pulse.gain for pulse in runtime] == [12000, 8000]
    assert [pulse.freq_mhz for pulse in runtime] == [100.0, 100.0]


def test_runtime_composite_calibration_builds_gain_table_for_selected_pulse_only(
    monkeypatch,
):
    calls = []

    class FakeCalibration:
        summary = SimpleNamespace(run_id=73)

        def build_gain_schedule(
            self,
            frequencies,
            target_power_dbm,
            **kwargs,
        ):
            calls.append((
                tuple(float(value) for value in frequencies),
                float(target_power_dbm),
                kwargs,
            ))
            return SimpleNamespace(
                gain_codes=np.asarray([101, 102, 103], dtype=np.int32)
            )

    class FakeCalibrationDatabase:
        def __init__(self, path):
            assert path == "pulse_calibration.db"

        def output_calibration(self, board_type, frequencies, **kwargs):
            assert board_type == "RF_Out"
            assert tuple(frequencies) == (100.0, 110.0, 120.0)
            assert kwargs == {
                "run_id": 73,
                "nqz": 2,
                "output_filter_type": "highpass",
                "output_filter_cutoff_ghz": 1.5,
                "output_filter_bandwidth_ghz": 0.4,
            }
            return FakeCalibration()

    monkeypatch.setattr(
        experiment_module,
        "CalibrationDatabase",
        FakeCalibrationDatabase,
    )
    spec = QickRfPulseSpec(
        0,
        "set_0",
        0.1,
        1.0,
        100.0,
        20_000,
        10.0,
        5.0,
        nqz=2,
        filter_type="highpass",
        filter_cutoff=1.5,
        filter_bandwidth=0.4,
        pulse_mode="composite",
        frequency_parameters=(
            QickRfFrequencyParameterSpec(
                "f0", 100.0, True, 100.0, 120.0, 3
            ),
        ),
        composite_items=(
            QickRfCompositeItemSpec(
                "pulse",
                "calibrated",
                0.2,
                "f0",
                1234,
                0.0,
                power_calibration_enabled=True,
                power_calibration_database_path="pulse_calibration.db",
                power_calibration_run_id=73,
                target_output_power_dbm=-31.5,
            ),
            QickRfCompositeItemSpec(
                "pulse", "manual", 0.1, "f0", 8000, 90.0
            ),
        ),
    )
    runtime = build_runtime_rf_pulses(
        {
            "tprocs": [{"f_time": 300.0}],
            "gens": [{"f_fabric": 300.0}],
        },
        (spec,),
    )

    calibrated, manual = runtime
    assert calibrated.gain == 101
    assert calibrated.sweep_gain_codes == (101, 102, 103)
    assert calibrated.sweep_gain_shape == (3, 1)
    assert calibrated.power_calibration_run_id == 73
    assert manual.gain == 8000
    assert manual.sweep_gain_codes == ()
    assert manual.sweep_gain_shape == (0, 0)
    assert manual.power_calibration_run_id is None
    assert calls == [(
        (100.0, 110.0, 120.0),
        -31.5,
        {
            "output_att1_db": 10.0,
            "output_att2_db": 5.0,
            "max_entries": 3,
        },
    )]


def test_runtime_rf_frequency_power_sweep_builds_calibrated_gain_matrix(
    monkeypatch,
):
    calls = []

    class FakeCalibration:
        summary = SimpleNamespace(run_id=91)

        def build_gain_schedule(
            self,
            frequencies,
            target_power_dbm,
            **kwargs,
        ):
            calls.append((
                tuple(float(value) for value in frequencies),
                float(target_power_dbm),
                kwargs,
            ))
            offset = 100 if target_power_dbm == -30.0 else 200
            return SimpleNamespace(
                gain_codes=np.asarray(
                    [offset + index for index in range(len(frequencies))],
                    dtype=np.int32,
                )
            )

    class FakeCalibrationDatabase:
        def __init__(self, path):
            assert path == "calibration.db"

        def output_calibration(self, board_type, frequencies, **kwargs):
            assert board_type == "RF_Out"
            assert tuple(frequencies) == (100.0, 150.0, 200.0)
            assert kwargs == {
                "run_id": 91,
                "nqz": 2,
                "output_filter_type": "highpass",
                "output_filter_cutoff_ghz": 1.5,
                "output_filter_bandwidth_ghz": 0.4,
            }
            return FakeCalibration()

    monkeypatch.setattr(
        experiment_module,
        "CalibrationDatabase",
        FakeCalibrationDatabase,
    )
    spec = QickRfPulseSpec(
        0,
        "set_0",
        0.0,
        1.0,
        100.0,
        20_000,
        10.0,
        5.0,
        nqz=2,
        filter_type="highpass",
        filter_cutoff=1.5,
        filter_bandwidth=0.4,
        frequency_sweep_enabled=True,
        frequency_sweep_start_mhz=100.0,
        frequency_sweep_stop_mhz=200.0,
        frequency_sweep_count=3,
        power_sweep_enabled=True,
        power_sweep_start_dbm=-30.0,
        power_sweep_stop_dbm=-20.0,
        power_sweep_count=2,
        power_calibration_enabled=True,
        power_calibration_database_path="calibration.db",
        power_calibration_run_id=91,
    )
    runtime = build_runtime_rf_pulses(
        {
            "tprocs": [{"f_time": 300.0}],
            "gens": [{"f_fabric": 300.0}],
        },
        (spec,),
    )[0]

    assert runtime.freq_mhz == 100.0
    assert runtime.gain == 100
    assert runtime.sweep_gain_shape == (3, 2)
    assert runtime.sweep_gain_codes == (100, 200, 101, 201, 102, 202)
    assert runtime.power_calibration_run_id == 91
    assert [call[1] for call in calls] == [-30.0, -20.0]
    assert all(
        call[2]
        == {
            "output_att1_db": 10.0,
            "output_att2_db": 5.0,
            "max_entries": 3,
        }
        for call in calls
    )


def test_build_qick_program_reuses_runtime_conversion_without_hardware():
    calls = []

    class FakeSequence:
        def make_program(self, soccfg, **kwargs):
            calls.append((soccfg, kwargs))
            return "program"

    soccfg = {
        "tprocs": [{"f_time": 400.0}],
        "gens": [{"f_fabric": 250.0}],
    }
    rf = QickRfPulseSpec(
        0, "set_0", 0.2, 0.4, 43.5, 10000, 6.0, 7.0
    )

    program = build_qick_program(
        soccfg,
        FakeSequence(),
        awg_channels=(3, 5),
        repetitions_per_sweep=7,
        tproc_mhz=300.0,
        rf_specs=(rf,),
        readout_spec=None,
        compile_validation_mode="boundary",
    )

    assert program == "program"
    kwargs = calls[0][1]
    assert kwargs["awg_channels"] == (3, 5)
    assert kwargs["repetitions_per_sweep"] == 7
    assert kwargs["tproc_mhz"] == 300.0
    assert kwargs["compile_validation_mode"] == "boundary"
    assert kwargs["rf_pulses"][0].delay_tproc_cycles == 60
    assert kwargs["rf_pulses"][0].length_cycles == 100
    assert "ddr_readout" not in kwargs


def test_connect_and_run_support_injected_qick_server(tmp_path, monkeypatch):
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging"))
    ddr_result = _ddr_result()
    calls = []
    progress_updates = []
    event_updates = []

    class FakeSoc:
        def rfb_set_gen_rf(self, gen_ch, att1, att2):
            calls.append(("gen", gen_ch, att1, att2))
            return att1, att2

        def rfb_set_gen_filter(self, gen_ch, **kwargs):
            calls.append(("gen_filter", gen_ch, kwargs))

        def rfb_set_ro_rf(self, ro_ch, attenuation):
            calls.append(("ro", ro_ch, attenuation))
            return attenuation

        def rfb_set_ro_filter(self, ro_ch, **kwargs):
            calls.append(("filter", ro_ch, kwargs))

    class FakeProgram:
        def acquire_fir_ddr(
            self,
            soc,
            progress=False,
            counter_progress=None,
            readback_progress=None,
            phase_callback=None,
        ):
            calls.append(("acquire", soc, progress))
            if phase_callback is not None:
                phase_callback("ddr_arm", "started", "Arming")
                phase_callback("ddr_arm", "completed", "Armed")
                phase_callback("acquisition", "started", "Acquiring")
            if counter_progress is not None:
                counter_progress(0, 4)
                counter_progress(2, 4)
                counter_progress(4, 4)
            if phase_callback is not None:
                phase_callback("acquisition", "completed", "Acquired")
                phase_callback("ddr_readback", "started", "Reading")
            if readback_progress is not None:
                readback_progress(0, 4)
                readback_progress(1, 4)
                readback_progress(4, 4)
            if phase_callback is not None:
                phase_callback("ddr_readback", "completed", "Read")
            return ddr_result

        def summary(self):
            return {"program_instructions": 7}

    class FakeSequence:
        def make_program(self, soccfg, **kwargs):
            calls.append(("program", soccfg, kwargs))
            return FakeProgram()

    soc = FakeSoc()
    soccfg = {
        "tprocs": [{"f_time": 400.0}],
        "gens": [{"f_fabric": 300.0}],
        "ddr4_buf": {
            "sample_capture": True,
            "fir_enabled": True,
            "fir_rate_profile": "1_msps",
            "stored_sample_rate_hz": 1_000_000.0,
            "fir_decimation": 300,
            "fir_input_fs_mhz": 300.0,
            "fir_group_delay_input_samples": 8677.0,
        },
    }

    def connector(**kwargs):
        calls.append(("connect", kwargs))
        return soc, soccfg

    connection = QickConnectionConfig("198.51.100.9", 9999, "testqick")
    assert connect_qick(connection, connector=connector) == (soc, soccfg)
    result = run_qick_qcodes_experiment(
        connection_config=connection,
        run_config=QcodesRunConfig(
            str(tmp_path / "end_to_end.db"),
            experiment_name="Injected QICK",
            sample_name="fake soc",
        ),
        sequence=FakeSequence(),
        awg_channels=(0,),
        repetitions_per_sweep=2,
        rf_specs=(QickRfPulseSpec(
            0, "set_0", 0.0, 0.4, 50.0, 10000, 5.0, 6.0
        ),),
        readout_spec=QickDdrReadoutSpec(0, "set_0", 0.0, 3),
        gui_settings=_gui_metadata(),
        connector=connector,
        progress_callback=lambda percent, message: progress_updates.append(
            (percent, message)
        ),
        event_callback=lambda key, state, message: event_updates.append(
            (key, state, message)
        ),
    )

    assert result.row_count == 12
    assert result.database_path.exists()
    assert not any(call[0] in {"gen", "gen_filter"} for call in calls)
    assert result.rf_settings["output_details"] == ({
        "gen_ch": 0,
        "board_type": "RF_Out",
        "attenuators_present": True,
        "requested_att1_db": 5.0,
        "requested_att2_db": 6.0,
        "commanded_att1_db": 5.0,
        "commanded_att2_db": 6.0,
        "filter_type": "bypass",
        "filter_cutoff_ghz": 2.5,
        "filter_bandwidth_ghz": 1.0,
    },)
    program_call = next(call for call in calls if call[0] == "program")
    assert program_call[2]["tproc_mhz"] == 300.0
    assert program_call[2]["rf_pulses"][0].delay_tproc_cycles == 0
    assert any(call[0] == "acquire" for call in calls)
    assert progress_updates[0][0] == 0
    assert progress_updates[-1] == (100, "Experiment saved")
    assert any(percent == 32 for percent, _ in progress_updates)
    assert any(percent == 55 for percent, _ in progress_updates)
    assert any(percent == 57 for percent, _ in progress_updates)
    assert any(percent == 64 for percent, _ in progress_updates)
    assert any(
        "Reading FIR DDR traces 1/4" in message
        and "3/12 I/Q sample pairs" in message
        for _, message in progress_updates
    )
    assert ("connection", "started") in [
        event[:2] for event in event_updates
    ]
    assert ("connection", "completed") in [
        event[:2] for event in event_updates
    ]
    assert ("compile", "started") in [event[:2] for event in event_updates]
    assert ("compile", "completed") in [event[:2] for event in event_updates]
    assert ("acquisition", "completed") in [
        event[:2] for event in event_updates
    ]
    assert ("ddr_readback", "completed") in [
        event[:2] for event in event_updates
    ]
    assert event_updates[-1][:2] == ("qcodes_save", "completed")


def test_configure_rf_output_applies_attenuators_and_filter_explicitly():
    calls = []

    class FakeSoc:
        def rfb_set_gen_rf(self, gen_ch, att1, att2):
            calls.append(("gen", gen_ch, att1, att2))
            return 5.25, 7.5

        def rfb_set_gen_filter(self, gen_ch, **kwargs):
            calls.append(("filter", gen_ch, kwargs))

    spec = QickRfPulseSpec(
        2,
        "set_0",
        0.0,
        1.0,
        100.0,
        12_000,
        5.25,
        7.5,
        filter_type="lowpass",
        filter_cutoff=2.25,
        filter_bandwidth=0.75,
    )

    details = configure_rf_output(FakeSoc(), spec)

    assert calls == [
        ("gen", 2, 5.25, 7.5),
        (
            "filter",
            2,
            {"fc": 2.25, "bw": 0.75, "ftype": "lowpass"},
        ),
    ]
    assert details["commanded_att1_db"] == 5.25
    assert details["commanded_att2_db"] == 7.5


def test_run_uses_50_ksps_hwh_rate_for_qcodes_time_axis(tmp_path, monkeypatch):
    captured = {}
    ddr_result = _ddr_result()
    soccfg = {
        "tprocs": [{"f_time": 300.0}],
        "gens": [{"f_fabric": 300.0}],
        "ddr4_buf": {
            "sample_capture": True,
            "fir_enabled": True,
            "fir_rate_profile": "50_ksps",
            "stored_sample_rate_hz": 50_000.0,
            "fir_decimation": 6000,
            "fir_input_fs_mhz": 300.0,
            "fir_group_delay_input_samples": 296_677.0,
            "supports_trigger_delay": True,
            "trigger_delay_units": "valid_input_samples",
            "trigger_delay_default_samples": 50,
        },
    }

    class FakeProgram:
        def summary(self):
            return {"fir_rate_profile": "50_ksps"}

    monkeypatch.setattr(
        experiment_module,
        "connect_qick",
        lambda *_args, **_kwargs: (object(), soccfg),
    )
    monkeypatch.setattr(
        experiment_module,
        "execute_qick_sequence",
        lambda *_args, **_kwargs: (FakeProgram(), ddr_result, {}),
    )

    def fake_store(_ddr_result, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(run_id=91, guid="rate-guid"), 1

    monkeypatch.setattr(experiment_module, "store_qick_result", fake_store)
    requested = QcodesRunConfig(str(tmp_path / "rate.db"))
    result = experiment_module.run_qick_qcodes_experiment(
        connection_config=QickConnectionConfig("host", 8888, "proxy"),
        run_config=requested,
        sequence=object(),
        awg_channels=(0,),
        repetitions_per_sweep=1,
        rf_specs=(),
        readout_spec=QickDdrReadoutSpec(0, "set_0", 0.0, 3),
        gui_settings={"qick": {}},
    )

    assert captured["run_config"].sample_rate_hz == 50_000.0
    assert captured["gui_settings"]["qick"]["fir_rate_profile"] == "50_ksps"
    assert captured["gui_settings"]["qick"]["fir_sample_period_us"] == 20.0
    assert result.database_path == requested.resolved_database_path


def test_configure_rf_board_uses_zcu216_dc_chain_apis():
    calls = []

    class FakeSoc:
        def rfb_set_gen_dc(self, gen_ch):
            calls.append(("gen_dc", gen_ch))

        def rfb_set_gen_filter(self, gen_ch, **kwargs):
            calls.append(("gen_filter", gen_ch, kwargs))

        def rfb_set_ro_dc(self, ro_ch, gain):
            calls.append(("ro_dc", ro_ch, gain))
            return gain

        def rfb_set_ro_filter(self, ro_ch, **kwargs):
            calls.append(("ro_filter", ro_ch, kwargs))

    rf = QickRfPulseSpec(
        4,
        "set_0",
        0.0,
        1.0,
        100.0,
        10000,
        7.0,
        8.0,
        output_board_type="DC_Out",
    )
    readout = QickDdrReadoutSpec(
        2,
        "set_0",
        0.0,
        8,
        input_board_type="DC_In",
        dc_gain_db=12.0,
        dc_measure_mode=True,
        dc_measure_gain_v_per_a=1.0e6,
    )

    configured = configure_rf_board(FakeSoc(), (rf,), readout)

    assert ("gen_dc", 4) in calls
    assert ("ro_dc", 2, 12.0) in calls
    assert not any(call[0] in {"gen_filter", "ro_filter"} for call in calls)
    assert configured["outputs"] == ((0.0, 0.0),)
    assert configured["readout"] == 12.0
    assert configured["output_details"][0]["board_type"] == "DC_Out"
    assert configured["output_details"][0]["attenuators_present"] is False
    assert configured["readout_details"]["board_type"] == "DC_In"
    assert configured["readout_details"]["commanded_dc_gain_db"] == 12.0
    assert configured["readout_details"]["dc_measure_mode"] is True
    assert configured["readout_details"]["dc_measure_gain_v_per_a"] == 1.0e6
    assert configured["readout_details"]["adc_to_voltage_conversion"] == "identity"
    assert configured["readout_details"]["measurement_unit"] == "A"
