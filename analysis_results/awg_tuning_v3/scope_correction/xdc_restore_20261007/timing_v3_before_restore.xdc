# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
# 300 MHz external CLK104 PL clock; rounded slightly down for timing analysis.
create_clock -name clk_104_pl -period 3.333 [get_ports CLK104_PL_CLK_P]
# The BD connects tProcessor, AWG, RF DDS, FIR, and DDR source stream to the
# same dac_clk_buf/BUFG_O net. Their data/trigger paths are synchronous and
# remain timed at 3.333 ns. The old clk_core cell and RFDC clk_adc2/clk_dac1
# output nets are absent/disconnected in this BD; they are not clock domains.
set clk_axi [get_clocks -of_objects [get_nets -of_objects [get_pins d_1_i/usp_rf_data_converter_0/s_axi_aclk]]]
set clk_ddr4 [get_clocks -of_objects [get_nets -of_objects [get_pins d_1_i/ddr4/ddr4_0/c0_ddr4_ui_clk]]]

# Keep the three existing asynchronous domain crossings: host AXI, common
# 300 MHz fabric, and DDR UI memory clock (internal async FIFO/CDC bridges).
set_clock_groups -name clk_axi_to_dac0 -asynchronous \
    -group $clk_axi -group [get_clocks clk_104_pl]
set_clock_groups -name clk_axi_to_ddr4 -asynchronous \
    -group $clk_axi -group $clk_ddr4
set_clock_groups -name clk_ddr4_to_clk104_pl -asynchronous \
    -group $clk_ddr4 -group [get_clocks clk_104_pl]

# Retain the existing common fabric reset exception.
set_false_path -through [get_pins d_1_i/rst_dac0/peripheral_aresetn[0]]
