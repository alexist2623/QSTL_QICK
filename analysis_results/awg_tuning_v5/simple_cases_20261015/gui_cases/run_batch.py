"""Independent process per Qt case; original attempts are never replaced."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from prepare import cases, sha

HERE=Path(__file__).resolve().parent
PYTHON=Path('C:/Users/Measurement2/.conda/envs/qcodes2/python.exe')
env=dict(os.environ)
env['PYTHONPATH']=';'.join(('C:/Users/Measurement2/AppData/Local/Temp/qick-v3-validation-deps',
    'C:/Users/Measurement2/AppData/Local/Temp/qick-waveform-time-axis-deps',
    'C:/GIT_Workspace/QSTL_QICK/qick/qick_lib','C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI'))
env['QT_QPA_PLATFORM']='offscreen'
env['PATH']='C:/Users/Measurement2/.conda/envs/qcodes2/Library/bin;C:/Users/Measurement2/.conda/envs/qcodes2/DLLs;'+env['PATH']
started=time.time();rows=[]
selected=[c for c in cases() if len(sys.argv)==1 or c['name'] in sys.argv[1:]]
for case in selected:
    before=set(p for p in HERE.iterdir() if p.is_dir())
    log=HERE/f'batch_{case["name"]}_{time.time_ns()}.log'
    with log.open('w',encoding='utf8') as stream:
        result=subprocess.run([str(PYTHON),'-X','utf8','-X','faulthandler',str(HERE/'prepare.py'),case['name']],
            env=env,cwd='C:/GIT_Workspace/QSTL_QICK',stdout=stream,stderr=subprocess.STDOUT)
    new=set(p for p in HERE.iterdir() if p.is_dir())-before
    assert len(new)==1,new
    folder=new.pop()
    status=json.loads((folder/'result.json').read_text()) if (folder/'result.json').exists() else dict(status='process_failure')
    row=dict(name=case['name'],folder=str(folder),exit_code=result.returncode,log=str(log),log_sha256=sha(log),result=status)
    rows.append(row)
    (folder/'process_exit.json').write_text(json.dumps(row,indent=2),encoding='utf8')
    (HERE/'batch_status.json').write_text(json.dumps(dict(complete=False,cases=rows),indent=2),encoding='utf8')
    print(case['name'],result.returncode,status['status'],flush=True)
counts={s:sum(row['result']['status']==s for row in rows) for s in sorted({row['result']['status'] for row in rows})}
(HERE/'batch_status.json').write_text(json.dumps(dict(complete=True,cases=rows,status_counts=counts,
    elapsed_seconds=time.time()-started,helper_sha256=sha(HERE/'prepare.py'),batch_sha256=sha(__file__)),indent=2),encoding='utf8')
print(counts,flush=True)
