"""Plot saved real-RTL samples; no behavioral output replaces the DUT."""
from pathlib import Path
import argparse
import json
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--unit',type=Path,required=True)
    p.add_argument('--gui-rtl',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    scale=800/32768
    data=np.genfromtxt(a.gui_rtl/'rc_analog.csv',delimiter=',',names=True)
    fig,axes=plt.subplots(3,2,figsize=(13,9),constrained_layout=True)
    colors=('#2f6cce','#d07316','#20834b')
    for ch in range(3):
        d=data[data['channel']==ch];t=d['cycle']/300
        start=t[np.flatnonzero(d['target']!=0)[0]]
        t-=start
        window=(t>=-.1)&(t< (25 if ch<2 else 1000))
        x=t[window];target=d['target'][window]*scale
        dac=d['dac'][window]*scale;actual=d['after_rc'][window]*scale
        ax=axes[ch,0]
        ax.plot(x,dac,color=colors[1],lw=1.1,label='Actual RTL DAC output')
        ax.plot(x,target,color=colors[0],lw=1.5,label='Requested waveform',alpha=.8)
        ax.plot(x,actual,color=colors[2],lw=.8,ls='--',label='After analog RC')
        ax.set(title=('AWG output 1: DC + RC' if ch==0 else 'AWG output 2: DC + RC' if ch==1 else 'SquarePulse: 500 us period, RC'),ylabel='Voltage (mV)',xlabel='Time (us)')
        ax.grid(alpha=.2)
        axes[ch,1].plot(t,(d['after_rc']-d['target'])*scale,color=colors[2],lw=.7)
        axes[ch,1].axhline(4*scale,color='gray',ls=':',label='One effective DAC LSB')
        axes[ch,1].axhline(-4*scale,color='gray',ls=':')
        axes[ch,1].set(title='RC output error across all 100 points x 2 repeats',xlabel='Time (us)',ylabel='Error (mV)',ylim=(-.11,.11))
        axes[ch,1].grid(alpha=.2)
    axes[0,0].legend(loc='upper right',fontsize=8)
    axes[0,1].legend(fontsize=8)
    fig.suptitle('GUI Python → real tProcessor / TMUX / AWG / SquarePulse RTL → independent analog RC\n300 MHz fabric, 4.8 GSPS DAC samples, tau = 10 us, full scale = ±800 mV',fontsize=13)
    for ext in ('png','pdf'):fig.savefig(a.output/f'gui_rc_verification.{ext}',dpi=170)
    plt.close(fig)
    data=np.genfromtxt(a.unit/'rc_traces.csv',delimiter=',',names=True)
    fig,axes=plt.subplots(2,1,figsize=(12,6.5),constrained_layout=True)
    for ax,prefix in zip(axes,('awg','square')):
        for key,label,color in ((prefix+'_target','Requested waveform',colors[0]),(prefix+'_dac','Actual RTL DAC output',colors[1]),(prefix+'_after_rc','After analog RC',colors[2])):
            ax.plot(data['cycle']/300,data[key]*scale,label=label,color=color,lw=1)
        ax.set(xlabel='Time (us)',ylabel='Voltage (mV)',title='SET/RAMP/repeats' if prefix=='awg' else 'Continuous phase: amplitude, frequency, and offset-phase updates')
        ax.grid(alpha=.2)
    for when,label in ((10000/300,'Amplitude update'),(15000/300,'Frequency update'),(20000/300,'Phase offset update')):
        axes[1].axvline(when,color='gray',ls=':');axes[1].text(when,80,label,rotation=90,va='top',ha='right',fontsize=8)
    axes[0].legend(loc='upper right',fontsize=8)
    fig.suptitle('Production IP RTL: tau = 10 us, independently modeled analog RC',fontsize=13)
    for ext in ('png','pdf'):fig.savefig(a.output/f'ip_rc_updates.{ext}',dpi=170)
    plt.close(fig)
    result=json.loads((a.gui_rtl/'result.json').read_text())
    result['full_scale_mv']=800
    result['max_gui_error_mv']=[float(re.search(r'codes=([\d.]+)',s)[1])*scale for s in result['analog_results']]
    (a.output/'results.json').write_text(json.dumps(result,indent=2))


if __name__=='__main__':main()
