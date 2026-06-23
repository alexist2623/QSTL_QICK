// AVG accumulation block.
//
// Input samples are packed as {Q[B-1:0], I[B-1:0]} with signed I/Q.
// AVG_ACCUM_LEN_REG[15:0] selects the number of raw input samples M to
// accumulate per stored AVG point. M=0 and M=1 both mean one raw sample.
// AVG_LEN_REG is the number of stored output points; the raw input span for
// one capture is AVG_LEN_REG * effective_M samples.
//
// No division or shift is applied. Each stored word is packed as:
//   {signext(Q_accum[3*B-1:0]) to 4*B,
//    signext(I_accum[3*B-1:0]) to 4*B}.
module avg #(
    parameter N = 10,
    parameter B = 16
) (
    // Reset and clock.
    input  wire             rstn,
    input  wire             clk,

    // Trigger input.
    input  wire             trigger_i,

    // Data input.
    input  wire             din_valid_i,
    input  wire [2*B-1:0]   din_i,

    // Memory interface.
    output wire             mem_we_o,
    output wire [N-1:0]     mem_addr_o,
    output wire [8*B-1:0]   mem_di_o,

    // Registers.
    input  wire             START_REG,
    input  wire [N-1:0]     ADDR_REG,
    input  wire [31:0]      LEN_REG,
    input  wire             PHOTON_MODE_REG,
    input  wire [B-1:0]     H_THRSH_REG,
    input  wire [B-1:0]     L_THRSH_REG,
    input  wire [15:0]      AVG_ACCUM_LEN_REG
);

localparam int unsigned ACC_WIDTH = 3 * B;
localparam int unsigned LANE_WIDTH = 4 * B;
localparam int unsigned OUT_WIDTH = 8 * B;
localparam int unsigned COUNT_WIDTH = 16;

typedef enum logic [2:0] {
    INIT_ST,
    START_ST,
    TRIGGER_ST,
    COLLECT_ST,
    WAIT_TRIGGER_ST
} state_t;

(* fsm_encoding = "one_hot" *) state_t state;

logic start_state;
logic trigger_state;
logic collect_state;

logic [N-1:0]         base_addr_r;
logic [N-1:0]         addr_r;
logic [N-1:0]         len_eff_r;
logic [N-1:0]         output_cnt_r;
logic [COUNT_WIDTH-1:0] accum_len_eff_r;
logic [COUNT_WIDTH-1:0] sample_cnt_r;

logic                 photon_mode_r;
logic signed [B-1:0]  h_thrsh_r;
logic signed [B-1:0]  l_thrsh_r;
logic                 high_state;
logic                 high_state_reg;

wire signed [B-1:0] din_ii = $signed(din_i[B-1:0]);
wire signed [B-1:0] din_qq = $signed(din_i[2*B-1:B]);
wire signed [ACC_WIDTH-1:0] din_i_ext = {{(ACC_WIDTH-B){din_i[B-1]}}, din_i[B-1:0]};
wire signed [ACC_WIDTH-1:0] din_q_ext = {{(ACC_WIDTH-B){din_i[2*B-1]}}, din_i[2*B-1:B]};

logic signed [ACC_WIDTH-1:0] acc_i_r;
logic signed [ACC_WIDTH-1:0] acc_q_r;
logic signed [ACC_WIDTH-1:0] next_acc_i;
logic signed [ACC_WIDTH-1:0] next_acc_q;
logic [ACC_WIDTH-1:0]        photon_acc_r;
logic [ACC_WIDTH-1:0]        next_photon_acc;
logic [OUT_WIDTH-1:0]        write_data_comb;
logic                        group_done;
logic                        last_output;

function automatic [COUNT_WIDTH-1:0] effective_accum_len(input [15:0] reg_value);
    begin
        if (reg_value <= 16'd1)
            effective_accum_len = {{(COUNT_WIDTH-1){1'b0}}, 1'b1};
        else
            effective_accum_len = reg_value[COUNT_WIDTH-1:0];
    end
endfunction

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

function automatic [OUT_WIDTH-1:0] pack_photon_count(
    input logic [ACC_WIDTH-1:0] count
);
    begin
        pack_photon_count = {
            {LANE_WIDTH{1'b0}},
            {(LANE_WIDTH-ACC_WIDTH){1'b0}}, count
        };
    end
endfunction

always_comb begin
    next_acc_i = acc_i_r + din_i_ext;
    next_acc_q = acc_q_r + din_q_ext;
    next_photon_acc = photon_acc_r;
    if (high_state == 1'b1 && high_state_reg == 1'b0)
        next_photon_acc = photon_acc_r + {{(ACC_WIDTH-1){1'b0}}, 1'b1};

    group_done = din_valid_i && (sample_cnt_r == (accum_len_eff_r - 1'b1));
    last_output = (output_cnt_r == (len_eff_r - 1'b1));

    if (!photon_mode_r)
        write_data_comb = pack_iq_accum(next_acc_i, next_acc_q);
    else
        write_data_comb = pack_photon_count(next_photon_acc);
end

always_ff @(posedge clk) begin
    if (!rstn) begin
        state           <= INIT_ST;
        base_addr_r     <= '0;
        addr_r          <= '0;
        len_eff_r       <= {{(N-1){1'b0}}, 1'b1};
        output_cnt_r    <= '0;
        accum_len_eff_r <= {{(COUNT_WIDTH-1){1'b0}}, 1'b1};
        sample_cnt_r    <= '0;
        photon_mode_r   <= 1'b0;
        h_thrsh_r       <= '0;
        l_thrsh_r       <= '0;
        high_state      <= 1'b0;
        high_state_reg  <= 1'b0;
        acc_i_r         <= '0;
        acc_q_r         <= '0;
        photon_acc_r    <= '0;
    end
    else begin
        unique case (state)
            INIT_ST: begin
                state <= START_ST;
            end

            START_ST: begin
                if (START_REG)
                    state <= TRIGGER_ST;
            end

            TRIGGER_ST: begin
                if (!START_REG)
                    state <= START_ST;
                else if (trigger_i)
                    state <= COLLECT_ST;
            end

            COLLECT_ST: begin
                if (!START_REG) begin
                    state <= START_ST;
                end
                else if (group_done && last_output) begin
                    state <= WAIT_TRIGGER_ST;
                end
            end

            WAIT_TRIGGER_ST: begin
                if (!START_REG)
                    state <= START_ST;
                else if (!trigger_i)
                    state <= TRIGGER_ST;
            end

            default: begin
                state <= START_ST;
            end
        endcase

        if (start_state) begin
            base_addr_r     <= ADDR_REG;
            addr_r          <= ADDR_REG;
            len_eff_r       <= (LEN_REG[N-1:0] == '0) ? {{(N-1){1'b0}}, 1'b1} : LEN_REG[N-1:0];
            accum_len_eff_r <= effective_accum_len(AVG_ACCUM_LEN_REG);
            photon_mode_r   <= PHOTON_MODE_REG;
            h_thrsh_r       <= H_THRSH_REG;
            l_thrsh_r       <= L_THRSH_REG;
        end

        if (trigger_state) begin
            addr_r         <= base_addr_r;
            output_cnt_r   <= '0;
            sample_cnt_r   <= '0;
            acc_i_r        <= '0;
            acc_q_r        <= '0;
            photon_acc_r   <= '0;
            high_state     <= 1'b0;
            high_state_reg <= 1'b0;
        end
        else if (collect_state && din_valid_i) begin
            if (!photon_mode_r) begin
                acc_i_r <= next_acc_i;
                acc_q_r <= next_acc_q;
            end
            else begin
                photon_acc_r <= next_photon_acc;
            end

            if (group_done)
                sample_cnt_r <= '0;
            else
                sample_cnt_r <= sample_cnt_r + 1'b1;
        end

        if (collect_state && din_valid_i) begin
            high_state_reg <= high_state;
            if (din_ii > h_thrsh_r)
                high_state <= 1'b1;
            else if (din_ii < l_thrsh_r)
                high_state <= 1'b0;
        end

        if (group_done) begin
            acc_i_r      <= '0;
            acc_q_r      <= '0;
            photon_acc_r <= '0;
            if (!last_output) begin
                output_cnt_r <= output_cnt_r + 1'b1;
                addr_r       <= addr_r + 1'b1;
            end
        end
    end
end

always_comb begin
    start_state     = 1'b0;
    trigger_state   = 1'b0;
    collect_state   = 1'b0;

    unique case (state)
        START_ST:     start_state     = 1'b1;
        TRIGGER_ST:   trigger_state   = 1'b1;
        COLLECT_ST:   collect_state   = 1'b1;
        default: ;
    endcase
end

assign mem_we_o   = collect_state && group_done;
assign mem_addr_o = addr_r;
assign mem_di_o   = write_data_comb;

endmodule
