# TODO 검증 현황

실제 RTL 완료는 각 실행의 `result.json`과 명령 값·시각 비교 통과로 판단한다.
소프트웨어 명령 모델을 실제 RTL 완료로 대체하지 않는다.

| 경우 | 지점 × 반복 | 실제 RTL | 마지막 기록 clock / 전체 clock | 용량 MiB |
|---|---:|---|---:|---:|
| rc_precomp_repeat_reset_no_aux_grid_200x200_todo_increment_20261004_awg_v2 | 40000 × 2 | 통과 | 38240555 / 38242393 | 92.4 |
| rc_precomp_repeat_reset_no_aux_grid_200x200_todo_increment_20261004_awg_v2_stability | 40000 × 2 | 통과 | 41680555 / 41682393 | 55.0 |
| rc_precomp_repeat_reset_rf_duration_20x20_todo_fixed_time_20261004_awg_v2 | 400 × 2 | 통과 | 1328507 / 1325755 | 15.1 |
| rc_precomp_repeat_reset_rf_duration_20x20_todo_fixed_voltage_minset_20261004_awg_v2 | 400 × 2 | 통과 | 2810365 / 2807613 | 15.1 |
| rc_precomp_repeat_reset_rf_duration_fixed_20x20_todo_fixed_time_20261004_awg_v2 | 400 × 2 | 통과 | 1224547 / 1225755 | 15.0 |
| rc_precomp_repeat_reset_rf_duration_fixed_20x20_todo_fixed_voltage_minset_20261004_awg_v2 | 400 × 2 | 통과 | 1337187 / 1338395 | 15.0 |

## 검증 범위

- 두 DAC virtual gate: AWG Tuning 200×200×2 정방향, Stability 200×200×2 역방향 및 축 순서 반전.
- 행렬 `[[1, 0.23], [-0.17, 1]]`, DAC full-scale ±800/±400 mV. X 5→15 mV, Y −9→7 mV.
- RF duration × voltage: fixed/extend_by_rf_duration × DC fixed_time/fixed_voltage 네 조합. 각 20×20×2 actual RTL, 두 AWG+RF DDS+실제 tProcessor/TMUX/RC.
- 고정전압 보상 20 mV의 최초 두 RTL 실행은 1~2클록 보상이 3클록으로 늘어나는 실패를 검출했다. 해당 rev2 기록을 통과로 세지 않는다. 현재 소프트웨어는 이런 조건을 실행 전에 거부한다.
- 지원 범위 RTL 재검증은 fixed_voltage에서 extend=0.5 mV, fixed=2 mV의 별도 조건이다. 사용자 설정을 자동 변경한 것이 아니다. 자세한 실패 및 검출 근거는 SHORT_DC_FINDING.md 참조.
- RF 200×200의 양방향·축 순서·두 DC 모드는 별도 소프트웨어 검사다. RF 전체 200×200 RTL이라고 부르지 않는다.
- 대규모 grid에는 매 clock raw AWG 및 RC 정수 연산 검사가 있다. analog RC 통과 오차와 SET 명령의 이상 목표 전압 오차는 별개다.
- 실제 ADC/RFDC, ARM, 보드에서의 아날로그 측정을 포함하지 않는다. RF DDS의 디지털 파형을 검사한다.
- 이전 FIR/DC 실행 순서 기능은 기존 8종 실제 RTL 증거와 이번 소프트웨어 회귀 검사로 확인한다.
- 추가 면적 누적 IP와 bitstream 변경은 하지 않았다. LTspice 비교는 별도 보고서 참조.

## 소프트웨어 프로세스 종료 코드

- `test_awg_tuning_v2`: exit=0, 13 passed in 11.06s
- `test_gui_shutdown`: exit=0, 3 passed in 4.58s
- `test_qick_fine_tune_sweep`: exit=0, 54 passed in 1.40s
- `test_rf_duration_oneshot`: exit=0, 16 passed in 0.26s
- `test_stability_diagram`: exit=0, 23 passed in 1.40s
- `test_rc_precompensation`: exit=0, 13 passed in 3.02s
- `test_dc_readout_timing`: exit=0, 53 passed in 1.37s
- `test_dc_waveform_gui_rf`: exit=0, 78 passed, 1 warning in 36.42s
- `test_qick_qcodes_experiment`: exit=0, 33 passed in 2.27s
- `test_qick_output_triggers`: exit=0, 18 passed in 0.19s
- `test_bias_t_set_spacing`: exit=0, 10 passed in 0.38s
- `test_incremental_virtual_grid`: exit=0, 66 passed in 11.57s
- `test_rc_sweep_matrix`: exit=0, 33 passed in 5.25s

## 남는 정수 증분 오차

사용자의 2026-10-04 요청에 따라 점별 nearest-DAC 전압표를 제거하고 기존 고정 증분/add/rewind 방식을 유지했다.
32-bit Q18 확장은 RAMP step에만 적용되며 SET의 DAC 코드 간격은 바뀌지 않는다.
따라서 명령 값·시각 RTL 검사 통과를 이상적인 요청 전압과 정확히 일치한다는 뜻으로 해석하면 안 된다.
상세 수치는 `increment_errors.json`, 파형 비교는 `virtual_grid_fixed_time.png` 및 `LTSPICE_REPORT.md`에 있다.
특히 fixed_time DC 전압 증분도 누적 양자화 오차를 가지며, 기존 방식에서는 정확한 면적 상쇄를 일반적으로 보장하지 않는다.
증분 누적 결과가 DAC/보상 레지스터 범위를 넘으면 RC 옵션과 무관하게 실행 전에 오류를 낸다.
