# Focused simple-case software regression — 2026-10-15 local

Status: **110/110 selected implemented software tests passed** across 12 source modules. Process exit 0; zero failed/skipped/not-run cases. No retry or environment failure.

This is a fresh run of existing unit tests, compiler/tProcessor behavior-model checks and offscreen GUI tests. It is not a physical GUI-to-board/scope run, and it is not the separate representative RTL run. No production or test source was edited.

## Scope and counts

| Category | Unique tests | Result |
|---|---:|---|
| HOLD/RAMP duration and anchored timing | 6 | PASS |
| RF frequency/duration, fine masks, repetitions and boundaries | 34 | PASS |
| Voltage, nonidentity virtual matrix and metadata | 7 | PASS |
| Acquisition anchors, DC/RC compensation and resets | 34 | PASS |
| Invalid gain/range, short duration, overlap/spacing and cancellation | 16 | PASS |
| Existing offscreen GUI input, settings and exported-code paths | 13 | PASS |

Counts are unique pytest node IDs after parametrization. The 74 explicit selectors expand to 110 cases; category counts do not overlap. Every exact node ID and phase result is preserved in `pytest_results.json`, `collected.json`, and `category_mapping.json`.

## Evidence and integrity

- Start: 2026-10-16T01:43:06.247660+00:00
- End: 2026-10-16T01:43:20.938330+00:00
- Raw output: `pytest.log`; JUnit: `junit.xml`; per-phase event stream: `events.jsonl`.
- Before/after SHA-256 maps: `source_before.json` / `source_after.json`. All 170 Python production/test files under PulseGenerator/DCWaveformGeneratorGUI and QSTL_QICK/qick/qick_lib remained byte-identical.
- Requested scope: `selection.json`; original TODO input: `TODO_input.txt`; input SHA-256 is recorded in `run_started.json`.
- Exact executable, command, working directory, timestamps and final exit status: `run_started.json` / `run_finished.json`.
- Reproduction: run `run_controller.py` in a fresh evidence directory after updating its ROOT through copying the complete evidence harness; the existing controller intentionally refuses to overwrite its current result files.

## Harness and environment

Used qcodes2 Python, the existing qick.sim desktop PYNQ bootstrap, the documented dependency PYTHONPATH, QT_QPA_PLATFORM=offscreen, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 and disabled bytecode/pytest cache. One owned QApplication was explicitly closed after pytest to avoid desktop teardown ambiguity. TCP connection methods were blocked within the validation process. Test code and assertions were unchanged.

## Scope limits

- RF duration register-arithmetic TODO: **unavailable**, not implemented. These tests exercise the existing six-word per-dependent-point DMEM tables. They do not demonstrate a 4,800-point constant-memory implementation.
- Grouped sweeps/shared point-count linkage/lifecycle: **unavailable**, not implemented. Existing Cartesian or shared-duration parameters are not treated as this future feature.
- Physical v5 GUI/board/scope measurements, analog timing and RF carrier fitting, hardware trigger timeout/incomplete transfer recovery, and a full archive of actual measured waveforms: **not performed**.
- The selected checks do not directly test a within-HOLD violation that appears only at a later fine-duration point; that negative GUI case must remain separately identified.
- Invalid range/count checks cover the listed existing rejection tests, not every possible invalid input across all sweep types.
- Existing unit tests use local metadata/fakes/behavior models where their fixtures specify them. Offscreen GUI PASS does not imply visible GUI-to-hardware acquisition PASS.
- Scope/precision-timing measurement was explicitly deferred by the current user request.

## Selection rationale

The run includes basic SET/RAMP loops, duration movement of later commands and acquisition anchors, N=1 and descending RF axes, fine short/long sample boundaries, pattern reuse, hardware pointer reset, nonidentity virtual-to-physical conversion and storage metadata, independent DC/RC combinations, and explicit invalid gain/range/padding/spacing/cancellation cases. Large 200x200/million-point suites and unrelated features were excluded.

## Outcome

All selected existing checks passed on this source snapshot. The unavailable/deferred/partial items above remain coverage gaps; this result is not completion of every acceptance criterion in the TODO.
