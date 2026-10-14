# QICK 라이브러리·펌웨어 업데이트 GUI

메뉴: **Setup → QICK Library and Firmware Update...**

2026-10-14 전체 v4 회귀 완료 **후** 추가한 기능입니다. 최초 구현은 정적 검토만 했으며,
이후 사용자 요청으로 `qcodes2`에 Paramiko 4.0.0을 설치하고 실제 보드의 GUI 폴더 탐색과
읽기 전용 설치 정보 확인, 임시 폴더의 교체·복원 27개 테스트를 수행했습니다.
실제 보드 업로드·파일 교체·pip 재설치·서버 재시작·FPGA 다운로드는 수행하지 않았습니다.
기존 RTL 회귀와 이번 유지보수 기능의 검증 기록은 구분하여 보존합니다.

## 위치 선택

- **Local QSTL_QICK / Browse…**: PC의 저장소 폴더를 고릅니다. 라이브러리 원본은 그 아래 `qick/qick_lib/qick` 코드 폴더입니다.
- **Firmware build manifest / Browse…**: 성공한 v4 빌드의 `build_manifest.json`을 고릅니다. 같은 폴더의 BIT/HWH/XSA 해시와 XSA 내부 BIT/HWH 일치를 확인합니다. 현재 구현은 이 v4 manifest 형식을 지원합니다.
- **Board repository / Browse board…**: 입력한 SSH 계정으로 보드의 실제 폴더 목록을 읽어 선택합니다. 기본값은 확인된 `/home/QSTL_QICK`이며 라이브러리 대상은 그 아래 `qick/qick_lib/qick`입니다.
- **BIT path within repository / Browse board…**: 보드 저장소의 `qick/firmware` 아래 대상 폴더를 고릅니다. BIT 파일명은 텍스트에서 변경할 수 있고 HWH는 같은 위치·이름을 사용합니다. 새 하위 경로도 직접 입력할 수 있습니다.
- PC 탐색기는 로컬 경로, **Browse board…**는 SSH 보드 경로입니다. 경로를 선택하거나 조회할 때 폴더를 만들거나 파일을 변경하지 않습니다. 화면에 라이브러리/BIT/HWH **원본 → 대상**을 표시합니다.

보드 저장소는 실제 디렉토리인 `/home/...` 또는 `/root/...`만 지원합니다. 대상 경로의
심볼릭 링크와 저장소 밖 firmware 경로는 거부합니다. 기본 Board Python은 확인된
`/usr/local/share/pynq-venv/bin/python3`입니다. 다른 위치는 직접 입력할 수 있습니다.

## 설치 정보와 서버 BIT 경로 보존

`qick_lib` 전체를 교체하지 않습니다. `qick_lib/qick` 코드 폴더만 교체하며,
`qick_lib/qick.egg-info`, Python `site-packages/qick.egg-link`와 `.pth` 연결은 보존합니다.
현재 PC/보드의 QICK 버전은 모두 0.2.357이며 의존성 목록도 같습니다.
버전·Python 요구사항·의존성·entry point가 달라지면 자동 파일 교체를 거부합니다.
그 경우 별도의 editable 재설치가 필요합니다. 보드의 설치 기준 디렉토리는
`setup.py`가 있는 `/home/QSTL_QICK/qick`입니다. GUI는 `pip install -e .`를 실행하지 않습니다.

보드의 기존 `qick/qick_lib/qick/pyro_cli.py`는 그 파일의 `start_server(..., bitfile=...)`
문자열 값만 선택한 BIT의 절대경로로 바꿉니다. 기존 nameserver/port/iface/soc_class,
주석과 줄바꿈은 유지하고, PC의 `pyro_cli.py` 기본값으로 보드 설정을 덮지 않습니다.
변경본은 staging에 먼저 만들고 원본·변경본 해시와 이전/새 BIT 경로를 기록합니다.
실제 파일 교체 시 라이브러리 및 BIT/HWH와 함께 반영하며, 복원 또는 교체 중 실패 시에는
원래 `pyro_cli.py`와 BIT/HWH를 함께 돌려놓습니다. 호출이 여러 개이거나 bitfile이 동적
표현식인 경우 추측하여 수정하지 않고 준비를 거부합니다. 예전 format 1/2 준비물도 다시
검토·준비해야 합니다. 현재 준비물 형식은 3입니다.

이 경로 변경은 다음 서버 시작에 적용됩니다. Notebook이나 별도 실행 코드가 명시적으로
다른 BIT를 지정하면 그 경로를 사용하므로, 해당 코드 자체는 사용자가 확인해야 합니다.

## 사용 흐름

1. **Inspect board**로 보드 Python, 실제 QICK import 경로, 여유 공간, 실행 중인 펌웨어 정보와 이전 백업을 조회합니다. 이때 파형을 출력하거나 FPGA를 다운로드하지 않습니다.
2. **Review local package**로 성공 manifest/파일 해시/같은 XSA의 BIT·HWH 및 GUI Python 환경의 QICK 소스 파일 일치를 확인합니다.
3. **Upload and verify staging**은 별도 임시 거래 폴더에 `qick_lib/qick`와 BIT/HWH를 전송하고 해시를 대조합니다. 기존 보드 `pyro_cli.py`의 BIT 경로 변경본도 여기에서 준비해 표시합니다. 기존 실행 파일은 아직 바꾸지 않습니다. XSA는 PC에서만 확인하고 전송하지 않습니다.
4. 다른 클라이언트를 포함해 모든 실험·출력을 중지하고 QICK 서버를 수동으로 종료합니다. 두 확인란을 체크한 뒤 **Apply prepared update…**를 누릅니다. 대상과 패키지를 다시 확인하며, 확인창의 기본 선택은 No입니다. 서버가 실행 중이거나 상태를 확인할 수 없으면 교체를 거부합니다. Pyro nameserver는 계속 실행돼 있어야 합니다.
5. 이전 코드 폴더(기존 `pyro_cli.py` 포함)/BIT/HWH를 보존한 뒤 준비된 파일을 교체합니다. 이 시점의 상태는 **files updated / restart required**이며 FPGA 적용 완료가 아닙니다. `python -m qick.pyro_cli ...`로 수동 재시작하면 변경한 BIT 경로를 사용합니다. Notebook이면 커널 프로세스도 재시작해야 합니다. 서버 시작 명령이나 Notebook 셀 자체는 자동 수정하지 않습니다.
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
- 생산 설정 JSON, 실험 데이터, Git 브랜치, Notebook, 서버 시작 명령은 업데이트 대상이 아닙니다. `pyro_cli.py`에서는 위에 명시한 BIT 경로만 변경합니다.

## 2026-10-14 실행한 검증

- qcodes2 Python 3.12.5에서 Paramiko 4.0.0 설치와 import 확인.
- 실제 `192.168.2.99`의 폴더 목록을 production Qt Browse 버튼으로 조회: 상위 이동, 폴더 진입, 잘못된 경로 거부, 선택한 저장소/BIT/HWH 및 launcher 경로 표시 PASS. Qt는 offscreen으로 실행했습니다.
- 성공 v4 manifest의 106개 전송 파일/해시, 동일 XSA의 BIT/HWH 및 현재 로컬 QICK 소스 검토 PASS. 메타데이터는 전송 목록에 포함되지 않습니다.
- 보드 Python 3.8.2에서 설치 메타데이터 검사 helper를 메모리에서 실행해 현재 경로·버전·의존성과 editable 링크 일치 확인. 런처나 QickSoc는 실행하지 않았습니다.
- 임시 디렉토리 테스트 **27 PASS**: metadata/link 보존, 실제 editable import·버전 조회, 교체/복원, HWH rename 실패 복구, 경로 동기화, 나머지 launcher 옵션 보존, Unicode/CRLF/기존 보드 줄바꿈, 동적·중복 호출 거부, staging/원본 변조 및 이전 준비물 거부.
- 실제 보드 `pyro_cli.py`를 읽어 만든 로컬 변경본의 AST를 비교하여 BIT 값 외 변경이 없음을 확인했습니다. 보드 원본 해시는 동일합니다.

증거는 QSTL_QICK 저장소의
`analysis_results/awg_tuning_v4/gui_update_pyro_path_20261014/REPORT.md`와 같은 폴더의
`transaction_tests.xml`, `local_and_board_metadata.json`, `browse/results.json`에 있습니다.
테스트 코드는 `test_qick_update_transactions.py`입니다.

## 실행 검증이 남은 항목

- 서로 다른 BIT·HWH/manifest 변조 등 전체 부정 입력 조합.
- SSH 잘못된 host key·심볼릭 링크·권한 오류·시간 초과·실제 전송 중단.
- 실제 동시 프로세스 잠금·강제 종료·전원 손실 후 복구.
- 실제 교체를 포함한 전체 GUI 상태 전이, 백업 선택, 확인창, 작업 중 닫기.
- 시험용 보드에서 서버 정지 판별, 실제 드라이버 import, 수동 재시작, 잘못된 firmware 식별, 교체 후 GUI 재시작.

**실제 보드 업데이트는 아직 실행하지 않았습니다. 위 남은 항목까지 PASS라고 주장하지 않습니다.**
