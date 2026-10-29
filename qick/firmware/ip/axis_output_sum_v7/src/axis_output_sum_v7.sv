// v7: equalize common-latency AWG(27) and DDS(29) command-to-sample paths.
// Delay every AWG path by 2 clocks, including channels without DDS addition.
// The following two-stage signed sum/round/clamp is identical to v1.
`timescale 1ns/1ps
`default_nettype none
module axis_output_sum_v7 #(
    parameter integer N_PTS = 16,
    parameter integer BYPASS = 0,
    parameter integer PIPELINE_CYCLES = 2,
    parameter integer AWG_DELAY_CYCLES = 2
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
    // Data need not be reset: the reset valid pipeline masks all stale words.
    // This also permits SRL inference without a 512-bit reset fanout per DAC.
    logic [16*N_PTS-1:0] awg_delay [AWG_DELAY_CYCLES];
    logic [AWG_DELAY_CYCLES-1:0] awg_valid;
    wire [16*N_PTS-1:0] aligned_awg = awg_delay[AWG_DELAY_CYCLES-1];
    wire aligned_valid = awg_valid[AWG_DELAY_CYCLES-1];
    logic signed [16:0] sums [N_PTS];
    logic valid_sum;
    wire unused_ready = m_axis_tready;
    assign s0_axis_tready = 1'b1;
    assign s1_axis_tready = 1'b1;

    always_ff @(posedge aclk) begin
        awg_delay[0] <= s0_axis_tdata;
        for (integer d=1; d<AWG_DELAY_CYCLES; d=d+1)
            awg_delay[d] <= awg_delay[d-1];
        if (!aresetn) awg_valid <= '0;
        else awg_valid <= {awg_valid[AWG_DELAY_CYCLES-2:0],s0_axis_tvalid};
    end

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
            valid_sum <= aligned_valid | ((BYPASS == 0) && s1_axis_tvalid);
            m_axis_tvalid <= valid_sum;
            clipped_o <= 0;
            for (integer i=0; i<N_PTS; i=i+1) begin
                sums[i] <= (aligned_valid ?
                    $signed({aligned_awg[16*i+15],aligned_awg[16*i+:16]}) : 17'sd0)
                    + ((BYPASS == 0 && s1_axis_tvalid) ?
                    $signed({s1_axis_tdata[16*i+15],s1_axis_tdata[16*i+:16]}) : 17'sd0);
                m_axis_tdata[16*i+:16] <= valid_sum ? saturate(sums[i]) : 16'd0;
                if (valid_sum && (sums[i] > 17'sd32764 || sums[i] < -17'sd32768))
                    clipped_o <= 1;
            end
        end
    end
    initial begin
        if (AWG_DELAY_CYCLES != 2 || PIPELINE_CYCLES != 2 || N_PTS != 16 || (BYPASS != 0 && BYPASS != 1))
            $error("axis_output_sum_v7 requires AWG_DELAY_CYCLES=2, N_PTS=16, PIPELINE_CYCLES=2, BYPASS=0/1");
    end
endmodule
`default_nettype wire
