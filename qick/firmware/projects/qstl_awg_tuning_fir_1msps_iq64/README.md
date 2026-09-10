# 1 MSPS signed-int64 IQ capture

This project keeps the QICK readout's 300 MSPS signed-int16 I/Q input and the
three original FIR coefficient sets. It removes no bits between those FIRs.
The additional 50 kSPS FIR/notch path is absent. Triggering does not reset FIR
history or decimation phase.

## Integer arithmetic and storage

| Boundary | Signed bits per component | Removed bits |
| --- | ---: | ---: |
| QICK output | 16 | Upstream QICK behavior is unchanged |
| FIR 0, /10 | 34 | 0 |
| FIR 1, /10 | 51 | 0 |
| FIR 2, /3 | 69 | 0 |
| Final DDR format | 64 | 5, rounded once, ties away from zero |

All values in the FIR datapath and DDR are integers. Coefficients are the
existing signed 18-bit integer coefficients. Each coefficient set has a scale
of 2^17. The final stored integer therefore has an overall scale of 2^46 after
the final divide by 32. To display the result in the old input-code units,
multiply a copy by 2^-46. This conversion must never replace the raw int64 data.

The final FIR uses a 69-bit accumulator to satisfy the conservative stage-wise
bounds below. Even the full-scale DC result exceeds signed-int64 range, so
storing every possible exact result in 64 bits is impossible. This design
preserves all intermediate bits and applies only the final five-bit reduction. Its error is
at most 2^-47 of one input code. Coefficient quantization, filtering response,
and quantization already inside QICK are separate effects.

The actual coefficient L1 norms prove maximum absolute stage values of
5,429,395,456; 984,881,476,927,488; and 258,403,353,101,465,026,560 for arbitrary
signed-int16 input. These fit the stated widths, including transients and
full-scale negative input. Final signed-int64 storage cannot overflow under
this bound.

## DDR and firmware identification

`axis_buffer_ddr_sample_v3` stores `{Q[63:0], I[63:0]}` per 128-bit sample.
Two consecutive IQ samples form each 256-bit DDR write, first sample in the
low 128 bits. Each trigger's last partial word is zero-padded. An N-sample
capture occupies `ceil(N/2)*32` bytes, about 16 MB/s for long 1 MSPS captures.

The V2 capture controls, clock-domain crossing and timestamp queue are retained.
V3 adds read-only AXI-Lite format registers:

| Word index | Byte offset | Value |
| ---: | ---: | --- |
| 10 | 0x28 | 0x5149434b, format magic |
| 11 | 0x2c | 1, format version |
| 12 | 0x30 | 64, signed component width |
| 13 | 0x34 | 46, integer scale exponent |

HWH parameters describe the same format. Software checks the loaded register
values against the HWH before capture and readback. Old IP names remain bound
to their old drivers and signed-int16 layout. Use matching BIT and HWH files.

## Software and deployment files

Use this project's `bitstream.bit` and `bitstream.hwh` together. The generated
`bitstream.xsa` contains the hardware platform, and `build_manifest.json`
records the artifact hashes and matching source-file hashes. Final timing and
test results are documented in `VALIDATION.md` and `validation_reports/`.

The QICK Python changes are in this repository's `qick/qick_lib/qick/`.
Update that library on the QICK board/server before loading the new firmware.
The matching client changes are in the separate `PulseGenerator` repository,
under `DCWaveformGeneratorGUI/`; its `FIR_DDR_IQ64.md` describes raw data,
database reload and compatibility. Updating only the GUI cannot add the V3
driver to an older board-side QICK installation.

The updated driver and GUI also support the previous int16 firmware paths.
Format detection uses IP identity, HWH parameters and V3 hardware registers;
it does not depend on a manually selected GUI mode or a filename. No board
deployment is performed by the build or validation scripts.

## Timing

The input clock is 300 MHz. FIR group delay is 8677 source cycles. The new
registered arithmetic and final formatter add 35 source cycles relative to
the decimation sample index; the nominal delay setting is therefore 8712
cycles (29.04 us). Capture selects the first 1 MSPS output at or after the
trigger deadline. Continuous phase adds up to one output sample period of
selection uncertainty; trigger synchronizer latency is separate.

## Reproduce validation and build

1. Run `../../ip/axis_fir_decim_300to1_v2/scripts/verify_full_precision.py`
   with Python, NumPy and Matplotlib to produce exact integer vectors and plots.
2. Run Vivado 2023.1 in batch mode with `run_xsim.tcl`, passing a fresh short
   output directory. It checks all stage bits, final int64, reset, valid gaps,
   DDR packing and the real FIR/DDR trigger path.
3. Run `build_vivado_2023_1_run5.tcl` with a fresh short output directory. Review
   `build_result.txt` and the post-route timing reports before using artifacts.

The low-signal vectors are synthetic post-QICK int16 data, including adjacent
integer-code sequences with sub-LSB means. The dBm labels use nominal I
amplitude, with 0 dBm mapping to 32767 peak I codes and Q = -I/10. They are
not calibrated total RF power or an RF/ADC simulation.
Already-zero QICK output contains no signal for these FIRs to recover.
