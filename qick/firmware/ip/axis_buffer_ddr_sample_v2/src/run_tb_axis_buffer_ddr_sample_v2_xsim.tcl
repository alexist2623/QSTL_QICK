# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
set src_dir [file normalize [file dirname [info script]]]
if {[info exists ::env(QICK_VIVADO_OUTPUT)]} {
  set output_root [file normalize $::env(QICK_VIVADO_OUTPUT)]
} else {
  set output_root {C:/JeonghyunPark/Workspace/Vivado_Output}
}
set sim_dir [file join $output_root axis_buffer_ddr_sample_v2_sim]

file delete -force $sim_dir
file mkdir $sim_dir
cd $sim_dir

exec xvlog -sv \
  [file join $src_dir axis_buffer_ddr_sample_v2.sv] \
  [file join $src_dir tb_axis_buffer_ddr_sample_v2.sv]
exec xelab tb_axis_buffer_ddr_sample_v2 -s ddr_sample_v2_sim
exec xsim ddr_sample_v2_sim -runall
