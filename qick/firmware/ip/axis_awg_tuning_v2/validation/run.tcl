set here [file dirname [file normalize [info script]]]
set out [file normalize [lindex $argv 0]]
if {[file exists $out]} {error "Use a fresh output directory: $out"}
file mkdir $out
cd $out
proc checked {cmd} {
 if {[catch {exec {*}$cmd 2>@1} result]} {puts $result; error $cmd}
 puts $result
 return $result
}
checked [list xvlog -sv {*}[glob [file join $here .. src *.sv]] [file join $here tb_awg_v2.sv] C:/Xilinx/Vivado/2023.1/data/verilog/src/glbl.v]
checked [list xelab --relax --timescale 1ns/1ps tb_awg_v2 glbl -L unisims_ver -s awg_v2]
set result [checked [list xsim awg_v2 -runall]]
if {[string first "PASS:" $result]<0 || [string first "Fatal:" $result]>=0} {error "AWG v2 failed"}
exit 0
