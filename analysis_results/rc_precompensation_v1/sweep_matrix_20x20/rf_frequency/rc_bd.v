//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//Copyright 2022-2023 Advanced Micro Devices, Inc. All Rights Reserved.
//--------------------------------------------------------------------------------
//Tool Version: Vivado v.2023.1 (win64) Build 3865809 Sun May  7 15:05:29 MDT 2023
//Date        : Wed Sep 23 08:35:01 2026
//Host        : DESKTOP-SU4R45B running 64-bit major release  (build 9200)
//Command     : generate_target sim_bd.bd
//Design      : sim_bd
//Purpose     : IP block netlist
//--------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* CORE_GENERATION_INFO = "sim_bd,IP_Integrator,{x_ipVendor=xilinx.com,x_ipLibrary=BlockDiagram,x_ipName=sim_bd,x_ipVersion=1.00.a,x_ipLanguage=VERILOG,numBlks=78,numReposBlks=78,numNonXlnxBlks=46,numHierBlks=0,maxHierDepth=0,numSysgenBlks=0,numHlsBlks=0,numHdlrefBlks=0,numPkgbdBlks=0,bdsource=USER,synth_mode=OOC_per_IP}" *) (* HW_HANDOFF = "sim_bd.hwdef" *) 
module rc_bd
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
  (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 CLK.CLK_300000000 CLK" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME CLK.CLK_300000000, ASSOCIATED_BUSIF ext_axis_dyn_readout_v1_0_s1_axis:ext_axis_dyn_readout_v1_1_s1_axis:ext_axis_dyn_readout_v1_2_s1_axis:ext_axis_dyn_readout_v1_3_s1_axis:ext_axis_register_slice_0_m_axis:ext_axis_register_slice_1_m_axis:ext_axis_register_slice_10_m_axis:ext_axis_register_slice_11_m_axis:ext_axis_register_slice_12_m_axis:ext_axis_register_slice_13_m_axis:ext_axis_register_slice_14_m_axis:ext_axis_register_slice_15_m_axis:ext_axis_register_slice_16_m_axis:ext_axis_register_slice_2_m_axis:ext_axis_register_slice_3_m_axis:ext_axis_register_slice_8_m_axis, ASSOCIATED_RESET resetn, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, FREQ_TOLERANCE_HZ 0, INSERT_VIP 0, PHASE 0.0" *) input clk_300000000;
  (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 CLK.CLK_333250000 CLK" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME CLK.CLK_333250000, ASSOCIATED_BUSIF ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi, ASSOCIATED_RESET resetn, CLK_DOMAIN sim_bd_clk_333250000, FREQ_HZ 333250000, FREQ_TOLERANCE_HZ 0, INSERT_VIP 0, PHASE 0.0" *) input clk_333250000;
  (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 CLK.CLK_99999985 CLK" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME CLK.CLK_99999985, ASSOCIATED_BUSIF ext_axis_awg_tuning_v1_10_s_axi:ext_axis_awg_tuning_v1_11_s_axi:ext_axis_awg_tuning_v1_4_s_axi:ext_axis_awg_tuning_v1_5_s_axi:ext_axis_awg_tuning_v1_6_s_axi:ext_axis_awg_tuning_v1_8_s_axi:ext_axis_awg_tuning_v1_9_s_axi:ext_axis_signal_gen_v6_0_s_axi:ext_axis_signal_gen_v6_1_s_axi:ext_axis_signal_gen_v6_2_s_axi:ext_axis_signal_gen_v6_3_s_axi:ext_axis_square_pulse_v1_0_s_axi:ext_axis_switch_avg_M00_AXIS:ext_axis_switch_avg_S_AXI_CTRL:ext_axis_switch_buf_M00_AXIS:ext_axis_switch_buf_S_AXI_CTRL:ext_axis_switch_ddr_S_AXI_CTRL:ext_axis_switch_gen_S00_AXIS:ext_axis_switch_gen_M04_AXIS:ext_axis_switch_gen_M05_AXIS:ext_axis_switch_gen_M06_AXIS:ext_axis_switch_gen_M07_AXIS:ext_axis_switch_gen_M08_AXIS:ext_axis_switch_gen_M09_AXIS:ext_axis_switch_gen_M10_AXIS:ext_axis_switch_gen_M11_AXIS:ext_axis_switch_gen_S_AXI_CTRL:ext_axis_switch_mr_S_AXI_CTRL:ext_axis_tproc64x32_x8_0_m0_axis:ext_axis_tproc64x32_x8_0_s0_axis:ext_axis_tproc64x32_x8_0_s_axi:ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi:ext_mr_buffer_et_0_m00_axis:ext_mr_buffer_et_0_s00_axi:ext_axis_avg_buffer_0_s_axi:ext_axis_avg_buffer_1_s_axi:ext_axis_avg_buffer_2_s_axi:ext_axis_avg_buffer_3_s_axi, ASSOCIATED_RESET resetn, CLK_DOMAIN sim_bd_clk_99999985, FREQ_HZ 99999985, FREQ_TOLERANCE_HZ 0, INSERT_VIP 0, PHASE 0.0" *) input clk_99999985;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_avg_buffer_0_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_avg_buffer_0_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi ARPROT" *) input [2:0]ext_axis_avg_buffer_0_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi ARREADY" *) output ext_axis_avg_buffer_0_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi ARVALID" *) input ext_axis_avg_buffer_0_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi AWADDR" *) input [5:0]ext_axis_avg_buffer_0_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi AWPROT" *) input [2:0]ext_axis_avg_buffer_0_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi AWREADY" *) output ext_axis_avg_buffer_0_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi AWVALID" *) input ext_axis_avg_buffer_0_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi BREADY" *) input ext_axis_avg_buffer_0_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi BRESP" *) output [1:0]ext_axis_avg_buffer_0_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi BVALID" *) output ext_axis_avg_buffer_0_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi RDATA" *) output [31:0]ext_axis_avg_buffer_0_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi RREADY" *) input ext_axis_avg_buffer_0_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi RRESP" *) output [1:0]ext_axis_avg_buffer_0_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi RVALID" *) output ext_axis_avg_buffer_0_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi WDATA" *) input [31:0]ext_axis_avg_buffer_0_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi WREADY" *) output ext_axis_avg_buffer_0_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi WSTRB" *) input [3:0]ext_axis_avg_buffer_0_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_0_s_axi WVALID" *) input ext_axis_avg_buffer_0_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_avg_buffer_1_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_avg_buffer_1_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi ARPROT" *) input [2:0]ext_axis_avg_buffer_1_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi ARREADY" *) output ext_axis_avg_buffer_1_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi ARVALID" *) input ext_axis_avg_buffer_1_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi AWADDR" *) input [5:0]ext_axis_avg_buffer_1_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi AWPROT" *) input [2:0]ext_axis_avg_buffer_1_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi AWREADY" *) output ext_axis_avg_buffer_1_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi AWVALID" *) input ext_axis_avg_buffer_1_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi BREADY" *) input ext_axis_avg_buffer_1_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi BRESP" *) output [1:0]ext_axis_avg_buffer_1_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi BVALID" *) output ext_axis_avg_buffer_1_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi RDATA" *) output [31:0]ext_axis_avg_buffer_1_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi RREADY" *) input ext_axis_avg_buffer_1_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi RRESP" *) output [1:0]ext_axis_avg_buffer_1_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi RVALID" *) output ext_axis_avg_buffer_1_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi WDATA" *) input [31:0]ext_axis_avg_buffer_1_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi WREADY" *) output ext_axis_avg_buffer_1_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi WSTRB" *) input [3:0]ext_axis_avg_buffer_1_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_1_s_axi WVALID" *) input ext_axis_avg_buffer_1_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_avg_buffer_2_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_avg_buffer_2_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi ARPROT" *) input [2:0]ext_axis_avg_buffer_2_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi ARREADY" *) output ext_axis_avg_buffer_2_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi ARVALID" *) input ext_axis_avg_buffer_2_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi AWADDR" *) input [5:0]ext_axis_avg_buffer_2_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi AWPROT" *) input [2:0]ext_axis_avg_buffer_2_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi AWREADY" *) output ext_axis_avg_buffer_2_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi AWVALID" *) input ext_axis_avg_buffer_2_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi BREADY" *) input ext_axis_avg_buffer_2_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi BRESP" *) output [1:0]ext_axis_avg_buffer_2_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi BVALID" *) output ext_axis_avg_buffer_2_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi RDATA" *) output [31:0]ext_axis_avg_buffer_2_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi RREADY" *) input ext_axis_avg_buffer_2_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi RRESP" *) output [1:0]ext_axis_avg_buffer_2_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi RVALID" *) output ext_axis_avg_buffer_2_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi WDATA" *) input [31:0]ext_axis_avg_buffer_2_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi WREADY" *) output ext_axis_avg_buffer_2_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi WSTRB" *) input [3:0]ext_axis_avg_buffer_2_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_2_s_axi WVALID" *) input ext_axis_avg_buffer_2_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_avg_buffer_3_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_avg_buffer_3_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi ARPROT" *) input [2:0]ext_axis_avg_buffer_3_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi ARREADY" *) output ext_axis_avg_buffer_3_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi ARVALID" *) input ext_axis_avg_buffer_3_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi AWADDR" *) input [5:0]ext_axis_avg_buffer_3_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi AWPROT" *) input [2:0]ext_axis_avg_buffer_3_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi AWREADY" *) output ext_axis_avg_buffer_3_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi AWVALID" *) input ext_axis_avg_buffer_3_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi BREADY" *) input ext_axis_avg_buffer_3_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi BRESP" *) output [1:0]ext_axis_avg_buffer_3_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi BVALID" *) output ext_axis_avg_buffer_3_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi RDATA" *) output [31:0]ext_axis_avg_buffer_3_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi RREADY" *) input ext_axis_avg_buffer_3_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi RRESP" *) output [1:0]ext_axis_avg_buffer_3_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi RVALID" *) output ext_axis_avg_buffer_3_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi WDATA" *) input [31:0]ext_axis_avg_buffer_3_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi WREADY" *) output ext_axis_avg_buffer_3_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi WSTRB" *) input [3:0]ext_axis_avg_buffer_3_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_avg_buffer_3_s_axi WVALID" *) input ext_axis_avg_buffer_3_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_awg_tuning_v1_10_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_awg_tuning_v1_10_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi ARPROT" *) input [2:0]ext_axis_awg_tuning_v1_10_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi ARREADY" *) output ext_axis_awg_tuning_v1_10_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi ARVALID" *) input ext_axis_awg_tuning_v1_10_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi AWADDR" *) input [5:0]ext_axis_awg_tuning_v1_10_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi AWPROT" *) input [2:0]ext_axis_awg_tuning_v1_10_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi AWREADY" *) output ext_axis_awg_tuning_v1_10_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi AWVALID" *) input ext_axis_awg_tuning_v1_10_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi BREADY" *) input ext_axis_awg_tuning_v1_10_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi BRESP" *) output [1:0]ext_axis_awg_tuning_v1_10_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi BVALID" *) output ext_axis_awg_tuning_v1_10_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi RDATA" *) output [31:0]ext_axis_awg_tuning_v1_10_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi RREADY" *) input ext_axis_awg_tuning_v1_10_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi RRESP" *) output [1:0]ext_axis_awg_tuning_v1_10_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi RVALID" *) output ext_axis_awg_tuning_v1_10_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi WDATA" *) input [31:0]ext_axis_awg_tuning_v1_10_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi WREADY" *) output ext_axis_awg_tuning_v1_10_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi WSTRB" *) input [3:0]ext_axis_awg_tuning_v1_10_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_10_s_axi WVALID" *) input ext_axis_awg_tuning_v1_10_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_awg_tuning_v1_11_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_awg_tuning_v1_11_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi ARPROT" *) input [2:0]ext_axis_awg_tuning_v1_11_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi ARREADY" *) output ext_axis_awg_tuning_v1_11_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi ARVALID" *) input ext_axis_awg_tuning_v1_11_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi AWADDR" *) input [5:0]ext_axis_awg_tuning_v1_11_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi AWPROT" *) input [2:0]ext_axis_awg_tuning_v1_11_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi AWREADY" *) output ext_axis_awg_tuning_v1_11_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi AWVALID" *) input ext_axis_awg_tuning_v1_11_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi BREADY" *) input ext_axis_awg_tuning_v1_11_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi BRESP" *) output [1:0]ext_axis_awg_tuning_v1_11_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi BVALID" *) output ext_axis_awg_tuning_v1_11_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi RDATA" *) output [31:0]ext_axis_awg_tuning_v1_11_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi RREADY" *) input ext_axis_awg_tuning_v1_11_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi RRESP" *) output [1:0]ext_axis_awg_tuning_v1_11_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi RVALID" *) output ext_axis_awg_tuning_v1_11_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi WDATA" *) input [31:0]ext_axis_awg_tuning_v1_11_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi WREADY" *) output ext_axis_awg_tuning_v1_11_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi WSTRB" *) input [3:0]ext_axis_awg_tuning_v1_11_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_11_s_axi WVALID" *) input ext_axis_awg_tuning_v1_11_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_awg_tuning_v1_4_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_awg_tuning_v1_4_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi ARPROT" *) input [2:0]ext_axis_awg_tuning_v1_4_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi ARREADY" *) output ext_axis_awg_tuning_v1_4_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi ARVALID" *) input ext_axis_awg_tuning_v1_4_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi AWADDR" *) input [5:0]ext_axis_awg_tuning_v1_4_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi AWPROT" *) input [2:0]ext_axis_awg_tuning_v1_4_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi AWREADY" *) output ext_axis_awg_tuning_v1_4_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi AWVALID" *) input ext_axis_awg_tuning_v1_4_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi BREADY" *) input ext_axis_awg_tuning_v1_4_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi BRESP" *) output [1:0]ext_axis_awg_tuning_v1_4_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi BVALID" *) output ext_axis_awg_tuning_v1_4_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi RDATA" *) output [31:0]ext_axis_awg_tuning_v1_4_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi RREADY" *) input ext_axis_awg_tuning_v1_4_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi RRESP" *) output [1:0]ext_axis_awg_tuning_v1_4_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi RVALID" *) output ext_axis_awg_tuning_v1_4_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi WDATA" *) input [31:0]ext_axis_awg_tuning_v1_4_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi WREADY" *) output ext_axis_awg_tuning_v1_4_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi WSTRB" *) input [3:0]ext_axis_awg_tuning_v1_4_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_4_s_axi WVALID" *) input ext_axis_awg_tuning_v1_4_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_awg_tuning_v1_5_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_awg_tuning_v1_5_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi ARPROT" *) input [2:0]ext_axis_awg_tuning_v1_5_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi ARREADY" *) output ext_axis_awg_tuning_v1_5_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi ARVALID" *) input ext_axis_awg_tuning_v1_5_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi AWADDR" *) input [5:0]ext_axis_awg_tuning_v1_5_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi AWPROT" *) input [2:0]ext_axis_awg_tuning_v1_5_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi AWREADY" *) output ext_axis_awg_tuning_v1_5_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi AWVALID" *) input ext_axis_awg_tuning_v1_5_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi BREADY" *) input ext_axis_awg_tuning_v1_5_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi BRESP" *) output [1:0]ext_axis_awg_tuning_v1_5_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi BVALID" *) output ext_axis_awg_tuning_v1_5_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi RDATA" *) output [31:0]ext_axis_awg_tuning_v1_5_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi RREADY" *) input ext_axis_awg_tuning_v1_5_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi RRESP" *) output [1:0]ext_axis_awg_tuning_v1_5_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi RVALID" *) output ext_axis_awg_tuning_v1_5_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi WDATA" *) input [31:0]ext_axis_awg_tuning_v1_5_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi WREADY" *) output ext_axis_awg_tuning_v1_5_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi WSTRB" *) input [3:0]ext_axis_awg_tuning_v1_5_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_5_s_axi WVALID" *) input ext_axis_awg_tuning_v1_5_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_awg_tuning_v1_6_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_awg_tuning_v1_6_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi ARPROT" *) input [2:0]ext_axis_awg_tuning_v1_6_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi ARREADY" *) output ext_axis_awg_tuning_v1_6_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi ARVALID" *) input ext_axis_awg_tuning_v1_6_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi AWADDR" *) input [5:0]ext_axis_awg_tuning_v1_6_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi AWPROT" *) input [2:0]ext_axis_awg_tuning_v1_6_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi AWREADY" *) output ext_axis_awg_tuning_v1_6_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi AWVALID" *) input ext_axis_awg_tuning_v1_6_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi BREADY" *) input ext_axis_awg_tuning_v1_6_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi BRESP" *) output [1:0]ext_axis_awg_tuning_v1_6_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi BVALID" *) output ext_axis_awg_tuning_v1_6_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi RDATA" *) output [31:0]ext_axis_awg_tuning_v1_6_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi RREADY" *) input ext_axis_awg_tuning_v1_6_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi RRESP" *) output [1:0]ext_axis_awg_tuning_v1_6_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi RVALID" *) output ext_axis_awg_tuning_v1_6_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi WDATA" *) input [31:0]ext_axis_awg_tuning_v1_6_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi WREADY" *) output ext_axis_awg_tuning_v1_6_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi WSTRB" *) input [3:0]ext_axis_awg_tuning_v1_6_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_6_s_axi WVALID" *) input ext_axis_awg_tuning_v1_6_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_awg_tuning_v1_8_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_awg_tuning_v1_8_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi ARPROT" *) input [2:0]ext_axis_awg_tuning_v1_8_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi ARREADY" *) output ext_axis_awg_tuning_v1_8_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi ARVALID" *) input ext_axis_awg_tuning_v1_8_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi AWADDR" *) input [5:0]ext_axis_awg_tuning_v1_8_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi AWPROT" *) input [2:0]ext_axis_awg_tuning_v1_8_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi AWREADY" *) output ext_axis_awg_tuning_v1_8_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi AWVALID" *) input ext_axis_awg_tuning_v1_8_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi BREADY" *) input ext_axis_awg_tuning_v1_8_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi BRESP" *) output [1:0]ext_axis_awg_tuning_v1_8_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi BVALID" *) output ext_axis_awg_tuning_v1_8_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi RDATA" *) output [31:0]ext_axis_awg_tuning_v1_8_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi RREADY" *) input ext_axis_awg_tuning_v1_8_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi RRESP" *) output [1:0]ext_axis_awg_tuning_v1_8_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi RVALID" *) output ext_axis_awg_tuning_v1_8_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi WDATA" *) input [31:0]ext_axis_awg_tuning_v1_8_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi WREADY" *) output ext_axis_awg_tuning_v1_8_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi WSTRB" *) input [3:0]ext_axis_awg_tuning_v1_8_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_8_s_axi WVALID" *) input ext_axis_awg_tuning_v1_8_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_awg_tuning_v1_9_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_awg_tuning_v1_9_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi ARPROT" *) input [2:0]ext_axis_awg_tuning_v1_9_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi ARREADY" *) output ext_axis_awg_tuning_v1_9_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi ARVALID" *) input ext_axis_awg_tuning_v1_9_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi AWADDR" *) input [5:0]ext_axis_awg_tuning_v1_9_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi AWPROT" *) input [2:0]ext_axis_awg_tuning_v1_9_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi AWREADY" *) output ext_axis_awg_tuning_v1_9_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi AWVALID" *) input ext_axis_awg_tuning_v1_9_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi BREADY" *) input ext_axis_awg_tuning_v1_9_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi BRESP" *) output [1:0]ext_axis_awg_tuning_v1_9_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi BVALID" *) output ext_axis_awg_tuning_v1_9_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi RDATA" *) output [31:0]ext_axis_awg_tuning_v1_9_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi RREADY" *) input ext_axis_awg_tuning_v1_9_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi RRESP" *) output [1:0]ext_axis_awg_tuning_v1_9_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi RVALID" *) output ext_axis_awg_tuning_v1_9_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi WDATA" *) input [31:0]ext_axis_awg_tuning_v1_9_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi WREADY" *) output ext_axis_awg_tuning_v1_9_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi WSTRB" *) input [3:0]ext_axis_awg_tuning_v1_9_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_awg_tuning_v1_9_s_axi WVALID" *) input ext_axis_awg_tuning_v1_9_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_dyn_readout_v1_0_s1_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_dyn_readout_v1_0_s1_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 16, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) input [127:0]ext_axis_dyn_readout_v1_0_s1_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_dyn_readout_v1_0_s1_axis TREADY" *) output ext_axis_dyn_readout_v1_0_s1_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_dyn_readout_v1_0_s1_axis TVALID" *) input ext_axis_dyn_readout_v1_0_s1_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_dyn_readout_v1_1_s1_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_dyn_readout_v1_1_s1_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 16, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) input [127:0]ext_axis_dyn_readout_v1_1_s1_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_dyn_readout_v1_1_s1_axis TREADY" *) output ext_axis_dyn_readout_v1_1_s1_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_dyn_readout_v1_1_s1_axis TVALID" *) input ext_axis_dyn_readout_v1_1_s1_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_dyn_readout_v1_2_s1_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_dyn_readout_v1_2_s1_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 16, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) input [127:0]ext_axis_dyn_readout_v1_2_s1_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_dyn_readout_v1_2_s1_axis TREADY" *) output ext_axis_dyn_readout_v1_2_s1_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_dyn_readout_v1_2_s1_axis TVALID" *) input ext_axis_dyn_readout_v1_2_s1_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_dyn_readout_v1_3_s1_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_dyn_readout_v1_3_s1_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 16, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) input [127:0]ext_axis_dyn_readout_v1_3_s1_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_dyn_readout_v1_3_s1_axis TREADY" *) output ext_axis_dyn_readout_v1_3_s1_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_dyn_readout_v1_3_s1_axis TVALID" *) input ext_axis_dyn_readout_v1_3_s1_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_0_m_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_register_slice_0_m_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 32, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [255:0]ext_axis_register_slice_0_m_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_0_m_axis TREADY" *) input ext_axis_register_slice_0_m_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_0_m_axis TVALID" *) output ext_axis_register_slice_0_m_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_10_m_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_register_slice_10_m_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 32, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [255:0]ext_axis_register_slice_10_m_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_10_m_axis TREADY" *) input ext_axis_register_slice_10_m_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_10_m_axis TVALID" *) output ext_axis_register_slice_10_m_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_11_m_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_register_slice_11_m_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 32, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [255:0]ext_axis_register_slice_11_m_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_11_m_axis TREADY" *) input ext_axis_register_slice_11_m_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_11_m_axis TVALID" *) output ext_axis_register_slice_11_m_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_12_m_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_register_slice_12_m_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 32, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [255:0]ext_axis_register_slice_12_m_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_12_m_axis TREADY" *) input ext_axis_register_slice_12_m_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_12_m_axis TVALID" *) output ext_axis_register_slice_12_m_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_13_m_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_register_slice_13_m_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 32, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [255:0]ext_axis_register_slice_13_m_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_13_m_axis TREADY" *) input ext_axis_register_slice_13_m_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_13_m_axis TVALID" *) output ext_axis_register_slice_13_m_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_14_m_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_register_slice_14_m_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 32, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [255:0]ext_axis_register_slice_14_m_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_14_m_axis TREADY" *) input ext_axis_register_slice_14_m_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_14_m_axis TVALID" *) output ext_axis_register_slice_14_m_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_15_m_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_register_slice_15_m_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 32, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [255:0]ext_axis_register_slice_15_m_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_15_m_axis TREADY" *) input ext_axis_register_slice_15_m_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_15_m_axis TVALID" *) output ext_axis_register_slice_15_m_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_16_m_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_register_slice_16_m_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 32, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [255:0]ext_axis_register_slice_16_m_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_16_m_axis TREADY" *) input ext_axis_register_slice_16_m_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_16_m_axis TVALID" *) output ext_axis_register_slice_16_m_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_1_m_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_register_slice_1_m_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 32, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [255:0]ext_axis_register_slice_1_m_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_1_m_axis TREADY" *) input ext_axis_register_slice_1_m_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_1_m_axis TVALID" *) output ext_axis_register_slice_1_m_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_2_m_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_register_slice_2_m_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 32, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [255:0]ext_axis_register_slice_2_m_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_2_m_axis TREADY" *) input ext_axis_register_slice_2_m_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_2_m_axis TVALID" *) output ext_axis_register_slice_2_m_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_3_m_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_register_slice_3_m_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 32, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [255:0]ext_axis_register_slice_3_m_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_3_m_axis TREADY" *) input ext_axis_register_slice_3_m_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_3_m_axis TVALID" *) output ext_axis_register_slice_3_m_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_8_m_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_register_slice_8_m_axis, CLK_DOMAIN sim_bd_clk_300000000, FREQ_HZ 300000000, HAS_TKEEP 0, HAS_TLAST 0, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 32, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [255:0]ext_axis_register_slice_8_m_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_8_m_axis TREADY" *) input ext_axis_register_slice_8_m_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_register_slice_8_m_axis TVALID" *) output ext_axis_register_slice_8_m_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_signal_gen_v6_0_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_signal_gen_v6_0_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi ARPROT" *) input [2:0]ext_axis_signal_gen_v6_0_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi ARREADY" *) output ext_axis_signal_gen_v6_0_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi ARVALID" *) input ext_axis_signal_gen_v6_0_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi AWADDR" *) input [5:0]ext_axis_signal_gen_v6_0_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi AWPROT" *) input [2:0]ext_axis_signal_gen_v6_0_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi AWREADY" *) output ext_axis_signal_gen_v6_0_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi AWVALID" *) input ext_axis_signal_gen_v6_0_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi BREADY" *) input ext_axis_signal_gen_v6_0_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi BRESP" *) output [1:0]ext_axis_signal_gen_v6_0_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi BVALID" *) output ext_axis_signal_gen_v6_0_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi RDATA" *) output [31:0]ext_axis_signal_gen_v6_0_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi RREADY" *) input ext_axis_signal_gen_v6_0_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi RRESP" *) output [1:0]ext_axis_signal_gen_v6_0_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi RVALID" *) output ext_axis_signal_gen_v6_0_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi WDATA" *) input [31:0]ext_axis_signal_gen_v6_0_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi WREADY" *) output ext_axis_signal_gen_v6_0_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi WSTRB" *) input [3:0]ext_axis_signal_gen_v6_0_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_0_s_axi WVALID" *) input ext_axis_signal_gen_v6_0_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_signal_gen_v6_1_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_signal_gen_v6_1_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi ARPROT" *) input [2:0]ext_axis_signal_gen_v6_1_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi ARREADY" *) output ext_axis_signal_gen_v6_1_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi ARVALID" *) input ext_axis_signal_gen_v6_1_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi AWADDR" *) input [5:0]ext_axis_signal_gen_v6_1_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi AWPROT" *) input [2:0]ext_axis_signal_gen_v6_1_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi AWREADY" *) output ext_axis_signal_gen_v6_1_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi AWVALID" *) input ext_axis_signal_gen_v6_1_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi BREADY" *) input ext_axis_signal_gen_v6_1_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi BRESP" *) output [1:0]ext_axis_signal_gen_v6_1_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi BVALID" *) output ext_axis_signal_gen_v6_1_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi RDATA" *) output [31:0]ext_axis_signal_gen_v6_1_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi RREADY" *) input ext_axis_signal_gen_v6_1_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi RRESP" *) output [1:0]ext_axis_signal_gen_v6_1_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi RVALID" *) output ext_axis_signal_gen_v6_1_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi WDATA" *) input [31:0]ext_axis_signal_gen_v6_1_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi WREADY" *) output ext_axis_signal_gen_v6_1_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi WSTRB" *) input [3:0]ext_axis_signal_gen_v6_1_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_1_s_axi WVALID" *) input ext_axis_signal_gen_v6_1_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_signal_gen_v6_2_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_signal_gen_v6_2_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi ARPROT" *) input [2:0]ext_axis_signal_gen_v6_2_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi ARREADY" *) output ext_axis_signal_gen_v6_2_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi ARVALID" *) input ext_axis_signal_gen_v6_2_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi AWADDR" *) input [5:0]ext_axis_signal_gen_v6_2_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi AWPROT" *) input [2:0]ext_axis_signal_gen_v6_2_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi AWREADY" *) output ext_axis_signal_gen_v6_2_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi AWVALID" *) input ext_axis_signal_gen_v6_2_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi BREADY" *) input ext_axis_signal_gen_v6_2_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi BRESP" *) output [1:0]ext_axis_signal_gen_v6_2_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi BVALID" *) output ext_axis_signal_gen_v6_2_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi RDATA" *) output [31:0]ext_axis_signal_gen_v6_2_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi RREADY" *) input ext_axis_signal_gen_v6_2_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi RRESP" *) output [1:0]ext_axis_signal_gen_v6_2_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi RVALID" *) output ext_axis_signal_gen_v6_2_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi WDATA" *) input [31:0]ext_axis_signal_gen_v6_2_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi WREADY" *) output ext_axis_signal_gen_v6_2_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi WSTRB" *) input [3:0]ext_axis_signal_gen_v6_2_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_2_s_axi WVALID" *) input ext_axis_signal_gen_v6_2_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_signal_gen_v6_3_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_signal_gen_v6_3_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi ARPROT" *) input [2:0]ext_axis_signal_gen_v6_3_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi ARREADY" *) output ext_axis_signal_gen_v6_3_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi ARVALID" *) input ext_axis_signal_gen_v6_3_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi AWADDR" *) input [5:0]ext_axis_signal_gen_v6_3_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi AWPROT" *) input [2:0]ext_axis_signal_gen_v6_3_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi AWREADY" *) output ext_axis_signal_gen_v6_3_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi AWVALID" *) input ext_axis_signal_gen_v6_3_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi BREADY" *) input ext_axis_signal_gen_v6_3_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi BRESP" *) output [1:0]ext_axis_signal_gen_v6_3_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi BVALID" *) output ext_axis_signal_gen_v6_3_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi RDATA" *) output [31:0]ext_axis_signal_gen_v6_3_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi RREADY" *) input ext_axis_signal_gen_v6_3_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi RRESP" *) output [1:0]ext_axis_signal_gen_v6_3_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi RVALID" *) output ext_axis_signal_gen_v6_3_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi WDATA" *) input [31:0]ext_axis_signal_gen_v6_3_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi WREADY" *) output ext_axis_signal_gen_v6_3_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi WSTRB" *) input [3:0]ext_axis_signal_gen_v6_3_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_signal_gen_v6_3_s_axi WVALID" *) input ext_axis_signal_gen_v6_3_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_square_pulse_v1_0_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_axis_square_pulse_v1_0_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi ARPROT" *) input [2:0]ext_axis_square_pulse_v1_0_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi ARREADY" *) output ext_axis_square_pulse_v1_0_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi ARVALID" *) input ext_axis_square_pulse_v1_0_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi AWADDR" *) input [5:0]ext_axis_square_pulse_v1_0_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi AWPROT" *) input [2:0]ext_axis_square_pulse_v1_0_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi AWREADY" *) output ext_axis_square_pulse_v1_0_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi AWVALID" *) input ext_axis_square_pulse_v1_0_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi BREADY" *) input ext_axis_square_pulse_v1_0_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi BRESP" *) output [1:0]ext_axis_square_pulse_v1_0_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi BVALID" *) output ext_axis_square_pulse_v1_0_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi RDATA" *) output [31:0]ext_axis_square_pulse_v1_0_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi RREADY" *) input ext_axis_square_pulse_v1_0_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi RRESP" *) output [1:0]ext_axis_square_pulse_v1_0_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi RVALID" *) output ext_axis_square_pulse_v1_0_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi WDATA" *) input [31:0]ext_axis_square_pulse_v1_0_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi WREADY" *) output ext_axis_square_pulse_v1_0_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi WSTRB" *) input [3:0]ext_axis_square_pulse_v1_0_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_square_pulse_v1_0_s_axi WVALID" *) input ext_axis_square_pulse_v1_0_s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_avg_M00_AXIS TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_avg_M00_AXIS, CLK_DOMAIN sim_bd_clk_99999985, FREQ_HZ 99999985, HAS_TKEEP 0, HAS_TLAST 1, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 8, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [63:0]ext_axis_switch_avg_M00_AXIS_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_avg_M00_AXIS TLAST" *) output [0:0]ext_axis_switch_avg_M00_AXIS_tlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_avg_M00_AXIS TREADY" *) input [0:0]ext_axis_switch_avg_M00_AXIS_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_avg_M00_AXIS TVALID" *) output [0:0]ext_axis_switch_avg_M00_AXIS_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_avg_S_AXI_CTRL, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 0, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 0, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [6:0]ext_axis_switch_avg_S_AXI_CTRL_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL ARREADY" *) output ext_axis_switch_avg_S_AXI_CTRL_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL ARVALID" *) input ext_axis_switch_avg_S_AXI_CTRL_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL AWADDR" *) input [6:0]ext_axis_switch_avg_S_AXI_CTRL_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL AWREADY" *) output ext_axis_switch_avg_S_AXI_CTRL_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL AWVALID" *) input ext_axis_switch_avg_S_AXI_CTRL_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL BREADY" *) input ext_axis_switch_avg_S_AXI_CTRL_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL BRESP" *) output [1:0]ext_axis_switch_avg_S_AXI_CTRL_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL BVALID" *) output ext_axis_switch_avg_S_AXI_CTRL_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL RDATA" *) output [31:0]ext_axis_switch_avg_S_AXI_CTRL_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL RREADY" *) input ext_axis_switch_avg_S_AXI_CTRL_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL RRESP" *) output [1:0]ext_axis_switch_avg_S_AXI_CTRL_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL RVALID" *) output ext_axis_switch_avg_S_AXI_CTRL_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL WDATA" *) input [31:0]ext_axis_switch_avg_S_AXI_CTRL_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL WREADY" *) output ext_axis_switch_avg_S_AXI_CTRL_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_avg_S_AXI_CTRL WVALID" *) input ext_axis_switch_avg_S_AXI_CTRL_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_buf_M00_AXIS TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_buf_M00_AXIS, CLK_DOMAIN sim_bd_clk_99999985, FREQ_HZ 99999985, HAS_TKEEP 0, HAS_TLAST 1, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 4, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [31:0]ext_axis_switch_buf_M00_AXIS_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_buf_M00_AXIS TLAST" *) output [0:0]ext_axis_switch_buf_M00_AXIS_tlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_buf_M00_AXIS TREADY" *) input [0:0]ext_axis_switch_buf_M00_AXIS_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_buf_M00_AXIS TVALID" *) output [0:0]ext_axis_switch_buf_M00_AXIS_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_buf_S_AXI_CTRL, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 0, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 0, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [6:0]ext_axis_switch_buf_S_AXI_CTRL_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL ARREADY" *) output ext_axis_switch_buf_S_AXI_CTRL_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL ARVALID" *) input ext_axis_switch_buf_S_AXI_CTRL_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL AWADDR" *) input [6:0]ext_axis_switch_buf_S_AXI_CTRL_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL AWREADY" *) output ext_axis_switch_buf_S_AXI_CTRL_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL AWVALID" *) input ext_axis_switch_buf_S_AXI_CTRL_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL BREADY" *) input ext_axis_switch_buf_S_AXI_CTRL_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL BRESP" *) output [1:0]ext_axis_switch_buf_S_AXI_CTRL_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL BVALID" *) output ext_axis_switch_buf_S_AXI_CTRL_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL RDATA" *) output [31:0]ext_axis_switch_buf_S_AXI_CTRL_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL RREADY" *) input ext_axis_switch_buf_S_AXI_CTRL_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL RRESP" *) output [1:0]ext_axis_switch_buf_S_AXI_CTRL_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL RVALID" *) output ext_axis_switch_buf_S_AXI_CTRL_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL WDATA" *) input [31:0]ext_axis_switch_buf_S_AXI_CTRL_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL WREADY" *) output ext_axis_switch_buf_S_AXI_CTRL_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_buf_S_AXI_CTRL WVALID" *) input ext_axis_switch_buf_S_AXI_CTRL_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_ddr_S_AXI_CTRL, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 0, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 0, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [6:0]ext_axis_switch_ddr_S_AXI_CTRL_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL ARREADY" *) output ext_axis_switch_ddr_S_AXI_CTRL_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL ARVALID" *) input ext_axis_switch_ddr_S_AXI_CTRL_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL AWADDR" *) input [6:0]ext_axis_switch_ddr_S_AXI_CTRL_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL AWREADY" *) output ext_axis_switch_ddr_S_AXI_CTRL_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL AWVALID" *) input ext_axis_switch_ddr_S_AXI_CTRL_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL BREADY" *) input ext_axis_switch_ddr_S_AXI_CTRL_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL BRESP" *) output [1:0]ext_axis_switch_ddr_S_AXI_CTRL_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL BVALID" *) output ext_axis_switch_ddr_S_AXI_CTRL_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL RDATA" *) output [31:0]ext_axis_switch_ddr_S_AXI_CTRL_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL RREADY" *) input ext_axis_switch_ddr_S_AXI_CTRL_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL RRESP" *) output [1:0]ext_axis_switch_ddr_S_AXI_CTRL_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL RVALID" *) output ext_axis_switch_ddr_S_AXI_CTRL_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL WDATA" *) input [31:0]ext_axis_switch_ddr_S_AXI_CTRL_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL WREADY" *) output ext_axis_switch_ddr_S_AXI_CTRL_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_ddr_S_AXI_CTRL WVALID" *) input ext_axis_switch_ddr_S_AXI_CTRL_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M04_AXIS TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_gen_M04_AXIS, CLK_DOMAIN sim_bd_clk_99999985, FREQ_HZ 99999985, HAS_TKEEP 1, HAS_TLAST 1, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 4, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [31:0]ext_axis_switch_gen_M04_AXIS_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M04_AXIS TKEEP" *) output [3:0]ext_axis_switch_gen_M04_AXIS_tkeep;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M04_AXIS TLAST" *) output [0:0]ext_axis_switch_gen_M04_AXIS_tlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M04_AXIS TREADY" *) input [0:0]ext_axis_switch_gen_M04_AXIS_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M04_AXIS TVALID" *) output [0:0]ext_axis_switch_gen_M04_AXIS_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M05_AXIS TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_gen_M05_AXIS, CLK_DOMAIN sim_bd_clk_99999985, FREQ_HZ 99999985, HAS_TKEEP 1, HAS_TLAST 1, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 4, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [31:0]ext_axis_switch_gen_M05_AXIS_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M05_AXIS TKEEP" *) output [3:0]ext_axis_switch_gen_M05_AXIS_tkeep;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M05_AXIS TLAST" *) output [0:0]ext_axis_switch_gen_M05_AXIS_tlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M05_AXIS TREADY" *) input [0:0]ext_axis_switch_gen_M05_AXIS_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M05_AXIS TVALID" *) output [0:0]ext_axis_switch_gen_M05_AXIS_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M06_AXIS TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_gen_M06_AXIS, CLK_DOMAIN sim_bd_clk_99999985, FREQ_HZ 99999985, HAS_TKEEP 1, HAS_TLAST 1, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 4, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [31:0]ext_axis_switch_gen_M06_AXIS_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M06_AXIS TKEEP" *) output [3:0]ext_axis_switch_gen_M06_AXIS_tkeep;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M06_AXIS TLAST" *) output [0:0]ext_axis_switch_gen_M06_AXIS_tlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M06_AXIS TREADY" *) input [0:0]ext_axis_switch_gen_M06_AXIS_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M06_AXIS TVALID" *) output [0:0]ext_axis_switch_gen_M06_AXIS_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M07_AXIS TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_gen_M07_AXIS, CLK_DOMAIN sim_bd_clk_99999985, FREQ_HZ 99999985, HAS_TKEEP 1, HAS_TLAST 1, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 4, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [31:0]ext_axis_switch_gen_M07_AXIS_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M07_AXIS TKEEP" *) output [3:0]ext_axis_switch_gen_M07_AXIS_tkeep;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M07_AXIS TLAST" *) output [0:0]ext_axis_switch_gen_M07_AXIS_tlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M07_AXIS TREADY" *) input [0:0]ext_axis_switch_gen_M07_AXIS_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M07_AXIS TVALID" *) output [0:0]ext_axis_switch_gen_M07_AXIS_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M08_AXIS TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_gen_M08_AXIS, CLK_DOMAIN sim_bd_clk_99999985, FREQ_HZ 99999985, HAS_TKEEP 1, HAS_TLAST 1, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 4, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [31:0]ext_axis_switch_gen_M08_AXIS_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M08_AXIS TKEEP" *) output [3:0]ext_axis_switch_gen_M08_AXIS_tkeep;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M08_AXIS TLAST" *) output [0:0]ext_axis_switch_gen_M08_AXIS_tlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M08_AXIS TREADY" *) input [0:0]ext_axis_switch_gen_M08_AXIS_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M08_AXIS TVALID" *) output [0:0]ext_axis_switch_gen_M08_AXIS_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M09_AXIS TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_gen_M09_AXIS, CLK_DOMAIN sim_bd_clk_99999985, FREQ_HZ 99999985, HAS_TKEEP 1, HAS_TLAST 1, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 4, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [31:0]ext_axis_switch_gen_M09_AXIS_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M09_AXIS TKEEP" *) output [3:0]ext_axis_switch_gen_M09_AXIS_tkeep;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M09_AXIS TLAST" *) output [0:0]ext_axis_switch_gen_M09_AXIS_tlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M09_AXIS TREADY" *) input [0:0]ext_axis_switch_gen_M09_AXIS_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M09_AXIS TVALID" *) output [0:0]ext_axis_switch_gen_M09_AXIS_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M10_AXIS TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_gen_M10_AXIS, CLK_DOMAIN sim_bd_clk_99999985, FREQ_HZ 99999985, HAS_TKEEP 1, HAS_TLAST 1, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 4, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [31:0]ext_axis_switch_gen_M10_AXIS_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M10_AXIS TKEEP" *) output [3:0]ext_axis_switch_gen_M10_AXIS_tkeep;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M10_AXIS TLAST" *) output [0:0]ext_axis_switch_gen_M10_AXIS_tlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M10_AXIS TREADY" *) input [0:0]ext_axis_switch_gen_M10_AXIS_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M10_AXIS TVALID" *) output [0:0]ext_axis_switch_gen_M10_AXIS_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M11_AXIS TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_gen_M11_AXIS, CLK_DOMAIN sim_bd_clk_99999985, FREQ_HZ 99999985, HAS_TKEEP 1, HAS_TLAST 1, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 4, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [31:0]ext_axis_switch_gen_M11_AXIS_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M11_AXIS TKEEP" *) output [3:0]ext_axis_switch_gen_M11_AXIS_tkeep;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M11_AXIS TLAST" *) output [0:0]ext_axis_switch_gen_M11_AXIS_tlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M11_AXIS TREADY" *) input [0:0]ext_axis_switch_gen_M11_AXIS_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_M11_AXIS TVALID" *) output [0:0]ext_axis_switch_gen_M11_AXIS_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_S00_AXIS TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_gen_S00_AXIS, CLK_DOMAIN sim_bd_clk_99999985, FREQ_HZ 99999985, HAS_TKEEP 1, HAS_TLAST 1, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 4, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) input [31:0]ext_axis_switch_gen_S00_AXIS_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_S00_AXIS TKEEP" *) input [3:0]ext_axis_switch_gen_S00_AXIS_tkeep;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_S00_AXIS TLAST" *) input [0:0]ext_axis_switch_gen_S00_AXIS_tlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_S00_AXIS TREADY" *) output [0:0]ext_axis_switch_gen_S00_AXIS_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_switch_gen_S00_AXIS TVALID" *) input [0:0]ext_axis_switch_gen_S00_AXIS_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_gen_S_AXI_CTRL, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 0, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 0, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [6:0]ext_axis_switch_gen_S_AXI_CTRL_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL ARREADY" *) output ext_axis_switch_gen_S_AXI_CTRL_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL ARVALID" *) input ext_axis_switch_gen_S_AXI_CTRL_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL AWADDR" *) input [6:0]ext_axis_switch_gen_S_AXI_CTRL_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL AWREADY" *) output ext_axis_switch_gen_S_AXI_CTRL_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL AWVALID" *) input ext_axis_switch_gen_S_AXI_CTRL_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL BREADY" *) input ext_axis_switch_gen_S_AXI_CTRL_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL BRESP" *) output [1:0]ext_axis_switch_gen_S_AXI_CTRL_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL BVALID" *) output ext_axis_switch_gen_S_AXI_CTRL_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL RDATA" *) output [31:0]ext_axis_switch_gen_S_AXI_CTRL_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL RREADY" *) input ext_axis_switch_gen_S_AXI_CTRL_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL RRESP" *) output [1:0]ext_axis_switch_gen_S_AXI_CTRL_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL RVALID" *) output ext_axis_switch_gen_S_AXI_CTRL_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL WDATA" *) input [31:0]ext_axis_switch_gen_S_AXI_CTRL_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL WREADY" *) output ext_axis_switch_gen_S_AXI_CTRL_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_gen_S_AXI_CTRL WVALID" *) input ext_axis_switch_gen_S_AXI_CTRL_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_switch_mr_S_AXI_CTRL, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 0, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 0, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [6:0]ext_axis_switch_mr_S_AXI_CTRL_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL ARREADY" *) output ext_axis_switch_mr_S_AXI_CTRL_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL ARVALID" *) input ext_axis_switch_mr_S_AXI_CTRL_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL AWADDR" *) input [6:0]ext_axis_switch_mr_S_AXI_CTRL_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL AWREADY" *) output ext_axis_switch_mr_S_AXI_CTRL_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL AWVALID" *) input ext_axis_switch_mr_S_AXI_CTRL_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL BREADY" *) input ext_axis_switch_mr_S_AXI_CTRL_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL BRESP" *) output [1:0]ext_axis_switch_mr_S_AXI_CTRL_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL BVALID" *) output ext_axis_switch_mr_S_AXI_CTRL_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL RDATA" *) output [31:0]ext_axis_switch_mr_S_AXI_CTRL_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL RREADY" *) input ext_axis_switch_mr_S_AXI_CTRL_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL RRESP" *) output [1:0]ext_axis_switch_mr_S_AXI_CTRL_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL RVALID" *) output ext_axis_switch_mr_S_AXI_CTRL_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL WDATA" *) input [31:0]ext_axis_switch_mr_S_AXI_CTRL_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL WREADY" *) output ext_axis_switch_mr_S_AXI_CTRL_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_switch_mr_S_AXI_CTRL WVALID" *) input ext_axis_switch_mr_S_AXI_CTRL_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_tproc64x32_x8_0_m0_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_tproc64x32_x8_0_m0_axis, CLK_DOMAIN sim_bd_clk_99999985, FREQ_HZ 99999985, HAS_TKEEP 0, HAS_TLAST 1, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 4, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [31:0]ext_axis_tproc64x32_x8_0_m0_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_tproc64x32_x8_0_m0_axis TLAST" *) output ext_axis_tproc64x32_x8_0_m0_axis_tlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_tproc64x32_x8_0_m0_axis TREADY" *) input ext_axis_tproc64x32_x8_0_m0_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_tproc64x32_x8_0_m0_axis TVALID" *) output ext_axis_tproc64x32_x8_0_m0_axis_tvalid;
  output [19:0]ext_axis_tproc64x32_x8_0_pmem_addr;
  input [63:0]ext_axis_tproc64x32_x8_0_pmem_do;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_tproc64x32_x8_0_s0_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_tproc64x32_x8_0_s0_axis, CLK_DOMAIN sim_bd_clk_99999985, FREQ_HZ 99999985, HAS_TKEEP 0, HAS_TLAST 1, HAS_TREADY 1, HAS_TSTRB 0, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 4, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) input [31:0]ext_axis_tproc64x32_x8_0_s0_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_tproc64x32_x8_0_s0_axis TLAST" *) input ext_axis_tproc64x32_x8_0_s0_axis_tlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_tproc64x32_x8_0_s0_axis TREADY" *) output ext_axis_tproc64x32_x8_0_s0_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_axis_tproc64x32_x8_0_s0_axis TVALID" *) input ext_axis_tproc64x32_x8_0_s0_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_axis_tproc64x32_x8_0_s_axi, ADDR_WIDTH 32, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [31:0]ext_axis_tproc64x32_x8_0_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi ARPROT" *) input [2:0]ext_axis_tproc64x32_x8_0_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi ARREADY" *) output ext_axis_tproc64x32_x8_0_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi ARVALID" *) input ext_axis_tproc64x32_x8_0_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi AWADDR" *) input [31:0]ext_axis_tproc64x32_x8_0_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi AWPROT" *) input [2:0]ext_axis_tproc64x32_x8_0_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi AWREADY" *) output ext_axis_tproc64x32_x8_0_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi AWVALID" *) input ext_axis_tproc64x32_x8_0_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi BREADY" *) input ext_axis_tproc64x32_x8_0_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi BRESP" *) output [1:0]ext_axis_tproc64x32_x8_0_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi BVALID" *) output ext_axis_tproc64x32_x8_0_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi RDATA" *) output [31:0]ext_axis_tproc64x32_x8_0_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi RREADY" *) input ext_axis_tproc64x32_x8_0_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi RRESP" *) output [1:0]ext_axis_tproc64x32_x8_0_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi RVALID" *) output ext_axis_tproc64x32_x8_0_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi WDATA" *) input [31:0]ext_axis_tproc64x32_x8_0_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi WREADY" *) output ext_axis_tproc64x32_x8_0_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi WSTRB" *) input [3:0]ext_axis_tproc64x32_x8_0_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_axis_tproc64x32_x8_0_s_axi WVALID" *) input ext_axis_tproc64x32_x8_0_s_axi_wvalid;
  input ext_axis_tproc64x32_x8_0_start;
  input ext_c_shift_ram_0_D;
  output [0:0]ext_c_shift_ram_0_Q;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi AWADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi, ADDR_WIDTH 32, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_333250000, DATA_WIDTH 256, FREQ_HZ 333250000, HAS_BRESP 1, HAS_BURST 1, HAS_CACHE 1, HAS_LOCK 1, HAS_PROT 1, HAS_QOS 1, HAS_REGION 1, HAS_RRESP 0, HAS_WSTRB 1, ID_WIDTH 1, INSERT_VIP 0, MAX_BURST_LENGTH 256, NUM_READ_OUTSTANDING 2, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 2, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4, READ_WRITE_MODE WRITE_ONLY, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 1, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) output [31:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi AWBURST" *) output [1:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awburst;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi AWCACHE" *) output [3:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awcache;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi AWID" *) output [0:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi AWLEN" *) output [7:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlen;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi AWLOCK" *) output ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlock;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi AWPROT" *) output [2:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi AWQOS" *) output [3:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awqos;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi AWREADY" *) input ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi AWREGION" *) output [3:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awregion;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi AWSIZE" *) output [2:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awsize;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi AWVALID" *) output ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi BID" *) input [0:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi BREADY" *) output ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi BRESP" *) input [1:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi BVALID" *) input ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi WDATA" *) output [255:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi WLAST" *) output ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi WREADY" *) input ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi WSTRB" *) output [31:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi WVALID" *) output ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [7:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi ARPROT" *) input [2:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi ARREADY" *) output ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi ARVALID" *) input ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi AWADDR" *) input [7:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi AWPROT" *) input [2:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi AWREADY" *) output ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi AWVALID" *) input ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi BREADY" *) input ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi BRESP" *) output [1:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi BVALID" *) output ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi RDATA" *) output [31:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi RREADY" *) input ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi RRESP" *) output [1:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi RVALID" *) output ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi WDATA" *) input [31:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi WREADY" *) output ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi WSTRB" *) input [3:0]ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi WVALID" *) input ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wvalid;
  output ext_ddr4_axis_fir_decim_300to1_v2_0_capture_trigger;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_mr_buffer_et_0_m00_axis TDATA" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_mr_buffer_et_0_m00_axis, CLK_DOMAIN sim_bd_clk_99999985, FREQ_HZ 99999985, HAS_TKEEP 0, HAS_TLAST 1, HAS_TREADY 1, HAS_TSTRB 1, INSERT_VIP 0, LAYERED_METADATA undef, PHASE 0.0, TDATA_NUM_BYTES 4, TDEST_WIDTH 0, TID_WIDTH 0, TUSER_WIDTH 0" *) output [31:0]ext_mr_buffer_et_0_m00_axis_tdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_mr_buffer_et_0_m00_axis TLAST" *) output ext_mr_buffer_et_0_m00_axis_tlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_mr_buffer_et_0_m00_axis TREADY" *) input ext_mr_buffer_et_0_m00_axis_tready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_mr_buffer_et_0_m00_axis TSTRB" *) output [3:0]ext_mr_buffer_et_0_m00_axis_tstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 ext_mr_buffer_et_0_m00_axis TVALID" *) output ext_mr_buffer_et_0_m00_axis_tvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi ARADDR" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ext_mr_buffer_et_0_s00_axi, ADDR_WIDTH 16, ARUSER_WIDTH 0, AWUSER_WIDTH 0, BUSER_WIDTH 0, CLK_DOMAIN sim_bd_clk_99999985, DATA_WIDTH 32, FREQ_HZ 99999985, HAS_BRESP 1, HAS_BURST 0, HAS_CACHE 0, HAS_LOCK 0, HAS_PROT 1, HAS_QOS 0, HAS_REGION 0, HAS_RRESP 1, HAS_WSTRB 1, ID_WIDTH 0, INSERT_VIP 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_READ_THREADS 1, NUM_WRITE_OUTSTANDING 1, NUM_WRITE_THREADS 1, PHASE 0.0, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, RUSER_BITS_PER_BYTE 0, RUSER_WIDTH 0, SUPPORTS_NARROW_BURST 0, WUSER_BITS_PER_BYTE 0, WUSER_WIDTH 0" *) input [5:0]ext_mr_buffer_et_0_s00_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi ARPROT" *) input [2:0]ext_mr_buffer_et_0_s00_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi ARREADY" *) output ext_mr_buffer_et_0_s00_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi ARVALID" *) input ext_mr_buffer_et_0_s00_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi AWADDR" *) input [5:0]ext_mr_buffer_et_0_s00_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi AWPROT" *) input [2:0]ext_mr_buffer_et_0_s00_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi AWREADY" *) output ext_mr_buffer_et_0_s00_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi AWVALID" *) input ext_mr_buffer_et_0_s00_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi BREADY" *) input ext_mr_buffer_et_0_s00_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi BRESP" *) output [1:0]ext_mr_buffer_et_0_s00_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi BVALID" *) output ext_mr_buffer_et_0_s00_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi RDATA" *) output [31:0]ext_mr_buffer_et_0_s00_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi RREADY" *) input ext_mr_buffer_et_0_s00_axi_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi RRESP" *) output [1:0]ext_mr_buffer_et_0_s00_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi RVALID" *) output ext_mr_buffer_et_0_s00_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi WDATA" *) input [31:0]ext_mr_buffer_et_0_s00_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi WREADY" *) output ext_mr_buffer_et_0_s00_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi WSTRB" *) input [3:0]ext_mr_buffer_et_0_s00_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 ext_mr_buffer_et_0_s00_axi WVALID" *) input ext_mr_buffer_et_0_s00_axi_wvalid;
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
  (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 RST.RESETN RST" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME RST.RESETN, INSERT_VIP 0, POLARITY ACTIVE_LOW" *) input resetn;

  wire [31:0]S00_AXIS_0_1_TDATA;
  wire [3:0]S00_AXIS_0_1_TKEEP;
  wire [0:0]S00_AXIS_0_1_TLAST;
  wire [0:0]S00_AXIS_0_1_TREADY;
  wire [0:0]S00_AXIS_0_1_TVALID;
  wire [6:0]S_AXI_CTRL_0_1_ARADDR;
  wire S_AXI_CTRL_0_1_ARREADY;
  wire S_AXI_CTRL_0_1_ARVALID;
  wire [6:0]S_AXI_CTRL_0_1_AWADDR;
  wire S_AXI_CTRL_0_1_AWREADY;
  wire S_AXI_CTRL_0_1_AWVALID;
  wire S_AXI_CTRL_0_1_BREADY;
  wire [1:0]S_AXI_CTRL_0_1_BRESP;
  wire S_AXI_CTRL_0_1_BVALID;
  wire [31:0]S_AXI_CTRL_0_1_RDATA;
  wire S_AXI_CTRL_0_1_RREADY;
  wire [1:0]S_AXI_CTRL_0_1_RRESP;
  wire S_AXI_CTRL_0_1_RVALID;
  wire [31:0]S_AXI_CTRL_0_1_WDATA;
  wire S_AXI_CTRL_0_1_WREADY;
  wire S_AXI_CTRL_0_1_WVALID;
  wire [6:0]S_AXI_CTRL_0_2_ARADDR;
  wire S_AXI_CTRL_0_2_ARREADY;
  wire S_AXI_CTRL_0_2_ARVALID;
  wire [6:0]S_AXI_CTRL_0_2_AWADDR;
  wire S_AXI_CTRL_0_2_AWREADY;
  wire S_AXI_CTRL_0_2_AWVALID;
  wire S_AXI_CTRL_0_2_BREADY;
  wire [1:0]S_AXI_CTRL_0_2_BRESP;
  wire S_AXI_CTRL_0_2_BVALID;
  wire [31:0]S_AXI_CTRL_0_2_RDATA;
  wire S_AXI_CTRL_0_2_RREADY;
  wire [1:0]S_AXI_CTRL_0_2_RRESP;
  wire S_AXI_CTRL_0_2_RVALID;
  wire [31:0]S_AXI_CTRL_0_2_WDATA;
  wire S_AXI_CTRL_0_2_WREADY;
  wire S_AXI_CTRL_0_2_WVALID;
  wire [6:0]S_AXI_CTRL_0_3_ARADDR;
  wire S_AXI_CTRL_0_3_ARREADY;
  wire S_AXI_CTRL_0_3_ARVALID;
  wire [6:0]S_AXI_CTRL_0_3_AWADDR;
  wire S_AXI_CTRL_0_3_AWREADY;
  wire S_AXI_CTRL_0_3_AWVALID;
  wire S_AXI_CTRL_0_3_BREADY;
  wire [1:0]S_AXI_CTRL_0_3_BRESP;
  wire S_AXI_CTRL_0_3_BVALID;
  wire [31:0]S_AXI_CTRL_0_3_RDATA;
  wire S_AXI_CTRL_0_3_RREADY;
  wire [1:0]S_AXI_CTRL_0_3_RRESP;
  wire S_AXI_CTRL_0_3_RVALID;
  wire [31:0]S_AXI_CTRL_0_3_WDATA;
  wire S_AXI_CTRL_0_3_WREADY;
  wire S_AXI_CTRL_0_3_WVALID;
  wire [6:0]S_AXI_CTRL_0_4_ARADDR;
  wire S_AXI_CTRL_0_4_ARREADY;
  wire S_AXI_CTRL_0_4_ARVALID;
  wire [6:0]S_AXI_CTRL_0_4_AWADDR;
  wire S_AXI_CTRL_0_4_AWREADY;
  wire S_AXI_CTRL_0_4_AWVALID;
  wire S_AXI_CTRL_0_4_BREADY;
  wire [1:0]S_AXI_CTRL_0_4_BRESP;
  wire S_AXI_CTRL_0_4_BVALID;
  wire [31:0]S_AXI_CTRL_0_4_RDATA;
  wire S_AXI_CTRL_0_4_RREADY;
  wire [1:0]S_AXI_CTRL_0_4_RRESP;
  wire S_AXI_CTRL_0_4_RVALID;
  wire [31:0]S_AXI_CTRL_0_4_WDATA;
  wire S_AXI_CTRL_0_4_WREADY;
  wire S_AXI_CTRL_0_4_WVALID;
  wire [6:0]S_AXI_CTRL_0_5_ARADDR;
  wire S_AXI_CTRL_0_5_ARREADY;
  wire S_AXI_CTRL_0_5_ARVALID;
  wire [6:0]S_AXI_CTRL_0_5_AWADDR;
  wire S_AXI_CTRL_0_5_AWREADY;
  wire S_AXI_CTRL_0_5_AWVALID;
  wire S_AXI_CTRL_0_5_BREADY;
  wire [1:0]S_AXI_CTRL_0_5_BRESP;
  wire S_AXI_CTRL_0_5_BVALID;
  wire [31:0]S_AXI_CTRL_0_5_RDATA;
  wire S_AXI_CTRL_0_5_RREADY;
  wire [1:0]S_AXI_CTRL_0_5_RRESP;
  wire S_AXI_CTRL_0_5_RVALID;
  wire [31:0]S_AXI_CTRL_0_5_WDATA;
  wire S_AXI_CTRL_0_5_WREADY;
  wire S_AXI_CTRL_0_5_WVALID;
  wire [63:0]axis_avg_buffer_0_m0_axis_TDATA;
  wire axis_avg_buffer_0_m0_axis_TLAST;
  wire [0:0]axis_avg_buffer_0_m0_axis_TREADY;
  wire axis_avg_buffer_0_m0_axis_TVALID;
  wire [31:0]axis_avg_buffer_0_m1_axis_TDATA;
  wire axis_avg_buffer_0_m1_axis_TLAST;
  wire [0:0]axis_avg_buffer_0_m1_axis_TREADY;
  wire axis_avg_buffer_0_m1_axis_TVALID;
  wire [63:0]axis_avg_buffer_0_m2_axis_TDATA;
  wire axis_avg_buffer_0_m2_axis_TREADY;
  wire axis_avg_buffer_0_m2_axis_TVALID;
  wire [63:0]axis_avg_buffer_1_m0_axis_TDATA;
  wire axis_avg_buffer_1_m0_axis_TLAST;
  wire [1:1]axis_avg_buffer_1_m0_axis_TREADY;
  wire axis_avg_buffer_1_m0_axis_TVALID;
  wire [31:0]axis_avg_buffer_1_m1_axis_TDATA;
  wire axis_avg_buffer_1_m1_axis_TLAST;
  wire [1:1]axis_avg_buffer_1_m1_axis_TREADY;
  wire axis_avg_buffer_1_m1_axis_TVALID;
  wire [63:0]axis_avg_buffer_1_m2_axis_TDATA;
  wire axis_avg_buffer_1_m2_axis_TREADY;
  wire axis_avg_buffer_1_m2_axis_TVALID;
  wire [63:0]axis_avg_buffer_2_m0_axis_TDATA;
  wire axis_avg_buffer_2_m0_axis_TLAST;
  wire [2:2]axis_avg_buffer_2_m0_axis_TREADY;
  wire axis_avg_buffer_2_m0_axis_TVALID;
  wire [31:0]axis_avg_buffer_2_m1_axis_TDATA;
  wire axis_avg_buffer_2_m1_axis_TLAST;
  wire [2:2]axis_avg_buffer_2_m1_axis_TREADY;
  wire axis_avg_buffer_2_m1_axis_TVALID;
  wire [63:0]axis_avg_buffer_2_m2_axis_TDATA;
  wire axis_avg_buffer_2_m2_axis_TREADY;
  wire axis_avg_buffer_2_m2_axis_TVALID;
  wire [63:0]axis_avg_buffer_3_m0_axis_TDATA;
  wire axis_avg_buffer_3_m0_axis_TLAST;
  wire [3:3]axis_avg_buffer_3_m0_axis_TREADY;
  wire axis_avg_buffer_3_m0_axis_TVALID;
  wire [31:0]axis_avg_buffer_3_m1_axis_TDATA;
  wire axis_avg_buffer_3_m1_axis_TLAST;
  wire [3:3]axis_avg_buffer_3_m1_axis_TREADY;
  wire axis_avg_buffer_3_m1_axis_TVALID;
  wire [63:0]axis_avg_buffer_3_m2_axis_TDATA;
  wire axis_avg_buffer_3_m2_axis_TREADY;
  wire axis_avg_buffer_3_m2_axis_TVALID;
  wire [255:0]axis_awg_tuning_v1_10_m_axis_TDATA;
  wire axis_awg_tuning_v1_10_m_axis_TREADY;
  wire axis_awg_tuning_v1_10_m_axis_TVALID;
  wire [255:0]axis_awg_tuning_v1_11_m_axis_TDATA;
  wire axis_awg_tuning_v1_11_m_axis_TREADY;
  wire axis_awg_tuning_v1_11_m_axis_TVALID;
  wire [255:0]axis_awg_tuning_v1_4_m_axis_TDATA;
  wire axis_awg_tuning_v1_4_m_axis_TREADY;
  wire axis_awg_tuning_v1_4_m_axis_TVALID;
  wire [255:0]axis_awg_tuning_v1_5_m_axis_TDATA;
  wire axis_awg_tuning_v1_5_m_axis_TREADY;
  wire axis_awg_tuning_v1_5_m_axis_TVALID;
  wire [255:0]axis_awg_tuning_v1_6_m_axis_TDATA;
  wire axis_awg_tuning_v1_6_m_axis_TREADY;
  wire axis_awg_tuning_v1_6_m_axis_TVALID;
  wire [255:0]axis_awg_tuning_v1_8_m_axis_TDATA;
  wire axis_awg_tuning_v1_8_m_axis_TREADY;
  wire axis_awg_tuning_v1_8_m_axis_TVALID;
  wire [255:0]axis_awg_tuning_v1_9_m_axis_TDATA;
  wire axis_awg_tuning_v1_9_m_axis_TREADY;
  wire axis_awg_tuning_v1_9_m_axis_TVALID;
  wire [31:0]axis_broadcaster_0_M00_AXIS_TDATA;
  wire [0:0]axis_broadcaster_0_M00_AXIS_TVALID;
  wire [63:32]axis_broadcaster_0_M01_AXIS_TDATA;
  wire [1:1]axis_broadcaster_0_M01_AXIS_TVALID;
  wire [31:0]axis_broadcaster_1_M00_AXIS_TDATA;
  wire [0:0]axis_broadcaster_1_M00_AXIS_TVALID;
  wire [63:32]axis_broadcaster_1_M01_AXIS_TDATA;
  wire [1:1]axis_broadcaster_1_M01_AXIS_TVALID;
  wire [31:0]axis_broadcaster_2_M00_AXIS_TDATA;
  wire [0:0]axis_broadcaster_2_M00_AXIS_TVALID;
  wire [63:32]axis_broadcaster_2_M01_AXIS_TDATA;
  wire [1:1]axis_broadcaster_2_M01_AXIS_TVALID;
  wire [31:0]axis_broadcaster_3_M00_AXIS_TDATA;
  wire [0:0]axis_broadcaster_3_M00_AXIS_TVALID;
  wire [63:32]axis_broadcaster_3_M01_AXIS_TDATA;
  wire [1:1]axis_broadcaster_3_M01_AXIS_TVALID;
  wire [63:0]axis_clk_cnvrt_avg_0_M_AXIS_TDATA;
  wire axis_clk_cnvrt_avg_0_M_AXIS_TREADY;
  wire axis_clk_cnvrt_avg_0_M_AXIS_TVALID;
  wire [63:0]axis_clk_cnvrt_avg_1_M_AXIS_TDATA;
  wire axis_clk_cnvrt_avg_1_M_AXIS_TREADY;
  wire axis_clk_cnvrt_avg_1_M_AXIS_TVALID;
  wire [63:0]axis_clk_cnvrt_avg_2_M_AXIS_TDATA;
  wire axis_clk_cnvrt_avg_2_M_AXIS_TREADY;
  wire axis_clk_cnvrt_avg_2_M_AXIS_TVALID;
  wire [63:0]axis_clk_cnvrt_avg_3_M_AXIS_TDATA;
  wire axis_clk_cnvrt_avg_3_M_AXIS_TREADY;
  wire axis_clk_cnvrt_avg_3_M_AXIS_TVALID;
  wire [255:0]axis_dyn_readout_v1_0_m0_axis_TDATA;
  wire [0:0]axis_dyn_readout_v1_0_m0_axis_TREADY;
  wire axis_dyn_readout_v1_0_m0_axis_TVALID;
  wire [31:0]axis_dyn_readout_v1_0_m1_axis_TDATA;
  wire axis_dyn_readout_v1_0_m1_axis_TVALID;
  wire [255:0]axis_dyn_readout_v1_1_m0_axis_TDATA;
  wire [1:1]axis_dyn_readout_v1_1_m0_axis_TREADY;
  wire axis_dyn_readout_v1_1_m0_axis_TVALID;
  wire [31:0]axis_dyn_readout_v1_1_m1_axis_TDATA;
  wire axis_dyn_readout_v1_1_m1_axis_TVALID;
  wire [255:0]axis_dyn_readout_v1_2_m0_axis_TDATA;
  wire [2:2]axis_dyn_readout_v1_2_m0_axis_TREADY;
  wire axis_dyn_readout_v1_2_m0_axis_TVALID;
  wire [31:0]axis_dyn_readout_v1_2_m1_axis_TDATA;
  wire axis_dyn_readout_v1_2_m1_axis_TVALID;
  wire [255:0]axis_dyn_readout_v1_3_m0_axis_TDATA;
  wire [3:3]axis_dyn_readout_v1_3_m0_axis_TREADY;
  wire axis_dyn_readout_v1_3_m0_axis_TVALID;
  wire [31:0]axis_dyn_readout_v1_3_m1_axis_TDATA;
  wire axis_dyn_readout_v1_3_m1_axis_TVALID;
  wire [255:0]axis_register_slice_0_m_axis_TDATA;
  wire axis_register_slice_0_m_axis_TREADY;
  wire axis_register_slice_0_m_axis_TVALID;
  wire [255:0]axis_register_slice_10_m_axis_TDATA;
  wire axis_register_slice_10_m_axis_TREADY;
  wire axis_register_slice_10_m_axis_TVALID;
  wire [255:0]axis_register_slice_11_m_axis_TDATA;
  wire axis_register_slice_11_m_axis_TREADY;
  wire axis_register_slice_11_m_axis_TVALID;
  wire [255:0]axis_register_slice_12_m_axis_TDATA;
  wire axis_register_slice_12_m_axis_TREADY;
  wire axis_register_slice_12_m_axis_TVALID;
  wire [255:0]axis_register_slice_13_m_axis_TDATA;
  wire axis_register_slice_13_m_axis_TREADY;
  wire axis_register_slice_13_m_axis_TVALID;
  wire [255:0]axis_register_slice_14_m_axis_TDATA;
  wire axis_register_slice_14_m_axis_TREADY;
  wire axis_register_slice_14_m_axis_TVALID;
  wire [255:0]axis_register_slice_15_m_axis_TDATA;
  wire axis_register_slice_15_m_axis_TREADY;
  wire axis_register_slice_15_m_axis_TVALID;
  wire [255:0]axis_register_slice_16_m_axis_TDATA;
  wire axis_register_slice_16_m_axis_TREADY;
  wire axis_register_slice_16_m_axis_TVALID;
  wire [255:0]axis_register_slice_1_m_axis_TDATA;
  wire axis_register_slice_1_m_axis_TREADY;
  wire axis_register_slice_1_m_axis_TVALID;
  wire [159:0]axis_register_slice_21_M_AXIS_TDATA;
  wire axis_register_slice_21_M_AXIS_TVALID;
  wire [159:0]axis_register_slice_22_M_AXIS_TDATA;
  wire axis_register_slice_22_M_AXIS_TVALID;
  wire [159:0]axis_register_slice_23_M_AXIS_TDATA;
  wire axis_register_slice_23_M_AXIS_TVALID;
  wire [159:0]axis_register_slice_24_M_AXIS_TDATA;
  wire axis_register_slice_24_M_AXIS_TVALID;
  wire [159:0]axis_register_slice_25_M_AXIS_TDATA;
  wire axis_register_slice_25_M_AXIS_TVALID;
  wire [159:0]axis_register_slice_26_M_AXIS_TDATA;
  wire axis_register_slice_26_M_AXIS_TVALID;
  wire [159:0]axis_register_slice_27_M_AXIS_TDATA;
  wire axis_register_slice_27_M_AXIS_TVALID;
  wire [255:0]axis_register_slice_2_m_axis_TDATA;
  wire axis_register_slice_2_m_axis_TREADY;
  wire axis_register_slice_2_m_axis_TVALID;
  wire [255:0]axis_register_slice_3_m_axis_TDATA;
  wire axis_register_slice_3_m_axis_TREADY;
  wire axis_register_slice_3_m_axis_TVALID;
  wire [159:0]axis_register_slice_4_M_AXIS_TDATA;
  wire axis_register_slice_4_M_AXIS_TVALID;
  wire [159:0]axis_register_slice_5_M_AXIS_TDATA;
  wire axis_register_slice_5_M_AXIS_TVALID;
  wire [159:0]axis_register_slice_6_M_AXIS_TDATA;
  wire axis_register_slice_6_M_AXIS_TVALID;
  wire [159:0]axis_register_slice_7_M_AXIS_TDATA;
  wire axis_register_slice_7_M_AXIS_TVALID;
  wire [255:0]axis_register_slice_8_m_axis_TDATA;
  wire axis_register_slice_8_m_axis_TREADY;
  wire axis_register_slice_8_m_axis_TVALID;
  wire [159:0]axis_register_slice_9_M_AXIS_TDATA;
  wire axis_register_slice_9_M_AXIS_TVALID;
  wire [159:0]axis_set_reg_0_dout;
  wire [255:0]axis_signal_gen_v6_0_m_axis_TDATA;
  wire axis_signal_gen_v6_0_m_axis_TREADY;
  wire axis_signal_gen_v6_0_m_axis_TVALID;
  wire [255:0]axis_signal_gen_v6_1_m_axis_TDATA;
  wire axis_signal_gen_v6_1_m_axis_TREADY;
  wire axis_signal_gen_v6_1_m_axis_TVALID;
  wire [255:0]axis_signal_gen_v6_2_m_axis_TDATA;
  wire axis_signal_gen_v6_2_m_axis_TREADY;
  wire axis_signal_gen_v6_2_m_axis_TVALID;
  wire [255:0]axis_signal_gen_v6_3_m_axis_TDATA;
  wire axis_signal_gen_v6_3_m_axis_TREADY;
  wire axis_signal_gen_v6_3_m_axis_TVALID;
  wire [255:0]axis_square_pulse_v1_0_m_axis_TDATA;
  wire axis_square_pulse_v1_0_m_axis_TREADY;
  wire axis_square_pulse_v1_0_m_axis_TVALID;
  wire [63:0]axis_switch_avg_M00_AXIS_TDATA;
  wire [0:0]axis_switch_avg_M00_AXIS_TLAST;
  wire [0:0]axis_switch_avg_M00_AXIS_TREADY;
  wire [0:0]axis_switch_avg_M00_AXIS_TVALID;
  wire [31:0]axis_switch_buf_M00_AXIS_TDATA;
  wire [0:0]axis_switch_buf_M00_AXIS_TLAST;
  wire [0:0]axis_switch_buf_M00_AXIS_TREADY;
  wire [0:0]axis_switch_buf_M00_AXIS_TVALID;
  wire [31:0]axis_switch_ddr_M00_AXIS_TDATA;
  wire [0:0]axis_switch_ddr_M00_AXIS_TVALID;
  wire [31:0]axis_switch_gen_M00_AXIS_TDATA;
  wire axis_switch_gen_M00_AXIS_TREADY;
  wire [0:0]axis_switch_gen_M00_AXIS_TVALID;
  wire [63:32]axis_switch_gen_M01_AXIS_TDATA;
  wire axis_switch_gen_M01_AXIS_TREADY;
  wire [1:1]axis_switch_gen_M01_AXIS_TVALID;
  wire [95:64]axis_switch_gen_M02_AXIS_TDATA;
  wire axis_switch_gen_M02_AXIS_TREADY;
  wire [2:2]axis_switch_gen_M02_AXIS_TVALID;
  wire [127:96]axis_switch_gen_M03_AXIS_TDATA;
  wire axis_switch_gen_M03_AXIS_TREADY;
  wire [3:3]axis_switch_gen_M03_AXIS_TVALID;
  wire [159:128]axis_switch_gen_M04_AXIS_TDATA;
  wire [19:16]axis_switch_gen_M04_AXIS_TKEEP;
  wire [4:4]axis_switch_gen_M04_AXIS_TLAST;
  wire [0:0]axis_switch_gen_M04_AXIS_TREADY;
  wire [4:4]axis_switch_gen_M04_AXIS_TVALID;
  wire [191:160]axis_switch_gen_M05_AXIS_TDATA;
  wire [23:20]axis_switch_gen_M05_AXIS_TKEEP;
  wire [5:5]axis_switch_gen_M05_AXIS_TLAST;
  wire [0:0]axis_switch_gen_M05_AXIS_TREADY;
  wire [5:5]axis_switch_gen_M05_AXIS_TVALID;
  wire [223:192]axis_switch_gen_M06_AXIS_TDATA;
  wire [27:24]axis_switch_gen_M06_AXIS_TKEEP;
  wire [6:6]axis_switch_gen_M06_AXIS_TLAST;
  wire [0:0]axis_switch_gen_M06_AXIS_TREADY;
  wire [6:6]axis_switch_gen_M06_AXIS_TVALID;
  wire [255:224]axis_switch_gen_M07_AXIS_TDATA;
  wire [31:28]axis_switch_gen_M07_AXIS_TKEEP;
  wire [7:7]axis_switch_gen_M07_AXIS_TLAST;
  wire [0:0]axis_switch_gen_M07_AXIS_TREADY;
  wire [7:7]axis_switch_gen_M07_AXIS_TVALID;
  wire [287:256]axis_switch_gen_M08_AXIS_TDATA;
  wire [35:32]axis_switch_gen_M08_AXIS_TKEEP;
  wire [8:8]axis_switch_gen_M08_AXIS_TLAST;
  wire [0:0]axis_switch_gen_M08_AXIS_TREADY;
  wire [8:8]axis_switch_gen_M08_AXIS_TVALID;
  wire [319:288]axis_switch_gen_M09_AXIS_TDATA;
  wire [39:36]axis_switch_gen_M09_AXIS_TKEEP;
  wire [9:9]axis_switch_gen_M09_AXIS_TLAST;
  wire [0:0]axis_switch_gen_M09_AXIS_TREADY;
  wire [9:9]axis_switch_gen_M09_AXIS_TVALID;
  wire [351:320]axis_switch_gen_M10_AXIS_TDATA;
  wire [43:40]axis_switch_gen_M10_AXIS_TKEEP;
  wire [10:10]axis_switch_gen_M10_AXIS_TLAST;
  wire [0:0]axis_switch_gen_M10_AXIS_TREADY;
  wire [10:10]axis_switch_gen_M10_AXIS_TVALID;
  wire [383:352]axis_switch_gen_M11_AXIS_TDATA;
  wire [47:44]axis_switch_gen_M11_AXIS_TKEEP;
  wire [11:11]axis_switch_gen_M11_AXIS_TLAST;
  wire [0:0]axis_switch_gen_M11_AXIS_TREADY;
  wire [11:11]axis_switch_gen_M11_AXIS_TVALID;
  wire [255:0]axis_switch_mr_M00_AXIS_TDATA;
  wire axis_switch_mr_M00_AXIS_TREADY;
  wire [0:0]axis_switch_mr_M00_AXIS_TVALID;
  wire [159:0]axis_tmux_v1_0_m0_axis_TDATA;
  wire axis_tmux_v1_0_m0_axis_TVALID;
  wire [159:0]axis_tmux_v1_0_m1_axis_TDATA;
  wire axis_tmux_v1_0_m1_axis_TVALID;
  wire [159:0]axis_tmux_v1_1_m0_axis_TDATA;
  wire axis_tmux_v1_1_m0_axis_TVALID;
  wire [159:0]axis_tmux_v1_1_m1_axis_TDATA;
  wire axis_tmux_v1_1_m1_axis_TVALID;
  wire [159:0]axis_tmux_v1_2_m0_axis_TDATA;
  wire axis_tmux_v1_2_m0_axis_TVALID;
  wire [159:0]axis_tmux_v1_2_m1_axis_TDATA;
  wire axis_tmux_v1_2_m1_axis_TVALID;
  wire [159:0]axis_tmux_v1_3_m0_axis_TDATA;
  wire axis_tmux_v1_3_m0_axis_TVALID;
  wire [159:0]axis_tmux_v1_3_m1_axis_TDATA;
  wire axis_tmux_v1_3_m1_axis_TVALID;
  wire [159:0]axis_tmux_v1_4_m0_axis_TDATA;
  wire axis_tmux_v1_4_m0_axis_TVALID;
  wire [159:0]axis_tmux_v1_4_m1_axis_TDATA;
  wire axis_tmux_v1_4_m1_axis_TVALID;
  wire [159:0]axis_tmux_v1_5_m0_axis_TDATA;
  wire axis_tmux_v1_5_m0_axis_TVALID;
  wire [159:0]axis_tmux_v1_5_m1_axis_TDATA;
  wire axis_tmux_v1_5_m1_axis_TVALID;
  wire [159:0]axis_tmux_v1_6_m0_axis_TDATA;
  wire axis_tmux_v1_6_m0_axis_TVALID;
  wire [159:0]axis_tmux_v1_6_m1_axis_TDATA;
  wire axis_tmux_v1_6_m1_axis_TVALID;
  wire [159:0]axis_tmux_v1_6_m2_axis_TDATA;
  wire axis_tmux_v1_6_m2_axis_TVALID;
  wire [159:0]axis_tmux_v1_6_m3_axis_TDATA;
  wire axis_tmux_v1_6_m3_axis_TVALID;
  wire [31:0]axis_tproc64x32_x8_0_m0_axis_TDATA;
  wire axis_tproc64x32_x8_0_m0_axis_TLAST;
  wire axis_tproc64x32_x8_0_m0_axis_TREADY;
  wire axis_tproc64x32_x8_0_m0_axis_TVALID;
  wire [159:0]axis_tproc64x32_x8_0_m1_axis_TDATA;
  wire axis_tproc64x32_x8_0_m1_axis_TREADY;
  wire axis_tproc64x32_x8_0_m1_axis_TVALID;
  wire [159:0]axis_tproc64x32_x8_0_m2_axis_TDATA;
  wire axis_tproc64x32_x8_0_m2_axis_TREADY;
  wire axis_tproc64x32_x8_0_m2_axis_TVALID;
  wire [159:0]axis_tproc64x32_x8_0_m3_axis_TDATA;
  wire axis_tproc64x32_x8_0_m3_axis_TREADY;
  wire axis_tproc64x32_x8_0_m3_axis_TVALID;
  wire [159:0]axis_tproc64x32_x8_0_m4_axis_TDATA;
  wire axis_tproc64x32_x8_0_m4_axis_TREADY;
  wire axis_tproc64x32_x8_0_m4_axis_TVALID;
  wire [159:0]axis_tproc64x32_x8_0_m5_axis_TDATA;
  wire axis_tproc64x32_x8_0_m5_axis_TREADY;
  wire axis_tproc64x32_x8_0_m5_axis_TVALID;
  wire [159:0]axis_tproc64x32_x8_0_m6_axis_TDATA;
  wire axis_tproc64x32_x8_0_m6_axis_TREADY;
  wire axis_tproc64x32_x8_0_m6_axis_TVALID;
  wire [159:0]axis_tproc64x32_x8_0_m7_axis_TDATA;
  wire axis_tproc64x32_x8_0_m7_axis_TREADY;
  wire axis_tproc64x32_x8_0_m7_axis_TVALID;
  wire [159:0]axis_tproc64x32_x8_0_m8_axis_TDATA;
  wire axis_tproc64x32_x8_0_m8_axis_TREADY;
  wire axis_tproc64x32_x8_0_m8_axis_TVALID;
  wire [19:0]axis_tproc64x32_x8_0_pmem_addr;
  wire [0:0]c_shift_ram_0_Q;
  wire clk_300000000_1;
  wire clk_333250000_1;
  wire clk_99999985_1;
  wire [31:0]ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWADDR;
  wire [1:0]ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWBURST;
  wire [3:0]ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWCACHE;
  wire [0:0]ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWID;
  wire [7:0]ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWLEN;
  wire ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWLOCK;
  wire [2:0]ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWPROT;
  wire [3:0]ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWQOS;
  wire ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWREADY;
  wire [3:0]ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWREGION;
  wire [2:0]ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWSIZE;
  wire ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWVALID;
  wire [0:0]ddr4_axis_buffer_ddr_sample_v3_0_m_axi_BID;
  wire ddr4_axis_buffer_ddr_sample_v3_0_m_axi_BREADY;
  wire [1:0]ddr4_axis_buffer_ddr_sample_v3_0_m_axi_BRESP;
  wire ddr4_axis_buffer_ddr_sample_v3_0_m_axi_BVALID;
  wire [255:0]ddr4_axis_buffer_ddr_sample_v3_0_m_axi_WDATA;
  wire ddr4_axis_buffer_ddr_sample_v3_0_m_axi_WLAST;
  wire ddr4_axis_buffer_ddr_sample_v3_0_m_axi_WREADY;
  wire [31:0]ddr4_axis_buffer_ddr_sample_v3_0_m_axi_WSTRB;
  wire ddr4_axis_buffer_ddr_sample_v3_0_m_axi_WVALID;
  wire ddr4_axis_fir_decim_300to1_v2_0_capture_trigger;
  wire [127:0]ddr4_axis_fir_decim_300to1_v2_0_m_axis_TDATA;
  wire ddr4_axis_fir_decim_300to1_v2_0_m_axis_TLAST;
  wire ddr4_axis_fir_decim_300to1_v2_0_m_axis_TREADY;
  wire ddr4_axis_fir_decim_300to1_v2_0_m_axis_TVALID;
  wire ddr4_axis_trigger_sync_v1_0_trigger_pulse;
  wire [0:0]ddr4_fir_trigger_disable_dout;
  wire [63:0]ext_axis_tproc64x32_x8_0_pmem_do_1;
  wire ext_axis_tproc64x32_x8_0_start_1;
  wire ext_c_shift_ram_0_D_1;
  wire [31:0]mr_buffer_et_0_m00_axis_TDATA;
  wire mr_buffer_et_0_m00_axis_TLAST;
  wire mr_buffer_et_0_m00_axis_TREADY;
  wire [3:0]mr_buffer_et_0_m00_axis_TSTRB;
  wire mr_buffer_et_0_m00_axis_TVALID;
  wire qick_vec2bit_0_dout0;
  wire qick_vec2bit_0_dout1;
  wire qick_vec2bit_0_dout2;
  wire qick_vec2bit_0_dout3;
  wire qick_vec2bit_0_dout4;
  wire qick_vec2bit_0_dout5;
  wire qick_vec2bit_0_dout6;
  wire resetn_1;
  wire [5:0]s00_axi_0_1_ARADDR;
  wire [2:0]s00_axi_0_1_ARPROT;
  wire s00_axi_0_1_ARREADY;
  wire s00_axi_0_1_ARVALID;
  wire [5:0]s00_axi_0_1_AWADDR;
  wire [2:0]s00_axi_0_1_AWPROT;
  wire s00_axi_0_1_AWREADY;
  wire s00_axi_0_1_AWVALID;
  wire s00_axi_0_1_BREADY;
  wire [1:0]s00_axi_0_1_BRESP;
  wire s00_axi_0_1_BVALID;
  wire [31:0]s00_axi_0_1_RDATA;
  wire s00_axi_0_1_RREADY;
  wire [1:0]s00_axi_0_1_RRESP;
  wire s00_axi_0_1_RVALID;
  wire [31:0]s00_axi_0_1_WDATA;
  wire s00_axi_0_1_WREADY;
  wire [3:0]s00_axi_0_1_WSTRB;
  wire s00_axi_0_1_WVALID;
  wire [31:0]s0_axis_0_1_TDATA;
  wire s0_axis_0_1_TLAST;
  wire s0_axis_0_1_TREADY;
  wire s0_axis_0_1_TVALID;
  wire [127:0]s1_axis_0_1_TDATA;
  wire s1_axis_0_1_TREADY;
  wire s1_axis_0_1_TVALID;
  wire [127:0]s1_axis_0_2_TDATA;
  wire s1_axis_0_2_TREADY;
  wire s1_axis_0_2_TVALID;
  wire [127:0]s1_axis_0_3_TDATA;
  wire s1_axis_0_3_TREADY;
  wire s1_axis_0_3_TVALID;
  wire [127:0]s1_axis_0_4_TDATA;
  wire s1_axis_0_4_TREADY;
  wire s1_axis_0_4_TVALID;
  wire [5:0]s_axi_0_10_ARADDR;
  wire [2:0]s_axi_0_10_ARPROT;
  wire s_axi_0_10_ARREADY;
  wire s_axi_0_10_ARVALID;
  wire [5:0]s_axi_0_10_AWADDR;
  wire [2:0]s_axi_0_10_AWPROT;
  wire s_axi_0_10_AWREADY;
  wire s_axi_0_10_AWVALID;
  wire s_axi_0_10_BREADY;
  wire [1:0]s_axi_0_10_BRESP;
  wire s_axi_0_10_BVALID;
  wire [31:0]s_axi_0_10_RDATA;
  wire s_axi_0_10_RREADY;
  wire [1:0]s_axi_0_10_RRESP;
  wire s_axi_0_10_RVALID;
  wire [31:0]s_axi_0_10_WDATA;
  wire s_axi_0_10_WREADY;
  wire [3:0]s_axi_0_10_WSTRB;
  wire s_axi_0_10_WVALID;
  wire [5:0]s_axi_0_11_ARADDR;
  wire [2:0]s_axi_0_11_ARPROT;
  wire s_axi_0_11_ARREADY;
  wire s_axi_0_11_ARVALID;
  wire [5:0]s_axi_0_11_AWADDR;
  wire [2:0]s_axi_0_11_AWPROT;
  wire s_axi_0_11_AWREADY;
  wire s_axi_0_11_AWVALID;
  wire s_axi_0_11_BREADY;
  wire [1:0]s_axi_0_11_BRESP;
  wire s_axi_0_11_BVALID;
  wire [31:0]s_axi_0_11_RDATA;
  wire s_axi_0_11_RREADY;
  wire [1:0]s_axi_0_11_RRESP;
  wire s_axi_0_11_RVALID;
  wire [31:0]s_axi_0_11_WDATA;
  wire s_axi_0_11_WREADY;
  wire [3:0]s_axi_0_11_WSTRB;
  wire s_axi_0_11_WVALID;
  wire [5:0]s_axi_0_12_ARADDR;
  wire [2:0]s_axi_0_12_ARPROT;
  wire s_axi_0_12_ARREADY;
  wire s_axi_0_12_ARVALID;
  wire [5:0]s_axi_0_12_AWADDR;
  wire [2:0]s_axi_0_12_AWPROT;
  wire s_axi_0_12_AWREADY;
  wire s_axi_0_12_AWVALID;
  wire s_axi_0_12_BREADY;
  wire [1:0]s_axi_0_12_BRESP;
  wire s_axi_0_12_BVALID;
  wire [31:0]s_axi_0_12_RDATA;
  wire s_axi_0_12_RREADY;
  wire [1:0]s_axi_0_12_RRESP;
  wire s_axi_0_12_RVALID;
  wire [31:0]s_axi_0_12_WDATA;
  wire s_axi_0_12_WREADY;
  wire [3:0]s_axi_0_12_WSTRB;
  wire s_axi_0_12_WVALID;
  wire [5:0]s_axi_0_13_ARADDR;
  wire [2:0]s_axi_0_13_ARPROT;
  wire s_axi_0_13_ARREADY;
  wire s_axi_0_13_ARVALID;
  wire [5:0]s_axi_0_13_AWADDR;
  wire [2:0]s_axi_0_13_AWPROT;
  wire s_axi_0_13_AWREADY;
  wire s_axi_0_13_AWVALID;
  wire s_axi_0_13_BREADY;
  wire [1:0]s_axi_0_13_BRESP;
  wire s_axi_0_13_BVALID;
  wire [31:0]s_axi_0_13_RDATA;
  wire s_axi_0_13_RREADY;
  wire [1:0]s_axi_0_13_RRESP;
  wire s_axi_0_13_RVALID;
  wire [31:0]s_axi_0_13_WDATA;
  wire s_axi_0_13_WREADY;
  wire [3:0]s_axi_0_13_WSTRB;
  wire s_axi_0_13_WVALID;
  wire [5:0]s_axi_0_14_ARADDR;
  wire [2:0]s_axi_0_14_ARPROT;
  wire s_axi_0_14_ARREADY;
  wire s_axi_0_14_ARVALID;
  wire [5:0]s_axi_0_14_AWADDR;
  wire [2:0]s_axi_0_14_AWPROT;
  wire s_axi_0_14_AWREADY;
  wire s_axi_0_14_AWVALID;
  wire s_axi_0_14_BREADY;
  wire [1:0]s_axi_0_14_BRESP;
  wire s_axi_0_14_BVALID;
  wire [31:0]s_axi_0_14_RDATA;
  wire s_axi_0_14_RREADY;
  wire [1:0]s_axi_0_14_RRESP;
  wire s_axi_0_14_RVALID;
  wire [31:0]s_axi_0_14_WDATA;
  wire s_axi_0_14_WREADY;
  wire [3:0]s_axi_0_14_WSTRB;
  wire s_axi_0_14_WVALID;
  wire [5:0]s_axi_0_15_ARADDR;
  wire [2:0]s_axi_0_15_ARPROT;
  wire s_axi_0_15_ARREADY;
  wire s_axi_0_15_ARVALID;
  wire [5:0]s_axi_0_15_AWADDR;
  wire [2:0]s_axi_0_15_AWPROT;
  wire s_axi_0_15_AWREADY;
  wire s_axi_0_15_AWVALID;
  wire s_axi_0_15_BREADY;
  wire [1:0]s_axi_0_15_BRESP;
  wire s_axi_0_15_BVALID;
  wire [31:0]s_axi_0_15_RDATA;
  wire s_axi_0_15_RREADY;
  wire [1:0]s_axi_0_15_RRESP;
  wire s_axi_0_15_RVALID;
  wire [31:0]s_axi_0_15_WDATA;
  wire s_axi_0_15_WREADY;
  wire [3:0]s_axi_0_15_WSTRB;
  wire s_axi_0_15_WVALID;
  wire [5:0]s_axi_0_16_ARADDR;
  wire [2:0]s_axi_0_16_ARPROT;
  wire s_axi_0_16_ARREADY;
  wire s_axi_0_16_ARVALID;
  wire [5:0]s_axi_0_16_AWADDR;
  wire [2:0]s_axi_0_16_AWPROT;
  wire s_axi_0_16_AWREADY;
  wire s_axi_0_16_AWVALID;
  wire s_axi_0_16_BREADY;
  wire [1:0]s_axi_0_16_BRESP;
  wire s_axi_0_16_BVALID;
  wire [31:0]s_axi_0_16_RDATA;
  wire s_axi_0_16_RREADY;
  wire [1:0]s_axi_0_16_RRESP;
  wire s_axi_0_16_RVALID;
  wire [31:0]s_axi_0_16_WDATA;
  wire s_axi_0_16_WREADY;
  wire [3:0]s_axi_0_16_WSTRB;
  wire s_axi_0_16_WVALID;
  wire [31:0]s_axi_0_17_ARADDR;
  wire [2:0]s_axi_0_17_ARPROT;
  wire s_axi_0_17_ARREADY;
  wire s_axi_0_17_ARVALID;
  wire [31:0]s_axi_0_17_AWADDR;
  wire [2:0]s_axi_0_17_AWPROT;
  wire s_axi_0_17_AWREADY;
  wire s_axi_0_17_AWVALID;
  wire s_axi_0_17_BREADY;
  wire [1:0]s_axi_0_17_BRESP;
  wire s_axi_0_17_BVALID;
  wire [31:0]s_axi_0_17_RDATA;
  wire s_axi_0_17_RREADY;
  wire [1:0]s_axi_0_17_RRESP;
  wire s_axi_0_17_RVALID;
  wire [31:0]s_axi_0_17_WDATA;
  wire s_axi_0_17_WREADY;
  wire [3:0]s_axi_0_17_WSTRB;
  wire s_axi_0_17_WVALID;
  wire [7:0]s_axi_0_18_ARADDR;
  wire [2:0]s_axi_0_18_ARPROT;
  wire s_axi_0_18_ARREADY;
  wire s_axi_0_18_ARVALID;
  wire [7:0]s_axi_0_18_AWADDR;
  wire [2:0]s_axi_0_18_AWPROT;
  wire s_axi_0_18_AWREADY;
  wire s_axi_0_18_AWVALID;
  wire s_axi_0_18_BREADY;
  wire [1:0]s_axi_0_18_BRESP;
  wire s_axi_0_18_BVALID;
  wire [31:0]s_axi_0_18_RDATA;
  wire s_axi_0_18_RREADY;
  wire [1:0]s_axi_0_18_RRESP;
  wire s_axi_0_18_RVALID;
  wire [31:0]s_axi_0_18_WDATA;
  wire s_axi_0_18_WREADY;
  wire [3:0]s_axi_0_18_WSTRB;
  wire s_axi_0_18_WVALID;
  wire [5:0]s_axi_0_1_ARADDR;
  wire [2:0]s_axi_0_1_ARPROT;
  wire s_axi_0_1_ARREADY;
  wire s_axi_0_1_ARVALID;
  wire [5:0]s_axi_0_1_AWADDR;
  wire [2:0]s_axi_0_1_AWPROT;
  wire s_axi_0_1_AWREADY;
  wire s_axi_0_1_AWVALID;
  wire s_axi_0_1_BREADY;
  wire [1:0]s_axi_0_1_BRESP;
  wire s_axi_0_1_BVALID;
  wire [31:0]s_axi_0_1_RDATA;
  wire s_axi_0_1_RREADY;
  wire [1:0]s_axi_0_1_RRESP;
  wire s_axi_0_1_RVALID;
  wire [31:0]s_axi_0_1_WDATA;
  wire s_axi_0_1_WREADY;
  wire [3:0]s_axi_0_1_WSTRB;
  wire s_axi_0_1_WVALID;
  wire [5:0]s_axi_0_2_ARADDR;
  wire [2:0]s_axi_0_2_ARPROT;
  wire s_axi_0_2_ARREADY;
  wire s_axi_0_2_ARVALID;
  wire [5:0]s_axi_0_2_AWADDR;
  wire [2:0]s_axi_0_2_AWPROT;
  wire s_axi_0_2_AWREADY;
  wire s_axi_0_2_AWVALID;
  wire s_axi_0_2_BREADY;
  wire [1:0]s_axi_0_2_BRESP;
  wire s_axi_0_2_BVALID;
  wire [31:0]s_axi_0_2_RDATA;
  wire s_axi_0_2_RREADY;
  wire [1:0]s_axi_0_2_RRESP;
  wire s_axi_0_2_RVALID;
  wire [31:0]s_axi_0_2_WDATA;
  wire s_axi_0_2_WREADY;
  wire [3:0]s_axi_0_2_WSTRB;
  wire s_axi_0_2_WVALID;
  wire [5:0]s_axi_0_3_ARADDR;
  wire [2:0]s_axi_0_3_ARPROT;
  wire s_axi_0_3_ARREADY;
  wire s_axi_0_3_ARVALID;
  wire [5:0]s_axi_0_3_AWADDR;
  wire [2:0]s_axi_0_3_AWPROT;
  wire s_axi_0_3_AWREADY;
  wire s_axi_0_3_AWVALID;
  wire s_axi_0_3_BREADY;
  wire [1:0]s_axi_0_3_BRESP;
  wire s_axi_0_3_BVALID;
  wire [31:0]s_axi_0_3_RDATA;
  wire s_axi_0_3_RREADY;
  wire [1:0]s_axi_0_3_RRESP;
  wire s_axi_0_3_RVALID;
  wire [31:0]s_axi_0_3_WDATA;
  wire s_axi_0_3_WREADY;
  wire [3:0]s_axi_0_3_WSTRB;
  wire s_axi_0_3_WVALID;
  wire [5:0]s_axi_0_4_ARADDR;
  wire [2:0]s_axi_0_4_ARPROT;
  wire s_axi_0_4_ARREADY;
  wire s_axi_0_4_ARVALID;
  wire [5:0]s_axi_0_4_AWADDR;
  wire [2:0]s_axi_0_4_AWPROT;
  wire s_axi_0_4_AWREADY;
  wire s_axi_0_4_AWVALID;
  wire s_axi_0_4_BREADY;
  wire [1:0]s_axi_0_4_BRESP;
  wire s_axi_0_4_BVALID;
  wire [31:0]s_axi_0_4_RDATA;
  wire s_axi_0_4_RREADY;
  wire [1:0]s_axi_0_4_RRESP;
  wire s_axi_0_4_RVALID;
  wire [31:0]s_axi_0_4_WDATA;
  wire s_axi_0_4_WREADY;
  wire [3:0]s_axi_0_4_WSTRB;
  wire s_axi_0_4_WVALID;
  wire [5:0]s_axi_0_5_ARADDR;
  wire [2:0]s_axi_0_5_ARPROT;
  wire s_axi_0_5_ARREADY;
  wire s_axi_0_5_ARVALID;
  wire [5:0]s_axi_0_5_AWADDR;
  wire [2:0]s_axi_0_5_AWPROT;
  wire s_axi_0_5_AWREADY;
  wire s_axi_0_5_AWVALID;
  wire s_axi_0_5_BREADY;
  wire [1:0]s_axi_0_5_BRESP;
  wire s_axi_0_5_BVALID;
  wire [31:0]s_axi_0_5_RDATA;
  wire s_axi_0_5_RREADY;
  wire [1:0]s_axi_0_5_RRESP;
  wire s_axi_0_5_RVALID;
  wire [31:0]s_axi_0_5_WDATA;
  wire s_axi_0_5_WREADY;
  wire [3:0]s_axi_0_5_WSTRB;
  wire s_axi_0_5_WVALID;
  wire [5:0]s_axi_0_6_ARADDR;
  wire [2:0]s_axi_0_6_ARPROT;
  wire s_axi_0_6_ARREADY;
  wire s_axi_0_6_ARVALID;
  wire [5:0]s_axi_0_6_AWADDR;
  wire [2:0]s_axi_0_6_AWPROT;
  wire s_axi_0_6_AWREADY;
  wire s_axi_0_6_AWVALID;
  wire s_axi_0_6_BREADY;
  wire [1:0]s_axi_0_6_BRESP;
  wire s_axi_0_6_BVALID;
  wire [31:0]s_axi_0_6_RDATA;
  wire s_axi_0_6_RREADY;
  wire [1:0]s_axi_0_6_RRESP;
  wire s_axi_0_6_RVALID;
  wire [31:0]s_axi_0_6_WDATA;
  wire s_axi_0_6_WREADY;
  wire [3:0]s_axi_0_6_WSTRB;
  wire s_axi_0_6_WVALID;
  wire [5:0]s_axi_0_7_ARADDR;
  wire [2:0]s_axi_0_7_ARPROT;
  wire s_axi_0_7_ARREADY;
  wire s_axi_0_7_ARVALID;
  wire [5:0]s_axi_0_7_AWADDR;
  wire [2:0]s_axi_0_7_AWPROT;
  wire s_axi_0_7_AWREADY;
  wire s_axi_0_7_AWVALID;
  wire s_axi_0_7_BREADY;
  wire [1:0]s_axi_0_7_BRESP;
  wire s_axi_0_7_BVALID;
  wire [31:0]s_axi_0_7_RDATA;
  wire s_axi_0_7_RREADY;
  wire [1:0]s_axi_0_7_RRESP;
  wire s_axi_0_7_RVALID;
  wire [31:0]s_axi_0_7_WDATA;
  wire s_axi_0_7_WREADY;
  wire [3:0]s_axi_0_7_WSTRB;
  wire s_axi_0_7_WVALID;
  wire [5:0]s_axi_0_8_ARADDR;
  wire [2:0]s_axi_0_8_ARPROT;
  wire s_axi_0_8_ARREADY;
  wire s_axi_0_8_ARVALID;
  wire [5:0]s_axi_0_8_AWADDR;
  wire [2:0]s_axi_0_8_AWPROT;
  wire s_axi_0_8_AWREADY;
  wire s_axi_0_8_AWVALID;
  wire s_axi_0_8_BREADY;
  wire [1:0]s_axi_0_8_BRESP;
  wire s_axi_0_8_BVALID;
  wire [31:0]s_axi_0_8_RDATA;
  wire s_axi_0_8_RREADY;
  wire [1:0]s_axi_0_8_RRESP;
  wire s_axi_0_8_RVALID;
  wire [31:0]s_axi_0_8_WDATA;
  wire s_axi_0_8_WREADY;
  wire [3:0]s_axi_0_8_WSTRB;
  wire s_axi_0_8_WVALID;
  wire [5:0]s_axi_0_9_ARADDR;
  wire [2:0]s_axi_0_9_ARPROT;
  wire s_axi_0_9_ARREADY;
  wire s_axi_0_9_ARVALID;
  wire [5:0]s_axi_0_9_AWADDR;
  wire [2:0]s_axi_0_9_AWPROT;
  wire s_axi_0_9_AWREADY;
  wire s_axi_0_9_AWVALID;
  wire s_axi_0_9_BREADY;
  wire [1:0]s_axi_0_9_BRESP;
  wire s_axi_0_9_BVALID;
  wire [31:0]s_axi_0_9_RDATA;
  wire s_axi_0_9_RREADY;
  wire [1:0]s_axi_0_9_RRESP;
  wire s_axi_0_9_RVALID;
  wire [31:0]s_axi_0_9_WDATA;
  wire s_axi_0_9_WREADY;
  wire [3:0]s_axi_0_9_WSTRB;
  wire s_axi_0_9_WVALID;
  wire [63:0]xlconstant_0_dout;
  wire [0:0]xlconstant_1_dout;
  wire [0:0]xlconstant_2_dout;
  wire [7:0]xlconstant_3_dout;
  wire [11:0]xlconstant_4_dout;
  wire [47:0]NLW_axis_switch_gen_m_axis_tkeep_UNCONNECTED;
  wire [11:0]NLW_axis_switch_gen_m_axis_tlast_UNCONNECTED;

  assign S00_AXIS_0_1_TDATA = ext_axis_switch_gen_S00_AXIS_tdata[31:0];
  assign S00_AXIS_0_1_TKEEP = ext_axis_switch_gen_S00_AXIS_tkeep[3:0];
  assign S00_AXIS_0_1_TLAST = ext_axis_switch_gen_S00_AXIS_tlast[0];
  assign S00_AXIS_0_1_TVALID = ext_axis_switch_gen_S00_AXIS_tvalid[0];
  assign S_AXI_CTRL_0_1_ARADDR = ext_axis_switch_avg_S_AXI_CTRL_araddr[6:0];
  assign S_AXI_CTRL_0_1_ARVALID = ext_axis_switch_avg_S_AXI_CTRL_arvalid;
  assign S_AXI_CTRL_0_1_AWADDR = ext_axis_switch_avg_S_AXI_CTRL_awaddr[6:0];
  assign S_AXI_CTRL_0_1_AWVALID = ext_axis_switch_avg_S_AXI_CTRL_awvalid;
  assign S_AXI_CTRL_0_1_BREADY = ext_axis_switch_avg_S_AXI_CTRL_bready;
  assign S_AXI_CTRL_0_1_RREADY = ext_axis_switch_avg_S_AXI_CTRL_rready;
  assign S_AXI_CTRL_0_1_WDATA = ext_axis_switch_avg_S_AXI_CTRL_wdata[31:0];
  assign S_AXI_CTRL_0_1_WVALID = ext_axis_switch_avg_S_AXI_CTRL_wvalid;
  assign S_AXI_CTRL_0_2_ARADDR = ext_axis_switch_buf_S_AXI_CTRL_araddr[6:0];
  assign S_AXI_CTRL_0_2_ARVALID = ext_axis_switch_buf_S_AXI_CTRL_arvalid;
  assign S_AXI_CTRL_0_2_AWADDR = ext_axis_switch_buf_S_AXI_CTRL_awaddr[6:0];
  assign S_AXI_CTRL_0_2_AWVALID = ext_axis_switch_buf_S_AXI_CTRL_awvalid;
  assign S_AXI_CTRL_0_2_BREADY = ext_axis_switch_buf_S_AXI_CTRL_bready;
  assign S_AXI_CTRL_0_2_RREADY = ext_axis_switch_buf_S_AXI_CTRL_rready;
  assign S_AXI_CTRL_0_2_WDATA = ext_axis_switch_buf_S_AXI_CTRL_wdata[31:0];
  assign S_AXI_CTRL_0_2_WVALID = ext_axis_switch_buf_S_AXI_CTRL_wvalid;
  assign S_AXI_CTRL_0_3_ARADDR = ext_axis_switch_ddr_S_AXI_CTRL_araddr[6:0];
  assign S_AXI_CTRL_0_3_ARVALID = ext_axis_switch_ddr_S_AXI_CTRL_arvalid;
  assign S_AXI_CTRL_0_3_AWADDR = ext_axis_switch_ddr_S_AXI_CTRL_awaddr[6:0];
  assign S_AXI_CTRL_0_3_AWVALID = ext_axis_switch_ddr_S_AXI_CTRL_awvalid;
  assign S_AXI_CTRL_0_3_BREADY = ext_axis_switch_ddr_S_AXI_CTRL_bready;
  assign S_AXI_CTRL_0_3_RREADY = ext_axis_switch_ddr_S_AXI_CTRL_rready;
  assign S_AXI_CTRL_0_3_WDATA = ext_axis_switch_ddr_S_AXI_CTRL_wdata[31:0];
  assign S_AXI_CTRL_0_3_WVALID = ext_axis_switch_ddr_S_AXI_CTRL_wvalid;
  assign S_AXI_CTRL_0_4_ARADDR = ext_axis_switch_gen_S_AXI_CTRL_araddr[6:0];
  assign S_AXI_CTRL_0_4_ARVALID = ext_axis_switch_gen_S_AXI_CTRL_arvalid;
  assign S_AXI_CTRL_0_4_AWADDR = ext_axis_switch_gen_S_AXI_CTRL_awaddr[6:0];
  assign S_AXI_CTRL_0_4_AWVALID = ext_axis_switch_gen_S_AXI_CTRL_awvalid;
  assign S_AXI_CTRL_0_4_BREADY = ext_axis_switch_gen_S_AXI_CTRL_bready;
  assign S_AXI_CTRL_0_4_RREADY = ext_axis_switch_gen_S_AXI_CTRL_rready;
  assign S_AXI_CTRL_0_4_WDATA = ext_axis_switch_gen_S_AXI_CTRL_wdata[31:0];
  assign S_AXI_CTRL_0_4_WVALID = ext_axis_switch_gen_S_AXI_CTRL_wvalid;
  assign S_AXI_CTRL_0_5_ARADDR = ext_axis_switch_mr_S_AXI_CTRL_araddr[6:0];
  assign S_AXI_CTRL_0_5_ARVALID = ext_axis_switch_mr_S_AXI_CTRL_arvalid;
  assign S_AXI_CTRL_0_5_AWADDR = ext_axis_switch_mr_S_AXI_CTRL_awaddr[6:0];
  assign S_AXI_CTRL_0_5_AWVALID = ext_axis_switch_mr_S_AXI_CTRL_awvalid;
  assign S_AXI_CTRL_0_5_BREADY = ext_axis_switch_mr_S_AXI_CTRL_bready;
  assign S_AXI_CTRL_0_5_RREADY = ext_axis_switch_mr_S_AXI_CTRL_rready;
  assign S_AXI_CTRL_0_5_WDATA = ext_axis_switch_mr_S_AXI_CTRL_wdata[31:0];
  assign S_AXI_CTRL_0_5_WVALID = ext_axis_switch_mr_S_AXI_CTRL_wvalid;
  assign axis_register_slice_0_m_axis_TREADY = ext_axis_register_slice_0_m_axis_tready;
  assign axis_register_slice_10_m_axis_TREADY = ext_axis_register_slice_10_m_axis_tready;
  assign axis_register_slice_11_m_axis_TREADY = ext_axis_register_slice_11_m_axis_tready;
  assign axis_register_slice_12_m_axis_TREADY = ext_axis_register_slice_12_m_axis_tready;
  assign axis_register_slice_13_m_axis_TREADY = ext_axis_register_slice_13_m_axis_tready;
  assign axis_register_slice_14_m_axis_TREADY = ext_axis_register_slice_14_m_axis_tready;
  assign axis_register_slice_15_m_axis_TREADY = ext_axis_register_slice_15_m_axis_tready;
  assign axis_register_slice_16_m_axis_TREADY = ext_axis_register_slice_16_m_axis_tready;
  assign axis_register_slice_1_m_axis_TREADY = ext_axis_register_slice_1_m_axis_tready;
  assign axis_register_slice_2_m_axis_TREADY = ext_axis_register_slice_2_m_axis_tready;
  assign axis_register_slice_3_m_axis_TREADY = ext_axis_register_slice_3_m_axis_tready;
  assign axis_register_slice_8_m_axis_TREADY = ext_axis_register_slice_8_m_axis_tready;
  assign axis_switch_avg_M00_AXIS_TREADY = ext_axis_switch_avg_M00_AXIS_tready[0];
  assign axis_switch_buf_M00_AXIS_TREADY = ext_axis_switch_buf_M00_AXIS_tready[0];
  assign axis_switch_gen_M04_AXIS_TREADY = ext_axis_switch_gen_M04_AXIS_tready[0];
  assign axis_switch_gen_M05_AXIS_TREADY = ext_axis_switch_gen_M05_AXIS_tready[0];
  assign axis_switch_gen_M06_AXIS_TREADY = ext_axis_switch_gen_M06_AXIS_tready[0];
  assign axis_switch_gen_M07_AXIS_TREADY = ext_axis_switch_gen_M07_AXIS_tready[0];
  assign axis_switch_gen_M08_AXIS_TREADY = ext_axis_switch_gen_M08_AXIS_tready[0];
  assign axis_switch_gen_M09_AXIS_TREADY = ext_axis_switch_gen_M09_AXIS_tready[0];
  assign axis_switch_gen_M10_AXIS_TREADY = ext_axis_switch_gen_M10_AXIS_tready[0];
  assign axis_switch_gen_M11_AXIS_TREADY = ext_axis_switch_gen_M11_AXIS_tready[0];
  assign axis_tproc64x32_x8_0_m0_axis_TREADY = ext_axis_tproc64x32_x8_0_m0_axis_tready;
  assign clk_300000000_1 = clk_300000000;
  assign clk_333250000_1 = clk_333250000;
  assign clk_99999985_1 = clk_99999985;
  assign ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWREADY = ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awready;
  assign ddr4_axis_buffer_ddr_sample_v3_0_m_axi_BID = ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bid[0];
  assign ddr4_axis_buffer_ddr_sample_v3_0_m_axi_BRESP = ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bresp[1:0];
  assign ddr4_axis_buffer_ddr_sample_v3_0_m_axi_BVALID = ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bvalid;
  assign ddr4_axis_buffer_ddr_sample_v3_0_m_axi_WREADY = ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wready;
  assign ext_axis_avg_buffer_0_s_axi_arready = s_axi_0_1_ARREADY;
  assign ext_axis_avg_buffer_0_s_axi_awready = s_axi_0_1_AWREADY;
  assign ext_axis_avg_buffer_0_s_axi_bresp[1:0] = s_axi_0_1_BRESP;
  assign ext_axis_avg_buffer_0_s_axi_bvalid = s_axi_0_1_BVALID;
  assign ext_axis_avg_buffer_0_s_axi_rdata[31:0] = s_axi_0_1_RDATA;
  assign ext_axis_avg_buffer_0_s_axi_rresp[1:0] = s_axi_0_1_RRESP;
  assign ext_axis_avg_buffer_0_s_axi_rvalid = s_axi_0_1_RVALID;
  assign ext_axis_avg_buffer_0_s_axi_wready = s_axi_0_1_WREADY;
  assign ext_axis_avg_buffer_1_s_axi_arready = s_axi_0_2_ARREADY;
  assign ext_axis_avg_buffer_1_s_axi_awready = s_axi_0_2_AWREADY;
  assign ext_axis_avg_buffer_1_s_axi_bresp[1:0] = s_axi_0_2_BRESP;
  assign ext_axis_avg_buffer_1_s_axi_bvalid = s_axi_0_2_BVALID;
  assign ext_axis_avg_buffer_1_s_axi_rdata[31:0] = s_axi_0_2_RDATA;
  assign ext_axis_avg_buffer_1_s_axi_rresp[1:0] = s_axi_0_2_RRESP;
  assign ext_axis_avg_buffer_1_s_axi_rvalid = s_axi_0_2_RVALID;
  assign ext_axis_avg_buffer_1_s_axi_wready = s_axi_0_2_WREADY;
  assign ext_axis_avg_buffer_2_s_axi_arready = s_axi_0_3_ARREADY;
  assign ext_axis_avg_buffer_2_s_axi_awready = s_axi_0_3_AWREADY;
  assign ext_axis_avg_buffer_2_s_axi_bresp[1:0] = s_axi_0_3_BRESP;
  assign ext_axis_avg_buffer_2_s_axi_bvalid = s_axi_0_3_BVALID;
  assign ext_axis_avg_buffer_2_s_axi_rdata[31:0] = s_axi_0_3_RDATA;
  assign ext_axis_avg_buffer_2_s_axi_rresp[1:0] = s_axi_0_3_RRESP;
  assign ext_axis_avg_buffer_2_s_axi_rvalid = s_axi_0_3_RVALID;
  assign ext_axis_avg_buffer_2_s_axi_wready = s_axi_0_3_WREADY;
  assign ext_axis_avg_buffer_3_s_axi_arready = s_axi_0_4_ARREADY;
  assign ext_axis_avg_buffer_3_s_axi_awready = s_axi_0_4_AWREADY;
  assign ext_axis_avg_buffer_3_s_axi_bresp[1:0] = s_axi_0_4_BRESP;
  assign ext_axis_avg_buffer_3_s_axi_bvalid = s_axi_0_4_BVALID;
  assign ext_axis_avg_buffer_3_s_axi_rdata[31:0] = s_axi_0_4_RDATA;
  assign ext_axis_avg_buffer_3_s_axi_rresp[1:0] = s_axi_0_4_RRESP;
  assign ext_axis_avg_buffer_3_s_axi_rvalid = s_axi_0_4_RVALID;
  assign ext_axis_avg_buffer_3_s_axi_wready = s_axi_0_4_WREADY;
  assign ext_axis_awg_tuning_v1_10_s_axi_arready = s_axi_0_5_ARREADY;
  assign ext_axis_awg_tuning_v1_10_s_axi_awready = s_axi_0_5_AWREADY;
  assign ext_axis_awg_tuning_v1_10_s_axi_bresp[1:0] = s_axi_0_5_BRESP;
  assign ext_axis_awg_tuning_v1_10_s_axi_bvalid = s_axi_0_5_BVALID;
  assign ext_axis_awg_tuning_v1_10_s_axi_rdata[31:0] = s_axi_0_5_RDATA;
  assign ext_axis_awg_tuning_v1_10_s_axi_rresp[1:0] = s_axi_0_5_RRESP;
  assign ext_axis_awg_tuning_v1_10_s_axi_rvalid = s_axi_0_5_RVALID;
  assign ext_axis_awg_tuning_v1_10_s_axi_wready = s_axi_0_5_WREADY;
  assign ext_axis_awg_tuning_v1_11_s_axi_arready = s_axi_0_6_ARREADY;
  assign ext_axis_awg_tuning_v1_11_s_axi_awready = s_axi_0_6_AWREADY;
  assign ext_axis_awg_tuning_v1_11_s_axi_bresp[1:0] = s_axi_0_6_BRESP;
  assign ext_axis_awg_tuning_v1_11_s_axi_bvalid = s_axi_0_6_BVALID;
  assign ext_axis_awg_tuning_v1_11_s_axi_rdata[31:0] = s_axi_0_6_RDATA;
  assign ext_axis_awg_tuning_v1_11_s_axi_rresp[1:0] = s_axi_0_6_RRESP;
  assign ext_axis_awg_tuning_v1_11_s_axi_rvalid = s_axi_0_6_RVALID;
  assign ext_axis_awg_tuning_v1_11_s_axi_wready = s_axi_0_6_WREADY;
  assign ext_axis_awg_tuning_v1_4_s_axi_arready = s_axi_0_7_ARREADY;
  assign ext_axis_awg_tuning_v1_4_s_axi_awready = s_axi_0_7_AWREADY;
  assign ext_axis_awg_tuning_v1_4_s_axi_bresp[1:0] = s_axi_0_7_BRESP;
  assign ext_axis_awg_tuning_v1_4_s_axi_bvalid = s_axi_0_7_BVALID;
  assign ext_axis_awg_tuning_v1_4_s_axi_rdata[31:0] = s_axi_0_7_RDATA;
  assign ext_axis_awg_tuning_v1_4_s_axi_rresp[1:0] = s_axi_0_7_RRESP;
  assign ext_axis_awg_tuning_v1_4_s_axi_rvalid = s_axi_0_7_RVALID;
  assign ext_axis_awg_tuning_v1_4_s_axi_wready = s_axi_0_7_WREADY;
  assign ext_axis_awg_tuning_v1_5_s_axi_arready = s_axi_0_8_ARREADY;
  assign ext_axis_awg_tuning_v1_5_s_axi_awready = s_axi_0_8_AWREADY;
  assign ext_axis_awg_tuning_v1_5_s_axi_bresp[1:0] = s_axi_0_8_BRESP;
  assign ext_axis_awg_tuning_v1_5_s_axi_bvalid = s_axi_0_8_BVALID;
  assign ext_axis_awg_tuning_v1_5_s_axi_rdata[31:0] = s_axi_0_8_RDATA;
  assign ext_axis_awg_tuning_v1_5_s_axi_rresp[1:0] = s_axi_0_8_RRESP;
  assign ext_axis_awg_tuning_v1_5_s_axi_rvalid = s_axi_0_8_RVALID;
  assign ext_axis_awg_tuning_v1_5_s_axi_wready = s_axi_0_8_WREADY;
  assign ext_axis_awg_tuning_v1_6_s_axi_arready = s_axi_0_9_ARREADY;
  assign ext_axis_awg_tuning_v1_6_s_axi_awready = s_axi_0_9_AWREADY;
  assign ext_axis_awg_tuning_v1_6_s_axi_bresp[1:0] = s_axi_0_9_BRESP;
  assign ext_axis_awg_tuning_v1_6_s_axi_bvalid = s_axi_0_9_BVALID;
  assign ext_axis_awg_tuning_v1_6_s_axi_rdata[31:0] = s_axi_0_9_RDATA;
  assign ext_axis_awg_tuning_v1_6_s_axi_rresp[1:0] = s_axi_0_9_RRESP;
  assign ext_axis_awg_tuning_v1_6_s_axi_rvalid = s_axi_0_9_RVALID;
  assign ext_axis_awg_tuning_v1_6_s_axi_wready = s_axi_0_9_WREADY;
  assign ext_axis_awg_tuning_v1_8_s_axi_arready = s_axi_0_10_ARREADY;
  assign ext_axis_awg_tuning_v1_8_s_axi_awready = s_axi_0_10_AWREADY;
  assign ext_axis_awg_tuning_v1_8_s_axi_bresp[1:0] = s_axi_0_10_BRESP;
  assign ext_axis_awg_tuning_v1_8_s_axi_bvalid = s_axi_0_10_BVALID;
  assign ext_axis_awg_tuning_v1_8_s_axi_rdata[31:0] = s_axi_0_10_RDATA;
  assign ext_axis_awg_tuning_v1_8_s_axi_rresp[1:0] = s_axi_0_10_RRESP;
  assign ext_axis_awg_tuning_v1_8_s_axi_rvalid = s_axi_0_10_RVALID;
  assign ext_axis_awg_tuning_v1_8_s_axi_wready = s_axi_0_10_WREADY;
  assign ext_axis_awg_tuning_v1_9_s_axi_arready = s_axi_0_11_ARREADY;
  assign ext_axis_awg_tuning_v1_9_s_axi_awready = s_axi_0_11_AWREADY;
  assign ext_axis_awg_tuning_v1_9_s_axi_bresp[1:0] = s_axi_0_11_BRESP;
  assign ext_axis_awg_tuning_v1_9_s_axi_bvalid = s_axi_0_11_BVALID;
  assign ext_axis_awg_tuning_v1_9_s_axi_rdata[31:0] = s_axi_0_11_RDATA;
  assign ext_axis_awg_tuning_v1_9_s_axi_rresp[1:0] = s_axi_0_11_RRESP;
  assign ext_axis_awg_tuning_v1_9_s_axi_rvalid = s_axi_0_11_RVALID;
  assign ext_axis_awg_tuning_v1_9_s_axi_wready = s_axi_0_11_WREADY;
  assign ext_axis_dyn_readout_v1_0_s1_axis_tready = s1_axis_0_1_TREADY;
  assign ext_axis_dyn_readout_v1_1_s1_axis_tready = s1_axis_0_2_TREADY;
  assign ext_axis_dyn_readout_v1_2_s1_axis_tready = s1_axis_0_3_TREADY;
  assign ext_axis_dyn_readout_v1_3_s1_axis_tready = s1_axis_0_4_TREADY;
  assign ext_axis_register_slice_0_m_axis_tdata[255:0] = axis_register_slice_0_m_axis_TDATA;
  assign ext_axis_register_slice_0_m_axis_tvalid = axis_register_slice_0_m_axis_TVALID;
  assign ext_axis_register_slice_10_m_axis_tdata[255:0] = axis_register_slice_10_m_axis_TDATA;
  assign ext_axis_register_slice_10_m_axis_tvalid = axis_register_slice_10_m_axis_TVALID;
  assign ext_axis_register_slice_11_m_axis_tdata[255:0] = axis_register_slice_11_m_axis_TDATA;
  assign ext_axis_register_slice_11_m_axis_tvalid = axis_register_slice_11_m_axis_TVALID;
  assign ext_axis_register_slice_12_m_axis_tdata[255:0] = axis_register_slice_12_m_axis_TDATA;
  assign ext_axis_register_slice_12_m_axis_tvalid = axis_register_slice_12_m_axis_TVALID;
  assign ext_axis_register_slice_13_m_axis_tdata[255:0] = axis_register_slice_13_m_axis_TDATA;
  assign ext_axis_register_slice_13_m_axis_tvalid = axis_register_slice_13_m_axis_TVALID;
  assign ext_axis_register_slice_14_m_axis_tdata[255:0] = axis_register_slice_14_m_axis_TDATA;
  assign ext_axis_register_slice_14_m_axis_tvalid = axis_register_slice_14_m_axis_TVALID;
  assign ext_axis_register_slice_15_m_axis_tdata[255:0] = axis_register_slice_15_m_axis_TDATA;
  assign ext_axis_register_slice_15_m_axis_tvalid = axis_register_slice_15_m_axis_TVALID;
  assign ext_axis_register_slice_16_m_axis_tdata[255:0] = axis_register_slice_16_m_axis_TDATA;
  assign ext_axis_register_slice_16_m_axis_tvalid = axis_register_slice_16_m_axis_TVALID;
  assign ext_axis_register_slice_1_m_axis_tdata[255:0] = axis_register_slice_1_m_axis_TDATA;
  assign ext_axis_register_slice_1_m_axis_tvalid = axis_register_slice_1_m_axis_TVALID;
  assign ext_axis_register_slice_2_m_axis_tdata[255:0] = axis_register_slice_2_m_axis_TDATA;
  assign ext_axis_register_slice_2_m_axis_tvalid = axis_register_slice_2_m_axis_TVALID;
  assign ext_axis_register_slice_3_m_axis_tdata[255:0] = axis_register_slice_3_m_axis_TDATA;
  assign ext_axis_register_slice_3_m_axis_tvalid = axis_register_slice_3_m_axis_TVALID;
  assign ext_axis_register_slice_8_m_axis_tdata[255:0] = axis_register_slice_8_m_axis_TDATA;
  assign ext_axis_register_slice_8_m_axis_tvalid = axis_register_slice_8_m_axis_TVALID;
  assign ext_axis_signal_gen_v6_0_s_axi_arready = s_axi_0_12_ARREADY;
  assign ext_axis_signal_gen_v6_0_s_axi_awready = s_axi_0_12_AWREADY;
  assign ext_axis_signal_gen_v6_0_s_axi_bresp[1:0] = s_axi_0_12_BRESP;
  assign ext_axis_signal_gen_v6_0_s_axi_bvalid = s_axi_0_12_BVALID;
  assign ext_axis_signal_gen_v6_0_s_axi_rdata[31:0] = s_axi_0_12_RDATA;
  assign ext_axis_signal_gen_v6_0_s_axi_rresp[1:0] = s_axi_0_12_RRESP;
  assign ext_axis_signal_gen_v6_0_s_axi_rvalid = s_axi_0_12_RVALID;
  assign ext_axis_signal_gen_v6_0_s_axi_wready = s_axi_0_12_WREADY;
  assign ext_axis_signal_gen_v6_1_s_axi_arready = s_axi_0_13_ARREADY;
  assign ext_axis_signal_gen_v6_1_s_axi_awready = s_axi_0_13_AWREADY;
  assign ext_axis_signal_gen_v6_1_s_axi_bresp[1:0] = s_axi_0_13_BRESP;
  assign ext_axis_signal_gen_v6_1_s_axi_bvalid = s_axi_0_13_BVALID;
  assign ext_axis_signal_gen_v6_1_s_axi_rdata[31:0] = s_axi_0_13_RDATA;
  assign ext_axis_signal_gen_v6_1_s_axi_rresp[1:0] = s_axi_0_13_RRESP;
  assign ext_axis_signal_gen_v6_1_s_axi_rvalid = s_axi_0_13_RVALID;
  assign ext_axis_signal_gen_v6_1_s_axi_wready = s_axi_0_13_WREADY;
  assign ext_axis_signal_gen_v6_2_s_axi_arready = s_axi_0_14_ARREADY;
  assign ext_axis_signal_gen_v6_2_s_axi_awready = s_axi_0_14_AWREADY;
  assign ext_axis_signal_gen_v6_2_s_axi_bresp[1:0] = s_axi_0_14_BRESP;
  assign ext_axis_signal_gen_v6_2_s_axi_bvalid = s_axi_0_14_BVALID;
  assign ext_axis_signal_gen_v6_2_s_axi_rdata[31:0] = s_axi_0_14_RDATA;
  assign ext_axis_signal_gen_v6_2_s_axi_rresp[1:0] = s_axi_0_14_RRESP;
  assign ext_axis_signal_gen_v6_2_s_axi_rvalid = s_axi_0_14_RVALID;
  assign ext_axis_signal_gen_v6_2_s_axi_wready = s_axi_0_14_WREADY;
  assign ext_axis_signal_gen_v6_3_s_axi_arready = s_axi_0_15_ARREADY;
  assign ext_axis_signal_gen_v6_3_s_axi_awready = s_axi_0_15_AWREADY;
  assign ext_axis_signal_gen_v6_3_s_axi_bresp[1:0] = s_axi_0_15_BRESP;
  assign ext_axis_signal_gen_v6_3_s_axi_bvalid = s_axi_0_15_BVALID;
  assign ext_axis_signal_gen_v6_3_s_axi_rdata[31:0] = s_axi_0_15_RDATA;
  assign ext_axis_signal_gen_v6_3_s_axi_rresp[1:0] = s_axi_0_15_RRESP;
  assign ext_axis_signal_gen_v6_3_s_axi_rvalid = s_axi_0_15_RVALID;
  assign ext_axis_signal_gen_v6_3_s_axi_wready = s_axi_0_15_WREADY;
  assign ext_axis_square_pulse_v1_0_s_axi_arready = s_axi_0_16_ARREADY;
  assign ext_axis_square_pulse_v1_0_s_axi_awready = s_axi_0_16_AWREADY;
  assign ext_axis_square_pulse_v1_0_s_axi_bresp[1:0] = s_axi_0_16_BRESP;
  assign ext_axis_square_pulse_v1_0_s_axi_bvalid = s_axi_0_16_BVALID;
  assign ext_axis_square_pulse_v1_0_s_axi_rdata[31:0] = s_axi_0_16_RDATA;
  assign ext_axis_square_pulse_v1_0_s_axi_rresp[1:0] = s_axi_0_16_RRESP;
  assign ext_axis_square_pulse_v1_0_s_axi_rvalid = s_axi_0_16_RVALID;
  assign ext_axis_square_pulse_v1_0_s_axi_wready = s_axi_0_16_WREADY;
  assign ext_axis_switch_avg_M00_AXIS_tdata[63:0] = axis_switch_avg_M00_AXIS_TDATA;
  assign ext_axis_switch_avg_M00_AXIS_tlast[0] = axis_switch_avg_M00_AXIS_TLAST;
  assign ext_axis_switch_avg_M00_AXIS_tvalid[0] = axis_switch_avg_M00_AXIS_TVALID;
  assign ext_axis_switch_avg_S_AXI_CTRL_arready = S_AXI_CTRL_0_1_ARREADY;
  assign ext_axis_switch_avg_S_AXI_CTRL_awready = S_AXI_CTRL_0_1_AWREADY;
  assign ext_axis_switch_avg_S_AXI_CTRL_bresp[1:0] = S_AXI_CTRL_0_1_BRESP;
  assign ext_axis_switch_avg_S_AXI_CTRL_bvalid = S_AXI_CTRL_0_1_BVALID;
  assign ext_axis_switch_avg_S_AXI_CTRL_rdata[31:0] = S_AXI_CTRL_0_1_RDATA;
  assign ext_axis_switch_avg_S_AXI_CTRL_rresp[1:0] = S_AXI_CTRL_0_1_RRESP;
  assign ext_axis_switch_avg_S_AXI_CTRL_rvalid = S_AXI_CTRL_0_1_RVALID;
  assign ext_axis_switch_avg_S_AXI_CTRL_wready = S_AXI_CTRL_0_1_WREADY;
  assign ext_axis_switch_buf_M00_AXIS_tdata[31:0] = axis_switch_buf_M00_AXIS_TDATA;
  assign ext_axis_switch_buf_M00_AXIS_tlast[0] = axis_switch_buf_M00_AXIS_TLAST;
  assign ext_axis_switch_buf_M00_AXIS_tvalid[0] = axis_switch_buf_M00_AXIS_TVALID;
  assign ext_axis_switch_buf_S_AXI_CTRL_arready = S_AXI_CTRL_0_2_ARREADY;
  assign ext_axis_switch_buf_S_AXI_CTRL_awready = S_AXI_CTRL_0_2_AWREADY;
  assign ext_axis_switch_buf_S_AXI_CTRL_bresp[1:0] = S_AXI_CTRL_0_2_BRESP;
  assign ext_axis_switch_buf_S_AXI_CTRL_bvalid = S_AXI_CTRL_0_2_BVALID;
  assign ext_axis_switch_buf_S_AXI_CTRL_rdata[31:0] = S_AXI_CTRL_0_2_RDATA;
  assign ext_axis_switch_buf_S_AXI_CTRL_rresp[1:0] = S_AXI_CTRL_0_2_RRESP;
  assign ext_axis_switch_buf_S_AXI_CTRL_rvalid = S_AXI_CTRL_0_2_RVALID;
  assign ext_axis_switch_buf_S_AXI_CTRL_wready = S_AXI_CTRL_0_2_WREADY;
  assign ext_axis_switch_ddr_S_AXI_CTRL_arready = S_AXI_CTRL_0_3_ARREADY;
  assign ext_axis_switch_ddr_S_AXI_CTRL_awready = S_AXI_CTRL_0_3_AWREADY;
  assign ext_axis_switch_ddr_S_AXI_CTRL_bresp[1:0] = S_AXI_CTRL_0_3_BRESP;
  assign ext_axis_switch_ddr_S_AXI_CTRL_bvalid = S_AXI_CTRL_0_3_BVALID;
  assign ext_axis_switch_ddr_S_AXI_CTRL_rdata[31:0] = S_AXI_CTRL_0_3_RDATA;
  assign ext_axis_switch_ddr_S_AXI_CTRL_rresp[1:0] = S_AXI_CTRL_0_3_RRESP;
  assign ext_axis_switch_ddr_S_AXI_CTRL_rvalid = S_AXI_CTRL_0_3_RVALID;
  assign ext_axis_switch_ddr_S_AXI_CTRL_wready = S_AXI_CTRL_0_3_WREADY;
  assign ext_axis_switch_gen_M04_AXIS_tdata[31:0] = axis_switch_gen_M04_AXIS_TDATA;
  assign ext_axis_switch_gen_M04_AXIS_tkeep[3:0] = axis_switch_gen_M04_AXIS_TKEEP;
  assign ext_axis_switch_gen_M04_AXIS_tlast[0] = axis_switch_gen_M04_AXIS_TLAST;
  assign ext_axis_switch_gen_M04_AXIS_tvalid[0] = axis_switch_gen_M04_AXIS_TVALID;
  assign ext_axis_switch_gen_M05_AXIS_tdata[31:0] = axis_switch_gen_M05_AXIS_TDATA;
  assign ext_axis_switch_gen_M05_AXIS_tkeep[3:0] = axis_switch_gen_M05_AXIS_TKEEP;
  assign ext_axis_switch_gen_M05_AXIS_tlast[0] = axis_switch_gen_M05_AXIS_TLAST;
  assign ext_axis_switch_gen_M05_AXIS_tvalid[0] = axis_switch_gen_M05_AXIS_TVALID;
  assign ext_axis_switch_gen_M06_AXIS_tdata[31:0] = axis_switch_gen_M06_AXIS_TDATA;
  assign ext_axis_switch_gen_M06_AXIS_tkeep[3:0] = axis_switch_gen_M06_AXIS_TKEEP;
  assign ext_axis_switch_gen_M06_AXIS_tlast[0] = axis_switch_gen_M06_AXIS_TLAST;
  assign ext_axis_switch_gen_M06_AXIS_tvalid[0] = axis_switch_gen_M06_AXIS_TVALID;
  assign ext_axis_switch_gen_M07_AXIS_tdata[31:0] = axis_switch_gen_M07_AXIS_TDATA;
  assign ext_axis_switch_gen_M07_AXIS_tkeep[3:0] = axis_switch_gen_M07_AXIS_TKEEP;
  assign ext_axis_switch_gen_M07_AXIS_tlast[0] = axis_switch_gen_M07_AXIS_TLAST;
  assign ext_axis_switch_gen_M07_AXIS_tvalid[0] = axis_switch_gen_M07_AXIS_TVALID;
  assign ext_axis_switch_gen_M08_AXIS_tdata[31:0] = axis_switch_gen_M08_AXIS_TDATA;
  assign ext_axis_switch_gen_M08_AXIS_tkeep[3:0] = axis_switch_gen_M08_AXIS_TKEEP;
  assign ext_axis_switch_gen_M08_AXIS_tlast[0] = axis_switch_gen_M08_AXIS_TLAST;
  assign ext_axis_switch_gen_M08_AXIS_tvalid[0] = axis_switch_gen_M08_AXIS_TVALID;
  assign ext_axis_switch_gen_M09_AXIS_tdata[31:0] = axis_switch_gen_M09_AXIS_TDATA;
  assign ext_axis_switch_gen_M09_AXIS_tkeep[3:0] = axis_switch_gen_M09_AXIS_TKEEP;
  assign ext_axis_switch_gen_M09_AXIS_tlast[0] = axis_switch_gen_M09_AXIS_TLAST;
  assign ext_axis_switch_gen_M09_AXIS_tvalid[0] = axis_switch_gen_M09_AXIS_TVALID;
  assign ext_axis_switch_gen_M10_AXIS_tdata[31:0] = axis_switch_gen_M10_AXIS_TDATA;
  assign ext_axis_switch_gen_M10_AXIS_tkeep[3:0] = axis_switch_gen_M10_AXIS_TKEEP;
  assign ext_axis_switch_gen_M10_AXIS_tlast[0] = axis_switch_gen_M10_AXIS_TLAST;
  assign ext_axis_switch_gen_M10_AXIS_tvalid[0] = axis_switch_gen_M10_AXIS_TVALID;
  assign ext_axis_switch_gen_M11_AXIS_tdata[31:0] = axis_switch_gen_M11_AXIS_TDATA;
  assign ext_axis_switch_gen_M11_AXIS_tkeep[3:0] = axis_switch_gen_M11_AXIS_TKEEP;
  assign ext_axis_switch_gen_M11_AXIS_tlast[0] = axis_switch_gen_M11_AXIS_TLAST;
  assign ext_axis_switch_gen_M11_AXIS_tvalid[0] = axis_switch_gen_M11_AXIS_TVALID;
  assign ext_axis_switch_gen_S00_AXIS_tready[0] = S00_AXIS_0_1_TREADY;
  assign ext_axis_switch_gen_S_AXI_CTRL_arready = S_AXI_CTRL_0_4_ARREADY;
  assign ext_axis_switch_gen_S_AXI_CTRL_awready = S_AXI_CTRL_0_4_AWREADY;
  assign ext_axis_switch_gen_S_AXI_CTRL_bresp[1:0] = S_AXI_CTRL_0_4_BRESP;
  assign ext_axis_switch_gen_S_AXI_CTRL_bvalid = S_AXI_CTRL_0_4_BVALID;
  assign ext_axis_switch_gen_S_AXI_CTRL_rdata[31:0] = S_AXI_CTRL_0_4_RDATA;
  assign ext_axis_switch_gen_S_AXI_CTRL_rresp[1:0] = S_AXI_CTRL_0_4_RRESP;
  assign ext_axis_switch_gen_S_AXI_CTRL_rvalid = S_AXI_CTRL_0_4_RVALID;
  assign ext_axis_switch_gen_S_AXI_CTRL_wready = S_AXI_CTRL_0_4_WREADY;
  assign ext_axis_switch_mr_S_AXI_CTRL_arready = S_AXI_CTRL_0_5_ARREADY;
  assign ext_axis_switch_mr_S_AXI_CTRL_awready = S_AXI_CTRL_0_5_AWREADY;
  assign ext_axis_switch_mr_S_AXI_CTRL_bresp[1:0] = S_AXI_CTRL_0_5_BRESP;
  assign ext_axis_switch_mr_S_AXI_CTRL_bvalid = S_AXI_CTRL_0_5_BVALID;
  assign ext_axis_switch_mr_S_AXI_CTRL_rdata[31:0] = S_AXI_CTRL_0_5_RDATA;
  assign ext_axis_switch_mr_S_AXI_CTRL_rresp[1:0] = S_AXI_CTRL_0_5_RRESP;
  assign ext_axis_switch_mr_S_AXI_CTRL_rvalid = S_AXI_CTRL_0_5_RVALID;
  assign ext_axis_switch_mr_S_AXI_CTRL_wready = S_AXI_CTRL_0_5_WREADY;
  assign ext_axis_tproc64x32_x8_0_m0_axis_tdata[31:0] = axis_tproc64x32_x8_0_m0_axis_TDATA;
  assign ext_axis_tproc64x32_x8_0_m0_axis_tlast = axis_tproc64x32_x8_0_m0_axis_TLAST;
  assign ext_axis_tproc64x32_x8_0_m0_axis_tvalid = axis_tproc64x32_x8_0_m0_axis_TVALID;
  assign ext_axis_tproc64x32_x8_0_pmem_addr[19:0] = axis_tproc64x32_x8_0_pmem_addr;
  assign ext_axis_tproc64x32_x8_0_pmem_do_1 = ext_axis_tproc64x32_x8_0_pmem_do[63:0];
  assign ext_axis_tproc64x32_x8_0_s0_axis_tready = s0_axis_0_1_TREADY;
  assign ext_axis_tproc64x32_x8_0_s_axi_arready = s_axi_0_17_ARREADY;
  assign ext_axis_tproc64x32_x8_0_s_axi_awready = s_axi_0_17_AWREADY;
  assign ext_axis_tproc64x32_x8_0_s_axi_bresp[1:0] = s_axi_0_17_BRESP;
  assign ext_axis_tproc64x32_x8_0_s_axi_bvalid = s_axi_0_17_BVALID;
  assign ext_axis_tproc64x32_x8_0_s_axi_rdata[31:0] = s_axi_0_17_RDATA;
  assign ext_axis_tproc64x32_x8_0_s_axi_rresp[1:0] = s_axi_0_17_RRESP;
  assign ext_axis_tproc64x32_x8_0_s_axi_rvalid = s_axi_0_17_RVALID;
  assign ext_axis_tproc64x32_x8_0_s_axi_wready = s_axi_0_17_WREADY;
  assign ext_axis_tproc64x32_x8_0_start_1 = ext_axis_tproc64x32_x8_0_start;
  assign ext_c_shift_ram_0_D_1 = ext_c_shift_ram_0_D;
  assign ext_c_shift_ram_0_Q[0] = c_shift_ram_0_Q;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awaddr[31:0] = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWADDR;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awburst[1:0] = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWBURST;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awcache[3:0] = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWCACHE;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awid[0] = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWID;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlen[7:0] = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWLEN;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlock = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWLOCK;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awprot[2:0] = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWPROT;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awqos[3:0] = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWQOS;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awregion[3:0] = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWREGION;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awsize[2:0] = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWSIZE;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awvalid = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_AWVALID;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bready = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_BREADY;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wdata[255:0] = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_WDATA;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wlast = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_WLAST;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wstrb[31:0] = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_WSTRB;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wvalid = ddr4_axis_buffer_ddr_sample_v3_0_m_axi_WVALID;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arready = s_axi_0_18_ARREADY;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awready = s_axi_0_18_AWREADY;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bresp[1:0] = s_axi_0_18_BRESP;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bvalid = s_axi_0_18_BVALID;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rdata[31:0] = s_axi_0_18_RDATA;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rresp[1:0] = s_axi_0_18_RRESP;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rvalid = s_axi_0_18_RVALID;
  assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wready = s_axi_0_18_WREADY;
  assign ext_ddr4_axis_fir_decim_300to1_v2_0_capture_trigger = ddr4_axis_fir_decim_300to1_v2_0_capture_trigger;
  assign ext_mr_buffer_et_0_m00_axis_tdata[31:0] = mr_buffer_et_0_m00_axis_TDATA;
  assign ext_mr_buffer_et_0_m00_axis_tlast = mr_buffer_et_0_m00_axis_TLAST;
  assign ext_mr_buffer_et_0_m00_axis_tstrb[3:0] = mr_buffer_et_0_m00_axis_TSTRB;
  assign ext_mr_buffer_et_0_m00_axis_tvalid = mr_buffer_et_0_m00_axis_TVALID;
  assign ext_mr_buffer_et_0_s00_axi_arready = s00_axi_0_1_ARREADY;
  assign ext_mr_buffer_et_0_s00_axi_awready = s00_axi_0_1_AWREADY;
  assign ext_mr_buffer_et_0_s00_axi_bresp[1:0] = s00_axi_0_1_BRESP;
  assign ext_mr_buffer_et_0_s00_axi_bvalid = s00_axi_0_1_BVALID;
  assign ext_mr_buffer_et_0_s00_axi_rdata[31:0] = s00_axi_0_1_RDATA;
  assign ext_mr_buffer_et_0_s00_axi_rresp[1:0] = s00_axi_0_1_RRESP;
  assign ext_mr_buffer_et_0_s00_axi_rvalid = s00_axi_0_1_RVALID;
  assign ext_mr_buffer_et_0_s00_axi_wready = s00_axi_0_1_WREADY;
  assign ext_qick_vec2bit_0_dout0 = qick_vec2bit_0_dout0;
  assign ext_qick_vec2bit_0_dout1 = qick_vec2bit_0_dout1;
  assign ext_qick_vec2bit_0_dout2 = qick_vec2bit_0_dout2;
  assign ext_qick_vec2bit_0_dout3 = qick_vec2bit_0_dout3;
  assign ext_qick_vec2bit_0_dout4 = qick_vec2bit_0_dout4;
  assign ext_qick_vec2bit_0_dout5 = qick_vec2bit_0_dout5;
  assign ext_qick_vec2bit_0_dout6 = qick_vec2bit_0_dout6;
  assign ext_xlconstant_0_dout[63:0] = xlconstant_0_dout;
  assign ext_xlconstant_1_dout[0] = xlconstant_1_dout;
  assign ext_xlconstant_2_dout[0] = xlconstant_2_dout;
  assign ext_xlconstant_3_dout[7:0] = xlconstant_3_dout;
  assign ext_xlconstant_4_dout[11:0] = xlconstant_4_dout;
  assign mr_buffer_et_0_m00_axis_TREADY = ext_mr_buffer_et_0_m00_axis_tready;
  assign resetn_1 = resetn;
  assign s00_axi_0_1_ARADDR = ext_mr_buffer_et_0_s00_axi_araddr[5:0];
  assign s00_axi_0_1_ARPROT = ext_mr_buffer_et_0_s00_axi_arprot[2:0];
  assign s00_axi_0_1_ARVALID = ext_mr_buffer_et_0_s00_axi_arvalid;
  assign s00_axi_0_1_AWADDR = ext_mr_buffer_et_0_s00_axi_awaddr[5:0];
  assign s00_axi_0_1_AWPROT = ext_mr_buffer_et_0_s00_axi_awprot[2:0];
  assign s00_axi_0_1_AWVALID = ext_mr_buffer_et_0_s00_axi_awvalid;
  assign s00_axi_0_1_BREADY = ext_mr_buffer_et_0_s00_axi_bready;
  assign s00_axi_0_1_RREADY = ext_mr_buffer_et_0_s00_axi_rready;
  assign s00_axi_0_1_WDATA = ext_mr_buffer_et_0_s00_axi_wdata[31:0];
  assign s00_axi_0_1_WSTRB = ext_mr_buffer_et_0_s00_axi_wstrb[3:0];
  assign s00_axi_0_1_WVALID = ext_mr_buffer_et_0_s00_axi_wvalid;
  assign s0_axis_0_1_TDATA = ext_axis_tproc64x32_x8_0_s0_axis_tdata[31:0];
  assign s0_axis_0_1_TLAST = ext_axis_tproc64x32_x8_0_s0_axis_tlast;
  assign s0_axis_0_1_TVALID = ext_axis_tproc64x32_x8_0_s0_axis_tvalid;
  assign s1_axis_0_1_TDATA = ext_axis_dyn_readout_v1_0_s1_axis_tdata[127:0];
  assign s1_axis_0_1_TVALID = ext_axis_dyn_readout_v1_0_s1_axis_tvalid;
  assign s1_axis_0_2_TDATA = ext_axis_dyn_readout_v1_1_s1_axis_tdata[127:0];
  assign s1_axis_0_2_TVALID = ext_axis_dyn_readout_v1_1_s1_axis_tvalid;
  assign s1_axis_0_3_TDATA = ext_axis_dyn_readout_v1_2_s1_axis_tdata[127:0];
  assign s1_axis_0_3_TVALID = ext_axis_dyn_readout_v1_2_s1_axis_tvalid;
  assign s1_axis_0_4_TDATA = ext_axis_dyn_readout_v1_3_s1_axis_tdata[127:0];
  assign s1_axis_0_4_TVALID = ext_axis_dyn_readout_v1_3_s1_axis_tvalid;
  assign s_axi_0_10_ARADDR = ext_axis_awg_tuning_v1_8_s_axi_araddr[5:0];
  assign s_axi_0_10_ARPROT = ext_axis_awg_tuning_v1_8_s_axi_arprot[2:0];
  assign s_axi_0_10_ARVALID = ext_axis_awg_tuning_v1_8_s_axi_arvalid;
  assign s_axi_0_10_AWADDR = ext_axis_awg_tuning_v1_8_s_axi_awaddr[5:0];
  assign s_axi_0_10_AWPROT = ext_axis_awg_tuning_v1_8_s_axi_awprot[2:0];
  assign s_axi_0_10_AWVALID = ext_axis_awg_tuning_v1_8_s_axi_awvalid;
  assign s_axi_0_10_BREADY = ext_axis_awg_tuning_v1_8_s_axi_bready;
  assign s_axi_0_10_RREADY = ext_axis_awg_tuning_v1_8_s_axi_rready;
  assign s_axi_0_10_WDATA = ext_axis_awg_tuning_v1_8_s_axi_wdata[31:0];
  assign s_axi_0_10_WSTRB = ext_axis_awg_tuning_v1_8_s_axi_wstrb[3:0];
  assign s_axi_0_10_WVALID = ext_axis_awg_tuning_v1_8_s_axi_wvalid;
  assign s_axi_0_11_ARADDR = ext_axis_awg_tuning_v1_9_s_axi_araddr[5:0];
  assign s_axi_0_11_ARPROT = ext_axis_awg_tuning_v1_9_s_axi_arprot[2:0];
  assign s_axi_0_11_ARVALID = ext_axis_awg_tuning_v1_9_s_axi_arvalid;
  assign s_axi_0_11_AWADDR = ext_axis_awg_tuning_v1_9_s_axi_awaddr[5:0];
  assign s_axi_0_11_AWPROT = ext_axis_awg_tuning_v1_9_s_axi_awprot[2:0];
  assign s_axi_0_11_AWVALID = ext_axis_awg_tuning_v1_9_s_axi_awvalid;
  assign s_axi_0_11_BREADY = ext_axis_awg_tuning_v1_9_s_axi_bready;
  assign s_axi_0_11_RREADY = ext_axis_awg_tuning_v1_9_s_axi_rready;
  assign s_axi_0_11_WDATA = ext_axis_awg_tuning_v1_9_s_axi_wdata[31:0];
  assign s_axi_0_11_WSTRB = ext_axis_awg_tuning_v1_9_s_axi_wstrb[3:0];
  assign s_axi_0_11_WVALID = ext_axis_awg_tuning_v1_9_s_axi_wvalid;
  assign s_axi_0_12_ARADDR = ext_axis_signal_gen_v6_0_s_axi_araddr[5:0];
  assign s_axi_0_12_ARPROT = ext_axis_signal_gen_v6_0_s_axi_arprot[2:0];
  assign s_axi_0_12_ARVALID = ext_axis_signal_gen_v6_0_s_axi_arvalid;
  assign s_axi_0_12_AWADDR = ext_axis_signal_gen_v6_0_s_axi_awaddr[5:0];
  assign s_axi_0_12_AWPROT = ext_axis_signal_gen_v6_0_s_axi_awprot[2:0];
  assign s_axi_0_12_AWVALID = ext_axis_signal_gen_v6_0_s_axi_awvalid;
  assign s_axi_0_12_BREADY = ext_axis_signal_gen_v6_0_s_axi_bready;
  assign s_axi_0_12_RREADY = ext_axis_signal_gen_v6_0_s_axi_rready;
  assign s_axi_0_12_WDATA = ext_axis_signal_gen_v6_0_s_axi_wdata[31:0];
  assign s_axi_0_12_WSTRB = ext_axis_signal_gen_v6_0_s_axi_wstrb[3:0];
  assign s_axi_0_12_WVALID = ext_axis_signal_gen_v6_0_s_axi_wvalid;
  assign s_axi_0_13_ARADDR = ext_axis_signal_gen_v6_1_s_axi_araddr[5:0];
  assign s_axi_0_13_ARPROT = ext_axis_signal_gen_v6_1_s_axi_arprot[2:0];
  assign s_axi_0_13_ARVALID = ext_axis_signal_gen_v6_1_s_axi_arvalid;
  assign s_axi_0_13_AWADDR = ext_axis_signal_gen_v6_1_s_axi_awaddr[5:0];
  assign s_axi_0_13_AWPROT = ext_axis_signal_gen_v6_1_s_axi_awprot[2:0];
  assign s_axi_0_13_AWVALID = ext_axis_signal_gen_v6_1_s_axi_awvalid;
  assign s_axi_0_13_BREADY = ext_axis_signal_gen_v6_1_s_axi_bready;
  assign s_axi_0_13_RREADY = ext_axis_signal_gen_v6_1_s_axi_rready;
  assign s_axi_0_13_WDATA = ext_axis_signal_gen_v6_1_s_axi_wdata[31:0];
  assign s_axi_0_13_WSTRB = ext_axis_signal_gen_v6_1_s_axi_wstrb[3:0];
  assign s_axi_0_13_WVALID = ext_axis_signal_gen_v6_1_s_axi_wvalid;
  assign s_axi_0_14_ARADDR = ext_axis_signal_gen_v6_2_s_axi_araddr[5:0];
  assign s_axi_0_14_ARPROT = ext_axis_signal_gen_v6_2_s_axi_arprot[2:0];
  assign s_axi_0_14_ARVALID = ext_axis_signal_gen_v6_2_s_axi_arvalid;
  assign s_axi_0_14_AWADDR = ext_axis_signal_gen_v6_2_s_axi_awaddr[5:0];
  assign s_axi_0_14_AWPROT = ext_axis_signal_gen_v6_2_s_axi_awprot[2:0];
  assign s_axi_0_14_AWVALID = ext_axis_signal_gen_v6_2_s_axi_awvalid;
  assign s_axi_0_14_BREADY = ext_axis_signal_gen_v6_2_s_axi_bready;
  assign s_axi_0_14_RREADY = ext_axis_signal_gen_v6_2_s_axi_rready;
  assign s_axi_0_14_WDATA = ext_axis_signal_gen_v6_2_s_axi_wdata[31:0];
  assign s_axi_0_14_WSTRB = ext_axis_signal_gen_v6_2_s_axi_wstrb[3:0];
  assign s_axi_0_14_WVALID = ext_axis_signal_gen_v6_2_s_axi_wvalid;
  assign s_axi_0_15_ARADDR = ext_axis_signal_gen_v6_3_s_axi_araddr[5:0];
  assign s_axi_0_15_ARPROT = ext_axis_signal_gen_v6_3_s_axi_arprot[2:0];
  assign s_axi_0_15_ARVALID = ext_axis_signal_gen_v6_3_s_axi_arvalid;
  assign s_axi_0_15_AWADDR = ext_axis_signal_gen_v6_3_s_axi_awaddr[5:0];
  assign s_axi_0_15_AWPROT = ext_axis_signal_gen_v6_3_s_axi_awprot[2:0];
  assign s_axi_0_15_AWVALID = ext_axis_signal_gen_v6_3_s_axi_awvalid;
  assign s_axi_0_15_BREADY = ext_axis_signal_gen_v6_3_s_axi_bready;
  assign s_axi_0_15_RREADY = ext_axis_signal_gen_v6_3_s_axi_rready;
  assign s_axi_0_15_WDATA = ext_axis_signal_gen_v6_3_s_axi_wdata[31:0];
  assign s_axi_0_15_WSTRB = ext_axis_signal_gen_v6_3_s_axi_wstrb[3:0];
  assign s_axi_0_15_WVALID = ext_axis_signal_gen_v6_3_s_axi_wvalid;
  assign s_axi_0_16_ARADDR = ext_axis_square_pulse_v1_0_s_axi_araddr[5:0];
  assign s_axi_0_16_ARPROT = ext_axis_square_pulse_v1_0_s_axi_arprot[2:0];
  assign s_axi_0_16_ARVALID = ext_axis_square_pulse_v1_0_s_axi_arvalid;
  assign s_axi_0_16_AWADDR = ext_axis_square_pulse_v1_0_s_axi_awaddr[5:0];
  assign s_axi_0_16_AWPROT = ext_axis_square_pulse_v1_0_s_axi_awprot[2:0];
  assign s_axi_0_16_AWVALID = ext_axis_square_pulse_v1_0_s_axi_awvalid;
  assign s_axi_0_16_BREADY = ext_axis_square_pulse_v1_0_s_axi_bready;
  assign s_axi_0_16_RREADY = ext_axis_square_pulse_v1_0_s_axi_rready;
  assign s_axi_0_16_WDATA = ext_axis_square_pulse_v1_0_s_axi_wdata[31:0];
  assign s_axi_0_16_WSTRB = ext_axis_square_pulse_v1_0_s_axi_wstrb[3:0];
  assign s_axi_0_16_WVALID = ext_axis_square_pulse_v1_0_s_axi_wvalid;
  assign s_axi_0_17_ARADDR = ext_axis_tproc64x32_x8_0_s_axi_araddr[31:0];
  assign s_axi_0_17_ARPROT = ext_axis_tproc64x32_x8_0_s_axi_arprot[2:0];
  assign s_axi_0_17_ARVALID = ext_axis_tproc64x32_x8_0_s_axi_arvalid;
  assign s_axi_0_17_AWADDR = ext_axis_tproc64x32_x8_0_s_axi_awaddr[31:0];
  assign s_axi_0_17_AWPROT = ext_axis_tproc64x32_x8_0_s_axi_awprot[2:0];
  assign s_axi_0_17_AWVALID = ext_axis_tproc64x32_x8_0_s_axi_awvalid;
  assign s_axi_0_17_BREADY = ext_axis_tproc64x32_x8_0_s_axi_bready;
  assign s_axi_0_17_RREADY = ext_axis_tproc64x32_x8_0_s_axi_rready;
  assign s_axi_0_17_WDATA = ext_axis_tproc64x32_x8_0_s_axi_wdata[31:0];
  assign s_axi_0_17_WSTRB = ext_axis_tproc64x32_x8_0_s_axi_wstrb[3:0];
  assign s_axi_0_17_WVALID = ext_axis_tproc64x32_x8_0_s_axi_wvalid;
  assign s_axi_0_18_ARADDR = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_araddr[7:0];
  assign s_axi_0_18_ARPROT = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arprot[2:0];
  assign s_axi_0_18_ARVALID = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arvalid;
  assign s_axi_0_18_AWADDR = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awaddr[7:0];
  assign s_axi_0_18_AWPROT = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awprot[2:0];
  assign s_axi_0_18_AWVALID = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awvalid;
  assign s_axi_0_18_BREADY = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bready;
  assign s_axi_0_18_RREADY = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rready;
  assign s_axi_0_18_WDATA = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wdata[31:0];
  assign s_axi_0_18_WSTRB = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wstrb[3:0];
  assign s_axi_0_18_WVALID = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wvalid;
  assign s_axi_0_1_ARADDR = ext_axis_avg_buffer_0_s_axi_araddr[5:0];
  assign s_axi_0_1_ARPROT = ext_axis_avg_buffer_0_s_axi_arprot[2:0];
  assign s_axi_0_1_ARVALID = ext_axis_avg_buffer_0_s_axi_arvalid;
  assign s_axi_0_1_AWADDR = ext_axis_avg_buffer_0_s_axi_awaddr[5:0];
  assign s_axi_0_1_AWPROT = ext_axis_avg_buffer_0_s_axi_awprot[2:0];
  assign s_axi_0_1_AWVALID = ext_axis_avg_buffer_0_s_axi_awvalid;
  assign s_axi_0_1_BREADY = ext_axis_avg_buffer_0_s_axi_bready;
  assign s_axi_0_1_RREADY = ext_axis_avg_buffer_0_s_axi_rready;
  assign s_axi_0_1_WDATA = ext_axis_avg_buffer_0_s_axi_wdata[31:0];
  assign s_axi_0_1_WSTRB = ext_axis_avg_buffer_0_s_axi_wstrb[3:0];
  assign s_axi_0_1_WVALID = ext_axis_avg_buffer_0_s_axi_wvalid;
  assign s_axi_0_2_ARADDR = ext_axis_avg_buffer_1_s_axi_araddr[5:0];
  assign s_axi_0_2_ARPROT = ext_axis_avg_buffer_1_s_axi_arprot[2:0];
  assign s_axi_0_2_ARVALID = ext_axis_avg_buffer_1_s_axi_arvalid;
  assign s_axi_0_2_AWADDR = ext_axis_avg_buffer_1_s_axi_awaddr[5:0];
  assign s_axi_0_2_AWPROT = ext_axis_avg_buffer_1_s_axi_awprot[2:0];
  assign s_axi_0_2_AWVALID = ext_axis_avg_buffer_1_s_axi_awvalid;
  assign s_axi_0_2_BREADY = ext_axis_avg_buffer_1_s_axi_bready;
  assign s_axi_0_2_RREADY = ext_axis_avg_buffer_1_s_axi_rready;
  assign s_axi_0_2_WDATA = ext_axis_avg_buffer_1_s_axi_wdata[31:0];
  assign s_axi_0_2_WSTRB = ext_axis_avg_buffer_1_s_axi_wstrb[3:0];
  assign s_axi_0_2_WVALID = ext_axis_avg_buffer_1_s_axi_wvalid;
  assign s_axi_0_3_ARADDR = ext_axis_avg_buffer_2_s_axi_araddr[5:0];
  assign s_axi_0_3_ARPROT = ext_axis_avg_buffer_2_s_axi_arprot[2:0];
  assign s_axi_0_3_ARVALID = ext_axis_avg_buffer_2_s_axi_arvalid;
  assign s_axi_0_3_AWADDR = ext_axis_avg_buffer_2_s_axi_awaddr[5:0];
  assign s_axi_0_3_AWPROT = ext_axis_avg_buffer_2_s_axi_awprot[2:0];
  assign s_axi_0_3_AWVALID = ext_axis_avg_buffer_2_s_axi_awvalid;
  assign s_axi_0_3_BREADY = ext_axis_avg_buffer_2_s_axi_bready;
  assign s_axi_0_3_RREADY = ext_axis_avg_buffer_2_s_axi_rready;
  assign s_axi_0_3_WDATA = ext_axis_avg_buffer_2_s_axi_wdata[31:0];
  assign s_axi_0_3_WSTRB = ext_axis_avg_buffer_2_s_axi_wstrb[3:0];
  assign s_axi_0_3_WVALID = ext_axis_avg_buffer_2_s_axi_wvalid;
  assign s_axi_0_4_ARADDR = ext_axis_avg_buffer_3_s_axi_araddr[5:0];
  assign s_axi_0_4_ARPROT = ext_axis_avg_buffer_3_s_axi_arprot[2:0];
  assign s_axi_0_4_ARVALID = ext_axis_avg_buffer_3_s_axi_arvalid;
  assign s_axi_0_4_AWADDR = ext_axis_avg_buffer_3_s_axi_awaddr[5:0];
  assign s_axi_0_4_AWPROT = ext_axis_avg_buffer_3_s_axi_awprot[2:0];
  assign s_axi_0_4_AWVALID = ext_axis_avg_buffer_3_s_axi_awvalid;
  assign s_axi_0_4_BREADY = ext_axis_avg_buffer_3_s_axi_bready;
  assign s_axi_0_4_RREADY = ext_axis_avg_buffer_3_s_axi_rready;
  assign s_axi_0_4_WDATA = ext_axis_avg_buffer_3_s_axi_wdata[31:0];
  assign s_axi_0_4_WSTRB = ext_axis_avg_buffer_3_s_axi_wstrb[3:0];
  assign s_axi_0_4_WVALID = ext_axis_avg_buffer_3_s_axi_wvalid;
  assign s_axi_0_5_ARADDR = ext_axis_awg_tuning_v1_10_s_axi_araddr[5:0];
  assign s_axi_0_5_ARPROT = ext_axis_awg_tuning_v1_10_s_axi_arprot[2:0];
  assign s_axi_0_5_ARVALID = ext_axis_awg_tuning_v1_10_s_axi_arvalid;
  assign s_axi_0_5_AWADDR = ext_axis_awg_tuning_v1_10_s_axi_awaddr[5:0];
  assign s_axi_0_5_AWPROT = ext_axis_awg_tuning_v1_10_s_axi_awprot[2:0];
  assign s_axi_0_5_AWVALID = ext_axis_awg_tuning_v1_10_s_axi_awvalid;
  assign s_axi_0_5_BREADY = ext_axis_awg_tuning_v1_10_s_axi_bready;
  assign s_axi_0_5_RREADY = ext_axis_awg_tuning_v1_10_s_axi_rready;
  assign s_axi_0_5_WDATA = ext_axis_awg_tuning_v1_10_s_axi_wdata[31:0];
  assign s_axi_0_5_WSTRB = ext_axis_awg_tuning_v1_10_s_axi_wstrb[3:0];
  assign s_axi_0_5_WVALID = ext_axis_awg_tuning_v1_10_s_axi_wvalid;
  assign s_axi_0_6_ARADDR = ext_axis_awg_tuning_v1_11_s_axi_araddr[5:0];
  assign s_axi_0_6_ARPROT = ext_axis_awg_tuning_v1_11_s_axi_arprot[2:0];
  assign s_axi_0_6_ARVALID = ext_axis_awg_tuning_v1_11_s_axi_arvalid;
  assign s_axi_0_6_AWADDR = ext_axis_awg_tuning_v1_11_s_axi_awaddr[5:0];
  assign s_axi_0_6_AWPROT = ext_axis_awg_tuning_v1_11_s_axi_awprot[2:0];
  assign s_axi_0_6_AWVALID = ext_axis_awg_tuning_v1_11_s_axi_awvalid;
  assign s_axi_0_6_BREADY = ext_axis_awg_tuning_v1_11_s_axi_bready;
  assign s_axi_0_6_RREADY = ext_axis_awg_tuning_v1_11_s_axi_rready;
  assign s_axi_0_6_WDATA = ext_axis_awg_tuning_v1_11_s_axi_wdata[31:0];
  assign s_axi_0_6_WSTRB = ext_axis_awg_tuning_v1_11_s_axi_wstrb[3:0];
  assign s_axi_0_6_WVALID = ext_axis_awg_tuning_v1_11_s_axi_wvalid;
  assign s_axi_0_7_ARADDR = ext_axis_awg_tuning_v1_4_s_axi_araddr[5:0];
  assign s_axi_0_7_ARPROT = ext_axis_awg_tuning_v1_4_s_axi_arprot[2:0];
  assign s_axi_0_7_ARVALID = ext_axis_awg_tuning_v1_4_s_axi_arvalid;
  assign s_axi_0_7_AWADDR = ext_axis_awg_tuning_v1_4_s_axi_awaddr[5:0];
  assign s_axi_0_7_AWPROT = ext_axis_awg_tuning_v1_4_s_axi_awprot[2:0];
  assign s_axi_0_7_AWVALID = ext_axis_awg_tuning_v1_4_s_axi_awvalid;
  assign s_axi_0_7_BREADY = ext_axis_awg_tuning_v1_4_s_axi_bready;
  assign s_axi_0_7_RREADY = ext_axis_awg_tuning_v1_4_s_axi_rready;
  assign s_axi_0_7_WDATA = ext_axis_awg_tuning_v1_4_s_axi_wdata[31:0];
  assign s_axi_0_7_WSTRB = ext_axis_awg_tuning_v1_4_s_axi_wstrb[3:0];
  assign s_axi_0_7_WVALID = ext_axis_awg_tuning_v1_4_s_axi_wvalid;
  assign s_axi_0_8_ARADDR = ext_axis_awg_tuning_v1_5_s_axi_araddr[5:0];
  assign s_axi_0_8_ARPROT = ext_axis_awg_tuning_v1_5_s_axi_arprot[2:0];
  assign s_axi_0_8_ARVALID = ext_axis_awg_tuning_v1_5_s_axi_arvalid;
  assign s_axi_0_8_AWADDR = ext_axis_awg_tuning_v1_5_s_axi_awaddr[5:0];
  assign s_axi_0_8_AWPROT = ext_axis_awg_tuning_v1_5_s_axi_awprot[2:0];
  assign s_axi_0_8_AWVALID = ext_axis_awg_tuning_v1_5_s_axi_awvalid;
  assign s_axi_0_8_BREADY = ext_axis_awg_tuning_v1_5_s_axi_bready;
  assign s_axi_0_8_RREADY = ext_axis_awg_tuning_v1_5_s_axi_rready;
  assign s_axi_0_8_WDATA = ext_axis_awg_tuning_v1_5_s_axi_wdata[31:0];
  assign s_axi_0_8_WSTRB = ext_axis_awg_tuning_v1_5_s_axi_wstrb[3:0];
  assign s_axi_0_8_WVALID = ext_axis_awg_tuning_v1_5_s_axi_wvalid;
  assign s_axi_0_9_ARADDR = ext_axis_awg_tuning_v1_6_s_axi_araddr[5:0];
  assign s_axi_0_9_ARPROT = ext_axis_awg_tuning_v1_6_s_axi_arprot[2:0];
  assign s_axi_0_9_ARVALID = ext_axis_awg_tuning_v1_6_s_axi_arvalid;
  assign s_axi_0_9_AWADDR = ext_axis_awg_tuning_v1_6_s_axi_awaddr[5:0];
  assign s_axi_0_9_AWPROT = ext_axis_awg_tuning_v1_6_s_axi_awprot[2:0];
  assign s_axi_0_9_AWVALID = ext_axis_awg_tuning_v1_6_s_axi_awvalid;
  assign s_axi_0_9_BREADY = ext_axis_awg_tuning_v1_6_s_axi_bready;
  assign s_axi_0_9_RREADY = ext_axis_awg_tuning_v1_6_s_axi_rready;
  assign s_axi_0_9_WDATA = ext_axis_awg_tuning_v1_6_s_axi_wdata[31:0];
  assign s_axi_0_9_WSTRB = ext_axis_awg_tuning_v1_6_s_axi_wstrb[3:0];
  assign s_axi_0_9_WVALID = ext_axis_awg_tuning_v1_6_s_axi_wvalid;






  axis_awg_tuning_v1 #(.EXTRA_Y_PIPE_STAGES(3)) axis_awg_tuning_v1_4
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m_axis_tdata(axis_awg_tuning_v1_4_m_axis_TDATA),
        .m_axis_tready(axis_awg_tuning_v1_4_m_axis_TREADY),
        .m_axis_tvalid(axis_awg_tuning_v1_4_m_axis_TVALID),
        .s_axi_aclk(clk_99999985_1),
        .s_axi_araddr(s_axi_0_7_ARADDR),
        .s_axi_aresetn(resetn_1),
        .s_axi_arprot(s_axi_0_7_ARPROT),
        .s_axi_arready(s_axi_0_7_ARREADY),
        .s_axi_arvalid(s_axi_0_7_ARVALID),
        .s_axi_awaddr(s_axi_0_7_AWADDR),
        .s_axi_awprot(s_axi_0_7_AWPROT),
        .s_axi_awready(s_axi_0_7_AWREADY),
        .s_axi_awvalid(s_axi_0_7_AWVALID),
        .s_axi_bready(s_axi_0_7_BREADY),
        .s_axi_bresp(s_axi_0_7_BRESP),
        .s_axi_bvalid(s_axi_0_7_BVALID),
        .s_axi_rdata(s_axi_0_7_RDATA),
        .s_axi_rready(s_axi_0_7_RREADY),
        .s_axi_rresp(s_axi_0_7_RRESP),
        .s_axi_rvalid(s_axi_0_7_RVALID),
        .s_axi_wdata(s_axi_0_7_WDATA),
        .s_axi_wready(s_axi_0_7_WREADY),
        .s_axi_wstrb(s_axi_0_7_WSTRB),
        .s_axi_wvalid(s_axi_0_7_WVALID),
        .s_axis_tdata(axis_register_slice_9_M_AXIS_TDATA),
        .s_axis_tvalid(axis_register_slice_9_M_AXIS_TVALID));
  axis_awg_tuning_v1 #(.EXTRA_Y_PIPE_STAGES(3)) axis_awg_tuning_v1_5
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m_axis_tdata(axis_awg_tuning_v1_5_m_axis_TDATA),
        .m_axis_tready(axis_awg_tuning_v1_5_m_axis_TREADY),
        .m_axis_tvalid(axis_awg_tuning_v1_5_m_axis_TVALID),
        .s_axi_aclk(clk_99999985_1),
        .s_axi_araddr(s_axi_0_8_ARADDR),
        .s_axi_aresetn(resetn_1),
        .s_axi_arprot(s_axi_0_8_ARPROT),
        .s_axi_arready(s_axi_0_8_ARREADY),
        .s_axi_arvalid(s_axi_0_8_ARVALID),
        .s_axi_awaddr(s_axi_0_8_AWADDR),
        .s_axi_awprot(s_axi_0_8_AWPROT),
        .s_axi_awready(s_axi_0_8_AWREADY),
        .s_axi_awvalid(s_axi_0_8_AWVALID),
        .s_axi_bready(s_axi_0_8_BREADY),
        .s_axi_bresp(s_axi_0_8_BRESP),
        .s_axi_bvalid(s_axi_0_8_BVALID),
        .s_axi_rdata(s_axi_0_8_RDATA),
        .s_axi_rready(s_axi_0_8_RREADY),
        .s_axi_rresp(s_axi_0_8_RRESP),
        .s_axi_rvalid(s_axi_0_8_RVALID),
        .s_axi_wdata(s_axi_0_8_WDATA),
        .s_axi_wready(s_axi_0_8_WREADY),
        .s_axi_wstrb(s_axi_0_8_WSTRB),
        .s_axi_wvalid(s_axi_0_8_WVALID),
        .s_axis_tdata(axis_register_slice_21_M_AXIS_TDATA),
        .s_axis_tvalid(axis_register_slice_21_M_AXIS_TVALID));















  sim_bd_axis_register_slice_0_0 axis_register_slice_0
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m_axis_tdata(axis_register_slice_0_m_axis_TDATA),
        .m_axis_tready(axis_register_slice_0_m_axis_TREADY),
        .m_axis_tvalid(axis_register_slice_0_m_axis_TVALID),
        .s_axis_tdata(axis_signal_gen_v6_0_m_axis_TDATA),
        .s_axis_tready(axis_signal_gen_v6_0_m_axis_TREADY),
        .s_axis_tvalid(axis_signal_gen_v6_0_m_axis_TVALID));

  sim_bd_axis_register_slice_10_0 axis_register_slice_10
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m_axis_tdata(axis_register_slice_10_m_axis_TDATA),
        .m_axis_tready(axis_register_slice_10_m_axis_TREADY),
        .m_axis_tvalid(axis_register_slice_10_m_axis_TVALID),
        .s_axis_tdata(axis_awg_tuning_v1_5_m_axis_TDATA),
        .s_axis_tready(axis_awg_tuning_v1_5_m_axis_TREADY),
        .s_axis_tvalid(axis_awg_tuning_v1_5_m_axis_TVALID));

  sim_bd_axis_register_slice_12_0 axis_register_slice_12
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m_axis_tdata(axis_register_slice_12_m_axis_TDATA),
        .m_axis_tready(axis_register_slice_12_m_axis_TREADY),
        .m_axis_tvalid(axis_register_slice_12_m_axis_TVALID),
        .s_axis_tdata(axis_square_pulse_v1_0_m_axis_TDATA),
        .s_axis_tready(axis_square_pulse_v1_0_m_axis_TREADY),
        .s_axis_tvalid(axis_square_pulse_v1_0_m_axis_TVALID));





  sim_bd_axis_register_slice_21_0 axis_register_slice_21
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m_axis_tdata(axis_register_slice_21_M_AXIS_TDATA),
        .m_axis_tvalid(axis_register_slice_21_M_AXIS_TVALID),
        .s_axis_tdata(axis_tmux_v1_1_m1_axis_TDATA),
        .s_axis_tvalid(axis_tmux_v1_1_m1_axis_TVALID));

  sim_bd_axis_register_slice_23_0 axis_register_slice_23
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m_axis_tdata(axis_register_slice_23_M_AXIS_TDATA),
        .m_axis_tvalid(axis_register_slice_23_M_AXIS_TVALID),
        .s_axis_tdata(axis_tmux_v1_3_m1_axis_TDATA),
        .s_axis_tvalid(axis_tmux_v1_3_m1_axis_TVALID));





  sim_bd_axis_register_slice_4_0 axis_register_slice_4
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m_axis_tdata(axis_register_slice_4_M_AXIS_TDATA),
        .m_axis_tvalid(axis_register_slice_4_M_AXIS_TVALID),
        .s_axis_tdata(axis_tmux_v1_0_m0_axis_TDATA),
        .s_axis_tvalid(axis_tmux_v1_0_m0_axis_TVALID));



  sim_bd_axis_register_slice_8_0 axis_register_slice_8
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m_axis_tdata(axis_register_slice_8_m_axis_TDATA),
        .m_axis_tready(axis_register_slice_8_m_axis_TREADY),
        .m_axis_tvalid(axis_register_slice_8_m_axis_TVALID),
        .s_axis_tdata(axis_awg_tuning_v1_4_m_axis_TDATA),
        .s_axis_tready(axis_awg_tuning_v1_4_m_axis_TREADY),
        .s_axis_tvalid(axis_awg_tuning_v1_4_m_axis_TVALID));
  sim_bd_axis_register_slice_9_0 axis_register_slice_9
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m_axis_tdata(axis_register_slice_9_M_AXIS_TDATA),
        .m_axis_tvalid(axis_register_slice_9_M_AXIS_TVALID),
        .s_axis_tdata(axis_tmux_v1_0_m1_axis_TDATA),
        .s_axis_tvalid(axis_tmux_v1_0_m1_axis_TVALID));
  sim_bd_axis_set_reg_0_0 axis_set_reg_0
       (.dout(axis_set_reg_0_dout),
        .s_axis_aclk(clk_300000000_1),
        .s_axis_aresetn(resetn_1),
        .s_axis_tdata(axis_tproc64x32_x8_0_m8_axis_TDATA),
        .s_axis_tlast(1'b0),
        .s_axis_tready(axis_tproc64x32_x8_0_m8_axis_TREADY),
        .s_axis_tstrb({1'b1,1'b1,1'b1,1'b1,1'b1,1'b1,1'b1,1'b1,1'b1,1'b1,1'b1,1'b1,1'b1,1'b1,1'b1,1'b1,1'b1,1'b1,1'b1,1'b1}),
        .s_axis_tvalid(axis_tproc64x32_x8_0_m8_axis_TVALID));
  sim_bd_axis_signal_gen_v6_0_0 axis_signal_gen_v6_0
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m_axis_tdata(axis_signal_gen_v6_0_m_axis_TDATA),
        .m_axis_tready(axis_signal_gen_v6_0_m_axis_TREADY),
        .m_axis_tvalid(axis_signal_gen_v6_0_m_axis_TVALID),
        .s0_axis_aclk(clk_99999985_1),
        .s0_axis_aresetn(resetn_1),
        .s0_axis_tdata(axis_switch_gen_M00_AXIS_TDATA),
        .s0_axis_tready(axis_switch_gen_M00_AXIS_TREADY),
        .s0_axis_tvalid(axis_switch_gen_M00_AXIS_TVALID),
        .s1_axis_tdata(axis_register_slice_4_M_AXIS_TDATA),
        .s1_axis_tvalid(axis_register_slice_4_M_AXIS_TVALID),
        .s_axi_aclk(clk_99999985_1),
        .s_axi_araddr(s_axi_0_12_ARADDR),
        .s_axi_aresetn(resetn_1),
        .s_axi_arprot(s_axi_0_12_ARPROT),
        .s_axi_arready(s_axi_0_12_ARREADY),
        .s_axi_arvalid(s_axi_0_12_ARVALID),
        .s_axi_awaddr(s_axi_0_12_AWADDR),
        .s_axi_awprot(s_axi_0_12_AWPROT),
        .s_axi_awready(s_axi_0_12_AWREADY),
        .s_axi_awvalid(s_axi_0_12_AWVALID),
        .s_axi_bready(s_axi_0_12_BREADY),
        .s_axi_bresp(s_axi_0_12_BRESP),
        .s_axi_bvalid(s_axi_0_12_BVALID),
        .s_axi_rdata(s_axi_0_12_RDATA),
        .s_axi_rready(s_axi_0_12_RREADY),
        .s_axi_rresp(s_axi_0_12_RRESP),
        .s_axi_rvalid(s_axi_0_12_RVALID),
        .s_axi_wdata(s_axi_0_12_WDATA),
        .s_axi_wready(s_axi_0_12_WREADY),
        .s_axi_wstrb(s_axi_0_12_WSTRB),
        .s_axi_wvalid(s_axi_0_12_WVALID));



  axis_square_pulse_v1 axis_square_pulse_v1_0
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m_axis_tdata(axis_square_pulse_v1_0_m_axis_TDATA),
        .m_axis_tready(axis_square_pulse_v1_0_m_axis_TREADY),
        .m_axis_tvalid(axis_square_pulse_v1_0_m_axis_TVALID),
        .s_axi_aclk(clk_99999985_1),
        .s_axi_araddr(s_axi_0_16_ARADDR),
        .s_axi_aresetn(resetn_1),
        .s_axi_arprot(s_axi_0_16_ARPROT),
        .s_axi_arready(s_axi_0_16_ARREADY),
        .s_axi_arvalid(s_axi_0_16_ARVALID),
        .s_axi_awaddr(s_axi_0_16_AWADDR),
        .s_axi_awprot(s_axi_0_16_AWPROT),
        .s_axi_awready(s_axi_0_16_AWREADY),
        .s_axi_awvalid(s_axi_0_16_AWVALID),
        .s_axi_bready(s_axi_0_16_BREADY),
        .s_axi_bresp(s_axi_0_16_BRESP),
        .s_axi_bvalid(s_axi_0_16_BVALID),
        .s_axi_rdata(s_axi_0_16_RDATA),
        .s_axi_rready(s_axi_0_16_RREADY),
        .s_axi_rresp(s_axi_0_16_RRESP),
        .s_axi_rvalid(s_axi_0_16_RVALID),
        .s_axi_wdata(s_axi_0_16_WDATA),
        .s_axi_wready(s_axi_0_16_WREADY),
        .s_axi_wstrb(s_axi_0_16_WSTRB),
        .s_axi_wvalid(s_axi_0_16_WVALID),
        .s_axis_tdata(axis_register_slice_23_M_AXIS_TDATA),
        .s_axis_tvalid(axis_register_slice_23_M_AXIS_TVALID));





  sim_bd_axis_tmux_v1_0_0 axis_tmux_v1_0
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m0_axis_tdata(axis_tmux_v1_0_m0_axis_TDATA),
        .m0_axis_tvalid(axis_tmux_v1_0_m0_axis_TVALID),
        .m1_axis_tdata(axis_tmux_v1_0_m1_axis_TDATA),
        .m1_axis_tvalid(axis_tmux_v1_0_m1_axis_TVALID),
        .s_axis_tdata(axis_tproc64x32_x8_0_m1_axis_TDATA),
        .s_axis_tready(axis_tproc64x32_x8_0_m1_axis_TREADY),
        .s_axis_tvalid(axis_tproc64x32_x8_0_m1_axis_TVALID));
  sim_bd_axis_tmux_v1_1_0 axis_tmux_v1_1
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m0_axis_tdata(axis_tmux_v1_1_m0_axis_TDATA),
        .m0_axis_tvalid(axis_tmux_v1_1_m0_axis_TVALID),
        .m1_axis_tdata(axis_tmux_v1_1_m1_axis_TDATA),
        .m1_axis_tvalid(axis_tmux_v1_1_m1_axis_TVALID),
        .s_axis_tdata(axis_tproc64x32_x8_0_m2_axis_TDATA),
        .s_axis_tready(axis_tproc64x32_x8_0_m2_axis_TREADY),
        .s_axis_tvalid(axis_tproc64x32_x8_0_m2_axis_TVALID));

  sim_bd_axis_tmux_v1_3_0 axis_tmux_v1_3
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m0_axis_tdata(axis_tmux_v1_3_m0_axis_TDATA),
        .m0_axis_tvalid(axis_tmux_v1_3_m0_axis_TVALID),
        .m1_axis_tdata(axis_tmux_v1_3_m1_axis_TDATA),
        .m1_axis_tvalid(axis_tmux_v1_3_m1_axis_TVALID),
        .s_axis_tdata(axis_tproc64x32_x8_0_m4_axis_TDATA),
        .s_axis_tready(axis_tproc64x32_x8_0_m4_axis_TREADY),
        .s_axis_tvalid(axis_tproc64x32_x8_0_m4_axis_TVALID));



  sim_bd_axis_tproc64x32_x8_0_0 axis_tproc64x32_x8_0
       (.aclk(clk_300000000_1),
        .aresetn(resetn_1),
        .m0_axis_aclk(clk_99999985_1),
        .m0_axis_aresetn(resetn_1),
        .m0_axis_tdata(axis_tproc64x32_x8_0_m0_axis_TDATA),
        .m0_axis_tlast(axis_tproc64x32_x8_0_m0_axis_TLAST),
        .m0_axis_tready(axis_tproc64x32_x8_0_m0_axis_TREADY),
        .m0_axis_tvalid(axis_tproc64x32_x8_0_m0_axis_TVALID),
        .m1_axis_tdata(axis_tproc64x32_x8_0_m1_axis_TDATA),
        .m1_axis_tready(axis_tproc64x32_x8_0_m1_axis_TREADY),
        .m1_axis_tvalid(axis_tproc64x32_x8_0_m1_axis_TVALID),
        .m2_axis_tdata(axis_tproc64x32_x8_0_m2_axis_TDATA),
        .m2_axis_tready(axis_tproc64x32_x8_0_m2_axis_TREADY),
        .m2_axis_tvalid(axis_tproc64x32_x8_0_m2_axis_TVALID),
        .m3_axis_tdata(axis_tproc64x32_x8_0_m3_axis_TDATA),
        .m3_axis_tready(axis_tproc64x32_x8_0_m3_axis_TREADY),
        .m3_axis_tvalid(axis_tproc64x32_x8_0_m3_axis_TVALID),
        .m4_axis_tdata(axis_tproc64x32_x8_0_m4_axis_TDATA),
        .m4_axis_tready(axis_tproc64x32_x8_0_m4_axis_TREADY),
        .m4_axis_tvalid(axis_tproc64x32_x8_0_m4_axis_TVALID),
        .m5_axis_tdata(axis_tproc64x32_x8_0_m5_axis_TDATA),
        .m5_axis_tready(axis_tproc64x32_x8_0_m5_axis_TREADY),
        .m5_axis_tvalid(axis_tproc64x32_x8_0_m5_axis_TVALID),
        .m6_axis_tdata(axis_tproc64x32_x8_0_m6_axis_TDATA),
        .m6_axis_tready(axis_tproc64x32_x8_0_m6_axis_TREADY),
        .m6_axis_tvalid(axis_tproc64x32_x8_0_m6_axis_TVALID),
        .m7_axis_tdata(axis_tproc64x32_x8_0_m7_axis_TDATA),
        .m7_axis_tready(axis_tproc64x32_x8_0_m7_axis_TREADY),
        .m7_axis_tvalid(axis_tproc64x32_x8_0_m7_axis_TVALID),
        .m8_axis_tdata(axis_tproc64x32_x8_0_m8_axis_TDATA),
        .m8_axis_tready(axis_tproc64x32_x8_0_m8_axis_TREADY),
        .m8_axis_tvalid(axis_tproc64x32_x8_0_m8_axis_TVALID),
        .pmem_addr(axis_tproc64x32_x8_0_pmem_addr),
        .pmem_do(ext_axis_tproc64x32_x8_0_pmem_do_1),
        .s0_axis_aclk(clk_99999985_1),
        .s0_axis_aresetn(resetn_1),
        .s0_axis_tdata(s0_axis_0_1_TDATA),
        .s0_axis_tlast(s0_axis_0_1_TLAST),
        .s0_axis_tready(s0_axis_0_1_TREADY),
        .s0_axis_tvalid(s0_axis_0_1_TVALID),
        .s1_axis_tdata(axis_clk_cnvrt_avg_0_M_AXIS_TDATA),
        .s1_axis_tready(axis_clk_cnvrt_avg_0_M_AXIS_TREADY),
        .s1_axis_tvalid(axis_clk_cnvrt_avg_0_M_AXIS_TVALID),
        .s2_axis_tdata(axis_clk_cnvrt_avg_1_M_AXIS_TDATA),
        .s2_axis_tready(axis_clk_cnvrt_avg_1_M_AXIS_TREADY),
        .s2_axis_tvalid(axis_clk_cnvrt_avg_1_M_AXIS_TVALID),
        .s3_axis_tdata(axis_clk_cnvrt_avg_2_M_AXIS_TDATA),
        .s3_axis_tready(axis_clk_cnvrt_avg_2_M_AXIS_TREADY),
        .s3_axis_tvalid(axis_clk_cnvrt_avg_2_M_AXIS_TVALID),
        .s4_axis_tdata(axis_clk_cnvrt_avg_3_M_AXIS_TDATA),
        .s4_axis_tready(axis_clk_cnvrt_avg_3_M_AXIS_TREADY),
        .s4_axis_tvalid(axis_clk_cnvrt_avg_3_M_AXIS_TVALID),
        .s_axi_aclk(clk_99999985_1),
        .s_axi_araddr(s_axi_0_17_ARADDR),
        .s_axi_aresetn(resetn_1),
        .s_axi_arprot(s_axi_0_17_ARPROT),
        .s_axi_arready(s_axi_0_17_ARREADY),
        .s_axi_arvalid(s_axi_0_17_ARVALID),
        .s_axi_awaddr(s_axi_0_17_AWADDR),
        .s_axi_awprot(s_axi_0_17_AWPROT),
        .s_axi_awready(s_axi_0_17_AWREADY),
        .s_axi_awvalid(s_axi_0_17_AWVALID),
        .s_axi_bready(s_axi_0_17_BREADY),
        .s_axi_bresp(s_axi_0_17_BRESP),
        .s_axi_bvalid(s_axi_0_17_BVALID),
        .s_axi_rdata(s_axi_0_17_RDATA),
        .s_axi_rready(s_axi_0_17_RREADY),
        .s_axi_rresp(s_axi_0_17_RRESP),
        .s_axi_rvalid(s_axi_0_17_RVALID),
        .s_axi_wdata(s_axi_0_17_WDATA),
        .s_axi_wready(s_axi_0_17_WREADY),
        .s_axi_wstrb(s_axi_0_17_WSTRB),
        .s_axi_wvalid(s_axi_0_17_WVALID),
        .start(ext_axis_tproc64x32_x8_0_start_1));






  sim_bd_qick_vec2bit_0_0 qick_vec2bit_0
       (.din(axis_set_reg_0_dout),
        .dout0(qick_vec2bit_0_dout0),
        .dout1(qick_vec2bit_0_dout1),
        .dout2(qick_vec2bit_0_dout2),
        .dout3(qick_vec2bit_0_dout3),
        .dout4(qick_vec2bit_0_dout4),
        .dout5(qick_vec2bit_0_dout5),
        .dout6(qick_vec2bit_0_dout6));
  sim_bd_xlconstant_0_0 xlconstant_0
       (.dout(xlconstant_0_dout));
  sim_bd_xlconstant_1_0 xlconstant_1
       (.dout(xlconstant_1_dout));
  sim_bd_xlconstant_2_0 xlconstant_2
       (.dout(xlconstant_2_dout));
  sim_bd_xlconstant_3_0 xlconstant_3
       (.dout(xlconstant_3_dout));
  sim_bd_xlconstant_4_0 xlconstant_4
       (.dout(xlconstant_4_dout));
assign axis_clk_cnvrt_avg_0_M_AXIS_TDATA=64'b0;
assign axis_clk_cnvrt_avg_0_M_AXIS_TVALID=1'b0;
assign axis_clk_cnvrt_avg_1_M_AXIS_TDATA=64'b0;
assign axis_clk_cnvrt_avg_1_M_AXIS_TVALID=1'b0;
assign axis_clk_cnvrt_avg_2_M_AXIS_TDATA=64'b0;
assign axis_clk_cnvrt_avg_2_M_AXIS_TVALID=1'b0;
assign axis_clk_cnvrt_avg_3_M_AXIS_TDATA=64'b0;
assign axis_clk_cnvrt_avg_3_M_AXIS_TVALID=1'b0;
assign axis_tproc64x32_x8_0_m3_axis_TREADY=1'b1;
assign axis_tproc64x32_x8_0_m5_axis_TREADY=1'b1;
assign axis_tproc64x32_x8_0_m6_axis_TREADY=1'b1;
assign axis_tproc64x32_x8_0_m7_axis_TREADY=1'b1;
assign axis_switch_gen_M00_AXIS_TDATA=32'b0; assign axis_switch_gen_M00_AXIS_TVALID=1'b0;
endmodule
