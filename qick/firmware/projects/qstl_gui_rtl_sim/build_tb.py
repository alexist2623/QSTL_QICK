"""Generate only boundary wiring/BFMs; every retained IP is production RTL."""
import argparse
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument('project', type=Path)
    args = p.parse_args()
    wrapper = Path((args.project/'wrapper_path.txt').read_text().strip()).read_text()
    ports = re.findall(r'^\s*(input|output)\s+(\[[^\]]+\])?\s*(\w+);', wrapper, re.M)
    topology = json.loads((HERE/'topology.json').read_text())
    buses = [b for b in topology['external_buses'] if any(n == b+'_awaddr' and d == 'input' for d,w,n in ports)]
    lines = ['// Generated boundary connections. See tb_body.svh for the test.',
             '`timescale 1ns/1fs', 'module tb_gui;', f'localparam NB={len(buses)};',
             'logic [31:0] host_addr=0, host_data=0;',
             'logic host_aw=0, host_w=0, host_ar=0, host_bready=0;', 'integer selected=-1;',
             'wire [NB-1:0] awready,wready,bvalid,arready,rvalid;',
             'wire [31:0] rdata[NB];', 'wire [1:0] bresp[NB];',
             'logic [63:0] pmem[0:8191];', 'logic [127:0] adc_rom[0:29];',
             'integer adc_index=0;', 'logic [63:0] pmem_data=0;',
             'logic [127:0] adc_data=0;', 'logic mem_bvalid=0;',
             'integer mem_address=0;', 'integer memory_file;']
    for d,w,n in ports:
        lines.append(f'{"logic" if d == "input" and (n.startswith("clk_") or n=="resetn") else "wire"} {w or ""} {n};')
    for d,w,n in ports:
        if d != 'input' or n.startswith('clk_') or n=='resetn':
            continue
        match = next(((i,b,n[len(b)+1:]) for i,b in enumerate(buses) if n.startswith(b+'_')), None)
        value = "'0"
        if match:
            i,b,field = match
            value = dict(awaddr='host_addr',araddr='host_addr',wdata='host_data',wstrb="'1",
                awvalid=f'host_aw && selected=={i}',wvalid=f'host_w && selected=={i}',
                arvalid=f'host_ar && selected=={i}',bready=f'host_bready && selected=={i}',rready="1'b1").get(field,"'0")
        elif n.endswith('pmem_do'): value = 'pmem_data'
        elif n=='ext_axis_dyn_readout_v1_0_s1_axis_tdata': value = 'adc_data'
        elif n=='ext_axis_dyn_readout_v1_0_s1_axis_tvalid': value = 'resetn'
        elif n.endswith(('_tready','_TREADY')): value = "1'b1"
        elif '_m_axi_' in n:
            value = dict(awready="1'b1",wready="1'b1",bvalid='mem_bvalid').get(n.rsplit('_',1)[-1],"'0")
        lines.append(f'assign {n} = {value};')
    for i,b in enumerate(buses):
        for field in ('awready','wready','bvalid','arready','rvalid','rdata','bresp'):
            lines.append(f'assign {field}[{i}] = {b}_{field};')
    lines += ['sim_bd_wrapper dut (', ',\n'.join(f'    .{n}({n})' for d,w,n in ports), ');']
    for freq in topology['clocks']:
        lines.append(f'initial clk_{freq}=0; always #{500000000/int(freq):.9f} clk_{freq}=~clk_{freq};')
    for tag,b in dict(TPROC='ext_axis_tproc64x32_x8_0_s_axi',DDR='ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi',
                      SWITCH='ext_axis_switch_ddr_S_AXI_CTRL').items():
        lines.append(f'localparam {tag}={buses.index(b)};')
    # Pre-NBA sampling records the AXIS transfer at the receiving clock edge.
    for i in range(1,9):
        path=f'dut.sim_bd_i.axis_tproc64x32_x8_0'
        lines += [f'always @(posedge clk_300000000) if (resetn && {path}.m{i}_axis_tvalid) begin',
                  f' $fwrite(events_file,"%0d,%0d,{i-1},%040h\\n",cycle,tproc_time,{path}.m{i}_axis_tdata);', 'end']
    for label,cell in [('sqcmd','axis_square_pulse_v1_0'),('awgcmd','axis_awg_tuning_v1_4'),('rfcmd','axis_signal_gen_v6_2')]:
        path=f'dut.sim_bd_i.{cell}'
        port='s1_axis' if label=='rfcmd' else 's_axis'
        lines += [f'always @(posedge clk_300000000) if (resetn && {path}.{port}_tvalid && {path}.{port}_tready)',
                  f' $fwrite(commands_file,"%0d,{label},%040h\\n",cycle,{path}.{port}_tdata);']
    lines += ['`include "tb_body.svh"','endmodule']
    (HERE/'tb_gui.sv').write_text('\n'.join(lines)+'\n')
    (HERE/'host_buses.json').write_text(json.dumps(buses,indent=2)+'\n')
    print(len(ports),'ports,',len(buses),'AXI-Lite slaves')


if __name__=='__main__': main()
