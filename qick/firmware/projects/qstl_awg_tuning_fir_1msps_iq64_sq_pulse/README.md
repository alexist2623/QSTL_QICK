# 1 MSPS IQ64 with continuous square DDS

This is a separate project copied from `qstl_awg_tuning_fir_1msps_iq64`.
Only its fourth AWG in physical DAC order is replaced:

```
axis_awg_tuning_v1_7 -> axis_square_pulse_v1_0
tProc output 3 -> TMUX 3 destination 1 -> command register slice 23
square output -> register slice 12 -> RFDC s13_axis (physical DAC7)
AXI-Lite base address 0xA0120000
```

The normal QICK generator index is 7. Software detects the IP type and channel
from the loaded firmware. All other AWG/RF paths, the 300 MHz processing clock,
4.8 GSPS DAC sample stream and existing external marker path are retained.
The inherited 1 MSPS full-precision FIR /10, /10, /3 and IQ64 DDR path are
unchanged, including the 8712-cycle (29.04 us) FPGA capture delay setting.
See the base project's README for FIR arithmetic and DDR format details.

The square DDS continuously integrates a 32-bit frequency increment. The MSB
of accumulated phase plus phase offset selects +/-amplitude. Frequency and
amplitude updates preserve accumulated phase. See
`../../ip/axis_square_pulse_v1/README.md` for the command format, fifteen-cycle
pipeline, AXI-Lite mute and testbench.

## External trigger

No additional trigger IP is needed. The existing `axis_set_reg_0` and
`qick_vec2bit_0` expose `SPARE1_1V8` on tProcessor output port 7, bit 6; QICK
reports it as external output pin 0. The GUI can emit start/end markers per
experiment or repetition, with independently configured width. The DDR trigger
uses a different bit on this same port; software merges overlapping pulses.

## Build and use

Use Vivado 2023.1 with the installed ZCU216 board support and a valid synthesis
license. Run `build_vivado_2023_1.tcl` with a fresh short output directory to
avoid Vivado's Windows path-length limits. Set `XILINXD_LICENSE_FILE` if Vivado
does not discover the existing license automatically. Do not reuse an old BIT
or HWH from the base project.

On Windows, use a short ASCII `TEMP`/`TMP` directory. If Vivado's DDR PHY helper
crashes (`Mig 66-119`, `TclStackFree`, or the installed unimacro Tcl read error),
`prepare_ddr_phy_retry.py` accepts the reported helper's `get_cs_ip.tcl` and a
fresh short work directory. Run its generated Tcl with Vivado in that directory
to populate the original project's IP cache using one helper thread. Then run
`resume_implementation.tcl` with the original build directory. IP parameters
and generated pin/timing constraints are preserved. Normal synthesis and
implementation use five threads/jobs.

The published `bitstream.bit` and `bitstream.hwh` must be extracted from this
build's `bitstream.xsa` and used together. The manifest records matching hashes
and build results. `VALIDATION.md` records simulation, implementation timing
and Python/GUI checks. Board programming and analog measurements are separate
from the local build and simulation.

Update `qick/qick_lib` on the board/server and desktop. The command API is
`set_pulse_registers(style='square', freq=FTW, phase=POW, gain=amplitude, ...)`
followed by `pulse()`. `length` only reserves command scheduling time; it does
not stop this autonomous output. Use `soc.stop_square_pulse(ch)` to stop the
tProcessor and mute the generator. A minimal standalone example is
`qick/qick_demos/square_pulse_dds.py`.

The matching GUI changes are in the QICK checkout `PulseGenerator-qick`, on
`codex/rc-precompensation-gui`. The firmware and Python library are on
`QSTL_QICK` branch `codex/rc-precompensation`.
The GUI's `DCWaveformGeneratorGUI/SQUARE_PULSE_DDS.md`
describes hardware sweeps and triggering. The QCS checkout is not part of this
change.

## RC precompensation

All seven AWG Tuning wrappers now contain the selectable high-pass inverse.
SquarePulse uses signed linear increments computed in software. Both paths
include 11 output pipeline clocks even in bypass. HWH reports
`RC_PRECOMP_VERSION=1`, and the drivers expose the corresponding timing.
Tau is supported from 10 us through 1000 ms, with 72-bit internal histories
and no hardware division. See `../../ip/rc_precomp_validation/README.md`.
AWG Tuning and Stability Diagram have independent DC/RC controls. The previous
software RC waveform rewriting path has been removed.
