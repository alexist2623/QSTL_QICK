"""Collect final GUI-only feature evidence without running hardware or synthesis."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
V5 = HERE.parent
GUI = Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    suite = ET.parse(HERE/'final_named.xml').getroot().find('testsuite')
    assert suite is not None
    assert int(suite.attrib['failures']) == int(suite.attrib['errors']) == 0
    assert int(suite.attrib.get('skipped', 0)) == 0
    count = int(suite.attrib['tests'])
    execution = json.loads((HERE/'final_named_exit.json').read_text())
    assert execution['exit_code'] == 0 and execution['tests'] == count
    log = (HERE/'final_named.log').read_text(encoding='utf8')
    assert 'QT_EXPLICIT_TEARDOWN_COMPLETE' in log and 'QT_CALLBACK_ERRORS:' not in log
    compiler = json.loads((V5/'compiler_equivalence.json').read_text())
    assert compiler['complete'] and len(compiler['cases']) == 9
    for path, expected in compiler['source_hashes'].items():
        assert sha(path) == expected, ('source changed after compile', path)
    for case in compiler['cases']:
        assert case['passed']
        for path, expected in case['files'].items():
            assert sha(path) == expected
    rtl = json.loads((HERE/'rtl/result.json').read_text())
    assert rtl['passed'] and rtl['cases'] == 7 and rtl['actual_rf_bursts'] == 126
    for name, expected in rtl['reports'].items():
        assert sha(HERE/'rtl'/name) == expected
    proof = json.loads((HERE/'rtl/final_source_input_equivalence_named.json').read_text())
    for path, expected in proof['source_hashes'].items():
        assert sha(path) == expected, ('RTL source proof changed', path)
    files = [
        'DCWaveform_Generator.py', 'dc_waveform_core.py', 'dc_waveform_widgets.py',
        'qick_qcodes_experiment.py', 'acquisition_preview.py', 'awg_sweep_map.py',
        'test_rf_t2_delay_core.py', 'test_rf_t2_delay_editor.py',
        'test_rf_delay_software_sweep.py', 'test_rf_t2_integration.py',
        'test_acquisition_preview.py', 'test_dc_waveform_gui_rf.py',
    ]
    result = dict(
        passed=True, verified_at=datetime.now().astimezone().isoformat(),
        affected_tests=count, failures=0, errors=0, skipped=0, qt_clean_exit=True,
        current_legacy_compiler_equivalent_cases=9,
        actual_gui_to_v4_rtl_cases=7, actual_dds_bursts=126,
        manual_custom_rtl=True, summed_calibration_expected_rejection=True,
        summed_calibration_rtl=False, ordinary_rf_calibration_software_test=True,
        v5_timing_profile_changed=False, board_access=False,
        source_hashes={(GUI/name).as_posix():sha(GUI/name) for name in files},
        evidence_hashes={str(path):sha(path) for path in (
            HERE/'final_named.xml', HERE/'final_named.log', HERE/'final_named_exit.json', HERE/'rtl/result.json',
            HERE/'custom_named_manual_editor.png', HERE/'custom_named_calibration_editor.png',
            V5/'compiler_equivalence.json',
        )},
    )
    report = f'''# Composite RF / Custom parameter update

현재 요청한 Custom parameter 기능의 구현과 관련 검증을 완료했습니다.
기존 `awg_tuning_v4` 브랜치에서 작업했습니다.

## 동작

- Custom의 각 Pulse는 frequency, duration, amplitude, phase parameter를 개별 선택합니다. Delay는 이름 있는 delay parameter를 선택합니다. 같은 이름을 선택하면 값을 공유합니다.
- `Use common amplitude mode`에서 `Calibration (dBm)` 체크를 해제하면 Manual gain, 체크하면 Calibration dBm을 사용합니다. 모드와 보정 DB/run만 공통이며 각 펄스의 진폭 parameter 선택은 독립적입니다.
- 진폭 표는 Manual에서 `Gain`, Calibration에서 `Target [dBm]`으로 표시합니다. 모드를 바꿀 때 gain을 dBm으로 그대로 재해석하지 않으며 각 모드의 편집 중 값은 별도로 보존합니다.
- Delay, amplitude, phase parameter에 sweep을 지정할 수 있고 실험 sweep 목록의 단위는 각각 us, gain 또는 dBm, deg입니다. 저장/불러오기, 선택 지점 미리보기와 결과 메타데이터에 반영합니다.
- T2 처음/끝 π/2는 각각 선택할 수 있고 선택한 π duration의 절반을 매번 계산합니다. 선택 이름은 `d0/2`처럼 표시하며 원래 참조 `d0`를 유지합니다.
- Hahn echo는 전체 자유 진화 시간 τ를 양쪽 τ/2로 나눕니다. 프리셋의 Global frequency/Global gain은 유지하고 Custom 전환 시 실제 적용값을 각 행의 parameter 참조로 옮깁니다.
- Composite 파형 색상은 한 가지로 통일했고 Final phase 뒤 설명을 제거했습니다. Phase는 현재 RTL의 공통 시간 기준 위상에 더하는 offset입니다. 위상 초기화나 저수준 명령 타이밍은 변경하지 않았습니다.
- 기존 혼합 Manual/Calibration 설정을 불러오면 원래 값을 보존합니다. 공통 모드로의 전환은 사용자가 선택할 때 적용합니다.

## 이번 검증

| 범위 | 결과 |
|---|---|
| GUI/core/runtime/preview/map/기존 회귀 9개 모듈 | {count} PASS, 실패/오류/skip 0, Qt callback 오류 없음, 정상 종료 |
| 기존 시스템 9조건의 현재 GUI/compiler 재컴파일 | PMEM/DMEM과 GUI PMEM 전부 기존 입력과 바이트 동일 |
| 새 실제 MainWindow → Run Experiment → v4 RTL | 7조건, 3 RF/AWG 쌍, 각 2회, DDS burst 126개 PASS |
| τ×π 길이 | 3×2 조합, π/2 길이와 상대 출력 시각 정확히 일치 |
| Hahn → Custom의 개별 진폭/위상 | 끝단 gain1500/phase0°, 본체 gain750/phase90° 실제 DDS 확인 |
| 보정 소프트웨어/preview | 알려진 DB의 dBm→gain, 주파수 sweep 전체 범위에 맞는 run 선택과 반올림 일치 |
| v4 합산 출력의 Calibration 제한 | 세 쌍과 실제 runtime 경로에서 기존 사전 차단 확인 |

실제 RTL은 새 입력으로 실행한 **v4 디지털 시뮬레이션**입니다. 별도 진행 중인 v5 합성 결과나 v5 Python 지연 정합의 완료를 뜻하지 않습니다. 원래 6개 RTL 입력은 최종 소스로 다시 컴파일하여 PMEM/DMEM/ASM/예상 명령과 실제 RF 이벤트가 동일함을 확인했습니다. 새 serialization 필드의 차이는 별도 기록했습니다.

현재 v4의 AWG+RF 합산 출력은 기존 production 코드가 Calibration을 차단합니다. 이 제한을 우회하지 않았고 합산 출력의 Calibration RTL 성공으로 표시하지 않습니다. 일반 RF의 보정 변환은 소프트웨어/compiler/preview에서 검증했습니다.

## 실패 기록과 범위

옛 numeric widget API는 이름 있는 parameter 편집 API로 갱신했습니다. 이후 기존 GUI 검사 3건은 삭제된 펄스 이름의 전체 JSON 부재, legacy 수동 진폭 위젯 활성 상태, 기본 JSON의 완전 동일성을 가정해 실패했습니다. 이름 있는 parameter를 유지하는 현재 UI에 맞게 정확한 예상 상태와 serialization을 갱신했으며, 실제 pulse 값·타이밍·sweep 연결의 검사는 유지했습니다. 초기 로그와 재검사 로그를 보존했습니다.

이전 duration rename callback 오류는 수정 후 이번 회귀에 포함되어 통과했습니다. 초기 GUI geometry, 보정 fixture metadata, RTL 준비 단계의 비활성 필드 비교 문제도 원본 증거와 원인 구분을 보존했습니다. 실제 출력 검사 허용치를 완화하지 않았습니다.

실제 보드 출력/아날로그 측정과 ADC/FIR 산술 검증은 하지 않았습니다. AWG IIR 뒤에 더해지는 DDS의 면적과 clipping은 기존 AWG DC 면적 보상 대상이 아닙니다. 펌웨어/RTL/XDC/사용자 설정 JSON을 수정하거나 보드 업로드·서버 재시작·commit/push를 하지 않았습니다.

[Manual 화면](custom_named_manual_editor.png) · [Calibration 화면](custom_named_calibration_editor.png) · [전체 테스트](final_named.xml) · [실제 RTL 상세 보고서](rtl/REPORT.md) · [실제 진폭/위상 파형](rtl/named_hahn_actual_rtl.png) · [기존 입력 9조건 비교](../compiler_equivalence.json)
'''
    (HERE/'REPORT.md').write_text(report, encoding='utf8')
    result['report_sha256'] = sha(HERE/'REPORT.md')
    (HERE/'result.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    authorization = json.loads((V5/'authorized_gui_fix.json').read_text())
    authorization['files'].update(result['source_hashes'])
    authorization['composite_reason'] = 'Explicit user requests: Custom per-pulse delay/amplitude/phase parameters and sweeps; common Manual/Calibration mode; T2 endpoints, Hahn, global preset values and monochrome preview.'
    authorization['composite_evidence'] = str(HERE/'result.json')
    authorization['composite_evidence_sha256'] = sha(HERE/'result.json')
    (V5/'authorized_gui_fix.json').write_text(json.dumps(authorization, indent=2), encoding='utf8')
    print(json.dumps({key:result[key] for key in ('passed','affected_tests','actual_gui_to_v4_rtl_cases','actual_dds_bursts')}))


if __name__ == '__main__':
    main()
