# Show QICK Program 작업 스레드·모달 창 추가 진단

실제 사용 중 발생한 Show 응답 없음은 현재 재현되지 않았습니다. 아래 결과는 그 원인을 확정하거나 해결했다는 의미가 아닙니다. 생산 Python·RTL·설정은 수정하지 않았고 보드 연결, 기존 GUI 조작, 서버 재시작도 하지 않았습니다.

## 짧은 무보드 실행

별도의 offscreen QApplication에서 현재 `awg_rf_test.json`과 로컬 v5 메타데이터를 사용했습니다. 실제 `MainWindow → Show QICK Program → QThread → worker → assembly dialog` 경로를 실행하되, `connect_qick`만 작업 스레드 안에서 1초 `threading.Event.wait` 후 로컬 QickConfig를 반환하도록 대체했습니다. socket connect/create_connection/connect_ex는 호출 즉시 실패하도록 막았습니다. GUI 메인 스레드에는 10ms QTimer를 두었습니다.

| 관찰 항목 | 결과 |
|---|---|
| 프로세스 종료 | exit 0, 진단 PASS |
| 작업 스레드 대기 | 1.014786초 |
| 대기 중 메인 스레드 heartbeat | 65회, 최대 간격 16.7073ms |
| 대기 중 Run/Show/Stop | 모두 비활성 |
| worker / GUI thread ID | 168728 / 140132 |
| program / metadata 객체 | 일반 Python `FineTuneAmplitudeSweepProgram` / `QickConfig` |
| FIR preview | worker와 GUI에서 각각 정상 종료 |
| assembly 명령 수 | 118 |
| 모달 exec 중 heartbeat | 15회 |
| 모달 parent / transient parent | 모두 MainWindow와 일치 |
| 모달 플랫폼·표시 상태 | offscreen, visible=true, ApplicationModal |
| 닫은 뒤 MainWindow 아래 잔류 assembly dialog | 0개 |
| 네트워크 호출·예외 | 0건 |
| 기준 Python 소스(검증 코드 포함) 169개 / 사용자 JSON | 전후 SHA256 일치 |

이 조건에서는 연결 대기로 인해 실험 버튼이 비활성화되어도 Qt 메인 이벤트 루프가 계속 실행됐습니다. 모달 exec의 중첩 이벤트 루프도 정상 동작했습니다. `Event.wait`는 GIL을 놓으며 실제 Pyro 통신을 수행하지 않으므로, 모든 종류의 네트워크·확장 모듈 정체까지 배제하지는 않습니다.

## 코드에서 확인한 사항

- `DCWaveform_Generator.py:9812–9826`: worker는 `connect_qick`의 `_soc`를 반환 결과에 넣지 않습니다. 로컬 `soccfg`로 만든 program과 assembly/summary를 signal로 보냅니다.
- `qick/qick_lib/qick/pyro.py:128–135`: 실제 연결은 nameserver 탐색과 `soc.get_cfg()` 후 `QickConfig`를 만듭니다. `QickConfig`와 사용한 program은 QObject가 아닙니다. 현재 코드와 이번 관찰에서는 Pyro proxy가 GUI로 전달되어 Qt thread affinity 오류를 일으킨다는 직접 근거가 없습니다.
- `DCWaveform_Generator.py:15014–15030`: worker를 QThread로 옮기고 signal로 결과를 전달합니다. GUI 스레드의 동기 `wait`/`join`은 없습니다.
- `DCWaveform_Generator.py:9815`, `qick_fine_tune_sweep.py:7949`: `summary()`가 worker에서 이미 `fir_dc_timing_preview(0)`을 호출합니다. dialog는 `DCWaveform_Generator.py:9939,9962`에서 같은 point 0 preview를 다시 호출합니다. 따라서 GUI에서만 처음 수행하는 원격 FIR 계산이라고 해석하면 안 됩니다. 이번 두 호출은 모두 정상 종료됐습니다.
- `DCWaveform_Generator.py:15008–15012`: Show는 `show_progress=False`이고 취소도 기본적으로 비활성입니다. 실제 연결이 오래 걸리면 이 패널은 진행 정도나 취소 버튼 없이 대기 상태가 됩니다. 이번 대기 주입은 이것이 GUI 이벤트 루프 정지와 다른 상태임을 확인했습니다.
- `DCWaveform_Generator.py:9903,15041–15042`: assembly dialog는 MainWindow를 parent로 가지며 `exec_()`로 열립니다. 이번 실행에서는 parent와 transient parent 연결이 모두 정상입니다. 코드만으로 parent 누락을 원인으로 볼 수 없습니다.
- dialog의 명시적 `deleteLater`/`WA_DeleteOnClose`가 없더라도 이번 닫기 후 잔류 객체는 0개였습니다. 단일 실행으로 반복 사용 시 누적을 입증하거나 일반적인 누적 부재를 보장하지는 않습니다.

## 아직 확인되지 않은 범위

로컬 재현은 MainWindow를 화면에 표시하지 않는 offscreen 플랫폼이며 모달을 짧게 유지한 뒤 자동으로 닫습니다. 실제 Win32 포커스, 원격 데스크톱, 모니터 변경에 따른 모달 위치, 장시간 열린 창의 상태를 재현하지 않습니다. 메인 창이 모달 때문에 비활성화된 채 모달을 찾지 못하는 상황은 후보이며, 현재 증거로 원인이라고 단정할 수 없습니다.

실제 Pyro 연결의 응답 지연도 이번 실행의 범위 밖입니다. 현재 `make_proxy`는 통신 timeout을 명시하지 않으며 설치된 Pyro4의 기본 `COMMTIMEOUT`은 0입니다. 한편 `qick_update.py:491`은 같은 프로세스의 `Pyro4.config.COMMTIMEOUT`을 4로 설정하므로 실제 GUI 사용 이력에 따른 상태 차이도 가능합니다. Show와 Run은 같은 연결 함수를 사용하므로 이것만으로 Show 전용 문제를 설명할 수는 없습니다.

`_on_qick_program_ready`의 dialog 생성·preview에는 worker의 try/except와 별개인 GUI slot 경계가 있습니다. 실제 증상 재발 시 worker 연결 시작/종료, ready 진입, dialog 생성 완료, main heartbeat, Qt exception, 창 geometry/activeModalWidget 및 해당 시점 thread stack을 함께 기록해야 패널 대기·모달 표시·메인 스레드 정지를 구분할 수 있습니다. 현재 live stack은 정체 순간을 포착한 자료가 아니므로 원인 확정에 쓰지 않았습니다.

추가로 가능한 짧은 무보드 검증은 private process에서 연결 timeout 예외 주입, 반복 Show 후 객체/메모리 관찰, GUI preview 예외 경계 점검입니다. 이번 요청에서는 이 추가 시험들을 실행하지 않았습니다. 실제 Windows 표시 진단은 기존 사용자 GUI에 접근하지 않는 별도 실행에 대한 범위를 정한 뒤 수행해야 합니다.

## 증거

- [검토된 결과와 전체 heartbeat·소스 SHA256](reviewed_result.json)
- [최초 실행 결과](result.json) · [실행 로그](probe.log) · [진단 스크립트](probe.py)
- [기존 Show/Run 비교와 경로 분석](../SHOW_RUN_PATHS.md)

검토본은 최초 JSON의 `retained_closed_dialogs=[]` 측정값과 모순되는 정적 제한 문구 한 줄을 바로잡은 것입니다. 최초 JSON과 스크립트는 그대로 보존했으며 검토본의 `raw_evidence`에 최초 파일 SHA256과 수정 사유를 기록했습니다. 측정값이나 PASS 기준은 바꾸지 않았고 재실행하지 않았습니다.

검토본 SHA256: `a67ec3cbfa1ca902995d9f7f1d159a5f56df8dd49b71b48944a0a714039c8f1d`.
