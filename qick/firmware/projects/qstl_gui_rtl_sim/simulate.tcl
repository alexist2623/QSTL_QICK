set here [file dirname [file normalize [info script]]]
set project [file normalize [lindex $argv 0]]
set scenario [lindex $argv 1]
set cycles [lindex $argv 2]
set ntrig [lindex $argv 3]
open_project [file join $project qstl_gui_rtl_sim.xpr]
add_files -fileset sim_1 -norecurse [file join $here tb_gui.sv]
set_property include_dirs $here [get_filesets sim_1]
set_property top tb_gui [get_filesets sim_1]
set_property xsim.simulate.runtime 0ns [get_filesets sim_1]
set_property xsim.elaborate.debug_level typical [get_filesets sim_1]
set_property -dict [list xsim.simulate.xsim.more_options "-testplusarg ROOT=$here -testplusarg CASE=$here/$scenario -testplusarg CYCLES=$cycles -testplusarg NTRIG=$ntrig"] [get_filesets sim_1]
update_compile_order -fileset sim_1
launch_simulation -scripts_only
close_project
exit 0
