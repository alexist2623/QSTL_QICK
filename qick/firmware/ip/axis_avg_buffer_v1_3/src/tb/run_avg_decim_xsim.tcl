# Run from Vivado:
#   vivado -mode batch -source run_avg_decim_xsim.tcl
#
# The simulation project is created outside the repository so Vivado logs and
# generated files do not pollute the worktree.

set PART "xczu49dr-ffvf1760-2-e"
set TOP_TB "tb"

set TB_DIR  [file normalize [file dirname [info script]]]
set SRC_DIR [file normalize [file join $TB_DIR ".."]]
set OUT_DIR [file normalize "C:/JeonghyunPark/Workspace/Vivado_Output/axis_avg_buffer_v1_3_avg_decim_sim"]

file delete -force $OUT_DIR
file mkdir $OUT_DIR

create_project axis_avg_buffer_v1_3_avg_decim_sim $OUT_DIR -part $PART -force
set_property target_language Verilog [current_project]
set_property default_lib xil_defaultlib [current_project]

set SRC_LIST [list \
  "$SRC_DIR/axis_avg_buffer.v" \
  "$SRC_DIR/avg_buffer.v" \
  "$SRC_DIR/avg_top.v" \
  "$SRC_DIR/avg.sv" \
  "$SRC_DIR/avg_decimator_iq.sv" \
  "$SRC_DIR/trace_avg.sv" \
  "$SRC_DIR/buffer_top.v" \
  "$SRC_DIR/buffer.sv" \
  "$SRC_DIR/axi_slv_avg_buf.vhd" \
  "$SRC_DIR/data_reader.vhd" \
  "$SRC_DIR/synchronizer_n.vhd" \
  "$SRC_DIR/fifo/bram_dp.vhd" \
  "$SRC_DIR/fifo/bram_simple_dp.vhd" \
  "$SRC_DIR/fifo/fifo_dc_axi.vhd" \
  "$SRC_DIR/fifo/fifo_axi.vhd" \
  "$SRC_DIR/fifo/fifo_dc.vhd" \
  "$SRC_DIR/fifo/fifo.vhd" \
  "$SRC_DIR/fifo/gray2bin.vhd" \
  "$SRC_DIR/fifo/bin2gray.vhd" \
  "$SRC_DIR/fifo/rd2axi.vhd" \
  "$SRC_DIR/fifo/synchronizer_vect.vhd" \
]

add_files -norecurse -fileset sources_1 $SRC_LIST

foreach f [get_files -of_objects [get_filesets sources_1]] {
  if {[string match *.sv [file tail $f]]} {
    set_property file_type {SystemVerilog} $f
  } elseif {[string match *.vhd [file tail $f]]} {
    set_property file_type {VHDL 2008} $f
  }
}

set TB_FILE "$TB_DIR/tb_avg_decim.sv"
add_files -fileset sim_1 $TB_FILE
set_property file_type {SystemVerilog} [get_files $TB_FILE]
set_property top $TOP_TB [get_filesets sim_1]

launch_simulation -simset sim_1 -mode behavioral
run all
quit
