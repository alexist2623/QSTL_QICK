"""Small actual-RTL matrix for FIR/DC order; bounded traces and isolated runs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--gui', type=Path, required=True)
    args = parser.parse_args()
    output = args.build/'fir_dc_matrix_v4'
    output.mkdir(exist_ok=True)
    cases = [
        ('hold_overlap', 'hold_duration', 'overlap_readout', 'fixed_time'),
        ('hold_after', 'hold_duration', 'after_readout', 'fixed_time'),
        ('ramp_overlap', 'ramp_rate', 'overlap_readout', 'fixed_voltage'),
        ('ramp_after', 'ramp_rate', 'after_readout', 'fixed_voltage'),
        ('rf_overlap', 'rf_duration', 'overlap_readout', 'fixed_time'),
        ('rf_after', 'rf_duration', 'after_readout', 'fixed_time'),
        ('voltage_overlap', None, 'overlap_readout', 'fixed_voltage'),
        ('voltage_after', None, 'after_readout', 'fixed_voltage'),
    ]
    running, status = [], {}
    def save():
        (output/'status.json').write_text(json.dumps(status, indent=2))
    def poll():
        for name, process, stream in list(running):
            if process.poll() is not None:
                stream.close()
                status[name] = dict(state='passed' if process.returncode == 0 else 'failed', code=process.returncode)
                print(name, status[name], flush=True)
                running.remove((name, process, stream))
                save()
    script = Path(__file__).with_name('verify_gui_rtl.py')
    for name, sweep, policy, mode in cases:
        while len(running) >= 3:
            time.sleep(1)
            poll()
        command = [sys.executable, str(script), '--build', str(args.build), '--gui', str(args.gui),
                   '--awg-v2', '--repeat-reset', '--isolated-run', '--run-tag', 'fir_dc4_'+name,
                   '--dc-mode', mode, '--dc-readout-policy', policy]
        command += ['--sweep-case', sweep, '--sweep-count', '3'] if sweep else ['--grid-count', '3', '--no-aux']
        # Elaborate sequentially: these use shared compiled Vivado libraries.
        with (output/(name+'_prepare.log')).open('w') as stream:
            result = subprocess.run(command+['--prepare-only'], stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            status[name] = dict(state='prepare_failed', code=result.returncode)
            save()
            continue
        stream = (output/(name+'.log')).open('w')
        process = subprocess.Popen(command+['--reuse-snapshot'], stdout=stream, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        running.append((name, process, stream))
        status[name] = dict(state='running', pid=process.pid)
        save()
        poll()
    while running:
        time.sleep(1)
        poll()
    if any(value['state'] != 'passed' for value in status.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
