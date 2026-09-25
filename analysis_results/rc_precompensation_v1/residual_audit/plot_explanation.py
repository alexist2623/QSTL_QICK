"""Annotated explanation using saved production RTL and analog RC traces."""
from pathlib import Path
import csv
import json

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

OUT = Path(__file__).resolve().parent
BASE = Path('C:/JeonghyunPark/Workspace/Vivado_Output/gui_rtl6/rc_residual_audit')
font_manager.fontManager.addfont('C:/Windows/Fonts/malgun.ttf')
font_manager.fontManager.addfont('C:/Windows/Fonts/malgunbd.ttf')
plt.rcParams.update({
    'font.family': 'Malgun Gothic', 'font.size': 12,
    'axes.unicode_minus': False, 'axes.spines.top': False,
    'axes.spines.right': False, 'axes.titleweight': 'bold',
    'figure.facecolor': '#fafbfe', 'axes.facecolor': 'white',
})
BLUE, ORANGE, GREEN = '#2261b7', '#d36a06', '#138653'
GREY, RED = '#526174', '#b52735'
scale = 800 / 32768
data = np.genfromtxt(BASE/'rc_analog.csv', delimiter=',', names=True)
channels = [data[data['channel'] == i] for i in (0, 1)]
origin = channels[0]['cycle'][np.flatnonzero(channels[0]['target'] != 0)[0]]

def style(ax):
    ax.grid(alpha=.15)
    ax.axhline(0, color=GREY, lw=.9, zorder=0)
    ax.set_ylabel('전압 (mV)')

def save(fig, name):
    for ext in ('png', 'pdf'):
        fig.savefig(OUT/f'{name}.{ext}', dpi=155, facecolor=fig.get_facecolor())
    plt.close(fig)

# One full shot: show both the actual waveforms and just the added correction.
d = channels[0]
t = (d['cycle']-origin)/300
m = (t >= -.08) & (t <= 4.86)
t = t[m]
x, u, y = (d[k][m]*scale for k in ('target', 'dac', 'after_rc'))
fig, axes = plt.subplots(2, 1, figsize=(12, 8.4), sharex=True)
fig.subplots_adjust(left=.09, right=.97, bottom=.17, top=.81, hspace=.45)
fig.suptitle('① 첫 번째 반복: 중간에 남는 offset은 RC 보정 동작', fontsize=20, fontweight='bold', y=.97)
fig.text(.5, .915, '주황: DAC 출력  →  실제 RC 회로 모델  →  초록: 회로 뒤 전압',
         ha='center', fontsize=14)
ax = axes[0]
ax.plot(t, u, color=ORANGE, lw=2.5, label='DAC 출력 (실제 RTL)')
ax.plot(t, x, color=BLUE, lw=1.8, label='회로 뒤 목표 전압')
ax.plot(t, y, color=GREEN, lw=1.4, ls='--', label='RC 통과 후 전압')
ax.axvspan(3.66, 4.66, color='#dbe8f6', alpha=.55)
ax.text(4.16, 8.2, 'DC 보상 펄스', ha='center', color=BLUE, fontweight='bold')
ax.annotate('목표와 RC 뒤는 약 0\nDAC는 -0.684 mV 유지',
            xy=(2.95, -.684), xytext=(2.25, 5), color=ORANGE,
            arrowprops={'arrowstyle': '->', 'color': ORANGE},
            bbox={'boxstyle': 'round,pad=.35', 'fc': 'white', 'ec': '#ead3ba'})
ax.set(title='전체 파형 · AWG 1', ylim=(-11.7, 11.4), xlim=(-.08, 4.86))
ax.legend(loc='upper left', bbox_to_anchor=(0, 1.02), fontsize=10, ncol=3, frameon=False)
style(ax)
ax = axes[1]
correction = u-x
ax.fill_between(t, 0, correction, color=ORANGE, alpha=.2)
ax.plot(t, correction, color=ORANGE, lw=2)
ax.axvspan(3.66, 4.66, color='#dbe8f6', alpha=.4)
ax.set(title='RC가 추가한 부분만 확대: DAC 출력 - 목표 파형',
       ylim=(-.86, .9), xlabel='첫 파형 시작 기준 시간 (µs)')
ax.annotate('추가 ramp', xy=(.75, .4), xytext=(.25, .68),
            arrowprops={'arrowstyle': '->', 'color': ORANGE}, color=ORANGE)
ax.annotate('추가 flat offset\n여기도 면적이 있음', xy=(2.95, -.684), xytext=(2.25, .2),
            arrowprops={'arrowstyle': '->', 'color': ORANGE}, color=ORANGE)
ax.annotate('첫 반복에서는\nDAC도 0으로 복귀', xy=(4.77, 0), xytext=(3.7, .55),
            arrowprops={'arrowstyle': '->', 'color': GREY}, color=GREY)
style(ax)
fig.text(.09, .075, '색칠한 부분도 실제 DAC가 출력한 면적입니다. DAC 평균을 0으로 맞추려면 ramp와 flat 모두 포함해야 합니다.',
         fontsize=12, fontweight='bold')
fig.text(.09, .033, '실제 RTL 시뮬레이션 데이터 · 독립적인 1차 아날로그 RC 모델 · τ = 10 µs · ±800 mV 환산 기준',
         fontsize=10, color=GREY)
save(fig, '01_single_repeat_explained')

# End of every shot, sampled after its end marker and before the next start.
with (BASE/'rtl_gpio.csv').open() as f:
    markers = [int(r['cycle']) for r in csv.DictReader(f) if int(r['value'],16) != 0]
assert len(markers) == 400
ends = np.array(markers[1::2])
sample_cycles = ((ends+11)//4)*4
final_end = ends[-1]
fig, axes = plt.subplots(2, 2, figsize=(12.8, 8.2))
fig.subplots_adjust(left=.085, right=.96, bottom=.15, top=.81, hspace=.6, wspace=.29)
fig.suptitle('② 반복 종료 후: 남는 DAC 전압이 반복 중 누적됨',
             fontsize=20, fontweight='bold', y=.97)
fig.text(.5, .915, '왼쪽: 매 반복을 끝낸 뒤의 DAC 값     |     오른쪽: 200번째 반복 종료 후 확대',
         ha='center', fontsize=13)
export = []
for ch, d in enumerate(channels):
    lookup = {int(row['cycle']): row for row in d}
    after_shots = np.array([lookup[int(c)] for c in sample_cycles], dtype=d.dtype)
    assert np.all(after_shots['target'] == 0)
    end_values = after_shots['dac']*scale
    final_mv = d['dac'][-1]*scale
    ax = axes[ch, 0]
    ax.plot(np.arange(1, 201), end_values, color=ORANGE, lw=2)
    ax.plot(200, end_values[-1], 'o', color=RED, markersize=7)
    ax.text(.04, .88, f'200회 뒤: {final_mv:+.3f} mV', transform=ax.transAxes,
            color=RED, fontweight='bold', fontsize=14)
    ax.set(title=f'AWG {ch+1} · 각 반복 종료 시점', xlabel='반복 횟수', xlim=(1, 204))
    ax.set_ylim((-1.4, .35) if ch == 0 else (-.25, 1.4))
    style(ax)
    ax = axes[ch, 1]
    rel_t = (d['cycle']-final_end)/300
    m = (rel_t >= 0) & (rel_t <= 6.5)
    ax.plot(rel_t[m], d['dac'][m]*scale, color=ORANGE, lw=2.5, label='DAC 출력')
    ax.plot(rel_t[m], d['target'][m]*scale, color=BLUE, lw=1.8, label='목표 0 mV')
    ax.plot(rel_t[m], d['after_rc'][m]*scale, color=GREEN, ls='--', lw=1.7, label='RC 뒤 전압')
    ax.text(3, final_mv+(.14 if ch == 0 else -.3), f'DAC: {final_mv:+.3f} mV',
            ha='center', color=ORANGE, fontweight='bold')
    ax.text(3, .17 if ch == 0 else -.28, 'RC 뒤는 약 0 mV', ha='center', color=GREEN)
    ax.set(title=f'AWG {ch+1} · 200회 종료 후', xlabel='마지막 반복 종료 후 시간 (µs)',
           xlim=(0, 6.5), ylim=((-1.4, .4) if ch == 0 else (-.4, 1.4)))
    style(ax)
    if ch == 0:
        handles, labels = ax.get_legend_handles_labels()
        fig.legend(handles, labels, loc='center', bbox_to_anchor=(.72, .86),
                   ncol=3, fontsize=10, frameon=False)
    export.append({'channel': ch+1, 'end_values_mv': end_values.tolist()})
fig.text(.085, .075, '中間 offset과 달리, 이 잔류값은 DC 보상 후에도 남은 작은 면적 오차가 누적된 결과입니다.'.replace('中間', '중간'),
         fontsize=12, fontweight='bold')
fig.text(.085, .032, '실제 RTL 데이터 · 100 sweep points × 2 repeats · 초록은 독립 RC 모델 결과이며 실물 계측값은 아닙니다.',
         fontsize=10, color=GREY)
save(fig, '02_residual_accumulation_explained')
(OUT/'repeat_end_values.json').write_text(json.dumps(export, indent=2))
print(str(OUT/'01_single_repeat_explained.png'))
print(str(OUT/'02_residual_accumulation_explained.png'))
