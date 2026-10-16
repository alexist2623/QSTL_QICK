"""Analyze full captured traces without gain/offset correction or per-point fitting."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True)
    args=parser.parse_args();run=HERE/args.run
    meta=json.loads((run/'scope_capture/capture.json').read_text())
    expected=json.loads((HERE/'offline_prepared_retry1/expected_points.json').read_text())
    state=json.loads((run/'status.json').read_text())
    data={}
    for ch in (1,2):
        with np.load(run/f'scope_capture/ch{ch}.npz',allow_pickle=False) as f:
            data[ch]={k:f[k].copy() for k in f.files}
    # One alignment anchor, used ONLY to locate plateau windows. Do not fit
    # per-point shifts, amplitudes, offsets, or change the stored time arrays.
    t=data[2]['time_s'];v=data[2]['voltage_v']
    ii=np.where((v[:-1]<.1)&(v[1:]>=.1)&(np.abs(t[:-1])<.0001))[0]
    if not len(ii):raise RuntimeError('No CH2 100 mV rising crossing near scope trigger')
    j=ii[np.argmin(np.abs(t[ii]))]
    crossing=t[j]+(.1-v[j])*(t[j+1]-t[j])/(v[j+1]-v[j])
    anchor=expected['points'][1]['outputs'][1]
    fraction=.1/(anchor['quantized_mv']/1000.)
    expected_crossing_us=anchor['hold_digital_output_us']-1.+fraction
    offset_s=float(crossing-expected_crossing_us*1e-6)
    rows=[]
    for point in expected['points']:
        for ch,o in zip((1,2),point['outputs']):
            start=o['hold_digital_output_us']*1e-6+offset_s
            end=o['hold_end_digital_output_us']*1e-6+offset_s
            tt=data[ch]['time_s'];vv=data[ch]['voltage_v']
            mask=(tt>=start+.25*(end-start))&(tt<=end-.25*(end-start))
            values=vv[mask]*1000.
            if len(values)<100 or not np.isfinite(values).all():
                raise RuntimeError(f'Point {point["point_index"]} CH{ch} missing/invalid plateau')
            measured=float(np.median(values));err=measured-o['quantized_mv']
            # Explicit engineering screening criterion, not a calibrated scope
            # uncertainty budget or hardware accuracy specification.
            limit=5.+.02*abs(o['quantized_mv'])
            rows.append(dict(point=point['point_index'],axis0=point['axis_indices'][0],
                axis1=point['axis_indices'][1],scope_channel=ch,panel_dac=o['panel_dac'],
                generator=o['awg_gen'],requested_mv=o['requested_mv'],
                quantized_nominal_mv=o['quantized_mv'],measured_median_mv=measured,
                measured_mean_mv=float(values.mean()),noise_std_mv=float(values.std()),
                min_mv=float(values.min()),max_mv=float(values.max()),error_mv=err,
                screening_limit_mv=limit,within_screening_limit=bool(abs(err)<=limit),
                samples=len(values),hold_start_scope_s=start,hold_end_scope_s=end))
    with (run/'plateau_measurements.csv').open('x',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    tails={}
    last_zero_s=expected['last_output_zero_us']*1e-6+offset_s
    for ch in (1,2):
        tt=data[ch]['time_s'];vv=data[ch]['voltage_v']
        q=vv[(tt>=last_zero_s+.0001)&(tt<=last_zero_s+.0005)]*1000.
        if len(q)<100 or not np.isfinite(q).all():raise RuntimeError('Missing final zero evidence')
        tails[ch]=dict(median_mv=float(np.median(q)),std_mv=float(q.std()),samples=len(q),
                       within_5mv=bool(abs(np.median(q))<=5.))
    result=dict(status='measured',physical_points=9,measured_plateaus=len(rows),
        capture_id=meta['capture_id'],same_acquisition=meta['same_acquisition'],
        run_acquisition_success=state['acquisition_success'],
        all_plateaus_within_screening_limit=all(r['within_screening_limit'] for r in rows),
        max_absolute_nominal_error_mv=max(abs(r['error_mv']) for r in rows),
        final_zero=tails,alignment_offset_s=offset_s,
        alignment='One CH2 threshold crossing locates windows only; no gain/offset corrections or per-point timing fits.',
        acceptance='Basic engineering screen: |median - quantized nominal| <= 5 mV + 2% of nominal. Not a calibrated accuracy certification.',
        timing_limit='No fine timing or channel skew acceptance test; native channel time grids retained.',
        rows=rows)
    result['basic_check_passed']=bool(result['all_plateaus_within_screening_limit'] and
        all(x['within_5mv'] for x in tails.values()) and state['acquisition_success'])
    (run/'analysis.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    fig,axes=plt.subplots(3,1,figsize=(14,10),constrained_layout=True)
    colors=['#1f77b4','#d95f02']
    for ch,color in zip((1,2),colors):
        a=axes[ch-1];tt=data[ch]['time_s'];vv=data[ch]['voltage_v']
        # Decimate display only. Full-resolution samples remain in NPZ/raw files.
        stride=max(1,len(tt)//60000)
        a.plot(tt[::stride]*1000,vv[::stride]*1000,color=color,lw=.7,label=f'Scope CH{ch}: DAC{ch+3}')
        for r in [r for r in rows if r['scope_channel']==ch]:
            a.hlines(r['quantized_nominal_mv'],r['hold_start_scope_s']*1000,r['hold_end_scope_s']*1000,
                     colors='black',linestyles='--',lw=.9)
            a.text((r['hold_start_scope_s']+r['hold_end_scope_s'])*500,r['measured_median_mv']+25,
                   str(r['point']),ha='center',fontsize=9)
        a.set_ylabel('Voltage (mV)');a.set_xlabel('Scope time relative to trigger (ms)');a.grid(alpha=.25);a.legend()
    for ch,color in zip((1,2),colors):
        r=[q for q in rows if q['scope_channel']==ch]
        axes[2].plot([q['point'] for q in r],[q['measured_median_mv'] for q in r],'.-',color=color,label=f'CH{ch} measured')
        axes[2].plot([q['point'] for q in r],[q['quantized_nominal_mv'] for q in r],'x--',color=color,alpha=.6,label=f'CH{ch} nominal')
    axes[2].set_xlabel('Cartesian point index (axis 2 varies fastest)');axes[2].set_ylabel('Plateau voltage (mV)');axes[2].grid(alpha=.25);axes[2].legend(ncol=2)
    fig.suptitle('Physical two-axis voltage sweep: DAC4 / DAC5, 0 / 200 / 400 mV\nSingle oscilloscope acquisition; dashed traces are nominal levels')
    fig.savefig(run/'voltage_sweep.png',dpi=170);plt.close(fig)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))

if __name__=='__main__':main()
