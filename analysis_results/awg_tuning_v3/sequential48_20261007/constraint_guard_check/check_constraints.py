"""SYNTHETIC OFFLINE guard checks; no Vivado, xsim, or FPGA timing validation."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tkinter
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
REPO = Path('C:/GIT_Workspace/QSTL_QICK')
GUI = Path('C:/GIT_Workspace/PulseGenerator')
PROJECT = REPO/'qick/firmware/projects/qstl_awg_v3'
BUILD_SCRIPT = PROJECT/'build_vivado_2023_1.tcl'
PUBLISHER = PROJECT/'publish_build.py'
EVIDENCE = Path(__file__).resolve().parent
FIXTURES = Path('F:/Vivado_Output/a3_guard_check/run2')
EXPECTED = {
    'timing.xdc': '9f9d68f0d1d9e69d9c236606d65781e5c1f5eed4b1672a24daebfb670e0bacfb',
    'ios.xdc': '5435d174456af7c2156207ad1571fb56aec6ea1264efea73f9a42a11623430a7',
}
checks = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name, function):
    try:
        detail = function()
        checks.append(dict(name=name, passed=True, detail=detail))
    except Exception as error:
        checks.append(dict(name=name, passed=False,
                           error=f'{type(error).__name__}: {error}'))


def must_reject(function, required_message):
    try:
        function()
    except Exception as error:
        assert required_message in str(error), repr(error)
        return dict(rejected=True, exception=type(error).__name__, message=str(error))
    raise AssertionError('Invalid synthetic fixture was accepted')


def tcl_prefix(target, forbidden):
    interpreter = tkinter.Tcl()
    interpreter.call('set', 'argc', 1)
    interpreter.call('set', 'argv', interpreter.call('list', str(target)))
    interpreter.eval('set __version_called 0; set __create_called 0')
    interpreter.eval('proc version {args} {set ::__version_called 1; error "OFFLINE_STOP_BEFORE_VIVADO"}')
    interpreter.eval('proc create_project {args} {set ::__create_called 1; error "CREATE_PROJECT_MUST_NOT_RUN"}')
    try:
        interpreter.call('source', BUILD_SCRIPT.as_posix())
    except tkinter.TclError as error:
        message = str(error)
    else:
        raise AssertionError('Guard check must stop before any Vivado/build operation')
    assert int(interpreter.getvar('__create_called')) == 0
    assert int(interpreter.getvar('jobs')) == 4
    assert int(interpreter.getvar('threads')) == 5
    if forbidden:
        assert 'outside both Git repositories' in message, message
        assert int(interpreter.getvar('__version_called')) == 0
    else:
        assert message == 'OFFLINE_STOP_BEFORE_VIVADO', message
        assert int(interpreter.getvar('__version_called')) == 1
    return interpreter, dict(target=str(target), rejected=forbidden,
                             create_project_called=False, jobs=4, maxThreads=5, message=message)


def xml_fixture(build, path_style='absolute'):
    root = ET.Element('Project', Product='Vivado', Version='7', Minor='63')
    file_sets = ET.SubElement(root, 'FileSets')
    file_set = copy.deepcopy(previous_fileset)
    for entry in file_set.findall('File'):
        name = Path(entry.get('Path')).name
        if path_style == 'absolute':
            value = (build/'constraints'/name).as_posix()
        elif path_style == 'project_variable':
            value = '$PPRDIR/constraints/'+name
        else:
            value = 'constraints/'+name
        entry.set('Path', value)
    file_sets.append(file_set)
    return root


def fixture(name, path_style='absolute'):
    build = FIXTURES/name
    (build/'constraints').mkdir(parents=True, exist_ok=False)
    conditions = {'launch_jobs': '4', 'general.maxThreads': '5'}
    for name, expected in EXPECTED.items():
        (build/'constraints'/name).write_bytes((PROJECT/name).read_bytes())
        for label, path in (('source', PROJECT/name), ('snapshot', build/'constraints'/name)):
            conditions[f'constraint.{name}.{label}_path'] = path.as_posix()
            conditions[f'constraint.{name}.{label}_sha256'] = expected
    root = xml_fixture(build, path_style)
    ET.ElementTree(root).write(build/'qstl_awg_v3.xpr', encoding='utf-8', xml_declaration=True)
    return build, conditions, root


def save_fixture(build, conditions, root):
    ET.ElementTree(root).write(build/'qstl_awg_v3.xpr', encoding='utf-8', xml_declaration=True)
    (build/'build_conditions.txt').write_text(
        '\n'.join(f'{key}={value}' for key, value in conditions.items())+'\n', encoding='utf-8')


def publisher_accept(name, style):
    build, conditions, root = fixture(name, style)
    save_fixture(build, conditions, root)
    records = validate(build, PROJECT, conditions)
    assert {r['name']: r['sha256'] for r in records} == EXPECTED
    return dict(fixture=str(build), accepted=True, records=records)


def publisher_reject(name, mutation, message):
    build, conditions, root = fixture(name)
    mutation(build, conditions, root)
    save_fixture(build, conditions, root)
    detail = must_reject(lambda: validate(build, PROJECT, conditions), message)
    return dict(fixture=str(build), **detail)


def file_entry(root, name='timing.xdc'):
    return next(entry for entry in root.findall('.//FileSet/File') if Path(entry.get('Path')).name == name)


def omit_used_in(root, mode):
    info = file_entry(root).find('FileInfo')
    info.remove(info.find(f"Attr[@Name='UsedIn'][@Val='{mode}']"))


def real_hash(interpreter, name):
    observed = interpreter.call('sha256_file', (PROJECT/name).as_posix())
    assert observed == EXPECTED[name] == sha(PROJECT/name)
    return dict(file=str(PROJECT/name), actual_certutil_sha256=observed)


def parser_case(interpreter, output, expected=None):
    interpreter.call('set', '__hash_output', output)
    if expected is None:
        return must_reject(lambda: interpreter.call('sha256_file', (PROJECT/'timing.xdc').as_posix()),
                           'Could not read one SHA256')
    actual = interpreter.call('sha256_file', (PROJECT/'timing.xdc').as_posix())
    assert actual == expected
    return dict(sha256=actual, synthetic_certutil_output=True)


def fixed_baseline_rejection():
    build, conditions, root = fixture('wrong_but_self_consistent_baseline')
    synthetic_project = build/'synthetic_source/qstl_awg_v3'
    synthetic_reference = synthetic_project.parent/'qstl_awg_v2'
    synthetic_project.mkdir(parents=True)
    synthetic_reference.mkdir()
    for name in EXPECTED:
        content = (PROJECT/name).read_bytes()+b'\n# synthetic wrong baseline\n'
        for destination in (synthetic_project/name, synthetic_reference/name, build/'constraints'/name):
            destination.write_bytes(content)
        conditions[f'constraint.{name}.source_path'] = (synthetic_project/name).as_posix()
        for label in ('source', 'snapshot'):
            conditions[f'constraint.{name}.{label}_sha256'] = hashlib.sha256(content).hexdigest()
    save_fixture(build, conditions, root)
    return must_reject(lambda: validate(build, synthetic_project, conditions), 'successful v2 baseline')


FIXTURES.mkdir(parents=True, exist_ok=False)
tracked = [BUILD_SCRIPT, PUBLISHER]+[directory/name for directory in (PROJECT, PROJECT.parent/'qstl_awg_v2') for name in EXPECTED]
before = {str(path): sha(path) for path in tracked}
publisher_text = PUBLISHER.read_text(encoding='utf-8')
namespace = {'__name__': '_synthetic_constraint_guard_check', '__file__': str(PUBLISHER)}
exec(compile(publisher_text, str(PUBLISHER), 'exec'), namespace)
validate = namespace['validate_build_constraints']
previous_xpr = Path('F:/Vivado_Output/a3full6/qstl_awg_v3.xpr')
previous_text = previous_xpr.read_text(encoding='utf-8')
previous_root = ET.fromstring(previous_text)
previous_fileset = previous_root.find(".//FileSet[@Name='constrs_1']")


def previous_shape():
    assert 'Product Version: Vivado v2023.1 (64-bit)' in previous_text
    assert previous_fileset is not None
    entries = []
    for entry in previous_fileset.findall('File'):
        modes = sorted(attr.get('Val') for attr in entry.findall("FileInfo/Attr[@Name='UsedIn']"))
        assert modes == ['implementation', 'synthesis']
        entries.append(dict(path=entry.get('Path'), used_in=modes))
    assert {Path(entry['path']).name for entry in entries} == set(EXPECTED)
    return dict(read_only_previous_project=str(previous_xpr), vivado='2023.1', files=entries)


check('actual_Vivado_2023_1_XPR_attribute_shape', previous_shape)
for name, path in [('qick_root', REPO), ('qick_child', REPO/'guard_check_must_not_create'),
                   ('gui_root', GUI), ('gui_child', GUI/'guard_check_must_not_create'),
                   ('mixed_case_gui', Path('c:/git_workspace/pulsegenerator/guard_check_must_not_create'))]:
    check('Tcl_reject_'+name, lambda path=path: tcl_prefix(path, True)[1])
for name, path in [('external', FIXTURES/'uncreated_guard_target'),
                   ('sibling_name_boundary', Path('C:/GIT_Workspace/QSTL_QICK_extra_guard'))]:
    check('Tcl_accept_path_'+name, lambda path=path: tcl_prefix(path, False)[1])
interpreter, _ = tcl_prefix(FIXTURES/'uncreated_guard_target', False)
for name in EXPECTED:
    check('actual_certutil_sha256_'+name, lambda name=name: real_hash(interpreter, name))
interpreter.eval('rename exec __real_exec; proc exec {args} {return $::__hash_output}')
digest = EXPECTED['timing.xdc']
check('parser_localized_header_uppercase_spaced_digest', lambda: parser_case(
    interpreter, '지역화된 헤더\r\n'+' '.join(digest.upper()[i:i+2] for i in range(0,64,2))+'\r\n완료\r\n', digest))
check('parser_reject_missing_digest', lambda: parser_case(interpreter, 'No digest\n'))
check('parser_reject_two_digests', lambda: parser_case(interpreter, digest+'\n'+digest+'\n'))
interpreter.eval('rename exec {}; rename __real_exec exec')

for style in ('absolute', 'project_variable', 'relative'):
    check('publisher_accept_'+style, lambda style=style: publisher_accept('valid_'+style, style))

old_timing = REPO/'analysis_results/awg_tuning_v3/scope_correction/xdc_restore_20261007/timing_v3_before_restore.xdc'
negative_cases = [
    ('old_wrong_timing', lambda b,c,r: (b/'constraints/timing.xdc').write_bytes(old_timing.read_bytes()), 'constraints differ'),
    ('corrupted_ios', lambda b,c,r: (b/'constraints/ios.xdc').write_bytes((PROJECT/'ios.xdc').read_bytes()+b'\n# synthetic modification\n'), 'constraints differ'),
    ('wrong_source_hash', lambda b,c,r: c.update({'constraint.timing.xdc.source_sha256':'0'*64}), 'constraint provenance'),
    ('wrong_snapshot_hash', lambda b,c,r: c.update({'constraint.timing.xdc.snapshot_sha256':'0'*64}), 'constraint provenance'),
    ('wrong_source_record_path', lambda b,c,r: c.update({'constraint.timing.xdc.source_path':str(b/'wrong_source.xdc')}), 'constraint provenance'),
    ('wrong_snapshot_record_path', lambda b,c,r: c.update({'constraint.timing.xdc.snapshot_path':str(b/'wrong_snapshot.xdc')}), 'constraint provenance'),
    ('project_uses_repository_XDC', lambda b,c,r: file_entry(r).set('Path',(PROJECT/'timing.xdc').as_posix()), 'exactly the original build-local'),
    ('wrong_project_snapshot_path', lambda b,c,r: file_entry(r).set('Path',(b/'wrong/timing.xdc').as_posix()), 'exactly the original build-local'),
    ('project_unresolved_variable', lambda b,c,r: file_entry(r).set('Path','$UNEXPECTED/constraints/timing.xdc'), 'Unresolved project constraint path'),
    ('missing_UsedIn_synthesis', lambda b,c,r: omit_used_in(r,'synthesis'), 'not enabled in both'),
    ('missing_UsedIn_implementation', lambda b,c,r: omit_used_in(r,'implementation'), 'not enabled in both'),
    ('missing_ios_project_reference', lambda b,c,r: r.find('.//FileSet').remove(file_entry(r,'ios.xdc')), 'exactly the original build-local'),
]
for name, mutation, message in negative_cases:
    check('publisher_reject_'+name, lambda name=name, mutation=mutation, message=message:
          publisher_reject(name, mutation, message))
check('publisher_reject_wrong_self_consistent_fixed_baseline', fixed_baseline_rejection)
valid_build = FIXTURES/'valid_absolute'
expected_tcl_list = interpreter.call('list', *[item for pair in EXPECTED.items() for item in pair])
check('Tcl_snapshot_guard_accepts_correct_copy', lambda: dict(result=str(interpreter.call(
    'verify_constraint_snapshots', (valid_build/'constraints').as_posix(), expected_tcl_list))))
check('Tcl_snapshot_guard_rejects_archived_wrong_XDC', lambda: must_reject(lambda: interpreter.call(
    'verify_constraint_snapshots', (FIXTURES/'old_wrong_timing/constraints').as_posix(), expected_tcl_list),
    'Build constraint snapshot changed'))

after = {str(path): sha(path) for path in tracked}
check('source_and_real_constraints_unchanged', lambda: dict(unchanged=True) if before == after else
      (_ for _ in ()).throw(AssertionError('Implementation/XDC changed during this guard check')))
complete = all(case['passed'] for case in checks)
result = dict(kind='synthetic_offline_guard_checks', fpga_timing_validation=False,
              vivado_or_xsim_launched=False, created_utc=datetime.now(timezone.utc).isoformat(),
              complete=complete, passed=sum(case['passed'] for case in checks), total=len(checks),
              fixture_directory=str(FIXTURES), source_hashes=before,
              harness_sha256=sha(Path(__file__)), checks=checks)
(EVIDENCE/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
lines = ['# Synthetic offline constraint guard checks', '',
         '**These checks do not run Vivado or xsim and do not establish FPGA timing closure.**', '',
         f"Passed: {result['passed']}/{result['total']}; complete: {complete}.", '',
         'The actual previous Vivado 2023.1 XPR was read only to verify XML attribute shape.',
         'Acceptance/rejection fixtures and modified constraint copies exist only under `F:/Vivado_Output/a3_guard_check`.',
         'No implementation source, original XDC, or real build evidence was edited.', '',
         '| Check | Result |', '|---|---|']
lines += [f"| {case['name']} | {'PASS' if case['passed'] else 'FAIL'} |" for case in checks]
(EVIDENCE/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
print(json.dumps(dict(complete=complete, passed=result['passed'], total=result['total'],
                     failed=[case for case in checks if not case['passed']]), ensure_ascii=False, indent=2))
raise SystemExit(0 if complete else 1)
