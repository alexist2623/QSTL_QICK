"""Compile sequentially, then run independent real RTL snapshots concurrently."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

CASES=('ramp_rate','hold_duration','rf_duration','rf_duration_fixed',
       'rf_frequency','rf_power','rf_frequency_power')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--gui',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=7)
    parser.add_argument('--cases',nargs='+',choices=CASES,default=list(CASES))
    args=parser.parse_args()
    root=args.build/'sweep_matrix_20x20'
    root.mkdir(exist_ok=True)
    states={case:dict(status='pending') for case in CASES}
    manifest=root/'status.json'
    if manifest.exists():
        states.update(json.loads(manifest.read_text())['cases'])
    for case in args.cases:
        states[case]=dict(status='pending')

    def save():
        manifest.write_text(json.dumps(dict(updated_utc=datetime.now(timezone.utc).isoformat(),
            grid=[20,20],repetitions=2,cases=states),indent=2))

    runner=Path(__file__).with_name('verify_gui_rtl.py')
    common=[sys.executable,str(runner),'--build',str(args.build),'--gui',str(args.gui),
            '--repeat-reset','--sweep-count','20','--isolated-run']

    def simulate(case):
        with (root/f'{case}_run.log').open('w',encoding='utf-8') as log:
            result=subprocess.run(common+['--sweep-case',case,'--reuse-snapshot'],stdout=log,stderr=subprocess.STDOUT)
        output=args.build/f'rc_precomp_repeat_reset_{case}_20x20'/'result.json'
        validation=json.loads(output.read_text()).get('validation_status') if output.is_file() else None
        return result.returncode,output.is_file(),validation

    save()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={}
        for case in args.cases:
            states[case]=dict(status='preparing');save()
            print(f'PREPARE {case}',flush=True)
            with (root/f'{case}_prepare.log').open('w',encoding='utf-8') as log:
                prepared=subprocess.run(common+['--sweep-case',case,'--prepare-only'],stdout=log,stderr=subprocess.STDOUT)
            if prepared.returncode:
                states[case]=dict(status='prepare_failed',returncode=prepared.returncode)
                save();print(f'PREPARE FAILED {case}',flush=True)
                continue
            futures[pool.submit(simulate,case)]=case
            states[case]=dict(status='running');save()
            print(f'RUNNING {case}',flush=True)
        for future in as_completed(futures):
            case=futures[future]
            returncode,has_result,validation=future.result()
            status='failed'
            if has_result and returncode==0 and validation=='passed':status='passed'
            elif has_result and returncode==2 and validation=='completed_with_timing_findings':status=validation
            states[case]=dict(status=status,
                             returncode=returncode,result_present=has_result)
            save();print(f'{states[case]["status"].upper()} {case}',flush=True)
    if not all(state['status']=='passed' for state in states.values()):
        raise SystemExit(1)
    print('ALL 7 MIXED SWEEP CASES PASSED: 20 x 20 x 2 each',flush=True)


if __name__=='__main__':main()
