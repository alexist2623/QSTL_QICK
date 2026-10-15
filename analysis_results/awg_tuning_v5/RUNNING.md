# Current v5 state

## 2026-10-15 현재 v5 추가 GUI → RTL 검증 완료

새 실제 RTL 37회·352 shots가 통과했습니다. 원본 거부 조건을 통과로 바꾸지 않고 별도 RF +100ns 변형과 분리했습니다. Virtual matrix×sweep 21조건은 원본 1개와 명시적 변형 20개이며, composite 7조건은 원본 그대로 PASS입니다. 별도 compiler 17조합은 Calibration 정상 거부 6개, Quantum N=0 원본 RTL PASS 1개, CPMG/UDD 명시적 +100ns 변형 RTL PASS 8개, Quantum N=1/3 v5 latency 미지원 거부 2개입니다. 원본 45조건 전체 RTL PASS로 표시하지 않습니다.

실제 MainWindow/생산 compiler 입력과 새 PMEM/DMEM을 실제 tProcessor/TMUX/AWG/DDS/v5 합산 RTL로 실행했습니다. 정확한 AWG/RF 동시 시작은 사용자 지시에 따라 수정하지 않았습니다. 생산 소스·RTL/XDC·사용자 설정 및 기존 펌웨어는 보존했고, 이후 요청받은 로컬 v5 BIT/HWH/XSA/manifest 네 신규 파일만 추가했습니다. 보드 업로드와 새 합성은 없으며 자동화는 PAUSED 상태입니다.

[이번 최종 보고서와 케이스별 증거](expanded_gui_rtl_20261015/REPORT.md). Show/Run 경로 비교 및 미재현 정체 진단은 해당 보고서의 별도 링크를 따릅니다.

아래 기존 기록은 각 버전·빌드·조사 당시 상태를 보존한 것입니다.

---

Latest task, 2026-10-15: the completed-build records below are historical. A new
user-requested validation is running in expanded_gui_rtl_20261015: virtual
matrix/sweep21, compiler17 and composite7. Read that PLAN and per-group status
files. Exact simultaneous AWG/RF start is excluded from fixes. Original compiler
refusals are preserved separately from explicitly tagged +100ns RF-offset cases.
Two isolated xsim slots are used; do not duplicate or restart the FPGA build.
Production Python/GUI, RTL/XDC and user settings are frozen for these tests.

Later on this same task, the requested local v5 updater package was published to
qick/firmware/projects/qstl_awg_v5 (BIT/HWH/XSA/build_manifest.json). Exact hashes
and local package review are in local_firmware_package_20261015/result.json.
No existing firmware was overwritten and no board upload occurred. The package
records the expanded validation as pending. All automations remain PAUSED.

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

## Full build success and active software follow-up — 2026-10-15 02:40 local

The original workflow completed at 02:31:27 with exit0,
`complete=true`, `stage=timing_passed_candidate_not_deployed`. All its processes
have exited. Final routed WNS is +0.028000 ns, WHS +0.009357 ns, TNS/THS zero,
pulse-width failures zero, bus-skew 14/14 MET. Candidate BIT/HWH/XSA hashes,
embedded XSA bytes, seven sum-v2 blocks, AWG delay13/pipeline2/300MHz and
seven AWG 48-bit widths were independently checked. No candidate was deployed.

Original successful artifacts, sources and evidence (417 files) are frozen in
`successful_build_snapshot_v2/manifest.json`. The filename `prebuild_gate.json`
contains the workflow's final postbuild verification at 02:31; the separate
prebuild and postbuild logs are both preserved. Initial snapshot helper attempts
encountered UTF-16 log encoding, multiple subsidiary HWHs and Windows long paths;
the partial first snapshot remains untouched and v2 uses short content-addressed
copies. These were snapshot helper issues after a successful FPGA build.

Authorized postbuild Python/GUI work is now active. The exact eight verified
fine-duration files were promoted with original/source hash checks; backups and
promotion receipt are in `software_followup/fine_promotion`. Driver support for
v1/v2 metadata, role-specific latency and legacy behavior is implemented and
passed 71 unit/actual-HWH checks (`software_followup/driver`). Front Panel v2
baseband/shared-output support and version-specific error messages are being
checked. An independent offline updater-v5 validation change and new actual
GUI-to-v5-RTL adapters are in progress. Existing three-cycle shared-port guards
remain unchanged; exact zero-offset behavior must be reported honestly.

Do not start a duplicate workflow, promote the eight files again, or rerun the
old functional gate against intentionally updated software. Preserve the original
gate/compiler proofs and collect fresh postbuild source/compiler/RTL evidence
under `software_followup`. The running GUI, board, firmware and RTL/XDC remain
untouched. Pause this automation only after postbuild work and reporting finish.

## Postbuild software checks passed; fresh RTL active — 2026-10-15 02:54 local

Production source changes are now frozen for fresh validation. Driver/actual-HWH
71, shared-output GUI/model 68 and offline updater 105 checks passed. The exact
promoted production RF feature passed 680 affected tests and all nine coarse
PMEM/DMEM comparisons, exit0 with explicit Qt teardown and unchanged source
hashes. These group counts overlap and must not be blindly added.
`software_followup/scope_before_tests.json` verifies all 417 snapshot objects,
all protected source/build evidence, and only nine authorized existing-source
changes plus seven authorized additions. Both branches remain `awg_tuning_v4`.

Fresh GUI-to-v5 RTL controller: session61426, Python PID100128 created
02:48:48 local, `software_followup/gui_rtl/run_suite.py`. Read
`software_followup/gui_rtl/suite2_status.json`; build is
`F:/Vivado_Output/a5post_gui_rtl2`. First/second 10us HOLD simulations currently
use two xsim processes. The initial suite preserved a validation-runner missing
wrapper-path copy failure; one later prepare evidence has a harness-hash change
from a diagnostic wording edit and will be replaced by a new tagged run, with
the original rejection retained. No production source or RTL changed for these.

Five fine-width cases and a low-level same-timestamp diagnostic are prepared in
`F:/Vivado_Output/a5post_fine_rtl1`; they wait for the coarse suite so at most
two xsim instances run. Eight real MainWindow zero-offset HOLD/RF requests
already hit the unchanged production conflict guard. Do not label these as
successful simultaneous output. The raw diagnostic's physical timestamps are
explicitly inferred from observed source edges plus independently tested fixed
latencies; the coarse suite separately checks final output-slice samples.

Follow `software_followup/status.json` and the new `REPORT.md` for aggregate
progress. Do not repeat passed software tests, restart the FPGA build, modify
production sources while fresh RTL runs, or pause the automation prematurely.

## Final closeout - 2026-10-15

The waiting stages above are historical. The full v5 build and authorized
postbuild production Python/GUI integration are complete. Final WNS +0.028000 ns,
WHS +0.009357 ns; TNS/THS/pulse-width failures zero; bus-skew 14/14 MET.
The undeployed candidate remains in F:/Vivado_Output/a5full1. All 417 immutable
build snapshot objects remain valid; existing firmware and RTL/XDC are unchanged.

Driver/HWH 71, GUI/model 68, updater 105 and affected feature 680 tests passed,
plus 9/9 unchanged coarse compiler inputs. These groups overlap. Fresh actual
GUI-to-v5 RTL passed seven coarse cases (44 shots x three pairs; 11,821,824 final
DAC checks) and five fine cases (1,536 RF bursts; 16,307,904 sum lane checks).
Every active width 1..31 and all 16 ending patterns were exercised at 0/190 MHz.
The duration step is 0.208333 ns; starts retain the 3.333333 ns clock grid and
the zero-padded generator occupancy is at least 10 ns. All controllers/xsim
processes exited. Production169-file hashes are identical before/after tests;
the exact16 changed/added sources are archived in software_followup/verified_sources.

Exact zero-offset SET/HOLD + RF is still unsupported with this shared-port
command format. Eight real GUI requests remain rejected by the unchanged guard.
Actual raw RTL on all three ports and both orders delivers the second command
three clocks late, implying RF-minus-AWG component output skew +/-10 ns despite
native31/31. The component times are inferred from observed edges and verified
downstream delays. The separate coarse oracle checks actual final summed output.
Positive first/second HOLD cases explicitly request +100 ns RF offset and 9.9 us
width inside the selected10 us HOLD. No requested times were silently moved.
Do not change/rebuild RTL or weaken guards to hide this measured limit.

Source/evidence hash checks and reviewed identical-input retries are linked in
REPORT.md and software_followup/gui_rtl/reporting/REPORT.md. Original failed
runner/audit attempts remain preserved. Both waveform images and the selected48
RC200-shot error plot were opened and checked. Board analog and ADC/FIR arithmetic
were not measured; added DDS area/clipping after IIR are not compensated by the
existing DC-area correction. No board, live GUI, server, firmware replacement,
branch, commit or push action occurred. Pause only awg-v5-rtl after final reporting.

Automation closeout: `awg-v5-rtl` was set to PAUSED through the app and verified on 2026-10-15. Existing `awg-v3` and `awg-v4-timing` remain PAUSED. No simulation or build process remains active.
