# 물리 100×100 전압 sweep 분석

10,000점·20,000 plateau의 중앙 HOLD 구간을 분석했습니다. 시간/기록 무결성: **PASS**. 비영점 19,800개 중 **PASS 17061, FAIL 2739, 미완료 0**입니다.
점 단위 집계(비영점 축 중 하나라도 실패하면 FAIL): {'PASS': 7460, 'FAIL': 2539, 'N/A': 1, 'INCOMPLETE': 0}. (0,0)점과 모든 0mV 축의 백분율 판정은 N/A입니다. 전체 결과: **PASS 아님**.

## 판정 방법

채널별 100개 0mV HOLD의 중앙 5µs sample을 합친 median 하나를 모든 점에서 동일하게 뺐습니다. 요청 전압(400×index/99)을 분모로 절대 상대오차가 엄격히 5% 미만일 때만 PASS입니다. gain fit·점별 offset·점별 시간 이동은 하지 않았습니다. 평균값은 참고 진단 열로만 보존했습니다.
요청 endpoint는400mV, 실제 compiler의164-code 일정 증가에 따른 endpoint는397.120034180mV입니다. 이 차이는 숨기지 않았고 판정 분모를 실제 code 전압으로 바꾸지 않았습니다.

|채널|고정 offset(mV)|비영점 PASS|FAIL|raw 수직 간격(mV)|
|---|---:|---:|---:|---:|
|DAC4/CH1|-24.267717120|8487|1413|3.347279360|
|DAC5/CH2|-14.225879040|8574|1326|3.347279360|

## 시간 정렬 및 완전성

CH2 raw300mV threshold crossing의 첫 row 끝을point99로 연결했습니다. 1µs 선형 RAMP의 threshold 분율을 첫 anchor 근처 baseline/high에서 구해 단일 시간 offset -0.000980662627843s를 적용했습니다. 이 전압 두 값은 시간 정렬에만 사용했습니다.
row 끝99,199,…9999에 해당하는 high-threshold burst 100개를 검사했고 최대 residual은0.204951µs입니다. 사전 기준은 절대 residual<2µs, dt≤500ns, ROI≥10samples, 순서상 서로 겹치지 않는20000개 window입니다. 실제 두채널 native time축은 각각 유지했습니다.
정렬 문제가 있으면 진폭 수치가 기준 내여도 전체 PASS가 될 수 없습니다. 세부 문제: []

## 제한과 원시자료

첫 비영점 요청은4.040404mV이고5%허용폭은0.202020mV입니다. 이 acquisition의 수직 표본 간격·잡음보다 작을 수 있어 median이 같은code에 묶이거나 낮은값의 상대오차가 커질 수 있습니다. 실패는 그대로 보존하며 이 결과만으로 DAC gain/offset 또는 scope 교정 중 원인을 단정하지 않습니다. 별도의 교정 불확도 인증이나 정밀 timing/skew 검증이 아닙니다.
끝 zero는 별도 구간의 baseline residual을 results.json에 저장했습니다. 0mV에 상대% PASS를 부여하지 않았습니다.
- [전체20000개 plateau CSV](all_20000_plateaus.csv)
- [전체10000점 판정](all_10000_point_verdicts.csv)
- [전체 결과](results.json)
- [시간 정렬](alignment.json)
- [고정 offset](offsets.json)
- [전체 capture min/max 그림](full_record_overview.png)
- [첫 row native-sample 확대](first_row_zoom.png)
- [마지막 row native-sample 확대](last_row_zoom.png)
- [전점 오차/실패 지도](error_and_failure_maps.png)
- 원본: ../run_01/scope_capture의 채널별 gzip IEEE block와preamble; 모든sample을 무손실 유지하며 여기서는중복저장하지않았습니다.
