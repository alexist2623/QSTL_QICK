`timescale 1ns/1ps
module tb_awg_v2;
  reg clk=0; always #1.6665 clk=~clk;
  reg rstn=0,valid=0;
  reg [159:0] command=0;
  wire [255:0] samples;
  axis_awg_tuning_v2 #(.EXTRA_Y_PIPE_STAGES(3)) dut (
    .aclk(clk),.aresetn(rstn),.s_axis_tdata(command),.s_axis_tvalid(valid),
    .s_axis_tready(),.m_axis_tdata(samples),.m_axis_tvalid(),.m_axis_tready(1'b1),
    .s_axi_aclk(clk),.s_axi_aresetn(rstn),.s_axi_awaddr(6'd0),.s_axi_awprot(3'd0),
    .s_axi_awvalid(1'b0),.s_axi_wdata(32'd0),.s_axi_wstrb(4'd0),.s_axi_wvalid(1'b0),
    .s_axi_bready(1'b1),.s_axi_araddr(6'd0),.s_axi_arprot(3'd0),.s_axi_arvalid(1'b0),.s_axi_rready(1'b1));
  integer cases=0, checked=0, fd;
  reg [255:0] delayed[0:10];
  integer warm=0;
  // Check the complete production wrapper, including equal-latency RC bypass.
  always @(posedge clk) begin
    if (!rstn) begin warm=0; for(integer i=0;i<11;i=i+1) delayed[i]=0; end
    else begin
      #0.01;
      if(warm>12 && samples !== delayed[10]) $fatal(1,"RC bypass delay mismatch");
      for(integer i=10;i>0;i=i-1) delayed[i]=delayed[i-1];
      delayed[0]=dut.core_samples; warm=warm+1;
    end
  end
  function automatic integer quantize(input longint signed fixed_value);
    longint signed value;
    begin
      value=fixed_value >>> 18;
      if(value>32764)value=32764;
      if(value< -32768)value=-32768;
      quantize=integer'(value)&(-4);
    end
  endfunction
  task automatic send(input integer target,input integer duration,input integer step,input integer opcode);
    @(negedge clk); command=0; command[31:0]=target; command[86:64]=duration;
    command[127:96]=step;command[145:144]=opcode;valid=1;
    @(posedge clk); #0.05;
    @(negedge clk);valid=0;
  endtask
  task automatic ramp_test(input integer start_value,input integer target,input integer duration,input integer step);
    integer index, expected, actual, words;
    longint signed fixed_value;
    begin
      send(start_value,0,0,1);
      repeat(15) @(negedge clk);
      send(target,duration,step,2);
      words=(duration+15)/16;
      if(words==0)words=1;
      for(integer t=1;t<=7+words+2;t=t+1) begin
        @(posedge clk); #0.05;
        for(integer lane=0;lane<16;lane=lane+1) begin
          if(t<7) expected=quantize(longint'(start_value)<<<18);
          else begin
            index=(t-7)*16+lane;
            if(index>=duration-1) expected=quantize(longint'(target)<<<18);
            else begin fixed_value=(longint'(start_value)<<<18)+longint'(step)*index;expected=quantize(fixed_value);end
          end
          actual=$signed(dut.core_samples[lane*16+:16]);
          if(actual!=expected) $fatal(1,"case=%0d cycle=%0d lane=%0d step=%0d actual=%0d expected=%0d",cases,t,lane,step,actual,expected);
          checked=checked+1;
          if(cases<4 && t>=7 && t<7+words) $fwrite(fd,"%0d,%0d,%0d,%0d\n",cases,(t-7)*16+lane,expected,actual);
        end
      end
      repeat(15) @(negedge clk);
      cases=cases+1;
    end
  endtask
  integer a,b,d,step;
  longint signed numerator;
  initial begin
    fd=$fopen("ramp_samples.csv","w");$fwrite(fd,"case,sample,expected,actual\n");
    repeat(8) @(negedge clk);rstn=1;repeat(20) @(negedge clk);
    ramp_test(-32768,32764,16,1145254707);
    ramp_test(32764,-32768,16,-1145254707);
    ramp_test(-5120,12288,16,304226850);
    ramp_test(12288,-5120,16,-304226850);
    ramp_test(0,4,32,2147483647);
    ramp_test(0,-4,32,32'sh80000000);
    ramp_test(0,4,4096,1);
    ramp_test(0,-4,4096,-1);
    ramp_test(-32768,32764,1,0);
    ramp_test(32764,-32768,0,0);
    for(integer k=0;k<160;k=k+1) begin
      a=(($urandom % 16384)-8192)*4;b=(($urandom % 16384)-8192)*4;
      d=16+($urandom%1000);
      numerator=longint'(b-a)<<<18;step=numerator/(d-1);
      ramp_test(a,b,d,step);
    end
    $fclose(fd);$display("PASS: AWG V2 cases=%0d samples=%0d full_scale_one_clock_both_directions=1 bypass_delay=11",cases,checked);$finish;
  end
endmodule
