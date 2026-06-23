// Trace accumulation block.
//
// One trigger captures one trace repetition. For each stored output point,
// AVG_ACCUM_LEN_REG selects the number of raw input samples M to accumulate.
// AVG_TRACE_REPS_REG selects the number of trace repetitions R to accumulate.
// Register value 0 maps to R=1; M=0 and M=1 both map to M=1.
//
// No division, shift, or reciprocal multiply is applied. The final stored
// trace word is packed as {signext(Q_accum[3*B-1:0]) to 4*B,
// signext(I_accum[3*B-1:0]) to 4*B}. M and R are 16-bit registers, so for
// B=16 the 48-bit signed accumulators cover the worst-case M*R*sample sum.
module trace_avg #(
    parameter int unsigned N = 10,
    parameter int unsigned B = 16
) (
    input  logic             rstn,
    input  logic             clk,

    input  logic             trigger_i,

    input  logic             din_valid_i,
    input  logic [2*B-1:0]   din_i,

    output logic             mem_we_o,
    output logic [N-1:0]     mem_addr_o,
    output logic [8*B-1:0]   mem_di_o,

    input  logic             START_REG,
    input  logic [15:0]      AVG_TRACE_REPS_REG,
    input  logic [N-1:0]     ADDR_REG,
    input  logic [31:0]      LEN_REG,
    input  logic [15:0]      AVG_ACCUM_LEN_REG
);

    localparam int unsigned ACC_WIDTH  = 3 * B;
    localparam int unsigned LANE_WIDTH = 4 * B;
    localparam int unsigned OUT_WIDTH  = 8 * B;
    localparam int unsigned WW         = 2 * ACC_WIDTH;
    localparam int unsigned COUNT_W    = 16;

    typedef enum logic [2:0] {
        IDLE,
        CLEAR,
        WAIT_TRIG,
        COLLECT,
        FLUSH_GROUP,
        OUTPUT_PREP,
        OUTPUT_TRACE,
        OUTPUT_FLUSH
    } state_t;

    state_t state;

    logic start_q;
    logic trig_q;
    wire  start_edge = START_REG & ~start_q;
    wire  trig_edge  = trigger_i & ~trig_q;

    logic [N-1:0]       base_addr_r;
    logic [N-1:0]       len_eff_r;
    logic [N-1:0]       clr_idx_r;
    logic [N-1:0]       output_idx_r;
    logic [COUNT_W-1:0] accum_len_eff_r;
    logic [COUNT_W-1:0] trace_reps_eff_r;
    logic [COUNT_W-1:0] sample_cnt_r;
    logic [COUNT_W-1:0] rep_cnt_r;

    logic signed [ACC_WIDTH-1:0] group_i_r;
    logic signed [ACC_WIDTH-1:0] group_q_r;
    logic signed [ACC_WIDTH-1:0] next_group_i;
    logic signed [ACC_WIDTH-1:0] next_group_q;
    logic                        group_done;
    logic                        last_output;
    logic                        last_rep;

    logic                        pending_valid_r;
    logic [N-1:0]                pending_addr_r;
    logic signed [ACC_WIDTH-1:0] pending_i_r;
    logic signed [ACC_WIDTH-1:0] pending_q_r;

    logic                        bram_web;
    logic [N-1:0]                bram_addra;
    logic [N-1:0]                bram_addrb;
    logic [WW-1:0]               bram_dib;
    wire  [WW-1:0]               bram_doa;

    logic                        output_pipe_valid_r;
    logic [N-1:0]                output_addr_pipe_r;

    wire signed [ACC_WIDTH-1:0] din_i_ext = {{(ACC_WIDTH-B){din_i[B-1]}}, din_i[B-1:0]};
    wire signed [ACC_WIDTH-1:0] din_q_ext = {{(ACC_WIDTH-B){din_i[2*B-1]}}, din_i[2*B-1:B]};

    wire signed [ACC_WIDTH-1:0] prev_i_s = $signed(bram_doa[ACC_WIDTH-1:0]);
    wire signed [ACC_WIDTH-1:0] prev_q_s = $signed(bram_doa[WW-1:ACC_WIDTH]);
    wire signed [ACC_WIDTH-1:0] out_i_s  = $signed(bram_doa[ACC_WIDTH-1:0]);
    wire signed [ACC_WIDTH-1:0] out_q_s  = $signed(bram_doa[WW-1:ACC_WIDTH]);
    wire signed [ACC_WIDTH-1:0] sum_i_s  = prev_i_s + pending_i_r;
    wire signed [ACC_WIDTH-1:0] sum_q_s  = prev_q_s + pending_q_r;

    function automatic [OUT_WIDTH-1:0] pack_iq_accum(
        input logic signed [ACC_WIDTH-1:0] i_accum,
        input logic signed [ACC_WIDTH-1:0] q_accum
    );
        begin
            pack_iq_accum = {
                {(LANE_WIDTH-ACC_WIDTH){q_accum[ACC_WIDTH-1]}}, q_accum,
                {(LANE_WIDTH-ACC_WIDTH){i_accum[ACC_WIDTH-1]}}, i_accum
            };
        end
    endfunction

    function automatic [COUNT_W-1:0] effective_accum_len(input [15:0] reg_value);
        begin
            if (reg_value <= 16'd1)
                effective_accum_len = {{(COUNT_W-1){1'b0}}, 1'b1};
            else
                effective_accum_len = reg_value[COUNT_W-1:0];
        end
    endfunction

    function automatic [COUNT_W-1:0] effective_trace_reps(input [15:0] reg_value);
        begin
            if (reg_value == 16'd0)
                effective_trace_reps = {{(COUNT_W-1){1'b0}}, 1'b1};
            else
                effective_trace_reps = reg_value[COUNT_W-1:0];
        end
    endfunction

    always_comb begin
        next_group_i = group_i_r + din_i_ext;
        next_group_q = group_q_r + din_q_ext;
        group_done   = din_valid_i && (sample_cnt_r == (accum_len_eff_r - 1'b1));
        last_output  = (output_idx_r == (len_eff_r - 1'b1));
        last_rep     = (rep_cnt_r == (trace_reps_eff_r - 1'b1));
    end

    // Port A reads either the current accumulation bin or the final output bin.
    always_comb begin
        bram_addra = '0;
        if (state == COLLECT)
            bram_addra = output_idx_r;
        else if (state == OUTPUT_TRACE)
            bram_addra = output_idx_r;
    end

    bram_dp #(
        .N (N),
        .B (WW)
    ) buffer_i (
        .clka  (clk),
        .clkb  (clk),
        .ena   (1'b1),
        .enb   (1'b1),
        .wea   (1'b0),
        .web   (bram_web),
        .addra (bram_addra),
        .addrb (bram_addrb),
        .dia   ({WW{1'b0}}),
        .dib   (bram_dib),
        .doa   (bram_doa),
        .dob   ()
    );

    always_ff @(posedge clk) begin
        if (!rstn) begin
            start_q             <= 1'b0;
            trig_q              <= 1'b0;
            state               <= IDLE;
            base_addr_r         <= '0;
            len_eff_r           <= {{(N-1){1'b0}}, 1'b1};
            clr_idx_r           <= '0;
            output_idx_r        <= '0;
            accum_len_eff_r     <= {{(COUNT_W-1){1'b0}}, 1'b1};
            trace_reps_eff_r    <= {{(COUNT_W-1){1'b0}}, 1'b1};
            sample_cnt_r        <= '0;
            rep_cnt_r           <= '0;
            group_i_r           <= '0;
            group_q_r           <= '0;
            pending_valid_r     <= 1'b0;
            pending_addr_r      <= '0;
            pending_i_r         <= '0;
            pending_q_r         <= '0;
            bram_web            <= 1'b0;
            bram_addrb          <= '0;
            bram_dib            <= '0;
            output_pipe_valid_r <= 1'b0;
            output_addr_pipe_r  <= '0;
            mem_we_o            <= 1'b0;
            mem_addr_o          <= '0;
            mem_di_o            <= '0;
        end
        else begin
            start_q <= START_REG;
            trig_q  <= trigger_i;

            bram_web   <= 1'b0;
            bram_addrb <= '0;
            bram_dib   <= '0;
            mem_we_o   <= 1'b0;
            mem_addr_o <= '0;
            mem_di_o   <= '0;

            if (pending_valid_r) begin
                bram_web   <= 1'b1;
                bram_addrb <= pending_addr_r;
                bram_dib   <= {sum_q_s, sum_i_s};
            end

            unique case (state)
                IDLE: begin
                    pending_valid_r     <= 1'b0;
                    output_pipe_valid_r <= 1'b0;
                    if (start_edge) begin
                        base_addr_r      <= ADDR_REG;
                        len_eff_r        <= (LEN_REG[N-1:0] == '0) ? {{(N-1){1'b0}}, 1'b1} : LEN_REG[N-1:0];
                        accum_len_eff_r  <= effective_accum_len(AVG_ACCUM_LEN_REG);
                        trace_reps_eff_r <= effective_trace_reps(AVG_TRACE_REPS_REG);
                        clr_idx_r        <= '0;
                        rep_cnt_r        <= '0;
                        bram_web         <= 1'b1;
                        bram_addrb       <= '0;
                        bram_dib         <= '0;
                        state            <= CLEAR;
                    end
                end

                CLEAR: begin
                    pending_valid_r <= 1'b0;
                    bram_web        <= 1'b1;
                    bram_addrb      <= clr_idx_r;
                    bram_dib        <= '0;
                    if (clr_idx_r == {N{1'b1}}) begin
                        clr_idx_r <= '0;
                        state     <= WAIT_TRIG;
                    end
                    else begin
                        clr_idx_r <= clr_idx_r + 1'b1;
                    end
                end

                WAIT_TRIG: begin
                    pending_valid_r <= 1'b0;
                    if (!START_REG) begin
                        state <= IDLE;
                    end
                    else if (trig_edge) begin
                        output_idx_r <= '0;
                        sample_cnt_r <= '0;
                        group_i_r    <= '0;
                        group_q_r    <= '0;
                        state        <= COLLECT;
                    end
                end

                COLLECT: begin
                    if (!START_REG) begin
                        pending_valid_r <= 1'b0;
                        state           <= IDLE;
                    end
                    else begin
                        pending_valid_r <= 1'b0;

                        if (din_valid_i) begin
                            if (group_done) begin
                                pending_valid_r <= 1'b1;
                                pending_addr_r  <= output_idx_r;
                                pending_i_r     <= next_group_i;
                                pending_q_r     <= next_group_q;
                                group_i_r       <= '0;
                                group_q_r       <= '0;
                                sample_cnt_r    <= '0;

                                if (last_output) begin
                                    output_idx_r <= '0;
                                    state        <= FLUSH_GROUP;
                                end
                                else begin
                                    output_idx_r <= output_idx_r + 1'b1;
                                end
                            end
                            else begin
                                group_i_r    <= next_group_i;
                                group_q_r    <= next_group_q;
                                sample_cnt_r <= sample_cnt_r + 1'b1;
                            end
                        end
                    end
                end

                FLUSH_GROUP: begin
                    pending_valid_r <= 1'b0;
                    if (last_rep) begin
                        output_idx_r        <= '0;
                        output_pipe_valid_r <= 1'b0;
                        state               <= OUTPUT_PREP;
                    end
                    else begin
                        rep_cnt_r <= rep_cnt_r + 1'b1;
                        state     <= WAIT_TRIG;
                    end
                end

                OUTPUT_PREP: begin
                    output_idx_r        <= '0;
                    output_pipe_valid_r <= 1'b0;
                    state               <= OUTPUT_TRACE;
                end

                OUTPUT_TRACE: begin
                    if (output_pipe_valid_r) begin
                        mem_we_o   <= 1'b1;
                        mem_addr_o <= output_addr_pipe_r;
                        mem_di_o   <= pack_iq_accum(out_i_s, out_q_s);
                    end

                    output_pipe_valid_r <= 1'b1;
                    output_addr_pipe_r  <= base_addr_r + output_idx_r;
                    if (output_idx_r == (len_eff_r - 1'b1)) begin
                        output_idx_r <= '0;
                        state        <= OUTPUT_FLUSH;
                    end
                    else begin
                        output_idx_r <= output_idx_r + 1'b1;
                    end
                end

                OUTPUT_FLUSH: begin
                    if (output_pipe_valid_r) begin
                        mem_we_o   <= 1'b1;
                        mem_addr_o <= output_addr_pipe_r;
                        mem_di_o   <= pack_iq_accum(out_i_s, out_q_s);
                    end
                    output_pipe_valid_r <= 1'b0;
                    rep_cnt_r           <= '0;
                    state               <= IDLE;
                end

                default: begin
                    state <= IDLE;
                end
            endcase
        end
    end

endmodule
