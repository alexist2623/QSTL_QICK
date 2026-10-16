# Physical RAMP-duration × voltage sweep — 2026-10-15

## Requested scope
- Latest voltage range: −400 to +400 mV, 100 points.
- RAMP duration: 10 ns to 1 us, 100 points. HOLD: 10 us.
- DC: fixed voltage 300 mV, or fixed time 10/20/30 us.
- RC time constant: 10/20/30 us.
- Same DAC4/5 → scope CH1/2 wiring, AWG generators 1/3.
- Primary criterion retained: one fixed baseline offset per channel; absolute central-window median error >15 mV is FAIL. No gain fit.

## Explicit test interpretation
Current GUI has independent RAMP-duration axes and output-specific voltage axes. To preserve the requested 100×100 grid and the identity virtual matrix, run each rising/falling RAMP and each DAC separately. The other RAMP stays at 1 us; the other DAC stays at zero. This produces 48 requested conditions (2 directions × 2 DACs × 12 DC/RC combinations), not one million Cartesian points. This is a validation fixture; user settings and production code are not changed.

Range guards remain active. A condition rejected before output is recorded as NOT RUN / range rejected, never PASS. In particular τ10 us with ±400 mV may exceed the recorded nominal DAC full scale after RC precompensation.

## Evidence and limitations
Actual MainWindow modal inputs → normal argument builder → current compiler → finite existing-board program; scope replaces the RunWorker/ADC/DDR/QCoDeS acquisition path. PMEM and runtime DMEM must match the offline GUI compilation before execution. This is a physical scope campaign, not a new RTL simulation or synthesis.

Full-frame captures check all 10,000 HOLD values, DC and zero windows at ≤500 ns sample spacing, using actual per-point command times. They cannot resolve a 10 ns RAMP. Separate high-resolution representative captures cover 10 ns, 500 ns and 1 us at ±400 mV for each DAC/direction, with RC20 us and fixed-time DC10 us. These are not all-point high-resolution timing proof.

Preserve requested values and actual quantized values separately. The register-add voltage sweep can end near +404 mV despite a +400 mV requested endpoint; requested voltage remains the primary reference. Preserve original failures, raw samples (lossless gzip), plots, source hashes and setup backups. Restore scope configuration and zero/reset selected AWGs after every acquisition.

No firmware changes, server restart, GUI termination, production edits, branch creation, or unrelated-output changes. Evidence commit/push after completed analysis is authorized by the continuing user request.

High-resolution representatives are separately GUI-compiled fixed one-point settings at the requested endpoint voltage. Their exact transport rounding can differ from the 100-point register-add sweep's endpoint. Each uses its own preserved actual PMEM/model; do not describe them as captures of the identical 10,000-point command stream.

## Completed scope

All48 requested cases were handled:32 physical100x100 sweeps,16 RC tau10 range rejections before output. All24 representative high-resolution captures completed. Existing source/firmware/user settings were preserved. Final acquisition cleanup and scope restoration passed in each of56 captures. The main and representative waveform failures/coverage limits are reported separately in REPORT.md; no all-PASS claim is made.
