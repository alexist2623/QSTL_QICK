# Combine the three retained AWGs with RF; removed DAC8..11 emit digital zero.
# Logical QICK RF gens 0/2/4 correspond to physical IP suffixes 0/1/3.
current_bd_instance /
set zero [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 sum_zero_word]
set_property -dict [list CONFIG.CONST_WIDTH {256} CONFIG.CONST_VAL {0}] $zero
set one_valid [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 sum_one_valid]
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {1}] $one_valid

foreach {awg suffix rf old_rf_slice} {4 8 0 0 5 10 1 1 6 11 3 3} {
    set sum [create_bd_cell -type ip -vlnv QSTL:User:axis_output_sum_v7:1.0 axis_output_sum_$awg]
    set_property -dict [list CONFIG.N_PTS {16} CONFIG.PIPELINE_CYCLES {2} CONFIG.AWG_DELAY_CYCLES {2} CONFIG.BYPASS [expr {$rf < 0}]] $sum
    set sink [get_bd_intf_pins axis_register_slice_$suffix/s_axis]
    disconnect_bd_intf_net [get_bd_intf_nets -of_objects $sink] $sink
    connect_bd_intf_net [get_bd_intf_pins axis_awg_tuning_v7_$awg/m_axis] [get_bd_intf_pins $sum/s0_axis]
    connect_bd_intf_net [get_bd_intf_pins $sum/m_axis] $sink
    if {$rf >= 0} {
        set old_sink [get_bd_intf_pins axis_register_slice_$old_rf_slice/s_axis]
        disconnect_bd_intf_net [get_bd_intf_nets -of_objects $old_sink] $old_sink
        connect_bd_intf_net [get_bd_intf_pins axis_signal_gen_v6_$rf/m_axis] [get_bd_intf_pins $sum/s1_axis]
        # These previous RF DAC inputs now emit zero; the source is routed to
        # exactly one DAC through the AWG sum. Do not leave sample buses floating.
        connect_bd_net [get_bd_pins $zero/dout] [get_bd_pins axis_register_slice_$old_rf_slice/s_axis_tdata]
        connect_bd_net [get_bd_pins $one_valid/dout] [get_bd_pins axis_register_slice_$old_rf_slice/s_axis_tvalid]
    }
    connect_bd_net [get_bd_pins axis_awg_tuning_v7_$awg/aclk] [get_bd_pins $sum/aclk]
    connect_bd_net [get_bd_pins axis_awg_tuning_v7_$awg/aresetn] [get_bd_pins $sum/aresetn]
}
foreach suffix {13 14 15 16} {
    connect_bd_net [get_bd_pins $zero/dout] [get_bd_pins axis_register_slice_$suffix/s_axis_tdata]
    connect_bd_net [get_bd_pins $one_valid/dout] [get_bd_pins axis_register_slice_$suffix/s_axis_tvalid]
}
validate_bd_design
save_bd_design
