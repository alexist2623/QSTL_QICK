`timescale 1ns/1ps

module axis_signal_gen_v6_tb;

localparam int N_DDS = 16;
real          F_ACLK = 100.0e6;      // aclk = 100 MHz

// ---------------------------------------------------------------------------
// Clocks & resets
// ---------------------------------------------------------------------------
reg s_axi_aclk    = 1'b0;
reg s0_axis_aclk  = 1'b0;
reg aclk          = 1'b0;

// 50 MHz, 50 MHz, 100 MHz
always #10.0 s_axi_aclk   = ~s_axi_aclk;   // 20 ns period
always #10.0 s0_axis_aclk = ~s0_axis_aclk; // 20 ns period
always #5.0  aclk         = ~aclk;         // 10 ns period

reg s_axi_aresetn   = 1'b0;
reg s0_axis_aresetn = 1'b0;
reg aresetn         = 1'b0;

reg  [5:0]  s_axi_awaddr  = '0;
reg  [2:0]  s_axi_awprot  = '0;
reg         s_axi_awvalid = 1'b0;
wire        s_axi_awready;

reg  [31:0] s_axi_wdata   = '0;
reg  [3:0]  s_axi_wstrb   = '0;
reg         s_axi_wvalid  = 1'b0;
wire        s_axi_wready;

wire [1:0]  s_axi_bresp;
wire        s_axi_bvalid;
reg         s_axi_bready  = 1'b0;

reg  [5:0]  s_axi_araddr  = '0;
reg  [2:0]  s_axi_arprot  = '0;
reg         s_axi_arvalid = 1'b0;
wire        s_axi_arready;

wire [31:0] s_axi_rdata;
wire [1:0]  s_axi_rresp;
wire        s_axi_rvalid;
reg         s_axi_rready  = 1'b0;

reg  [31:0] s0_axis_tdata  = '0;
reg         s0_axis_tvalid = 1'b0;
wire        s0_axis_tready;

reg  [159:0] s1_axis_tdata  = '0;
reg          s1_axis_tvalid = 1'b0;
wire         s1_axis_tready;

reg                       m_axis_tready = 1'b1;
wire                      m_axis_tvalid;
wire [N_DDS*16-1:0]       m_axis_tdata;

// ---------------------------------------------------------------------------
// DUT instance
// ---------------------------------------------------------------------------
axis_signal_gen_v6 dut (
    // AXI-Lite
    .s_axi_aclk    (s_axi_aclk),
    .s_axi_aresetn (s_axi_aresetn),

    .s_axi_awaddr  (s_axi_awaddr),
    .s_axi_awprot  (s_axi_awprot),
    .s_axi_awvalid (s_axi_awvalid),
    .s_axi_awready (s_axi_awready),

    .s_axi_wdata   (s_axi_wdata),
    .s_axi_wstrb   (s_axi_wstrb),
    .s_axi_wvalid  (s_axi_wvalid),
    .s_axi_wready  (s_axi_wready),

    .s_axi_bresp   (s_axi_bresp),
    .s_axi_bvalid  (s_axi_bvalid),
    .s_axi_bready  (s_axi_bready),

    .s_axi_araddr  (s_axi_araddr),
    .s_axi_arprot  (s_axi_arprot),
    .s_axi_arvalid (s_axi_arvalid),
    .s_axi_arready (s_axi_arready),

    .s_axi_rdata   (s_axi_rdata),
    .s_axi_rresp   (s_axi_rresp),
    .s_axi_rvalid  (s_axi_rvalid),
    .s_axi_rready  (s_axi_rready),

    // s0_axis (unused)
    .s0_axis_aclk   (s0_axis_aclk),
    .s0_axis_aresetn(s0_axis_aresetn),
    .s0_axis_tdata  (s0_axis_tdata),
    .s0_axis_tvalid (s0_axis_tvalid),
    .s0_axis_tready (s0_axis_tready),

    // s1/m axis clock/reset
    .aresetn        (aresetn),
    .aclk           (aclk),

    // s1_axis (control words)
    .s1_axis_tdata  (s1_axis_tdata),
    .s1_axis_tvalid (s1_axis_tvalid),
    .s1_axis_tready (s1_axis_tready),

    // m_axis (outputs)
    .m_axis_tready  (m_axis_tready),
    .m_axis_tvalid  (m_axis_tvalid),
    .m_axis_tdata   (m_axis_tdata)
);

function automatic [159:0] pack_ctrl (
    input logic [31:0] pinc,     // freq
    input logic [31:0] phase,    // phase
    input logic [15:0] addr,     // addr
    input logic [15:0] gain,     // gain
    input logic [15:0] nsamp,    // nsamp
    input logic [1:0]  outsel,   // 1: DDS only
    input logic        mode,     // 0: burst
    input logic        stdysel,
    input logic        phrst
);
    logic [159:0] w;
    w               = '0;
    w[31:0]         = pinc;      // freq
    w[63:32]        = phase;     // phase
    w[79:64]        = addr;      // addr
    w[111:96]       = gain;      // gain
    w[143:128]      = nsamp;     // nsamp
    w[145:144]      = outsel;    // outsel
    w[146]          = mode;      // mode
    w[147]          = stdysel;   // stdysel
    w[148]          = phrst;     // phrst
    return w;
endfunction

function automatic [31:0] calc_pinc (input real f_out_hz);
    real val = (f_out_hz * 4294967296.0) / (F_ACLK * N_DDS); // 2^32
    if (val < 0.0)           val = 0.0;
    if (val > 4294967295.0)  val = 4294967295.0;
    return $rtoi(val + 0.5); // round
endfunction

task automatic push_ctrl (input [159:0] word);
    @(posedge aclk);
    while (!s1_axis_tready) @(posedge aclk);
    s1_axis_tdata  <= word;
    s1_axis_tvalid <= 1'b1;
    @(posedge aclk);
    s1_axis_tvalid <= 1'b0;
endtask

int samp_cnt = 0;
always @(posedge aclk) begin
    if (m_axis_tvalid && m_axis_tready) begin
        samp_cnt++;
        if ((samp_cnt % 64) == 0) begin
            $display(
                "%0t : sample[%0d] lane0 = %0d",
                $time, samp_cnt, $signed(m_axis_tdata[15:0])
            );
        end
    end
end

// ---------------------------------------------------------------------------
// Stimulus
// ---------------------------------------------------------------------------

real f1 = 1.0e6;    // 1 MHz
real f2 = 2.0e6;    // 5 MHz
real f3 = 3.0e6;   // 10 MHz
logic [31:0] pinc1;
logic [31:0] pinc2;
logic [31:0] pinc3;


initial begin
    // Reset
    s_axi_aresetn   = 1'b0;
    s0_axis_aresetn = 1'b0;
    aresetn         = 1'b0;

    repeat (10) @(posedge aclk);
    s_axi_aresetn   = 1'b1;
    s0_axis_aresetn = 1'b1;
    aresetn         = 1'b1;

    repeat (10) @(posedge aclk);


    pinc1 = calc_pinc(f1);
    pinc2 = calc_pinc(f2);
    pinc3 = calc_pinc(f3);

    $display("N_DDS=%0d, aclk=%.3f MHz => Fs=%.3f Msps ",
             N_DDS, F_ACLK/1e6, (F_ACLK*N_DDS)/1e6);
    $display("pinc1(%.3f MHz)=0x%08h, pinc2(%.3f MHz)=0x%08h, pinc3(%.3f MHz)=0x%08h",
             f1/1e6, pinc1, f2/1e6, pinc2, f3/1e6, pinc3);

    push_ctrl( pack_ctrl(pinc1, 32'd0, 16'd0, 16'h4000, 16'd2048, 2'd1, 1'b0, 1'b0, 1'b1) );
    push_ctrl( pack_ctrl(pinc2, 32'd0, 16'd0, 16'h4000, 16'd2048, 2'd1, 1'b0, 1'b0, 1'b1) );
    push_ctrl( pack_ctrl(pinc3, 32'd0, 16'd0, 16'h4000, 16'd2048, 2'd1, 1'b0, 1'b0, 1'b1) );

    repeat (20000) @(posedge aclk);
    $finish;
end

endmodule
