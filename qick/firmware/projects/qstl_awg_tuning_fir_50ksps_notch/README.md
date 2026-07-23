# qstl_awg_tuning_fir_50ksps_notch

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

This project is copied from `qstl_awg_tuning_fir`. Only the DDR capture
hierarchy is changed. The original project remains independently buildable.

DDR capture path:

```text
axis_switch_ddr/M00_AXIS
  -> axis_fir_decim_300to1_v1_0       (300 MSPS -> 1 MSPS)
  -> axis_notch_decim_1m_to50k_v1_0  (Kaiser FIR /10, /2 + 20 harmonics x 2 notches)
  -> axis_buffer_ddr_sample_v2_0      (trigger-delayed finite capture + CDC)
  -> axi_smc_1/S01_AXI
  -> ddr4_0/C0_DDR4_S_AXI
```

The legacy trigger input of `axis_fir_decim_300to1_v1_0` is tied low in this
project. FIR history, notch history, and both decimation phases therefore run
continuously and are never aligned to a trigger.

The synchronized tProcessor trigger goes only to the DDR V2 capture block.
Register `TRIGGER_DELAY_SAMPLES_REG` at byte offset `0x24` skips valid 50 kSPS
filter outputs before capture. The reset/default value is 50. The nominal
low-frequency full-path delay is about 988.89 us, including 28.92 us from the
existing 300-to-1 FIR and 959.97 us from the added two-stage Kaiser FIR and
notch datapath. FIR delay is exact; notch IIR delay is frequency-dependent, so
software can override this value for the measured signal band.

The 50 kSPS output sample period is 20 us. The stored 32-bit word remains packed
as signed `Q[31:16]` and signed `I[15:0]`.

The Python driver discovers this profile from `bitstream.hwh`: it traces
`axis_buffer_ddr_sample_v2` upstream through
`axis_notch_decim_1m_to50k_v1` and `axis_fir_decim_300to1_v1`, then exposes
`fir_rate_profile="50_ksps"`, `stored_sample_rate_hz=50000`, and
`stored_sample_period_us=20`. The same `arm_ddr4_fir_samples()` and
`get_ddr4_fir_samples()` APIs continue to support the original 1 MSPS project.
