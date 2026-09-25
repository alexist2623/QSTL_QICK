"""Independent two-AWG oracle, requested-point error, and full-DUT equivalence."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from check_awg_request import dac_code,trunc_div,nearest_div,signed

HERE=Path(__file__).resolve().parent


def rows(path):
    with path.open() as f:return list(csv.DictReader(f))


def make_plan(meta):
    """Compute the affine integer sweep from its public voltage/time rules."""
    table=meta['table'];fs=meta['full_scale_mv'];axes=meta['axes']
    baseline={g:[dac_code(row[2+i],fs) for row in table] for i,g in enumerate(meta['channels'])}
    endpoint={g:list(v) for g,v in baseline.items()}
    for axis in axes:
        baseline[axis['gen']][3]=dac_code(axis['start_mv'],fs)
        endpoint[axis['gen']][3]=dac_code(axis['stop_mv'],fs)
    segment_starts=[];relative=[];elapsed=0
    for row,(ramp,flat,*_) in enumerate(table):
        if row:
            duration=round(ramp*300)
            relative.append(dict(row=row,kind='ramp',time=elapsed-7,
                                 start=elapsed,duration=duration))
            elapsed+=duration+1
        segment_starts.append(elapsed)
        relative.append(dict(row=row,kind='set',time=elapsed,start=elapsed,duration=0))
        elapsed+=round(flat*300)
    # No SquarePulse command in this case. Marker preparation adds 128 clocks
    # to the original 128-clock initialization lead.
    initial=256;marker_end=elapsed+20;period=marker_end+112
    commands=[];points=[]
    for ix in range(10):
        for iy in range(10):
            index=ix*10+iy;start=initial+index*period
            for output,gen in enumerate(meta['channels']):
                axis=axes[output];coordinate=(ix,iy)[output]
                requested=axis['start_mv']+(axis['stop_mv']-axis['start_mv'])*coordinate/9
                direct=dac_code(requested,fs)
                b=baseline[gen];e=endpoint[gen]
                def target(row):return b[row]+coordinate*nearest_div(e[row]-b[row],9*4)*4
                p=dict(point=index,x=ix,y=iy,gen=gen,requested_mv=requested,
                       direct_code=direct,affine_code=target(3),code_error=target(3)-direct,
                       actual_mv=target(3)*fs/32768,
                       voltage_error_mv=target(3)*fs/32768-requested,
                       set3_schedule=start+segment_starts[3])
                points.append(p)
                for spec in relative:
                    row=spec['row'];n=spec['duration']*16
                    if spec['kind']=='ramp':
                        bs=trunc_div((b[row]-b[row-1])*65536,n-1)
                        es=trunc_div((e[row]-e[row-1])*65536,n-1)
                        step=bs+coordinate*nearest_div(es-bs,9)
                    else:step=0
                    commands.append(dict(point=index,gen=gen,row=row,kind=spec['kind'],
                        schedule=start+spec['time'],output_time=start+spec['start'],
                        target=target(row),start=target(row-1) if row else 0,
                        duration=n,step=step))
    commands.sort(key=lambda c:(c['schedule'],c['gen']))
    return commands,points,period,marker_end,relative


def reconstruct(trace,key,end):
    result=np.zeros((end,16),dtype=np.int16)
    for index,row in enumerate(trace):
        begin=int(row['cycle']);finish=int(trace[index+1]['cycle']) if index+1<len(trace) else end
        word=int(row[key],16)
        result[begin:min(end,finish)]=[signed(word>>(16*lane)&65535,16) for lane in range(16)]
    return result


def reference(commands,gen,end,origin):
    """Generate scalar samples without decoding the actual or model commands."""
    refs=[c for c in commands if c['gen']==gen]
    result=np.zeros(end*16,dtype=np.int16);ramps=[]
    for index,c in enumerate(refs):
        cycle=origin+c['output_time']+14
        if cycle>=end:break
        next_cycle=origin+refs[index+1]['output_time']+14 if index+1<len(refs) else end
        # Each command owns its segment through the next command's visible
        # effect. RAMP endpoint is held during the following guard interval.
        result[cycle*16:min(end,next_cycle)*16]=c['target']
        if c['kind']=='ramp':
            k=np.arange(c['duration'],dtype=np.int64)
            values=((c['start']*65536+k*c['step'])>>16)&~3
            values=np.clip(values,-32768,32764);values[-1]=c['target']
            count=min(len(values),len(result)-cycle*16)
            result[cycle*16:cycle*16+count]=values[:count]
            lower=min(c['start'],c['target']);upper=max(c['start'],c['target'])
            overshoot=max(0,int(values.max())-upper,lower-int(values.min()))
            ideal=c['start']+(c['target']-c['start'])*k/(c['duration']-1)
            ramps.append(dict(point=c['point'],gen=gen,row=c['row'],
                              overshoot_codes=overshoot,
                              max_line_error_codes=float(np.max(np.abs(values-ideal)))))
    return result.reshape(end,16),ramps


def analyze(directory,meta,full=False):
    log=directory/('full' if full else 'focus')
    checks=dict(line.split('=') for line in (log/'rtl_checks.txt').read_text().splitlines())
    events=rows(log/'rtl_events.csv');received=rows(log/'rtl_commands.csv')
    trace=rows(log/'rtl_samples.csv');gpio=rows(log/'rtl_gpio.csv')
    end=int(checks['end_cycle']);origins={int(r['cycle'])-int(r['tproc_time']) for r in events}
    assert len(origins)==1,origins
    origin=origins.pop();errors=[]
    if int(checks['errors']):errors.append('Unknown RTL AWG samples')
    if meta['model_conflicts']:errors.append('Compiler instruction model scheduling conflict')
    plan,points,period,marker_end,relative=make_plan(meta)
    timing=[]
    for port in [0,1,7]:
        expected=[e for e in meta['events'] if e['port']==port and e['cycle']+origin+1<end]
        observed=[r for r in events if int(r['port'])==port]
        if len(expected)!=len(observed):errors.append(f'Port {port} count {len(observed)} != {len(expected)}')
        for index,(e,o) in enumerate(zip(expected,observed)):
            delta=int(o['tproc_time'])-e['cycle']
            timing.append(dict(port=port,event=index,expected=e['cycle'],actual=int(o['tproc_time']),delta=delta))
            if delta!=1 or int(o['word'],16)!=int(e['word'],16):errors.append(f'Port {port} command {index} mismatch')
    wanted=[c for c in plan if c['schedule']+origin+4<end]
    for gen in meta['channels']:
        actual=[r for r in received if int(r['gen'])==gen]
        desired=[c for c in wanted if c['gen']==gen]
        if len(actual)!=len(desired):errors.append(f'Gen {gen} command count mismatch')
        for index,(c,r) in enumerate(zip(desired,actual)):
            word=int(r['word'],16)
            fields=(word>>144&3,signed(word&0xffffffff,32),word>>64&0x7fffff,signed(word>>96&0xffffff,24))
            requested=(1 if c['kind']=='set' else 2,c['target'],c['duration'],c['step'])
            if fields!=requested or int(r['cycle'])!=c['schedule']+origin+4:
                errors.append(f'Gen {gen} command {index}: received {fields} at {r["cycle"]}, expected {requested} at {c["schedule"]+origin+4}')
    per_gen={};ramps=[]
    for gen in meta['channels']:
        expected,r=reference(plan,gen,end,origin);ramps.extend(r)
        actual=reconstruct(trace,'awg'+str(gen),end)
        mismatch=np.argwhere(actual[17:]!=expected[17:])
        if len(mismatch):errors.append(f'Gen {gen}: {len(mismatch)} scalar DAC mismatches')
        for point in points:
            if point['gen']!=gen:continue
            cycle=point['set3_schedule']+origin+14
            if cycle<end:point['observed_code']=int(actual[cycle,0])
        per_gen[str(gen)]=dict(samples=(end-17)*16,mismatches=len(mismatch),
                              examples=(mismatch[:8]+[17,0]).tolist())
    # GPIO includes one rising/falling pair at each point's start and end.
    wanted_gpio=[]
    for point in range(100):
        start=256+point*period
        for offset,value in [(0,64),(111,0),(marker_end,64),(marker_end+111,0)]:
            cycle=origin+start+offset+1
            if cycle<end:wanted_gpio.append((cycle,value))
    actual_gpio=[(int(r['cycle']),int(r['value'],16)) for r in gpio]
    if actual_gpio!=wanted_gpio:errors.append('Marker edges disagree with independent point schedule')
    marker_lateness=[actual[0]-wanted[0] for actual,wanted in zip(actual_gpio,wanted_gpio)]
    marker_widths=[actual_gpio[i+1][0]-actual_gpio[i][0] for i in range(0,len(actual_gpio)-1,2)]
    with (log/'point_values.csv').open('w',newline='') as f:
        fields=list(points[0]);w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(points)
    with (log/'command_timing.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(timing[0]));w.writeheader();w.writerows(timing)
    observed_points=[p for p in points if 'observed_code' in p]
    if any(p['code_error'] for p in observed_points):
        errors.append('Requested plateau codes differ from individually rounded sweep points')
    if any(r['overshoot_codes'] for r in ramps):
        errors.append('RAMP samples leave the interval between their quantized endpoints')
    result=dict(passed=not errors,errors=errors,variant='full_prefix' if full else 'focused_100_points',
        origin=origin,end_cycle=end,end_required=int(checks['end_required']),
        program_commands=len(events),awg_commands=len(received),channels=per_gen,
        point_count=len(observed_points)//2,point_period_cycles=period,point_period_us=period/300,
        marker_edges=len(gpio),processor_delta_cycles=sorted({r['delta'] for r in timing}),
        literal_table_duration_us=sum(row[0]+row[1] for row in meta['table']),
        scheduled_waveform_duration_us=(marker_end-20)/300,
        hardware_matches_affine_sweep=not any(e.startswith('Gen ') for e in errors),
        marker_edges_late=sum(v!=0 for v in marker_lateness),
        marker_lateness_cycles=sorted(set(marker_lateness)),
        marker_width_cycles={str(w):marker_widths.count(w) for w in sorted(set(marker_widths))},
        strictly_matches_requested_set_codes=all(p['code_error']==0 for p in observed_points),
        max_requested_set_error_codes=max(abs(p['code_error']) for p in observed_points),
        max_requested_voltage_error_mv=max(abs(p['voltage_error_mv']) for p in observed_points),
        max_ramp_overshoot_codes=max(r['overshoot_codes'] for r in ramps),
        max_ramp_line_error_codes=max(r['max_line_error_codes'] for r in ramps),
        ramp_overshoot_examples=[r for r in ramps if r['overshoot_codes']][:12])
    (log/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return result


def equivalence(directory):
    f=json.loads((directory/'focus/comparison.json').read_text())
    a=json.loads((directory/'full/comparison.json').read_text())
    errors=[]
    for file in ['rtl_events.csv','rtl_commands.csv','rtl_gpio.csv']:
        expected=rows(directory/'focus'/file);actual=rows(directory/'full'/file)
        limit=a['end_cycle']-a['origin']
        def normalize(data,origin):
            return [dict(r,cycle=int(r['cycle'])-origin) for r in data
                    if int(r['cycle'])-origin<limit]
        if normalize(expected,f['origin'])!=normalize(actual,a['origin']):errors.append(file+' differs')
    ft=rows(directory/'focus/rtl_samples.csv');at=rows(directory/'full/rtl_samples.csv')
    # Both BFMs use identical host initialization; reject unexpected origin
    # changes instead of silently fitting channel latency.
    if f['origin']!=a['origin']:errors.append('Host initialization clock origins differ')
    for gen in (1,3):
        e=reconstruct(ft,'awg'+str(gen),a['end_cycle'])
        o=reconstruct(at,'awg'+str(gen),a['end_cycle'])
        if not np.array_equal(e,o):errors.append(f'Gen {gen} DAC full/focus mismatch')
    result=dict(passed=not errors,errors=errors,cycles=a['end_cycle'],
                samples_per_channel=a['channels']['1']['samples'],
                complete_points=a['point_count'],same_pmem=True,same_dmem=True)
    (directory/'full_focus_equivalence.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if errors:raise SystemExit(1)


def main():
    p=argparse.ArgumentParser();p.add_argument('--case',default='gui_complex_10x10')
    p.add_argument('--full',action='store_true');a=p.parse_args()
    directory=HERE/a.case;meta=json.loads((directory/'expected.json').read_text())
    result=analyze(directory,meta,a.full)
    if a.full:equivalence(directory)
    if not result['passed']:raise SystemExit(1)


if __name__=='__main__':main()
