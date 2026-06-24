// Trace accumulation block for axis_avg_buffer v1.3.
//
// M = effective(AVG_ACCUM_LEN_REG[23:0]), where 0 and 1 both mean 1.
// R = effective(AVG_TRACE_REPS_REG[23:0]), where 0 means 1.
//
// AVG_LEN_REG is the number of stored output points. Each trigger consumes
// AVG_LEN_REG * M raw input samples. After R triggers the stored output is:
//   Y[m] = sum over r=0..R-1 and j=0..M-1 of x_r[m*M + j]
//
// No division, right shift, reciprocal multiply, or pairwise averaging is
// applied. Output packing is {Q_accum[4*B-1:0], I_accum[4*B-1:0]}.

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
    input  logic [23:0]      AVG_TRACE_REPS_REG,
    input  logic [N-1:0]     ADDR_REG,
    input  logic [31:0]      LEN_REG,
    input  logic [23:0]      AVG_ACCUM_LEN_REG
);

    localparam int unsigned ACC_CH_WIDTH   = 4 * B;
    localparam int unsigned ACC_WORD_WIDTH = 8 * B;
    localparam int unsigned COUNT_W        = 24;
    localparam int unsigned FLUSH_CYCLES   = ((N > 10) ? (N - 10) : 0) + 4;

    localparam logic [1:0] OP_CLEAR  = 2'd0;
    localparam logic [1:0] OP_UPDATE = 2'd1;
    localparam logic [1:0] OP_READ   = 2'd2;

    typedef enum logic [3:0] {
        IDLE,
        CLEAR,
        CLEAR_FLUSH,
        WAIT_TRIG,
        COLLECT,
        UPDATE_FLUSH,
        OUTPUT_READ,
        OUTPUT_DRAIN
    } state_t;

    state_t state;

    logic start_q;
    logic trig_q;
    wire  start_edge = START_REG & ~start_q;
    wire  trig_edge  = trigger_i & ~trig_q;

    logic [N-1:0]       base_addr_r;
    logic [N-1:0]       len_eff_r;
    logic [N-1:0]       clear_idx_r;
    logic [N-1:0]       output_idx_r;
    logic [N-1:0]       read_issue_idx_r;
    logic [N-1:0]       read_return_cnt_r;
    logic [COUNT_W-1:0] accum_len_eff_r;
    logic [COUNT_W-1:0] trace_reps_eff_r;
    logic [COUNT_W-1:0] sample_cnt_r;
    logic [COUNT_W-1:0] rep_cnt_r;
    logic [$clog2(FLUSH_CYCLES+1)-1:0] flush_cnt_r;

    logic signed [ACC_CH_WIDTH-1:0] group_i_r;
    logic signed [ACC_CH_WIDTH-1:0] group_q_r;
    logic signed [ACC_CH_WIDTH-1:0] next_group_i;
    logic signed [ACC_CH_WIDTH-1:0] next_group_q;
    logic                           group_done;
    logic                           last_output;
    logic                           last_rep;

    logic                           accum_valid;
    logic [1:0]                     accum_op;
    logic [N-1:0]                   accum_addr;
    logic [ACC_WORD_WIDTH-1:0]      accum_delta;
    wire                            accum_read_valid;
    wire [N-1:0]                    accum_read_addr;
    wire [ACC_WORD_WIDTH-1:0]       accum_read_data;

    wire signed [B-1:0] din_i_s = $signed(din_i[B-1:0]);
    wire signed [B-1:0] din_q_s = $signed(din_i[2*B-1:B]);
    wire signed [ACC_CH_WIDTH-1:0] din_i_ext =
        {{(ACC_CH_WIDTH-B){din_i_s[B-1]}}, din_i_s};
    wire signed [ACC_CH_WIDTH-1:0] din_q_ext =
        {{(ACC_CH_WIDTH-B){din_q_s[B-1]}}, din_q_s};

    function automatic [COUNT_W-1:0] effective_accum_len(input [23:0] reg_value);
        begin
            if (reg_value <= 24'd1)
                effective_accum_len = {{(COUNT_W-1){1'b0}}, 1'b1};
            else
                effective_accum_len = reg_value[COUNT_W-1:0];
        end
    endfunction

    function automatic [COUNT_W-1:0] effective_trace_reps(input [23:0] reg_value);
        begin
            if (reg_value == 24'd0)
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

        accum_valid = 1'b0;
        accum_op    = OP_CLEAR;
        accum_addr  = '0;
        accum_delta = '0;

        unique case (state)
            CLEAR: begin
                accum_valid = 1'b1;
                accum_op    = OP_CLEAR;
                accum_addr  = base_addr_r + clear_idx_r;
            end

            COLLECT: begin
                if (group_done) begin
                    accum_valid = 1'b1;
                    accum_op    = OP_UPDATE;
                    accum_addr  = base_addr_r + output_idx_r;
                    accum_delta = {next_group_q, next_group_i};
                end
            end

            OUTPUT_READ: begin
                accum_valid = 1'b1;
                accum_op    = OP_READ;
                accum_addr  = base_addr_r + read_issue_idx_r;
            end

            default: ;
        endcase
    end

    ramb36e2_accum_mem #(
        .N              (N),
        .B              (B),
        .ACC_CH_WIDTH   (ACC_CH_WIDTH),
        .ACC_WORD_WIDTH (ACC_WORD_WIDTH)
    ) accum_mem_i (
        .clk          (clk),
        .rstn         (rstn),
        .valid_i      (accum_valid),
        .op_i         (accum_op),
        .addr_i       (accum_addr),
        .delta_i      (accum_delta),
        .read_valid_o (accum_read_valid),
        .read_addr_o  (accum_read_addr),
        .read_data_o  (accum_read_data)
    );

    always_ff @(posedge clk) begin
        if (!rstn) begin
            start_q           <= 1'b0;
            trig_q            <= 1'b0;
            state             <= IDLE;
            base_addr_r       <= '0;
            len_eff_r         <= {{(N-1){1'b0}}, 1'b1};
            clear_idx_r       <= '0;
            output_idx_r      <= '0;
            read_issue_idx_r  <= '0;
            read_return_cnt_r <= '0;
            accum_len_eff_r   <= {{(COUNT_W-1){1'b0}}, 1'b1};
            trace_reps_eff_r  <= {{(COUNT_W-1){1'b0}}, 1'b1};
            sample_cnt_r      <= '0;
            rep_cnt_r         <= '0;
            flush_cnt_r       <= '0;
            group_i_r         <= '0;
            group_q_r         <= '0;
            mem_we_o          <= 1'b0;
            mem_addr_o        <= '0;
            mem_di_o          <= '0;
        end
        else begin
            start_q  <= START_REG;
            trig_q   <= trigger_i;
            mem_we_o <= 1'b0;

            if (accum_read_valid) begin
                mem_we_o   <= 1'b1;
                mem_addr_o <= accum_read_addr;
                mem_di_o   <= accum_read_data;
            end

            unique case (state)
                IDLE: begin
                    if (start_edge) begin
                        base_addr_r      <= ADDR_REG;
                        len_eff_r        <= (LEN_REG[N-1:0] == '0) ?
                                            {{(N-1){1'b0}}, 1'b1} : LEN_REG[N-1:0];
                        accum_len_eff_r  <= effective_accum_len(AVG_ACCUM_LEN_REG);
                        trace_reps_eff_r <= effective_trace_reps(AVG_TRACE_REPS_REG);
                        clear_idx_r      <= '0;
                        rep_cnt_r        <= '0;
                        state            <= CLEAR;
                    end
                end

                CLEAR: begin
                    if (!START_REG) begin
                        state <= IDLE;
                    end
                    else if (clear_idx_r == (len_eff_r - 1'b1)) begin
                        clear_idx_r <= '0;
                        flush_cnt_r <= FLUSH_CYCLES;
                        state       <= CLEAR_FLUSH;
                    end
                    else begin
                        clear_idx_r <= clear_idx_r + 1'b1;
                    end
                end

                CLEAR_FLUSH: begin
                    if (!START_REG) begin
                        state <= IDLE;
                    end
                    else if (flush_cnt_r == '0) begin
                        state <= WAIT_TRIG;
                    end
                    else begin
                        flush_cnt_r <= flush_cnt_r - 1'b1;
                    end
                end

                WAIT_TRIG: begin
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
                        state <= IDLE;
                    end
                    else if (din_valid_i) begin
                        if (group_done) begin
                            group_i_r    <= '0;
                            group_q_r    <= '0;
                            sample_cnt_r <= '0;

                            if (last_output) begin
                                output_idx_r <= '0;
                                flush_cnt_r  <= FLUSH_CYCLES;
                                state        <= UPDATE_FLUSH;
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

                UPDATE_FLUSH: begin
                    if (!START_REG) begin
                        state <= IDLE;
                    end
                    else if (flush_cnt_r != '0) begin
                        flush_cnt_r <= flush_cnt_r - 1'b1;
                    end
                    else if (last_rep) begin
                        read_issue_idx_r  <= '0;
                        read_return_cnt_r <= '0;
                        state             <= OUTPUT_READ;
                    end
                    else begin
                        rep_cnt_r <= rep_cnt_r + 1'b1;
                        state     <= WAIT_TRIG;
                    end
                end

                OUTPUT_READ: begin
                    if (!START_REG) begin
                        state <= IDLE;
                    end
                    else if (read_issue_idx_r == (len_eff_r - 1'b1)) begin
                        read_issue_idx_r <= '0;
                        state            <= OUTPUT_DRAIN;
                    end
                    else begin
                        read_issue_idx_r <= read_issue_idx_r + 1'b1;
                    end

                    if (accum_read_valid)
                        read_return_cnt_r <= read_return_cnt_r + 1'b1;
                end

                OUTPUT_DRAIN: begin
                    if (accum_read_valid)
                        read_return_cnt_r <= read_return_cnt_r + 1'b1;

                    if (!START_REG) begin
                        state <= IDLE;
                    end
                    else if (accum_read_valid &&
                             (read_return_cnt_r == (len_eff_r - 1'b1))) begin
                        rep_cnt_r <= '0;
                        state     <= IDLE;
                    end
                end

                default: begin
                    state <= IDLE;
                end
            endcase
        end
    end

endmodule
