# GUI 전체 firmware 업데이트·버전 선택·단일 Update

사용자 후속 요청을 기존 `awg_tuning_v4` GUI에 구현했습니다. **실제 보드 파일 업데이트는 실행하지 않았습니다.**

## 동작

- 작업 버튼은 **Update** 하나입니다. 검사 → 전체 업로드 → 무결성 검사 → 백업 → 교체를 순서대로 처리합니다. 전송 진행률은 실제 전송 바이트로 계산하며 다른 단계는 단계 이름과 진행 애니메이션을 표시합니다.
- Update를 누르면 **서버 종료**, **실험·출력 정지(다른 클라이언트/Notebook 포함)** 확인창이 열립니다. 두 체크박스 모두 선택해야 Confirmed — Update를 누를 수 있습니다. 기본값은 Cancel이고 매번 다시 확인합니다.
- PC/보드에서 `QSTL_QICK` 또는 그 안의 `qick` 폴더를 선택할 수 있습니다. PC의 `qick/firmware`에서 BIT/HWH 쌍을 검색하며 현재 **19개** 버전이 표시됩니다.
- 버전 선택은 보드 `pyro_cli.py`의 `start_server(bitfile=...)`에 들어갈 파일을 결정합니다. 선택 버전뿐 아니라 **firmware 전체 폴더**를 업데이트하며 기존 보드 폴더 전체는 백업합니다.
- `qick_lib/qick` 코드 폴더만 교체하여 `.egg-info`, `.egg-link`, `.pth`를 유지합니다. 보드 launcher의 BIT 경로 외 설정도 유지합니다.
- 파일 업데이트는 SSH와 보드 표준 라이브러리만 사용합니다. 보드 root 계정의 Pyro4 유무를 업데이트 선행 조건으로 사용하지 않습니다. 서버·FPGA는 자동 실행하지 않습니다.

## 검증

| 항목 | 결과 |
| --- | --- |
| 전용 로컬 테스트 | **55 PASS**, 실패/오류 0 |
| 전체 폴더 교체·복구 | 실제 임시 파일로 전체 firmware/라이브러리 백업·교체·복원, rename 오류 원상복구 확인 |
| 설치 정보 | metadata/link/pth 보존 및 실제 Python import·버전 조회 확인 |
| 선택 경로 | 선택한 다른 버전으로 launcher BIT 경로 변경, 기존 옵션 보존, 선택 변경·파일 변조 거부 |
| Pyro4 없는 파일 작업 | Pyro4/QICK runtime import를 금지한 상태에서 inspect/prepare/apply/rollback 통과 |
| GUI | 단일 버튼, 실제 Qt 확인창 두 체크/확인/취소, 작업 중 중복 방지, 바이트 진행률, 성공/실패 신호 확인 |
| 실제 로컬 패키지 | 19개 버전 발견, manifest가 있는 5개 및 없는 1개 검사 통과. 각 검토의 전송 목록은 2,033파일 / 767,907,912 bytes |
| 보드 읽기 전용 | `/home/QSTL_QICK/qick` 선택의 저장소 정규화·설치 정보·폴더 목록 조회 성공. launcher SHA256 전후 동일 |
| 기존 회귀·펌웨어 | 보호 59파일과 완료된 회귀 결과 해시 유지. 과거 메뉴 추가 외 174파일 스냅샷의 추가 변경 없음 |

선택 버전에 manifest가 있으면 기록된 timing과 BIT/HWH/XSA 해시 및 XSA 내부 쌍을 확인합니다.
manifest 없는 버전은 파일 쌍·HWH XML/timestamp·전송 무결성 검사입니다. 모든 버전의 기능 호환성이나
timing을 새로 검증했다는 뜻은 아닙니다. 전체 폴더 전송에서는 Python 캐시를 제외하며 빈 디렉토리는 전송하지 않습니다.

일반적인 QICK 서버 launcher 프로세스가 실행 중이면 업데이트를 거부합니다. 사용자 정의 서버 스크립트나
Notebook의 실행 내용까지 자동 판별하지 못하므로 확인창의 두 정지 조건은 사용자가 확인해야 합니다.

최초 offscreen QMessageBox 화면 검사는 접근 위반이 발생했고 최소 예제에서도 재현했습니다.
새 확인창을 일반 QDialog로 구현한 뒤 **실제 확인/취소 테스트와 최종 화면 캡처가 exit 0**으로 종료했습니다.
최초 실패 로그를 보존했습니다. 첫 테스트 실행의 pytest 경로 누락은 기존 검증 의존성 경로를 설정하여 해결했으며
환경에 새 패키지를 설치하지 않았습니다.

## 증거

- [55개 테스트 결과](tests_final.xml), [로그](tests_final.log)
- [결과·변경 범위·소스 해시](results.json), [검증 소스](validated_sources/QICK_UPDATE.md)
- [19개 버전 및 6개 실제 패키지 검토](local_review.json)
- [보드 읽기 전용 확인](board_readonly.json)
- [업데이트 화면](update_dialog.png), [펌웨어 목록](firmware_versions.png), [서버/실험 확인창](server_confirmation.png)

실제 보드의 대용량 업로드·교체·재설치·서버 재시작·FPGA 로드는 미수행입니다.
시험용 보드에서 강제 중단/전원 손실을 포함한 실제 업데이트·복구 검증은 별도로 남아 있습니다.
기존 실행 중 GUI는 종료하지 않았으므로 사용자가 GUI를 다시 시작하면 새 화면이 반영됩니다.
commit/push/새 브랜치/합성·RTL 재실행은 하지 않았습니다.
