# axis_trigger_sync_v1

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

`axis_trigger_sync_v1` synchronizes an external trigger into `aclk` and emits a
single-cycle `trigger_pulse` on each rising edge.

In `qstl_awg_tuning_fir`, this pulse is fanned out to both the FIR decimator and
the DDR sample buffer so the FIR decimation phase and DDR capture start align to
the same source-clock trigger event.
