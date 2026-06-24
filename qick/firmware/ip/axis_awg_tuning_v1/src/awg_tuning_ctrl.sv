`default_nettype none

// 160-bit command format, compatible with tProcessor v1 AXIS output width:
//
// | bits      | field                                                     |
// |-----------|-----------------------------------------------------------|
// | 31:0      | y_target for SET/RAMP, signed integer                    |
// | 63:32     | reserved/deprecated y_start field; ignored by RAMP       |
// | 86:64     | duration: RAMP scalar samples, unsigned 23-bit; 0 -> 1   |
// | 95:87     | ignored duration extension bits                           |
// | 119:96    | step for RAMP, signed 24-bit fixed-point with FRAC bits   |
// | 127:120   | ignored step extension bits                               |
// | 143:128   | reserved                                                  |
// | 145:144   | opcode: 00 NOP, 01 SET, 10 RAMP, 11 IDLE                 |
// | 146       | SET hold mode: 0 hold target, 1 hold zero after SET word |
// | 147       | reserved, samples are always signed and saturated         |
// | 148       | deprecated clear field; ignored                           |
// | 159:149   | reserved                                                  |
//
// Continuous RFDC DAC sample source semantics:
// - s_axis_tready is always 1; command input is not backpressured.
// - m_axis_tready is ignored; output timing is deterministic.
// - m_axis_tvalid is 1 after reset deassertion in every state.
// - SET executes inside IDLE_ST without a separate SET state.
// - RAMP starts from the internal current value, uses the command-provided
//   signed 24-bit fixed-point step, and emits one N_PTS-wide word every aclk
//   after the DSP lane-multiply, DSP lane-add, and EXTRA_Y_PIPE_STAGES
//   pass-through pipeline latency.
// - OP_IDLE is a no-op in this simplified FSM.
// - Commands presented during RAMP_ST are intentionally dropped.
// - AXI-Lite override has higher priority than AXIS command processing.
//   If an override and AXIS command arrive in the same cycle, the override
//   is applied, the FSM is forced to IDLE_ST, and the AXIS command is dropped.
//
// RAMP datapath:
//   word_inc_fixed = N_PTS * step        (explicit DSP48E2 constant multiply)
//   inc[i]         = i * step            (explicit DSP48E2 lane multiply)
//   y_add[i]       = base_y_fixed + inc  (explicit DSP48E2 48-bit add)
//   y_pipe         = pass-through register stages only; P is not a scale.
//   base_y_fixed   = base_y_fixed + word_inc_fixed

(* keep_hierarchy = "yes", DONT_TOUCH = "true" *)
module dsp48e2_mul_step_const
   #(
      parameter int STEP_WIDTH = 24,
      parameter int FIXED_WIDTH = 48,
      parameter int CONST_VALUE = 0,
      parameter int REGISTER_OUTPUT = 1
   )
   (
      input  wire                         clk,
      input  wire                         rstn,
      input  wire                         ce_i,
      input  wire signed [STEP_WIDTH-1:0] step_i,
      output wire signed [FIXED_WIDTH-1:0] product_o
   );

localparam int PREG_VALUE = (REGISTER_OUTPUT != 0) ? 1 : 0;
localparam logic signed [17:0] CONST_B = CONST_VALUE;

wire signed [29:0] a_ext = {{(30-STEP_WIDTH){step_i[STEP_WIDTH-1]}}, step_i};
wire [47:0] p_out;

// DSP48E2 multiplier mode with C=0:
//   OPMODE=000110101 selects P = C + A*B.
// REGISTER_OUTPUT=1 gives one registered DSP48E2 P-stage cycle of latency.
DSP48E2 #(
   .ACASCREG(0),
   .ADREG(0),
   .ALUMODEREG(0),
   .AREG(0),
   .A_INPUT("DIRECT"),
   .BCASCREG(0),
   .BREG(0),
   .B_INPUT("DIRECT"),
   .CARRYINREG(0),
   .CARRYINSELREG(0),
   .CREG(0),
   .DREG(0),
   .INMODEREG(0),
   .MREG(0),
   .OPMODEREG(0),
   .PREG(PREG_VALUE),
   .USE_MULT("MULTIPLY"),
   .USE_SIMD("ONE48")
) dsp48e2_i (
   .ACOUT(),
   .BCOUT(),
   .CARRYCASCOUT(),
   .CARRYOUT(),
   .MULTSIGNOUT(),
   .OVERFLOW(),
   .P(p_out),
   .PATTERNBDETECT(),
   .PATTERNDETECT(),
   .PCOUT(),
   .UNDERFLOW(),
   .XOROUT(),
   .A(a_ext),
   .ACIN(30'b0),
   .ALUMODE(4'b0000),
   .B(CONST_B),
   .BCIN(18'b0),
   .C(48'd0),
   .CARRYCASCIN(1'b0),
   .CARRYIN(1'b0),
   .CARRYINSEL(3'b000),
   .CEA1(1'b0),
   .CEA2(1'b0),
   .CEAD(1'b0),
   .CEALUMODE(1'b0),
   .CEB1(1'b0),
   .CEB2(1'b0),
   .CEC(1'b0),
   .CECARRYIN(1'b0),
   .CECTRL(1'b0),
   .CED(1'b0),
   .CEINMODE(1'b0),
   .CEM(1'b0),
   .CEP(ce_i),
   .CLK(clk),
   .D(27'd0),
   .INMODE(5'b00000),
   .MULTSIGNIN(1'b0),
   .OPMODE(9'b000110101),
   .PCIN(48'd0),
   .RSTA(~rstn),
   .RSTALLCARRYIN(~rstn),
   .RSTALUMODE(~rstn),
   .RSTB(~rstn),
   .RSTC(~rstn),
   .RSTCTRL(~rstn),
   .RSTD(~rstn),
   .RSTINMODE(~rstn),
   .RSTM(~rstn),
   .RSTP(~rstn)
);

assign product_o = p_out[FIXED_WIDTH-1:0];

endmodule

module dsp48e2_mul_step_lane
   #(
      parameter int STEP_WIDTH = 24,
      parameter int FIXED_WIDTH = 48,
      parameter int LANE_INDEX = 0
   )
   (
      input  wire                         clk,
      input  wire                         rstn,
      input  wire                         ce_i,
      input  wire signed [STEP_WIDTH-1:0] step_i,
      output wire signed [FIXED_WIDTH-1:0] product_o
   );

// One-cycle latency through the DSP48E2 P register.
dsp48e2_mul_step_const #(
   .STEP_WIDTH(STEP_WIDTH),
   .FIXED_WIDTH(FIXED_WIDTH),
   .CONST_VALUE(LANE_INDEX),
   .REGISTER_OUTPUT(1)
) mul_i (
   .clk(clk),
   .rstn(rstn),
   .ce_i(ce_i),
   .step_i(step_i),
   .product_o(product_o)
);

endmodule

module dsp48e2_mul_step_npts
   #(
      parameter int STEP_WIDTH = 24,
      parameter int FIXED_WIDTH = 48,
      parameter int N_PTS_VALUE = 16
   )
   (
      input  wire                         clk,
      input  wire                         rstn,
      input  wire                         ce_i,
      input  wire signed [STEP_WIDTH-1:0] step_i,
      output wire signed [FIXED_WIDTH-1:0] product_o
   );

// Command-time word increment multiply. The primitive is explicit DSP48E2;
// the controller captures the combinational DSP output on command acceptance.
dsp48e2_mul_step_const #(
   .STEP_WIDTH(STEP_WIDTH),
   .FIXED_WIDTH(FIXED_WIDTH),
   .CONST_VALUE(N_PTS_VALUE),
   .REGISTER_OUTPUT(0)
) mul_i (
   .clk(clk),
   .rstn(rstn),
   .ce_i(ce_i),
   .step_i(step_i),
   .product_o(product_o)
);

endmodule

(* keep_hierarchy = "yes", DONT_TOUCH = "true" *)
module dsp48e2_add48
   #(
      parameter int REGISTER_OUTPUT = 1
   )
   (
      input  wire                  clk,
      input  wire                  rstn,
      input  wire                  ce_i,
      input  wire signed [47:0]    a_i,
      input  wire signed [47:0]    b_i,
      output wire signed [47:0]    sum_o
   );

localparam int PREG_VALUE = (REGISTER_OUTPUT != 0) ? 1 : 0;
wire [47:0] p_out;

// DSP48E2 48-bit ALU add mode:
//   USE_MULT="NONE"
//   X mux = {A,B}, Y mux = 0, Z mux = C, W mux = 0
//   ALUMODE=0000, CARRYINSEL=000 so P = {A,B} + C.
// REGISTER_OUTPUT=1 gives one registered DSP48E2 P-stage cycle of latency.
DSP48E2 #(
   .ACASCREG(0),
   .ADREG(0),
   .ALUMODEREG(0),
   .AREG(0),
   .A_INPUT("DIRECT"),
   .BCASCREG(0),
   .BREG(0),
   .B_INPUT("DIRECT"),
   .CARRYINREG(0),
   .CARRYINSELREG(0),
   .CREG(0),
   .DREG(0),
   .INMODEREG(0),
   .MREG(0),
   .OPMODEREG(0),
   .PREG(PREG_VALUE),
   .USE_MULT("NONE"),
   .USE_SIMD("ONE48")
) dsp48e2_i (
   .ACOUT(),
   .BCOUT(),
   .CARRYCASCOUT(),
   .CARRYOUT(),
   .MULTSIGNOUT(),
   .OVERFLOW(),
   .P(p_out),
   .PATTERNBDETECT(),
   .PATTERNDETECT(),
   .PCOUT(),
   .UNDERFLOW(),
   .XOROUT(),
   .A(a_i[47:18]),
   .ACIN(30'b0),
   .ALUMODE(4'b0000),
   .B(a_i[17:0]),
   .BCIN(18'b0),
   .C(b_i),
   .CARRYCASCIN(1'b0),
   .CARRYIN(1'b0),
   .CARRYINSEL(3'b000),
   .CEA1(1'b0),
   .CEA2(1'b0),
   .CEAD(1'b0),
   .CEALUMODE(1'b0),
   .CEB1(1'b0),
   .CEB2(1'b0),
   .CEC(1'b0),
   .CECARRYIN(1'b0),
   .CECTRL(1'b0),
   .CED(1'b0),
   .CEINMODE(1'b0),
   .CEM(1'b0),
   .CEP(ce_i),
   .CLK(clk),
   .D(27'd0),
   .INMODE(5'b00000),
   .MULTSIGNIN(1'b0),
   .OPMODE(9'b000110011),
   .PCIN(48'd0),
   .RSTA(~rstn),
   .RSTALLCARRYIN(~rstn),
   .RSTALUMODE(~rstn),
   .RSTB(~rstn),
   .RSTC(~rstn),
   .RSTCTRL(~rstn),
   .RSTD(~rstn),
   .RSTINMODE(~rstn),
   .RSTM(~rstn),
   .RSTP(~rstn)
);

assign sum_o = p_out;

endmodule

module awg_tuning_ctrl
   #(
      parameter int N_PTS = 16,
      parameter int B = 16,
      parameter int FRAC = 16,
      parameter int CMD_WIDTH = 160,
      parameter int STEP_WIDTH = 24,
      parameter int DURATION_WIDTH = 23,
      parameter int FIXED_WIDTH = 48,
      parameter int EXTRA_Y_PIPE_STAGES = 1
   )
   (
      // Reset and clock.
      input  wire                   aresetn,
      input  wire                   aclk,

      // AXIS slave command input.
      input  wire [CMD_WIDTH-1:0]   s_axis_tdata,
      input  wire                   s_axis_tvalid,
      output logic                  s_axis_tready,

      // Software/debug override from the AXI-Lite clock-domain bridge.
      input  wire signed [31:0]     axi_override_value,
      input  wire                   axi_override_valid,

      // RFDC-facing continuous sample output.
      output logic [N_PTS*B-1:0]    m_axis_tdata,
      output logic                  m_axis_tvalid,
      input  wire                   m_axis_tready,

      // Synchronized by the top-level before AXI-Lite readback.
      output logic signed [31:0]    current_value_o,
      output logic [31:0]           status_o
   );

localparam logic [1:0] OP_NOP  = 2'b00;
localparam logic [1:0] OP_SET  = 2'b01;
localparam logic [1:0] OP_RAMP = 2'b10;
localparam logic [1:0] OP_IDLE = 2'b11;
localparam logic [DURATION_WIDTH:0] N_PTS_U = N_PTS;

typedef enum logic {
   IDLE_ST,
   RAMP_ST
} state_t;

state_t state;

wire signed [31:0]                  cmd_target = s_axis_tdata[31:0];
wire [DURATION_WIDTH-1:0]           cmd_duration_23 = s_axis_tdata[64 +: DURATION_WIDTH];
wire signed [STEP_WIDTH-1:0]        cmd_step_24 = s_axis_tdata[96 +: STEP_WIDTH];
wire [1:0]                          cmd_opcode = s_axis_tdata[145:144];
wire                                cmd_hold_zero = s_axis_tdata[146];
wire                                cmd_clear = s_axis_tdata[148];
wire                                cmd_valid = s_axis_tvalid;

wire                                unused_m_axis_tready = m_axis_tready;
wire                                unused_cmd_clear = cmd_clear;
wire [48:0]                         unused_cmd_ignored_fields =
   {s_axis_tdata[63:32], s_axis_tdata[95:87], s_axis_tdata[127:120]};

logic [B-1:0]                       hold_sample_r;
logic signed [31:0]                 current_value_r;
logic signed [31:0]                 current_value_readback_r;
logic                                axi_override_seen_r;

logic signed [31:0]                 ramp_target_value_r;
logic signed [STEP_WIDTH-1:0]       ramp_step_r;
logic [DURATION_WIDTH-1:0]          ramp_duration_r;
logic [DURATION_WIDTH:0]            ramp_base_index_r;
logic signed [FIXED_WIDTH-1:0]      ramp_base_y_fixed_r;
logic signed [FIXED_WIDTH-1:0]      ramp_word_inc_fixed_r;
logic                               ramp_issue_valid_r;

logic signed [FIXED_WIDTH-1:0]      lane_inc_dsp [0:N_PTS-1];
logic signed [FIXED_WIDTH-1:0]      lane_y_add_dsp [0:N_PTS-1];
logic signed [FIXED_WIDTH-1:0]      base_next_dsp;
logic signed [FIXED_WIDTH-1:0]      word_inc_cmd_dsp;

logic                               mul_valid_r;
logic signed [FIXED_WIDTH-1:0]      mul_base_y_r;
logic signed [31:0]                 mul_target_r;
logic [DURATION_WIDTH-1:0]          mul_duration_r;
logic [DURATION_WIDTH:0]            mul_base_index_r;
logic                               mul_last_r;

logic                               add_valid_r;
logic signed [31:0]                 add_target_r;
logic [DURATION_WIDTH-1:0]          add_duration_r;
logic [DURATION_WIDTH:0]            add_base_index_r;
logic                               add_last_r;

logic [N_PTS*FIXED_WIDTH-1:0]       y_pipe_r [0:EXTRA_Y_PIPE_STAGES];
logic signed [31:0]                 y_pipe_target_r [0:EXTRA_Y_PIPE_STAGES];
logic [DURATION_WIDTH-1:0]          y_pipe_duration_r [0:EXTRA_Y_PIPE_STAGES];
logic [DURATION_WIDTH:0]            y_pipe_base_index_r [0:EXTRA_Y_PIPE_STAGES];
logic                               y_pipe_last_r [0:EXTRA_Y_PIPE_STAGES];
logic                               y_pipe_valid_r [0:EXTRA_Y_PIPE_STAGES];

function automatic logic [DURATION_WIDTH-1:0] normalize_duration;
   input logic [DURATION_WIDTH-1:0] duration;
   begin
      normalize_duration = (duration == {DURATION_WIDTH{1'b0}}) ?
                           {{(DURATION_WIDTH-1){1'b0}}, 1'b1} : duration;
   end
endfunction

function automatic logic signed [FIXED_WIDTH-1:0] int32_to_fixed;
   input logic signed [31:0] value;
   logic signed [FIXED_WIDTH-1:0] value_ext;
   begin
      value_ext = {{(FIXED_WIDTH-32){value[31]}}, value};
      int32_to_fixed = value_ext <<< FRAC;
   end
endfunction

function automatic logic [B-1:0] sat_dac16_msb_aligned;
   input logic signed [FIXED_WIDTH-1:0] fixed_value;
   logic signed [FIXED_WIDTH-1:0] int_value;
   logic signed [FIXED_WIDTH-1:0] max_sample;
   logic signed [FIXED_WIDTH-1:0] min_sample;
   logic signed [B-1:0] sample;
   logic [B-1:0] align_mask;
   begin
      int_value = fixed_value >>> FRAC;
      max_sample = (({{(FIXED_WIDTH-1){1'b0}}, 1'b1} <<< (B-1)) - 1) & ~{{(FIXED_WIDTH-2){1'b0}}, 2'b11};
      min_sample = -({{(FIXED_WIDTH-1){1'b0}}, 1'b1} <<< (B-1));
      align_mask = {{(B-2){1'b1}}, 2'b00};

      if (int_value > max_sample)
         sample = max_sample[B-1:0];
      else if (int_value < min_sample)
         sample = min_sample[B-1:0];
      else
         sample = int_value[B-1:0];

      sat_dac16_msb_aligned = sample & align_mask;
   end
endfunction

function automatic logic [B-1:0] sat_int32_msb_aligned;
   input logic signed [31:0] value;
   begin
      sat_int32_msb_aligned = sat_dac16_msb_aligned(int32_to_fixed(value));
   end
endfunction

function automatic logic [N_PTS*B-1:0] sample_word;
   input logic [B-1:0] sample;
   logic [N_PTS*B-1:0] word;
   begin
      word = {N_PTS*B{1'b0}};
      for (int i = 0; i < N_PTS; i = i + 1)
         word[i*B +: B] = sample;
      sample_word = word;
   end
endfunction

function automatic logic ramp_base_is_last;
   input logic [DURATION_WIDTH:0] base_index;
   input logic [DURATION_WIDTH-1:0] duration;
   logic [DURATION_WIDTH:0] next_base_ext;
   logic [DURATION_WIDTH:0] duration_ext;
   begin
      next_base_ext = base_index + N_PTS_U;
      duration_ext = {1'b0, duration};
      ramp_base_is_last = (next_base_ext >= duration_ext);
   end
endfunction

function automatic logic [N_PTS*B-1:0] ramp_word_from_fixed;
   input logic [N_PTS*FIXED_WIDTH-1:0] fixed_lanes;
   input logic signed [31:0] target_value;
   input logic [DURATION_WIDTH-1:0] duration;
   input logic [DURATION_WIDTH:0] base_index;
   logic [N_PTS*B-1:0] word;
   logic signed [FIXED_WIDTH-1:0] fixed_value;
   logic [DURATION_WIDTH:0] sample_index;
   logic [DURATION_WIDTH:0] final_index;
   begin
      word = {N_PTS*B{1'b0}};
      final_index = {1'b0, duration} - {{DURATION_WIDTH{1'b0}}, 1'b1};

      for (int i = 0; i < N_PTS; i = i + 1) begin
         sample_index = base_index + i[DURATION_WIDTH:0];
         fixed_value = $signed(fixed_lanes[i*FIXED_WIDTH +: FIXED_WIDTH]);

         if (duration <= {{(DURATION_WIDTH-1){1'b0}}, 1'b1} ||
             sample_index >= final_index) begin
            word[i*B +: B] = sat_int32_msb_aligned(target_value);
         end
         else begin
            word[i*B +: B] = sat_dac16_msb_aligned(fixed_value);
         end
      end

      ramp_word_from_fixed = word;
   end
endfunction

function automatic logic signed [31:0] lane_to_i32;
   input logic [B-1:0] sample;
   logic signed [B-1:0] signed_sample;
   begin
      signed_sample = sample;
      lane_to_i32 = signed_sample;
   end
endfunction

wire [DURATION_WIDTH-1:0] cmd_duration_norm = normalize_duration(cmd_duration_23);
wire [B-1:0] cmd_target_sample = sat_int32_msb_aligned(cmd_target);
wire [B-1:0] cmd_set_hold_sample = cmd_hold_zero ? {B{1'b0}} : cmd_target_sample;
wire [B-1:0] axi_override_sample = sat_int32_msb_aligned(axi_override_value);
wire [N_PTS*B-1:0] hold_word = sample_word(hold_sample_r);
wire [N_PTS*B-1:0] cmd_set_word = sample_word(cmd_target_sample);
wire [N_PTS*B-1:0] axi_override_word = sample_word(axi_override_sample);
wire [N_PTS*B-1:0] ramp_output_word =
   ramp_word_from_fixed(y_pipe_r[EXTRA_Y_PIPE_STAGES],
                        y_pipe_target_r[EXTRA_Y_PIPE_STAGES],
                        y_pipe_duration_r[EXTRA_Y_PIPE_STAGES],
                        y_pipe_base_index_r[EXTRA_Y_PIPE_STAGES]);

genvar lane_g;
generate
   for (lane_g = 0; lane_g < N_PTS; lane_g = lane_g + 1) begin : GEN_DSP_LANES
      dsp48e2_mul_step_lane #(
         .STEP_WIDTH(STEP_WIDTH),
         .FIXED_WIDTH(FIXED_WIDTH),
         .LANE_INDEX(lane_g)
      ) lane_mul_i (
         .clk(aclk),
         .rstn(aresetn),
         .ce_i(ramp_issue_valid_r),
         .step_i(ramp_step_r),
         .product_o(lane_inc_dsp[lane_g])
      );

      dsp48e2_add48 #(
         .REGISTER_OUTPUT(1)
      ) lane_add_i (
         .clk(aclk),
         .rstn(aresetn),
         .ce_i(mul_valid_r),
         .a_i(mul_base_y_r),
         .b_i(lane_inc_dsp[lane_g]),
         .sum_o(lane_y_add_dsp[lane_g])
      );
   end
endgenerate

dsp48e2_mul_step_npts #(
   .STEP_WIDTH(STEP_WIDTH),
   .FIXED_WIDTH(FIXED_WIDTH),
   .N_PTS_VALUE(N_PTS)
) word_inc_mul_i (
   .clk(aclk),
   .rstn(aresetn),
   .ce_i(1'b1),
   .step_i(cmd_step_24),
   .product_o(word_inc_cmd_dsp)
);

dsp48e2_add48 #(
   .REGISTER_OUTPUT(0)
) base_add_i (
   .clk(aclk),
   .rstn(aresetn),
   .ce_i(1'b1),
   .a_i(ramp_base_y_fixed_r),
   .b_i(ramp_word_inc_fixed_r),
   .sum_o(base_next_dsp)
);

always_comb begin
   s_axis_tready = 1'b1;
   status_o = 32'd0;
   if (aresetn) begin
      status_o[0] = (state == IDLE_ST);
      status_o[1] = (state == RAMP_ST);
      status_o[2] = m_axis_tvalid;
      status_o[3] = s_axis_tready;
      status_o[4] = axi_override_valid;
      status_o[5] = axi_override_seen_r;
   end
   current_value_o = current_value_readback_r;
end

always_ff @(posedge aclk) begin
   if (!aresetn) begin
      state <= IDLE_ST;
      hold_sample_r <= {B{1'b0}};
      current_value_r <= 32'sd0;
      current_value_readback_r <= 32'sd0;
      axi_override_seen_r <= 1'b0;
      ramp_target_value_r <= 32'sd0;
      ramp_step_r <= {STEP_WIDTH{1'b0}};
      ramp_duration_r <= {{(DURATION_WIDTH-1){1'b0}}, 1'b1};
      ramp_base_index_r <= {DURATION_WIDTH+1{1'b0}};
      ramp_base_y_fixed_r <= {FIXED_WIDTH{1'b0}};
      ramp_word_inc_fixed_r <= {FIXED_WIDTH{1'b0}};
      ramp_issue_valid_r <= 1'b0;
      mul_valid_r <= 1'b0;
      mul_base_y_r <= {FIXED_WIDTH{1'b0}};
      mul_target_r <= 32'sd0;
      mul_duration_r <= {{(DURATION_WIDTH-1){1'b0}}, 1'b1};
      mul_base_index_r <= {DURATION_WIDTH+1{1'b0}};
      mul_last_r <= 1'b0;
      add_valid_r <= 1'b0;
      add_target_r <= 32'sd0;
      add_duration_r <= {{(DURATION_WIDTH-1){1'b0}}, 1'b1};
      add_base_index_r <= {DURATION_WIDTH+1{1'b0}};
      add_last_r <= 1'b0;
      for (int p = 0; p <= EXTRA_Y_PIPE_STAGES; p = p + 1) begin
         y_pipe_r[p] <= {N_PTS*FIXED_WIDTH{1'b0}};
         y_pipe_target_r[p] <= 32'sd0;
         y_pipe_duration_r[p] <= {{(DURATION_WIDTH-1){1'b0}}, 1'b1};
         y_pipe_base_index_r[p] <= {DURATION_WIDTH+1{1'b0}};
         y_pipe_last_r[p] <= 1'b0;
         y_pipe_valid_r[p] <= 1'b0;
      end
      m_axis_tdata <= {N_PTS*B{1'b0}};
      m_axis_tvalid <= 1'b0;
   end
   else begin
      m_axis_tvalid <= 1'b1;
      m_axis_tdata <= hold_word;
      current_value_readback_r <= current_value_r;

      // Default pipeline advance. These stages continue to drain after the
      // last word has been issued; no new arithmetic is performed in y_pipe.
      mul_valid_r <= ramp_issue_valid_r;
      if (ramp_issue_valid_r) begin
         mul_base_y_r <= ramp_base_y_fixed_r;
         mul_target_r <= ramp_target_value_r;
         mul_duration_r <= ramp_duration_r;
         mul_base_index_r <= ramp_base_index_r;
         mul_last_r <= ramp_base_is_last(ramp_base_index_r, ramp_duration_r);
      end

      add_valid_r <= mul_valid_r;
      if (mul_valid_r) begin
         add_target_r <= mul_target_r;
         add_duration_r <= mul_duration_r;
         add_base_index_r <= mul_base_index_r;
         add_last_r <= mul_last_r;
      end

      y_pipe_valid_r[0] <= add_valid_r;
      if (add_valid_r) begin
         for (int i = 0; i < N_PTS; i = i + 1)
            y_pipe_r[0][i*FIXED_WIDTH +: FIXED_WIDTH] <= lane_y_add_dsp[i];
         y_pipe_target_r[0] <= add_target_r;
         y_pipe_duration_r[0] <= add_duration_r;
         y_pipe_base_index_r[0] <= add_base_index_r;
         y_pipe_last_r[0] <= add_last_r;
      end

      for (int p = 0; p < EXTRA_Y_PIPE_STAGES; p = p + 1) begin
         y_pipe_valid_r[p+1] <= y_pipe_valid_r[p];
         if (y_pipe_valid_r[p]) begin
            y_pipe_r[p+1] <= y_pipe_r[p];
            y_pipe_target_r[p+1] <= y_pipe_target_r[p];
            y_pipe_duration_r[p+1] <= y_pipe_duration_r[p];
            y_pipe_base_index_r[p+1] <= y_pipe_base_index_r[p];
            y_pipe_last_r[p+1] <= y_pipe_last_r[p];
         end
      end

      if (ramp_issue_valid_r) begin
         ramp_base_y_fixed_r <= base_next_dsp;
         ramp_base_index_r <= ramp_base_index_r + N_PTS_U;
         if (ramp_base_is_last(ramp_base_index_r, ramp_duration_r))
            ramp_issue_valid_r <= 1'b0;
      end

      if (axi_override_valid) begin
         m_axis_tdata <= axi_override_word;
         hold_sample_r <= axi_override_sample;
         current_value_r <= axi_override_value;
         current_value_readback_r <= axi_override_value;
         axi_override_seen_r <= 1'b1;
         ramp_target_value_r <= axi_override_value;
         ramp_step_r <= {STEP_WIDTH{1'b0}};
         ramp_duration_r <= {{(DURATION_WIDTH-1){1'b0}}, 1'b1};
         ramp_base_index_r <= {DURATION_WIDTH+1{1'b0}};
         ramp_base_y_fixed_r <= int32_to_fixed(axi_override_value);
         ramp_word_inc_fixed_r <= {FIXED_WIDTH{1'b0}};
         ramp_issue_valid_r <= 1'b0;
         mul_valid_r <= 1'b0;
         add_valid_r <= 1'b0;
         for (int p = 0; p <= EXTRA_Y_PIPE_STAGES; p = p + 1)
            y_pipe_valid_r[p] <= 1'b0;
         state <= IDLE_ST;
      end
      else begin
         case (state)
            IDLE_ST: begin
               if (cmd_valid) begin
                  case (cmd_opcode)
                     OP_SET: begin
                        m_axis_tdata <= cmd_set_word;
                        hold_sample_r <= cmd_set_hold_sample;
                        current_value_r <= cmd_hold_zero ? 32'sd0 : cmd_target;
                        current_value_readback_r <= cmd_target;
                        ramp_target_value_r <= cmd_target;
                        ramp_step_r <= {STEP_WIDTH{1'b0}};
                        ramp_duration_r <= {{(DURATION_WIDTH-1){1'b0}}, 1'b1};
                        ramp_base_index_r <= {DURATION_WIDTH+1{1'b0}};
                        ramp_base_y_fixed_r <= int32_to_fixed(cmd_hold_zero ? 32'sd0 : cmd_target);
                        ramp_word_inc_fixed_r <= {FIXED_WIDTH{1'b0}};
                        ramp_issue_valid_r <= 1'b0;
                        mul_valid_r <= 1'b0;
                        add_valid_r <= 1'b0;
                        for (int p = 0; p <= EXTRA_Y_PIPE_STAGES; p = p + 1)
                           y_pipe_valid_r[p] <= 1'b0;
                        state <= IDLE_ST;
                     end

                     OP_RAMP: begin
                        ramp_target_value_r <= cmd_target;
                        ramp_step_r <= cmd_step_24;
                        ramp_duration_r <= cmd_duration_norm;
                        ramp_base_index_r <= {DURATION_WIDTH+1{1'b0}};
                        ramp_base_y_fixed_r <= int32_to_fixed(current_value_r);
                        ramp_word_inc_fixed_r <= word_inc_cmd_dsp;
                        ramp_issue_valid_r <= 1'b1;
                        mul_valid_r <= 1'b0;
                        add_valid_r <= 1'b0;
                        for (int p = 0; p <= EXTRA_Y_PIPE_STAGES; p = p + 1)
                           y_pipe_valid_r[p] <= 1'b0;
                        state <= RAMP_ST;
                     end

                     OP_NOP, OP_IDLE: begin
                        state <= IDLE_ST;
                     end

                     default: begin
                        state <= IDLE_ST;
                     end
                  endcase
               end
            end

            RAMP_ST: begin
               if (y_pipe_valid_r[EXTRA_Y_PIPE_STAGES]) begin
                  m_axis_tdata <= ramp_output_word;
                  current_value_readback_r <= lane_to_i32(ramp_output_word[B-1:0]);

                  if (y_pipe_last_r[EXTRA_Y_PIPE_STAGES]) begin
                     hold_sample_r <= sat_int32_msb_aligned(ramp_target_value_r);
                     current_value_r <= ramp_target_value_r;
                     ramp_issue_valid_r <= 1'b0;
                     mul_valid_r <= 1'b0;
                     add_valid_r <= 1'b0;
                     for (int p = 0; p <= EXTRA_Y_PIPE_STAGES; p = p + 1)
                        y_pipe_valid_r[p] <= 1'b0;
                     state <= IDLE_ST;
                  end
               end
            end

            default: begin
               state <= IDLE_ST;
            end
         endcase
      end
   end
end

endmodule

`default_nettype wire
