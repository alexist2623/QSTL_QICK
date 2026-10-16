# DC·RC + RAMP duration × voltage 실물 검증 결과

요청한 **10ns~1µs RAMP duration 100점 × −400~+400mV 전압 100점**을 검사했습니다. 요청 48조건 중 32조건·320,000점을 실제 출력·취득했고, 16조건은 RC 출력 한도 검사에서 거부되어 출력하지 않았습니다. **전체 PASS는 아닙니다.**

상승·하강 RAMP와 DAC4·DAC5를 각각 분리하여 identity matrix와 100×100 크기를 유지했습니다. 반대 RAMP는 1µs, 반대 DAC는 0V, HOLD는 10µs입니다. RC τ 10/20/30µs × DC 고정 300mV 또는 고정 10/20/30µs의 12조합을 유지했습니다.

|측정 구간|PASS|FAIL|미판정|
|---|---:|---:|---:|
|활성 출력 HOLD|319,968|32|0|
|비활성 출력 0V|320,000|0|0|
|활성 DC 보상|306,234|64|13,702|
|두 출력 DC 뒤 0V|639,827|173|0|

주 HOLD의 최대 중앙구간 절대 오차는 **20.283694mV**입니다. 종료 뒤 두 출력의 0V 복귀는 모든 조건에서 통과했습니다. DC 미판정 13,702건은 짧은 보상 구간에 native 표본이 3개 미만이어서 평가하지 못한 경우입니다. PASS에 포함하지 않았습니다.

각 capture의 시작 전 baseline offset 하나만 빼고, 중앙구간 median 오차의 절대값이 15mV를 초과하면 FAIL입니다. 모든 순간 샘플의 ±15mV 보장을 뜻하지 않습니다. RC 선보상 출력은 요청 전압에 적분 기울기가 더해지므로 각 점의 요청 상승시간을 포함한 RC 기대값과 비교했습니다. 요청값과 실제 양자화된 값은 별도로 저장하고 판정 기준을 실제값으로 바꾸지 않았습니다.

## 고해상도 대표 파형

RC 20µs/DC 고정 10µs에서 10ns·500ns·1µs 및 ±400mV, 두 DAC/두 방향 24조건을 별도 1점 GUI 설정으로 컴파일하고 취득했습니다. 각 채널의 원래 시간축을 보존했습니다. HOLD/모델 잔차와 RAMP의 10–90% 폭을 기록했지만, 아날로그 경로 보정이나 정밀 시간 허용오차 판정은 하지 않았습니다. 첫 edge에 대한 전체 시간 정렬은 케이블/시작 지연을 제거하므로 절대 출력 지연 측정도 아닙니다.

이 대표 파형은 전체 10,000점 명령열과 동일한 프로그램의 취득이 아닙니다. 단일점 반올림은 register-add sweep 끝값과 다를 수 있습니다. 전체 sweep의 500ns 기록으로 모든 10ns RAMP 모양을 검증했다고 주장하지 않습니다.

대표 파형의 상승·하강 RAMP 총 48구간 중 중앙값 잔차가 15mV를 넘는 구간은 13개입니다. 그러나 native 표본 360,800개 중 108,471개가 15mV를 초과하고, RAMP 구간 내 최대 순간 잔차는 399.051mV입니다. 구간 median과 순간 파형 오차를 구분해야 합니다.

이 399.051mV는 기존 시간 정렬을 유지한 모델 잔차이며, 순수한 진폭 결함의 크기로 해석할 수 없습니다. DAC5의 +400mV·10ns 하강 대표 파형을 독립 검토한 결과 실제 빠른 하강 구간이 존재했고, 10–90% 폭 후보는 7.078~7.378ns였습니다. 첫 1µs 상승 파형의 200mV crossing 후보 범위가 54.335ns여서, 기존 기준의 약 41ns 하강 시각 차이는 그 정렬 불확실성 안에 있습니다. 명령의 7클록 시작 지연·3클록 RAMP·다음 SET 간격은 서로 일치했습니다. 이 자료만으로 RTL 지연 결함을 확정하지 않으며, 기존 잔차와 미판정은 그대로 보존합니다. [명령·원시 파형 독립 검토](highres_timing_review_01/diagnostic_summary.json)

DAC4의 −400mV·10ns 상승 RAMP 직후 100ns를 별도 검토했습니다. 종료 뒤 10.138ns의 실제 offset 보정 전압은 −482.008mV, 모델 대비 잔차는 **−81.758mV**였습니다. 해당 1,000표본 중 334개가 15mV를 초과합니다. 이 과도응답은 RAMP 내부 및 HOLD 중앙구간 통계 밖에 있으므로 별도로 기록합니다. 정착시간/정밀 시간 PASS는 판정하지 않았습니다. [과도응답 원시 재검토](review_highres_rising_dac4_duration10ns_negative_01/results.json) · [파형](review_highres_rising_dac4_duration10ns_negative_01/post_ramp_100ns.png)

|방향|DAC|요청 길이(ns)|전압(mV)|native 간격(ns)|분석|
|---|---:|---:|---:|---:|---|
|rising|4|10|-400|0.1|[결과](analysis_highres_rising_dac4_duration10ns_negative_01/results.json)|
|rising|4|10|400|0.1|[결과](analysis_highres_rising_dac4_duration10ns_positive_01/results.json)|
|rising|4|500|-400|0.1|[결과](analysis_highres_rising_dac4_duration500ns_negative_01/results.json)|
|rising|4|500|400|0.1|[결과](analysis_highres_rising_dac4_duration500ns_positive_01/results.json)|
|rising|4|1000|-400|0.1|[결과](analysis_highres_rising_dac4_duration1000ns_negative_01/results.json)|
|rising|4|1000|400|0.1|[결과](analysis_highres_rising_dac4_duration1000ns_positive_01/results.json)|
|rising|5|10|-400|0.1|[결과](analysis_highres_rising_dac5_duration10ns_negative_01/results.json)|
|rising|5|10|400|0.1|[결과](analysis_highres_rising_dac5_duration10ns_positive_01/results.json)|
|rising|5|500|-400|0.1|[결과](analysis_highres_rising_dac5_duration500ns_negative_01/results.json)|
|rising|5|500|400|0.1|[결과](analysis_highres_rising_dac5_duration500ns_positive_01/results.json)|
|rising|5|1000|-400|0.1|[결과](analysis_highres_rising_dac5_duration1000ns_negative_01/results.json)|
|rising|5|1000|400|0.1|[결과](analysis_highres_rising_dac5_duration1000ns_positive_01/results.json)|
|falling|4|10|-400|0.1|[결과](analysis_highres_falling_dac4_duration10ns_negative_01/results.json)|
|falling|4|10|400|0.1|[결과](analysis_highres_falling_dac4_duration10ns_positive_01/results.json)|
|falling|4|500|-400|0.1|[결과](analysis_highres_falling_dac4_duration500ns_negative_01/results.json)|
|falling|4|500|400|0.1|[결과](analysis_highres_falling_dac4_duration500ns_positive_01/results.json)|
|falling|4|1000|-400|0.1|[결과](analysis_highres_falling_dac4_duration1000ns_negative_01/results.json)|
|falling|4|1000|400|0.1|[결과](analysis_highres_falling_dac4_duration1000ns_positive_01/results.json)|
|falling|5|10|-400|0.1|[결과](analysis_highres_falling_dac5_duration10ns_negative_01/results.json)|
|falling|5|10|400|0.1|[결과](analysis_highres_falling_dac5_duration10ns_positive_01/results.json)|
|falling|5|500|-400|0.1|[결과](analysis_highres_falling_dac5_duration500ns_negative_01/results.json)|
|falling|5|500|400|0.1|[결과](analysis_highres_falling_dac5_duration500ns_positive_01/results.json)|
|falling|5|1000|-400|0.1|[결과](analysis_highres_falling_dac5_duration1000ns_negative_01/results.json)|
|falling|5|1000|400|0.1|[결과](analysis_highres_falling_dac5_duration1000ns_positive_01/results.json)|

## 증거 및 한계

전체 및 대표 raw IEEE block 총 227,201,232bytes를 무손실 gzip 47,451,228bytes로 저장했습니다. 요청한 파형 PNG, 각 point CSV, PMEM/DMEM, 원시자료, 설정백업 및 hash를 보존했습니다.
생산 Python 170파일 해시는 변경되지 않았습니다. 각 실행의 카운터·출력 정리·오실로스코프 복원을 확인했습니다. 기존 v5 보드를 사용했으며 새 합성·펌웨어 교체·서버 재시작·사용자 GUI 종료·사용자 JSON 수정은 하지 않았습니다.
실제 GUI 입력 → 생산 컴파일러 → 현재 보드의 유한 프로그램 → 오실로스코프 경로입니다. RunWorker의 ADC/FIR/DDR/QCoDeS 취득이나 새 RTL 시뮬레이션을 이 검사로 대체하지 않습니다. 외부 RC 회로·정밀 아날로그 면적·모든 shot 내부 overflow는 검증하지 않았습니다.
전체 sweep 준비 1조건은 모든 검사/manifest 저장 뒤 SIP 종료 접근 위반이 발생했습니다. 원본을 보존하고 종료 방식만 수정한 새 준비가 exit0이며 ASM/PMEM/DMEM·압축 해제 기대값·모델·GUI 입력이 동일함을 별도 감사했습니다. 기존 25개 성공 검사는 재사용하고 미실행 조건만 재개했습니다.
초기 고해상도 준비의 Qt 접근 위반은 컴파일/장비 출력 전 발생했습니다. 원인 미확정 상태로 원본 폴더·로그·helper를 보존하고 고정 duration 입력을 실제 GUI에서 읽는 검토된 별도 시도로 준비했습니다. 해당 실패와 물리 측정 FAIL은 분리했습니다.

- [전체100×100 상세판정](fullframe_summary_01/REPORT.md)
- [전체집계 및 대표결과](results.json)
- [실물실행 상태](physical_campaign_status.json)
- [고해상도 실행상태](highres_campaign_status.json)
- [첫DC/zero실패 raw독립검토](first_capture_failure_review.json)
- 각analysis폴더에 full_record.png / representative_waveforms.png / primary_error_maps.png, highres폴더에 RAMP진단그림이 있습니다.
