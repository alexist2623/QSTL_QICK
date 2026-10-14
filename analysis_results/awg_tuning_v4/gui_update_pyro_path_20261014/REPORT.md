# GUI 업데이트: 설치 정보 보존 및 pyro_cli BIT 경로 동기화

2026-10-14 사용자 후속 요청에 따라 구현 및 제한된 실행 검증을 마쳤습니다.
**실제 보드의 업로드·파일 교체·재설치·서버 재시작·FPGA 다운로드는 실행하지 않았습니다.**

## 구현 결과

- 이전 코드는 `.egg-info`를 업로드에서 제외하면서 `qick_lib` 전체를 교체하여 보드 설치 메타데이터를 잃는 문제가 있었습니다. 이제 `qick_lib/qick` 코드 폴더만 교체합니다. `qick.egg-info`, `site-packages/qick.egg-link`, `.pth` 및 라이브러리 루트의 다른 파일을 보존합니다.
- PC와 보드의 버전·Python 요구사항·의존성·entry point가 같을 때만 파일 교체를 허용합니다. 서로 다르면 별도 editable 재설치가 필요하다고 표시하고 거부합니다. GUI에서 pip를 자동 실행하지 않습니다.
- 기존 보드 `qick/qick_lib/qick/pyro_cli.py`의 `start_server(..., bitfile=...)` 문자열 값만 선택한 BIT의 절대경로로 바꿉니다. PC의 런처 파일로 덮지 않으므로 기존 보드의 ns_host/ns_port/proxy_name/soc_class/iface와 주석·줄바꿈을 유지합니다.
- staging에서 변경본을 만들고 이전/새 경로와 원본/변경본 SHA256을 기록합니다. Apply 시 코드·BIT/HWH와 함께 적용하고, 복원 또는 교체 중 오류 시 원래 코드·런처 경로·BIT/HWH를 함께 복구합니다.
- GUI 원본→대상 표시와 Apply/Restore 확인 문구에 런처 경로 변경을 포함했습니다. 경로 선택만으로 보드 파일을 변경하지 않습니다.
- 동적인 bitfile 표현식이나 복수 start_server 호출은 추측하여 수정하지 않습니다. 예전 준비물(format 1/2)은 새 방식(format 3)으로 다시 준비해야 합니다.

## 실제 확인한 환경과 경로

- PC: `C:/Users/Measurement2/.conda/envs/qcodes2/python.exe`, Python 3.12.5.
- 이 환경에 Paramiko 4.0.0 설치 완료. 의존성으로 bcrypt 5.0.0, cryptography 50.0.2, invoke 3.0.3, PyNaCl 1.6.2, cffi 2.1.1 설치. cffi는 기존 1.17.1에서 갱신됐습니다. 별도 `qcodes` 환경은 수정하지 않았습니다.
- 보드: `192.168.2.99`, 저장소 `/home/QSTL_QICK`, Python `/usr/local/share/pynq-venv/bin/python3` (3.8.2).
- 설치 정보: `/home/QSTL_QICK/qick/qick_lib/qick.egg-info`.
- editable 링크: `/usr/local/share/pynq-venv/lib/python3.8/site-packages/qick.egg-link` → `/home/QSTL_QICK/qick/qick_lib`.
- PC/보드 버전은 모두 0.2.357이며 요구 의존성 목록이 일치합니다. `.egg` 압축 파일이 아니라 `.egg-info` 디렉토리가 확인됐습니다.
- `pip install -e .`의 기준 위치는 `setup.py`가 있는 `/home/QSTL_QICK/qick`입니다. 이번에는 보드에서 이 명령을 실행하지 않았습니다.

현재 보드 런처 BIT는 아래와 같습니다. **여전히 이 값이며 실제 변경하지 않았습니다.**

```text
/home/QSTL_QICK/qick/firmware/projects/qstl_awg_v2/bitstream.bit
```

로컬 검증용 변경본에서는 선택한 예시 경로가 다음과 같이 들어가는지 확인했습니다.

```text
/home/QSTL_QICK/qick/firmware/projects/qstl_awg_v4/bitstream.bit
```

새 버전 문자열을 고정해서 쓰는 구현은 아닙니다. GUI에서 선택한 저장소와 BIT 경로를 사용합니다.

## 수행한 검증

| 검증 | 결과 / 범위 |
| --- | --- |
| 임시 디렉토리의 실제 파일 교체·복원 | **27 PASS**, failure/error 0 |
| editable 설치 보존 | 교체 전/후/복원 후 실제 Python import 및 `importlib.metadata.version('qick')` 정상; metadata·egg-link·pth 보존 |
| 런처 경로 | 새 BIT 경로 반영, 다른 옵션 보존, 복원 시 이전 값 복구 |
| 실패 복구 | HWH rename 실패 주입 후 원본 코드·런처·BIT/HWH 복원 |
| 변경·오류 거부 | 의존성/버전 변경, metadata/link/launcher 변경, staging 변조, 구형 준비물, 동적/복수 호출 거부 |
| 문자열 처리 | Unicode, LF/CRLF/보드 CRCRLF, BOM, 여러 줄 문자열, 따옴표·공백 경로 PASS |
| 로컬 실제 패키지 검토 | 106개 전송 파일, 성공 v4 manifest 해시 및 같은 XSA의 BIT/HWH 일치; `.egg-info` 전송 제외 |
| 보드 Python 검사 | 생산 helper를 메모리에서 실행하여 설치 경로·메타데이터 읽기 확인, exit 0. QICK 런처/FPGA는 실행하지 않음 |
| 실제 GUI → SSH 탐색 | Qt offscreen에서 production Browse 버튼 사용, 6회 폴더 목록 읽기 및 11개 확인 PASS |
| 실제 보드 런처 원본 | SFTP로 읽고 로컬 변경본 AST 비교: bitfile 외 설정 동일, 보드 원본 hash 불변 |
| 범위 확인 | 보호 59파일, 기존 RTL·드라이버·펌웨어 및 완료된 전체 회귀 결과 hash 보존 |

임시 디렉토리 테스트의 보드 root/서버 정지 상태/Python 설치 위치만 fixture로 제공했습니다.
파일 교체·해시 검사·복원 함수는 실제 updater 함수를 실행했습니다. 합성/RTL 시뮬레이션은
추가하지 않았으며 기존 1,223개/9조건/48RC 전체 회귀 결과를 새 기능 PASS로 재사용하지 않았습니다.

GUI 탐색 테스트에서는 전송·교체 메서드를 호출하면 즉시 실패하도록 막고 실제 SSH/SFTP
폴더 조회만 허용했습니다. 알려진 host key를 검증했으며 비밀번호는 증거 파일에 저장하지 않았습니다.
초기 offscreen 캡처의 폰트 누락은 테스트에서 Windows Segoe UI를 명시해 해결했고,
최종 폴더 탐색 및 업데이트 창 이미지를 열어 텍스트·경로 표시를 확인했습니다.

## 증거

- [기계 판독 결과와 소스 해시](results.json)
- [27개 테스트 결과](transaction_tests.xml)
- [보드 설치 정보·현재/예시 BIT 경로·해시](local_and_board_metadata.json)
- [실제 GUI 탐색 결과](browse/results.json)
- [GUI 화면](browse/update_dialog.png)
- [보드 폴더 탐색 화면](browse/repository_browser.png)
- [보드 런처 읽기 원본](board_pyro_cli_before.py), [실행하지 않은 로컬 변경본](board_pyro_cli_preview.py)
- [검증한 테스트 소스](validated_sources/test_qick_update_transactions.py)
- [검증한 구현·설명서 스냅샷](validated_sources/QICK_UPDATE.md)

기존 GUI의 메뉴 추가는 이전 작업에서 완료한 상태 그대로입니다. 이번에는 새 updater
3개 모듈, 신규 전용 테스트와 문서만 수정했습니다. 두 저장소는 기존 `awg_tuning_v4`이고
commit/push하지 않았습니다. 기존 QSTL_QICK v3 체크리스트의 CRLF whitespace 경고는 이 작업과
무관하여 변경하지 않았습니다.

## 실행하지 않은 범위

실제 보드 staging 업로드/Apply/Restore, 수동 서버 재시작 후 실행 펌웨어 식별,
전원 손실·프로세스 강제 종료·실제 동시 업데이트 복구 및 남은 오류 입력 조합은 미검증입니다.
Notebook 또는 별도 코드가 다른 BIT를 직접 지정하는 경우 그 코드까지 변경하지 않습니다.
라이브러리/펌웨어 교체는 아직 수행하지 않았으며 아날로그 출력 검증 결과도 아닙니다.
