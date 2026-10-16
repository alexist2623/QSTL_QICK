
// Program

                               synci 200;
                               regwi 1, $10, 366503876;//target = 0x57619f10
                               bitwi 1, $10, $10 << 2;
                               regwi 1, $11, 0; //reserved_start = 0x00000000
                               regwi 1, $12, 0; //duration = 0x00000000
                               regwi 1, $13, 0; //step = 0x00000000
                               regwi 1, $14, 19857408;//control = 0x012f0000
                               regwi 1, $15, 0; //t = 0
                               set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                               regwi 1, $26, 366503876;//target = 0x57619f10
                               bitwi 1, $26, $26 << 2;
                               regwi 1, $27, 0; //reserved_start = 0x00000000
                               regwi 1, $28, 0; //duration = 0x00000000
                               regwi 1, $29, 0; //step = 0x00000000
                               regwi 1, $30, 19857408;//control = 0x012f0000
                               regwi 1, $31, 0; //t = 0
                               set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                               synci 100;
                               synci 256;
                               regwi 1, $10, 0; //target = 0x00000000
                               regwi 1, $11, 0; //reserved_start = 0x00000000
                               regwi 1, $12, 0; //duration = 0x00000000
                               regwi 1, $13, 0; //step = 0x00000000
                               regwi 1, $14, 16842752;//control = 0x01010000
                               regwi 1, $15, 0; //t = 0
                               set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                               regwi 1, $26, 0; //target = 0x00000000
                               regwi 1, $27, 0; //reserved_start = 0x00000000
                               regwi 1, $28, 0; //duration = 0x00000000
                               regwi 1, $29, 0; //step = 0x00000000
                               regwi 1, $30, 16842752;//control = 0x01010000
                               regwi 1, $31, 0; //t = 0
                               set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                               synci 256;
                               regwi 1, $10, 0; //target = 0x00000000
                               regwi 1, $11, 0; //reserved_start = 0x00000000
                               regwi 1, $12, 0; //duration = 0x00000000
                               regwi 1, $13, 0; //step = 0x00000000
                               regwi 1, $14, 21168128;//control = 0x01430000
                               regwi 1, $15, 0; //t = 0
                               set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                               regwi 1, $26, 0; //target = 0x00000000
                               regwi 1, $27, 0; //reserved_start = 0x00000000
                               regwi 1, $28, 0; //duration = 0x00000000
                               regwi 1, $29, 0; //step = 0x00000000
                               regwi 1, $30, 21168128;//control = 0x01430000
                               regwi 1, $31, 0; //t = 0
                               set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                               synci 256;
                               regwi 0, $13, 0;
                               regwi 0, $14, 10000;//final acquisition count
                               regwi 1, $26, -16352;//initialize DMEM sweep state (1, 1, 0, 'target')
                               memwi 1, $26, 4091;//store initial DMEM sweep state (1, 1, 0, 'target')
                               regwi 1, $2, -893223;//initialize direct sweep state (1, 1, 0, 'step')
                               regwi 1, $3, -16352;//initialize direct sweep state (2, 1, 0, 'target')
                               regwi 1, $4, 0;  //initialize direct sweep state (3, 0, 0, 'step')
                               regwi 1, $5, 48; //initialize direct sweep state (3, 0, 0, 'duration')
                               regwi 1, $6, 91203801;//initialize direct sweep state (3, 1, 0, 'step')
                               regwi 1, $7, 48; //initialize direct sweep state (3, 1, 0, 'duration')
                               regwi 1, $8, 6305;//initialize direct sweep state ('event_time', 'awg', 4, 0, 0)
                               regwi 1, $9, 6305;//initialize direct sweep state ('event_time', 'awg', 4, 1, 0)
                               regwi 1, $15, 9305;//initialize DMEM sweep state ('event_time', 'bias_pre_zero', 0)
                               memwi 1, $15, 4095;//store initial DMEM sweep state ('event_time', 'bias_pre_zero', 0)
                               regwi 1, $31, 9305;//initialize DMEM sweep state ('event_time', 'bias_pre_zero', 1)
                               memwi 1, $31, 4094;//store initial DMEM sweep state ('event_time', 'bias_pre_zero', 1)
                               regwi 1, $1, 16; //initialize RAMP-rate table pointer
                               memr 1, $4, $1;  //load initial RAMP-rate row (3, 0, 0, 'step')
                               mathi 1, $1, $1 + 1;//advance initial RAMP-rate column 0
                               memr 1, $6, $1;  //load initial RAMP-rate row (3, 1, 0, 'step')
                               mathi 1, $1, $1 + 1;//advance initial RAMP-rate column 1
                               memr 1, $11, $1; //load initial RAMP-rate axis coefficient
                               memwi 1, $11, 4093;//store initial RAMP-rate axis coefficient
                               mathi 1, $1, $1 + 1;//advance initial RAMP-rate column 2
                               memr 1, $11, $1; //load initial RAMP-rate axis coefficient
                               memwi 1, $11, 4092;//store initial RAMP-rate axis coefficient
                               mathi 1, $1, $1 + 1;//advance initial RAMP-rate column 3
                               memwi 1, $1, 4090;//store initial RAMP-rate table pointer
                               regwi 0, $1, 99; //initialize sweep axis 0 counter
                               regwi 0, $2, 99; //initialize sweep axis 1 counter
                               synci 128;
FINE_TUNE_POINT:               regwi 0, $15, 0;
FINE_TUNE_REP:                 regwi 1, $10, 0; //awg_0:set_0:target
                               regwi 1, $11, 0; //awg_0:set_0:reserved_start
                               regwi 1, $12, 0; //awg_0:set_0:duration
                               regwi 1, $13, 0; //awg_0:set_0:step
                               regwi 1, $14, 16842752;//awg_0:set_0:control
                               regwi 1, $15, 0; //set_0 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_0
                               regwi 1, $26, 0; //awg_1:set_0:target
                               regwi 1, $27, 0; //awg_1:set_0:reserved_start
                               regwi 1, $28, 0; //awg_1:set_0:duration
                               regwi 1, $29, 0; //awg_1:set_0:step
                               regwi 1, $30, 16842752;//awg_1:set_0:control
                               regwi 1, $31, 0; //set_0 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_0
                               regwi 1, $10, 0; //awg_0:ramp_0_to_1:target
                               regwi 1, $11, 0; //awg_0:ramp_0_to_1:reserved_start
                               regwi 1, $12, 4800;//awg_0:ramp_0_to_1:duration
                               regwi 1, $13, 0; //awg_0:ramp_0_to_1:step
                               regwi 1, $14, 16908288;//awg_0:ramp_0_to_1:control
                               regwi 1, $15, 2993;//ramp_0_to_1 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_0_to_1
                               memri 1, $26, 4091;//load spilled awg_1:ramp_0_to_1:target
                               regwi 1, $27, 0; //awg_1:ramp_0_to_1:reserved_start
                               regwi 1, $28, 4800;//awg_1:ramp_0_to_1:duration
                               mathi 1, $29, $2 + 0;//awg_1:ramp_0_to_1:step
                               regwi 1, $30, 16908288;//awg_1:ramp_0_to_1:control
                               regwi 1, $31, 2993;//ramp_0_to_1 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_0_to_1
                               regwi 1, $10, 0; //awg_0:set_1:target
                               regwi 1, $11, 0; //awg_0:set_1:reserved_start
                               regwi 1, $12, 0; //awg_0:set_1:duration
                               regwi 1, $13, 0; //awg_0:set_1:step
                               regwi 1, $14, 16842752;//awg_0:set_1:control
                               regwi 1, $15, 3301;//set_1 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_1
                               mathi 1, $26, $3 + 0;//awg_1:set_1:target
                               regwi 1, $27, 0; //awg_1:set_1:reserved_start
                               regwi 1, $28, 0; //awg_1:set_1:duration
                               regwi 1, $29, 0; //awg_1:set_1:step
                               regwi 1, $30, 16842752;//awg_1:set_1:control
                               regwi 1, $31, 3301;//set_1 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_1
                               regwi 1, $10, 0; //awg_0:ramp_1_to_2:target
                               regwi 1, $11, 0; //awg_0:ramp_1_to_2:reserved_start
                               mathi 1, $12, $5 + 0;//awg_0:ramp_1_to_2:duration
                               mathi 1, $13, $4 + 0;//awg_0:ramp_1_to_2:step
                               regwi 1, $14, 16908288;//awg_0:ramp_1_to_2:control
                               regwi 1, $15, 6294;//ramp_1_to_2 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_1_to_2
                               regwi 1, $26, 0; //awg_1:ramp_1_to_2:target
                               regwi 1, $27, 0; //awg_1:ramp_1_to_2:reserved_start
                               mathi 1, $28, $7 + 0;//awg_1:ramp_1_to_2:duration
                               mathi 1, $29, $6 + 0;//awg_1:ramp_1_to_2:step
                               regwi 1, $30, 16908288;//awg_1:ramp_1_to_2:control
                               regwi 1, $31, 6294;//ramp_1_to_2 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_1_to_2
                               regwi 1, $10, 0; //awg_0:set_2:target
                               regwi 1, $11, 0; //awg_0:set_2:reserved_start
                               regwi 1, $12, 0; //awg_0:set_2:duration
                               regwi 1, $13, 0; //awg_0:set_2:step
                               regwi 1, $14, 16842752;//awg_0:set_2:control
                               mathi 1, $15, $8 + 0;//copy swept set_2 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_2
                               regwi 1, $26, 0; //awg_1:set_2:target
                               regwi 1, $27, 0; //awg_1:set_2:reserved_start
                               regwi 1, $28, 0; //awg_1:set_2:duration
                               regwi 1, $29, 0; //awg_1:set_2:step
                               regwi 1, $30, 16842752;//awg_1:set_2:control
                               mathi 1, $31, $9 + 0;//copy swept set_2 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_2
                               regwi 1, $10, 0; //awg_0:bias_t_pre_zero:target
                               regwi 1, $11, 0; //awg_0:bias_t_pre_zero:reserved_start
                               regwi 1, $12, 0; //awg_0:bias_t_pre_zero:duration
                               regwi 1, $13, 0; //awg_0:bias_t_pre_zero:step
                               regwi 1, $14, 16842752;//awg_0:bias_t_pre_zero:control
                               memri 1, $15, 4095;//load swept bias_t_pre_zero t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:bias_t_pre_zero
                               regwi 1, $26, 0; //awg_1:bias_t_pre_zero:target
                               regwi 1, $27, 0; //awg_1:bias_t_pre_zero:reserved_start
                               regwi 1, $28, 0; //awg_1:bias_t_pre_zero:duration
                               regwi 1, $29, 0; //awg_1:bias_t_pre_zero:step
                               regwi 1, $30, 16842752;//awg_1:bias_t_pre_zero:control
                               memri 1, $31, 4094;//load swept bias_t_pre_zero t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:bias_t_pre_zero
                               synci 9633;
                               synci 1;         //common Bias-T guard after pre-compensation zero
                               regwi 1, $10, 694830264;//target = 0x296a44b8
                               regwi 1, $11, 29826;//reserved_start = 0x00007482
                               regwi 1, $12, 9000;//duration = 0x00002328
                               regwi 1, $13, 0; //step = 0x00000000
                               regwi 1, $14, 21692416;//control = 0x014b0000
                               regwi 1, $15, 64;//t = 64
                               set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                               regwi 1, $26, 694830264;//target = 0x296a44b8
                               regwi 1, $27, 29826;//reserved_start = 0x00007482
                               regwi 1, $28, 9000;//duration = 0x00002328
                               regwi 1, $29, 0; //step = 0x00000000
                               regwi 1, $30, 21692416;//control = 0x014b0000
                               regwi 1, $31, 64;//t = 64
                               set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                               regwi 1, $10, 9113;//wait for hardware DC area completion and IIR flush
                               sync 1, $10;     //hardware DC compensation and capture complete
                               synci 1;         //separate Bias-T stop from the next sweep point
                               synci 20;        //post Bias-T shot recovery
                               mathi 0, $13, $13 + 1;
                               condj 0, $13, ==, $14, @DEFER_FINAL_ACQUISITION_COUNT;
                               memwi 0, $13, 1;
DEFER_FINAL_ACQUISITION_COUNT: loopnz 0, $15, @FINE_TUNE_REP;
                               loopnz 0, $2, @FINE_TUNE_ADVANCE_1;
                               regwi 0, $2, 99; //reload sweep axis 1 counter
                               memri 1, $26, 4091;//load reset axis 1 (1, 1, 0, 'target')
                               mathi 1, $26, $26 + -32868;//reset axis 1 (1, 1, 0, 'target')
                               memwi 1, $26, 4091;//store reset axis 1 (1, 1, 0, 'target')
                               mathi 1, $2, $2 + -1786455;//reset axis 1 (1, 1, 0, 'step')
                               mathi 1, $3, $3 + -32868;//reset axis 1 (2, 1, 0, 'target')
                               memri 1, $11, 4092;//load RAMP-rate reset axis 1 coefficient
                               math 1, $6, $6 + $11;//RAMP-rate reset axis 1 (3, 1, 0, 'step')
                               loopnz 0, $1, @FINE_TUNE_ADVANCE_0;
                               waiti 0, 0;      //wait for experiment epilogue
                               memwi 0, $13, 1;
                               end ;
FINE_TUNE_ADVANCE_0:           mathi 1, $5, $5 + 48;//advance axis 0 (3, 0, 0, 'duration')
                               mathi 1, $7, $7 + 48;//advance axis 0 (3, 1, 0, 'duration')
                               mathi 1, $8, $8 + 3;//advance axis 0 ('event_time', 'awg', 4, 0, 0)
                               mathi 1, $9, $9 + 3;//advance axis 0 ('event_time', 'awg', 4, 1, 0)
                               memri 1, $15, 4095;//load advance axis 0 ('event_time', 'bias_pre_zero', 0)
                               mathi 1, $15, $15 + 3;//advance axis 0 ('event_time', 'bias_pre_zero', 0)
                               memwi 1, $15, 4095;//store advance axis 0 ('event_time', 'bias_pre_zero', 0)
                               memri 1, $31, 4094;//load advance axis 0 ('event_time', 'bias_pre_zero', 1)
                               mathi 1, $31, $31 + 3;//advance axis 0 ('event_time', 'bias_pre_zero', 1)
                               memwi 1, $31, 4094;//store advance axis 0 ('event_time', 'bias_pre_zero', 1)
                               memri 1, $1, 4090;//load RAMP-rate axis 0 table pointer
                               memr 1, $4, $1;  //load axis 0 advance RAMP-rate row (3, 0, 0, 'step')
                               mathi 1, $1, $1 + 1;//advance axis 0 advance RAMP-rate column 0
                               memr 1, $6, $1;  //load axis 0 advance RAMP-rate row (3, 1, 0, 'step')
                               mathi 1, $1, $1 + 1;//advance axis 0 advance RAMP-rate column 1
                               memr 1, $11, $1; //load axis 0 advance RAMP-rate axis coefficient
                               memwi 1, $11, 4093;//store axis 0 advance RAMP-rate axis coefficient
                               mathi 1, $1, $1 + 1;//advance axis 0 advance RAMP-rate column 2
                               memr 1, $11, $1; //load axis 0 advance RAMP-rate axis coefficient
                               memwi 1, $11, 4092;//store axis 0 advance RAMP-rate axis coefficient
                               mathi 1, $1, $1 + 1;//advance axis 0 advance RAMP-rate column 3
                               memwi 1, $1, 4090;//store axis 0 advance RAMP-rate table pointer
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;
FINE_TUNE_ADVANCE_1:           memri 1, $26, 4091;//load advance axis 1 (1, 1, 0, 'target')
                               mathi 1, $26, $26 + 332;//advance axis 1 (1, 1, 0, 'target')
                               memwi 1, $26, 4091;//store advance axis 1 (1, 1, 0, 'target')
                               mathi 1, $2, $2 + 18045;//advance axis 1 (1, 1, 0, 'step')
                               mathi 1, $3, $3 + 332;//advance axis 1 (2, 1, 0, 'target')
                               memri 1, $11, 4093;//load RAMP-rate advance axis 1 coefficient
                               math 1, $6, $6 + $11;//RAMP-rate advance axis 1 (3, 1, 0, 'step')
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;