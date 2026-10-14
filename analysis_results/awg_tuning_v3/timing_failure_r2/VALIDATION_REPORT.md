# AWG Tuning v3 — IIR 전단 면적 누적과 shot별 DC 보상

상태(2026-10-07 05:24 PDT): 첫 전체 배치·배선의 setup WNS -0.553749 ns를
확인하고 보상 word/delta를 미리 준비하는 파이프라인을 추가했습니다.
**수정 후 실제 GUI→tProcessor/TMUX/AWG/RF/DDR 네 조건과 단위 RTL이 모두
통과했습니다.** 일반 출력 16 clocks, DC 시작 17 clocks, RF/DDR 시각도 유지됩니다.
수정 RTL로 IP 등록 콜백 수정 후 전체 FPGA 빌드(`F:/Vivado_Output/a3full3`)를 진행 중이며,
새 BIT/HWH는 아직 배포하지 않았습니다. 긴 32/48/64비트 RC 비교도 수정 후
재검증을 완료했고, 모든 수치가 수정 전과 동일합니다. 아래 기능 수치와 그림은
현재 RTL 기준입니다. 이전 증거는 `timing_failure_r1`에 보존합니다.

두 저장소는 `C:/GIT_Workspace/QSTL_QICK`, `C:/GIT_Workspace/PulseGenerator`이며
현재 브랜치는 모두 `awg_tuning_v3`입니다.

## 구현

`axis_awg_tuning_v3`는 실제 SET/RAMP의 유효 14비트 DAC 샘플 16개를 매 fabric
clock마다 합산합니다. 누적 위치와 DC 보상 삽입 위치는 모두 RC IIR 앞입니다.
RC 보정으로 만들어진 DAC ramp/offset 면적을 다시 DC 보상에 더하지 않습니다.

- **고정전압:** 반대 부호의 보상 샘플을 출력합니다. 마지막에 필요한 경우 한
  scalar sample의 크기만 줄이고, 남은 lane은 0으로 채웁니다.
- **고정시간:** 지정된 fabric clock 수 안에서 인접한 두 DAC 코드로 정수
  면적을 정확히 배분합니다. Python이 Q64 reciprocal을 전달하고 FPGA는
  파이프라인 곱셈과 나머지 보정을 사용합니다. RTL divider는 없습니다.
- 보상 마지막에 0을 IIR에 통과시켜 마지막 적분 경계를 처리한 뒤 면적과
  IIR 상태를 초기화합니다. 물리적인 RC 커패시터가 강제로 초기화되지는 않습니다.
- 일반 출력과 bypass 지연은 모두 16 fabric clocks입니다. DC 시작은 명령
  이후 IIR 입력에서 17 clocks, DAC 출력에서 28 clocks입니다.
- 새 AWG 지연 5 clocks는 GUI의 segment/RF/DDR 기준 시각에도 반영했습니다.
  기존 FIR/DDR 8,712-clock 지연을 대체하거나 중복 가산하지 않았습니다.

기존 DC 보상의 1~2-clock SET 펄스 문제는 IP 내부의 샘플 출력으로 해결합니다.
일반 tProcessor SET 명령 사이의 최소 간격을 줄인 것은 아닙니다.

## 32 / 48 / 64비트 비교

동일한 100점 voltage sweep을 고정전압·고정시간으로 실행하여 폭마다 총
200 shots를 실제 RTL 및 독립 RC 회로 수치 모델로 비교했습니다.

| 누적기 폭 | Overflow | 완료 shots | 보상 후 디지털 잔여 면적 |
|---|---:|---:|---|
| 32 | 34 | 166 | overflow한 조건은 보상 실패로 분류 |
| 48 | 0 | 200 | 모든 shot에서 0 |
| 64 | 0 | 200 | 모든 shot에서 0 |

48/64비트는 모든 수치 결과가 동일했습니다. 따라서 요청하신 대로 48비트를
선택했습니다. 두 경우 RC 모델 최대 오차는 0.054616819 mV, shot 종료 후
잔류 전압 최대값은 0.000863351 mV(약 0.863 µV)였습니다. 해당 조건의 유효
DAC 1 LSB는 0.09765625 mV입니다. RC의 아날로그 상태는 shot 사이에 유지했습니다.

48비트는 4.8 GSPS에서 full-scale 단일 부호 면적 약 3.579초를 저장할 수
있습니다. 무제한 누적기가 아니며, 소프트웨어 사전 범위 검사와 RTL overflow
fault가 있습니다. IIR의 Q48/72비트 상태와 Q64 reciprocal은 면적 누적기 폭과
다른 항목입니다.

![비트 폭별 누적 오차](width_comparison/accumulated_error_by_width.png)

[원본 수치와 상세 비교](width_comparison/WIDTH_COMPARISON.md)

## GUI → 실제 RTL

검증 경로는 실제 GUI MainWindow 설정 → Run Experiment 프로그램 생성 →
PMEM/DMEM → 실제 tProcessor/TMUX/AWG/RF DDS/DDR capture RTL입니다.
두 DC 모드의 GUI 결과를 변경 없이 사용하는 조건, 축 순서를 반전한 추가
compiler 조건, Stability builder의 10×10 grid를 분리하여 기록합니다.

각 조건은 100지점 × 2회 반복이며 두 DAC의 실제 전 샘플 면적과 IIR 정수
연산을 검사합니다. 큰 파형 파일은 첫 12,000 clocks만 저장하지만 모니터는
전체 실행을 검사합니다. [시스템 보고서](system_validation/REPORT.md)의
`complete=true`이며 네 조건 모두 통과했습니다. 모든 조건에서 각 DAC의
보상/초기화 200회, 잔여 면적 0, 명령 값·시각 불일치 0을 확인했습니다.
세 RF 포함 조건마다 RF 200개/폭 오차 0, DDR trigger 200개/샘플 800개/
AXI write 400개가 일치했습니다.

DDR은 실제 capture IP에 FIR cadence의 timestamp stream을 넣어 지연·개수·
AXI 기록을 검증합니다. ADC 아날로그 측정 또는 FIR 산술의 정확도까지 검증한
것은 아닙니다. 실제 보드 출력 측정은 이번 작업에서 수행하지 않았습니다.

## 소프트웨어와 남는 오차

GUI의 DC 체크박스는 HWH의 `dc_area_version=1`을 인식하면 새 하드웨어
경로를 선택합니다. AWG Tuning과 Stability가 같은 구현을 사용하며 DC/RC
옵션 및 readout/DC 순서 선택을 유지합니다. 보상 완료와 readout 완료를 모두
기다린 뒤 다음 shot으로 진행합니다.

사용자 요청대로 기존 SET voltage sweep의 정수 고정 증분/add/rewind를
유지했습니다. **보상 잔여 면적 0은 실제 실행된 샘플을 기준으로 한 결과이며,
이상적인 목표 전압과 정수 sweep 값의 차이가 0이라는 뜻은 아닙니다.**
점별 Cartesian nearest-DAC 표를 만들지 않았습니다.

긴 ramp가 DAC rail에서 포화되는 경우에도 소프트웨어 면적 예측은 실제
포화된 샘플을 합산합니다. [최종 소프트웨어 재검사](SOFTWARE_RECHECK.md)에
34개 QICK 검사 및 89개 GUI DC/RC/readout 검사와 RTL 입력 일치 근거를 남겼습니다.

## FPGA 배포 조건

새 전체 프로젝트는 `qick/firmware/projects/qstl_awg_v3`입니다. 기존 최신 v2
BD의 AWG 7개를 교체했고 AWG/tProcessor/RF/FIR/DDR source의 공통 300 MHz
클록, RFDC 4.8 GSPS, 기존 FIR/DDR 구성은 유지합니다.

합성 추정치만으로 통과 여부를 정하지 않습니다. 전체 배치·배선 후 setup,
hold, pulse width, bus skew와 clock 누락을 확인합니다. 통과 시 같은 XSA에서
BIT/HWH를 추출하고 생성된 RTL, HWH 파라미터, 클록 연결 및 검증 증거를
확인한 뒤 위 프로젝트 폴더에 배포합니다. 현재는 이 단계가 진행 중입니다.
