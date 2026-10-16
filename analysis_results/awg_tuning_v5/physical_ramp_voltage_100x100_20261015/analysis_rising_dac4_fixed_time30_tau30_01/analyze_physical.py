"""Offline RAMP-duration x voltage DC/RC capture analysis; never opens devices.

Primary: GUI-requested ideal RC precompensation at native scope sample times,
median(measured - expected) in the central 5 us HOLD, abs(error) <= 15 mV.
Actual compiled fixed-point RC is a separate diagnostic. One global time
offset and one pre-frame zero median per channel; no gain or per-point fit.
One active DAC, one zero DAC. Only one of the two RAMP durations is swept;
the other remains 1 us. Full-record sampling does not certify 10 ns edges.
"""
from pathlib import Path
import argparse
import csv
import gzip
import hashlib
import json
import math
import sys
import traceback

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

HERE = Path(__file__).resolve().parent
MODEL_DIR = HERE / 'model_review'
sys.path.insert(0, str(MODEL_DIR))
from command_expectation import output_model

LIMIT_MV = 15.
MAX_DT_S = 5e-7
MIN_MAIN_SAMPLES = 10
MIN_DIAGNOSTIC_SAMPLES = 3
ANCHOR_MV = -200.
MAX_ROW_RESIDUAL_S = 2e-6


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    path = Path(path)
    if path.suffix == '.gz':
        return json.loads(gzip.decompress(path.read_bytes()).decode('utf8'))
    return json.loads(path.read_text(encoding='utf8'))


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf8')


def csv_save(path, rows):
    with Path(path).open('x', newline='', encoding='utf8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def child(value):
    path = (HERE / value).resolve()
    if path.parent != HERE.resolve():
        raise ValueError('Use a direct child directory of this evidence root')
    return path


def load_channel(folder, record):
    archive = record['archive']
    raw_path = folder / Path(archive['path']).name
    pre_path = folder / Path(archive['preamble_path']).name
    assert sha(raw_path) == archive['gzip_sha256']
    assert sha(pre_path) == archive['preamble_sha256']
    block = gzip.decompress(raw_path.read_bytes())
    assert hashlib.sha256(block).hexdigest() == archive['raw_sha256']
    assert block[:1] == b'#' and block[1:2] in b'123456789'
    digits = int(block[1:2])
    length = int(block[2:2 + digits])
    start = 2 + digits
    payload = block[start:start + length]
    assert len(payload) == length and block[start + length:] in (b'', b'\n', b'\r\n')
    assert hashlib.sha256(payload).hexdigest() == record['payload_sha256']
    pre = read(pre_path)
    values = [float(v) for v in pre['preamble_text'].split(',')]
    keys = ('format', 'type', 'points', 'count', 'x_increment', 'x_origin', 'x_reference', 'y_increment', 'y_origin', 'y_reference')
    assert len(values) == len(keys)
    p = dict(zip(keys, values))
    for key in keys[:4]:
        p[key] = int(p[key])
    assert p == record['preamble'] and p['format'] == 1
    assert p['points'] == pre['queried_points'] and length == 2 * p['points']
    codes = np.frombuffer(payload, dtype='<u2').copy()
    invalid = (codes == 0) | (codes == 0x100) | (codes == 0xff00)
    voltage = (codes.astype(np.float64) - p['y_reference']) * p['y_increment'] + p['y_origin']
    voltage[invalid] = np.nan
    time = (np.arange(len(codes), dtype=np.float64) - p['x_reference']) * p['x_increment'] + p['x_origin']
    unique = np.unique(codes)
    step = int(np.gcd.reduce(np.diff(unique).astype(np.int64))) if len(unique) > 1 else None
    return dict(preamble=p, codes=codes, time=time, voltage=voltage, invalid=invalid,
                observed_vertical_step_mv=step * p['y_increment'] * 1000 if step else None,
                paths=[raw_path, pre_path])


def window(channel, lo, hi):
    left = int(np.searchsorted(channel['time'], lo, side='left'))
    right = int(np.searchsorted(channel['time'], hi, side='right'))
    return left, right, channel['time'][left:right], channel['voltage'][left:right] * 1000


def valid_window(channel, lo, hi, values, minimum):
    return bool(hi > lo and lo >= channel['time'][0] and hi <= channel['time'][-1]
                and len(values) >= minimum and np.isfinite(values).all())


def compiled_values(model, program_us):
    return np.array([model.at_program_us(t)['expected_direct_dac_mv'] for t in program_us], dtype=float)


def requested_values(output, program_us):
    """GUI ideal: requested linear zero->V RAMP then the requested HOLD.

    The actual compiler's RAMP-to-HOLD guard is deliberately not added here;
    its value and exact compiled response are separately recorded.
    """
    elapsed = np.asarray(program_us) - output['hold_digital_output_us']
    return output['requested_mv'] * (1. + (.5 * output['requested_rise_us'] + elapsed) / output['rc_tau_us'])


def validate_expected(expected):
    """Reject ambiguous fixtures rather than deriving requested inputs from RTL.

    The 100 duration values are outer rows; the 100 voltage values vary fastest.
    Actual command durations remain an independent diagnostic and may differ
    through quantization. Explicit GUI requested durations are mandatory.
    """
    points = expected['points']
    assert len(points) == 10000 and expected['point_count'] == 10000
    assert expected['duration_count'] == expected['voltage_count'] == 100
    assert expected['sweep_shape'] == [100, 100]
    assert expected['plateau_duration_us'] == 10.
    active = int(expected['active_axis'])
    assert active in (0, 1) and expected['swept_ramp'] in ('rising', 'falling')
    assert expected['requested_range_mv'][0] < ANCHOR_MV and expected['requested_range_mv'][1] > 0
    lo, hi = map(float, expected['requested_ramp_range_us'])
    assert math.isclose(lo, .01, abs_tol=1e-12) and math.isclose(hi, 1., abs_tol=1e-12)
    for i, point in enumerate(points):
        assert point['point_index'] == i and point['axis_indices'] == [i // 100, i % 100]
        assert [o['panel_dac'] for o in point['outputs']] == [4, 5]
        assert [o['awg_gen'] for o in point['outputs']] == [1, 3]
        duration = lo + (hi - lo) * (i // 100) / 99
        voltage = expected['requested_range_mv'][0] + (expected['requested_range_mv'][1] - expected['requested_range_mv'][0]) * (i % 100) / 99
        for axis, output in enumerate(point['outputs']):
            requested_rise = float(output['requested_rise_us'])
            requested_fall = float(output['requested_fall_us'])
            assert math.isfinite(requested_rise) and math.isfinite(requested_fall)
            assert math.isclose(requested_rise, duration if expected['swept_ramp'] == 'rising' else 1., abs_tol=1e-10)
            assert math.isclose(requested_fall, duration if expected['swept_ramp'] == 'falling' else 1., abs_tol=1e-10)
            assert math.isclose(output['requested_mv'], voltage if axis == active else 0., abs_tol=1e-8)
            assert math.isclose(output['hold_end_digital_output_us'] - output['hold_digital_output_us'], 10., abs_tol=1e-7)
            assert math.isclose(output['rc_tau_us'], expected['rc_tau_us'], abs_tol=1e-12)
            if axis != active:
                assert output['dac_code'] == 0 and output['quantized_mv'] == 0.
                assert output['pre_dc_area_effective_code_samples'] == 0
                assert all(command['transport_target'] == 0 and command['step_signed'] == 0 for command in output['commands'])
                assert all(code == 0 for count, code in output['dc_runs_effective14'])
    return active


def falling_crossings(channel, fixed_offset_mv, threshold_mv=ANCHOR_MV):
    voltage = channel['voltage'] * 1000 - fixed_offset_mv
    indices = np.flatnonzero((voltage[:-1] > threshold_mv) & (voltage[1:] <= threshold_mv))
    times = channel['time'][indices] + (threshold_mv - voltage[indices]) * (
        channel['time'][indices + 1] - channel['time'][indices]) / (voltage[indices + 1] - voltage[indices])
    return indices, times


def model_anchor_us(output, model):
    command = output['commands'][1]
    assert command['opcode'] == 2 and output['requested_mv'] < ANCHOR_MV
    first = (int(command['cycle']) + 31 + 7) * 16
    last = first + int(command['duration_samples']) - 1
    value = lambda scalar: model.at_program_us(scalar / 4800.)['expected_direct_dac_mv']
    assert value(first) > ANCHOR_MV and value(last) <= ANCHOR_MV
    lo, hi = first, last
    while lo < hi:
        mid = (lo + hi) // 2
        if value(mid) <= ANCHOR_MV:
            hi = mid
        else:
            lo = mid + 1
    # Native piecewise constant model; no fitted analog ramp shape.
    return lo / 4800.


def roi_row(channel, output, model, point, axis, offset_mv, alignment_s, active_axis):
    start = output['hold_digital_output_us'] * 1e-6 + alignment_s
    end = output['hold_end_digital_output_us'] * 1e-6 + alignment_s
    lo, hi = start + 2.5e-6, end - 2.5e-6
    left, right, time, raw = window(channel, lo, hi)
    valid = valid_window(channel, lo, hi, raw, MIN_MAIN_SAMPLES)
    program_us = (time - alignment_s) * 1e6
    ideal = requested_values(output, program_us)
    exact = compiled_values(model, program_us)
    corrected = raw - offset_mv
    primary_error = float(np.median(corrected - ideal)) if valid else None
    compiled_error = float(np.median(corrected - exact)) if valid else None
    ramp = output['commands'][1]
    ramp_end_us = (ramp['cycle'] + 31 + 7) / 300. + ramp['duration_samples'] / 4800.
    return dict(point=point, axis0=point // 100, axis1=point % 100, scope_channel=axis + 1,
        active_output=axis == active_axis, reference_kind='requested_rc' if axis == active_axis else 'inactive_zero',
        requested_rise_us=output['requested_rise_us'], requested_fall_us=output['requested_fall_us'],
        compiled_rise_us=output['commands'][1]['duration_samples'] / 4800.,
        compiled_fall_us=output['commands'][3]['duration_samples'] / 4800.,
        panel_dac=output['panel_dac'], generator=output['awg_gen'], requested_mv=output['requested_mv'],
        compiled_nominal_mv=output['quantized_mv'], compiled_minus_requested_nominal_mv=output['quantized_mv'] - output['requested_mv'],
        dac_code=output['dac_code'], rc_tau_us=output['rc_tau_us'], rc_coefficient=output['rc_coefficient'],
        ramp_to_hold_guard_us=output['hold_digital_output_us'] - ramp_end_us,
        raw_median_mv=float(np.median(raw)) if valid else None, fixed_offset_mv=offset_mv,
        corrected_median_mv=float(np.median(corrected)) if valid else None,
        ideal_requested_rc_median_mv=float(np.median(ideal)) if valid else None,
        compiled_rc_median_mv=float(np.median(exact)) if valid else None,
        primary_median_error_mv=primary_error, primary_pass=bool(abs(primary_error) <= LIMIT_MV) if valid else None,
        compiled_median_error_mv=compiled_error, compiled_pass=bool(abs(compiled_error) <= LIMIT_MV) if valid else None,
        maximum_sample_primary_error_mv=float(np.max(np.abs(corrected - ideal))) if valid else None,
        maximum_sample_compiled_error_mv=float(np.max(np.abs(corrected - exact))) if valid else None,
        flat_request_diagnostic_error_mv=float(np.median(corrected) - output['requested_mv']) if valid else None,
        residual_std_mv=float(np.std(corrected - ideal)) if valid else None,
        samples=len(raw), roi_start_index=left, roi_stop_index_exclusive=right,
        roi_start_scope_s=lo, roi_end_scope_s=hi, hold_start_scope_s=start, hold_end_scope_s=end,
        roi_valid=valid)


def diagnostic_row(channel, model, point, axis, kind, start_us, end_us, offset_mv, alignment_s):
    lo, hi = start_us * 1e-6 + alignment_s, end_us * 1e-6 + alignment_s
    left, right, time, raw = window(channel, lo, hi)
    valid = valid_window(channel, lo, hi, raw, MIN_DIAGNOSTIC_SAMPLES)
    exact = compiled_values(model, (time - alignment_s) * 1e6)
    error = float(np.median(raw - offset_mv - exact)) if valid else None
    return dict(point=point, scope_channel=axis + 1, kind=kind,
        expected_window_duration_us=end_us - start_us, samples=len(raw),
        roi_start_index=left, roi_stop_index_exclusive=right, roi_start_scope_s=lo, roi_end_scope_s=hi,
        raw_median_mv=float(np.median(raw)) if valid else None, fixed_offset_mv=offset_mv,
        expected_compiled_median_mv=float(np.median(exact)) if valid else None,
        median_error_mv=error, passed=bool(abs(error) <= LIMIT_MV) if valid else None,
        valid=valid, note='' if valid else 'Not resolved: central DC window needs >=3 native samples')


def verdict_counts(rows, key):
    return dict(PASS=sum(r[key] is True for r in rows), FAIL=sum(r[key] is False for r in rows),
                INCOMPLETE=sum(r[key] is None for r in rows))


def minmax_plot(axis, channel, offset, label):
    edges = np.linspace(0, len(channel['time']), 6001, dtype=int)
    low, high, mid = [], [], []
    for a, b in zip(edges[:-1], edges[1:]):
        if b <= a:
            continue
        values = channel['voltage'][a:b] * 1000 - offset
        low.append(np.nanmin(values)); high.append(np.nanmax(values))
        mid.append((channel['time'][a] + channel['time'][b - 1]) * 500)
    axis.fill_between(mid, low, high, alpha=.7, lw=.2, label=label)
    axis.set(xlabel='Scope time (ms)', ylabel='Corrected mV')
    axis.grid(alpha=.2); axis.legend()


def plots(out, channels, offsets, expected, rows, alignment_s):
    fig, axes = plt.subplots(2, 1, figsize=(15, 8), constrained_layout=True)
    for ch in (1, 2):
        role = 'active' if ch - 1 == expected['active_axis'] else 'inactive zero'
        minmax_plot(axes[ch - 1], channels[ch], offsets[ch]['median_mv'], f'Physical DAC{ch + 3}/CH{ch}, {role}, min/max bins')
    fig.suptitle(f'Physical {expected["swept_ramp"]} RAMP duration x voltage, DC + RC\nFull native record retained; fixed baseline; no gain fit')
    fig.savefig(out / 'full_record.png', dpi=160); plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(13, 10), constrained_layout=True)
    maps = {}
    for ch in (1, 2):
        selected = rows[ch - 1::2]
        errors = np.array([r['primary_median_error_mv'] if r['primary_median_error_mv'] is not None else np.nan for r in selected]).reshape(100, 100)
        verdict = np.array([-1 if r['primary_pass'] is None else int(r['primary_pass']) for r in selected], dtype=np.int8).reshape(100, 100)
        maps[f'ch{ch}_primary_error_mv'] = errors; maps[f'ch{ch}_primary_verdict'] = verdict
        im = axes[ch - 1, 0].imshow(errors, origin='lower', aspect='auto', cmap='coolwarm', vmin=-30, vmax=30)
        fig.colorbar(im, ax=axes[ch - 1, 0], label='Median error (mV), plot clipped +/-30; full CSV retained')
        reference = 'GUI requested RC' if ch - 1 == expected['active_axis'] else 'inactive 0 mV'
        axes[ch - 1, 0].set_title(f'CH{ch}: measured minus {reference}')
        im = axes[ch - 1, 1].imshow(verdict, origin='lower', aspect='auto', vmin=-1, vmax=1, cmap=ListedColormap(['#aaaaaa', '#b43838', '#26784a']))
        bar = fig.colorbar(im, ax=axes[ch - 1, 1], ticks=[-1, 0, 1]); bar.ax.set_yticklabels(['Incomplete', 'Fail', 'Pass'])
        axes[ch - 1, 1].set_title('Primary: abs(median residual) <=15 mV')
        for ax in axes[ch - 1]:
            ax.set(xlabel=f'Voltage index (fast): {expected["requested_range_mv"][0]:g} to {expected["requested_range_mv"][1]:g} mV',
                   ylabel=f'{expected["swept_ramp"].capitalize()} RAMP index (slow): 10 ns to 1 us')
    fig.savefig(out / 'primary_error_maps.png', dpi=160); plt.close(fig)
    np.savez_compressed(out / 'derived_primary_maps.npz', **maps)
    fig, axes = plt.subplots(3, 2, figsize=(16, 11), constrained_layout=True)
    for row_index, point_index in enumerate((0, 5050, 9999)):
        for axis, output in enumerate(expected['points'][point_index]['outputs']):
            ch = axis + 1; ax = axes[row_index, axis]; model = output_model(output)
            start = output['sequence_start_command_us'] - 1
            end = output['dc_zero_reset_bound_us'] + 3
            left, right, times, raw = window(channels[ch], start * 1e-6 + alignment_s, end * 1e-6 + alignment_s)
            program_us = (times - alignment_s) * 1e6
            relative_us = program_us - output['hold_digital_output_us']
            ax.plot(relative_us, raw - offsets[ch]['median_mv'], '.-', ms=2, lw=.65, label='Observed physical samples')
            ax.plot(relative_us, compiled_values(model, program_us), '-', lw=.9, label='Exact compiled RC expectation')
            hold = (program_us >= output['hold_digital_output_us']) & (program_us <= output['hold_end_digital_output_us'])
            ax.plot(relative_us[hold], requested_values(output, program_us[hold]), '--', lw=1., label='Primary GUI-requested ideal RC')
            ax.axvspan(2.5, 7.5, color='#e5c54a', alpha=.14)
            ax.set(title=f'Point {point_index}, CH{ch}, {output["requested_mv"]:.6g} mV; rise {output["requested_rise_us"]:g} / fall {output["requested_fall_us"]:g} us', xlabel='Time from actual HOLD anchor (us)', ylabel='Corrected mV')
            ax.legend(fontsize=7); ax.grid(alpha=.2)
    fig.suptitle('Representative duration/voltage points: direct DAC physical measurement\nOne global time offset; shaded 5 us HOLD ROI; DC tail separate; RAMP shape unresolved at full-frame sampling')
    fig.savefig(out / 'representative_waveforms.png', dpi=170); plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepared', required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    prepared, run, out = child(args.prepared), child(args.run), child(args.output)
    if out.exists():
        raise FileExistsError(out)
    out.mkdir()
    inputs, issues = {}, []
    def protect(path):
        inputs[str(path)] = sha(path)
    try:
        for source in (Path(__file__), MODEL_DIR / 'command_expectation.py', MODEL_DIR / 'compact_expectation.py'):
            protect(source); (out / source.name).write_bytes(source.read_bytes())
        expected_path = prepared / 'expected_points.json.gz'
        if not expected_path.exists():
            expected_path = prepared / 'expected_points.json'
        protect(expected_path); expected = read(expected_path); points = expected['points']
        active_axis = validate_expected(expected)
        anchor_channel = active_axis + 1
        manifest_path = prepared / 'manifest.json'; protect(manifest_path)
        manifest = read(manifest_path)
        recorded_hash = manifest['files'][expected_path.name]
        if isinstance(recorded_hash, dict):
            recorded_hash = recorded_hash['sha256']
        assert recorded_hash == sha(expected_path)
        board_path = prepared / 'board_config_snapshot.json'
        protect(board_path)
        board = read(board_path)
        board_hash = manifest['files'][board_path.name]
        if isinstance(board_hash, dict):
            board_hash = board_hash['sha256']
        assert board_hash == sha(board_path)
        for gen_index in (1, 3):
            gen = board['gens'][gen_index]
            assert gen['type'] == 'axis_awg_tuning_v3' and gen['n_pts'] == 16
            assert gen['f_fabric'] == 300. and gen['frac'] == 18
            assert gen['output_latency_cycles'] == 31 and gen['ramp_startup_latency_cycles'] == 7
            assert gen['output_sum_version'] == 2 and gen['output_sum_awg_delay_cycles'] == 13
            assert gen['dc_area_version'] == gen['rc_precomp_version'] == 1
        status_path, capture_path = run / 'status.json', run / 'scope_capture/capture.json'
        protect(status_path); protect(capture_path)
        status, capture = read(status_path), read(capture_path)
        if not status.get('acquisition_success') or not status.get('sweep_completed') or not status.get('cleanup_zero'):
            issues.append('Physical acquisition/counter/cleanup did not complete')
        if not status.get('scope_restore', {}).get('passed') or status.get('production_sources_changed'):
            issues.append('Scope restore or source preservation failed')
        sweeps = [e for e in status.get('events', []) if e['name'] in ('voltage_sweep', 'ramp_voltage_sweep')]
        if len(sweeps) != 1 or sweeps[0]['progress'][-1] != [10000, 10000]:
            issues.append('Missing exact completed 10000/10000 hardware counter')
        if not capture.get('same_acquisition') or not capture.get('validation_passed') or status.get('capture_id') != capture['capture_id']:
            issues.append('Scope capture identity/invariant failed')
        channels = {ch: load_channel(run / 'scope_capture', capture['channels'][str(ch)]) for ch in (1, 2)}
        for ch, channel in channels.items():
            for path in channel['paths']:
                protect(path)
            if channel['preamble']['x_increment'] > MAX_DT_S or channel['invalid'].any():
                issues.append(f'CH{ch}: inadequate sample interval or invalid/clipped samples')
        dump(out / 'policy.json', dict(primary='GUI-requested ideal RC response for active output; inactive output must remain zero',
            ideal_formula='V_requested*(1+(requested_rise_us/2 + t_since_actual_HOLD)/tau_us)',
            error='median(raw_mv - one_fixed_offset_mv - expected_mv) over central 5 us',
            failure='abs(median error) >15mV; <=15mV passes', maximum_sample_error_diagnostic_only=True,
            compiled_rc_reference='Separate exact command/fixed-point RC diagnostic; never substitutes for primary',
            dc_reference='Exact compiled integer area compensation plus RC; separate diagnostic',
            minimum_main_samples=MIN_MAIN_SAMPLES, minimum_diagnostic_samples=MIN_DIAGNOSTIC_SAMPLES,
            maximum_sample_interval_s=MAX_DT_S, baseline='First 1 ms from native record start+1 us, strictly before first program output',
            active_axis=active_axis, active_scope_channel=anchor_channel, swept_ramp=expected['swept_ramp'],
            time_alignment=f'First active CH{anchor_channel} -200mV falling crossing versus exact compiled first RAMP, one global offset',
            row_alignment_maximum_absolute_residual_s=MAX_ROW_RESIDUAL_S,
            per_point_time_fit=False, gain_fit=False, per_point_voltage_offset=False,
            physical_reference_assumption='Direct DAC-to-scope connection; external RC network would require a different physical reference'))
        offsets = {}
        for ch, channel in channels.items():
            lo = float(channel['time'][0] + 1e-6); hi = lo + .001
            left, right, time, values = window(channel, lo, hi)
            if not valid_window(channel, lo, hi, values, 50) or hi >= -.001:
                raise RuntimeError(f'CH{ch}: insufficient pretrigger baseline, cannot choose a fixed zero offset')
            offsets[ch] = dict(median_mv=float(np.median(values)), samples=len(values),
                std_mv=float(np.std(values)), roi_start_scope_s=lo, roi_end_scope_s=hi,
                roi_start_index=left, roi_stop_index_exclusive=right)
        dump(out / 'fixed_offsets.json', offsets)
        indices, crossings = falling_crossings(channels[anchor_channel], offsets[anchor_channel]['median_mv'])
        crossings = crossings[crossings > offsets[anchor_channel]['roi_end_scope_s']]
        if not len(crossings):
            raise RuntimeError('No first negative RAMP anchor; physical response cannot be assigned to points')
        anchor_output = points[0]['outputs'][active_axis]
        first_model = output_model(anchor_output)
        anchor_program_us = model_anchor_us(anchor_output, first_model)
        alignment = float(crossings[0] - anchor_program_us * 1e-6)
        earliest_output = min(o['sequence_start_command_us'] for o in points[0]['outputs']) * 1e-6 + alignment
        if any(v['roi_end_scope_s'] >= earliest_output - 10e-6 for v in offsets.values()):
            raise RuntimeError('Selected baseline is not wholly before initial RC-reset/zero program frame')
        row_alignment = []
        for row_index in range(100):
            output = points[row_index * 100]['outputs'][active_axis]
            predicted = model_anchor_us(output, output_model(output)) * 1e-6 + alignment
            nearest = int(np.argmin(np.abs(crossings - predicted)))
            observed = float(crossings[nearest]); residual = observed - predicted
            row_alignment.append(dict(row=row_index, point=row_index * 100,
                requested_rise_us=output['requested_rise_us'], requested_fall_us=output['requested_fall_us'],
                matched_crossing_index=nearest, predicted_scope_s=predicted,
                observed_scope_s=observed, residual_us=residual * 1e6, within_strict_2us=abs(residual) < MAX_ROW_RESIDUAL_S))
        if any(not row['within_strict_2us'] for row in row_alignment):
            issues.append('At least one row first-point edge exceeds strict 2us global-alignment residual')
        if len({row['matched_crossing_index'] for row in row_alignment}) != 100:
            issues.append('A physical edge was reused for more than one duration row')
        csv_save(out / 'row_alignment.csv', row_alignment)
        dump(out / 'alignment.json', dict(single_time_offset_s=alignment, anchor_point=0, anchor_channel=anchor_channel,
            anchor_threshold_mv=ANCHOR_MV, anchor_observed_scope_s=float(crossings[0]),
            anchor_model_program_us=anchor_program_us, maximum_row_residual_us=max(abs(r['residual_us']) for r in row_alignment),
            note='One global edge alignment for ROI assignment only, not precision timing or zero channel skew certification.'))
        rows, dc_rows, zero_rows, timing_rows = [], [], [], []
        last_right = {1: -1, 2: -1}
        metadata_mismatches = []
        for point in points:
            for axis, output in enumerate(point['outputs']):
                ch = axis + 1; index = point['point_index']; model = output_model(output)
                if model.metadata_step_mismatches:
                    metadata_mismatches.append(dict(point=index, channel=ch, mismatches=list(model.metadata_step_mismatches)))
                row = roi_row(channels[ch], output, model, index, axis, offsets[ch]['median_mv'], alignment, active_axis)
                if row['roi_start_index'] < last_right[ch]:
                    row['roi_valid'] = False; row['primary_pass'] = None; row['compiled_pass'] = None
                last_right[ch] = row['roi_stop_index_exclusive']; rows.append(row)
                dc_start, dc_end = output['dc_start_digital_output_us'], output['dc_end_digital_output_us']
                duration = dc_end - dc_start
                dc_row = diagnostic_row(channels[ch], model, index, axis, 'dc_central_half',
                    dc_start + .25 * duration, dc_end - .25 * duration, offsets[ch]['median_mv'], alignment)
                dc_row['active_output'] = axis == active_axis
                dc_row['compensation_applicable'] = axis == active_axis
                if axis != active_axis:
                    # No nonzero command or nonzero area was requested on this
                    # output. Do not inflate DC pulse coverage with zero runs.
                    dc_row['passed'] = None
                    dc_row['note'] = 'N/A: inactive output has zero input area and zero-valued DC runs; HOLD and post-DC zero are separately checked'
                dc_rows.append(dc_row)
                # DC completes, forces a zero word and clears digital RC history.
                # Leave 1 us settling, then inspect a 2 us zero interval.
                zero_start = output['dc_zero_reset_bound_us'] + 1.
                zero_end = zero_start + 2.
                if index + 1 < len(points):
                    following = points[index + 1]['outputs'][axis]['commands'][1]
                    zero_end = min(zero_end, (following['cycle'] + 31 + 7) / 300. - 1.)
                zero_rows.append(diagnostic_row(channels[ch], model, index, axis, 'post_dc_zero',
                    zero_start, zero_end, offsets[ch]['median_mv'], alignment))
                timing_rows.append(dict(point=index, scope_channel=ch, requested_hold_us=10.,
                    active_output=axis == active_axis,
                    requested_rise_us=output['requested_rise_us'], requested_fall_us=output['requested_fall_us'],
                    compiled_rise_us=output['commands'][1]['duration_samples'] / 4800.,
                    compiled_fall_us=output['commands'][3]['duration_samples'] / 4800.,
                    accepted_hold_start_us=output['hold_digital_output_us'], ramp_to_hold_guard_us=row['ramp_to_hold_guard_us'],
                    dc_start_program_us=dc_start, dc_end_program_us=dc_end, expected_dc_duration_us=duration,
                    actual_duration_measurement=False, note='Expected DC windows; central voltage/zero observed. No precise edge-duration claim.'))
        if metadata_mismatches:
            issues.append('Exported decoded command metadata differs from authoritative command words')
        if any(not r['roi_valid'] for r in rows):
            issues.append('One or more main HOLD windows invalid, overlapping, or below 10 samples')
        csv_save(out / 'all_20000_holds.csv', rows)
        csv_save(out / 'all_10000_active_holds.csv', [r for r in rows if r['active_output']])
        csv_save(out / 'all_10000_inactive_zero_holds.csv', [r for r in rows if not r['active_output']])
        csv_save(out / 'all_20000_dc_windows.csv', dc_rows)
        csv_save(out / 'all_20000_post_dc_zero_windows.csv', zero_rows)
        csv_save(out / 'expected_timing_windows.csv', timing_rows)
        dump(out / 'decoded_metadata_mismatches.json', metadata_mismatches)
        point_rows = []
        for index in range(10000):
            pair = rows[2 * index:2 * index + 2]
            primary = 'INCOMPLETE' if any(r['primary_pass'] is None for r in pair) else 'FAIL' if any(r['primary_pass'] is False for r in pair) else 'PASS'
            compiled = 'INCOMPLETE' if any(r['compiled_pass'] is None for r in pair) else 'FAIL' if any(r['compiled_pass'] is False for r in pair) else 'PASS'
            point_rows.append(dict(point=index, axis0=index // 100, axis1=index % 100, primary_verdict=primary,
                compiled_verdict=compiled, ch1_primary_error_mv=pair[0]['primary_median_error_mv'], ch2_primary_error_mv=pair[1]['primary_median_error_mv']))
        csv_save(out / 'all_10000_point_verdicts.csv', point_rows)
        final_zero = {}
        final_start = expected['last_output_zero_bound_us'] + 100.
        for ch in (1, 2):
            final_zero[ch] = diagnostic_row(channels[ch], output_model(points[-1]['outputs'][ch - 1]), 9999, ch - 1,
                'final_zero_100_to_500us', final_start, final_start + 400., offsets[ch]['median_mv'], alignment)
        if any(not r['valid'] for r in final_zero.values()):
            issues.append('Capture does not contain final zero window')
        unchanged = all(sha(p) == h for p, h in inputs.items())
        if not unchanged:
            issues.append('An input or analysis source changed during analysis')
        primary_counts = verdict_counts(rows, 'primary_pass')
        result = dict(analysis_complete=True, new_hardware_execution=False, prepared_bundle=args.prepared, source_run=args.run,
            capture_id=capture['capture_id'], mode=expected['mode'], rc_tau_us=expected['rc_tau_us'],
            dc_time_us=expected.get('dc_time_us'), dc_voltage_mv=expected.get('dc_voltage_mv'),
            requested_range_mv=expected['requested_range_mv'], failure_threshold_mv=LIMIT_MV,
            requested_ramp_range_us=expected['requested_ramp_range_us'], swept_ramp=expected['swept_ramp'], active_axis=active_axis,
            physical_reference='Direct DAC-to-scope RC-precompensated waveform; no external RC-network transfer model',
            integrity_passed=not issues, integrity_issues=issues,
            overall_primary_passed=bool(not issues and primary_counts == dict(PASS=20000, FAIL=0, INCOMPLETE=0)),
            primary_channel_counts=primary_counts,
            active_primary_counts=verdict_counts([r for r in rows if r['active_output']], 'primary_pass'),
            inactive_zero_counts=verdict_counts([r for r in rows if not r['active_output']], 'primary_pass'),
            primary_point_counts={v: sum(r['primary_verdict'] == v for r in point_rows) for v in ('PASS', 'FAIL', 'INCOMPLETE')},
            compiled_channel_counts=verdict_counts(rows, 'compiled_pass'),
            dc_diagnostics=dict(central_compensation=verdict_counts([r for r in dc_rows if r['compensation_applicable']], 'passed'),
                inactive_compensation_not_applicable=sum(not r['compensation_applicable'] for r in dc_rows),
                post_dc_zero=verdict_counts(zero_rows, 'passed'), final_zero=final_zero,
                duration_certified=False, duration_note='Expected integer/DC windows only; no precision duration or external-capacitor-state claim'),
            fixed_offsets_mv={str(ch): v['median_mv'] for ch, v in offsets.items()}, single_time_offset_s=alignment,
            maximum_primary_median_error_mv=max((abs(r['primary_median_error_mv']) for r in rows if r['primary_median_error_mv'] is not None), default=None),
            maximum_compiled_median_error_mv=max((abs(r['compiled_median_error_mv']) for r in rows if r['compiled_median_error_mv'] is not None), default=None),
            per_channel={str(ch): dict(primary_counts=verdict_counts(rows[ch - 1::2], 'primary_pass'), compiled_counts=verdict_counts(rows[ch - 1::2], 'compiled_pass'),
                maximum_primary_median_error_mv=max((abs(r['primary_median_error_mv']) for r in rows[ch - 1::2] if r['primary_median_error_mv'] is not None), default=None),
                sample_interval_s=channels[ch]['preamble']['x_increment'], observed_vertical_step_mv=channels[ch]['observed_vertical_step_mv']) for ch in (1, 2)},
            input_hashes_unchanged=unchanged, analogue_accuracy_calibrated=False,
            limitations=['Primary ideal includes GUI voltage quantization error; exact compiled expectation is not substituted.',
                'First-RAMP scalar timing and per-channel scope grids are retained; one global timing offset only.',
                'Maximum per-sample residual is diagnostic; criterion remains the central-window median residual.',
                'Sub-resolution fixed-voltage DC tails can be unresolved and remain INCOMPLETE in separate diagnostics.',
                'Scope noise/bandwidth/vertical quantization and uncalibrated DC path are not removed by fitted gain.',
                'RAMP duration is a requested axis and compiled timing is retained; full-frame capture does not certify 10ns RAMP shape or precise duration.',
                'Inactive DC runs with zero area are not counted as nonzero compensation-pulse coverage.',
                'DC zero diagnostics do not expose internal per-shot area/overflow counters or certify an external RC circuit.'])
        dump(out / 'results.json', result); dump(out / 'input_hashes.json', inputs)
        plots(out, channels, offsets, expected, rows, alignment)
        assert all(sha(p) == h for p, h in inputs.items())
        dump(out / 'manifest.json', dict(analysis_complete=True, input_hashes_unchanged=True,
            files={p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in out.iterdir() if p.is_file()}))
        print(json.dumps({k: result[k] for k in ('integrity_passed', 'integrity_issues', 'overall_primary_passed', 'primary_channel_counts', 'primary_point_counts', 'compiled_channel_counts')}, indent=2))
        return 0 if not issues else 2
    except Exception as exc:
        dump(out / 'analysis_failure.json', dict(error=repr(exc), traceback=traceback.format_exc(), inputs=inputs,
            note='No hardware calls; original capture and inputs preserved. No physical PASS is assigned.'))
        raise


if __name__ == '__main__':
    raise SystemExit(main())
