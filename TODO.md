# QICK / GUI TODO

작성일: 2026-10-03 (America/Vancouver)

기준 브랜치: QSTL_QICK 및 PulseGenerator 모두 `awg_tuning_v2`.
기준 커밋: QSTL_QICK `587f46d7`, GUI `3e78e0c`.
이 문서는 후속 작업을 기록하며, 아래 미해결 항목을 수정 완료했다는 의미가 아니다.

## 1. Virtual gate + 대규모 2차원 voltage hardware sweep

- [ ] Coupling으로 두 sweep 축에 의존하는 전압·ramp·DC 보상 값을 200×200에서도 DMEM 범위 내에서 처리하도록 개선한다.

**현재 재현된 문제**

- `Vphysical = M @ Vvirtual`에서 `M = [[1, 0.23], [-0.17, 1]]`을 사용했다.
- 두 DAC full-scale은 각각 ±800 mV, ±400 mV로 설정했다.
- Virtual X: 5→15 mV, Virtual Y: −9→7 mV, 각각 200점.
- AWG Tuning과 Stability Diagram 모두 200×200 hardware sweep 프로그램 생성 시 중단된다.
- `_exact_voltage_field_model()`이 두 축에 의존하는 필드에 40,000행 테이블을 요구하지만, tProcessor DMEM은 총 4,096-word이다. 여러 필드와 실행 상태도 이 메모리를 공유한다.
- 오류 예: `exact voltage sweep field (...) requires 40000 dependent rows; tProcessor DMEM cannot hold this coupled voltage/duration grid`.
- 실행 전에 검출되는 메모리 제한이다. 실행 도중 잘못된 전압이 출력되었다는 결과는 아니다.

**이미 확인한 범위**

- 두 virtual gate 20×20 × 지점당 2회: AWG Tuning 및 Stability Diagram 모두 실제 tProcessor/TMUX/AWG v2 Verilog RTL 통과.
- 한 virtual gate 200점 × 지점당 2회: tProcessor 명령 실행 모델 통과.
- 변환된 목표 전압, ramp 증분, DC 보상, RC 정수 연산, 반복 및 축 전환 초기화 확인.
- GUI 탭 전환과 설정 저장·복원 시 행렬 및 채널별 full-scale 유지 확인.
- 위 결과가 임의의 행렬·segment 수·grid 크기 모두의 동작을 보장하지는 않는다.

**완료 조건**

- DAC 양자화 전의 축별 기여를 분리하는 방식 등 메모리 절감 방법을 검토한다. 분리한 값을 각각 반올림해서 더할 경우 생기는 오차도 확인한다.
- 기존의 점별 nearest-DAC-code 정확도를 유지하고, ramp와 DC 보상이 실제 양자화된 목표값에 일치하도록 한다.
- 두 DAC, 양·음 coupling, 정방향·역방향, 두 축 순서, DC/RC 옵션, 채널별 서로 다른 full-scale을 검증한다.
- 200×200 명령 실행 모델과 실제 RTL 결과를 구분해 기록하고, 지원 한계를 넘으면 실행 전에 명확한 오류를 표시한다.

관련 코드: GUI `DCWaveformGeneratorGUI/qick_fine_tune_sweep.py`의 `_exact_voltage_field_model()`, `_build_sweep_register_plan()` 및 DMEM 테이블 할당 부분.

검증 자료: [결과 요약](analysis_results/virtual_gate_voltage_20261003/summary.json), [소프트웨어 재현 결과](analysis_results/virtual_gate_voltage_20261003/software_results.json). 이 자료들은 현재 로컬 검증 산출물이다.

## 2. RF duration sweep + voltage sweep

- [ ] 이전에 논의한 RF duration + voltage 복합 hardware sweep의 남은 제한과 미검증 조합을 점검한다.

**기존 이슈 및 현재 상태**

- RF duration이 변하면 `extend_by_rf_duration` 모드에서는 이후 segment의 시각과 AWG 유지 시간이 달라진다. 이에 따라 DC 보상 면적에 voltage × duration 항이 생기므로 RF length만 갱신해서는 충분하지 않다.
- `fixed` 모드와 `extend_by_rf_duration` 모드를 구분하고, 이후 AWG/RF/readout/trigger 시각, 보상 전압 또는 보상 시간, 반복 종료 시각을 함께 확인해야 한다.
- 과거 짧은 RF 펄스가 periodic 3클록 블록 경계에서 종료되어 1~2클록 길어지던 문제는 oneshot length를 직접 지정하는 방식으로 수정되었다.
- 20×20 × 2회 짧은 RF duration + voltage sweep은 기존 RTL 기록에서 통과했다. AWG v2의 `rf_duration` 사례도 800개 RF 펄스의 길이 및 명령 시각 검사를 통과했다. 이 범위를 미해결 오류로 다시 기록하지 않는다.
- 긴 펄스는 기존 요청대로 periodic 방식을 유지한다. 실행할 sweep 지점 중 하나라도 65,535 generator clocks를 초과하면 해당 duration 축 전체가 periodic이다.
- 이 경우 블록 경계에 따른 종료 지연은 남아 있다. 기존 경계 테스트에서는 65,536클록 요청이 65,538클록 출력이었다. 이는 보존된 긴 펄스 동작이며 exact timing 통과가 아니다.

**후속 확인 사항**

- 200×200에서 DC `fixed_time` / `fixed_voltage`, RF segment `fixed` / `extend_by_rf_duration`, 축 순서 및 sweep 방향별 지원 범위를 정리한다.
- 기존 `fixed_voltage` 200×200 사례에는 전체 point table 대신 계수 행을 사용하는 소프트웨어 검사가 있다. 이것을 모든 조합의 지원 또는 200×200 전체 RTL 검증으로 확대 해석하지 않는다.
- Voltage × duration에 의존하는 DC 보상 및 기타 필드가 큰 joint table을 요구하는 조건을 재현하고, DMEM 절감 시 전압 반올림·보상 정확도·축 초기화를 함께 검증한다.
- Virtual gate를 추가한 조합도 별도 검증한다. 위 1번의 coupling 메모리 문제와 동시에 발생할 수 있다.
- 긴 periodic RF의 요청 길이와 실제 길이 차이를 사용자에게 어떻게 표시할지 검토한다. 기존에 요청된 긴 펄스 정책을 임의로 바꾸지 않는다.

관련 코드: GUI `DCWaveformGeneratorGUI/qick_fine_tune_sweep.py`, `test_rf_duration_oneshot.py`, `test_rc_sweep_matrix.py`.

기존 증거: [RF duration 검증 보고서](analysis_results/rc_precompensation_v1/rf_duration_oneshot_v1/REPORT.md), [AWG v2 RF duration + voltage RTL 결과](analysis_results/awg_tuning_v2/rtl_evidence/rc_precomp_repeat_reset_rf_duration_20x20_exact_voltage_awg_v2.json).
