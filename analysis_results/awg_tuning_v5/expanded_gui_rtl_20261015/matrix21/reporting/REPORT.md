# Current v5 Virtual matrix × sweep GUI → RTL results

Fresh selected executions: 21/21 PASS. Original unmodified requests passed: 1; original requests rejected: 20; explicitly labelled +100ns variants passed: 20.

Original requests and explicit-offset variants are separate results. No production timing guard or requested original timing was changed.

| Case | Original request | Actual RTL input/result | Points × repeats |
|---|---|---|---|
| hold_fixed_time | shared-port rejection preserved | explicit RF +100ns PASS | 9 × 2 |
| hold_fixed_voltage_descending | accepted | original PASS | 9 × 2 |
| ramp_fixed_time | shared-port rejection preserved | explicit RF +100ns PASS | 4 × 2 |
| ramp_fixed_voltage_descending | shared-port rejection preserved | explicit RF +100ns PASS | 4 × 2 |
| rf_duration_fixed | shared-port rejection preserved | explicit RF +100ns PASS | 4 × 2 |
| rf_duration_extend | shared-port rejection preserved | explicit RF +100ns PASS | 4 × 2 |
| rf_frequency | shared-port rejection preserved | explicit RF +100ns PASS | 4 × 2 |
| two_voltage_axes | shared-port rejection preserved | explicit RF +100ns PASS | 9 × 2 |
| two_voltage_axes_reversed | shared-port rejection preserved | explicit RF +100ns PASS | 9 × 2 |
| rc_only | shared-port rejection preserved | explicit RF +100ns PASS | 4 × 2 |
| dc_only | shared-port rejection preserved | explicit RF +100ns PASS | 4 × 2 |
| compensation_off | shared-port rejection preserved | explicit RF +100ns PASS | 4 × 2 |
| square_frequency | shared-port rejection preserved | explicit RF +100ns PASS | 4 × 2 |
| square_amplitude | shared-port rejection preserved | explicit RF +100ns PASS | 4 × 2 |
| square_phase | shared-port rejection preserved | explicit RF +100ns PASS | 4 × 2 |
| cpmg_n1_tau200ns | shared-port rejection preserved | explicit RF +100ns PASS | 2 × 2 |
| cpmg_n1_tau400ns | shared-port rejection preserved | explicit RF +100ns PASS | 2 × 2 |
| cpmg_n2_tau200ns | shared-port rejection preserved | explicit RF +100ns PASS | 2 × 2 |
| cpmg_n2_tau400ns | shared-port rejection preserved | explicit RF +100ns PASS | 2 × 2 |
| cpmg_named_frequency | shared-port rejection preserved | explicit RF +100ns PASS | 4 × 2 |
| cpmg_named_duration | shared-port rejection preserved | explicit RF +100ns PASS | 4 × 2 |

Executed totals: 96 points, 192 shots, 5568 commands; 18,725,952 v5 sum lane checks and 18,675,552 final digital output lane checks.

The saved GUI axes, order, counts and directions match all 96 Cartesian coordinates of the independent oracle. The independent C×V/increment oracle has 288 compiler-model target comparisons. A separate post-execution audit directly checks 576 actual RTL HOLD SET payloads (each shot × three ports), including repetition and axis rewind. Per-case applicability, counts and observed values are in result.json.

The matrix and AWG axes were entered through real modal widgets. Actual MainWindow compiler PMEM/DMEM were matched before the RTL execution. CPMG N/τ coordinates use the existing production software-point selector; named frequency/duration use the hardware parameter sweep path. All three AWG/RF pairs, raw AWG, IIR, area/reset or bypass, v5 delay/sum and final register slices are checked; Square cases retain the original independent Square oracle. Matrix targets follow the existing constant quantized increment policy; PASS means that policy matches the independent oracle, not that ideal analog voltages are free of quantization error.

The +100ns variant is authorized diagnostic coverage of matrix/sweep behavior. Its saved GUI input differs from the rejected original only in the three RF base-delay values. It does not turn the original exact-start request into a PASS.

Stable provenance is rechecked against prepared source hashes and exact RTL/PMEM/DMEM fingerprint. The inherited result also includes hashes of live controller/status files observed at individual case end; those temporal entries are preserved and are not presented as final source gates.

[Machine-readable results, original rejections, all paths and SHA256](result.json) · [Actual matrix dialog](matrix_v5_actual_dialog.png) · [Actual final v5 DAC trace, all three pairs](matrix_v5_actual_trace_v2.png)

No board analog measurement, ADC/FIR arithmetic validation, synthesis, upload or firmware replacement. DDS area/clipping after AWG IIR remains outside existing DC area compensation.
