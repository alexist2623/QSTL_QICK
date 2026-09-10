# IQ64 validation

## Arithmetic and RTL

The exact reference uses Python arbitrary-precision integers and the actual
383 coefficients from the packaged FIR source. No float64/int64 accumulator
is used for the reference convolution.

- 330,000 synthetic signed-int16 IQ inputs: measurement-scale DC, sub-LSB
  integer-code densities, assumed -60/-70/-80/-90 dBm levels, random full-range
  codes, positive/negative full scale, transitions and zeros.
- Repeated after reset with valid gaps: 660,000 IQ inputs total.
- Every stage-0 (34-bit), stage-1 (51-bit), stage-2 (69-bit), and stored
  signed-int64 IQ output matched the exact reference bit for bit.
- No intermediate bit removal, saturation or wrap. Final divide-by-32 rounding
  error was at most 16 / 2^51 = 7.105427357601002e-15 input codes.
- The RTL output latency relative to its selected input index was 35 source
  clocks, both with and without valid gaps.
- Vector-loading checks explicitly reject missing/unknown data. The final
  regression had no vector-loading warnings.

| Post-QICK input mean, I/Q | Legacy per-FIR int16 output, I/Q | New settled output in input-code units, I/Q |
| --- | --- | --- |
| -33 / 3 | -33 / 3 | -32.999999946 / 2.999999995 |
| -0.33 / 0.03 | 0 / 0 | -0.329999985 / 0.029999362 |
| -0.0033 / 0.0003 | 0 / 0 | -0.003299965 / 0.000268963 |

Differences between the requested density mean and the exact FIR response
include finite-length integer density and filter response. They are not the
final integer-format rounding error. These are post-QICK simulation inputs,
not measured RF traces or a calibrated 190 MHz ADC/DDC simulation.
The dBm cases use nominal I amplitude (32767 codes at 0 dBm) and Q = -I/10;
the low-power plot shows that weaker Q component, not total IQ magnitude.

Plots and machine-readable results are in
`../../ip/axis_fir_decim_300to1_v2/vectors/`.

## DDR integration

- Exact high, low and sign bits in both 64-bit lanes survived AXI writes.
- 1, 2 and 13 samples per trigger, two shots, automatic/explicit strides,
  nonzero byte addresses, final-word zero padding, rearm, and AXI stalls passed.
- Read-only magic/version/width/scale registers matched the new format.
- Real FIR -> trigger synchronizer -> DDR integration passed with four
  25-us-spaced triggers and 13 samples/trigger, at delay 0 and 8712 cycles.
  All 128 bits were compared against independently selected FIR outputs.
- FIR output spacing remained 300 source clocks across triggers and rearming.

The 40 kHz figure in that integration test is the **trigger repetition rate**.
It is not the RF input or readout frequency.

Final RTL run: `C:/JeonghyunPark/Workspace/Vivado_Output/q64sim4`.

## Python and GUI

- 31 QICK driver tests passed, covering legacy paths plus raw signed-int64
  decoding, stride/padding, capacity checks, invalid formats and delay metadata.
- The GUI regression run passed 147 tests with two pre-existing failures
  excluded; the same two failures were reproduced from the unmodified GUI HEAD.
  They concern QCS/front-panel routing defaults and are unrelated to IQ64.
  The existing failures are
  `test_calibration_front_panel_path_is_independent_from_other_tabs` and
  `test_gui_has_independent_sparameter_tab_gain_limit_and_settings_round_trip`.
- Four analysis/calibration suites passed 74 tests.
- The final focused IQ64 suite passed 9 tests, including exact database
  round trips above 2^53, preserved low bits while averaging shots, S-parameter
  reload/scaling, and chunked AWG readback with nonzero addresses.
- The generated HWH was traced through the QICK driver into the GUI. It reports
  1 MSPS, signed-int64 IQ, continuous phase, and 8712 source-clock cycles
  (29.04 us) of programmed FPGA delay.
- The actual GUI memory widget reported 13 IQ samples as 208 valid bytes plus
  16 padding bytes = 224 bytes, and displayed the int64 format in its status.

GUI source: `C:/JeonghyunPark/Workspace/PulseGenerator/DCWaveformGeneratorGUI`.
Runtime used for tests: QCoDeS 0.58.0, PyQt5 5.15.11; isolated test dependencies
under the QSTL workspace's `tmp/iq64_gui_python_deps`.

## FPGA implementation

Build directory: `C:/JeonghyunPark/Workspace/Vivado_Output/q64a`.
Vivado 2023.1, ZCU216 xczu49dr-ffvf1760-2-e, five jobs/threads.

All 130 IP synthesis runs completed. The new FIR IP synthesis used 53,528 LUTs,
96,174 registers and 1,150 DSP48E2 blocks. Full-design synthesis also completed:
200,135 LUTs, 303,584 registers, 442.5 BRAM tiles, and 2,386 DSP48E2 blocks.
The pre-route setup slack was +0.497 ns; this is not a routed timing result.

The first implementation attempt stopped inside Vivado's DDR4 PHY helper
because it could not read the installed `unimacro_verilog.tcl` runtime file.
The exact generated PHY was successfully synthesized separately with one
thread and the same parameters/pin constraints. Its result was placed in
the build's IP cache (ID `76c734d762a38b9c`). The implementation retry confirmed
that it loaded this cached PHY. No FIR or DDR arithmetic change was needed.

Implementation and bitstream generation completed successfully on 2026-09-10.
The routed timing report states that all user-specified timing constraints
are met. Global margins below use the completed run's exact reported values;
per-clock margins use the timing report's displayed precision.

| Check | Result |
| --- | --- |
| Whole-design setup WNS / TNS | +0.019190 ns / 0 ns |
| Whole-design hold WHS / THS | +0.009340 ns / 0 ns |
| 300 MHz `clk_104_pl` setup / hold | +0.071 ns / +0.010 ns |
| Processing-clock constraint | 3.333 ns (slightly stricter than exactly 300 MHz) |
| Setup / hold / pulse-width failing endpoints | 0 / 0 / 0 |
| Registers/latches without a clock | 0 |
| Unconstrained internal endpoints | 0 |
| Fully routed / routable nets | 466,212 / 466,212 |
| Routing errors | 0 |
| Bus-skew checks | 14 met; minimum reported slack +2.373 ns |
| Post-route DRC | No errors; warnings/advisories remain |

Post-route utilization is 179,754 LUTs (42.27%), 295,228 registers (34.71%),
442.5 BRAM tiles (40.97%), and 2,386 DSP48E2 blocks (55.85%). The detailed
timing report includes the new FIR's stage-1 valid to stage-2 history-enable
paths under the 3.333 ns processing clock, confirming that this path is timed.

The inherited external-I/O delay warnings remain: four inputs and 24 outputs
have no explicit I/O delay. This is the same as the previous 1 MSPS build.
The pre-existing critical-warning messages concerning unused clock/port
constraints also matched the previous build. The new internal FIR path is
clocked and constrained; these checks do not establish external-board I/O
timing or replace a physical-board test.

The final [BIT](bitstream.bit), [HWH](bitstream.hwh), and [XSA](bitstream.xsa)
are stored in this project directory. Artifact and source hashes are recorded
in [build_manifest.json](build_manifest.json). Both standalone files were
extracted directly from the XSA: `bitstream.bit` and the top-level `d_1.hwh`
(renamed to `bitstream.hwh`). They match those archive members byte for byte;
Git newline conversion is disabled for the firmware artifacts. Source hashes
record the original build-machine bytes, which may differ after Git text
newline conversion. Timing, route, DRC, bus-skew and
software/RTL test reports are archived under `validation_reports/`.

The exported HWH also passed the QICK-driver-to-GUI format check: signed int64
I/Q, 1 MSPS, continuous FIR phase, and 8712 source-clock cycles (29.04 us)
of FPGA delay. The updated board/server QICK library and client GUI must be
installed together for the new format; both retain the legacy int16 paths.

No physical-board capture or deployment has been performed.
