"""Plot separately tested amplitude-only, frequency-only and phase-only updates."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze import rows, signed

HERE=Path(__file__).resolve().parent
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})


def main():
    fig,axs=plt.subplots(2,3,figsize=(15,6),layout='constrained')
    fields={'Frequency':0,'Phase':32,'Amplitude':64}
    cases=[('gui_500us','Amplitude',50,65),('gui_frequency','Frequency',600,6000),
           ('gui_sweep','Phase',150,1200)]
    for column,(case,name,before,after) in enumerate(cases):
        d=HERE/case
        assert json.loads((d/'comparison.json').read_text())['passed'],case
        trace=rows(d/'rtl_samples.csv')
        commands=[r for r in rows(d/'rtl_commands.csv') if r['kind']=='sqcmd']
        words=[int(r['word'],16) for r in commands]
        shift=fields[name]
        j=next(i for i in range(1,len(words)) if (words[i]>>shift&0xffffffff)!=(words[i-1]>>shift&0xffffffff))
        for other,bits in fields.items():
            if other!=name:assert (words[j]>>bits&0xffffffff)==(words[j-1]>>bits&0xffffffff),(case,other)
        assert words[j]>>128==words[j-1]>>128
        event=int(commands[j]['cycle']);dense=np.arange(event-before,event+after)
        cycles=np.array([int(r['cycle']) for r in trace])
        def unpack(key,offset=0):
            indices=np.searchsorted(cycles,dense-offset,side='right')-1
            return np.array([signed(int(trace[max(i,0)][key],16)>>(16*k)&65535,16)
                             for i in indices for k in range(16)])
        expected=unpack('expected',10);actual=unpack('dac')
        assert np.array_equal(expected,actual),case
        x=(np.repeat(dense,16)+np.tile(np.arange(16)/16,len(dense))-event)/300
        values=[words[i]>>shift&0xffffffff for i in [j-1,j]]
        unit='DAC codes'
        if name=='Frequency':values=[v*4800000/2**32 for v in values];unit='kHz'
        if name=='Phase':values=[v*360/2**32 for v in values];unit='degrees'
        axs[0,column].plot(x,expected,color='black',lw=1.8,label='Predicted DAC')
        axs[0,column].plot(x,actual,color='#e76f24',ls='--',lw=.9,label='RTL DAC')
        axs[0,column].axvline(0,color='gray',ls=':',lw=.8)
        axs[0,column].set_title(f'{name}: {values[0]:g} -> {values[1]:g} {unit}')
        axs[0,column].set_ylabel('DAC code');axs[0,column].legend(fontsize=8)
        axs[1,column].plot(x,actual-expected,color='#2d8192')
        axs[1,column].set_ylim(-1,1);axs[1,column].set_ylabel('RTL - predicted (codes)')
        axs[1,column].set_xlabel('Time from IP command acceptance (us)')
        for axis in axs[:,column]:axis.grid(alpha=.2)
    fig.suptitle('Single-parameter updates: other parameters held constant\n'
                 'Independent scalar phase-integral prediction vs actual RTL (all 16 DAC lanes)')
    fig.savefig(HERE/'independent_updates.png')
    fig.savefig(HERE/'independent_updates.pdf')
    plt.close(fig)


if __name__=='__main__':main()
