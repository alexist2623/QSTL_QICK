"""Plot requested AWG sweep waveforms versus completed RTL, including repeats."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from analyze import rows
from check_awg_request import prediction, expand_awg

HERE=Path(__file__).resolve().parent
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                     'savefig.dpi':180})


def load(case):
    d=HERE/case
    result=json.loads((d/'comparison.json').read_text())
    if not result['passed']:raise RuntimeError(f'{case} did not pass')
    meta=json.loads((d/'expected.json').read_text())
    checks=dict(line.split('=') for line in (d/'rtl_checks.txt').read_text().splitlines())
    events=rows(d/'rtl_events.csv')
    origin=int(events[0]['cycle'])-int(events[0]['tproc_time'])
    expected,points,period,marker=prediction(meta,int(checks['end_cycle']),origin)
    observed=expand_awg(rows(d/'rtl_samples.csv'),len(expected))
    return d,result,meta,expected,observed,points,period


def save(fig,name):
    fig.savefig(HERE/(name+'.png'));fig.savefig(HERE/(name+'.pdf'));plt.close(fig)


def main():
    d,result,meta,expected,observed,points,period=load('gui_awg_repeat')
    # Lane-zero overview is used only for legibility; all 16 lanes are checked.
    first=points[0]['set_dac_cycle'];last=points[-1]['set_dac_cycle']+period
    time=(np.arange(first,last)-first)/300
    fig,axs=plt.subplots(2,1,figsize=(14,6.2),sharex=True,layout='constrained',
                         gridspec_kw={'height_ratios':[3,1]})
    for point in points:
        if point['repeat']:continue
        left=(point['set_dac_cycle']-first)/300
        if point['point']%2==0:axs[0].axvspan(left,left+3*period/300,color='#3157a0',alpha=.06)
        axs[0].text(left+1.5*period/300,475,f"P{point['point']+1}",ha='center',fontsize=9)
        axs[0].axvline(left,color='gray',lw=.5,alpha=.4)
    axs[0].step(time,expected[first:last,0],where='post',color='black',lw=1.8,label='Requested-value prediction')
    axs[0].step(time,observed[first:last,0],where='post',color='#e76f24',ls='--',lw=.9,label='Actual RTL DAC')
    axs[0].set_ylim(-465,550);axs[0].set_ylabel('AWG DAC code (lane 0)')
    axs[0].legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=2,frameon=False)
    sample_error=np.max(np.abs(observed[first:last]-expected[first:last]),axis=1)
    axs[1].plot(time,sample_error,color='#257d8d');axs[1].set_ylim(-.1,1)
    axs[1].set_ylabel('Max error\n(all 16 lanes)');axs[1].set_xlabel('Time from first AWG DAC SET (us)')
    for ax in axs:ax.grid(alpha=.15)
    fig.suptitle('AWG Tuning: 12 parameter points x 3 hardware repeats = 36 shots\n'
                 'Amplitude: -10 / 0 / +10 mV; hold: 1.5 / 2.5 us; ramp: 0.5 / 1.0 us')
    save(fig,'awg_repeat_overview')

    colors=['#245aa5','#258660','#af4d2d']
    fig,axs=plt.subplots(2,2,figsize=(13,8),sharex=True,sharey=True,layout='constrained')
    for ax,(hold,ramp) in zip(axs.flat,[(1.5,.5),(2.5,.5),(1.5,1.),(2.5,1.)]):
        subset=[p for p in points if p['hold_us']==hold and p['ramp_us']==ramp]
        for point in subset:
            start=point['set_dac_cycle'];count=round((hold+ramp+.35)*4800)
            x=np.arange(count)/4800
            pred=expected.reshape(-1)[start*16:start*16+count]
            obs=observed.reshape(-1)[start*16:start*16+count]
            color=colors[meta['awg_request']['amplitude_mv'].index(point['amplitude_mv'])]
            if point['repeat']==0:ax.plot(x,pred,color='#333333',lw=2.4,alpha=.55)
            # Each repeat is independently plotted on the same local time axis.
            ax.plot(x,obs,color=color,ls=['--',':','-.'][point['repeat']],lw=.85)
        ax.axvline(hold,color='gray',ls=':',lw=.8)
        ax.axvline(hold+ramp,color='gray',ls=':',lw=.8)
        ax.set_title(f'Hold {hold:g} us; ramp {ramp:g} us; tail +5 mV')
        ax.set_xlabel('Time from each AWG DAC SET (us)');ax.set_ylabel('AWG DAC code')
        ax.grid(alpha=.18)
    legend=[Line2D([0],[0],color='#333333',lw=2,label='Requested prediction')]
    legend += [Line2D([0],[0],color=color,ls='--',label=f'RTL {amp:+g} mV (3 repeats)')
               for color,amp in zip(colors,meta['awg_request']['amplitude_mv'])]
    fig.legend(handles=legend,loc='outside lower center',ncol=4,frameon=False,fontsize=9)
    fig.suptitle('AWG voltage and duration sweeps: independent prediction vs RTL\n'
                 'All repetitions overlay exactly; scalar comparison includes every DAC lane')
    save(fig,'awg_sweep_detail')

    # Keep marker-to-DAC latency and RAMP startup compensation visible separately.
    point=points[0];start=point['set_dac_cycle'];lo=start-20;hi=start+round(3*300)
    count=(hi-lo)*16;x=(np.arange(count)+(lo-start)*16)/4800
    fig,axs=plt.subplots(2,1,figsize=(12,6),layout='constrained',gridspec_kw={'height_ratios':[3,2]})
    axs[0].plot(x,expected[lo:hi].reshape(-1),color='black',lw=2,label='Requested prediction')
    axs[0].plot(x,observed[lo:hi].reshape(-1),color='#e76f24',ls='--',lw=1,label='Actual RTL DAC')
    axs[0].axvline(point['hold_us'],color='#3157a0',ls=':',label='Requested RAMP start')
    axs[0].axvline(point['hold_us']+point['ramp_us'],color='#338755',ls=':',label='Requested RAMP end')
    axs[0].set_xlabel('Time from AWG DAC SET (us)');axs[0].set_ylabel('AWG DAC code')
    axs[0].legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=2,frameon=False,fontsize=9)
    # First 120 ns, relative to the external loop-start marker.
    gpio=rows(d/'rtl_gpio.csv');marker=start-13
    t=np.arange(marker-4,marker+38)
    values=np.array([int(r['value'],16) for r in gpio]);gt=np.array([int(r['cycle']) for r in gpio])
    indices=np.searchsorted(gt,t,side='right')-1
    pulse=np.where(indices>=0,(values[np.maximum(indices,0)]>>6)&1,0)
    axs[1].step((t-marker)/300*1000,pulse,where='post',color='#8f408e',label='Loop marker')
    axs[1].step((t-marker)/300*1000,(observed[t,0]==point['start_code']).astype(int)+1.5,
                where='post',color='#245aa5',label='AWG is at requested SET value')
    axs[1].axvline(13/300*1000,color='gray',ls=':')
    axs[1].text(13/300*1000+3,.5,'13 clocks = 43.333 ns',fontsize=9)
    axs[1].set_yticks([0,1,1.5,2.5],['0','1','0','1'])
    axs[1].set_xlabel('Time from loop-start marker (ns)');axs[1].set_ylabel('Digital timing')
    axs[1].legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=2,frameon=False,fontsize=9)
    for ax in axs:ax.grid(alpha=.18)
    fig.suptitle('AWG timing: exact hold/ramp durations plus the fixed output-path latency')
    save(fig,'awg_repeat_timing')


if __name__=='__main__':main()
