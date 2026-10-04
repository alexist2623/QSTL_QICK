"""Run relevant GUI/compiler tests in isolated processes with real exit codes."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--gui',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--modules',nargs='+',help='Rerun only changed modules, retaining other recorded exits.')
    args=parser.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    modules=args.modules or ['test_bias_t_set_spacing','test_incremental_virtual_grid','test_awg_tuning_v2','test_gui_shutdown',
             'test_qick_fine_tune_sweep','test_rc_sweep_matrix','test_rf_duration_oneshot',
             'test_stability_diagram','test_rc_precompensation','test_dc_readout_timing',
             'test_dc_waveform_gui_rf','test_qick_qcodes_experiment','test_qick_output_triggers']
    status=args.out/'exit_codes.json'
    results=json.loads(status.read_text()) if args.modules and status.exists() else []
    results=[r for r in results if r['module'] not in modules]
    for module in modules:
        with (args.out/f'{module}.log').open('w') as stream:
            run=subprocess.run([sys.executable,'-X','faulthandler','-m','pytest','-q',module+'.py',
                                '--disable-warnings'],cwd=args.gui/'DCWaveformGeneratorGUI',
                               stdout=stream,stderr=subprocess.STDOUT)
        result=dict(module=module,exit_code=run.returncode);results.append(result)
        (args.out/'exit_codes.json').write_text(json.dumps(results,indent=2))
        print(result,flush=True)
    if any(r['exit_code'] for r in results):raise SystemExit(1)


if __name__=='__main__':main()
