"""Create full-DUT and focused two-AWG benches from the same production netlist.

The focused variant removes only unrelated instances. Retained instance text,
parameters, nets and real implementation sources are unchanged. Full-DUT
prefix equivalence checks cover the same PMEM/DMEM image and both AWG outputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('build',type=Path)
    args=parser.parse_args();out=args.build/'complex_awg';out.mkdir(exist_ok=True)
    source=args.build/'qstl_gui_rtl_sim.gen/sources_1/bd/sim_bd/sim/sim_bd.v'
    netlist=source.read_text()
    keep={'axis_tproc64x32_x8_0','axis_tmux_v1_0','axis_tmux_v1_1',
          'axis_awg_tuning_v1_4','axis_awg_tuning_v1_5',
          'axis_register_slice_8','axis_register_slice_9',
          'axis_register_slice_10','axis_register_slice_21',
          'axis_set_reg_0','qick_vec2bit_0',
          *('xlconstant_'+str(i) for i in range(5))}
    pattern=re.compile(r'^  (sim_bd_\w+) (\w+)\s*\n.*?\);',re.M|re.S)
    matches=list(pattern.finditer(netlist))
    assert len(matches)==78,len(matches)
    assert keep<={m[2] for m in matches}
    def retained(m):return m[0] if m[2] in keep else ''
    focus=pattern.sub(retained,netlist)
    focus=focus.replace('module sim_bd\n','module focus_bd\n',1)
    tieoffs=[]
    for i in range(4):
        tieoffs.extend([f'assign axis_clk_cnvrt_avg_{i}_M_AXIS_TDATA = 64\'b0;',
                        f'assign axis_clk_cnvrt_avg_{i}_M_AXIS_TVALID = 1\'b0;'])
    for i in range(3,8):tieoffs.append(f'assign axis_tproc64x32_x8_0_m{i}_axis_TREADY = 1\'b1;')
    focus=focus.replace('endmodule','\n'.join(tieoffs)+'\nendmodule')
    (out/'focus_bd.v').write_text(focus)
    wrapper_path=Path((args.build/'wrapper_path.txt').read_text().strip())
    wrapper=wrapper_path.read_text().replace('module sim_bd_wrapper','module focus_bd_wrapper',1)
    wrapper=wrapper.replace('sim_bd sim_bd_i','focus_bd sim_bd_i',1)
    (out/'focus_bd_wrapper.v').write_text(wrapper)
    copied={m[2]:m[0] for m in pattern.finditer(focus)}
    assert all(copied[m[2]]==m[0] for m in matches if m[2] in keep)
    audit=dict(source=str(source),source_sha256=sha(source.read_bytes()),
               retained_cells=sorted(keep),removed_cells=sorted({m[2] for m in matches}-keep),
               retained_instance_text_identical=True,
               instances={m[2]:sha(m[0].encode()) for m in matches if m[2] in keep},
               focus_sha256=sha((out/'focus_bd.v').read_bytes()),tieoffs=tieoffs,
               note='Unused readout inputs idle and unused tProcessor output ports ready; no datapath replacement.')
    (HERE/'complex_topology_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    # Reuse the verified external port wiring and AXI host mux, while replacing
    # only the observation/driver body for this two-channel experiment.
    original=(HERE/'tb_gui.sv').read_text()
    prefix=original[:original.index('always @(posedge clk_300000000) if (resetn && dut.')]
    for full in (False,True):
        name='tb_complex_full' if full else 'tb_complex_focus'
        text=prefix.replace('module tb_gui;',f'module {name};',1)
        if not full:text=text.replace('sim_bd_wrapper dut','focus_bd_wrapper dut',1)
        text+='`include "tb_complex_body.svh"\nendmodule\n'
        (out/(name+'.sv')).write_text(text)
    (out/'tb_complex_body.svh').write_bytes((HERE/'tb_complex_body.svh').read_bytes())
    print(json.dumps(dict(retained=len(keep),output=str(out),retained_instances_identical=True)))


if __name__=='__main__':main()
