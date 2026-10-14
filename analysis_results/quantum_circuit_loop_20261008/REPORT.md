# Quantum Circuit Loop 및 n sweep 검증

2026-10-08, GUI 브랜치 `awg_tuning_v3`.

## 구현

- 왼쪽 Quantum Circuit 패널에서 게이트를 선택하고 Add Loop로 반복 구간과 횟수 n을 지정합니다. 오른쪽에는 반복된 회로와 AWG/RF/Acquisition 시간을 함께 표시합니다.
- Loop 편집 창에서 Sweep n을 켜고 정수 Start/Stop/Step을 지정하면 각 n을 순서대로 실행합니다. Preview n은 미리보기만 선택하며 Run은 전체 sweep을 실행합니다. Shots는 각 n에 적용됩니다.
- n=0은 구간을 생략합니다. 반복 뒤 게이트와 Acquisition은 변경된 길이에 맞춰 이동합니다. 상대 AWG 변화는 반복 간 이어지고 절대값 설정은 반복마다 해당 값으로 설정됩니다.
- 모든 n의 프로그램을 먼저 컴파일해 검증한 뒤 측정을 시작합니다. 각 n은 별도의 QCoDeS Run으로 저장하며 데이터베이스 옆 JSON 인덱스에 n과 Run ID를 기록합니다. 취소나 실패 시 앞서 저장한 결과와 인덱스를 보존합니다.
- 게이트 또는 Loop를 오른쪽 클릭하여 편집하거나 삭제할 수 있습니다. 반복된 게이트의 편집은 원본 게이트 정의에 반영됩니다.
- GUI의 `QICK Square Wave` 탭 이름을 `Square Wave`로 변경했습니다.

## 지원 범위

Loop는 선택된 게이트가 차지하는 전체 시간 구간입니다. 그 구간과 겹치는 다른 큐비트의 게이트도 함께 선택해야 합니다. 서로 분리된 여러 Loop는 지원하며 중첩/겹치는 Loop는 거부합니다. n sweep은 한 번에 하나의 Loop에서 지원합니다.

현재 실행 경로는 shot당 Acquisition 한 개를 지원합니다. 여러 번 반복하는 구간에는 Acquisition을 넣지 않고 반복 구간 뒤에 배치해야 합니다. 회로는 펼친 후 기존 컴파일러로 변환되며, 실제 연결 장비의 프로그램 메모리 용량을 검사합니다. 최대 1,000개 sweep 지점, 펼친 게이트 4,096개 및 펄스 설정 16,384개 제한도 적용합니다.

## 검증 결과

10개 모듈의 최종 유효 검사 311개가 모두 통과했습니다. Loop/n sweep 32개, 회로 통합 15개, 모델 67개, 위젯 24개, 실행 32개, 기존 GUI/RF 78개, Bias Control 11개, GUI 종료 3개, Acquisition 미리보기 19개, Square Wave 30개입니다.

첫 통합 실행에서 기존 Square Wave 오류 메시지와 맞지 않는 테스트 문구 한 개가 실패했습니다. 동작 코드는 유지하고 테스트 기대 문구를 맞춘 뒤 해당 모듈 전체 30개를 다시 통과했습니다. 초기 실패 로그도 보존했습니다. 별도 초기 Loop 검사에서 기존 컴파일러가 먼저 발생시키는 메모리 초과 예외 형식을 맞춘 이력도 보존했습니다.

검사는 실제 GUI 이벤트, 저장/복원, n=0/1/3/100 생산용 프로그램 컴파일, 두 AWG와 RF 시간 정합, RC/DC 모드 유지, 실제 SQLite에 n별 Run 저장 및 다시 읽기, 취소/부분 실패 보존을 포함합니다. 하드웨어 취득은 모의 객체를 사용했으며 컴파일 증거의 HWH 설정은 시험용입니다. 이번 변경에 대한 실제 보드 측정이나 새로운 Verilog 시뮬레이션은 수행하지 않았습니다.

예제 회로의 생산용 컴파일 결과:

| n | PMEM 명령 수 | RF 펄스 수 | Acquisition 시작 (µs) |
|---:|---:|---:|---:|
| 0 | 91 | 0 | 5 |
| 1 | 147 | 2 | 10 |
| 3 | 259 | 6 | 20 |
| 100 | 5691 | 200 | 505 |

이번 작업 전후 SHA256 비교에서 기존 `qick_fine_tune_sweep.py`, `qick_qcodes_experiment.py`, `dc_waveform_core.py`, `dc_waveform_widgets.py`는 동일합니다. RTL, XDC, 펌웨어 및 합성 설정을 변경하지 않았습니다. commit/push는 수행하지 않았습니다.

## 증거 및 사용 방법

- [검사 결과 및 소스 해시](C:/GIT_Workspace/QSTL_QICK/analysis_results/quantum_circuit_loop_20261008/verification.json)
- [n별 컴파일 증거](C:/GIT_Workspace/QSTL_QICK/analysis_results/quantum_circuit_loop_20261008/compiled_loop_evidence.json)
- [GUI 사용 방법](C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI/QUANTUM_CIRCUIT.md)
- [전체 GUI 화면](C:/GIT_Workspace/QSTL_QICK/analysis_results/quantum_circuit_loop_20261008/loop_window.png)
- [반복 회로와 파형](C:/GIT_Workspace/QSTL_QICK/analysis_results/quantum_circuit_loop_20261008/loop_timeline.png)
- [Loop 편집 화면](C:/GIT_Workspace/QSTL_QICK/analysis_results/quantum_circuit_loop_20261008/loop_editor.png)

실제 Qt 화면을 렌더링하고 위 세 그림을 열어 표시를 확인했습니다.
