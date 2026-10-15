"""Audit authorized postbuild software against the immutable successful build."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GUI = Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')
LIB = Path('C:/GIT_Workspace/QSTL_QICK/qick/qick_lib/qick')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    assert not output.exists(), 'Use a fresh output; retain earlier audits'
    snapshot_path = ROOT/'successful_build_snapshot_v2/manifest.json'
    snapshot = read(snapshot_path)
    reasons = {
        GUI/'dc_waveform_core.py': 'Previously validated RF sample-duration feature promotion',
        GUI/'DCWaveform_Generator.py': 'Previously validated RF sample-duration editor promotion',
        GUI/'qick_fine_tune_sweep.py': 'RF sample-duration promotion; version-specific v5 conflict messages',
        GUI/'qick_qcodes_experiment.py': 'RF sample-duration promotion; version-specific v5 control messages',
        GUI/'qick_front_panel.py': 'Recognize sum-v2 shared/baseband output metadata',
        GUI/'qick_update.py': 'Offline validation of selected v5 firmware topology and provenance',
        LIB/'dac_current.py': 'Recognize verified v1/v2 shared-DAC hardware routes',
        LIB/'ip.py': 'Traverse sum-v2 hardware routes',
        LIB/'output_sum.py': 'Version/role-specific latency profile and reconfiguration',
    }
    additions = [GUI/x for x in (
        'qick_rf_fine_duration.py', 'test_rf_fine_duration_compiler.py',
        'test_rf_fine_duration_editor.py', 'test_rf_fine_duration_runtime.py',
        'test_output_sum_v5_gui.py', 'test_qick_update_v5.py')]
    additions.append(LIB/'test_output_sum.py')
    changes, unchanged, frozen = [], [], []
    preserved_names = {'workflow_status.json', 'candidate_manifest.json',
                       'prebuild_gate.json', 'prebuild_gate.log', 'postbuild_gate.log',
                       'compiler_equivalence.json', 'authorized_gui_fix.json',
                       'replays_status.json', 'selected48_status.json'}
    failures = []
    for record in snapshot['files']:
        saved = Path(record['snapshot'])
        if not saved.is_file() or sha(saved) != record['sha256']:
            failures.append(f'Snapshot changed: {saved}')
        source = Path(record['source'])
        production = (source.is_relative_to(GUI) or source.is_relative_to(LIB)
                      or '/firmware/' in source.as_posix())
        must_preserve = (source.name in preserved_names or
                         (source.suffix in ('.bit', '.hwh', '.xsa', '.xdc', '.rpt')))
        if production or must_preserve:
            current = sha(source) if source.is_file() else None
            if current != record['sha256']:
                if production and source in reasons:
                    changes.append(dict(path=str(source), before=record['sha256'],
                                        after=current, reason=reasons[source]))
                else:
                    failures.append(f'Unexpected change: {source}')
            else:
                unchanged.append(str(source))
                if must_preserve:
                    frozen.append(str(source))
    for source in additions:
        if not source.is_file():
            failures.append(f'Missing authorized addition: {source}')
    source_hashes = {str(p): sha(p) for p in sorted(set(GUI.glob('*.py')) |
                     set(LIB.rglob('*.py')))}
    result = dict(passed=not failures, checked=datetime.datetime.now().astimezone().isoformat(),
                  snapshot=str(snapshot_path), snapshot_files_verified=len(snapshot['files']),
                  authorized_existing_changes=changes,
                  authorized_additions={str(p): sha(p) for p in additions if p.is_file()},
                  unchanged_production_or_build_files=len(unchanged),
                  preserved_build_evidence=frozen, source_hashes=source_hashes,
                  failures=failures, board_access=False, firmware_deployed=False,
                  note='Historical build gates remain frozen; this audit describes authorized later software.')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('passed', 'snapshot_files_verified', 'failures')}))
    assert not failures, failures


if __name__ == '__main__':
    main()
