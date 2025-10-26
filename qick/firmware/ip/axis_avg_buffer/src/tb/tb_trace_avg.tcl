# ---------------------------------------------------------------
# vivado -mode batch -source scripts/sim_trace_avg.tcl
# ---------------------------------------------------------------

set PART "xczu49dr-ffvf1760-2-e"    ;
set TOP_TB "tb"                     ;
# ----------------------------------------------------------------
set ROOT [file normalize [pwd]]
set PROJ    "$ROOT/.sim/sim_trace_avg"
file mkdir  $PROJ

create_project sim_trace_avg $PROJ -part $PART -force
set_property target_language Verilog [current_project]
set_property default_lib xil_defaultlib [current_project]

set SRC_LIST [list \
  "$ROOT/avg_buffer.v" \
  "$ROOT/avg_top.v" \
  "$ROOT/avg.sv" \
  "$ROOT/trace_avg.sv" \
  "$ROOT/buffer_top.v" \
  "$ROOT/buffer.sv" \
  "$ROOT/data_reader.vhd" \
  "$ROOT/synchronizer_n.vhd" \
  "$ROOT/fifo/bram_dp.vhd" \
  "$ROOT/fifo/bram_simple_dp.vhd" \
  "$ROOT/fifo/fifo_dc_axi.vhd" \
  "$ROOT/fifo/fifo_axi.vhd" \
  "$ROOT/fifo/fifo_dc.vhd" \
  "$ROOT/fifo/fifo.vhd" \
  "$ROOT/fifo/gray2bin.vhd" \
  "$ROOT/fifo/bin2gray.vhd" \
  "$ROOT/fifo/rd2axi.vhd" \
  "$ROOT/fifo/synchronizer_vect.vhd"
]

add_files -norecurse -fileset sources_1 $SRC_LIST

foreach f [get_files -of_objects [get_filesets sources_1]] {
  if {[string match *.sv [file tail $f]]} {
    set_property file_type {SystemVerilog} $f
  } elseif {[string match *.vhd [file tail $f]]} {
    set_property file_type {VHDL 2008} $f
  }
}

set TB_FILE "$ROOT/tb/tb_trace_avg.sv"
if {![file exists $TB_FILE]} {
  puts "ERROR: $TB_FILE is not found."
  exit 1
}
add_files -fileset sim_1 $TB_FILE
set_property file_type {SystemVerilog} [get_files $TB_FILE]
set_property top $TOP_TB [get_filesets sim_1]

if {[file exists "$ROOT/tb/tb_waves.wcfg"]} {
  set_property xsim.view $ROOT/tb/tb_waves.wcfg [get_filesets sim_1]
}

# launch_simulation -simset sim_1 -mode behavioral
# run all
# quit
