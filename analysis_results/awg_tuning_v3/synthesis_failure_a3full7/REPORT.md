# a3full7 초기 합성 실패 및 동일 조건 재개

2026-10-07 PDT. 새 프로젝트는 12:04:02에 시작했고, 12:08:05에 IP/상위 합성 작업을 요청했습니다. 12:42:13에 합성 실패로 Vivado가 종료됐습니다. 전체 실행 약38분11초이며 배치·배선 및 최종 timing 검사는 시작하지 못했습니다.

## 확인된 실패

- `d_1_axis_fir_decim_300to1_v2_0_0_synth_1`: Technology Mapping에서 `out of memory allocating 8388640 bytes` 두 번 기록 후 `EXCEPTION_ACCESS_VIOLATION`. crash log와 dump를 보존했습니다. 메모리 할당 실패는 확인됐지만 당시 시스템 전체 commit 사용량은 기록이 없어 확정하지 않습니다.
- `d_1_axi_smc_1_0_synth_1`: RAM/DSP 보고 직후 `TclStackFree: incorrect freePtr. Call out of sequence?`로 Vivado 내부 Tcl 런타임 종료. 별도 RTL 문법 오류나 timing 실패는 기록되지 않았습니다. 메모리 부족과 같은 원인인지는 확정하지 않습니다.
- 나머지 IP 합성128개는 정상 종료 marker가 있습니다. 상위 합성과 구현은 미완료입니다. 이는 전체 합성 통과가 아닙니다.

## 증거 보존과 재개 범위

실패한 두 run 폴더 전체와 초기 전체 로그, 원본 빌드 스크립트, .xpr, build_conditions 및 두 XDC 사본을 보존했습니다. `preservation_manifest.json`에 228개 파일 SHA256과 재개 직전 현재 기능증거15개의 검사를 기록했습니다. 원본 실패 결과를 PASS로 바꾸지 않습니다.

재개 스크립트: `F:/Vivado_Output/a3full7/resume_failed_ip_20261007.tcl`. Git 밖에 이번에 새로 만든 프로젝트를 이어서 사용합니다. 이전 v2/중단 프로젝트를 열거나 새로 복제하지 않습니다. 실패한 두 IP run만 reset/retry하고 이미 완료된128개는 유지합니다. 두 재시도 후 상위 합성·구현·보고 단계는 원본 빌드 Tcl의 동일 tail을 사용합니다.

`jobs=4`, `general.maxThreads=5`, 전략·디바이스·RTL·XDC를 유지합니다. 페이지파일/Windows 메모리 설정을 바꾸지 않았습니다. 48비트 기능/GUI→RTL/기본 검증은 현재 소스 해시와 일치하므로 xsim을 재실행하지 않습니다.

12:56:45 PDT의 첫 재개(세션18865/PID30520)는 IP상태 검사에서 실제run초기화/재합성 전에 종료됐습니다. 읽기 전용 상태질의로62개 Complete 및66개 Using cached IP results(모두100%)를 확인했습니다. 재개실행기는 이 두 완료상태를 성공marker/DCP와 함께 확인하며 미사용 IP구현run은 제외하도록 수정했습니다. 생산RTL/XDC를 변경한 것이 아닙니다. 첫 재개로그/스크립트와 상태질의로그를 보존했습니다.

13:00:50 PDT의 활성 재개는 세션67840/PID28100입니다. 스크립트는 `F:/Vivado_Output/a3full7/resume_failed_ip_retry2_20261007.tcl`, 로그는 `F:/Vivado_Output/a3full7_resume_failed_ip_retry2_20261007.log`입니다. 재개 성공 및 최종 timing은 아직 확인되지 않았습니다. 전체 timing과 publisher 검사를 통과하기 전 BIT/HWH를 배포하지 않습니다.

## 13:53 확인 — 두 IP 통과, 상위 run 초기화 누락

SmartConnect는13:05:22, FIR는13:06:47에 `synth_design Complete!`로 통과했습니다. 두 경우 모두 합성오류0이며 현재 총130개 IP의 성공결과가 있습니다. FIR 메모리 실패와 SmartConnect Tcl 오류는 동일 소스·설정 재시도에서 재발하지 않았습니다.

이후 `launch_runs synth_1`에서 `Run 'synth_1' needs to be reset before launching`으로13:06:48에 실행이 종료됐습니다. 상위 합성은 시작하지 않았습니다. 재개 스크립트에 기존 상위 run의 초기화가 빠진 절차 오류이며 RTL/timing 실패가 아닙니다.

`top_resume`에 당시 상위 run 폴더, 로그, 프로젝트 및 스크립트를 보존했습니다. 새 `F:/Vivado_Output/a3full7/resume_top_synth_20261007.tcl`은130개 IP 완료상태/성공marker/DCP를 확인하고 상위 `synth_1`만 초기화한 뒤 동일 항목을 다시 확인합니다. 이후 원본 빌드 tail을 실행합니다. jobs4/maxThreads5/생산소스/XDC/전략을 유지하고 기능증거15개도 현재소스로 재확인했습니다.

13:56:26에 상위 `synth_1` 실제 실행을 확인했습니다(세션41220/부모PID29132/합성자식PID21672). 상위초기화 전후 완료IP130개가 유지됐습니다. 전체합성과 최종 timing은 아직 미완료입니다.
