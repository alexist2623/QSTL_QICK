// Generated boundary connections. See tb_body.svh for the test.
`timescale 1ns/1fs
module tb_gui;
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
sim_bd_wrapper dut (
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
always @(posedge clk_300000000) if (resetn && dut.sim_bd_i.axis_tproc64x32_x8_0.m1_axis_tvalid) begin
 $fwrite(events_file,"%0d,%0d,0,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m1_axis_tdata);
end
always @(posedge clk_300000000) if (resetn && dut.sim_bd_i.axis_tproc64x32_x8_0.m2_axis_tvalid) begin
 $fwrite(events_file,"%0d,%0d,1,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m2_axis_tdata);
end
always @(posedge clk_300000000) if (resetn && dut.sim_bd_i.axis_tproc64x32_x8_0.m3_axis_tvalid) begin
 $fwrite(events_file,"%0d,%0d,2,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m3_axis_tdata);
end
always @(posedge clk_300000000) if (resetn && dut.sim_bd_i.axis_tproc64x32_x8_0.m4_axis_tvalid) begin
 $fwrite(events_file,"%0d,%0d,3,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m4_axis_tdata);
end
always @(posedge clk_300000000) if (resetn && dut.sim_bd_i.axis_tproc64x32_x8_0.m5_axis_tvalid) begin
 $fwrite(events_file,"%0d,%0d,4,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m5_axis_tdata);
end
always @(posedge clk_300000000) if (resetn && dut.sim_bd_i.axis_tproc64x32_x8_0.m6_axis_tvalid) begin
 $fwrite(events_file,"%0d,%0d,5,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m6_axis_tdata);
end
always @(posedge clk_300000000) if (resetn && dut.sim_bd_i.axis_tproc64x32_x8_0.m7_axis_tvalid) begin
 $fwrite(events_file,"%0d,%0d,6,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m7_axis_tdata);
end
always @(posedge clk_300000000) if (resetn && dut.sim_bd_i.axis_tproc64x32_x8_0.m8_axis_tvalid) begin
 $fwrite(events_file,"%0d,%0d,7,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m8_axis_tdata);
end
always @(posedge clk_300000000) if (resetn && dut.sim_bd_i.axis_square_pulse_v1_0.s_axis_tvalid && dut.sim_bd_i.axis_square_pulse_v1_0.s_axis_tready)
 $fwrite(commands_file,"%0d,sqcmd,%040h\n",cycle,dut.sim_bd_i.axis_square_pulse_v1_0.s_axis_tdata);
always @(posedge clk_300000000) if (resetn && dut.sim_bd_i.axis_awg_tuning_v1_4.s_axis_tvalid && dut.sim_bd_i.axis_awg_tuning_v1_4.s_axis_tready)
 $fwrite(commands_file,"%0d,awgcmd,%040h\n",cycle,dut.sim_bd_i.axis_awg_tuning_v1_4.s_axis_tdata);
always @(posedge clk_300000000) if (resetn && dut.sim_bd_i.axis_signal_gen_v6_2.s1_axis_tvalid && dut.sim_bd_i.axis_signal_gen_v6_2.s1_axis_tready)
 $fwrite(commands_file,"%0d,rfcmd,%040h\n",cycle,dut.sim_bd_i.axis_signal_gen_v6_2.s1_axis_tdata);
`include "tb_body.svh"
endmodule
