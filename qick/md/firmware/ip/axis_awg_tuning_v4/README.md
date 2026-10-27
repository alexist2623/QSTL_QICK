# AXIS AWG tuning v4

This IP is the generator used by the AWG v6 project. It preserves the 160-bit
SET/RAMP/DC/RC command encoding and the 48-bit per-shot area accumulator while
giving SET and RAMP the same deterministic command-to-core-output latency.

## Timing contract

With `EXTRA_Y_PIPE_STAGES=3`, both SET and RAMP first words appear seven clocks
after command acceptance. A RAMP of `duration` scalar samples issues
`ceil(max(duration,1)/16)` consecutive words. A new command can be accepted on
the clock immediately after those issued words, even while old words remain in
the output pipeline. A one-word rising RAMP, one-word SET/HOLD, and one-word
falling RAMP can therefore be commanded on three consecutive clocks. Commands
inside the unfinished issue duration are still ignored; AXIS ready stays high.

The controller keeps the next command's logical starting value separate from
the physically emitted hold value. All words carry their own target and
hold-zero metadata through the pipeline. A normal SET, including SET zero,
does not discard older words. AXI-Lite override is an immediate abort of the
controller pipeline. Readback reports the emitted/held, quantized lane-zero
sample rather than a future target. Status bits 0/1 mean pipeline idle/busy;
new status bit 6 indicates whether another SET/RAMP can be accepted now.

DC and RC control packets receive the same seven-clock delay. The existing
DC arithmetic and RC arithmetic are unchanged. With DC bypass latency 5 and
RC latency 11, command-to-wrapper-output latency is 23 for both SET and RAMP.
The AWG v6 output sum adds 6 AWG alignment stages and 2 sum stages, giving 31
clocks, matching the DDS path. DC compensation has a distinct command latency:
7 control alignment + 17 DC setup + 11 RC + 6 alignment + 2 sum = 43 clocks.

## Validation

`validation/run_unit_bench.py --build F:/Vivado_Output/a6_NAME --bench NAME`
compiles the actual RTL and vendor DSP48E2 simulation primitive in an isolated
directory. It records source hashes and checks that they remain unchanged.
Only the selected 48-bit production width runs. Supported benches:

- `tb_common_latency`: seven-clock equality, 100 repetitions each of
  1/1/1, 1/2/1 and 2/1/2-clock RAMP/HOLD/fall triples, partial-word transitions, physical
  readback, hold-zero, clipping, ignored premature commands and aborts.
- `tb_control_alignment`: delayed DC/RC commands, SET wrapper latency, both
  DC modes' separate latency, zero residual area.
- `tb_dc_area`, `tb_dc_boundaries`, `tb_dc_faults`: unchanged DC engine contracts.
- `tb_width_awg`: 400 compensated shots through the new full wrapper, with an
  independent v4 command-to-sample oracle and zero residual checks.
- `tb_set_saturation`: all signed 16-bit values and random 32-bit targets,
  consecutive commands, override and terminal RAMP clipping.
- `tb_timing_tail`: randomized RAMP boundary/step checks and the existing
  square-pulse quantizer and bypass arithmetic regression.

These test sources are not a claim of completed simulation or timing closure.
Run results belong outside Git in the private analysis/build locations.
