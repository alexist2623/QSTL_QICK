# Definitional proc to organize widgets for parameters.
proc init_gui { IPINST } {
  ipgui::add_param $IPINST -name "Component_Name"
  #Adding Page
  set Page_0 [ipgui::add_page $IPINST -name "Page 0"]
  ipgui::add_param $IPINST -name "DECIMATION_PARAM" -parent ${Page_0}
  ipgui::add_param $IPINST -name "LANE_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "M_AXIS_DATA_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "S_AXIS_DATA_WIDTH" -parent ${Page_0}


}

proc update_PARAM_VALUE.DECIMATION_PARAM { PARAM_VALUE.DECIMATION_PARAM } {
	# Procedure called to update DECIMATION_PARAM when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.DECIMATION_PARAM { PARAM_VALUE.DECIMATION_PARAM } {
	# Procedure called to validate DECIMATION_PARAM
	return true
}

proc update_PARAM_VALUE.LANE_WIDTH { PARAM_VALUE.LANE_WIDTH } {
	# Procedure called to update LANE_WIDTH when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.LANE_WIDTH { PARAM_VALUE.LANE_WIDTH } {
	# Procedure called to validate LANE_WIDTH
	return true
}

proc update_PARAM_VALUE.M_AXIS_DATA_WIDTH { PARAM_VALUE.M_AXIS_DATA_WIDTH } {
	# Procedure called to update M_AXIS_DATA_WIDTH when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.M_AXIS_DATA_WIDTH { PARAM_VALUE.M_AXIS_DATA_WIDTH } {
	# Procedure called to validate M_AXIS_DATA_WIDTH
	return true
}

proc update_PARAM_VALUE.S_AXIS_DATA_WIDTH { PARAM_VALUE.S_AXIS_DATA_WIDTH } {
	# Procedure called to update S_AXIS_DATA_WIDTH when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.S_AXIS_DATA_WIDTH { PARAM_VALUE.S_AXIS_DATA_WIDTH } {
	# Procedure called to validate S_AXIS_DATA_WIDTH
	return true
}


proc update_MODELPARAM_VALUE.S_AXIS_DATA_WIDTH { MODELPARAM_VALUE.S_AXIS_DATA_WIDTH PARAM_VALUE.S_AXIS_DATA_WIDTH } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.S_AXIS_DATA_WIDTH}] ${MODELPARAM_VALUE.S_AXIS_DATA_WIDTH}
}

proc update_MODELPARAM_VALUE.M_AXIS_DATA_WIDTH { MODELPARAM_VALUE.M_AXIS_DATA_WIDTH PARAM_VALUE.M_AXIS_DATA_WIDTH } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.M_AXIS_DATA_WIDTH}] ${MODELPARAM_VALUE.M_AXIS_DATA_WIDTH}
}

proc update_MODELPARAM_VALUE.LANE_WIDTH { MODELPARAM_VALUE.LANE_WIDTH PARAM_VALUE.LANE_WIDTH } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.LANE_WIDTH}] ${MODELPARAM_VALUE.LANE_WIDTH}
}

proc update_MODELPARAM_VALUE.DECIMATION_PARAM { MODELPARAM_VALUE.DECIMATION_PARAM PARAM_VALUE.DECIMATION_PARAM } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.DECIMATION_PARAM}] ${MODELPARAM_VALUE.DECIMATION_PARAM}
}
