// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`default_nettype none
// V7 uses one RAMP opcode with legacy and extended payloads. The public
// formats are documented below and in md/firmware/projects/qstl_awg_v7.
// SET/RAMP share 11 cycles. Timed commands never flush older output tags;
// logical current seeds subsequent commands, while physical current commits
// with its output word. Immediate AXI override explicitly aborts the pipe.
// Multiplication uses two signed 25x18 DSP products per lane, with full
// product overflow preserved until endpoint clamping. No boundary resets.

(* keep_hierarchy = "yes", DONT_TOUCH = "true" *)
module v7_dsp48e2_add48
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

// V7 RAMP: legacy packets retain their ABI. Bit 151 selects the extended
// RAMP payload (same opcode 10), never a fifth opcode.
// [15:0] turn target, [31:16] terminal target, signed DAC codes;
// [66:32] first step, [101:67] second step, signed Q18/35 bits;
// [105:102] first start lane, [110:106] second start lane (31=absent);
// [133:111] total scalar samples, [143:134] second start WORD offset.
// [150:146] must be zero in extended RAMP; [159:152] remains TMUX.
// The coarse second-word offset allows an edge to straddle a word without
// wrapping its timestamp or requiring a second same-clock command.
// Duration includes the terminal sample; all trailing lanes hold the target.
// A fractional step is NEVER restarted at a word boundary.
module v7_awg_tuning_ctrl
   #(
      parameter int N_PTS = 16, B = 16, FRAC = 18, CMD_WIDTH = 160,
      parameter int STEP_WIDTH = 32, DURATION_WIDTH = 23, FIXED_WIDTH = 48,
      parameter int EXTRA_Y_PIPE_STAGES = 3
   )
   (
      input  wire                       aresetn, aclk,
      input  wire [CMD_WIDTH-1:0]        s_axis_tdata,
      input  wire                       s_axis_tvalid,
      output wire                       s_axis_tready,
      input  wire signed [31:0]         axi_override_value,
      input  wire                       axi_override_valid,
      output logic [N_PTS*B-1:0]        m_axis_tdata,
      output logic                      m_axis_tvalid,
      input  wire                       m_axis_tready,
      output logic signed [31:0]       current_value_o,
      output logic [31:0]              status_o
   );

localparam int CORE_LATENCY = EXTRA_Y_PIPE_STAGES + 8;
localparam int TAGS = CORE_LATENCY - 1;
wire [1:0] opcode = s_axis_tdata[145:144];
wire extended = s_axis_tdata[151];
wire [22:0] ext_duration = s_axis_tdata[133:111];
wire [3:0] ext_start = s_axis_tdata[105:102];
wire [4:0] ext_fall = s_axis_tdata[110:106];
wire [13:0] ext_fall_sample = {s_axis_tdata[143:134], ext_fall[3:0]};
wire invalid_extended = extended &&
   (opcode != 2 || s_axis_tdata[150:146] != 0 || ext_duration == 0 || ext_duration <= {19'd0, ext_start} ||
    (ext_fall != 31 &&
     (ext_fall > 15 || ext_fall_sample < {10'd0, ext_start} || {9'd0, ext_fall_sample} >= ext_duration)));
wire issue_available;
wire accepted = s_axis_tvalid && (opcode == 1 || opcode == 2) && issue_available && !invalid_extended;
logic issue_valid = 0, mode_extended = 0, fall_enabled = 0;
logic [23:0] word_index = 0, total = 1;
logic [3:0] rise_start = 0;
logic [13:0] fall_start = 0;
logic signed [34:0] rise_step = 0, fall_step = 0;
logic signed [47:0] seed = 0, turn = 0, terminal = 0;
logic signed [31:0] logical_current = 0;
logic [15:0] physical_hold = 0, issued_hold = 0;
logic override_seen = 0, command_fault = 0;
wire issue_last = (word_index + 24'd16 >= total);
assign issue_available = !issue_valid || issue_last;
logic [TAGS-1:0] tag_valid = 0, tag_last = 0;
logic [15:0] tag_hold[0:TAGS-1];
// S1 chooses the segment, elapsed index and bounding voltages per lane.
logic [23:0] elapsed1[0:15];
logic signed [34:0] slope1[0:15];
logic signed [47:0] origin[0:5][0:15], limit[0:5][0:15];
logic bounded[0:5][0:15], descending[0:5][0:15];
// Each 35-bit step is split into signed high18 and unsigned low17.
// 25x18 fits one DSP48E2. Operand/M/P stages precede the 48-bit adders.
logic signed [24:0] offset2[0:15];
logic signed [17:0] high2[0:15], low2[0:15];
(* use_dsp="yes" *) logic signed [42:0] high3[0:15], low3[0:15];
logic signed [42:0] high4[0:15], low4[0:15];
wire signed [47:0] high_shift[0:15], low_extend[0:15];
wire signed [47:0] product5[0:15], value6[0:15];
// Preserve the upper product bits until extended-RAMP endpoint clamping.
// A short, steep edge followed by a long hold can exceed signed 48 bits.
logic signed [11:0] product_upper5[0:15];
wire signed [47:0] product_for_add[0:15];
logic [255:0] quant_pipe[0:EXTRA_Y_PIPE_STAGES];

function automatic signed [47:0] fixed32(input logic signed [31:0] value);
   logic signed [47:0] v;
   begin
      v = value > 32764 ? 48'sd32764 : (value < -32768 ? -48'sd32768 : {{16{value[31]}}, value});
      return v <<< 18;
   end
endfunction

function automatic [15:0] quant(input logic signed [47:0] value);
   logic signed [47:0] v;
   begin
      v = value >>> 18;
      if (v > 32764) return 16'h7ffc;
      if (v < -32768) return 16'h8000;
      return {v[15:2], 2'b00};
   end
endfunction

function automatic [15:0] bounded_quant(
   input logic signed [47:0] value,
   input logic signed [47:0] endpoint,
   input logic en, down
);
   if (en && ((down && value < endpoint) || (!down && value > endpoint))) return quant(endpoint);
   return quant(value);
endfunction

assign s_axis_tready = 1'b1;

always_comb begin
   status_o = 0;
   if (aresetn) begin
      status_o[0] = !(issue_valid || (|tag_valid));
      status_o[1] = !status_o[0];
      status_o[2] = m_axis_tvalid;
      status_o[3] = 1;
      status_o[4] = axi_override_valid;
      status_o[5] = override_seen;
      status_o[6] = issue_available;
      status_o[7] = command_fault;
   end
end

for (genvar lane = 0; lane < 16; lane++) begin : LANES
   wire [31:0] upper_carry = {1'b0, high4[lane][30:0]} + {6'b0, low4[lane][42:17]};
   // The low 17 bits of high_shift are zero: this 32-bit sum supplies
   // exactly the carry into bit 48 of the full 60-bit signed product.
   always_ff @(posedge aclk) begin
      if (!aresetn) product_upper5[lane] <= 0;
      else product_upper5[lane] <= $signed(high4[lane][42:31]) + $signed({11'b0, upper_carry[31]});
   end
   assign high_shift[lane] = $signed({{5{high4[lane][42]}}, high4[lane]}) <<< 17;
   assign low_extend[lane] = {{5{low4[lane][42]}}, low4[lane]};
   // All legal DAC endpoint differences fit signed 35 bits in Q18.
   // Capping a larger product at +/-2^35 preserves its endpoint decision,
   // and leaves ample headroom for the origin addition. Legacy arithmetic
   // keeps its original modulo-48 semantics.
   assign product_for_add[lane] = bounded[4][lane] &&
      ((product_upper5[lane] != {12{product5[lane][35]}}) ||
       (product5[lane][47:36] != {12{product5[lane][35]}})) ?
      (product_upper5[lane][11] ? -(48'sd1 <<< 35) : (48'sd1 <<< 35)) : product5[lane];

   v7_dsp48e2_add48 #(
      .REGISTER_OUTPUT(1)
   ) partial_add (
      .clk(aclk),
      .rstn(aresetn),
      .ce_i(1'b1),
      .a_i(high_shift[lane]),
      .b_i(low_extend[lane]),
      .sum_o(product5[lane])
   );
   v7_dsp48e2_add48 #(
      .REGISTER_OUTPUT(1)
   ) origin_add (
      .clk(aclk),
      .rstn(aresetn),
      .ce_i(1'b1),
      .a_i(product_for_add[lane]),
      .b_i(origin[4][lane]),
      .sum_o(value6[lane])
   );
end

always_ff @(posedge aclk) begin
   if (!aresetn) begin
      issue_valid <= 0;
      mode_extended <= 0;
      fall_enabled <= 0;
      word_index <= 0;
      total <= 1;
      rise_start <= 0;
      fall_start <= 0;
      rise_step <= 0;
      fall_step <= 0;
      seed <= 0;
      turn <= 0;
      terminal <= 0;
      logical_current <= 0;
      physical_hold <= 0;
      issued_hold <= 0;
      override_seen <= 0;
      command_fault <= 0;
      tag_valid <= 0;
      tag_last <= 0;
      m_axis_tdata <= 0;
      m_axis_tvalid <= 0;
      current_value_o <= 0;
      for (int s = 0; s < TAGS; s++) tag_hold[s] <= 0;
      for (int s = 0; s <= EXTRA_Y_PIPE_STAGES; s++) quant_pipe[s] <= 0;
      for (int i = 0; i < 16; i++) begin
         elapsed1[i] <= 0;
         slope1[i] <= 0;
         offset2[i] <= 0;
         high2[i] <= 0;
         low2[i] <= 0;
         high3[i] <= 0;
         low3[i] <= 0;
         high4[i] <= 0;
         low4[i] <= 0;
         for (int s = 0; s < 6; s++) begin
            origin[s][i] <= 0;
            limit[s][i] <= 0;
            bounded[s][i] <= 0;
            descending[s][i] <= 0;
         end
      end
   end else begin
      m_axis_tvalid <= 1;
      m_axis_tdata <= {16{physical_hold}};
      current_value_o <= {{16{physical_hold[15]}}, physical_hold};
      tag_valid <= {tag_valid[TAGS-2:0], issue_valid};
      tag_last <= {tag_last[TAGS-2:0], issue_last};
      tag_hold[0] <= issued_hold;
      for (int s = 1; s < TAGS; s++) tag_hold[s] <= tag_hold[s-1];
      for (int i = 0; i < 16; i++) begin : PREPARE
         logic [23:0] n;
         n = word_index + i;
         elapsed1[i] <= 0;
         slope1[i] <= 0;
         origin[0][i] <= seed;
         bounded[0][i] <= 0;
         descending[0][i] <= 0;
         limit[0][i] <= terminal;
         if (n >= total - 1) begin
            origin[0][i] <= terminal;
         end else if (!mode_extended) begin
            elapsed1[i] <= n;
            slope1[i]   <= rise_step;
         end else if (n < {20'd0, rise_start}) begin
            origin[0][i] <= seed;
         end else if (fall_enabled && n >= {10'd0, fall_start}) begin
            elapsed1[i] <= n - {10'd0, fall_start};
            slope1[i] <= fall_step;
            origin[0][i] <= turn;
            limit[0][i] <= terminal;
            bounded[0][i] <= 1;
            descending[0][i] <= terminal < turn;
         end else begin
            elapsed1[i] <= n - {20'd0, rise_start};
            slope1[i] <= rise_step;
            limit[0][i] <= turn;
            bounded[0][i] <= 1;
            descending[0][i] <= turn < seed;
         end
         // Pipeline all metadata alongside the arithmetic; no command may
         // overwrite the origin/limit/hold tags of an older in-flight word.
         for (int s = 1; s < 6; s++) begin
            origin[s][i] <= origin[s-1][i];
            limit[s][i] <= limit[s-1][i];
            bounded[s][i] <= bounded[s-1][i];
            descending[s][i] <= descending[s-1][i];
         end
         offset2[i] <= $signed({1'b0, elapsed1[i]});
         high2[i] <= slope1[i][34:17];
         low2[i] <= $signed({1'b0, slope1[i][16:0]});
         high3[i] <= offset2[i] * high2[i];
         low3[i] <= offset2[i] * low2[i];
         high4[i] <= high3[i];
         low4[i] <= low3[i];
         quant_pipe[0][16*i+:16] <= bounded_quant(value6[i], limit[5][i], bounded[5][i], descending[5][i]);
      end
      for (int s = 1; s <= EXTRA_Y_PIPE_STAGES; s++) quant_pipe[s] <= quant_pipe[s-1];
      if (issue_valid) begin
         word_index <= word_index + 24'd16;
         if (issue_last) issue_valid <= 0;
      end
      if (tag_valid[TAGS-1]) begin
         m_axis_tdata <= quant_pipe[EXTRA_Y_PIPE_STAGES];
         current_value_o <= {
            {16{quant_pipe[EXTRA_Y_PIPE_STAGES][15]}}, quant_pipe[EXTRA_Y_PIPE_STAGES][15:0]
         };
         if (tag_last[TAGS-1]) physical_hold <= tag_hold[TAGS-1];
      end
      if (s_axis_tvalid && invalid_extended) command_fault <= 1;
      if (accepted) begin
         word_index <= 0;
         issue_valid <= 1;
         mode_extended <= extended;
         seed <= fixed32(logical_current);
         rise_start <= 0;
         fall_start <= 0;
         fall_enabled <= 0;
         if (extended) begin
            total <= {1'b0, ext_duration};
            rise_start <= ext_start;
            fall_start <= ext_fall_sample;
            fall_enabled <= ext_fall != 31;
            rise_step <= s_axis_tdata[66:32];
            fall_step <= s_axis_tdata[101:67];
            turn <= fixed32($signed(s_axis_tdata[15:0]));
            terminal <= fixed32(
               ext_fall == 31 ? $signed(s_axis_tdata[15:0]) : $signed(s_axis_tdata[31:16])
            );
            issued_hold <= quant(
               fixed32(ext_fall == 31 ? $signed(s_axis_tdata[15:0]) : $signed(s_axis_tdata[31:16]))
            );
            logical_current <= ext_fall == 31 ? $signed(s_axis_tdata[15:0]) : $signed(s_axis_tdata[31:16]);
         end else begin
            terminal <= fixed32($signed(s_axis_tdata[31:0]));
            issued_hold <= opcode == 1 && s_axis_tdata[146] ? 0 : quant(
               fixed32($signed(s_axis_tdata[31:0]))
            );
            logical_current <= opcode == 1 && s_axis_tdata[146] ? 0 : $signed(s_axis_tdata[31:0]);
            total <= opcode == 1 || s_axis_tdata[86:64] == 0 ? 24'd1 : {1'b0, s_axis_tdata[86:64]};
            rise_step <= {{3{s_axis_tdata[127]}}, s_axis_tdata[127:96]};
         end
      end
      // Preserve the existing immediate core override/flush contract.
      if (axi_override_valid) begin
         logical_current <= axi_override_value;
         physical_hold <= quant(fixed32(axi_override_value));
         m_axis_tdata <= {16{quant(fixed32(axi_override_value))}};
         current_value_o <= $signed(quant(fixed32(axi_override_value)));
         issue_valid <= 0;
         tag_valid <= 0;
         tag_last <= 0;
         override_seen <= 1;
         command_fault <= 0;
      end
   end
end

initial begin
   if (N_PTS != 16 || B != 16 || FRAC != 18 || FIXED_WIDTH != 48 || STEP_WIDTH != 32 ||
       DURATION_WIDTH != 23 || EXTRA_Y_PIPE_STAGES != 3)
      $error("V7 production profile is 16 lanes, Q18, 48-bit arithmetic, common latency 11");
end
endmodule
`default_nettype wire
