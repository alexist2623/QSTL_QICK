# 기본 GUI·RTL 검증 결과 — 2026-10-15

요청하신 간단한 케이스를 새로 검사했습니다. **전체 PASS는 아닙니다.**
고정 1µs RAMP가 1클록 늘어나는 수치 오류 1건과 현재 GUI/컴파일러의 제한을
확인했습니다. 생산 Python·GUI·RTL·펌웨어는 수정하지 않았습니다.

실행 날짜는 Vancouver 2026-10-15이며 UTC 로그 날짜는 2026-10-16입니다.
[원본 요청 문서](REQUESTED_TODO.txt), [범위](PLAN.md), [통합 결과](results.json).

## 결과

| 검증 층 | 새 실행 결과 |
|---|---|
| 관련 소프트웨어 회귀 | 12개 모듈의 고유 110검사 PASS, 실패/skip 0, exit0 |
| GUI 입력→생산 컴파일러→tProcessor 실행 모델 | 계획 38조건: 정상 29, 의도한 경계 거부 4, 수치 실패 1, 예상외 거부 2, 미지원 2 |
| 실제 GUI 입력→v5 RTL 대표 실행 | 4묶음 PASS, 16점·32 shots·904명령, 명령값/시각 오류 0 |
| 디지털 출력 | 합산 3,818,544 lane 및 최종 DAC register slice 3,808,944 lane 검사 PASS |
| Virtual matrix | 비대각 3×3 변환과 실제 SET payload의 독립 대조 72검사 PASS |
| 보존 확인 | 생산 코드·설정·펌웨어 등 2,364파일의 전후 SHA256 동일 |

검사 단위가 다르므로 위 숫자를 합쳐 하나의 테스트 개수로 표시하지 않습니다.
GUI의 자식 프로세스 exit0만으로 PASS를 판단하지 않고 각 결과의 status를 확인했습니다.
SET-only 두 조건은 실행 완료로 세지 않습니다. mixed matrix에서 실제 입력 거부를
확인했고 identity 변형은 동일 표현 제한 때문에 실행하지 않았습니다.

## 확인된 오류와 제한

### 고정 1µs RAMP가 301클록으로 변환됨

`log_ramp_02`: 앞 RAMP를 0.464158883361µs로 입력한 뒤, 다음 RAMP는 정확히 1µs로
입력했습니다. 저장된 GUI 경계는 3464.158883361ns와 4464.158883361ns입니다.
십진수 차는 정확히 1000ns지만 float 차감 결과는 1000.0000000000005ns입니다.
`dc_waveform_core.py:2197`의 차분이 `:2128`의 허용오차 없는 ceil을 거치면서
300.0000000000001→301클록, 즉 4,800→4,816 samples가 됩니다.
300MHz에서 요청보다 3.333333ns 깁니다. 실제 생성된 명령과 실행 모델에서도 확인했습니다.

이 실패는 독립 요청 기준과의 불일치이며 검사기를 완화하지 않았습니다. 해당 10점
로그 grid 전체를 실제 RTL이나 실물 보드에서 실행했다는 뜻은 아닙니다.
[실패 케이스](gui_cases/log_ramp_02), [GUI 전체 결과](gui_cases/batch_status.json).

### Fine RF의 세그먼트 교차 두 조건이 컴파일에서 거부됨

`rf_fine_crossing_False`, `rf_fine_beyond_final_False`는
`require_within_segment=False`여도 공유 포트 명령 순서 변화 또는 3클록 미만 간격
검사에 걸렸습니다. 같은 범위의 coarse RF 조건은 통과했습니다. 이 옵션은 HOLD 내부
제한을 해제할 뿐 공유 포트의 스케줄 제약까지 해제하지 않습니다. 실패한 입력을
수정하거나 시각을 이동해서 통과시키지 않았고, 해당 조건은 현재 제약으로 남겼습니다.

반면 `require_within_segment=True`의 coarse/fine 교차·마지막 구간 초과 4조건은
첫 점이 내부에 있고 후반 점이 초과할 때 정상 거부됐습니다. 이는 예상한 음성 검사입니다.

### 정확한 SET-only GUI 파형은 미지원

현재 GUI/PulseSequence는 증가하는 경계 시간과 양수 incoming RAMP 시간을 요구합니다.
RAMP=0인 정확한 3단계 SET-only identity/nonidentity 조건은 미지원입니다.
저수준 컴파일러나 RTL의 SET 명령 자체가 미지원이라는 뜻은 아닙니다.

초기 offscreen 시험에서 잘못된 0 RAMP 입력의 경고창을 띄울 때 access violation도
기록했습니다. 여러 MainWindow를 연속 생성/종료하는 초기 실행기는 삭제된
QScrollArea에 접근하는 지연 콜백 오류를 드러냈습니다. 최종 케이스별 독립 프로세스는
이 생명주기 영향을 분리했으며, 생산 GUI의 해당 동작이 수정됐다고 주장하지 않습니다.

## 실제 수행 범위

GUI 시간 grid는 0.1~100µs의 로그 간격 10값을 HOLD와 RAMP에 각각 개별 입력한
20조건입니다. native 로그 하드웨어 sweep으로 표시하지 않습니다. 그 외 voltage
상승/하강/N=1, 반복, identity/nonidentity matrix, RF 주파수 및 coarse/fine 길이의
내부/교차/마지막 구간 초과 조건을 검사했습니다. 독립 요청 시간축·segment 구조·C@V·
양자화 기준과 GUI committed 값 및 실제 실행 명령을 나누어 대조했습니다.

대표 RTL은 HOLD 1.0/1.9µs×virtual voltage 5/15mV, RAMP 0.1/0.4µs×5/15mV,
RF0 180/225MHz×5/15mV, fine RF0 94/95/96/97sample입니다. 각각 4점×2반복이며
세 AWG/RF 쌍을 확인했습니다. RF offset +100ns는 명시한 입력이고 정확한 동시 시작은
이번 범위가 아닙니다. fine 기준은 0.208333ns/sample이며 95→96sample의 한 명령→두
명령 전환을 확인했습니다.

이전 PASS/명령 입력을 재사용하지 않고 새 Qt 입력·컴파일·RTL 실행을 수행했습니다.
다만 검증된 기존 시뮬레이션 기반 구조와 vendor library는 재사용했습니다. coarse의
matrix/축은 Qt 모달 입력이며 RF 설정은 MainWindow settings load, fine는 duration
위젯의 실제 키 입력입니다. 38조건 전체가 RTL 실행인 것은 아닙니다.

## 증거

- [110개 회귀검사](software_regression/REPORT.md), [독립 검토](software_regression/INDEPENDENT_REVIEW_FINAL.md)
- [GUI 케이스 보고서](gui_cases/REPORT.md), [GUI 개별 결과](gui_cases/batch_status.json)
- [실제 RTL 보고서](rtl/reporting/REPORT.md), [RTL 원본·수치 archive 목록](rtl/reporting/archive_manifest.json)
- [Matrix 적용 최종 DAC 디지털 파형](rtl/reporting/matrix_hold_final_dac_rtl.png)
- [Fine RF 94~97sample 디지털 파형](rtl/reporting/fine_94_97_rtl.png)
- [소스·설정 보존 확인](preservation_audit.json), [전체 evidence 해시 목록](archive_manifest.json)

수치 CSV 70개(309,459행)를 포함한 RTL 증거 214파일을 무손실 압축하고 복원 해시를
검사했습니다. 원본 외부 실행 폴더도 유지했습니다. 대표 그림 두 개는 실제 열어
확인했습니다. Qt offscreen 캡처에는 글자가 누락되는 한계가 있어 화면 글자로 수치가
검증됐다고 주장하지 않으며 committed JSON/위젯 값/명령 입력을 근거로 사용했습니다.

## 이번에 하지 않은 항목

오실로스코프·보드 접속, 실제 Run worker/업로드/ADC·FIR 수집, 아날로그 파형·정밀
시간·주파수·전압 측정은 하지 않았습니다. 후속 물리 검증의 전체 파형 보관 및
트리거/전송 오류 복구도 남아 있습니다. RF 길이의 전체 로그 grid 물리/RTL 검증을
완료한 것으로 보지 않습니다.

TODO의 레지스터 연산형 RF duration sweep과 그룹 sweep은 미구현 상태이며 PASS가
아닙니다. 현재 10,000점 fine DMEM 제한은 [별도 GUI 용량 확인](../fine_duration_10000_20261015/REPORT.md)에
기록돼 있습니다. 이번 작업에서는 기능 구현·수정, 새 합성, 펌웨어 교체를 하지 않았습니다.
기존 두 저장소의 `awg_tuning_v4` 브랜치를 유지합니다.
