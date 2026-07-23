# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
# Run from this directory with Vivado 2023.1:
#   vivado -mode batch -source package_ip.tcl

set IP_ROOT [file normalize [file dirname [info script]]]
set TMP_PROJ [file join $IP_ROOT ".ip_packager_tmp"]

file delete -force $TMP_PROJ
create_project axis_notch_decim_1m_to50k_v1_pack $TMP_PROJ -part xczu49dr-ffvf1760-2-e
add_files -norecurse [list \
  [file join $IP_ROOT "src/notch_decim_1m_to50k_coeffs_pkg.sv"] \
  [file join $IP_ROOT "src/axis_fir_decim_stage.sv"] \
  [file join $IP_ROOT "src/dsp48e2_sos_pipeline.sv"] \
  [file join $IP_ROOT "src/axis_sos_iq_engine.sv"] \
  [file join $IP_ROOT "src/axis_notch_decim_1m_to50k_v1.sv"] \
]
set_property top axis_notch_decim_1m_to50k_v1 [current_fileset]
update_compile_order -fileset sources_1

ipx::package_project -root_dir $IP_ROOT -vendor QICK -library QICK -taxonomy /QICK/Readout -import_files -force
set core [ipx::current_core]
set_property name axis_notch_decim_1m_to50k_v1 $core
set_property display_name {AXIS Notch Decimator 1M to 50k V1} $core
set_property description {Continuous two-stage Kaiser FIR decimator from 1 MSPS to 50 kSPS with two cascaded notches at each of 20 mains harmonics.} $core
set_property version 1.0 $core
set_property vendor_display_name {Quantum Instrumentation Control Kit} $core
set_property company_url {https://github.com/openquantumhardware/qick/} $core

set aclk_busif [ipx::get_bus_interfaces aclk -of_objects $core]
set associated_busif [ipx::get_bus_parameters ASSOCIATED_BUSIF -of_objects $aclk_busif]
set_property value {s_axis:m_axis} $associated_busif

ipx::check_integrity $core -quiet
ipx::save_core $core
close_project
file delete -force $TMP_PROJ
