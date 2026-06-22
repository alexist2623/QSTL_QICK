`timescale 1ns/1ps
`default_nettype none

module tb_simple();

localparam int N_DDS = 16;
localparam int B = 16;
localparam int FRAC = 16;
localparam int CMD_WIDTH = 160;
localparam int OUT_WIDTH = N_DDS*B;
localparam real ACLK_PERIOD_NS = 10.0;
localparam real DBG_SAMPLE_STEP_NS = ACLK_PERIOD_NS / 16.0;

localparam logic [1:0] OP_NOP  = 2'b00;
localparam logic [1:0] OP_SET  = 2'b01;
localparam logic [1:0] OP_RAMP = 2'b10;
localparam logic [1:0] OP_IDLE = 2'b11;

localparam logic signed [31:0] IGNORED_CMD_STEP = 32'sh1357_2468;

logic                   aresetn;
logic                   aclk;
logic [CMD_WIDTH-1:0]   s_axis_tdata;
logic                   s_axis_tvalid;
wire                    s_axis_tready;
wire [OUT_WIDTH-1:0]    m_axis_tdata;
wire                    m_axis_tvalid;
logic                   m_axis_tready;

logic signed [B-1:0]    dbg_axis_lane_sample [0:N_DDS-1];

logic                   dbg_sample_x16_clk;
logic                   dbg_sample_x16_valid;
logic signed [B-1:0]    dbg_sample_x16_tdata;
int unsigned            dbg_sample_x16_lane;
int unsigned            dbg_sample_x16_word;
int unsigned            dbg_sample_x16_index;

int                     fd;
int                     fd_fast_simple;
int                     checked_word;
bit                     have_hold;
logic [OUT_WIDTH-1:0]   current_hold_word;

typedef struct {
   logic [OUT_WIDTH-1:0] word;
   int unsigned          word_index;
} dbg_simple_word_t;

dbg_simple_word_t       dbg_simple_words[$];
dbg_simple_word_t       dbg_simple_word_push;
dbg_simple_word_t       dbg_simple_word_pop;

event                   dbg_simple_word_ev;
int unsigned            dbg_simple_slow_word_count;
wire                    dbg_simple_word_accept;

assign dbg_simple_word_accept = m_axis_tvalid;

axis_awg_tuning_v1
   #(
      .N_DDS     (N_DDS    ),
      .B         (B        ),
      .FRAC      (FRAC     ),
      .CMD_WIDTH (CMD_WIDTH)
   )
   DUT
   (
      .aresetn          (aresetn       ),
      .aclk             (aclk          ),
      .s_axis_tdata     (s_axis_tdata  ),
      .s_axis_tvalid    (s_axis_tvalid ),
      .s_axis_tready    (s_axis_tready ),
      .m_axis_tdata     (m_axis_tdata  ),
      .m_axis_tvalid    (m_axis_tvalid ),
      .m_axis_tready    (m_axis_tready )
   );

// RFDC/PG269-style lane order:
// m_axis_tdata[15:0]     = earliest sample in this slow AXIS word.
// m_axis_tdata[31:16]    = next sample.
// ...
// m_axis_tdata[255:240]  = latest sample in this slow AXIS word.
//
// dbg_sample_x16_tdata is testbench-only waveform/debug logic.
// It serializes each accepted 256-bit output word into 16 signed 16-bit samples.
// It does not drive DUT logic.
genvar dbg_lane_i;
generate
   for (dbg_lane_i = 0; dbg_lane_i < N_DDS; dbg_lane_i = dbg_lane_i + 1) begin : GEN_DBG_AXIS_LANES_SIMPLE
      assign dbg_axis_lane_sample[dbg_lane_i] = $signed(m_axis_tdata[B*dbg_lane_i +: B]);
   end
endgenerate

initial begin
   if (B != 16)
      $fatal(1, "tb_simple x16 debug stream expects B=16, got B=%0d", B);
   if (N_DDS != 16)
      $fatal(1, "tb_simple x16 debug stream expects N_DDS=16, got N_DDS=%0d", N_DDS);
end

always begin
   aclk = 1'b0;
   #5;
   aclk = 1'b1;
   #5;
end

initial begin
   dbg_sample_x16_clk = 1'b0;
   forever #(DBG_SAMPLE_STEP_NS/2.0) dbg_sample_x16_clk = ~dbg_sample_x16_clk;
end

initial begin
   $dumpfile("tb_simple.vcd");
   $dumpvars(0, tb_simple);
end

always @(posedge aclk) begin
   #1;
   if (aresetn) begin
      if (s_axis_tready !== 1'b1)
         $fatal(1, "s_axis_tready dropped");
      if (m_axis_tvalid !== 1'b1)
         $fatal(1, "m_axis_tvalid dropped");
   end
end

always @(posedge aclk) begin
   if (!aresetn) begin
      dbg_simple_slow_word_count <= 0;
      dbg_simple_words.delete();
   end
   else if (dbg_simple_word_accept) begin
      dbg_simple_word_push.word = m_axis_tdata;
      dbg_simple_word_push.word_index = dbg_simple_slow_word_count;
      dbg_simple_words.push_back(dbg_simple_word_push);
      dbg_simple_slow_word_count <= dbg_simple_slow_word_count + 1;
      -> dbg_simple_word_ev;
   end
end

function automatic logic [CMD_WIDTH-1:0] make_cmd;
   input logic signed [31:0] target;
   input logic signed [31:0] start_or_reserved;
   input logic [31:0] duration;
   input logic signed [31:0] step_or_reserved;
   input logic [1:0] opcode;
   input logic hold_zero;
   input logic clear;
   logic [CMD_WIDTH-1:0] cmd;
   begin
      cmd = {CMD_WIDTH{1'b0}};
      cmd[31:0]    = target;
      cmd[63:32]   = start_or_reserved;
      cmd[95:64]   = duration;
      cmd[127:96]  = step_or_reserved;
      cmd[145:144] = opcode;
      cmd[146]     = hold_zero;
      cmd[148]     = clear;
      make_cmd = cmd;
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

function automatic logic signed [31:0] calc_step;
   input logic signed [31:0] start_value;
   input logic signed [31:0] target_value;
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
         delta = target_value - start_value;
         numerator = delta <<< FRAC;
         denominator = duration - 1;
         quotient = numerator / denominator;
         calc_step = quotient[31:0];
      end
   end
endfunction

function automatic logic [OUT_WIDTH-1:0] expected_ramp_word;
   input logic signed [31:0] start_value;
   input logic signed [31:0] target_value;
   input logic [31:0] duration;
   input logic signed [31:0] step;
   input int unsigned base_index;
   logic [OUT_WIDTH-1:0] word;
   longint signed fixed_value;
   longint signed int_value;
   int unsigned sample_index;
   begin
      word = {OUT_WIDTH{1'b0}};

      for (int i = 0; i < N_DDS; i = i + 1) begin
         sample_index = base_index + i;

         if (duration <= 1 || sample_index >= duration - 1) begin
            word[i*B +: B] = sat_int64(target_value);
         end
         else begin
            fixed_value = (longint'(start_value) <<< FRAC) + (longint'(step) * sample_index);
            int_value = fixed_value >>> FRAC;
            word[i*B +: B] = sat_int64(int_value);
         end
      end

      expected_ramp_word = word;
   end
endfunction

task automatic emit_dbg_sample_word_simple;
   input logic [OUT_WIDTH-1:0] word;
   input int unsigned word_index;

   int unsigned lane;
   logic signed [B-1:0] lane_value;

   begin
      #0.001;

      for (lane = 0; lane < N_DDS; lane = lane + 1) begin
         if (lane != 0)
            #(DBG_SAMPLE_STEP_NS);

         lane_value = $signed(word[B*lane +: B]);

         dbg_sample_x16_valid = 1'b1;
         dbg_sample_x16_tdata = lane_value;
         dbg_sample_x16_lane = lane;
         dbg_sample_x16_word = word_index;
         dbg_sample_x16_index = word_index*N_DDS + lane;

         if (fd_fast_simple != 0)
            $fwrite(fd_fast_simple, "%0d,%0d,%0d,%0d\n",
                    dbg_sample_x16_index,
                    dbg_sample_x16_word,
                    dbg_sample_x16_lane,
                    dbg_sample_x16_tdata);
      end

      #(DBG_SAMPLE_STEP_NS);
      dbg_sample_x16_valid = 1'b0;
   end
endtask

initial begin
   dbg_sample_x16_valid = 1'b0;
   dbg_sample_x16_tdata = '0;
   dbg_sample_x16_lane = 0;
   dbg_sample_x16_word = 0;
   dbg_sample_x16_index = 0;

   forever begin
      if (dbg_simple_words.size() == 0)
         @dbg_simple_word_ev;

      while (dbg_simple_words.size() != 0) begin
         dbg_simple_word_pop = dbg_simple_words.pop_front();
         emit_dbg_sample_word_simple(dbg_simple_word_pop.word,
                                     dbg_simple_word_pop.word_index);
      end
   end
end

task automatic write_checked_word;
   input logic [OUT_WIDTH-1:0] word;
   input string tag;
   logic signed [B-1:0] lane_value;
   begin
      for (int i = 0; i < N_DDS; i = i + 1) begin
         lane_value = word[i*B +: B];
         $fwrite(fd, "%s,%0d,%0d,%0d\n", tag, checked_word, i, lane_value);
      end
      checked_word++;
   end
endtask

task automatic fail_mismatch;
   input string tag;
   input logic [OUT_WIDTH-1:0] expected;
   begin
      $display("ERROR: %s mismatch at t=%0t", tag, $time);
      $display("Expected %h", expected);
      $display("Actual   %h", m_axis_tdata);
      $fatal(1);
   end
endtask

task automatic check_word;
   input logic [OUT_WIDTH-1:0] expected;
   input string tag;
   begin
      if (m_axis_tdata !== expected)
         fail_mismatch(tag, expected);

      write_checked_word(m_axis_tdata, tag);
   end
endtask

task automatic send_cmd;
   input logic [CMD_WIDTH-1:0] cmd;
   input bit expect_hold;
   input logic [OUT_WIDTH-1:0] hold_word;
   input string tag;
   begin
      @(negedge aclk);
      s_axis_tdata = cmd;
      s_axis_tvalid = 1'b1;

      do begin
         @(posedge aclk);

         if (expect_hold && m_axis_tvalid && m_axis_tready)
            check_word(hold_word, {tag, " old hold during command accept"});
      end while (!(s_axis_tvalid && s_axis_tready));

      @(negedge aclk);
      s_axis_tvalid = 1'b0;
      s_axis_tdata = {CMD_WIDTH{1'b0}};
   end
endtask

task automatic send_cmd_and_check_word;
   input logic [CMD_WIDTH-1:0] cmd;
   input logic [OUT_WIDTH-1:0] expected;
   input string tag;
   begin
      @(negedge aclk);
      s_axis_tdata = cmd;
      s_axis_tvalid = 1'b1;

      @(posedge aclk);
      if (s_axis_tready !== 1'b1)
         $fatal(1, "%s saw s_axis_tready low", tag);
      if (m_axis_tvalid !== 1'b1)
         $fatal(1, "%s saw m_axis_tvalid low", tag);
      check_word(expected, tag);

      #1;
      s_axis_tvalid = 1'b0;
      s_axis_tdata = {CMD_WIDTH{1'b0}};
   end
endtask

task automatic recv_word;
   input logic [OUT_WIDTH-1:0] expected;
   input string tag;
   begin
      do begin
         @(posedge aclk);
      end while (!(m_axis_tvalid && m_axis_tready));

      check_word(expected, tag);
   end
endtask

task automatic check_next_stream_word;
   input logic [OUT_WIDTH-1:0] expected;
   input string tag;
   begin
      @(posedge aclk);
      if (m_axis_tvalid !== 1'b1)
         $fatal(1, "%s saw m_axis_tvalid low", tag);
      check_word(expected, tag);
   end
endtask

task automatic check_hold_words;
   input logic signed [31:0] hold_value;
   input int unsigned count;
   input string tag;
   logic [OUT_WIDTH-1:0] expected;
   begin
      expected = scalar_word(hold_value);
      for (int i = 0; i < count; i = i + 1)
         recv_word(expected, $sformatf("%s word %0d", tag, i));
   end
endtask

task automatic check_ramp;
   input logic signed [31:0] start_value;
   input logic signed [31:0] target_value;
   input logic [31:0] duration;
   input string tag;
   logic signed [31:0] step;
   logic [OUT_WIDTH-1:0] expected;
   logic signed [B-1:0] lane_value;
   logic [B-1:0] start_sample;
   logic [B-1:0] target_sample;
   int direction;
   int unsigned base_index;
   int unsigned lane_index;
   int unsigned final_lane;
   longint signed sample_value;
   longint signed previous_value;
   bit have_previous;

   begin
      step = calc_step(start_value, target_value, duration);
      start_sample = sat_int64(start_value);
      target_sample = sat_int64(target_value);
      direction = (target_value > start_value) ? 1 : ((target_value < start_value) ? -1 : 0);
      base_index = 0;
      previous_value = 0;
      have_previous = 1'b0;

      while (base_index < duration || base_index == 0) begin
         expected = expected_ramp_word(start_value, target_value, duration, step, base_index);
         recv_word(expected, $sformatf("%s base=%0d", tag, base_index));

         if (base_index == 0 && m_axis_tdata[0 +: B] !== start_sample)
            $fatal(1, "%s first ramp sample did not equal start value", tag);

         if (base_index + N_DDS >= duration) begin
            final_lane = (duration <= 1) ? 0 : ((duration - 1) - base_index);
            if (m_axis_tdata[final_lane*B +: B] !== target_sample)
               $fatal(1, "%s final ramp sample did not equal target value", tag);
         end

         for (int i = 0; i < N_DDS; i = i + 1) begin
            lane_index = base_index + i;
            if (lane_index < duration) begin
               lane_value = m_axis_tdata[i*B +: B];
               sample_value = lane_value;

               if (have_previous && direction > 0 && sample_value < previous_value)
                  $fatal(1, "%s ramp decreased at scalar sample %0d", tag, lane_index);

               if (have_previous && direction < 0 && sample_value > previous_value)
                  $fatal(1, "%s ramp increased at scalar sample %0d", tag, lane_index);

               previous_value = sample_value;
               have_previous = 1'b1;
            end
         end

         if (duration <= N_DDS)
            base_index = duration;
         else
            base_index = base_index + N_DDS;
      end

      check_hold_words(target_value, 3, {tag, " final hold"});
   end
endtask

initial begin
   logic [CMD_WIDTH-1:0] cmd;
   logic signed [31:0] step;
   logic [OUT_WIDTH-1:0] expected;

   fd = $fopen("dout_awg_tuning_simple.csv", "w");
   if (fd == 0)
      $fatal(1, "could not open dout_awg_tuning_simple.csv");
   $fwrite(fd, "tag,word,lane,value\n");

   fd_fast_simple = $fopen("dout_awg_tuning_simple_fast.csv", "w");
   if (fd_fast_simple == 0)
      $fatal(1, "could not open dout_awg_tuning_simple_fast.csv");
   $fwrite(fd_fast_simple, "sample_index,slow_word,lane,value\n");

   checked_word = 0;
   have_hold = 1'b0;
   current_hold_word = {OUT_WIDTH{1'b0}};
   aresetn = 1'b0;
   s_axis_tdata = {CMD_WIDTH{1'b0}};
   s_axis_tvalid = 1'b0;
   m_axis_tready = 1'b1;

   repeat (8) begin
      @(posedge aclk);
      #1;
      if (m_axis_tvalid !== 1'b0)
         $fatal(1, "m_axis_tvalid should be low during reset");
      if (m_axis_tdata !== {OUT_WIDTH{1'b0}})
         $fatal(1, "m_axis_tdata should be zero during reset");
   end

   aresetn = 1'b1;
   @(posedge aclk);
   #1;
   if (s_axis_tready !== 1'b1)
      $fatal(1, "s_axis_tready should be high after reset");
   if (m_axis_tvalid !== 1'b1)
      $fatal(1, "m_axis_tvalid should be high after reset");
   if (m_axis_tdata !== {OUT_WIDTH{1'b0}})
      $fatal(1, "m_axis_tdata should hold zero after reset");
   current_hold_word = scalar_word(32'sd0);
   have_hold = 1'b1;
   check_hold_words(32'sd0, 2, "RESET HOLD 0");

   cmd = make_cmd(32'sd1000, 32'sd0, 32'd0, 32'sd0, OP_SET, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "SET 1000");
   current_hold_word = scalar_word(32'sd1000);
   recv_word(current_hold_word, "SET 1000 output");
   check_hold_words(32'sd1000, 3, "HOLD 1000");
   have_hold = 1'b1;

   step = calc_step(32'sd1000, 32'sd2000, 32'd64);
   cmd = make_cmd(32'sd2000, -32'sd30000, 32'd64, IGNORED_CMD_STEP, OP_RAMP, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "RAMP 1000 to 2000");
   expected = expected_ramp_word(32'sd1000, 32'sd2000, 32'd64, step, 0);
   recv_word(expected, "RAMP 1000 to 2000 base=0");

   cmd = make_cmd(-32'sd1234, 32'sd0, 32'd0, 32'sd0, OP_SET, 1'b0, 1'b0);
   expected = expected_ramp_word(32'sd1000, 32'sd2000, 32'd64, step, N_DDS);
   send_cmd_and_check_word(cmd, expected, "DROP SET during RAMP base=16");

   cmd = make_cmd(32'sd3000, -32'sd111, 32'd32, IGNORED_CMD_STEP, OP_RAMP, 1'b0, 1'b0);
   expected = expected_ramp_word(32'sd1000, 32'sd2000, 32'd64, step, 2*N_DDS);
   send_cmd_and_check_word(cmd, expected, "DROP RAMP during RAMP base=32");

   expected = expected_ramp_word(32'sd1000, 32'sd2000, 32'd64, step, 3*N_DDS);
   recv_word(expected, "RAMP 1000 to 2000 base=48");
   check_hold_words(32'sd2000, 3, "RAMP 1000 to 2000 final hold");
   current_hold_word = scalar_word(32'sd2000);

   cmd = make_cmd(-32'sd500, 32'sd0, 32'd0, 32'sd0, OP_SET, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "SET -500");
   current_hold_word = scalar_word(-32'sd500);
   recv_word(current_hold_word, "SET -500 output");
   check_hold_words(-32'sd500, 3, "HOLD -500");

   step = calc_step(-32'sd500, -32'sd1500, 32'd64);
   cmd = make_cmd(-32'sd1500, 32'sd12345, 32'd64, IGNORED_CMD_STEP, OP_RAMP, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "RAMP -500 to -1500");
   m_axis_tready = 1'b0;
   expected = expected_ramp_word(-32'sd500, -32'sd1500, 32'd64, step, 0);
   check_next_stream_word(expected, "RAMP -500 to -1500 base=0 ready low");
   expected = expected_ramp_word(-32'sd500, -32'sd1500, 32'd64, step, N_DDS);
   check_next_stream_word(expected, "RAMP -500 to -1500 base=16 ready low");
   m_axis_tready = 1'b1;
   expected = expected_ramp_word(-32'sd500, -32'sd1500, 32'd64, step, 2*N_DDS);
   recv_word(expected, "RAMP -500 to -1500 base=32 ready restored");
   expected = expected_ramp_word(-32'sd500, -32'sd1500, 32'd64, step, 3*N_DDS);
   recv_word(expected, "RAMP -500 to -1500 base=48 ready restored");
   check_hold_words(-32'sd1500, 3, "RAMP -500 to -1500 final hold");
   current_hold_word = scalar_word(-32'sd1500);

   cmd = make_cmd(32'sd9999, 32'sd0, 32'd64, 32'sd0, OP_IDLE, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "OP_IDLE no-op");
   check_hold_words(-32'sd1500, 2, "OP_IDLE no-op hold");

   cmd = make_cmd(32'sd123, 32'sd0, 32'd0, 32'sd0, OP_SET, 1'b1, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "SET 123 zero hold");
   recv_word(scalar_word(32'sd123), "SET 123 zero-hold output");
   current_hold_word = scalar_word(32'sd0);
   check_hold_words(32'sd0, 2, "SET zero-hold final hold");

   cmd = make_cmd(32'sd0, 32'sd0, 32'd0, 32'sd0, OP_SET, 1'b0, 1'b0);
   send_cmd(cmd, have_hold, current_hold_word, "SET 0");
   current_hold_word = scalar_word(32'sd0);
   recv_word(current_hold_word, "SET 0 output");
   check_hold_words(32'sd0, 2, "HOLD 0");

   $fclose(fd);
   $fclose(fd_fast_simple);
   $display("PASS: tb_simple axis_awg_tuning_v1 continuous SET/RAMP/drop test completed");
   $finish;
end

endmodule

`default_nettype wire
