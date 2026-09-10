# qstl_awg_tuning_fir_1msps_v2

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

Continuous 1 MSPS capture derived from `qstl_awg_tuning_fir_50ksps_notch`.
The latest shared FIR and timestamp-queue DDR V2 are retained. The entire
post-1-MSPS `axis_notch_decim_1m_to50k_v1` block is removed, including its
113/125-tap FIR decimators and 40 notch sections.

Validated firmware: [BIT](bitstream.bit), [HWH](bitstream.hwh),
[XSA](bitstream.xsa). Use the BIT and HWH together.
[Validation results](VALIDATION.md) include the passing Vivado 2023.1 timing,
RTL/Python regressions, artifact hashes, and remaining board-test limitations.

```text
axis_switch_ddr/M00_AXIS
  -> axis_fir_decim_300to1_v1_0 (300 MSPS -> /10 -> /10 -> /3 -> 1 MSPS)
  -> axis_buffer_ddr_sample_v2_0 (programmable trigger delay, capture, CDC)
  -> axi_smc_1/S01_AXI -> DDR4

tProcessor trigger -> axis_trigger_sync_v1_0 -> DDR V2 trigger
constant 0 -> FIR trigger
```

The FIR keeps its history and decimation phase across triggers and DDR re-arm.
The FIR `capture_trigger` output is unused. DDR V2 waits for the programmed
deadline, then captures the next available FIR sample. Samples are 32-bit
signed IQ, `Q[31:16]`, `I[15:0]`, at a 1 us interval (4 MB/s before padding).
Each trigger's data is padded to a multiple of eight samples for DDR writes;
the Python readback API removes that padding.

## Clock and delay

The actual external CLK104 PL clock is **300 MHz**, as confirmed by the board
owner in the earlier tuning work. Legacy Tcl/HWH files labeled this clock as
400 MHz even though the timing constraint was already 3.333 ns. This project's
two differential clock ports use `FREQ_HZ=300000000`, so generated HWH metadata
for the tProcessor, AWG, FIR and DDR source domain agrees with the board.
The XDC period remains 3.333 ns, slightly conservative relative to 300 MHz.
Tcl/HWH metadata does not itself program the external clock synthesizer.

Register 9 / AXI-Lite byte offset `0x24`, `TRIGGER_DELAY_CYCLES_REG`, counts
every `s_axis_aclk` cycle, independently of `tvalid`:

```text
cycles = round(delay_us * 300)
delay_us = cycles / 300
FIR group delay = 47 + 10*63 + 100*80 = 8677 input samples
default delay = 8677 cycles = 28.923333 us
```

This default compensates the FIR's calculated linear-phase group delay. It is
not a measurement of total ADC/readout/FIR pipeline latency. Trigger
synchronization adds fixed clock cycles, and capture waits for a valid output
on the continuous 1 us sample grid. Software can override the delay to include
measured system latency. Removing the post-filter removes its 676 us FIR delay
and its frequency-dependent notch delay; do not reuse the 50 kSPS delay value.

The 32-bit timestamp queue has 64 future-event entries. The programmable range
is `0..0xFFFFFFFF` cycles (about 14.3166 s at 300 MHz). The delay is latched at
arm. Matured events remain pending if a previous capture is busy, so overlapping
capture windows are served later rather than reconstructed at their original
timestamps. Continuous 40 kHz triggers are practical when each capture fits
within the 25 us period; the integration test uses 13 samples per trigger and
a delay longer than one trigger period.

## Python

Load this project's matching `bitstream.bit` and `bitstream.hwh` with the QICK
library from this branch. Driver metadata reports `fir_rate_profile="1_msps"`,
`stored_sample_rate_hz=1000000`, `supports_trigger_delay=True`,
`fir_trigger_aligned=False`, and `fir_clock_mhz=300`.

```python
delay_us = 8677 / 300
soc.arm_ddr4_fir_samples(
    ch=0, n_samples=13, n_triggers=4,
    trigger_delay_cycles=round(delay_us * soc.ddr4_buf.cfg["fir_clock_mhz"]),
)
# Run the tProcessor program that emits four DDR triggers, and wait for done.
iq = soc.get_ddr4_fir_samples(n_samples=13, n_triggers=4)
```

Keep the upstream readout stream running through the delayed capture windows.
Readout length must include any user-selected delay as well as capture time.
The delay argument is a clock count, not a count of 1 MSPS samples. Omitting it
preserves the current register setting, initialized to 8677 at driver setup.

Consumers must select FPGA delay by `supports_trigger_delay` and continuous
filter metadata, not solely by the `50_ksps` profile name. In particular, the
separate PulseGenerator GUI's existing `profile_name == "50_ksps"` delay
selection needs adaptation before using its legacy 1 MSPS workflow with V2;
that workflow otherwise adds the old software trigger shift. This firmware
project and QICK API do not modify that separate repository.

## Build and verification

Use Vivado 2023.1, ZCU216 / `xczu49dr-ffvf1760-2-e`. Both build concurrency
settings remain 5 (`launch_runs -jobs 5`, `general.maxThreads=5`), with the
default synthesis and implementation strategies. The script requires a fresh,
short output path to avoid Vivado's Windows temporary-path limit.

```powershell
$env:TEMP = "C:\VivadoTemp"
$env:TMP = "C:\VivadoTemp"
$env:XILINXD_LICENSE_FILE = "C:\Xilinx\Xilinx.lic"
& "C:\Xilinx\Vivado\2023.1\bin\vivado.bat" -mode batch -source qick/firmware/projects/qstl_awg_tuning_fir_1msps_v2/build_vivado_2023_1_run5.tcl -tclargs C:/JeonghyunPark/Workspace/Vivado_Output/q1mv2b
```

`proj.tcl` creates the block design only. The full build script exports matching
BIT/HWH/XSA and setup/hold results. `resume_vivado_2023_1_impl_run5.tcl` resumes
an existing completed synthesis after a transient implementation tool error.
Publish artifacts only after both setup and hold timing pass.
Use your installed license path/server for `XILINXD_LICENSE_FILE`. On the
development PC the valid device license is in `C:\Xilinx\Xilinx.lic`, outside
Vivado's default search path; omitting that environment setting prevents
synthesis even though simulation and BD validation succeed.

```powershell
& "C:\Xilinx\Vivado\2023.1\bin\vivado.bat" -mode batch -source qick/firmware/projects/qstl_awg_tuning_fir_1msps_v2/run_xsim.tcl -tclargs C:/JeonghyunPark/Workspace/Vivado_Output/q1mv2_tests
python qick/qick_lib/qick/test_ddr_triggered_pack_support.py
```

The XSim runner executes the shared FIR vector regression, the DDR V2 queue,
wraparound, overflow, packing and backpressure regression, and a real FIR/DDR
integration test. The latter checks the 300-cycle output spacing across raw
triggers/re-arm, programmable delays of 0 and 8677 cycles, four 40 kHz triggers,
and the exact captured IQ words and padding against a separate deadline model.
The latest FIR DSP input/valid pipelining remains in the shared IP; no FIR or
DDR datapath RTL was rolled back.

The baseline design's BD warnings remain: four 20-byte TMUX to 11-byte readout
command interfaces, an address-network overlap warning, and older IP versions.
These also occur in the prior `q50tsq1` 50 kSPS build. The inherited XDC contains
some unmatched legacy clock/reset/trigger pin queries; the active 300 MHz
`clk_104_pl` clock and its DDR CDC clock group are still explicitly constrained.
