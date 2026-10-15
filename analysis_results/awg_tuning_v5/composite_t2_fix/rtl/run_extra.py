"""Run the additional Hahn/global GUI case after the six isolated custom cases."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

from run import check, VIVADO

HERE = Path(__file__).resolve().parent


def main():
    state_file = HERE / 'hahn_status.json'
    if state_file.exists():
        raise RuntimeError('Existing Hahn execution evidence; do not duplicate/retry automatically')
    custom = json.loads((HERE / 'status.json').read_text())
    assert custom['complete'] and custom['stage'] == 'passed', 'Six custom cases must finish first'
    preparations = [json.loads((HERE / 'hahn_manual_prepared.json').read_text())]
    assert all(len(prepared['cases']) == 1 for prepared in preparations)
    state = dict(complete=False, stage='simulate', cases=[],
                 simulation_snapshot=str(Path(custom['build']) / 'sim'),
                 new_inputs=[prepared['build'] for prepared in preparations],
                 started=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
    def save():
        state['updated'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        state_file.write_text(json.dumps(state, indent=2))
    try:
        save()
        for prepared in preparations:
            case = prepared['cases'][0]
            state['active_scenario'] = prepared['scenario']
            save()
            out = Path(case['folder'])
            options = out / 'options.txt'
            options.write_text('\n'.join(['t2_gui', '-runall', '-testplusarg "CASE=' + out.as_posix() + '"',
                '-testplusarg "OUT=' + out.as_posix() + '"', '-testplusarg "CYCLES=' + str(case['cycles']) + '"',
                '-log "' + (out / 'xsim.log').as_posix() + '"']))
            with (out / 'run_console.log').open('w') as stream:
                result = subprocess.run([str(VIVADO/'xsim.bat'), '-f', str(options)],
                    cwd=Path(custom['build'])/'sim', stdout=stream, stderr=subprocess.STDOUT)
            assert result.returncode == 0, result.returncode
            checked = check(case)
            checked['scenario'] = prepared['scenario']
            checked['expected_runtime_gains'] = case['expected_runtime_gains']
            state['cases'].append(checked)
            save()
        state['complete'] = True
        state['stage'] = 'passed'
        state['helper_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        save()
        print('PASS Hahn->Custom named per-pulse amplitude+phase, T2 endpoints, all3pairs x2', flush=True)
    except BaseException as exc:
        state['stage'] = 'failed'
        state['error'] = repr(exc)
        save()
        raise


if __name__ == '__main__':
    main()
