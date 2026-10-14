# AWG Tuning v3 최종 검증 및 펌웨어 저장 결과

2026-10-07, America/Vancouver. **48비트 IIR 전단 면적 누적/DC 보상, 실제 GUI→RTL 검증, 전체 배치·배선 및 펌웨어 저장을 완료했습니다.** Vivado는17:34:58에 exit0으로 종료했고, 최종 확인 후 같은 성공 XSA에서 추출한 BIT/HWH를 저장했습니다.

## 최종 FPGA 결과

| 항목 | 결과 |
|---|---:|
| Setup WNS / TNS | +0.011847 ns / 0 |
| Hold WHS / THS | +0.009619 ns / 0 |
| Setup / Hold / Pulse-width 위반 endpoint | 모두 0 |
| Bus-skew | 14개 모두 통과, 최소 여유 +2.429 ns |
| 배선 완료 / 오류 | 577,428개 / 0 |
| no_clock / 내부 미제약 endpoint | 0 / 0 |
| 최종 DRC·Methodology Critical/Error | 0 |

Vivado2023.1, `jobs=4`, `general.maxThreads=5`, 기존 기본 합성·구현 전략을 사용했습니다. 두 Git 저장소 밖 `F:/Vivado_Output/a3full7`에 새 프로젝트를 생성했습니다. 성공했던 v2의 `timing.xdc`와 `ios.xdc`를 바이트 그대로 복원해 사용했으며, 실제 `.xpr` 참조와 원본/사본 해시도 확인했습니다. 타이밍 여유는 양수이지만 setup약11.847ps/hold약9.619ps로 작습니다.

[최종 타이밍 그림](final_build/routed_timing.png) · [수치·파일 검증 결과](final_build/verification.json) · [원본 배치·배선 보고서](../../qick/firmware/projects/qstl_awg_v3/validation_reports/timing_summary_postroute.rpt)

## 기능 검증

- **선택된48비트 RC 시험:** 고정전압100회→고정시간100회, 총200 shots 완료. overflow, 면적 수집 오차, shot 종료 잔여 면적, 누적 잔여 면적 모두0입니다. 물리 RC 모델의 커패시터 상태는 shot 및 모드 사이에도 계속 이어집니다.
- **독립 RC 모델 오차:** 최대0.05461681895mV, 종료 잔류 최대0.000863350555mV(약0.86335µV). 최대 오차는 시험 조건의 유효 DAC1LSB인0.09765625mV보다 작습니다. 이는 디지털 면적 오차0과 다른 지표입니다.
- **실제 GUI→RTL:** 고정전압, 고정시간, 별도 축반전, Stability의4조건을 각각100점×2회 검사했습니다. 각 조건의 두 DAC 보상/reset200회, 잔여면적0, 명령값·시각 불일치0입니다. 실제 MainWindow→Run Experiment의 두 DC 모드 PMEM/DMEM 바이트 일치와 현재 GUI/compiler 재생성 일치도 확인했습니다.
- **RF/DDR:** RF가 있는3조건 각각200펄스, 폭 오차0, DDR200trigger/800sample/400AXIwrite입니다. 출력16클록, IIR 전단 DC시작17클록, RF출력42클록 및 DDR8712클록+다음300클록 샘플 경계 지연을 확인했습니다. Stability 조건 자체에는 RF/DDR가 없습니다.
- **기본 회귀:** 소프트웨어65모듈986개, 48비트 RTL단위5개, 기존 SET/RAMP/SquarePulse 출력·지연 검사 통과. 기존 주요 소스53개 보호 해시와 GUI 생산소스·사용자 설정 해시가 유지됐습니다.
- 32/48/64비트 비교는 폭을 선택했던 과거 증거로 보존합니다. 48/64 결과가 같아48비트를 선택했고, 이후32/64 검증을 다시 실행하지 않았습니다. 최종 현재소스 검증은 위48비트 시험입니다.

[누적 면적 오차 그림](selected48_validation/accumulated_error_48.png) · [RC 전압 오차 그림](selected48_validation/rc_error_48.png) · [GUI→RTL 지연 그림](system_validation/system_timing.png) · [GUI→RTL 보고서](system_validation/REPORT.md) · [기본 회귀 보고서](regular_validation/REPORT.md)

## 저장한 펌웨어와 일치 확인

- [bitstream.bit](../../qick/firmware/projects/qstl_awg_v3/bitstream.bit)
- [bitstream.hwh](../../qick/firmware/projects/qstl_awg_v3/bitstream.hwh)
- [bitstream.xsa](../../qick/firmware/projects/qstl_awg_v3/bitstream.xsa)
- [build_manifest.json](../../qick/firmware/projects/qstl_awg_v3/build_manifest.json)

publisher는 현재 기능증거15개·생산소스 해시·생성 RTL·원본XDC·최종 타이밍을 확인해 exit0으로 완료했습니다. 저장 후 BIT/HWH가 같은 XSA 내부 멤버와 바이트 단위로 일치하고, XSA 자체와 모든 manifest 해시도 일치함을 재확인했습니다. HWH는7개48비트AWG, 공통300MHz, 출력16/DC시작17클록, 기존 FIR/DDR8712클록 설정을 통과했습니다.

| 파일 | SHA256 |
|---|---|
| BIT | `d36762cce6f8fc3f79a61085b222817d05d7d8537a54a14f8d78d89aac3fa11b` |
| HWH | `f664dd16ee4790322a482193dfec85f6c72fbaefbf84c1447be5219b8bb82da7` |
| XSA | `a174920455287d77c9a7c86c5ec8fad1e8495605babc1e62df9bfb76f05826d1` |

## 확인 범위와 남는 한계

기존 정수 SET sweep 증분/add/rewind를 유지했습니다. **이상 목표 전압 대비 기존 SET 양자화·누적 증분 오차까지 없어진 것은 아닙니다.** 변경은 새 IIR 전단 DC 누적·보상 회로, 해당 파이프라인과 필요한 v3 연동 범위입니다. 기존 SET/RAMP/SquarePulse/IIR/RF/FIR/DDR 주요 로직은 보호 기준을 유지했습니다.

현재 결과는 **원본 제약 아래의 timing closure**입니다. 외부 입력4포트/출력24포트는 지연 제약이 없고, CDC1건·동기화 속성1건·비동기 reset42건·기존 비동기 그룹이 덮는 max-delay10건 등의 Methodology 경고가 남습니다. 기존 XDC의 미존재 클록/포트 참조 경고와 최종 DRC 경고·권고도 보고서에 보존했습니다. 전체 보드 I/O·CDC 검증 완료로 해석하지 않습니다.

DDR 시험은300클록 간격의 timestamp 입력 스트림으로 저장 시각과 AXI 동작을 확인했습니다. ADC 아날로그 입력이나 FIR 산술 전체를 이 시험으로 검증한 것은 아닙니다. 실제 보드 업로드·아날로그 실측은 수행하지 않았습니다.

## 실패 기록과 종료 상태

이전 timing 실패와 중단 결과는 보존했습니다. a3full7의 최초 FIR 메모리 할당 실패와 SmartConnect 내부 Tcl 오류는 동일 소스·설정 재시도로 해결됐습니다. 이후 상위 합성 초기화가 누락된 재개 절차도 수정했으며 완료IP130개를 보존했습니다. [실패와 재개 근거](synthesis_failure_a3full7/REPORT.md), 최종 실행 로그와 재개 스크립트는 `final_build`에 있습니다.

기본회귀의 최초 환경/Qt종료/오래된 테스트문구 실패도 원본과 재검사 결과를 함께 보존했습니다. 실패를 통과로 바꾸거나 허용오차를 늘리지 않았습니다.

두 저장소 브랜치는 `awg_tuning_v3`를 유지합니다. commit/push/컴퓨터 종료는 하지 않았습니다. Vivado/xsim은 종료됐고, 자동화는 PAUSED 상태를 유지합니다. [전체 체크리스트](VALIDATION_CHECKLIST.md)와 [진행 기록](RUNNING.md)에 최종 상태를 반영했습니다.
