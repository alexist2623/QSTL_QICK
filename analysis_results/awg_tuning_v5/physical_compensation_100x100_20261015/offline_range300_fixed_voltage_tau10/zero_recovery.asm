
// Program

                 synci 200;
                 regwi 1, $10, 0;               //target = 0x00000000
                 regwi 1, $11, 0;               //reserved_start = 0x00000000
                 regwi 1, $12, 0;               //duration = 0x00000000
                 regwi 1, $13, 0;               //step = 0x00000000
                 regwi 1, $14, 19595264;        //control = 0x012b0000
                 regwi 1, $15, 0;               //t = 0
                 set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                 regwi 1, $26, 0;               //target = 0x00000000
                 regwi 1, $27, 0;               //reserved_start = 0x00000000
                 regwi 1, $28, 0;               //duration = 0x00000000
                 regwi 1, $29, 0;               //step = 0x00000000
                 regwi 1, $30, 19595264;        //control = 0x012b0000
                 regwi 1, $31, 0;               //t = 0
                 set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                 synci 100;
                 synci 256;
                 regwi 1, $10, 0;               //target = 0x00000000
                 regwi 1, $11, 0;               //reserved_start = 0x00000000
                 regwi 1, $12, 0;               //duration = 0x00000000
                 regwi 1, $13, 0;               //step = 0x00000000
                 regwi 1, $14, 16842752;        //control = 0x01010000
                 regwi 1, $15, 0;               //t = 0
                 set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                 regwi 1, $26, 0;               //target = 0x00000000
                 regwi 1, $27, 0;               //reserved_start = 0x00000000
                 regwi 1, $28, 0;               //duration = 0x00000000
                 regwi 1, $29, 0;               //step = 0x00000000
                 regwi 1, $30, 16842752;        //control = 0x01010000
                 regwi 1, $31, 0;               //t = 0
                 set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                 synci 256;
                 regwi 1, $10, 0;               //target = 0x00000000
                 regwi 1, $11, 0;               //reserved_start = 0x00000000
                 regwi 1, $12, 0;               //duration = 0x00000000
                 regwi 1, $13, 0;               //step = 0x00000000
                 regwi 1, $14, 21954560;        //control = 0x014f0000
                 regwi 1, $15, 0;               //t = 0
                 set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                 regwi 1, $26, 0;               //target = 0x00000000
                 regwi 1, $27, 0;               //reserved_start = 0x00000000
                 regwi 1, $28, 0;               //duration = 0x00000000
                 regwi 1, $29, 0;               //step = 0x00000000
                 regwi 1, $30, 21954560;        //control = 0x014f0000
                 regwi 1, $31, 0;               //t = 0
                 set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                 synci 256;
                 regwi 0, $13, 0;
                 synci 128;
FINE_TUNE_POINT: regwi 0, $15, 0;
FINE_TUNE_REP:   regwi 1, $10, 0;               //awg_0:set_0:target
                 regwi 1, $11, 0;               //awg_0:set_0:reserved_start
                 regwi 1, $12, 0;               //awg_0:set_0:duration
                 regwi 1, $13, 0;               //awg_0:set_0:step
                 regwi 1, $14, 16842752;        //awg_0:set_0:control
                 regwi 1, $15, 0;               //set_0 t
                 set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_0
                 regwi 1, $26, 0;               //awg_1:set_0:target
                 regwi 1, $27, 0;               //awg_1:set_0:reserved_start
                 regwi 1, $28, 0;               //awg_1:set_0:duration
                 regwi 1, $29, 0;               //awg_1:set_0:step
                 regwi 1, $30, 16842752;        //awg_1:set_0:control
                 regwi 1, $31, 0;               //set_0 t
                 set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_0
                 synci 3051;
                 mathi 0, $13, $13 + 1;
                 memwi 0, $13, 1;
                 loopnz 0, $15, @FINE_TUNE_REP;
                 end ;