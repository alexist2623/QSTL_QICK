"""Plot newly executed digital traces; no hardware or source mutation."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent
EVIDENCE=HERE.parent
BUILD=Path('F:/Vivado_Output/a5post_gui_rtl2')
FINE=Path('F:/Vivado_Output/a5post_fine_rtl1')

def lanes(word):
    value=int(word,16)
    return [(((value>>(16*i))&65535)+32768)%65536-32768 for i in range(16)]

def main():
    fig,axes=plt.subplots(2,2,figsize=(13,7),gridspec_kw={'width_ratios':[3,2]})
    for i,hold in enumerate((1,2)):
        folder=next(p for p in BUILD.iterdir() if f'_v5_post_hold{hold}_output_sum' in p.name)
        result=json.loads((folder/'result.json').read_text());proof=result['output_sum']['pairs'][0]['measurements'][0]
        events=json.loads((folder/'expected.json').read_text())['events']
        first_ramp=next(e['cycle'] for e in events if e['port']==0 and (int(e['word'],16)>>152)&255==1 and (int(e['word'],16)>>144)&3==2)
        origin=first_ramp+result['cycle_offset']+51
        with (folder/'physical_4.csv').open() as stream:rows=list(csv.DictReader(stream))
        cycles=np.asarray([int(r['cycle']) for r in rows]);start=max(0,int(np.searchsorted(cycles,origin-30)));stop=int(np.searchsorted(cycles,max(origin+12150,proof['rf_physical_stop']+150)))
        rows=rows[start:stop];cycles=cycles[start:stop]
        x=(cycles.repeat(16)*16+np.tile(np.arange(16),len(rows))-origin*16)/4800.
        y=np.asarray([v for r in rows for v in lanes(r['dac'])])
        rf_start=(proof['rf_physical_start']-origin)/300.;rf_stop=(proof['rf_physical_stop']-origin)/300.
        for ax in axes[i]:
            ax.plot(x,y,color='#236b9b',lw=.45,label='Actual final digital DAC samples')
            ax.axvspan(rf_start,rf_stop,color='#dca02c',alpha=.18,label='Requested RF window (+100 ns, 9.9 us)')
            ax.axvline(rf_start,color='#a95321',lw=.9);ax.axvline(rf_stop,color='#a95321',lw=.9);ax.set_xlabel('Time from first ramp output (us)');ax.set_ylabel('DAC code');ax.grid(alpha=.2)
        axes[i,0].set_xlim(-.1,max(40.5,rf_stop+.5));axes[i,1].set_xlim(rf_start-.04,rf_start+.06)
        axes[i,0].set_title(f'RF in HOLD {hold}; 10 us RAMP/HOLD/RAMP/HOLD')
        axes[i,1].set_title(f'HOLD {hold} RF turn-on, digital samples')
    axes[0,0].legend(fontsize=8,loc='upper right')
    fig.suptitle('Fresh v5 GUI → tProcessor/TMUX → AWG/DDS → sum-v2 → final output slice\nRepresentative pair 1; all three pairs checked. Exact zero-offset request is unsupported.\nActual output includes IIR/RC precompensation: the DAC baseline may slope during a requested HOLD.',fontsize=11)
    fig.tight_layout();fig.savefig(HERE/'v5_first_second_hold_v2.png',dpi=160);plt.close(fig)

    folder=FINE/'short_1_to_31_gain4000';result=json.loads((folder/'result.json').read_text())
    proof=result['checks'][0]
    with (folder/'fine_0.csv').open() as stream:rows=list(csv.DictReader(stream))
    origin=int(rows[0]['cycle'])*16;values=np.asarray([v for row in rows for v in lanes(row['rf'])])
    fig,axes=plt.subplots(1,3,figsize=(12,3.8))
    for ax,n in zip(axes,(1,16,31)):
        burst=next(b for b in proof['bursts'] if b['samples']==n)
        first=burst['first_sample']-origin;lo=first-3;hi=first+n+4
        time=(np.arange(lo,hi)-first)/4.8
        ax.step(time,values[lo:hi],where='post',color='#236b9b',lw=1.6)
        ax.axvline(0,color='#777',ls=':',lw=1);ax.axvline(n/4.8,color='#a95321',ls=':',lw=1)
        ax.set_title(f'{n} sample(s) = {n/4.8:.6f} ns');ax.set_xlabel('Time from RF active start (ns)');ax.set_ylabel('RF sample code');ax.grid(alpha=.2)
    fig.suptitle('Fresh v5 GUI → real SG-v6 BRAM/DDS: 1/16/31 active samples\nRF input to sum shown; final sum is independently checked on all lanes. No analog measurement.',fontsize=10)
    fig.tight_layout();fig.savefig(HERE/'v5_fine_1_16_31.png',dpi=160);plt.close(fig)

if __name__=='__main__':main()
