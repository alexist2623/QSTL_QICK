
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
                 regwi 2, $16, 0;               //target = 0x00000000
                 regwi 2, $17, 0;               //reserved_start = 0x00000000
                 regwi 2, $18, 0;               //duration = 0x00000000
                 regwi 2, $19, 0;               //step = 0x00000000
                 regwi 2, $20, 19595264;        //control = 0x012b0000
                 regwi 2, $21, 0;               //t = 0
                 set 2, 2, $16, $17, $18, $19, $20, $21;//ch = 5, pulse @t = $21
                 synci 100;
                 synci 384;
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
                 regwi 2, $16, 0;               //target = 0x00000000
                 regwi 2, $17, 0;               //reserved_start = 0x00000000
                 regwi 2, $18, 0;               //duration = 0x00000000
                 regwi 2, $19, 0;               //step = 0x00000000
                 regwi 2, $20, 16842752;        //control = 0x01010000
                 regwi 2, $21, 0;               //t = 0
                 set 2, 2, $16, $17, $18, $19, $20, $21;//ch = 5, pulse @t = $21
                 synci 384;
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
                 regwi 2, $16, 0;               //target = 0x00000000
                 regwi 2, $17, 0;               //reserved_start = 0x00000000
                 regwi 2, $18, 0;               //duration = 0x00000000
                 regwi 2, $19, 0;               //step = 0x00000000
                 regwi 2, $20, 21954560;        //control = 0x014f0000
                 regwi 2, $21, 0;               //t = 0
                 set 2, 2, $16, $17, $18, $19, $20, $21;//ch = 5, pulse @t = $21
                 synci 384;
                 regwi 0, $13, 0;
                 synci 128;
FINE_TUNE_POINT: regwi 0, $15, 0;
FINE_TUNE_REP:   regwi 1, $10, 124;             //awg_0:set_0:target
                 regwi 1, $11, 0;               //awg_0:set_0:reserved_start
                 regwi 1, $12, 0;               //awg_0:set_0:duration
                 regwi 1, $13, 0;               //awg_0:set_0:step
                 regwi 1, $14, 16842752;        //awg_0:set_0:control
                 regwi 1, $15, 0;               //set_0 t
                 set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_0
                 regwi 1, $26, 1073741746;      //awg_1:set_0:target
                 bitwi 1, $26, $26 << 2;
                 regwi 1, $27, 0;               //awg_1:set_0:reserved_start
                 regwi 1, $28, 0;               //awg_1:set_0:duration
                 regwi 1, $29, 0;               //awg_1:set_0:step
                 regwi 1, $30, 16842752;        //awg_1:set_0:control
                 regwi 1, $31, 0;               //set_0 t
                 set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_0
                 regwi 2, $16, 172;             //awg_2:set_0:target
                 regwi 2, $17, 0;               //awg_2:set_0:reserved_start
                 regwi 2, $18, 0;               //awg_2:set_0:duration
                 regwi 2, $19, 0;               //awg_2:set_0:step
                 regwi 2, $20, 16842752;        //awg_2:set_0:control
                 regwi 2, $21, 0;               //set_0 t
                 set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:set_0
                 regwi 1, $10, 484;             //awg_0:ramp_0_to_1:target
                 regwi 1, $11, 0;               //awg_0:ramp_0_to_1:reserved_start
                 regwi 1, $12, 4800;            //awg_0:ramp_0_to_1:duration
                 regwi 1, $13, 19664;           //awg_0:ramp_0_to_1:step
                 regwi 1, $14, 16908288;        //awg_0:ramp_0_to_1:control
                 regwi 1, $15, 293;             //ramp_0_to_1 t
                 set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_0_to_1
                 regwi 1, $26, 1073741491;      //awg_1:ramp_0_to_1:target
                 bitwi 1, $26, $26 << 2;
                 regwi 1, $27, 0;               //awg_1:ramp_0_to_1:reserved_start
                 regwi 1, $28, 4800;            //awg_1:ramp_0_to_1:duration
                 regwi 1, $29, 1073727894;      //awg_1:ramp_0_to_1:step
                 bitwi 1, $29, $29 << 2;
                 mathi 1, $29, $29 + 3;
                 regwi 1, $30, 16908288;        //awg_1:ramp_0_to_1:control
                 regwi 1, $31, 293;             //ramp_0_to_1 t
                 set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_0_to_1
                 regwi 2, $16, 700;             //awg_2:ramp_0_to_1:target
                 regwi 2, $17, 0;               //awg_2:ramp_0_to_1:reserved_start
                 regwi 2, $18, 4800;            //awg_2:ramp_0_to_1:duration
                 regwi 2, $19, 28841;           //awg_2:ramp_0_to_1:step
                 regwi 2, $20, 16908288;        //awg_2:ramp_0_to_1:control
                 regwi 2, $21, 293;             //ramp_0_to_1 t
                 set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:ramp_0_to_1
                 regwi 1, $10, 484;             //awg_0:set_1:target
                 regwi 1, $11, 0;               //awg_0:set_1:reserved_start
                 regwi 1, $12, 0;               //awg_0:set_1:duration
                 regwi 1, $13, 0;               //awg_0:set_1:step
                 regwi 1, $14, 16842752;        //awg_0:set_1:control
                 regwi 1, $15, 601;             //set_1 t
                 set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_1
                 regwi 1, $26, 1073741491;      //awg_1:set_1:target
                 bitwi 1, $26, $26 << 2;
                 regwi 1, $27, 0;               //awg_1:set_1:reserved_start
                 regwi 1, $28, 0;               //awg_1:set_1:duration
                 regwi 1, $29, 0;               //awg_1:set_1:step
                 regwi 1, $30, 16842752;        //awg_1:set_1:control
                 regwi 1, $31, 601;             //set_1 t
                 set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_1
                 regwi 2, $16, 700;             //awg_2:set_1:target
                 regwi 2, $17, 0;               //awg_2:set_1:reserved_start
                 regwi 2, $18, 0;               //awg_2:set_1:duration
                 regwi 2, $19, 0;               //awg_2:set_1:step
                 regwi 2, $20, 16842752;        //awg_2:set_1:control
                 regwi 2, $21, 601;             //set_1 t
                 set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:set_1
                 regwi 1, $10, 1073741764;      //awg_0:ramp_1_to_2:target
                 bitwi 1, $10, $10 << 2;
                 regwi 1, $11, 0;               //awg_0:ramp_1_to_2:reserved_start
                 regwi 1, $12, 4800;            //awg_0:ramp_1_to_2:duration
                 regwi 1, $13, 1073731937;      //awg_0:ramp_1_to_2:step
                 bitwi 1, $13, $13 << 2;
                 regwi 1, $14, 16908288;        //awg_0:ramp_1_to_2:control
                 regwi 1, $15, 30594;           //ramp_1_to_2 t
                 set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_1_to_2
                 regwi 1, $26, 668;             //awg_1:ramp_1_to_2:target
                 regwi 1, $27, 0;               //awg_1:ramp_1_to_2:reserved_start
                 regwi 1, $28, 4800;            //awg_1:ramp_1_to_2:duration
                 regwi 1, $29, 109249;          //awg_1:ramp_1_to_2:step
                 regwi 1, $30, 16908288;        //awg_1:ramp_1_to_2:control
                 regwi 1, $31, 30594;           //ramp_1_to_2 t
                 set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_1_to_2
                 regwi 2, $16, 1073741736;      //awg_2:ramp_1_to_2:target
                 bitwi 2, $16, $16 << 2;
                 regwi 2, $17, 0;               //awg_2:ramp_1_to_2:reserved_start
                 regwi 2, $18, 4800;            //awg_2:ramp_1_to_2:duration
                 regwi 2, $19, 1073727457;      //awg_2:ramp_1_to_2:step
                 bitwi 2, $19, $19 << 2;
                 mathi 2, $19, $19 + 3;
                 regwi 2, $20, 16908288;        //awg_2:ramp_1_to_2:control
                 regwi 2, $21, 30594;           //ramp_1_to_2 t
                 set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:ramp_1_to_2
                 regwi 1, $10, 1073741764;      //awg_0:set_2:target
                 bitwi 1, $10, $10 << 2;
                 regwi 1, $11, 0;               //awg_0:set_2:reserved_start
                 regwi 1, $12, 0;               //awg_0:set_2:duration
                 regwi 1, $13, 0;               //awg_0:set_2:step
                 regwi 1, $14, 16842752;        //awg_0:set_2:control
                 regwi 1, $15, 30902;           //set_2 t
                 set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_2
                 regwi 1, $26, 668;             //awg_1:set_2:target
                 regwi 1, $27, 0;               //awg_1:set_2:reserved_start
                 regwi 1, $28, 0;               //awg_1:set_2:duration
                 regwi 1, $29, 0;               //awg_1:set_2:step
                 regwi 1, $30, 16842752;        //awg_1:set_2:control
                 regwi 1, $31, 30902;           //set_2 t
                 set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_2
                 regwi 2, $16, 1073741736;      //awg_2:set_2:target
                 bitwi 2, $16, $16 << 2;
                 regwi 2, $17, 0;               //awg_2:set_2:reserved_start
                 regwi 2, $18, 0;               //awg_2:set_2:duration
                 regwi 2, $19, 0;               //awg_2:set_2:step
                 regwi 2, $20, 16842752;        //awg_2:set_2:control
                 regwi 2, $21, 30902;           //set_2 t
                 set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:set_2
                 synci 31253;
                 mathi 0, $13, $13 + 1;
                 memwi 0, $13, 1;
                 loopnz 0, $15, @FINE_TUNE_REP;
                 end ;