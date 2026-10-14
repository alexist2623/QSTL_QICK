# AWG v3 검증·합성·배포 체크리스트

기준: 2026-10-07 최종 완료. 기능검증·합성·배치배선timing·BIT/HWH/XSA 저장 및일치검사가 모두 완료됐습니다. [최종보고서](FINAL_REPORT.md)와 [진행기록](RUNNING.md)을 참조하십시오. 원본제약의외부I/O/CDC경고는최종보고서에보존했습니다.

## 작업 범위와 실행 조건

- 두 저장소: `C:/GIT_Workspace/QSTL_QICK`, `C:/GIT_Workspace/PulseGenerator`, 브랜치 `awg_tuning_v3`.
- 면적 누적기는 **48비트로 확정**했습니다. 32/64비트 폭 비교를 다시 실행하지 않습니다. 과거 비교 결과는 `width_comparison`에 보존합니다.
- 변경 범위는 새 IIR 전단 DC 면적 누적·보상 회로와 필요한 파이프라인·v3 연동입니다. 기존 SET/RAMP/SquarePulse/IIR/RF/FIR/DDR 주요 로직과 정수 SET 증분/add/rewind를 유지합니다.
- 검증끼리는 병렬 실행할 수 있습니다. **필수 검증을 모두 통과한 다음 합성**하며 검증과 합성을 겹치지 않습니다.
- 새 전체 빌드: `F:/Vivado_Output/a3full7`. 두 Git 저장소 밖에 새 프로젝트를 만들며 이전 `.xpr`을 열거나 재사용하지 않습니다.
- Vivado 2023.1, **`jobs=4`, `general.maxThreads=5`**(이전 성공 빌드의 내부 스레드 설정), 기존 전략·디바이스·300 MHz 유지.
- 원본 `timing.xdc` 및 `ios.xdc`를 바이트 동일하게 사용합니다. clock group, false path, 허용오차를 완화하여 통과시키지 않습니다.
- commit/push/컴퓨터 종료 금지. 자동화는 PAUSED 유지. 실패 증거·기존 펌웨어·사용자 설정을 보존합니다.

## 합성 전 필수 검증

| 확인 항목 | 통과 조건 | 현재 상태 / 근거 |
|---|---|---|
| 기존 로직 원복·보존 | 보호 소스 53개가 원복 기준 해시와 일치 | 완료 — `scope_correction/legacy_logic_baseline.json`, `legacy_logic_guard.py` |
| 기본 소프트웨어 회귀 | QICK/GUI 기존 65모듈, 모든 테스트 및 프로세스 정상 종료 | 완료 — 986개 통과, `regular_validation/REPORT.md` |
| GUI 설정 보존 | 검증 전후 생산 소스와 사용자 JSON 해시 동일 | 완료 — `regular_validation/source_hashes.json`, `status.json` |
| 48비트 면적·보상 단위 | 양/음/0, 두 DC 모드, 반복, 샘플 면적 일치, 보상 잔여 0, 완료/reset | 완료 — `regular_validation/tb_dc_area` |
| 48비트 산술 경계 | signed overflow를 wrap 없이 검출, carry·quotient·remainder·partial lane 경계 | 완료 — `regular_validation/tb_dc_boundaries` |
| 실제 AWG 연결·bypass | 400 shots, 1,030,144 raw 샘플, 400 RAMP, 841 SET, 241 bypass 지연 검사 | 완료 — `regular_validation/tb_width_awg` |
| 비정상 DC 명령·중단 | 미ARM, 잘못된 전압/시간, 보상 중 입력·중복 명령, abort/fault 처리 | 완료 — `regular_validation/tb_dc_faults` |
| 기존 SET/RAMP/Square 출력 | SET 86,357 출력 비교, RAMP 1,637,952 샘플, Square 101,932 word, 기존 IIR enable/bypass 11클록 | 완료 — `regular_validation/tb_set_saturation`, `legacy_outputs` |
| 실제 GUI→RTL 두 DC 모드 | MainWindow 입력→Run Experiment와 export의 PMEM/DMEM 바이트 일치, 실제 tProcessor/TMUX/AWG/RF/DDR 실행 | 완료 — `system_validation/REPORT.md` |
| 축 반전·Stability | 별도 축 반전과 Stability builder를 포함한 4조건 각각 100점×2회 | 완료 — `system_validation/status.json` |
| shot 면적·reset | 네 조건 각각 두 DAC의 보상/reset 200회, 잔여 면적 0, 명령값·시각 불일치 0 | 완료 — 각 `hardware_area_results`, `area_ch*.csv` |
| RF/DDR/출력 지연 | RF 3조건 각각 200펄스·폭 오차 0, DDR 200trigger/800sample/400AXI write, 설정 지연 8712클록과 300클록 샘플 주기 정합 | 완료 — `system_validation/system_timing.png` |
| 현재 GUI/compiler 출처 | 현재 Python 소스로 다시 생성한 4프로그램의 PMEM/DMEM이 검증된 RTL 입력과 일치 | 완료 — `compiler_replay2`; xsim 재실행 없음 |
| 48비트 긴 RC 연속 sweep | 고정전압 100점→고정시간 100점, 200 shots 모두 완료, overflow/면적 수집 오차/보상 잔여·누적 면적 0 | 완료 — `selected48_validation/width_results.json`, 11:59 exit0 |
| RC 오차·그림 | 독립 RC 모델 최대 오차 < 유효 DAC 1 LSB(0.09765625mV), 종료 잔류 수치와 shot별·누적 그래프 저장 및 열어 확인 | 완료 — 최대0.05461681895mV, 종료잔류0.000863350555mV, 그림2개 확인 |
| 최종 증거 검사 | 모든 결과의 정상 종료·횟수·현 소스 해시 확인, 누락/실패/변조 결과를 publisher가 거부 | 완료 — 현 증거15개 승인, 양성/거부13항목 통과, `sequential48_20261007/functional_gate_check.json` |

기본 소프트웨어 최초 실행의 환경/종료/오래된 테스트 문구 실패를 통과로 바꾸지 않았습니다. 원본 실패 로그와 재검사 기록을 모두 보존하며 최종 정상 종료 결과를 따로 사용합니다. 저장소의 기존 생산 로직과 테스트는 변경하지 않았고, SquareWave 오류 문구 한 곳은 빌드 폴더의 테스트 복사본에서만 현재 문구에 맞췄습니다.

## 합성 이후 필수 검증과 배포

- [x] 필수 기능 검증 및 simulator/후처리 종료 확인. 소프트웨어986개, RTL단위/GUI시스템 및48비트RC200회 완료.
- [x] Git밖 a3full7 새프로젝트, jobs4/maxThreads5/기존전략 확인.
- [x] 실제XPR의원본XDC사본참조·v2/v3/사본해시 일치 확인. 내용수정 없음.
- [x] 같은XSA의HWH: 7개48비트AWG/공통300MHz/출력16/DC17/기존FIR·DDR8712 설정 통과.
- [x] 최종 setup+0.011847ns/hold+0.009619ns, TNS/THS0, pulse-width위반0, bus-skew14개통과(최소+2.429ns). no_clock/내부미제약0,배선오류0.
- [x] 이전위반/중단/도구오류자료 보존. 최종빌드는추가RTL·제약변경없이통과. 기존주요로직보호검사통과.
- [x] publisher의현재기능증거15개/소스·생성RTL/빌드조건/실제XDC/최종timing 검사 exit0.
- [x] 같은성공XSA의 BIT/HWH를 qstl_awg_v3에저장하고 XSA자체/내부멤버/manifest해시 재확인.
- [x] TODO/README/검증보고서/누적오차·RTL지연·최종timing그림 갱신·시각확인. 보드업로드/아날로그실측은수행하지않음.

## 다음 RC 검증의 분할·병렬 실행 방안

**가능하지만, 독립 조건의 병렬 실행과 하나의 연속 sweep을 잘라 실행하는 것은 구분해야 합니다. 이번 실행은 중단·분할·재시작하지 않습니다. 아래는 다음 검증기 개선을 위한 설계 기록이며 아직 구현하지 않았습니다.**

### 현재 시험에서 이어지는 상태

`validation/tb_dc_width.sv`는 한 실행에서 고정전압 100점 뒤 고정시간 100점을 순서대로 처리합니다. FPGA의 면적/IIR 상태는 shot마다 정상 DC 종료/ARM 절차로 초기화하지만, 독립 아날로그 모델의 `capacitor`는 **shot 사이뿐 아니라 두 모드 사이에도 초기화하지 않습니다**. 따라서 앞선 출력 이력이 뒤 지점의 RC 오차에 영향을 줍니다.

이 긴 RC 시험 자체는 각 지점의 정수 증분 전압을 시험벤치에서 직접 공급합니다. 실제 tProcessor의 sweep add/rewind 명령 실행은 별도 GUI→RTL 검증에서 확인합니다. 따라서 분할의 제약은 단순히 'sweep이기 때문'이 아니라, 이 시험이 검증하는 연속 상태에 있습니다.

각 조각을 capacitor=0에서 시작하고 CSV만 합치면 원래 연속 sweep과 같은 검증이 아닙니다. 디지털 면적이 shot마다 0이라고 해서 아날로그 커패시터 상태까지 정확히 0인 것은 아닙니다. 단순히 앞부분을 생략하거나 충분히 작을 것이라고 가정해서는 안 됩니다.

### 우선 적용할 수 있는 방법

1. **독립 시험 조건을 병렬 실행:** 서로 독립적으로 정의된 파형/초기조건/τ/모드 등의 시험을 각각 실행하되, 각 시험 안의 100점 sweep 순서는 유지합니다. 기존 GUI→RTL의 독립 조건처럼 나눌 수 있습니다. 고정시간을 독립 초기조건으로 새로 시작하는 시험은 현재의 '고정전압→고정시간 연속 200점'과 다르므로 그 차이를 보고서에 명시하고 필요한 연속성 검증도 남깁니다.
2. **점별 산술 경계 검사는 병렬 실행:** independent digital area/overflow/quotient/partial-lane 시험은 별도 작업으로 나눌 수 있습니다. 이를 연속 RC 누적 검증을 대체한 것으로 표시하지 않습니다.
3. **동일한 연속 sweep을 구간 분할하려면 경계 상태를 전달:** 각 구간 시작 시 capacitor뿐 아니라 IIR 이력, pending sample/valid/clear 파이프라인, target-delay, DUT 상태·완료 카운터와 전역 point index 등 결과에 영향을 주는 상태를 정확히 재현해야 합니다. 안정된 shot 경계를 선택하여 어떤 디지털 상태가 항상 동일한지 먼저 증명할 수는 있으나, 아날로그 이력은 별도로 이어야 합니다. 앞 구간의 상태를 알아야 한다는 의존성이 있어 분할만으로 병렬 속도 향상이 보장되지는 않습니다.

상태 snapshot 또는 동일 소스의 prefix 재생은 후보입니다. prefix를 매 작업에서 반복하면 총 연산량이 늘어나며, RTL/파형/RC 설정이 달라졌는데 과거 snapshot을 재사용하면 안 됩니다. 이후 DAC trace와 RC recurrence를 분리·계산하는 방식도 검토할 수 있지만, 현재 기준 실행과의 동등성을 확인한 뒤 적용해야 합니다.

### 병렬 검증기 도입 시 완료 조건

- [ ] 생산 RTL과 실제 sweep 명령을 바꾸지 않고 검증기에서만 분할합니다.
- [ ] 먼저 짧은 동일 입력으로 직렬 기준과 분할 결과를 비교합니다. 모든 지점의 디지털 값·시각·잔여 면적은 정확히 같아야 하며, RC 경계 상태와 오차도 기존 기준으로 일치해야 합니다.
- [ ] 각 작업의 소스/입력/초기 상태 해시, point 범위, 정상 종료 코드를 저장합니다.
- [ ] 집계 시 빠진 지점·중복 지점·다른 소스·실패/미완료 작업을 거부합니다. point 순서를 복원하여 누적 오차를 계산합니다.
- [ ] CPU/메모리 사용과 실제 소요 시간을 측정하여 동시 작업 수를 정합니다. Vivado `jobs=4`는 RC 시뮬레이터 병렬 개수 설정과 별개입니다.
- [ ] 변경 없는 완료 검증은 반복하지 않고, 변경으로 영향을 받은 검증만 새 증거로 실행합니다.

## 결과 해석의 한계

- 디지털 면적 0, RC 모델 오차, 이상 목표 전압 대비 SET 양자화 오차는 서로 다른 지표입니다. 기존 정수 SET sweep의 목표 전압 오차는 보존합니다.
- GUI→RTL의 DDR 입력은 300클록 timestamp stream입니다. 실제 ADC/FIR 산술·실제 아날로그 측정 전체를 대신하지 않습니다.
- OOC timing 통과는 전체 FPGA timing closure가 아닙니다. 최종 성공 BIT/HWH가 준비되기 전에는 배포 완료로 표시하지 않습니다.
