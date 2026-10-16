# Running — physical RAMP duration × voltage

Current stage: COMPLETED. All48 requested conditions handled:32 physical sweeps and16 range rejections. All24 representative high-resolution captures and independent analysis completed. Overall waveform PASS=false; see REPORT.md.

- New evidence root only. Existing campaign evidence and production sources unchanged.
- Preparation controller: `run_preparations.py`, session24476, max2 Qt workers; first bundle verified and reused.
- Physical controller: `run_campaign.py --execute`, session23987, sequential, sole instrument owner.
- Offline analysis controller: `run_analysis.py`, session73709, sequential; no device access.
- Main grid: rising/falling separately × activeDAC4/5 separately × RC10/20/30 × DC300mV or10/20/30us =48 requested conditions. Each valid condition100×100 points, selected RAMP10ns..1us, requested voltage−400..400mV, HOLD10us; otherDAC0V/otherRAMP1us.
- Range-rejected conditions remain NOT RUN; no bypass or voltage reduction.
- First actual physical case `run_rising_dac4_fixed_time10_tau20_01`: exit0, counter10000, no holes/clipping, zero cleanup and fullscope restore PASS. MainHOLD10000PASS; separate DC1FAIL / post-DCzero9FAIL preserved.
- The originally planned main48 handling, highres24 captures, independent audit, plot inspection and Korean report are complete. Evidence-only archival/commit/push uses the existing awg_tuning_v4 branch.

## High-resolution evidence

Fullframe dt500ns cannot resolve10ns RAMP. Plan representative1point fixed duration10ns/500ns/1us, voltage±400mV, activeDAC4/5 and rising/falling separately atRC20/DCfixed10us. Prepare after the max2 mainQt workers finish. `prepare_highres.py` and `analyze_highres.py` owned by highres agent, mainhelpers frozen. Initial highres Qt accessviolation−1073741819 occurred before compilation/output, preserved; root cause unconfirmed. No instrument was accessed by that attempt.

No new synthesis, firmware replacement, server restart or userGUI termination.

## Reviewed preparation recovery

Original main preparation stopped with25successful exits,1SIP teardown accessviolation and22pending cases. Windows Event1000 identifies sip.cp312-win_amd64.pyd/0xc0000005 after all compiled/model artifacts and manifest were saved. Original batch/status/artifacts remain unchanged.

`prepare_main_resume.py` changes only isolated CLI termination after complete success evidence or after failure evidence. One fresh retry `offline_rising_dac5_fixed_voltage_tau30_retry01` exited0. `preparation_resume_retry_comparison.json` proves identical ASM/PMEM/DMEM, decompressed expected/model data, GUI input/compiler plans and source hashes. The25successful preparations were reused by hash; only22pending conditions are newly prepared. Resume session89860; state `preparation_resume_status.json`; final merged state `preparation_merged_status.json`.

Highres original wait controller exited without starting Qt because main preparation stopped. New waiting controller session99182 uses `highres_preparation_resume_status.json` and waits for the merged main result plus actual process exits. No highres hardware is started until main physical campaign ends. Highres runner now requests50us record at≤0.5ns; separate native time origins are retained with absolute difference≤1ns and no channel-skew certification.

## Completed acquisition and analysis

Main preparation48 = 32 prepared plus16 range rejections. Physical controller23987 and analysis73709 exited0. Main final audit83771 exited0: 320000points; activeHOLD32FAIL/max20.283694mV; DC64FAIL/13702INCOMPLETE; postDCzero173FAIL. Main raw, analysis and fullframe_summary_01 are frozen.

Highres preparation99182 and physical/analysis controller74275 exited0 with24 captures, each500000samples/channel at0.1ns. All AWGzero/scope restore/source preservation checks passed. First10ns postRAMP review reports−81.758mV peak residual; short fallingRAMP timing review is complete: actual edge present, but54.335ns first-edge candidate ambiguity prevents assigning the approximately41ns displacement to RTL. Existing measurements and criteria remain unchanged.

## Final result

Root REPORT.md/results.json integrate frozen fullframe and representative results. Highres48RAMP windows include13 median residuals over15mV; largest model residual399.051mV is sensitive to the documented first-edge alignment ambiguity and is not an established pure amplitude defect. The independent first10ns rising transient has−81.758mV peak residual. Precision timing/settling are not certified. All56 acquisitions ended with zero cleanup/fullscope restore; all170production-source hashes remain unchanged. No instrument/controller process remains active.
