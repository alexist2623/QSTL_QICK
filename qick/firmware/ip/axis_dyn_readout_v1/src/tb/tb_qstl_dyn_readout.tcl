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
  "$ROOT/src/fifo/fifo.vhd" \
  "$ROOT/src/fir_compiler_0/fir_compiler_0.xci" \
  "$ROOT/src/dds_compiler_0/dds_compiler_0.xci" \
  "$ROOT/src/tb/tb_qstl_dyn_readout.sv" \
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

set_property top tb_qstl_dyn_readout [get_filesets sim_1]
set_property -name {xsim.simulate.runtime} -value {10ms} -objects [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1