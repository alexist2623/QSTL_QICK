# RF fine duration: promotion review

Reviewed 2026-10-15T00:23:00.856456-07:00. This is a read-only source/gate audit, not promotion approval or final feature signoff. Production, existing gates, live GUI and board were not changed. Exact original/current paths and hashes are in [promotion_review.json](promotion_review.json).

## Scope and source identity

All 105 original top-level production Python files still match `before_manifest.json`; no production additions or missing baseline files were found. Staging has 109 top-level Python files. Exactly four existing production modules changed, one production module is new, and three tests are new.

| File | Change | Role | Proposed SHA256 |
|---|---|---|---|
| `DCWaveform_Generator.py` | changed | production | `feb847fe8dd879251921e9f841f3d18c23be17632fa17fc671cef8d38374192a` |
| `dc_waveform_core.py` | changed | production | `5b4010d5f9cc4eaad22a7b44ef19d052732c9e02a0c661bad02aec8be42d1941` |
| `qick_fine_tune_sweep.py` | changed | production | `9fcd771c595373cde3e012c1d144b334b4f1226deff05763861198db609179d6` |
| `qick_qcodes_experiment.py` | changed | production | `38a157763efc6c2a939006c320e24c2d1e9544e433bd28c545678505f36159f1` |
| `qick_rf_fine_duration.py` | new | production | `09fdc757ee3f22c456245b36555d530a049a59a8382643fd7f8b1e989fd647ce` |
| `test_rf_fine_duration_compiler.py` | new | test | `4289627b1b86f8e567aac8f6c59778cbd4cb71a53e54726955b43bddb246a9b0` |
| `test_rf_fine_duration_editor.py` | new | test | `4ae5e973272acd372532e3e6ae780d21d9b1b5337ceea82526d8cf53d641abf1` |
| `test_rf_fine_duration_runtime.py` | new | test | `225f0d0d038382e003f0902a0b0e8f096d56e8b35cb6c9ba4552aff8e3026e6c` |

No other source files should be copied from staging. Before any later copy, recheck these hashes and the original production hashes; a changed source invalidates this snapshot and its matching evidence.

## GUI, persistence and user-visible behavior

- The common RF-port `Fine duration (DAC sample)` checkbox maps to strict Boolean `QickRfPulseSpec.fine_duration`, defaulting to false for old settings. It covers every pulse emitted by that RF port, including Custom and derived T2 endpoints.
- Panel save/load, both MainWindow JSON decoders, preset/Custom cloning, generated Python RF configuration, runtime conversion and experiment metadata carry the flag. Requested values and actual sample counts/durations are distinguished in runtime metadata.
- Duration editors keep nine decimal places in microseconds. RF duration sweep labels use 12 significant digits, so a sample-sized change at a long duration remains visible. The shared quantizer rounds upward except for snapping within half the GUI decimal resolution (plus floating-point tolerance) to the exact sample grid.
- Editor evidence includes actual-widget roundtrips of all 16 ending residues, Single and Custom modes, old defaults, T2 and precise long-duration labels. `editor_preview.png` was rendered and opened; it shows a 32-point 81..112-sample sweep without overlap or clipped controls.
- This is active width/ending resolution. At 300 MHz and 16 samples per fabric clock the DAC sample period is 0.208333333 ns; starts remain fabric-clock aligned. Analog rise time and physical board behavior have not been measured.

## Limits that belong in the final report

- Opt-in only. SG-v6, 16 lanes, matching fabric/tProcessor clock and the supported standard maxv=32766 geometry are required.
- Requested manual gain or resolved calibration gain must remain within -16383..16383 at every point. Envelope scaling uses twice the gain; exhaustive integer scaling checks bound plateau-versus-product error to one DAC code for the checked full DDS range and boundary gains.
- Sixteen 128-sample I/Q patterns use 2048 complex envelope samples per generator, preloaded once. DMEM rows select the ending inside the hardware loop. This is not a per-point host upload.
- Very short pulses still occupy a minimum three fabric clocks with zero padding. Active duration and generator busy time differ; existing command-spacing, overlap and memory guards remain active.
- Hardware fine-duration sweeps require a fixed AWG HOLD anchor; incompatible HOLD-extension schedules are rejected. Existing T2 pi-duration host-sweep policy is unchanged.
- Current Python uses the existing v4 timing profile. The fine-duration RTL harness uses the real tProcessor/TMUX/SG-v6/vendor DDS and sum topology but does not establish pending v5 absolute RF/AWG latency or analog output correctness.

## Existing gate requirements

`validate_scope.ps1` first verifies every exact `authorized_gui_fix.json.files` hash, then compares the immutable original protected baseline. With `-RequireFunctional`, it also validates original RTL/replay/RC source hashes and the nine-case current compiler proof. The 18 unit/system/RC hash manifests were inspected: none references any of these eight proposed Python destinations, so unchanged RTL evidence remains independently checked.

`recompile_inputs.py` records every current top-level GUI Python source and qick library source. It requires byte-identical PMEM/DMEM for all nine original replay cases. Therefore replacing only authorization hashes is insufficient: a fresh compiler proof from the promoted files is mandatory. Do not manually relabel old proof source hashes as current. Preserve the original compiler report/logs before producing the new proof.

The current `run_workflow.ps1` calls the same strict functional gate after Vivado finishes. Its reader has no lock or atomic multi-file snapshot. Replacing sources, authorization and compiler proof while it reaches that postbuild gate can create a transient mismatch even when the eventual state is valid. Updating authorization first or last does not solve this race.

## Recommended promotion sequence

1. Finish the strict actual-RTL phase and full hardware-sweep matrix, final affected regression and nine-case staging compiler proof. Freeze final source/evidence hashes.
2. Prefer leaving production untouched until the existing build and its postbuild source gate finish. If promotion during the build is essential, first establish a coordinated quiescent interval that prevents the postgate reader from executing; the present workflow provides no such mechanism. Do not weaken or bypass the gate to make the copy pass.
3. Recheck production against the 105-file baseline and preserve original authorization/compiler/gate evidence. Copy only the eight reviewed files.
4. Merge the exact eight `proposed_authorization_files` entries from the JSON into `authorized_gui_fix.json.files`, preserving unrelated entries and prior reasons. Add a fine-duration reason and final evidence path/hash. Keep `protected_before.json`, `validate_scope.ps1`, RTL, XDC and build timing conditions unchanged.
5. Run the unchanged nine-case `recompile_inputs.py` into a new isolated build folder, preserving earlier proof. Verify all source hashes and byte-equal PMEM/DMEM, then run the unchanged functional gate. The nine coarse cases prove backward compatibility; new fine-mode RTL/phase evidence is a separate necessary signoff.
6. Record the promoted hash set and final validation results. Do not restart a live GUI/server, upload to the board, replace firmware or otherwise deploy without the applicable user authorization.

## Snapshot blockers

At the time of this review, compact3 first-case actual RTL passed with the strict command oracle. Phase and the full hardware-duration matrix were still pending. This report does not mark them passed.

`staging_verified_sources.json` matches all current staged files. `baseline_equivalence.json` and `staging_final_sources.json` are stale for `qick_rf_fine_duration.py` and `test_rf_fine_duration_compiler.py` after the instruction-throughput correction. Root's post-correction affected suite is separate and must be assessed when complete. The final promotion proof must match the frozen source hashes, including the helper hash shown above.
