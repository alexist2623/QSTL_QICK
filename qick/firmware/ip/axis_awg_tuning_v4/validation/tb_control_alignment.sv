`timescale 1ns/1ps
// Test the complete AWG wrapper. DC/RC command alignment is deliberately
// checked separately from the SET/RAMP datapath and the external output sum.
module tb_control_alignment;
 reg clk=0,rstn=0,command_valid=0;
 reg [159:0] command=0;
 wire [255:0] dac;
 wire valid;
 integer cycles=0,dc_cases=0;
 always #1.6665 clk=~clk;
 axis_awg_tuning_v4 #(.EXTRA_Y_PIPE_STAGES(3),.DC_AREA_BITS(48)) dut(
   .s_axi_aclk(clk),.s_axi_aresetn(rstn),.s_axi_awaddr(6'd0),.s_axi_awprot(3'd0),.s_axi_awvalid(1'b0),
   .s_axi_wdata(32'd0),.s_axi_wstrb(4'd0),.s_axi_wvalid(1'b0),.s_axi_bready(1'b1),
   .s_axi_araddr(6'd0),.s_axi_arprot(3'd0),.s_axi_arvalid(1'b0),.s_axi_rready(1'b1),
   .aclk(clk),.aresetn(rstn),.s_axis_tdata(command),.s_axis_tvalid(command_valid),
   .m_axis_tdata(dac),.m_axis_tvalid(valid),.m_axis_tready(1'b1),.s_axis_tready());
 awg_v4_raw_checker oracle(.clk(clk),.rstn(rstn),.command_valid(command_valid),
   .command(command),.raw_samples(dut.core_samples),.override_valid(1'b0),.override_value(32'sd0));
 always @(posedge clk) begin #0.005;cycles=cycles+1;end
 task automatic tick; @(posedge clk);#0.1;endtask
 task automatic send(input reg [159:0] packet);
   @(negedge clk);command=packet;command_valid=1;tick();
   @(negedge clk);command_valid=0;command=0;
 endtask
 function automatic [159:0] set_cmd(input integer value);
   reg [159:0] c; c=0;c[145:144]=1;c[31:0]=value;return c;
 endfunction
 function automatic [159:0] dc_cmd(input integer action);
   reg [159:0] c; reg [127:0] numerator;
   c=0;c[145:144]=3;c[150]=1;c[147:146]=action;
   if(action==1)c[31:0]=1284;
   if(action==2)begin numerator=128'd1<<64;c[63:0]=numerator/(16*97);c[95:64]=97;end
   return c;
 endfunction
 initial begin
   reg [159:0] c;
   integer issued,first_area,first_dac,timeout;
   repeat(10)tick();@(negedge clk);rstn=1;repeat(30)tick();
   // Configuration must not run ahead of the new common core pipeline.
   send(dc_cmd(0));issued=cycles;
   if(dut.area_enabled)$fatal(1,"DC ARM not delayed");
   for(integer i=1;i<=7;i=i+1)begin
     tick();if(dut.area_enabled!==(i==7))$fatal(1,"DC ARM delay is not 7 clocks i=%0d",i);
   end
   c=0;c[149]=1;c[145:144]=3;c[146]=1;c[147]=1;c[31:0]=0;
   send(c);
   for(integer i=1;i<=7;i=i+1)begin
     tick();if(dut.rc_enabled!==(i==7))$fatal(1,"RC enable delay is not 7 clocks i=%0d",i);
   end
   // Zero RC coefficient is an exact identity, while retaining its 11 stages.
   send(set_cmd(1024));issued=cycles;
   for(integer i=1;i<=23;i=i+1)begin
     tick();
     if(dut.core_samples!==(i>=7 ? {16{16'd1024}} : 256'd0))$fatal(1,"SET raw latency i=%0d",i);
     if(dac!==(i==23 ? {16{16'd1024}} : 256'd0))$fatal(1,"SET wrapper latency i=%0d",i);
   end
   send(set_cmd(0));repeat(30)tick();
   for(integer mode=1;mode<=2;mode=mode+1)begin
     // Re-arm and make a deterministic nonzero shot in each compensation mode.
     send(dc_cmd(0));repeat(20)tick();
     send(set_cmd(1024));repeat(30)tick();send(set_cmd(0));repeat(30)tick();
     if(dut.area_sum<=0)$fatal(1,"missing positive shot area");
     send(dc_cmd(mode));issued=cycles;first_area=-1;first_dac=-1;timeout=0;
     while(!dut.area_done || first_dac<0)begin
       tick();timeout=timeout+1;
       if(dut.area_fault || dut.rc_clipped)$fatal(1,"compensation fault mode=%0d",mode);
       if(dut.area_samples!=0 && first_area<0)first_area=cycles;
       if(dac!=0 && first_dac<0)first_dac=cycles;
       if(timeout>1000)$fatal(1,"compensation timeout mode=%0d",mode);
     end
     if(first_area-issued!=24 || first_dac-issued!=35)
       $fatal(1,"DC command latency mode=%0d area=%0d wrapper=%0d expected=24,35",mode,first_area-issued,first_dac-issued);
     if(dut.area_sum!=0)$fatal(1,"residual area mode=%0d",mode);
     repeat(20)tick();if(dac!=0)$fatal(1,"nonzero post-shot output");dc_cases=dc_cases+1;
   end
   $display("PASS CONTROL ALIGNMENT: RC/DC controls +7; SET core=7 wrapper=23; DC fixed-voltage/time area=24 wrapper=35 (external sum6+2 gives43); %0d zero-residual shots",dc_cases);
   $finish;
 end
 initial begin #1000000;$fatal(1,"watchdog");end
endmodule
