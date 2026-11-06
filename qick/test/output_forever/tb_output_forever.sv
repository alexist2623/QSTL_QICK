`timescale 1ns/1ps
module tb_output_forever;
reg clk=0; always #1.666667 clk=~clk;
reg rstn=0,start=0;
wire [12:0] pmem_addr;
reg [63:0] pmem_do=0,pmem[0:8191];
wire dmem_we;wire [11:0] dmem_addr;wire [31:0] dmem_di;
reg [31:0] dmem_do=0,dmem[0:4095];
wire [159:0] cpu_word[0:7];wire cpu_valid[0:7],cpu_ready[0:7];
wire [159:0] acmd,rcmd,scmd;wire av,rv,sv;
wire [255:0] square_samples;
wire [255:0] ar,rr,af,rf,combined;
reg [207:0] expected[0:2047];reg [31:0] meta[0:4];reg [79:0] expected_pins[0:255];reg [31:0] pin_state=0;
integer i,c,seen,shots,cycle,done_cycle,pin_seen;
tproc64x32_x8 #(
   .N(13),
   .M(12)
) cpu (
   .clk(clk),
   .rstn(rstn),
   .start(1'b0),
   .START_SRC_REG(1'b0),
   .START_REG(start),
   .pmem_addr(pmem_addr),
   .pmem_do(pmem_do),
   .dmem_we(dmem_we),
   .dmem_addr(dmem_addr),
   .dmem_di(dmem_di),
   .dmem_do(dmem_do),
   .s0_axis_tdata(64'd0),
   .s0_axis_tvalid(1'b0),
   .s1_axis_tdata(64'd0),
   .s1_axis_tvalid(1'b0),
   .s2_axis_tdata(64'd0),
   .s2_axis_tvalid(1'b0),
   .s3_axis_tdata(64'd0),
   .s3_axis_tvalid(1'b0),
   .m0_axis_tdata(cpu_word[0]),
   .m0_axis_tvalid(cpu_valid[0]),
   .m0_axis_tready(cpu_ready[0]),
   .m1_axis_tdata(cpu_word[1]),
   .m1_axis_tvalid(cpu_valid[1]),
   .m1_axis_tready(1'b1),
   .m2_axis_tdata(cpu_word[2]),
   .m2_axis_tvalid(cpu_valid[2]),
   .m2_axis_tready(1'b1),
   .m3_axis_tdata(cpu_word[3]),
   .m3_axis_tvalid(cpu_valid[3]),
   .m3_axis_tready(1'b1),
   .m4_axis_tdata(cpu_word[4]),
   .m4_axis_tvalid(cpu_valid[4]),
   .m4_axis_tready(1'b1),
   .m5_axis_tdata(cpu_word[5]),
   .m5_axis_tvalid(cpu_valid[5]),
   .m5_axis_tready(1'b1),
   .m6_axis_tdata(cpu_word[6]),
   .m6_axis_tvalid(cpu_valid[6]),
   .m6_axis_tready(1'b1),
   .m7_axis_tdata(cpu_word[7]),
   .m7_axis_tvalid(cpu_valid[7]),
   .m7_axis_tready(1'b1)
);

axis_tmux_v1 #(.N(8),.B(160)) tmux(
 .aclk(clk),.aresetn(rstn),.s_axis_tdata(cpu_word[0]),.s_axis_tvalid(cpu_valid[0]),.s_axis_tready(cpu_ready[0]),
 .m0_axis_tdata(rcmd),.m0_axis_tvalid(rv),.m1_axis_tdata(acmd),.m1_axis_tvalid(av),.m2_axis_tdata(scmd),.m2_axis_tvalid(sv));
axis_square_pulse_v1 square_dut (
 .s_axi_aclk(clk),.s_axi_aresetn(rstn),.s_axi_awaddr(6'd0),.s_axi_awprot(3'd0),.s_axi_awvalid(1'b0),
 .s_axi_wdata(32'd0),.s_axi_wstrb(4'd0),.s_axi_wvalid(1'b0),.s_axi_bready(1'b1),
 .s_axi_araddr(6'd0),.s_axi_arprot(3'd0),.s_axi_arvalid(1'b0),.s_axi_rready(1'b1),
 .aclk(clk),.aresetn(rstn),.s_axis_tdata(scmd),.s_axis_tvalid(sv),
 .m_axis_tdata(square_samples),.m_axis_tready(1'b1));
cpu_native_pair datapath(clk,rstn,acmd,rcmd,av,rv,ar,rr,af,rf,combined);
always @(posedge clk) begin
 pmem_do <= pmem[pmem_addr];
 dmem_do <= dmem[dmem_addr];
 if(rstn) begin
  cycle=cycle+1;
  if(dmem_we) begin
   dmem[dmem_addr] <= dmem_di;
   if(dmem_addr==1) begin
    shots=shots+1;
    if(shots==meta[3]-1) dmem[2]<=1;
   end
   if(dmem_addr==3 && dmem_di==1) done_cycle=cycle;
  end
  if(cpu_valid[0] && cpu_ready[0]) begin
   if(seen>=meta[0] || cpu_word[0] !== expected[seen][159:0])
    $fatal(1,"CPU output mismatch case=%0d command=%0d actual=%040h expected=%040h",c,seen,cpu_word[0],expected[seen]);
   if(cpu.t_cnt !== expected[seen][207:160]+48'd1)
    $fatal(1,"Late command case=%0d index=%0d actual=%0d expected=%0d",c,seen,cpu.t_cnt,expected[seen][207:160]+1);
   seen=seen+1;
  end
  if(cpu_valid[7]) begin
   if(pin_seen>=meta[4] || cpu_word[7][31:0] !== expected_pins[pin_seen][31:0]) $fatal(1,"Marker mismatch");
   if(cpu.t_cnt !== expected_pins[pin_seen][79:32]+48'd1) $fatal(1,"Late marker");
   pin_seen=pin_seen+1;pin_state=cpu_word[7][31:0];
  end
  for(integer port=1;port<7;port=port+1)
   if(cpu_valid[port]) $fatal(1,"Unexpected readout/trigger command port=%0d",port);
  if(done_cycle>0 && cycle>done_cycle+4 && (ar !== 256'd0 || rr !== 256'd0 || combined !== 256'd0 || square_samples !== 256'd0 || pin_state !== 0))
   $fatal(1,"Nonzero output after stop acknowledgement case=%0d AWG=%h RF=%h SUM=%h",c,ar,rr,combined);
  if(cycle>100000) $fatal(1,"Output-only stop timed out");
 end
end
initial begin
 for(c=0;c<10;c=c+1) begin
  rstn=0;start=0;seen=0;shots=0;cycle=0;done_cycle=0;pin_seen=0;pin_state=0;
  for(i=0;i<8192;i=i+1)pmem[i]=0;
  for(i=0;i<4096;i=i+1)dmem[i]=0;
  // Literal names avoid an XSIM 2023.1 dynamic-string readmemh defect.
  case(c)
   0: begin
    $readmemh("case0_meta.hex",meta);
    $readmemh("case0_pmem.hex",pmem,0,meta[1]-1);
    $readmemh("case0_dmem.hex",dmem);
    $readmemh("case0_expected.hex",expected,0,meta[0]-1);
   end
   1: begin
    $readmemh("case1_meta.hex",meta);
    $readmemh("case1_pmem.hex",pmem,0,meta[1]-1);
    $readmemh("case1_dmem.hex",dmem);
    $readmemh("case1_expected.hex",expected,0,meta[0]-1);
   end
   2: begin
    $readmemh("case2_meta.hex",meta);
    $readmemh("case2_pmem.hex",pmem,0,meta[1]-1);
    $readmemh("case2_dmem.hex",dmem);
    $readmemh("case2_expected.hex",expected,0,meta[0]-1);
   end
   3: begin
    $readmemh("case3_meta.hex",meta);
    $readmemh("case3_pmem.hex",pmem,0,meta[1]-1);
    $readmemh("case3_dmem.hex",dmem);
    $readmemh("case3_expected.hex",expected,0,meta[0]-1);
   end
   4: begin
    $readmemh("case4_meta.hex",meta);
    $readmemh("case4_pmem.hex",pmem,0,meta[1]-1);
    $readmemh("case4_dmem.hex",dmem);
    $readmemh("case4_expected.hex",expected,0,meta[0]-1);
   end
   5: begin
    $readmemh("case5_meta.hex",meta);
    $readmemh("case5_pmem.hex",pmem,0,meta[1]-1);
    $readmemh("case5_dmem.hex",dmem);
    $readmemh("case5_expected.hex",expected,0,meta[0]-1);
   end
   6: begin
    $readmemh("case6_meta.hex",meta);
    $readmemh("case6_pmem.hex",pmem,0,meta[1]-1);
    $readmemh("case6_dmem.hex",dmem);
    $readmemh("case6_expected.hex",expected,0,meta[0]-1);
   end
   7: begin
    $readmemh("case7_meta.hex",meta);
    $readmemh("case7_pmem.hex",pmem,0,meta[1]-1);
    $readmemh("case7_dmem.hex",dmem);
    $readmemh("case7_expected.hex",expected,0,meta[0]-1);
   end
   8: begin
    $readmemh("case8_meta.hex",meta);
    $readmemh("case8_pmem.hex",pmem,0,meta[1]-1);
    $readmemh("case8_dmem.hex",dmem);
    $readmemh("case8_expected.hex",expected,0,meta[0]-1);
    $readmemh("case8_pins.hex",expected_pins,0,meta[4]-1);
   end
   9: begin
    $readmemh("case9_meta.hex",meta);
    $readmemh("case9_pmem.hex",pmem,0,meta[1]-1);
    $readmemh("case9_dmem.hex",dmem);
    $readmemh("case9_expected.hex",expected,0,meta[0]-1);
    $readmemh("case9_pins.hex",expected_pins,0,meta[4]-1);
   end
  endcase
  if(meta[0]===32'bx || meta[0]==0 || meta[1]==0) $fatal(1,"Missing fixture data");
  repeat(20)@(negedge clk);rstn=1;
  repeat(20)@(negedge clk);start=1;
  wait(done_cycle>0);repeat(500)@(negedge clk);
  if(seen!=meta[0] || pin_seen!=meta[4] || shots!=meta[3]-1) $fatal(1,"Output count/shot mismatch");
  $display("OUTPUT_FOREVER_CASE_PASS case=%0d commands=%0d completed_shots=%0d digital_zero=1",c,seen,shots+1);
 end
 $display("OUTPUT_FOREVER_RTL_PASS cases=10");$finish;
end
endmodule
