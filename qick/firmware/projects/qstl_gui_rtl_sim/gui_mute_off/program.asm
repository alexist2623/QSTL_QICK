
// Program

                               regwi 0, $13, 0;
                               regwi 0, $14, 2; //final acquisition count
                               regwi 3, $1, 16; //initialize ('square_point_table', 7, 'amplitude') DMEM pointer
                               regwi 0, $1, 1;  //initialize sweep axis 0 counter
                               synci 128;
                               synci 128;       //initial lookahead for SquarePulse and external markers
FINE_TUNE_POINT:               regwi 0, $15, 0;
FINE_TUNE_REP:                 regwi 3, $14, 1790;//freq = 1790
                               regwi 3, $15, 536870912;//phase = 536870912
                               regwi 3, $16, 408;//gain = 408
                               regwi 3, $17, 0; //reserved = 0
                               regwi 3, $18, 16777217;//control = 16777217
                               memr 3, $16, $1; //load SquarePulse hardware sweep word
                               regwi 3, $19, 0; //t = 0
                               set 3, 3, $14, $15, $16, $17, $18, $19;//ch = 7, pulse @t = $19
                               synci 8;
                               regwi 1, $10, 408;//awg_0:set_0:target
                               regwi 1, $11, 0; //awg_0:set_0:reserved_start
                               regwi 1, $12, 0; //awg_0:set_0:duration
                               regwi 1, $13, 0; //awg_0:set_0:step
                               regwi 1, $14, 16842752;//awg_0:set_0:control
                               regwi 1, $15, 0; //set_0 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_0
                               synci 3020;
                               mathi 0, $13, $13 + 1;
                               condj 0, $13, ==, $14, @DEFER_FINAL_ACQUISITION_COUNT;
                               memwi 0, $13, 1;
DEFER_FINAL_ACQUISITION_COUNT: loopnz 0, $15, @FINE_TUNE_REP;
                               loopnz 0, $1, @FINE_TUNE_ADVANCE_0;
                               waiti 0, 0;      //wait for experiment epilogue
                               memwi 0, $13, 1;
                               end ;
FINE_TUNE_ADVANCE_0:           mathi 3, $1, $1 + 1;//advance axis 0 ('square_point_table', 7, 'amplitude') pointer
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;