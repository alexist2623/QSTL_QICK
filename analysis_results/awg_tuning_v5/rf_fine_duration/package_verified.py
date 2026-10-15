"""Preserve reviewed fine-duration source without changing the live GUI tree."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
GUI = Path('F:/Vivado_Output/a5fine_sw/DCWaveformGeneratorGUI')
PRODUCTION = Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    baseline = json.loads((HERE/'before_manifest.json').read_text(encoding='utf-8-sig'))
    tested = json.loads((HERE/'release/result.json').read_text(encoding='utf-8-sig'))
    assert tested['passed'] and tested['tests'] == 680 and tested['coarse_cases'] == 9
    assert all(sha(path) == digest.lower() for path, digest in tested['source_hashes'].items())
    before = {Path(path).name: digest.lower() for path, digest in baseline['source_hashes'].items()}
    assert all(sha(PRODUCTION/name) == digest for name, digest in before.items())
    expected = {'DCWaveform_Generator.py', 'dc_waveform_core.py', 'qick_qcodes_experiment.py',
                'qick_fine_tune_sweep.py', 'qick_rf_fine_duration.py',
                'test_rf_fine_duration_compiler.py', 'test_rf_fine_duration_editor.py',
                'test_rf_fine_duration_runtime.py'}
    changed = [p for p in GUI.glob('*.py') if before.get(p.name) != sha(p)]
    assert {p.name for p in changed} == expected
    dest = HERE/'release_package'
    dest.mkdir(exist_ok=False)
    (dest/'DCWaveformGeneratorGUI').mkdir()
    entries = []
    for source in sorted(changed):
        target = dest/'DCWaveformGeneratorGUI'/source.name
        shutil.copy2(source, target)
        entries.append(dict(name=source.name, path=str(target), sha256=sha(target),
                            production_destination=str(PRODUCTION/source.name),
                            expected_production_sha256=before.get(source.name)))
    manifest = dict(software_verified=True, software_tests=680, coarse_cases=9,
                    rtl_report=str(HERE/'rtl/REPORT.md'),
                    production_promoted=False, files=entries,
                    production_policy='Keep original v5 build source gate intact; promote after its successful postbuild gate with fresh compiler proof.',
                    software_result_sha256=sha(HERE/'release/result.json'),
                    source_baseline_sha256=sha(HERE/'before_manifest.json'))
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print(f'Packaged {len(entries)} verified files; production unchanged')


if __name__ == '__main__':
    main()
