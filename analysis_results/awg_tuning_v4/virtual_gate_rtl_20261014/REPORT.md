# Virtual gate × parameter sweep — 현재 v4 추가 검증

실제 RTL **21/21 PASS**, GUI/compiler **14/17 PASS**, **3 실패**입니다. 전체 PASS로 표시하지 않습니다.

새 RTL 실행은 총 96점·192회, 명령 5,568개, 세 합산 DAC의 lane 샘플 18,709,728개를 검사했습니다. 각 통과 케이스의 exit 0, GUI PMEM/DMEM 일치, 준비된 RTL/입력 fingerprint, GUI/compiler 159개 소스 해시를 다시 확인했습니다.

## 입력과 검사 범위

실제 MainWindow 행렬·전압/HOLD/RAMP 설정창에 키보드 입력하고 Run Experiment 컴파일 PMEM/DMEM을 export와 바이트 비교했습니다. 비대칭 3×3 C의 모든 출력이 결합되며 Physical=C×Virtual, full scale 800/400/800mV입니다. 독립 C@V/정수 증분 계산, 모든 tProcessor 명령값·시각, 세 raw AWG와 세 IIR 모든 lane, DC 잔여 면적/reset 또는 RC/OFF bypass, 세 합산 출력의 합산식·반올림·2클록 파이프라인을 검사했습니다. RF 주파수/진폭 수치 검사는 RF1, 나머지 RF2/3은 고정 펄스의 시작/폭과 합산을 검사했습니다. 이번 작은 전압의 조합에서 clipping 경계 발생을 별도로 요구하지 않으며 기존 합산 단위 경계시험과 구분합니다.

각 케이스는 작은 직교 조합이며 모든 파라미터×모드×방향의 전체 곱을 망라했다고 주장하지 않습니다. 이전 100×2 회귀, 48비트 RC200회나 전체 timing을 이번 추가 실행으로 다시 센 것이 아닙니다.

| 실제 GUI→RTL 케이스 | 상태 | 점×반복 | 명령 비교 |
|---|---|---:|---:|
| hold_fixed_time | PASS | 9 × 2 | 513 |
| hold_fixed_voltage_descending | PASS | 9 × 2 | 513 |
| ramp_fixed_time | PASS | 4 × 2 | 233 |
| ramp_fixed_voltage_descending | PASS | 4 × 2 | 233 |
| rf_duration_fixed | PASS | 4 × 2 | 233 |
| rf_duration_extend | PASS | 4 × 2 | 233 |
| rf_frequency | PASS | 4 × 2 | 233 |
| two_voltage_axes | PASS | 9 × 2 | 513 |
| two_voltage_axes_reversed | PASS | 9 × 2 | 513 |
| rc_only | PASS | 4 × 2 | 233 |
| dc_only | PASS | 4 × 2 | 233 |
| compensation_off | PASS | 4 × 2 | 185 |
| square_frequency | PASS | 4 × 2 | 242 |
| square_amplitude | PASS | 4 × 2 | 242 |
| square_phase | PASS | 4 × 2 | 242 |
| cpmg_n1_tau200ns | PASS | 2 × 2 | 121 |
| cpmg_n1_tau400ns | PASS | 2 × 2 | 121 |
| cpmg_n2_tau200ns | PASS | 2 × 2 | 125 |
| cpmg_n2_tau400ns | PASS | 2 × 2 | 125 |
| cpmg_named_frequency | PASS | 4 × 2 | 241 |
| cpmg_named_duration | PASS | 4 × 2 | 241 |

## 남은 실패 / 제품 범위

- **UDD N=2, τ=0.2µs:** 실제 GUI의 outer software sweep 좌표를 production compiler에 넣었을 때 공유 tProcessor 포트0의 AWG 명령13클록/RF 명령15클록이 2클록 간격이라 필수3클록 조건을 위반하여 거부됐습니다. guard가 실패를 숨긴 것이 아니라 이 설정이 실행 불가인 것입니다. 이 조건의 RTL 실행은 하지 않았습니다. N=1의 두 τ와 N=2/τ=0.4µs는 별도 compiler 검사를 수행했습니다.
- **Quantum Circuit RF Loop n=1,3:** v4 합산으로 AWG 출력 latency가 18클록인데 circuit RF profile 판정은 v3의 16클록 조건을 요구하여 unknown latency로 거부됩니다. 임의 latency override나 생산 코드 수정으로 통과시키지 않았습니다.
- **Quantum Circuit의 Virtual matrix:** AWG Tuning의 행렬을 circuit 전압 계산에 적용하는 경로가 없습니다. n=0의 실제 GUI→compiler 검사에서는 AWG 설정에 저장된 비단위행렬과 별개로 circuit sequence가 단위행렬인 것을 확인했습니다. Quantum matrix+loop RTL PASS라고 표시하지 않습니다.
- **RF power/calibration:** 합산 DAC에서는 기존 RF 전용 커넥터 보정을 사용할 수 없도록 막혀 있습니다. 세 RF 출력×보정/보정 sweep 6개 GUI spec→production compiler 거부 검사가 통과했습니다. 정상 출력 시험 PASS와 다릅니다.

## 초기 실패와 재검사

RAMP의 실제 axis_kind 이름과 OFF의 초기 RC reset 정책을 새 helper가 잘못 가정한 초기 실패는 원본 로그/소스를 보존했습니다. 생산 코드나 허용오차를 바꾸지 않고 검증 helper만 수정했으며 별도 retry 폴더 결과를 사용합니다. GUI/compiler 초기 Quantum n=0의 반환 객체 접근 오류도 원본을 보존하고 실제 document의 timeline을 검사하도록 수정했습니다. 나머지 실제 compiler 거부 3건은 실패로 유지합니다.

기본/추가 controller의 finished_with_failures 및 exit 1은 초기 helper 실패를 보존한 값입니다. 최종 채택한 RTL 21회는 각각 exit 0입니다. results.json의 execution_complete는 실행 종료, complete는 전체 통과를 뜻하므로 현재 각각 true/false입니다. 추가 장시간 재실행이나 제품 수정으로 실패를 덮지 않았습니다.

## 보존과 한계

보호 59파일 변경 0, 검증 전후 생산 소스/사용자 JSON/펌웨어 변경 0개. 새 합성·commit/push·SSH 연결·보드 출력·펌웨어 업로드는 수행하지 않았습니다.
기존 정수 SET sweep add/rewind 양자화 오차를 해결했다는 의미가 아닙니다. AWG IIR 뒤 DDS 면적·clipping은 기존 DC 면적 보상 대상이 아닙니다. 보드 아날로그 및 ADC/FIR 산술 검증은 포함하지 않습니다.

[상세 결과/해시](results.json) · [초기 실행](status.json) · [추가 실행](additional_status.json) · [GUI/compiler 상세 실패](software_detailed.log) · [실패 시각·지연 진단](failure_diagnostics.json)

[실제 RTL 합산 파형](virtual_matrix_rtl_alignment.png) · [세 물리 출력 목표값](virtual_matrix_physical_targets.png)
