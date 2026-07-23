# axis_fir_decim_300to1_v1

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

`axis_fir_decim_300to1_v1` is a two-lane 32-bit AXIS FIR anti-alias decimator for
the `qstl_awg_tuning_fir` DDR capture branch.

The stream format is:

```text
tdata[15:0]  = signed lane 0
tdata[31:16] = signed lane 1
```

The cascade is:

```text
stage 0: FIR decimate by 10, 300 MSPS -> 30 MSPS
stage 1: FIR decimate by 10,  30 MSPS ->  3 MSPS
stage 2: FIR decimate by 3,    3 MSPS ->  1 MSPS
```

Arithmetic uses signed 16-bit input lanes, signed 18-bit Q1.17 coefficients,
signed 48-bit accumulators, round-half-away-from-zero coefficient rescaling, and
signed 16-bit output saturation.

The FIR path intentionally ignores output backpressure. `s_axis_tready` is held
high, `m_axis_tready` is not fed back into the pipeline, and decimated
`m_axis_tvalid` pulses continue at the FIR output rate. The downstream DDR
sample buffer must therefore be provisioned so it can accept the 1 MSPS FIR
output stream.

The `trigger` input is synchronized to `aclk` and used as a rising-edge
alignment event. On each trigger rising edge, the FIR keeps its sample history
and clears only the decimation phase plus valid pipeline. The FIR response
therefore remains continuous, while the 300-to-1 output phase is aligned to the
trigger event.

`capture_trigger` is the DDR-facing trigger output. The FIR computes its group
delay from the three tap counts and decimation factors, then counts actual
`m_axis_tvalid` events after each input trigger. With the default 95/127/161-tap
10x/10x/3x cascade, the group delay is 8677 input samples (28.923333 us at
300 MSPS). The block skips 28 early FIR outputs and pulses `capture_trigger`
during the full output interval before the first sample whose FIR center is at
or after the trigger. The first stored 1 MSPS sample is therefore aligned to
within 22 input samples (73.333 ns) of the trigger without moving the tProcessor
command timeline. The remaining offset is the nearest available point on the
existing 1 MSPS output phase; no FIR data samples or history are discarded.
If another trigger arrives before the compensated pulse is emitted, the phase
and pending delay restart from the newer trigger. Default triggers therefore
need at least 28 us separation, in addition to the DDR capture length rule.
