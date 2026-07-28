// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps

// Sample-count DDR capture buffer with programmable trigger delay.
//
// Capture control:
//   - AXI-Lite programs a byte address, output samples per trigger, trigger
//     count, optional stride, optional sample decimation, and trigger delay.
//   - In the source clock domain, trigger rising edges start finite captures.
//   - trigger_delay_cycles_reg delays each accepted trigger by a programmable
//     number of s_axis_aclk cycles. Filtering and upstream decimation continue
//     independently.
//   - A free-running 32-bit timestamp is added to the programmed delay and the
//     resulting due timestamp is stored in a FIFO. Delay length therefore does
//     not change the hardware depth.
//   - Due timestamps are compared for equality. The programmed delay remains
//     fixed while armed, so trigger order is preserved across 32-bit timestamp
//     wraparound without a signed deadline comparison.
//   - A pending-event counter holds due triggers while a finite capture is
//     active. The capture FSM consumes those events in order.
//   - The local sample-picker phase is aligned when capture starts.
//     sample_decim_reg = 0 or
//     1 keeps every input sample. N > 1 keeps samples 0, N, 2N, ...
//   - Exactly nsamp_reg decimated 32-bit samples are written to an internal
//     async FIFO per trigger event.
//
// DDR write path:
//   - The DDR clock domain reads the FIFO, packs eight 32-bit samples into one
//     256-bit AXI write word, and zero-pads the final partial word of each
//     trigger event.
//   - Lane order is little-lane:
//       sample 0 -> m_axi_wdata[ 31:  0]
//       sample 1 -> m_axi_wdata[ 63: 32]
//       ...
//       sample 7 -> m_axi_wdata[255:224]
//   - Every AXI write is a 256-bit single-beat INCR burst with AWLEN=0.

module axis_buffer_ddr_sample_v2 #(
    parameter TARGET_SLAVE_BASE_ADDR = 32'h0000_0000,
    parameter ID_WIDTH               = 1,
    parameter S_AXIS_DATA_WIDTH      = 32,
    parameter M_AXI_DATA_WIDTH       = 256,
    parameter FIFO_ADDR_WIDTH        = 6,
    parameter TRIGGER_QUEUE_ADDR_WIDTH = 6,
    parameter DEFAULT_TRIGGER_DELAY_CYCLES = 281970
)(
    // Source/readout AXIS clock domain.
    input  wire                          s_axis_aclk,
    input  wire                          s_axis_aresetn,

    // DDR UI / AXI master clock domain.
    input  wire                          m_axi_aclk,
    input  wire                          m_axi_aresetn,

    // AXI-Lite clock domain.
    input  wire                          s_axi_aclk,
    input  wire                          s_axi_aresetn,

    // Trigger input. Synchronize internally to s_axis_aclk.
    input  wire                          trigger,

    // 32-bit AXIS input.
    output wire                          s_axis_tready,
    input  wire [S_AXIS_DATA_WIDTH-1:0]  s_axis_tdata,
    input  wire                          s_axis_tvalid,
    input  wire                          s_axis_tlast,

    // AXI-Lite slave.
    input  wire [7:0]                    s_axi_awaddr,
    input  wire [2:0]                    s_axi_awprot,
    input  wire                          s_axi_awvalid,
    output reg                           s_axi_awready,
    input  wire [31:0]                   s_axi_wdata,
    input  wire [3:0]                    s_axi_wstrb,
    input  wire                          s_axi_wvalid,
    output reg                           s_axi_wready,
    output wire [1:0]                    s_axi_bresp,
    output reg                           s_axi_bvalid,
    input  wire                          s_axi_bready,
    input  wire [7:0]                    s_axi_araddr,
    input  wire [2:0]                    s_axi_arprot,
    input  wire                          s_axi_arvalid,
    output reg                           s_axi_arready,
    output reg [31:0]                    s_axi_rdata,
    output wire [1:0]                    s_axi_rresp,
    output reg                           s_axi_rvalid,
    input  wire                          s_axi_rready,

    // 256-bit AXI4 master write interface.
    output wire [ID_WIDTH-1:0]           m_axi_awid,
    output reg  [31:0]                   m_axi_awaddr,
    output wire [7:0]                    m_axi_awlen,
    output wire [2:0]                    m_axi_awsize,
    output wire [1:0]                    m_axi_awburst,
    output wire                          m_axi_awlock,
    output wire [3:0]                    m_axi_awcache,
    output wire [2:0]                    m_axi_awprot,
    output wire [3:0]                    m_axi_awregion,
    output wire [3:0]                    m_axi_awqos,
    output reg                           m_axi_awvalid,
    input  wire                          m_axi_awready,

    output reg  [M_AXI_DATA_WIDTH-1:0]   m_axi_wdata,
    output wire [M_AXI_DATA_WIDTH/8-1:0] m_axi_wstrb,
    output wire                          m_axi_wlast,
    output reg                           m_axi_wvalid,
    input  wire                          m_axi_wready,

    input  wire [ID_WIDTH-1:0]           m_axi_bid,
    input  wire [1:0]                    m_axi_bresp,
    input  wire                          m_axi_bvalid,
    output wire                          m_axi_bready
);

    localparam int LANES           = M_AXI_DATA_WIDTH / S_AXIS_DATA_WIDTH;
    localparam int FIFO_WIDTH      = S_AXIS_DATA_WIDTH + 1;
    localparam int AXI_SIZE_32BYTE = 5;
    localparam int TRIGGER_QUEUE_DEPTH = 1 << TRIGGER_QUEUE_ADDR_WIDTH;
    localparam int TRIGGER_QUEUE_COUNT_WIDTH =
        $clog2(TRIGGER_QUEUE_DEPTH + 1);

    localparam int REG_CONTROL       = 0;
    localparam int REG_WADDR         = 1;
    localparam int REG_NSAMP         = 2;
    localparam int REG_NTRIG         = 3;
    localparam int REG_STRIDE        = 4;
    localparam int REG_STATUS        = 5;
    localparam int REG_SAMPLE_COUNT  = 6;
    localparam int REG_TRIGGER_COUNT = 7;
    localparam int REG_SAMPLE_DECIM  = 8;
    localparam int REG_TRIGGER_DELAY = 9;

    wire unused_axi_inputs = |s_axi_awprot | |s_axi_arprot | |s_axis_tlast | |s_axi_wstrb | |m_axi_bid;

    //--------------------------------------------------------------------------
    // AXI-Lite register bank.
    //--------------------------------------------------------------------------
    reg [31:0] waddr_reg;
    reg [31:0] nsamp_reg;
    reg [31:0] ntrig_reg;
    reg [31:0] stride_reg;
    reg [31:0] sample_decim_reg;
    reg [31:0] trigger_delay_cycles_reg;

    reg arm_toggle_axi;
    reg soft_reset_toggle_axi;

    reg [2:0] busy_m_axi_sync;
    reg [2:0] done_m_axi_sync;
    reg [2:0] overflow_m_axi_sync;
    reg [2:0] overflow_s_axi_sync;
    reg [2:0] armed_s_axi_sync;

    reg [31:0] sample_count_s_axi_meta;
    reg [31:0] sample_count_s_axi;
    reg [31:0] trigger_count_s_axi_meta;
    reg [31:0] trigger_count_s_axi;

    reg done_sticky_axi;
    reg overflow_sticky_axi;

    reg [31:0] sample_count_s;
    reg [31:0] trigger_count_s;
    reg        armed_s;
    reg        overflow_s;

    reg        busy_m;
    reg        done_m;
    reg        overflow_m;

    wire busy_axi     = busy_m_axi_sync[2];
    wire done_axi     = done_sticky_axi | done_m_axi_sync[2];
    wire overflow_axi = overflow_sticky_axi | overflow_m_axi_sync[2] | overflow_s_axi_sync[2];
    wire armed_axi    = armed_s_axi_sync[2];

    assign s_axi_bresp = 2'b00;
    assign s_axi_rresp = 2'b00;

    always_ff @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            waddr_reg             <= 32'd0;
            nsamp_reg             <= 32'd0;
            ntrig_reg             <= 32'd0;
            stride_reg            <= 32'd0;
            sample_decim_reg      <= 32'd1;
            trigger_delay_cycles_reg <= DEFAULT_TRIGGER_DELAY_CYCLES;
            arm_toggle_axi        <= 1'b0;
            soft_reset_toggle_axi <= 1'b0;
            s_axi_awready         <= 1'b0;
            s_axi_wready          <= 1'b0;
            s_axi_bvalid          <= 1'b0;
            s_axi_arready         <= 1'b0;
            s_axi_rvalid          <= 1'b0;
            s_axi_rdata           <= 32'd0;
            done_sticky_axi       <= 1'b0;
            overflow_sticky_axi   <= 1'b0;
            busy_m_axi_sync       <= 3'b000;
            done_m_axi_sync       <= 3'b000;
            overflow_m_axi_sync   <= 3'b000;
            overflow_s_axi_sync   <= 3'b000;
            armed_s_axi_sync      <= 3'b000;
            sample_count_s_axi_meta  <= 32'd0;
            sample_count_s_axi       <= 32'd0;
            trigger_count_s_axi_meta <= 32'd0;
            trigger_count_s_axi      <= 32'd0;
        end else begin
            s_axi_awready <= 1'b0;
            s_axi_wready  <= 1'b0;
            s_axi_arready <= 1'b0;

            busy_m_axi_sync     <= {busy_m_axi_sync[1:0], busy_m};
            done_m_axi_sync     <= {done_m_axi_sync[1:0], done_m};
            overflow_m_axi_sync <= {overflow_m_axi_sync[1:0], overflow_m};
            overflow_s_axi_sync <= {overflow_s_axi_sync[1:0], overflow_s};
            armed_s_axi_sync    <= {armed_s_axi_sync[1:0], armed_s};

            sample_count_s_axi_meta  <= sample_count_s;
            sample_count_s_axi       <= sample_count_s_axi_meta;
            trigger_count_s_axi_meta <= trigger_count_s;
            trigger_count_s_axi      <= trigger_count_s_axi_meta;

            if (done_m_axi_sync[2])
                done_sticky_axi <= 1'b1;
            if (overflow_m_axi_sync[2] || overflow_s_axi_sync[2])
                overflow_sticky_axi <= 1'b1;

            if (s_axi_bvalid && s_axi_bready)
                s_axi_bvalid <= 1'b0;

            if (!s_axi_bvalid && s_axi_awvalid && s_axi_wvalid) begin
                s_axi_awready <= 1'b1;
                s_axi_wready  <= 1'b1;
                s_axi_bvalid  <= 1'b1;

                case (s_axi_awaddr[7:2])
                    REG_CONTROL: begin
                        if (s_axi_wdata[1])
                            soft_reset_toggle_axi <= ~soft_reset_toggle_axi;
                        if (s_axi_wdata[2]) begin
                            done_sticky_axi     <= 1'b0;
                            overflow_sticky_axi <= 1'b0;
                        end
                        if (s_axi_wdata[0] && !busy_axi) begin
                            done_sticky_axi     <= 1'b0;
                            overflow_sticky_axi <= 1'b0;
                            arm_toggle_axi      <= ~arm_toggle_axi;
                        end
                    end
                    REG_WADDR:
                        if (!busy_axi) waddr_reg <= s_axi_wdata;
                    REG_NSAMP:
                        if (!busy_axi) nsamp_reg <= s_axi_wdata;
                    REG_NTRIG:
                        if (!busy_axi) ntrig_reg <= s_axi_wdata;
                    REG_STRIDE:
                        if (!busy_axi) stride_reg <= s_axi_wdata;
                    REG_SAMPLE_DECIM:
                        if (!busy_axi) sample_decim_reg <= s_axi_wdata;
                    REG_TRIGGER_DELAY:
                        if (!busy_axi) trigger_delay_cycles_reg <= s_axi_wdata;
                    default: begin
                    end
                endcase
            end

            if (s_axi_rvalid && s_axi_rready)
                s_axi_rvalid <= 1'b0;

            if (!s_axi_rvalid && s_axi_arvalid) begin
                s_axi_arready <= 1'b1;
                s_axi_rvalid  <= 1'b1;
                case (s_axi_araddr[7:2])
                    REG_CONTROL:
                        s_axi_rdata <= 32'd0;
                    REG_WADDR:
                        s_axi_rdata <= waddr_reg;
                    REG_NSAMP:
                        s_axi_rdata <= nsamp_reg;
                    REG_NTRIG:
                        s_axi_rdata <= ntrig_reg;
                    REG_STRIDE:
                        s_axi_rdata <= stride_reg;
                    REG_STATUS:
                        s_axi_rdata <= {24'd0, 4'd0, armed_axi, overflow_axi, done_axi, busy_axi};
                    REG_SAMPLE_COUNT:
                        s_axi_rdata <= sample_count_s_axi;
                    REG_TRIGGER_COUNT:
                        s_axi_rdata <= trigger_count_s_axi;
                    REG_SAMPLE_DECIM:
                        s_axi_rdata <= sample_decim_reg;
                    REG_TRIGGER_DELAY:
                        s_axi_rdata <= trigger_delay_cycles_reg;
                    default:
                        s_axi_rdata <= 32'd0;
                endcase
            end
        end
    end

    //--------------------------------------------------------------------------
    // Source/readout clock domain: trigger detection and finite sample capture.
    //--------------------------------------------------------------------------
    reg [2:0] arm_s_sync;
    reg [2:0] soft_reset_s_sync;
    reg       arm_s_seen;
    reg       soft_reset_s_seen;

    wire arm_pulse_s        = arm_s_sync[2] ^ arm_s_seen;
    wire soft_reset_pulse_s = soft_reset_s_sync[2] ^ soft_reset_s_seen;

    reg [31:0] nsamp_s;
    reg [31:0] ntrig_s;
    reg [31:0] sample_decim_s;
    reg [31:0] decim_count_s;
    reg [31:0] accepted_trigger_count_s;
    reg [31:0] trigger_delay_cycles_s;
    reg [31:0] trigger_timestamp_s;
    reg [31:0] trigger_due_queue_s [0:TRIGGER_QUEUE_DEPTH-1];
    reg [TRIGGER_QUEUE_ADDR_WIDTH-1:0] trigger_queue_wr_ptr_s;
    reg [TRIGGER_QUEUE_ADDR_WIDTH-1:0] trigger_queue_rd_ptr_s;
    reg [TRIGGER_QUEUE_COUNT_WIDTH-1:0] trigger_queue_count_s;
    reg [31:0] trigger_queue_head_due_s;
    reg [31:0] trigger_pending_count_s;

    typedef enum logic {
        TRIGGER_QUEUE_EMPTY_ST,
        TRIGGER_QUEUE_WAIT_ST
    } trigger_queue_state_t;
    trigger_queue_state_t trigger_queue_state_s;

    typedef enum logic {
        CAPTURE_WAIT_ST,
        CAPTURE_ACTIVE_ST
    } capture_state_t;
    capture_state_t capture_state_s;
    wire capture_s = (capture_state_s == CAPTURE_ACTIVE_ST);

    reg trigger_meta_s;
    reg trigger_sync_s;
    reg trigger_sync_d_s;

    wire trigger_rise_s = trigger_sync_s & ~trigger_sync_d_s;

    wire fifo_wfull;
    wire fifo_rempty;
    wire fifo_wen;
    wire fifo_ren;
    wire [FIFO_WIDTH-1:0] fifo_wdata;
    wire [FIFO_WIDTH-1:0] fifo_rdata;
    wire fifo_wr_rstn = s_axis_aresetn && !soft_reset_pulse_s;

    wire [31:0] effective_sample_decim_s = (sample_decim_s == 32'd0) ? 32'd1 : sample_decim_s;
    wire sample_due_s = (decim_count_s == 32'd0);
    wire capture_ready_s = sample_due_s ? !fifo_wfull : 1'b1;
    wire trigger_queue_full_s =
        (trigger_queue_count_s == TRIGGER_QUEUE_DEPTH);
    wire trigger_queue_due_s =
        (trigger_queue_state_s == TRIGGER_QUEUE_WAIT_ST) &&
        (trigger_timestamp_s == trigger_queue_head_due_s);
    wire trigger_pending_full_s = &trigger_pending_count_s;
    wire trigger_accept_request_s =
        armed_s &&
        trigger_rise_s &&
        (accepted_trigger_count_s < ntrig_s);
    wire trigger_accept_s =
        trigger_accept_request_s &&
        ((trigger_delay_cycles_s == 32'd0) ||
         !trigger_queue_full_s ||
         trigger_queue_due_s);
    wire trigger_enqueue_s =
        trigger_accept_s &&
        (trigger_delay_cycles_s != 32'd0);
    wire [31:0] trigger_new_due_s =
        trigger_timestamp_s + trigger_delay_cycles_s;
    wire trigger_mature_s =
        trigger_queue_due_s ||
        (trigger_accept_s && (trigger_delay_cycles_s == 32'd0));
    wire trigger_available_s =
        (trigger_pending_count_s != 0) || trigger_mature_s;
    wire trigger_start_s =
        armed_s &&
        !capture_s &&
        trigger_available_s &&
        s_axis_tvalid &&
        capture_ready_s;
    wire trigger_mature_accept_s =
        trigger_mature_s &&
        (!trigger_pending_full_s || trigger_start_s);
    wire capture_active_s = capture_s || trigger_start_s;

    assign s_axis_tready =
        capture_s
            ? capture_ready_s
            : (trigger_available_s ? capture_ready_s : 1'b1);

    wire input_fire_s = s_axis_tvalid & s_axis_tready;
    wire output_fire_s = capture_active_s && input_fire_s && sample_due_s;
    wire last_sample_s = output_fire_s && (sample_count_s == (nsamp_s - 1));

    assign fifo_wen   = output_fire_s;
    assign fifo_wdata = {last_sample_s, s_axis_tdata};

    always_ff @(posedge s_axis_aclk) begin
        if (!s_axis_aresetn) begin
            arm_s_sync        <= 3'b000;
            soft_reset_s_sync <= 3'b000;
            arm_s_seen        <= 1'b0;
            soft_reset_s_seen <= 1'b0;
            nsamp_s           <= 32'd0;
            ntrig_s           <= 32'd0;
            sample_decim_s    <= 32'd1;
            decim_count_s     <= 32'd0;
            accepted_trigger_count_s <= 32'd0;
            trigger_delay_cycles_s   <= DEFAULT_TRIGGER_DELAY_CYCLES;
            trigger_timestamp_s      <= 32'd0;
            trigger_queue_wr_ptr_s   <= '0;
            trigger_queue_rd_ptr_s   <= '0;
            trigger_queue_count_s    <= '0;
            trigger_queue_head_due_s <= 32'd0;
            trigger_pending_count_s  <= 32'd0;
            trigger_queue_state_s    <= TRIGGER_QUEUE_EMPTY_ST;
            sample_count_s    <= 32'd0;
            trigger_count_s   <= 32'd0;
            armed_s           <= 1'b0;
            capture_state_s   <= CAPTURE_WAIT_ST;
            overflow_s        <= 1'b0;
            trigger_meta_s    <= 1'b0;
            trigger_sync_s    <= 1'b0;
            trigger_sync_d_s  <= 1'b0;
        end else begin
            arm_s_sync        <= {arm_s_sync[1:0], arm_toggle_axi};
            soft_reset_s_sync <= {soft_reset_s_sync[1:0], soft_reset_toggle_axi};
            trigger_meta_s    <= trigger;
            trigger_sync_s    <= trigger_meta_s;
            trigger_sync_d_s  <= trigger_sync_s;
            trigger_timestamp_s <= trigger_timestamp_s + 1'b1;

            if (soft_reset_pulse_s) begin
                soft_reset_s_seen <= soft_reset_s_sync[2];
                arm_s_seen        <= arm_s_sync[2];
                sample_count_s    <= 32'd0;
                trigger_count_s   <= 32'd0;
                decim_count_s     <= 32'd0;
                accepted_trigger_count_s <= 32'd0;
                trigger_delay_cycles_s   <= DEFAULT_TRIGGER_DELAY_CYCLES;
                trigger_queue_wr_ptr_s   <= '0;
                trigger_queue_rd_ptr_s   <= '0;
                trigger_queue_count_s    <= '0;
                trigger_queue_head_due_s <= 32'd0;
                trigger_pending_count_s  <= 32'd0;
                trigger_queue_state_s    <= TRIGGER_QUEUE_EMPTY_ST;
                armed_s           <= 1'b0;
                capture_state_s   <= CAPTURE_WAIT_ST;
                overflow_s        <= 1'b0;
            end else begin
                if (arm_pulse_s) begin
                    arm_s_seen      <= arm_s_sync[2];
                    nsamp_s         <= nsamp_reg;
                    ntrig_s         <= ntrig_reg;
                    sample_decim_s  <= sample_decim_reg;
                    decim_count_s   <= 32'd0;
                    accepted_trigger_count_s <= 32'd0;
                    trigger_delay_cycles_s   <= trigger_delay_cycles_reg;
                    trigger_queue_wr_ptr_s   <= '0;
                    trigger_queue_rd_ptr_s   <= '0;
                    trigger_queue_count_s    <= '0;
                    trigger_queue_head_due_s <= 32'd0;
                    trigger_pending_count_s  <= 32'd0;
                    trigger_queue_state_s    <= TRIGGER_QUEUE_EMPTY_ST;
                    sample_count_s  <= 32'd0;
                    trigger_count_s <= 32'd0;
                    capture_state_s <= CAPTURE_WAIT_ST;
                    overflow_s      <= 1'b0;
                    armed_s         <=
                        (nsamp_reg != 32'd0) &&
                        (ntrig_reg != 32'd0);
                    if ((nsamp_reg == 32'd0) ||
                        (ntrig_reg == 32'd0))
                        overflow_s <= 1'b1;
                end else begin
                    case ({trigger_enqueue_s, trigger_queue_due_s})
                        2'b10: begin
                            trigger_due_queue_s[trigger_queue_wr_ptr_s] <=
                                trigger_new_due_s;
                            trigger_queue_wr_ptr_s <=
                                trigger_queue_wr_ptr_s + 1'b1;
                            trigger_queue_count_s <=
                                trigger_queue_count_s + 1'b1;
                            if (trigger_queue_state_s ==
                                TRIGGER_QUEUE_EMPTY_ST)
                                trigger_queue_head_due_s <=
                                    trigger_new_due_s;
                            trigger_queue_state_s <=
                                TRIGGER_QUEUE_WAIT_ST;
                        end
                        2'b01: begin
                            trigger_queue_rd_ptr_s <=
                                trigger_queue_rd_ptr_s + 1'b1;
                            trigger_queue_count_s <=
                                trigger_queue_count_s - 1'b1;
                            if (trigger_queue_count_s == 1) begin
                                trigger_queue_state_s <=
                                    TRIGGER_QUEUE_EMPTY_ST;
                            end else begin
                                trigger_queue_head_due_s <=
                                    trigger_due_queue_s[
                                        trigger_queue_rd_ptr_s + 1'b1
                                    ];
                                trigger_queue_state_s <=
                                    TRIGGER_QUEUE_WAIT_ST;
                            end
                        end
                        2'b11: begin
                            trigger_due_queue_s[trigger_queue_wr_ptr_s] <=
                                trigger_new_due_s;
                            trigger_queue_wr_ptr_s <=
                                trigger_queue_wr_ptr_s + 1'b1;
                            trigger_queue_rd_ptr_s <=
                                trigger_queue_rd_ptr_s + 1'b1;
                            if (trigger_queue_count_s == 1)
                                trigger_queue_head_due_s <=
                                    trigger_new_due_s;
                            else
                                trigger_queue_head_due_s <=
                                    trigger_due_queue_s[
                                        trigger_queue_rd_ptr_s + 1'b1
                                    ];
                            trigger_queue_state_s <=
                                TRIGGER_QUEUE_WAIT_ST;
                        end
                        default: begin
                        end
                    endcase

                    if (trigger_accept_s)
                        accepted_trigger_count_s <=
                            accepted_trigger_count_s + 1'b1;

                    if (trigger_accept_request_s && !trigger_accept_s)
                        overflow_s <= 1'b1;

                    if (trigger_start_s) begin
                        sample_count_s <= 32'd0;
                        decim_count_s  <= 32'd0;
                    end

                    case ({trigger_mature_accept_s, trigger_start_s})
                        2'b10:
                            trigger_pending_count_s <=
                                trigger_pending_count_s + 1'b1;
                        2'b01:
                            trigger_pending_count_s <=
                                trigger_pending_count_s - 1'b1;
                        default: begin
                        end
                    endcase

                    if (trigger_mature_s &&
                        trigger_pending_full_s &&
                        !trigger_start_s)
                        overflow_s <= 1'b1;

                    if (capture_active_s &&
                        s_axis_tvalid &&
                        sample_due_s &&
                        fifo_wfull)
                        overflow_s <= 1'b1;

                    if (capture_active_s && input_fire_s) begin
                        if (sample_due_s) begin
                            if (last_sample_s) begin
                                capture_state_s <= CAPTURE_WAIT_ST;
                                sample_count_s  <= 32'd0;
                                decim_count_s   <= 32'd0;
                                trigger_count_s <= trigger_count_s + 1;
                                if ((trigger_count_s + 1) >= ntrig_s)
                                    armed_s <= 1'b0;
                            end else begin
                                capture_state_s <= CAPTURE_ACTIVE_ST;
                                sample_count_s <= sample_count_s + 1;
                                decim_count_s  <= (effective_sample_decim_s > 32'd1) ? (effective_sample_decim_s - 32'd1) : 32'd0;
                            end
                        end else begin
                            decim_count_s <= decim_count_s - 32'd1;
                        end
                    end
                end
            end
        end
    end

    //--------------------------------------------------------------------------
    // DDR UI clock domain: 32-bit FIFO read, 256-bit packing, single-beat AXI.
    //--------------------------------------------------------------------------
    reg [2:0] arm_m_sync;
    reg [2:0] soft_reset_m_sync;
    reg       arm_m_seen;
    reg       soft_reset_m_seen;

    wire arm_pulse_m        = arm_m_sync[2] ^ arm_m_seen;
    wire soft_reset_pulse_m = soft_reset_m_sync[2] ^ soft_reset_m_seen;
    wire fifo_rd_rstn       = m_axi_aresetn && !soft_reset_pulse_m;

    reg [31:0] waddr_m;
    reg [31:0] nsamp_m;
    reg [31:0] ntrig_m;
    reg [31:0] stride_m;
    reg [31:0] stride_bytes_m;
    reg [31:0] event_base_addr_m;
    reg [31:0] word_index_m;
    reg [31:0] event_index_m;

    reg [M_AXI_DATA_WIDTH-1:0] pack_data_m;
    reg [2:0]                  pack_count_m;
    reg                        write_active_m;
    reg                        write_event_last_m;

    wire cfg_aligned_m = (waddr_reg[4:0] == 5'd0) && ((stride_reg == 32'd0) || (stride_reg[4:0] == 5'd0));
    wire cfg_valid_m   = (nsamp_reg != 32'd0) && (ntrig_reg != 32'd0) && cfg_aligned_m;

    function automatic [31:0] auto_stride_bytes(input [31:0] nsamp);
        begin
            auto_stride_bytes = (((nsamp + 32'd7) >> 3) << 5);
        end
    endfunction

    assign fifo_ren = busy_m && !write_active_m && !fifo_rempty;

    assign m_axi_awid     = '0;
    assign m_axi_awlen    = 8'd0;
    assign m_axi_awsize   = AXI_SIZE_32BYTE[2:0];
    assign m_axi_awburst  = 2'b01;
    assign m_axi_awlock   = 1'b0;
    assign m_axi_awcache  = 4'b0000;
    assign m_axi_awprot   = 3'b010;
    assign m_axi_awregion = 4'b0000;
    assign m_axi_awqos    = 4'b0000;

    assign m_axi_wstrb  = {M_AXI_DATA_WIDTH/8{1'b1}};
    assign m_axi_wlast  = 1'b1;
    assign m_axi_bready = write_active_m && !m_axi_awvalid && !m_axi_wvalid;

    always_ff @(posedge m_axi_aclk) begin
        logic [M_AXI_DATA_WIDTH-1:0] pack_next;
        logic fifo_event_last;

        if (!m_axi_aresetn) begin
            arm_m_sync          <= 3'b000;
            soft_reset_m_sync   <= 3'b000;
            arm_m_seen          <= 1'b0;
            soft_reset_m_seen   <= 1'b0;
            waddr_m             <= 32'd0;
            nsamp_m             <= 32'd0;
            ntrig_m             <= 32'd0;
            stride_m            <= 32'd0;
            stride_bytes_m      <= 32'd0;
            event_base_addr_m   <= 32'd0;
            word_index_m        <= 32'd0;
            event_index_m       <= 32'd0;
            pack_data_m         <= '0;
            pack_count_m        <= 3'd0;
            write_active_m      <= 1'b0;
            write_event_last_m  <= 1'b0;
            busy_m              <= 1'b0;
            done_m              <= 1'b0;
            overflow_m          <= 1'b0;
            m_axi_awaddr        <= 32'd0;
            m_axi_awvalid       <= 1'b0;
            m_axi_wdata         <= '0;
            m_axi_wvalid        <= 1'b0;
        end else begin
            arm_m_sync        <= {arm_m_sync[1:0], arm_toggle_axi};
            soft_reset_m_sync <= {soft_reset_m_sync[1:0], soft_reset_toggle_axi};

            if (soft_reset_pulse_m) begin
                soft_reset_m_seen  <= soft_reset_m_sync[2];
                arm_m_seen         <= arm_m_sync[2];
                write_active_m     <= 1'b0;
                busy_m             <= 1'b0;
                done_m             <= 1'b0;
                overflow_m         <= 1'b0;
                m_axi_awvalid      <= 1'b0;
                m_axi_wvalid       <= 1'b0;
                pack_data_m        <= '0;
                pack_count_m       <= 3'd0;
                event_index_m      <= 32'd0;
                word_index_m       <= 32'd0;
            end else begin
                if (arm_pulse_m) begin
                    arm_m_seen        <= arm_m_sync[2];
                    waddr_m           <= waddr_reg;
                    nsamp_m           <= nsamp_reg;
                    ntrig_m           <= ntrig_reg;
                    stride_m          <= stride_reg;
                    stride_bytes_m    <= (stride_reg != 32'd0) ? stride_reg : auto_stride_bytes(nsamp_reg);
                    event_base_addr_m <= TARGET_SLAVE_BASE_ADDR + waddr_reg;
                    word_index_m      <= 32'd0;
                    event_index_m     <= 32'd0;
                    pack_data_m       <= '0;
                    pack_count_m      <= 3'd0;
                    write_active_m    <= 1'b0;
                    m_axi_awvalid     <= 1'b0;
                    m_axi_wvalid      <= 1'b0;
                    overflow_m        <= !cfg_valid_m;
                    busy_m            <= cfg_valid_m;
                    done_m            <= !cfg_valid_m;
                end

                if (m_axi_awvalid && m_axi_awready)
                    m_axi_awvalid <= 1'b0;
                if (m_axi_wvalid && m_axi_wready)
                    m_axi_wvalid <= 1'b0;

                if (write_active_m && !m_axi_awvalid && !m_axi_wvalid && m_axi_bvalid) begin
                    write_active_m <= 1'b0;
                    if (m_axi_bresp != 2'b00)
                        overflow_m <= 1'b1;

                    if (write_event_last_m) begin
                        word_index_m <= 32'd0;
                        if ((event_index_m + 1) >= ntrig_m) begin
                            event_index_m <= event_index_m + 1;
                            busy_m        <= 1'b0;
                            done_m        <= 1'b1;
                        end else begin
                            event_index_m     <= event_index_m + 1;
                            event_base_addr_m <= event_base_addr_m + stride_bytes_m;
                        end
                    end else begin
                        word_index_m <= word_index_m + 1;
                    end
                end

                if (fifo_ren) begin
                    pack_next = pack_data_m;
                    fifo_event_last = fifo_rdata[S_AXIS_DATA_WIDTH];
                    pack_next[pack_count_m*S_AXIS_DATA_WIDTH +: S_AXIS_DATA_WIDTH] = fifo_rdata[S_AXIS_DATA_WIDTH-1:0];

                    if ((pack_count_m == (LANES-1)) || fifo_event_last) begin
                        m_axi_awaddr       <= event_base_addr_m + (word_index_m << 5);
                        m_axi_awvalid      <= 1'b1;
                        m_axi_wdata        <= pack_next;
                        m_axi_wvalid       <= 1'b1;
                        write_active_m     <= 1'b1;
                        write_event_last_m <= fifo_event_last;
                        pack_data_m        <= '0;
                        pack_count_m       <= 3'd0;
                    end else begin
                        pack_data_m  <= pack_next;
                        pack_count_m <= pack_count_m + 1;
                    end
                end
            end
        end
    end

    axis_buffer_ddr_sample_async_fifo #(
        .WIDTH      (FIFO_WIDTH),
        .ADDR_WIDTH (FIFO_ADDR_WIDTH)
    ) sample_fifo_i (
        .wr_clk  (s_axis_aclk),
        .wr_rstn (fifo_wr_rstn),
        .wr_en   (fifo_wen),
        .wr_data (fifo_wdata),
        .wr_full (fifo_wfull),
        .rd_clk  (m_axi_aclk),
        .rd_rstn (fifo_rd_rstn),
        .rd_en   (fifo_ren),
        .rd_data (fifo_rdata),
        .rd_empty(fifo_rempty)
    );

endmodule

module axis_buffer_ddr_sample_async_fifo #(
    parameter WIDTH = 33,
    parameter ADDR_WIDTH = 6
)(
    input  wire             wr_clk,
    input  wire             wr_rstn,
    input  wire             wr_en,
    input  wire [WIDTH-1:0] wr_data,
    output wire             wr_full,

    input  wire             rd_clk,
    input  wire             rd_rstn,
    input  wire             rd_en,
    output wire [WIDTH-1:0] rd_data,
    output wire             rd_empty
);

    localparam int PTR_WIDTH = ADDR_WIDTH + 1;
    localparam int DEPTH = 1 << ADDR_WIDTH;

    reg [WIDTH-1:0] mem [0:DEPTH-1];

    reg [PTR_WIDTH-1:0] wbin;
    reg [PTR_WIDTH-1:0] wgray;
    reg [PTR_WIDTH-1:0] rbin;
    reg [PTR_WIDTH-1:0] rgray;

    reg [PTR_WIDTH-1:0] rgray_wsync1;
    reg [PTR_WIDTH-1:0] rgray_wsync2;
    reg [PTR_WIDTH-1:0] wgray_rsync1;
    reg [PTR_WIDTH-1:0] wgray_rsync2;

    wire [PTR_WIDTH-1:0] wbin_plus1  = wbin + {{(PTR_WIDTH-1){1'b0}}, 1'b1};
    wire [PTR_WIDTH-1:0] wgray_plus1 = (wbin_plus1 >> 1) ^ wbin_plus1;

    assign wr_full = (wgray_plus1 == {~rgray_wsync2[PTR_WIDTH-1:PTR_WIDTH-2], rgray_wsync2[PTR_WIDTH-3:0]});
    assign rd_empty = (rgray == wgray_rsync2);

    wire winc = wr_en && !wr_full;
    wire rinc = rd_en && !rd_empty;

    wire [PTR_WIDTH-1:0] wbin_next  = wbin + {{(PTR_WIDTH-1){1'b0}}, winc};
    wire [PTR_WIDTH-1:0] wgray_next = (wbin_next >> 1) ^ wbin_next;
    wire [PTR_WIDTH-1:0] rbin_next  = rbin + {{(PTR_WIDTH-1){1'b0}}, rinc};
    wire [PTR_WIDTH-1:0] rgray_next = (rbin_next >> 1) ^ rbin_next;

    assign rd_data = mem[rbin[ADDR_WIDTH-1:0]];

    always_ff @(posedge wr_clk) begin
        if (!wr_rstn) begin
            wbin <= '0;
            wgray <= '0;
            rgray_wsync1 <= '0;
            rgray_wsync2 <= '0;
        end else begin
            rgray_wsync1 <= rgray;
            rgray_wsync2 <= rgray_wsync1;
            if (winc) begin
                mem[wbin[ADDR_WIDTH-1:0]] <= wr_data;
                wbin <= wbin_next;
                wgray <= wgray_next;
            end
        end
    end

    always_ff @(posedge rd_clk) begin
        if (!rd_rstn) begin
            rbin <= '0;
            rgray <= '0;
            wgray_rsync1 <= '0;
            wgray_rsync2 <= '0;
        end else begin
            wgray_rsync1 <= wgray;
            wgray_rsync2 <= wgray_rsync1;
            if (rinc) begin
                rbin <= rbin_next;
                rgray <= rgray_next;
            end
        end
    end

endmodule
