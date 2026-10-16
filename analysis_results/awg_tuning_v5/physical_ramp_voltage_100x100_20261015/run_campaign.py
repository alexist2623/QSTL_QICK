"""Sequential physical cases; only reviewed run_physical owns instruments.
No implicit retries. Rejects remain evidence. Existing successful first case may
be adopted only after cleanup, restore, source hashes and point count checks.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent

def now(): return datetime.now(timezone.utc).isoformat()
def main():
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true',required=True)
    args=p.parse_args()
    target=HERE/'physical_campaign_status.json'
    if target.exists(): raise FileExistsError(target)
    state=dict(started_utc=now(),complete=False,cases=[])
    def save(): target.write_text(json.dumps(state,indent=2),encoding='utf8')
    save()
    try:
        # Every requested condition appears; rejected cases are never marked PASS.
        for tau in (20,30,10):
            for direction in ('rising','falling'):
                for dac in (4,5):
                    for dc in ('fixed_time10','fixed_time20','fixed_time30','fixed_voltage'):
                        label=f'{direction}_dac{dac}_{dc}_tau{tau}'
                        bundle=HERE/f'offline_{label}'
                        deadline=time.monotonic()+1200
                        while not (bundle/'manifest.json').exists():
                            if (bundle/'preparation_failure.json').exists(): break
                            if time.monotonic()>deadline: raise TimeoutError(f'Preparation unavailable: {label}')
                            time.sleep(1)
                        failure=bundle/'preparation_failure.json'
                        if failure.exists():
                            rejection=json.loads(failure.read_text(encoding='utf8'))
                            message=rejection.get('error','')
                            # Exact production range failures only; all other errors stop.
                            if not ('RC' in message and ('range' in message.lower() or 'limit' in message.lower())):
                                raise RuntimeError(f'Unexpected preparation failure: {label}: {message}')
                            row=dict(label=label,prepared=bundle.name,status='range_rejected_not_run',physical_execution=False,error=message)
                            state['cases'].append(row);save();print(json.dumps(row),flush=True)
                            continue
                        out=HERE/f'run_{label}_01'
                        previous=out.exists()
                        if not previous:
                            with (HERE/f'{out.name}.log').open('xb') as log:
                                proc=subprocess.run([sys.executable,'-X','utf8',str(HERE/'run_physical.py'),'--execute','--prepared',bundle.name,'--output',out.name],cwd='C:/GIT_Workspace/QSTL_QICK',stdout=log,stderr=subprocess.STDOUT)
                            code=proc.returncode
                        else: code=0
                        measured=json.loads((out/'status.json').read_text(encoding='utf8')) if (out/'status.json').exists() else {}
                        good=code==0 and measured.get('acquisition_success') and measured.get('cleanup_zero') and measured.get('scope_restore',{}).get('passed') and not measured.get('production_sources_changed')
                        row=dict(label=label,prepared=bundle.name,run=out.name,status='acquired' if good else 'acquisition_failed',exit_code=code,acquisition_success=bool(good),preexisting_success_preserved=previous,capture_id=measured.get('capture_id'),cleanup_zero=measured.get('cleanup_zero'),scope_restore_passed=measured.get('scope_restore',{}).get('passed'))
                        state['cases'].append(row);save();print(json.dumps(row),flush=True)
                        if not good: raise RuntimeError(f'Acquisition failed; stopped: {label}')
        state['complete']=True;state['finished_utc']=now();save()
    except BaseException as exc:
        state['error']=repr(exc);state['finished_utc']=now();save();raise
if __name__=='__main__':main()
