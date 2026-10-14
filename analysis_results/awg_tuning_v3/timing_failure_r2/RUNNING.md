# v3 실행 상태 / 재개 정보

## 2026-10-07 09:46 PDT — 배선 완료, 최종 보고서 생성 중

- 동일 세션95967/main10748/implementation24948 유지. `route_design completed successfully`, elapsed1시간26분17초입니다. routed DRC/Methodology 보고서 생성 후 현재 report_power를 수행 중입니다. 아직 최종 report_timing_summary/critical path 보고서는 생성되지 않았습니다.
- Router 추가 physical optimization 뒤 마지막 수치는 WNS-0.092ns/TNS-2.165ns, WHS+0.006ns/THS0입니다. setup 위반이 남아 있으므로 배포하지 않습니다. 정확한 최종 routed critical path 보고서가 나오면 원인 경로를 검토하고 필요한 수정·GUI→RTL 재검증·전체 재빌드를 진행합니다. 허용오차/clock/falsepath 완화는 하지 않습니다.
- CPU19880초로 증가,가용RAM5.3GiB/F:여유661.3GiB. 프로세스는 정상이며 보고서/BIT 생성이 끝나기 전에 종료하거나 중복 실행하지 않습니다. 현재 RTL/검증 증거는 보존합니다.

## 2026-10-07 09:16 PDT — 지연/skew 최적화 진행

- 동일 세션95967/main10748/implementation24948에서 route_design의 Global Iteration0~3을 마치고 Phase5 Delay and Skew Optimization / Phase5.1.1 Update Timing으로 진행했습니다.
- 중간 setup WNS는-0.339→-0.261→-0.170→-0.195ns, 마지막TNS-2.715ns입니다. 마지막 겹침0이며 hold 최종값/전체 routed timing은 아직 없습니다. 배선 결과가 확정될 때까지 계속 실행합니다.
- CPU가09:06의16386초에서09:16의17008초로 증가했습니다. 로그 ERROR없음, 가용RAM7.7GiB/F:여유661.3GiB. 기능검증은 최신 소스로 완료되어 있고 BIT/HWH는 배포하지 않았습니다.

## 2026-10-07 08:46 PDT — 배선 겹침 해소, timing 최적화 대기

- 동일 세션95967/main10748/implementation24948에서 route_design Phase4.1 Global Iteration0 진행 중입니다. 배선 겹침 수가84711→0으로 감소했습니다. 혼잡도5 경고는 보존하며, 겹침0은 최종 timing 통과를 뜻하지 않습니다.
- 앞선 배선 초기 중간값 WNS+0.011ns/TNS0, WHS-0.144ns/THS-117.885ns 이후 최종 timing 수치는 아직 없습니다. 지연/hold/skew 보정까지 계속 확인합니다.
- CPU가08:36의14331초에서08:46의14969초로 증가했습니다. 로그 ERROR없음, 가용RAM7.8GiB/F:여유661.3GiB입니다. 소스 변경, 중복 실행, BIT/HWH 배포 없음.

## 2026-10-07 08:16 PDT — route_design 시작

- 같은 전체 빌드 세션95967/main10748/implementation24948 유지. 물리 최적화를 마치고 `route_design` Phase1 Build RT Design에 진입했습니다. 배선 전 DRC 두 검사 모두 오류0입니다.
- 마지막 물리 최적화 중간 WNS 추정-0.087ns/TNS-4.562ns는 최종 결과가 아닙니다. 전체 배선과 지연/hold 보정을 마칠 때까지 실행을 유지합니다.
- implementation CPU가08:06의11193초에서08:16의12113초로 증가했습니다. 가용RAM8.9GiB/F:여유661.3GiB, 로그 ERROR없음. 기능증거/RTL/제약 변경 및 BIT/HWH 배포 없음.

## 2026-10-07 07:56 PDT — 배치 완료, 물리 최적화 진행

- 전체 빌드 세션95967/main10748/implementation24948 유지. `place_design completed successfully`, 오류0,배치 elapsed59분23초이며 placed checkpoint를 저장한 뒤 `phys_opt_design`을 시작했습니다.
- 배치 후 WNS 추정은-0.395ns로 최종 timing 통과가 아닙니다. 사용자 지시대로 물리 최적화와 배선을 끝까지 수행한 후 최종 routed setup/hold/pulse-width/bus-skew를 평가합니다.
- implementation CPU10338초로 증가,가용RAM약10GiB/F:여유661.6GiB. 정상 진행 중이며 소스/제약 변경, 기능검증 중복, BIT/HWH 배포 없음.

## 2026-10-07 07:46 PDT — 배치 후 타이밍 최적화 진행

- 전체 빌드 세션95967/main10748/implementation24948은 그대로 실행 중입니다. Global/Detail Placement를 마치고 Phase4.1.1.2 Post Placement Timing Optimization에 진입했습니다. 최종 place_design/route_design 완료는 아직 아닙니다.
- implementation CPU가07:36의8613초에서07:46의9512초로 증가했습니다. ERROR없음, working set약17.5GiB/가용RAM2.4GiB, C:여유118GiB/F:662GiB입니다. 새 빌드나 시뮬레이션은 시작하지 않았습니다.
- 기능검증 결과는 유효하며 BIT/HWH는 최종 routed setup/hold/pulse-width/bus-skew 통과 후 교체합니다. source/제약 변경, commit/push/컴퓨터 종료 없음.

## 2026-10-07 06:55 PDT — place_design 진행 중

- 같은 전체 빌드 세션95967/main10748/implementation24948이 계속 실행 중입니다. opt_design을 마치고 `place_design`의 Phase1.3(Build Placer Netlist Model)에 진입했습니다. 두 로그에 ERROR는 없습니다.
- implementation CPU가06:45의3224초에서06:55의4305초로 증가했습니다. working set약15.2GiB/가용RAM4.8GiB, C:여유118GiB/F:662GiB입니다. 정상 진행이며 중복 실행하지 않습니다.
- 최종 routed timing은 아직 없고 BIT/HWH는 미배포입니다. 최신 GUI→RTL 및 폭 비교 증거는 그대로 유효하며 소스를 바꾸거나 검증을 중복 실행하지 않았습니다.

## 2026-10-07 06:15 PDT — impl_1 시작

- 동일 세션95967/main10748의 a3full3가06:14에 `impl_1`을 시작했습니다. implementation Vivado24948(06:14생성)은 checkpoint/IP/제약 로딩 중이며 CPU가 증가합니다. 로그 ERROR 없음, 가용메모리약16GiB/F:여유662GiB입니다.
- 합성 후 전체 자원: LUT289418(68.05%), FF369244(43.41%), DSP2583(60.46%), BRAM442.5(40.97%). 합성 후 timing 추정은 setup+0.402ns/hold-0.501ns/pulse-width-0.088ns이며 **최종 closure가 아닙니다**. Vivado 배치·배선·보정을 끝까지 진행합니다.
- 소스/기능검증/출력지연은 변경하지 않았습니다. 최종 routed setup/hold/pulse-width/bus-skew 통과 전 BIT/HWH 배포 없음.

## 2026-10-07 06:05 PDT — 전체 synth_1 완료, 구현 준비 중

- 같은 전체 빌드 세션95967 / `F:/Vivado_Output/a3full3`가 계속 실행 중입니다. `synth_1`은06:01에 성공 종료했고 해당 runme.log는0 Errors/0 Critical Warnings입니다. IP 하위 합성 로그에도 ERROR가 없습니다.
- main Vivado10748은 합성 checkpoint와 IP/clock 제약을 읽어 전체 설계를 여는 중입니다. CPU가 계속 증가하며, 가용 메모리약20GiB/F:여유662GiB를 확인했습니다. 아직 최종 배치·배선 timing 결과는 없습니다.
- 기능검증을 재실행하거나 BIT/HWH를 배포하지 않았습니다. 이후 implementation의 최종 setup/hold/pulse-width/bus-skew까지 확인합니다. 전체 빌드 중복 실행 및 commit/push/종료 없음.

## 2026-10-07 05:24 PDT — 모든 수정 RTL 기능 검증 완료, 전체 합성 진행

- 긴 폭 비교 세션34013이 exit0으로 완료됐습니다. `F:/Vivado_Output/a3width_pipe2`의 32/48/64 각200조건을 모두 검사했습니다. 32는34 overflow/166정상완료,48/64는200정상완료/overflow0/잔여면적과누적오차0입니다. 48/64 최대RC오차0.05461681895mV,종료잔류0.000863350555mV. 모든폭의 CSV가 파이프라인 수정 전과 바이트 동일합니다.
- width_comparison의 보고서/두 그림/rtl_source_manifest.json을 재생성하고 두 그림을 열어 확인했습니다. system_validation 네조건도 최신 RTL complete=true입니다. publisher::validate_functional_evidence는10개 evidence를 받아들였고, 누락/변조sourcehash 거부 검사도 통과했습니다(evidence_guard_check.json).
- **남은 활성 작업은 전체 FPGA 세션95967 / F:/Vivado_Output/a3full3**입니다. 로그 F:/Vivado_Output/a3full3_build.log. IP등록/BD검증/전체IP생성 완료 후05:15에 synth_1을 시작했습니다. 중복 시작하지 않습니다. 새HWH도7개48비트AWG,출력16/DC시작17,공통dac_clk_buf_BUFG_O300MHz,FIR/DDR8712설정을 통과했습니다(a3full3_hwh_preflight.json). 이는 최종timing/배포 완료가 아닙니다.
- RTL 변경이 없으면 기능시뮬레이션을 다시 돌릴 필요 없습니다. 전체배치·배선의최종setup/hold/pulse-width/bus-skew가남았습니다. 실패시실제경로에따라수정하고새GUI→RTL/폭회귀와전체빌드를진행합니다. 최종통과후publisher로같은XSA의BIT/HWH를교체합니다.
- heartbeat `awg-v3`가10분마다 확인합니다. 정상 진행은 조용히 유지하고 완료/실패/조치필요시에만 알립니다. 최종보고후PAUSED. commit/push/컴퓨터종료 없음.

## 2026-10-07 05:11 PDT — Vivado IP 등록 콜백 수정, a3full3 재시작

- a3full2/세션19061은 합성 전에 DC_AREA_BITS=48 검증에서 실패했습니다. 콜백의 Tcl expr 반환값1 대신 literal true/false를 반환하도록 xgui Tcl만 수정했습니다. 실제 Vivado catalog/BD 검사에서 default/explicit48 수락,32/64거부,최종48유지,exit0을 확인했습니다. 기대한 거부 ERROR도 포함해 ip_customization_fix에 모두 기록했습니다.
- **현재 전체 빌드는 세션95967, F:/Vivado_Output/a3full3, 로그 F:/Vivado_Output/a3full3_build.log**입니다. 앞선 두 빌드는 종료됐습니다. 중복 시작하지 않습니다. RTL이 바뀌지 않았으므로 새 GUI/시스템4PASS의 source hash는 유효합니다.
- 긴폭비교 세션34013은 동일하게 진행 중입니다. 완료 시 최신 보고서/그림/소스manifest를 생성해야 합니다.
- 현재 대화에 heartbeat 자동화 `awg-v3`를10분 간격으로 설정했습니다. 정상 진행은 조용히 확인하고 의미있는 완료/실패시에만 알립니다. 최종 성공과BIT/HWH배포/보고 또는 수정불가능한실패보고뒤PAUSED로바꿉니다. 새 commit/push/종료 없음.

## 2026-10-07 05:04 PDT — 수정 RTL의 GUI→RTL 네 조건 통과, 두 번째 전체 빌드 시작

- 보상 lookahead 파이프라인의 unit4개 및 실제 GUI/시스템4개 모두 exit0입니다. system_validation/status.json complete=true,각조건100점×2/두DAC200보상·reset/잔여0,명령값·시각불일치0. RF3조건200pulse폭오차0,DDR200trigger/800samples/400AXIwrite/8712delay. 기존 PMEM/DMEM과 네 조건 모두 바이트 동일합니다.
- 새 시스템 보고서·그래프를 생성하고 두 그림을 열어 확인했습니다. source manifest도 현재 RTL과 일치합니다. old evidence는 timing_failure_r1/system_validation에 보존했습니다.
- 전체 첫 빌드 a3full1은 정상 종료했지만 timing_closed=NO(WNS -0.553749ns,TNS -1470.887085ns,WHS +0.009491ns,THS0)로 wrapper exit1. failed BIT/XSA는 실행 폴더에만 있고 배포하지 않았습니다. 주요 실패 보고서는 timing_failure_r1에 복사했습니다.
- **두 번째 전체 빌드 세션19061**, `F:/Vivado_Output/a3full2`, 로그 `F:/Vivado_Output/a3full2_build.log`를 시작했습니다. 300MHz/기존제약/3jobs를 유지하며 전체합성→배치→배선→최종timing을 확인합니다. 중복 시작하지 않습니다.
- area 단독 OOC F:/Vivado_Output/a3o48pipe2: 내부setup +0.397ns/hold +0.029ns. 전체port의virtualboundaryhold -0.080ns를 보존하며 전체FPGAclosure로 주장하지 않습니다. 보고서는 ooc_lookahead_48.
- 긴32/48/64RC비교 재검증은 **세션34013**, `F:/Vivado_Output/a3width_pipe2`에서 실행 중입니다. 원래 폭 선택 비교는 이미 완료했으며 이번은 pipeline회귀입니다. 48/64고정전압100점완료,고정시간진행중. 완료 후 report_width_comparison.py --build ... --out analysis_results/awg_tuning_v3/width_comparison 으로 보고서/그림/새source manifest를 갱신하고열어확인합니다. 원래비교는 timing_failure_r1/width_comparison에보존했습니다.
- RTL소스는 새로운검증이 시작된뒤 변경하지 않았습니다. 최종 publisher는 system 및widthsourcehash를모두확인합니다. commit/push/컴퓨터종료 없음.

## 2026-10-07 04:36 PDT — 최종 route setup 실패, 보상 경로 파이프라인 수정

- a3full1은 routed WNS -0.554ns/TNS -1470.887ns/10184 endpoints, hold +0.009ns/THS0, pulse-width0. route 오류/미배선0. 타이밍 실패이므로 BIT/HWH를 배포하지 않습니다. main49628은 마지막 보고서 생성 중입니다.
- 실제 critical path: remainder → 이번 word 면적/부호 → area 누적. 추가 area → 절댓값 → multiplier 및 overflow → 상태-enable 경로도 확인했습니다.
- 보상 word/면적 delta를 출력 전 클록에 등록하고, captured area의 절댓값 계산을 PREPARE 첫 클록으로 옮겼습니다. overflow는 하위18비트 carry+상위 경계 패턴으로 검출하고 raw nonzero도 등록합니다. 외부16/17클록 지연은 설계상 유지하며 새 RTL로 재검증해야 합니다.
- 기존 4개 system 결과/RTL 원본은 timing_failure_r1에 보존했습니다. 기존 PASS를 수정한 RTL에 재사용하지 않습니다. 결과별 source manifest가 source hash를 검사하므로 새 actual GUI→RTL이 필수입니다.
- 초기 수정 boundary quotient/overflow RTL은 32/48/64 통과했습니다. 추가 carry 판정 무작위/경계 검사와 모든 unit/system 재실행을 계속합니다. commit/push/종료 없음.

## 2026-10-07 03:50 PDT — 배선 후 지연/skew 최적화 진행 중

- 여전히 유일한 활성 작업은 전체 빌드 세션49628/main12108/impl6788입니다. 새 시뮬레이터나 빌드를 실행하지 않았습니다.
- route_design의 초기 혼잡도6(64x64), 첫 배선 겹침90642개를0개로 해소한 뒤 전역 최적화4회(iteration0~3)를 완료했습니다. setup 중간 추정은 -0.958→-0.827→-0.735→-0.733ns, 마지막 TNS -1530.417ns입니다. hold의 마지막 수치 확인은 -0.043ns이며 이후 반복에는 N/A로 출력되었습니다.
- 현재 **Phase5 Delay and Skew Optimization / Phase5.1.1 Update Timing**입니다. 로그 갱신이 수분 동안 없어도 CPU가 계속 증가합니다(03:50 CPU17167초,working set약14GiB). 가용 메모리 약6.5GiB를 확인했습니다. 정상 실행을 중복/재시작하지 않습니다.
- 최종 routed timing/critical path 보고서는 아직 없으며 타이밍 통과가 아닙니다. 사용자의 지시대로 Vivado 구현을 끝까지 진행한 뒤 실제 위반이 남으면 해당 경로를 수정/파이프라인하고 필요한 GUI→RTL 재검증 및 전체 빌드를 수행해야 합니다.
- 소스 변경은 없이 상태 문서만 갱신했습니다. 기존 GUI/RTL 네 조건 및 폭 비교는 모두 완료했지만, RTL 수정 시 그 증거를 새 RTL 통과로 재사용하면 안 됩니다. BIT/HWH/XSA는 아직 배포하지 않았습니다.

## 2026-10-07 03:01 PDT — route_design 진행 중

- 동일한 전체 빌드 세션49628/main12108/impl6788이 유일하게 실행 중입니다. `F:/Vivado_Output/a3full1`을 재시작하거나 중복 실행하지 않습니다.
- place_design(58분8초), phys_opt_design(11분36초)은 오류0으로 완료했습니다. 물리 최적화 후 WNS 추정 -0.619ns입니다. 배치 혼잡 경고는 보존합니다.
- 현재 route_design, 배선 전 DRC 오류0, global clock routing 완료. Phase2.4의 중간 setup WNS -0.492ns/hold WHS -0.210ns입니다. **최종 타이밍 통과로 해석하지 않습니다.** 다음 배선·보정이 진행 중이고 CPU는 계속 증가합니다.
- 두 저장소 `git diff --check` 통과, 모두 awg_tuning_v3입니다. 새 commit/push/컴퓨터 종료 없음. GUI 사용자 JSON은 그대로 보존합니다.
- 네 GUI/시스템 RTL과 폭 비교는 이미 완료되어 중복 실행하지 않았습니다. BIT/HWH/XSA는 아직 배포하지 않았습니다. 최종 route 결과에 따라 필요한 물리 최적화/파이프라인 수정과 지연 재검증을 진행해야 합니다.

## 2026-10-07 02:30 PDT — 배치 완료, 물리 최적화/배선 대기

- 유일한 활성 빌드는 세션49628, main Vivado12108/impl6788, `F:/Vivado_Output/a3full1`입니다. 중복 실행하지 않습니다.
- `place_design` 오류0으로 완료(58분8초). 중간 WNS -0.995ns에서 배치 후 -0.768ns로 개선되었지만 **타이밍 통과가 아닙니다**. 배선 혼잡 경고가 있어 최종 routed timing 및 실제 critical path를 확인해야 합니다.
- 배치 checkpoint 저장 이후 기본 `phys_opt_design`, `route_design`, bitstream 단계가 이어집니다. 사용자 요청대로 합성/배치 추정치만으로 중단하지 않고 최종 구현 결과를 기다립니다.
- GUI 입력 그대로의 두 DC 모드와 추가 축반전/Stability를 포함한 네 시스템 RTL은 모두 완료했습니다. 폭 비교/시스템 그래프를 사용자에게 표시했습니다. RTL/GUI 소스는 완료된 검증 이후 변경하지 않았습니다.
- BIT/HWH/XSA 배포는 아직 하지 않았습니다. 최종 setup/hold/pulse-width/bus-skew 및 publisher 검사가 통과해야 합니다. F: 여유 약664GiB. commit/push/컴퓨터 종료 없음.

## 2026-10-07 01:57 PDT — place_design 진행 중

- GUI→RTL 최종 네 조건 complete=true, 그림 두 개를 열어 확인했습니다. 관련 테스트/시뮬레이션은 모두 종료되어 재실행할 필요가 없습니다.
- **유일한 활성 빌드 세션49628**, main Vivado12108/impl6788. `F:/Vivado_Output/a3full1/qstl_awg_v3.runs/impl_1/runme.log`의 opt_design 정상 완료(25분21초), 오류0. 현재 place_design의 Phase2.4(Global Placement Core)입니다. 이 계산은 로그가 한동안 갱신되지 않아도 CPU가 계속 증가하는 정상 진행 상태입니다. 마지막 메모리 약13GiB/가용8GiB 수준이었습니다.
- 합성 사용량 LUT290713/68.36%, FF364162/42.81%, DSP2583/60.46%. 이 값은 타이밍 통과 판정이 아닙니다.
- 최종 route/setup/hold/pulse-width/bus-skew 및 같은XSA BIT/HWH 검증·배포가 남아 있습니다. 전체 빌드를 중복 시작하지 않습니다.
- 완료 시 `publish_build.py F:/Vivado_Output/a3full1 --gui-dir C:/GIT_Workspace/PulseGenerator`를 사용합니다. 이제 기능 evidence는 네조건/두모드의 변경 없는 GUI 입력 일치를 필수로 검사하며, 함수 검사5개evidence는 이미통과했습니다.
- `TODO.md`에 v3 진행 상태를 추가했고 마지막 FPGA 배포 체크만 미완료입니다. `VALIDATION_REPORT.md`, 프로젝트/IP README의 진행 상태도 실제 완료 후 업데이트해야 합니다.

## 2026-10-07 01:17 PDT — 모든 GUI/시스템 RTL 완료, FPGA 구현만 진행 중

- 추가 normal-axis GUI fixed_voltage100점×2 실제RTL **세션56876 exit0**. result.json passed,각DAC200shot/reset/잔여0,명령값·시각불일치0,RF200폭오차0,DDR200trigger/800sample/400AXIwrite/8712clocks.
- 전체 **네 경우** complete=true로 최종 system report와 그림을 재생성했습니다. 두 DC 모드가 GUI의 Run Experiment 생성 결과를 변경 없이 실행한 조건을 각각 포함합니다. 축반전 스트레스와 Stability builder는 별도 조건으로 기록했습니다.
- `publish_build.py::validate_functional_evidence`도 통과(증거5개). 다만 전체 timing 조건은 아직 검사 전이므로 publisher 본 실행을 하지 않았습니다.
- 현재 유일한 활성 작업은 전체 FPGA **세션49628**,impl_1 PID6788,build `F:/Vivado_Output/a3full1`. opt_design 논리 최적화 완료/전력 최적화 단계입니다. 중복 실행하지 않습니다.
- 최종판 `VALIDATION_REPORT.md`, `SOFTWARE_RECHECK.md`,system_validation/REPORT.md 참조. BIT/HWH/XSA는 아직 배포하지 않았습니다.

## 2026-10-07 01:01 PDT — 추가 GUI 그대로 실행 검증

- 기존 fixed_voltage 축반전 경우는 GUI를 읽은 뒤 `sequence.sweeps.reverse()`를 호출한 스트레스 시험입니다. 실제 GUI 입력에서 변경 없이 실행한 경우로 분류하지 않습니다.
- GUI 입력 그대로 fixed_voltage/overlap_readout100점×2회를 추가 실행했습니다. **세션56876**, `F:/Vivado_Output/a3sim1/rc_precomp_repeat_reset_rf_duration_v3_100_voltage_gui_overlap_readout_awg_v3`,299723cycles. 기존 실행과 중복이 아닌 normal-axis GUI 프로그램입니다.
- `gui_widget_match.json`에 `gui_sequence_unmodified`와 `sequence_mutations`를 기록합니다. 기존 두 RF 경우는 메타데이터 재생성/동일 fingerprint 확인 완료입니다.
- 최종 system report와 publisher는 이제 **네 경우** 완료 및 두 DC 모드에서 GUI 생성 결과 그대로 실행한 조건을 필수로 검사합니다. 현재 status complete=false(추가 실행 pending). report는 완료 뒤 --allow-partial 없이 재생성합니다.
- 전체 FPGA는 link_design 완료 후 opt_design 중입니다. timing.xdc는 critical warning 없이 읽혔습니다. ios.xdc의 기존 SPARE/PMOD 미사용 포트40건 경고는 DRC0error이며 사용 중인 핀 제약을 풀지 않았습니다.

## 2026-10-07 00:58 PDT — GUI 재대조 완료, 전체 implementation 진행 중

- 최신 포화 ramp 면적 예측 수정 후 QICK 34개 / GUI DC·RC·readout 89개 검사 통과. `SOFTWARE_RECHECK.md` 참고.
- 완료된 세 RTL 조건을 `--reuse-snapshot --prepare-only`로 재생성하여 RTL 소스와 PMEM/DMEM fingerprint 일치를 확인했습니다. 두 RF 조건은 실제 MainWindow 입력도 다시 대조했습니다. 세 로그는 `replay_*_final.log`, 시뮬레이터는 중복 실행하지 않았습니다.
- `system_validation/REPORT.md`와 두 그림을 최신 증거로 다시 생성했습니다. 전체 complete=true, 모든 100점×2회 조건 passed입니다.
- 전체 Vivado 세션49628: synth 완료, **impl_1 실행 중** (`F:/Vivado_Output/a3full1/qstl_awg_v3.runs/impl_1/runme.log`). 아직 route closure 및 BIT/HWH/XSA 배포 전입니다.
- 합성 추정 setup +0.275ns, hold -0.501ns, pulse width -0.088ns입니다. 합성 추정 hold/pulse width만으로 멈추지 않고 실제 배치·배선 결과를 확인합니다.
- v3 timing.xdc의 존재하지 않는 clk_core 및 연결되지 않은 RFDC 출력 clock 쿼리를 정리했습니다. 실제 300MHz 주기와 세 비동기 host/fabric/DDR 교차 제약은 유지했고 AWG/tProcessor/RF/FIR 사이에 false path를 추가하지 않았습니다. implementation은 이 변경 후 시작했습니다.
- 두 저장소 awg_tuning_v3 유지. commit/push, 컴퓨터 종료 없음.

## 2026-10-07 00:36 PDT — 통합 RTL 최종 완료

- 세 시스템 경우 모두 result.json passed. 두 r2 RF 시험 세션94472/16567 정상 종료했습니다. 재실행하지 않습니다.
- 두 RF 경우 각각100점×2회/두DAC:명령값·시각불일치0,각DAC200보상/200reset/잔여0,RF200펄스/폭오차0,DDR200trigger/800samples/400AXI writes/8712clocks. 실제 MainWindow 입력과PMEM/DMEM일치 확인.
- Stability100점×2회도 통과. 최종 `system_validation/status.json` complete=true, `REPORT.md`, `system_accumulated_area.png`, `system_timing.png` 생성했습니다.
- 독립 RC 최대 오차: fixed_voltage 두DAC0.059391602/0.029074451mV; fixed_time0.068002466/0.033597107mV. 각 채널 유효1LSB보다 작습니다. 양자화된 실제입력 면적 보상 결과이지 기존SET증분오차 수정이 아닙니다.
- 전체Vivado세션49628만진행중. 개별IP합성완료,최상위synth_1실행중. 아직route/BIT/HWH/XSA배포전입니다.
- publish_build.py는 이제 위GUI→RTL결과완료도필수조건으로검사합니다. HWH의AWG/tProc/FIR/DDRsource가같은300MHznet이고RAMPstartup7임도검사합니다.

## 2026-10-07 00:14 PDT — 현재 상태 (아래 기록보다 우선)

- 실제 GUI 입력 → RTL 통과가 필수라는 사용자 지시를 다시 확인했습니다. 두 저장소 `C:/GIT_Workspace/{QSTL_QICK,PulseGenerator}`, `awg_tuning_v3` 유지. commit/push 및 종료는 하지 않습니다.
- 전체 FPGA 세션 **49628**, `F:/Vivado_Output/a3full1`, `F:/Vivado_Output/a3full1_build.log`: IP 합성 진행 중. BIT/HWH/XSA 아직 배포 전. 합성 추정치로 중단하지 말고 실제 place/route 결과를 확인합니다.
- Stability 실제 RTL `rc_precomp_repeat_reset_no_aux_grid_10x10_v3_stability_100_awg_v3_stability/result.json` 통과. 실제 Stability builder, 역방향/축반전, 100점×2회, 두 DAC 각 200회 보상/초기화, 잔여 면적 0, 명령 값/시각 불일치0. 이 경우 자체에는 RF/DDR가 없습니다.
- RF/DDR smoke2 `rc_precomp_repeat_reset_rf_duration_2x2_v3smoke2_overlap_readout_awg_v3` 통과: RF폭오차0, DDR8 triggers/64 samples/32 AXI writes/8712clocks, 두DAC reset8/잔여0. 첫 smoke는 monitor 누락으로 coverage 검사 실패였으며 통과로 세지 않습니다.
- RF100점 첫 실행 두 개는 재사용 DDR testbench의 standalone 600us watchdog으로 중간 종료했습니다. production IP/GUI 프로그램 오류로 확인된 것이 아닙니다. `RUN_REGRESSION=0`일 때 standalone watchdog을 끄고 상위 CYCLES 종료/전 shot 검사를 사용하도록 bench만 수정했습니다. 실패 evidence는 보존했습니다.
- 새 fixed_voltage/overlap_readout 100점×2 실제RTL: **세션94472**, `F:/Vivado_Output/a3sim1/rc_precomp_repeat_reset_rf_duration_v3_100_voltage_r2_overlap_readout_awg_v3`,299723clocks. 두DAC, reverseaxes, τ10us, DC20mV,4FIRsamples,±800/±400mV.
- 새 fixed_time/after_readout 100점×2 실제RTL: **세션16567**, `F:/Vivado_Output/a3sim1/rc_precomp_repeat_reset_rf_duration_fixed_v3_100_time_r2_after_readout_awg_v3`,351723clocks,DC1us,4FIRsamples. 중복 실행하지 않습니다.
- 두 RF시험 모두 실제 Qt MainWindow 설정복원 → `_experiment_run_arguments` → `build_qick_program`으로 생성한 PMEM/DMEM과 RTL 입력이 바이트 일치합니다. `gui_widget_match.json`, GUI 스크린샷을 저장했습니다. 보드 metadata는 offline fixture입니다.
- QICK33검사 통과. GUI DC/RC/readout timing 최종88검사 통과(`gui_timing_final.log`). 넓은 이전257검사 중 옛 Cartesian 표를 기대하던 테스트1개를 정수증분 유지 정책에 맞춰 수정했고 관련 검사를 재통과했습니다. 중간 실패는 gui_software.log에 보존했습니다.
- 새 RF 두 경우가 완료되면 각200shots/reset,RF200/width0,DDR200trigger/800sample/400AXIwrite/8712clocks 및 모든명령/IIR검사를 확인합니다. `axis_awg_tuning_v3/validation/report_system_validation.py --build F:/Vivado_Output/a3sim1 --out analysis_results/awg_tuning_v3/system_validation`으로 최종보고서/그림을 생성하고 열어확인합니다. 진행중만 --allow-partial.
- 전체 route setup/hold/pulse-width/bus-skew 통과 뒤 `qstl_awg_v3/publish_build.py F:/Vivado_Output/a3full1 --gui-dir C:/GIT_Workspace/PulseGenerator`로 같은XSA의BIT/HWH를 배포/검증합니다. 기존v2파일을 덮어쓰지 않습니다.
- 보상 잔여0은 실행디지털파형 기준입니다. 기존정수SET증분의 이상요청전압 오차는 별개입니다. DDR은 실제captureIP+synthetic timestamp stream으로 타이밍/개수/AXI를 검사하며 ADC실측/FIR산술 검사는 아닙니다.

## 2026-10-06 후속 상태 (최우선)

- 사용자가 합성 추정치로 멈추지 말고 Vivado 구현을 끝까지 진행하도록 지시했다.
- 48-bit OOC 첫 배선 setup -0.091 ns의 경로를 PREPARE의 lane prefix 레지스터와 마지막 잔여 면적 검사 분리로 수정했다. 출력 latency는 normal 5 + IIR 11 = 16, DC 시작 17 clocks로 유지했다.
- `F:/Vivado_Output/a3o48r2`: 내부 setup +0.334 ns, 내부 hold +0.046 ns. 가상 OOC 입력 경계 hold -0.089 ns는 남으므로 전체 FPGA closure로 주장하지 않는다. 증거는 `ooc_timing/pipeline_fixed/`.
- 최신 RTL의 area/fault/boundary/production 네 테스트 모두 통과. `F:/Vivado_Output/a3pipe1_tb_*`, 증거 `unit_validation/pipeline_fixed/`.
- 전체 7개 v3 AWG BD 빌드 실행 중: 세션49628, `F:/Vivado_Output/a3full1`, 로그 `F:/Vivado_Output/a3full1_build.log`. 합성/구현 중복 실행 금지. BIT/HWH/XSA 아직 교체하지 않았다.
- GUI v3의 실제 고정 증분 모델 평가, 면적 overflow/전압 검증, fixed_time/fixed_voltage 명령, 자동 shot reset 및 완료 대기 구현 중. 신규5 + 기존54 소프트웨어 검사 통과. 이후 DDR preview/다채널 초기화 보강은 재검사 예정.
- 실제 tProcessor/TMUX/RF/DDR 시뮬레이션 공통 라이브러리 `F:/Vivado_Output/a3sim1` compile-only 성공. v3 새 시스템 monitor는 모든 scalar sample의 면적과 보상 값/시작/완료, Python ledger, IIR reset을 대조한다. 첫 smoke 실행 세션8116, rf_duration 2×2×2 / fixed_voltage / overlap_readout. 전체100점 검사는 아직 완료되지 않았다.
- DDR 테스트는 실제 DDR capture IP + 합성 timestamp FIR stream이다. ADC 아날로그 데이터나 FIR 산술을 측정했다고 주장하지 않는다.
- 두 저장소 awg_tuning_v3 유지. commit/push 및 컴퓨터 종료는 하지 않는다.

## 최신 상태 (아래 이전 기록보다 우선)

- width_compare_r2 전체 완료. 48/64 수치 전부 동일, 디지털 잔여 면적/누적 0. RC 최대 오차 0.05461681895 mV, 종료 잔류 최대 0.000863350555 mV. 최종 width_comparison 그래프/CSV를 생성하고 두 그림을 확인했다.
- 사용자 요청대로 48-bit 선택. packaged DC_AREA_BITS=48. reciprocal Q64와 기존 IIR Q48/72는 별개의 산술이며 유지한다.
- PREPARE 마지막 cycle 및 EMIT에서 비영 raw 입력/잘못된 명령의 FAULT 우선순위를 수정했다. F:/Vivado_Output/awg3_48_guard_tb_dc_faults, tb_dc_area, tb_dc_boundaries, tb_width_awg 모두 통과. 415-shot area, 폭별 400-shot production, 산술 경계, fault/abort 포함.
- QICK dc_area.py, AxisAwgTuningV3 및 asm_v1 awg_dc 추가. 신규+기존 33 tests 통과.
- 현재 48-bit area OOC 300 MHz 구현: 세션85752, F:/Vivado_Output/a3o48r1/status.json 및 width_48.log. 중복 실행하지 않는다.
- GUI/전체 BD/tProcessor·RF·DDR 통합과 전체 FPGA timing closure는 아직 진행 전. 기존 BIT/HWH/XSA는 유지한다.

아직 v3 펌웨어 배포 완료 상태가 아닙니다. 새 commit/push는 하지 않았습니다.

## 현재 비트 폭 비교

- 실행 명령: `axis_awg_tuning_v3/validation/run_width_comparison.py --build F:/Vivado_Output/awg3_width_compare_r2`
- Python: `C:/Users/Measurement2/.conda/envs/qcodes2/python.exe`
- 배치 실행 세션: 64688. 실제 결과는 실행 폴더 `status.json`과 각 폭의 `run.log`, `width_sweep.csv`를 기준으로 확인합니다. 중복 실행하지 않습니다.
- 32/48/64-bit 각각 100점 × 두 DC 모드 = 200 shots. 동일한 100/10/400 µs 입력, 정수 전압 증분, 300 MHz / 16 samples, RC τ=300 µs.
- 32-bit overflow는 예상된 범위 부족입니다. 이를 보상 성공으로 세지 않습니다. 48/64-bit overflow 또는 비영 잔여 면적은 실패입니다.
- Windows batch가 `AREA_WIDTH=64`를 잘라 넘기던 최초 xelab 실패는 별도 top 모듈로 해결했습니다. `awg3_width_compare`는 실패 증거이며 최종 결과로 사용하지 않습니다.
- 한 지점 smoke(`awg3_width_smoke`)는 고정전압/시간 둘 다 통과했습니다. 전체 결과 대신 사용하지 않습니다.
- 그래프 명령: `validation/report_width_comparison.py --build F:/Vivado_Output/awg3_width_compare_r2 --out analysis_results/awg_tuning_v3/width_comparison`. 진행 중에만 `--allow-partial`을 추가합니다. 최종 실행에서는 제거해야 합니다.
- 전체 결과 확인 전 최종 비트 폭 선택이나 전체 Vivado BD/IP 반영을 진행하지 않습니다.

## 추가로 완료한 실제 RTL 검증

- `F:/Vivado_Output/awg3_width_production_r2`: 실제 AWG SET/RAMP -> 면적 엔진 -> 기존 IIR. 32/48/64 각각 100점 × 두 반복 × 두 DC 모드, 400 shots. 잔여 면적 0, shot 종료 후 IIR/출력 0, bypass 16 clocks 통과. 직접 명령 테스트이며 tProcessor/RF/DDR 통합 시험은 아닙니다.
- `F:/Vivado_Output/awg3_boundary_r3`: 양/음 signed overflow가 wrap 없이 오류로 검출됨. quotient/remainder 검사는 각각 10/18/19개 통과. 큰 area 레지스터를 직접 seed한 산술 경계 시험이며 수초~수시간 실제 파형을 실행했다고 해석하지 않습니다.
- `F:/Vivado_Output/awg3_area_unit_r2`: 415 shots 통과. 일반 sweep, 32-bit를 넘는 자연 누적, ±full-scale/mixed/random lane 합산, 한 샘플 부분 보상, zero area를 포함합니다.
- 증거 복사 위치: `unit_validation/` (첫 두 시험의 로그/해시/결과 및 production CSV).

## 다음 단계

1. 위 전체 폭 비교 완료 및 오차 그래프 최종 저장/열기.
2. 폭 선택을 위한 OOC resource/timing 검토. 준비된 `validation/synth_area_width.tcl`은 아직 실행하지 않았습니다. 이 결과는 전체 FPGA 타이밍과 별개입니다.
3. 구현 계획에 적힌 driver/assembler/GUI/실제 tProcessor·RF·DDR 시험, 새 v3 BD 전체 build와 timing closure, 같은 성공 XSA의 BIT/HWH 배포.

RTL 검토 메모: PREPARE의 마지막 cycle에서 비영 raw 입력을 검출한 FAULT가 EMIT 대입으로 덮이지 않도록 fault 우선순위를 정리해야 합니다. 정상 비교 입력은 이 경로를 지나지 않지만, 최종 IP에는 해당 비정상 명령 시험도 추가해야 합니다. 현재 비교 중 RTL은 수정하지 않고 source fingerprint를 보존합니다.
