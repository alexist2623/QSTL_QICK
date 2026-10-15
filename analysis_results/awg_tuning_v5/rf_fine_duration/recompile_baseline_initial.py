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
    results = []
    for name, case in state['cases'].items():
        log_path = HERE / f'baseline_{name}.log'
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
        results.append(dict(case=name, passed=True, files=comparisons))
        print(f'{name}: unchanged coarse PMEM/DMEM', flush=True)
    evidence = dict(complete=True, cases=results, gui=str(GUI),
                    source_hashes={str(p): sha(p) for p in GUI.glob('*.py')},
                    adapter_sha256=sha(__file__), original_sha256=sha(ORIGINAL),
                    production_changes=False, rtl_rerun=False, board_access=False)
    (HERE / 'baseline_equivalence.json').write_text(json.dumps(evidence, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
