"""Fresh v4 regression; never build, publish, or substitute historical PASS.

The separately started regular runner is observed to completion first. Shared
simulation libraries are prepared serially; isolated runs use at most 3 workers.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GUI = ROOT.parent / 'PulseGenerator'
BASE = Path('F:/Vivado_Output/a4reg1')
SIM = Path('F:/Vivado_Output/a3sim1')
TAG = 'v4_all_20261014'
VALID = ROOT / 'qick/firmware/ip/axis_awg_tuning_v3/validation'
VERIFY = ROOT / 'qick/firmware/ip/rc_precomp_validation/verify_gui_rtl.py'
PY = [sys.executable, '-X', 'utf8', '-X', 'faulthandler']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2), encoding='utf8')
    temp.replace(path)


def generate_stability():
    """Extend the unchanged baseline Stability builder fixture to v4 routing.

    It remains an AWG-only Stability builder test, not RF/DDR acquisition.
    All original area/raw/command monitors are kept; three sum monitors added.
    """
    text = VERIFY.read_text(encoding='utf8')
    changes = []
    def replace(old, new):
        nonlocal text
        assert text.count(old) == 1, old
        text = text.replace(old, new, 1)
        changes.append(dict(old=old, new=new))
    replace('HERE=Path(__file__).resolve().parent', f'HERE=Path({str(VERIFY.parent)!r})')
    replace('if args.output_sum and (not args.awg_v3 or not args.sweep_case):',
            "if args.output_sum and (not args.awg_v3 or not (args.sweep_case or args.v2_fixture=='stability')):")
    replace("segment_length_mode=rf_specs[0].segment_length_mode if ch==0 else 'fixed') for ch in (0,2,4)]",
            "segment_length_mode=rf_specs[0].segment_length_mode if ch==0 else 'fixed') for ch in ((0,2,4) if rf_specs else ())]")
    replace("output_names=('awg_0','awg_1'),", "output_names=('awg_0','awg_1','awg_2'),")
    replace('cross_capacitance={np.asarray(args.cross_capacitance).reshape(2,2).tolist()!r},',
            'cross_capacitance={matrix.tolist()!r},')
    replace('output_full_scales_mv={tuple(v*40 for v in args.dac_current_ma[:2])!r})',
            'output_full_scales_mv={scales!r})')
    replace('return sequence.make_program(soccfg,awg_channels=(1,3),repetitions_per_sweep=2,',
            'return sequence.make_program(soccfg,awg_channels=(1,3,5),repetitions_per_sweep=2,')
    replace("    if args.sweep_case:\n        keep.update(('axis_signal_gen_v6_0', 'axis_register_slice_0', 'axis_register_slice_4'))",
            "    if args.sweep_case or args.output_sum:\n        keep.update(('axis_signal_gen_v6_0', 'axis_register_slice_0', 'axis_register_slice_4'))")
    replace("    if args.sweep_case:\n        ties += [\"assign axis_switch_gen_M00_AXIS_TDATA=32'b0; assign axis_switch_gen_M00_AXIS_TVALID=1'b0;\"]",
            "    if args.sweep_case or args.output_sum:\n        ties += [\"assign axis_switch_gen_M00_AXIS_TDATA=32'b0; assign axis_switch_gen_M00_AXIS_TVALID=1'b0;\"]")
    replace("summary['output_sum']=sum_validation.analyze(out,result,model,offset,shots,args.sum_rf_delay_us)",
            "from stability_support import analyze\n        summary['output_sum']=analyze(out,result,model,offset,shots,args.sum_rf_delay_us)")
    target = HERE / 'verify_stability_generated.py'
    target.write_text(text, encoding='utf8')
    write(HERE / 'stability_harness_changes.json', dict(original=str(VERIFY), original_sha256=sha(VERIFY),
        generated=str(target), generated_sha256=sha(target), changes=changes,
        scope='Current Stability public sequence builder, 3 AWGs through v4 sum, RF inputs zero; no DDR'))
    return target


def main():
    statepath = HERE / 'status.json'
    if statepath.exists():
        raise RuntimeError('Fresh run only; existing evidence must not be overwritten')
    source_files = list((GUI / 'DCWaveformGeneratorGUI').glob('*.py'))
    source_files += list((GUI / 'DCWaveformGeneratorGUI').glob('*.json'))
    source_files += list((ROOT / 'qick/qick_lib/qick').rglob('*.py'))
    for ip in ('axis_awg_tuning_v3', 'axis_square_pulse_v1', 'axis_output_sum_v1'):
        source_files += list((ROOT / 'qick/firmware/ip' / ip / 'src').glob('*'))
    project = ROOT / 'qick/firmware/projects/qstl_awg_v4'
    source_files += [project / n for n in ('timing.xdc', 'ios.xdc', 'bitstream.bit', 'bitstream.hwh', 'bitstream.xsa')]
    hashes = {str(p): sha(p) for p in source_files if p.is_file()}
    write(HERE / 'source_hashes_before.json', hashes)
    state = dict(complete=False, stage='waiting_regular', pid=os.getpid(), selected_width=48,
        started_utc=datetime.now(timezone.utc).isoformat(), basic_build=str(BASE), stages={}, cases={},
        no_synthesis_or_publication=True, max_isolated_simulators=3)
    lock = threading.RLock()
    def save():
        with lock:
            state['updated_utc'] = datetime.now(timezone.utc).isoformat()
            write(statepath, state)
    def execute(name, argv, cwd=ROOT):
        log = HERE / (name + '.log')
        if log.exists(): raise RuntimeError('Existing log: ' + str(log))
        entry = dict(state='running', command=list(map(str, argv)), log=str(log), started=time.time())
        with lock:
            state['stage'] = name
            state['stages'][name] = entry
            save()
        with log.open('w', encoding='utf8') as stream:
            child = subprocess.Popen(list(map(str, argv)), cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
            with lock:
                entry['pid'] = child.pid
                save()
            rc = child.wait()
        with lock:
            entry.update(state='passed' if rc == 0 else 'failed', exit_code=rc, elapsed_s=time.time()-entry['started'])
            save()
        print(name + ': exit ' + str(rc), flush=True)
        return rc == 0
    save()
    while True:
        regular = json.loads((BASE / 'status.json').read_text())
        if 'finished' in regular: break
        time.sleep(20)
    state['regular_complete'] = regular['complete']
    state['regular_failures'] = [k for k,v in regular['stages'].items() if v['state'] != 'passed']
    save()
    execute('scope', PY + [project / 'validate_scope.py'])
    # Redirect this test's screenshot into the new evidence directory; retain
    # all original assertions and read-only checks of published manifests.
    test_original = HERE.parent / 'test_final_firmware_integration.py'
    test_text = test_original.read_text(encoding='utf8')
    for old,new in [
        ('ROOT = Path(__file__).resolve().parents[2]', f'ROOT = Path({str(ROOT)!r})'),
        ('OUT = Path(__file__).resolve().parent', f'OUT = Path({str(HERE.parent)!r})'),
        ("str(OUT / 'final_gui_shared_dac.png')", f'str(Path({str(HERE / "final_gui_shared_dac.png")!r}))'),
    ]:
        assert test_text.count(old)==1, old
        test_text=test_text.replace(old,new,1)
    test_copy = HERE / test_original.name
    test_copy.write_text(test_text,encoding='utf8')
    write(HERE/'integration_test_redirect.json',dict(original=str(test_original),original_sha256=sha(test_original),
        executed=str(test_copy),executed_sha256=sha(test_copy),assertions_unchanged=True))
    execute('software_additional', PY + ['-m', 'pytest', project / 'test_guards.py',
        test_copy, '-q', '-p', 'no:cacheprovider',
        '--basetemp', 'F:/Vivado_Output/a4reg_extra_temp', '--junitxml', HERE / 'software_additional.xml'], cwd=HERE.parent)
    execute('output_sum_unit', PY + [ROOT / 'qick/firmware/ip/axis_output_sum_v1/validation/run_unit.py',
        '--build', 'F:/Vivado_Output/a4reg_sum1'])

    spec = importlib.util.spec_from_file_location('v4_system_runner', ROOT / 'qick/firmware/ip/axis_output_sum_v1/validation/run_system.py')
    runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    cases = [(name, runner.arguments(SIM,name,cfg,TAG), runner.folder(SIM,name,cfg,TAG))
             for name,cfg in runner.CASES.items()]
    cfg = dict(sweep='rf_duration',count=10,mode='fixed_voltage',policy='overlap_readout',delay=0.)
    cases.append(('reversed_axes', runner.arguments(SIM,'reversed_axes',cfg,TAG) +
        ['--reverse-axes', '--cross-capacitance','1','.23','-.17','1','--dac-current-ma','20','10','20'],
        runner.folder(SIM,'reversed_axes',cfg,TAG)))
    stability = generate_stability()
    cases.append(('stability', PY + [stability, '--build',SIM,'--gui',GUI,'--vivado','F:/Xilinx/Vivado/2023.1/bin',
        '--awg-v3','--output-sum','--repeat-reset','--isolated-run','--no-aux','--v2-fixture','stability',
        '--grid-count','10','--dc-mode','fixed_time','--grid-x-mv','-15','15','--grid-y-mv','15','-15',
        '--cross-capacitance','1','.23','-.17','1','--dac-current-ma','20','10','20',
        '--reverse-axes','--run-tag',TAG+'_stability'],
        SIM / ('rc_precomp_repeat_reset_no_aux_grid_10x10_'+TAG+'_stability_output_sum_awg_v3_stability')))

    # Two already requested exact-duration fixtures, rerun under new names.
    old = HERE.parent / 'hold10us_gui_rtl'
    hold_source = (old / 'run_case.py').read_text(encoding='utf8')
    assert hold_source.count("v4_exact10us_hold{args.hold}") == 1
    hold_source = hold_source.replace('v4_exact10us_hold{args.hold}', TAG+'_exact10us_hold{args.hold}')
    (HERE / 'run_hold.py').write_text(hold_source, encoding='utf8')
    shutil.copy2(old / 'hold10us_support.py', HERE / 'hold10us_support.py')
    for hold in (1,2):
        cases.append((f'exact10us_hold{hold}', PY + [HERE/'run_hold.py','--hold',str(hold)],
            SIM / f'rc_precomp_repeat_reset_hold_duration_2x2_{TAG}_exact10us_hold{hold}_output_sum_awg_v3'))
    for name, argv, folder in cases:
        if folder.exists(): raise RuntimeError('Existing case: '+str(folder))
        state['cases'][name] = dict(folder=str(folder), state='pending')
    save()
    prepared = []
    for name, argv, folder in cases:
        state['cases'][name]['state'] = 'preparing';save()
        if not execute(name+'_prepare', argv + ['--prepare-only']):
            state['cases'][name]['state'] = 'failed_prepare';save();continue
        state['cases'][name]['state'] = 'prepared';save()
        prepared.append((name,argv,folder))
    def run_case(name,argv,folder):
        with lock:
            state['cases'][name]['state'] = 'running';save()
        ok = execute(name+'_rtl', argv + ['--reuse-snapshot'])
        with lock:
            state['cases'][name]['state'] = 'passed' if ok else 'failed'
            if ok:
                result = json.loads((folder/'result.json').read_text())
                assert result['validation_status'] == 'passed'
                state['cases'][name]['result'] = result
            save()
    def run_rc():
        if execute('rc48', PY + [VALID/'run_width_comparison.py','--width','48','--build','F:/Vivado_Output/a4reg_rc48']):
            execute('rc48_report', PY + [VALID/'report_selected48.py','--build','F:/Vivado_Output/a4reg_rc48','--out',HERE/'selected48'])
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(run_rc)] + [pool.submit(run_case,*case) for case in prepared]
        for future in as_completed(futures): future.result()
    execute('scope_after', PY + [project/'validate_scope.py'])
    changed = [p for p,h in hashes.items() if not Path(p).is_file() or sha(p) != h]
    state['changed_sources_settings_or_firmware'] = changed
    state['complete'] = regular['complete'] and not changed and all(v['state']=='passed' for v in state['stages'].values())
    state['stage'] = 'finished' if state['complete'] else 'finished_with_failures'
    state['finished_utc'] = datetime.now(timezone.utc).isoformat()
    save()
    raise SystemExit(0 if state['complete'] else 1)


if __name__ == '__main__': main()
