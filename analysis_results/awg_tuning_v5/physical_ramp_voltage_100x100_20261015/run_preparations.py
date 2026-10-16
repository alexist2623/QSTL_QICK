"""Offline-only batch: actual GUI preparation in isolated bounded subprocesses.

No instruments. Existing complete first bundle is verified, never overwritten.
Only the explicit production RC range rejection is an expected nonexecuted case.
"""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path('C:/GIT_Workspace/QSTL_QICK')
HERE=Path(__file__).resolve().parent
PYTHON=Path('C:/Users/Measurement2/.conda/envs/qcodes2/python.exe')
HELPER=HERE/'prepare_program.py'
FIRST_HELPER='7d32c3b91d59bcc004f6dc2f4bc55a2d794c274d6ba74f797c7968c242f2a3ef'
EXPECTED_HELPER='f282b6b9f99079f499645c149e86063fe35983a780f30244beb4366d51b1454d'
STATUS=HERE/'preparation_batch_status.json'

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def save(value):
    temporary=STATUS.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(value,indent=2),encoding='utf8')
    temporary.replace(STATUS)

def cases():
    result=[]
    # Complete safe candidates first; preserve all tau10 guard rejections later.
    for tau in (20,30,10):
        for direction in ('rising','falling'):
            for active in (0,1):
                for mode,dc_time in (('fixed_time',10),('fixed_time',20),('fixed_time',30),('fixed_voltage',10)):
                    mode_label=mode+str(dc_time) if mode=='fixed_time' else mode
                    label=f'{direction}_dac{4+active}_{mode_label}_tau{tau}'
                    result.append(dict(label=label,output_dir=str(HERE/f'offline_{label}'),
                        log=str(HERE/f'preparation_{label}.log'),direction=direction,
                        active_output=active,mode=mode,dc_time_us=dc_time,tau_us=tau,status='pending'))
    return result

def run_case(case):
    if sha(HELPER)!=EXPECTED_HELPER: raise RuntimeError('Frozen main helper changed')
    destination=Path(case['output_dir'])
    if destination.exists():
        # Only the already completed first bundle may be reused, with every hash.
        if case['label']!='rising_dac4_fixed_time10_tau20':
            raise FileExistsError(destination)
        manifest=json.loads((destination/'manifest.json').read_text())
        assert manifest['status']=='offline_prepared' and manifest['helper_sha256']==FIRST_HELPER
        assert manifest['points']==10000 and manifest['sweep_shape']==[100,100]
        assert all(sha(destination/name)==digest for name,digest in manifest['files'].items())
        return dict(status='offline_prepared',exit_code=0,reused_verified_first=True,
                    summary=json.loads((destination/'preparation_summary.json').read_text()))
    argv=[str(PYTHON),'-X','utf8',str(HELPER),'--mode',case['mode'],
          '--hold-us','10','--dc-time-us',str(case['dc_time_us']),'--tau-us',str(case['tau_us']),
          '--voltage-start-mv','-400','--voltage-stop-mv','400','--dc-voltage-mv','300',
          '--direction',case['direction'],'--active-output',str(case['active_output']),
          '--board-config',str(ROOT/'analysis_results/awg_tuning_v5/physical_voltage_2axis_20261015/board_config_191721.json'),
          '--current-settings',str(ROOT/'analysis_results/awg_tuning_v5/physical_voltage_2axis_20261015/dac_current_settings.json'),
          '--gen-channels','1','3','--full-scales-mv','801.48','801.48','--output-dir',str(destination)]
    env=os.environ.copy()
    env.update(PYTHONPATH=';'.join(('C:/Users/Measurement2/AppData/Local/Temp/qick-v3-validation-deps',
        'C:/Users/Measurement2/AppData/Local/Temp/qick-waveform-time-axis-deps',
        'C:/GIT_Workspace/QSTL_QICK/qick/qick_lib','C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')),
        QT_QPA_PLATFORM='offscreen',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
    env['PATH']='C:/Users/Measurement2/.conda/envs/qcodes2/Library/bin;C:/Users/Measurement2/.conda/envs/qcodes2/DLLs;'+env['PATH']
    with Path(case['log']).open('x',encoding='utf8') as log:
        completed=subprocess.run(argv,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    result=dict(exit_code=completed.returncode,command=argv,physical_execution=False)
    if completed.returncode==0:
        manifest=json.loads((destination/'manifest.json').read_text())
        assert manifest['status']=='offline_prepared' and manifest['helper_sha256']==EXPECTED_HELPER
        assert manifest['points']==10000 and manifest['sweep_shape']==[100,100]
        assert all(sha(destination/name)==digest for name,digest in manifest['files'].items())
        result.update(status='offline_prepared',summary=json.loads((destination/'preparation_summary.json').read_text()))
    else:
        failure=json.loads((destination/'preparation_failure.json').read_text())
        # No assertion/model/environment failure is silently classified as a range rejection.
        expected=(failure['error_type']=='ValueError' and case['tau_us']==10
                  and 'RC-compensated DAC output' in failure['error']
                  and 'exceeds' in failure['error'])
        result.update(status='range_rejected_not_executed' if expected else 'unexpected_failure',failure=failure)
    return result

def main():
    if STATUS.exists(): raise FileExistsError('Refuse duplicate controller; inspect existing status/process')
    state=dict(started=now(),controller_pid=os.getpid(),helper_sha256=EXPECTED_HELPER,
               production_changes=False,physical_execution=False,maximum_parallel=2,
               complete=False,cases=cases())
    save(state)
    pending=iter(state['cases']); running={}; stop=False
    with ThreadPoolExecutor(max_workers=2) as pool:
        while True:
            while not stop and len(running)<2:
                try: case=next(pending)
                except StopIteration: break
                case.update(status='running',started=now());save(state)
                running[pool.submit(run_case,case)]=case
            if not running: break
            done,_=wait(running,return_when=FIRST_COMPLETED)
            for future in done:
                case=running.pop(future)
                try: case.update(future.result())
                except BaseException as exc:
                    case.update(status='unexpected_failure',error_type=type(exc).__name__,error=str(exc))
                case['finished']=now()
                print(f"{case['label']}: {case['status']}",flush=True)
                if case['status']=='unexpected_failure': stop=True
                save(state)
    state.update(finished=now(),complete=not stop,status='finished' if not stop else 'stopped_after_unexpected_failure',
                 offline_prepared=sum(c['status']=='offline_prepared' for c in state['cases']),
                 range_rejected=sum(c['status']=='range_rejected_not_executed' for c in state['cases']))
    save(state)
    return 1 if stop else 0

if __name__=='__main__': sys.exit(main())
