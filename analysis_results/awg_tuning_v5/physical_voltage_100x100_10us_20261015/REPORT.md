# 100×100 전압 sweep · 10 µs HOLD 실물 결과

**10,000점 출력·취득은 완료됐고 시간/기록 무결성은 PASS입니다. 고정 offset 제거 후 요청 전압 대비 오차 <5% 판정은 전체 PASS가 아닙니다.**

DAC4→scope CH1, DAC5→CH2에서 각각 0–400 mV 100점, 두 번째 축을 빠르게 변화시켰습니다. 각 점은 기존 형태인 10 µs zero → 1 µs RAMP → **10 µs HOLD** → 1 µs RAMP → 10 µs zero입니다. 명령 간 처리를 포함한 점 간격은 32.1766667 µs이고 마지막 zero 시각은 시작 기준 약 321.760587 ms입니다.

실제 MainWindow의 sweep 입력을 생산 컴파일러로 컴파일했고, 그 PMEM/DMEM과 동일한 프로그램을 실제 보드에서 실행했습니다. 하드웨어 counter가 10,000/10,000까지 도달했습니다. Identity matrix를 사용한 scope-only 경로이며 GUI RunWorker·ADC/FIR·DDR·QCoDeS 검증을 주장하지 않습니다. 프로그램은 PMEM 152 words, DMEM 0 words입니다.

## 5% 판정

두 채널의 비영점 HOLD **19,800개 중 17,061 PASS / 2,739 FAIL**입니다. 점 단위로는 **7,460 PASS / 2,539 FAIL / 1 N/A**입니다. 두 비영점 축 중 하나라도 실패하면 그 점은 FAIL입니다. (0,0)점은 백분율 분모가 0이므로 N/A입니다.

| 출력 | 비영점 PASS | FAIL | 실패한 요청 전압 범위 | 400 mV 요청 |
|---|---:|---:|---:|---|
| DAC4 / CH1 | 8,487 | 1,413 | 4.04–117.17 mV | 100/100 PASS |
| DAC5 / CH2 | 8,574 | 1,326 | 4.04–113.13 mV | 100/100 PASS |

각 채널의 0 mV HOLD 100개에서 중앙 5 µs, 총 2,500개 sample의 median 하나를 구했습니다. 고정 offset은 DAC4 **−24.26771712 mV**, DAC5 **−14.22587904 mV**이며 모든 점에서 동일하게 뺐습니다. Gain fit이나 점별 offset은 적용하지 않았습니다. 200개 0 mV 축 측정은 baseline으로 보존하고 백분율 판정에서 제외했습니다.

요청 전압 간격은 4.040404 mV이나 정수 코드의 일정 증가량은 164 codes = 4.01131348 mV입니다. 따라서 실제 마지막 명령 전압은 **397.12003418 mV**입니다. 판정 기준은 요청한 400 mV를 유지했습니다. 400 mV 요청의 실측 보정값 범위는 DAC4 **391.632–394.979 mV**, DAC5 **388.284–391.632 mV**였습니다.

이번 오실로스코프의 실제 수직 표본 간격은 **3.34727936 mV**입니다. 첫 비영점 4.0404 mV의 5% 허용폭은 약 **0.2020 mV**여서 낮은 전압의 상대오차는 표본 간격·잡음에 민감합니다. 해당 실패를 삭제하거나 기준을 완화하지 않았으며, 이 측정만으로 오차의 원인을 단정하지 않습니다.

## 파형과 원시 데이터

한 번의 SINGLE 취득에서 두 채널 각각 **2,000,000 samples**, **200 ns 간격**, 총 **0.4초**를 기록했습니다. 누락·clipping은 모두 0입니다. 중앙 5 µs 판정 구간마다 25 samples가 있습니다. 100개 행 끝의 파형과 명령 시각 차이는 단일 시간 정렬 후 최대 **0.204951 µs**였습니다. 점별 시간 이동이나 clock fit은 적용하지 않았고, 정밀 timing/skew 교정 검증과는 구별합니다.

모든 원시 sample code는 preamble·취득 설정·SHA256과 함께 한 벌만 무손실 압축했습니다. 원시 code 총 **8,000,000 bytes (8 MB)**가 gzip **1,718,127 bytes (1.72 MB)**입니다. 압축 해제 후 원본 바이트/코드 일치를 검증했습니다. 재생성 가능한 전체 time/voltage 배열을 별도로 중복 저장하지 않았습니다.

- [전체 측정 파형](analysis_run_01/full_record_overview.png)
- [10 µs HOLD 펄스 확대](pulse_detail.png)
- [첫 행 확대](analysis_run_01/first_row_zoom.png) · [마지막 행 확대](analysis_run_01/last_row_zoom.png)
- [전점 오차·실패 지도](analysis_run_01/error_and_failure_maps.png)
- [20,000개 채널 측정 CSV](analysis_run_01/all_20000_plateaus.csv) · [10,000점 판정 CSV](analysis_run_01/all_10000_point_verdicts.csv)
- [상세 분석 보고서](analysis_run_01/REPORT.md) · [독립 검산](independent_audit.json)
- [실행 상태](run_01/status.json) · [실제 어셈블리](offline_prepared/sweep.asm)

실행 후 선택된 AWG를 0 V 명령으로 복귀했고 마지막 baseline residual median은 offset 제거 후 두 채널 모두 0 mV였습니다. Scope 설정 및 원래 STOP 상태, DAC current를 확인했습니다. 생산 소스 170개와 기존 성공·실패 증거 해시는 그대로입니다. 펌웨어 교체나 서버 재시작은 하지 않았습니다.

기존 3×3 데이터도 새 5% 기준으로 별도 재판정하여 비영점 **12/12 PASS**를 확인했습니다. [기존 3×3의 5% 보고서](../physical_voltage_2axis_20261015/offset_5pct_review/REPORT.md). 이전 2% 판정은 보존했습니다.
