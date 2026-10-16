"""Offline representative high-resolution RAMP analysis. No device imports.

One fixed zero offset/channel and one global first-edge time alignment are
allowed. The actual command-word RC model is a digital reference, not an
analog transfer-function calibration. Rise/fall times are diagnostics only.
Native RAW samples and source-specific time grids are never resampled.
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

HERE = Path(__file__).resolve().parent
MODEL_DIR = HERE / 'model_review'
sys.path.insert(0, str(MODEL_DIR))
from command_expectation import output_model

MAX_DT_S = 5e-10
LIMIT_MV = 15.


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    path = Path(path)
    raw = path.read_bytes()
    return json.loads((gzip.decompress(raw) if path.suffix == '.gz' else raw).decode('utf8'))


def dump(path, value):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)


def child(value):
    path = (HERE / value).resolve()
    if path.parent != HERE:
        raise ValueError('Use a direct child directory of this evidence root')
    return path


def load_channel(folder, record):
    """Independently verify and reconstruct exact archived WORD payload."""
    info = record['archive']
    raw_path = folder / Path(info['path']).name
    pre_path = folder / Path(info['preamble_path']).name
    assert sha(raw_path) == info['gzip_sha256']
    assert sha(pre_path) == info['preamble_sha256']
    block = gzip.decompress(raw_path.read_bytes())
    assert hashlib.sha256(block).hexdigest() == info['raw_sha256']
    assert block[:1] == b'#' and block[1:2] in b'123456789'
    digits = int(block[1:2]); start = 2 + digits
    length = int(block[2:start]); payload = block[start:start + length]
    assert len(payload) == length and block[start + length:] in (b'', b'\n', b'\r\n')
    assert hashlib.sha256(payload).hexdigest() == record['payload_sha256']
    pre = read(pre_path)
    keys = ('format', 'type', 'points', 'count', 'x_increment', 'x_origin', 'x_reference',
            'y_increment', 'y_origin', 'y_reference')
    values = [float(v) for v in pre['preamble_text'].split(',')]
    assert len(values) == 10 and all(math.isfinite(v) for v in values)
    p = dict(zip(keys, values))
    for key in keys[:4]:
        assert p[key] == int(p[key]); p[key] = int(p[key])
    assert p == record['preamble'] and p['format'] == 1
    assert p['points'] == pre['queried_points'] and length == 2 * p['points']
    assert p['x_increment'] > 0 and p['y_increment'] > 0
    codes = np.frombuffer(payload, dtype='<u2')
    invalid = (codes == 0) | (codes == 0x100) | (codes == 0xff00)
    voltage = (codes.astype(float) - p['y_reference']) * p['y_increment'] * 1000 + p['y_origin'] * 1000
    voltage[invalid] = np.nan
    time = (np.arange(len(codes), dtype=float) - p['x_reference']) * p['x_increment'] + p['x_origin']
    unique = np.unique(codes[~invalid])
    step = int(np.gcd.reduce(np.diff(unique).astype(np.int64))) if len(unique) > 1 else None
    return dict(preamble=p, codes=codes, time=time, mv=voltage, invalid=invalid,
                observed_vertical_step_mv=step * p['y_increment'] * 1000 if step else None,
                paths=[raw_path, pre_path])


def select(channel, lo, hi):
    a = int(np.searchsorted(channel['time'], lo, side='left'))
    b = int(np.searchsorted(channel['time'], hi, side='left'))
    valid = bool(hi > lo and channel['time'][0] <= lo and hi <= channel['time'][-1]
                 and b > a and np.isfinite(channel['mv'][a:b]).all())
    return a, b, valid


def compiled(model, program_us):
    """Exact ZOH model evaluated once per distinct native DAC sample."""
    scalar = np.floor(np.asarray(program_us) * model.scalar_mhz).astype(np.int64)
    unique, inverse = np.unique(scalar, return_inverse=True)
    values = []
    for index in unique:
        row = model.at_program_us((int(index) + .25) / model.scalar_mhz)
        assert row['relative_scalar_index'] == int(index) - model.origin_scalar
        values.append(row['expected_direct_dac_mv'])
    return np.asarray(values)[inverse]


def ramps(output):
    commands = [c for c in output['commands'] if c['opcode'] == 2]
    if len(commands) != 2:
        raise ValueError('Representative fixture must contain exactly two body RAMP commands')
    result = []
    for direction, command in zip(('rising', 'falling'), commands):
        word = int(command['word'], 16)
        count = (word >> 64) & ((1 << 23) - 1)
        assert count == command['duration_samples'] and count > 0
        start = (int(command['cycle']) + 31 + 7) / 300.
        result.append(dict(direction=direction, command=command, start_us=start,
            end_us=start + count / 4800., scalar_count=count,
            requested_us=float(output['requested_rise_us' if direction == 'rising' else 'requested_fall_us'])))
    return result


def crossings(time, values, level, increasing):
    left, right = values[:-1], values[1:]
    mask = ((left < level) & (right >= level)) if increasing else ((left > level) & (right <= level))
    indices = np.flatnonzero(mask & np.isfinite(left) & np.isfinite(right))
    return time[indices] + (level - left[indices]) * (time[indices + 1] - time[indices]) / (right[indices] - left[indices])


def model_cross(model, ramp, level, increasing):
    first = (int(ramp['command']['cycle']) + 31 + 7) * 16
    last = first + ramp['scalar_count'] - 1
    def value(index):
        return model.at_program_us((index + .25) / 4800.)['expected_direct_dac_mv']
    a, b = value(first), value(last)
    if not (a <= level <= b if increasing else b <= level <= a):
        raise ValueError('Threshold is outside the actual command RAMP')
    lo, hi = first, last
    while lo < hi:
        mid = (lo + hi) // 2
        if (value(mid) >= level) if increasing else (value(mid) <= level):
            hi = mid
        else:
            lo = mid + 1
    return lo / 4800.


def residual_row(channel, model, start_us, end_us, alignment, offset, *, minimum=3):
    a, b, valid = select(channel, start_us * 1e-6 + alignment, end_us * 1e-6 + alignment)
    valid = valid and b - a >= minimum
    measured = channel['mv'][a:b] - offset
    exact = compiled(model, (channel['time'][a:b] - alignment) * 1e6)
    error = measured - exact
    return dict(valid=valid, samples=b-a, roi_start_index=a, roi_stop_index_exclusive=b,
                start_program_us=start_us, end_program_us=end_us,
                median_residual_mv=float(np.median(error)) if valid else None,
                max_abs_residual_mv=float(np.max(np.abs(error))) if valid else None,
                residual_std_mv=float(np.std(error)) if valid else None,
                samples_abs_error_over_15mv=int(np.count_nonzero(np.abs(error) > LIMIT_MV)) if valid else None,
                median_within_15mv=bool(abs(float(np.median(error))) <= LIMIT_MV) if valid else None)


def ramp_diagnostic(channel, output, model, ramp, alignment, offset):
    row = residual_row(channel, model, ramp['start_us'], ramp['end_us'], alignment, offset)
    duration = ramp['end_us'] - ramp['start_us']
    row.update(direction=ramp['direction'], requested_duration_ns=ramp['requested_us'] * 1000,
        compiled_duration_ns=duration * 1000, compiled_scalar_samples=ramp['scalar_count'],
        duration_quantization_ns=(duration - ramp['requested_us']) * 1000,
        native_scope_sample_interval_ns=channel['preamble']['x_increment'] * 1e9,
        nominal_samples_per_compiled_ramp=duration * 1e-6 / channel['preamble']['x_increment'],
        precision_timing_pass=None, measured_10_90_ns=None, model_10_90_ns=None,
        extrapolated_linear_full_duration_ns=None, extrapolated_onset_residual_ns=None)
    first_scalar = (ramp['command']['cycle'] + 31 + 7) * 16
    endpoints = compiled(model, np.array([first_scalar+.25, first_scalar+ramp['scalar_count']-.75]) / 4800.)
    increasing = bool(endpoints[1] > endpoints[0])
    margin_us = max(.02, .2 * duration)
    a, b, coverage = select(channel, (ramp['start_us']-margin_us)*1e-6+alignment,
                            (ramp['end_us']+margin_us)*1e-6+alignment)
    chosen, model_times, all_candidates = [], [], []
    for fraction in (.1, .9):
        level = float(endpoints[0] + fraction * (endpoints[1]-endpoints[0]))
        predicted_us = model_cross(model, ramp, level, increasing)
        found = crossings(channel['time'][a:b], channel['mv'][a:b]-offset, level, increasing)
        target = predicted_us * 1e-6 + alignment
        selected = float(found[np.argmin(np.abs(found-target))]) if len(found) else None
        chosen.append(selected); model_times.append(predicted_us)
        all_candidates.append(dict(fraction=fraction, threshold_mv=level,
            model_program_us=predicted_us, observed_scope_s=selected, candidates_scope_s=found.tolist()))
    row['crossings'] = all_candidates
    row['crossing_window_complete'] = coverage
    if coverage and all(t is not None for t in chosen) and chosen[1] > chosen[0]:
        delta = chosen[1] - chosen[0]
        row['measured_10_90_ns'] = delta * 1e9
        row['model_10_90_ns'] = (model_times[1] - model_times[0]) * 1000
        row['extrapolated_linear_full_duration_ns'] = delta * 1e9 / .8
        onset = chosen[0] - delta / 8.
        row['extrapolated_onset_residual_ns'] = (onset - alignment - ramp['start_us'] * 1e-6) * 1e9
    row['timing_note'] = ('10-90% crossing and linear extrapolation are diagnostics, not a duration tolerance test. '
        'RC curvature, bandwidth, quantization, noise and threshold selection affect these values. '
        'Crossing selection never changes the one global time offset.')
    return row


def plot(out, channel, output, model, ramp_rows, alignment, offset):
    fig, axes = plt.subplots(3, 2, figsize=(14, 11), constrained_layout=True)
    for col, ramp in enumerate(ramps(output)):
        duration = ramp['end_us']-ramp['start_us']; margin=max(.03, duration*.2)
        a,b,_=select(channel,(ramp['start_us']-margin)*1e-6+alignment,(ramp['end_us']+margin)*1e-6+alignment)
        t=channel['time'][a:b]; x=((t-alignment)*1e6-ramp['start_us'])*1000
        measured=channel['mv'][a:b]-offset; exact=compiled(model,(t-alignment)*1e6)
        axes[0,col].plot(x,measured,'.-',ms=2,lw=.6,label='Physical RAW samples')
        axes[0,col].step(x,exact,where='post',lw=1,label='Exact compiled RC DAC')
        axes[0,col].axvspan(0,duration*1000,alpha=.08,color='green')
        axes[0,col].set(title=f'{ramp["direction"]}: requested {ramp["requested_us"]*1000:g} ns, compiled {duration*1000:.3f} ns',ylabel='Fixed-offset-corrected mV')
        axes[1,col].plot(x,measured-exact,lw=.7);axes[1,col].axhline(15,color='grey',ls='--');axes[1,col].axhline(-15,color='grey',ls='--')
        axes[1,col].set(xlabel='Time from compiled RAMP start (ns)',ylabel='Measured minus model (mV)')
        row=ramp_rows[col]
        axes[1,col].set_title(f'Native dt {row["native_scope_sample_interval_ns"]:.3g} ns; {row["samples"]} RAMP samples')
    start=ramps(output)[0]['start_us'];end=output['dc_end_digital_output_us']+.5
    a,b,_=select(channel,start*1e-6+alignment-1e-6,end*1e-6+alignment)
    # Only display is thinned; residual statistics above use every native sample.
    index=np.unique(np.linspace(a,max(a,b-1),min(6000,max(1,b-a))).astype(int))
    t=channel['time'][index];exact=compiled(model,(t-alignment)*1e6)
    axes[2,0].plot((t-alignment)*1e6-start,channel['mv'][index]-offset,lw=.7,label='Physical (display thinned)')
    axes[2,0].plot((t-alignment)*1e6-start,exact,lw=.8,label='Compiled RC DAC')
    axes[2,0].set(xlabel='Time from first RAMP (us)',ylabel='mV',title='HOLD and DC compensation context')
    axes[2,1].axis('off')
    axes[2,1].text(0,1,'Representative physical capture only\nOne fixed baseline offset; one global first-edge alignment\nNo gain fit or per-edge time fit\n10-90% timing is diagnostic, not a calibrated timing PASS\nAll native samples remain in the source RAW gzip archive',va='top',wrap=True)
    for ax in axes.flat:
        if ax.axison:
            ax.grid(alpha=.2)
            if ax.get_legend_handles_labels()[0]:ax.legend(fontsize=8)
    fig.suptitle(f'Physical DAC{output["panel_dac"]}: requested {output["requested_mv"]:g} mV, RC tau {output["rc_tau_us"]:g} us')
    fig.savefig(out/'highres_ramps.png',dpi=170);plt.close(fig)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepared',required=True);parser.add_argument('--run',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--channel',type=int,choices=(1,2));args=parser.parse_args()
    prepared,run,out=child(args.prepared),child(args.run),child(args.output)
    if out.exists():raise FileExistsError(out)
    out.mkdir();inputs={};issues=[]
    def protect(path):inputs[str(path)]=sha(path)
    try:
        for source in (Path(__file__),MODEL_DIR/'command_expectation.py',MODEL_DIR/'compact_expectation.py'):
            protect(source);(out/source.name).write_bytes(source.read_bytes())
        ep=prepared/'expected_points.json.gz'
        if not ep.exists():ep=prepared/'expected_points.json'
        paths=[ep,prepared/'manifest.json',run/'status.json',run/'scope_capture/capture.json']
        for path in paths:protect(path)
        expected,manifest,status,capture=map(read,paths)
        recorded=manifest['files'][ep.name]
        assert (recorded['sha256'] if isinstance(recorded,dict) else recorded)==sha(ep)
        # One point is intentional: 24 independent representative acquisitions.
        # Multi-point records require a separately reviewed coverage policy.
        assert len(expected['points'])==1,'High-resolution analyzer currently requires a one-point representative fixture'
        active=int(manifest['active_axis']);ch=active+1
        assert active in (0,1) and expected['active_axis']==active
        assert args.channel is None or args.channel==ch
        point=expected['points'][0];assert point['point_index']==0
        output=point['outputs'][active]
        assert abs(output['requested_mv'])==400. and expected['plateau_duration_us']==10.
        assert output['rc_tau_us']==20. and expected['mode']=='fixed_time' and expected['dc_time_us']==10.
        assert manifest['swept_ramp'] in ('rising','falling')
        requested=output['requested_rise_us' if manifest['swept_ramp']=='rising' else 'requested_fall_us']
        assert any(math.isclose(requested,value,abs_tol=1e-12) for value in (.01,.5,1.))
        if not all(status.get(key) for key in ('acquisition_success','sweep_completed','capture_saved','cleanup_zero','high_resolution')):issues.append('Physical acquisition/counter/cleanup/high-resolution status failed')
        if status.get('production_sources_changed') or not status.get('scope_restore',{}).get('passed'):issues.append('Source preservation or scope restore failed')
        sweeps=[e for e in status.get('events',[]) if e['name']=='voltage_sweep']
        if len(sweeps)!=1 or sweeps[0]['progress'][-1]!=[1,1]:issues.append('Missing one-point completed hardware counter')
        if not capture.get('same_acquisition') or not capture.get('validation_passed') or capture['capture_id']!=status.get('capture_id'):issues.append('Capture identity failed')
        channels={i:load_channel(run/'scope_capture',capture['channels'][str(i)]) for i in (1,2)}
        for i,c in channels.items():
            for path in c['paths']:protect(path)
            if c['invalid'].any() or c['preamble']['x_increment']>MAX_DT_S:issues.append(f'CH{i}: invalid data or native sample interval >0.5ns')
        offsets={}
        for i,c in channels.items():
            lo=float(c['time'][0]+.25e-6);hi=lo+1e-6;a,b,valid=select(c,lo,hi)
            if not valid or b-a<100 or hi>=-1e-6:raise ValueError(f'CH{i}: no complete early zero baseline in short record')
            offsets[i]=dict(median_mv=float(np.median(c['mv'][a:b])),std_mv=float(np.std(c['mv'][a:b])),samples=b-a,
                start_scope_s=lo,end_scope_s=hi,roi_start_index=a,roi_stop_index_exclusive=b)
        model=output_model(output)
        assert not model.metadata_step_mismatches
        first=ramps(output)[0];threshold=math.copysign(200.,output['requested_mv'])
        model_anchor=model_cross(model,first,threshold,output['requested_mv']>0)
        c=channels[ch];found=crossings(c['time'],c['mv']-offsets[ch]['median_mv'],threshold,output['requested_mv']>0)
        candidates=found[(found>offsets[ch]['end_scope_s']) & (np.abs(found)<2e-6)]
        if not len(candidates):raise ValueError('No first RAMP threshold crossing near trigger')
        anchor=float(candidates[np.argmin(np.abs(candidates))]);alignment=anchor-model_anchor*1e-6
        if any(v['end_scope_s']>=first['start_us']*1e-6+alignment-1e-6 for v in offsets.values()):raise ValueError('Baseline overlaps the first RAMP')
        # Verify the chosen fixed-zero interval against both exact digital models.
        for i,other in enumerate(point['outputs'],1):
            baseline_model=output_model(other);interval=np.array([offsets[i]['start_scope_s'],offsets[i]['end_scope_s']])
            assert np.all(compiled(baseline_model,(interval-alignment)*1e6)==0)
        ramp_rows=[ramp_diagnostic(c,output,model,r,alignment,offsets[ch]['median_mv']) for r in ramps(output)]
        if any(not row['valid'] or row['samples']<20 for row in ramp_rows):issues.append('At least one RAMP lacks complete coverage or 20 native samples')
        hold_rows=[]
        for i,o in enumerate(point['outputs'],1):
            m=output_model(o);lo=o['hold_digital_output_us']+2.5;hi=o['hold_end_digital_output_us']-2.5
            row=residual_row(channels[i],m,lo,hi,alignment,offsets[i]['median_mv'],minimum=10)
            a,b=row['roi_start_index'],row['roi_stop_index_exclusive'];t=(channels[i]['time'][a:b]-alignment)*1e6
            ideal=o['requested_mv']*(1.+(.5*o['requested_rise_us']+t-o['hold_digital_output_us'])/o['rc_tau_us'])
            error=channels[i]['mv'][a:b]-offsets[i]['median_mv']-ideal
            row.update(scope_channel=i,requested_mv=o['requested_mv'],compiled_nominal_mv=o['quantized_mv'],
                requested_ideal_median_error_mv=float(np.median(error)) if row['valid'] else None,
                requested_ideal_median_within_15mv=bool(abs(float(np.median(error)))<=LIMIT_MV) if row['valid'] else None)
            hold_rows.append(row)
        dc_start,dc_end=output['dc_start_digital_output_us'],output['dc_end_digital_output_us']
        dc=residual_row(c,model,dc_start+.25*(dc_end-dc_start),dc_end-.25*(dc_end-dc_start),alignment,offsets[ch]['median_mv'])
        result=dict(analysis_complete=True,new_hardware_execution=False,representative_only=True,point_count=1,
            prepared_bundle=args.prepared,source_run=args.run,capture_id=capture['capture_id'],active_channel=ch,
            swept_ramp=manifest['swept_ramp'],requested_voltage_mv=output['requested_mv'],requested_swept_duration_us=requested,
            integrity_passed=not issues,integrity_issues=issues,fixed_offsets=offsets,single_time_offset_s=alignment,
            alignment=dict(threshold_mv=threshold,observed_scope_s=anchor,model_program_us=model_anchor,
                candidate_crossings_scope_s=candidates.tolist(),method='First main RAMP crossing nearest trigger; one offset for both edges and channels'),
            ramps=ramp_rows,hold=hold_rows,dc_central_half=dc,
            channel_sample_intervals_s={i:v['preamble']['x_increment'] for i,v in channels.items()},
            channel_observed_voltage_steps_mv={i:v['observed_vertical_step_mv'] for i,v in channels.items()},
            precision_timing_pass=None,analog_accuracy_calibrated=False,full_10000_point_ramp_validation=False,
            limitations=['All model residual statistics use native samples and source-specific time grids.',
                'First-edge alignment removes unknown launch/cable delay; absolute latency is not measured.',
                'No per-edge/per-point timing fit, gain fit, or voltage-dependent zero offset is used.',
                '10-90% widths and linear onset extrapolation are diagnostics, not an exact RAMP duration tolerance verdict.',
                'Compiled RC waveform is the direct DAC digital expectation, not a calibrated analog path model.',
                'HOLD requested-ideal error includes requested-to-compiled voltage/duration differences.'])
        dump(out/'results.json',result);dump(out/'input_hashes.json',inputs)
        plot(out,c,output,model,ramp_rows,alignment,offsets[ch]['median_mv'])
        assert all(sha(path)==digest for path,digest in inputs.items()),'Inputs changed during analysis'
        dump(out/'manifest.json',dict(analysis_complete=True,input_hashes_unchanged=True,
            files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in out.iterdir() if p.is_file()}))
        print(json.dumps({key:result[key] for key in ('integrity_passed','integrity_issues','active_channel','requested_swept_duration_us','ramps')},indent=2))
        return 0 if not issues else 2
    except Exception as exc:
        dump(out/'analysis_failure.json',dict(error=repr(exc),traceback=traceback.format_exc(),inputs=inputs,
            note='Original evidence preserved; no device calls and no physical PASS assigned.'))
        raise


if __name__=='__main__':
    raise SystemExit(main())
