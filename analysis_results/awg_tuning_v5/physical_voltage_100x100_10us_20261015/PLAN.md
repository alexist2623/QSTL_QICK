# Physical 100 x 100 voltage sweep, 10 us HOLD

User authorization: repeat the real DAC4 / DAC5 scope measurement with 100 points per voltage axis, 0 to 400 mV, and 10 us HOLD; use fixed-offset-corrected error strictly below 5% of requested voltage as the acceptance criterion.

- DAC4 / AWG generator 1 -> scope CH1; DAC5 / AWG generator 3 -> CH2.
- Actual MainWindow sweep editors -> production argument builder -> production compiler; scope-only execution, no RunWorker / ADC / DDR / QCoDeS acquisition claim.
- Identity 2 x 2 matrix, axis 2 fastest, 10,000 points, one repetition.
- Same waveform structure: 10 us zero, 1 us RAMP, 10 us HOLD, 1 us RAMP to zero, 10 us zero. Point duration includes compiler scheduling overhead and is recorded from decoded commands.
- No production edits, firmware loading, server restart, current / mixer / Nyquist reconfiguration, or unrelated generator reset. Selected paired DDS paths 0/2 are explicitly idled and selected AWG paths are zeroed before/after.
- Scope single acquisition spanning all points; original settings / RUN-STOP state restored. Full raw samples retained losslessly with preambles and hashes. Waveform and error plots saved.
- One fixed median zero offset per channel, computed from zero-level HOLD windows. No gain fit or per-point offset. 0 mV percent error is undefined (N/A). Nonzero denominator is the requested value, not the quantized hardware value.
- The 4.0404 mV requested increment and smallest 0.2020 mV acceptance band may be below measurement resolution. Record actual failures and scope resolution; do not weaken acceptance to force a pass.
- Prior evidence and user settings remain untouched. Evidence from this run is separate.
