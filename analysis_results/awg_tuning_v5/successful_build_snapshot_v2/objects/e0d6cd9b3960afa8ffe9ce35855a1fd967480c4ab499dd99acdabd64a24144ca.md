# Current v5 state

Schedule/scope updated 2026-10-14 20:03 America/Vancouver.
Execution snapshot below is from 19:55; no new build-result check is implied.

Both repositories remain on `awg_tuning_v4`. New FPGA project: `qstl_awg_v5`.
The specifically authorized Python AWG selector fix is complete (73 tests pass).
The selector fix plus the later user-requested plot/editor fix and their new
tests are authorized by `authorized_gui_fix.json`; Python timing/compiler/driver and v4 firmware remain
protected by `protected_before.json` until the full build/artifact gates succeed.
The user now authorizes subsequent v5 Python/GUI integration and verification;
see `SOFTWARE_FOLLOWUP.md`. No board actions are authorized.

Fresh v5 sum, actual AWG/DDS latency, direct 10 us RAMP/HOLD tests and six basic
RTL suites have passed. Basic software: 1,249 tests after three reviewed
desktop-environment retries. See PLAN.md and `desktop_retries.json`.

Nine system replays are in progress; `replays_status.json` is authoritative.
Controller: session 27768, powershell.exe PID 84116, created 2026-10-14
19:32:16 local; command `analysis_results/awg_tuning_v5/run_replays.ps1`.
Verify name, command and creation time before trusting the PID. Do not duplicate.
Maximum two system simulations plus the separate continuous 48-bit RC run
execute concurrently. CSV writes can remain
buffered until simulation exit; use xsimk CPU progress and logs as well.

No v5 synthesis has started. Continuation controller: session 23350,
powershell.exe PID 132544, created 2026-10-14 19:42:02 local, command
`analysis_results/awg_tuning_v5/run_workflow.ps1`. It is already running;
do not launch a second copy. `run_workflow.ps1` is the one-way continuation:
wait for all nine replays, require functional/source gates, then build fresh
`F:/Vivado_Output/a5full1` with Vivado 2023.1, jobs=4, maxThreads=5 and unchanged
default strategies/XDC. Consult `workflow_status.json` before launching it.
No automatic retry, source repair or publication is allowed. On final timing
failure stop and report setup/hold/pulse-width/bus-skew evidence. Candidate
BIT/HWH/XSA remain outside Git and are not deployed or substituted for v4.

Native v5 command-to-sum latency is 31 clocks for both generators. Existing
Python still has v4 RF timing assumptions; do not claim v5 GUI compatibility or
load this candidate on the user's running board. Native waveform evidence:
`native_ramp_hold.png` (rendered and visually inspected).

The checklist's separate continuous RC 200-shot baseline is also rerun with
`run_selected48.ps1` into fresh `F:/Vivado_Output/a5rc48`; status is
`selected48_status.json`. Only width 48 is selected. The functional gate requires
200 completed shots, overflow/collection/residual/cumulative area zero and the
unchanged RC error limit. No 32/64-bit comparison is run.
RC controller: session 63939, powershell.exe PID 141076, started 19:44:16 local;
verify its identity before acting. It runs the existing selected-width validator
and report tool without modifying either.

All nine compiler inputs were freshly regenerated with current production
Python/GUI and match the replayed PMEM/DMEM (`compiler_equivalence.json`, exit 0).
Eight include actual MainWindow; Stability uses the public builder. The original
reversed-axes fixture reverses sweep order after GUI input. This connects current
software to the fresh RTL tests without changing the v4 timing profile.

Completion follow-up `awg-v5-rtl` first checks this existing workflow at
2026-10-14 23:02:58 America/Vancouver (2026-10-15 06:02:58 UTC), then every ten
minutes. Existing controllers continue running. Before that start time, do not
perform scheduled build-result checks or start software edits. It does not
launch duplicate work. Existing `awg-v3` and `awg-v4-timing` remain paused.
On failure report and pause. On verified full build success, freeze original
build/source/evidence snapshots, then complete the authorized v5 Python/GUI
support and affected tests before the final report and pause. Keep new software
evidence separate from the original prebuild/postbuild gates. Do not deploy,
restart the user's GUI/server, modify RTL/XDC, create a branch, commit or push.

Five of nine system cases have passed: both exact 10 us HOLD selections, both RF
duration policies, and RC-only. The two long HOLD sweeps are running; reversed
axes and Stability are queued. RC200 remains running. Current process CPU is
increasing. Read status files for subsequent changes; these counts are a snapshot.

Final routing is checked before bitstream generation. `validate_routed.ps1`
checks exact setup/hold statistics, pulse-width endpoints, all 14 bus-skew paths
and routing errors. Its nine acceptance/rejection tests passed using copies of
v4 reports (not v5 signoff). Original test-harness stderr handling failure is
preserved in `F:/Vivado_Output/a5gatecases`; successful parser tests are in
`a5gatecases2`. If final routing fails, no BIT/HWH/XSA candidate is exported.
If it passes, `validate_artifacts.ps1` checks seven v2 sum blocks, their 13-clock
delay, 300 MHz/48-bit configuration, source/sink connections and XSA BIT/HWH
byte equality, writing `candidate_manifest.json` in the external build folder.

Additional GUI task completed 2026-10-14: stale annotation cleanup, continuous
HOLD voltage drag across deferred refresh, RF names inside envelopes.
`plot_annotation_fix/REPORT.md` records 79 affected tests/exit0, current nine-case
compiler-input equivalence, original evidence preservation and exact scope hashes.
The strict broader RF GUI run has 157 passing assertions but exit1 from a separate
duration-name rename callback `KeyError: d1`; do not report it as all-green.
Its unchanged source path and failed isolated baseline-startup attempts are
documented. No RTL/build retry or board action was performed for this GUI task.
This update does not change the scheduled review time or v5 timing profile.

## Active composite RF editor work (2026-10-14)

Later explicit user requests authorize composite editor/core/runtime changes
before the scheduled v5 review: monochrome pulse preview, independent T2 pi/2
endpoints derived from half a selected pi duration, named tau sweeps, Hahn echo,
global frequency/amplitude and parameterized delay/amplitude/phase. The latest
request uses a common Manual-gain / Calibration-dBm mode and common calibration
selection. This work does not alter the QICK low-level compiler, phase reset,
RTL, XDC, firmware, running board/server or running GUI. New evidence is kept in
`composite_t2_fix`; prior evidence remains intact.

This separate GUI feature task completed at about 21:30 local: the final nine
affected software modules passed 282 tests with clean Qt teardown and exit0.
Custom uses per-pulse amplitude/phase/delay references; only Manual/Calibration
mode and calibration selection are common. Presets retain Global frequency and
numeric Global gain. Old settings and preset-to-Custom effective values are
preserved. The final six tau/pi cases plus one Hahn-to-Custom amplitude/phase
case passed actual v4 RTL: three RF/AWG pairs, two repetitions, 126 DDS bursts.
All widths, relative times, commands, saturation and DC residual checks pass;
independent DDS fits also check carrier gain/frequency/relative phase. These
controllers have ended; do not duplicate them. Both actual RTL figures were
opened and checked.

The current GUI/compiler was recompiled for all nine baseline system cases in
`F:/Vivado_Output/a5gui_named_1`; PMEM/DMEM remain byte-identical. Final-source
recompilation also exactly matches the six new already-executed RTL inputs;
serialization additions are itemized separately. `compiler_equivalence.json`
and `authorized_gui_fix.json` now record final sources/evidence. Original
evidence, initial failed test assumptions and reviewed corrections are retained
in `composite_t2_fix`. See `composite_t2_fix/REPORT.md` and `result.json`.

Calibration conversion is tested in ordinary RF software/compiler/preview.
The production v4 summed-output Calibration guard remains enforced and was
checked through all three pairs and the actual runtime host loop. No calibrated
summed-output RTL run or analog calibration success is claimed. No board action,
live GUI restart, RTL/XDC/firmware change, commit or push was performed.

The separate scheduled v5 result review remains at 23:02:58 local. This editor
work is not the postbuild v5 timing integration, and current Python retains the
v4 timing profile. The prior duration-name callback issue is now corrected as
part of parameter-reference handling and is covered by the new editor tests.

## Nyquist display follow-up (2026-10-14, about 22:06 local)

The user pointed out the duplicated Nyquist zone control. Only the RF Output
editor's visible Nyquist row was removed; hidden state still receives the
Front Panel value and preserves settings/calibration/runtime propagation.
48 affected tests passed with exit0/clean Qt teardown. All nine baseline
compiler inputs were recompiled in `F:/Vivado_Output/a5gui_nqz_1` and remain
byte-identical. Exact authorization/source hashes are refreshed; earlier
composite test/RTL evidence and the pre-edit source snapshot are preserved.
See `nyquist_front_panel_fix/REPORT.md`. No RTL simulation was repeated and
no hardware or live GUI action was performed. The user also asked why tau
is a software sweep: this was explained as the current host-loop implementation,
not a hardware limitation. Tau execution was not changed in this follow-up.
The separate v5 result review schedule remains unchanged.

## First scheduled result review — 2026-10-14 23:05 America/Vancouver

All nine fresh v5 system replays completed successfully by 21:33:53. These
retain the v4-timed GUI inputs; they are not postbuild v5 GUI timing signoff.
The separate selected-48 RC run completed with RTL/report exit 0: 200 shots,
overflow/collection/residual/cumulative area errors all zero, maximum RC model
error 0.05461681895 mV and maximum end residual 0.000863350555 mV.
`selected48/rc_error_48.png` was opened and visually checked at this review.
The prebuild gate passed with 253 protected files and all required checks.

The existing workflow started the full build at 21:34:10. Top-level synthesis
completed successfully at 22:23:57 with zero errors. Implementation is running:
`opt_design` completed successfully and its post-optimization DRC is in progress.
Final placement/routing and timing signoff are still pending. Vivado critical
warnings, including clock-group lookup warnings in unchanged XDC, remain in
the logs; this is not a warning-free or timing-closed result.

Verified live identities: workflow powershell PID 132544 (created 19:42:02),
Vivado parent PID 82744 (21:34:11), implementation Vivado PID 75836 (22:36:00).
Implementation CPU increased from 3574.265625 to 3618.40625 seconds between
23:04:25 and 23:04:55, with advancing logs. Free physical RAM was 8.86 GiB of
31.86 GiB. Replay and RC controllers have exited. `workflow_status.json` remains
`complete=false`, `stage=full_build`; no duplicate work or source changes were
made. Keep the existing ten-minute review active. Postbuild Python/GUI timing
integration must wait for the final routed and artifact gates.

## Scheduled review — 2026-10-14 23:15 America/Vancouver

Post-optimization DRC completed and placement began at 23:08:55. The latest
log is in placer initialization / Build Placer Netlist Model. The same verified
workflow and Vivado processes remain live; implementation CPU reached
4842.9375 seconds at 23:14:58 (up from 3618.40625 at the preceding review).
There is no routed result or candidate artifact yet.

Memory pressure was briefly high: at 23:14:28, available physical memory was
1.198 GiB and committed memory 54.407 / 55.358 GiB (98%). Windows pagefile
management is automatic. By 23:14:58, Vivado memory usage had fallen and
available physical memory recovered to 5.013 GiB, committed 51.639 / 55.358
GiB (93%), with no page input/output in that sample. No process termination,
pagefile configuration change or build retry was performed. Snapshot:
`review_20261014_2315.json`. Continue scheduled review; final timing and
postbuild software integration remain pending.

## Separately authorized RF sample-duration feature — 2026-10-14 23:58

The user explicitly requested approximately 0.2 ns RF width control and actual
RTL verification, including sixteen preloaded ending patterns for hardware
duration sweep. Development is isolated in
`F:/Vivado_Output/a5fine_sw/DCWaveformGeneratorGUI`; original source hashes and
build gates are preserved in `rf_fine_duration/before`. Production sources have
not yet been changed for this feature. See `rf_fine_duration/PLAN.md`.

At 300 MHz x 16 lanes the exact digital width grid is 0.208333333 ns. Fine mode
is opt-in, uses existing SG-v6 envelope BRAM and a hardware DMEM selection table,
and preserves the existing v4 latency profile. It is not the pending v5 timing
integration. No new RTL or synthesis, board action, upload, firmware replacement,
live GUI/server restart, commit or push is authorized by this feature work.

The initial affected staging software suite passed 663 tests with clean Qt
teardown. All nine existing coarse GUI inputs were recompiled in
`F:/Vivado_Output/a5fine_baseline1` and their PMEM/DMEM are byte-identical. Extra
fine-only timing guards are still under review, so use the eventual final-source
results rather than treating these initial test counts as final signoff.
Actual real-tProcessor/TMUX/SG-v6/vendor DDS RTL has passed the first 96-sample
plateau/tail case on all three shared RF/AWG pairs, twice each; full sixteen-way
hardware sweep and further cases remain running. No complete RTL PASS yet.

The separate v5 full build remains in post-placement optimization at this
snapshot. Verified process identities are unchanged; final routing is pending.

## Scheduled review — 2026-10-15 00:13 America/Vancouver

Placement has completed and `d_1_wrapper_placed.dcp` exists. The unchanged
default `phys_opt_design` completed with zero errors; it reported nonnegative
pre-route setup WNS and skipped setup optimization. This is not final routed
timing closure. Final routing and artifact/source gates remain pending.
The verified implementation process PID 75836 reached CPU 11718.59375 s.

Memory remains constrained (available 1273 MiB; commit 55.21 / 56.37 GiB in this
sample, with automatically managed pagefile growth). Do not launch concurrent
large validation processes. No process termination, machine configuration
change, rebuild or hardware action was performed.

The separate fine-duration feature is still staged. Its first compact actual
RTL test exposed duplicate initialization and excessive per-event command
preparation, causing late commands. Those failures are preserved in the fine
evidence directory; strict command timing checks remain enabled. The compiler
is being optimized and rechecked before feature promotion. Current production
compiler and the v5 protected-source gates are unchanged.

## RF sample-duration validation finished — 2026-10-15 00:56 local

The separately requested approximately 0.2 ns feature is implemented and
validated in the isolated staging tree. Exact step: 0.208333333 ns at 4.8 GS/s.
All 680 affected software tests and all nine unchanged coarse GUI PMEM/DMEM
comparisons passed on the final source. Actual GUI -> tProcessor/shared TMUX ->
SG-v6/vendor DDS -> v4 sum RTL passed nine cases, 1644 RF bursts and 10281
commands. All widths 1..31 passed on three paths twice at both 0 MHz and
190 MHz; all sixteen ending patterns passed hardware duration/frequency
sweeps. Long 10/100/300 us ending/periodic cases passed. No command timing/value,
sum-lane, or outside-window output errors remain. Both actual-data plots were
opened and visually checked. Earlier failed runs and exact input/source hashes
remain preserved. See `rf_fine_duration/REPORT.md` and `results.json`.

The active width can be one sample (0.208333 ns); the generator reserves at
least three fabric clocks (10 ns) including zero padding. Onset still uses the
fabric clock grid. Gain magnitude is limited to 16383, and hardware fine-width
sweeps require a fixed HOLD. These are digital results, not analog measurements.

Production promotion is still pending, deliberately preserving the original
v5 build's final source gate. The 105 original production Python hashes are
unchanged. The exact eight tested files are preserved in
`rf_fine_duration/release_package/manifest.json`; do not copy any `.venv`, user
JSON or unrelated file from staging. All fine-duration test processes ended.

After the original v5 workflow succeeds and its pre/postbuild evidence is
snapshotted, complete this already authorized follow-up before v5 latency
integration: compare production files with the package's original hashes,
promote the eight files, retain previous gate/compiler/authorization evidence,
refresh exact authorization hashes and run the nine current GUI input
comparisons against the promoted tree. `run_software_checks.ps1 -Tag <new>
-Gui C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI` can reproduce the
680-test and nine-case check into fresh evidence. Do not manually relabel an
old compiler proof. Preserve the original v4 latency behavior in this feature.
Then continue the separately authorized v5 latency profile/GUI-to-v5 RTL work,
including affected fine-width cases. Do not claim the v4 fine-width RTL test
establishes v5 command alignment. If the original v5 timing fails, follow the
existing stop/report/no-source-change instruction and leave this package staged.

The original workflow remains `full_build` at this snapshot. Verified identities
remain powershell PID 132544 (19:42:02.750955), parent Vivado PID 82744
(21:34:11.514620), implementation Vivado PID 75836 (22:36:00.079464).
Implementation CPU reached 15909.58 seconds; routing is still active. Final
routed timing and candidate acceptance have not been reported as passed.

## Scheduled review — 2026-10-15 01:43 America/Vancouver

`route_design` has completed successfully with zero errors. Unrouted nets,
partially routed nets and node overlaps are all zero, and routed-net verification
completed successfully. The route step retained 221 warnings and 68 critical
warnings; this is not a warning-free result. Routed DRC and methodology reports
finished, and the existing implementation process is generating the power report.

The workflow remains `complete=false`, `stage=full_build`. Final timing/artifact
gates and the candidate manifest are still pending. Do not promote staged fine-RF
software or start v5 latency integration yet. The same verified workflow,
parent Vivado and implementation processes remain live (PIDs 132544, 82744,
75836 with their original creation times and command lines). Implementation CPU
increased to 20189.015625 seconds; available memory was 8260 MiB with commit
54.372 / 58.386 GiB. No process, build, production source or board action occurred.

## Scheduled review — 2026-10-15 01:54 America/Vancouver

Implementation's `d_1_wrapper_timing_summary_routed.rpt` now reports all user
timing constraints met: rounded WNS +0.028 ns, WHS +0.009 ns, TNS/THS zero,
setup/hold failing endpoints zero, WPWS/TPWS zero and pulse-width failing
endpoints zero. `d_1_wrapper_bus_skew_routed.rpt` has 14/14 MET paths, minimum
reported bus-skew slack +2.475 ns. Route status has 582434/582434 fully routed
nets and zero routing errors. These are routed reports, not synthesis estimates.

The existing workflow is still `full_build`, `complete=false`; its custom final
timing gate, artifact/source checks and candidate manifest remain pending while
the implementation saves its routed results. Do not treat these reports as the
completed artifact acceptance, change production sources or start software tests.
Verified original processes remain active; implementation CPU is 21266.5 s.
Available physical memory was 2527 MiB; commit 58.546 / 59.394 GiB. No additional
large processes or board actions were started. Continue the existing automation.

## Scheduled review — 2026-10-15 02:14 America/Vancouver

The original workflow's explicit final routed gate printed
`ROUTED_GATE=V5_ROUTED_GATE_PASS` before launching `write_bitstream`. Exact
saved statistics are WNS +0.028000 ns, WHS +0.009357 ns, TNS/THS zero.
The existing implementation process exited at 01:53:43 after writing its
routed checkpoint. The same parent workflow/Vivado now has a bitstream-step
Vivado child PID 150316, created 02:11:53.085477 local; its command runs
`d_1_wrapper.tcl`, and its log opens `d_1_wrapper_routed.dcp`. This is the
authorized continuation of the original build, not a new synthesis or retry.

`workflow_status` remains incomplete/full_build. `build_result.txt` still has
`timing_closed=UNKNOWN` at this intermediate stage, and the candidate manifest
is absent. Wait for final export, artifact equality and protected-source gate
before declaring full success or changing Python/GUI. At 02:13:27 parent CPU
was 4442.71875 s, bitstream child CPU 61.15625 s; physical memory available
12888 MiB. No source changes, additional simulations or board actions occurred.
