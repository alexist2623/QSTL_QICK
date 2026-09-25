
// Program

                               regwi 0, $13, 0;
                               regwi 0, $14, 100;//final acquisition count
                               regwi 1, $1, 5120;//initialize direct sweep state (5, 0, 0, 'target')
                               regwi 1, $2, 4773433;//initialize direct sweep state (5, 0, 0, 'step')
                               regwi 1, $3, -3072;//initialize direct sweep state (5, 1, 0, 'target')
                               regwi 1, $4, -842370;//initialize direct sweep state (5, 1, 0, 'step')
                               regwi 1, $5, 5120;//initialize direct sweep state (6, 0, 0, 'target')
                               regwi 1, $6, -3072;//initialize direct sweep state (6, 1, 0, 'target')
                               regwi 1, $7, -700510;//initialize direct sweep state (7, 0, 0, 'step')
                               regwi 1, $8, 420306;//initialize direct sweep state (7, 1, 0, 'step')
                               regwi 0, $1, 9;  //initialize sweep axis 0 counter
                               regwi 0, $2, 9;  //initialize sweep axis 1 counter
                               synci 128;
                               synci 128;       //initial lookahead for SquarePulse and external markers
FINE_TUNE_POINT:               regwi 0, $15, 0;
FINE_TUNE_REP:                 regwi 0, $16, 64;//out = 0b0000000001000000
                               seti 7, 0, $16, 0;//ch =0 out = $16 @t = 0
                               seti 7, 0, $0, 111;//ch =0 out = 0 @t = 0
                               regwi 1, $26, 0; //awg_0:set_0:target
                               regwi 1, $27, 0; //awg_0:set_0:reserved_start
                               regwi 1, $28, 0; //awg_0:set_0:duration
                               regwi 1, $29, 0; //awg_0:set_0:step
                               regwi 1, $30, 16842752;//awg_0:set_0:control
                               regwi 1, $31, 0; //set_0 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_0:set_0
                               regwi 1, $10, 0; //awg_1:set_0:target
                               regwi 1, $11, 0; //awg_1:set_0:reserved_start
                               regwi 1, $12, 0; //awg_1:set_0:duration
                               regwi 1, $13, 0; //awg_1:set_0:step
                               regwi 1, $14, 16842752;//awg_1:set_0:control
                               regwi 1, $15, 0; //set_0 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_1:set_0
                               regwi 1, $26, 0; //awg_0:ramp_0_to_1:target
                               regwi 1, $27, 0; //awg_0:ramp_0_to_1:reserved_start
                               regwi 1, $28, 4800;//awg_0:ramp_0_to_1:duration
                               regwi 1, $29, 0; //awg_0:ramp_0_to_1:step
                               regwi 1, $30, 16908288;//awg_0:ramp_0_to_1:control
                               regwi 1, $31, 1493;//ramp_0_to_1 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_0:ramp_0_to_1
                               regwi 1, $10, 12288;//awg_1:ramp_0_to_1:target
                               regwi 1, $11, 0; //awg_1:ramp_0_to_1:reserved_start
                               regwi 1, $12, 4800;//awg_1:ramp_0_to_1:duration
                               regwi 1, $13, 167807;//awg_1:ramp_0_to_1:step
                               regwi 1, $14, 16908288;//awg_1:ramp_0_to_1:control
                               regwi 1, $15, 1493;//ramp_0_to_1 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_1:ramp_0_to_1
                               regwi 1, $26, 0; //awg_0:set_1:target
                               regwi 1, $27, 0; //awg_0:set_1:reserved_start
                               regwi 1, $28, 0; //awg_0:set_1:duration
                               regwi 1, $29, 0; //awg_0:set_1:step
                               regwi 1, $30, 16842752;//awg_0:set_1:control
                               regwi 1, $31, 1801;//set_1 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_0:set_1
                               regwi 1, $10, 12288;//awg_1:set_1:target
                               regwi 1, $11, 0; //awg_1:set_1:reserved_start
                               regwi 1, $12, 0; //awg_1:set_1:duration
                               regwi 1, $13, 0; //awg_1:set_1:step
                               regwi 1, $14, 16842752;//awg_1:set_1:control
                               regwi 1, $15, 1801;//set_1 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_1:set_1
                               regwi 1, $26, 1073738752;//awg_0:ramp_1_to_2:target
                               bitwi 1, $26, $26 << 2;
                               regwi 1, $27, 0; //awg_0:ramp_1_to_2:reserved_start
                               regwi 1, $28, 4800;//awg_0:ramp_1_to_2:duration
                               regwi 1, $29, 16609409;//awg_0:ramp_1_to_2:step
                               regwi 1, $30, 16908288;//awg_0:ramp_1_to_2:control
                               regwi 1, $31, 3294;//ramp_1_to_2 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_0:ramp_1_to_2
                               regwi 1, $10, 0; //awg_1:ramp_1_to_2:target
                               regwi 1, $11, 0; //awg_1:ramp_1_to_2:reserved_start
                               regwi 1, $12, 4800;//awg_1:ramp_1_to_2:duration
                               regwi 1, $13, 16609409;//awg_1:ramp_1_to_2:step
                               regwi 1, $14, 16908288;//awg_1:ramp_1_to_2:control
                               regwi 1, $15, 3294;//ramp_1_to_2 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_1:ramp_1_to_2
                               regwi 1, $26, 1073738752;//awg_0:set_2:target
                               bitwi 1, $26, $26 << 2;
                               regwi 1, $27, 0; //awg_0:set_2:reserved_start
                               regwi 1, $28, 0; //awg_0:set_2:duration
                               regwi 1, $29, 0; //awg_0:set_2:step
                               regwi 1, $30, 16842752;//awg_0:set_2:control
                               regwi 1, $31, 3602;//set_2 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_0:set_2
                               regwi 1, $10, 0; //awg_1:set_2:target
                               regwi 1, $11, 0; //awg_1:set_2:reserved_start
                               regwi 1, $12, 0; //awg_1:set_2:duration
                               regwi 1, $13, 0; //awg_1:set_2:step
                               regwi 1, $14, 16842752;//awg_1:set_2:control
                               regwi 1, $15, 3602;//set_2 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_1:set_2
                               mathi 1, $26, $1 + 0;//awg_0:ramp_2_to_3:target
                               regwi 1, $27, 0; //awg_0:ramp_2_to_3:reserved_start
                               regwi 1, $28, 240;//awg_0:ramp_2_to_3:duration
                               bitwi 1, $29, $2 & 16777215;//awg_0:ramp_2_to_3:step
                               regwi 1, $30, 16908288;//awg_0:ramp_2_to_3:control
                               regwi 1, $31, 5095;//ramp_2_to_3 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_0:ramp_2_to_3
                               mathi 1, $10, $3 + 0;//awg_1:ramp_2_to_3:target
                               regwi 1, $11, 0; //awg_1:ramp_2_to_3:reserved_start
                               regwi 1, $12, 240;//awg_1:ramp_2_to_3:duration
                               bitwi 1, $13, $4 & 16777215;//awg_1:ramp_2_to_3:step
                               regwi 1, $14, 16908288;//awg_1:ramp_2_to_3:control
                               regwi 1, $15, 5095;//ramp_2_to_3 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_1:ramp_2_to_3
                               mathi 1, $26, $5 + 0;//awg_0:set_3:target
                               regwi 1, $27, 0; //awg_0:set_3:reserved_start
                               regwi 1, $28, 0; //awg_0:set_3:duration
                               regwi 1, $29, 0; //awg_0:set_3:step
                               regwi 1, $30, 16842752;//awg_0:set_3:control
                               regwi 1, $31, 5118;//set_3 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_0:set_3
                               mathi 1, $10, $6 + 0;//awg_1:set_3:target
                               regwi 1, $11, 0; //awg_1:set_3:reserved_start
                               regwi 1, $12, 0; //awg_1:set_3:duration
                               regwi 1, $13, 0; //awg_1:set_3:step
                               regwi 1, $14, 16842752;//awg_1:set_3:control
                               regwi 1, $15, 5118;//set_3 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_1:set_3
                               regwi 1, $26, 0; //awg_0:ramp_3_to_4:target
                               regwi 1, $27, 0; //awg_0:ramp_3_to_4:reserved_start
                               regwi 1, $28, 480;//awg_0:ramp_3_to_4:duration
                               bitwi 1, $29, $7 & 16777215;//awg_0:ramp_3_to_4:step
                               regwi 1, $30, 16908288;//awg_0:ramp_3_to_4:control
                               regwi 1, $31, 5141;//ramp_3_to_4 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_0:ramp_3_to_4
                               regwi 1, $10, 0; //awg_1:ramp_3_to_4:target
                               regwi 1, $11, 0; //awg_1:ramp_3_to_4:reserved_start
                               regwi 1, $12, 480;//awg_1:ramp_3_to_4:duration
                               bitwi 1, $13, $8 & 16777215;//awg_1:ramp_3_to_4:step
                               regwi 1, $14, 16908288;//awg_1:ramp_3_to_4:control
                               regwi 1, $15, 5141;//ramp_3_to_4 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_1:ramp_3_to_4
                               regwi 1, $26, 0; //awg_0:set_4:target
                               regwi 1, $27, 0; //awg_0:set_4:reserved_start
                               regwi 1, $28, 0; //awg_0:set_4:duration
                               regwi 1, $29, 0; //awg_0:set_4:step
                               regwi 1, $30, 16842752;//awg_0:set_4:control
                               regwi 1, $31, 5179;//set_4 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_0:set_4
                               regwi 1, $10, 0; //awg_1:set_4:target
                               regwi 1, $11, 0; //awg_1:set_4:reserved_start
                               regwi 1, $12, 0; //awg_1:set_4:duration
                               regwi 1, $13, 0; //awg_1:set_4:step
                               regwi 1, $14, 16842752;//awg_1:set_4:control
                               regwi 1, $15, 5179;//set_4 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_1:set_4
                               synci 17199;
                               regwi 0, $16, 64;//out = 0b0000000001000000
                               seti 7, 0, $16, 0;//ch =0 out = $16 @t = 0
                               seti 7, 0, $0, 111;//ch =0 out = 0 @t = 0
                               synci 112;       //complete external end marker
                               mathi 0, $13, $13 + 1;
                               condj 0, $13, ==, $14, @DEFER_FINAL_ACQUISITION_COUNT;
                               memwi 0, $13, 1;
DEFER_FINAL_ACQUISITION_COUNT: loopnz 0, $15, @FINE_TUNE_REP;
                               loopnz 0, $2, @FINE_TUNE_ADVANCE_1;
                               regwi 0, $2, 9;  //reload sweep axis 1 counter
                               mathi 1, $3, $3 + -3672;//reset axis 1 (5, 1, 0, 'target')
                               mathi 1, $4, $4 + -1011285;//reset axis 1 (5, 1, 0, 'step')
                               mathi 1, $6, $6 + -3672;//reset axis 1 (6, 1, 0, 'target')
                               mathi 1, $8, $8 + 504585;//reset axis 1 (7, 1, 0, 'step')
                               loopnz 0, $1, @FINE_TUNE_ADVANCE_0;
                               waiti 0, 0;      //wait for experiment epilogue
                               memwi 0, $13, 1;
                               end ;
FINE_TUNE_ADVANCE_0:           mathi 1, $1, $1 + 408;//advance axis 0 (5, 0, 0, 'target')
                               mathi 1, $2, $2 + 112365;//advance axis 0 (5, 0, 0, 'step')
                               mathi 1, $5, $5 + 408;//advance axis 0 (6, 0, 0, 'target')
                               mathi 1, $7, $7 + -56065;//advance axis 0 (7, 0, 0, 'step')
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;
FINE_TUNE_ADVANCE_1:           mathi 1, $3, $3 + 408;//advance axis 1 (5, 1, 0, 'target')
                               mathi 1, $4, $4 + 112365;//advance axis 1 (5, 1, 0, 'step')
                               mathi 1, $6, $6 + 408;//advance axis 1 (6, 1, 0, 'target')
                               mathi 1, $8, $8 + -56065;//advance axis 1 (7, 1, 0, 'step')
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;