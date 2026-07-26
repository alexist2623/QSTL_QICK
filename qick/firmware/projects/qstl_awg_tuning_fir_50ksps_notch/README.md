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
Register `TRIGGER_DELAY_CYCLES_REG` at byte offset `0x24` delays capture by
source fabric-clock cycles. The reset/default value is 50. Trigger pulses move
through a one-bit shift delay line, so multiple triggers can be in flight
without the former target FIFO and 64-bit deadline comparison. Software can
override the cycle count before arming.

The 50 kSPS output sample period is 20 us. The stored 32-bit word remains packed
as signed `Q[31:16]` and signed `I[15:0]`.

The Python driver discovers this profile from `bitstream.hwh`: it traces
`axis_buffer_ddr_sample_v2` upstream through
`axis_notch_decim_1m_to50k_v1` and `axis_fir_decim_300to1_v1`, then exposes
`fir_rate_profile="50_ksps"`, `stored_sample_rate_hz=50000`, and
`stored_sample_period_us=20`. The same `arm_ddr4_fir_samples()` and
`get_ddr4_fir_samples()` APIs continue to support the original 1 MSPS project.

Vivado 2023.1 build conditions and the clean Run=5 procedure are documented in
`VIVADO_BUILD.md`. Use `build_vivado_2023_1_run5.tcl` so both
`launch_runs -jobs 5` and `general.maxThreads=5` are applied. Use
`resume_vivado_2023_1_impl_run5.tcl` only after synthesis completed and a
transient Vivado tool error stopped implementation. To repeat independent
clean builds until timing closes (up to ten attempts), use
`run_vivado_2023_1_until_timing_closure.ps1`.
