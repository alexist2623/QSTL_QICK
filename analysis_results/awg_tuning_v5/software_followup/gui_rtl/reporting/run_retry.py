import hashlib,json,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent; E=HERE.parent
old=json.loads((E/'suite2_status.json').read_text());case=old['cases']['hold_fixed_voltage'];assert case['exit_code']==1
cmd=case['command'][:];cmd[cmd.index('--run-tag')+1]='v5_post_hold_fixed_voltage_retry'
state=dict(complete=False,stage='running',command=cmd,original=dict(status=str(E/'suite2_status.json'),case=case),reason='Validation-only raw_same_timestamp.py reporting edit changed prepared source hash before simulation; original failure preserved. Fresh preparation and execution use stable same production source.',started=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
p=HERE/'hold_fixed_voltage_retry_status.json';assert not p.exists()
with (HERE/'hold_fixed_voltage_retry.log').open('w') as stream:
    child=subprocess.Popen(cmd,cwd='C:/GIT_Workspace/QSTL_QICK',stdout=stream,stderr=subprocess.STDOUT)
    state['pid']=child.pid;p.write_text(json.dumps(state,indent=2));code=child.wait()
state.update(complete=code==0,stage='passed' if code==0 else 'failed',exit_code=code,finished=time.strftime('%Y-%m-%dT%H:%M:%S%z'));p.write_text(json.dumps(state,indent=2));sys.exit(code)
