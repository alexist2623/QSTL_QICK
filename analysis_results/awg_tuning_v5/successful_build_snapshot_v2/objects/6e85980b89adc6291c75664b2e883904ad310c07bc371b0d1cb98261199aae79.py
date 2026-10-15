"""Exercise RC preflight with real hardware loops and mixed RF/AWG sweeps."""
from dataclasses import replace

import numpy as np
import pytest
from qick.sim import QickSim  # noqa: F401
from qick.awg_tuning import TProcV1BehaviorModel
from qick_fine_tune_sweep import FineTuneSequence, RfPulseConfig
from qick_rc_validation import sweep_corners, validate_sequence_rc_range
from test_qick_fine_tune_sweep import _shared_tmux_soccfg


KINDS = ('amplitude', 'ramp_rate', 'hold_duration', 'rf_duration_fixed',
         'rf_duration_extend', 'rf_frequency_power', 'combined')


def make_case(kind, dc_mode='fixed_voltage', descending=False):
    cfg = _shared_tmux_soccfg()
    cfg['gens'][1].update(rc_precomp_version=1, output_latency_cycles=11)
    seq = FineTuneSequence(('awg_0',)).add_set('start', -.02, 300)
    seq.add_ramp('ramp', 60).add_set('gate', .03, 600)
    seq.add_ramp('back', 60).add_set('end', 0., 300)
    counts = (3, 4)
    lo, hi = (.1, .3) if not descending else (.3, .1)
    if kind in ('ramp_rate', 'combined'):
        seq.add_ramp_duration_sweep('ramp', start_us=lo, stop_us=hi,
                                    count=counts[0], sequence_fabric_mhz=300.)
    if kind in ('hold_duration', 'combined'):
        seq.add_hold_duration_sweep('start', start_us=lo+1, stop_us=hi+1,
                                    count=counts[0], sequence_fabric_mhz=300.)
    if kind != 'rf_frequency_power':
        seq.add_amplitude_sweep('gate', 'awg_0', .01, .04, counts[1])
    rf = RfPulseConfig(0, 'gate', 120, 1000, freq_mhz=190., phase_degrees=30.)
    if kind in ('rf_duration_fixed', 'rf_duration_extend', 'combined'):
        seq.add_rf_duration_sweep('gate', 0, lo+.3, hi+.3, counts[0],
            segment_length_mode='fixed' if kind == 'rf_duration_fixed' else 'extend_by_rf_duration',
            sequence_fabric_mhz=300.)
    if kind in ('rf_frequency_power', 'combined'):
        seq.add_rf_frequency_sweep('gate', 0, 180., 200., counts[0])
        seq.add_rf_power_sweep('gate', 0, -30., -20., 2)
        rf = replace(rf, sweep_gain_codes=(1000, 2000, 1100, 2100, 1200, 2200),
                     sweep_gain_shape=(3, 2), power_calibration_run_id=77)
    seq.set_rc_compensation(10.)
    if dc_mode is not None:
        # Small areas need a lower voltage to last >= 3 tProcessor clocks.
        seq.set_bias_t_compensation(.01, mode=dc_mode,
                                   fixed_duration_cycles=600 if dc_mode == 'fixed_time' else None)
    return cfg, seq, rf


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('dc_mode', [None, 'fixed_time', 'fixed_voltage'])
def test_mixed_sweeps_preserve_commands_timing_and_resets(kind, dc_mode, monkeypatch):
    cfg, seq, rf = make_case(kind, dc_mode)
    preview = validate_sequence_rc_range(seq, 300., 800.)
    assert {r['point_index'] for r in preview} == set(sweep_corners(seq))
    programs, traces = {}, {}
    for mode in ('full', 'boundary'):
        prog = seq.make_program(cfg, awg_channels=(1,), rf_pulse=rf,
            repetitions_per_sweep=2, compile_validation_mode=mode)
        prog.compile()
        model = TProcV1BehaviorModel(strict=True)
        prog.load_runtime_dmem_into_model(model)
        model.run(prog, max_steps=10_000_000)
        assert not model.timing_conflicts
        assert {r['point_index'] for r in prog.rc_output_range_validation} == set(sweep_corners(seq))
        programs[mode] = prog
        traces[mode] = [(e.cycle, e.tproc_ch, e.word) for e in model.output_events]
    assert traces['full'] == traces['boundary']
    assert programs['full']._runtime_dmem_words == programs['boundary']._runtime_dmem_words

    # The new range check is observational: it must not rewrite PMEM or DMEM.
    import qick_rc_validation
    monkeypatch.setattr(qick_rc_validation, 'validate_program_rc_range', lambda program: ())
    unchecked = seq.make_program(cfg, awg_channels=(1,), rf_pulse=rf,
        repetitions_per_sweep=2, compile_validation_mode='boundary')
    unchecked.compile()
    assert unchecked.binprog == programs['boundary'].binprog
    assert unchecked._runtime_dmem_words == programs['boundary']._runtime_dmem_words

    awg = [(time, word) for time, _, word in traces['full'] if (word >> 152) & 255 == 1]
    resets = [i for i, (_, word) in enumerate(awg) if word & (1 << 149)]
    assert len(resets) == 1 + seq.sweep_point_count * 2
    rf_events = [(time, word) for time, _, word in traces['full'] if (word >> 152) & 255 == 0]
    starts = [(time, word) for time, word in rf_events if (word >> 96) & 0xffffffff]
    assert len(starts) == seq.sweep_point_count * 2
    for shot in range(seq.sweep_point_count * 2):
        point_index = shot // 2
        commands = [c for segment in programs['full'].compiled_points[point_index].segment_commands for c in segment]
        events = awg[resets[shot]+1:resets[shot+1]]
        assert [word for _, word in events[:len(commands)]] == [
            sum(int(w) << (32*i) for i, w in enumerate(c.words)) for c in commands]
        assert events[-1][1] & 0xffffffff == 0
        if dc_mode == 'fixed_time':
            assert programs['full']._bias_t_max_target_code_error <= 8
            code = int(programs['full']._bias_t_target_code_actual[point_index, 0])
            if code:
                assert events[-2][1] & 0xffffffff == code & 0xffffffff
                assert events[-1][0] - events[-2][0] == 600
        elif dc_mode == 'fixed_voltage':
            assert programs['full']._bias_t_max_duration_q_error <= 2
            q = int(programs['full']._bias_t_duration_q_actual[point_index, 0])
            if abs(q) >= 128:
                assert events[-1][0] - events[-2][0] == (abs(q) + 128) >> 8
        # The nominal pulse must reach zero at its swept total duration.
        duration = sum(seq.segment_duration_cycles_at(point_index, i) for i in range(len(seq.segments)))
        guard = sum(int(cfg['gens'][1]['ramp_guard_cycles']) for s in seq.segments if s.kind == 'ramp')
        assert events[len(commands)][0] - events[0][0] == duration + guard
        rf_start, word = starts[shot]
        assert rf_start - events[2][0] == 11  # RC output pipeline alignment.
        coordinates = seq.sweep_coordinate(point_index)
        values = {type(axis).__name__: value for axis, value in zip(seq.sweep_axes, coordinates)}
        if 'RfFrequencySweep' in values:
            assert word & 0xffffffff == programs['full']._rf_frequency_word(rf, values['RfFrequencySweep'])
            fi = round((values['RfFrequencySweep'] - 180) / 10)
            pi = round((values['RfPowerSweep'] + 30) / 10)
            assert (word >> 96) & 0xffffffff == rf.sweep_gain_codes[fi*2+pi]
        else:
            assert (word >> 96) & 0xffffffff == 1000
        if 'RfDurationSweep' in values:
            assert (word >> 146) & 1 == 0
            assert (word >> 128) & 0xffff == round(values['RfDurationSweep']*300)


@pytest.mark.parametrize('kind', ['ramp_rate', 'hold_duration', 'rf_duration_extend'])
def test_descending_duration_axes(kind):
    cfg, seq, rf = make_case(kind, descending=True)
    prog = seq.make_program(cfg, awg_channels=(1,), rf_pulse=rf, compile_validation_mode='boundary')
    model = TProcV1BehaviorModel(strict=True)
    prog.load_runtime_dmem_into_model(model); model.run(prog)
    assert not model.timing_conflicts
    assert len(prog.rc_output_range_validation) == 4


@pytest.mark.parametrize('kind', ['ramp_rate', 'hold_duration', 'rf_duration_extend'])
def test_long_duration_endpoint_rejects_rc_overflow(kind):
    cfg, _, _ = make_case(kind)
    seq = FineTuneSequence(('awg_0',)).add_set('gate', .4, 300)
    rf = None
    if kind == 'ramp_rate':
        seq.add_ramp('ramp', 300).add_set('end', .4, 300)
        seq.add_ramp_duration_sweep('ramp', start_us=1, stop_us=40.8, count=200, sequence_fabric_mhz=300.)
    elif kind == 'hold_duration':
        seq.add_hold_duration_sweep('gate', start_us=1, stop_us=40.8, count=200, sequence_fabric_mhz=300.)
    else:
        seq.add_rf_duration_sweep('gate', 0, 1, 40.8, 200,
            segment_length_mode='extend_by_rf_duration', sequence_fabric_mhz=300.)
        rf = RfPulseConfig(0, 'gate', 300, 1000, freq_mhz=190.)
    seq.set_rc_compensation(10.)
    with pytest.raises(ValueError, match='sweep corner 199'):
        validate_sequence_rc_range(seq, 300., 800.)
    with pytest.raises(ValueError, match='RC-compensated DAC output exceeds range'):
        seq.make_program(cfg, awg_channels=(1,), rf_pulse=rf, compile_validation_mode='boundary')


@pytest.mark.parametrize('rf_outer', [False, True])
@pytest.mark.parametrize('dc_mode', ['fixed_time', 'fixed_voltage'])
def test_rf_extension_voltage_cross_term_both_axis_orders(rf_outer, dc_mode):
    cfg, seq, rf = make_case('rf_duration_extend', dc_mode)
    if rf_outer:
        seq.sweeps.reverse()
        seq._sweep_coordinate_cache = None
    prog = seq.make_program(cfg, awg_channels=(1,), rf_pulse=rf, compile_validation_mode='boundary')
    assert prog._bias_t_max_target_code_error <= 4
    assert prog._bias_t_max_duration_q_error <= 2
    assert prog._runtime_dmem_words
    model = TProcV1BehaviorModel(strict=True)
    prog.load_runtime_dmem_into_model(model); model.run(prog)
    assert not model.timing_conflicts


def test_200_by_200_rf_extension_uses_coefficient_rows_not_point_table():
    cfg, seq, rf = make_case('rf_duration_extend', 'fixed_voltage')
    seq.sweeps.clear()
    seq.add_amplitude_sweep('gate', 'awg_0', .001, .003, 200)
    seq.add_rf_duration_sweep('gate', 0, .4, 40.2, 200,
        segment_length_mode='extend_by_rf_duration', sequence_fabric_mhz=300.)
    seq.set_rc_compensation(300.)
    seq.set_bias_t_compensation(.1/800, mode='fixed_voltage')
    prog = seq.make_program(cfg, awg_channels=(1,), rf_pulse=rf, compile_validation_mode='boundary')
    assert len(prog.rc_output_range_validation) == 4
    assert len(prog._compile_validation_point_indices) == 400
    # Three DC coefficient columns plus one RF mode/length column per axis
    # coordinate. This remains O(200), not a 200 x 200 Cartesian table.
    assert len(prog._runtime_dmem_words) == 800
    assert len(prog.binprog) < 1000


def test_two_dac_hold_sweep_spills_state_for_dc_table_pointer():
    from copy import deepcopy
    from dc_waveform_core import (PulseSequence, QickSweepSpec,
        QickHoldDurationSweepSpec, QickRfPulseSpec, generate_qick_program_code)
    cfg = _shared_tmux_soccfg()
    # Match the production register pressure: each tProc port owns RF + AWG.
    pair = deepcopy(cfg['gens'])
    for port in range(1, 4):
        for gen in pair:
            extra = dict(gen, tproc_ch=port, dac=f'{port}{gen["tmux_ch"]}')
            cfg['gens'].append(extra)
    for gen in cfg['gens']:
        if gen['type'] == 'axis_awg_tuning_v1':
            gen.update(rc_precomp_version=1, output_latency_cycles=11)
    cfg['tprocs'][0]['output_pins'] = [('output', 7, 0, 'marker')]
    pulses = []
    for scale in (1., -.5):
        pulse = PulseSequence()
        pulse.t = np.array([0, 1000, 1200, 2200, 2400, 3400], dtype=float)
        pulse.v = np.array([10, 10, -10, -10, 0, 0], dtype=float)*scale
        pulse.segment_names = ['positive', 'negative', 'zero']
        pulses.append(pulse)
    source = generate_qick_program_code(pulses, awg_channels=(1, 3),
        full_scale_mv=800., fabric_mhz=300., tproc_mhz=300., repetitions_per_sweep=2,
        sweeps=[QickHoldDurationSweepSpec('set_0', 1., 1.9, 3),
                QickSweepSpec('set_0', 'awg_0', 5/800, 15/800, 3)],
        bias_t_compensation_enabled=True, bias_t_compensation_type='dc_rc',
        bias_t_compensation_mode='fixed_time', bias_t_compensation_duration_us=1.,
        bias_t_filter_tau_us=10.,
        rf_pulse_specs=[QickRfPulseSpec(0, 'set_0', 0., .1, 190., 2000, 0., 0.)],
        output_trigger_settings=dict(enabled=True, pin=0, scope='loop', edge='both', width_us=.1))
    namespace = {}
    exec(source, namespace)
    prog = namespace['build_program'](cfg)
    model = TProcV1BehaviorModel(strict=True)
    prog.load_runtime_dmem_into_model(model)
    model.run(prog)
    assert not model.timing_conflicts
    assert len(prog.rc_output_range_validation) == 8
    assert sum(bool(e.word & (1 << 149)) for e in model.output_events) == 38
