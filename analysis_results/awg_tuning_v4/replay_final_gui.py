"""Recompile five actual GUI cases after post-publication control-only fixes.

Execute the unchanged fixture's compilation prefix through PMEM/DMEM export.
Stop before its behavior model or any RTL preparation, compilation or simulation.
The old RTL evidence and publication gate remain immutable.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
VALIDATION = ROOT / 'qick/firmware/ip/axis_output_sum_v1/validation'
sys.path.insert(0, str(VALIDATION))
import run_system
from gui_rtl_extension import source_hashes


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compile_case(name):
    original = ROOT / 'qick/firmware/ip/rc_precomp_validation/verify_gui_rtl.py'
    tree = ast.parse(original.read_text(encoding='utf8'), filename=str(original))
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    boundary = next(i for i, node in enumerate(main.body)
                    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'model'
                    for t in node.targets))
    assert ast.unparse(main.body[boundary].value) == 'TProcV1BehaviorModel(strict=True)'
    assert "'dmem.txt'" in ast.unparse(main.body[boundary - 1])
    main.body = main.body[:boundary]
    ast.fix_missing_locations(tree)
    build = OUT / 'compiler_replay'
    build.mkdir(exist_ok=True)
    sys.argv = run_system.arguments(build, name, run_system.CASES[name], 'v4_final2')[3:]
    namespace = dict(__name__='compile_prefix_only', __file__=str(original))
    exec(compile(tree, str(original), 'exec'), namespace)
    namespace['main']()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=list(run_system.CASES))
    args = parser.parse_args()
    if args.case:
        compile_case(args.case)
        return
    status = json.loads((OUT / 'v4_final2_status.json').read_text())
    records = []
    for name, cfg in run_system.CASES.items():
        with (OUT / f'compiler_replay_{name}.log').open('w', encoding='utf8') as log:
            subprocess.run([sys.executable, '-X', 'utf8', __file__, '--case', name],
                           cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        new = run_system.folder(OUT / 'compiler_replay', name, cfg, 'v4_final2')
        old = Path(status['cases'][name]['folder'])
        compared = {}
        for filename in ('pmem.hex', 'dmem.txt', 'gui_widget_pmem.hex'):
            assert (new / filename).read_bytes() == (old / filename).read_bytes(), (name, filename)
            compared[filename] = dict(original=str(old / filename), current=str(new / filename),
                                      sha256=digest(new / filename), byte_equal=True)
        proof = json.loads((new / 'gui_widget_match.json').read_text())
        assert proof['pmem_equal'] and proof['dmem_equal'] and proof['gui_sequence_unmodified']
        records.append(dict(case=name, files=compared, gui_proof=proof))
        print(f'{name}: GUI PMEM/DMEM byte-identical to completed RTL inputs', flush=True)
    (OUT / 'postpublish_program_equivalence.json').write_text(json.dumps(dict(
        complete=True, cases=records, source_hashes=source_hashes(ROOT.parent / 'PulseGenerator'),
        harness_sha256=digest(__file__), original_fixture_sha256=digest(
            ROOT / 'qick/firmware/ip/rc_precomp_validation/verify_gui_rtl.py'),
        rtl_rerun=False, reason='Only front-panel settings and DAC-current discovery changed; '
        'all five actual MainWindow compiler outputs match the completed RTL inputs.'), indent=2))


if __name__ == '__main__':
    main()
