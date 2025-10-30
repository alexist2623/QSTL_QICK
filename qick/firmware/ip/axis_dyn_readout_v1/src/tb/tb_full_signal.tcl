# ---------------------------------------------------------------
# Goto src directory and run below script to make project
# vivado -mode batch -source ./tb/tb_qstl_dyn_readout.tcl
# ---------------------------------------------------------------

set PART "xczu49dr-ffvf1760-2-e"    ;
set TOP_TB "tb"                     ;
# ----------------------------------------------------------------
set ROOT [file normalize [pwd]]
set PROJ    "$ROOT/.sim/tb_qstl_dyn_readout"
file mkdir  $PROJ

create_project tb_qstl_dyn_readout $PROJ -part $PART -force
set_property target_language Verilog [current_project]
set_property default_lib xil_defaultlib [current_project]

set SRC_LIST [list \
  "$ROOT/src/axis_dyn_readout_v1.v" \
  "$ROOT/src/ctrl_dyn_ro_v1.sv" \
  "$ROOT/src/down_conversion_fir.v" \
  "$ROOT/src/down_conversion.v" \
  "$ROOT/src/fir.coe" \
  "$ROOT/src/readout_top.v" \
  "$ROOT/src/fifo/bram_simple_dp.vhd" \
  "$ROOT/src/fifo/bram_dp.vhd" \
  "$ROOT/src/fifo/fifo.vhd" \
  "$ROOT/../axis_signal_gen_v6/src/axi_slv_sg_v6.vhd" \
  "$ROOT/../axis_signal_gen_v6/src/axis_signal_gen_v6.v" \
  "$ROOT/../axis_signal_gen_v6/src/ctrl_sg_v6.sv" \
  "$ROOT/../axis_signal_gen_v6/src/data_writer.vhd" \
  "$ROOT/../axis_signal_gen_v6/src/latency_reg.v" \
  "$ROOT/../axis_signal_gen_v6/src/signal_gen_top.v" \
  "$ROOT/../axis_signal_gen_v6/src/signal_gen.v" \
  "$ROOT/../axis_signal_gen_v6/src/synchronizer_n.vhd" \
  "$ROOT/src/fir_compiler_0/fir_compiler_0.xci" \
  "$ROOT/src/dds_compiler_0/dds_compiler_0.xci" \
  "$ROOT/src/tb/tb_full_signal.sv"
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

set_property top tb_full_signal [get_filesets sim_1]
set_property -name {xsim.simulate.runtime} -value {10ms} -objects [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1