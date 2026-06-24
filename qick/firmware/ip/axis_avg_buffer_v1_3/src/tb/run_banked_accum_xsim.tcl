# Run from Vivado:
#   vivado -mode batch -source run_banked_accum_xsim.tcl
#
# The simulation project is created outside the repository.

set PART "xczu49dr-ffvf1760-2-e"
set TOP_TB "tb_banked_accum_mem"

set TB_DIR  [file normalize [file dirname [info script]]]
set SRC_DIR [file normalize [file join $TB_DIR ".."]]
set OUT_DIR [file normalize "C:/JeonghyunPark/Workspace/Vivado_Output/axis_avg_buffer_v1_3_banked_accum_sim"]

file delete -force $OUT_DIR
file mkdir $OUT_DIR

create_project axis_avg_buffer_v1_3_banked_accum_sim $OUT_DIR -part $PART -force
set_property target_language Verilog [current_project]
set_property default_lib xil_defaultlib [current_project]
set_property verilog_define {SIM_MODEL} [get_filesets sources_1]
set_property verilog_define {SIM_MODEL} [get_filesets sim_1]

set SRC_LIST [list \
  "$SRC_DIR/ramb36e2_accum_mem.sv" \
]

add_files -norecurse -fileset sources_1 $SRC_LIST

foreach f [get_files -of_objects [get_filesets sources_1]] {
  if {[string match *.sv [file tail $f]]} {
    set_property file_type {SystemVerilog} $f
  }
}

set TB_FILE "$TB_DIR/tb_banked_accum_mem.sv"
add_files -fileset sim_1 $TB_FILE
set_property file_type {SystemVerilog} [get_files $TB_FILE]
set_property top $TOP_TB [get_filesets sim_1]

launch_simulation -simset sim_1 -mode behavioral
run all
quit
