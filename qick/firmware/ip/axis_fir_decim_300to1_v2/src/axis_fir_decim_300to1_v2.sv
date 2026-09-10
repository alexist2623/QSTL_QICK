// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps
import fir_decim_300to1_v2_coeffs_pkg::*;

// Continuous full-precision 300-to-1 MSPS FIR. Input: two signed int16 lanes.
// Exact stage results: 34, 51, 69 bits, with no intermediate bit removal.
// Only the final 69-to-64 conversion rounds the least-significant five bits.
// Stored output: {signed Q[63:0], signed I[63:0]}; input-code units are recovered
// by multiplying the stored integer by 2^-OUTPUT_SCALE_LOG2. No floating-point
// arithmetic is used in this IP or its DDR storage format.
module axis_fir_decim_300to1_v2 #(
    parameter int S_AXIS_DATA_WIDTH = 32,
    parameter int M_AXIS_DATA_WIDTH = 128,
    parameter int LANE_WIDTH = 16,
    parameter int DECIM0 = 10,
    parameter int DECIM1 = 10,
    parameter int DECIM2 = 3,
    parameter int COEF_WIDTH_PARAM = 18,
    parameter int ACC_WIDTH = 69,
    parameter int OUT_WIDTH = 64,
    parameter int OUTPUT_SCALE_LOG2 = 46,
    parameter int FORMAT_VERSION = 1,
    parameter int PIPELINE_LATENCY_CYCLES = 35
)(
    input wire aclk,
    input wire aresetn,
    input wire trigger,
    output wire capture_trigger,
    input wire [S_AXIS_DATA_WIDTH-1:0] s_axis_tdata,
    input wire s_axis_tvalid,
    output wire s_axis_tready,
    input wire s_axis_tlast,
    output wire [M_AXIS_DATA_WIDTH-1:0] m_axis_tdata,
    output logic m_axis_tvalid,
    input wire m_axis_tready,
    output wire m_axis_tlast
);
    initial begin
        if (S_AXIS_DATA_WIDTH!=32 || M_AXIS_DATA_WIDTH!=128 || LANE_WIDTH!=16 ||
            DECIM0!=10 || DECIM1!=10 || DECIM2!=3 || COEF_WIDTH_PARAM!=18 ||
            ACC_WIDTH!=69 || OUT_WIDTH!=64 || OUTPUT_SCALE_LOG2!=46 ||
            FORMAT_VERSION!=1 || PIPELINE_LATENCY_CYCLES!=35)
            $fatal(1,"Unsupported full-precision FIR parameters");
    end
    wire unused_inputs = trigger | s_axis_tlast | m_axis_tready;
    assign capture_trigger = 1'b0;
    assign m_axis_tlast = 1'b0;
    wire [67:0] stage0_data;
    wire [101:0] stage1_data;
    wire [137:0] stage2_data;
    wire stage0_valid,stage1_valid,stage2_valid;

    axis_fir_decim_full_precision_stage #(
        .STAGE_ID(0),.DECIM(10),.TAPS(95),.IN_WIDTH(16),.OUT_WIDTH(34)
    ) stage0_i (
        .aclk(aclk),.aresetn(aresetn),.s_axis_tdata(s_axis_tdata),
        .s_axis_tvalid(s_axis_tvalid),.s_axis_tready(s_axis_tready),
        .m_axis_tdata(stage0_data),.m_axis_tvalid(stage0_valid)
    );
    axis_fir_decim_full_precision_stage #(
        .STAGE_ID(1),.DECIM(10),.TAPS(127),.IN_WIDTH(34),.OUT_WIDTH(51)
    ) stage1_i (
        .aclk(aclk),.aresetn(aresetn),.s_axis_tdata(stage0_data),
        .s_axis_tvalid(stage0_valid),.s_axis_tready(),
        .m_axis_tdata(stage1_data),.m_axis_tvalid(stage1_valid)
    );
    axis_fir_decim_full_precision_stage #(
        .STAGE_ID(2),.DECIM(3),.TAPS(161),.IN_WIDTH(51),.OUT_WIDTH(69)
    ) stage2_i (
        .aclk(aclk),.aresetn(aresetn),.s_axis_tdata(stage1_data),
        .s_axis_tvalid(stage1_valid),.s_axis_tready(),
        .m_axis_tdata(stage2_data),.m_axis_tvalid(stage2_valid)
    );

    logic [1:0] format_valid;
    always_ff @(posedge aclk) begin
        if (!aresetn) begin format_valid <= '0; m_axis_tvalid <= 1'b0; end
        else begin
            format_valid <= {format_valid[0],stage2_valid};
            m_axis_tvalid <= format_valid[1];
        end
    end
    for (genvar lane=0;lane<2;lane++) begin : g_format
        wire signed [68:0] full = stage2_data[lane*69 +: 69];
        logic negative,negative_delayed;
        logic [68:0] magnitude,biased;
        logic signed [63:0] stored;
        // The L1-bound proof gives abs(full) < 2^68. After the final /32
        // rounding, the value fits signed int64 without clipping or wrapping.
        always_ff @(posedge aclk) begin
            negative <= full[68];
            magnitude <= full[68] ? $unsigned(-full) : $unsigned(full);
            negative_delayed <= negative;
            biased <= magnitude + 69'd16;
            if (!aresetn) stored <= '0;
            else if (format_valid[1])
                stored <= negative_delayed ? -$signed(biased[68:5]) : $signed(biased[68:5]);
        end
        assign m_axis_tdata[lane*64 +: 64] = stored;
    end
endmodule
