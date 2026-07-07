# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
# Run from Vivado:
#   vivado -mode batch -source run_accum_word_to_axis64_xsim.tcl
#
# The simulation project is created outside the repository so Vivado logs and
# generated files do not pollute the worktree.

set TOP_TB "tb_accum_word_to_axis64"

set TB_DIR  [file normalize [file dirname [info script]]]
set SRC_DIR [file normalize [file join $TB_DIR ".."]]
set OUT_DIR [file normalize "C:/JeonghyunPark/Workspace/Vivado_Output/axis_avg_buffer_v1_3_axis64_serializer_sim"]

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

run_cmd [list xvlog -sv "$SRC_DIR/axis_accum_word_to_axis64.sv" "$TB_DIR/tb_accum_word_to_axis64.sv"]
run_cmd [list xelab $TOP_TB -s axis64_serializer_sim]
run_cmd [list xsim axis64_serializer_sim -runall]
