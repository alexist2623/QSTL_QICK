"""Bind current GUI source to completed real RTL without rerunning xsim."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
from run_hold_validation import OUT,BUILD,CASES,COMMON,source_hashes

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    state=json.loads((OUT/'run_status.json').read_text(encoding='utf-8-sig'))
    assert state['complete'], 'Never replay or analyze a still-running simulator'
    dest=OUT/'current_gui_replay'
    dest.mkdir(exist_ok=False)
    current=source_hashes()
    report=dict(complete=False,started=time.time(),source_hashes=current,cases={},
        source_changes_since_prepare={p:dict(before=h,after=current.get(p))
            for p,h in state['source_hashes'].items() if current.get(p)!=h},
        sources_added_since_prepare={p:h for p,h in current.items() if p not in state['source_hashes']},
        simulator_rerun=False)
    path=dest/'result.json'
    path.write_text(json.dumps(report,indent=2))
    for name,config in CASES.items():
        source=Path(state['cases'][name]['folder'])
        previous=dest/name/'before'
        previous.mkdir(parents=True)
        for filename in ('pmem.hex','dmem.txt','gui_widget_pmem.hex','gui_widget_match.json',
                         'gui_input.json','gui_input.png','gui_compiled_timing.png','result.json'):
            shutil.copy2(source/filename,previous/filename)
        expected={filename:digest(source/filename) for filename in ('pmem.hex','dmem.txt')}
        command=COMMON+['--dc-mode',name,'--dc-readout-policy',config['policy'],
            '--run-tag',config['tag'],'--analyze-only']
        with (dest/f'{name}.log').open('w',encoding='utf-8') as stream:
            proc=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
        report['cases'][name]=dict(exit_code=proc.returncode,command=command,
            old_sha256=expected,new_sha256={filename:digest(source/filename) for filename in expected})
        path.write_text(json.dumps(report,indent=2))
        assert proc.returncode==0, name
        assert report['cases'][name]['new_sha256']==expected,'Current GUI changed executed PMEM/DMEM'
        for filename in ('gui_widget_match.json','gui_input.json','gui_input.png','gui_compiled_timing.png'):
            shutil.copy2(source/filename,dest/name/filename)
    assert source_hashes()==current,'Sources changed during replay'
    report.update(complete=True,finished=time.time())
    path.write_text(json.dumps(report,indent=2))
    print('Current GUI widget PMEM/DMEM byte-identical to both completed RTL snapshots; xsim not rerun.')

if __name__=='__main__':main()
