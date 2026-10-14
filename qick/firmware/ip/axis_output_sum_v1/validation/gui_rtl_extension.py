"""v4 additions to the existing GUI/PMEM/real tProcessor/RF/AWG testbench."""
import csv
import json
import re
import hashlib
from pathlib import Path


def source_hashes(gui):
    repo=Path(__file__).resolve().parents[5]
    files=list((gui/'DCWaveformGeneratorGUI').glob('*.py'))
    files+=list((repo/'qick/qick_lib/qick').rglob('*.py'))
    files += [Path(__file__).resolve(),repo/'qick/firmware/ip/rc_precomp_validation/verify_gui_rtl.py',
              repo/'qick/firmware/ip/axis_awg_tuning_v3/validation/gui_widget_fixture.py']
    return {str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))}


def configure(cfg):
    from qick.output_sum import apply_output_sum_config
    for awg, rf, suffix in ((1,0,4),(3,2,5),(5,4,6)):
        route=dict(output_sum_version=1,output_sum_block=f'axis_output_sum_{suffix}',
                   output_sum_bypass=False,post_output_latency_cycles=2,
                   output_sum_awg=f'axis_awg_tuning_v3_{suffix}',
                   output_sum_rf=f'axis_signal_gen_v6_{(0,1,3)[awg//2]}')
        cfg['gens'][rf]['dac']=cfg['gens'][awg]['dac']
        for ch,role in ((awg,'awg'),(rf,'rf')):
            apply_output_sum_config(cfg['gens'][ch],dict(route,output_sum_role=role))


def connect(text):
    """Insert before output slice, exactly as the production BD does."""
    additions=[]
    for suffix, output_slice, rf in ((4,8,0),(5,10,1),(6,11,3)):
        awg=f'axis_awg_tuning_v1_{suffix}_m_axis'
        new=f'sum_{suffix}'
        pattern=rf'(  sim_bd_axis_register_slice_{output_slice}_0 axis_register_slice_{output_slice}\s+.*?\);)'
        match=re.search(pattern,text,re.S)
        assert match, output_slice
        replacement=match[0].replace(awg+'_TDATA',new+'_data').replace(awg+'_TVALID',new+'_valid').replace(awg+'_TREADY',new+'_ready')
        text=text[:match.start()]+replacement+text[match.end():]
        # Retain the old RF output slice only as a diagnostic probe. Its
        # ready is independent because the production DDS is fixed cadence.
        rfdata="256'd0" if rf is None else f'axis_signal_gen_v6_{rf}_m_axis_TDATA'
        rfvalid="1'b0" if rf is None else f'axis_signal_gen_v6_{rf}_m_axis_TVALID'
        additions.append(f'''
wire [255:0] {new}_data;
wire {new}_valid,{new}_ready;
axis_output_sum_v1 #(.BYPASS(0)) {new} (
 .aclk(clk_300000000_1),.aresetn(resetn_1),
 .s0_axis_tdata({awg}_TDATA),.s0_axis_tvalid({awg}_TVALID),.s0_axis_tready({awg}_TREADY),
 .s1_axis_tdata({rfdata}),.s1_axis_tvalid({rfvalid}),.s1_axis_tready(),
 .m_axis_tdata({new}_data),.m_axis_tvalid({new}_valid),.m_axis_tready({new}_ready),.clipped_o());
''')
    return text.replace('endmodule','\n'.join(additions)+'\nendmodule')


def monitor(top, shots, program, out, args):
    blocks=[]
    for suffix in (4,5,6):
        root=f'dut.sim_bd_i.sum_{suffix}'
        blocks.append(f'''
integer sum_checks_{suffix}=0;
logic [255:0] sum_expected_{suffix}=0;
always @(posedge clk_300000000) begin: SUM_ORACLE_{suffix}
 integer total,code;
 logic [255:0] next_expected;
 if(!resetn) sum_expected_{suffix}=0;
 else begin
  for(integer lane=0;lane<16;lane=lane+1) begin
   total=({root}.s0_axis_tvalid ? $signed({root}.s0_axis_tdata[lane*16+:16]) : 0)
        +({root}.s1_axis_tvalid ? $signed({root}.s1_axis_tdata[lane*16+:16]) : 0);
   if(total>32764)code=32764; else if(total< -32768)code=-32768;
   else code=((total+2)>>>2)*4;
   next_expected[lane*16+:16]=16'(code);
  end
  #0.003;
  if(cycle>20 && {root}.m_axis_tdata!==sum_expected_{suffix})
   $fatal(1,"v4 SUM mismatch suffix={suffix} cycle=%0d",cycle);
  sum_checks_{suffix}=sum_checks_{suffix}+16;
  sum_expected_{suffix}=next_expected;
 end
end
final $display("OUTPUT_SUM_RESULT suffix={suffix} samples=%0d",sum_checks_{suffix});
''')
    # Sparse first-shot sample probes independent of AWG raw/IIR/DC monitors.
    blocks.append('''
always @(posedge clk_300000000) if(resetn && dut.sim_bd_i.axis_tproc64x32_x8_0.m3_axis_tvalid)
 $fwrite(events_file,"%0d,%0d,2,%040h\\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m3_axis_tdata);
''')
    for suffix in (4,5,6):
        blocks.append(f'''
integer sum_trace_{suffix},sum_edges_{suffix};
logic [255:0] sum_last_awg_{suffix}=0,sum_last_rf_{suffix}=0;
initial begin
 if(!$value$plusargs("OUT=%s",output_dir)) $fatal(1,"Missing OUT");
 sum_trace_{suffix}=$fopen({{output_dir,"/sum_alignment_{suffix}.csv"}},"w");
 sum_edges_{suffix}=$fopen({{output_dir,"/sum_edges_{suffix}.csv"}},"w");
 $fwrite(sum_trace_{suffix},"cycle,awg,rf,sum\\n");
 $fwrite(sum_edges_{suffix},"cycle,stream,edge\\n");
end
always @(posedge clk_300000000) if(resetn) begin
 #0.004;
 if(cycle<12000 && (dut.sim_bd_i.sum_{suffix}.s0_axis_tdata!=sum_last_awg_{suffix} || dut.sim_bd_i.sum_{suffix}.s1_axis_tdata!=sum_last_rf_{suffix}))
  $fwrite(sum_trace_{suffix},"%0d,%064h,%064h,%064h\\n",cycle,dut.sim_bd_i.sum_{suffix}.s0_axis_tdata,dut.sim_bd_i.sum_{suffix}.s1_axis_tdata,dut.sim_bd_i.sum_{suffix}.m_axis_tdata);
 if((dut.sim_bd_i.sum_{suffix}.s0_axis_tdata!=0)!=(sum_last_awg_{suffix}!=0))
  $fwrite(sum_edges_{suffix},"%0d,awg,%0d\\n",cycle,dut.sim_bd_i.sum_{suffix}.s0_axis_tdata!=0);
 if((dut.sim_bd_i.sum_{suffix}.s1_axis_tdata!=0)!=(sum_last_rf_{suffix}!=0))
  $fwrite(sum_edges_{suffix},"%0d,rf,%0d\\n",cycle,dut.sim_bd_i.sum_{suffix}.s1_axis_tdata!=0);
 sum_last_awg_{suffix}=dut.sim_bd_i.sum_{suffix}.s0_axis_tdata;
 sum_last_rf_{suffix}=dut.sim_bd_i.sum_{suffix}.s1_axis_tdata;
end
final begin $fclose(sum_trace_{suffix});$fclose(sum_edges_{suffix});end
''')
    third='dut.sim_bd_i.axis_awg_tuning_v1_6'
    blocks.append(f'''awg_v2_raw_checker #(.CHANNEL(3)) raw_checker3 (
 .clk(clk_300000000),.rstn(resetn),.command_valid({third}.s_axis_tvalid),
 .command({third}.s_axis_tdata),.raw_samples({third}.core_samples));''')
    if args.rc_only:
        from rc_only_monitor import rc_only_monitor
        blocks.append('generate\n'+rc_only_monitor(3,third,shots)+'endgenerate\n')
    else:
        from system_monitor import area_monitor
        from qick_dc_area import point_plan
        planned=out/'planned_area_3.hex'
        planned.write_text(''.join(f'{point_plan(program,i,2)["area"] & ((1<<64)-1):016x}\n'
                          for i in range(program.sequence.sweep_point_count) for _ in range(2)))
        blocks.append('generate\n'+area_monitor(3,third,shots,planned)+'endgenerate\n')
    return top.replace('endmodule','\n'.join(blocks)+'\nendmodule')


def analyze(out, log, model, offset, shots, delay_us):
    checked=re.findall(r'OUTPUT_SUM_RESULT suffix=(\d+) samples=(\d+)',log)
    assert len(checked)==3 and all(int(n)>0 for _,n in checked)
    results=[]
    for port,suffix in enumerate((4,5,6)):
        with (out/f'sum_edges_{suffix}.csv').open() as stream: rows=list(csv.DictReader(stream))
        starts=[int(r['cycle']) for r in rows if r['stream']=='rf' and r['edge']=='1']
        stops=[int(r['cycle']) for r in rows if r['stream']=='rf' and r['edge']=='0']
        awg_starts=[int(r['cycle']) for r in rows if r['stream']=='awg' and r['edge']=='1']
        events=[e for e in model.output_events if e.tproc_ch==port and (e.word>>152)&255==0 and (e.word>>96)&0xffffffff]
        assert len(starts)==len(stops)==len(events)==shots,(suffix,len(starts),len(events))
        for start,stop,event in zip(starts,stops,events):
            assert start-event.cycle-offset==32, (suffix,start,event.cycle,offset)
            assert stop-start==(event.word>>128)&65535
            assert start-round(delay_us*300) in awg_starts, (suffix,start,awg_starts[:8])
        results.append(dict(suffix=suffix,shots=shots,start_skew_cycles=0,width_mismatches=0,
                            rf_command_to_sum_input_cycles=32,requested_delay_cycles=round(delay_us*300)))
    result=dict(sample_oracles=checked,pairs=results,combiner_pipeline_cycles=2)
    (out/'output_sum_result.json').write_text(json.dumps(result,indent=2))
    return result
