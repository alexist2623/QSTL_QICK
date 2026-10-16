# DC·RC 보상 100×100 실물 sweep 결과

**12조건·120,000점 출력 및 취득을 완료했습니다. 모든 취득/명령/기록 무결성 검사는 PASS이며, 15 mV 전압 기준은 전체 PASS가 아닙니다.**

DAC4(AWG generator1)→CH1, DAC5(generator3)→CH2에서 두 축 각각 −300~+300mV 100점, identity matrix를 사용했습니다. 각 점은 10µs zero → 1µs RAMP → 10µs HOLD → 1µs RAMP → 10µs zero 및 하드웨어 DC 보상입니다. RC τ=10/20/30µs 각각에 DC 고정 전압300mV 또는 고정 시간10/20/30µs를 조합했습니다.

주 HOLD 판정은 **120,000점 중 PASS 119,893, FAIL 107**입니다. 두 채널 중 하나라도 실패하면 그 점은 FAIL입니다. 총240,000개 채널 측정 중 FAIL 107, 최대 절대 중앙구간 오차 19.516638mV입니다.

|RC τ(µs)|DC 모드|주 HOLD 실패점 /10,000|CH1 실패|CH2 실패|최대 오차(mV)|파형|
|---:|---|---:|---:|---:|---:|---|
|10|고정 전압 300mV|24|0|24|18.836|[파형](analysis_fixed_voltage_tau10_01/representative_waveforms.png)|
|10|고정 시간 10µs|41|1|40|19.517|[파형](analysis_fixed_time10_tau10_01/representative_waveforms.png)|
|10|고정 시간 20µs|0|0|0|14.401|[파형](analysis_fixed_time20_tau10_01/representative_waveforms.png)|
|10|고정 시간 30µs|41|41|0|17.759|[파형](analysis_fixed_time30_tau10_01/representative_waveforms.png)|
|20|고정 전압 300mV|1|0|1|15.687|[파형](analysis_fixed_voltage_tau20_01/representative_waveforms.png)|
|20|고정 시간 10µs|0|0|0|13.521|[파형](analysis_fixed_time10_tau20_01/representative_waveforms.png)|
|20|고정 시간 20µs|0|0|0|12.607|[파형](analysis_fixed_time20_tau20_01/representative_waveforms.png)|
|20|고정 시간 30µs|0|0|0|14.990|[파형](analysis_fixed_time30_tau20_01/representative_waveforms.png)|
|30|고정 전압 300mV|0|0|0|13.565|[파형](analysis_fixed_voltage_tau30_01/representative_waveforms.png)|
|30|고정 시간 10µs|0|0|0|14.717|[파형](analysis_fixed_time10_tau30_01/representative_waveforms.png)|
|30|고정 시간 20µs|0|0|0|14.524|[파형](analysis_fixed_time20_tau30_01/representative_waveforms.png)|
|30|고정 시간 30µs|0|0|0|12.506|[파형](analysis_fixed_time30_tau30_01/representative_waveforms.png)|

## 비교 기준과 검증 범위

이전 시험과 같은 DAC 직접 연결로 해석했습니다. 외부 RC/bias-tee 회로 통과 여부는 답변을 받지 못했으므로 외부 회로의 보상 성능을 검증했다고 주장하지 않습니다. RC가 켜진 DAC 출력은 요청 HOLD 전압에 적분 보상 기울기가 더해집니다. 따라서 평평한 요청 전압과 직접 비교하지 않고, 요청 V에 대한 이상적 RC 출력 V×[1+(0.5µs+HOLD 경과시간)/τ]를 기준으로 중앙5µs의 median(실측−기대값)을 판정했습니다.
각 capture의 출력 시작 전 0V 구간에서 채널별 offset 하나만 구해 모든 점에 동일 적용했습니다. 절대 median 오차가 15mV를 초과하면 FAIL, 15mV 이하면 PASS입니다. 점별 offset·gain 보정·시간 이동은 하지 않았습니다. 실제 fixed-point 명령의 RC 기대값은 별도 진단 열에 저장했고, GUI 요청 전압의 양자화 오차를 숨기기 위해 기준을 바꾸지 않았습니다.
실제 GUI 입력 → 생산 컴파일러의 PMEM/DMEM → 기존 보드의 유한 10,000점 실행 → 두 채널 SINGLE 취득 경로입니다. GUI RunWorker의 ADC/FIR/DDR/QCoDeS 경로 또는 새 RTL 시뮬레이션을 수행했다고 주장하지 않습니다. 모든 프로그램의 완료 counter는10,000/10,000이고, 각 실행 후 RC OFF+RESET·DC DISABLE·0V 정리 및 원래 scope 설정/STOP 상태 복원을 확인했습니다.

## DC 보상과 종료 구간

DC 보상 중앙구간은 실제 컴파일 명령으로 만든 정수 면적·RC 기대값과 별도로 비교했습니다. 주 HOLD 판정에 섞어 숨기지 않습니다.
- DC 중앙구간: {'PASS': 226485, 'FAIL': 67, 'INCOMPLETE': 13448}
- DC 뒤 zero 구간: {'PASS': 239782, 'FAIL': 218, 'INCOMPLETE': 0}
- 전체 sweep 종료 뒤 zero: 모든 채널 PASS=True
고정 전압 보상은 요청 면적이 작을 때 약0.1µs까지 짧아집니다. 이번 500ns 샘플 간격으로 충분한 표본을 얻지 못한 구간은 INCOMPLETE이며 PASS로 합산하지 않았습니다. 정확한 펄스 폭·면적 적분·아날로그 외부 RC 상태는 별도 고해상도 측정이 필요합니다. 내부 면적/overflow 레지스터는 현재 RPC로 관측하지 않았으며, 마지막 상태만으로 모든 shot의 내부 overflow0을 주장하지 않습니다.

## 원시 자료와 보존

두 채널 원시 IEEE block 총 67,200,264bytes를 16,207,018bytes로 무손실 gzip 저장했습니다. 해제 후 원본 SHA256을 모두 대조했습니다. 각 capture의 preamble·설정·UUID·샘플과 모든 점 CSV/파형 그림을 보존했습니다. 기록 간격500ns, main HOLD 중앙5µs에최소10samples입니다. 이번1.6V scope range에서 관측된 수직code 간격은 약6.69456mV이며 gain fitting으로 제거하지 않았습니다.
생산 Python 170파일 해시는 변경되지 않았습니다. 펌웨어/서버/RTL/사용자 JSON을 수정하지 않았습니다. 기존 범위0..400 및−400..400 준비증거와 검사기 초기 오류는 그대로 보존했습니다. −400..400·τ10의범위초과는 최종−300..300 시험 실패와 구분합니다. 준비용 normalized JSON 검사/step 부가 metadata 수정은 생산코드 변경이 아니며, 최종12개 bundle은 정정된 검증기로 새로 생성했습니다.

- [전체 집계 및 독립 검산](results.json)
- [측정 조건](campaign_plan.json)
- [실제 실행 완료 기록](physical_campaign_status.json)
- [독립 정수 RC 모델 및 검산](model_review/)
- 각 analysis 폴더: all_20000_holds.csv, all_10000_point_verdicts.csv, DC/zero CSV, full_record.png, primary_error_maps.png, representative_waveforms.png

Git commit/push는 이 증거 및 보고서만 대상으로 합니다.
