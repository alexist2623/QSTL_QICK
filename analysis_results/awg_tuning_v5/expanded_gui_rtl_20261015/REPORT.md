# 현재 v5 GUI → 실제 RTL 추가 검증 결과

검증 종료: 2026-10-15T09:54:46.606152-07:00. 새 실제 RTL 실행 37개, 352회, 최종 디지털 출력 샘플 43,980,672개 검사 PASS입니다.

원본 GUI가 거부한 조건과 명시적인 RF +100 ns 변형은 별도로 기록했습니다. 따라서 원본 45조건이 모두 RTL을 통과했다는 의미는 아닙니다. 사용자가 제외한 AWG/RF 정확한 동시 시작 문제는 수정하지 않았습니다.

| 요청 묶음 | 이번 새 실행 결과 |
|---|---|
| Virtual matrix × sweep 21조건 | 실제 RTL 21/21 PASS. 원본 1조건, 원본 공유 포트 거부 후 별도 RF +100 ns 변형 20조건. 96점 × 2회. |
| 별도 compiler 17조합 | 원본 전체를 실제 GUI/compiler로 확인. Calibration 정상 거부 6개, Quantum N=0 원본 RTL PASS 1개, CPMG/UDD 공유 포트 거부 8개는 별도 +100 ns 변형 RTL 8/8 PASS. Quantum N=1/3 두 조건은 v5 RF latency profile 미지원으로 실행 전 거부. |
| Composite 7조건 | 기존 원본 설정으로 실제 RTL 7/7 PASS. τ×π 6조건과 Hahn→Custom 1조건, 세 RF/AWG 쌍·두 반복·126 RF burst. |

## GUI 입력과 실제 RTL의 연결

실제 MainWindow/설정창 → Run Experiment의 생산 컴파일 경로 → 새 PMEM/DMEM → 실제 tProcessor/TMUX/AWG/DDS/IIR/axis_output_sum_v2/최종 출력 slice를 실행했습니다. 보드 I/O 경계만 로컬 컴파일로 대체했습니다. N/τ 및 Custom host parameter는 정상 software-coordinate 해석을 거치며, hardware sweep은 프로그램 안에서 실행됩니다.

Matrix는 비대칭 완전결합 3×3, 물리 출력 scale 800/400/800 mV와 독립 C@V·정수 증가량 oracle을 사용했습니다. 기존 SET 양자화 정책을 검증한 것이며 이상적 연속 전압 오차가 0이라는 뜻은 아닙니다. compiler17의 CPMG는 9점 HOLD×전압 grid이고 matrix21의 해당 N/τ는 2점 진폭 grid라 별도 실행했습니다.

저장된 GUI grid 96좌표, compiler 모델 목표값 288개, 별도의 실제 RTL SET payload 576개가 독립 기대값과 일치했습니다.

Matrix의 inherited analog_results/GUI_RC_RESULT는 일부 경로의 가상 RC 진단값입니다. 세 AWG의 아날로그 오차 통과 결과로 해석하지 않습니다. 이번 통과 기준은 세 AWG의 디지털 IIR 점화식·면적/reset 또는 bypass와 최종 DAC oracle이며, 기존 연속 RC 200회 검증은 별도 기록입니다.

+100 ns 변형은 외부 RF 시작 offset만 바꿨습니다. 내부 τ/π/phase, 생산 spacing guard, 원본 실패 기록은 유지했습니다. Quantum N=0은 RF가 없는 Quantum 경로이며 AWG Tuning virtual matrix를 상속하지 않습니다. Quantum N=1/3은 별도 Quantum RF latency 탐색이 v5를 인식하지 못하는 제한입니다.

## 보존 및 범위

기준 Python 소스(관련 검증 코드 포함) 169개와 검증 전 보호 파일 374개의 해시를 유지했습니다. 사용자가 이후 요청한 로컬 v5 BIT/HWH/XSA/manifest 네 신규 파일만 정확한 해시로 추가를 허용하여 최종 378개를 대조했습니다. 각 묶음의 새 RTL/입력/로그 증거도 재검사했습니다.

Compiler17의 RTL 실행은 모두 exit0이었지만 최초 controller는 최종 파일 감사에서 exit1로 종료했습니다. Vivado가 실행 후 생성한 런타임 파일 8개를 입력 변경으로 집계한 감사기 오류였습니다. 원본 실패를 보존하고 정확한 신규 출력 경로·해시를 별도 기록한 후처리 감사가 통과했습니다. 기존 입력과 compiled snapshot 해시는 동일하며 RTL을 다시 실행하거나 허용 오차를 바꾸지 않았습니다.

이번 검증에서 새 합성, 보드 접속·업로드·서버 재시작, 사용자 설정 변경, 생산 코드 변경은 없습니다. 기존 자동화는 PAUSED 상태입니다. 로컬 firmware package의 additional_validation=running은 복사 시점 기록이며, 이후 완료 증거는 이 보고서와 연결된 최종 결과입니다.

실물 아날로그 측정과 ADC/FIR 산술은 미수행입니다. AWG IIR 뒤 DDS 면적 및 clipping은 기존 AWG DC 면적 보상 범위 밖입니다.

## 결과 파일

- [전체 결과와 증거 SHA256](results.json)
- [Matrix 21 상세](matrix21/reporting/REPORT.md) · [실제 최종 출력 파형](matrix21/reporting/matrix_v5_actual_trace_v2.png)
- [Compiler 17 상세 및 거부 원인](compiler17/REPORT.md)
- [Composite 7 상세](composite7/REPORT.md) · [실제 RTL 파형](composite7/composite7_actual_v5_rtl.png)
- [검증 전 보존 감사](before.json) · [검증 후 보존 감사](after.json)
- [로컬 v5 패키지](../local_firmware_package_20261015/REPORT.md)
- [Show QICK Program / Run Experiment 코드 경로와 비교](../show_program_freeze_20261015/SHOW_RUN_PATHS.md)

Show 응답 없음은 현재 재현되지 않아 원인을 확정하거나 해결로 표시하지 않았습니다. awg_rf_test.json의 로컬 v4/v5 검증에서는 Show와 Run 직전 ASM/PMEM/DMEM/RF envelope가 일치했습니다.
