"""Prepare shared libraries serially; execute at most three isolated snapshots."""
import concurrent.futures
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from cases import CASES
from run_case import ROOT,EVIDENCE,folder

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    status=EVIDENCE/'status.json'
    if status.exists():raise RuntimeError('Existing batch; inspect it rather than duplicate execution')
    gui=ROOT.parent/'PulseGenerator/DCWaveformGeneratorGUI'
    files=list(gui.glob('*.py'))+list(gui.glob('*.json'))+list((ROOT/'qick/qick_lib/qick').rglob('*.py'))
    for ip in ('axis_awg_tuning_v3','axis_square_pulse_v1','axis_output_sum_v1'):
        files+=list((ROOT/'qick/firmware/ip'/ip/'src').glob('*.sv'))
    project=ROOT/'qick/firmware/projects/qstl_awg_v4'
    files += [project/n for n in ('timing.xdc','ios.xdc','bitstream.bit','bitstream.hwh','bitstream.xsa')]
    before={str(p):sha(p) for p in files}
    (EVIDENCE/'production_hashes_before.json').write_text(json.dumps(before,indent=2),encoding='utf8')
    state=dict(pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),complete=False,
        max_isolated_simulators=3,cases={},production_changes=[],stage='running')
    lock=threading.RLock()
    def save():
        with lock:
            state['updated_utc']=datetime.now(timezone.utc).isoformat()
            tmp=status.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2),encoding='utf8');tmp.replace(status)
    def execute(name,phase,extra):
        log=EVIDENCE/f'{name}_{phase}.log'
        if log.exists():raise RuntimeError('Preserve existing log '+str(log))
        argv=[sys.executable,'-X','utf8','-X','faulthandler',str(Path(__file__).with_name('run_case.py')),'--case',name,*extra]
        start=time.time()
        with log.open('w',encoding='utf8') as stream:
            process=subprocess.Popen(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            with lock:
                state['cases'][name][phase]=dict(pid=process.pid,command=argv,log=str(log),started_utc=datetime.now(timezone.utc).isoformat())
                save()
            code=process.wait()
        with lock:
            state['cases'][name][phase].update(exit_code=code,elapsed_s=time.time()-start)
            save()
        print(name,phase,'exit',code,flush=True)
        return code==0
    def simulate(name):
        with lock:state['cases'][name]['state']='running';save()
        ok=execute(name,'rtl',['--reuse-snapshot'])
        if ok:
            result=json.loads((folder(name)/'result.json').read_text())
            ok=result['validation_status']=='passed'
        with lock:state['cases'][name]['state']='passed' if ok else 'failed';save()
    save()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures=[]
        for name in CASES:
            with lock:state['cases'][name]=dict(folder=str(folder(name)),state='preparing');save()
            prepared=folder(name)/'prepared.json'
            if prepared.exists():
                # The first exploratory preparation was executed by this task;
                # reuse only its snapshot, never historical simulation results.
                assert name=='hold_fixed_time' and not (folder(name)/'result.json').exists()
                state['cases'][name]['preparation']='initial current-task preparation; fingerprint rechecked on reuse'
                ok=True
            else:ok=execute(name,'prepare',['--prepare-only'])
            if ok:futures.append(pool.submit(simulate,name))
            else:
                with lock:state['cases'][name]['state']='failed_prepare';save()
        for f in concurrent.futures.as_completed(futures):f.result()
    state['production_changes']=[p for p,h in before.items() if not Path(p).is_file() or sha(Path(p))!=h]
    state['complete']=not state['production_changes'] and all(v['state']=='passed' for v in state['cases'].values())
    state['stage']='finished' if state['complete'] else 'finished_with_failures'
    state['finished_utc']=datetime.now(timezone.utc).isoformat();save()
    return 0 if state['complete'] else 1

if __name__=='__main__':raise SystemExit(main())
