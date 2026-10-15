"""One completed real RTL trace; no additional simulation or source mutation."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
FOLDER = Path('F:/Vivado_Output/a5matrix1/rc_precomp_repeat_reset_hold_duration_3x3_v5matrix_20261015_hold_fixed_time_rf100ns_output_sum_awg_v3')

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    result = json.loads((FOLDER / 'result.json').read_text())
    oracle = json.loads((FOLDER / 'independent_matrix_oracle.json').read_text())
    assert result['validation_status'] == 'passed'
    fig, axes = plt.subplots(3, 2, figsize=(13, 8), constrained_layout=True)
    provenance = {'source_folder': str(FOLDER), 'case': 'hold_fixed_time', 'fixture': 'explicit RF +100ns variant', 'sources': {}}
    for row, pair in enumerate(result['output_sum']['pairs']):
        measurement = pair['measurements'][0]
        anchor = measurement['awg_hold_physical_start']
        path = FOLDER / f"physical_{pair['suffix']}.csv"
        values = []
        times = []
        with path.open() as stream:
            for sample in csv.DictReader(stream):
                cycle = int(sample['cycle'])
                t = (cycle - anchor) / 300
                if t < -.12:
                    continue
                if t > 1.12:
                    break
                word = int(sample['dac'], 16)
                lanes = [(word >> (16 * i)) & 65535 for i in range(16)]
                values.extend(v - 65536 if v >= 32768 else v for v in lanes)
                times.extend((cycle - anchor + np.arange(16) / 16) / 300)
        provenance['sources'][str(path)] = sha(path)
        times = np.asarray(times)
        values = np.asarray(values)
        rf_start = (measurement['rf_physical_start'] - anchor) / 300
        rf_end = (measurement['rf_physical_stop'] - anchor) / 300
        assert rf_start == .1 and rf_end == .2
        for col, limits in enumerate(((-.1, 1.1), (.08, .22))):
            ax = axes[row, col]
            ax.plot(times, values, color='#165b8e', linewidth=.75, label='Actual final DAC RTL samples')
            ax.axhline(oracle['base_codes'][row], color='#805c27', linestyle='--', linewidth=.9, label='Quantized C × V HOLD target')
            ax.axvspan(rf_start, rf_end, color='#000000', alpha=.07)
            ax.set_xlim(*limits)
            ax.grid(alpha=.18)
            ax.set_ylabel(f'AWG {2 * row + 1} + RF {2 * row}\nDAC code')
            ax.set_title('First HOLD, full interval' if col == 0 else 'RF burst detail')
            if row == 2:
                ax.set_xlabel('Time from HOLD reference (µs)')
        axes[row, 0].text(.26, .91, 'RF +100ns', transform=axes[row, 0].get_xaxis_transform(), fontsize=8)
    axes[0, 0].legend(loc='upper right', fontsize=8)
    fig.suptitle('Current GUI → v5 RTL: virtual-matrix HOLD sweep, first point / first repetition\n'
        'C = [[1, .23, −.11], [−.17, 1, .07], [.12, −.09, 1]]; virtual V = [5, −5, 2.5] mV', fontsize=12)
    fig.supxlabel('Final digital output trace, not a board measurement. HOLD reference uses command time + verified transport latency.\n'
        'IIR/DC compensation changes the baseline around the target; original zero-offset request remains separately rejected.', fontsize=9)
    dest = HERE / 'matrix_v5_actual_trace_v2.png'
    assert not dest.exists()
    fig.savefig(dest, dpi=160)
    plt.close(fig)
    matrix_dest = HERE / 'matrix_v5_actual_dialog.png'
    assert matrix_dest.exists() and sha(matrix_dest) == sha(FOLDER / 'matrix_input.png')
    provenance['figure'] = {'path': str(dest), 'sha256': sha(dest)}
    provenance['matrix_dialog'] = {'path': str(matrix_dest), 'sha256': sha(matrix_dest)}
    provenance['sources'][str(FOLDER / 'result.json')] = sha(FOLDER / 'result.json')
    provenance['sources'][str(FOLDER / 'independent_matrix_oracle.json')] = sha(FOLDER / 'independent_matrix_oracle.json')
    (HERE / 'plot_provenance_v2.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    print(dest)

if __name__ == '__main__':
    main()
