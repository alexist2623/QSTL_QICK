"""Read-only review of two previously captured DC/RC waveform examples.

Writes new evidence only beside this file. Does not open instruments or change
the original global alignment, offsets, analysis policies, sources or verdicts.
"""
from pathlib import Path
import csv
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OLD = HERE.parents[1] / 'physical_compensation_100x100_20261015'
sys.path.insert(0, str(OLD / 'model_review'))
spec = importlib.util.spec_from_file_location('previous_capture_analyzer', OLD / 'analyze_physical.py')
analyzer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyzer)
hashes = {}


def protect(path):
    path = Path(path)
    hashes[str(path)] = analyzer.sha(path)
    return path


def read(path):
    return analyzer.read(protect(path))


def write_json(name, value):
    path = HERE / name
    if path.exists():
        raise FileExistsError(path)
    analyzer.dump(path, value)


def evaluate(model, times):
    return np.array([model.at_program_us(float(t))['expected_direct_dac_mv'] for t in times])


def stitched(models, times):
    origins = np.array([m.origin_scalar / m.scalar_mhz for m in models])
    return np.array([models[max(0, int(np.searchsorted(origins, t, side='right')) - 1)].at_program_us(float(t))['expected_direct_dac_mv'] for t in times])


def dense_times(models, low, high):
    # Display every short DC scalar sample and both sides of each exact run
    # boundary; longer regions need only a 20ns grid. Raw data is never resampled.
    result = list(np.arange(low, high, .02))
    for m in models:
        boundaries = [m.origin_scalar] + [m.origin_scalar + end for end in m.waveform.ends]
        for boundary in boundaries:
            for fraction in (-.25, .25):
                t = (boundary + fraction) / m.scalar_mhz
                if low <= t <= high:
                    result.append(t)
        if m.dc_end_scalar - m.dc_start_scalar < 5000:
            result.extend((np.arange(m.dc_start_scalar, m.dc_end_scalar) + .25) / m.scalar_mhz)
    return np.unique(np.array([t for t in result if low <= t <= high]))


def main():
    for path in [OLD / 'analyze_physical.py', OLD / 'model_review/command_expectation.py', OLD / 'model_review/compact_expectation.py']:
        protect(path)
    result = dict(new_hardware_execution=False, existing_sources_and_evidence_changed=False,
                  original_offsets_and_verdicts_unchanged=True, cases={})
    for label, point_index, selected in [('fixed_voltage_tau10', 5050, [5049, 5050, 5051]),
                                          ('fixed_time30_tau20', 9999, [9998, 9999])]:
        prepared = OLD / ('offline_range300_' + label)
        run = OLD / ('run_' + label + '_01')
        previous_analysis = OLD / ('analysis_' + label + '_01')
        expected = read(prepared / 'expected_points.json.gz')
        original = read(previous_analysis / 'results.json')
        alignment = read(previous_analysis / 'alignment.json')
        capture = read(run / 'scope_capture/capture.json')
        protect(previous_analysis / 'representative_waveforms.png')
        protect(previous_analysis / 'all_20000_dc_windows.csv')
        points = [expected['points'][i] for i in selected]
        channels = {}
        for ch in (1, 2):
            rec = capture['channels'][str(ch)]
            channels[ch] = analyzer.load_channel(run / 'scope_capture', rec)
            for path in channels[ch]['paths']:
                protect(path)
        case = dict(point_index=point_index, capture_id=capture['capture_id'],
                    points=points, point_spacing_cycles=expected['point_spacing_cycles'],
                    coordinate_order=expected['coordinate_order'], original_alignment=alignment,
                    fixed_offsets_mv=original['fixed_offsets_mv'], channel_diagnostics=[])
        fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
        csv_rows = []
        for axis in range(2):
            ch = axis + 1
            output = expected['points'][point_index]['outputs'][axis]
            model = analyzer.output_model(output)
            prior_output = expected['points'][point_index - 1]['outputs'][axis]
            prior_model = analyzer.output_model(prior_output)
            channel = channels[ch]
            offset = original['fixed_offsets_mv'][str(ch)]
            align_s = original['single_time_offset_s']
            hold = output['hold_digital_output_us']
            if point_index == 5050:
                bounds = [(-2, 23), (20.9, 22.1)]
                diagnostic_low, diagnostic_high = output['dc_start_digital_output_us'] - 1, output['dc_end_digital_output_us'] + 1
                models = [model]
            else:
                bounds = [(-65, 55), (-13, -9)]
                diagnostic_low, diagnostic_high = output['sequence_start_command_us'] - 1, output['sequence_start_command_us'] + 2
                models = [prior_model, model]
            l, r, raw_time, raw_mv = analyzer.window(channel, diagnostic_low * 1e-6 + align_s, diagnostic_high * 1e-6 + align_s)
            sample_rows = []
            for index, t_scope, value in zip(range(l, r), raw_time, raw_mv):
                t = (t_scope - align_s) * 1e6
                row = dict(case=label, channel=ch, native_sample_index=index, scope_time_s=float(t_scope),
                           program_us=float(t), time_from_current_hold_us=float(t - hold), raw_mv=float(value),
                           fixed_offset_mv=offset, corrected_mv=float(value - offset),
                           current_point_model_mv=model.at_program_us(t)['expected_direct_dac_mv'],
                           previous_point_model_mv=prior_model.at_program_us(t)['expected_direct_dac_mv'])
                sample_rows.append(row); csv_rows.append(row)
            dc_sc = np.arange(model.dc_start_scalar, model.dc_end_scalar)
            if point_index == 5050:
                dc_exact = evaluate(model, (dc_sc + .25) / model.scalar_mhz)
                inside = (raw_time >= output['dc_start_digital_output_us'] * 1e-6 + align_s) & (raw_time < output['dc_end_digital_output_us'] * 1e-6 + align_s)
            else:
                dc_exact = evaluate(prior_model, (np.array([prior_model.dc_end_scalar - 1]) + .25) / prior_model.scalar_mhz)
                inside = np.array([], dtype=bool)
            diagnostic = dict(channel=ch, sample_interval_ns=channel['preamble']['x_increment'] * 1e9,
                current_hold_us=hold, previous_hold_us=prior_output['hold_digital_output_us'],
                previous_dc_start_relative_us=prior_output['dc_start_digital_output_us'] - hold,
                previous_dc_end_relative_us=prior_output['dc_end_digital_output_us'] - hold,
                current_origin_relative_us=model.origin_scalar / model.scalar_mhz - hold,
                original_plot_start_relative_us=output['sequence_start_command_us'] - 1 - hold,
                current_dc_start_relative_us=output['dc_start_digital_output_us'] - hold,
                current_dc_end_relative_us=output['dc_end_digital_output_us'] - hold,
                dc_duration_ns=output['dc_duration_us'] * 1000,
                pre_dc_area_effective_code_samples=model.pre_dc_area, final_integer_area=model.waveform.area,
                model_dc_range_mv=[float(dc_exact.min()), float(dc_exact.max())],
                native_samples_in_current_dc_interval=int(inside.sum()) if point_index == 5050 else None,
                raw_near_feature=sample_rows)
            case['channel_diagnostics'].append(diagnostic)
            for row_index, (x0, x1) in enumerate(bounds):
                ax = axes[row_index, axis]
                lo, hi = hold + x0, hold + x1
                _, _, t_scope, volt = analyzer.window(channel, lo * 1e-6 + align_s, hi * 1e-6 + align_s)
                t = (t_scope - align_s) * 1e6
                grid = dense_times(models, lo, hi)
                ax.plot(t - hold, volt - offset, '.-', ms=4, lw=.65, label='Raw native samples; original fixed offset')
                ax.plot(grid - hold, stitched(models, grid), '-', lw=1, color='#e07000', label='Exact command model; interval-aware display')
                if point_index == 5050:
                    ax.plot(t - hold, evaluate(model, t), 'x', ms=4, color='#666666', label='Original model samples (500ns grid)')
                    ax.axvspan(output['dc_start_digital_output_us'] - hold, output['dc_end_digital_output_us'] - hold, alpha=.15, color='#a64a97', label='Requested fixed-voltage DC window')
                    if row_index == 1:
                        ax.text(.03, .97, '123.333ns model DC; zero native samples inside\nRaw spike at +21.603958us; no new time fit', transform=ax.transAxes, va='top', fontsize=8)
                else:
                    ax.axvspan(prior_output['dc_start_digital_output_us'] - hold, prior_output['dc_end_digital_output_us'] - hold, alpha=.12, color='#888888', label='Previous point 9998 DC tail')
                    ax.axvline(model.origin_scalar / model.scalar_mhz - hold, color='#222222', lw=.8, ls='--', label='Point9999 SET0 output')
                    if row_index == 1:
                        ax.plot(t - hold, evaluate(model, t), '--', lw=.8, color='#b00040', label='Original current-point-only model')
                ax.set(xlim=(x0, x1), xlabel='Time from point %d HOLD (us)' % point_index,
                       ylabel='Fixed-offset-corrected mV', title='DAC%d / CH%d' % (ch + 3, ch))
                ax.grid(alpha=.2); ax.legend(fontsize=7, loc='best')
        title = ('Point5050: intentional short -300mV DC compensation; original model display missed the interval'
                 if point_index == 5050 else 'Points9998 -> 9999: preceding negative DC tail is inside the original point9999 crop')
        fig.suptitle(title + '\nPreserved original global alignment and offsets; no new acquisition or verdict change', fontsize=12)
        png = HERE / (label + '_continuous_review.png')
        if png.exists():
            raise FileExistsError(png)
        fig.savefig(png, dpi=170); plt.close(fig)
        analyzer.csv_save(HERE / (label + '_raw_feature_samples.csv'), csv_rows)
        result['cases'][label] = case
    result['input_hashes'] = hashes
    result['input_hashes_unchanged'] = all(analyzer.sha(path) == old_hash for path, old_hash in hashes.items())
    assert result['input_hashes_unchanged']
    write_json('review_results.json', result)
    print(json.dumps(dict(complete=True, input_count=len(hashes), input_hashes_unchanged=True,
                         figures=['fixed_voltage_tau10_continuous_review.png', 'fixed_time30_tau20_continuous_review.png']), indent=2))


if __name__ == '__main__':
    main()
