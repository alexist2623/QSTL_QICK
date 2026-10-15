# Current production GUI -> candidate v5 RTL: composite 7 cases

PASS. Seven newly compiled inputs and seven fresh actual RTL simulations completed. Prior v4 simulation results were not reused as current PASS. Production GUI, Python, RTL, XDC, firmware and board state were not changed.

Input flow: actual MainWindow settings -> normal Run Experiment arguments -> normal runtime host-coordinate resolver -> real QICK compiler PMEM/DMEM -> actual tProcessor/TMUX/DDS/AWG/v5 sum RTL. Only the board-I/O boundary was replaced by local compilation. The prior six tau x pi host coordinates and Hahn-to-Custom named-amplitude/phase settings were retained.

| Case | GUI setting | tau (us) | pi (us) | Commands | DDS bursts | Result |
|---:|---|---:|---:|---:|---:|---|
| 1 | custom_sweep | 1 | 0.2 | 77 | 18 | PASS |
| 2 | custom_sweep | 1 | 0.4 | 77 | 18 | PASS |
| 3 | custom_sweep | 2 | 0.2 | 77 | 18 | PASS |
| 4 | custom_sweep | 2 | 0.4 | 77 | 18 | PASS |
| 5 | custom_sweep | 3 | 0.2 | 77 | 18 | PASS |
| 6 | custom_sweep | 3 | 0.4 | 77 | 18 | PASS |
| 7 | hahn_manual | 4 | 0.4 | 77 | 18 | PASS |

- Six Custom points sweep RF generator 0: tau=1/2/3 us x pi=.2/.4 us. Other two RF paths retain tau=1 us, pi=.2 us. Enabled endpoint pi/2 duration is half the chosen pi duration.
- Hahn -> Custom is exercised through the actual preset-selection control; emitted events are unchanged by conversion. Total tau=4 us gives 2 us on each side. Named endpoints use a0=1500/p0=0 degrees and the body a1=750/p1=90 degrees on all three paths.
- Existing outer HOLD-relative RF offset is +100 ns. It was already present in the original seven fixtures and was retained; no rejection workaround or input-shift variant was needed. Exact simultaneous AWG/RF commands are outside this request.
- All 126 actual RF bursts passed exact fabric-clock width and relative-onset checks. Every emitted command word and timestamp matched the independent instruction-model expectation after one constant testbench origin offset.
- The production driver reads the actual candidate HWH, requiring v2 sum, AWG delay13 and common pipeline2. Both native latencies are31. Actual RF command-to-trace timing is checked separately for every burst.
- Independent sum lane and final-output checks passed. 9,905,616 final DAC sample checks use saturate/round(AWG[c-25]+RF[c-12]); the separate RTL sum oracle maintains its own 13-entry AWG history.
- Three DC-area engines completed two repetitions in every case, with zero residual area and both IIR/reset checks passing.
- Actual DDS frequency/gain/relative-phase fits passed: max gain error 0.148000 codes (<2), max carrier RMS 0.545345 codes (<1.2), max relative-phase error 0.005699 degrees (<.05). Phase command words are also checked exactly. Carrier-fit quantization bounds do not relax timing.
- No preparation, compile, elaboration, simulation or checker failure occurred; no retries were performed. A dedicated copied simulation library was used, with at most one xsim process from this suite.
- All 169 captured production Python files, current RTL inputs and newly generated PMEM/DMEM match their recorded hashes after execution. Candidate HWH SHA256: `52d16d740d227698e4f07f20113d24aa866531d8cb161e54ef899b8c67f54080`.

Scope: digital simulation only. No new synthesis, board analog measurement, ADC/FIR arithmetic verification, calibration power measurement or firmware deployment. The DDS sum is after AWG IIR; additional DDS area and clipping are not compensated by AWG DC-area correction.

[Actual RTL waveforms](composite7_actual_v5_rtl.png) | [Execution status](status.json) | [Source/input/evidence hashes](proof_hashes.json) | [Adapter provenance](adapter_provenance.json)
