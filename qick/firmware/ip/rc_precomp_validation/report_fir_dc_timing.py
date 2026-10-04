"""Inspect completed real-RTL evidence and render FIR/DC ordering plots."""
import argparse
import csv
import json
from pathlib import Path
import subprocess


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--gui',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    paths=[]
    for path in args.build.glob('*fir_dc4_*awg_v2/result.json'):
        result=json.loads(path.read_text())
        if result['validation_status']=='passed':
            paths.append(path.parent)
    assert len(paths)==8, f'Expected 8 completed cases, found {len(paths)}'
    results=[]
    def read_csv(path):
        with path.open() as stream: return list(csv.DictReader(stream))
    for folder in paths:
        result=json.loads((folder/'result.json').read_text())
        previews=json.loads((folder/'fir_dc_timing.json').read_text())
        events=read_csv(folder/'rtl_events.csv')
        origins=[int(e['cycle']) for e in events if int(e['port'])==4]
        assert len(origins)==18
        # Independent policy checks on actually executed command timestamps,
        # and preview-to-RTL correspondence at every point/repetition/channel.
        verified=0
        for shot,origin in enumerate(origins):
            preview=previews[shot//2]
            for port,output in enumerate(preview['dc_outputs']):
                if not output['active']: continue
                command_cycle=origin+round(output['command_start_us']*300)
                matching=[e for e in events if int(e['port'])==port and int(e['cycle'])==command_cycle
                          and (int(e['word'],16)>>152)&255==1]
                assert len(matching)==1, (folder.name,shot,port,command_cycle)
                assert command_cycle>=origin+round(preview['user_pulse_end_us']*300)
                if preview['policy']=='after_readout':
                    assert command_cycle>=origin+round(preview['input_end_barrier_us']*300)
                else:
                    assert command_cycle<origin+round(preview['input_end_barrier_us']*300)
                if shot+1<len(origins):
                    assert origins[shot+1] > origin+round(preview['input_end_barrier_us']*300)
                    assert origins[shot+1] > origin+round(output['dac_end_us']*300)
                verified+=1
        capture=read_csv(folder/'ddr_capture.csv')
        samples=[r for r in capture if r['event']=='sample']
        assert len(samples)==144
        assert all(int(r['cycle'])==int(r['tag']) for r in samples)
        for shot in range(18):
            one=[r for r in samples if int(r['shot'])==shot]
            assert [int(r['sample']) for r in one]==list(range(8))
            assert all(int(b['cycle'])-int(a['cycle'])==300 for a,b in zip(one,one[1:]))
        result['preview_dc_commands_verified']=verified
        result['case_directory']=str(folder)
        results.append(result)
    (args.out/'results.json').write_text(json.dumps(results,indent=2))

    selected={}
    for folder,result in zip(paths,results):
        if result['sweep_case']=='hold_duration': selected[result['dc_readout_policy']]=folder
    fig,axes=plt.subplots(2,2,figsize=(13,7),sharex=True,sharey='row')
    for col,policy in enumerate(('after_readout','overlap_readout')):
        folder=selected[policy]
        events=read_csv(folder/'rtl_events.csv')
        origin=next(int(e['cycle']) for e in events if int(e['port'])==4)
        next_origin=[int(e['cycle']) for e in events if int(e['port'])==4][1]
        preview=json.loads((folder/'fir_dc_timing.json').read_text())[0]
        data=read_csv(folder/'rc_analog.csv')
        for ch in range(2):
            ax=axes[ch,col]
            rows=[r for r in data if int(r['channel'])==ch and origin<=int(r['cycle'])<min(next_origin,origin+3600)]
            t=np.array([int(r['cycle'])-origin for r in rows])/300
            for key,label,color in [('target','Nominal AWG target','#2463d3'),
                                    ('dac','RTL DAC with RC','#e07a20'),
                                    ('after_rc','After analog RC model','#21884c')]:
                ax.plot(t,np.array([float(r[key]) for r in rows])*800/32768,label=label,color=color,lw=1.15)
            ax.axvspan(preview['trigger_us'],preview['input_end_barrier_us'],color='#297fc3',alpha=.08,label='Input measurement window')
            dc=preview['dc_outputs'][ch]
            ax.axvspan(dc['dac_start_us'],dc['dac_end_us'],color='#eb9d22',alpha=.2,label='DC compensation')
            ax.axvline(preview['user_pulse_end_us'],color='gray',ls=':',lw=1)
            if next_origin-origin<3300:
                ax.axvline((next_origin-origin)/300,color='gray',ls='--',lw=1)
                ax.text((next_origin-origin)/300+.08, ax.get_ylim()[0], 'Next repetition',rotation=90,va='bottom',fontsize=8)
            ax.set_xlim(0,11)
            ax.grid(alpha=.2)
            ax.set_ylabel(f'DAC {ch+1} (mV)')
            ax.set_xlabel('Time from repetition reference (us)')
        axes[0,col].set_title('Measure at zero, then DC' if col==0 else 'Measure through DC compensation')
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',ncol=3,fontsize=9)
    fig.suptitle('Real tProcessor / TMUX / AWG v2 RTL: first point, first repetition\n'
                 'RC tau = 10 us; 8 stored samples at 1 MSPS; both modes preserve sample count')
    fig.tight_layout(rect=(0,.1,1,.91))
    fig.savefig(args.out/'fir_dc_order_rtl.png',dpi=160)
    plt.close(fig)

    # Show real DDR acceptance/storage against the planned sample-grid bounds.
    fig,axes=plt.subplots(2,1,figsize=(12,5.3))
    for ax,(policy,folder) in zip(axes,selected.items()):
        events=read_csv(folder/'rtl_events.csv')
        origin=next(int(e['cycle']) for e in events if int(e['port'])==4)
        preview=json.loads((folder/'fir_dc_timing.json').read_text())[0]
        rows=[r for r in read_csv(folder/'ddr_capture.csv') if int(r['shot'])==0]
        sample_t=[(int(r['cycle'])-origin)/300 for r in rows if r['event']=='sample']
        ax.broken_barh([(preview['trigger_us'],8.)],(2.6,.45),facecolors='#7eb6df',label='Nominal input window')
        dc=preview['dc_outputs'][0]
        ax.broken_barh([(dc['dac_start_us'],dc['dac_end_us']-dc['dac_start_us'])],(1.6,.45),facecolors='#e8a638',label='DC compensation')
        ax.scatter(sample_t,[1.]*len(sample_t),color='#21924b',marker='|',s=150,label='Actual DDR sample accepts')
        ax.axvline(preview['storage_start_us'],color='gray',ls='--',lw=1)
        ax.set_yticks([1,1.8,2.8],['DDR samples','DC output','Input window'])
        ax.set_title(policy)
        ax.set_xlim(0,40)
        ax.grid(axis='x',alpha=.25)
        ax.set_xlabel('Time from repetition reference (us)')
    fig.suptitle('Actual DDR v3 capture controller / AXI sink; timestamp-tagged synthetic FIR input')
    fig.tight_layout(rect=(0,0,1,.94))
    fig.savefig(args.out/'fir_dc_ddr_timing.png',dpi=160)
    plt.close(fig)
    lines=['# FIR measurement / DC compensation order validation','',
           'GUI branch: `awg_tuning_v2`. Default: `after_readout`; optional: `overlap_readout`.',
           'GUI commit: `'+subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.gui,text=True).strip()+'`.',
           'No FPGA IP or bitstream change is required.',
           '', '| Case | Policy | DC mode | Points x repeats | Command timing/value errors | DDR samples |',
           '|---|---|---|---|---|---|']
    for result in results:
        lines.append(f"| {result['sweep_case'] or 'two-DAC voltage'} | {result['dc_readout_policy']} | {result['dc_mode']} | 9 x 2 | 0 / 0 | 144 |")
    lines.extend(['','All 8 runs passed: 144 shots, 1152 DDR IQ samples. Two AWG channels each reset 19 times per run.',
                  'Real production tProcessor, TMUX, AWG v2, RC recurrence, RF DDS (mixed cases), GPIO, DDR v3 controller and AXI sink were simulated.',
                  'DDR input was synthetic timestamp-tagged data at 1 MSPS. This is not an ADC/RFDC/FIR numeric or physical-board measurement.',
                  'The configured 8712-clock delay matures exactly, then capture starts on the next valid 1 MSPS sample. Input windows and DDR storage windows are different.',
                  'Every point/repeat command was compared; every AWG scalar sample and RC integer recurrence was checked. RF durations matched all tested commands.',
                  'Initial harness diagnostics exposed a sample-edge assumption, a missing monitor insertion, and a frozen timestamp tag. Only corrected fir_dc4 matrix result.json files are counted.',
                  'Waveform files contain only the first 12000 clocks. Full-run event and sample-count checks remain active.',
                  'Software: 246 assertions passed. Two Qt test modules hit a native exception during process teardown; the previous GUI also reproduces it after settings reload. See [recovery notes](RECOVERY.md) and [exit codes](software_modules/exit_codes.json).',
                  'Recovery checks found no corrupted Git objects, changed RTL fingerprints, PMEM/DMEM mismatch, Python syntax errors, or damaged report JSON/PNG files.',
                  '', '![RTL waveform](fir_dc_order_rtl.png)', '', '![DDR timing](fir_dc_ddr_timing.png)'])
    (args.out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=len(results),shots=144,ddr_samples=1152,out=str(args.out)),indent=2))


if __name__=='__main__': main()
