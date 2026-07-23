# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
set tb_dir [file normalize [file dirname [info script]]]
set src_dir [file normalize [file join $tb_dir ..]]
if {[info exists ::env(QICK_VIVADO_OUTPUT)]} {
  set output_root [file normalize $::env(QICK_VIVADO_OUTPUT)]
} else {
  set output_root {C:/JeonghyunPark/Workspace/Vivado_Output}
}
set sim_dir [file join $output_root axis_notch_decim_1m_to50k_v1_sim]

file delete -force $sim_dir
file mkdir $sim_dir
file copy -force [file join $tb_dir input.hex] [file join $sim_dir input.hex]
file copy -force [file join $tb_dir expected.hex] [file join $sim_dir expected.hex]
cd $sim_dir

exec xvlog -sv -d SIM_MODEL \
  [file join $src_dir notch_decim_1m_to50k_coeffs_pkg.sv] \
  [file join $src_dir axis_fir_decim_stage.sv] \
  [file join $src_dir dsp48e2_sos_pipeline.sv] \
  [file join $src_dir axis_sos_iq_engine.sv] \
  [file join $src_dir axis_notch_decim_1m_to50k_v1.sv] \
  [file join $tb_dir tb_axis_notch_decim_1m_to50k_v1.sv]
exec xelab tb_axis_notch_decim_1m_to50k_v1 -s notch_decim_sim
exec xsim notch_decim_sim -runall
