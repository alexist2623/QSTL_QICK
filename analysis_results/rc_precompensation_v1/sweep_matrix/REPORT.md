# RC range checks and mixed hardware sweeps

The GUI exports Python, which generates PMEM/DMEM. Vivado xsim executes the
production tProcessor, TMUX, two AWG IPs, RC filters, and RF DDS IP. RFDC and
ARM are excluded. RF measurements below are digital samples at the DAC interface,
not measurements of a physical RF output. DC + RC are enabled; tau is 10 us.

## Completed RTL cases

| Case | Grid / repeats per point | Verified AWG samples per channel | Maximum analog-model error, either AWG | RF result |
|---|---:|---:|---:|---|
| Ramp rate | 10 x 10 / 2 | 5,170,032 | 0.145275 mV | 200 pulses, 190 MHz, 0.1 us |
| Hold duration | 3 x 3 / 2 | 567,440 | 0.072298 mV | 18 pulses, 190 MHz, 0.1 us |
| RF duration, extending AWG hold | 3 x 3 / 2 | 527,408 | 0.079583 mV | 18 pulses, 0.1 / 0.25 / 0.4 us |
| RF frequency | 3 x 3 / 2 | 484,928 | 0.075560 mV | 18 pulses, 180 / 202.5 / 225 MHz |

All 16 DAC lanes and the signed 72-bit RC accumulator matched the independent
integer recurrence on every checked clock. No clipping or unknown samples were
accepted. Every executed command word and timestamp matched the instruction
model with one fixed origin offset. Digital RC history and all DAC lanes were
zero after every repetition's reset, including the final repetition.

The independent analog RC model retains its capacitor state through digital
resets. Its error is measured against the delayed nominal, quantized AWG output,
not against an infinitely precise user voltage. The prior 4.2-code bound applied
to a particular fixed waveform; the swept-ramp case exceeded it. These tests
report the actual analog error while separately requiring exact digital results.
Thus the ramp case is not a claim of sub-LSB analog accuracy.

All RF peaks were exactly 2000 codes. RF pulse widths matched the programmed
cycles; frequency estimates from zero crossings were within 0.002 MHz. The RF
digital pipeline latency was consistently 42 cycles from the timed tProcessor
command. Software tests separately cover calibrated RF power lookup tables.

## Software findings and fixes

1. RF-duration extension combined with a voltage sweep omitted a voltage-times-
   duration term from DC compensation. The earlier sweep axis now selects
   coefficient rows and the later axis uses the appropriate row increment.
   Both axis orders are tested. A 200 x 200 RF-duration/voltage compile uses
   600 coefficient words, 400 coefficient-validation points, and four voltage-
   range corners. This compile-only test is separate from the two-DAC RTL grid.
2. Two AWGs plus RF and a hold-duration/DC table could exhaust a register page.
   The compiler now spills ordinary sweep state into DMEM when the table pointer
   needs a register. The hold-duration RTL case exercises the corrected path.

Regression suites after these changes: 190 mixed-sweep, RC, compiler, and GUI
tests, plus 23 Stability tests, passed. The mixed-sweep file includes 33 tests.
Full and boundary compilation modes produce identical words and timestamps for
the tested cases. Range checks do not modify PMEM or DMEM.

## Grid verification and limits

The 200 x 200 run was cancelled at the user's request on 2026-09-24 and
replaced with 20 x 20, keeping two DACs and two repetitions per point.
The replacement uses 400 points, 800 shots, and 384,793 simulated clocks.
Its completed results are recorded separately in `GRID_REPORT.md` and
`grid_20x20/result.json`. The cancelled 200 x 200 run is not a completed pass.

The dedicated 200 x 200 case uses two independent DAC voltage axes, 5 to 15 mV,
two repetitions per point, SET/RAMP/zero holds, fixed-time DC compensation,
and per-repetition RC reset. The final zero hold is 600 ns and the DC pulse
is 100 ns. It has 40,000 points, 80,000 shots, and 38,242,393 simulated cycles.
It did not finish; `cancelled.json` records its cancellation.

A deliberately shorter 100 ns final zero hold caused real tProcessor queue
lookahead to run out: one command was 9 cycles late relative to the instruction
model. This is a command-throughput limit and does not establish correct timing
for arbitrarily short dense waveforms. Reproduce with `--grid-zero-hold-ns 100`.
The stress waveform keeps the 600 ns zero hold to avoid this condition.

The earlier 5-to-15 mV/200-point range exposes existing integer-step
quantization: a requested 0.050251 mV step becomes 4 DAC codes (0.09765625 mV).
The command endpoints are 4.98046875 and 24.4140625 mV, so the final target error
is +9.4140625 mV. Correct loop reset and RC arithmetic do not remove that error.
The range guard checks actual compiled corner voltages, including this effect.
Do not describe this narrow sweep as accurately producing the requested voltages.

With 20 points the increment is 20 codes (0.48828125 mV), so the executed
nominal endpoints are 4.98046875 and 14.2578125 mV. The last target differs
from the requested 15 mV by -0.7421875 mV. This is distinct from digital
RC recurrence or loop/timing mismatches; reducing the grid does not eliminate
the existing rounded-increment error.

## Retention

Large-grid waveform and IP-input CSVs stop after 12,000 clocks (~150 KiB for
the waveform). All-shot timed command evidence is retained, along with all-shot
in-simulator assertions; no full waveform VCD/WDB is requested. Expected command
JSON is omitted for the large grid because PMEM/DMEM reproduce it. Existing
compiled libraries are reused. Completed-case sources, summaries, plots, logs,
and hashes are saved here without duplicating the larger raw CSV files.

An attempted cleanup of old isolated xsim snapshots was rejected by automatic
approval policy; those existing snapshots were not removed. Firmware BIT/HWH/XSA
and production project files were not cleanup targets.
