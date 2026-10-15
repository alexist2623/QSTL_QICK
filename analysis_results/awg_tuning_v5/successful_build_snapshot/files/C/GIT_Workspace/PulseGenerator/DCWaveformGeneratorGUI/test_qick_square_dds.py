import itertools
import pytest
from qick.sim import QickSim  # installs desktop PYNQ stubs
from qick.awg_tuning import TProcV1BehaviorModel
from qick.square_pulse import square_words
from test_qick_fine_tune_sweep import _mock_soccfg
from qick_fine_tune_sweep import FineTuneSequence
from qick_square_dds import SquarePulseConfig, SquarePulseSweep, attach_square_settings


def configuration():
    cfg=_mock_soccfg(1)
    gen=dict(cfg['gens'][0])
    gen.update(type='axis_square_pulse_v1',gen_type='square_pulse',tmux_ch=2,
               dac='13',f_dds=4800.0,has_dds=True,command_latency_cycles=4)
    cfg['gens'].append(gen)
    return cfg


@pytest.mark.parametrize('mute', [False, True])
def test_cartesian_words_from_hardware_loops(mute):
    cfg=configuration()
    config=SquarePulseConfig(1,mute_on_finish=mute)
    axes=(SquarePulseSweep('frequency',0.04,190,3,1),
          SquarePulseSweep('amplitude',0,800,3,1),
          SquarePulseSweep('phase',-180,360,4,1))
    seq=FineTuneSequence(('gate',)).add_set('measure',0.1,3000)
    attach_square_settings(seq,config,axes)
    prog=seq.make_program(cfg,awg_channels=(0,),repetitions_per_sweep=2)
    prog.compile()
    model=TProcV1BehaviorModel(strict=True)
    prog.load_runtime_dmem_into_model(model)
    model.run(prog)
    events=[ev for ev in model.output_events if (ev.word>>152)&255==2]
    expected=[]
    for f,a,p in itertools.product(*(axis.points for axis in axes)):
        words=square_words(config.word('frequency',f,cfg['gens'][1]),
                           config.word('phase',p,cfg['gens'][1]),
                           config.word('amplitude',a,cfg['gens'][1]),tmux_ch=2)
        expected.extend([sum(w<<(32*i) for i,w in enumerate(words))]*2)
    assert [ev.word for ev in (events[:-1] if mute else events)]==expected
    if mute:
        assert events[-1].word & (1<<128)==0
        assert events[-1].word == events[-2].word & ~(1<<128)
    else:
        assert events[-1].word == expected[-1]
    assert not any(ev.word & (1<<129) for ev in events)
    assert len(prog._runtime_dmem_words)==10
    assert prog.cfg['expts']==36


def test_square_axes_do_not_unroll_instruction_memory():
    sizes=[]
    for count in (2,100):
        seq=FineTuneSequence(('gate',)).add_set('measure',0.1,3000)
        attach_square_settings(seq,SquarePulseConfig(1),(SquarePulseSweep('phase',0,360,count,1),))
        prog=seq.make_program(configuration(),awg_channels=(0,))
        sizes.append(len(prog.prog_list))
    assert sizes[0]==sizes[1]


def test_old_firmware_rejects_only_enabled_square():
    seq=FineTuneSequence(('gate',)).add_set('measure',0.1,3000)
    attach_square_settings(seq)
    seq.make_program(_mock_soccfg(1),awg_channels=(0,))
    attach_square_settings(seq,SquarePulseConfig(0))
    with pytest.raises(ValueError,match='not a SquarePulse'):
        seq.make_program(_mock_soccfg(1),awg_channels=(0,))


def test_twelve_generators_four_readouts_with_square_and_shared_marker():
    from copy import deepcopy
    from test_qick_fine_tune_sweep import _fir_soccfg, _shared_tmux_soccfg
    from qick_fine_tune_sweep import DdrFirReadoutConfig
    from qick_square_dds import OutputTriggerConfig
    cfg = _fir_soccfg(ddr_trigger_port=7)
    rf, awg = _shared_tmux_soccfg()['gens']
    gens = []
    for port in range(4):
        for dest, source in enumerate((rf, awg)):
            gen = deepcopy(source)
            gen.update(tproc_ch=port, tmux_ch=dest, dac=f'{dest}{port}')
            gens.append(gen)
    for port, dest, dac in ((4,1,'20'), (5,1,'21'), (6,0,'22'), (6,2,'23')):
        gen = deepcopy(awg); gen.update(tproc_ch=port, tmux_ch=dest, dac=dac)
        gens.append(gen)
    gens[7].update(type='axis_square_pulse_v1',gen_type='square_pulse',has_dds=True,f_dds=4800.0)
    cfg['gens'] = gens
    readout = cfg['readouts'][0]
    cfg['readouts'] = [dict(readout, tproc_ctrl=port, tmux_ch=dest, trigger_port=7,
                            trigger_bit=i, adc=f'{i}0')
                       for i,(port,dest) in enumerate(((4,0),(5,0),(6,1),(6,3)))]
    cfg['tprocs'][0]['output_pins']=[('output',7,6,'SPARE1_1V8')]
    seq=FineTuneSequence(('gate0','gate1','gate2')).add_set('measure',(0.1,0.2,0.3),3000)
    axes=tuple(SquarePulseSweep(name,start,stop,3,7) for name,start,stop in
               [('frequency',.04,190),('amplitude',10,800),('phase',-180,180)])
    attach_square_settings(seq,SquarePulseConfig(7),axes,OutputTriggerConfig(True,0,'loop','both',1))
    prog=seq.make_program(cfg,awg_channels=(1,3,5),
                          ddr_readout=DdrFirReadoutConfig(0,2,'measure',margin_input_samples=0))
    prog.compile()
    model=TProcV1BehaviorModel(strict=True)
    prog.load_runtime_dmem_into_model(model); model.run(prog)
    commands=[event for event in model.output_events if event.tproc_ch==3 and event.word>>152==1]
    assert len(commands)==28
    assert commands[-1].word & (1<<128)==0
    assert model.dmem[prog.COUNTER_ADDR]==27
    assert not model.timing_conflicts
