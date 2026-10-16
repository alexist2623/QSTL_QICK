"""Apply the user's fixed-offset, strict <2% criterion to existing raw capture.

No instrument access. Previous evidence is read only. No gain fitting, per-point
offset, or calibration chosen to obtain a pass.
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
original=json.loads((RUN/'analysis.json').read_text())
capture=json.loads((RUN/'scope_capture/capture.json').read_text())
previous_manifest=json.loads((ROOT/'archive_manifest.json').read_text())
for name,row in previous_manifest['files'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==row['sha256'],name

offsets={};rows=[];traces={};zeros={}
for ch in (1,2):
    with np.load(RUN/f'scope_capture/ch{ch}.npz',allow_pickle=False) as f:
        t=f['time_s'].copy();v=f['voltage_v'].copy()
    traces[ch]=(t,v)
    zero_samples=[]
    for r in original['rows']:
        if r['scope_channel']!=ch or r['requested_mv']!=0:continue
        start=r['hold_start_scope_s'];end=r['hold_end_scope_s']
        mask=(t>=start+.25*(end-start))&(t<=end-.25*(end-start))
        zero_samples.append(v[mask]*1000)
    values=np.concatenate(zero_samples)
    assert len(values)==187500 and np.isfinite(values).all()
    offsets[ch]=dict(median_mv=float(np.median(values)),mean_mv=float(np.mean(values)),
                     samples=len(values),zero_point_indices=[r['point'] for r in original['rows'] if r['scope_channel']==ch and r['requested_mv']==0])
for r in original['rows']:
    ch=r['scope_channel'];target=r['requested_mv']
    corrected=r['measured_median_mv']-offsets[ch]['median_mv']
    corrected_mean=r['measured_mean_mv']-offsets[ch]['mean_mv']
    percent=100*(corrected-target)/abs(target) if target else None
    mean_percent=100*(corrected_mean-target)/abs(target) if target else None
    rows.append(dict(point=r['point'],scope_channel=ch,panel_dac=r['panel_dac'],
        requested_mv=target,raw_median_mv=r['measured_median_mv'],
        fixed_offset_mv=offsets[ch]['median_mv'],corrected_mv=corrected,
        signed_error_pct=percent,absolute_error_pct=abs(percent) if percent is not None else None,
        passed=bool(abs(percent)<2.) if percent is not None else None,
        mean_corrected_mv=corrected_mean,mean_signed_error_pct=mean_percent,
        mean_passed=bool(abs(mean_percent)<2.) if mean_percent is not None else None))
tested=[r for r in rows if r['passed'] is not None]
storage=dict(previous_full_evidence_bytes=47481683,full_resolution_samples_per_channel=1500000,
    raw_uint16_bytes_both_channels=6000000,
    derived_npz_bytes_both_channels=9913281+9817449,
    raw_gzip_level9_bytes_ch1=486614,raw_gzip_level9_bytes_ch2=446651,
    raw_gzip_level9_total_bytes=933265,
    lossless_compression_measurement='gzip.compress(raw,compresslevel=9,mtime=0); decompressed bytes verified identical in memory',
    saved_compressed_raw_files=False,deleted_files=False,
    recommendation='Retain all raw sample codes once, losslessly compressed, with preamble and capture metadata. Time and voltage arrays are reproducible and need not be duplicated. Existing evidence remains unchanged.')
result=dict(criterion='abs((plateau median - fixed channel zero median) - requested voltage) / abs(requested voltage) * 100 < 2',
    threshold_percent=2.,comparison='strictly_less_than',denominator='requested 200 or 400 mV, not quantized nominal',
    offset_policy='One fixed median offset per channel from all three 0-mV plateau center windows, 187500 samples per channel',
    zero_policy='0 mV establishes the offset; relative percent error and pass are undefined and stored as null',
    offsets=offsets,nonzero_plateaus=len(tested),passed=sum(r['passed'] for r in tested),
    failed=sum(not r['passed'] for r in tested),overall_passed=all(r['passed'] for r in tested),
    failing_points=[dict(point=r['point'],panel_dac=r['panel_dac'],requested_mv=r['requested_mv'],error_pct=r['signed_error_pct']) for r in tested if not r['passed']],
    rows=rows,storage=storage,original_archive_hashes_unchanged=True,
    capture_id=capture['capture_id'],new_hardware_execution=False)
(HERE/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
with (HERE/'corrected_measurements.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

fig,axes=plt.subplots(3,1,figsize=(14,10),constrained_layout=True)
for ch,color in ((1,'#1f77b4'),(2,'#d95f02')):
    t,v=traces[ch];step=max(1,len(t)//60000)
    axes[ch-1].plot(t[::step]*1000,v[::step]*1000-offsets[ch]['median_mv'],color=color,lw=.65,
        label=f'DAC{ch+3}, fixed offset removed ({offsets[ch]["median_mv"]:.3f} mV)')
    for r in original['rows']:
        if r['scope_channel']==ch:
            axes[ch-1].hlines(r['requested_mv'],r['hold_start_scope_s']*1000,r['hold_end_scope_s']*1000,color='black',ls='--',lw=.8)
    axes[ch-1].set_xlabel('Scope trigger-relative time (ms)');axes[ch-1].set_ylabel('Corrected voltage (mV)');axes[ch-1].legend();axes[ch-1].grid(alpha=.25)
    rr=[r for r in tested if r['scope_channel']==ch]
    axes[2].plot([r['point'] for r in rr],[r['signed_error_pct'] for r in rr],'o-',color=color,label=f'DAC{ch+3}')
axes[2].axhline(2,color='black',ls='--');axes[2].axhline(-2,color='black',ls='--')
axes[2].set_xlabel('Sweep point (0-mV points excluded)');axes[2].set_ylabel('Error / requested voltage (%)');axes[2].grid(alpha=.25);axes[2].legend()
fig.suptitle('Fixed-offset correction: strict |error| < 2%\nDAC4 passes; DAC5 at 400 mV remains outside the limit')
fig.savefig(HERE/'offset_corrected.png',dpi=170);plt.close(fig)

summary=[]
for ch in (1,2):
    for target in (200,400):
        r=next(r for r in tested if r['scope_channel']==ch and r['requested_mv']==target)
        summary.append(f'| DAC{r["panel_dac"]} / CH{ch} | {target} | {r["corrected_mv"]:.3f} | {r["absolute_error_pct"]:.3f}% | {"PASS" if r["passed"] else "FAIL"} |')
report='''# Offset 제거 후 2% 기준 재판정

사용자 요청에 따라 각 채널의 고정 offset을 뺀 뒤, 요청 전압 대비 절대 오차가 **2% 미만일 때만 PASS**로 판정했습니다. 기존 실측 데이터를 다시 분석했으며 장비를 새로 실행하거나 원본 데이터를 바꾸지 않았습니다.

DAC4 offset은 −27.61508352 mV, DAC5 offset은 −14.22596096 mV입니다. 각 채널의 0 mV plateau 세 구간 중앙 50%, 총 187,500개 샘플에서 median 하나를 구하고 모든 점에 동일하게 적용했습니다. gain 보정이나 점별 offset은 적용하지 않았습니다.

| 출력 | 설정 (mV) | Offset 보정 후 (mV) | 절대 오차 | 판정 |
|---|---:|---:|---:|---|
'''+ '\n'.join(summary)+'''

각 조건이 세 번씩 있으므로 비영점 plateau **12개 중 9개 PASS, 3개 FAIL**입니다. 실패는 DAC5의 400 mV 세 점(점 번호 2·5·8)입니다. 따라서 전체 PASS는 아닙니다. 0 mV는 분모가 0이므로 백분율 오차 판정에서 제외하고 offset 계산에 사용했습니다.

기존과 동일한 median을 주 판정값으로 유지했습니다. 참고로 fixed mean offset과 plateau mean을 사용해도 DAC5의 400 mV 오차는 2.020–2.063%여서 엄격한 2% 미만 기준을 통과하지 않습니다. 반올림하여 2.0%로 표시한 뒤 PASS로 바꾸지 않았습니다. 현재 scope 수직 표본 간격은 약 6.695 mV이며 별도의 장비 교정 불확도는 이번 요청의 판정식에 추가하지 않았습니다.

- [Offset 보정 파형·오차 plot](offset_corrected.png)
- [전체 수치](results.json)
- [점별 CSV](corrected_measurements.csv)
- [보정 전 실측 보고서](../REPORT.md)

## 저장 용량

현재 보정 전 증거 전체는 **47,481,683 bytes (47.48 MB, 45.28 MiB)**입니다. 유효 취득의 실제 원시 코드는 두 채널 총 300만 샘플 × 2 bytes = **6,000,000 bytes (6 MB)**입니다. 같은 원시 코드의 여러 사본과 재생성 가능한 시간·전압 배열을 함께 저장해서 전체 용량이 늘었습니다.

두 raw payload를 gzip level 9로 무손실 압축해 메모리에서 시험하고 압축 해제 일치까지 확인한 결과, 각각 486,614 / 446,651 bytes, 합계 **933,265 bytes (0.93 MB)**였습니다. 여기에 preamble·취득 설정·해시를 보존하면 모든 샘플의 시간과 전압을 다시 계산할 수 있습니다. 기존 NPZ의 시간·전압 배열 약 19.73 MB와 raw 중복 사본은 재현을 위한 필수 항목이 아닙니다.

단순 통과 여부만 보려면 모든 샘플이 필수는 아니지만, glitch·잡음·경계 구간을 나중에 다시 확인하려면 **전체 raw code를 한 번만 무손실 압축해 보관**하는 방식이 적절합니다. 이번에는 용량 확인과 재판정만 했으며 기존 파일을 삭제하거나 덮어쓰지 않았습니다.
'''
(HERE/'REPORT.md').write_text(report,encoding='utf-8')
files={str(p.relative_to(HERE)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in HERE.iterdir() if p.is_file() and p.name!='manifest.json'}
(HERE/'manifest.json').write_text(json.dumps(dict(files=files,original_capture_unchanged=True),indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('offsets','nonzero_plateaus','passed','failed','overall_passed','failing_points')},indent=2))
