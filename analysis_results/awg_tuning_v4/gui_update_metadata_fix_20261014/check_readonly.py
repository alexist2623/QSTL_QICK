"""Read-only local package review and board installation-metadata check."""
import ast, json, os, sys, hashlib, shlex
from pathlib import Path
from datetime import datetime, timezone
import qick_update as update
import qick_update_remote as remote
out=Path(__file__).resolve().parent
repo=Path('C:/GIT_Workspace/QSTL_QICK')
gui=Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')
review=update.review_package(repo, repo/'qick/firmware/projects/qstl_awg_v4/build_manifest.json')
remote.validate_manifest(review['manifest'])
assert all(n.startswith('qick_lib/qick/') or n in ('firmware/bitstream.bit','firmware/bitstream.hwh') for n in review['files'])
assert all('.egg-info' not in n for n in review['files'])
helper=(gui/'qick_update_remote.py').read_text(encoding='utf-8')
ast.parse(helper,feature_version=(3,8))
code="namespace = {'__name__': 'readonly_metadata_check'}\nexec("+repr(helper)+", namespace)\n"
code+="import json, sys\nfrom pathlib import Path\n"
code+="state=namespace['installation_state'](Path('/home/QSTL_QICK'), "+repr(review['manifest']['installation_contract'])+")\n"
code+="print(json.dumps({'python':sys.version, 'installation':state}))\n"
connection=update.UpdateConnection(host='192.168.2.99',password=os.environ.pop('QICK_BROWSE_TEST_PASSWORD'))
with update.BoardUpdater(connection) as board:
    command=shlex.quote(connection.python)+' -B -'
    stdin,stdout,stderr=board.client.exec_command(command,timeout=30)
    stdin.write(code);stdin.flush();stdin.channel.shutdown_write()
    result_text=stdout.read().decode();error=stderr.read().decode();status=stdout.channel.recv_exit_status()
    assert status==0,(status,error,result_text)
    observed=json.loads(result_text)
    assert observed['installation']['contract']==review['manifest']['installation_contract']
    assert observed['installation']['egg_info'] and observed['installation']['egg_links']
result={'passed':True,'checked_utc':datetime.now(timezone.utc).isoformat(),
        'local_review':{key:review[key] for key in ('identity','file_count','total_bytes','setup_wns_ns','hold_whs_ns')},
        'format':review['manifest']['format'],'library_scope':review['manifest']['library_scope'],
        'installation_contract':review['manifest']['installation_contract'], 'board':observed,
        'board_helper_exit_code':status, 'python38_syntax_pass':True,
        'board_reads_only':True,'upload':False,'replacement':False,'pip_install_on_board':False,
        'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [gui/'qick_update.py',gui/'qick_update_remote.py',gui/'qick_update_dialog.py']}}
(out/'local_and_board_metadata.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
