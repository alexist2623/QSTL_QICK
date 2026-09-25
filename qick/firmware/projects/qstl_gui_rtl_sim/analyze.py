"""Check GUI schedule versus actual processor/routing/output/capture traces."""
import argparse
import csv
import json
from pathlib import Path
from collections import Counter
from itertools import product

HERE=Path(__file__).resolve().parent


def rows(path):
    with path.open() as f:return list(csv.DictReader(f))


def signed(x,n):return (x&((1<<(n-1))-1))-(x&(1<<(n-1)))


def main():
    p=argparse.ArgumentParser();p.add_argument('case');a=p.parse_args()
    d=HERE/a.case;meta=json.loads((d/'expected.json').read_text())
    actual=rows(d/'rtl_events.csv');cmds=rows(d/'rtl_commands.csv')
    epochs=rows(d/'rtl_epochs.csv')
    gui_start=next(int(r['cycle']) for r in epochs if r['kind']=='gui_start')
    gui_actual=[r for r in actual if int(r['cycle'])>=gui_start]
    errors=[];timing=[]
    if meta['model_conflicts']:errors.append('Instruction model reported scheduling conflicts')
    for port in range(8):
        expected=[r for r in meta['events'] if r['port']==port]
        observed=[r for r in gui_actual if int(r['port'])==port]
        if len(expected)!=len(observed):errors.append(f'Port {port}: {len(observed)} events, expected {len(expected)}')
        for n,(e,o) in enumerate(zip(expected,observed)):
            if int(e['word'],16)!=int(o['word'],16):errors.append(f'Port {port} event {n}: command word mismatch')
            # timed_ictrl compares time in WAIT_ST; transfer is the next edge.
            delta=int(o['tproc_time'])-e['cycle']
            timing.append(dict(port=port,event=n,expected=e['cycle'],actual=int(o['tproc_time']),delta=delta))
            if delta!=1:errors.append(f'Port {port} event {n}: time delta {delta}, expected 1')
    route={}
    for kind,port,dest in [('sqcmd',3,1),('awgcmd',0,1),('rfcmd',3,0)]:
        generated=[r for r in actual if int(r['port'])==port and int(r['word'],16)>>152==dest]
        received=[r for r in cmds if r['kind']==kind]
        if len(generated)!=len(received):errors.append(f'{kind}: routing lost/duplicated commands')
        deltas=[]
        for g,r in zip(generated,received):
            if g['word']!=r['word']:errors.append(f'{kind}: routed word mismatch')
            deltas.append(int(r['cycle'])-int(g['cycle']))
        route[kind]=dict(count=len(received),latency_cycles=sorted(set(deltas)))
        if deltas and set(deltas)!={3}:errors.append(f'{kind}: routing delay {set(deltas)}, expected 3 clocks')
    checks=dict(line.split('=') for line in (d/'rtl_checks.txt').read_text().splitlines())
    if int(checks['errors']):errors.append('Scalar DDS/DAC sample checker reported errors')
    gpio=rows(d/'rtl_gpio.csv');prev=0;rises=[];widths=[];rise=None
    gpio_source=[r for r in actual if int(r['port'])==7]
    gpio_latency=[]
    if len(gpio_source)!=len(gpio):errors.append('GPIO changed-event count differs from tProcessor commands')
    for event,output in zip(gpio_source,gpio):
        if (int(event['word'],16)&127)!=int(output['value'],16):errors.append('GPIO output word mismatch')
        gpio_latency.append(int(output['cycle'])-int(event['cycle']))
    if gpio_latency and set(gpio_latency)!={0}:errors.append(f'GPIO latency {set(gpio_latency)}, expected zero extra clocks')
    for row in gpio:
        value=int(row['value'],16);c=int(row['cycle'])
        if value&64 and not prev&64:rise=c;rises.append(c)
        if prev&64 and not value&64:
            widths.append(c-rise)
        prev=value
    ncaptures=sum(bool(int(e['word'],16)&32) for e in meta['events'] if e['port']==7)
    nshots=ncaptures
    if 'awg_request' in meta:
        request=meta['awg_request']
        nshots=len(request['amplitude_mv'])*len(request['hold_us'])*len(request['ramp_us'])*request['repetitions']
    nmarkers=nshots*2 if meta['trigger']['scope']=='loop' else 2
    if len(widths)!=nmarkers or set(widths)!={111}:errors.append(f'Markers: widths {widths}, expected {nmarkers} x 111')
    cap=rows(d/'rtl_capture.csv');accept=[int(r['cycle']) for r in cap if r['kind']=='accept']
    mature=[int(r['cycle']) for r in cap if r['kind']=='mature']
    capture_samples=[r for r in cap if r['kind']=='sample']
    delay=[m-s for s,m in zip(accept,mature)]
    if len(delay)!=ncaptures or (ncaptures and set(delay)!={8712}):errors.append(f'DDR trigger compensation {delay}')
    ddr=rows(d/'rtl_ddr.csv');memory=[]
    for i,row in enumerate(ddr):
        word=int(row['data'],16)
        if int(row['address'],16)!=i*32:errors.append(f'DDR address at beat {i}')
        if int(row['strobe'],16)!=0xffffffff:errors.append(f'DDR strobe at beat {i}')
        memory.extend([word&((1<<128)-1),word>>128])
    source=[int(r['iq'],16) for r in capture_samples]
    if len(source)!=ncaptures*8:errors.append(f'Captured {len(source)} samples, expected {ncaptures*8}')
    if memory!=source:errors.append('DDR packed IQ differs from captured FIR output')
    # FIR CSV is sampled after its output register changes; the downstream
    # AXIS transfer consumes that word at the following rising edge.
    fir_transfers=[(int(r['cycle'])+1,int(r['iq'],16)) for r in rows(d/'rtl_fir.csv')]
    capture_alignment_errors=[]
    for shot,deadline in enumerate(mature):
        wanted=[r for r in fir_transfers if r[0]>=deadline][:8]
        observed=[(int(r['cycle']),int(r['iq'],16)) for r in capture_samples[shot*8:(shot+1)*8]]
        if wanted!=observed:capture_alignment_errors.append(shot)
    if capture_alignment_errors:errors.append(f'Capture did not start at the next FIR valid sample: shots {capture_alignment_errors}')
    # Decode AWG commands independently and compare every held/output word.
    # The CSV records every AWG output change; missing cycles hold the last word.
    from qick.sim import QickSim  # Install hardware-free import stubs only.
    from qick.awg_tuning import AwgTuningBehaviorModel
    waveform=rows(d/'rtl_samples.csv')
    awg_model=AwgTuningBehaviorModel(extra_y_pipe_stages=3)
    awg_commands={int(r['cycle']):int(r['word'],16) for r in cmds if r['kind']=='awgcmd'}
    awg_values={int(r['cycle']):int(r['awg'],16) for r in waveform}
    actual_word=0;model_pipe=[0]*10;awg_errors=[];awg_checks=0
    for cycle in range(int(checks['end_cycle'])):
        if cycle in awg_commands:awg_model.accept_command(cycle,awg_commands[cycle])
        predicted=model_pipe.pop(0);model_pipe.append(awg_model.step(cycle))
        actual_word=awg_values.get(cycle,actual_word)
        if cycle>16:
            awg_checks+=16
            if predicted!=actual_word and len(awg_errors)<8:awg_errors.append(cycle)
    if awg_errors:errors.append(f'AWG scalar reference mismatch at cycles {awg_errors}')
    if awg_model.dropped_commands:errors.append('AWG reference detected commands during busy RAMP')
    # Independently measure the actual RF DAC samples used by the ADC loopback.
    rf_intervals=[];rf_start=None;rf_words=[];first_rf=[];rf_peak=0
    for row in waveform:
        word=int(row['rf'],16);cycle=int(row['cycle'])
        if word:
            if rf_start is None:rf_start=cycle;rf_words=[]
            samples=[signed(word>>(16*k)&65535,16) for k in range(16)]
            rf_peak=max(rf_peak,max(abs(v) for v in samples))
            rf_words.append((cycle,samples))
        elif rf_start is not None:
            rf_intervals.append((rf_start,cycle))
            if not first_rf:first_rf=rf_words
            rf_start=None
    rf_durations=[end-start for start,end in rf_intervals]
    rf_accept=[int(r['cycle']) for r in cmds if r['kind']=='rfcmd']
    rf_latencies=[start-command for (start,end),command in zip(rf_intervals,rf_accept)]
    if len(set(rf_latencies))>1:errors.append(f'RF onset latency changed: {rf_latencies}')
    if len(rf_intervals)!=nshots or set(rf_durations)!={round(meta['rf']['duration_us']*300)}:
        errors.append(f'RF pulse durations/count: {rf_durations}')
    crossings=[];previous=None
    for cycle,samples in first_rf:
        for lane,value in enumerate(samples):
            index=cycle*16+lane
            if previous is not None and previous[1]<0<=value:
                crossings.append(previous[0]+(-previous[1])/(value-previous[1]))
            previous=(index,value)
    rf_frequency=(len(crossings)-1)*4800/(crossings[-1]-crossings[0]) if len(crossings)>1 else None
    if rf_frequency is None or abs(rf_frequency-meta['rf']['frequency_mhz'])>.01:
        errors.append(f'RF DAC frequency {rf_frequency} MHz')
    if abs(rf_peak-meta['rf']['gain'])>4:errors.append(f'RF DAC peak code {rf_peak}')
    # Recover exact DAC edge sample indices from packed words, including edges
    # inside a 16-sample fabric word. Ignore the initial enable transition.
    positive_edges=[];last_sign=0
    for row in waveform:
        word=int(row['dac'],16)
        for lane in range(16):
            sample=signed((word>>(16*lane))&65535,16)
            sign=(sample>0)-(sample<0)
            if sign>0 and last_sign<0:positive_edges.append(int(row['cycle'])*16+lane)
            last_sign=sign
    square_commands=[r for r in cmds if r['kind']=='sqcmd']
    square_points=[]
    for r in square_commands:
        word=int(r['word'],16)
        if word>>128&1:
            square_points.append((word&0xffffffff,word>>64&0xffffffff,word>>32&0xffffffff))
        if word>>129&1:errors.append('Unexpected phase-accumulator reset command')
    if meta['square'].get('enabled'):
        def points(name):
            v=meta['square']['parameters'][name]
            return [v['start']+(v['stop']-v['start'])*i/(v['count']-1) for i in range(v['count'])] if v.get('sweep') and v['count']>1 else [v['value']]
        requested=Counter((round(f/4800*2**32),min(32764,round(amp/800*8192)*4),round(ph/360*2**32)&0xffffffff)
                          for f,amp,ph in product(points('frequency'),points('amplitude'),points('phase')))
        if 'awg_request' in meta:
            requested=Counter({key:value*nshots for key,value in requested.items()})
        if Counter(square_points)!=requested:errors.append('SquarePulse command points differ from requested Cartesian sweep')
    elif square_points!=[(1790,1228,0)] or len(square_commands)!=1:
        errors.append('Autonomy scenario must contain exactly one seed update and no main-program update')
    if a.case=='gui_autonomy':
        stopped=next(int(r['cycle']) for r in epochs if r['kind']=='seed_end_confirmed')
        if gui_start-stopped<30000:errors.append('Less than 100 us of autonomous output after seed END')
    initial_phase_rate=(int(square_commands[0]['word'],16)&((1<<64)-1)) if square_commands else None
    first_update=next((int(r['cycle'])+14 for r in square_commands[1:]
                       if (int(r['word'],16)&((1<<64)-1))!=initial_phase_rate
                       or not ((int(r['word'],16)>>128)&1)),None)
    initial_edges=[s for s in positive_edges if first_update is None or s<first_update*16]
    periods=[(b-a)/4800 for a,b in zip(initial_edges,initial_edges[1:])]
    ftw=int(square_commands[0]['word'],16)&0xffffffff
    theoretical_period=2**32/(ftw*4800)
    if a.case=='gui_500us' and (not periods or any(abs(v-theoretical_period)>1/4800 for v in periods)):
        errors.append(f'500 us period measurement {periods}, expected {theoretical_period} +/- one DAC sample')
    requested_awg=None
    if 'awg_request' in meta:
        from check_awg_request import check_requested_awg
        requested_awg=check_requested_awg(d,meta,actual,cmds,waveform,gpio,checks)
        errors.extend(requested_awg['errors'])
    summary=dict(case=a.case,passed=not errors,errors=errors,sample_checks=int(checks['samples']),
        awg_sample_checks=awg_checks,awg_mismatch_examples=awg_errors,
        gui_events=len(gui_actual),processor_timing_deltas=sorted(set(t['delta'] for t in timing)),
        routing=route,marker_count=len(widths),marker_width_cycles=widths,
        gpio_extra_cycles=sorted(set(gpio_latency)),square_command_points=square_points,
        epochs=epochs,
        rf_frequency_mhz=rf_frequency,rf_peak_code=rf_peak,rf_pulse_cycles=rf_durations,
        rf_command_to_dac_cycles=sorted(set(rf_latencies)),
        first_nonzero_dac_cycles={key:next((int(r['cycle']) for r in waveform if int(r[key],16)),None)
                                  for key in ['core','dac','awg','rf']},
        first_marker_cycle=rises[0],
        trigger_delay_cycles=delay,captured_samples=len(source),ddr_beats=len(ddr),
        capture_matches_next_fir_valid=not capture_alignment_errors,
        initial_square_periods_us=periods,
        initial_square_theoretical_period_us=theoretical_period,
        trigger_to_first_sample_cycles=[int(capture_samples[i*8]['cycle'])-accept[i] for i in range(min(len(accept),len(source)//8))])
    if requested_awg is not None:summary['requested_awg']=requested_awg
    (d/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    with (d/'command_timing.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['port','event','expected','actual','delta']);w.writeheader();w.writerows(timing)
    print(json.dumps(summary,indent=2))
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
