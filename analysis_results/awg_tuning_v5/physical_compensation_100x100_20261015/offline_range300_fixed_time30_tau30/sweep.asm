
// Program

                               synci 200;
                               regwi 1, $10, 977343669;//target = 0x3a4114b5
                               regwi 1, $11, 0; //reserved_start = 0x00000000
                               regwi 1, $12, 0; //duration = 0x00000000
                               regwi 1, $13, 0; //step = 0x00000000
                               regwi 1, $14, 19857408;//control = 0x012f0000
                               regwi 1, $15, 0; //t = 0
                               set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                               regwi 1, $26, 977343669;//target = 0x3a4114b5
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
                               regwi 1, $1, -12264;//initialize direct sweep state (1, 0, 0, 'target')
                               regwi 1, $2, -669917;//initialize direct sweep state (1, 0, 0, 'step')
                               regwi 1, $3, -12264;//initialize direct sweep state (1, 1, 0, 'target')
                               regwi 1, $4, -669917;//initialize direct sweep state (1, 1, 0, 'step')
                               regwi 1, $5, -12264;//initialize direct sweep state (2, 0, 0, 'target')
                               regwi 1, $6, -12264;//initialize direct sweep state (2, 1, 0, 'target')
                               regwi 1, $7, 669917;//initialize direct sweep state (3, 0, 0, 'step')
                               regwi 1, $8, 669917;//initialize direct sweep state (3, 1, 0, 'step')
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
                               mathi 1, $10, $1 + 0;//awg_0:ramp_0_to_1:target
                               regwi 1, $11, 0; //awg_0:ramp_0_to_1:reserved_start
                               regwi 1, $12, 4800;//awg_0:ramp_0_to_1:duration
                               mathi 1, $13, $2 + 0;//awg_0:ramp_0_to_1:step
                               regwi 1, $14, 16908288;//awg_0:ramp_0_to_1:control
                               regwi 1, $15, 2993;//ramp_0_to_1 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_0_to_1
                               mathi 1, $26, $3 + 0;//awg_1:ramp_0_to_1:target
                               regwi 1, $27, 0; //awg_1:ramp_0_to_1:reserved_start
                               regwi 1, $28, 4800;//awg_1:ramp_0_to_1:duration
                               mathi 1, $29, $4 + 0;//awg_1:ramp_0_to_1:step
                               regwi 1, $30, 16908288;//awg_1:ramp_0_to_1:control
                               regwi 1, $31, 2993;//ramp_0_to_1 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_0_to_1
                               mathi 1, $10, $5 + 0;//awg_0:set_1:target
                               regwi 1, $11, 0; //awg_0:set_1:reserved_start
                               regwi 1, $12, 0; //awg_0:set_1:duration
                               regwi 1, $13, 0; //awg_0:set_1:step
                               regwi 1, $14, 16842752;//awg_0:set_1:control
                               regwi 1, $15, 3301;//set_1 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_1
                               mathi 1, $26, $6 + 0;//awg_1:set_1:target
                               regwi 1, $27, 0; //awg_1:set_1:reserved_start
                               regwi 1, $28, 0; //awg_1:set_1:duration
                               regwi 1, $29, 0; //awg_1:set_1:step
                               regwi 1, $30, 16842752;//awg_1:set_1:control
                               regwi 1, $31, 3301;//set_1 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_1
                               regwi 1, $10, 0; //awg_0:ramp_1_to_2:target
                               regwi 1, $11, 0; //awg_0:ramp_1_to_2:reserved_start
                               regwi 1, $12, 4800;//awg_0:ramp_1_to_2:duration
                               mathi 1, $13, $7 + 0;//awg_0:ramp_1_to_2:step
                               regwi 1, $14, 16908288;//awg_0:ramp_1_to_2:control
                               regwi 1, $15, 6294;//ramp_1_to_2 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_1_to_2
                               regwi 1, $26, 0; //awg_1:ramp_1_to_2:target
                               regwi 1, $27, 0; //awg_1:ramp_1_to_2:reserved_start
                               regwi 1, $28, 4800;//awg_1:ramp_1_to_2:duration
                               mathi 1, $29, $8 + 0;//awg_1:ramp_1_to_2:step
                               regwi 1, $30, 16908288;//awg_1:ramp_1_to_2:control
                               regwi 1, $31, 6294;//ramp_1_to_2 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_1_to_2
                               regwi 1, $10, 0; //awg_0:set_2:target
                               regwi 1, $11, 0; //awg_0:set_2:reserved_start
                               regwi 1, $12, 0; //awg_0:set_2:duration
                               regwi 1, $13, 0; //awg_0:set_2:step
                               regwi 1, $14, 16842752;//awg_0:set_2:control
                               regwi 1, $15, 6602;//set_2 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_2
                               regwi 1, $26, 0; //awg_1:set_2:target
                               regwi 1, $27, 0; //awg_1:set_2:reserved_start
                               regwi 1, $28, 0; //awg_1:set_2:duration
                               regwi 1, $29, 0; //awg_1:set_2:step
                               regwi 1, $30, 16842752;//awg_1:set_2:control
                               regwi 1, $31, 6602;//set_2 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_2
                               regwi 1, $10, 0; //awg_0:bias_t_pre_zero:target
                               regwi 1, $11, 0; //awg_0:bias_t_pre_zero:reserved_start
                               regwi 1, $12, 0; //awg_0:bias_t_pre_zero:duration
                               regwi 1, $13, 0; //awg_0:bias_t_pre_zero:step
                               regwi 1, $14, 16842752;//awg_0:bias_t_pre_zero:control
                               regwi 1, $15, 9602;//bias_t_pre_zero t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:bias_t_pre_zero
                               regwi 1, $26, 0; //awg_1:bias_t_pre_zero:target
                               regwi 1, $27, 0; //awg_1:bias_t_pre_zero:reserved_start
                               regwi 1, $28, 0; //awg_1:bias_t_pre_zero:duration
                               regwi 1, $29, 0; //awg_1:bias_t_pre_zero:step
                               regwi 1, $30, 16842752;//awg_1:bias_t_pre_zero:control
                               regwi 1, $31, 9602;//bias_t_pre_zero t
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
                               mathi 1, $3, $3 + -24552;//reset axis 1 (1, 1, 0, 'target')
                               mathi 1, $4, $4 + -1339866;//reset axis 1 (1, 1, 0, 'step')
                               mathi 1, $6, $6 + -24552;//reset axis 1 (2, 1, 0, 'target')
                               mathi 1, $8, $8 + 1339866;//reset axis 1 (3, 1, 0, 'step')
                               loopnz 0, $1, @FINE_TUNE_ADVANCE_0;
                               waiti 0, 0;      //wait for experiment epilogue
                               memwi 0, $13, 1;
                               end ;
FINE_TUNE_ADVANCE_0:           mathi 1, $1, $1 + 248;//advance axis 0 (1, 0, 0, 'target')
                               mathi 1, $2, $2 + 13534;//advance axis 0 (1, 0, 0, 'step')
                               mathi 1, $5, $5 + 248;//advance axis 0 (2, 0, 0, 'target')
                               mathi 1, $7, $7 + -13534;//advance axis 0 (3, 0, 0, 'step')
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;
FINE_TUNE_ADVANCE_1:           mathi 1, $3, $3 + 248;//advance axis 1 (1, 1, 0, 'target')
                               mathi 1, $4, $4 + 13534;//advance axis 1 (1, 1, 0, 'step')
                               mathi 1, $6, $6 + 248;//advance axis 1 (2, 1, 0, 'target')
                               mathi 1, $8, $8 + -13534;//advance axis 1 (3, 1, 0, 'step')
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;