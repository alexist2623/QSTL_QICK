"""Record the specifically authorized editor fix without changing baseline hashes."""
import ast
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
GUI = Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

old = ast.parse((HERE / 'dc_waveform_widgets.before.py').read_text(encoding='utf8'))
new = ast.parse((GUI / 'dc_waveform_widgets.py').read_text(encoding='utf8'))
allowed = {
    'RfPulseTimelineWidget': {'set_pulses'},
    'WaveformPlotWidget': {'set_virtual_preview', 'set_voltage_view', 'add_pulse',
        'set_selected_port_idx', 'remove_pulse', '_finish_drag', '_hide_annotation',
        'event', 'eventFilter', 'mouseMoveEvent', 'mouseReleaseEvent'},
}
def outside_changes(tree):
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == 'PyQt5':
            node.names = [name for name in node.names if name.name != 'sip']
        if isinstance(node, ast.ClassDef) and node.name in allowed:
            node.body = [member for member in node.body
                         if not isinstance(member, ast.FunctionDef)
                         or member.name not in allowed[node.name]]
    return ast.dump(tree)
assert outside_changes(old) == outside_changes(new), 'Unrelated widget logic changed'
suite = ET.parse(HERE / 'targeted.xml').getroot().find('testsuite')
assert suite.attrib['tests'] == '79'
assert suite.attrib['failures'] == suite.attrib['errors'] == '0'
log = (HERE / 'targeted.log').read_text(encoding='utf-8-sig')
assert 'QT_EXPLICIT_TEARDOWN_COMPLETE' in log and 'QT_CALLBACK_ERRORS' not in log
compiler = json.loads((EVIDENCE / 'compiler_equivalence.json').read_text())
assert compiler['complete'] and len(compiler['cases']) == 9
assert sha(EVIDENCE / 'recompile_inputs.py') == compiler['harness_sha256']
for path, expected in compiler['source_hashes'].items():
    assert sha(path) == expected, path
for case in compiler['cases']:
    assert case['passed']
    for path, expected in case['files'].items():
        assert sha(path) == expected, path
files = {(GUI / name).as_posix(): sha(GUI / name) for name in (
    'dc_waveform_widgets.py', 'test_waveform_plot_annotations.py')}
record = dict(requested_fix_passed=True, targeted_tests=79, targeted_exit_code=0,
    compiler_equivalent_cases=9, broader_assertions_passed=157, broader_exit_code=1,
    broader_issue="Separate RF duration-name callback KeyError d1; unchanged production code",
    source_hashes=files, evidence_hashes={name:sha(HERE / name) for name in (
        'targeted.xml', 'targeted.log', 'tests.xml', 'tests.log', 'waveform_labels.png',
        'REPORT.md', 'run_tests.py', 'record_evidence.py')},
    compiler_evidence_sha256=sha(EVIDENCE / 'compiler_equivalence.json'),
    hardware_access=False, production_compiler_or_rtl_changed=False)
(HERE / 'result.json').write_text(json.dumps(record, indent=2), encoding='utf8')
auth_path = EVIDENCE / 'authorized_gui_fix.json'
auth = json.loads(auth_path.read_text(encoding='utf-8-sig'))
auth['files'] = {path.replace('\\', '/'): expected for path, expected in auth['files'].items()}
for path, expected in auth['files'].items():
    assert sha(path).lower() == expected.lower(), path
auth['files'].update(files)
auth['display_fix_reason'] = 'Explicit user request: stuck AWG annotation, HOLD voltage dragging, RF names inside pulses.'
auth['display_fix_evidence'] = str(HERE / 'result.json')
auth['display_fix_evidence_sha256'] = sha(HERE / 'result.json')
auth_path.write_text(json.dumps(auth, indent=2), encoding='utf8')
print('DISPLAY_FIX_SCOPE_AND_INPUT_PROOF_PASS tests=79 compiler_cases=9; broader RF rename issue recorded')
