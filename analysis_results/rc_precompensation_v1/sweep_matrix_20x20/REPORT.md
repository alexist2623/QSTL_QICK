# All mixed sweeps: completed 20 x 20 RTL verification

Each case executes 400 points, with two repetitions per point and two active AWG outputs.
All seven cases ran the production tProcessor/TMUX/AWG/RC and RF DDS RTL.
RFDC and ARM are excluded; the measurements here are digital DAC interface samples.
The separate two-DAC voltage 20 x 20 x 2 test also completed; its result is retained as dual_dac_voltage_result.json.

RF duration timing discrepancies remain; completion is not an all-tests-pass claim.

| Case | Result | Shots | Commands checked | Samples checked per AWG | Max analog RC error (mV) |
|---|---|---:|---:|---:|---:|
| Ramp duration | passed | 800 | 18,386 | 20,530,672 | 0.264771 |
| Hold duration | passed | 800 | 18,314 | 23,304,432 | 0.269798 |
| RF duration + AWG extension | completed_with_timing_findings | 800 | 19,118 | 21,277,552 | 0.283945 |
| RF duration, AWG fixed | completed_with_timing_findings | 800 | 19,202 | 19,614,192 | 0.244093 |
| RF frequency | passed | 800 | 18,402 | 19,624,752 | 0.244093 |
| RF amplitude/power | passed | 800 | 18,402 | 19,624,752 | 0.244093 |
| RF frequency x power | passed | 800 | 18,402 | 19,835,952 | 0.064111 |

## RF duration finding

The RF duration sweep uses a continuous periodic command with a three-clock block. The RF controller consumes a queued zero-gain stop only at a block boundary.
For a commanded duration of N clocks, the measured width is ceil(N/3)*3 clocks. This creates a real output-duration error of zero, one, or two clocks (up to 6.666667 ns at 300 MHz).
This behavior is not a postprocessing artifact and has not been fixed in production software or RTL. It is retained as a failed exact-duration check.
- RF duration + AWG extension: 520/800 pulses differ from the commanded duration; maximum 2 clocks.
- RF duration, AWG fixed: 520/800 pulses differ from the commanded duration; maximum 2 clocks.

Every timed command word and timestamp matched the instruction model.
All 16 DAC lanes and the signed 72-bit RC history matched the independent integer recurrence on every checked clock.
Both AWGs passed 801 history/zero checks: initial configuration plus all 800 repeat completions.
RF frequency, fitted sine amplitude, sample peak and pulse width were measured from every emitted RF pulse. A short sampled sinusoid need not hit its continuous-time peak; amplitude is therefore fitted from all samples, with residuals checked separately.
RF repetitions had identical programmed frequency/gain/width; every power-table gain matched the independent fixture formula within one code.

## Settings and interpretation

- AWG voltage axis: 5 to 15 mV, 20 points; second AWG also outputs SET/RAMP/DC waveforms.
- Ramp/RF duration: 0.1 to 0.416666667 us, 20 points, 5 fabric-clock increments.
- AWG hold duration: 1 to 1.95 us, 20 points, 15 fabric-clock increments.
- RF frequency: 180 to 225 MHz; RF power axis: -26 to -14 dBm in the synthetic fixture.
- DC + RC enabled; tau 10 us. Analog RC capacitor state is retained across digital resets.
- RF power tests use an explicitly synthetic SQLite calibration dataset read by the production GUI calibration loader. They verify gain scheduling and DDS output, not physical dBm calibration.
- Analog error is measured against the delayed nominal, quantized AWG waveform. It is separate from the existing integer-increment voltage error.
- The prior 20-point AWG voltage test measured 14.2578125 mV at a requested 15 mV endpoint; these tests do not claim that existing quantization error has been fixed.

## Retention

Waveform CSV capture is bounded to the initial 12,000 clocks after program start; assertions and analog RC error statistics cover every clock of every shot.
All-shot RF pulse samples and timed command logs are retained. Compiled snapshots were isolated for concurrent runs. No firmware/production project files were deleted.
The former 200 x 200 run was cancelled at user request and is not counted as a completed validation.

## Initial analysis and recapture

The initial analysis incorrectly required explicit RF stop commands even for oneshot output. The corrected analysis uses the oneshot length field and explicit stop timing only for periodic mode.
The initial hold-duration and RF-duration-with-extension runs completed all in-RTL checks but left truncated RF sample streams. Those two complete 20 x 20 x 2 simulations were rerun with explicit file closure. The original evidence remains in each case's capture_v1_incomplete directory.
Other cases were reanalyzed from their existing complete RTL command and RF sample evidence. No missing samples were invented or replaced with model output.
