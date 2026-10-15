"""Read-only bounded review of the frozen sample-width compiler; no board."""
from dataclasses import replace
from pathlib import Path
import hashlib
import json

import qick.sim
from qick.awg_tuning import TProcV1BehaviorModel
from qick_fine_tune_sweep import FineTuneSequence, RfPulseConfig
from qick_rf_fine_duration import samples_from_us
import qick_qcodes_experiment as runtime
from test_qick_fine_tune_sweep import _shared_tmux_soccfg
from test_rf_fine_duration_compiler import execute, active_samples
from test_rf_delay_software_sweep import custom_spec


def main():
    results = []
    program, events = execute(97, 1, 1, reps=3)
    assert sum(row[1] for row in active_samples(program, events)) == 97*3
    assert not any(table.get('fine_row') for table in program._rf_point_tables)
    results.append(dict(case='count_one_uses_start_coordinate', passed=True, samples=97, repetitions=3))

    program, events = execute(112, 81, 32, reps=3, outer=2)
    assert sum(row[1] for row in active_samples(program, events)) == sum(range(81,113))*6
    assert len(program.envelopes[0]['envs']) == 16
    assert len(program._runtime_dmem_words) == 32*6
    results.append(dict(case='descending_cross_boundary_repetition_outer_reset', passed=True,
                        points=32, repetitions=3, outer_points=2, envelope_patterns=16, dmem_words=192))

    cfg = _shared_tmux_soccfg()
    seq = FineTuneSequence(('awg_0',)).add_set('hold', .01, 2000)
    pulses = (
        RfPulseConfig(0,'hold',5,5000,freq_mhz=20.,delay_tproc_cycles=30,event_id='coarse_a'),
        RfPulseConfig(0,'hold',7,1000,delay_tproc_cycles=100,event_id='fine_b',fine_duration=True,duration_samples=97),
        RfPulseConfig(0,'hold',8,2000,phase_degrees=90.,delay_tproc_cycles=200,event_id='coarse_c'),
        RfPulseConfig(0,'hold',6,1000,delay_tproc_cycles=300,event_id='fine_d',fine_duration=True,duration_samples=81),
    )
    program = seq.make_program(cfg, awg_channels=(1,), rf_pulses=pulses, repetitions_per_sweep=2)
    program.compile()
    model=TProcV1BehaviorModel(strict=True);program.load_runtime_dmem_into_model(model);model.run(program)
    rf_events=[event for event in model.output_events if (event.word>>152)&255==0]
    assert len(rf_events)==10 and not model.timing_conflicts
    assert [((event.word>>144)&3) for event in rf_events]==[1,1,0,1,0]*2
    assert [(event.word>>96)&65535 for event in rf_events]==[5000,1000,2000,2000,2000]*2
    assert len(program.envelopes[0]['envs'])==16
    details=program.summary()['rf_fine_duration']
    assert [row['duration_samples'] for row in details]==[(97,),(81,)]
    assert [row['actual_duration_us'] for row in details]==[(97/4800.,),(81/4800.,)]
    results.append(dict(case='mixed_coarse_fine_same_generator',passed=True,commands=10,
                        envelope_patterns=16,actual_samples=[97,81]))

    for resource in ('envelope','dmem'):
        cfg=_shared_tmux_soccfg()
        seq=FineTuneSequence(('awg_0',)).add_set('hold',.01,2000)
        if resource=='envelope':
            cfg['gens'][0]['maxlen']=2047
        else:
            cfg['tprocs'][0]['dmem_size']=32
            seq.add_rf_duration_sweep('hold',0,81/4800.,112/4800.,4,sequence_fabric_mhz=300.)
        try:
            seq.make_program(cfg,awg_channels=(1,),rf_pulse=replace(pulses[1],event_id='capacity'))
        except (RuntimeError,ValueError) as error:
            assert ('envelope memory' if resource=='envelope' else 'DMEM') in str(error)
            results.append(dict(case=resource+'_capacity_rejected',passed=True,error=str(error)))
        else:
            raise AssertionError(resource+' overrun accepted')

    spec=custom_spec(fine_duration=True)
    spec=replace(spec,composite_items=tuple(replace(item,gain=1000) if item.kind=='pulse' else item
                                            for item in spec.composite_items))
    bindings=runtime._rf_software_sweep_bindings((spec,))
    counts=[]
    for coordinate in runtime._software_sweep_coordinates(bindings):
        concrete,=runtime._rf_specs_at_software_coordinate((spec,),bindings,coordinate)
        pulses=runtime.build_runtime_rf_pulses(_shared_tmux_soccfg(),(concrete,))
        assert all(p.fine_duration and p.duration_samples==960 for p in pulses)
        assert [p.delay_tproc_cycles for p in pulses]==[30,round((.3+coordinate[0])*300),round((.5+2*coordinate[0])*300)]
        seq=FineTuneSequence(('awg_0',)).add_set('hold',.01,6000)
        program=seq.make_program(_shared_tmux_soccfg(),awg_channels=(1,),rf_pulses=pulses)
        program.compile();counts.append(len(program.envelopes[0]['envs']))
    assert counts==[16,16,16]
    results.append(dict(case='named_tau_host_coordinates_with_fine_width',passed=True,
                        tau_us=[1.,2.,3.],samples_per_pulse=960,patterns_per_program=counts,
                        distinction='tau remains an explicit host sweep; fine duration remains a hardware sweep'))

    for value in (0.,-1.,float('nan'),float('inf')):
        try: samples_from_us(value,300.)
        except ValueError: pass
        else: raise AssertionError('invalid duration accepted')
    for value in (0,True,1.5,None):
        try: RfPulseConfig(0,'hold',3,1000,fine_duration=True,duration_samples=value)
        except (TypeError,ValueError): pass
        else: raise AssertionError('invalid sample count accepted')
    results.append(dict(case='invalid_duration_and_sample_count',passed=True))

    cfg=_shared_tmux_soccfg();cfg['gens'][0]['has_dds']=False
    seq=FineTuneSequence(('awg_0',)).add_set('hold',.01,2000)
    rf=RfPulseConfig(0,'hold',7,1000,freq_mhz=50.,delay_tproc_cycles=30,
                     fine_duration=True,duration_samples=97)
    try:
        seq.make_program(cfg,awg_channels=(1,),rf_pulse=rf).compile()
        dds_guard='missing_confirmed'
    except (RuntimeError,ValueError):
        dds_guard='rejected'
    stage=Path('F:/Vivado_Output/a5fine_sw/DCWaveformGeneratorGUI')
    result=dict(source_sha256=hashlib.sha256((stage/'qick_rf_fine_duration.py').read_bytes()).hexdigest(),
                checks=results,dds_disabled_configuration=dds_guard,
                scope='No source changes, no board, no synthesis, no new RTL simulation.')
    target=Path(__file__).with_suffix('.json')
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
