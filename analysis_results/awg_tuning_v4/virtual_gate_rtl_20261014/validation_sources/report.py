"""Report actual current-task results; retain unresolved failures as failures."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET
from run_case import EVIDENCE,ROOT,folder
from cases import CASES,MATRIX

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def audit_case(path, entry):
    """Require process success and recheck the exact compiled input/source."""
    issues=[]
    if entry.get('rtl',{}).get('exit_code')!=0:issues.append('RTL process did not exit zero')
    prepared=json.loads((path/'prepared.json').read_text())
    files=[Path(s) for s in re.findall(r'^sv\s+\S+\s+"([^"]+)"', (path/'sources.prj').read_text(),re.M)]
    assert files, path
    fingerprint=hashlib.sha256(b''.join(p.read_bytes() for p in files+[path/'pmem.hex',path/'dmem.txt'])).hexdigest()
    if fingerprint!=prepared['fingerprint']:issues.append('Prepared RTL/input fingerprint differs')
    changed=[p for p,h in prepared['program_source_hashes'].items() if not Path(p).is_file() or sha(Path(p))!=h]
    if changed:issues.append('GUI/compiler source differs')
    match=json.loads((path/'gui_widget_match.json').read_text())
    if not match['pmem_equal'] or not match['dmem_equal']:issues.append('GUI/export byte mismatch')
    if (path/'gui_widget_pmem.hex').read_bytes()!=(path/'pmem.hex').read_bytes():issues.append('Saved GUI PMEM differs from RTL PMEM')
    if sha(path/'gui_widget_pmem.hex')!=match['pmem_sha256']:issues.append('GUI PMEM evidence hash differs')
    oracle=json.loads((path/'independent_matrix_oracle.json').read_text())
    if not oracle['passed'] or oracle['matrix']!=MATRIX:issues.append('Independent matrix oracle failed')
    log=(path/'xsim.log').read_text()
    if 'RTL COMPLETE' not in log or re.search(r'^ERROR:|^Fatal:',log,re.M):issues.append('Simulator completion/error log invalid')
    return dict(passed=not issues,issues=issues,prepared_fingerprint=fingerprint,
        checked_program_sources=len(prepared['program_source_hashes']),changed_program_sources=changed,
        rtl_exit_code=entry.get('rtl',{}).get('exit_code'),pmem_sha256=sha(path/'pmem.hex'),dmem_sha256=sha(path/'dmem.txt'))

def main():
    initial=json.loads((EVIDENCE/'status.json').read_text())
    additional=json.loads((EVIDENCE/'additional_status.json').read_text())
    cases=dict(initial['cases'])
    for name,entry in additional['cases'].items():
        if name.endswith('_retry1') and name!='compensation_off_retry1':cases[name[:-7]]=entry
        elif not name.endswith('_retry1'):cases[name]=entry
    off=folder('compensation_off').with_name(folder('compensation_off').name.replace('compensation_off_output_sum','compensation_off_retry2_output_sum'))
    off_state=json.loads((EVIDENCE/'off_status.json').read_text())
    if off_state.get('finished_utc'):
        cases['compensation_off']=dict(folder=str(off),state='passed' if off_state['complete'] else 'failed',retry='retry2',rtl=off_state.get('rtl',{}))
    entries={}
    for name,entry in cases.items():
        path=Path(entry['folder']);result_path=path/'result.json'
        passed=entry['state']=='passed' and result_path.exists()
        result=json.loads(result_path.read_text()) if passed else None
        passed=passed and result['validation_status']=='passed'
        audit=audit_case(path,entry) if passed else None
        passed=passed and audit['passed']
        target=EVIDENCE/'cases'/name;target.mkdir(parents=True,exist_ok=True)
        hashes={}
        if passed:
            for p in path.iterdir():
                if p.is_file() and p.suffix in ('.json','.hex','.sv','.v','.py','.asm','.txt','.log','.csv','.png','.prj'):
                    if p.stat().st_size < 5_000_000:
                        shutil.copy2(p,target/p.name);hashes[p.name]=sha(p)
        entries[name]=dict(passed=passed,state=entry['state'],folder=str(path),result=result,audit=audit,evidence_sha256=hashes)
    tree=ET.parse(EVIDENCE/'software_detailed.xml')
    tests=[]
    for t in tree.findall('.//testcase'):
        failure=t.find('failure');error=t.find('error')
        issue=failure if failure is not None else error
        tests.append(dict(name=t.attrib['name'],passed=issue is None,
            error=None if issue is None else issue.attrib.get('message',issue.text)))
    before=json.loads((EVIDENCE/'production_hashes_before.json').read_text())
    changed=[p for p,h in before.items() if not Path(p).is_file() or sha(Path(p))!=h]
    protected=json.loads((EVIDENCE.parent/'protected_v3_sources.json').read_text())
    protected_changed=[p for p,h in protected.items() if sha(ROOT/p)!=h]
    finished=all(bool(s.get('finished_utc')) for s in (initial,additional,off_state))
    totals=dict(rtl_cases=len(entries),rtl_passed=sum(e['passed'] for e in entries.values()),
        software_tests=len(tests),software_passed=sum(t['passed'] for t in tests),
        software_failed=sum(not t['passed'] for t in tests),protected_files=len(protected),
        points=sum(e['result']['points'] for e in entries.values() if e['passed']),
        shots=sum(e['result']['points']*e['result']['repetitions'] for e in entries.values() if e['passed']),
        commands=sum(e['result']['commands'] for e in entries.values() if e['passed']),
        summed_output_samples=sum(int(row[1]) for e in entries.values() if e['passed'] for row in e['result']['output_sum']['sample_oracles']))
    results=dict(complete=finished and all(e['passed'] for e in entries.values()) and all(t['passed'] for t in tests) and not changed and not protected_changed,
        controllers_finished=finished,execution_complete=finished,
        generated_utc=datetime.now(timezone.utc).isoformat(),
        totals=totals,production_changes=changed,protected_changes=protected_changed,
        cases=entries,software=tests,matrix=MATRIX,no_board_or_synthesis=True,
        initial_harness_failures_preserved=['ramp_fixed_time','ramp_fixed_voltage_descending','compensation_off','compensation_off_retry1'],
        initial_software_harness_errors_preserved=['axis_kind ramp_duration','CircuitExecution has no timeline attribute'])
    (EVIDENCE/'results.json').write_text(json.dumps(results,indent=2),encoding='utf8')
    snapshot=EVIDENCE/'validation_sources';snapshot.mkdir(exist_ok=True)
    source_manifest={}
    for source in Path(__file__).parent.iterdir():
        if source.is_file():
            shutil.copy2(source,snapshot/source.name);source_manifest[source.name]=sha(source)
    (snapshot/'manifest.json').write_text(json.dumps(source_manifest,indent=2),encoding='utf8')
    lines=['# Virtual gate × parameter sweep — 현재 v4 추가 검증','',
        f"실제 RTL **{totals['rtl_passed']}/{totals['rtl_cases']} PASS**, GUI/compiler **{totals['software_passed']}/{totals['software_tests']} PASS**, **{totals['software_failed']} 실패**입니다. 전체 PASS로 표시하지 않습니다.",
        '',f"새 RTL 실행은 총 {totals['points']}점·{totals['shots']}회, 명령 {totals['commands']:,}개, 세 합산 DAC의 lane 샘플 {totals['summed_output_samples']:,}개를 검사했습니다. 각 통과 케이스의 exit 0, GUI PMEM/DMEM 일치, 준비된 RTL/입력 fingerprint, GUI/compiler 159개 소스 해시를 다시 확인했습니다.",
        '', '## 입력과 검사 범위','',
        '실제 MainWindow 행렬·전압/HOLD/RAMP 설정창에 키보드 입력하고 Run Experiment 컴파일 PMEM/DMEM을 export와 바이트 비교했습니다. 비대칭 3×3 C의 모든 출력이 결합되며 Physical=C×Virtual, full scale 800/400/800mV입니다. 독립 C@V/정수 증분 계산, 모든 tProcessor 명령값·시각, 세 raw AWG와 세 IIR 모든 lane, DC 잔여 면적/reset 또는 RC/OFF bypass, 세 합산 출력의 합산식·반올림·2클록 파이프라인을 검사했습니다. RF 주파수/진폭 수치 검사는 RF1, 나머지 RF2/3은 고정 펄스의 시작/폭과 합산을 검사했습니다. 이번 작은 전압의 조합에서 clipping 경계 발생을 별도로 요구하지 않으며 기존 합산 단위 경계시험과 구분합니다.',
        '', '각 케이스는 작은 직교 조합이며 모든 파라미터×모드×방향의 전체 곱을 망라했다고 주장하지 않습니다. 이전 100×2 회귀, 48비트 RC200회나 전체 timing을 이번 추가 실행으로 다시 센 것이 아닙니다.',
        '', '| 실제 GUI→RTL 케이스 | 상태 | 점×반복 | 명령 비교 |','|---|---|---:|---:|']
    for name,e in entries.items():
        r=e['result'] or {}
        lines.append(f"| {name} | {'PASS' if e['passed'] else e['state']} | {str(r.get('points','—'))+' × '+str(r.get('repetitions','—'))} | {r.get('commands','—')} |")
    lines+=['','## 남은 실패 / 제품 범위','',
        '- **UDD N=2, τ=0.2µs:** 실제 GUI의 outer software sweep 좌표를 production compiler에 넣었을 때 공유 tProcessor 포트0의 AWG 명령13클록/RF 명령15클록이 2클록 간격이라 필수3클록 조건을 위반하여 거부됐습니다. guard가 실패를 숨긴 것이 아니라 이 설정이 실행 불가인 것입니다. 이 조건의 RTL 실행은 하지 않았습니다. N=1의 두 τ와 N=2/τ=0.4µs는 별도 compiler 검사를 수행했습니다.',
        '- **Quantum Circuit RF Loop n=1,3:** v4 합산으로 AWG 출력 latency가 18클록인데 circuit RF profile 판정은 v3의 16클록 조건을 요구하여 unknown latency로 거부됩니다. 임의 latency override나 생산 코드 수정으로 통과시키지 않았습니다.',
        '- **Quantum Circuit의 Virtual matrix:** AWG Tuning의 행렬을 circuit 전압 계산에 적용하는 경로가 없습니다. n=0의 실제 GUI→compiler 검사에서는 AWG 설정에 저장된 비단위행렬과 별개로 circuit sequence가 단위행렬인 것을 확인했습니다. Quantum matrix+loop RTL PASS라고 표시하지 않습니다.',
        '- **RF power/calibration:** 합산 DAC에서는 기존 RF 전용 커넥터 보정을 사용할 수 없도록 막혀 있습니다. 세 RF 출력×보정/보정 sweep 6개 GUI spec→production compiler 거부 검사가 통과했습니다. 정상 출력 시험 PASS와 다릅니다.',
        '', '## 초기 실패와 재검사','',
        'RAMP의 실제 axis_kind 이름과 OFF의 초기 RC reset 정책을 새 helper가 잘못 가정한 초기 실패는 원본 로그/소스를 보존했습니다. 생산 코드나 허용오차를 바꾸지 않고 검증 helper만 수정했으며 별도 retry 폴더 결과를 사용합니다. GUI/compiler 초기 Quantum n=0의 반환 객체 접근 오류도 원본을 보존하고 실제 document의 timeline을 검사하도록 수정했습니다. 나머지 실제 compiler 거부 3건은 실패로 유지합니다.',
        '', '기본/추가 controller의 finished_with_failures 및 exit 1은 초기 helper 실패를 보존한 값입니다. 최종 채택한 RTL 21회는 각각 exit 0입니다. results.json의 execution_complete는 실행 종료, complete는 전체 통과를 뜻하므로 현재 각각 true/false입니다. 추가 장시간 재실행이나 제품 수정으로 실패를 덮지 않았습니다.',
        '', '## 보존과 한계','',
        f"보호 {len(protected)}파일 변경 {len(protected_changed)}, 검증 전후 생산 소스/사용자 JSON/펌웨어 변경 {len(changed)}개. 새 합성·commit/push·SSH 연결·보드 출력·펌웨어 업로드는 수행하지 않았습니다.",
        '기존 정수 SET sweep add/rewind 양자화 오차를 해결했다는 의미가 아닙니다. AWG IIR 뒤 DDS 면적·clipping은 기존 DC 면적 보상 대상이 아닙니다. 보드 아날로그 및 ADC/FIR 산술 검증은 포함하지 않습니다.',
        '', '[상세 결과/해시](results.json) · [초기 실행](status.json) · [추가 실행](additional_status.json) · [GUI/compiler 상세 실패](software_detailed.log) · [실패 시각·지연 진단](failure_diagnostics.json)',
        '', '[실제 RTL 합산 파형](virtual_matrix_rtl_alignment.png) · [세 물리 출력 목표값](virtual_matrix_physical_targets.png)',
        '']
    (EVIDENCE/'REPORT.md').write_text('\n'.join(lines),encoding='utf8')
    print(json.dumps(totals),flush=True)

if __name__=='__main__':main()
