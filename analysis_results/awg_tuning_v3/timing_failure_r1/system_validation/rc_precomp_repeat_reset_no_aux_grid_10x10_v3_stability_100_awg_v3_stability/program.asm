
// Program

                               synci 200;
                               regwi 1, $10, 97734367;//target = 0x05d34edf
                               regwi 1, $11, 0; //reserved_start = 0x00000000
                               regwi 1, $12, 0; //duration = 0x00000000
                               regwi 1, $13, 0; //step = 0x00000000
                               regwi 1, $14, 19857408;//control = 0x012f0000
                               regwi 1, $15, 0; //t = 0
                               set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                               regwi 1, $26, 97734367;//target = 0x05d34edf
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
                               regwi 1, $1, -472;//initialize direct sweep state (0, 0, 0, 'target')
                               regwi 1, $2, 1436;//initialize direct sweep state (0, 1, 0, 'target')
                               regwi 0, $1, 9;  //initialize sweep axis 0 counter
                               regwi 0, $2, 9;  //initialize sweep axis 1 counter
                               synci 128;
FINE_TUNE_POINT:               regwi 0, $15, 1;
FINE_TUNE_REP:                 mathi 1, $10, $1 + 0;//awg_0:set_0:target
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
                               regwi 1, $10, 0; //awg_0:bias_t_pre_zero:target
                               regwi 1, $11, 0; //awg_0:bias_t_pre_zero:reserved_start
                               regwi 1, $12, 0; //awg_0:bias_t_pre_zero:duration
                               regwi 1, $13, 0; //awg_0:bias_t_pre_zero:step
                               regwi 1, $14, 16842752;//awg_0:bias_t_pre_zero:control
                               regwi 1, $15, 600;//bias_t_pre_zero t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:bias_t_pre_zero
                               regwi 1, $26, 0; //awg_1:bias_t_pre_zero:target
                               regwi 1, $27, 0; //awg_1:bias_t_pre_zero:reserved_start
                               regwi 1, $28, 0; //awg_1:bias_t_pre_zero:duration
                               regwi 1, $29, 0; //awg_1:bias_t_pre_zero:step
                               regwi 1, $30, 16842752;//awg_1:bias_t_pre_zero:control
                               regwi 1, $31, 600;//bias_t_pre_zero t
                               set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:bias_t_pre_zero
                               synci 616;
                               synci 1;         //common Bias-T guard after pre-compensation zero
                               regwi 1, $10, 458129844;//target = 0x6d3a06d3
                               bitwi 1, $10, $10 << 2;
                               mathi 1, $10, $10 + 3;
                               regwi 1, $11, 447392;//reserved_start = 0x0006d3a0
                               regwi 1, $12, 600;//duration = 0x00000258
                               regwi 1, $13, 0; //step = 0x00000000
                               regwi 1, $14, 21692416;//control = 0x014b0000
                               regwi 1, $15, 64;//t = 64
                               set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                               regwi 1, $26, 458129844;//target = 0x6d3a06d3
                               bitwi 1, $26, $26 << 2;
                               mathi 1, $26, $26 + 3;
                               regwi 1, $27, 447392;//reserved_start = 0x0006d3a0
                               regwi 1, $28, 600;//duration = 0x00000258
                               regwi 1, $29, 0; //step = 0x00000000
                               regwi 1, $30, 21692416;//control = 0x014b0000
                               regwi 1, $31, 64;//t = 64
                               set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
                               regwi 1, $10, 713;//wait for hardware DC area completion and IIR flush
                               sync 1, $10;     //hardware DC compensation and capture complete
                               synci 1;         //separate Bias-T stop from the next sweep point
                               synci 20;        //post Bias-T shot recovery
                               mathi 0, $13, $13 + 1;
                               condj 0, $13, ==, $14, @DEFER_FINAL_ACQUISITION_COUNT;
                               memwi 0, $13, 1;
DEFER_FINAL_ACQUISITION_COUNT: loopnz 0, $15, @FINE_TUNE_REP;
                               loopnz 0, $2, @FINE_TUNE_ADVANCE_1;
                               regwi 0, $2, 9;  //reload sweep axis 1 counter
                               mathi 1, $1, $1 + -1224;//reset axis 1 (0, 0, 0, 'target')
                               mathi 1, $2, $2 + 432;//reset axis 1 (0, 1, 0, 'target')
                               loopnz 0, $1, @FINE_TUNE_ADVANCE_0;
                               waiti 0, 0;      //wait for experiment epilogue
                               memwi 0, $13, 1;
                               end ;
FINE_TUNE_ADVANCE_0:           mathi 1, $1, $1 + -32;//advance axis 0 (0, 0, 0, 'target')
                               mathi 1, $2, $2 + -272;//advance axis 0 (0, 1, 0, 'target')
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;
FINE_TUNE_ADVANCE_1:           mathi 1, $1, $1 + 136;//advance axis 1 (0, 0, 0, 'target')
                               mathi 1, $2, $2 + -48;//advance axis 1 (0, 1, 0, 'target')
                               condj 0, $0, ==, $0, @FINE_TUNE_POINT;