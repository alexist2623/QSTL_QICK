"""Read-only comparison of old coarse inputs with the isolated fine compiler."""
from pathlib import Path
import importlib.util
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path('C:/GIT_Workspace/QSTL_QICK')
HERE = Path(__file__).resolve().parent
GUI = Path(os.environ.get('QICK_FINE_GUI', 'F:/Vivado_Output/a5fine_sw/DCWaveformGeneratorGUI'))
BUILD = Path(os.environ.get('QICK_FINE_BASELINE_BUILD', 'F:/Vivado_Output/a5fine_baseline1'))
EVIDENCE = Path(os.environ.get('QICK_FINE_BASELINE_EVIDENCE', str(HERE)))
ORIGINAL = HERE.parent / 'recompile_inputs.py'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_original():
    spec = importlib.util.spec_from_file_location('original_v5_recompile', ORIGINAL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BUILD = BUILD
    original_arguments = module.case_arguments
    def arguments(name, state):
        source, argv = original_arguments(name, state)
        argv = list(argv)
        argv[argv.index('--gui') + 1] = str(GUI.parent)
        return source, argv
    module.case_arguments = arguments
    return module


def main():
    module = load_original()
    state = json.loads((module.OLD / 'status.json').read_text())
    if len(sys.argv) == 3 and sys.argv[1] == '--case':
        module.compile_case(sys.argv[2], state)
        return
    BUILD.mkdir(exist_ok=False)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    sources = list(GUI.glob('*.py'))
    sources += list((ROOT / 'qick/qick_lib/qick').rglob('*.py'))
    source_hashes = {str(p): sha(p) for p in sources}
    results = []
    for name, case in state['cases'].items():
        log_path = EVIDENCE / f'baseline_{name}.log'
        with log_path.open('w', encoding='utf8') as log:
            result = subprocess.run([sys.executable, '-X', 'utf8', __file__, '--case', name],
                                    cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f'{name}: exit {result.returncode}, {log_path}')
        old = Path(case['folder'])
        new = BUILD / old.name
        files = ['pmem.hex', 'dmem.txt']
        if name != 'stability':
            files.append('gui_widget_pmem.hex')
        comparisons = {}
        for filename in files:
            assert (old / filename).read_bytes() == (new / filename).read_bytes(), (name, filename)
            comparisons[str(new / filename)] = sha(new / filename)
        source, argv = module.case_arguments(name, state)
        proof = None
        if name != 'stability':
            proof = json.loads((new / 'gui_widget_match.json').read_text())
            assert proof['pmem_equal'] and proof['dmem_equal']
            assert proof['gui_sequence_unmodified'] == (name != 'reversed_axes')
        results.append(dict(case=name, passed=True, files=comparisons,
                            source=str(source), source_sha256=sha(source),
                            command=argv, gui_proof=proof))
        print(f'{name}: unchanged coarse PMEM/DMEM', flush=True)
    evidence = dict(complete=True, cases=results, gui=str(GUI),
                    source_hashes=source_hashes,
                    adapter_sha256=sha(__file__), original_sha256=sha(ORIGINAL),
                    harness_sha256=sha(ORIGINAL),
                    timing_policy='unchanged v4 Python timing; fine duration is opt-in',
                    stability='public builder, no RF/DDR',
                    reversed_axes='sweep axes reversed after GUI input by original fixture',
                    production_changes=False, rtl_rerun=False, board_access=False)
    assert source_hashes == {str(p): sha(p) for p in sources}, 'Sources changed during compilation'
    (EVIDENCE / 'baseline_equivalence.json').write_text(json.dumps(evidence, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
