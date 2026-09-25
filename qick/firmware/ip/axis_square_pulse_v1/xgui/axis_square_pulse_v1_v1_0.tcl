proc init_gui {IPINST} {
    ipgui::add_param $IPINST -name Component_Name
    set page [ipgui::add_page $IPINST -name {Square DDS}]
    foreach name {N_PTS B CMD_WIDTH} {ipgui::add_param $IPINST -name $name -parent $page}
}
proc update_PARAM_VALUE.N_PTS {PARAM_VALUE.N_PTS} {}
proc update_PARAM_VALUE.B {PARAM_VALUE.B} {}
proc update_PARAM_VALUE.CMD_WIDTH {PARAM_VALUE.CMD_WIDTH} {}
proc validate_PARAM_VALUE.N_PTS {PARAM_VALUE.N_PTS} {return true}
proc validate_PARAM_VALUE.B {PARAM_VALUE.B} {return true}
proc validate_PARAM_VALUE.CMD_WIDTH {PARAM_VALUE.CMD_WIDTH} {return true}
proc update_MODELPARAM_VALUE.N_PTS {MODELPARAM_VALUE.N_PTS PARAM_VALUE.N_PTS} {
    set_property value [get_property value ${PARAM_VALUE.N_PTS}] ${MODELPARAM_VALUE.N_PTS}
}
proc update_MODELPARAM_VALUE.B {MODELPARAM_VALUE.B PARAM_VALUE.B} {
    set_property value [get_property value ${PARAM_VALUE.B}] ${MODELPARAM_VALUE.B}
}
proc update_MODELPARAM_VALUE.CMD_WIDTH {MODELPARAM_VALUE.CMD_WIDTH PARAM_VALUE.CMD_WIDTH} {
    set_property value [get_property value ${PARAM_VALUE.CMD_WIDTH}] ${MODELPARAM_VALUE.CMD_WIDTH}
}

proc update_PARAM_VALUE.RC_PRECOMP_VERSION { PARAM_VALUE.RC_PRECOMP_VERSION } {}
proc validate_PARAM_VALUE.RC_PRECOMP_VERSION { PARAM_VALUE.RC_PRECOMP_VERSION } { return true }
proc update_MODELPARAM_VALUE.RC_PRECOMP_VERSION { MODELPARAM_VALUE.RC_PRECOMP_VERSION PARAM_VALUE.RC_PRECOMP_VERSION } {
  set_property value [get_property value ${PARAM_VALUE.RC_PRECOMP_VERSION}] ${MODELPARAM_VALUE.RC_PRECOMP_VERSION}
}
