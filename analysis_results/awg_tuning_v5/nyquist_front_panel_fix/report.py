"""Verify the display-only Nyquist correction and preserve prior evidence."""
import ast
from copy import deepcopy
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
    before = ast.parse((HERE/'DCWaveform_Generator.py.before').read_text(encoding='utf8'))
    current = ast.parse((GUI/'DCWaveform_Generator.py').read_text(encoding='utf8'))
    old_class = next(n for n in before.body if isinstance(n, ast.ClassDef) and n.name == 'RfPulsePortPanel')
    new_class = next(n for n in current.body if isinstance(n, ast.ClassDef) and n.name == 'RfPulsePortPanel')
    old_init = next(n for n in old_class.body if isinstance(n, ast.FunctionDef) and n.name == '__init__')
    new_index = next(i for i,n in enumerate(new_class.body) if isinstance(n, ast.FunctionDef) and n.name == '__init__')
    new_class.body[new_index] = deepcopy(old_init)
    assert ast.dump(before, include_attributes=False) == ast.dump(current, include_attributes=False)
    suite = ET.parse(HERE/'tests.xml').getroot().find('testsuite')
    assert suite is not None
    assert all(int(suite.attrib.get(key, 0)) == 0 for key in ('failures','errors','skipped'))
    log = (HERE/'tests.log').read_text(encoding='utf8')
    assert 'QT_EXPLICIT_TEARDOWN_COMPLETE' in log and 'QT_CALLBACK_ERRORS:' not in log
    compiler = json.loads((V5/'compiler_equivalence.json').read_text())
    assert compiler['complete'] and len(compiler['cases']) == 9
    for path, value in compiler['source_hashes'].items():
        assert sha(path) == value, path
    paths = ['DCWaveform_Generator.py','test_qick_front_panel.py']
    hashes = {(GUI/name).as_posix():sha(GUI/name) for name in paths}
    result = dict(passed=True, checked=datetime.now().astimezone().isoformat(),
        tests=int(suite.attrib['tests']), exit_code=0,
        changed_production_methods=['RfPulsePortPanel.__init__'],
        other_production_ast_identical=True, source_hashes=hashes,
        compiler_cases_byte_identical=9, hardware_access=False,
        tau_execution_changed=False, rtl_or_firmware_changed=False,
        prior_composite_rtl_not_rerun=True,
        evidence_hashes={str(p):sha(p) for p in (
            HERE/'tests.xml', HERE/'tests.log', HERE/'compiler.log',
            V5/'compiler_equivalence.json', HERE/'DCWaveform_Generator.py.before')})
    (HERE/'result.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    text = f'''# RF editor Nyquist duplicate removal

- RF Output 편집기의 중복 Nyquist zone 입력 행을 제거했습니다. Nyquist zone은 Front Panel에서 선택합니다.
- 숨겨진 내부 값은 유지하므로 Front Panel의 output_nqz가 기존 RF 설정 저장/불러오기, calibration 조회, 프로그램 생성으로 전달됩니다.
- Front Panel의 즉시 Update가 NQZ를 직접 하드웨어에 쓴다고 주장하지 않습니다. 기존 실제 적용은 프로그램의 declare_gen(..., nqz=...) 경로입니다.
- 관련 {result['tests']} 검사 PASS / exit0 / Qt callback 오류 없음. Front Panel NQZ=2 적용, 편집기에서 숨김, 설정 roundtrip 및 hardware-update 경계로 전달되는 spec을 mock으로 확인했습니다.
- 기존 9 시스템 조건 재컴파일 PMEM/DMEM은 바이트 동일합니다. 기존 composite 7조건 RTL의 실행 증거는 보존했으며, 이번 표시 수정 때문에 재실행하지 않았습니다.
- 생산 코드 변경은 RfPulsePortPanel.__init__의 표시/위젯 소유권/안내문에 한정됩니다. 그 생성자를 제외한 전체 모듈 AST가 이전과 동일함을 확인했습니다.

## Tau 설명

현재 preset tau는 rf_template_tau, Custom delay는 rf_delay host 축입니다. 각 좌표에서 구체적인 RF 이벤트와 AWG SET 길이를 계산하여 프로그램을 다시 실행합니다. 실제 pulse 간격은 FPGA가 생성하지만 점 간에는 host 처리 시간이 있습니다.

이는 하드웨어의 필수 제약이 아니라 앞선 구현 선택입니다. 현재 pulse event는 named delay를 숫자 offset으로 합치고 하드웨어 시간 의존성으로 전달하지 않습니다. 기존 RF duration/tProcessor loop 기반에 delay 의존성·후속 RF timestamp·SET/획득 종료·clock 양자화 검사를 연결해야 hardware tau sweep이 됩니다. 고정 N의 UDD도 tau에 선형이므로 UDD라는 이유로 software sweep이 필수인 것은 아닙니다. 이번 수정에서 tau 실행 방식은 변경하지 않았습니다.

RTL/XDC/펌웨어, 실행 중인 GUI/서버 및 보드는 변경하지 않았습니다. 별도 v5 빌드 결과 확인 일정도 그대로입니다.

[검사 결과](tests.xml) · [소스/증거 해시](result.json) · [기존 입력 비교](../compiler_equivalence.json)
'''
    (HERE/'REPORT.md').write_text(text, encoding='utf8')
    authorization = json.loads((V5/'authorized_gui_fix.json').read_text())
    authorization['files'].update(hashes)
    authorization['nyquist_fix_reason'] = 'User requested Nyquist zone control only in Front Panel; remove duplicate RF editor row while retaining all saved/runtime values.'
    authorization['nyquist_fix_evidence'] = str(HERE/'result.json')
    authorization['nyquist_fix_evidence_sha256'] = sha(HERE/'result.json')
    (V5/'authorized_gui_fix.json').write_text(json.dumps(authorization,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
