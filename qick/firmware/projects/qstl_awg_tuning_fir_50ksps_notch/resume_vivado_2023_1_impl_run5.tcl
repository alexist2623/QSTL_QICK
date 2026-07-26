# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
#
# Restart implementation for a project whose synthesis completed successfully.
# Usage:
#   vivado -mode batch -source resume_vivado_2023_1_impl_run5.tcl \
#       -tclargs W:/q50r5

set project_name qstl_awg_tuning_fir_50ksps_notch
set jobs 5

if {$argc != 1} {
    error "Pass exactly one existing Vivado output directory"
}
set output_dir [file normalize [lindex $argv 0]]
set project_file [file join $output_dir "$project_name.xpr"]
if {![file exists $project_file]} {
    error "Vivado project not found: $project_file"
}

set vivado_version [version -short]
if {![string match "2023.1*" $vivado_version]} {
    error "Vivado 2023.1 is required; found $vivado_version"
}

# Validate and warm the runtime Tcl files before DDR4 PHY regeneration starts
# in a synthesis helper process.
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

set_param general.maxThreads $jobs
open_project $project_file

set synth_status [get_property STATUS [get_runs synth_1]]
if {[string first "Complete" $synth_status] < 0} {
    error "Synthesis is not complete: $synth_status"
}

set retry_log [open [file join $output_dir implementation_retry.txt] a]
puts $retry_log "timestamp=[clock format [clock seconds] -format {%Y-%m-%d %H:%M:%S}]"
puts $retry_log "vivado_version=$vivado_version"
puts $retry_log "launch_jobs=$jobs"
puts $retry_log "general.maxThreads=[get_param general.maxThreads]"
puts $retry_log "synthesis_status=$synth_status"
if {[info exists ::env(TEMP)]} {
    puts $retry_log "TEMP=$::env(TEMP)"
}
if {[info exists ::env(TMP)]} {
    puts $retry_log "TMP=$::env(TMP)"
}
close $retry_log

set_property strategy {Vivado Implementation Defaults} [get_runs impl_1]
reset_run impl_1
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
    puts "BUILD_FAILED_AT=IMPLEMENTATION_RETRY"
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
puts $result "implementation_retried=YES"
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
