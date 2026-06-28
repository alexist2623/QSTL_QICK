# Run from Vivado:
#   vivado -mode batch -source run_tb_axis_buffer_ddr_sample_xsim.tcl
#
# Generated simulation files are written outside the repository.

set TOP_TB "tb_axis_buffer_ddr_sample_v1"

set SRC_DIR [file normalize [file dirname [info script]]]
set OUT_DIR [file normalize "C:/JeonghyunPark/Workspace/Vivado_Output/axis_buffer_ddr_sample_v1_sim"]

file delete -force $OUT_DIR
file mkdir $OUT_DIR
cd $OUT_DIR

proc run_cmd {cmd} {
  puts "Running: [join $cmd { }]"
  if {[catch {exec {*}$cmd} result]} {
    puts $result
    exit 1
  }
  puts $result
}

run_cmd [list xvlog -sv "$SRC_DIR/axis_buffer_ddr_sample_v1.sv" "$SRC_DIR/tb_axis_buffer_ddr_sample_v1.sv"]
run_cmd [list xelab $TOP_TB -s ddr_sample_sim]
run_cmd [list xsim ddr_sample_sim -runall]
