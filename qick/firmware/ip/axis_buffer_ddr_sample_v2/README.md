# AXIS Buffer DDR Sample V2

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

VLNV: `QICK:QICK:axis_buffer_ddr_sample_v2:1.0`

Version 2 preserves the V1 sample-count capture, internal CDC, 32-to-256 packing,
zero padding, stride, and optional sample-picker behavior. It adds register 9:

| AXI byte offset | Register | Meaning |
| --- | --- | --- |
| `0x24` | `TRIGGER_DELAY_CYCLES_REG` | Number of `s_axis_aclk` cycles between an accepted synchronized trigger and its capture request. |

The reset default is 50 source-clock cycles. A value of zero makes the
synchronized trigger request capture immediately. If no valid AXIS sample is
present at the requested cycle, the request remains pending until the next
valid sample. The delay line itself advances on every `s_axis_aclk` cycle and
does not depend on `s_axis_tvalid`.

This register gates storage only. It does not reset or realign any upstream FIR,
IIR, or decimation state.

## Multi-trigger delay line

Each accepted trigger inserts one bit at the configured stage of a one-bit
shift register. Bits move one stage toward stage 0 on every source clock, so
multiple trigger pulses can be in flight simultaneously. The line depth is the
next power of two that is at least twice `DEFAULT_TRIGGER_DELAY_CYCLES`:

```text
required depth = max(2, 2 * DEFAULT_TRIGGER_DELAY_CYCLES)
implemented depth = 2 ** ceil(log2(required depth))
```

The default 50-cycle delay therefore uses 128 stages and accepts programmable
delays from 0 through 128 cycles. Values above the implemented depth reject the
arm operation and set the sticky overflow/error status. `NTRIG_REG` still
limits the number of accepted trigger events for one arm operation.

Matured pulses are represented only by a small pending-count register; there is
no target RAM, FIFO read pointer, asynchronous RAM head, 64-bit sample index, or
wide deadline comparison in the trigger path. The single capture datapath still
cannot store overlapping windows at their exact requested cycles. A pulse that
matures during an active capture is retained for later service and sets the
sticky overflow status to report the alignment miss.
