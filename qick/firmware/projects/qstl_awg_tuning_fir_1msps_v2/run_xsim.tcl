# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
# Run the shared FIR/DDR regressions and the new project's integration test.
# Argument 0 must be a fresh output directory; existing results are preserved.
set project_dir [file dirname [file normalize [info script]]]
set ip_dir [file normalize [file join $project_dir .. .. ip]]
if {$argc != 1} { error "Usage: vivado -mode batch -source run_xsim.tcl -tclargs FRESH_OUTPUT_DIR" }
set output_dir [file normalize [lindex $argv 0]]
if {[file exists $output_dir]} { error "Output already exists: $output_dir" }
file mkdir $output_dir
cd $output_dir

proc run_checked {command} {
    puts "RUN: $command"
    if {[catch {exec {*}$command 2>@1} result]} {
        puts $result
        error "Command failed: $command"
    }
    puts $result
    return $result
}
set fir_dir [file join $ip_dir axis_fir_decim_300to1_v1]
set ddr_dir [file join $ip_dir axis_buffer_ddr_sample_v2 src]
run_checked [list xvlog -sv \
    [file join $fir_dir src fir_decim_300to1_coeffs_pkg.sv] \
    [file join $fir_dir src axis_fir_decim_stage.sv] \
    [file join $fir_dir src axis_fir_decim_300to1_v1.sv] \
    [file join $fir_dir src tb tb_axis_fir_decim_300to1_v1.sv] \
    [file join $ip_dir axis_trigger_sync_v1 src axis_trigger_sync_v1.sv] \
    [file join $ddr_dir axis_buffer_ddr_sample_v2.sv] \
    [file join $ddr_dir tb_axis_buffer_ddr_sample_v2.sv] \
    [file join $project_dir tb_fir_ddr_1msps_v2.sv]]
foreach top {tb_axis_buffer_ddr_sample_v2 tb_axis_fir_decim_300to1_v1 tb_fir_ddr_1msps_v2} {
    run_checked [list xelab $top -s $top]
    set result [run_checked [list xsim $top -runall -testplusarg "VECTOR_DIR=[file join $fir_dir vectors]"]]
    if {[string first "PASS:" $result] < 0 || [string first "FAIL:" $result] >= 0} {
        error "Simulation did not pass: $top"
    }
}
puts "PASS: all 1 MSPS V2 RTL regressions"
exit 0
