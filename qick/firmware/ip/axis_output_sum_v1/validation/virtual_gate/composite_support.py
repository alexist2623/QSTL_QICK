"""Composite RF extension: public software-point selection plus actual RTL."""
from dataclasses import replace
import csv
import json
import re
import numpy as np
import support
from support import matrix_oracle,extra_monitors,finish

def configure_inputs(args,pulses,axes,rf_specs,square):
    from dc_waveform_core import QickRfFrequencyParameterSpec,QickRfDurationParameterSpec
    from qick_qcodes_experiment import _rf_software_sweep_bindings,_rf_specs_at_software_coordinate
    axes,rf_specs,square=support.configure_inputs(args,pulses,axes,rf_specs,square)
    axes=[a for a in axes if a.axis_kind=='amplitude']
    c=args.virtual_case
    frequency=QickRfFrequencyParameterSpec('f0',190.,c.get('named')=='frequency',180.,225.,2)
    duration=QickRfDurationParameterSpec('d0',.1,c.get('named')=='duration',.1,.2,2)
    first=replace(rf_specs[0],pulse_mode='composite',predefined_template='cpmg',
        predefined_n=c.get('n',2),predefined_tau_us=c.get('tau',.2),
        predefined_frequency_parameter='f0',predefined_duration_parameter='d0',predefined_gain=2000,
        predefined_n_sweep_enabled=not c.get('named'),predefined_n_sweep_start=1,
        predefined_n_sweep_stop=2,predefined_n_sweep_count=2,
        predefined_tau_sweep_enabled=not c.get('named'),predefined_tau_sweep_start_us=.2,
        predefined_tau_sweep_stop_us=.4,predefined_tau_sweep_count=2,
        frequency_parameters=(frequency,),duration_parameters=(duration,))
    args.outer_rf_specs=[first,*rf_specs[1:]]
    bindings=_rf_software_sweep_bindings(args.outer_rf_specs)
    concrete=_rf_specs_at_software_coordinate(args.outer_rf_specs,bindings,[c['n'],c['tau']]) if bindings else args.outer_rf_specs
    args.concrete_rf_specs=concrete
    return axes,concrete,square

def build_from_widgets(cfg,pulses,axes,rf_specs,options,out):
    import qick_qcodes_experiment as ex
    original=ex.build_qick_program
    def select_point(cfg,sequence,**kwargs):
        bindings=ex._rf_software_sweep_bindings(kwargs['rf_specs'])
        if bindings:
            coordinate=[options.virtual_case['n'],options.virtual_case['tau']]
            specs=ex._rf_specs_at_software_coordinate(kwargs['rf_specs'],bindings,coordinate)
            sequence=ex._sequence_at_rf_software_coordinate(sequence,specs,fabric_mhz=300.)
            kwargs['rf_specs']=specs
            (out/'gui_software_point.json').write_text(json.dumps(dict(coordinate=coordinate,
                path='Actual GUI controls -> production _rf_specs_at_software_coordinate / _sequence_at_rf_software_coordinate -> production build_qick_program',
                board_execution=False),indent=2))
        return original(cfg,sequence,**kwargs)
    ex.build_qick_program=select_point
    try:return support.build_from_widgets(cfg,pulses,axes,options.outer_rf_specs,options,out)
    finally:ex.build_qick_program=original

def analyze_rf(out,model,offset,shots,args,program):
    with (out/'rf_samples.csv').open() as f:rows=list(csv.DictReader(f))
    pulses=[];wave=[]
    for r in rows:
        word=int(r['word'],16);cycle=int(r['cycle'])
        if word:
            values=[(word>>(16*k))&65535 for k in range(16)]
            wave.append((cycle,[v-65536 if v>=32768 else v for v in values]))
        elif wave:pulses.append((wave,cycle));wave=[]
    n=args.virtual_case.get('n',2)
    events=[e for e in model.output_events if e.tproc_ch==0 and (e.word>>152)&255==0 and (e.word>>96)&0xffffffff]
    assert len(pulses)==len(events)==shots*n and not wave
    results=[]
    for index,((samples,stop),event) in enumerate(zip(pulses,events)):
        values=np.array([v for _,w in samples for v in w])
        point=index//(n*2)
        coords=program.sequence.sweep_coordinate(point)
        frequency=190.;duration=.1
        for axis,value in zip(program.sequence.sweep_axes,coords):
            if axis.axis_kind=='rf_frequency':frequency=float(value)
            if axis.axis_kind=='rf_duration':duration=float(value)
        ftw=int(round(frequency/4800*2**32))
        assert event.word&0xffffffff==ftw
        assert (event.word>>96)&0xffffffff==2000
        assert (event.word>>128)&65535==round(duration*300)
        assert stop-samples[0][0]==round(duration*300)
        phase=np.arange(len(values))*2*np.pi*ftw/2**32
        basis=np.column_stack((np.cos(phase),np.sin(phase),np.ones(len(values))))
        fit=np.linalg.lstsq(basis,values,rcond=None)[0]
        residual=float(max(abs(basis@fit-values)))
        amplitude=float(np.hypot(fit[0],fit[1]))
        assert abs(amplitude-2000)<=1 and residual<=4
        results.append(dict(point=point,first_cycle=samples[0][0],width_cycles=stop-samples[0][0],
            latency_cycles=samples[0][0]-event.cycle-offset,amplitude_error_codes=abs(amplitude-2000),residual_codes=residual))
    assert len({r['latency_cycles'] for r in results})==1
    (out/'rf_measurements.json').write_text(json.dumps(results,indent=2))
    return dict(pulses=len(results),width_mismatch_pulses=0,width_error_max_cycles=0,
        amplitude_error_max_codes=max(r['amplitude_error_codes'] for r in results),
        fit_residual_max_codes=max(r['residual_codes'] for r in results))

def analyze_sum(out,log,model,offset,shots,args,program):
    checked=re.findall(r'OUTPUT_SUM_RESULT suffix=(\d+) samples=(\d+)',log)
    assert len(checked)==3 and all(int(n)>0 for _,n in checked)
    tables=[]
    for port,suffix in enumerate((4,5,6)):
        with (out/f'sum_edges_{suffix}.csv').open() as f:rows=list(csv.DictReader(f))
        starts=[int(r['cycle']) for r in rows if r['stream']=='rf' and r['edge']=='1']
        stops=[int(r['cycle']) for r in rows if r['stream']=='rf' and r['edge']=='0']
        awg=[int(r['cycle']) for r in rows if r['stream']=='awg' and r['edge']=='1']
        events=[e for e in model.output_events if e.tproc_ch==port and (e.word>>152)&255==0 and (e.word>>96)&0xffffffff]
        n=args.virtual_case.get('n',2) if port==0 else 1
        assert len(starts)==len(stops)==len(events)==shots*n
        for start,stop,event in zip(starts,stops,events):
            assert start-event.cycle-offset==32
            assert stop-start==(event.word>>128)&65535
            if port:assert start in awg
        tables.append(starts)
    n=args.virtual_case.get('n',2);tau=args.virtual_case.get('tau',.2)
    for shot in range(shots):
        coords=program.sequence.sweep_coordinate(shot//2)
        duration=next((float(v) for a,v in zip(program.sequence.sweep_axes,coords) if a.axis_kind=='rf_duration'),.1)
        for pulse in range(n):
            requested_delay=round((tau*(pulse+.5)+pulse*duration)*300)
            assert tables[0][shot*n+pulse]-tables[1][shot]==requested_delay
    return dict(sample_oracles=checked,combiner_pipeline_cycles=2,
        pulse_counts=[len(t) for t in tables],cpmg_delay_checks=shots*n,start_skew_cycles=0,width_mismatches=0)
