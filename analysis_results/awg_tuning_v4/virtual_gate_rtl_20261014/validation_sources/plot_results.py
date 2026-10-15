"""Plot saved actual RTL traces and independently checked physical targets."""
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_case import EVIDENCE,folder

def word(value):
    integer=int(value,16)
    return np.array([((integer>>(16*i))&65535) for i in range(16)],dtype=np.int64)

def main():
    path=folder('hold_fixed_time')
    assert json.loads((path/'result.json').read_text())['validation_status']=='passed'
    fig,axs=plt.subplots(3,1,figsize=(12,8),sharex=True,constrained_layout=True)
    for ch,suffix in enumerate((4,5,6)):
        rows=list(csv.DictReader((path/f'sum_alignment_{suffix}.csv').open()))
        origin=next(int(r['cycle']) for r in rows if int(r['awg'],16))
        times=[];values={key:[] for key in ('awg','rf','sum')}
        for r in rows:
            cycle=int(r['cycle'])
            # The original sparse probe triggers on INPUT changes. Its saved
            # SUM words are continuous during DDS activity, but not during the
            # final two-clock flush. Plot onset only; never interpolate that gap.
            if not origin<=cycle<origin+27:continue
            times.extend((cycle-origin+np.arange(16)/16)/300)
            for key in values:
                v=word(r[key]);v[v>=32768]-=65536
                values[key].extend(v*(800,400,800)[ch]/32768)
        ax=axs[ch]
        ax.axhline(0,color='#a0a0a0',lw=.7)
        for key,label,color in [('awg','AWG after IIR','#2c7a7b'),('rf','DDS input','#c28115'),('sum','Combiner output (+2 clocks)','#3455c5')]:
            ax.plot(times,values[key],label=label,color=color,lw=1.,alpha=.85)
        ax.set_ylabel(f'Pair {ch+1} (mV)');ax.grid(alpha=.15)
        ax.axvline(0,color='#555',ls=':',lw=.8)
        ax.axvline(2/300,color='#3455c5',ls=':',lw=.8)
    axs[0].legend(loc='upper right',ncol=3,fontsize=9)
    axs[-1].set_xlabel('Time from first AWG/DDS input (us)')
    fig.suptitle('Actual v4 RTL: full 3 x 3 matrix, simultaneous AWG + DDS onset\nFirst 90 ns of the pulse; digital trace, no analog board measurement',fontsize=13)
    fig.savefig(EVIDENCE/'virtual_matrix_rtl_alignment.png',dpi=160);plt.close(fig)
    path=folder('two_voltage_axes')
    if not (path/'result.json').exists():return
    oracle=json.loads((path/'independent_matrix_oracle.json').read_text())
    targets=np.array([r['target_codes'] for r in oracle['points']])*np.array(oracle['scales_mv'])/32768
    fig,ax=plt.subplots(figsize=(10,4.5),constrained_layout=True)
    for ch in range(3):ax.plot(np.arange(len(targets)),targets[:,ch],'-o',label=f'Physical AWG {ch+1}')
    ax.axhline(0,color='#888',lw=.8)
    ax.set(xlabel='Executed Cartesian point (each repeated twice)',ylabel='Quantized SET target (mV)',
        title='Two virtual-voltage axes -> three coupled physical outputs\nIndependent matrix/increment oracle, matched to RTL commands')
    ax.legend();ax.grid(alpha=.2)
    fig.savefig(EVIDENCE/'virtual_matrix_physical_targets.png',dpi=160);plt.close(fig)

if __name__=='__main__':main()
