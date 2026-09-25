
// Program

                               regwi 2, $22, 170009122;//freq = 170009122
                               regwi 2, $23, 0; //phase = 0
                               regwi 2, $25, 2000;//gain = 2000
                               regwi 2, $26, 589974;//phrst| stdysel | mode | | outsel = 0b01001 | length = 150 
                               regwi 0, $13, 0;
                               regwi 0, $14, 36;//final acquisition count
                               regwi 1, $1, -408;//initialize direct sweep state (0, 0, 0, 'target')
                               regwi 1, $2, 16718;//initialize direct sweep state (1, 0, 0, 'step')
                               regwi 1, $3, 2400;//initialize direct sweep state (1, 0, 0, 'duration')
                               regwi 1, $4, 443;//initialize direct sweep state ('event_time', 'awg', 1, 0, 0)
                               regwi 1, $5, 601;//initialize direct sweep state ('event_time', 'awg', 2, 0, 0)
                               regwi 1, $6, 16; //initialize RAMP-rate table pointer
                               memr 1, $2, $6;  //load initial RAMP-rate row (1, 0, 0, 'step')
                               mathi 1, $6, $6 + 1;//advance initial RAMP-rate column 0
                               memr 1, $11, $6; //load initial RAMP-rate axis coefficient
                               memwi 1, $11, 4095;//store initial RAMP-rate axis coefficient
                               mathi 1, $6, $6 + 1;//advance initial RAMP-rate column 1
                               memr 1, $11, $6; //load initial RAMP-rate axis coefficient
                               memwi 1, $11, 4094;//store initial RAMP-rate axis coefficient
                               mathi 1, $6, $6 + 1;//advance initial RAMP-rate column 2
                               memwi 1, $6, 4093;//store initial RAMP-rate table pointer
                               regwi 0, $1, 1;  //initialize sweep axis 0 counter
                               regwi 0, $2, 1;  //initialize sweep axis 1 counter
                               regwi 0, $3, 2;  //initialize sweep axis 2 counter
                               synci 128;
                               synci 256;       //initial lookahead for SquarePulse and external markers
FINE_TUNE_POINT:               regwi 0, $15, 2;
FINE_TUNE_REP:                 regwi 3, $14, 35791;//freq = 35791
                               regwi 3, $15, 0; //phase = 0
                               regwi 3, $16, 820;//gain = 820
                               regwi 3, $17, 0; //reserved = 0
                               regwi 3, $18, 16777217;//control = 16777217
                               regwi 3, $19, 0; //t = 0
                               set 3, 3, $14, $15, $16, $17, $18, $19;//ch = 7, pulse @t = $19
                               synci 8;
                               regwi 0, $16, 64;//out = 0b0000000001000000
                               seti 7, 0, $16, 0;//ch =0 out = $16 @t = 0
                               seti 7, 0, $0, 111;//ch =0 out = 0 @t = 0
                               mathi 1, $10, $1 + 0;//awg_0:set_0:target
                               regwi 1, $11, 0; //awg_0:set_0:reserved_start
                               regwi 1, $12, 0; //awg_0:set_0:duration
                               regwi 1, $13, 0; //awg_0:set_0:step
                               regwi 1, $14, 16842752;//awg_0:set_0:control
                               regwi 1, $15, 0; //set_0 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_0
                               regwi 2, $22, 170009122;//freq = 170009122
                               regwi 2, $23, 0; //phase = 0
                               regwi 2, $25, 2000;//gain = 2000
                               regwi 2, $26, 589974;//phrst| stdysel | mode | | outsel = 0b01001 | length = 150 
                               regwi 2, $27, 90;//RF duration-sweep start
                               set 3, 2, $22, $23, $0, $25, $26, $27;//RF duration-sweep start
                               regwi 1, $10, 204;//awg_0:ramp_0_to_1:target
                               regwi 1, $11, 0; //awg_0:ramp_0_to_1:reserved_start
                               mathi 1, $12, $3 + 0;//awg_0:ramp_0_to_1:duration
                               bitwi 1, $13, $2 & 16777215;//awg_0:ramp_0_to_1:step
                               regwi 1, $14, 16908288;//awg_0:ramp_0_to_1:control
                               mathi 1, $15, $4 + 0;//copy swept ramp_0_to_1 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_0_to_1
                               regwi 1, $10, 204;//awg_0:set_1:target
                               regwi 1, $11, 0; //awg_0:set_1:reserved_start
                               regwi 1, $12, 0; //awg_0:set_1:duration
                               regwi 1, $13, 0; //awg_0:set_1:step
                               regwi 1, $14, 16842752;//awg_0:set_1:control
                               mathi 1, $15, $5 + 0;//copy swept set_1 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_1
                               synci 1371;
                               regwi 0, $16, 64;//out = 0b0000000001000000
                               seti 7, 0, $16, 0;//ch =0 out = $16 @t = 0
                               seti 7, 0, $0, 111;//ch =0 out = 0 @t = 0
                               synci 112;       //complete external end marker
                               mathi 0, $13, $13 + 1;
                               condj 0, $13, ==, $14, @DEFER_FINAL_ACQUISITION_COUNT;
                               memwi 0, $13, 1;
DEFER_FINAL_ACQUISITION_COUNT: loopnz 0, $15, @FINE_TUNE_REP;
                               loopnz 0, $3, @FINE_TUNE_ADVANCE_2;
                               regwi 0, $3, 2;  //reload sweep axis 2 counter
                               mathi 1, $1, $1 + -816;//reset axis 2 (0, 0, 0, 'target')
                               memri 1, $11, 4094;//load RAMP-rate reset axis 2 coefficient
                               math 1, $2, $2 + $11;//RAMP-rate reset axis 2 (1, 0, 0, 'step')
                               loopnz 0, $2, @FINE_TUNE_ADVANCE_1;
                               regwi 0, $2, 1;  //reload sweep axis 1 counter
                               mathi 1, $4, $4 + -300;//reset axis 1 ('event_time', 'awg', 1, 0, 0)
                               mathi 1, $5, $5 + -300;//reset axis 1 ('event_time', 'awg', 2, 0, 0)
                               loopnz 0, $1, @FINE_TUNE_ADVANCE_0;
                               regwi 3, $18, 16777216;//mute SquarePulse without changing phase rate
                               regwi 3, $19, 0; //t = 0
                               set 3, 3, $14, $15, $16, $17, $18, $19;//ch = 7, pulse @t = $19
                               synci 8;
                               waiti 0, 0;      //wait for experiment epilogue
                               memwi 0, $13, 1;
                               end ;
FINE_TUNE_ADVANCE_0:           mathi 1, $3, $3 + 2400;//advance axis 0 (1, 0, 0, 'duration')
                               mathi 1, $5, $5 + 150;//advance axis 0 ('event_time', 'awg', 2, 0, 0)
                               memri 1, $6, 4093;//load RAMP-rate axis 0 table pointer
                               memr 1, $2, $6;  //load axis 0 advance RAMP-rate row (1, 0, 0, 'step')
                               mathi 1, $6, $6 + 1;//advance axis 0 advance RAMP-rate column 0
                               memr 1, $11, $6; //load axis 0 advance RAMP-rate axis coefficient
                               memwi 1, $11, 4095;//store axis 0 advance RAMP-rate axis coefficient
                               mathi 1, $6, $6 + 1;//advance axis 0 advance RAMP-rate column 1
                               memr 1, $11, $6; //load axis 0 advance RAMP-rate axis coefficient
                               memwi 1, $11, 4094;//store axis 0 advance RAMP-rate axis coefficient
                               mathi 1, $6, $6 + 1;//advance axis 0 advance RAMP-rate column 2
                               memwi 1, $6, 4093;//store axis 0 advance RAMP-rate table pointer
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;
FINE_TUNE_ADVANCE_1:           mathi 1, $4, $4 + 300;//advance axis 1 ('event_time', 'awg', 1, 0, 0)
                               mathi 1, $5, $5 + 300;//advance axis 1 ('event_time', 'awg', 2, 0, 0)
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;
FINE_TUNE_ADVANCE_2:           mathi 1, $1, $1 + 408;//advance axis 2 (0, 0, 0, 'target')
                               memri 1, $11, 4095;//load RAMP-rate advance axis 2 coefficient
                               math 1, $2, $2 + $11;//RAMP-rate advance axis 2 (1, 0, 0, 'step')
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;