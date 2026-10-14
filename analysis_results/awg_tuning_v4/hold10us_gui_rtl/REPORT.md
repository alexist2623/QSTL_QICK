# 10µs RAMP/HOLD GUI → RTL 추가 검증

실제 GUI MainWindow 설정 → Run Experiment 컴파일 경로 → PMEM/DMEM → 실제 tProcessor/TMUX/AWG/DDS/합산/최종 출력 지연 RTL을 실행했습니다. 두 조건 모두 PASS입니다. 보드에서 아날로그 출력을 측정한 결과는 아닙니다.

| 설정 | 검증 결과 |
|---|---|
| 공통 입력 | 초기 0V SET 1µs + RAMP 10µs → HOLD 10µs → RAMP 10µs → HOLD 10µs |
| AWG1 / AWG2 / AWG3 | 0 → +10 → 0mV / 0 → −5 → 0mV / 0 → +2.5 → 0mV |
| RF | 세 RF 모두 190MHz, gain 2000, delay 0, duration 10µs |
| 조건 1 | Anchor SET = 첫 HOLD (`set_1`) |
| 조건 2 | Anchor SET = 둘째 HOLD (`set_2`) |
| 반복 | 각 조건 1점 × 2회, 세 RF/AWG 쌍 모두 검사 |
| 보상 | DC fixed_time 1µs + RC τ=10µs 활성화 |
| 구간 길이 설정 | Keep AWG segment length fixed; Keep pulse inside anchor SET 활성화 |
| GUI 입력 일치 | 두 조건 모두 PMEM / DMEM 바이트 일치; GUI sequence 변경 없음 |
| 명령 값 / 명령 시각 | 불일치 0 / 0 |
| RF와 실제 HOLD 시작 차이 | 0클록 |
| RF 폭 | 모든 12개 펄스 3000클록 = 10µs; 폭 오차 0 |
| 예상 밖 RF 펄스 | 0; RAMP 구간에서 RF 꺼짐 |
| 최종 DAC 샘플 | 2,828,640개 독립 signed 합산/포화/반올림 비교 통과 |
| DC 면적/초기화 | 각 출력 각 조건 2회 보상/초기화 확인, 잔여 정수 면적 0 |

## 기존 RAMP guard와 실제 출력 시각

기존 v3부터 RAMP 뒤에 `ramp_guard_cycles=1`이 있습니다. RAMP 데이터 자체는 정확히 48000샘플(3000클록, 10µs)이지만 다음 HOLD 경계는 이 1클록(3.333ns) 뒤입니다. GUI의 이상적인 시간축에는 이 guard가 표시되지 않습니다. 이번 검증에서는 이를 오차 없이 10µs 간격이라고 처리하지 않았습니다.

첫 RAMP 시작을 0으로 잡으면:

| RF 선택 | 이상적인 GUI 표시 | 실제 RTL RF 시작–종료 | 실제 HOLD와 차이 |
|---|---|---|---|
| 첫 HOLD | 10–20µs | 10.003333–20.003333µs | 0클록 |
| 둘째 HOLD | 30–40µs | 30.006667–40.006667µs | 0클록 |

따라서 RF는 선택한 실제 HOLD 전체에 맞고 RAMP와 겹치지 않습니다. 다만 이상적인 40µs 타임라인과는 guard 두 개만큼 차이가 납니다. 기존 guard/RTL/GUI/드라이버/XDC/펌웨어는 변경하지 않았습니다. 최종 출력 검사에는 합산 2클록과 기존 출력 지연 10클록을 포함했습니다.

## 증거

파형에서 점선은 RC 이전의 실제 AWG 값이고 파란 선은 RC 보상이 적용된 값입니다. HOLD 중 파란 선이 기울어지는 것은 RC 보상 동작입니다.

- [실제 RTL 출력 파형](rtl_hold10us.png)
- [첫 HOLD GUI 설정](hold1/gui_input.png), [둘째 HOLD GUI 설정](hold2/gui_input.png)
- [첫 HOLD 결과](hold1/result.json), [둘째 HOLD 결과](hold2/result.json)
- [입력/소스/증거 해시 및 전체 결과](status.json)
- 전체 16-lane 샘플 CSV와 isolated simulator snapshot은 각 결과의 `build_folder`에 있습니다.

생성된 테스트 사본과 추가 모니터만 새 폴더에 만들었습니다. 기존 최종 검증 보고서/해시와 배포 펌웨어를 덮어쓰지 않았고, 합성도 다시 실행하지 않았습니다. 합산은 AWG IIR 뒤이므로 AWG DC 보상은 추가 RF 면적이나 최종 clipping을 보상하지 않습니다.

후처리 기록: 두 xsim 실행은 RTL COMPLETE와 모든 RTL monitor 통과로 종료했습니다. 첫 Python 후처리에서는 새 검사기의 출력 지연 가정이 잘못되어 실패했으며, 실제 IP 설정 `axis_register_slice_nb N=10`에 맞게 검사기를 정정했습니다. 같은 저장 CSV를 `--analyze-only`로 재검사하여 모든 샘플이 통과했습니다. RTL 또는 허용오차는 변경하지 않았으며 시뮬레이션도 반복하지 않았습니다. 최초 로그는 `hold1_run.log`, `hold2_run.log`, 최종 후처리 로그는 `hold1_analysis.log`, `hold2_analysis.log`로 보존했습니다.
