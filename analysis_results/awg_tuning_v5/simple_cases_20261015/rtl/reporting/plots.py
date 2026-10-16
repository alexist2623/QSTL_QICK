"""Small representative plots from observed digital RTL data only."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent
E=HERE.parent
def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def signed(word):
    value=int(word,16)
    return [(((value>>(16*i))&65535)+32768)%65536-32768 for i in range(16)]

def fine():
    case=read(E/'fine/prepared.json')['cases'][0]
    out=Path(case['folder'])
    results=read(out/'result.json')['checks'][0]['bursts']
    with (out/'fine_0.csv').open() as stream:
        rows=list(csv.DictReader(stream))
    origin=int(rows[0]['cycle'])*16
    samples=np.asarray([value for row in rows for value in signed(row['rf'])])
    fig,axes=plt.subplots(2,2,figsize=(12,6.7),sharex=True,sharey=True)
    for ax,burst in zip(axes.flat,results[::2]):
        start=burst['first_sample']-origin
        n=burst['samples']
        relative=np.arange(-5,106)
        times=relative/4.8
        y=samples[start+relative]
        ax.step(times,y,where='post',color='#006f9e',lw=1.5,label='Observed SG-v6 RF output')
        expected=np.where((relative>=0)&(relative<n),4000,0)
        ax.step(times,expected,where='post',color='#555555',lw=.9,ls='--',label='Requested active window')
        ax.axvline(n/4.8,color='#a34400',lw=1,ls=':')
        ax.text(n/4.8-.25,4200,f'{n/4.8:.6f} ns',ha='right',fontsize=10,color='#793000')
        ax.set_title(f'{n} DAC samples | '+('one command' if n<96 else 'two commands'),fontsize=11)
        ax.set_ylim(-250,4900);ax.grid(alpha=.18);ax.set_xlim(-1.05,22)
        ax.set_xlabel('Time from observed RF start (ns)');ax.set_ylabel('RF DAC code')
    axes[0,0].legend(loc='upper left',fontsize=8)
    fig.suptitle('Digital RTL: fine RF duration across the 95 / 96 sample boundary',fontsize=15)
    fig.text(.5,.02,'One sample = 0.208333 ns. RF0 first repetition shown; all 24 pulses checked.\nRF sum-input waveform shown; sum and final DAC register-slice lanes are verified separately. No physical measurement.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.08,1,.94))
    target=HERE/'fine_94_97_rtl.png';assert not target.exists();fig.savefig(target,dpi=155);plt.close(fig)
    (HERE/'fine_plot_provenance.json').write_text(json.dumps(dict(plot=str(target),sha256=sha(target),
        source=str(out/'fine_0.csv'),source_sha256=sha(out/'fine_0.csv'),result_sha256=sha(out/'result.json'),
        no_measurement=True,code_sha256=sha(Path(__file__))),indent=2))

def coarse():
    out=Path(read(E/'coarse_status.json')['cases']['hold_fixed_time']['folder'])
    assert read(out/'result.json')['validation_status']=='passed'
    with (out/'rtl_events.csv').open() as stream:
        events=[dict(cycle=int(r['cycle']),port=int(r['port']),word=int(r['word'],16)) for r in csv.DictReader(stream)]
    anchors=[r for r in events if r['port']==1 and (r['word']>>152)&255==0 and (r['word']>>96)&0xffffffff]
    first=anchors[0]['cycle']-30
    last=anchors[1]['cycle']-30
    fig,axes=plt.subplots(3,1,figsize=(13,8),sharex=True)
    inputs=[]
    for channel,(suffix,ax) in enumerate(zip((4,5,6),axes)):
        path=out/f'physical_{suffix}.csv';inputs.append(dict(path=str(path),sha256=sha(path)))
        with path.open() as stream:
            rows=[r for r in csv.DictReader(stream) if first-10<=int(r['cycle'])<=last+50]
        idx=np.asarray([int(r['cycle'])*16+lane for r in rows for lane in range(16)])
        times=(idx-first*16)/4800.
        dac=np.asarray([v for r in rows for v in signed(r['dac'])])
        ax.plot(times,dac,color='#006f9e',lw=.7,label='Observed final DAC digital samples')
        ax.axhline(0,color='#999999',lw=.6)
        ax.set_ylabel(f'AWG{1+2*channel} + RF{2*channel}\nDAC code')
        ax.grid(alpha=.18)
        ax.legend(loc='upper right',fontsize=8)
    axes[-1].set_xlabel('Time relative to first observed HOLD SET command (us)')
    axes[-1].set_xlim(-.03,(last-first)/300.+.15)
    matrix=read(out/'independent_matrix_oracle.json')
    fig.suptitle('Digital RTL: nonidentity virtual matrix + HOLD / voltage sweep',fontsize=15)
    fig.text(.5,.015,'First point, first repetition shown; three AWG/RF pairs. Matrix = [[1, .23, -.11], [-.17, 1, .07], [.12, -.09, 1]].\nRF offset +100 ns explicitly requested. IIR/DC compensation changes the final DAC baseline; this is not an analog oscilloscope trace.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.07,1,.94))
    target=HERE/'matrix_hold_final_dac_rtl.png';assert not target.exists();fig.savefig(target,dpi=150);plt.close(fig)
    (HERE/'matrix_plot_provenance.json').write_text(json.dumps(dict(plot=str(target),sha256=sha(target),
        numeric_sources=inputs,result_sha256=sha(out/'result.json'),matrix=matrix['matrix'],
        first_tproc_set_cycle=first,shown_next_shot_boundary=last,no_measurement=True,
        code_sha256=sha(Path(__file__))),indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('kind',choices=('fine','coarse'));args=parser.parse_args()
    globals()[args.kind]()
