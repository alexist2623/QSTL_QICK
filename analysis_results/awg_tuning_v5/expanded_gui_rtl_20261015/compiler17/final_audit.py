"""Immutable pre/post RTL evidence and source checks; reads only tested files."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['before','after']);mode=ap.parse_args().mode
    out=HERE/f'rtl_integrity_{mode}.json';assert not out.exists()
    paths={Path(__file__),HERE/'run_all.ps1',HERE/'run_rtl_exec.py',HERE/'run_cpmg_rtl_exec.py'}
    expected={};cases=[];snapshots=[]
    for name in ('prepared.json','prepared_cpmg.json'):
        paths.add(HERE/name);prep=read(HERE/name);build=Path(prep['build'])
        for group in ('source_hashes','helper_hashes','template_sources'):
            for p,h in prep[group].items():expected[Path(p)]=h
        for case in prep['cases']:
            cases.append(case)
            for n,h in case['inputs'].items():expected[Path(case['folder'])/n]=h
        paths.update(Path(v) for v in re.findall(r'"([^"]+)"',(build/'template/sources.prj').read_text()))
        snapshot=list((build/'sim/xsim.dir/compiler17').rglob('*'))
        snapshots.extend(str(p) for p in snapshot if p.is_file())
        paths.update(p for p in snapshot if p.is_file())
    paths.update(expected)
    missing=[str(p) for p in paths if not p.is_file()];assert not missing,missing
    current={str(p):sha(p) for p in sorted(paths)}
    expected_diff=[str(p) for p,h in expected.items() if current[str(p)]!=h];assert not expected_diff,expected_diff
    differences=[];exit_codes=[];evidence={}
    if mode=='after':
        before=read(HERE/'rtl_integrity_before.json')['files']
        differences=[p for p in sorted(set(before)|set(current)) if before.get(p)!=current.get(p)]
        assert not differences,differences
        for state_name in ('rtl_status.json','cpmg_rtl_status.json'):
            state=read(HERE/state_name);assert state['complete'] and state['stage']=='passed'
            commands=state['command_exits'];assert len(commands)==len(state['cases']) and all(v['tool']=='xsim' and v['exit_code']==0 for v in commands)
            exit_codes.extend(commands);evidence[str(HERE/state_name)]=sha(HERE/state_name)
        for case in cases:
            folder=Path(case['folder']);result=read(folder/'result.json')
            assert result['passed'] and result['xsim_exit_code']==0
            for p in folder.iterdir():
                if p.is_file():evidence[str(p)]=sha(p)
        for folder in [HERE/'semantic_audit',*(HERE/c['original_case'] for c in cases)]:
            for p in folder.rglob('*'):
                if p.is_file():evidence[str(p)]=sha(p)
    result=dict(passed=True,mode=mode,checked=datetime.datetime.now().astimezone().isoformat(),files=current,
        file_count=len(current),snapshot_file_count=len(snapshots),snapshots=snapshots,
        prepared_expected_hash_checks=len(expected),differences=differences,expected_differences=expected_diff,
        case_count=len(cases),xsim_exit_codes=exit_codes,final_evidence_hashes=evidence,
        pmem_dmem_envelope_inputs_included=True,production_rtl_inputs_included=True,board_access=False)
    out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('passed','mode','file_count','snapshot_file_count','prepared_expected_hash_checks','case_count')}))

if __name__=='__main__':main()
