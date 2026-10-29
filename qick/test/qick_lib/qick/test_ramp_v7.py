"""V7 public packing, exact endpoint reach, scheduling and latency tests."""
from fractions import Fraction
import pytest
from qick.sim import QickSim
from qick.ramp_v7 import ramp_packet, edge_step
from qick.awg_tuning import AxisAwgTuningV7
from qick.asm_v1 import QickProgram
from qick.output_sum import apply_output_sum_config
from test_awg_tuning_asmv1 import make_soccfg


@pytest.mark.parametrize('first', range(16))
@pytest.mark.parametrize('fall_lane', range(16))
def test_every_lane_and_fall_carry(first, fall_lane):
    end=first+3
    fall=fall_lane if fall_lane>=end else fall_lane+16
    if fall<end:fall+=16
    packet=ramp_packet(start=-32768,target=32764,rise_start=first,rise_end=end,
                       fall_start=fall,fall_end=fall+11,end_target=-1000,tmux=7)
    w=packet['word']
    assert w.bit_length()<=160 and w>>152==7
    assert (w>>144)&3==2 and (w>>151)&1==1
    assert (w>>102)&15==first and (w>>106)&31==fall_lane
    assert ((w>>134)&1023)*16+((w>>106)&15)==fall
    assert packet['reservation_cycles']==(fall+12+15)//16
    assert sum(word<<(32*i) for i,word in enumerate(packet['words']))==w


@pytest.mark.parametrize('a,b', [(-32768,32764),(32764,-32768),(0,4),(4,0),(-100,100),(800,800)])
@pytest.mark.parametrize('intervals', [1,2,3,15,16,17,31,32,1000,8388606])
def test_fractional_rounding_reaches_without_extra_terminal_jump(a,b,intervals):
    step=edge_step(a,b,intervals)
    ideal=Fraction((b-a)*(1<<18),intervals)
    assert abs(Fraction(step)-ideal)<1
    actual=(a<<18)+step*intervals
    assert actual >= b<<18 if b>=a else actual<=b<<18
    assert -(1<<34)<=step<(1<<34)


def test_sentinel_and_one_interval_full_scale():
    p=ramp_packet(start=-32768,target=32764,rise_start=15,rise_end=16)
    assert (p['word']>>106)&31==31
    assert p['fall_step']==0 and p['terminal']==32764 and p['reservation_cycles']==2
    assert p['rise_step']>2**31-1


@pytest.mark.parametrize('bad', [dict(rise_start=16),dict(rise_end=0),dict(target=32767),
                                 dict(fall_start=2,fall_end=4,end_target=0),
                                 dict(fall_start=16384,fall_end=16400,end_target=0),
                                 dict(fall_start=5,fall_end=5,end_target=0),dict(rise_end=2**23)])
def test_unrepresentable_or_discontinuous_requests_are_rejected(bad):
    kw=dict(start=0,target=4000,rise_start=1,rise_end=3);kw.update(bad)
    with pytest.raises(ValueError):ramp_packet(**kw)


def test_native_and_combined_latency_exactly_once():
    gen=AxisAwgTuningV7(dict(type='QICK:QICK:axis_awg_tuning_v7:1.0',fullpath='awg',
        parameters=dict(RC_PRECOMP_VERSION='1',DC_AREA_VERSION='1',DC_AREA_BITS='48')))
    assert gen.cfg['set_ramp_common_latency_cycles']==11
    assert gen.cfg['output_latency_cycles']==27
    for role in ('awg','rf'):
        cfg=dict(gen.cfg) if role=='awg' else {}
        route=dict(output_sum_version=7,output_sum_role=role,post_output_latency_cycles=2,
                   output_sum_awg_delay_cycles=2)
        for _ in range(3):
            apply_output_sum_config(cfg,route)
            assert cfg['output_latency_cycles']==31


def test_same_ramp_style_and_adjacent_timestamp_reservation():
    cfg=make_soccfg(tmux_ch=1)
    cfg['gens'][0].update(type='axis_awg_tuning_v7',frac=18,step_width=32,
                         extended_ramp_version=1,ramp_guard_cycles=0,ramp_startup_latency_cycles=0)
    prog=QickProgram(cfg)
    prog.set_pulse_registers(0,style='awg_set',value=0,duration=1)
    prog.set_pulse_registers(0,style='awg_ramp',target=16000,rise_start=2,rise_end=5,
                             fall_start=14,fall_end=20,end_target=400)
    mgr=prog._gen_mgrs[0]
    assert mgr.next_pulse['length']==2 and mgr.current_value==400
    assert mgr.last_cmd>>152==1
    prog.set_pulse_registers(0,style='awg_ramp',target=0,duration=1)
    assert mgr.next_pulse['length']==1 and mgr.current_value==0


def test_old_firmware_rejects_extended_style():
    prog=QickProgram(make_soccfg())
    with pytest.raises(ValueError,match='v7'):
        prog.set_pulse_registers(0,style='awg_ramp',target=1600,rise_start=2,rise_end=5)


def test_v7_driver_is_exported_and_legacy_waveform_model_fails_closed():
    import qick.awg_tuning as awg
    from qick.sim.exceptions import UnsupportedModeError
    assert 'AxisAwgTuningV7' in awg.__all__
    gen=AxisAwgTuningV7(dict(type='QICK:QICK:axis_awg_tuning_v7:1.0',fullpath='awg',
        parameters=dict(RC_PRECOMP_VERSION='1',DC_AREA_VERSION='1',DC_AREA_BITS='48')))
    with pytest.raises(UnsupportedModeError,match='legacy AWG waveform model'):
        QickSim._model_for_gen(None, gen, 0)


def test_unaligned_legacy_seed_is_not_silently_reinterpreted():
    cfg=make_soccfg(tmux_ch=1)
    cfg['gens'][0].update(type='axis_awg_tuning_v7',frac=18,step_width=32,
                         extended_ramp_version=1,ramp_guard_cycles=0,ramp_startup_latency_cycles=0)
    prog=QickProgram(cfg)
    prog.set_pulse_registers(0,style='awg_set',value=5,duration=1)
    with pytest.raises(ValueError,match='aligned awg_set'):
        prog.set_pulse_registers(0,style='awg_ramp',target=1600,rise_start=0,rise_end=10)



def test_public_awg_ramp_wrapper_schedules_extended_then_legacy():
    cfg = make_soccfg(tmux_ch=1)
    cfg['gens'][0].update(type='axis_awg_tuning_v7', frac=18, step_width=32,
        extended_ramp_version=1, ramp_guard_cycles=0, ramp_startup_latency_cycles=0)
    prog = QickProgram(cfg)
    prog.awg_set(0, 0, 1, t=100)
    prog.awg_ramp(0, 16000, rise_start=2, rise_end=5,
                  fall_start=14, fall_end=20, end_target=400)
    manager = prog._gen_mgrs[0]
    assert manager.next_pulse['length'] == 2 and manager.current_value == 400
    assert manager.last_cmd == ramp_packet(start=0, target=16000,
        rise_start=2, rise_end=5, fall_start=14, fall_end=20,
        end_target=400, tmux=1)['word']
    assert prog.get_timestamp(gen_ch=0) == 103
    prog.awg_ramp(0, 0, 1)
    assert manager.current_value == 0 and not (manager.last_cmd >> 151) & 1
    assert prog.get_timestamp(gen_ch=0) == 104


@pytest.mark.parametrize('extra', [dict(duration=1), dict(step=1)])
def test_public_wrapper_rejects_mixed_legacy_fields_before_mutation(extra):
    cfg = make_soccfg()
    cfg['gens'][0].update(type='axis_awg_tuning_v7', frac=18, step_width=32,
        extended_ramp_version=1, ramp_guard_cycles=0, ramp_startup_latency_cycles=0)
    prog = QickProgram(cfg)
    prog.awg_set(0, 0, 1, t=100)
    before = (len(prog.prog_list), prog._gen_mgrs[0].last_cmd)
    with pytest.raises(ValueError, match='cannot also specify'):
        prog.awg_ramp(0, 400, rise_start=0, rise_end=5, **extra)
    assert (len(prog.prog_list), prog._gen_mgrs[0].last_cmd) == before


def test_public_wrapper_requires_legacy_duration():
    prog = QickProgram(make_soccfg())
    with pytest.raises(ValueError, match='requires duration'):
        prog.awg_ramp(0, 0)
