# A separate simulation-only project; the production design is never modified.
set project_dir [file dirname [file normalize [info script]]]
set repo_dir [file normalize [file join $project_dir .. .. .. ..]]
if {$argc != 1} {error "Usage: vivado -mode batch -source proj.tcl -tclargs OUTPUT_DIR"}
set output_dir [file normalize [lindex $argv 0]]
if {[file exists $output_dir]} {error "Use a fresh output directory: $output_dir"}
create_project qstl_gui_rtl_sim $output_dir -part xczu49dr-ffvf1760-2-e
set_property target_language Verilog [current_project]
set_property simulator_language Mixed [current_project]
set_property enable_vhdl_2008 true [current_project]
set_property ip_repo_paths [file join $repo_dir qick firmware ip] [current_project]
update_ip_catalog
source [file join $project_dir design.tcl]
set bd [get_files sim_bd.bd]
generate_target all $bd
set wrappers [make_wrapper -files $bd -top]
add_files -norecurse $wrappers
set_property top sim_bd_wrapper [get_filesets sources_1]
update_compile_order -fileset sources_1
set f [open [file join $output_dir wrapper_path.txt] w]
puts $f [lindex $wrappers 0]
close $f
puts "PASS: production-matched digital simulation project generated"
exit 0
