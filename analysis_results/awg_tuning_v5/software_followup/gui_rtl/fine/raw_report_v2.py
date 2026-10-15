"""Low-level diagnostic only. It deliberately bypasses GUI construction, not its guard.

Identical timestamps are sent through the existing real tProcessor/TMUX path to
measure serialized delivery. This is NOT a supported GUI experiment or PASS for
simultaneous physical timing.
"""
import csv
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]

def prepare(build):
    import qick.sim
    from qick import QickConfig
    from qick.asm_v1 import QickProgram
    from qick.awg_tuning import TProcV1BehaviorModel
    from extension_v5 import configure
    cfg=QickConfig(json.loads((ROOT/'qick/firmware/projects/qstl_gui_rtl_sim/soccfg.json').read_text()))
    for gen in cfg['gens']:
        if gen['type']=='axis_awg_tuning_v1':gen.update(type='axis_awg_tuning_v3',frac=18,step_width=32,dc_area_version=1,dc_area_bits=48,output_latency_cycles=16,dc_start_cycles=17)
    configure(cfg)
    program=QickProgram(cfg)
    for awg in (1,3,5):program.awg_set(awg,value=0,duration=30,t=1000)
    for trial,first in enumerate(('awg','rf')):
        when=3000+trial*2000
        for awg,rf in ((1,0),(3,2),(5,4)):
            for kind in (first,'rf' if first=='awg' else 'awg'):
                if kind=='awg':program.awg_set(awg,value=4096,duration=30,t=when)
                else:program.setup_and_pulse(rf,t=when,style='const',freq=0,phase=0,gain=4000,length=30,mode='oneshot',stdysel='zero',phrst=0)
        for awg in (1,3,5):program.awg_set(awg,value=0,duration=30,t=when+60)
    program.end();program.compile()
    model=TProcV1BehaviorModel(strict=False);model.run(program,max_steps=100000)
    out=Path(build)/'raw_same_timestamp';out.mkdir(exist_ok=False)
    (out/'pmem.hex').write_text(''.join(f'{int(w):016x}\n' for w in program.binprog))
    (out/'dmem.txt').write_text('');(out/'program.asm').write_text(program.asm())
    for rf in (0,2,4):(out/f'envelope_{rf}.hex').write_text('')
    wanted=[dict(cycle=e.cycle,port=e.tproc_ch,word=f'{e.word:040x}') for e in model.output_events]
    (out/'expected.json').write_text(json.dumps(dict(events=wanted,model_timing_conflicts=model.timing_conflicts,
        disclaimer='Raw low-level diagnostic; GUI guard is retained and this is not a supported simultaneous-output program.'),indent=2,default=str))
    return dict(name='raw_same_timestamp',folder=str(out),cycles=8000,raw_same_timestamp=True)

def check(case):
    out=Path(case['folder']);log=(out/'run_console.log').read_text(errors='replace')
    assert 'RTL COMPLETE' in log and 'Fatal:' not in log and 'ERROR:' not in log
    wanted=json.loads((out/'expected.json').read_text())['events']
    with (out/'rtl_events.csv').open() as stream:actual=list(csv.DictReader(stream))
    result=[]
    for port,channel in enumerate((0,2,4)):
        req=[r for r in wanted if r['port']==port];got=[r for r in actual if int(r['port'])==port]
        assert len(req)==len(got),(port,len(req),len(got))
        offset=int(got[0]['cycle'])-req[0]['cycle']
        for a,b in zip(req,got):assert int(a['word'],16)==int(b['word'],16)
        with (out/f'fine_{channel}.csv').open() as stream:trace=list(csv.DictReader(stream))
        awg=[int(r['cycle']) for a,r in zip(trace,trace[1:]) if int(a['awg'],16)==0 and int(r['awg'],16)!=0]
        rf=[int(r['cycle']) for a,r in zip(trace,trace[1:]) if int(a['rf'],16)==0 and int(r['rf'],16)!=0]
        assert len(awg)==len(rf)==2
        for trial,indices in enumerate(((1,2),(4,5))):
            requests=[req[i] for i in indices];deliveries=[got[i] for i in indices]
            assert requests[0]['cycle']==requests[1]['cycle']
            item=dict(port=port,order='AWG then RF' if trial==0 else 'RF then AWG',requested_timestamp=requests[0]['cycle'],
                observed_tproc_cycles=[int(x['cycle']) for x in deliveries],
                command_lateness_cycles=[int(x['cycle'])-requests[0]['cycle']-offset for x in deliveries],
                awg_sum_input_start=awg[trial],rf_sum_input_start=rf[trial],
                inferred_awg_physical_start=awg[trial]+25,inferred_rf_physical_start=rf[trial]+12,
                inferred_physical_rf_minus_awg_cycles=rf[trial]+12-awg[trial]-25,
                physical_timestamp_method='Inferred from directly observed sum input edges plus separately verified AWG25/RF12 downstream latency; components are not separately observable after addition.')
            result.append(item)
    assert log.count('OUTPUT_SUM_RESULT')==3
    report=dict(passed=True,diagnostic_only=True,sum_lane_oracle_errors=0,
        simultaneous_output_supported=all(r['inferred_physical_rf_minus_awg_cycles']==0 for r in result),
        measurements=result,conclusion='Measured actual delivery/output skew for intentionally identical timestamps; production GUI guards were not changed.')
    (out/'result.json').write_text(json.dumps(report,indent=2));return report

if __name__=='__main__':
    path=Path(sys.argv[1]);prepared=json.loads(path.read_text());prepared['cases'].append(prepare(prepared['build']));path.write_text(json.dumps(prepared,indent=2))
