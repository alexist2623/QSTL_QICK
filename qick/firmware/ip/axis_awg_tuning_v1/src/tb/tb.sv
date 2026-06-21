`timescale 1ns/1ps
`default_nettype none

module tb();

localparam int N_DDS = 4;
localparam int B = 16;
localparam int FRAC = 16;
localparam int CMD_WIDTH = 160;
localparam int OUT_WIDTH = N_DDS*B;

localparam logic [1:0] OP_NOP  = 2'b00;
localparam logic [1:0] OP_SET  = 2'b01;
localparam logic [1:0] OP_RAMP = 2'b10;
localparam logic [1:0] OP_IDLE = 2'b11;

// RAMP duration is packed in scalar samples. One slow output cycle is one
// accepted m_axis vector word, so N_DDS scalar samples make one slow cycle.
// IDLE duration uses the same command field and counts aclk sequencer cycles
// while m_axis_tvalid stays low.
localparam int LONG_POS_WORDS = 5;
localparam int LONG_NEG_WORDS = 6;
localparam int LONG_POS_DURATION = LONG_POS_WORDS*N_DDS;
localparam int LONG_NEG_DURATION = LONG_NEG_WORDS*N_DDS;
localparam int IDLE_SLOW_CYCLES = 5;

logic                   aresetn;
logic                   aclk;

logic [CMD_WIDTH-1:0]   s_axis_tdata;
logic                   s_axis_tvalid;
wire                    s_axis_tready;

wire [OUT_WIDTH-1:0]    m_axis_tdata;
wire                    m_axis_tvalid;
logic                   m_axis_tready;

int                     fd;
int                     errors;
int                     csv_sample;
logic [OUT_WIDTH-1:0]   current_hold_word;
bit                     have_hold;

axis_awg_tuning_v1
   #(
      .N_DDS     (N_DDS    ),
      .B         (B        ),
      .FRAC      (FRAC     ),
      .CMD_WIDTH (CMD_WIDTH)
   )
   DUT
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

always begin
   aclk = 1'b0;
   #5;
   aclk = 1'b1;
   #5;
end

function automatic logic signed [31:0] calc_step;
   input logic signed [31:0] y_start;
   input logic signed [31:0] y_target;
   input logic [31:0] duration;
   longint signed delta;
   longint signed numerator;
   longint signed denominator;
   longint signed quotient;
   begin
      if (duration <= 1) begin
         calc_step = 32'sd0;
      end
      else begin
         delta = y_target - y_start;
         numerator = delta <<< FRAC;
         denominator = duration - 1;
         quotient = numerator / denominator;
         calc_step = quotient[31:0];
      end
   end
endfunction

function automatic logic [B-1:0] sat_int64;
   input longint signed value;
   longint signed max_sample;
   longint signed min_sample;
   begin
      max_sample = (64'sd1 <<< (B-1)) - 64'sd1;
      min_sample = -(64'sd1 <<< (B-1));

      if (value > max_sample)
         sat_int64 = {1'b0, {(B-1){1'b1}}};
      else if (value < min_sample)
         sat_int64 = {1'b1, {(B-1){1'b0}}};
      else
         sat_int64 = value[B-1:0];
   end
endfunction

function automatic logic [OUT_WIDTH-1:0] scalar_word;
   input logic signed [31:0] value;
   logic [OUT_WIDTH-1:0] word;
   logic [B-1:0] sample;
   begin
      sample = sat_int64(value);
      word = {OUT_WIDTH{1'b0}};
      for (int i = 0; i < N_DDS; i = i + 1)
         word[i*B +: B] = sample;
      scalar_word = word;
   end
endfunction

function automatic logic [OUT_WIDTH-1:0] expected_ramp_word;
   input logic signed [31:0] y_start;
   input logic signed [31:0] y_target;
   input logic [31:0] duration;
   input logic signed [31:0] step;
   input int unsigned base_index;
   logic [OUT_WIDTH-1:0] word;
   longint signed fixed_value;
   longint signed int_value;
   longint signed signed_lane_index;
   int unsigned lane_index;
   begin
      word = {OUT_WIDTH{1'b0}};

      for (int i = 0; i < N_DDS; i = i + 1) begin
         lane_index = base_index + i;

         if (duration <= 1 || lane_index >= duration - 1) begin
            word[i*B +: B] = sat_int64(y_target);
         end
         else begin
            signed_lane_index = lane_index;
            fixed_value = (longint'(y_start) <<< FRAC) + (longint'(step) * signed_lane_index);
            int_value = fixed_value >>> FRAC;
            word[i*B +: B] = sat_int64(int_value);
         end
      end

      expected_ramp_word = word;
   end
endfunction

function automatic logic [CMD_WIDTH-1:0] make_cmd;
   input logic signed [31:0] y_target;
   input logic signed [31:0] y_start;
   input logic [31:0] duration;
   input logic signed [31:0] step;
   input logic [1:0] opcode;
   input logic hold_zero;
   input logic clear;
   logic [CMD_WIDTH-1:0] cmd;
   begin
      cmd = {CMD_WIDTH{1'b0}};
      cmd[31:0]    = y_target;
      cmd[63:32]   = y_start;
      cmd[95:64]   = duration;
      cmd[127:96]  = step;
      cmd[145:144] = opcode;
      cmd[146]     = hold_zero;
      cmd[148]     = clear;
      make_cmd = cmd;
   end
endfunction

task automatic fail;
   input string msg;
   begin
      errors++;
      $display("ERROR: %s at t=%0t", msg, $time);
      $fatal(1);
   end
endtask

task automatic dump_word;
   input logic [OUT_WIDTH-1:0] word;
   logic signed [B-1:0] lane_value;
   begin
      for (int i = 0; i < N_DDS; i = i + 1) begin
         lane_value = word[i*B +: B];
         $fwrite(fd, "%0d,%0d,%0d\n", csv_sample, i, lane_value);
      end
      csv_sample++;
   end
endtask

task automatic check_word;
   input logic [OUT_WIDTH-1:0] expected;
   input string tag;
   begin
      if (m_axis_tdata !== expected) begin
         $display("Expected %h", expected);
         $display("Actual   %h", m_axis_tdata);
         fail({"m_axis_tdata mismatch: ", tag});
      end

      dump_word(m_axis_tdata);
   end
endtask

task automatic send_cmd;
   input logic [CMD_WIDTH-1:0] cmd;
   input bit drain_hold;
   input logic [OUT_WIDTH-1:0] hold_word;
   input string tag;
   begin
      @(negedge aclk);
      s_axis_tdata  = cmd;
      s_axis_tvalid = 1'b1;
      m_axis_tready = drain_hold;

      if (drain_hold && !m_axis_tvalid)
         fail({"expected held output before command: ", tag});

      do begin
         @(posedge aclk);

         if (drain_hold && m_axis_tvalid && m_axis_tready)
            check_word(hold_word, {tag, " held output"});
      end while (!(s_axis_tvalid && s_axis_tready));

      @(negedge aclk);
      s_axis_tvalid = 1'b0;
      m_axis_tready = 1'b0;
   end
endtask

task automatic recv_word;
   input logic [OUT_WIDTH-1:0] expected;
   input string tag;
   begin
      @(negedge aclk);
      m_axis_tready = 1'b1;

      do begin
         @(posedge aclk);
      end while (!(m_axis_tvalid && m_axis_tready));

      check_word(expected, tag);

      @(negedge aclk);
      m_axis_tready = 1'b0;
   end
endtask

task automatic recv_ramp;
   input logic signed [31:0] y_start;
   input logic signed [31:0] y_target;
   input logic [31:0] duration;
   input logic signed [31:0] step;
   input string tag;
   int unsigned base_index;
   logic [OUT_WIDTH-1:0] expected;
   begin
      base_index = 0;

      while (base_index < duration || base_index == 0) begin
         expected = expected_ramp_word(y_start, y_target, duration, step, base_index);
         recv_word(expected, $sformatf("%s base=%0d", tag, base_index));

         if (duration <= N_DDS)
            base_index = duration;
         else
            base_index = base_index + N_DDS;
      end
   end
endtask

task automatic recv_ramp_checked;
   input logic signed [31:0] y_start;
   input logic signed [31:0] y_target;
   input logic [31:0] duration;
   input logic signed [31:0] step;
   input string tag;
   input int direction;
   int unsigned base_index;
   int unsigned lane_index;
   logic [OUT_WIDTH-1:0] expected;
   logic signed [B-1:0] lane_value;
   longint signed sample_value;
   longint signed previous_value;
   bit have_previous;
   begin
      base_index = 0;
      have_previous = 1'b0;
      previous_value = 0;

      while (base_index < duration || base_index == 0) begin
         expected = expected_ramp_word(y_start, y_target, duration, step, base_index);

         @(negedge aclk);
         m_axis_tready = 1'b1;

         do begin
            @(posedge aclk);
         end while (!(m_axis_tvalid && m_axis_tready));

         check_word(expected, $sformatf("%s base=%0d", tag, base_index));

         if (direction != 0) begin
            for (int i = 0; i < N_DDS; i = i + 1) begin
               lane_index = base_index + i;

               if (lane_index < duration) begin
                  lane_value = m_axis_tdata[i*B +: B];
                  sample_value = lane_value;

                  if (have_previous && direction > 0 && sample_value < previous_value)
                     fail($sformatf("%s is not monotonically increasing at sample %0d", tag, lane_index));

                  if (have_previous && direction < 0 && sample_value > previous_value)
                     fail($sformatf("%s is not monotonically decreasing at sample %0d", tag, lane_index));

                  previous_value = sample_value;
                  have_previous = 1'b1;
               end
            end
         end

         @(negedge aclk);
         m_axis_tready = 1'b0;

         if (duration <= N_DDS)
            base_index = duration;
         else
            base_index = base_index + N_DDS;
      end
   end
endtask

task automatic check_idle_interval;
   input int unsigned cycles;
   input logic [OUT_WIDTH-1:0] hold_word;
   input string tag;
   begin
      for (int i = 0; i < cycles; i = i + 1) begin
         m_axis_tready = (i[0] == 1'b0) ? 1'b0 : 1'b1;
         #1;

         if (s_axis_tready !== 1'b0)
            fail($sformatf("%s accepted a command during idle cycle %0d", tag, i));

         if (m_axis_tvalid !== 1'b0)
            fail($sformatf("%s asserted m_axis_tvalid during idle cycle %0d", tag, i));

         if (m_axis_tdata !== hold_word)
            fail($sformatf("%s changed held tdata during idle cycle %0d", tag, i));

         @(negedge aclk);
      end

      m_axis_tready = 1'b1;
      #1;

      if (s_axis_tready !== 1'b1)
         fail({tag, " did not return ready after idle duration"});

      if (m_axis_tvalid !== 1'b1)
         fail({tag, " did not resume held output after idle duration"});

      if (m_axis_tdata !== hold_word)
         fail({tag, " resumed with a changed held output"});

      m_axis_tready = 1'b0;
   end
endtask

task automatic accept_pending_with_hold;
   input logic [OUT_WIDTH-1:0] hold_word;
   input string tag;
   begin
      @(negedge aclk);
      m_axis_tready = 1'b1;

      do begin
         @(posedge aclk);

         if (m_axis_tvalid && m_axis_tready)
            check_word(hold_word, {tag, " held output"});
      end while (!(s_axis_tvalid && s_axis_tready));

      @(negedge aclk);
      s_axis_tvalid = 1'b0;
      m_axis_tready = 1'b0;
   end
endtask

initial begin
   logic [CMD_WIDTH-1:0] cmd;
   logic signed [31:0] step;
   logic [OUT_WIDTH-1:0] expected;
   logic [OUT_WIDTH-1:0] frozen_word;
   int unsigned bp_base;

   errors = 0;
   csv_sample = 0;
   have_hold = 1'b0;
   current_hold_word = {OUT_WIDTH{1'b0}};

   fd = $fopen("dout_awg_tuning.csv", "w");
   if (fd == 0)
      fail("could not open dout_awg_tuning.csv");
   $fwrite(fd, "word,lane,value\n");

   aresetn = 1'b0;
   s_axis_tdata = {CMD_WIDTH{1'b0}};
   s_axis_tvalid = 1'b0;
   m_axis_tready = 1'b0;

   repeat (8) @(posedge aclk);
   aresetn = 1'b1;
   repeat (4) @(posedge aclk);

   if (s_axis_tready !== 1'b1)
      fail("s_axis_tready should be high after reset");
   if (m_axis_tvalid !== 1'b0)
      fail("m_axis_tvalid should be low after reset");

   // SET to a positive value.
   cmd = make_cmd(32'sd1234, 32'sd0, 32'd0, 32'sd0, OP_SET, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "set positive");
   expected = scalar_word(32'sd1234);
   recv_word(expected, "set positive");
   current_hold_word = expected;
   have_hold = 1'b1;

   // SET to a negative value.
   cmd = make_cmd(-32'sd1234, 32'sd0, 32'd0, 32'sd0, OP_SET, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "set negative");
   expected = scalar_word(-32'sd1234);
   recv_word(expected, "set negative");
   current_hold_word = expected;

   // NOP ignores duration and does not enter the timed IDLE path.
   cmd = make_cmd(32'sd0, 32'sd0, IDLE_SLOW_CYCLES, 32'sd0, OP_NOP, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "nop duration ignored");
   m_axis_tready = 1'b1;
   #1;
   if (s_axis_tready !== 1'b1)
      fail("NOP consumed duration instead of returning ready immediately");
   if (m_axis_tdata !== current_hold_word)
      fail("NOP changed held output");
   m_axis_tready = 1'b0;

   // IDLE after SET waits without emitting output or changing the held value.
   cmd = make_cmd(32'sd0, 32'sd0, IDLE_SLOW_CYCLES, 32'sd0, OP_IDLE, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "idle after set");
   check_idle_interval(IDLE_SLOW_CYCLES, current_hold_word, "idle after set");

   // RAMP increasing.
   step = calc_step(-32'sd1000, 32'sd1000, 32'd8);
   cmd = make_cmd(32'sd1000, -32'sd1000, 32'd8, step, OP_RAMP, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "ramp increasing");
   recv_ramp(-32'sd1000, 32'sd1000, 32'd8, step, "ramp increasing");
   current_hold_word = scalar_word(32'sd1000);

   // RAMP decreasing.
   step = calc_step(32'sd2000, -32'sd2000, 32'd9);
   cmd = make_cmd(-32'sd2000, 32'sd2000, 32'd9, step, OP_RAMP, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "ramp decreasing");
   recv_ramp(32'sd2000, -32'sd2000, 32'd9, step, "ramp decreasing");
   current_hold_word = scalar_word(-32'sd2000);

   // Long positive RAMP: 5 accepted m_axis words, not just 5 lanes.
   step = calc_step(-32'sd1500, 32'sd1500, LONG_POS_DURATION);
   cmd = make_cmd(32'sd1500, -32'sd1500, LONG_POS_DURATION, step, OP_RAMP, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "long ramp increasing");
   recv_ramp_checked(-32'sd1500, 32'sd1500, LONG_POS_DURATION, step, "long ramp increasing", 1);
   current_hold_word = scalar_word(32'sd1500);

   // Long negative RAMP: 6 accepted m_axis words with monotonic decrease.
   step = calc_step(32'sd1800, -32'sd1800, LONG_NEG_DURATION);
   cmd = make_cmd(-32'sd1800, 32'sd1800, LONG_NEG_DURATION, step, OP_RAMP, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "long ramp decreasing");
   recv_ramp_checked(32'sd1800, -32'sd1800, LONG_NEG_DURATION, step, "long ramp decreasing", -1);
   current_hold_word = scalar_word(-32'sd1800);

   // RAMP with duration 1.
   cmd = make_cmd(32'sd222, 32'sd111, 32'd1, 32'sd0, OP_RAMP, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "duration one");
   recv_ramp(32'sd111, 32'sd222, 32'd1, 32'sd0, "duration one");
   current_hold_word = scalar_word(32'sd222);

   // IDLE between two RAMPs: no samples are emitted during the wait, and the
   // next ramp starts correctly after the timed gap.
   step = calc_step(-32'sd300, 32'sd300, LONG_POS_DURATION);
   cmd = make_cmd(32'sd300, -32'sd300, LONG_POS_DURATION, step, OP_RAMP, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "pre-idle ramp");
   recv_ramp_checked(-32'sd300, 32'sd300, LONG_POS_DURATION, step, "pre-idle ramp", 1);
   current_hold_word = scalar_word(32'sd300);

   cmd = make_cmd(32'sd0, 32'sd0, IDLE_SLOW_CYCLES, 32'sd0, OP_IDLE, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "idle between ramps");
   check_idle_interval(IDLE_SLOW_CYCLES, current_hold_word, "idle between ramps");

   step = calc_step(32'sd300, -32'sd600, LONG_POS_DURATION);
   cmd = make_cmd(-32'sd600, 32'sd300, LONG_POS_DURATION, step, OP_RAMP, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "post-idle ramp");
   recv_ramp_checked(32'sd300, -32'sd600, LONG_POS_DURATION, step, "post-idle ramp", -1);
   current_hold_word = scalar_word(-32'sd600);

   // RAMP with output backpressure and data stability check.
   step = calc_step(32'sd0, 32'sd96, LONG_NEG_DURATION);
   cmd = make_cmd(32'sd96, 32'sd0, LONG_NEG_DURATION, step, OP_RAMP, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "backpressure ramp");

   wait (m_axis_tvalid === 1'b1);
   frozen_word = m_axis_tdata;
   expected = expected_ramp_word(32'sd0, 32'sd96, LONG_NEG_DURATION, step, 0);
   if (frozen_word !== expected)
      fail("unexpected first ramp word before backpressure release");

   repeat (4) begin
      @(posedge aclk);
      if (m_axis_tdata !== frozen_word)
         fail("m_axis_tdata changed while m_axis_tvalid=1 and m_axis_tready=0");
   end

   recv_word(expected, "backpressure ramp base=0");
   for (bp_base = N_DDS; bp_base < LONG_NEG_DURATION; bp_base = bp_base + N_DDS) begin
      recv_word(expected_ramp_word(32'sd0, 32'sd96, LONG_NEG_DURATION, step, bp_base),
                $sformatf("backpressure ramp base=%0d", bp_base));
   end
   current_hold_word = scalar_word(32'sd96);

   // Back-to-back command behavior: a SET command is held valid while a ramp is busy.
   step = calc_step(32'sd10, 32'sd70, 32'd8);
   cmd = make_cmd(32'sd70, 32'sd10, 32'd8, step, OP_RAMP, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "back-to-back ramp");

   @(negedge aclk);
   s_axis_tdata = make_cmd(32'sd77, 32'sd0, 32'd0, 32'sd0, OP_SET, 1'b0, 1'b0);
   s_axis_tvalid = 1'b1;
   m_axis_tready = 1'b0;

   repeat (2) begin
      @(posedge aclk);
      if (s_axis_tready !== 1'b0)
         fail("s_axis_tready should stay low while ramp is busy");
   end

   recv_word(expected_ramp_word(32'sd10, 32'sd70, 32'd8, step, 0), "back-to-back ramp base=0");
   if (s_axis_tready !== 1'b0)
      fail("s_axis_tready went high before ramp completed");
   recv_word(expected_ramp_word(32'sd10, 32'sd70, 32'd8, step, N_DDS), "back-to-back ramp base=4");
   current_hold_word = scalar_word(32'sd70);
   accept_pending_with_hold(current_hold_word, "back-to-back set accept");

   expected = scalar_word(32'sd77);
   recv_word(expected, "back-to-back set output");
   current_hold_word = expected;

   // Saturation behavior.
   cmd = make_cmd(32'sd40000, 32'sd0, 32'd0, 32'sd0, OP_SET, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "positive saturation");
   expected = scalar_word(32'sd40000);
   recv_word(expected, "positive saturation");
   current_hold_word = expected;

   cmd = make_cmd(-32'sd40000, 32'sd0, 32'd0, 32'sd0, OP_SET, 1'b1, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "negative saturation zero hold");
   expected = scalar_word(-32'sd40000);
   recv_word(expected, "negative saturation zero hold");
   current_hold_word = scalar_word(32'sd0);

   // Verify zero-hold after the last command.
   recv_word(current_hold_word, "zero hold after command");

   repeat (4) @(posedge aclk);
   $fclose(fd);

   if (errors == 0)
      $display("PASS: axis_awg_tuning_v1 unit test completed");

   $finish;
end

endmodule

`default_nettype wire
