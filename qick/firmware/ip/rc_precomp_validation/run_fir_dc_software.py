"""Run GUI validation modules in separate Qt processes and retain exit codes."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--gui',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    names=('test_qick_fine_tune_sweep','test_dc_waveform_gui_rf','test_qick_qcodes_experiment',
           'test_fir_rate_gui','test_acquisition_segment_timing','test_qick_output_triggers',
           'test_dc_readout_timing')
    def run(name):
        with (args.out/(name+'.log')).open('w',encoding='utf-8') as stream:
            completed=subprocess.run([sys.executable,'-X','faulthandler','-m','pytest',
                f'DCWaveformGeneratorGUI/{name}.py','-q','--tb=short'],cwd=args.gui,
                stdout=stream,stderr=subprocess.STDOUT)
        print(name,completed.returncode,flush=True)
        return name,completed.returncode
    with ThreadPoolExecutor(max_workers=2) as executor:
        results=dict(executor.map(run,names))
    (args.out/'exit_codes.json').write_text(json.dumps(results,indent=2))
    if any(results.values()): raise SystemExit(1)

if __name__=='__main__': main()
