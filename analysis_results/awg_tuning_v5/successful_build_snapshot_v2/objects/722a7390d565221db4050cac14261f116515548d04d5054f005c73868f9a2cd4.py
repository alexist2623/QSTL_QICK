"""Reject DC compensation that the real v1 timed-output FIFO stretches."""
from types import SimpleNamespace

import numpy as np
import pytest
from qick.sim import QickSim  # noqa: F401
from qick_fine_tune_sweep import FineTuneSequence, FineTuneAmplitudeSweepProgram
from test_incremental_virtual_grid import firmware, MATRIX, SCALES


@pytest.mark.parametrize('mode', ['fixed_voltage', 'fixed_time'])
@pytest.mark.parametrize('clocks', [1, 2, 3])
def test_single_compensation_minimum_interval(mode, clocks):
    seq = FineTuneSequence(('x',)).add_set('gate', .01, clocks)
    seq.add_set('zero', 0., 300)
    seq.set_bias_t_compensation(.01, mode=mode,
        fixed_duration_cycles=clocks if mode == 'fixed_time' else None)
    if clocks < 3:
        with pytest.raises(ValueError, match='below the 3-clock SET interval'):
            seq.make_program(firmware(), awg_channels=(0,))
    else:
        program = seq.make_program(firmware(), awg_channels=(0,))
        program.compile()


def test_original_20mv_grid_rejects_interior_short_compensation():
    seq = FineTuneSequence(('x', 'y'))
    seq.set_cross_capacitance(MATRIX)
    seq.set_voltage_scales(800., SCALES)
    seq.add_set('gate', (0., 0.), 300)
    seq.add_ramp('return', 30).add_set('zero', (0., 0.), 500)
    seq.add_amplitude_sweep('gate', 'x', 5/800, 15/800, 200)
    seq.add_amplitude_sweep('gate', 'y', -9/800, 7/800, 200)
    seq.set_bias_t_compensation(.025, mode='fixed_voltage')
    with pytest.raises(ValueError, match='sweep point 102 requires 1'):
        seq.make_program(firmware(), awg_channels=(0, 1), compile_validation_mode='boundary')


@pytest.mark.parametrize('table_axis', [None, 0, 1])
def test_affine_spacing_search_matches_exhaustive_widths(table_axis):
    # Compare the integer interval solver against every coordinate, with both
    # signs and axis orders. No per-point waveform compilation is needed.
    rng = np.random.default_rng(190)
    shape = (20, 23)
    obj = SimpleNamespace(
        sequence=SimpleNamespace(sweep_axes=[SimpleNamespace(count=n) for n in shape], output_names=('x',)),
        _check_cancel=lambda: None, tproc_mhz=300.)
    for _ in range(60):
        base = int(rng.integers(-5000, 5000))
        deltas = rng.integers(-900, 901, size=2)
        model = dict(register_name='bias_t_duration_q', output_index=0,
                     duration_frac_bits=8, base=base, axis_deltas=tuple(deltas))
        if table_axis is None:
            values = base + np.arange(shape[0])[:, None]*deltas[0] + np.arange(shape[1])[None, :]*deltas[1]
        else:
            other = 1-table_axis
            bases = rng.integers(-5000, 5000, size=shape[table_axis])
            steps = rng.integers(-900, 901, size=shape[table_axis])
            model.update(duration_axis_indices=(table_axis,), duration_table_shape=(shape[table_axis],),
                duration_table_bases=tuple(bases), duration_table_axis_deltas={other: tuple(steps)})
            values = bases[:, None] + steps[:, None]*np.arange(shape[other])[None, :]
        widths = (abs(values)+128)//256
        if np.any((widths > 0) & (widths < 3)):
            with pytest.raises(ValueError, match='below the 3-clock SET interval'):
                FineTuneAmplitudeSweepProgram._validate_bias_t_set_spacing(obj, model)
        else:
            FineTuneAmplitudeSweepProgram._validate_bias_t_set_spacing(obj, model)
