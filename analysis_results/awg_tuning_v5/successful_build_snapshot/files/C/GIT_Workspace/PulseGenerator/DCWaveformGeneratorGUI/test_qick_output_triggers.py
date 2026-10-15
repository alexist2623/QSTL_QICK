import pytest
from types import SimpleNamespace
from qick.sim import QickSim  # desktop PYNQ stubs
from qick.awg_tuning import TProcV1BehaviorModel
from test_qick_fine_tune_sweep import _avg_soccfg, _fir_soccfg
from qick_fine_tune_sweep import FineTuneSequence, ReadoutConfig, DdrFirReadoutConfig
from qick_square_dds import OutputTriggerConfig, attach_square_settings


def edges_for_bit(events,bit):
    state=0; edges=[]
    for event in events:
        value=bool(event.word & (1<<bit))
        if value!=state: edges.append((event.cycle,value)); state=value
    return edges


@pytest.mark.parametrize('delay,width',[(0,10),(0,50),(5,5),(5,10),(5,15),(5,30),(20,5),(20,20)])
@pytest.mark.parametrize('scope',['loop','experiment'])
def test_shared_marker_does_not_shorten_adc_trigger(delay,width,scope):
    cfg=_avg_soccfg(1)
    cfg['readouts'][0]['trigger_port']=7
    cfg['tprocs'][0]['output_pins']=[('output',7,6,'SPARE1_1V8')]
    sequence=FineTuneSequence(('awg',)).add_set('measure',0.1,200)
    attach_square_settings(sequence,trigger=OutputTriggerConfig(True,0,scope,'both',width/300))
    prog=sequence.make_program(cfg,awg_channels=(0,),repetitions_per_sweep=2,
                              readout=ReadoutConfig(0,40,at_segment='measure',timing_reference='segment_start',
                                                   measure_delay_tproc_cycles=delay,trigger_width_tproc_cycles=10))
    prog.compile()
    model=TProcV1BehaviorModel(strict=True); model.run(prog)
    events=[ev for ev in model.output_events if ev.tproc_ch==7]
    events += [SimpleNamespace(cycle=ev['cycle'],word=ev['word'])
               for ev in model.output_pin_events if ev['port']==7]
    events.sort(key=lambda ev: ev.cycle)
    assert [ev.cycle for ev in events]==sorted(ev.cycle for ev in events)
    assert len({ev.cycle for ev in events})==len(events)
    adc=edges_for_bit(events,0)
    assert len(adc)==4
    assert [adc[i+1][0]-adc[i][0] for i in (0,2)]==[10,10]
    markers=edges_for_bit(events,6)
    assert len(markers)==(8 if scope=='loop' else 4)
    assert all(markers[i+1][0]-markers[i][0]==width for i in range(0,len(markers),2))
    assert prog.ro_chs[0]['trigs']==1
    assert model.dmem[prog.COUNTER_ADDR]==2
    # Markers must not add a blocking wait to every repetition. The pre-existing
    # ADC completion wait remains separate from the one final marker wait.
    waits=[inst for inst in prog.prog_list if inst['name']=='waiti' and
           'marker' in inst.get('comment','')]
    assert not waits
    waits=[inst for inst in prog.prog_list if inst.get('comment')=='wait for experiment epilogue']
    assert len(waits)==1


def test_missing_pin_is_rejected():
    sequence=FineTuneSequence(('awg',)).add_set('measure',0.1,200)
    attach_square_settings(sequence,trigger=OutputTriggerConfig(True))
    with pytest.raises(ValueError,match='absent'):
        sequence.make_program(_avg_soccfg(1),awg_channels=(0,))


def test_ddr_marker_preserves_swept_timestamp_and_width():
    cfg=_fir_soccfg(ddr_trigger_port=7)
    cfg['tprocs'][0]['output_pins']=[('output',7,6,'SPARE1_1V8')]
    sequence=FineTuneSequence(('awg',)).add_set('lead',0.0,100).add_set('measure',0.1,1000)
    sequence.add_hold_duration_sweep('lead',start_us=0.02,stop_us=1.0,count=5,sequence_fabric_mhz=300)
    attach_square_settings(sequence,trigger=OutputTriggerConfig(True,0,'loop','start',28.5))
    ddr=DdrFirReadoutConfig(0,2,'measure',margin_input_samples=0,trigger_width_tproc_cycles=12)
    prog=sequence.make_program(cfg,awg_channels=(0,),ddr_readout=ddr)
    prog.compile()
    model=TProcV1BehaviorModel(strict=True)
    prog.load_runtime_dmem_into_model(model); model.run(prog)
    events=[ev for ev in model.output_events if ev.tproc_ch==7]
    assert len({ev.cycle for ev in events})==len(events)
    markers=edges_for_bit(events,6); captures=edges_for_bit(events,1)
    assert len(markers)==len(captures)==10
    for index in range(5):
        assert markers[2*index+1][0]-markers[2*index][0]==8550
        assert captures[2*index+1][0]-captures[2*index][0]==12
    # Legacy 1 MSPS uses software FIR-delay compensation (8397 cycles here).
    assert [captures[2*i][0]-markers[2*i][0] for i in range(5)]==[8403,8477,8551,8625,8699]
