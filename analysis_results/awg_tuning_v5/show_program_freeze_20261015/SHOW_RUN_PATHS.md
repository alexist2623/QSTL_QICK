# Show QICK Program / Run Experiment 경로 비교

검토 시각: 2026-10-15. 생산 코드 읽기 전용 검토입니다. 아래 GUI 파일의 기준 디렉터리는 `C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI`입니다.

## 결론

두 버튼은 공통 `build_qick_program` 컴파일러를 사용합니다. 다만 Show 버튼은 현재 RF spec 한 묶음으로 프로그램 하나를 만들고, Run은 software sweep이 있으면 각 host 좌표를 적용한 뒤 프로그램을 여러 개 만듭니다. 따라서 **항상 같은 어셈블리를 만든다고 볼 수 없습니다.**

software sweep이 없고 GUI 입력, 연결 시 읽은 HWH/config, DAC scale 상태, calibration DB/선택 run, 컴파일 모드가 동일하면 공통 builder에 전달되는 주요 입력이 같으므로 같은 프로그램을 기대할 수 있습니다. 실제 동일성 확인에는 ASM/PMEM뿐 아니라 runtime DMEM과 RF envelope 내용도 필요합니다.

사용자 확인 파일 `awg_rf_test.json`은 RF software sweep 축이 0개입니다.
별도 GUI에서 실제 Show worker를 실행하고, 정상 Run 경로의
`execute_qick_sequence`가 `acquire_fir_ddr`를 호출하기 직전에 데이터를
포착한 결과 **v4 및 v5 모두 ASM/PMEM/runtime DMEM/RF envelope가 일치**했습니다.
각각 118개 명령입니다. 이 파일의 runtime DMEM과 RF envelope bank는 양쪽 모두 비어 있어,
해당 두 항목의 일치는 빈 상태의 일치입니다. 실제 RF DAC 파형을 측정한 검사는 아닙니다.
로컬 config를 사용하고 readout 하드웨어 설정만 대체했으며
보드에는 연결하거나 프로그램을 실행하지 않았습니다. 이 결과는 해당 파일의
컴파일 동일성 증거이며, 사용자의 실제 연결/표시 정체가 해결됐다는 뜻은 아닙니다.
증거: `show_run_equal_v4.json`, `show_run_equal_v5.json`, `compare_show_run.py`.

## Show 경로

1. `DCWaveform_Generator.py:14981` `_show_qick_program`이 `:13138` `_experiment_run_arguments(require_readout=False, require_run_config=False)`로 현재 GUI의 sequence/RF/readout 설정을 읽습니다.
2. `DCWaveform_Generator.py:14997`의 kwargs는 sequence, AWG 채널, 반복 수, tProcessor MHz, RF specs, readout spec, compile validation mode입니다.
3. `DCWaveform_Generator.py:9798` `QickProgramWorker`의 `run`에서 `:9812` 연결, `:9813` `build_qick_program`, `:9814` compile, 이후 summary/asm을 수행합니다. 하드웨어 실험 실행은 하지 않습니다.
4. `DCWaveform_Generator.py:15032` `_on_qick_program_ready`가 `:9899` `QickAssemblyDialog`를 만듭니다. DDR readout이 설정되어 있으면 생성 중 `:9939`에서 `_update_fir_dc_timing(0)`을 호출합니다.
5. `DCWaveform_Generator.py:9960` `_update_fir_dc_timing`은 `qick_fine_tune_sweep.py:7645` `fir_dc_timing_preview`의 결과를 표시합니다. 이 dialog/FIR preview는 Show 전용입니다. `summary()` 자체는 Run에서도 결과 저장에 사용되므로 Show에만 존재하는 계산이라고 보면 안 됩니다.

## Run 경로

1. `DCWaveform_Generator.py:14849` `_run_qick_experiment`도 공통 `:13138` `_experiment_run_arguments`를 호출하지만 readout과 run 설정을 필수로 검증하고 GUI 설정 스냅샷을 포함합니다.
2. `DCWaveform_Generator.py:9733` `QickExperimentWorker` → `:9762` `run_qick_qcodes_experiment`입니다. 현재 함수 이름은 `run_qick_qcodes_experiment`이며 `run_qick_finetune_experiment`가 아닙니다.
3. `qick_qcodes_experiment.py:2954`가 실행 진입점이고, `:2982`에서 연결한 현재 HWH config를 사용합니다. FIR profile과 저장 metadata를 준비한 뒤 `:3129`에서 `execute_qick_sequence`를 호출합니다.
4. `qick_qcodes_experiment.py:1613` `execute_qick_sequence`는 RF software sweep bindings를 확인합니다. 없으면 sequence/spec 그대로 `_execute_qick_sequence_once`에 전달합니다.
5. bindings가 있으면 `:1452`의 Cartesian host 좌표를 순회하며 `:1661`에서 `_rf_specs_at_software_coordinate`(`:1461`)로 N, τ, named delay, amplitude, phase, T2 duration 값을 적용하고, `:1666`에서 `_sequence_at_rf_software_coordinate`(`:1505`)로 RF에 따른 SET 길이 확장을 다시 계산합니다. 각 좌표마다 `_execute_qick_sequence_once`를 호출합니다.
6. `qick_qcodes_experiment.py:1224` `_execute_qick_sequence_once`는 `:1256`에서 readout 하드웨어를 설정하고, `:1283`에서 Show와 같은 `build_qick_program`을 사용합니다. `:1375`에서 `acquire_fir_ddr`로 실제 실행·수집합니다. 이후 QCoDeS 결과 및 프로그램 summary를 저장합니다.

## 공통값과 차이

| 항목 | Show | Run |
|---|---|---|
| Compiler | `qick_qcodes_experiment.py:986` | 동일 builder |
| Hardware sweep | sequence 안에 포함되어 프로그램으로 내려갑니다 | 동일 |
| RF host software sweep | 현재 spec 한 묶음, host 좌표 순회 없음 | 모든 좌표를 적용하고 프로그램별 재컴파일 |
| tProcessor MHz | `self._qick_tproc_mhz` | GUI 스냅샷의 `qick.tproc_mhz`(`qick_qcodes_experiment.py:3023`) |
| HWH/config | 버튼 클릭 뒤 연결 시 읽음 | 실행 시작 뒤 연결 시 읽음 |
| DAC scale/current | 공통 GUI state 사용 | 공통 GUI state 사용 |
| RF calibration | 공통 RF builder에서 DB를 읽음 | 좌표별 공통 RF builder에서 DB를 읽음 |
| FIR timing dialog | 프로그램 생성 뒤 별도 프리뷰 표시 | 이 dialog를 만들지 않음 |
| Hardware acquisition/QCoDeS 저장 | 없음 | 있음 |

DAC scale/current는 `DCWaveform_Generator.py:13539` `_dac_scale_arguments`가 현재 GUI `_dac_current_state`의 채널별 scale 및 snapshot을 넣는 방식입니다. 두 버튼의 `connect_qick` 호출 자체가 DAC 전류를 새로 읽는 것은 아닙니다. Identify/Apply DAC current 작업에서 갱신한 GUI state가 입력으로 쓰입니다.

RF calibration은 공통 `qick_qcodes_experiment.py:695` `build_runtime_rf_pulses` 내부에서 `:815` DB를 읽고 gain schedule을 만듭니다. 같은 DB 경로라도 선택 run이 latest이거나 DB가 바뀌면 시점별 결과가 달라질 수 있습니다. v5 summed RF 출력의 calibration 거부도 이 공통 경로에 있습니다.

## GUI 응답 없음 현상 조사 상태

사용자가 실제 파일은 `awg_rf_test.json`이며 창이 닫히는 것이 아니라 응답이 없어진다고 확인했습니다. 별도 오프스크린 프로세스에서 이 파일을 실제 GUI에 로드하고 v4 및 v5 config로 `reproduce.py`를 실행한 결과, 각각 118개 명령을 생성하고 assembly 창에 정상 진입했습니다. v5에서는 입력 해석부터 assembly 창까지 약 0.05초였습니다. 실제 서버에는 접속하지 않았습니다. 실행 중 GUI의 읽기 전용 호출 스택은 main event loop 대기 상태였으며 사용자가 현재 재현할 수 없다고 했습니다. **실제 멈춤 지점과 원인은 아직 확정하지 않았습니다.**

읽기 검토에서 확인한 예외 경계는 다음과 같습니다.

- `QickProgramWorker.run`은 connect/build/compile/summary를 `except Exception`으로 잡아 failed 신호를 보냅니다.
- `_on_qick_program_ready`의 dialog 생성 및 `QickAssemblyDialog` 생성 중 FIR timing preview에는 같은 예외 보호가 없습니다. 여기서 발생한 예외는 Qt slot 밖으로 전달될 수 있어 조사 대상입니다. 아직 이번 사용자 현상의 원인으로 확정된 것은 아닙니다.
- `_show_qick_program` 초기 GUI argument 수집은 ImportError/RuntimeError/TypeError/ValueError만 잡습니다. KeyError/IndexError/AttributeError 등은 그 보호 범위에 없습니다.
- 기존 단순 assembly dialog 검사는 `program` 없는 가짜 결과도 사용하므로 실제 사용자 프로그램의 FIR timing preview 경로 전체를 보장하지 않습니다.

이 문서 작성으로 생산 Python/GUI, RTL, 사용자 JSON, 서버 또는 펌웨어를 변경하지 않았습니다.

진단 도구 `py-spy 0.4.2`는 qcodes2 설치를 바꾸지 않고 별도 Temp 디렉터리에
설치했습니다. `dump`로 GUI Python 프로세스의 호출 스택만 읽었으며 locals나
메모리 덤프를 수집하지 않았습니다. 사용 방식은 [공식 py-spy 문서](https://github.com/benfred/py-spy#dump)를 따랐습니다.
진단 초기 v5 config 준비에서 기본 fixture의 v1 AWG 타입 변환을 누락한
AssertionError는 `reproduction_v5.log`에 보존했습니다. 테스트용 config를
기존 검증과 같은 v3 타입으로 구성한 뒤 정상 재현했고 생산 소스는 수정하지 않았습니다.

## 연결 대기와 GUI 이벤트 루프 분리 검사

실제 `_show_qick_program` → `QThread` 경로에서 `connect_qick`만 1초
`Event.wait`로 대체한 무보드 진단도 수행했습니다. 1.0148초 대기 중 메인
Qt timer가 65회 실행됐고 최대 간격은 16.71ms였습니다. Run/Show/Stop
버튼은 비활성 상태였지만 이벤트 루프는 계속 동작했습니다. Show 진입점의
`set_running(True, ..., show_progress=False)`(`DCWaveform_Generator.py:15008`)는
진행바를 표시하지 않으므로 이 대기 상태와 전체 GUI 정지를 구분해야 합니다.

모달 `exec_()` 중에도 timer가 15회 실행됐습니다. 모달 parent/transient parent는
MainWindow와 일치했고, worker에서 전달된 program은 QObject나 원격 proxy가 아닌
일반 Python program/로컬 `QickConfig`였습니다. worker와 GUI의 FIR preview는 모두
정상 종료했고 이 단일 실행에서 닫힌 assembly dialog가 남아 있지 않았습니다.

이 검사는 GIL을 놓는 모의 대기와 offscreen Qt 조건입니다. 실제 Pyro 통신 장애,
Win32 창 위치·포커스, 원격 데스크톱 화면, 반복 사용 중 문제를 재현한 것은 아닙니다.
**사용자에게 발생한 응답 없음의 원인은 여전히 미확정이며 생산 수정은 하지 않았습니다.**

[검토된 진단 결과](worker_wait_probe/reviewed_result.json),
[진단 스크립트](worker_wait_probe/probe.py), [원본 로그](worker_wait_probe/probe.log).
원본 결과의 정적 제한 문구가 측정된 dialog 잔존 0개와 모순되어 검토본에서 해당
설명만 정정했습니다. 원본 JSON과 원본 해시는 그대로 보존했습니다.
