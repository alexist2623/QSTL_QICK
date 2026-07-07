// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`default_nettype none

module axi_slv_awg_tuning_v1
   (
      input  wire         s_axi_aclk,
      input  wire         s_axi_aresetn,

      input  wire [5:0]   s_axi_awaddr,
      input  wire [2:0]   s_axi_awprot,
      input  wire         s_axi_awvalid,
      output logic        s_axi_awready,

      input  wire [31:0]  s_axi_wdata,
      input  wire [3:0]   s_axi_wstrb,
      input  wire         s_axi_wvalid,
      output logic        s_axi_wready,

      output logic [1:0]  s_axi_bresp,
      output logic        s_axi_bvalid,
      input  wire         s_axi_bready,

      input  wire [5:0]   s_axi_araddr,
      input  wire [2:0]   s_axi_arprot,
      input  wire         s_axi_arvalid,
      output logic        s_axi_arready,

      output logic [31:0] s_axi_rdata,
      output logic [1:0]  s_axi_rresp,
      output logic        s_axi_rvalid,
      input  wire         s_axi_rready,

      output logic signed [31:0] override_value,
      output logic               override_req_toggle,
      input  wire                override_ack_toggle,

      input  wire signed [31:0]  current_value_snapshot,
      input  wire [31:0]         status_snapshot
   );

localparam logic [3:0] CURRENT_VALUE_WORD = 4'd0;
localparam logic [3:0] STATUS_WORD        = 4'd1;

logic [1:0] override_ack_sync;
logic       override_ack_seen;
logic       override_pending;
logic       override_seen;

wire [3:0] write_word = s_axi_awaddr[5:2];
wire [3:0] read_word  = s_axi_araddr[5:2];
wire       can_accept_write = !s_axi_bvalid && !override_pending;
wire       write_accept = can_accept_write && s_axi_awvalid && s_axi_wvalid;
wire [31:0] status_read = (status_snapshot & 32'hFFFF_FFCF)
                          | {26'd0, override_seen, override_pending, 4'd0};

wire unused_axi_prot = |s_axi_awprot | |s_axi_arprot;

function automatic logic [31:0] apply_wstrb;
   input logic [31:0] old_value;
   input logic [31:0] new_value;
   input logic [3:0]  wstrb;
   logic [31:0] merged;
   begin
      merged = old_value;
      for (int i = 0; i < 4; i = i + 1) begin
         if (wstrb[i])
            merged[i*8 +: 8] = new_value[i*8 +: 8];
      end
      apply_wstrb = merged;
   end
endfunction

always_ff @(posedge s_axi_aclk) begin
   if (!s_axi_aresetn) begin
      override_ack_sync  <= 2'b00;
      override_ack_seen  <= 1'b0;
      override_pending   <= 1'b0;
      override_seen      <= 1'b0;
      override_value     <= 32'sd0;
      override_req_toggle <= 1'b0;

      s_axi_awready <= 1'b0;
      s_axi_wready  <= 1'b0;
      s_axi_bresp   <= 2'b00;
      s_axi_bvalid  <= 1'b0;
      s_axi_arready <= 1'b0;
      s_axi_rdata   <= 32'd0;
      s_axi_rresp   <= 2'b00;
      s_axi_rvalid  <= 1'b0;
   end
   else begin
      override_ack_sync <= {override_ack_sync[0], override_ack_toggle};
      s_axi_awready <= 1'b0;
      s_axi_wready  <= 1'b0;
      s_axi_arready <= 1'b0;

      if (override_ack_sync[1] != override_ack_seen) begin
         override_ack_seen <= override_ack_sync[1];
         override_pending  <= 1'b0;
         override_seen     <= 1'b1;
      end

      if (s_axi_bvalid && s_axi_bready)
         s_axi_bvalid <= 1'b0;

      if (write_accept) begin
         s_axi_awready <= 1'b1;
         s_axi_wready  <= 1'b1;
         s_axi_bresp   <= 2'b00;
         s_axi_bvalid  <= 1'b1;

         if (write_word == CURRENT_VALUE_WORD) begin
            override_value      <= $signed(apply_wstrb(override_value, s_axi_wdata, s_axi_wstrb));
            override_req_toggle <= ~override_req_toggle;
            override_pending    <= 1'b1;
         end
      end

      if (s_axi_rvalid && s_axi_rready)
         s_axi_rvalid <= 1'b0;

      if (!s_axi_rvalid && s_axi_arvalid) begin
         s_axi_arready <= 1'b1;
         s_axi_rresp   <= 2'b00;
         s_axi_rvalid  <= 1'b1;

         case (read_word)
            CURRENT_VALUE_WORD: s_axi_rdata <= current_value_snapshot;
            STATUS_WORD:        s_axi_rdata <= status_read;
            default:            s_axi_rdata <= 32'd0;
         endcase
      end
   end
end

endmodule

`default_nettype wire
