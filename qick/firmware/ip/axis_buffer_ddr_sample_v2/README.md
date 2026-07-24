# AXIS Buffer DDR Sample V2

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

VLNV: `QICK:QICK:axis_buffer_ddr_sample_v2:1.0`

Version 2 preserves the V1 sample-count capture, internal CDC, 32-to-256 packing,
zero padding, stride, and optional sample-picker behavior. It adds register 9:

| AXI byte offset | Register | Meaning |
| --- | --- | --- |
| `0x24` | `TRIGGER_DELAY_SAMPLES_REG` | Number of valid input samples skipped after a synchronized trigger before capture starts. |

The reset default is 50 samples. In the `qstl_awg_tuning_fir_50ksps_notch`
path this selects the first valid 50 kSPS sample at or after the nominal
988.89 us low-frequency delay. That delay includes 28.92 us from the existing
300-to-1 FIR and 959.97 us from the added two-stage Kaiser FIR and notch
datapath. A value of zero captures the first valid sample after the trigger.
The delay counts `s_axis_tvalid` events, not 300 MHz fabric clocks.

This register gates storage only. It does not reset or realign any upstream FIR,
IIR, or decimation state.

## Pending-trigger FIFO

Each accepted trigger is converted to an absolute valid-sample deadline and
stored in a source-clock-domain FIFO. This allows later triggers to arrive while
earlier triggers are still inside the programmable delay. The FIFO depth is the
next power of two that is at least twice `DEFAULT_TRIGGER_DELAY_SAMPLES`:

```text
required depth = max(2, 2 * DEFAULT_TRIGGER_DELAY_SAMPLES)
implemented depth = 2 ** ceil(log2(required depth))
```

The default 50-sample delay therefore uses 128 entries, exceeding the requested
two-times margin of 100 pending triggers. `NTRIG_REG` still limits the number of
accepted trigger events for one arm operation.

The single capture datapath cannot store overlapping capture windows. Trigger
spacing must therefore be at least the configured captured window in valid
input-sample units, including `SAMPLE_DECIM_REG`. If a queued deadline expires
while another capture is still active, the sticky overflow status is asserted
instead of silently treating the late sample as correctly aligned.
