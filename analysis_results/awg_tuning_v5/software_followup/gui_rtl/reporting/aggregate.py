"""Strictly aggregate completed v5 followup evidence without rewriting original runs."""
import hashlib,json,re,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;E=HERE.parent

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def evidence(p):return dict(path=str(p),sha256=sha(p))

def main():
    suite=read(E/'suite2_status.json');retry=read(HERE/'hold_fixed_voltage_retry_status.json')
    assert suite['stage']=='failed' and not suite['complete']
    assert [n for n,c in suite['cases'].items() if c['state']!='passed']==['hold_fixed_voltage']
    assert retry['complete'] and retry['exit_code']==0
    failure=E/'suite2_hold_fixed_voltage.run.log';assert 'source changed after preparation' in failure.read_text() and 'xsim' not in failure.read_text()
    old=Path(suite['cases']['hold_fixed_voltage']['folder'])
    fixed=old.with_name(old.name.replace('v5_post_hold_fixed_voltage','v5_post_hold_fixed_voltage_retry'))
    previous=read(old/'prepared.json')['program_source_hashes']
    changed=[p for p,h in previous.items() if sha(p)!=h]
    assert changed==[str(E/'raw_same_timestamp.py')],changed
    identical={n:sha(old/n)==sha(fixed/n) for n in ('pmem.hex','dmem.txt','gui_input.json')};assert all(identical.values()),identical
    coarse=[]
    for name,case in suite['cases'].items():
        folder=fixed if name=='hold_fixed_voltage' else Path(case['folder'])
        if name!='hold_fixed_voltage':assert case['exit_code']==0
        result=read(folder/'result.json');assert result['validation_status']=='passed'
        assert result['command_value_mismatches']==result['command_timing_mismatches']==0
        prepared=read(folder/'prepared.json')
        assert all(sha(p)==h for p,h in prepared['program_source_hashes'].items()),name
        sums=result['output_sum'];assert len(sums['pairs'])==3 and sums['awg_delay_cycles']==13
        assert all(m['requested_timing_error_cycles']==0 for pair in sums['pairs'] for m in pair['measurements'])
        match=read(folder/'gui_widget_match.json');assert match['pmem_equal'] and match['dmem_equal'] and match['gui_sequence_unmodified'] and match['sequence_mutations']==[]
        coarse.append(dict(case=name,folder=str(folder),result=evidence(folder/'result.json'),gui_widget_match=evidence(folder/'gui_widget_match.json'),
            points=result['points'],repetitions=result['repetitions'],shots=result['points']*result['repetitions'],
            pairs=len(sums['pairs']),physical_sample_checks=sum(p['physical_sample_checks'] for p in sums['pairs']),
            command_value_errors=0,command_timing_errors=0,explicit_rf_offset_us=sums['explicit_rf_offset_us'],
            hardware_area_results=result['hardware_area_results'],ddr_capture_results=result['ddr_capture_results']))
    prepared=read(E/'fine/prepared.json');assert all(sha(p)==h for p,h in prepared['source_hashes'].items())
    assert all(sha(p)==h for p,h in prepared['template_sources'].items())
    fine=[]
    for state_name in ('matrix_a_status.json','matrix_b_status.json'):
        state=read(E/'fine'/state_name);assert state['complete'] and state['stage']=='passed'
        for result in state['cases']:
            assert result['passed'];folder=Path(result['folder'])
            case=next(c for c in prepared['cases'] if c['name']==result['name'])
            assert all(sha(folder/n)==h for n,h in case['inputs'].items())
            result_path=folder/'result.json';assert read(result_path)==result
            oracle_rows=re.findall(r'OUTPUT_SUM_RESULT suffix=(\d+) samples=(\d+)',(folder/'run_console.log').read_text())
            assert len(oracle_rows)==3 and {int(a) for a,b in oracle_rows}=={4,5,6}
            fine.append(dict(case=case['name'],points=case['points'],repetitions=case['repetitions'],result=evidence(result_path),
                rf_bursts=sum(len(c['bursts']) for c in result['checks']),sum_lane_samples=sum(int(b) for a,b in oracle_rows),command_value_errors=result['command_value_errors'],
                command_timing_errors=result['command_timing_errors'],sum_lane_oracle_errors=result['sum_lane_oracle_errors']))
    assert len(fine)==5 and all(c['command_value_errors']==c['command_timing_errors']==c['sum_lane_oracle_errors']==0 for c in fine)
    audit_path=HERE/'fine_input_provenance_audit.json';audit=read(audit_path)
    assert audit['passed'] and audit['request_timing_preserved'] and audit['quantization_differences']==[] and len(audit['cases'])==5
    assert all(sha(p)==h for p,h in audit['source_hashes'].items())
    zero_path=E/'zero_offset/result.json';zero=read(zero_path)
    assert zero['passed'] and len(zero['cases'])==8 and all(c['expected_rejection'] and not c['guard_modified'] for c in zero['cases'])
    raw_state=read(E/'fine/raw_status.json');assert raw_state['complete'] and raw_state['stage']=='passed'
    raw_path=Path(prepared['build'])/'raw_same_timestamp/result.json';raw=read(raw_path)
    assert raw['passed'] and raw['diagnostic_only'] and not raw['simultaneous_output_supported'] and raw['sum_lane_oracle_errors']==0
    assert len(raw['measurements'])==6 and all(m['command_lateness_cycles']==[0,3] for m in raw['measurements'])
    result=dict(complete=True,executed_supported_cases_passed=True,exact_zero_offset_supported=False,
        finished=time.strftime('%Y-%m-%dT%H:%M:%S%z'),coarse=coarse,fine=fine,
        coarse_shots=sum(c['shots'] for c in coarse),coarse_pair_shots=sum(c['shots']*c['pairs'] for c in coarse),
        physical_sample_checks=sum(c['physical_sample_checks'] for c in coarse),fine_rf_bursts=sum(c['rf_bursts'] for c in fine),fine_sum_lane_samples=sum(c['sum_lane_samples'] for c in fine),
        negative_gui_cases=8,zero_offset=evidence(zero_path),raw_diagnostic=evidence(raw_path),fine_parameter_audit=evidence(audit_path),
        raw_measurements=raw['measurements'],production_source_hashes=prepared['source_hashes'],
        reviewed_retries=[dict(reason='First suite preparation lacked wrapper_path.txt. Fresh suite2 prepared all cases using the existing wrapper; original failure retained.',original=evidence(E/'suite_status.json'),log=evidence(E/'hold1.prepare.log')),
            dict(reason=retry['reason'],original=evidence(E/'suite2_status.json'),log=evidence(failure),
                 modified_validation_only_files=changed,retry=evidence(HERE/'hold_fixed_voltage_retry_status.json'),
                 original_vs_retry_input_hashes_equal=identical)],
        audit_attempts=[dict(path=str(HERE/'fine_audit.log'),outcome='process termination -1073740791; empty log, cause not proven'),
            dict(path=str(HERE/'fine_audit_retry.log'),outcome='checker incorrectly used round-to-nearest; production uses ceil with integer nearness. Original failure preserved.'),
            dict(path=str(HERE/'fine_audit_v2.log'),outcome='exit0; exact fields, documented GUI precision bound, actual quantization, byte-identical recompile PASS')],
        limitations=['Zero-offset HOLD SET + RF on a shared port is unsupported; native latency equality does not remove dispatch serialization.',
            '10us first/second HOLD tests request explicit +100ns offset and 9.9us width relative to the actual HOLD anchor, not an ideal absolute RAMP timeline.',
            'Fine RF duration step 0.208333ns; start scheduling remains 3.333333ns fabric grid.',
            'Physical component starts in diagnostic are inferred from directly observed pre-sum edges and verified downstream latency; actual summed output lanes are independently checked.',
            'No board analog measurement, ADC/FIR arithmetic verification, synthesis, upload or deployment. IIR-after DDS area/clipping is outside existing DC area compensation.'])
    out=HERE/'result.json';assert not out.exists();out.write_text(json.dumps(result,indent=2))
    lines=['# Fresh v5 GUI to RTL followup validation','',
        'Supported test cases passed. Exact zero-offset HOLD SET + RF remains unsupported on the existing shared tProcessor port. No production spacing guard was relaxed.','',
        '| Group | Fresh execution result |','|---|---|',
        f"| Actual MainWindow → PMEM/DMEM → v5 RTL | 7 cases, {result['coarse_shots']} shots × 3 AWG/RF pairs; command and timing mismatches 0 |",
        f"| Final digital output oracle | {result['physical_sample_checks']:,} lane/sample checks; errors 0 |",
        f"| Fine actual GUI → AXI/AXIS BRAM load → SG-v6 → v5 sum | 5 cases, {result['fine_rf_bursts']:,} RF bursts; sample widths, gain/frequency/phase, outside-window zero, command/timing and sum-lane checks PASS |",
        '| Zero-offset real GUI | 8 expected rejections; unchanged guard |',
        '| Raw identical timestamp diagnostic | All 3 ports × both orders: second command 3 clocks late; inferred component skew ±3 clocks = ±10ns |',
        '| Additional source/input audit | 5 cases: all requested resolved fields, exact PMEM/DMEM/envelope recompile, actual HWH/full configured soccfg/source hashes PASS; quantized request/GUI delay differences 0 |','',
        'The seven supported cases are first HOLD, second HOLD, two-dimensional HOLD duration sweep with fixed-time compensation, HOLD duration sweep with fixed-voltage compensation, RF duration with fixed HOLD, RF duration extending HOLD, and RC-only. All three AWG/RF pairs and both DDR policies represented by the fixtures are checked. First/second HOLD use 10us RAMP → 10us HOLD → 10us RAMP → 10us HOLD, with explicit RF +100ns offset and 9.9us width inside the selected HOLD.','',
        'Fine cases exercise each of the three channels through 81..112 samples at 0/190MHz (all 16 remainders and the 95/96 split), plus every duration 1..31 at 0MHz and at 190MHz/37deg. Other pairs remain active. The carrier short-pulse oracle uses a separately observed long reference, not a fit to each short pulse.','',
        'The original suite2 status remains failed because its first fixed-voltage attempt detected a validation-harness source-hash change before simulation. The fresh fixed-voltage retry re-prepared identical PMEM/DMEM/GUI input bytes and passed. The only differing prior source hash was the validation-only raw diagnostic reporting file. Original failures and logs are preserved. The first suite lacked wrapper_path.txt before simulation and is also preserved.','',
        'The additional audit first terminated with an empty log (cause unproven); its logged retry exposed an incorrect nearest-round delay comparison. The corrected new audit uses the production ceil rule and the exact nine-decimal GUI precision bound, keeps all earlier artifacts, and reports zero actual quantized timing differences.','',
        'See [TIMING_LIMIT.md](TIMING_LIMIT.md) for the direct observation versus inferred physical timestamp distinction and the shared-port limitation. `requested_timing_error_cycles=0` is relative to the actual HOLD anchor +100ns, not zero-offset output or an ideal absolute RAMP timeline.','',
        '[First/second HOLD digital output](v5_first_second_hold_v3.png) · [1/16/31-sample RF traces](v5_fine_1_16_31.png) · [Machine-readable evidence and exact paths](result.json)','',
        'No board access or analog measurement, ADC/FIR arithmetic validation, RTL/XDC edit, new synthesis or deployment was performed. DDS area/clipping after IIR remains outside existing DC area compensation.']
    (HERE/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('complete','exact_zero_offset_supported','coarse_shots','coarse_pair_shots','physical_sample_checks','fine_rf_bursts')}))

if __name__=='__main__':main()
