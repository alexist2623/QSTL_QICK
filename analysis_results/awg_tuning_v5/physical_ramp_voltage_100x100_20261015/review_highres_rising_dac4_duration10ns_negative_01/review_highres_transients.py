"""Offline post-RAMP transient review; preserves the frozen primary analyzer.

This is a supplemental native-sample diagnostic, not a settling-time test.
The original analysis fixes both baseline and global time alignment; this
review never refits either quantity and never changes any original result.
"""
from pathlib import Path
import argparse
import csv
import gzip
import io
import json

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from analyze_highres import (HERE, MODEL_DIR, child, sha, read, dump,
                            load_channel, compiled, ramps, select, output_model)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--analysis', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    analysis, out = child(args.analysis), child(args.output)
    if out.exists():
        raise FileExistsError(out)
    original = read(analysis / 'results.json')
    assert original['analysis_complete'] and original['integrity_passed']
    inputs = read(analysis / 'input_hashes.json')
    assert all(sha(path) == value for path, value in inputs.items())
    for path in (analysis / 'results.json', analysis / 'input_hashes.json',
                 Path(__file__), HERE / 'analyze_highres.py',
                 MODEL_DIR / 'command_expectation.py', MODEL_DIR / 'compact_expectation.py'):
        inputs[str(path)] = sha(path)
    prepared, run = child(original['prepared_bundle']), child(original['source_run'])
    expected_path = prepared / 'expected_points.json.gz'
    if not expected_path.exists():
        expected_path = prepared / 'expected_points.json'
    expected = read(expected_path)
    capture = read(run / 'scope_capture/capture.json')
    assert capture['capture_id'] == original['capture_id']
    ch = int(original['active_channel'])
    channel = load_channel(run / 'scope_capture', capture['channels'][str(ch)])
    output = expected['points'][0]['outputs'][ch - 1]
    model = output_model(output)
    assert not model.metadata_step_mismatches
    alignment = original['single_time_offset_s']
    offset = original['fixed_offsets'][str(ch)]['median_mv']
    out.mkdir()
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    rows = []
    numeric = []
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    for col, ramp in enumerate(ramps(output)):
        start = ramp['end_us'] * 1e-6 + alignment
        stop = start + 100e-9
        a, b, valid = select(channel, start, stop)
        assert valid and np.isfinite(channel['mv'][a:b]).all()
        time = channel['time'][a:b]
        since = (time - start) * 1e9
        measured = channel['mv'][a:b] - offset
        reference = compiled(model, (time - alignment) * 1e6)
        error = measured - reference
        peak = int(np.argmax(np.abs(error)))
        minimum, maximum = int(np.argmin(measured)), int(np.argmax(measured))

        def sample(index):
            return dict(raw_sample_index=a + index,
                time_after_compiled_ramp_end_ns=float(since[index]),
                scope_time_s=float(time[index]),
                program_time_us=float((time[index] - alignment) * 1e6),
                corrected_measured_mv=float(measured[index]),
                exact_compiled_rc_dac_mv=float(reference[index]),
                residual_mv=float(error[index]))

        bins = []
        for lo in range(0, 100, 10):
            mask = (since >= lo) & (since < lo + 10)
            assert mask.any()
            bins.append(dict(start_after_ramp_end_ns=lo, stop_exclusive_ns=lo + 10,
                samples=int(mask.sum()), median_residual_mv=float(np.median(error[mask])),
                max_abs_residual_mv=float(np.max(np.abs(error[mask]))),
                samples_abs_error_over_15mv=int((np.abs(error[mask]) > 15.).sum())))
        rows.append(dict(direction=ramp['direction'], requested_ramp_duration_ns=ramp['requested_us'] * 1000,
            compiled_ramp_duration_ns=(ramp['end_us'] - ramp['start_us']) * 1000,
            post_ramp_window_ns=[0., 100.], window_end_exclusive=True,
            start_program_us=ramp['end_us'], stop_program_us=ramp['end_us'] + .1,
            roi_start_index=a, roi_stop_index_exclusive=b, samples=b-a,
            native_sample_interval_ns=channel['preamble']['x_increment'] * 1e9,
            original_ramp_roi_stop_index_exclusive=original['ramps'][col]['roi_stop_index_exclusive'],
            disjoint_from_original_ramp_roi=bool(a >= original['ramps'][col]['roi_stop_index_exclusive']),
            max_abs_residual_mv=float(np.max(np.abs(error))), peak_abs_residual=sample(peak),
            minimum_corrected_voltage=sample(minimum), maximum_corrected_voltage=sample(maximum),
            median_residual_mv=float(np.median(error)),
            samples_abs_error_over_15mv=int((np.abs(error) > 15.).sum()),
            ten_ns_bins=bins, settling_time_ns=None, settling_pass=None,
            settling_note='No analog settling criterion was specified. No settling time or pass is assigned; 10 ns bins are descriptive only.'))
        for j in range(b-a):
            numeric.append([ramp['direction'], a+j, float(since[j]), float(time[j]),
                            float(channel['mv'][a+j]), float(measured[j]),
                            float(reference[j]), float(error[j]), int(channel['codes'][a+j])])
        axes[0, col].plot(since, measured, lw=.75, label='Physical native RAW, fixed offset')
        axes[0, col].step(since, reference, where='post', lw=1, label='Exact compiled RC DAC')
        axes[0, col].scatter([since[peak]], [measured[peak]], color='red', s=22, zorder=5)
        axes[0, col].set(title=f'{ramp["direction"]}, requested {ramp["requested_us"]*1000:g} ns RAMP',
                         ylabel='mV')
        axes[1, col].plot(since, error, lw=.75)
        axes[1, col].axhline(15, color='grey', ls='--')
        axes[1, col].axhline(-15, color='grey', ls='--')
        axes[1, col].set(xlabel='Time after compiled RAMP end (ns)', ylabel='Measured minus model (mV)',
                         title=f'Native peak |residual| {np.max(np.abs(error)):.3f} mV; {int((np.abs(error)>15).sum())}/{len(error)} exceed 15 mV')
    for ax in axes.flat:
        ax.grid(alpha=.2)
        if ax.get_legend_handles_labels()[0]:
            ax.legend(fontsize=8)
    fig.suptitle(f'Physical DAC{output["panel_dac"]}: post-RAMP first 100 ns, requested {output["requested_mv"]:g} mV\n'
                 'Original fixed zero offset and one global alignment retained; no fitted gain or settling-time verdict', fontsize=11)
    fig.savefig(out / 'post_ramp_100ns.png', dpi=170)
    plt.close(fig)
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['direction', 'raw_sample_index', 'time_after_ramp_end_ns', 'scope_time_s',
                     'raw_scaled_mv', 'fixed_offset_corrected_mv', 'exact_compiled_rc_dac_mv', 'residual_mv', 'raw_code'])
    writer.writerows(numeric)
    csv_bytes = stream.getvalue().encode('utf8')
    compressed = gzip.compress(csv_bytes, mtime=0)
    (out / 'post_ramp_native_samples.csv.gz').write_bytes(compressed)
    assert gzip.decompress(compressed) == csv_bytes
    result = dict(complete=True, diagnostic_only=True, new_hardware_execution=False,
        original_analysis=args.analysis, source_run=original['source_run'], capture_id=original['capture_id'],
        active_channel=ch, offset_mv=offset, original_single_time_offset_s=alignment,
        no_refit=True, reference='Exact compiled command-word RC DAC model, evaluated at every native scope sample',
        threshold_mv=15., threshold_note='Strict abs(error)>15 mV count is descriptive and does not replace the original median HOLD criterion.',
        ramps=rows, native_rows=len(numeric), raw_reconstruction_verified=True,
        primary_results_unchanged=True, physical_settling_pass=None,
        limitations=['The first 100 ns after each RAMP is separate from its original RAMP-internal ROI.',
                     'Noise, oscilloscope bandwidth/quantization and analog response remain present; no calibrated accuracy or exact timing PASS is claimed.',
                     'Ten-ns bin medians do not establish analog settling.'])
    dump(out / 'results.json', result)
    dump(out / 'input_hashes.json', inputs)
    assert all(sha(path) == value for path, value in inputs.items())
    dump(out / 'manifest.json', dict(complete=True, source_inputs_unchanged=True,
        files={p.name:dict(bytes=p.stat().st_size, sha256=sha(p)) for p in out.iterdir() if p.is_file()}))
    print(json.dumps(dict(complete=True, ramps=rows), indent=2))


if __name__ == '__main__':
    main()
