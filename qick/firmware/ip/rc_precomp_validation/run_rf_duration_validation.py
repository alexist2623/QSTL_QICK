"""Run revised short RF duration grids and both sides of the length limit."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

JOBS = (
    ('short_extend', 'rf_duration', 20, None),
    ('short_fixed', 'rf_duration_fixed', 20, None),
    ('limit_oneshot', 'rf_duration_fixed', 2, 'oneshot'),
    ('limit_periodic', 'rf_duration_fixed', 2, 'periodic'),
)
TAG = 'oneshot_v1'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--gui', type=Path, required=True)
    args = parser.parse_args()
    root = args.build / 'rf_duration_oneshot_v1'
    root.mkdir(exist_ok=True)
    manifest = root / 'status.json'
    if manifest.exists():
        raise SystemExit('Existing validation batch found; inspect it instead of starting duplicate runs.')
    states = {}

    def save():
        manifest.write_text(json.dumps(dict(updated_utc=datetime.now(timezone.utc).isoformat(),
                                            cases=states), indent=2))

    runner = Path(__file__).with_name('verify_gui_rtl.py')
    common = [sys.executable, str(runner), '--build', str(args.build), '--gui', str(args.gui),
              '--repeat-reset', '--isolated-run', '--run-tag', TAG]

    def simulate(label, command, out, boundary):
        with (root / f'{label}_run.log').open('w', encoding='utf-8') as log:
            completed = subprocess.run(command + ['--reuse-snapshot'], stdout=log, stderr=subprocess.STDOUT)
        result_path = out / 'result.json'
        result = json.loads(result_path.read_text()) if result_path.exists() else None
        passed = completed.returncode == 0 and result is not None
        if boundary == 'periodic' and completed.returncode == 2 and result is not None:
            passed = result['validation_status'] == 'completed_with_timing_findings'
        return completed.returncode, passed, result

    save()
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {}
        for label, case, count, boundary in JOBS:
            name = f'rc_precomp_repeat_reset_{case}_{count}x{count}'
            if boundary:
                name += '_boundary_' + boundary
            out = args.build / (name + '_' + TAG)
            command = common + ['--sweep-case', case, '--sweep-count', str(count)]
            if boundary:
                command += ['--rf-length-boundary', boundary]
            states[label] = dict(status='preparing', output=str(out), points=count*count, repetitions=2)
            save()
            print(f'PREPARE {label}', flush=True)
            with (root / f'{label}_prepare.log').open('w', encoding='utf-8') as log:
                prepared = subprocess.run(command + ['--prepare-only'], stdout=log, stderr=subprocess.STDOUT)
            if prepared.returncode:
                states[label]['status'] = 'prepare_failed'
                save()
                continue
            shutil.copy2(args.gui / 'DCWaveformGeneratorGUI/qick_fine_tune_sweep.py', out / 'gui_compiler_source.py')
            futures[pool.submit(simulate, label, command, out, boundary)] = label
            states[label]['status'] = 'running'
            save()
            print(f'RUNNING {label}', flush=True)
        for future in as_completed(futures):
            label = futures[future]
            returncode, passed, result = future.result()
            states[label].update(status='passed' if passed else 'failed', returncode=returncode)
            if result:
                states[label]['rf_measurements'] = result['rf_measurements']
                states[label]['validation_status'] = result['validation_status']
            save()
            print(f'{states[label]["status"].upper()} {label}', flush=True)
    if not all(state['status'] == 'passed' for state in states.values()):
        raise SystemExit(1)
    print('Short RF length and whole-axis periodic fallback checks passed.', flush=True)


if __name__ == '__main__':
    main()
