// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps

import notch_decim_1m_to50k_coeffs_pkg::*;

// Continuous 1 MSPS to 50 kSPS FIR decimator and mains-notch cascade.
//
// Signal path:
//   1 MSPS IQ -> 113-tap Kaiser FIR /10 -> 100 kSPS ->
//   125-tap Kaiser FIR /2 -> 50 kSPS ->
//   20 harmonics x two identical notch biquads -> 50 kSPS IQ.
//
// The FIR stages deliberately use the same Q1.17 coefficient, 48-bit
// accumulator, parallel multiplier, and registered adder-tree methodology as
// axis_fir_decim_300to1_v1. Triggering is absent: all filter histories and
// decimation phases continue across capture events. The downstream DDR block
// gates storage and applies a programmable valid-output-sample delay.
module axis_notch_decim_1m_to50k_v1 #(
    parameter int S_AXIS_DATA_WIDTH = 32,
    parameter int M_AXIS_DATA_WIDTH = 32,
    parameter int LANE_WIDTH        = 16,
    parameter int DECIMATION_PARAM  = 20
)(
    input  wire                          aclk,
    input  wire                          aresetn,

    input  wire [S_AXIS_DATA_WIDTH-1:0] s_axis_tdata,
    input  wire                         s_axis_tvalid,
    output wire                         s_axis_tready,
    input  wire                         s_axis_tlast,

    output wire [M_AXIS_DATA_WIDTH-1:0] m_axis_tdata,
    output wire                         m_axis_tvalid,
    input  wire                         m_axis_tready,
    output wire                         m_axis_tlast
);

    wire [31:0] stage0_tdata;
    wire        stage0_tvalid;
    wire        stage0_tready;
    wire [31:0] stage1_tdata;
    wire        stage1_tvalid;
    wire        stage1_tready;
    wire        notch_tready;
    wire unused_inputs = s_axis_tlast | m_axis_tready | (DECIMATION_PARAM != DECIMATION);

    assign m_axis_tlast = 1'b0;

    axis_fir_decim_stage #(
        .STAGE_ID   (0),
        .DECIM      (STAGE0_DECIM),
        .TAPS       (STAGE0_TAPS),
        .DATA_WIDTH (S_AXIS_DATA_WIDTH),
        .LANE_WIDTH (LANE_WIDTH),
        .ACC_WIDTH  (FIR_ACC_WIDTH)
    ) fir_stage0_i (
        .aclk          (aclk),
        .aresetn       (aresetn),
        .s_axis_tdata  (s_axis_tdata),
        .s_axis_tvalid (s_axis_tvalid),
        .s_axis_tready (s_axis_tready),
        .m_axis_tdata  (stage0_tdata),
        .m_axis_tvalid (stage0_tvalid),
        .m_axis_tready (stage0_tready)
    );

    axis_fir_decim_stage #(
        .STAGE_ID   (1),
        .DECIM      (STAGE1_DECIM),
        .TAPS       (STAGE1_TAPS),
        .DATA_WIDTH (M_AXIS_DATA_WIDTH),
        .LANE_WIDTH (LANE_WIDTH),
        .ACC_WIDTH  (FIR_ACC_WIDTH)
    ) fir_stage1_i (
        .aclk          (aclk),
        .aresetn       (aresetn),
        .s_axis_tdata  (stage0_tdata),
        .s_axis_tvalid (stage0_tvalid),
        .s_axis_tready (stage0_tready),
        .m_axis_tdata  (stage1_tdata),
        .m_axis_tvalid (stage1_tvalid),
        .m_axis_tready (stage1_tready)
    );

    axis_sos_iq_engine #(
        .N_SECTIONS (NOTCH_SECTIONS),
        .DATA_WIDTH (M_AXIS_DATA_WIDTH),
        .LANE_WIDTH (LANE_WIDTH)
    ) notch_i (
        .aclk          (aclk),
        .aresetn       (aresetn),
        .s_axis_tdata  (stage1_tdata),
        .s_axis_tvalid (stage1_tvalid),
        .s_axis_tready (stage1_tready),
        .m_axis_tdata  (m_axis_tdata),
        .m_axis_tvalid (m_axis_tvalid)
    );

    assign notch_tready = stage1_tready;

`ifndef SYNTHESIS
    always_ff @(posedge aclk) begin
        if (aresetn && stage0_tvalid && !stage0_tready)
            $fatal(1, "100 kSPS FIR sample was not accepted by stage 1");
        if (aresetn && stage1_tvalid && !notch_tready)
            $fatal(1, "50 kSPS FIR sample arrived while notch engine was busy");
    end
`endif

endmodule
