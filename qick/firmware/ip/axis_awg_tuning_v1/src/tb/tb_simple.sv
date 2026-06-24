`timescale 1ns/1ps
`default_nettype none

module tb_simple
   #(
      parameter int EXTRA_Y_PIPE_STAGES = 1
   )
   ();

localparam int N_PTS = 16;
localparam int B = 16;
localparam int FRAC = 16;
localparam int CMD_WIDTH = 160;
localparam int STEP_WIDTH = 24;
localparam int DURATION_WIDTH = 23;
localparam int FIXED_WIDTH = 48;
localparam int OUT_WIDTH = N_PTS*B;
localparam real ACLK_PERIOD_NS = 10.0;
localparam real S_AXI_ACLK_PERIOD_NS = 14.0;
localparam real DBG_SAMPLE_STEP_NS = ACLK_PERIOD_NS / 16.0;

localparam logic [5:0] AXI_CURRENT_VALUE_ADDR = 6'h00;
localparam logic [5:0] AXI_STATUS_ADDR        = 6'h04;

localparam logic [1:0] OP_NOP  = 2'b00;
localparam logic [1:0] OP_SET  = 2'b01;
localparam logic [1:0] OP_RAMP = 2'b10;
localparam logic [1:0] OP_IDLE = 2'b11;

localparam int RAMP_STARTUP_LATENCY_CYCLES = EXTRA_Y_PIPE_STAGES + 4;
localparam int RAMP_FILL_WORDS_AFTER_COMMAND = RAMP_STARTUP_LATENCY_CYCLES - 1;

logic                   aresetn;
logic                   aclk;
logic                   s_axi_aclk;
logic                   s_axi_aresetn;
logic [5:0]             s_axi_awaddr;
logic [2:0]             s_axi_awprot;
logic                   s_axi_awvalid;
wire                    s_axi_awready;
logic [31:0]            s_axi_wdata;
logic [3:0]             s_axi_wstrb;
logic                   s_axi_wvalid;
wire                    s_axi_wready;
wire [1:0]              s_axi_bresp;
wire                    s_axi_bvalid;
logic                   s_axi_bready;
logic [5:0]             s_axi_araddr;
logic [2:0]             s_axi_arprot;
logic                   s_axi_arvalid;
wire                    s_axi_arready;
wire [31:0]             s_axi_rdata;
wire [1:0]              s_axi_rresp;
wire                    s_axi_rvalid;
logic                   s_axi_rready;
logic [CMD_WIDTH-1:0]   s_axis_tdata;
logic                   s_axis_tvalid;
wire                    s_axis_tready;
wire [OUT_WIDTH-1:0]    m_axis_tdata;
wire                    m_axis_tvalid;
logic                   m_axis_tready;

logic signed [B-1:0]    dbg_axis_lane_sample [0:N_PTS-1];

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
logic signed [31:0]     current_value;
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
      .N_PTS     (N_PTS    ),
      .B         (B        ),
      .FRAC      (FRAC     ),
      .CMD_WIDTH (CMD_WIDTH),
      .STEP_WIDTH (STEP_WIDTH),
      .DURATION_WIDTH (DURATION_WIDTH),
      .FIXED_WIDTH (FIXED_WIDTH),
      .EXTRA_Y_PIPE_STAGES (EXTRA_Y_PIPE_STAGES)
   )
   DUT
   (
      .s_axi_aclk       (s_axi_aclk    ),
      .s_axi_aresetn    (s_axi_aresetn ),
      .s_axi_awaddr     (s_axi_awaddr  ),
      .s_axi_awprot     (s_axi_awprot  ),
      .s_axi_awvalid    (s_axi_awvalid ),
      .s_axi_awready    (s_axi_awready ),
      .s_axi_wdata      (s_axi_wdata   ),
      .s_axi_wstrb      (s_axi_wstrb   ),
      .s_axi_wvalid     (s_axi_wvalid  ),
      .s_axi_wready     (s_axi_wready  ),
      .s_axi_bresp      (s_axi_bresp   ),
      .s_axi_bvalid     (s_axi_bvalid  ),
      .s_axi_bready     (s_axi_bready  ),
      .s_axi_araddr     (s_axi_araddr  ),
      .s_axi_arprot     (s_axi_arprot  ),
      .s_axi_arvalid    (s_axi_arvalid ),
      .s_axi_arready    (s_axi_arready ),
      .s_axi_rdata      (s_axi_rdata   ),
      .s_axi_rresp      (s_axi_rresp   ),
      .s_axi_rvalid     (s_axi_rvalid  ),
      .s_axi_rready     (s_axi_rready  ),
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
   for (dbg_lane_i = 0; dbg_lane_i < N_PTS; dbg_lane_i = dbg_lane_i + 1) begin : GEN_DBG_AXIS_LANES_SIMPLE
      assign dbg_axis_lane_sample[dbg_lane_i] = $signed(m_axis_tdata[B*dbg_lane_i +: B]);
   end
endgenerate

initial begin
   if (B != 16)
      $fatal(1, "tb_simple x16 debug stream expects B=16, got B=%0d", B);
   if (N_PTS != 16)
      $fatal(1, "tb_simple x16 debug stream expects N_PTS=16, got N_PTS=%0d", N_PTS);
end

always begin
   aclk = 1'b0;
   #5;
   aclk = 1'b1;
   #5;
end

initial begin
   s_axi_aclk = 1'b0;
   forever #(S_AXI_ACLK_PERIOD_NS/2.0) s_axi_aclk = ~s_axi_aclk;
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
      if ($isunknown(m_axis_tdata))
         $fatal(1, "m_axis_tdata contains X/Z");
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
      if (duration >= (32'd1 << DURATION_WIDTH))
         $fatal(1, "duration %0d does not fit in %0d bits", duration, DURATION_WIDTH);
      if (step_or_reserved < -(32'sd1 <<< (STEP_WIDTH-1)) ||
          step_or_reserved > ((32'sd1 <<< (STEP_WIDTH-1)) - 32'sd1))
         $fatal(1, "step %0d does not fit in signed %0d bits",
                step_or_reserved, STEP_WIDTH);

      cmd = {CMD_WIDTH{1'b0}};
      cmd[31:0]    = target;
      cmd[63:32]   = start_or_reserved;
      cmd[64 +: DURATION_WIDTH] = duration[DURATION_WIDTH-1:0];
      cmd[96 +: STEP_WIDTH] = step_or_reserved[STEP_WIDTH-1:0];
      cmd[145:144] = opcode;
      cmd[146]     = hold_zero;
      cmd[148]     = clear;
      make_cmd = cmd;
   end
endfunction

function automatic logic signed [31:0] cmd_step_field;
   input logic [CMD_WIDTH-1:0] cmd;
   logic signed [STEP_WIDTH-1:0] step_field;
   begin
      step_field = cmd[96 +: STEP_WIDTH];
      cmd_step_field = step_field;
   end
endfunction

function automatic logic [31:0] cmd_duration_field;
   input logic [CMD_WIDTH-1:0] cmd;
   begin
      cmd_duration_field = {{(32-DURATION_WIDTH){1'b0}}, cmd[64 +: DURATION_WIDTH]};
   end
endfunction

function automatic logic [B-1:0] sat_int64;
   input longint signed value;
   longint signed max_sample;
   longint signed min_sample;
   logic signed [B-1:0] sample;
   logic [B-1:0] align_mask;
   begin
      max_sample = ((64'sd1 <<< (B-1)) - 64'sd1) & ~64'sd3;
      min_sample = -(64'sd1 <<< (B-1));
      align_mask = {{(B-2){1'b1}}, 2'b00};

      if (value > max_sample)
         sample = max_sample[B-1:0];
      else if (value < min_sample)
         sample = min_sample[B-1:0];
      else
         sample = value[B-1:0];

      sat_int64 = sample & align_mask;
   end
endfunction

function automatic logic [OUT_WIDTH-1:0] scalar_word;
   input logic signed [31:0] value;
   logic [OUT_WIDTH-1:0] word;
   logic [B-1:0] sample;
   begin
      sample = sat_int64(value);
      word = {OUT_WIDTH{1'b0}};
      for (int i = 0; i < N_PTS; i = i + 1)
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
         if (quotient < -(64'sd1 <<< (STEP_WIDTH-1)) ||
             quotient > ((64'sd1 <<< (STEP_WIDTH-1)) - 64'sd1))
            $fatal(1, "calc_step result %0d does not fit in signed %0d bits",
                   quotient, STEP_WIDTH);
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

      for (int i = 0; i < N_PTS; i = i + 1) begin
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

      for (lane = 0; lane < N_PTS; lane = lane + 1) begin
         if (lane != 0)
            #(DBG_SAMPLE_STEP_NS);

         lane_value = $signed(word[B*lane +: B]);

         dbg_sample_x16_valid = 1'b1;
         dbg_sample_x16_tdata = lane_value;
         dbg_sample_x16_lane = lane;
         dbg_sample_x16_word = word_index;
         dbg_sample_x16_index = word_index*N_PTS + lane;

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
      for (int i = 0; i < N_PTS; i = i + 1) begin
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

task automatic check_no_unknown_word;
   input logic [OUT_WIDTH-1:0] word;
   input string tag;
   begin
      if ($isunknown(word))
         $fatal(1, "%s contains X/Z", tag);
   end
endtask

task automatic check_dac_lsb_zero;
   input logic [OUT_WIDTH-1:0] word;
   input string tag;
   begin
      for (int i = 0; i < N_PTS; i = i + 1) begin
         if (word[i*B +: 2] !== 2'b00)
            $fatal(1, "%s lane %0d lower two DAC bits are not zero: %b",
                   tag, i, word[i*B +: 2]);
      end
   end
endtask

task automatic check_word;
   input logic [OUT_WIDTH-1:0] expected;
   input string tag;
   begin
      check_no_unknown_word(m_axis_tdata, tag);
      check_dac_lsb_zero(m_axis_tdata, tag);
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
      #1;
      check_word(expected, tag);

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

      #1;
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
      #1;
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

task automatic check_ramp_startup_latency;
   input logic [OUT_WIDTH-1:0] hold_word_expected;
   input string tag;
   begin
      for (int i = 0; i < RAMP_FILL_WORDS_AFTER_COMMAND; i = i + 1)
         recv_word(hold_word_expected,
                   $sformatf("%s pipeline fill word %0d", tag, i));
   end
endtask

task automatic check_ramp;
   input logic signed [31:0] start_value;
   input logic signed [31:0] target_value;
   input logic [31:0] duration;
   input logic signed [31:0] step;
   input string tag;
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

         if (base_index + N_PTS >= duration) begin
            final_lane = (duration <= 1) ? 0 : ((duration - 1) - base_index);
            if (m_axis_tdata[final_lane*B +: B] !== target_sample)
               $fatal(1, "%s final ramp sample did not equal target value", tag);
         end

         for (int i = 0; i < N_PTS; i = i + 1) begin
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

         if (duration <= N_PTS)
            base_index = duration;
         else
            base_index = base_index + N_PTS;
      end

      check_hold_words(target_value, 3, {tag, " final hold"});
   end
endtask

task automatic check_ramp_word_properties;
   input logic signed [31:0] start_value;
   input logic signed [31:0] target_value;
   input logic [31:0] duration;
   input int unsigned base_index;
   input string tag;
   inout longint signed previous_value;
   inout bit have_previous;

   logic signed [B-1:0] lane_value;
   logic [B-1:0] start_sample;
   logic [B-1:0] target_sample;
   int direction;
   int unsigned lane_index;
   int unsigned final_lane;
   longint signed sample_value;

   begin
      start_sample = sat_int64(start_value);
      target_sample = sat_int64(target_value);
      direction = (target_value > start_value) ? 1 : ((target_value < start_value) ? -1 : 0);

      if (base_index == 0 && duration > 1 && m_axis_tdata[0 +: B] !== start_sample)
         $fatal(1, "%s first ramp sample did not equal tracked start value", tag);

      if (base_index + N_PTS >= duration) begin
         final_lane = (duration <= 1) ? 0 : ((duration - 1) - base_index);
         if (m_axis_tdata[final_lane*B +: B] !== target_sample)
            $fatal(1, "%s final ramp sample did not equal target value", tag);
      end

      for (int i = 0; i < N_PTS; i = i + 1) begin
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
   end
endtask

task automatic axi_write32;
   input logic [5:0] addr;
   input logic [31:0] data;
   input string tag;
   begin
      @(negedge s_axi_aclk);
      s_axi_awaddr  = addr;
      s_axi_awprot  = 3'd0;
      s_axi_awvalid = 1'b1;
      s_axi_wdata   = data;
      s_axi_wstrb   = 4'hF;
      s_axi_wvalid  = 1'b1;
      s_axi_bready  = 1'b0;

      do begin
         @(posedge s_axi_aclk);
      end while (!(s_axi_awready && s_axi_wready));

      @(negedge s_axi_aclk);
      s_axi_awvalid = 1'b0;
      s_axi_wvalid  = 1'b0;
      s_axi_awaddr  = 6'd0;
      s_axi_wdata   = 32'd0;
      s_axi_wstrb   = 4'd0;

      do begin
         @(posedge s_axi_aclk);
      end while (!s_axi_bvalid);

      if (s_axi_bresp !== 2'b00)
         $fatal(1, "%s AXI write BRESP was %b", tag, s_axi_bresp);

      @(negedge s_axi_aclk);
      s_axi_bready = 1'b1;
      @(posedge s_axi_aclk);
      @(negedge s_axi_aclk);
      s_axi_bready = 1'b0;
   end
endtask

task automatic axi_read32;
   input logic [5:0] addr;
   output logic [31:0] data;
   input string tag;
   begin
      @(negedge s_axi_aclk);
      s_axi_araddr  = addr;
      s_axi_arprot  = 3'd0;
      s_axi_arvalid = 1'b1;
      s_axi_rready  = 1'b0;

      do begin
         @(posedge s_axi_aclk);
      end while (!s_axi_arready);

      @(negedge s_axi_aclk);
      s_axi_arvalid = 1'b0;
      s_axi_araddr  = 6'd0;
      s_axi_rready  = 1'b1;

      do begin
         @(posedge s_axi_aclk);
      end while (!s_axi_rvalid);

      data = s_axi_rdata;
      if (s_axi_rresp !== 2'b00)
         $fatal(1, "%s AXI read RRESP was %b", tag, s_axi_rresp);
      if ($isunknown(s_axi_rdata))
         $fatal(1, "%s AXI read returned X/Z", tag);

      @(negedge s_axi_aclk);
      s_axi_rready = 1'b0;
   end
endtask

task automatic axi_wait_current;
   input logic signed [31:0] expected;
   input string tag;
   logic [31:0] data;
   bit matched;
   begin
      matched = 1'b0;
      for (int i = 0; i < 80 && !matched; i = i + 1) begin
         axi_read32(AXI_CURRENT_VALUE_ADDR, data, {tag, " CURRENT_VALUE_REG"});
         if ($signed(data) == expected)
            matched = 1'b1;
         else
            repeat (2) @(posedge s_axi_aclk);
      end

      if (!matched)
         $fatal(1, "%s CURRENT_VALUE_REG did not reach %0d, last=%0d",
                tag, expected, $signed(data));
   end
endtask

task automatic axi_wait_idle_status;
   input string tag;
   logic [31:0] status;
   bit matched;
   begin
      matched = 1'b0;
      for (int i = 0; i < 80 && !matched; i = i + 1) begin
         axi_read32(AXI_STATUS_ADDR, status, {tag, " STATUS_REG"});
         if (status[0] && !status[1] && status[2] && status[3] && status[5])
            matched = 1'b1;
         else
            repeat (2) @(posedge s_axi_aclk);
      end

      if (!matched)
         $fatal(1, "%s STATUS_REG did not report idle/valid/ready/override_seen, last=%h",
                tag, status);
   end
endtask

task automatic wait_output_word;
   input logic [OUT_WIDTH-1:0] expected;
   input string tag;
   bit matched;
   begin
      matched = 1'b0;
      for (int i = 0; i < 80 && !matched; i = i + 1) begin
         @(posedge aclk);
         #1;
         if (m_axis_tvalid && m_axis_tdata === expected) begin
            check_word(expected, tag);
            matched = 1'b1;
         end
      end

      if (!matched)
         fail_mismatch(tag, expected);
   end
endtask

task automatic check_m_axis_tready_ignored;
   begin
      @(negedge aclk);
      m_axis_tready = 1'b0;

      repeat (3) begin
         @(posedge aclk);
         #1;
         if (m_axis_tvalid !== 1'b1)
            $fatal(1, "m_axis_tvalid dropped while m_axis_tready was low");
         check_no_unknown_word(m_axis_tdata, "m_axis_tready ignored");
         if (m_axis_tdata !== current_hold_word)
            fail_mismatch("m_axis_tready ignored hold", current_hold_word);
      end

      @(negedge aclk);
      m_axis_tready = 1'b1;
      check_next_stream_word(current_hold_word, "m_axis_tready ignored recovery");
   end
endtask

task automatic open_output_files;
   begin
      fd = $fopen("dout_awg_tuning_simple.csv", "w");
      if (fd == 0)
         $fatal(1, "could not open dout_awg_tuning_simple.csv");
      $fwrite(fd, "tag,word,lane,value\n");

      fd_fast_simple = $fopen("dout_awg_tuning_simple_fast.csv", "w");
      if (fd_fast_simple == 0)
         $fatal(1, "could not open dout_awg_tuning_simple_fast.csv");
      $fwrite(fd_fast_simple, "sample_index,slow_word,lane,value\n");
   end
endtask

task automatic close_output_files;
   begin
      $fclose(fd);
      $fclose(fd_fast_simple);
   end
endtask

task automatic init_tb_state;
   begin
      checked_word = 0;
      have_hold = 1'b0;
      current_value = 32'sd0;
      current_hold_word = {OUT_WIDTH{1'b0}};
   end
endtask

task automatic reset_dut;
   begin
      aresetn = 1'b0;
      s_axi_aresetn = 1'b0;
      s_axis_tdata = {CMD_WIDTH{1'b0}};
      s_axis_tvalid = 1'b0;
      m_axis_tready = 1'b1;
      s_axi_awaddr = 6'd0;
      s_axi_awprot = 3'd0;
      s_axi_awvalid = 1'b0;
      s_axi_wdata = 32'd0;
      s_axi_wstrb = 4'd0;
      s_axi_wvalid = 1'b0;
      s_axi_bready = 1'b0;
      s_axi_araddr = 6'd0;
      s_axi_arprot = 3'd0;
      s_axi_arvalid = 1'b0;
      s_axi_rready = 1'b0;

      repeat (8) begin
         @(posedge aclk);
         #1;
         if (m_axis_tvalid !== 1'b0)
            $fatal(1, "m_axis_tvalid should be low during reset");
         if (m_axis_tdata !== {OUT_WIDTH{1'b0}})
            $fatal(1, "m_axis_tdata should be zero during reset");
      end

      @(negedge s_axi_aclk);
      s_axi_aresetn = 1'b1;
      @(negedge aclk);
      aresetn = 1'b1;
      @(posedge aclk);
      #1;
      if (s_axis_tready !== 1'b1)
         $fatal(1, "s_axis_tready should be high after reset");
      if (m_axis_tvalid !== 1'b1)
         $fatal(1, "m_axis_tvalid should be high after reset");
      if (m_axis_tdata !== scalar_word(32'sd0))
         $fatal(1, "m_axis_tdata should hold zero after reset");

      current_value = 32'sd0;
      current_hold_word = scalar_word(32'sd0);
      have_hold = 1'b1;
      check_hold_words(32'sd0, 2, "RESET HOLD 0");
      axi_wait_current(32'sd0, "RESET");
   end
endtask

task automatic set_awg;
   input logic signed [31:0] value;

   logic [CMD_WIDTH-1:0] cmd;
   string tag;

   begin
      tag = $sformatf("SET %0d", value);
      cmd = make_cmd(value, 32'sd0, 32'd0, 32'sd0, OP_SET, 1'b0, 1'b0);
      send_cmd_and_check_word(cmd, scalar_word(value), {tag, " output"});

      current_value = value;
      current_hold_word = scalar_word(value);
      have_hold = 1'b1;

      check_hold_words(value, 3, {tag, " hold"});
   end
endtask

task automatic set_awg_zero_hold;
   input logic signed [31:0] value;

   logic [CMD_WIDTH-1:0] cmd;
   string tag;

   begin
      tag = $sformatf("SET %0d zero hold", value);
      cmd = make_cmd(value, 32'sd0, 32'd0, 32'sd0, OP_SET, 1'b1, 1'b0);
      send_cmd_and_check_word(cmd, scalar_word(value), {tag, " output"});

      current_value = 32'sd0;
      current_hold_word = scalar_word(32'sd0);
      have_hold = 1'b1;

      check_hold_words(32'sd0, 2, {tag, " final hold"});
   end
endtask

task automatic ramp_awg;
   input logic signed [31:0] final_value;
   input logic [31:0] ramp_duration;

   logic [CMD_WIDTH-1:0] cmd;
   logic signed [31:0] start_value;
   logic signed [31:0] wrong_start;
   logic signed [31:0] step;
   string tag;

   begin
      start_value = current_value;
      tag = $sformatf("RAMP %0d to %0d duration %0d",
                      start_value, final_value, ramp_duration);
      wrong_start = (start_value == -32'sd30000) ? 32'sd30000 : -32'sd30000;
      step = calc_step(start_value, final_value, ramp_duration);
      if (ramp_duration > 1 && final_value != start_value && step == 32'sd0)
         $fatal(1, "%s command step should be nonzero", tag);
      cmd = make_cmd(final_value, wrong_start, ramp_duration, step, OP_RAMP, 1'b0, 1'b0);
      if (cmd_step_field(cmd) !== step)
         $fatal(1, "%s command step field mismatch", tag);
      if (cmd_duration_field(cmd) !== ramp_duration)
         $fatal(1, "%s command duration field mismatch", tag);

      send_cmd(cmd, have_hold, current_hold_word, tag);
      check_ramp_startup_latency(current_hold_word, tag);
      check_ramp(start_value, final_value, ramp_duration, step, tag);

      current_value = final_value;
      current_hold_word = scalar_word(final_value);
      have_hold = 1'b1;
   end
endtask

task automatic ramp_awg_explicit_step;
   input logic signed [31:0] final_value;
   input logic [31:0] ramp_duration;
   input logic signed [31:0] explicit_step;
   input string tag_suffix;

   logic [CMD_WIDTH-1:0] cmd;
   logic signed [31:0] start_value;
   logic signed [31:0] wrong_start;
   string tag;

   begin
      start_value = current_value;
      tag = $sformatf("RAMP explicit step %s start %0d target %0d duration %0d step %0d",
                      tag_suffix, start_value, final_value, ramp_duration, explicit_step);
      wrong_start = (start_value == -32'sd30000) ? 32'sd30000 : -32'sd30000;
      cmd = make_cmd(final_value, wrong_start, ramp_duration, explicit_step, OP_RAMP, 1'b0, 1'b0);
      if (cmd_step_field(cmd) !== explicit_step)
         $fatal(1, "%s command step field mismatch", tag);
      if (cmd_duration_field(cmd) !== ramp_duration)
         $fatal(1, "%s command duration field mismatch", tag);

      send_cmd(cmd, have_hold, current_hold_word, tag);
      check_ramp_startup_latency(current_hold_word, tag);
      check_ramp(start_value, final_value, ramp_duration, explicit_step, tag);

      current_value = final_value;
      current_hold_word = scalar_word(final_value);
      have_hold = 1'b1;
   end
endtask

task automatic check_command_field_limits;
   logic [CMD_WIDTH-1:0] cmd;
   logic signed [31:0] max_step;
   logic signed [31:0] min_step;
   logic [31:0] max_duration;
   begin
      max_step = (32'sd1 <<< (STEP_WIDTH-1)) - 32'sd1;
      min_step = -(32'sd1 <<< (STEP_WIDTH-1));
      max_duration = (32'd1 << DURATION_WIDTH) - 32'd1;

      cmd = make_cmd(32'sd0, 32'sd0, max_duration, max_step, OP_RAMP, 1'b0, 1'b0);
      if (cmd_step_field(cmd) !== max_step)
         $fatal(1, "max signed 24-bit step field mismatch");
      if (cmd_duration_field(cmd) !== max_duration)
         $fatal(1, "max unsigned 23-bit duration field mismatch");
      if (cmd[95:87] !== 9'd0 || cmd[127:120] !== 8'd0)
         $fatal(1, "ignored high duration/step bits should remain zero");

      cmd = make_cmd(32'sd0, 32'sd0, 32'd1, min_step, OP_RAMP, 1'b0, 1'b0);
      if (cmd_step_field(cmd) !== min_step)
         $fatal(1, "min signed 24-bit step field mismatch");
   end
endtask

task automatic axi_override_current;
   input logic signed [31:0] value;
   input string tag;
   logic [OUT_WIDTH-1:0] expected;
   begin
      expected = scalar_word(value);
      axi_write32(AXI_CURRENT_VALUE_ADDR, value, tag);
      wait_output_word(expected, {tag, " output"});

      current_value = value;
      current_hold_word = expected;
      have_hold = 1'b1;

      axi_wait_current(value, tag);
      axi_wait_idle_status(tag);
      check_hold_words(value, 2, {tag, " hold"});
   end
endtask

task automatic ramp_awg_abort_with_axi_override;
   input logic signed [31:0] aborted_target;
   input logic [31:0] aborted_duration;
   input logic signed [31:0] override_value;
   input logic signed [31:0] next_target;
   input logic [31:0] next_duration;

   logic [CMD_WIDTH-1:0] cmd;
   logic signed [31:0] start_value;
   logic signed [31:0] wrong_start;
   logic signed [31:0] step;
   logic [OUT_WIDTH-1:0] expected;
   longint signed previous_value;
   bit have_previous;
   string tag;

   begin
      start_value = current_value;
      tag = $sformatf("RAMP abort %0d to %0d override %0d",
                      start_value, aborted_target, override_value);
      wrong_start = (start_value == -32'sd30000) ? 32'sd30000 : -32'sd30000;
      step = calc_step(start_value, aborted_target, aborted_duration);
      previous_value = 0;
      have_previous = 1'b0;

      cmd = make_cmd(aborted_target, wrong_start, aborted_duration,
                     step, OP_RAMP, 1'b0, 1'b0);
      if (cmd_step_field(cmd) !== step)
         $fatal(1, "%s command step field mismatch", tag);
      if (cmd_duration_field(cmd) !== aborted_duration)
         $fatal(1, "%s command duration field mismatch", tag);
      send_cmd(cmd, have_hold, current_hold_word, tag);
      check_ramp_startup_latency(current_hold_word, tag);

      expected = expected_ramp_word(start_value, aborted_target,
                                    aborted_duration, step, 0);
      recv_word(expected, {tag, " base=0 before AXI override"});
      check_ramp_word_properties(start_value, aborted_target, aborted_duration,
                                 0, {tag, " base=0 before AXI override"},
                                 previous_value, have_previous);

      axi_override_current(override_value, {tag, " AXI override"});
      ramp_awg(next_target, next_duration);
   end
endtask

task automatic ramp_awg_with_drop_tests;
   input logic signed [31:0] final_value;
   input logic [31:0] ramp_duration;

   logic [CMD_WIDTH-1:0] cmd;
   logic signed [31:0] start_value;
   logic signed [31:0] wrong_start;
   logic signed [31:0] step;
   logic signed [31:0] dropped_step;
   logic [OUT_WIDTH-1:0] expected;
   int unsigned base_index;
   longint signed previous_value;
   bit have_previous;
   string tag;

   begin
      start_value = current_value;
      tag = $sformatf("RAMP %0d to %0d duration %0d with drop tests",
                      start_value, final_value, ramp_duration);

      if (ramp_duration < 3*N_PTS)
         $fatal(1, "%s duration must cover at least three output words for drop tests", tag);

      wrong_start = (start_value == -32'sd30000) ? 32'sd30000 : -32'sd30000;
      step = calc_step(start_value, final_value, ramp_duration);
      previous_value = 0;
      have_previous = 1'b0;

      cmd = make_cmd(final_value, wrong_start, ramp_duration, step, OP_RAMP, 1'b0, 1'b0);
      if (cmd_step_field(cmd) !== step)
         $fatal(1, "%s command step field mismatch", tag);
      if (cmd_duration_field(cmd) !== ramp_duration)
         $fatal(1, "%s command duration field mismatch", tag);
      send_cmd(cmd, have_hold, current_hold_word, tag);
      check_ramp_startup_latency(current_hold_word, tag);

      expected = expected_ramp_word(start_value, final_value, ramp_duration, step, 0);
      recv_word(expected, {tag, " base=0"});
      check_ramp_word_properties(start_value, final_value, ramp_duration, 0,
                                 {tag, " base=0"}, previous_value, have_previous);

      cmd = make_cmd(-32'sd1234, 32'sd0, 32'd0, 32'sd0, OP_SET, 1'b0, 1'b0);
      expected = expected_ramp_word(start_value, final_value, ramp_duration, step, N_PTS);
      send_cmd_and_check_word(cmd, expected, {tag, " DROP SET base=16"});
      check_ramp_word_properties(start_value, final_value, ramp_duration, N_PTS,
                                 {tag, " DROP SET base=16"}, previous_value, have_previous);

      dropped_step = calc_step(start_value, 32'sd3000, 32'd32);
      cmd = make_cmd(32'sd3000, 32'sd111, 32'd32, dropped_step, OP_RAMP, 1'b0, 1'b0);
      expected = expected_ramp_word(start_value, final_value, ramp_duration, step, 2*N_PTS);
      send_cmd_and_check_word(cmd, expected, {tag, " DROP RAMP base=32"});
      check_ramp_word_properties(start_value, final_value, ramp_duration, 2*N_PTS,
                                 {tag, " DROP RAMP base=32"}, previous_value, have_previous);

      for (base_index = 3*N_PTS; base_index < ramp_duration; base_index = base_index + N_PTS) begin
         expected = expected_ramp_word(start_value, final_value, ramp_duration, step, base_index);
         recv_word(expected, $sformatf("%s base=%0d", tag, base_index));
         check_ramp_word_properties(start_value, final_value, ramp_duration, base_index,
                                    $sformatf("%s base=%0d", tag, base_index),
                                    previous_value, have_previous);
      end

      check_hold_words(final_value, 3, {tag, " final hold"});

      current_value = final_value;
      current_hold_word = scalar_word(final_value);
      have_hold = 1'b1;
   end
endtask

task automatic idle_noop_awg;
   logic [CMD_WIDTH-1:0] cmd;
   string tag;

   begin
      tag = "OP_IDLE no-op";
      cmd = make_cmd(32'sd9999, 32'sd0, 32'd64, 32'sd0, OP_IDLE, 1'b0, 1'b0);
      send_cmd(cmd, have_hold, current_hold_word, tag);
      check_hold_words(current_value, 2, {tag, " hold"});
   end
endtask

initial begin
   open_output_files();
   init_tb_state();

   reset_dut();
   check_command_field_limits();

   check_m_axis_tready_ignored();
   set_awg(32'sd1000);
   axi_wait_current(32'sd1000, "SET 1000 AXI readback");
   axi_override_current(32'sd1234, "AXI OVERRIDE IDLE 1234");
   ramp_awg_abort_with_axi_override(
      32'sd2000,
      32'd64,
      -32'sd777,
      32'sd1750,
      32'd64
   );
   ramp_awg_with_drop_tests(
      32'sd2000,
      32'd64
   );
   set_awg(-32'sd500);
   ramp_awg(
      -32'sd1500,
      32'd64
   );
   idle_noop_awg();
   set_awg_zero_hold(32'sd123);
   set_awg(32'sd0);
   ramp_awg_explicit_step(
      32'sd1024,
      32'd9,
      (32'sd1 <<< (STEP_WIDTH-1)) - 32'sd1,
      "max valid signed 24-bit step"
   );
   set_awg(32'sd0);
   ramp_awg_explicit_step(
      -32'sd1024,
      32'd9,
      -(32'sd1 <<< (STEP_WIDTH-1)),
      "min valid signed 24-bit step"
   );

   close_output_files();
   $display("PASS: tb_simple axis_awg_tuning_v1 continuous SET/RAMP/drop test completed");
   $finish;
end

endmodule

`default_nettype wire
