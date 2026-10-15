# Fine-duration software-point metadata correction

The software-sweep bundle formerly copied only the last compiled program summary. Fine-mode runs now retain the original last-program field with an explicit `rf_fine_duration_scope`, and also store `rf_fine_duration_software_points` containing each zero-based index, host coordinate and that program's realized fine-duration metadata. Coordinate columns follow the existing `software_sweep_axes` order.

The new keys are emitted only when at least one program has fine-duration metadata. Coarse summary contents remain exactly equal to the previous construction. This change does not alter runtime execution, compiler emission, hardware axes, timing or board behavior.

Validation: 141 runtime checks PASS in 2.03 seconds, exit 0 with explicit Qt teardown. The three added regressions compile all six actual programs for T2 pi durations 962/994/1026 samples crossed with two named-delay points, verify pi/2 widths 481/497/513 samples, persist the complete summary through local QCoDeS SQLite metadata JSON, and compare coarse metadata with the legacy construction. Only acquisition is replaced in those tests; no board or live GUI is accessed.

Prior 675-check logs/XML, source manifest and nine-case compiler proof are preserved under `before/`. Current source and evidence hashes are recorded in `result.json`. Both production files remain unchanged; this correction exists only in staging.
