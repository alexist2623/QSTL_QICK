
// Program

                     regwi 0, $22, 143165577;   //freq = 143165577
                     regwi 0, $23, 536870912;   //phase = 536870912
                     regwi 0, $25, 2000;        //gain = 2000
                     regwi 0, $26, 590124;      //phrst| stdysel | mode | | outsel = 0b01001 | length = 300 
                     regwi 0, $13, 0;
                     regwi 0, $2, 330;          //initialize direct sweep state ('event_time', 'rf_stop', 0)
                     regwi 0, $1, 16;           //initialize ('rf_point_table', 0, 'duration') DMEM pointer
                     regwi 0, $3, 15;           //initialize sweep axis 0 counter
                     synci 128;
FINE_TUNE_POINT:     regwi 0, $15, 0;
FINE_TUNE_REP:       regwi 1, $26, 328;         //awg_0:gate:target
                     regwi 1, $27, 0;           //awg_0:gate:reserved_start
                     regwi 1, $28, 0;           //awg_0:gate:duration
                     regwi 1, $29, 0;           //awg_0:gate:step
                     regwi 1, $30, 16842752;    //awg_0:gate:control
                     regwi 1, $31, 0;           //gate t
                     set 0, 1, $26, $27, $28, $29, $30, $31;//awg_0:gate
                     regwi 0, $22, 143165577;   //freq = 143165577
                     regwi 0, $23, 536870912;   //phase = 536870912
                     regwi 0, $25, 2000;        //gain = 2000
                     regwi 0, $26, 590124;      //phrst| stdysel | mode | | outsel = 0b01001 | length = 300 
                     memr 0, $26, $1;           //load swept rf_duration from DMEM
                     regwi 0, $27, 30;          //RF duration-sweep start
                     set 0, 0, $22, $23, $0, $25, $26, $27;//RF duration-sweep start
                     synci 400020;
                     mathi 0, $13, $13 + 1;
                     memwi 0, $13, 1;
                     loopnz 0, $15, @FINE_TUNE_REP;
                     loopnz 0, $3, @FINE_TUNE_ADVANCE_0;
                     end ;
FINE_TUNE_ADVANCE_0: mathi 0, $1, $1 + 1;       //advance axis 0 ('rf_point_table', 0, 'duration') pointer
                     mathi 0, $2, $2 + 1;       //advance axis 0 ('event_time', 'rf_stop', 0)
                     condj 0, $0, ==, $0, @FINE_TUNE_POINT;