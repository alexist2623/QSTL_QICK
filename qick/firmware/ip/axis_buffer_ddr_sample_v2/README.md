# AXIS Buffer DDR Sample V2

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

VLNV: `QICK:QICK:axis_buffer_ddr_sample_v2:1.0`

Version 2 preserves the V1 sample-count capture, internal CDC, 32-to-256 packing,
zero padding, stride, and optional sample-picker behavior. It adds register 9:

| AXI byte offset | Register | Meaning |
| --- | --- | --- |
| `0x24` | `TRIGGER_DELAY_CYCLES_REG` | Number of `s_axis_aclk` cycles between an accepted synchronized trigger and its capture request. |

The reset default is 281970 source-clock cycles. At the 400 MHz source clock
used by `qstl_awg_tuning_fir_50ksps_notch`, this is 704.925 us and compensates
the calculated FIR group delay. A value of zero makes the synchronized trigger
request capture immediately. If no valid AXIS sample is present at the
requested cycle, the request remains pending until the next valid sample. The
timestamp advances on every `s_axis_aclk` cycle and does not depend on
`s_axis_tvalid`.

This register gates storage only. It does not reset or realign any upstream FIR,
IIR, or decimation state.

## 32-bit timestamp queue

The source domain maintains a free-running 32-bit timestamp. For every accepted
trigger it enqueues:

```text
due_timestamp = current_timestamp + TRIGGER_DELAY_CYCLES_REG
```

The queue FSM waits until the head timestamp equals the current timestamp, then
moves that event to a pending-event counter. Equality comparison is sufficient
because the delay register is latched at arm time and is common to all events;
therefore due timestamps preserve trigger order even across 32-bit wraparound.
The full unsigned 32-bit register range is supported.

`TRIGGER_QUEUE_ADDR_WIDTH` controls only the number of not-yet-due events:

```text
queue depth = 1 << TRIGGER_QUEUE_ADDR_WIDTH
```

The default width is 6, or 64 future trigger events. Delay length does not
increase queue resource usage. If the timestamp queue is full when another
nonzero-delay trigger arrives, the trigger is rejected and sticky overflow is
set. `NTRIG_REG` still limits accepted events for one arm operation.

Matured events can remain pending while the finite capture FSM is active, so a
trigger is not discarded merely because an earlier capture is still being
written. The single capture datapath cannot store overlapping windows at their
original due cycles; pending captures are serviced in order as soon as the
current capture finishes and a valid AXIS sample is available.
