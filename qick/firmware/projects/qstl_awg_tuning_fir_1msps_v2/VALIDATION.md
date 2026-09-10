# 1 MSPS V2 validation

Validation date: 2026-09-09.
Branch: `codex/qstl-fir-1msps-v2`.
Base source commit: `6925f8c03d9b03fd4c2fd439ab472034be42b72b`.

## Build status

Synthesis, placement, routing, static timing and BIT/HWH/XSA export completed.
All 398196 routable nets are fully routed, with zero routing errors or overlaps.
No-clock register pins and unconstrained internal endpoints are both zero.

| Final check | Result |
| --- | --- |
| Setup WNS / TNS | +0.099763 ns / 0 ns |
| Hold WHS / THS | +0.009249 ns / 0 ns |
| Bus skew | All 14 constraints passed; minimum slack +2.595 ns |
| LUT / FF | 132801 (31.23%) / 210095 (24.70%) |
| BRAM / DSP | 442.5 (40.97%) / 2252 (52.72%) |

The [build result](validation/build_result.txt),
[timing summary](validation/timing_summary_postroute.rpt), and other reports
are saved in `validation/`. Timing uses the original 3.333 ns constraint;
no clock relaxation or extra timing exceptions were added.

Matching [BIT](bitstream.bit), [HWH](bitstream.hwh), and [XSA](bitstream.xsa)
are in this project directory. SHA-256 checks confirm that the XSA's top-level
`d_1.hwh` and embedded BIT match the standalone files, and all three copied
artifacts match the build output. The HWH is byte-identical to the file used
by the 27 passing Python tests. Hashes and sizes are recorded in the
[artifact manifest](validation/artifact_manifest.json).

Build directory: `C:/JeonghyunPark/Workspace/Vivado_Output/q1mv2b`.
The build uses Vivado 2023.1, the default synthesis/implementation strategies,
`launch_runs -jobs 5`, and `general.maxThreads=5`.
The [source fingerprint](validation/build_source_sha256.json) records the
actual source files, including the new project changes beyond the base commit.
All 12 recorded hardware source files still matched when artifacts were
packaged. These changes have not been committed or pushed.

## Functional checks

| Check | Result |
| --- | --- |
| Python DDR/metadata regression | 27 tests passed |
| Repository HWH profiles | Legacy 1 MSPS, 50 kSPS, and new 1 MSPS V2 passed |
| Shared FIR RTL vectors | Passed, maximum lane error 0 |
| DDR V2 RTL cases 0–22 | Passed |
| Continuous FIR + DDR V2 integration | Passed |

The integration test uses the real FIR RTL and trigger synchronizer, a 300 MHz
source domain, and the DDR V2 AXI memory test model. It checks four 40 kHz
triggers, 13 samples per trigger, zero padding to two AXI words, and delays of
0 and 8677 source-clock cycles. Captured words match an independent deadline
and sample-selection model. The FIR output interval remains 300 clocks across
triggers and DDR re-arm. The 8677-cycle case keeps multiple future triggers in
the queue because the trigger period is only 7500 cycles.

HWH checks verify that the extra FIR/notch IP is absent, the remaining FIR
feeds DDR V2 directly, FIR.trigger is tied to zero, the unused FIR.capture_trigger
does not drive capture, and the DDR trigger comes from axis_trigger_sync_v1.
AWG, tProcessor, FIR and DDR source clocks report 300 MHz. DDR defaults are
8677 delay cycles and a 64-entry timestamp queue.

RTL log: `C:/JeonghyunPark/Workspace/Vivado_Output/q1mv2_test_a.log`.

## Existing warnings

The opt_design critical-warning IDs and counts exactly match the previous
`q50tsq1` build: `Vivado 12-4739` (20), `Vivado 12-5201` (7),
`Constraints 18-4644` (1), and `Common 17-55` (40). These refer to inherited
unmatched clock-group and I/O constraint queries. The active `clk_104_pl`
constraint is 3.333 ns. Existing BD address-overlap, older-IP-version and four
TMUX/readout command-width warnings also remain.

The routed DRC has no Error or Critical Warning entries; its rule IDs match
the 50 kSPS baseline. DSP input-pipelining warnings decrease from 1632 to 1248;
PREG output-pipelining warnings change from 17 to 19. The routed methodology
report has the same 82 warnings as the baseline: LUTAR-1 (42), TIMING-9 (1),
TIMING-10 (1), TIMING-18 (28), and TIMING-24 (10).
The timing report retains the baseline's four inputs and 24 outputs without
I/O delay constraints; internal paths are constrained.

No FPGA board acquisition or analog latency calibration has been performed in
this validation. The programmable default is the FIR's calculated group delay;
system latency can be calibrated through the same delay register. The separate
PulseGenerator GUI still needs its profile-based delay selection adapted for
1 MSPS V2, as described in the project README.
