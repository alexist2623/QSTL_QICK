"""Run the twelve explicitly requested finite physical cases sequentially.

No board access here: the reviewed single-case runner owns each connection,
finite program, zero cleanup, fresh single acquisition and scope restoration.
Stops after any acquisition failure. Never retries or overwrites a run.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', required=True)
    parser.parse_args()
    target = HERE/'physical_campaign_status.json'
    if target.exists():
        raise FileExistsError('Preserve an existing campaign status; inspect before resuming')
    status = dict(started_utc=datetime.now(timezone.utc).isoformat(), complete=False, cases=[])
    def save():
        target.write_text(json.dumps(status,indent=2),encoding='utf8')
    save()
    for tau in (10,20,30):
        for dc in ('fixed_voltage','fixed_time10','fixed_time20','fixed_time30'):
            label=f'{dc}_tau{tau}'
            bundle=HERE/f'offline_range300_{label}'
            out=HERE/f'run_{label}_01'
            if out.exists():
                previous=json.loads((out/'status.json').read_text())
                if label!='fixed_voltage_tau10' or not previous['acquisition_success']:
                    raise RuntimeError(f'Unexpected existing run {out.name}; no overwrite or retry')
                row=dict(label=label,prepared=bundle.name,run=out.name,exit_code=0,
                         preexisting_success_preserved=True,capture_id=previous['capture_id'])
            else:
                deadline=time.monotonic()+600
                while not (bundle/'manifest.json').exists():
                    if (bundle/'failure.json').exists() or time.monotonic()>deadline:
                        raise RuntimeError(f'Preparation failed or timed out: {bundle.name}')
                    time.sleep(1)
                with (HERE/f'{out.name}.log').open('xb') as log:
                    done=subprocess.run([sys.executable,'-X','utf8',str(HERE/'run_physical.py'),
                        '--execute','--prepared',bundle.name,'--output',out.name],
                        cwd='C:/GIT_Workspace/QSTL_QICK',stdout=log,stderr=subprocess.STDOUT)
                measured=json.loads((out/'status.json').read_text()) if (out/'status.json').exists() else {}
                row=dict(label=label,prepared=bundle.name,run=out.name,exit_code=done.returncode,
                         acquisition_success=measured.get('acquisition_success',False),
                         capture_id=measured.get('capture_id'),cleanup_zero=measured.get('cleanup_zero'),
                         scope_restore_passed=measured.get('scope_restore',{}).get('passed'))
            status['cases'].append(row);save();print(json.dumps(row),flush=True)
            if row['exit_code'] or not row.get('acquisition_success',row.get('preexisting_success_preserved')):
                raise RuntimeError(f'Physical case failed; stopped campaign: {label}')
    status['complete']=True
    status['finished_utc']=datetime.now(timezone.utc).isoformat()
    save()

if __name__=='__main__':
    main()
