`default_nettype none

// 160-bit command format, compatible with tProcessor v1 AXIS output width:
//
// | bits      | field                                                     |
// |-----------|-----------------------------------------------------------|
// | 31:0      | y_target for SET/RAMP, signed integer                    |
// | 63:32     | reserved/deprecated y_start field; ignored by RAMP       |
// | 95:64     | duration: RAMP scalar samples; 0 -> 1                    |
// | 127:96    | step for RAMP, signed fixed-point with FRAC frac bits    |
// | 143:128   | reserved                                                  |
// | 145:144   | opcode: 00 NOP, 01 SET, 10 RAMP, 11 IDLE                 |
// | 146       | SET hold mode: 0 hold target, 1 hold zero after SET word |
// | 147       | reserved, samples are always signed and saturated         |
// | 148       | deprecated clear field; ignored                           |
// | 159:149   | reserved                                                  |
//
// Continuous RFDC DAC sample source semantics:
// - The FSM has only IDLE_ST and RAMP_ST.
// - s_axis_tready is always 1; command input is not backpressured.
// - m_axis_tready is ignored; output timing is deterministic.
// - m_axis_tvalid is 1 after reset deassertion in every state.
// - SET executes inside IDLE_ST without a separate SET state.
// - RAMP starts from the internal current value, uses the command-provided
//   step field, and emits one N_PTS-wide word every aclk after a two-cycle
//   start latency.
// - OP_IDLE is a no-op in this simplified FSM.
// - Commands presented during RAMP_ST are intentionally dropped.
//   The command input is always ready; software/tProc must avoid issuing
//   meaningful commands during an active ramp if they should not be lost.
// - AXI-Lite override has higher priority than AXIS command processing.
//   If an override and AXIS command arrive in the same cycle, the override
//   is applied, the FSM is forced to IDLE_ST, and the AXIS command is dropped.

module awg_tuning_ctrl
   #(
      parameter int N_PTS = 16,
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
localparam logic [31:0] N_PTS_U32 = N_PTS;

typedef enum logic {
   IDLE_ST,
   RAMP_ST
} state_t;

state_t state;

wire signed [31:0] cmd_target    = s_axis_tdata[31:0];
wire        [31:0] cmd_duration  = s_axis_tdata[95:64];
wire signed [31:0] cmd_step      = s_axis_tdata[127:96];
wire        [1:0]  cmd_opcode    = s_axis_tdata[145:144];
wire               cmd_hold_zero = s_axis_tdata[146];
wire               cmd_clear     = s_axis_tdata[148];
wire               cmd_valid     = s_axis_tvalid;

wire               unused_m_axis_tready = m_axis_tready;
wire               unused_cmd_clear = cmd_clear;

logic [B-1:0]       hold_sample_r;
logic signed [31:0] current_value_r;
logic signed [31:0] current_value_readback_r;

logic signed [31:0] ramp_start_value_r;
logic signed [31:0] ramp_target_value_r;
logic signed [31:0] ramp_step_r;
logic [31:0]        ramp_duration_r;
logic [31:0]        ramp_base_index_r;

logic signed [31:0] ramp_pipe_start_r;
logic signed [31:0] ramp_pipe_target_r;
logic signed [31:0] ramp_pipe_step_r;
logic [31:0]        ramp_pipe_duration_r;
logic [31:0]        ramp_pipe_base_index_r;
logic               ramp_pipe_last_r;
logic               ramp_pipe_valid_r;

logic [N_PTS*B-1:0] ramp_word_pipe_r;
logic               ramp_word_pipe_last_r;
logic               ramp_word_pipe_valid_r;

function automatic logic [31:0] normalize_duration;
   input logic [31:0] duration;
   begin
      normalize_duration = (duration == 32'd0) ? 32'd1 : duration;
   end
endfunction

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
   input logic [31:0] base_index;
   input logic [31:0] duration;
   logic [32:0] next_base_ext;
   logic [32:0] duration_ext;
   begin
      next_base_ext = {1'b0, base_index} + {1'b0, N_PTS_U32};
      duration_ext = {1'b0, duration};
      ramp_base_is_last = (next_base_ext >= duration_ext);
   end
endfunction

function automatic logic [B-1:0] sat_fixed64;
   input logic signed [63:0] fixed_value;
   logic signed [63:0] int_value;
   logic signed [63:0] max_sample;
   logic signed [63:0] min_sample;
   begin
      int_value = fixed_value >>> FRAC;
      max_sample = (64'sd1 <<< (B-1)) - 64'sd1;
      min_sample = -(64'sd1 <<< (B-1));

      if (int_value > max_sample)
         sat_fixed64 = {1'b0, {(B-1){1'b1}}};
      else if (int_value < min_sample)
         sat_fixed64 = {1'b1, {(B-1){1'b0}}};
      else
         sat_fixed64 = int_value[B-1:0];
   end
endfunction

function automatic logic [N_PTS*B-1:0] ramp_word;
   input logic signed [31:0] start_value;
   input logic signed [31:0] target_value;
   input logic [31:0] duration;
   input logic signed [31:0] step;
   input logic [31:0] base_index;
   logic [N_PTS*B-1:0] word;
   logic [31:0] sample_index;
   logic signed [63:0] fixed_value;
   logic signed [63:0] start_fixed;
   logic signed [63:0] step_ext;
   logic signed [63:0] sample_index_ext;
   begin
      word = {N_PTS*B{1'b0}};
      start_fixed = {{32{start_value[31]}}, start_value} <<< FRAC;
      step_ext = {{32{step[31]}}, step};

      for (int i = 0; i < N_PTS; i = i + 1) begin
         sample_index = base_index + i;
         sample_index_ext = {32'd0, sample_index};

         if (duration <= 32'd1 || sample_index >= duration - 32'd1) begin
            word[i*B +: B] = sat_int32(target_value);
         end
         else begin
            fixed_value = start_fixed + (step_ext * sample_index_ext);
            word[i*B +: B] = sat_fixed64(fixed_value);
         end
      end

      ramp_word = word;
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

wire [31:0] cmd_duration_norm = normalize_duration(cmd_duration);
wire [B-1:0] cmd_target_sample = sat_int32(cmd_target);
wire [B-1:0] cmd_set_hold_sample = cmd_hold_zero ? {B{1'b0}} : cmd_target_sample;
wire [B-1:0] axi_override_sample = sat_int32(axi_override_value);
wire [N_PTS*B-1:0] hold_word = sample_word(hold_sample_r);
wire [N_PTS*B-1:0] cmd_set_word = sample_word(cmd_target_sample);
wire [N_PTS*B-1:0] axi_override_word = sample_word(axi_override_sample);
wire [31:0] ramp_pipe_next_base_index = ramp_pipe_base_index_r + N_PTS_U32;
wire [N_PTS*B-1:0] ramp_pipe_word =
   ramp_word(ramp_pipe_start_r, ramp_pipe_target_r, ramp_pipe_duration_r,
             ramp_pipe_step_r, ramp_pipe_base_index_r);

always_comb begin
   s_axis_tready = 1'b1;
   status_o = 32'd0;
   if (aresetn) begin
      status_o[0] = (state == IDLE_ST);
      status_o[1] = (state == RAMP_ST);
      status_o[2] = m_axis_tvalid;
      status_o[3] = s_axis_tready;
   end
   current_value_o = current_value_readback_r;
end

always_ff @(posedge aclk) begin
   if (!aresetn) begin
      state               <= IDLE_ST;
      hold_sample_r       <= {B{1'b0}};
      current_value_r     <= 32'sd0;
      current_value_readback_r <= 32'sd0;
      ramp_start_value_r  <= 32'sd0;
      ramp_target_value_r <= 32'sd0;
      ramp_step_r         <= 32'sd0;
      ramp_duration_r     <= 32'd1;
      ramp_base_index_r   <= 32'd0;
      ramp_pipe_start_r   <= 32'sd0;
      ramp_pipe_target_r  <= 32'sd0;
      ramp_pipe_step_r    <= 32'sd0;
      ramp_pipe_duration_r <= 32'd1;
      ramp_pipe_base_index_r <= 32'd0;
      ramp_pipe_last_r    <= 1'b0;
      ramp_pipe_valid_r   <= 1'b0;
      ramp_word_pipe_r    <= {N_PTS*B{1'b0}};
      ramp_word_pipe_last_r <= 1'b0;
      ramp_word_pipe_valid_r <= 1'b0;
      m_axis_tdata        <= {N_PTS*B{1'b0}};
      m_axis_tvalid       <= 1'b0;
   end
   else begin
      m_axis_tvalid <= 1'b1;
      m_axis_tdata  <= hold_word;
      current_value_readback_r <= current_value_r;

      if (axi_override_valid) begin
         m_axis_tdata        <= axi_override_word;
         hold_sample_r       <= axi_override_sample;
         current_value_r     <= axi_override_value;
         current_value_readback_r <= axi_override_value;
         ramp_start_value_r  <= axi_override_value;
         ramp_target_value_r <= axi_override_value;
         ramp_step_r         <= 32'sd0;
         ramp_duration_r     <= 32'd1;
         ramp_base_index_r   <= 32'd0;
         ramp_pipe_valid_r   <= 1'b0;
         ramp_pipe_last_r    <= 1'b0;
         ramp_word_pipe_valid_r <= 1'b0;
         ramp_word_pipe_last_r <= 1'b0;
         state               <= IDLE_ST;
      end
      else begin
         case (state)
            IDLE_ST: begin
               if (cmd_valid) begin
                  case (cmd_opcode)
                     OP_SET: begin
                        m_axis_tdata    <= cmd_set_word;
                        hold_sample_r   <= cmd_set_hold_sample;
                        current_value_r <= cmd_hold_zero ? 32'sd0 : cmd_target;
                        current_value_readback_r <= cmd_target;
                        ramp_pipe_valid_r <= 1'b0;
                        ramp_word_pipe_valid_r <= 1'b0;
                        state           <= IDLE_ST;
                     end

                     OP_RAMP: begin
                        ramp_start_value_r  <= current_value_r;
                        ramp_target_value_r <= cmd_target;
                        ramp_step_r         <= cmd_step;
                        ramp_duration_r     <= cmd_duration_norm;
                        ramp_base_index_r   <= 32'd0;
                        ramp_pipe_start_r   <= current_value_r;
                        ramp_pipe_target_r  <= cmd_target;
                        ramp_pipe_step_r    <= cmd_step;
                        ramp_pipe_duration_r <= cmd_duration_norm;
                        ramp_pipe_base_index_r <= 32'd0;
                        ramp_pipe_last_r    <= ramp_base_is_last(32'd0, cmd_duration_norm);
                        ramp_pipe_valid_r   <= 1'b1;
                        ramp_word_pipe_valid_r <= 1'b0;
                        ramp_word_pipe_last_r <= 1'b0;
                        state               <= RAMP_ST;
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
               if (ramp_word_pipe_valid_r) begin
                  m_axis_tdata <= ramp_word_pipe_r;
                  current_value_readback_r <= lane_to_i32(ramp_word_pipe_r[B-1:0]);

                  if (ramp_word_pipe_last_r) begin
                     hold_sample_r   <= sat_int32(ramp_target_value_r);
                     current_value_r <= ramp_target_value_r;
                     ramp_pipe_valid_r <= 1'b0;
                     ramp_word_pipe_valid_r <= 1'b0;
                     state           <= IDLE_ST;
                  end
               end

               if (ramp_pipe_valid_r) begin
                  ramp_word_pipe_r <= ramp_pipe_word;
                  ramp_word_pipe_valid_r <= 1'b1;
                  ramp_word_pipe_last_r <= ramp_pipe_last_r;
                  ramp_base_index_r <= ramp_pipe_base_index_r;

                  if (ramp_pipe_last_r) begin
                     ramp_pipe_valid_r <= 1'b0;
                  end
                  else begin
                     ramp_pipe_base_index_r <= ramp_pipe_next_base_index;
                     ramp_pipe_last_r <= ramp_base_is_last(ramp_pipe_next_base_index,
                                                           ramp_pipe_duration_r);
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
