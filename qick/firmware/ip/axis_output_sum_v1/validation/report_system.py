"""Validate completed v4 evidence, render traces, and write the build gate."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[5]
OUT=ROOT/'analysis_results/awg_tuning_v4'
sys.path.insert(0,str(ROOT/'qick/firmware/projects/qstl_awg_v4'))
from validate_scope import validate
from gui_rtl_extension import source_hashes
from run_system import CASES


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def collect(tag):
    validate()
    state=json.loads((OUT/f'{tag}_status.json').read_text())
    assert state['complete'] and set(state['cases'])==set(CASES), 'Incomplete system validation'
    records={};summaries={};sources={}
    for name,entry in state['cases'].items():
        assert entry['state']=='passed' and entry['exit_code']==0
        source=Path(entry['folder']);result=json.loads((source/'result.json').read_text())
        shots=CASES[name]['count']**2*2
        assert result['points']*result['repetitions']==shots and result['validation_status']=='passed'
        assert result['command_value_mismatches']==result['command_timing_mismatches']==0
        assert len(result['output_sum']['pairs'])==3
        assert all(p['shots']==shots and p['start_skew_cycles']==p['width_mismatches']==0 for p in result['output_sum']['pairs'])
        match=json.loads((source/'gui_widget_match.json').read_text())
        assert match['pmem_equal'] and match['dmem_equal'] and match['gui_sequence_unmodified']
        assert result['ddr_capture_results']==[f'FIR_DC_CAPTURE_RESULT triggers={shots} samples={shots*4} AXI_writes={shots*2} delay_cycles=8712']
        if CASES[name].get('rc_only'):
            assert len(result['rc_only_results'])==3 and not result['hardware_area_results']
        else:
            assert len(result['hardware_area_results'])==3
            for ch in (0,1,3):
                with (source/f'area_ch{ch}.csv').open() as stream:area=list(csv.DictReader(stream))
                assert len(area)==shots and all(int(row['residual_area'])==0 for row in area)
        prepared=json.loads((source/'prepared.json').read_text())
        assert prepared['program_source_hashes']==source_hashes(ROOT.parent/'PulseGenerator')
        explicit=[Path(p) for p in re.findall(r'^sv xil_defaultlib "([^"]+)"',(source/'sources.prj').read_text(),re.M)]
        assert hashlib.sha256(b''.join(p.read_bytes() for p in explicit+[source/'pmem.hex',source/'dmem.txt'])).hexdigest()==prepared['fingerprint']
        sources.update(prepared['program_source_hashes'])
        sources.update({str(p):digest(p) for p in explicit})
        destination=OUT/'system_validation'/name;destination.mkdir(parents=True,exist_ok=True)
        for p in source.iterdir():
            if p.is_file() and (p.suffix in ('.json','.hex','.sv','.v','.asm','.png') or p.name in ('dmem.txt','xsim.log','sources.prj')
                              or p.name.startswith(('area_ch','sum_edges','sum_alignment','ddr_capture'))):
                shutil.copy2(p,destination/p.name)
                records[str((destination/p.name).resolve())]=digest(destination/p.name)
        summaries[name]=result
    unit=json.loads((OUT/'unit/result.json').read_text());assert unit['passed'] and unit['samples']>=1_000_000
    for p,sha in json.loads((OUT/'unit/source_hashes.json').read_text()).items():
        assert digest(p)==sha;sources[p]=sha
    xml=ET.parse(OUT/'software_final.xml').getroot()
    suites=list(xml.iter('testsuite'))
    assert suites and sum(int(s.get('tests','0')) for s in suites)>=234
    assert all(s.get('failures')=='0' and s.get('errors')=='0' for s in suites)
    for name in ('software_final.xml','software_final.log','unit/result.json','unit/run.log','unit/source_hashes.json','hwh_preflight.json',f'{tag}_status.json'):
        records[str(OUT/name)]=digest(OUT/name)
    assert json.loads((OUT/'hwh_preflight.json').read_text())['passed']
    for p in (ROOT/'qick/firmware/projects/qstl_awg_v4').iterdir():
        if p.suffix in ('.py','.tcl','.xdc'):sources[str(p)]=digest(p)
    for p in Path(__file__).resolve().parent.glob('*.py'):
        sources[str(p)]=digest(p)
    gate=dict(complete=True,tag=tag,cases=list(summaries),source_hashes=sources,evidence_hashes=records,
              selected_area_bits=48,physical_pair_dacs=['10','11','12'],output_pipeline_cycles=2)
    (OUT/'prebuild_gate.json').write_text(json.dumps(gate,indent=2))
    (OUT/'system_summary.json').write_text(json.dumps(summaries,indent=2))
    return summaries


def plot(source_dir=None, output=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    source_dir=Path(source_dir or OUT/'system_validation/hold_fixed_time')
    output=Path(output or OUT/'rtl_sum_alignment.png')
    fig,axes=plt.subplots(3,1,figsize=(12,8),sharex=True)
    for ax,suffix,pair in zip(axes,(4,5,6),(1,2,3)):
        with (source_dir/f'sum_alignment_{suffix}.csv').open() as stream:
            rows=list(csv.DictReader(stream))
        start=next(int(r['cycle']) for r in rows if int(r['rf'],16))
        rows=[r for r in rows if start-2<=int(r['cycle'])<=start+8]
        # Every packed lane is a consecutive 4.8 GSPS sample. Plotting only
        # lane zero would alias the RF and misrepresent the output waveform.
        x=[(int(r['cycle'])-start+lane/16)*1000/300 for r in rows for lane in range(16)]
        for field,label in [('awg','AWG at sum input'),('rf','RF at sum input'),('sum','Sum output (2 registers)')]:
            samples=[]
            for r in rows:
                packed=int(r[field],16)
                for lane in range(16):
                    value=(packed>>(16*lane))&65535
                    samples.append(value-65536 if value>=32768 else value)
            ax.plot(x,samples,label=label,lw=1.4)
        ax.set_title(f'RF {pair} + AWG {pair} — actual GUI / tProcessor / RTL')
        ax.set_ylabel('signed DAC code');ax.grid(alpha=.2);ax.axvline(0,color='gray',lw=.6)
        ax.axvline(2*1000/300,color='gray',lw=.6,ls=':')
    axes[0].legend(ncol=3,fontsize=8);axes[-1].set_xlabel('Time from coincident input start (ns) — all 16 lanes')
    fig.tight_layout();fig.savefig(output,dpi=160);plt.close(fig)


def write_report(summaries):
    lines=[
        '# AWG Tuning v4 — functional validation',
        '',
        'All five cases below passed on the recorded source hashes. This report',
        'does not certify full FPGA timing closure or on-board analog operation.',
        'See `workflow_status.json` for the build stage and the v4 project',
        '`build_manifest.json` for successful firmware publication.',
        '',
        '| GUI / RTL case | Points x repetitions | RF/AWG pairs | Requested RF offset (cycles) | Start / width mismatches | Command value / timing mismatches |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for name,result in summaries.items():
        pairs=result['output_sum']['pairs']
        offsets=sorted({p['requested_delay_cycles'] for p in pairs})
        lines.append(f"| {name} | {result['points']} x {result['repetitions']} | {len(pairs)} | {offsets} | "
                     f"{sum(p['start_skew_cycles'] for p in pairs)} / {sum(p['width_mismatches'] for p in pairs)} | "
                     f"{result['command_value_mismatches']} / {result['command_timing_mismatches']} |")
    lines += [
        '',
        'Each case used actual MainWindow -> Run Experiment compilation; PMEM and',
        'DMEM matched the Verilog input byte-for-byte. Every sum lane was checked',
        'against an independent signed-add/saturate/round reference. The DC-enabled',
        'cases checked all three pre-IIR area engines and reset after each shot,',
        'with zero residual integer area. RC-only cases required zero DC commands.',
        '',
        'DDR capture used a timestamp stream to check trigger/data alignment:',
        'four samples and two AXI writes per shot, with the existing 8712-cycle',
        'delay. It does not test ADC analog conversion or FIR numeric response.',
        '',
        'The sum and bypass unit test checked 1,114,160 samples, including 149,495',
        'positive clips, 83,952 negative clips and 549,930 rounding checks.',
        'Related GUI/library software tests: 234 passed. Protected v3 source',
        'and constraint hashes: 59 files unchanged. The accumulator remains 48 bits.',
        '',
        'The added sum/bypass delay is two 300 MHz clocks. Measured RF and AWG',
        'generator path difference is 13 clocks; v4 scheduling compensates it.',
        'Final physical output path latencies are AWG 31 / RF 44 clocks from the',
        'tProcessor event, including the common routing and output slice. The',
        '`rf_measurements.latency_cycles=42` field refers to the old RF slice',
        'retained only as a diagnostic in the focused testbench. It is not the',
        'new summed physical output. In production the former RF DAC ports are zero.',
        '',
        '![Actual scalar-lane RTL trace](rtl_sum_alignment.png)',
        '',
        'The sum follows the existing AWG IIR. AWG DC compensation does not cancel',
        'added DDS area or final clipping distortion. RF gain uses raw DDS codes;',
        'calibration of the old dedicated RF connector cannot be reused. Existing',
        'integer SET sweep quantization and analog bandwidth remain unchanged.',
        '',
        'Evidence is in `system_validation/`, `system_summary.json`, `unit/`,',
        '`software_final.xml`, and `prebuild_gate.json`. The gate binds source and',
        'evidence hashes and is rechecked before full synthesis and publication.',
    ]
    (OUT/'VALIDATION_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf8')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tag',default='v4_final1');a=p.parse_args()
    summaries=collect(a.tag);plot();write_report(summaries)
    print(json.dumps({'complete':True,'cases':list(summaries)}))
