// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps
import fir_decim_300to1_v2_coeffs_pkg::*;

// Exact two-lane FIR. There is no coefficient-scale shift, rounding or
// saturation at this stage's output. The stage-specific output widths are
// proven against the actual coefficient L1 norms in the accompanying model.
// Wide products use a signed upper chunk and an unsigned 26-bit lower chunk;
// each partial multiply fits one DSP48E2 27x18 multiplier. Registered product
// recombination and eight registered adder levels isolate wide carry paths.
module axis_fir_decim_full_precision_stage #(
    parameter int STAGE_ID = 0,
    parameter int DECIM = 10,
    parameter int TAPS = 95,
    parameter int IN_WIDTH = 16,
    parameter int OUT_WIDTH = 34
)(
    input wire aclk,
    input wire aresetn,
    input wire [2*IN_WIDTH-1:0] s_axis_tdata,
    input wire s_axis_tvalid,
    output wire s_axis_tready,
    output logic [2*OUT_WIDTH-1:0] m_axis_tdata,
    output logic m_axis_tvalid
);
    logic [$clog2(DECIM)-1:0] decim_count;
    logic [9:0] valid_pipe;
    wire output_due = s_axis_tvalid && (decim_count == DECIM-1);
    assign s_axis_tready = 1'b1;

    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            decim_count <= '0;
            valid_pipe <= '0;
            m_axis_tvalid <= 1'b0;
        end else begin
            valid_pipe <= {valid_pipe[8:0], output_due};
            m_axis_tvalid <= valid_pipe[9];
            if (s_axis_tvalid)
                decim_count <= (decim_count == DECIM-1) ? '0 : decim_count + 1'b1;
        end
    end

    for (genvar lane=0; lane<2; lane++) begin : g_lane
        logic signed [IN_WIDTH-1:0] history [0:TAPS-2];
        wire signed [IN_WIDTH-1:0] current_sample = s_axis_tdata[lane*IN_WIDTH +: IN_WIDTH];
        wire signed [OUT_WIDTH-1:0] product [0:TAPS-1];
        wire signed [OUT_WIDTH-1:0] level [0:8][0:TAPS-1];

        always_ff @(posedge aclk) begin
            if (!aresetn) begin
                for (int k=0; k<TAPS-1; k++) history[k] <= '0;
            end else if (s_axis_tvalid) begin
                history[0] <= current_sample;
                for (int k=1; k<TAPS-1; k++) history[k] <= history[k-1];
            end
        end

        for (genvar tap=0; tap<TAPS; tap++) begin : g_tap
            wire signed [IN_WIDTH-1:0] operand;
            if (tap==0) assign operand = current_sample;
            else assign operand = history[tap-1];
            localparam logic signed [17:0] COEFF = fir_coeff(STAGE_ID,tap);
            logic signed [OUT_WIDTH-1:0] combined;
            if (IN_WIDTH <= 27) begin : g_single
                (* use_dsp="yes" *) logic signed [IN_WIDTH+18-1:0] partial;
                always_ff @(posedge aclk) begin
                    if (s_axis_tvalid) partial <= operand * COEFF;
                    combined <= $signed(partial);
                end
            end else begin : g_split
                localparam int HIGH_WIDTH = IN_WIDTH-26;
                wire signed [26:0] lower = $signed({1'b0,operand[25:0]});
                wire signed [HIGH_WIDTH-1:0] upper = $signed(operand[IN_WIDTH-1:26]);
                (* use_dsp="yes" *) logic signed [44:0] partial_low;
                (* use_dsp="yes" *) logic signed [HIGH_WIDTH+18-1:0] partial_high;
                wire signed [OUT_WIDTH-1:0] low_extended = $signed(partial_low);
                wire signed [OUT_WIDTH-1:0] high_extended = $signed(partial_high);
                always_ff @(posedge aclk) begin
                    if (s_axis_tvalid) begin
                        partial_low <= lower * COEFF;
                        partial_high <= upper * COEFF;
                    end
                    combined <= low_extended + (high_extended <<< 26);
                end
            end
            assign product[tap] = combined;
            assign level[0][tap] = product[tap];
        end

        for (genvar depth=1; depth<=8; depth++) begin : g_tree
            localparam int PREVIOUS = (TAPS + (1<<(depth-1))-1) >> (depth-1);
            localparam int COUNT = (TAPS + (1<<depth)-1) >> depth;
            for (genvar k=0; k<COUNT; k++) begin : g_sum
                (* use_dsp="no" *) logic signed [OUT_WIDTH-1:0] sum;
                if (2*k+1 < PREVIOUS) begin : g_pair
                    always_ff @(posedge aclk)
                        sum <= $signed(level[depth-1][2*k]) + $signed(level[depth-1][2*k+1]);
                end else begin : g_tail
                    always_ff @(posedge aclk) sum <= level[depth-1][2*k];
                end
                assign level[depth][k] = sum;
            end
        end
        always_ff @(posedge aclk) begin
            if (!aresetn) m_axis_tdata[lane*OUT_WIDTH +: OUT_WIDTH] <= '0;
            else if (valid_pipe[9]) m_axis_tdata[lane*OUT_WIDTH +: OUT_WIDTH] <= level[8][0];
        end
    end
endmodule
