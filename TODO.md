# QICK / GUI TODO

작성일: 2026-10-03 (America/Vancouver)

기준 브랜치: QSTL_QICK 및 PulseGenerator 모두 `awg_tuning_v2`.
기준 커밋: QSTL_QICK `587f46d7`, GUI `3e78e0c`.
이 문서는 후속 작업을 기록하며, 아래 미해결 항목을 수정 완료했다는 의미가 아니다.

## 2026-10-04 작업 상태

- 사용자가 점별 nearest-DAC-code 전압표 대신 기존 고정 증분/add/rewind 방식을 유지하도록 요청했다. 아래 1번의 종전 정확도 조건은 이 요청으로 대체한다.
- Cartesian 전압표를 제거하고 duration에 따른 계수 행만 유지하도록 수정했다. 200×200 virtual gate 및 RF duration×voltage 소프트웨어 검사를 추가했다.
- AWG v2의 32-bit Q18은 RAMP `step` 폭이다. SET 전압의 16-bit 코드/하위 2-bit 무효 조건은 바뀌지 않으며, 고정 정수 증분의 전압 및 fixed-time DC 보상 오차는 남는다. 이 오차가 없어진 것으로 보고하지 않는다.
- 누적된 SET/DC 보상 코드가 범위를 벗어나면 RC 옵션과 무관하게 실행 전에 검출하도록 보완했다.
- 실제 RTL 완료: 두 DAC AWG Tuning 및 Stability 각각 200×200×2, RF 복합 sweep 4종 각각 20×20×2의 `result.json`이 모두 passed다. 명령 값·시각 불일치 0이다. [최종 결과 및 그림](analysis_results/todo_resolution_20261004/FINAL_REPORT.md).
- 추가 RTL에서 고정전압 20 mV 보상의 일부 1~2클록 SET 펄스가 실제로는 3클록이 되는 제한을 확인했다. 원래 RF 복합 sweep 두 실행은 실패 기록으로 보존한다. 현재는 실행 전 거부하며, 지원 가능한 별도 보상 전압(extend=0.5 mV / fixed=2 mV) RTL은 통과했다. 1~2클록 파형 자체를 지원하도록 수정한 것은 아니다. [근거와 수정 범위](analysis_results/todo_resolution_20261004/SHORT_DC_FINDING.md).
- 검증 현황: [RTL/소프트웨어 보고서](analysis_results/todo_resolution_20261004/RTL_REPORT.md). [오차 수치](analysis_results/todo_resolution_20261004/increment_errors.json).
- 추가 면적 누적 FPGA IP는 구현하지 않았다. 실제 LTspice R/C 회로에서 IIR 앞/뒤 면적 수집 및 보상 위치를 비교했다: [LTspice 보고서](analysis_results/todo_resolution_20261004/LTSPICE_REPORT.md).

## 1. Virtual gate + 대규모 2차원 voltage hardware sweep

- [x] Coupling으로 두 sweep 축에 의존하는 전압·ramp·DC 보상 값을 200×200에서도 DMEM 범위 내에서 처리하도록 개선한다. 기존 정수 증분의 정확도 한계는 보존한다.

**최종 확인 — 2026-10-04**

- 실제 tProcessor/TMUX/AWG v2/IIR RTL: AWG Tuning 및 역방향·축반전 Stability 각각 40,000점×2회, 각 DAC reset 80,001회. 명령 값/시각 불일치 0이며 반복 및 축 초기화를 확인했다.
- Sweep DMEM 0 word, PMEM은 각각 211/135 word이다. 전체 clock의 raw AWG 및 RC 정수 연산 검사를 통과했다. 이 대규모 grid에 아날로그 RC 모델은 적용하지 않았다.
- 실제 SET 목표와 이상적인 요청 전압의 최대 차이는 AWG 9.43328125/5.1203125 mV, Stability 9.44203125/5.140234375 mV이다. 메모리 회귀 해결을 전압 정밀도 개선으로 해석하지 않는다.

**현재 재현된 문제**

- `Vphysical = M @ Vvirtual`에서 `M = [[1, 0.23], [-0.17, 1]]`을 사용했다.
- 두 DAC full-scale은 각각 ±800 mV, ±400 mV로 설정했다.
- Virtual X: 5→15 mV, Virtual Y: −9→7 mV, 각각 200점.
- AWG Tuning과 Stability Diagram 모두 200×200 hardware sweep 프로그램 생성 시 중단된다.
- `_exact_voltage_field_model()`이 두 축에 의존하는 필드에 40,000행 테이블을 요구하지만, tProcessor DMEM은 총 4,096-word이다. 여러 필드와 실행 상태도 이 메모리를 공유한다.
- 오류 예: `exact voltage sweep field (...) requires 40000 dependent rows; tProcessor DMEM cannot hold this coupled voltage/duration grid`.
- 실행 전에 검출되는 메모리 제한이다. 실행 도중 잘못된 전압이 출력되었다는 결과는 아니다.

**발생 시점 확인**

- GUI `3e78e0c`에서 전압 sweep 누적 오차를 없애는 점별 정밀 테이블을 도입하면서 생긴 회귀다. 기존부터 virtual gate 200×200이 불가능했던 것은 아니다.
- 동일한 virtual gate 행렬·전압 범위·두 DAC·AWG v1 구성으로 비교했을 때, 이전 GUI `5a1933c`는 AWG Tuning 및 Stability Diagram의 40,000점 프로그램 생성·컴파일에 성공했다. DC compensation ON/OFF 모두 sweep 테이블용 DMEM은 0 word였다.
- 현재 GUI `610b9cc`는 위 네 조건 모두 `requires 40000 dependent rows` 오류로 실패했다. 이 비교는 프로그램 생성·컴파일 검증이며 이전 버전의 실제 출력 정확도까지 재검증했다는 의미는 아니다.

**이미 확인한 범위**

- 두 virtual gate 20×20 × 지점당 2회: AWG Tuning 및 Stability Diagram 모두 실제 tProcessor/TMUX/AWG v2 Verilog RTL 통과.
- 한 virtual gate 200점 × 지점당 2회: tProcessor 명령 실행 모델 통과.
- 변환된 목표 전압, ramp 증분, DC 보상, RC 정수 연산, 반복 및 축 전환 초기화 확인.
- GUI 탭 전환과 설정 저장·복원 시 행렬 및 채널별 full-scale 유지 확인.
- 위 결과가 임의의 행렬·segment 수·grid 크기 모두의 동작을 보장하지는 않는다.

**완료 조건**

- DAC 양자화 전의 축별 기여를 분리하는 방식 등 메모리 절감 방법을 검토한다. 분리한 값을 각각 반올림해서 더할 경우 생기는 오차도 확인한다.
- 2026-10-04 사용자 지시: 점별 nearest-DAC-code 표로 해결하지 않고 기존 고정 증분/add/rewind를 유지한다. 이 방식의 요청 전압 오차, ramp 및 DC 보상 오차를 별도로 수치화하며, 명령 실행 검사의 통과와 구분한다.
- 두 DAC, 양·음 coupling, 정방향·역방향, 두 축 순서, DC/RC 옵션, 채널별 서로 다른 full-scale을 검증한다.
- 200×200 명령 실행 모델과 실제 RTL 결과를 구분해 기록하고, 지원 한계를 넘으면 실행 전에 명확한 오류를 표시한다.

관련 코드: GUI `DCWaveformGeneratorGUI/qick_fine_tune_sweep.py`의 `_build_sweep_register_plan()`, `_linear_bias_t_models()`, `_boundary_bias_models_from_values()` 및 DMEM 테이블 할당 부분. 회귀를 만든 `_exact_voltage_field_model()`은 이번 수정에서 제거했다.

검증 자료: [결과 요약](analysis_results/virtual_gate_voltage_20261003/summary.json), [소프트웨어 재현 결과](analysis_results/virtual_gate_voltage_20261003/software_results.json). 이 자료들은 현재 로컬 검증 산출물이다.

## 2. RF duration sweep + voltage sweep

- [x] 이전에 논의한 RF duration + voltage 복합 hardware sweep의 남은 제한과 미검증 조합을 점검한다. 아래 지원 범위와 명시적 사전 거부 조건을 확인했다.

**최종 확인 — 2026-10-04**

- RF segment fixed/extend × DC fixed_time/fixed_voltage 네 조합의 실제 RTL 20×20×2 통과. 각각 RF 800개, 각 AWG reset 801회, 명령 값/시각 및 RF width 불일치 0이다.
- 원래 보상 20 mV fixed_voltage 두 실행의 62/80개 시각 불일치는 실패 기록으로 남긴다. 재검증은 각각 0.5/2 mV의 지원 가능한 조건이며 원래 설정을 자동 수정한 것은 아니다.
- 1~2 tProcessor clock DC SET 보상은 하드웨어 최소 간격 때문에 실행 전에 오류로 안내한다. 내부 면적 0 교차도 증분 계수에서 검출한다. 자동 시간/전압 조정 정책 및 하드웨어 변경은 구현하지 않았다.
- RF 200×200은 방향·축 순서·DC 모드별 소프트웨어 검증이다. 최종 13개 모듈 413개 검사, 모두 정상 exit=0. 실제 RF 200×200 RTL을 실행한 것으로 보고하지 않는다.

**기존 이슈 및 현재 상태**

- RF duration이 변하면 `extend_by_rf_duration` 모드에서는 이후 segment의 시각과 AWG 유지 시간이 달라진다. 이에 따라 DC 보상 면적에 voltage × duration 항이 생기므로 RF length만 갱신해서는 충분하지 않다.
- `fixed` 모드와 `extend_by_rf_duration` 모드를 구분하고, 이후 AWG/RF/readout/trigger 시각, 보상 전압 또는 보상 시간, 반복 종료 시각을 함께 확인해야 한다.
- 과거 짧은 RF 펄스가 periodic 3클록 블록 경계에서 종료되어 1~2클록 길어지던 문제는 oneshot length를 직접 지정하는 방식으로 수정되었다.
- 20×20 × 2회 짧은 RF duration + voltage sweep은 기존 RTL 기록에서 통과했다. AWG v2의 `rf_duration` 사례도 800개 RF 펄스의 길이 및 명령 시각 검사를 통과했다. 이 범위를 미해결 오류로 다시 기록하지 않는다.
- 긴 펄스는 기존 요청대로 periodic 방식을 유지한다. 실행할 sweep 지점 중 하나라도 65,535 generator clocks를 초과하면 해당 duration 축 전체가 periodic이다.
- 이 경우 블록 경계에 따른 종료 지연은 남아 있다. 기존 경계 테스트에서는 65,536클록 요청이 65,538클록 출력이었다. 이는 보존된 긴 펄스 동작이며 exact timing 통과가 아니다.

**후속 확인 사항**

- 200×200에서 DC `fixed_time` / `fixed_voltage`, RF segment `fixed` / `extend_by_rf_duration`, 축 순서 및 sweep 방향별 지원 범위를 정리한다.
- 기존 `fixed_voltage` 200×200 사례에는 전체 point table 대신 계수 행을 사용하는 소프트웨어 검사가 있다. 이것을 모든 조합의 지원 또는 200×200 전체 RTL 검증으로 확대 해석하지 않는다.
- Voltage × duration에 의존하는 DC 보상 및 기타 필드가 큰 joint table을 요구하는 조건을 재현하고, DMEM 절감 시 전압 반올림·보상 정확도·축 초기화를 함께 검증한다.
- Virtual gate를 추가한 조합도 별도 검증한다. 위 1번의 coupling 메모리 문제와 동시에 발생할 수 있다.
- 2026-10-04 추가 발견: tProcessor v1 같은 포트의 연속 SET 최소 간격은 3클록(300 MHz에서 10 ns)이다. 1~2클록 고정전압 DC 보상은 그대로 정확히 출력할 수 없어 실행 전에 출력/지점을 명시해 거부한다. 내부 면적 0 교차는 파형 전체 컴파일 대신 기존 affine 계수에 정수 구간식을 적용해 검출한다. 자동으로 전압을 낮추거나 시간을 늘리지는 않는다.
- 긴 periodic RF의 요청 길이와 실제 길이 차이를 사용자에게 어떻게 표시할지 검토한다. 기존에 요청된 긴 펄스 정책을 임의로 바꾸지 않는다.

관련 코드: GUI `DCWaveformGeneratorGUI/qick_fine_tune_sweep.py`, `test_rf_duration_oneshot.py`, `test_rc_sweep_matrix.py`.

기존 증거: [RF duration 검증 보고서](analysis_results/rc_precompensation_v1/rf_duration_oneshot_v1/REPORT.md), [AWG v2 RF duration + voltage RTL 결과](analysis_results/awg_tuning_v2/rtl_evidence/rc_precomp_repeat_reset_rf_duration_20x20_exact_voltage_awg_v2.json).

## 3. AWG Tuning RF Readout: FIR 측정 구간과 DC compensation의 실행 순서 선택

- [x] RF Readout의 `Stored FIR samples`로 정한 측정 구간이 사용자 AWG pulse 끝을 넘어갈 때, DC compensation 구간을 포함해서 측정할지 또는 0 전압 구간에서 측정을 마친 뒤 DC compensation을 수행할지 GUI에서 선택할 수 있게 한다.

**변경 전 동작 — 후자 방식 (GUI `610b9cc`)**

- GUI `610b9cc`의 `qick_fine_tune_sweep.py`에서 DDR capture 종료 시각을 `point_end`에 포함한다.
- `_emit_point()`는 사용자 pulse 끝에 `bias_t_pre_zero` SET 명령을 예약해 AWG 목표값을 0으로 바꾼다. 이후 capture 종료를 포함한 시각까지 `sync_all(0)`으로 진행한 뒤 `_emit_bias_t_compensation()`을 호출한다.
- 따라서 pulse 종료 이후에도 측정이 남으면 그동안 AWG 목표값을 0으로 유지하고, 측정 종료 후 DC compensation을 실행한다. 현재 이 순서를 고르는 GUI 옵션은 없다.
- 여기서 0은 AWG에 명령한 목표값이다. RC precompensation을 함께 사용하면 적분 상태 때문에 실제 DAC 출력에 잔류 offset이 있을 수 있으므로 물리적인 DAC 0 V와 구분한다.

**구현한 선택지**

| 선택 | 사용자 AWG pulse 종료 후 동작 | 저장되는 측정 구간 |
| --- | --- | --- |
| DC compensation 포함 측정 | 필요한 명령·출력 지연을 반영해 DC compensation을 시작하고 FIR 측정을 계속한다. | 설정한 샘플 수를 유지하며 겹치는 DC compensation 구간도 포함한다. |
| 0 전압에서 측정 완료 후 DC compensation | AWG 목표값을 0으로 바꾸고 남은 FIR 측정을 완료한 뒤 DC compensation을 시작한다. | DC compensation 시작 전의 구간을 저장한다. 기존 동작이며 기본값으로 유지한다. |

**완료 조건 / 검증 사항**

- RF Readout GUI에 선택 옵션을 추가하고 설정 저장·복원, Python 코드 생성 및 측정 메타데이터에 반영한다. 과거 저장 설정에는 기존 동작을 적용한다.
- 샘플 수를 임의로 줄이거나 0 데이터로 채우지 않는다. FIR 지연 및 펌웨어의 trigger 지연 보정을 반영해 실제 입력 시간 구간과 저장 시각을 구분하고, preview에서 사용자 pulse 끝·capture 끝·DC compensation 시작/끝을 확인할 수 있게 한다.
- 측정이 pulse 끝 이전에 끝나는 경우, 정확히 끝에 닿는 경우, compensation 도중 또는 compensation 종료 이후까지 이어지는 경우를 검증한다.
- DC `fixed_time` / `fixed_voltage`, 두 DAC, RC ON/OFF, 반복 및 voltage/ramp/hold/RF duration sweep에서 선택한 순서가 유지되고 DC 보상 계산·출력 시각·RC 초기화가 일관되는지 확인한다.
- DC compensation 포함 측정에서도 다음 반복은 capture와 compensation이 모두 끝난 뒤 시작해야 한다. 기존 trigger 경계 및 출력 명령 FIFO 순서를 보존한다.
- GUI 생성 프로그램을 tProcessor 명령 실행 모델 및 실제 RTL 테스트벤치에서 확인하고, 요청 타이밍과 AWG 출력·capture·compensation 구간을 함께 plot한다.

관련 코드: GUI `DCWaveformGeneratorGUI/DCWaveform_Generator.py`의 RF Readout 설정 및 내보내기, `DCWaveformGeneratorGUI/qick_fine_tune_sweep.py`의 DDR capture/point-end 계산, `_emit_point()`, `_emit_bias_t_compensation()`.

**완료 및 검증 — 2026-10-04**

- `RF Readout > DC compensation timing`에 두 선택지를 추가했다. 과거 설정과 기본값은 `after_readout`이며 새 선택은 `overlap_readout`이다. 설정 JSON, 생성 Python, 실제 실행 config, QCoDeS 프로그램 메타데이터로 전달된다.
- `Show QICK Program > FIR / DC timing`에서 sweep 지점별 pulse 끝, 입력 측정 종료, FIR 지연을 반영한 DDR 저장 시각, 두 DAC의 보상 시작·종료를 표시한다. FIR의 유한 응답과 연속 decimation의 샘플 경계 오차는 별도로 안내한다.
- 새 모드는 각 지점의 출력 종료와 입력 측정 종료를 별도 tProcessor 레지스터로 처리한다. 보상 전압·시간 계산을 유지하고, 반복 종료 및 RC 초기화는 측정과 보상이 모두 완료된 뒤 진행한다. 긴 출력 trigger와 RF 종료도 보존한다.
- GUI/소프트웨어 assertion 246개 통과. 경계 샘플 수, 두 DC 모드, RC ON/OFF, 반복, 전압/ramp/hold/RF duration sweep, 긴 trigger, 1 MSPS/50 kSPS profile, 과거 JSON 및 새 JSON 저장·복원을 검사했다. Qt 종료 시 별도 접근 위반은 아래 4번에 기록한다. 모든 테스트 프로세스가 정상 종료했다는 뜻은 아니다.
- 실제 RTL 8종, 각각 3×3×2회(총 144회) 통과. 명령 값·시각 불일치 0, 두 AWG 각각 매 실행 19회 reset, DDR 총 1,152개 샘플 저장을 확인했다. RF DDS를 포함한 혼합 sweep의 펄스 길이도 일치했다.
- DDR v3 capture IP와 AXI sink는 실제 RTL이며, FIR 입력은 1 MSPS timestamp-tag 테스트 스트림이다. ADC/RFDC/FIR 수치 연산이나 보드의 아날로그 측정을 새로 검증했다는 의미는 아니다.
- 전원 중단 후 RTL 소스·PMEM·DMEM SHA-256을 저장된 fingerprint와 비교했고, 현재 GUI 코드로 재생성한 PMEM/DMEM도 8종 모두 일치했다. Python 구문, JSON·PNG 파일과 Git 객체 무결성을 재확인했다.
- FPGA IP/bitstream 변경은 없다. 대규모 중간 산출물은 Git에 포함하지 않고 파형 기록은 실행당 처음 12,000클록으로 제한했다.

검증 자료: [결과 보고서](analysis_results/fir_dc_order_20261003/REPORT.md), [실제 RTL 출력 비교](analysis_results/fir_dc_order_20261003/fir_dc_order_rtl.png), [DDR 수집 시각](analysis_results/fir_dc_order_20261003/fir_dc_ddr_timing.png), [GUI 화면](analysis_results/fir_dc_order_20261003/rf_readout_controls.png), [복구 무결성 검사](analysis_results/fir_dc_order_20261003/recovery_integrity.json).

## 4. 설정 복원 후 Windows offscreen Qt 테스트 프로세스 종료 오류

- [x] 설정 파일을 불러온 MainWindow가 닫힌 뒤 Python/Qt 정리 단계에서 발생하는 native access violation을 조사하고 종료 순서 및 테스트 객체 수명을 수정한다.
- 2026-10-04 전원 중단 후 재검사에서 GUI assertion은 모두 통과했으나, 프로세스 종료 시 `0xC0000005`가 발생했다. `-X faulthandler` 출력에는 Python frame이 없다.
- 새 FIR/DC 코드 이전 GUI `610b9cc`의 `DCWaveform_Generator.py`를 별도 파일로 읽어 동일 환경에서 `MainWindow → save settings → load settings → close`를 실행해 같은 종료 오류를 재현했다. 단순 창 생성·close는 정상 종료였다. 체크아웃/브랜치를 변경하지 않았다.
- 여기서 사용한 환경은 Codex bundled Python/PyQt5와 `QT_QPA_PLATFORM=offscreen`이다. 실제 사용자 GUI 환경에서의 재현 여부 및 Qt 객체/타이머 수명 문제는 추가 확인이 필요하다. 시스템 전원 중단으로 파일이 손상되었다는 증거는 아니다.
- 새 RF Readout 패널과 FIR/DC timing dialog만 실행한 두 GUI 검사는 정상 종료했고, MainWindow 설정 복원 검사 및 기존 GUI 종합 검사는 종료 오류를 보였다. 실험 데이터·RTL 타이밍 검증과 이 종료 오류를 구분한다.
- 증거: [분리 실행 exit codes](analysis_results/fir_dc_order_20261003/software_modules/exit_codes.json), [복구 확인](analysis_results/fir_dc_order_20261003/RECOVERY.md).

**수정 및 재검사 — 2026-10-04**

- 실제 GUI 진입점에서 event loop 종료 후 MainWindow의 deferred deletion → Python 참조 순환 정리 → 소유한 QApplication 파괴 순서를 명시했다. `os._exit()`로 충돌을 숨기는 방식은 사용하지 않았다.
- headless 테스트도 생성한 MainWindow를 QApplication 수명 안에서 정리하도록 수정했다. 저장·복원 뒤 단순 `close()`만 호출하고 Python 종료에 객체 정리를 맡기던 경우와 구분했다.
- 별도 프로세스에서 실제 `main()` 진입점과 Qt event loop를 실행하여 설정 복원 0/1/5회 후 정상 exit=0을 확인했다. 기존 GUI 검사 78개와 FIR/DC 검사 53개도 각각 정상 종료했다.
- 최신 전체 회귀 결과는 [프로세스 종료 코드](analysis_results/todo_resolution_20261004/software/exit_codes.json)에 보존한다. Windows offscreen 환경의 검사이며 실제 보드에 연결한 GUI 측정 시험은 아니다.
- 수정 후 관련 12개 테스트 모듈, 총 403개 검사를 통과했고 모든 테스트 프로세스의 종료 코드가 0이다.
- 이후 DC 최소 SET 간격 검사를 포함한 최종 소프트웨어 결과는 13개 모듈 413개 통과, 모든 프로세스 exit=0이다. 지원 불가 조건의 거부 검사와 지원 가능한 낮은 보상 전압 검사를 구분한다. [최종 exit codes](analysis_results/todo_resolution_20261004/software_final/exit_codes.json).
