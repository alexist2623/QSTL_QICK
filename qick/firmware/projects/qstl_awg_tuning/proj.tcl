# Resolve paths from this script so the project can be launched from any cwd.
namespace eval _qstl_awg_tuning {
  proc get_script_folder {} {
    set script_path [file normalize [info script]]
    return [file dirname $script_path]
  }
}

set script_dir [_qstl_awg_tuning::get_script_folder]
set repo_root [file normalize [file join $script_dir .. .. .. ..]]
set workspace_root [file normalize [file join $repo_root ..]]
set project_root [file normalize [file join $workspace_root Vivado_Output qstl_awg_tuning]]

file mkdir $project_root

# Set the project name.
set _xil_proj_name_ "qstl_awg_tuning"

# Create project under the parent workspace's Vivado_Output/qstl_awg_tuning.
create_project -force ${_xil_proj_name_} $project_root -part xczu49dr-ffvf1760-2-e

# Set the directory path for the new project.
set proj_dir [get_property directory [current_project]]

# Set project properties.
set obj [current_project]
set_property -name "board_part" -value "xilinx.com:zcu216:part0:2.0" -objects $obj
set_property -name "default_lib" -value "xil_defaultlib" -objects $obj
set_property -name "enable_vhdl_2008" -value "1" -objects $obj
set_property -name "ip_cache_permissions" -value "read write" -objects $obj
set_property -name "ip_output_repo" -value "$proj_dir/${_xil_proj_name_}.cache/ip" -objects $obj
set_property -name "mem.enable_memory_map_generation" -value "1" -objects $obj
set_property -name "platform.board_id" -value "zcu216" -objects $obj
set_property -name "sim.central_dir" -value "$proj_dir/${_xil_proj_name_}.ip_user_files" -objects $obj
set_property -name "sim.ip.auto_export_scripts" -value "1" -objects $obj
set_property -name "simulator_language" -value "Mixed" -objects $obj

# Set IP repository paths.
set obj [get_filesets sources_1]
set_property "ip_repo_paths" [file normalize [file join $repo_root qick firmware ip]] $obj

# Rebuild user ip_repo's index before adding any source files.
update_ip_catalog -rebuild

# Set 'constrs_1' fileset object.
set obj [get_filesets constrs_1]

# Add/import constraints from this variant directory.
set files [list \
  [file normalize [file join $script_dir timing.xdc]] \
  [file normalize [file join $script_dir ios.xdc]] \
]
add_files -fileset $obj $files

# Source block design from this variant directory.
set file [file normalize [file join $script_dir bd_2023-1.tcl]]
source $file

validate_bd_design
report_ip_status
save_bd_design

# Set sources_1 fileset object.
set obj [get_filesets sources_1]
