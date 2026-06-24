# Run from Vivado:
#   vivado -mode batch -source run_trace_noise_avg_xsim.tcl
#
# The simulation project is created outside the repository so Vivado logs and
# generated files do not pollute the worktree.

set TOP_TB "tb"

set TB_DIR  [file normalize [file dirname [info script]]]
set SRC_DIR [file normalize [file join $TB_DIR ".."]]
set OUT_DIR [file normalize "C:/JeonghyunPark/Workspace/Vivado_Output/axis_avg_buffer_v1_3_trace_noise_avg_sim"]

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

set VERILOG_LIST [list \
  "$SRC_DIR/axis_avg_buffer.v" \
  "$SRC_DIR/avg_buffer.v" \
  "$SRC_DIR/avg_top.v" \
  "$SRC_DIR/avg.sv" \
  "$SRC_DIR/axis_accum_word_to_axis64.sv" \
  "$SRC_DIR/ramb36e2_accum_mem.sv" \
  "$SRC_DIR/trace_avg.sv" \
  "$SRC_DIR/buffer_top.v" \
  "$SRC_DIR/buffer.sv" \
  "$TB_DIR/tb_trace_noise_avg.sv" \
]

set VHDL_LIST [list \
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

run_cmd [concat [list xvhdl --2008] $VHDL_LIST]
run_cmd [concat [list xvlog -sv -d SIM_MODEL -d FAST_SIM] $VERILOG_LIST]
run_cmd [list xelab $TOP_TB -s trace_noise_avg_sim]
run_cmd [list xsim trace_noise_avg_sim -runall]
