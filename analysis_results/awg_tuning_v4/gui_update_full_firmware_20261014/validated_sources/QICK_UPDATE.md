# QICK 라이브러리·펌웨어 업데이트 GUI

메뉴: **Setup → QICK Library and Firmware Update...**

현재 화면은 **Update 버튼 하나**, 펌웨어 버전 선택 목록, 진행바로 구성됩니다.
전체 v4 RTL 회귀 완료 후 추가한 유지보수 기능이며, 해당 회귀 결과와 이 기능의 검증은 별도로 기록합니다.
실제 보드 업로드·교체·pip 설치·서버 재시작·FPGA 다운로드는 이번 구현 검증에서 수행하지 않았습니다.

## 위치와 펌웨어 버전 선택

- **Local QSTL_QICK or qick / Browse…**: PC의 QSTL_QICK 저장소 또는 그 아래 `qick` 폴더를 선택합니다.
- **Board QSTL_QICK or qick / Browse board…**: SSH로 보드 폴더 목록을 열어 `/home/QSTL_QICK` 또는 `/home/QSTL_QICK/qick`을 선택합니다. 폴더 탐색은 읽기 전용입니다.
- **Firmware version**: 선택한 PC 경로의 `qick/firmware`에서 `.bit`와 같은 이름의 `.hwh`가 있는 항목을 자동 검색합니다. 현재 저장소에서는 19개가 표시됩니다. v4가 있으면 처음에는 v4를 선택합니다.
- 선택한 버전의 실제 파일명을 사용합니다. 예를 들어 `qstl_awg_v2`는 `projects/qstl_awg_v2/bitstream.bit`, `qick_tprocv1_216_standard/out/qick_216.bit`는 그 파일을 그대로 사용합니다.
- 선택은 **다음 서버 시작에 사용할 BIT 경로**를 정합니다. 전송 대상은 선택 버전만이 아니라 **firmware 전체 폴더**입니다. XSA, 다른 버전, RTL, 설정·검증 소스도 포함하며 Python 캐시(`__pycache__`, `.pyc`, `.pyo`)만 제외합니다. 빈 디렉토리는 따로 보존하지 않습니다.
- 보드 대상은 `/home` 또는 `/root` 아래의 실제 저장소이며 심볼릭 링크와 저장소 밖 경로는 거부합니다. 대상 경로는 화면에 표시합니다.

기본 Board Python은 확인된 `/usr/local/share/pynq-venv/bin/python3`입니다.
창을 열거나 로컬 펌웨어 버전을 고르는 것만으로 보드에 접속하거나 파일을 교체하지 않습니다.

## Update 사용 흐름

1. 접속 정보, PC/보드 저장소 위치, 사용할 펌웨어 버전을 고르고 **Update**를 누릅니다.
2. 확인창에서 **QICK 서버 종료**와 **실험·출력 정지(Notebook/다른 클라이언트 포함)**를 각각 체크합니다. 둘 다 체크해야 **Confirmed — Update**가 활성화됩니다. 기본 버튼은 Cancel이며 취소·창 닫기는 업데이트를 시작하지 않습니다. 매 Update 시 새로 확인합니다.
3. 로컬 라이브러리/firmware 파일과 설치 계약을 확인하고 SSH로 보드 경로·설치 정보·여유 공간을 확인합니다. 일반적인 QICK 서버 실행 프로세스가 남아 있으면 파일 교체를 거부합니다.
4. 전체 파일을 별도 staging 폴더에 업로드하고 SHA256을 대조합니다. 업로드 중에는 실제 전송 바이트 기준 비율을 표시하고, 검사·패키징·백업·교체 단계는 단계 문구와 움직이는 진행바로 표시합니다.
5. 보드의 이전 코드 폴더와 **firmware 전체 폴더**를 백업한 뒤 검증된 파일로 교체합니다. 서버나 FPGA를 실행하지 않습니다.
6. 완료 문구가 나오면 사용자가 QICK 서버를 시작하고 GUI를 재시작하여 다시 연결합니다. 완료는 **파일 업데이트 완료**이며 실제 FPGA 로드·아날로그 동작 확인을 의미하지 않습니다.

이전 Upload/Apply는 위 4/5 단계로 내부에 통합했습니다. 별도 작업 버튼은 없습니다.
백업은 `.qick_gui_updates/<transaction-id>/backup/`에 보존하며 로그에 거래 폴더를 표시합니다.
보드에만 있던 firmware 파일도 이전 전체 폴더 백업에 남습니다. 실제 대상 폴더는 PC 파일 구성이 됩니다.

정지 확인은 Pyro RPC에 의존하지 않습니다. `/proc`에서 `qick.pyro_cli`, `pyro_cli.py`,
`pyro_service.py`, 일반적인 `start_server(...)` 실행을 검사합니다. 이름이 다른 사용자 정의
스크립트/Notebook 커널까지 실행 내용으로 판별할 수는 없으므로 확인창에서 모든 클라이언트의
실험·출력을 정지했다고 확인해야 합니다. nameserver만 실행 중인 경우에는 파일 교체를 막지 않습니다.

## 설치 정보와 pyro_cli 경로

`qick_lib/qick` 코드 폴더만 교체하고 `qick_lib/qick.egg-info`, Python site-packages의
`qick.egg-link`/`.pth`, 라이브러리 루트의 다른 파일은 유지합니다. PC/보드의 패키지 버전,
Python 요구사항, 의존성, entry point가 다르면 파일 교체를 거부하고 별도 재설치를 안내합니다.
GUI는 `pip install -e .`를 실행하지 않습니다. 이 저장소에서 설치 기준은 `setup.py`가 있는 `qick` 폴더입니다.

기존 보드 `qick/qick_lib/qick/pyro_cli.py`의 `start_server(..., bitfile=...)` 문자열만
선택한 버전의 보드 절대경로로 바꿉니다. 기존 nameserver/port/iface/soc_class 등 다른 옵션,
주석과 줄바꿈은 유지합니다. 동적인 경로나 여러 start_server 호출은 추측하여 수정하지 않습니다.
다른 실행 스크립트/Notebook이 직접 BIT 경로를 지정한다면 그 코드는 수정하지 않습니다.

교체 전·후 코드/펌웨어/설치 정보 해시를 확인합니다. 교체 중 오류가 발생하면 원본을 복구하고,
복구가 불가능하면 기록을 보존하고 오류를 표시합니다. 파일 교체 또는 그 단계의 오류 이후에는
기존 GUI의 장치 조작을 막으므로 설정을 저장하고 GUI를 재시작해야 합니다.

백업 복원은 내부 API에 유지되어 있고 전용 임시 폴더 테스트로 확인했습니다. 간소화한 창에는
복원 버튼을 표시하지 않습니다. 중단된 거래나 잠금, 전원 손실 등은 기록을 먼저 검토해야 합니다.
이전 형식(format 1/2/3)의 staging은 새 전체 firmware 형식(format 4)으로 다시 준비해야 합니다.

## 검사 범위와 의존성

- SSH 파일 교체에는 **보드 Pyro4가 필요하지 않습니다**. 보드 helper는 표준 라이브러리로 파일·프로세스·설치 메타데이터를 검사하며 QICK을 import하여 실행하지 않습니다. 사용자별 Pyro4 설치나 서버 시작은 GUI가 수행하지 않습니다.
- PC에는 `requirements-updater.txt`의 Paramiko가 필요합니다. 현재 `qcodes2`에는 Paramiko 4.0.0이 설치되어 있습니다. SSH 비밀번호는 메모리에만 보관하며 저장하지 않습니다. 호스트 키는 기존 `known_hosts`로 확인합니다.
- PC GUI가 선택한 QICK 소스와 같은 라이브러리를 사용하는지 확인합니다. 보드 Python도 선택한 저장소의 라이브러리를 가리켜야 합니다.
- 선택 버전에 `build_manifest.json`이 있으면 timing closure 기록과 BIT/HWH/XSA 해시, XSA 내부 BIT/HWH를 확인합니다. v4는 합산 출력 연결 검증 기록도 필요합니다. 기존 v2/v3 및 이전 manifest 형식을 지원합니다.
- manifest가 없는 버전은 BIT/HWH 파일·HWH XML/timestamp와 전송 해시만 검사합니다. timing closure나 현재 드라이버와의 기능 호환성을 새로 검증했다는 뜻이 아닙니다. 선택한 버전 외의 firmware 파일은 전송 무결성을 확인합니다.
- 선택적인 서버 런타임 식별 API는 남아 있으나 단일 Update 흐름에는 포함하지 않습니다. 이 API는 PC의 Pyro4를 사용합니다.
- 사용자 실험 설정 JSON, 데이터, Notebook, Git 상태, 서버 실행 명령은 업데이트 대상이 아닙니다. 단, 선택한 `firmware` 폴더 내부 파일은 전체 폴더 교체 범위에 포함됩니다.

## 2026-10-14 검증 결과

새 전용 검사 **55 PASS**입니다. 실제 임시 파일 교체/복원과 editable 설치 메타데이터 보존,
전체 firmware 백업, rename 실패 복구, 변조 거부, 선택 버전의 런처 경로, Pyro4 없는 파일 작업,
서버 정지 조건, 실제 Qt 확인창의 두 체크/확인/취소, 단일 Update 비동기 흐름/진행률을 검증했습니다.
실제 저장소의 19개 버전 목록과 manifest 있는 5개/없는 1개 버전의 패키지 검사를 확인했습니다.
보드 root의 실제 SSH 읽기 전용 검사와 폴더 조회는 성공했으며 launcher 파일 해시는 유지됐습니다.

최초 QMessageBox 화면 검사는 현재 offscreen Qt 환경에서 접근 위반이 발생했습니다.
새 확인창은 일반 QDialog와 두 확인 체크박스로 구현하고 실제 표시·확인·취소 및 캡처를 exit 0으로 확인했습니다.
초기 실패 로그는 삭제하지 않았습니다.

증거: QSTL_QICK 저장소의
`analysis_results/awg_tuning_v4/gui_update_full_firmware_20261014/REPORT.md`, `results.json`,
`tests_final.xml`, `local_review.json`, `board_readonly.json`, `server_confirmation.png`.

실제 보드 대용량 전송·파일 교체·강제 중단/전원 손실·서버 재시작·FPGA 출력 검증은 수행하지 않았습니다.
