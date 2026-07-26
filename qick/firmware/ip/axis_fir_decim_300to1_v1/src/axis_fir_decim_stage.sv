// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps

import fir_decim_300to1_coeffs_pkg::*;

// One two-lane direct-form FIR decimation stage with a registered adder tree.
//
// Arithmetic:
//   - two signed 16-bit lanes,
//   - signed 18-bit Q1.17 coefficients,
//   - signed 48-bit accumulation,
//   - round half away from zero before shifting by COEF_FRAC_BITS,
//   - signed 16-bit saturation.
//
// Datapath behavior:
//   - the FIR dot product is launched for every accepted input sample,
//   - decim_count_r selects which completed FIR result is marked valid,
//   - decimation control does not drive the multiplier or adder datapath.
//
// AXIS behavior:
//   - trigger_align clears decimation phase and valid pipeline,
//   - input is always accepted when s_axis_tvalid is asserted,
//   - m_axis_tready is intentionally ignored,
//   - output valid/data pulses are generated continuously without backpressure.
module axis_fir_decim_stage #(
    parameter int STAGE_ID   = 0,
    parameter int DECIM      = 10,
    parameter int TAPS       = 95,
    parameter int DATA_WIDTH = 32,
    parameter int LANE_WIDTH = 16,
    parameter int ACC_WIDTH  = 48,
    parameter int OUT_WIDTH  = 16
)(
    input  wire                         aclk,
    input  wire                         aresetn,
    input  wire                         trigger_align,

    input  wire [DATA_WIDTH-1:0]        s_axis_tdata,
    input  wire                         s_axis_tvalid,
    output wire                         s_axis_tready,

    output logic [DATA_WIDTH-1:0]       m_axis_tdata,
    output logic                        m_axis_tvalid,
    input  wire                         m_axis_tready
);

    localparam int SUM_L1 = (TAPS   + 1) / 2;
    localparam int SUM_L2 = (SUM_L1 + 1) / 2;
    localparam int SUM_L3 = (SUM_L2 + 1) / 2;
    localparam int SUM_L4 = (SUM_L3 + 1) / 2;
    localparam int SUM_L5 = (SUM_L4 + 1) / 2;
    localparam int SUM_L6 = (SUM_L5 + 1) / 2;
    localparam int SUM_L7 = (SUM_L6 + 1) / 2;
    localparam int SUM_L8 = (SUM_L7 + 1) / 2;

    logic signed [LANE_WIDTH-1:0] lane0_hist [0:TAPS-2];
    logic signed [LANE_WIDTH-1:0] lane1_hist [0:TAPS-2];
    logic [$clog2(DECIM)-1:0] decim_count_r;

    wire input_fire = s_axis_tvalid;
    wire output_due = input_fire && (decim_count_r == DECIM-1);
    wire unused_ready = m_axis_tready;

    assign s_axis_tready = 1'b1;

    function automatic logic signed [OUT_WIDTH-1:0] round_saturate(input logic signed [ACC_WIDTH-1:0] acc);
        logic signed [ACC_WIDTH-1:0] round_offset;
        logic [ACC_WIDTH-1:0] rounded_mag;
        logic [ACC_WIDTH-1:0] acc_mag;
        logic signed [ACC_WIDTH-1:0] shifted;
        logic signed [ACC_WIDTH-1:0] max_value;
        logic signed [ACC_WIDTH-1:0] min_value;
        begin
            round_offset = ({{(ACC_WIDTH-1){1'b0}}, 1'b1} <<< (COEF_FRAC_BITS-1));
            if (acc >= 0) begin
                rounded_mag = acc[ACC_WIDTH-1:0] + round_offset[ACC_WIDTH-1:0];
                shifted = $signed(rounded_mag >> COEF_FRAC_BITS);
            end else begin
                acc_mag = $unsigned(-acc);
                rounded_mag = acc_mag + round_offset[ACC_WIDTH-1:0];
                shifted = -$signed(rounded_mag >> COEF_FRAC_BITS);
            end

            max_value = ({{(ACC_WIDTH-1){1'b0}}, 1'b1} <<< (OUT_WIDTH-1)) - 1;
            min_value = -({{(ACC_WIDTH-1){1'b0}}, 1'b1} <<< (OUT_WIDTH-1));

            if (shifted > max_value)
                round_saturate = {1'b0, {(OUT_WIDTH-1){1'b1}}};
            else if (shifted < min_value)
                round_saturate = {1'b1, {(OUT_WIDTH-1){1'b0}}};
            else
                round_saturate = shifted[OUT_WIDTH-1:0];
        end
    endfunction

    (* use_dsp = "yes" *) logic signed [ACC_WIDTH-1:0] prod0_r [0:TAPS-1];
    (* use_dsp = "yes" *) logic signed [ACC_WIDTH-1:0] prod1_r [0:TAPS-1];
    logic signed [ACC_WIDTH-1:0] sum0_l1 [0:SUM_L1-1];
    logic signed [ACC_WIDTH-1:0] sum1_l1 [0:SUM_L1-1];
    logic signed [ACC_WIDTH-1:0] sum0_l2 [0:SUM_L2-1];
    logic signed [ACC_WIDTH-1:0] sum1_l2 [0:SUM_L2-1];
    logic signed [ACC_WIDTH-1:0] sum0_l3 [0:SUM_L3-1];
    logic signed [ACC_WIDTH-1:0] sum1_l3 [0:SUM_L3-1];
    logic signed [ACC_WIDTH-1:0] sum0_l4 [0:SUM_L4-1];
    logic signed [ACC_WIDTH-1:0] sum1_l4 [0:SUM_L4-1];
    logic signed [ACC_WIDTH-1:0] sum0_l5 [0:SUM_L5-1];
    logic signed [ACC_WIDTH-1:0] sum1_l5 [0:SUM_L5-1];
    logic signed [ACC_WIDTH-1:0] sum0_l6 [0:SUM_L6-1];
    logic signed [ACC_WIDTH-1:0] sum1_l6 [0:SUM_L6-1];
    logic signed [ACC_WIDTH-1:0] sum0_l7 [0:SUM_L7-1];
    logic signed [ACC_WIDTH-1:0] sum1_l7 [0:SUM_L7-1];
    logic signed [ACC_WIDTH-1:0] sum0_l8 [0:SUM_L8-1];
    logic signed [ACC_WIDTH-1:0] sum1_l8 [0:SUM_L8-1];
    logic [8:0] valid_pipe_r;

    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            decim_count_r <= '0;
            m_axis_tdata  <= '0;
            m_axis_tvalid <= 1'b0;
            valid_pipe_r  <= '0;
            for (int k = 0; k < TAPS-1; k++) begin
                lane0_hist[k] <= '0;
                lane1_hist[k] <= '0;
            end
            // The product/sum pipeline intentionally has no reset. valid_pipe_r
            // suppresses its contents until deterministic post-reset data reaches
            // the output, avoiding a high-fanout reset into hundreds of DSP regs.
        end else if (trigger_align) begin
            decim_count_r <= '0;
            m_axis_tdata  <= '0;
            m_axis_tvalid <= 1'b0;
            valid_pipe_r  <= '0;
        end else begin
            valid_pipe_r <= {valid_pipe_r[7:0], output_due};
            m_axis_tvalid <= valid_pipe_r[8];

            // Compute the full-rate FIR result for every accepted sample.
            // output_due only qualifies the corresponding result through
            // valid_pipe_r; it must not become a DSP operand/zero-select mux.
            if (input_fire) begin
                for (int k = 0; k < TAPS; k++) begin
                    if (k == 0) begin
                        prod0_r[k] <= $signed(s_axis_tdata[LANE_WIDTH-1:0]) * $signed(fir_coeff(STAGE_ID, k));
                        prod1_r[k] <= $signed(s_axis_tdata[2*LANE_WIDTH-1:LANE_WIDTH]) * $signed(fir_coeff(STAGE_ID, k));
                    end else begin
                        prod0_r[k] <= $signed(lane0_hist[k-1]) * $signed(fir_coeff(STAGE_ID, k));
                        prod1_r[k] <= $signed(lane1_hist[k-1]) * $signed(fir_coeff(STAGE_ID, k));
                    end
                end
            end

            for (int k = 0; k < SUM_L1; k++) begin
                if ((2*k+1) < TAPS) begin
                    sum0_l1[k] <= prod0_r[2*k] + prod0_r[2*k+1];
                    sum1_l1[k] <= prod1_r[2*k] + prod1_r[2*k+1];
                end else begin
                    sum0_l1[k] <= prod0_r[2*k];
                    sum1_l1[k] <= prod1_r[2*k];
                end
            end
            for (int k = 0; k < SUM_L2; k++) begin
                if ((2*k+1) < SUM_L1) begin
                    sum0_l2[k] <= sum0_l1[2*k] + sum0_l1[2*k+1];
                    sum1_l2[k] <= sum1_l1[2*k] + sum1_l1[2*k+1];
                end else begin
                    sum0_l2[k] <= sum0_l1[2*k];
                    sum1_l2[k] <= sum1_l1[2*k];
                end
            end
            for (int k = 0; k < SUM_L3; k++) begin
                if ((2*k+1) < SUM_L2) begin
                    sum0_l3[k] <= sum0_l2[2*k] + sum0_l2[2*k+1];
                    sum1_l3[k] <= sum1_l2[2*k] + sum1_l2[2*k+1];
                end else begin
                    sum0_l3[k] <= sum0_l2[2*k];
                    sum1_l3[k] <= sum1_l2[2*k];
                end
            end
            for (int k = 0; k < SUM_L4; k++) begin
                if ((2*k+1) < SUM_L3) begin
                    sum0_l4[k] <= sum0_l3[2*k] + sum0_l3[2*k+1];
                    sum1_l4[k] <= sum1_l3[2*k] + sum1_l3[2*k+1];
                end else begin
                    sum0_l4[k] <= sum0_l3[2*k];
                    sum1_l4[k] <= sum1_l3[2*k];
                end
            end
            for (int k = 0; k < SUM_L5; k++) begin
                if ((2*k+1) < SUM_L4) begin
                    sum0_l5[k] <= sum0_l4[2*k] + sum0_l4[2*k+1];
                    sum1_l5[k] <= sum1_l4[2*k] + sum1_l4[2*k+1];
                end else begin
                    sum0_l5[k] <= sum0_l4[2*k];
                    sum1_l5[k] <= sum1_l4[2*k];
                end
            end
            for (int k = 0; k < SUM_L6; k++) begin
                if ((2*k+1) < SUM_L5) begin
                    sum0_l6[k] <= sum0_l5[2*k] + sum0_l5[2*k+1];
                    sum1_l6[k] <= sum1_l5[2*k] + sum1_l5[2*k+1];
                end else begin
                    sum0_l6[k] <= sum0_l5[2*k];
                    sum1_l6[k] <= sum1_l5[2*k];
                end
            end
            for (int k = 0; k < SUM_L7; k++) begin
                if ((2*k+1) < SUM_L6) begin
                    sum0_l7[k] <= sum0_l6[2*k] + sum0_l6[2*k+1];
                    sum1_l7[k] <= sum1_l6[2*k] + sum1_l6[2*k+1];
                end else begin
                    sum0_l7[k] <= sum0_l6[2*k];
                    sum1_l7[k] <= sum1_l6[2*k];
                end
            end
            for (int k = 0; k < SUM_L8; k++) begin
                if ((2*k+1) < SUM_L7) begin
                    sum0_l8[k] <= sum0_l7[2*k] + sum0_l7[2*k+1];
                    sum1_l8[k] <= sum1_l7[2*k] + sum1_l7[2*k+1];
                end else begin
                    sum0_l8[k] <= sum0_l7[2*k];
                    sum1_l8[k] <= sum1_l7[2*k];
                end
            end

            if (input_fire) begin
                for (int k = TAPS-2; k > 0; k--) begin
                    lane0_hist[k] <= lane0_hist[k-1];
                    lane1_hist[k] <= lane1_hist[k-1];
                end
                lane0_hist[0] <= s_axis_tdata[LANE_WIDTH-1:0];
                    lane1_hist[0] <= s_axis_tdata[2*LANE_WIDTH-1:LANE_WIDTH];

                if (output_due) begin
                    decim_count_r <= '0;
                end else begin
                    decim_count_r <= decim_count_r + 1'b1;
                end
            end

            if (valid_pipe_r[8]) begin
                m_axis_tdata <= {
                    round_saturate(sum1_l8[0]),
                    round_saturate(sum0_l8[0])
                };
            end
        end
    end

endmodule
