`timescale 1ns/1ps
// Actual controller/DSP primitive pipeline, including the minimum one-word
// RAMP -> one-word HOLD -> one-word falling RAMP and overlapping drain.
module tb_common_latency;
 reg clk=0,rstn=0,command_valid=0,override_valid=0;
 reg [159:0] command=0;
 reg signed [31:0] override_value=0;
 wire [255:0] samples;
 wire valid,ready;
 wire [31:0] status;
 wire signed [31:0] current;
 integer commands=0,triples=0,hold2_triples=0,ramp2_triples=0;
 always #1.6665 clk=~clk;
 v4_awg_tuning_ctrl #(.EXTRA_Y_PIPE_STAGES(3)) dut(
   .aclk(clk),.aresetn(rstn),.s_axis_tdata(command),.s_axis_tvalid(command_valid),
   .s_axis_tready(ready),.axi_override_value(override_value),.axi_override_valid(override_valid),
   .m_axis_tdata(samples),.m_axis_tvalid(valid),.m_axis_tready(1'b0),
   .status_o(status),.current_value_o(current));
 awg_v4_raw_checker oracle(.clk(clk),.rstn(rstn),.command_valid(command_valid),
   .command(command),.raw_samples(samples),.override_valid(override_valid),.override_value(override_value));
 task automatic tick; @(posedge clk);#0.1; endtask
 task automatic issue(input integer opcode,input integer target,input integer duration,input integer step,input bit zero);
   @(negedge clk); command=0; command_valid=1; override_valid=0;
   command[145:144]=opcode; command[31:0]=target; command[86:64]=duration;
   command[127:96]=step; command[146]=zero; tick(); commands=commands+1;
 endtask
 task automatic idle(input integer cycles);
   @(negedge clk); command_valid=0;override_valid=0;command=0;
   repeat(cycles)tick();
 endtask
 task automatic override_now(input integer value);
   @(negedge clk); override_value=value;override_valid=1;command_valid=1;
   command=0;command[145:144]=1;command[31:0]=~value;tick();
   if(current!==$signed(samples[15:0]))$fatal(1,"override readback is not physical");
 endtask
 always @(posedge clk) begin
   #0.03;
   if(rstn && (!valid || !ready || current!==$signed(samples[15:0])))
     $fatal(1,"continuous output, ignored downstream ready, or physical readback failure");
 end
 initial begin
   integer amplitude,step,n;
   // Vendor glbl holds GSR for the first 100 ns; do not launch a DSP test
   // until both that startup reset and the explicit DUT reset have ended.
   repeat(40)tick();@(negedge clk);rstn=1;idle(10);
   // Each command is one aclk apart. All 16 lanes and latency are checked.
   for(integer trial=1;trial<=100;trial=trial+1) begin
     amplitude=(trial%2 ? 1 : -1)*(400+trial*4);
     step=(64'(amplitude)<<<18)/15;
     issue(2,amplitude,16,step,0);
     issue(1,amplitude,0,0,0);
     issue(2,0,16,-step,0); triples=triples+1;
   end
   idle(12);
   // Explicit 2/1/2 clocks: two rising words, one HOLD word, two falling
   // words. Following commands arrive exactly at each issue boundary.
   for(integer trial=1;trial<=100;trial=trial+1) begin
     amplitude=(trial%2 ? 1 : -1)*(1200+trial*4);
     step=(64'(amplitude)<<<18)/31;
     issue(2,amplitude,32,step,0);idle(1);
     issue(1,amplitude,0,0,0);issue(2,0,32,-step,0);idle(1);
     ramp2_triples=ramp2_triples+1;
   end
   idle(12);
   // A two-clock HOLD is the same constant value for two complete words;
   // the falling RAMP starts at T+3, without adding hidden startup spacing.
   for(integer trial=1;trial<=100;trial=trial+1) begin
     amplitude=(trial%2 ? 1 : -1)*(800+trial*4);
     step=(64'(amplitude)<<<18)/15;
     issue(2,amplitude,16,step,0);issue(1,amplitude,0,0,0);
     idle(1);issue(2,0,16,-step,0);hold2_triples=hold2_triples+1;
   end
   idle(12);
   // SET zero-hold must seed the following RAMP with zero while the previous
   // nonzero SET word still drains. Ordinary SET 0 does not abort old tails.
   issue(1,12340,0,0,1);issue(2,600,16,10485760,0);issue(1,0,0,0,0);
   issue(1,32767,0,0,0);issue(2,-32768,16,-1145041169,0);
   issue(1,32'sh7fffffff,0,0,0);issue(2,0,16,-572592674,0);
   idle(12);
   // Partial final words, arbitrary 32-bit steps and exactly adjacent
   // multiword transitions. The expected lane formula uses wide integers.
   for(integer trial=0;trial<400;trial=trial+1) begin
     n=1+trial%130; amplitude=$signed($urandom); step=$signed($urandom);
     issue(2,amplitude,n,step,0);
     if((n+15)/16>1) idle((n+15)/16-1);
     issue(1,-trial*4,0,0,trial%7==0);
   end
   idle(12);
   // Commands before the issue duration ends remain rejected, but the last
   // issue edge accepts a replacement. Never confuse this with drain busy.
   issue(2,1000,64,4161015,0);issue(1,20000,0,0,0);issue(2,-20000,16,0,0);
   idle(1);issue(1,0,0,0,0);idle(12);
   // Abort at every pending stage; no delayed value may reappear afterwards.
   for(integer delay=0;delay<9;delay=delay+1) begin
     issue(1,4000,0,0,0);issue(2,8000,160,6594820,0);
     if(delay>0)idle(delay);
     override_now(delay%2 ? -400 : 0);idle(15);
   end
   issue(1,880,0,0,0);issue(2,-880,16,-30758229,0);idle(15);
   if(!status[0] || status[1] || !status[6])$fatal(1,"pipeline did not fully drain");
   if(oracle.ramps<500 || oracle.sets<500 || oracle.overrides!=9 || oracle.dropped!=2)
     $fatal(1,"coverage missing ramps=%0d sets=%0d aborts=%0d dropped=%0d",oracle.ramps,oracle.sets,oracle.overrides,oracle.dropped);
   $display("PASS COMMON LATENCY: SET/RAMP both 7 clocks; %0d 1/1/1, %0d 1/2/1 and %0d 2/1/2 RAMP/HOLD/fall triples; %0d commands; all lanes, tails, partial words, readback, busy and abort",triples,hold2_triples,ramp2_triples,commands);
   $finish;
 end
 initial begin #1000000;$fatal(1,"watchdog");end
endmodule
