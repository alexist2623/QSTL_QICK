// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps

// Synchronize a trigger into one clock domain and emit one rising-edge pulse.
//
// This small utility IP is used by qstl_awg_tuning_fir so the FIR decimation
// phase reset and DDR sample-capture start are driven by the same aligned
// source-clock event.
module axis_trigger_sync_v1 (
    input  wire aclk,
    input  wire aresetn,
    input  wire trigger_in,
    output reg  trigger_pulse
);

    reg trigger_meta;
    reg trigger_sync;
    reg trigger_sync_d;

    always @(posedge aclk) begin
        if (!aresetn) begin
            trigger_meta  <= 1'b0;
            trigger_sync  <= 1'b0;
            trigger_sync_d <= 1'b0;
            trigger_pulse <= 1'b0;
        end else begin
            trigger_meta  <= trigger_in;
            trigger_sync  <= trigger_meta;
            trigger_sync_d <= trigger_sync;
            trigger_pulse <= trigger_sync & ~trigger_sync_d;
        end
    end

endmodule
