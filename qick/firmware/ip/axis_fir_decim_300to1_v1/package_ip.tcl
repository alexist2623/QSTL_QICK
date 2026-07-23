# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
# Package axis_fir_decim_300to1_v1 as a QICK Vivado IP.
# Run from this directory with:
#   vivado -mode batch -source package_ip.tcl

set IP_ROOT [file normalize [file dirname [info script]]]
set TMP_PROJ [file join $IP_ROOT ".ip_packager_tmp"]

file delete -force $TMP_PROJ
create_project axis_fir_decim_300to1_v1_pack $TMP_PROJ -part xczu49dr-ffvf1760-2-e
add_files -norecurse [list \
  [file join $IP_ROOT "src/fir_decim_300to1_coeffs_pkg.sv"] \
  [file join $IP_ROOT "src/axis_fir_decim_stage.sv"] \
  [file join $IP_ROOT "src/axis_fir_decim_300to1_v1.sv"] \
]
set_property top axis_fir_decim_300to1_v1 [current_fileset]
update_compile_order -fileset sources_1

ipx::package_project -root_dir $IP_ROOT -vendor QICK -library QICK -taxonomy /QICK/Readout -import_files -force
set core [ipx::current_core]
set_property name axis_fir_decim_300to1_v1 $core
set_property display_name {AXIS FIR Decimator 300 to 1 V1} $core
set_property description {Two-lane 32-bit AXIS FIR anti-alias decimator for 300 MSPS to 1 MSPS DDR capture.} $core
set_property version 1.0 $core
set_property vendor_display_name {Quantum Instrumentation Control Kit} $core
set_property company_url {https://github.com/openquantumhardware/qick/} $core

ipx::check_integrity $core -quiet
ipx::save_core $core
close_project
file delete -force $TMP_PROJ
