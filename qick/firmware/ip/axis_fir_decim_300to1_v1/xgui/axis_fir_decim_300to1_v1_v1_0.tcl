# Definitional proc to organize widgets for parameters.
proc init_gui { IPINST } {
  ipgui::add_param $IPINST -name "Component_Name"
  #Adding Page
  set Page_0 [ipgui::add_page $IPINST -name "Page 0"]
  ipgui::add_param $IPINST -name "ACC_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "COEF_WIDTH_PARAM" -parent ${Page_0}
  ipgui::add_param $IPINST -name "DECIM0" -parent ${Page_0}
  ipgui::add_param $IPINST -name "DECIM1" -parent ${Page_0}
  ipgui::add_param $IPINST -name "DECIM2" -parent ${Page_0}
  ipgui::add_param $IPINST -name "LANE_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "M_AXIS_DATA_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "OUT_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "S_AXIS_DATA_WIDTH" -parent ${Page_0}


}

proc update_PARAM_VALUE.ACC_WIDTH { PARAM_VALUE.ACC_WIDTH } {
	# Procedure called to update ACC_WIDTH when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.ACC_WIDTH { PARAM_VALUE.ACC_WIDTH } {
	# Procedure called to validate ACC_WIDTH
	return true
}

proc update_PARAM_VALUE.COEF_WIDTH_PARAM { PARAM_VALUE.COEF_WIDTH_PARAM } {
	# Procedure called to update COEF_WIDTH_PARAM when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.COEF_WIDTH_PARAM { PARAM_VALUE.COEF_WIDTH_PARAM } {
	# Procedure called to validate COEF_WIDTH_PARAM
	return true
}

proc update_PARAM_VALUE.DECIM0 { PARAM_VALUE.DECIM0 } {
	# Procedure called to update DECIM0 when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.DECIM0 { PARAM_VALUE.DECIM0 } {
	# Procedure called to validate DECIM0
	return true
}

proc update_PARAM_VALUE.DECIM1 { PARAM_VALUE.DECIM1 } {
	# Procedure called to update DECIM1 when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.DECIM1 { PARAM_VALUE.DECIM1 } {
	# Procedure called to validate DECIM1
	return true
}

proc update_PARAM_VALUE.DECIM2 { PARAM_VALUE.DECIM2 } {
	# Procedure called to update DECIM2 when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.DECIM2 { PARAM_VALUE.DECIM2 } {
	# Procedure called to validate DECIM2
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

proc update_PARAM_VALUE.OUT_WIDTH { PARAM_VALUE.OUT_WIDTH } {
	# Procedure called to update OUT_WIDTH when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.OUT_WIDTH { PARAM_VALUE.OUT_WIDTH } {
	# Procedure called to validate OUT_WIDTH
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

proc update_MODELPARAM_VALUE.DECIM0 { MODELPARAM_VALUE.DECIM0 PARAM_VALUE.DECIM0 } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.DECIM0}] ${MODELPARAM_VALUE.DECIM0}
}

proc update_MODELPARAM_VALUE.DECIM1 { MODELPARAM_VALUE.DECIM1 PARAM_VALUE.DECIM1 } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.DECIM1}] ${MODELPARAM_VALUE.DECIM1}
}

proc update_MODELPARAM_VALUE.DECIM2 { MODELPARAM_VALUE.DECIM2 PARAM_VALUE.DECIM2 } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.DECIM2}] ${MODELPARAM_VALUE.DECIM2}
}

proc update_MODELPARAM_VALUE.COEF_WIDTH_PARAM { MODELPARAM_VALUE.COEF_WIDTH_PARAM PARAM_VALUE.COEF_WIDTH_PARAM } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.COEF_WIDTH_PARAM}] ${MODELPARAM_VALUE.COEF_WIDTH_PARAM}
}

proc update_MODELPARAM_VALUE.ACC_WIDTH { MODELPARAM_VALUE.ACC_WIDTH PARAM_VALUE.ACC_WIDTH } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.ACC_WIDTH}] ${MODELPARAM_VALUE.ACC_WIDTH}
}

proc update_MODELPARAM_VALUE.OUT_WIDTH { MODELPARAM_VALUE.OUT_WIDTH PARAM_VALUE.OUT_WIDTH } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.OUT_WIDTH}] ${MODELPARAM_VALUE.OUT_WIDTH}
}

