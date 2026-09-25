set here [file dirname [file normalize [info script]]]
set output_dir [file normalize [lindex $argv 0]]
file mkdir $output_dir
cd $output_dir
set_param general.maxThreads 5
foreach prefix {awg square} {
    create_project -in_memory -part xczu49dr-ffvf1760-2-e
    if {$prefix eq "awg"} {set folder axis_awg_tuning_v1} else {set folder axis_square_pulse_v1}
    set sources [lsearch -all -inline -not -glob [glob [file join $here .. $folder src *.sv]] *tb_*]
    read_verilog -sv $sources
    synth_design -top $folder -part xczu49dr-ffvf1760-2-e -mode out_of_context
    create_clock -name dac_clk -period 3.333333 [get_ports aclk]
    create_clock -name axi_clk -period 10 [get_ports s_axi_aclk]
    set_clock_groups -asynchronous -group [get_clocks dac_clk] -group [get_clocks axi_clk]
    opt_design
    place_design
    phys_opt_design
    route_design
    report_timing_summary -file ${prefix}_timing.rpt
    report_utilization -file ${prefix}_utilization.rpt
    report_timing -max_paths 10 -file ${prefix}_paths.rpt
    write_checkpoint -force ${prefix}_routed.dcp
    close_project
}
exit 0
