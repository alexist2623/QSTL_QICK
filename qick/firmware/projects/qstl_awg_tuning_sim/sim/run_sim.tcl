# Run qstl_awg_tuning_sim in Vivado/XSim batch mode.

set script_dir [file dirname [file normalize [info script]]]
set repo_dir [file normalize [file join $script_dir .. .. .. .. ..]]
set workspace_dir [file dirname $repo_dir]
set sim_output_dir [file normalize [file join $workspace_dir Vivado_Output qstl_awg_tuning_sim qstl_awg_tuning_sim.sim sim_1 behav xsim]]
source [file normalize [file join $script_dir .. proj.tcl]]

launch_simulation -simset sim_1 -mode behavioral
close_sim
catch {open_bd_design [get_files qstl_awg_tuning_sim_bd.bd]}

puts "Simulation CSV outputs are in: $sim_output_dir"
