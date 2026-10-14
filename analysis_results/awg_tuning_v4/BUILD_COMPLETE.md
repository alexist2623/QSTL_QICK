# AWG Tuning v4 build and software integration complete

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
