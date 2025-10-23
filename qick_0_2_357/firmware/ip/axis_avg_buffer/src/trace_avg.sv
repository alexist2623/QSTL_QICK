module trace_avg #(
    parameter int unsigned N = 10,   // memory depth = 2**N
    parameter int unsigned B = 16    // per-channel width
) (
    // Reset and clock.
    input  logic              rstn,
    input  logic              clk,

    // Trigger input (rising edge starts one "shot").
    input  logic              trigger_i,

    // Stream input (I,Q packed: I lower B, Q upper B).
    input  logic              din_valid_i,
    input  logic [2*B-1:0]    din_i,

    // BRAM Port-A (RMW)
    output wire               mem_we_o,     // write enable (1 cycle pulse)
    output wire  [N-1:0]      mem_addr_o,   // address (read and write)
    output wire  [4*B-1:0]    mem_di_o,     // write data {sum_q, sum_i}

    // Control registers (already synchronized to 'clk' domain).
    input  logic              START_REG,    // arm/clear
    input  logic [15:0]       AVG_NUMBER_REG, // number of averages (1 to 65536) 
    input  logic [N-1:0]      ADDR_REG,     // base address. start to save trace in BRAM from this address
    input  logic [31:0]       LEN_REG       // number of samples per shot
);

    //--------------------------------------------------------------------------
    // Local typedefs/constants
    //--------------------------------------------------------------------------
    localparam int unsigned WCH = 2 * B;  // stored width per channel
    localparam int unsigned WW  = 4 * B;  // total stored width {Q,I}

    typedef enum logic [2:0] {
        IDLE,           // idle state
        CLEAR,          // clear BRAM to 0
        WAIT_TRIG,      // wait for trigger rising edge
        RMW_READ,       // present read address; latch input sample
        RMW_WRITE,      // write back (prev + sample) to same address
        DONE_SHOT       // one shot done -> go WAIT_TRIG
    } state_t;

    //--------------------------------------------------------------------------
    // Registers
    //--------------------------------------------------------------------------
    state_t               state;

    // START / TRIGGER edge detection
    reg                   start_q, start_edge;
    reg                   trig_q,  trig_edge;

    // Effective LEN (use lower N bits; SW should ensure LEN <= 2**N)
    reg [N-1:0]           len_eff_r;

    // Base address latch (at START)
    reg [N-1:0]           base_addr_r;

    // Clear/write index and shot sample index
    reg [N-1:0]           clr_idx_r;

    // Pipe to hold sample across RMW (one-cycle)
    reg [B-1:0]           samp_buf1_i_r, samp_buf1_q_r;       // signed B-bit each
    reg [B-1:0]           samp_buf2_i_r, samp_buf2_q_r;       // signed B-bit each
    reg [B-1:0]           samp_buf3_i_r, samp_buf3_q_r;       // signed B-bit each
    reg [B-1:0]           samp_buf4_i_r, samp_buf4_q_r;       // signed B-bit each
    reg [B-1:0]           samp_buf5_i_r, samp_buf5_q_r;       // signed B-bit each
    reg [B-1:0]           samp_buf6_i_r, samp_buf6_q_r;       // signed B-bit each

    // Combinational addends from BRAM read (registered output)
    reg   signed [WCH-1:0] prev_i_s, prev_q_s;
    logic signed [WCH-1:0] samp_i_ext_s, samp_q_ext_s;
    logic signed [WCH-1:0] sum_i_s, sum_q_s;

    assign start_edge = (START_REG & ~start_q);
    assign trig_edge  = (trigger_i & ~trig_q);
    assign mem_we_o  = mem_we_o3;
    assign mem_addr_o = mem_addr_o3;
    assign mem_di_o  = mem_di_o1;
    
    //--------------------------------------------------------------------------
    // Dual-port RAM instance
    // A : Read
    // B : Write
    //--------------------------------------------------------------------------
    reg  [4*B-1:0]  buffer_din1;
    reg  [4*B-1:0]  buffer_din2;
    reg  [4*B-1:0]  buffer_din3;
    reg  [4*B-1:0]  buffer_din4;
    reg  [4*B-1:0]  buffer_din5;
    wire [4*B-1:0]  buffer_dout;
    reg  [N-1:0]    buffer_addr_r1;
    reg  [N-1:0]    buffer_addr_r2;
    reg  [N-1:0]    buffer_addr_w1;
    reg  [N-1:0]    buffer_addr_w2;
    reg  [N-1:0]    buffer_addr_w3;
    reg  [N-1:0]    buffer_addr_w4;
    reg  [N-1:0]    buffer_addr_w5;
    reg             buffer_wen1;
    reg             buffer_wen2;
    reg             buffer_wen3;
    reg             buffer_wen4;
    reg             buffer_wen5;

    reg signed [WCH-1:0] samp_i_ext_s1, samp_q_ext_s1;

    reg [15:0]      avg_number;

    reg             mem_we_o1;
    reg [N-1:0]     mem_addr_o1;
    reg [4*B-1:0]   mem_di_o1;

    reg             mem_we_o2;
    reg [N-1:0]     mem_addr_o2;
    reg [4*B-1:0]   mem_di_o2;

    reg             mem_we_o3;
    reg [N-1:0]     mem_addr_o3;
    reg [4*B-1:0]   mem_di_o3;

    bram_dp
    #(
		.N	(N	),
        .B 	(4*B)
    )
    buffer_i
	( 
		.clka	(clk			),
		.clkb	(clk            ),
		.ena    (1'b1			),
		.enb    (1'b1			),
		.wea    (1'b0           ),
		.web    (buffer_wen5    ),
		.addra  (buffer_addr_r2 ),
		.addrb  (buffer_addr_w5 ),
		.dia    ('0             ),
		.dib    (buffer_din2    ),
		.doa    (buffer_dout    ),
		.dob    (	            )
    );

    //--------------------------------------------------------------------------
    // Edge detectors
    //--------------------------------------------------------------------------
    always_ff @(posedge clk) begin
        if (!rstn) begin
            start_q <= 1'b0;
            trig_q  <= 1'b0;
        end
        else begin
            start_q <= START_REG;
            trig_q  <= trigger_i;
        end
    end

    //--------------------------------------------------------------------------
    // Latch base address and effective length at START
    //--------------------------------------------------------------------------
    always_ff @(posedge clk) begin
        if (!rstn) begin
            base_addr_r <= '0;
            len_eff_r   <= '0;
        end
        else if (start_edge) begin
            base_addr_r <= ADDR_REG;
            // if LEN_REG lower N bits are 0, treat as 1 to avoid underflow
            len_eff_r   <= (LEN_REG[N-1:0] == '0) ? {{N-1{1'b0}},1'b1} : LEN_REG[N-1:0];
        end
    end

    //--------------------------------------------------------------------------
    // Sign-extension and sum formation (combinational)
    //--------------------------------------------------------------------------
    // Extract previous sums from BRAM word (lower = I, upper = Q)
    always_comb begin
        // Sign-extend B-bit samples to 2*B
        samp_i_ext_s = $signed({{B{samp_buf4_i_r[B-1]}}, samp_buf4_i_r});
        samp_q_ext_s = $signed({{B{samp_buf4_q_r[B-1]}}, samp_buf4_q_r});

        // Add
        sum_i_s = prev_i_s + samp_i_ext_s1;
        sum_q_s = prev_q_s + samp_q_ext_s1;
    end

    //--------------------------------------------------------------------------
    // State machine
    //--------------------------------------------------------------------------
    always_ff @(posedge clk) begin
        if (!rstn) begin
            state             <= IDLE;
            clr_idx_r         <= '0;

            mem_we_o1          <= 1'b0;
            mem_addr_o1        <= '0;
            mem_di_o1          <= '0;

            mem_we_o2          <= 1'b0;
            mem_addr_o2        <= '0;
            mem_di_o2          <= '0;

            mem_we_o3          <= 1'b0;
            mem_addr_o3        <= '0;
            mem_di_o3          <= '0;
            // Also clear sample regs
            samp_buf1_i_r   <= '0;
            samp_buf1_q_r   <= '0;
            samp_buf2_i_r   <= '0;
            samp_buf2_q_r   <= '0;
            samp_buf3_i_r   <= '0;
            samp_buf3_q_r   <= '0;
            samp_buf4_i_r   <= '0;
            samp_buf4_q_r   <= '0;
            samp_buf5_i_r   <= '0;
            samp_buf5_q_r   <= '0;
            samp_buf6_i_r   <= '0;
            samp_buf6_q_r   <= '0;

            samp_i_ext_s1   <= '0;
            samp_q_ext_s1   <= '0;

            // BRAM signals
            buffer_addr_r1  <= '0;
            buffer_addr_r2  <= '0;
            buffer_addr_w1  <= '0;
            buffer_addr_w2  <= '0;
            buffer_addr_w3  <= '0;
            buffer_addr_w4  <= '0;
            buffer_addr_w5  <= '0;
            buffer_din1     <= '0;
            buffer_din2     <= '0;
            buffer_din3     <= '0;
            buffer_din4     <= '0;
            buffer_din5     <= '0;
            buffer_wen1     <= 1'b0;
            buffer_wen2     <= 1'b0;
            buffer_wen3     <= 1'b0;
            buffer_wen4     <= 1'b0;
            buffer_wen5     <= 1'b0;

            avg_number      <= '0;

            prev_i_s        <= '0;
            prev_q_s        <= '0;
        end
        else begin
            // Defaults (may be overridden per state)
            buffer_addr_r1  <= '0;
            buffer_addr_r2  <= buffer_addr_r1;

            buffer_addr_w1  <= '0;
            buffer_addr_w2  <= buffer_addr_w1;
            buffer_addr_w3  <= buffer_addr_w2;
            buffer_addr_w4  <= buffer_addr_w3;
            buffer_addr_w5  <= buffer_addr_w4;

            buffer_din1     <= '0;
            buffer_din2     <= buffer_din1;
            buffer_din3     <= buffer_din2;
            buffer_din4     <= buffer_din3;
            buffer_din5     <= buffer_din4;

            buffer_wen1     <= 1'b0;
            buffer_wen2     <= buffer_wen1;
            buffer_wen3     <= buffer_wen2;
            buffer_wen4     <= buffer_wen3;
            buffer_wen5     <= buffer_wen4;

            mem_di_o1       <= buffer_dout;
            mem_we_o1       <= 1'b0;

            mem_we_o2        <= mem_we_o1;
            mem_addr_o2      <= mem_addr_o1;
            mem_di_o2        <= mem_di_o1;

            mem_we_o3        <= mem_we_o2;
            mem_addr_o3      <= mem_addr_o2;
            mem_di_o3        <= mem_di_o2;

            samp_buf1_i_r   <= din_i[B-1:0];
            samp_buf1_q_r   <= din_i[2*B-1:B];
            samp_buf2_i_r   <= samp_buf1_i_r;
            samp_buf2_q_r   <= samp_buf1_q_r;
            samp_buf3_i_r   <= samp_buf2_i_r;
            samp_buf3_q_r   <= samp_buf2_q_r;
            samp_buf4_i_r   <= samp_buf3_i_r;
            samp_buf4_q_r   <= samp_buf3_q_r;
            samp_buf5_i_r   <= samp_buf4_i_r;
            samp_buf5_q_r   <= samp_buf4_q_r;
            samp_buf6_i_r   <= samp_buf5_i_r;
            samp_buf6_q_r   <= samp_buf5_q_r;

            samp_i_ext_s1   <= samp_i_ext_s;
            samp_q_ext_s1   <= samp_q_ext_s;

            prev_i_s        <= $signed(buffer_dout[WCH-1:0]);
            prev_q_s        <= $signed(buffer_dout[WW-1:WCH]);
            unique case (state)
                IDLE: begin
                    if (start_edge) begin
                        clr_idx_r       <= '0;
                        state           <= CLEAR;
                        buffer_addr_w1  <= '0;
                        buffer_wen1     <= 1'b1;
                    end
                end

                CLEAR: begin
                    // BRAM_DP instance do not have a reset input.
                    // So we clear the memory by writing zeros to all locations.
                    // Initialize BRAM for 0 ~ (2**N - 1) addresses.
                    avg_number          <= 0;
                    buffer_wen1         <= 1'b1;
                    buffer_addr_w1      <= buffer_addr_w1 + 1;
                    clr_idx_r           <= clr_idx_r + 1'b1;
                    if (clr_idx_r == {N{1'b1}}) begin
                        state           <= WAIT_TRIG;
                    end
                end

                WAIT_TRIG: begin
                    buffer_din1      <= {sum_q_s, sum_i_s};
                    if (trig_edge) begin
                        state           <= RMW_READ;
                        buffer_addr_r1  <= buffer_addr_r1 + 1;
                        buffer_wen1     <= 1'b1;
                        buffer_addr_w1  <= 0;
                    end
                end

                RMW_READ: begin
                    buffer_din1     <= {sum_q_s, sum_i_s};
                    buffer_addr_r1  <= buffer_addr_r1 + 1'b1;
                    buffer_addr_w1  <= buffer_addr_w1 + 1;
                    buffer_wen1     <= 1'b1;
                    
                    if (buffer_addr_w1 == (len_eff_r - 1'b1)) begin
                        state           <= RMW_WRITE;
                        buffer_addr_r1  <= '0;
                        buffer_addr_w1  <= '0;
                        buffer_wen1     <= 1'b0;
                    end
                end

                RMW_WRITE: begin
                    buffer_din1         <= {sum_q_s, sum_i_s};
                    if (avg_number == AVG_NUMBER_REG - 1) begin
                        mem_addr_o1     <= base_addr_r;
                        buffer_addr_r1  <= buffer_addr_r1 + 1;
                        mem_we_o1       <= 1'b1;
                        state           <= DONE_SHOT;
                    end
                    else begin
                        state           <= DONE_SHOT;
                    end
                end
                DONE_SHOT: begin
                    buffer_din1     <= {sum_q_s, sum_i_s};
                    if (avg_number == AVG_NUMBER_REG - 1) begin
                        mem_addr_o1  <= mem_addr_o1 + 1;
                        buffer_addr_r1 <= buffer_addr_r1 + 1;
                        mem_we_o1    <= 1'b1;
                        if (mem_addr_o1 == (base_addr_r + len_eff_r - 1)) begin
                            mem_addr_o1 <= '0;
                            buffer_addr_r1 <= '0;
                            state       <= IDLE;
                            avg_number  <= 0;
                        end
                    end
                    else begin
                        state           <= WAIT_TRIG;
                        avg_number      <= avg_number + 1;
                    end
                end

                default: begin
                    state <= IDLE;
                end
            endcase
        end
    end

endmodule