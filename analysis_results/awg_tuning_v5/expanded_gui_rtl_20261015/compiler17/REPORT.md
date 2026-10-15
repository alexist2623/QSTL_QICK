# Original compiler17 requests on current v5

Status: completed_with_documented_limitations. The 17 original requests are classified separately from eight explicit +100 ns RF-offset variants.

| Original request | Fresh real-GUI/compiler result | Actual current-v5 RTL |
|---|---|---|
| calibration_ch0_sweep0 | Expected unsupported summed-output calibration guard | Not run: rejected before code generation |
| calibration_ch2_sweep0 | Expected unsupported summed-output calibration guard | Not run: rejected before code generation |
| calibration_ch4_sweep0 | Expected unsupported summed-output calibration guard | Not run: rejected before code generation |
| calibration_ch0_sweep1 | Expected unsupported summed-output calibration guard | Not run: rejected before code generation |
| calibration_ch2_sweep1 | Expected unsupported summed-output calibration guard | Not run: rejected before code generation |
| calibration_ch4_sweep1 | Expected unsupported summed-output calibration guard | Not run: rejected before code generation |
| cpmg_n1_tau200ns | Rejected: shared-port command timing | Original not run; separate +100 ns variant below |
| udd_n1_tau200ns | Rejected: shared-port command timing | Original not run; separate +100 ns variant below |
| cpmg_n1_tau400ns | Rejected: shared-port command timing | Original not run; separate +100 ns variant below |
| udd_n1_tau400ns | Rejected: shared-port command timing | Original not run; separate +100 ns variant below |
| cpmg_n2_tau200ns | Rejected: shared-port command timing | Original not run; separate +100 ns variant below |
| udd_n2_tau200ns | Rejected: shared-port command timing | Original not run; separate +100 ns variant below |
| cpmg_n2_tau400ns | Rejected: shared-port command timing | Original not run; separate +100 ns variant below |
| udd_n2_tau400ns | Rejected: shared-port command timing | Original not run; separate +100 ns variant below |
| quantum_n0 | Accepted | PASS |
| quantum_n1 | Rejected: Quantum RF latency profile does not recognize v5 | Not run: no override applied |
| quantum_n3 | Rejected: Quantum RF latency profile does not recognize v5 | Not run: no override applied |

The Quantum N1/N3 rejection is distinct from the shared-port collision. `DCWaveformGeneratorGUI/quantum_circuit_execution.py::_rf_latencies` automatically accepts the AWG v3 profile only when `output_latency_cycles == 16`. The actual v5 HWH profile reports 31; therefore RF latency is rejected as unknown. No production modification or explicit latency override was used.

Quantum N0 has no RF pulses. Its two-channel circuit uses an identity matrix; it does not inherit the AWG editor virtual matrix.

## Explicit diagnostic variants

For each original CPMG/UDD request, all three RF outer HOLD offsets were explicitly changed from 0 to +100 ns in the actual MainWindow. The original rejection, internal CPMG/UDD pulse spacing, pulse duration/frequency/gain/phase, 3×3 HOLD×amplitude axes, matrix and 2 repetitions are preserved. N and tau are the four 2×2 host software coordinates; each coordinate retains nine hardware HOLD×amplitude points and two repetitions (18 shots). They are not equivalent to matrix21 composite cases, which use a different hardware sweep grid.

| Variant | Actual RTL result | Final output sample comparisons |
|---|---|---|
| udd_n1_tau200ns_rf100ns | PASS | 1794912 |
| udd_n1_tau400ns_rf100ns | PASS | 1794912 |
| udd_n2_tau200ns_rf100ns | PASS | 1794912 |
| udd_n2_tau400ns_rf100ns | PASS | 1794912 |
| cpmg_n1_tau200ns_rf100ns | PASS | 1794912 |
| cpmg_n1_tau400ns_rf100ns | PASS | 1794912 |
| cpmg_n2_tau200ns_rf100ns | PASS | 1794912 |
| cpmg_n2_tau400ns_rf100ns | PASS | 1794912 |

## Evidence and limits

- `inventory.json` and each original case folder preserve the complete GUI request, source hashes, runtime RF specs, rejection text and traceback.
- `semantic_audit/result.json`: all nine prepared cases recompiled through MainWindow with identical PMEM/DMEM; independent C@V integer target checks cover 216 comparisons across eight nine-point variants. Every concrete RF event differs from its original by exactly +100 ns delay and no other event field.
- `prepared.json` / `prepared_cpmg.json`: immutable actual-GUI input hashes, actual candidate HWH metadata and isolated testbench/library sources.
- `rtl_integrity_before.json` / `rtl_integrity_after.json`: original production source and RTL source hashes, compiled simulation snapshots, testbench templates, PMEM/DMEM/envelopes, explicit per-case xsim exit codes and final evidence hashes are independently rechecked.
- The original controller exited 1 only after all nine RTL runs passed: its final auditor incorrectly counted eight newly generated Vivado runtime files as changed compiled inputs. The original controller state, auditor and diagnostic are preserved. `final_audit_v2.py` checks all 327 original files unchanged (including 18 compiled-snapshot files), all 295 prepared expected hashes, and exactly those eight new runtime outputs separately. No RTL run or production edit was repeated; finalization is recorded separately in `postprocessing_completion.json`.
- `runtime_output_metadata.json` records the exact eight new paths, SHA256, sizes, creation/modification times and contents. Both generated xsim wrappers exactly match the final case CASE/OUT/CYCLES/runall options; no generic wildcard exception is used.
- RTL checks include every tProcessor output command and timestamp, TMUX, independent raw AWG assertions, DC area completion/residual/faults, 13-cycle AWG history through v5 sum, final DAC digital slices, RF pulse count/length/registers and carrier phase continuity.
- The RF carrier phase oracle fits the first burst and compares subsequent bursts using the same absolute-cycle phase; it is a continuity test rather than an absolute analog-phase calibration.
- ADC/FIR arithmetic and analog board measurements are outside this validation. No board connection, upload or synthesis was performed. DDS area/clipping after IIR remains outside the original DC-area correction.
- Current original source hash differences: 0.
- Final digital output comparisons: 15,399,504; sum-lane comparisons: 15,421,104.
- Pending RTL: none.
