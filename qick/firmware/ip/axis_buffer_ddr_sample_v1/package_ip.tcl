# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
# Package axis_buffer_ddr_sample_v1 as a QICK Vivado IP.
# Run from this directory with:
#   vivado -mode batch -source package_ip.tcl

set IP_ROOT [file normalize [file dirname [info script]]]
set TMP_PROJ [file join $IP_ROOT ".ip_packager_tmp"]

file delete -force $TMP_PROJ
create_project axis_buffer_ddr_sample_v1_pack $TMP_PROJ -part xczu28dr-ffvg1517-2-e
add_files -norecurse [file join $IP_ROOT "src/axis_buffer_ddr_sample_v1.sv"]
set_property top axis_buffer_ddr_sample_v1 [current_fileset]
update_compile_order -fileset sources_1

ipx::package_project -root_dir $IP_ROOT -vendor QICK -library QICK -taxonomy /QICK/Buffer -import_files -force
set core [ipx::current_core]
set_property name axis_buffer_ddr_sample_v1 $core
set_property display_name {AXIS Buffer DDR Sample V1} $core
set_property description {Sample-count trigger-based 32-bit AXIS to 256-bit DDR capture buffer with trigger-aligned sample decimation and internal CDC.} $core
set_property version 1.0 $core
set_property vendor_display_name {Quantum Instrumentation Control Kit} $core
set_property company_url {https://github.com/openquantumhardware/qick/} $core

ipx::save_core $core
close_project
file delete -force $TMP_PROJ
