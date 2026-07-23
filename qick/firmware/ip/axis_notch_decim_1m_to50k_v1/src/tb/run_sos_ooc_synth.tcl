# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
set tb_dir [file normalize [file dirname [info script]]]
set src_dir [file normalize [file join $tb_dir ..]]
if {[info exists ::env(QICK_VIVADO_OUTPUT)]} {
  set output_root [file normalize $::env(QICK_VIVADO_OUTPUT)]
} else {
  set output_root {C:/JeonghyunPark/Workspace/Vivado_Output}
}
set run_dir [file join $output_root axis_notch_decim_sos_ooc]

file delete -force $run_dir
file mkdir $run_dir
cd $run_dir

read_verilog -sv [file join $src_dir notch_decim_1m_to50k_coeffs_pkg.sv]
read_verilog -sv [file join $src_dir dsp48e2_sos_pipeline.sv]
read_verilog -sv [file join $src_dir axis_sos_iq_engine.sv]
synth_design -top axis_sos_iq_engine -part xczu49dr-ffvf1760-2-e -mode out_of_context

create_clock -name aclk -period 3.333 [get_ports aclk]
set_clock_uncertainty 0.100 [get_clocks aclk]
opt_design

write_checkpoint -force [file join $run_dir axis_sos_iq_engine_post_synth.dcp]
report_utilization -hierarchical -file [file join $run_dir utilization_hierarchical.rpt]
report_timing_summary -delay_type min_max -max_paths 20 -file [file join $run_dir timing_summary.rpt]
report_timing -delay_type max -max_paths 50 -sort_by group -file [file join $run_dir timing_paths.rpt]
report_drc -file [file join $run_dir drc.rpt]

set dsp_cells [get_cells -hierarchical -filter {REF_NAME == DSP48E2}]
set latch_cells [get_cells -hierarchical -filter {PRIMITIVE_TYPE =~ REGISTER.LATCH.*}]
set summary_file [open [file join $run_dir structural_summary.txt] w]
puts $summary_file "DSP48E2_COUNT=[llength $dsp_cells]"
puts $summary_file "LATCH_COUNT=[llength $latch_cells]"
puts $summary_file "WORST_SLACK_NS=[get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]"
puts $summary_file "DSP48E2_CELLS:"
foreach cell $dsp_cells {
  puts $summary_file $cell
}
close $summary_file
