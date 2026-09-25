`timescale 1ns/1ps
module tb_three_level;
logic clk=0, rstn=0, command_valid=0;
always #1.666666667 clk=~clk;
logic [159:0] command=0;
wire [255:0] output_word;
axis_awg_tuning_v1 #(.EXTRA_Y_PIPE_STAGES(3)) awg(
 .aclk(clk),.aresetn(rstn),.s_axis_tdata(command),.s_axis_tvalid(command_valid),
 .m_axis_tdata(output_word),.m_axis_tready(1'b1),
 .s_axi_aclk(clk),.s_axi_aresetn(rstn),.s_axi_awvalid(1'b0),.s_axi_wvalid(1'b0),
 .s_axi_arvalid(1'b0),.s_axi_bready(1'b1),.s_axi_rready(1'b1),
 .s_axi_awaddr(6'd0),.s_axi_awprot(3'd0),.s_axi_wdata(32'd0),.s_axi_wstrb(4'd0),
 .s_axi_araddr(6'd0),.s_axi_arprot(3'd0));
localparam COMMANDS=15, TOTAL_CYCLES=389996;
logic [31:0] times[0:COMMANDS-1];
logic [159:0] words[0:COMMANDS-1];
integer cycle=0, pointer=0, file, previous_dac=0, previous_target=0;
integer resets=0, zero_checks=0, check_at=-1, first_clip=-1;
longint checked_samples=0;
logic signed [71:0] q=0, value, temp, q_history[0:8];
logic signed [15:0] previous_x=0;
logic [255:0] expected[0:10], nominal[0:10];
integer raw, actual, target;
function automatic signed [15:0] quant(input logic signed [71:0] v);
 logic signed [71:0] rounded;
 begin
  rounded=(v+(72'sd1<<49)) >>> 50;
  if(rounded>8191) quant=32764;
  else if(rounded< -8192) quant=-32768;
  else quant=rounded*4;
 end
endfunction
initial begin
 $readmemh("cycles.hex",times);$readmemh("words.hex",words);
 file=$fopen("waveform_rle.csv","w");
 $fwrite(file,"sample,dac,target\n0,0,0\n");
 for(integer s=0;s<11;s=s+1)begin expected[s]=0;nominal[s]=0;end
 for(integer s=0;s<9;s=s+1)q_history[s]=0;
 repeat(40)@(negedge clk);rstn=1;
end
always @(negedge clk)if(rstn)begin
 cycle=cycle+1;command_valid=0;
 if(pointer<COMMANDS && cycle==times[pointer])begin
  command=words[pointer];command_valid=1;pointer=pointer+1;
 end
 if(cycle==TOTAL_CYCLES)begin
  if(pointer!=COMMANDS || resets!=3 || zero_checks!=3 || first_clip>=0)
   $fatal(1,"Unexpected clipping or missing command/reset checks");
  $fclose(file);
  $display("PASS samples=%0d resets=%0d zero_checks=%0d first_clip_cycle=%0d end_sample=%0d",
    checked_samples,resets,zero_checks,first_clip,TOTAL_CYCLES*16);
  $finish;
 end
end
always @(posedge clk)if(rstn)begin
 for(integer s=8;s>0;s=s-1)q_history[s]=q_history[s-1];
 for(integer s=10;s>0;s=s-1)begin expected[s]=expected[s-1];nominal[s]=nominal[s-1];end
 if(awg.rc_clear)begin
  q=0;previous_x=0;resets=resets+1;check_at=cycle+12;
 end
 for(integer lane=0;lane<16;lane=lane+1)begin
  raw=$signed(awg.core_samples[16*lane+:16]);
  nominal[0][16*lane+:16]=raw;
  if(awg.rc_enabled && awg.core_valid)begin
   temp=raw+previous_x;q=q+temp*$signed({1'b0,awg.rc_coefficient});
  end
  if(awg.core_valid)previous_x=raw;
  value=(72'(raw)<<<48)+q;
  expected[0][16*lane+:16]=awg.rc_enabled?quant(value):raw;
 end
 q_history[0]=q;
 #0.001;
 if(cycle>20)begin
  if(output_word!==expected[10] || awg.GEN_RC.rc.integral!==q_history[8])
   $fatal(1,"Exact scalar oracle mismatch at cycle=%0d",cycle);
  checked_samples=checked_samples+16;
 end
 if(awg.rc_clipped && first_clip<0)first_clip=cycle;
 if(cycle==check_at)begin
  if(output_word!==0 || awg.GEN_RC.rc.integral!==0)
   $fatal(1,"Reset did not clear DAC and IIR");
  zero_checks=zero_checks+1;
 end
 for(integer lane=0;lane<16;lane=lane+1)begin
  actual=$signed(output_word[16*lane+:16]);
  target=$signed(nominal[10][16*lane+:16]);
  if(actual!=previous_dac || target!=previous_target)begin
   $fwrite(file,"%0d,%0d,%0d\n",cycle*16+lane,actual,target);
   previous_dac=actual;previous_target=target;
  end
 end
end
endmodule
