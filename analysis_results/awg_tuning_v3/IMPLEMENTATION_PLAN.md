# AWG v3: IIR 전단 면적 누적과 shot별 DC 보상

상태: 설계 및 구현 중. RTL/합성/bitstream 성공을 아직 의미하지 않는다.
최종 폭 선택: 200-shot RTL 비교에서 48/64-bit 결과가 모두 동일하여 사용자 요청대로 48-bit를 선택했다. 32-bit는 34회 overflow. 아래 초기 설계의 '선택 전' 기술보다 이 완료 결과가 우선한다. 48-bit는 4.8 GSPS full-scale 단일 부호 면적 약 3.579초를 표현하며 shot의 모든 prefix 범위를 검사한다.
사용자 요청일: 2026-10-06 (America/Vancouver).

## 기존 결정과 근거

- `../todo_resolution_20261004/LTSPICE_REPORT.md`: 실제 AWG 샘플의 면적을 **IIR 앞**에서 수집하고 DC 보상도 **IIR 앞**에 삽입한다. IIR 이후 ramp/offset 면적을 다시 합산하지 않는다.
- `SHORT_DC_FINDING.md`: 기존 tProcessor의 SET/SET 간격은 최소 3 clock이다. 1~2 clock DC 펄스가 늘어나던 문제는 IP 내부에서 종료해야 해결된다.
- `VOLTAGE_ERROR.md`, `FINAL_REPORT.md`: 고정시간 DC 전압의 정수 sweep 증분 오차가 남았다. 실제 샘플 면적을 직접 보상하면 이 DC 오차를 분리해 해결할 수 있다. 기존 SET voltage sweep 자체의 정수 증분 정책은 이번에도 별개이며 점별 Cartesian 반올림표로 바꾸지 않는다.
- 구형 `axis_awg_tuning_v2/README.md`와 9월 보고서의 nearest-DAC table 설명은 10월 4일 변경 이전 내용이다. 최신 결정과 실제 코드의 고정 증분/add/rewind 방식을 기준으로 한다.
- 현재 최신 배포 BD는 `projects/qstl_awg_v2`이다. 그 BD의 7개 AWG를 새 v3로 교체한 파생 프로젝트를 만들며 RF, SquarePulse, FIR IQ64, DDR, 핀과 300 MHz 제약을 유지한다.

## 구현 계약

1. 새로운 `axis_awg_tuning_v3`를 만들고 기존 v1/v2는 유지한다. RAMP signed32/Q18과 160-bit 명령 형식, DAC 16개 병렬 샘플을 유지한다.
2. 면적은 실제 IIR 입력의 14-bit 유효 DAC 코드(transport code / 4)를 정수로 합산한다. 사용자 추가 요청에 따라 **32/48/64-bit를 동일한 100점 sweep으로 비교한 뒤 최종 폭을 결정**한다. 샘플에 소수 면적 손실은 없다. 64-bit 시안은 약 65시간의 단일 부호 전 범위 누적 여유가 있으나 최종 선택은 아직 아니다. overflow는 상태 오류로 검출하고 wrap하지 않는다. 기존 IIR Q48/72-bit와 reciprocal Q64는 이 비교에서 공통으로 유지한다.
3. 고정전압 보상은 반대 부호 샘플로 잔여 면적을 줄인다. 마지막 word는 필요한 lane까지만 출력하고 마지막 scalar sample의 크기를 잔여 면적으로 맞춘다. 따라서 기존 3-clock SET 간격에 의존하지 않는다.
4. 고정시간 보상은 software가 `floor(2^64 / scalar_sample_count)`를 제공한다. FPGA는 파이프라인 곱셈과 나머지 보정으로 평균 DAC 코드를 구한다. 인접한 두 유효 DAC 코드에 정수 잔여 면적을 배분해 설정한 word 수 내에서 면적을 상쇄한다. FPGA `/` divider는 사용하지 않는다.
5. 처음과 끝이 0일 때 scalar sample 합계 0은 기존 IIR의 trapezoidal 합계 0과 같다. 마지막 보상 뒤 **0 word를 먼저 출력해 마지막 trapezoid 경계까지 반영한 다음** 면적 상태와 IIR 상태를 초기화한다. 파이프라인 안의 마지막 샘플을 reset으로 잘라내지 않는다.
6. 누적/보상 경로를 사용하지 않아도 동일한 bypass 지연을 둔다. 새 latency를 HWH/Python에서 노출하고 AWG 실제 출력 anchor, RF와 DDR trigger/readout 시각에 반영한다. FIR 자체의 기존 group delay를 중복 가산하지 않는다.
7. 고정전압 완료는 IP 내부에서 결정한다. tProcessor는 보상 시작 명령을 보내고 안전한 완료 시간까지 기다린다. 보상 완료 전에 다음 shot/reset이 진입하지 않도록 software 상한과 RTL 검사를 함께 둔다.
8. DC/RC 옵션은 독립적이다. GUI AWG Tuning과 Stability의 기존 옵션, FIR capture/DC 순서 선택을 유지한다. IIR 이후 clipping은 면적 상쇄만으로 해결되지 않으므로 기존 headroom 검사를 유지/갱신한다.

## 검증 및 배포 순서

- 독립적인 sample/area oracle로 100점 이상 voltage sweep, 양/음/0 교차, 짧은 보상, 두 DC 모드, 반복 초기화, 32-bit 이상 면적, overflow/status를 검사한다.
- 실제 tProcessor/TMUX/AWG v3/IIR 및 RF/DDR 경로에서 명령, 실제 출력 에지, capture timing을 검사한다. 명령 일치, DC 잔여 면적, RC 이후 오차와 기존 target 증분 오차를 분리한다.
- 모듈 타이밍 확인 후 최신 BD를 기반으로 전체 합성/배치배선한다. setup/hold/pulse width/bus skew를 확인하며 필요한 경우 파이프라인을 조정하고 latency 검증을 반복한다.
- 성공한 한 XSA에서 BIT/HWH를 함께 추출하고 RTL fingerprint와 HWH metadata를 확인한 후 배포한다. 이전 정상 펌웨어를 실패한 산출물로 덮어쓰지 않는다.
- GUI와 QICK은 이미 `awg_tuning_v3` 체크아웃이다. 기존 v3를 사용한다. 실제 보드/아날로그 측정을 한 것으로 보고하지 않는다.

## 폭 비교 중 확인한 통합 지점 (아직 소프트웨어에 반영하지 않음)

- `qick/qick_lib/qick/asm_v1.py`의 `AwgTuningGenManager`: v3도 signed32/Q18로 인식하고, 새 DC 명령의 reciprocal 64 bits를 `target/reserved_start` 두 32-bit word로 나눠 전달한다. 기존 tProcessor 산술 폭이나 SET sweep 증분 정책을 바꾸지 않는다.
- `qick/qick_lib/qick/awg_tuning.py`: v3 드라이버가 HWH의 면적 폭/기능 및 실제 측정한 output latency를 내보낸다. 현재 직접 명령 production RTL 시험에서는 raw AWG 뒤 16 clocks(면적 경로 5 + IIR 11)를 확인했다. 최종 파이프라인 변경 시 재검증한다.
- GUI `qick_fine_tune_sweep.py`의 `_build_sweep_register_plan`, `_emit_bias_t_compensation`: v3에서 이전 DC 면적 affine DMEM 값을 사용하지 않고 IP에 보상 시작 조건을 전달한다. v1/v2는 기존 동작을 유지한다.
- `_validate_bias_t_set_spacing`의 3-clock 제한은 legacy SET/SET DC에만 적용한다. v3의 내부 출력은 한 scalar sample의 보상도 처리할 수 있지만, tProcessor에서 보내는 일반 명령의 SET 간격 제한은 그대로다.
- `_emit_point`, `_emit_overlap_compensation_start`, `_emit_capture_end_max`: FIR capture와 DC의 순서 옵션을 유지하고, 보상과 capture 양쪽이 끝나기 전에 다음 shot이 시작되지 않도록 한다. 하드웨어 보상 완료 시각의 안전한 상한을 software가 예약해야 한다.
- `qick_rc_validation.py`: v3의 실제 sample 면적을 기준으로 DC 전압/시간 및 IIR headroom을 검사해야 한다. `_bias_t_fields`가 비어 있다는 이유로 DC 구간 검사가 빠지면 안 된다.
- `qstl_awg_v2/bd_2023-1.tcl`: 7개 AWG와 tProcessor/RF/readout은 `dac_clk_buf/BUFG_O`의 같은 300 MHz fabric clock net에 연결되어 있다. AXI host clock은 별도다. 기존 DDR trigger delay 8,712 clocks와 FIR group delay를 새 AWG latency로 대체하거나 중복 가산하지 않는다.
- 전체 GUI RTL harness는 이전 PC의 `C:/Xilinx` 및 생성된 sim library 경로를 사용하므로 현재 머신의 `F:/Xilinx/Vivado/2023.1`와 새로운 simulation build에 맞춰야 한다. 이전 실행 결과를 새 v3 결과로 재사용하지 않는다.

## 사용자 추가 요청: 그래프 보존

32/48/64-bit 각각의 shot별 잔여 면적, 그 signed 누적합, RC 출력 최대 오차와 종료 잔류 전압을 PNG와 원본 CSV로 보존한다. 진행 중 그림은 명시적으로 표시하고, 각 폭의 100점 × DC 2모드가 모두 끝나기 전에는 최종 비교로 보고하지 않는다. 결과 위치: `width_comparison/`.
