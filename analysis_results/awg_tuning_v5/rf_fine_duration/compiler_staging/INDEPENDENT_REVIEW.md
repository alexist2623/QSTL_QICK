# Fine RF duration independent review

This review checks the staged compiler and runtime integration. It does not change production code, RTL, the running implementation build, or the board. Actual RTL results have their own source hashes and reports; software checks below do not replace them.

## Findings and resolution

- The frozen `09fdc757ee3f22c456245b36555d530a049a59a8382643fd7f8b1e989fd647ce` helper accepted a generator whose `has_dds` was false. Direct fine register emission bypassed the ordinary manager's DDS capability check. Following explicit freeze release, the sole compiler correction requires `has_dds is True`, matching the boolean driver schema. The new helper hash is `18d262cf1a64ae5cb510658965cba004b98ebe9f226b10b6f9113d74fca6be12`. Existing actual RTL fixtures declare true; emitted command generation was not edited.
- Original helper, test log/XML, hashes, and the review that exposed the missing guard remain in `before_dds_guard_*`, `qick_rf_fine_duration.before_dds_guard.py`, and `independent_review_before_dds_guard.json`.
- Initial runtime bundle metadata retained realized fine widths only for the last software point. The separate runtime owner added `rf_fine_duration_software_points` with every host coordinate and its actual sample widths, and labels the inherited single summary as `last_software_point`. Fine hardware duration arrays remain in each program's summary. Original GUI settings retain requested values.

## Executed checks

The final guarded helper passes 201 focused tests: 136 fine compiler checks, 16 legacy oneshot checks, and 49 DDR/DC timing checks. Four GUI-dependent checks are excluded from this small run; the root task runs the affected GUI suite. See `focused_tests.xml` and `focused_tests.log`.

Seven additional bounded review checks passed on both the original frozen helper and the guarded helper. Exact details are in `independent_review.json`:

1. A count-one duration axis selects its start value (97 samples), repeats three times, and needs no duration table.
2. A descending 112-to-81 hardware sweep crosses the short/long boundary correctly with two outer points and three repetitions. It uses 16 envelopes and 192 DMEM words.
3. Coarse and fine RF events can alternate on the same generator: 10 emitted commands over two repetitions retained expected gain/output-selection values, and the two fine events reported 97 and 81 actual samples. One shared bank contains 16 patterns. Non-fine dispatch still delegates to the unchanged coarse implementation.
4. Insufficient envelope memory (2047 samples for a 2048-sample bank) is rejected before envelope creation.
5. A duration table that exceeds available DMEM is rejected.
6. Named tau host coordinates 1, 2, and 3 microseconds retain exact starts and fixed fine widths, with 16 patterns per compiled program. Tau is explicitly a host sweep; fine RF duration is a hardware sweep and does not add a host loop.
7. Zero, negative and nonfinite durations, and noninteger/boolean/absent sample counts are rejected.

The final guard additionally rejects false or unknown DDS capability. Product quantization is bounded independently over all 65536 signed DDS samples at gains +/-4000 and +/-16383: maximum difference from DDS-only output is one DAC code. `gain_quantization_exhaustive.json` records the formulas and result.

## Scope and limits

- At 300 MHz and 16 samples per fabric clock, width resolution is 1/4800 microseconds (0.208333... ns). Pulse starts remain fabric-clock aligned. Sub-three-clock pulses have zero padding and occupy at least three clocks; overlap validation uses this busy interval.
- Each RF channel loads 16 patterns of 128 samples once. Hardware duration rows select existing addresses, mode words and exact timestamps. Each dependent coordinate uses six DMEM words; frequency/gain tables share the existing hardware sweep machinery. PMEM is not unrolled by point count.
- Supported fine generators are SGv6 with DDS, 16 samples per clock, standard envelope maximum 32766 and matching generator/tProcessor clocks. `stdysel='zero'` is required. Absolute manual or resolved calibration gain above 16383 is rejected because product endings use doubled gain.
- Fine duration sweeps require a fixed HOLD anchor. Automatic HOLD extension driven by a fine duration axis is rejected, as is a coarse event that follows a fine swept duration dependency. Same-generator overlap and shared timed-port collisions remain errors.
- Long durations use a three-clock periodic plateau only beyond the oneshot length limit, with a correctly aligned three-to-five-word tail. Exact actual RTL proof for long cases is tracked in the separate matrix, not inferred from this review.
- Existing normal DMEM capacity checks prevent upload of oversized tables. The Cartesian rows are materialized in host memory before that final capacity rejection; extremely large invalid parameter products can therefore consume host memory during compilation. This remains a practical bounded-input limitation, not a claim of unrestricted sweep size.
- No board analog validation, DAC analog timing measurement, or v5 bitstream result is asserted here. Current actual RTL exercises the existing v4 digital path.
