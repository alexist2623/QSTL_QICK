# 고해상도 10 ns 하강 RAMP의 시간 정렬 독립 검토

대상은 `falling_dac5_duration10ns_positive` 한 조건입니다. 보존된 실제 GUI 입력, PMEM/DMEM 감사, command model, scope 원시 IEEE block 및 기존 분석 결과만 읽었습니다. 장비 실행, 소스 수정, 기존 결과 변경, 추가 시간·진폭 fitting은 하지 않았습니다. `highres_ramps.png`도 직접 열어 확인했습니다.

**현재 근거만으로 큰 model residual을 RTL 진폭 결함 또는 RTL 지연 오류로 확정할 수 없습니다.** 실제 하강 threshold는 기존 전역 정렬의 모델보다 약 41 ns 앞에 있지만, 정렬 기준으로 쓴 첫 1 µs 상승 edge의 원시 threshold 후보가 54.335 ns에 걸쳐 있습니다. 명령과 모델의 시작 지연 계산에는 이번 검토에서 모순을 찾지 못했습니다. 원래 FAIL과 수치는 그대로 유지합니다.

## 명령 및 모델 시간의 일관성

실제 AWG3 하강 RAMP는 command cycle 7490, scalar sample 48, signed step −91,203,801, target 0입니다. 이전 HOLD SET은 cycle 4497, 다음 SET 0은 cycle 7501입니다. native output latency 31 cycle과 RAMP startup 7 cycle을 적용하면 다음과 같습니다.

| 항목 | 프로그램 시각 |
|---|---:|
| HOLD 시작 | 15.093333333 µs |
| 하강 RAMP 시작 | 25.093333333 µs |
| 하강 RAMP 종료 | 25.103333333 µs |
| 다음 SET 출력 | 25.106666667 µs |

RAMP와 다음 SET의 명령 간격 11 cycle은 startup 7 + RAMP 길이 3 + guard 1과 일치합니다. 다음 SET이 RAMP 완료 전에 잘라 버린다는 근거는 없습니다. 48 scalar sample / 4800 MHz = 요청한 전체 길이 10 ns이며, transport target 16352는 399.9573046875 mV입니다.

생산 compiler의 `qick_fine_tune_sweep.py:5883–5898`은 RAMP 명령을 startup만큼 앞당기며, `:5903–5907`은 startup·실제 길이·guard를 합친 점유 간격을 검사합니다. 분석기의 `analyze_highres.py:111–122` 및 `model_review/command_expectation.py:59–103`은 **이미 앞당겨진 실제 명령 시각**에 31 + 7 cycle을 적용합니다. 이 두 처리는 이중 지연 가산이 아닙니다. 실제 v3 제어 RTL `v3_awg_tuning_ctrl.sv:656–668`은 RAMP 명령의 target/step/duration을 받고, `:682–696`은 등록된 파이프라인 결과가 유효할 때 출력하며 마지막 word에서 target을 유지합니다.

## 첫 edge 정렬과 실제 하강 폭의 구분

기존 분석기는 `analyze_highres.py:288–294`에서 첫 상승의 200 mV crossing 후보 중 scope 시각 0에 가장 가까운 하나를 선택해 모든 구간에 동일한 offset을 적용합니다. 이 capture의 native 간격은 0.1 ns이지만, 첫 1 µs 상승의 원시 전압 양자화·변동으로 후보가 여러 개 생겼습니다.

| 기존 정렬의 관측값 | 값 |
|---|---:|
| 첫 상승 crossing 후보 수 | 75 |
| 후보 범위, scope 기준 | −66.806250 .. −12.470833 ns |
| 후보 범위 폭 | 54.335417 ns |
| 기존에 선택된 후보 | −12.470833 ns |
| 기존 전역 offset | −14596.637500 ns |

**전역 offset은 바꾸지 않았습니다.** 아래 하강 폭은 시간 원점을 공통 이동해도 변하지 않는 별도 진단입니다. 모델의 RC 하강 양끝에서 얻은 10–90% threshold 570.027212 / 250.139638 mV를 사용했습니다. 앞선 HOLD의 noise crossing을 제외하기 위해 유일한 400 mV 하강 crossing 전후 15 ns 안에서 위 threshold는 앞, 아래 threshold는 뒤에 있는 후보만 기록했습니다. 이 선택으로 원래 모델과 파형을 재정렬하거나 판정을 다시 계산하지 않았습니다.

| 하강 진단 | 값 |
|---|---:|
| 실제 상단 threshold, 기존 모델 시작 대비 | −39.910614 또는 −39.610614 ns |
| 실제 하단 threshold, 기존 모델 시작 대비 | −32.532294 ns |
| 원시 10–90% 폭 후보 | **7.078320 .. 7.378320 ns** |
| 이산 모델의 10–90% 폭 | 7.916667 ns |
| 기존 모델 threshold 대비 하단 crossing 차이 | −41.490627 ns |

10–90% 폭은 요청한 전체 RAMP 길이 10 ns와 같은 정의가 아닙니다. 원시 폭에는 아날로그 전달 특성·noise·수직 양자화 및 threshold 정의의 영향이 남으므로 정밀 시간 PASS를 부여하지 않았습니다.

첫 edge의 보존된 후보 전체를 **불확실성 범위로만** 보면 하단 threshold의 시간 차이는 −41.491 .. +12.845 ns를 포함합니다. 약 41 ns 차이는 이 54.335 ns 범위 안에 있습니다. 새 후보를 선택한 결과가 아니며, 후보 중 하나를 골라 PASS로 전환하지 않았습니다. 따라서 이번 자료만으로 RTL 지연과 전역 정렬/아날로그 전달/원시 변동의 영향을 분리할 수 없습니다.

## 원래 실패와 남는 실제 파형 특징

이 조건의 기존 10 ns 모델 창에서 median residual은 −191.601559 mV, 최대 절대 residual은 389.092637 mV입니다. 이는 고정된 전역 정렬 아래의 **시각별 모델 차이**이며 순수한 정상상태 gain 오차를 뜻하지 않습니다. 전체 24조건의 최대 399.051 mV라는 집계값도 같은 의미로 해석해야 합니다. 이번 한 조건의 검토를 다른 조건 전체의 원인 설명으로 확대하지 않습니다.

정렬과 별개로 실제 원시 하강 후 undershoot와 회복이 관측됩니다. 하강 직전 5 ns median은 약 595.816 mV, 이후 최소 개별 sample은 113.808 mV, 인접 5 ns median은 127.197 mV이며, 뒤에서는 약 200.837 mV plateau로 회복합니다. 이 파형 특징은 공통 시간 원점을 바꿔도 없어지지 않습니다. 원인은 이번 검토에서 확정하지 않았습니다.

## 보존 및 한계

`raw_review.json`은 입력 15파일의 해시, 원시 decode, 전체 threshold 후보 및 5 ns 구간 통계를 보존합니다. `diagnostic_summary.json`은 위 진단 범위와 원래 판정 불변을 기록합니다. 원시 gzip payload와 입력 해시를 대조했고 기존 증거의 변경은 없었습니다. 제조사 시간/전압 교정이나 analog bandwidth 보정을 추가하지 않았으며, 새로운 물리 측정도 수행하지 않았습니다.

이 리뷰는 기존 FAIL을 유지하면서 해석의 한계를 구분하기 위한 추가 증거입니다. 생산 코드·분석 기준·기존 source 및 결과는 동결 상태입니다.
