"""Additional user-requested GUI -> real RTL 10 us ramp/hold regression.

Preserves all production sources and original validation evidence. Generates a
reviewable, dedicated copy of the existing harness with only fixture changes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ORIGINAL = ROOT / 'qick/firmware/ip/rc_precomp_validation/verify_gui_rtl.py'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hold', type=int, choices=(1, 2), required=True)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--reuse-snapshot', action='store_true')
    parser.add_argument('--analyze-only', action='store_true')
    args = parser.parse_args()
    source = ORIGINAL.read_text(encoding='utf8')

    def change(old, new):
        nonlocal source
        assert source.count(old) == 1, old
        source = source.replace(old, new, 1)

    change('HERE=Path(__file__).resolve().parent', f'HERE=Path({str(ORIGINAL.parent)!r})')
    change('    code=generate_qick_program_code(pulses,awg_channels=awg_channels,full_scale_mv=800.,',
           f'''    # Dedicated exact-duration fixture; no sweep changes these durations.
    for pulse, scale in zip(pulses, (1., -.5, .25)):
        pulse.t=np.array([0.,1000.,11000.,21000.,31000.,41000.])
        pulse.v=np.array([0.,0.,10.,10.,0.,0.])*scale
        pulse.segment_names=['initial_zero','hold_1','hold_2']
    axes=[]
    rf_specs=[replace(spec,segment_name='set_{args.hold}',delay_us=0.,duration_us=10.,
                      duration_sweep_enabled=False,segment_length_mode='fixed') for spec in rf_specs]
    rf_duration_start=rf_duration_stop=10.
    code=generate_qick_program_code(pulses,awg_channels=awg_channels,full_scale_mv=800.,''')
    change('    points=program.sequence.sweep_point_count',
           '''    (out/'compiled_timing.json').write_text(json.dumps(dict(
        segment_starts=program.timing['segment_starts'],segment_ends=program.timing['segment_ends'],
        timing_repr=repr(program.timing),aux_timing_repr=repr(program.aux_timing),
        segments=[vars(s) for s in program.sequence.segments]),indent=2,default=str))
    points=program.sequence.sweep_point_count''')
    change('        top=sum_validation.monitor(top, shots, program, out, args)',
           '''        top=sum_validation.monitor(top, shots, program, out, args)
        from hold10us_support import extra_monitor
        top=extra_monitor(top).replace('cycle<12000', 'cycle<60000')''')
    change('zip(program.sequence.sweep_axes,coordinates) if isinstance(axis,RfDurationSweep)),30.)',
           'zip(program.sequence.sweep_axes,coordinates) if isinstance(axis,RfDurationSweep)),3000.)')
    change('summary[\'output_sum\']=sum_validation.analyze(out,result,model,offset,shots,args.sum_rf_delay_us)',
           f'''from hold10us_support import analyze
        summary['output_sum']=analyze(out,result,model,offset,shots,{args.hold})''')
    generated = HERE / f'verify_hold{args.hold}_generated.py'
    generated.write_text(source, encoding='utf8')
    (HERE / f'harness_hold{args.hold}.json').write_text(json.dumps(dict(
        original=str(ORIGINAL),original_sha256=hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
        generated=str(generated),generated_sha256=hashlib.sha256(generated.read_bytes()).hexdigest(),
        sequence_us=[10,10,10,10], initial_set_us=1, rf_anchor=f'set_{args.hold}',
        rf_duration_us=10, repetitions=2, awg_channels=[1,3,5],rf_channels=[0,2,4]),indent=2))
    command = [sys.executable,'-X','utf8',str(generated),
        '--build','F:/Vivado_Output/a3sim1','--gui',str(ROOT.parent/'PulseGenerator'),
        '--vivado','F:/Xilinx/Vivado/2023.1/bin','--awg-v3','--output-sum',
        '--repeat-reset','--isolated-run','--verify-gui-widgets',
        '--sweep-case','hold_duration','--sweep-count','2',
        '--run-tag',f'v4_exact10us_hold{args.hold}','--dc-mode','fixed_time',
        '--capture-cycles','60000']
    if args.prepare_only: command.append('--prepare-only')
    if args.reuse_snapshot: command.append('--reuse-snapshot')
    if args.analyze_only: command.append('--analyze-only')
    raise SystemExit(subprocess.call(command, cwd=ROOT))


if __name__ == '__main__':
    main()
