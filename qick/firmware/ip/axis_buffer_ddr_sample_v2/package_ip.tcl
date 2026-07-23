# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
# Run from this directory with Vivado 2023.1:
#   vivado -mode batch -source package_ip.tcl

set IP_ROOT [file normalize [file dirname [info script]]]
set TMP_PROJ [file join $IP_ROOT ".ip_packager_tmp"]

file delete -force $TMP_PROJ
create_project axis_buffer_ddr_sample_v2_pack $TMP_PROJ -part xczu49dr-ffvf1760-2-e
add_files -norecurse [file join $IP_ROOT "src/axis_buffer_ddr_sample_v2.sv"]
set_property top axis_buffer_ddr_sample_v2 [current_fileset]
update_compile_order -fileset sources_1

ipx::package_project -root_dir $IP_ROOT -vendor QICK -library QICK -taxonomy /QICK/Buffer -import_files -force
set core [ipx::current_core]
set_property name axis_buffer_ddr_sample_v2 $core
set_property display_name {AXIS Buffer DDR Sample V2} $core
set_property description {Sample-count 32-bit AXIS to 256-bit DDR capture buffer with internal CDC and programmable valid-sample trigger delay.} $core
set_property version 1.0 $core
set_property vendor_display_name {Quantum Instrumentation Control Kit} $core
set_property company_url {https://github.com/openquantumhardware/qick/} $core

ipx::check_integrity $core -quiet
ipx::save_core $core
close_project
file delete -force $TMP_PROJ
