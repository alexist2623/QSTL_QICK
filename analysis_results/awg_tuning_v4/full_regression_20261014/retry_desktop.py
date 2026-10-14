"""Preserve and rerun only confirmed desktop setup/Qt teardown failures."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
GUI=ROOT.parent/'PulseGenerator'
VALID=ROOT/'qick/firmware/ip/axis_awg_tuning_v3/validation'
BASE=Path('F:/Vivado_Output/a4reg1')
state=json.loads((BASE/'status.json').read_text())
results={}
for stem in ('test_sparameter_phase_storage','test_trigger_output_panel'):
    name='gui_DCWaveformGeneratorGUI_'+stem
    first=state['stages'][name]
    assert first['state']=='failed'
    log=Path(first['log']).read_text(errors='replace')
    module=GUI/'DCWaveformGeneratorGUI'/(stem+'.py')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    if stem=='test_sparameter_phase_storage':
        assert '14 passed' in log and 'access violation' in log
        harness=VALID/'phase_storage_lifecycle.py'
        command=[sys.executable,'-X','utf8','-X','faulthandler',str(harness),str(module),'F:/Vivado_Output/a4reg_phase_retry_tmp']
        reason='All 14 assertions passed before Qt teardown access violation; explicitly own/destroy QApplication.'
    else:
        assert "No module named 'pynq'" in log
        harness=VALID/'retry_desktop_regressions.py'
        command=[sys.executable,'-X','utf8','-X','faulthandler',str(harness),
                 '--build',str(BASE),'--gui',str(GUI),'--worker',str(module),
                 '--basetemp','F:/Vivado_Output/a4reg_trigger_retry_tmp']
        reason='Initialize the existing qick.sim desktop bootstrap; no board imports/writes.'
    output=HERE/(stem+'.reviewed_retry.log')
    assert not output.exists()
    item=dict(first_attempt=first,command=command,reason=reason,
              module=str(module),module_sha256=sha(module),harness=str(harness),harness_sha256=sha(harness),
              log=str(output),state='running',started=time.time())
    results[name]=item
    (HERE/'desktop_retries.json').write_text(json.dumps(results,indent=2))
    with output.open('w',encoding='utf8') as stream:
        rc=subprocess.call(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
    assert sha(module)==item['module_sha256']
    item.update(state='passed' if rc==0 else 'failed',exit_code=rc,elapsed_s=time.time()-item['started'])
    (HERE/'desktop_retries.json').write_text(json.dumps(results,indent=2))
    print(stem,rc,flush=True)
raise SystemExit(0 if all(r['exit_code']==0 for r in results.values()) else 1)
