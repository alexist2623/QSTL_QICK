"""Independent voltage math checked against executed tProcessor commands."""
import json
from fractions import Fraction
from pathlib import Path

import numpy as np
from qick.sim import QickSim  # Install desktop PYNQ stubs.
from qick.awg_tuning import TProcV1BehaviorModel
from dc_waveform_core import PulseSequence, QickSweepSpec, generate_qick_program_code
from stability_diagram import StabilityDiagramConfig, StabilitySweepAxis, build_stability_hold_sequence
from test_qick_fine_tune_sweep import _independent_awg_soccfg

OUT = Path('C:/JeonghyunPark/Workspace/QSTL_QICK/analysis_results/virtual_gate_voltage_20261003')
OUT.mkdir(parents=True, exist_ok=True)
MATRIX = np.array([[1., .23], [-.17, 1.]])
SCALES = np.array([800., 400.])
CFG = _independent_awg_soccfg(2)
for gen in CFG['gens']:
    gen.update(type='axis_awg_tuning_v2', step_width=32, frac=18,
               rc_precomp_version=1, output_latency_cycles=11)


def build(kind, count, axes, dc=True):
    if kind == 'stability':
        config = StabilityDiagramConfig(
            x_axis=StabilitySweepAxis('awg_0', 5., 15., count),
            y_axis=StabilitySweepAxis('awg_1', -9., 7., count),
            repetitions_per_point=2, settle_time_us=0., trace_samples_per_point=1,
            bias_t_compensation_enabled=True,
            bias_t_compensation_type='dc_rc' if dc else 'filter',
            bias_t_compensation_mode='fixed_time',
            bias_t_compensation_duration_us=2., bias_t_filter_tau_us=300.)
        seq = build_stability_hold_sequence(config, output_names=('awg_0', 'awg_1'),
            fabric_mhz=300., full_scale_mv=800., sample_period_us=1.,
            output_full_scales_mv=SCALES, cross_capacitance=MATRIX)
    else:
        pulses = []
        for _ in range(2):
            pulse = PulseSequence()
            pulse.t = np.array([0., 1000., 1100., 3100., 3200., 4200.])
            pulse.v = np.zeros(6)
            pulse.segment_names = ['start', 'gate', 'zero']
            pulses.append(pulse)
        sweeps = [QickSweepSpec('set_1', 'awg_0', 5/800, 15/800, count)]
        if axes == 2:
            sweeps.append(QickSweepSpec('set_1', 'awg_1', -9/800, 7/800, count))
        code = generate_qick_program_code(pulses, awg_channels=(0, 1),
            full_scale_mv=800., output_full_scales_mv=tuple(map(float, SCALES)),
            cross_capacitance=MATRIX, fabric_mhz=300., tproc_mhz=300.,
            repetitions_per_sweep=2, sweeps=sweeps,
            bias_t_compensation_enabled=True,
            bias_t_compensation_type='dc_rc' if dc else 'filter',
            bias_t_compensation_mode='fixed_time',
            bias_t_compensation_duration_us=2., bias_t_filter_tau_us=300.)
        ns = {}
        exec(code, ns)
        seq = ns['build_sequence']()
        (OUT / f'{kind}_{count}_{axes}_dc{int(dc)}_export.py').write_text(code, encoding='utf-8')
    program = seq.make_program(CFG, awg_channels=(0, 1), repetitions_per_sweep=2,
                               compile_validation_mode='boundary')
    return program


def signed(word):
    word &= 0xffffffff
    return word - 2**32 if word >= 2**31 else word


def nearest_four(value):
    return (1 if value >= 0 else -1) * int(abs(value)/4 + Fraction(1, 2)) * 4


def verify(kind, count, axes, dc):
    p = build(kind, count, axes, dc)
    p.compile()
    model = TProcV1BehaviorModel(strict=True)
    p.load_runtime_dmem_into_model(model)
    model.run(p, max_steps=4_000_000)
    assert not model.timing_conflicts
    n = count**axes
    virtual = np.array([(x, y) for x in np.linspace(5., 15., count)
                        for y in (np.linspace(-9., 7., count) if axes == 2 else [0.])])
    physical = virtual @ MATRIX.T
    codes = np.rint(physical / SCALES * 8192).astype(int) * 4
    checks = [0, 0]
    for ch in range(2):
        groups = []
        for event in model.output_events:
            if event.tproc_ch != ch:
                continue
            if event.word & (1 << 149):
                assert event.word & (1 << 147)
                assert (event.word & 0xffffffff) == round(2**48 / (2 * 300 * 4800))
                groups.append([])
            else:
                groups[-1].append(event)
        assert len(groups) == 2*n + 1 and not groups[-1]
        for shot, events in enumerate(groups[:-1]):
            code = int(codes[shot//2, ch])
            if kind == 'awg':
                expected = [(1, 0, 0), (2, code, int(Fraction(code * 2**18, 479))),
                            (1, code, 0), (2, 0, int(Fraction(-code * 2**18, 479))), (1, 0, 0)]
                # Two 0.1 us ramps and a 2 us plateau, including both ramps' area.
                area = Fraction(code * (600 + 30))
            else:
                expected = [(1, code, 0)]
                # 1 us capture plus the builder's 1 us point guard.
                area = Fraction(code * 600)
            for event, (mode, target, step) in zip(events, expected):
                assert (event.word >> 144) & 3 == mode
                assert signed(event.word) == target, (kind, shot, ch, target, signed(event.word))
                if mode == 2:
                    assert signed(event.word >> 96) == step
                    assert (event.word >> 64) & 0x7fffff == 480
                checks[ch] += 1
            if dc:
                comp = nearest_four(-area / 600)
                nonzero_after = [e for e in events[len(expected):] if signed(e.word)]
                assert len(nonzero_after) == (1 if comp else 0), (shot, ch, comp, len(nonzero_after))
                if comp:
                    e = nonzero_after[0]
                    assert signed(e.word) == comp, (shot, ch, comp, signed(e.word))
                    stop = next(e2 for e2 in events if e2.cycle > e.cycle and signed(e2.word) == 0)
                    assert stop.cycle - e.cycle == 600
            if shot % 2:
                previous = groups[shot-1]
                assert [e.word for e in events] == [e.word for e in previous]
                assert [e.cycle-events[0].cycle for e in events] == [e.cycle-previous[0].cycle for e in previous]
    error = np.max(abs(codes * SCALES / 32768 - physical), axis=0)
    assert np.all(error <= SCALES/16384 + 1e-12)
    result = dict(kind=kind, count=count, axes=axes, points=n, repetitions=2, dc=dc,
        status='passed', dmem_words=len(p._runtime_dmem_words),
        command_checks=checks, commands=len(model.output_events),
        max_target_error_mv=error.tolist(), matrix=MATRIX.tolist(), full_scale_mv=SCALES.tolist(),
        timing_conflicts=0, repeat_mismatches=0, axis_rewind_mismatches=0)
    print(json.dumps(result), flush=True)
    return result


results = []
for kind, count, axes in [('awg',20,1), ('awg',200,1), ('awg',20,2), ('stability',20,2)]:
    for dc in (False, True):
        try:
            results.append(verify(kind, count, axes, dc))
        except Exception as exc:
            results.append(dict(kind=kind,count=count,axes=axes,dc=dc,status='failed',
                                error=f'{type(exc).__name__}: {exc}'))
            print(results[-1], flush=True)
for kind in ('awg', 'stability'):
    try:
        p = build(kind, 200, 2, True)
        results.append(dict(kind=kind,count=200,axes=2,status='compiled',dmem_words=len(p._runtime_dmem_words)))
    except RuntimeError as exc:
        results.append(dict(kind=kind,count=200,axes=2,status='blocked_by_dmem',error=str(exc)))
    print(results[-1], flush=True)
(OUT/'software_results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
assert all(r['status'] != 'failed' for r in results)
