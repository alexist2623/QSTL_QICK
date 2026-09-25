"""Exact ZOH RC propagation of the RTL-verified periodic DAC waveform."""
from pathlib import Path
import json
import math
import shutil

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

OUT=Path(__file__).resolve().parent
BUILD=Path('C:/JeonghyunPark/Workspace/Vivado_Output/rc_three_level_tau300')
info=json.loads((OUT/'config.json').read_text())
trace=np.genfromtxt(BUILD/'waveform_rle.csv',delimiter=',',names=True,dtype=np.int64)
start=int(trace['sample'][np.flatnonzero(trace['target']==12288)[0]])
N=info['period_cycles']*16
periods=[]
for k in (0,1):
    m=(trace['sample']>=start+k*N)&(trace['sample']<start+(k+1)*N)
    values=trace[m].copy();values['sample']-=start+k*N
    periods.append(values)
assert np.array_equal(periods[0],periods[1]), 'The two actual RTL periods must match bit-for-bit.'
d=periods[0]
scale=800/32768
fs=4800.
tau=300.
t0=d['sample']/fs
edges=np.append(t0,N/fs)
dt=np.diff(edges)
u=d['dac']*scale
x=d['target']*scale
a=np.exp(-dt/tau)

def propagate(initial):
    state=np.empty(len(u)+1)
    state[0]=initial
    for i in range(len(u)):
        state[i+1]=a[i]*state[i]-math.expm1(-dt[i]/tau)*u[i]
    return state

b=propagate(0.)[-1]
period_decay=math.exp(-edges[-1]/tau)
state=0.
boundaries=[state]
for repetition in range(200):
    state=period_decay*state+b
    boundaries.append(state)
last_states=propagate(boundaries[199])
first_states=propagate(0.)
assert abs(last_states[-1]-boundaries[200])<1e-9
area=np.r_[0.,np.cumsum(x*dt)]

def evaluate(times, states):
    times=np.asarray(times,dtype=float)
    indices=np.clip(np.searchsorted(t0,times,side='right')-1,0,len(u)-1)
    age=times-t0[indices]
    after=(u[indices]-states[indices])*np.exp(-age/tau)
    nominal=x[indices].copy()
    dac=u[indices].copy()
    needed=nominal+(area[indices]+nominal*age)/tau
    stopped=times>=edges[-1]
    after[stopped]=-states[-1]*np.exp(-(times[stopped]-edges[-1])/tau)
    nominal[stopped]=0;dac[stopped]=0;needed[stopped]=0
    return nominal,dac,after,needed

rail=32764*scale
clip_intervals=np.flatnonzero(d['dac']==32764)
clip_start=float(t0[clip_intervals[0]])
clip_end=float(edges[clip_intervals[-1]+1])
dc=np.flatnonzero(x<0)
dc_start=float(t0[dc[0]]);dc_end=float(edges[dc[-1]+1])
at_end=evaluate([510-1/fs],last_states)
at_start=evaluate([0],last_states)
out=dict(info)
out.pop('events')
out.update(two_rtl_periods_identical=True,
           independent_rc_method='Exact zero-order-hold RC state update; the identical RTL period is propagated 200 times without analog reset.',
           dc_actual_mv=float(x[dc[0]]),dc_start_us=dc_start,dc_end_us=dc_end,
           dc_duration_us=dc_end-dc_start,dac_positive_rail_mv=rail,
           clipping_start_us=clip_start,clipping_end_us=clip_end,
           required_peak_dac_mv=600+271000/300,
           last_600mv_segment_end_mv=float(at_end[2][0]),
           last_first_segment_start_mv=float(at_start[2][0]),
           capacitor_at_last_repeat_start_mv=boundaries[199],
           capacitor_after_last_repeat_mv=boundaries[200],
           post_stop_output_mv=-boundaries[200],
           first_vs_200th_max_difference_mv=abs(boundaries[199]),
           final_nominal_area_mv_us=float(area[-1]))
(OUT/'result.json').write_text(json.dumps(out,indent=2))

font_manager.fontManager.addfont('C:/Windows/Fonts/malgun.ttf')
font_manager.fontManager.addfont('C:/Windows/Fonts/malgunbd.ttf')
plt.rcParams.update({'font.family':'Malgun Gothic','font.size':12,
    'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False})
BLUE,ORANGE,GREEN,GREY,RED='#2261b7','#d36a06','#138653','#69788a','#b52735'
fig,axes=plt.subplots(3,1,figsize=(12.5,12))
fig.subplots_adjust(left=.085,right=.97,top=.87,bottom=.105,hspace=.55)
fig.suptitle('200번째 반복의 파형 · RC 시정수 τ = 300 µs',fontsize=21,fontweight='bold',y=.974)
fig.text(.5,.935,'목표: 300 mV × 100 µs  →  100 mV × 10 µs  →  600 mV × 400 µs',
         ha='center',fontsize=14)
fig.text(.5,.903,'DC 보상 켬 (-80 mV 고정) · 매 반복 IIR reset · DAC 범위 ±800 mV',
         ha='center',fontsize=12,color=GREY)
times=np.unique(np.r_[np.linspace(-.1,650,25000),t0[(t0>=0)&(t0<650)],100,110,510])
times=times[times>=0]
target,dac,after,needed=evaluate(times,last_states)

ax=axes[0]
ax.plot(times,target,color=BLUE,lw=2,label='회로 뒤 목표 전압')
ax.plot(times,after,color=GREEN,lw=2,label='RC 통과 후 전압 (200번째)')
m=(times>=110)&(times<510)
ax.fill_between(times[m],target[m],after[m],color=RED,alpha=.12)
ax.axvline(clip_start,color=RED,ls=':',lw=1.2)
ax.annotate(f'DAC 상한 도달\n{clip_start:.2f} µs',xy=(clip_start,600),xytext=(205,420),
            color=RED,arrowprops={'arrowstyle':'->','color':RED})
ax.annotate(f'600 mV 구간 끝: {after[np.searchsorted(times,510)-1]:.1f} mV',
            xy=(509.9,at_end[2][0]),xytext=(285,75),color=GREEN,
            arrowprops={'arrowstyle':'->','color':GREEN})
ax.set(title='실험 구간 확대: 목표 600 mV가 끝까지 유지되지 않음',
       xlim=(0,650),ylim=(-120,760),ylabel='전압 (mV)',xlabel='마지막 반복 시작 후 시간 (µs)')
ax.legend(loc='upper right',fontsize=10,frameon=False)

ax=axes[1]
ax.plot(times,needed,color=GREY,ls='--',lw=1.7,label='출력 제한이 없다면 필요한 DAC 전압')
ax.plot(times,dac,color=ORANGE,lw=2.2,label='실제 RTL DAC 출력')
ax.axhline(rail,color=RED,ls=':',lw=1.1)
ax.text(8,rail+45,f'DAC 상한: {rail:.1f} mV',color=RED,fontsize=11)
ax.annotate('필요한 최고 전압: 1503.3 mV',xy=(509.9,1503.3),xytext=(230,1250),
            arrowprops={'arrowstyle':'->','color':GREY},color=GREY)
ax.set(title='원인: RC 보정을 더하면 DAC 출력 범위를 초과함',
       xlim=(0,650),ylim=(-70,1700),ylabel='전압 (mV)',xlabel='마지막 반복 시작 후 시간 (µs)')
ax.legend(loc='upper left',fontsize=10,frameon=False)

ax=axes[2]
whole=np.unique(np.r_[np.linspace(0,edges[-1]+900,20000),t0,edges[-1]])
target,dac,after,needed=evaluate(whole,last_states)
ax.axvspan(dc_start,dc_end,color='#dbe8f6',alpha=.55)
ax.plot(whole,target,color=BLUE,lw=1.7,label='목표 (DC 보상 포함)')
ax.plot(whole,dac,color=ORANGE,lw=1.8,label='DAC 출력')
ax.plot(whole,after,color=GREEN,lw=1.5,ls='--',label='RC 뒤 전압')
ax.text(2300,480,f'DC 보상 구간\n{dc_end-dc_start:.2f} µs · {x[dc[0]]:.2f} mV',
        ha='center',color=BLUE,fontsize=12)
ax.axvline(edges[-1],color=GREY,ls=':',lw=1.2)
ax.text(edges[-1]+60,250,'마지막 반복 종료\nDAC = 0',color=GREY,fontsize=11)
ax.set(title='마지막 반복 전체와 종료 후: DC 보상 펄스까지 포함',
       xlim=(0,edges[-1]+900),ylim=(-160,1000),ylabel='전압 (mV)',xlabel='마지막 반복 시작 후 시간 (µs)')
ax.legend(loc='upper right',fontsize=9,frameon=False,ncol=3)
for ax in axes:
    ax.axhline(0,color=GREY,lw=.8,zorder=0);ax.grid(alpha=.15)
fig.text(.085,.054,'DAC: 실제 AWG IP RTL 2주기의 동일 출력 확인. RC: 커패시터 상태를 유지한 채 200회 연속 계산.',
         fontsize=10,color=GREY)
fig.text(.085,.029,'실물 계측이 아닌 시뮬레이션입니다. IIR reset은 아날로그 커패시터 전압을 초기화하지 않습니다.',
         fontsize=10,color=GREY)
for ext in ('png','pdf'):
    fig.savefig(OUT/f'last_repeat.{ext}',dpi=160)
plt.close(fig)
np.savez_compressed(OUT/'last_repeat.npz',time_us=whole,target_mv=target,dac_mv=dac,after_rc_mv=after)
shutil.copyfile(BUILD/'waveform_rle.csv',OUT/'waveform_rle.csv')
print(json.dumps(out,indent=2))
