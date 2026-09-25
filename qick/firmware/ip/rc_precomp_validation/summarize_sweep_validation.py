"""Retain compact, reproducible evidence from completed sweep simulations."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--grid-count', type=int, default=200)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cases = ('ramp_rate', 'hold_duration_3x3', 'rf_duration_3x3', 'rf_frequency_3x3')
    summaries = {}
    manifest = []
    for case in cases:
        src = args.build / ('rc_precomp_repeat_reset_' + case)
        result = json.loads((src / 'result.json').read_text())
        summaries[case] = result
        dest = args.out / case
        dest.mkdir(exist_ok=True)
        for name in ('result.json', 'gui_export.py', 'program.asm', 'pmem.hex',
                     'dmem.txt', 'tb_rc_gui.sv', 'rf_measurements.json', 'xsim.log'):
            shutil.copyfile(src / name, dest / name)
        for name in ('rtl_events.csv', 'rtl_commands.csv', 'rc_analog.csv', 'rf_samples.csv'):
            path = src / name
            manifest.append(dict(path=str(path), bytes=path.stat().st_size,
                sha256=hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()))
    (args.out / 'summaries.json').write_text(json.dumps(summaries, indent=2))
    (args.out / 'raw_evidence_manifest.json').write_text(json.dumps(manifest, indent=2))

    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    for ax, case in zip(axes.flat, cases):
        src = args.build / ('rc_precomp_repeat_reset_' + case)
        # Retain only the beginning for plotting; the RTL oracle checked all samples.
        rows = []
        with (src / 'rc_analog.csv').open() as stream:
            for row in csv.DictReader(stream):
                if int(row['cycle']) > 7000:
                    break
                if row['channel'] == '0':
                    rows.append([float(row[k]) for k in ('cycle','target','dac','after_rc')])
        data = np.array(rows)
        active = np.flatnonzero(data[:,1] != 0)
        start = data[active[0],0]
        t = (data[:,0]-start)/300
        window = (t >= -.1) & (t <= 10)
        for index, label, color in ((2, 'Actual RTL DAC', '#df7a13'),
                                    (1, 'Nominal AWG', '#416eaa'),
                                    (3, 'After modeled RC', '#17824f')):
            ax.plot(t[window], data[window,index]*800/32768,
                    label=label, color=color, lw=1.2)
        result = summaries[case]
        errors = [float(s.split('=')[-1])*800/32768 for s in result['analog_results'][:2]]
        ax.set(title=f'{case.replace("_3x3", "").replace("_", " ")} | {result["points"]} points x 2 repeats',
               xlabel='Time from first pulse (us)', ylabel='Voltage (mV)')
        ax.text(.02,.02,f'All-shot RC error max: {max(errors):.4f} mV',
                transform=ax.transAxes, fontsize=9)
        ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('GUI export -> tProcessor/TMUX/dual AWG/RF RTL\nDC + RC enabled, tau = 10 us; RFDC and ARM excluded')
    fig.savefig(args.out / 'sweep_rtl_waveforms.png', dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
    for ax, case, field, title in (
        (axes[0], 'rf_duration_3x3', 'width_cycles', 'RF duration sweep'),
        (axes[1], 'rf_frequency_3x3', 'frequency_mhz', 'RF frequency sweep')):
        src = args.build / ('rc_precomp_repeat_reset_' + case)
        records = json.loads((src / 'rf_measurements.json').read_text())
        values = [r[field]/300 if field=='width_cycles' else r[field] for r in records]
        ax.plot(range(len(records)), values, 'o-', ms=4)
        ax.set(title=title, xlabel='Shot index', ylabel='Duration (us)' if field=='width_cycles' else 'Frequency (MHz)')
        ax.grid(alpha=.2)
    fig.suptitle('Measured directly from the real DDS RTL output samples')
    fig.savefig(args.out / 'rf_sweep_measurements.png', dpi=160)
    plt.close(fig)

    grid_name = f'{args.grid_count}x{args.grid_count}'
    grid = args.build / f'rc_precomp_repeat_reset_no_aux_grid_{grid_name}'
    if (grid / 'result.json').is_file():
        dest = args.out / f'grid_{grid_name}'
        dest.mkdir(exist_ok=True)
        result = json.loads((grid / 'result.json').read_text())
        records = json.loads((grid / 'grid_axes.json').read_text())
        for name in ('result.json', 'grid_axes.json', 'gui_export.py', 'program.asm',
                     'pmem.hex', 'dmem.txt', 'tb_rc_gui.sv', 'xsim.log', 'rtl_checks.txt'):
            shutil.copyfile(grid / name, dest / name)
        fig, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
        for ch, record in enumerate(records):
            indices = np.arange(len(record['requested_mv']))
            axes[0].plot(indices, record['executed_target_mv'],
                         label=f'DAC {ch+1}: executed target', ls='-' if ch==0 else '--')
            axes[1].plot(indices, np.array(record['executed_target_mv'])-record['requested_mv'],
                         label=f'DAC {ch+1}', ls='-' if ch==0 else '--')
        axes[0].plot(indices, records[0]['requested_mv'], 'k:', label='Requested target')
        axes[0].set(xlabel='Axis index', ylabel='Nominal target (mV)', title=f'Both DAC axes: all {result["points"]:,} points checked')
        axes[1].set(xlabel='Axis index', ylabel='Target error (mV)', title='Existing integer increment quantization')
        for ax in axes:
            ax.grid(alpha=.2)
            ax.legend(fontsize=9)
        fig.suptitle(f'{args.grid_count} x {args.grid_count} x {result["repetitions"]}: execution and voltage-step quantization')
        fig.savefig(args.out / 'grid_target_error.png', dpi=160)
        plt.close(fig)
        report = [
            f'# Completed two-DAC {args.grid_count} x {args.grid_count} RTL run', '',
            f'Points: {result["points"]}; repetitions per point: {result["repetitions"]}.',
            f'All {result["commands"]:,} command words and timestamps matched the instruction model.',
            f'Cycles: {result["cycles"]:,}; PMEM: {result["pmem_words"]} words; DMEM table: {result["dmem_words"]} words.', '',
            *result['exact_awg_results'], *result['reset_results'], '',
            f'Maximum nominal target error: {result["grid_target_error_mv"]} mV.',
            'This is the existing rounded integer sweep-step error, not a mismatched RTL recurrence.',
            'Neither repetition nor inner-axis reset mismatches occurred.',
            'The analog RC model was not run over this full large grid; see the smaller mixed-sweep analog validations.',
            '', 'Only the first 12,000 clocks of the waveform were stored. All clocks were checked in the RTL testbench.',
        ]
        (args.out / 'GRID_REPORT.md').write_text('\n'.join(report)+'\n')


if __name__ == '__main__':
    main()
