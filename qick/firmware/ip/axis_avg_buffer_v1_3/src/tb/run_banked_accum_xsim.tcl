# Run from Vivado:
#   vivado -mode batch -source run_banked_accum_xsim.tcl
#
# The simulation project is created outside the repository.

set TOP_TB "tb_banked_accum_mem"

set TB_DIR  [file normalize [file dirname [info script]]]
set SRC_DIR [file normalize [file join $TB_DIR ".."]]
set OUT_DIR [file normalize "C:/JeonghyunPark/Workspace/Vivado_Output/axis_avg_buffer_v1_3_banked_accum_sim"]

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

run_cmd [list xvlog -sv -d SIM_MODEL "$SRC_DIR/ramb36e2_accum_mem.sv" "$TB_DIR/tb_banked_accum_mem.sv"]
run_cmd [list xelab $TOP_TB -s banked_accum_sim]
run_cmd [list xsim banked_accum_sim -runall]
