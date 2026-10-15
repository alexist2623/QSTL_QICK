"""Independent delayed-AWG sum/output oracle for new v5 GUI compiler inputs."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from types import SimpleNamespace
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=Path('C:\\GIT_Workspace\\QSTL_QICK')
OLD=ROOT/'qick/firmware/ip/axis_output_sum_v1/validation/gui_rtl_extension.py'
HWH=Path('F:/Vivado_Output/a5full1/bitstream.hwh')
spec=importlib.util.spec_from_file_location('old_sum_validation',OLD)
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
HOLD=ROOT/'analysis_results/awg_tuning_v4/full_regression_20261014/hold10us_support.py'
spec=importlib.util.spec_from_file_location('old_hold_support',HOLD)
hold=importlib.util.module_from_spec(spec);spec.loader.exec_module(hold)
extra_monitor=hold.extra_monitor
signed_lanes=hold.signed_lanes

def source_hashes(gui):
    result=old.source_hashes(gui)
    for path in list(HERE.glob('*.py'))+list(HERE.glob('*.svh'))+[ROOT/'qick/firmware/ip/axis_output_sum_v2/src/axis_output_sum_v2.sv',ROOT/'qick/firmware/projects/qstl_gui_rtl_sim/soccfg.json']:
        result[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    result[str(HWH)]=hashlib.sha256(HWH.read_bytes()).hexdigest()
    return result

def configure(cfg):
    import qick.sim
    from qick.ip import QickMetadata
    from qick.output_sum import apply_output_sum_config,output_sum_config
    metadata=QickMetadata(SimpleNamespace(parser=SimpleNamespace(root=ET.parse(HWH).getroot())))
    routes=[]
    for awg,rf,suffix,rf_suffix in ((1,0,4,0),(3,2,5,1),(5,4,6,3)):
        cfg['gens'][rf]['dac']=cfg['gens'][awg]['dac']
        for channel,path in ((awg,f'axis_awg_tuning_v3_{suffix}'),(rf,f'axis_signal_gen_v6_{rf_suffix}')):
            route=output_sum_config(metadata,path)
            assert route['output_sum_version']==2 and route['output_sum_awg_delay_cycles']==13
            assert route['post_output_latency_cycles']==2 and not route['output_sum_bypass']
            apply_output_sum_config(cfg['gens'][channel],route)
            assert cfg['gens'][channel]['output_latency_cycles']==31
            routes.append(dict(channel=channel,fullpath=path,route=route))
    cfg['validation_candidate_hwh']=str(HWH)
    cfg['validation_candidate_hwh_sha256']=hashlib.sha256(HWH.read_bytes()).hexdigest()
    cfg['validation_routes']=routes

def connect(text):return old.connect(text).replace('axis_output_sum_v1 #','axis_output_sum_v2 #')

def delayed_oracle(top):
    for suffix in (4,5,6):
        token=f'logic [255:0] sum_expected_{suffix}=0;'
        assert token in top
        top=top.replace(token,token+f'\nlogic [255:0] history_{suffix} [0:12];\nlogic [12:0] history_valid_{suffix}=0;')
        top=top.replace(f'if(!resetn) sum_expected_{suffix}=0;',f'if(!resetn) begin sum_expected_{suffix}=0;history_valid_{suffix}=0;end')
        top=top.replace(f'dut.sim_bd_i.sum_{suffix}.s0_axis_tvalid ? $signed(dut.sim_bd_i.sum_{suffix}.s0_axis_tdata[lane*16+:16])',f'history_valid_{suffix}[12] ? $signed(history_{suffix}[12][lane*16+:16])')
        anchor=f'  #0.003;\n  if(cycle>20 && dut.sim_bd_i.sum_{suffix}.m_axis_tdata!==sum_expected_{suffix})'
        update=f'  for(integer h=12;h>0;h=h-1) history_{suffix}[h]=history_{suffix}[h-1];\n  history_{suffix}[0]=dut.sim_bd_i.sum_{suffix}.s0_axis_tdata;\n  history_valid_{suffix}={{history_valid_{suffix}[11:0],dut.sim_bd_i.sum_{suffix}.s0_axis_tvalid}};\n'
        assert anchor in top
        top=top.replace(anchor,update+anchor).replace(f'v4 SUM mismatch suffix={suffix}',f'v5 SUM mismatch suffix={suffix}')
    return top

def monitor(top,shots,program,out,args):
    (out/'configured_soccfg.json').write_text(json.dumps(program.soccfg._cfg,indent=2))
    (out/'v5_route_metadata.json').write_text(json.dumps(dict(hwh=str(HWH),hwh_sha256=hashlib.sha256(HWH.read_bytes()).hexdigest(),routes=program.soccfg['validation_routes']),indent=2))
    return delayed_oracle(old.monitor(top,shots,program,out,args))

def physical_rows(out,suffix):
    with (out/f'physical_{suffix}.csv').open() as stream:
        return [dict(cycle=int(row['cycle']),**{k:int(row[k],16) for k in ('raw','awg','rf','sum','dac')}) for row in csv.DictReader(stream)]

def physical_oracle(rows,suffix):
    by={r['cycle']:r for r in rows};samples=0
    for row in rows[50:]:
        awg=by[row['cycle']-25]['awg'];rf=by[row['cycle']-12]['rf']
        values=[]
        for a,b in zip(signed_lanes(awg),signed_lanes(rf)):
            total=a+b
            values.append(32764 if total>32764 else -32768 if total< -32768 else ((total+2)>>2)*4)
        expected=sum((v&65535)<<(16*i) for i,v in enumerate(values))
        assert row['dac']==expected,('delayed physical sum mismatch',suffix,row['cycle'])
        samples+=16
    return samples

def _analyze(out,log,model,offset,shots,delay_us,hold_index=None):
    checked=re.findall(r'OUTPUT_SUM_RESULT suffix=(\d+) samples=(\d+)',log)
    assert len(checked)==3 and all(int(n)>0 for _,n in checked)
    pairs=[];delay=round(delay_us*300)
    for port,suffix in enumerate((4,5,6)):
        rows=physical_rows(out,suffix)
        starts=[r['cycle'] for a,r in zip(rows,rows[1:]) if not a['rf'] and r['rf']]
        stops=[r['cycle'] for a,r in zip(rows,rows[1:]) if a['rf'] and not r['rf']]
        events=[e for e in model.output_events if e.tproc_ch==port]
        rf=[e for e in events if (e.word>>152)&255==0 and (e.word>>96)&0xffffffff]
        sets=[e for e in events if (e.word>>152)&255==1 and (e.word>>144)&3==1]
        ramps=[e for e in events if (e.word>>152)&255==1 and (e.word>>144)&3==2]
        assert len(starts)==len(stops)==len(rf)==shots,(suffix,len(starts),len(stops),len(rf),shots)
        measures=[]
        for shot,(start,stop,event) in enumerate(zip(starts,stops,rf)):
            assert start-event.cycle-offset==32,(suffix,start,event.cycle,offset)
            width=(event.word>>128)&65535
            assert stop-start==width
            anchor=next(e for e in sets if e.cycle==event.cycle-delay)
            assert start==(anchor.cycle+offset+32)+delay
            item=dict(shot=shot,awg_hold_command=anchor.cycle,rf_command=event.cycle,requested_offset_cycles=delay,
                rf_sum_input_start=start,rf_sum_input_stop=stop,awg_hold_physical_start=anchor.cycle+offset+44,
                rf_physical_start=start+12,rf_physical_stop=stop+12,width_cycles=width,requested_timing_error_cycles=0)
            if hold_index is not None:
                first,second=ramps[shot*2:shot*2+2]
                assert (first.word>>64)&((1<<23)-1)==48000 and (second.word>>64)&((1<<23)-1)==48000
                assert second.cycle-first.cycle==6001
                ramp=first if hold_index==1 else second
                assert anchor.cycle-ramp.cycle==3008
                assert width==3000-delay
                item.update(hold=hold_index,ramp_duration_cycles=3000,existing_ramp_startup_cycles=7,existing_ramp_guard_cycles=1)
            measures.append(item)
        pairs.append(dict(suffix=suffix,shots=shots,measurements=measures,physical_sample_checks=physical_oracle(rows,suffix),unexpected_rf_pulses=0))
    result=dict(pairs=pairs,sample_oracles=checked,awg_delay_cycles=13,combiner_pipeline_cycles=2,output_register_cycles=10,
                timing_profile='v5 candidate HWH metadata, native AWG=RF=31',explicit_rf_offset_us=delay_us,board_measurement=False)
    (out/'output_sum_result.json').write_text(json.dumps(result,indent=2));return result

def analyze(out,log,model,offset,shots,delay_us):return _analyze(out,log,model,offset,shots,delay_us)
def analyze_hold(out,log,model,offset,shots,hold_index):return _analyze(out,log,model,offset,shots,.1,hold_index)


def analyze_composite(out,log,model,offset,shots,args,program):
    checked=re.findall(r'OUTPUT_SUM_RESULT suffix=(\d+) samples=(\d+)',log)
    assert len(checked)==3 and all(int(n)>0 for _,n in checked)
    pairs=[];tables=[]
    for port,suffix in enumerate((4,5,6)):
        rows=physical_rows(out,suffix)
        starts=[r['cycle'] for a,r in zip(rows,rows[1:]) if not a['rf'] and r['rf']]
        stops=[r['cycle'] for a,r in zip(rows,rows[1:]) if a['rf'] and not r['rf']]
        events=[e for e in model.output_events if e.tproc_ch==port and (e.word>>152)&255==0 and (e.word>>96)&0xffffffff]
        n=args.virtual_case.get('n',2) if port==0 else 1
        assert len(starts)==len(stops)==len(events)==shots*n,(port,len(starts),len(events),shots*n)
        for start,stop,event in zip(starts,stops,events):
            assert start-event.cycle-offset==32
            assert stop-start==(event.word>>128)&65535
        tables.append(starts)
        pairs.append(dict(suffix=suffix,pulses=len(starts),command_to_sum_input_cycles=32,width_errors=0,physical_sample_checks=physical_oracle(rows,suffix)))
    n=args.virtual_case.get('n',2);tau=args.virtual_case.get('tau',.2)
    for shot in range(shots):
        coords=program.sequence.sweep_coordinate(shot//2)
        duration=next((float(v) for a,v in zip(program.sequence.sweep_axes,coords) if a.axis_kind=='rf_duration'),.1)
        for pulse in range(n):
            requested_delay=round((tau*(pulse+.5)+pulse*duration)*300)
            assert tables[0][shot*n+pulse]-tables[1][shot]==requested_delay
    result=dict(sample_oracles=checked,pairs=pairs,awg_delay_cycles=13,combiner_pipeline_cycles=2,output_register_cycles=10,
        cpmg_delay_checks=shots*n,explicit_rf_offset_us=args.sum_rf_delay_us,board_measurement=False)
    (out/'output_sum_result.json').write_text(json.dumps(result,indent=2));return result
