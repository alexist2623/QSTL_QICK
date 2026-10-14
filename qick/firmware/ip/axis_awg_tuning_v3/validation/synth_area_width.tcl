# Run only after the RTL width/error comparison has completed.
# Out-of-context resource/timing comparison; not a production bitstream build.
if {$argc != 2} { error "Usage: -tclargs WIDTH FRESH_OUTPUT_DIRECTORY" }
set width [lindex $argv 0]
if {$width ni {32 48 64}} { error "Width must be 32, 48 or 64" }
set build [file normalize [lindex $argv 1]]
if {[file exists $build] && [llength [glob -nocomplain -directory $build *]]} {
    error "Refusing to overwrite existing synthesis evidence: $build"
}
file mkdir $build
set source [file normalize [file join [file dirname [info script]] .. src v3_awg_dc_area.sv]]
set_param general.maxThreads 2
create_project -in_memory -part xczu49dr-ffvf1760-2-e
read_verilog -sv $source
set constraint_file [file join $build area_timing.xdc]
set constraints [open $constraint_file w]
puts $constraints {
create_clock -name fabric -period 3.333 [get_ports clk]
set data_inputs [get_ports -filter {DIRECTION == IN && NAME != clk && NAME != rstn}]
set_input_delay -clock fabric 0.0 $data_inputs
set_output_delay -clock fabric 0.0 [all_outputs]
# rstn is a reset control, not a fabric-cycle data input in this arithmetic test.
set_false_path -from [get_ports rstn]
}
close $constraints
read_xdc $constraint_file
synth_design -top v3_awg_dc_area -mode out_of_context -flatten_hierarchy rebuilt -generic AREA_WIDTH=$width
report_utilization -file [file join $build utilization_synth.rpt]
write_checkpoint -force [file join $build synthesized.dcp]
opt_design
place_design
phys_opt_design
route_design
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -file [file join $build timing_summary.rpt]
report_timing -max_paths 20 -delay_type max -file [file join $build setup_paths.rpt]
report_timing -max_paths 20 -delay_type min -file [file join $build hold_paths.rpt]
report_timing -from [all_registers] -to [all_registers] -max_paths 20 -delay_type max -file [file join $build internal_setup_paths.rpt]
report_timing -from [all_registers] -to [all_registers] -max_paths 20 -delay_type min -file [file join $build internal_hold_paths.rpt]
report_utilization -file [file join $build utilization_routed.rpt]
report_drc -file [file join $build drc.rpt]
write_checkpoint -force [file join $build routed.dcp]
set setup_path [get_timing_paths -delay_type max -max_paths 1]
set hold_path [get_timing_paths -delay_type min -max_paths 1]
set fp [open [file join $build result.txt] w]
puts $fp "area_width=$width"
puts $fp "source=$source"
puts $fp "scope=area_engine_only_out_of_context"
puts $fp "period_ns=3.333"
puts $fp "wns_ns=[get_property SLACK $setup_path]"
puts $fp "whs_ns=[get_property SLACK $hold_path]"
puts $fp "internal_wns_ns=[get_property SLACK [get_timing_paths -from [all_registers] -to [all_registers] -delay_type max -max_paths 1]]"
puts $fp "internal_whs_ns=[get_property SLACK [get_timing_paths -from [all_registers] -to [all_registers] -delay_type min -max_paths 1]]"
close $fp
exit
