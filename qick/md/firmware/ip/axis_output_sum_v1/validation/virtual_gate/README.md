# Virtual gate parameter-sweep validation

These are validation-only adapters. They do not edit the production GUI,
Python driver, RTL, XDC, firmware, board, or user settings.

- `cases.py`: fifteen orthogonal configurations, using a fully coupled,
  asymmetric 3×3 matrix and 800/400/800 mV output scales.
- `run_case.py`, `support.py`: actual MainWindow matrix and AWG sweep dialogs
  receive keyboard input; the Run Experiment PMEM/DMEM must equal the export.
  An independent C×V/integer-increment oracle checks every Cartesian target.
  Current real tProcessor/TMUX/AWG/IIR/RF/output-sum RTL executes those bytes.
- `square_oracle.svh`: independent command-level phase accumulator and exact
  scalar filter recurrence for every Square output lane.
- `run_composite.py`, `composite_support.py`: actual GUI CPMG N/τ software
  coordinates and named frequency/duration sweeps. The public software-point
  selectors are used; no fake acquisition or hardware connection is involved.
- `../../../../../test/firmware/ip/axis_output_sum_v1/validation/virtual_gate/test_coverage.py`: **GUI/compiler tests, not Verilog**. Tests the three
  summed RF power guards, CPMG/UDD N×τ points, and Quantum Circuit matrix/loop
  scope. Known unsupported inputs remain visible as failures in this audit.
- `run_retry.py`, `run_off_final.py`: preserved, separately named retries of
  test-harness mistakes. They are not product fixes or relaxed tolerances.
- `report.py`: consolidates initial/retry evidence without replacing original
  failed logs, checks protected/production hashes, and preserves real failures.
- `diagnose_failures.py`: records exact conflicting clocks and latency metadata.

All simulation folders are outside Git, in `F:/Vivado_Output/a3sim1`.
Preparation modifies shared simulation libraries and must be serial. Only
isolated snapshots can simulate concurrently, with at most three processes.
Do not start another controller while the current controller is active.

Use the qcodes2 interpreter, offscreen Qt, existing desktop `qick.sim`
bootstrap/dependency paths, and Vivado 2023.1. The controller guards reject
overwriting the dated evidence. To execute a standalone fresh case, supply a
new `--run-tag`; use `--prepare-only` and then `--reuse-snapshot` with exactly
the same arguments and unchanged source. Never substitute an older PASS when
the input, source, routing, or pipeline changed.

The canonical case list/status and result table are in
`analysis_results/awg_tuning_v4/virtual_gate_rtl_20261014/`. This is additional
coverage, not another synthesis run or a replacement for the full regression.
It does not exhaust every parameter×compensation×direction Cartesian product.
It does not claim analog board validation or elimination of SET quantization
error. Quantum Circuit does not inherit the AWG Tuning virtual matrix.
