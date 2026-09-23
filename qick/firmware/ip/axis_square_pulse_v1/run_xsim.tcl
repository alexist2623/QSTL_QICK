set ip_dir [file dirname [file normalize [info script]]]
if {$argc != 1} {error "Pass a fresh output directory"}
set output_dir [file normalize [lindex $argv 0]]
if {[file exists $output_dir]} {error "Output already exists: $output_dir"}
file mkdir $output_dir
cd $output_dir
proc checked {command} {
    if {[catch {exec {*}$command 2>@1} result]} {puts $result; error $command}
    puts $result
    return $result
}
checked [list xvlog -sv [file join $ip_dir src square_dds.sv] [file join $ip_dir src axis_square_pulse_v1.sv] [file join $ip_dir src tb_square_dds.sv] [file join $ip_dir src tb_axis_square_pulse_v1.sv]]
foreach top {tb_square_dds tb_axis_square_pulse_v1} {
    checked [list xelab $top -s $top]
    set result [checked [list xsim $top -runall]]
    if {[string first "PASS:" $result] < 0 || [string first "Fatal:" $result] >= 0} {error "Square DDS regression failed: $top"}
}
puts "PASS: square DDS regression"
exit 0
