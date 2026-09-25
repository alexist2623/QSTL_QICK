"""Compare measured RTL shot-end outputs before and after per-shot reset."""
from pathlib import Path
import csv
import json
import shutil

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = Path(__file__).resolve().parent
OUT = HERE.parent/'repeat_reset'
OUT.mkdir(exist_ok=True)
NEW = Path('C:/JeonghyunPark/Workspace/Vivado_Output/gui_rtl6/rc_precomp_repeat_reset')
OLD = NEW.parent/'rc_precomp'
font_manager.fontManager.addfont('C:/Windows/Fonts/malgun.ttf')
font_manager.fontManager.addfont('C:/Windows/Fonts/malgunbd.ttf')
plt.rcParams.update({'font.family': 'Malgun Gothic', 'font.size': 12,
                    'axes.unicode_minus': False, 'axes.spines.top': False,
                    'axes.spines.right': False})
scale = 800/32768

def load(folder):
    data = np.genfromtxt(folder/'rc_analog.csv', delimiter=',', names=True)
    with (folder/'rtl_gpio.csv').open() as f:
        edges = [int(r['cycle']) for r in csv.DictReader(f) if int(r['value'], 16) != 0]
    assert len(edges) == 400
    ends = np.array(edges[1::2])
    samples = ((ends+11)//4)*4
    values = []
    for ch in (0, 1):
        d = data[data['channel'] == ch]
        lookup = {int(row['cycle']): row for row in d}
        after = [lookup[int(c)] for c in samples]
        assert all(r['target'] == 0 for r in after)
        values.append(np.array([r['dac']*scale for r in after]))
    return values, np.array(edges[::2])

old, old_starts = load(OLD)
new, new_starts = load(NEW)
assert all(np.all(v == 0) for v in new)
assert np.all(np.diff(new_starts) - np.diff(old_starts) == 79)
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.9))
fig.subplots_adjust(left=.075, right=.97, top=.77, bottom=.24, wspace=.22)
fig.suptitle('각 반복 종료 후 IIR 초기화: 200회 모두 DAC = 0',
             fontsize=20, fontweight='bold', y=.97)
for ch, ax in enumerate(axes):
    x = np.arange(1, 201)
    ax.plot(x, old[ch], color='#d36a06', lw=2, label='수정 전: 누적값 유지')
    ax.plot(x, new[ch], color='#138653', lw=2.5, label='수정 후: 매 반복 초기화')
    ax.scatter([200], [0], color='#138653', s=42, zorder=4)
    ax.set(title=f'AWG {ch+1}', xlabel='반복 횟수', ylabel='반복 종료 후 DAC 전압 (mV)',
           xlim=(1, 207), ylim=((-1.4, .35) if ch == 0 else (-.3, 1.4)))
    ax.grid(alpha=.2)
    ax.text(105, .13 if ch == 0 else -.21, '수정 후: 모든 반복에서 0 mV',
            color='#138653', ha='center', fontsize=12, fontweight='bold')
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(.5, .89), ncol=2, frameon=False)
fig.text(.075, .1, '실제 tProcessor + AWG RTL · 10×10 sweep × 2회 · 내부 누적값과 16개 DAC 샘플 모두 0 확인', fontsize=11)
fig.text(.075, .035, '아날로그 RC는 초기화하지 않음. 이 파형의 RC 뒤 최대 오차: 0.0764 mV (τ = 10 µs, ±800 mV 환산).',
         fontsize=10, color='#526174')
for ext in ('png', 'pdf'):
    fig.savefig(OUT/f'before_after.{ext}', dpi=160)
plt.close(fig)
summary=json.loads((NEW/'result.json').read_text())
summary.update(per_repeat_dac_zero=True, additional_cycles_per_repeat=79,
               additional_us_per_repeat=79/300,
               final_dac_before_mv=[float(v[-1]) for v in old],
               final_dac_after_mv=[float(v[-1]) for v in new])
(OUT/'result.json').write_text(json.dumps(summary, indent=2))
for name in ('xsim.log','gui_export.py','program.asm'):
    shutil.copyfile(NEW/name, OUT/name)
print(json.dumps(summary, indent=2))
