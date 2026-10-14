"""Report fresh v4 results, keeping initial failed attempts and retries explicit."""
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=Path('F:/Vivado_Output/a4reg1')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))


def main():
    state=read(HERE/'status.json')
    basic=read(BASE/'status.json')
    assert 'finished' in basic and not basic['changed_sources_or_user_settings']
    hashes=read(HERE/'source_hashes_before.json')
    changed=[p for p,h in hashes.items() if not Path(p).is_file() or sha(p)!=h]
    desktop=read(HERE/'desktop_retries.json')
    rc=read(HERE/'rc_gui_teardown_retry.json')
    retries=dict(desktop)
    retries['gui_DCWaveformGeneratorGUI_test_rc_precompensation']=dict(
        module=str(ROOT.parent/'PulseGenerator/DCWaveformGeneratorGUI/test_rc_precompensation.py'),
        module_sha256=rc['test_sha256'].lower(),
        harness=str(ROOT/'qick/firmware/ip/axis_awg_tuning_v3/validation'/rc['harness']),
        harness_sha256=rc['harness_sha256'].lower(), exit_code=rc['exit_code'],
        log=str(HERE/rc['log']))
    software={}
    total=0
    for name,item in basic['stages'].items():
        if not name.startswith(('gui_','qick_')):continue
        selected=item
        if item['state']!='passed':
            assert name in retries, 'Unreviewed failure: '+name
            selected=retries[name]
            assert selected['exit_code']==0
            assert sha(selected['module'])==selected['module_sha256']
            assert sha(selected['harness'])==selected['harness_sha256']
            if 'rc_precompensation' in name or 'phase_storage' in name:
                assert 'QT_EXPLICIT_TEARDOWN_COMPLETE' in Path(selected['log']).read_text()
        log=Path(selected['log']).read_text(errors='replace')
        counts=re.findall(r'(\d+) passed',log)
        assert counts and not re.search(r'\d+ failed|Windows fatal exception',log)
        count=int(counts[-1]);total+=count
        software[name]=dict(tests=count,exit_code=selected['exit_code'],log=selected['log'],
            initial_attempt=item,reviewed_retry=selected if selected is not item else None)
    units={}
    for name in ('tb_dc_area','tb_dc_boundaries','tb_width_awg','tb_dc_faults','tb_set_saturation','legacy_outputs'):
        assert basic['stages'][name]['exit_code']==0
        result=read(BASE/name/'result.json'); assert result['passed']
        sources=read(BASE/name/'sources.json')
        assert all(sha(p)==h for p,h in sources.items())
        dest=HERE/'basic_rtl'/name;dest.mkdir(parents=True,exist_ok=True)
        for f in ('result.json','sources.json','run.log'):shutil.copy2(BASE/name/f,dest/f)
        units[name]=result
    basic_out=HERE/'software';basic_out.mkdir(exist_ok=True)
    for name,item in software.items():
        shutil.copy2(item['initial_attempt']['log'],basic_out/(name+'.initial.log'))
        if item['reviewed_retry']:shutil.copy2(item['log'],basic_out/(name+'.retry.log'))
    (basic_out/'results.json').write_text(json.dumps(software,indent=2))
    shutil.copy2(BASE/'status.json',HERE/'regular_initial_status.json')
    unit=read('F:/Vivado_Output/a4reg_sum1/result.json')
    assert unit['passed']
    for p,h in read('F:/Vivado_Output/a4reg_sum1/source_hashes.json').items():assert sha(p)==h
    unit_dest=HERE/'output_sum_unit';unit_dest.mkdir(exist_ok=True)
    for f in ('result.json','source_hashes.json','run.log'):shutil.copy2(Path('F:/Vivado_Output/a4reg_sum1')/f,unit_dest/f)
    junit=ET.parse(HERE/'software_additional.xml').getroot()
    suites=list(junit.iter('testsuite'))
    assert all(int(s.get(k,0))==0 for s in suites for k in ('failures','errors','skipped'))
    extra=sum(int(s.get('tests',0)) for s in suites)
    assert state['stages']['software_additional']['exit_code']==0
    cases={}
    for name,item in state['cases'].items():
        entry=dict(state=item['state'],folder=item['folder'])
        if item['state']=='passed':
            folder=Path(item['folder']); result=read(folder/'result.json')
            assert result['validation_status']=='passed'
            assert result['command_value_mismatches']==result['command_timing_mismatches']==0
            files=[Path(p) for p in re.findall(r'^sv xil_defaultlib "([^"]+)"',(folder/'sources.prj').read_text(),re.M)]
            fingerprint=hashlib.sha256(b''.join(p.read_bytes() for p in files+[folder/'pmem.hex',folder/'dmem.txt'])).hexdigest()
            assert fingerprint==read(folder/'prepared.json')['fingerprint']
            assert all(sha(p)==h for p,h in read(folder/'prepared.json')['program_source_hashes'].items())
            if name!='stability':
                match=read(folder/'gui_widget_match.json');assert match['pmem_equal'] and match['dmem_equal']
            entry.update(points=result['points'],repetitions=result['repetitions'],
                checks=result['output_sum']['sample_oracles'],result_sha256=sha(folder/'result.json'),
                input_fingerprint=fingerprint)
        cases[name]=entry
    rcpath=HERE/'selected48/width_results.json'
    rc_result=read(rcpath) if rcpath.exists() else None
    rc_done=bool(rc_result and rc_result['complete'] and state['stages'].get('rc48_report',{}).get('exit_code')==0)
    complete=(not changed and len(cases)==9 and all(c['state']=='passed' for c in cases.values())
              and rc_done and all(s['state']=='passed' for s in state['stages'].values()))
    result=dict(complete=complete,verified_utc=datetime.now(timezone.utc).isoformat(),
        version='awg_tuning_v4',fresh_rerun=True,software_modules=len(software),software_tests=total,
        additional_tests=extra,software_total=total+extra,reviewed_initial_failures=list(retries),
        basic_rtl=units,output_sum_unit=unit,cases=cases,rc48=rc_result,
        changed_sources_settings_or_firmware=changed,synthesis_repeated=False)
    (HERE/'results.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    lines=['# 현재 v4 전체 기본 회귀 재검증','',
        '**전체 완료: '+('PASS**' if complete else '아직 미완료**'),'',
        f'- 현재 v4 기본 소프트웨어 {len(software)}모듈 / {total}개 PASS, 추가 연동·증거 검사 {extra}개 PASS.',
        '- 기본 RTL 6묶음과 합산 단위 RTL 1,114,160 샘플을 현재 소스로 새로 실행해 PASS.',
        '- 초기 3개 실패는 원본 로그에 보존: RC/phase-storage의 Qt 종료 접근 위반 2건, trigger-panel의 desktop PYNQ 초기화 누락 1건.',
        '- 동일 원본 테스트/생산 소스를 유지하고 명시적인 Qt 종료 또는 기존 qick.sim 초기화를 적용한 재실행은 모두 exit 0.',
        '- 32/64비트 비교, 새 합성, 펌웨어 교체는 수행하지 않았습니다.',
        f'- 생산 소스·사용자 설정·펌웨어 해시 변경: {len(changed)}개.','',
        '| 시스템 조건 | 상태 |','|---|---|']
    lines += [f'| {name} | {item["state"]} |' for name,item in cases.items()]
    lines += ['', 'Stability는 현재 GUI가 사용하는 public Stability builder → 실제 RTL 시험입니다. RF/DDR가 없는 기존 기본 조건을 유지하며 v4 합산단을 포함합니다. 다른 8조건은 실제 MainWindow 입력/Run Experiment 컴파일과 PMEM/DMEM 일치를 확인합니다.',
        '', '48비트 연속 RC 200회: '+('PASS' if rc_done else '진행/대기 중')+'.',
        '', '현재 RTL 변경 후 전체 기본 검증 재실행 원칙은 [통합 체크리스트](../VALIDATION_CHECKLIST.md)에 있습니다.',
        '원본 실행 상태는 [status.json](status.json), 결과 대조는 [results.json](results.json), 기본 회귀 최초 실행은 [regular_initial_status.json](regular_initial_status.json)입니다.',
        '', '보드 아날로그 측정과 ADC/FIR 산술 응답은 이 검증 범위가 아닙니다. AWG IIR 뒤 DDS 합산 면적·clipping은 기존 DC 면적 보상에 포함되지 않습니다.']
    (HERE/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('complete','software_modules','software_total','changed_sources_settings_or_firmware')}))


if __name__=='__main__':main()
