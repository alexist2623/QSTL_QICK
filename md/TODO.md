# QICK / GUI TODO

작성일: 2026-10-03 (America/Vancouver)

기준 브랜치: QSTL_QICK 및 PulseGenerator 모두 `awg_tuning_v2`.
기준 커밋: QSTL_QICK `587f46d7`, GUI `3e78e0c`.
이 문서는 후속 작업을 기록하며, 아래 미해결 항목을 수정 완료했다는 의미가 아니다.

## 2026-10-07 v3 후속 작업 상태

- 현재 두 저장소 브랜치는 `awg_tuning_v3`입니다. 아래 2026-10-04 기록은 v2 결과이며 그대로 보존합니다.
- [x] IIR 전단의 실제 DAC 샘플 면적을 합산하고, DC 보상 및 마지막 0 경계 처리 뒤 shot마다 면적/IIR을 초기화하는 v3 IP를 구현했습니다.
- [x] 32/48/64비트의 동일 100점 sweep·두 DC 모드 RTL 비교와 누적 오차 그래프를 저장했습니다. 48/64 수치가 같아 48비트를 선택했습니다. 32비트는 34회 overflow로 실패를 명시했습니다.
- [x] GUI/Python에서 새 IP를 인식하고 두 DC 모드, RC, RF/DDR 타이밍을 반영했습니다. GUI 생성 결과 그대로 두 DC 모드 각각 100점×2회 실제 tProcessor/TMUX/AWG/RF/DDR RTL을 통과했습니다. 별도 축반전 및 Stability builder 100점×2회도 통과했습니다.
- [x] 모든 검증 shot의 디지털 잔여 면적 0, shot 초기화, 명령 값·시각 일치를 확인했습니다. 기존 SET sweep 정수 증분 오차는 사용자 지시에 따라 보존하며, 이상 목표 전압이 정확해진 것으로 해석하지 않습니다.
- [x] 기존 SET/RAMP/SquarePulse/IIR/RF/DDR 주요 로직을 원복하고 53개 보호 소스 해시를 확인했습니다. 현 소스로 GUI→RTL 네 조건과 소프트웨어986개, 48비트 단위5개, 기존 출력·지연 회귀를 통과했습니다. 초기 실패와 테스트 환경 재검사 기록을 보존합니다.
- [x] 선택된 48비트의 긴 RC 검증 200회를 완료하고 누적오차 그림2개를 갱신·확인했습니다. overflow/수집오차/잔여·누적면적0, 최대RC오차0.05461681895mV, 종료잔류0.000863350555mV입니다. 32/64비트 폭 선택 비교는 재실행하지 않았습니다.
- [x] 저장소 밖 새 프로젝트 `F:/Vivado_Output/a3full7`의 전체 빌드가 **2026-10-07 17:34:58 PDT**에 완료됐습니다. **jobs=4 / maxThreads=5**, 원본 v2 XDC와 바이트 동일한 실제 프로젝트 제약을 유지했습니다. 최종 setup WNS **+0.011847 ns**, hold WHS **+0.009619 ns**, TNS/THS 0, pulse-width 위반 0, bus-skew 14개 모두 통과(최소 여유 +2.429 ns), 배선 오류 0입니다.
- [x] 최신 소스·기능 검증·전체 timing·7개 48비트 AWG와 공통 300 MHz 구성을 검사한 뒤, 같은 성공 XSA에서 BIT/HWH를 추출하여 [펌웨어 폴더](../qick/md/firmware/projects/qstl_awg_v3/README.md)에 교체했습니다. [배포 manifest](../qick/firmware/projects/qstl_awg_v3/build_manifest.json)에 소스·증거·펌웨어 해시를 저장했습니다. commit/push는 수행하지 않았습니다.
- 실패 이력은 보존합니다. `a3full1`(-0.554 ns), `a3full3`(-0.092 ns)은 배포하지 않았습니다. `a3full7`의 초기 FIR 메모리 할당/SmartConnect Tcl 오류는 두 실패 IP만 같은 조건으로 재시도해 통과했고, 완료된 IP 결과를 유지한 채 상위 합성·구현을 마쳤습니다.
- 검증 한계: 원본 제약 기준 timing closure이며, 외부 I/O 지연 미지정 28포트 및 CDC/동기화 속성·기존 max-delay 덮어쓰기 경고는 남습니다. 보드 아날로그 측정을 수행한 결과가 아니며, 기존 SET 정수 증분의 이상 목표 전압 양자화 오차를 해결한 것으로 해석하지 않습니다.
- [최종 결과 및 펌웨어](../analysis_results/awg_tuning_v3/FINAL_REPORT.md), [결과 및 검증 범위](../analysis_results/awg_tuning_v3/VALIDATION_REPORT.md), [GUI → 실제 RTL](../analysis_results/awg_tuning_v3/system_validation/REPORT.md), [현재 48비트 RC 검증](../analysis_results/awg_tuning_v3/selected48_validation/REPORT.md), [역사적 32/48/64 비교](../analysis_results/awg_tuning_v3/width_comparison/WIDTH_COMPARISON.md).

## 2026-10-04 작업 상태

- 사용자가 점별 nearest-DAC-code 전압표 대신 기존 고정 증분/add/rewind 방식을 유지하도록 요청했다. 아래 1번의 종전 정확도 조건은 이 요청으로 대체한다.
- Cartesian 전압표를 제거하고 duration에 따른 계수 행만 유지하도록 수정했다. 200×200 virtual gate 및 RF duration×voltage 소프트웨어 검사를 추가했다.
- AWG v2의 32-bit Q18은 RAMP `step` 폭이다. SET 전압의 16-bit 코드/하위 2-bit 무효 조건은 바뀌지 않으며, 고정 정수 증분의 전압 및 fixed-time DC 보상 오차는 남는다. 이 오차가 없어진 것으로 보고하지 않는다.
- 누적된 SET/DC 보상 코드가 범위를 벗어나면 RC 옵션과 무관하게 실행 전에 검출하도록 보완했다.
- 실제 RTL 완료: 두 DAC AWG Tuning 및 Stability 각각 200×200×2, RF 복합 sweep 4종 각각 20×20×2의 `result.json`이 모두 passed다. 명령 값·시각 불일치 0이다. [최종 결과 및 그림](../analysis_results/todo_resolution_20261004/FINAL_REPORT.md).
- 추가 RTL에서 고정전압 20 mV 보상의 일부 1~2클록 SET 펄스가 실제로는 3클록이 되는 제한을 확인했다. 원래 RF 복합 sweep 두 실행은 실패 기록으로 보존한다. 현재는 실행 전 거부하며, 지원 가능한 별도 보상 전압(extend=0.5 mV / fixed=2 mV) RTL은 통과했다. 1~2클록 파형 자체를 지원하도록 수정한 것은 아니다. [근거와 수정 범위](../analysis_results/todo_resolution_20261004/SHORT_DC_FINDING.md).
- 검증 현황: [RTL/소프트웨어 보고서](../analysis_results/todo_resolution_20261004/RTL_REPORT.md). [오차 수치](../analysis_results/todo_resolution_20261004/increment_errors.json).
- 추가 면적 누적 FPGA IP는 구현하지 않았다. 실제 LTspice R/C 회로에서 IIR 앞/뒤 면적 수집 및 보상 위치를 비교했다: [LTspice 보고서](../analysis_results/todo_resolution_20261004/LTSPICE_REPORT.md).

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

검증 자료: [결과 요약](../analysis_results/virtual_gate_voltage_20261003/summary.json), [소프트웨어 재현 결과](../analysis_results/virtual_gate_voltage_20261003/software_results.json). 이 자료들은 현재 로컬 검증 산출물이다.

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

기존 증거: [RF duration 검증 보고서](../analysis_results/rc_precompensation_v1/rf_duration_oneshot_v1/REPORT.md), [AWG v2 RF duration + voltage RTL 결과](../analysis_results/awg_tuning_v2/rtl_evidence/rc_precomp_repeat_reset_rf_duration_20x20_exact_voltage_awg_v2.json).

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

검증 자료: [결과 보고서](../analysis_results/fir_dc_order_20261003/REPORT.md), [실제 RTL 출력 비교](../analysis_results/fir_dc_order_20261003/fir_dc_order_rtl.png), [DDR 수집 시각](../analysis_results/fir_dc_order_20261003/fir_dc_ddr_timing.png), [GUI 화면](../analysis_results/fir_dc_order_20261003/rf_readout_controls.png), [복구 무결성 검사](../analysis_results/fir_dc_order_20261003/recovery_integrity.json).

## 4. 설정 복원 후 Windows offscreen Qt 테스트 프로세스 종료 오류

- [x] 설정 파일을 불러온 MainWindow가 닫힌 뒤 Python/Qt 정리 단계에서 발생하는 native access violation을 조사하고 종료 순서 및 테스트 객체 수명을 수정한다.
- 2026-10-04 전원 중단 후 재검사에서 GUI assertion은 모두 통과했으나, 프로세스 종료 시 `0xC0000005`가 발생했다. `-X faulthandler` 출력에는 Python frame이 없다.
- 새 FIR/DC 코드 이전 GUI `610b9cc`의 `DCWaveform_Generator.py`를 별도 파일로 읽어 동일 환경에서 `MainWindow → save settings → load settings → close`를 실행해 같은 종료 오류를 재현했다. 단순 창 생성·close는 정상 종료였다. 체크아웃/브랜치를 변경하지 않았다.
- 여기서 사용한 환경은 Codex bundled Python/PyQt5와 `QT_QPA_PLATFORM=offscreen`이다. 실제 사용자 GUI 환경에서의 재현 여부 및 Qt 객체/타이머 수명 문제는 추가 확인이 필요하다. 시스템 전원 중단으로 파일이 손상되었다는 증거는 아니다.
- 새 RF Readout 패널과 FIR/DC timing dialog만 실행한 두 GUI 검사는 정상 종료했고, MainWindow 설정 복원 검사 및 기존 GUI 종합 검사는 종료 오류를 보였다. 실험 데이터·RTL 타이밍 검증과 이 종료 오류를 구분한다.
- 증거: [분리 실행 exit codes](../analysis_results/fir_dc_order_20261003/software_modules/exit_codes.json), [복구 확인](../analysis_results/fir_dc_order_20261003/RECOVERY.md).

**수정 및 재검사 — 2026-10-04**

- 실제 GUI 진입점에서 event loop 종료 후 MainWindow의 deferred deletion → Python 참조 순환 정리 → 소유한 QApplication 파괴 순서를 명시했다. `os._exit()`로 충돌을 숨기는 방식은 사용하지 않았다.
- headless 테스트도 생성한 MainWindow를 QApplication 수명 안에서 정리하도록 수정했다. 저장·복원 뒤 단순 `close()`만 호출하고 Python 종료에 객체 정리를 맡기던 경우와 구분했다.
- 별도 프로세스에서 실제 `main()` 진입점과 Qt event loop를 실행하여 설정 복원 0/1/5회 후 정상 exit=0을 확인했다. 기존 GUI 검사 78개와 FIR/DC 검사 53개도 각각 정상 종료했다.
- 최신 전체 회귀 결과는 [프로세스 종료 코드](../analysis_results/todo_resolution_20261004/software/exit_codes.json)에 보존한다. Windows offscreen 환경의 검사이며 실제 보드에 연결한 GUI 측정 시험은 아니다.
- 수정 후 관련 12개 테스트 모듈, 총 403개 검사를 통과했고 모든 테스트 프로세스의 종료 코드가 0이다.
- 이후 DC 최소 SET 간격 검사를 포함한 최종 소프트웨어 결과는 13개 모듈 413개 통과, 모든 프로세스 exit=0이다. 지원 불가 조건의 거부 검사와 지원 가능한 낮은 보상 전압 검사를 구분한다. [최종 exit codes](../analysis_results/todo_resolution_20261004/software_final/exit_codes.json).

## 5. Waveform Plot 확대·축소 시 시간 표시 단위 자동 전환

- [x] 현재 보이는 시간 범위에 맞춰 x축 표시 단위를 `ns / µs / ms / s`로 자동 전환한다. 눈금 간격뿐 아니라 눈금 숫자와 축의 단위 표기를 함께 갱신한다.
- 등록일: 2026-10-06 (America/Vancouver). 사용자 첨부 화면에서 확대·축소 후에도 `time [µs]` 단위가 유지되는 현상을 기준으로 한다.
- 2026-10-06 구현: 보이는 시간 폭을 기준으로 표시 단위를 선택한다. 1 µs 미만은 ns, 1 ms 미만은 us, 1 s 미만은 ms, 그 이상은 s로 표시한다. 입력칸의 시간 단위 선택과 Waveform Plot의 자동 표시를 분리했다.
- Virtual / Physical / RC compensation 곡선과 sweep 범위 표시 모두 같은 시간축 배율을 사용한다.
- 단위 전환은 표시만 변경한다. 내부 시간 데이터, 입력한 pulse duration, sweep 값, grid snapping 및 실제 출력 타이밍은 유지한다.
- 검증: 확대·축소 및 Fit 시 단위와 눈금 숫자가 일치하고, 동일한 파형 지점의 실제 시간이 바뀌지 않는지 확인한다. 단위 경계에서 반복 전환하거나 눈금이 겹치는 현상도 확인한다.
- 긴 파형의 뒤쪽을 확대할 때 기본 6자리 유효숫자 포맷으로 눈금 값이 중복되던 문제도 수정했다. 눈금 간격으로 소수 자릿수를 결정하며 내부 시간 데이터는 ns를 유지한다.
- 관련 GUI 회귀 검사 125개 통과, 프로세스 exit=0. 실제 Qt 휠 이벤트의 양방향 전환과 Fit, 단위 경계·pan·y축 확대, 입력 단위 변경, Virtual/Physical/RC/sweep 데이터 및 snapping 유지, 설정 복원 후 정상 종료를 확인했다. Windows offscreen GUI 검사이며 FPGA 변경은 없다.
- 검증 자료: [결과](../analysis_results/waveform_time_axis_20261006/REPORT.md), [GUI 화면](../analysis_results/waveform_time_axis_20261006/waveform_time_units.png), [휠 이벤트 기록](../analysis_results/waveform_time_axis_20261006/zoom_checks.json).

관련 코드: GUI `DCWaveformGeneratorGUI/dc_waveform_widgets.py`의 `WaveformPlotWidget`, `set_time_unit()`, `_refresh_grid_tick_spacing()` 및 view range 변경 처리.

## 6. DAC 전류: 포트별 실제 readback과 편집값 분리

등록 / 조사일: 2026-10-23. 아래 6~8번은 현재 로컬 v6 관련 소스와 오프라인 재현을 조사한 후속 작업이다. 기존 문서 상단의 v2/v3 이력과 구분한다. **구현·FPGA 배포·실물 검증은 아직 수행하지 않았다.**

**확인한 동작과 재현 범위**

- 보드의 `DacCurrentControl.get_dac_current_settings()`는 RFDC의 물리 DAC별 `OutputCurr`를 읽는다. 단위는 µA이며 DAC full-scale 전류 설정의 readback이다. 부하에 순간적으로 흐르는 전류 측정값이 아니다. 상태는 `DacCurrentState.records[converter_id]`에 저장되므로 모든 포트가 하나의 전류값을 공유하는 구조는 아니다. 같은 물리 DAC로 합산되는 RF/AWG generator들은 전류 설정을 공유한다.
- 프론트패널의 전류 편집 위젯은 하나를 재사용한다. 포트 선택 시 `_refresh_current()`가 해당 DAC의 **캐시된 readback**을 표시하지만, 선택할 때마다 새 하드웨어 조회를 하지는 않는다. 전류 쓰기는 별도 Apply 요청에서 대상 converter ID와 요청값을 함께 전달한다.
- 실제 위젯과 상태 클래스를 사용한 오프라인 재현에서, 유효한 두 DAC를 선택하면 29.968 → 19.993 mA로 표시가 바뀌며 전류 쓰기 요청은 발생하지 않았다. 이전 포트의 미적용 편집값도 다른 유효 포트로 전달되지 않았다.
- 반면 미매핑 포트 또는 `current_ua=None`인 포트를 선택하면 전류 입력과 Apply가 비활성화되지만 **이전 29.968 mA 숫자가 남았다.** 이 표시 결함은 재현했다. 이것만으로 실제 다른 DAC에 전류가 쓰였다고 판단하지 않는다.
- 설정 JSON을 불러오는 `_apply_settings()`는 저장된 `dac_current_settings`를 공유 상태에 넣는다. 현재 실제 readback과 저장 당시 snapshot을 구별하는 freshness/provenance가 부족하다. 기존 configuration이 있으면 프론트패널을 다시 열어도 자동 Identify를 생략하는 경로도 있다.
- 실행 직전 `verify_current_settings()`는 새 readback을 컴파일 당시 snapshot과 비교한다. 불일치 또는 읽기 불가 시 첨부 화면의 오류를 내는 보호 기능이며 유지해야 한다. 사용자 당시의 실제 원인은 현재 증거만으로 확정하지 않는다. 오래된 snapshot, 외부 변경, 읽기 실패, 논리 generator와 물리 DAC의 대응을 구분해 진단해야 한다.
- 오류의 `DAC 12`는 이 코드에서 RFDC converter ID `"12"`(tile 1 / block 2)를 뜻한다. 프론트패널의 SMA 번호 12와 동일하다고 해석하면 안 된다.

**수정할 작업**

- [ ] 상태 키를 연결 대상·펌웨어 식별·물리 converter ID 기준으로 관리하고, 실제 readback / 요청값 / 미적용 편집값 / 조회 시각 / 오류를 분리한다. 저장 JSON의 값은 과거 snapshot으로 표시하고 실제 장비 상태를 덮어쓰지 않는다.
- [ ] 포트 선택 시 해당 DAC의 최신 상태를 비동기로 조회하거나, 캐시임을 명확히 표시하고 Refresh를 제공한다. 미매핑·읽기 불가 상태는 숫자 대신 `— / N/A`로 표시한다. 이전 포트 숫자를 실제값처럼 남기지 않는다.
- [ ] 전류 쓰기는 명시적 Apply에서만 수행한다. 요청 당시의 연결 세대·물리 DAC ID·요청값을 고정하고, 늦게 도착한 응답을 새로 선택한 다른 포트에 적용하지 않는다. 쓰기 후 실제 양자화된 readback을 표시한다.
- [ ] 전류 변경에 따른 컴파일/교정 캐시 무효화와 재컴파일을 유지한다. 입력한 전압값을 임의로 바꾸거나 current mismatch 검사를 없애서 해결하지 않는다. 모든 사전 검증은 DDR arm 전에 수행하고, arm 이후 오류도 7번 공통 cleanup으로 처리한다.
- [ ] 오류에 SMA 번호, RFDC ID, generator aliases, expected/actual µA, 읽기 오류, snapshot 출처·시각을 표시한다. 단순 변경과 readback 실패를 다른 메시지로 구분한다.
- [ ] 회귀 검증: 사용/미사용 매핑 포트, 미매핑 포트, 읽기 실패, pending 편집, 빠른 포트 전환과 지연 응답, JSON 로드, 같은 물리 DAC의 RF/AWG aliases. 포트 선택만으로 하드웨어 쓰기가 0회인지 확인한다. 실물에서는 서로 다른 두 DAC의 전류가 독립적으로 유지되는지 별도 확인한다.

관련 코드: GUI `qick_front_panel.py`의 `_refresh_current`, `_request_current`, `_select_port`; `qick_dac_current.py`의 `DacCurrentState`, `verify_current_settings`; `DCWaveform_Generator.py`의 `QickConfigurationWorker`, `_apply_settings`, `_identify_qick_configuration`. 보드 [dac_current.py](../qick/qick_lib/qick/dac_current.py).

참고: [AMD XRFdc_GetOutputCurr](https://docs.amd.com/r/en-US/pg269-rf-data-converter/XRFdc_GetOutputCurr)는 tile/block별 전류 readback API를 설명한다. 실제 GUI 경로 판단은 위 로컬 소스를 기준으로 했다.

## 7. Cancel 후 DDR busy 및 출력 잔류: 공통 정지·복구 경로

등록 / 조사일: 2026-10-23. **Run forever를 활성화하기 전에 완료해야 하는 우선 작업.**

**확인한 누락과 오류의 의미**

- GUI Cancel은 worker의 취소 event를 설정한다. `acquire_fir_ddr()`에는 arm부터 종료까지를 소유하는 하드웨어 cleanup `finally`가 없고, `_run_rounds_with_counter_progress()`의 `finally`는 실행 중 tProcessor만 정지한다. 이 정지의 예외도 현재 무시한다. QCoDeS의 별도 finally는 일부 SquarePulse 정지만 담당한다.
- 오프라인 fake SoC 재현: DDR arm 직후 취소하면 abort 호출 없이 캡처가 armed로 남는다. 카운터 대기 중 취소해도 `stop_tproc()`만 호출되고 DDR은 armed로 남는다. 다음 `arm_samples()`에서 첨부 화면과 같은 `cannot re-arm ... previous capture is busy` 오류가 발생한다.
- DDR v3 RTL은 arm 시 busy를 설정하고, 요청한 마지막 trigger의 마지막 AXI 쓰기 응답까지 받아야 정상 해제한다. 따라서 Cancel로 남은 trigger가 오지 않으면 캡처가 끝나지 않을 수 있다. 이 busy는 PC가 파일/DDR 데이터를 읽는 중이라는 뜻이 아니다. 실제 당시 상태가 trigger 대기인지 AXI 쓰기 대기인지는 별도 status/trace가 필요하다.
- **두 첨부 오류가 연결되는 경로도 있다.** 현재는 DDR arm 후 `config_all()`에서 DAC current를 재검증한다. 여기서 current mismatch가 발생하면 tProcessor 시작 전, 그리고 해당 실행 함수의 try 진입 전에도 빠져나간다. 즉 Cancel 없이도 arm된 DDR에 trigger가 오지 않아 다음 실행의 busy 오류를 만들 수 있다. 이는 소스에서 확인한 경로이며 사용자 당시 원인으로 확정한 것은 아니다.

**AXI 정지 / reset 기능의 현재 범위**

| 대상 | 현재 로컬 소스의 기능 | 한계 / 필요한 처리 |
| --- | --- | --- |
| DDR sample v3 | AXI control word 0의 bit 1(`0x2`) soft reset이 존재한다. bit 2(`0x4`)는 sticky 상태 clear이다. | 드라이버의 공개 capture-abort 경로가 없다. `0x4`나 `force_overwrite`로 busy를 해제할 수 없다. 현재 soft reset은 진행 중인 AW/W valid와 write-active를 즉시 내리므로, AXI 거래 중 임의 호출을 안전한 Cancel 구현으로 채택하면 안 된다. |
| AWG tuning v4 | `override_current(0)`으로 AXI 출력 코드 override가 가능하다. 내부 ramp 중단, 명령 파이프라인 flush, 0 override의 DC/RC 정리 경로가 있다. | 여기서 current는 **현재 출력 sample 값**이며 DAC full-scale 전류(mA)가 아니다. 상위 tProcessor/TMUX에 남은 명령의 재유입을 막고 CDC ack·idle·출력 상태를 확인해야 한다. |
| Square DDS | `AxisSquarePulse.mute()` / `stop_square_pulse()`의 AXI mute가 있다. | CDC/파이프라인 지연 뒤 출력이 0이 된다. producer를 먼저 막아 새 명령이 재활성화하지 못하게 해야 한다. DDS phase accumulator 정지와 출력 mute는 다르다. |
| 일반 RF DDS (`axis_signal_gen_v6`) | `reset_gens()`가 tProcessor에 최소 zero-gain 프로그램을 실행한다. | 이 IP에 독립 AXI mute는 현재 없다. `reset_gens()`만으로 별도 AWG tuning IP까지 정리되지 않는다. tProcessor가 응답하지 않아도 확실히 끄려면 RF/AWG 합산 경로를 포함한 AXI mute/gate 확장이 필요하다. |
| tProcessor v1 | `stop_tproc(lazy=False)`는 PMEM reset/reload로 실행을 정지시킨다. | DDR·DDS·AWG 전체 reset이 아니다. 예약된 출력 명령/FIFO까지 취소됐다고 가정하면 안 된다. v1에서 lazy stop에 의존하지 않는다. |

**수정할 작업**

- [ ] 보드 측 실행 소유권과 `IDLE → PREPARING → ARMED/RUNNING → STOPPING → IDLE 또는 ERROR_LOCKED` 상태를 도입한다. 검증된 idle 전까지 Run/재arm/관련 설정 변경을 막는다. GUI의 취소 signal 수신만으로 재실행 가능 상태로 바꾸지 않는다.
- [ ] current/readout/메모리/펌웨어 capability 검증과 프로그램 준비를 arm 전에 끝낸다. arm부터 실행·readback까지 하나의 `try/finally`가 소유하고, 취소·검증 오류·RPC 오류·창 종료 모두 공통 cleanup을 거친다. 정상 완료도 tProcessor counter뿐 아니라 DDR done·쓰기 완료를 확인한다.
- [ ] 먼저 새 tProcessor/외부 시작 및 trigger 공급을 차단한다. 예약 명령의 잔류 여부를 검증하고 AWG zero override, Square mute, 일반 RF zero 프로그램을 조합한다. 필요한 경우 출력단에 명시적으로 해제하기 전까지 유지되는 AXI mute를 추가해 늦은 명령으로 재출력되는 것을 차단한다. 모든 합산 경로와 marker도 검사한다.
- [ ] DDR에 **graceful abort**를 구현한다. 신규 trigger/sample 및 신규 쓰기 발행을 중단하되 이미 발행한 AW/W 거래와 B 응답은 끝까지 처리하고, 이후 미발행 부분 데이터·FIFO·trigger queue를 정리한다. CDC별 abort ack, idle, outstanding-write 상태, aborted/partial 카운트를 노출한다. busy=0만으로 버스가 정리됐다고 판단하지 않는다.
- [ ] 기존 `0x2` soft reset은 거래가 없는 상태에서의 사용 조건과 검증을 먼저 확립한다. trigger 대기와 AW/W/B stall을 구별할 수 없는 현재 인터페이스에서 무조건 reset 후 rearm하지 않는다. timeout 시 원인과 부분 데이터/상태를 보존하고 ERROR_LOCKED로 남긴다. 보드 전체 재설정·bitstream 재적재는 정상 Cancel 대안으로 자동 실행하지 않는다.
- [ ] cleanup 오류를 삼키지 않고 최초 오류와 함께 보고한다. bounded timeout과 재진입 가능한 cleanup을 만들고, 정지 확인 전 완료/취소 완료로 표시하지 않는다. 취소된 데이터는 완료 데이터와 구분하며, reset 전 확보한 진단과 유효한 저장 자료를 보존한다.
- [ ] 기본 정지 상태는 출력 zero/mute이고, 기존 설정은 다음 명시적 Start를 위해 보존한다. 중단 전 펄스나 DDS를 자동 재시작하지 않는다. 사용자 nonzero bias 복원이 필요하면 별도 명시적 정책으로 처리한다. DC 보상 도중 끊긴 물리적 면적을 디지털 reset만으로 상쇄했다고 주장하거나 임의 보상 펄스를 추가하지 않는다.
- [ ] 새 API의 지원 여부를 HWH/IP 버전으로 검증한다. 디지털 ack/readback과 실제 아날로그 0 V를 구분하고, 실물 acceptance에는 oscilloscope로 잔류 출력·늦은 재출력이 없는지 확인한다.
- [ ] 회귀/RTL 검증: arm 직전·직후, 첫 trigger 전, trigger 중간, AW 또는 W만 handshake된 상태, B 응답 stall, 마지막 sample, readback 중, DAC 검증 실패, RPC 실패, 반복 Cancel→Run. AW/W VALID 유지, outstanding 거래 배출, DDR 재arm, AWG/RF/Square/marker zero, 긴 예약 출력, RC/DC 상태, 정상 finite 실행을 함께 검사한다. 기존 테스트의 `stop_tproc` 호출 확인만으로 완료 처리하지 않는다.

관련 코드: GUI `qick_fine_tune_sweep.py`의 `config_all`, `_run_rounds_with_counter_progress`, `acquire_fir_ddr`; `DCWaveform_Generator.py`의 `QickExperimentWorker`, `_stop_qick_experiment`, `_on_experiment_cancelled`; `qick_qcodes_experiment.py`의 SquarePulse finally. 보드 [readout.py](../qick/qick_lib/qick/drivers/readout.py), [DDR v3 RTL](../qick/firmware/ip/axis_buffer_ddr_sample_v3/src/axis_buffer_ddr_sample_v3.sv), [awg_tuning.py](../qick/qick_lib/qick/awg_tuning.py), [square_pulse.py](../qick/qick_lib/qick/drivers/square_pulse.py), [qick.py](../qick/qick_lib/qick/qick.py).

참고: [AMD AXI protocol checks](https://docs.amd.com/r/en-US/pg267-axi-vip/AXI-Protocol-Checks-and-Descriptions)의 handshake 전 VALID 유지 조건 때문에 local soft reset을 거래 중 안전한 abort와 동일시하지 않는다. [QICK reset_gens 문서](https://docs.qick.dev/latest/_autosummary/qick.qick.html#qick.qick.QickSoc.reset_gens)는 zero-gain 프로그램 방식을 설명한다. 이 저장소의 custom AWG/DDR 동작은 로컬 소스가 기준이다.

## 8. AWG Tuning: RF acquisition 없는 Run forever

등록 / 조사일: 2026-10-23. **가능한 기능이지만 아직 구현되지 않았으며, 7번의 검증된 정지·재실행 기능을 먼저 완료한다.**

**구현 가능성과 loop 방식**

- backend sequence/program 생성은 `readout=None`, `ddr_readout=None`을 표현할 수 있다. 현재 GUI Start experiment의 유한 acquisition/저장 경로와 분리한 출력 전용 실행 경로가 필요하다. RF 출력 펄스와 RF Readout의 ADC 측정은 별개이다.
- 현재 assembly는 `FINE_TUNE_POINT → reps 초기화 → FINE_TUNE_REP → shot → loopnz → sweep 축 갱신 → end` 순서이다. 반복 레지스터에 1을 더한 뒤 `loopnz`로 1을 빼는 제안은 단일 shot의 무한 반복 방식으로 가능하다.
- 다만 그 수정을 **현재 내부 rep loop에만** 넣으면 sweep 축 갱신에 도달하지 않아 첫 voltage/duration 지점만 무한 반복한다. sweep 전체를 반복하려면 유한 reps/전체 grid 바깥에 반복 loop를 두고 축 값·카운터·DMEM 포인터 등을 매 cycle 정확히 초기화해야 한다. 큰 reps 값을 지정하는 방식은 진짜 forever가 아니다.

**수정할 작업**

- [ ] 기존 Start experiment는 유한 측정·저장으로 유지하고 별도 `Run forever` / `Stop`을 추가한다. 진행률은 총 rep 수 기반 퍼센트 대신 실행 시간·완료 cycle/shot 등 제한된 상태값으로 표시한다.
- [ ] `execution_mode=output_forever`를 설정·생성 Python·컴파일 캐시 키·실행 메타데이터에 명시한다. 유한 acquisition용 캐시와 혼용하지 않는다. readout이 없을 때도 정상 컴파일/출력이 가능하도록 GUI 검증을 분리한다.
- [ ] forever에서는 활성화된 RF Readout/ADC acquisition(DDR, averaged/decimated 등)이 하나라도 있으면 **arm/start 전에 명확한 오류**로 거부한다. GUI뿐 아니라 backend 및 생성 Python에도 같은 검사를 둔다. 측정을 몰래 끄거나 무한 데이터를 버리는 방식으로 우회하지 않는다. 비활성화된 저장 설정과 활성 측정 요청은 구별한다.
- [ ] 출력 전용 worker는 DDR arm·ADC capture trigger·readout streaming·QCoDeS 측정 행 저장·무한 파형 buffer 할당을 하지 않는다. 시작/종료 및 설정 등 제한된 메타데이터는 보존한다. RF 출력과 사용자 외부 marker는 필요하면 유지하되 정지 시 함께 정리한다.
- [ ] sweep이 없으면 완전한 한 shot을 반복하고, sweep이 있으면 명시한 유한 reps × 전체 grid를 반복하는 정책을 기본으로 한다. 고정 선택 지점 반복을 제공한다면 별도 선택지로 표시한다. 축 초기화, 계수 포인터, RF tables, phase 정책을 검사한다.
- [ ] shot 끝의 출력 종료·DC compensation·RC repeat reset·recovery·동기화 경계를 보존한다. 무한 분기가 보상이나 종료 절차를 건너뛰지 않게 한다. 기존 finite 전용 epilogue/count 처리도 분리한다.
- [ ] 정상 Stop은 가능한 shot 경계에서 cleanup으로 분기하고, 응답 불가/장시간 trigger 대기는 7번의 독립 정지 경로로 처리한다. 호스트 연결 단절에도 지속 출력이 방치되지 않도록 보드 실행 소유권·watchdog 정책을 구현한다. 안전한 idle 확인 뒤에만 다시 Start를 허용한다.
- [ ] 검증: output-only 설정/컴파일, readout 요청 거부와 하드웨어 호출 0회, 단일 shot 및 전체 sweep 반복, counter/time-reference wrap, 짧은 shot의 명령 공급 여유·FIFO, 긴 RC/DC 펄스, 임의 phase에서 Stop→재실행, 연결 단절. 행동 모델·실제 RTL·승인된 낮은 출력의 실물 순으로 확인한다. 소프트웨어 모델의 반복 성공을 무한 실물 동작 보장으로 표현하지 않는다.

관련 코드: GUI `DCWaveform_Generator.py`의 `_experiment_run_arguments` 및 실행 worker; `qick_fine_tune_sweep.py`의 `make_program`, `_emit_point`, `FINE_TUNE_REP`, sweep 축 loop; `qick_qcodes_experiment.py`의 acquisition/저장 경로. `loopnz` 동작은 로컬 tProcessor 모델/RTL을 기준으로 확인했다.

**이번 조사 증거와 제한 (6~8번 공통)**

- 오프라인 재현 [offline_probe_result.json](F:/QICK_Private_Analysis/gui_stop_forever_review_20261023_080516Z/offline_probe_result.json), [실행 코드](F:/QICK_Private_Analysis/gui_stop_forever_review_20261023_080516Z/offline_probe.py)에 입력·호출 기록과 소스 SHA를 보존했다.
- 실제 GUI 위젯/상태 및 취소·arm 메서드를 synthetic configuration/fake SoC로 검사했다. 장비 RPC, 전류 쓰기, reset, 출력, 무한 실행은 하지 않았다. 사용자의 당시 세션 자체나 실물 AXI 중단 race를 재현한 결과는 아니다.
- 구현 완료로 체크한 항목은 없다. 작업 순서는 6번 표시/상태 교정과 7번 정지·복구를 우선하고, 7번 acceptance가 끝난 뒤 8번을 활성화한다. 관련 생산 소스·기존 실측 자료·자동화 상태는 변경하지 않았다.

## 9. Grouped sweep 약 60점에서 GUI 지연: 조사 결과와 수정 TODO

등록: 2026-10-27 UTC / 2026-10-26 PDT. **사용자 요청에 따라 조사·기록만 했으며 생산 코드는 수정하지 않았다.** 기존 TODO 변경도 보존했다.

### 재현 범위와 측정

실제 `MainWindow`를 offscreen/Fusion으로 생성하여 `_notify_sweep_state_changed(fit_view=True)`를 호출했다. 전압 2개와 RAMP 시간 sweep을 묶고 DC/RC 보상을 켠 합성 입력이다. socket 연결을 차단했으며 장비 접속·컴파일 실행·실물 출력은 없다. 사용자의 당시 저장되지 않은 설정 자체를 재현한 것은 아니다.

| 한 그룹의 점 수 | 전압 2개만 묶음 | 전압 2개 + RAMP 시간 묶음 |
| --- | ---: | ---: |
| 10 | 22.5 ms | 80.5 ms |
| 30 | 17.1 ms | 353.3 ms |
| 60 | 18.0 ms | 1,144.2 ms |

위 표는 **cProfile을 끈 단일 갱신 실측 시간**이다. 둘 다 실제 sweep shape는 `(N,)`이다. 60점 한 그룹이 잘못 60×60으로 풀려서 생긴 지연은 이 재현에서는 아니다. 별도의 cProfile 측정에서 60점 시간 포함 그룹은 4.313초였으며, profiler 비용이 있으므로 표와 섞어 해석하지 않는다. 시간 포함 독립 그룹 2개를 각 30점으로 설정한 경우에는 합법적으로 `(30, 30)` / 900점이 되어 profiler 사용 시 65.283초였다. 추가 60×60 진단은 비용을 제한하기 위해 해당 오프라인 진단 프로세스만 종료했고, 그 경우의 완료 시간은 보고하지 않는다.

### 확인한 병목

1. `DCWaveform_Generator.py:11486,12623–12680,12339`의 sweep 변경 signal이 GUI 스레드에서 `_synchronize_sweep_views → _refresh_sweep_overlay → _refresh_physical_waveforms`를 동기 실행한다. 갱신 1회가 끝날 때까지 일반 UI 이벤트 처리가 지연된다. 해당 동기 경로에 변경 요청 병합·취소 또는 debounce가 없다.
2. `qick_rc_validation.py:sweep_corners`는 **duration과 voltage가 연동된 그룹의 내부 면적 극값**을 놓치지 않도록 그 그룹의 모든 index를 검사한다. `build_qick_sequence → validate_channel_voltage_ranges`의 nominal/DC 검사와 `_refresh_physical_waveforms → validate_sequence_rc_range`의 RC 검사가 각각 이 지점들을 순회한다. 이는 필요한 안전 검사이며 단순히 양 끝점만 보거나 검사를 삭제하는 최적화는 금지한다.
3. `qick_fine_tune_sweep.py:490–519,1782,1883`에서 `sweep_coordinate()`가 한 좌표를 요청해도 각 axis의 `.points` 전체 tuple을 다시 만든다. `RampDurationSweep.duration_cycles_points`는 N개를 만들며 각 원소마다 `start_cycles`와 `duration_step_cycles`를 재평가하고, 후자는 다시 start/stop의 clock 변환을 수행한다. `segment_duration_cycles_at()`도 전체 duration tuple을 만들어 한 원소만 선택한다. 결과적으로 전체 N점 검사 내부에 반복적인 N점 생성이 들어간다.
4. 60점 단일 그룹 profiler에서 `duration_cycles_points` **2,497회 / 누적 3.665초**, `clock_cycles` **449,478회 / 누적 3.006초**, `_refresh_physical_waveforms` **4.305초**가 관찰됐다. 누적 시간은 서로 포함되므로 합산하면 안 된다. 이 재현의 주된 병목은 하드웨어 대기나 행 60개의 표 그리기가 아니라, GUI 갱신 중 반복되는 duration/좌표 계산과 보상 범위 검사이다. RF·복잡한 segment·다른 설정에서는 추가 병목이 있을 수 있다.

### 수정할 작업 — 모두 미구현

- [ ] immutable sweep axis의 `start_cycles`, `step_cycles`, quantized duration/points를 한 번 계산해 재사용하거나, 선택 좌표를 `start_cycles + index * step_cycles`로 O(1)에 평가한다. start/stop/count/fabric clock 및 group 수정 시 정확한 무효화·재생성을 보장하고, 기존 정수 반올림·실행 마지막 값 의미를 유지한다. 표시용 이상 stop으로 대체하지 않는다.
- [ ] sequence의 group 대표축·model shape·point index를 한 갱신 안에서 재사용한다. 같은 point의 nominal/DC/RC 계산에서 공통 좌표·segment duration·면적 계산을 재활용하되, 서로 다른 물리 범위 검사를 생략하지 않는다.
- [ ] UI 변경을 묶어 한 번 갱신하고, 연속 편집에는 짧은 debounce 및 revision ID를 둔다. 선택 파형 미리보기와 전체 범위 검사를 구분해 전체 검사는 immutable snapshot 기반 worker에서 수행한다. 이전 revision의 결과가 최신 UI를 덮지 않게 한다. Qt widget 조작은 GUI 스레드에 남긴다.
- [ ] 전체 검사가 미완료·실패인 동안 실행 가능한 상태로 표시하지 않는다. Start/export/backend의 최종 동일 설정 검증을 유지하며, 취소·timeout 상태를 성공으로 바꾸지 않는다.
- [ ] duration 포함 여러 독립 그룹의 검사 비용은 그룹별 count의 곱이 될 수 있음을 UI에 표시하고, 진행/취소를 제공한다. 지점 간 상관관계에 따른 내부 극값을 유지하는 검증된 수학적 상한 또는 정확한 재사용 없이는 corner 수를 임의 축소하지 않는다.
- [ ] 회귀 검증: 전압만 / voltage+RAMP / voltage+HOLD / RF duration 혼합, 1·10·30·60·100점, 한 그룹 및 두 독립 그룹, DC 두 모드·RC ON/OFF, cross-capacitance, interior headroom 위반, compile binary/quantized coordinate 불변, 빠른 연속 편집·group/ungroup·취소·오래된 worker 결과 폐기. UI 응답 시간과 계산 시간을 분리 측정하고 profiler 없는 반복 시간으로 성능을 비교한다.

증거: [profiler 없는 측정](F:/QICK_Private_Analysis/grouped_sweep_lag_20261027_0212/attempt04_unprofiled/result.json), [함수별 profiler 결과](F:/QICK_Private_Analysis/grouped_sweep_lag_20261027_0212/attempt02/progress.json), [진단 코드](F:/QICK_Private_Analysis/grouped_sweep_lag_20261027_0212/attempt04_unprofiled/profile_gui.py). 소스 SHA와 초기 준비 오류도 F:에 보존했다. 첫 진단의 잘못된 compensation enum 및 profiler를 끈 뒤 빈 Stats를 읽은 준비 오류는 유효 성능 결과에서 제외했다. 생산 GUI를 보이는 창으로 열거나 하드웨어 측정 코드를 변경한 결과가 아니다.


## 10. v6 GUI 수정 결과 — 2026-10-27 UTC

사용자가 이후 GUI 수정·확인을 승인한 범위의 결과입니다. **Cancel 처리는 명시적으로 제외했으며, 7번 및 8번은 미구현 상태를 유지합니다.** 장비 접속·출력·드라이버·RTL·FPGA 배포 없이 offscreen Qt와 fake SoC로 확인했습니다. 사용 중인 데스크톱 GUI를 띄우거나 재시작하지 않았습니다.

### 시간 단위 및 시간 sweep 표시

- [x] `us`에 PyQtGraph의 milli 접두사가 붙어 `mus`로 보이는 문제를 수정했습니다. 시간축 눈금만 seconds 기준으로 변환하여 올바른 `ns / µs / ms / s`를 표시합니다. 모든 입력칸을 ns로 고정하는 변경은 아니며, 원래 곡선·이미지 좌표와 저장값·실행 시간은 유지합니다. 시간축을 전압축으로 전환하면 표시 배율도 복원합니다.
- [x] RAMP/HOLD 설정 창과 시간 sweep 목록에 시작·요청 끝·실제 적용 끝·step·점 수를 표시했습니다. RAMP/HOLD의 step과 적용 끝은 컴파일러의 정수 클록 반올림으로 계산합니다. RF/software 시간축의 값은 요청 step으로 구분하며, 여기서 계산하지 않은 하드웨어 양자화를 실측 또는 확정값처럼 표시하지 않습니다.
- [x] 예: 300 MHz, 0.1→1 µs, 100점은 실제 step 3클록(10 ns), 실제 끝 1.09 µs입니다. 기존 컴파일 규칙을 바꾸지 않고 요청값과 적용값의 차이를 보여줍니다. 시간축 `mus→ns`, 설정 dialog와 sweep table의 실제 offscreen 이미지를 직접 확인했습니다.

### 6번 DAC 전류 중 완료한 GUI 범위

- [x] 선택 포트에 매핑/readback이 없으면 이전 포트의 숫자를 남기지 않고 `N/A`와 Apply 비활성화를 표시합니다. 유효한 포트 전환과 미적용 편집값 변경만으로 전류 쓰기가 발생하지 않음을 검사했습니다.
- [x] 요청 전류와 물리 DAC ID/gen별 마지막 readback을 분리하고, 하드웨어 조회 시각·저장 snapshot·읽기 불가 출처를 표시합니다. 동일 연결 대상의 실제 readback을 설정 JSON의 과거값으로 덮어쓰지 않습니다.
- [x] Identify 도중 쓰기 비활성화, 연결 대상 불일치 시 Apply 거부, 이전 연결의 지연 응답 폐기, 읽기 실패 시 routing 유지 및 current unavailable 처리를 추가했습니다. 컴파일 직전 mismatch 보호는 유지하고 expected/actual µA와 generator aliases를 오류에 추가했습니다.
- [ ] 펌웨어/연결 세대까지 포함한 완전한 상태 식별, 모든 오류의 SMA·상세 원인·시각 통합, 두 물리 DAC의 실물 독립성 검증은 남아 있습니다. 캐시 표시가 매 포트 선택 시 새 하드웨어 조회를 뜻하지는 않습니다.

### 9번 grouped sweep 지연 중 완료한 범위

- [x] immutable axis의 클록 변환·duration/points를 캐시하고, 현재 count/group signature에 따른 layout 캐시를 제한된 크기로 재사용합니다. axis 교체·group 변경·순서 변경을 반영하며 내부 안전 검증 지점은 줄이지 않았습니다. 파생 캐시값은 컴파일의 의미상 cache key에서 제외하여 preview 조회만으로 cache miss가 나지 않게 했습니다.
- [x] 같은 오프라인 전압 2개+RAMP 그룹 조건에서 warm median 갱신 시간: 60점 1.141→0.155초, 100점 2.891→0.253초. 3점·10점의 컴파일 binary/DMEM/양자화 좌표/명령 실행 모델 출력 SHA가 수정 전과 같았습니다.
- [ ] debounce·전체 검사 worker·여러 독립 그룹의 큰 Cartesian grid 비용 처리는 아직 구현하지 않았습니다. 모든 grouped sweep 지연이 해결됐다고 표시하지 않습니다.

검증: 관련 11개 테스트 모듈 **377개 통과**, 종료 코드 0. 단위 전환·시간 sweep·DAC 상태·그룹 캐시·컴파일 캐시·기존 RC 범위 검사를 포함합니다. 실물 검증 결과는 아닙니다. Cancel/정지 메서드·실행 worker와 DDR arm/acquisition 함수의 AST는 작업 전과 동일하며, `qick_qcodes_experiment.py`도 작업 전 바이트와 같습니다.

자료: [수정 전후 코드 설명](F:/QICK_Private_Analysis/gui_v6_host_fixes_20261027_035716Z/TIME_DISPLAY_CODE_REVIEW.md), [정확한 변경 패치](F:/QICK_Private_Analysis/gui_v6_host_fixes_20261027_035716Z/changes_from_before.patch), [검증 및 성능 보고서](F:/QICK_Private_Analysis/gui_v6_host_fixes_20261027_035716Z/REPORT.md). 원래 있던 미커밋 변경은 작업 시작 사본과 비교하여 보존했으며 Git commit/push는 하지 않았습니다.
