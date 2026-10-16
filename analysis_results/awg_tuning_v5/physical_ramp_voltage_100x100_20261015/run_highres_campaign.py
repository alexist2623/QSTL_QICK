"""Twenty-four representative fixed-point high-resolution acquisitions.
Requires completed main physical campaign; sole board/scope owner after it.
Each case restores scope and resets/zeros AWGs before the next case.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
import psutil
HERE=Path(__file__).resolve().parent
ROOT=Path('C:/GIT_Workspace/QSTL_QICK')
def now():return datetime.now(timezone.utc).isoformat()
def main():
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true',required=True);p.parse_args()
    main_status=json.loads((HERE/'physical_campaign_status.json').read_text())
    assert main_status['complete'],'Wait for full main campaign before instrument access'
    for proc in psutil.process_iter(['name','cmdline']):
        a=[str(x).replace('\\','/') for x in proc.info.get('cmdline') or []]
        if any('physical_ramp_voltage_100x100_20261015/' in x and (x.endswith('/run_campaign.py') or x.endswith('/run_physical.py')) for x in a):
            raise RuntimeError('Main instrument process still running')
    target=HERE/'highres_campaign_status.json'
    if target.exists():raise FileExistsError(target)
    state=dict(started_utc=now(),complete=False,cases=[],scope='24 fixed-point GUI representatives, not identical full-sweep command stream')
    def save():target.write_text(json.dumps(state,indent=2),encoding='utf8')
    save()
    try:
        labels=[c['label'] for c in json.loads((HERE/'highres_preparation_resume_status.json').read_text())['cases']]
        assert len(labels)==24
        for label in labels:
            deadline=time.monotonic()+1200
            while True:
                prep_status=json.loads((HERE/'highres_preparation_resume_status.json').read_text())
                case=next(c for c in prep_status['cases'] if c['label']==label)
                if case['status']=='offline_prepared_and_reconstructed':break
                if prep_status.get('error') or time.monotonic()>deadline:raise RuntimeError('Highres preparation unavailable: '+label)
                time.sleep(1)
            bundle=Path(case['output_dir']);out=HERE/f'run_{label}_01';analysis=HERE/f'analysis_{label}_01'
            existing=out.exists()
            if not existing:
                with (HERE/f'{out.name}.log').open('xb') as log:
                    run=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'run_highres.py'),'--execute','--highres','--prepared',bundle.name,'--output',out.name],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                if run.returncode:raise RuntimeError('Highres capture failed: '+label)
            measured=json.loads((out/'status.json').read_text())
            assert measured['acquisition_success'] and measured['cleanup_zero'] and measured['scope_restore']['passed'] and not measured['production_sources_changed']
            if not analysis.exists():
                with (HERE/f'{analysis.name}.log').open('xb') as log:
                    result=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'analyze_highres.py'),'--prepared',bundle.name,'--run',out.name,'--output',analysis.name],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                if result.returncode:raise RuntimeError('Highres analysis failed: '+label)
            report=json.loads((analysis/'results.json').read_text())
            assert measured['prepared_bundle']==bundle.name
            assert report['prepared_bundle']==bundle.name and report['source_run']==out.name
            assert report['capture_id']==measured['capture_id'] and report['integrity_passed']
            row=dict(label=label,prepared=bundle.name,run=out.name,analysis=analysis.name,capture_id=measured['capture_id'],acquisition_success=True,cleanup_zero=True,scope_restore_passed=True,preexisting_success_preserved=existing,status='analyzed')
            state['cases'].append(row);save();print(json.dumps(row),flush=True)
        state['complete']=True;state['finished_utc']=now();save()
    except BaseException as exc:
        state['error']=repr(exc);state['finished_utc']=now();save();raise
if __name__=='__main__':main()
