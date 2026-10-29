// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`default_nettype none

module axis_awg_tuning_v7
   #(
      // Number of parallel 16-bit samples per output word.
      parameter int N_PTS = 16,

      // Output sample width.
      parameter int B = 16,

      // Fractional bits in the signed fixed-point ramp step.
      // With the default command field layout this is a signed 14.18 step.
      parameter int FRAC = 18,

      // tProcessor v1 realtime output width.
      parameter int CMD_WIDTH = 160,

      // RAMP command datapath field widths.
      parameter int STEP_WIDTH = 32,
      parameter int DURATION_WIDTH = 23,
      parameter int FIXED_WIDTH = 48,

      // Extra pass-through y <= y stages after the DSP lane add stage.
      parameter int EXTRA_Y_PIPE_STAGES = 3,
      parameter int RC_PRECOMP_VERSION = 1,
      parameter int DC_AREA_VERSION = 1,
      parameter int DC_AREA_BITS = 48
   )
   (
      // AXI-Lite slave for software/debug current-value override.
      input  wire                   s_axi_aclk,
      input  wire                   s_axi_aresetn,
      input  wire [5:0]             s_axi_awaddr,
      input  wire [2:0]             s_axi_awprot,
      input  wire                   s_axi_awvalid,
      output logic                  s_axi_awready,
      input  wire [31:0]            s_axi_wdata,
      input  wire [3:0]             s_axi_wstrb,
      input  wire                   s_axi_wvalid,
      output logic                  s_axi_wready,
      output logic [1:0]            s_axi_bresp,
      output logic                  s_axi_bvalid,
      input  wire                   s_axi_bready,
      input  wire [5:0]             s_axi_araddr,
      input  wire [2:0]             s_axi_arprot,
      input  wire                   s_axi_arvalid,
      output logic                  s_axi_arready,
      output logic [31:0]           s_axi_rdata,
      output logic [1:0]            s_axi_rresp,
      output logic                  s_axi_rvalid,
      input  wire                   s_axi_rready,

      // Reset and clock.
      input  wire                   aresetn,
      input  wire                   aclk,

      // AXIS slave command input.
      input  wire [CMD_WIDTH-1:0]   s_axis_tdata,
      input  wire                   s_axis_tvalid,
      output wire                   s_axis_tready,

      // AXIS master sample output.
      output wire [N_PTS*B-1:0]     m_axis_tdata,
      output wire                   m_axis_tvalid,
      input  wire                   m_axis_tready
   );

logic signed [31:0] override_value_axi;
logic               override_req_toggle_axi;
logic               override_ack_toggle_aclk;

(* ASYNC_REG = "TRUE" *) logic [1:0] override_req_sync_aclk;
logic                    override_req_seen_aclk;
logic signed [31:0]      override_value_aclk;
logic                    override_valid_aclk;

logic signed [31:0] ctrl_current_value_aclk;
logic [31:0]        ctrl_status_aclk;
wire [31:0]        core_status;
wire [N_PTS*B-1:0] core_samples;
wire core_valid;
logic [31:0] rc_coefficient;
logic rc_enabled, rc_clear;
wire rc_clipped;
wire [N_PTS*B-1:0] area_samples;
wire area_valid, area_clear_rc, area_done, area_enabled, area_busy, area_fault;
wire signed [63:0] area_sum;
wire [31:0] area_completed_shots;
// Compensator controls observe the same command timeline as the common
// SET/RAMP core pipeline. At EXTRA=3 this is eleven clocks for every opcode.
localparam integer COMMAND_PIPELINE_CYCLES = EXTRA_Y_PIPE_STAGES + 8;
logic [CMD_WIDTH-1:0] command_pipe [0:COMMAND_PIPELINE_CYCLES-1];
logic [COMMAND_PIPELINE_CYCLES-1:0] command_valid_pipe;
wire [CMD_WIDTH-1:0] aligned_command = command_pipe[COMMAND_PIPELINE_CYCLES-1];
wire aligned_command_valid = command_valid_pipe[COMMAND_PIPELINE_CYCLES-1] && !override_valid_aclk;
always_ff @(posedge aclk) begin
   if (!aresetn || override_valid_aclk) begin
      command_valid_pipe <= '0;
      for (int p=0;p<COMMAND_PIPELINE_CYCLES;p=p+1) command_pipe[p] <= '0;
   end else begin
      command_pipe[0] <= s_axis_tdata;
      command_valid_pipe[0] <= s_axis_tvalid;
      for (int p=1;p<COMMAND_PIPELINE_CYCLES;p=p+1) begin
         command_pipe[p] <= command_pipe[p-1];
         command_valid_pipe[p] <= command_valid_pipe[p-1];
      end
   end
end

assign ctrl_status_aclk=core_status |
    {13'd0,area_fault,area_busy,area_enabled,6'd0,rc_clipped,rc_enabled,8'd0};

v7_awg_dc_area #(.N_PTS(N_PTS),.AREA_WIDTH(DC_AREA_BITS)) dc_area (
    .clk(aclk),.rstn(aresetn),.valid_i(core_valid),.samples_i(core_samples),
    .command_i(aligned_command),.command_valid_i(aligned_command_valid),
    .abort_i(override_valid_aclk && override_value_aclk==0),
    .samples_o(area_samples),.valid_o(area_valid),.clear_rc_o(area_clear_rc),
    .done_o(area_done),.enabled_o(area_enabled),.busy_o(area_busy),
    .fault_o(area_fault),.area_o(area_sum),.completed_shots_o(area_completed_shots));

// Atomic realtime configuration: IDLE opcode plus bit 149 distinguishes it
// from legacy no-ops. target holds round(2^48/(2*tau*scalar_sample_rate)).
// Control bit 146 enables RC; bit 147 explicitly clears its history.
always_ff @(posedge aclk) begin
   if(!aresetn) begin rc_coefficient<=0; rc_enabled<=0; rc_clear<=0; end
   else begin
      rc_clear<=0;
      if(RC_PRECOMP_VERSION!=0 && aligned_command_valid && aligned_command[149] && aligned_command[145:144]==2'b11) begin
         rc_coefficient<=aligned_command[31:0];
         rc_enabled<=aligned_command[146]; rc_clear<=aligned_command[147];
      end
      // A software zero override is an explicit stop, unlike an AXIS SET 0.
      if(override_valid_aclk && override_value_aclk==0) begin rc_enabled<=0; rc_clear<=1; end
   end
end
generate if(RC_PRECOMP_VERSION!=0) begin: GEN_RC
   v7_awg_rc_precomp #(.N_PTS(N_PTS)) rc (
      .clk(aclk),.rstn(aresetn),.valid_i(area_valid),.active_i(1'b1),
      .enable_i(rc_enabled),.clear_i(rc_clear | area_clear_rc),.coefficient_i(rc_coefficient),
      .samples_i(area_samples),.samples_o(m_axis_tdata),.valid_o(m_axis_tvalid),.clipped_o(rc_clipped));
end else begin: GEN_LEGACY
   assign m_axis_tdata=area_samples; assign m_axis_tvalid=area_valid; assign rc_clipped=1'b0;
end endgenerate

logic signed [31:0] snapshot_current_value_aclk;
logic [31:0]        snapshot_status_aclk;
logic               snapshot_req_toggle_aclk;
(* ASYNC_REG = "TRUE" *) logic [1:0] snapshot_ack_sync_aclk;

(* ASYNC_REG = "TRUE" *) logic [1:0] snapshot_req_sync_axi;
logic                    snapshot_req_seen_axi;
logic                    snapshot_ack_toggle_axi;
logic signed [31:0]      snapshot_current_value_axi;
logic [31:0]             snapshot_status_axi;

v7_axi_slv_awg_tuning_v1 axi_slv_i
   (
      .s_axi_aclk             (s_axi_aclk               ),
      .s_axi_aresetn          (s_axi_aresetn            ),
      .s_axi_awaddr           (s_axi_awaddr             ),
      .s_axi_awprot           (s_axi_awprot             ),
      .s_axi_awvalid          (s_axi_awvalid            ),
      .s_axi_awready          (s_axi_awready            ),
      .s_axi_wdata            (s_axi_wdata              ),
      .s_axi_wstrb            (s_axi_wstrb              ),
      .s_axi_wvalid           (s_axi_wvalid             ),
      .s_axi_wready           (s_axi_wready             ),
      .s_axi_bresp            (s_axi_bresp              ),
      .s_axi_bvalid           (s_axi_bvalid             ),
      .s_axi_bready           (s_axi_bready             ),
      .s_axi_araddr           (s_axi_araddr             ),
      .s_axi_arprot           (s_axi_arprot             ),
      .s_axi_arvalid          (s_axi_arvalid            ),
      .s_axi_arready          (s_axi_arready            ),
      .s_axi_rdata            (s_axi_rdata              ),
      .s_axi_rresp            (s_axi_rresp              ),
      .s_axi_rvalid           (s_axi_rvalid             ),
      .s_axi_rready           (s_axi_rready             ),
      .override_value         (override_value_axi       ),
      .override_req_toggle    (override_req_toggle_axi  ),
      .override_ack_toggle    (override_ack_toggle_aclk ),
      .current_value_snapshot (snapshot_current_value_axi),
      .status_snapshot        (snapshot_status_axi      )
   );

always_ff @(posedge aclk) begin
   if (!aresetn) begin
      override_req_sync_aclk <= 2'b00;
      override_req_seen_aclk <= 1'b0;
      override_value_aclk    <= 32'sd0;
      override_valid_aclk    <= 1'b0;
      override_ack_toggle_aclk <= 1'b0;
   end
   else begin
      override_req_sync_aclk <= {override_req_sync_aclk[0], override_req_toggle_axi};
      override_valid_aclk <= 1'b0;

      if (override_req_sync_aclk[1] != override_req_seen_aclk) begin
         override_req_seen_aclk <= override_req_sync_aclk[1];
         override_value_aclk    <= override_value_axi;
         override_valid_aclk    <= 1'b1;
         override_ack_toggle_aclk <= ~override_ack_toggle_aclk;
      end
   end
end

// Snapshot current readback/status into the AXI-Lite clock domain. During
// output activity, CURRENT_VALUE_REG reads lane 0 of the emitted core word;
// otherwise it reads the physical held sample (not a pending logical target). The snapshot may lag by a
// few cycles but the bus is held stable during each CDC transfer.
always_ff @(posedge aclk) begin
   if (!aresetn) begin
      snapshot_current_value_aclk <= 32'sd0;
      snapshot_status_aclk        <= 32'd0;
      snapshot_req_toggle_aclk    <= 1'b0;
      snapshot_ack_sync_aclk      <= 2'b00;
   end
   else begin
      snapshot_ack_sync_aclk <= {snapshot_ack_sync_aclk[0], snapshot_ack_toggle_axi};
      if (snapshot_req_toggle_aclk == snapshot_ack_sync_aclk[1]) begin
         snapshot_current_value_aclk <= ctrl_current_value_aclk;
         snapshot_status_aclk        <= ctrl_status_aclk;
         snapshot_req_toggle_aclk    <= ~snapshot_req_toggle_aclk;
      end
   end
end

always_ff @(posedge s_axi_aclk) begin
   if (!s_axi_aresetn) begin
      snapshot_req_sync_axi      <= 2'b00;
      snapshot_req_seen_axi      <= 1'b0;
      snapshot_ack_toggle_axi    <= 1'b0;
      snapshot_current_value_axi <= 32'sd0;
      snapshot_status_axi        <= 32'd0;
   end
   else begin
      snapshot_req_sync_axi <= {snapshot_req_sync_axi[0], snapshot_req_toggle_aclk};
      if (snapshot_req_sync_axi[1] != snapshot_req_seen_axi) begin
         snapshot_req_seen_axi      <= snapshot_req_sync_axi[1];
         snapshot_current_value_axi <= snapshot_current_value_aclk;
         snapshot_status_axi        <= snapshot_status_aclk;
         snapshot_ack_toggle_axi    <= ~snapshot_ack_toggle_axi;
      end
   end
end

v7_awg_tuning_ctrl
   #(
      .N_PTS      (N_PTS    ),
      .B          (B        ),
      .FRAC       (FRAC     ),
      .CMD_WIDTH  (CMD_WIDTH),
      .STEP_WIDTH (STEP_WIDTH),
      .DURATION_WIDTH (DURATION_WIDTH),
      .FIXED_WIDTH (FIXED_WIDTH),
      .EXTRA_Y_PIPE_STAGES (EXTRA_Y_PIPE_STAGES)
   )
   awg_tuning_ctrl_i
   (
      // Reset and clock.
      .aresetn          (aresetn        ),
      .aclk             (aclk           ),

      // AXIS slave command input.
      .s_axis_tdata     (s_axis_tdata   ),
      .s_axis_tvalid    (s_axis_tvalid  ),
      .s_axis_tready    (s_axis_tready  ),
      .axi_override_value (override_value_aclk),
      .axi_override_valid (override_valid_aclk),

      // AXIS master sample output.
      .m_axis_tdata     (core_samples   ),
      .m_axis_tvalid    (core_valid  ),
      .m_axis_tready    (m_axis_tready  ),
      .current_value_o  (ctrl_current_value_aclk),
      .status_o         (core_status)
   );

endmodule

`default_nettype wire
