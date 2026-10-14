"""Read-only evidence audit; never reruns simulations/builds or rewrites signoff."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
V3=OUT.parent/'awg_tuning_v3'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compare(mapping):
    differences=[]
    for name,digest in mapping.items():
        path=Path(name)
        if not path.is_absolute():path=ROOT/path
        if not path.exists() or sha(path)!=digest:differences.append(str(path))
    return dict(files=len(mapping),matches=len(mapping)-len(differences),differences=differences)


def main():
    results={}
    regular=read(V3/'regular_validation/status.json')
    assert regular['complete'] and regular['software_passed_tests']==986
    assert not regular['changed_sources_or_user_settings']
    for value in regular['stages'].values():
        assert value['state']=='passed' and value['exit_code']==0
        assert Path(value['log']).exists()
    results['v3_regular']=dict(stages_passed=len(regular['stages']),tests_passed=986,
        recorded_logs_present=True,source_comparison=compare(read(V3/'regular_validation/source_hashes.json')),
        current_v4_full_986_suite_rerun=False)
    units={}
    for bench in ('tb_dc_area','tb_dc_boundaries','tb_width_awg','tb_dc_faults','tb_set_saturation','legacy_outputs'):
        folder=V3/'regular_validation'/bench
        result=read(folder/'result.json');assert result['passed']
        source=compare(read(folder/'sources.json'));assert not source['differences']
        log=Path(regular['stages'][bench]['log'])
        units[bench]=dict(passed=True,result_sha256=sha(folder/'result.json'),sources=source,
                          log=str(log),log_sha256=sha(log),execution_generation='v3; unchanged RTL')
    results['v3_basic_rtl']=units
    rc=read(V3/'selected48_validation/width_results.json')
    assert rc['complete'] and rc['selected_width']==48 and not rc['comparison_performed']
    width=rc['widths']['48'];assert width['completed_shots']==200 and width['overflow_points']==0
    assert all(width[k]==0 for k in ('max_residual_effective_code_samples','max_cumulative_effective_code_samples',
                                      'max_collection_error_without_overflow','final_cumulative_effective_code_samples'))
    sources={r['path']:r['sha256'] for r in read(V3/'selected48_validation/rtl_source_manifest.json')['repository_sources']}
    source=compare(sources);assert not source['differences']
    assert sha(V3/'selected48_validation/width_48.csv')==width['csv_sha256']
    results['v3_continuous_rc']=dict(result=rc,sources=source,csv_hash_matched=True)
    old_system=read(V3/'system_validation/status.json')
    assert old_system['complete'] and len(old_system['cases'])==4
    for case in old_system['cases'].values():assert case['state']=='passed'
    results['v3_system']=dict(cases_passed=4,case_names=list(old_system['cases']),
                             v4_axis_reversal_stability_full_rtl_rerun=False)
    protected=compare(read(OUT/'protected_v3_sources.json'));assert not protected['differences']
    results['v4_protected']=protected
    unit=read(OUT/'unit/result.json');assert unit['passed'] and unit['exit_code']==0
    source=compare(read(OUT/'unit/source_hashes.json'));assert not source['differences']
    results['v4_sum_unit']=dict(result=unit,sources=source)
    gate=read(OUT/'prebuild_gate.json')
    historical=compare(gate['source_hashes'])
    final=read(OUT/'final_integration_manifest.json')
    expected={x['path'] for x in final['postpublication_changes']}
    assert set(historical['differences'])==expected
    current=compare(final['current_source_hashes']);assert not current['differences']
    evidence=compare(gate['evidence_hashes']);assert not evidence['differences']
    additional=compare(final['additional_evidence']);assert not additional['differences']
    system=read(OUT/'v4_final2_status.json');assert system['complete'] and len(system['cases'])==5
    for case in system['cases'].values():
        assert case['state']=='passed' and case['exit_code']==0
    suites=list(ET.parse(OUT/'postpublish_software.xml').iter('testsuite'))
    assert sum(int(s.get('tests',0)) for s in suites)==274
    assert all(int(s.get(k,0))==0 for s in suites for k in ('failures','errors','skipped'))
    modules=Counter(t.get('classname') for t in ET.parse(OUT/'postpublish_software.xml').iter('testcase'))
    replay=read(OUT/'postpublish_program_equivalence.json');assert replay['complete'] and len(replay['cases'])==5
    for case in replay['cases']:
        assert case['gui_proof']['pmem_equal'] and case['gui_proof']['dmem_equal']
        for item in case['files'].values():assert sha(item['original'])==sha(item['current'])==item['sha256']
    results['v4_system_and_software']=dict(rtl_cases_passed=5,software_tests_passed=274,
        software_modules=dict(modules),gui_replay_cases=5,current_sources=current,
        original_evidence=evidence,postpublication_evidence=additional,
        preserved_prebuild_source_differences=historical['differences'])
    ten=read(OUT/'hold10us_gui_rtl/status.json');assert ten['complete'] and len(ten['cases'])==2
    ten_evidence=compare(ten['evidence_sha256']);assert not ten_evidence['differences']
    results['v4_hold10us']=dict(cases_passed=2,evidence=ten_evidence,
        finding=ten['finding'],physical_samples=sum(p['physical_sample_checks'] for c in ten['cases'].values()
            for p in c['result']['output_sum']['pairs']))
    project=ROOT/'qick/firmware/projects/qstl_awg_v4'
    manifest=read(project/'build_manifest.json');assert manifest['timing']['timing_closed']=='YES'
    for artifact in manifest['artifacts']:assert sha(artifact['path'])==artifact['sha256']
    with zipfile.ZipFile(project/'bitstream.xsa') as archive:
        assert archive.read(manifest['xsa_members']['bit'])==(project/'bitstream.bit').read_bytes()
        assert archive.read(manifest['xsa_members']['hwh'])==(project/'bitstream.hwh').read_bytes()
    for name in ('timing.xdc','ios.xdc','bd_2023-1.tcl'):
        assert (project/name).read_bytes()==(project.parent/'qstl_awg_v3'/name).read_bytes()
    workflow=read(OUT/'workflow_status.json');assert workflow['complete'] and workflow['exit_code']==0
    results['v4_firmware']=dict(artifacts_verified=3,xsa_members_identical=True,timing=manifest['timing'],
        bus_skew_met=final['bus_skew_constraints_met'],minimum_bus_skew_slack_ns=final['minimum_bus_skew_slack_ns'],
        unchanged_v3_constraints=True)
    branches={str(p):subprocess.check_output(['git','-C',str(p),'branch','--show-current'],text=True).strip()
              for p in (ROOT,ROOT.parent/'PulseGenerator')}
    assert set(branches.values())=={'awg_tuning_v4'}
    output=dict(audit_complete=True,verified_utc=datetime.now(timezone.utc).isoformat(),branches=branches,
        all_basic_tests_rerun_on_current_v4=False,results=results,
        gaps=['The full 986-test v3 software suite has not been rerun on current v4; 274 relevant tests passed.',
              'Axis-reversal/Stability full RTL cases are v3 evidence, not a new v4 end-to-end run.',
              'The ideal GUI preview omits the existing one-clock guard after each RAMP.'],
        excluded=['Analog board measurement','ADC/FIR numeric response','Unimplemented RC partition/checkpoint runner'],
        simulations_started=0,synthesis_started=0)
    (OUT/'checklist_audit.json').write_text(json.dumps(output,indent=2),encoding='utf8')
    print(json.dumps(dict(audit_complete=True,v3_stages=73,v3_software=986,v3_rtl_groups=6,
                         continuous_rc_shots=200,v4_software=274,v4_rtl_cases=5,extra_hold_cases=2,
                         protected_files=protected['files'],all_current_v4_basics_rerun=False)))


if __name__=='__main__':main()
