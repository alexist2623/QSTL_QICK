# AWG v5 build and software follow-up

## 2026-10-15 현재 v5 추가 GUI → RTL 검증 완료

새 실제 RTL 37회·352 shots가 통과했습니다. 원본 거부 조건을 통과로 바꾸지 않고 별도 RF +100ns 변형과 분리했습니다. Virtual matrix×sweep 21조건은 원본 1개와 명시적 변형 20개이며, composite 7조건은 원본 그대로 PASS입니다. 별도 compiler 17조합은 Calibration 정상 거부 6개, Quantum N=0 원본 RTL PASS 1개, CPMG/UDD 명시적 +100ns 변형 RTL PASS 8개, Quantum N=1/3 v5 latency 미지원 거부 2개입니다. 원본 45조건 전체 RTL PASS로 표시하지 않습니다.

실제 MainWindow/생산 compiler 입력과 새 PMEM/DMEM을 실제 tProcessor/TMUX/AWG/DDS/v5 합산 RTL로 실행했습니다. 정확한 AWG/RF 동시 시작은 사용자 지시에 따라 수정하지 않았습니다. 생산 소스·RTL/XDC·사용자 설정 및 기존 펌웨어는 보존했고, 이후 요청받은 로컬 v5 BIT/HWH/XSA/manifest 네 신규 파일만 추가했습니다. 보드 업로드와 새 합성은 없으며 자동화는 PAUSED 상태입니다.

[이번 최종 보고서와 케이스별 증거](expanded_gui_rtl_20261015/REPORT.md). Show/Run 경로 비교 및 미재현 정체 진단은 해당 보고서의 별도 링크를 따릅니다.

아래 기존 기록은 각 버전·빌드·조사 당시 상태를 보존한 것입니다.

---

Final status — 2026-10-15 03:27 America/Vancouver: the full FPGA build and
authorized postbuild Python/GUI work are complete. Fresh supported GUI-to-v5 RTL
cases passed. **Exact zero-offset SET/HOLD + RF on a shared port remains
unsupported with the present command format.** Both native latencies are 31
clocks, but the second shared-port command arrives 3 clocks (10 ns) late.
This limitation was measured and retained; no timing guard or requested time
was relaxed, and no RTL rebuild or deployment followed.

## Completed FPGA build

The original `F:/Vivado_Output/a5full1` workflow finished on 2026-10-15 at
02:31:27 America/Vancouver with exit 0 and
`stage=timing_passed_candidate_not_deployed`.

| Final routed measurement | Result |
| --- | ---: |
| Setup WNS | +0.028000 ns |
| Hold WHS | +0.009357 ns |
| TNS / THS | 0 / 0 |
| Pulse-width failing endpoints | 0 |
| Bus-skew paths | 14/14 MET |
| Minimum reported bus-skew slack | +2.475 ns |
| Fully routed nets | 582434/582434 |
| Routing errors | 0 |

The exact BIT/HWH contents match their members in the same XSA. Seven sum-v2
blocks have AWG delay 13, pipeline 2, 300 MHz clocks and seven 48-bit AWG paths.
Both source gates passed. The candidate remains outside Git and is not deployed.

- [Workflow status](workflow_status.json)
- [Final routed timing](F:/Vivado_Output/a5full1/timing_summary_postroute.rpt)
- [Candidate manifest](F:/Vivado_Output/a5full1/candidate_manifest.json)
- [BIT](F:/Vivado_Output/a5full1/bitstream.bit),
  [HWH](F:/Vivado_Output/a5full1/bitstream.hwh),
  [XSA](F:/Vivado_Output/a5full1/bitstream.xsa)
- [Immutable successful-build snapshot: 417 files](successful_build_snapshot_v2/manifest.json)

The historical `prebuild_gate.json` filename contains the final postbuild check;
both original gate logs and their timestamps are preserved in the snapshot.
Original gate and candidate metadata describe the software at build completion
and are not rewritten to claim later Python integration.

## Fresh RTL checks before the build

- Native AWG/DDS latency: 96 conditions, both 31 clocks at the sum output.
- Sum/bypass/reset/valid/saturation: 1,115,040 samples passed.
- Direct 10 us RAMP/HOLD/RAMP/HOLD, RF in each HOLD, three pairs: 288,000 checks.
- Six basic RTL suites passed. Software baseline: 74 modules / 1,249 checks
  after three reviewed desktop-environment retries, with first failures retained.
- Nine system replays passed. Their inputs retain v4 software timing; they are
  not evidence of postbuild v5 GUI timing compatibility.
- Selected 48-bit continuous RC: 200 shots, overflow/collection/residual and
  accumulated area errors zero. Maximum modeled RC error 0.054616819 mV;
  maximum end error 0.000863351 mV. No 32/64-bit comparison was repeated.

[Selected-48 RC error plot](selected48/rc_error_48.png) was opened and visually
checked, as were both final postbuild waveform figures linked below.

## Authorized postbuild software

The successful build was frozen before any production software change.
The exact eight already-validated fine-duration files were promoted with
original destination hashes and backups. Driver metadata then gained v2 support.

- v5 AWG/RF latency is 31/31 clocks; v4 remains 18/31 and legacy AWG remains 16.
  Repeated configuration does not accumulate delays. Shared physical DAC routes
  are checked from HWH, including four bypass AWGs.
- Front Panel recognizes v2 shared DACs, chooses the AWG logical generator in
  AWG mode and retains baseband-only output controls.
- Compiler timing consumes the firmware latency metadata. Shared-port spacing
  guards remain unchanged; version-specific errors identify v5 conflicts.
- The updater validates a future explicitly selected v5 deployment manifest and
  actual HWH topology offline. The current candidate manifest is not treated as
  a deployment manifest. No firmware was copied, selected or applied.
- RF active width supports 0.208333333 ns sample steps, including 1–31 samples.
  The generator occupies at least three fabric clocks (10 ns) including zero
  padding. Start timing remains on the 3.333333333 ns fabric grid. Sixteen
  preloaded ending patterns support fixed-HOLD hardware width sweeps; this does
  not make all timing parameters sample-resolution hardware sweeps.

Completed postbuild software runs:

| Run | Result |
| --- | ---: |
| Driver and actual v3/v4/v5 HWH | 71 passed |
| Shared-output GUI and compiler behavior model | 68 passed |
| v5 updater plus unchanged updater UI/transaction tests | 105 passed |
| Promoted RF feature and affected production GUI/compiler modules | 680 passed |
| Unchanged coarse GUI/public-builder PMEM/DMEM comparisons | 9/9 identical |

These are run-level counts with overlapping tests, not a claimed sum of unique
tests. GUI tests ended with explicit Qt teardown and exit 0. The 680-test run
also verified unchanged source hashes across execution.

- [Driver evidence](software_followup/driver/REPORT.md)
- [GUI log](software_followup/gui/gui_v5.log)
- [Updater evidence](software_followup/updater/REPORT.md)
- [Production RF feature regression](rf_fine_duration/postbuild_production1/result.json)
- [Final source/build scope audit](software_followup/scope_after_tests.json)
- [Exact tested software archive](software_followup/verified_sources/manifest.json)

All 417 successful-build snapshot objects remain valid. All 169 production
Python file hashes are identical before and after the postbuild tests. Only the
nine authorized existing files and seven authorized additions differ from the
build-time source; these 16 files are preserved in the tested-software archive.
The existing firmware, RTL/XDC and original build evidence remain unchanged.

## Actual GUI-to-v5 RTL verification — complete with the stated limitation

Fresh MainWindow inputs use the actual candidate HWH and production v5 latency
profile. Seven bounded HOLD/sweep/RC/DDR cases and five fine-width cases passed
actual tProcessor/TMUX/AWG/DDS/sum-v2 simulation. All controllers and xsim
processes have exited. The two exact
10 us RAMP/HOLD/RAMP/HOLD cases explicitly request RF offset +100 ns and width
9.9 us. These are legal-offset tests, not silent replacements for zero offset.

| Fresh postbuild execution | Result |
| --- | ---: |
| Actual MainWindow coarse cases | 7 cases, 44 shots × 3 pairs |
| Final digital DAC output checks | 11,821,824 samples, zero errors |
| Fine-width GUI-to-RTL cases | 5 cases, 1,536 RF bursts |
| Fine sum-output lane/sample checks | 16,307,904, zero errors |
| Command value/timestamp and sum-lane errors | 0 |
| Zero-offset GUI requests | 8 expected rejections |

Coarse coverage includes the first and second HOLD, both HOLD-duration sweep
compensation modes, RF duration with fixed/extended HOLD, RC-only and both DDR
policies. Fine coverage includes all 16 remainder patterns on each RF channel
and every active width 1–31 samples on all three pairs at 0 and 190 MHz. The
190 MHz short-pulse check uses a separately observed long reference. Fine width
is measured at the RF sum input and the sum output is independently checked on
all lanes; the separate coarse suite checks the actual final output slice.

- [Fresh GUI-to-v5 RTL report and exact evidence paths](software_followup/gui_rtl/reporting/REPORT.md)
- [First/second 10 us HOLD waveform](software_followup/gui_rtl/reporting/v5_first_second_hold_v3.png)
- [1/16/31-sample RF waveform](software_followup/gui_rtl/reporting/v5_fine_1_16_31.png)

Eight separate MainWindow zero-offset requests (first/second HOLD, individual
and all pairs) correctly hit the unchanged shared-port conflict check.
The raw identical-timestamp diagnostic completed on all three shared ports:
the first word arrived on time and the second arrived three clocks late.
AWG-first therefore gives inferred RF-minus-AWG output skew +3 clocks; RF-first
gives -3 clocks, or +10/-10 ns at 300 MHz. These component output times are
inferred from directly observed sum-input edges and separately validated fixed
downstream latencies; they are not separate analog measurements after addition.

**Equal native latency does not provide exact simultaneous SET/HOLD + RF output
with the present shared-port command format.** The dispatcher owns one timestamp
FIFO per physical port and needs READ/WAIT/SET states between releases; changing
the TMUX selector does not create a second timed queue. The diagnostic bypasses
GUI construction only to expose this behavior. Its completed `passed` status is
not a simultaneous-timing PASS, and `simultaneous_output_supported=false` is
explicitly recorded. Production guards and requested times were not changed.

- [Actual same-timestamp diagnostic](F:/Vivado_Output/a5post_fine_rtl1/raw_same_timestamp/result.json)
- [RTL dispatcher/TMUX source review](software_followup/review/TMUX.md)
- [Separate fine-input/provenance audit](software_followup/gui_rtl/reporting/fine_input_provenance_audit.json)

The fine-input audit checks every channel/frequency/gain/phase and sweep field,
records the actual candidate HWH/configuration/RTL hashes, and reproduces exact
PMEM/DMEM/envelope bytes. GUI decimal serialization was checked against the
production ceil-to-cycle rule: no requested-versus-GUI command-time differences
were found. This supplement is stored separately from the original preparation.

[Verification plan](software_followup/gui_rtl/PLAN.md),
[final machine-readable status](software_followup/status.json) and
[independent review with supplementary audit](software_followup/review/REPORT.md).

## Retained issues and scope limits

The initial snapshot helper encountered UTF-16 log encoding, subsidiary HWH
members and Windows long paths. The partial first snapshot remains intact; the
final snapshot uses short content-addressed paths and verifies every file.
Updater test setup/parser issues and the GUI-RTL runner's missing wrapper-path
copy are preserved with original logs; none was a new FPGA timing failure.
The original coarse suite status remains failed because one preparation hash
included a validation-only diagnostic file that changed before simulation.
Only that file differed; the new tagged fixed-voltage run had byte-identical
GUI/PMEM/DMEM inputs and passed. The final aggregate explicitly reconciles this
retry without overwriting the first failure. A supplementary audit's first
empty-log termination has no proven cause; its logged retry exposed a checker
rounding error. The new audit uses the production ceil rule, preserves earlier
attempts and reports zero requested/GUI quantized-time differences.

RTL/XDC, existing firmware, running GUI and board/server were not changed during
this follow-up. No board analog measurement was performed. The sum is after AWG
IIR, so existing DC-area correction does not compensate added DDS area or clipping.
ADC/FIR arithmetic and board analog behavior were not validated by this work.
The unchanged seven-clock RAMP startup and shared-port command arrival must be
distinguished from equal native generator latency.

Automation closeout: `awg-v5-rtl` was set to PAUSED through the app and verified on 2026-10-15. Existing `awg-v3` and `awg-v4-timing` remain PAUSED. No simulation or build process remains active.
