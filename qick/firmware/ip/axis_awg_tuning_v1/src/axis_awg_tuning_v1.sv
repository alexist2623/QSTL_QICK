`default_nettype none

module axis_awg_tuning_v1
   #(
      // Number of parallel 16-bit samples per output word.
      parameter int N_DDS = 16,

      // Output sample width.
      parameter int B = 16,

      // Fractional bits in the signed fixed-point ramp step.
      // With the default command field width this is a signed 16.16 step.
      parameter int FRAC = 16,

      // tProcessor v1 realtime output width.
      parameter int CMD_WIDTH = 160
   )
   (
      // Reset and clock.
      input  wire                   aresetn,
      input  wire                   aclk,

      // AXIS slave command input.
      input  wire [CMD_WIDTH-1:0]   s_axis_tdata,
      input  wire                   s_axis_tvalid,
      output wire                   s_axis_tready,

      // AXIS master sample output.
      output wire [N_DDS*B-1:0]     m_axis_tdata,
      output wire                   m_axis_tvalid,
      input  wire                   m_axis_tready
   );

awg_tuning_ctrl
   #(
      .N_DDS      (N_DDS    ),
      .B          (B        ),
      .FRAC       (FRAC     ),
      .CMD_WIDTH  (CMD_WIDTH)
   )
   awg_tuning_ctrl_i
   (
      // Reset and clock.
      .aresetn          (aresetn        ),
      .aclk             (aclk           ),

      // AXIS slave command input.
      .s_axis_tdata     (s_axis_tdata   ),
      .s_axis_tvalid    (s_axis_tvalid  ),
      .s_axis_tready    (s_axis_tready  ),

      // AXIS master sample output.
      .m_axis_tdata     (m_axis_tdata   ),
      .m_axis_tvalid    (m_axis_tvalid  ),
      .m_axis_tready    (m_axis_tready  )
   );

endmodule

`default_nettype wire
