`default_nettype none

// 160-bit command format, compatible with tProcessor v1 AXIS output width:
//
// | bits      | field                                                     |
// |-----------|-----------------------------------------------------------|
// | 31:0      | y_target for SET/RAMP, signed integer                    |
// | 63:32     | reserved/deprecated y_start field; ignored by RAMP       |
// | 95:64     | duration: RAMP scalar samples, IDLE slow cycles; 0 -> 1  |
// | 127:96    | reserved/deprecated software step field; ignored by RAMP |
// | 143:128   | reserved                                                  |
// | 145:144   | opcode: 00 NOP, 01 SET, 10 RAMP, 11 IDLE                 |
// | 146       | hold mode: 0 hold final value, 1 output zero after command |
// | 147       | reserved, samples are always signed and saturated         |
// | 148       | clear held output state before SET; ignored by RAMP/IDLE/NOP |
// | 159:149   | reserved                                                  |
//
// RAMP commands are continuous: the hardware ignores the deprecated y_start
// and step fields, starts from the current logical output value, and computes:
// step = trunc(((y_target - current_value) <<< FRAC) / (duration - 1)).
// The division is performed once when the RAMP command is accepted.
//
// NOP is an immediate no-op. IDLE is a timed wait using the same duration
// field, counted in aclk slow sequencer cycles. IDLE emits no m_axis samples,
// leaves the current held output/ramp configuration unchanged, and returns to
// the normal ready/hold state when the wait expires.

module awg_tuning_ctrl
   #(
      parameter int N_DDS = 16,
      parameter int B = 16,
      parameter int FRAC = 16,
      parameter int CMD_WIDTH = 160
   )
   (
      // Reset and clock.
      input  wire                   aresetn,
      input  wire                   aclk,

      // AXIS slave command input.
      input  wire [CMD_WIDTH-1:0]   s_axis_tdata,
      input  wire                   s_axis_tvalid,
      output logic                  s_axis_tready,

      // AXIS master sample output.
      output logic [N_DDS*B-1:0]    m_axis_tdata,
      output logic                  m_axis_tvalid,
      input  wire                   m_axis_tready
   );

localparam logic [1:0] OP_NOP  = 2'b00;
localparam logic [1:0] OP_SET  = 2'b01;
localparam logic [1:0] OP_RAMP = 2'b10;
localparam logic [1:0] OP_IDLE = 2'b11;

typedef enum logic [2:0] {
   IDLE_ST,
   SET_ST,
   RAMP_ST,
   HOLD_ST,
   WAIT_IDLE_ST
} state_t;

state_t state;

wire signed [31:0] cmd_target    = s_axis_tdata[31:0];
wire        [31:0] cmd_duration  = s_axis_tdata[95:64];
wire        [1:0]  cmd_opcode    = s_axis_tdata[145:144];
wire               cmd_hold_zero = s_axis_tdata[146];
wire               cmd_clear     = s_axis_tdata[148];

logic                   cmd_fire;
logic                   ramp_start_r;
logic signed [31:0]     ramp_start_value_r;
logic signed [31:0]     ramp_target_value_r;
logic signed [31:0]     ramp_step_r;
logic [31:0]            ramp_duration_r;
logic                   ramp_hold_zero_r;
logic [N_DDS*B-1:0]     ramp_tdata;
logic                   ramp_tvalid;
logic                   ramp_done;
logic                   ramp_active;

logic [B-1:0]           set_sample_r;
logic signed [31:0]     set_target_value_r;
logic                   set_hold_zero_r;
logic [B-1:0]           hold_sample_r;
logic                   hold_valid_r;
logic signed [31:0]     current_value_r;
logic [31:0]            idle_duration_r;
logic [31:0]            idle_count_r;

function automatic logic [B-1:0] sat_int32;
   input logic signed [31:0] value;
   logic signed [63:0] value_64;
   logic signed [63:0] max_sample;
   logic signed [63:0] min_sample;
   begin
      value_64 = value;
      max_sample = (64'sd1 <<< (B-1)) - 64'sd1;
      min_sample = -(64'sd1 <<< (B-1));

      if (value_64 > max_sample)
         sat_int32 = {1'b0, {(B-1){1'b1}}};
      else if (value_64 < min_sample)
         sat_int32 = {1'b1, {(B-1){1'b0}}};
      else
         sat_int32 = value[B-1:0];
   end
endfunction

function automatic logic [N_DDS*B-1:0] sample_word;
   input logic [B-1:0] sample;
   logic [N_DDS*B-1:0] word;
   begin
      word = {N_DDS*B{1'b0}};
      for (int i = 0; i < N_DDS; i = i + 1)
         word[i*B +: B] = sample;
      sample_word = word;
   end
endfunction

function automatic logic signed [31:0] calc_ramp_step;
   input logic signed [31:0] y_start;
   input logic signed [31:0] y_target;
   input logic [31:0] duration;
   logic signed [63:0] y_start_ext;
   logic signed [63:0] y_target_ext;
   logic signed [63:0] delta;
   logic signed [63:0] numerator;
   logic signed [63:0] denominator;
   logic signed [63:0] quotient;
   begin
      if (duration <= 32'd1) begin
         calc_ramp_step = 32'sd0;
      end
      else begin
         y_start_ext = {{32{y_start[31]}}, y_start};
         y_target_ext = {{32{y_target[31]}}, y_target};
         delta = y_target_ext - y_start_ext;
         numerator = delta <<< FRAC;
         denominator = {32'd0, duration - 32'd1};
         quotient = numerator / denominator;
         calc_ramp_step = quotient[31:0];
      end
   end
endfunction

awg_linear_ramp
   #(
      .N_DDS          (N_DDS ),
      .B              (B     ),
      .FRAC           (FRAC  ),
      .VALUE_WIDTH    (32    ),
      .STEP_WIDTH     (32    ),
      .DURATION_WIDTH (32    )
   )
   awg_linear_ramp_i
   (
      // Reset and clock.
      .aresetn          (aresetn             ),
      .aclk             (aclk                ),

      // Ramp configuration.
      .start_i          (ramp_start_r        ),
      .y_start_i        (ramp_start_value_r  ),
      .y_target_i       (ramp_target_value_r ),
      .step_i           (ramp_step_r         ),
      .duration_i       (ramp_duration_r     ),

      // Output stream.
      .m_axis_tdata_o   (ramp_tdata          ),
      .m_axis_tvalid_o  (ramp_tvalid         ),
      .m_axis_tready_i  (m_axis_tready       ),

      // Status.
      .active_o         (ramp_active         ),
      .done_o           (ramp_done           )
   );

always_comb begin
   case (state)
      IDLE_ST:
         s_axis_tready = 1'b1;

      HOLD_ST:
         s_axis_tready = hold_valid_r ? m_axis_tready : 1'b1;

      default:
         s_axis_tready = 1'b0;
   endcase
end

assign cmd_fire = s_axis_tvalid & s_axis_tready;

always_comb begin
   m_axis_tvalid = 1'b0;
   m_axis_tdata  = {N_DDS*B{1'b0}};

   case (state)
      SET_ST: begin
         m_axis_tvalid = 1'b1;
         m_axis_tdata  = sample_word(set_sample_r);
      end

      RAMP_ST: begin
         m_axis_tvalid = ramp_tvalid;
         m_axis_tdata  = ramp_tdata;
      end

      HOLD_ST: begin
         m_axis_tvalid = hold_valid_r;
         m_axis_tdata  = sample_word(hold_sample_r);
      end

      WAIT_IDLE_ST: begin
         m_axis_tvalid = 1'b0;
         m_axis_tdata  = sample_word(hold_sample_r);
      end

      default: begin
         m_axis_tvalid = 1'b0;
         m_axis_tdata  = {N_DDS*B{1'b0}};
      end
   endcase
end

always_ff @(posedge aclk) begin
   if (!aresetn) begin
      state               <= IDLE_ST;
      ramp_start_r        <= 1'b0;
      ramp_start_value_r  <= 32'sd0;
      ramp_target_value_r <= 32'sd0;
      ramp_step_r         <= 32'sd0;
      ramp_duration_r     <= 32'd0;
      ramp_hold_zero_r    <= 1'b0;
      set_sample_r        <= {B{1'b0}};
      set_target_value_r  <= 32'sd0;
      set_hold_zero_r     <= 1'b0;
      hold_sample_r       <= {B{1'b0}};
      hold_valid_r        <= 1'b0;
      current_value_r     <= 32'sd0;
      idle_duration_r     <= 32'd0;
      idle_count_r        <= 32'd0;
   end
   else begin
      ramp_start_r <= 1'b0;

      case (state)
         IDLE_ST, HOLD_ST: begin
            if (cmd_fire) begin
               case (cmd_opcode)
                  OP_SET: begin
                     if (cmd_clear) begin
                        hold_sample_r <= {B{1'b0}};
                        hold_valid_r  <= 1'b0;
                     end

                     set_sample_r       <= sat_int32(cmd_target);
                     set_target_value_r <= cmd_target;
                     set_hold_zero_r    <= cmd_hold_zero;
                     state              <= SET_ST;
                  end

                  OP_RAMP: begin
                     ramp_start_value_r  <= current_value_r;
                     ramp_target_value_r <= cmd_target;
                     ramp_step_r         <= calc_ramp_step(current_value_r, cmd_target, cmd_duration);
                     ramp_duration_r     <= cmd_duration;
                     ramp_hold_zero_r    <= cmd_hold_zero;
                     ramp_start_r        <= 1'b1;
                     state               <= RAMP_ST;
                  end

                  OP_IDLE: begin
                     idle_duration_r <= (cmd_duration == 32'd0) ? 32'd1 : cmd_duration;
                     idle_count_r    <= 32'd0;
                     state           <= WAIT_IDLE_ST;
                  end

                  OP_NOP: begin
                     state <= hold_valid_r ? HOLD_ST : IDLE_ST;
                  end

                  default: begin
                     state <= hold_valid_r ? HOLD_ST : IDLE_ST;
                  end
               endcase
            end
         end

         SET_ST: begin
            if (m_axis_tvalid && m_axis_tready) begin
               hold_sample_r   <= set_hold_zero_r ? {B{1'b0}} : set_sample_r;
               hold_valid_r    <= 1'b1;
               current_value_r <= set_hold_zero_r ? 32'sd0 : set_target_value_r;
               state           <= HOLD_ST;
            end
         end

         RAMP_ST: begin
            if (ramp_done) begin
               hold_sample_r   <= ramp_hold_zero_r ? {B{1'b0}} : sat_int32(ramp_target_value_r);
               hold_valid_r    <= 1'b1;
               current_value_r <= ramp_hold_zero_r ? 32'sd0 : ramp_target_value_r;
               state           <= HOLD_ST;
            end
         end

         WAIT_IDLE_ST: begin
            if (idle_count_r == idle_duration_r - 32'd1) begin
               idle_count_r <= 32'd0;
               state        <= hold_valid_r ? HOLD_ST : IDLE_ST;
            end
            else begin
               idle_count_r <= idle_count_r + 32'd1;
            end
         end

         default:
            state <= IDLE_ST;
      endcase
   end
end

endmodule

`default_nettype wire
