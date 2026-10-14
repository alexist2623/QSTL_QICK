"""Run existing desktop regressions and selected-48 RTL checks before synthesis."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--gui', type=Path, required=True)
    args = parser.parse_args()
    args.build.mkdir(parents=True, exist_ok=False)
    (args.build/'pytest_temp').mkdir()
    here = Path(__file__).resolve().parent
    repo = here.parents[4]
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    state = dict(complete=False, selected_width=48, stages={})
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    protected = list((here.parent/'src').glob('*.sv'))
    protected += list((args.gui/'DCWaveformGeneratorGUI').glob('*.py'))
    protected += list((args.gui/'DCWaveformGeneratorGUI').glob('*.json'))
    before = {str(p): sha(p) for p in protected}
    (args.build/'source_hashes.json').write_text(json.dumps(before, indent=2))

    def save():
        temp = args.build/'status.tmp'
        temp.write_text(json.dumps(state, indent=2), encoding='utf-8')
        temp.replace(args.build/'status.json')

    def run(key, command, cwd):
        log = args.build/(key+'.log')
        start = time.time()
        state['stages'][key] = dict(state='running', command=list(map(str, command)), log=str(log), started=start)
        save()
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run(list(map(str, command)), cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT)
        state['stages'][key].update(state='passed' if result.returncode == 0 else 'failed',
                                    exit_code=result.returncode, elapsed_s=time.time()-start)
        save()
        print(f'{key}: exit {result.returncode}', flush=True)

    run('legacy_before', [sys.executable, '-X', 'utf8', here/'legacy_logic_guard.py'], repo)
    modules = [('qick', p, repo) for p in sorted((repo/'qick/qick_lib/qick').rglob('test_*.py'))]
    modules += [('gui', p, args.gui) for p in sorted((args.gui/'DCWaveformGeneratorGUI').glob('test_*.py'))]
    for group, module, cwd in modules:
        key = group+'_'+module.parent.name+'_'+module.stem
        run(key, [sys.executable, '-X', 'utf8', '-X', 'faulthandler', '-m', 'pytest', module,
                  '-q', '-p', 'no:cacheprovider', '--basetemp', args.build/'pytest_temp'/key], cwd)
    for bench in ('tb_dc_area', 'tb_dc_boundaries', 'tb_width_awg', 'tb_dc_faults', 'tb_set_saturation'):
        run(bench, [sys.executable, '-X', 'utf8', here/'run_unit_bench.py', '--bench', bench,
                    '--width', '48', '--build', args.build/bench], repo)
    run('legacy_outputs', [sys.executable, '-X', 'utf8', here/'validate_timing_tail.py',
                          '--build', args.build/'legacy_outputs'], repo)
    run('legacy_after', [sys.executable, '-X', 'utf8', here/'legacy_logic_guard.py'], repo)
    changed = [path for path, expected in before.items() if not Path(path).is_file() or sha(Path(path)) != expected]
    state['changed_sources_or_user_settings'] = changed
    state['complete'] = not changed and all(s['state'] == 'passed' for s in state['stages'].values())
    state['finished'] = time.time()
    save()
    print(json.dumps(dict(complete=state['complete'], stages=len(state['stages']), changed=changed)))
    raise SystemExit(0 if state['complete'] else 1)


if __name__ == '__main__':
    main()
