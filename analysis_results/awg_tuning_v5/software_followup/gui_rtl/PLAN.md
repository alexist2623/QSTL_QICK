# New v5 GUI → RTL validation

This folder is separate from the successful build's prebuild/postbuild evidence.
The original v4-timed replays are not substituted for these tests.

## Input and oracle

- Read the successful candidate HWH through the production QickMetadata and
  output_sum_config/apply_output_sum_config functions; require v2, 13 AWG delay
  clocks, two sum clocks, and equal 31-clock native output latency.
- Load real MainWindow controls, obtain normal Run Experiment arguments, and
  compare actual widget PMEM/DMEM with the normal exported program.
- Compile fresh candidate v2 sum plus current unchanged AWG/Square RTL, using
  the existing vendor DDS/real tProcessor/shared TMUX routing libraries.
- Preserve original command, raw-AWG, DC-area, RC-reset and DDR assertions.
- Check every sum lane using a separate 13-entry AWG history. Independently check
  the physical output slice from AWG[c−25] + RF[c−12], including rounding/clamp.

## Bounded cases

1. Exact 10 µs RAMP → 10 µs HOLD → 10 µs RAMP → 10 µs HOLD; RF in first HOLD.
2. Same waveform; RF in second HOLD.
   Both explicitly request a legal +100 ns RF offset and 9.9 µs width. They do
   not represent the unsupported exact zero-offset request.
3. 2×2 HOLD-duration/voltage sweep, fixed-time DC + RC, DDR after readout.
4. Same with fixed-voltage DC + RC, DDR overlapping readout.
5. 2×2 RF-duration sweep inside fixed HOLD, DC + RC + DDR.
6. 2×2 RF-duration sweep extending HOLD, DC + RC + DDR.
7. 2×2 RC-only sweep with DDR.

All seven use all three RF/AWG pairs and two repetitions. Fine RF tests use the
previous independent exact-width oracle with fresh GUI inputs, v5 HWH metadata
and v5 sum: 1–31 samples at zero and 190 MHz, plus 32 widths covering all sixteen
remainders on each pair, including the short/long threshold.

## Unsupported simultaneous request

Eight real MainWindow negative cases request zero offset on first/second HOLD,
each pair separately and all pairs. The production shared-port spacing guard
must reject them, and the exact request/error is preserved.

A separate low-level diagnostic intentionally queues identical timestamp words
through the actual tProcessor/TMUX in both AWG-first and RF-first orders. It
records command delivery and physical output skew. This is not a GUI program,
does not remove any production guard, and is not counted as a simultaneous
output timing PASS.

No board access, running GUI action, production RTL/XDC modification, synthesis,
firmware replacement, commit or push is performed.
