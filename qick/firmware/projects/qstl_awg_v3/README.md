# qstl_awg_v3

Source project derived from the latest timing-closed `qstl_awg_v2` BD. Seven AWG
instances become `axis_awg_tuning_v3` with 48-bit pre-IIR shot area compensation.
The RF, SquarePulse, FIR IQ64, DDR, pins, and clock topology remain those of the
source project. The AWG and tProcessor fabric clock is 300 MHz (16 samples/word,
4.8 GSPS). Host AXI clocks are separate.

The full `F:/Vivado_Output/a3full7` build completed at **2026-10-07 17:34:58 PDT**.
The validated [BIT](bitstream.bit), [HWH](bitstream.hwh), and [XSA](bitstream.xsa)
are published in this directory. `publish_build.py` passed the current source and
functional-evidence checks, full setup/hold/pulse-width/bus-skew closure, HWH
parameters, and generated-RTL checks, then extracted BIT/HWH from that same
successful XSA. The [build manifest](build_manifest.json) records their hashes
and provenance. See the [final report](../../../../analysis_results/awg_tuning_v3/FINAL_REPORT.md).
The historical 32/48/64-bit comparison selected 48 bits. Publication now requires
current selected-48 RC evidence, the ordinary software/48-bit RTL regressions,
and all four 100-point system RTL results, including unmodified GUI widget -> PMEM/DMEM
equality in both DC modes. A separate reversed-axis stress test changes the
axis order after GUI input and is explicitly distinguished from those runs.
Each system result includes hashes of its explicit repository RTL sources,
verified against the simulator's combined source/PMEM/DMEM fingerprint. The
publisher rejects evidence if a production source has since changed or is absent.
The HWH check enforces the same 300 MHz clock net for AWG, tProcessor, FIR, and
the DDR source stream; the DDR AXI memory clock remains separate.

Build with Vivado 2023.1 using `build_vivado_2023_1.tcl` and a fresh short output
directory outside both Git repositories. The current host uses
`F:/Xilinx/Vivado/2023.1`, **4 concurrent jobs** and the previous successful build's
**`general.maxThreads=5`**. Each full build creates a new project outside Git;
it does not reuse an earlier build's `.xpr`. The recovery below reopened only
this newly created `a3full7` project.
The original successful-v2 XDC contents are copied byte-for-byte into the build
directory, actually used by the project, and checked against pinned hashes.
No clock-group or false-path constraints are removed.
Run the selected area engine's RTL and OOC timing checks first. The final timing
decision belongs to the complete placed-and-routed project: a virtual OOC input
boundary hold estimate is not a full-system timing result. The current pipeline
passed internal OOC setup/hold and the completed full-project timing checks.

All four GUI/compiler-to-RTL cases, the ordinary
986 software tests, 48-bit unit/legacy-output checks, and the 200-shot selected-48
RC test have passed. Both RC error plots were reviewed; current functional
evidence and source hashes passed the publication gate. After all verification
writers exited, the fresh `F:/Vivado_Output/a3full7` full build started at
12:04:02 PDT. Project creation, actual XDC references/hashes, jobs=4 and
maxThreads=5 were confirmed. Synthesis, implementation, bitstream generation,
and publication are complete. No commit or push was performed.

The initial synthesis attempt exited at 12:42 after a FIR memory allocation
failure and a SmartConnect internal Tcl abort. Failure artifacts were archived.
Both failed IP runs passed on retry with unchanged RTL/XDC, jobs=4 and
maxThreads=5; 128 completed IP runs were retained. The top-level synthesis then
resumed with all 130 IP results complete and finished successfully, followed by
placement, routing, and bitstream generation. Earlier a3full1/a3full3 timing
failures remain preserved and were not published.

Final routed setup WNS is **+0.011847 ns** and hold WHS is **+0.009619 ns**;
TNS/THS and all setup/hold/pulse-width failing endpoint counts are zero. All 14
bus-skew checks pass, with minimum slack **+2.429 ns**. All 577,428 routable nets
are routed, with zero routing errors. There are zero no-clock pins and zero
unconstrained internal endpoints.

These results establish closure under the preserved original constraints.
External I/O delay constraints remain absent for 28 ports; CDC/synchronizer,
overridden max-delay, and asynchronous-reset methodology warnings remain.
DRC and methodology reports contain warnings/advisories but no Critical/Error
violations. This is not a complete board-level I/O or CDC sign-off. The system
DDR test uses a timestamp stream, not new ADC/FIR arithmetic or board analog
measurements. The existing integer SET sweep increments and their ideal-target
voltage quantization error remain unchanged.
