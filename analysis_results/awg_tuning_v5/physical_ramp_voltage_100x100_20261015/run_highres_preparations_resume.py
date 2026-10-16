"""Offline 24-case GUI preparation, sequentially AFTER main Qt preparation ends.

No board or scope operations. First interrupted Qt attempt is preserved and is
not silently reused. A nonzero exit stops the batch and preserves all evidence.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import psutil

HERE=Path(__file__).resolve().parent
ROOT=Path('C:/GIT_Workspace/QSTL_QICK')
PYTHON=Path('C:/Users/Measurement2/.conda/envs/qcodes2/python.exe')
HELPER=HERE/'prepare_highres.py'
AUDIT=HERE/'audit_highres_prepared.py'
STATUS=HERE/'highres_preparation_resume_status.json'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def save(state):
    temporary=STATUS.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(state,indent=2),encoding='utf8');temporary.replace(STATUS)


def main_processes():
    found=[]
    for process in psutil.process_iter(['pid','name','cmdline','create_time']):
        try:
            info=process.info
            if not info['name'].lower().startswith('python'):continue
            args=[str(a).replace('\\','/') for a in info['cmdline'] or []]
            if any('physical_ramp_voltage_100x100_20261015/' in a and
                   (a.endswith('/run_preparations.py') or a.endswith('/prepare_program.py') or a.endswith('/prepare_main_resume.py') or a.endswith('/run_preparations_resume.py') or a.endswith('/resume_preparations.py') or a.endswith('/run_preparation_resume.py')) for a in args):
                found.append(info)
        except (psutil.NoSuchProcess,psutil.AccessDenied):continue
    return found


def cases():
    rows=[]
    for direction in ('rising','falling'):
        for active in (0,1):
            for ns in (10,500,1000):
                for voltage,sign in ((-400,'negative'),(400,'positive')):
                    label=f'highres_{direction}_dac{4+active}_duration{ns}ns_{sign}'
                    folder='offline_'+label
                    if direction=='rising' and active==0 and ns==10 and voltage<0:folder+='_retry01'
                    rows.append(dict(label=label,output_dir=str(HERE/folder),direction=direction,
                        active_axis=active,duration_us=ns/1000.,requested_mv=voltage,status='pending'))
    return rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--main-status',required=True);args=parser.parse_args()
    main_status=(HERE/args.main_status).resolve()
    if main_status.parent!=HERE or main_status.name=='preparation_batch_status.json':raise ValueError('Require a new merged main preparation status in this root')
    if STATUS.exists():raise FileExistsError('Existing controller status; refuse duplicate execution')
    state=dict(started=now(),controller_pid=os.getpid(),controller_create_time=psutil.Process().create_time(),
        helper_sha256=sha(HELPER),audit_sha256=sha(AUDIT),maximum_parallel=1,
        physical_execution=False,complete=False,status='waiting_for_main_resume_exit',main_status=str(main_status),cases=cases(),
        failed_attempts=[dict(bundle='offline_highres_rising_dac4_duration10ns_negative',exit_code=-1073741819,
            classification='Windows Qt access violation; cause not established; original folder/log/helper snapshot preserved')])
    save(state)
    try:
        while True:
            if not main_status.exists():
                time.sleep(5);continue
            main_state=json.loads(main_status.read_text())
            active=main_processes()
            if main_state.get('complete') and not active:break
            if main_state.get('finished') and not main_state.get('complete') and not active:
                raise RuntimeError('Main preparation ended with an unexpected failure; highres GUI remains unstarted')
            time.sleep(5)
        state['main_preparation_ended_before_highres']=dict(checked=now(),status_sha256=sha(main_status),
            controller_pid=main_state.get('controller_pid'),complete=True,matching_processes=[])
        state['status']='preparing';save(state)
        env=os.environ.copy()
        env.update(PYTHONPATH=';'.join(('C:/Users/Measurement2/AppData/Local/Temp/qick-v3-validation-deps',
            'C:/Users/Measurement2/AppData/Local/Temp/qick-waveform-time-axis-deps',
            'C:/GIT_Workspace/QSTL_QICK/qick/qick_lib','C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')),
            QT_QPA_PLATFORM='offscreen',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
        env['PATH']='C:/Users/Measurement2/.conda/envs/qcodes2/Library/bin;C:/Users/Measurement2/.conda/envs/qcodes2/DLLs;'+env['PATH']
        for case in state['cases']:
            assert sha(HELPER)==state['helper_sha256'] and sha(AUDIT)==state['audit_sha256'],'Frozen helper changed'
            assert not main_processes(),'Main GUI preparation restarted; do not overlap Qt preparation'
            destination=Path(case['output_dir'])
            if destination.exists():raise FileExistsError(destination)
            duration=str(case['duration_us']);voltage=str(case['requested_mv'])
            command=[str(PYTHON),'-B','-X','utf8',str(HELPER),'--mode','fixed_time','--hold-us','10',
                '--dc-time-us','10','--tau-us','20','--voltage-start-mv',voltage,'--voltage-stop-mv',voltage,
                '--dc-voltage-mv','300','--direction',case['direction'],'--active-output',str(case['active_axis']),
                '--duration-start-us',duration,'--duration-stop-us',duration,'--duration-count','1','--voltage-count','1',
                '--board-config',str(ROOT/'analysis_results/awg_tuning_v5/physical_voltage_2axis_20261015/board_config_191721.json'),
                '--current-settings',str(ROOT/'analysis_results/awg_tuning_v5/physical_voltage_2axis_20261015/dac_current_settings.json'),
                '--gen-channels','1','3','--full-scales-mv','801.48','801.48','--output-dir',str(destination)]
            log=HERE/('preparation_'+case['label']+'_serial.log')
            case.update(status='running',started=now(),command=command,log=str(log));save(state)
            with log.open('x',encoding='utf8') as stream:
                process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
                case['pid']=process.pid;case['process_create_time']=psutil.Process(process.pid).create_time();save(state)
                try:code=process.wait(timeout=120)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait();case['timed_out']=True;raise
            case['exit_code']=code
            if code!=0:
                case['status']='preparation_failed';save(state);raise RuntimeError(f'{case["label"]} exited {code}')
            audit_path=HERE/('audit_'+case['label']+'.json')
            audit_command=[str(PYTHON),'-B','-X','utf8',str(AUDIT),'--prepared',destination.name,'--output',audit_path.name]
            audit_log=HERE/('audit_'+case['label']+'.log')
            with audit_log.open('x',encoding='utf8') as stream:
                audited=subprocess.run(audit_command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=60)
            case.update(audit_exit_code=audited.returncode,audit_path=str(audit_path),audit_log=str(audit_log))
            if audited.returncode!=0:
                case['status']='reconstruction_failed';save(state);raise RuntimeError('Fresh highres reconstruction/model audit failed')
            m=json.loads((destination/'manifest.json').read_text());assert m['helper_sha256']==state['helper_sha256']
            assert all(sha(destination/name)==digest for name,digest in m['files'].items())
            case.update(status='offline_prepared_and_reconstructed',finished=now(),manifest_sha256=sha(destination/'manifest.json'),
                audit_sha256=sha(audit_path),summary=json.loads((destination/'preparation_summary.json').read_text()))
            save(state);print(case['label']+': prepared and reconstructed',flush=True)
        state.update(complete=True,status='passed',finished=now());save(state);return 0
    except BaseException as exc:
        state.update(status='stopped_after_failure',error=repr(exc),finished=now());save(state);raise


if __name__=='__main__':raise SystemExit(main())
