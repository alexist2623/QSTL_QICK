"""Summarize real RTL evidence for per-channel DAC-current normalization."""
import argparse
import json
from pathlib import Path
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    cases={
        'baseline': 'rc_precomp_repeat_reset_grid_3x3_current_20_20_20',
        'different_currents': 'rc_precomp_repeat_reset_grid_3x3_current_10_32_16_analog',
        'rf_and_duration': 'rc_precomp_repeat_reset_hold_duration_3x3_current_32_10_20',
        'grid_20x20': 'rc_precomp_repeat_reset_grid_20x20_current_10_32_16',
        'fixed_voltage_dc': 'rc_precomp_repeat_reset_grid_3x3_current_fixed_voltage',
    }
    results={}
    for name,directory in cases.items():
        result=json.loads((args.build/directory/'result.json').read_text())
        assert result['validation_status']=='passed',name
        assert result['points']==(400 if name=='grid_20x20' else 9),name
        assert result['repetitions']==2
        assert len(result['exact_awg_results'])==2
        expected=result['points']*2+1
        assert all(f'resets={expected} zero_checks={expected}' in row for row in result['reset_results'])
        results[name]=result
    fig,axes=plt.subplots(3,2,figsize=(12,9),sharex=True,layout='constrained')
    for col,key in enumerate(('baseline','different_currents')):
        directory=args.build/cases[key]
        data=np.genfromtxt(directory/'rc_analog.csv',delimiter=',',names=True)
        for ch in range(3):
            ax=axes[ch,col];rows=data[data['channel']==ch]
            current=results[key]['dac_current_ma'][ch];scale=current*40/32768
            time=rows['cycle']/300
            ax.plot(time,rows['target']*scale,label='Nominal RTL waveform',lw=1.3)
            ax.plot(time,rows['dac']*scale,label='DAC output with RC compensation',lw=.9,alpha=.8)
            ax.plot(time,rows['after_rc']*scale,label='After analog RC',lw=.9,ls='--')
            ax.set_title(f'{("AWG 1", "AWG 2", "SquarePulse")[ch]}: {current:g} mA, FS +/-{current*40:g} mV')
            ax.set_ylabel('Voltage (mV)');ax.grid(alpha=.2)
            if ch==2:ax.set_xlabel('Simulation time (us)')
        if key=='different_currents':
            square=data[data['channel']==2]
            # The GUI requests 10 mV; check the independent pre-filter RTL bus.
            peak=np.max(np.abs(square['target']))*results[key]['dac_current_ma'][2]*40/32768
            assert abs(peak-10)<=results[key]['dac_current_ma'][2]*40/8192
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Generated GUI Python -> real tProcessor / TMUX / waveform RTL\nCurrent-to-voltage gain modeled from 20 mA = +/-800 mV; tau = 10 us')
    fig.savefig(args.out/'current_voltage_rtl.png',dpi=160);plt.close(fig)
    grid=json.loads((args.build/cases['grid_20x20']/'grid_axes.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for ch,axis in enumerate(grid):
        current=results['grid_20x20']['dac_current_ma'][ch]
        axes[ch].plot(axis['requested_mv'],axis['requested_mv'],'k--',label='Requested voltage')
        axes[ch].plot(axis['requested_mv'],axis['executed_target_mv'],'o-',label='Executed target')
        axes[ch].set_title(f'AWG {ch+1}, {current:g} mA: max error {axis["max_target_error_mv"]:.6g} mV')
        axes[ch].set_xlabel('Requested sweep voltage (mV)');axes[ch].set_ylabel('Voltage (mV)')
        axes[ch].grid(alpha=.2);axes[ch].legend()
    fig.suptitle('20 x 20 x 2 repeats: existing integer sweep-step error is retained')
    fig.savefig(args.out/'current_sweep_error.png',dpi=160);plt.close(fig)
    lines=['# DAC current RTL validation','',
           'Software scaling and command timing passed. Physical current/voltage were not measured.',
           'RFDC analog current gain is modeled as 800 mV at 20 mA; ARM and RFDC are excluded from this RTL testbench.',
           '', '| Case | Points x repeats | Currents: AWG1 / AWG2 / Square (mA) | Commands | Cycles |',
           '|---|---:|---|---:|---:|']
    for name,result in results.items():
        lines.append(f'| {name} | {result["points"]} x 2 | {result["dac_current_ma"]} | {result["commands"]} | {result["cycles"]} |')
    lines+=['','Every emitted command word and timestamp matched; both AWG RC integer recurrences were checked at every scalar sample.',
            'Each repeat and sweep-axis reset was checked. The 20x20 case had 801 history resets per AWG.',
            'Small cases also used an independent analog RC model. The full 20x20 grid checked digital arithmetic without the analog RC model.',
            '', '## Analog RC residuals (small cases)', '', '| Case | Channel | Maximum error (mV) |','|---|---|---:|']
    for name,result in results.items():
        for row in result['analog_results']:
            match=re.search(r'ch=(\d+) max_error_codes=([\d.eE+-]+)',row)
            if match:
                ch=int(match[1]);error=float(match[2])*result['dac_current_ma'][ch]*40/32768
                lines.append(f'| {name} | {ch} | {error:.9g} |')
    lines+=['','## Voltage sweep precision','',
            'This change preserves the existing integer increment mechanism; it does not fix accumulated sweep-step rounding.',
            'Requested 5 -> 15 mV, 20 points:']
    for ch,axis in enumerate(grid):
        lines.append(f'- AWG {ch+1}: final {axis["executed_target_mv"][-1]:.9g} mV; maximum target error {axis["max_target_error_mv"]:.9g} mV.')
    lines+=['','The nominal voltage-to-code quantization step is full_scale_mv / 8192 (four signed-16 codes).',
            'Requested increment is 10/19 = 0.526315789 mV. The existing constant code increment rounds to 44 codes (0.537109375 mV) at 10 mA, and 12 codes (0.46875 mV) at 32 mA.',
            'RF duration case checks 18 RF pulses while the two AWGs use different currents; RF gain/frequency and pulse timing are unchanged.',
            '', '## Shared GUI and independent compensation checks', '',
            '356 selected GUI/compiler regression tests passed; after the final port-selection fix, all 35 current/front-panel tests passed again.',
            'The GUI click test opens AWG Tuning -> Stability -> AWG Tuning front panels, applies 10/32/16/12 mA through the real worker/server setter with an emulated RFDC, and checks every channel write. Untargeted DACs, RF outputs, AWG assignments and user-entered voltage/sweep values remain unchanged.',
            'Fixed-voltage and fixed-time DC fields were independently checked against hold + trapezoidal ramp area in mV us for two channels, both current assignments and every 3x3 point. RC coefficient was checked against round(2^48 / (2*tau_us*4800)), independent of output current.',
            'Live RFDC current and physical output voltage were not measured. Current control requires a compatible updated QICK server and enabled VOP hardware conditions.',
            '', '![Shared front panel (emulated readback)](front_panel_current.png)',
            '', '![RTL waveforms](current_voltage_rtl.png)', '', '![Sweep error](current_sweep_error.png)']
    (args.out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (args.out/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
