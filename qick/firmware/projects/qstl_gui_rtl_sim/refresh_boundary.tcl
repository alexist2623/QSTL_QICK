# For an existing simulation project: preserve host DMA stream attributes.
set here [file dirname [file normalize [info script]]]
set project [file normalize [lindex $argv 0]]
open_project [file join $project qstl_gui_rtl_sim.xpr]
open_bd_design [get_files sim_bd.bd]
set f [open [file join $here design.tcl] r]
foreach line [split [read $f] \n] {
    if {[string match {set_property -dict*get_bd_intf_ports*} $line]} {eval $line}
}
close $f
validate_bd_design
save_bd_design
generate_target all [get_files sim_bd.bd]
set wrappers [make_wrapper -files [get_files sim_bd.bd] -top]
close_project
exit 0
