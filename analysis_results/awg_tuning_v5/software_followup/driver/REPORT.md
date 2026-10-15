# v5 드라이버 연동 검증

- 총 **71검사 PASS**, 실패/오류/skip 0, 프로세스 exit 0.
- 실제 retained v3/v4와 최종 candidate v5 HWH를 `QickMetadata` 및 생산 `AbsSignalGen.configure_connections`로 탐색했다. MMIO 생성, 보드 연결, 업로드는 하지 않았다.
- v5의 7개 `axis_output_sum_v2`: AWG delay 13 + pipeline 2. 세 RF/AWG 쌍은 AWG 31 / RF 31클록이며, 네 AWG bypass도 31클록이다.
- v4의 7개 v1: AWG 18 / RF 31클록 유지. v3 AWG 16클록, 별도 RF 및 RF4/Square 연결 유지.
- 반복 연결과 v1↔v2 전환에서 지연이 누적되지 않으며, 합산단 제거 시 원래 latency 필드 상태로 돌아간다.
- HWH input identity, v2 13클록 parameter, N_PTS 16, pipeline 2, bypass 0/1 검사를 유지한다. 잘못된/누락된 parameter와 없는 RF/AWG input을 거부한다.
- DAC current는 같은 버전과 HWH 연결을 가진 두 입력만 하나의 물리 DAC로 인정한다. 실제 HWH 연결 + fake RFDC로 단일 DAC 쓰기 및 불일치 버전 read-only 동작을 검사했다.
- `post_output_latency_cycles=2`는 공통 합산 pipeline이고 `output_sum_awg_delay_cycles=13`은 v2의 AWG 전용 delay이다. `output_sum_native_latency_cycles`는 반복 설정/원상복귀를 위한 원래 설정값이다.

생산 변경: `qick/output_sum.py`, `qick/ip.py`, `qick/dac_current.py`.
새 회귀: `qick/test_output_sum.py`, `test_actual_hwh.py`.

**범위 제한:** 같은 tProcessor 포트에서 원하는 RF/AWG timestamp를 함께 실행할 수 있는지는 별도의 GUI→실제 RTL 검증 대상이다. 이 드라이버 결과만으로 동시 물리출력을 주장하지 않는다. 실물 아날로그 측정은 하지 않았다.

상세 실행 로그는 [tests.log](tests.log), JUnit은 [tests.xml](tests.xml), 소스/증거 SHA256 및 실제 HWH 경로/latency는 [result.json](result.json)에 보존했다.
