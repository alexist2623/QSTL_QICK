"""Prepare an isolated real-tProc/SG-v6 testbench; never touch production RTL.

The existing generated v4 BD uses the vendor DDS, real SG-v6 data_writer and
BRAM. Only its DMA input is driven by a host AXIS model. No waveform memory is
patched hierarchically and no generator output is forced.
"""
from pathlib import Path
import hashlib
import re
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from extension_v5 import delayed_oracle

ROOT = Path('C:/GIT_Workspace/QSTL_QICK')
BASE = Path('F:/Vivado_Output/a3sim1/rc_precomp_repeat_reset_hold_duration_2x2_v4_all_20261014_exact10us_hold1_output_sum_awg_v3')
SHARED = Path('F:/Vivado_Output/a3sim1/qstl_gui_rtl_sim.sim/sim_1/behav/xsim')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


DMA = r'''
// Real host AXI writes configure SG-v6; AXIS models only the upstream DMA.
logic [31:0] envelope_dma_data=0;
logic [2:0] envelope_dma_valid=0;
wire [2:0] envelope_dma_ready={
 dut.sim_bd_i.axis_switch_gen_M03_AXIS_TREADY,
 dut.sim_bd_i.axis_switch_gen_M01_AXIS_TREADY,
 dut.sim_bd_i.axis_switch_gen_M00_AXIS_TREADY};
initial begin
 force dut.sim_bd_i.axis_switch_gen_M00_AXIS_TDATA=envelope_dma_data;
 force dut.sim_bd_i.axis_switch_gen_M01_AXIS_TDATA=envelope_dma_data;
 force dut.sim_bd_i.axis_switch_gen_M03_AXIS_TDATA=envelope_dma_data;
 force dut.sim_bd_i.axis_switch_gen_M00_AXIS_TVALID=envelope_dma_valid[0];
 force dut.sim_bd_i.axis_switch_gen_M01_AXIS_TVALID=envelope_dma_valid[1];
 force dut.sim_bd_i.axis_switch_gen_M03_AXIS_TVALID=envelope_dma_valid[2];
end
task automatic load_envelope(input integer index,input integer gen,input integer target);
 integer fd,scan,value,count,timeout;
 begin
  fd=$fopen($sformatf("%s/envelope_%0d.hex",case_dir,gen),"r");
  if(!fd) $fatal(1,"Missing envelope input gen=%0d",gen);
  host_write(target,0,0); // START_ADDR_REG in scalar IQ samples.
  host_write(target,4,1); // WE_REG crosses into the data_writer clock.
  repeat(10) @(negedge clk_99999985);
  count=0;
  while(!$feof(fd)) begin
   scan=$fscanf(fd,"%h\n",value);
   if(scan==1) begin
    @(negedge clk_99999985);
    envelope_dma_data=value;envelope_dma_valid=3'b001<<index;
    timeout=0;
    @(posedge clk_99999985);
    while(!envelope_dma_ready[index]) begin
     @(posedge clk_99999985);timeout=timeout+1;
     if(timeout>1000) $fatal(1,"Envelope DMA timeout gen=%0d",gen);
    end
    count=count+1;
   end
  end
  @(negedge clk_99999985);envelope_dma_valid=0;
  repeat(10) @(negedge clk_99999985);
  host_write(target,4,0);
  $fclose(fd);
  if(count>16384) $fatal(1,"Envelope exceeds configured BRAM gen=%0d",gen);
  $display("ENVELOPE_LOAD gen=%0d samples=%0d AXIS=1 direct_bram_write=0",gen,count);
 end
endtask
'''


def monitor():
    """Full-rate words before/after sum, including zero padded tails."""
    blocks = []
    for channel, suffix, instance in ((0, 4, 0), (2, 5, 1), (4, 6, 3)):
        blocks.append(f'''
integer fine_trace_{channel};
initial begin
 wait(output_dir!="");
 fine_trace_{channel}=$fopen({{output_dir,"/fine_{channel}.csv"}},"w");
 $fwrite(fine_trace_{channel},"cycle,rf,awg,sum\\n");
end
always @(posedge clk_300000000) if(resetn && cycle_at_start>0 && cycle>=cycle_at_start) begin
 #0.005;
 if($isunknown(dut.sim_bd_i.sum_{suffix}.s1_axis_tdata))
  $fatal(1,"Unknown RF sample channel={channel} cycle=%0d",cycle);
 $fwrite(fine_trace_{channel},"%0d,%064h,%064h,%064h\\n",cycle,
  dut.sim_bd_i.sum_{suffix}.s1_axis_tdata,
  dut.sim_bd_i.sum_{suffix}.s0_axis_tdata,
  dut.sim_bd_i.sum_{suffix}.m_axis_tdata);
end
''')
    return '\n'.join(blocks)


def prepare(build, copy_libraries=True):
    build = Path(build)
    template = build / 'template'
    template.mkdir()
    for name in ('rc_bd.v', 'rc_wrapper.v'):
        shutil.copy2(BASE / name, template / name)
        if name=='rc_bd.v':
            p=template/name;p.write_text(p.read_text().replace('axis_output_sum_v1 #','axis_output_sum_v2 #'))
    old = (BASE / 'tb_rc_gui.sv').read_text()
    # Keep host AXI and the real PMEM/DMEM path. The old fixture's area and
    # analog-RC assertions have different shot/sequence requirements.
    end = old.index('\nend\n', old.index('initial begin : test')) + len('\nend\n')
    top = old[:end]
    top = top.replace('task automatic host_write(', DMA + '\ntask automatic host_write(', 1)
    top = top.replace('cycle_at_start=cycle;host_write(TPROC,4,1);',
        'load_envelope(0,0,11);load_envelope(1,2,12);load_envelope(2,4,14);\n'
        ' cycle_at_start=cycle;host_write(TPROC,4,1);', 1)
    # Preserve the exact, independent, per-lane v4 output-sum oracle.
    start = old.index('integer sum_checks_4=0;')
    stop = old.index('integer sum_trace_4,', start)
    top += '\n' + old[start:stop] + monitor() + '\nendmodule\n'
    top=delayed_oracle(top)
    (template / 'tb_rc_gui.sv').write_text(top)
    project = (BASE / 'sources.prj').read_text().replace(BASE.as_posix(), template.as_posix())
    project=project.replace('axis_output_sum_v1/src/axis_output_sum_v1.sv','axis_output_sum_v2/src/axis_output_sum_v2.sv')
    (template / 'sources.prj').write_text(project)
    if copy_libraries:
        sim = build / 'sim'
        (sim / 'xsim.dir').mkdir(parents=True)
        shutil.copytree(SHARED / 'xsim.dir/xil_defaultlib', sim / 'xsim.dir/xil_defaultlib')
        shutil.copy2(SHARED / 'xsim.ini', sim / 'xsim.ini')
    cached = Path('F:/Vivado_Output/a3sim1/namespaced')
    equivalence = []
    for prefix,name in ((41,'axis_signal_gen_v6.v'),(42,'signal_gen_top.v'),
                        (43,'signal_gen.v'),(45,'ctrl_sg_v6.sv'),(49,'data_writer.vhd')):
        original = ROOT/'qick/firmware/ip/axis_signal_gen_v6/src'/name
        copied = cached/f'{prefix:03d}_{name}'
        def normalize(text):
            # The original namespace rewrite also lowercased "Fifo" in comments.
            text = text.replace('sim_axis_signal_gen_v6_','')
            return re.sub(r'(?m)//[^\n]*$','',text)
        equal = normalize(copied.read_text()) == normalize(original.read_text())
        assert equal, f'Cached SG-v6 core changed beyond namespace: {name}'
        equivalence.append(dict(source=str(original),source_sha256=sha(original),
                                cached_source=str(copied),cached_sha256=sha(copied),
                                equal_after_namespace_and_comment_removal=equal))
    return dict(
        libraries=list(dict.fromkeys(re.findall(r'-L (\w+)', (SHARED / 'elaborate.bat').read_text()))),
        template_sources={str(p): sha(p) for p in template.iterdir() if p.is_file()},
        cached_sg_v6_source_equivalence=equivalence,
        rtl_version='unchanged routing, SG-v6 vendor DDS, candidate v5 axis_output_sum_v2',
        envelope_load='host AXI START_ADDR/WE; handshaken scalar IQ AXIS stream into actual data_writer/BRAM',
        board_access=False, production_rtl_modified=False, shared_library_writes=False)
