# RF editor Nyquist duplicate removal

- RF Output 편집기의 중복 Nyquist zone 입력 행을 제거했습니다. Nyquist zone은 Front Panel에서 선택합니다.
- 숨겨진 내부 값은 유지하므로 Front Panel의 output_nqz가 기존 RF 설정 저장/불러오기, calibration 조회, 프로그램 생성으로 전달됩니다.
- Front Panel의 즉시 Update가 NQZ를 직접 하드웨어에 쓴다고 주장하지 않습니다. 기존 실제 적용은 프로그램의 declare_gen(..., nqz=...) 경로입니다.
- 관련 48 검사 PASS / exit0 / Qt callback 오류 없음. Front Panel NQZ=2 적용, 편집기에서 숨김, 설정 roundtrip 및 hardware-update 경계로 전달되는 spec을 mock으로 확인했습니다.
- 기존 9 시스템 조건 재컴파일 PMEM/DMEM은 바이트 동일합니다. 기존 composite 7조건 RTL의 실행 증거는 보존했으며, 이번 표시 수정 때문에 재실행하지 않았습니다.
- 생산 코드 변경은 RfPulsePortPanel.__init__의 표시/위젯 소유권/안내문에 한정됩니다. 그 생성자를 제외한 전체 모듈 AST가 이전과 동일함을 확인했습니다.

## Tau 설명

현재 preset tau는 rf_template_tau, Custom delay는 rf_delay host 축입니다. 각 좌표에서 구체적인 RF 이벤트와 AWG SET 길이를 계산하여 프로그램을 다시 실행합니다. 실제 pulse 간격은 FPGA가 생성하지만 점 간에는 host 처리 시간이 있습니다.

이는 하드웨어의 필수 제약이 아니라 앞선 구현 선택입니다. 현재 pulse event는 named delay를 숫자 offset으로 합치고 하드웨어 시간 의존성으로 전달하지 않습니다. 기존 RF duration/tProcessor loop 기반에 delay 의존성·후속 RF timestamp·SET/획득 종료·clock 양자화 검사를 연결해야 hardware tau sweep이 됩니다. 고정 N의 UDD도 tau에 선형이므로 UDD라는 이유로 software sweep이 필수인 것은 아닙니다. 이번 수정에서 tau 실행 방식은 변경하지 않았습니다.

RTL/XDC/펌웨어, 실행 중인 GUI/서버 및 보드는 변경하지 않았습니다. 별도 v5 빌드 결과 확인 일정도 그대로입니다.

[검사 결과](tests.xml) · [소스/증거 해시](result.json) · [기존 입력 비교](../compiler_equivalence.json)
