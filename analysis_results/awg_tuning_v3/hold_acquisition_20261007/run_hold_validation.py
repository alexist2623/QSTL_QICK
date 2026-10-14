"""Actual GUI widget -> PMEM/DMEM -> isolated Verilog hold sweep checks."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
GUI=Path('C:/GIT_Workspace/PulseGenerator')
BUILD=Path('F:/Vivado_Output/a3sim1')
VERIFIER=ROOT/'qick/firmware/ip/rc_precomp_validation/verify_gui_rtl.py'
CASES={
    'fixed_voltage':dict(policy='overlap_readout',tag='v3_hold_20261007_voltage'),
    'fixed_time':dict(policy='after_readout',tag='v3_hold_20261007_time'),
}
COMMON=[sys.executable,'-X','utf8','-X','faulthandler',str(VERIFIER),
    '--build',str(BUILD),'--gui',str(GUI),'--vivado','F:/Xilinx/Vivado/2023.1/bin',
    '--awg-v3','--repeat-reset','--isolated-run','--cross-capacitance','1','.23','-.17','1',
    '--dac-current-ma','20','10','20','--sweep-case','hold_duration','--sweep-count','10',
    '--stored-fir-samples','4','--verify-gui-widgets']

def source_hashes():
    sources=list((GUI/'DCWaveformGeneratorGUI').glob('*.py'))
    sources+=list((ROOT/'qick/qick_lib/qick').glob('*.py'))
    sources+=list((ROOT/'qick/firmware/ip/axis_awg_tuning_v3/src').glob('*.sv'))
    sources+=[VERIFIER, ROOT/'qick/firmware/ip/axis_awg_tuning_v3/validation/gui_widget_fixture.py']
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)}

def main():
    status_path=OUT/'run_status.json'
    if status_path.exists():raise RuntimeError('Refuse duplicate validation batch')
    status=dict(started=time.time(),cases={},source_hashes=source_hashes(),complete=False)
    lock=threading.Lock()
    def update(name,**values):
        with lock:
            if values.get('state')=='running':
                previous=status['cases'].get(name,{})
                if previous:
                    status.setdefault('stage_history',{}).setdefault(name,[]).append(dict(previous))
                for stale in ('exit_code','finished'):
                    previous.pop(stale,None)
            status['cases'].setdefault(name,{}).update(values)
            status_path.write_text(json.dumps(status,indent=2),encoding='utf-8')
    def invoke(name,stage):
        config=CASES[name]
        folder='rc_precomp_repeat_reset_hold_duration_'+config['tag']+'_'+config['policy']+'_awg_v3'
        command=COMMON+['--dc-mode',name,'--dc-readout-policy',config['policy'],'--run-tag',config['tag']]
        command+=['--prepare-only'] if stage=='prepare' else ['--reuse-snapshot']
        if stage=='prepare' and (BUILD/folder).exists():raise RuntimeError(f'Refuse overwrite: {folder}')
        update(name,stage=stage,state='running',started=time.time(),command=command,folder=str(BUILD/folder))
        with (OUT/f'{name}_{stage}.log').open('w',encoding='utf-8') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
        values=dict(state='passed' if result.returncode==0 else 'failed',exit_code=result.returncode,finished=time.time())
        prepared=BUILD/folder/'prepared.json'
        if prepared.exists():values['prepared']=json.loads(prepared.read_text())
        update(name,**values)
        print(f'{name} {stage}: exit={result.returncode}, prepared={values.get("prepared")}',flush=True)
        return result.returncode==0
    for name in CASES:
        if not invoke(name,'prepare'):raise SystemExit(1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        passes=list(pool.map(lambda name:invoke(name,'run'),CASES))
    status.update(complete=all(passes),finished=time.time())
    status_path.write_text(json.dumps(status,indent=2),encoding='utf-8')
    raise SystemExit(0 if all(passes) else 1)

if __name__=='__main__':main()
