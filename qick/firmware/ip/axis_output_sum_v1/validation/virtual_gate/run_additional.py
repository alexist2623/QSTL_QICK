"""Current-task harness retries plus CPMG outer points/named parameter sweeps."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from run_case import EVIDENCE,ROOT,folder

HERE=Path(__file__).resolve().parent

def main():
    path=EVIDENCE/'additional_status.json'
    assert not path.exists(),'Do not duplicate current additional controller'
    state=dict(pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),complete=False,
        stage='waiting_shared_preparation',cases={})
    lock=threading.RLock()
    def save():
        with lock:
            state['updated_utc']=datetime.now(timezone.utc).isoformat()
            tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2));tmp.replace(path)
    def execute(name,argv,phase):
        log=EVIDENCE/f'{name}_{phase}.log';assert not log.exists()
        with log.open('w',encoding='utf8') as stream:
            p=subprocess.Popen(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            with lock:state['cases'][name][phase]=dict(pid=p.pid,command=argv,log=str(log));save()
            rc=p.wait()
        with lock:state['cases'][name][phase]['exit_code']=rc;save()
        print(name,phase,rc,flush=True)
        return rc==0
    save()
    # The existing batch owns the shared xelab library until its last case is prepared.
    while True:
        initial=json.loads((EVIDENCE/'status.json').read_text())
        last=initial['cases'].get('square_phase',{})
        if 'exit_code' in last.get('prepare',{}):break
        time.sleep(10)
    tasks=[]
    for name in ('ramp_fixed_time','ramp_fixed_voltage_descending','compensation_off'):
        target=folder(name).with_name(folder(name).name.replace(name+'_output_sum',name+'_retry1_output_sum'))
        tasks.append((name+'_retry1',[str(HERE/'run_retry.py'),'--case',name],target))
    for n in (1,2):
        for tau in (.2,.4):
            name=f'cpmg_n{n}_tau{round(tau*1000)}ns'
            target=folder('ramp_fixed_time').with_name(f'rc_precomp_repeat_reset_hold_duration_2x2_v4virt_20261014_{name}_output_sum_awg_v3')
            tasks.append((name,[str(HERE/'run_composite.py'),'--n',str(n),'--tau',str(tau)],target))
    for parameter in ('frequency','duration'):
        name='cpmg_named_'+parameter
        target=folder('ramp_fixed_time').with_name(f'rc_precomp_repeat_reset_hold_duration_2x2_v4virt_20261014_{name}_output_sum_awg_v3')
        tasks.append((name,[str(HERE/'run_composite.py'),'--named',parameter],target))
    ready=[]
    state['stage']='preparing'
    for name,args,target in tasks:
        assert not target.exists(),str(target)
        argv=[sys.executable,'-X','utf8','-X','faulthandler',*args]
        state['cases'][name]=dict(folder=str(target),state='preparing');save()
        if execute(name,argv+['--prepare-only'],'prepare'):
            state['cases'][name]['state']='prepared';ready.append((name,argv))
        else:state['cases'][name]['state']='failed_prepare'
        save()
    state['stage']='waiting_initial_simulators';save()
    while 'finished_utc' not in json.loads((EVIDENCE/'status.json').read_text()):time.sleep(10)
    def run(task):
        name,argv=task
        with lock:state['cases'][name]['state']='running';save()
        ok=execute(name,argv+['--reuse-snapshot'],'rtl')
        with lock:state['cases'][name]['state']='passed' if ok else 'failed';save()
    state['stage']='simulating';save()
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(run,ready))
    before=json.loads((EVIDENCE/'production_hashes_before.json').read_text())
    state['production_changes']=[p for p,h in before.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    state['complete']=not state['production_changes'] and all(v['state']=='passed' for v in state['cases'].values())
    state['stage']='finished' if state['complete'] else 'finished_with_failures'
    state['finished_utc']=datetime.now(timezone.utc).isoformat();save()
    return 0 if state['complete'] else 1

if __name__=='__main__':raise SystemExit(main())
