// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps

import notch_decim_1m_to50k_coeffs_pkg::*;

// Time-multiplexed two-channel SOS cascade with explicit DSP48E2 arithmetic.
//
// The history/coefficient MUX is registered in SELECT_ST before multiplication.
// Each signed 32x32 multiply is built from pipelined DSP48E2 partial products.
// APPLY_PREP_ST prepares five accumulation candidates without adding:
//   0: product, 1: accumulator+product, 2: accumulator+product,
//   3: accumulator-product, 4: accumulator-product.
// All five candidates are evaluated in parallel.  APPLY_SELECT_ST uses only the
// delayed operation tag to select the registered result.  The 68-bit adders
// propagate carry over two DSP48E2 stages (47 low bits, then 21 high bits).
module axis_sos_iq_engine #(
    parameter int N_SECTIONS      = 40,
    parameter int DATA_WIDTH      = 32,
    parameter int LANE_WIDTH      = 16,
    parameter int SIGNAL_WIDTH    = 32,
    parameter int SIGNAL_FRAC     = 16,
    parameter int ACC_WIDTH       = 68
)(
    input  wire                       aclk,
    input  wire                       aresetn,

    input  wire [DATA_WIDTH-1:0]      s_axis_tdata,
    input  wire                       s_axis_tvalid,
    output wire                       s_axis_tready,

    output logic [DATA_WIDTH-1:0]     m_axis_tdata,
    output logic                      m_axis_tvalid
);

    localparam int SECTION_WIDTH = (N_SECTIONS <= 1) ? 1 : $clog2(N_SECTIONS);
    localparam int N_OPERATIONS = 5;

    typedef enum logic [3:0] {
        IDLE_ST,
        SELECT_ST,
        MUL_LAUNCH_ST,
        MUL_WAIT_ST,
        APPLY_PREP_ST,
        APPLY_LAUNCH_ST,
        APPLY_WAIT_ST,
        APPLY_SELECT_ST,
        FINAL_ABS_ST,
        FINAL_ROUND_ADD_ST,
        FINAL_SHIFT_ST,
        FINAL_SIGN_ST,
        FINAL_SAT_ST,
        FINAL_LANE_ST,
        FINAL_COMMIT_ST
    } state_t;

    state_t state_r;
    logic [SECTION_WIDTH-1:0] section_r;
    logic [2:0] operation_r;
    logic [2:0] selected_operation_r;
    logic [2:0] apply_operation_r;

    logic signed [SIGNAL_WIDTH-1:0] current_i_r;
    logic signed [SIGNAL_WIDTH-1:0] current_q_r;

    logic signed [SIGNAL_WIDTH-1:0] x1_i_r [0:N_SECTIONS-1];
    logic signed [SIGNAL_WIDTH-1:0] x2_i_r [0:N_SECTIONS-1];
    logic signed [SIGNAL_WIDTH-1:0] y1_i_r [0:N_SECTIONS-1];
    logic signed [SIGNAL_WIDTH-1:0] y2_i_r [0:N_SECTIONS-1];
    logic signed [SIGNAL_WIDTH-1:0] x1_q_r [0:N_SECTIONS-1];
    logic signed [SIGNAL_WIDTH-1:0] x2_q_r [0:N_SECTIONS-1];
    logic signed [SIGNAL_WIDTH-1:0] y1_q_r [0:N_SECTIONS-1];
    logic signed [SIGNAL_WIDTH-1:0] y2_q_r [0:N_SECTIONS-1];

    logic signed [SIGNAL_WIDTH-1:0] mux_operand_i;
    logic signed [SIGNAL_WIDTH-1:0] mux_operand_q;
    logic signed [SOS_COEFF_WIDTH-1:0] mux_coefficient;
    logic signed [SIGNAL_WIDTH-1:0] operand_i_r;
    logic signed [SIGNAL_WIDTH-1:0] operand_q_r;
    logic signed [SOS_COEFF_WIDTH-1:0] coefficient_r;

    logic signed [ACC_WIDTH-1:0] product_i_r;
    logic signed [ACC_WIDTH-1:0] product_q_r;
    logic signed [ACC_WIDTH-1:0] accumulator_i_r;
    logic signed [ACC_WIDTH-1:0] accumulator_q_r;

    logic [ACC_WIDTH-1:0] candidate_a_i_r [0:N_OPERATIONS-1];
    logic [ACC_WIDTH-1:0] candidate_b_i_r [0:N_OPERATIONS-1];
    logic                 candidate_carry_i_r [0:N_OPERATIONS-1];
    logic [ACC_WIDTH-1:0] candidate_a_q_r [0:N_OPERATIONS-1];
    logic [ACC_WIDTH-1:0] candidate_b_q_r [0:N_OPERATIONS-1];
    logic                 candidate_carry_q_r [0:N_OPERATIONS-1];
    wire  [ACC_WIDTH-1:0] candidate_sum_i [0:N_OPERATIONS-1];
    wire  [ACC_WIDTH-1:0] candidate_sum_q [0:N_OPERATIONS-1];
    wire                  candidate_valid_i [0:N_OPERATIONS-1];
    wire                  candidate_valid_q [0:N_OPERATIONS-1];

    logic                          round_negative_i_r;
    logic                          round_negative_q_r;
    logic [ACC_WIDTH-1:0]          magnitude_i_r;
    logic [ACC_WIDTH-1:0]          magnitude_q_r;
    logic [ACC_WIDTH-1:0]          biased_magnitude_i_r;
    logic [ACC_WIDTH-1:0]          biased_magnitude_q_r;
    logic [ACC_WIDTH-1:0]          shifted_magnitude_i_r;
    logic [ACC_WIDTH-1:0]          shifted_magnitude_q_r;
    logic signed [ACC_WIDTH-1:0]   restored_i_r;
    logic signed [ACC_WIDTH-1:0]   restored_q_r;
    logic signed [SIGNAL_WIDTH-1:0] rounded_i_r;
    logic signed [SIGNAL_WIDTH-1:0] rounded_q_r;
    logic signed [LANE_WIDTH-1:0] lane_i_r;
    logic signed [LANE_WIDTH-1:0] lane_q_r;

    wire mul_launch = (state_r == MUL_LAUNCH_ST);
    wire apply_launch = (state_r == APPLY_LAUNCH_ST);
    wire mul_valid_i;
    wire mul_valid_q;
    wire signed [ACC_WIDTH-1:0] mul_product_i;
    wire signed [ACC_WIDTH-1:0] mul_product_q;

    localparam logic [ACC_WIDTH-1:0] COEFF_ROUND_BIAS =
        {{(ACC_WIDTH-1){1'b0}}, 1'b1} << (SOS_COEFF_FRAC_BITS-1);
    localparam logic signed [ACC_WIDTH-1:0] SIGNAL_MAX_EXT =
        $signed({{(ACC_WIDTH-SIGNAL_WIDTH){1'b0}}, 1'b0, {(SIGNAL_WIDTH-1){1'b1}}});
    localparam logic signed [ACC_WIDTH-1:0] SIGNAL_MIN_EXT =
        $signed({{(ACC_WIDTH-SIGNAL_WIDTH){1'b1}}, 1'b1, {(SIGNAL_WIDTH-1){1'b0}}});

    wire unused_parameter_check =
        (DATA_WIDTH != 2*LANE_WIDTH) ||
        (SIGNAL_WIDTH != 32) ||
        (SOS_COEFF_WIDTH != 32) ||
        (ACC_WIDTH != 68);

    assign s_axis_tready = (state_r == IDLE_ST);

    // MUX output is never consumed by arithmetic in this cycle.  SELECT_ST
    // registers all selected data and metadata before MUL_LAUNCH_ST.
    always_comb begin
        case (operation_r)
            3'd0: begin mux_operand_i = current_i_r;       mux_operand_q = current_q_r;       end
            3'd1: begin mux_operand_i = x1_i_r[section_r]; mux_operand_q = x1_q_r[section_r]; end
            3'd2: begin mux_operand_i = x2_i_r[section_r]; mux_operand_q = x2_q_r[section_r]; end
            3'd3: begin mux_operand_i = y1_i_r[section_r]; mux_operand_q = y1_q_r[section_r]; end
            default: begin mux_operand_i = y2_i_r[section_r]; mux_operand_q = y2_q_r[section_r]; end
        endcase
        mux_coefficient = notch_coeff(section_r, operation_r);
    end

    (* keep_hierarchy = "yes", DONT_TOUCH = "true" *)
    dsp48e2_mul32x32_pipe multiplier_i_i (
        .clk(aclk),
        .rstn(aresetn),
        .valid_i(mul_launch),
        .a_i(operand_i_r),
        .b_i(coefficient_r),
        .valid_o(mul_valid_i),
        .product_o(mul_product_i)
    );

    (* keep_hierarchy = "yes", DONT_TOUCH = "true" *)
    dsp48e2_mul32x32_pipe multiplier_q_i (
        .clk(aclk),
        .rstn(aresetn),
        .valid_i(mul_launch),
        .a_i(operand_q_r),
        .b_i(coefficient_r),
        .valid_o(mul_valid_q),
        .product_o(mul_product_q)
    );

    generate
        for (genvar candidate = 0; candidate < N_OPERATIONS; candidate++) begin : g_candidates
            (* keep_hierarchy = "yes", DONT_TOUCH = "true" *)
            dsp48e2_add68_chunked_pipe accumulator_candidate_i_i (
                .clk(aclk),
                .rstn(aresetn),
                .valid_i(apply_launch),
                .a_i(candidate_a_i_r[candidate]),
                .b_i(candidate_b_i_r[candidate]),
                .carry_i(candidate_carry_i_r[candidate]),
                .valid_o(candidate_valid_i[candidate]),
                .sum_o(candidate_sum_i[candidate])
            );

            (* keep_hierarchy = "yes", DONT_TOUCH = "true" *)
            dsp48e2_add68_chunked_pipe accumulator_candidate_q_i (
                .clk(aclk),
                .rstn(aresetn),
                .valid_i(apply_launch),
                .a_i(candidate_a_q_r[candidate]),
                .b_i(candidate_b_q_r[candidate]),
                .carry_i(candidate_carry_q_r[candidate]),
                .valid_o(candidate_valid_q[candidate]),
                .sum_o(candidate_sum_q[candidate])
            );
        end
    endgenerate

    function automatic logic signed [LANE_WIDTH-1:0] q_to_lane(
        input logic signed [SIGNAL_WIDTH-1:0] value
    );
        logic [SIGNAL_WIDTH-1:0] magnitude;
        logic [SIGNAL_WIDTH-1:0] rounded_magnitude;
        logic signed [SIGNAL_WIDTH-1:0] shifted;
        logic signed [SIGNAL_WIDTH-1:0] maximum;
        logic signed [SIGNAL_WIDTH-1:0] minimum;
        begin
            magnitude = (value < 0) ? $unsigned(-value) : $unsigned(value);
            rounded_magnitude = magnitude + ({{(SIGNAL_WIDTH-1){1'b0}}, 1'b1} <<< (SIGNAL_FRAC-1));
            shifted = $signed(rounded_magnitude >> SIGNAL_FRAC);
            if (value < 0)
                shifted = -shifted;

            maximum = ({{(SIGNAL_WIDTH-1){1'b0}}, 1'b1} <<< (LANE_WIDTH-1)) - 1;
            minimum = -({{(SIGNAL_WIDTH-1){1'b0}}, 1'b1} <<< (LANE_WIDTH-1));
            if (shifted > maximum)
                q_to_lane = {1'b0, {(LANE_WIDTH-1){1'b1}}};
            else if (shifted < minimum)
                q_to_lane = {1'b1, {(LANE_WIDTH-1){1'b0}}};
            else
                q_to_lane = shifted[LANE_WIDTH-1:0];
        end
    endfunction

    always_ff @(posedge aclk) begin : sos_engine_proc
        if (!aresetn) begin
            state_r               <= IDLE_ST;
            section_r             <= '0;
            operation_r           <= '0;
            selected_operation_r  <= '0;
            apply_operation_r     <= '0;
            current_i_r           <= '0;
            current_q_r           <= '0;
            operand_i_r           <= '0;
            operand_q_r           <= '0;
            coefficient_r         <= '0;
            product_i_r           <= '0;
            product_q_r           <= '0;
            accumulator_i_r       <= '0;
            accumulator_q_r       <= '0;
            round_negative_i_r    <= 1'b0;
            round_negative_q_r    <= 1'b0;
            magnitude_i_r         <= '0;
            magnitude_q_r         <= '0;
            biased_magnitude_i_r  <= '0;
            biased_magnitude_q_r  <= '0;
            shifted_magnitude_i_r <= '0;
            shifted_magnitude_q_r <= '0;
            restored_i_r          <= '0;
            restored_q_r          <= '0;
            rounded_i_r           <= '0;
            rounded_q_r           <= '0;
            lane_i_r              <= '0;
            lane_q_r              <= '0;
            m_axis_tdata          <= '0;
            m_axis_tvalid         <= 1'b0;
            for (int section = 0; section < N_SECTIONS; section++) begin
                x1_i_r[section] <= '0;
                x2_i_r[section] <= '0;
                y1_i_r[section] <= '0;
                y2_i_r[section] <= '0;
                x1_q_r[section] <= '0;
                x2_q_r[section] <= '0;
                y1_q_r[section] <= '0;
                y2_q_r[section] <= '0;
            end
            for (int candidate = 0; candidate < N_OPERATIONS; candidate++) begin
                candidate_a_i_r[candidate] <= '0;
                candidate_b_i_r[candidate] <= '0;
                candidate_carry_i_r[candidate] <= 1'b0;
                candidate_a_q_r[candidate] <= '0;
                candidate_b_q_r[candidate] <= '0;
                candidate_carry_q_r[candidate] <= 1'b0;
            end
        end else begin
            m_axis_tvalid <= 1'b0;

            case (state_r)
                IDLE_ST: begin
                    if (s_axis_tvalid) begin
                        current_i_r <= $signed({
                            {(SIGNAL_WIDTH-LANE_WIDTH){s_axis_tdata[LANE_WIDTH-1]}},
                            s_axis_tdata[LANE_WIDTH-1:0]
                        }) <<< SIGNAL_FRAC;
                        current_q_r <= $signed({
                            {(SIGNAL_WIDTH-LANE_WIDTH){s_axis_tdata[2*LANE_WIDTH-1]}},
                            s_axis_tdata[2*LANE_WIDTH-1:LANE_WIDTH]
                        }) <<< SIGNAL_FRAC;
                        section_r   <= '0;
                        operation_r <= '0;
                        state_r     <= SELECT_ST;
                    end
                end

                SELECT_ST: begin
                    operand_i_r          <= mux_operand_i;
                    operand_q_r          <= mux_operand_q;
                    coefficient_r        <= mux_coefficient;
                    selected_operation_r <= operation_r;
                    state_r              <= MUL_LAUNCH_ST;
                end

                MUL_LAUNCH_ST: begin
                    state_r <= MUL_WAIT_ST;
                end

                MUL_WAIT_ST: begin
                    if (mul_valid_i && mul_valid_q) begin
                        product_i_r <= mul_product_i;
                        product_q_r <= mul_product_q;
                        state_r     <= APPLY_PREP_ST;
                    end
                end

                APPLY_PREP_ST: begin
                    // Five physically independent candidates are prepared here.
                    // No addition or subtraction is performed in this MUX stage.
                    candidate_a_i_r[0] <= '0;
                    candidate_b_i_r[0] <= product_i_r;
                    candidate_carry_i_r[0] <= 1'b0;
                    candidate_a_q_r[0] <= '0;
                    candidate_b_q_r[0] <= product_q_r;
                    candidate_carry_q_r[0] <= 1'b0;

                    candidate_a_i_r[1] <= accumulator_i_r;
                    candidate_b_i_r[1] <= product_i_r;
                    candidate_carry_i_r[1] <= 1'b0;
                    candidate_a_q_r[1] <= accumulator_q_r;
                    candidate_b_q_r[1] <= product_q_r;
                    candidate_carry_q_r[1] <= 1'b0;

                    candidate_a_i_r[2] <= accumulator_i_r;
                    candidate_b_i_r[2] <= product_i_r;
                    candidate_carry_i_r[2] <= 1'b0;
                    candidate_a_q_r[2] <= accumulator_q_r;
                    candidate_b_q_r[2] <= product_q_r;
                    candidate_carry_q_r[2] <= 1'b0;

                    candidate_a_i_r[3] <= accumulator_i_r;
                    candidate_b_i_r[3] <= ~product_i_r;
                    candidate_carry_i_r[3] <= 1'b1;
                    candidate_a_q_r[3] <= accumulator_q_r;
                    candidate_b_q_r[3] <= ~product_q_r;
                    candidate_carry_q_r[3] <= 1'b1;

                    candidate_a_i_r[4] <= accumulator_i_r;
                    candidate_b_i_r[4] <= ~product_i_r;
                    candidate_carry_i_r[4] <= 1'b1;
                    candidate_a_q_r[4] <= accumulator_q_r;
                    candidate_b_q_r[4] <= ~product_q_r;
                    candidate_carry_q_r[4] <= 1'b1;

                    apply_operation_r <= selected_operation_r;
                    state_r           <= APPLY_LAUNCH_ST;
                end

                APPLY_LAUNCH_ST: begin
                    state_r <= APPLY_WAIT_ST;
                end

                APPLY_WAIT_ST: begin
                    if (candidate_valid_i[0] && candidate_valid_q[0])
                        state_r <= APPLY_SELECT_ST;
                end

                APPLY_SELECT_ST: begin
                    // Selection happens only after all five registered adders.
                    accumulator_i_r <= $signed(candidate_sum_i[apply_operation_r]);
                    accumulator_q_r <= $signed(candidate_sum_q[apply_operation_r]);
                    if (apply_operation_r == 3'd4) begin
                        state_r <= FINAL_ABS_ST;
                    end else begin
                        operation_r <= apply_operation_r + 1'b1;
                        state_r     <= SELECT_ST;
                    end
                end

                FINAL_ABS_ST: begin
                    // Stage 1: register sign and absolute magnitude. No rounding
                    // addition, scaling shift, or saturation is done here.
                    round_negative_i_r <= accumulator_i_r[ACC_WIDTH-1];
                    round_negative_q_r <= accumulator_q_r[ACC_WIDTH-1];
                    magnitude_i_r <= accumulator_i_r[ACC_WIDTH-1]
                        ? $unsigned(-accumulator_i_r) : $unsigned(accumulator_i_r);
                    magnitude_q_r <= accumulator_q_r[ACC_WIDTH-1]
                        ? $unsigned(-accumulator_q_r) : $unsigned(accumulator_q_r);
                    state_r <= FINAL_ROUND_ADD_ST;
                end

                FINAL_ROUND_ADD_ST: begin
                    // Stage 2: round-to-nearest, ties away from zero.
                    biased_magnitude_i_r <= magnitude_i_r + COEFF_ROUND_BIAS;
                    biased_magnitude_q_r <= magnitude_q_r + COEFF_ROUND_BIAS;
                    state_r <= FINAL_SHIFT_ST;
                end

                FINAL_SHIFT_ST: begin
                    // Stage 3: remove the Q2.30 coefficient fractional bits.
                    shifted_magnitude_i_r <= biased_magnitude_i_r >> SOS_COEFF_FRAC_BITS;
                    shifted_magnitude_q_r <= biased_magnitude_q_r >> SOS_COEFF_FRAC_BITS;
                    state_r <= FINAL_SIGN_ST;
                end

                FINAL_SIGN_ST: begin
                    // Stage 4: restore the sign after unsigned magnitude rounding.
                    restored_i_r <= round_negative_i_r
                        ? -$signed(shifted_magnitude_i_r) : $signed(shifted_magnitude_i_r);
                    restored_q_r <= round_negative_q_r
                        ? -$signed(shifted_magnitude_q_r) : $signed(shifted_magnitude_q_r);
                    state_r <= FINAL_SAT_ST;
                end

                FINAL_SAT_ST: begin
                    // Stage 5: signed 68-to-32-bit saturation and result register.
                    if (restored_i_r > SIGNAL_MAX_EXT)
                        rounded_i_r <= {1'b0, {(SIGNAL_WIDTH-1){1'b1}}};
                    else if (restored_i_r < SIGNAL_MIN_EXT)
                        rounded_i_r <= {1'b1, {(SIGNAL_WIDTH-1){1'b0}}};
                    else
                        rounded_i_r <= restored_i_r[SIGNAL_WIDTH-1:0];

                    if (restored_q_r > SIGNAL_MAX_EXT)
                        rounded_q_r <= {1'b0, {(SIGNAL_WIDTH-1){1'b1}}};
                    else if (restored_q_r < SIGNAL_MIN_EXT)
                        rounded_q_r <= {1'b1, {(SIGNAL_WIDTH-1){1'b0}}};
                    else
                        rounded_q_r <= restored_q_r[SIGNAL_WIDTH-1:0];
                    state_r <= FINAL_LANE_ST;
                end

                FINAL_LANE_ST: begin
                    lane_i_r <= q_to_lane(rounded_i_r);
                    lane_q_r <= q_to_lane(rounded_q_r);
                    state_r  <= FINAL_COMMIT_ST;
                end

                FINAL_COMMIT_ST: begin
                    x2_i_r[section_r] <= x1_i_r[section_r];
                    x1_i_r[section_r] <= current_i_r;
                    y2_i_r[section_r] <= y1_i_r[section_r];
                    y1_i_r[section_r] <= rounded_i_r;
                    x2_q_r[section_r] <= x1_q_r[section_r];
                    x1_q_r[section_r] <= current_q_r;
                    y2_q_r[section_r] <= y1_q_r[section_r];
                    y1_q_r[section_r] <= rounded_q_r;

                    if (section_r == N_SECTIONS-1) begin
                        m_axis_tdata  <= {lane_q_r, lane_i_r};
                        m_axis_tvalid <= 1'b1;
                        state_r       <= IDLE_ST;
                    end else begin
                        current_i_r <= rounded_i_r;
                        current_q_r <= rounded_q_r;
                        section_r   <= section_r + 1'b1;
                        operation_r <= '0;
                        state_r     <= SELECT_ST;
                    end
                end

                default: state_r <= IDLE_ST;
            endcase
        end
    end

endmodule
