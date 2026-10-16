"""Plot saved native samples only; no device access."""
from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from compact_capture import reload_channel, scaled_slice

root = Path(__file__).resolve().parent
rows = list(csv.DictReader((root/'analysis_run_01/all_20000_plateaus.csv').open(encoding='utf-8')))
chosen = [r for r in rows if 9995 <= int(r['point']) <= 9999]
origin = min(float(r['hold_start_scope_s']) for r in chosen) - 3e-6
stop = max(float(r['hold_end_scope_s']) for r in chosen) + 4e-6
fig, axes = plt.subplots(2, 1, figsize=(13, 6), sharex=True, constrained_layout=True)
for ch, color in ((1, '#1f77b4'), (2, '#d95f02')):
    cap = root/'run_01/scope_capture'
    data = reload_channel(cap/f'ch{ch}.preamble.json', cap/f'ch{ch}.ieee_block.bin.gz')
    t, v, invalid = scaled_slice(data)
    keep = (t >= origin) & (t <= stop)
    selected = [r for r in chosen if int(r['scope_channel']) == ch]
    offset = float(selected[0]['fixed_offset_mv'])
    ax = axes[ch-1]
    ax.plot((t[keep]-origin)*1e6, v[keep]*1000-offset, '.-', ms=2, lw=.8,
            color=color, label=f'DAC{ch+3}/CH{ch}: native 200 ns samples')
    for r in selected:
        start = (float(r['hold_start_scope_s'])-origin)*1e6
        end = (float(r['hold_end_scope_s'])-origin)*1e6
        target = float(r['requested_mv'])
        ax.hlines(target, start, end, colors='black', linestyles='--', lw=.8)
        ax.axvspan(start, end, color='grey', alpha=.12)
        ax.text((start+end)/2, 425, f'{r["point"]}\n10 us', ha='center', fontsize=8)
    ax.set_ylabel('Corrected voltage (mV)')
    ax.set_ylim(-25, 465)
    ax.legend(loc='lower left', fontsize=8)
    ax.grid(alpha=.2)
axes[-1].set_xlabel('Time from local plot origin (us)')
fig.suptitle('Last five points: 10 us programmed HOLD, 1 us ramps\nShading/dashes: programmed HOLD/requested level; fixed channel offset removed')
fig.savefig(root/'pulse_detail.png', dpi=170)
plt.close(fig)
