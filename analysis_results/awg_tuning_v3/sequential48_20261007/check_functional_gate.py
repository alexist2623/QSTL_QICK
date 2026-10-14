"""Offline negative evidence checks. Existing results and sources are never edited."""
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

repo = Path('C:/GIT_Workspace/QSTL_QICK')
root = repo/'analysis_results/awg_tuning_v3'
path = repo/'qick/firmware/projects/qstl_awg_v3/publish_build.py'
spec = importlib.util.spec_from_file_location('publisher', path)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
original_read = Path.read_text
results = []
evidence = publisher.validate_functional_evidence(repo)
results.append(dict(name='current_completed_evidence', passed=True, evidence_count=len(evidence)))


def reject(name, relative, mutate=None, missing=False):
    target = (root/relative).resolve()
    def changed_read(current, *args, **kwargs):
        text = original_read(current, *args, **kwargs)
        if current.resolve() == target:
            if missing:
                raise FileNotFoundError('Synthetic missing evidence')
            data = json.loads(text)
            mutate(data)
            return json.dumps(data)
        return text
    try:
        with patch.object(Path, 'read_text', changed_read):
            publisher.validate_functional_evidence(repo)
    except (AssertionError, RuntimeError, KeyError, FileNotFoundError) as error:
        results.append(dict(name=name, passed=True, rejected_as=type(error).__name__))
    else:
        raise AssertionError('Evidence guard accepted '+name)


reject('missing_selected48_result', 'selected48_validation/width_results.json', missing=True)
reject('incomplete_selected48', 'selected48_validation/width_results.json', lambda d: d.update(complete=False))
reject('selected48_nonzero_residual', 'selected48_validation/width_results.json',
       lambda d: d['widths']['48'].update(max_residual_effective_code_samples=1))
reject('selected48_overflow', 'selected48_validation/width_results.json',
       lambda d: d['widths']['48'].update(overflow_points=1))
reject('wrong_width', 'selected48_validation/width_results.json', lambda d: d.update(selected_width=64))
reject('stale_area_source', 'selected48_validation/rtl_source_manifest.json',
       lambda d: d['repository_sources'][0].update(sha256='0'*64))
reject('regular_failed_stage', 'regular_validation/status.json',
       lambda d: d['stages']['tb_dc_area'].update(state='failed',exit_code=1))
reject('missing_regular_stage', 'regular_validation/status.json', lambda d: d['stages'].pop('tb_dc_boundaries'))
reject('stale_compiler', 'compiler_replay2/source_hashes.json', lambda d: d.update({next(iter(d)):'0'*64}))
reject('mismatched_replayed_PMEM', 'compiler_replay2/result.json',
       lambda d: next(iter(d['cases'].values())).update(pmem_sha256='0'*64))
reject('incomplete_system', 'system_validation/status.json', lambda d: d.update(complete=False))
reject('command_timing_error', 'system_validation/status.json',
       lambda d: next(iter(d['cases'].values()))['result'].update(command_timing_mismatches=1))
publisher.validate_functional_evidence(repo)
out = dict(complete=True, synthetic_offline_guard_checks=True, production_results_edited=False,
           publisher_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), checks=results)
(root/'sequential48_20261007/functional_gate_check.json').write_text(json.dumps(out,indent=2))
print(json.dumps(dict(passed=len(results),total=len(results),real_evidence_unchanged=True)))
