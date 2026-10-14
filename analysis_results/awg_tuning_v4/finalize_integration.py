"""Bind post-publication GUI/driver fixes to preserved firmware and RTL evidence."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PROJECT = ROOT / 'qick/firmware/projects/qstl_awg_v4'
GUI = ROOT.parent / 'PulseGenerator'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_and_record():
    manifest = json.loads((PROJECT / 'build_manifest.json').read_text())
    workflow = json.loads((OUT / 'workflow_status.json').read_text())
    assert workflow['complete'] and workflow['stage'] == 'published'
    assert manifest['timing']['timing_closed'] == 'YES'
    for artifact in manifest['artifacts']:
        assert sha(artifact['path']) == artifact['sha256']
    with zipfile.ZipFile(PROJECT / 'bitstream.xsa') as archive:
        for kind, filename in [('bit', 'bitstream.bit'), ('hwh', 'bitstream.hwh')]:
            assert archive.read(manifest['xsa_members'][kind]) == (PROJECT / filename).read_bytes()
    assert sha(OUT / 'prebuild_gate.json') == manifest['functional_gate']['sha256']
    gate = json.loads((OUT / 'prebuild_gate.json').read_text())
    allowed = {
        GUI / 'DCWaveformGeneratorGUI/qick_front_panel.py': 'qick_front_panel.py.before',
        ROOT / 'qick/qick_lib/qick/dac_current.py': 'dac_current.py.before',
    }
    changes = []
    for name, expected in gate['source_hashes'].items():
        path = Path(name)
        if sha(path) != expected:
            assert path in allowed, f'Unexpected post-publication source change: {path}'
            snapshot = OUT / 'postpublish_sources' / allowed[path]
            assert sha(snapshot) == expected
            changes.append(dict(path=str(path), before_sha256=expected,
                                after_sha256=sha(path), before_snapshot=str(snapshot)))
    assert {Path(item['path']) for item in changes} == set(allowed)
    for name, expected in gate['evidence_hashes'].items():
        assert sha(name) == expected, name
    spec = importlib.util.spec_from_file_location('final_scope', PROJECT / 'validate_scope.py')
    scope = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scope)
    assert scope.validate() == dict(passed=True, protected_files=59)
    equivalence = json.loads((OUT / 'postpublish_program_equivalence.json').read_text())
    assert equivalence['complete'] and len(equivalence['cases']) == 5
    for name, expected in equivalence['source_hashes'].items():
        assert sha(name) == expected, name
    for case in equivalence['cases']:
        assert case['gui_proof']['pmem_equal'] and case['gui_proof']['dmem_equal']
        for item in case['files'].values():
            assert sha(item['original']) == sha(item['current']) == item['sha256']
    suites = list(ET.parse(OUT / 'postpublish_software.xml').iter('testsuite'))
    assert sum(int(s.get('tests')) for s in suites) == 274
    assert all(int(s.get(key, '0')) == 0 for s in suites for key in ('errors', 'failures', 'skipped'))
    timing = (PROJECT / 'validation_reports/timing_summary_postroute.rpt').read_text()
    assert 'All user specified timing constraints are met' in timing
    bus = (PROJECT / 'validation_reports/bus_skew_postroute.rpt').read_text()
    slack = [float(value) for value in re.findall(r'Slack \(MET\)\s*:\s*([\d.]+)ns', bus)]
    assert len(slack) == 14 and min(slack) >= 0 and 'VIOLATED' not in bus
    branches = {str(repo): subprocess.check_output(['git', '-C', str(repo), 'branch', '--show-current'],
                text=True).strip() for repo in (ROOT, GUI)}
    assert all(branch == 'awg_tuning_v4' for branch in branches.values())
    evidence = [OUT / 'postpublish_software.xml', OUT / 'postpublish_software.log',
                OUT / 'postpublish_program_equivalence.json', OUT / 'test_final_firmware_integration.py',
                OUT / 'replay_final_gui.py', OUT / 'final_gui_shared_dac.png',
                OUT / 'postpublish_before_fix.log', Path(__file__)]
    result = dict(complete=True, verified_utc=datetime.now(timezone.utc).isoformat(),
        build_manifest=dict(path=str(PROJECT / 'build_manifest.json'), sha256=sha(PROJECT / 'build_manifest.json')),
        original_functional_gate=manifest['functional_gate'], protected_files=59,
        branches=branches, postpublication_changes=changes,
        current_source_hashes={name: sha(name) for name in gate['source_hashes']},
        additional_evidence={str(path): sha(path) for path in evidence},
        software_tests_passed=274, gui_program_equivalence_cases=5,
        timing=manifest['timing'], bus_skew_constraints_met=14, minimum_bus_skew_slack_ns=min(slack),
        physical_pairs=[dict(rf_gen=r, awg_gen=a, rfdc_dac=d, front_panel_dac=p)
                        for r,a,d,p in [(0,1,'10',4),(2,3,'11',5),(4,5,'12',6)]],
        rtl_changed_after_build=False, firmware_changed_after_publication=False,
        rtl_simulation_repeated=False, full_build_repeated=False, board_analog_tested=False,
        validation_note='The immutable prebuild gate certifies the build-time sources. '
        'This supplemental manifest binds only the two reviewed software changes to '
        '274 passing tests and five byte-identical GUI PMEM/DMEM replays. '
        'The old gate was not rewritten to claim new sources were simulated.')
    (OUT / 'final_integration_manifest.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(complete=True, software_tests=274, gui_replays=5,
                         postpublication_source_changes=len(changes), artifacts=3)))


if __name__ == '__main__':
    verify_and_record()
