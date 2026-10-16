# Run with Vivado 2023.1 from a private build directory:
# vivado -mode batch -source <this-file> -log <private-log> -journal <private-journal>
# Only the new 2.0 component metadata is saved. The v1 directory is never opened.
set ip_root [file normalize [file dirname [info script]]]
set component [file join $ip_root component.xml]
ipx::open_core $component
set core [ipx::current_core]
if {[get_property VLNV $core] ne "QICK:QICK:axis_tproc64x32_x8:2.0"} {
    error "Unexpected core identity; refusing to package a different IP"
}
set_property core_revision 1 $core
ipx::update_checksums $core
ipx::check_integrity $core
ipx::save_core $core
puts "TPROC_V2_PACKAGE_PASS [get_property VLNV $core]"
