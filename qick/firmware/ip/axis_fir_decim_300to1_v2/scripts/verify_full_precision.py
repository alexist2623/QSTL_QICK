"""Exact Python-integer reference, RTL vectors, and low-signal error plots.

Inputs are synthetic *post-QICK* signed int16 I/Q, not an ADC/RF model.
Sub-LSB means use deterministic adjacent-code density; already-zero input
cannot be recovered. The power labels use nominal I amplitude with
0 dBm = 32767 peak codes and Q = -I/10 (not calibrated total RF power).
"""
from pathlib import Path
import argparse
import json
import math
import re
import numpy as np

IP = Path(__file__).resolve().parents[1]


def coefficients():
    source = (IP / 'src/fir_decim_300to1_v2_coeffs_pkg.sv').read_text()
    values = [int(sign + value) for sign, value in
              re.findall(r"fir_coeff = (-?)18'sd(\d+)", source)]
    assert len(values) == 95 + 127 + 161
    return [values[:95], values[95:222], values[222:]]


def decimate(data, coeff, factor):
    # Python arbitrary-precision integers: never float64 or overflowing int64.
    padded = [(0, 0)] * (len(coeff)-1) + data
    return [tuple(sum(int(padded[n+len(coeff)-1-k][lane])*c
                      for k, c in enumerate(coeff)) for lane in range(2))
            for n in range(factor-1, len(data), factor)]


def round_shift(value, bits):
    return (-1 if value < 0 else 1) * ((abs(value)+(1 << (bits-1))) >> bits)


def density(mean, count):
    # Exact adjacent integer codes whose long-term mean approaches 'mean'.
    return np.diff(np.floor(np.arange(count+1)*mean)).astype(np.int16)


def write_hex(path, data, width):
    mask = (1 << width)-1
    path.write_text(''.join(f'{((int(q)&mask)<<width)|(int(i)&mask):0{width//2}x}\n'
                            for i, q in data))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=IP/'vectors')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    coeffs = coefficients()
    bound = 32768
    bounds = []
    for coeff, width in zip(coeffs, [34, 51, 69]):
        bound *= sum(abs(c) for c in coeff)
        assert bound < 1 << (width-1)
        bounds.append({'width': width, 'absolute_bound': bound,
                       'coefficient_l1': sum(abs(c) for c in coeff)})
    assert round_shift(bound, 5) < 1 << 63
    n = 30000
    cases = [('measurement_scale', -33.0, 3.0),
             ('sub_lsb', -0.33, 0.03), ('very_weak', -0.0033, 0.0003)]
    for power in [-60, -70, -80, -90]:
        amplitude = 32767 * 10**(power/20)
        cases.append((f'{power}_dBm', -amplitude, amplitude/10))
    source = []
    for name, i, q in cases:
        source.extend(zip(density(i, n).tolist(), density(q, n).tolist()))
    rng = np.random.default_rng(190)
    source.extend(map(tuple, rng.integers(-32768, 32768, (n, 2)).tolist()))
    source.extend([(32767, -32768)]*n)
    source.extend([(-32768, 32767)]*n)
    source.extend([(0, 0)]*n)
    stages = []
    exact = source
    for c, d in zip(coeffs, [10, 10, 3]):
        exact = decimate(exact, c, d)
        stages.append(exact)
    stored = [tuple(round_shift(v, 5) for v in pair) for pair in exact]
    assert all(-(1 << 63) <= v < 1 << 63 for p in stored for v in p)
    error_numerators = [abs(v*32-ref) for p, r in zip(stored, exact) for v, ref in zip(p, r)]
    assert max(error_numerators) <= 16
    old = source
    for c, d in zip(coeffs, [10, 10, 3]):
        old = [tuple(max(-32768, min(32767, round_shift(v, 17))) for v in pair)
               for pair in decimate(old, c, d)]
    write_hex(args.output/'input.hex', source, 16)
    for k, (stage, width) in enumerate(zip(stages, [34, 51, 69])):
        # Nibble padding uses ceil(2*width/4); values remain lane packed.
        mask = (1 << width)-1
        (args.output/f'stage{k}.hex').write_text(''.join(
            f'{((q&mask)<<width)|(i&mask):0{math.ceil(width/2)}x}\n' for i, q in stage))
    write_hex(args.output/'stored.hex', stored, 64)
    (args.output/'counts.txt').write_text(' '.join(map(str, [len(source), *map(len, stages)])))
    rows = []
    gain = math.prod(sum(c) for c in coeffs)/(2**51)
    for k, (name, i, q) in enumerate(cases):
        selected = slice(k*n//300+75, (k+1)*n//300)
        rows.append({'case': name, 'input_mean_i': i, 'input_mean_q': q,
                     'exact_reference_mean_i_input_codes': float(np.mean([p[0]/2**51 for p in exact[selected]])),
                     'exact_reference_mean_q_input_codes': float(np.mean([p[1]/2**51 for p in exact[selected]])),
                     'new_mean_i_input_codes': float(np.mean([p[0]/2**46 for p in stored[selected]])),
                     'new_mean_q_input_codes': float(np.mean([p[1]/2**46 for p in stored[selected]])),
                     'old_mean_i_input_codes': float(np.mean([p[0] for p in old[selected]])),
                     'old_mean_q_input_codes': float(np.mean([p[1] for p in old[selected]]))})
    report = {'input': 'synthetic post-QICK int16 IQ; adjacent-code density for sub-LSB means',
              'power_label_basis': 'nominal I amplitude: 32767 * 10**(dBm/20); Q=-I/10',
              'bounds': bounds, 'dc_gain': gain, 'input_count': len(source),
              'stage_counts': list(map(len, stages)), 'integer_storage_bits_per_lane': 64,
              'maximum_final_error_input_codes': max(error_numerators)/2**51,
              'intermediate_removed_bits': 0, 'final_removed_bits': 5, 'cases': rows}
    (args.output/'reference_report.json').write_text(json.dumps(report, indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    for column, k in enumerate([0, 1]):
        # Show settled weak signals at their own scale rather than hiding
        # them under the transition from the preceding larger segment.
        begin = 60 if k == 1 else 0
        sl = slice(k*n//300+begin, (k+1)*n//300)
        x = np.arange(begin, n//300)
        for lane, label in enumerate(['I', 'Q']):
            ax = axes[lane, column]
            ax.plot(x, [p[lane]/2**51 for p in exact[sl]], label='Exact integer reference', linewidth=2)
            ax.plot(x, [p[lane]/2**46 for p in stored[sl]], '--', label='int64 storage')
            ax.step(x, [p[lane] for p in old[sl]], where='mid', label='Legacy int16 after each FIR', alpha=.7)
            ax.set(title=f'{cases[k][0]} / {label}', xlabel='Time within segment (us)', ylabel='Input-code units')
            ax.grid(alpha=.25)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('Three FIRs, 300 MSPS → 1 MSPS: exact arithmetic vs stored output\nSynthetic post-demodulation integer input; no ADC/RF noise model')
    fig.tight_layout()
    fig.savefig(args.output/'precision_comparison.png', dpi=160)
    fig2, ax2 = plt.subplots(1, 2, figsize=(12, 4))
    power_rows=rows[3:]
    powers=[int(row['case'].split('_')[0]) for row in power_rows]
    ax2[0].plot(powers,[row['new_mean_q_input_codes'] for row in power_rows], 'o-',label='int64 storage')
    ax2[0].plot(powers,[row['old_mean_q_input_codes'] for row in power_rows], 's--',label='Legacy int16 after each FIR')
    ax2[0].set(xlabel='Nominal I-equivalent power (dBm)',ylabel='Settled Q mean (input codes)',title='Weak quadrature survives (Q = -I/10)')
    ax2[0].legend(fontsize=8); ax2[0].grid(alpha=.25)
    signed_errors=[(p[0]*32-ref[0])/2**51 for p,ref in zip(stored,exact)]
    ax2[1].plot(signed_errors, linewidth=.6)
    ax2[1].set(xlabel='1 MSPS output sample',ylabel='Error relative to exact integer FIR (input codes)',title='Only final 69 → 64 rounding error')
    ax2[1].grid(alpha=.25)
    fig2.suptitle('Synthetic post-QICK int16 IQ; 0 dBm = 32767 peak I codes assumed')
    fig2.tight_layout(); fig2.savefig(args.output/'low_power_and_error.png',dpi=160)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
