//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//Copyright 2022-2023 Advanced Micro Devices, Inc. All Rights Reserved.
//--------------------------------------------------------------------------------
//Tool Version: Vivado v.2023.1 (win64) Build 3865809 Sun May  7 15:05:29 MDT 2023
//Date        : Tue Oct  6 23:25:42 2026
//Host        : ECE-CDW-JS03 running 64-bit major release  (build 9200)
//Command     : generate_target sim_bd_wrapper.bd
//Design      : sim_bd_wrapper
//Purpose     : IP block netlist
//--------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

module rc_wrapper
   (clk_300000000,
    clk_333250000,
    clk_99999985,
    ext_axis_avg_buffer_0_s_axi_araddr,
    ext_axis_avg_buffer_0_s_axi_arprot,
    ext_axis_avg_buffer_0_s_axi_arready,
    ext_axis_avg_buffer_0_s_axi_arvalid,
    ext_axis_avg_buffer_0_s_axi_awaddr,
    ext_axis_avg_buffer_0_s_axi_awprot,
    ext_axis_avg_buffer_0_s_axi_awready,
    ext_axis_avg_buffer_0_s_axi_awvalid,
    ext_axis_avg_buffer_0_s_axi_bready,
    ext_axis_avg_buffer_0_s_axi_bresp,
    ext_axis_avg_buffer_0_s_axi_bvalid,
    ext_axis_avg_buffer_0_s_axi_rdata,
    ext_axis_avg_buffer_0_s_axi_rready,
    ext_axis_avg_buffer_0_s_axi_rresp,
    ext_axis_avg_buffer_0_s_axi_rvalid,
    ext_axis_avg_buffer_0_s_axi_wdata,
    ext_axis_avg_buffer_0_s_axi_wready,
    ext_axis_avg_buffer_0_s_axi_wstrb,
    ext_axis_avg_buffer_0_s_axi_wvalid,
    ext_axis_avg_buffer_1_s_axi_araddr,
    ext_axis_avg_buffer_1_s_axi_arprot,
    ext_axis_avg_buffer_1_s_axi_arready,
    ext_axis_avg_buffer_1_s_axi_arvalid,
    ext_axis_avg_buffer_1_s_axi_awaddr,
    ext_axis_avg_buffer_1_s_axi_awprot,
    ext_axis_avg_buffer_1_s_axi_awready,
    ext_axis_avg_buffer_1_s_axi_awvalid,
    ext_axis_avg_buffer_1_s_axi_bready,
    ext_axis_avg_buffer_1_s_axi_bresp,
    ext_axis_avg_buffer_1_s_axi_bvalid,
    ext_axis_avg_buffer_1_s_axi_rdata,
    ext_axis_avg_buffer_1_s_axi_rready,
    ext_axis_avg_buffer_1_s_axi_rresp,
    ext_axis_avg_buffer_1_s_axi_rvalid,
    ext_axis_avg_buffer_1_s_axi_wdata,
    ext_axis_avg_buffer_1_s_axi_wready,
    ext_axis_avg_buffer_1_s_axi_wstrb,
    ext_axis_avg_buffer_1_s_axi_wvalid,
    ext_axis_avg_buffer_2_s_axi_araddr,
    ext_axis_avg_buffer_2_s_axi_arprot,
    ext_axis_avg_buffer_2_s_axi_arready,
    ext_axis_avg_buffer_2_s_axi_arvalid,
    ext_axis_avg_buffer_2_s_axi_awaddr,
    ext_axis_avg_buffer_2_s_axi_awprot,
    ext_axis_avg_buffer_2_s_axi_awready,
    ext_axis_avg_buffer_2_s_axi_awvalid,
    ext_axis_avg_buffer_2_s_axi_bready,
    ext_axis_avg_buffer_2_s_axi_bresp,
    ext_axis_avg_buffer_2_s_axi_bvalid,
    ext_axis_avg_buffer_2_s_axi_rdata,
    ext_axis_avg_buffer_2_s_axi_rready,
    ext_axis_avg_buffer_2_s_axi_rresp,
    ext_axis_avg_buffer_2_s_axi_rvalid,
    ext_axis_avg_buffer_2_s_axi_wdata,
    ext_axis_avg_buffer_2_s_axi_wready,
    ext_axis_avg_buffer_2_s_axi_wstrb,
    ext_axis_avg_buffer_2_s_axi_wvalid,
    ext_axis_avg_buffer_3_s_axi_araddr,
    ext_axis_avg_buffer_3_s_axi_arprot,
    ext_axis_avg_buffer_3_s_axi_arready,
    ext_axis_avg_buffer_3_s_axi_arvalid,
    ext_axis_avg_buffer_3_s_axi_awaddr,
    ext_axis_avg_buffer_3_s_axi_awprot,
    ext_axis_avg_buffer_3_s_axi_awready,
    ext_axis_avg_buffer_3_s_axi_awvalid,
    ext_axis_avg_buffer_3_s_axi_bready,
    ext_axis_avg_buffer_3_s_axi_bresp,
    ext_axis_avg_buffer_3_s_axi_bvalid,
    ext_axis_avg_buffer_3_s_axi_rdata,
    ext_axis_avg_buffer_3_s_axi_rready,
    ext_axis_avg_buffer_3_s_axi_rresp,
    ext_axis_avg_buffer_3_s_axi_rvalid,
    ext_axis_avg_buffer_3_s_axi_wdata,
    ext_axis_avg_buffer_3_s_axi_wready,
    ext_axis_avg_buffer_3_s_axi_wstrb,
    ext_axis_avg_buffer_3_s_axi_wvalid,
    ext_axis_awg_tuning_v1_10_s_axi_araddr,
    ext_axis_awg_tuning_v1_10_s_axi_arprot,
    ext_axis_awg_tuning_v1_10_s_axi_arready,
    ext_axis_awg_tuning_v1_10_s_axi_arvalid,
    ext_axis_awg_tuning_v1_10_s_axi_awaddr,
    ext_axis_awg_tuning_v1_10_s_axi_awprot,
    ext_axis_awg_tuning_v1_10_s_axi_awready,
    ext_axis_awg_tuning_v1_10_s_axi_awvalid,
    ext_axis_awg_tuning_v1_10_s_axi_bready,
    ext_axis_awg_tuning_v1_10_s_axi_bresp,
    ext_axis_awg_tuning_v1_10_s_axi_bvalid,
    ext_axis_awg_tuning_v1_10_s_axi_rdata,
    ext_axis_awg_tuning_v1_10_s_axi_rready,
    ext_axis_awg_tuning_v1_10_s_axi_rresp,
    ext_axis_awg_tuning_v1_10_s_axi_rvalid,
    ext_axis_awg_tuning_v1_10_s_axi_wdata,
    ext_axis_awg_tuning_v1_10_s_axi_wready,
    ext_axis_awg_tuning_v1_10_s_axi_wstrb,
    ext_axis_awg_tuning_v1_10_s_axi_wvalid,
    ext_axis_awg_tuning_v1_11_s_axi_araddr,
    ext_axis_awg_tuning_v1_11_s_axi_arprot,
    ext_axis_awg_tuning_v1_11_s_axi_arready,
    ext_axis_awg_tuning_v1_11_s_axi_arvalid,
    ext_axis_awg_tuning_v1_11_s_axi_awaddr,
    ext_axis_awg_tuning_v1_11_s_axi_awprot,
    ext_axis_awg_tuning_v1_11_s_axi_awready,
    ext_axis_awg_tuning_v1_11_s_axi_awvalid,
    ext_axis_awg_tuning_v1_11_s_axi_bready,
    ext_axis_awg_tuning_v1_11_s_axi_bresp,
    ext_axis_awg_tuning_v1_11_s_axi_bvalid,
    ext_axis_awg_tuning_v1_11_s_axi_rdata,
    ext_axis_awg_tuning_v1_11_s_axi_rready,
    ext_axis_awg_tuning_v1_11_s_axi_rresp,
    ext_axis_awg_tuning_v1_11_s_axi_rvalid,
    ext_axis_awg_tuning_v1_11_s_axi_wdata,
    ext_axis_awg_tuning_v1_11_s_axi_wready,
    ext_axis_awg_tuning_v1_11_s_axi_wstrb,
    ext_axis_awg_tuning_v1_11_s_axi_wvalid,
    ext_axis_awg_tuning_v1_4_s_axi_araddr,
    ext_axis_awg_tuning_v1_4_s_axi_arprot,
    ext_axis_awg_tuning_v1_4_s_axi_arready,
    ext_axis_awg_tuning_v1_4_s_axi_arvalid,
    ext_axis_awg_tuning_v1_4_s_axi_awaddr,
    ext_axis_awg_tuning_v1_4_s_axi_awprot,
    ext_axis_awg_tuning_v1_4_s_axi_awready,
    ext_axis_awg_tuning_v1_4_s_axi_awvalid,
    ext_axis_awg_tuning_v1_4_s_axi_bready,
    ext_axis_awg_tuning_v1_4_s_axi_bresp,
    ext_axis_awg_tuning_v1_4_s_axi_bvalid,
    ext_axis_awg_tuning_v1_4_s_axi_rdata,
    ext_axis_awg_tuning_v1_4_s_axi_rready,
    ext_axis_awg_tuning_v1_4_s_axi_rresp,
    ext_axis_awg_tuning_v1_4_s_axi_rvalid,
    ext_axis_awg_tuning_v1_4_s_axi_wdata,
    ext_axis_awg_tuning_v1_4_s_axi_wready,
    ext_axis_awg_tuning_v1_4_s_axi_wstrb,
    ext_axis_awg_tuning_v1_4_s_axi_wvalid,
    ext_axis_awg_tuning_v1_5_s_axi_araddr,
    ext_axis_awg_tuning_v1_5_s_axi_arprot,
    ext_axis_awg_tuning_v1_5_s_axi_arready,
    ext_axis_awg_tuning_v1_5_s_axi_arvalid,
    ext_axis_awg_tuning_v1_5_s_axi_awaddr,
    ext_axis_awg_tuning_v1_5_s_axi_awprot,
    ext_axis_awg_tuning_v1_5_s_axi_awready,
    ext_axis_awg_tuning_v1_5_s_axi_awvalid,
    ext_axis_awg_tuning_v1_5_s_axi_bready,
    ext_axis_awg_tuning_v1_5_s_axi_bresp,
    ext_axis_awg_tuning_v1_5_s_axi_bvalid,
    ext_axis_awg_tuning_v1_5_s_axi_rdata,
    ext_axis_awg_tuning_v1_5_s_axi_rready,
    ext_axis_awg_tuning_v1_5_s_axi_rresp,
    ext_axis_awg_tuning_v1_5_s_axi_rvalid,
    ext_axis_awg_tuning_v1_5_s_axi_wdata,
    ext_axis_awg_tuning_v1_5_s_axi_wready,
    ext_axis_awg_tuning_v1_5_s_axi_wstrb,
    ext_axis_awg_tuning_v1_5_s_axi_wvalid,
    ext_axis_awg_tuning_v1_6_s_axi_araddr,
    ext_axis_awg_tuning_v1_6_s_axi_arprot,
    ext_axis_awg_tuning_v1_6_s_axi_arready,
    ext_axis_awg_tuning_v1_6_s_axi_arvalid,
    ext_axis_awg_tuning_v1_6_s_axi_awaddr,
    ext_axis_awg_tuning_v1_6_s_axi_awprot,
    ext_axis_awg_tuning_v1_6_s_axi_awready,
    ext_axis_awg_tuning_v1_6_s_axi_awvalid,
    ext_axis_awg_tuning_v1_6_s_axi_bready,
    ext_axis_awg_tuning_v1_6_s_axi_bresp,
    ext_axis_awg_tuning_v1_6_s_axi_bvalid,
    ext_axis_awg_tuning_v1_6_s_axi_rdata,
    ext_axis_awg_tuning_v1_6_s_axi_rready,
    ext_axis_awg_tuning_v1_6_s_axi_rresp,
    ext_axis_awg_tuning_v1_6_s_axi_rvalid,
    ext_axis_awg_tuning_v1_6_s_axi_wdata,
    ext_axis_awg_tuning_v1_6_s_axi_wready,
    ext_axis_awg_tuning_v1_6_s_axi_wstrb,
    ext_axis_awg_tuning_v1_6_s_axi_wvalid,
    ext_axis_awg_tuning_v1_8_s_axi_araddr,
    ext_axis_awg_tuning_v1_8_s_axi_arprot,
    ext_axis_awg_tuning_v1_8_s_axi_arready,
    ext_axis_awg_tuning_v1_8_s_axi_arvalid,
    ext_axis_awg_tuning_v1_8_s_axi_awaddr,
    ext_axis_awg_tuning_v1_8_s_axi_awprot,
    ext_axis_awg_tuning_v1_8_s_axi_awready,
    ext_axis_awg_tuning_v1_8_s_axi_awvalid,
    ext_axis_awg_tuning_v1_8_s_axi_bready,
    ext_axis_awg_tuning_v1_8_s_axi_bresp,
    ext_axis_awg_tuning_v1_8_s_axi_bvalid,
    ext_axis_awg_tuning_v1_8_s_axi_rdata,
    ext_axis_awg_tuning_v1_8_s_axi_rready,
    ext_axis_awg_tuning_v1_8_s_axi_rresp,
    ext_axis_awg_tuning_v1_8_s_axi_rvalid,
    ext_axis_awg_tuning_v1_8_s_axi_wdata,
    ext_axis_awg_tuning_v1_8_s_axi_wready,
    ext_axis_awg_tuning_v1_8_s_axi_wstrb,
    ext_axis_awg_tuning_v1_8_s_axi_wvalid,
    ext_axis_awg_tuning_v1_9_s_axi_araddr,
    ext_axis_awg_tuning_v1_9_s_axi_arprot,
    ext_axis_awg_tuning_v1_9_s_axi_arready,
    ext_axis_awg_tuning_v1_9_s_axi_arvalid,
    ext_axis_awg_tuning_v1_9_s_axi_awaddr,
    ext_axis_awg_tuning_v1_9_s_axi_awprot,
    ext_axis_awg_tuning_v1_9_s_axi_awready,
    ext_axis_awg_tuning_v1_9_s_axi_awvalid,
    ext_axis_awg_tuning_v1_9_s_axi_bready,
    ext_axis_awg_tuning_v1_9_s_axi_bresp,
    ext_axis_awg_tuning_v1_9_s_axi_bvalid,
    ext_axis_awg_tuning_v1_9_s_axi_rdata,
    ext_axis_awg_tuning_v1_9_s_axi_rready,
    ext_axis_awg_tuning_v1_9_s_axi_rresp,
    ext_axis_awg_tuning_v1_9_s_axi_rvalid,
    ext_axis_awg_tuning_v1_9_s_axi_wdata,
    ext_axis_awg_tuning_v1_9_s_axi_wready,
    ext_axis_awg_tuning_v1_9_s_axi_wstrb,
    ext_axis_awg_tuning_v1_9_s_axi_wvalid,
    ext_axis_dyn_readout_v1_0_s1_axis_tdata,
    ext_axis_dyn_readout_v1_0_s1_axis_tready,
    ext_axis_dyn_readout_v1_0_s1_axis_tvalid,
    ext_axis_dyn_readout_v1_1_s1_axis_tdata,
    ext_axis_dyn_readout_v1_1_s1_axis_tready,
    ext_axis_dyn_readout_v1_1_s1_axis_tvalid,
    ext_axis_dyn_readout_v1_2_s1_axis_tdata,
    ext_axis_dyn_readout_v1_2_s1_axis_tready,
    ext_axis_dyn_readout_v1_2_s1_axis_tvalid,
    ext_axis_dyn_readout_v1_3_s1_axis_tdata,
    ext_axis_dyn_readout_v1_3_s1_axis_tready,
    ext_axis_dyn_readout_v1_3_s1_axis_tvalid,
    ext_axis_register_slice_0_m_axis_tdata,
    ext_axis_register_slice_0_m_axis_tready,
    ext_axis_register_slice_0_m_axis_tvalid,
    ext_axis_register_slice_10_m_axis_tdata,
    ext_axis_register_slice_10_m_axis_tready,
    ext_axis_register_slice_10_m_axis_tvalid,
    ext_axis_register_slice_11_m_axis_tdata,
    ext_axis_register_slice_11_m_axis_tready,
    ext_axis_register_slice_11_m_axis_tvalid,
    ext_axis_register_slice_12_m_axis_tdata,
    ext_axis_register_slice_12_m_axis_tready,
    ext_axis_register_slice_12_m_axis_tvalid,
    ext_axis_register_slice_13_m_axis_tdata,
    ext_axis_register_slice_13_m_axis_tready,
    ext_axis_register_slice_13_m_axis_tvalid,
    ext_axis_register_slice_14_m_axis_tdata,
    ext_axis_register_slice_14_m_axis_tready,
    ext_axis_register_slice_14_m_axis_tvalid,
    ext_axis_register_slice_15_m_axis_tdata,
    ext_axis_register_slice_15_m_axis_tready,
    ext_axis_register_slice_15_m_axis_tvalid,
    ext_axis_register_slice_16_m_axis_tdata,
    ext_axis_register_slice_16_m_axis_tready,
    ext_axis_register_slice_16_m_axis_tvalid,
    ext_axis_register_slice_1_m_axis_tdata,
    ext_axis_register_slice_1_m_axis_tready,
    ext_axis_register_slice_1_m_axis_tvalid,
    ext_axis_register_slice_2_m_axis_tdata,
    ext_axis_register_slice_2_m_axis_tready,
    ext_axis_register_slice_2_m_axis_tvalid,
    ext_axis_register_slice_3_m_axis_tdata,
    ext_axis_register_slice_3_m_axis_tready,
    ext_axis_register_slice_3_m_axis_tvalid,
    ext_axis_register_slice_8_m_axis_tdata,
    ext_axis_register_slice_8_m_axis_tready,
    ext_axis_register_slice_8_m_axis_tvalid,
    ext_axis_signal_gen_v6_0_s_axi_araddr,
    ext_axis_signal_gen_v6_0_s_axi_arprot,
    ext_axis_signal_gen_v6_0_s_axi_arready,
    ext_axis_signal_gen_v6_0_s_axi_arvalid,
    ext_axis_signal_gen_v6_0_s_axi_awaddr,
    ext_axis_signal_gen_v6_0_s_axi_awprot,
    ext_axis_signal_gen_v6_0_s_axi_awready,
    ext_axis_signal_gen_v6_0_s_axi_awvalid,
    ext_axis_signal_gen_v6_0_s_axi_bready,
    ext_axis_signal_gen_v6_0_s_axi_bresp,
    ext_axis_signal_gen_v6_0_s_axi_bvalid,
    ext_axis_signal_gen_v6_0_s_axi_rdata,
    ext_axis_signal_gen_v6_0_s_axi_rready,
    ext_axis_signal_gen_v6_0_s_axi_rresp,
    ext_axis_signal_gen_v6_0_s_axi_rvalid,
    ext_axis_signal_gen_v6_0_s_axi_wdata,
    ext_axis_signal_gen_v6_0_s_axi_wready,
    ext_axis_signal_gen_v6_0_s_axi_wstrb,
    ext_axis_signal_gen_v6_0_s_axi_wvalid,
    ext_axis_signal_gen_v6_1_s_axi_araddr,
    ext_axis_signal_gen_v6_1_s_axi_arprot,
    ext_axis_signal_gen_v6_1_s_axi_arready,
    ext_axis_signal_gen_v6_1_s_axi_arvalid,
    ext_axis_signal_gen_v6_1_s_axi_awaddr,
    ext_axis_signal_gen_v6_1_s_axi_awprot,
    ext_axis_signal_gen_v6_1_s_axi_awready,
    ext_axis_signal_gen_v6_1_s_axi_awvalid,
    ext_axis_signal_gen_v6_1_s_axi_bready,
    ext_axis_signal_gen_v6_1_s_axi_bresp,
    ext_axis_signal_gen_v6_1_s_axi_bvalid,
    ext_axis_signal_gen_v6_1_s_axi_rdata,
    ext_axis_signal_gen_v6_1_s_axi_rready,
    ext_axis_signal_gen_v6_1_s_axi_rresp,
    ext_axis_signal_gen_v6_1_s_axi_rvalid,
    ext_axis_signal_gen_v6_1_s_axi_wdata,
    ext_axis_signal_gen_v6_1_s_axi_wready,
    ext_axis_signal_gen_v6_1_s_axi_wstrb,
    ext_axis_signal_gen_v6_1_s_axi_wvalid,
    ext_axis_signal_gen_v6_2_s_axi_araddr,
    ext_axis_signal_gen_v6_2_s_axi_arprot,
    ext_axis_signal_gen_v6_2_s_axi_arready,
    ext_axis_signal_gen_v6_2_s_axi_arvalid,
    ext_axis_signal_gen_v6_2_s_axi_awaddr,
    ext_axis_signal_gen_v6_2_s_axi_awprot,
    ext_axis_signal_gen_v6_2_s_axi_awready,
    ext_axis_signal_gen_v6_2_s_axi_awvalid,
    ext_axis_signal_gen_v6_2_s_axi_bready,
    ext_axis_signal_gen_v6_2_s_axi_bresp,
    ext_axis_signal_gen_v6_2_s_axi_bvalid,
    ext_axis_signal_gen_v6_2_s_axi_rdata,
    ext_axis_signal_gen_v6_2_s_axi_rready,
    ext_axis_signal_gen_v6_2_s_axi_rresp,
    ext_axis_signal_gen_v6_2_s_axi_rvalid,
    ext_axis_signal_gen_v6_2_s_axi_wdata,
    ext_axis_signal_gen_v6_2_s_axi_wready,
    ext_axis_signal_gen_v6_2_s_axi_wstrb,
    ext_axis_signal_gen_v6_2_s_axi_wvalid,
    ext_axis_signal_gen_v6_3_s_axi_araddr,
    ext_axis_signal_gen_v6_3_s_axi_arprot,
    ext_axis_signal_gen_v6_3_s_axi_arready,
    ext_axis_signal_gen_v6_3_s_axi_arvalid,
    ext_axis_signal_gen_v6_3_s_axi_awaddr,
    ext_axis_signal_gen_v6_3_s_axi_awprot,
    ext_axis_signal_gen_v6_3_s_axi_awready,
    ext_axis_signal_gen_v6_3_s_axi_awvalid,
    ext_axis_signal_gen_v6_3_s_axi_bready,
    ext_axis_signal_gen_v6_3_s_axi_bresp,
    ext_axis_signal_gen_v6_3_s_axi_bvalid,
    ext_axis_signal_gen_v6_3_s_axi_rdata,
    ext_axis_signal_gen_v6_3_s_axi_rready,
    ext_axis_signal_gen_v6_3_s_axi_rresp,
    ext_axis_signal_gen_v6_3_s_axi_rvalid,
    ext_axis_signal_gen_v6_3_s_axi_wdata,
    ext_axis_signal_gen_v6_3_s_axi_wready,
    ext_axis_signal_gen_v6_3_s_axi_wstrb,
    ext_axis_signal_gen_v6_3_s_axi_wvalid,
    ext_axis_square_pulse_v1_0_s_axi_araddr,
    ext_axis_square_pulse_v1_0_s_axi_arprot,
    ext_axis_square_pulse_v1_0_s_axi_arready,
    ext_axis_square_pulse_v1_0_s_axi_arvalid,
    ext_axis_square_pulse_v1_0_s_axi_awaddr,
    ext_axis_square_pulse_v1_0_s_axi_awprot,
    ext_axis_square_pulse_v1_0_s_axi_awready,
    ext_axis_square_pulse_v1_0_s_axi_awvalid,
    ext_axis_square_pulse_v1_0_s_axi_bready,
    ext_axis_square_pulse_v1_0_s_axi_bresp,
    ext_axis_square_pulse_v1_0_s_axi_bvalid,
    ext_axis_square_pulse_v1_0_s_axi_rdata,
    ext_axis_square_pulse_v1_0_s_axi_rready,
    ext_axis_square_pulse_v1_0_s_axi_rresp,
    ext_axis_square_pulse_v1_0_s_axi_rvalid,
    ext_axis_square_pulse_v1_0_s_axi_wdata,
    ext_axis_square_pulse_v1_0_s_axi_wready,
    ext_axis_square_pulse_v1_0_s_axi_wstrb,
    ext_axis_square_pulse_v1_0_s_axi_wvalid,
    ext_axis_switch_avg_M00_AXIS_tdata,
    ext_axis_switch_avg_M00_AXIS_tlast,
    ext_axis_switch_avg_M00_AXIS_tready,
    ext_axis_switch_avg_M00_AXIS_tvalid,
    ext_axis_switch_avg_S_AXI_CTRL_araddr,
    ext_axis_switch_avg_S_AXI_CTRL_arready,
    ext_axis_switch_avg_S_AXI_CTRL_arvalid,
    ext_axis_switch_avg_S_AXI_CTRL_awaddr,
    ext_axis_switch_avg_S_AXI_CTRL_awready,
    ext_axis_switch_avg_S_AXI_CTRL_awvalid,
    ext_axis_switch_avg_S_AXI_CTRL_bready,
    ext_axis_switch_avg_S_AXI_CTRL_bresp,
    ext_axis_switch_avg_S_AXI_CTRL_bvalid,
    ext_axis_switch_avg_S_AXI_CTRL_rdata,
    ext_axis_switch_avg_S_AXI_CTRL_rready,
    ext_axis_switch_avg_S_AXI_CTRL_rresp,
    ext_axis_switch_avg_S_AXI_CTRL_rvalid,
    ext_axis_switch_avg_S_AXI_CTRL_wdata,
    ext_axis_switch_avg_S_AXI_CTRL_wready,
    ext_axis_switch_avg_S_AXI_CTRL_wvalid,
    ext_axis_switch_buf_M00_AXIS_tdata,
    ext_axis_switch_buf_M00_AXIS_tlast,
    ext_axis_switch_buf_M00_AXIS_tready,
    ext_axis_switch_buf_M00_AXIS_tvalid,
    ext_axis_switch_buf_S_AXI_CTRL_araddr,
    ext_axis_switch_buf_S_AXI_CTRL_arready,
    ext_axis_switch_buf_S_AXI_CTRL_arvalid,
    ext_axis_switch_buf_S_AXI_CTRL_awaddr,
    ext_axis_switch_buf_S_AXI_CTRL_awready,
    ext_axis_switch_buf_S_AXI_CTRL_awvalid,
    ext_axis_switch_buf_S_AXI_CTRL_bready,
    ext_axis_switch_buf_S_AXI_CTRL_bresp,
    ext_axis_switch_buf_S_AXI_CTRL_bvalid,
    ext_axis_switch_buf_S_AXI_CTRL_rdata,
    ext_axis_switch_buf_S_AXI_CTRL_rready,
    ext_axis_switch_buf_S_AXI_CTRL_rresp,
    ext_axis_switch_buf_S_AXI_CTRL_rvalid,
    ext_axis_switch_buf_S_AXI_CTRL_wdata,
    ext_axis_switch_buf_S_AXI_CTRL_wready,
    ext_axis_switch_buf_S_AXI_CTRL_wvalid,
    ext_axis_switch_ddr_S_AXI_CTRL_araddr,
    ext_axis_switch_ddr_S_AXI_CTRL_arready,
    ext_axis_switch_ddr_S_AXI_CTRL_arvalid,
    ext_axis_switch_ddr_S_AXI_CTRL_awaddr,
    ext_axis_switch_ddr_S_AXI_CTRL_awready,
    ext_axis_switch_ddr_S_AXI_CTRL_awvalid,
    ext_axis_switch_ddr_S_AXI_CTRL_bready,
    ext_axis_switch_ddr_S_AXI_CTRL_bresp,
    ext_axis_switch_ddr_S_AXI_CTRL_bvalid,
    ext_axis_switch_ddr_S_AXI_CTRL_rdata,
    ext_axis_switch_ddr_S_AXI_CTRL_rready,
    ext_axis_switch_ddr_S_AXI_CTRL_rresp,
    ext_axis_switch_ddr_S_AXI_CTRL_rvalid,
    ext_axis_switch_ddr_S_AXI_CTRL_wdata,
    ext_axis_switch_ddr_S_AXI_CTRL_wready,
    ext_axis_switch_ddr_S_AXI_CTRL_wvalid,
    ext_axis_switch_gen_M04_AXIS_tdata,
    ext_axis_switch_gen_M04_AXIS_tkeep,
    ext_axis_switch_gen_M04_AXIS_tlast,
    ext_axis_switch_gen_M04_AXIS_tready,
    ext_axis_switch_gen_M04_AXIS_tvalid,
    ext_axis_switch_gen_M05_AXIS_tdata,
    ext_axis_switch_gen_M05_AXIS_tkeep,
    ext_axis_switch_gen_M05_AXIS_tlast,
    ext_axis_switch_gen_M05_AXIS_tready,
    ext_axis_switch_gen_M05_AXIS_tvalid,
    ext_axis_switch_gen_M06_AXIS_tdata,
    ext_axis_switch_gen_M06_AXIS_tkeep,
    ext_axis_switch_gen_M06_AXIS_tlast,
    ext_axis_switch_gen_M06_AXIS_tready,
    ext_axis_switch_gen_M06_AXIS_tvalid,
    ext_axis_switch_gen_M07_AXIS_tdata,
    ext_axis_switch_gen_M07_AXIS_tkeep,
    ext_axis_switch_gen_M07_AXIS_tlast,
    ext_axis_switch_gen_M07_AXIS_tready,
    ext_axis_switch_gen_M07_AXIS_tvalid,
    ext_axis_switch_gen_M08_AXIS_tdata,
    ext_axis_switch_gen_M08_AXIS_tkeep,
    ext_axis_switch_gen_M08_AXIS_tlast,
    ext_axis_switch_gen_M08_AXIS_tready,
    ext_axis_switch_gen_M08_AXIS_tvalid,
    ext_axis_switch_gen_M09_AXIS_tdata,
    ext_axis_switch_gen_M09_AXIS_tkeep,
    ext_axis_switch_gen_M09_AXIS_tlast,
    ext_axis_switch_gen_M09_AXIS_tready,
    ext_axis_switch_gen_M09_AXIS_tvalid,
    ext_axis_switch_gen_M10_AXIS_tdata,
    ext_axis_switch_gen_M10_AXIS_tkeep,
    ext_axis_switch_gen_M10_AXIS_tlast,
    ext_axis_switch_gen_M10_AXIS_tready,
    ext_axis_switch_gen_M10_AXIS_tvalid,
    ext_axis_switch_gen_M11_AXIS_tdata,
    ext_axis_switch_gen_M11_AXIS_tkeep,
    ext_axis_switch_gen_M11_AXIS_tlast,
    ext_axis_switch_gen_M11_AXIS_tready,
    ext_axis_switch_gen_M11_AXIS_tvalid,
    ext_axis_switch_gen_S00_AXIS_tdata,
    ext_axis_switch_gen_S00_AXIS_tkeep,
    ext_axis_switch_gen_S00_AXIS_tlast,
    ext_axis_switch_gen_S00_AXIS_tready,
    ext_axis_switch_gen_S00_AXIS_tvalid,
    ext_axis_switch_gen_S_AXI_CTRL_araddr,
    ext_axis_switch_gen_S_AXI_CTRL_arready,
    ext_axis_switch_gen_S_AXI_CTRL_arvalid,
    ext_axis_switch_gen_S_AXI_CTRL_awaddr,
    ext_axis_switch_gen_S_AXI_CTRL_awready,
    ext_axis_switch_gen_S_AXI_CTRL_awvalid,
    ext_axis_switch_gen_S_AXI_CTRL_bready,
    ext_axis_switch_gen_S_AXI_CTRL_bresp,
    ext_axis_switch_gen_S_AXI_CTRL_bvalid,
    ext_axis_switch_gen_S_AXI_CTRL_rdata,
    ext_axis_switch_gen_S_AXI_CTRL_rready,
    ext_axis_switch_gen_S_AXI_CTRL_rresp,
    ext_axis_switch_gen_S_AXI_CTRL_rvalid,
    ext_axis_switch_gen_S_AXI_CTRL_wdata,
    ext_axis_switch_gen_S_AXI_CTRL_wready,
    ext_axis_switch_gen_S_AXI_CTRL_wvalid,
    ext_axis_switch_mr_S_AXI_CTRL_araddr,
    ext_axis_switch_mr_S_AXI_CTRL_arready,
    ext_axis_switch_mr_S_AXI_CTRL_arvalid,
    ext_axis_switch_mr_S_AXI_CTRL_awaddr,
    ext_axis_switch_mr_S_AXI_CTRL_awready,
    ext_axis_switch_mr_S_AXI_CTRL_awvalid,
    ext_axis_switch_mr_S_AXI_CTRL_bready,
    ext_axis_switch_mr_S_AXI_CTRL_bresp,
    ext_axis_switch_mr_S_AXI_CTRL_bvalid,
    ext_axis_switch_mr_S_AXI_CTRL_rdata,
    ext_axis_switch_mr_S_AXI_CTRL_rready,
    ext_axis_switch_mr_S_AXI_CTRL_rresp,
    ext_axis_switch_mr_S_AXI_CTRL_rvalid,
    ext_axis_switch_mr_S_AXI_CTRL_wdata,
    ext_axis_switch_mr_S_AXI_CTRL_wready,
    ext_axis_switch_mr_S_AXI_CTRL_wvalid,
    ext_axis_tproc64x32_x8_0_m0_axis_tdata,
    ext_axis_tproc64x32_x8_0_m0_axis_tlast,
    ext_axis_tproc64x32_x8_0_m0_axis_tready,
    ext_axis_tproc64x32_x8_0_m0_axis_tvalid,
    ext_axis_tproc64x32_x8_0_pmem_addr,
    ext_axis_tproc64x32_x8_0_pmem_do,
    ext_axis_tproc64x32_x8_0_s0_axis_tdata,
    ext_axis_tproc64x32_x8_0_s0_axis_tlast,
    ext_axis_tproc64x32_x8_0_s0_axis_tready,
    ext_axis_tproc64x32_x8_0_s0_axis_tvalid,
    ext_axis_tproc64x32_x8_0_s_axi_araddr,
    ext_axis_tproc64x32_x8_0_s_axi_arprot,
    ext_axis_tproc64x32_x8_0_s_axi_arready,
    ext_axis_tproc64x32_x8_0_s_axi_arvalid,
    ext_axis_tproc64x32_x8_0_s_axi_awaddr,
    ext_axis_tproc64x32_x8_0_s_axi_awprot,
    ext_axis_tproc64x32_x8_0_s_axi_awready,
    ext_axis_tproc64x32_x8_0_s_axi_awvalid,
    ext_axis_tproc64x32_x8_0_s_axi_bready,
    ext_axis_tproc64x32_x8_0_s_axi_bresp,
    ext_axis_tproc64x32_x8_0_s_axi_bvalid,
    ext_axis_tproc64x32_x8_0_s_axi_rdata,
    ext_axis_tproc64x32_x8_0_s_axi_rready,
    ext_axis_tproc64x32_x8_0_s_axi_rresp,
    ext_axis_tproc64x32_x8_0_s_axi_rvalid,
    ext_axis_tproc64x32_x8_0_s_axi_wdata,
    ext_axis_tproc64x32_x8_0_s_axi_wready,
    ext_axis_tproc64x32_x8_0_s_axi_wstrb,
    ext_axis_tproc64x32_x8_0_s_axi_wvalid,
    ext_axis_tproc64x32_x8_0_start,
    ext_c_shift_ram_0_D,
    ext_c_shift_ram_0_Q,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awaddr,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awburst,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awcache,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awid,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlen,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlock,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awprot,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awqos,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awready,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awregion,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awsize,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awvalid,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bid,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bready,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bresp,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bvalid,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wdata,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wlast,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wready,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wstrb,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wvalid,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_araddr,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arprot,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arready,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arvalid,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awaddr,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awprot,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awready,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awvalid,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bready,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bresp,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bvalid,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rdata,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rready,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rresp,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rvalid,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wdata,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wready,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wstrb,
    ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wvalid,
    ext_ddr4_axis_fir_decim_300to1_v2_0_capture_trigger,
    ext_mr_buffer_et_0_m00_axis_tdata,
    ext_mr_buffer_et_0_m00_axis_tlast,
    ext_mr_buffer_et_0_m00_axis_tready,
    ext_mr_buffer_et_0_m00_axis_tstrb,
    ext_mr_buffer_et_0_m00_axis_tvalid,
    ext_mr_buffer_et_0_s00_axi_araddr,
    ext_mr_buffer_et_0_s00_axi_arprot,
    ext_mr_buffer_et_0_s00_axi_arready,
    ext_mr_buffer_et_0_s00_axi_arvalid,
    ext_mr_buffer_et_0_s00_axi_awaddr,
    ext_mr_buffer_et_0_s00_axi_awprot,
    ext_mr_buffer_et_0_s00_axi_awready,
    ext_mr_buffer_et_0_s00_axi_awvalid,
    ext_mr_buffer_et_0_s00_axi_bready,
    ext_mr_buffer_et_0_s00_axi_bresp,
    ext_mr_buffer_et_0_s00_axi_bvalid,
    ext_mr_buffer_et_0_s00_axi_rdata,
    ext_mr_buffer_et_0_s00_axi_rready,
    ext_mr_buffer_et_0_s00_axi_rresp,
    ext_mr_buffer_et_0_s00_axi_rvalid,
    ext_mr_buffer_et_0_s00_axi_wdata,
    ext_mr_buffer_et_0_s00_axi_wready,
    ext_mr_buffer_et_0_s00_axi_wstrb,
    ext_mr_buffer_et_0_s00_axi_wvalid,
    ext_qick_vec2bit_0_dout0,
    ext_qick_vec2bit_0_dout1,
    ext_qick_vec2bit_0_dout2,
    ext_qick_vec2bit_0_dout3,
    ext_qick_vec2bit_0_dout4,
    ext_qick_vec2bit_0_dout5,
    ext_qick_vec2bit_0_dout6,
    ext_xlconstant_0_dout,
    ext_xlconstant_1_dout,
    ext_xlconstant_2_dout,
    ext_xlconstant_3_dout,
    ext_xlconstant_4_dout,
    resetn);
  input clk_300000000;
  input clk_333250000;
  input clk_99999985;
  input [5:0]ext_axis_avg_buffer_0_s_axi_araddr;
  input [2:0]ext_axis_avg_buffer_0_s_axi_arprot;
  output ext_axis_avg_buffer_0_s_axi_arready;
  input ext_axis_avg_buffer_0_s_axi_arvalid;
  input [5:0]ext_axis_avg_buffer_0_s_axi_awaddr;
  input [2:0]ext_axis_avg_buffer_0_s_axi_awprot;
  output ext_axis_avg_buffer_0_s_axi_awready;
  input ext_axis_avg_buffer_0_s_axi_awvalid;
  input ext_axis_avg_buffer_0_s_axi_bready;
  output [1:0]ext_axis_avg_buffer_0_s_axi_bresp;
  output ext_axis_avg_buffer_0_s_axi_bvalid;
  output [31:0]ext_axis_avg_buffer_0_s_axi_rdata;
  input ext_axis_avg_buffer_0_s_axi_rready;
  output [1:0]ext_axis_avg_buffer_0_s_axi_rresp;
  output ext_axis_avg_buffer_0_s_axi_rvalid;
  input [31:0]ext_axis_avg_buffer_0_s_axi_wdata;
  output ext_axis_avg_buffer_0_s_axi_wready;
  input [3:0]ext_axis_avg_buffer_0_s_axi_wstrb;
  input ext_axis_avg_buffer_0_s_axi_wvalid;
  input [5:0]ext_axis_avg_buffer_1_s_axi_araddr;
  input [2:0]ext_axis_avg_buffer_1_s_axi_arprot;
  output ext_axis_avg_buffer_1_s_axi_arready;
  input ext_axis_avg_buffer_1_s_axi_arvalid;
  input [5:0]ext_axis_avg_buffer_1_s_axi_awaddr;
  input [2:0]ext_axis_avg_buffer_1_s_axi_awprot;
  output ext_axis_avg_buffer_1_s_axi_awready;
  input ext_axis_avg_buffer_1_s_axi_awvalid;
  input ext_axis_avg_buffer_1_s_axi_bready;
  output [1:0]ext_axis_avg_buffer_1_s_axi_bresp;
  output ext_axis_avg_buffer_1_s_axi_bvalid;
  output [31:0]ext_axis_avg_buffer_1_s_axi_rdata;
  input ext_axis_avg_buffer_1_s_axi_rready;
  output [1:0]ext_axis_avg_buffer_1_s_axi_rresp;
  output ext_axis_avg_buffer_1_s_axi_rvalid;
  input [31:0]ext_axis_avg_buffer_1_s_axi_wdata;
  output ext_axis_avg_buffer_1_s_axi_wready;
  input [3:0]ext_axis_avg_buffer_1_s_axi_wstrb;
  input ext_axis_avg_buffer_1_s_axi_wvalid;
  input [5:0]ext_axis_avg_buffer_2_s_axi_araddr;
  input [2:0]ext_axis_avg_buffer_2_s_axi_arprot;
  output ext_axis_avg_buffer_2_s_axi_arready;
  input ext_axis_avg_buffer_2_s_axi_arvalid;
  input [5:0]ext_axis_avg_buffer_2_s_axi_awaddr;
  input [2:0]ext_axis_avg_buffer_2_s_axi_awprot;
  output ext_axis_avg_buffer_2_s_axi_awready;
  input ext_axis_avg_buffer_2_s_axi_awvalid;
  input ext_axis_avg_buffer_2_s_axi_bready;
  output [1:0]ext_axis_avg_buffer_2_s_axi_bresp;
  output ext_axis_avg_buffer_2_s_axi_bvalid;
  output [31:0]ext_axis_avg_buffer_2_s_axi_rdata;
  input ext_axis_avg_buffer_2_s_axi_rready;
  output [1:0]ext_axis_avg_buffer_2_s_axi_rresp;
  output ext_axis_avg_buffer_2_s_axi_rvalid;
  input [31:0]ext_axis_avg_buffer_2_s_axi_wdata;
  output ext_axis_avg_buffer_2_s_axi_wready;
  input [3:0]ext_axis_avg_buffer_2_s_axi_wstrb;
  input ext_axis_avg_buffer_2_s_axi_wvalid;
  input [5:0]ext_axis_avg_buffer_3_s_axi_araddr;
  input [2:0]ext_axis_avg_buffer_3_s_axi_arprot;
  output ext_axis_avg_buffer_3_s_axi_arready;
  input ext_axis_avg_buffer_3_s_axi_arvalid;
  input [5:0]ext_axis_avg_buffer_3_s_axi_awaddr;
  input [2:0]ext_axis_avg_buffer_3_s_axi_awprot;
  output ext_axis_avg_buffer_3_s_axi_awready;
  input ext_axis_avg_buffer_3_s_axi_awvalid;
  input ext_axis_avg_buffer_3_s_axi_bready;
  output [1:0]ext_axis_avg_buffer_3_s_axi_bresp;
  output ext_axis_avg_buffer_3_s_axi_bvalid;
  output [31:0]ext_axis_avg_buffer_3_s_axi_rdata;
  input ext_axis_avg_buffer_3_s_axi_rready;
  output [1:0]ext_axis_avg_buffer_3_s_axi_rresp;
  output ext_axis_avg_buffer_3_s_axi_rvalid;
  input [31:0]ext_axis_avg_buffer_3_s_axi_wdata;
  output ext_axis_avg_buffer_3_s_axi_wready;
  input [3:0]ext_axis_avg_buffer_3_s_axi_wstrb;
  input ext_axis_avg_buffer_3_s_axi_wvalid;
  input [5:0]ext_axis_awg_tuning_v1_10_s_axi_araddr;
  input [2:0]ext_axis_awg_tuning_v1_10_s_axi_arprot;
  output ext_axis_awg_tuning_v1_10_s_axi_arready;
  input ext_axis_awg_tuning_v1_10_s_axi_arvalid;
  input [5:0]ext_axis_awg_tuning_v1_10_s_axi_awaddr;
  input [2:0]ext_axis_awg_tuning_v1_10_s_axi_awprot;
  output ext_axis_awg_tuning_v1_10_s_axi_awready;
  input ext_axis_awg_tuning_v1_10_s_axi_awvalid;
  input ext_axis_awg_tuning_v1_10_s_axi_bready;
  output [1:0]ext_axis_awg_tuning_v1_10_s_axi_bresp;
  output ext_axis_awg_tuning_v1_10_s_axi_bvalid;
  output [31:0]ext_axis_awg_tuning_v1_10_s_axi_rdata;
  input ext_axis_awg_tuning_v1_10_s_axi_rready;
  output [1:0]ext_axis_awg_tuning_v1_10_s_axi_rresp;
  output ext_axis_awg_tuning_v1_10_s_axi_rvalid;
  input [31:0]ext_axis_awg_tuning_v1_10_s_axi_wdata;
  output ext_axis_awg_tuning_v1_10_s_axi_wready;
  input [3:0]ext_axis_awg_tuning_v1_10_s_axi_wstrb;
  input ext_axis_awg_tuning_v1_10_s_axi_wvalid;
  input [5:0]ext_axis_awg_tuning_v1_11_s_axi_araddr;
  input [2:0]ext_axis_awg_tuning_v1_11_s_axi_arprot;
  output ext_axis_awg_tuning_v1_11_s_axi_arready;
  input ext_axis_awg_tuning_v1_11_s_axi_arvalid;
  input [5:0]ext_axis_awg_tuning_v1_11_s_axi_awaddr;
  input [2:0]ext_axis_awg_tuning_v1_11_s_axi_awprot;
  output ext_axis_awg_tuning_v1_11_s_axi_awready;
  input ext_axis_awg_tuning_v1_11_s_axi_awvalid;
  input ext_axis_awg_tuning_v1_11_s_axi_bready;
  output [1:0]ext_axis_awg_tuning_v1_11_s_axi_bresp;
  output ext_axis_awg_tuning_v1_11_s_axi_bvalid;
  output [31:0]ext_axis_awg_tuning_v1_11_s_axi_rdata;
  input ext_axis_awg_tuning_v1_11_s_axi_rready;
  output [1:0]ext_axis_awg_tuning_v1_11_s_axi_rresp;
  output ext_axis_awg_tuning_v1_11_s_axi_rvalid;
  input [31:0]ext_axis_awg_tuning_v1_11_s_axi_wdata;
  output ext_axis_awg_tuning_v1_11_s_axi_wready;
  input [3:0]ext_axis_awg_tuning_v1_11_s_axi_wstrb;
  input ext_axis_awg_tuning_v1_11_s_axi_wvalid;
  input [5:0]ext_axis_awg_tuning_v1_4_s_axi_araddr;
  input [2:0]ext_axis_awg_tuning_v1_4_s_axi_arprot;
  output ext_axis_awg_tuning_v1_4_s_axi_arready;
  input ext_axis_awg_tuning_v1_4_s_axi_arvalid;
  input [5:0]ext_axis_awg_tuning_v1_4_s_axi_awaddr;
  input [2:0]ext_axis_awg_tuning_v1_4_s_axi_awprot;
  output ext_axis_awg_tuning_v1_4_s_axi_awready;
  input ext_axis_awg_tuning_v1_4_s_axi_awvalid;
  input ext_axis_awg_tuning_v1_4_s_axi_bready;
  output [1:0]ext_axis_awg_tuning_v1_4_s_axi_bresp;
  output ext_axis_awg_tuning_v1_4_s_axi_bvalid;
  output [31:0]ext_axis_awg_tuning_v1_4_s_axi_rdata;
  input ext_axis_awg_tuning_v1_4_s_axi_rready;
  output [1:0]ext_axis_awg_tuning_v1_4_s_axi_rresp;
  output ext_axis_awg_tuning_v1_4_s_axi_rvalid;
  input [31:0]ext_axis_awg_tuning_v1_4_s_axi_wdata;
  output ext_axis_awg_tuning_v1_4_s_axi_wready;
  input [3:0]ext_axis_awg_tuning_v1_4_s_axi_wstrb;
  input ext_axis_awg_tuning_v1_4_s_axi_wvalid;
  input [5:0]ext_axis_awg_tuning_v1_5_s_axi_araddr;
  input [2:0]ext_axis_awg_tuning_v1_5_s_axi_arprot;
  output ext_axis_awg_tuning_v1_5_s_axi_arready;
  input ext_axis_awg_tuning_v1_5_s_axi_arvalid;
  input [5:0]ext_axis_awg_tuning_v1_5_s_axi_awaddr;
  input [2:0]ext_axis_awg_tuning_v1_5_s_axi_awprot;
  output ext_axis_awg_tuning_v1_5_s_axi_awready;
  input ext_axis_awg_tuning_v1_5_s_axi_awvalid;
  input ext_axis_awg_tuning_v1_5_s_axi_bready;
  output [1:0]ext_axis_awg_tuning_v1_5_s_axi_bresp;
  output ext_axis_awg_tuning_v1_5_s_axi_bvalid;
  output [31:0]ext_axis_awg_tuning_v1_5_s_axi_rdata;
  input ext_axis_awg_tuning_v1_5_s_axi_rready;
  output [1:0]ext_axis_awg_tuning_v1_5_s_axi_rresp;
  output ext_axis_awg_tuning_v1_5_s_axi_rvalid;
  input [31:0]ext_axis_awg_tuning_v1_5_s_axi_wdata;
  output ext_axis_awg_tuning_v1_5_s_axi_wready;
  input [3:0]ext_axis_awg_tuning_v1_5_s_axi_wstrb;
  input ext_axis_awg_tuning_v1_5_s_axi_wvalid;
  input [5:0]ext_axis_awg_tuning_v1_6_s_axi_araddr;
  input [2:0]ext_axis_awg_tuning_v1_6_s_axi_arprot;
  output ext_axis_awg_tuning_v1_6_s_axi_arready;
  input ext_axis_awg_tuning_v1_6_s_axi_arvalid;
  input [5:0]ext_axis_awg_tuning_v1_6_s_axi_awaddr;
  input [2:0]ext_axis_awg_tuning_v1_6_s_axi_awprot;
  output ext_axis_awg_tuning_v1_6_s_axi_awready;
  input ext_axis_awg_tuning_v1_6_s_axi_awvalid;
  input ext_axis_awg_tuning_v1_6_s_axi_bready;
  output [1:0]ext_axis_awg_tuning_v1_6_s_axi_bresp;
  output ext_axis_awg_tuning_v1_6_s_axi_bvalid;
  output [31:0]ext_axis_awg_tuning_v1_6_s_axi_rdata;
  input ext_axis_awg_tuning_v1_6_s_axi_rready;
  output [1:0]ext_axis_awg_tuning_v1_6_s_axi_rresp;
  output ext_axis_awg_tuning_v1_6_s_axi_rvalid;
  input [31:0]ext_axis_awg_tuning_v1_6_s_axi_wdata;
  output ext_axis_awg_tuning_v1_6_s_axi_wready;
  input [3:0]ext_axis_awg_tuning_v1_6_s_axi_wstrb;
  input ext_axis_awg_tuning_v1_6_s_axi_wvalid;
  input [5:0]ext_axis_awg_tuning_v1_8_s_axi_araddr;
  input [2:0]ext_axis_awg_tuning_v1_8_s_axi_arprot;
  output ext_axis_awg_tuning_v1_8_s_axi_arready;
  input ext_axis_awg_tuning_v1_8_s_axi_arvalid;
  input [5:0]ext_axis_awg_tuning_v1_8_s_axi_awaddr;
  input [2:0]ext_axis_awg_tuning_v1_8_s_axi_awprot;
  output ext_axis_awg_tuning_v1_8_s_axi_awready;
  input ext_axis_awg_tuning_v1_8_s_axi_awvalid;
  input ext_axis_awg_tuning_v1_8_s_axi_bready;
  output [1:0]ext_axis_awg_tuning_v1_8_s_axi_bresp;
  output ext_axis_awg_tuning_v1_8_s_axi_bvalid;
  output [31:0]ext_axis_awg_tuning_v1_8_s_axi_rdata;
  input ext_axis_awg_tuning_v1_8_s_axi_rready;
  output [1:0]ext_axis_awg_tuning_v1_8_s_axi_rresp;
  output ext_axis_awg_tuning_v1_8_s_axi_rvalid;
  input [31:0]ext_axis_awg_tuning_v1_8_s_axi_wdata;
  output ext_axis_awg_tuning_v1_8_s_axi_wready;
  input [3:0]ext_axis_awg_tuning_v1_8_s_axi_wstrb;
  input ext_axis_awg_tuning_v1_8_s_axi_wvalid;
  input [5:0]ext_axis_awg_tuning_v1_9_s_axi_araddr;
  input [2:0]ext_axis_awg_tuning_v1_9_s_axi_arprot;
  output ext_axis_awg_tuning_v1_9_s_axi_arready;
  input ext_axis_awg_tuning_v1_9_s_axi_arvalid;
  input [5:0]ext_axis_awg_tuning_v1_9_s_axi_awaddr;
  input [2:0]ext_axis_awg_tuning_v1_9_s_axi_awprot;
  output ext_axis_awg_tuning_v1_9_s_axi_awready;
  input ext_axis_awg_tuning_v1_9_s_axi_awvalid;
  input ext_axis_awg_tuning_v1_9_s_axi_bready;
  output [1:0]ext_axis_awg_tuning_v1_9_s_axi_bresp;
  output ext_axis_awg_tuning_v1_9_s_axi_bvalid;
  output [31:0]ext_axis_awg_tuning_v1_9_s_axi_rdata;
  input ext_axis_awg_tuning_v1_9_s_axi_rready;
  output [1:0]ext_axis_awg_tuning_v1_9_s_axi_rresp;
  output ext_axis_awg_tuning_v1_9_s_axi_rvalid;
  input [31:0]ext_axis_awg_tuning_v1_9_s_axi_wdata;
  output ext_axis_awg_tuning_v1_9_s_axi_wready;
  input [3:0]ext_axis_awg_tuning_v1_9_s_axi_wstrb;
  input ext_axis_awg_tuning_v1_9_s_axi_wvalid;
  input [127:0]ext_axis_dyn_readout_v1_0_s1_axis_tdata;
  output ext_axis_dyn_readout_v1_0_s1_axis_tready;
  input ext_axis_dyn_readout_v1_0_s1_axis_tvalid;
  input [127:0]ext_axis_dyn_readout_v1_1_s1_axis_tdata;
  output ext_axis_dyn_readout_v1_1_s1_axis_tready;
  input ext_axis_dyn_readout_v1_1_s1_axis_tvalid;
  input [127:0]ext_axis_dyn_readout_v1_2_s1_axis_tdata;
  output ext_axis_dyn_readout_v1_2_s1_axis_tready;
  input ext_axis_dyn_readout_v1_2_s1_axis_tvalid;
  input [127:0]ext_axis_dyn_readout_v1_3_s1_axis_tdata;
  output ext_axis_dyn_readout_v1_3_s1_axis_tready;
  input ext_axis_dyn_readout_v1_3_s1_axis_tvalid;
  output [255:0]ext_axis_register_slice_0_m_axis_tdata;
  input ext_axis_register_slice_0_m_axis_tready;
  output ext_axis_register_slice_0_m_axis_tvalid;
  output [255:0]ext_axis_register_slice_10_m_axis_tdata;
  input ext_axis_register_slice_10_m_axis_tready;
  output ext_axis_register_slice_10_m_axis_tvalid;
  output [255:0]ext_axis_register_slice_11_m_axis_tdata;
  input ext_axis_register_slice_11_m_axis_tready;
  output ext_axis_register_slice_11_m_axis_tvalid;
  output [255:0]ext_axis_register_slice_12_m_axis_tdata;
  input ext_axis_register_slice_12_m_axis_tready;
  output ext_axis_register_slice_12_m_axis_tvalid;
  output [255:0]ext_axis_register_slice_13_m_axis_tdata;
  input ext_axis_register_slice_13_m_axis_tready;
  output ext_axis_register_slice_13_m_axis_tvalid;
  output [255:0]ext_axis_register_slice_14_m_axis_tdata;
  input ext_axis_register_slice_14_m_axis_tready;
  output ext_axis_register_slice_14_m_axis_tvalid;
  output [255:0]ext_axis_register_slice_15_m_axis_tdata;
  input ext_axis_register_slice_15_m_axis_tready;
  output ext_axis_register_slice_15_m_axis_tvalid;
  output [255:0]ext_axis_register_slice_16_m_axis_tdata;
  input ext_axis_register_slice_16_m_axis_tready;
  output ext_axis_register_slice_16_m_axis_tvalid;
  output [255:0]ext_axis_register_slice_1_m_axis_tdata;
  input ext_axis_register_slice_1_m_axis_tready;
  output ext_axis_register_slice_1_m_axis_tvalid;
  output [255:0]ext_axis_register_slice_2_m_axis_tdata;
  input ext_axis_register_slice_2_m_axis_tready;
  output ext_axis_register_slice_2_m_axis_tvalid;
  output [255:0]ext_axis_register_slice_3_m_axis_tdata;
  input ext_axis_register_slice_3_m_axis_tready;
  output ext_axis_register_slice_3_m_axis_tvalid;
  output [255:0]ext_axis_register_slice_8_m_axis_tdata;
  input ext_axis_register_slice_8_m_axis_tready;
  output ext_axis_register_slice_8_m_axis_tvalid;
  input [5:0]ext_axis_signal_gen_v6_0_s_axi_araddr;
  input [2:0]ext_axis_signal_gen_v6_0_s_axi_arprot;
  output ext_axis_signal_gen_v6_0_s_axi_arready;
  input ext_axis_signal_gen_v6_0_s_axi_arvalid;
  input [5:0]ext_axis_signal_gen_v6_0_s_axi_awaddr;
  input [2:0]ext_axis_signal_gen_v6_0_s_axi_awprot;
  output ext_axis_signal_gen_v6_0_s_axi_awready;
  input ext_axis_signal_gen_v6_0_s_axi_awvalid;
  input ext_axis_signal_gen_v6_0_s_axi_bready;
  output [1:0]ext_axis_signal_gen_v6_0_s_axi_bresp;
  output ext_axis_signal_gen_v6_0_s_axi_bvalid;
  output [31:0]ext_axis_signal_gen_v6_0_s_axi_rdata;
  input ext_axis_signal_gen_v6_0_s_axi_rready;
  output [1:0]ext_axis_signal_gen_v6_0_s_axi_rresp;
  output ext_axis_signal_gen_v6_0_s_axi_rvalid;
  input [31:0]ext_axis_signal_gen_v6_0_s_axi_wdata;
  output ext_axis_signal_gen_v6_0_s_axi_wready;
  input [3:0]ext_axis_signal_gen_v6_0_s_axi_wstrb;
  input ext_axis_signal_gen_v6_0_s_axi_wvalid;
  input [5:0]ext_axis_signal_gen_v6_1_s_axi_araddr;
  input [2:0]ext_axis_signal_gen_v6_1_s_axi_arprot;
  output ext_axis_signal_gen_v6_1_s_axi_arready;
  input ext_axis_signal_gen_v6_1_s_axi_arvalid;
  input [5:0]ext_axis_signal_gen_v6_1_s_axi_awaddr;
  input [2:0]ext_axis_signal_gen_v6_1_s_axi_awprot;
  output ext_axis_signal_gen_v6_1_s_axi_awready;
  input ext_axis_signal_gen_v6_1_s_axi_awvalid;
  input ext_axis_signal_gen_v6_1_s_axi_bready;
  output [1:0]ext_axis_signal_gen_v6_1_s_axi_bresp;
  output ext_axis_signal_gen_v6_1_s_axi_bvalid;
  output [31:0]ext_axis_signal_gen_v6_1_s_axi_rdata;
  input ext_axis_signal_gen_v6_1_s_axi_rready;
  output [1:0]ext_axis_signal_gen_v6_1_s_axi_rresp;
  output ext_axis_signal_gen_v6_1_s_axi_rvalid;
  input [31:0]ext_axis_signal_gen_v6_1_s_axi_wdata;
  output ext_axis_signal_gen_v6_1_s_axi_wready;
  input [3:0]ext_axis_signal_gen_v6_1_s_axi_wstrb;
  input ext_axis_signal_gen_v6_1_s_axi_wvalid;
  input [5:0]ext_axis_signal_gen_v6_2_s_axi_araddr;
  input [2:0]ext_axis_signal_gen_v6_2_s_axi_arprot;
  output ext_axis_signal_gen_v6_2_s_axi_arready;
  input ext_axis_signal_gen_v6_2_s_axi_arvalid;
  input [5:0]ext_axis_signal_gen_v6_2_s_axi_awaddr;
  input [2:0]ext_axis_signal_gen_v6_2_s_axi_awprot;
  output ext_axis_signal_gen_v6_2_s_axi_awready;
  input ext_axis_signal_gen_v6_2_s_axi_awvalid;
  input ext_axis_signal_gen_v6_2_s_axi_bready;
  output [1:0]ext_axis_signal_gen_v6_2_s_axi_bresp;
  output ext_axis_signal_gen_v6_2_s_axi_bvalid;
  output [31:0]ext_axis_signal_gen_v6_2_s_axi_rdata;
  input ext_axis_signal_gen_v6_2_s_axi_rready;
  output [1:0]ext_axis_signal_gen_v6_2_s_axi_rresp;
  output ext_axis_signal_gen_v6_2_s_axi_rvalid;
  input [31:0]ext_axis_signal_gen_v6_2_s_axi_wdata;
  output ext_axis_signal_gen_v6_2_s_axi_wready;
  input [3:0]ext_axis_signal_gen_v6_2_s_axi_wstrb;
  input ext_axis_signal_gen_v6_2_s_axi_wvalid;
  input [5:0]ext_axis_signal_gen_v6_3_s_axi_araddr;
  input [2:0]ext_axis_signal_gen_v6_3_s_axi_arprot;
  output ext_axis_signal_gen_v6_3_s_axi_arready;
  input ext_axis_signal_gen_v6_3_s_axi_arvalid;
  input [5:0]ext_axis_signal_gen_v6_3_s_axi_awaddr;
  input [2:0]ext_axis_signal_gen_v6_3_s_axi_awprot;
  output ext_axis_signal_gen_v6_3_s_axi_awready;
  input ext_axis_signal_gen_v6_3_s_axi_awvalid;
  input ext_axis_signal_gen_v6_3_s_axi_bready;
  output [1:0]ext_axis_signal_gen_v6_3_s_axi_bresp;
  output ext_axis_signal_gen_v6_3_s_axi_bvalid;
  output [31:0]ext_axis_signal_gen_v6_3_s_axi_rdata;
  input ext_axis_signal_gen_v6_3_s_axi_rready;
  output [1:0]ext_axis_signal_gen_v6_3_s_axi_rresp;
  output ext_axis_signal_gen_v6_3_s_axi_rvalid;
  input [31:0]ext_axis_signal_gen_v6_3_s_axi_wdata;
  output ext_axis_signal_gen_v6_3_s_axi_wready;
  input [3:0]ext_axis_signal_gen_v6_3_s_axi_wstrb;
  input ext_axis_signal_gen_v6_3_s_axi_wvalid;
  input [5:0]ext_axis_square_pulse_v1_0_s_axi_araddr;
  input [2:0]ext_axis_square_pulse_v1_0_s_axi_arprot;
  output ext_axis_square_pulse_v1_0_s_axi_arready;
  input ext_axis_square_pulse_v1_0_s_axi_arvalid;
  input [5:0]ext_axis_square_pulse_v1_0_s_axi_awaddr;
  input [2:0]ext_axis_square_pulse_v1_0_s_axi_awprot;
  output ext_axis_square_pulse_v1_0_s_axi_awready;
  input ext_axis_square_pulse_v1_0_s_axi_awvalid;
  input ext_axis_square_pulse_v1_0_s_axi_bready;
  output [1:0]ext_axis_square_pulse_v1_0_s_axi_bresp;
  output ext_axis_square_pulse_v1_0_s_axi_bvalid;
  output [31:0]ext_axis_square_pulse_v1_0_s_axi_rdata;
  input ext_axis_square_pulse_v1_0_s_axi_rready;
  output [1:0]ext_axis_square_pulse_v1_0_s_axi_rresp;
  output ext_axis_square_pulse_v1_0_s_axi_rvalid;
  input [31:0]ext_axis_square_pulse_v1_0_s_axi_wdata;
  output ext_axis_square_pulse_v1_0_s_axi_wready;
  input [3:0]ext_axis_square_pulse_v1_0_s_axi_wstrb;
  input ext_axis_square_pulse_v1_0_s_axi_wvalid;
  output [63:0]ext_axis_switch_avg_M00_AXIS_tdata;
  output [0:0]ext_axis_switch_avg_M00_AXIS_tlast;
  input [0:0]ext_axis_switch_avg_M00_AXIS_tready;
  output [0:0]ext_axis_switch_avg_M00_AXIS_tvalid;
  input [6:0]ext_axis_switch_avg_S_AXI_CTRL_araddr;
  output ext_axis_switch_avg_S_AXI_CTRL_arready;
  input ext_axis_switch_avg_S_AXI_CTRL_arvalid;
  input [6:0]ext_axis_switch_avg_S_AXI_CTRL_awaddr;
  output ext_axis_switch_avg_S_AXI_CTRL_awready;
  input ext_axis_switch_avg_S_AXI_CTRL_awvalid;
  input ext_axis_switch_avg_S_AXI_CTRL_bready;
  output [1:0]ext_axis_switch_avg_S_AXI_CTRL_bresp;
  output ext_axis_switch_avg_S_AXI_CTRL_bvalid;
  output [31:0]ext_axis_switch_avg_S_AXI_CTRL_rdata;
  input ext_axis_switch_avg_S_AXI_CTRL_rready;
  output [1:0]ext_axis_switch_avg_S_AXI_CTRL_rresp;
  output ext_axis_switch_avg_S_AXI_CTRL_rvalid;
  input [31:0]ext_axis_switch_avg_S_AXI_CTRL_wdata;
  output ext_axis_switch_avg_S_AXI_CTRL_wready;
  input ext_axis_switch_avg_S_AXI_CTRL_wvalid;
  output [31:0]ext_axis_switch_buf_M00_AXIS_tdata;
  output [0:0]ext_axis_switch_buf_M00_AXIS_tlast;
  input [0:0]ext_axis_switch_buf_M00_AXIS_tready;
  output [0:0]ext_axis_switch_buf_M00_AXIS_tvalid;
  input [6:0]ext_axis_switch_buf_S_AXI_CTRL_araddr;
  output ext_axis_switch_buf_S_AXI_CTRL_arready;
  input ext_axis_switch_buf_S_AXI_CTRL_arvalid;
  input [6:0]ext_axis_switch_buf_S_AXI_CTRL_awaddr;
  output ext_axis_switch_buf_S_AXI_CTRL_awready;
  input ext_axis_switch_buf_S_AXI_CTRL_awvalid;
  input ext_axis_switch_buf_S_AXI_CTRL_bready;
  output [1:0]ext_axis_switch_buf_S_AXI_CTRL_bresp;
  output ext_axis_switch_buf_S_AXI_CTRL_bvalid;
  output [31:0]ext_axis_switch_buf_S_AXI_CTRL_rdata;
  input ext_axis_switch_buf_S_AXI_CTRL_rready;
  output [1:0]ext_axis_switch_buf_S_AXI_CTRL_rresp;
  output ext_axis_switch_buf_S_AXI_CTRL_rvalid;
  input [31:0]ext_axis_switch_buf_S_AXI_CTRL_wdata;
  output ext_axis_switch_buf_S_AXI_CTRL_wready;
  input ext_axis_switch_buf_S_AXI_CTRL_wvalid;
  input [6:0]ext_axis_switch_ddr_S_AXI_CTRL_araddr;
  output ext_axis_switch_ddr_S_AXI_CTRL_arready;
  input ext_axis_switch_ddr_S_AXI_CTRL_arvalid;
  input [6:0]ext_axis_switch_ddr_S_AXI_CTRL_awaddr;
  output ext_axis_switch_ddr_S_AXI_CTRL_awready;
  input ext_axis_switch_ddr_S_AXI_CTRL_awvalid;
  input ext_axis_switch_ddr_S_AXI_CTRL_bready;
  output [1:0]ext_axis_switch_ddr_S_AXI_CTRL_bresp;
  output ext_axis_switch_ddr_S_AXI_CTRL_bvalid;
  output [31:0]ext_axis_switch_ddr_S_AXI_CTRL_rdata;
  input ext_axis_switch_ddr_S_AXI_CTRL_rready;
  output [1:0]ext_axis_switch_ddr_S_AXI_CTRL_rresp;
  output ext_axis_switch_ddr_S_AXI_CTRL_rvalid;
  input [31:0]ext_axis_switch_ddr_S_AXI_CTRL_wdata;
  output ext_axis_switch_ddr_S_AXI_CTRL_wready;
  input ext_axis_switch_ddr_S_AXI_CTRL_wvalid;
  output [31:0]ext_axis_switch_gen_M04_AXIS_tdata;
  output [3:0]ext_axis_switch_gen_M04_AXIS_tkeep;
  output [0:0]ext_axis_switch_gen_M04_AXIS_tlast;
  input [0:0]ext_axis_switch_gen_M04_AXIS_tready;
  output [0:0]ext_axis_switch_gen_M04_AXIS_tvalid;
  output [31:0]ext_axis_switch_gen_M05_AXIS_tdata;
  output [3:0]ext_axis_switch_gen_M05_AXIS_tkeep;
  output [0:0]ext_axis_switch_gen_M05_AXIS_tlast;
  input [0:0]ext_axis_switch_gen_M05_AXIS_tready;
  output [0:0]ext_axis_switch_gen_M05_AXIS_tvalid;
  output [31:0]ext_axis_switch_gen_M06_AXIS_tdata;
  output [3:0]ext_axis_switch_gen_M06_AXIS_tkeep;
  output [0:0]ext_axis_switch_gen_M06_AXIS_tlast;
  input [0:0]ext_axis_switch_gen_M06_AXIS_tready;
  output [0:0]ext_axis_switch_gen_M06_AXIS_tvalid;
  output [31:0]ext_axis_switch_gen_M07_AXIS_tdata;
  output [3:0]ext_axis_switch_gen_M07_AXIS_tkeep;
  output [0:0]ext_axis_switch_gen_M07_AXIS_tlast;
  input [0:0]ext_axis_switch_gen_M07_AXIS_tready;
  output [0:0]ext_axis_switch_gen_M07_AXIS_tvalid;
  output [31:0]ext_axis_switch_gen_M08_AXIS_tdata;
  output [3:0]ext_axis_switch_gen_M08_AXIS_tkeep;
  output [0:0]ext_axis_switch_gen_M08_AXIS_tlast;
  input [0:0]ext_axis_switch_gen_M08_AXIS_tready;
  output [0:0]ext_axis_switch_gen_M08_AXIS_tvalid;
  output [31:0]ext_axis_switch_gen_M09_AXIS_tdata;
  output [3:0]ext_axis_switch_gen_M09_AXIS_tkeep;
  output [0:0]ext_axis_switch_gen_M09_AXIS_tlast;
  input [0:0]ext_axis_switch_gen_M09_AXIS_tready;
  output [0:0]ext_axis_switch_gen_M09_AXIS_tvalid;
  output [31:0]ext_axis_switch_gen_M10_AXIS_tdata;
  output [3:0]ext_axis_switch_gen_M10_AXIS_tkeep;
  output [0:0]ext_axis_switch_gen_M10_AXIS_tlast;
  input [0:0]ext_axis_switch_gen_M10_AXIS_tready;
  output [0:0]ext_axis_switch_gen_M10_AXIS_tvalid;
  output [31:0]ext_axis_switch_gen_M11_AXIS_tdata;
  output [3:0]ext_axis_switch_gen_M11_AXIS_tkeep;
  output [0:0]ext_axis_switch_gen_M11_AXIS_tlast;
  input [0:0]ext_axis_switch_gen_M11_AXIS_tready;
  output [0:0]ext_axis_switch_gen_M11_AXIS_tvalid;
  input [31:0]ext_axis_switch_gen_S00_AXIS_tdata;
  input [3:0]ext_axis_switch_gen_S00_AXIS_tkeep;
  input [0:0]ext_axis_switch_gen_S00_AXIS_tlast;
  output [0:0]ext_axis_switch_gen_S00_AXIS_tready;
  input [0:0]ext_axis_switch_gen_S00_AXIS_tvalid;
  input [6:0]ext_axis_switch_gen_S_AXI_CTRL_araddr;
  output ext_axis_switch_gen_S_AXI_CTRL_arready;
  input ext_axis_switch_gen_S_AXI_CTRL_arvalid;
  input [6:0]ext_axis_switch_gen_S_AXI_CTRL_awaddr;
  output ext_axis_switch_gen_S_AXI_CTRL_awready;
  input ext_axis_switch_gen_S_AXI_CTRL_awvalid;
  input ext_axis_switch_gen_S_AXI_CTRL_bready;
  output [1:0]ext_axis_switch_gen_S_AXI_CTRL_bresp;
  output ext_axis_switch_gen_S_AXI_CTRL_bvalid;
  output [31:0]ext_axis_switch_gen_S_AXI_CTRL_rdata;
  input ext_axis_switch_gen_S_AXI_CTRL_rready;
  output [1:0]ext_axis_switch_gen_S_AXI_CTRL_rresp;
  output ext_axis_switch_gen_S_AXI_CTRL_rvalid;
  input [31:0]ext_axis_switch_gen_S_AXI_CTRL_wdata;
  output ext_axis_switch_gen_S_AXI_CTRL_wready;
  input ext_axis_switch_gen_S_AXI_CTRL_wvalid;
  input [6:0]ext_axis_switch_mr_S_AXI_CTRL_araddr;
  output ext_axis_switch_mr_S_AXI_CTRL_arready;
  input ext_axis_switch_mr_S_AXI_CTRL_arvalid;
  input [6:0]ext_axis_switch_mr_S_AXI_CTRL_awaddr;
  output ext_axis_switch_mr_S_AXI_CTRL_awready;
  input ext_axis_switch_mr_S_AXI_CTRL_awvalid;
  input ext_axis_switch_mr_S_AXI_CTRL_bready;
  output [1:0]ext_axis_switch_mr_S_AXI_CTRL_bresp;
  output ext_axis_switch_mr_S_AXI_CTRL_bvalid;
  output [31:0]ext_axis_switch_mr_S_AXI_CTRL_rdata;
  input ext_axis_switch_mr_S_AXI_CTRL_rready;
  output [1:0]ext_axis_switch_mr_S_AXI_CTRL_rresp;
  output ext_axis_switch_mr_S_AXI_CTRL_rvalid;
  input [31:0]ext_axis_switch_mr_S_AXI_CTRL_wdata;
  output ext_axis_switch_mr_S_AXI_CTRL_wready;
  input ext_axis_switch_mr_S_AXI_CTRL_wvalid;
  output [31:0]ext_axis_tproc64x32_x8_0_m0_axis_tdata;
  output ext_axis_tproc64x32_x8_0_m0_axis_tlast;
  input ext_axis_tproc64x32_x8_0_m0_axis_tready;
  output ext_axis_tproc64x32_x8_0_m0_axis_tvalid;
  output [19:0]ext_axis_tproc64x32_x8_0_pmem_addr;
  input [63:0]ext_axis_tproc64x32_x8_0_pmem_do;
  input [31:0]ext_axis_tproc64x32_x8_0_s0_axis_tdata;
  input ext_axis_tproc64x32_x8_0_s0_axis_tlast;
  output ext_axis_tproc64x32_x8_0_s0_axis_tready;
  input ext_axis_tproc64x32_x8_0_s0_axis_tvalid;
  input [31:0]ext_axis_tproc64x32_x8_0_s_axi_araddr;
  input [2:0]ext_axis_tproc64x32_x8_0_s_axi_arprot;
  output ext_axis_tproc64x32_x8_0_s_axi_arready;
  input ext_axis_tproc64x32_x8_0_s_axi_arvalid;
  input [31:0]ext_axis_tproc64x32_x8_0_s_axi_awaddr;
  input [2:0]ext_axis_tproc64x32_x8_0_s_axi_awprot;
  output ext_axis_tproc64x32_x8_0_s_axi_awready;
  input ext_axis_tproc64x32_x8_0_s_axi_awvalid;
  input ext_axis_tproc64x32_x8_0_s_axi_bready;
  output [1:0]ext_axis_tproc64x32_x8_0_s_axi_bresp;
  output ext_axis_tproc64x32_x8_0_s_axi_bvalid;
  output [31:0]ext_axis_tproc64x32_x8_0_s_axi_rdata;
  input ext_axis_tproc64x32_x8_0_s_axi_rready;
  output [1:0]ext_axis_tproc64x32_x8_0_s_axi_rresp;
  output ext_axis_tproc64x32_x8_0_s_axi_rvalid;
  input [31:0]ext_axis_tproc64x32_x8_0_s_axi_wdata;
  output ext_axis_tproc64x32_x8_0_s_axi_wready;
  input [3:0]ext_axis_tproc64x32_x8_0_s_axi_wstrb;
  input ext_axis_tproc64x32_x8_0_s_axi_wvalid;
  input ext_axis_tproc64x32_x8_0_start;
  input ext_c_shift_ram_0_D;
  output [0:0]ext_c_shift_ram_0_Q;
  output [31:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awaddr;
  output [1:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awburst;
  output [3:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awcache;
  output [0:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awid;
  output [7:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlen;
  output ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlock;
  output [2:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awprot;
  output [3:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awqos;
  input ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awready;
  output [3:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awregion;
  output [2:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awsize;
  output ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awvalid;
  input [0:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bid;
  output ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bready;
  input [1:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bresp;
  input ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bvalid;
  output [255:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wdata;
  output ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wlast;
  input ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wready;
  output [31:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wstrb;
  output ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wvalid;
  input [7:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_araddr;
  input [2:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arprot;
  output ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arready;
  input ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arvalid;
  input [7:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awaddr;
  input [2:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awprot;
  output ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awready;
  input ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awvalid;
  input ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bready;
  output [1:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bresp;
  output ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bvalid;
  output [31:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rdata;
  input ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rready;
  output [1:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rresp;
  output ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rvalid;
  input [31:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wdata;
  output ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wready;
  input [3:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wstrb;
  input ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wvalid;
  output ext_ddr4_axis_fir_decim_300to1_v2_0_capture_trigger;
  output [31:0]ext_mr_buffer_et_0_m00_axis_tdata;
  output ext_mr_buffer_et_0_m00_axis_tlast;
  input ext_mr_buffer_et_0_m00_axis_tready;
  output [3:0]ext_mr_buffer_et_0_m00_axis_tstrb;
  output ext_mr_buffer_et_0_m00_axis_tvalid;
  input [5:0]ext_mr_buffer_et_0_s00_axi_araddr;
  input [2:0]ext_mr_buffer_et_0_s00_axi_arprot;
  output ext_mr_buffer_et_0_s00_axi_arready;
  input ext_mr_buffer_et_0_s00_axi_arvalid;
  input [5:0]ext_mr_buffer_et_0_s00_axi_awaddr;
  input [2:0]ext_mr_buffer_et_0_s00_axi_awprot;
  output ext_mr_buffer_et_0_s00_axi_awready;
  input ext_mr_buffer_et_0_s00_axi_awvalid;
  input ext_mr_buffer_et_0_s00_axi_bready;
  output [1:0]ext_mr_buffer_et_0_s00_axi_bresp;
  output ext_mr_buffer_et_0_s00_axi_bvalid;
  output [31:0]ext_mr_buffer_et_0_s00_axi_rdata;
  input ext_mr_buffer_et_0_s00_axi_rready;
  output [1:0]ext_mr_buffer_et_0_s00_axi_rresp;
  output ext_mr_buffer_et_0_s00_axi_rvalid;
  input [31:0]ext_mr_buffer_et_0_s00_axi_wdata;
  output ext_mr_buffer_et_0_s00_axi_wready;
  input [3:0]ext_mr_buffer_et_0_s00_axi_wstrb;
  input ext_mr_buffer_et_0_s00_axi_wvalid;
  output ext_qick_vec2bit_0_dout0;
  output ext_qick_vec2bit_0_dout1;
  output ext_qick_vec2bit_0_dout2;
  output ext_qick_vec2bit_0_dout3;
  output ext_qick_vec2bit_0_dout4;
  output ext_qick_vec2bit_0_dout5;
  output ext_qick_vec2bit_0_dout6;
  output [63:0]ext_xlconstant_0_dout;
  output [0:0]ext_xlconstant_1_dout;
  output [0:0]ext_xlconstant_2_dout;
  output [7:0]ext_xlconstant_3_dout;
  output [11:0]ext_xlconstant_4_dout;
  input resetn;

  wire clk_300000000;
  wire clk_333250000;
  wire clk_99999985;
  wire [5:0]ext_axis_avg_buffer_0_s_axi_araddr;
  wire [2:0]ext_axis_avg_buffer_0_s_axi_arprot;
  wire ext_axis_avg_buffer_0_s_axi_arready;
  wire ext_axis_avg_buffer_0_s_axi_arvalid;
  wire [5:0]ext_axis_avg_buffer_0_s_axi_awaddr;
  wire [2:0]ext_axis_avg_buffer_0_s_axi_awprot;
  wire ext_axis_avg_buffer_0_s_axi_awready;
  wire ext_axis_avg_buffer_0_s_axi_awvalid;
  wire ext_axis_avg_buffer_0_s_axi_bready;
  wire [1:0]ext_axis_avg_buffer_0_s_axi_bresp;
  wire ext_axis_avg_buffer_0_s_axi_bvalid;
  wire [31:0]ext_axis_avg_buffer_0_s_axi_rdata;
  wire ext_axis_avg_buffer_0_s_axi_rready;
  wire [1:0]ext_axis_avg_buffer_0_s_axi_rresp;
  wire ext_axis_avg_buffer_0_s_axi_rvalid;
  wire [31:0]ext_axis_avg_buffer_0_s_axi_wdata;
  wire ext_axis_avg_buffer_0_s_axi_wready;
  wire [3:0]ext_axis_avg_buffer_0_s_axi_wstrb;
  wire ext_axis_avg_buffer_0_s_axi_wvalid;
  wire [5:0]ext_axis_avg_buffer_1_s_axi_araddr;
  wire [2:0]ext_axis_avg_buffer_1_s_axi_arprot;
  wire ext_axis_avg_buffer_1_s_axi_arready;
  wire ext_axis_avg_buffer_1_s_axi_arvalid;
  wire [5:0]ext_axis_avg_buffer_1_s_axi_awaddr;
  wire [2:0]ext_axis_avg_buffer_1_s_axi_awprot;
  wire ext_axis_avg_buffer_1_s_axi_awready;
  wire ext_axis_avg_buffer_1_s_axi_awvalid;
  wire ext_axis_avg_buffer_1_s_axi_bready;
  wire [1:0]ext_axis_avg_buffer_1_s_axi_bresp;
  wire ext_axis_avg_buffer_1_s_axi_bvalid;
  wire [31:0]ext_axis_avg_buffer_1_s_axi_rdata;
  wire ext_axis_avg_buffer_1_s_axi_rready;
  wire [1:0]ext_axis_avg_buffer_1_s_axi_rresp;
  wire ext_axis_avg_buffer_1_s_axi_rvalid;
  wire [31:0]ext_axis_avg_buffer_1_s_axi_wdata;
  wire ext_axis_avg_buffer_1_s_axi_wready;
  wire [3:0]ext_axis_avg_buffer_1_s_axi_wstrb;
  wire ext_axis_avg_buffer_1_s_axi_wvalid;
  wire [5:0]ext_axis_avg_buffer_2_s_axi_araddr;
  wire [2:0]ext_axis_avg_buffer_2_s_axi_arprot;
  wire ext_axis_avg_buffer_2_s_axi_arready;
  wire ext_axis_avg_buffer_2_s_axi_arvalid;
  wire [5:0]ext_axis_avg_buffer_2_s_axi_awaddr;
  wire [2:0]ext_axis_avg_buffer_2_s_axi_awprot;
  wire ext_axis_avg_buffer_2_s_axi_awready;
  wire ext_axis_avg_buffer_2_s_axi_awvalid;
  wire ext_axis_avg_buffer_2_s_axi_bready;
  wire [1:0]ext_axis_avg_buffer_2_s_axi_bresp;
  wire ext_axis_avg_buffer_2_s_axi_bvalid;
  wire [31:0]ext_axis_avg_buffer_2_s_axi_rdata;
  wire ext_axis_avg_buffer_2_s_axi_rready;
  wire [1:0]ext_axis_avg_buffer_2_s_axi_rresp;
  wire ext_axis_avg_buffer_2_s_axi_rvalid;
  wire [31:0]ext_axis_avg_buffer_2_s_axi_wdata;
  wire ext_axis_avg_buffer_2_s_axi_wready;
  wire [3:0]ext_axis_avg_buffer_2_s_axi_wstrb;
  wire ext_axis_avg_buffer_2_s_axi_wvalid;
  wire [5:0]ext_axis_avg_buffer_3_s_axi_araddr;
  wire [2:0]ext_axis_avg_buffer_3_s_axi_arprot;
  wire ext_axis_avg_buffer_3_s_axi_arready;
  wire ext_axis_avg_buffer_3_s_axi_arvalid;
  wire [5:0]ext_axis_avg_buffer_3_s_axi_awaddr;
  wire [2:0]ext_axis_avg_buffer_3_s_axi_awprot;
  wire ext_axis_avg_buffer_3_s_axi_awready;
  wire ext_axis_avg_buffer_3_s_axi_awvalid;
  wire ext_axis_avg_buffer_3_s_axi_bready;
  wire [1:0]ext_axis_avg_buffer_3_s_axi_bresp;
  wire ext_axis_avg_buffer_3_s_axi_bvalid;
  wire [31:0]ext_axis_avg_buffer_3_s_axi_rdata;
  wire ext_axis_avg_buffer_3_s_axi_rready;
  wire [1:0]ext_axis_avg_buffer_3_s_axi_rresp;
  wire ext_axis_avg_buffer_3_s_axi_rvalid;
  wire [31:0]ext_axis_avg_buffer_3_s_axi_wdata;
  wire ext_axis_avg_buffer_3_s_axi_wready;
  wire [3:0]ext_axis_avg_buffer_3_s_axi_wstrb;
  wire ext_axis_avg_buffer_3_s_axi_wvalid;
  wire [5:0]ext_axis_awg_tuning_v1_10_s_axi_araddr;
  wire [2:0]ext_axis_awg_tuning_v1_10_s_axi_arprot;
  wire ext_axis_awg_tuning_v1_10_s_axi_arready;
  wire ext_axis_awg_tuning_v1_10_s_axi_arvalid;
  wire [5:0]ext_axis_awg_tuning_v1_10_s_axi_awaddr;
  wire [2:0]ext_axis_awg_tuning_v1_10_s_axi_awprot;
  wire ext_axis_awg_tuning_v1_10_s_axi_awready;
  wire ext_axis_awg_tuning_v1_10_s_axi_awvalid;
  wire ext_axis_awg_tuning_v1_10_s_axi_bready;
  wire [1:0]ext_axis_awg_tuning_v1_10_s_axi_bresp;
  wire ext_axis_awg_tuning_v1_10_s_axi_bvalid;
  wire [31:0]ext_axis_awg_tuning_v1_10_s_axi_rdata;
  wire ext_axis_awg_tuning_v1_10_s_axi_rready;
  wire [1:0]ext_axis_awg_tuning_v1_10_s_axi_rresp;
  wire ext_axis_awg_tuning_v1_10_s_axi_rvalid;
  wire [31:0]ext_axis_awg_tuning_v1_10_s_axi_wdata;
  wire ext_axis_awg_tuning_v1_10_s_axi_wready;
  wire [3:0]ext_axis_awg_tuning_v1_10_s_axi_wstrb;
  wire ext_axis_awg_tuning_v1_10_s_axi_wvalid;
  wire [5:0]ext_axis_awg_tuning_v1_11_s_axi_araddr;
  wire [2:0]ext_axis_awg_tuning_v1_11_s_axi_arprot;
  wire ext_axis_awg_tuning_v1_11_s_axi_arready;
  wire ext_axis_awg_tuning_v1_11_s_axi_arvalid;
  wire [5:0]ext_axis_awg_tuning_v1_11_s_axi_awaddr;
  wire [2:0]ext_axis_awg_tuning_v1_11_s_axi_awprot;
  wire ext_axis_awg_tuning_v1_11_s_axi_awready;
  wire ext_axis_awg_tuning_v1_11_s_axi_awvalid;
  wire ext_axis_awg_tuning_v1_11_s_axi_bready;
  wire [1:0]ext_axis_awg_tuning_v1_11_s_axi_bresp;
  wire ext_axis_awg_tuning_v1_11_s_axi_bvalid;
  wire [31:0]ext_axis_awg_tuning_v1_11_s_axi_rdata;
  wire ext_axis_awg_tuning_v1_11_s_axi_rready;
  wire [1:0]ext_axis_awg_tuning_v1_11_s_axi_rresp;
  wire ext_axis_awg_tuning_v1_11_s_axi_rvalid;
  wire [31:0]ext_axis_awg_tuning_v1_11_s_axi_wdata;
  wire ext_axis_awg_tuning_v1_11_s_axi_wready;
  wire [3:0]ext_axis_awg_tuning_v1_11_s_axi_wstrb;
  wire ext_axis_awg_tuning_v1_11_s_axi_wvalid;
  wire [5:0]ext_axis_awg_tuning_v1_4_s_axi_araddr;
  wire [2:0]ext_axis_awg_tuning_v1_4_s_axi_arprot;
  wire ext_axis_awg_tuning_v1_4_s_axi_arready;
  wire ext_axis_awg_tuning_v1_4_s_axi_arvalid;
  wire [5:0]ext_axis_awg_tuning_v1_4_s_axi_awaddr;
  wire [2:0]ext_axis_awg_tuning_v1_4_s_axi_awprot;
  wire ext_axis_awg_tuning_v1_4_s_axi_awready;
  wire ext_axis_awg_tuning_v1_4_s_axi_awvalid;
  wire ext_axis_awg_tuning_v1_4_s_axi_bready;
  wire [1:0]ext_axis_awg_tuning_v1_4_s_axi_bresp;
  wire ext_axis_awg_tuning_v1_4_s_axi_bvalid;
  wire [31:0]ext_axis_awg_tuning_v1_4_s_axi_rdata;
  wire ext_axis_awg_tuning_v1_4_s_axi_rready;
  wire [1:0]ext_axis_awg_tuning_v1_4_s_axi_rresp;
  wire ext_axis_awg_tuning_v1_4_s_axi_rvalid;
  wire [31:0]ext_axis_awg_tuning_v1_4_s_axi_wdata;
  wire ext_axis_awg_tuning_v1_4_s_axi_wready;
  wire [3:0]ext_axis_awg_tuning_v1_4_s_axi_wstrb;
  wire ext_axis_awg_tuning_v1_4_s_axi_wvalid;
  wire [5:0]ext_axis_awg_tuning_v1_5_s_axi_araddr;
  wire [2:0]ext_axis_awg_tuning_v1_5_s_axi_arprot;
  wire ext_axis_awg_tuning_v1_5_s_axi_arready;
  wire ext_axis_awg_tuning_v1_5_s_axi_arvalid;
  wire [5:0]ext_axis_awg_tuning_v1_5_s_axi_awaddr;
  wire [2:0]ext_axis_awg_tuning_v1_5_s_axi_awprot;
  wire ext_axis_awg_tuning_v1_5_s_axi_awready;
  wire ext_axis_awg_tuning_v1_5_s_axi_awvalid;
  wire ext_axis_awg_tuning_v1_5_s_axi_bready;
  wire [1:0]ext_axis_awg_tuning_v1_5_s_axi_bresp;
  wire ext_axis_awg_tuning_v1_5_s_axi_bvalid;
  wire [31:0]ext_axis_awg_tuning_v1_5_s_axi_rdata;
  wire ext_axis_awg_tuning_v1_5_s_axi_rready;
  wire [1:0]ext_axis_awg_tuning_v1_5_s_axi_rresp;
  wire ext_axis_awg_tuning_v1_5_s_axi_rvalid;
  wire [31:0]ext_axis_awg_tuning_v1_5_s_axi_wdata;
  wire ext_axis_awg_tuning_v1_5_s_axi_wready;
  wire [3:0]ext_axis_awg_tuning_v1_5_s_axi_wstrb;
  wire ext_axis_awg_tuning_v1_5_s_axi_wvalid;
  wire [5:0]ext_axis_awg_tuning_v1_6_s_axi_araddr;
  wire [2:0]ext_axis_awg_tuning_v1_6_s_axi_arprot;
  wire ext_axis_awg_tuning_v1_6_s_axi_arready;
  wire ext_axis_awg_tuning_v1_6_s_axi_arvalid;
  wire [5:0]ext_axis_awg_tuning_v1_6_s_axi_awaddr;
  wire [2:0]ext_axis_awg_tuning_v1_6_s_axi_awprot;
  wire ext_axis_awg_tuning_v1_6_s_axi_awready;
  wire ext_axis_awg_tuning_v1_6_s_axi_awvalid;
  wire ext_axis_awg_tuning_v1_6_s_axi_bready;
  wire [1:0]ext_axis_awg_tuning_v1_6_s_axi_bresp;
  wire ext_axis_awg_tuning_v1_6_s_axi_bvalid;
  wire [31:0]ext_axis_awg_tuning_v1_6_s_axi_rdata;
  wire ext_axis_awg_tuning_v1_6_s_axi_rready;
  wire [1:0]ext_axis_awg_tuning_v1_6_s_axi_rresp;
  wire ext_axis_awg_tuning_v1_6_s_axi_rvalid;
  wire [31:0]ext_axis_awg_tuning_v1_6_s_axi_wdata;
  wire ext_axis_awg_tuning_v1_6_s_axi_wready;
  wire [3:0]ext_axis_awg_tuning_v1_6_s_axi_wstrb;
  wire ext_axis_awg_tuning_v1_6_s_axi_wvalid;
  wire [5:0]ext_axis_awg_tuning_v1_8_s_axi_araddr;
  wire [2:0]ext_axis_awg_tuning_v1_8_s_axi_arprot;
  wire ext_axis_awg_tuning_v1_8_s_axi_arready;
  wire ext_axis_awg_tuning_v1_8_s_axi_arvalid;
  wire [5:0]ext_axis_awg_tuning_v1_8_s_axi_awaddr;
  wire [2:0]ext_axis_awg_tuning_v1_8_s_axi_awprot;
  wire ext_axis_awg_tuning_v1_8_s_axi_awready;
  wire ext_axis_awg_tuning_v1_8_s_axi_awvalid;
  wire ext_axis_awg_tuning_v1_8_s_axi_bready;
  wire [1:0]ext_axis_awg_tuning_v1_8_s_axi_bresp;
  wire ext_axis_awg_tuning_v1_8_s_axi_bvalid;
  wire [31:0]ext_axis_awg_tuning_v1_8_s_axi_rdata;
  wire ext_axis_awg_tuning_v1_8_s_axi_rready;
  wire [1:0]ext_axis_awg_tuning_v1_8_s_axi_rresp;
  wire ext_axis_awg_tuning_v1_8_s_axi_rvalid;
  wire [31:0]ext_axis_awg_tuning_v1_8_s_axi_wdata;
  wire ext_axis_awg_tuning_v1_8_s_axi_wready;
  wire [3:0]ext_axis_awg_tuning_v1_8_s_axi_wstrb;
  wire ext_axis_awg_tuning_v1_8_s_axi_wvalid;
  wire [5:0]ext_axis_awg_tuning_v1_9_s_axi_araddr;
  wire [2:0]ext_axis_awg_tuning_v1_9_s_axi_arprot;
  wire ext_axis_awg_tuning_v1_9_s_axi_arready;
  wire ext_axis_awg_tuning_v1_9_s_axi_arvalid;
  wire [5:0]ext_axis_awg_tuning_v1_9_s_axi_awaddr;
  wire [2:0]ext_axis_awg_tuning_v1_9_s_axi_awprot;
  wire ext_axis_awg_tuning_v1_9_s_axi_awready;
  wire ext_axis_awg_tuning_v1_9_s_axi_awvalid;
  wire ext_axis_awg_tuning_v1_9_s_axi_bready;
  wire [1:0]ext_axis_awg_tuning_v1_9_s_axi_bresp;
  wire ext_axis_awg_tuning_v1_9_s_axi_bvalid;
  wire [31:0]ext_axis_awg_tuning_v1_9_s_axi_rdata;
  wire ext_axis_awg_tuning_v1_9_s_axi_rready;
  wire [1:0]ext_axis_awg_tuning_v1_9_s_axi_rresp;
  wire ext_axis_awg_tuning_v1_9_s_axi_rvalid;
  wire [31:0]ext_axis_awg_tuning_v1_9_s_axi_wdata;
  wire ext_axis_awg_tuning_v1_9_s_axi_wready;
  wire [3:0]ext_axis_awg_tuning_v1_9_s_axi_wstrb;
  wire ext_axis_awg_tuning_v1_9_s_axi_wvalid;
  wire [127:0]ext_axis_dyn_readout_v1_0_s1_axis_tdata;
  wire ext_axis_dyn_readout_v1_0_s1_axis_tready;
  wire ext_axis_dyn_readout_v1_0_s1_axis_tvalid;
  wire [127:0]ext_axis_dyn_readout_v1_1_s1_axis_tdata;
  wire ext_axis_dyn_readout_v1_1_s1_axis_tready;
  wire ext_axis_dyn_readout_v1_1_s1_axis_tvalid;
  wire [127:0]ext_axis_dyn_readout_v1_2_s1_axis_tdata;
  wire ext_axis_dyn_readout_v1_2_s1_axis_tready;
  wire ext_axis_dyn_readout_v1_2_s1_axis_tvalid;
  wire [127:0]ext_axis_dyn_readout_v1_3_s1_axis_tdata;
  wire ext_axis_dyn_readout_v1_3_s1_axis_tready;
  wire ext_axis_dyn_readout_v1_3_s1_axis_tvalid;
  wire [255:0]ext_axis_register_slice_0_m_axis_tdata;
  wire ext_axis_register_slice_0_m_axis_tready;
  wire ext_axis_register_slice_0_m_axis_tvalid;
  wire [255:0]ext_axis_register_slice_10_m_axis_tdata;
  wire ext_axis_register_slice_10_m_axis_tready;
  wire ext_axis_register_slice_10_m_axis_tvalid;
  wire [255:0]ext_axis_register_slice_11_m_axis_tdata;
  wire ext_axis_register_slice_11_m_axis_tready;
  wire ext_axis_register_slice_11_m_axis_tvalid;
  wire [255:0]ext_axis_register_slice_12_m_axis_tdata;
  wire ext_axis_register_slice_12_m_axis_tready;
  wire ext_axis_register_slice_12_m_axis_tvalid;
  wire [255:0]ext_axis_register_slice_13_m_axis_tdata;
  wire ext_axis_register_slice_13_m_axis_tready;
  wire ext_axis_register_slice_13_m_axis_tvalid;
  wire [255:0]ext_axis_register_slice_14_m_axis_tdata;
  wire ext_axis_register_slice_14_m_axis_tready;
  wire ext_axis_register_slice_14_m_axis_tvalid;
  wire [255:0]ext_axis_register_slice_15_m_axis_tdata;
  wire ext_axis_register_slice_15_m_axis_tready;
  wire ext_axis_register_slice_15_m_axis_tvalid;
  wire [255:0]ext_axis_register_slice_16_m_axis_tdata;
  wire ext_axis_register_slice_16_m_axis_tready;
  wire ext_axis_register_slice_16_m_axis_tvalid;
  wire [255:0]ext_axis_register_slice_1_m_axis_tdata;
  wire ext_axis_register_slice_1_m_axis_tready;
  wire ext_axis_register_slice_1_m_axis_tvalid;
  wire [255:0]ext_axis_register_slice_2_m_axis_tdata;
  wire ext_axis_register_slice_2_m_axis_tready;
  wire ext_axis_register_slice_2_m_axis_tvalid;
  wire [255:0]ext_axis_register_slice_3_m_axis_tdata;
  wire ext_axis_register_slice_3_m_axis_tready;
  wire ext_axis_register_slice_3_m_axis_tvalid;
  wire [255:0]ext_axis_register_slice_8_m_axis_tdata;
  wire ext_axis_register_slice_8_m_axis_tready;
  wire ext_axis_register_slice_8_m_axis_tvalid;
  wire [5:0]ext_axis_signal_gen_v6_0_s_axi_araddr;
  wire [2:0]ext_axis_signal_gen_v6_0_s_axi_arprot;
  wire ext_axis_signal_gen_v6_0_s_axi_arready;
  wire ext_axis_signal_gen_v6_0_s_axi_arvalid;
  wire [5:0]ext_axis_signal_gen_v6_0_s_axi_awaddr;
  wire [2:0]ext_axis_signal_gen_v6_0_s_axi_awprot;
  wire ext_axis_signal_gen_v6_0_s_axi_awready;
  wire ext_axis_signal_gen_v6_0_s_axi_awvalid;
  wire ext_axis_signal_gen_v6_0_s_axi_bready;
  wire [1:0]ext_axis_signal_gen_v6_0_s_axi_bresp;
  wire ext_axis_signal_gen_v6_0_s_axi_bvalid;
  wire [31:0]ext_axis_signal_gen_v6_0_s_axi_rdata;
  wire ext_axis_signal_gen_v6_0_s_axi_rready;
  wire [1:0]ext_axis_signal_gen_v6_0_s_axi_rresp;
  wire ext_axis_signal_gen_v6_0_s_axi_rvalid;
  wire [31:0]ext_axis_signal_gen_v6_0_s_axi_wdata;
  wire ext_axis_signal_gen_v6_0_s_axi_wready;
  wire [3:0]ext_axis_signal_gen_v6_0_s_axi_wstrb;
  wire ext_axis_signal_gen_v6_0_s_axi_wvalid;
  wire [5:0]ext_axis_signal_gen_v6_1_s_axi_araddr;
  wire [2:0]ext_axis_signal_gen_v6_1_s_axi_arprot;
  wire ext_axis_signal_gen_v6_1_s_axi_arready;
  wire ext_axis_signal_gen_v6_1_s_axi_arvalid;
  wire [5:0]ext_axis_signal_gen_v6_1_s_axi_awaddr;
  wire [2:0]ext_axis_signal_gen_v6_1_s_axi_awprot;
  wire ext_axis_signal_gen_v6_1_s_axi_awready;
  wire ext_axis_signal_gen_v6_1_s_axi_awvalid;
  wire ext_axis_signal_gen_v6_1_s_axi_bready;
  wire [1:0]ext_axis_signal_gen_v6_1_s_axi_bresp;
  wire ext_axis_signal_gen_v6_1_s_axi_bvalid;
  wire [31:0]ext_axis_signal_gen_v6_1_s_axi_rdata;
  wire ext_axis_signal_gen_v6_1_s_axi_rready;
  wire [1:0]ext_axis_signal_gen_v6_1_s_axi_rresp;
  wire ext_axis_signal_gen_v6_1_s_axi_rvalid;
  wire [31:0]ext_axis_signal_gen_v6_1_s_axi_wdata;
  wire ext_axis_signal_gen_v6_1_s_axi_wready;
  wire [3:0]ext_axis_signal_gen_v6_1_s_axi_wstrb;
  wire ext_axis_signal_gen_v6_1_s_axi_wvalid;
  wire [5:0]ext_axis_signal_gen_v6_2_s_axi_araddr;
  wire [2:0]ext_axis_signal_gen_v6_2_s_axi_arprot;
  wire ext_axis_signal_gen_v6_2_s_axi_arready;
  wire ext_axis_signal_gen_v6_2_s_axi_arvalid;
  wire [5:0]ext_axis_signal_gen_v6_2_s_axi_awaddr;
  wire [2:0]ext_axis_signal_gen_v6_2_s_axi_awprot;
  wire ext_axis_signal_gen_v6_2_s_axi_awready;
  wire ext_axis_signal_gen_v6_2_s_axi_awvalid;
  wire ext_axis_signal_gen_v6_2_s_axi_bready;
  wire [1:0]ext_axis_signal_gen_v6_2_s_axi_bresp;
  wire ext_axis_signal_gen_v6_2_s_axi_bvalid;
  wire [31:0]ext_axis_signal_gen_v6_2_s_axi_rdata;
  wire ext_axis_signal_gen_v6_2_s_axi_rready;
  wire [1:0]ext_axis_signal_gen_v6_2_s_axi_rresp;
  wire ext_axis_signal_gen_v6_2_s_axi_rvalid;
  wire [31:0]ext_axis_signal_gen_v6_2_s_axi_wdata;
  wire ext_axis_signal_gen_v6_2_s_axi_wready;
  wire [3:0]ext_axis_signal_gen_v6_2_s_axi_wstrb;
  wire ext_axis_signal_gen_v6_2_s_axi_wvalid;
  wire [5:0]ext_axis_signal_gen_v6_3_s_axi_araddr;
  wire [2:0]ext_axis_signal_gen_v6_3_s_axi_arprot;
  wire ext_axis_signal_gen_v6_3_s_axi_arready;
  wire ext_axis_signal_gen_v6_3_s_axi_arvalid;
  wire [5:0]ext_axis_signal_gen_v6_3_s_axi_awaddr;
  wire [2:0]ext_axis_signal_gen_v6_3_s_axi_awprot;
  wire ext_axis_signal_gen_v6_3_s_axi_awready;
  wire ext_axis_signal_gen_v6_3_s_axi_awvalid;
  wire ext_axis_signal_gen_v6_3_s_axi_bready;
  wire [1:0]ext_axis_signal_gen_v6_3_s_axi_bresp;
  wire ext_axis_signal_gen_v6_3_s_axi_bvalid;
  wire [31:0]ext_axis_signal_gen_v6_3_s_axi_rdata;
  wire ext_axis_signal_gen_v6_3_s_axi_rready;
  wire [1:0]ext_axis_signal_gen_v6_3_s_axi_rresp;
  wire ext_axis_signal_gen_v6_3_s_axi_rvalid;
  wire [31:0]ext_axis_signal_gen_v6_3_s_axi_wdata;
  wire ext_axis_signal_gen_v6_3_s_axi_wready;
  wire [3:0]ext_axis_signal_gen_v6_3_s_axi_wstrb;
  wire ext_axis_signal_gen_v6_3_s_axi_wvalid;
  wire [5:0]ext_axis_square_pulse_v1_0_s_axi_araddr;
  wire [2:0]ext_axis_square_pulse_v1_0_s_axi_arprot;
  wire ext_axis_square_pulse_v1_0_s_axi_arready;
  wire ext_axis_square_pulse_v1_0_s_axi_arvalid;
  wire [5:0]ext_axis_square_pulse_v1_0_s_axi_awaddr;
  wire [2:0]ext_axis_square_pulse_v1_0_s_axi_awprot;
  wire ext_axis_square_pulse_v1_0_s_axi_awready;
  wire ext_axis_square_pulse_v1_0_s_axi_awvalid;
  wire ext_axis_square_pulse_v1_0_s_axi_bready;
  wire [1:0]ext_axis_square_pulse_v1_0_s_axi_bresp;
  wire ext_axis_square_pulse_v1_0_s_axi_bvalid;
  wire [31:0]ext_axis_square_pulse_v1_0_s_axi_rdata;
  wire ext_axis_square_pulse_v1_0_s_axi_rready;
  wire [1:0]ext_axis_square_pulse_v1_0_s_axi_rresp;
  wire ext_axis_square_pulse_v1_0_s_axi_rvalid;
  wire [31:0]ext_axis_square_pulse_v1_0_s_axi_wdata;
  wire ext_axis_square_pulse_v1_0_s_axi_wready;
  wire [3:0]ext_axis_square_pulse_v1_0_s_axi_wstrb;
  wire ext_axis_square_pulse_v1_0_s_axi_wvalid;
  wire [63:0]ext_axis_switch_avg_M00_AXIS_tdata;
  wire [0:0]ext_axis_switch_avg_M00_AXIS_tlast;
  wire [0:0]ext_axis_switch_avg_M00_AXIS_tready;
  wire [0:0]ext_axis_switch_avg_M00_AXIS_tvalid;
  wire [6:0]ext_axis_switch_avg_S_AXI_CTRL_araddr;
  wire ext_axis_switch_avg_S_AXI_CTRL_arready;
  wire ext_axis_switch_avg_S_AXI_CTRL_arvalid;
  wire [6:0]ext_axis_switch_avg_S_AXI_CTRL_awaddr;
  wire ext_axis_switch_avg_S_AXI_CTRL_awready;
  wire ext_axis_switch_avg_S_AXI_CTRL_awvalid;
  wire ext_axis_switch_avg_S_AXI_CTRL_bready;
  wire [1:0]ext_axis_switch_avg_S_AXI_CTRL_bresp;
  wire ext_axis_switch_avg_S_AXI_CTRL_bvalid;
  wire [31:0]ext_axis_switch_avg_S_AXI_CTRL_rdata;
  wire ext_axis_switch_avg_S_AXI_CTRL_rready;
  wire [1:0]ext_axis_switch_avg_S_AXI_CTRL_rresp;
  wire ext_axis_switch_avg_S_AXI_CTRL_rvalid;
  wire [31:0]ext_axis_switch_avg_S_AXI_CTRL_wdata;
  wire ext_axis_switch_avg_S_AXI_CTRL_wready;
  wire ext_axis_switch_avg_S_AXI_CTRL_wvalid;
  wire [31:0]ext_axis_switch_buf_M00_AXIS_tdata;
  wire [0:0]ext_axis_switch_buf_M00_AXIS_tlast;
  wire [0:0]ext_axis_switch_buf_M00_AXIS_tready;
  wire [0:0]ext_axis_switch_buf_M00_AXIS_tvalid;
  wire [6:0]ext_axis_switch_buf_S_AXI_CTRL_araddr;
  wire ext_axis_switch_buf_S_AXI_CTRL_arready;
  wire ext_axis_switch_buf_S_AXI_CTRL_arvalid;
  wire [6:0]ext_axis_switch_buf_S_AXI_CTRL_awaddr;
  wire ext_axis_switch_buf_S_AXI_CTRL_awready;
  wire ext_axis_switch_buf_S_AXI_CTRL_awvalid;
  wire ext_axis_switch_buf_S_AXI_CTRL_bready;
  wire [1:0]ext_axis_switch_buf_S_AXI_CTRL_bresp;
  wire ext_axis_switch_buf_S_AXI_CTRL_bvalid;
  wire [31:0]ext_axis_switch_buf_S_AXI_CTRL_rdata;
  wire ext_axis_switch_buf_S_AXI_CTRL_rready;
  wire [1:0]ext_axis_switch_buf_S_AXI_CTRL_rresp;
  wire ext_axis_switch_buf_S_AXI_CTRL_rvalid;
  wire [31:0]ext_axis_switch_buf_S_AXI_CTRL_wdata;
  wire ext_axis_switch_buf_S_AXI_CTRL_wready;
  wire ext_axis_switch_buf_S_AXI_CTRL_wvalid;
  wire [6:0]ext_axis_switch_ddr_S_AXI_CTRL_araddr;
  wire ext_axis_switch_ddr_S_AXI_CTRL_arready;
  wire ext_axis_switch_ddr_S_AXI_CTRL_arvalid;
  wire [6:0]ext_axis_switch_ddr_S_AXI_CTRL_awaddr;
  wire ext_axis_switch_ddr_S_AXI_CTRL_awready;
  wire ext_axis_switch_ddr_S_AXI_CTRL_awvalid;
  wire ext_axis_switch_ddr_S_AXI_CTRL_bready;
  wire [1:0]ext_axis_switch_ddr_S_AXI_CTRL_bresp;
  wire ext_axis_switch_ddr_S_AXI_CTRL_bvalid;
  wire [31:0]ext_axis_switch_ddr_S_AXI_CTRL_rdata;
  wire ext_axis_switch_ddr_S_AXI_CTRL_rready;
  wire [1:0]ext_axis_switch_ddr_S_AXI_CTRL_rresp;
  wire ext_axis_switch_ddr_S_AXI_CTRL_rvalid;
  wire [31:0]ext_axis_switch_ddr_S_AXI_CTRL_wdata;
  wire ext_axis_switch_ddr_S_AXI_CTRL_wready;
  wire ext_axis_switch_ddr_S_AXI_CTRL_wvalid;
  wire [31:0]ext_axis_switch_gen_M04_AXIS_tdata;
  wire [3:0]ext_axis_switch_gen_M04_AXIS_tkeep;
  wire [0:0]ext_axis_switch_gen_M04_AXIS_tlast;
  wire [0:0]ext_axis_switch_gen_M04_AXIS_tready;
  wire [0:0]ext_axis_switch_gen_M04_AXIS_tvalid;
  wire [31:0]ext_axis_switch_gen_M05_AXIS_tdata;
  wire [3:0]ext_axis_switch_gen_M05_AXIS_tkeep;
  wire [0:0]ext_axis_switch_gen_M05_AXIS_tlast;
  wire [0:0]ext_axis_switch_gen_M05_AXIS_tready;
  wire [0:0]ext_axis_switch_gen_M05_AXIS_tvalid;
  wire [31:0]ext_axis_switch_gen_M06_AXIS_tdata;
  wire [3:0]ext_axis_switch_gen_M06_AXIS_tkeep;
  wire [0:0]ext_axis_switch_gen_M06_AXIS_tlast;
  wire [0:0]ext_axis_switch_gen_M06_AXIS_tready;
  wire [0:0]ext_axis_switch_gen_M06_AXIS_tvalid;
  wire [31:0]ext_axis_switch_gen_M07_AXIS_tdata;
  wire [3:0]ext_axis_switch_gen_M07_AXIS_tkeep;
  wire [0:0]ext_axis_switch_gen_M07_AXIS_tlast;
  wire [0:0]ext_axis_switch_gen_M07_AXIS_tready;
  wire [0:0]ext_axis_switch_gen_M07_AXIS_tvalid;
  wire [31:0]ext_axis_switch_gen_M08_AXIS_tdata;
  wire [3:0]ext_axis_switch_gen_M08_AXIS_tkeep;
  wire [0:0]ext_axis_switch_gen_M08_AXIS_tlast;
  wire [0:0]ext_axis_switch_gen_M08_AXIS_tready;
  wire [0:0]ext_axis_switch_gen_M08_AXIS_tvalid;
  wire [31:0]ext_axis_switch_gen_M09_AXIS_tdata;
  wire [3:0]ext_axis_switch_gen_M09_AXIS_tkeep;
  wire [0:0]ext_axis_switch_gen_M09_AXIS_tlast;
  wire [0:0]ext_axis_switch_gen_M09_AXIS_tready;
  wire [0:0]ext_axis_switch_gen_M09_AXIS_tvalid;
  wire [31:0]ext_axis_switch_gen_M10_AXIS_tdata;
  wire [3:0]ext_axis_switch_gen_M10_AXIS_tkeep;
  wire [0:0]ext_axis_switch_gen_M10_AXIS_tlast;
  wire [0:0]ext_axis_switch_gen_M10_AXIS_tready;
  wire [0:0]ext_axis_switch_gen_M10_AXIS_tvalid;
  wire [31:0]ext_axis_switch_gen_M11_AXIS_tdata;
  wire [3:0]ext_axis_switch_gen_M11_AXIS_tkeep;
  wire [0:0]ext_axis_switch_gen_M11_AXIS_tlast;
  wire [0:0]ext_axis_switch_gen_M11_AXIS_tready;
  wire [0:0]ext_axis_switch_gen_M11_AXIS_tvalid;
  wire [31:0]ext_axis_switch_gen_S00_AXIS_tdata;
  wire [3:0]ext_axis_switch_gen_S00_AXIS_tkeep;
  wire [0:0]ext_axis_switch_gen_S00_AXIS_tlast;
  wire [0:0]ext_axis_switch_gen_S00_AXIS_tready;
  wire [0:0]ext_axis_switch_gen_S00_AXIS_tvalid;
  wire [6:0]ext_axis_switch_gen_S_AXI_CTRL_araddr;
  wire ext_axis_switch_gen_S_AXI_CTRL_arready;
  wire ext_axis_switch_gen_S_AXI_CTRL_arvalid;
  wire [6:0]ext_axis_switch_gen_S_AXI_CTRL_awaddr;
  wire ext_axis_switch_gen_S_AXI_CTRL_awready;
  wire ext_axis_switch_gen_S_AXI_CTRL_awvalid;
  wire ext_axis_switch_gen_S_AXI_CTRL_bready;
  wire [1:0]ext_axis_switch_gen_S_AXI_CTRL_bresp;
  wire ext_axis_switch_gen_S_AXI_CTRL_bvalid;
  wire [31:0]ext_axis_switch_gen_S_AXI_CTRL_rdata;
  wire ext_axis_switch_gen_S_AXI_CTRL_rready;
  wire [1:0]ext_axis_switch_gen_S_AXI_CTRL_rresp;
  wire ext_axis_switch_gen_S_AXI_CTRL_rvalid;
  wire [31:0]ext_axis_switch_gen_S_AXI_CTRL_wdata;
  wire ext_axis_switch_gen_S_AXI_CTRL_wready;
  wire ext_axis_switch_gen_S_AXI_CTRL_wvalid;
  wire [6:0]ext_axis_switch_mr_S_AXI_CTRL_araddr;
  wire ext_axis_switch_mr_S_AXI_CTRL_arready;
  wire ext_axis_switch_mr_S_AXI_CTRL_arvalid;
  wire [6:0]ext_axis_switch_mr_S_AXI_CTRL_awaddr;
  wire ext_axis_switch_mr_S_AXI_CTRL_awready;
  wire ext_axis_switch_mr_S_AXI_CTRL_awvalid;
  wire ext_axis_switch_mr_S_AXI_CTRL_bready;
  wire [1:0]ext_axis_switch_mr_S_AXI_CTRL_bresp;
  wire ext_axis_switch_mr_S_AXI_CTRL_bvalid;
  wire [31:0]ext_axis_switch_mr_S_AXI_CTRL_rdata;
  wire ext_axis_switch_mr_S_AXI_CTRL_rready;
  wire [1:0]ext_axis_switch_mr_S_AXI_CTRL_rresp;
  wire ext_axis_switch_mr_S_AXI_CTRL_rvalid;
  wire [31:0]ext_axis_switch_mr_S_AXI_CTRL_wdata;
  wire ext_axis_switch_mr_S_AXI_CTRL_wready;
  wire ext_axis_switch_mr_S_AXI_CTRL_wvalid;
  wire [31:0]ext_axis_tproc64x32_x8_0_m0_axis_tdata;
  wire ext_axis_tproc64x32_x8_0_m0_axis_tlast;
  wire ext_axis_tproc64x32_x8_0_m0_axis_tready;
  wire ext_axis_tproc64x32_x8_0_m0_axis_tvalid;
  wire [19:0]ext_axis_tproc64x32_x8_0_pmem_addr;
  wire [63:0]ext_axis_tproc64x32_x8_0_pmem_do;
  wire [31:0]ext_axis_tproc64x32_x8_0_s0_axis_tdata;
  wire ext_axis_tproc64x32_x8_0_s0_axis_tlast;
  wire ext_axis_tproc64x32_x8_0_s0_axis_tready;
  wire ext_axis_tproc64x32_x8_0_s0_axis_tvalid;
  wire [31:0]ext_axis_tproc64x32_x8_0_s_axi_araddr;
  wire [2:0]ext_axis_tproc64x32_x8_0_s_axi_arprot;
  wire ext_axis_tproc64x32_x8_0_s_axi_arready;
  wire ext_axis_tproc64x32_x8_0_s_axi_arvalid;
  wire [31:0]ext_axis_tproc64x32_x8_0_s_axi_awaddr;
  wire [2:0]ext_axis_tproc64x32_x8_0_s_axi_awprot;
  wire ext_axis_tproc64x32_x8_0_s_axi_awready;
  wire ext_axis_tproc64x32_x8_0_s_axi_awvalid;
  wire ext_axis_tproc64x32_x8_0_s_axi_bready;
  wire [1:0]ext_axis_tproc64x32_x8_0_s_axi_bresp;
  wire ext_axis_tproc64x32_x8_0_s_axi_bvalid;
  wire [31:0]ext_axis_tproc64x32_x8_0_s_axi_rdata;
  wire ext_axis_tproc64x32_x8_0_s_axi_rready;
  wire [1:0]ext_axis_tproc64x32_x8_0_s_axi_rresp;
  wire ext_axis_tproc64x32_x8_0_s_axi_rvalid;
  wire [31:0]ext_axis_tproc64x32_x8_0_s_axi_wdata;
  wire ext_axis_tproc64x32_x8_0_s_axi_wready;
  wire [3:0]ext_axis_tproc64x32_x8_0_s_axi_wstrb;
  wire ext_axis_tproc64x32_x8_0_s_axi_wvalid;
  wire ext_axis_tproc64x32_x8_0_start;
  wire ext_c_shift_ram_0_D;
  wire [0:0]ext_c_shift_ram_0_Q;
  wire [31:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awaddr;
  wire [1:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awburst;
  wire [3:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awcache;
  wire [0:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awid;
  wire [7:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlen;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlock;
  wire [2:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awprot;
  wire [3:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awqos;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awready;
  wire [3:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awregion;
  wire [2:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awsize;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awvalid;
  wire [0:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bid;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bready;
  wire [1:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bresp;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bvalid;
  wire [255:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wdata;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wlast;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wready;
  wire [31:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wstrb;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wvalid;
  wire [7:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_araddr;
  wire [2:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arprot;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arready;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arvalid;
  wire [7:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awaddr;
  wire [2:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awprot;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awready;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awvalid;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bready;
  wire [1:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bresp;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bvalid;
  wire [31:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rdata;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rready;
  wire [1:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rresp;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rvalid;
  wire [31:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wdata;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wready;
  wire [3:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wstrb;
  wire ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wvalid;
  wire ext_ddr4_axis_fir_decim_300to1_v2_0_capture_trigger;
  wire [31:0]ext_mr_buffer_et_0_m00_axis_tdata;
  wire ext_mr_buffer_et_0_m00_axis_tlast;
  wire ext_mr_buffer_et_0_m00_axis_tready;
  wire [3:0]ext_mr_buffer_et_0_m00_axis_tstrb;
  wire ext_mr_buffer_et_0_m00_axis_tvalid;
  wire [5:0]ext_mr_buffer_et_0_s00_axi_araddr;
  wire [2:0]ext_mr_buffer_et_0_s00_axi_arprot;
  wire ext_mr_buffer_et_0_s00_axi_arready;
  wire ext_mr_buffer_et_0_s00_axi_arvalid;
  wire [5:0]ext_mr_buffer_et_0_s00_axi_awaddr;
  wire [2:0]ext_mr_buffer_et_0_s00_axi_awprot;
  wire ext_mr_buffer_et_0_s00_axi_awready;
  wire ext_mr_buffer_et_0_s00_axi_awvalid;
  wire ext_mr_buffer_et_0_s00_axi_bready;
  wire [1:0]ext_mr_buffer_et_0_s00_axi_bresp;
  wire ext_mr_buffer_et_0_s00_axi_bvalid;
  wire [31:0]ext_mr_buffer_et_0_s00_axi_rdata;
  wire ext_mr_buffer_et_0_s00_axi_rready;
  wire [1:0]ext_mr_buffer_et_0_s00_axi_rresp;
  wire ext_mr_buffer_et_0_s00_axi_rvalid;
  wire [31:0]ext_mr_buffer_et_0_s00_axi_wdata;
  wire ext_mr_buffer_et_0_s00_axi_wready;
  wire [3:0]ext_mr_buffer_et_0_s00_axi_wstrb;
  wire ext_mr_buffer_et_0_s00_axi_wvalid;
  wire ext_qick_vec2bit_0_dout0;
  wire ext_qick_vec2bit_0_dout1;
  wire ext_qick_vec2bit_0_dout2;
  wire ext_qick_vec2bit_0_dout3;
  wire ext_qick_vec2bit_0_dout4;
  wire ext_qick_vec2bit_0_dout5;
  wire ext_qick_vec2bit_0_dout6;
  wire [63:0]ext_xlconstant_0_dout;
  wire [0:0]ext_xlconstant_1_dout;
  wire [0:0]ext_xlconstant_2_dout;
  wire [7:0]ext_xlconstant_3_dout;
  wire [11:0]ext_xlconstant_4_dout;
  wire resetn;

  rc_bd sim_bd_i
       (.clk_300000000(clk_300000000),
        .clk_333250000(clk_333250000),
        .clk_99999985(clk_99999985),
        .ext_axis_avg_buffer_0_s_axi_araddr(ext_axis_avg_buffer_0_s_axi_araddr),
        .ext_axis_avg_buffer_0_s_axi_arprot(ext_axis_avg_buffer_0_s_axi_arprot),
        .ext_axis_avg_buffer_0_s_axi_arready(ext_axis_avg_buffer_0_s_axi_arready),
        .ext_axis_avg_buffer_0_s_axi_arvalid(ext_axis_avg_buffer_0_s_axi_arvalid),
        .ext_axis_avg_buffer_0_s_axi_awaddr(ext_axis_avg_buffer_0_s_axi_awaddr),
        .ext_axis_avg_buffer_0_s_axi_awprot(ext_axis_avg_buffer_0_s_axi_awprot),
        .ext_axis_avg_buffer_0_s_axi_awready(ext_axis_avg_buffer_0_s_axi_awready),
        .ext_axis_avg_buffer_0_s_axi_awvalid(ext_axis_avg_buffer_0_s_axi_awvalid),
        .ext_axis_avg_buffer_0_s_axi_bready(ext_axis_avg_buffer_0_s_axi_bready),
        .ext_axis_avg_buffer_0_s_axi_bresp(ext_axis_avg_buffer_0_s_axi_bresp),
        .ext_axis_avg_buffer_0_s_axi_bvalid(ext_axis_avg_buffer_0_s_axi_bvalid),
        .ext_axis_avg_buffer_0_s_axi_rdata(ext_axis_avg_buffer_0_s_axi_rdata),
        .ext_axis_avg_buffer_0_s_axi_rready(ext_axis_avg_buffer_0_s_axi_rready),
        .ext_axis_avg_buffer_0_s_axi_rresp(ext_axis_avg_buffer_0_s_axi_rresp),
        .ext_axis_avg_buffer_0_s_axi_rvalid(ext_axis_avg_buffer_0_s_axi_rvalid),
        .ext_axis_avg_buffer_0_s_axi_wdata(ext_axis_avg_buffer_0_s_axi_wdata),
        .ext_axis_avg_buffer_0_s_axi_wready(ext_axis_avg_buffer_0_s_axi_wready),
        .ext_axis_avg_buffer_0_s_axi_wstrb(ext_axis_avg_buffer_0_s_axi_wstrb),
        .ext_axis_avg_buffer_0_s_axi_wvalid(ext_axis_avg_buffer_0_s_axi_wvalid),
        .ext_axis_avg_buffer_1_s_axi_araddr(ext_axis_avg_buffer_1_s_axi_araddr),
        .ext_axis_avg_buffer_1_s_axi_arprot(ext_axis_avg_buffer_1_s_axi_arprot),
        .ext_axis_avg_buffer_1_s_axi_arready(ext_axis_avg_buffer_1_s_axi_arready),
        .ext_axis_avg_buffer_1_s_axi_arvalid(ext_axis_avg_buffer_1_s_axi_arvalid),
        .ext_axis_avg_buffer_1_s_axi_awaddr(ext_axis_avg_buffer_1_s_axi_awaddr),
        .ext_axis_avg_buffer_1_s_axi_awprot(ext_axis_avg_buffer_1_s_axi_awprot),
        .ext_axis_avg_buffer_1_s_axi_awready(ext_axis_avg_buffer_1_s_axi_awready),
        .ext_axis_avg_buffer_1_s_axi_awvalid(ext_axis_avg_buffer_1_s_axi_awvalid),
        .ext_axis_avg_buffer_1_s_axi_bready(ext_axis_avg_buffer_1_s_axi_bready),
        .ext_axis_avg_buffer_1_s_axi_bresp(ext_axis_avg_buffer_1_s_axi_bresp),
        .ext_axis_avg_buffer_1_s_axi_bvalid(ext_axis_avg_buffer_1_s_axi_bvalid),
        .ext_axis_avg_buffer_1_s_axi_rdata(ext_axis_avg_buffer_1_s_axi_rdata),
        .ext_axis_avg_buffer_1_s_axi_rready(ext_axis_avg_buffer_1_s_axi_rready),
        .ext_axis_avg_buffer_1_s_axi_rresp(ext_axis_avg_buffer_1_s_axi_rresp),
        .ext_axis_avg_buffer_1_s_axi_rvalid(ext_axis_avg_buffer_1_s_axi_rvalid),
        .ext_axis_avg_buffer_1_s_axi_wdata(ext_axis_avg_buffer_1_s_axi_wdata),
        .ext_axis_avg_buffer_1_s_axi_wready(ext_axis_avg_buffer_1_s_axi_wready),
        .ext_axis_avg_buffer_1_s_axi_wstrb(ext_axis_avg_buffer_1_s_axi_wstrb),
        .ext_axis_avg_buffer_1_s_axi_wvalid(ext_axis_avg_buffer_1_s_axi_wvalid),
        .ext_axis_avg_buffer_2_s_axi_araddr(ext_axis_avg_buffer_2_s_axi_araddr),
        .ext_axis_avg_buffer_2_s_axi_arprot(ext_axis_avg_buffer_2_s_axi_arprot),
        .ext_axis_avg_buffer_2_s_axi_arready(ext_axis_avg_buffer_2_s_axi_arready),
        .ext_axis_avg_buffer_2_s_axi_arvalid(ext_axis_avg_buffer_2_s_axi_arvalid),
        .ext_axis_avg_buffer_2_s_axi_awaddr(ext_axis_avg_buffer_2_s_axi_awaddr),
        .ext_axis_avg_buffer_2_s_axi_awprot(ext_axis_avg_buffer_2_s_axi_awprot),
        .ext_axis_avg_buffer_2_s_axi_awready(ext_axis_avg_buffer_2_s_axi_awready),
        .ext_axis_avg_buffer_2_s_axi_awvalid(ext_axis_avg_buffer_2_s_axi_awvalid),
        .ext_axis_avg_buffer_2_s_axi_bready(ext_axis_avg_buffer_2_s_axi_bready),
        .ext_axis_avg_buffer_2_s_axi_bresp(ext_axis_avg_buffer_2_s_axi_bresp),
        .ext_axis_avg_buffer_2_s_axi_bvalid(ext_axis_avg_buffer_2_s_axi_bvalid),
        .ext_axis_avg_buffer_2_s_axi_rdata(ext_axis_avg_buffer_2_s_axi_rdata),
        .ext_axis_avg_buffer_2_s_axi_rready(ext_axis_avg_buffer_2_s_axi_rready),
        .ext_axis_avg_buffer_2_s_axi_rresp(ext_axis_avg_buffer_2_s_axi_rresp),
        .ext_axis_avg_buffer_2_s_axi_rvalid(ext_axis_avg_buffer_2_s_axi_rvalid),
        .ext_axis_avg_buffer_2_s_axi_wdata(ext_axis_avg_buffer_2_s_axi_wdata),
        .ext_axis_avg_buffer_2_s_axi_wready(ext_axis_avg_buffer_2_s_axi_wready),
        .ext_axis_avg_buffer_2_s_axi_wstrb(ext_axis_avg_buffer_2_s_axi_wstrb),
        .ext_axis_avg_buffer_2_s_axi_wvalid(ext_axis_avg_buffer_2_s_axi_wvalid),
        .ext_axis_avg_buffer_3_s_axi_araddr(ext_axis_avg_buffer_3_s_axi_araddr),
        .ext_axis_avg_buffer_3_s_axi_arprot(ext_axis_avg_buffer_3_s_axi_arprot),
        .ext_axis_avg_buffer_3_s_axi_arready(ext_axis_avg_buffer_3_s_axi_arready),
        .ext_axis_avg_buffer_3_s_axi_arvalid(ext_axis_avg_buffer_3_s_axi_arvalid),
        .ext_axis_avg_buffer_3_s_axi_awaddr(ext_axis_avg_buffer_3_s_axi_awaddr),
        .ext_axis_avg_buffer_3_s_axi_awprot(ext_axis_avg_buffer_3_s_axi_awprot),
        .ext_axis_avg_buffer_3_s_axi_awready(ext_axis_avg_buffer_3_s_axi_awready),
        .ext_axis_avg_buffer_3_s_axi_awvalid(ext_axis_avg_buffer_3_s_axi_awvalid),
        .ext_axis_avg_buffer_3_s_axi_bready(ext_axis_avg_buffer_3_s_axi_bready),
        .ext_axis_avg_buffer_3_s_axi_bresp(ext_axis_avg_buffer_3_s_axi_bresp),
        .ext_axis_avg_buffer_3_s_axi_bvalid(ext_axis_avg_buffer_3_s_axi_bvalid),
        .ext_axis_avg_buffer_3_s_axi_rdata(ext_axis_avg_buffer_3_s_axi_rdata),
        .ext_axis_avg_buffer_3_s_axi_rready(ext_axis_avg_buffer_3_s_axi_rready),
        .ext_axis_avg_buffer_3_s_axi_rresp(ext_axis_avg_buffer_3_s_axi_rresp),
        .ext_axis_avg_buffer_3_s_axi_rvalid(ext_axis_avg_buffer_3_s_axi_rvalid),
        .ext_axis_avg_buffer_3_s_axi_wdata(ext_axis_avg_buffer_3_s_axi_wdata),
        .ext_axis_avg_buffer_3_s_axi_wready(ext_axis_avg_buffer_3_s_axi_wready),
        .ext_axis_avg_buffer_3_s_axi_wstrb(ext_axis_avg_buffer_3_s_axi_wstrb),
        .ext_axis_avg_buffer_3_s_axi_wvalid(ext_axis_avg_buffer_3_s_axi_wvalid),
        .ext_axis_awg_tuning_v1_10_s_axi_araddr(ext_axis_awg_tuning_v1_10_s_axi_araddr),
        .ext_axis_awg_tuning_v1_10_s_axi_arprot(ext_axis_awg_tuning_v1_10_s_axi_arprot),
        .ext_axis_awg_tuning_v1_10_s_axi_arready(ext_axis_awg_tuning_v1_10_s_axi_arready),
        .ext_axis_awg_tuning_v1_10_s_axi_arvalid(ext_axis_awg_tuning_v1_10_s_axi_arvalid),
        .ext_axis_awg_tuning_v1_10_s_axi_awaddr(ext_axis_awg_tuning_v1_10_s_axi_awaddr),
        .ext_axis_awg_tuning_v1_10_s_axi_awprot(ext_axis_awg_tuning_v1_10_s_axi_awprot),
        .ext_axis_awg_tuning_v1_10_s_axi_awready(ext_axis_awg_tuning_v1_10_s_axi_awready),
        .ext_axis_awg_tuning_v1_10_s_axi_awvalid(ext_axis_awg_tuning_v1_10_s_axi_awvalid),
        .ext_axis_awg_tuning_v1_10_s_axi_bready(ext_axis_awg_tuning_v1_10_s_axi_bready),
        .ext_axis_awg_tuning_v1_10_s_axi_bresp(ext_axis_awg_tuning_v1_10_s_axi_bresp),
        .ext_axis_awg_tuning_v1_10_s_axi_bvalid(ext_axis_awg_tuning_v1_10_s_axi_bvalid),
        .ext_axis_awg_tuning_v1_10_s_axi_rdata(ext_axis_awg_tuning_v1_10_s_axi_rdata),
        .ext_axis_awg_tuning_v1_10_s_axi_rready(ext_axis_awg_tuning_v1_10_s_axi_rready),
        .ext_axis_awg_tuning_v1_10_s_axi_rresp(ext_axis_awg_tuning_v1_10_s_axi_rresp),
        .ext_axis_awg_tuning_v1_10_s_axi_rvalid(ext_axis_awg_tuning_v1_10_s_axi_rvalid),
        .ext_axis_awg_tuning_v1_10_s_axi_wdata(ext_axis_awg_tuning_v1_10_s_axi_wdata),
        .ext_axis_awg_tuning_v1_10_s_axi_wready(ext_axis_awg_tuning_v1_10_s_axi_wready),
        .ext_axis_awg_tuning_v1_10_s_axi_wstrb(ext_axis_awg_tuning_v1_10_s_axi_wstrb),
        .ext_axis_awg_tuning_v1_10_s_axi_wvalid(ext_axis_awg_tuning_v1_10_s_axi_wvalid),
        .ext_axis_awg_tuning_v1_11_s_axi_araddr(ext_axis_awg_tuning_v1_11_s_axi_araddr),
        .ext_axis_awg_tuning_v1_11_s_axi_arprot(ext_axis_awg_tuning_v1_11_s_axi_arprot),
        .ext_axis_awg_tuning_v1_11_s_axi_arready(ext_axis_awg_tuning_v1_11_s_axi_arready),
        .ext_axis_awg_tuning_v1_11_s_axi_arvalid(ext_axis_awg_tuning_v1_11_s_axi_arvalid),
        .ext_axis_awg_tuning_v1_11_s_axi_awaddr(ext_axis_awg_tuning_v1_11_s_axi_awaddr),
        .ext_axis_awg_tuning_v1_11_s_axi_awprot(ext_axis_awg_tuning_v1_11_s_axi_awprot),
        .ext_axis_awg_tuning_v1_11_s_axi_awready(ext_axis_awg_tuning_v1_11_s_axi_awready),
        .ext_axis_awg_tuning_v1_11_s_axi_awvalid(ext_axis_awg_tuning_v1_11_s_axi_awvalid),
        .ext_axis_awg_tuning_v1_11_s_axi_bready(ext_axis_awg_tuning_v1_11_s_axi_bready),
        .ext_axis_awg_tuning_v1_11_s_axi_bresp(ext_axis_awg_tuning_v1_11_s_axi_bresp),
        .ext_axis_awg_tuning_v1_11_s_axi_bvalid(ext_axis_awg_tuning_v1_11_s_axi_bvalid),
        .ext_axis_awg_tuning_v1_11_s_axi_rdata(ext_axis_awg_tuning_v1_11_s_axi_rdata),
        .ext_axis_awg_tuning_v1_11_s_axi_rready(ext_axis_awg_tuning_v1_11_s_axi_rready),
        .ext_axis_awg_tuning_v1_11_s_axi_rresp(ext_axis_awg_tuning_v1_11_s_axi_rresp),
        .ext_axis_awg_tuning_v1_11_s_axi_rvalid(ext_axis_awg_tuning_v1_11_s_axi_rvalid),
        .ext_axis_awg_tuning_v1_11_s_axi_wdata(ext_axis_awg_tuning_v1_11_s_axi_wdata),
        .ext_axis_awg_tuning_v1_11_s_axi_wready(ext_axis_awg_tuning_v1_11_s_axi_wready),
        .ext_axis_awg_tuning_v1_11_s_axi_wstrb(ext_axis_awg_tuning_v1_11_s_axi_wstrb),
        .ext_axis_awg_tuning_v1_11_s_axi_wvalid(ext_axis_awg_tuning_v1_11_s_axi_wvalid),
        .ext_axis_awg_tuning_v1_4_s_axi_araddr(ext_axis_awg_tuning_v1_4_s_axi_araddr),
        .ext_axis_awg_tuning_v1_4_s_axi_arprot(ext_axis_awg_tuning_v1_4_s_axi_arprot),
        .ext_axis_awg_tuning_v1_4_s_axi_arready(ext_axis_awg_tuning_v1_4_s_axi_arready),
        .ext_axis_awg_tuning_v1_4_s_axi_arvalid(ext_axis_awg_tuning_v1_4_s_axi_arvalid),
        .ext_axis_awg_tuning_v1_4_s_axi_awaddr(ext_axis_awg_tuning_v1_4_s_axi_awaddr),
        .ext_axis_awg_tuning_v1_4_s_axi_awprot(ext_axis_awg_tuning_v1_4_s_axi_awprot),
        .ext_axis_awg_tuning_v1_4_s_axi_awready(ext_axis_awg_tuning_v1_4_s_axi_awready),
        .ext_axis_awg_tuning_v1_4_s_axi_awvalid(ext_axis_awg_tuning_v1_4_s_axi_awvalid),
        .ext_axis_awg_tuning_v1_4_s_axi_bready(ext_axis_awg_tuning_v1_4_s_axi_bready),
        .ext_axis_awg_tuning_v1_4_s_axi_bresp(ext_axis_awg_tuning_v1_4_s_axi_bresp),
        .ext_axis_awg_tuning_v1_4_s_axi_bvalid(ext_axis_awg_tuning_v1_4_s_axi_bvalid),
        .ext_axis_awg_tuning_v1_4_s_axi_rdata(ext_axis_awg_tuning_v1_4_s_axi_rdata),
        .ext_axis_awg_tuning_v1_4_s_axi_rready(ext_axis_awg_tuning_v1_4_s_axi_rready),
        .ext_axis_awg_tuning_v1_4_s_axi_rresp(ext_axis_awg_tuning_v1_4_s_axi_rresp),
        .ext_axis_awg_tuning_v1_4_s_axi_rvalid(ext_axis_awg_tuning_v1_4_s_axi_rvalid),
        .ext_axis_awg_tuning_v1_4_s_axi_wdata(ext_axis_awg_tuning_v1_4_s_axi_wdata),
        .ext_axis_awg_tuning_v1_4_s_axi_wready(ext_axis_awg_tuning_v1_4_s_axi_wready),
        .ext_axis_awg_tuning_v1_4_s_axi_wstrb(ext_axis_awg_tuning_v1_4_s_axi_wstrb),
        .ext_axis_awg_tuning_v1_4_s_axi_wvalid(ext_axis_awg_tuning_v1_4_s_axi_wvalid),
        .ext_axis_awg_tuning_v1_5_s_axi_araddr(ext_axis_awg_tuning_v1_5_s_axi_araddr),
        .ext_axis_awg_tuning_v1_5_s_axi_arprot(ext_axis_awg_tuning_v1_5_s_axi_arprot),
        .ext_axis_awg_tuning_v1_5_s_axi_arready(ext_axis_awg_tuning_v1_5_s_axi_arready),
        .ext_axis_awg_tuning_v1_5_s_axi_arvalid(ext_axis_awg_tuning_v1_5_s_axi_arvalid),
        .ext_axis_awg_tuning_v1_5_s_axi_awaddr(ext_axis_awg_tuning_v1_5_s_axi_awaddr),
        .ext_axis_awg_tuning_v1_5_s_axi_awprot(ext_axis_awg_tuning_v1_5_s_axi_awprot),
        .ext_axis_awg_tuning_v1_5_s_axi_awready(ext_axis_awg_tuning_v1_5_s_axi_awready),
        .ext_axis_awg_tuning_v1_5_s_axi_awvalid(ext_axis_awg_tuning_v1_5_s_axi_awvalid),
        .ext_axis_awg_tuning_v1_5_s_axi_bready(ext_axis_awg_tuning_v1_5_s_axi_bready),
        .ext_axis_awg_tuning_v1_5_s_axi_bresp(ext_axis_awg_tuning_v1_5_s_axi_bresp),
        .ext_axis_awg_tuning_v1_5_s_axi_bvalid(ext_axis_awg_tuning_v1_5_s_axi_bvalid),
        .ext_axis_awg_tuning_v1_5_s_axi_rdata(ext_axis_awg_tuning_v1_5_s_axi_rdata),
        .ext_axis_awg_tuning_v1_5_s_axi_rready(ext_axis_awg_tuning_v1_5_s_axi_rready),
        .ext_axis_awg_tuning_v1_5_s_axi_rresp(ext_axis_awg_tuning_v1_5_s_axi_rresp),
        .ext_axis_awg_tuning_v1_5_s_axi_rvalid(ext_axis_awg_tuning_v1_5_s_axi_rvalid),
        .ext_axis_awg_tuning_v1_5_s_axi_wdata(ext_axis_awg_tuning_v1_5_s_axi_wdata),
        .ext_axis_awg_tuning_v1_5_s_axi_wready(ext_axis_awg_tuning_v1_5_s_axi_wready),
        .ext_axis_awg_tuning_v1_5_s_axi_wstrb(ext_axis_awg_tuning_v1_5_s_axi_wstrb),
        .ext_axis_awg_tuning_v1_5_s_axi_wvalid(ext_axis_awg_tuning_v1_5_s_axi_wvalid),
        .ext_axis_awg_tuning_v1_6_s_axi_araddr(ext_axis_awg_tuning_v1_6_s_axi_araddr),
        .ext_axis_awg_tuning_v1_6_s_axi_arprot(ext_axis_awg_tuning_v1_6_s_axi_arprot),
        .ext_axis_awg_tuning_v1_6_s_axi_arready(ext_axis_awg_tuning_v1_6_s_axi_arready),
        .ext_axis_awg_tuning_v1_6_s_axi_arvalid(ext_axis_awg_tuning_v1_6_s_axi_arvalid),
        .ext_axis_awg_tuning_v1_6_s_axi_awaddr(ext_axis_awg_tuning_v1_6_s_axi_awaddr),
        .ext_axis_awg_tuning_v1_6_s_axi_awprot(ext_axis_awg_tuning_v1_6_s_axi_awprot),
        .ext_axis_awg_tuning_v1_6_s_axi_awready(ext_axis_awg_tuning_v1_6_s_axi_awready),
        .ext_axis_awg_tuning_v1_6_s_axi_awvalid(ext_axis_awg_tuning_v1_6_s_axi_awvalid),
        .ext_axis_awg_tuning_v1_6_s_axi_bready(ext_axis_awg_tuning_v1_6_s_axi_bready),
        .ext_axis_awg_tuning_v1_6_s_axi_bresp(ext_axis_awg_tuning_v1_6_s_axi_bresp),
        .ext_axis_awg_tuning_v1_6_s_axi_bvalid(ext_axis_awg_tuning_v1_6_s_axi_bvalid),
        .ext_axis_awg_tuning_v1_6_s_axi_rdata(ext_axis_awg_tuning_v1_6_s_axi_rdata),
        .ext_axis_awg_tuning_v1_6_s_axi_rready(ext_axis_awg_tuning_v1_6_s_axi_rready),
        .ext_axis_awg_tuning_v1_6_s_axi_rresp(ext_axis_awg_tuning_v1_6_s_axi_rresp),
        .ext_axis_awg_tuning_v1_6_s_axi_rvalid(ext_axis_awg_tuning_v1_6_s_axi_rvalid),
        .ext_axis_awg_tuning_v1_6_s_axi_wdata(ext_axis_awg_tuning_v1_6_s_axi_wdata),
        .ext_axis_awg_tuning_v1_6_s_axi_wready(ext_axis_awg_tuning_v1_6_s_axi_wready),
        .ext_axis_awg_tuning_v1_6_s_axi_wstrb(ext_axis_awg_tuning_v1_6_s_axi_wstrb),
        .ext_axis_awg_tuning_v1_6_s_axi_wvalid(ext_axis_awg_tuning_v1_6_s_axi_wvalid),
        .ext_axis_awg_tuning_v1_8_s_axi_araddr(ext_axis_awg_tuning_v1_8_s_axi_araddr),
        .ext_axis_awg_tuning_v1_8_s_axi_arprot(ext_axis_awg_tuning_v1_8_s_axi_arprot),
        .ext_axis_awg_tuning_v1_8_s_axi_arready(ext_axis_awg_tuning_v1_8_s_axi_arready),
        .ext_axis_awg_tuning_v1_8_s_axi_arvalid(ext_axis_awg_tuning_v1_8_s_axi_arvalid),
        .ext_axis_awg_tuning_v1_8_s_axi_awaddr(ext_axis_awg_tuning_v1_8_s_axi_awaddr),
        .ext_axis_awg_tuning_v1_8_s_axi_awprot(ext_axis_awg_tuning_v1_8_s_axi_awprot),
        .ext_axis_awg_tuning_v1_8_s_axi_awready(ext_axis_awg_tuning_v1_8_s_axi_awready),
        .ext_axis_awg_tuning_v1_8_s_axi_awvalid(ext_axis_awg_tuning_v1_8_s_axi_awvalid),
        .ext_axis_awg_tuning_v1_8_s_axi_bready(ext_axis_awg_tuning_v1_8_s_axi_bready),
        .ext_axis_awg_tuning_v1_8_s_axi_bresp(ext_axis_awg_tuning_v1_8_s_axi_bresp),
        .ext_axis_awg_tuning_v1_8_s_axi_bvalid(ext_axis_awg_tuning_v1_8_s_axi_bvalid),
        .ext_axis_awg_tuning_v1_8_s_axi_rdata(ext_axis_awg_tuning_v1_8_s_axi_rdata),
        .ext_axis_awg_tuning_v1_8_s_axi_rready(ext_axis_awg_tuning_v1_8_s_axi_rready),
        .ext_axis_awg_tuning_v1_8_s_axi_rresp(ext_axis_awg_tuning_v1_8_s_axi_rresp),
        .ext_axis_awg_tuning_v1_8_s_axi_rvalid(ext_axis_awg_tuning_v1_8_s_axi_rvalid),
        .ext_axis_awg_tuning_v1_8_s_axi_wdata(ext_axis_awg_tuning_v1_8_s_axi_wdata),
        .ext_axis_awg_tuning_v1_8_s_axi_wready(ext_axis_awg_tuning_v1_8_s_axi_wready),
        .ext_axis_awg_tuning_v1_8_s_axi_wstrb(ext_axis_awg_tuning_v1_8_s_axi_wstrb),
        .ext_axis_awg_tuning_v1_8_s_axi_wvalid(ext_axis_awg_tuning_v1_8_s_axi_wvalid),
        .ext_axis_awg_tuning_v1_9_s_axi_araddr(ext_axis_awg_tuning_v1_9_s_axi_araddr),
        .ext_axis_awg_tuning_v1_9_s_axi_arprot(ext_axis_awg_tuning_v1_9_s_axi_arprot),
        .ext_axis_awg_tuning_v1_9_s_axi_arready(ext_axis_awg_tuning_v1_9_s_axi_arready),
        .ext_axis_awg_tuning_v1_9_s_axi_arvalid(ext_axis_awg_tuning_v1_9_s_axi_arvalid),
        .ext_axis_awg_tuning_v1_9_s_axi_awaddr(ext_axis_awg_tuning_v1_9_s_axi_awaddr),
        .ext_axis_awg_tuning_v1_9_s_axi_awprot(ext_axis_awg_tuning_v1_9_s_axi_awprot),
        .ext_axis_awg_tuning_v1_9_s_axi_awready(ext_axis_awg_tuning_v1_9_s_axi_awready),
        .ext_axis_awg_tuning_v1_9_s_axi_awvalid(ext_axis_awg_tuning_v1_9_s_axi_awvalid),
        .ext_axis_awg_tuning_v1_9_s_axi_bready(ext_axis_awg_tuning_v1_9_s_axi_bready),
        .ext_axis_awg_tuning_v1_9_s_axi_bresp(ext_axis_awg_tuning_v1_9_s_axi_bresp),
        .ext_axis_awg_tuning_v1_9_s_axi_bvalid(ext_axis_awg_tuning_v1_9_s_axi_bvalid),
        .ext_axis_awg_tuning_v1_9_s_axi_rdata(ext_axis_awg_tuning_v1_9_s_axi_rdata),
        .ext_axis_awg_tuning_v1_9_s_axi_rready(ext_axis_awg_tuning_v1_9_s_axi_rready),
        .ext_axis_awg_tuning_v1_9_s_axi_rresp(ext_axis_awg_tuning_v1_9_s_axi_rresp),
        .ext_axis_awg_tuning_v1_9_s_axi_rvalid(ext_axis_awg_tuning_v1_9_s_axi_rvalid),
        .ext_axis_awg_tuning_v1_9_s_axi_wdata(ext_axis_awg_tuning_v1_9_s_axi_wdata),
        .ext_axis_awg_tuning_v1_9_s_axi_wready(ext_axis_awg_tuning_v1_9_s_axi_wready),
        .ext_axis_awg_tuning_v1_9_s_axi_wstrb(ext_axis_awg_tuning_v1_9_s_axi_wstrb),
        .ext_axis_awg_tuning_v1_9_s_axi_wvalid(ext_axis_awg_tuning_v1_9_s_axi_wvalid),
        .ext_axis_dyn_readout_v1_0_s1_axis_tdata(ext_axis_dyn_readout_v1_0_s1_axis_tdata),
        .ext_axis_dyn_readout_v1_0_s1_axis_tready(ext_axis_dyn_readout_v1_0_s1_axis_tready),
        .ext_axis_dyn_readout_v1_0_s1_axis_tvalid(ext_axis_dyn_readout_v1_0_s1_axis_tvalid),
        .ext_axis_dyn_readout_v1_1_s1_axis_tdata(ext_axis_dyn_readout_v1_1_s1_axis_tdata),
        .ext_axis_dyn_readout_v1_1_s1_axis_tready(ext_axis_dyn_readout_v1_1_s1_axis_tready),
        .ext_axis_dyn_readout_v1_1_s1_axis_tvalid(ext_axis_dyn_readout_v1_1_s1_axis_tvalid),
        .ext_axis_dyn_readout_v1_2_s1_axis_tdata(ext_axis_dyn_readout_v1_2_s1_axis_tdata),
        .ext_axis_dyn_readout_v1_2_s1_axis_tready(ext_axis_dyn_readout_v1_2_s1_axis_tready),
        .ext_axis_dyn_readout_v1_2_s1_axis_tvalid(ext_axis_dyn_readout_v1_2_s1_axis_tvalid),
        .ext_axis_dyn_readout_v1_3_s1_axis_tdata(ext_axis_dyn_readout_v1_3_s1_axis_tdata),
        .ext_axis_dyn_readout_v1_3_s1_axis_tready(ext_axis_dyn_readout_v1_3_s1_axis_tready),
        .ext_axis_dyn_readout_v1_3_s1_axis_tvalid(ext_axis_dyn_readout_v1_3_s1_axis_tvalid),
        .ext_axis_register_slice_0_m_axis_tdata(ext_axis_register_slice_0_m_axis_tdata),
        .ext_axis_register_slice_0_m_axis_tready(ext_axis_register_slice_0_m_axis_tready),
        .ext_axis_register_slice_0_m_axis_tvalid(ext_axis_register_slice_0_m_axis_tvalid),
        .ext_axis_register_slice_10_m_axis_tdata(ext_axis_register_slice_10_m_axis_tdata),
        .ext_axis_register_slice_10_m_axis_tready(ext_axis_register_slice_10_m_axis_tready),
        .ext_axis_register_slice_10_m_axis_tvalid(ext_axis_register_slice_10_m_axis_tvalid),
        .ext_axis_register_slice_11_m_axis_tdata(ext_axis_register_slice_11_m_axis_tdata),
        .ext_axis_register_slice_11_m_axis_tready(ext_axis_register_slice_11_m_axis_tready),
        .ext_axis_register_slice_11_m_axis_tvalid(ext_axis_register_slice_11_m_axis_tvalid),
        .ext_axis_register_slice_12_m_axis_tdata(ext_axis_register_slice_12_m_axis_tdata),
        .ext_axis_register_slice_12_m_axis_tready(ext_axis_register_slice_12_m_axis_tready),
        .ext_axis_register_slice_12_m_axis_tvalid(ext_axis_register_slice_12_m_axis_tvalid),
        .ext_axis_register_slice_13_m_axis_tdata(ext_axis_register_slice_13_m_axis_tdata),
        .ext_axis_register_slice_13_m_axis_tready(ext_axis_register_slice_13_m_axis_tready),
        .ext_axis_register_slice_13_m_axis_tvalid(ext_axis_register_slice_13_m_axis_tvalid),
        .ext_axis_register_slice_14_m_axis_tdata(ext_axis_register_slice_14_m_axis_tdata),
        .ext_axis_register_slice_14_m_axis_tready(ext_axis_register_slice_14_m_axis_tready),
        .ext_axis_register_slice_14_m_axis_tvalid(ext_axis_register_slice_14_m_axis_tvalid),
        .ext_axis_register_slice_15_m_axis_tdata(ext_axis_register_slice_15_m_axis_tdata),
        .ext_axis_register_slice_15_m_axis_tready(ext_axis_register_slice_15_m_axis_tready),
        .ext_axis_register_slice_15_m_axis_tvalid(ext_axis_register_slice_15_m_axis_tvalid),
        .ext_axis_register_slice_16_m_axis_tdata(ext_axis_register_slice_16_m_axis_tdata),
        .ext_axis_register_slice_16_m_axis_tready(ext_axis_register_slice_16_m_axis_tready),
        .ext_axis_register_slice_16_m_axis_tvalid(ext_axis_register_slice_16_m_axis_tvalid),
        .ext_axis_register_slice_1_m_axis_tdata(ext_axis_register_slice_1_m_axis_tdata),
        .ext_axis_register_slice_1_m_axis_tready(ext_axis_register_slice_1_m_axis_tready),
        .ext_axis_register_slice_1_m_axis_tvalid(ext_axis_register_slice_1_m_axis_tvalid),
        .ext_axis_register_slice_2_m_axis_tdata(ext_axis_register_slice_2_m_axis_tdata),
        .ext_axis_register_slice_2_m_axis_tready(ext_axis_register_slice_2_m_axis_tready),
        .ext_axis_register_slice_2_m_axis_tvalid(ext_axis_register_slice_2_m_axis_tvalid),
        .ext_axis_register_slice_3_m_axis_tdata(ext_axis_register_slice_3_m_axis_tdata),
        .ext_axis_register_slice_3_m_axis_tready(ext_axis_register_slice_3_m_axis_tready),
        .ext_axis_register_slice_3_m_axis_tvalid(ext_axis_register_slice_3_m_axis_tvalid),
        .ext_axis_register_slice_8_m_axis_tdata(ext_axis_register_slice_8_m_axis_tdata),
        .ext_axis_register_slice_8_m_axis_tready(ext_axis_register_slice_8_m_axis_tready),
        .ext_axis_register_slice_8_m_axis_tvalid(ext_axis_register_slice_8_m_axis_tvalid),
        .ext_axis_signal_gen_v6_0_s_axi_araddr(ext_axis_signal_gen_v6_0_s_axi_araddr),
        .ext_axis_signal_gen_v6_0_s_axi_arprot(ext_axis_signal_gen_v6_0_s_axi_arprot),
        .ext_axis_signal_gen_v6_0_s_axi_arready(ext_axis_signal_gen_v6_0_s_axi_arready),
        .ext_axis_signal_gen_v6_0_s_axi_arvalid(ext_axis_signal_gen_v6_0_s_axi_arvalid),
        .ext_axis_signal_gen_v6_0_s_axi_awaddr(ext_axis_signal_gen_v6_0_s_axi_awaddr),
        .ext_axis_signal_gen_v6_0_s_axi_awprot(ext_axis_signal_gen_v6_0_s_axi_awprot),
        .ext_axis_signal_gen_v6_0_s_axi_awready(ext_axis_signal_gen_v6_0_s_axi_awready),
        .ext_axis_signal_gen_v6_0_s_axi_awvalid(ext_axis_signal_gen_v6_0_s_axi_awvalid),
        .ext_axis_signal_gen_v6_0_s_axi_bready(ext_axis_signal_gen_v6_0_s_axi_bready),
        .ext_axis_signal_gen_v6_0_s_axi_bresp(ext_axis_signal_gen_v6_0_s_axi_bresp),
        .ext_axis_signal_gen_v6_0_s_axi_bvalid(ext_axis_signal_gen_v6_0_s_axi_bvalid),
        .ext_axis_signal_gen_v6_0_s_axi_rdata(ext_axis_signal_gen_v6_0_s_axi_rdata),
        .ext_axis_signal_gen_v6_0_s_axi_rready(ext_axis_signal_gen_v6_0_s_axi_rready),
        .ext_axis_signal_gen_v6_0_s_axi_rresp(ext_axis_signal_gen_v6_0_s_axi_rresp),
        .ext_axis_signal_gen_v6_0_s_axi_rvalid(ext_axis_signal_gen_v6_0_s_axi_rvalid),
        .ext_axis_signal_gen_v6_0_s_axi_wdata(ext_axis_signal_gen_v6_0_s_axi_wdata),
        .ext_axis_signal_gen_v6_0_s_axi_wready(ext_axis_signal_gen_v6_0_s_axi_wready),
        .ext_axis_signal_gen_v6_0_s_axi_wstrb(ext_axis_signal_gen_v6_0_s_axi_wstrb),
        .ext_axis_signal_gen_v6_0_s_axi_wvalid(ext_axis_signal_gen_v6_0_s_axi_wvalid),
        .ext_axis_signal_gen_v6_1_s_axi_araddr(ext_axis_signal_gen_v6_1_s_axi_araddr),
        .ext_axis_signal_gen_v6_1_s_axi_arprot(ext_axis_signal_gen_v6_1_s_axi_arprot),
        .ext_axis_signal_gen_v6_1_s_axi_arready(ext_axis_signal_gen_v6_1_s_axi_arready),
        .ext_axis_signal_gen_v6_1_s_axi_arvalid(ext_axis_signal_gen_v6_1_s_axi_arvalid),
        .ext_axis_signal_gen_v6_1_s_axi_awaddr(ext_axis_signal_gen_v6_1_s_axi_awaddr),
        .ext_axis_signal_gen_v6_1_s_axi_awprot(ext_axis_signal_gen_v6_1_s_axi_awprot),
        .ext_axis_signal_gen_v6_1_s_axi_awready(ext_axis_signal_gen_v6_1_s_axi_awready),
        .ext_axis_signal_gen_v6_1_s_axi_awvalid(ext_axis_signal_gen_v6_1_s_axi_awvalid),
        .ext_axis_signal_gen_v6_1_s_axi_bready(ext_axis_signal_gen_v6_1_s_axi_bready),
        .ext_axis_signal_gen_v6_1_s_axi_bresp(ext_axis_signal_gen_v6_1_s_axi_bresp),
        .ext_axis_signal_gen_v6_1_s_axi_bvalid(ext_axis_signal_gen_v6_1_s_axi_bvalid),
        .ext_axis_signal_gen_v6_1_s_axi_rdata(ext_axis_signal_gen_v6_1_s_axi_rdata),
        .ext_axis_signal_gen_v6_1_s_axi_rready(ext_axis_signal_gen_v6_1_s_axi_rready),
        .ext_axis_signal_gen_v6_1_s_axi_rresp(ext_axis_signal_gen_v6_1_s_axi_rresp),
        .ext_axis_signal_gen_v6_1_s_axi_rvalid(ext_axis_signal_gen_v6_1_s_axi_rvalid),
        .ext_axis_signal_gen_v6_1_s_axi_wdata(ext_axis_signal_gen_v6_1_s_axi_wdata),
        .ext_axis_signal_gen_v6_1_s_axi_wready(ext_axis_signal_gen_v6_1_s_axi_wready),
        .ext_axis_signal_gen_v6_1_s_axi_wstrb(ext_axis_signal_gen_v6_1_s_axi_wstrb),
        .ext_axis_signal_gen_v6_1_s_axi_wvalid(ext_axis_signal_gen_v6_1_s_axi_wvalid),
        .ext_axis_signal_gen_v6_2_s_axi_araddr(ext_axis_signal_gen_v6_2_s_axi_araddr),
        .ext_axis_signal_gen_v6_2_s_axi_arprot(ext_axis_signal_gen_v6_2_s_axi_arprot),
        .ext_axis_signal_gen_v6_2_s_axi_arready(ext_axis_signal_gen_v6_2_s_axi_arready),
        .ext_axis_signal_gen_v6_2_s_axi_arvalid(ext_axis_signal_gen_v6_2_s_axi_arvalid),
        .ext_axis_signal_gen_v6_2_s_axi_awaddr(ext_axis_signal_gen_v6_2_s_axi_awaddr),
        .ext_axis_signal_gen_v6_2_s_axi_awprot(ext_axis_signal_gen_v6_2_s_axi_awprot),
        .ext_axis_signal_gen_v6_2_s_axi_awready(ext_axis_signal_gen_v6_2_s_axi_awready),
        .ext_axis_signal_gen_v6_2_s_axi_awvalid(ext_axis_signal_gen_v6_2_s_axi_awvalid),
        .ext_axis_signal_gen_v6_2_s_axi_bready(ext_axis_signal_gen_v6_2_s_axi_bready),
        .ext_axis_signal_gen_v6_2_s_axi_bresp(ext_axis_signal_gen_v6_2_s_axi_bresp),
        .ext_axis_signal_gen_v6_2_s_axi_bvalid(ext_axis_signal_gen_v6_2_s_axi_bvalid),
        .ext_axis_signal_gen_v6_2_s_axi_rdata(ext_axis_signal_gen_v6_2_s_axi_rdata),
        .ext_axis_signal_gen_v6_2_s_axi_rready(ext_axis_signal_gen_v6_2_s_axi_rready),
        .ext_axis_signal_gen_v6_2_s_axi_rresp(ext_axis_signal_gen_v6_2_s_axi_rresp),
        .ext_axis_signal_gen_v6_2_s_axi_rvalid(ext_axis_signal_gen_v6_2_s_axi_rvalid),
        .ext_axis_signal_gen_v6_2_s_axi_wdata(ext_axis_signal_gen_v6_2_s_axi_wdata),
        .ext_axis_signal_gen_v6_2_s_axi_wready(ext_axis_signal_gen_v6_2_s_axi_wready),
        .ext_axis_signal_gen_v6_2_s_axi_wstrb(ext_axis_signal_gen_v6_2_s_axi_wstrb),
        .ext_axis_signal_gen_v6_2_s_axi_wvalid(ext_axis_signal_gen_v6_2_s_axi_wvalid),
        .ext_axis_signal_gen_v6_3_s_axi_araddr(ext_axis_signal_gen_v6_3_s_axi_araddr),
        .ext_axis_signal_gen_v6_3_s_axi_arprot(ext_axis_signal_gen_v6_3_s_axi_arprot),
        .ext_axis_signal_gen_v6_3_s_axi_arready(ext_axis_signal_gen_v6_3_s_axi_arready),
        .ext_axis_signal_gen_v6_3_s_axi_arvalid(ext_axis_signal_gen_v6_3_s_axi_arvalid),
        .ext_axis_signal_gen_v6_3_s_axi_awaddr(ext_axis_signal_gen_v6_3_s_axi_awaddr),
        .ext_axis_signal_gen_v6_3_s_axi_awprot(ext_axis_signal_gen_v6_3_s_axi_awprot),
        .ext_axis_signal_gen_v6_3_s_axi_awready(ext_axis_signal_gen_v6_3_s_axi_awready),
        .ext_axis_signal_gen_v6_3_s_axi_awvalid(ext_axis_signal_gen_v6_3_s_axi_awvalid),
        .ext_axis_signal_gen_v6_3_s_axi_bready(ext_axis_signal_gen_v6_3_s_axi_bready),
        .ext_axis_signal_gen_v6_3_s_axi_bresp(ext_axis_signal_gen_v6_3_s_axi_bresp),
        .ext_axis_signal_gen_v6_3_s_axi_bvalid(ext_axis_signal_gen_v6_3_s_axi_bvalid),
        .ext_axis_signal_gen_v6_3_s_axi_rdata(ext_axis_signal_gen_v6_3_s_axi_rdata),
        .ext_axis_signal_gen_v6_3_s_axi_rready(ext_axis_signal_gen_v6_3_s_axi_rready),
        .ext_axis_signal_gen_v6_3_s_axi_rresp(ext_axis_signal_gen_v6_3_s_axi_rresp),
        .ext_axis_signal_gen_v6_3_s_axi_rvalid(ext_axis_signal_gen_v6_3_s_axi_rvalid),
        .ext_axis_signal_gen_v6_3_s_axi_wdata(ext_axis_signal_gen_v6_3_s_axi_wdata),
        .ext_axis_signal_gen_v6_3_s_axi_wready(ext_axis_signal_gen_v6_3_s_axi_wready),
        .ext_axis_signal_gen_v6_3_s_axi_wstrb(ext_axis_signal_gen_v6_3_s_axi_wstrb),
        .ext_axis_signal_gen_v6_3_s_axi_wvalid(ext_axis_signal_gen_v6_3_s_axi_wvalid),
        .ext_axis_square_pulse_v1_0_s_axi_araddr(ext_axis_square_pulse_v1_0_s_axi_araddr),
        .ext_axis_square_pulse_v1_0_s_axi_arprot(ext_axis_square_pulse_v1_0_s_axi_arprot),
        .ext_axis_square_pulse_v1_0_s_axi_arready(ext_axis_square_pulse_v1_0_s_axi_arready),
        .ext_axis_square_pulse_v1_0_s_axi_arvalid(ext_axis_square_pulse_v1_0_s_axi_arvalid),
        .ext_axis_square_pulse_v1_0_s_axi_awaddr(ext_axis_square_pulse_v1_0_s_axi_awaddr),
        .ext_axis_square_pulse_v1_0_s_axi_awprot(ext_axis_square_pulse_v1_0_s_axi_awprot),
        .ext_axis_square_pulse_v1_0_s_axi_awready(ext_axis_square_pulse_v1_0_s_axi_awready),
        .ext_axis_square_pulse_v1_0_s_axi_awvalid(ext_axis_square_pulse_v1_0_s_axi_awvalid),
        .ext_axis_square_pulse_v1_0_s_axi_bready(ext_axis_square_pulse_v1_0_s_axi_bready),
        .ext_axis_square_pulse_v1_0_s_axi_bresp(ext_axis_square_pulse_v1_0_s_axi_bresp),
        .ext_axis_square_pulse_v1_0_s_axi_bvalid(ext_axis_square_pulse_v1_0_s_axi_bvalid),
        .ext_axis_square_pulse_v1_0_s_axi_rdata(ext_axis_square_pulse_v1_0_s_axi_rdata),
        .ext_axis_square_pulse_v1_0_s_axi_rready(ext_axis_square_pulse_v1_0_s_axi_rready),
        .ext_axis_square_pulse_v1_0_s_axi_rresp(ext_axis_square_pulse_v1_0_s_axi_rresp),
        .ext_axis_square_pulse_v1_0_s_axi_rvalid(ext_axis_square_pulse_v1_0_s_axi_rvalid),
        .ext_axis_square_pulse_v1_0_s_axi_wdata(ext_axis_square_pulse_v1_0_s_axi_wdata),
        .ext_axis_square_pulse_v1_0_s_axi_wready(ext_axis_square_pulse_v1_0_s_axi_wready),
        .ext_axis_square_pulse_v1_0_s_axi_wstrb(ext_axis_square_pulse_v1_0_s_axi_wstrb),
        .ext_axis_square_pulse_v1_0_s_axi_wvalid(ext_axis_square_pulse_v1_0_s_axi_wvalid),
        .ext_axis_switch_avg_M00_AXIS_tdata(ext_axis_switch_avg_M00_AXIS_tdata),
        .ext_axis_switch_avg_M00_AXIS_tlast(ext_axis_switch_avg_M00_AXIS_tlast),
        .ext_axis_switch_avg_M00_AXIS_tready(ext_axis_switch_avg_M00_AXIS_tready),
        .ext_axis_switch_avg_M00_AXIS_tvalid(ext_axis_switch_avg_M00_AXIS_tvalid),
        .ext_axis_switch_avg_S_AXI_CTRL_araddr(ext_axis_switch_avg_S_AXI_CTRL_araddr),
        .ext_axis_switch_avg_S_AXI_CTRL_arready(ext_axis_switch_avg_S_AXI_CTRL_arready),
        .ext_axis_switch_avg_S_AXI_CTRL_arvalid(ext_axis_switch_avg_S_AXI_CTRL_arvalid),
        .ext_axis_switch_avg_S_AXI_CTRL_awaddr(ext_axis_switch_avg_S_AXI_CTRL_awaddr),
        .ext_axis_switch_avg_S_AXI_CTRL_awready(ext_axis_switch_avg_S_AXI_CTRL_awready),
        .ext_axis_switch_avg_S_AXI_CTRL_awvalid(ext_axis_switch_avg_S_AXI_CTRL_awvalid),
        .ext_axis_switch_avg_S_AXI_CTRL_bready(ext_axis_switch_avg_S_AXI_CTRL_bready),
        .ext_axis_switch_avg_S_AXI_CTRL_bresp(ext_axis_switch_avg_S_AXI_CTRL_bresp),
        .ext_axis_switch_avg_S_AXI_CTRL_bvalid(ext_axis_switch_avg_S_AXI_CTRL_bvalid),
        .ext_axis_switch_avg_S_AXI_CTRL_rdata(ext_axis_switch_avg_S_AXI_CTRL_rdata),
        .ext_axis_switch_avg_S_AXI_CTRL_rready(ext_axis_switch_avg_S_AXI_CTRL_rready),
        .ext_axis_switch_avg_S_AXI_CTRL_rresp(ext_axis_switch_avg_S_AXI_CTRL_rresp),
        .ext_axis_switch_avg_S_AXI_CTRL_rvalid(ext_axis_switch_avg_S_AXI_CTRL_rvalid),
        .ext_axis_switch_avg_S_AXI_CTRL_wdata(ext_axis_switch_avg_S_AXI_CTRL_wdata),
        .ext_axis_switch_avg_S_AXI_CTRL_wready(ext_axis_switch_avg_S_AXI_CTRL_wready),
        .ext_axis_switch_avg_S_AXI_CTRL_wvalid(ext_axis_switch_avg_S_AXI_CTRL_wvalid),
        .ext_axis_switch_buf_M00_AXIS_tdata(ext_axis_switch_buf_M00_AXIS_tdata),
        .ext_axis_switch_buf_M00_AXIS_tlast(ext_axis_switch_buf_M00_AXIS_tlast),
        .ext_axis_switch_buf_M00_AXIS_tready(ext_axis_switch_buf_M00_AXIS_tready),
        .ext_axis_switch_buf_M00_AXIS_tvalid(ext_axis_switch_buf_M00_AXIS_tvalid),
        .ext_axis_switch_buf_S_AXI_CTRL_araddr(ext_axis_switch_buf_S_AXI_CTRL_araddr),
        .ext_axis_switch_buf_S_AXI_CTRL_arready(ext_axis_switch_buf_S_AXI_CTRL_arready),
        .ext_axis_switch_buf_S_AXI_CTRL_arvalid(ext_axis_switch_buf_S_AXI_CTRL_arvalid),
        .ext_axis_switch_buf_S_AXI_CTRL_awaddr(ext_axis_switch_buf_S_AXI_CTRL_awaddr),
        .ext_axis_switch_buf_S_AXI_CTRL_awready(ext_axis_switch_buf_S_AXI_CTRL_awready),
        .ext_axis_switch_buf_S_AXI_CTRL_awvalid(ext_axis_switch_buf_S_AXI_CTRL_awvalid),
        .ext_axis_switch_buf_S_AXI_CTRL_bready(ext_axis_switch_buf_S_AXI_CTRL_bready),
        .ext_axis_switch_buf_S_AXI_CTRL_bresp(ext_axis_switch_buf_S_AXI_CTRL_bresp),
        .ext_axis_switch_buf_S_AXI_CTRL_bvalid(ext_axis_switch_buf_S_AXI_CTRL_bvalid),
        .ext_axis_switch_buf_S_AXI_CTRL_rdata(ext_axis_switch_buf_S_AXI_CTRL_rdata),
        .ext_axis_switch_buf_S_AXI_CTRL_rready(ext_axis_switch_buf_S_AXI_CTRL_rready),
        .ext_axis_switch_buf_S_AXI_CTRL_rresp(ext_axis_switch_buf_S_AXI_CTRL_rresp),
        .ext_axis_switch_buf_S_AXI_CTRL_rvalid(ext_axis_switch_buf_S_AXI_CTRL_rvalid),
        .ext_axis_switch_buf_S_AXI_CTRL_wdata(ext_axis_switch_buf_S_AXI_CTRL_wdata),
        .ext_axis_switch_buf_S_AXI_CTRL_wready(ext_axis_switch_buf_S_AXI_CTRL_wready),
        .ext_axis_switch_buf_S_AXI_CTRL_wvalid(ext_axis_switch_buf_S_AXI_CTRL_wvalid),
        .ext_axis_switch_ddr_S_AXI_CTRL_araddr(ext_axis_switch_ddr_S_AXI_CTRL_araddr),
        .ext_axis_switch_ddr_S_AXI_CTRL_arready(ext_axis_switch_ddr_S_AXI_CTRL_arready),
        .ext_axis_switch_ddr_S_AXI_CTRL_arvalid(ext_axis_switch_ddr_S_AXI_CTRL_arvalid),
        .ext_axis_switch_ddr_S_AXI_CTRL_awaddr(ext_axis_switch_ddr_S_AXI_CTRL_awaddr),
        .ext_axis_switch_ddr_S_AXI_CTRL_awready(ext_axis_switch_ddr_S_AXI_CTRL_awready),
        .ext_axis_switch_ddr_S_AXI_CTRL_awvalid(ext_axis_switch_ddr_S_AXI_CTRL_awvalid),
        .ext_axis_switch_ddr_S_AXI_CTRL_bready(ext_axis_switch_ddr_S_AXI_CTRL_bready),
        .ext_axis_switch_ddr_S_AXI_CTRL_bresp(ext_axis_switch_ddr_S_AXI_CTRL_bresp),
        .ext_axis_switch_ddr_S_AXI_CTRL_bvalid(ext_axis_switch_ddr_S_AXI_CTRL_bvalid),
        .ext_axis_switch_ddr_S_AXI_CTRL_rdata(ext_axis_switch_ddr_S_AXI_CTRL_rdata),
        .ext_axis_switch_ddr_S_AXI_CTRL_rready(ext_axis_switch_ddr_S_AXI_CTRL_rready),
        .ext_axis_switch_ddr_S_AXI_CTRL_rresp(ext_axis_switch_ddr_S_AXI_CTRL_rresp),
        .ext_axis_switch_ddr_S_AXI_CTRL_rvalid(ext_axis_switch_ddr_S_AXI_CTRL_rvalid),
        .ext_axis_switch_ddr_S_AXI_CTRL_wdata(ext_axis_switch_ddr_S_AXI_CTRL_wdata),
        .ext_axis_switch_ddr_S_AXI_CTRL_wready(ext_axis_switch_ddr_S_AXI_CTRL_wready),
        .ext_axis_switch_ddr_S_AXI_CTRL_wvalid(ext_axis_switch_ddr_S_AXI_CTRL_wvalid),
        .ext_axis_switch_gen_M04_AXIS_tdata(ext_axis_switch_gen_M04_AXIS_tdata),
        .ext_axis_switch_gen_M04_AXIS_tkeep(ext_axis_switch_gen_M04_AXIS_tkeep),
        .ext_axis_switch_gen_M04_AXIS_tlast(ext_axis_switch_gen_M04_AXIS_tlast),
        .ext_axis_switch_gen_M04_AXIS_tready(ext_axis_switch_gen_M04_AXIS_tready),
        .ext_axis_switch_gen_M04_AXIS_tvalid(ext_axis_switch_gen_M04_AXIS_tvalid),
        .ext_axis_switch_gen_M05_AXIS_tdata(ext_axis_switch_gen_M05_AXIS_tdata),
        .ext_axis_switch_gen_M05_AXIS_tkeep(ext_axis_switch_gen_M05_AXIS_tkeep),
        .ext_axis_switch_gen_M05_AXIS_tlast(ext_axis_switch_gen_M05_AXIS_tlast),
        .ext_axis_switch_gen_M05_AXIS_tready(ext_axis_switch_gen_M05_AXIS_tready),
        .ext_axis_switch_gen_M05_AXIS_tvalid(ext_axis_switch_gen_M05_AXIS_tvalid),
        .ext_axis_switch_gen_M06_AXIS_tdata(ext_axis_switch_gen_M06_AXIS_tdata),
        .ext_axis_switch_gen_M06_AXIS_tkeep(ext_axis_switch_gen_M06_AXIS_tkeep),
        .ext_axis_switch_gen_M06_AXIS_tlast(ext_axis_switch_gen_M06_AXIS_tlast),
        .ext_axis_switch_gen_M06_AXIS_tready(ext_axis_switch_gen_M06_AXIS_tready),
        .ext_axis_switch_gen_M06_AXIS_tvalid(ext_axis_switch_gen_M06_AXIS_tvalid),
        .ext_axis_switch_gen_M07_AXIS_tdata(ext_axis_switch_gen_M07_AXIS_tdata),
        .ext_axis_switch_gen_M07_AXIS_tkeep(ext_axis_switch_gen_M07_AXIS_tkeep),
        .ext_axis_switch_gen_M07_AXIS_tlast(ext_axis_switch_gen_M07_AXIS_tlast),
        .ext_axis_switch_gen_M07_AXIS_tready(ext_axis_switch_gen_M07_AXIS_tready),
        .ext_axis_switch_gen_M07_AXIS_tvalid(ext_axis_switch_gen_M07_AXIS_tvalid),
        .ext_axis_switch_gen_M08_AXIS_tdata(ext_axis_switch_gen_M08_AXIS_tdata),
        .ext_axis_switch_gen_M08_AXIS_tkeep(ext_axis_switch_gen_M08_AXIS_tkeep),
        .ext_axis_switch_gen_M08_AXIS_tlast(ext_axis_switch_gen_M08_AXIS_tlast),
        .ext_axis_switch_gen_M08_AXIS_tready(ext_axis_switch_gen_M08_AXIS_tready),
        .ext_axis_switch_gen_M08_AXIS_tvalid(ext_axis_switch_gen_M08_AXIS_tvalid),
        .ext_axis_switch_gen_M09_AXIS_tdata(ext_axis_switch_gen_M09_AXIS_tdata),
        .ext_axis_switch_gen_M09_AXIS_tkeep(ext_axis_switch_gen_M09_AXIS_tkeep),
        .ext_axis_switch_gen_M09_AXIS_tlast(ext_axis_switch_gen_M09_AXIS_tlast),
        .ext_axis_switch_gen_M09_AXIS_tready(ext_axis_switch_gen_M09_AXIS_tready),
        .ext_axis_switch_gen_M09_AXIS_tvalid(ext_axis_switch_gen_M09_AXIS_tvalid),
        .ext_axis_switch_gen_M10_AXIS_tdata(ext_axis_switch_gen_M10_AXIS_tdata),
        .ext_axis_switch_gen_M10_AXIS_tkeep(ext_axis_switch_gen_M10_AXIS_tkeep),
        .ext_axis_switch_gen_M10_AXIS_tlast(ext_axis_switch_gen_M10_AXIS_tlast),
        .ext_axis_switch_gen_M10_AXIS_tready(ext_axis_switch_gen_M10_AXIS_tready),
        .ext_axis_switch_gen_M10_AXIS_tvalid(ext_axis_switch_gen_M10_AXIS_tvalid),
        .ext_axis_switch_gen_M11_AXIS_tdata(ext_axis_switch_gen_M11_AXIS_tdata),
        .ext_axis_switch_gen_M11_AXIS_tkeep(ext_axis_switch_gen_M11_AXIS_tkeep),
        .ext_axis_switch_gen_M11_AXIS_tlast(ext_axis_switch_gen_M11_AXIS_tlast),
        .ext_axis_switch_gen_M11_AXIS_tready(ext_axis_switch_gen_M11_AXIS_tready),
        .ext_axis_switch_gen_M11_AXIS_tvalid(ext_axis_switch_gen_M11_AXIS_tvalid),
        .ext_axis_switch_gen_S00_AXIS_tdata(ext_axis_switch_gen_S00_AXIS_tdata),
        .ext_axis_switch_gen_S00_AXIS_tkeep(ext_axis_switch_gen_S00_AXIS_tkeep),
        .ext_axis_switch_gen_S00_AXIS_tlast(ext_axis_switch_gen_S00_AXIS_tlast),
        .ext_axis_switch_gen_S00_AXIS_tready(ext_axis_switch_gen_S00_AXIS_tready),
        .ext_axis_switch_gen_S00_AXIS_tvalid(ext_axis_switch_gen_S00_AXIS_tvalid),
        .ext_axis_switch_gen_S_AXI_CTRL_araddr(ext_axis_switch_gen_S_AXI_CTRL_araddr),
        .ext_axis_switch_gen_S_AXI_CTRL_arready(ext_axis_switch_gen_S_AXI_CTRL_arready),
        .ext_axis_switch_gen_S_AXI_CTRL_arvalid(ext_axis_switch_gen_S_AXI_CTRL_arvalid),
        .ext_axis_switch_gen_S_AXI_CTRL_awaddr(ext_axis_switch_gen_S_AXI_CTRL_awaddr),
        .ext_axis_switch_gen_S_AXI_CTRL_awready(ext_axis_switch_gen_S_AXI_CTRL_awready),
        .ext_axis_switch_gen_S_AXI_CTRL_awvalid(ext_axis_switch_gen_S_AXI_CTRL_awvalid),
        .ext_axis_switch_gen_S_AXI_CTRL_bready(ext_axis_switch_gen_S_AXI_CTRL_bready),
        .ext_axis_switch_gen_S_AXI_CTRL_bresp(ext_axis_switch_gen_S_AXI_CTRL_bresp),
        .ext_axis_switch_gen_S_AXI_CTRL_bvalid(ext_axis_switch_gen_S_AXI_CTRL_bvalid),
        .ext_axis_switch_gen_S_AXI_CTRL_rdata(ext_axis_switch_gen_S_AXI_CTRL_rdata),
        .ext_axis_switch_gen_S_AXI_CTRL_rready(ext_axis_switch_gen_S_AXI_CTRL_rready),
        .ext_axis_switch_gen_S_AXI_CTRL_rresp(ext_axis_switch_gen_S_AXI_CTRL_rresp),
        .ext_axis_switch_gen_S_AXI_CTRL_rvalid(ext_axis_switch_gen_S_AXI_CTRL_rvalid),
        .ext_axis_switch_gen_S_AXI_CTRL_wdata(ext_axis_switch_gen_S_AXI_CTRL_wdata),
        .ext_axis_switch_gen_S_AXI_CTRL_wready(ext_axis_switch_gen_S_AXI_CTRL_wready),
        .ext_axis_switch_gen_S_AXI_CTRL_wvalid(ext_axis_switch_gen_S_AXI_CTRL_wvalid),
        .ext_axis_switch_mr_S_AXI_CTRL_araddr(ext_axis_switch_mr_S_AXI_CTRL_araddr),
        .ext_axis_switch_mr_S_AXI_CTRL_arready(ext_axis_switch_mr_S_AXI_CTRL_arready),
        .ext_axis_switch_mr_S_AXI_CTRL_arvalid(ext_axis_switch_mr_S_AXI_CTRL_arvalid),
        .ext_axis_switch_mr_S_AXI_CTRL_awaddr(ext_axis_switch_mr_S_AXI_CTRL_awaddr),
        .ext_axis_switch_mr_S_AXI_CTRL_awready(ext_axis_switch_mr_S_AXI_CTRL_awready),
        .ext_axis_switch_mr_S_AXI_CTRL_awvalid(ext_axis_switch_mr_S_AXI_CTRL_awvalid),
        .ext_axis_switch_mr_S_AXI_CTRL_bready(ext_axis_switch_mr_S_AXI_CTRL_bready),
        .ext_axis_switch_mr_S_AXI_CTRL_bresp(ext_axis_switch_mr_S_AXI_CTRL_bresp),
        .ext_axis_switch_mr_S_AXI_CTRL_bvalid(ext_axis_switch_mr_S_AXI_CTRL_bvalid),
        .ext_axis_switch_mr_S_AXI_CTRL_rdata(ext_axis_switch_mr_S_AXI_CTRL_rdata),
        .ext_axis_switch_mr_S_AXI_CTRL_rready(ext_axis_switch_mr_S_AXI_CTRL_rready),
        .ext_axis_switch_mr_S_AXI_CTRL_rresp(ext_axis_switch_mr_S_AXI_CTRL_rresp),
        .ext_axis_switch_mr_S_AXI_CTRL_rvalid(ext_axis_switch_mr_S_AXI_CTRL_rvalid),
        .ext_axis_switch_mr_S_AXI_CTRL_wdata(ext_axis_switch_mr_S_AXI_CTRL_wdata),
        .ext_axis_switch_mr_S_AXI_CTRL_wready(ext_axis_switch_mr_S_AXI_CTRL_wready),
        .ext_axis_switch_mr_S_AXI_CTRL_wvalid(ext_axis_switch_mr_S_AXI_CTRL_wvalid),
        .ext_axis_tproc64x32_x8_0_m0_axis_tdata(ext_axis_tproc64x32_x8_0_m0_axis_tdata),
        .ext_axis_tproc64x32_x8_0_m0_axis_tlast(ext_axis_tproc64x32_x8_0_m0_axis_tlast),
        .ext_axis_tproc64x32_x8_0_m0_axis_tready(ext_axis_tproc64x32_x8_0_m0_axis_tready),
        .ext_axis_tproc64x32_x8_0_m0_axis_tvalid(ext_axis_tproc64x32_x8_0_m0_axis_tvalid),
        .ext_axis_tproc64x32_x8_0_pmem_addr(ext_axis_tproc64x32_x8_0_pmem_addr),
        .ext_axis_tproc64x32_x8_0_pmem_do(ext_axis_tproc64x32_x8_0_pmem_do),
        .ext_axis_tproc64x32_x8_0_s0_axis_tdata(ext_axis_tproc64x32_x8_0_s0_axis_tdata),
        .ext_axis_tproc64x32_x8_0_s0_axis_tlast(ext_axis_tproc64x32_x8_0_s0_axis_tlast),
        .ext_axis_tproc64x32_x8_0_s0_axis_tready(ext_axis_tproc64x32_x8_0_s0_axis_tready),
        .ext_axis_tproc64x32_x8_0_s0_axis_tvalid(ext_axis_tproc64x32_x8_0_s0_axis_tvalid),
        .ext_axis_tproc64x32_x8_0_s_axi_araddr(ext_axis_tproc64x32_x8_0_s_axi_araddr),
        .ext_axis_tproc64x32_x8_0_s_axi_arprot(ext_axis_tproc64x32_x8_0_s_axi_arprot),
        .ext_axis_tproc64x32_x8_0_s_axi_arready(ext_axis_tproc64x32_x8_0_s_axi_arready),
        .ext_axis_tproc64x32_x8_0_s_axi_arvalid(ext_axis_tproc64x32_x8_0_s_axi_arvalid),
        .ext_axis_tproc64x32_x8_0_s_axi_awaddr(ext_axis_tproc64x32_x8_0_s_axi_awaddr),
        .ext_axis_tproc64x32_x8_0_s_axi_awprot(ext_axis_tproc64x32_x8_0_s_axi_awprot),
        .ext_axis_tproc64x32_x8_0_s_axi_awready(ext_axis_tproc64x32_x8_0_s_axi_awready),
        .ext_axis_tproc64x32_x8_0_s_axi_awvalid(ext_axis_tproc64x32_x8_0_s_axi_awvalid),
        .ext_axis_tproc64x32_x8_0_s_axi_bready(ext_axis_tproc64x32_x8_0_s_axi_bready),
        .ext_axis_tproc64x32_x8_0_s_axi_bresp(ext_axis_tproc64x32_x8_0_s_axi_bresp),
        .ext_axis_tproc64x32_x8_0_s_axi_bvalid(ext_axis_tproc64x32_x8_0_s_axi_bvalid),
        .ext_axis_tproc64x32_x8_0_s_axi_rdata(ext_axis_tproc64x32_x8_0_s_axi_rdata),
        .ext_axis_tproc64x32_x8_0_s_axi_rready(ext_axis_tproc64x32_x8_0_s_axi_rready),
        .ext_axis_tproc64x32_x8_0_s_axi_rresp(ext_axis_tproc64x32_x8_0_s_axi_rresp),
        .ext_axis_tproc64x32_x8_0_s_axi_rvalid(ext_axis_tproc64x32_x8_0_s_axi_rvalid),
        .ext_axis_tproc64x32_x8_0_s_axi_wdata(ext_axis_tproc64x32_x8_0_s_axi_wdata),
        .ext_axis_tproc64x32_x8_0_s_axi_wready(ext_axis_tproc64x32_x8_0_s_axi_wready),
        .ext_axis_tproc64x32_x8_0_s_axi_wstrb(ext_axis_tproc64x32_x8_0_s_axi_wstrb),
        .ext_axis_tproc64x32_x8_0_s_axi_wvalid(ext_axis_tproc64x32_x8_0_s_axi_wvalid),
        .ext_axis_tproc64x32_x8_0_start(ext_axis_tproc64x32_x8_0_start),
        .ext_c_shift_ram_0_D(ext_c_shift_ram_0_D),
        .ext_c_shift_ram_0_Q(ext_c_shift_ram_0_Q),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awaddr(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awaddr),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awburst(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awburst),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awcache(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awcache),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awid(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awid),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlen(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlen),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlock(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlock),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awprot(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awprot),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awqos(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awqos),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awready(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awready),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awregion(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awregion),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awsize(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awsize),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awvalid(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awvalid),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bid(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bid),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bready(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bready),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bresp(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bresp),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bvalid(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bvalid),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wdata(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wdata),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wlast(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wlast),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wready(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wready),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wstrb(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wstrb),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wvalid(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wvalid),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_araddr(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_araddr),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arprot(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arprot),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arready(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arready),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arvalid(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arvalid),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awaddr(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awaddr),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awprot(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awprot),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awready(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awready),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awvalid(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awvalid),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bready(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bready),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bresp(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bresp),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bvalid(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bvalid),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rdata(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rdata),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rready(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rready),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rresp(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rresp),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rvalid(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rvalid),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wdata(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wdata),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wready(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wready),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wstrb(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wstrb),
        .ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wvalid(ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wvalid),
        .ext_ddr4_axis_fir_decim_300to1_v2_0_capture_trigger(ext_ddr4_axis_fir_decim_300to1_v2_0_capture_trigger),
        .ext_mr_buffer_et_0_m00_axis_tdata(ext_mr_buffer_et_0_m00_axis_tdata),
        .ext_mr_buffer_et_0_m00_axis_tlast(ext_mr_buffer_et_0_m00_axis_tlast),
        .ext_mr_buffer_et_0_m00_axis_tready(ext_mr_buffer_et_0_m00_axis_tready),
        .ext_mr_buffer_et_0_m00_axis_tstrb(ext_mr_buffer_et_0_m00_axis_tstrb),
        .ext_mr_buffer_et_0_m00_axis_tvalid(ext_mr_buffer_et_0_m00_axis_tvalid),
        .ext_mr_buffer_et_0_s00_axi_araddr(ext_mr_buffer_et_0_s00_axi_araddr),
        .ext_mr_buffer_et_0_s00_axi_arprot(ext_mr_buffer_et_0_s00_axi_arprot),
        .ext_mr_buffer_et_0_s00_axi_arready(ext_mr_buffer_et_0_s00_axi_arready),
        .ext_mr_buffer_et_0_s00_axi_arvalid(ext_mr_buffer_et_0_s00_axi_arvalid),
        .ext_mr_buffer_et_0_s00_axi_awaddr(ext_mr_buffer_et_0_s00_axi_awaddr),
        .ext_mr_buffer_et_0_s00_axi_awprot(ext_mr_buffer_et_0_s00_axi_awprot),
        .ext_mr_buffer_et_0_s00_axi_awready(ext_mr_buffer_et_0_s00_axi_awready),
        .ext_mr_buffer_et_0_s00_axi_awvalid(ext_mr_buffer_et_0_s00_axi_awvalid),
        .ext_mr_buffer_et_0_s00_axi_bready(ext_mr_buffer_et_0_s00_axi_bready),
        .ext_mr_buffer_et_0_s00_axi_bresp(ext_mr_buffer_et_0_s00_axi_bresp),
        .ext_mr_buffer_et_0_s00_axi_bvalid(ext_mr_buffer_et_0_s00_axi_bvalid),
        .ext_mr_buffer_et_0_s00_axi_rdata(ext_mr_buffer_et_0_s00_axi_rdata),
        .ext_mr_buffer_et_0_s00_axi_rready(ext_mr_buffer_et_0_s00_axi_rready),
        .ext_mr_buffer_et_0_s00_axi_rresp(ext_mr_buffer_et_0_s00_axi_rresp),
        .ext_mr_buffer_et_0_s00_axi_rvalid(ext_mr_buffer_et_0_s00_axi_rvalid),
        .ext_mr_buffer_et_0_s00_axi_wdata(ext_mr_buffer_et_0_s00_axi_wdata),
        .ext_mr_buffer_et_0_s00_axi_wready(ext_mr_buffer_et_0_s00_axi_wready),
        .ext_mr_buffer_et_0_s00_axi_wstrb(ext_mr_buffer_et_0_s00_axi_wstrb),
        .ext_mr_buffer_et_0_s00_axi_wvalid(ext_mr_buffer_et_0_s00_axi_wvalid),
        .ext_qick_vec2bit_0_dout0(ext_qick_vec2bit_0_dout0),
        .ext_qick_vec2bit_0_dout1(ext_qick_vec2bit_0_dout1),
        .ext_qick_vec2bit_0_dout2(ext_qick_vec2bit_0_dout2),
        .ext_qick_vec2bit_0_dout3(ext_qick_vec2bit_0_dout3),
        .ext_qick_vec2bit_0_dout4(ext_qick_vec2bit_0_dout4),
        .ext_qick_vec2bit_0_dout5(ext_qick_vec2bit_0_dout5),
        .ext_qick_vec2bit_0_dout6(ext_qick_vec2bit_0_dout6),
        .ext_xlconstant_0_dout(ext_xlconstant_0_dout),
        .ext_xlconstant_1_dout(ext_xlconstant_1_dout),
        .ext_xlconstant_2_dout(ext_xlconstant_2_dout),
        .ext_xlconstant_3_dout(ext_xlconstant_3_dout),
        .ext_xlconstant_4_dout(ext_xlconstant_4_dout),
        .resetn(resetn));
endmodule
