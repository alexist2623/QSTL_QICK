"""Scientific plots of the complex two-AWG run, including observed issues."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze_complex import rows,make_plan,reference,reconstruct

HERE=Path(__file__).resolve().parent
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})


def main():
    p=argparse.ArgumentParser();p.add_argument('--case',default='gui_complex_10x10');a=p.parse_args()
    d=HERE/a.case;m=json.loads((d/'expected.json').read_text())
    r=json.loads((d/'focus/comparison.json').read_text())
    plan,points,period,marker_end,relative=make_plan(m)
    trace=rows(d/'focus/rtl_samples.csv');origin=r['origin'];end=r['end_cycle']
    # Only the first 10 points are needed for waveform details. All 100 points
    # and all lanes were checked by analyze_complex.py.
    limit=origin+256+10*period+14
    values={};expected={}
    for gen in [3,1]:
        values[gen]=reconstruct(trace,'awg'+str(gen),limit)
        expected[gen]=reference(plan,gen,limit,origin)[0]
    def save(fig,name):
        fig.savefig(d/(name+'.png'));fig.savefig(d/(name+'.pdf'));plt.close(fig)
    colors={3:'#bf2637',1:'#b58a00'}
    start=origin+256+14
    fig,axs=plt.subplots(3,1,figsize=(12,9),layout='constrained')
    for ax,gen in zip(axs[:2],[3,1]):
        sl=slice(start,start+period)
        x=np.arange(period)/300
        ax.plot(x,expected[gen][sl,0]*(800.0/32768),color='black',lw=1.8,label='Integer-sweep prediction')
        ax.plot(x,values[gen][sl,0]*(800.0/32768),color=colors[gen],ls='--',lw=1.1,label='Actual RTL')
        ax.set_ylabel(f'Gen {gen} (mV equivalent)');ax.set_xlabel('Time from first DAC SET (us)')
        ax.legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=2,frameon=False,fontsize=9)
        ax.grid(alpha=.18)
    lo=start+round(16.97*300);hi=start+round(17.34*300)
    x=(np.arange((hi-lo)*16)+(lo-start)*16)/4800
    for gen in [3,1]:
        axs[2].plot(x,expected[gen][lo:hi].reshape(-1)*(800.0/32768),color='black',lw=2)
        axs[2].plot(x,values[gen][lo:hi].reshape(-1)*(800.0/32768),color=colors[gen],ls='--',lw=1,label=f'RTL gen {gen}')
    axs[2].set_xlabel('Time from first DAC SET (us)');axs[2].set_ylabel('Short-segment detail (mV)')
    axs[2].legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=2,frameon=False,fontsize=9)
    axs[2].grid(alpha=.18)
    fig.suptitle('Screenshot waveform: actual two-channel RTL at the first sweep point\n'
                 'Gen 3 set_3 = 125 mV; gen 1 set_3 = -75 mV; both channels checked on all 16 lanes')
    save(fig,'waveform_comparison')

    fig,axs=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    measured_points=rows(d/'focus/point_values.csv')
    axis_values=[np.linspace(a['start_mv'],a['stop_mv'],a['count']) for a in m['axes']]
    for ax,gen in zip(axs,[3,1]):
        grid=np.array([int(p['observed_code'])*m['full_scale_mv']/32768-float(p['requested_mv'])
                       for p in measured_points if int(p['gen'])==gen]).reshape(10,10)
        im=ax.imshow(grid,origin='lower',vmin=-.36,vmax=0,cmap='RdYlBu',aspect='equal')
        ax.set_xticks(range(10),[f'{v:g}' for v in axis_values[1]],rotation=45)
        ax.set_yticks(range(10),[f'{v:g}' for v in axis_values[0]])
        ax.set_xlabel('Requested gen 1 set_3 (mV)');ax.set_ylabel('Requested gen 3 set_3 (mV)')
        ax.set_title(f'Gen {gen}: RTL plateau minus requested voltage')
        fig.colorbar(im,ax=ax,label='Error (mV equivalent)',shrink=.9)
    fig.suptitle('10 x 10 sweep: 10 mV requested increments become 408 DAC codes\n'
                 'Actual increment = 9.9609375 mV; endpoint error = -0.3515625 mV')
    save(fig,'sweep_voltage_error')

    # Worst small overshoot: gen1 near the end of the final 0.1 us ramp at
    # point (0,9). Its RAMP step and SET code have been rounded independently.
    c=next(c for c in plan if c['point']==9 and c['gen']==1 and c['row']==4 and c['kind']=='ramp')
    ramp_start=origin+c['output_time']+14;finish=ramp_start+c['duration']//16
    lo=finish-7;hi=finish+4
    x=(np.arange((hi-lo)*16)+(lo-finish)*16)/4.8
    fig,ax=plt.subplots(figsize=(11,4.6),layout='constrained')
    ax.step(x,expected[1][lo:hi].reshape(-1),where='post',color='black',lw=2,label='Affine-step prediction')
    ax.step(x,values[1][lo:hi].reshape(-1),where='post',color='#bf2637',ls='--',lw=1.1,label='Actual RTL')
    ax.axhline(0,color='gray',ls=':',label='Requested target = 0')
    ax.axvline(0,color='#3157a0',ls=':',label='End of RAMP sample block')
    ax.set_xlabel('Time relative to end of the 0.1 us RAMP (ns)');ax.set_ylabel('Gen 1 DAC code')
    fig.suptitle('Observed undershoot at point (0,9): -16 codes = -0.390625 mV')
    ax.legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=2,frameon=False,fontsize=9)
    ax.grid(alpha=.18);save(fig,'ramp_endpoint_detail')

    gpio=rows(d/'focus/rtl_gpio.csv');cycles=np.array([int(x['cycle']) for x in gpio]);levels=np.array([int(x['value'],16)>>6&1 for x in gpio])
    rises=cycles[levels==1][::2]
    wanted=origin+256+np.arange(100)*period+1
    late=(rises-wanted)/300*1000
    fig,axs=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    dense=np.arange(wanted[1]-4,wanted[1]+12)
    observed=levels[np.searchsorted(cycles,dense,side='right')-1]
    planned=((dense<wanted[1]-1)|(dense>=wanted[1])).astype(int)
    axs[0].step((dense-wanted[1])/300*1000,planned,where='post',color='black',lw=2,label='Scheduled marker')
    axs[0].step((dense-wanted[1])/300*1000,observed,where='post',color='#bf2637',ls='--',lw=1.4,label='Actual marker')
    axs[0].set_xlabel('Time from scheduled point-1 start marker (ns)');axs[0].set_ylabel('Marker level')
    axs[0].legend(frameon=False,loc='lower right');axs[0].grid(alpha=.18)
    axs[1].plot(np.arange(100),late,'.-',color='#bf2637',ms=3)
    axs[1].set_xlabel('Sweep point index');axs[1].set_ylabel('Start marker lateness (ns)');axs[1].grid(alpha=.18)
    fig.suptitle('Marker timing failure: 99 later loop starts are 2 clocks (6.667 ns) late\n'
                 'Later start-marker width is 109 clocks; requested width is 111 clocks')
    save(fig,'marker_timing_error')


if __name__=='__main__':main()
