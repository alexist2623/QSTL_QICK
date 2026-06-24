# Definitional proc to organize widgets for parameters.
proc init_gui { IPINST } {
  ipgui::add_param $IPINST -name "Component_Name"
  set Page_0 [ipgui::add_page $IPINST -name "Page 0"]
  ipgui::add_param $IPINST -name "N_PTS" -parent ${Page_0}
  ipgui::add_param $IPINST -name "B" -parent ${Page_0}
  ipgui::add_param $IPINST -name "FRAC" -parent ${Page_0}
  ipgui::add_param $IPINST -name "CMD_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "STEP_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "DURATION_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "FIXED_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "EXTRA_Y_PIPE_STAGES" -parent ${Page_0}
}

proc update_PARAM_VALUE.N_PTS { PARAM_VALUE.N_PTS } {}
proc validate_PARAM_VALUE.N_PTS { PARAM_VALUE.N_PTS } { return true }

proc update_PARAM_VALUE.B { PARAM_VALUE.B } {}
proc validate_PARAM_VALUE.B { PARAM_VALUE.B } { return true }

proc update_PARAM_VALUE.FRAC { PARAM_VALUE.FRAC } {}
proc validate_PARAM_VALUE.FRAC { PARAM_VALUE.FRAC } { return true }

proc update_PARAM_VALUE.CMD_WIDTH { PARAM_VALUE.CMD_WIDTH } {}
proc validate_PARAM_VALUE.CMD_WIDTH { PARAM_VALUE.CMD_WIDTH } { return true }

proc update_PARAM_VALUE.STEP_WIDTH { PARAM_VALUE.STEP_WIDTH } {}
proc validate_PARAM_VALUE.STEP_WIDTH { PARAM_VALUE.STEP_WIDTH } { return true }

proc update_PARAM_VALUE.DURATION_WIDTH { PARAM_VALUE.DURATION_WIDTH } {}
proc validate_PARAM_VALUE.DURATION_WIDTH { PARAM_VALUE.DURATION_WIDTH } { return true }

proc update_PARAM_VALUE.FIXED_WIDTH { PARAM_VALUE.FIXED_WIDTH } {}
proc validate_PARAM_VALUE.FIXED_WIDTH { PARAM_VALUE.FIXED_WIDTH } { return true }

proc update_PARAM_VALUE.EXTRA_Y_PIPE_STAGES { PARAM_VALUE.EXTRA_Y_PIPE_STAGES } {}
proc validate_PARAM_VALUE.EXTRA_Y_PIPE_STAGES { PARAM_VALUE.EXTRA_Y_PIPE_STAGES } { return true }

proc update_MODELPARAM_VALUE.N_PTS { MODELPARAM_VALUE.N_PTS PARAM_VALUE.N_PTS } {
  set_property value [get_property value ${PARAM_VALUE.N_PTS}] ${MODELPARAM_VALUE.N_PTS}
}

proc update_MODELPARAM_VALUE.B { MODELPARAM_VALUE.B PARAM_VALUE.B } {
  set_property value [get_property value ${PARAM_VALUE.B}] ${MODELPARAM_VALUE.B}
}

proc update_MODELPARAM_VALUE.FRAC { MODELPARAM_VALUE.FRAC PARAM_VALUE.FRAC } {
  set_property value [get_property value ${PARAM_VALUE.FRAC}] ${MODELPARAM_VALUE.FRAC}
}

proc update_MODELPARAM_VALUE.CMD_WIDTH { MODELPARAM_VALUE.CMD_WIDTH PARAM_VALUE.CMD_WIDTH } {
  set_property value [get_property value ${PARAM_VALUE.CMD_WIDTH}] ${MODELPARAM_VALUE.CMD_WIDTH}
}

proc update_MODELPARAM_VALUE.STEP_WIDTH { MODELPARAM_VALUE.STEP_WIDTH PARAM_VALUE.STEP_WIDTH } {
  set_property value [get_property value ${PARAM_VALUE.STEP_WIDTH}] ${MODELPARAM_VALUE.STEP_WIDTH}
}

proc update_MODELPARAM_VALUE.DURATION_WIDTH { MODELPARAM_VALUE.DURATION_WIDTH PARAM_VALUE.DURATION_WIDTH } {
  set_property value [get_property value ${PARAM_VALUE.DURATION_WIDTH}] ${MODELPARAM_VALUE.DURATION_WIDTH}
}

proc update_MODELPARAM_VALUE.FIXED_WIDTH { MODELPARAM_VALUE.FIXED_WIDTH PARAM_VALUE.FIXED_WIDTH } {
  set_property value [get_property value ${PARAM_VALUE.FIXED_WIDTH}] ${MODELPARAM_VALUE.FIXED_WIDTH}
}

proc update_MODELPARAM_VALUE.EXTRA_Y_PIPE_STAGES { MODELPARAM_VALUE.EXTRA_Y_PIPE_STAGES PARAM_VALUE.EXTRA_Y_PIPE_STAGES } {
  set_property value [get_property value ${PARAM_VALUE.EXTRA_Y_PIPE_STAGES}] ${MODELPARAM_VALUE.EXTRA_Y_PIPE_STAGES}
}
