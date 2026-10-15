
// Program

                 regwi 0, $13, 0;
                 synci 128;
FINE_TUNE_POINT: regwi 0, $15, 0;
FINE_TUNE_REP:   regwi 1, $26, 328;             //awg_0:gate:target
                 regwi 1, $27, 0;               //awg_0:gate:reserved_start
                 regwi 1, $28, 0;               //awg_0:gate:duration
                 regwi 1, $29, 0;               //awg_0:gate:step
                 regwi 1, $30, 16842752;        //awg_0:gate:control
                 regwi 1, $31, 0;               //gate t
                 set 0, 1, $26, $27, $28, $29, $30, $31;//awg_0:gate
                 regwi 0, $27, 30;              //fine RF t
                 regwi 0, $26, 590121;          //fine RF mode
                 regwi 0, $24, 10;              //fine RF addr
                 regwi 0, $22, 143165577;       //fine RF freq
                 regwi 0, $23, 536870912;       //fine RF phase
                 regwi 0, $25, 2000;            //fine RF gain
                 set 0, 0, $22, $23, $24, $25, $26, $27;//fine RF start
                 bitwi 0, $25, $25 << 1;        //compensate product envelope scaling
                 regwi 0, $26, 524292;          //fine RF tail mode
                 regwi 0, $27, 327;             //fine RF tail time
                 set 0, 0, $22, $23, $24, $25, $26, $27;//fine RF ending pattern
                 synci 400020;
                 mathi 0, $13, $13 + 1;
                 memwi 0, $13, 1;
                 loopnz 0, $15, @FINE_TUNE_REP;
                 end ;