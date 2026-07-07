# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
# QSTL AWG tuning simulation-only block design shell for Vivado 2023.1.
#
# The production qstl_awg_tuning design routes:
#   axis_tproc64x32_x8_0/m1_axis -> axis_tmux_v1_0/s_axis
#   axis_tmux_v1_0/m0_axis -> axis_signal_gen_v6_0/s1_axis
#   axis_signal_gen_v6_0/m_axis -> usp_rf_data_converter_0/s00_axis
#   axis_tmux_v1_0/m1_axis -> axis_awg_tuning_v1_4/s_axis
#   axis_awg_tuning_v1_4/m_axis -> usp_rf_data_converter_0/s10_axis
#
# This simulation project keeps a small BD shell for Vivado project validation
# and source organization. The BD wrapper contains the real packaged
# axis_signal_gen_v6_0 and axis_awg_tuning_v1_4 IPs so that RFDC-bound packed
# and x16 debug streams can be captured in batch simulation without modifying
# the production qstl_awg_tuning project.

set design_name qstl_awg_tuning_sim_bd

if {[catch {current_bd_design $design_name}]} {
  create_bd_design $design_name
} else {
  current_bd_design $design_name
}

set aclk [create_bd_port -dir I -type clk -freq_hz 100000000 aclk]
set_property CONFIG.FREQ_HZ 100000000 $aclk
set aresetn [create_bd_port -dir I -type rst aresetn]
set_property CONFIG.POLARITY ACTIVE_LOW $aresetn
set_property CONFIG.ASSOCIATED_RESET aresetn $aclk

create_bd_port -dir I -from 159 -to 0 awg_s_axis_tdata
create_bd_port -dir I awg_s_axis_tvalid
create_bd_port -dir O awg_s_axis_tready

create_bd_port -dir I -from 159 -to 0 siggen_s_axis_tdata
create_bd_port -dir I siggen_s_axis_tvalid
create_bd_port -dir O siggen_s_axis_tready

create_bd_port -dir O -from 255 -to 0 siggen_dac_axis_tdata
create_bd_port -dir O siggen_dac_axis_tvalid
create_bd_port -dir I siggen_dac_axis_tready

create_bd_port -dir O -from 255 -to 0 awg_dac_axis_tdata
create_bd_port -dir O awg_dac_axis_tvalid
create_bd_port -dir I awg_dac_axis_tready

set awg_cell [create_bd_cell -type ip -vlnv QICK:QICK:axis_awg_tuning_v1:1.0 axis_awg_tuning_v1_4]
set_property -dict [list CONFIG.N_PTS {16} CONFIG.B {16} CONFIG.FRAC {16} CONFIG.CMD_WIDTH {160}] $awg_cell
set siggen_cell [create_bd_cell -type ip -vlnv QICK:QICK:axis_signal_gen_v6:1.0 axis_signal_gen_v6_0]
set_property -dict [list CONFIG.N {10} CONFIG.N_DDS {16} CONFIG.GEN_DDS {TRUE} CONFIG.ENVELOPE_TYPE {COMPLEX}] $siggen_cell

set zero1 [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 zero1]
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {0}] $zero1
set one1 [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 one1]
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {1}] $one1
set zero3 [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 zero3]
set_property -dict [list CONFIG.CONST_WIDTH {3} CONFIG.CONST_VAL {0}] $zero3
set zero4 [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 zero4]
set_property -dict [list CONFIG.CONST_WIDTH {4} CONFIG.CONST_VAL {0}] $zero4
set zero6 [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 zero6]
set_property -dict [list CONFIG.CONST_WIDTH {6} CONFIG.CONST_VAL {0}] $zero6
set zero32 [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 zero32]
set_property -dict [list CONFIG.CONST_WIDTH {32} CONFIG.CONST_VAL {0}] $zero32

connect_bd_net [get_bd_ports aclk] [get_bd_pins axis_awg_tuning_v1_4/aclk]
connect_bd_net [get_bd_ports aresetn] [get_bd_pins axis_awg_tuning_v1_4/aresetn]
connect_bd_net [get_bd_ports aclk] [get_bd_pins axis_awg_tuning_v1_4/s_axi_aclk]
connect_bd_net [get_bd_ports aresetn] [get_bd_pins axis_awg_tuning_v1_4/s_axi_aresetn]
connect_bd_net [get_bd_ports awg_s_axis_tdata] [get_bd_pins axis_awg_tuning_v1_4/s_axis_tdata]
connect_bd_net [get_bd_ports awg_s_axis_tvalid] [get_bd_pins axis_awg_tuning_v1_4/s_axis_tvalid]
connect_bd_net [get_bd_pins axis_awg_tuning_v1_4/s_axis_tready] [get_bd_ports awg_s_axis_tready]
connect_bd_net [get_bd_pins axis_awg_tuning_v1_4/m_axis_tdata] [get_bd_ports awg_dac_axis_tdata]
connect_bd_net [get_bd_pins axis_awg_tuning_v1_4/m_axis_tvalid] [get_bd_ports awg_dac_axis_tvalid]
connect_bd_net [get_bd_ports awg_dac_axis_tready] [get_bd_pins axis_awg_tuning_v1_4/m_axis_tready]
connect_bd_net [get_bd_pins zero6/dout] [get_bd_pins axis_awg_tuning_v1_4/s_axi_awaddr]
connect_bd_net [get_bd_pins zero3/dout] [get_bd_pins axis_awg_tuning_v1_4/s_axi_awprot]
connect_bd_net [get_bd_pins zero1/dout] [get_bd_pins axis_awg_tuning_v1_4/s_axi_awvalid]
connect_bd_net [get_bd_pins zero32/dout] [get_bd_pins axis_awg_tuning_v1_4/s_axi_wdata]
connect_bd_net [get_bd_pins zero4/dout] [get_bd_pins axis_awg_tuning_v1_4/s_axi_wstrb]
connect_bd_net [get_bd_pins zero1/dout] [get_bd_pins axis_awg_tuning_v1_4/s_axi_wvalid]
connect_bd_net [get_bd_pins one1/dout] [get_bd_pins axis_awg_tuning_v1_4/s_axi_bready]
connect_bd_net [get_bd_pins zero6/dout] [get_bd_pins axis_awg_tuning_v1_4/s_axi_araddr]
connect_bd_net [get_bd_pins zero3/dout] [get_bd_pins axis_awg_tuning_v1_4/s_axi_arprot]
connect_bd_net [get_bd_pins zero1/dout] [get_bd_pins axis_awg_tuning_v1_4/s_axi_arvalid]
connect_bd_net [get_bd_pins one1/dout] [get_bd_pins axis_awg_tuning_v1_4/s_axi_rready]

connect_bd_net [get_bd_ports aclk] [get_bd_pins axis_signal_gen_v6_0/aclk]
connect_bd_net [get_bd_ports aresetn] [get_bd_pins axis_signal_gen_v6_0/aresetn]
connect_bd_net [get_bd_ports aclk] [get_bd_pins axis_signal_gen_v6_0/s_axi_aclk]
connect_bd_net [get_bd_ports aresetn] [get_bd_pins axis_signal_gen_v6_0/s_axi_aresetn]
connect_bd_net [get_bd_ports aclk] [get_bd_pins axis_signal_gen_v6_0/s0_axis_aclk]
connect_bd_net [get_bd_ports aresetn] [get_bd_pins axis_signal_gen_v6_0/s0_axis_aresetn]
connect_bd_net [get_bd_ports siggen_s_axis_tdata] [get_bd_pins axis_signal_gen_v6_0/s1_axis_tdata]
connect_bd_net [get_bd_ports siggen_s_axis_tvalid] [get_bd_pins axis_signal_gen_v6_0/s1_axis_tvalid]
connect_bd_net [get_bd_pins axis_signal_gen_v6_0/s1_axis_tready] [get_bd_ports siggen_s_axis_tready]
connect_bd_net [get_bd_pins axis_signal_gen_v6_0/m_axis_tdata] [get_bd_ports siggen_dac_axis_tdata]
connect_bd_net [get_bd_pins axis_signal_gen_v6_0/m_axis_tvalid] [get_bd_ports siggen_dac_axis_tvalid]
connect_bd_net [get_bd_ports siggen_dac_axis_tready] [get_bd_pins axis_signal_gen_v6_0/m_axis_tready]
connect_bd_net [get_bd_pins zero32/dout] [get_bd_pins axis_signal_gen_v6_0/s0_axis_tdata]
connect_bd_net [get_bd_pins zero1/dout] [get_bd_pins axis_signal_gen_v6_0/s0_axis_tvalid]
connect_bd_net [get_bd_pins zero6/dout] [get_bd_pins axis_signal_gen_v6_0/s_axi_awaddr]
connect_bd_net [get_bd_pins zero3/dout] [get_bd_pins axis_signal_gen_v6_0/s_axi_awprot]
connect_bd_net [get_bd_pins zero1/dout] [get_bd_pins axis_signal_gen_v6_0/s_axi_awvalid]
connect_bd_net [get_bd_pins zero32/dout] [get_bd_pins axis_signal_gen_v6_0/s_axi_wdata]
connect_bd_net [get_bd_pins zero4/dout] [get_bd_pins axis_signal_gen_v6_0/s_axi_wstrb]
connect_bd_net [get_bd_pins zero1/dout] [get_bd_pins axis_signal_gen_v6_0/s_axi_wvalid]
connect_bd_net [get_bd_pins one1/dout] [get_bd_pins axis_signal_gen_v6_0/s_axi_bready]
connect_bd_net [get_bd_pins zero6/dout] [get_bd_pins axis_signal_gen_v6_0/s_axi_araddr]
connect_bd_net [get_bd_pins zero3/dout] [get_bd_pins axis_signal_gen_v6_0/s_axi_arprot]
connect_bd_net [get_bd_pins zero1/dout] [get_bd_pins axis_signal_gen_v6_0/s_axi_arvalid]
connect_bd_net [get_bd_pins one1/dout] [get_bd_pins axis_signal_gen_v6_0/s_axi_rready]

validate_bd_design
save_bd_design
