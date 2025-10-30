`timescale 1ns/1ps

// -----------------------------------------------------------------------------
// Top-level TB: Connect axis_signal_gen_v6 (generator) -> axis_dyn_readout_v1 (demod)
// -----------------------------------------------------------------------------
module tb_full_signal;

    // ----------------------------
    // Configuration
    // ----------------------------
    localparam int SAMPLE_W = 16;

    // Lanes on each side (edit to match your RTL if parameterizable)
    // If you know both modules are N=8, set both to 8 and the adapter is not used.
    localparam int N_GEN   = 16; // lanes from axis_signal_gen_v6 (per-cycle samples)
    localparam int N_DEMOD = 8;  // lanes into axis_dyn_readout_v1 (per-cycle samples)

    // Clock frequencies
    real          F_ACLK_HZ   = 100.0e6; // 100 MHz stream clock (shared)
    real          F_AXI_HZ    = 50.0e6;  // 50 MHz (AXI-Lite / optional)
    localparam    real T_ACLK = 1e9/100.0e6; // 10 ns
    localparam    real T_AXI  = 1e9/50.0e6;  // 20 ns

    // ----------------------------
    // Clocks and resets
    // ----------------------------
    reg aclk = 1'b0;
    always #(T_ACLK/2.0) aclk = ~aclk; // 100 MHz

    reg s_axi_aclk = 1'b0;
    always #(T_AXI/2.0) s_axi_aclk = ~s_axi_aclk; // 50 MHz

    // Some designs separate s0_axis_aclk; tie to AXI or to aclk as needed.
    reg s0_axis_aclk = 1'b0;
    always #(T_AXI/2.0) s0_axis_aclk = ~s0_axis_aclk; // 50 MHz (unused by demod)

    reg aresetn         = 1'b0;
    reg s_axi_aresetn   = 1'b0;
    reg s0_axis_aresetn = 1'b0;

    // ----------------------------
    // AXI-Lite signals (kept idle; not used by this TB)
    // ----------------------------
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

    // ----------------------------
    // Generator control (s1_axis) and output (m_axis)
    // ----------------------------
    reg  [159:0] gen_s1_axis_tdata  = '0;  // 160-bit control word
    reg          gen_s1_axis_tvalid = 1'b0;
    wire         gen_s1_axis_tready;

    wire                      gen_m_axis_tvalid;
    wire [N_GEN*SAMPLE_W-1:0] gen_m_axis_tdata;
    wire                      gen_m_axis_tready; // will be driven by demod side

    // Unused generator s0_axis data-path (kept idle)
    reg  [31:0] gen_s0_axis_tdata  = '0;
    reg         gen_s0_axis_tvalid = 1'b0;
    wire        gen_s0_axis_tready;

    // ----------------------------
    // Demod control (s0_axis), input (s1_axis), and outputs (m0/m1)
    // ----------------------------
    wire         demod_s0_axis_tready;
    reg          demod_s0_axis_tvalid = 1'b0;
    reg  [87:0]  demod_s0_axis_tdata;

    wire                      demod_s1_axis_tready;
    wire                      demod_s1_axis_tvalid;
    wire [N_DEMOD*SAMPLE_W-1:0] demod_s1_axis_tdata;

    reg   demod_m0_axis_tready = 1'b1;
    wire  demod_m0_axis_tvalid;
    wire [N_DEMOD*32-1:0] demod_m0_axis_tdata; // 32b per complex sample (I[15:0],Q[31:16])

    reg   demod_m1_axis_tready = 1'b1;
    wire  demod_m1_axis_tvalid;
    wire [31:0] demod_m1_axis_tdata;          // 1 complex sample per cycle

    // -----------------------------------------------------------------------------
    // Device Under Test: Signal generator
    // NOTE: If your RTL exposes parameters for lane count, set them here if needed.
    // -----------------------------------------------------------------------------
    axis_signal_gen_v6 u_gen (
        // AXI-Lite (unused)
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

        // s0_axis (unused in this TB)
        .s0_axis_aclk    (s0_axis_aclk),
        .s0_axis_aresetn (s0_axis_aresetn),
        .s0_axis_tdata   (gen_s0_axis_tdata),
        .s0_axis_tvalid  (gen_s0_axis_tvalid),
        .s0_axis_tready  (gen_s0_axis_tready),

        // s1/m axis clock/reset
        .aresetn         (aresetn),
        .aclk            (aclk),

        // s1_axis (control words)
        .s1_axis_tdata   (gen_s1_axis_tdata),
        .s1_axis_tvalid  (gen_s1_axis_tvalid),
        .s1_axis_tready  (gen_s1_axis_tready),

        // m_axis (generated outputs)
        .m_axis_tready   (gen_m_axis_tready),
        .m_axis_tvalid   (gen_m_axis_tvalid),
        .m_axis_tdata    (gen_m_axis_tdata)
    );

    // -----------------------------------------------------------------------------
    // Optional lane shrink adapter (e.g., 16 lanes -> 8 lanes)
    // If N_GEN == N_DEMOD, this block is bypassed and direct wiring is used.
    // -----------------------------------------------------------------------------
    generate
        if (N_GEN == N_DEMOD) begin : GEN_DIRECT_WIRE
            assign demod_s1_axis_tdata  = gen_m_axis_tdata;
            assign demod_s1_axis_tvalid = gen_m_axis_tvalid;
            assign gen_m_axis_tready     = demod_s1_axis_tready;
        end else begin : GEN_LANE_ADAPTER
            // Compile-time check: IN must be an integer multiple of OUT.
            initial begin
                if (N_GEN % N_DEMOD != 0) begin
                    $error("Lane adapter requires N_GEN %% N_DEMOD == 0. Given N_GEN=%0d, N_DEMOD=%0d", N_GEN, N_DEMOD);
                end
            end

            axis_lane_shrink #(
                .IN_LANES  (N_GEN),
                .OUT_LANES (N_DEMOD),
                .SAMPLE_W  (SAMPLE_W)
            ) u_shrink (
                .aclk            (aclk),
                .aresetn         (aresetn),

                .s_axis_tvalid   (gen_m_axis_tvalid),
                .s_axis_tready   (gen_m_axis_tready),
                .s_axis_tdata    (gen_m_axis_tdata),

                .m_axis_tvalid   (demod_s1_axis_tvalid),
                .m_axis_tready   (demod_s1_axis_tready),
                .m_axis_tdata    (demod_s1_axis_tdata)
            );
        end
    endgenerate

    // -----------------------------------------------------------------------------
    // Device Under Test: Demodulator
    // -----------------------------------------------------------------------------
    axis_dyn_readout_v1 u_demod (
        // Reset and clock
        .aresetn         (aresetn),
        .aclk            (aclk),

        // s0_axis: control/programming (push LO/waveform params)
        .s0_axis_tready  (demod_s0_axis_tready),
        .s0_axis_tvalid  (demod_s0_axis_tvalid),
        .s0_axis_tdata   (demod_s0_axis_tdata),

        // s1_axis: input data from generator
        .s1_axis_tready  (demod_s1_axis_tready),
        .s1_axis_tvalid  (demod_s1_axis_tvalid),
        .s1_axis_tdata   (demod_s1_axis_tdata),

        // m0_axis: N complex samples per cycle
        .m0_axis_tready  (demod_m0_axis_tready),
        .m0_axis_tvalid  (demod_m0_axis_tvalid),
        .m0_axis_tdata   (demod_m0_axis_tdata),

        // m1_axis: 1 complex sample per cycle
        .m1_axis_tready  (demod_m1_axis_tready),
        .m1_axis_tvalid  (demod_m1_axis_tvalid),
        .m1_axis_tdata   (demod_m1_axis_tdata)
    );

    // -----------------------------------------------------------------------------
    // Helper: control word packers and frequency step calculators
    // -----------------------------------------------------------------------------
    // Generator: 160-bit control word packer (mirrors your original TB)
    function automatic [159:0] pack_ctrl_gen (
        input logic [31:0] pinc,     // freq step
        input logic [31:0] phase,    // phase
        input logic [15:0] addr,     // address
        input logic [15:0] gain,     // linear gain
        input logic [15:0] nsamp,    // samples to generate
        input logic [1:0]  outsel,   // 1: DDS only
        input logic        mode,     // 0: burst
        input logic        stdysel,  // 
        input logic        phrst     // phase reset
    );
        logic [159:0] w;
        w               = '0;
        w[31:0]         = pinc;
        w[63:32]        = phase;
        w[79:64]        = addr;
        w[111:96]       = gain;
        w[143:128]      = nsamp;
        w[145:144]      = outsel;
        w[146]          = mode;
        w[147]          = stdysel;
        w[148]          = phrst;
        return w;
    endfunction

    // Generator: PINC from target output frequency
    function automatic [31:0] calc_pinc_gen (input real f_out_hz);
        real val = (f_out_hz * 4294967296.0) / (F_ACLK_HZ * N_GEN); // 2^32
        if (val < 0.0)          val = 0.0;
        if (val > 4294967295.0) val = 4294967295.0;
        return $rtoi(val + 0.5); // round to nearest
    endfunction

    // Demod: frequency register calculator
    function automatic [31:0] freq_calc_demod (
        input real f
    );
        real val = (f  * (2.0**32)) / (F_ACLK_HZ * N_DEMOD);
        return $rtoi(val + 0.5);
    endfunction

    // AXIS push (1 beat) helpers
    task automatic push_ctrl_gen (input [159:0] word);
        @(posedge aclk);
        while (!gen_s1_axis_tready) @(posedge aclk);
        gen_s1_axis_tdata  <= word;
        gen_s1_axis_tvalid <= 1'b1;
        @(posedge aclk);
        gen_s1_axis_tvalid <= 1'b0;
    endtask

    task automatic push_ctrl_demod (input [87:0] word);
        @(posedge aclk);
        while (!demod_s0_axis_tready) @(posedge aclk);
        demod_s0_axis_tdata  <= word;
        demod_s0_axis_tvalid <= 1'b1;
        @(posedge aclk);
        demod_s0_axis_tvalid <= 1'b0;
    endtask

    // Demod control packer: {zero[3:0], phrst, mode, outsel[1:0], nsamp[15:0], phase[31:0], freq[31:0]}
    function automatic [87:0] pack_ctrl_demod (
        input logic [31:0] freq,
        input logic [31:0] phase,
        input logic [15:0] nsamp,
        input logic [1:0]  outsel,
        input logic        mode,
        input logic        phrst
    );
        logic [87:0] w;
        w = '0;
        w[31:0]   = freq;            // [31:0]
        w[63:32]  = phase;           // [63:32]
        w[79:64]  = nsamp;           // [79:64]
        w[81:80]  = outsel;          // [81:80]
        w[82]     = mode;            // [82]
        w[83]     = phrst;           // [83]
        // w[87:84] are zeros
        return w;
    endfunction

    // -----------------------------------------------------------------------------
    // Simple monitors
    // -----------------------------------------------------------------------------
    int samp_cnt_m1 = 0;
    always @(posedge aclk) begin
        if (demod_m1_axis_tvalid && demod_m1_axis_tready) begin
            samp_cnt_m1++;
            if ((samp_cnt_m1 % 128) == 0) begin
                $display("%0t : demod m1 sample[%0d] I=%0d Q=%0d",
                         $time, samp_cnt_m1,
                         $signed(demod_m1_axis_tdata[15:0]),
                         $signed(demod_m1_axis_tdata[31:16]));
            end
        end
    end

    // Optional: peek lane-0 of generator (before lane shrink)
    int gen_samp_cnt = 0;
    always @(posedge aclk) begin
        if (gen_m_axis_tvalid && gen_m_axis_tready) begin
            gen_samp_cnt++;
            if ((gen_samp_cnt % 64) == 0) begin
                $display("%0t : gen sample[%0d] lane0 = %0d",
                         $time, gen_samp_cnt,
                         $signed(gen_m_axis_tdata[15:0]));
            end
        end
    end

    // -----------------------------------------------------------------------------
    // Stimulus
    // -----------------------------------------------------------------------------
    real f1 = 1.0e6;
    real f2 = 5.0e6;
    real f3 = 50.0e6;
    logic [31:0] pinc1, pinc2, pinc3;

    int FCLK_MHz = int'(F_ACLK_HZ/1.0e6);
    initial begin
        // Global Reset
        aresetn         = 1'b0;
        s_axi_aresetn   = 1'b0;
        s0_axis_aresetn = 1'b0;
        demod_s0_axis_tvalid = 1'b0;
        gen_s1_axis_tvalid   = 1'b0;

        repeat (10) @(posedge aclk);
        aresetn         = 1'b1;
        s_axi_aresetn   = 1'b1;
        s0_axis_aresetn = 1'b1;

        repeat (10) @(posedge aclk);

        // Compute generator frequency steps (2^32 scaling, Fs = F_ACLK_HZ * N_GEN)
        pinc1 = calc_pinc_gen(f1);
        pinc2 = calc_pinc_gen(f2);
        pinc3 = calc_pinc_gen(f3);

        // Program generator: push three tones (same as your original TB style)
        push_ctrl_gen(
            pack_ctrl_gen(pinc1, 32'd0, 16'd0, 16'h4000, 16'd2048, 2'd1, 1'b0, 1'b0, 1'b0)
        );
        push_ctrl_demod(
            pack_ctrl_demod(freq_calc_demod(f1), 32'd0, 16'd64, 2'd0, 1'b1, 1'b0)
        );
        repeat (2000) @(posedge aclk);
        push_ctrl_gen(
            pack_ctrl_gen(pinc2, 32'd0, 16'd0, 16'h4000, 16'd2048, 2'd1, 1'b0, 1'b0, 1'b0)
        );
        push_ctrl_demod(
            pack_ctrl_demod(freq_calc_demod(f2), 32'd0, 16'd128, 2'd0, 1'b1, 1'b1)
        );
        repeat (4000) @(posedge aclk);
        push_ctrl_gen(
            pack_ctrl_gen(pinc3, 32'd0, 16'd0, 16'h4000, 16'd2048, 2'd1, 1'b0, 1'b0, 1'b0)
        );
        push_ctrl_demod(
            pack_ctrl_demod(freq_calc_demod(f3), 32'd0, 16'd256, 2'd0, 1'b1, 1'b1)
        );
        repeat (20000) @(posedge aclk);

        // Program demod LO: match the same tones (2^31 scaling by default here)
        // If you know demod expects 2^32, change the function accordingly.
        $display("DEMOD: N_DEMOD=%0d, aclk=%.3f MHz => Fs=%.3f Msps ",
                 N_DEMOD, F_ACLK_HZ/1e6, (F_ACLK_HZ*N_DEMOD)/1e6);
        // Run for a while and finish
        $finish;
    end

endmodule

// -----------------------------------------------------------------------------
// AXI-Stream lane shrink adapter (IN_LANES -> OUT_LANES, integer ratio)
// * For each input beat of IN_LANES samples, it emits RATIO beats of OUT_LANES,
//   slicing the input vector into contiguous chunks.
// * Backpressure on the output side will throttle the input via s_axis_tready.
// * No TLAST here since original ports do not expose it.
// -----------------------------------------------------------------------------
module axis_lane_shrink #(
    parameter int IN_LANES  = 16,
    parameter int OUT_LANES = 8,
    parameter int SAMPLE_W  = 16
) (
    input  wire                          aclk,
    input  wire                          aresetn,

    // Input AXIS
    input  wire                          s_axis_tvalid,
    output wire                          s_axis_tready,
    input  wire [IN_LANES*SAMPLE_W-1:0]  s_axis_tdata,

    // Output AXIS
    output wire                          m_axis_tvalid,
    input  wire                          m_axis_tready,
    output wire [OUT_LANES*SAMPLE_W-1:0] m_axis_tdata
);
    localparam int RATIO = IN_LANES / OUT_LANES;
    initial begin
        if (IN_LANES % OUT_LANES != 0) begin
            $error("axis_lane_shrink: IN_LANES must be multiple of OUT_LANES");
        end
    end

    typedef enum logic [1:0] {IDLE=2'd0, SEND=2'd1} state_t;
    state_t state;

    reg [IN_LANES*SAMPLE_W-1:0] buf_samp;
    integer idx; // 0..RATIO-1

    // Ready when idle (we can accept a new input beat)
    assign s_axis_tready = (state == IDLE);

    // Output valid when in SEND state
    assign m_axis_tvalid = (state == SEND);

    // Slice selection
    reg [OUT_LANES*SAMPLE_W-1:0] slice;
    assign m_axis_tdata = slice;

    // Build current slice based on idx
    always @(*) begin
        int lo = idx*OUT_LANES*SAMPLE_W;
        slice = buf_samp[lo +: OUT_LANES*SAMPLE_W];
    end

    // FSM
    always @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            state <= IDLE;
            idx   <= 0;
            buf_samp   <= '0;
        end else begin
            case (state)
                IDLE: begin
                    if (s_axis_tvalid && s_axis_tready) begin
                        buf_samp   <= s_axis_tdata;
                        idx   <= 0;
                        state <= SEND;
                    end
                end
                SEND: begin
                    if (m_axis_tvalid && m_axis_tready) begin
                        if (idx == (RATIO-1)) begin
                            state <= IDLE;
                            idx   <= 0;
                        end else begin
                            idx <= idx + 1;
                            state <= SEND;
                        end
                    end
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
