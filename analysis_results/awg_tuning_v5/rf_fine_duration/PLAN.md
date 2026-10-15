# RF sample-duration implementation and validation

User request: implement approximately 0.2 ns RF duration control and run actual
RTL validation; preload all 16 ending patterns for hardware duration sweeps.

At the current 300 MHz / 16-sample SG-v6 configuration, one DAC sample is
0.208333333 ns. This changes the active RF width, not the fabric-clock-aligned
start time or the analog edge rise time. Production generator RTL is unchanged.

## Isolation and scope

- Develop in `F:/Vivado_Output/a5fine_sw/DCWaveformGeneratorGUI` while the existing
  v5 place/route workflow finishes and validates its protected source hashes.
- `before_manifest.json` records the 105 top-level original GUI Python files.
- No board access, upload, firmware replacement, live GUI/server restart,
  new branch, commit, push, RTL/XDC change, or synthesis retry.
- Preserve the existing v4 Python timing profile; this is independent of the
  pending v5 postbuild timing integration.
- Promote only the reviewed feature files after the original build source gate
  is complete or after explicitly preserving/updating the authorization evidence.

## Implementation

- Default-off GUI `Fine duration (DAC sample)` setting, preserved by settings,
  Custom/T2 conversion, generated Python and experiment metadata.
- Sixteen 128-sample I/Q envelopes per RF generator: 2048 complex samples total.
- Short durations select a pattern and word offset; long durations combine a
  DDS plateau with the final pattern. Commands still require at least three
  fabric clocks, including trailing zero padding for very short pulses.
- Hardware sweep selects mode/address/timestamp rows in DMEM inside the existing
  tProcessor loop; it does not upload each point or unroll the program per point.
- Keep existing same-port command-spacing and busy-window checks. Reject
  unsupported geometry, insufficient envelope/DMEM space, incompatible segment
  extension, or an unrepresentable schedule rather than silently moving pulses.
- Envelope product scaling uses twice the requested gain with integer
  truncation. The supported requested/resolved gain range is -16383..16383.
- Quantize upward to a sample, snapping values within half the GUI's 1e-9 us
  decimal precision of an exact sample grid point. Metadata distinguishes
  requested time from actual sample count and duration.

## Required evidence

1. GUI roundtrip of every ending pattern, precise sweep labels, default behavior.
2. Compiler/model hardware loops: all short lengths, 16 endings and wrap,
   short/long transitions, ascending/descending, repetitions/axis reset,
   frequency/gain combinations, memory and timing guards.
3. Runtime conversion, decimal roundtrip and amplitude/geometry guards.
4. Affected existing software regression and nine unchanged coarse GUI inputs.
5. Actual MainWindow -> PMEM/DMEM/envelope -> real tProcessor/TMUX/SG-v6/vendor
   DDS and output sum. Load envelope through AXI configuration and handshaken
   AXIS DMA input, not direct BRAM assignment or forced generator output.
6. All three real shared RF/AWG port pairs; full-rate sample oracle, command
   comparison, carrier/phase and long plateau/tail continuity.
7. User follow-up: explicitly exercise every active width from 1 through 31
   samples. The minimum command playback slot (three clocks / 10 ns) must not
   be confused with the minimum active width (one sample / 0.208333333 ns).
   Short playback contains the requested active samples followed by zeros;
   the padded interval remains reserved before another pulse can use the same
   generator. Check both the zero-frequency envelope count and nonzero-carrier
   samples against an independently measured carrier reference.

## Final-source audit additions

- Reject a generator without DDS support before direct register emission.
  The actual SG-v6 target has DDS; recompilation must prove unchanged PMEM,
  DMEM and envelope bytes for already executed valid inputs.
- For host T2/duration sweeps, preserve quantized fine-duration metadata for
  every software coordinate. Label the existing last-point summary explicitly;
  do not present it as the settings for all software points.
- Preserve earlier failed timing executions and their exact source snapshots.
  The corrected compiler must pass the unchanged strict command-time oracle.

Status and figures will be summarized in `REPORT.md` only after their actual
execution. Python assertions or tProcessor model results alone are not RTL PASS.
