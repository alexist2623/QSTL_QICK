`timescale 1ns / 1ps
// Production AWG v4, DDS v6 (vendor model), and sum v3 datapaths.
// Commands come only from the real CPU and actual TMUX in tb_cpu_tmux_v7.
module cpu_native_pair #(
   parameter integer PAIR = 0
) (
   input wire clk,
   rstn,
   input wire [159:0] acmd,
   rcmd,
   input wire av,
   rv,
   output wire [255:0] awg_raw,
   rf_raw,
   awg_final,
   rf_final,
   combined
);
wire awvalid, rfvalid;
axis_awg_tuning_v7 #(
   .DC_AREA_BITS(48),
   .EXTRA_Y_PIPE_STAGES(3)
) awg (
   .s_axi_aclk(clk),
   .s_axi_aresetn(rstn),
   .s_axi_awaddr(6'd0),
   .s_axi_awprot(3'd0),
   .s_axi_awvalid(1'b0),
   .s_axi_wdata(32'd0),
   .s_axi_wstrb(4'd0),
   .s_axi_wvalid(1'b0),
   .s_axi_bready(1'b1),
   .s_axi_araddr(6'd0),
   .s_axi_arprot(3'd0),
   .s_axi_arvalid(1'b0),
   .s_axi_rready(1'b1),
   .aclk(clk),
   .aresetn(rstn),
   .s_axis_tdata(acmd),
   .s_axis_tvalid(av),
   .m_axis_tdata(awg_raw),
   .m_axis_tvalid(awvalid),
   .m_axis_tready(1'b1)
);
sim_axis_signal_gen_v6_axis_signal_gen_v6 rf (
   .s_axi_aclk(clk),
   .s_axi_aresetn(rstn),
   .s_axi_awaddr(6'd0),
   .s_axi_awprot(3'd0),
   .s_axi_awvalid(1'b0),
   .s_axi_wdata(32'd0),
   .s_axi_wstrb(4'd0),
   .s_axi_wvalid(1'b0),
   .s_axi_bready(1'b1),
   .s_axi_araddr(6'd0),
   .s_axi_arprot(3'd0),
   .s_axi_arvalid(1'b0),
   .s_axi_rready(1'b1),
   .s0_axis_aclk(clk),
   .s0_axis_aresetn(rstn),
   .s0_axis_tdata(32'd0),
   .s0_axis_tvalid(1'b0),
   .aclk(clk),
   .aresetn(rstn),
   .s1_axis_tdata(rcmd),
   .s1_axis_tvalid(rv),
   .m_axis_tdata(rf_raw),
   .m_axis_tvalid(rfvalid),
   .m_axis_tready(1'b1)
);
axis_output_sum_v7 #(
   .BYPASS(1)
) awg_only (
   .aclk(clk),
   .aresetn(rstn),
   .s0_axis_tdata(awg_raw),
   .s0_axis_tvalid(awvalid),
   .s1_axis_tdata(256'd0),
   .s1_axis_tvalid(1'b0),
   .m_axis_tdata(awg_final),
   .m_axis_tready(1'b1)
);
axis_output_sum_v7 rf_only (
   .aclk(clk),
   .aresetn(rstn),
   .s0_axis_tdata(256'd0),
   .s0_axis_tvalid(1'b0),
   .s1_axis_tdata(rf_raw),
   .s1_axis_tvalid(rfvalid),
   .m_axis_tdata(rf_final),
   .m_axis_tready(1'b1)
);
axis_output_sum_v7 sum (
   .aclk(clk),
   .aresetn(rstn),
   .s0_axis_tdata(awg_raw),
   .s0_axis_tvalid(awvalid),
   .s1_axis_tdata(rf_raw),
   .s1_axis_tvalid(rfvalid),
   .m_axis_tdata(combined),
   .m_axis_tready(1'b1)
);
endmodule
