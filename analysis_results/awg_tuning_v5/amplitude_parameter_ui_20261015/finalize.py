"""Record this GUI-only change without rewriting earlier RTL evidence."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
GUI = Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def digest(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()

baseline_path = HERE.parent / 'expanded_gui_rtl_20261015/after.json'
baseline = read(baseline_path)['files']
allowed_names = {
    'DCWaveform_Generator.py', 'test_dc_waveform_gui_rf.py',
    'test_rf_t2_delay_editor.py', 'test_rf_t2_integration.py',
    'test_rf_fine_duration_editor.py',
}
allowed_paths = {str(GUI / name).lower() for name in allowed_names}
changes = []
unexpected = []
for path, before in baseline.items():
    after = digest(path)
    if before.lower() != after:
        change = dict(path=path, before_sha256=before, after_sha256=after)
        changes.append(change)
        if str(Path(path)).lower() not in allowed_paths:
            unexpected.append(change)
assert not unexpected, unexpected
user_json = [entry for entry in read(HERE / 'before_hashes.json')
             if Path(entry['Path']).suffix == '.json']
assert all(digest(entry['Path']) == entry['Hash'].lower() for entry in user_json)

logs = {
    'existing_editor_tests_second.log': 111,
    'three_editor_modules_final.log': 57,
    'model_compiler_calibration.log': 76,
    'final_loader_regression.log': 7,
    'final_t2_editor_regression.log': 33,
    'latest_single_fix.log': 27,
}
for name, count in logs.items():
    text = (HERE / name).read_text(encoding='utf-8-sig')
    assert re.search(rf'\b{count} passed\b', text), name
    assert not re.search(r'\d+ failed|\d+ error', text), name

latest = read(HERE / 'latest_single_fix.json')
source = GUI / 'DCWaveform_Generator.py'
result = {
    'completed_at': datetime.now().astimezone().isoformat(),
    'passed': True,
    'scope': 'Composite RF amplitude parameter UI, migration, persistence, preview and software compiler/calibration regression',
    'unique_tests': 245,
    'unique_test_breakdown': {'existing_editor': 111, 'amplitude_editor': 27,
                              't2_integration_and_fine_editor': 31,
                              'model_compiler_calibration': 76},
    'rechecks_are_not_added_to_unique_total': True,
    'final_source_sha256': digest(source),
    'latest_amplitude_run': latest,
    'changed_existing_files': changes,
    'new_test_file': {'path': str(GUI / 'test_rf_amplitude_parameter_editor.py'),
                      'sha256': digest(GUI / 'test_rf_amplitude_parameter_editor.py')},
    'baseline_path': str(baseline_path),
    'baseline_files_checked': len(baseline),
    'unexpected_changed_files': unexpected,
    'user_json_files_checked': len(user_json),
    'user_json_unchanged': True,
    'logs': {name: {'passed_count': count, 'sha256': digest(HERE / name)} for name, count in logs.items()},
    'initial_failure_logs_preserved': [
        'existing_editor_tests.log', 'affected_retry.log',
        '../rf_amplitude_parameter_editor_first.log'],
    'visual_review': {
        'images_opened': ['preset_hahn_manual_v2.png', 'custom_calibration_v2.png'],
        'image_source_sha256': read(HERE / 'screenshots_v2.json')['source_sha256'],
        'note': 'Captured and opened before the final Single dormant-composite loader fix; no visible controls changed afterward. Initial blank-font images are preserved but rejected as visual evidence.',
    },
    'rtl_simulation_run_for_this_change': False,
    'board_access': False,
    'live_gui_restarted': False,
    'commit_or_push': False,
}
(HERE / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
report = '''# Composite RF amplitude parameter UI

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
'''
(HERE / 'REPORT.md').write_text(report, encoding='utf-8')
print(json.dumps({key: result[key] for key in ['passed', 'unique_tests', 'baseline_files_checked', 'user_json_files_checked', 'unexpected_changed_files', 'final_source_sha256']}, ensure_ascii=False))
