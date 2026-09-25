"""Compare the long-period amplitude sweep and autonomous DDS output."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze import rows,signed

HERE=Path(__file__).resolve().parent
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})


def main():
    fig,axs=plt.subplots(2,1,figsize=(13,7),layout='constrained')
    for axis,case in zip(axs,['gui_500us','gui_autonomy']):
        d=HERE/case;result=json.loads((d/'comparison.json').read_text())
        assert result['passed'],case
        trace=rows(d/'rtl_samples.csv')
        time=np.array([int(r['cycle']) for r in trace])/300
        predicted=[signed(int(r['expected'],16)&65535,16) for r in trace]
        actual=[signed(int(r['dac'],16)&65535,16) for r in trace]
        axis.step(time+10/300,predicted,where='post',color='black',lw=1.8,label='Predicted DAC')
        axis.step(time,actual,where='post',color='#e76f24',ls='--',lw=1,label='RTL DAC')
        axis.set_ylabel('Square DAC code');axis.set_xlabel('Time on the 300 MHz cycle grid (us)')
        axis.grid(alpha=.18);axis.legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=2,frameon=False)
        if case=='gui_500us':
            edges=[];previous=0
            for row in trace:
                word=int(row['dac'],16)
                for lane in range(16):
                    sample=signed(word>>(16*lane)&65535,16)
                    if sample>0 and previous<0:edges.append(int(row['cycle'])/300+lane/4800)
                    previous=sample
            start,end=edges[:2]
            axis.set_ylim(-1850,2300)
            axis.annotate('',xy=(end,1920),xytext=(start,1920),arrowprops=dict(arrowstyle='<->',color='#3157a0'))
            axis.text((start+end)/2,1990,f'Full period: {end-start:.6f} us',ha='center',color='#3157a0')
            commands=[r for r in rows(d/'rtl_commands.csv') if r['kind']=='sqcmd']
            when=(int(commands[1]['cycle'])+14)/300
            axis.axvline(when,color='#338755',ls=':',lw=1)
            axis.text(when+6,-1500,'Amplitude only\n820 -> 1640',color='#338755')
            axis.text(.01,.04,'2 kHz request; fixed 270-degree phase offset',transform=axis.transAxes,fontsize=9)
        else:
            epochs={r['kind']:int(r['cycle'])/300 for r in rows(d/'rtl_epochs.csv')}
            stopped=epochs['seed_end_confirmed'];started=epochs['gui_start']
            axis.set_ylim(-1800,2150)
            axis.axvspan(stopped,started,color='#3157a0',alpha=.09)
            axis.axvline(stopped,color='gray',ls=':',lw=1)
            axis.axvline(started,color='gray',ls=':',lw=1)
            axis.text(stopped+5,1670,'Seed END\nconfirmed',fontsize=9)
            axis.text(started+5,1670,'GUI main starts\n(no DDS command or reset)',fontsize=9)
            axis.text(.01,.04,'2 kHz DDS keeps its accumulated phase through END and restart',transform=axis.transAxes,fontsize=9)
    fig.suptitle('Long-period and autonomous output: actual tProcessor + production digital IPs\n'
                 'RFDC and ARM PS replaced by testbench boundaries')
    fig.savefig(HERE/'long_runs.png');fig.savefig(HERE/'long_runs.pdf');plt.close(fig)


if __name__=='__main__':main()
