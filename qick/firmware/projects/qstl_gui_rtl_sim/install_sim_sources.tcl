# Make the generated .xpr runnable from Vivado's normal Run Simulation UI.
# Namespaced copies are simulation sources only; production BD remains visible.
set here [file dirname [file normalize [info script]]]
set build [file normalize [lindex $argv 0]]
set scenario [lindex $argv 1]
set cycles [lindex $argv 2]
set ntrig [lindex $argv 3]
open_project [file join $build qstl_gui_rtl_sim.xpr]
set_property used_in {synthesis implementation} [get_files -of_objects [get_filesets sources_1]]
set old [get_files -of_objects [get_filesets sim_1]]
if {[llength $old]} {remove_files $old}
set generated [file join $build namespaced]
set copied_sources [lsort [glob -nocomplain $generated/*.v $generated/*.sv $generated/*.vhd]]
add_files -fileset sim_1 -norecurse $copied_sources
set_property library xil_defaultlib [get_files -of_objects [get_filesets sim_1]]
set_property used_in {simulation} [get_files -of_objects [get_filesets sim_1]]
set_property include_dirs $generated [get_filesets sim_1]
set_property top tb_gui [get_filesets sim_1]
set_property xsim.elaborate.debug_level off [get_filesets sim_1]
set run [file join $build qstl_gui_rtl_sim.sim sim_1 behav xsim]
set f [open [file join $run elaborate.bat] r]
set script [read $f]
close $f
set libs [lsort -unique [regexp -all -inline -- {-L \w+} $script]]
set_property -dict [list xsim.elaborate.xelab.more_options [join $libs { }]] [get_filesets sim_1]
set f [open [file join $build gui_plusargs.txt] w]
puts $f "-testplusarg \"ROOT=$here\""
puts $f "-testplusarg \"CASE=$here/$scenario\""
puts $f "-testplusarg \"CYCLES=$cycles\""
puts $f "-testplusarg \"NTRIG=$ntrig\""
puts $f "-testplusarg \"SEED=[expr {$scenario eq {gui_autonomy}}]\""
close $f
set_property -dict [list xsim.simulate.xsim.more_options "-f \"$build/gui_plusargs.txt\""] [get_filesets sim_1]
set_property xsim.simulate.runtime 0ns [get_filesets sim_1]
update_compile_order -fileset sim_1
close_project
exit 0
