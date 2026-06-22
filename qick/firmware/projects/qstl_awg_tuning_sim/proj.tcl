# Vivado 2023.1 batch project for qstl_awg_tuning simulation only.
# Generated project files are written outside this repository.

set script_dir [file dirname [file normalize [info script]]]
set repo_dir [file normalize [file join $script_dir .. .. .. ..]]
set workspace_dir [file dirname $repo_dir]
set output_dir [file normalize [file join $workspace_dir Vivado_Output qstl_awg_tuning_sim]]
set project_name qstl_awg_tuning_sim
set part_name xczu49dr-ffvf1760-2-e
set board_part xilinx.com:zcu216:part0:2.0

file mkdir $output_dir
create_project -force $project_name $output_dir -part $part_name
set_property board_part $board_part [current_project]
set_property target_language Verilog [current_project]
set_property simulator_language Mixed [current_project]

set_property ip_repo_paths [list [file normalize [file join $repo_dir qick firmware ip]]] [current_project]
update_ip_catalog

source [file normalize [file join $script_dir bd_2023-1.tcl]]

set bd_file [get_files qstl_awg_tuning_sim_bd.bd]
validate_bd_design
generate_target all $bd_file
set wrapper_files [make_wrapper -files $bd_file -top]
add_files -norecurse $wrapper_files

add_files -fileset sim_1 -norecurse [list \
  [file normalize [file join $script_dir sim tb_qstl_awg_tuning_sim.sv]] \
]

set_property top tb_qstl_awg_tuning_sim [get_filesets sim_1]
set_property top_lib xil_defaultlib [get_filesets sim_1]
set_property -name {xsim.simulate.runtime} -value {all} -objects [get_filesets sim_1]

update_compile_order -fileset sources_1
update_compile_order -fileset sim_1

puts "QSTL AWG tuning simulation project created at: $output_dir"
puts "Run simulation with: vivado -mode batch -source [file normalize [file join $script_dir sim run_sim.tcl]]"
