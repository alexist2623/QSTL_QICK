"""Apply only the eight verified feature files after successful v5 snapshot."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    state=read(HERE/'workflow_status.json')
    frozen=read(HERE/'successful_build_snapshot_v2/manifest.json')
    package=read(HERE/'rf_fine_duration/release_package/manifest.json')
    assert state['complete'] and state['stage']=='timing_passed_candidate_not_deployed'
    assert frozen['complete'] and package['software_verified'] and len(package['files'])==8
    evidence=HERE/'software_followup/fine_promotion'
    assert not evidence.exists(), 'Do not repeat promotion'
    for item in package['files']:
        assert sha(item['path'])==item['sha256']
        dest=Path(item['production_destination'])
        assert dest.parent==Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')
        old=item['expected_production_sha256']
        assert (sha(dest)==old if old else not dest.exists()), str(dest)
    evidence.mkdir(parents=True)
    for item in package['files']:
        dest=Path(item['production_destination'])
        if dest.exists(): shutil.copy2(dest,evidence/(dest.name+'.before'))
        shutil.copy2(item['path'],dest)
        assert sha(dest)==item['sha256']
    result=dict(promoted=True,time=datetime.datetime.now().astimezone().isoformat(),files=package['files'],
                original_snapshot=str(HERE/'successful_build_snapshot_v2/manifest.json'),
                production_verification_pending=True,board_access=False,live_gui_restarted=False)
    (evidence/'promotion.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('PROMOTED_VERIFIED_FINE_DURATION files=8 fresh_production_checks_pending=true')

if __name__=='__main__': main()
