// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps

import fir_decim_300to1_coeffs_pkg::*;

// 300 MSPS to 1 MSPS two-lane FIR decimator for the qstl_awg_tuning_fir DDR path.
//
// Cascade:
//   stage 0: decimate by 10, 300 MSPS -> 30 MSPS
//   stage 1: decimate by 10,  30 MSPS ->  3 MSPS
//   stage 2: decimate by 3,    3 MSPS ->  1 MSPS
//
// The 32-bit stream is packed as:
//   lane 0 = tdata[15:0]
//   lane 1 = tdata[31:16]
module axis_fir_decim_300to1_v1 #(
    parameter int S_AXIS_DATA_WIDTH = 32,
    parameter int M_AXIS_DATA_WIDTH = 32,
    parameter int LANE_WIDTH        = 16,
    parameter int DECIM0            = 10,
    parameter int DECIM1            = 10,
    parameter int DECIM2            = 3,
    parameter int COEF_WIDTH_PARAM  = 18,
    parameter int ACC_WIDTH         = 48,
    parameter int OUT_WIDTH         = 16
)(
    input  wire                         aclk,
    input  wire                         aresetn,
    input  wire                         trigger,
    output logic                        capture_trigger,

    input  wire [S_AXIS_DATA_WIDTH-1:0] s_axis_tdata,
    input  wire                         s_axis_tvalid,
    output wire                         s_axis_tready,
    input  wire                         s_axis_tlast,

    output wire [M_AXIS_DATA_WIDTH-1:0] m_axis_tdata,
    output wire                         m_axis_tvalid,
    input  wire                         m_axis_tready,
    output wire                         m_axis_tlast
);

    localparam int TOTAL_DECIM = DECIM0 * DECIM1 * DECIM2;
    localparam int FIR_GROUP_DELAY_INPUT_SAMPLES =
        ((STAGE0_TAPS - 1) / 2) +
        DECIM0 * ((STAGE1_TAPS - 1) / 2) +
        DECIM0 * DECIM1 * ((STAGE2_TAPS - 1) / 2);
    // Every stage emits on DECIM-1 after a phase reset, so the first cascade
    // output is associated with input sample TOTAL_DECIM-1. Capture starts at
    // the first output whose FIR center is at or after the trigger sample.
    localparam int FIRST_OUTPUT_PHASE_INPUT_SAMPLES = TOTAL_DECIM - 1;
    localparam int DELAY_AFTER_FIRST_OUTPUT =
        FIR_GROUP_DELAY_INPUT_SAMPLES - FIRST_OUTPUT_PHASE_INPUT_SAMPLES;
    localparam int CAPTURE_SKIP_OUTPUTS =
        (DELAY_AFTER_FIRST_OUTPUT <= 0) ? 0 :
        ((DELAY_AFTER_FIRST_OUTPUT + TOTAL_DECIM - 1) / TOTAL_DECIM);

    wire unused_inputs = s_axis_tlast | (COEF_WIDTH_PARAM != COEF_WIDTH);

    wire [S_AXIS_DATA_WIDTH-1:0] stage0_tdata;
    wire                         stage0_tvalid;
    wire                         stage0_tready;

    wire [S_AXIS_DATA_WIDTH-1:0] stage1_tdata;
    wire                         stage1_tvalid;
    wire                         stage1_tready;

    assign m_axis_tlast = 1'b0;

    logic trigger_meta;
    logic trigger_sync;
    logic trigger_sync_d;
    logic capture_trigger_pending_r;
    logic [31:0] capture_output_count_r;

    wire trigger_align = trigger_sync & ~trigger_sync_d;

    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            trigger_meta   <= 1'b0;
            trigger_sync   <= 1'b0;
            trigger_sync_d <= 1'b0;
        end else begin
            trigger_meta   <= trigger;
            trigger_sync   <= trigger_meta;
            trigger_sync_d <= trigger_sync;
        end
    end

    // The FIR history remains continuous across a trigger, so its first
    // post-trigger outputs still describe pre-trigger input. Count real FIR
    // output-valid events and notify the DDR buffer one output period before
    // the first group-delay-compensated sample. The DDR buffer's trigger
    // synchronizer settles during that full 1 MSPS output interval.
    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            capture_trigger           <= 1'b0;
            capture_trigger_pending_r <= 1'b0;
            capture_output_count_r    <= '0;
        end else begin
            capture_trigger <= 1'b0;

            if (trigger_align) begin
                capture_output_count_r <= '0;
                if (CAPTURE_SKIP_OUTPUTS == 0) begin
                    capture_trigger           <= 1'b1;
                    capture_trigger_pending_r <= 1'b0;
                end else begin
                    capture_trigger_pending_r <= 1'b1;
                end
            end else if (capture_trigger_pending_r && m_axis_tvalid) begin
                if (capture_output_count_r == CAPTURE_SKIP_OUTPUTS - 1) begin
                    capture_trigger           <= 1'b1;
                    capture_trigger_pending_r <= 1'b0;
                end else begin
                    capture_output_count_r <= capture_output_count_r + 1'b1;
                end
            end
        end
    end

    axis_fir_decim_stage #(
        .STAGE_ID   (0),
        .DECIM      (DECIM0),
        .TAPS       (STAGE0_TAPS),
        .DATA_WIDTH (S_AXIS_DATA_WIDTH),
        .LANE_WIDTH (LANE_WIDTH),
        .ACC_WIDTH  (ACC_WIDTH),
        .OUT_WIDTH  (OUT_WIDTH)
    ) stage0_i (
        .aclk          (aclk),
        .aresetn       (aresetn),
        .trigger_align (trigger_align),
        .s_axis_tdata  (s_axis_tdata),
        .s_axis_tvalid (s_axis_tvalid),
        .s_axis_tready (s_axis_tready),
        .m_axis_tdata  (stage0_tdata),
        .m_axis_tvalid (stage0_tvalid),
        .m_axis_tready (stage0_tready)
    );

    axis_fir_decim_stage #(
        .STAGE_ID   (1),
        .DECIM      (DECIM1),
        .TAPS       (STAGE1_TAPS),
        .DATA_WIDTH (S_AXIS_DATA_WIDTH),
        .LANE_WIDTH (LANE_WIDTH),
        .ACC_WIDTH  (ACC_WIDTH),
        .OUT_WIDTH  (OUT_WIDTH)
    ) stage1_i (
        .aclk          (aclk),
        .aresetn       (aresetn),
        .trigger_align (trigger_align),
        .s_axis_tdata  (stage0_tdata),
        .s_axis_tvalid (stage0_tvalid),
        .s_axis_tready (stage0_tready),
        .m_axis_tdata  (stage1_tdata),
        .m_axis_tvalid (stage1_tvalid),
        .m_axis_tready (stage1_tready)
    );

    axis_fir_decim_stage #(
        .STAGE_ID   (2),
        .DECIM      (DECIM2),
        .TAPS       (STAGE2_TAPS),
        .DATA_WIDTH (M_AXIS_DATA_WIDTH),
        .LANE_WIDTH (LANE_WIDTH),
        .ACC_WIDTH  (ACC_WIDTH),
        .OUT_WIDTH  (OUT_WIDTH)
    ) stage2_i (
        .aclk          (aclk),
        .aresetn       (aresetn),
        .trigger_align (trigger_align),
        .s_axis_tdata  (stage1_tdata),
        .s_axis_tvalid (stage1_tvalid),
        .s_axis_tready (stage1_tready),
        .m_axis_tdata  (m_axis_tdata),
        .m_axis_tvalid (m_axis_tvalid),
        .m_axis_tready (m_axis_tready)
    );

endmodule
