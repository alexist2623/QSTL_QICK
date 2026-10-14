# 두 번째 routed timing 실패와 후속 수정

대상: `F:/Vivado_Output/a3full3`, Vivado 2023.1, 300 MHz(3.333 ns).
전체 배선은 끝났지만 setup WNS -0.092 ns/TNS -2.165 ns, 58개 endpoint가
실패했습니다. Hold WHS +0.006 ns/THS 0, pulse-width 0, 배선 오류 0입니다.
이 빌드의 BIT/HWH는 배포하지 않습니다. 반올림 전 수치는 최종
`build_result.txt`에 보존합니다.

## 확인한 경로

| 실제 routed 경로 | Slack | 수정한 조합 경로 |
|---|---:|---|
| AXIS command register → AWG output register | -0.092 ns | SET/override/terminal target의 int32→fixed→DAC 중복 포화 검사를 직접 signed16 범위 검사로 대체 |
| Fixed-time remainder → fixed-voltage remaining | -0.084 ns | 두 모드가 공유하던 emitted_area 대신 fixed-voltage의 일정한 word 면적으로 remaining 갱신 |
| Remaining → planned compensation samples | -0.083 ns | 일정한 보상 코드의 부호를 PREPARE에서 미리 등록, 부분 lane은 부호에 따라 뺄셈 순서를 선택 |
| Raw sum → reciprocal multiplier register enable | -0.075 ns | 32/48비트에서 도달 불가능한 -2^63 검사를 compile-time 제거; 64비트 검사는 유지 |
| Fixed-time remainder → planned compensation samples | -0.068 ns | signed base와 signed(base+1)을 PREPARE에서 미리 등록 |
| RAMP fixed-point sample → output | -0.052 ns | 추가 후보: 정수부의 sign-extension bits reduction으로 포화 범위를 판단 |
| SquarePulse RC corrected sample → output | -0.051 ns | 추가 후보: 72비트 add/shift 대신 signed23 정수부 + half-LSB bit로 같은 반올림 결과 생성 |
| RAMP duration → output | -0.048 ns | 추가 후보: 기존 y_pipe 첫 stage에서 terminal lane mask를 계산하고 데이터와 함께 전달 |

`critical_paths.json`과 `d_1_wrapper_timing_summary_routed.rpt`가 원본 경로
근거입니다. 이는 잘못된 false-path 제약을 추가한 것이 아니며, 실제 데이터
연산과 모드별 입력을 정리한 RTL 수정입니다. Clock/기존 제약/비교 허용오차를
바꾸지 않았습니다.

전체 상세 보고서 생성 후 `all_reported_setup_failures.json`으로 58개 경로를
모두 보존했습니다. 추가 11개 위반은 위 표의 마지막 세 종류입니다. 해당
후보는 `timing_tail_candidate`에서 production 소스와 분리해 검증했습니다.
1,040개 RAMP 명령/1,637,952개 실제 sample 및 101,932개 Square 양자화 word,
Square enabled/bypass의 11클록 지연 검사가 모두 통과했습니다. 진행 중인
pipe3 시스템 실행의 증거를 보존한 뒤 production 반영과 새 GUI→RTL 검증을
진행합니다. 후보 단위 검증만으로 전체 FPGA 통과를 주장하지 않습니다.

Square 후보는 `floor(value / 2^50) + value[49]`를 23비트 부호 있는 정수로
계산합니다. 72비트 Q48 값에서 effective DAC 단위 4로 반올림할 때 하위
49비트는 carry에 영향을 주지 않습니다. 원래 ties toward +infinity와
-8192..8191 effective-code 포화를 유지하며, 73비트 독립 기준식으로 전
DAC 코드의 반올림 경계와 임의 72비트 값을 검증했습니다.

## 유지해야 하는 동작과 검증

- SET의 포화 범위 -32768..32764 및 2 LSB 정렬을 유지합니다. RAMP 시작값의
  fixed-point 변환은 변경하지 않습니다. 새 테스트는 내부 함수를 호출하지 않고
  실제 출력의 16 lanes를 독립 정수 clamp 기준과 비교합니다.
- 고정전압 보상은 실제 잔여 면적을 모두 출력합니다. 마지막 부분 lane의
  두 prefix를 14비트로 잘라도 선택된 차는 0..8191 이내여야 하며, 최대 진폭과
  각 lane 경계의 양쪽을 검증합니다.
- 고정시간의 -8192 effective-code 출력도 허용합니다. +8192는 허용하지 않습니다.
- IIR 이전 실제 면적, shot 종료 잔여 0, clear/reset 순서를 유지합니다.
- 출력 16클록/DC 시작 17클록/RF 및 DDR 지연은 변경하지 않는 설계입니다.
  새 단위검사와 실제 GUI→Verilog의 100지점×2회 검증으로 확인해야 합니다.
- 이전 완료 기능 결과는 이 폴더의 `system_validation`, `width_comparison`에
  보존합니다. 수정된 RTL의 통과로 재사용하지 않습니다.

수정 후 OOC 성공만으로 전체 FPGA timing closure를 선언하지 않습니다.
새 전체 합성·배치·배선의 setup/hold/pulse-width/bus-skew와 최신 소스 해시가
연결된 기능 검증이 모두 통과해야 BIT/HWH를 교체합니다.
