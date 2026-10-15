# Package only the new output stage. All generated IP/project files stay in BUILD.
set package_root [file join $output_dir ip_repo axis_output_sum_v1]
create_project sum_package [file join $output_dir sum_package] -part xczu49dr-ffvf1760-2-e
add_files -norecurse [file join $repo_dir qick firmware ip axis_output_sum_v1 src axis_output_sum_v1.sv]
set_property top axis_output_sum_v1 [current_fileset]
update_compile_order -fileset sources_1
ipx::package_project -root_dir $package_root -vendor QSTL -library User -taxonomy /UserIP -import_files -set_current true
set core [ipx::current_core]
set_property name axis_output_sum_v1 $core
set_property display_name {Fixed-latency signed DAC output sum} $core
set_property version 1.0 $core
set_property supported_families {zynquplus Production} $core
set clock [ipx::get_bus_interfaces aclk -of_objects $core]
set_property value {s0_axis:s1_axis:m_axis} [ipx::get_bus_parameters ASSOCIATED_BUSIF -of_objects $clock]
foreach {param value} {N_PTS 16 PIPELINE_CYCLES 2} {
    set item [ipx::get_user_parameters $param -of_objects $core]
    set_property value_validation_type list $item
    set_property value_validation_list $value $item
}
set item [ipx::get_user_parameters BYPASS -of_objects $core]
set_property value_validation_type list $item
set_property value_validation_list {0 1} $item
ipx::create_xgui_files $core
ipx::update_checksums $core
ipx::check_integrity $core
ipx::save_core $core
close_project
