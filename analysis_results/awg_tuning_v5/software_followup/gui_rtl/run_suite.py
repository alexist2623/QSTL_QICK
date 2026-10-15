"""Bounded new v5 GUI -> real RTL runs. Fresh directories preserve every failure."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
SHARED=Path('F:/Vivado_Output/a3sim1')
BUILD=Path(os.environ.get('QICK_V5_POST_GUI_BUILD','F:/Vivado_Output/a5post_gui_rtl1'))
GUI=ROOT.parent/'PulseGenerator'
TAG=os.environ.get('QICK_V5_POST_RUN_TAG','suite')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def initialize():
    BUILD.mkdir(exist_ok=False)
    src=SHARED/'qstl_gui_rtl_sim.sim/sim_1/behav/xsim'
    dst=BUILD/'qstl_gui_rtl_sim.sim/sim_1/behav/xsim'
    (dst/'xsim.dir').mkdir(parents=True)
    shutil.copytree(src/'xsim.dir/xil_defaultlib',dst/'xsim.dir/xil_defaultlib')
    for name in ('xsim.ini','elaborate.bat'):shutil.copy2(src/name,dst/name)
    source=SHARED/'qstl_gui_rtl_sim.gen/sources_1/bd/sim_bd/sim/sim_bd.v'
    dest=BUILD/source.relative_to(SHARED);dest.parent.mkdir(parents=True);shutil.copy2(source,dest)
    shutil.copy2(SHARED/'wrapper_path.txt',BUILD/'wrapper_path.txt')

def cases():
    common=['--build',str(BUILD),'--gui',str(GUI),'--vivado','F:/Xilinx/Vivado/2023.1/bin',
            '--awg-v3','--output-sum','--repeat-reset','--isolated-run','--verify-gui-widgets',
            '--sum-rf-delay-us','.1','--sweep-count','2','--capture-cycles','60000']
    specifications=[
      ('hold1','hold1','hold_duration','fixed_time',None,False),
      ('hold2','hold2','hold_duration','fixed_time',None,False),
      ('hold_fixed_time','general','hold_duration','fixed_time','after_readout',False),
      ('hold_fixed_voltage','general','hold_duration','fixed_voltage','overlap_readout',False),
      ('rf_duration_fixed','general','rf_duration_fixed','fixed_time','after_readout',False),
      ('rf_duration_extend','general','rf_duration','fixed_voltage','overlap_readout',False),
      ('rc_only','general','hold_duration','fixed_time','after_readout',True)]
    for name,script,sweep,mode,ddr,rc in specifications:
        argv=[sys.executable,'-X','utf8',str(HERE/f'verify_{script}.py'),*common,
              '--sweep-case',sweep,'--dc-mode',mode,'--run-tag','v5_post_'+name]
        if ddr:argv+=['--dc-readout-policy',ddr]
        if rc:argv+=['--rc-only']
        yield name,argv

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--resume-prepared',action='store_true');args=parser.parse_args()
    status_path=HERE/f'{TAG}_status.json'
    if args.resume_prepared:
        state=json.loads(status_path.read_text());assert state['stage']=='prepared'
    else:
        assert not status_path.exists();initialize()
        files=list((GUI/'DCWaveformGeneratorGUI').glob('*.py'))+list((ROOT/'qick/qick_lib/qick').rglob('*.py'))
        state=dict(complete=False,stage='preparing',build=str(BUILD),cases={},source_hashes={str(p):sha(p) for p in files})
    def save():state['updated']=time.strftime('%Y-%m-%dT%H:%M:%S%z');status_path.write_text(json.dumps(state,indent=2))
    try:
        if not args.resume_prepared:
            for name,argv in cases():
                state['cases'][name]=dict(state='preparing',command=argv);save()
                with (HERE/f'{TAG}_{name}.prepare.log').open('w') as log:
                    code=subprocess.call([*argv,'--prepare-only'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                state['cases'][name]['prepare_exit_code']=code
                assert code==0,(name,'prepare failed')
                directories=[p for p in BUILD.iterdir() if p.is_dir() and f'_v5_post_{name}_output_sum' in p.name]
                assert len(directories)==1,(name,directories)
                state['cases'][name].update(state='prepared',folder=str(directories[0]));save()
            state['stage']='prepared';save()
        if args.prepare_only:return
        active={};pending=[(name,case) for name,case in state['cases'].items() if case['state']=='prepared']
        while pending or active:
            while pending and len(active)<2:
                name,case=pending.pop(0);log=(HERE/f'{TAG}_{name}.run.log').open('w')
                child=subprocess.Popen([*case['command'],'--reuse-snapshot'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                active[name]=(child,log);case.update(state='running',pid=child.pid);save()
            for name,(child,log) in list(active.items()):
                code=child.poll()
                if code is None:continue
                log.close();del active[name];case=state['cases'][name]
                result_path=Path(case['folder'])/'result.json'
                result=json.loads(result_path.read_text()) if result_path.exists() else {}
                case.update(state='passed' if code==0 and result.get('validation_status')=='passed' else 'failed',exit_code=code)
                save()
            if active:time.sleep(2)
        changed=[p for p,h in state['source_hashes'].items() if sha(p)!=h]
        state['source_changes']=changed
        state['complete']=not changed and all(c['state']=='passed' for c in state['cases'].values())
        state['stage']='passed' if state['complete'] else 'failed';save()
        if not state['complete']:raise SystemExit(1)
    except BaseException as exc:
        state['stage']='failed';state['error']=repr(exc);save();raise

if __name__=='__main__':main()
