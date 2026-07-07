// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps

// Convert one accumulated IQ word into 64-bit AXIS beats.
//
// Internal AVG accumulation uses {Q_accum[4*B-1:0], I_accum[4*B-1:0]}.
// The external processed AXIS interface remains 4*B bits wide for
// compatibility with existing 64-bit tProc paths when B=16.
//
// Full-precision mode beat order:
//   beat 0: I_accum
//   beat 1: Q_accum
//
// Compact mode emits one beat:
//   {Q_accum[2*B-1:0], I_accum[2*B-1:0]}
//
// For B=16, compact mode is {Q_accum[31:0], I_accum[31:0]}.
module axis_accum_word_to_axis64 #(
    parameter int B = 16,
    parameter int ACC_CH_WIDTH = 4*B,
    parameter int ACC_WORD_WIDTH = 8*B,
    parameter int OUT_WIDTH = 4*B
) (
    input  logic                         clk,
    input  logic                         rstn,

    input  logic                         in_valid_i,
    output logic                         in_ready_o,
    input  logic [ACC_WORD_WIDTH-1:0]    in_word_i,
    input  logic                         in_last_i,
    input  logic                         compact_i,

    output logic                         m_axis_tvalid,
    input  logic                         m_axis_tready,
    output logic [OUT_WIDTH-1:0]         m_axis_tdata,
    output logic                         m_axis_tlast
);

    logic active_r;
    logic beat_sel_r;
    logic last_r;
    logic [ACC_WORD_WIDTH-1:0] word_r;

    wire [ACC_CH_WIDTH-1:0] in_i_word = in_word_i[ACC_CH_WIDTH-1:0];
    wire [ACC_CH_WIDTH-1:0] in_q_word = in_word_i[ACC_WORD_WIDTH-1:ACC_CH_WIDTH];
    wire [ACC_CH_WIDTH-1:0] hold_i_word = word_r[ACC_CH_WIDTH-1:0];
    wire [ACC_CH_WIDTH-1:0] hold_q_word = word_r[ACC_WORD_WIDTH-1:ACC_CH_WIDTH];
    wire [OUT_WIDTH-1:0] compact_word = {
        in_q_word[2*B-1:0],
        in_i_word[2*B-1:0]
    };

    assign in_ready_o    = compact_i ? m_axis_tready : ~active_r;
    assign m_axis_tvalid = compact_i ? in_valid_i : active_r;
    assign m_axis_tdata  = compact_i ? compact_word :
                           (beat_sel_r ? hold_q_word[OUT_WIDTH-1:0]
                                       : hold_i_word[OUT_WIDTH-1:0]);
    assign m_axis_tlast  = compact_i ? (in_valid_i & in_last_i) :
                           (active_r & beat_sel_r & last_r);

    always_ff @(posedge clk) begin
        if (!rstn) begin
            active_r   <= 1'b0;
            beat_sel_r <= 1'b0;
            last_r     <= 1'b0;
            word_r     <= '0;
        end else if (compact_i) begin
            active_r   <= 1'b0;
            beat_sel_r <= 1'b0;
            last_r     <= 1'b0;
            word_r     <= '0;
        end else begin
            if (!active_r) begin
                if (in_valid_i) begin
                    active_r   <= 1'b1;
                    beat_sel_r <= 1'b0;
                    last_r     <= in_last_i;
                    word_r     <= in_word_i;
                end
            end else if (m_axis_tready) begin
                if (!beat_sel_r) begin
                    beat_sel_r <= 1'b1;
                end else begin
                    active_r   <= 1'b0;
                    beat_sel_r <= 1'b0;
                    last_r     <= 1'b0;
                end
            end
        end
    end

endmodule
