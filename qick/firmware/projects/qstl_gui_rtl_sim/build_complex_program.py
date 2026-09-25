"""Compile the screenshot's two-channel waveform with a 10 x 10 GUI sweep."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument('--gui',type=Path,required=True)
    p.add_argument('--gen3-range',type=float,nargs=2,default=(125.,215.))
    p.add_argument('--gen1-range',type=float,nargs=2,default=(-75.,15.))
    p.add_argument('--case',default='gui_complex_10x10')
    a=p.parse_args();d=HERE/a.case;d.mkdir(exist_ok=True)
    sys.path.insert(0,str(a.gui/'DCWaveformGeneratorGUI'))
    from qick.sim import QickSim  # Hardware-free import stubs.
    from qick import QickConfig
    from qick.awg_tuning import TProcV1BehaviorModel
    from dc_waveform_core import PulseSequence,QickSweepSpec,generate_qick_program_code
    import numpy as np
    soc=QickConfig(json.loads((HERE/'soccfg.json').read_text()))
    # Rows are (incoming ramp us, flat us, left/gen3 mV, right/gen1 mV).
    table=[(0.,5.,0.,0.),(1.,5.,0.,300.),(1.,5.,-300.,0.),
           (.05,.1,125.,-75.),(.1,40.,0.,0.)]
    pulses=[]
    for output in range(2):
        t=[0.];v=[table[0][2+output]];elapsed=0.
        for index,(ramp,flat,left,right) in enumerate(table):
            voltage=(left,right)[output]
            if index:
                elapsed+=ramp*1000;t.append(elapsed);v.append(voltage)
            elapsed+=flat*1000;t.append(elapsed);v.append(voltage)
        pulse=PulseSequence();pulse.t=np.array(t);pulse.v=np.array(v)
        pulse.segment_names=[f'set_{i}' for i in range(5)];pulses.append(pulse)
    specs=[QickSweepSpec('set_3',name,limits[0]/800,limits[1]/800,10)
           for name,limits in zip(('awg_0','awg_1'),(a.gen3_range,a.gen1_range))]
    trigger=dict(enabled=True,pin=0,scope='loop',edge='both',width_us=.37)
    code=generate_qick_program_code(pulses,awg_channels=(3,1),full_scale_mv=800.,
        fabric_mhz=300.,tproc_mhz=300.,repetitions_per_sweep=1,sweeps=specs,
        output_trigger_settings=trigger)
    (d/'gui_export.py').write_text(code,encoding='utf-8')
    ns={'__name__':'gui_complex_export'};exec(compile(code,str(d/'gui_export.py'),'exec'),ns)
    program=ns['build_program'](soc);program.compile()
    (d/'program.asm').write_text(program.asm())
    (d/'pmem.hex').write_text(''.join(f'{int(w):016x}\n' for w in program.binprog))
    dm={int(program._runtime_dmem_base)+i:int(v)&0xffffffff for i,v in enumerate(program._runtime_dmem_words)}
    (d/'dmem.txt').write_text(''.join(f'{addr:08x} {word:08x}\n' for addr,word in dm.items()))
    model=TProcV1BehaviorModel(strict=True);program.load_runtime_dmem_into_model(model);model.run(program)
    events=[dict(cycle=e.cycle,port=e.tproc_ch,word=f'{e.word:040x}',kind='axis') for e in model.output_events]
    events += [dict(cycle=e['cycle'],port=e['port'],word=f'{e["word"]:040x}',kind=e['kind']) for e in model.output_pin_events]
    events.sort(key=lambda e:(e['cycle'],e['port']))
    from dataclasses import asdict
    meta=dict(case=a.case,table=table,channels=[3,1],full_scale_mv=800.,
        axes=[dict(gen=gen,output=name,segment='set_3',start_mv=limits[0],stop_mv=limits[1],count=10)
              for gen,name,limits in zip((3,1),('awg_0','awg_1'),(a.gen3_range,a.gen1_range))],
        range_source='Explicit test assumption: ranges absent from screenshot; first point matches screenshot',
        trigger=trigger,repetitions=1,points=100,events=events,
        pmem_words=len(program.binprog),dmem_words=len(dm),
        stop_cycle=max(e['cycle'] for e in events)+1500,
        model_conflicts=[asdict(c) for c in model.timing_conflicts])
    (d/'expected.json').write_text(json.dumps(meta,indent=2)+'\n')
    sources={name:hashlib.sha256((a.gui/'DCWaveformGeneratorGUI'/name).read_bytes()).hexdigest()
             for name in ('dc_waveform_core.py','qick_fine_tune_sweep.py','qick_square_dds.py')}
    (d/'gui_sources.json').write_text(json.dumps(sources,indent=2)+'\n')
    print(json.dumps({k:meta[k] for k in ['points','pmem_words','dmem_words','stop_cycle','model_conflicts']},indent=2))


if __name__=='__main__':main()
