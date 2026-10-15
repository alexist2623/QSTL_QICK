# Composite RF amplitude parameter UI

2026-10-15 요청에 따라 preset과 Custom의 amplitude 설정을 parameter 방식으로 통일했습니다.

## 변경 사항

- CPMG, UDD, Hahn echo: Global gain parameter를 선택합니다. 시작·끝 π/2를 포함한 모든 pulse에 적용됩니다.
- Custom: 각 pulse 행의 Amplitude parameter를 선택합니다. Use common amplitude mode와 행별 Manual/calibration 버튼은 화면에서 제거했습니다.
- Use power calibration (dBm) 체크박스 하나로 진폭 단위를 선택합니다. 해제 시 정수 gain, 선택 시 dBm이며 값과 sweep 시작·끝 값에 같은 단위를 사용합니다.
- Calibration DB와 run 선택은 calibration을 사용할 때 활성화됩니다. 실제 변환에는 기존 보정 데이터와 검사 기준을 그대로 사용합니다.
- Gain/dBm의 값과 sweep 설정을 따로 보존합니다. 모드를 처음 바꾸면 해당 모드 기본값을 사용하며, gain을 임의로 dBm으로 환산하지 않습니다. 이후 모드 전환과 JSON 저장·재로드로 각 설정을 복원합니다.
- 예전 파일의 독립적인 π/π2 진폭이나 서로 다른 calibration 설정을 묵시적으로 합치지 않습니다. 독립 preset은 Global parameter를 직접 고를 때 공유로 전환하며, 혼합 calibration 파일은 안내와 부분 체크 상태로 원래 값을 보존합니다.

## 검증 결과

| 범위 | 고유 검사 수 | 결과 |
| --- | ---: | --- |
| 기존 RF GUI / T2 editor | 111 | PASS |
| 신규 amplitude UI·migration·저장·재로드 | 27 | PASS |
| T2 integration / fine duration editor | 31 | PASS |
| 모델·실제 Python compiler·calibration | 76 | PASS |
| 합계 | 245 | PASS |

최초 실패와 중간 결과는 별도 로그로 보존했습니다. 문제는 mode별 값 저장, UDD 재로드 시 표시 정밀도로 인한 delay 이름 중복, 새 UI에 맞지 않는 기존 검사 조작, Single의 휴면 composite 설정 로드와 관련됐습니다. 동작 문제를 수정했고 기존 검사에서는 UI 조작·새 저장 필드 기대값만 갱신했습니다. UDD의 기존 spinbox 표시 정밀도 비교 외 파형·진폭·phase 검사를 완화하지 않았습니다.

마지막 Single 휴면 목록 수정 후 신규 amplitude 27개, 관련 기존 loader 7개, T2 editor 33개를 재검사했습니다. 재검사 횟수는 고유 검사 합계에 중복으로 더하지 않았습니다. 다른 검사와 화면 캡처의 소스 시점 및 SHA256은 results.json, 각 실행 결과 JSON에 구분해 보존했습니다.

실제 offscreen 위젯 화면을 열어 Global parameter, Custom 행별 선택, dBm 값·sweep 단위와 제거된 버튼을 확인했습니다. 첫 캡처의 폰트 누락은 캡처 환경 오류로 보존하고 Windows 폰트를 명시한 v2 캡처를 확인했습니다.

## 범위와 증거

- 생산 변경: `C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI/DCWaveform_Generator.py`
- 새 검사: `test_rf_amplitude_parameter_editor.py`; 기존 RF GUI/T2/fine-duration 검사 4개 파일을 새 UI와 저장 형식에 맞게 갱신했습니다.
- 이번 변경은 소프트웨어 UI 작업입니다. RTL은 수정하거나 재실행하지 않았으며, 이전 GUI→RTL 결과를 이번 UI 수정의 새 RTL 결과로 표시하지 않습니다.
- 보드 접속·업로드·실험 실행·기존 GUI 재시작·펌웨어 교체·commit/push는 수행하지 않았습니다. 사용자 설정 JSON은 해시가 동일합니다.
- 두 저장소의 기존 `awg_tuning_v4` 브랜치를 유지했습니다.
- `results.json`: 최종 소스·로그 해시, 변경 범위, 검증 결과.
- `production_change.diff`: 이번 요청 시작 시점 대비 생산 코드 변경.
- `preset_hahn_manual_v2.png`, `custom_calibration_v2.png`: 확인한 실제 위젯 화면.
