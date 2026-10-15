# AWG Tuning v5 — RTL latency equalization

User scope (2026-10-14): keep both repositories on existing `awg_tuning_v4`;
create a separate v5 FPGA project, equalize native AWG/RF latency in RTL and
build. Preserve Python timing/compiler/driver, user settings and the running board.
The later explicit user instruction authorizes the AWG output-selector Python fix
first, then continuation of the RTL work. That narrow GUI fix is recorded in
`authorized_gui_fix.json`. Until the full build and artifact gates succeed,
no other Python production change is authorized except the subsequently requested
plot/editor correction documented below. The later user instruction
(2026-10-14 20:03 America/Vancouver) authorizes v5 Python/GUI integration and
verification after successful synthesis, implementation and artifact checks.

- New `axis_output_sum_v2` delays AWG samples and valid by 13 clocks before
  the existing two-register signed saturating sum. All seven AWGs use this
  same delay, including four channels with no RF sum.
- AWG 16 + 13 + 2 = RF 29 + 2 = 31 clocks at the sum output (300 MHz).
  Common command routing/output slices are additional, unchanged delays.
- Equal native latency does not collapse different command arrival times.
  Existing tProcessor/TMUX behavior is preserved.
- v4 Python advances RF by 13 clocks. It remains untouched until the full build
  succeeds and is not yet a v5 driver. Subsequent software must select timing
  from firmware metadata and retain v4/legacy behavior. No automatic board update.
- Keep existing generator, SET/RAMP/IIR/DC, RF, DDR, Square and XDC unchanged.
  `protected_before.json` records 253 files before this task.
- Fresh verification: exhaustive sum/bypass/reset/valid/clipping; actual
  AWG plus vendor DDS native command latency; selected-48 basic RTL suites;
  system fixture replay with v5 output oracle. No previous-version PASS is
  substituted for tests of the changed datapath. Record the distinction
  between unchanged GUI-generated input and direct RTL commands.
- Build only after required fresh checks pass. Vivado 2023.1, jobs=4,
  general.maxThreads=5, default strategies, original byte-identical XDC.
  New full project `F:/Vivado_Output/a5full1` stays outside Git.
- Review final routed setup/hold/pulse-width/bus-skew. On failure stop;
  no RTL/XDC relaxation or automatic retry. Do not deploy any result to board
  or replace v4 firmware. No commit, push, or new branch.

## Verification status (2026-10-14)

- GUI shared-DAC AWG selection: 73 tests passed. AWG mode selects the AWG
  generator on DAC4/5/6 and excludes the RF generator sharing that output.
- Fresh v5 sum/bypass/reset/valid/saturation: 1,115,040 samples passed (`a5sum2`).
- Actual AWG v3 + vendor DDS: 96 native-latency checks passed (`a5native3`),
  raw AWG 16 / RF 29 clocks, both 31 clocks after the v5 sum block.
- Direct RTL 10 us RAMP/HOLD/RAMP/HOLD: both RF-HOLD selections passed on all
  three pairs (`a5ramp2`), with 288,000 flat-HOLD scalar checks. The original
  seven-clock RAMP startup is preserved and accounted for by the test commands.
- Fresh basic regression: six RTL suites passed; 74 software modules, 1,249
  tests passed after three reviewed desktop-environment retries. Original Qt
  shutdown/bootstrap failures remain in `a5reg1/status.json`; retry records and
  logs are in this evidence directory. The 73 GUI checks overlap these suites
  and are not added as 73 unique extra tests.
- Nine system fixtures are being replayed against freshly compiled v5 RTL.
  All nine were also freshly recompiled using current GUI/public-builder code;
  PMEM/DMEM is byte-identical to the replay input (`compiler_equivalence.json`).
  Eight include actual MainWindow compilation. Axis reversal remains the
  original fixture's post-GUI operation. Existing GUI PMEM/DMEM is unchanged,
  including the v4 RF scheduling advance.
  This proves the new RTL against those inputs, not v5 GUI timing compatibility.
  Stability uses the existing public-builder input, rather than MainWindow.
- Testbench-only counting/window/RAMP-startup corrections and the initial
  replay setup failure are retained. Production RTL was not altered to make
  those tests pass.
- The separate 48-bit continuous RC 200-shot baseline is running in `a5rc48`;
  it is required by the prebuild gate. No other accumulator widths are run.

## Scheduled build review and authorized software follow-up

- First scheduled review: 2026-10-14 23:02:58 America/Vancouver
  (2026-10-15 06:02:58 UTC), then every ten minutes. Existing controllers
  continue without interruption; do not start duplicate work.
- A successful synthesis estimate is insufficient. Require completed workflow,
  final routed timing and matching BIT/HWH/XSA, source and evidence hashes.
- Freeze the successful build evidence before changing software. Use a separate
  postbuild software evidence directory; do not rewrite original gate snapshots.
- Then implement and verify v5 Python driver/compiler and GUI support in the
  existing branches. Preserve v4, legacy firmware, user settings and running GUI.
  See `SOFTWARE_FOLLOWUP.md`, including the shared-port timing issue that still
  requires actual GUI-to-v5-RTL proof. Never silently shift requested RF timing.
- Functional or final timing failure stops this workflow; no software follow-up,
  RTL/XDC repair, retry or deployment. On success, report and pause the heartbeat
  only after software follow-up and its affected verification are complete.

## Additional user-requested GUI plot/editor correction (2026-10-14)

The user separately authorized fixing stale AWG edit annotations, interrupted
HOLD voltage dragging, and RF pulse names clipped above their rectangles.
Only `dc_waveform_widgets.py` and a new regression module changed for this fix.
79 affected tests pass with clean Qt teardown; nine regenerated compiler inputs
remain byte-identical. Exact file hashes are added to `authorized_gui_fix.json`;
the original baseline and earlier compiler evidence are preserved.
See `plot_annotation_fix/REPORT.md`. Its broader 157-assertion run is not a full
PASS because it exposed a separate RF duration-name callback `KeyError: d1`
in unchanged GUI code; that issue is recorded separately and not modified.
Production compiler, driver, RTL/XDC and running hardware remain unchanged.

## Subsequent composite RF parameter work

The user subsequently authorized T2 pi/2 endpoint options, named delay sweeps,
monochrome composite output, Hahn echo, common frequency/amplitude, and named
amplitude/phase parameters with one Manual-gain / Calibration-dBm mode. See
RUNNING.md and `composite_t2_fix` for live scope and evidence. The half-duration
reference is displayed as `d0/2`, not stored as an unrelated fixed number.
Preserve old per-pulse settings on load; verify new GUI round trips, host sweep
resolution, calibration, previews and actual GUI-to-RTL inputs. Keep the
unchanged low-level compiler and v4 phase/timing behavior. Refresh the exact
authorized hashes and all nine baseline compiler-input comparisons after the
last source change. Do not modify the independent v5 RTL build or deploy to
the user's board for this editor work.

This authorized feature work is now complete: 282 affected software tests pass,
nine baseline compiler-input cases are byte-identical, and seven newly executed
GUI-to-v4-RTL cases check 126 DDS bursts. Source/evidence hashes and authorized
scope are refreshed. See `composite_t2_fix/REPORT.md`. Custom amplitude/phase
references are independent per pulse, with one common Manual/Calibration mode;
the existing v4 summed-output calibration rejection is preserved. The separate
v5 workflow and 23:02:58 scheduled result review remain unchanged.

## First scheduled review (2026-10-14 23:05 local)

The nine system replays and selected-48 RC 200-shot run have passed. The
prebuild gate passed and the existing full build started at 21:34:10. Synthesis
finished successfully at 22:23:57; implementation optimization has completed
and its DRC is running. Final routed timing/artifact acceptance and subsequent
v5 software integration remain pending. See RUNNING.md for process identity,
progress, memory and retained warning details. No retry or deployment occurred.

## RF sample-duration feature, separately authorized

Implementation and current-v4 GUI-to-RTL validation are complete in an isolated
source package: [report](rf_fine_duration/REPORT.md). It supports one-sample
active widths (0.208333 ns), sixteen preloaded ending patterns with hardware
sweep, and preserves the v4 timing profile. Final evidence: 680 software tests,
nine unchanged coarse GUI inputs, nine real RTL cases / 1644 bursts / 10281
commands. Every width 1..31 passed on all three RF paths at 0 and 190 MHz.

Promotion into the production GUI waits for the existing v5 successful postbuild
source gate; use the eight exact files and original destination hashes in
`rf_fine_duration/release_package/manifest.json`. RUNNING.md records the ordered
promotion and fresh source/compiler-proof checks. This does not replace the
subsequent v5 latency-profile integration or its actual GUI-to-v5 RTL tests.
