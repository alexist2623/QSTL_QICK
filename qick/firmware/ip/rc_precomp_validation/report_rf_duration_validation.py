"""Summarize complete RTL evidence for direct RF lengths and long fallback."""
import argparse
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    state=json.loads((args.build/'rf_duration_oneshot_v1/status.json').read_text())
    assert len(state['cases'])==4
    assert all(s['status']=='passed' for s in state['cases'].values()),state
    args.out.mkdir(parents=True,exist_ok=True)
    results={};measurements={}
    for label,s in state['cases'].items():
        source=Path(s['output'])
        result=json.loads((source/'result.json').read_text())
        shots=s['points']*s['repetitions']
        rf=result['rf_measurements']
        assert result['points']==s['points'] and result['repetitions']==2
        assert rf['pulses']==shots
        assert len(result['reset_results'])==2
        assert all(f'resets={shots+1} zero_checks={shots+1}' in r for r in result['reset_results'])
        assert len(result['exact_awg_results'])==2
        assert rf['periodic']==(label=='limit_periodic')
        if label!='limit_periodic':
            assert rf['width_mismatch_pulses']==0 and rf['width_error_max_cycles']==0
            assert rf['requested_width_error_max_cycles']<1e-8
            assert result['validation_status']=='passed'
        else:
            assert result['validation_status']=='completed_with_timing_findings'
            assert rf['width_error_max_cycles']==2
        results[label]=result
        measurements[label]=json.loads((source/'rf_measurements.json').read_text())
        dest=args.out/label;dest.mkdir(exist_ok=True)
        for name in ('result.json','rf_measurements.json','gui_export.py','gui_compiler_source.py',
                     'program.asm','pmem.hex','dmem.txt','tb_rc_gui.sv','prepared.json','xsim.log'):
            shutil.copy2(source/name,dest/name)
    (args.out/'results.json').write_text(json.dumps(results,indent=2))
    shutil.copy2(args.build/'rf_duration_oneshot_v1/status.json',args.out/'status.json')

    fig,axes=plt.subplots(2,2,figsize=(12,7),constrained_layout=True)
    for row,(label,old_case,title) in enumerate((
        ('short_extend','rf_duration','AWG length extends with RF'),
        ('short_fixed','rf_duration_fixed','AWG length fixed'),
    )):
        old_path=args.build/f'rc_precomp_repeat_reset_{old_case}_20x20/rf_measurements.json'
        old=json.loads(old_path.read_text())
        new=measurements[label]
        for col,(data,version) in enumerate(((old,'Before: periodic'),(new,'After: direct one-shot length'))):
            err=np.array([(r['width_cycles']-r['requested_width_cycles'])*1000/300 for r in data]).reshape(20,20,2)
            err[np.abs(err)<1e-8]=0
            im=axes[row,col].imshow(np.max(err,axis=2),origin='lower',aspect='auto',
                                   extent=(-.5,19.5,-.5,19.5),vmin=0,vmax=20/3)
            axes[row,col].set(title=f'{title}\n{version}',xlabel='RF duration index',ylabel='AWG voltage index')
    fig.colorbar(im,ax=axes.ravel().tolist(),label='Actual minus requested RF width (ns)')
    fig.suptitle('Actual production RTL: each panel covers 20 x 20 points x 2 repeats')
    fig.savefig(args.out/'rf_duration_before_after.png',dpi=150);plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    for ax,label,title in zip(axes,('limit_oneshot','limit_periodic'),
                             ('All lengths fit: one-shot','One length exceeds limit: entire axis periodic')):
        rows=measurements[label][:4:2]
        x=np.arange(2)
        ax.plot(x,[r['command_width_cycles'] for r in rows],'k--o',label='Requested clocks')
        ax.plot(x,[r['width_cycles'] for r in rows],'rx',ms=9,label='Actual RTL clocks')
        ax.set(title=title,xlabel='Duration index',ylabel='RF output clocks',xticks=x)
        ax.ticklabel_format(axis='y',useOffset=False,style='plain')
        ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('65,535-clock boundary: separate 2 x 2 points x 2 repeats; AWG waveforms zero')
    fig.savefig(args.out/'rf_duration_length_limit.png',dpi=150);plt.close(fig)

    report=['# Direct RF duration RTL verification','',
        'Short RF pulses use their direct one-shot length. A duration axis uses periodic mode throughout if any executed point exceeds 65,535 generator clocks.',
        'All four fixtures executed the production tProcessor/TMUX/AWG/RC/RF DDS RTL. RFDC and ARM are not included.',
        '', '| Fixture | Points x repeats | RF mode | Widths (clocks) | Maximum requested-width error |',
        '|---|---:|---|---|---:|']
    for label,r in results.items():
        rf=r['rf_measurements']
        mode='periodic (retained long-pulse behavior)' if rf['periodic'] else 'one-shot'
        widths=', '.join(str(v) for v in rf['widths_cycles'])
        report.append(f'| {label} | {r["points"]} x 2 | {mode} | {widths} | {rf["width_error_max_cycles"]} clocks |')
    report.extend(['',
        '- The GUI/shared-compiler software suite passed 229 tests before these RTL runs.',
        '- Both full short-duration grids emitted 800 RF pulses each. Every requested length, including 35 and 40 clocks, matched the actual RF output width exactly.',
        '- The boundary one-shot fixture checked 65,534 and 65,535 clocks. The periodic fixture checked 65,535 and 65,536 clocks, with all points in periodic mode.',
        '- Long periodic output retains its block-boundary stop: 65,536 requested clocks produce 65,538 output clocks. This is preserved behavior, not an exact-timing pass.',
        '- Every emitted command word and timestamp matched the instruction model. Both AWGs matched the independent RC integer recurrence and passed all per-repeat resets.',
        '- Short-grid waveform traces are bounded to the first 12,000 clocks; command and sample checks cover every point. Boundary fixtures keep AWG values zero to isolate RF mode selection.',
        '- The existing AWG voltage increment error and analog RC residuals are separate from this RF duration change.',
        '- No production RTL, firmware bitstream, or physical RF calibration was changed by this fix.',
        '', 'Raw simulator outputs remain at the per-case paths recorded in status.json. Prior failing-duration evidence is retained unchanged.'])
    report.extend(['', '## Analog RC residuals', '',
        'These values compare the independent analog RC model with the delayed, quantized nominal AWG output. They are not RF pulse-width errors or a claim of zero analog error. Tau is 10 us; analog capacitor state persists across digital resets.', '',
        '| Fixture | AWG 1 maximum error (mV) | AWG 2 maximum error (mV) |',
        '|---|---:|---:|'])
    for label in ('short_extend', 'short_fixed'):
        errors = [float(value.split('max_error_codes=')[1]) * 800 / 32768
                  for value in results[label]['analog_results'][:2]]
        report.append(f'| {label} | {errors[0]:.6f} | {errors[1]:.6f} |')
    (args.out/'REPORT.md').write_text('\n'.join(report)+'\n')
    print('Reported all four RF duration RTL fixtures, with preserved long-periodic timing limitation.')


if __name__=='__main__':
    main()
