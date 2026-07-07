# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
set script_dir [file dirname [file normalize [info script]]]
set src_dir [file normalize [file join $script_dir ..]]

if {[info exists ::env(XILINX_VIVADO)]} {
   set vivado_bin [file normalize [file join $::env(XILINX_VIVADO) bin]]
} else {
   set vivado_bin {}
}

proc xsim_tool {tool_name} {
   global vivado_bin tcl_platform

   if {$vivado_bin ne ""} {
      if {$tcl_platform(platform) eq "windows"} {
         set candidate [file join $vivado_bin "${tool_name}.bat"]
      } else {
         set candidate [file join $vivado_bin $tool_name]
      }

      if {[file exists $candidate]} {
         return $candidate
      }
   }

   return $tool_name
}

proc run_cmd {cmd} {
   puts [join $cmd " "]
   exec {*}$cmd >@ stdout 2>@ stderr
}

set xvlog [xsim_tool xvlog]
set xelab [xsim_tool xelab]
set xsim  [xsim_tool xsim]

if {$vivado_bin ne ""} {
   set vivado_root [file dirname $vivado_bin]
   set glbl_src [file join $vivado_root data verilog src glbl.v]
} else {
   set glbl_src {}
}

set sources [list \
   [file join $src_dir axi_slv_awg_tuning_v1.sv] \
   [file join $src_dir awg_tuning_ctrl.sv] \
   [file join $src_dir axis_awg_tuning_v1.sv] \
   [file join $script_dir tb_simple.sv] \
   [file join $script_dir tb_simple_p3.sv] \
]
if {$glbl_src ne "" && [file exists $glbl_src]} {
   lappend sources $glbl_src
}

set xvlog_cmd [list $xvlog --relax --sv -work xil_defaultlib]
foreach src $sources {
   lappend xvlog_cmd [file normalize $src]
}
run_cmd $xvlog_cmd

if {[info exists ::env(TB_TOP)]} {
   set tb_top $::env(TB_TOP)
} else {
   set tb_top xil_defaultlib.tb_simple
}

set tb_top_leaf [string map {"xil_defaultlib." "" "." "_"} $tb_top]
set snapshot "${tb_top_leaf}_behav"

run_cmd [list $xelab --debug typical --relax --mt 2 -L xil_defaultlib -L unisims_ver $tb_top xil_defaultlib.glbl -snapshot $snapshot -log "elaborate_${tb_top_leaf}.log"]

set run_tcl [file normalize [file join [pwd] tb_simple_run.tcl]]
set fh [open $run_tcl w]
puts $fh "run all"
puts $fh "quit"
close $fh

run_cmd [list $xsim $snapshot -tclbatch $run_tcl -log "simulate_${tb_top_leaf}.log"]
