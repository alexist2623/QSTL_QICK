# AWG Tuning 기본·v4 통합 검증 체크리스트

2026-10-14 기준. 기존 v3 `VALIDATION_CHECKLIST.md`와 v4 `PLAN.md`를 합친 관리 문서입니다. 기본 검증, v4 합산 출력, GUI/드라이버, 합성·배포 및 추가 10µs HOLD 시험을 여기에서 확인합니다.

## 현재 확인된 범위

### Virtual matrix × parameter sweep 추가 검증 (2026-10-14, 실행 완료 / 3건 거부)

이전 v4 기본 회귀의 대부분은 단위행렬이며, 축 반전/Stability의 행렬은 2×2 결합을 3×3에 삽입한 조건입니다. 이를 임의의 3출력 결합 또는 모든 sweep의 GUI→RTL PASS로 확대하지 않습니다.

실제 MainWindow 행렬/전압·HOLD·RAMP 설정창 키보드 입력, 비대칭 완전결합 3×3 행렬, 세 물리 출력 800/400/800mV를 사용했습니다. 두 전압축/역방향/축 순서, HOLD/RAMP의 두 DC 모드, RC-only·DC-only·OFF, RF duration fixed/extend·frequency, Square frequency/amplitude/phase, CPMG N×τ 및 named frequency/duration의 **실제 GUI→RTL 21/21조건 PASS**입니다. 총 96점·192회, 5,568명령과 18,709,728 합산 lane 샘플을 대조했습니다. 초기 helper 오류는 보존했고 별도 retry에서 exit 0과 입력/소스 해시를 확인했습니다.

별도 GUI/compiler는 **14/17 PASS, 3건 거부**입니다. UDD N=2/τ=0.2µs/폭0.1µs의 공유 명령 포트 간격 부족 1건, Quantum Circuit RF Loop n=1,3의 v4 지연 profile 미인식 2건입니다. 이 조건을 RTL PASS로 세지 않습니다. UDD 다른 세 좌표는 compiler만 검증했고, Quantum Circuit에는 AWG Tuning 행렬 적용 경로가 없습니다. 합산 RF power/calibration의 의도된 거부 검사 6개는 정상 출력 시험과 다릅니다. 전체 조합의 완전한 곱은 미검증입니다.

검증 코드와 범위: [virtual_gate/README.md](../../qick/firmware/ip/axis_output_sum_v1/validation/virtual_gate/README.md), [케이스별 최종 보고서](virtual_gate_rtl_20261014/REPORT.md), [현재 결과/해시](virtual_gate_rtl_20261014/results.json). 세 controller와 시뮬레이션은 종료했고 생산 소스·XDC·펌웨어·사용자 JSON 변경 0, 보호 59파일 일치입니다. 실행 종료(execution_complete=true)와 전체 통과(complete=false)를 구분합니다.

### 사용자 지시: RTL 변경 후 전체 기본 재검증 필수 (2026-10-14)

- **RTL 또는 출력 연결/파이프라인이 바뀌면, 변경된 버전에서 기본 검증 전체를 새로 실행합니다.** 일부 하위 RTL의 해시가 이전과 같다는 이유로 이전 버전 PASS를 해당 버전의 재검증으로 대체하지 않습니다.
- 필수 범위는 전체 GUI/Python 회귀, 기본 RTL 6묶음, 선택된 48비트 연속 RC 200회, 두 DC 모드·축 반전·Stability, 해당 버전의 출력 합산·지연·RF/DDR 및 실제 GUI→RTL 검사입니다. 32/64비트 폭 선택 시험은 다시 실행하지 않습니다.
- 실제 GUI 재컴파일/PMEM 일치와 실제 RTL 시뮬레이션을 구분합니다. 완료 표시는 현재 소스·입력 해시와 새 실행 로그/종료 코드/결과가 모두 있는 경우에만 합니다.
- 이번 v4 전체 재검증은 **새 실행 전체 PASS**이며 이전의 빌드·배포 완료와 별도로 관리합니다. 결과는 `full_regression_20261014/`에 보존합니다. 기존 결과나 펌웨어를 덮어쓰지 않습니다.

현재 새 실행 결과는 [전체 기본 회귀 보고서](full_regression_20261014/REPORT.md)와 [결과 JSON](full_regression_20261014/results.json)을 기준으로 합니다.
기본 소프트웨어 72모듈 1,194개 및 추가 검사 29개, 기본 RTL 6묶음, 합산 단위 RTL 1,114,160샘플은 현재 v4로 새로 실행해 PASS입니다.
초기 desktop 초기화/Qt 종료 실패 3건은 원본 로그를 보존했고 동일 검사 재실행의 정상 종료를 확인했습니다.
48비트 연속 RC는 이번 새 실행에서 **200/200회 PASS**, overflow·잔여·누적 면적 0입니다. [새 RC 결과/그림](full_regression_20261014/selected48/REPORT.md)과 소스 해시를 확인했습니다. 실제 GUI 입력 8조건과 Stability public builder 1조건을 포함한 시스템 RTL **9/9조건이 모두 새 실행 PASS**입니다. controller 종료 및 새 stage 전부 exit 0을 확인했습니다. 초기 환경 오류 3건은 원본/재실행을 분리 보존했고 통합 결과는 complete=true입니다. 검증 당시 174개 파일은 [스냅샷](full_regression_20261014/validated_snapshot/manifest.json)에 보존했습니다. 이후 GUI 업데이트 기능의 추가/수정은 이 PASS 범위가 아닙니다.

### 재검증 요청 전의 증거 범위 (이전 기록)

다음은 전체 재검증 요청 전에 확인한 범위입니다. 이번 새 실행의 완료 상태와 구분합니다.

- **기본 RTL — 기존 PASS 유지:** v3의 6개 테스트 묶음은 모두 통과했고, 각 RTL/테스트벤치 소스 해시가 현재와 일치합니다. 48비트 연속 RC 200회 결과·CSV 해시·RTL도 일치합니다.
- **기본 소프트웨어 — v3 전체 PASS, v4 전체 재실행은 미수행:** v3 65개 소프트웨어 모듈의 986개 검사는 통과했습니다. 현재 v4에서 재실행한 관련 검사는 274개입니다. v3 소스 목록 158개 중 12개가 현재와 달라, 986개 전체를 현재 v4 PASS라고 표시하지 않습니다.
- **v4 실제 GUI→RTL — PASS:** 5개 조건에서 세 RF/AWG 쌍을 검사했습니다. 빌드 후 소프트웨어 변경에 대해서는 274개 검사와 5개 GUI PMEM/DMEM 재컴파일 일치로 연결했습니다. 이 재컴파일을 RTL 재실행으로 세지 않습니다.
- **10µs RAMP/HOLD — 현재 소스로 실제 GUI→RTL 추가 PASS:** 첫 HOLD/둘째 HOLD 두 조건, 세 쌍 × 각 2회, 총 12개 RF 펄스와 최종 DAC 2,828,640개 샘플을 검사했습니다.
- **축 반전·Stability 전체 RTL — v3 PASS:** 별도 v4 전체 RTL 재실행 결과는 없습니다.
- **v4 전체 timing·펌웨어 — PASS:** 합성·배치·배선 및 같은 XSA의 BIT/HWH 일치까지 완료했습니다. 보드 아날로그 측정은 수행하지 않았습니다.

이전 문서 통합 당시에는 기존 실행 로그와 결과, 현재 소스·펌웨어·증거 해시만 재대조했습니다. 당시 감사 결과는 [checklist_audit.json](checklist_audit.json)에 보존하며, 현재 새 시뮬레이션 결과로 덮어쓰지 않습니다.

## 범위와 공통 실행 조건

- QICK와 GUI 저장소 모두 기존 `awg_tuning_v4` 브랜치를 사용합니다. 새 중복 브랜치를 만들지 않습니다.
- 면적 누적기는 **48비트**입니다. 완료된 32/48/64비트 폭 선택을 반복하지 않습니다.
- 기존 SET/RAMP/Square Wave/IIR/RF/FIR/DDR 주요 로직, 정수 SET 증분/add/rewind, XDC를 보존합니다. 기존 v3 보호 항목 53개에 v4 보호 범위를 더한 현재 **59개 파일**을 해시로 확인합니다.
- 검증끼리는 자원이 허용할 때 병렬 실행할 수 있습니다. 필요한 기능 검증을 통과한 후 합성하며, 검증과 합성을 겹치지 않습니다. 다른 버전의 PASS를 재사용하여 RTL 변경 후 전체 기본 재검증을 생략하지 않습니다.
- 전체 프로젝트는 Git 밖의 새 폴더에 생성합니다. v3 성공 빌드는 `F:/Vivado_Output/a3full7`, v4 성공 빌드는 `F:/Vivado_Output/a4full2`입니다.
- Vivado 2023.1, `jobs=4`, `general.maxThreads=5`, 기존 default 전략·디바이스·300MHz를 유지합니다. v3/v4 `timing.xdc`, `ios.xdc`, 기반 `bd_2023-1.tcl`은 바이트 동일합니다.
- clock group/false path/오차 기준을 완화해서 실패를 숨기지 않습니다. 전체 최종 timing 실패 시 추가 RTL 수정·빌드 재시도·펌웨어 배포 없이 보고한다는 사용자 지시를 유지합니다.
- commit/push/컴퓨터 종료를 하지 않습니다. 소스, 기존 펌웨어, 실패 증거, 사용자 설정 JSON을 보존합니다. 기존 v4 확인 자동화는 이번 회귀 검증 완료 확인에만 사용하고 최종 보고 후 PAUSED로 되돌립니다. v3 자동화는 PAUSED입니다.

## 1. 기본 검증

아래 기본 표는 2026-10-14 새 v4 전체 회귀 결과입니다. 과거 v3 결과 재사용 기록은 위의 이전 기록과 checklist_audit.json에 보존했습니다.

| 검증 / 테스트벤치 | 반드시 확인할 내용 | 확인 상태와 근거 |
|---|---|---|
| 기존 로직 보존 | 보호 소스와 기준 해시 일치 | 현재 59개 일치 — [protected_v3_sources.json](protected_v3_sources.json), 감사 결과 |
| 기본 소프트웨어 전체 회귀 | GUI/QICK 전 모듈, 실패·종료 오류 검토 | **현재 v4 72모듈 1,194개 + 추가 29개 PASS** — [소프트웨어 결과 및 초기 실패/재실행](full_regression_20261014/software/results.json) |
| 사용자 설정 보존 | 검증 전후 생산 소스·사용자 JSON·펌웨어 변경 없음 | **이번 검증 변경 0** — [검증 소스 스냅샷](full_regression_20261014/validated_snapshot/manifest.json) |
| `tb_dc_area` | 양/음/0 면적, 고정시간·고정전압, 반복, 실제 샘플 누적, 잔여 0, done/reset | **현재 v4 새 실행 PASS** — [결과](full_regression_20261014/basic_rtl/tb_dc_area/result.json) |
| `tb_dc_boundaries` | signed overflow 검출, carry, quotient/remainder, partial lane 경계 | **현재 v4 새 실행 PASS** — [결과](full_regression_20261014/basic_rtl/tb_dc_boundaries/result.json) |
| `tb_width_awg` | 실제 AWG 연결, 400 shots, 1,030,144 raw 샘플, 400 RAMP, 841 SET, 241 bypass 및 지연 | **현재 v4 새 실행 PASS** — [결과](full_regression_20261014/basic_rtl/tb_width_awg/result.json) |
| `tb_dc_faults` | 미ARM, 잘못된 전압/시간, 보상 중 입력·중복 명령, abort/fault | **현재 v4 새 실행 PASS** — [결과](full_regression_20261014/basic_rtl/tb_dc_faults/result.json) |
| `tb_set_saturation` | 기존 SET 포화값과 86,357 출력 비교 | **현재 v4 새 실행 PASS** — [결과](full_regression_20261014/basic_rtl/tb_set_saturation/result.json) |
| `legacy_outputs` / `tb_timing_tail` | 기존 RAMP 1,637,952 샘플, Square 101,932 word, IIR enable/bypass 11클록 | **현재 v4 새 실행 PASS** — [결과](full_regression_20261014/basic_rtl/legacy_outputs/result.json) |
| 두 DC 모드 실제 GUI→RTL | MainWindow PMEM/DMEM 일치, tProcessor/TMUX/AWG/RF/DDR | **현재 v4 새 실행 두100점×2회 PASS** — [시스템 결과](full_regression_20261014/results.json) |
| 축 반전·Stability | 각 100점×2회, v4 합산단 포함 | **현재 v4 새 실행 모두 PASS** — [9조건 결과](full_regression_20261014/results.json). Stability는 public builder이며 RF/DDR 없음 |
| shot 면적·초기화 | 각 shot 종료 시 정수 면적·IIR 이력 0, 명령 값·시각 일치 | v3/v4 시스템 PASS; v4는 세 쌍 전체 검사 — 각 `hardware_area_results`, `area_ch*.csv` |
| RF/DDR 타이밍 | RF 폭, trigger/sample/AXI write 수, 지연 8712클록, timestamp 입력 주기 300클록 | v3/v4 시스템 PASS. ADC/FIR 수치 응답 시험과 구분 — [v4 결과](VALIDATION_REPORT.md) |
| 현재 GUI/compiler와 기존 RTL 입력의 연결 | 실제 GUI 재컴파일 PMEM/DMEM 바이트 일치, 변경 소스 별도 검사 | v3 재컴파일 4조건과 v4 재컴파일 5조건은 해당 시점 증거 — [v4 재컴파일](postpublish_program_equivalence.json) |
| `tb_dc_width`, 48비트 연속 RC | 고정전압 100점→고정시간 100점을 상태 연속으로 실행, overflow/면적 오차/잔여·누적 면적 0 | **현재 v4 새 실행 200회 PASS** — [결과](full_regression_20261014/selected48/width_results.json), [소스 해시](full_regression_20261014/selected48/rtl_source_manifest.json) |
| RC 모델 오차 | 최대 < 유효 DAC 1 LSB(0.09765625mV), 종료 잔류·누적 그림 보존 | 최대 0.05461681895mV, 종료 잔류 0.000863350555mV — [보고서/그림](../awg_tuning_v3/selected48_validation/REPORT.md) |
| 증거 검증기의 거부 동작 | 실패/누락/변조/다른 소스 결과를 완료로 인정하지 않음 | v3 증거 15개·거부 포함 13검사 PASS — [기록](../awg_tuning_v3/sequential48_20261007/functional_gate_check.json). v4 현재 증거 연결은 아래 별도 manifest 사용 |

기본 RTL 실행 진입점은 [run_unit_bench.py](../../qick/firmware/ip/axis_awg_tuning_v3/validation/run_unit_bench.py), 기본 회귀 묶음은 [run_regular_validation.py](../../qick/firmware/ip/axis_awg_tuning_v3/validation/run_regular_validation.py)입니다. 실행 전 인자와 소스 버전을 확인하고 새 결과 폴더를 사용합니다. 이전 실행 실패 및 환경/fixture 수정 로그를 통과 로그로 덮어쓰지 않습니다.

## 2. v4 구성과 추가 단위 검증

| 출력 쌍 | QICK RF / AWG generator | RF IP / AWG IP | RFDC ID / GUI 커넥터 |
|---|---|---|---|
| RF1 + AWG1 | 0 / 1 | `axis_signal_gen_v6_0` / `axis_awg_tuning_v3_4` | `10` / DAC4 |
| RF2 + AWG2 | 2 / 3 | `axis_signal_gen_v6_1` / `axis_awg_tuning_v3_5` | `11` / DAC5 |
| RF3 + AWG3 | 4 / 5 | `axis_signal_gen_v6_3` / `axis_awg_tuning_v3_6` | `12` / DAC6 |

합산은 AWG IIR 뒤에 위치합니다. 원래 RF1–3 전용 DAC 입력은 0이며, RF4와 Square Wave 경로는 유지합니다. 다른 AWG 4개도 동일한 2클록 지연을 bypass로 거칩니다.

| 확인 항목 | 통과 기준 | 근거 |
|---|---|---|
| `tb_output_sum` | 16개 lane 독립 signed16→signed17 덧셈, 양/음 포화, 합산 뒤 한 번 반올림, 14비트 정렬 | **PASS**, 1,114,160 samples; 양 포화 149,495, 음 포화 83,952, 반올림 549,930 — [이번 새 단위 결과](full_regression_20261014/output_sum_unit/result.json) |
| 합산/bypass 제어 | reset, invalid stream을 0으로 처리, backpressure로 샘플 시각이 밀리지 않음, 일정한 2클록 지연 | 위 단위 RTL PASS — [테스트벤치](../../qick/firmware/ip/axis_output_sum_v1/validation/tb_output_sum.sv) |
| BD/HWH 연결 | 세 합산 쌍, 7개 48비트 AWG, 공통 300MHz, 나머지 AWG 같은 지연, 기존 FIR/DDR | 최종 HWH/manifest PASS — [build_manifest.json](../../qick/firmware/projects/qstl_awg_v4/build_manifest.json) |
| RF/AWG 정합 | 같은 관측 경계에서 지연 측정, 동일 GUI 시각 출력, RF 폭 유지 | RF 명령을 13클록 앞당김. metadata 지연 AWG18/RF31, 공통 경로 포함 31/44클록 — 실제 RTL 5조건 |
| 예약 불가능한 시각 | 겹치는 명령을 몰래 뒤로 이동시키지 않고 거부 | v4 소프트웨어 회귀에 포함 — [274개 검사](postpublish_software.xml) |
| GUI/드라이버 공유 DAC | 같은 물리 출력 표시·설정·전류 환산, 중복 전류 쓰기 방지, v4 metadata 없을 때 기존 동작 | 최종 HWH 기반 연동 PASS, 274개 중 실제 펌웨어 연동 23개 — [최종 통합 증거](final_integration_manifest.json) |
| 기존 RF 보정 제한 | 새 합산 커넥터에 옛 RF 전용 커넥터의 보정을 적용하지 않음, ATT0/filter bypass/NQZ1 | 관련 회귀 PASS. 실제 합산 커넥터의 아날로그 교정 수행을 의미하지 않음 |

## 3. 실제 GUI→RTL 시스템 검증

MainWindow 설정 → Run Experiment의 컴파일 경로 → PMEM/DMEM → 실제 tProcessor/TMUX/AWG/DDS/합산 RTL로 검사합니다. 소프트웨어 모델만 실행한 결과와 구분합니다.

| 조건 | 점 × 반복 | RF/AWG 쌍 | 상태 |
|---|---:|---:|---|
| HOLD duration × 전압, DC 고정시간 | 100 × 2 | 3 | PASS |
| HOLD duration × 전압, DC 고정전압, RF offset 100ns | 100 × 2 | 3 | PASS |
| RF duration, AWG segment 연장 | 4 × 2 | 3 | PASS |
| RF duration, AWG segment 길이 고정 | 4 × 2 | 3 | PASS |
| RC-only, DC 비활성 | 16 × 2 | 3 | 새 실행 PASS; DC 실행 명령 없음 |
| 축 반전 | 100 × 2 | 3 | 새 실행 PASS |
| Stability public builder | 100 × 2 | AWG 3개, RF/DDR 없음 | 새 실행 PASS |
| 10µs RAMP→10µs HOLD→10µs RAMP→10µs HOLD, 첫 HOLD RF | 1 × 2 | 3 | 현재 소스로 추가 PASS |
| 동일 파형, 둘째 HOLD RF | 1 × 2 | 3 | 현재 소스로 추가 PASS |

9조건 전체의 최신 새 실행은 [통합 결과](full_regression_20261014/results.json)에 있습니다. 다음 링크는 이전 빌드 시점의 증거입니다. 앞의 5조건은 [system_summary.json](system_summary.json), [v4_final2_status.json](v4_final2_status.json), [보고서](VALIDATION_REPORT.md)에 있습니다. GUI 입력 일치, 명령 값/시각, RF 시작/폭, 합산 각 lane, DC shot 종료 및 reset, DDR timestamp capture를 확인했습니다.

마지막 두 조건은 [10µs 보고서](hold10us_gui_rtl/REPORT.md)와 [상태/해시](hold10us_gui_rtl/status.json)에 있습니다. RF 12개 모두 실제 HOLD 시작 차이 0클록, 폭 3000클록=10µs, 예상 밖 RF 펄스 0, 최종 출력 샘플 2,828,640개 일치입니다. 초기 SET 1µs와 DC+RC를 포함했습니다.

**알려진 GUI 시간축 차이:** 기존 v3부터 RAMP 뒤 `ramp_guard_cycles=1`이 있습니다. 첫 RAMP 시작 기준 첫 HOLD RF는 10.003333–20.003333µs, 둘째 HOLD RF는 30.006667–40.006667µs입니다. RF는 실제 HOLD에 맞지만 GUI 이상적 시간축에는 guard가 표시되지 않습니다. 이를 정확한 10/20/30/40µs 경계 통과라고 표현하지 않습니다.

빌드 후 `qick_front_panel.py`, `dac_current.py` 두 파일 변경은 원래 `prebuild_gate.json`을 고쳐 덮지 않았습니다. [final_integration_manifest.json](final_integration_manifest.json)의 현재 소스 해시, 274개 검사, 5개 GUI PMEM/DMEM 일치가 원래 RTL 증거와 연결합니다. 원래 `validate_scope.py --require-functional`을 현재 트리에 단독 실행하면 이 두 변경을 검출하는 것이 정상입니다.

## 4. 합성 이후 필수 검증과 배포

| 항목 | v4 결과 / 기준 |
|---|---|
| 새 프로젝트 / 실행 조건 | Git 밖 `a4full2`; Vivado2023.1, jobs4, maxThreads5, default 전략 |
| 제약 보존 | v3와 XDC 바이트 일치; 완화 없음 |
| 최종 routed setup | WNS +0.002841ns, TNS 0 |
| 최종 routed hold | WHS +0.009116ns, THS 0 |
| pulse-width / bus-skew | 실패 endpoint 0; bus-skew 14/14 MET, 최소 +2.201ns |
| 배선 / 내부 제약 | 579,977/579,977 nets, 배선 오류 0, no_clock·내부 unconstrained 0 |
| 기존 외부 제약 경고 | input-delay 미지정 4개 / output-delay 미지정 24개 보존; 제거했다고 주장하지 않음 |
| HWH/생성 RTL | 세 합산 쌍, 7개48비트 AWG,300MHz,기존 FIR/DDR·출력 지연 확인 |
| 펌웨어 일치 | 같은 성공 XSA의 BIT/HWH 내부 바이트와 저장 BIT/HWH/XSA SHA256 일치 |
| 후속 GUI/드라이버 | 274개 검사 + 5개 실제 GUI 재컴파일 일치; 영향 없는 장시간 RTL 재실행 없음 |
| 보고서/그림/상태 | 최종 보고서·파형·펌웨어 경로 저장; 이후 10µs 추가 요청은 별도 증거 유지 |

펌웨어: [bitstream.bit](../../qick/firmware/projects/qstl_awg_v4/bitstream.bit), [bitstream.hwh](../../qick/firmware/projects/qstl_awg_v4/bitstream.hwh), [bitstream.xsa](../../qick/firmware/projects/qstl_awg_v4/bitstream.xsa). BIT/HWH는 같은 버전의 쌍으로 사용합니다. v3 펌웨어와 실패 증거는 보존합니다. OOC/합성 추정치만으로 전체 timing 통과를 판정하지 않습니다.

## 5. 재검증이 필요한 경우와 아직 수행하지 않은 범위

- [x] **현재 v4 전체 기본 소프트웨어 전 모듈 실행:** 이번 새 실행은 72모듈 1,194개 PASS이며 추가 연동·증거 29개도 PASS입니다. 이전 986/274개와 합산하여 검사 수를 늘리지 않습니다. 초기 실행 오류와 검토된 재실행을 새 보고서에 구분했습니다.
- [x] **v4 축 반전·Stability 실제 RTL 재실행:** `full_regression_20261014`의 새 v4 실행이 완료됐습니다. 축 반전은 GUI runtime 이후 Python에서 순서를 바꾼 조건이며, Stability는 GUI public builder 경로입니다. 실제 GUI 설정창으로 두 전압 축과 순서를 설정하는 추가 검증은 위 Virtual matrix 배치에서 별도 관리합니다.
- [ ] **GUI 시간축에 기존 RAMP guard 표시:** 이번 검증에서 차이를 확인했으나 제품 코드는 수정하지 않았습니다.
- 미수행 범위: 실제 보드 아날로그 출력, 합산 커넥터 교정, ADC/FIR 수치 응답. DDR timestamp 검증으로 대신한 것으로 표시하지 않습니다.
- RTL/출력 연결/파이프라인 변경 시 기본 검증 전체와 버전별 추가 검증을 새 소스·입력 해시로 실행합니다. 소프트웨어만 바뀌었고 검증된 PMEM/DMEM 및 RTL이 같다면 해당 재컴파일 증거와 소프트웨어 검사를 연결할 수 있지만 이를 RTL 재실행으로 표시하지 않습니다.
- 정수 면적 0, RC 모델 오차, 이상 목표 전압 대비 SET 양자화 오차는 별개입니다. 기존 정수 SET sweep 양자화 오차 해결을 주장하지 않습니다.
- AWG DC 면적 보상은 IIR 이전 AWG 면적만 취급합니다. IIR 뒤에 더해지는 DDS 면적이나 clipping 왜곡은 보상하지 않습니다.

## 6. 향후 RC 분할·병렬 실행 방안 — 미구현

독립 조건의 병렬 실행은 가능하지만, 하나의 연속 RC sweep을 잘라 처음부터 시작한 결과를 이어 붙이는 것은 동일한 시험이 아닙니다. `tb_dc_width.sv`는 고정전압 100점 다음 고정시간 100점을 처리하며 독립 아날로그 모델의 `capacitor`를 shot/모드 사이에 초기화하지 않습니다. 면적/IIR 상태가 shot마다 정상 초기화되더라도 아날로그 이력은 이어집니다.

독립 파형/τ/초기조건 시험과 점별 산술 경계 검사는 각각 병렬 실행할 수 있습니다. 동일한 연속 sweep을 분할하려면 capacitor, IIR 이력, pending sample/valid/clear pipeline, DUT 완료 카운터, 전역 point index 등 결과에 영향을 주는 경계 상태를 정확히 전달해야 합니다. snapshot/prefix 재생은 후보이며 아직 구현·동등성 검증하지 않았습니다.

도입 전 확인 항목:

- [ ] 생산 RTL·실제 sweep 명령을 바꾸지 않고 검증기에서만 분할할 것.
- [ ] 짧은 동일 입력으로 직렬 기준과 분할 결과의 값/시각/잔여 면적/RC 경계 상태가 일치할 것.
- [ ] 작업별 소스·입력·초기 상태 해시, point 범위, 정상 종료 코드를 남길 것.
- [ ] 누락/중복/다른 소스/실패·미완료 작업을 거부하고 원래 순서로 누적 오차를 계산할 것.
- [ ] CPU/메모리/시간을 측정해 병렬 수를 정할 것. Vivado `jobs=4`와 시뮬레이터 병렬 수는 별개임.

## 문서 원본과 재확인

합치기 전 [v3 체크리스트](checklist_sources/v3_VALIDATION_CHECKLIST.md), [v4 계획](checklist_sources/v4_PLAN.md), [원본 해시](checklist_sources/manifest.json)를 보존했습니다. 과거 완료 표시를 현재 실행 결과로 바꾸지 않았습니다. 이후 검증 항목/상태는 이 통합 문서를 기준으로 갱신합니다.

현재 소스·결과·펌웨어를 읽기 전용으로 대조하려면 저장소 루트에서 다음 명령을 사용합니다. 시뮬레이션/합성을 실행하거나 기존 signoff manifest를 다시 쓰지 않으며, `checklist_audit.json`만 갱신합니다.

```powershell
& 'C:/Users/Measurement2/.conda/envs/qcodes2/python.exe' -X utf8 analysis_results/awg_tuning_v4/audit_checklist.py
```

## 회귀 이후 GUI 유지보수 기능의 별도 검증 범위

새 업데이트 GUI는 전체 회귀 완료 후 구현했고 사용자 지시로 실행/신규 테스트를 수행하지 않았습니다. 완료된 회귀의 소스 스냅샷과 분리하며, 경로/패키지 검사, SSH/SFTP, 교체·복원·중단 복구, GUI 상태 전이 및 시험용 보드 검증이 남아 있습니다. [사용법과 미수행 검증 목록](../../../PulseGenerator/DCWaveformGeneratorGUI/QICK_UPDATE.md), [구현 기록](gui_update_implementation.json).

## 2026-10-14 Composite / Custom parameter 추가 검증

별도 사용자 요청으로 GUI composite 기능을 확장한 뒤 수행한 결과입니다. 위 전체 기본 회귀나 v5 합성 완료로 대체하여 표시하지 않습니다. [상세 보고서](../awg_tuning_v5/composite_t2_fix/REPORT.md), [정확한 소스·결과 해시](../awg_tuning_v5/composite_t2_fix/result.json).

- [x] Custom의 펄스별 amplitude/phase 및 named delay 선택·sweep, 공통 Manual gain/Calibration dBm 모드, 저장/불러오기·미리보기·메타데이터: 관련 9모듈 282검사 PASS, Qt callback 오류 없이 exit0.
- [x] 기존 mixed calibration 설정과 독립 global override, Unicode/중복 이름, delay 참조 변경·삭제, preset↔Custom 전환의 실제 값·타이밍 보존.
- [x] T2 앞/뒤 π/2 선택, `d0/2` 참조와 duration sweep, Hahn echo τ/2·π·τ/2 동작.
- [x] 새 MainWindow→Run Experiment→실제 v4 RTL 7조건: τ×π 6조합 및 Hahn→Custom의 개별 진폭/위상 1조건. 세 RF/AWG 쌍 × 두 반복, 126 DDS burst의 명령·폭·상대시간·합산·DC 잔여면적 및 carrier 진폭/주파수/상대위상 검사 PASS.
- [x] 현재 소스로 기존 9 시스템 조건 재컴파일: PMEM/DMEM 바이트 일치. 새 RTL 6조건도 최종 소스로 재컴파일하여 실제 실행 입력과 명령/이벤트 동일성 확인. 메타데이터의 추가 필드는 별도로 기록.
- [x] Calibration 보정 DB의 dBm→gain 및 전체 frequency sweep에 맞는 run 선택은 일반 RF 소프트웨어/compiler/preview로 검증. v4 합산 출력은 기존 사전 차단을 세 쌍과 실제 runtime 경로에서 확인했으며 우회하지 않음.
- [ ] v4 합산 커넥터의 실제 Calibration 출력, 보드 아날로그 측정, ADC/FIR 산술은 이 검증 범위에 포함되지 않음.
