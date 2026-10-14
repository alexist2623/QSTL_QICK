# Probe the actual Vivado IP catalog/customization path without a full build.
# The production package supports only the selected 48-bit area width.
set root [file normalize [file join [file dirname [info script]] .. ..]]
if {$argc != 1} { error "Usage: -tclargs FRESH_PROBE_DIRECTORY" }
set probe_dir [file normalize [lindex $argv 0]]
if {[file exists $probe_dir] && [llength [glob -nocomplain -directory $probe_dir *]]} {
    error "Refusing to overwrite probe evidence: $probe_dir"
}
file mkdir $probe_dir
cd $probe_dir
create_project -in_memory -part xczu49dr-ffvf1760-2-e
set_property ip_repo_paths $root [current_fileset]
update_ip_catalog -rebuild
create_bd_design v3_customization
set cell [create_bd_cell -type ip -vlnv QICK:QICK:axis_awg_tuning_v3:1.0 awg]
if {[get_property CONFIG.DC_AREA_BITS $cell] != 48} { error "Wrong default area width" }
set_property CONFIG.DC_AREA_BITS 48 $cell
puts "PASS_IP_CUSTOMIZATION_DEFAULT_AND_EXPLICIT_48"
foreach width {32 64} {
    if {![catch {set_property CONFIG.DC_AREA_BITS $width $cell} message]} {
        error "Production package unexpectedly accepted area width $width"
    }
    puts "PASS_IP_CUSTOMIZATION_REJECT_$width"
}
if {[get_property CONFIG.DC_AREA_BITS $cell] != 48} { error "Invalid width changed valid setting" }
puts "PASS_IP_CUSTOMIZATION_FINAL_48"
close_project
exit 0
