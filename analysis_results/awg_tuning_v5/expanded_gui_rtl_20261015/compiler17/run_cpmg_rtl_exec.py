"""Isolated compiler17 RTL runner. --compile-only never starts xsim."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
EXT=ROOT/'analysis_results/awg_tuning_v5/software_followup/gui_rtl'
sys.path[:0]=[str(EXT),str(ROOT.parent/'PulseGenerator/DCWaveformGeneratorGUI')]
from extension_v5 import physical_rows,physical_oracle,signed_lanes
VIVADO=Path('F:/Xilinx/Vivado/2023.1/bin')


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,data):Path(path).write_text(json.dumps(data,indent=2))


def verify(case):
    import numpy as np
    out=Path(case['folder']);log=(out/'run_console.log').read_text(errors='replace')
    assert 'RTL COMPLETE' in log and not re.search(r'Fatal:|ERROR:',log),log[-4000:]
    sums=re.findall(r'OUTPUT_SUM_RESULT suffix=(\d+) samples=(\d+)',log)
    raws=re.findall(r'RAW_AWG_V2_RESULT ch=(\d+) samples=(\d+) ramps=(\d+) sets=(\d+)',log)
    areas=re.findall(r'COMPILER17_AREA suffix=(\d+) shots=(\d+) residual=(-?\d+) enabled=(\d+) fault=(\d+)',log)
    assert {int(v[0]) for v in sums}=={4,5,6} and all(int(v[1])>0 for v in sums)
    assert {int(v[0]) for v in raws}=={4,5,6} and all(int(v[1])>0 for v in raws)
    assert len(areas)==3
    for suffix,shots,residual,enabled,fault in areas:
        assert int(shots)==case['expected_area_shots'][int(suffix)-4] and int(residual)==0 and int(fault)==0,(case['name'],areas)
    wanted=sorted(read(out/'expected.json')['events'],key=lambda e:(e['cycle'],e['port']))
    with (out/'rtl_events.csv').open() as f:actual=sorted(list(csv.DictReader(f)),key=lambda e:(int(e['cycle']),int(e['port'])))
    assert len(actual)==len(wanted),(len(actual),len(wanted))
    origin=int(actual[0]['cycle'])-wanted[0]['cycle']
    for e,v in zip(wanted,actual):
        assert int(v['port'])==e['port'] and int(v['word'],16)==int(e['word'],16),(e,v)
        assert int(v['cycle'])-e['cycle']==origin,(e,v,origin)
    specs=[]
    if case['explicit_offset_variant']:
        import qick.sim
        from dc_waveform_core import QickRfPulseSpec
        specs=[QickRfPulseSpec(**v) for v in read(out/'concrete_specs.json')]
    rf_info=read(out/'rf_expected.json');rf_checks=[];physical_checks=0
    for channel,suffix in ((0,4),(2,5),(4,6)):
        rows=physical_rows(out,suffix);physical_checks+=physical_oracle(rows,suffix)
        pulses=[];active=[]
        for row in rows:
            if row['rf']:active.append(row)
            elif active:pulses.append((active,row['cycle']));active=[]
        assert not active
        commands=next(r['commands'] for r in rf_info if r['channel']==channel)
        assert len(pulses)==len(commands)==case['expected_rf_counts'][channel//2]
        reference=None;carrier_errors=[];measurements=[]
        requested=list(specs[channel//2].pulse_events) if specs else []
        for index,((samples,stop),cmd) in enumerate(zip(pulses,commands)):
            word=int(cmd['word'],16);width=(word>>128)&65535;ftw=word&0xffffffff;gain=(word>>96)&0xffff;phaseword=(word>>32)&0xffffffff
            gain=gain-65536 if gain>=32768 else gain
            assert samples[0]['cycle']-cmd['cycle']-origin==32
            assert stop-samples[0]['cycle']==width
            req=requested[index%len(requested)]
            assert ftw==round(req.frequency_mhz/4800*2**32)&0xffffffff
            assert phaseword==round(req.phase_degrees/360*2**32)&0xffffffff
            assert gain==req.gain and width==round(req.duration_us*300)
            assert ((word>>148)&1)==0 and ((word>>147)&1)==1
            values=np.asarray([v for row in samples for v in signed_lanes(row['rf'])],dtype=float)
            scalar=np.arange(len(values))+samples[0]['cycle']*16
            theta=scalar*(2*np.pi*ftw/2**32)
            if ftw:
                basis=np.column_stack((np.cos(theta),np.sin(theta),np.ones(len(values))))
                if reference is None:
                    reference=np.linalg.lstsq(basis,values,rcond=None)[0]
                    assert abs(float(np.hypot(reference[0],reference[1]))-abs(gain))<=1
                residual=float(max(abs(basis@reference-values)))
                assert residual<=4,(channel,index,residual)
            else:
                # Zero-frequency fixtures use zero phase and a positive gain.
                assert phaseword==0 and gain>0
                residual=float(max(abs(values-gain)));assert residual<=1
            carrier_errors.append(residual)
            measurements.append(dict(index=index,command_cycle=cmd['cycle'],sum_input_start=samples[0]['cycle'],width_cycles=width,
                frequency_register=ftw,gain=gain,phase_register=phaseword,carrier_error_codes=residual))
        rf_checks.append(dict(channel=channel,pulses=len(pulses),measurements=measurements,carrier_error_max_codes=max(carrier_errors,default=0)))
    result=dict(passed=True,xsim_exit_code=0,actual_gui_input=True,actual_tprocessor_tmux_rtl=True,name=case['name'],original_case=case['original_case'],
        explicit_offset_variant=case['explicit_offset_variant'],request_description=case['request_description'],
        command_count=len(wanted),command_value_errors=0,command_timing_errors=0,command_origin=origin,
        physical_sample_checks=physical_checks,sum_lane_samples=sum(int(v[1]) for v in sums),raw_awg=raws,areas=areas,
        rf_checks=rf_checks,board_access=False,adc_fir_arithmetic_validated=False)
    save(out/'result.json',result);return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--compile-only',action='store_true');parser.add_argument('--skip-compile',action='store_true');args=parser.parse_args()
    prepared=read(HERE/'prepared_cpmg.json');build=Path(prepared['build']);sim=build/'sim'
    for group in ('source_hashes','helper_hashes','template_sources'):
        assert all(sha(p)==h for p,h in prepared[group].items()),group
    for case in prepared['cases']:assert all(sha(Path(case['folder'])/n)==h for n,h in case['inputs'].items()),case['name']
    status_path=HERE/('cpmg_compile_status.json' if args.compile_only else 'cpmg_rtl_status.json');assert not status_path.exists()
    state=dict(complete=False,stage='compile',started=time.strftime('%Y-%m-%dT%H:%M:%S%z'),runner_sha256=sha(__file__),cases=[])
    def update():state['updated']=time.strftime('%Y-%m-%dT%H:%M:%S%z');save(status_path,state)
    def execute(name,arguments,log):
        with Path(log).open('w') as stream:
            process=subprocess.Popen([str(VIVADO/(name+'.bat')),*arguments],cwd=sim,stdout=stream,stderr=subprocess.STDOUT)
            state['child_pid']=process.pid;update();code=process.wait()
        state.setdefault('command_exits',[]).append(dict(tool=name,arguments=arguments,log=str(log),pid=process.pid,exit_code=code));update()
        assert code==0,(name,code,str(log))
    try:
        update()
        if not args.skip_compile:
            execute('xvlog',['--relax','-prj',str(build/'template/sources.prj')],build/'compile_console.log')
            state['stage']='elaborate';update()
            libraries=[v for name in prepared['libraries'] for v in ('-L',name)]
            execute('xelab',['--O2','--debug','off','--relax','--mt','off',*libraries,'--snapshot','compiler17','xil_defaultlib.tb_rc_gui','xil_defaultlib.glbl'],build/'elaborate_console.log')
        if not args.compile_only:
            assert (sim/'xsim.dir/compiler17').exists()
            for case in prepared['cases']:
                state['stage']='simulate';state['active_case']=case['name'];update();out=Path(case['folder'])
                options=out/'options.txt';options.write_text('\n'.join(['compiler17','-runall',f'-testplusarg "CASE={out.as_posix()}"',f'-testplusarg "OUT={out.as_posix()}"',f'-testplusarg "CYCLES={case["cycles"]}"',f'-log "{(out/"xsim.log").as_posix()}"']))
                execute('xsim',['-f',str(options)],out/'run_console.log')
                state['stage']='analyze';update();state['cases'].append(verify(case));update();print('PASS',case['name'],flush=True)
        state['complete']=True;state['stage']='compiled' if args.compile_only else 'passed';update()
    except BaseException as exc:
        state['stage']='failed';state['error']=repr(exc);update();raise

if __name__=='__main__':main()
