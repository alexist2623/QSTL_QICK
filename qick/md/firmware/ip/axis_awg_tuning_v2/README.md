# AWG tuning v2

V2 extends the realtime RAMP step from signed 24-bit Q16 to signed 32-bit
Q18. It is a distinct `QICK:QICK:axis_awg_tuning_v2:1.0` IP; v1 is retained.
The five 32-bit tProcessor words and existing TMUX routes are unchanged.

| Command bits | Field |
| --- | --- |
| 31:0 | Signed integer target |
| 63:32 | Reserved; the ramp starts from the current value |
| 86:64 | Scalar sample count, unsigned 23 bits; zero means one sample |
| 127:96 | Signed 32-bit step with 18 fractional bits |
| 145:144 | NOP / SET / RAMP / IDLE |
| 146 | SET hold-zero; RC enable for RC configuration |
| 147 | RC history reset for RC configuration |
| 149 | RC configuration marker (IDLE opcode) |
| 159:152 | TMUX destination |

`step / 2**18` is the increment between adjacent scalar DAC samples, measured
in signed 16-bit transport codes. The effective DAC resolution remains 14 bits:
codes -32768 through 32764 in multiples of four. The representable increment
is -8192 through 8192 - 2**-18 transport codes/sample.

At 300 MHz, one fabric word contains 16 samples at 4.8 GSPS. A one-word ramp
has 15 sample intervals. A full-scale ramp needs 65532/15 = 4368.8 codes/sample,
so both full-scale directions fit. Python computes the signed step with
truncation toward zero; the final sample is explicitly set to the target.
The public Python `duration` remains fabric clocks; the command contains 16
times that many scalar samples. No runtime FPGA division is introduced.

The v1 DSP multiplier cannot accept a signed 32-bit operand. V2 implements
the small compile-time lane constants with full-width shift/add logic and an
output register, retaining the DSP48E2 48-bit lane/base additions. With
`EXTRA_Y_PIPE_STAGES=3`, RAMP startup is seven fabric clocks; RC processing or
bypass adds eleven clocks. SET and RAMP retain their distinct startup timing.
Commands arriving while a ramp is busy are still dropped; the compiler reserves
startup, ramp duration and the existing guard interval.

The QICK driver and GUI select width/precision using the actual IP identity
and HWH parameters. V1 remains Q16/24-bit. V2 sweep copies retain the entire
32-bit word. Large axis rewind/add constants are split into encodable signed
31-bit immediates; the final addition is modulo 2**32. No second data register
or 33rd-bit carry is needed to store a v2 step.

Validation entry points:

- `validation/run.tcl`: production wrapper, full-scale one-clock ramps in both
  directions, signed step limits, random ramps, endpoint hold and RC bypass delay.
- `../rc_precomp_validation/verify_gui_rtl.py --awg-v2`: real GUI export,
  instruction memory, tProcessor, TMUX, slices and two production AWG v2 IPs.
  The independent raw checker compares every lane to the received commands;
  existing RC oracles check every compensated sample. ARM and RFDC are excluded.
- `--v2-fixture fast --grid-count 20 --no-aux`: two-DAC wide-step 20x20 sweep.
- `--v2-fixture stability --grid-count 20 --no-aux --repeat-reset`: actual
  Stability tab sequence builder, two-DAC scan with DC and RC compensation.

Ramp fractional precision does not change DAC resolution. The GUI now rounds
each requested voltage point to the nearest DAC code and keeps its RAMP and DC
compensation values consistent. Exact arithmetic progressions use register
adds; other payloads use tables over their dependent axes, read by tProcessor
hardware loops. Independent two-DAC grids use O(Nx + Ny) data. Coupled fields
need joint rows and are rejected before execution if DMEM is insufficient.
Reports separate unavoidable DAC rounding from command/sample disagreements.
