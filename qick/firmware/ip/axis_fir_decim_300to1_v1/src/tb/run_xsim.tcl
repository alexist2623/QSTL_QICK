# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
# Run from any directory with:
#   vivado -mode batch -source qick/firmware/ip/axis_fir_decim_300to1_v1/src/tb/run_xsim.tcl

set TB_DIR [file normalize [file dirname [info script]]]
set IP_ROOT [file normalize [file join $TB_DIR .. ..]]
set SRC_DIR [file join $IP_ROOT src]
set VECTOR_DIR [file normalize [file join $IP_ROOT vectors]]
set OUT_DIR [file normalize "C:/JeonghyunPark/Workspace/Vivado_Output/axis_fir_decim_300to1_v1_sim"]
set TOP_TB tb_axis_fir_decim_300to1_v1

file mkdir $OUT_DIR
cd $OUT_DIR

proc run_cmd {cmd} {
    puts "RUN: $cmd"
    if {[catch {exec {*}$cmd} result]} {
        puts $result
        exit 1
    }
    puts $result
}

run_cmd [list xvlog -sv \
    [file join $SRC_DIR fir_decim_300to1_coeffs_pkg.sv] \
    [file join $SRC_DIR axis_fir_decim_stage.sv] \
    [file join $SRC_DIR axis_fir_decim_300to1_v1.sv] \
    [file join $SRC_DIR tb tb_axis_fir_decim_300to1_v1.sv]]
run_cmd [list xelab $TOP_TB -s fir_decim_sim]
run_cmd [list xsim fir_decim_sim -runall -testplusarg "VECTOR_DIR=$VECTOR_DIR"]
