set here [file dirname [file normalize [info script]]]
if {$argc < 1} {error "Pass a fresh output directory and optional testbench name"}
set top tb_rc_precomp
if {$argc > 1} {set top [lindex $argv 1]}
set output_dir [file normalize [lindex $argv 0]]
if {[file exists $output_dir]} {error "Output already exists: $output_dir"}
file mkdir $output_dir
cd $output_dir
proc checked {command} {
    if {[catch {exec {*}$command 2>@1} result]} {puts $result; error $command}
    puts $result
    return $result
}
set sources [glob [file join $here .. axis_awg_tuning_v1 src *.sv]]
lappend sources {*}[glob [file join $here .. axis_square_pulse_v1 src *.sv]]
set sources [lsearch -all -inline -not -glob $sources *tb_*]
checked [list xvlog -sv {*}$sources [file join $here ${top}.sv] C:/Xilinx/Vivado/2023.1/data/verilog/src/glbl.v]
checked [list xelab $top glbl -L unisims_ver -s $top]
set result [checked [list xsim $top -runall]]
if {[string first "PASS:" $result] < 0 || [string first "Fatal:" $result] >= 0} {
    error "RC regression failed"
}
exit 0
