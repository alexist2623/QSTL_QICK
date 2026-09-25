
// Program

                               synci 200;
                               regwi 1, $10, 97734367;//target = 0x05d34edf
                               regwi 1, $11, 0; //reserved_start = 0x00000000
                               regwi 1, $12, 0; //duration = 0x00000000
                               regwi 1, $13, 0; //step = 0x00000000
                               regwi 1, $14, 19857408;//control = 0x012f0000
                               regwi 1, $15, 0; //t = 0
                               set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                               synci 100;
                               regwi 0, $13, 0;
                               regwi 0, $14, 200;//final acquisition count
                               regwi 1, $12, 106586022;//initialize DMEM sweep state ('bias_t', 0, 'bias_t_duration_q')
                               memwi 1, $12, 4095;//store initial DMEM sweep state ('bias_t', 0, 'bias_t_duration_q')
                               synci 128;
FINE_TUNE_POINT:               regwi 0, $15, 199;
FINE_TUNE_REP:                 regwi 1, $10, 12288;//awg_0:300mV_100us:target
                               regwi 1, $11, 0; //awg_0:300mV_100us:reserved_start
                               regwi 1, $12, 0; //awg_0:300mV_100us:duration
                               regwi 1, $13, 0; //awg_0:300mV_100us:step
                               regwi 1, $14, 16842752;//awg_0:300mV_100us:control
                               regwi 1, $15, 0; //300mV_100us t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:300mV_100us
                               regwi 1, $10, 4096;//awg_0:100mV_10us:target
                               regwi 1, $11, 0; //awg_0:100mV_10us:reserved_start
                               regwi 1, $12, 0; //awg_0:100mV_10us:duration
                               regwi 1, $13, 0; //awg_0:100mV_10us:step
                               regwi 1, $14, 16842752;//awg_0:100mV_10us:control
                               regwi 1, $15, 30000;//100mV_10us t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:100mV_10us
                               regwi 1, $10, 8192;//awg_0:200mV_400us:target
                               regwi 1, $11, 0; //awg_0:200mV_400us:reserved_start
                               regwi 1, $12, 0; //awg_0:200mV_400us:duration
                               regwi 1, $13, 0; //awg_0:200mV_400us:step
                               regwi 1, $14, 16842752;//awg_0:200mV_400us:control
                               regwi 1, $15, 33000;//200mV_400us t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:200mV_400us
                               regwi 1, $10, 0; //awg_0:bias_t_pre_zero:target
                               regwi 1, $11, 0; //awg_0:bias_t_pre_zero:reserved_start
                               regwi 1, $12, 0; //awg_0:bias_t_pre_zero:duration
                               regwi 1, $13, 0; //awg_0:bias_t_pre_zero:step
                               regwi 1, $14, 16842752;//awg_0:bias_t_pre_zero:control
                               regwi 1, $15, 153000;//bias_t_pre_zero t
                               set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:bias_t_pre_zero
                               synci 153011;
                               synci 1;         //common Bias-T guard after pre-compensation zero
                               regwi 1, $10, 0; //clear maximum Bias-T duration
                               memwi 1, $10, 4094;//store cleared maximum Bias-T duration
                               regwi 1, $11, 0; //awg_0 Bias-T reserved_start
                               regwi 1, $12, 0; //awg_0 Bias-T duration
                               regwi 1, $13, 0; //awg_0 Bias-T step
                               regwi 1, $14, 16842752;//awg_0 Bias-T control
                               regwi 1, $15, 32;//awg_0 common Bias-T start offset
                               memri 1, $12, 4095;//load signed Bias-T duration for awg_0
                               condj 1, $12, ==, $0, @BIAS_T_DONE_0;//skip zero-area Bias-T output awg_0
                               condj 1, $12, <, $0, @BIAS_T_NEGATIVE_AREA_0;//select Bias-T polarity for awg_0
                               regwi 1, $10, -3276;//awg_0 negative Bias-T target
                               condj 1, $0, ==, $0, @BIAS_T_DURATION_READY_0;//Bias-T polarity ready
BIAS_T_NEGATIVE_AREA_0:        math 1, $12, $0 - $12;//absolute Bias-T duration for awg_0
                               regwi 1, $10, 3276;//awg_0 positive Bias-T target
BIAS_T_DURATION_READY_0:       mathi 1, $12, $12 + 128;//round Bias-T duration for awg_0
                               bitwi 1, $12, $12 >> 8;//Bias-T duration in tProcessor cycles for awg_0
                               condj 1, $12, ==, $0, @BIAS_T_DONE_0;//skip sub-cycle Bias-T output awg_0
                               set 0, 1, $10, $11, $12, $13, $14, $15;//start Bias-T compensation on awg_0
                               regwi 1, $10, 0; //awg_0 return to zero after Bias-T compensation
                               mathi 1, $15, $12 + 32;//awg_0 Bias-T stop offset
                               set 0, 1, $10, $11, $12, $13, $14, $15;//finish Bias-T compensation on awg_0
                               memri 1, $10, 4094;//load maximum Bias-T duration for awg_0
                               condj 1, $12, <=, $10, @BIAS_T_MAX_READY_0;//keep maximum Bias-T duration after awg_0
                               memwi 1, $12, 4094;//update maximum Bias-T duration from awg_0
BIAS_T_MAX_READY_0:            mathi 1, $12, $12 + 0;//maximum Bias-T duration checked for awg_0
BIAS_T_DONE_0:                 mathi 1, $12, $12 + 0;//Bias-T output awg_0 complete
                               memri 1, $12, 4094;//load maximum Bias-T duration
                               condj 1, $12, ==, $0, @BIAS_T_NO_ACTIVE_OUTPUT;//skip Bias-T timing advance when all areas are zero
                               mathi 1, $12, $12 + 32;//include common Bias-T command lead
                               sync 1, $12;     //advance to latest simultaneous Bias-T stop
BIAS_T_NO_ACTIVE_OUTPUT:       mathi 1, $12, $12 + 0;//simultaneous Bias-T compensation complete
                               synci 1;         //separate Bias-T stop from the next sweep point
                               synci 32;        //lookahead for per-repeat AWG RC reset
                               regwi 1, $10, 97734367;//target = 0x05d34edf
                               regwi 1, $11, 0; //reserved_start = 0x00000000
                               regwi 1, $12, 0; //duration = 0x00000000
                               regwi 1, $13, 0; //step = 0x00000000
                               regwi 1, $14, 19857408;//control = 0x012f0000
                               regwi 1, $15, 0; //t = 0
                               set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
                               synci 15;        //flush per-repeat AWG RC reset
                               synci 20;        //post Bias-T shot recovery
                               mathi 0, $13, $13 + 1;
                               condj 0, $13, ==, $14, @DEFER_FINAL_ACQUISITION_COUNT;
                               memwi 0, $13, 1;
DEFER_FINAL_ACQUISITION_COUNT: loopnz 0, $15, @FINE_TUNE_REP;
                               waiti 0, 0;      //wait for experiment epilogue
                               memwi 0, $13, 1;
                               end ;