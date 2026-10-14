// Generated boundary connections. See tb_body.svh for the test.
`timescale 1ns/1fs
module tb_rc_gui;
localparam NB=24;
logic [31:0] host_addr=0, host_data=0;
logic host_aw=0, host_w=0, host_ar=0, host_bready=0;
integer selected=-1;
wire [NB-1:0] awready,wready,bvalid,arready,rvalid;
wire [31:0] rdata[NB];
wire [1:0] bresp[NB];
logic [63:0] pmem[0:8191];
logic [127:0] adc_rom[0:29];
integer adc_index=0;
logic [63:0] pmem_data=0;
logic [127:0] adc_data=0;
logic mem_bvalid=0;
integer mem_address=0;
integer memory_file;
logic  clk_300000000;
logic  clk_333250000;
logic  clk_99999985;
wire [5:0] ext_axis_avg_buffer_0_s_axi_araddr;
wire [2:0] ext_axis_avg_buffer_0_s_axi_arprot;
wire  ext_axis_avg_buffer_0_s_axi_arready;
wire  ext_axis_avg_buffer_0_s_axi_arvalid;
wire [5:0] ext_axis_avg_buffer_0_s_axi_awaddr;
wire [2:0] ext_axis_avg_buffer_0_s_axi_awprot;
wire  ext_axis_avg_buffer_0_s_axi_awready;
wire  ext_axis_avg_buffer_0_s_axi_awvalid;
wire  ext_axis_avg_buffer_0_s_axi_bready;
wire [1:0] ext_axis_avg_buffer_0_s_axi_bresp;
wire  ext_axis_avg_buffer_0_s_axi_bvalid;
wire [31:0] ext_axis_avg_buffer_0_s_axi_rdata;
wire  ext_axis_avg_buffer_0_s_axi_rready;
wire [1:0] ext_axis_avg_buffer_0_s_axi_rresp;
wire  ext_axis_avg_buffer_0_s_axi_rvalid;
wire [31:0] ext_axis_avg_buffer_0_s_axi_wdata;
wire  ext_axis_avg_buffer_0_s_axi_wready;
wire [3:0] ext_axis_avg_buffer_0_s_axi_wstrb;
wire  ext_axis_avg_buffer_0_s_axi_wvalid;
wire [5:0] ext_axis_avg_buffer_1_s_axi_araddr;
wire [2:0] ext_axis_avg_buffer_1_s_axi_arprot;
wire  ext_axis_avg_buffer_1_s_axi_arready;
wire  ext_axis_avg_buffer_1_s_axi_arvalid;
wire [5:0] ext_axis_avg_buffer_1_s_axi_awaddr;
wire [2:0] ext_axis_avg_buffer_1_s_axi_awprot;
wire  ext_axis_avg_buffer_1_s_axi_awready;
wire  ext_axis_avg_buffer_1_s_axi_awvalid;
wire  ext_axis_avg_buffer_1_s_axi_bready;
wire [1:0] ext_axis_avg_buffer_1_s_axi_bresp;
wire  ext_axis_avg_buffer_1_s_axi_bvalid;
wire [31:0] ext_axis_avg_buffer_1_s_axi_rdata;
wire  ext_axis_avg_buffer_1_s_axi_rready;
wire [1:0] ext_axis_avg_buffer_1_s_axi_rresp;
wire  ext_axis_avg_buffer_1_s_axi_rvalid;
wire [31:0] ext_axis_avg_buffer_1_s_axi_wdata;
wire  ext_axis_avg_buffer_1_s_axi_wready;
wire [3:0] ext_axis_avg_buffer_1_s_axi_wstrb;
wire  ext_axis_avg_buffer_1_s_axi_wvalid;
wire [5:0] ext_axis_avg_buffer_2_s_axi_araddr;
wire [2:0] ext_axis_avg_buffer_2_s_axi_arprot;
wire  ext_axis_avg_buffer_2_s_axi_arready;
wire  ext_axis_avg_buffer_2_s_axi_arvalid;
wire [5:0] ext_axis_avg_buffer_2_s_axi_awaddr;
wire [2:0] ext_axis_avg_buffer_2_s_axi_awprot;
wire  ext_axis_avg_buffer_2_s_axi_awready;
wire  ext_axis_avg_buffer_2_s_axi_awvalid;
wire  ext_axis_avg_buffer_2_s_axi_bready;
wire [1:0] ext_axis_avg_buffer_2_s_axi_bresp;
wire  ext_axis_avg_buffer_2_s_axi_bvalid;
wire [31:0] ext_axis_avg_buffer_2_s_axi_rdata;
wire  ext_axis_avg_buffer_2_s_axi_rready;
wire [1:0] ext_axis_avg_buffer_2_s_axi_rresp;
wire  ext_axis_avg_buffer_2_s_axi_rvalid;
wire [31:0] ext_axis_avg_buffer_2_s_axi_wdata;
wire  ext_axis_avg_buffer_2_s_axi_wready;
wire [3:0] ext_axis_avg_buffer_2_s_axi_wstrb;
wire  ext_axis_avg_buffer_2_s_axi_wvalid;
wire [5:0] ext_axis_avg_buffer_3_s_axi_araddr;
wire [2:0] ext_axis_avg_buffer_3_s_axi_arprot;
wire  ext_axis_avg_buffer_3_s_axi_arready;
wire  ext_axis_avg_buffer_3_s_axi_arvalid;
wire [5:0] ext_axis_avg_buffer_3_s_axi_awaddr;
wire [2:0] ext_axis_avg_buffer_3_s_axi_awprot;
wire  ext_axis_avg_buffer_3_s_axi_awready;
wire  ext_axis_avg_buffer_3_s_axi_awvalid;
wire  ext_axis_avg_buffer_3_s_axi_bready;
wire [1:0] ext_axis_avg_buffer_3_s_axi_bresp;
wire  ext_axis_avg_buffer_3_s_axi_bvalid;
wire [31:0] ext_axis_avg_buffer_3_s_axi_rdata;
wire  ext_axis_avg_buffer_3_s_axi_rready;
wire [1:0] ext_axis_avg_buffer_3_s_axi_rresp;
wire  ext_axis_avg_buffer_3_s_axi_rvalid;
wire [31:0] ext_axis_avg_buffer_3_s_axi_wdata;
wire  ext_axis_avg_buffer_3_s_axi_wready;
wire [3:0] ext_axis_avg_buffer_3_s_axi_wstrb;
wire  ext_axis_avg_buffer_3_s_axi_wvalid;
wire [5:0] ext_axis_awg_tuning_v1_10_s_axi_araddr;
wire [2:0] ext_axis_awg_tuning_v1_10_s_axi_arprot;
wire  ext_axis_awg_tuning_v1_10_s_axi_arready;
wire  ext_axis_awg_tuning_v1_10_s_axi_arvalid;
wire [5:0] ext_axis_awg_tuning_v1_10_s_axi_awaddr;
wire [2:0] ext_axis_awg_tuning_v1_10_s_axi_awprot;
wire  ext_axis_awg_tuning_v1_10_s_axi_awready;
wire  ext_axis_awg_tuning_v1_10_s_axi_awvalid;
wire  ext_axis_awg_tuning_v1_10_s_axi_bready;
wire [1:0] ext_axis_awg_tuning_v1_10_s_axi_bresp;
wire  ext_axis_awg_tuning_v1_10_s_axi_bvalid;
wire [31:0] ext_axis_awg_tuning_v1_10_s_axi_rdata;
wire  ext_axis_awg_tuning_v1_10_s_axi_rready;
wire [1:0] ext_axis_awg_tuning_v1_10_s_axi_rresp;
wire  ext_axis_awg_tuning_v1_10_s_axi_rvalid;
wire [31:0] ext_axis_awg_tuning_v1_10_s_axi_wdata;
wire  ext_axis_awg_tuning_v1_10_s_axi_wready;
wire [3:0] ext_axis_awg_tuning_v1_10_s_axi_wstrb;
wire  ext_axis_awg_tuning_v1_10_s_axi_wvalid;
wire [5:0] ext_axis_awg_tuning_v1_11_s_axi_araddr;
wire [2:0] ext_axis_awg_tuning_v1_11_s_axi_arprot;
wire  ext_axis_awg_tuning_v1_11_s_axi_arready;
wire  ext_axis_awg_tuning_v1_11_s_axi_arvalid;
wire [5:0] ext_axis_awg_tuning_v1_11_s_axi_awaddr;
wire [2:0] ext_axis_awg_tuning_v1_11_s_axi_awprot;
wire  ext_axis_awg_tuning_v1_11_s_axi_awready;
wire  ext_axis_awg_tuning_v1_11_s_axi_awvalid;
wire  ext_axis_awg_tuning_v1_11_s_axi_bready;
wire [1:0] ext_axis_awg_tuning_v1_11_s_axi_bresp;
wire  ext_axis_awg_tuning_v1_11_s_axi_bvalid;
wire [31:0] ext_axis_awg_tuning_v1_11_s_axi_rdata;
wire  ext_axis_awg_tuning_v1_11_s_axi_rready;
wire [1:0] ext_axis_awg_tuning_v1_11_s_axi_rresp;
wire  ext_axis_awg_tuning_v1_11_s_axi_rvalid;
wire [31:0] ext_axis_awg_tuning_v1_11_s_axi_wdata;
wire  ext_axis_awg_tuning_v1_11_s_axi_wready;
wire [3:0] ext_axis_awg_tuning_v1_11_s_axi_wstrb;
wire  ext_axis_awg_tuning_v1_11_s_axi_wvalid;
wire [5:0] ext_axis_awg_tuning_v1_4_s_axi_araddr;
wire [2:0] ext_axis_awg_tuning_v1_4_s_axi_arprot;
wire  ext_axis_awg_tuning_v1_4_s_axi_arready;
wire  ext_axis_awg_tuning_v1_4_s_axi_arvalid;
wire [5:0] ext_axis_awg_tuning_v1_4_s_axi_awaddr;
wire [2:0] ext_axis_awg_tuning_v1_4_s_axi_awprot;
wire  ext_axis_awg_tuning_v1_4_s_axi_awready;
wire  ext_axis_awg_tuning_v1_4_s_axi_awvalid;
wire  ext_axis_awg_tuning_v1_4_s_axi_bready;
wire [1:0] ext_axis_awg_tuning_v1_4_s_axi_bresp;
wire  ext_axis_awg_tuning_v1_4_s_axi_bvalid;
wire [31:0] ext_axis_awg_tuning_v1_4_s_axi_rdata;
wire  ext_axis_awg_tuning_v1_4_s_axi_rready;
wire [1:0] ext_axis_awg_tuning_v1_4_s_axi_rresp;
wire  ext_axis_awg_tuning_v1_4_s_axi_rvalid;
wire [31:0] ext_axis_awg_tuning_v1_4_s_axi_wdata;
wire  ext_axis_awg_tuning_v1_4_s_axi_wready;
wire [3:0] ext_axis_awg_tuning_v1_4_s_axi_wstrb;
wire  ext_axis_awg_tuning_v1_4_s_axi_wvalid;
wire [5:0] ext_axis_awg_tuning_v1_5_s_axi_araddr;
wire [2:0] ext_axis_awg_tuning_v1_5_s_axi_arprot;
wire  ext_axis_awg_tuning_v1_5_s_axi_arready;
wire  ext_axis_awg_tuning_v1_5_s_axi_arvalid;
wire [5:0] ext_axis_awg_tuning_v1_5_s_axi_awaddr;
wire [2:0] ext_axis_awg_tuning_v1_5_s_axi_awprot;
wire  ext_axis_awg_tuning_v1_5_s_axi_awready;
wire  ext_axis_awg_tuning_v1_5_s_axi_awvalid;
wire  ext_axis_awg_tuning_v1_5_s_axi_bready;
wire [1:0] ext_axis_awg_tuning_v1_5_s_axi_bresp;
wire  ext_axis_awg_tuning_v1_5_s_axi_bvalid;
wire [31:0] ext_axis_awg_tuning_v1_5_s_axi_rdata;
wire  ext_axis_awg_tuning_v1_5_s_axi_rready;
wire [1:0] ext_axis_awg_tuning_v1_5_s_axi_rresp;
wire  ext_axis_awg_tuning_v1_5_s_axi_rvalid;
wire [31:0] ext_axis_awg_tuning_v1_5_s_axi_wdata;
wire  ext_axis_awg_tuning_v1_5_s_axi_wready;
wire [3:0] ext_axis_awg_tuning_v1_5_s_axi_wstrb;
wire  ext_axis_awg_tuning_v1_5_s_axi_wvalid;
wire [5:0] ext_axis_awg_tuning_v1_6_s_axi_araddr;
wire [2:0] ext_axis_awg_tuning_v1_6_s_axi_arprot;
wire  ext_axis_awg_tuning_v1_6_s_axi_arready;
wire  ext_axis_awg_tuning_v1_6_s_axi_arvalid;
wire [5:0] ext_axis_awg_tuning_v1_6_s_axi_awaddr;
wire [2:0] ext_axis_awg_tuning_v1_6_s_axi_awprot;
wire  ext_axis_awg_tuning_v1_6_s_axi_awready;
wire  ext_axis_awg_tuning_v1_6_s_axi_awvalid;
wire  ext_axis_awg_tuning_v1_6_s_axi_bready;
wire [1:0] ext_axis_awg_tuning_v1_6_s_axi_bresp;
wire  ext_axis_awg_tuning_v1_6_s_axi_bvalid;
wire [31:0] ext_axis_awg_tuning_v1_6_s_axi_rdata;
wire  ext_axis_awg_tuning_v1_6_s_axi_rready;
wire [1:0] ext_axis_awg_tuning_v1_6_s_axi_rresp;
wire  ext_axis_awg_tuning_v1_6_s_axi_rvalid;
wire [31:0] ext_axis_awg_tuning_v1_6_s_axi_wdata;
wire  ext_axis_awg_tuning_v1_6_s_axi_wready;
wire [3:0] ext_axis_awg_tuning_v1_6_s_axi_wstrb;
wire  ext_axis_awg_tuning_v1_6_s_axi_wvalid;
wire [5:0] ext_axis_awg_tuning_v1_8_s_axi_araddr;
wire [2:0] ext_axis_awg_tuning_v1_8_s_axi_arprot;
wire  ext_axis_awg_tuning_v1_8_s_axi_arready;
wire  ext_axis_awg_tuning_v1_8_s_axi_arvalid;
wire [5:0] ext_axis_awg_tuning_v1_8_s_axi_awaddr;
wire [2:0] ext_axis_awg_tuning_v1_8_s_axi_awprot;
wire  ext_axis_awg_tuning_v1_8_s_axi_awready;
wire  ext_axis_awg_tuning_v1_8_s_axi_awvalid;
wire  ext_axis_awg_tuning_v1_8_s_axi_bready;
wire [1:0] ext_axis_awg_tuning_v1_8_s_axi_bresp;
wire  ext_axis_awg_tuning_v1_8_s_axi_bvalid;
wire [31:0] ext_axis_awg_tuning_v1_8_s_axi_rdata;
wire  ext_axis_awg_tuning_v1_8_s_axi_rready;
wire [1:0] ext_axis_awg_tuning_v1_8_s_axi_rresp;
wire  ext_axis_awg_tuning_v1_8_s_axi_rvalid;
wire [31:0] ext_axis_awg_tuning_v1_8_s_axi_wdata;
wire  ext_axis_awg_tuning_v1_8_s_axi_wready;
wire [3:0] ext_axis_awg_tuning_v1_8_s_axi_wstrb;
wire  ext_axis_awg_tuning_v1_8_s_axi_wvalid;
wire [5:0] ext_axis_awg_tuning_v1_9_s_axi_araddr;
wire [2:0] ext_axis_awg_tuning_v1_9_s_axi_arprot;
wire  ext_axis_awg_tuning_v1_9_s_axi_arready;
wire  ext_axis_awg_tuning_v1_9_s_axi_arvalid;
wire [5:0] ext_axis_awg_tuning_v1_9_s_axi_awaddr;
wire [2:0] ext_axis_awg_tuning_v1_9_s_axi_awprot;
wire  ext_axis_awg_tuning_v1_9_s_axi_awready;
wire  ext_axis_awg_tuning_v1_9_s_axi_awvalid;
wire  ext_axis_awg_tuning_v1_9_s_axi_bready;
wire [1:0] ext_axis_awg_tuning_v1_9_s_axi_bresp;
wire  ext_axis_awg_tuning_v1_9_s_axi_bvalid;
wire [31:0] ext_axis_awg_tuning_v1_9_s_axi_rdata;
wire  ext_axis_awg_tuning_v1_9_s_axi_rready;
wire [1:0] ext_axis_awg_tuning_v1_9_s_axi_rresp;
wire  ext_axis_awg_tuning_v1_9_s_axi_rvalid;
wire [31:0] ext_axis_awg_tuning_v1_9_s_axi_wdata;
wire  ext_axis_awg_tuning_v1_9_s_axi_wready;
wire [3:0] ext_axis_awg_tuning_v1_9_s_axi_wstrb;
wire  ext_axis_awg_tuning_v1_9_s_axi_wvalid;
wire [127:0] ext_axis_dyn_readout_v1_0_s1_axis_tdata;
wire  ext_axis_dyn_readout_v1_0_s1_axis_tready;
wire  ext_axis_dyn_readout_v1_0_s1_axis_tvalid;
wire [127:0] ext_axis_dyn_readout_v1_1_s1_axis_tdata;
wire  ext_axis_dyn_readout_v1_1_s1_axis_tready;
wire  ext_axis_dyn_readout_v1_1_s1_axis_tvalid;
wire [127:0] ext_axis_dyn_readout_v1_2_s1_axis_tdata;
wire  ext_axis_dyn_readout_v1_2_s1_axis_tready;
wire  ext_axis_dyn_readout_v1_2_s1_axis_tvalid;
wire [127:0] ext_axis_dyn_readout_v1_3_s1_axis_tdata;
wire  ext_axis_dyn_readout_v1_3_s1_axis_tready;
wire  ext_axis_dyn_readout_v1_3_s1_axis_tvalid;
wire [255:0] ext_axis_register_slice_0_m_axis_tdata;
wire  ext_axis_register_slice_0_m_axis_tready;
wire  ext_axis_register_slice_0_m_axis_tvalid;
wire [255:0] ext_axis_register_slice_10_m_axis_tdata;
wire  ext_axis_register_slice_10_m_axis_tready;
wire  ext_axis_register_slice_10_m_axis_tvalid;
wire [255:0] ext_axis_register_slice_11_m_axis_tdata;
wire  ext_axis_register_slice_11_m_axis_tready;
wire  ext_axis_register_slice_11_m_axis_tvalid;
wire [255:0] ext_axis_register_slice_12_m_axis_tdata;
wire  ext_axis_register_slice_12_m_axis_tready;
wire  ext_axis_register_slice_12_m_axis_tvalid;
wire [255:0] ext_axis_register_slice_13_m_axis_tdata;
wire  ext_axis_register_slice_13_m_axis_tready;
wire  ext_axis_register_slice_13_m_axis_tvalid;
wire [255:0] ext_axis_register_slice_14_m_axis_tdata;
wire  ext_axis_register_slice_14_m_axis_tready;
wire  ext_axis_register_slice_14_m_axis_tvalid;
wire [255:0] ext_axis_register_slice_15_m_axis_tdata;
wire  ext_axis_register_slice_15_m_axis_tready;
wire  ext_axis_register_slice_15_m_axis_tvalid;
wire [255:0] ext_axis_register_slice_16_m_axis_tdata;
wire  ext_axis_register_slice_16_m_axis_tready;
wire  ext_axis_register_slice_16_m_axis_tvalid;
wire [255:0] ext_axis_register_slice_1_m_axis_tdata;
wire  ext_axis_register_slice_1_m_axis_tready;
wire  ext_axis_register_slice_1_m_axis_tvalid;
wire [255:0] ext_axis_register_slice_2_m_axis_tdata;
wire  ext_axis_register_slice_2_m_axis_tready;
wire  ext_axis_register_slice_2_m_axis_tvalid;
wire [255:0] ext_axis_register_slice_3_m_axis_tdata;
wire  ext_axis_register_slice_3_m_axis_tready;
wire  ext_axis_register_slice_3_m_axis_tvalid;
wire [255:0] ext_axis_register_slice_8_m_axis_tdata;
wire  ext_axis_register_slice_8_m_axis_tready;
wire  ext_axis_register_slice_8_m_axis_tvalid;
wire [5:0] ext_axis_signal_gen_v6_0_s_axi_araddr;
wire [2:0] ext_axis_signal_gen_v6_0_s_axi_arprot;
wire  ext_axis_signal_gen_v6_0_s_axi_arready;
wire  ext_axis_signal_gen_v6_0_s_axi_arvalid;
wire [5:0] ext_axis_signal_gen_v6_0_s_axi_awaddr;
wire [2:0] ext_axis_signal_gen_v6_0_s_axi_awprot;
wire  ext_axis_signal_gen_v6_0_s_axi_awready;
wire  ext_axis_signal_gen_v6_0_s_axi_awvalid;
wire  ext_axis_signal_gen_v6_0_s_axi_bready;
wire [1:0] ext_axis_signal_gen_v6_0_s_axi_bresp;
wire  ext_axis_signal_gen_v6_0_s_axi_bvalid;
wire [31:0] ext_axis_signal_gen_v6_0_s_axi_rdata;
wire  ext_axis_signal_gen_v6_0_s_axi_rready;
wire [1:0] ext_axis_signal_gen_v6_0_s_axi_rresp;
wire  ext_axis_signal_gen_v6_0_s_axi_rvalid;
wire [31:0] ext_axis_signal_gen_v6_0_s_axi_wdata;
wire  ext_axis_signal_gen_v6_0_s_axi_wready;
wire [3:0] ext_axis_signal_gen_v6_0_s_axi_wstrb;
wire  ext_axis_signal_gen_v6_0_s_axi_wvalid;
wire [5:0] ext_axis_signal_gen_v6_1_s_axi_araddr;
wire [2:0] ext_axis_signal_gen_v6_1_s_axi_arprot;
wire  ext_axis_signal_gen_v6_1_s_axi_arready;
wire  ext_axis_signal_gen_v6_1_s_axi_arvalid;
wire [5:0] ext_axis_signal_gen_v6_1_s_axi_awaddr;
wire [2:0] ext_axis_signal_gen_v6_1_s_axi_awprot;
wire  ext_axis_signal_gen_v6_1_s_axi_awready;
wire  ext_axis_signal_gen_v6_1_s_axi_awvalid;
wire  ext_axis_signal_gen_v6_1_s_axi_bready;
wire [1:0] ext_axis_signal_gen_v6_1_s_axi_bresp;
wire  ext_axis_signal_gen_v6_1_s_axi_bvalid;
wire [31:0] ext_axis_signal_gen_v6_1_s_axi_rdata;
wire  ext_axis_signal_gen_v6_1_s_axi_rready;
wire [1:0] ext_axis_signal_gen_v6_1_s_axi_rresp;
wire  ext_axis_signal_gen_v6_1_s_axi_rvalid;
wire [31:0] ext_axis_signal_gen_v6_1_s_axi_wdata;
wire  ext_axis_signal_gen_v6_1_s_axi_wready;
wire [3:0] ext_axis_signal_gen_v6_1_s_axi_wstrb;
wire  ext_axis_signal_gen_v6_1_s_axi_wvalid;
wire [5:0] ext_axis_signal_gen_v6_2_s_axi_araddr;
wire [2:0] ext_axis_signal_gen_v6_2_s_axi_arprot;
wire  ext_axis_signal_gen_v6_2_s_axi_arready;
wire  ext_axis_signal_gen_v6_2_s_axi_arvalid;
wire [5:0] ext_axis_signal_gen_v6_2_s_axi_awaddr;
wire [2:0] ext_axis_signal_gen_v6_2_s_axi_awprot;
wire  ext_axis_signal_gen_v6_2_s_axi_awready;
wire  ext_axis_signal_gen_v6_2_s_axi_awvalid;
wire  ext_axis_signal_gen_v6_2_s_axi_bready;
wire [1:0] ext_axis_signal_gen_v6_2_s_axi_bresp;
wire  ext_axis_signal_gen_v6_2_s_axi_bvalid;
wire [31:0] ext_axis_signal_gen_v6_2_s_axi_rdata;
wire  ext_axis_signal_gen_v6_2_s_axi_rready;
wire [1:0] ext_axis_signal_gen_v6_2_s_axi_rresp;
wire  ext_axis_signal_gen_v6_2_s_axi_rvalid;
wire [31:0] ext_axis_signal_gen_v6_2_s_axi_wdata;
wire  ext_axis_signal_gen_v6_2_s_axi_wready;
wire [3:0] ext_axis_signal_gen_v6_2_s_axi_wstrb;
wire  ext_axis_signal_gen_v6_2_s_axi_wvalid;
wire [5:0] ext_axis_signal_gen_v6_3_s_axi_araddr;
wire [2:0] ext_axis_signal_gen_v6_3_s_axi_arprot;
wire  ext_axis_signal_gen_v6_3_s_axi_arready;
wire  ext_axis_signal_gen_v6_3_s_axi_arvalid;
wire [5:0] ext_axis_signal_gen_v6_3_s_axi_awaddr;
wire [2:0] ext_axis_signal_gen_v6_3_s_axi_awprot;
wire  ext_axis_signal_gen_v6_3_s_axi_awready;
wire  ext_axis_signal_gen_v6_3_s_axi_awvalid;
wire  ext_axis_signal_gen_v6_3_s_axi_bready;
wire [1:0] ext_axis_signal_gen_v6_3_s_axi_bresp;
wire  ext_axis_signal_gen_v6_3_s_axi_bvalid;
wire [31:0] ext_axis_signal_gen_v6_3_s_axi_rdata;
wire  ext_axis_signal_gen_v6_3_s_axi_rready;
wire [1:0] ext_axis_signal_gen_v6_3_s_axi_rresp;
wire  ext_axis_signal_gen_v6_3_s_axi_rvalid;
wire [31:0] ext_axis_signal_gen_v6_3_s_axi_wdata;
wire  ext_axis_signal_gen_v6_3_s_axi_wready;
wire [3:0] ext_axis_signal_gen_v6_3_s_axi_wstrb;
wire  ext_axis_signal_gen_v6_3_s_axi_wvalid;
wire [5:0] ext_axis_square_pulse_v1_0_s_axi_araddr;
wire [2:0] ext_axis_square_pulse_v1_0_s_axi_arprot;
wire  ext_axis_square_pulse_v1_0_s_axi_arready;
wire  ext_axis_square_pulse_v1_0_s_axi_arvalid;
wire [5:0] ext_axis_square_pulse_v1_0_s_axi_awaddr;
wire [2:0] ext_axis_square_pulse_v1_0_s_axi_awprot;
wire  ext_axis_square_pulse_v1_0_s_axi_awready;
wire  ext_axis_square_pulse_v1_0_s_axi_awvalid;
wire  ext_axis_square_pulse_v1_0_s_axi_bready;
wire [1:0] ext_axis_square_pulse_v1_0_s_axi_bresp;
wire  ext_axis_square_pulse_v1_0_s_axi_bvalid;
wire [31:0] ext_axis_square_pulse_v1_0_s_axi_rdata;
wire  ext_axis_square_pulse_v1_0_s_axi_rready;
wire [1:0] ext_axis_square_pulse_v1_0_s_axi_rresp;
wire  ext_axis_square_pulse_v1_0_s_axi_rvalid;
wire [31:0] ext_axis_square_pulse_v1_0_s_axi_wdata;
wire  ext_axis_square_pulse_v1_0_s_axi_wready;
wire [3:0] ext_axis_square_pulse_v1_0_s_axi_wstrb;
wire  ext_axis_square_pulse_v1_0_s_axi_wvalid;
wire [63:0] ext_axis_switch_avg_M00_AXIS_tdata;
wire [0:0] ext_axis_switch_avg_M00_AXIS_tlast;
wire [0:0] ext_axis_switch_avg_M00_AXIS_tready;
wire [0:0] ext_axis_switch_avg_M00_AXIS_tvalid;
wire [6:0] ext_axis_switch_avg_S_AXI_CTRL_araddr;
wire  ext_axis_switch_avg_S_AXI_CTRL_arready;
wire  ext_axis_switch_avg_S_AXI_CTRL_arvalid;
wire [6:0] ext_axis_switch_avg_S_AXI_CTRL_awaddr;
wire  ext_axis_switch_avg_S_AXI_CTRL_awready;
wire  ext_axis_switch_avg_S_AXI_CTRL_awvalid;
wire  ext_axis_switch_avg_S_AXI_CTRL_bready;
wire [1:0] ext_axis_switch_avg_S_AXI_CTRL_bresp;
wire  ext_axis_switch_avg_S_AXI_CTRL_bvalid;
wire [31:0] ext_axis_switch_avg_S_AXI_CTRL_rdata;
wire  ext_axis_switch_avg_S_AXI_CTRL_rready;
wire [1:0] ext_axis_switch_avg_S_AXI_CTRL_rresp;
wire  ext_axis_switch_avg_S_AXI_CTRL_rvalid;
wire [31:0] ext_axis_switch_avg_S_AXI_CTRL_wdata;
wire  ext_axis_switch_avg_S_AXI_CTRL_wready;
wire  ext_axis_switch_avg_S_AXI_CTRL_wvalid;
wire [31:0] ext_axis_switch_buf_M00_AXIS_tdata;
wire [0:0] ext_axis_switch_buf_M00_AXIS_tlast;
wire [0:0] ext_axis_switch_buf_M00_AXIS_tready;
wire [0:0] ext_axis_switch_buf_M00_AXIS_tvalid;
wire [6:0] ext_axis_switch_buf_S_AXI_CTRL_araddr;
wire  ext_axis_switch_buf_S_AXI_CTRL_arready;
wire  ext_axis_switch_buf_S_AXI_CTRL_arvalid;
wire [6:0] ext_axis_switch_buf_S_AXI_CTRL_awaddr;
wire  ext_axis_switch_buf_S_AXI_CTRL_awready;
wire  ext_axis_switch_buf_S_AXI_CTRL_awvalid;
wire  ext_axis_switch_buf_S_AXI_CTRL_bready;
wire [1:0] ext_axis_switch_buf_S_AXI_CTRL_bresp;
wire  ext_axis_switch_buf_S_AXI_CTRL_bvalid;
wire [31:0] ext_axis_switch_buf_S_AXI_CTRL_rdata;
wire  ext_axis_switch_buf_S_AXI_CTRL_rready;
wire [1:0] ext_axis_switch_buf_S_AXI_CTRL_rresp;
wire  ext_axis_switch_buf_S_AXI_CTRL_rvalid;
wire [31:0] ext_axis_switch_buf_S_AXI_CTRL_wdata;
wire  ext_axis_switch_buf_S_AXI_CTRL_wready;
wire  ext_axis_switch_buf_S_AXI_CTRL_wvalid;
wire [6:0] ext_axis_switch_ddr_S_AXI_CTRL_araddr;
wire  ext_axis_switch_ddr_S_AXI_CTRL_arready;
wire  ext_axis_switch_ddr_S_AXI_CTRL_arvalid;
wire [6:0] ext_axis_switch_ddr_S_AXI_CTRL_awaddr;
wire  ext_axis_switch_ddr_S_AXI_CTRL_awready;
wire  ext_axis_switch_ddr_S_AXI_CTRL_awvalid;
wire  ext_axis_switch_ddr_S_AXI_CTRL_bready;
wire [1:0] ext_axis_switch_ddr_S_AXI_CTRL_bresp;
wire  ext_axis_switch_ddr_S_AXI_CTRL_bvalid;
wire [31:0] ext_axis_switch_ddr_S_AXI_CTRL_rdata;
wire  ext_axis_switch_ddr_S_AXI_CTRL_rready;
wire [1:0] ext_axis_switch_ddr_S_AXI_CTRL_rresp;
wire  ext_axis_switch_ddr_S_AXI_CTRL_rvalid;
wire [31:0] ext_axis_switch_ddr_S_AXI_CTRL_wdata;
wire  ext_axis_switch_ddr_S_AXI_CTRL_wready;
wire  ext_axis_switch_ddr_S_AXI_CTRL_wvalid;
wire [31:0] ext_axis_switch_gen_M04_AXIS_tdata;
wire [3:0] ext_axis_switch_gen_M04_AXIS_tkeep;
wire [0:0] ext_axis_switch_gen_M04_AXIS_tlast;
wire [0:0] ext_axis_switch_gen_M04_AXIS_tready;
wire [0:0] ext_axis_switch_gen_M04_AXIS_tvalid;
wire [31:0] ext_axis_switch_gen_M05_AXIS_tdata;
wire [3:0] ext_axis_switch_gen_M05_AXIS_tkeep;
wire [0:0] ext_axis_switch_gen_M05_AXIS_tlast;
wire [0:0] ext_axis_switch_gen_M05_AXIS_tready;
wire [0:0] ext_axis_switch_gen_M05_AXIS_tvalid;
wire [31:0] ext_axis_switch_gen_M06_AXIS_tdata;
wire [3:0] ext_axis_switch_gen_M06_AXIS_tkeep;
wire [0:0] ext_axis_switch_gen_M06_AXIS_tlast;
wire [0:0] ext_axis_switch_gen_M06_AXIS_tready;
wire [0:0] ext_axis_switch_gen_M06_AXIS_tvalid;
wire [31:0] ext_axis_switch_gen_M07_AXIS_tdata;
wire [3:0] ext_axis_switch_gen_M07_AXIS_tkeep;
wire [0:0] ext_axis_switch_gen_M07_AXIS_tlast;
wire [0:0] ext_axis_switch_gen_M07_AXIS_tready;
wire [0:0] ext_axis_switch_gen_M07_AXIS_tvalid;
wire [31:0] ext_axis_switch_gen_M08_AXIS_tdata;
wire [3:0] ext_axis_switch_gen_M08_AXIS_tkeep;
wire [0:0] ext_axis_switch_gen_M08_AXIS_tlast;
wire [0:0] ext_axis_switch_gen_M08_AXIS_tready;
wire [0:0] ext_axis_switch_gen_M08_AXIS_tvalid;
wire [31:0] ext_axis_switch_gen_M09_AXIS_tdata;
wire [3:0] ext_axis_switch_gen_M09_AXIS_tkeep;
wire [0:0] ext_axis_switch_gen_M09_AXIS_tlast;
wire [0:0] ext_axis_switch_gen_M09_AXIS_tready;
wire [0:0] ext_axis_switch_gen_M09_AXIS_tvalid;
wire [31:0] ext_axis_switch_gen_M10_AXIS_tdata;
wire [3:0] ext_axis_switch_gen_M10_AXIS_tkeep;
wire [0:0] ext_axis_switch_gen_M10_AXIS_tlast;
wire [0:0] ext_axis_switch_gen_M10_AXIS_tready;
wire [0:0] ext_axis_switch_gen_M10_AXIS_tvalid;
wire [31:0] ext_axis_switch_gen_M11_AXIS_tdata;
wire [3:0] ext_axis_switch_gen_M11_AXIS_tkeep;
wire [0:0] ext_axis_switch_gen_M11_AXIS_tlast;
wire [0:0] ext_axis_switch_gen_M11_AXIS_tready;
wire [0:0] ext_axis_switch_gen_M11_AXIS_tvalid;
wire [31:0] ext_axis_switch_gen_S00_AXIS_tdata;
wire [3:0] ext_axis_switch_gen_S00_AXIS_tkeep;
wire [0:0] ext_axis_switch_gen_S00_AXIS_tlast;
wire [0:0] ext_axis_switch_gen_S00_AXIS_tready;
wire [0:0] ext_axis_switch_gen_S00_AXIS_tvalid;
wire [6:0] ext_axis_switch_gen_S_AXI_CTRL_araddr;
wire  ext_axis_switch_gen_S_AXI_CTRL_arready;
wire  ext_axis_switch_gen_S_AXI_CTRL_arvalid;
wire [6:0] ext_axis_switch_gen_S_AXI_CTRL_awaddr;
wire  ext_axis_switch_gen_S_AXI_CTRL_awready;
wire  ext_axis_switch_gen_S_AXI_CTRL_awvalid;
wire  ext_axis_switch_gen_S_AXI_CTRL_bready;
wire [1:0] ext_axis_switch_gen_S_AXI_CTRL_bresp;
wire  ext_axis_switch_gen_S_AXI_CTRL_bvalid;
wire [31:0] ext_axis_switch_gen_S_AXI_CTRL_rdata;
wire  ext_axis_switch_gen_S_AXI_CTRL_rready;
wire [1:0] ext_axis_switch_gen_S_AXI_CTRL_rresp;
wire  ext_axis_switch_gen_S_AXI_CTRL_rvalid;
wire [31:0] ext_axis_switch_gen_S_AXI_CTRL_wdata;
wire  ext_axis_switch_gen_S_AXI_CTRL_wready;
wire  ext_axis_switch_gen_S_AXI_CTRL_wvalid;
wire [6:0] ext_axis_switch_mr_S_AXI_CTRL_araddr;
wire  ext_axis_switch_mr_S_AXI_CTRL_arready;
wire  ext_axis_switch_mr_S_AXI_CTRL_arvalid;
wire [6:0] ext_axis_switch_mr_S_AXI_CTRL_awaddr;
wire  ext_axis_switch_mr_S_AXI_CTRL_awready;
wire  ext_axis_switch_mr_S_AXI_CTRL_awvalid;
wire  ext_axis_switch_mr_S_AXI_CTRL_bready;
wire [1:0] ext_axis_switch_mr_S_AXI_CTRL_bresp;
wire  ext_axis_switch_mr_S_AXI_CTRL_bvalid;
wire [31:0] ext_axis_switch_mr_S_AXI_CTRL_rdata;
wire  ext_axis_switch_mr_S_AXI_CTRL_rready;
wire [1:0] ext_axis_switch_mr_S_AXI_CTRL_rresp;
wire  ext_axis_switch_mr_S_AXI_CTRL_rvalid;
wire [31:0] ext_axis_switch_mr_S_AXI_CTRL_wdata;
wire  ext_axis_switch_mr_S_AXI_CTRL_wready;
wire  ext_axis_switch_mr_S_AXI_CTRL_wvalid;
wire [31:0] ext_axis_tproc64x32_x8_0_m0_axis_tdata;
wire  ext_axis_tproc64x32_x8_0_m0_axis_tlast;
wire  ext_axis_tproc64x32_x8_0_m0_axis_tready;
wire  ext_axis_tproc64x32_x8_0_m0_axis_tvalid;
wire [19:0] ext_axis_tproc64x32_x8_0_pmem_addr;
wire [63:0] ext_axis_tproc64x32_x8_0_pmem_do;
wire [31:0] ext_axis_tproc64x32_x8_0_s0_axis_tdata;
wire  ext_axis_tproc64x32_x8_0_s0_axis_tlast;
wire  ext_axis_tproc64x32_x8_0_s0_axis_tready;
wire  ext_axis_tproc64x32_x8_0_s0_axis_tvalid;
wire [31:0] ext_axis_tproc64x32_x8_0_s_axi_araddr;
wire [2:0] ext_axis_tproc64x32_x8_0_s_axi_arprot;
wire  ext_axis_tproc64x32_x8_0_s_axi_arready;
wire  ext_axis_tproc64x32_x8_0_s_axi_arvalid;
wire [31:0] ext_axis_tproc64x32_x8_0_s_axi_awaddr;
wire [2:0] ext_axis_tproc64x32_x8_0_s_axi_awprot;
wire  ext_axis_tproc64x32_x8_0_s_axi_awready;
wire  ext_axis_tproc64x32_x8_0_s_axi_awvalid;
wire  ext_axis_tproc64x32_x8_0_s_axi_bready;
wire [1:0] ext_axis_tproc64x32_x8_0_s_axi_bresp;
wire  ext_axis_tproc64x32_x8_0_s_axi_bvalid;
wire [31:0] ext_axis_tproc64x32_x8_0_s_axi_rdata;
wire  ext_axis_tproc64x32_x8_0_s_axi_rready;
wire [1:0] ext_axis_tproc64x32_x8_0_s_axi_rresp;
wire  ext_axis_tproc64x32_x8_0_s_axi_rvalid;
wire [31:0] ext_axis_tproc64x32_x8_0_s_axi_wdata;
wire  ext_axis_tproc64x32_x8_0_s_axi_wready;
wire [3:0] ext_axis_tproc64x32_x8_0_s_axi_wstrb;
wire  ext_axis_tproc64x32_x8_0_s_axi_wvalid;
wire  ext_axis_tproc64x32_x8_0_start;
wire  ext_c_shift_ram_0_D;
wire [0:0] ext_c_shift_ram_0_Q;
wire [31:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awaddr;
wire [1:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awburst;
wire [3:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awcache;
wire [0:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awid;
wire [7:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlen;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlock;
wire [2:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awprot;
wire [3:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awqos;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awready;
wire [3:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awregion;
wire [2:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awsize;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awvalid;
wire [0:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bid;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bready;
wire [1:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bresp;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bvalid;
wire [255:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wdata;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wlast;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wready;
wire [31:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wstrb;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wvalid;
wire [7:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_araddr;
wire [2:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arprot;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arready;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arvalid;
wire [7:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awaddr;
wire [2:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awprot;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awready;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awvalid;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bready;
wire [1:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bresp;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bvalid;
wire [31:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rdata;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rready;
wire [1:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rresp;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rvalid;
wire [31:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wdata;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wready;
wire [3:0] ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wstrb;
wire  ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wvalid;
wire  ext_ddr4_axis_fir_decim_300to1_v2_0_capture_trigger;
wire [31:0] ext_mr_buffer_et_0_m00_axis_tdata;
wire  ext_mr_buffer_et_0_m00_axis_tlast;
wire  ext_mr_buffer_et_0_m00_axis_tready;
wire [3:0] ext_mr_buffer_et_0_m00_axis_tstrb;
wire  ext_mr_buffer_et_0_m00_axis_tvalid;
wire [5:0] ext_mr_buffer_et_0_s00_axi_araddr;
wire [2:0] ext_mr_buffer_et_0_s00_axi_arprot;
wire  ext_mr_buffer_et_0_s00_axi_arready;
wire  ext_mr_buffer_et_0_s00_axi_arvalid;
wire [5:0] ext_mr_buffer_et_0_s00_axi_awaddr;
wire [2:0] ext_mr_buffer_et_0_s00_axi_awprot;
wire  ext_mr_buffer_et_0_s00_axi_awready;
wire  ext_mr_buffer_et_0_s00_axi_awvalid;
wire  ext_mr_buffer_et_0_s00_axi_bready;
wire [1:0] ext_mr_buffer_et_0_s00_axi_bresp;
wire  ext_mr_buffer_et_0_s00_axi_bvalid;
wire [31:0] ext_mr_buffer_et_0_s00_axi_rdata;
wire  ext_mr_buffer_et_0_s00_axi_rready;
wire [1:0] ext_mr_buffer_et_0_s00_axi_rresp;
wire  ext_mr_buffer_et_0_s00_axi_rvalid;
wire [31:0] ext_mr_buffer_et_0_s00_axi_wdata;
wire  ext_mr_buffer_et_0_s00_axi_wready;
wire [3:0] ext_mr_buffer_et_0_s00_axi_wstrb;
wire  ext_mr_buffer_et_0_s00_axi_wvalid;
wire  ext_qick_vec2bit_0_dout0;
wire  ext_qick_vec2bit_0_dout1;
wire  ext_qick_vec2bit_0_dout2;
wire  ext_qick_vec2bit_0_dout3;
wire  ext_qick_vec2bit_0_dout4;
wire  ext_qick_vec2bit_0_dout5;
wire  ext_qick_vec2bit_0_dout6;
wire [63:0] ext_xlconstant_0_dout;
wire [0:0] ext_xlconstant_1_dout;
wire [0:0] ext_xlconstant_2_dout;
wire [7:0] ext_xlconstant_3_dout;
wire [11:0] ext_xlconstant_4_dout;
logic  resetn;
assign ext_axis_avg_buffer_0_s_axi_araddr = host_addr;
assign ext_axis_avg_buffer_0_s_axi_arprot = '0;
assign ext_axis_avg_buffer_0_s_axi_arvalid = host_ar && selected==0;
assign ext_axis_avg_buffer_0_s_axi_awaddr = host_addr;
assign ext_axis_avg_buffer_0_s_axi_awprot = '0;
assign ext_axis_avg_buffer_0_s_axi_awvalid = host_aw && selected==0;
assign ext_axis_avg_buffer_0_s_axi_bready = host_bready && selected==0;
assign ext_axis_avg_buffer_0_s_axi_rready = 1'b1;
assign ext_axis_avg_buffer_0_s_axi_wdata = host_data;
assign ext_axis_avg_buffer_0_s_axi_wstrb = '1;
assign ext_axis_avg_buffer_0_s_axi_wvalid = host_w && selected==0;
assign ext_axis_avg_buffer_1_s_axi_araddr = host_addr;
assign ext_axis_avg_buffer_1_s_axi_arprot = '0;
assign ext_axis_avg_buffer_1_s_axi_arvalid = host_ar && selected==1;
assign ext_axis_avg_buffer_1_s_axi_awaddr = host_addr;
assign ext_axis_avg_buffer_1_s_axi_awprot = '0;
assign ext_axis_avg_buffer_1_s_axi_awvalid = host_aw && selected==1;
assign ext_axis_avg_buffer_1_s_axi_bready = host_bready && selected==1;
assign ext_axis_avg_buffer_1_s_axi_rready = 1'b1;
assign ext_axis_avg_buffer_1_s_axi_wdata = host_data;
assign ext_axis_avg_buffer_1_s_axi_wstrb = '1;
assign ext_axis_avg_buffer_1_s_axi_wvalid = host_w && selected==1;
assign ext_axis_avg_buffer_2_s_axi_araddr = host_addr;
assign ext_axis_avg_buffer_2_s_axi_arprot = '0;
assign ext_axis_avg_buffer_2_s_axi_arvalid = host_ar && selected==2;
assign ext_axis_avg_buffer_2_s_axi_awaddr = host_addr;
assign ext_axis_avg_buffer_2_s_axi_awprot = '0;
assign ext_axis_avg_buffer_2_s_axi_awvalid = host_aw && selected==2;
assign ext_axis_avg_buffer_2_s_axi_bready = host_bready && selected==2;
assign ext_axis_avg_buffer_2_s_axi_rready = 1'b1;
assign ext_axis_avg_buffer_2_s_axi_wdata = host_data;
assign ext_axis_avg_buffer_2_s_axi_wstrb = '1;
assign ext_axis_avg_buffer_2_s_axi_wvalid = host_w && selected==2;
assign ext_axis_avg_buffer_3_s_axi_araddr = host_addr;
assign ext_axis_avg_buffer_3_s_axi_arprot = '0;
assign ext_axis_avg_buffer_3_s_axi_arvalid = host_ar && selected==3;
assign ext_axis_avg_buffer_3_s_axi_awaddr = host_addr;
assign ext_axis_avg_buffer_3_s_axi_awprot = '0;
assign ext_axis_avg_buffer_3_s_axi_awvalid = host_aw && selected==3;
assign ext_axis_avg_buffer_3_s_axi_bready = host_bready && selected==3;
assign ext_axis_avg_buffer_3_s_axi_rready = 1'b1;
assign ext_axis_avg_buffer_3_s_axi_wdata = host_data;
assign ext_axis_avg_buffer_3_s_axi_wstrb = '1;
assign ext_axis_avg_buffer_3_s_axi_wvalid = host_w && selected==3;
assign ext_axis_awg_tuning_v1_10_s_axi_araddr = host_addr;
assign ext_axis_awg_tuning_v1_10_s_axi_arprot = '0;
assign ext_axis_awg_tuning_v1_10_s_axi_arvalid = host_ar && selected==4;
assign ext_axis_awg_tuning_v1_10_s_axi_awaddr = host_addr;
assign ext_axis_awg_tuning_v1_10_s_axi_awprot = '0;
assign ext_axis_awg_tuning_v1_10_s_axi_awvalid = host_aw && selected==4;
assign ext_axis_awg_tuning_v1_10_s_axi_bready = host_bready && selected==4;
assign ext_axis_awg_tuning_v1_10_s_axi_rready = 1'b1;
assign ext_axis_awg_tuning_v1_10_s_axi_wdata = host_data;
assign ext_axis_awg_tuning_v1_10_s_axi_wstrb = '1;
assign ext_axis_awg_tuning_v1_10_s_axi_wvalid = host_w && selected==4;
assign ext_axis_awg_tuning_v1_11_s_axi_araddr = host_addr;
assign ext_axis_awg_tuning_v1_11_s_axi_arprot = '0;
assign ext_axis_awg_tuning_v1_11_s_axi_arvalid = host_ar && selected==5;
assign ext_axis_awg_tuning_v1_11_s_axi_awaddr = host_addr;
assign ext_axis_awg_tuning_v1_11_s_axi_awprot = '0;
assign ext_axis_awg_tuning_v1_11_s_axi_awvalid = host_aw && selected==5;
assign ext_axis_awg_tuning_v1_11_s_axi_bready = host_bready && selected==5;
assign ext_axis_awg_tuning_v1_11_s_axi_rready = 1'b1;
assign ext_axis_awg_tuning_v1_11_s_axi_wdata = host_data;
assign ext_axis_awg_tuning_v1_11_s_axi_wstrb = '1;
assign ext_axis_awg_tuning_v1_11_s_axi_wvalid = host_w && selected==5;
assign ext_axis_awg_tuning_v1_4_s_axi_araddr = host_addr;
assign ext_axis_awg_tuning_v1_4_s_axi_arprot = '0;
assign ext_axis_awg_tuning_v1_4_s_axi_arvalid = host_ar && selected==6;
assign ext_axis_awg_tuning_v1_4_s_axi_awaddr = host_addr;
assign ext_axis_awg_tuning_v1_4_s_axi_awprot = '0;
assign ext_axis_awg_tuning_v1_4_s_axi_awvalid = host_aw && selected==6;
assign ext_axis_awg_tuning_v1_4_s_axi_bready = host_bready && selected==6;
assign ext_axis_awg_tuning_v1_4_s_axi_rready = 1'b1;
assign ext_axis_awg_tuning_v1_4_s_axi_wdata = host_data;
assign ext_axis_awg_tuning_v1_4_s_axi_wstrb = '1;
assign ext_axis_awg_tuning_v1_4_s_axi_wvalid = host_w && selected==6;
assign ext_axis_awg_tuning_v1_5_s_axi_araddr = host_addr;
assign ext_axis_awg_tuning_v1_5_s_axi_arprot = '0;
assign ext_axis_awg_tuning_v1_5_s_axi_arvalid = host_ar && selected==7;
assign ext_axis_awg_tuning_v1_5_s_axi_awaddr = host_addr;
assign ext_axis_awg_tuning_v1_5_s_axi_awprot = '0;
assign ext_axis_awg_tuning_v1_5_s_axi_awvalid = host_aw && selected==7;
assign ext_axis_awg_tuning_v1_5_s_axi_bready = host_bready && selected==7;
assign ext_axis_awg_tuning_v1_5_s_axi_rready = 1'b1;
assign ext_axis_awg_tuning_v1_5_s_axi_wdata = host_data;
assign ext_axis_awg_tuning_v1_5_s_axi_wstrb = '1;
assign ext_axis_awg_tuning_v1_5_s_axi_wvalid = host_w && selected==7;
assign ext_axis_awg_tuning_v1_6_s_axi_araddr = host_addr;
assign ext_axis_awg_tuning_v1_6_s_axi_arprot = '0;
assign ext_axis_awg_tuning_v1_6_s_axi_arvalid = host_ar && selected==8;
assign ext_axis_awg_tuning_v1_6_s_axi_awaddr = host_addr;
assign ext_axis_awg_tuning_v1_6_s_axi_awprot = '0;
assign ext_axis_awg_tuning_v1_6_s_axi_awvalid = host_aw && selected==8;
assign ext_axis_awg_tuning_v1_6_s_axi_bready = host_bready && selected==8;
assign ext_axis_awg_tuning_v1_6_s_axi_rready = 1'b1;
assign ext_axis_awg_tuning_v1_6_s_axi_wdata = host_data;
assign ext_axis_awg_tuning_v1_6_s_axi_wstrb = '1;
assign ext_axis_awg_tuning_v1_6_s_axi_wvalid = host_w && selected==8;
assign ext_axis_awg_tuning_v1_8_s_axi_araddr = host_addr;
assign ext_axis_awg_tuning_v1_8_s_axi_arprot = '0;
assign ext_axis_awg_tuning_v1_8_s_axi_arvalid = host_ar && selected==9;
assign ext_axis_awg_tuning_v1_8_s_axi_awaddr = host_addr;
assign ext_axis_awg_tuning_v1_8_s_axi_awprot = '0;
assign ext_axis_awg_tuning_v1_8_s_axi_awvalid = host_aw && selected==9;
assign ext_axis_awg_tuning_v1_8_s_axi_bready = host_bready && selected==9;
assign ext_axis_awg_tuning_v1_8_s_axi_rready = 1'b1;
assign ext_axis_awg_tuning_v1_8_s_axi_wdata = host_data;
assign ext_axis_awg_tuning_v1_8_s_axi_wstrb = '1;
assign ext_axis_awg_tuning_v1_8_s_axi_wvalid = host_w && selected==9;
assign ext_axis_awg_tuning_v1_9_s_axi_araddr = host_addr;
assign ext_axis_awg_tuning_v1_9_s_axi_arprot = '0;
assign ext_axis_awg_tuning_v1_9_s_axi_arvalid = host_ar && selected==10;
assign ext_axis_awg_tuning_v1_9_s_axi_awaddr = host_addr;
assign ext_axis_awg_tuning_v1_9_s_axi_awprot = '0;
assign ext_axis_awg_tuning_v1_9_s_axi_awvalid = host_aw && selected==10;
assign ext_axis_awg_tuning_v1_9_s_axi_bready = host_bready && selected==10;
assign ext_axis_awg_tuning_v1_9_s_axi_rready = 1'b1;
assign ext_axis_awg_tuning_v1_9_s_axi_wdata = host_data;
assign ext_axis_awg_tuning_v1_9_s_axi_wstrb = '1;
assign ext_axis_awg_tuning_v1_9_s_axi_wvalid = host_w && selected==10;
assign ext_axis_dyn_readout_v1_0_s1_axis_tdata = adc_data;
assign ext_axis_dyn_readout_v1_0_s1_axis_tvalid = resetn;
assign ext_axis_dyn_readout_v1_1_s1_axis_tdata = '0;
assign ext_axis_dyn_readout_v1_1_s1_axis_tvalid = '0;
assign ext_axis_dyn_readout_v1_2_s1_axis_tdata = '0;
assign ext_axis_dyn_readout_v1_2_s1_axis_tvalid = '0;
assign ext_axis_dyn_readout_v1_3_s1_axis_tdata = '0;
assign ext_axis_dyn_readout_v1_3_s1_axis_tvalid = '0;
assign ext_axis_register_slice_0_m_axis_tready = 1'b1;
assign ext_axis_register_slice_10_m_axis_tready = 1'b1;
assign ext_axis_register_slice_11_m_axis_tready = 1'b1;
assign ext_axis_register_slice_12_m_axis_tready = 1'b1;
assign ext_axis_register_slice_13_m_axis_tready = 1'b1;
assign ext_axis_register_slice_14_m_axis_tready = 1'b1;
assign ext_axis_register_slice_15_m_axis_tready = 1'b1;
assign ext_axis_register_slice_16_m_axis_tready = 1'b1;
assign ext_axis_register_slice_1_m_axis_tready = 1'b1;
assign ext_axis_register_slice_2_m_axis_tready = 1'b1;
assign ext_axis_register_slice_3_m_axis_tready = 1'b1;
assign ext_axis_register_slice_8_m_axis_tready = 1'b1;
assign ext_axis_signal_gen_v6_0_s_axi_araddr = host_addr;
assign ext_axis_signal_gen_v6_0_s_axi_arprot = '0;
assign ext_axis_signal_gen_v6_0_s_axi_arvalid = host_ar && selected==11;
assign ext_axis_signal_gen_v6_0_s_axi_awaddr = host_addr;
assign ext_axis_signal_gen_v6_0_s_axi_awprot = '0;
assign ext_axis_signal_gen_v6_0_s_axi_awvalid = host_aw && selected==11;
assign ext_axis_signal_gen_v6_0_s_axi_bready = host_bready && selected==11;
assign ext_axis_signal_gen_v6_0_s_axi_rready = 1'b1;
assign ext_axis_signal_gen_v6_0_s_axi_wdata = host_data;
assign ext_axis_signal_gen_v6_0_s_axi_wstrb = '1;
assign ext_axis_signal_gen_v6_0_s_axi_wvalid = host_w && selected==11;
assign ext_axis_signal_gen_v6_1_s_axi_araddr = host_addr;
assign ext_axis_signal_gen_v6_1_s_axi_arprot = '0;
assign ext_axis_signal_gen_v6_1_s_axi_arvalid = host_ar && selected==12;
assign ext_axis_signal_gen_v6_1_s_axi_awaddr = host_addr;
assign ext_axis_signal_gen_v6_1_s_axi_awprot = '0;
assign ext_axis_signal_gen_v6_1_s_axi_awvalid = host_aw && selected==12;
assign ext_axis_signal_gen_v6_1_s_axi_bready = host_bready && selected==12;
assign ext_axis_signal_gen_v6_1_s_axi_rready = 1'b1;
assign ext_axis_signal_gen_v6_1_s_axi_wdata = host_data;
assign ext_axis_signal_gen_v6_1_s_axi_wstrb = '1;
assign ext_axis_signal_gen_v6_1_s_axi_wvalid = host_w && selected==12;
assign ext_axis_signal_gen_v6_2_s_axi_araddr = host_addr;
assign ext_axis_signal_gen_v6_2_s_axi_arprot = '0;
assign ext_axis_signal_gen_v6_2_s_axi_arvalid = host_ar && selected==13;
assign ext_axis_signal_gen_v6_2_s_axi_awaddr = host_addr;
assign ext_axis_signal_gen_v6_2_s_axi_awprot = '0;
assign ext_axis_signal_gen_v6_2_s_axi_awvalid = host_aw && selected==13;
assign ext_axis_signal_gen_v6_2_s_axi_bready = host_bready && selected==13;
assign ext_axis_signal_gen_v6_2_s_axi_rready = 1'b1;
assign ext_axis_signal_gen_v6_2_s_axi_wdata = host_data;
assign ext_axis_signal_gen_v6_2_s_axi_wstrb = '1;
assign ext_axis_signal_gen_v6_2_s_axi_wvalid = host_w && selected==13;
assign ext_axis_signal_gen_v6_3_s_axi_araddr = host_addr;
assign ext_axis_signal_gen_v6_3_s_axi_arprot = '0;
assign ext_axis_signal_gen_v6_3_s_axi_arvalid = host_ar && selected==14;
assign ext_axis_signal_gen_v6_3_s_axi_awaddr = host_addr;
assign ext_axis_signal_gen_v6_3_s_axi_awprot = '0;
assign ext_axis_signal_gen_v6_3_s_axi_awvalid = host_aw && selected==14;
assign ext_axis_signal_gen_v6_3_s_axi_bready = host_bready && selected==14;
assign ext_axis_signal_gen_v6_3_s_axi_rready = 1'b1;
assign ext_axis_signal_gen_v6_3_s_axi_wdata = host_data;
assign ext_axis_signal_gen_v6_3_s_axi_wstrb = '1;
assign ext_axis_signal_gen_v6_3_s_axi_wvalid = host_w && selected==14;
assign ext_axis_square_pulse_v1_0_s_axi_araddr = host_addr;
assign ext_axis_square_pulse_v1_0_s_axi_arprot = '0;
assign ext_axis_square_pulse_v1_0_s_axi_arvalid = host_ar && selected==15;
assign ext_axis_square_pulse_v1_0_s_axi_awaddr = host_addr;
assign ext_axis_square_pulse_v1_0_s_axi_awprot = '0;
assign ext_axis_square_pulse_v1_0_s_axi_awvalid = host_aw && selected==15;
assign ext_axis_square_pulse_v1_0_s_axi_bready = host_bready && selected==15;
assign ext_axis_square_pulse_v1_0_s_axi_rready = 1'b1;
assign ext_axis_square_pulse_v1_0_s_axi_wdata = host_data;
assign ext_axis_square_pulse_v1_0_s_axi_wstrb = '1;
assign ext_axis_square_pulse_v1_0_s_axi_wvalid = host_w && selected==15;
assign ext_axis_switch_avg_M00_AXIS_tready = 1'b1;
assign ext_axis_switch_avg_S_AXI_CTRL_araddr = host_addr;
assign ext_axis_switch_avg_S_AXI_CTRL_arvalid = host_ar && selected==16;
assign ext_axis_switch_avg_S_AXI_CTRL_awaddr = host_addr;
assign ext_axis_switch_avg_S_AXI_CTRL_awvalid = host_aw && selected==16;
assign ext_axis_switch_avg_S_AXI_CTRL_bready = host_bready && selected==16;
assign ext_axis_switch_avg_S_AXI_CTRL_rready = 1'b1;
assign ext_axis_switch_avg_S_AXI_CTRL_wdata = host_data;
assign ext_axis_switch_avg_S_AXI_CTRL_wvalid = host_w && selected==16;
assign ext_axis_switch_buf_M00_AXIS_tready = 1'b1;
assign ext_axis_switch_buf_S_AXI_CTRL_araddr = host_addr;
assign ext_axis_switch_buf_S_AXI_CTRL_arvalid = host_ar && selected==17;
assign ext_axis_switch_buf_S_AXI_CTRL_awaddr = host_addr;
assign ext_axis_switch_buf_S_AXI_CTRL_awvalid = host_aw && selected==17;
assign ext_axis_switch_buf_S_AXI_CTRL_bready = host_bready && selected==17;
assign ext_axis_switch_buf_S_AXI_CTRL_rready = 1'b1;
assign ext_axis_switch_buf_S_AXI_CTRL_wdata = host_data;
assign ext_axis_switch_buf_S_AXI_CTRL_wvalid = host_w && selected==17;
assign ext_axis_switch_ddr_S_AXI_CTRL_araddr = host_addr;
assign ext_axis_switch_ddr_S_AXI_CTRL_arvalid = host_ar && selected==18;
assign ext_axis_switch_ddr_S_AXI_CTRL_awaddr = host_addr;
assign ext_axis_switch_ddr_S_AXI_CTRL_awvalid = host_aw && selected==18;
assign ext_axis_switch_ddr_S_AXI_CTRL_bready = host_bready && selected==18;
assign ext_axis_switch_ddr_S_AXI_CTRL_rready = 1'b1;
assign ext_axis_switch_ddr_S_AXI_CTRL_wdata = host_data;
assign ext_axis_switch_ddr_S_AXI_CTRL_wvalid = host_w && selected==18;
assign ext_axis_switch_gen_M04_AXIS_tready = 1'b1;
assign ext_axis_switch_gen_M05_AXIS_tready = 1'b1;
assign ext_axis_switch_gen_M06_AXIS_tready = 1'b1;
assign ext_axis_switch_gen_M07_AXIS_tready = 1'b1;
assign ext_axis_switch_gen_M08_AXIS_tready = 1'b1;
assign ext_axis_switch_gen_M09_AXIS_tready = 1'b1;
assign ext_axis_switch_gen_M10_AXIS_tready = 1'b1;
assign ext_axis_switch_gen_M11_AXIS_tready = 1'b1;
assign ext_axis_switch_gen_S00_AXIS_tdata = '0;
assign ext_axis_switch_gen_S00_AXIS_tkeep = '0;
assign ext_axis_switch_gen_S00_AXIS_tlast = '0;
assign ext_axis_switch_gen_S00_AXIS_tvalid = '0;
assign ext_axis_switch_gen_S_AXI_CTRL_araddr = host_addr;
assign ext_axis_switch_gen_S_AXI_CTRL_arvalid = host_ar && selected==19;
assign ext_axis_switch_gen_S_AXI_CTRL_awaddr = host_addr;
assign ext_axis_switch_gen_S_AXI_CTRL_awvalid = host_aw && selected==19;
assign ext_axis_switch_gen_S_AXI_CTRL_bready = host_bready && selected==19;
assign ext_axis_switch_gen_S_AXI_CTRL_rready = 1'b1;
assign ext_axis_switch_gen_S_AXI_CTRL_wdata = host_data;
assign ext_axis_switch_gen_S_AXI_CTRL_wvalid = host_w && selected==19;
assign ext_axis_switch_mr_S_AXI_CTRL_araddr = host_addr;
assign ext_axis_switch_mr_S_AXI_CTRL_arvalid = host_ar && selected==20;
assign ext_axis_switch_mr_S_AXI_CTRL_awaddr = host_addr;
assign ext_axis_switch_mr_S_AXI_CTRL_awvalid = host_aw && selected==20;
assign ext_axis_switch_mr_S_AXI_CTRL_bready = host_bready && selected==20;
assign ext_axis_switch_mr_S_AXI_CTRL_rready = 1'b1;
assign ext_axis_switch_mr_S_AXI_CTRL_wdata = host_data;
assign ext_axis_switch_mr_S_AXI_CTRL_wvalid = host_w && selected==20;
assign ext_axis_tproc64x32_x8_0_m0_axis_tready = 1'b1;
assign ext_axis_tproc64x32_x8_0_pmem_do = pmem_data;
assign ext_axis_tproc64x32_x8_0_s0_axis_tdata = '0;
assign ext_axis_tproc64x32_x8_0_s0_axis_tlast = '0;
assign ext_axis_tproc64x32_x8_0_s0_axis_tvalid = '0;
assign ext_axis_tproc64x32_x8_0_s_axi_araddr = host_addr;
assign ext_axis_tproc64x32_x8_0_s_axi_arprot = '0;
assign ext_axis_tproc64x32_x8_0_s_axi_arvalid = host_ar && selected==21;
assign ext_axis_tproc64x32_x8_0_s_axi_awaddr = host_addr;
assign ext_axis_tproc64x32_x8_0_s_axi_awprot = '0;
assign ext_axis_tproc64x32_x8_0_s_axi_awvalid = host_aw && selected==21;
assign ext_axis_tproc64x32_x8_0_s_axi_bready = host_bready && selected==21;
assign ext_axis_tproc64x32_x8_0_s_axi_rready = 1'b1;
assign ext_axis_tproc64x32_x8_0_s_axi_wdata = host_data;
assign ext_axis_tproc64x32_x8_0_s_axi_wstrb = '1;
assign ext_axis_tproc64x32_x8_0_s_axi_wvalid = host_w && selected==21;
assign ext_axis_tproc64x32_x8_0_start = '0;
assign ext_c_shift_ram_0_D = '0;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awready = 1'b1;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bid = '0;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bresp = '0;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bvalid = mem_bvalid;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wready = 1'b1;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_araddr = host_addr;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arprot = '0;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arvalid = host_ar && selected==22;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awaddr = host_addr;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awprot = '0;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awvalid = host_aw && selected==22;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bready = host_bready && selected==22;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rready = 1'b1;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wdata = host_data;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wstrb = '1;
assign ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wvalid = host_w && selected==22;
assign ext_mr_buffer_et_0_m00_axis_tready = 1'b1;
assign ext_mr_buffer_et_0_s00_axi_araddr = host_addr;
assign ext_mr_buffer_et_0_s00_axi_arprot = '0;
assign ext_mr_buffer_et_0_s00_axi_arvalid = host_ar && selected==23;
assign ext_mr_buffer_et_0_s00_axi_awaddr = host_addr;
assign ext_mr_buffer_et_0_s00_axi_awprot = '0;
assign ext_mr_buffer_et_0_s00_axi_awvalid = host_aw && selected==23;
assign ext_mr_buffer_et_0_s00_axi_bready = host_bready && selected==23;
assign ext_mr_buffer_et_0_s00_axi_rready = 1'b1;
assign ext_mr_buffer_et_0_s00_axi_wdata = host_data;
assign ext_mr_buffer_et_0_s00_axi_wstrb = '1;
assign ext_mr_buffer_et_0_s00_axi_wvalid = host_w && selected==23;
assign awready[0] = ext_axis_avg_buffer_0_s_axi_awready;
assign wready[0] = ext_axis_avg_buffer_0_s_axi_wready;
assign bvalid[0] = ext_axis_avg_buffer_0_s_axi_bvalid;
assign arready[0] = ext_axis_avg_buffer_0_s_axi_arready;
assign rvalid[0] = ext_axis_avg_buffer_0_s_axi_rvalid;
assign rdata[0] = ext_axis_avg_buffer_0_s_axi_rdata;
assign bresp[0] = ext_axis_avg_buffer_0_s_axi_bresp;
assign awready[1] = ext_axis_avg_buffer_1_s_axi_awready;
assign wready[1] = ext_axis_avg_buffer_1_s_axi_wready;
assign bvalid[1] = ext_axis_avg_buffer_1_s_axi_bvalid;
assign arready[1] = ext_axis_avg_buffer_1_s_axi_arready;
assign rvalid[1] = ext_axis_avg_buffer_1_s_axi_rvalid;
assign rdata[1] = ext_axis_avg_buffer_1_s_axi_rdata;
assign bresp[1] = ext_axis_avg_buffer_1_s_axi_bresp;
assign awready[2] = ext_axis_avg_buffer_2_s_axi_awready;
assign wready[2] = ext_axis_avg_buffer_2_s_axi_wready;
assign bvalid[2] = ext_axis_avg_buffer_2_s_axi_bvalid;
assign arready[2] = ext_axis_avg_buffer_2_s_axi_arready;
assign rvalid[2] = ext_axis_avg_buffer_2_s_axi_rvalid;
assign rdata[2] = ext_axis_avg_buffer_2_s_axi_rdata;
assign bresp[2] = ext_axis_avg_buffer_2_s_axi_bresp;
assign awready[3] = ext_axis_avg_buffer_3_s_axi_awready;
assign wready[3] = ext_axis_avg_buffer_3_s_axi_wready;
assign bvalid[3] = ext_axis_avg_buffer_3_s_axi_bvalid;
assign arready[3] = ext_axis_avg_buffer_3_s_axi_arready;
assign rvalid[3] = ext_axis_avg_buffer_3_s_axi_rvalid;
assign rdata[3] = ext_axis_avg_buffer_3_s_axi_rdata;
assign bresp[3] = ext_axis_avg_buffer_3_s_axi_bresp;
assign awready[4] = ext_axis_awg_tuning_v1_10_s_axi_awready;
assign wready[4] = ext_axis_awg_tuning_v1_10_s_axi_wready;
assign bvalid[4] = ext_axis_awg_tuning_v1_10_s_axi_bvalid;
assign arready[4] = ext_axis_awg_tuning_v1_10_s_axi_arready;
assign rvalid[4] = ext_axis_awg_tuning_v1_10_s_axi_rvalid;
assign rdata[4] = ext_axis_awg_tuning_v1_10_s_axi_rdata;
assign bresp[4] = ext_axis_awg_tuning_v1_10_s_axi_bresp;
assign awready[5] = ext_axis_awg_tuning_v1_11_s_axi_awready;
assign wready[5] = ext_axis_awg_tuning_v1_11_s_axi_wready;
assign bvalid[5] = ext_axis_awg_tuning_v1_11_s_axi_bvalid;
assign arready[5] = ext_axis_awg_tuning_v1_11_s_axi_arready;
assign rvalid[5] = ext_axis_awg_tuning_v1_11_s_axi_rvalid;
assign rdata[5] = ext_axis_awg_tuning_v1_11_s_axi_rdata;
assign bresp[5] = ext_axis_awg_tuning_v1_11_s_axi_bresp;
assign awready[6] = ext_axis_awg_tuning_v1_4_s_axi_awready;
assign wready[6] = ext_axis_awg_tuning_v1_4_s_axi_wready;
assign bvalid[6] = ext_axis_awg_tuning_v1_4_s_axi_bvalid;
assign arready[6] = ext_axis_awg_tuning_v1_4_s_axi_arready;
assign rvalid[6] = ext_axis_awg_tuning_v1_4_s_axi_rvalid;
assign rdata[6] = ext_axis_awg_tuning_v1_4_s_axi_rdata;
assign bresp[6] = ext_axis_awg_tuning_v1_4_s_axi_bresp;
assign awready[7] = ext_axis_awg_tuning_v1_5_s_axi_awready;
assign wready[7] = ext_axis_awg_tuning_v1_5_s_axi_wready;
assign bvalid[7] = ext_axis_awg_tuning_v1_5_s_axi_bvalid;
assign arready[7] = ext_axis_awg_tuning_v1_5_s_axi_arready;
assign rvalid[7] = ext_axis_awg_tuning_v1_5_s_axi_rvalid;
assign rdata[7] = ext_axis_awg_tuning_v1_5_s_axi_rdata;
assign bresp[7] = ext_axis_awg_tuning_v1_5_s_axi_bresp;
assign awready[8] = ext_axis_awg_tuning_v1_6_s_axi_awready;
assign wready[8] = ext_axis_awg_tuning_v1_6_s_axi_wready;
assign bvalid[8] = ext_axis_awg_tuning_v1_6_s_axi_bvalid;
assign arready[8] = ext_axis_awg_tuning_v1_6_s_axi_arready;
assign rvalid[8] = ext_axis_awg_tuning_v1_6_s_axi_rvalid;
assign rdata[8] = ext_axis_awg_tuning_v1_6_s_axi_rdata;
assign bresp[8] = ext_axis_awg_tuning_v1_6_s_axi_bresp;
assign awready[9] = ext_axis_awg_tuning_v1_8_s_axi_awready;
assign wready[9] = ext_axis_awg_tuning_v1_8_s_axi_wready;
assign bvalid[9] = ext_axis_awg_tuning_v1_8_s_axi_bvalid;
assign arready[9] = ext_axis_awg_tuning_v1_8_s_axi_arready;
assign rvalid[9] = ext_axis_awg_tuning_v1_8_s_axi_rvalid;
assign rdata[9] = ext_axis_awg_tuning_v1_8_s_axi_rdata;
assign bresp[9] = ext_axis_awg_tuning_v1_8_s_axi_bresp;
assign awready[10] = ext_axis_awg_tuning_v1_9_s_axi_awready;
assign wready[10] = ext_axis_awg_tuning_v1_9_s_axi_wready;
assign bvalid[10] = ext_axis_awg_tuning_v1_9_s_axi_bvalid;
assign arready[10] = ext_axis_awg_tuning_v1_9_s_axi_arready;
assign rvalid[10] = ext_axis_awg_tuning_v1_9_s_axi_rvalid;
assign rdata[10] = ext_axis_awg_tuning_v1_9_s_axi_rdata;
assign bresp[10] = ext_axis_awg_tuning_v1_9_s_axi_bresp;
assign awready[11] = ext_axis_signal_gen_v6_0_s_axi_awready;
assign wready[11] = ext_axis_signal_gen_v6_0_s_axi_wready;
assign bvalid[11] = ext_axis_signal_gen_v6_0_s_axi_bvalid;
assign arready[11] = ext_axis_signal_gen_v6_0_s_axi_arready;
assign rvalid[11] = ext_axis_signal_gen_v6_0_s_axi_rvalid;
assign rdata[11] = ext_axis_signal_gen_v6_0_s_axi_rdata;
assign bresp[11] = ext_axis_signal_gen_v6_0_s_axi_bresp;
assign awready[12] = ext_axis_signal_gen_v6_1_s_axi_awready;
assign wready[12] = ext_axis_signal_gen_v6_1_s_axi_wready;
assign bvalid[12] = ext_axis_signal_gen_v6_1_s_axi_bvalid;
assign arready[12] = ext_axis_signal_gen_v6_1_s_axi_arready;
assign rvalid[12] = ext_axis_signal_gen_v6_1_s_axi_rvalid;
assign rdata[12] = ext_axis_signal_gen_v6_1_s_axi_rdata;
assign bresp[12] = ext_axis_signal_gen_v6_1_s_axi_bresp;
assign awready[13] = ext_axis_signal_gen_v6_2_s_axi_awready;
assign wready[13] = ext_axis_signal_gen_v6_2_s_axi_wready;
assign bvalid[13] = ext_axis_signal_gen_v6_2_s_axi_bvalid;
assign arready[13] = ext_axis_signal_gen_v6_2_s_axi_arready;
assign rvalid[13] = ext_axis_signal_gen_v6_2_s_axi_rvalid;
assign rdata[13] = ext_axis_signal_gen_v6_2_s_axi_rdata;
assign bresp[13] = ext_axis_signal_gen_v6_2_s_axi_bresp;
assign awready[14] = ext_axis_signal_gen_v6_3_s_axi_awready;
assign wready[14] = ext_axis_signal_gen_v6_3_s_axi_wready;
assign bvalid[14] = ext_axis_signal_gen_v6_3_s_axi_bvalid;
assign arready[14] = ext_axis_signal_gen_v6_3_s_axi_arready;
assign rvalid[14] = ext_axis_signal_gen_v6_3_s_axi_rvalid;
assign rdata[14] = ext_axis_signal_gen_v6_3_s_axi_rdata;
assign bresp[14] = ext_axis_signal_gen_v6_3_s_axi_bresp;
assign awready[15] = ext_axis_square_pulse_v1_0_s_axi_awready;
assign wready[15] = ext_axis_square_pulse_v1_0_s_axi_wready;
assign bvalid[15] = ext_axis_square_pulse_v1_0_s_axi_bvalid;
assign arready[15] = ext_axis_square_pulse_v1_0_s_axi_arready;
assign rvalid[15] = ext_axis_square_pulse_v1_0_s_axi_rvalid;
assign rdata[15] = ext_axis_square_pulse_v1_0_s_axi_rdata;
assign bresp[15] = ext_axis_square_pulse_v1_0_s_axi_bresp;
assign awready[16] = ext_axis_switch_avg_S_AXI_CTRL_awready;
assign wready[16] = ext_axis_switch_avg_S_AXI_CTRL_wready;
assign bvalid[16] = ext_axis_switch_avg_S_AXI_CTRL_bvalid;
assign arready[16] = ext_axis_switch_avg_S_AXI_CTRL_arready;
assign rvalid[16] = ext_axis_switch_avg_S_AXI_CTRL_rvalid;
assign rdata[16] = ext_axis_switch_avg_S_AXI_CTRL_rdata;
assign bresp[16] = ext_axis_switch_avg_S_AXI_CTRL_bresp;
assign awready[17] = ext_axis_switch_buf_S_AXI_CTRL_awready;
assign wready[17] = ext_axis_switch_buf_S_AXI_CTRL_wready;
assign bvalid[17] = ext_axis_switch_buf_S_AXI_CTRL_bvalid;
assign arready[17] = ext_axis_switch_buf_S_AXI_CTRL_arready;
assign rvalid[17] = ext_axis_switch_buf_S_AXI_CTRL_rvalid;
assign rdata[17] = ext_axis_switch_buf_S_AXI_CTRL_rdata;
assign bresp[17] = ext_axis_switch_buf_S_AXI_CTRL_bresp;
assign awready[18] = ext_axis_switch_ddr_S_AXI_CTRL_awready;
assign wready[18] = ext_axis_switch_ddr_S_AXI_CTRL_wready;
assign bvalid[18] = ext_axis_switch_ddr_S_AXI_CTRL_bvalid;
assign arready[18] = ext_axis_switch_ddr_S_AXI_CTRL_arready;
assign rvalid[18] = ext_axis_switch_ddr_S_AXI_CTRL_rvalid;
assign rdata[18] = ext_axis_switch_ddr_S_AXI_CTRL_rdata;
assign bresp[18] = ext_axis_switch_ddr_S_AXI_CTRL_bresp;
assign awready[19] = ext_axis_switch_gen_S_AXI_CTRL_awready;
assign wready[19] = ext_axis_switch_gen_S_AXI_CTRL_wready;
assign bvalid[19] = ext_axis_switch_gen_S_AXI_CTRL_bvalid;
assign arready[19] = ext_axis_switch_gen_S_AXI_CTRL_arready;
assign rvalid[19] = ext_axis_switch_gen_S_AXI_CTRL_rvalid;
assign rdata[19] = ext_axis_switch_gen_S_AXI_CTRL_rdata;
assign bresp[19] = ext_axis_switch_gen_S_AXI_CTRL_bresp;
assign awready[20] = ext_axis_switch_mr_S_AXI_CTRL_awready;
assign wready[20] = ext_axis_switch_mr_S_AXI_CTRL_wready;
assign bvalid[20] = ext_axis_switch_mr_S_AXI_CTRL_bvalid;
assign arready[20] = ext_axis_switch_mr_S_AXI_CTRL_arready;
assign rvalid[20] = ext_axis_switch_mr_S_AXI_CTRL_rvalid;
assign rdata[20] = ext_axis_switch_mr_S_AXI_CTRL_rdata;
assign bresp[20] = ext_axis_switch_mr_S_AXI_CTRL_bresp;
assign awready[21] = ext_axis_tproc64x32_x8_0_s_axi_awready;
assign wready[21] = ext_axis_tproc64x32_x8_0_s_axi_wready;
assign bvalid[21] = ext_axis_tproc64x32_x8_0_s_axi_bvalid;
assign arready[21] = ext_axis_tproc64x32_x8_0_s_axi_arready;
assign rvalid[21] = ext_axis_tproc64x32_x8_0_s_axi_rvalid;
assign rdata[21] = ext_axis_tproc64x32_x8_0_s_axi_rdata;
assign bresp[21] = ext_axis_tproc64x32_x8_0_s_axi_bresp;
assign awready[22] = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_awready;
assign wready[22] = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_wready;
assign bvalid[22] = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bvalid;
assign arready[22] = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_arready;
assign rvalid[22] = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rvalid;
assign rdata[22] = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_rdata;
assign bresp[22] = ext_ddr4_axis_buffer_ddr_sample_v3_0_s_axi_bresp;
assign awready[23] = ext_mr_buffer_et_0_s00_axi_awready;
assign wready[23] = ext_mr_buffer_et_0_s00_axi_wready;
assign bvalid[23] = ext_mr_buffer_et_0_s00_axi_bvalid;
assign arready[23] = ext_mr_buffer_et_0_s00_axi_arready;
assign rvalid[23] = ext_mr_buffer_et_0_s00_axi_rvalid;
assign rdata[23] = ext_mr_buffer_et_0_s00_axi_rdata;
assign bresp[23] = ext_mr_buffer_et_0_s00_axi_bresp;
rc_wrapper dut (
    .clk_300000000(clk_300000000),
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
    .resetn(resetn)
);
initial clk_99999985=0; always #5.000000750 clk_99999985=~clk_99999985;
initial clk_300000000=0; always #1.666666667 clk_300000000=~clk_300000000;
initial clk_333250000=0; always #1.500375094 clk_333250000=~clk_333250000;
localparam TPROC=21;
localparam DDR=22;
localparam SWITCH=18;
// Actual dual-AWG path: full and focused DUTs execute the same PMEM image.
integer rc_file,rf_file,rf_cmd_file;
integer cycle=0,events_file,commands_file,samples_file,gpio_file,checks_file;
integer run_cycles=0,cycle_at_start=0,sample_words=0,errors=0;
string case_dir,output_dir;
wire [47:0] tproc_time=dut.sim_bd_i.axis_tproc64x32_x8_0.inst.tproc_i.t_cnt;
wire [255:0] awg1=ext_axis_register_slice_8_m_axis_tdata;
wire [255:0] awg3=ext_axis_register_slice_10_m_axis_tdata;
wire [6:0] gpio={ext_qick_vec2bit_0_dout6,ext_qick_vec2bit_0_dout5,
 ext_qick_vec2bit_0_dout4,ext_qick_vec2bit_0_dout3,ext_qick_vec2bit_0_dout2,
 ext_qick_vec2bit_0_dout1,ext_qick_vec2bit_0_dout0};
logic [255:0] last_awg1=0,last_awg3=0;
logic [6:0] last_gpio=0;

task automatic host_write(input integer target,input logic [31:0] address,input logic [31:0] data);
 integer timeout;
 begin
  @(negedge clk_99999985);
  selected=target;host_addr=address;host_data=data;host_aw=1;host_w=1;host_bready=0;
  timeout=0;
  while(host_aw || host_w) begin
   @(posedge clk_99999985);
   if(awready[target]) host_aw<=0;
   if(wready[target]) host_w<=0;
   timeout=timeout+1;
   if(timeout>1000) $fatal(1,"AXI request timeout");
   @(negedge clk_99999985);
  end
  host_bready=1;
  while(!bvalid[target]) begin
   @(negedge clk_99999985);timeout=timeout+1;
   if(timeout>1000) $fatal(1,"AXI response timeout");
  end
  if(bresp[target]!==0) $fatal(1,"AXI write error");
  @(negedge clk_99999985);selected=-1;host_bready=0;
 end
endtask

always @(posedge clk_300000000)
 pmem_data<=pmem[ext_axis_tproc64x32_x8_0_pmem_addr>>3];
always @(negedge clk_300000000) if(resetn) cycle=cycle+1;

always @(posedge clk_300000000) if(resetn) begin
 if(dut.sim_bd_i.axis_tproc64x32_x8_0.m5_axis_tvalid)
  $fwrite(events_file,"%0d,%0d,4,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m5_axis_tdata);
 if(dut.sim_bd_i.axis_tproc64x32_x8_0.m4_axis_tvalid)
  $fwrite(events_file,"%0d,%0d,3,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m4_axis_tdata);
 if(dut.sim_bd_i.axis_tproc64x32_x8_0.m1_axis_tvalid)
  $fwrite(events_file,"%0d,%0d,0,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m1_axis_tdata);
 if(dut.sim_bd_i.axis_tproc64x32_x8_0.m2_axis_tvalid)
  $fwrite(events_file,"%0d,%0d,1,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m2_axis_tdata);
 if(dut.sim_bd_i.axis_tproc64x32_x8_0.m8_axis_tvalid)
  $fwrite(events_file,"%0d,%0d,7,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m8_axis_tdata);
 if(dut.sim_bd_i.axis_awg_tuning_v1_4.s_axis_tvalid && dut.sim_bd_i.axis_awg_tuning_v1_4.s_axis_tready)
  if(cycle<cycle_at_start+12000)   $fwrite(commands_file,"%0d,1,%040h\n",cycle,dut.sim_bd_i.axis_awg_tuning_v1_4.s_axis_tdata);
 if(dut.sim_bd_i.axis_awg_tuning_v1_5.s_axis_tvalid && dut.sim_bd_i.axis_awg_tuning_v1_5.s_axis_tready)
  if(cycle<cycle_at_start+12000)   $fwrite(commands_file,"%0d,3,%040h\n",cycle,dut.sim_bd_i.axis_awg_tuning_v1_5.s_axis_tdata);
 #0.001;
 if(cycle>16) begin
  sample_words=sample_words+1;
  if($isunknown(awg1) || $isunknown(awg3)) begin
   errors=errors+1;
   if(errors<4) $display("Unknown AWG sample at %0d",cycle);
  end
 end
 if(cycle<cycle_at_start+12000 && (awg1!==last_awg1 || awg3!==last_awg3 || cycle%128==0)) begin
  $fwrite(samples_file,"%0d,%064h,%064h\n",cycle,awg1,awg3);
  last_awg1=awg1;last_awg3=awg3;
 end
 if(gpio!==last_gpio) begin
  $fwrite(gpio_file,"%0d,%0d,%h\n",cycle,tproc_time,gpio);last_gpio=gpio;
 end
end

initial begin : test
 integer f,scan,addr,data,require_end;
 string pmem_path;
 resetn=0;
 if(!$value$plusargs("CASE=%s",case_dir)) $fatal(1,"Missing CASE");
 if(!$value$plusargs("OUT=%s",output_dir)) $fatal(1,"Missing OUT");
 if(!$value$plusargs("CYCLES=%d",run_cycles)) $fatal(1,"Missing CYCLES");
 if(!$value$plusargs("REQUIRE_END=%d",require_end)) require_end=1;
 for(integer j=0;j<8192;j=j+1) pmem[j]=64'h3f00000000000000;
 pmem_path=$sformatf("%s/pmem.hex",case_dir);$readmemh(pmem_path,pmem);
 if($isunknown(pmem[0])) $fatal(1,"PMEM not loaded");
 rc_file=$fopen({output_dir,"/rc_analog.csv"},"w");
 $fwrite(rc_file,"cycle,channel,target,dac,after_rc\n");
 rf_file=$fopen({output_dir,"/rf_samples.csv"},"w");
 $fwrite(rf_file,"cycle,word\n");
 rf_cmd_file=$fopen({output_dir,"/rf_commands.csv"},"w");
 $fwrite(rf_cmd_file,"cycle,word\n");
 events_file=$fopen({output_dir,"/rtl_events.csv"},"w");
 commands_file=$fopen({output_dir,"/rtl_commands.csv"},"w");
 samples_file=$fopen({output_dir,"/rtl_samples.csv"},"w");
 gpio_file=$fopen({output_dir,"/rtl_gpio.csv"},"w");
 $fwrite(events_file,"cycle,tproc_time,port,word\n");
 $fwrite(commands_file,"cycle,gen,word\n");
 $fwrite(samples_file,"cycle,awg1,awg3\n");
 $fwrite(gpio_file,"cycle,tproc_time,value\n");
 repeat(50) @(negedge clk_99999985);resetn=1;
 host_write(TPROC,0,0);host_write(TPROC,4,0);
 f=$fopen({case_dir,"/dmem.txt"},"r");
 while(!$feof(f)) begin
  scan=$fscanf(f,"%h %h\n",addr,data);
  if(scan==2) host_write(TPROC,256+4*addr,data);
 end
 $fclose(f);
 repeat(100) @(negedge clk_300000000);
 wait(ddr_armed);
 cycle_at_start=cycle;host_write(TPROC,4,1);
 repeat(run_cycles) @(negedge clk_300000000);
 if(require_end && dut.sim_bd_i.axis_tproc64x32_x8_0.inst.tproc_i.ir_r[63:56]!==8'h3f)
  $fatal(1,"Program did not reach END");
 checks_file=$fopen({output_dir,"/rtl_checks.txt"},"w");
 $fwrite(checks_file,"samples_per_channel=%0d\nerrors=%0d\nstart_cycle=%0d\nend_cycle=%0d\nend_required=%0d\n",sample_words*16,errors,cycle_at_start,cycle,require_end);
 $fclose(rc_file);$fclose(rf_file);$fclose(rf_cmd_file);$fclose(checks_file);$fclose(events_file);$fclose(commands_file);$fclose(samples_file);$fclose(gpio_file);
 $display("RTL COMPLETE two-AWG samples/channel=%0d errors=%0d",sample_words*16,errors);
 if(errors) $fatal(1,"Unknown AWG output");
 $finish;
end

generate

begin: MONITOR0
 logic [255:0] nominal[0:10];
 real z=0,decay,max_error=0,error,y,target;
 integer sample;
 initial begin
  decay=$exp(-1.0/48000.0);
  for(integer i=0;i<11;i=i+1) nominal[i]=0;
 end
 always @(posedge clk_300000000) if(resetn) begin
  for(integer i=10;i>0;i=i-1) nominal[i]=nominal[i-1];
  nominal[0]=dut.sim_bd_i.axis_awg_tuning_v1_4.area_samples;
  #0.001;
  for(integer lane=0;lane<16;lane=lane+1) begin
   sample=$signed(dut.sim_bd_i.axis_awg_tuning_v1_4.m_axis_tdata[16*lane+:16]);
   target=$signed(nominal[10][16*lane+:16]);
   y=sample-z; error=y-target;if(error<0)error=-error;
   if(error>max_error)max_error=error;
   z=decay*z+(1.0-decay)*sample;
   if(lane==0 && cycle%4==0 && (0==12000 || cycle<cycle_at_start+12000))$fwrite(rc_file,"%0d,0,%f,%0d,%f\n",cycle,target,sample,y);
  end
 end
 final $display("GUI_RC_RESULT ch=0 max_error_codes=%f",max_error);
end

begin: MONITOR1
 logic [255:0] nominal[0:10];
 real z=0,decay,max_error=0,error,y,target;
 integer sample;
 initial begin
  decay=$exp(-1.0/48000.0);
  for(integer i=0;i<11;i=i+1) nominal[i]=0;
 end
 always @(posedge clk_300000000) if(resetn) begin
  for(integer i=10;i>0;i=i-1) nominal[i]=nominal[i-1];
  nominal[0]=dut.sim_bd_i.axis_awg_tuning_v1_5.area_samples;
  #0.001;
  for(integer lane=0;lane<16;lane=lane+1) begin
   sample=$signed(dut.sim_bd_i.axis_awg_tuning_v1_5.m_axis_tdata[16*lane+:16]);
   target=$signed(nominal[10][16*lane+:16]);
   y=sample-z; error=y-target;if(error<0)error=-error;
   if(error>max_error)max_error=error;
   z=decay*z+(1.0-decay)*sample;
   if(lane==0 && cycle%4==0 && (0==12000 || cycle<cycle_at_start+12000))$fwrite(rc_file,"%0d,1,%f,%0d,%f\n",cycle,target,sample,y);
  end
 end
 final $display("GUI_RC_RESULT ch=1 max_error_codes=%f",max_error);
end

begin: MONITOR2
 logic [255:0] nominal[0:10];
 real z=0,decay,max_error=0,error,y,target;
 integer sample;
 initial begin
  decay=$exp(-1.0/48000.0);
  for(integer i=0;i<11;i=i+1) nominal[i]=0;
 end
 always @(posedge clk_300000000) if(resetn) begin
  for(integer i=10;i>0;i=i-1) nominal[i]=nominal[i-1];
  nominal[0]=dut.sim_bd_i.axis_square_pulse_v1_0.raw_samples;
  #0.001;
  for(integer lane=0;lane<16;lane=lane+1) begin
   sample=$signed(dut.sim_bd_i.axis_square_pulse_v1_0.m_axis_tdata[16*lane+:16]);
   target=$signed(nominal[10][16*lane+:16]);
   y=sample-z; error=y-target;if(error<0)error=-error;
   if(error>max_error)max_error=error;
   z=decay*z+(1.0-decay)*sample;
   if(lane==0 && cycle%4==0 && (0==12000 || cycle<cycle_at_start+12000))$fwrite(rc_file,"%0d,2,%f,%0d,%f\n",cycle,target,sample,y);
  end
 end
 final $display("GUI_RC_RESULT ch=2 max_error_codes=%f",max_error);
end

begin: EXACT_AWG0
 logic signed [71:0] integral=0, qhistory[0:8], v, rounded;
 logic signed [15:0] previous_x=0;
 logic [255:0] expected[0:10];
 integer raw;
 longint samples=0;
 initial begin
  for(integer i=0;i<11;i=i+1) expected[i]=0;
  for(integer i=0;i<9;i=i+1) qhistory[i]=0;
 end
 always @(posedge clk_300000000) if(resetn) begin
  for(integer i=10;i>0;i=i-1) expected[i]=expected[i-1];
  for(integer i=8;i>0;i=i-1) qhistory[i]=qhistory[i-1];
  if(dut.sim_bd_i.axis_awg_tuning_v1_4.rc_clear || dut.sim_bd_i.axis_awg_tuning_v1_4.area_clear_rc) begin integral=0;previous_x=0;end
  for(integer lane=0;lane<16;lane=lane+1) begin
   raw=$signed(dut.sim_bd_i.axis_awg_tuning_v1_4.area_samples[16*lane+:16]);
   if(dut.sim_bd_i.axis_awg_tuning_v1_4.rc_enabled && dut.sim_bd_i.axis_awg_tuning_v1_4.area_valid)
    integral=integral+72'(raw+previous_x)*$signed({1'b0,dut.sim_bd_i.axis_awg_tuning_v1_4.rc_coefficient});
   if(dut.sim_bd_i.axis_awg_tuning_v1_4.area_valid)previous_x=raw;
   v=(72'(raw)<<<48)+integral;
   rounded=(v+(72'sd1<<49))>>>50;
   if(rounded>8191 || rounded< -8192) $fatal(1,"Unexpected AWG clipping ch=0");
   expected[0][16*lane+:16]=dut.sim_bd_i.axis_awg_tuning_v1_4.rc_enabled ? 16'(rounded*4) : 16'(raw);
  end
  qhistory[0]=integral;
  #0.001;
  if(cycle>30) begin
   if(dut.sim_bd_i.axis_awg_tuning_v1_4.m_axis_tdata!==expected[10] || dut.sim_bd_i.axis_awg_tuning_v1_4.GEN_RC.rc.integral!==qhistory[8])
    $fatal(1,"Exact AWG recurrence mismatch ch=0 cycle=%0d",cycle);
   samples=samples+16;
  end
 end
 final $display("EXACT_AWG_RESULT ch=0 samples=%0d",samples);
end

begin: EXACT_AWG1
 logic signed [71:0] integral=0, qhistory[0:8], v, rounded;
 logic signed [15:0] previous_x=0;
 logic [255:0] expected[0:10];
 integer raw;
 longint samples=0;
 initial begin
  for(integer i=0;i<11;i=i+1) expected[i]=0;
  for(integer i=0;i<9;i=i+1) qhistory[i]=0;
 end
 always @(posedge clk_300000000) if(resetn) begin
  for(integer i=10;i>0;i=i-1) expected[i]=expected[i-1];
  for(integer i=8;i>0;i=i-1) qhistory[i]=qhistory[i-1];
  if(dut.sim_bd_i.axis_awg_tuning_v1_5.rc_clear || dut.sim_bd_i.axis_awg_tuning_v1_5.area_clear_rc) begin integral=0;previous_x=0;end
  for(integer lane=0;lane<16;lane=lane+1) begin
   raw=$signed(dut.sim_bd_i.axis_awg_tuning_v1_5.area_samples[16*lane+:16]);
   if(dut.sim_bd_i.axis_awg_tuning_v1_5.rc_enabled && dut.sim_bd_i.axis_awg_tuning_v1_5.area_valid)
    integral=integral+72'(raw+previous_x)*$signed({1'b0,dut.sim_bd_i.axis_awg_tuning_v1_5.rc_coefficient});
   if(dut.sim_bd_i.axis_awg_tuning_v1_5.area_valid)previous_x=raw;
   v=(72'(raw)<<<48)+integral;
   rounded=(v+(72'sd1<<49))>>>50;
   if(rounded>8191 || rounded< -8192) $fatal(1,"Unexpected AWG clipping ch=1");
   expected[0][16*lane+:16]=dut.sim_bd_i.axis_awg_tuning_v1_5.rc_enabled ? 16'(rounded*4) : 16'(raw);
  end
  qhistory[0]=integral;
  #0.001;
  if(cycle>30) begin
   if(dut.sim_bd_i.axis_awg_tuning_v1_5.m_axis_tdata!==expected[10] || dut.sim_bd_i.axis_awg_tuning_v1_5.GEN_RC.rc.integral!==qhistory[8])
    $fatal(1,"Exact AWG recurrence mismatch ch=1 cycle=%0d",cycle);
   samples=samples+16;
  end
 end
 final $display("EXACT_AWG_RESULT ch=1 samples=%0d",samples);
end

begin: RF_MONITOR
 logic [255:0] previous_word=0;
 wire [255:0] word=ext_axis_register_slice_0_m_axis_tdata;
 always @(posedge clk_300000000) if(resetn) begin
  if(dut.sim_bd_i.axis_signal_gen_v6_0.s1_axis_tvalid)
   $fwrite(rf_cmd_file,"%0d,%040h\n",cycle,dut.sim_bd_i.axis_signal_gen_v6_0.s1_axis_tdata);
  #0.002;
  if(cycle>100 && $isunknown(word)) $fatal(1,"Unknown RF output");
  if(cycle>100 && (word!=0 || previous_word!=0)) $fwrite(rf_file,"%0d,%064h\n",cycle,word);
  previous_word=word;
 end
end
endgenerate
awg_v2_raw_checker #(.CHANNEL(0)) raw_checker0 (
 .clk(clk_300000000),.rstn(resetn),.command_valid(dut.sim_bd_i.axis_awg_tuning_v1_4.s_axis_tvalid),
 .command(dut.sim_bd_i.axis_awg_tuning_v1_4.s_axis_tdata),.raw_samples(dut.sim_bd_i.axis_awg_tuning_v1_4.core_samples));
awg_v2_raw_checker #(.CHANNEL(1)) raw_checker1 (
 .clk(clk_300000000),.rstn(resetn),.command_valid(dut.sim_bd_i.axis_awg_tuning_v1_5.s_axis_tvalid),
 .command(dut.sim_bd_i.axis_awg_tuning_v1_5.s_axis_tdata),.raw_samples(dut.sim_bd_i.axis_awg_tuning_v1_5.core_samples));
// Real DDR capture IP driven by real tProcessor -> axis_set_reg GPIO.
// The FIR stream is a synthetic timestamp tag every 300 fabric clocks.
// This checks capture count/delay/queue behavior, not FIR arithmetic or ADC data.
logic ddr_armed=0;
integer ddr_file, ddr_accepts=0, ddr_matures=0, ddr_starts=0, ddr_samples=0;
integer accepted_at[0:8-1];
wire [127:0] timestamp_tag=128'(cycle);
tb_axis_buffer_ddr_sample_v3 #(.RUN_REGRESSION(0)) ddr_check();
initial begin
 force ddr_check.s_axis_aclk=clk_300000000;
 wait(resetn);
 ddr_check.reset_dut();
 ddr_check.arm_capture_delay(0, 4, 8, ((4+1)/2)*32, 8712);
 force ddr_check.trigger=ext_qick_vec2bit_0_dout5;
 force ddr_check.s_axis_tvalid=(cycle%300==0);
 force ddr_check.s_axis_tdata=timestamp_tag;
 ddr_file=$fopen({output_dir,"/ddr_capture.csv"},"w");
 $fwrite(ddr_file,"cycle,event,shot,sample,tag\n");
 ddr_armed=1;
end
always @(posedge clk_300000000) if(ddr_armed) begin
 if(ddr_check.dut.trigger_accept_s) begin
  if(ddr_accepts>=8) $fatal(1,"Too many DDR triggers");
  accepted_at[ddr_accepts]=cycle;
  $fwrite(ddr_file,"%0d,trigger,%0d,0,0\n",cycle,ddr_accepts);
  ddr_accepts=ddr_accepts+1;
 end
 if(ddr_check.dut.trigger_mature_s) begin
  if(cycle-accepted_at[ddr_matures]!=8712) $fatal(1,"DDR trigger delay mismatch");
  ddr_matures=ddr_matures+1;
 end
 if(ddr_check.dut.trigger_start_s) begin
  if(cycle-accepted_at[ddr_starts]<8712 || cycle-accepted_at[ddr_starts]>=8712+300)
   $fatal(1,"DDR first valid sample is outside delayed sample-grid boundary");
  $fwrite(ddr_file,"%0d,start,%0d,0,0\n",cycle,ddr_starts);
  ddr_starts=ddr_starts+1;
 end
 if(ddr_check.dut.output_fire_s) begin
  $fwrite(ddr_file,"%0d,sample,%0d,%0d,%0d\n",cycle,ddr_starts-1,
          ddr_check.dut.sample_count_s,ddr_check.s_axis_tdata);
  ddr_samples=ddr_samples+1;
 end
end
final begin
 $fclose(ddr_file);
 if(ddr_accepts!=8 || ddr_matures!=8 || ddr_starts!=8 || ddr_samples!=8*4)
  $fatal(1,"DDR counts accepts=%0d starts=%0d samples=%0d",ddr_accepts,ddr_starts,ddr_samples);
 if(ddr_check.errors || ddr_check.dut.overflow_s)
  $fatal(1,"DDR capture error or overflow");
 if(ddr_check.completed_count != 8*((4+1)/2))
  $fatal(1,"DDR AXI writes missing: %0d",ddr_check.completed_count);
 $display("FIR_DC_CAPTURE_RESULT triggers=%0d samples=%0d AXI_writes=%0d delay_cycles=8712",
          ddr_accepts,ddr_samples,ddr_check.completed_count);
end

generate

begin: AREA_CHECK_0
 logic [255:0] delayed_raw[5];
 logic signed [63:0] planned[0:7];
 logic [159:0] command;
 bit accepted;
 longint signed total=0, captured=0, magnitude=0, amp=0, q=0, r=0;
 longint start_cycle=-1, end_cycle=-1, zero_check=-1, cmd_cycle=-1;
 longint words=0, index=0, desired=0, remaining=0, expected_done=-1;
 longint samples=0, completed=0, latency_checks=0;
 integer fd,mode=0,sgn=0;
 logic [255:0] expected_word;
 initial begin
  for(integer i=0;i<5;i=i+1)delayed_raw[i]=0;
  $readmemh("F:/Vivado_Output/a3sim1/rc_precomp_repeat_reset_rf_duration_2x2_v4_final2_rf_duration_extend_output_sum_overlap_readout_awg_v3/planned_area_0.hex",planned);
  wait(resetn);
  fd=$fopen({output_dir,"/area_ch0.csv"},"w");
  if(!fd) $fatal(1,"Cannot open area evidence ch=0");
  $fwrite(fd,"shot,command_cycle,first_area_cycle,done_cycle,input_area,residual_area\n");
 end
 always @(posedge clk_300000000) if(resetn) begin
  for(integer i=4;i>0;i=i-1)delayed_raw[i]=delayed_raw[i-1];
  delayed_raw[0]=dut.sim_bd_i.axis_awg_tuning_v1_4.core_samples;
  command=dut.sim_bd_i.axis_awg_tuning_v1_4.s_axis_tdata;
  accepted=dut.sim_bd_i.axis_awg_tuning_v1_4.s_axis_tvalid && command[150] && !command[149] &&
           command[145:144]==3 && (command[147:146]==1 || command[147:146]==2);
  #0.002;
  if(dut.sim_bd_i.axis_awg_tuning_v1_4.area_fault || dut.sim_bd_i.axis_awg_tuning_v1_4.rc_clipped)
   $fatal(1,"AWG v3 area fault or RC clipping ch=0 cycle=%0d",cycle);
  expected_word=delayed_raw[4];
  if(cycle>=start_cycle && cycle<end_cycle && start_cycle>=0) begin
   for(integer lane=0;lane<16;lane=lane+1) begin
    index=(cycle-start_cycle)*16+lane;
    if(mode==2) desired=q+(index<r);
    else begin
     remaining=magnitude-index*amp;
     desired=remaining<=0 ? 0 : (remaining>=amp ? amp : remaining);
    end
    expected_word[16*lane+:16]=16'(sgn*desired*4);
   end
  end
  if(dut.sim_bd_i.axis_awg_tuning_v1_4.area_valid) begin
   if(dut.sim_bd_i.axis_awg_tuning_v1_4.area_samples!==expected_word)
    $fatal(1,"Area output mismatch ch=0 cycle=%0d actual=%h expected=%h",cycle,dut.sim_bd_i.axis_awg_tuning_v1_4.area_samples,expected_word);
   samples=samples+16;
   if(dut.sim_bd_i.axis_awg_tuning_v1_4.area_enabled)
    for(integer lane=0;lane<16;lane=lane+1)
     total=total+($signed(dut.sim_bd_i.axis_awg_tuning_v1_4.area_samples[16*lane+:16])>>>2);
  end
  if(accepted) begin
   if(completed>=8 || expected_done>=cycle)
    $fatal(1,"Unexpected overlapping compensation ch=0");
   captured=total;
   if(captured!==dut.sim_bd_i.axis_awg_tuning_v1_4.area_sum || captured!==planned[completed])
    $fatal(1,"Collected area differs from GUI ledger ch=0 shot=%0d actual=%0d IP=%0d plan=%0d",completed,captured,dut.sim_bd_i.axis_awg_tuning_v1_4.area_sum,planned[completed]);
   magnitude=captured<0 ? -captured : captured;
   sgn=captured<0 ? 1 : -1; mode=command[147:146];
   amp=command[15:2];
   if(mode==2) begin
    words=command[95:64]; q=magnitude/(words*16); r=magnitude%(words*16);
   end else words=magnitude==0 ? 1 : (magnitude+amp*16-1)/(amp*16);
   cmd_cycle=cycle; start_cycle=cycle+17; end_cycle=start_cycle+words;
   expected_done=end_cycle+1;
  end
  if(dut.sim_bd_i.axis_awg_tuning_v1_4.area_done || cycle==expected_done) begin
   if(!dut.sim_bd_i.axis_awg_tuning_v1_4.area_done || cycle!=expected_done || total!=0 || dut.sim_bd_i.axis_awg_tuning_v1_4.area_sum!=0)
    $fatal(1,"DC completion/residual mismatch ch=0 cycle=%0d expected=%0d total=%0d",cycle,expected_done,total);
   $fwrite(fd,"%0d,%0d,%0d,%0d,%0d,%0d\n",completed,cmd_cycle,start_cycle,cycle,captured,total);
   completed=completed+1; zero_check=cycle+12;
  end
  if(cycle==zero_check) begin
   if(dut.sim_bd_i.axis_awg_tuning_v1_4.m_axis_tdata!==0 || dut.sim_bd_i.axis_awg_tuning_v1_4.GEN_RC.rc.integral!==0 || dut.sim_bd_i.axis_awg_tuning_v1_4.area_sum!==0)
    $fatal(1,"DC/IIR histories not zero ch=0");
   latency_checks=latency_checks+1;
  end
 end
 final begin
  $fclose(fd);
  if(completed!=8 || latency_checks!=8)
   $fatal(1,"Missing DC shots/reset checks ch=0 completed=%0d checks=%0d",completed,latency_checks);
  $display("AREA_V3_RESULT ch=0 shots=%0d samples=%0d reset_checks=%0d residual=0",completed,samples,latency_checks);
 end
end
endgenerate
generate

begin: AREA_CHECK_1
 logic [255:0] delayed_raw[5];
 logic signed [63:0] planned[0:7];
 logic [159:0] command;
 bit accepted;
 longint signed total=0, captured=0, magnitude=0, amp=0, q=0, r=0;
 longint start_cycle=-1, end_cycle=-1, zero_check=-1, cmd_cycle=-1;
 longint words=0, index=0, desired=0, remaining=0, expected_done=-1;
 longint samples=0, completed=0, latency_checks=0;
 integer fd,mode=0,sgn=0;
 logic [255:0] expected_word;
 initial begin
  for(integer i=0;i<5;i=i+1)delayed_raw[i]=0;
  $readmemh("F:/Vivado_Output/a3sim1/rc_precomp_repeat_reset_rf_duration_2x2_v4_final2_rf_duration_extend_output_sum_overlap_readout_awg_v3/planned_area_1.hex",planned);
  wait(resetn);
  fd=$fopen({output_dir,"/area_ch1.csv"},"w");
  if(!fd) $fatal(1,"Cannot open area evidence ch=1");
  $fwrite(fd,"shot,command_cycle,first_area_cycle,done_cycle,input_area,residual_area\n");
 end
 always @(posedge clk_300000000) if(resetn) begin
  for(integer i=4;i>0;i=i-1)delayed_raw[i]=delayed_raw[i-1];
  delayed_raw[0]=dut.sim_bd_i.axis_awg_tuning_v1_5.core_samples;
  command=dut.sim_bd_i.axis_awg_tuning_v1_5.s_axis_tdata;
  accepted=dut.sim_bd_i.axis_awg_tuning_v1_5.s_axis_tvalid && command[150] && !command[149] &&
           command[145:144]==3 && (command[147:146]==1 || command[147:146]==2);
  #0.002;
  if(dut.sim_bd_i.axis_awg_tuning_v1_5.area_fault || dut.sim_bd_i.axis_awg_tuning_v1_5.rc_clipped)
   $fatal(1,"AWG v3 area fault or RC clipping ch=1 cycle=%0d",cycle);
  expected_word=delayed_raw[4];
  if(cycle>=start_cycle && cycle<end_cycle && start_cycle>=0) begin
   for(integer lane=0;lane<16;lane=lane+1) begin
    index=(cycle-start_cycle)*16+lane;
    if(mode==2) desired=q+(index<r);
    else begin
     remaining=magnitude-index*amp;
     desired=remaining<=0 ? 0 : (remaining>=amp ? amp : remaining);
    end
    expected_word[16*lane+:16]=16'(sgn*desired*4);
   end
  end
  if(dut.sim_bd_i.axis_awg_tuning_v1_5.area_valid) begin
   if(dut.sim_bd_i.axis_awg_tuning_v1_5.area_samples!==expected_word)
    $fatal(1,"Area output mismatch ch=1 cycle=%0d actual=%h expected=%h",cycle,dut.sim_bd_i.axis_awg_tuning_v1_5.area_samples,expected_word);
   samples=samples+16;
   if(dut.sim_bd_i.axis_awg_tuning_v1_5.area_enabled)
    for(integer lane=0;lane<16;lane=lane+1)
     total=total+($signed(dut.sim_bd_i.axis_awg_tuning_v1_5.area_samples[16*lane+:16])>>>2);
  end
  if(accepted) begin
   if(completed>=8 || expected_done>=cycle)
    $fatal(1,"Unexpected overlapping compensation ch=1");
   captured=total;
   if(captured!==dut.sim_bd_i.axis_awg_tuning_v1_5.area_sum || captured!==planned[completed])
    $fatal(1,"Collected area differs from GUI ledger ch=1 shot=%0d actual=%0d IP=%0d plan=%0d",completed,captured,dut.sim_bd_i.axis_awg_tuning_v1_5.area_sum,planned[completed]);
   magnitude=captured<0 ? -captured : captured;
   sgn=captured<0 ? 1 : -1; mode=command[147:146];
   amp=command[15:2];
   if(mode==2) begin
    words=command[95:64]; q=magnitude/(words*16); r=magnitude%(words*16);
   end else words=magnitude==0 ? 1 : (magnitude+amp*16-1)/(amp*16);
   cmd_cycle=cycle; start_cycle=cycle+17; end_cycle=start_cycle+words;
   expected_done=end_cycle+1;
  end
  if(dut.sim_bd_i.axis_awg_tuning_v1_5.area_done || cycle==expected_done) begin
   if(!dut.sim_bd_i.axis_awg_tuning_v1_5.area_done || cycle!=expected_done || total!=0 || dut.sim_bd_i.axis_awg_tuning_v1_5.area_sum!=0)
    $fatal(1,"DC completion/residual mismatch ch=1 cycle=%0d expected=%0d total=%0d",cycle,expected_done,total);
   $fwrite(fd,"%0d,%0d,%0d,%0d,%0d,%0d\n",completed,cmd_cycle,start_cycle,cycle,captured,total);
   completed=completed+1; zero_check=cycle+12;
  end
  if(cycle==zero_check) begin
   if(dut.sim_bd_i.axis_awg_tuning_v1_5.m_axis_tdata!==0 || dut.sim_bd_i.axis_awg_tuning_v1_5.GEN_RC.rc.integral!==0 || dut.sim_bd_i.axis_awg_tuning_v1_5.area_sum!==0)
    $fatal(1,"DC/IIR histories not zero ch=1");
   latency_checks=latency_checks+1;
  end
 end
 final begin
  $fclose(fd);
  if(completed!=8 || latency_checks!=8)
   $fatal(1,"Missing DC shots/reset checks ch=1 completed=%0d checks=%0d",completed,latency_checks);
  $display("AREA_V3_RESULT ch=1 shots=%0d samples=%0d reset_checks=%0d residual=0",completed,samples,latency_checks);
 end
end
endgenerate

integer sum_checks_4=0;
logic [255:0] sum_expected_4=0;
always @(posedge clk_300000000) begin: SUM_ORACLE_4
 integer total,code;
 logic [255:0] next_expected;
 if(!resetn) sum_expected_4=0;
 else begin
  for(integer lane=0;lane<16;lane=lane+1) begin
   total=(dut.sim_bd_i.sum_4.s0_axis_tvalid ? $signed(dut.sim_bd_i.sum_4.s0_axis_tdata[lane*16+:16]) : 0)
        +(dut.sim_bd_i.sum_4.s1_axis_tvalid ? $signed(dut.sim_bd_i.sum_4.s1_axis_tdata[lane*16+:16]) : 0);
   if(total>32764)code=32764; else if(total< -32768)code=-32768;
   else code=((total+2)>>>2)*4;
   next_expected[lane*16+:16]=16'(code);
  end
  #0.003;
  if(cycle>20 && dut.sim_bd_i.sum_4.m_axis_tdata!==sum_expected_4)
   $fatal(1,"v4 SUM mismatch suffix=4 cycle=%0d",cycle);
  sum_checks_4=sum_checks_4+16;
  sum_expected_4=next_expected;
 end
end
final $display("OUTPUT_SUM_RESULT suffix=4 samples=%0d",sum_checks_4);


integer sum_checks_5=0;
logic [255:0] sum_expected_5=0;
always @(posedge clk_300000000) begin: SUM_ORACLE_5
 integer total,code;
 logic [255:0] next_expected;
 if(!resetn) sum_expected_5=0;
 else begin
  for(integer lane=0;lane<16;lane=lane+1) begin
   total=(dut.sim_bd_i.sum_5.s0_axis_tvalid ? $signed(dut.sim_bd_i.sum_5.s0_axis_tdata[lane*16+:16]) : 0)
        +(dut.sim_bd_i.sum_5.s1_axis_tvalid ? $signed(dut.sim_bd_i.sum_5.s1_axis_tdata[lane*16+:16]) : 0);
   if(total>32764)code=32764; else if(total< -32768)code=-32768;
   else code=((total+2)>>>2)*4;
   next_expected[lane*16+:16]=16'(code);
  end
  #0.003;
  if(cycle>20 && dut.sim_bd_i.sum_5.m_axis_tdata!==sum_expected_5)
   $fatal(1,"v4 SUM mismatch suffix=5 cycle=%0d",cycle);
  sum_checks_5=sum_checks_5+16;
  sum_expected_5=next_expected;
 end
end
final $display("OUTPUT_SUM_RESULT suffix=5 samples=%0d",sum_checks_5);


integer sum_checks_6=0;
logic [255:0] sum_expected_6=0;
always @(posedge clk_300000000) begin: SUM_ORACLE_6
 integer total,code;
 logic [255:0] next_expected;
 if(!resetn) sum_expected_6=0;
 else begin
  for(integer lane=0;lane<16;lane=lane+1) begin
   total=(dut.sim_bd_i.sum_6.s0_axis_tvalid ? $signed(dut.sim_bd_i.sum_6.s0_axis_tdata[lane*16+:16]) : 0)
        +(dut.sim_bd_i.sum_6.s1_axis_tvalid ? $signed(dut.sim_bd_i.sum_6.s1_axis_tdata[lane*16+:16]) : 0);
   if(total>32764)code=32764; else if(total< -32768)code=-32768;
   else code=((total+2)>>>2)*4;
   next_expected[lane*16+:16]=16'(code);
  end
  #0.003;
  if(cycle>20 && dut.sim_bd_i.sum_6.m_axis_tdata!==sum_expected_6)
   $fatal(1,"v4 SUM mismatch suffix=6 cycle=%0d",cycle);
  sum_checks_6=sum_checks_6+16;
  sum_expected_6=next_expected;
 end
end
final $display("OUTPUT_SUM_RESULT suffix=6 samples=%0d",sum_checks_6);


always @(posedge clk_300000000) if(resetn && dut.sim_bd_i.axis_tproc64x32_x8_0.m3_axis_tvalid)
 $fwrite(events_file,"%0d,%0d,2,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m3_axis_tdata);


integer sum_trace_4,sum_edges_4;
logic [255:0] sum_last_awg_4=0,sum_last_rf_4=0;
initial begin
 if(!$value$plusargs("OUT=%s",output_dir)) $fatal(1,"Missing OUT");
 sum_trace_4=$fopen({output_dir,"/sum_alignment_4.csv"},"w");
 sum_edges_4=$fopen({output_dir,"/sum_edges_4.csv"},"w");
 $fwrite(sum_trace_4,"cycle,awg,rf,sum\n");
 $fwrite(sum_edges_4,"cycle,stream,edge\n");
end
always @(posedge clk_300000000) if(resetn) begin
 #0.004;
 if(cycle<12000 && (dut.sim_bd_i.sum_4.s0_axis_tdata!=sum_last_awg_4 || dut.sim_bd_i.sum_4.s1_axis_tdata!=sum_last_rf_4))
  $fwrite(sum_trace_4,"%0d,%064h,%064h,%064h\n",cycle,dut.sim_bd_i.sum_4.s0_axis_tdata,dut.sim_bd_i.sum_4.s1_axis_tdata,dut.sim_bd_i.sum_4.m_axis_tdata);
 if((dut.sim_bd_i.sum_4.s0_axis_tdata!=0)!=(sum_last_awg_4!=0))
  $fwrite(sum_edges_4,"%0d,awg,%0d\n",cycle,dut.sim_bd_i.sum_4.s0_axis_tdata!=0);
 if((dut.sim_bd_i.sum_4.s1_axis_tdata!=0)!=(sum_last_rf_4!=0))
  $fwrite(sum_edges_4,"%0d,rf,%0d\n",cycle,dut.sim_bd_i.sum_4.s1_axis_tdata!=0);
 sum_last_awg_4=dut.sim_bd_i.sum_4.s0_axis_tdata;
 sum_last_rf_4=dut.sim_bd_i.sum_4.s1_axis_tdata;
end
final begin $fclose(sum_trace_4);$fclose(sum_edges_4);end


integer sum_trace_5,sum_edges_5;
logic [255:0] sum_last_awg_5=0,sum_last_rf_5=0;
initial begin
 if(!$value$plusargs("OUT=%s",output_dir)) $fatal(1,"Missing OUT");
 sum_trace_5=$fopen({output_dir,"/sum_alignment_5.csv"},"w");
 sum_edges_5=$fopen({output_dir,"/sum_edges_5.csv"},"w");
 $fwrite(sum_trace_5,"cycle,awg,rf,sum\n");
 $fwrite(sum_edges_5,"cycle,stream,edge\n");
end
always @(posedge clk_300000000) if(resetn) begin
 #0.004;
 if(cycle<12000 && (dut.sim_bd_i.sum_5.s0_axis_tdata!=sum_last_awg_5 || dut.sim_bd_i.sum_5.s1_axis_tdata!=sum_last_rf_5))
  $fwrite(sum_trace_5,"%0d,%064h,%064h,%064h\n",cycle,dut.sim_bd_i.sum_5.s0_axis_tdata,dut.sim_bd_i.sum_5.s1_axis_tdata,dut.sim_bd_i.sum_5.m_axis_tdata);
 if((dut.sim_bd_i.sum_5.s0_axis_tdata!=0)!=(sum_last_awg_5!=0))
  $fwrite(sum_edges_5,"%0d,awg,%0d\n",cycle,dut.sim_bd_i.sum_5.s0_axis_tdata!=0);
 if((dut.sim_bd_i.sum_5.s1_axis_tdata!=0)!=(sum_last_rf_5!=0))
  $fwrite(sum_edges_5,"%0d,rf,%0d\n",cycle,dut.sim_bd_i.sum_5.s1_axis_tdata!=0);
 sum_last_awg_5=dut.sim_bd_i.sum_5.s0_axis_tdata;
 sum_last_rf_5=dut.sim_bd_i.sum_5.s1_axis_tdata;
end
final begin $fclose(sum_trace_5);$fclose(sum_edges_5);end


integer sum_trace_6,sum_edges_6;
logic [255:0] sum_last_awg_6=0,sum_last_rf_6=0;
initial begin
 if(!$value$plusargs("OUT=%s",output_dir)) $fatal(1,"Missing OUT");
 sum_trace_6=$fopen({output_dir,"/sum_alignment_6.csv"},"w");
 sum_edges_6=$fopen({output_dir,"/sum_edges_6.csv"},"w");
 $fwrite(sum_trace_6,"cycle,awg,rf,sum\n");
 $fwrite(sum_edges_6,"cycle,stream,edge\n");
end
always @(posedge clk_300000000) if(resetn) begin
 #0.004;
 if(cycle<12000 && (dut.sim_bd_i.sum_6.s0_axis_tdata!=sum_last_awg_6 || dut.sim_bd_i.sum_6.s1_axis_tdata!=sum_last_rf_6))
  $fwrite(sum_trace_6,"%0d,%064h,%064h,%064h\n",cycle,dut.sim_bd_i.sum_6.s0_axis_tdata,dut.sim_bd_i.sum_6.s1_axis_tdata,dut.sim_bd_i.sum_6.m_axis_tdata);
 if((dut.sim_bd_i.sum_6.s0_axis_tdata!=0)!=(sum_last_awg_6!=0))
  $fwrite(sum_edges_6,"%0d,awg,%0d\n",cycle,dut.sim_bd_i.sum_6.s0_axis_tdata!=0);
 if((dut.sim_bd_i.sum_6.s1_axis_tdata!=0)!=(sum_last_rf_6!=0))
  $fwrite(sum_edges_6,"%0d,rf,%0d\n",cycle,dut.sim_bd_i.sum_6.s1_axis_tdata!=0);
 sum_last_awg_6=dut.sim_bd_i.sum_6.s0_axis_tdata;
 sum_last_rf_6=dut.sim_bd_i.sum_6.s1_axis_tdata;
end
final begin $fclose(sum_trace_6);$fclose(sum_edges_6);end

awg_v2_raw_checker #(.CHANNEL(3)) raw_checker3 (
 .clk(clk_300000000),.rstn(resetn),.command_valid(dut.sim_bd_i.axis_awg_tuning_v1_6.s_axis_tvalid),
 .command(dut.sim_bd_i.axis_awg_tuning_v1_6.s_axis_tdata),.raw_samples(dut.sim_bd_i.axis_awg_tuning_v1_6.core_samples));
generate

begin: AREA_CHECK_3
 logic [255:0] delayed_raw[5];
 logic signed [63:0] planned[0:7];
 logic [159:0] command;
 bit accepted;
 longint signed total=0, captured=0, magnitude=0, amp=0, q=0, r=0;
 longint start_cycle=-1, end_cycle=-1, zero_check=-1, cmd_cycle=-1;
 longint words=0, index=0, desired=0, remaining=0, expected_done=-1;
 longint samples=0, completed=0, latency_checks=0;
 integer fd,mode=0,sgn=0;
 logic [255:0] expected_word;
 initial begin
  for(integer i=0;i<5;i=i+1)delayed_raw[i]=0;
  $readmemh("F:/Vivado_Output/a3sim1/rc_precomp_repeat_reset_rf_duration_2x2_v4_final2_rf_duration_extend_output_sum_overlap_readout_awg_v3/planned_area_3.hex",planned);
  wait(resetn);
  fd=$fopen({output_dir,"/area_ch3.csv"},"w");
  if(!fd) $fatal(1,"Cannot open area evidence ch=3");
  $fwrite(fd,"shot,command_cycle,first_area_cycle,done_cycle,input_area,residual_area\n");
 end
 always @(posedge clk_300000000) if(resetn) begin
  for(integer i=4;i>0;i=i-1)delayed_raw[i]=delayed_raw[i-1];
  delayed_raw[0]=dut.sim_bd_i.axis_awg_tuning_v1_6.core_samples;
  command=dut.sim_bd_i.axis_awg_tuning_v1_6.s_axis_tdata;
  accepted=dut.sim_bd_i.axis_awg_tuning_v1_6.s_axis_tvalid && command[150] && !command[149] &&
           command[145:144]==3 && (command[147:146]==1 || command[147:146]==2);
  #0.002;
  if(dut.sim_bd_i.axis_awg_tuning_v1_6.area_fault || dut.sim_bd_i.axis_awg_tuning_v1_6.rc_clipped)
   $fatal(1,"AWG v3 area fault or RC clipping ch=3 cycle=%0d",cycle);
  expected_word=delayed_raw[4];
  if(cycle>=start_cycle && cycle<end_cycle && start_cycle>=0) begin
   for(integer lane=0;lane<16;lane=lane+1) begin
    index=(cycle-start_cycle)*16+lane;
    if(mode==2) desired=q+(index<r);
    else begin
     remaining=magnitude-index*amp;
     desired=remaining<=0 ? 0 : (remaining>=amp ? amp : remaining);
    end
    expected_word[16*lane+:16]=16'(sgn*desired*4);
   end
  end
  if(dut.sim_bd_i.axis_awg_tuning_v1_6.area_valid) begin
   if(dut.sim_bd_i.axis_awg_tuning_v1_6.area_samples!==expected_word)
    $fatal(1,"Area output mismatch ch=3 cycle=%0d actual=%h expected=%h",cycle,dut.sim_bd_i.axis_awg_tuning_v1_6.area_samples,expected_word);
   samples=samples+16;
   if(dut.sim_bd_i.axis_awg_tuning_v1_6.area_enabled)
    for(integer lane=0;lane<16;lane=lane+1)
     total=total+($signed(dut.sim_bd_i.axis_awg_tuning_v1_6.area_samples[16*lane+:16])>>>2);
  end
  if(accepted) begin
   if(completed>=8 || expected_done>=cycle)
    $fatal(1,"Unexpected overlapping compensation ch=3");
   captured=total;
   if(captured!==dut.sim_bd_i.axis_awg_tuning_v1_6.area_sum || captured!==planned[completed])
    $fatal(1,"Collected area differs from GUI ledger ch=3 shot=%0d actual=%0d IP=%0d plan=%0d",completed,captured,dut.sim_bd_i.axis_awg_tuning_v1_6.area_sum,planned[completed]);
   magnitude=captured<0 ? -captured : captured;
   sgn=captured<0 ? 1 : -1; mode=command[147:146];
   amp=command[15:2];
   if(mode==2) begin
    words=command[95:64]; q=magnitude/(words*16); r=magnitude%(words*16);
   end else words=magnitude==0 ? 1 : (magnitude+amp*16-1)/(amp*16);
   cmd_cycle=cycle; start_cycle=cycle+17; end_cycle=start_cycle+words;
   expected_done=end_cycle+1;
  end
  if(dut.sim_bd_i.axis_awg_tuning_v1_6.area_done || cycle==expected_done) begin
   if(!dut.sim_bd_i.axis_awg_tuning_v1_6.area_done || cycle!=expected_done || total!=0 || dut.sim_bd_i.axis_awg_tuning_v1_6.area_sum!=0)
    $fatal(1,"DC completion/residual mismatch ch=3 cycle=%0d expected=%0d total=%0d",cycle,expected_done,total);
   $fwrite(fd,"%0d,%0d,%0d,%0d,%0d,%0d\n",completed,cmd_cycle,start_cycle,cycle,captured,total);
   completed=completed+1; zero_check=cycle+12;
  end
  if(cycle==zero_check) begin
   if(dut.sim_bd_i.axis_awg_tuning_v1_6.m_axis_tdata!==0 || dut.sim_bd_i.axis_awg_tuning_v1_6.GEN_RC.rc.integral!==0 || dut.sim_bd_i.axis_awg_tuning_v1_6.area_sum!==0)
    $fatal(1,"DC/IIR histories not zero ch=3");
   latency_checks=latency_checks+1;
  end
 end
 final begin
  $fclose(fd);
  if(completed!=8 || latency_checks!=8)
   $fatal(1,"Missing DC shots/reset checks ch=3 completed=%0d checks=%0d",completed,latency_checks);
  $display("AREA_V3_RESULT ch=3 shots=%0d samples=%0d reset_checks=%0d residual=0",completed,samples,latency_checks);
 end
end
endgenerate

endmodule
