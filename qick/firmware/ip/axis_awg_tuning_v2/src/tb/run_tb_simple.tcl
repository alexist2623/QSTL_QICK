# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
# Compatibility entry point for the production AWG v2 validation suite.
# Pass one fresh output directory with Vivado -tclargs.
if {$argc != 1} {error "Pass a fresh output directory with -tclargs"}
set script_dir [file dirname [file normalize [info script]]]
source [file normalize [file join $script_dir .. .. validation run.tcl]]
