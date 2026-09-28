# QSTL AWG tuning v2 project

Based on `qstl_awg_tuning_fir_1msps_iq64_sq_pulse`, with all seven AWG tuning
generators replaced by `axis_awg_tuning_v2`. The dedicated SquarePulse port,
RF generators, IQ64 FIR/DDR path and external triggers are retained.

## Clocks

The checked-in `pll/LMK04828_300.00.txt` and QICK ZCU216 clock setup use
LMK04828 at a 300 MHz reference. The external CLK104 PL clock is constrained
to 3.333 ns, and Tcl/HWH metadata specify 300000000 Hz. DAC sample rate is
4.8 GSPS with 16 parallel samples/clock. Earlier 400 MHz metadata belonged
to legacy projects and is not used here. Configuration files do not constitute
a live board clock measurement.

## Build and recovery

On the development PC, launch Vivado 2023.1 with its existing license and an
ASCII temporary directory. These environment settings affect only this process:

```powershell
$env:XILINXD_LICENSE_FILE = 'C:/Xilinx/Xilinx.lic'
$env:TEMP = 'C:/VivadoTemp'
$env:TMP = 'C:/VivadoTemp'
& C:/Xilinx/Vivado/2023.1/bin/vivado.bat -mode batch -source build_vivado_2023_1.tcl -tclargs C:/JeonghyunPark/Workspace/Vivado_Output/awg2b
```

Use a fresh output directory for a clean build. `resume_build.tcl` can recover
unfinished runs when the existing XPR is readable and no workers are running.
If generated project metadata is incomplete, regenerate it from the source Tcl.
Do not replace source, BIT/HWH/XSA or an existing published project during recovery.

Run `publish_build.py <build-directory>` only after routed setup, hold,
pulse-width and bus-skew checks pass. Publication extracts BIT and top-level HWH
from the same XSA, validates v2 parameters/clock connections and hashes sources.
Old firmware artifacts are not copied into this project as placeholders.

## Validated build, 2026-09-27

Vivado 2023.1 completed synthesis, placement, routing and bitstream generation
in `C:/JeonghyunPark/Workspace/Vivado_Output/awg2b`. Routed setup WNS is
0.006120 ns and hold WHS is 0.009412 ns. Pulse-width checks and all 14 bus-skew
constraints pass; minimum bus-skew slack is 2.532 ns. No-clock and unconstrained
internal endpoint counts are zero. External I/O delay and methodology warnings
remain documented in `validation_reports`.

`bitstream.bit` and `bitstream.hwh` were extracted from this directory's
`bitstream.xsa`. `build_manifest.json` records their hashes, archive member names,
hardware parameters and the corresponding software source hashes. Seven AWG
ports use signed 32-bit/F18 steps; the SquarePulse, FIR64 and DDR paths retain
their existing interfaces. The Python driver and GUI continue to support v1.

See [the validation report](../../../../analysis_results/awg_tuning_v2/REPORT.md)
for production-RTL sweeps, exact voltage-grid results and recovery checks.
