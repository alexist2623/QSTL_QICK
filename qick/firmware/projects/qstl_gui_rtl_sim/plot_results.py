"""Standalone scientific plots from independent predictions and XSim traces."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze import rows, signed

HERE=Path(__file__).resolve().parent
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                     'figure.dpi':140,'savefig.dpi':180})


def main():
    p=argparse.ArgumentParser();p.add_argument('case');a=p.parse_args();d=HERE/a.case
    summary=json.loads((d/'comparison.json').read_text())
    trace=rows(d/'rtl_samples.csv');commands=rows(d/'rtl_commands.csv');gpio=rows(d/'rtl_gpio.csv')
    cycles=np.array([int(r['cycle']) for r in trace]);time=cycles/300
    def lane0(key):return np.array([signed(int(r[key],16)&65535,16) for r in trace])
    sq=[r for r in commands if r['kind']=='sqcmd']
    ct=np.array([int(r['cycle']) for r in sq])/300
    words=[int(r['word'],16) for r in sq]
    freq=[(w&0xffffffff)*4800000/2**32 for w in words]
    amp=[(w>>64)&0xffffffff for w in words]
    phase=[((w>>32)&0xffffffff)*360/2**32 for w in words]
    enabled=[(w>>128)&1 for w in words]
    fig,axs=plt.subplots(4,1,figsize=(13,9),sharex=True,layout='constrained')
    axs[0].step(time+10/300,lane0('expected'),where='post',color='black',lw=1.7,label='Predicted DAC (phase integral + pipeline)')
    axs[0].step(time,lane0('dac'),where='post',color='#e76f24',lw=.9,ls='--',label='RTL DAC stream, lane 0')
    axs[0].set_ylabel('Square DAC code');axs[0].legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=2,frameon=False,fontsize=8)
    axs[1].step(time,lane0('awg'),where='post',color='#226f9a',lw=1,label='AWG DAC stream, lane 0')
    axs[1].set_ylabel('AWG DAC code');axs[1].legend(loc='lower center',bbox_to_anchor=(.5,1.01),frameon=False,fontsize=8)
    gt=np.array([0]+[int(r['cycle'])/300 for r in gpio]+[time[-1]])
    gv=[0]+[int(r['value'],16) for r in gpio]
    gv.append(gv[-1]);gv=np.array(gv)
    axs[2].step(gt,((gv>>6)&1)+1.3,where='post',label='External marker (bit 6)',color='#8f408e')
    axs[2].step(gt,(gv>>5)&1,where='post',label='DDR request (bit 5)',color='#338755')
    axs[2].set_yticks([0,1,1.3,2.3],['0','1','0','1']);axs[2].set_ylabel('Trigger outputs')
    axs[2].legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=2,frameon=False,fontsize=8)
    if sq:
        axs[3].step(np.r_[ct,time[-1]],np.r_[freq,freq[-1]],where='post',lw=2,label='Frequency (kHz)',color='#3157a0')
        ax=axs[3].twinx();ax.step(np.r_[ct,time[-1]],np.r_[amp,amp[-1]],where='post',ls='--',lw=1.2,color='#ab5b23',label='Amplitude code')
        ax.set_ylabel('Amplitude code',color='#ab5b23');axs[3].set_ylabel('Frequency (kHz)',color='#3157a0')
    axs[3].set_xlabel('Time since reset release (us)')
    for axis in axs:axis.grid(alpha=.18)
    if a.case=='gui_autonomy':
        for row in rows(d/'rtl_epochs.csv'):
            x=int(row['cycle'])/300
            for axis in axs:axis.axvline(x,color='gray',lw=.8,ls=':')
            label={'seed_end_confirmed':'Seed END confirmed','gui_start':'GUI main starts'}.get(row['kind'])
            if label:
                axs[0].text(x+2,.03,label,transform=axs[0].get_xaxis_transform(),rotation=90,fontsize=8,va='bottom')
    fig.suptitle(f'{a.case}: GUI Python -> machine code -> actual tProcessor RTL\n'
                 f'{summary["sample_checks"]:,} scalar DDS sample checks; {len(summary["errors"])} errors')
    fig.savefig(d/'overview.png');fig.savefig(d/'overview.pdf');plt.close(fig)

    # Full 16-lane words around the amplitude transition (or initial enable).
    index=next((i for i in range(1,len(sq)) if amp[i]!=amp[i-1]),0)
    change=int(sq[index]['cycle']) if sq else int(cycles[0])
    lo=change-50;hi=change+65
    dense=np.arange(lo,hi)
    # CSV includes every change in these streams; reconstruct exact held words.
    indices=np.searchsorted(cycles,dense,side='right')-1
    def unpack(key,offset=0):
        source=np.searchsorted(cycles,dense-offset,side='right')-1
        return np.array([signed((int(trace[max(i,0)][key],16)>>(16*k))&65535,16)
                         for i in source for k in range(16)])
    x=(np.repeat(dense,16)+np.tile(np.arange(16)/16,len(dense))-change)*1000/300
    prediction=unpack('expected',10);observed=unpack('dac')
    fig,axs=plt.subplots(2,1,figsize=(11,5.5),sharex=True,layout='constrained')
    axs[0].plot(x,prediction,color='black',lw=2,label='Predicted DAC')
    axs[0].plot(x,observed,color='#e76f24',ls='--',lw=1,label='RTL DAC (all 16 lanes)')
    axs[0].axvline(0,color='#888',ls=':',label='Command accepted by SquarePulse')
    axs[0].axvline(14*1000/300,color='#507a4b',ls=':',label='Expected DAC update: +14 cycles')
    axs[0].set_ylabel('DAC code');axs[0].legend(fontsize=8)
    axs[1].plot(x,observed-prediction,color='#2d8192');axs[1].set_ylabel('RTL - predicted\n(DAC codes)')
    axs[1].set_xlabel('Time relative to SquarePulse command acceptance (ns)')
    for axis in axs:axis.grid(alpha=.2)
    fig.suptitle(f'{a.case}: command-to-DAC update detail')
    fig.savefig(d/'update_detail.png');plt.close(fig)

    if a.case=='gui_sweep':
        fig,axs=plt.subplots(2,3,figsize=(15,6),layout='constrained')
        for column,(name,values,before,after) in enumerate([
            ('Amplitude',amp,50,65),('Frequency',freq,600,6000),('Phase',phase,150,1200)]):
            j=next(i for i in range(1,len(sq)) if values[i]!=values[i-1])
            event_cycle=int(sq[j]['cycle'])
            dense=np.arange(event_cycle-before,event_cycle+after)
            prediction=unpack('expected',10);observed=unpack('dac')
            x=(np.repeat(dense,16)+np.tile(np.arange(16)/16,len(dense))-event_cycle)/300
            axs[0,column].plot(x,prediction,color='black',lw=1.8,label='Predicted DAC')
            axs[0,column].plot(x,observed,color='#e76f24',ls='--',lw=.9,label='RTL DAC')
            axs[0,column].axvline(0,color='gray',ls=':',lw=.8)
            extra={'Amplitude':'Also: phase 90 -> 0 degrees',
                   'Frequency':'Also: amplitude 1640 -> 820; phase 90 -> 0',
                   'Phase':'Frequency and amplitude unchanged'}[name]
            axs[0,column].set_title(f'{name}: {values[j-1]:g} -> {values[j]:g}\n{extra}',fontsize=10)
            axs[0,column].set_ylabel('DAC code');axs[0,column].legend(fontsize=8)
            axs[1,column].plot(x,observed-prediction,color='#2d8192')
            axs[1,column].set_ylim(-1,1);axs[1,column].set_ylabel('RTL - predicted')
            axs[1,column].set_xlabel('Time from IP command acceptance (us)')
            for axis in axs[:,column]:axis.grid(alpha=.2)
        fig.suptitle('Cartesian sweep transitions: scalar phase-integral prediction vs actual RTL\n'
                     'Frequency in kHz; amplitude in DAC codes; phase in degrees')
        fig.savefig(d/'parameter_updates.png');plt.close(fig)

        marker=summary['first_marker_cycle']
        dense=np.arange(marker-12,marker+125)
        indices=np.searchsorted(cycles,dense,side='right')-1
        x=(dense-marker)*1000/300
        fig,axs=plt.subplots(3,1,figsize=(10,6),sharex=True,layout='constrained')
        gpio_cycles=np.array([int(r['cycle']) for r in gpio])
        gpio_indices=np.searchsorted(gpio_cycles,dense,side='right')-1
        markers=np.array([0 if i<0 else (int(gpio[i]['value'],16)>>6)&1 for i in gpio_indices])
        axs[0].step(x,markers,where='post',color='#8f408e');axs[0].set_ylabel('External marker')
        for axis,key,label,color in [(axs[1],'dac','Square DAC','#e76f24'),(axs[2],'awg','AWG DAC','#226f9a')]:
            samples=[signed(int(trace[max(i,0)][key],16)&65535,16) for i in indices]
            axis.step(x,samples,where='post',color=color);axis.set_ylabel(label+' code')
            delay=(summary['first_nonzero_dac_cycles'][key]-marker)*1000/300
            axis.axvline(delay,color='gray',ls=':',lw=.8)
            axis.text(delay+8,max(samples)*.5,f'+{delay:.3f} ns',fontsize=9)
        for axis in axs:axis.axvline(0,color='gray',ls=':',lw=.8);axis.grid(alpha=.2)
        axs[2].set_xlabel('Time from first external marker rising edge (ns)')
        fig.suptitle('Digital marker and DAC boundary timing at the first loop start')
        fig.savefig(d/'startup.png');plt.close(fig)

    cap=rows(d/'rtl_capture.csv');accept=[int(r['cycle']) for r in cap if r['kind']=='accept']
    mature=[int(r['cycle']) for r in cap if r['kind']=='mature']
    samples=[r for r in cap if r['kind']=='sample'];ddr=rows(d/'rtl_ddr.csv')
    fig,axs=plt.subplots(2,1,figsize=(11,6),layout='constrained')
    if accept:
        x=np.arange(len(accept));pred=np.array(accept)+8712
        axs[0].plot(x,(pred-np.array(accept))/300,'o',ms=7,mfc='none',label='Predicted deadline')
        axs[0].plot(x,(np.array(mature)-accept)/300,'x',label='RTL deadline')
        axs[0].plot(x,np.array(summary['trigger_to_first_sample_cycles'])/300,'.',label='RTL first 1 MSPS sample')
        axs[0].set_ylabel('Delay from accepted trigger (us)');axs[0].set_xlabel('Trigger index')
        axs[0].legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=3,frameon=False,fontsize=8)
    if samples:
        iq=[int(r['iq'],16) for r in samples]
        memory=[(int(r['data'],16)>>(128*k))&((1<<128)-1) for r in ddr for k in range(2)]
        for lane,label,color in [(0,'I','#356da0'),(1,'Q','#bc6634')]:
            predicted=[signed((w>>(64*lane))&((1<<64)-1),64) for w in iq]
            actual=[signed((w>>(64*lane))&((1<<64)-1),64) for w in memory]
            axs[1].plot(predicted,color=color,lw=1.5,label=f'{label}: FIR capture value')
            axs[1].plot(actual,'x',color=color,ms=3,label=f'{label}: DDR AXI data')
        axs[1].set_ylabel('Stored signed int64 code');axs[1].set_xlabel('Captured sample index')
        axs[1].legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=4,frameon=False,fontsize=8)
    for axis in axs:axis.grid(alpha=.2)
    fig.suptitle(f'{a.case}: FPGA trigger compensation and IQ64 storage')
    fig.savefig(d/'capture.png');plt.close(fig)


if __name__=='__main__':main()
