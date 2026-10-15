`timescale 1ns/1ps
// Actual 48-bit AWG/IIR and production DDS (vendor DDS model), direct commands.
// This is deliberately independent of Python's existing v4 RF advance.
module native_pair #(parameter integer PAIR=0)(
 input wire clk,rstn,input wire [159:0] acmd,rcmd,input wire av,rv,
 output wire [255:0] awg_raw,rf_raw,awg_final,rf_final,combined
);
 wire awvalid,rfvalid;
 axis_awg_tuning_v3 #(.DC_AREA_BITS(48),.EXTRA_Y_PIPE_STAGES(3)) awg(
  .s_axi_aclk(clk),.s_axi_aresetn(rstn),
  .s_axi_awaddr(6'd0),.s_axi_awprot(3'd0),.s_axi_awvalid(1'b0),
  .s_axi_wdata(32'd0),.s_axi_wstrb(4'd0),.s_axi_wvalid(1'b0),.s_axi_bready(1'b1),
  .s_axi_araddr(6'd0),.s_axi_arprot(3'd0),.s_axi_arvalid(1'b0),.s_axi_rready(1'b1),
  .aclk(clk),.aresetn(rstn),.s_axis_tdata(acmd),.s_axis_tvalid(av),
  .m_axis_tdata(awg_raw),.m_axis_tvalid(awvalid),.m_axis_tready(1'b1));
 sim_axis_signal_gen_v6_axis_signal_gen_v6 rf(
  .s_axi_aclk(clk),.s_axi_aresetn(rstn),
  .s_axi_awaddr(6'd0),.s_axi_awprot(3'd0),.s_axi_awvalid(1'b0),
  .s_axi_wdata(32'd0),.s_axi_wstrb(4'd0),.s_axi_wvalid(1'b0),.s_axi_bready(1'b1),
  .s_axi_araddr(6'd0),.s_axi_arprot(3'd0),.s_axi_arvalid(1'b0),.s_axi_rready(1'b1),
  .s0_axis_aclk(clk),.s0_axis_aresetn(rstn),.s0_axis_tdata(32'd0),.s0_axis_tvalid(1'b0),
  .aclk(clk),.aresetn(rstn),.s1_axis_tdata(rcmd),.s1_axis_tvalid(rv),
  .m_axis_tdata(rf_raw),.m_axis_tvalid(rfvalid),.m_axis_tready(1'b1));
 axis_output_sum_v2 #(.BYPASS(1)) awg_only(
  .aclk(clk),.aresetn(rstn),.s0_axis_tdata(awg_raw),.s0_axis_tvalid(awvalid),
  .s1_axis_tdata(256'd0),.s1_axis_tvalid(1'b0),.m_axis_tdata(awg_final),.m_axis_tready(1'b1));
 axis_output_sum_v2 rf_only(
  .aclk(clk),.aresetn(rstn),.s0_axis_tdata(256'd0),.s0_axis_tvalid(1'b0),
  .s1_axis_tdata(rf_raw),.s1_axis_tvalid(rfvalid),.m_axis_tdata(rf_final),.m_axis_tready(1'b1));
 axis_output_sum_v2 sum(
  .aclk(clk),.aresetn(rstn),.s0_axis_tdata(awg_raw),.s0_axis_tvalid(awvalid),
  .s1_axis_tdata(rf_raw),.s1_axis_tvalid(rfvalid),.m_axis_tdata(combined),.m_axis_tready(1'b1));
endmodule

module tb_native_alignment;
 reg clk=0;always #1.666667 clk=~clk;
 reg rstn=0,av=0,rv=0;
 reg [159:0] acmd[3],rcmd[3];
 wire [255:0] ar[3],rr[3],af[3],rf[3],y[3];
 for(genvar p=0;p<3;p=p+1)begin: pairs
  native_pair #(.PAIR(p)) dut(clk,rstn,acmd[p],rcmd[p],av,rv,ar[p],rr[p],af[p],rf[p],y[p]);
 end
 integer cycle=0,fd,checks=0,trial,offset,aw_at,rf_at,width;
 integer ar_on[3],rr_on[3],af_on[3],rf_on[3],af_off[3],rf_off[3];
 reg measure=0;
 always @(posedge clk)begin
  cycle=cycle+1;#0.02;
  if(measure) for(integer p=0;p<3;p=p+1)begin
   if($isunknown({ar[p],rr[p],af[p],rf[p],y[p]}))$fatal(1,"unknown output pair=%0d",p);
   if(ar[p]!=0 && ar_on[p]<0) ar_on[p]=cycle;
   if(rr[p]!=0 && rr_on[p]<0) rr_on[p]=cycle;
   if(af[p]!=0 && af_on[p]<0) af_on[p]=cycle;
   if(rf[p]!=0 && rf_on[p]<0) rf_on[p]=cycle;
   if(af[p]==0 && af_on[p]>=0 && af_off[p]<0) af_off[p]=cycle;
   if(rf[p]==0 && rf_on[p]>=0 && rf_off[p]<0) rf_off[p]=cycle;
  end
 end
 task tick;@(posedge clk);#0.1;endtask
 function automatic [159:0] setc(input integer v);
  reg[159:0] c;c=0;c[31:0]=v;c[145:144]=1;return c;
 endfunction
 function automatic [159:0] rfc(input integer gain,input integer words);
  reg[159:0] c;c=0;c[111:96]=gain;c[143:128]=words;
  c[145:144]=1;c[148]=1;return c; // DDS, phase reset, zero after pulse.
 endfunction
 task reset_trial;
  measure=0;rstn=0;av=0;rv=0;
  for(integer p=0;p<3;p=p+1)begin
   acmd[p]=0;rcmd[p]=0;ar_on[p]=-1;rr_on[p]=-1;af_on[p]=-1;rf_on[p]=-1;af_off[p]=-1;rf_off[p]=-1;
  end
  repeat(12)tick();@(negedge clk);rstn=1;repeat(100)tick();@(negedge clk);measure=1;
 endtask
 initial begin
  fd=$fopen("native_latency.csv","w");
  $fwrite(fd,"trial,pair,offset,awg_command,rf_command,awg_raw,rf_raw,awg_output,rf_output,awg_off,rf_off,width\n");
  for(trial=0;trial<32;trial=trial+1)begin
   case(trial%8)0:offset=-13;1:offset=-3;2:offset=-1;3:offset=0;4:offset=1;5:offset=3;6:offset=13;7:offset=30;endcase
   reset_trial();width=8+trial;aw_at=cycle+20;rf_at=aw_at+offset;
   for(integer n=0;n<110;n=n+1)begin
    av=(cycle+1==aw_at || cycle+1==aw_at+width);rv=(cycle+1==rf_at);
    for(integer p=0;p<3;p=p+1)begin
     acmd[p]=setc(cycle+1==aw_at ? (p==2 ? -4096 : (p+1)*4096):0);
     rcmd[p]=rfc(p==2 ? -8192 : (p+1)*4096,width);
    end
    tick();@(negedge clk);
   end
   for(integer p=0;p<3;p=p+1)begin
    $fwrite(fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d\n",trial,p,offset,aw_at,rf_at,ar_on[p],rr_on[p],af_on[p],rf_on[p],af_off[p],rf_off[p],width);
    if(ar_on[p]-aw_at+1!=16 || rr_on[p]-rf_at+1!=29 || af_on[p]-aw_at+1!=31 || rf_on[p]-rf_at+1!=31)
     $fatal(1,"native latency pair=%0d raw AWG/RF=%0d/%0d final=%0d/%0d",p,ar_on[p]-aw_at+1,rr_on[p]-rf_at+1,af_on[p]-aw_at+1,rf_on[p]-rf_at+1);
    if(rf_on[p]-af_on[p]!=offset || af_off[p]-af_on[p]!=width || rf_off[p]-rf_on[p]!=width)
     $fatal(1,"offset/width pair=%0d",p);
    checks=checks+1;
   end
  end
  $fclose(fd);$display("V5_NATIVE_ALIGNMENT_PASS pairs=3 trials=32 checks=%0d awg_native=16 rf_native=29 awg_final=31 rf_final=31",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"watchdog");end
endmodule
