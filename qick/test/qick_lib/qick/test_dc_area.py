"""Desktop command ABI, full-word precision, and exact area reference tests."""
import random
import subprocess
import sys

import pytest
from qick.dc_area import (dc_area_words, compensation_plan, floor_sum,
                          ramp_area, validate_area_bounds)


def test_desktop_helper_does_not_load_pynq():
    subprocess.run([sys.executable, '-c',
        "from qick.dc_area import dc_area_words; import sys; "
        "assert 'pynq' not in sys.modules; assert dc_area_words('arm')[4] == 0x430000"], check=True)


def test_word_layout_keeps_tmux_and_rc_bits_separate():
    for action, index in [('arm',0), ('fixed_voltage',1), ('fixed_time',2), ('disable',3)]:
        args = {'amplitude': 8192} if index == 1 else {'words':60000} if index == 2 else {}
        values=dc_area_words(action, tmux_ch=7, **args)
        packet=sum(word << (32*i) for i,word in enumerate(values))
        assert (packet >> 152) == 7
        assert (packet >> 149) & 1 == 0
        assert (packet >> 150) & 1 == 1
        assert (packet >> 144) & 15 == 3+(index << 2)
        if index == 2:
            assert values[0]+(values[1]<<32) == (1<<64)//960000
            assert values[2] == 60000


@pytest.mark.parametrize('action,kwargs', [
    ('unknown',{}), ('arm',{'amplitude':4}), ('disable',{'words':1}),
    ('fixed_voltage',{'amplitude':1}), ('fixed_voltage',{'amplitude':32768}),
    ('fixed_voltage',{'amplitude':0}), ('fixed_time',{'words':0}),
    ('fixed_time',{'words':1<<32}), ('fixed_time',{'words':True}),
])
def test_invalid_command_rejected(action,kwargs):
    with pytest.raises(ValueError): dc_area_words(action, **kwargs)


def test_exact_area_on_random_ramps_and_both_dc_modes():
    rng=random.Random(480064)
    for _ in range(1000):
        n=rng.randrange(1,400)
        start=rng.randrange(-8192,8192)*4
        target=rng.randrange(-8192,8192)*4
        slope=int((target-start)*(1<<18)/max(1,n-1))
        expected=sum((start*(1<<18)+slope*i) >> 20 for i in range(n-1))+(target >> 2)
        assert ramp_area(start,target,slope,n) == expected
        for params in ({'amplitude':2048}, {'words':400}):
            plan=compensation_plan(expected,**params)
            assert plan['residual'] == 0
            assert sum(c for c,v in plan['runs']) == plan['words']*16
            assert all(-8192 <= v <= 8191 for c,v in plan['runs'])


def test_signed_floor_sum_matches_scalar_reference():
    for n in (0,1,3,19,101):
        for slope in (-923, -1,0,1,739):
            for offset in (-982,0,871):
                assert floor_sum(n,128,slope,offset) == sum((slope*i+offset)//128 for i in range(n))


def test_clipped_ramp_sum_matches_independent_scalar_dac():
    from qick.dc_area import clipped_floor_sum
    rng=random.Random(480063)
    for _ in range(1000):
        count=rng.randrange(0,400)
        divisor=1 << rng.randrange(0,21)
        slope=rng.randrange(-16000,16001)*divisor+rng.randrange(divisor)
        start=rng.randrange(-16000,16001)*divisor+rng.randrange(divisor)
        expected=sum(min(8191,max(-8192,(start+slope*i)//divisor)) for i in range(count))
        assert clipped_floor_sum(count,divisor,slope,start)==expected


def test_48_bit_prefix_limit_not_just_net_zero():
    validate_area_bounds(-(1<<47),(1<<47)-1)
    with pytest.raises(ValueError):validate_area_bounds(0,1<<47)
    with pytest.raises(ValueError):validate_area_bounds(-(1<<47)-1,0)
    for area in (-(1<<47),(1<<47)-1):
        assert compensation_plan(area, words=0xffffffff)['residual'] == 0


def test_v3_driver_and_asm_metadata():
    from qick.sim import QickSim  # installs board stubs for driver-only test
    from qick.awg_tuning import AxisAwgTuningV3
    from qick.asm_v1 import QickProgram, AwgTuningGenManager
    dut=AxisAwgTuningV3(dict(type='QICK:QICK:axis_awg_tuning_v3:1.0', fullpath='awg',
        parameters={'N_PTS':'16','B':'16','CMD_WIDTH':'160','RC_PRECOMP_VERSION':'1',
                    'DC_AREA_BITS':'48','DC_AREA_VERSION':'1'}))
    assert dut['output_latency_cycles'] == 16
    assert dut['dc_area_bits'] == 48
    assert dut['step_width'] == 32 and dut['frac'] == 18
    assert QickProgram.gentypes['axis_awg_tuning_v3'] is AwgTuningGenManager
