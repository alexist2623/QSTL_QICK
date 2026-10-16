# 기존 3×3 실측의 고정 오프셋 제거 후 5% 재판정

사용자가 새로 지정한 **절대 상대오차 < 5%** 기준으로 기존 run_03을 재분석했습니다. 비영점 plateau **12/12 PASS**, 최대 절대오차 **2.92886144%**입니다. 새 100×100 실측 결과가 아닙니다.

채널마다 0 mV plateau 세 구간 중앙 50%의 총 187,500개 sample에서 얻은 median 하나를 모든 점에 동일하게 뺐습니다. DAC4/CH1 offset은 −27.61508352 mV, DAC5/CH2는 −14.22596096 mV입니다. 이전 2% 분석과 offset·median·window·요청전압 분모가 같고 판정 한계만 사용자 요청대로 바뀌었습니다. Gain 보정이나 점별 offset은 적용하지 않았습니다.

| 출력 | 요청 전압 | 보정 후 | 부호 있는 상대오차 | <5% |
|---|---:|---:|---:|---|
|DAC4/CH1|200 mV|200.836838 mV|+0.418419%|PASS (각 3점)|
|DAC4/CH1|400 mV|394.979116 mV|-1.255221%|PASS (각 3점)|
|DAC5/CH2|200 mV|200.836838 mV|+0.418419%|PASS (각 3점)|
|DAC5/CH2|400 mV|388.284554 mV|-2.928861%|PASS (각 3점)|

0 mV 여섯 plateau는 offset 계산에 사용하며 분모가 0이므로 백분율 오차·PASS 판정은 null입니다. 5%와 같은 값은 FAIL이며 반올림한 표시값으로 판정하지 않았습니다.

원시 payload를 `<u2`와 저장된 preamble로 다시 해독해 전체 NPZ time/voltage/code와 일치함을 확인했습니다. 18개 plateau window도 원시 배열에서 다시 계산했고 이전 median 값과 일치합니다. 기존 capture·보정 전 보고서·2% 결과/그림/소스의 모든 보존 해시를 실행 전후 검증했습니다. **기존 2% 기준의 9 PASS/3 FAIL 결과는 변경하지 않았습니다.**

이번 acquisition의 수직 raw code 간격은 약 6.695 mV이며 이 판정은 사용자 정의 공학 기준입니다. 별도의 교정 정확도·불확도 인증으로 해석하지 않습니다. 원본을 새로 측정하거나 삭제하지 않았습니다.

- [새 판정 수치](results.json)
- [18개 plateau CSV](corrected_measurements.csv)
- [보정 파형과 ±5% 오차 그림](offset_corrected.png)
- [이전 2% 보고서](../offset_2pct_review/REPORT.md)
- [보존 입력 SHA256](input_hashes.json)
