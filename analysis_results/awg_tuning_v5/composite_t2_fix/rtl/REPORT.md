# Composite T2 / named tau: fresh GUI-to-RTL results

PASS. Six newly compiled tau x pi coordinates plus one Hahn-to-Custom named-amplitude/phase case executed in the existing v4 real tProcessor/TMUX/DDS/AWG/output-sum RTL. These are seven new simulation runs, not reused simulation PASS, and are not v5 synthesis results.

Input path: actual MainWindow settings -> Run Experiment arguments -> existing runtime host-coordinate resolver -> QICK PMEM/DMEM. The executor is replaced only at the board-I/O boundary with real local compilation. No board connection or output was performed.

| tau (us) | pi (us) | pi/2 (us) | Repetitions | RF paths checked | Commands | Result |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 0.2 | 0.1 | 2 | 3 | 77 | PASS |
| 1 | 0.4 | 0.2 | 2 | 3 | 77 | PASS |
| 2 | 0.2 | 0.1 | 2 | 3 | 77 | PASS |
| 2 | 0.4 | 0.2 | 2 | 3 | 77 | PASS |
| 3 | 0.2 | 0.1 | 2 | 3 | 77 | PASS |
| 3 | 0.4 | 0.2 | 2 | 3 | 77 | PASS |

Additional actual GUI Hahn echo -> Custom case: tau total=4 us (2 us delay on each side), pi=.4 us, enabled pi/2=.2 us. Three RF paths x two repetitions passed. Endpoints use a0=1500 and p0=0 degrees; the body uses a1=750 and p1=90 degrees. Named table references remain independent after GUI preset conversion.

- 126 actual DDS bursts: every output width and relative onset matched the requested event timing exactly in fabric clocks.
- The two delays share tau. RF generator 0 sweeps tau=1/2/3 us and pi=.2/.4 us. The other two summed RF paths keep tau=1 us and pi=.2 us and exercise the same enabled endpoint sequence.
- All tProcessor command values and times match the instruction-model oracle; one constant testbench origin offset is removed. No scheduling tolerance was relaxed.
- All three 16-lane output-sum saturation oracles passed. All three AWG DC-area engines completed both repetitions with residual area zero and cleared IIR history.
- Independent fits of all actual DDS samples verify the requested carrier frequency, gain and relative phase offsets. Bounds are <2 signed DAC codes in fitted amplitude, <1.2 code RMS carrier residual, and <0.05 degree relative phase error. These account for integer DDS/multiply quantization; command timing, burst widths and onsets still require exact clock equality.
- Final-source recompilation produced byte-identical PMEM, DMEM, assembly and expected commands plus identical emitted RF events for all six original cases. Added/default serialization fields are itemized separately; see final_source_input_equivalence_named.json. Previous source proofs are preserved.
- Fresh v4 RTL was elaborated in an isolated copied simulation library. Existing v5 replay/build workflows and their libraries were not changed.

Calibration: actual GUI Hahn-to-Custom settings with named dBm amplitudes were rejected as expected by all three v4 summed-output production guards and by the actual runtime host loop. No calibration RTL case was run on those outputs, and no guard was bypassed. Ordinary RF software/compiler/preview tests separately use a synthetic known database: -30/-10 dBm at 180 MHz resolve to exactly gain100/1000. This is validation of software calibration conversion, not measured board power.

Initial preparation evidence: prepare_1.log/a5t2gui1 retains an over-broad dataclass-equality assertion failure (inactive delay gain normalized to zero and inactive Custom template duration choice normalized to the existing pi parameter), followed by Qt teardown access violation. Preparation 2 compares emitted RF events and both hardware/software axes exactly, records gui_normalization.json, and exits zero. No waveform/sweep tolerance was weakened.

Scope: real digital RTL checks only. These checks validate command timing and RF pulse widths/relative spacing in the existing v4 implementation; they do not claim the separate v5 absolute AWG/DDS delay change or synthesis is complete. Board analog measurement and ADC/FIR arithmetic are not tested. The sum occurs after AWG IIR; added DDS area and clipping are not covered by AWG DC-area compensation.

[Actual tau/pi RF waveform](t2_tau_actual_rtl.png) | [Named amplitude/phase RF waveform](named_hahn_actual_rtl.png) | [Execution status](status.json) | [Final source/input proof](final_source_input_equivalence_named.json) | [DDS carrier checks](carrier_checks.json) | [Expected calibration guard](calibration_guard.json)
