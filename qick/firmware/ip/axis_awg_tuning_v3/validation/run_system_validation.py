"""Prepare serially in shared Vivado libraries, then run isolated real RTL.

This revision repeats all four system cases after the compensation lookahead
pipeline. Completed first-build evidence is kept in separate case directories.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

from report_system_validation import CASES, verified_source_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--gui', type=Path, required=True)
    parser.add_argument('--vivado', type=Path, default=Path('F:/Xilinx/Vivado/2023.1/bin'))
    parser.add_argument('--resume-preparation', action='store_true',
                        help='Resume a stopped preparation batch; refuses any started simulation.')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    verifier = here.parents[1]/'rc_precomp_validation/verify_gui_rtl.py'
    batch = args.build/'v3_scoped1_batch'
    if not args.resume_preparation:
        batch.mkdir(exist_ok=False)
        for folder in CASES.values():
            if (args.build/folder).exists():
                raise RuntimeError(f'Refusing duplicate/overwrite: {folder}')
    common = [sys.executable, '-X', 'utf8', '-X', 'faulthandler', str(verifier), '--build', str(args.build),
              '--gui', str(args.gui), '--vivado', str(args.vivado), '--awg-v3',
              '--repeat-reset', '--isolated-run', '--cross-capacitance', '1', '.23', '-.17', '1',
              '--dac-current-ma', '20', '10', '20']
    options = [
        ['--sweep-case', 'rf_duration', '--sweep-count', '10', '--dc-mode', 'fixed_voltage',
         '--dc-readout-policy', 'overlap_readout', '--stored-fir-samples', '4',
         '--verify-gui-widgets', '--run-tag', 'v3_scoped1_voltage_gui'],
        ['--sweep-case', 'rf_duration', '--sweep-count', '10', '--dc-mode', 'fixed_voltage',
         '--dc-readout-policy', 'overlap_readout', '--stored-fir-samples', '4',
         '--verify-gui-widgets', '--reverse-axes', '--run-tag', 'v3_scoped1_voltage_reverse'],
        ['--sweep-case', 'rf_duration_fixed', '--sweep-count', '10', '--dc-mode', 'fixed_time',
         '--dc-readout-policy', 'after_readout', '--stored-fir-samples', '4',
         '--verify-gui-widgets', '--run-tag', 'v3_scoped1_time_gui'],
        ['--no-aux', '--v2-fixture', 'stability', '--grid-count', '10', '--dc-mode', 'fixed_time',
         '--grid-x-mv', '-15', '15', '--grid-y-mv', '15', '-15', '--reverse-axes',
         '--run-tag', 'v3_scoped1_stability'],
    ]
    status = {'source_hashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (here.parent/'src').glob('*.sv')}, 'cases': {}}
    if args.resume_preparation:
        previous = json.loads((batch/'status.json').read_text())
        assert previous['source_hashes'] == status['source_hashes'], 'RTL changed since preparation'
        assert set(previous['cases']).issubset(CASES), 'Batch cases changed'
        for name, entry in previous['cases'].items():
            assert entry['stage'] == 'prepare' and entry['state'] in ('passed', 'failed'), \
                'Resume only a stopped preparation; never duplicate a running prepare or simulation'
            source = args.build/CASES[name]
            assert not (source/'result.json').exists() and not (source/'rtl_events.csv').exists(), \
                'RTL execution has already started'
            if entry['state'] == 'passed':
                verified_source_manifest(source, here.parents[4])
        archive = batch/f'preparation_failure_{time.time_ns()}'
        archive.mkdir()
        shutil.copy2(batch/'status.json', archive/'status.json')
        for index, name in enumerate(CASES):
            entry = previous['cases'].get(name)
            if entry and entry['state'] == 'failed':
                shutil.copytree(args.build/CASES[name], archive/CASES[name])
                shutil.copy2(batch/f'{index}_prepare.log', archive/f'{index}_prepare.log')
        status = previous
    lock = threading.Lock()
    def update(name, **data):
        with lock:
            status['cases'].setdefault(name, {}).update(data)
            (batch/'status.json').write_text(json.dumps(status, indent=2))
    def invoke(index, stage, extra):
        name = list(CASES)[index]
        command = common+options[index]+extra
        old = status['cases'].get(name)
        history = list(old.get('history', [])) if old else []
        if old:
            history.append({k: v for k, v in old.items() if k != 'history'})
        update(name, stage=stage, state='running', command=command, started=time.time(), history=history)
        logfile = batch/f'{index}_{stage}.log'
        if logfile.exists():
            logfile = batch/f'{index}_{stage}_{time.time_ns()}.log'
        update(name, log=str(logfile))
        with logfile.open('w', encoding='utf-8') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        update(name, state='passed' if result.returncode == 0 else 'failed',
               exit_code=result.returncode, finished=time.time())
        print(f'{name}: {stage} exit {result.returncode}', flush=True)
        return result.returncode == 0
    # xvlog/xelab mutate common simulation libraries: never prepare concurrently.
    for index in range(4):
        entry = status['cases'].get(list(CASES)[index], {})
        if args.resume_preparation and entry.get('state') == 'passed':
            continue
        if not invoke(index, 'prepare', ['--prepare-only']):
            raise SystemExit(1)
    with ThreadPoolExecutor(max_workers=4) as pool:
        passed = list(pool.map(lambda index: invoke(index, 'run', ['--reuse-snapshot']), range(4)))
    raise SystemExit(0 if all(passed) else 1)


if __name__ == '__main__':
    main()
