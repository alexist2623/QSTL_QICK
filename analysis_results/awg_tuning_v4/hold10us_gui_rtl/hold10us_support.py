"""Extra physical-output probes and exact HOLD alignment assertions."""
import csv
import json
import re


def extra_monitor(top):
    blocks=[]
    for suffix, output_slice in ((4,8),(5,10),(6,11)):
        root=f'dut.sim_bd_i'
        blocks.append(f'''
integer physical_trace_{suffix};
initial begin
 if(!$value$plusargs("OUT=%s",output_dir)) $fatal(1,"Missing OUT");
 physical_trace_{suffix}=$fopen({{output_dir,"/physical_{suffix}.csv"}},"w");
 $fwrite(physical_trace_{suffix},"cycle,raw,awg,rf,sum,dac\\n");
end
always @(posedge clk_300000000) if(resetn) begin
 #0.020;
 $fwrite(physical_trace_{suffix},"%0d,%064h,%064h,%064h,%064h,%064h\\n",cycle,
  {root}.axis_awg_tuning_v1_{suffix}.core_samples,
  {root}.sum_{suffix}.s0_axis_tdata,{root}.sum_{suffix}.s1_axis_tdata,
  {root}.sum_{suffix}.m_axis_tdata,
  {root}.axis_register_slice_{output_slice}_m_axis_TDATA);
end
final $fclose(physical_trace_{suffix});
''')
    return top.replace('endmodule','\n'.join(blocks)+'\nendmodule')


def signed_lanes(word):
    return [((word >> (i*16)) & 65535) - (65536 if word & (1 << (i*16+15)) else 0)
            for i in range(16)]


def analyze(out, log, model, offset, shots, hold):
    checked=re.findall(r'OUTPUT_SUM_RESULT suffix=(\d+) samples=(\d+)',log)
    assert len(checked)==3 and all(int(n)>0 for _,n in checked)
    pairs=[]
    for port,suffix in enumerate((4,5,6)):
        with (out/f'physical_{suffix}.csv').open() as stream:
            rows=[dict(cycle=int(r['cycle']),**{k:int(r[k],16) for k in ('raw','awg','rf','sum','dac')})
                  for r in csv.DictReader(stream)]
        by_cycle={r['cycle']:r for r in rows}
        starts=[r['cycle'] for a,r in zip(rows,rows[1:]) if not a['rf'] and r['rf']]
        stops=[r['cycle'] for a,r in zip(rows,rows[1:]) if a['rf'] and not r['rf']]
        events=[e for e in model.output_events if e.tproc_ch==port]
        rf=[e for e in events if (e.word>>152)&255==0 and (e.word>>96)&0xffffffff]
        ramps=[e for e in events if (e.word>>152)&255==1 and (e.word>>144)&3==2]
        assert len(rf)==len(starts)==len(stops)==shots
        assert len(ramps)==2*shots
        measurements=[]
        for shot,(start,stop,event) in enumerate(zip(starts,stops,rf)):
            first,second=ramps[shot*2:shot*2+2]
            # Explicit 10 us RAMP length: 48000 scalar samples at 4.8 GS/s.
            assert (first.word>>64)&((1<<23)-1)==48000
            assert (second.word>>64)&((1<<23)-1)==48000
            hold_sets=[e for e in events if (e.word>>152)&255==1 and (e.word>>144)&3==1
                       and e.cycle> (first if hold==1 else second).cycle]
            anchor=hold_sets[0]
            assert start-event.cycle-offset==32, (suffix,start,event.cycle,offset)
            assert stop-start==3000, (suffix,shot,stop-start)
            assert start==anchor.cycle+offset+19, (suffix,shot,start,anchor.cycle+offset+19)
            # Existing compiler includes one explicit guard clock after each RAMP.
            # Keep that visible separately from the requested 3000-clock ramp.
            assert second.cycle-first.cycle==6001
            # Seven startup clocks plus the existing one-clock guard.
            ramp=(first if hold==1 else second)
            assert anchor.cycle-ramp.cycle==3008, (anchor.cycle,ramp.cycle)
            ramp_start=first.cycle+offset+26
            assert start-ramp_start==(3001 if hold==1 else 9002)
            # Existing axis_register_slice_nb has N=10; the combiner adds two.
            for cycle in range(start+12,stop+12):
                assert by_cycle[cycle-12]['rf'] != 0
            measurements.append(dict(shot=shot,first_ramp_sum_input_cycle=ramp_start,
                rf_sum_input_start_cycle=start,rf_sum_input_stop_cycle=stop,
                physical_start_cycle=start+12,physical_stop_cycle=stop+12,
                start_relative_first_ramp_us=(start-ramp_start)/300,
                stop_relative_first_ramp_us=(stop-ramp_start)/300,
                width_cycles=stop-start,start_skew_cycles=0,
                existing_ramp_guard_cycles=1,
                offset_from_ideal_10us_timeline_cycles=hold))
        # Independent all-lane reference through combiner AND final output slice.
        samples=0
        for row in rows[40:]:
            previous=by_cycle[row['cycle']-12]
            values=[]
            for a,b in zip(signed_lanes(previous['awg']),signed_lanes(previous['rf'])):
                total=a+b
                values.append(32764 if total>32764 else -32768 if total< -32768 else ((total+2)>>2)*4)
            expected=sum((v&65535)<<(16*i) for i,v in enumerate(values))
            assert row['dac']==expected, ('physical sum mismatch',suffix,row['cycle'])
            samples+=16
        pairs.append(dict(suffix=suffix,shots=shots,hold=hold,measurements=measurements,
            physical_sample_checks=samples,start_skew_cycles=0,width_mismatches=0,
            unexpected_rf_pulses=0))
    result=dict(sample_oracles=checked,pairs=pairs,combiner_pipeline_cycles=2,
                output_register_cycles=10,rf_duration_us=10,gui_initial_set_us=1)
    (out/'output_sum_result.json').write_text(json.dumps(result,indent=2))
    return result
