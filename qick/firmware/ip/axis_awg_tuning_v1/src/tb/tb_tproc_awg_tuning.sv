`timescale 1ns/1ps
`default_nettype none

module tb_tproc_awg_tuning();

localparam int PMEM_N = 16;
localparam int DMEM_N = 10;
localparam int N_DDS = 4;
localparam int B = 16;
localparam int FRAC = 16;
localparam int OUT_WIDTH = N_DDS*B;

// Exactly one mode should be enabled.
// USE_TPROC_PROGRAM expects a valid tProcessor v1 program image in prog.bin.
// USE_DIRECT_COMMAND_DRIVER bypasses the tProcessor output and drives the same
// 160-bit command stream directly into axis_awg_tuning_v1.
localparam bit USE_TPROC_PROGRAM = 1'b0;
localparam bit USE_DIRECT_COMMAND_DRIVER = 1'b1;

localparam logic [1:0] OP_SET  = 2'b01;
localparam logic [1:0] OP_RAMP = 2'b10;
localparam logic [1:0] OP_IDLE = 2'b11;

logic                   s_axi_aclk;
logic                   s_axi_aresetn;
logic                   aclk;
logic                   aresetn;
logic                   start;

logic [31:0]            s_axi_awaddr;
logic [2:0]             s_axi_awprot;
logic                   s_axi_awvalid;
wire                    s_axi_awready;
logic [31:0]            s_axi_wdata;
logic [3:0]             s_axi_wstrb;
logic                   s_axi_wvalid;
wire                    s_axi_wready;
wire [1:0]              s_axi_bresp;
wire                    s_axi_bvalid;
logic                   s_axi_bready;
logic [31:0]            s_axi_araddr;
logic [2:0]             s_axi_arprot;
logic                   s_axi_arvalid;
wire                    s_axi_arready;
wire [31:0]             s_axi_rdata;
wire [1:0]              s_axi_rresp;
wire                    s_axi_rvalid;
logic                   s_axi_rready;

logic [31:0]            s0_axis_tdata;
logic                   s0_axis_tlast;
logic                   s0_axis_tvalid;
wire                    s0_axis_tready;
wire [31:0]             m0_axis_tdata;
wire                    m0_axis_tlast;
wire                    m0_axis_tvalid;
logic                   m0_axis_tready;

wire [PMEM_N-1:0]       pmem_addr;
wire [63:0]             pmem_do;

logic [63:0]            s1_axis_tdata;
logic                   s1_axis_tvalid;
wire                    s1_axis_tready;
logic [63:0]            s2_axis_tdata;
logic                   s2_axis_tvalid;
wire                    s2_axis_tready;
logic [63:0]            s3_axis_tdata;
logic                   s3_axis_tvalid;
wire                    s3_axis_tready;
logic [63:0]            s4_axis_tdata;
logic                   s4_axis_tvalid;
wire                    s4_axis_tready;

wire [159:0]            m1_axis_tdata;
wire                    m1_axis_tvalid;
wire                    m1_axis_tready;
wire [159:0]            m2_axis_tdata;
wire                    m2_axis_tvalid;
logic                   m2_axis_tready;
wire [159:0]            m3_axis_tdata;
wire                    m3_axis_tvalid;
logic                   m3_axis_tready;
wire [159:0]            m4_axis_tdata;
wire                    m4_axis_tvalid;
logic                   m4_axis_tready;
wire [159:0]            m5_axis_tdata;
wire                    m5_axis_tvalid;
logic                   m5_axis_tready;
wire [159:0]            m6_axis_tdata;
wire                    m6_axis_tvalid;
logic                   m6_axis_tready;
wire [159:0]            m7_axis_tdata;
wire                    m7_axis_tvalid;
logic                   m7_axis_tready;
wire [159:0]            m8_axis_tdata;
wire                    m8_axis_tvalid;
logic                   m8_axis_tready;

logic [159:0]           direct_tdata;
logic                   direct_tvalid;
wire                    direct_tready;

wire [159:0]            awg_s_axis_tdata;
wire                    awg_s_axis_tvalid;
wire                    awg_s_axis_tready;
wire [OUT_WIDTH-1:0]    awg_m_axis_tdata;
wire                    awg_m_axis_tvalid;
logic                   awg_m_axis_tready;

int                     fd;
logic signed [B-1:0]    lane_value;

always begin
   s_axi_aclk = 1'b0;
   #5;
   s_axi_aclk = 1'b1;
   #5;
end

always begin
   aclk = 1'b0;
   #2;
   aclk = 1'b1;
   #2;
end

assign awg_s_axis_tdata  = USE_DIRECT_COMMAND_DRIVER ? direct_tdata  : m1_axis_tdata;
assign awg_s_axis_tvalid = USE_DIRECT_COMMAND_DRIVER ? direct_tvalid : m1_axis_tvalid;
assign direct_tready     = USE_DIRECT_COMMAND_DRIVER ? awg_s_axis_tready : 1'b0;
assign m1_axis_tready    = USE_DIRECT_COMMAND_DRIVER ? 1'b1 : awg_s_axis_tready;

bram
   #(
      .N (PMEM_N),
      .B (64    )
   )
   pmem_i
   (
      .clk    (aclk                         ),
      .ena    (1'b1                         ),
      .wea    (1'b0                         ),
      .addra  ({3'b000, pmem_addr[PMEM_N-1:3]}),
      .dia    ({64{1'b0}}                   ),
      .doa    (pmem_do                      )
   );

axis_tproc64x32_x8
   #(
      .PMEM_N (PMEM_N),
      .DMEM_N (DMEM_N)
   )
   tproc_i
   (
      .s_axi_aclk       (s_axi_aclk    ),
      .s_axi_aresetn    (s_axi_aresetn ),
      .s_axi_awaddr     (s_axi_awaddr  ),
      .s_axi_awprot     (s_axi_awprot  ),
      .s_axi_awvalid    (s_axi_awvalid ),
      .s_axi_awready    (s_axi_awready ),
      .s_axi_wdata      (s_axi_wdata   ),
      .s_axi_wstrb      (s_axi_wstrb   ),
      .s_axi_wvalid     (s_axi_wvalid  ),
      .s_axi_wready     (s_axi_wready  ),
      .s_axi_bresp      (s_axi_bresp   ),
      .s_axi_bvalid     (s_axi_bvalid  ),
      .s_axi_bready     (s_axi_bready  ),
      .s_axi_araddr     (s_axi_araddr  ),
      .s_axi_arprot     (s_axi_arprot  ),
      .s_axi_arvalid    (s_axi_arvalid ),
      .s_axi_arready    (s_axi_arready ),
      .s_axi_rdata      (s_axi_rdata   ),
      .s_axi_rresp      (s_axi_rresp   ),
      .s_axi_rvalid     (s_axi_rvalid  ),
      .s_axi_rready     (s_axi_rready  ),
      .s0_axis_aclk     (s_axi_aclk    ),
      .s0_axis_aresetn  (s_axi_aresetn ),
      .s0_axis_tdata    (s0_axis_tdata ),
      .s0_axis_tlast    (s0_axis_tlast ),
      .s0_axis_tvalid   (s0_axis_tvalid),
      .s0_axis_tready   (s0_axis_tready),
      .m0_axis_aclk     (s_axi_aclk    ),
      .m0_axis_aresetn  (s_axi_aresetn ),
      .m0_axis_tdata    (m0_axis_tdata ),
      .m0_axis_tlast    (m0_axis_tlast ),
      .m0_axis_tvalid   (m0_axis_tvalid),
      .m0_axis_tready   (m0_axis_tready),
      .aclk             (aclk          ),
      .aresetn          (aresetn       ),
      .start            (start         ),
      .pmem_addr        (pmem_addr     ),
      .pmem_do          (pmem_do       ),
      .s1_axis_tdata    (s1_axis_tdata ),
      .s1_axis_tvalid   (s1_axis_tvalid),
      .s1_axis_tready   (s1_axis_tready),
      .s2_axis_tdata    (s2_axis_tdata ),
      .s2_axis_tvalid   (s2_axis_tvalid),
      .s2_axis_tready   (s2_axis_tready),
      .s3_axis_tdata    (s3_axis_tdata ),
      .s3_axis_tvalid   (s3_axis_tvalid),
      .s3_axis_tready   (s3_axis_tready),
      .s4_axis_tdata    (s4_axis_tdata ),
      .s4_axis_tvalid   (s4_axis_tvalid),
      .s4_axis_tready   (s4_axis_tready),
      .m1_axis_tdata    (m1_axis_tdata ),
      .m1_axis_tvalid   (m1_axis_tvalid),
      .m1_axis_tready   (m1_axis_tready),
      .m2_axis_tdata    (m2_axis_tdata ),
      .m2_axis_tvalid   (m2_axis_tvalid),
      .m2_axis_tready   (m2_axis_tready),
      .m3_axis_tdata    (m3_axis_tdata ),
      .m3_axis_tvalid   (m3_axis_tvalid),
      .m3_axis_tready   (m3_axis_tready),
      .m4_axis_tdata    (m4_axis_tdata ),
      .m4_axis_tvalid   (m4_axis_tvalid),
      .m4_axis_tready   (m4_axis_tready),
      .m5_axis_tdata    (m5_axis_tdata ),
      .m5_axis_tvalid   (m5_axis_tvalid),
      .m5_axis_tready   (m5_axis_tready),
      .m6_axis_tdata    (m6_axis_tdata ),
      .m6_axis_tvalid   (m6_axis_tvalid),
      .m6_axis_tready   (m6_axis_tready),
      .m7_axis_tdata    (m7_axis_tdata ),
      .m7_axis_tvalid   (m7_axis_tvalid),
      .m7_axis_tready   (m7_axis_tready),
      .m8_axis_tdata    (m8_axis_tdata ),
      .m8_axis_tvalid   (m8_axis_tvalid),
      .m8_axis_tready   (m8_axis_tready)
   );

axis_awg_tuning_v1
   #(
      .N_DDS     (N_DDS),
      .B         (B    ),
      .FRAC      (FRAC ),
      .CMD_WIDTH (160  )
   )
   awg_tuning_i
   (
      .aresetn          (aresetn            ),
      .aclk             (aclk               ),
      .s_axis_tdata     (awg_s_axis_tdata   ),
      .s_axis_tvalid    (awg_s_axis_tvalid  ),
      .s_axis_tready    (awg_s_axis_tready  ),
      .m_axis_tdata     (awg_m_axis_tdata   ),
      .m_axis_tvalid    (awg_m_axis_tvalid  ),
      .m_axis_tready    (awg_m_axis_tready  )
   );

function automatic logic signed [31:0] calc_step;
   input logic signed [31:0] y_start;
   input logic signed [31:0] y_target;
   input logic [31:0] duration;
   longint signed delta;
   longint signed numerator;
   longint signed denominator;
   longint signed quotient;
   begin
      if (duration <= 1) begin
         calc_step = 32'sd0;
      end
      else begin
         delta = y_target - y_start;
         numerator = delta <<< FRAC;
         denominator = duration - 1;
         quotient = numerator / denominator;
         calc_step = quotient[31:0];
      end
   end
endfunction

function automatic logic [159:0] make_cmd;
   input logic signed [31:0] y_target;
   input logic signed [31:0] y_start;
   input logic [31:0] duration;
   input logic signed [31:0] step;
   input logic [1:0] opcode;
   logic [159:0] cmd;
   begin
      cmd = 160'd0;
      cmd[31:0]    = y_target;
      cmd[63:32]   = y_start;
      cmd[95:64]   = duration;
      cmd[127:96]  = step;
      cmd[145:144] = opcode;
      make_cmd = cmd;
   end
endfunction

task automatic drive_direct_cmd;
   input logic [159:0] cmd;
   begin
      @(posedge aclk);
      direct_tdata  <= cmd;
      direct_tvalid <= 1'b1;

      do begin
         @(posedge aclk);
      end while (!direct_tready);

      direct_tvalid <= 1'b0;
   end
endtask

initial begin
   if (USE_TPROC_PROGRAM == USE_DIRECT_COMMAND_DRIVER) begin
      $fatal(1, "Select exactly one tb_tproc_awg_tuning mode");
   end

   fd = $fopen("dout_tproc_awg_tuning.csv", "w");
   if (fd == 0)
      $fatal(1, "could not open dout_tproc_awg_tuning.csv");
   $fwrite(fd, "time,lane,value\n");

   s_axi_aresetn <= 1'b0;
   aresetn <= 1'b0;
   start <= 1'b0;
   s_axi_awaddr <= 32'd0;
   s_axi_awprot <= 3'd0;
   s_axi_awvalid <= 1'b0;
   s_axi_wdata <= 32'd0;
   s_axi_wstrb <= 4'd0;
   s_axi_wvalid <= 1'b0;
   s_axi_bready <= 1'b1;
   s_axi_araddr <= 32'd0;
   s_axi_arprot <= 3'd0;
   s_axi_arvalid <= 1'b0;
   s_axi_rready <= 1'b1;
   s0_axis_tdata <= 32'd0;
   s0_axis_tlast <= 1'b0;
   s0_axis_tvalid <= 1'b0;
   m0_axis_tready <= 1'b1;
   s1_axis_tdata <= 64'd0;
   s1_axis_tvalid <= 1'b0;
   s2_axis_tdata <= 64'd0;
   s2_axis_tvalid <= 1'b0;
   s3_axis_tdata <= 64'd0;
   s3_axis_tvalid <= 1'b0;
   s4_axis_tdata <= 64'd0;
   s4_axis_tvalid <= 1'b0;
   m2_axis_tready <= 1'b1;
   m3_axis_tready <= 1'b1;
   m4_axis_tready <= 1'b1;
   m5_axis_tready <= 1'b1;
   m6_axis_tready <= 1'b1;
   m7_axis_tready <= 1'b1;
   m8_axis_tready <= 1'b1;
   direct_tdata <= 160'd0;
   direct_tvalid <= 1'b0;
   awg_m_axis_tready <= 1'b1;

   repeat (20) @(posedge aclk);
   s_axi_aresetn <= 1'b1;
   aresetn <= 1'b1;
   repeat (10) @(posedge aclk);

   if (USE_TPROC_PROGRAM) begin
      // TODO: provide a prog.bin assembled for tProcessor v1 that writes the
      // axis_awg_tuning_v1 command map on m1_axis. The legacy tProcessor v1
      // assembler format is not inferred here to avoid faking a valid program.
      $readmemb("prog.bin", pmem_i.RAM);
      start <= 1'b1;
      @(posedge aclk);
      start <= 1'b0;
      repeat (2000) @(posedge aclk);
   end

   if (USE_DIRECT_COMMAND_DRIVER) begin
      drive_direct_cmd(make_cmd(32'sd512, 32'sd0, 32'd0, 32'sd0, OP_SET));
      repeat (8) @(posedge aclk);
      drive_direct_cmd(make_cmd(32'sd0, 32'sd0, 32'd5, 32'sd0, OP_IDLE));
      repeat (8) @(posedge aclk);
      drive_direct_cmd(make_cmd(32'sd2048, -32'sd2048, 32'd16, calc_step(-32'sd2048, 32'sd2048, 32'd16), OP_RAMP));
      repeat (80) @(posedge aclk);
   end

   $display("PASS: tb_tproc_awg_tuning completed in selected mode");
   $fclose(fd);
   $finish;
end

always_ff @(posedge aclk) begin
   if (aresetn && awg_m_axis_tvalid && awg_m_axis_tready) begin
      for (int i = 0; i < N_DDS; i = i + 1) begin
         lane_value = awg_m_axis_tdata[i*B +: B];
         $fwrite(fd, "%0t,%0d,%0d\n", $time, i, lane_value);
      end
   end
end

endmodule

`default_nettype wire
