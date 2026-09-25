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
BUILD=Path('C:/JeonghyunPark/Workspace/Vivado_Output/rc_three_level_tau300_20mv')
info=json.loads((OUT/'config.json').read_text())
trace=np.genfromtxt(BUILD/'waveform_rle.csv',delimiter=',',names=True,dtype=np.int64)
start=int(trace['sample'][np.flatnonzero(trace['target']==1228)[0]])
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

dc=np.flatnonzero(x<0)
dc_start=float(t0[dc[0]]); dc_end=float(edges[dc[-1]+1])
end_value=evaluate([510-1/fs],last_states)[2][0]
error_start=u-last_states[:-1]-x
error_end=(u-last_states[:-1])*np.exp(-np.maximum(0,dt-1/fs)/tau)-x
max_error=float(max(np.max(abs(error_start)),np.max(abs(error_end))))
requested=np.select([d['target']==1228,d['target']==408,d['target']==820,d['target']<0],
                    [30.,10.,20.,-80.],default=0.)
input_error=float(max(np.max(abs(error_start+x-requested)),np.max(abs(error_end+x-requested))))
out={k:v for k,v in info.items() if k!='events'}
out.update(two_rtl_periods_identical=True,clipped=False,
    required_ideal_peak_dac_mv=57.,actual_peak_dac_mv=float(u.max()),actual_min_dac_mv=float(u.min()),
    final_segment_target_mv=float(x[(t0>=110)&(t0<510)][0]),final_segment_end_after_rc_mv=float(end_value),
    max_error_vs_quantized_target_mv=max_error,max_error_vs_input_target_mv=input_error,
    dc_actual_mv=float(x[dc[0]]),dc_start_us=dc_start,
    dc_end_us=dc_end,dc_duration_us=dc_end-dc_start,post_stop_output_mv=-boundaries[200],
    first_vs_200th_max_difference_mv=abs(boundaries[199]),final_nominal_area_mv_us=float(area[-1]),
    method='Two bit-identical production AWG RTL periods; exact ZOH analog RC state propagated for 200 repeats without resetting the capacitor.')
(OUT/'result.json').write_text(json.dumps(out,indent=2))
font_manager.fontManager.addfont('C:/Windows/Fonts/malgun.ttf')
font_manager.fontManager.addfont('C:/Windows/Fonts/malgunbd.ttf')
plt.rcParams.update({'font.family':'Malgun Gothic','font.size':11,'axes.unicode_minus':False,
    'axes.spines.top':False,'axes.spines.right':False})
BLUE,ORANGE,GREEN,GREY='#2261b7','#d36a06','#138653','#69788a'
fig,axes=plt.subplots(3,1,figsize=(12.5,12))
fig.subplots_adjust(left=.09,right=.97,top=.865,bottom=.10,hspace=.55)
fig.suptitle('전압을 1/10로 낮춘 경우 · 200번째 반복',fontsize=20,fontweight='bold',y=.987)
fig.text(.5,.937,'30 mV × 100 µs  →  10 mV × 10 µs  →  20 mV × 400 µs',ha='center',fontsize=15)
fig.text(.5,.905,'τ = 300 µs · DC 보상 -80 mV · 매 반복 IIR reset · DAC 범위 ±800 mV',ha='center',color=GREY)
times=np.unique(np.r_[np.linspace(0,510,16000),t0[(t0>=0)&(t0<510)]])
target,dac,after,needed=evaluate(times,last_states)
ideal=np.where(times<100,30.,np.where(times<110,10.,np.where(times<510,20.,0.)))
ax=axes[0]
ax.plot(times,ideal,color=BLUE,lw=2.5,label='입력 목표 전압')
ax.plot(times,after,color=GREEN,lw=1.5,ls='--',label='RC 통과 후 전압')
ax.annotate(f'마지막 20 mV 구간 끝\n{end_value:.4f} mV',xy=(509.9,end_value),xytext=(320,30),
    color=GREEN,arrowprops={'arrowstyle':'->','color':GREEN})
ax.set(title='실험 구간: RC 통과 후 목표 전압 유지',xlim=(0,510),ylim=(-3,38),ylabel='전압 (mV)',xlabel='마지막 반복 시작 후 시간 (µs)')
ax.legend(loc='lower center',ncol=2,frameon=False)
ax=axes[1]
whole=np.unique(np.r_[np.linspace(0,edges[-1]+900,20000),t0,edges[-1]])
target,dac,after,needed=evaluate(whole,last_states)
ax.axvspan(dc_start,dc_end,color='#dbe8f6',alpha=.7)
ax.plot(whole,target,color=BLUE,lw=1.6,label='목표 (DC 보상 포함)')
ax.plot(whole,dac,color=ORANGE,lw=1.8,label='실제 RTL DAC 출력')
ax.plot(whole,after,color=GREEN,ls='--',lw=1.5,label='RC 통과 후 전압')
ax.annotate(f'DAC 최고 {u.max():.4f} mV\n포화 없음',xy=(509.9,u.max()),xytext=(270,80),
    color=ORANGE,arrowprops={'arrowstyle':'->','color':ORANGE})
ax.text(dc_end+50,-55,f'DC 보상 {dc_end-dc_start:.3f} µs\n목표 {x[dc[0]]:.3f} mV',color=BLUE)
ax.axvline(edges[-1],color=GREY,ls=':')
ax.text(edges[-1]+25,30,'반복 종료 / IIR reset\nDAC = 0',color=GREY)
ax.set(title='마지막 반복 전체: RC 보정 출력과 DC 보상 펄스',xlim=(0,edges[-1]+350),ylim=(-95,105),ylabel='전압 (mV)',xlabel='마지막 반복 시작 후 시간 (µs)')
ax.legend(loc='upper right',fontsize=9,frameon=False)
ax=axes[2]
tail=np.linspace(0,900,6000)
tail_rc=-last_states[-1]*np.exp(-tail/tau)
ax.plot(tail,np.zeros_like(tail),color=ORANGE,lw=1.6,label='DAC 출력 = 0')
ax.plot(tail,tail_rc*1000,color=GREEN,lw=1.8,label='RC 통과 후 잔류 전압')
ax.text(.98,.52,f'종료 직후 {(-last_states[-1]*1000):+.3f} µV\nRC = 300 µs로 감쇠',
    transform=ax.transAxes,ha='right',color=GREEN,fontsize=13)
ax.set(title='종료 직후 확대: 디지털 초기화 뒤에도 커패시터 전압은 남음',xlim=(0,900),ylabel='전압 (µV)',xlabel='마지막 반복 종료 후 시간 (µs)')
ax.legend(loc='upper right',frameon=False,fontsize=10)
for ax in axes:
    ax.axhline(0,color=GREY,lw=.7,zorder=0); ax.grid(alpha=.15)
fig.text(.09,.052,'실제 AWG RTL 2주기의 출력 일치 확인 → 아날로그 RC 상태를 유지하며 200회 연속 계산.',fontsize=10,color=GREY)
fig.text(.09,.029,f'입력 목표 대비 최대 오차: {input_error:.4f} mV (DAC 양자화 포함). 실물 측정이 아닌 시뮬레이션입니다.',fontsize=10,color=GREY)
for ext in ('png','pdf'): fig.savefig(OUT/f'last_repeat.{ext}',dpi=160)
plt.close(fig)
np.savez_compressed(OUT/'last_repeat.npz',time_us=whole,target_mv=target,dac_mv=dac,after_rc_mv=after)
shutil.copyfile(BUILD/'waveform_rle.csv',OUT/'waveform_rle.csv')
print(json.dumps(out,indent=2))
