"""Plot the measured RTL DAC output across END and the explicit AXI-Lite Stop."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from verify_square_gui_controls import CASES

HERE=Path(__file__).resolve().parent
fig,axes=plt.subplots(3,1,figsize=(12,8),layout='constrained',sharex=True)
for ax,case,title in zip(axes,CASES,('Experiment: mute ON','Experiment: mute OFF','Standalone SquarePulse Start')):
    d=HERE/case
    def rows(name):
        with (d/name).open() as f:return list(csv.DictReader(f))
    epochs={r['kind']:int(r['cycle']) for r in rows('rtl_epochs.csv')}
    start=epochs['gui_start'];data=rows('rtl_samples.csv')
    x=np.array([(int(r['cycle'])-start)/300 for r in data])
    raw=np.array([int(r['dac'],16)&65535 for r in data],dtype=np.int32)
    raw=np.where(raw>=32768,raw-65536,raw)
    ax.step(x,raw*(800./32768),where='post',color='#2466a4',lw=1.4,label='Actual RTL DAC output')
    ax.axvline((epochs['end_confirmed']-start)/300,color='#967120',ls='--',label='tProcessor END')
    ax.axvline((epochs['manual_mute']-start)/300,color='#b93449',ls=':',label='Explicit AXI-Lite Stop')
    ax.set_title(title,loc='left');ax.set_ylabel('mV equivalent');ax.set_ylim(-25,25)
    ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
axes[0].legend(loc='upper center',bbox_to_anchor=(.65,1.25),ncol=3,frameon=False,fontsize=9)
axes[-1].set_xlim(-2,1120);axes[-1].set_xlabel('Time from host program start (us)')
fig.suptitle('Actual tProcessor + SquarePulse RTL: requested 2 kHz / 500 us period\n'
             'Amplitude sweep 10 to 20 mV; standalone 20 mV; phase offset 45 degrees',fontsize=13)
fig.savefig(HERE/'square_controls_rtl.png',dpi=170)
fig.savefig(HERE/'square_controls_rtl.pdf')
