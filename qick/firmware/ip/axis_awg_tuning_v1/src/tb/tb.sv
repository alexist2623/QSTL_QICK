`timescale 1ns/1ps
`default_nettype none

module tb();

initial begin
   $display("INFO: tb.sv is obsolete for the continuous RFDC-streaming AWG tuning FSM.");
   $display("INFO: Run tb_simple.sv for the current IDLE_ST/RAMP_ST deterministic stream checks.");
   $finish;
end

endmodule

`default_nettype wire
