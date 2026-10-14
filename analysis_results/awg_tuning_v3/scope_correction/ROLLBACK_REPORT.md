# 요청 범위 교정과 기존 회로 롤백

2026-10-07 10:52 PDT. 사용자의 최신 지시에 따라 새 pre-IIR DC 누적·보상 회로 안의 파이프라인 작업만 계속합니다. 기존 주요 회로는 임의 수정하지 않습니다.

## 복원한 변경

- `v3_awg_tuning_ctrl.sv`: SET/override/terminal RAMP의 직접 signed16 포화, RAMP 포화의 sign-extension 최적화, terminal lane mask의 앞 단계 이동을 모두 취소했습니다. `timing_failure_r2/src` 원본과 byte-identical입니다. 커밋된 v2 controller와는 v2_/v3_ 모듈 접두어만 다릅니다.
- `square_rc_precomp.sv`: 23비트 출력 양자화 최적화를 취소하고 기존 72비트 반올림 코드를 복원했습니다. 보존 원본과 byte-identical이며 Git diff가 없습니다.
- `generate_rtl.py`: Square 출력 함수 치환 및 render 리팩터링을 취소했습니다. 보존 원본과 byte-identical이며 Git diff가 없습니다.
- 롤백 전 파일은 `before_rollback`에 보존했습니다. 전체 증거는 `rollback_verification.json`입니다.

기존 v1/v2 AWG, SquarePulse, RF signal generator, DDR, FIR의 production 소스와 v3의 기존 IIR/AXI 사본도 비교했습니다. 후자는 v2_/v3_ 이름 외 내용이 같습니다. 총 53개 파일을 `legacy_logic_baseline.json`에 고정했고 `legacy_logic_guard.py`가 값의 변경을 거부합니다. 이 기준을 사용자 허가 없이 갱신해서 변경을 허용하지 않습니다.

## 유지한 요청 범위

새 `v3_awg_dc_area.sv`는 IIR 앞에서 실제 DAC samples의 면적을 48비트로 누적하고, 같은 위치에 DC 보상을 넣고, 마지막 zero edge 후 면적 및 IIR 상태 reset을 요청합니다. 기존 IIR 산술은 그대로입니다.

이 새 모듈 안에서만 adder tree, reciprocal 곱셈, captured area/absolute value, 다음 보상 word와 signed delta 등록을 분리했습니다. 5클록 raw pipeline과 17클록 DC 시작을 유지합니다. 기존 SET sweep의 정수 고정 증분/add/rewind는 바꾸지 않았습니다.

유지된 연결 변경은 v3 wrapper의 새 모듈/status/reset 연결, 라이브러리의 v3 IP 인식과 DC 명령, GUI의 v3 인식·DC 명령 생성·보상 완료 대기·추가 5클록 출력 지연 반영입니다. RF/DDR 기존 production RTL과 FIR/DDR 기본 8712클록 지연은 변경하지 않았습니다. 기존 DDR testbench의 독립실행 timeout을 통합 testbench에서는 그쪽 watchdog이 맡게 한 변경은 검증 코드에만 있습니다. GUI verifier의 Qt 정리 수정도 검증 도구에만 있습니다.

## 실행 상태와 검증 한계

범위를 벗어난 변경을 사용하던 a3full4 및 pipe4 GUI 시뮬레이션, 이전 긴 폭 비교는 사용자 중단 지시로 종료했습니다. 중단 결과를 PASS로 세지 않습니다. 실행 파일/로그는 보존했습니다. BIT/HWH/XSA는 교체하지 않았습니다.

사용자가 재검증·합성을 다시 지시하여 복원 소스로 새 검증을 시작했습니다:

- 단위 및 기존 출력 회귀: 세션41245, `F:/Vivado_Output/a3scope1_tb_*`, `a3scope1_legacy`.
- 실제 GUI→Verilog 4조건: 세션34194, `F:/Vivado_Output/a3sim1/v3_scoped1_batch/status.json`.
- 32/48/64 장시간 비교: 세션59707, `F:/Vivado_Output/a3width_scope1/status.json`.

완료 전 결과는 통과로 표시하지 않습니다. 복원 소스 단위5개와 기존 출력 검사는 모두 통과했습니다. 새 전체 합성은 `a3full5` 폴더, 세션93013, Vivado18512(10:53:13 시작)에서 진행 중입니다. 기존 회로에서 timing 위반이 나타나면 임의로 고치지 않고 사용자에게 보고합니다. 전체 timing closure는 아직 미해결입니다.

반복 예약 awg-v3는 PAUSED 상태를 유지합니다. 현재 직접 실행한 검증과 별개이며, 사용자 지시 없이 재활성화하지 않습니다. commit/push/컴퓨터 종료는 하지 않습니다.
