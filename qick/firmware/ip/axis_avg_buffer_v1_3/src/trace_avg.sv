module trace_avg #(
    parameter int unsigned N = 10,   // memory depth = 2**N
    parameter int unsigned B = 16,   // per-channel width
    parameter int unsigned MAX_AVG_DECIM_LOG2 = 6
) (
    // Reset and clock.
    input  logic              rstn,
    input  logic              clk,

    // Trigger input (rising edge starts one shot).
    input  logic              trigger_i,

    // Stream input (I,Q packed: I lower B, Q upper B).
    input  logic              din_valid_i,
    input  logic [2*B-1:0]    din_i,

    // Outer AVG BRAM Port-A write interface.
    output logic              mem_we_o,
    output logic [N-1:0]      mem_addr_o,
    output logic [4*B-1:0]    mem_di_o,

    // Control registers (already synchronized to clk domain).
    input  logic              START_REG,
    input  logic [15:0]       AVG_NUMBER_REG,
    input  logic [N-1:0]      ADDR_REG,
    input  logic [31:0]       LEN_REG,
    input  logic [3:0]        AVG_DECIM_LOG2_REG
);

    localparam int unsigned WCH = 2 * B;
    localparam int unsigned WW  = 4 * B;

    typedef enum logic [2:0] {
        IDLE,
        CLEAR,
        WAIT_TRIG,
        COLLECT,
        FLUSH_SHOT,
        OUTPUT_PREP,
        OUTPUT_TRACE,
        OUTPUT_FLUSH
    } state_t;

    state_t state;

    logic start_q;
    logic trig_q;
    wire  start_edge = START_REG & ~start_q;
    wire  trig_edge  = trigger_i & ~trig_q;

    logic [N-1:0] base_addr_r;
    logic [N-1:0] len_eff_r;
    logic [N-1:0] clr_idx_r;
    logic [N-1:0] sample_idx_r;
    logic [N-1:0] output_idx_r;
    logic [15:0]  shot_count_r;
    logic [3:0]   decim_log2_r;

    logic              bram_web;
    logic [N-1:0]      bram_addra;
    logic [N-1:0]      bram_addrb;
    logic [WW-1:0]     bram_dib;
    wire  [WW-1:0]     bram_doa;

    logic              collect_pipe_valid_r;
    logic [N-1:0]      collect_addr_pipe_r;
    logic signed [WCH-1:0] collect_i_pipe_r;
    logic signed [WCH-1:0] collect_q_pipe_r;

    logic              output_pipe_valid_r;
    logic [N-1:0]      output_addr_pipe_r;

    wire [3:0]         effective_decim_log2;
    wire               decim_enabled = (decim_log2_r != 4'd0);
    wire               decim_valid;
    wire [2*B-1:0]     decim_din;
    wire               sample_valid = (decim_enabled == 1'b1) ? decim_valid : din_valid_i;
    wire [2*B-1:0]     sample_din   = (decim_enabled == 1'b1) ? decim_din   : din_i;

    wire signed [WCH-1:0] prev_i_s = $signed(bram_doa[WCH-1:0]);
    wire signed [WCH-1:0] prev_q_s = $signed(bram_doa[WW-1:WCH]);
    wire signed [WCH-1:0] sum_i_s  = prev_i_s + collect_i_pipe_r;
    wire signed [WCH-1:0] sum_q_s  = prev_q_s + collect_q_pipe_r;

    function automatic [3:0] clamp_decim_log2(input [3:0] decim_log2);
        if (decim_log2 > MAX_AVG_DECIM_LOG2)
            clamp_decim_log2 = MAX_AVG_DECIM_LOG2;
        else
            clamp_decim_log2 = decim_log2;
    endfunction

    assign effective_decim_log2 = clamp_decim_log2(AVG_DECIM_LOG2_REG);

    // Port-A is read-only. During collection it reads the current accumulated
    // trace bin; during output it streams the accumulated trace to AVG memory.
    always_comb begin
        bram_addra = '0;
        if (state == COLLECT)
            bram_addra = sample_idx_r;
        else if (state == OUTPUT_TRACE)
            bram_addra = output_idx_r;
    end

    bram_dp
    #(
        .N (N),
        .B (WW)
    )
    buffer_i
    (
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

    avg_decimator_iq
    #(
        .B (B),
        .MAX_AVG_DECIM_LOG2 (MAX_AVG_DECIM_LOG2)
    )
    avg_decimator_i
    (
        .rstn           (rstn),
        .clk            (clk),
        .clear_i        ((state != COLLECT) || (decim_enabled == 1'b0)),
        .decim_log2_i   (decim_log2_r),
        .din_valid_i    (din_valid_i),
        .din_i          (din_i),
        .dout_valid_o   (decim_valid),
        .dout_i         (decim_din)
    );

    always_ff @(posedge clk) begin
        if (!rstn) begin
            start_q              <= 1'b0;
            trig_q               <= 1'b0;
            state                <= IDLE;
            base_addr_r          <= '0;
            len_eff_r            <= '0;
            clr_idx_r            <= '0;
            sample_idx_r         <= '0;
            output_idx_r         <= '0;
            shot_count_r         <= '0;
            decim_log2_r         <= '0;
            collect_pipe_valid_r <= 1'b0;
            collect_addr_pipe_r  <= '0;
            collect_i_pipe_r     <= '0;
            collect_q_pipe_r     <= '0;
            output_pipe_valid_r  <= 1'b0;
            output_addr_pipe_r   <= '0;
            bram_web             <= 1'b0;
            bram_addrb           <= '0;
            bram_dib             <= '0;
            mem_we_o             <= 1'b0;
            mem_addr_o           <= '0;
            mem_di_o             <= '0;
        end
        else begin
            start_q  <= START_REG;
            trig_q   <= trigger_i;

            bram_web <= 1'b0;
            bram_addrb <= '0;
            bram_dib <= '0;
            mem_we_o <= 1'b0;
            mem_addr_o <= '0;
            mem_di_o <= '0;

            unique case (state)
                IDLE: begin
                    collect_pipe_valid_r <= 1'b0;
                    output_pipe_valid_r  <= 1'b0;
                    if (start_edge) begin
                        base_addr_r  <= ADDR_REG;
                        len_eff_r    <= (LEN_REG[N-1:0] == '0) ? {{N-1{1'b0}}, 1'b1} : LEN_REG[N-1:0];
                        decim_log2_r <= effective_decim_log2;
                        clr_idx_r    <= '0;
                        shot_count_r <= '0;
                        bram_web     <= 1'b1;
                        bram_addrb   <= '0;
                        bram_dib     <= '0;
                        state        <= CLEAR;
                    end
                end

                CLEAR: begin
                    bram_web   <= 1'b1;
                    bram_addrb <= clr_idx_r;
                    bram_dib   <= '0;
                    if (clr_idx_r == {N{1'b1}}) begin
                        clr_idx_r <= '0;
                        state     <= WAIT_TRIG;
                    end
                    else begin
                        clr_idx_r <= clr_idx_r + 1'b1;
                    end
                end

                WAIT_TRIG: begin
                    collect_pipe_valid_r <= 1'b0;
                    if (START_REG == 1'b0) begin
                        state <= IDLE;
                    end
                    else if (trig_edge) begin
                        sample_idx_r <= '0;
                        state        <= COLLECT;
                    end
                end

                COLLECT: begin
                    if (START_REG == 1'b0) begin
                        collect_pipe_valid_r <= 1'b0;
                        state <= IDLE;
                    end
                    else begin
                        if (collect_pipe_valid_r) begin
                            bram_web   <= 1'b1;
                            bram_addrb <= collect_addr_pipe_r;
                            bram_dib   <= {sum_q_s, sum_i_s};
                        end

                        collect_pipe_valid_r <= 1'b0;
                        if (sample_valid) begin
                            collect_pipe_valid_r <= 1'b1;
                            collect_addr_pipe_r  <= sample_idx_r;
                            collect_i_pipe_r     <= $signed({{B{sample_din[B-1]}}, sample_din[B-1:0]});
                            collect_q_pipe_r     <= $signed({{B{sample_din[2*B-1]}}, sample_din[2*B-1:B]});

                            if (sample_idx_r == (len_eff_r - 1'b1)) begin
                                sample_idx_r <= '0;
                                state        <= FLUSH_SHOT;
                            end
                            else begin
                                sample_idx_r <= sample_idx_r + 1'b1;
                            end
                        end
                    end
                end

                FLUSH_SHOT: begin
                    if (collect_pipe_valid_r) begin
                        bram_web   <= 1'b1;
                        bram_addrb <= collect_addr_pipe_r;
                        bram_dib   <= {sum_q_s, sum_i_s};
                    end
                    collect_pipe_valid_r <= 1'b0;

                    if (shot_count_r == (AVG_NUMBER_REG - 1'b1)) begin
                        output_idx_r        <= '0;
                        output_pipe_valid_r <= 1'b0;
                        state               <= OUTPUT_PREP;
                    end
                    else begin
                        shot_count_r <= shot_count_r + 1'b1;
                        state        <= WAIT_TRIG;
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
                        mem_di_o   <= bram_doa;
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
                        mem_di_o   <= bram_doa;
                    end
                    output_pipe_valid_r <= 1'b0;
                    shot_count_r        <= '0;
                    state               <= IDLE;
                end

                default: begin
                    state <= IDLE;
                end
            endcase
        end
    end

endmodule
