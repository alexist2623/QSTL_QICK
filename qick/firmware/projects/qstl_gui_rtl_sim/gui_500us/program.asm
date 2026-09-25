
// Program

                               regwi 2, $22, 170009122;//freq = 170009122
                               regwi 2, $23, 0; //phase = 0
                               regwi 2, $25, 2000;//gain = 2000
                               regwi 2, $26, 591324;//phrst| stdysel | mode | | outsel = 0b01001 | length = 1500 
                               regwi 4, $22, 340018244;//freq = 340018244
                               regwi 4, $26, 327679;//mode | outsel = 0b00100 | length = 65535 
                               regwi 0, $13, 0;
                               regwi 0, $14, 2; //final acquisition count
                               regwi 3, $1, 16; //initialize ('square_point_table', 7, 'amplitude') DMEM pointer
                               regwi 0, $1, 1;  //initialize sweep axis 0 counter
                               synci 128;
                               synci 256;       //initial lookahead for SquarePulse and external markers
FINE_TUNE_POINT:               regwi 0, $15, 0;
FINE_TUNE_REP:                 regwi 3, $14, 1790;//freq = 1790
                               regwi 3, $15, 805306368;//phase = 3221225472
                               bitwi 3, $15, $15 << 2;
                               regwi 3, $16, 820;//gain = 820
                               regwi 3, $17, 0; //reserved = 0
                               regwi 3, $18, 16777217;//control = 16777217
                               memr 3, $16, $1; //load SquarePulse hardware sweep word
                               regwi 3, $19, 0; //t = 0
                               set 3, 3, $14, $15, $16, $17, $18, $19;//ch = 7, pulse @t = $19
                               synci 8;
                               regwi 4, $27, 0; //readout 0 t
                               set 4, 4, $22, $0, $26, $0, $26, $27;//readout 0
                               regwi 1, $10, 408;//awg_0:set_0:target
                               regwi 1, $11, 0; //awg_0:set_0:reserved_start
                               regwi 1, $12, 0; //awg_0:set_0:duration
                               regwi 1, $13, 0; //awg_0:set_0:step
                               regwi 1, $14, 16842752;//awg_0:set_0:control
                               regwi 1, $15, 0; //set_0 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_0
                               condj 0, $13, ==, $0, @OUTPUT_MARKER_1_MERGED;
                               regwi 0, $16, 32;//out = 0b0000000000100000
                               seti 7, 0, $16, 600;//ch =0 out = $16 @t = 600
                               seti 7, 0, $0, 612;//ch =0 out = 0 @t = 600
                               condj 0, $0, ==, $0, @OUTPUT_MARKER_1_DONE;
OUTPUT_MARKER_1_MERGED:        regwi 0, $17, 600;//readout trigger start
                               mathi 0, $18, $17 + 12;//readout trigger end
                               regwi 0, $19, 111;//external marker end
                               regwi 0, $20, 0; //external marker start
                               condj 0, $17, ==, $20, @OUTPUT_MARKER_1_NO_START;
                               regwi 0, $16, 64;//combined external/readout trigger bits
                               set 7, 0, $16, $0, $0, $0, $0, $20;//merged trigger edge
OUTPUT_MARKER_1_NO_START:      condj 0, $17, >, $19, @OUTPUT_MARKER_1_AFTER;
                               condj 0, $17, ==, $19, @OUTPUT_MARKER_1_TOUCH;
                               regwi 0, $16, 96;//combined external/readout trigger bits
                               set 7, 0, $16, $0, $0, $0, $0, $17;//merged trigger edge
                               condj 0, $18, >, $19, @OUTPUT_MARKER_1_STRADDLE;
                               condj 0, $18, ==, $19, @OUTPUT_MARKER_1_SAME_END;
                               regwi 0, $16, 64;//combined external/readout trigger bits
                               set 7, 0, $16, $0, $0, $0, $0, $18;//merged trigger edge
OUTPUT_MARKER_1_SAME_END:      regwi 0, $16, 0; //combined external/readout trigger bits
                               set 7, 0, $16, $0, $0, $0, $0, $19;//merged trigger edge
                               condj 0, $0, ==, $0, @OUTPUT_MARKER_1_DONE;
OUTPUT_MARKER_1_STRADDLE:      regwi 0, $16, 32;//combined external/readout trigger bits
                               set 7, 0, $16, $0, $0, $0, $0, $19;//merged trigger edge
                               regwi 0, $16, 0; //combined external/readout trigger bits
                               set 7, 0, $16, $0, $0, $0, $0, $18;//merged trigger edge
                               condj 0, $0, ==, $0, @OUTPUT_MARKER_1_DONE;
OUTPUT_MARKER_1_AFTER:         regwi 0, $16, 0; //combined external/readout trigger bits
                               set 7, 0, $16, $0, $0, $0, $0, $19;//merged trigger edge
OUTPUT_MARKER_1_TOUCH:         regwi 0, $16, 32;//combined external/readout trigger bits
                               set 7, 0, $16, $0, $0, $0, $0, $17;//merged trigger edge
                               regwi 0, $16, 0; //combined external/readout trigger bits
                               set 7, 0, $16, $0, $0, $0, $0, $18;//merged trigger edge
OUTPUT_MARKER_1_DONE:          regwi 2, $22, 170009122;//freq = 170009122
                               regwi 2, $23, 0; //phase = 0
                               regwi 2, $25, 2000;//gain = 2000
                               regwi 2, $26, 591324;//phrst| stdysel | mode | | outsel = 0b01001 | length = 1500 
                               regwi 2, $27, 900;//RF duration-sweep start
                               set 3, 2, $22, $23, $0, $25, $26, $27;//RF duration-sweep start
                               regwi 1, $10, 1073741773;//awg_0:ramp_0_to_1:target
                               bitwi 1, $10, $10 << 2;
                               regwi 1, $11, 0; //awg_0:ramp_0_to_1:reserved_start
                               regwi 1, $12, 2400;//awg_0:ramp_0_to_1:duration
                               regwi 1, $13, 16760498;//awg_0:ramp_0_to_1:step
                               regwi 1, $14, 16908288;//awg_0:ramp_0_to_1:control
                               regwi 1, $15, 97493;//ramp_0_to_1 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_0_to_1
                               regwi 1, $10, 1073741773;//awg_0:set_1:target
                               bitwi 1, $10, $10 << 2;
                               regwi 1, $11, 0; //awg_0:set_1:reserved_start
                               regwi 1, $12, 0; //awg_0:set_1:duration
                               regwi 1, $13, 0; //awg_0:set_1:step
                               regwi 1, $14, 16842752;//awg_0:set_1:control
                               regwi 1, $15, 97651;//set_1 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_1
                               synci 100521;
                               mathi 0, $13, $13 + 1;
                               condj 0, $13, ==, $14, @DEFER_FINAL_ACQUISITION_COUNT;
                               memwi 0, $13, 1;
DEFER_FINAL_ACQUISITION_COUNT: loopnz 0, $15, @FINE_TUNE_REP;
                               loopnz 0, $1, @FINE_TUNE_ADVANCE_0;
                               regwi 3, $18, 16777216;//mute SquarePulse without changing phase rate
                               regwi 3, $19, 0; //t = 0
                               set 3, 3, $14, $15, $16, $17, $18, $19;//ch = 7, pulse @t = $19
                               synci 8;
                               regwi 0, $16, 64;//out = 0b0000000001000000
                               seti 7, 0, $16, 0;//ch =0 out = $16 @t = 0
                               seti 7, 0, $0, 111;//ch =0 out = 0 @t = 0
                               synci 112;       //complete external end marker
                               waiti 0, 0;      //wait for experiment epilogue
                               memwi 0, $13, 1;
                               end ;
FINE_TUNE_ADVANCE_0:           mathi 3, $1, $1 + 1;//advance axis 0 ('square_point_table', 7, 'amplitude') pointer
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;