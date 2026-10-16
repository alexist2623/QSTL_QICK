# Basic validation requested 2026-10-15

The user requested only the simple cases from the supplied TODO, reserving
oscilloscope waveform and precise timing measurement details for later. The user
then authorized committing and pushing after validation.

## Scope

- Fresh actual MainWindow Qt input -> production compilation -> execution-model
  checks for three-segment SET/RAMP patterns, duration grid, voltage/matrix,
  RF frequency/duration, and segment-boundary rejection.
- Ten logarithmic duration values from 0.1 to 100 us are individual GUI cases,
  **not** a native logarithmic hardware sweep.
- Four fresh GUI -> actual tProcessor/TMUX/generator/sum v5 RTL runs cover small
  HOLD/voltage, RAMP/voltage, RF-frequency/voltage, and fine-duration boundary sweeps.
- Focused existing software tests cover supporting timing, compensation,
  acquisition, validation guards and GUI state.
- Preserve requested settings, committed state, quantized expectations, compiled
  input, observed simulation output, source hashes and original failures.

## Exclusions and evidence limits

No board or oscilloscope is accessed. No production GUI process, firmware,
RTL/XDC, user configuration or server is modified. Simulated results do not prove
physical output, analog calibration, ADC/FIR arithmetic, instrument triggering,
waveform transfer, or live-run recovery. The full physical suite in the TODO
remains pending. Register-arithmetic RF duration sweep and grouped sweep controls
are explicitly planned, unavailable features and are not marked passed.

All simulation build products remain outside Git. No new FPGA synthesis is run.
The existing awg_tuning_v4 branches are retained. Only validation artifacts and
related documentation are intended for this commit. Existing untracked user
JSON files are excluded.

## Work ownership

- `gui_cases/`: fresh GUI cases and independent analytic/model expectations.
- `rtl/`: four actual RTL runs, source/input provenance and numeric outputs.
- `software_regression/`: selected existing tests and exact node IDs.
- Root `REPORT.md`: final results, remaining coverage gaps and push status.

Production and user configuration preservation is checked by `audit_sources.py`.
