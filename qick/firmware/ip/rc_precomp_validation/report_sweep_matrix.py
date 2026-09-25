"""Report only completed 20 x 20 production-RTL sweep cases."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from run_sweep_matrix import CASES

LABELS=dict(ramp_rate='Ramp duration',hold_duration='Hold duration',
    rf_duration='RF duration + AWG extension',rf_duration_fixed='RF duration, AWG fixed',
    rf_frequency='RF frequency',rf_power='RF amplitude/power',
    rf_frequency_power='RF frequency x power')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    summaries={};measurements={};manifest=[]
    for case in CASES:
        source=args.build/f'rc_precomp_repeat_reset_{case}_20x20'
        result=json.loads((source/'result.json').read_text())
        assert result['points']==400 and result['repetitions']==2
        assert result['validation_status'] in ('passed','completed_with_timing_findings')
        assert result['rf_measurements']['pulses']==800
        assert len(result['exact_awg_results'])==2
        assert all('resets=801 zero_checks=801' in text for text in result['reset_results'])
        assert len(result['reset_results'])==2
        summaries[case]=result
        measurements[case]=json.loads((source/'rf_measurements.json').read_text())
        dest=args.out/case;dest.mkdir(exist_ok=True)
        for name in ('result.json','gui_export.py','program.asm','pmem.hex','dmem.txt',
                     'tb_rc_gui.sv','rc_bd.v','rf_measurements.json','xsim.log','prepared.json'):
            shutil.copyfile(source/name,dest/name)
        fixture=source/'synthetic_calibration.db'
        if fixture.exists():shutil.copyfile(fixture,dest/fixture.name)
        for name in ('rtl_events.csv','rtl_commands.csv','rc_analog.csv','rf_samples.csv'):
            path=source/name
            with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            manifest.append(dict(path=str(path),bytes=path.stat().st_size,sha256=digest))
    (args.out/'results.json').write_text(json.dumps(summaries,indent=2))
    (args.out/'raw_manifest.json').write_text(json.dumps(manifest,indent=2))
    voltage_source=args.build/'rc_precomp_repeat_reset_no_aux_grid_20x20'
    voltage_result=json.loads((voltage_source/'result.json').read_text())
    assert voltage_result['points']==400 and voltage_result['repetitions']==2
    shutil.copyfile(voltage_source/'result.json',args.out/'dual_dac_voltage_result.json')

    fig,axes=plt.subplots(2,2,figsize=(13,8),constrained_layout=True)
    rows=measurements['rf_frequency'][0:40:2]
    axes[0,0].plot(range(20),[r['expected_frequency_mhz'] for r in rows],'k--',label='Command')
    axes[0,0].plot(range(20),[r['frequency_mhz'] for r in rows],'o',ms=4,label='Measured RTL samples')
    axes[0,0].set(title='RF frequency: 20 values',xlabel='Sweep index',ylabel='MHz')
    for case,marker in (('rf_duration','o'),('rf_duration_fixed','x')):
        rows=measurements[case][0:40:2]
        axes[0,1].plot(range(20),[r['width_cycles']/300 for r in rows],marker,
                       ms=5,label=LABELS[case])
    axes[0,1].plot(range(20),[r['requested_width_cycles']/300 for r in rows],'k--',label='Requested duration')
    axes[0,1].set(title='RF duration: both AWG timing modes',xlabel='Sweep index',ylabel='us')
    rows=measurements['rf_power'][0:40:2]
    axes[1,0].plot(range(20),[r['expected_gain'] for r in rows],'k--',label='Gain command')
    axes[1,0].plot(range(20),[r['fitted_amplitude_code'] for r in rows],'o',ms=4,label='Sine amplitude from RTL samples')
    axes[1,0].set(title='RF amplitude: synthetic calibration -> real DDS',xlabel='Power sweep index',ylabel='DAC code')
    xpos=np.arange(len(CASES))
    for ch in range(2):
        errors=[float(summaries[case]['analog_results'][ch].split('=')[-1])*800/32768 for case in CASES]
        axes[1,1].bar(xpos+(ch-.5)*.35,errors,width=.35,label=f'AWG {ch+1}')
    axes[1,1].set(title='After analog RC: max error over all shots',ylabel='mV',xticks=xpos,
                 xticklabels=['Ramp','Hold','RF dur+','RF dur','RF freq','RF amp','RF f x amp'])
    for ax in axes.flat:
        ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Every case: 20 x 20 points x 2 repeats | two AWGs + real tProcessor/TMUX/RF RTL\nDC + RC enabled; tau = 10 us; no RFDC or ARM')
    fig.savefig(args.out/'sweep_matrix_results.png',dpi=150);plt.close(fig)

    rows=measurements['rf_frequency_power']
    peaks=np.array([r['fitted_amplitude_code'] for r in rows]).reshape(20,20,2)
    gains=np.array([r['expected_gain'] for r in rows]).reshape(20,20,2)
    fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    for ax,data,title in ((axes[0],peaks[:,:,0],'Sine amplitude measured from actual RTL'),
                         (axes[1],np.max(np.abs(peaks-gains),axis=2),'Maximum amplitude error across 2 repeats')):
        im=ax.imshow(data,origin='lower',aspect='auto',extent=(-26,-14,180,225))
        ax.set(title=title,xlabel='Requested power in calibration fixture (dBm)',ylabel='Frequency (MHz)')
        fig.colorbar(im,ax=ax,label='DAC codes')
    fig.savefig(args.out/'rf_frequency_power_grid.png',dpi=150);plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(12,4),constrained_layout=True)
    for ax,case in zip(axes,('rf_duration','rf_duration_fixed')):
        errors=np.array([r['width_error_cycles']*1000/300 for r in measurements[case]]).reshape(20,20,2)
        im=ax.imshow(np.max(errors,axis=2),origin='lower',aspect='auto',vmin=0,vmax=20/3,
                     extent=(-.5,19.5,-.5,19.5))
        ax.set(title=LABELS[case],xlabel='RF duration sweep index',ylabel='AWG voltage sweep index')
        fig.colorbar(im,ax=ax,label='Actual width minus commanded width (ns)')
    fig.suptitle('Timing finding: periodic RF stops only at 3-clock block boundaries\nAll 400 points and both repetitions measured in RTL')
    fig.savefig(args.out/'rf_duration_timing_error.png',dpi=150);plt.close(fig)

    report=['# All mixed sweeps: completed 20 x 20 RTL verification','',
        'Each case executes 400 points, with two repetitions per point and two active AWG outputs.',
        'All seven cases ran the production tProcessor/TMUX/AWG/RC and RF DDS RTL.',
        'RFDC and ARM are excluded; the measurements here are digital DAC interface samples.',
        'The separate two-DAC voltage 20 x 20 x 2 test also completed; its result is retained as dual_dac_voltage_result.json.',
        '','RF duration timing discrepancies remain; completion is not an all-tests-pass claim.',
        '','| Case | Result | Shots | Commands checked | Samples checked per AWG | Max analog RC error (mV) |',
        '|---|---|---:|---:|---:|---:|']
    for case,result in summaries.items():
        samples=int(result['exact_awg_results'][0].split('=')[-1])
        error=max(float(line.split('=')[-1])*800/32768 for line in result['analog_results'][:2])
        report.append(f'| {LABELS[case]} | {result["validation_status"]} | 800 | {result["commands"]:,} | {samples:,} | {error:.6f} |')
    report.extend(['','## RF duration finding','',
        'The RF duration sweep uses a continuous periodic command with a three-clock block. The RF controller consumes a queued zero-gain stop only at a block boundary.',
        'For a commanded duration of N clocks, the measured width is ceil(N/3)*3 clocks. This creates a real output-duration error of zero, one, or two clocks (up to 6.666667 ns at 300 MHz).',
        'This behavior is not a postprocessing artifact and has not been fixed in production software or RTL. It is retained as a failed exact-duration check.'])
    for case in ('rf_duration','rf_duration_fixed'):
        rf=summaries[case]['rf_measurements']
        report.append(f'- {LABELS[case]}: {rf["width_mismatch_pulses"]}/800 pulses differ from the commanded duration; maximum {rf["width_error_max_cycles"]} clocks.')
    report.extend(['','Every timed command word and timestamp matched the instruction model.',
        'All 16 DAC lanes and the signed 72-bit RC history matched the independent integer recurrence on every checked clock.',
        'Both AWGs passed 801 history/zero checks: initial configuration plus all 800 repeat completions.',
        'RF frequency, fitted sine amplitude, sample peak and pulse width were measured from every emitted RF pulse. A short sampled sinusoid need not hit its continuous-time peak; amplitude is therefore fitted from all samples, with residuals checked separately.',
        'RF repetitions had identical programmed frequency/gain/width; every power-table gain matched the independent fixture formula within one code.',
        '', '## Settings and interpretation', '',
        '- AWG voltage axis: 5 to 15 mV, 20 points; second AWG also outputs SET/RAMP/DC waveforms.',
        '- Ramp/RF duration: 0.1 to 0.416666667 us, 20 points, 5 fabric-clock increments.',
        '- AWG hold duration: 1 to 1.95 us, 20 points, 15 fabric-clock increments.',
        '- RF frequency: 180 to 225 MHz; RF power axis: -26 to -14 dBm in the synthetic fixture.',
        '- DC + RC enabled; tau 10 us. Analog RC capacitor state is retained across digital resets.',
        '- RF power tests use an explicitly synthetic SQLite calibration dataset read by the production GUI calibration loader. They verify gain scheduling and DDS output, not physical dBm calibration.',
        '- Analog error is measured against the delayed nominal, quantized AWG waveform. It is separate from the existing integer-increment voltage error.',
        '- The prior 20-point AWG voltage test measured 14.2578125 mV at a requested 15 mV endpoint; these tests do not claim that existing quantization error has been fixed.',
        '', '## Retention', '',
        'Waveform CSV capture is bounded to the initial 12,000 clocks after program start; assertions and analog RC error statistics cover every clock of every shot.',
        'All-shot RF pulse samples and timed command logs are retained. Compiled snapshots were isolated for concurrent runs. No firmware/production project files were deleted.',
        'The former 200 x 200 run was cancelled at user request and is not counted as a completed validation.'])
    report.extend(['','## Initial analysis and recapture','',
        'The initial analysis incorrectly required explicit RF stop commands even for oneshot output. The corrected analysis uses the oneshot length field and explicit stop timing only for periodic mode.',
        'The initial hold-duration and RF-duration-with-extension runs completed all in-RTL checks but left truncated RF sample streams. Those two complete 20 x 20 x 2 simulations were rerun with explicit file closure. The original evidence remains in each case\'s capture_v1_incomplete directory.',
        'Other cases were reanalyzed from their existing complete RTL command and RF sample evidence. No missing samples were invented or replaced with model output.'])
    (args.out/'REPORT.md').write_text('\n'.join(report)+'\n')
    print('All seven 20 x 20 x 2 RTL cases completed and reported, including unresolved RF duration timing findings.')


if __name__=='__main__':main()
