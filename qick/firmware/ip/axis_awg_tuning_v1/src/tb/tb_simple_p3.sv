`timescale 1ns/1ps
`default_nettype none

module tb_simple_p3();

tb_simple #(
   .EXTRA_Y_PIPE_STAGES(3)
) tb_i ();

endmodule

`default_nettype wire
