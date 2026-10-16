# Simple current-feature GUI/compiler/model verification

38개 계획의 최종 결과는 **정상 PASS 29, 예상 경계 거부 4, 실제 수치 실패 1, 예상외 컴파일 거부 2, GUI 입력 미지원 2**입니다. 전체 PASS가 아닙니다.
모든 최종 case subprocess는 exit 0으로 종료했습니다. 기능 판정은 프로세스 종료 코드와 별도로 위 결과로 분류했습니다.

## 범위와 근거

새 비공개 offscreen MainWindow에서 Qt 마우스/키보드로 전압·시간·행렬·sweep 입력을 commit하고 `_experiment_run_arguments` → 실제 runtime compiler → TProc 실행모델로 검사했습니다. 하드웨어 정보는 실제 v5 candidate HWH route를 적용한 offline metadata이며, 보드 발견/접속/업로드/아날로그 측정은 하지 않았습니다.
정상 29개에서 75 shots, AWG 1125개 명령 검사, RF 126개 이벤트 검사를 완료했습니다. 실패한 RAMP의 추가 1 shot도 전체 model_commands가 보존됩니다. 생산 Python 170파일의 전후 SHA256이 같고 각 case의 runner snapshot SHA256도 모두 일치합니다.
요청 타임라인·C@V·DAC code 양자화 기대값은 입력 specification에서 독립 계산했습니다. GUI committed 값, 요청/양자화 정수 cycle, 실제 TProc 명령을 분리해 기록했습니다. 모든 point/repetition/3출력의 명령·참조를 보존했고, 실제 측정 파형으로 표현하지 않았습니다.

## 발견한 문제

- `log_ramp_02`: 앞 RAMP 0.464158883361 µs 입력 후 뒤 RAMP를 정확히 1 µs로 입력했지만 세 AWG 모두 301 cycles/4,816 samples로 컴파일되었습니다. 기대값은 300 cycles/4,800 samples이며 초과는 1 cycle = 3.333333 ns입니다. GUI의 절대 경계 차분이 `1000.0000000000005 ns`, cycle이 `300.0000000000001`이 되어 core helper의 `ceil`이 301로 올립니다. 원본 ASM 146/154/162행과 실행 명령에서 확인했습니다. 생산 수정이나 검사 허용오차 완화는 하지 않았습니다.
- `rf_fine_crossing_False`, `rf_fine_beyond_final_False`: `require_within_segment=False`를 실제 commit했지만 `qick_rf_fine_duration.py:360`의 공유 포트 순서/3클록 간격 가드에 거부됩니다. 이 입력에서는 tail 시간이 sweep에 따라 뒤의 AWG 명령을 지나므로 고정 명령 순서 검사의 제약과 부합합니다. 개별점 또는 모든 outside-HOLD fine 출력이 불가능하다고 일반화하지 않습니다. 원래 범위/시간은 변경하지 않았고 두 case는 PASS가 아닙니다. 동일 coarse 범위 False는 통과했습니다.
- `set_only_identity`, `set_only_mixed`: current GUI PulseSequence는 strictly increasing times와 positive incoming ramp를 요구하므로 정확히 0시간 transition의 SET-only 입력은 미지원입니다. mixed 원본 두 시도는 invalid-edit QMessageBox 경로에서 access violation(-1073741819)이 발생했습니다. 메시지박스 안의 crash 원인은 별도로 확정하지 않았으며 단순 환경 오류로 분류하지 않았습니다. identity는 같은 입력 제약으로 실행하지 않았습니다.

## coverage

- HOLD log grid 10점(0.1…100 µs): 10/10 PASS. RAMP 동일 grid: 9 PASS + 위 수치 실패 1. 이는 10개씩의 개별 GUI 설정/컴파일이며 한 번의 hardware logarithmic sweep이라고 주장하지 않습니다.
- Matrix identity/nonidentity를 log cases에서 번갈아 적용했고 3출력의 서로 다른 +/- 전압, 비대각 matrix C@V를 확인했습니다. Voltage asc/desc 3점 및 N=1, reps=2는 3/3 PASS입니다.
- RF frequency 80/100/120 MHz, reps=2: DDS register 비교 PASS. 3RF 쌍 모두 AWG main HOLD 대비 +100 ns 명시 offset을 실제 명령 cycle에서 검사했습니다. 아날로그 주파수 추정은 미수행입니다.
- Coarse/fine 각각 inside/crossing/beyond-final × require true/false: 12 cases. 첫 sweep point는 inside이고 후반만 초과하는 true 4건은 구체적 HOLD 범위 오류로 거부되어 negative PASS입니다. Fine crossing/beyond false 2건은 별도 제약 거부입니다. Fine inside의 plateau/tail mode·gain·시각·BRAM envelope 활성 sample 수는 독립 요청 수와 비교했습니다.
- RF 자체의 10점 logarithmic grid, grouping, register arithmetic 구현, cancellation/timeout, compensation/ADC/FIR/보드 아날로그 검사는 이번 기본 범위에서 미수행/미지원입니다. 대표 실제 GUI→RTL 네 묶음은 별도 `../rtl` 보고서를 따릅니다.

## 초기 시도와 재검사

모든 초기 폴더/로그/runner snapshot을 보존했습니다. 첫 입력도우미는 stale table QLineEdit를 골라 전압 일부를 commit하지 못했고, RF helper는 disabled sweep editor/숨은 tab/잘못된 attribute·focus에서 commit 검사에 걸렸습니다. 실제 current editor와 활성 tab·checkbox·focus를 확인하는 입력도우미로 수정한 후 다시 실행했습니다. 검사 기준은 약화하지 않았습니다.
다중 MainWindow 단일 process 시도에서는 이전 window의 지연 timer가 삭제된 QScrollArea를 참조하는 오류가 다음 case까지 전달되었습니다(`smoke4.log`, GUI :2450). 최종 run은 case별 독립 subprocess와 명시 QApplication teardown을 사용했습니다. 이는 초기 SET invalid-warning access violation과 서로 다른 증거입니다.
최종 기준은 `batch_status.json`/`final_results.json`이며 `results.json`은 가장 마지막 단일 case의 보조 결과입니다. Smoke의 PASS를 최종 case 수에 중복 합산하지 않았습니다.

## 파일

- [최종 집계](final_results.json), [case별 표](case_index.csv), [최종 process/결과 manifest](batch_status.json)
- [RAMP 명령 전수 audit](ramp_duration_audit.json), [부동소수 차분 증거](floating_duration_diagnostic.json)
- 각 case: `request.json`, `gui_input.json`, `committed_waveforms.json`, `analytic_reference.json`, `program.asm`, `pmem.hex`, `dmem.txt`, `model_commands.json`, `model_awg_checks.json`, `model_rf_checks.json`, fine `envelope_0.npy`; 거부 case는 `compile_error.txt`와 참조를 보존합니다.

|Case|결과|추가 내용|
|---|---|---|
|[log_hold_00](log_hold_00_attempt03/result.json)|passed||
|[log_hold_01](log_hold_01/result.json)|passed||
|[log_hold_02](log_hold_02/result.json)|passed||
|[log_hold_03](log_hold_03/result.json)|passed||
|[log_hold_04](log_hold_04/result.json)|passed||
|[log_hold_05](log_hold_05/result.json)|passed||
|[log_hold_06](log_hold_06/result.json)|passed||
|[log_hold_07](log_hold_07/result.json)|passed||
|[log_hold_08](log_hold_08/result.json)|passed||
|[log_hold_09](log_hold_09/result.json)|passed||
|[log_ramp_00](log_ramp_00/result.json)|passed||
|[log_ramp_01](log_ramp_01_attempt02/result.json)|passed||
|[log_ramp_02](log_ramp_02/result.json)|failed|기대 300, 실제 301 cycles (+1)|
|[log_ramp_03](log_ramp_03/result.json)|passed||
|[log_ramp_04](log_ramp_04/result.json)|passed||
|[log_ramp_05](log_ramp_05/result.json)|passed||
|[log_ramp_06](log_ramp_06/result.json)|passed||
|[log_ramp_07](log_ramp_07/result.json)|passed||
|[log_ramp_08](log_ramp_08/result.json)|passed||
|[log_ramp_09](log_ramp_09/result.json)|passed||
|[set_only_identity](set_only_identity/result.json)|unavailable|Exact zero-time SET transitions cannot be represented: production PulseSequence requires strictly increasing times and positive incoming ramp duration.|
|[set_only_mixed](set_only_mixed_attempt03/result.json)|unavailable|Exact zero-time SET transitions cannot be represented: production PulseSequence requires strictly increasing times and positive incoming ramp duration.|
|[voltage_ascending](voltage_ascending/result.json)|passed||
|[voltage_descending](voltage_descending_attempt02/result.json)|passed||
|[voltage_n1](voltage_n1/result.json)|passed||
|[rf_frequency_digital](rf_frequency_digital_attempt05/result.json)|passed||
|[rf_coarse_inside_True](rf_coarse_inside_True/result.json)|passed||
|[rf_coarse_inside_False](rf_coarse_inside_False/result.json)|passed||
|[rf_coarse_crossing_True](rf_coarse_crossing_True_attempt05/result.json)|expected_rejection|RF pulse for generator 0 exceeds SET segment 'set_1' by up to 180 tProcessor cycles|
|[rf_coarse_crossing_False](rf_coarse_crossing_False/result.json)|passed||
|[rf_coarse_beyond_final_True](rf_coarse_beyond_final_True/result.json)|expected_rejection|RF pulse for generator 0 exceeds SET segment 'set_1' by up to 1230 tProcessor cycles|
|[rf_coarse_beyond_final_False](rf_coarse_beyond_final_False_attempt05/result.json)|passed||
|[rf_fine_inside_True](rf_fine_inside_True_attempt07/result.json)|passed||
|[rf_fine_inside_False](rf_fine_inside_False/result.json)|passed||
|[rf_fine_crossing_True](rf_fine_crossing_True/result.json)|expected_rejection|fine RF padded waveform exceeds its HOLD segment at a hardware sweep point|
|[rf_fine_crossing_False](rf_fine_crossing_False/result.json)|unexpected_rejection|fine RF sweep changes shared-port command order or requires commands less than 3 clocks apart|
|[rf_fine_beyond_final_True](rf_fine_beyond_final_True/result.json)|expected_rejection|fine RF padded waveform exceeds its HOLD segment at a hardware sweep point|
|[rf_fine_beyond_final_False](rf_fine_beyond_final_False/result.json)|unexpected_rejection|fine RF sweep changes shared-port command order or requires commands less than 3 clocks apart|
