`timescale 1ns / 1ps
// Every 16-bit input and random full-width targets through the public v7
// pipeline. Independent oracle checks all 16 lanes after exactly 11 clocks.
module tb_set_saturation;
reg clk = 0, rstn = 0, command_valid = 0, override_valid = 0;
always #1.6665 clk = ~clk;
reg [159:0] command = 0;
reg signed [31:0] override_value = 0;
wire [255:0] out;
wire valid, ready;
wire [31:0] status;
integer sent = 0;
v7_awg_tuning_ctrl #(
   .EXTRA_Y_PIPE_STAGES(3)
) dut (
   .aclk(clk),
   .aresetn(rstn),
   .s_axis_tdata(command),
   .s_axis_tvalid(command_valid),
   .s_axis_tready(ready),
   .axi_override_value(override_value),
   .axi_override_valid(override_valid),
   .m_axis_tdata(out),
   .m_axis_tvalid(valid),
   .m_axis_tready(1'b1),
   .status_o(status),
   .current_value_o()
);
awg_v7_raw_checker oracle (
   .clk(clk),
   .rstn(rstn),
   .command_valid(command_valid),
   .command(command),
   .raw_samples(out),
   .override_valid(override_valid),
   .override_value(override_value)
);
task automatic tick;
   @(posedge clk);
   #0.1;
endtask
task automatic set_value(input integer value, input bit use_override, input bit zero);
   @(negedge clk);
   command = 0;
   command[31:0] = use_override ? ~value : value;
   command[145:144] = 1;
   command[146] = zero;
   command_valid = 1;
   override_valid = use_override;
   override_value = value;
   tick();
   sent = sent + 1;
   if (!valid || !ready) $fatal(1, "continuous valid/ready lost");
endtask
task automatic terminal_ramp(input integer value);
   @(negedge clk);
   command = 0;
   command[31:0] = value;
   command[145:144] = 2;
   command[86:64] = 1;
   command_valid = 1;
   override_valid = 0;
   tick();
   @(negedge clk);
   command_valid = 0;
   command = 0;
   repeat (14) tick();
endtask
initial begin
   repeat (40) tick();
   @(negedge clk);
   rstn = 1;
   repeat (5) tick();
   for (integer value = -33000; value <= 33000; value = value + 1) set_value(value, 0, value % 257 == 0);
   set_value(32'sh80000000, 0, 0);
   set_value(32'sh7fffffff, 0, 0);
   set_value(32'sh80000000, 1, 0);
   set_value(32'sh7fffffff, 1, 0);
   for (integer trial = 0; trial < 20000; trial = trial + 1)
   set_value($signed($urandom), trial % 2, trial % 257 == 0);
   for (integer value = -32772; value <= -32760; value = value + 1) terminal_ramp(value);
   for (integer value = 32760; value <= 32772; value = value + 1) terminal_ramp(value);
   terminal_ramp(32'sh80000000);
   terminal_ramp(32'sh7fffffff);
   if (oracle.ramps != 28 || oracle.overrides != 10002 || sent != 86005) $fatal(1, "coverage missing");
   $display(
      "PASS SET/override/terminal RAMP saturation: %0d consecutive SET/override commands; 28 terminal RAMP commands; %0d all-lane samples",
      sent, oracle.checks);
   $finish;
end
initial begin
   #1000000;
   $fatal(1, "watchdog");
end
endmodule
