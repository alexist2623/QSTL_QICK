`timescale 1ns/1ps
module tb_rc_limits;
logic clk=0,rstn=0,av=0,sv=0;
always #1.666667 clk=~clk;
logic [159:0] acmd=0,scmd=0;
wire [255:0] ay,sy;
axis_awg_tuning_v1 #(.EXTRA_Y_PIPE_STAGES(3)) a (
 .aclk(clk),.aresetn(rstn),.s_axis_tdata(acmd),.s_axis_tvalid(av),.m_axis_tdata(ay),.m_axis_tready(1'b1),
 .s_axi_aclk(clk),.s_axi_aresetn(rstn),.s_axi_awvalid(1'b0),.s_axi_wvalid(1'b0),.s_axi_arvalid(1'b0),
 .s_axi_bready(1'b1),.s_axi_rready(1'b1),.s_axi_awaddr(6'd0),.s_axi_awprot(3'd0),
 .s_axi_wdata(32'd0),.s_axi_wstrb(4'd0),.s_axi_araddr(6'd0),.s_axi_arprot(3'd0));
axis_square_pulse_v1 s (
 .aclk(clk),.aresetn(rstn),.s_axis_tdata(scmd),.s_axis_tvalid(sv),.m_axis_tdata(sy),.m_axis_tready(1'b1),
 .s_axi_aclk(clk),.s_axi_aresetn(rstn),.s_axi_awvalid(1'b0),.s_axi_wvalid(1'b0),.s_axi_arvalid(1'b0),
 .s_axi_bready(1'b1),.s_axi_rready(1'b1),.s_axi_awaddr(6'd0),.s_axi_awprot(3'd0),
 .s_axi_wdata(32'd0),.s_axi_wstrb(4'd0),.s_axi_araddr(6'd0),.s_axi_arprot(3'd0));
task awg_config(input bit enable,input bit clear);
 @(negedge clk);av=1;acmd=0;acmd[31:0]=32'd2932031007;
 acmd[149]=1;acmd[145:144]=3;acmd[146]=enable;acmd[147]=clear;
 @(negedge clk);av=0;
endtask
task square_config(input bit enable,input bit rc,input bit clear);
 @(negedge clk);sv=1;scmd=0;scmd[79:64]=30000;
 scmd[127:80]=48'd87960930222080; // 30000 * 2^48 / (2*10 us*4800 MHz)
 scmd[128]=enable;scmd[130]=rc;scmd[131]=clear;
 @(negedge clk);sv=0;
endtask
initial begin
 repeat(40)@(negedge clk);rstn=1;
 awg_config(1,1);square_config(1,1,1);
 @(negedge clk);av=1;acmd=0;acmd[31:0]=30000;acmd[145:144]=1;
 @(negedge clk);av=0;
 repeat(1200)@(negedge clk);
 if(ay!=={16{16'd32764}} || sy!=={16{16'd32764}} || !a.rc_clipped || !s.rc_clipped)
  $fatal(1,"Expected positive DAC saturation, not wraparound");
 // A mode update takes exactly the fixed 11-cycle AWG output pipeline.
 awg_config(0,0);
 for(integer n=1;n<=10;n=n+1)begin @(posedge clk);#0.001;
  if(ay!=={16{16'd32764}})$fatal(1,"AWG bypass changed early: %0d",n);
 end
 @(posedge clk);#0.001;if(ay!=={16{16'd30000}})$fatal(1,"AWG bypass latency != 11");
 // DDS command four cycles plus the same eleven-cycle compensation pipeline.
 square_config(1,0,0);
 for(integer n=1;n<=14;n=n+1)begin @(posedge clk);#0.001;
  if(sy!=={16{16'd32764}})$fatal(1,"Square bypass changed early: %0d",n);
 end
 @(posedge clk);#0.001;if(sy!=={16{16'd30000}})$fatal(1,"Square bypass latency != 15");
 square_config(0,1,0);
 repeat(15)@(posedge clk);#0.001;
 if(sy!==0)$fatal(1,"Mute must output zero even with nonzero integral history");
 awg_config(1,1);repeat(40)@(negedge clk);
 if(a.rc_clipped)$fatal(1,"Explicit history reset must clear clipping status");
 // Deposit a near-limit history to exercise the 72-bit rail directly.
 // The actual production datapath performs the saturation arithmetic.
 a.GEN_RC.rc.integral={1'b0,{71{1'b1}}};
 repeat(20)@(negedge clk);
 if(ay!=={16{16'd32764}} || a.GEN_RC.rc.integral!=={1'b0,{71{1'b1}}})
  $fatal(1,"Integral or corrected-sample overflow wrapped");
 @(negedge clk);av=1;acmd=0;acmd[31:0]=-30000;acmd[145:144]=1;
 @(negedge clk);av=0;
 repeat(20)@(negedge clk);
 a.GEN_RC.rc.integral={1'b1,{71{1'b0}}};
 repeat(20)@(negedge clk);
 if(ay!=={16{16'h8000}} || a.GEN_RC.rc.integral!=={1'b1,{71{1'b0}}})
  $fatal(1,"Negative integral or corrected-sample overflow wrapped");
 $display("PASS: real IP clipping, 72-bit history rail, explicit clear, matched bypass, and mute");
 $finish;
end
endmodule
