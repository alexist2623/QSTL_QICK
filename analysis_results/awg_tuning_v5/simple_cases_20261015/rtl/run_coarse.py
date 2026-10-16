"""Three fresh actual-Qt compile and actual RTL cases, serial and isolated."""
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import shutil
import subprocess
import sys
from cases import CASES
from run_case import generate, ROOT, SIM, folder

HERE = Path(__file__).resolve().parent
def now(): return datetime.now(timezone.utc).isoformat()

def main():
    status = HERE/'coarse_status.json'
    assert not status.exists()
    for name in CASES: generate(name)
    source = Path('F:/Vivado_Output/a3sim1')
    SIM.mkdir(exist_ok=False)
    sub = Path('qstl_gui_rtl_sim.sim/sim_1/behav/xsim')
    src, dst = source/sub, SIM/sub
    (dst/'xsim.dir').mkdir(parents=True)
    shutil.copytree(src/'xsim.dir/xil_defaultlib', dst/'xsim.dir/xil_defaultlib')
    for name in ('xsim.ini', 'elaborate.bat'): shutil.copy2(src/name, dst/name)
    name = Path('qstl_gui_rtl_sim.gen/sources_1/bd/sim_bd/sim/sim_bd.v')
    (SIM/name).parent.mkdir(parents=True)
    shutil.copy2(source/name, SIM/name)
    shutil.copy2(source/'wrapper_path.txt', SIM/'wrapper_path.txt')
    state = dict(complete=False, pid=os.getpid(), started=now(), cases={}, max_xsim=1)
    def save():
        state['updated'] = now(); status.write_text(json.dumps(state, indent=2))
    save()
    for name in CASES:
        entry = state['cases'][name] = dict(folder=str(folder(name)), rf_offset_us=.1)
        for phase, flag in [('prepare', '--prepare-only'), ('rtl', '--reuse-snapshot')]:
            log = HERE/f'{name}.{phase}.log'
            assert not log.exists()
            argv = [sys.executable, '-X', 'utf8', '-u', str(HERE/'run_case.py'), '--case', name, flag]
            entry[phase] = dict(command=argv, log=str(log), started=now()); save()
            with log.open('w') as out:
                process = subprocess.Popen(argv, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
                entry[phase]['pid'] = process.pid; save(); code = process.wait()
            entry[phase].update(exit_code=code, finished=now()); save()
            print(name, phase, code, flush=True)
            if code: break
        result_path = folder(name)/'result.json'
        entry['passed'] = code == 0 and result_path.exists() and json.loads(result_path.read_text()).get('validation_status') == 'passed'
        save()
    state['complete'] = True
    state['passed'] = all(c['passed'] for c in state['cases'].values())
    state['finished'] = now(); save()
    return 0 if state['passed'] else 1

if __name__ == '__main__': raise SystemExit(main())
