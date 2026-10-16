# 파형 질문 및 grouped sweep 구현 상태 확인

이번 결과는 기존 원시 파형 재분석과 작은 오프라인 기능 확인입니다. **새 grouped 100×100 실물 시험은 실행하지 않았습니다.** 이 폴더 이름은 요청한 시험을 식별하며, 시험 완료를 의미하지 않습니다.

## TODO 구현 상태

사용자가 제공한 TODO 원문과 당시 [기본 시험 범위](../simple_cases_20261015/PLAN.md), [결과](../simple_cases_20261015/REPORT.md)를 다시 대조했습니다. 당시 실행 범위는 “명시된 간단한 케이스들만 테스트”였고, 아래 두 신규 기능은 구현하지 않았습니다. 이후 실물 시험 결과 역시 이 기능들의 구현이나 검증을 대신하지 않습니다.

| TODO 항목 | 현재 상태 |
|---|---|
| Fine RF duration의 per-point 6-word DMEM 표를 tProcessor register arithmetic으로 대체 | 미구현. `qick_rf_fine_duration.py:218–226`에 `fine_row=True, row_width=6` 경로가 남아 있습니다. |
| GUI sweep parameter grouping, shared count, 그룹 해제/삭제/재추가, compiler/data 연동 | 미구현. 여러 독립 축을 하나의 index로 묶는 schema/UI/compiler 경로가 없습니다. |
| 기본 GUI→실행 모델 및 대표 RTL 시험 | 기존 별도 보고서에 실제 수행 범위와 실패/미지원 항목이 기록돼 있습니다. TODO 전체 완료가 아닙니다. |
| 전체 자동 GUI→실물 검증 suite | 부분 수행. 기존 물리 캠페인은 개별 보고서 범위만 증명하며 grouping 등 미지원 항목은 남아 있습니다. |

## 요청한 두 그림

1. 고정전압 DC 300 mV / RC τ10 µs의 Point5050은 양 채널 요청이 +3.030303 mV입니다. 고정 진폭의 반대 부호 펄스로 작은 양의 면적을 상쇄하므로 약 −300 mV의 짧은 DC 보상이 실제 명령됩니다. 정수 모델의 전체 보상 구간은 123.333 ns입니다. 기존 500 ns 표본 시각에서만 모델을 그려 주황색 선이 이 구간을 놓쳤습니다. 원시 sample 하나로 아날로그 폭·면적·타이밍을 확정할 수 없어 기존 INCOMPLETE 판정을 유지합니다.
2. 고정시간 DC 30 µs / RC τ20 µs의 Point9999 그림 왼쪽 −100 mV는 직전 Point9998의 DC 보상 꼬리입니다. Point9998은 DAC4/CH1 +300 mV, DAC5/CH2 +293.939394 mV를 요청했고, Point9999는 양쪽 +300 mV입니다. 기존 그림 시작 시각이 이전 DC 종료보다 약 0.91 µs 앞입니다. 현재 점은 SET 0부터 시작합니다. 전체 조건 실행 순서에서도 이 run 직전은 DC 20 µs / RC τ20 µs 조건입니다.

[명령·원시 sample·연속 파형 상세](review_previous_waveforms/REPORT.md)

- [Point5050 짧은 DC 펄스 확대](review_previous_waveforms/fixed_voltage_tau10_continuous_review.png)
- [Point9998→9999 연속 파형](review_previous_waveforms/fixed_time30_tau20_continuous_review.png)

두 새 그림을 실제 열어 확인했습니다. 원본 파형·기존 정렬·offset·판정은 변경하지 않았습니다.

## 10 ns RAMP와 50 ns 기억

현재 `dc_waveform_core.py:25`의 50 ns는 새 RAMP 삽입 기본값이며 전역 하한이 아닙니다. 현재 GUI 입력과 compiler는 10 ns를 허용합니다. 300 MHz fabric에서 10 ns는 3 clocks / 48 scalar samples이고, 요청한 10 ns→1 µs 100점은 3,6,…300 clocks입니다. 기존 [RAMP 실물 캠페인](../physical_ramp_voltage_100x100_20261015/REPORT.md)에서도 10 ns를 실제 실행했습니다.

RAMP 시작 7 clocks와 guard 1 clock, shared-port 명령 간격, step register 범위는 경사 길이와 별도 제약입니다. 이전 50 ns 실패의 정확한 입력/오류는 확인되지 않아 그 원인이 해결됐다고 단정하지 않습니다. 기존 고해상도 결과에는 transient와 시간 정렬 불확실성도 남아 있으므로 입력 허용을 아날로그 정밀도 PASS와 혼동하지 않습니다.

## 요청한 grouped 100×100 시험의 현재 제한

같은 RAMP segment의 시간은 두 AWG가 공유하지만, rising segment와 falling segment는 각각 독립 축입니다. HOLD 전압도 `(segment, output)`마다 독립 축입니다. 따라서 현재 방식으로 상승·하강·두 출력 전압을 각각 100점 설정하면 `100×100×100×100 = 100,000,000`점입니다. 요청한 두 그룹의 10,000점이 아닙니다.

생산 모델에 각 축 2점만 입력한 [작은 오프라인 probe](grouping_capability_review/results.json)는 shape `[2,2,2,2]`, 16점과 서로 다른 상승/하강 및 출력 전압 조합을 확인했습니다. 원하는 그룹 동작이면 shape `[2,2]`, 4점이어야 합니다. Qt·보드·컴파일·tProcessor/RTL·100M grid는 실행하지 않았고, 검사한 소스 및 사용자 JSON 7개 전후 해시는 동일합니다.

따라서 **AWG1/AWG2의 rising/falling 공동 duration 축 × 두 HOLD 공동 voltage 축의 실물 시험은 미실행/미지원**입니다. 이전 독립 축 시험을 이 시험의 PASS로 표시하지 않습니다.
