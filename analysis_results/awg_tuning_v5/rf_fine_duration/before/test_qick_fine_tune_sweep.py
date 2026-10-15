"""Focused tests for tProcessor loop/add AWG amplitude sweeps.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

import numpy as np
import pytest

# Desktop imports need the PYNQ stubs installed before regular QICK modules.
from qick.sim import QickSim  # noqa: F401
from qick.awg_tuning import TProcV1BehaviorModel
from qick.qick_asm import QickConfig

import qick_fine_tune_sweep as sweep_module
from qick_fine_tune_sweep import (
    COMPILE_VALIDATION_BOUNDARY,
    COMPILE_VALIDATION_FULL,
    DdrFirReadoutConfig,
    FineTuneSequence,
    HoldDurationSweep,
    RampDurationSweep,
    ReadoutConfig,
    RfPulseConfig,
)


def _mock_soccfg(n_outputs=2):
    gens = []
    for index in range(n_outputs):
        gens.append({
            "type": "axis_awg_tuning_v1",
            "gen_type": "awg_tuning",
            "tproc_ch": 0,
            "tmux_ch": index,
            "f_fabric": 300.0,
            "n_pts": 16,
            "samps_per_clk": 16,
            "frac": 16,
            "cmd_width": 160,
            "step_width": 24,
            "duration_width": 23,
            "fixed_width": 48,
            "dac_invalid_lsb": 2,
            "maxv": 32764,
            "minv": -32768,
            "ramp_startup_latency_cycles": 7,
            "ramp_guard_cycles": 1,
            "has_mixer": False,
            "has_dds": False,
            "b_dds": 32,
            "b_phase": 32,
            "dac": f"{index:02d}",
            "interpolation": 1,
        })
    return QickConfig({
        "sw_version": "0.2.357",
        "tprocs": [{
            "type": "axis_tproc64x32_x8",
            "f_time": 300.0,
            "pmem_size": 65536,
            "dmem_size": 4096,
            "output_pins": [],
        }],
        "gens": gens,
        "readouts": [],
    })


def _independent_awg_soccfg(n_outputs=2):
    cfg = _mock_soccfg(n_outputs)
    for index, gen in enumerate(cfg["gens"]):
        gen["tproc_ch"] = index
    return cfg


def _shared_tmux_soccfg():
    """Normal RF gen and AWG tuning share tProc port 0 through a TMUX."""
    cfg = _mock_soccfg(1)._cfg
    awg = dict(cfg["gens"][0])
    awg.update({"tmux_ch": 1, "dac": "10"})
    signal_gen = {
        "type": "axis_signal_gen_v6",
        "tproc_ch": 0,
        "tmux_ch": 0,
        "f_fabric": 300.0,
        "f_dds": 300.0,
        "fs_mult": 1,
        "fs_div": 1,
        "fdds_div": 1,
        "samps_per_clk": 16,
        "maxlen": 16384,
        "maxv": 32766,
        "maxv_scale": 1.0,
        "complex_env": True,
        "has_mixer": False,
        "has_dds": True,
        "b_dds": 32,
        "b_phase": 32,
        "dac": "00",
        "interpolation": 1,
    }
    cfg["gens"] = [signal_gen, awg]
    cfg["refclk_freq"] = 300.0
    return QickConfig(cfg)


def _fir_soccfg(*, fir_rate_profile="1_msps", ddr_trigger_port=0):
    cfg = _mock_soccfg(1)._cfg
    is_50_ksps = fir_rate_profile == "50_ksps"
    cfg["refclk_freq"] = 300.0
    cfg["readouts"] = [{
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
    }]
    cfg["ddr4_buf"] = {
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
            "s_axis_aclk_cycles" if is_50_ksps else "valid_input_samples"
        ),
        "trigger_delay_default_cycles": 50 if is_50_ksps else 0,
        "trigger_delay_default_samples": 0,
        "trigger_type": "dport",
        "trigger_port": int(ddr_trigger_port),
        "trigger_bit": 1,
    }
    return QickConfig(cfg)


def _avg_soccfg(n_outputs=2):
    """Mock the normal accumulated-readout path used by AVG buffer tests."""
    cfg = _mock_soccfg(n_outputs)._cfg
    cfg["refclk_freq"] = 300.0
    cfg["readouts"] = [{
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
    }]
    return QickConfig(cfg)


def _command_word(command):
    return sum(
        (int(word) & 0xFFFFFFFF) << (32 * index)
        for index, word in enumerate(command.words)
    )


def _expected_words(program):
    expected = []
    for point in program.compiled_points:
        point_words = [
            _command_word(command)
            for commands in point.segment_commands
            for command in commands
        ]
        for _ in range(program.cfg["reps"]):
            expected.extend(point_words)
    return expected


def _make_cartesian_sequence():
    sequence = FineTuneSequence(("awg_0", "awg_1"))
    sequence.set_cross_capacitance(((1.0, 0.0), (0.25, 1.0)))
    sequence.add_set("start", (-0.25, 0.15), 12)
    sequence.add_ramp("to_gate", 24)
    sequence.add_set("gate", (0.1, -0.2), 18)
    sequence.add_ramp("to_measure", 20)
    sequence.add_set("measure", (0.3, 0.2), 16)
    sequence.add_amplitude_sweep("gate", "awg_0", -0.53, 0.47, 4)
    sequence.add_amplitude_sweep("measure", "awg_1", -0.31, 0.29, 3)
    return sequence


def test_set_and_ramp_words_are_updated_by_nested_loop_and_add():
    sequence = _make_cartesian_sequence()
    program = sequence.make_program(
        _mock_soccfg(),
        awg_channels=(0, 1),
        repetitions_per_sweep=3,
    )
    program.compile()

    tproc = TProcV1BehaviorModel(strict=True)
    tproc.run(program.prog_list, max_steps=1_000_000)

    assert [event.word for event in tproc.output_events] == _expected_words(program)
    assert sum(inst["name"] == "loopnz" for inst in program.prog_list) == 3
    assert any(
        inst["name"] == "mathi" and inst["args"][3] == "+"
        for inst in program.prog_list
    )
    assert not any(inst["name"] in {"memr", "memri"} for inst in program.prog_list)
    assert program.summary()["sweep_execution"] == "tproc_loop_and_add"
    assert program.summary()["sweep_uses_point_table"] is False

    swept_kinds = {
        program.compiled_points[0]
        .segment_commands[field["command_key"][0]][0]
        .kind
        for field in program._sweep_fields
    }
    assert swept_kinds == {"set", "ramp"}


def test_boundary_validation_matches_full_cartesian_tproc_output():
    sequence = _make_cartesian_sequence()
    full = sequence.make_program(
        _mock_soccfg(),
        awg_channels=(0, 1),
        repetitions_per_sweep=2,
        compile_validation_mode=COMPILE_VALIDATION_FULL,
    )
    boundary = sequence.make_program(
        _mock_soccfg(),
        awg_channels=(0, 1),
        repetitions_per_sweep=2,
        compile_validation_mode=COMPILE_VALIDATION_BOUNDARY,
    )
    full.compile()
    boundary.compile()

    full_tproc = TProcV1BehaviorModel(strict=True)
    boundary_tproc = TProcV1BehaviorModel(strict=True)
    full.load_runtime_dmem_into_model(full_tproc)
    boundary.load_runtime_dmem_into_model(boundary_tproc)
    full_tproc.run(full.prog_list, max_steps=1_000_000)
    boundary_tproc.run(boundary.prog_list, max_steps=1_000_000)

    assert sequence.sweep_point_count == 12
    assert len(full.compiled_points) == 12
    assert boundary._compile_validation_point_indices == (0, 2, 9, 11)
    assert len(boundary._compiled_point_by_index) == 4
    assert len(boundary.compiled_points) == 1
    assert [event.word for event in boundary_tproc.output_events] == [
        event.word for event in full_tproc.output_events
    ]
    assert boundary._runtime_dmem_words == full._runtime_dmem_words
    assert boundary.summary()["compile_validation_mode"] == "boundary"
    assert boundary.summary()["compile_validation_point_count"] == 4


def test_boundary_validation_does_not_expand_million_point_sweep():
    sequence = FineTuneSequence(("awg_0", "awg_1", "awg_2"))
    sequence.add_set("base", (0.0, 0.0, 0.0), 16)
    for output_index in range(3):
        sequence.add_amplitude_sweep(
            "base",
            f"awg_{output_index}",
            -0.5,
            0.5,
            101,
        )

    program = sequence.make_program(
        _independent_awg_soccfg(3),
        awg_channels=(0, 1, 2),
        repetitions_per_sweep=1,
        compile_validation_mode=COMPILE_VALIDATION_BOUNDARY,
    )

    assert sequence.sweep_point_count == 1_030_301
    assert program._compile_validation_point_indices == (
        0,
        100,
        10_100,
        10_200,
        1_020_100,
        1_020_200,
        1_030_200,
        1_030_300,
    )
    assert len(program.compiled_points) == 1
    assert program._compiled_point_by_index is not None
    assert len(program._compiled_point_by_index) == 8
    assert len(program.prog_list) < 500


def test_ramp_rate_sweep_recomputes_steps_for_adjacent_voltage_axes():
    sequence = FineTuneSequence(("awg_0", "awg_1"))
    sequence.set_cross_capacitance(((1.0, 0.2), (-0.15, 1.0)))
    sequence.add_set("start", (-0.2, 0.1), 18)
    sequence.add_ramp("ramp_0_to_1", 30)
    sequence.add_set("gate", (0.35, -0.25), 24)
    sequence.add_ramp_duration_sweep(
        "ramp_0_to_1",
        start_us=0.08,
        stop_us=0.12,
        count=4,
        sequence_fabric_mhz=300.0,
    )
    sequence.add_amplitude_sweep("start", "awg_0", -0.3, 0.3, 3)
    sequence.add_amplitude_sweep("gate", "awg_1", -0.4, 0.4, 5)

    assert isinstance(sequence.sweep_axes[0], RampDurationSweep)
    assert sequence.sweep_shape == (4, 3, 5)

    program = sequence.make_program(
        _mock_soccfg(2),
        awg_channels=(0, 1),
        repetitions_per_sweep=2,
    )
    program.compile()

    tproc = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(tproc)
    tproc.run(program.prog_list, max_steps=2_000_000)

    assert [event.word for event in tproc.output_events] == _expected_words(program)
    assert tproc.timing_conflicts == []
    summary = program.summary()
    assert summary["sweep_execution"] == (
        "tproc_loop_add_with_ramp_rate_coefficients"
    )
    assert summary["sweep_uses_point_table"] is False
    assert summary["ramp_rate_coefficient_table_words"] > 0
    assert summary["ramp_rate_coefficient_table_words"] < np.prod(
        sequence.sweep_shape
    )
    assert summary["sweep_max_duration_quantization_error"] == 0

    ramp_durations = {
        command.duration_samples
        for point in program.compiled_points
        for command in point.segment_commands[1]
    }
    assert ramp_durations == {24 * 16, 28 * 16, 32 * 16, 36 * 16}
    ramp_steps = {
        command.step
        for point in program.compiled_points
        for command in point.segment_commands[1]
    }
    assert len(ramp_steps) > len(ramp_durations)


def test_boundary_validation_matches_full_for_duration_table_and_bias_t():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (-0.2,), 18)
    sequence.add_ramp("to_gate", 30)
    sequence.add_set("gate", (0.35,), 24)
    sequence.add_ramp_duration_sweep(
        "to_gate",
        start_us=0.08,
        stop_us=0.12,
        count=4,
        sequence_fabric_mhz=300.0,
    )
    sequence.add_amplitude_sweep("gate", "awg_0", -0.4, 0.4, 5)
    sequence.set_bias_t_compensation(0.1)

    programs = {}
    events = {}
    for mode in (COMPILE_VALIDATION_FULL, COMPILE_VALIDATION_BOUNDARY):
        program = sequence.make_program(
            _independent_awg_soccfg(1),
            awg_channels=(0,),
            repetitions_per_sweep=1,
            recovery_tproc_cycles=0,
            compile_validation_mode=mode,
        )
        program.compile()
        tproc = TProcV1BehaviorModel(strict=True)
        program.load_runtime_dmem_into_model(tproc)
        tproc.run(program.prog_list, max_steps=2_000_000)
        assert tproc.timing_conflicts == []
        programs[mode] = program
        events[mode] = [event.word for event in tproc.output_events]

    boundary = programs[COMPILE_VALIDATION_BOUNDARY]
    full = programs[COMPILE_VALIDATION_FULL]
    assert sequence.sweep_point_count == 20
    assert len(boundary._compile_validation_point_indices) == 8
    assert events[COMPILE_VALIDATION_BOUNDARY] == events[COMPILE_VALIDATION_FULL]
    assert boundary._runtime_dmem_words == full._runtime_dmem_words
    assert boundary._bias_t_max_duration_q_error == (
        full._bias_t_max_duration_q_error
    )
    assert boundary._bias_t_max_target_code_error == (
        full._bias_t_max_target_code_error
    )


def test_independent_ramp_rate_sweeps_use_nested_tables_without_point_table():
    sequence = FineTuneSequence(("awg_0", "awg_1"))
    sequence.set_cross_capacitance(((1.0, 0.2), (-0.15, 1.0)))
    sequence.add_set("start", (-0.2, 0.1), 18)
    sequence.add_ramp("ramp_0_to_1", 30)
    sequence.add_set("gate", (0.35, -0.25), 24)
    sequence.add_ramp("ramp_1_to_2", 36)
    sequence.add_set("measure", (0.1, 0.4), 20)
    sequence.add_ramp_duration_sweep(
        "ramp_0_to_1",
        start_us=0.08,
        stop_us=0.12,
        count=3,
        sequence_fabric_mhz=300.0,
    )
    sequence.add_ramp_duration_sweep(
        "ramp_1_to_2",
        start_us=0.10,
        stop_us=0.16,
        count=4,
        sequence_fabric_mhz=300.0,
    )
    sequence.add_amplitude_sweep("start", "awg_0", -0.3, 0.3, 2)
    sequence.add_amplitude_sweep("measure", "awg_1", -0.4, 0.4, 3)

    assert tuple(
        axis.segment_name
        for axis in sequence.sweep_axes
        if isinstance(axis, RampDurationSweep)
    ) == ("ramp_0_to_1", "ramp_1_to_2")
    assert sequence.sweep_shape == (3, 4, 2, 3)

    program = sequence.make_program(
        _mock_soccfg(2),
        awg_channels=(0, 1),
        repetitions_per_sweep=1,
    )
    program.compile()

    tproc = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(tproc)
    tproc.run(program.prog_list, max_steps=4_000_000)

    assert [event.word for event in tproc.output_events] == _expected_words(program)
    assert tproc.timing_conflicts == []
    assert {
        int(group["axis_index"])
        for group in program._ramp_duration_table_groups.values()
    } == {0, 1}
    assert len({
        int(group["pointer_state_addr"])
        for group in program._ramp_duration_table_groups.values()
    }) == len(program._ramp_duration_table_groups)

    first_durations = {
        command.duration_samples
        for point in program.compiled_points
        for command in point.segment_commands[1]
    }
    second_durations = {
        command.duration_samples
        for point in program.compiled_points
        for command in point.segment_commands[3]
    }
    assert first_durations == {24 * 16, 30 * 16, 36 * 16}
    assert second_durations == {30 * 16, 36 * 16, 42 * 16, 48 * 16}

    summary = program.summary()
    assert summary["sweep_uses_point_table"] is False
    assert summary["ramp_rate_coefficient_table_words"] > 0
    assert summary["ramp_rate_coefficient_table_words"] < (
        sequence.sweep_point_count * 2
    )
    assert len(summary["ramp_duration_sweeps"]) == 2


def test_two_ramp_rate_axes_drive_exact_dc_bias_t_duration_table():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (0.4,), 18)
    sequence.add_ramp("positive_ramp", 30)
    sequence.add_set("middle", (0.2,), 18)
    sequence.add_ramp("negative_ramp", 40)
    sequence.add_set("finish", (-0.6,), 18)
    sequence.add_ramp_duration_sweep(
        "positive_ramp",
        start_us=0.08,
        stop_us=0.16,
        count=3,
        sequence_fabric_mhz=300.0,
    )
    sequence.add_ramp_duration_sweep(
        "negative_ramp",
        start_us=0.08,
        stop_us=0.34,
        count=4,
        sequence_fabric_mhz=300.0,
    )
    sequence.set_bias_t_compensation(0.1)

    program = sequence.make_program(
        _mock_soccfg(1),
        awg_channels=(0,),
        repetitions_per_sweep=1,
        recovery_tproc_cycles=0,
    )
    program.compile()

    assert program._bias_t_max_duration_q_error == 0
    assert np.array_equal(
        program._bias_t_duration_q_actual,
        program._bias_t_duration_q_requested,
    )
    assert {
        tuple(int(axis) for axis in group["axis_indices"])
        for group in program._ramp_duration_table_groups.values()
    } >= {(0,), (1,), (0, 1)}
    bias_field = program._bias_t_fields[0]
    assert tuple(bias_field["duration_axis_indices"]) == (0, 1)
    assert tuple(bias_field["duration_table_shape"]) == (3, 4)
    assert len(bias_field["duration_table_bases"]) == 12

    tproc = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(tproc)
    tproc.run(program.prog_list, max_steps=2_000_000)

    positive = int(bias_field["positive_code"])
    negative = int(bias_field["negative_code"])
    compensation_events = []
    for event in tproc.output_events:
        target = event.word & 0xFFFFFFFF
        target = target - (1 << 32) if target & (1 << 31) else target
        if target in {positive, negative}:
            compensation_events.append((event, target))
    expected_q = [
        int(value)
        for value in program._bias_t_duration_q_actual[:, 0]
    ]
    assert len(compensation_events) == len(expected_q)
    assert {np.sign(value) for value in expected_q} == {-1, 1}
    for (event, target), duration_q in zip(compensation_events, expected_q):
        expected_target = negative if duration_q > 0 else positive
        assert target == expected_target
        following_zero = next(
            candidate
            for candidate in tproc.output_events
            if candidate.tproc_ch == event.tproc_ch
            and candidate.cycle > event.cycle
            and (candidate.word & 0xFFFFFFFF) == 0
        )
        expected_duration = (abs(duration_q) + (1 << 7)) >> 8
        assert following_zero.cycle - event.cycle == expected_duration
    assert tproc.timing_conflicts == []


def test_two_ramp_rate_axes_support_fixed_time_dc_bias_t_compensation():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (0.1,), 18)
    sequence.add_ramp("first_ramp", 12)
    sequence.add_set("middle", (0.3,), 18)
    sequence.add_ramp("second_ramp", 18)
    sequence.add_set("finish", (-0.2,), 18)
    sequence.add_ramp_duration_sweep(
        "first_ramp",
        start_us=0.04,
        stop_us=0.08,
        count=3,
        sequence_fabric_mhz=300.0,
    )
    sequence.add_ramp_duration_sweep(
        "second_ramp",
        start_us=0.06,
        stop_us=0.12,
        count=2,
        sequence_fabric_mhz=300.0,
    )
    sequence.set_bias_t_compensation(
        0.1,
        mode="fixed_time",
        fixed_duration_cycles=128,
    )

    program = sequence.make_program(
        _mock_soccfg(1),
        awg_channels=(0,),
        recovery_tproc_cycles=0,
    )
    program.compile()

    assert program.summary()["bias_t_compensation_mode"] == "fixed_time"
    assert program._bias_t_max_target_code_error == 0
    assert np.array_equal(
        program._bias_t_target_code_actual,
        program._bias_t_target_code_requested,
    )
    assert tuple(program._bias_t_fields[0]["duration_axis_indices"]) == (0, 1)

    tproc = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(tproc)
    tproc.run(program.prog_list, max_steps=2_000_000)
    assert tproc.timing_conflicts == []


def test_two_ramp_rate_bias_t_table_refreshes_inner_voltage_axis_delta():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (0.1,), 18)
    sequence.add_ramp("first_ramp", 30)
    sequence.add_set("middle", (0.2,), 18)
    sequence.add_ramp("second_ramp", 36)
    sequence.add_set("finish", (0.3,), 18)
    sequence.add_ramp_duration_sweep(
        "first_ramp",
        start_us=0.08,
        stop_us=0.16,
        count=3,
        sequence_fabric_mhz=300.0,
    )
    sequence.add_ramp_duration_sweep(
        "second_ramp",
        start_us=0.10,
        stop_us=0.20,
        count=2,
        sequence_fabric_mhz=300.0,
    )
    sequence.add_amplitude_sweep(
        "finish",
        "awg_0",
        0.2,
        0.4,
        3,
    )
    sequence.set_bias_t_compensation(0.125)

    program = sequence.make_program(
        _mock_soccfg(1),
        awg_channels=(0,),
        recovery_tproc_cycles=0,
    )
    program.compile()

    bias_field = program._bias_t_fields[0]
    assert tuple(bias_field["duration_axis_indices"]) == (0, 1)
    assert set(bias_field["duration_delta_slots"]) == {2}
    assert program._bias_t_max_duration_q_error <= 1

    tproc = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(tproc)
    tproc.run(program.prog_list, max_steps=3_000_000)

    positive = int(bias_field["positive_code"])
    negative = int(bias_field["negative_code"])
    compensation_events = []
    for event in tproc.output_events:
        target = event.word & 0xFFFFFFFF
        target = target - (1 << 32) if target & (1 << 31) else target
        if target in {positive, negative}:
            compensation_events.append(event)
    expected_q = [
        int(value)
        for value in program._bias_t_duration_q_actual[:, 0]
    ]
    assert len(compensation_events) == len(expected_q)
    for event, duration_q in zip(compensation_events, expected_q):
        following_zero = next(
            candidate
            for candidate in tproc.output_events
            if candidate.tproc_ch == event.tproc_ch
            and candidate.cycle > event.cycle
            and (candidate.word & 0xFFFFFFFF) == 0
        )
        assert following_zero.cycle - event.cycle == (
            abs(duration_q) + (1 << 7)
        ) >> 8
    assert tproc.timing_conflicts == []


def test_ramp_rate_sweep_replaces_and_clears_only_its_target_segment():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (0.0,), 18)
    sequence.add_ramp("ramp_0_to_1", 30)
    sequence.add_set("gate", (0.4,), 24)
    sequence.add_ramp("ramp_1_to_2", 36)
    sequence.add_set("measure", (-0.2,), 60)
    sequence.add_ramp_duration_sweep(
        "ramp_0_to_1",
        start_us=0.08,
        stop_us=0.12,
        count=3,
        sequence_fabric_mhz=300.0,
    )
    sequence.add_ramp_duration_sweep(
        "ramp_1_to_2",
        start_us=0.10,
        stop_us=0.16,
        count=4,
        sequence_fabric_mhz=300.0,
    )
    sequence.add_ramp_duration_sweep(
        "ramp_0_to_1",
        start_us=0.20,
        stop_us=0.24,
        count=2,
        sequence_fabric_mhz=300.0,
    )

    assert tuple(axis.segment_name for axis in sequence.sweep_axes) == (
        "ramp_0_to_1",
        "ramp_1_to_2",
    )
    assert sequence.sweep_axes[0].points == (0.20, 0.24)
    assert sequence.sweep_axes[1].points == (0.10, 0.12, 0.14, 0.16)

    sequence.clear_ramp_duration_sweep("ramp_0_to_1")
    assert tuple(axis.segment_name for axis in sequence.sweep_axes) == (
        "ramp_1_to_2",
    )


def test_ramp_rate_sweep_moves_50_ksps_ddr_trigger_with_segment():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (0.0,), 18)
    sequence.add_ramp("ramp_0_to_1", 30)
    sequence.add_set("capture", (0.4,), 60)
    sequence.add_ramp_duration_sweep(
        "ramp_0_to_1",
        start_us=0.08,
        stop_us=0.12,
        count=3,
        sequence_fabric_mhz=300.0,
    )
    ddr = DdrFirReadoutConfig(
        ro_ch=0,
        samples_per_trigger=8,
        at_segment="capture",
        trigger_delay_tproc_cycles=17,
        margin_input_samples=0,
    )
    program = sequence.make_program(
        _fir_soccfg(
            fir_rate_profile="50_ksps",
            ddr_trigger_port=7,
        ),
        awg_channels=(0,),
        repetitions_per_sweep=1,
        ddr_readout=ddr,
    )
    program.compile()

    tproc = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(tproc)
    tproc.run(program.prog_list, max_steps=500_000)

    awg_events = [
        event for event in tproc.output_events if event.tproc_ch == 0
    ]
    trigger_high = [
        event
        for event in tproc.output_events
        if event.tproc_ch == 7 and event.word == 1 << 1
    ]
    trigger_low = [
        event
        for event in tproc.output_events
        if event.tproc_ch == 7 and event.word == 0
    ]
    assert [event.word for event in awg_events] == _expected_words(program)
    assert len(trigger_high) == 3
    assert len(trigger_low) == 3
    assert len(awg_events) == 3 * 3
    for point_index, (trigger_event, low_event) in enumerate(
        zip(trigger_high, trigger_low)
    ):
        capture_set_event = awg_events[point_index * 3 + 2]
        assert trigger_event.cycle - capture_set_event.cycle == 17
        assert low_event.cycle - trigger_event.cycle == ddr.trigger_width_tproc_cycles
    assert all(
        instruction.get("name") != "setb"
        for instruction in program.prog_list
        if isinstance(instruction, dict)
    )
    assert program.summary()["fir_software_warmup_compensation"] is False
    assert tproc.timing_conflicts == []


def test_hold_duration_sweep_moves_later_commands_and_50_ksps_trigger():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (0.0,), 18)
    sequence.add_ramp("to_capture", 30)
    sequence.add_set("capture", (0.4,), 60)
    sequence.add_hold_duration_sweep(
        "start",
        start_us=0.10,
        stop_us=0.20,
        count=3,
        sequence_fabric_mhz=300.0,
    )

    assert isinstance(sequence.sweep_axes[0], HoldDurationSweep)
    assert sequence.sweep_axes[0].duration_cycles_points == (30, 45, 60)
    assert tuple(
        sequence.segment_duration_cycles_at(point_index, 0)
        for point_index in range(3)
    ) == (30, 45, 60)
    assert tuple(
        sequence.waveform_vertices(point_index)[0][-1]
        for point_index in range(3)
    ) == (120.0, 135.0, 150.0)

    ddr = DdrFirReadoutConfig(
        ro_ch=0,
        samples_per_trigger=8,
        at_segment="capture",
        trigger_delay_tproc_cycles=17,
        margin_input_samples=0,
    )
    program = sequence.make_program(
        _fir_soccfg(
            fir_rate_profile="50_ksps",
            ddr_trigger_port=7,
        ),
        awg_channels=(0,),
        repetitions_per_sweep=1,
        ddr_readout=ddr,
    )
    program.compile()

    tproc = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(tproc)
    tproc.run(program.prog_list, max_steps=500_000)

    awg_events = [
        event for event in tproc.output_events if event.tproc_ch == 0
    ]
    trigger_high = [
        event
        for event in tproc.output_events
        if event.tproc_ch == 7 and event.word == 1 << 1
    ]
    trigger_low = [
        event
        for event in tproc.output_events
        if event.tproc_ch == 7 and event.word == 0
    ]
    assert [event.word for event in awg_events] == _expected_words(program)
    assert len(trigger_high) == 3
    assert len(trigger_low) == 3
    for point_index, (trigger_event, low_event) in enumerate(
        zip(trigger_high, trigger_low)
    ):
        capture_set_event = awg_events[point_index * 3 + 2]
        assert trigger_event.cycle - capture_set_event.cycle == 17
        assert low_event.cycle - trigger_event.cycle == (
            ddr.trigger_width_tproc_cycles
        )
    assert len(program.summary()["hold_duration_sweeps"]) == 1
    assert tproc.timing_conflicts == []


def test_hold_duration_axis_drives_exact_bias_t_duration_table():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (0.4,), 18)
    sequence.add_ramp("to_middle", 30)
    sequence.add_set("middle", (0.2,), 18)
    sequence.add_ramp("to_finish", 40)
    sequence.add_set("finish", (-0.6,), 18)
    sequence.add_hold_duration_sweep(
        "middle",
        start_us=0.06,
        stop_us=0.10,
        count=3,
        sequence_fabric_mhz=300.0,
    )
    sequence.add_amplitude_sweep(
        "finish",
        "awg_0",
        -0.6,
        -0.4,
        2,
    )
    sequence.set_bias_t_compensation(0.1)

    program = sequence.make_program(
        _mock_soccfg(1),
        awg_channels=(0,),
        repetitions_per_sweep=1,
        recovery_tproc_cycles=0,
    )
    program.compile()

    bias_field = program._bias_t_fields[0]
    assert tuple(bias_field["duration_axis_indices"]) == (0,)
    assert tuple(bias_field["duration_table_shape"]) == (3,)
    assert program._bias_t_max_duration_q_error <= 1

    tproc = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(tproc)
    tproc.run(program.prog_list, max_steps=1_000_000)
    assert len(tproc.output_events) > len(_expected_words(program))
    assert tproc.timing_conflicts == []


def test_two_ramp_rate_axes_move_50_ksps_ddr_trigger_additively():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (0.0,), 18)
    sequence.add_ramp("ramp_0_to_1", 30)
    sequence.add_set("gate", (0.4,), 24)
    sequence.add_ramp("ramp_1_to_2", 36)
    sequence.add_set("capture", (-0.2,), 60)
    sequence.add_ramp_duration_sweep(
        "ramp_0_to_1",
        start_us=0.08,
        stop_us=0.12,
        count=2,
        sequence_fabric_mhz=300.0,
    )
    sequence.add_ramp_duration_sweep(
        "ramp_1_to_2",
        start_us=0.10,
        stop_us=0.16,
        count=3,
        sequence_fabric_mhz=300.0,
    )
    ddr = DdrFirReadoutConfig(
        ro_ch=0,
        samples_per_trigger=8,
        at_segment="capture",
        trigger_delay_tproc_cycles=17,
        margin_input_samples=0,
    )
    program = sequence.make_program(
        _fir_soccfg(fir_rate_profile="50_ksps"),
        awg_channels=(0,),
        repetitions_per_sweep=1,
        ddr_readout=ddr,
    )
    program.compile()

    tproc = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(tproc)
    tproc.run(program.prog_list, max_steps=1_000_000)

    awg_events = [
        event
        for event in tproc.output_events
        if event.tproc_ch == 0 and event.word not in (0, 1 << 1)
    ]
    trigger_high = [
        event
        for event in tproc.output_events
        if event.tproc_ch == 0 and event.word == 1 << 1
    ]
    trigger_low = [
        event
        for event in tproc.output_events
        if event.tproc_ch == 0 and event.word == 0
    ]
    commands_per_point = 5
    assert len(trigger_high) == 6
    assert len(trigger_low) == 6
    assert [event.word for event in awg_events] == _expected_words(program)
    for point_index, (trigger_event, low_event) in enumerate(
        zip(trigger_high, trigger_low)
    ):
        capture_set_event = awg_events[
            point_index * commands_per_point + commands_per_point - 1
        ]
        assert trigger_event.cycle - capture_set_event.cycle == 17
        assert low_event.cycle - trigger_event.cycle == ddr.trigger_width_tproc_cycles
    assert all(
        instruction.get("name") != "setb"
        for instruction in program.prog_list
        if isinstance(instruction, dict)
    )
    assert tproc.timing_conflicts == []


def test_50_ksps_ddr_delay_stays_in_fpga_without_tproc_timing_shift(monkeypatch):
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("capture", (0.25,), 300)
    ddr = DdrFirReadoutConfig(
        ro_ch=0,
        samples_per_trigger=8,
        at_segment="capture",
        trigger_delay_tproc_cycles=17,
        margin_input_samples=0,
    )
    baseline = sequence.make_program(
        _fir_soccfg(fir_rate_profile="50_ksps"),
        awg_channels=(0,),
        repetitions_per_sweep=1,
    )
    program = sequence.make_program(
        _fir_soccfg(fir_rate_profile="50_ksps"),
        awg_channels=(0,),
        repetitions_per_sweep=1,
        ddr_readout=ddr,
    )

    assert program.timing["segment_starts"] == baseline.timing["segment_starts"]
    assert program.aux_timing["fir_warmup_tproc_cycles"] == 0
    assert program.aux_timing["ddr_readout_start"] == 0
    assert program.aux_timing["ddr_trigger_time"] == (
        baseline.timing["segment_starts"][0] + 17
    )
    assert program.summary()["fir_rate_profile"] == "50_ksps"
    assert program.summary()["fir_software_warmup_compensation"] is False

    raw = np.arange(8 * 2, dtype=np.int32).reshape(8, 2)

    class FakeSoc:
        def arm_ddr4_fir_samples(self, **kwargs):
            self.arm_kwargs = kwargs
            return 16

        def get_ddr4_fir_samples(self, **_kwargs):
            return raw

    soc = FakeSoc()
    monkeypatch.setattr(program, "run_rounds", lambda *_args, **_kwargs: None)
    result = program.acquire_fir_ddr(soc, progress=False)

    assert soc.arm_kwargs["trigger_delay_cycles"] == 50
    assert result.iq.shape == (1, 1, 8, 2)
    assert result.sample_rate_hz == 50_000.0
    assert result.fir_rate_profile == "50_ksps"


def test_1_msps_ddr_trigger_is_delayed_to_the_fir_step_center():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("capture", (0.25,), 300)
    ddr = DdrFirReadoutConfig(
        ro_ch=0,
        samples_per_trigger=8,
        at_segment="capture",
        trigger_delay_tproc_cycles=0,
        margin_input_samples=0,
    )
    program = sequence.make_program(
        _fir_soccfg(fir_rate_profile="1_msps", ddr_trigger_port=7),
        awg_channels=(0,),
        repetitions_per_sweep=1,
        ddr_readout=ddr,
    )

    capture_start = program.timing["segment_starts"][0]
    assert program.aux_timing["ddr_readout_start"] == 0
    assert program.aux_timing["fir_warmup_tproc_cycles"] == 8677
    assert program.aux_timing["fir_software_trigger_delay_tproc_cycles"] == 8397
    assert program.aux_timing["ddr_trigger_time"] - capture_start == 8397
    assert program.summary()["fir_software_trigger_delay_output_samples"] == 28
    assert program.summary()["fir_software_trigger_delay_input_samples"] == 8397

    program.compile()
    tproc = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(tproc)
    tproc.run(program.prog_list, max_steps=500_000)

    capture_command = next(
        event for event in tproc.output_events if event.tproc_ch == 0
    )
    trigger_high = next(
        event
        for event in tproc.output_pin_events
        if event["port"] == 7 and event["word"] == 1 << 1
    )
    assert trigger_high["cycle"] - capture_command.cycle == 8397
    assert tproc.timing_conflicts == []


def test_fir_ddr_readback_is_chunked_by_trigger_on_the_client(monkeypatch):
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("capture", (0.0,), 300)
    sequence.set_amplitude_sweep("capture", "awg_0", -0.2, 0.2, 3)
    ddr = DdrFirReadoutConfig(
        ro_ch=0,
        samples_per_trigger=10,
        at_segment="capture",
        margin_input_samples=0,
        address=128,
        settle_seconds=0.0,
    )
    program = sequence.make_program(
        _fir_soccfg(fir_rate_profile="50_ksps"),
        awg_channels=(0,),
        repetitions_per_sweep=2,
        ddr_readout=ddr,
    )

    class FakeSoc:
        def __init__(self):
            self.read_calls = []

        def arm_ddr4_fir_samples(self, **kwargs):
            self.arm_kwargs = kwargs
            return kwargs["n_triggers"] * 16

        def get_ddr4_fir_samples(self, **kwargs):
            self.read_calls.append(kwargs)
            first_trigger = (kwargs["start"] - 32) // 16
            count = kwargs["n_triggers"]
            values = np.empty((count * 10, 2), dtype=np.int16)
            for local_trigger in range(count):
                trigger = first_trigger + local_trigger
                first_sample = local_trigger * 10
                values[first_sample:first_sample + 10, 0] = trigger
                values[first_sample:first_sample + 10, 1] = -trigger
            return values

    soc = FakeSoc()
    phase_events = []
    readback_updates = []
    monkeypatch.setattr(program, "run_rounds", lambda *_args, **_kwargs: None)
    result = program.acquire_fir_ddr(
        soc,
        progress=False,
        readback_progress=lambda completed, total: readback_updates.append(
            (completed, total)
        ),
        phase_callback=lambda key, state, message: phase_events.append(
            (key, state, message)
        ),
        readback_chunk_triggers=4,
    )

    assert soc.arm_kwargs["n_triggers"] == 6
    assert [
        (call["start"], call["n_triggers"])
        for call in soc.read_calls
    ] == [(32, 4), (96, 2)]
    assert result.iq.shape == (3, 2, 10, 2)
    np.testing.assert_array_equal(
        result.iq[:, :, 0, 0].reshape(-1),
        np.arange(6),
    )
    np.testing.assert_array_equal(
        result.iq[:, :, 0, 1].reshape(-1),
        -np.arange(6),
    )
    assert [event[:2] for event in phase_events] == [
        ("ddr_arm", "started"),
        ("ddr_arm", "completed"),
        ("acquisition", "started"),
        ("acquisition", "completed"),
        ("ddr_readback", "started"),
        ("ddr_readback", "completed"),
    ]
    assert readback_updates == [(0, 6), (4, 6), (6, 6)]


def test_50_ksps_ddr_does_not_repeat_fir_group_delay_between_points():
    sequence = FineTuneSequence(("awg_0",))
    # Stability-style point: ten 50 kSPS samples plus one microsecond guard.
    sequence.add_set("capture", (0.0,), 60_300)
    sequence.set_amplitude_sweep("capture", "awg_0", -0.25, 0.25, 2)
    ddr = DdrFirReadoutConfig(
        ro_ch=0,
        samples_per_trigger=10,
        at_segment="capture",
        margin_input_samples=0,
        fpga_trigger_delay_samples=0,
    )
    baseline = sequence.make_program(
        _fir_soccfg(fir_rate_profile="50_ksps"),
        awg_channels=(0,),
        repetitions_per_sweep=1,
        recovery_tproc_cycles=0,
    )
    program = sequence.make_program(
        _fir_soccfg(fir_rate_profile="50_ksps"),
        awg_channels=(0,),
        repetitions_per_sweep=1,
        ddr_readout=ddr,
        recovery_tproc_cycles=0,
    )

    assert program._fir_cfg["trigger_delay_arm_kwargs"] == {
        "trigger_delay_cycles": 0
    }
    assert program.aux_timing["ddr_capture_end"] == 60_000
    assert program.timing["point_end"] == baseline.timing["point_end"] == 60_300
    assert program.timing["point_end"] < int(
        np.ceil(program._fir_cfg["group_delay_input_samples"])
    )


def test_legacy_50_ksps_fpga_delay_does_not_serialize_awg_sweep_points():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("capture", (0.0,), 60_300)
    sequence.set_amplitude_sweep("capture", "awg_0", -0.25, 0.25, 2)
    soccfg = _fir_soccfg(fir_rate_profile="50_ksps")
    ddr_cfg = soccfg._cfg["ddr4_buf"]
    ddr_cfg["trigger_delay_units"] = "valid_input_samples"
    ddr_cfg.pop("trigger_delay_default_cycles", None)
    ddr_cfg["trigger_delay_default_samples"] = 50
    ddr = DdrFirReadoutConfig(
        ro_ch=0,
        samples_per_trigger=10,
        at_segment="capture",
        margin_input_samples=0,
    )

    program = sequence.make_program(
        soccfg,
        awg_channels=(0,),
        repetitions_per_sweep=1,
        ddr_readout=ddr,
        recovery_tproc_cycles=0,
    )

    assert program._fir_cfg["trigger_delay_input_cycles"] == 300_000
    assert program._fir_cfg["trigger_delay_arm_kwargs"] == {
        "trigger_delay_samples": 50
    }
    assert program.aux_timing["ddr_capture_end"] == 60_000
    assert program.timing["point_end"] == 60_300


def test_pmem_size_does_not_scale_with_sweep_point_count():
    instruction_counts = []
    for count in (3, 101):
        sequence = FineTuneSequence(("awg_0",))
        sequence.add_set("start", (-0.2,), 10)
        sequence.add_ramp("to_gate", 24)
        sequence.add_set("gate", (0.4,), 12)
        sequence.set_amplitude_sweep("gate", "awg_0", -0.73, 0.61, count)
        program = sequence.make_program(_mock_soccfg(1), awg_channels=(0,))
        program.compile()
        instruction_counts.append(len(program.prog_list))

    assert instruction_counts[0] == instruction_counts[1]


def test_direct_register_sweep_scales_to_eight_outputs():
    names = tuple(f"awg_{index}" for index in range(8))
    coupling = np.eye(8)
    coupling[:, 0] = np.linspace(1.0, 0.125, 8)
    sequence = FineTuneSequence(names)
    sequence.set_cross_capacitance(coupling)
    sequence.add_set("start", (0.0,) * 8, 30)
    sequence.add_ramp("to_gate", 40)
    sequence.add_set("gate", (0.1,) * 8, 30)
    sequence.set_amplitude_sweep("gate", "awg_0", -0.4, 0.4, 5)
    program = sequence.make_program(
        _mock_soccfg(8),
        awg_channels=tuple(range(8)),
    )
    program.compile()

    tproc = TProcV1BehaviorModel(strict=True)
    tproc.run(program.prog_list, max_steps=1_000_000)
    assert [event.word for event in tproc.output_events] == _expected_words(program)
    assert len(program.awg_channels) == 8
    assert not any(inst["name"] in {"memr", "memri"} for inst in program.prog_list)


def test_set_duration_excludes_startup_lead_and_hides_ramp_pipeline():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("set_0", (0.0,), 300)
    sequence.add_ramp("ramp_0", 300)
    sequence.add_set("set_1", (0.5,), 300)
    sequence.add_ramp("ramp_1", 300)
    sequence.add_set("set_2", (0.0,), 300)
    program = sequence.make_program(
        _mock_soccfg(1),
        awg_channels=(0,),
        repetitions_per_sweep=2,
        command_lead_tproc_cycles=128,
    )
    program.compile()

    for segment_index in (0, 2, 4):
        actual = (
            program.timing["segment_ends"][segment_index]
            - program.timing["segment_starts"][segment_index]
        )
        assert actual == 300

    startup = 7
    first_set_command = program.timing["command_times"][(0, 0)]
    first_ramp_command = program.timing["command_times"][(1, 0)]
    assert first_set_command == 0
    assert first_ramp_command + startup - first_set_command == 300
    assert program.summary()["startup_lead_tproc_cycles_once"] == 128

    tproc = TProcV1BehaviorModel(strict=True)
    tproc.run(program.prog_list, max_steps=100_000)
    command_cycles = [event.cycle for event in tproc.output_events]
    commands_per_point = program.summary()["commands_per_point"]
    assert command_cycles[0] == 128
    assert command_cycles[commands_per_point] - command_cycles[0] == (
        program.timing["point_end"] + program.recovery_tproc_cycles
    )


def test_manual_tproc_clock_overrides_stale_hwh_for_all_program_timing():
    soccfg = _mock_soccfg(1)
    soccfg["tprocs"][0]["f_time"] = 400.0
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (0.0,), 300)
    sequence.add_ramp("to_gate", 300)
    sequence.add_set("gate", (0.5,), 300)

    program = sequence.make_program(
        soccfg,
        awg_channels=(0,),
        tproc_mhz=300.0,
    )
    program.compile()

    assert soccfg["tprocs"][0]["f_time"] == 400.0
    assert program.tproccfg["f_time"] == 300.0
    assert program.timing["segment_ends"][0] == 300
    assert program.summary()["tproc_mhz"] == 300.0
    assert program.summary()["hwh_tproc_mhz"] == 400.0
    assert program.summary()["tproc_clock_is_manual"] is True

    fallback = sequence.make_program(soccfg, awg_channels=(0,))
    fallback.compile()
    assert fallback.timing["segment_ends"][0] == 400
    assert fallback.summary()["tproc_clock_is_manual"] is False


def test_shared_tmux_commands_are_enqueued_in_timestamp_order():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (0.0,), 100)
    sequence.add_ramp("to_gate", 100)
    sequence.add_set("gate", (0.4,), 400)
    sequence.add_ramp("to_end", 100)
    sequence.add_set("end", (0.0,), 100)
    rf = RfPulseConfig(
        gen_ch=0,
        at_segment="gate",
        length_cycles=30,
        gain=10000,
        freq_mhz=0.0,
        delay_tproc_cycles=20,
    )
    program = sequence.make_program(
        _shared_tmux_soccfg(),
        awg_channels=(1,),
        rf_pulse=rf,
    )
    program.compile()

    tproc = TProcV1BehaviorModel(strict=True)
    tproc.run(program.prog_list, max_steps=100_000)
    port_zero_events = [
        event for event in tproc.output_events if event.tproc_ch == 0
    ]
    event_cycles = [event.cycle for event in port_zero_events]
    assert event_cycles == sorted(event_cycles)

    tmux_channels = [(event.word >> 152) & 0xFF for event in port_zero_events]
    rf_index = tmux_channels.index(0)
    assert ((port_zero_events[rf_index].word >> 148) & 1) == 0
    assert port_zero_events[rf_index].cycle == (
        program.command_lead_tproc_cycles + program.aux_timing["rf_start"]
    )
    assert any(
        event.cycle > port_zero_events[rf_index].cycle
        and tmux_channel == 1
        for event, tmux_channel in zip(port_zero_events, tmux_channels)
    )


def test_shared_tmux_accepts_rf_exactly_one_clock_after_awg_set():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("set_0", (0.25,), 100)
    rf = RfPulseConfig(
        gen_ch=0,
        at_segment="set_0",
        length_cycles=30,
        gain=10_000,
        freq_mhz=10.0,
        delay_tproc_cycles=1,
    )
    program = sequence.make_program(
        _shared_tmux_soccfg(),
        awg_channels=(1,),
        rf_pulse=rf,
    )
    program.compile()

    assert program.timing["segment_starts"][0] == 0
    assert tuple(program.timing["command_times"].values()) == (0,)
    assert program.aux_timing["rf_requested_start"] == 1
    assert program.aux_timing["rf_start"] == 1
    assert program.aux_timing["rf_command_skew_tproc_cycles"] == 0

    tproc = TProcV1BehaviorModel(strict=True)
    tproc.run(program.prog_list, max_steps=100_000)
    port_zero_events = [
        event for event in tproc.output_events if event.tproc_ch == 0
    ]
    awg_set = next(
        event
        for event in port_zero_events
        if ((event.word >> 152) & 0xFF) == 1
        and ((event.word >> 144) & 0b11) == 0b01
    )
    rf_start = next(
        event
        for event in port_zero_events
        if ((event.word >> 152) & 0xFF) == 0
    )
    assert rf_start.cycle - awg_set.cycle == 1


def test_long_rf_pulse_uses_periodic_start_and_timed_zero_stop():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("measure", (0.25,), 400_000)
    rf = RfPulseConfig(
        gen_ch=0,
        at_segment="measure",
        length_cycles=300_000,
        gain=12_000,
        freq_mhz=10.0,
        require_within_segment=True,
    )
    program = sequence.make_program(
        _shared_tmux_soccfg(),
        awg_channels=(1,),
        rf_pulse=rf,
        repetitions_per_sweep=2,
    )
    program.compile()

    assert program.aux_timing["rf_mode"] == "periodic_timed_stop"
    assert program.aux_timing["rf_end"] - program.aux_timing["rf_start"] == 300_000

    tproc = TProcV1BehaviorModel(strict=True)
    tproc.run(program.prog_list, max_steps=100_000)
    rf_events = [
        event
        for event in tproc.output_events
        if event.tproc_ch == 0 and ((event.word >> 152) & 0xFF) == 0
    ]
    assert len(rf_events) == 4
    assert rf_events[1].cycle - rf_events[0].cycle == 300_000
    assert rf_events[3].cycle - rf_events[2].cycle == 300_000


@pytest.mark.parametrize(
    ("segment_length_mode", "expected_ramp_offsets"),
    [
        ("fixed", [92, 92, 92]),
        ("extend_by_rf_duration", [102, 112, 122]),
    ],
)
def test_rf_duration_sweep_updates_length_and_selected_segment_timing(
    segment_length_mode,
    expected_ramp_offsets,
):
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("gate", (0.0,), 100)
    sequence.add_ramp("to_end", 20)
    sequence.add_set("end", (0.25,), 100)
    sequence.add_rf_duration_sweep(
        "gate",
        0,
        10 / 300,
        30 / 300,
        3,
        segment_length_mode=segment_length_mode,
        sequence_fabric_mhz=300.0,
    )
    rf = RfPulseConfig(
        gen_ch=0,
        at_segment="gate",
        length_cycles=10,
        gain=12_000,
        require_within_segment=True,
    )
    program = sequence.make_program(
        _shared_tmux_soccfg(),
        awg_channels=(1,),
        rf_pulse=rf,
        command_lead_tproc_cycles=0,
        recovery_tproc_cycles=0,
    )
    program.compile()

    tproc = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(tproc)
    tproc.run(program.prog_list, max_steps=100_000)
    rf_events = [
        event
        for event in tproc.output_events
        if event.tproc_ch == 0 and ((event.word >> 152) & 0xFF) == 0
    ]
    assert program.aux_timing["rf_mode"] == "oneshot"
    assert len(rf_events) == 3
    assert [(event.word >> 128) & 0xFFFF for event in rf_events] == [10, 20, 30]
    rf_gain_words = [
        (event.word >> 96) & 0xFFFFFFFF
        for event in rf_events
    ]
    assert rf_gain_words == [12_000, 12_000, 12_000]

    awg_ramps = [
        event
        for event in tproc.output_events
        if (
            event.tproc_ch == 0
            and ((event.word >> 152) & 0xFF) == 1
            and ((event.word >> 144) & 0x3) == 0b10
        )
    ]
    assert len(awg_ramps) == 3
    assert [
        ramp.cycle - rf_events[index].cycle
        for index, ramp in enumerate(awg_ramps)
    ] == expected_ramp_offsets
    expected_segment_lengths = (
        [100, 100, 100]
        if segment_length_mode == "fixed"
        else [110, 120, 130]
    )
    assert [
        sequence.segment_duration_cycles_at(point_index, 0)
        for point_index in range(3)
    ] == expected_segment_lengths


def test_rf_duration_is_a_cartesian_axis_with_amplitude_sweep():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("gate", (0.0,), 100)
    sequence.add_amplitude_sweep("gate", "awg_0", -0.25, 0.25, 2)
    sequence.add_rf_duration_sweep(
        "gate",
        0,
        10 / 300,
        30 / 300,
        3,
        sequence_fabric_mhz=300.0,
    )
    assert sequence.sweep_shape == (2, 3)
    np.testing.assert_allclose(
        sequence.sweep_coordinates,
        [
            [-0.25, 10 / 300],
            [-0.25, 20 / 300],
            [-0.25, 30 / 300],
            [0.25, 10 / 300],
            [0.25, 20 / 300],
            [0.25, 30 / 300],
        ],
    )


def test_named_composite_rf_duration_axes_shift_following_pulse_timestamps():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("gate", (0.0,), 200)
    sequence.add_rf_duration_sweep(
        "gate",
        0,
        10 / 300,
        20 / 300,
        2,
        parameter_name="d0",
        output_name="rf_gen_0_d0_duration",
    )
    sequence.add_rf_duration_sweep(
        "gate",
        0,
        30 / 300,
        50 / 300,
        2,
        parameter_name="d1",
        output_name="rf_gen_0_d1_duration",
    )
    pulses = (
        RfPulseConfig(
            gen_ch=0,
            at_segment="gate",
            length_cycles=10,
            gain=12_000,
            event_id="prepare",
            pulse_name="prepare",
            duration_parameter="d0",
        ),
        RfPulseConfig(
            gen_ch=0,
            at_segment="gate",
            length_cycles=30,
            gain=8_000,
            delay_tproc_cycles=11,
            event_id="read",
            pulse_name="read",
            duration_parameter="d1",
            preceding_duration_parameters=("d0",),
        ),
    )
    program = sequence.make_program(
        _shared_tmux_soccfg(),
        awg_channels=(1,),
        rf_pulses=pulses,
        command_lead_tproc_cycles=0,
        recovery_tproc_cycles=0,
    )
    program.compile()

    assert sequence.sweep_shape == (2, 2)
    assert [axis.parameter_name for axis in sequence.sweep_axes] == ["d0", "d1"]
    models = {model["key"]: model for model in program._event_timing_models}
    assert models[("event_time", "rf_stop", 0)]["axis_deltas"] == (10, 0)
    assert models[("event_time", "rf_start", 1)]["axis_deltas"] == (10, 0)
    assert models[("event_time", "rf_stop", 1)]["axis_deltas"] == (10, 20)


def test_composite_segment_extension_sums_shared_duration_parameters():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("gate", (0.0,), 20)
    sequence.add_ramp("to_end", 10)
    sequence.add_set("end", (0.25,), 20)
    sequence.set_rf_segment_length_extension(
        "gate",
        0,
        40,
        parameter_multiplicities={"d0": 2, "d1": 1},
    )
    sequence.add_rf_duration_sweep(
        "gate",
        0,
        10 / 300,
        20 / 300,
        2,
        segment_length_mode="extend_by_rf_duration",
        parameter_name="d0",
    )
    sequence.add_rf_duration_sweep(
        "gate",
        0,
        20 / 300,
        40 / 300,
        2,
        segment_length_mode="extend_by_rf_duration",
        parameter_name="d1",
    )

    assert sequence.sweep_shape == (2, 2)
    assert [
        sequence.segment_duration_cycles_at(point_index, 0)
        for point_index in range(4)
    ] == [60, 80, 80, 100]

    pulses = (
        RfPulseConfig(
            gen_ch=0,
            at_segment="gate",
            length_cycles=10,
            gain=12_000,
            event_id="prepare_a",
            duration_parameter="d0",
        ),
        RfPulseConfig(
            gen_ch=0,
            at_segment="gate",
            length_cycles=10,
            gain=12_000,
            delay_tproc_cycles=10,
            event_id="prepare_b",
            duration_parameter="d0",
            preceding_duration_parameters=("d0",),
        ),
        RfPulseConfig(
            gen_ch=0,
            at_segment="gate",
            length_cycles=20,
            gain=8_000,
            delay_tproc_cycles=20,
            event_id="read",
            duration_parameter="d1",
            preceding_duration_parameters=("d0", "d0"),
        ),
    )
    program = sequence.make_program(
        _shared_tmux_soccfg(),
        awg_channels=(1,),
        rf_pulses=pulses,
        command_lead_tproc_cycles=0,
        recovery_tproc_cycles=0,
    )
    program.compile()
    assert program._extension_axis_deltas(
        1,
        include_current=False,
    ) == (20, 20)


def test_rf_frequency_and_power_sweeps_load_exact_dmem_words():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("gate", (0.0,), 100)
    sequence.add_rf_frequency_sweep(
        "gate",
        0,
        10.0,
        30.0,
        3,
    )
    sequence.add_rf_power_sweep(
        "gate",
        0,
        -30.0,
        -20.0,
        2,
    )
    rf = RfPulseConfig(
        gen_ch=0,
        at_segment="gate",
        length_cycles=20,
        gain=101,
        freq_mhz=10.0,
        sweep_gain_codes=(101, 102, 201, 202, 301, 302),
        sweep_gain_shape=(3, 2),
        power_calibration_run_id=77,
    )
    program = sequence.make_program(
        _shared_tmux_soccfg(),
        awg_channels=(1,),
        rf_pulse=rf,
        command_lead_tproc_cycles=0,
        recovery_tproc_cycles=0,
    )
    program.compile()

    tproc = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(tproc)
    tproc.run(program.prog_list, max_steps=200_000)
    rf_events = [
        event
        for event in tproc.output_events
        if event.tproc_ch == 0 and ((event.word >> 152) & 0xFF) == 0
    ]
    assert len(rf_events) == 6
    expected_frequencies = [
        program._rf_frequency_word(rf, frequency)
        for frequency in (10.0, 10.0, 20.0, 20.0, 30.0, 30.0)
    ]
    assert [event.word & 0xFFFFFFFF for event in rf_events] == (
        expected_frequencies
    )
    assert [
        (event.word >> 96) & 0xFFFFFFFF for event in rf_events
    ] == [101, 102, 201, 202, 301, 302]
    assert any(
        instruction["name"] == "memr"
        for instruction in program.prog_list
    )
    summary = program.summary()
    assert summary["rf_frequency_sweeps"] == 1
    assert summary["rf_power_sweeps"] == 1
    assert summary["rf_point_table_count"] == 2
    assert summary["rf_point_table_words"] == 9


def test_composite_rf_events_share_one_named_frequency_dmem_table():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("gate", (0.0,), 200)
    sequence.add_rf_frequency_sweep(
        "gate",
        0,
        10.0,
        30.0,
        3,
        parameter_name="f0",
    )
    pulses = (
        RfPulseConfig(
            gen_ch=0,
            at_segment="gate",
            length_cycles=20,
            gain=1000,
            freq_mhz=10.0,
            delay_tproc_cycles=10,
            event_id="prepare",
            pulse_name="prepare",
            frequency_parameter="f0",
        ),
        RfPulseConfig(
            gen_ch=0,
            at_segment="gate",
            length_cycles=10,
            gain=2000,
            freq_mhz=10.0,
            delay_tproc_cycles=60,
            event_id="read",
            pulse_name="read",
            frequency_parameter="f0",
        ),
    )
    program = sequence.make_program(
        _shared_tmux_soccfg(),
        awg_channels=(1,),
        rf_pulses=pulses,
        command_lead_tproc_cycles=0,
        recovery_tproc_cycles=0,
    )
    program.compile()

    summary = program.summary()
    assert summary["rf_frequency_sweeps"] == 1
    assert summary["rf_point_table_count"] == 1
    assert summary["rf_point_table_words"] == 3
    frequency_tables = [
        table
        for table in program._rf_point_tables
        if table["register_name"] == "rf_frequency"
    ]
    assert len(frequency_tables) == 1
    assert frequency_tables[0]["event_indices"] == (0, 1)

    tproc = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(tproc)
    tproc.run(program.prog_list, max_steps=200_000)
    rf_events = [
        event
        for event in tproc.output_events
        if event.tproc_ch == 0 and ((event.word >> 152) & 0xFF) == 0
    ]
    assert len(rf_events) == 6
    expected = [
        program._rf_frequency_word(pulses[0], frequency)
        for frequency in (10.0, 10.0, 20.0, 20.0, 30.0, 30.0)
    ]
    assert [event.word & 0xFFFFFFFF for event in rf_events] == expected


def test_composite_rf_calibration_uses_event_specific_gain_dmem_table():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("gate", (0.0,), 200)
    sequence.add_rf_frequency_sweep(
        "gate",
        0,
        10.0,
        30.0,
        3,
        parameter_name="f0",
    )
    pulses = (
        RfPulseConfig(
            gen_ch=0,
            at_segment="gate",
            length_cycles=20,
            gain=101,
            freq_mhz=10.0,
            delay_tproc_cycles=10,
            sweep_gain_codes=(101, 102, 103),
            sweep_gain_shape=(3, 1),
            power_calibration_run_id=73,
            event_id="calibrated",
            pulse_name="calibrated",
            frequency_parameter="f0",
        ),
        RfPulseConfig(
            gen_ch=0,
            at_segment="gate",
            length_cycles=10,
            gain=2000,
            freq_mhz=10.0,
            delay_tproc_cycles=60,
            event_id="manual",
            pulse_name="manual",
            frequency_parameter="f0",
        ),
    )
    program = sequence.make_program(
        _shared_tmux_soccfg(),
        awg_channels=(1,),
        rf_pulses=pulses,
        command_lead_tproc_cycles=0,
        recovery_tproc_cycles=0,
    )
    program.compile()

    summary = program.summary()
    assert summary["rf_point_table_count"] == 2
    assert summary["rf_point_table_words"] == 6
    gain_tables = [
        table
        for table in program._rf_point_tables
        if table["register_name"] == "rf_gain"
    ]
    assert len(gain_tables) == 1
    assert gain_tables[0]["event_indices"] == (0,)

    tproc = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(tproc)
    tproc.run(program.prog_list, max_steps=200_000)
    rf_events = [
        event
        for event in tproc.output_events
        if event.tproc_ch == 0 and ((event.word >> 152) & 0xFF) == 0
    ]
    assert len(rf_events) == 6
    assert [
        (event.word >> 96) & 0xFFFFFFFF for event in rf_events
    ] == [101, 2000, 102, 2000, 103, 2000]


def test_rf_and_readout_phase_reset_are_fixed_off():
    rf = RfPulseConfig(
        gen_ch=0,
        at_segment="gate",
        length_cycles=30,
        gain=10000,
    )
    readout = ReadoutConfig(ro_ch=0, length=16)
    assert rf.phrst == 0
    assert readout.phrst == 0

    with pytest.raises(ValueError, match="RF output phrst is fixed to 0"):
        RfPulseConfig(
            gen_ch=0,
            at_segment="gate",
            length_cycles=30,
            gain=10000,
            phrst=1,
        )
    with pytest.raises(ValueError, match="readout phrst is fixed to 0"):
        ReadoutConfig(ro_ch=0, length=16, phrst=1)


def test_waveform_vertices_reconstruct_swept_virtual_and_physical_pulses():
    sequence = FineTuneSequence(("awg_0", "awg_1"))
    sequence.set_cross_capacitance(((1.0, 0.0), (0.5, 1.0)))
    sequence.add_set("start", (0.0, 0.0), 10)
    sequence.add_ramp("to_gate", 5)
    sequence.add_set("gate", (0.4, -0.2), 8)
    sequence.set_amplitude_sweep("gate", "awg_0", -0.4, 0.4, 3)

    virtual_t, virtual, _ = sequence.waveform_vertices(0, space="virtual")
    physical_t, physical, _ = sequence.waveform_vertices(0, space="physical")
    assert virtual_t.tolist() == [0.0, 10.0, 15.0, 23.0]
    assert physical_t.tolist() == virtual_t.tolist()
    assert virtual["awg_0"].tolist() == [0.0, 0.0, -0.4, -0.4]
    assert virtual["awg_1"].tolist() == [0.0, 0.0, -0.2, -0.2]
    assert physical["awg_0"].tolist() == [0.0, 0.0, -0.4, -0.4]
    assert physical["awg_1"].tolist() == [0.0, 0.0, -0.4, -0.4]

    jump = FineTuneSequence(("awg_0",))
    jump.add_set("low", (0.0,), 10)
    jump.add_set("high", (1.0,), 5)
    jump_t, jump_values, _ = jump.waveform_vertices(space="virtual")
    assert jump_t.tolist() == [0.0, 10.0, 10.0, 15.0]
    assert jump_values["awg_0"].tolist() == [0.0, 0.0, 1.0, 1.0]


def test_counter_progress_tracks_hardware_sweep_and_repetition_count():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (0.0,), 10)
    sequence.set_amplitude_sweep("start", "awg_0", -0.2, 0.2, 3)
    program = sequence.make_program(
        _mock_soccfg(1),
        awg_channels=(0,),
        repetitions_per_sweep=2,
    )
    calls = []

    class FakeSoc:
        counts = iter((0, 2, 6))

        def reload_mem(self):
            calls.append("reload")

        def clear_tproc_counter(self, addr):
            calls.append(("clear", addr))

        def start_src(self, source):
            calls.append(("source", source))

        def start_tproc(self):
            calls.append("start")

        def get_tproc_counter(self, addr):
            calls.append(("counter", addr))
            return next(self.counts)

    program.config_all = lambda *args, **kwargs: calls.append("config")
    progress = []
    program._run_rounds_with_counter_progress(
        FakeSoc(),
        lambda completed, total: progress.append((completed, total)),
        poll_interval_seconds=0.0,
    )

    assert progress == [(0, 6), (0, 6), (2, 6), (6, 6)]
    assert program.summary()["repetitions_per_sweep_point"] == 2
    assert program.summary()["total_acquisitions"] == 6
    assert calls.count("start") == 1
    assert calls[-1] == ("source", "internal")


def test_avg_buffer_cartesian_sweep_and_repetitions_are_tprocessor_loops():
    sequence = FineTuneSequence(("awg_0", "awg_1"))
    sequence.add_set("set_0", (0.0, 0.0), 300)
    sequence.add_amplitude_sweep("set_0", "awg_0", -0.2, 0.2, 3)
    sequence.add_amplitude_sweep("set_0", "awg_1", -0.1, 0.1, 2)
    program = sequence.make_program(
        _avg_soccfg(2),
        awg_channels=(0, 1),
        repetitions_per_sweep=4,
        readout=ReadoutConfig(
            ro_ch=0,
            length=8,
            freq_mhz=19.0,
            at_segment="set_0",
            timing_reference="segment_start",
            measure_delay_tproc_cycles=10,
        ),
        recovery_tproc_cycles=25,
    )
    program.compile()

    tproc = TProcV1BehaviorModel(strict=True).run(
        program.prog_list,
        max_steps=1_000_000,
    )
    summary = program.summary()

    assert sequence.sweep_shape == (3, 2)
    assert program.loop_dims == [6, 4]
    assert summary["total_acquisitions"] == 24
    assert summary["avg_buffer_readout"] is True
    assert summary["acquisition_source"] == "avg_buffer"
    assert sum(event.tproc_ch == 0 for event in tproc.output_events) == 48
    assert sum(event.tproc_ch == 1 for event in tproc.output_events) == 24
    assert tproc.timing_conflicts == []


def test_avg_buffer_acquisition_restores_cartesian_points(monkeypatch):
    sequence = FineTuneSequence(("awg_0", "awg_1"))
    sequence.add_set("set_0", (0.0, 0.0), 300)
    sequence.add_amplitude_sweep("set_0", "awg_0", -0.2, 0.2, 3)
    sequence.add_amplitude_sweep("set_0", "awg_1", -0.1, 0.1, 2)
    program = sequence.make_program(
        _avg_soccfg(2),
        awg_channels=(0, 1),
        repetitions_per_sweep=4,
        readout=ReadoutConfig(
            ro_ch=0,
            length=8,
            at_segment="set_0",
            timing_reference="segment_start",
        ),
    )
    progress_updates = []

    def fake_acquire(_program, _soc, *, progress=False, **_kwargs):
        assert progress is False
        return (
            sequence.sweep_points,
            [np.asarray([[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]])],
            [np.asarray([[-1.0, -2.0, -3.0, -4.0, -5.0, -6.0]])],
        )

    monkeypatch.setattr(sweep_module.RAveragerProgram, "acquire", fake_acquire)
    result = program.acquire_avg_buffer(
        object(),
        counter_progress=lambda completed, total: progress_updates.append(
            (completed, total)
        ),
    )

    assert progress_updates == [(0, 24), (24, 24)]
    assert result.acquisition_source == "avg_buffer"
    assert result.accumulation_repetitions == 4
    assert result.iq.shape == (6, 1, 1, 2)
    assert result.sweep_shape == (3, 2)
    np.testing.assert_allclose(result.sweep_points, sequence.sweep_points)
    np.testing.assert_allclose(result.iq[:, 0, 0, 0], np.arange(1.0, 7.0))
    np.testing.assert_allclose(result.iq[:, 0, 0, 1], -np.arange(1.0, 7.0))


def test_program_compilation_observes_cancellation_between_sweep_points():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (0.0,), 10)
    sequence.set_amplitude_sweep("start", "awg_0", -0.4, 0.4, 100)

    class Cancelled(RuntimeError):
        pass

    checks = 0

    def cancel_check():
        nonlocal checks
        checks += 1
        if checks >= 10:
            raise Cancelled("compile stopped")

    with pytest.raises(Cancelled, match="compile stopped"):
        sequence.make_program(
            _mock_soccfg(1),
            awg_channels=(0,),
            repetitions_per_sweep=1,
            compile_validation_mode=COMPILE_VALIDATION_FULL,
            cancel_check=cancel_check,
        )

    assert checks == 10


def test_counter_progress_cancellation_stops_tprocessor():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (0.0,), 10)
    sequence.set_amplitude_sweep("start", "awg_0", -0.2, 0.2, 3)
    program = sequence.make_program(
        _mock_soccfg(1),
        awg_channels=(0,),
        repetitions_per_sweep=2,
    )
    calls = []

    class Cancelled(RuntimeError):
        pass

    class FakeSoc:
        def reload_mem(self):
            calls.append("reload")

        def clear_tproc_counter(self, addr):
            calls.append(("clear", addr))

        def start_src(self, source):
            calls.append(("source", source))

        def start_tproc(self):
            calls.append("start")

        def stop_tproc(self):
            calls.append("stop")

        def get_tproc_counter(self, addr):
            calls.append(("counter", addr))
            return 0

    checks = 0

    def cancel_check():
        nonlocal checks
        checks += 1
        if checks >= 4:
            raise Cancelled("stop")

    program.config_all = lambda *args, **kwargs: calls.append("config")
    with pytest.raises(Cancelled, match="stop"):
        program._run_rounds_with_counter_progress(
            FakeSoc(),
            lambda _completed, _total: None,
            poll_interval_seconds=0.0,
            cancel_check=cancel_check,
        )

    assert calls.count("start") == 1
    assert calls.count("stop") == 1
    assert calls[-1] == ("source", "internal")


def test_fir_ddr_cancellation_stops_between_readback_chunks(monkeypatch):
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("capture", (0.0,), 300)
    sequence.set_amplitude_sweep("capture", "awg_0", -0.2, 0.2, 3)
    program = sequence.make_program(
        _fir_soccfg(fir_rate_profile="50_ksps"),
        awg_channels=(0,),
        repetitions_per_sweep=2,
        ddr_readout=DdrFirReadoutConfig(
            ro_ch=0,
            samples_per_trigger=2,
            at_segment="capture",
            margin_input_samples=0,
            settle_seconds=0.0,
        ),
    )

    class Cancelled(RuntimeError):
        pass

    class FakeSoc:
        def __init__(self):
            self.cancelled = False
            self.read_calls = 0

        def arm_ddr4_fir_samples(self, **kwargs):
            return kwargs["n_triggers"] * 8

        def get_ddr4_fir_samples(self, **kwargs):
            self.read_calls += 1
            self.cancelled = True
            return np.zeros((kwargs["n_triggers"] * 2, 2), dtype=np.int16)

    soc = FakeSoc()
    monkeypatch.setattr(
        program,
        "_run_rounds_with_counter_progress",
        lambda *_args, **_kwargs: None,
    )

    def cancel_check():
        if soc.cancelled:
            raise Cancelled("readback stopped")

    with pytest.raises(Cancelled, match="readback stopped"):
        program.acquire_fir_ddr(
            soc,
            progress=False,
            cancel_check=cancel_check,
            readback_chunk_triggers=2,
        )

    assert soc.read_calls == 1


def test_bias_t_preview_cancels_positive_and_negative_physical_area():
    sequence = FineTuneSequence(("awg_0", "awg_1"))
    sequence.add_set("hold", (0.2, -0.1), 10)
    sequence.set_bias_t_compensation(0.1)

    previews = sequence.bias_t_compensation_preview()
    assert previews[0].pulse_area == 2.0
    assert previews[0].target_amplitude == -0.1
    assert previews[0].duration_cycles == 20
    assert previews[0].residual_area == 0.0
    assert previews[1].pulse_area == -1.0
    assert previews[1].target_amplitude == 0.1
    assert previews[1].duration_cycles == 10
    assert previews[1].residual_area == 0.0

    times, values, boundaries = sequence.compensated_waveform_vertices()
    assert times[-1] == 95.0
    assert values["awg_0"][-1] == 0.0
    assert values["awg_1"][-1] == 0.0
    starts = {name: start for name, start, _end in boundaries[-2:]}
    ends = {name: end for name, _start, end in boundaries[-2:]}
    assert starts == {
        "bias_t_comp_awg_0": 75.0,
        "bias_t_comp_awg_1": 75.0,
    }
    assert ends == {
        "bias_t_comp_awg_0": 95.0,
        "bias_t_comp_awg_1": 85.0,
    }
    assert [name for name, _start, _end in boundaries[-2:]] == [
        "bias_t_comp_awg_0",
        "bias_t_comp_awg_1",
    ]


def test_bias_t_duration_is_swept_and_applied_by_tprocessor_sync():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("start", (0.1,), 20)
    sequence.add_ramp("to_gate", 100)
    sequence.add_set("gate", (0.2,), 20)
    sequence.set_amplitude_sweep("gate", "awg_0", 0.2, 0.4, 3)
    sequence.set_bias_t_compensation(0.1)
    program = sequence.make_program(
        _mock_soccfg(1),
        awg_channels=(0,),
        repetitions_per_sweep=2,
    )
    program.compile()

    assert any(inst["name"] == "sync" for inst in program.prog_list)
    assert any(
        inst["name"] == "bitwi" and inst["args"][3:] == (">>", 8)
        for inst in program.prog_list
    )
    assert program.summary()["bias_t_duration_execution"] == (
        "tproc_simultaneous_set_and_max_sync"
    )
    assert program.summary()["bias_t_dynamic_register_fields"] == 0
    assert program.summary()["bias_t_dynamic_dmem_fields"] == 1
    assert program._bias_t_duration_q_actual[:, 0].tolist() == sorted(
        program._bias_t_duration_q_actual[:, 0].tolist()
    )

    tproc = TProcV1BehaviorModel(strict=True).run(
        program.prog_list,
        max_steps=1_000_000,
    )
    compensation_code = program._bias_t_fields[0]["negative_code"] & 0xFFFFFFFF
    expected_durations = [
        (abs(int(value)) + (1 << 7)) >> 8
        for value in program._bias_t_duration_q_actual[:, 0]
        for _rep in range(program.cfg["reps"])
    ]
    compensation_events = [
        event
        for event in tproc.output_events
        if (event.word & 0xFFFFFFFF) == compensation_code
    ]
    assert len(compensation_events) == len(expected_durations)
    for event, duration in zip(compensation_events, expected_durations):
        following_zero = next(
            candidate
            for candidate in tproc.output_events
            if candidate.cycle > event.cycle
            and (candidate.word & 0xFFFFFFFF) == 0
        )
        assert following_zero.cycle - event.cycle == duration


def test_bias_t_compensation_dmem_state_fits_eight_outputs():
    names = tuple(f"awg_{index}" for index in range(8))
    sequence = FineTuneSequence(names)
    sequence.add_set("hold", tuple(0.05 * (index + 1) for index in range(8)), 20)
    sequence.set_bias_t_compensation(0.1)
    program = sequence.make_program(
        _independent_awg_soccfg(8),
        awg_channels=tuple(range(8)),
    )
    program.compile()
    assert len(program._bias_t_fields) == 8
    assert len({
        field["dmem_addr"]
        for field in program._bias_t_fields
    }) == 8
    assert all("state_register" not in field for field in program._bias_t_fields)
    assert all(
        field["work_register"]
        == program._gen_regmap[(field["gen_ch"], "duration")][1]
        for field in program._bias_t_fields
    )
    tproc = TProcV1BehaviorModel(strict=True).run(
        program.prog_list,
        max_steps=1_000_000,
    )
    assert tproc.timing_conflicts == []


def test_bias_t_independent_outputs_start_together_and_stop_independently():
    sequence = FineTuneSequence(("awg_0", "awg_1"))
    sequence.add_set("hold", (0.2, -0.1), 10)
    sequence.set_bias_t_compensation(0.1)
    program = sequence.make_program(
        _independent_awg_soccfg(2),
        awg_channels=(0, 1),
        recovery_tproc_cycles=0,
    )
    tproc = TProcV1BehaviorModel(strict=True).run(
        program.prog_list,
        max_steps=1_000_000,
    )

    compensation_codes = {
        int(field["gen_ch"]): (
            int(field["negative_code"])
            if int(field["base"]) > 0
            else int(field["positive_code"])
        ) & 0xFFFFFFFF
        for field in program._bias_t_fields
    }
    starts = {}
    stops = {}
    for event in tproc.output_events:
        target = event.word & 0xFFFFFFFF
        if target == compensation_codes.get(event.tproc_ch):
            starts[event.tproc_ch] = event.cycle
        elif (
            event.tproc_ch in starts
            and target == 0
            and event.cycle > starts[event.tproc_ch]
        ):
            stops.setdefault(event.tproc_ch, event.cycle)

    assert starts[0] == starts[1]
    assert stops[0] - starts[0] == 20
    assert stops[1] - starts[1] == 10
    assert tproc.timing_conflicts == []
    assert program.summary()["bias_t_simultaneous_start"] is True
    assert program.summary()["bias_t_simultaneous_start_lead_cycles"] == 64


def test_bias_t_rejects_awgs_sharing_one_tprocessor_output():
    soccfg = _mock_soccfg(2)
    sequence = FineTuneSequence(("awg_0", "awg_1"))
    sequence.add_set("hold", (0.2, -0.1), 10)
    sequence.set_bias_t_compensation(0.1)

    with pytest.raises(ValueError, match="independent tProcessor output"):
        sequence.make_program(soccfg, awg_channels=(0, 1))


def test_bias_t_dmem_state_avoids_full_register_page_failure():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("initial", (0.0,), 16)
    for index in range(8):
        sequence.add_ramp(f"ramp_{index}", 16)
        segment_name = f"set_{index}"
        sequence.add_set(segment_name, (0.01 * (index + 1),), 16)
        sequence.add_amplitude_sweep(
            segment_name,
            "awg_0",
            0.01 * (index + 1),
            0.01 * (index + 2),
            2,
        )
    sequence.set_bias_t_compensation(0.1)

    # Generator 1 uses register page 1. Its eight swept SETs and dependent
    # RAMPs consume 24 direct target/step state registers, reproducing the
    # page-pressure case which previously left no Bias-T work register.
    program = sequence.make_program(_mock_soccfg(2), awg_channels=(1,))
    program.compile()

    direct_fields = [
        field
        for field in program._sweep_fields
        if field.get("storage") != "dmem" and field["page"] == 1
    ]
    assert len(direct_fields) == 24
    assert program._bias_t_fields[0]["page"] == 1
    assert program._bias_t_fields[0]["dmem_addr"] == 4095
    assert program._bias_t_max_duration_dmem_addr == 4094
    assert program.summary()["bias_t_dynamic_dmem_fields"] == 1
    assert any(inst["name"] == "memri" for inst in program.prog_list)
    assert any(inst["name"] == "memwi" for inst in program.prog_list)


def test_sweep_state_spills_to_dmem_after_register_page_is_full():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("initial", (0.0,), 16)
    for index in range(9):
        sequence.add_ramp(f"ramp_{index}", 16)
        segment_name = f"set_{index}"
        sequence.add_set(segment_name, (0.01 * (index + 1),), 16)
        sequence.add_amplitude_sweep(
            segment_name,
            "awg_0",
            0.01 * (index + 1),
            0.01 * (index + 2),
            2,
        )
    sequence.set_bias_t_compensation(0.1)

    program = sequence.make_program(_mock_soccfg(2), awg_channels=(1,))
    program.compile()

    register_fields = [
        field for field in program._sweep_fields
        if field.get("storage") == "register"
    ]
    dmem_fields = [
        field for field in program._sweep_fields
        if field.get("storage") == "dmem"
    ]
    assert len(register_fields) == 25
    assert len(dmem_fields) == 3
    assert len({field["dmem_addr"] for field in dmem_fields}) == 3
    assert all(field["dmem_addr"] > program.COUNTER_ADDR for field in dmem_fields)


def test_bias_t_tprocessor_selects_opposite_polarity_across_zero_area():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("hold", (0.0,), 20)
    sequence.set_amplitude_sweep("hold", "awg_0", -0.2, 0.2, 3)
    sequence.set_bias_t_compensation(0.1)
    program = sequence.make_program(_mock_soccfg(1), awg_channels=(0,))
    tproc = TProcV1BehaviorModel(strict=True).run(
        program.prog_list,
        max_steps=1_000_000,
    )

    positive = int(program._bias_t_fields[0]["positive_code"])
    negative = int(program._bias_t_fields[0]["negative_code"])
    compensation_targets = []
    for event in tproc.output_events:
        target = event.word & 0xFFFFFFFF
        target = target - (1 << 32) if target & (1 << 31) else target
        if target in {positive, negative}:
            compensation_targets.append(target)
    assert compensation_targets == [positive, negative]


def test_bias_t_fixed_point_range_supports_100us_full_scale_pulse():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("hold", (1.0,), 30_000)
    sequence.set_bias_t_compensation(0.1)
    program = sequence.make_program(_mock_soccfg(1), awg_channels=(0,))
    duration_cycles = (
        abs(int(program._bias_t_duration_q_actual[0, 0])) + (1 << 7)
    ) >> 8
    assert 299_900 <= duration_cycles <= 300_100


def test_bias_t_fixed_time_preview_adjusts_voltage_and_keeps_duration():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("hold", (0.2,), 10)
    sequence.set_bias_t_compensation(
        0.1,
        mode="fixed_time",
        fixed_duration_cycles=20,
    )

    (preview,) = sequence.bias_t_compensation_preview()
    assert preview.pulse_area == 2.0
    assert preview.duration_cycles == 20
    assert preview.target_amplitude == pytest.approx(-0.1, abs=2 / 32768)
    assert abs(preview.residual_area) <= 40 / 32768


def test_bias_t_fixed_time_sweeps_dmem_target_and_emits_constant_duration():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("hold", (0.1,), 20)
    sequence.set_amplitude_sweep("hold", "awg_0", 0.1, 0.3, 3)
    sequence.set_bias_t_compensation(
        0.1,
        mode="fixed_time",
        fixed_duration_cycles=40,
    )
    program = sequence.make_program(
        _mock_soccfg(1),
        awg_channels=(0,),
    )
    program.compile()

    expected_targets = program._bias_t_target_code_actual[:, 0].tolist()
    assert len(set(expected_targets)) == 3
    assert all(target < 0 and target & 0b11 == 0 for target in expected_targets)
    assert program.summary()["bias_t_compensation_mode"] == "fixed_time"
    assert program.summary()["bias_t_duration_execution"] == (
        "tproc_fixed_time_dynamic_voltage"
    )
    assert program.summary()["bias_t_dynamic_dmem_fields"] == 1

    tproc = TProcV1BehaviorModel(strict=True).run(
        program.prog_list,
        max_steps=1_000_000,
    )

    def signed_target(event):
        target = event.word & 0xFFFFFFFF
        return target - (1 << 32) if target & (1 << 31) else target

    starts = [
        event
        for event in tproc.output_events
        if signed_target(event) in set(expected_targets)
    ]
    assert [signed_target(event) for event in starts] == expected_targets
    for event in starts:
        following_zero = next(
            candidate
            for candidate in tproc.output_events
            if candidate.tproc_ch == event.tproc_ch
            and candidate.cycle > event.cycle
            and (candidate.word & 0xFFFFFFFF) == 0
        )
        assert following_zero.cycle - event.cycle == 40
    assert tproc.timing_conflicts == []


def test_bias_t_fixed_time_rejects_duration_that_requires_overrange_voltage():
    sequence = FineTuneSequence(("awg_0",))
    sequence.add_set("hold", (1.0,), 100)
    sequence.set_bias_t_compensation(
        0.1,
        mode="fixed_time",
        fixed_duration_cycles=1,
    )

    with pytest.raises(ValueError, match="too short"):
        sequence.make_program(_mock_soccfg(1), awg_channels=(0,))
