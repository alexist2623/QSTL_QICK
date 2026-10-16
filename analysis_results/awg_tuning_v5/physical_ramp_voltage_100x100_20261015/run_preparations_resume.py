"""Resume only pending offline cases after a reviewed SIP teardown retry."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
STATUS=HERE/'preparation_resume_status.json'
MERGED=HERE/'preparation_merged_status.json'
OLD=HERE/'preparation_batch_status.json'
COMPARISON=HERE/'preparation_resume_retry_comparison.json'
RESUME_SHA='f522ff161f6a75a423e84163185ba2ba7f2b73d1bd3c402f7f6b13d54319ceb8'
RETRY_LABEL='rising_dac5_fixed_voltage_tau30'

spec=importlib.util.spec_from_file_location('frozen_original_batch',HERE/'run_preparations.py')
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
original.HELPER=HERE/'prepare_main_resume.py'
original.EXPECTED_HELPER=RESUME_SHA

def now(): return datetime.now(timezone.utc).isoformat()
def save(state):
    temporary=STATUS.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(state,indent=2),encoding='utf8')
    temporary.replace(STATUS)

def verify_bundle(path):
    path=Path(path)
    manifest=json.loads((path/'manifest.json').read_text())
    assert manifest['status']=='offline_prepared' and manifest['points']==10000
    assert manifest['production_sources_unchanged'] and not manifest['physical_execution']
    assert all(original.sha(path/name)==digest for name,digest in manifest['files'].items())
    before=json.loads((path/'source_before.json').read_text())
    assert before==json.loads((path/'source_after.json').read_text())
    return before

def main():
    if STATUS.exists() or MERGED.exists():
        raise FileExistsError('Refuse duplicate resume controller or overwriting final evidence')
    assert original.sha(HERE/'prepare_main_resume.py')==RESUME_SHA
    old=json.loads(OLD.read_text())
    assert old['status']=='stopped_after_unexpected_failure' and old['offline_prepared']==25
    comparison=json.loads(COMPARISON.read_text())
    assert comparison['status']=='passed' and comparison['retry_exit_code']==0
    assert comparison['all_pmem_dmem_identical'] and comparison['uncompressed_expected_points_identical']
    assert comparison['uncompressed_model_events_identical']
    cases=copy.deepcopy(old['cases']); baselines=[]
    for case in cases:
        if case['status']=='offline_prepared':
            baselines.append(verify_bundle(case['output_dir']))
            case['reused_verified_exit0_bundle']=True
        elif case['label']==RETRY_LABEL:
            assert case['status']=='unexpected_failure'
            retry=HERE/'offline_rising_dac5_fixed_voltage_tau30_retry01'
            baselines.append(verify_bundle(retry))
            case.update(original_attempt_status=case['status'],status='offline_prepared',
                        exit_code=0,reviewed_retry_output_dir=str(retry),
                        successful_preparation_output_dir=str(retry),
                        retry_comparison=str(COMPARISON),
                        summary=json.loads((retry/'preparation_summary.json').read_text()))
        else:
            assert case['status']=='pending',case
            assert not Path(case['output_dir']).exists(),case
    assert len(baselines)==26 and all(item==baselines[0] for item in baselines)
    assert all(original.sha(path)==digest for path,digest in baselines[0].items())
    state=dict(started=now(),controller_pid=os.getpid(),complete=False,
        frozen_original_status_sha256=original.sha(OLD),original_status=str(OLD),
        retry_comparison=str(COMPARISON),retry_comparison_sha256=original.sha(COMPARISON),
        helper_sha256=RESUME_SHA,maximum_parallel=2,
        reused_exit0_count=25,reviewed_retry_count=1,pending_at_start=22,
        source_files_verified_unchanged=len(baselines[0]),
        physical_execution=False,cases=cases)
    save(state)
    pending=iter(case for case in cases if case['status']=='pending')
    running={};stop=False
    with ThreadPoolExecutor(max_workers=2) as pool:
        while True:
            while not stop and len(running)<2:
                try: case=next(pending)
                except StopIteration: break
                case.update(status='running',started=now());save(state)
                running[pool.submit(original.run_case,case)]=case
            if not running: break
            done,_=wait(running,return_when=FIRST_COMPLETED)
            for future in done:
                case=running.pop(future)
                try: case.update(future.result())
                except BaseException as exc:
                    case.update(status='unexpected_failure',error_type=type(exc).__name__,error=str(exc))
                case['finished']=now()
                print(f"{case['label']}: {case['status']}",flush=True)
                if case['status']=='unexpected_failure': stop=True
                save(state)
    assert original.sha(OLD)==state['frozen_original_status_sha256']
    assert all(original.sha(path)==digest for path,digest in baselines[0].items())
    prepared=sum(case['status']=='offline_prepared' for case in cases)
    rejected=sum(case['status']=='range_rejected_not_executed' for case in cases)
    if not stop: assert prepared==32 and rejected==16,(prepared,rejected)
    state.update(finished=now(),complete=not stop,
        status='finished' if not stop else 'stopped_after_unexpected_failure',
        offline_prepared=prepared,range_rejected=rejected)
    save(state)
    MERGED.write_text(json.dumps(state,indent=2),encoding='utf8')
    return 1 if stop else 0

if __name__=='__main__': sys.exit(main())
