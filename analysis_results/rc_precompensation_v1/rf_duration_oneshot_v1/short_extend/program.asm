
// Program

                                    regwi 0, $22, 170009122;//freq = 170009122
                                    regwi 0, $23, 0;//phase = 0
                                    regwi 0, $25, 2000;//gain = 2000
                                    regwi 0, $26, 589854;//phrst| stdysel | mode | | outsel = 0b01001 | length = 30 
                                    synci 200;
                                    regwi 1, $10, 733007751;//target = 0xaec33e1f
                                    bitwi 1, $10, $10 << 2;
                                    mathi 1, $10, $10 + 3;
                                    regwi 1, $11, 0;//reserved_start = 0x00000000
                                    regwi 1, $12, 0;//duration = 0x00000000
                                    regwi 1, $13, 0;//step = 0x00000000
                                    regwi 1, $14, 19857408;//control = 0x012f0000
                                    regwi 1, $15, 0;//t = 0
                                    set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                                    regwi 1, $26, 733007751;//target = 0xaec33e1f
                                    bitwi 1, $26, $26 << 2;
                                    mathi 1, $26, $26 + 3;
                                    regwi 1, $27, 0;//reserved_start = 0x00000000
                                    regwi 1, $28, 0;//duration = 0x00000000
                                    regwi 1, $29, 0;//step = 0x00000000
                                    regwi 1, $30, 19857408;//control = 0x012f0000
                                    regwi 1, $31, 0;//t = 0
                                    set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                                    synci 100;
                                    regwi 0, $13, 0;
                                    regwi 0, $14, 800;//final acquisition count
                                    regwi 1, $10, 204;//initialize DMEM sweep state (0, 0, 0, 'target')
                                    memwi 1, $10, 4085;//store initial DMEM sweep state (0, 0, 0, 'target')
                                    regwi 1, $2, -41822;//initialize direct sweep state (1, 0, 0, 'step')
                                    regwi 1, $12, 244;//initialize DMEM sweep state ('bias_t', 0, 'bias_t_target_code')
                                    memwi 1, $12, 4095;//store initial DMEM sweep state ('bias_t', 0, 'bias_t_target_code')
                                    regwi 1, $28, 0;//initialize DMEM sweep state ('bias_t', 1, 'bias_t_target_code')
                                    memwi 1, $28, 4094;//store initial DMEM sweep state ('bias_t', 1, 'bias_t_target_code')
                                    regwi 1, $3, 323;//initialize direct sweep state ('event_time', 'awg', 1, 0, 0)
                                    regwi 1, $4, 323;//initialize direct sweep state ('event_time', 'awg', 1, 1, 0)
                                    regwi 1, $5, 391;//initialize direct sweep state ('event_time', 'awg', 2, 0, 0)
                                    regwi 1, $6, 391;//initialize direct sweep state ('event_time', 'awg', 2, 1, 0)
                                    regwi 1, $7, 684;//initialize direct sweep state ('event_time', 'awg', 3, 0, 0)
                                    regwi 1, $8, 684;//initialize direct sweep state ('event_time', 'awg', 3, 1, 0)
                                    regwi 1, $9, 752;//initialize direct sweep state ('event_time', 'awg', 4, 0, 0)
                                    regwi 1, $31, 752;//initialize DMEM sweep state ('event_time', 'awg', 4, 1, 0)
                                    memwi 1, $31, 4093;//store initial DMEM sweep state ('event_time', 'awg', 4, 1, 0)
                                    regwi 0, $2, 41;//initialize direct sweep state ('event_time', 'rf_stop', 0)
                                    regwi 1, $15, 1052;//initialize DMEM sweep state ('event_time', 'bias_pre_zero', 0)
                                    memwi 1, $15, 4092;//store initial DMEM sweep state ('event_time', 'bias_pre_zero', 0)
                                    regwi 1, $31, 1052;//initialize DMEM sweep state ('event_time', 'bias_pre_zero', 1)
                                    memwi 1, $31, 4091;//store initial DMEM sweep state ('event_time', 'bias_pre_zero', 1)
                                    regwi 0, $1, 136;//initialize ('rf_point_table', 0, 'duration') DMEM pointer
                                    regwi 1, $1, 16;//initialize RAMP-rate table pointer
                                    memr 1, $12, $1;//load initial RAMP-rate row ('bias_t', 0, 'bias_t_target_code')
                                    memwi 1, $12, 4095;//store initial RAMP-rate row ('bias_t', 0, 'bias_t_target_code')
                                    mathi 1, $1, $1 + 1;//advance initial RAMP-rate column 0
                                    memr 1, $11, $1;//load initial RAMP-rate axis coefficient
                                    memwi 1, $11, 4089;//store initial RAMP-rate axis coefficient
                                    mathi 1, $1, $1 + 1;//advance initial RAMP-rate column 1
                                    memr 1, $11, $1;//load initial RAMP-rate axis coefficient
                                    memwi 1, $11, 4088;//store initial RAMP-rate axis coefficient
                                    mathi 1, $1, $1 + 1;//advance initial RAMP-rate column 2
                                    memr 1, $28, $1;//load initial RAMP-rate row ('bias_t', 1, 'bias_t_target_code')
                                    memwi 1, $28, 4094;//store initial RAMP-rate row ('bias_t', 1, 'bias_t_target_code')
                                    mathi 1, $1, $1 + 1;//advance initial RAMP-rate column 3
                                    memr 1, $11, $1;//load initial RAMP-rate axis coefficient
                                    memwi 1, $11, 4087;//store initial RAMP-rate axis coefficient
                                    mathi 1, $1, $1 + 1;//advance initial RAMP-rate column 4
                                    memr 1, $11, $1;//load initial RAMP-rate axis coefficient
                                    memwi 1, $11, 4086;//store initial RAMP-rate axis coefficient
                                    mathi 1, $1, $1 + 1;//advance initial RAMP-rate column 5
                                    memwi 1, $1, 4084;//store initial RAMP-rate table pointer
                                    regwi 0, $3, 19;//initialize sweep axis 0 counter
                                    regwi 0, $4, 19;//initialize sweep axis 1 counter
                                    synci 128;
                                    synci 128;  //initial lookahead for SquarePulse and external markers
FINE_TUNE_POINT:                    regwi 0, $15, 1;
FINE_TUNE_REP:                      regwi 0, $16, 64;//out = 0b0000000001000000
                                    seti 7, 0, $16, 11;//ch =0 out = $16 @t = 11
                                    seti 7, 0, $0, 41;//ch =0 out = 0 @t = 11
                                    memri 1, $10, 4085;//load spilled awg_0:set_0:target
                                    regwi 1, $11, 0;//awg_0:set_0:reserved_start
                                    regwi 1, $12, 0;//awg_0:set_0:duration
                                    regwi 1, $13, 0;//awg_0:set_0:step
                                    regwi 1, $14, 16842752;//awg_0:set_0:control
                                    regwi 1, $15, 0;//set_0 t
                                    set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_0
                                    regwi 1, $26, 1073741773;//awg_1:set_0:target
                                    bitwi 1, $26, $26 << 2;
                                    regwi 1, $27, 0;//awg_1:set_0:reserved_start
                                    regwi 1, $28, 0;//awg_1:set_0:duration
                                    regwi 1, $29, 0;//awg_1:set_0:step
                                    regwi 1, $30, 16842752;//awg_1:set_0:control
                                    regwi 1, $31, 0;//set_0 t
                                    set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_0
                                    regwi 0, $22, 170009122;//freq = 170009122
                                    regwi 0, $23, 0;//phase = 0
                                    regwi 0, $25, 2000;//gain = 2000
                                    regwi 0, $26, 589854;//phrst| stdysel | mode | | outsel = 0b01001 | length = 30 
                                    memr 0, $26, $1;//load swept rf_duration from DMEM
                                    regwi 0, $27, 11;//RF duration-sweep start
                                    set 0, 0, $22, $23, $0, $25, $26, $27;//RF duration-sweep start
                                    regwi 1, $10, 1073741722;//awg_0:ramp_0_to_1:target
                                    bitwi 1, $10, $10 << 2;
                                    regwi 1, $11, 0;//awg_0:ramp_0_to_1:reserved_start
                                    regwi 1, $12, 960;//awg_0:ramp_0_to_1:duration
                                    bitwi 1, $13, $2 & 16777215;//awg_0:ramp_0_to_1:step
                                    regwi 1, $14, 16908288;//awg_0:ramp_0_to_1:control
                                    mathi 1, $15, $3 + 0;//copy swept ramp_0_to_1 t
                                    set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_0_to_1
                                    regwi 1, $26, 204;//awg_1:ramp_0_to_1:target
                                    regwi 1, $27, 0;//awg_1:ramp_0_to_1:reserved_start
                                    regwi 1, $28, 960;//awg_1:ramp_0_to_1:duration
                                    regwi 1, $29, 27881;//awg_1:ramp_0_to_1:step
                                    regwi 1, $30, 16908288;//awg_1:ramp_0_to_1:control
                                    mathi 1, $31, $4 + 0;//copy swept ramp_0_to_1 t
                                    set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_0_to_1
                                    regwi 1, $10, 1073741722;//awg_0:set_1:target
                                    bitwi 1, $10, $10 << 2;
                                    regwi 1, $11, 0;//awg_0:set_1:reserved_start
                                    regwi 1, $12, 0;//awg_0:set_1:duration
                                    regwi 1, $13, 0;//awg_0:set_1:step
                                    regwi 1, $14, 16842752;//awg_0:set_1:control
                                    mathi 1, $15, $5 + 0;//copy swept set_1 t
                                    set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_1
                                    regwi 1, $26, 204;//awg_1:set_1:target
                                    regwi 1, $27, 0;//awg_1:set_1:reserved_start
                                    regwi 1, $28, 0;//awg_1:set_1:duration
                                    regwi 1, $29, 0;//awg_1:set_1:step
                                    regwi 1, $30, 16842752;//awg_1:set_1:control
                                    mathi 1, $31, $6 + 0;//copy swept set_1 t
                                    set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_1
                                    regwi 1, $10, 0;//awg_0:ramp_1_to_2:target
                                    regwi 1, $11, 0;//awg_0:ramp_1_to_2:reserved_start
                                    regwi 1, $12, 960;//awg_0:ramp_1_to_2:duration
                                    regwi 1, $13, 27881;//awg_0:ramp_1_to_2:step
                                    regwi 1, $14, 16908288;//awg_0:ramp_1_to_2:control
                                    mathi 1, $15, $7 + 0;//copy swept ramp_1_to_2 t
                                    set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_1_to_2
                                    regwi 1, $26, 0;//awg_1:ramp_1_to_2:target
                                    regwi 1, $27, 0;//awg_1:ramp_1_to_2:reserved_start
                                    regwi 1, $28, 960;//awg_1:ramp_1_to_2:duration
                                    regwi 1, $29, 16763276;//awg_1:ramp_1_to_2:step
                                    regwi 1, $30, 16908288;//awg_1:ramp_1_to_2:control
                                    mathi 1, $31, $8 + 0;//copy swept ramp_1_to_2 t
                                    set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_1_to_2
                                    regwi 1, $10, 0;//awg_0:set_2:target
                                    regwi 1, $11, 0;//awg_0:set_2:reserved_start
                                    regwi 1, $12, 0;//awg_0:set_2:duration
                                    regwi 1, $13, 0;//awg_0:set_2:step
                                    regwi 1, $14, 16842752;//awg_0:set_2:control
                                    mathi 1, $15, $9 + 0;//copy swept set_2 t
                                    set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_2
                                    regwi 1, $26, 0;//awg_1:set_2:target
                                    regwi 1, $27, 0;//awg_1:set_2:reserved_start
                                    regwi 1, $28, 0;//awg_1:set_2:duration
                                    regwi 1, $29, 0;//awg_1:set_2:step
                                    regwi 1, $30, 16842752;//awg_1:set_2:control
                                    memri 1, $31, 4093;//load swept set_2 t
                                    set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_2
                                    regwi 1, $10, 0;//awg_0:bias_t_pre_zero:target
                                    regwi 1, $11, 0;//awg_0:bias_t_pre_zero:reserved_start
                                    regwi 1, $12, 0;//awg_0:bias_t_pre_zero:duration
                                    regwi 1, $13, 0;//awg_0:bias_t_pre_zero:step
                                    regwi 1, $14, 16842752;//awg_0:bias_t_pre_zero:control
                                    memri 1, $15, 4092;//load swept bias_t_pre_zero t
                                    set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:bias_t_pre_zero
                                    regwi 1, $26, 0;//awg_1:bias_t_pre_zero:target
                                    regwi 1, $27, 0;//awg_1:bias_t_pre_zero:reserved_start
                                    regwi 1, $28, 0;//awg_1:bias_t_pre_zero:duration
                                    regwi 1, $29, 0;//awg_1:bias_t_pre_zero:step
                                    regwi 1, $30, 16842752;//awg_1:bias_t_pre_zero:control
                                    memri 1, $31, 4091;//load swept bias_t_pre_zero t
                                    set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:bias_t_pre_zero
                                    synci 1158;
                                    synci 1;    //common Bias-T guard after pre-compensation zero
                                    regwi 1, $10, 0;//clear fixed-time Bias-T active marker
                                    memwi 1, $10, 4090;//store cleared fixed-time Bias-T active marker
                                    regwi 1, $11, 0;//awg_0 fixed-time Bias-T reserved_start
                                    regwi 1, $12, 0;//awg_0 fixed-time Bias-T duration
                                    regwi 1, $13, 0;//awg_0 fixed-time Bias-T step
                                    regwi 1, $14, 16842752;//awg_0 fixed-time Bias-T control
                                    regwi 1, $15, 64;//awg_0 common fixed-time Bias-T start offset
                                    memri 1, $12, 4095;//load fixed-time Bias-T target for awg_0
                                    condj 1, $12, ==, $0, @BIAS_T_FIXED_TIME_DONE_0;//skip zero-area fixed-time Bias-T output awg_0
                                    mathi 1, $10, $12 + 0;//apply fixed-time Bias-T target for awg_0
                                    set 0, 1, $10, $11, $12, $13, $14, $15;//start fixed-time Bias-T compensation on awg_0
                                    regwi 1, $10, 0;//awg_0 return to zero after fixed-time Bias-T
                                    regwi 1, $15, 364;//awg_0 fixed-time Bias-T stop offset
                                    set 0, 1, $10, $11, $12, $13, $14, $15;//finish fixed-time Bias-T compensation on awg_0
                                    memwi 1, $12, 4090;//mark fixed-time Bias-T active for awg_0
BIAS_T_FIXED_TIME_DONE_0:           mathi 1, $12, $12 + 0;//fixed-time Bias-T output awg_0 complete
                                    regwi 1, $27, 0;//awg_1 fixed-time Bias-T reserved_start
                                    regwi 1, $28, 0;//awg_1 fixed-time Bias-T duration
                                    regwi 1, $29, 0;//awg_1 fixed-time Bias-T step
                                    regwi 1, $30, 16842752;//awg_1 fixed-time Bias-T control
                                    regwi 1, $31, 64;//awg_1 common fixed-time Bias-T start offset
                                    memri 1, $28, 4094;//load fixed-time Bias-T target for awg_1
                                    condj 1, $28, ==, $0, @BIAS_T_FIXED_TIME_DONE_1;//skip zero-area fixed-time Bias-T output awg_1
                                    mathi 1, $26, $28 + 0;//apply fixed-time Bias-T target for awg_1
                                    set 1, 1, $26, $27, $28, $29, $30, $31;//start fixed-time Bias-T compensation on awg_1
                                    regwi 1, $26, 0;//awg_1 return to zero after fixed-time Bias-T
                                    regwi 1, $31, 364;//awg_1 fixed-time Bias-T stop offset
                                    set 1, 1, $26, $27, $28, $29, $30, $31;//finish fixed-time Bias-T compensation on awg_1
                                    memwi 1, $28, 4090;//mark fixed-time Bias-T active for awg_1
BIAS_T_FIXED_TIME_DONE_1:           mathi 1, $28, $28 + 0;//fixed-time Bias-T output awg_1 complete
                                    memri 1, $12, 4090;//load fixed-time Bias-T active marker
                                    condj 1, $12, ==, $0, @BIAS_T_FIXED_TIME_NO_ACTIVE_OUTPUT;//skip fixed-time Bias-T advance when all areas are zero
                                    regwi 1, $12, 364;//fixed-time Bias-T latest stop offset
                                    sync 1, $12;//advance to fixed-time Bias-T stop
BIAS_T_FIXED_TIME_NO_ACTIVE_OUTPUT: mathi 1, $12, $12 + 0;//fixed-time Bias-T compensation complete
                                    synci 1;    //separate Bias-T stop from the next sweep point
                                    synci 64;   //lookahead for per-repeat AWG RC reset
                                    regwi 1, $10, 733007751;//target = 0xaec33e1f
                                    bitwi 1, $10, $10 << 2;
                                    mathi 1, $10, $10 + 3;
                                    regwi 1, $11, 0;//reserved_start = 0x00000000
                                    regwi 1, $12, 0;//duration = 0x00000000
                                    regwi 1, $13, 0;//step = 0x00000000
                                    regwi 1, $14, 19857408;//control = 0x012f0000
                                    regwi 1, $15, 0;//t = 0
                                    set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                                    regwi 1, $26, 733007751;//target = 0xaec33e1f
                                    bitwi 1, $26, $26 << 2;
                                    mathi 1, $26, $26 + 3;
                                    regwi 1, $27, 0;//reserved_start = 0x00000000
                                    regwi 1, $28, 0;//duration = 0x00000000
                                    regwi 1, $29, 0;//step = 0x00000000
                                    regwi 1, $30, 19857408;//control = 0x012f0000
                                    regwi 1, $31, 0;//t = 0
                                    set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                                    synci 15;   //flush per-repeat AWG RC reset
                                    synci 20;   //post Bias-T shot recovery
                                    regwi 0, $16, 64;//out = 0b0000000001000000
                                    seti 7, 0, $16, 0;//ch =0 out = $16 @t = 0
                                    seti 7, 0, $0, 30;//ch =0 out = 0 @t = 0
                                    synci 31;   //complete external end marker
                                    mathi 0, $13, $13 + 1;
                                    condj 0, $13, ==, $14, @DEFER_FINAL_ACQUISITION_COUNT;
                                    memwi 0, $13, 1;
DEFER_FINAL_ACQUISITION_COUNT:      loopnz 0, $15, @FINE_TUNE_REP;
                                    loopnz 0, $4, @FINE_TUNE_ADVANCE_1;
                                    regwi 0, $4, 19;//reload sweep axis 1 counter
                                    mathi 0, $1, $1 + -19;//reset axis 1 ('rf_point_table', 0, 'duration') pointer
                                    memri 1, $11, 4088;//load RAMP-rate reset axis 1 coefficient
                                    memri 1, $12, 4095;//load RAMP-rate reset state ('bias_t', 0, 'bias_t_target_code')
                                    math 1, $12, $12 + $11;//RAMP-rate reset axis 1 ('bias_t', 0, 'bias_t_target_code')
                                    memwi 1, $12, 4095;//store RAMP-rate reset state ('bias_t', 0, 'bias_t_target_code')
                                    memri 1, $11, 4086;//load RAMP-rate reset axis 1 coefficient
                                    memri 1, $28, 4094;//load RAMP-rate reset state ('bias_t', 1, 'bias_t_target_code')
                                    math 1, $28, $28 + $11;//RAMP-rate reset axis 1 ('bias_t', 1, 'bias_t_target_code')
                                    memwi 1, $28, 4094;//store RAMP-rate reset state ('bias_t', 1, 'bias_t_target_code')
                                    mathi 1, $3, $3 + -95;//reset axis 1 ('event_time', 'awg', 1, 0, 0)
                                    mathi 1, $4, $4 + -95;//reset axis 1 ('event_time', 'awg', 1, 1, 0)
                                    mathi 1, $5, $5 + -95;//reset axis 1 ('event_time', 'awg', 2, 0, 0)
                                    mathi 1, $6, $6 + -95;//reset axis 1 ('event_time', 'awg', 2, 1, 0)
                                    mathi 1, $7, $7 + -95;//reset axis 1 ('event_time', 'awg', 3, 0, 0)
                                    mathi 1, $8, $8 + -95;//reset axis 1 ('event_time', 'awg', 3, 1, 0)
                                    mathi 1, $9, $9 + -95;//reset axis 1 ('event_time', 'awg', 4, 0, 0)
                                    memri 1, $31, 4093;//load reset axis 1 ('event_time', 'awg', 4, 1, 0)
                                    mathi 1, $31, $31 + -95;//reset axis 1 ('event_time', 'awg', 4, 1, 0)
                                    memwi 1, $31, 4093;//store reset axis 1 ('event_time', 'awg', 4, 1, 0)
                                    mathi 0, $2, $2 + -95;//reset axis 1 ('event_time', 'rf_stop', 0)
                                    memri 1, $15, 4092;//load reset axis 1 ('event_time', 'bias_pre_zero', 0)
                                    mathi 1, $15, $15 + -95;//reset axis 1 ('event_time', 'bias_pre_zero', 0)
                                    memwi 1, $15, 4092;//store reset axis 1 ('event_time', 'bias_pre_zero', 0)
                                    memri 1, $31, 4091;//load reset axis 1 ('event_time', 'bias_pre_zero', 1)
                                    mathi 1, $31, $31 + -95;//reset axis 1 ('event_time', 'bias_pre_zero', 1)
                                    memwi 1, $31, 4091;//store reset axis 1 ('event_time', 'bias_pre_zero', 1)
                                    loopnz 0, $3, @FINE_TUNE_ADVANCE_0;
                                    waiti 0, 0; //wait for experiment epilogue
                                    memwi 0, $13, 1;
                                    end ;
FINE_TUNE_ADVANCE_0:                memri 1, $10, 4085;//load advance axis 0 (0, 0, 0, 'target')
                                    mathi 1, $10, $10 + 20;//advance axis 0 (0, 0, 0, 'target')
                                    memwi 1, $10, 4085;//store advance axis 0 (0, 0, 0, 'target')
                                    mathi 1, $2, $2 + -1482;//advance axis 0 (1, 0, 0, 'step')
                                    memri 1, $1, 4084;//load RAMP-rate axis 0 table pointer
                                    memr 1, $12, $1;//load axis 0 advance RAMP-rate row ('bias_t', 0, 'bias_t_target_code')
                                    memwi 1, $12, 4095;//store axis 0 advance RAMP-rate row ('bias_t', 0, 'bias_t_target_code')
                                    mathi 1, $1, $1 + 1;//advance axis 0 advance RAMP-rate column 0
                                    memr 1, $11, $1;//load axis 0 advance RAMP-rate axis coefficient
                                    memwi 1, $11, 4089;//store axis 0 advance RAMP-rate axis coefficient
                                    mathi 1, $1, $1 + 1;//advance axis 0 advance RAMP-rate column 1
                                    memr 1, $11, $1;//load axis 0 advance RAMP-rate axis coefficient
                                    memwi 1, $11, 4088;//store axis 0 advance RAMP-rate axis coefficient
                                    mathi 1, $1, $1 + 1;//advance axis 0 advance RAMP-rate column 2
                                    memr 1, $28, $1;//load axis 0 advance RAMP-rate row ('bias_t', 1, 'bias_t_target_code')
                                    memwi 1, $28, 4094;//store axis 0 advance RAMP-rate row ('bias_t', 1, 'bias_t_target_code')
                                    mathi 1, $1, $1 + 1;//advance axis 0 advance RAMP-rate column 3
                                    memr 1, $11, $1;//load axis 0 advance RAMP-rate axis coefficient
                                    memwi 1, $11, 4087;//store axis 0 advance RAMP-rate axis coefficient
                                    mathi 1, $1, $1 + 1;//advance axis 0 advance RAMP-rate column 4
                                    memr 1, $11, $1;//load axis 0 advance RAMP-rate axis coefficient
                                    memwi 1, $11, 4086;//store axis 0 advance RAMP-rate axis coefficient
                                    mathi 1, $1, $1 + 1;//advance axis 0 advance RAMP-rate column 5
                                    memwi 1, $1, 4084;//store axis 0 advance RAMP-rate table pointer
                                    condj 0, $0, ==, $0, @FINE_TUNE_POINT;
FINE_TUNE_ADVANCE_1:                mathi 0, $1, $1 + 1;//advance axis 1 ('rf_point_table', 0, 'duration') pointer
                                    memri 1, $11, 4089;//load RAMP-rate advance axis 1 coefficient
                                    memri 1, $12, 4095;//load RAMP-rate advance state ('bias_t', 0, 'bias_t_target_code')
                                    math 1, $12, $12 + $11;//RAMP-rate advance axis 1 ('bias_t', 0, 'bias_t_target_code')
                                    memwi 1, $12, 4095;//store RAMP-rate advance state ('bias_t', 0, 'bias_t_target_code')
                                    memri 1, $11, 4087;//load RAMP-rate advance axis 1 coefficient
                                    memri 1, $28, 4094;//load RAMP-rate advance state ('bias_t', 1, 'bias_t_target_code')
                                    math 1, $28, $28 + $11;//RAMP-rate advance axis 1 ('bias_t', 1, 'bias_t_target_code')
                                    memwi 1, $28, 4094;//store RAMP-rate advance state ('bias_t', 1, 'bias_t_target_code')
                                    mathi 1, $3, $3 + 5;//advance axis 1 ('event_time', 'awg', 1, 0, 0)
                                    mathi 1, $4, $4 + 5;//advance axis 1 ('event_time', 'awg', 1, 1, 0)
                                    mathi 1, $5, $5 + 5;//advance axis 1 ('event_time', 'awg', 2, 0, 0)
                                    mathi 1, $6, $6 + 5;//advance axis 1 ('event_time', 'awg', 2, 1, 0)
                                    mathi 1, $7, $7 + 5;//advance axis 1 ('event_time', 'awg', 3, 0, 0)
                                    mathi 1, $8, $8 + 5;//advance axis 1 ('event_time', 'awg', 3, 1, 0)
                                    mathi 1, $9, $9 + 5;//advance axis 1 ('event_time', 'awg', 4, 0, 0)
                                    memri 1, $31, 4093;//load advance axis 1 ('event_time', 'awg', 4, 1, 0)
                                    mathi 1, $31, $31 + 5;//advance axis 1 ('event_time', 'awg', 4, 1, 0)
                                    memwi 1, $31, 4093;//store advance axis 1 ('event_time', 'awg', 4, 1, 0)
                                    mathi 0, $2, $2 + 5;//advance axis 1 ('event_time', 'rf_stop', 0)
                                    memri 1, $15, 4092;//load advance axis 1 ('event_time', 'bias_pre_zero', 0)
                                    mathi 1, $15, $15 + 5;//advance axis 1 ('event_time', 'bias_pre_zero', 0)
                                    memwi 1, $15, 4092;//store advance axis 1 ('event_time', 'bias_pre_zero', 0)
                                    memri 1, $31, 4091;//load advance axis 1 ('event_time', 'bias_pre_zero', 1)
                                    mathi 1, $31, $31 + 5;//advance axis 1 ('event_time', 'bias_pre_zero', 1)
                                    memwi 1, $31, 4091;//store advance axis 1 ('event_time', 'bias_pre_zero', 1)
                                    condj 0, $0, ==, $0, @FINE_TUNE_POINT;