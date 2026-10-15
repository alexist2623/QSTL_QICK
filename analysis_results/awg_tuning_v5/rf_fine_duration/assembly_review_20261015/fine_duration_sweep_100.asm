
// Program

                     regwi 0, $13, 0;
                     regwi 0, $1, 16;           //initialize ('rf_point_table', 0, 'fine_duration') DMEM pointer
                     regwi 0, $2, 99;           //initialize sweep axis 0 counter
                     synci 128;
FINE_TUNE_POINT:     regwi 0, $15, 0;
FINE_TUNE_REP:       regwi 1, $26, 328;         //awg_0:gate:target
                     regwi 1, $27, 0;           //awg_0:gate:reserved_start
                     regwi 1, $28, 0;           //awg_0:gate:duration
                     regwi 1, $29, 0;           //awg_0:gate:step
                     regwi 1, $30, 16842752;    //awg_0:gate:control
                     regwi 1, $31, 0;           //gate t
                     set 0, 1, $26, $27, $28, $29, $30, $31;//awg_0:gate
                     memr 0, $27, $1;           //load fine RF t
                     mathi 0, $1, $1 + 1;
                     memr 0, $26, $1;           //load fine RF mode
                     mathi 0, $1, $1 + 1;
                     memr 0, $24, $1;           //load fine RF addr
                     mathi 0, $1, $1 + 1;
                     memr 0, $30, $1;           //load fine RF mode2
                     mathi 0, $1, $1 + 1;
                     memr 0, $28, $1;           //load fine RF addr2
                     mathi 0, $1, $1 + 1;
                     memr 0, $31, $1;           //load fine RF mode3
                     mathi 0, $1, $1 + -5;      //restore fine RF row pointer
                     regwi 0, $22, 143165577;   //fine RF freq
                     regwi 0, $23, 536870912;   //fine RF phase
                     regwi 0, $25, 2000;        //fine RF gain
                     set 0, 0, $22, $23, $24, $25, $26, $27;//fine RF start
                     bitwi 0, $25, $25 << 1;    //compensate product envelope scaling
                     set 0, 0, $22, $23, $24, $25, $30, $28;//fine RF ending pattern
                     synci 400020;
                     mathi 0, $13, $13 + 1;
                     memwi 0, $13, 1;
                     loopnz 0, $15, @FINE_TUNE_REP;
                     loopnz 0, $2, @FINE_TUNE_ADVANCE_0;
                     end ;
FINE_TUNE_ADVANCE_0: mathi 0, $1, $1 + 6;       //advance axis 0 ('rf_point_table', 0, 'fine_duration') pointer
                     condj 0, $0, ==, $0, @FINE_TUNE_POINT;