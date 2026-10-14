# AWG Tuning v4: RF + AWG output sum

Status: complete. Full routed timing passed; matching v4 BIT/HWH/XSA published.
Final GUI/driver integration passed 274 tests and five byte-identical GUI
PMEM/DMEM replays. See VALIDATION_REPORT.md and final_integration_manifest.json.
The initial a4full1 startup environment failure is preserved.

Latest user direction (2026-10-13): finish the current validation and full build;
if final timing closure fails, stop and report without RTL/constraint changes or
another build. Do not publish failed firmware.

## Authorized topology

The user approved the diagram on 2026-10-13 and requested a new v4 project.
Start from the final timing-closed v3 source project. Both repositories stay on
their existing `awg_tuning_v4` branches. The user confirmed that this is already
the GUI v4 branch; do not create a duplicate branch. No commit/push is included
in this implementation request.

| GUI default pair | Existing RF IP | Existing AWG IP | Sum output |
|---|---|---|---|
| RF 1 (gen 0) + AWG 1 (gen 1) | axis_signal_gen_v6_0 | axis_awg_tuning_v3_4 | DAC 10 / s10_axis |
| RF 2 (gen 2) + AWG 2 (gen 3) | axis_signal_gen_v6_1 | axis_awg_tuning_v3_5 | DAC 11 / s11_axis |
| RF 3 (gen 4) + AWG 3 (gen 5) | axis_signal_gen_v6_3 | axis_awg_tuning_v3_6 | DAC 12 / s12_axis |

The first three RF streams are rerouted to these sums. Their old dedicated DAC
inputs receive zero. RF 4, Square Wave, RF/FIR/DDR algorithms, and all original
AWG SET/RAMP/DC/IIR algorithms stay unchanged. The remaining four AWG outputs
get the same two-register output stage in bypass mode. Every lane adds signed
16-bit inputs into 17 bits, saturates, then quantizes once to aligned 14-bit DAC
codes. Missing streams contribute zero; no lane carry and no sample stalling.

This is a post-AWG-output sum, as drawn. The AWG area engine continues to cancel
AWG pre-IIR area only. It does not claim to cancel added DDS area or clipping
distortion. RF power calibration from the old connector must not be silently
treated as calibration of the new AWG physical output.

## Timing and scope

- Fixed two-register sum/bypass latency at 300 MHz (16 scalar samples/word).
- Determine RF/AWG relative latency at identical observation boundaries in RTL.
  Do not blindly subtract the old reported 42/16 numbers.
- For a common GUI output time, advance commands by each path's measured delay.
  Preserve pulse duration, ramp/hold sweep timing, and acquisition alignment.
- Do not silently shift an unschedulable coincident event; reject or schedule it
  with valid lead time and verify the actual tProcessor behavior.
- Do not modify existing generator datapaths, IIR, XDC, RF/FIR/DDR source logic.
  Necessary HWH tracing, endpoint metadata, compiler timing, and plot mapping are
  part of the v4 integration and must preserve legacy behavior without v4 metadata.

## Ordered validation / build checklist

- [x] Freeze v3 source and constraints hashes; ensure no previous jobs are running.
- [x] Sum/bypass RTL: all lanes, signed bounds, both clipping signs, full input
      codes, rounding, invalid streams, reset, constant delay and backpressure.
- [x] New v4 BD/HWH: correct three RF pairs, seven equal-latency AWG paths,
      unchanged clocks/constraints/legacy sources, unused RF DAC inputs zero.
- [x] Library and GUI: discover shared physical DACs and new latency, correct
      output identity, reject conflicting DAC settings / wrong RF calibration.
- [x] Actual GUI -> PMEM/DMEM -> tProcessor/TMUX/AWG/RF/sum RTL: simultaneous and
      offset pulses, all three pairs, 100-point voltage
      and hold-duration sweeps, RF duration and stop, DC fixed-time/fixed-voltage,
      RC only, and DDR timestamp capture timing. Save source hashes and plots.
      Unrelated AWG bypass delay is covered by unit RTL and generated HWH checks.
- [x] Applicable ordinary software/RTL regressions; v3 protected source hashes.
      Width selection is complete: do not repeat 32/48/64 selection.
- [x] New full project outside Git: F:/Vivado_Output/a4full2; Vivado 2023.1,
      jobs=4, general.maxThreads=5, default strategies, byte-identical v3 XDC.
- [x] Full routed setup/hold/pulse-width/bus-skew closure, final HWH topology and
      source/evidence validation before publishing v4 BIT/HWH from the same XSA.
- [x] After successful full build, finish requested GUI and Python driver
      integration against final v4 firmware on GUI branch `awg_tuning_v4`: review shared
      output identity/settings, driver discovery/configuration, firmware paths
      and legacy behavior; implement remaining changes if necessary and verify
      affected behavior. Keep the existing tested sources frozen during build.
      Refresh affected evidence if additional software changes alter it.
      If final timing fails, stop/report instead of starting this follow-up.
- [x] Final report, diagrams and test limits. Never label unfinished checks PASS.
