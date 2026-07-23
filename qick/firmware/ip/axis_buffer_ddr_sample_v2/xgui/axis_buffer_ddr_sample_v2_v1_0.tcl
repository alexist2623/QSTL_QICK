# Definitional proc to organize widgets for parameters.
proc init_gui { IPINST } {
  ipgui::add_param $IPINST -name "Component_Name"
  #Adding Page
  set Page_0 [ipgui::add_page $IPINST -name "Page 0"]
  ipgui::add_param $IPINST -name "DEFAULT_TRIGGER_DELAY_SAMPLES" -parent ${Page_0}
  ipgui::add_param $IPINST -name "FIFO_ADDR_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "ID_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "M_AXI_DATA_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "S_AXIS_DATA_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "TARGET_SLAVE_BASE_ADDR" -parent ${Page_0}


}

proc update_PARAM_VALUE.DEFAULT_TRIGGER_DELAY_SAMPLES { PARAM_VALUE.DEFAULT_TRIGGER_DELAY_SAMPLES } {
	# Procedure called to update DEFAULT_TRIGGER_DELAY_SAMPLES when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.DEFAULT_TRIGGER_DELAY_SAMPLES { PARAM_VALUE.DEFAULT_TRIGGER_DELAY_SAMPLES } {
	# Procedure called to validate DEFAULT_TRIGGER_DELAY_SAMPLES
	return true
}

proc update_PARAM_VALUE.FIFO_ADDR_WIDTH { PARAM_VALUE.FIFO_ADDR_WIDTH } {
	# Procedure called to update FIFO_ADDR_WIDTH when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.FIFO_ADDR_WIDTH { PARAM_VALUE.FIFO_ADDR_WIDTH } {
	# Procedure called to validate FIFO_ADDR_WIDTH
	return true
}

proc update_PARAM_VALUE.ID_WIDTH { PARAM_VALUE.ID_WIDTH } {
	# Procedure called to update ID_WIDTH when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.ID_WIDTH { PARAM_VALUE.ID_WIDTH } {
	# Procedure called to validate ID_WIDTH
	return true
}

proc update_PARAM_VALUE.M_AXI_DATA_WIDTH { PARAM_VALUE.M_AXI_DATA_WIDTH } {
	# Procedure called to update M_AXI_DATA_WIDTH when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.M_AXI_DATA_WIDTH { PARAM_VALUE.M_AXI_DATA_WIDTH } {
	# Procedure called to validate M_AXI_DATA_WIDTH
	return true
}

proc update_PARAM_VALUE.S_AXIS_DATA_WIDTH { PARAM_VALUE.S_AXIS_DATA_WIDTH } {
	# Procedure called to update S_AXIS_DATA_WIDTH when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.S_AXIS_DATA_WIDTH { PARAM_VALUE.S_AXIS_DATA_WIDTH } {
	# Procedure called to validate S_AXIS_DATA_WIDTH
	return true
}

proc update_PARAM_VALUE.TARGET_SLAVE_BASE_ADDR { PARAM_VALUE.TARGET_SLAVE_BASE_ADDR } {
	# Procedure called to update TARGET_SLAVE_BASE_ADDR when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.TARGET_SLAVE_BASE_ADDR { PARAM_VALUE.TARGET_SLAVE_BASE_ADDR } {
	# Procedure called to validate TARGET_SLAVE_BASE_ADDR
	return true
}


proc update_MODELPARAM_VALUE.TARGET_SLAVE_BASE_ADDR { MODELPARAM_VALUE.TARGET_SLAVE_BASE_ADDR PARAM_VALUE.TARGET_SLAVE_BASE_ADDR } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.TARGET_SLAVE_BASE_ADDR}] ${MODELPARAM_VALUE.TARGET_SLAVE_BASE_ADDR}
}

proc update_MODELPARAM_VALUE.ID_WIDTH { MODELPARAM_VALUE.ID_WIDTH PARAM_VALUE.ID_WIDTH } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.ID_WIDTH}] ${MODELPARAM_VALUE.ID_WIDTH}
}

proc update_MODELPARAM_VALUE.S_AXIS_DATA_WIDTH { MODELPARAM_VALUE.S_AXIS_DATA_WIDTH PARAM_VALUE.S_AXIS_DATA_WIDTH } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.S_AXIS_DATA_WIDTH}] ${MODELPARAM_VALUE.S_AXIS_DATA_WIDTH}
}

proc update_MODELPARAM_VALUE.M_AXI_DATA_WIDTH { MODELPARAM_VALUE.M_AXI_DATA_WIDTH PARAM_VALUE.M_AXI_DATA_WIDTH } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.M_AXI_DATA_WIDTH}] ${MODELPARAM_VALUE.M_AXI_DATA_WIDTH}
}

proc update_MODELPARAM_VALUE.FIFO_ADDR_WIDTH { MODELPARAM_VALUE.FIFO_ADDR_WIDTH PARAM_VALUE.FIFO_ADDR_WIDTH } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.FIFO_ADDR_WIDTH}] ${MODELPARAM_VALUE.FIFO_ADDR_WIDTH}
}

proc update_MODELPARAM_VALUE.DEFAULT_TRIGGER_DELAY_SAMPLES { MODELPARAM_VALUE.DEFAULT_TRIGGER_DELAY_SAMPLES PARAM_VALUE.DEFAULT_TRIGGER_DELAY_SAMPLES } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.DEFAULT_TRIGGER_DELAY_SAMPLES}] ${MODELPARAM_VALUE.DEFAULT_TRIGGER_DELAY_SAMPLES}
}
