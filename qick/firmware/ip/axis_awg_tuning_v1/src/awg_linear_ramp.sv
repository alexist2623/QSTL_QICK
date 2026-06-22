`default_nettype none

// Deterministic ramp helper retained for standalone builds.
//
// awg_tuning_ctrl now implements the RFDC streaming scheduler directly and no
// longer instantiates this module. This helper intentionally has no AXIS
// output handshake: once started, it advances one N_DDS-wide word per aclk.

module awg_linear_ramp
   #(
      parameter int N_DDS = 16,
      parameter int B = 16,
      parameter int FRAC = 16,
      parameter int VALUE_WIDTH = 32,
      parameter int STEP_WIDTH = 32,
      parameter int DURATION_WIDTH = 32
   )
   (
      // Reset and clock.
      input  wire                              aresetn,
      input  wire                              aclk,

      // One-cycle load pulse.
      input  wire                              start_i,
      input  wire signed [VALUE_WIDTH-1:0]     y_start_i,
      input  wire signed [VALUE_WIDTH-1:0]     y_target_i,
      input  wire signed [STEP_WIDTH-1:0]      step_i,
      input  wire        [DURATION_WIDTH-1:0]  duration_i,

      // Deterministic output word.
      output logic [N_DDS*B-1:0]               m_axis_tdata_o,

      // Status.
      output logic                             active_o,
      output logic                             done_o
   );

localparam int LANE_BITS = (N_DDS <= 1) ? 1 : $clog2(N_DDS);
localparam int ACC_WIDTH = VALUE_WIDTH + FRAC + LANE_BITS + 4;

localparam logic signed [ACC_WIDTH-1:0] MAX_SAMPLE =
   {{(ACC_WIDTH-B){1'b0}}, 1'b0, {(B-1){1'b1}}};
localparam logic signed [ACC_WIDTH-1:0] MIN_SAMPLE =
   {{(ACC_WIDTH-B){1'b1}}, 1'b1, {(B-1){1'b0}}};

logic                             active_r;
logic [DURATION_WIDTH-1:0]        duration_r;
logic [DURATION_WIDTH-1:0]        sample_index_r;
logic signed [ACC_WIDTH-1:0]      acc_r;
logic signed [ACC_WIDTH-1:0]      step_r;
logic signed [ACC_WIDTH-1:0]      target_fixed_r;

logic [DURATION_WIDTH:0]          next_sample_index;
logic                             last_word;
logic signed [ACC_WIDTH-1:0]      word_step;
localparam logic [DURATION_WIDTH:0] N_DDS_EXT = N_DDS;
localparam logic [DURATION_WIDTH-1:0] N_DDS_TRUNC = N_DDS;

function automatic logic signed [ACC_WIDTH-1:0] value_to_fixed;
   input logic signed [VALUE_WIDTH-1:0] value;
   logic signed [ACC_WIDTH-1:0] value_ext;
   begin
      value_ext = {{(ACC_WIDTH-VALUE_WIDTH){value[VALUE_WIDTH-1]}}, value};
      value_to_fixed = value_ext <<< FRAC;
   end
endfunction

function automatic logic signed [ACC_WIDTH-1:0] step_extend;
   input logic signed [STEP_WIDTH-1:0] step;
   begin
      step_extend = {{(ACC_WIDTH-STEP_WIDTH){step[STEP_WIDTH-1]}}, step};
   end
endfunction

function automatic logic [B-1:0] sat_fixed;
   input logic signed [ACC_WIDTH-1:0] fixed_value;
   logic signed [ACC_WIDTH-1:0] int_value;
   begin
      int_value = fixed_value >>> FRAC;

      if (int_value > MAX_SAMPLE)
         sat_fixed = {1'b0, {(B-1){1'b1}}};
      else if (int_value < MIN_SAMPLE)
         sat_fixed = {1'b1, {(B-1){1'b0}}};
      else
         sat_fixed = int_value[B-1:0];
   end
endfunction

assign next_sample_index = {1'b0, sample_index_r} + N_DDS_EXT;
assign last_word = (next_sample_index >= {1'b0, duration_r});
assign word_step = step_r * N_DDS;

generate
genvar gi;
   for (gi = 0; gi < N_DDS; gi = gi + 1) begin : GEN_lane
      localparam int LANE = gi;
      localparam logic [DURATION_WIDTH:0] LANE_EXT = gi;

      logic [DURATION_WIDTH:0] lane_index;
      logic [DURATION_WIDTH:0] final_index;
      logic signed [ACC_WIDTH-1:0] lane_fixed;
      logic [B-1:0] lane_sample;

      always_comb begin
         lane_index = {1'b0, sample_index_r} + LANE_EXT;
         final_index = {1'b0, duration_r} - {{DURATION_WIDTH{1'b0}}, 1'b1};
         lane_fixed = acc_r + (step_r * LANE);

         if (!active_r)
            lane_sample = {B{1'b0}};
         else if (lane_index >= final_index)
            lane_sample = sat_fixed(target_fixed_r);
         else
            lane_sample = sat_fixed(lane_fixed);
      end

      always_comb begin
         m_axis_tdata_o[LANE*B +: B] = lane_sample;
      end
   end
endgenerate

always_ff @(posedge aclk) begin
   if (!aresetn) begin
      active_r       <= 1'b0;
      duration_r     <= {DURATION_WIDTH{1'b0}};
      sample_index_r <= {DURATION_WIDTH{1'b0}};
      acc_r          <= {ACC_WIDTH{1'b0}};
      step_r         <= {ACC_WIDTH{1'b0}};
      target_fixed_r <= {ACC_WIDTH{1'b0}};
      done_o         <= 1'b0;
   end
   else begin
      done_o <= 1'b0;

      if (start_i) begin
         active_r       <= 1'b1;
         duration_r     <= (duration_i == {DURATION_WIDTH{1'b0}}) ? {{(DURATION_WIDTH-1){1'b0}}, 1'b1} : duration_i;
         sample_index_r <= {DURATION_WIDTH{1'b0}};
         acc_r          <= value_to_fixed(y_start_i);
         step_r         <= step_extend(step_i);
         target_fixed_r <= value_to_fixed(y_target_i);
      end
      else if (active_r) begin
         if (last_word) begin
            active_r       <= 1'b0;
            sample_index_r <= {DURATION_WIDTH{1'b0}};
            acc_r          <= target_fixed_r;
            done_o         <= 1'b1;
         end
         else begin
            sample_index_r <= sample_index_r + N_DDS_TRUNC;
            acc_r          <= acc_r + word_step;
         end
      end
   end
end

assign active_o = active_r;

endmodule

`default_nettype wire
