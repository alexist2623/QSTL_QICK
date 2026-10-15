"""Hardware-area planning and unchanged fixed-increment voltage sweep policy."""
import pytest
from qick.sim import QickSim  # desktop-only test stubs, before driver imports
from qick.awg_tuning import TProcV1BehaviorModel
from test_qick_fine_tune_sweep import _independent_awg_soccfg
from qick_fine_tune_sweep import FineTuneSequence
from qick_dc_area import point_plan, waveform_ledger


def config(outputs=2):
    cfg=_independent_awg_soccfg(outputs)
    for gen in cfg['gens']:
        gen.update(type='axis_awg_tuning_v3',step_width=32,frac=18,
            dc_area_version=1,dc_area_bits=48,output_latency_cycles=16,
            rc_precomp_version=1,dc_start_cycles=17)
    return cfg


def sequence(mode):
    seq=FineTuneSequence(('awg_0','awg_1'))
    seq.set_cross_capacitance(((1,.23),(-.17,1)))
    seq.add_set('start',(.03,-.02),40)
    seq.add_ramp('ramp',60)
    seq.add_set('gate',(.06,-.05),80)
    seq.add_set('zero',(0,0),40)
    seq.add_amplitude_sweep('gate','awg_0',-.08,.08,100)
    seq.set_bias_t_compensation(.25,mode=mode,
        **({'fixed_duration_cycles':200} if mode=='fixed_time' else {}))
    return seq


@pytest.mark.parametrize('mode',['fixed_voltage','fixed_time'])
def test_100_point_two_dac_uses_ip_area_no_compensation_table(mode):
    seq=sequence(mode)
    program=seq.make_program(config(),awg_channels=(0,1),repetitions_per_sweep=2,
                             compile_validation_mode='boundary')
    program.compile()
    assert program._bias_t_fields == ()
    assert program.summary()['hardware_dc_area']
    assert program.summary()['voltage_grid_policy'] == 'constant_quantized_increment'
    assert program.summary()['bias_t_duration_execution'] == 'hardware_pre_iir_area'
    for index in range(100):
        for output in range(2):
            plan=point_plan(program,index,output)
            assert plan['residual'] == 0
            low,high=program._hardware_dc_net_bounds[output]
            assert low <= plan['area'] <= high
            assert 17+plan['words']+2 < program._hardware_dc_deadline
    model=TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(model)
    model.run(program.prog_list,max_steps=2_000_000)
    assert not model.timing_conflicts
    commands=[e.word for e in model.output_events if e.word & (1<<150)]
    assert len(commands)==402  # two ARM commands, 200 compensation shots x 2 DAC
    assert sum(((word>>146)&3)==0 for word in commands)==2
    assert sum(((word>>146)&3)==(1 if mode=='fixed_voltage' else 2) for word in commands)==400


def test_tiny_compensation_avoids_legacy_three_clock_rejection():
    seq=FineTuneSequence(('awg_0',))
    seq.add_set('tiny',(4/32768,),20)
    seq.add_set('zero',(0,),20)
    seq.set_bias_t_compensation(.5)
    program=seq.make_program(config(1),awg_channels=(0,),repetitions_per_sweep=1)
    plan=point_plan(program,0,0)
    assert plan['words']==1
    assert plan['residual']==0
    assert len([r for r in plan['runs'] if r[1]])==1


def test_dc_off_disables_previous_engine_state():
    seq=FineTuneSequence(('awg_0',))
    seq.add_set('zero',(0,),40)
    program=seq.make_program(config(1),awg_channels=(0,),repetitions_per_sweep=1)
    model=TProcV1BehaviorModel(strict=True)
    model.run(program.prog_list,max_steps=10000)
    commands=[e.word for e in model.output_events if e.word & (1<<150)]
    assert len(commands)==1 and ((commands[0]>>146)&3)==3


def test_48bit_overflow_bound_rejected_before_execution():
    seq=FineTuneSequence(('awg_0',))
    seq.add_set('long',(.5,),1_200_000_000)
    seq.set_bias_t_compensation(.5)
    with pytest.raises(ValueError,match='48-bit DC area accumulator'):
        seq.make_program(config(1),awg_channels=(0,),repetitions_per_sweep=1)


@pytest.mark.parametrize('policy',['after_readout','overlap_readout'])
@pytest.mark.parametrize('mode',['fixed_voltage','fixed_time'])
@pytest.mark.parametrize('sweep',['voltage','ramp','hold','rf'])
def test_capture_preview_matches_actual_tproc_commands(policy,mode,sweep):
    from test_dc_readout_timing import fixture
    cfg,seq,ddr,rf=fixture(policy,mode=mode,sweep=sweep)
    for gen in cfg['gens'][:2]:
        gen.update(type='axis_awg_tuning_v3',dc_area_version=1,dc_area_bits=48,
                   output_latency_cycles=16,dc_start_cycles=17)
    program=seq.make_program(cfg,awg_channels=(0,1),ddr_readout=ddr,rf_pulse=rf,
        repetitions_per_sweep=2,compile_validation_mode='boundary')
    model=TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(model)
    model.run(program,max_steps=2_000_000)
    readouts=[e for e in model.output_events if e.tproc_ch==2]
    for shot,readout in enumerate(readouts):
        point=shot//2
        preview=program.fir_dc_timing_preview(point)
        limit=readouts[shot+1].cycle if shot+1<len(readouts) else float('inf')
        for output in range(2):
            events=[e for e in model.output_events if e.tproc_ch==output
                and readout.cycle <= e.cycle < limit and e.word & (1<<150)]
            assert len(events)==1
            dc=preview['dc_outputs'][output]
            assert dc['command_start_us']*300 == pytest.approx(events[0].cycle-readout.cycle)
            assert (dc['dac_start_us']-dc['command_start_us'])*300 == pytest.approx(28)
            assert dc['dac_end_us']*300+readout.cycle < limit
            plan=point_plan(program,point,output)
            low,high=program._hardware_dc_net_bounds[output]
            assert low <= plan['area'] <= high
            assert plan['residual']==0
        assert preview['input_end_barrier_us']*300+readout.cycle < limit


def test_seven_independent_awgs_initialize_with_sufficient_lookahead():
    seq=FineTuneSequence(tuple(f'awg_{i}' for i in range(7)))
    seq.add_set('start',tuple(.01 for _ in range(7)),1000)
    seq.add_set('zero',tuple(0 for _ in range(7)),1000)
    seq.set_bias_t_compensation(.1)
    program=seq.make_program(config(7),awg_channels=tuple(range(7)),repetitions_per_sweep=2)
    model=TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(model)
    model.run(program,max_steps=100000)
    assert not model.timing_conflicts
    assert model.dmem[program.COUNTER_ADDR]==2
    assert any(i['name']=='waiti' for i in program.prog_list)


def test_extra_five_awg_cycles_shift_rf_and_ddr_anchors_together():
    from test_dc_readout_timing import fixture
    programs=[]
    for v3 in (False,True):
        cfg,seq,ddr,rf=fixture('overlap_readout',sweep='rf')
        seq.bias_t_compensation=None
        if v3:
            for gen in cfg['gens'][:2]:
                gen.update(type='axis_awg_tuning_v3',dc_area_version=1,dc_area_bits=48,
                           output_latency_cycles=16,dc_start_cycles=17)
        programs.append(seq.make_program(cfg,awg_channels=(0,1),ddr_readout=ddr,rf_pulse=rf,
                                        compile_validation_mode='boundary'))
    old,new=programs
    assert new.timing['command_times']==old.timing['command_times']
    assert all(b-a==5 for a,b in zip(old.timing['segment_starts'],new.timing['segment_starts']))
    for key in ('rf_0_start','rf_0_end','ddr_trigger_time','ddr_capture_end'):
        assert new.aux_timing[key]-old.aux_timing[key]==5
    assert new._fir_cfg['trigger_delay_input_cycles']==old._fir_cfg['trigger_delay_input_cycles']==8712


def test_long_near_rail_sweep_accounts_for_actual_ramp_saturation():
    from qick_dc_area import executed_commands
    from qick.dc_area import clipped_floor_sum
    import numpy as np
    seq=FineTuneSequence(('awg_0',)).add_set('start',-.01,40)
    seq.add_ramp('ramp',500000).add_set('end',.9998,40).add_set('zero',0.,40)
    seq.add_amplitude_sweep('start','awg_0',-.01,.01,100)
    seq.set_bias_t_compensation(.25)
    p=seq.make_program(config(1),awg_channels=(0,),compile_validation_mode='boundary')
    for index in range(100):
        plan=point_plan(p,index,0)
        low,high=p._hardware_dc_net_bounds[0]
        assert low<=plan['area']<=high
        assert plan['residual']==0
    # Last-point raw ramp really crosses the rail, although SET targets remain
    # legal. Compare the analytic accumulator to an independent sample loop.
    commands=list(executed_commands(p,99))
    start=commands[0].target_code*(1<<18)
    ramp=next(c for c in commands if c.kind=='ramp')
    n=ramp.duration_samples-1
    total=0
    for begin in range(0,n,65536):
        samples=(start+ramp.step*np.arange(begin,min(n,begin+65536),dtype=np.int64))//(1<<20)
        total+=int(np.clip(samples,-8192,8191).sum())
    assert (start+ramp.step*(n-1))//(1<<20)>8191
    assert clipped_floor_sum(n,1<<20,ramp.step,start)==total
    assert point_plan(p,99,0)['clip_upper_bound']>0
