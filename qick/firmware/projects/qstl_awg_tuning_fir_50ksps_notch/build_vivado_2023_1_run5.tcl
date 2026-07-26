# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
#
# Reproducible Vivado 2023.1 build for qstl_awg_tuning_fir_50ksps_notch.
# The optional first Tcl argument is a fresh output directory.

set script_dir [file dirname [file normalize [info script]]]
set repo_dir [file normalize [file join $script_dir .. .. .. ..]]
set workspace_dir [file dirname $repo_dir]
set project_name qstl_awg_tuning_fir_50ksps_notch
set jobs 5

if {$argc > 0} {
    set output_dir [file normalize [lindex $argv 0]]
} else {
    set output_dir [file normalize [file join \
        $workspace_dir Vivado_Output qstl_awg_tuning_fir_50ksps_notch_run5]]
}

set vivado_version [version -short]
if {![string match "2023.1*" $vivado_version]} {
    error "Vivado 2023.1 is required; found $vivado_version"
}

# Vivado 2023.1 occasionally reports "couldn't read file ...: No error" when
# its synthesis helper first opens the unimacro Tcl files during DDR4 PHY
# regeneration. Verify and warm these installation files in the parent process
# before any child synthesis process is launched.
if {[info exists ::env(XILINX_VIVADO)]} {
    foreach runtime_name {unimacro_verilog.tcl unimacro_vhdl.tcl} {
        set runtime_path [file join \
            $::env(XILINX_VIVADO) scripts rt data unimacro $runtime_name]
        if {![file readable $runtime_path]} {
            error "Vivado runtime Tcl is not readable: $runtime_path"
        }
        set runtime_file [open $runtime_path r]
        set runtime_bytes [string length [read $runtime_file]]
        close $runtime_file
        if {$runtime_bytes == 0} {
            error "Vivado runtime Tcl is empty: $runtime_path"
        }
        puts "PREFLIGHT_RUNTIME_TCL=$runtime_path ($runtime_bytes bytes)"
    }
}

# Vivado 2023.1 debug-hub generation fails on Windows when its temporary path
# exceeds 146 characters. Predict that path before creating a large project.
# Prefer a short physical output directory. A subst drive is a fallback when a
# short physical directory is unavailable.
set expected_impl_temp [file join \
    $output_dir "$project_name.runs" impl_1 .Xil \
    "Vivado-[pid]-[info hostname]"]
if {[string length $expected_impl_temp] > 146} {
    error "Predicted Vivado implementation temporary path is [string length $expected_impl_temp] characters (limit 146): $expected_impl_temp. Use a short physical path such as C:/JeonghyunPark/Workspace/Vivado_Output/q50r5, or a subst drive as a fallback."
}

if {[file exists $output_dir]} {
    set existing_files [glob -nocomplain -directory $output_dir *]
    if {[llength $existing_files] != 0} {
        error "Output directory is not empty: $output_dir"
    }
}
file mkdir $output_dir

# launch_runs -jobs controls concurrent run workers. general.maxThreads controls
# the threads used inside synthesis and implementation. Both are required for a
# build that is comparable with the previous timing-closed run.
set_param general.maxThreads $jobs

set manifest_path [file join $output_dir build_conditions.txt]
set manifest [open $manifest_path w]
puts $manifest "project=$project_name"
puts $manifest "vivado_version=$vivado_version"
puts $manifest "part=xczu49dr-ffvf1760-2-e"
puts $manifest "board_part=xilinx.com:zcu216:part0:2.0"
puts $manifest "launch_jobs=$jobs"
puts $manifest "general.maxThreads=[get_param general.maxThreads]"
puts $manifest "synthesis_strategy=Vivado Synthesis Defaults"
puts $manifest "implementation_strategy=Vivado Implementation Defaults"
puts $manifest "manual_routing=disabled"
puts $manifest "repo_dir=$repo_dir"
puts $manifest "project_source_dir=$script_dir"
puts $manifest "output_dir=$output_dir"
if {[info exists ::env(TEMP)]} {
    puts $manifest "TEMP=$::env(TEMP)"
}
if {[info exists ::env(TMP)]} {
    puts $manifest "TMP=$::env(TMP)"
}
puts $manifest "predicted_impl_temp_path=$expected_impl_temp"
puts $manifest "predicted_impl_temp_path_length=[string length $expected_impl_temp]"
if {![catch {exec git -C $repo_dir branch --show-current} git_branch]} {
    puts $manifest "git_branch=[string trim $git_branch]"
}
if {![catch {exec git -C $repo_dir rev-parse HEAD} git_commit]} {
    puts $manifest "git_commit=[string trim $git_commit]"
}
close $manifest

puts "VIVADO_VERSION=$vivado_version"
puts "OUTPUT_DIR=$output_dir"
puts "LAUNCH_JOBS=$jobs"
puts "GENERAL_MAX_THREADS=[get_param general.maxThreads]"

create_project $project_name $output_dir -part xczu49dr-ffvf1760-2-e -force

set project_obj [current_project]
set_property board_part xilinx.com:zcu216:part0:2.0 $project_obj
set_property default_lib xil_defaultlib $project_obj
set_property enable_vhdl_2008 1 $project_obj
set_property ip_cache_permissions {read write} $project_obj
set_property ip_output_repo [file join $output_dir "$project_name.cache" ip] $project_obj
set_property mem.enable_memory_map_generation 1 $project_obj
set_property platform.board_id zcu216 $project_obj
set_property sim.central_dir [file join $output_dir "$project_name.ip_user_files"] $project_obj
set_property sim.ip.auto_export_scripts 1 $project_obj
set_property simulator_language Mixed $project_obj

set sources_obj [get_filesets sources_1]
set_property ip_repo_paths [file join $repo_dir qick firmware ip] $sources_obj
update_ip_catalog -rebuild

set constrs_obj [get_filesets constrs_1]
add_files -fileset $constrs_obj [list \
    [file join $script_dir timing.xdc] \
    [file join $script_dir ios.xdc] \
]

source [file join $script_dir bd_2023-1.tcl]
validate_bd_design
save_bd_design
report_ip_status -file [file join $output_dir ip_status_before_synth.rpt]

set bd_file [get_files [file join \
    $output_dir "$project_name.srcs" sources_1 bd d_1 d_1.bd]]
set wrapper_file [make_wrapper -files $bd_file -top]
add_files -norecurse $wrapper_file
set_property top d_1_wrapper [current_fileset]
update_compile_order -fileset sources_1

set_property strategy {Vivado Synthesis Defaults} [get_runs synth_1]
set_property strategy {Vivado Implementation Defaults} [get_runs impl_1]

launch_runs synth_1 -jobs $jobs
set synth_wait_failed [catch {wait_on_run synth_1} synth_wait_message]
set synth_status [get_property STATUS [get_runs synth_1]]
puts "SYNTH_STATUS=$synth_status"
if {$synth_wait_failed || [string first "Complete" $synth_status] < 0} {
    puts "SYNTH_WAIT_MESSAGE=$synth_wait_message"
    puts "BUILD_FAILED_AT=SYNTHESIS"
    close_project
    exit 2
}

open_run synth_1
report_utilization -file [file join $output_dir utilization_postsynth.rpt]
report_timing_summary \
    -file [file join $output_dir timing_summary_postsynth.rpt] \
    -warn_on_violation
close_design

launch_runs impl_1 -to_step write_bitstream -jobs $jobs
set impl_wait_failed [catch {wait_on_run impl_1} impl_wait_message]
set impl_status [get_property STATUS [get_runs impl_1]]
puts "IMPL_STATUS=$impl_status"
if {$impl_wait_failed || [string first "Complete" $impl_status] < 0} {
    puts "IMPL_WAIT_MESSAGE=$impl_wait_message"
    catch {open_run impl_1}
    catch {
        report_timing_summary \
            -file [file join $output_dir timing_summary_failed.rpt] \
            -warn_on_violation
    }
    puts "BUILD_FAILED_AT=IMPLEMENTATION"
    close_project
    exit 3
}

open_run impl_1
report_timing_summary \
    -file [file join $output_dir timing_summary_postroute.rpt] \
    -warn_on_violation
report_timing \
    -delay_type max \
    -max_paths 100 \
    -sort_by group \
    -file [file join $output_dir timing_paths_postroute.rpt]
report_utilization \
    -file [file join $output_dir utilization_postroute.rpt]
report_utilization \
    -hierarchical \
    -file [file join $output_dir utilization_hierarchical_postroute.rpt]
report_route_status \
    -file [file join $output_dir route_status_postroute.rpt]
report_drc \
    -file [file join $output_dir drc_postroute.rpt]
report_methodology \
    -file [file join $output_dir methodology_postroute.rpt]

set bit_src [get_property BITSTREAM.FILE [current_run]]
if {$bit_src eq ""} {
    set bit_src [file join \
        $output_dir "$project_name.runs" impl_1 d_1_wrapper.bit]
}
if {![file exists $bit_src]} {
    puts "BUILD_FAILED_AT=BITSTREAM_COPY"
    puts "MISSING_BITSTREAM=$bit_src"
    close_project
    exit 4
}
file copy -force $bit_src [file join $output_dir bitstream.bit]

set xsa_path [file join $output_dir bitstream.xsa]
write_hw_platform -fixed -include_bit -force -file $xsa_path

set hwh_src [file join \
    $output_dir "$project_name.gen" sources_1 bd d_1 hw_handoff d_1.hwh]
if {[file exists $hwh_src]} {
    file copy -force $hwh_src [file join $output_dir bitstream.hwh]
    puts "HWH_SOURCE=$hwh_src"
} else {
    puts "WARNING: generated HWH file was not found at $hwh_src"
}

set impl_run [get_runs impl_1]
set final_wns [get_property STATS.WNS $impl_run]
set final_tns [get_property STATS.TNS $impl_run]
set final_whs [get_property STATS.WHS $impl_run]
set final_ths [get_property STATS.THS $impl_run]
set timing_closed UNKNOWN
if {$final_wns ne "" && $final_whs ne ""} {
    if {[expr {double($final_wns) >= 0.0 && double($final_whs) >= 0.0}]} {
        set timing_closed YES
    } else {
        set timing_closed NO
    }
}

set result_path [file join $output_dir build_result.txt]
set result [open $result_path w]
puts $result "synthesis_status=$synth_status"
puts $result "implementation_status=$impl_status"
puts $result "setup_wns_ns=$final_wns"
puts $result "setup_tns_ns=$final_tns"
puts $result "hold_whs_ns=$final_whs"
puts $result "hold_ths_ns=$final_ths"
puts $result "timing_closed=$timing_closed"
puts $result "bitstream=[file join $output_dir bitstream.bit]"
puts $result "xsa=$xsa_path"
puts $result "hwh=[file join $output_dir bitstream.hwh]"
close $result

puts "FINAL_SETUP_WNS=$final_wns"
puts "FINAL_SETUP_TNS=$final_tns"
puts "FINAL_HOLD_WHS=$final_whs"
puts "FINAL_HOLD_THS=$final_ths"
puts "TIMING_CLOSED=$timing_closed"
puts "BITSTREAM_PATH=[file join $output_dir bitstream.bit]"
puts "XSA_PATH=$xsa_path"
puts "BUILD_DONE"
close_project
exit 0
