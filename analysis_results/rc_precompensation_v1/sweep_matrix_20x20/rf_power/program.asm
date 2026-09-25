
// Program

                                    regwi 0, $22, 170009122;//freq = 170009122
                                    regwi 0, $23, 0;//phase = 0
                                    regwi 0, $25, 1002;//gain = 1002
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
                                    regwi 1, $1, 204;//initialize direct sweep state (0, 0, 0, 'target')
                                    regwi 1, $2, -41822;//initialize direct sweep state (1, 0, 0, 'step')
                                    regwi 1, $12, 264;//initialize DMEM sweep state ('bias_t', 0, 'bias_t_target_code')
                                    memwi 1, $12, 4095;//store initial DMEM sweep state ('bias_t', 0, 'bias_t_target_code')
                                    regwi 1, $28, -20;//initialize DMEM sweep state ('bias_t', 1, 'bias_t_target_code')
                                    memwi 1, $28, 4094;//store initial DMEM sweep state ('bias_t', 1, 'bias_t_target_code')
                                    regwi 0, $1, 16;//initialize ('rf_point_table', 0, 'rf_gen_0_single', 'gain') DMEM pointer
                                    regwi 0, $2, 19;//initialize sweep axis 0 counter
                                    regwi 0, $3, 19;//initialize sweep axis 1 counter
                                    synci 128;
                                    synci 128;  //initial lookahead for SquarePulse and external markers
FINE_TUNE_POINT:                    regwi 0, $15, 1;
FINE_TUNE_REP:                      regwi 0, $16, 64;//out = 0b0000000001000000
                                    seti 7, 0, $16, 11;//ch =0 out = $16 @t = 11
                                    seti 7, 0, $0, 41;//ch =0 out = 0 @t = 11
                                    mathi 1, $10, $1 + 0;//awg_0:set_0:target
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
                                    regwi 0, $25, 1002;//gain = 1002
                                    regwi 0, $26, 589854;//phrst| stdysel | mode | | outsel = 0b01001 | length = 30 
                                    memr 0, $25, $1;//load swept rf_gain from DMEM
                                    regwi 0, $27, 11;//RF duration-sweep start
                                    set 0, 0, $22, $23, $0, $25, $26, $27;//RF duration-sweep start
                                    regwi 1, $10, 1073741722;//awg_0:ramp_0_to_1:target
                                    bitwi 1, $10, $10 << 2;
                                    regwi 1, $11, 0;//awg_0:ramp_0_to_1:reserved_start
                                    regwi 1, $12, 960;//awg_0:ramp_0_to_1:duration
                                    bitwi 1, $13, $2 & 16777215;//awg_0:ramp_0_to_1:step
                                    regwi 1, $14, 16908288;//awg_0:ramp_0_to_1:control
                                    regwi 1, $15, 293;//ramp_0_to_1 t
                                    set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_0_to_1
                                    regwi 1, $26, 204;//awg_1:ramp_0_to_1:target
                                    regwi 1, $27, 0;//awg_1:ramp_0_to_1:reserved_start
                                    regwi 1, $28, 960;//awg_1:ramp_0_to_1:duration
                                    regwi 1, $29, 27881;//awg_1:ramp_0_to_1:step
                                    regwi 1, $30, 16908288;//awg_1:ramp_0_to_1:control
                                    regwi 1, $31, 293;//ramp_0_to_1 t
                                    set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_0_to_1
                                    regwi 1, $10, 1073741722;//awg_0:set_1:target
                                    bitwi 1, $10, $10 << 2;
                                    regwi 1, $11, 0;//awg_0:set_1:reserved_start
                                    regwi 1, $12, 0;//awg_0:set_1:duration
                                    regwi 1, $13, 0;//awg_0:set_1:step
                                    regwi 1, $14, 16842752;//awg_0:set_1:control
                                    regwi 1, $15, 361;//set_1 t
                                    set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_1
                                    regwi 1, $26, 204;//awg_1:set_1:target
                                    regwi 1, $27, 0;//awg_1:set_1:reserved_start
                                    regwi 1, $28, 0;//awg_1:set_1:duration
                                    regwi 1, $29, 0;//awg_1:set_1:step
                                    regwi 1, $30, 16842752;//awg_1:set_1:control
                                    regwi 1, $31, 361;//set_1 t
                                    set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_1
                                    regwi 1, $10, 0;//awg_0:ramp_1_to_2:target
                                    regwi 1, $11, 0;//awg_0:ramp_1_to_2:reserved_start
                                    regwi 1, $12, 960;//awg_0:ramp_1_to_2:duration
                                    regwi 1, $13, 27881;//awg_0:ramp_1_to_2:step
                                    regwi 1, $14, 16908288;//awg_0:ramp_1_to_2:control
                                    regwi 1, $15, 654;//ramp_1_to_2 t
                                    set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_1_to_2
                                    regwi 1, $26, 0;//awg_1:ramp_1_to_2:target
                                    regwi 1, $27, 0;//awg_1:ramp_1_to_2:reserved_start
                                    regwi 1, $28, 960;//awg_1:ramp_1_to_2:duration
                                    regwi 1, $29, 16763276;//awg_1:ramp_1_to_2:step
                                    regwi 1, $30, 16908288;//awg_1:ramp_1_to_2:control
                                    regwi 1, $31, 654;//ramp_1_to_2 t
                                    set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_1_to_2
                                    regwi 1, $10, 0;//awg_0:set_2:target
                                    regwi 1, $11, 0;//awg_0:set_2:reserved_start
                                    regwi 1, $12, 0;//awg_0:set_2:duration
                                    regwi 1, $13, 0;//awg_0:set_2:step
                                    regwi 1, $14, 16842752;//awg_0:set_2:control
                                    regwi 1, $15, 722;//set_2 t
                                    set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_2
                                    regwi 1, $26, 0;//awg_1:set_2:target
                                    regwi 1, $27, 0;//awg_1:set_2:reserved_start
                                    regwi 1, $28, 0;//awg_1:set_2:duration
                                    regwi 1, $29, 0;//awg_1:set_2:step
                                    regwi 1, $30, 16842752;//awg_1:set_2:control
                                    regwi 1, $31, 722;//set_2 t
                                    set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_2
                                    regwi 1, $10, 0;//awg_0:bias_t_pre_zero:target
                                    regwi 1, $11, 0;//awg_0:bias_t_pre_zero:reserved_start
                                    regwi 1, $12, 0;//awg_0:bias_t_pre_zero:duration
                                    regwi 1, $13, 0;//awg_0:bias_t_pre_zero:step
                                    regwi 1, $14, 16842752;//awg_0:bias_t_pre_zero:control
                                    regwi 1, $15, 1022;//bias_t_pre_zero t
                                    set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:bias_t_pre_zero
                                    regwi 1, $26, 0;//awg_1:bias_t_pre_zero:target
                                    regwi 1, $27, 0;//awg_1:bias_t_pre_zero:reserved_start
                                    regwi 1, $28, 0;//awg_1:bias_t_pre_zero:duration
                                    regwi 1, $29, 0;//awg_1:bias_t_pre_zero:step
                                    regwi 1, $30, 16842752;//awg_1:bias_t_pre_zero:control
                                    regwi 1, $31, 1022;//bias_t_pre_zero t
                                    set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:bias_t_pre_zero
                                    synci 1033;
                                    synci 1;    //common Bias-T guard after pre-compensation zero
                                    regwi 1, $10, 0;//clear fixed-time Bias-T active marker
                                    memwi 1, $10, 4093;//store cleared fixed-time Bias-T active marker
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
                                    memwi 1, $12, 4093;//mark fixed-time Bias-T active for awg_0
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
                                    memwi 1, $28, 4093;//mark fixed-time Bias-T active for awg_1
BIAS_T_FIXED_TIME_DONE_1:           mathi 1, $28, $28 + 0;//fixed-time Bias-T output awg_1 complete
                                    memri 1, $12, 4093;//load fixed-time Bias-T active marker
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
                                    loopnz 0, $3, @FINE_TUNE_ADVANCE_1;
                                    regwi 0, $3, 19;//reload sweep axis 1 counter
                                    mathi 0, $1, $1 + -19;//reset axis 1 ('rf_point_table', 0, 'rf_gen_0_single', 'gain') pointer
                                    loopnz 0, $2, @FINE_TUNE_ADVANCE_0;
                                    waiti 0, 0; //wait for experiment epilogue
                                    memwi 0, $13, 1;
                                    end ;
FINE_TUNE_ADVANCE_0:                mathi 1, $1, $1 + 20;//advance axis 0 (0, 0, 0, 'target')
                                    mathi 1, $2, $2 + -1482;//advance axis 0 (1, 0, 0, 'step')
                                    memri 1, $12, 4095;//load advance axis 0 ('bias_t', 0, 'bias_t_target_code')
                                    mathi 1, $12, $12 + -20;//advance axis 0 ('bias_t', 0, 'bias_t_target_code')
                                    memwi 1, $12, 4095;//store advance axis 0 ('bias_t', 0, 'bias_t_target_code')
                                    condj 0, $0, ==, $0, @FINE_TUNE_POINT;
FINE_TUNE_ADVANCE_1:                mathi 0, $1, $1 + 1;//advance axis 1 ('rf_point_table', 0, 'rf_gen_0_single', 'gain') pointer
                                    condj 0, $0, ==, $0, @FINE_TUNE_POINT;