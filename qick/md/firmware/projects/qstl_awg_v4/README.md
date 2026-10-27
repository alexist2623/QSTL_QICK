# AWG Tuning v4

New Vivado 2023.1 project, based on the timing-closed v3 sources. Generated
projects, IP packages, simulation libraries and run files live outside Git.
`bd_2023-1.tcl`, `timing.xdc` and `ios.xdc` are exact v3 copies. The separate
`connect_output_sum.tcl` adds the v4 topology after the baseline BD is created.

| DDS | AWG | Existing physical AWG DAC |
| --- | --- | --- |
| RF 1 / gen 0 / IP 0 | AWG 1 / gen 1 / IP 4 | DAC 10 |
| RF 2 / gen 2 / IP 1 | AWG 2 / gen 3 / IP 5 | DAC 11 |
| RF 3 / gen 4 / IP 3 | AWG 3 / gen 5 / IP 6 | DAC 12 |

The sum follows the unchanged AWG DC-area/IIR chain. Each of 16 lanes adds
signed 16-bit samples into 17 bits, clamps to [-32768, 32764], and rounds once
to MSB-aligned signed 14-bit DAC codes (nearest, ties toward positive infinity).
Two registers are used on both the sum path and the remaining four AWG paths.
The former RF 1/2/3 DAC inputs output zero. RF 4 and Square Wave retain their
original connections. No original generator arithmetic or XDC is changed.

Both streams use a common 300 MHz clock. Their generator pipelines differ by
13 clocks. v4-aware software schedules RF commands earlier so the requested
waveforms meet at the sum input. AWG metadata is 18 clocks and RF metadata is
31 clocks; both omit the common command-routing/output-slice delay. The initial
actual GUI/RTL probe confirmed equal first-sample clocks for all three pairs.
The extended batch checks every shot and requested RF offset. Shared-port
commands less than three clocks apart are rejected instead of silently shifted.

The shared DAC requires Nyquist zone 1 and zero mixer frequency. The DDS gain
is a raw code referred to the AWG physical output. Calibration, attenuation and
filter settings for the old dedicated RF connector cannot be used here. The
AWG area engine still compensates AWG pre-IIR area only; added DDS area and
distortion from final clipping are not covered. Existing SET sweep rounding
and analog bandwidth/transfer characteristics have not been changed.

## Build and publication

`build_vivado_2023_1.tcl BUILD prepare` creates a fresh BD project without
synthesis. A normal build requires the current functional evidence gate.
The full build uses jobs=4, general.maxThreads=5 and the previous strategies.
`publish_build.py BUILD` checks functional hashes, generated RTL, topology,
setup/hold/pulse-width/bus-skew closure, and matching XSA members before writing
v4 firmware here. v3 firmware is retained. The 2026-10-14 publication is complete: 
setup WNS +0.002841 ns, hold WHS +0.009116 ns, pulse-width failures 0 and
bus-skew 14/14 MET. Use the matching `bitstream.bit` and `bitstream.hwh` in
this directory; `bitstream.xsa` is the common source archive.

Progress and evidence: `analysis_results/awg_tuning_v4/` in the QSTL_QICK repo.

## Final software integration

Both repositories use their existing `awg_tuning_v4` branch. In the GUI,
RFDC DAC IDs 10/11/12 are front-panel DAC4/5/6. Each lists both its RF and AWG
generator; the output summary identifies the sum. The v4 front-panel settings
use NQZ 1, attenuation 0 and bypass filter. The Python driver uses the HWH
pairing for shared DAC current readback/scaling; dedicated RF outputs keep
their previous read-only current behavior. No RF connector power calibration
is transferred to the shared AWG output.

Post-publication checks: 274 software tests passed; all five actual GUI compiler
PMEM/DMEM outputs are byte-identical to the completed RTL inputs. Only
`qick_front_panel.py` and `qick/dac_current.py` changed after publication.
The immutable build manifest/gate describe build-time sources. Current software
is separately bound by `analysis_results/awg_tuning_v4/final_integration_manifest.json`;
run `python analysis_results/awg_tuning_v4/finalize_integration.py` from the QICK
repository to recheck those artifacts, source hashes and equivalence evidence.
Do not rewrite the original build gate to make post-build sources appear simulated.
No on-board download or analog measurement was performed.
