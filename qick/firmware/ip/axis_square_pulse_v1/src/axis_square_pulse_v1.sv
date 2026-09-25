// Phase-coherent square DDS with AXIS realtime updates and AXI-Lite mute.
`timescale 1ns/1ps
`default_nettype none
module axis_square_pulse_v1 #(
    parameter integer N_PTS = 16,
    parameter integer B = 16,
    parameter integer CMD_WIDTH = 160,
    parameter integer RC_PRECOMP_VERSION = 1
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


    logic mute_req, mute_ack;
    (* ASYNC_REG = "TRUE" *) logic [1:0] req_sync, ack_sync, enabled_sync;
    logic req_seen, mute;
    wire enabled;
    wire [N_PTS*16-1:0] raw_samples;
    wire [47:0] rc_half_step;
    wire rc_enabled, rc_clear, samples_active, rc_clipped;
    (* ASYNC_REG="TRUE" *) logic [1:0] rc_clipped_sync;
    logic have_aw, have_w;
    logic [5:0] awaddr;
    logic [3:0] wstrb;
    assign s_axis_tready = aresetn;
    generate if(RC_PRECOMP_VERSION!=0) begin: GEN_RC
        square_rc_precomp #(.N_PTS(N_PTS)) rc (
            .clk(aclk),.rstn(aresetn),.valid_i(aresetn),.active_i(samples_active),
            .enable_i(rc_enabled),.clear_i(rc_clear),.half_step_i(rc_half_step),
            .samples_i(raw_samples),.samples_o(m_axis_tdata),.valid_o(m_axis_tvalid),.clipped_o(rc_clipped));
    end else begin: GEN_LEGACY
        assign m_axis_tdata=raw_samples; assign m_axis_tvalid=aresetn; assign rc_clipped=1'b0;
    end endgenerate
    // The DAC is a realtime sink: its ready cannot pause phase accumulation.
    // There is no waveform FIFO, exactly as for axis_awg_tuning_v1.
    square_dds #(.N_PTS(N_PTS)) dds (
        .aclk(aclk), .aresetn(aresetn), .command(s_axis_tdata[159:0]),
        .command_valid(s_axis_tvalid && s_axis_tready), .mute(mute),
        .enabled(enabled), .samples(raw_samples),.rc_half_step(rc_half_step),
        .rc_enabled(rc_enabled),.rc_clear(rc_clear),.samples_active(samples_active)
    );
    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            req_sync <= 0; req_seen <= 0; mute_ack <= 0; mute <= 0;
        end else begin
            req_sync <= {req_sync[0], mute_req};
            mute <= 0;
            if (req_sync[1] != req_seen) begin
                req_seen <= req_sync[1]; mute_ack <= req_sync[1]; mute <= 1;
            end
        end
    end
    // AW and W can arrive independently. Requests and responses are held
    // until their respective handshakes. One software mute can be in flight.
    always_comb begin
        s_axi_awready = s_axi_aresetn && !have_aw && !s_axi_bvalid;
        s_axi_wready = s_axi_aresetn && !have_w && !s_axi_bvalid;
        s_axi_arready = s_axi_aresetn && !s_axi_rvalid;
    end
    always_ff @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            mute_req <= 0; ack_sync <= 0; enabled_sync <= 0;
            rc_clipped_sync<=0;
            have_aw <= 0; have_w <= 0; awaddr <= 0; wstrb <= 0;
            s_axi_bvalid <= 0; s_axi_bresp <= 0;
            s_axi_rvalid <= 0; s_axi_rresp <= 0; s_axi_rdata <= 0;
        end else begin
            ack_sync <= {ack_sync[0], mute_ack};
            enabled_sync <= {enabled_sync[0], enabled};
            rc_clipped_sync<={rc_clipped_sync[0],rc_clipped};
            if (s_axi_awvalid && s_axi_awready) begin
                have_aw <= 1; awaddr <= s_axi_awaddr;
            end
            if (s_axi_wvalid && s_axi_wready) begin
                have_w <= 1; wstrb <= s_axi_wstrb;
            end
            if (s_axi_bvalid && s_axi_bready) s_axi_bvalid <= 0;
            if (have_aw && have_w && !s_axi_bvalid && mute_req == ack_sync[1]) begin
                have_aw <= 0; have_w <= 0; s_axi_bvalid <= 1;
                s_axi_bresp <= (awaddr[5:2] == 0) ? 0 : 2;
                if (awaddr[5:2] == 0 && |wstrb) mute_req <= ~mute_req;
            end
            if (s_axi_rvalid && s_axi_rready) s_axi_rvalid <= 0;
            if (s_axi_arvalid && s_axi_arready) begin
                s_axi_rvalid <= 1; s_axi_rresp <= 0;
                case (s_axi_araddr[5:2])
                    0: s_axi_rdata <= 32'h53515031; // "SQP1"; write = mute
                    1: s_axi_rdata <= {29'd0,rc_clipped_sync[1],(mute_req != ack_sync[1]), enabled_sync[1]};
                    2: s_axi_rdata <= 4+((RC_PRECOMP_VERSION!=0) ? 11 : 0);
                    3: s_axi_rdata <= N_PTS;
                    4: s_axi_rdata <= RC_PRECOMP_VERSION;
                    default: begin s_axi_rdata <= 0; s_axi_rresp <= 2; end
                endcase
            end
        end
    end
endmodule
`default_nettype wire
