"""Run completed snapshots, then build v4 only after every functional gate passes."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=ROOT/'analysis_results/awg_tuning_v4'
VALIDATION=ROOT/'qick/firmware/ip/axis_output_sum_v1/validation'


def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True)
    p.add_argument('--simulation-build',type=Path,default=Path('F:/Vivado_Output/a3sim1'))
    p.add_argument('--full-build',type=Path,default=Path('F:/Vivado_Output/a4full1'))
    a=p.parse_args()
    # Exclusive marker prevents accidentally starting a second orchestrator.
    lock=OUT/(a.tag+'_workflow.lock')
    with lock.open('x') as stream:stream.write(str(os.getpid()))
    state=dict(complete=False,stage='starting',pid=os.getpid(),tag=a.tag,
               full_build=str(a.full_build),started_utc=datetime.now(timezone.utc).isoformat())
    def save():
        state['updated_utc']=datetime.now(timezone.utc).isoformat()
        (OUT/'workflow_status.json').write_text(json.dumps(state,indent=2))
    def run(stage,command):
        state['stage']=stage;save()
        with (OUT/(stage+'.log')).open('w',encoding='utf8') as log:
            code=subprocess.call(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        state['exit_code']=code;save()
        if code:raise RuntimeError(f'{stage} failed with exit {code}; inspect {stage}.log')
    python=[sys.executable,'-X','utf8']
    try:
        assert not a.full_build.exists(), 'Full-build directory already exists; do not duplicate a build'
        prepared=json.loads((OUT/(a.tag+'_status.json')).read_text())
        assert len(prepared['cases'])==5 and all(c['state']=='prepared' for c in prepared['cases'].values())
        run('system_run',python+[str(VALIDATION/'run_system.py'),'--build',str(a.simulation_build),
                                '--tag',a.tag,'--workers','3','--reuse'])
        run('system_report',python+[str(VALIDATION/'report_system.py'),'--tag',a.tag])
        run('prebuild_check',python+[str(HERE/'validate_scope.py'),'--require-functional'])
        run('full_build',['F:/Xilinx/Vivado/2023.1/bin/vivado.bat','-mode','batch','-notrace',
            '-source',str(HERE/'build_vivado_2023_1.tcl'),'-log',str(a.full_build)+'_build.log',
            '-journal',str(a.full_build)+'_build.jou','-tclargs',str(a.full_build)])
        run('publish',python+[str(HERE/'publish_build.py'),str(a.full_build)])
        state.update(complete=True,stage='published',exit_code=0);save()
        (OUT/'BUILD_COMPLETE.md').write_text(
            '# AWG Tuning v4 build complete\n\n'
            'All five GUI/RTL cases and routed timing checks passed. '
            'The v4 BIT/HWH/XSA were extracted from the same successful XSA.\n\n'
            f'Firmware: `{HERE}`\n\n'
            'See build_manifest.json and system_summary.json for measured evidence. '
            'AWG pre-IIR compensation does not cancel added DDS area or final clipping. '
            'No on-board analog measurement has been performed.\n',encoding='utf8')
    except Exception as exc:
        state.update(complete=False,stage='failed',error=str(exc));save();raise
    # Keep the marker as execution provenance; a retry uses a new tag/build.


if __name__=='__main__':main()
