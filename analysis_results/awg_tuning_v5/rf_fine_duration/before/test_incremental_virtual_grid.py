"""Large coupled grids keep hardware increments, never Cartesian DAC tables."""
from fractions import Fraction
import numpy as np
import pytest
from qick.sim import QickSim  # noqa: F401
from qick_fine_tune_sweep import FineTuneSequence, RfPulseConfig
from test_qick_fine_tune_sweep import _independent_awg_soccfg, _shared_tmux_soccfg
from stability_diagram import StabilityDiagramConfig, StabilitySweepAxis, build_stability_hold_sequence


MATRIX = np.array(((1., .23), (-.17, 1.)))
SCALES = (800., 400.)


def round_increment(value):
    value = Fraction(value)
    return (1 if value >= 0 else -1)*int(abs(value)+Fraction(1,2))


def firmware():
    cfg = _independent_awg_soccfg(2)
    for gen in cfg['gens']:
        gen.update(type='axis_awg_tuning_v2', step_width=32, frac=18,
                   rc_precomp_version=1, output_latency_cycles=11)
    return cfg


def test_increment_drift_cannot_wrap_the_dac_with_rc_disabled():
    seq = FineTuneSequence(('x','y')).add_set('gate',(0.,0.),300)
    seq.add_amplitude_sweep('gate','x',.01,.9999,200)
    with pytest.raises(ValueError,match='incremental voltage sweep exceeds DAC range'):
        seq.make_program(firmware(),awg_channels=(0,1),compile_validation_mode='boundary')


def test_fixed_time_compensation_increment_cannot_wrap_the_dac():
    seq = FineTuneSequence(('x','y')).add_set('gate',(-8000/32768,0.),300)
    seq.add_amplitude_sweep('gate','x',-8000/32768,-8796/32768,200)
    seq.set_bias_t_compensation(mode='fixed_time',fixed_duration_cycles=81)
    with pytest.raises(ValueError,match='incremental Bias-T compensation exceeds range'):
        seq.make_program(firmware(),awg_channels=(0,1),compile_validation_mode='boundary')


@pytest.mark.parametrize('source', ['awg', 'stability'])
@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('swap', [False, True])
@pytest.mark.parametrize('dc', [None, 'fixed_time', 'fixed_voltage'])
@pytest.mark.parametrize('rc', [False, True])
def test_200x200_virtual_grid(source, reverse, swap, dc, rc):
    limits = [(5.,15.),(-9.,7.)]
    if reverse: limits = [pair[::-1] for pair in limits]
    if source == 'stability':
        config = StabilityDiagramConfig(
            x_axis=StabilitySweepAxis('x',*limits[0],200),
            y_axis=StabilitySweepAxis('y',*limits[1],200),
            settle_time_us=0., trace_samples_per_point=1,
            bias_t_compensation_enabled=dc is not None,
            bias_t_compensation_type='dc',
            bias_t_compensation_mode=dc or 'fixed_time',
            bias_t_compensation_duration_us=2.,bias_t_compensation_voltage_mv=.1)
        seq = build_stability_hold_sequence(config, output_names=('x','y'),
            fabric_mhz=300., full_scale_mv=800., sample_period_us=1.,
            cross_capacitance=MATRIX, output_full_scales_mv=SCALES)
    else:
        seq = FineTuneSequence(('x','y'))
        seq.set_cross_capacitance(MATRIX)
        seq.set_voltage_scales(800., SCALES)
        seq.add_set('gate',(0.,0.),300)
        seq.add_ramp('return',30).add_set('zero',(0.,0.),500)
        for name, (lo,hi) in zip(('x','y'),limits):
            seq.add_amplitude_sweep('gate',name,lo/800,hi/800,200)
        if dc:
            # Keep even near-zero-area compensation above the SET interval.
            # The original 20 mV unsupported case is covered separately.
            seq.set_bias_t_compensation(.1/800,mode=dc,
                fixed_duration_cycles=600 if dc=='fixed_time' else None)
    if rc: seq.set_rc_compensation(300.)
    if swap: seq.sweeps.reverse()
    program = seq.make_program(firmware(),awg_channels=(0,1),
        repetitions_per_sweep=2,compile_validation_mode='boundary')
    program.compile()
    assert not program._runtime_dmem_words
    assert len(program._compile_validation_point_indices)==4
    assert program.summary()['tproc_memory_within_4096']
    assert program.summary()['voltage_grid_policy']=='constant_quantized_increment'
    x,y = [np.linspace(*pair,200) for pair in limits]
    for output,scale in enumerate(SCALES):
        requested = MATRIX[output,0]*x[:,None]+MATRIX[output,1]*y[None,:]
        if swap: requested = requested.T
        nearest = np.rint(requested*32768/scale/4).astype(int)*4
        base = nearest[0,0]
        deltas = [round_increment(Fraction(int(end-base),199*4))*4
                  for end in (nearest[-1,0],nearest[0,-1])]
        expected = base+np.arange(200)[:,None]*deltas[0]+np.arange(200)[None,:]*deltas[1]
        field = program._sweep_models[(0,output,0,'target')]
        assert field['base']==base and tuple(field['axis_deltas'])==tuple(deltas)
        # Check all 40,000 modeled coordinates; instruction/RTL execution is
        # separately exercised by the production testbench.
        actual = np.array([program._sweep_model_value(field,p) for p in range(40000)]).reshape(200,200)
        np.testing.assert_array_equal(actual,expected)
        assert np.max(abs(actual-nearest)) <= 2*199*2+4
        if dc:
            comp = program._bias_t_fields[output]
            assert 'duration_table_bases' not in comp
    assert all(not m.get('exact_voltage_table') for m in program._sweep_models.values())


@pytest.mark.parametrize('extension', ['fixed','extend_by_rf_duration'])
@pytest.mark.parametrize('dc', ['fixed_time','fixed_voltage'])
@pytest.mark.parametrize('reverse', [False,True])
@pytest.mark.parametrize('swap', [False,True])
def test_200x200_rf_duration_with_coupled_voltage(extension, dc, reverse, swap):
    cfg = _shared_tmux_soccfg()
    cfg['gens'][1].update(type='axis_awg_tuning_v2',step_width=32,frac=18,
                         rc_precomp_version=1,output_latency_cycles=11)
    other = dict(cfg['gens'][1],tproc_ch=1,dac='11')
    cfg['gens'].append(other)
    seq = FineTuneSequence(('x','y'))
    seq.set_cross_capacitance(MATRIX)
    seq.set_voltage_scales(800.,SCALES)
    seq.add_set('gate',(0.,.003),600)
    seq.add_ramp('back',60).add_set('zero',(0.,0.),300)
    volts=(5/800,15/800); times=(.1,.4)
    if reverse: volts=volts[::-1]; times=times[::-1]
    seq.add_amplitude_sweep('gate','x',*volts,200)
    seq.add_rf_duration_sweep('gate',0,*times,200,
        segment_length_mode=extension,sequence_fabric_mhz=300.)
    if swap: seq.sweeps.reverse()
    seq.set_bias_t_compensation(.025,mode=dc,
        fixed_duration_cycles=600 if dc=='fixed_time' else None)
    seq.set_rc_compensation(300.)
    rf=RfPulseConfig(0,'gate',30,1000,freq_mhz=190.)
    p=seq.make_program(cfg,awg_channels=(1,2),rf_pulse=rf,compile_validation_mode='boundary')
    p.compile()
    assert p.summary()['tproc_memory_within_4096']
    assert len(p._runtime_dmem_words)<=200*7  # RF length + two base/delta/rewind DC columns.
    assert not any(m.get('exact_voltage_table') for m in p._sweep_fields)
    if extension=='extend_by_rf_duration':
        assert all(len(f['duration_table_bases'])==200 for f in p._bias_t_fields)
    assert p._sweep_max_duration_error==0
