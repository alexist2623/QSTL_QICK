set IP_ROOT "[file normalize [pwd]]"
set COMP "$IP_ROOT/component.xml"
set core [ipx::open_core $COMP]

puts "Available file groups:"
foreach fg [ipx::get_file_groups -of_objects $core] {
  puts "  [get_property NAME $fg]"
}
set fs_synth ""
set fs_sim   ""

foreach fg [ipx::get_file_groups -of_objects $core] {
  set name [get_property NAME $fg]
  if {$name eq "xilinx_anylanguagesynthesis"} {
    set fs_synth $fg
  } elseif {$name eq "xilinx_anylanguagebehavioralsimulation"} {
    set fs_sim $fg
  }
}
if {$fs_synth eq ""} { error "synthesis file group not found" }
if {$fs_sim   eq ""} { error "simulation file group not found" }

ipx::add_file -file_group $fs_synth -name  [file normalize ./src/trace_avg.sv]
ipx::add_file -file_group $fs_sim -name  [file normalize ./src/trace_avg.sv]

ipx::check_integrity $core -quiet
ipx::save_core $core
ipx::unload_core $core
