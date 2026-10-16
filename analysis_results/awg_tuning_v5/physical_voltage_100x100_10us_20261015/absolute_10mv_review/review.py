"""Reassess existing physical data: FAIL iff fixed-offset error exceeds 10 mV.

No instrument access and no edits to previous captures or assessments.
"""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = ROOT/'analysis_run_01'
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, v): Path(p).write_text(json.dumps(v, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
def csv_save(p, rows):
    with Path(p).open('x', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def passed(error): return abs(error) <= 10.

assert passed(10.) and passed(-10.) and not passed(10.000001) and not passed(-10.000001)
if (HERE/'results.json').exists(): raise FileExistsError('Existing review evidence is immutable')
manifest = read(ROOT/'archive_manifest.json')
for name, info in manifest['files'].items(): assert sha(ROOT/name) == info['sha256'], name
original = read(SOURCE/'results.json')
assert original['integrity_passed'] and original['analysis_complete']
rows = []
with (SOURCE/'all_20000_plateaus.csv').open(encoding='utf-8') as f:
    for r in csv.DictReader(f):
        assert r['roi_valid'] == 'True' and int(r['samples']) == 25
        raw = float(r['raw_median_mv']); offset = float(r['fixed_offset_mv'])
        corrected = raw-offset; target = float(r['requested_mv']); error = corrected-target
        assert abs(error-float(r['error_mv'])) < 1e-12
        assert abs(corrected-float(r['corrected_median_mv'])) < 1e-12
        rows.append(dict(point=int(r['point']), axis0=int(r['axis0']), axis1=int(r['axis1']),
            scope_channel=int(r['scope_channel']), panel_dac=int(r['panel_dac']),
            requested_mv=target, raw_median_mv=raw, fixed_offset_mv=offset,
            corrected_median_mv=corrected, signed_error_mv=error, absolute_error_mv=abs(error),
            passed=passed(error), zero_target=target == 0.))
assert len(rows) == 20000
points = []
for i in range(10000):
    pair = rows[2*i:2*i+2]
    assert [r['point'] for r in pair] == [i, i] and [r['scope_channel'] for r in pair] == [1, 2]
    points.append(dict(point=i, axis0=i//100, axis1=i%100,
        passed=all(r['passed'] for r in pair), ch1_error_mv=pair[0]['signed_error_mv'],
        ch2_error_mv=pair[1]['signed_error_mv']))
csv_save(HERE/'all_20000_plateaus.csv', rows)
csv_save(HERE/'all_10000_point_verdicts.csv', points)
per_channel = {}
for ch in (1, 2):
    rr = [r for r in rows if r['scope_channel'] == ch]; failed = [r for r in rr if not r['passed']]
    zero = [r for r in rr if r['zero_target']]
    worst = max(rr, key=lambda r: r['absolute_error_mv'])
    per_channel[str(ch)] = dict(passed=sum(r['passed'] for r in rr), failed=len(failed),
        zero_target_count=len(zero), zero_target_passed=sum(r['passed'] for r in zero),
        max_absolute_error_mv=worst['absolute_error_mv'], worst_example=worst,
        failed_requested_min_mv=min((r['requested_mv'] for r in failed), default=None),
        failed_requested_max_mv=max((r['requested_mv'] for r in failed), default=None))

# Apply exactly the same new rule to the earlier 3x3 data as a separate result.
prior_dir = ROOT.parent/'physical_voltage_2axis_20261015/offset_5pct_review'
for name, info in read(prior_dir/'manifest.json')['files'].items():
    assert sha(prior_dir/name) == info['sha256'], name
prior_rows = list(csv.DictReader((prior_dir/'corrected_measurements.csv').open(encoding='utf-8')))
prior = []
for r in prior_rows:
    error = float(r['corrected_mv'])-float(r['requested_mv'])
    prior.append(dict(point=int(r['point']), scope_channel=int(r['scope_channel']),
        requested_mv=float(r['requested_mv']), corrected_mv=float(r['corrected_mv']),
        signed_error_mv=error, passed=passed(error)))
csv_save(HERE/'prior_3x3_plateaus.csv', prior)
prior_point_pass = [all(r['passed'] for r in prior if r['point'] == i) for i in range(9)]
result = dict(criterion='FAIL iff abs((plateau median - fixed channel offset) - requested voltage) > 10 mV',
    tolerance_mv=10., failure_comparison='strictly_greater_than', pass_comparison='less_than_or_equal',
    offset_policy='Unchanged fixed per-channel median from the 100 zero-HOLD central windows',
    zero_policy='0 mV axes and (0,0) point included in absolute-error verdict; no percentage denominator',
    source_capture_id=original['capture_id'], new_hardware_execution=False,
    plateau_counts=dict(total=20000, passed=sum(r['passed'] for r in rows), failed=sum(not r['passed'] for r in rows)),
    point_counts=dict(total=10000, passed=sum(r['passed'] for r in points), failed=sum(not r['passed'] for r in points)),
    per_channel=per_channel, integrity_passed=original['integrity_passed'],
    overall_passed=all(r['passed'] for r in points),
    previous_5pct_point_counts=original['point_counts'],
    prior_3x3=dict(plateaus=18, passed_plateaus=sum(r['passed'] for r in prior),
        failed_plateaus=sum(not r['passed'] for r in prior), passed_points=sum(prior_point_pass),
        failed_points=sum(not p for p in prior_point_pass)),
    previous_evidence_unchanged=True,
    interpretation='This is a plateau-median accuracy check; individual noisy samples/glitches are not assigned this verdict. No gain/per-point correction or time-window changes.')
save(HERE/'results.json', result)

fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
for ch in (1, 2):
    rr = [r for r in rows if r['scope_channel'] == ch]
    errors = np.array([r['signed_error_mv'] for r in rr]).reshape(100, 100)
    verdicts = np.array([int(r['passed']) for r in rr]).reshape(100, 100)
    im = axes[ch-1, 0].imshow(errors, origin='lower', aspect='auto', vmin=-15, vmax=15, cmap='coolwarm')
    fig.colorbar(im, ax=axes[ch-1, 0], label='Fixed-offset error (mV)')
    axes[ch-1, 0].set_title(f'DAC{ch+3}/CH{ch}: measured minus requested')
    im = axes[ch-1, 1].imshow(verdicts, origin='lower', aspect='auto', vmin=0, vmax=1,
        cmap=ListedColormap(['#bd3c3c', '#247c54']))
    bar = fig.colorbar(im, ax=axes[ch-1, 1], ticks=[0, 1]); bar.ax.set_yticklabels(['FAIL', 'PASS'])
    axes[ch-1, 1].set_title(f'PASS {per_channel[str(ch)]["passed"]}, FAIL {per_channel[str(ch)]["failed"]}')
    for ax in axes[ch-1]: ax.set_xlabel('Axis 1 index (fast)'); ax.set_ylabel('Axis 0 index (slow)')
fig.suptitle('Existing 100 x 100 / 10 us physical capture: FAIL only when |error| > 10 mV\nFixed offsets and windows unchanged; zero-voltage points included')
fig.savefig(HERE/'absolute_error_maps.png', dpi=170); plt.close(fig)
report = f'''# 절대오차 10 mV 기준 재판정

사용자 요청에 따라 **고정 offset 보정 후 요청 전압과의 절대 차이가 10 mV를 초과하면 FAIL**, **10 mV 이하면 PASS**로 판정했습니다. 정확히 ±10 mV인 값은 PASS입니다. 기존 100×100 · 10 µs HOLD 실물 기록을 재분석했으며 새 장비 실행은 하지 않았습니다.

10,000점 중 **{result['point_counts']['passed']:,} PASS / {result['point_counts']['failed']:,} FAIL**입니다. 두 축 중 하나라도 실패하면 그 점은 FAIL입니다. 20,000개 채널 HOLD 측정 중 **{result['plateau_counts']['passed']:,} PASS / {result['plateau_counts']['failed']:,} FAIL**입니다. 전체 PASS 여부: **{result['overall_passed']}**.

| 출력 | PASS | FAIL | 최대 절대오차 |
|---|---:|---:|---:|
| DAC4 / CH1 | {per_channel['1']['passed']:,} | {per_channel['1']['failed']:,} | {per_channel['1']['max_absolute_error_mv']:.6f} mV |
| DAC5 / CH2 | {per_channel['2']['passed']:,} | {per_channel['2']['failed']:,} | {per_channel['2']['max_absolute_error_mv']:.6f} mV |

기존과 동일하게 각 HOLD 중앙 5 µs의 25 samples median을 사용했습니다. 고정 offset은 DAC4 −24.26771712 mV, DAC5 −14.22587904 mV이며, 시간 구간·gain·offset·요청 전압 기준은 바꾸지 않았습니다. 이 판정은 각 HOLD의 대표 전압 오차이며 순간 noise/glitch sample 하나하나의 초과 여부를 의미하지 않습니다.

절대오차 방식이므로 **0 mV 축 200개와 (0,0)점도 포함**했습니다. 0 mV 측정은 두 채널 각각 {per_channel['1']['zero_target_passed']}/100, {per_channel['2']['zero_target_passed']}/100 PASS입니다. 이 0 mV 구간들은 고정 offset을 구하는 데도 사용됐습니다.

이전 3×3 데이터도 같은 기준으로 재판정하면 채널 측정 {result['prior_3x3']['passed_plateaus']}/18 PASS, 점 단위 {result['prior_3x3']['passed_points']}/9 PASS입니다. 이는 이전 5% 판정과 다른 기준이며 기존 결과는 그대로 보존했습니다.

- [절대오차·실패 지도](absolute_error_maps.png)
- [20,000개 측정값](all_20000_plateaus.csv) · [10,000점 판정](all_10000_point_verdicts.csv)
- [전체 결과 JSON](results.json)
- [원래 실물 측정 보고서와 파형](../REPORT.md) · [10 µs 펄스 확대](../pulse_detail.png)

실물 기록의 누락·clipping·시간 구간 검증은 이전과 동일하게 통과 상태입니다. 기존 원시 기록 및 5% 보고서/그림/판정을 덮어쓰지 않았고 보존 해시가 일치합니다.
'''
(HERE/'REPORT.md').write_text(report, encoding='utf-8')
for name, info in manifest['files'].items(): assert sha(ROOT/name) == info['sha256'], name
save(HERE/'manifest.json', dict(files={p.name:dict(bytes=p.stat().st_size, sha256=sha(p))
    for p in HERE.iterdir() if p.is_file() and p.name != 'manifest.json'}, previous_evidence_unchanged=True))
print(json.dumps(result, indent=2, ensure_ascii=False))
