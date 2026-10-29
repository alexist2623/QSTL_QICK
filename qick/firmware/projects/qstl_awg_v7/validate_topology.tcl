# Validate the actual elaborated BD before synthesis, not just its source text.
proc require_intf_link {first second} {
    set first_pin [get_bd_intf_pins $first]
    set second_pin [get_bd_intf_pins $second]
    set first_net [get_bd_intf_nets -of_objects $first_pin]
    set second_net [get_bd_intf_nets -of_objects $second_pin]
    if {[llength $first_pin] != 1 || [llength $second_pin] != 1 ||
        [llength $first_net] != 1 || $first_net ne $second_net} {
        error "Topology mismatch: $first -> $second"
    }
}
proc require_pin_link {first second} {
    set first_pin [get_bd_pins $first]
    set second_pin [get_bd_pins $second]
    set first_net [get_bd_nets -of_objects $first_pin]
    set second_net [get_bd_nets -of_objects $second_pin]
    if {[llength $first_pin] != 1 || [llength $second_pin] != 1 ||
        [llength $first_net] != 1 || $first_net ne $second_net} {
        error "Topology mismatch: $first -> $second"
    }
}
proc require_config {cell name expected} {
    if {[get_property CONFIG.$name [get_bd_cells $cell]] ne $expected} {
        error "Topology parameter mismatch: $cell $name expected $expected"
    }
}
current_bd_instance /
if {[llength [get_bd_cells -hier -filter {VLNV == QICK:QICK:axis_awg_tuning_v7:1.0}]] != 3 ||
    [llength [get_bd_cells -hier -filter {VLNV == QSTL:User:axis_output_sum_v7:1.0}]] != 3} {
    error "Expected exactly three AWGs and three output sums"
}
foreach awg {8 9 10 11} {
    if {[llength [get_bd_cells -quiet axis_awg_tuning_v7_$awg]] != 0 ||
        [llength [get_bd_cells -quiet axis_output_sum_$awg]] != 0} {
        error "Removed AWG remains: DAC$awg"
    }
}
foreach slice {24 25 26 27} {
    if {[llength [get_bd_cells -quiet axis_register_slice_$slice]] != 0} {
        error "Removed command slice remains: $slice"
    }
}
foreach {awg slice rf dac command_slice tmux} {4 8 0 10 9 0 5 10 1 11 21 1 6 11 3 12 22 2} {
    set generator axis_awg_tuning_v7_$awg
    set sum axis_output_sum_$awg
    foreach {key value} {N_PTS 16 DC_AREA_BITS 48 EXTRA_Y_PIPE_STAGES 3 RC_PRECOMP_VERSION 1 DC_AREA_VERSION 1} {
        require_config $generator $key $value
    }
    foreach {key value} {N_PTS 16 PIPELINE_CYCLES 2 AWG_DELAY_CYCLES 2 BYPASS 0} {
        require_config $sum $key $value
    }
    require_intf_link axis_tmux_v1_$tmux/m1_axis axis_register_slice_$command_slice/S_AXIS
    require_intf_link axis_register_slice_$command_slice/M_AXIS $generator/s_axis
    require_intf_link $generator/m_axis $sum/s0_axis
    require_intf_link axis_signal_gen_v6_$rf/m_axis $sum/s1_axis
    require_intf_link $sum/m_axis axis_register_slice_$slice/s_axis
    require_intf_link axis_register_slice_$slice/M_AXIS usp_rf_data_converter_0/s${dac}_axis
    require_pin_link $generator/aclk $sum/aclk
    require_pin_link $generator/aresetn $sum/aresetn
}
require_config sum_zero_word CONST_WIDTH 256
require_config sum_zero_word CONST_VAL 0
require_config sum_one_valid CONST_VAL 1
foreach {slice dac} {13 20 14 21 15 22 16 23} {
    require_pin_link sum_zero_word/dout axis_register_slice_$slice/s_axis_tdata
    require_pin_link sum_one_valid/dout axis_register_slice_$slice/s_axis_tvalid
    require_intf_link axis_register_slice_$slice/M_AXIS usp_rf_data_converter_0/s${dac}_axis
}
require_intf_link axis_square_pulse_v1_0/m_axis axis_register_slice_12/s_axis
require_intf_link axis_register_slice_12/M_AXIS usp_rf_data_converter_0/s13_axis
foreach {tmux output readout} {4 0 0 5 0 1 6 1 2 6 3 3} {
    require_intf_link axis_tmux_v1_$tmux/m${output}_axis axis_dyn_readout_v1_$readout/s0_axis
}
require_config ps8_0_axi_periph NUM_MI 34
for {set i 0} {$i < 34} {incr i} {
    set master [format "ps8_0_axi_periph/M%02d_AXI" $i]
    set net [get_bd_intf_nets -of_objects [get_bd_intf_pins $master]]
    if {[llength $net] != 1 || [llength [get_bd_intf_pins -of_objects $net]] != 2} {
        error "Unconnected/ambiguous AXI master: $master"
    }
}
set review [open [file join $output_dir topology_review.txt] w]
puts $review "passed=true"
puts $review "awg_front_panel=4,5,6"
puts $review "square_front_panel=7"
puts $review "digital_zero_front_panel=8,9,10,11"
puts $review "awg_blocks=3"
puts $review "sum_blocks=3"
puts $review "axi_master_count=34"
puts $review "readout_tmux_mapping=unchanged"
puts $review "rf_alignment_awg_delay=2"
puts $review "rf_alignment_sum_pipeline=2"
puts $review "utc=[clock format [clock seconds] -gmt 1 -format {%Y-%m-%dT%H:%M:%SZ}]"
close $review
puts "V7_THREE_AWG_TOPOLOGY_PASS"
