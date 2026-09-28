# Recover interrupted synthesis workers after a host shutdown. No live Vivado
# workers may be using this project when this entry point is invoked.
set script_dir [file dirname [file normalize [info script]]]
set repo_dir [file normalize [file join $script_dir .. .. .. ..]]
set project_name qstl_awg_v2
set jobs 5
if {$argc != 1} {error "Pass the existing build directory"}
set output_dir [file normalize [lindex $argv 0]]
if {![string match "2023.1*" [version -short]]} {error "Vivado 2023.1 required"}
set_param general.maxThreads $jobs
open_project [file join $output_dir ${project_name}.xpr]
set status_file [open [file join $output_dir recovery_run_status.txt] w]
foreach run [get_runs] {
 puts $status_file "[get_property NAME $run]: [get_property STATUS $run]"
}
close $status_file
set unfinished {}
foreach run [get_runs -filter {IS_SYNTHESIS == 1}] {
 set run_status [get_property STATUS $run]
 if {[string first "Complete" $run_status] < 0 && $run_status ne "Using cached IP results"} {
  lappend unfinished $run
 }
}
foreach run $unfinished {
  puts "RECOVER_RESET=[get_property NAME $run]"
  reset_run $run
  set_property STEPS.SYNTH_DESIGN.TCL.PRE [file join $script_dir single_thread_synthesis.tcl] $run
}
set source_file [open [file join $script_dir build_vivado_2023_1.tcl] r]
set original [read $source_file]
close $source_file
set tail_start [string first {set_property strategy {Vivado Synthesis Defaults} [get_runs synth_1]} $original]
if {$tail_start < 0} {error "Build continuation section not found"}
# Use the identical synthesis, implementation and publication checks.
eval [string range $original $tail_start end]
