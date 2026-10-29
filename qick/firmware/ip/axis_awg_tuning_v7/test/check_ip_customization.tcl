# Update/check this new package only; all project/catalog output stays outside
# Git in the required fresh probe directory. No synthesis or hardware access.
if {$argc != 1} { error "Usage: -tclargs F:/Vivado_Output/a6_probe" }
set package_dir [file normalize [file join [file dirname [info script]] ..]]
set ip_root [file dirname $package_dir]
set probe_dir [file normalize [lindex $argv 0]]
if {[file exists $probe_dir] && [llength [glob -nocomplain -directory $probe_dir *]]} {
    error "Refusing to overwrite probe evidence: $probe_dir"
}
file mkdir $probe_dir
cd $probe_dir
ipx::open_core [file join $package_dir component.xml]
set core [ipx::current_core]
if {[get_property NAME $core] ne "axis_awg_tuning_v7"} { error "Wrong package" }
set_property core_revision 7 $core
ipx::update_checksums $core
ipx::check_integrity -quiet $core
ipx::save_core $core
ipx::unload_core $core
create_project -in_memory -part xczu49dr-ffvf1760-2-e
set_property ip_repo_paths $ip_root [current_fileset]
update_ip_catalog -rebuild
create_bd_design v7_customization
set cell [create_bd_cell -type ip -vlnv QICK:QICK:axis_awg_tuning_v7:1.0 awg]
if {[get_property CONFIG.DC_AREA_BITS $cell] != 48} { error "Wrong default area width" }
if {[get_property CONFIG.EXTRA_Y_PIPE_STAGES $cell] != 3} { error "Wrong common latency default" }
set_property CONFIG.DC_AREA_BITS 48 $cell
set_property CONFIG.EXTRA_Y_PIPE_STAGES 3 $cell
puts "PASS_IP_CUSTOMIZATION_V7_COMMON11_SELECTED48"
close_project
exit 0
