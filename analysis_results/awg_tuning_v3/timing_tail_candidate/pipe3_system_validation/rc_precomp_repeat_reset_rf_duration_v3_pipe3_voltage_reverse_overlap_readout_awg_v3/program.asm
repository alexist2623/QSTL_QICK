
// Program

                               regwi 0, $22, 170009122;//freq = 170009122
                               regwi 0, $23, 0; //phase = 0
                               regwi 0, $25, 2000;//gain = 2000
                               regwi 0, $26, 589854;//phrst| stdysel | mode | | outsel = 0b01001 | length = 30 
                               regwi 4, $22, 0; //freq = 0
                               regwi 4, $26, 327679;//mode | outsel = 0b00100 | length = 65535 
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
                               synci 100;
                               synci 256;
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
                               synci 256;
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
                               synci 256;
                               regwi 0, $13, 0;
                               regwi 0, $14, 200;//final acquisition count
                               regwi 1, $1, 156;//initialize direct sweep state (0, 0, 0, 'target')
                               regwi 1, $2, -480;//initialize direct sweep state (0, 1, 0, 'target')
                               regwi 1, $3, -142142;//initialize direct sweep state (1, 0, 0, 'step')
                               regwi 1, $4, 281005;//initialize direct sweep state (1, 1, 0, 'step')
                               regwi 1, $5, 323;//initialize direct sweep state ('event_time', 'awg', 1, 0, 0)
                               regwi 1, $6, 323;//initialize direct sweep state ('event_time', 'awg', 1, 1, 0)
                               regwi 1, $7, 391;//initialize direct sweep state ('event_time', 'awg', 2, 0, 0)
                               regwi 1, $8, 391;//initialize direct sweep state ('event_time', 'awg', 2, 1, 0)
                               regwi 1, $9, 684;//initialize direct sweep state ('event_time', 'awg', 3, 0, 0)
                               regwi 1, $31, 684;//initialize DMEM sweep state ('event_time', 'awg', 3, 1, 0)
                               memwi 1, $31, 4095;//store initial DMEM sweep state ('event_time', 'awg', 3, 1, 0)
                               regwi 1, $15, 752;//initialize DMEM sweep state ('event_time', 'awg', 4, 0, 0)
                               memwi 1, $15, 4094;//store initial DMEM sweep state ('event_time', 'awg', 4, 0, 0)
                               regwi 1, $31, 752;//initialize DMEM sweep state ('event_time', 'awg', 4, 1, 0)
                               memwi 1, $31, 4093;//store initial DMEM sweep state ('event_time', 'awg', 4, 1, 0)
                               regwi 0, $2, 46; //initialize direct sweep state ('event_time', 'rf_stop', 0)
                               regwi 1, $15, 1052;//initialize DMEM sweep state ('event_time', 'bias_pre_zero', 0)
                               memwi 1, $15, 4092;//store initial DMEM sweep state ('event_time', 'bias_pre_zero', 0)
                               regwi 1, $31, 1052;//initialize DMEM sweep state ('event_time', 'bias_pre_zero', 1)
                               memwi 1, $31, 4091;//store initial DMEM sweep state ('event_time', 'bias_pre_zero', 1)
                               regwi 1, $12, 1068;//initialize DMEM sweep state ('capture_compensation', 'wave_end')
                               memwi 1, $12, 4090;//store initial DMEM sweep state ('capture_compensation', 'wave_end')
                               regwi 1, $12, 46;//initialize DMEM sweep state ('capture_compensation', 'rf_end_0')
                               memwi 1, $12, 4089;//store initial DMEM sweep state ('capture_compensation', 'rf_end_0')
                               regwi 0, $1, 16; //initialize ('rf_point_table', 0, 'duration') DMEM pointer
                               regwi 0, $3, 9;  //initialize sweep axis 0 counter
                               regwi 0, $4, 9;  //initialize sweep axis 1 counter
                               synci 128;
                               synci 128;       //initial lookahead for SquarePulse and external markers
FINE_TUNE_POINT:               regwi 0, $15, 1;
FINE_TUNE_REP:                 regwi 4, $27, 0; //readout 0 t
                               set 4, 4, $22, $0, $26, $0, $26, $27;//readout 0
                               mathi 1, $10, $1 + 0;//awg_0:set_0:target
                               regwi 1, $11, 0; //awg_0:set_0:reserved_start
                               regwi 1, $12, 0; //awg_0:set_0:duration
                               regwi 1, $13, 0; //awg_0:set_0:step
                               regwi 1, $14, 16842752;//awg_0:set_0:control
                               regwi 1, $15, 0; //set_0 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_0
                               mathi 1, $26, $2 + 0;//awg_1:set_0:target
                               regwi 1, $27, 0; //awg_1:set_0:reserved_start
                               regwi 1, $28, 0; //awg_1:set_0:duration
                               regwi 1, $29, 0; //awg_1:set_0:step
                               regwi 1, $30, 16842752;//awg_1:set_0:control
                               regwi 1, $31, 0; //set_0 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_0
                               regwi 0, $22, 170009122;//freq = 170009122
                               regwi 0, $23, 0; //phase = 0
                               regwi 0, $25, 2000;//gain = 2000
                               regwi 0, $26, 589854;//phrst| stdysel | mode | | outsel = 0b01001 | length = 30 
                               memr 0, $26, $1; //load swept rf_duration from DMEM
                               regwi 0, $27, 16;//RF duration-sweep start
                               set 0, 0, $22, $23, $0, $25, $26, $27;//RF duration-sweep start
                               regwi 0, $17, 16;//readout trigger start
                               mathi 0, $18, $17 + 12;//readout trigger end
                               regwi 0, $19, 46;//external marker end
                               regwi 0, $20, 16;//external marker start
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
OUTPUT_MARKER_1_DONE:          regwi 1, $10, 1073741733;//awg_0:ramp_0_to_1:target
                               bitwi 1, $10, $10 << 2;
                               regwi 1, $11, 0; //awg_0:ramp_0_to_1:reserved_start
                               regwi 1, $12, 960;//awg_0:ramp_0_to_1:duration
                               mathi 1, $13, $3 + 0;//awg_0:ramp_0_to_1:step
                               regwi 1, $14, 16908288;//awg_0:ramp_0_to_1:control
                               mathi 1, $15, $5 + 0;//copy swept ramp_0_to_1 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_0_to_1
                               regwi 1, $26, 548;//awg_1:ramp_0_to_1:target
                               regwi 1, $27, 0; //awg_1:ramp_0_to_1:reserved_start
                               regwi 1, $28, 960;//awg_1:ramp_0_to_1:duration
                               mathi 1, $29, $4 + 0;//awg_1:ramp_0_to_1:step
                               regwi 1, $30, 16908288;//awg_1:ramp_0_to_1:control
                               mathi 1, $31, $6 + 0;//copy swept ramp_0_to_1 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_0_to_1
                               regwi 1, $10, 1073741733;//awg_0:set_1:target
                               bitwi 1, $10, $10 << 2;
                               regwi 1, $11, 0; //awg_0:set_1:reserved_start
                               regwi 1, $12, 0; //awg_0:set_1:duration
                               regwi 1, $13, 0; //awg_0:set_1:step
                               regwi 1, $14, 16842752;//awg_0:set_1:control
                               mathi 1, $15, $7 + 0;//copy swept set_1 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_1
                               regwi 1, $26, 548;//awg_1:set_1:target
                               regwi 1, $27, 0; //awg_1:set_1:reserved_start
                               regwi 1, $28, 0; //awg_1:set_1:duration
                               regwi 1, $29, 0; //awg_1:set_1:step
                               regwi 1, $30, 16842752;//awg_1:set_1:control
                               mathi 1, $31, $8 + 0;//copy swept set_1 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_1
                               regwi 1, $10, 0; //awg_0:ramp_1_to_2:target
                               regwi 1, $11, 0; //awg_0:ramp_1_to_2:reserved_start
                               regwi 1, $12, 960;//awg_0:ramp_1_to_2:duration
                               regwi 1, $13, 99499;//awg_0:ramp_1_to_2:step
                               regwi 1, $14, 16908288;//awg_0:ramp_1_to_2:control
                               mathi 1, $15, $9 + 0;//copy swept ramp_1_to_2 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_1_to_2
                               regwi 1, $26, 0; //awg_1:ramp_1_to_2:target
                               regwi 1, $27, 0; //awg_1:ramp_1_to_2:reserved_start
                               regwi 1, $28, 960;//awg_1:ramp_1_to_2:duration
                               regwi 1, $29, 1073704375;//awg_1:ramp_1_to_2:step
                               bitwi 1, $29, $29 << 2;
                               regwi 1, $30, 16908288;//awg_1:ramp_1_to_2:control
                               memri 1, $31, 4095;//load swept ramp_1_to_2 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_1_to_2
                               regwi 1, $10, 0; //awg_0:set_2:target
                               regwi 1, $11, 0; //awg_0:set_2:reserved_start
                               regwi 1, $12, 0; //awg_0:set_2:duration
                               regwi 1, $13, 0; //awg_0:set_2:step
                               regwi 1, $14, 16842752;//awg_0:set_2:control
                               memri 1, $15, 4094;//load swept set_2 t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_2
                               regwi 1, $26, 0; //awg_1:set_2:target
                               regwi 1, $27, 0; //awg_1:set_2:reserved_start
                               regwi 1, $28, 0; //awg_1:set_2:duration
                               regwi 1, $29, 0; //awg_1:set_2:step
                               regwi 1, $30, 16842752;//awg_1:set_2:control
                               memri 1, $31, 4093;//load swept set_2 t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_2
                               regwi 1, $10, 0; //awg_0:bias_t_pre_zero:target
                               regwi 1, $11, 0; //awg_0:bias_t_pre_zero:reserved_start
                               regwi 1, $12, 0; //awg_0:bias_t_pre_zero:duration
                               regwi 1, $13, 0; //awg_0:bias_t_pre_zero:step
                               regwi 1, $14, 16842752;//awg_0:bias_t_pre_zero:control
                               memri 1, $15, 4092;//load swept bias_t_pre_zero t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:bias_t_pre_zero
                               regwi 1, $26, 0; //awg_1:bias_t_pre_zero:target
                               regwi 1, $27, 0; //awg_1:bias_t_pre_zero:reserved_start
                               regwi 1, $28, 0; //awg_1:bias_t_pre_zero:duration
                               regwi 1, $29, 0; //awg_1:bias_t_pre_zero:step
                               regwi 1, $30, 16842752;//awg_1:bias_t_pre_zero:control
                               memri 1, $31, 4091;//load swept bias_t_pre_zero t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:bias_t_pre_zero
                               regwi 1, $10, 0; //start output completion barrier
                               memri 1, $12, 4090;//load swept DC overlap output end
                               condj 1, $10, >=, $12, @DC_OVERLAP_MAX_0;//retain latest output end
                               mathi 1, $10, $12 + 0;//update latest output end
DC_OVERLAP_MAX_0:              mathi 1, $12, $12 + 0;
                               memri 1, $12, 4089;//load swept DC overlap output end
                               condj 1, $10, >=, $12, @DC_OVERLAP_MAX_1;//retain latest output end
                               mathi 1, $10, $12 + 0;//update latest output end
DC_OVERLAP_MAX_1:              mathi 1, $12, $12 + 0;
                               regwi 1, $12, 0; //DC overlap output end
                               condj 1, $10, >=, $12, @DC_OVERLAP_MAX_2;//retain latest output end
                               mathi 1, $10, $12 + 0;//update latest output end
DC_OVERLAP_MAX_2:              mathi 1, $12, $12 + 0;
                               regwi 1, $12, 47;//DC overlap output end
                               condj 1, $10, >=, $12, @DC_OVERLAP_MAX_3;//retain latest output end
                               mathi 1, $10, $12 + 0;//update latest output end
DC_OVERLAP_MAX_3:              mathi 1, $12, $12 + 0;
                               regwi 1, $12, 1216;//DC overlap capture end
                               math 1, $12, $12 - $10;//capture time remaining after output end
                               mathi 1, $12, $12 - 1;//subtract common DC guard
                               condj 1, $12, >=, $0, @DC_OVERLAP_REMAINING;//clamp completed capture to zero
                               regwi 1, $12, 0; //
DC_OVERLAP_REMAINING:          memwi 1, $12, 4088;//save capture completion offset
                               sync 1, $10;     //advance to output end while FIR capture continues
                               synci 1;         //common Bias-T guard after pre-compensation zero
                               regwi 1, $10, 820;//target = 0x00000334
                               regwi 1, $11, 0; //reserved_start = 0x00000000
                               regwi 1, $12, 0; //duration = 0x00000000
                               regwi 1, $13, 0; //step = 0x00000000
                               regwi 1, $14, 21430272;//control = 0x01470000
                               regwi 1, $15, 64;//t = 64
                               set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                               regwi 1, $26, 1640;//target = 0x00000668
                               regwi 1, $27, 0; //reserved_start = 0x00000000
                               regwi 1, $28, 0; //duration = 0x00000000
                               regwi 1, $29, 0; //step = 0x00000000
                               regwi 1, $30, 21430272;//control = 0x01470000
                               regwi 1, $31, 64;//t = 64
                               set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                               regwi 1, $10, 256;//wait for hardware DC area completion and IIR flush
                               memri 1, $13, 4088;//load remaining FIR capture time
                               condj 1, $10, >=, $13, @DC_CAPTURE_DONE;//wait for DC and FIR capture
                               mathi 1, $10, $13 + 0;//extend point through FIR capture
DC_CAPTURE_DONE:               mathi 1, $10, $10 + 0;
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
                               loopnz 0, $4, @FINE_TUNE_ADVANCE_1;
                               regwi 0, $4, 9;  //reload sweep axis 1 counter
                               mathi 1, $1, $1 + -396;//reset axis 1 (0, 0, 0, 'target')
                               mathi 1, $2, $2 + 144;//reset axis 1 (0, 1, 0, 'target')
                               mathi 1, $3, $3 + 112617;//reset axis 1 (1, 0, 0, 'step')
                               mathi 1, $4, $4 + -38268;//reset axis 1 (1, 1, 0, 'step')
                               loopnz 0, $3, @FINE_TUNE_ADVANCE_0;
                               waiti 0, 0;      //wait for experiment epilogue
                               memwi 0, $13, 1;
                               end ;
FINE_TUNE_ADVANCE_0:           mathi 0, $1, $1 + 1;//advance axis 0 ('rf_point_table', 0, 'duration') pointer
                               mathi 1, $5, $5 + 10;//advance axis 0 ('event_time', 'awg', 1, 0, 0)
                               mathi 1, $6, $6 + 10;//advance axis 0 ('event_time', 'awg', 1, 1, 0)
                               mathi 1, $7, $7 + 10;//advance axis 0 ('event_time', 'awg', 2, 0, 0)
                               mathi 1, $8, $8 + 10;//advance axis 0 ('event_time', 'awg', 2, 1, 0)
                               mathi 1, $9, $9 + 10;//advance axis 0 ('event_time', 'awg', 3, 0, 0)
                               memri 1, $31, 4095;//load advance axis 0 ('event_time', 'awg', 3, 1, 0)
                               mathi 1, $31, $31 + 10;//advance axis 0 ('event_time', 'awg', 3, 1, 0)
                               memwi 1, $31, 4095;//store advance axis 0 ('event_time', 'awg', 3, 1, 0)
                               memri 1, $15, 4094;//load advance axis 0 ('event_time', 'awg', 4, 0, 0)
                               mathi 1, $15, $15 + 10;//advance axis 0 ('event_time', 'awg', 4, 0, 0)
                               memwi 1, $15, 4094;//store advance axis 0 ('event_time', 'awg', 4, 0, 0)
                               memri 1, $31, 4093;//load advance axis 0 ('event_time', 'awg', 4, 1, 0)
                               mathi 1, $31, $31 + 10;//advance axis 0 ('event_time', 'awg', 4, 1, 0)
                               memwi 1, $31, 4093;//store advance axis 0 ('event_time', 'awg', 4, 1, 0)
                               mathi 0, $2, $2 + 10;//advance axis 0 ('event_time', 'rf_stop', 0)
                               memri 1, $15, 4092;//load advance axis 0 ('event_time', 'bias_pre_zero', 0)
                               mathi 1, $15, $15 + 10;//advance axis 0 ('event_time', 'bias_pre_zero', 0)
                               memwi 1, $15, 4092;//store advance axis 0 ('event_time', 'bias_pre_zero', 0)
                               memri 1, $31, 4091;//load advance axis 0 ('event_time', 'bias_pre_zero', 1)
                               mathi 1, $31, $31 + 10;//advance axis 0 ('event_time', 'bias_pre_zero', 1)
                               memwi 1, $31, 4091;//store advance axis 0 ('event_time', 'bias_pre_zero', 1)
                               memri 1, $12, 4090;//load advance axis 0 ('capture_compensation', 'wave_end')
                               mathi 1, $12, $12 + 10;//advance axis 0 ('capture_compensation', 'wave_end')
                               memwi 1, $12, 4090;//store advance axis 0 ('capture_compensation', 'wave_end')
                               memri 1, $12, 4089;//load advance axis 0 ('capture_compensation', 'rf_end_0')
                               mathi 1, $12, $12 + 10;//advance axis 0 ('capture_compensation', 'rf_end_0')
                               memwi 1, $12, 4089;//store advance axis 0 ('capture_compensation', 'rf_end_0')
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;
FINE_TUNE_ADVANCE_1:           mathi 1, $1, $1 + 44;//advance axis 1 (0, 0, 0, 'target')
                               mathi 1, $2, $2 + -16;//advance axis 1 (0, 1, 0, 'target')
                               mathi 1, $3, $3 + -12513;//advance axis 1 (1, 0, 0, 'step')
                               mathi 1, $4, $4 + 4252;//advance axis 1 (1, 1, 0, 'step')
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;