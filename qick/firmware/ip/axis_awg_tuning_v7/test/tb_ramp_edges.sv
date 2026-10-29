`timescale 1ns / 1ps
module tb_ramp_edges;
reg clk = 0, rstn = 0, cv = 0, ov = 0;
always #1.666667 clk = ~clk;
reg [159:0] command = 0;
reg signed [31:0] override_value = 0;
wire [255:0] samples;
wire [31:0] status;
wire signed [31:0] current;
reg [193:0] inputs[0:99999];
reg [255:0] expected[0:99999];
reg [31:0] count[0:0];
v7_awg_tuning_ctrl dut (
   .aclk(clk),
   .aresetn(rstn),
   .s_axis_tdata(command),
   .s_axis_tvalid(cv),
   .axi_override_value(override_value),
   .axi_override_valid(ov),
   .m_axis_tdata(samples),
   .m_axis_tready(1'b0),
   .current_value_o(current),
   .status_o(status)
);
initial begin
   $readmemh("vector_count.hex", count);
   $readmemh("stimulus.hex", inputs, 0, count[0] - 1);
   $readmemh("expected.hex", expected, 0, count[0] - 1);
   repeat (40) @(negedge clk);
   rstn = 1;
   for (int i = 0; i < count[0]; i++) begin
      command = inputs[i][159:0];
      cv = inputs[i][160];
      override_value = inputs[i][192:161];
      ov = inputs[i][193];
      @(posedge clk);
      #0.1;
      if (samples !== expected[i])
         $fatal(1, "v7 all-sample mismatch cycle=%0d actual=%h expected=%h", i, samples, expected[i]);
      if (current !== $signed(samples[15:0])) $fatal(1, "readback is not physical lane0");
      if (status[7]) $fatal(1, "legal extended packet rejected cycle=%0d", i);
      @(negedge clk);
   end
   $display("PASS V7_RAMP_EDGES cycles=%0d scalar_samples=%0d latency=11", count[0], count[0] * 16);
   $finish;
end
initial begin
   #10000000;
   $fatal(1, "watchdog");
end
endmodule
