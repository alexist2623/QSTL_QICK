"""AWG v3 planning against executed command words, before the RC IIR.

The FPGA measures area. Python only packs its settings, checks finite storage
and voltage limits, and reserves a conservative completion deadline. It never
uploads a Cartesian per-point voltage or compensation table.
"""
from dataclasses import replace
from fractions import Fraction
from itertools import product

from qick.dc_area import (AREA_BITS, DC_START_CYCLES, compensation_plan,
                          clipped_floor_sum, validate_area_bounds)


def supported(program):
    flags = [int(program.soccfg['gens'][ch].get('dc_area_version', 0)) == 1
             for ch in program.awg_channels]
    if any(flags) and not all(flags) and program.sequence.bias_t_compensation is not None:
        raise ValueError('DC compensation requires matching AWG area-engine versions on all selected outputs')
    return all(flags)


def empty_legacy_models(program):
    import numpy as np
    config = program.sequence.bias_t_compensation
    program._bias_t_mode = None if config is None else config.mode
    program._bias_t_comp_codes = ()
    for name in ('duration_q_requested', 'duration_q_actual', 'target_code_requested', 'target_code_actual'):
        setattr(program, '_bias_t_'+name, np.empty((0, 0), dtype=np.int64))
    program._bias_t_max_duration_q_error = program._bias_t_max_target_code_error = 0
    return ()


def executed_commands(program, point_index):
    """Evaluate existing register-add models at one requested preview point."""
    for commands in program.compiled_points[0].segment_commands:
        for command in commands:
            values = {}
            for register, attribute in (('target','target_code'), ('step','step'), ('duration','duration_samples')):
                model = program._sweep_models.get((*program._command_key(command), register))
                if model is not None:
                    values[attribute] = program._sweep_model_value(model, point_index)
            yield replace(command, **values)


def waveform_ledger(program, point_index, output):
    """Exact scalar area, including ramp startup/guard and forced final target.

    Constant time per SET and logarithmic time per RAMP, with no scalar sample
    arrays. The relative raw timing is sufficient because uniform pipeline
    delay cannot change a shot that begins and ends at zero.
    """
    ch = program.awg_channels[output]
    gen = program.soccfg['gens'][ch]
    if Fraction(str(gen['f_fabric'])) != Fraction(str(program.tproc_mhz)):
        raise ValueError('AWG v3 DC timing requires the verified common AWG/tProcessor fabric clock')
    models = {m['key']:m for m in program._event_timing_models}
    def event(key, default):
        return (program._sweep_model_value(models[key], point_index)
                if key in models else int(default))
    events=[]
    for command in executed_commands(program, point_index):
        if command.output_index == output:
            timestamp=event(('event_time','awg',*program._command_key(command)),
                            program.timing['command_times'][program._timing_key(command)])
            events.append((timestamp, command))
    zero_time=event(('event_time','bias_pre_zero',output),
        program.timing['segment_ends'][-1]-program.awg_output_latency_tproc+program._channel_slots[ch])
    events.append((zero_time,None))
    area=low=high=cursor=current=ramp_samples=0
    ideal_area=Fraction(0)
    clip_upper_bound=clip_lower_bound=Fraction(0)
    intervals=[]
    rate=float(gen['f_fabric'])*16
    def hold(value, count):
        nonlocal area,low,high,ideal_area
        if count < 0:
            raise ValueError('AWG DC planning found overlapping raw output intervals')
        area += value*count
        ideal_area += value*count
        low=min(low,area); high=max(high,area)
        if count: intervals.append((value/8192, value/8192, count/rate, 0.0))
    for timestamp,command in sorted(events,key=lambda item:item[0]):
        if command is not None and command.kind == 'ramp':
            start=(timestamp+int(gen['ramp_startup_latency_cycles']))*16
            hold(current,start-cursor)
            count=int(command.duration_samples)
            if count <= 0: raise ValueError('RAMP needs a positive scalar duration')
            b=current*(1 << (int(gen['frac'])+2))
            a=int(command.step); m=1 << (int(gen['frac'])+2)
            # A monotone ramp can change area direction only at its zero cross.
            candidates={0,count-1}
            if a:
                cross=(-b)//a
                candidates.update(max(0,min(count-1,cross+d)) for d in (-1,0,1,2))
            prefixes=[area+clipped_floor_sum(k,m,a,b) for k in candidates]
            low=min(low,*prefixes); high=max(high,*prefixes)
            area+=clipped_floor_sum(count-1,m,a,b)
            ideal_area+=Fraction((count-1)*b+a*(count-1)*(count-2)//2,m)
            ramp_samples+=count-1
            raw_ends=(Fraction(b,m),Fraction(b+a*max(0,count-2),m))
            clip_upper_bound+=(count-1)*max(Fraction(0),max(raw_ends)-8191)
            clip_lower_bound+=(count-1)*max(Fraction(0),-8192-min(raw_ends))
            target=int(command.target_code)>>2
            area+=target
            ideal_area+=target
            low=min(low,area); high=max(high,area)
            stepped=(b+a*max(0,count-1))/m
            error=(1+abs(stepped-target))/8192
            intervals.append((current/8192,target/8192,count/rate,error))
            cursor=start+count
            current=target
            padding=(-count)%16
            hold(current,padding); cursor+=padding
        else:
            start=timestamp*16
            hold(current,start-cursor)
            current=0 if command is None else int(command.target_code)>>2
            cursor=start
    return dict(area=area, prefix_min=low, prefix_max=high, scalar_samples=cursor,
                ideal_area=ideal_area,ramp_samples=ramp_samples,
                clip_upper_bound=clip_upper_bound,clip_lower_bound=clip_lower_bound,
                intervals=intervals, end_cycle=zero_time)


def validation_points(program):
    """Endpoints of affine axes, conditioned on existing duration-coefficient rows."""
    import numpy as np
    axes=program.sequence.sweep_axes
    conditioned=set(a for m in program._sweep_models.values()
                    for a in m.get('duration_axis_indices',()))
    shape=tuple(axis.count for axis in axes)
    if not shape: return (0,)
    return tuple(int(np.ravel_multi_index(index,shape)) for index in product(*(
        range(count) if a in conditioned else (0,) if count==1 else (0,count-1)
        for a,count in enumerate(shape))))


def point_plan(program, point_index, output):
    ledger=waveform_ledger(program,point_index,output)
    validate_area_bounds(ledger['prefix_min'],ledger['prefix_max'])
    settings=program._hardware_dc_settings[output]
    plan=compensation_plan(ledger['area'], **settings)
    return dict(ledger, **plan)


def prepare(program):
    """Build settings and a finite completion bound; the RTL selects actual area."""
    from qick_fine_tune_sweep import normalized_to_dac
    config=program.sequence.bias_t_compensation
    program._hardware_dc_settings=()
    program.hardware_dc_validation=()
    if config is None or not program._hardware_dc_area:
        return
    settings=[]
    for output,ch in enumerate(program.awg_channels):
        gen=program.soccfg['gens'][ch]
        if int(gen.get('dc_area_bits',0)) != AREA_BITS:
            raise ValueError('AWG v3 requires the selected 48-bit DC area firmware')
        if config.mode=='fixed_time':
            settings.append(dict(words=int(config.fixed_duration_cycles)))
        else:
            value=normalized_to_dac(config.amplitude*program.sequence.voltage_scale_factors[output],
                min_code=int(gen.get('minv',-32768)),max_code=int(gen.get('maxv',32764)),invalid_lsb=2)
            if value <= 0: raise ValueError('DC compensation voltage is below one effective DAC code')
            settings.append(dict(amplitude=value))
    program._hardware_dc_settings=tuple(settings)
    reports=[]
    ideals=[[] for _ in settings]
    quantization=[0 for _ in settings]
    clip_upper=[Fraction(0) for _ in settings]
    clip_lower=[Fraction(0) for _ in settings]
    for index in validation_points(program):
        for output in range(len(program.awg_channels)):
            plan=point_plan(program,index,output)
            reports.append(dict(point=index,output=output,area=plan['area'],
                prefix_min=plan['prefix_min'],prefix_max=plan['prefix_max'],
                compensation_words=plan['words'],residual=plan['residual']))
            ideals[output].append(plan['ideal_area'])
            quantization[output]=max(quantization[output],plan['ramp_samples'])
            clip_upper[output]=max(clip_upper[output],plan['clip_upper_bound'])
            clip_lower[output]=max(clip_lower[output],plan['clip_lower_bound'])
    # Full-scale bound covers any sign changes, virtual-gate mixing, and every
    # intermediate point, not just a net area that might happen to cancel.
    maximum_end=int(program._dynamic_point_end)+max(program._channel_slots.values())+8
    absolute_bound=maximum_end*16*8192
    validate_area_bounds(-absolute_bound,absolute_bound)
    maximum_words=0
    net_bounds=[]
    for output,setting in enumerate(settings):
        # With a duration-coefficient row held fixed, the unfloored area is
        # multi-affine in the remaining axes. Each scalar floor loses <1 code.
        # This encloses interior points without compiling a Cartesian grid.
        # Ramp saturation can occur between legal SET targets when independently
        # rounded target/step increments drift apart. The pre-clamp ramp is
        # affine per axis; sums of positive over/undershoot bounds are convex
        # per axis, so their maxima are also enclosed by the same corners.
        lo=min(ideals[output]).__floor__()-quantization[output]-clip_upper[output].__ceil__()
        hi=max(ideals[output]).__floor__()+clip_lower[output].__ceil__()
        net_bounds.append((lo,hi))
        if 'words' in setting:
            bound=setting['words']
            for area in (lo,hi): compensation_plan(area,words=bound)
        else:
            per_word=(setting['amplitude']//4)*16
            net_bound=max(abs(lo),abs(hi))
            bound=max(1,(net_bound+per_word-1)//per_word)
        maximum_words=max(maximum_words,bound)
    # tProcessor sync consumes a signed 32-bit time register.
    deadline=program.bias_t_simultaneous_start_lead_cycles+DC_START_CYCLES+maximum_words+32
    if deadline >= (1<<31):
        raise ValueError('DC completion bound exceeds tProcessor time range; use a higher compensation voltage or shorter shot')
    program._hardware_dc_deadline=deadline
    program._hardware_dc_net_bounds=tuple(net_bounds)
    program.hardware_dc_validation=tuple(reports)


def emit(program):
    config=program.sequence.bias_t_compensation
    for output,ch in enumerate(program.awg_channels):
        program.set_pulse_registers(ch=ch,style='awg_dc',action=config.mode,
                                   **program._hardware_dc_settings[output])
        program.pulse(ch=ch,t=program.bias_t_simultaneous_start_lead_cycles)
    ch=program.awg_channels[0]
    page,reg=program._gen_regmap[(ch,'target')]
    program.safe_regwi(page,reg,program._hardware_dc_deadline,'wait for hardware DC area completion and IIR flush')
    if program._overlap_dc_readout():
        program._emit_capture_end_max(page,reg)
    program.sync(page,reg,'hardware DC compensation and capture complete')
    program.reset_timestamps()


def validate_rc(program):
    from qick.precompensation import rc_coefficient
    from qick_rc_validation import interval_extrema, check_limits
    result=[]
    for index in validation_points(program):
        for output,ch in enumerate(program.awg_channels):
            gen=program.soccfg['gens'][ch]
            rate=float(gen['f_fabric'])*16
            coefficient=rc_coefficient(program.sequence.rc_compensation.tau_us,rate)
            inverse_tau=2*coefficient*rate/(1<<48)
            plan=point_plan(program,index,output)
            intervals=list(plan['intervals'])
            intervals.append((0,0,0,0))
            intervals.extend((value/8192,value/8192,count/rate,0)
                             for count,value in plan['runs'])
            intervals.append((0,0,0,0))
            low,high=interval_extrema(intervals,inverse_tau)
            peak=max(abs(v) for interval in intervals for v in interval[:2])
            margin=0.5/8192+peak*inverse_tau*(len(intervals)*2/float(gen['f_fabric'])+1/rate)
            bounds=low-margin,high+margin
            check_limits(bounds,name=f'{program.sequence.output_names[output]} (gen {ch})',
                point=index,limits=(int(gen['minv'])/32768,int(gen['maxv'])/32768),
                full_scale_mv=(program.sequence.output_full_scales_mv[output]
                               if program.sequence.output_full_scales_mv else None))
            result.append(dict(point_index=index,gen_ch=ch,minimum_normalized=bounds[0],maximum_normalized=bounds[1]))
    return tuple(result)
