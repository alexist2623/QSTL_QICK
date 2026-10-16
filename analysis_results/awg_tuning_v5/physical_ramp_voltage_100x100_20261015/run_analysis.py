"""Sequential offline analyzer; never imports hardware runners or devices.

Consume completed physical-campaign records only. Preserve every run and
analysis attempt. A valid analysis may contain physical FAIL measurements;
process success is acquisition/analysis integrity, not waveform PASS.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def child(name):
    result = (HERE / name).resolve()
    if result.parent != HERE:
        raise ValueError('Use a direct child evidence directory')
    return result


def verify_analysis(folder, run):
    result = read(folder / 'results.json')
    manifest = read(folder / 'manifest.json')
    measured = read(run / 'status.json')
    assert result['analysis_complete'] and result['integrity_passed'] and result['input_hashes_unchanged']
    assert manifest['analysis_complete'] and manifest['input_hashes_unchanged']
    assert result['capture_id'] == measured['capture_id']
    for name, item in manifest['files'].items():
        assert sha(folder / name) == item['sha256'], name
    for path, digest in read(folder / 'input_hashes.json').items():
        assert sha(Path(path)) == digest, path
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-wait-seconds', type=float, default=7200.)
    args = parser.parse_args()
    target = HERE / 'analysis_campaign_status.json'
    if target.exists():
        raise FileExistsError('Preserve the original controller status; no implicit rerun')
    analyzer = HERE / 'analyze_physical.py'
    sources = {str(p): sha(p) for p in (Path(__file__), analyzer,
               HERE / 'model_review/command_expectation.py', HERE / 'model_review/compact_expectation.py')}
    state = dict(started_utc=now(), complete=False, instrument_access=False,
                 analyzer_source_hashes=sources, cases=[])

    def save():
        target.write_text(json.dumps(state, indent=2) + '\n', encoding='utf8')

    save()
    seen = set()
    deadline = time.monotonic() + args.max_wait_seconds
    try:
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError('Timed out waiting for completed physical cases')
            physical_path = HERE / 'physical_campaign_status.json'
            if not physical_path.exists():
                time.sleep(2)
                continue
            try:
                physical = read(physical_path)
            except json.JSONDecodeError:
                time.sleep(2)
                continue
            for case in physical['cases']:
                label = case['label']
                if label in seen:
                    continue
                assert all(sha(Path(p)) == digest for p, digest in sources.items()), 'Analyzer source changed'
                if case['status'] == 'range_rejected_not_run':
                    row = dict(label=label, status='range_rejected_not_run', physical_execution=False,
                               prepared=case['prepared'], error=case['error'])
                elif case['status'] == 'acquired':
                    run = child(case['run'])
                    measured = read(run / 'status.json')
                    assert measured['acquisition_success'] and measured['sweep_completed'] and measured['cleanup_zero']
                    assert measured['scope_restore']['passed'] and not measured['production_sources_changed']
                    output = child(f'analysis_{label}_01')
                    existed = output.exists()
                    if not existed:
                        with child(output.name + '.log').open('xb') as log:
                            process = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(analyzer),
                                '--prepared', case['prepared'], '--run', run.name, '--output', output.name],
                                cwd='C:/GIT_Workspace/QSTL_QICK', stdout=log, stderr=subprocess.STDOUT)
                        if process.returncode:
                            raise RuntimeError(f'{label}: analyzer exit {process.returncode}; original attempt retained')
                    result = verify_analysis(output, run)
                    row = dict(label=label, status='analyzed', integrity_passed=True,
                               physical_execution=True, prepared=case['prepared'], run=run.name,
                               analysis=output.name, reused_verified_existing=existed, capture_id=result['capture_id'],
                               active_primary_counts=result['active_primary_counts'], inactive_zero_counts=result['inactive_zero_counts'],
                               main_all_passed=result['overall_primary_passed'], dc=result['dc_diagnostics']['central_compensation'])
                else:
                    raise RuntimeError(f'Physical case is not valid for analysis: {label}: {case["status"]}')
                state['cases'].append(row)
                seen.add(label)
                save()
                print(json.dumps(row), flush=True)
            if physical.get('error'):
                raise RuntimeError('Physical controller stopped: ' + physical['error'])
            if physical.get('complete'):
                assert len(seen) == len(physical['cases']) == 48
                state['complete'] = True
                state['finished_utc'] = now()
                state['source_hashes_unchanged'] = all(sha(Path(p)) == h for p, h in sources.items())
                assert state['source_hashes_unchanged']
                save()
                return 0
            time.sleep(2)
    except BaseException as exc:
        state['error'] = repr(exc)
        state['finished_utc'] = now()
        save()
        raise


if __name__ == '__main__':
    raise SystemExit(main())
