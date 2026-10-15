"""RC headroom regressions for GUI preflight and executed sweep endpoints."""
from dataclasses import replace

import numpy as np
import pytest
from qick.sim import QickSim  # noqa: F401
from qick_fine_tune_sweep import FineTuneSequence
from qick_rc_validation import interval_extrema, validate_sequence_rc_range, sweep_corners
from test_qick_fine_tune_sweep import _independent_awg_soccfg
from test_rc_precompensation import upgraded


def three_levels(last=600, factor=1):
    seq = FineTuneSequence(('x',))
    for name, voltage, duration in [('a', 300, 100), ('b', 100, 10), ('c', last, 400)]:
        seq.add_set(name, voltage * factor / 800, duration * 300)
    seq.set_rc_compensation(300)
    seq.set_bias_t_compensation(.1)
    seq.output_full_scale_mv = 800.
    return seq


@pytest.mark.parametrize('factor', [1, -1])
def test_positive_and_negative_rc_overflow_rejected(factor):
    seq = three_levels(factor=factor)
    with pytest.raises(ValueError, match='RC-compensated DAC output exceeds range'):
        validate_sequence_rc_range(seq, 300, 800)
    with pytest.raises(ValueError, match='RC-compensated DAC output exceeds range'):
        seq.make_program(upgraded(_independent_awg_soccfg(1)), awg_channels=(0,))


@pytest.mark.parametrize('mode', ['full', 'boundary'])
def test_safe_low_voltage_dc_and_rc_compile(mode):
    seq = three_levels(last=200, factor=.1)
    preview = validate_sequence_rc_range(seq, 300, 800)[0]
    assert preview['maximum_mv'] == pytest.approx(57.)
    assert preview['minimum_mv'] == pytest.approx(-79.98046875, abs=.02)
    prog = seq.make_program(upgraded(_independent_awg_soccfg(1)), awg_channels=(0,),
                            compile_validation_mode=mode)
    result = prog.summary()['rc_output_range_validation'][0]
    # Independently measured production RTL bounds, including quantization.
    assert result['maximum_normalized'] * 800 >= 57.03125
    assert result['minimum_normalized'] * 800 <= -79.98046875
    assert result['maximum_normalized'] * 800 < 57.2


def test_ramp_interior_peak_is_checked():
    assert interval_extrema([(.6, -.6, 100., 0.)], .1)[1] == pytest.approx(1.56)
    seq = FineTuneSequence(('x',)).add_set('a', .6, 300)
    seq.add_ramp('ramp', 30000).add_set('b', -.6, 300)
    seq.set_rc_compensation(10)
    with pytest.raises(ValueError, match='RC-compensated DAC'):
        validate_sequence_rc_range(seq, 300, 800)
    with pytest.raises(ValueError, match='RC-compensated DAC'):
        seq.make_program(upgraded(_independent_awg_soccfg(1)), awg_channels=(0,))


def test_zero_input_hold_includes_integrator_offset():
    low, high = interval_extrema([(-.5, -.5, 10., 0.), (0., 0., 20., 0.)], .1)
    assert (low, high) == pytest.approx((-1., 0.))


def test_200_by_200_checks_only_four_corners(monkeypatch):
    seq = FineTuneSequence(('x', 'y')).add_set('a', (0., 0.), 300)
    seq.add_amplitude_sweep('a', 'x', -.1, .1, 200)
    seq.add_amplitude_sweep('a', 'y', -.1, .1, 200)
    seq.set_rc_compensation(300)
    corners = (0, 199, 39800, 39999)
    assert sweep_corners(seq) == corners
    called = []
    original = seq.compensated_waveform_vertices
    def check(point):
        assert point in corners
        called.append(point)
        return original(point)
    monkeypatch.setattr(seq, 'compensated_waveform_vertices', check)
    assert len(validate_sequence_rc_range(seq, 300, 800)) == 8
    assert tuple(called) == corners
    prog = seq.make_program(upgraded(_independent_awg_soccfg(2)), awg_channels=(0, 1),
                            compile_validation_mode='boundary')
    assert {r['point_index'] for r in prog.rc_output_range_validation} == set(corners)
    assert len(prog.rc_output_range_validation) == 8


def test_hardware_rounded_sweep_stop_rechecked():
    seq = FineTuneSequence(('x',)).add_set('a', .79, 600)
    # The user-required fixed integer increment is retained. The ideal corner
    # fits, but 199 rounded increments move the executed endpoint past the rail.
    seq.add_amplitude_sweep('a', 'x', .79, .831, 200)
    seq.set_rc_compensation(10)
    validate_sequence_rc_range(seq, 300, 800)  # Ideal maximum = .9972 FS.
    with pytest.raises(ValueError, match='sweep corner 199'):
        seq.make_program(upgraded(_independent_awg_soccfg(1)), awg_channels=(0,),
                         compile_validation_mode='boundary')

    # A smaller remaining margin still fails the compiler's quantization check,
    # even though the ideal preview is just inside full scale.
    seq = FineTuneSequence(('x',)).add_set('a', .79, 600)
    seq.add_amplitude_sweep('a', 'x', .79, .8333, 200)
    seq.set_rc_compensation(10)
    validate_sequence_rc_range(seq, 300, 800)
    with pytest.raises(ValueError, match='sweep corner 199'):
        seq.make_program(upgraded(_independent_awg_soccfg(1)), awg_channels=(0,),
                         compile_validation_mode='boundary')


@pytest.mark.parametrize('dc_mode', ['fixed_voltage', 'fixed_time'])
def test_dc_fields_are_included(dc_mode):
    seq = FineTuneSequence(('x',)).add_set('a', .04, 3000)
    seq.set_rc_compensation(300)
    seq.set_bias_t_compensation(.1, mode=dc_mode,
                               fixed_duration_cycles=1200 if dc_mode == 'fixed_time' else None)
    prog = seq.make_program(upgraded(_independent_awg_soccfg(1)), awg_channels=(0,))
    assert prog.rc_output_range_validation[0]['minimum_normalized'] < -.099


def test_gui_and_stability_use_same_preflight():
    from dc_waveform_core import PulseSequence, build_qick_sequence, generate_qick_program_code
    pulses = (PulseSequence(initial_voltage=600, initial_duration_ns=400000),)
    kwargs = dict(bias_t_compensation_enabled=True, bias_t_compensation_type='filter',
                  bias_t_filter_tau_us=300.)
    with pytest.raises(ValueError, match='RC-compensated DAC'):
        build_qick_sequence(pulses, **kwargs)
    ns = {}
    exec(generate_qick_program_code(pulses, **kwargs), ns)
    with pytest.raises(ValueError, match='RC-compensated DAC'):
        ns['build_sequence']()
    from test_stability_diagram import _config
    from stability_diagram import build_stability_hold_sequence
    config = replace(_config(), settle_time_us=3000., bias_t_compensation_enabled=True,
                     bias_t_compensation_type='filter', bias_t_filter_tau_us=10.)
    with pytest.raises(ValueError, match='RC-compensated DAC'):
        build_stability_hold_sequence(config, output_names=('awg_0', 'awg_1'),
                                      fabric_mhz=300, full_scale_mv=800)


def test_legacy_without_rc_unaffected():
    seq = three_levels()
    seq.set_rc_compensation(300, enabled=False)
    assert validate_sequence_rc_range(seq, 300, 800) == ()
    prog = seq.make_program(_independent_awg_soccfg(1), awg_channels=(0,))
    assert prog.rc_output_range_validation == ()
