"""Schedule the final OFF fixture without exceeding three simulators total."""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from run_case import ROOT,EVIDENCE,folder

if __name__=='__main__':
    path=EVIDENCE/'off_status.json';assert not path.exists()
    target=folder('compensation_off').with_name(folder('compensation_off').name.replace('compensation_off_output_sum','compensation_off_retry2_output_sum'))
    state=dict(pid=os.getpid(),folder=str(target),stage='waiting_shared_library',complete=False,
        started_utc=datetime.now(timezone.utc).isoformat())
    def save():
        state['updated_utc']=datetime.now(timezone.utc).isoformat()
        tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2));tmp.replace(path)
    def execute(stage,flag):
        log=EVIDENCE/f'compensation_off_retry2_{stage}.log';assert not log.exists()
        args=[sys.executable,'-X','utf8','-X','faulthandler',str(Path(__file__).with_name('run_off_final.py')),flag]
        with log.open('w',encoding='utf8') as f:
            p=subprocess.Popen(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
            state['stage']=stage;state[stage]=dict(pid=p.pid,command=args,log=str(log));save()
            code=p.wait()
        state[stage]['exit_code']=code;save()
        print(stage,code,flush=True)
        return code==0
    save()
    while json.loads((EVIDENCE/'additional_status.json').read_text())['stage'] in ('waiting_shared_preparation','preparing'):time.sleep(10)
    if execute('prepare','--prepare-only'):
        state['stage']='waiting_simulator_slot';save()
        while True:
            initial=json.loads((EVIDENCE/'status.json').read_text())
            extra=json.loads((EVIDENCE/'additional_status.json').read_text())
            stages=[v['state'] for v in extra['cases'].values()]
            if 'finished_utc' in initial and not any(s in ('prepared','preparing') for s in stages) and stages.count('running')<=2:break
            time.sleep(10)
        state['complete']=execute('rtl','--reuse-snapshot')
    state['stage']='finished' if state['complete'] else 'failed';state['finished_utc']=datetime.now(timezone.utc).isoformat();save()
    raise SystemExit(0 if state['complete'] else 1)
