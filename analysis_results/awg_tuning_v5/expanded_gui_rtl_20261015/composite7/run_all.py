"""Seven fresh GUI->v5 RTL cases, one isolated xsim process at a time."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path('C:/GIT_Workspace/QSTL_QICK')
HERE = Path(__file__).resolve().parent
OLD = ROOT/'analysis_results/awg_tuning_v5/composite_t2_fix/rtl'
V5 = ROOT/'analysis_results/awg_tuning_v5/software_followup/gui_rtl'
BUILD = Path('F:/Vivado_Output/a5composite1')
VIVADO = Path('F:/Xilinx/Vivado/2023.1/bin')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def module(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def main():
    status=HERE/'status.json'
    assert not status.exists() and not BUILD.exists(), 'Existing evidence: never overwrite an attempt'
    BUILD.mkdir()
    gui=ROOT.parent/'PulseGenerator/DCWaveformGeneratorGUI'
    files=list(gui.glob('*.py'))+list((ROOT/'qick/qick_lib/qick').rglob('*.py'))
    state=dict(complete=False, stage='prepare', started=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
               build=str(BUILD), pid=os.getpid(), source_hashes={str(p):sha(p) for p in files},
               cases=[], preparations=[])
    def save():
        state['updated']=time.strftime('%Y-%m-%dT%H:%M:%S%z')
        status.write_text(json.dumps(state,indent=2))
    def run(command, cwd, log, env=None):
        print('RUN', ' '.join(map(str,command)),flush=True)
        with log.open('w') as stream:
            proc=subprocess.run(list(map(str,command)),cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT)
        assert proc.returncode==0,(proc.returncode,str(log))
        return proc.returncode
    save()
    try:
        prepared=[]
        for scenario in ('custom_sweep','hahn_manual'):
            env=os.environ.copy()
            env.update(QICK_T2_SCENARIO=scenario,QICK_T2_RTL_BUILD=str(BUILD/scenario),
                       QICK_T2_PREPARED_NAME=f'{scenario}_prepared.json')
            if scenario=='hahn_manual': env['QICK_T2_COMPILE_ONLY']='1'
            run([sys.executable,'-X','utf8',HERE/'prepare_v5.py'],ROOT,HERE/f'{scenario}.prepare.log',env)
            item=json.loads((HERE/f'{scenario}_prepared.json').read_text())
            prepared.append(item)
            state['preparations'].append(dict(scenario=scenario,exit_code=0,cases=len(item['cases'])))
            save()
        cases=[dict(case,scenario=p['scenario']) for p in prepared for case in p['cases']]
        assert len(cases)==7
        sim=BUILD/'custom_sweep/sim'
        template=BUILD/'custom_sweep/template'
        state['stage']='compile';save()
        run([VIVADO/'xvlog.bat','--relax','-prj',template/'sources.prj'],sim,BUILD/'compile_console.log')
        libraries=[arg for lib in prepared[0]['libraries'] for arg in ('-L',lib)]
        state['stage']='elaborate';save()
        run([VIVADO/'xelab.bat','--O2','--debug','off','--relax','--mt','4',*libraries,
             '--snapshot','composite7_v5','xil_defaultlib.tb_rc_gui','xil_defaultlib.glbl'],
            sim,BUILD/'elaborate_console.log')
        original=module('prior_composite_checks',OLD/'run.py')
        physical=module('current_v5_physical_checks',V5/'extension_v5.py')
        carrier=module('independent_dds_checks',OLD/'check_carrier.py')
        for index,case in enumerate(cases):
            out=Path(case['folder'])
            state.update(stage='simulate',active_case=index,active_folder=str(out));save()
            options=out/'options.txt'
            options.write_text('\n'.join(['composite7_v5','-runall',f'-testplusarg "CASE={out.as_posix()}"',
                f'-testplusarg "OUT={out.as_posix()}"',f'-testplusarg "CYCLES={case["cycles"]}"',
                f'-log "{(out/"xsim.log").as_posix()}"']))
            run([VIVADO/'xsim.bat','-f',options],sim,out/'run_console.log')
            result=original.check(case)
            result['scenario']=case['scenario']
            result['expected_runtime_gains']=case['expected_runtime_gains']
            expected=json.loads((out/'expected.json').read_text())['events']
            native=[]
            for port,suffix in enumerate((4,5,6)):
                events=[e for e in expected if e['port']==port and
                    (int(e['word'],16)>>152)&255==0 and (int(e['word'],16)>>96)&0xffffffff]
                bursts=result['rf_checks'][port]['blocks']
                assert len(events)==len(bursts)==6
                measures=[]
                for event,(begin,end) in zip(events,bursts):
                    assert begin-event['cycle']-result['command_origin_offset_cycles']==32
                    measures.append(dict(command_cycle=event['cycle'],sum_rf_input_start=begin,
                        physical_rf_start=begin+12,physical_rf_stop=end+12,command_to_rf_trace_cycles=32))
                rows=physical.physical_rows(out,suffix)
                samples=physical.physical_oracle(rows,suffix)
                native.append(dict(suffix=suffix,measurements=measures,physical_samples_checked=samples,
                    delayed_awg_cycles=13,physical_expression='saturate_round(AWG[c-25]+RF[c-12])'))
            result['v5_physical']=native
            result['carrier']=carrier.check_case(result)
            (out/'result.json').write_text(json.dumps(result,indent=2))
            state['cases'].append(result);save()
            print(f'PASS {index+1}/7 {case["scenario"]}: tau={case["tau_us"]} pi={case["pi_us"]}',flush=True)
        changed=[p for p,h in state['source_hashes'].items() if sha(p)!=h]
        assert not changed, changed
        for item in prepared:
            for p,h in item['rtl_source_hashes'].items(): assert sha(p)==h,('RTL changed',p)
            for case in item['cases']:
                for name,h in case['inputs'].items(): assert sha(Path(case['folder'])/name)==h
        state.update(complete=True,stage='passed',production_source_changes=[],
                     helper_sha256=sha(__file__),candidate_hwh_sha256=sha('F:/Vivado_Output/a5full1/bitstream.hwh'))
        save()
    except BaseException as exc:
        state.update(stage='failed',error=repr(exc));save();raise

if __name__=='__main__':
    main()
