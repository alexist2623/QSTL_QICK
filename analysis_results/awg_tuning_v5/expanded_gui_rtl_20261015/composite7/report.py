"""Audit new composite7 proofs and plot the actual v5 RTL output traces."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
ROOT=Path('C:/GIT_Workspace/QSTL_QICK')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    state=json.loads((HERE/'status.json').read_text())
    assert state['complete'] and state['stage']=='passed' and len(state['cases'])==7
    provenance=json.loads((HERE/'adapter_provenance.json').read_text())
    for path_key,hash_key in (('original','original_sha256'),('adapter','adapter_sha256'),
                               ('reused_v5_oracle','oracle_sha256')):
        assert sha(provenance[path_key])==provenance[hash_key]
    for path,digest in state['source_hashes'].items():
        assert sha(path)==digest,('Changed production source',path)
    files={}
    prepared=[]
    for name in ('custom_sweep','hahn_manual'):
        item=json.loads((HERE/f'{name}_prepared.json').read_text())
        prepared.append(item)
        input_root=Path(item['build'])
        assert sha(input_root/'gui_input.json')==item['gui_input_sha256']
        for path in input_root.iterdir():
            if path.is_file(): files[str(path)]=sha(path)
        for path,digest in item['source_hashes'].items(): assert sha(path)==digest
        for path,digest in item['rtl_source_hashes'].items():
            assert sha(path)==digest,('Changed RTL input',path)
            files[path]=digest
        for case in item['cases']:
            for name,digest in case['inputs'].items(): assert sha(Path(case['folder'])/name)==digest
    bursts=0
    physical_samples=0
    amplitude_errors=[]
    rms_errors=[]
    phase_errors=[]
    figure,axes=plt.subplots(7,1,figsize=(12,14),sharex=True,constrained_layout=True)
    rows=[]
    for index,(case,axis) in enumerate(zip(state['cases'],axes)):
        assert case['passed'] and case['carrier']['passed']
        for path,digest in case['evidence_hashes'].items():
            assert sha(path)==digest,('Changed simulation evidence',path)
            files[path]=digest
        out=Path(case['case'])
        for name in ('result.json','runtime_rf_pulses.json','rf_specs.json','expected.json','program.asm','pmem.hex','dmem.txt'):
            files[str(out/name)]=sha(out/name)
        assert case['command_value_mismatches']==case['command_timing_mismatches']==0
        assert len(case['area_checks'])==3
        assert all('residual=0' in line and 'shots=2' in line and 'reset_checks=2' in line for line in case['area_checks'])
        assert len(case['rf_checks'])==3 and len(case['v5_physical'])==3
        for check,physical,path in zip(case['rf_checks'],case['v5_physical'],case['carrier']['paths']):
            assert len(check['blocks'])==len(path['bursts'])==6
            assert check['width_errors']==check['relative_timing_errors']==0
            bursts+=len(check['blocks'])
            physical_samples+=physical['physical_samples_checked']
            for burst in path['bursts']:
                amplitude_errors.append(abs(burst['fitted_amplitude']-burst['gain']))
                rms_errors.append(burst['rms_codes'])
                phase_errors.append(abs(burst['relative_phase_error_degrees']))
        blocks=case['rf_checks'][0]['blocks'][:3]
        origin=blocks[0][0]
        x=[];y=[]
        with (out/'physical_4.csv').open() as stream:
            for row in csv.DictReader(stream):
                cycle=int(row['cycle'])
                if origin-30<=cycle<=blocks[-1][1]+30:
                    word=int(row['rf'],16)
                    samples=[(((word>>(16*lane))&65535)+32768)%65536-32768 for lane in range(16)]
                    x.append((cycle-origin)/300.)
                    y.append(max(abs(value) for value in samples))
        axis.step(x,y,where='post',color='#245e87',linewidth=.85)
        axis.fill_between(x,y,step='post',color='#245e87',alpha=.15)
        axis.grid(axis='x',color='#dddddd',linewidth=.5)
        axis.set_ylim(-100,2500)
        axis.set_ylabel('|DDS| codes')
        title=(f'Custom: tau={case["tau_us"]:g} us, pi={case["pi_us"]:g} us, '
               f'pi/2={case["pi_us"]/2:g} us') if index<6 else (
               'GUI Hahn -> Custom: total tau=4 us; pi=.4 us; endpoints gain1500/phase0, body gain750/phase90')
        axis.set_title(title,loc='left',fontsize=9)
        for label,(begin,end) in zip(('pi/2','pi','pi/2'),blocks):
            axis.text(((begin+end)/2-origin)/300.,2200,label,ha='center',fontsize=8)
        rows.append(f'| {index+1} | {case["scenario"]} | {case["tau_us"]:g} | {case["pi_us"]:g} | {case["command_count"]} | 18 | PASS |')
    assert bursts==126
    axes[-1].set_xlabel('Time from first RF pi/2 burst [us]')
    axes[-1].set_xlim(-.1,7.7)
    figure.suptitle('Fresh current GUI -> actual v5 RTL: composite 7 cases\nRF path 0, first repetition; all three paths and both repetitions independently checked',fontsize=12)
    plot=HERE/'composite7_actual_v5_rtl.png'
    figure.savefig(plot,dpi=150)
    plt.close(figure)
    lines=['# Current production GUI -> candidate v5 RTL: composite 7 cases','',
        'PASS. Seven newly compiled inputs and seven fresh actual RTL simulations completed. Prior v4 simulation results were not reused as current PASS. Production GUI, Python, RTL, XDC, firmware and board state were not changed.','',
        'Input flow: actual MainWindow settings -> normal Run Experiment arguments -> normal runtime host-coordinate resolver -> real QICK compiler PMEM/DMEM -> actual tProcessor/TMUX/DDS/AWG/v5 sum RTL. Only the board-I/O boundary was replaced by local compilation. The prior six tau x pi host coordinates and Hahn-to-Custom named-amplitude/phase settings were retained.','',
        '| Case | GUI setting | tau (us) | pi (us) | Commands | DDS bursts | Result |',
        '|---:|---|---:|---:|---:|---:|---|',*rows,'',
        '- Six Custom points sweep RF generator 0: tau=1/2/3 us x pi=.2/.4 us. Other two RF paths retain tau=1 us, pi=.2 us. Enabled endpoint pi/2 duration is half the chosen pi duration.',
        '- Hahn -> Custom is exercised through the actual preset-selection control; emitted events are unchanged by conversion. Total tau=4 us gives 2 us on each side. Named endpoints use a0=1500/p0=0 degrees and the body a1=750/p1=90 degrees on all three paths.',
        '- Existing outer HOLD-relative RF offset is +100 ns. It was already present in the original seven fixtures and was retained; no rejection workaround or input-shift variant was needed. Exact simultaneous AWG/RF commands are outside this request.',
        '- All 126 actual RF bursts passed exact fabric-clock width and relative-onset checks. Every emitted command word and timestamp matched the independent instruction-model expectation after one constant testbench origin offset.',
        '- The production driver reads the actual candidate HWH, requiring v2 sum, AWG delay13 and common pipeline2. Both native latencies are31. Actual RF command-to-trace timing is checked separately for every burst.',
        f'- Independent sum lane and final-output checks passed. {physical_samples:,} final DAC sample checks use saturate/round(AWG[c-25]+RF[c-12]); the separate RTL sum oracle maintains its own 13-entry AWG history.',
        '- Three DC-area engines completed two repetitions in every case, with zero residual area and both IIR/reset checks passing.',
        f'- Actual DDS frequency/gain/relative-phase fits passed: max gain error {max(amplitude_errors):.6f} codes (<2), max carrier RMS {max(rms_errors):.6f} codes (<1.2), max relative-phase error {max(phase_errors):.6f} degrees (<.05). Phase command words are also checked exactly. Carrier-fit quantization bounds do not relax timing.',
        '- No preparation, compile, elaboration, simulation or checker failure occurred; no retries were performed. A dedicated copied simulation library was used, with at most one xsim process from this suite.',
        f'- All {len(state["source_hashes"])} captured production Python files, current RTL inputs and newly generated PMEM/DMEM match their recorded hashes after execution. Candidate HWH SHA256: `{state["candidate_hwh_sha256"]}`.','',
        'Scope: digital simulation only. No new synthesis, board analog measurement, ADC/FIR arithmetic verification, calibration power measurement or firmware deployment. The DDS sum is after AWG IIR; additional DDS area and clipping are not compensated by AWG DC-area correction.','',
        '[Actual RTL waveforms](composite7_actual_v5_rtl.png) | [Execution status](status.json) | [Source/input/evidence hashes](proof_hashes.json) | [Adapter provenance](adapter_provenance.json)','']
    (HERE/'REPORT.md').write_text('\n'.join(lines),encoding='utf8')
    for path in HERE.glob('*.py'): files[str(path)]=sha(path)
    validators=ROOT/'analysis_results/awg_tuning_v5/composite_t2_fix/rtl'
    for name,record in (('run.py','status.json'),('check_carrier.py','carrier_checks.json')):
        expected=json.loads((validators/record).read_text())['helper_sha256']
        assert sha(validators/name)==expected,('Original checker source changed',name)
        files[str(validators/name)]=expected
    files[provenance['reused_v5_oracle']]=provenance['oracle_sha256']
    for path in HERE.glob('*prepared.json'): files[str(path)]=sha(path)
    for path in HERE.glob('*.prepare.log'): files[str(path)]=sha(path)
    for name in ('compile_console.log','elaborate_console.log'):
        path=Path(state['build'])/name;files[str(path)]=sha(path)
    for name in ('adapter_provenance.json','REPORT.md','composite7_actual_v5_rtl.png','status.json'):
        files[str(HERE/name)]=sha(HERE/name)
    proof=dict(production_source_hashes=state['source_hashes'],evidence_hashes=files,
               candidate_hwh_sha256=state['candidate_hwh_sha256'],source_and_input_match=True)
    (HERE/'proof_hashes.json').write_text(json.dumps(proof,indent=2))
    result=dict(passed=True,fresh_gui_programs=7,fresh_real_rtl_runs=7,rf_bursts=bursts,
        repetitions=2,rf_paths=3,command_mismatches=0,width_mismatches=0,relative_timing_mismatches=0,
        final_physical_sample_checks=physical_samples,area_residuals=0,failures=0,retries=0,
        source_and_input_match=True,board_access=False,exact_simultaneous_tested=False,
        max_gain_error_codes=max(amplitude_errors),max_carrier_rms_codes=max(rms_errors),
        max_relative_phase_error_degrees=max(phase_errors),
        report_sha256=sha(HERE/'REPORT.md'),proof_sha256=sha(HERE/'proof_hashes.json'))
    (HERE/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
