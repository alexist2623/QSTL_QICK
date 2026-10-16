"""Offline 100x100 physical voltage analysis. Never opens an instrument.

Predeclared: CH2 300mV rising crossings, one fixed offset from the first row's
last crossing (point 99), 1us ramp crossing fraction from local raw baseline and
high level ONLY for timing. All 100 row-end residuals must be strictly <2us.
Central 5us of each 10us HOLD, >=10 samples, one median zero offset/channel,
and strict abs(error/requested)<5%. No per-point timing/voltage correction.
"""
from pathlib import Path
import argparse
import csv
import gzip
import hashlib
import json
import math
import traceback
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

HERE=Path(__file__).resolve().parent
THRESHOLD_V=.3
LIMIT_PERCENT=5.
MAX_SAMPLE_INTERVAL_S=5e-7
MAX_ROW_RESIDUAL_S=2e-6
MIN_ROI_SAMPLES=10
RAMP_S=1e-6
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')
def safe_number(x):return float(x) if math.isfinite(float(x)) else None
def csv_file(path,rows):
    with Path(path).open('x',newline='',encoding='utf8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def child(name):
    path=(HERE/name).resolve()
    if path.parent!=HERE.resolve():raise ValueError('Use a direct child directory')
    return path

def load_channel(folder,record):
    archive=record['archive']
    raw_path=folder/Path(archive['path']).name
    pre_path=folder/Path(archive['preamble_path']).name
    assert sha(raw_path)==archive['gzip_sha256']
    assert sha(pre_path)==archive['preamble_sha256']
    raw=gzip.decompress(raw_path.read_bytes())
    assert hashlib.sha256(raw).hexdigest()==archive['raw_sha256']
    assert raw[:1]==b'#' and raw[1:2] in b'123456789'
    digits=int(raw[1:2]);length=int(raw[2:2+digits]);start=2+digits
    payload=raw[start:start+length]
    assert raw[start+length:] in (b'',b'\n',b'\r\n')
    assert hashlib.sha256(payload).hexdigest()==record['payload_sha256']
    pre=read(pre_path);values=[float(v) for v in pre['preamble_text'].split(',')]
    assert len(values)==10
    keys=('format','type','points','count','x_increment','x_origin','x_reference','y_increment','y_origin','y_reference')
    p=dict(zip(keys,values))
    for key in keys[:4]:p[key]=int(p[key])
    assert p==record['preamble'] and p['format']==1
    assert p['points']==pre['queried_points'] and length==2*p['points']
    codes=np.frombuffer(payload,dtype='<u2').copy()
    invalid=(codes==0)|(codes==0x100)|(codes==0xff00)
    voltage=(codes.astype(np.float64)-p['y_reference'])*p['y_increment']+p['y_origin']
    voltage[invalid]=np.nan
    time=(np.arange(len(codes),dtype=np.float64)-p['x_reference'])*p['x_increment']+p['x_origin']
    unique=np.unique(codes);step=int(np.gcd.reduce(np.diff(unique).astype(np.int64))) if len(unique)>1 else None
    return dict(preamble=p,codes=codes,time=time,voltage=voltage,invalid=invalid,
        observed_code_step=step,observed_vertical_step_mv=step*p['y_increment']*1000 if step else None,
        paths=[raw_path,pre_path])

def subset(channel,lo,hi):
    # Index lookup avoids 20000 full-trace Boolean scans; native grids retained.
    time=channel['time'];left=int(np.searchsorted(time,lo,side='left'));right=int(np.searchsorted(time,hi,side='right'))
    return left,right,channel['voltage'][left:right]*1000.

def minmax_plot(axis,channel,offset,label,color,max_bins=5000,lo=None,hi=None):
    time=channel['time'];voltage=channel['voltage']*1000-offset
    start=0 if lo is None else int(np.searchsorted(time,lo))
    stop=len(time) if hi is None else int(np.searchsorted(time,hi,'right'))
    if lo is not None:
        axis.plot(time[start:stop]*1000,voltage[start:stop],color=color,lw=.55,label=label)
        return
    edges=np.linspace(start,stop,min(max_bins,stop-start)+1,dtype=int)
    mid=[];low=[];high=[]
    for a,b in zip(edges[:-1],edges[1:]):
        if b<=a:continue
        mid.append((time[a]+time[b-1])*500);low.append(float(np.nanmin(voltage[a:b])));high.append(float(np.nanmax(voltage[a:b])))
    axis.fill_between(mid,low,high,color=color,alpha=.7,lw=.2,label=label+' (min/max bins)')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();run=child(args.run);out=child(args.output)
    if out.exists():raise FileExistsError(out)
    out.mkdir();(out/'analyze_physical_snapshot.py').write_bytes(Path(__file__).read_bytes())
    issues=[];inputs={};diagnostics={}
    def protect(path):inputs[str(path)]=sha(path)
    expected_path=HERE/'offline_prepared/expected_points.json';protect(expected_path)
    expected=read(expected_path);points=expected['points']
    assert len(points)==10000 and expected['axis_count']==100 and expected['plateau_duration_us']==10.
    for i,point in enumerate(points):
        assert point['point_index']==i and point['axis_indices']==[i//100,i%100]
        assert [o['panel_dac'] for o in point['outputs']]==[4,5]
    status_path=run/'status.json';capture_path=run/'scope_capture/capture.json'
    protect(status_path);protect(capture_path);state=read(status_path);capture=read(capture_path)
    dump(out/'policy.json',dict(rising_threshold_v=THRESHOLD_V,anchor_point=99,row_endpoint_indices=list(range(99,10000,100)),
        maximum_row_endpoint_residual_s=MAX_ROW_RESIDUAL_S,strict_residual=True,maximum_sample_interval_s=MAX_SAMPLE_INTERVAL_S,
        hold_roi_fraction=[.25,.75],minimum_roi_samples=MIN_ROI_SAMPLES,threshold_percent=LIMIT_PERCENT,
        strict_percent=True,denominator='requested voltage',offset='One median of all 100 zero-HOLD central windows per channel',
        zero_percent_verdict=None,per_point_timing_fit=False,per_point_offset=False,gain_fit=False))
    if not state.get('acquisition_success'):issues.append('Run acquisition_success is false')
    if not capture.get('same_acquisition') or not capture.get('validation_passed'):issues.append('Capture invariant failed')
    if state.get('capture_id')!=capture['capture_id']:issues.append('Capture identity mismatch')
    channels={}
    for ch in (1,2):
        channel=load_channel(run/'scope_capture',capture['channels'][str(ch)]);channels[ch]=channel
        for path in channel['paths']:protect(path)
        if channel['preamble']['x_increment']>MAX_SAMPLE_INTERVAL_S:issues.append(f'CH{ch} insufficient sample rate')
        if channel['invalid'].any():issues.append(f'CH{ch} invalid/clipped raw codes')
    dump(out/'input_hashes.json',inputs)

    time=channels[2]['time'];voltage=channels[2]['voltage']
    crossings=np.flatnonzero((voltage[:-1]<THRESHOLD_V)&(voltage[1:]>=THRESHOLD_V))
    crossing_times=time[crossings]+(THRESHOLD_V-voltage[crossings])*(time[crossings+1]-time[crossings])/(voltage[crossings+1]-voltage[crossings])
    period_s=float(np.median(np.diff([p['outputs'][1]['hold_digital_output_us'] for p in points])))*1e-6
    # Consolidate threshold recrossings within one <=10us pulse. Keep first edge;
    # the final 400mV pulse of every row is well above the threshold.
    cluster_starts=np.r_[0,np.flatnonzero(np.diff(crossing_times)>period_s*.5)+1] if len(crossing_times) else np.array([],dtype=int)
    pulse_edges=crossing_times[cluster_starts]
    burst_starts=np.r_[0,np.flatnonzero(np.diff(pulse_edges)>2*period_s)+1] if len(pulse_edges) else np.array([],dtype=int)
    burst_stops=np.r_[burst_starts[1:],len(pulse_edges)]
    row_ends=np.array([pulse_edges[b-1] for b in burst_stops]) if len(burst_starts) else np.array([])
    diagnostics.update(raw_crossing_count=len(crossings),pulse_crossing_count=len(pulse_edges),row_burst_count=len(row_ends),
        model_point_period_s=period_s,threshold_clusters=[dict(first_edge_s=float(pulse_edges[a]),last_edge_s=float(pulse_edges[b-1]),pulse_count=int(b-a))
            for a,b in zip(burst_starts,burst_stops)])
    if len(row_ends)!=100:issues.append(f'Expected 100 high-threshold row bursts; observed {len(row_ends)}')
    if not len(row_ends):
        dump(out/'alignment.json',dict(**diagnostics,issues=issues));raise RuntimeError('No timing anchor; no plateau assignment possible')
    anchor=float(row_ends[0])
    _,_,base=subset(channels[2],anchor-8e-6,anchor-2e-6)
    _,_,high=subset(channels[2],anchor+2e-6,anchor+7e-6)
    if len(base)<3 or len(high)<3:raise RuntimeError('Insufficient local timing-anchor samples')
    baseline=float(np.median(base))/1000.;peak=float(np.median(high))/1000.
    fraction=(THRESHOLD_V-baseline)/(peak-baseline)
    if not 0<fraction<1:raise RuntimeError('300mV anchor not between local baseline and plateau')
    expected_crossing=points[99]['outputs'][1]['hold_digital_output_us']*1e-6-RAMP_S+fraction*RAMP_S
    alignment=anchor-expected_crossing
    endpoint_rows=[]
    for row,observed in enumerate(row_ends[:100]):
        point=row*100+99
        predicted=points[point]['outputs'][1]['hold_digital_output_us']*1e-6-RAMP_S+fraction*RAMP_S+alignment
        residual=float(observed-predicted)
        endpoint_rows.append(dict(row=row,point=point,observed_crossing_s=float(observed),predicted_crossing_s=predicted,
            residual_s=residual,residual_us=residual*1e6,within_strict_2us=abs(residual)<MAX_ROW_RESIDUAL_S))
    if any(not r['within_strict_2us'] for r in endpoint_rows):issues.append('Row endpoint exceeds strict 2us alignment check')
    diagnostics.update(anchor_observed_s=anchor,anchor_point=99,local_baseline_v=baseline,local_high_v=peak,
        crossing_fraction=fraction,single_alignment_offset_s=alignment,local_levels_used_only_for_timing=True,
        row_endpoints=endpoint_rows,max_absolute_row_endpoint_residual_us=max(abs(r['residual_us']) for r in endpoint_rows))
    dump(out/'alignment.json',diagnostics)
    csv_file(out/'row_endpoint_alignment.csv',endpoint_rows)

    rows=[];zero_windows={1:[],2:[]};zero_records={1:[],2:[]};last_right={1:-1,2:-1}
    for point in points:
        for ch,o in zip((1,2),point['outputs']):
            start=o['hold_digital_output_us']*1e-6+alignment;end=o['hold_end_digital_output_us']*1e-6+alignment
            lo=start+.25*(end-start);hi=end-.25*(end-start)
            left,right,values=subset(channels[ch],lo,hi)
            valid=len(values)>=MIN_ROI_SAMPLES and np.isfinite(values).all() and lo>=channels[ch]['time'][0] and hi<=channels[ch]['time'][-1]
            distinct=left>=last_right[ch];last_right[ch]=right
            if not valid:issues.append(f'Invalid or insufficient ROI point {point["point_index"]} CH{ch}')
            if not distinct:issues.append(f'Overlapping ROI point {point["point_index"]} CH{ch}')
            row=dict(point=point['point_index'],axis0=point['axis_indices'][0],axis1=point['axis_indices'][1],scope_channel=ch,
                panel_dac=o['panel_dac'],generator=o['awg_gen'],requested_mv=o['requested_mv'],quantized_nominal_mv=o['quantized_mv'],dac_code=o['dac_code'],
                raw_median_mv=safe_number(np.median(values)) if len(values) else None,
                raw_mean_mv=safe_number(np.mean(values)) if len(values) else None,
                std_mv=safe_number(np.std(values)) if len(values) else None,
                minimum_mv=safe_number(np.min(values)) if len(values) else None,maximum_mv=safe_number(np.max(values)) if len(values) else None,
                samples=len(values),roi_start_index=left,roi_stop_index_exclusive=right,roi_start_scope_s=lo,roi_end_scope_s=hi,
                hold_start_scope_s=start,hold_end_scope_s=end,roi_valid=bool(valid and distinct))
            rows.append(row)
            if o['requested_mv']==0 and valid:
                zero_windows[ch].append(values);zero_records[ch].append(dict(point=point['point_index'],raw_median_mv=row['raw_median_mv'],samples=len(values)))
    assert len(rows)==20000
    offsets={}
    for ch in (1,2):
        if len(zero_windows[ch])!=100:issues.append(f'CH{ch}: expected 100 zero-HOLD windows, found {len(zero_windows[ch])}')
        if not zero_windows[ch]:raise RuntimeError('Missing zero baseline')
        values=np.concatenate(zero_windows[ch]);offsets[ch]=dict(median_mv=float(np.median(values)),mean_mv=float(np.mean(values)),samples=len(values),
            zero_hold_windows=len(zero_windows[ch]),records=zero_records[ch])
    for row in rows:
        ch=row['scope_channel'];target=row['requested_mv'];valid=row['roi_valid']
        corrected=row['raw_median_mv']-offsets[ch]['median_mv'] if valid else None
        mean_corrected=row['raw_mean_mv']-offsets[ch]['mean_mv'] if valid else None
        percent=100*(corrected-target)/abs(target) if target and valid else None
        mean_percent=100*(mean_corrected-target)/abs(target) if target and valid else None
        row.update(fixed_offset_mv=offsets[ch]['median_mv'],corrected_median_mv=corrected,
            error_mv=corrected-target if valid else None,signed_error_pct=percent,
            abs_error_pct=abs(percent) if percent is not None else None,
            strict_under_5pct=bool(abs(percent)<LIMIT_PERCENT) if percent is not None else None,
            mean_diagnostic_corrected_mv=mean_corrected,mean_diagnostic_error_pct=mean_percent,
            zero_baseline_only=target==0)
    csv_file(out/'all_20000_plateaus.csv',rows)
    offsets_without_records={str(k):{a:b for a,b in v.items() if a!='records'} for k,v in offsets.items()}
    dump(out/'offsets.json',offsets)
    point_rows=[]
    for point in range(10000):
        pair=rows[point*2:point*2+2];tested=[r for r in pair if r['requested_mv']!=0]
        verdict='N/A' if not tested else 'INCOMPLETE' if any(not r['roi_valid'] for r in tested) else 'FAIL' if any(not r['strict_under_5pct'] for r in tested) else 'PASS'
        point_rows.append(dict(point=point,axis0=point//100,axis1=point%100,nonzero_axes=len(tested),verdict=verdict,
            ch1_requested_mv=pair[0]['requested_mv'],ch2_requested_mv=pair[1]['requested_mv'],
            ch1_error_pct=pair[0]['signed_error_pct'],ch2_error_pct=pair[1]['signed_error_pct']))
    csv_file(out/'all_10000_point_verdicts.csv',point_rows)
    final_zero={}
    last_zero=expected['last_output_zero_us']*1e-6+alignment
    for ch in (1,2):
        left,right,values=subset(channels[ch],last_zero+100e-6,last_zero+500e-6)
        valid=len(values)>=MIN_ROI_SAMPLES and np.isfinite(values).all()
        if not valid:issues.append(f'CH{ch}: missing final zero evidence')
        final_zero[ch]=dict(samples=len(values),raw_median_mv=safe_number(np.median(values)) if valid else None,
            fixed_offset_mv=offsets[ch]['median_mv'],corrected_residual_mv=safe_number(np.median(values)-offsets[ch]['median_mv']) if valid else None,
            std_mv=safe_number(np.std(values)) if valid else None,relative_percent_verdict=None,
            note='Final baseline residual only; percent of zero is undefined')
    nonzero=[r for r in rows if r['requested_mv']!=0];assert len(nonzero)==19800
    maps={}
    for ch in (1,2):
        selected=[r for r in rows if r['scope_channel']==ch]
        maps[f'ch{ch}_error_percent']=np.array([r['signed_error_pct'] if r['signed_error_pct'] is not None else np.nan for r in selected]).reshape(100,100)
        maps[f'ch{ch}_verdict']=np.array([-1 if r['strict_under_5pct'] is None else int(r['strict_under_5pct']) for r in selected],dtype=np.int8).reshape(100,100)
        maps[f'ch{ch}_corrected_mv']=np.array([r['corrected_median_mv'] for r in selected]).reshape(100,100)
    np.savez_compressed(out/'derived_error_and_verdict_maps.npz',**maps)
    source_unchanged=all(sha(p)==h for p,h in inputs.items())
    if not source_unchanged:issues.append('Input hash changed during analysis')
    diagnostics['integrity_issues']=issues;diagnostics['integrity_passed']=not issues;dump(out/'alignment.json',diagnostics)
    result=dict(capture_id=capture['capture_id'],new_hardware_execution=False,source_run=args.run,analysis_complete=True,
        integrity_passed=not issues,integrity_issues=issues,physical_points=10000,measured_plateaus=20000,
        nonzero_plateaus=19800,passed_nonzero_plateaus=sum(r['strict_under_5pct'] is True for r in nonzero),
        failed_nonzero_plateaus=sum(r['strict_under_5pct'] is False for r in nonzero),
        incomplete_nonzero_plateaus=sum(r['strict_under_5pct'] is None for r in nonzero),
        zero_plateaus_percent_NA=200,point_counts={v:sum(r['verdict']==v for r in point_rows) for v in ('PASS','FAIL','N/A','INCOMPLETE')},
        overall_passed=bool(not issues and all(r['strict_under_5pct'] is True for r in nonzero)),
        threshold_percent=5.,comparison='strictly_less_than',denominator='requested voltage 400*axis_index/99; not hardware quantized value',
        offsets=offsets_without_records,maximum_absolute_error_pct=max(r['abs_error_pct'] for r in nonzero if r['abs_error_pct'] is not None),
        per_channel={str(ch):dict(passed=sum(r['strict_under_5pct'] is True for r in nonzero if r['scope_channel']==ch),
            failed=sum(r['strict_under_5pct'] is False for r in nonzero if r['scope_channel']==ch),
            maximum_absolute_error_pct=max(r['abs_error_pct'] for r in nonzero if r['scope_channel']==ch and r['abs_error_pct'] is not None),
            sample_interval_s=channels[ch]['preamble']['x_increment'],observed_vertical_step_mv=channels[ch]['observed_vertical_step_mv']) for ch in (1,2)},
        final_zero=final_zero,single_time_offset_s=alignment,max_row_endpoint_residual_us=diagnostics['max_absolute_row_endpoint_residual_us'],
        input_hashes_unchanged=source_unchanged,requested_endpoint_mv=400.,actual_compiled_endpoint_mv=points[-1]['outputs'][0]['quantized_mv'],
        actual_compiled_code_increment=164,analogue_accuracy_calibrated=False,
        limitations=['Median resolution and low-voltage relative-percent sensitivity retained; no tolerance widening.',
            'Raw baseline/high used only for the single timing anchor, not amplitude gain correction.',
            'Alignment integrity supports ROI assignment, not ns-scale timing/skew certification.',
            'Capture raw samples remain in original lossless gzip files; this folder stores only derived summaries/maps/plots.',
            'Run-worker ADC/FIR/DDR/QCoDeS path and nonidentity matrix are outside this scope-only identity test.'])
    dump(out/'results.json',result)

    # Full record uses min/max bins so narrow pulses are not lost by decimation.
    fig,axes=plt.subplots(2,1,figsize=(15,8),constrained_layout=True)
    for ch,color in ((1,'#1f77b4'),(2,'#d95f02')):
        minmax_plot(axes[ch-1],channels[ch],offsets[ch]['median_mv'],f'DAC{ch+3}/CH{ch}',color)
        axes[ch-1].set_ylabel('Fixed-offset corrected mV');axes[ch-1].set_xlabel('Scope time (ms)');axes[ch-1].legend();axes[ch-1].grid(alpha=.2)
    fig.suptitle('100 x 100 physical voltage capture, full record min/max envelope\nOne fixed channel offset; native full-resolution gzip samples retained')
    fig.savefig(out/'full_record_overview.png',dpi=160);plt.close(fig)
    for name,row_index in (('first_row',0),('last_row',99)):
        subset_rows=rows[row_index*200:(row_index+1)*200]
        lo=min(r['hold_start_scope_s'] for r in subset_rows)-15e-6;hi=max(r['hold_end_scope_s'] for r in subset_rows)+15e-6
        fig,axes=plt.subplots(2,1,figsize=(16,8),constrained_layout=True)
        for ch,color in ((1,'#1f77b4'),(2,'#d95f02')):
            minmax_plot(axes[ch-1],channels[ch],offsets[ch]['median_mv'],f'DAC{ch+3}/CH{ch}: all native samples',color,lo=lo,hi=hi)
            selected=[r for r in subset_rows if r['scope_channel']==ch]
            for r in selected:
                axes[ch-1].hlines(r['requested_mv'],r['hold_start_scope_s']*1000,r['hold_end_scope_s']*1000,color='black',linestyles='--',lw=.5)
            axes[ch-1].plot([(r['roi_start_scope_s']+r['roi_end_scope_s'])*500 for r in selected],[r['corrected_median_mv'] for r in selected],'.',color='crimson',ms=2,label='ROI median')
            axes[ch-1].set_ylabel('Corrected mV');axes[ch-1].set_xlabel('Scope time (ms)');axes[ch-1].legend();axes[ch-1].grid(alpha=.2)
        fig.suptitle(f'{name.replace("_"," ").title()} (axis0={row_index}); dashed=requested, red=ROI median')
        fig.savefig(out/f'{name}_zoom.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(13,10),constrained_layout=True)
    for ch in (1,2):
        im=axes[ch-1,0].imshow(maps[f'ch{ch}_error_percent'],origin='lower',aspect='auto',vmin=-10,vmax=10,cmap='coolwarm')
        fig.colorbar(im,ax=axes[ch-1,0],label='Signed % error (display clipped +/-10%; full CSV retained)')
        axes[ch-1,0].set_title(f'DAC{ch+3}/CH{ch} requested-voltage error')
        im2=axes[ch-1,1].imshow(maps[f'ch{ch}_verdict'],origin='lower',aspect='auto',vmin=-1,vmax=1,cmap=ListedColormap(['#cccccc','#bd3c3c','#247c54']))
        bar=fig.colorbar(im2,ax=axes[ch-1,1],ticks=[-1,0,1]);bar.ax.set_yticklabels(['N/A','FAIL','PASS'])
        axes[ch-1,1].set_title('Strict absolute relative error <5%')
        for ax in axes[ch-1]:ax.set_xlabel('Axis1 index (fast)');ax.set_ylabel('Axis0 index (slow)')
    fig.suptitle('Every point/channel verdict; zero targets excluded from percentage')
    fig.savefig(out/'error_and_failure_maps.png',dpi=170);plt.close(fig)
    report=['# 물리 100×100 전압 sweep 분석','',
        f'10,000점·20,000 plateau의 중앙 HOLD 구간을 분석했습니다. 시간/기록 무결성: **{"PASS" if not issues else "FAIL"}**. 비영점 19,800개 중 **PASS {result["passed_nonzero_plateaus"]}, FAIL {result["failed_nonzero_plateaus"]}, 미완료 {result["incomplete_nonzero_plateaus"]}**입니다.',
        f'점 단위 집계(비영점 축 중 하나라도 실패하면 FAIL): {result["point_counts"]}. (0,0)점과 모든 0mV 축의 백분율 판정은 N/A입니다. 전체 결과: **{"PASS" if result["overall_passed"] else "PASS 아님"}**.',
        '', '## 판정 방법','',
        '채널별 100개 0mV HOLD의 중앙 5µs sample을 합친 median 하나를 모든 점에서 동일하게 뺐습니다. 요청 전압(400×index/99)을 분모로 절대 상대오차가 엄격히 5% 미만일 때만 PASS입니다. gain fit·점별 offset·점별 시간 이동은 하지 않았습니다. 평균값은 참고 진단 열로만 보존했습니다.',
        f'요청 endpoint는400mV, 실제 compiler의164-code 일정 증가에 따른 endpoint는{result["actual_compiled_endpoint_mv"]:.9f}mV입니다. 이 차이는 숨기지 않았고 판정 분모를 실제 code 전압으로 바꾸지 않았습니다.',
        '', '|채널|고정 offset(mV)|비영점 PASS|FAIL|raw 수직 간격(mV)|','|---|---:|---:|---:|---:|']
    for ch in (1,2):
        info=result['per_channel'][str(ch)];report.append(f'|DAC{ch+3}/CH{ch}|{offsets[ch]["median_mv"]:.9f}|{info["passed"]}|{info["failed"]}|{info["observed_vertical_step_mv"]:.9f}|')
    report += ['', '## 시간 정렬 및 완전성','',
        f'CH2 raw300mV threshold crossing의 첫 row 끝을point99로 연결했습니다. 1µs 선형 RAMP의 threshold 분율을 첫 anchor 근처 baseline/high에서 구해 단일 시간 offset {alignment:.12g}s를 적용했습니다. 이 전압 두 값은 시간 정렬에만 사용했습니다.',
        f'row 끝99,199,…9999에 해당하는 high-threshold burst {len(row_ends)}개를 검사했고 최대 residual은{diagnostics["max_absolute_row_endpoint_residual_us"]:.6f}µs입니다. 사전 기준은 절대 residual<2µs, dt≤500ns, ROI≥10samples, 순서상 서로 겹치지 않는20000개 window입니다. 실제 두채널 native time축은 각각 유지했습니다.',
        '정렬 문제가 있으면 진폭 수치가 기준 내여도 전체 PASS가 될 수 없습니다. 세부 문제: '+str(issues),
        '', '## 제한과 원시자료','',
        '첫 비영점 요청은4.040404mV이고5%허용폭은0.202020mV입니다. 이 acquisition의 수직 표본 간격·잡음보다 작을 수 있어 median이 같은code에 묶이거나 낮은값의 상대오차가 커질 수 있습니다. 실패는 그대로 보존하며 이 결과만으로 DAC gain/offset 또는 scope 교정 중 원인을 단정하지 않습니다. 별도의 교정 불확도 인증이나 정밀 timing/skew 검증이 아닙니다.',
        '끝 zero는 별도 구간의 baseline residual을 results.json에 저장했습니다. 0mV에 상대% PASS를 부여하지 않았습니다.',
        '- [전체20000개 plateau CSV](all_20000_plateaus.csv)', '- [전체10000점 판정](all_10000_point_verdicts.csv)',
        '- [전체 결과](results.json)', '- [시간 정렬](alignment.json)', '- [고정 offset](offsets.json)',
        '- [전체 capture min/max 그림](full_record_overview.png)', '- [첫 row native-sample 확대](first_row_zoom.png)',
        '- [마지막 row native-sample 확대](last_row_zoom.png)', '- [전점 오차/실패 지도](error_and_failure_maps.png)',
        f'- 원본: ../{args.run}/scope_capture의 채널별 gzip IEEE block와preamble; 모든sample을 무손실 유지하며 여기서는중복저장하지않았습니다.']
    (out/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf8')
    assert all(sha(p)==h for p,h in inputs.items())
    dump(out/'manifest.json',dict(analysis_complete=True,inputs_unchanged=True,physical_run_not_repeated=True,
        files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in out.iterdir() if p.is_file() and p.name!='manifest.json'}))
    print(json.dumps({k:result[k] for k in ('integrity_passed','integrity_issues','passed_nonzero_plateaus','failed_nonzero_plateaus','point_counts','overall_passed','per_channel','final_zero')},indent=2))
    return 0 if not issues else 2

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise
