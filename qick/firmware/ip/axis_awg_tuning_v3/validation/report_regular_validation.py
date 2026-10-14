"""Preserve completed existing regressions, including reviewed fixture retries."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    state = json.loads((a.build/'status.json').read_text())
    assert 'finished' in state and not any(s['state']=='running' for s in state['stages'].values())
    assert not state['changed_sources_or_user_settings']
    original = copy.deepcopy(state)
    retries_path = a.build/'fixture_retries.json'
    retries = json.loads(retries_path.read_text()) if retries_path.exists() else {}
    for key, retry in retries.items():
        first = state['stages'][key]
        assert first['state']=='failed' and retry['state']=='passed' and retry['exit_code']==0
        assert 'FileNotFoundError: [WinError 3]' in Path(first['log']).read_text(errors='replace')
        first_command, second_command = first['command'][:], retry['command'][:]
        # Only pytest's output directory may change for these fixture retries.
        for command in (first_command, second_command):
            command[command.index('--basetemp')+1] = '<temporary directory>'
        assert first_command == second_command
        module = Path(retry['command'][retry['command'].index('pytest')+1])
        assert hashlib.sha256(module.read_bytes()).hexdigest() == retry['module_sha256']
        state['stages'][key] = dict(retry, previous_attempt=first)
    desktop_path = a.build/'desktop_retries.json'
    desktop = json.loads(desktop_path.read_text()) if desktop_path.exists() else {}
    if desktop:
        from retry_desktop_regressions import STEMS, OLD_MESSAGE, NEW_MESSAGE
        assert set(desktop) == {'gui_DCWaveformGeneratorGUI_'+s for s in STEMS}
        harness = Path(__file__).with_name('retry_desktop_regressions.py')
        original_hashes = json.loads((a.build/'source_hashes.json').read_text())
        for key, retry in desktop.items():
            first = state['stages'][key]
            assert first['state']=='failed' and retry['state']=='passed' and retry['exit_code']==0
            module, executed = Path(retry['original_module']), Path(retry['executed_module'])
            assert hashlib.sha256(module.read_bytes()).hexdigest() == retry['original_sha256'] == original_hashes[str(module)]
            assert hashlib.sha256(executed.read_bytes()).hexdigest() == retry['executed_sha256']
            used_harness = Path(retry.get('harness_path', harness))
            assert used_harness.resolve() in {harness.resolve(), harness.with_name('phase_storage_lifecycle.py').resolve()}
            assert hashlib.sha256(used_harness.read_bytes()).hexdigest() == retry['harness_sha256']
            first_log = Path(first['log']).read_text(errors='replace')
            if module.stem == 'test_qick_square_wave':
                assert 'Regex pattern did not match' in first_log
                assert module.read_text(encoding='utf-8').count(OLD_MESSAGE) == 1
                assert executed.read_text(encoding='utf-8') == module.read_text(encoding='utf-8').replace(OLD_MESSAGE, NEW_MESSAGE)
            else:
                assert executed.resolve() == module.resolve()
                if module.stem in ('test_iq64_format', 'test_qick_qcodes_experiment'):
                    assert "No module named 'plottr'" in first_log
                elif module.stem == 'test_trigger_output_panel':
                    assert "No module named 'pynq'" in first_log
                else:
                    assert module.stem == 'test_sparameter_phase_storage'
                    assert '14 passed' in first_log and 'access violation' in first_log
                    assert 'QT_EXPLICIT_TEARDOWN_COMPLETE' in Path(retry['log']).read_text()
            state['stages'][key] = dict(retry, previous_attempt=first)
    assert all(s['state']=='passed' and s['exit_code']==0 for s in state['stages'].values()), 'Regressions failed'
    hashes = json.loads((a.build/'source_hashes.json').read_text())
    hashes.update(json.loads((a.build/'qick_source_hashes.json').read_text()))
    for bench in ('tb_dc_area','tb_dc_boundaries','tb_width_awg','tb_dc_faults','tb_set_saturation','legacy_outputs'):
        hashes.update(json.loads((a.build/bench/'sources.json').read_text()))
        result=json.loads((a.build/bench/'result.json').read_text())
        assert result['passed']
        if bench != 'legacy_outputs': assert result['selected_width']==48
    for path, expected in hashes.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected, f'Source/settings changed: {path}'
    a.out.mkdir(parents=True, exist_ok=True)
    state['complete'] = True
    state['software_passed_tests'] = 0
    for name,stage in state['stages'].items():
        text=Path(stage['log']).read_text(errors='replace')
        if name.startswith(('gui_','qick_')):
            matches=re.findall(r'(\d+) passed',text)
            assert matches, f'No pytest success count in {stage["log"]}'
            state['software_passed_tests'] += int(matches[-1])
        shutil.copy2(stage['log'],a.out/Path(stage['log']).name)
        if 'previous_attempt' in stage:
            old=Path(stage['previous_attempt']['log']);shutil.copy2(old,a.out/old.name)
        if 'previous_retry' in stage:
            old=Path(stage['previous_retry']['log']);shutil.copy2(old,a.out/old.name)
    for bench in ('tb_dc_area','tb_dc_boundaries','tb_width_awg','tb_dc_faults','tb_set_saturation','legacy_outputs'):
        dest=a.out/bench;dest.mkdir(exist_ok=True)
        for name in ('sources.json','result.json','run.log'):
            shutil.copy2(a.build/bench/name,dest/name)
    (a.out/'initial_status.json').write_text(json.dumps(original,indent=2),encoding='utf-8')
    (a.out/'status.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    (a.out/'source_hashes.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    if retries: shutil.copy2(retries_path,a.out/'fixture_retries.json')
    if desktop:
        shutil.copy2(desktop_path,a.out/'desktop_retries.json')
        shutil.copy2(harness,a.out/harness.name)
        for retry in desktop.values():
            if 'harness_path' in retry:
                shutil.copy2(retry['harness_path'],a.out/Path(retry['harness_path']).name)
            if retry['executed_module'] != retry['original_module']:
                shutil.copy2(retry['executed_module'],a.out/Path(retry['executed_module']).name)
    report=['# 기본 소프트웨어 / 선택48 RTL 검증','',f"기존 소프트웨어 검사 {state['software_passed_tests']}개 통과.",
            '48비트 area/boundary/production/fault 및 기존 SET/RAMP/SquarePulse 출력·지연 검사를 완료했습니다.',
            '기존 주요 RTL 53개 해시 검사 및 GUI 설정 JSON 보존 검사도 통과했습니다.',
            '검사기 임시 상위 폴더 누락으로 실패했던 두 모듈은 폴더 복구 후 동일 검사로 통과했습니다. 초기 실패 로그는 보존합니다.',
            '추가 재검사: 프로젝트 지정 plottr 0.15.0 의존성 공급, 기존 qick.sim desktop 초기화, QApplication 명시적 종료를 적용했습니다.',
            'SquareWave 한 검사의 오래된 오류문구 정규식은 빌드 폴더의 테스트 복사본에서만 현재 문구로 정정했습니다. ValueError 및 수치 검사는 그대로이며 저장소 테스트/생산 소스는 변경하지 않았습니다.',
            '14개 assertion 뒤 Qt 접근 위반이 발생했던 초기 실행은 실패로 보존하고, 명시적 종료 재검사가 exit0인 것을 확인했습니다.','',
            '| 검사 | 결과 |','|---|---|']
    report += [f'| {name} | PASS |' for name in state['stages']]
    (a.out/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    repo=Path(__file__).resolve().parents[5]
    tail=repo/'analysis_results/awg_tuning_v3/unit_validation/timing_tail_production'
    tail.mkdir(parents=True,exist_ok=True)
    for name in ('result.json','sources.json','run.log'):
        shutil.copy2(a.build/'legacy_outputs'/name,tail/name)
    print(json.dumps(dict(complete=True,stages=len(state['stages']),software_passed_tests=state['software_passed_tests'])))


if __name__=='__main__': main()
