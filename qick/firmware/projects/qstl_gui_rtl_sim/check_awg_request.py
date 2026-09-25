"""Independent AWG sweep oracle derived from requested values, not RTL commands.

The scalar reference uses the published DAC quantization, integer affine sweep
coefficients, seven-clock RAMP startup, and ten-clock output register slice.
It never calls the GUI compiler or AwgTuningBehaviorModel.
"""
import csv
from itertools import product
import numpy as np


def signed(value, bits):
    return (value & ((1 << (bits-1))-1)) - (value & (1 << (bits-1)))


def trunc_div(value, divisor):
    return (1 if value >= 0 else -1) * (abs(value) // divisor)


def nearest_div(value, divisor):
    return (1 if value >= 0 else -1) * ((2*abs(value)+divisor)//(2*divisor))


def requested_shots(request):
    for point, (ramp, hold, amplitude) in enumerate(product(
            request['ramp_us'], request['hold_us'], request['amplitude_mv'])):
        for repeat in range(request['repetitions']):
            yield dict(point=point, repeat=repeat, ramp_us=ramp,
                       hold_us=hold, amplitude_mv=amplitude)


def dac_code(millivolts, full_scale):
    return max(-32768, min(32764, round(millivolts/full_scale*8192)*4))


def prediction(meta, end_cycle, clock_origin):
    req=meta['awg_request'];shots=list(requested_shots(req))
    expected=np.zeros(end_cycle*16, dtype=np.int64)
    point_rows=[]
    tail=dac_code(req['tail_mv'], req['full_scale_mv'])
    amplitudes=[dac_code(v, req['full_scale_mv']) for v in req['amplitude_mv']]
    # The exporter pads each loop to the longest Cartesian point, adds the
    # standard 20-cycle recovery, completes the 111-cycle end marker, and
    # advances eight clocks for the next SquarePulse/TMUX update.
    max_point=round((max(req['hold_us'])+max(req['ramp_us'])+req['tail_us'])*300)+1
    end_marker_offset=max_point+20
    period=end_marker_offset+112+8
    for index, shot in enumerate(shots):
        hold=round(shot['hold_us']*300);ramp=round(shot['ramp_us']*300)
        count=ramp*16
        amp_index=req['amplitude_mv'].index(shot['amplitude_mv'])
        start=amplitudes[amp_index]
        base_step=trunc_div((tail-amplitudes[0])*65536, count-1)
        final_step=trunc_div((tail-amplitudes[-1])*65536, count-1)
        increment=nearest_div(final_step-base_step, len(amplitudes)-1)
        step=base_step+amp_index*increment
        direct_step=trunc_div((tail-start)*65536, count-1)
        schedule=392+index*period  # initial synci(128), synci(256), SQ lead(8)
        output_start=clock_origin+schedule+1+3+10
        ramp_start=output_start+hold
        k=np.arange(count, dtype=np.int64)
        ramp_values=((start*65536+k*step) >> 16) & ~3
        ramp_values[-1]=tail
        expected[output_start*16:]=start
        expected[ramp_start*16:(ramp_start+ramp)*16]=ramp_values
        expected[(ramp_start+ramp)*16:]=tail
        ideal=start+(tail-start)*k/(count-1)
        direct=((start*65536+k*direct_step) >> 16) & ~3
        direct[-1]=tail
        changes=np.flatnonzero(ramp_values!=start)
        point_rows.append(dict(shot=index, **shot, start_code=start, tail_code=tail,
            hold_cycles=hold, ramp_cycles=ramp, duration_samples=count,
            step=step, direct_step=direct_step, step_error=step-direct_step,
            schedule=schedule, set_dac_cycle=output_start,
            ramp_dac_cycle=ramp_start, ramp_end_cycle=ramp_start+ramp,
            tail_set_dac_cycle=output_start+hold+ramp+1,
            first_ramp_change_sample=int(changes[0]) if len(changes) else -1,
            max_ideal_ramp_error_codes=float(np.max(np.abs(ramp_values-ideal))),
            max_direct_step_difference_codes=int(np.max(np.abs(ramp_values-direct)))))
    return expected.reshape(end_cycle,16), point_rows, period, end_marker_offset


def expand_awg(waveform, end_cycle):
    observed=np.zeros((end_cycle,16),dtype=np.int64)
    for index,row in enumerate(waveform):
        begin=int(row['cycle'])
        end=int(waveform[index+1]['cycle']) if index+1<len(waveform) else end_cycle
        word=int(row['awg'],16)
        values=[signed(word>>(16*lane)&65535,16) for lane in range(16)]
        observed[begin:min(end,end_cycle)]=values
    return observed


def check_requested_awg(directory, meta, events, commands, waveform, gpio, checks):
    errors=[]
    def check(condition, description):
        if not condition:errors.append(description)
    origins={int(e['cycle'])-int(e['tproc_time']) for e in events}
    check(len(origins)==1, f'AWG request: inconsistent processor clock origins {origins}')
    origin=min(origins)
    end=int(checks['end_cycle'])
    expected,points,period,end_marker_offset=prediction(meta,end,origin)
    observed=expand_awg(waveform,end)
    mismatch=np.argwhere(expected[17:]!=observed[17:])
    check(not len(mismatch), f'AWG request: {len(mismatch)} scalar samples differ from requested waveform')
    awg=[r for r in commands if r['kind']=='awgcmd']
    awg_events=[r for r in events if int(r['port'])==0]
    check(len(awg)==3*len(points), 'AWG request: wrong total SET/RAMP/SET command count')
    check(len(awg_events)==3*len(points), 'AWG request: wrong tProcessor AWG command count')
    marker_rises=[];previous=0
    for row in gpio:
        value=int(row['value'],16)
        if value&64 and not previous&64:marker_rises.append(int(row['cycle']))
        previous=value
    wanted_markers=[]
    for point in points:
        shot=point['shot'];base=point['schedule']
        command_offsets=[0,point['hold_cycles']-7,point['hold_cycles']+point['ramp_cycles']+1]
        wanted_words=[(1,point['start_code'],0,0),
                      (2,point['tail_code'],point['duration_samples'],point['step']),
                      (1,point['tail_code'],0,0)]
        for index,(offset,wanted) in enumerate(zip(command_offsets,wanted_words)):
            position=3*shot+index
            if position>=len(awg) or position>=len(awg_events):continue
            command=awg[position];word=int(command['word'],16)
            received=(word>>144&3,signed(word&0xffffffff,32),
                      word>>64&0x7fffff,signed(word>>96&0xffffff,24))
            check(received==wanted, f'AWG shot {shot} command {index}: {received}, requested {wanted}')
            check(int(awg_events[position]['tproc_time'])==base+offset+1,
                  f'AWG shot {shot} command {index}: incorrect requested dispatch time')
            check(int(command['cycle'])==origin+base+offset+4,
                  f'AWG shot {shot} command {index}: incorrect IP acceptance time')
        wanted_markers.extend([origin+base+1, origin+base+end_marker_offset+1])
        # The first non-constant scalar sample is measured, rather than calling
        # the unchanging initial RAMP sample an observed voltage edge.
        onset=point['ramp_dac_cycle']*16
        segment=observed.reshape(-1)[onset:onset+point['duration_samples']]
        actual_changes=np.flatnonzero(segment!=point['start_code'])
        actual_change=int(actual_changes[0]) if len(actual_changes) else -1
        point['observed_first_ramp_change_sample']=actual_change
        check(actual_change==point['first_ramp_change_sample'],
              f'AWG shot {shot}: first changing DAC sample is shifted')
        point['observed_set_code']=int(observed[point['set_dac_cycle'],0])
        point['observed_tail_code']=int(observed[point['ramp_end_cycle'],0])
    check(marker_rises==wanted_markers, 'AWG request: start/end markers disagree with requested loop timing')
    # Repeats of a point must be identical over the entire loop, including the
    # voltage-dependent RAMP and any padding before the next point.
    repeat_mismatches=[]
    for point in points:
        if not point['repeat']:continue
        first=points[point['shot']-point['repeat']]
        one=observed[first['set_dac_cycle']:first['set_dac_cycle']+period]
        other=observed[point['set_dac_cycle']:point['set_dac_cycle']+period]
        if not np.array_equal(one,other):repeat_mismatches.append(point['shot'])
    check(not repeat_mismatches, f'AWG request: repetition waveform mismatch {repeat_mismatches}')
    with (directory/'awg_point_timing.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(points[0]));writer.writeheader();writer.writerows(points)
    return dict(errors=errors,points=len(points)//meta['awg_request']['repetitions'],
        repetitions=meta['awg_request']['repetitions'],shots=len(points),
        independent_sample_checks=(end-17)*16,
        mismatch_count=len(mismatch),mismatch_examples=(mismatch[:8]+[17,0]).tolist(),
        loop_period_cycles=period,loop_period_us=period/300,
        repeat_mismatches=repeat_mismatches,
        input_amplitude_mv=meta['awg_request']['amplitude_mv'],
        measured_set_codes=sorted({p['observed_set_code'] for p in points}),
        measured_tail_codes=sorted({p['observed_tail_code'] for p in points}),
        hold_cycles=sorted({p['hold_cycles'] for p in points}),
        ramp_cycles=sorted({p['ramp_cycles'] for p in points}),
        ramp_step_errors=sorted({p['step_error'] for p in points}),
        max_ideal_ramp_error_codes=max(p['max_ideal_ramp_error_codes'] for p in points),
        max_direct_step_difference_codes=max(p['max_direct_step_difference_codes'] for p in points),
        marker_to_awg_dac_cycles=13,
        ramp_command_advance_cycles=7,tail_set_guard_cycles=1,
        all_requested_command_values_and_times_match=not errors)
