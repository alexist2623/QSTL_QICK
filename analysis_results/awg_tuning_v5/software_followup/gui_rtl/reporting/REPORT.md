# Fresh v5 GUI to RTL followup validation

Supported test cases passed. Exact zero-offset HOLD SET + RF remains unsupported on the existing shared tProcessor port. No production spacing guard was relaxed.

| Group | Fresh execution result |
|---|---|
| Actual MainWindow → PMEM/DMEM → v5 RTL | 7 cases, 44 shots × 3 AWG/RF pairs; command and timing mismatches 0 |
| Final digital output oracle | 11,821,824 lane/sample checks; errors 0 |
| Fine actual GUI → AXI/AXIS BRAM load → SG-v6 → v5 sum | 5 cases, 1,536 RF bursts; sample widths, gain/frequency/phase, outside-window zero, command/timing and sum-lane checks PASS |
| Zero-offset real GUI | 8 expected rejections; unchanged guard |
| Raw identical timestamp diagnostic | All 3 ports × both orders: second command 3 clocks late; inferred component skew ±3 clocks = ±10ns |
| Additional source/input audit | 5 cases: all requested resolved fields, exact PMEM/DMEM/envelope recompile, actual HWH/full configured soccfg/source hashes PASS; quantized request/GUI delay differences 0 |

The seven supported cases are first HOLD, second HOLD, two-dimensional HOLD duration sweep with fixed-time compensation, HOLD duration sweep with fixed-voltage compensation, RF duration with fixed HOLD, RF duration extending HOLD, and RC-only. All three AWG/RF pairs and both DDR policies represented by the fixtures are checked. First/second HOLD use 10us RAMP → 10us HOLD → 10us RAMP → 10us HOLD, with explicit RF +100ns offset and 9.9us width inside the selected HOLD.

Fine cases exercise each of the three channels through 81..112 samples at 0/190MHz (all 16 remainders and the 95/96 split), plus every duration 1..31 at 0MHz and at 190MHz/37deg. Other pairs remain active. The carrier short-pulse oracle uses a separately observed long reference, not a fit to each short pulse.

The original suite2 status remains failed because its first fixed-voltage attempt detected a validation-harness source-hash change before simulation. The fresh fixed-voltage retry re-prepared identical PMEM/DMEM/GUI input bytes and passed. The only differing prior source hash was the validation-only raw diagnostic reporting file. Original failures and logs are preserved. The first suite lacked wrapper_path.txt before simulation and is also preserved.

The additional audit first terminated with an empty log (cause unproven); its logged retry exposed an incorrect nearest-round delay comparison. The corrected new audit uses the production ceil rule and the exact nine-decimal GUI precision bound, keeps all earlier artifacts, and reports zero actual quantized timing differences.

See [TIMING_LIMIT.md](TIMING_LIMIT.md) for the direct observation versus inferred physical timestamp distinction and the shared-port limitation. `requested_timing_error_cycles=0` is relative to the actual HOLD anchor +100ns, not zero-offset output or an ideal absolute RAMP timeline.

[First/second HOLD digital output](v5_first_second_hold_v3.png) · [1/16/31-sample RF traces](v5_fine_1_16_31.png) · [Machine-readable evidence and exact paths](result.json)

No board access or analog measurement, ADC/FIR arithmetic validation, RTL/XDC edit, new synthesis or deployment was performed. DDS area/clipping after IIR remains outside existing DC area compensation.
