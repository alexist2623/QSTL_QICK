// Continuous, phase-coherent square DDS. Lane zero is the earliest sample.
`timescale 1ns/1ps
`default_nettype none
module square_dds #(
    parameter integer N_PTS = 16
) (
    input wire aclk, aresetn,
    input wire [159:0] command,
    input wire command_valid,
    input wire mute,
    output logic enabled,
    output logic [N_PTS*16-1:0] samples,
    output logic [47:0] rc_half_step,
    output logic rc_enabled, rc_clear, samples_active
);
    logic [31:0] ftw, offset, accumulator;
    logic [15:0] amplitude;
    logic clear_phase;
    logic [31:0] base0, base1;
    logic [31:0] partial_lo [N_PTS], partial_hi [N_PTS];
    logic [31:0] lane_offset [N_PTS], lane_phase [N_PTS];
    logic [15:0] positive [3], negative [3];
    logic [47:0] half_step, step_pipe[3];
    logic rc_enable, clear_rc;
    logic [2:0] rc_enable_pipe, rc_clear_pipe, active_pipe;

    // Accepted command -> first updated output word: four aclk periods.
    // Every stage carries its own amplitude and phase-offset state, so even
    // adjacent commands cannot mix fields from different updates.
    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            ftw <= 0; offset <= 0; amplitude <= 0;
            accumulator <= 0; clear_phase <= 0; enabled <= 0;
            base0 <= 0; base1 <= 0; samples <= 0;
            half_step<=0; rc_enable<=0; clear_rc<=0;
            rc_half_step<=0; rc_enabled<=0; rc_clear<=0; samples_active<=0;
            rc_enable_pipe<=0; rc_clear_pipe<=0; active_pipe<=0;
            for (integer j=0; j<3; j=j+1) begin
                positive[j] <= 0; negative[j] <= 0;
                step_pipe[j]<=0;
            end
            for (integer k=0; k<N_PTS; k=k+1) begin
                partial_lo[k] <= 0; partial_hi[k] <= 0;
                lane_offset[k] <= 0; lane_phase[k] <= 0;
            end
        end else begin
            clear_phase <= 0;
            clear_rc<=0;
            if (command_valid) begin
                ftw <= command[31:0];
                offset <= command[63:32];
                // Unsigned magnitude; symmetric DAC codes, two unused LSBs.
                amplitude <= (command[79:64] > 32764) ? 16'd32764
                              : {1'b0, command[78:66], 2'b00};
                enabled <= command[128];
                clear_phase <= command[129];
                half_step<=command[127:80];
                rc_enable<=command[130]; clear_rc<=command[131];
            end
            // Stop the tProcessor before software mute: a later AXIS command
            // explicitly enables output again. Mute never resets phase.
            if (mute) enabled <= 0;

            accumulator <= (clear_phase ? 32'd0 : accumulator) + N_PTS*ftw;
            base0 <= (clear_phase ? 32'd0 : accumulator) + offset;
            positive[0] <= enabled ? amplitude : 16'd0;
            negative[0] <= enabled ? -amplitude : 16'd0;
            base1 <= base0;
            positive[1] <= positive[0]; negative[1] <= negative[0];
            positive[2] <= positive[1]; negative[2] <= negative[1];
            step_pipe[0]<=half_step; step_pipe[1]<=step_pipe[0]; step_pipe[2]<=step_pipe[1];
            rc_enable_pipe<={rc_enable_pipe[1:0],rc_enable};
            rc_clear_pipe<={rc_clear_pipe[1:0],clear_rc};
            active_pipe<={active_pipe[1:0],enabled};
            rc_half_step<=step_pipe[2]; rc_enabled<=rc_enable_pipe[2];
            rc_clear<=rc_clear_pipe[2]; samples_active<=active_pipe[2];
            for (integer k=0; k<N_PTS; k=k+1) begin
                // Each constant product uses at most one 32-bit addition.
                // Split lane*k into two base-four digits before summing.
                partial_lo[k] <= (k % 4)*ftw;
                partial_hi[k] <= (k / 4)*(ftw << 2);
                lane_offset[k] <= partial_lo[k] + partial_hi[k];
                lane_phase[k] <= base1 + lane_offset[k];
                samples[16*k +: 16] <= lane_phase[k][31] ? negative[2] : positive[2];
            end
        end
    end
endmodule
`default_nettype wire
