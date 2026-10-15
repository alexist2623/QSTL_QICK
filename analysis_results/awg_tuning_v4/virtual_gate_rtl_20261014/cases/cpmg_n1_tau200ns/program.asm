
// Program

                               regwi 0, $22, 170009122;//freq = 170009122
                               regwi 0, $23, 0; //phase = 0
                               regwi 0, $25, 2000;//gain = 2000
                               regwi 0, $26, 589854;//phrst| stdysel | mode | | outsel = 0b01001 | length = 30 
                               regwi 1, $16, 170009122;//freq = 170009122
                               regwi 1, $17, 0; //phase = 0
                               regwi 1, $19, 2000;//gain = 2000
                               regwi 1, $20, 589854;//phrst| stdysel | mode | | outsel = 0b01001 | length = 30 
                               regwi 2, $6, 170009122;//freq = 170009122
                               regwi 2, $7, 0;  //phase = 0
                               regwi 2, $9, 2000;//gain = 2000
                               regwi 2, $10, 589854;//phrst| stdysel | mode | | outsel = 0b01001 | length = 30 
                               synci 200;
                               regwi 1, $10, 733007751;//target = 0xaec33e1f
                               bitwi 1, $10, $10 << 2;
                               mathi 1, $10, $10 + 3;
                               regwi 1, $11, 0; //reserved_start = 0x00000000
                               regwi 1, $12, 0; //duration = 0x00000000
                               regwi 1, $13, 0; //step = 0x00000000
                               regwi 1, $14, 19857408;//control = 0x012f0000
                               regwi 1, $15, 0; //t = 0
                               set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                               regwi 1, $26, 733007751;//target = 0xaec33e1f
                               bitwi 1, $26, $26 << 2;
                               mathi 1, $26, $26 + 3;
                               regwi 1, $27, 0; //reserved_start = 0x00000000
                               regwi 1, $28, 0; //duration = 0x00000000
                               regwi 1, $29, 0; //step = 0x00000000
                               regwi 1, $30, 19857408;//control = 0x012f0000
                               regwi 1, $31, 0; //t = 0
                               set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                               regwi 2, $16, 733007751;//target = 0xaec33e1f
                               bitwi 2, $16, $16 << 2;
                               mathi 2, $16, $16 + 3;
                               regwi 2, $17, 0; //reserved_start = 0x00000000
                               regwi 2, $18, 0; //duration = 0x00000000
                               regwi 2, $19, 0; //step = 0x00000000
                               regwi 2, $20, 19857408;//control = 0x012f0000
                               regwi 2, $21, 0; //t = 0
                               set 2, 2, $16, $17, $18, $19, $20, $21;//ch = 5, pulse @t = $21
                               synci 100;
                               synci 384;
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
                               regwi 2, $16, 0; //target = 0x00000000
                               regwi 2, $17, 0; //reserved_start = 0x00000000
                               regwi 2, $18, 0; //duration = 0x00000000
                               regwi 2, $19, 0; //step = 0x00000000
                               regwi 2, $20, 16842752;//control = 0x01010000
                               regwi 2, $21, 0; //t = 0
                               set 2, 2, $16, $17, $18, $19, $20, $21;//ch = 5, pulse @t = $21
                               synci 384;
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
                               regwi 2, $16, 0; //target = 0x00000000
                               regwi 2, $17, 0; //reserved_start = 0x00000000
                               regwi 2, $18, 0; //duration = 0x00000000
                               regwi 2, $19, 0; //step = 0x00000000
                               regwi 2, $20, 21168128;//control = 0x01430000
                               regwi 2, $21, 0; //t = 0
                               set 2, 2, $16, $17, $18, $19, $20, $21;//ch = 5, pulse @t = $21
                               synci 384;
                               regwi 0, $13, 0;
                               regwi 0, $14, 4; //final acquisition count
                               regwi 1, $1, 148;//initialize direct sweep state (0, 0, 0, 'target')
                               regwi 1, $2, -464;//initialize direct sweep state (0, 1, 0, 'target')
                               regwi 2, $1, 144;//initialize direct sweep state (0, 2, 0, 'target')
                               regwi 1, $3, -136675;//initialize direct sweep state (1, 0, 0, 'step')
                               regwi 1, $4, 273351;//initialize direct sweep state (1, 1, 0, 'step')
                               regwi 2, $2, -85285;//initialize direct sweep state (1, 2, 0, 'step')
                               regwi 0, $1, 1;  //initialize sweep axis 0 counter
                               synci 128;
                               synci 128;       //initial lookahead for SquarePulse and external markers
FINE_TUNE_POINT:               regwi 0, $15, 1;
FINE_TUNE_REP:                 regwi 0, $16, 64;//out = 0b0000000001000000
                               seti 7, 0, $16, 31;//ch =0 out = $16 @t = 31
                               seti 7, 0, $0, 61;//ch =0 out = 0 @t = 31
                               regwi 1, $16, 170009122;//freq = 170009122
                               regwi 1, $17, 0; //phase = 0
                               regwi 1, $19, 2000;//gain = 2000
                               regwi 1, $20, 589854;//phrst| stdysel | mode | | outsel = 0b01001 | length = 30 
                               regwi 1, $21, 0; //RF duration-sweep start
                               set 1, 1, $16, $17, $0, $19, $20, $21;//RF duration-sweep start
                               regwi 2, $6, 170009122;//freq = 170009122
                               regwi 2, $7, 0;  //phase = 0
                               regwi 2, $9, 2000;//gain = 2000
                               regwi 2, $10, 589854;//phrst| stdysel | mode | | outsel = 0b01001 | length = 30 
                               regwi 2, $11, 0; //RF duration-sweep start
                               set 2, 2, $6, $7, $0, $9, $10, $11;//RF duration-sweep start
                               mathi 1, $10, $1 + 0;//awg_0:set_0:target
                               regwi 1, $11, 0; //awg_0:set_0:reserved_start
                               regwi 1, $12, 0; //awg_0:set_0:duration
                               regwi 1, $13, 0; //awg_0:set_0:step
                               regwi 1, $14, 16842752;//awg_0:set_0:control
                               regwi 1, $15, 13;//set_0 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_0
                               mathi 1, $26, $2 + 0;//awg_1:set_0:target
                               regwi 1, $27, 0; //awg_1:set_0:reserved_start
                               regwi 1, $28, 0; //awg_1:set_0:duration
                               regwi 1, $29, 0; //awg_1:set_0:step
                               regwi 1, $30, 16842752;//awg_1:set_0:control
                               regwi 1, $31, 13;//set_0 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_0
                               mathi 2, $16, $1 + 0;//awg_2:set_0:target
                               regwi 2, $17, 0; //awg_2:set_0:reserved_start
                               regwi 2, $18, 0; //awg_2:set_0:duration
                               regwi 2, $19, 0; //awg_2:set_0:step
                               regwi 2, $20, 16842752;//awg_2:set_0:control
                               regwi 2, $21, 13;//set_0 t
                               set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:set_0
                               regwi 0, $22, 170009122;//freq = 170009122
                               regwi 0, $23, 0; //phase = 0
                               regwi 0, $25, 2000;//gain = 2000
                               regwi 0, $26, 589854;//phrst| stdysel | mode | | outsel = 0b01001 | length = 30 
                               regwi 0, $27, 30;//RF duration-sweep start
                               set 0, 0, $22, $23, $0, $25, $26, $27;//RF duration-sweep start
                               regwi 1, $10, 1073741736;//awg_0:ramp_0_to_1:target
                               bitwi 1, $10, $10 << 2;
                               regwi 1, $11, 0; //awg_0:ramp_0_to_1:reserved_start
                               regwi 1, $12, 960;//awg_0:ramp_0_to_1:duration
                               mathi 1, $13, $3 + 0;//awg_0:ramp_0_to_1:step
                               regwi 1, $14, 16908288;//awg_0:ramp_0_to_1:control
                               regwi 1, $15, 306;//ramp_0_to_1 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_0_to_1
                               regwi 1, $26, 536;//awg_1:ramp_0_to_1:target
                               regwi 1, $27, 0; //awg_1:ramp_0_to_1:reserved_start
                               regwi 1, $28, 960;//awg_1:ramp_0_to_1:duration
                               mathi 1, $29, $4 + 0;//awg_1:ramp_0_to_1:step
                               regwi 1, $30, 16908288;//awg_1:ramp_0_to_1:control
                               regwi 1, $31, 306;//ramp_0_to_1 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_0_to_1
                               regwi 2, $16, 1073741782;//awg_2:ramp_0_to_1:target
                               bitwi 2, $16, $16 << 2;
                               regwi 2, $17, 0; //awg_2:ramp_0_to_1:reserved_start
                               regwi 2, $18, 960;//awg_2:ramp_0_to_1:duration
                               mathi 2, $19, $2 + 0;//awg_2:ramp_0_to_1:step
                               regwi 2, $20, 16908288;//awg_2:ramp_0_to_1:control
                               regwi 2, $21, 306;//ramp_0_to_1 t
                               set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:ramp_0_to_1
                               regwi 1, $10, 1073741736;//awg_0:set_1:target
                               bitwi 1, $10, $10 << 2;
                               regwi 1, $11, 0; //awg_0:set_1:reserved_start
                               regwi 1, $12, 0; //awg_0:set_1:duration
                               regwi 1, $13, 0; //awg_0:set_1:step
                               regwi 1, $14, 16842752;//awg_0:set_1:control
                               regwi 1, $15, 374;//set_1 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_1
                               regwi 1, $26, 536;//awg_1:set_1:target
                               regwi 1, $27, 0; //awg_1:set_1:reserved_start
                               regwi 1, $28, 0; //awg_1:set_1:duration
                               regwi 1, $29, 0; //awg_1:set_1:step
                               regwi 1, $30, 16842752;//awg_1:set_1:control
                               regwi 1, $31, 374;//set_1 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_1
                               regwi 2, $16, 1073741782;//awg_2:set_1:target
                               bitwi 2, $16, $16 << 2;
                               regwi 2, $17, 0; //awg_2:set_1:reserved_start
                               regwi 2, $18, 0; //awg_2:set_1:duration
                               regwi 2, $19, 0; //awg_2:set_1:step
                               regwi 2, $20, 16842752;//awg_2:set_1:control
                               regwi 2, $21, 374;//set_1 t
                               set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:set_1
                               regwi 1, $10, 0; //awg_0:ramp_1_to_2:target
                               regwi 1, $11, 0; //awg_0:ramp_1_to_2:reserved_start
                               regwi 1, $12, 960;//awg_0:ramp_1_to_2:duration
                               regwi 1, $13, 96219;//awg_0:ramp_1_to_2:step
                               regwi 1, $14, 16908288;//awg_0:ramp_1_to_2:control
                               regwi 1, $15, 667;//ramp_1_to_2 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_1_to_2
                               regwi 1, $26, 0; //awg_1:ramp_1_to_2:target
                               regwi 1, $27, 0; //awg_1:ramp_1_to_2:reserved_start
                               regwi 1, $28, 960;//awg_1:ramp_1_to_2:duration
                               regwi 1, $29, 1073705195;//awg_1:ramp_1_to_2:step
                               bitwi 1, $29, $29 << 2;
                               regwi 1, $30, 16908288;//awg_1:ramp_1_to_2:control
                               regwi 1, $31, 667;//ramp_1_to_2 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_1_to_2
                               regwi 2, $16, 0; //awg_2:ramp_1_to_2:target
                               regwi 2, $17, 0; //awg_2:ramp_1_to_2:reserved_start
                               regwi 2, $18, 960;//awg_2:ramp_1_to_2:duration
                               regwi 2, $19, 45923;//awg_2:ramp_1_to_2:step
                               regwi 2, $20, 16908288;//awg_2:ramp_1_to_2:control
                               regwi 2, $21, 667;//ramp_1_to_2 t
                               set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:ramp_1_to_2
                               regwi 1, $10, 0; //awg_0:set_2:target
                               regwi 1, $11, 0; //awg_0:set_2:reserved_start
                               regwi 1, $12, 0; //awg_0:set_2:duration
                               regwi 1, $13, 0; //awg_0:set_2:step
                               regwi 1, $14, 16842752;//awg_0:set_2:control
                               regwi 1, $15, 735;//set_2 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_2
                               regwi 1, $26, 0; //awg_1:set_2:target
                               regwi 1, $27, 0; //awg_1:set_2:reserved_start
                               regwi 1, $28, 0; //awg_1:set_2:duration
                               regwi 1, $29, 0; //awg_1:set_2:step
                               regwi 1, $30, 16842752;//awg_1:set_2:control
                               regwi 1, $31, 735;//set_2 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_2
                               regwi 2, $16, 0; //awg_2:set_2:target
                               regwi 2, $17, 0; //awg_2:set_2:reserved_start
                               regwi 2, $18, 0; //awg_2:set_2:duration
                               regwi 2, $19, 0; //awg_2:set_2:step
                               regwi 2, $20, 16842752;//awg_2:set_2:control
                               regwi 2, $21, 735;//set_2 t
                               set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:set_2
                               regwi 1, $10, 0; //awg_0:bias_t_pre_zero:target
                               regwi 1, $11, 0; //awg_0:bias_t_pre_zero:reserved_start
                               regwi 1, $12, 0; //awg_0:bias_t_pre_zero:duration
                               regwi 1, $13, 0; //awg_0:bias_t_pre_zero:step
                               regwi 1, $14, 16842752;//awg_0:bias_t_pre_zero:control
                               regwi 1, $15, 1035;//bias_t_pre_zero t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:bias_t_pre_zero
                               regwi 1, $26, 0; //awg_1:bias_t_pre_zero:target
                               regwi 1, $27, 0; //awg_1:bias_t_pre_zero:reserved_start
                               regwi 1, $28, 0; //awg_1:bias_t_pre_zero:duration
                               regwi 1, $29, 0; //awg_1:bias_t_pre_zero:step
                               regwi 1, $30, 16842752;//awg_1:bias_t_pre_zero:control
                               regwi 1, $31, 1035;//bias_t_pre_zero t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:bias_t_pre_zero
                               regwi 2, $16, 0; //awg_2:bias_t_pre_zero:target
                               regwi 2, $17, 0; //awg_2:bias_t_pre_zero:reserved_start
                               regwi 2, $18, 0; //awg_2:bias_t_pre_zero:duration
                               regwi 2, $19, 0; //awg_2:bias_t_pre_zero:step
                               regwi 2, $20, 16842752;//awg_2:bias_t_pre_zero:control
                               regwi 2, $21, 1035;//bias_t_pre_zero t
                               set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:bias_t_pre_zero
                               synci 1053;
                               synci 1;         //common Bias-T guard after pre-compensation zero
                               regwi 1, $10, 916259689;//target = 0xda740da7
                               bitwi 1, $10, $10 << 2;
                               mathi 1, $10, $10 + 3;
                               regwi 1, $11, 894784;//reserved_start = 0x000da740
                               regwi 1, $12, 300;//duration = 0x0000012c
                               regwi 1, $13, 0; //step = 0x00000000
                               regwi 1, $14, 21692416;//control = 0x014b0000
                               regwi 1, $15, 96;//t = 96
                               set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                               regwi 1, $26, 916259689;//target = 0xda740da7
                               bitwi 1, $26, $26 << 2;
                               mathi 1, $26, $26 + 3;
                               regwi 1, $27, 894784;//reserved_start = 0x000da740
                               regwi 1, $28, 300;//duration = 0x0000012c
                               regwi 1, $29, 0; //step = 0x00000000
                               regwi 1, $30, 21692416;//control = 0x014b0000
                               regwi 1, $31, 96;//t = 96
                               set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                               regwi 2, $16, 916259689;//target = 0xda740da7
                               bitwi 2, $16, $16 << 2;
                               mathi 2, $16, $16 + 3;
                               regwi 2, $17, 894784;//reserved_start = 0x000da740
                               regwi 2, $18, 300;//duration = 0x0000012c
                               regwi 2, $19, 0; //step = 0x00000000
                               regwi 2, $20, 21692416;//control = 0x014b0000
                               regwi 2, $21, 96;//t = 96
                               set 2, 2, $16, $17, $18, $19, $20, $21;//ch = 5, pulse @t = $21
                               regwi 1, $10, 445;//wait for hardware DC area completion and IIR flush
                               sync 1, $10;     //hardware DC compensation and capture complete
                               synci 1;         //separate Bias-T stop from the next sweep point
                               synci 20;        //post Bias-T shot recovery
                               regwi 0, $16, 64;//out = 0b0000000001000000
                               seti 7, 0, $16, 0;//ch =0 out = $16 @t = 0
                               seti 7, 0, $0, 30;//ch =0 out = 0 @t = 0
                               synci 31;        //complete external end marker
                               mathi 0, $13, $13 + 1;
                               condj 0, $13, ==, $14, @DEFER_FINAL_ACQUISITION_COUNT;
                               memwi 0, $13, 1;
DEFER_FINAL_ACQUISITION_COUNT: loopnz 0, $15, @FINE_TUNE_REP;
                               loopnz 0, $1, @FINE_TUNE_ADVANCE_0;
                               waiti 0, 0;      //wait for experiment epilogue
                               memwi 0, $13, 1;
                               end ;
FINE_TUNE_ADVANCE_0:           mathi 1, $1, $1 + 408;//advance axis 0 (0, 0, 0, 'target')
                               mathi 1, $2, $2 + -140;//advance axis 0 (0, 1, 0, 'target')
                               mathi 2, $1, $1 + 52;//advance axis 0 (0, 2, 0, 'target')
                               mathi 1, $3, $3 + -111528;//advance axis 0 (1, 0, 0, 'step')
                               mathi 1, $4, $4 + 38269;//advance axis 0 (1, 1, 0, 'step')
                               mathi 2, $2, $2 + -14214;//advance axis 0 (1, 2, 0, 'step')
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;