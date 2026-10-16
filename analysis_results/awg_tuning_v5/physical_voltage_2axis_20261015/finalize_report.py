"""Produce report and separate plots from preserved physical measurements."""
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
run=HERE/'run_03'
a=json.loads((run/'analysis.json').read_text())
c=json.loads((run/'scope_capture/capture.json').read_text())
s=json.loads((run/'status.json').read_text())
rows=a['rows']
ordered=all(int(np.digitize(r['measured_median_mv'],[100.,300.]))==r[f'axis{r["scope_channel"]-1}'] for r in rows)
summary=[]
for ch in (1,2):
    levels=[]
    for target in (0,200,400):
        rr=[r for r in rows if r['scope_channel']==ch and r['requested_mv']==target]
        levels.append(dict(requested_mv=target,median_of_plateau_medians_mv=float(np.median([r['measured_median_mv'] for r in rr])),
                           mean_of_plateau_means_mv=float(np.mean([r['measured_mean_mv'] for r in rr]))))
    summary.append(dict(scope_channel=ch,panel_dac=ch+3,awg_generator=2*ch-1,levels=levels))
result=dict(sweep_order_passed=ordered,absolute_voltage_screen_passed=a['basic_check_passed'],
    actual_hardware_points=9,measured_plateaus=18,channels=summary,
    max_absolute_nominal_error_mv=a['max_absolute_nominal_error_mv'],
    final_zero=a['final_zero'],scope_restored=s['scope_restore']['passed'],
    zero_command_completed=s['cleanup_zero'],source_changes=s['production_sources_changed'],
    record_points_per_channel=1500000,sample_interval_ns=8.,record_duration_ms=12.,
    observed_vertical_code_step_mv=6.69456128,
    channel_origin_difference_ps=c['time_grid_comparison']['x_origin']['delta_ch2_minus_ch1']*1e12,
    scope_input='DC, 1 MOhm, probe factor 1; original impedance/probe retained',
    voltage_reference='GUI current-based nominal full scale 801.48 mV; no external gain/offset calibration applied',
    interpretation='Correct two-axis ordering; absolute voltage screen fails. No automatic calibration or production fix performed.')
(HERE/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')

fig,axes=plt.subplots(2,1,figsize=(14,7),constrained_layout=True)
for ch,color in ((1,'#1f77b4'),(2,'#d95f02')):
    with np.load(run/f'scope_capture/ch{ch}.npz',allow_pickle=False) as f:
        t=f['time_s'];v=f['voltage_v'];stride=max(1,len(t)//60000)
        axes[ch-1].plot(t[::stride]*1000,v[::stride]*1000,color=color,lw=.65,label=f'DAC{ch+3} / scope CH{ch}')
    for r in [x for x in rows if x['scope_channel']==ch]:
        axes[ch-1].hlines(r['quantized_nominal_mv'],1000*r['hold_start_scope_s'],1000*r['hold_end_scope_s'],color='black',ls='--',lw=.8)
        axes[ch-1].text(500*(r['hold_start_scope_s']+r['hold_end_scope_s']),r['measured_median_mv']+25,str(r['point']),ha='center')
    axes[ch-1].set_ylabel('Voltage (mV)');axes[ch-1].set_xlabel('Time relative to scope trigger (ms)');axes[ch-1].grid(alpha=.25);axes[ch-1].legend()
fig.suptitle('Measured 3 x 3 voltage sweep — one acquisition, DAC4 and DAC5\nDashed lines: nominal voltage. No gain/offset correction applied.')
fig.savefig(run/'waveforms.png',dpi=170);plt.close(fig)
fig,ax=plt.subplots(figsize=(12,4.8),constrained_layout=True)
for ch,color in ((1,'#1f77b4'),(2,'#d95f02')):
    rr=[r for r in rows if r['scope_channel']==ch]
    ax.plot([r['point'] for r in rr],[r['measured_median_mv'] for r in rr],'o-',color=color,label=f'DAC{ch+3} measured median')
    ax.plot([r['point'] for r in rr],[r['quantized_nominal_mv'] for r in rr],'x--',color=color,alpha=.6,label=f'DAC{ch+3} nominal')
ax.set_xlabel('Sweep point index');ax.set_ylabel('Plateau voltage (mV)');ax.set_xticks(range(9));ax.grid(alpha=.25);ax.legend(ncol=2)
ax.set_title('9-point ordering confirmed; absolute voltage offset remains')
fig.savefig(run/'voltage_levels.png',dpi=170);plt.close(fig)

table='\n'.join(f'| {x["panel_dac"]} / {x["scope_channel"]} | '+ ' | '.join(f'{y["median_of_plateau_medians_mv"]:.3f}' for y in x['levels'])+' |' for x in summary)
report=f'''# 실물 오실로스코프 2축 voltage sweep — 2026-10-15

**9점의 두 축 순서는 확인했습니다. 절대 전압 정확도는 PASS가 아닙니다.**

사용자가 확인한 전면 DAC4 → scope CH1, DAC5 → CH2 연결에서 각각 0·200·400 mV, identity matrix, 3×3 Cartesian sweep을 실행했습니다. AWG generator는 각각 1·3입니다. 실제 GUI 입력·sweep dialog → 생산 compiler로 만든 152-word 프로그램을 기존 RFSoC 서버에서 실행했고 완료 counter는 **9/9**였습니다. 각 점의 HOLD는 1 ms입니다.

| 전면 DAC / scope CH | 0 mV 설정 시 측정 | 200 mV 설정 시 측정 | 400 mV 설정 시 측정 |
|---|---:|---:|---:|
{table}

단위는 mV이며 평탄부 중앙 50% 구간의 median입니다. 코드 양자화 후 명목값은 0 / 199.978652 / 399.957305 mV입니다. 최대 명목값 대비 편차는 **{a['max_absolute_nominal_error_mv']:.3f} mV**였습니다. 단순 engineering screen `5 mV + 명목 전압의 2%`를 통과하지 못했습니다. 이는 장비 교정 불확도에 기반한 공식 정확도 규격이 아닙니다. GUI의 801.48 mV full scale은 실제 DAC 전류 20,037 µA에 대한 선형 기준값이며, 외부 fixture의 gain/offset 교정은 적용하지 않았습니다. 현재 측정만으로 편차 원인을 보드·케이블·오실로스코프 중 하나로 확정하지 않습니다.

점 순서는 `(0,0), (0,200), (0,400), (200,0), (200,200), (200,400), (400,0), (400,200), (400,400)`입니다. 두 번째 축이 가장 빠릅니다. 독립적으로 100·300 mV 경계를 사용해 각 측정 레벨을 분류했을 때 18개 plateau의 좌표가 모두 일치했습니다. 이 순서 확인은 절대 전압 정확도 판정과 별개입니다.

## 저장된 파형

- [두 채널 실측 파형](run_03/waveforms.png)
- [9점 설정값·측정값 비교](run_03/voltage_levels.png)
- [통합 그림](run_03/voltage_sweep.png)
- [18개 plateau 측정 CSV](run_03/plateau_measurements.csv)
- [분석 수치](run_03/analysis.json), [실행·정리 상태](run_03/status.json)
- [채널 1 원시 코드/시간/전압](run_03/scope_capture/ch1.npz), [채널 2 원시 코드/시간/전압](run_03/scope_capture/ch2.npz)
- [Preamble·취득 설정·SHA256](run_03/scope_capture/capture.json)

DSO-X 6004A(MY60101437), DC coupling, 1 MΩ, probe factor 1로 측정했습니다. SINGLE 한 번으로 두 채널을 취득하고 STOP 상태에서 읽었습니다. 채널당 **1,500,000 samples**, 간격 **8 ns**, 전체 **12 ms**를 보존했습니다. Hole/clipping special code는 두 채널 모두 0개였습니다. 그림만 표시용으로 줄였고 원시 데이터·NPZ는 전체 해상도입니다. 저장 후 NPZ 재읽기와 binary SHA256도 확인했습니다.

독립 검토에서도 raw WORD/preamble로 300만 점의 전압·시간을 다시 환산한 값과 저장 배열이 정확히 일치했고 18개 plateau median도 재현됐습니다. 이 설정에서 실제 raw code 간격은 256, 수직 표본 간격은 **약 6.695 mV**입니다. WORD 전송이 16-bit 측정 분해능을 의미하지는 않습니다. 평균값과 표준편차도 CSV에 보존했습니다.

첫 점은 (0,0)이므로 edge가 없습니다. CH2 두 번째 점의 100 mV 상승으로 트리거하고 약 2 ms pretrigger를 포함해 첫 점도 취득했습니다. 한 번의 시간 정렬은 plateau 위치를 찾는 데만 사용했고, 전압 gain/offset 보정이나 점별 시간 fitting은 하지 않았습니다. 두 채널 preamble origin 차이는 **{result['channel_origin_difference_ps']:.3f} ps**이며 각 채널 원본 시간축을 유지했습니다. 이 차이의 원인을 특정하지 않았고 정밀 channel skew/지연 검증으로 주장하지 않습니다.

## 종료 상태와 검증 범위

선택 AWG generator 1·3의 명시적 zero 프로그램이 counter 1/1로 완료됐습니다. 실제 파형 끝의 0-code baseline은 DAC4 약 −27.615 mV, DAC5 약 −14.226 mV여서 물리 전압이 정확히 0이라고 주장하지 않습니다. 합산 RF generator 0·2는 시험 전에 gain=0 oneshot으로 idle 처리했습니다. 다른 generator는 대상으로 삼지 않았습니다. 오실로스코프 설정과 원래 STOP 상태를 복원하고 읽어 확인했습니다. DAC 전류는 변경하지 않았습니다.

이번 경로는 **실제 GUI 입력 → 생산 compiler → scope-only hardware execution**입니다. GUI Run worker / ADC / FIR-DDR / QCoDeS 저장 경로는 실행하지 않았습니다. 비항등 virtual matrix, fine RF duration, 정밀 시간·스큐, 교정된 아날로그 정확도 검증도 이번 범위에 포함하지 않았습니다. 생산 소스·사용자 JSON·펌웨어를 바꾸지 않았으며 보호된 Python source hash는 모두 일치합니다.

## 초기 오류와 재검사 구분

1. 최초 offline GUI 준비는 컴파일 후 Qt 종료 접근 위반이 발생했습니다. 원본 로그와 artifact는 보존했고 테스트 helper의 종료 처리만 수정한 `offline_prepared_retry1`은 exit0입니다. 생산 GUI는 수정하지 않았습니다.
2. Scope의 `RSTate?`, `OPERation:CONDition?`, `ADER?`는 이 펌웨어에서 미지원이었습니다. 지원되는 `OPERegister:CONDition?`·AER·TER로 확인했고 최초 오류를 보존했습니다. 첫 setup read는 newline 때문에 75 bytes로 잘렸으며 복원에 사용하지 않았습니다. 이후 167,580-byte 전체 payload와 SHA256를 확인했습니다.
3. `run_01`은 RPC tuple과 JSON list의 표현 차이를 설정 변경으로 오인해 **출력 전에 중단**됐습니다. 모든 필드를 동일 JSON 표현으로 비교하도록 검사기만 수정했습니다.
4. `run_02`는 실제 9점과 zero 정리를 완료했으나 채널 origin의 exact equality 검사에서 거부됐습니다. 원본 결과를 보존했습니다. 설정 복원 이후 회수한 데이터는 100 µs window로 잘린 recovery 자료이므로 12 ms 전체 취득의 PASS 증거로 쓰지 않았습니다.
5. source별 preamble origin은 서로 다를 수 있으므로 이번 전압 검사에서는 1 sample 미만 차이를 명시적으로 허용하고 실제 차이를 기록했습니다. points/increment/reference 검사는 유지했습니다. raw/preamble을 비교 전에 저장하도록 보완한 `run_03`이 최종 유효 취득입니다. **이 취득 성공이 절대 전압 PASS를 뜻하지는 않습니다.**

Scope 명령과 source별 preamble 정의는 [Keysight 6000 X-Series Programmer’s Guide](https://www.keysight.com/cf/en/assets/9018-07124/programming-guides/9018-07124.pdf)를 확인했습니다.
'''
(HERE/'REPORT.md').write_text(report,encoding='utf-8')
files={str(p.relative_to(HERE)).replace('\\','/'):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
       for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='archive_manifest.json'}
(HERE/'archive_manifest.json').write_text(json.dumps(dict(file_count=len(files),total_bytes=sum(x['bytes'] for x in files.values()),files=files),indent=2),encoding='utf-8')
print(json.dumps(dict(result=result,files=len(files),bytes=sum(x['bytes'] for x in files.values())),indent=2))
