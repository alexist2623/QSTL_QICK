# AWG Tuning v4 — Virtual matrix 추가 검증 완료 / 실행 제한 3건

사용자 요청으로 추가한 Virtual matrix × parameter sweep 검증을 완료했습니다. 실제 GUI→RTL **21/21 PASS**, 별도 GUI/compiler **14/17 PASS·3건 거부**입니다. 전체 PASS는 아닙니다. [현재 결과/해시](virtual_gate_rtl_20261014/results.json), [보고서](virtual_gate_rtl_20261014/REPORT.md)가 최종 기준입니다. 생산 코드·RTL·XDC·펌웨어·사용자 JSON 변경 0, 보호 59파일 일치입니다. 새 합성·보드 접속·배포 없이 검증만 수행했고 세 controller 및 xsimk는 모두 종료했습니다. `awg-v4-timing`과 `awg-v3`는 **PAUSED** 상태를 유지합니다.

## 2026-10-14 17:59 PDT — Virtual matrix 조합 신규 검증 완료

검증 코드: `qick/firmware/ip/axis_output_sum_v1/validation/virtual_gate/`. MainWindow의 실제 행렬/전압·HOLD·RAMP sweep 설정창에 QTest 키보드 입력 후 Run Experiment 컴파일 PMEM/DMEM을 export와 비교합니다. 세 AWG 모두 결합되는 비대칭 3×3 행렬, DAC full scale 800/400/800mV, 기존 정수 증분/add/rewind 정책을 독립 C@V 계산과 대조합니다. 실제 tProcessor/TMUX/AWG/IIR/RF/합산 RTL은 Git 밖 `F:/Vivado_Output/a3sim1/*v4virt_20261014*`에서 실행합니다.

- 기본 조합 15개: HOLD/RAMP 두 DC 모드·역방향, RF duration fixed/extend·frequency, 두 전압축/축 순서 반전, RC-only/DC-only/OFF, Square frequency/amplitude/phase. 세 IIR의 모든 샘플과 합산을 검사합니다.
- 추가: CPMG N(1,2)×τ(0.2,0.4µs) 네 software sweep 좌표와 composite named frequency/duration의 실제 GUI→RTL. 공유 라이브러리 준비는 순차, 격리 시뮬레이터는 전체 최대3개입니다. 추가 controller는 기본 controller의 모든 simulation 종료 후 simulation을 시작합니다.
- 최초 RAMP helper의 axis_kind 오인과 OFF helper의 초기 RC reset 정책 오인은 검증 도구 오류입니다. 원본 소스·로그를 보존했고 RAMP는 `_retry1`, OFF는 `_retry2` 별도 폴더에서 exit 0을 확인했습니다. 생산 코드나 허용오차는 변경하지 않았습니다.
- 실제 GUI→RTL 21조건, 총 96점·192회, 5,568명령, 세 합산 출력 18,709,728 lane 샘플 PASS입니다. 모든 통과 케이스의 실행 종료 코드·GUI PMEM/DMEM·RTL/입력 fingerprint·159개 GUI/compiler 소스 해시를 대조했습니다.
- GUI/compiler 17검사 중 14 PASS, 3건은 실행 불가입니다. UDD N=2/τ=0.2µs/펄스폭0.1µs는 공유 포트의 AWG 명령13클록과 RF 명령15클록 간격이 필수3클록보다 짧아 거부됩니다. Quantum Circuit RF Loop n=1,3은 v4 AWG latency18을 v3 latency16 조건에서 거부합니다. 이 세 입력은 RTL을 실행하지 못했으며 제품 수정도 하지 않았습니다.
- Quantum Circuit은 AWG Tuning의 Virtual matrix를 전압 변환에 적용하지 않습니다. 합산 RF의 기존 전용 커넥터 power/calibration은 의도적으로 거부되며, 세 출력×두 설정의 거부 검사 6개 PASS는 정상 출력 RTL 시험과 구분합니다.
- 기본/추가 controller의 exit 1은 최초 helper 실패 보존에 따른 것입니다. 별도 최종 RTL 결과는 전부 exit 0입니다. results.json의 execution_complete=true, complete=false는 실행은 끝났으나 위 compiler 3건이 남았다는 의미입니다. 모든 파라미터×모드×방향의 전체 곱을 검사했다고 주장하지 않습니다.

로그: [기본 배치](virtual_gate_rtl_20261014/status.json), [추가 배치](virtual_gate_rtl_20261014/additional_status.json), [보상 OFF](virtual_gate_rtl_20261014/off_status.json), [GUI/compiler 실패 진단](virtual_gate_rtl_20261014/failure_diagnostics.json). [실제 RTL 합산 파형](virtual_gate_rtl_20261014/virtual_matrix_rtl_alignment.png)과 [물리 출력 변환값](virtual_gate_rtl_20261014/virtual_matrix_physical_targets.png)을 열어 확인했습니다. 생산 코드 수정은 이번 검증 요청의 범위에 포함하지 않았습니다.

## 2026-10-14 최신 후속 — Virtual / Physical 행렬 표시

사용자 요청으로 공유 행렬 설정창의 위쪽에 **Virtual 입력 열**, 왼쪽에 **Physical AWG 출력 행**을 표시하고 각 셀에 입력→출력 방향 설명을 추가했습니다. 생산 변경은 `CrossCapacitanceDialog`의 표시/배치뿐이며 그 밖의 GUI 바이트, 변환 계산, 드라이버, RTL, XDC, 펌웨어는 그대로입니다.
실제 MainWindow 설정창에서 키보드 입력·확인·취소, 7출력 대각선 잠금/초기화와 두 화면을 확인했습니다. 비대칭 행렬 `[[1, 0.25], [-0.125, 1]]`을 GUI 설정으로 직렬화하고 기존 QCoDeS 저장 함수로 임시 SQLite DB에 저장한 뒤 닫고 다시 열었습니다. `cross_capacitance_json`, `qick_experiment_json`의 GUI 설정, `awg_waveform_recipe_json`의 행렬이 모두 정확히 일치했습니다.
GUI/저장 확인 6항목과 기존 메타데이터 테스트 **4 PASS**입니다. 실제 보드 접속/실험은 하지 않았고 기존 실행 GUI를 종료하지 않았습니다. GUI 재시작 시 표시가 반영됩니다. 이번 UI 변경은 과거 전체 RTL 회귀 결과와 구분하며 장시간 시뮬레이션을 재실행하지 않았습니다.
[새 검증 결과](virtual_gate_ui_20261014/results.json), [7출력 화면](virtual_gate_ui_20261014/matrix_7_outputs.png).

## 2026-10-14 최신 후속 — 전체 firmware·버전 목록·Update 확인창

GUI 작업 버튼을 **Update 하나**로 통합했습니다. 클릭 시 서버 종료와 실험·출력 정지를 각각 확인하는 창이 열리며, 두 항목 모두 체크해야 진행합니다. 실제 전송량 기준 진행률과 검사/백업/교체 단계 표시가 있습니다.
PC/보드의 저장소 또는 `qick` 폴더를 선택할 수 있고, 로컬 firmware의 BIT/HWH 19개 목록에서 고른 버전을 보드 `pyro_cli.py` BIT 경로로 사용합니다. 라이브러리 코드와 firmware 전체를 교체하며 metadata/link/기존 launcher 설정 및 전체 이전 firmware 백업을 유지합니다.
보드 Pyro4 의존성을 파일 업데이트 경로에서 제거했습니다. 실제 SSH 읽기 전용 검사와 폴더 조회에 성공했고 launcher 원본 해시는 동일했습니다.
새 전용 테스트 **55 PASS**와 실제 로컬 패키지 6개 검사, 확인창 화면 표시·확인·취소를 검증했습니다. 초기 Qt QMessageBox 접근 위반은 로그를 보존했고 일반 QDialog 확인창으로 구현한 최종 실행은 exit 0입니다.
기존 RTL/드라이버/XDC/펌웨어/완료된 회귀 증거와 보호 59파일은 유지했습니다. 실제 보드 업데이트·서버 시작·패키지 설치는 하지 않았으며 기존 실행 GUI를 종료하지 않았습니다. 사용자가 GUI를 재시작하면 새 화면이 반영됩니다.
[최신 보고서](gui_update_full_firmware_20261014/REPORT.md), [결과/소스 해시](gui_update_full_firmware_20261014/results.json). 아래 27개 테스트/여러 버튼에 관한 기록은 이전 구현 당시 상태입니다.

## 2026-10-14 후속 요청 — 설치 정보 보존 및 pyro_cli 경로 동기화

`qcodes2`에 Paramiko 4.0.0을 설치했고 실제 보드 `192.168.2.99` 폴더를 production GUI Browse 버튼으로 탐색했습니다. 보드의 editable 설치는 `qick_lib/qick.egg-info`와 Python site-packages의 `qick.egg-link`를 사용합니다.

기존 전체 `qick_lib` 교체가 설치 메타데이터를 제거하는 문제를 수정했습니다. 이제 코드 폴더 `qick_lib/qick`만 바꾸고 metadata/link를 보존하며, 버전·의존성 등이 다르면 별도 재설치가 필요하다고 거부합니다.
추가 요청에 따라 보드 기존 `pyro_cli.py`의 `start_server(bitfile=...)` 값만 GUI에서 선택한 BIT 절대경로로 동기화합니다. 기존 실행 옵션을 보존하고 백업 복원/교체 실패 시 런처 경로도 원상 복구합니다.

전용 임시 디렉토리 테스트 **27 PASS**, 실제 SSH GUI 탐색 11개 확인 PASS, 보드 Python 3.8.2 설치 정보 읽기 PASS입니다. 실제 보드 런처를 읽어 만든 로컬 변경본은 bitfile 외 AST가 일치합니다. 보드 원본은 여전히 v2 BIT 경로로, 변경하지 않았습니다.
보호 59파일·기존 RTL/드라이버/펌웨어 및 전체 회귀 완료 증거는 그대로입니다. [후속 보고서·범위·남은 검증](gui_update_pyro_path_20261014/REPORT.md), [결과 및 소스 해시](gui_update_pyro_path_20261014/results.json)를 참조합니다. 아래 최초 구현의 미실행 기록은 당시 상태입니다.

## 2026-10-14 09:05 PDT — 현재 v4 전체 기본 회귀 재실행 완료

**현재 v4로 새로 실행한 전체 기본 회귀가 PASS입니다.** [통합 결과](full_regression_20261014/results.json)의 `complete=true`와 [보고서](full_regression_20261014/REPORT.md)를 확인했습니다. controller와 xsimk는 모두 종료했습니다.

- 소프트웨어 72모듈 1,194개 + 추가 29개 = **1,223개 PASS**.
- 기본 RTL 6묶음 및 합산 단위 **1,114,160샘플 PASS**.
- 시스템 **9/9조건 PASS**: 두 HOLD sweep, RF duration 2조건, RC-only, 축 반전, Stability, 10µs RAMP/HOLD의 첫/둘째 HOLD RF.
- 8조건은 실제 MainWindow → Run Experiment → PMEM/DMEM 바이트 일치 → 실제 RTL입니다. Stability는 GUI public builder → 실제 RTL이며 RF/DDR가 없는 기존 기본 조건입니다.
- 48비트 연속 RC **200/200 PASS**, overflow·잔여·누적 면적 0. 최대 RC 오차 0.05461681895mV, 종료 잔류 최대 0.000863350555mV.
- 최초 Qt 종료 오류 2건과 desktop bootstrap 누락 1건은 원본을 보존했습니다. 동일 검사의 환경 처리 후 재실행은 모두 exit 0입니다. controller의 `finished_with_failures`/exit 1은 이 최초 3건을 보존한 값이며 새 stage/case 실패는 없습니다. 재실행 해시/로그를 대조한 통합 결과로 PASS를 판정했습니다.
- 검증 시 생산 소스·사용자 JSON·펌웨어 해시 변경 0, 보호 59파일 일치. 새 합성/배포/32·64비트 비교는 없습니다.

[검증 당시 174개 파일과 결과 스냅샷](full_regression_20261014/validated_snapshot/manifest.json)을 보존했습니다. 이후 GUI 유지보수 기능 추가는 이 PASS에 포함되지 않으며 실행 검증 전입니다. `report.py`를 수정된 트리에 다시 실행하여 이 완료 증거를 덮어쓰지 않습니다.
[누적 면적 그림](full_regression_20261014/selected48/accumulated_error_48.png)과 [RC 오차 그림](full_regression_20261014/selected48/rc_error_48.png)을 열어 확인했습니다.
보드 아날로그 측정/ADC·FIR 산술은 미수행이고, IIR 뒤 DDS 면적·clipping은 기존 DC 면적 보상 대상이 아닙니다.


## GUI 업데이트 기능 — 최초 구현 당시 기록 (후속 검증은 위 참조)

전체 기본 회귀 PASS를 먼저 확정하고 174개 소스/설정/펌웨어와 결과를 스냅샷으로 보존한 뒤 기존 GUI `awg_tuning_v4`에 구현했습니다.
메뉴는 `Setup → QICK Library and Firmware Update...`입니다. 로컬 저장소/성공 v4 manifest 선택, SSH 보드 폴더 탐색, 원본→대상 표시, 전송 전 해시 검사, 별도 staging, 백업/복원 및 재시작 후 펌웨어 식별 동작을 코드로 추가했습니다.
보드 기본 위치는 `/home/QSTL_QICK`; 라이브러리는 `qick/qick_lib`, BIT/HWH는 `qick/firmware` 아래에서 선택합니다. QICK 정지·재시작은 사용자가 수동으로 수행하며 이 기능이 서버를 자동 재시작하거나 파형을 실행하지 않습니다.

**사용자 지시대로 새 GUI·신규 테스트·업데이터·SSH 전송/교체·패키지 설치는 실행하지 않았습니다.** 정적 코드 검토와 diff 확인만 했습니다. Paramiko는 선택 의존성 파일에만 추가했습니다. 실제 사용 전 실행 검증이 남아 있으며 이 기능을 기존 회귀 PASS에 포함하지 않습니다.
기존 생산 파일 변경은 GUI 메뉴/진입점의 `DCWaveform_Generator.py` 1개이며 나머지는 새 유지보수 모듈/설명서입니다. 기존 RTL/드라이버/XDC/펌웨어/사용자 JSON과 보호 59파일은 변함없습니다.
[구현 소스 해시 및 미실행 기록](gui_update_implementation.json), [GUI 사용법·남은 검증](../../../PulseGenerator/DCWaveformGeneratorGUI/QICK_UPDATE.md).

## 이전 진행 기록 (아래 진행 중 표시는 당시 기록)

## 2026-10-14 사용자 요청: 현재 v4로 기본 검증 전체 재실행

RTL 변경 후 이전 버전의 PASS를 재사용하지 않고 기본 검증 전체를 다시 실행하라는 지시를 받았습니다.
통합 `VALIDATION_CHECKLIST.md`에 필수 기준을 명시했습니다. 새 증거는 `full_regression_20261014/`,
기본 실행 폴더는 Git 밖 `F:/Vivado_Output/a4reg1`을 사용합니다.
기본 소프트웨어 전 모듈, 기본 RTL 6묶음, 48비트 연속 RC, v4 합산 단위 및 실제 GUI→RTL
조건과 축 반전·Stability를 확인합니다. 새 합성이나 펌웨어 배포는 이번 검증 실행에 포함하지 않습니다.
이하의 과거 완료 기록은 전체 기본 v4 재실행 완료를 뜻하지 않습니다.

07:24 PDT 진행: 기본 72모듈 1,194개 + 추가 29개 소프트웨어 PASS, 기본 RTL 6묶음 PASS,
합산 단위 RTL 1,114,160샘플 PASS. 초기 Qt 종료 오류 2건/desktop bootstrap 누락 1건은
원본 로그를 보존하고 동일 검사 정상 종료를 확인했습니다. 생산 소스/사용자 JSON/펌웨어 변경 0입니다.
현재 추가 실행은 세션38153, Python PID106276(2026-10-14 07:20:21 PDT 시작),
`analysis_results/awg_tuning_v4/full_regression_20261014/run_additional.py`입니다.
공유 라이브러리 prepare는 순차, 격리 RTL/RC는 최대 3개 병렬입니다. 중복 실행하지 않습니다.
진행은 `full_regression_20261014/status.json`, 전체 판정은 `report.py`가 생성하는
`results.json`/`REPORT.md`에서 확인합니다. 기본 최초 status.complete=false는 보존된 초기 오류
3건 때문이며, 검토된 재실행은 별도 증거로 연결합니다. 새 검증 전체 완료와 혼동하지 않습니다.

08:12 PDT 확인: 새 48비트 연속 RC 200/200회가 exit 0으로 완료됐습니다. overflow·잔여·누적 면적 0, 최대 RC 오차 0.05461681895mV, 종료 잔류 최대 0.000863350555mV입니다. `full_regression_20261014/selected48/`의 소스 해시와 두 그림을 확인했습니다. RF duration 연장 조건도 새 GUI→RTL에서 PASS이며 나머지 시스템 조건은 진행/대기 중입니다. 전체 회귀는 아직 미완료입니다.

기존 `awg-v4-timing` 확인 자동화는 새 회귀 검증 결과 확인용으로 갱신하여 ACTIVE로 전환했습니다.
새 자동화를 중복 생성하지 않았습니다. 상태·결과를 확인하여 전체 완료/실패를 보고한 뒤 PAUSED로
되돌립니다. `awg-v3`는 PAUSED를 유지합니다. 합성/배포는 실행하지 않습니다.

2026-10-14 00:41 PDT 기준 전체 작업 완료입니다.

## 기본 검증 범위 정정 및 문서 통합 — 2026-10-14

**기본 검증 전체를 v4에서 다시 실행하지 않았습니다.** 기본 RTL 6묶음과 48비트 연속 RC는
현재 소스와 같은 v3 완료 증거를 사용했습니다. 기본 소프트웨어 986개 전체와 축 반전·Stability
전체 RTL의 v4 재실행은 미수행입니다. v4 실행 범위는 합산 단위 RTL, GUI→RTL 5조건,
관련 소프트웨어 274개 및 이후 10µs HOLD 2조건입니다. 빌드·연동 완료와 전체 기본 회귀 재실행을
혼동하지 않습니다. 두 체크리스트를 [VALIDATION_CHECKLIST.md](VALIDATION_CHECKLIST.md)에 통합했고,
[checklist_audit.json](checklist_audit.json)에 기존 결과/현재 해시 대조와 미수행 범위를 기록했습니다.
이번 문서 통합에서는 추가 시뮬레이션/합성을 실행하지 않았습니다.

## 추가 요청 완료 — 2026-10-14 10µs RAMP/HOLD GUI→RTL

사용자 요청으로 초기 SET 1µs 뒤 `RAMP 10µs → HOLD 10µs → RAMP 10µs → HOLD 10µs`를
실제 GUI에서 컴파일하여 첫 HOLD/둘째 HOLD에 RF를 각각 넣은 두 조건을 새 isolated RTL snapshot으로 실행했습니다.
세 RF/AWG 쌍, 각 2회, DC+RC 켠 조건에서 GUI PMEM/DMEM 일치, 12개 RF 펄스 HOLD 정합 0클록,
폭 3000클록(10µs), 최종 DAC 2,828,640 샘플 비교, DC 면적/초기화 검사 모두 PASS입니다.
기존 RAMP 뒤 guard 1클록은 유지되므로 첫 RAMP 기준 RF는 각각 10.003333–20.003333µs,
30.006667–40.006667µs에 출력됩니다. GUI 이상적 시간축에는 이 guard가 표시되지 않습니다.
RTL/GUI/드라이버/XDC/펌웨어 변경 및 재합성은 없고, 두 시뮬레이션은 종료했습니다.
59개 보호 소스와 34개 RTL/제약/빌드 소스, 배포 BIT/HWH/XSA 해시가 일치합니다.
보고서/파형/검사기 후처리 정정 기록: [hold10us_gui_rtl/REPORT.md](hold10us_gui_rtl/REPORT.md).
기존 최종 빌드 및 통합 manifest를 다시 쓰지 않았으며 자동화도 PAUSED 상태를 유지합니다.

## 최종 완료 — 2026-10-14

전체 합성·배치·배선, 펌웨어 파일 배포, GUI/Python 드라이버 연동 검증을 완료했습니다.
두 저장소 모두 기존 `awg_tuning_v4` 브랜치이며 commit/push는 하지 않았습니다.
실제 보드 다운로드 또는 아날로그 측정은 수행하지 않았습니다.

| 최종 routed 검사 | 결과 |
|---|---:|
| Setup WNS / TNS | +0.002841 ns / 0 ns |
| Hold WHS / THS | +0.009116 ns / 0 ns |
| Pulse-width 실패 endpoint | 0 |
| Bus skew | 14/14 MET, 최소 +2.201 ns |
| 배선 | 579,977/579,977 nets, 오류 0 |

Vivado 2023.1, jobs=4, general.maxThreads=5, 기존 default 전략을 유지했습니다.
원래 v3 timing.xdc/ios.xdc와 59개 보호 파일의 해시가 일치합니다.
기존 XDC의 input-delay 미지정 4개/output-delay 미지정 24개와 methodology 경고는
보고서에 그대로 남아 있습니다. 제약 완화 없이 명시된 timing 제약을 통과했습니다.
Setup 여유는 약 2.841 ps이므로 큰 여유가 있는 결과로 해석하지 않습니다.

`F:/Vivado_Output/a4full2`는 Git 밖의 새 프로젝트입니다.
10월 13일 19:47:43 시작, 10월 14일 00:27:27 Vivado 종료,
00:28:12 기존 workflow의 펌웨어 배포 완료입니다(약 4시간 40분).
`workflow_status.json`은 `complete=true`, `stage=published`, `exit_code=0`입니다.
BIT/HWH/XSA는 같은 성공 XSA에서 추출됐고 SHA256 및 내부 멤버 바이트 일치를 확인했습니다.

### 최종 GUI / Python 연동

| RF / AWG | QICK generator | RFDC DAC ID | GUI 물리 커넥터 |
|---|---|---|---|
| RF 1 + AWG 1 | 0 + 1 | 10 | DAC4 |
| RF 2 + AWG 2 | 2 + 3 | 11 | DAC5 |
| RF 3 + AWG 3 | 4 + 5 | 12 | DAC6 |

HWH를 실제 QICK metadata parser와 generator connection method로 읽어 세 합산 쌍,
나머지 AWG 4개의 동일 지연, RF 4/Square의 기존 경로를 확인했습니다.
AWG/RF metadata 지연은 각각 18/31클록, 공통 경로 포함 물리 출력 지연은 31/44클록입니다.
RF 명령을 13클록 앞당겨 요청한 출력 시각을 맞춥니다.

빌드 후에는 필요한 두 소프트웨어 파일만 추가 수정했습니다.
- GUI `qick_front_panel.py`: v4 합산 커넥터와 두 generator를 표시하고, 비활성 ATT의
  기본 10 dB가 설정에 섞이지 않도록 ATT=0 / filter=bypass / NQZ=1을 적용합니다.
- Python `qick/dac_current.py`: 실제 HWH 메타데이터로 서로 연결된 AWG/RF 합산 쌍만
  AWG 물리 DAC로 판별합니다. 두 generator가 같은 전류 readback/전압 환산을 사용하며,
  전류 변경은 물리 DAC에 한 번 적용됩니다. 기존 RF와 불완전한 합산 메타데이터는
  기존 읽기 전용 동작을 유지합니다. 기존 VOP/전류 범위 검사는 유지합니다.

최초 확대 검사에서 위 두 문제를 세 쌍 모두 재현했고 `postpublish_before_fix.log`에
보존했습니다. 수정 후 관련 소프트웨어/GUI/최종 HWH 연동 검사 **274개 PASS**입니다.
최초 테스트 fixture의 calibration DB 경로 누락으로 발생한 3개 실패도 별도 보존했으며,
제품 코드 문제와 구분합니다(`final_integration_fixture_failure.*`).

다섯 조건을 수정된 실제 MainWindow -> Run Experiment 경로로 다시 컴파일하여
PMEM/DMEM이 이전 완료 RTL 입력과 모두 바이트 일치하는 것을 확인했습니다.
RTL·제약·펌웨어·프로그램 생성 로직은 빌드 후 변경하지 않았고 장시간 시뮬레이션이나
합성을 다시 수행하지 않았습니다. 새 검사는 테스트용 RFDC/카드 정보를 사용하며
보드 아날로그 측정 결과가 아닙니다.

빌드 시점의 `prebuild_gate.json`과 `build_manifest.json`은 변경하지 않았습니다.
그 원본 gate는 빌드 당시 소스를 증명합니다. 이후 두 소프트웨어 변경의 현재 해시,
원본 스냅샷, 274개 검사 및 5개 GUI 프로그램 일치는
`final_integration_manifest.json`과 `postpublish_program_equivalence.json`으로 연결했습니다.
현재 트리에 원래 `validate_scope.py --require-functional`을 단독 실행하면 이 두 변경을
검출하는 것이 정상이며, 이를 우회하도록 원래 gate를 바꾸지 않았습니다.
현재 최종 연동 증거는 `python analysis_results/awg_tuning_v4/finalize_integration.py`로
검증합니다. 향후 다른 소스 수정/새 합성에는 새로운 기능 증거가 필요합니다.

### 파일 / 사용 범위

펌웨어는 `C:/GIT_Workspace/QSTL_QICK/qick/firmware/projects/qstl_awg_v4/`의
`bitstream.bit`, `bitstream.hwh`, `bitstream.xsa`입니다. BIT와 HWH는 같은 v4 쌍으로
사용해야 합니다. 기존 v3 펌웨어는 보존했습니다. 보드 Python 라이브러리와 PC GUI는
각 저장소의 `awg_tuning_v4` 코드를 함께 사용합니다.

- 파형: `rtl_sum_alignment.png` (16 scalar lanes 전체)
- GUI 확인: `final_gui_shared_dac.png` (최종 HWH 경로, 테스트용 카드 정보)
- 상세 timing: 프로젝트 `validation_reports/`
- 소프트웨어 검사: `postpublish_software.xml`, `postpublish_software.log`
- 실제 GUI 재컴파일: `compiler_replay/`, `postpublish_program_equivalence.json`
- 최종 증거 연결: `final_integration_manifest.json`

AWG DC 면적 보상은 IIR 이전 AWG 면적만 보상합니다. 이후 더해지는 DDS 면적과
최종 clipping 왜곡은 보상하지 않습니다. 기존 정수 SET sweep 양자화는 그대로입니다.
DDR 검증은 timestamp 스트림의 명령/trigger/capture 정합이며 ADC/FIR의 아날로그 또는
수치 응답 검증이 아닙니다. 최종 완료 확인 후 `awg-v4-timing` 자동화를 PAUSED로 전환했습니다. 기존 `awg-v3`도 PAUSED를 유지합니다.

## 이전 진행 기록 (완료 전 상태, 현재 지시 아님)

# AWG Tuning v4 — current work

2026-10-13 (America/Vancouver). Both repositories are on `awg_tuning_v4`.
No commit/push or computer shutdown is part of this task.

## Latest user instruction — stop on timing failure

On 2026-10-13 the user explicitly requested completion through full synthesis
and timing closure, with a report and no further work if timing closure fails.
Continue the existing `v4_final2` workflow; do not launch a duplicate. Let Vivado
complete placement/routing with the existing constraints. If final setup, hold,
pulse-width or bus-skew checks fail, preserve the reports and stop: no RTL edits,
pipeline changes, constraint relaxation, retry build, or BIT/HWH publication.
Report the measured failing metrics and relevant paths to the user. A functional
validation failure also blocks synthesis and must be reported, not bypassed.
The workflow already stops on a failed validation/build/publication guard.
The thread heartbeat `awg-v4-timing` checks this existing workflow every ten
minutes for completion, failure or a stall. It must not launch duplicate jobs.
Pause that heartbeat after the final success/failure report; leave the older
`awg-v3` heartbeat paused.

Latest follow-up (2026-10-13, after 23:24 local): after the full build passes,
complete the GUI and Python driver integration against the final v4 BIT/HWH,
including any necessary remaining software changes and relevant verification.
The user clarified that the existing GUI `awg_tuning_v4` is already the required
v4 branch. The assistant mistakenly created a redundant `v4` branch, then
returned to `awg_tuning_v4` and removed only that redundant branch after verifying
identical HEAD, staged/unstaged diff and untracked-file list. Do not create another
v4 branch. Both repositories remain on `awg_tuning_v4`.
Existing v4 metadata/timing/calibration
integration is already covered by the completed tests, but a final generated
firmware integration review is still pending. Do not change the current tested
sources while the full build and its publication hash gates are running.
If post-build software changes affect validated timing/program generation,
refresh affected evidence before declaring that integration complete. Do not
repeat unaffected long simulations. Check GUI output identity/settings and
Python discovery/configuration for all three shared DAC pairs, legacy behavior,
and final firmware paths. The timing-failure stop instruction still applies.
On success, do not pause the heartbeat or report the entire task complete until
this GUI/driver follow-up is finished; on timing failure, report and stop.

## Completed

- New sum RTL: 1,114,160 lane checks; 149,495 positive clips, 83,952 negative
  clips, 549,930 rounding checks. Sum and bypass both have two registers.
  Evidence: `unit/`, original run `F:/Vivado_Output/a4sum_unit1`.
- Fresh prepare-only Vivado project `F:/Vivado_Output/a4prep1` completed with
  exit 0. Real generated HWH checked with the actual QICK metadata parser:
  RF IPs 0/1/3 pair with AWG IPs 4/5/6 on DAC 10/11/12; seven 48-bit AWGs,
  common 300 MHz, equal added pipeline, old RF DAC inputs zero.
- Original generator RTL and constraints: 59 protected file hashes unchanged.
- Related software regressions: 234 passed, `software_final.xml/log`.
  Initial test collection lacked the existing plottr dependency path; the
  corrected environment includes `qick-v3-validation-deps`. Initial log kept.
- Initial actual MainWindow -> PMEM/DMEM -> tProcessor/TMUX/AWG/RF/sum probe:
  all three pairs, 4 points x 2 repetitions, zero start/width mismatch and
  zero command mismatch; three DC area/reset monitors passed; DDR 8 triggers,
  32 samples, 16 AXI writes with existing 8712-cycle delay.
  Original: `F:/Vivado_Output/a3sim1/rc_precomp_repeat_reset_hold_duration_2x2_v4_all_probe2_output_sum_after_readout_awg_v3`.

## Current / pending

All five `v4_final2` GUI/RTL cases have completed with exit 0. The two 100-point
x 2 hold cases each verified 200 shots on each of three pairs, zero command/
start/width mismatch, 200 area resets per channel, residual area zero, and DDR
200 triggers / 800 samples / 400 writes at delay 8712 clocks. RC-only verified
32 shots per pair with zero DC execution and no start/width mismatch.
`prebuild_gate.json` and `validate_scope.py --require-functional` passed.
The completed RTL plot `rtl_sum_alignment.png` was opened and visually checked.

The first full-build startup (`a4full1`, session 90436 / PID 30748) ended before
synthesis at 19:38:33 local. Vivado's bundled Python 3.8 PYTHONHOME/PYTHONPATH
contaminated the external validator, causing `SRE module mismatch`. This was
neither a functional-test failure nor a timing failure: synthesis and routing
had not run. Its logs, old gate and build scripts are preserved under
`startup_environment_failure_a4full1/`; the entire external project is retained.
Only the external validator invocation gained `-E`, ignoring Python environment
overrides; it uses its own standard library. The same command was checked inside
real Vivado and passed (environment_check.log). No RTL, GUI, library, clock,
strategy, job/thread count or XDC changed. All existing functional evidence was
rechecked and bound to the updated build scripts without rerunning simulation.

The continuing workflow is session 83072, Python PID 136460, created at
2026-10-13 19:47:43 America/Vancouver (2026-10-14 02:47:43 UTC), command
`run_workflow.py --tag v4_final2 --resume-startup-environment-failure --full-build F:/Vivado_Output/a4full2`.
Vivado parent PID 92796 was created at 19:47:46. Check names/command lines/start
times before trusting PIDs. The full build is `F:/Vivado_Output/a4full2`, with
log `F:/Vivado_Output/a4full2_build.log`. Do not duplicate or rerun simulations.
`workflow_status.json` reports the live stage. The recovery option is restricted
to this pre-synthesis environment failure and is guarded against timing retries.
The final timing-failure stop rule above still applies.
Vivado launched `synth_1` at 2026-10-13 19:52:00 local. At 19:54 it was
processing IP synthesis dependencies with four child jobs; logs had no ERROR
or FATAL entries and CPU time was increasing. The full build's generated HWH
also passed the seven-AWG/three-pair/300 MHz/topology check; evidence is
`a4full2_hwh_preflight.json`. This is not final timing closure or publication.
At 20:32:18 local, `synth_1` completed successfully (0 errors), including all
IP dependencies, about 40 minutes after launch. At 20:34 the parent Vivado was
opening/linking the synthesized checkpoints before implementation. The synthesis
log contains 8 critical warnings from unresolved clock variables in the unchanged
timing.xdc at the synthesis stage. Check their resolution in the linked design
and final implementation timing/constraint reports; do not alter the XDC.
Placement/routing and final timing closure are still pending. No firmware was
published at this milestone.
At 20:44 local, Vivado had linked the synthesis netlist and generated the
post-synthesis timing estimate. Its no_clock=273 and unconstrained internal
endpoints=277 match the successful v3 a3full7 post-synthesis report exactly;
these intermediate checks must be reassessed after implementation. Unresolved
legacy clock-group/unused-I/O warnings remain in this intermediate log. The
post-synthesis timing warning is not a final routed failure. Parent CPU time
increased from 515 to 1761 seconds over the last ten minutes; no ERROR/FATAL
or workflow failure was present. Continue the existing workflow without changes.
Implementation `impl_1` was launched at 20:45:12 local. Its Vivado child is
PID 87372, created at 20:45:22, running `d_1_wrapper.tcl`; the parent remains
PID 92796. At 20:54 the child was loading design/clock constraints and its CPU
time had risen from 73 seconds at 20:48 to 531 seconds. No ERROR/FATAL or memory
allocation failure was logged. Available RAM was 12.71 GiB; committed memory
36.79/46.29 GiB. Final routed timing is still pending.
At 21:34 local, implementation was in Global Placement / Partition Driven
Placement. Child CPU increased from 4265 to 5312 seconds since 21:24, with no
ERROR/FATAL or allocation failure. Available RAM decreased to 5.17 GiB and
commit reached 44.10/47.30 GiB. Windows reports an automatically managed page
file, which grew from 14778 to 15809 MiB; C: still has 76.0 GiB free. Monitor
the reduced memory margin as placement proceeds; no settings were changed.
At 22:14 local, placement had reached Phase 4.1 Post Commit Optimization. Its
intermediate Post Placement Timing Summary reported WNS=+0.105 ns; this is
not the final routed setup/hold/pulse-width/bus-skew result. Child CPU increased
from 9491 to 10711 seconds since 22:04 and the log advanced at 22:13:52. No
ERROR/FATAL or allocation failure was found. Available RAM was 7.64 GiB and
commit 45.98/53.50 GiB with automatic page-file management still unchanged.
At 22:34 local, placement and the default phys_opt_design step had completed;
routing reached Router Initialization / Update Timing. Its initial intermediate
estimate was WNS=+0.195 ns, TNS=0, WHS=-0.245 ns, THS=-117.126 ns. Routing and
hold fixing are still in progress: these numbers are not final timing closure
or a final failure. No source/constraint changes or retries were made. Child
CPU rose from 11793 to 12717 seconds since 22:24, with no ERROR/FATAL. Available
RAM was 6.94 GiB and commit 46.26/53.50 GiB.
At 23:14 local, routing was in Rip-up And Reroute / Global Iteration 4.
The latest intermediate estimate improved to WNS=-0.057 ns / TNS=-0.238 ns;
hold was not reported in that iteration. This is not the final routed result.
Child PID 87372 retained its original creation time and CPU increased from
15912 to 16410 seconds since 23:07; the log advanced at 23:13:47. No ERROR,
FATAL or memory-allocation failure was present. Available RAM was 5.65 GiB,
commit 47.13/53.50 GiB. Continue the existing run; no retry or publication.
At 23:44 local, route_design completed successfully with 0 errors. The existing
default router's final physical optimization improved its timing estimate from
WNS=-0.063 ns to +0.003 ns; TNS=0, WHS=+0.009 ns and THS=0. This optimization
was part of the original run, not a manual RTL/XDC change or a retry. Routed
DRC/report generation was still active, so complete setup/hold/pulse-width/
bus-skew signoff and publication were not yet confirmed. Original child PID
87372 CPU reached 19180 seconds; available RAM 3.65 GiB and commit 51.24/53.50
GiB, with no allocation failure. Continue monitoring the existing workflow.
At 2026-10-14 00:04 local, the completed impl_1 routed timing report (generated
23:58:25) confirmed WNS=+0.003 ns, TNS=0, WHS=+0.009 ns, THS=0 and pulse-width
failing endpoints=0. All user-specified timing constraints are met; no_clock=0
and unconstrained_internal_endpoints=0. The original 4 input/24 output ports
without I/O delays remain explicitly reported. The routed bus-skew report
(23:59:02) has 14/14 MET constraints, minimum slack +2.201 ns. Route status is
579977/579977 routable nets fully routed, 0 routing errors. write_bitstream was
still creating the bitmap; parent post-route reports/export/publication and
the final firmware integration review remain pending. Do not call the entire
workflow complete yet. Child CPU increased to 21545 seconds. Automatic page-file
growth continued with C: free 64.25 GiB, F: free 579.81 GiB; no allocation error.
At 00:14 local, BIT generation had completed successfully at 00:05:38 with
0 errors; implementation child PID 87372 had exited. Parent PID 92796 (same
19:47:46 creation time) was active, opening the implemented design and writing
the required post-route reports. The new root timing_summary_postroute.rpt
was generated at 00:14:05; export/publication and GUI/driver final review remain
pending. Do not restart Vivado or treat disappearance of the implementation
child as a failure. Parent CPU was 3338 seconds; memory commit decreased to
43.49/46.29 GiB. No ERROR/FATAL/allocation failure was found.
Preparation compiles isolated snapshots serially; simulation may use 3 workers.
The `v4_final1` preparation failure is preserved: the fixture incorrectly asked
three RF channels to auto-extend one segment. Only RF 1 now owns that extension;
RF 2/3 remain fixed-length in the RF-duration fixtures. Production logic was
not changed to bypass this valid restriction.

Final cases: hold-duration x voltage 100 points x 2, fixed time; same 100 points
with fixed voltage and 100 ns RF offset; RF-duration extension and fixed segment
4 points x 2 each; RC-only hold-duration 16 points x 2. Each exercises all three
RF/AWG pairs and real GUI compilation. Completed source hashes are checked.

The completed cases produced the RTL figure, report and functional build gate.
The workflow has started the fresh `F:/Vivado_Output/a4full2` project.
Only full routed timing closure and current evidence allow v4 publication.
No v4 BIT/HWH is published yet. No board/analog measurements were performed.
The completed initial probe is plotted in `rtl_probe_alignment.png`, using all
16 scalar samples per word to avoid aliasing the DDS waveform. The final batch
produced `rtl_sum_alignment.png` and `VALIDATION_REPORT.md` before synthesis.

## Commands / tools

Python: `C:/Users/Measurement2/.conda/envs/qcodes2/python.exe -X utf8`.
Vivado: `F:/Xilinx/Vivado/2023.1/bin`; jobs=4, maxThreads=5.
PYTHONPATH: existing `qick-v3-validation-deps`, `qick-waveform-time-axis-deps`,
repo `qick/qick_lib`, GUI repo and `DCWaveformGeneratorGUI`.
Qt offscreen; PATH starts with conda `Library/bin` and `DLLs`.

AWG DC area is still measured/compensated before its IIR. The post-IIR added
DDS area and clipping distortion are not claimed to be compensated. Preserve
legacy source, source/PMEM evidence, user settings, v3 firmware, and failures.
