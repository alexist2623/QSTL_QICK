# QICK 라이브러리·펌웨어 업데이트 GUI

메뉴: **Setup → QICK Library and Firmware Update...**

2026-10-14 전체 v4 회귀 완료 **후** 추가한 기능입니다. 사용자 지시에 따라
GUI·신규 테스트·업데이터·SSH 동작·패키지 설치·실제 보드 교체는 실행하지 않았습니다.
코드만 작성하고 정적으로 검토했습니다. 기존 회귀 PASS가 이 기능의 동작 검증을 뜻하지 않습니다.

## 위치 선택

- **Local QSTL_QICK / Browse…**: PC의 저장소 폴더를 고릅니다. 라이브러리 원본은 그 아래 `qick/qick_lib`입니다.
- **Firmware build manifest / Browse…**: 성공한 v4 빌드의 `build_manifest.json`을 고릅니다. 같은 폴더의 BIT/HWH/XSA 해시와 XSA 내부 BIT/HWH 일치를 확인합니다. 현재 구현은 이 v4 manifest 형식을 지원합니다.
- **Board repository / Browse board…**: 입력한 SSH 계정으로 보드의 실제 폴더 목록을 읽어 선택합니다. 기본값은 확인된 `/home/QSTL_QICK`이며 라이브러리 대상은 그 아래 `qick/qick_lib`입니다.
- **BIT path within repository / Browse board…**: 보드 저장소의 `qick/firmware` 아래 대상 폴더를 고릅니다. BIT 파일명은 텍스트에서 변경할 수 있고 HWH는 같은 위치·이름을 사용합니다. 새 하위 경로도 직접 입력할 수 있습니다.
- PC 탐색기는 로컬 경로, **Browse board…**는 SSH 보드 경로입니다. 경로를 선택하거나 조회할 때 폴더를 만들거나 파일을 변경하지 않습니다. 화면에 라이브러리/BIT/HWH **원본 → 대상**을 표시합니다.

보드 저장소는 실제 디렉토리인 `/home/...` 또는 `/root/...`만 지원합니다. 대상 경로의
심볼릭 링크와 저장소 밖 firmware 경로는 거부합니다. 기본 Board Python은 확인된
`/usr/local/share/pynq-venv/bin/python3`입니다. 다른 위치는 직접 입력할 수 있습니다.

## 사용 흐름 (이번 작업에서 실행하지 않음)

1. **Inspect board**로 보드 Python, 실제 QICK import 경로, 여유 공간, 실행 중인 펌웨어 정보와 이전 백업을 조회합니다. 이때 파형을 출력하거나 FPGA를 다운로드하지 않습니다.
2. **Review local package**로 성공 manifest/파일 해시/같은 XSA의 BIT·HWH 및 GUI Python 환경의 QICK 소스 파일 일치를 확인합니다.
3. **Upload and verify staging**은 별도 임시 거래 폴더에 `qick_lib`와 BIT/HWH를 전송하고 해시를 대조합니다. 기존 실행 파일은 아직 바꾸지 않습니다. XSA는 PC에서만 확인하고 전송하지 않습니다.
4. 다른 클라이언트를 포함해 모든 실험·출력을 중지하고 QICK 서버를 수동으로 종료합니다. 두 확인란을 체크한 뒤 **Apply prepared update…**를 누릅니다. 대상과 패키지를 다시 확인하며, 확인창의 기본 선택은 No입니다. 서버가 실행 중이거나 상태를 확인할 수 없으면 교체를 거부합니다. Pyro nameserver는 계속 실행돼 있어야 합니다.
5. 이전 라이브러리/BIT/HWH를 보존한 뒤 준비된 파일을 교체합니다. 이 시점의 상태는 **files updated / restart required**이며 FPGA 적용 완료가 아닙니다. QICK 서버를 선택한 BIT 경로로 수동 재시작합니다. Notebook이면 커널 프로세스도 재시작해야 합니다. 기존 서버 실행 명령이나 Notebook 셀은 자동 수정하지 않습니다.
6. **Verify running firmware**는 설치 파일 해시, 새 서버 프로세스, Python 실행 파일, QICK 버전, HWH timestamp, v4 AWG/RF 합산 연결을 확인합니다. 이는 설정·파일 식별 검사이며 아날로그 출력/실험 시험은 아닙니다. 패키지 의존성과 서버의 Python 경로는 사용 환경에서도 확인해야 합니다.
7. 파일 교체·복원 또는 교체 중 오류가 발생하면 현재 GUI의 장치 조작을 막습니다. File의 저장/종료와 열린 유지보수 창은 사용할 수 있습니다. 필요한 설정을 저장하고 **GUI를 재시작**한 뒤 QICK을 다시 식별해야 캐시된 설정/드라이버를 재사용하지 않습니다.

이전 거래를 선택해 **Restore selected backup…**으로 복원할 수 있습니다. 복원도 출력과
QICK 서버가 정지된 상태에서만 수행하며, 현재 파일 해시가 교체 후와 달라졌으면 거부합니다.
원래 파일과 밀려난 파일은 모두 보존하고, 복원 후에도 수동 재시작이 필요합니다.

보드에는 `.qick_gui_updates/<transaction-id>/` 아래 전송물, manifest, journal, 백업이
남습니다. 중단된 전송/실패 증거를 자동 삭제하지 않습니다. 프로세스 중단·전원 손실 등으로
거래나 `.qick_gui_update.lock`이 남으면 파일·journal을 검토하고 수동 복구해야 합니다.
도중 예외에서 정상 복원이 가능하면 원래 해시를 확인하고 복구 상태를 기록합니다.

## 연결과 의존성

- 창을 여는 것만으로 연결·전송·설치·재시작은 일어나지 않습니다. SSH는 Browse/Inspect/Upload 등 명시적 동작에서만 연결합니다.
- SSH 비밀번호는 창의 메모리에서만 사용하며 설정 JSON이나 로그에 저장하지 않습니다. 기존 SSH 키 인증도 지원합니다.
- SSH host key는 기존 `known_hosts`로 확인합니다. 등록되지 않았거나 바뀐 키는 거부하므로 정상 SSH 절차로 보드 키를 확인·등록해야 합니다.
- PC의 선택 의존성은 `requirements-updater.txt`의 Paramiko입니다. 자동 설치하지 않습니다. 보드 Python에는 기존 QICK 런타임의 Pyro4와 psutil이 필요합니다.
- 라이브러리는 현재 보드 Python이 선택한 저장소의 `qick/qick_lib/qick`를 import하는 경우만 교체합니다. pip 설치나 의존성 업데이트는 하지 않습니다.
- 생산 설정 JSON, 실험 데이터, Git 브랜치, Notebook, 서버 시작 명령은 업데이트 대상이 아닙니다.

## 실행 검증이 남은 항목

- 로컬 manifest/해시/서로 다른 BIT·HWH/변경된 소스 거부, 실제 GUI 환경의 QICK 탐색.
- SSH 인증·host key·보드 경로 탐색·심볼릭 링크·권한 오류·시간 초과·전송 중단.
- 임시 폴더에서 교체/복원, 부분 rename 오류, 대상 변경, 해시 오류, 동시 실행 잠금, 중단 후 복구.
- GUI 상태 전이, 선택 경로 변경, 백업 선택, 확인창, 작업 중 닫기, 비밀번호 보존 여부.
- 시험용 보드에서 서버 정지 판별, 실제 드라이버 import, 수동 재시작, 잘못된 firmware 식별, 교체 후 GUI 재시작.

**이번에는 위 검증이나 실제 업데이트를 실행하지 않았습니다.**
