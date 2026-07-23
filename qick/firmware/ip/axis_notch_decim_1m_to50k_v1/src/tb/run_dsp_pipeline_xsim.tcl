# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
set tb_dir [file normalize [file dirname [info script]]]
set src_dir [file normalize [file join $tb_dir ..]]
if {[info exists ::env(QICK_VIVADO_OUTPUT)]} {
  set output_root [file normalize $::env(QICK_VIVADO_OUTPUT)]
} else {
  set output_root {C:/JeonghyunPark/Workspace/Vivado_Output}
}
set sim_dir [file join $output_root axis_notch_decim_dsp48e2_sim]

file delete -force $sim_dir
file mkdir $sim_dir
cd $sim_dir

exec xvlog -sv \
  [file join $src_dir dsp48e2_sos_pipeline.sv] \
  [file join $tb_dir tb_dsp48e2_sos_pipeline.sv] \
  {C:/Xilinx/Vivado/2023.1/data/verilog/src/glbl.v}
exec xelab -L unisims_ver tb_dsp48e2_sos_pipeline glbl -s dsp48e2_pipeline_sim
exec xsim dsp48e2_pipeline_sim -runall
