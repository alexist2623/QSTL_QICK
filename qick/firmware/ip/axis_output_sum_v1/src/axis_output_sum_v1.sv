// Fixed-cadence DAC output combiner. Existing waveform generators are unchanged.
// Each word contains 16 consecutive signed 16-bit samples, lane zero first.
// This is a real-time sink/source, not an elastic AXIS FIFO: backpressure never
// pauses the sample timeline. Missing input words contribute zero.
`timescale 1ns/1ps
`default_nettype none
module axis_output_sum_v1 #(
    parameter integer N_PTS = 16,
    parameter integer BYPASS = 0,
    parameter integer PIPELINE_CYCLES = 2
) (
    (* X_INTERFACE_PARAMETER = "ASSOCIATED_BUSIF s0_axis:s1_axis:m_axis, ASSOCIATED_RESET aresetn" *)
    input wire aclk,
    (* X_INTERFACE_PARAMETER = "POLARITY ACTIVE_LOW" *) input wire aresetn,
    input wire [16*N_PTS-1:0] s0_axis_tdata,
    input wire s0_axis_tvalid,
    output wire s0_axis_tready,
    input wire [16*N_PTS-1:0] s1_axis_tdata,
    input wire s1_axis_tvalid,
    output wire s1_axis_tready,
    output logic [16*N_PTS-1:0] m_axis_tdata,
    output logic m_axis_tvalid,
    input wire m_axis_tready,
    output logic clipped_o
);
    logic signed [16:0] sums [N_PTS];
    logic valid_sum;
    wire unused_ready = m_axis_tready;
    assign s0_axis_tready = 1'b1;
    assign s1_axis_tready = 1'b1;

    // Retain both input LSBs until AFTER addition. Round once to effective
    // signed 14-bit DAC codes, ties toward +infinity, then restore MSB alignment.
    function automatic [15:0] saturate(input logic signed [16:0] value);
        logic signed [16:0] rounded;
        begin
            rounded = (value + 17'sd2) >>> 2;
            if (value > 17'sd32764) saturate = 16'h7ffc;
            else if (value < -17'sd32768) saturate = 16'h8000;
            else saturate = {rounded[13:0],2'b00};
        end
    endfunction

    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            valid_sum <= 0;
            m_axis_tvalid <= 0;
            m_axis_tdata <= 0;
            clipped_o <= 0;
            for (integer i=0; i<N_PTS; i=i+1) sums[i] <= 0;
        end else begin
            valid_sum <= s0_axis_tvalid | ((BYPASS == 0) && s1_axis_tvalid);
            m_axis_tvalid <= valid_sum;
            clipped_o <= 0;
            for (integer i=0; i<N_PTS; i=i+1) begin
                sums[i] <= (s0_axis_tvalid ?
                    $signed({s0_axis_tdata[16*i+15],s0_axis_tdata[16*i+:16]}) : 17'sd0)
                    + ((BYPASS == 0 && s1_axis_tvalid) ?
                    $signed({s1_axis_tdata[16*i+15],s1_axis_tdata[16*i+:16]}) : 17'sd0);
                m_axis_tdata[16*i+:16] <= valid_sum ? saturate(sums[i]) : 16'd0;
                if (valid_sum && (sums[i] > 17'sd32764 || sums[i] < -17'sd32768))
                    clipped_o <= 1;
            end
        end
    end

    // Elaboration guard: metadata must describe the physically implemented
    // two-register path. BYPASS follows that exact path as well.
    initial begin
        if (PIPELINE_CYCLES != 2 || N_PTS != 16 || (BYPASS != 0 && BYPASS != 1))
            $error("axis_output_sum_v1 requires N_PTS=16, PIPELINE_CYCLES=2, BYPASS=0/1");
    end
endmodule
`default_nettype wire
