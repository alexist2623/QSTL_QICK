# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
set script_dir [file dirname [file normalize [info script]]]
set repo_dir [file normalize [file join $script_dir .. .. .. ..]]
set workspace_dir [file dirname $repo_dir]
set output_dir [file normalize [file join $workspace_dir Vivado_Output qstl_awg_tuning_fir]]
set project_name qstl_awg_tuning_fir

file mkdir $output_dir

create_project $project_name $output_dir -part xczu49dr-ffvf1760-2-e -force

set project_obj [current_project]
set_property -name board_part -value xilinx.com:zcu216:part0:2.0 -objects $project_obj
set_property -name default_lib -value xil_defaultlib -objects $project_obj
set_property -name enable_vhdl_2008 -value 1 -objects $project_obj
set_property -name ip_cache_permissions -value "read write" -objects $project_obj
set_property -name ip_output_repo -value [file join $output_dir "$project_name.cache" ip] -objects $project_obj
set_property -name mem.enable_memory_map_generation -value 1 -objects $project_obj
set_property -name platform.board_id -value zcu216 -objects $project_obj
set_property -name sim.central_dir -value [file join $output_dir "$project_name.ip_user_files"] -objects $project_obj
set_property -name sim.ip.auto_export_scripts -value 1 -objects $project_obj
set_property -name simulator_language -value Mixed -objects $project_obj

set sources_obj [get_filesets sources_1]
set_property ip_repo_paths [file normalize [file join $repo_dir qick firmware ip]] $sources_obj
update_ip_catalog -rebuild

set constrs_obj [get_filesets constrs_1]
add_files -fileset $constrs_obj [list \
  [file normalize [file join $script_dir timing.xdc]] \
  [file normalize [file join $script_dir ios.xdc]] \
]

source [file normalize [file join $script_dir bd_2023-1.tcl]]
validate_bd_design
save_bd_design

set bd_file [get_files [file join $output_dir "$project_name.srcs" sources_1 bd d_1 d_1.bd]]
set wrapper_file [make_wrapper -files $bd_file -top]
add_files -norecurse $wrapper_file
set_property top d_1_wrapper [current_fileset]
update_compile_order -fileset sources_1
