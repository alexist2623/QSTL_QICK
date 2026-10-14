# Resume only the two crashed IP runs of the fresh a3full7 project.
# Original failure folders and original build script are preserved before reset_run.
set output_dir F:/Vivado_Output/a3full7
set project_name qstl_awg_v3
set repo_dir C:/GIT_Workspace/QSTL_QICK
set gui_repo_dir C:/GIT_Workspace/PulseGenerator
set script_dir C:/GIT_Workspace/QSTL_QICK/qick/firmware/projects/qstl_awg_v3
set jobs 4
set threads 5
set constraints_dir [file join $output_dir constraints]
set constraint_hashes [list timing.xdc 9f9d68f0d1d9e69d9c236606d65781e5c1f5eed4b1672a24daebfb670e0bacfb ios.xdc 5435d174456af7c2156207ad1571fb56aec6ea1264efea73f9a42a11623430a7]
proc path_is_inside {candidate parent} {
    # Vivado's Windows paths are case-insensitive; include the directory boundary.
    set candidate [string tolower [file normalize $candidate]]
    set parent [string trimright [string tolower [file normalize $parent]] /]
    return [expr {$candidate eq $parent || [string first "$parent/" $candidate] == 0}]
}
foreach protected_repo [list $repo_dir $gui_repo_dir] {
    if {[path_is_inside $output_dir $protected_repo]} {
        error "Build output must be outside both Git repositories: $output_dir"
    }
}

proc sha256_file {path} {
    set certutil [file join $::env(SystemRoot) System32 certutil.exe]
    set output [exec $certutil -hashfile [file nativename $path] SHA256]
    set hashes {}
    foreach line [split $output "\n"] {
        set line [string map [list " " "" "\t" "" "\r" ""] $line]
        if {[regexp {^[0-9a-fA-F]{64}$} $line]} {
            lappend hashes [string tolower $line]
        }
    }
    if {[llength $hashes] != 1} {error "Could not read one SHA256 for $path"}
    return [lindex $hashes 0]
}

proc verify_constraint_snapshots {constraints_dir expected_hashes} {
    foreach {name expected} $expected_hashes {
        if {[sha256_file [file join $constraints_dir $name]] ne $expected} {
            error "Build constraint snapshot changed: $name"
        }
    }
}


if {![string match "2023.1*" [version -short]]} {error "Wrong Vivado version"}
if {[sha256_file [file join $script_dir build_vivado_2023_1.tcl]] ne "9d627f1cf2acf9c19b2900cc9ac7062ef58a2855209a499fc97851770e56f254"} {error "Original build script changed"}
verify_constraint_snapshots $constraints_dir $constraint_hashes
verify_constraint_snapshots $script_dir $constraint_hashes
set_param general.maxThreads $threads
open_project [file join $output_dir "$project_name.xpr"]
if {[get_property PART [current_project]] ne "xczu49dr-ffvf1760-2-e"} {error "Wrong part"}
if {[get_property STRATEGY [get_runs synth_1]] ne "Vivado Synthesis Defaults"} {error "Synthesis strategy changed"}
if {[get_property STRATEGY [get_runs impl_1]] ne "Vivado Implementation Defaults"} {error "Implementation strategy changed"}
set retry_runs {d_1_axi_smc_1_0_synth_1 d_1_axis_fir_decim_300to1_v2_0_0_synth_1}
foreach run [get_runs] {
    set name [get_property NAME $run]
    if {![string match *_synth_1 $name] || $name in $retry_runs} {continue}
    set status [get_property STATUS $run]
    if {$status ni {"synth_design Complete!" "Using cached IP results"} || [get_property PROGRESS $run] ne "100%"} {error "Unexpected incomplete run: $name ($status)"}
    set run_dir [get_property DIRECTORY $run]
    if {![file exists [file join $run_dir .vivado.end.rst]] || [llength [glob -nocomplain -directory $run_dir *.dcp]] == 0} {error "Missing successful IP artifact: $name"}
}
foreach name $retry_runs {
    if {![file exists [file join $repo_dir analysis_results awg_tuning_v3 synthesis_failure_a3full7 $name .vivado.error.rst]]} {error "Missing preserved failure: $name"}
    if {[string first "ERROR" [string toupper [get_property STATUS [get_runs $name]]]] < 0} {error "Unexpected retry status: $name"}
    reset_run $name
}
puts "RECOVERY_JOBS=$jobs"
puts "RECOVERY_MAX_THREADS=[get_param general.maxThreads]"
launch_runs $retry_runs -jobs $jobs
foreach name $retry_runs {
    set failed [catch {wait_on_run $name} message]
    set status [get_property STATUS [get_runs $name]]
    puts "RETRY_STATUS=$name:$status"
    if {$failed || [string first "Complete" $status] < 0} {
        puts "RETRY_FAILED=$message"
        close_project
        exit 6
    }
}
# Original build tail below is byte-identical after newline normalization.
verify_constraint_snapshots $constraints_dir $constraint_hashes
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

verify_constraint_snapshots $constraints_dir $constraint_hashes
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
verify_constraint_snapshots $constraints_dir $constraint_hashes
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

set square_regs [get_cells -hier -filter {IS_SEQUENTIAL && NAME =~ *axis_square_pulse_v1_0*}]
if {[llength $square_regs] == 0} {error "SquarePulse registers were not found"}
report_timing -from $square_regs -to $square_regs -max_paths 20 -file [file join $output_dir square_dds_timing_postroute.rpt]
report_bus_skew -file [file join $output_dir bus_skew_postroute.rpt]

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
if {$timing_closed ne "YES"} {exit 5}
exit 0
