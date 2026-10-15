# v5 firmware updater offline review

Status: PASS. This change validates a future, explicitly selected v5 package; it does not copy the candidate into the firmware repository, select it automatically, connect to a board, or update firmware.

## Change

`PulseGenerator/DCWaveformGeneratorGUI/qick_update.py` now recognizes v5 from its project folder or from actual `axis_output_sum_v2` HWH modules. A renamed v5 folder therefore cannot fall back to the legacy file-pair-only review.

The review requires the existing deployment `build_manifest.json` format: finite passing setup/hold timing values, an artifact list, SHA256/size matches for BIT/HWH/XSA, named and unique BIT/HWH members in the XSA, and a passed topology record tied to the actual HWH SHA256. `candidate_manifest.json` is explicitly not treated as a deployment manifest.

Pure XML validation checks seven v2 combiners, no v1 combiner, 16 samples/clock, AWG delay 13, output pipeline 2, matching 300 MHz clocks, seven 48-bit AWGs, zero-valued bypass inputs, and every AWG/RF → combiner → register slice → expected RFDC DAC connection. Manifest topology must match those actual routes, including the separate `output_sum_awg_delay_cycles=13` and `post_output_latency_cycles=2` fields. The updater does not import or execute a firmware validator script.

The v4 and legacy review paths remain compatible. The default selection remains v4. Existing UI and transaction test sources were not changed.

## Validation

- Final run: **105 passed**, exit 0, explicit offscreen Qt teardown completed.
- New v5 tests: **50**. They copy the actual successfully built HWH into disposable test directories, use clearly fake BIT bytes and temporary XSA archives, and exercise only offline review.
- Existing updater UI/transaction regressions: **55**, unchanged test sources. All board actions are fakes or disposable local transactions.
- Verified rejection cases include absent/candidate manifests, renamed v5, invalid/nonfinite timing, duplicate artifact records, BIT tampering, wrong XSA member selection, duplicate XSA members, modified sum delays/pipeline/width/bypass, clock mismatches, nonzero bypass source, broken links, and mismatched topology metadata.
- Successful package review preserves every temporary package byte. No live GUI, board, server, production firmware, or installation metadata was changed by these checks.

Evidence: [final.log](final.log), [final.xml](final.xml), [results.json](results.json), [run_offline_tests.py](run_offline_tests.py).

## Earlier attempts retained

`v5_review.log` records an initial missing pytest import path. `v5_review_retry1.*` records a new fixture assertion that incorrectly expected the actual HWH root to be `SYSTEM`; the actual Vivado root is `EDKSYSTEM`. `v5_review_retry2.*` records six failures caused by the new validator treating the hexadecimal zero constant as a decimal string. The parser was corrected to compare integer values, preserving the zero-value requirement. `v5_review_retry3.*` has 48 passing tests before two additional delay-metadata checks were added. These earlier results are preserved and are not additional unique passing tests.

The input HWH is from `F:/Vivado_Output/a5full1/bitstream.hwh`, SHA256 `52d16d740d227698e4f07f20113d24aa866531d8cb161e54ef899b8c67f54080`. This offline review does not itself validate v5 GUI timing, authorize deployment, or constitute an analog board measurement.
