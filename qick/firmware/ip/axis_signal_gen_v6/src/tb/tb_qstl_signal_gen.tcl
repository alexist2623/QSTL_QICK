# ---------------------------------------------------------------
# Goto src directory and run below script to make project
# vivado -mode batch -source ./tb/tb_qstl_signal_gen.tcl
# ---------------------------------------------------------------

set PART "xczu49dr-ffvf1760-2-e"    ;
set TOP_TB "tb"                     ;
# ----------------------------------------------------------------
set ROOT [file normalize [pwd]]
set PROJ    "$ROOT/.sim/tb_qstl_signal_gen"
file mkdir  $PROJ

create_project tb_qstl_signal_gen $PROJ -part $PART -force
set_property target_language Verilog [current_project]
set_property default_lib xil_defaultlib [current_project]

set SRC_LIST [list \
  "$ROOT/src/axi_slv_sg_v6.vhd" \
  "$ROOT/src/axis_signal_gen_v6.v" \
  "$ROOT/src/ctrl_sg_v6.sv" \
  "$ROOT/src/data_writer.vhd" \
  "$ROOT/src/latency_reg.v" \
  "$ROOT/src/signal_gen_top.v" \
  "$ROOT/src/signal_gen.v" \
  "$ROOT/src/synchronizer_n.vhd" \
  "$ROOT/src/fifo/bram_simple_dp.vhd" \
  "$ROOT/src/fifo/bram_dp.vhd" \
  "$ROOT/src/fifo/fifo.vhd" \
  "$ROOT/src/dds_compiler_0/dds_compiler_0.xci" \
  "$ROOT/src/tb/tb_qstl_signal_gen.sv" \
]
add_files -norecurse -fileset sources_1 $SRC_LIST

foreach f [get_files -of_objects [get_filesets sources_1]] {
  if {[string match *.sv [file tail $f]]} {
    set_property file_type {SystemVerilog} $f
  } elseif {[string match *.vhd [file tail $f]]} {
    set_property file_type {VHDL 2008} $f
  }
}

upgrade_ip -quiet [get_ips dds_compiler_0]

set_property top axis_signal_gen_v6_tb [get_filesets sim_1]
set_property -name {xsim.simulate.runtime} -value {1ms} -objects [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1
