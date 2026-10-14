# 현재 v4 전체 기본 회귀 재검증

**전체 완료: PASS**

- 현재 v4 기본 소프트웨어 72모듈 / 1194개 PASS, 추가 연동·증거 검사 29개 PASS.
- 기본 RTL 6묶음과 합산 단위 RTL 1,114,160 샘플을 현재 소스로 새로 실행해 PASS.
- 초기 3개 실패는 원본 로그에 보존: RC/phase-storage의 Qt 종료 접근 위반 2건, trigger-panel의 desktop PYNQ 초기화 누락 1건.
- 동일 원본 테스트/생산 소스를 유지하고 명시적인 Qt 종료 또는 기존 qick.sim 초기화를 적용한 재실행은 모두 exit 0.
- 32/64비트 비교, 새 합성, 펌웨어 교체는 수행하지 않았습니다.
- 생산 소스·사용자 설정·펌웨어 해시 변경: 0개.

| 시스템 조건 | 상태 |
|---|---|
| hold_fixed_time | passed |
| hold_fixed_voltage_offset | passed |
| rf_duration_extend | passed |
| rf_duration_fixed | passed |
| rc_only | passed |
| reversed_axes | passed |
| stability | passed |
| exact10us_hold1 | passed |
| exact10us_hold2 | passed |

Stability는 현재 GUI가 사용하는 public Stability builder → 실제 RTL 시험입니다. RF/DDR가 없는 기존 기본 조건을 유지하며 v4 합산단을 포함합니다. 다른 8조건은 실제 MainWindow 입력/Run Experiment 컴파일과 PMEM/DMEM 일치를 확인합니다.

48비트 연속 RC 200회: PASS.

현재 RTL 변경 후 전체 기본 검증 재실행 원칙은 [통합 체크리스트](../VALIDATION_CHECKLIST.md)에 있습니다.
원본 실행 상태는 [status.json](status.json), 결과 대조는 [results.json](results.json), 기본 회귀 최초 실행은 [regular_initial_status.json](regular_initial_status.json)입니다.

보드 아날로그 측정과 ADC/FIR 산술 응답은 이 검증 범위가 아닙니다. AWG IIR 뒤 DDS 합산 면적·clipping은 기존 DC 면적 보상에 포함되지 않습니다.
