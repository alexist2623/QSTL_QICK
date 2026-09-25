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
checked [list xvlog -sv [file join $ip_dir src square_dds.sv] [file join $ip_dir src tb_square_dds_500us.sv]]
checked [list xelab tb_square_dds_500us -s tb_square_dds_500us]
set result [checked [list xsim tb_square_dds_500us -runall]]
if {[string first "PASS:" $result] < 0 || [string first "Fatal:" $result] >= 0} {
    error "500 us square DDS regression failed"
}
puts "PASS: 500 us square DDS regression"
exit 0
