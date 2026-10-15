# AWG Tuning v5 — RTL latency equalization

## 2026-10-15 현재 v5 추가 GUI → RTL 검증 완료

새 실제 RTL 37회·352 shots가 통과했습니다. 원본 거부 조건을 통과로 바꾸지 않고 별도 RF +100ns 변형과 분리했습니다. Virtual matrix×sweep 21조건은 원본 1개와 명시적 변형 20개이며, composite 7조건은 원본 그대로 PASS입니다. 별도 compiler 17조합은 Calibration 정상 거부 6개, Quantum N=0 원본 RTL PASS 1개, CPMG/UDD 명시적 +100ns 변형 RTL PASS 8개, Quantum N=1/3 v5 latency 미지원 거부 2개입니다. 원본 45조건 전체 RTL PASS로 표시하지 않습니다.

실제 MainWindow/생산 compiler 입력과 새 PMEM/DMEM을 실제 tProcessor/TMUX/AWG/DDS/v5 합산 RTL로 실행했습니다. 정확한 AWG/RF 동시 시작은 사용자 지시에 따라 수정하지 않았습니다. 생산 소스·RTL/XDC·사용자 설정 및 기존 펌웨어는 보존했고, 이후 요청받은 로컬 v5 BIT/HWH/XSA/manifest 네 신규 파일만 추가했습니다. 보드 업로드와 새 합성은 없으며 자동화는 PAUSED 상태입니다.

[이번 최종 보고서와 케이스별 증거](expanded_gui_rtl_20261015/REPORT.md). Show/Run 경로 비교 및 미재현 정체 진단은 해당 보고서의 별도 링크를 따릅니다.

아래 기존 기록은 각 버전·빌드·조사 당시 상태를 보존한 것입니다.

---

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
