"""User-authorized strict <5% reanalysis of the existing 3x3 physical capture.

No instrument imports/access, no production edits, and no rewriting previous
2%/uncorrected evidence. One fixed median offset per channel, requested-voltage
denominator, and unchanged plateau windows are retained.
"""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
RUN=ROOT/'run_03'
OLD=ROOT/'offset_2pct_review'
THRESHOLD=5.0
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf8')

protected={}
for base,manifest_name in ((ROOT,'archive_manifest.json'),(OLD,'manifest.json')):
    manifest=read(base/manifest_name)
    protected[str(base/manifest_name)]=sha(base/manifest_name)
    for name,info in manifest['files'].items():
        path=base/name
        assert sha(path)==info['sha256'],str(path)
        protected[str(path)]=info['sha256']
dump('input_hashes.json',protected)
original=read(RUN/'analysis.json')
capture=read(RUN/'scope_capture/capture.json')
previous=read(OLD/'results.json')
assert original['capture_id']==capture['capture_id']==previous['capture_id']
assert previous['threshold_percent']==2.0

offsets={};rows=[];traces={};windows={}
for channel in (1,2):
    record=capture['channels'][str(channel)]
    payload=(RUN/f'scope_capture/ch{channel}.payload.bin').read_bytes()
    assert hashlib.sha256(payload).hexdigest()==record['payload_sha256']
    preamble=record['preamble']
    raw=np.frombuffer(payload,dtype='<u2')
    voltage=(raw.astype(np.float64)-preamble['y_reference'])*preamble['y_increment']+preamble['y_origin']
    time=(np.arange(len(raw))-preamble['x_reference'])*preamble['x_increment']+preamble['x_origin']
    with np.load(RUN/f'scope_capture/ch{channel}.npz',allow_pickle=False) as arrays:
        assert np.array_equal(arrays['raw_codes'],raw)
        assert np.array_equal(arrays['voltage_v'],voltage)
        assert np.array_equal(arrays['time_s'],time)
        assert not arrays['invalid'].any()
    traces[channel]=(time,voltage)
    baseline=[]
    for original_row in original['rows']:
        if original_row['scope_channel']!=channel:continue
        start=original_row['hold_start_scope_s'];end=original_row['hold_end_scope_s']
        values=voltage[(time>=start+.25*(end-start))&(time<=end-.25*(end-start))]*1000.
        assert len(values)==62500 and np.isfinite(values).all()
        assert float(np.median(values))==original_row['measured_median_mv']
        windows[(channel,original_row['point'])]=values
        if original_row['requested_mv']==0:baseline.append(values)
    baseline=np.concatenate(baseline)
    assert len(baseline)==187500
    offsets[channel]=dict(median_mv=float(np.median(baseline)),mean_mv=float(baseline.mean()),
        samples=len(baseline),zero_point_indices=[r['point'] for r in original['rows']
            if r['scope_channel']==channel and r['requested_mv']==0])
    assert offsets[channel]==previous['offsets'][str(channel)]

for original_row in original['rows']:
    channel=original_row['scope_channel'];target=original_row['requested_mv']
    values=windows[(channel,original_row['point'])]
    corrected=float(np.median(values))-offsets[channel]['median_mv']
    corrected_mean=float(values.mean())-offsets[channel]['mean_mv']
    percent=100*(corrected-target)/abs(target) if target else None
    mean_percent=100*(corrected_mean-target)/abs(target) if target else None
    old_row=next(r for r in previous['rows'] if r['point']==original_row['point'] and r['scope_channel']==channel)
    assert corrected==old_row['corrected_mv'] and percent==old_row['signed_error_pct']
    rows.append(dict(point=original_row['point'],scope_channel=channel,panel_dac=original_row['panel_dac'],
        requested_mv=target,raw_median_mv=float(np.median(values)),fixed_offset_mv=offsets[channel]['median_mv'],
        corrected_mv=corrected,signed_error_pct=percent,absolute_error_pct=abs(percent) if percent is not None else None,
        passed=bool(abs(percent)<THRESHOLD) if percent is not None else None,
        previous_2pct_passed=old_row['passed'],mean_corrected_mv=corrected_mean,
        mean_signed_error_pct=mean_percent,mean_passed=bool(abs(mean_percent)<THRESHOLD) if mean_percent is not None else None,
        samples=len(values)))
tested=[r for r in rows if r['passed'] is not None]
assert len(tested)==12 and all(r['passed'] for r in tested)
result=dict(criterion='abs((plateau median - fixed channel zero median) - requested voltage) / abs(requested voltage) * 100 < 5',
    threshold_percent=THRESHOLD,comparison='strictly_less_than',denominator='requested 200 or 400 mV, not quantized nominal',
    offset_policy='One fixed median offset per channel from all three zero plateau center windows (187500 samples per channel), unchanged from the 2% review',
    zero_policy='0 mV establishes offset; relative percent error and verdict undefined/null',
    offsets=offsets,nonzero_plateaus=len(tested),passed=sum(r['passed'] for r in tested),
    failed=sum(not r['passed'] for r in tested),overall_passed=all(r['passed'] for r in tested),
    maximum_absolute_error_percent=max(r['absolute_error_pct'] for r in tested),
    zero_plateaus_excluded=6,rows=rows,capture_id=capture['capture_id'],new_hardware_execution=False,
    source_capture='run_03',previous_2pct_results_sha256=sha(OLD/'results.json'),
    previous_2pct_verdict_unchanged=True,original_capture_unchanged=True,
    raw_decode_independently_verified=True,limitations=['Existing 3x3 data only; not the newly requested 100x100 acquisition.',
        'One fixed offset removed; no gain fit, point-specific correction, new waveform alignment, or threshold relaxation beyond the explicitly requested 5%.',
        'Scope vertical code spacing is about 6.69456128 mV in this acquisition. This is a user-defined engineering criterion, not calibrated absolute-accuracy certification.'])
dump('results.json',result)
with (HERE/'corrected_measurements.csv').open('w',newline='',encoding='utf8') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

fig,axes=plt.subplots(3,1,figsize=(14,10),constrained_layout=True)
for channel,color in ((1,'#1f77b4'),(2,'#d95f02')):
    time,voltage=traces[channel];step=max(1,len(time)//60000)
    axes[channel-1].plot(time[::step]*1000,voltage[::step]*1000-offsets[channel]['median_mv'],
        color=color,lw=.65,label=f'DAC{channel+3}: fixed offset {offsets[channel]["median_mv"]:.3f} mV removed')
    for row in original['rows']:
        if row['scope_channel']==channel:
            axes[channel-1].hlines(row['requested_mv'],row['hold_start_scope_s']*1000,
                row['hold_end_scope_s']*1000,color='black',linestyles='--',lw=.8)
    axes[channel-1].set_xlabel('Scope trigger-relative time (ms)');axes[channel-1].set_ylabel('Corrected voltage (mV)')
    axes[channel-1].legend();axes[channel-1].grid(alpha=.25)
    selected=[r for r in tested if r['scope_channel']==channel]
    axes[2].plot([r['point'] for r in selected],[r['signed_error_pct'] for r in selected],
        'o-',color=color,label=f'DAC{channel+3}')
axes[2].axhline(THRESHOLD,color='black',linestyle='--',label='Strict limits; equality would fail')
axes[2].axhline(-THRESHOLD,color='black',linestyle='--')
axes[2].set_ylim(-6,6);axes[2].set_xlabel('Cartesian point (0-mV points excluded)')
axes[2].set_ylabel('Error / requested voltage (%)');axes[2].grid(alpha=.25);axes[2].legend()
fig.suptitle('Existing 3 x 3 capture: fixed-offset correction, strict |error| < 5%\n12 / 12 nonzero plateaus PASS; original measurements and 2% review retained')
fig.savefig(HERE/'offset_corrected.png',dpi=170);plt.close(fig)

report=['# 기존 3×3 실측의 고정 오프셋 제거 후 5% 재판정','',
    '사용자가 새로 지정한 **절대 상대오차 < 5%** 기준으로 기존 run_03을 재분석했습니다. 비영점 plateau **12/12 PASS**, 최대 절대오차 **2.92886144%**입니다. 새 100×100 실측 결과가 아닙니다.',
    '', '채널마다 0 mV plateau 세 구간 중앙 50%의 총 187,500개 sample에서 얻은 median 하나를 모든 점에 동일하게 뺐습니다. DAC4/CH1 offset은 −27.61508352 mV, DAC5/CH2는 −14.22596096 mV입니다. 이전 2% 분석과 offset·median·window·요청전압 분모가 같고 판정 한계만 사용자 요청대로 바뀌었습니다. Gain 보정이나 점별 offset은 적용하지 않았습니다.',
    '', '| 출력 | 요청 전압 | 보정 후 | 부호 있는 상대오차 | <5% |','|---|---:|---:|---:|---|']
for channel in (1,2):
    for target in (200,400):
        row=next(r for r in tested if r['scope_channel']==channel and r['requested_mv']==target)
        report.append(f'|DAC{channel+3}/CH{channel}|{target} mV|{row["corrected_mv"]:.6f} mV|{row["signed_error_pct"]:+.6f}%|PASS (각 3점)|')
report += ['', '0 mV 여섯 plateau는 offset 계산에 사용하며 분모가 0이므로 백분율 오차·PASS 판정은 null입니다. 5%와 같은 값은 FAIL이며 반올림한 표시값으로 판정하지 않았습니다.',
    '', '원시 payload를 `<u2`와 저장된 preamble로 다시 해독해 전체 NPZ time/voltage/code와 일치함을 확인했습니다. 18개 plateau window도 원시 배열에서 다시 계산했고 이전 median 값과 일치합니다. 기존 capture·보정 전 보고서·2% 결과/그림/소스의 모든 보존 해시를 실행 전후 검증했습니다. **기존 2% 기준의 9 PASS/3 FAIL 결과는 변경하지 않았습니다.**',
    '', '이번 acquisition의 수직 raw code 간격은 약 6.695 mV이며 이 판정은 사용자 정의 공학 기준입니다. 별도의 교정 정확도·불확도 인증으로 해석하지 않습니다. 원본을 새로 측정하거나 삭제하지 않았습니다.',
    '', '- [새 판정 수치](results.json)', '- [18개 plateau CSV](corrected_measurements.csv)',
    '- [보정 파형과 ±5% 오차 그림](offset_corrected.png)', '- [이전 2% 보고서](../offset_2pct_review/REPORT.md)',
    '- [보존 입력 SHA256](input_hashes.json)']
(HERE/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf8')
assert all(sha(path)==digest for path,digest in protected.items())
dump('input_integrity.json',dict(before_after_equal=True,protected_file_count=len(protected),
    original_and_2pct_evidence_unchanged=True,inputs_manifest_sha256=sha(HERE/'input_hashes.json')))
print(json.dumps({k:result[k] for k in ('threshold_percent','nonzero_plateaus','passed','failed','overall_passed','maximum_absolute_error_percent','offsets')},indent=2))
