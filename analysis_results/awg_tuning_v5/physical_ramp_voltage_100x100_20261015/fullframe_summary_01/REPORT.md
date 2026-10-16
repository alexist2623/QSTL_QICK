# RAMP duration × 전압 100×100 실물 검증

요청 48조건 중 16조건은 RC 출력 범위 검사에서 거부되어 실행하지 않았고, 32조건·320,000점을 취득했습니다. 실행한 자료의 취득·분석·해시 무결성은 확인했습니다. 범위 거부와 측정 FAIL/미해결이 있으므로 요청 전체를 PASS로 표시하지 않습니다.

DAC4(AWG1)→CH1, DAC5(AWG3)→CH2를 연결하고 한 출력만 활성화하며 반대 출력은 0V로 유지했습니다. 상승 또는 하강 RAMP 중 하나만 10ns~1µs 100점으로 sweep하고 다른 RAMP는 1µs로 고정했습니다. 전압은 −400~+400mV 100점이며 duration이 바깥 축, 전압이 안쪽 축입니다. HOLD10µs, identity matrix, RC τ10/20/30µs, DC 고정300mV 또는 고정10/20/30µs 조건입니다.

- 활성 출력 주 HOLD: {'PASS': 319968, 'FAIL': 32, 'INCOMPLETE': 0}
- 비활성 출력 0V 유지: {'PASS': 320000, 'FAIL': 0, 'INCOMPLETE': 0}
- 점 단위: PASS 319,968, FAIL 32; 어느 채널이라도 실패하면 해당 점은 FAIL입니다.
- 최대 중앙구간 절대 median 오차: 20.283694mV

|RAMP|활성 DAC|RC τ(µs)|DC 모드|활성 HOLD FAIL|비활성 zero FAIL|DC FAIL / 미해결|파형|
|---|---:|---:|---|---:|---:|---:|---|
|rising|4|20|10µs 고정|0|0|1 / 0|[파형](../analysis_rising_dac4_fixed_time10_tau20_01/representative_waveforms.png)|
|rising|4|20|20µs 고정|0|0|0 / 0|[파형](../analysis_rising_dac4_fixed_time20_tau20_01/representative_waveforms.png)|
|rising|4|20|30µs 고정|0|0|0 / 0|[파형](../analysis_rising_dac4_fixed_time30_tau20_01/representative_waveforms.png)|
|rising|4|20|300mV 고정|15|0|44 / 1,664|[파형](../analysis_rising_dac4_fixed_voltage_tau20_01/representative_waveforms.png)|
|rising|5|20|10µs 고정|1|0|0 / 0|[파형](../analysis_rising_dac5_fixed_time10_tau20_01/representative_waveforms.png)|
|rising|5|20|20µs 고정|0|0|0 / 0|[파형](../analysis_rising_dac5_fixed_time20_tau20_01/representative_waveforms.png)|
|rising|5|20|30µs 고정|0|0|0 / 0|[파형](../analysis_rising_dac5_fixed_time30_tau20_01/representative_waveforms.png)|
|rising|5|20|300mV 고정|0|0|4 / 1,640|[파형](../analysis_rising_dac5_fixed_voltage_tau20_01/representative_waveforms.png)|
|falling|4|20|10µs 고정|0|0|0 / 0|[파형](../analysis_falling_dac4_fixed_time10_tau20_01/representative_waveforms.png)|
|falling|4|20|20µs 고정|0|0|0 / 0|[파형](../analysis_falling_dac4_fixed_time20_tau20_01/representative_waveforms.png)|
|falling|4|20|30µs 고정|0|0|0 / 0|[파형](../analysis_falling_dac4_fixed_time30_tau20_01/representative_waveforms.png)|
|falling|4|20|300mV 고정|1|0|4 / 1,897|[파형](../analysis_falling_dac4_fixed_voltage_tau20_01/representative_waveforms.png)|
|falling|5|20|10µs 고정|0|0|0 / 0|[파형](../analysis_falling_dac5_fixed_time10_tau20_01/representative_waveforms.png)|
|falling|5|20|20µs 고정|0|0|0 / 0|[파형](../analysis_falling_dac5_fixed_time20_tau20_01/representative_waveforms.png)|
|falling|5|20|30µs 고정|0|0|0 / 0|[파형](../analysis_falling_dac5_fixed_time30_tau20_01/representative_waveforms.png)|
|falling|5|20|300mV 고정|0|0|6 / 1,663|[파형](../analysis_falling_dac5_fixed_voltage_tau20_01/representative_waveforms.png)|
|rising|4|30|10µs 고정|0|0|0 / 0|[파형](../analysis_rising_dac4_fixed_time10_tau30_01/representative_waveforms.png)|
|rising|4|30|20µs 고정|0|0|0 / 0|[파형](../analysis_rising_dac4_fixed_time20_tau30_01/representative_waveforms.png)|
|rising|4|30|30µs 고정|0|0|0 / 0|[파형](../analysis_rising_dac4_fixed_time30_tau30_01/representative_waveforms.png)|
|rising|4|30|300mV 고정|0|0|0 / 1,653|[파형](../analysis_rising_dac4_fixed_voltage_tau30_01/representative_waveforms.png)|
|rising|5|30|10µs 고정|0|0|0 / 0|[파형](../analysis_rising_dac5_fixed_time10_tau30_01/representative_waveforms.png)|
|rising|5|30|20µs 고정|1|0|0 / 0|[파형](../analysis_rising_dac5_fixed_time20_tau30_01/representative_waveforms.png)|
|rising|5|30|30µs 고정|11|0|0 / 0|[파형](../analysis_rising_dac5_fixed_time30_tau30_01/representative_waveforms.png)|
|rising|5|30|300mV 고정|1|0|3 / 1,663|[파형](../analysis_rising_dac5_fixed_voltage_tau30_01/representative_waveforms.png)|
|falling|4|30|10µs 고정|0|0|0 / 0|[파형](../analysis_falling_dac4_fixed_time10_tau30_01/representative_waveforms.png)|
|falling|4|30|20µs 고정|0|0|0 / 0|[파형](../analysis_falling_dac4_fixed_time20_tau30_01/representative_waveforms.png)|
|falling|4|30|30µs 고정|0|0|0 / 0|[파형](../analysis_falling_dac4_fixed_time30_tau30_01/representative_waveforms.png)|
|falling|4|30|300mV 고정|0|0|0 / 1,863|[파형](../analysis_falling_dac4_fixed_voltage_tau30_01/representative_waveforms.png)|
|falling|5|30|10µs 고정|0|0|0 / 0|[파형](../analysis_falling_dac5_fixed_time10_tau30_01/representative_waveforms.png)|
|falling|5|30|20µs 고정|0|0|0 / 0|[파형](../analysis_falling_dac5_fixed_time20_tau30_01/representative_waveforms.png)|
|falling|5|30|30µs 고정|2|0|0 / 0|[파형](../analysis_falling_dac5_fixed_time30_tau30_01/representative_waveforms.png)|
|falling|5|30|300mV 고정|0|0|2 / 1,659|[파형](../analysis_falling_dac5_fixed_voltage_tau30_01/representative_waveforms.png)|

## 판정 기준과 한계

DAC 직접 연결로 해석한 RC 선보상 기대값은 V요청×[1+(요청 상승RAMP 길이/2+HOLD 경과시간)/τ]입니다. 각 점의 상승 길이를 사용하며 실제 컴파일된 HOLD 시각을 기준으로 중앙5µs를 선택합니다. 1µs 상승에만 해당하는 0.5µs 항을 모든 점에 재사용하지 않습니다. 하강 sweep은 상승1µs를 그대로 사용합니다.
출력 전 baseline에서 채널별 offset 하나만 정해 모든 점에 고정 적용하고 median(실측−기대값)의 절대값이15mV를 초과하면 FAIL입니다. gain·점별offset·점별시간 fitting은 없습니다. 이는 모든 샘플/전체 파형의 ±15mV 보장을 뜻하지 않습니다. 실제 정수 명령·RC 기대값은 별도 진단이며 요청 전압·길이 기준을 대체하지 않습니다.
활성 채널의 첫 −200mV 하강 crossing으로 전체 기록에 시간 offset 하나를 적용하고, 실제 명령 시각으로100개 duration 행의 첫 edge를 검증했습니다. 각 행에 서로 다른 관측 edge가 대응하고 잔차는2µs 미만이어야 합니다. 전압·duration에 따라 변하는 point 간격을 고정 주기로 가정하지 않습니다.
기록 간격은500ns 이하이고 중앙5µs에 최소10 native samples를 요구합니다. 이 전체 sweep 기록으로10ns RAMP 모양이나 정밀 길이를 인증하지 않습니다. 정렬 잔차·수직 양자화·아날로그 대역폭은 제거하지 않았으므로 FAIL 원인을 바로 RTL/DAC gain으로 단정할 수 없습니다. 별도 high-resolution 대표 측정은 이 집계에 포함하지 않았습니다.

## DC 보상 및 zero

활성 출력 DC 중앙구간: {'PASS': 306234, 'FAIL': 64, 'INCOMPLETE': 13702}. 비활성 출력 DC 320,000구간은 면적0·zero-valued 명령으로 N/A이며 보상 pulse 성공 수에 포함하지 않았습니다. 비활성 출력은 주 HOLD와 DC 뒤 zero로 별도 검사했습니다.
DC 뒤 zero: {'PASS': 639827, 'FAIL': 173, 'INCOMPLETE': 0}. 전체 종료 뒤 두 채널 zero 모두 PASS=True.
활성 DC 구간에서 native 표본이3개 미만이면 INCOMPLETE로 남겼으며 PASS로 합산하지 않았습니다. 보상 구간의 정밀 폭·아날로그 면적 적분·외부 RC 회로 상태·모든 shot의 내부 overflow를 측정한 것은 아닙니다.

## 준비 단계 최초 실패와 검토된 재실행

최초 준비 batch는 25조건 exit0 뒤 rising_dac5_fixed_voltage_tau30의 모델·파일 작성이 끝난 후 SIP 0xc0000005 접근 위반으로 종료됐습니다. 최초 complete=false 및 Windows 오류 기록을 보존했습니다. 독립 CLI 종료 처리만 적용한 새 검증 helper로 같은 조건을 다시 실행하여 exit0을 확인하고, ASM/PMEM/DMEM·압축 해제 기대값/모델·GUI/컴파일러 자료가 원본과 동일함을 해시로 재검사했습니다.
기존 exit0 25조건은 재실행하지 않았으며 검토된 재실행1조건과 남은22조건 재개 결과를 별도로 합쳤습니다. 최종 준비 결과는32조건 준비 완료·16조건 RC 범위 거부입니다. 최초 오류를 물리 측정 FAIL과 섞거나 원래부터 exit0였다고 표시하지 않습니다.
- [원본 준비 상태](../preparation_batch_status.json), [재실행 대조](../preparation_resume_retry_comparison.json), [병합 준비 상태](../preparation_merged_status.json)

## 보존 및 실행 범위

전체 두 채널 raw IEEE block 179,200,704bytes를 무손실 gzip 38,788,517bytes로 보존하고 압축 해제 SHA256과 payload SHA256을 재대조했습니다. 생산 소스 170파일 해시, 실행 전후 DAC current, 완료 counter, zero 정리 및 scope 복원을 확인했습니다.
실제 GUI 설정 → 생산 컴파일러 → 기존 v5 하드웨어 → 두 채널 SINGLE 취득 경로입니다. 실물 실행은 run_physical.py가 수행했고 이 집계기는 보존된 자료를 오프라인 분석했습니다. 새 합성·펌웨어 교체·생산 코드 수정은 없었습니다. GUI RunWorker의 ADC/FIR/DDR/QCoDeS 경로 또는 새 RTL 시뮬레이션 PASS로 표현하지 않습니다.

- [독립 집계](results.json)
- [검토 입력 해시](input_hashes.json)
- [전체 물리 실행 기록](../physical_campaign_status.json)
- [전체 분석 기록](../analysis_campaign_status.json)

## 범위 거부: 물리 실행 없음

- rising_dac4_fixed_time10_tau10: `RC-compensated DAC output exceeds range: awg_0, sweep corner 9900. Predicted bounds [-820, +439.945] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
- rising_dac4_fixed_time20_tau10: `RC-compensated DAC output exceeds range: awg_0, sweep corner 9900. Predicted bounds [-820, +220.106] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
- rising_dac4_fixed_time30_tau10: `RC-compensated DAC output exceeds range: awg_0, sweep corner 9900. Predicted bounds [-820, +146.63] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
- rising_dac4_fixed_voltage_tau10: `RC-compensated DAC output exceeds range: awg_0, sweep corner 9900. Predicted bounds [-820, +300] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
- rising_dac5_fixed_time10_tau10: `RC-compensated DAC output exceeds range: awg_1, sweep corner 9900. Predicted bounds [-820, +439.945] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
- rising_dac5_fixed_time20_tau10: `RC-compensated DAC output exceeds range: awg_1, sweep corner 9900. Predicted bounds [-820, +220.106] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
- rising_dac5_fixed_time30_tau10: `RC-compensated DAC output exceeds range: awg_1, sweep corner 9900. Predicted bounds [-820, +146.63] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
- rising_dac5_fixed_voltage_tau10: `RC-compensated DAC output exceeds range: awg_1, sweep corner 9900. Predicted bounds [-820, +300] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
- falling_dac4_fixed_time10_tau10: `RC-compensated DAC output exceeds range: awg_0, sweep corner 0. Predicted bounds [-820, +420.219] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
- falling_dac4_fixed_time20_tau10: `RC-compensated DAC output exceeds range: awg_0, sweep corner 0. Predicted bounds [-820, +209.968] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
- falling_dac4_fixed_time30_tau10: `RC-compensated DAC output exceeds range: awg_0, sweep corner 0. Predicted bounds [-820, +140.21] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
- falling_dac4_fixed_voltage_tau10: `RC-compensated DAC output exceeds range: awg_0, sweep corner 0. Predicted bounds [-820, +300] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
- falling_dac5_fixed_time10_tau10: `RC-compensated DAC output exceeds range: awg_1, sweep corner 0. Predicted bounds [-820, +420.219] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
- falling_dac5_fixed_time20_tau10: `RC-compensated DAC output exceeds range: awg_1, sweep corner 0. Predicted bounds [-820, +209.968] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
- falling_dac5_fixed_time30_tau10: `RC-compensated DAC output exceeds range: awg_1, sweep corner 0. Predicted bounds [-820, +140.21] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
- falling_dac5_fixed_voltage_tau10: `RC-compensated DAC output exceeds range: awg_1, sweep corner 0. Predicted bounds [-820, +300] mV; allowed [-801.48, +801.48] mV. Includes DC compensation and the zero-input hold before IIR reset. Reduce voltage/duration or increase RC tau.`
