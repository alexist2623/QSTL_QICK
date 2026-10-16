
// Program

                            synci 200;
                            regwi 1, $10, 0;    //target = 0x00000000
                            regwi 1, $11, 0;    //reserved_start = 0x00000000
                            regwi 1, $12, 0;    //duration = 0x00000000
                            regwi 1, $13, 0;    //step = 0x00000000
                            regwi 1, $14, 19595264;//control = 0x012b0000
                            regwi 1, $15, 0;    //t = 0
                            set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                            regwi 1, $26, 0;    //target = 0x00000000
                            regwi 1, $27, 0;    //reserved_start = 0x00000000
                            regwi 1, $28, 0;    //duration = 0x00000000
                            regwi 1, $29, 0;    //step = 0x00000000
                            regwi 1, $30, 19595264;//control = 0x012b0000
                            regwi 1, $31, 0;    //t = 0
                            set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                            regwi 2, $16, 0;    //target = 0x00000000
                            regwi 2, $17, 0;    //reserved_start = 0x00000000
                            regwi 2, $18, 0;    //duration = 0x00000000
                            regwi 2, $19, 0;    //step = 0x00000000
                            regwi 2, $20, 19595264;//control = 0x012b0000
                            regwi 2, $21, 0;    //t = 0
                            set 2, 2, $16, $17, $18, $19, $20, $21;//ch = 5, pulse @t = $21
                            synci 100;
                            synci 384;
                            regwi 1, $10, 0;    //target = 0x00000000
                            regwi 1, $11, 0;    //reserved_start = 0x00000000
                            regwi 1, $12, 0;    //duration = 0x00000000
                            regwi 1, $13, 0;    //step = 0x00000000
                            regwi 1, $14, 16842752;//control = 0x01010000
                            regwi 1, $15, 0;    //t = 0
                            set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                            regwi 1, $26, 0;    //target = 0x00000000
                            regwi 1, $27, 0;    //reserved_start = 0x00000000
                            regwi 1, $28, 0;    //duration = 0x00000000
                            regwi 1, $29, 0;    //step = 0x00000000
                            regwi 1, $30, 16842752;//control = 0x01010000
                            regwi 1, $31, 0;    //t = 0
                            set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                            regwi 2, $16, 0;    //target = 0x00000000
                            regwi 2, $17, 0;    //reserved_start = 0x00000000
                            regwi 2, $18, 0;    //duration = 0x00000000
                            regwi 2, $19, 0;    //step = 0x00000000
                            regwi 2, $20, 16842752;//control = 0x01010000
                            regwi 2, $21, 0;    //t = 0
                            set 2, 2, $16, $17, $18, $19, $20, $21;//ch = 5, pulse @t = $21
                            synci 384;
                            regwi 1, $10, 0;    //target = 0x00000000
                            regwi 1, $11, 0;    //reserved_start = 0x00000000
                            regwi 1, $12, 0;    //duration = 0x00000000
                            regwi 1, $13, 0;    //step = 0x00000000
                            regwi 1, $14, 21954560;//control = 0x014f0000
                            regwi 1, $15, 0;    //t = 0
                            set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                            regwi 1, $26, 0;    //target = 0x00000000
                            regwi 1, $27, 0;    //reserved_start = 0x00000000
                            regwi 1, $28, 0;    //duration = 0x00000000
                            regwi 1, $29, 0;    //step = 0x00000000
                            regwi 1, $30, 21954560;//control = 0x014f0000
                            regwi 1, $31, 0;    //t = 0
                            set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                            regwi 2, $16, 0;    //target = 0x00000000
                            regwi 2, $17, 0;    //reserved_start = 0x00000000
                            regwi 2, $18, 0;    //duration = 0x00000000
                            regwi 2, $19, 0;    //step = 0x00000000
                            regwi 2, $20, 21954560;//control = 0x014f0000
                            regwi 2, $21, 0;    //t = 0
                            set 2, 2, $16, $17, $18, $19, $20, $21;//ch = 5, pulse @t = $21
                            synci 384;
                            regwi 0, $13, 0;
                            regwi 0, $1, 16;    //initialize ('rf_point_table', 0, 'fine_duration') DMEM pointer
                            regwi 0, $2, 1;     //initialize sweep axis 0 counter
                            synci 128;
FINE_TUNE_POINT:            regwi 0, $15, 0;
FINE_TUNE_REP:              regwi 1, $10, 0;    //awg_0:set_0:target
                            regwi 1, $11, 0;    //awg_0:set_0:reserved_start
                            regwi 1, $12, 0;    //awg_0:set_0:duration
                            regwi 1, $13, 0;    //awg_0:set_0:step
                            regwi 1, $14, 16842752;//awg_0:set_0:control
                            regwi 1, $15, 0;    //set_0 t
                            set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_0
                            regwi 1, $26, 0;    //awg_1:set_0:target
                            regwi 1, $27, 0;    //awg_1:set_0:reserved_start
                            regwi 1, $28, 0;    //awg_1:set_0:duration
                            regwi 1, $29, 0;    //awg_1:set_0:step
                            regwi 1, $30, 16842752;//awg_1:set_0:control
                            regwi 1, $31, 0;    //set_0 t
                            set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_0
                            regwi 2, $16, 0;    //awg_2:set_0:target
                            regwi 2, $17, 0;    //awg_2:set_0:reserved_start
                            regwi 2, $18, 0;    //awg_2:set_0:duration
                            regwi 2, $19, 0;    //awg_2:set_0:step
                            regwi 2, $20, 16842752;//awg_2:set_0:control
                            regwi 2, $21, 0;    //set_0 t
                            set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:set_0
                            regwi 1, $10, 352;  //awg_0:ramp_0_to_1:target
                            regwi 1, $11, 0;    //awg_0:ramp_0_to_1:reserved_start
                            regwi 1, $12, 480;  //awg_0:ramp_0_to_1:duration
                            regwi 1, $13, 192640;//awg_0:ramp_0_to_1:step
                            regwi 1, $14, 16908288;//awg_0:ramp_0_to_1:control
                            regwi 1, $15, 23;   //ramp_0_to_1 t
                            set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_0_to_1
                            regwi 1, $26, 1073741757;//awg_1:ramp_0_to_1:target
                            bitwi 1, $26, $26 << 2;
                            regwi 1, $27, 0;    //awg_1:ramp_0_to_1:reserved_start
                            regwi 1, $28, 480;  //awg_1:ramp_0_to_1:duration
                            regwi 1, $29, 1073705156;//awg_1:ramp_0_to_1:step
                            bitwi 1, $29, $29 << 2;
                            mathi 1, $29, $29 + 3;
                            regwi 1, $30, 16908288;//awg_1:ramp_0_to_1:control
                            regwi 1, $31, 23;   //ramp_0_to_1 t
                            set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_0_to_1
                            regwi 2, $16, 168;  //awg_2:ramp_0_to_1:target
                            regwi 2, $17, 0;    //awg_2:ramp_0_to_1:reserved_start
                            regwi 2, $18, 480;  //awg_2:ramp_0_to_1:duration
                            regwi 2, $19, 91941;//awg_2:ramp_0_to_1:step
                            regwi 2, $20, 16908288;//awg_2:ramp_0_to_1:control
                            regwi 2, $21, 23;   //ramp_0_to_1 t
                            set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:ramp_0_to_1
                            regwi 1, $10, 352;  //awg_0:set_1:target
                            regwi 1, $11, 0;    //awg_0:set_1:reserved_start
                            regwi 1, $12, 0;    //awg_0:set_1:duration
                            regwi 1, $13, 0;    //awg_0:set_1:step
                            regwi 1, $14, 16842752;//awg_0:set_1:control
                            regwi 1, $15, 61;   //set_1 t
                            set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_1
                            regwi 1, $26, 1073741757;//awg_1:set_1:target
                            bitwi 1, $26, $26 << 2;
                            regwi 1, $27, 0;    //awg_1:set_1:reserved_start
                            regwi 1, $28, 0;    //awg_1:set_1:duration
                            regwi 1, $29, 0;    //awg_1:set_1:step
                            regwi 1, $30, 16842752;//awg_1:set_1:control
                            regwi 1, $31, 61;   //set_1 t
                            set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_1
                            regwi 2, $16, 168;  //awg_2:set_1:target
                            regwi 2, $17, 0;    //awg_2:set_1:reserved_start
                            regwi 2, $18, 0;    //awg_2:set_1:duration
                            regwi 2, $19, 0;    //awg_2:set_1:step
                            regwi 2, $20, 16842752;//awg_2:set_1:control
                            regwi 2, $21, 61;   //set_1 t
                            set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:set_1
                            memr 0, $27, $1;    //load fine RF t
                            mathi 0, $1, $1 + 1;
                            memr 0, $26, $1;    //load fine RF mode
                            mathi 0, $1, $1 + 1;
                            memr 0, $24, $1;    //load fine RF addr
                            mathi 0, $1, $1 + 1;
                            memr 0, $30, $1;    //load fine RF mode2
                            mathi 0, $1, $1 + 1;
                            memr 0, $28, $1;    //load fine RF addr2
                            mathi 0, $1, $1 + 1;
                            memr 0, $31, $1;    //load fine RF mode3
                            mathi 0, $1, $1 + -5;//restore fine RF row pointer
                            regwi 0, $22, 0;    //fine RF freq
                            regwi 0, $23, 0;    //fine RF phase
                            regwi 0, $25, 1000; //fine RF gain
                            condj 0, $31, !=, $0, @FINE_RF_0_START_GAIN_READY;//DDS plateau keeps original gain
                            bitwi 0, $25, $25 << 1;//compensate product envelope scaling
FINE_RF_0_START_GAIN_READY: set 0, 0, $22, $23, $24, $25, $26, $27;//fine RF start
                            regwi 1, $21, 91;   //fine RF t
                            regwi 1, $20, 589827;//fine RF mode
                            regwi 1, $18, 10;   //fine RF addr
                            regwi 1, $16, 0;    //fine RF freq
                            regwi 1, $17, 0;    //fine RF phase
                            regwi 1, $19, 2000; //fine RF gain
                            set 1, 1, $16, $17, $18, $19, $20, $21;//fine RF start
                            regwi 2, $11, 91;   //fine RF t
                            regwi 2, $10, 524291;//fine RF mode
                            regwi 2, $8, 124;   //fine RF addr
                            regwi 2, $6, 0;     //fine RF freq
                            regwi 2, $7, 0;     //fine RF phase
                            regwi 2, $9, 3000;  //fine RF gain
                            bitwi 2, $9, $9 << 1;//compensate product envelope scaling
                            set 2, 2, $6, $7, $8, $9, $10, $11;//fine RF start
                            condj 0, $31, ==, $0, @FINE_RF_0_TAIL_DONE;//short fine RF has no second command
                            bitwi 0, $25, $25 << 1;//compensate product envelope scaling
                            set 0, 0, $22, $23, $24, $25, $30, $28;//fine RF ending pattern
FINE_RF_0_TAIL_DONE:        mathi 0, $31, $31 + 0;//fine RF tail complete
                            bitwi 1, $19, $19 << 1;//compensate product envelope scaling
                            regwi 1, $20, 524292;//fine RF tail mode
                            regwi 1, $21, 94;   //fine RF tail time
                            set 1, 1, $16, $17, $18, $19, $20, $21;//fine RF ending pattern
                            regwi 1, $10, 0;    //awg_0:ramp_1_to_2:target
                            regwi 1, $11, 0;    //awg_0:ramp_1_to_2:reserved_start
                            regwi 1, $12, 480;  //awg_0:ramp_1_to_2:duration
                            regwi 1, $13, 1073693664;//awg_0:ramp_1_to_2:step
                            bitwi 1, $13, $13 << 2;
                            regwi 1, $14, 16908288;//awg_0:ramp_1_to_2:control
                            regwi 1, $15, 3054; //ramp_1_to_2 t
                            set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_1_to_2
                            regwi 1, $26, 0;    //awg_1:ramp_1_to_2:target
                            regwi 1, $27, 0;    //awg_1:ramp_1_to_2:reserved_start
                            regwi 1, $28, 480;  //awg_1:ramp_1_to_2:duration
                            regwi 1, $29, 146669;//awg_1:ramp_1_to_2:step
                            regwi 1, $30, 16908288;//awg_1:ramp_1_to_2:control
                            regwi 1, $31, 3054; //ramp_1_to_2 t
                            set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_1_to_2
                            regwi 2, $16, 0;    //awg_2:ramp_1_to_2:target
                            regwi 2, $17, 0;    //awg_2:ramp_1_to_2:reserved_start
                            regwi 2, $18, 480;  //awg_2:ramp_1_to_2:duration
                            regwi 2, $19, 1073718838;//awg_2:ramp_1_to_2:step
                            bitwi 2, $19, $19 << 2;
                            mathi 2, $19, $19 + 3;
                            regwi 2, $20, 16908288;//awg_2:ramp_1_to_2:control
                            regwi 2, $21, 3054; //ramp_1_to_2 t
                            set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:ramp_1_to_2
                            regwi 1, $10, 0;    //awg_0:set_2:target
                            regwi 1, $11, 0;    //awg_0:set_2:reserved_start
                            regwi 1, $12, 0;    //awg_0:set_2:duration
                            regwi 1, $13, 0;    //awg_0:set_2:step
                            regwi 1, $14, 16842752;//awg_0:set_2:control
                            regwi 1, $15, 3092; //set_2 t
                            set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_2
                            regwi 1, $26, 0;    //awg_1:set_2:target
                            regwi 1, $27, 0;    //awg_1:set_2:reserved_start
                            regwi 1, $28, 0;    //awg_1:set_2:duration
                            regwi 1, $29, 0;    //awg_1:set_2:step
                            regwi 1, $30, 16842752;//awg_1:set_2:control
                            regwi 1, $31, 3092; //set_2 t
                            set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_2
                            regwi 2, $16, 0;    //awg_2:set_2:target
                            regwi 2, $17, 0;    //awg_2:set_2:reserved_start
                            regwi 2, $18, 0;    //awg_2:set_2:duration
                            regwi 2, $19, 0;    //awg_2:set_2:step
                            regwi 2, $20, 16842752;//awg_2:set_2:control
                            regwi 2, $21, 3092; //set_2 t
                            set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:set_2
                            synci 3173;
                            mathi 0, $13, $13 + 1;
                            memwi 0, $13, 1;
                            loopnz 0, $15, @FINE_TUNE_REP;
                            loopnz 0, $2, @FINE_TUNE_ADVANCE_0;
                            end ;
FINE_TUNE_ADVANCE_0:        mathi 0, $1, $1 + 6;//advance axis 0 ('rf_point_table', 0, 'fine_duration') pointer
                            condj 0, $0, ==, $0, @FINE_TUNE_POINT;