// Real DDR capture IP driven by real tProcessor -> axis_set_reg GPIO.
// The FIR stream is a synthetic timestamp tag every 300 fabric clocks.
// This checks capture count/delay/queue behavior, not FIR arithmetic or ADC data.
logic ddr_armed=0;
integer ddr_file, ddr_accepts=0, ddr_matures=0, ddr_starts=0, ddr_samples=0;
integer accepted_at[0:@SHOTS@-1];
wire [127:0] timestamp_tag=128'(cycle);
tb_axis_buffer_ddr_sample_v3 #(.RUN_REGRESSION(0)) ddr_check();
initial begin
 force ddr_check.s_axis_aclk=clk_300000000;
 wait(resetn);
 ddr_check.reset_dut();
 ddr_check.arm_capture_delay(0, @SAMPLES@, @SHOTS@, ((@SAMPLES@+1)/2)*32, 8712);
 force ddr_check.trigger=ext_qick_vec2bit_0_dout5;
 force ddr_check.s_axis_tvalid=(cycle%300==0);
 force ddr_check.s_axis_tdata=timestamp_tag;
 ddr_file=$fopen({output_dir,"/ddr_capture.csv"},"w");
 $fwrite(ddr_file,"cycle,event,shot,sample,tag\n");
 ddr_armed=1;
end
always @(posedge clk_300000000) if(ddr_armed) begin
 if(ddr_check.dut.trigger_accept_s) begin
  if(ddr_accepts>=@SHOTS@) $fatal(1,"Too many DDR triggers");
  accepted_at[ddr_accepts]=cycle;
  $fwrite(ddr_file,"%0d,trigger,%0d,0,0\n",cycle,ddr_accepts);
  ddr_accepts=ddr_accepts+1;
 end
 if(ddr_check.dut.trigger_mature_s) begin
  if(cycle-accepted_at[ddr_matures]!=8712) $fatal(1,"DDR trigger delay mismatch");
  ddr_matures=ddr_matures+1;
 end
 if(ddr_check.dut.trigger_start_s) begin
  if(cycle-accepted_at[ddr_starts]<8712 || cycle-accepted_at[ddr_starts]>=8712+300)
   $fatal(1,"DDR first valid sample is outside delayed sample-grid boundary");
  $fwrite(ddr_file,"%0d,start,%0d,0,0\n",cycle,ddr_starts);
  ddr_starts=ddr_starts+1;
 end
 if(ddr_check.dut.output_fire_s) begin
  $fwrite(ddr_file,"%0d,sample,%0d,%0d,%0d\n",cycle,ddr_starts-1,
          ddr_check.dut.sample_count_s,ddr_check.s_axis_tdata);
  ddr_samples=ddr_samples+1;
 end
end
final begin
 $fclose(ddr_file);
 if(ddr_accepts!=@SHOTS@ || ddr_matures!=@SHOTS@ || ddr_starts!=@SHOTS@ || ddr_samples!=@SHOTS@*@SAMPLES@)
  $fatal(1,"DDR counts accepts=%0d starts=%0d samples=%0d",ddr_accepts,ddr_starts,ddr_samples);
 if(ddr_check.errors || ddr_check.dut.overflow_s)
  $fatal(1,"DDR capture error or overflow");
 if(ddr_check.completed_count != @SHOTS@*((@SAMPLES@+1)/2))
  $fatal(1,"DDR AXI writes missing: %0d",ddr_check.completed_count);
 $display("FIR_DC_CAPTURE_RESULT triggers=%0d samples=%0d AXI_writes=%0d delay_cycles=8712",
          ddr_accepts,ddr_samples,ddr_check.completed_count);
end
