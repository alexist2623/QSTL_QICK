# Quantum Circuit 구현 및 검증

2026-10-08 · GUI/QICK 저장소 브랜치: `awg_tuning_v3`

## 구현 결과

- 왼쪽 Quantum Circuit 탭에서 큐비트와 게이트를 추가·편집·삭제합니다.
- 오른쪽에는 AWG/RF/Acquisition 시간축과 큐비트 회로를 함께 표시합니다. 게이트를 우클릭하면 Edit/Delete, 더블클릭하면 편집창이 열립니다.
- AWG Absolute는 절대 전압, Relative는 해당 AWG의 직전 유지 전압에 더할 변화량입니다. Ramp와 초기 전압도 설정할 수 있습니다. 게이트 종료 뒤에도 최종 AWG 전압은 유지됩니다.
- RF는 채널, 시작 지연, 길이, 주파수, 위상, gain을 설정합니다. Readout 게이트에는 Acquisition을 함께 넣을 수 있습니다. DDR write 구간은 표시하지 않습니다.
- CNOT/CZ는 제어 큐비트를 선택할 수 있습니다. 일반 게이트는 선택한 큐비트에만 상자를 표시합니다.
- Shots, QICK Run/Stop, 실행 상태, 설정 JSON 저장/복원을 연결했습니다. 이전 설정 형식은 기존 탭 선택을 유지하여 읽고, 새 회로 필드는 버전 44에 저장합니다.

## 실행 경로

`MainWindow → QuantumCircuitWorker → quantum_circuit_execution → 기존 FineTuneSequence/QICK compiler → 기존 QCoDeS runner`

Run은 실제 연결에서 얻은 HWH 정보를 사용해 먼저 컴파일하고 시간·채널·전압 범위·명령 간격을 검사합니다. 실행에는 별도의 회로 문서만 사용하며, 기존 AWG 편집기의 파형·sweep·SquarePulse 설정을 끌어오지 않습니다. 연결, 데이터베이스, 입력 calibration과 compensation 옵션은 기존 설정을 사용합니다. 회로 문서와 실제 실행 설정은 QCoDeS에 함께 기록됩니다.

RF의 아날로그 감쇠기/filter 변경은 기존 Front Panel Update로 적용해야 합니다. 회로 Run은 이 기존 동작을 변경하지 않습니다.

현재 QSTL v3 구성의 RF 디지털 출력 지연 42클록은 이전 실제 RTL 검증 결과를 사용합니다. 새 bridge는 AWG v3/48비트/출력 16클록, RF v6/revision 6/16 samples per clock/tmux 0, 공통 300 MHz 등 일치하는 metadata를 확인한 뒤 RF 명령을 앞당깁니다. 다른 구성은 동일 지연으로 추정하지 않고 거부합니다. 이는 검증된 디지털 인터페이스의 시간 정합이며 RFDC·케이블·아날로그 전달 지연의 calibration은 아닙니다.

## 최종 검증

최종 결합 실행: **247 passed**, 86.33초, exit 0.

| 검사 | 통과 수 |
|---|---:|
| 회로 문서·전압 상태·시간축 계산 | 67 |
| 편집창·회로 표시·우클릭 동작 | 24 |
| 실제 MainWindow/Qt worker 연결 | 13 |
| 기존 QICK compiler와 실행 bridge | 32 |
| 기존 GUI/RF·Bias·종료·Acquisition 회귀 검사 | 111 |

- 절대/상대 전압과 두 AWG의 동시 Ramp, 여러 RF pulse를 실제 프로그램 컴파일 경로로 검사했습니다.
- 1 MSPS/50 kSPS FIR 설정에서 Acquisition 입력 시간, RF 명령 시간과 지연 보정 후 출력 시간, 공통 시작 offset을 검사했습니다.
- RC-only, DC 고정전압/고정시간 옵션 전달을 검사했습니다. 새 회로 기능 때문에 보상 알고리즘을 변경하지 않았습니다.
- 사전 컴파일과 실행 경로의 PMEM 일치, 기존 QCoDeS runner의 임시 SQLite 저장을 검사했습니다. 해당 검사에서는 하드웨어 acquisition 경계만 가짜 데이터로 대체했습니다.
- 실제 Qt 스레드의 완료·실패·취소와 중복 실행 차단을 검사했습니다.
- 단순 Edit→확인으로 300 MHz의 7클록 등 clock-grid 값이 반올림되지 않는지, q1/q3 게이트가 q2를 덮지 않는지 검사했습니다.
- 최종 화면과 게이트 편집창을 실제 Qt로 렌더링하고 열어 확인했습니다.

이번 작업에서 실제 장비 출력이나 새 Verilog 시뮬레이션·합성은 실행하지 않았습니다. 이전 hold-duration/RC 검증 결과와 이번 소프트웨어 검증을 구분합니다.

## 지원 범위

- 현재 실행 backend는 shot당 Acquisition **1개**를 지원합니다. 길이는 live FIR sample period의 정수배여야 합니다.
- AWG 동시 Ramp는 시작/끝이 같을 때 지원합니다. 서로 엇갈려 겹치는 Ramp, 다른 Ramp 도중의 SET, 공유 포트의 너무 짧은 명령 간격은 실행 전에 안내합니다.
- X/Y/CNOT 등의 이름은 사용자가 설정한 pulse의 이름입니다. 보정된 양자 게이트 라이브러리나 상태 시뮬레이터를 자동으로 적용하지 않습니다.
- 설정 없는 게이트는 실행하지 않습니다. 의도적인 대기는 Wait/Idle/Delay로 지정합니다.
- 그림의 반복 loop 및 sweep 편집기는 이번 범위에 포함하지 않았습니다. Shots는 전체 회로의 반복 횟수입니다.
- 화면은 요청 파형입니다. 기존 DAC 양자화, RC/DC 보상, FIR 샘플 경계 및 아날로그 전달 특성의 오차가 사라졌다는 의미가 아닙니다.

## 변경 보존 및 결과 파일

새 회로 모듈들과 MainWindow 연결부를 추가했습니다. 기존 `qick_fine_tune_sweep.py`, `qick_qcodes_experiment.py`, `dc_waveform_core.py`, `dc_waveform_widgets.py`는 이 작업 시작 시점과 SHA-256이 동일합니다. 기존 미커밋 변경을 보존했으며 commit/push하지 않았습니다.

- [최종 테스트 로그](C:/GIT_Workspace/QSTL_QICK/analysis_results/quantum_circuit_20261008/final_tests.log) · [JUnit XML](C:/GIT_Workspace/QSTL_QICK/analysis_results/quantum_circuit_20261008/final_tests.xml)
- [기존 핵심 파일 hash 비교](C:/GIT_Workspace/QSTL_QICK/analysis_results/quantum_circuit_20261008/core_preservation_check.json)
- [이번 MainWindow 변경 diff](C:/GIT_Workspace/QSTL_QICK/analysis_results/quantum_circuit_20261008/mainwindow_feature.diff)
- [실행 bridge 검증](C:/GIT_Workspace/QSTL_QICK/analysis_results/quantum_circuit_20261008/execution_bridge_verification.json)
- [사용 방법](C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI/QUANTUM_CIRCUIT.md)
- [전체 화면](C:/GIT_Workspace/QSTL_QICK/analysis_results/quantum_circuit_20261008/quantum_circuit_window.png) · [게이트 편집창](C:/GIT_Workspace/QSTL_QICK/analysis_results/quantum_circuit_20261008/gate_editor.png)

![Quantum Circuit 화면](C:/GIT_Workspace/QSTL_QICK/analysis_results/quantum_circuit_20261008/quantum_circuit_window.png)

![게이트 AWG 편집창](C:/GIT_Workspace/QSTL_QICK/analysis_results/quantum_circuit_20261008/gate_editor.png)
