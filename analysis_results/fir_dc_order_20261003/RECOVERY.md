# 전원 중단 후 확인 (2026-10-04)

- QSTL_QICK 및 PulseGenerator-qick의 `git fsck --full` 통과. Dangling 객체는 있었으나 손상/누락 오류는 없었다. QICK은 `--no-dangling`으로 재검사하여 종료 코드 0도 확인했다.
- 실제 RTL 8종의 소스·PMEM·DMEM SHA-256은 각각 저장된 prepared fingerprint와 일치한다. 현재 GUI 코드로 생성한 PMEM/DMEM도 모든 실행에서 일치했다.
- 변경한 Python 파일의 구문 검사, 결과 JSON 파싱, PNG 이미지 무결성 검사를 통과했다. 보고서의 실제 DDR 샘플 태그 및 sweep 지점별 보상 시각 재분석도 통과했다.
- RTL 검증은 8종 모두 정상 종료했으며 결과 파일도 완전하다. 대형 시뮬레이션을 중복 실행할 필요는 없었다.
- 소프트웨어 assertion 246개는 통과했다. 다만 Qt를 포함한 일부 테스트 프로세스는 assertion 완료 이후 native access violation(`0xC0000005`)으로 종료했다. 분리 실행의 실제 종료 코드는 `software_modules/exit_codes.json`에 보존했다.
- 이전 GUI HEAD `610b9cc`의 MainWindow를 별도 모듈로 읽어 설정 저장·복원·close를 실행해 같은 오류를 재현했다(`BASELINE_LOAD_CLOSED` 이후 종료 코드 -1073741819). 단순 생성·close는 종료 코드 0이었다. 이 비교에는 현재의 의존 라이브러리를 사용했다.
- 새로운 RF Readout/timing dialog만 포함한 두 GUI 검사는 정상 종료였다. 기존 MainWindow 설정 복원 후 offscreen Qt 정리 문제는 TODO 4번으로 분리했고, 실제 사용자 환경에서의 재현 여부는 확인하지 않았다.

이번 작업에서 파일 손상은 발견되지 않았다. 위의 기존 Qt 종료 문제까지 해결됐다는 의미는 아니다.
