# RC precompensation and SquarePulse validation

## RC implementation update (2026-09-24)

The current source adds continuous RC precompensation to all seven AWG tuning
outputs and the dedicated SquarePulse output. The former GUI software RC
algorithm is removed. AWG Tuning and Stability Diagram have independent DC
and RC controls, with the existing DC pulse algorithm preserved.

Current RC test evidence, waveform plots and GUI screenshots are in
[`analysis_results/rc_precompensation_v1/REPORT.md`](../../../../analysis_results/rc_precompensation_v1/REPORT.md).
The actual-IP five-tau and rail/bypass/mute tests, two real-tProcessor
10 x 10 x 2 integration tests, 217 GUI tests and 23 library tests pass.
RC and bypass both add 11 clocks; current SquarePulse command latency is
15 clocks. These supersede the original four-clock wrapper timing below.

Full-project synthesis, placement, routing and bitstream generation pass.
The current build (`Vivado_Output/rc1`) has setup WNS **+0.041301 ns** and
hold WHS **+0.009500 ns**, with TNS/THS zero. Pulse-width violations, missing
clocks and unconstrained internal endpoints are zero. All 14 bus-skew
constraints pass (minimum slack +2.705 ns). The separate SquarePulse timing
report has minimum setup slack +0.256 ns.

The current `bitstream.bit` and `bitstream.hwh` were extracted from the same
`bitstream.xsa`. `build_manifest.json` records the member names, SHA-256 hashes,
source hashes, branches and hardware capabilities. It verifies all seven AWG
instances and the SquarePulse instance have `RC_PRECOMP_VERSION=1`, with the
existing 1 MSPS IQ64 FIR/DDR path and 8712-cycle capture correction preserved.

Final utilization: 241289 LUTs (56.74%), 336104 registers (39.52%), and 2576 DSPs
(60.30%). The SquarePulse RC path has no DSP multipliers. The existing timing
constraints were retained. Methodology warning categories/counts match the
previous build; there are no DRC errors.

The historical firmware numbers below describe the previous SquarePulse
build. Its original reports/manifest are preserved in the RC report's
`evidence/pre_rc_baseline` directory. The project's `validation_reports`
now contains the current RC implementation reports.

## Historical SquarePulse validation before RC

## Digital behavior

Vivado 2023.1 XSim completed both self-checking testbenches in
`C:/JeonghyunPark/Workspace/Vivado_Output/sqsim3`. The archived
`validation_reports/square_dds_xsim.log` contains their PASS results.

- The independent scalar phase-accumulator reference matched **361,216 DAC
  samples**, including approximately 40 kHz and 190 MHz, amplitude-only and
  phase-only changes, wraparound, zero frequency, zero amplitude, explicit
  phase clear, reset, mute/re-enable and 2,000 randomized back-to-back commands.
- The wrapper test verified independent AW/W ordering, held read responses,
  read-only identity/status/latency, asynchronous AXI-Lite mute CDC and AXIS
  reset behavior.
- Commands preserve accumulated phase unless bit 129 explicitly requests a
  clear. Command-to-output delay is four 300 MHz fabric clocks, excluding the
  existing command transport, output slice and RFDC.

The new IP's standalone synthesis uses 1,009 LUTs and 955 registers, with zero
DSP and BRAM blocks. Its utilization report is archived with the simulations.

### Additional 500 us period and amplitude regression

`run_500us_xsim.tcl` ran `tb_square_dds_500us.sv` with Vivado 2023.1 XSim.
The log is `validation_reports/square_dds_500us_xsim.log`. This adds a longer
test to the already-published RTL; the synthesizable RTL and bitstream are
unchanged, and both RTL files still match the original build-manifest hashes.

- A requested 500 us period is 2 kHz. At 4.8 GSPS the nearest 32-bit FTW is
  **1790**, giving **2000.480890274 Hz** and a nominal average period of
  **499.879806331 us** (about -0.120194 us, or -0.02404%, from the request).
- Over approximately **6.85 ms**, all **32,880,224 scalar output samples**
  matched an independent scalar phase accumulator, including the four-clock
  command pipeline.
- Peak DAC codes changed through **800, 1920, 320, 4, 32764, 0, 800**.
  Every nonzero level was held for more than two periods and both output
  polarities were observed. Zero amplitude produced zero output; restoring
  amplitude retained the phase accumulated during the zero-output interval.
- A separate output-edge monitor checked **11 complete periods** and **24
  half-periods** across amplitude changes. Observed full-period spacings were
  2,399,423 scalar samples; half-period spacings were 1,199,711 or 1,199,712.
  These fall on the expected sample grid for FTW 1790. Amplitude updates did
  not restart phase or create extra sign transitions.
- The Python/GUI conversion was also checked: `0.002 MHz` produces FTW 1790.
  With an example full-scale setting of 800 mV, requested peak amplitudes of
  0, 1, 10, 20 and 800 mV produce DAC codes 0, 40, 408, 820 and 32764.
  This verifies digital scaling, not measured analog output voltage.

## Python and GUI

Validation uses the local QSTL_QICK library and the QICK GUI checkout
`PulseGenerator-qick`, branch `alexist/feature/50ksps`, based on `efc64e3`.
The separate QCS checkout remains on `farbod/feature/qcs` and has no tracked
changes from this task.

The completed changes are published on separate branches:
`QSTL_QICK:codex/1msps-square-pulse-dds` and
`PulseGenerator:codex/square-pulse-dds-gui`. The original branches remain at
their existing commits.

Completed pytest runs:

- 167 tests: new SquarePulse words/tables and external markers, QCoDeS storage,
  signed-int64 and mean-only persistence, front-panel discovery, sweep plotting,
  and existing AWG hardware sweeps.
- 108 tests: original GUI/CPMG interactions, new tabs/settings/Python export,
  and the pre-existing standalone square-wave tab. Process exit code was zero.
  One existing pyqtgraph/NumPy deprecation warning was emitted.
- The driver and old AWG assembler run passed 12 tests. A subsequently added
  standalone-example test also passed.
- Additional focused tests passed for the actual 12-generator/4-readout
  register-layout size, shutdown on capture success/failure, final mute retaining
  the last DDS words, capability discovery, and loading enabled settings onto
  firmware without the new IP.

The hardware-loop reference interpreter verified every command for a 3 x 3 x 4
frequency/amplitude/phase sweep with two repetitions (72 updates), plus final
mute. Growing a phase sweep from 2 to 100 points did not increase instruction
count. Exact words reside in DMEM; the host does not step the sweep. A second
configuration exercises all 12 generators and four readouts with 27 Cartesian
points, three active AWGs, a SquarePulse generator and shared-port markers.

Marker tests cover loop/experiment start and end, identical boundaries,
non-overlap and both overlap directions with ADC trigger pulses. A DDR trigger
whose timestamp changes with a duration sweep retains its width while crossing
the external marker's falling edge. The final acquisition counter is deferred
until the final marker/output epilogue completes.

QCoDeS round trips preserve MHz/mV/degrees coordinates for all three axes.
Full-trace raw int64 values above 2^53 retain low bits exactly. Mean-only mode
does not save full raw traces. Settings JSON, generated Python and the existing
GUI controls were checked. Screenshots were rendered and inspected for the
SquarePulse and Triggering panels.

## Firmware mapping and implementation

The generated HWH confirms the sole AWG replacement at physical DAC7 / RFDC
`s13_axis`, 16 samples per 300 MHz clock, and all seven other AWG tuning blocks.
The inherited FIR output remains 1 MSPS signed-int64 IQ, with the same 8712-cycle
(29.04 us) hardware trigger-delay setting. `publish_build.py` rechecks these
properties before publishing and extracts both standalone files directly from
the same XSA. Git text conversion is disabled for those artifacts.

Vivado 2023.1 completed synthesis, placement, routing, bitstream generation and
XSA export on 2026-09-23. Final routed timing and artifact/source hashes are
recorded in `build_manifest.json` and `validation_reports/`. The timing report
states that all user-specified timing constraints are met.

| Check | Result |
| --- | --- |
| Whole-design setup WNS / TNS | +0.033420 ns / 0 ns |
| Whole-design hold WHS / THS | +0.009511 ns / 0 ns |
| 300 MHz `clk_104_pl` setup / hold | +0.114 ns / +0.010 ns |
| SquarePulse internal register-to-register setup | +0.916 ns |
| Processing-clock constraint | 3.333 ns |
| Setup / hold / pulse-width failing endpoints | 0 / 0 / 0 |
| Registers/latches without a clock | 0 |
| Unconstrained internal endpoints | 0 |
| Fully routed / routable nets | 461,726 / 461,726 |
| Routing errors | 0 |
| Bus-skew checks | 14 met; minimum slack +2.467 ns |
| Post-route DRC | No errors; existing warnings/advisories remain |

The SquarePulse-specific timing report includes its amplitude-to-negative-value
path under `clk_104_pl`, confirming that the new arithmetic is constrained.
The four-cycle RTL pipeline meets timing without further pipeline changes.
Post-route utilization for the IP is 1,006 LUTs, 955 registers, zero DSPs and
zero BRAMs. Whole-design utilization is 178,653 LUTs (42.01%), 292,897 registers
(34.44%), 442.5 BRAM tiles (40.97%) and 2,352 DSPs (55.06%).

The project's `bitstream.bit` and `bitstream.hwh` were extracted from the same
`bitstream.xsa`. The selected members are `bitstream.bit` and the top-level
`d_1.hwh`; subsidiary SmartConnect/MicroBlaze HWH files are not overlay handoffs.
Both extracted files match their selected archive members byte for byte.
Source hashes describe the build-machine file bytes; Git may normalize text
line endings on another checkout. Firmware artifacts disable Git text
conversion so their hashes and XSA-member equality are preserved.

The first implementation attempt hit a Vivado DDR PHY helper crash:
`TclStackFree: incorrect freePtr`. This was outside the new DDS. All PHY
parameters and actual XDC constraints matched the previously synthesized PHY;
only source-location metadata differed. A single-thread helper independently
validated cache entry `76c734d762a38b9c` with Vivado's own cache check. The retry
uses that matching PHY and a short ASCII temporary directory. Failure and
cache-validation logs are archived; no old BIT or HWH was substituted.

The 68 inherited critical-warning messages have the same categories and counts
as the previous IQ64 build: `Vivado 12-4739` (20), `Vivado 12-5201` (7),
`Constraints 18-4644` (1), and `Common 17-55` (40). These concern the existing
unused clock/port constraints; they are not new SquarePulse warnings. The
placed I/O report confirms the existing external marker at `SPARE1_1V8`,
package pin F15, LVCMOS18.

Four inherited external inputs and 24 outputs have no explicit I/O delay,
matching the original IQ64 project. Internal timing closure does not establish
timing against an external instrument's clock. The post-route methodology
report contains no SquarePulse-specific warnings.

No board programming, physical DAC voltage measurement or external-trigger
oscilloscope measurement was performed. Simulation verifies digital arithmetic
and scheduling, not analog edge shape or RF-board transfer characteristics.
