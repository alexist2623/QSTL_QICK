# qstl_awg_v5 — RTL AWG / RF latency match

Standalone FPGA project on the existing `awg_tuning_v4` Git branch.

`axis_output_sum_v2` adds 13 AWG clocks before the unchanged two-stage signed
sum/round/saturation. All seven AWGs use this delay, including four bypass
channels. At 300 MHz, native SET-to-sum-output and RF command-to-sum-output
latencies are both 31 clocks (AWG 16+13+2, RF 29+2). Commands reaching generators
at different times retain that time difference. RAMP's original 7-clock startup
is unchanged. tProcessor/TMUX and command scheduling are unchanged.

The original v4 Python still compensates the 13-clock difference in software.
**Do not load this v5 candidate using v4 timing assumptions.** This task does
not change driver/compiler timing or deploy to the board. The only separately
authorized Python fix is the shared-DAC AWG selector in the GUI, with 73 passing
tests. It is independent of v5 scheduling.

The BD baseline, generator IPs and XDC stay byte-identical to v4. Only the output
IP and its seven instances change. BIT/HWH/XSA build outputs remain outside Git
and do not replace the successful v4 files.

Build after fresh validation with Vivado 2023.1:

```text
vivado.bat -mode batch -source build_vivado_2023_1.tcl -tclargs F:/Vivado_Output/a5full1
```

Conditions: jobs=4, general.maxThreads=5, default synthesis/implementation
strategies, original timing.xdc and ios.xdc. Final routed setup/hold/pulse-width/
bus-skew is checked before bitstream generation. Failure means stop and report,
with no automatic RTL/XDC changes or retry. Successful external candidates also
require matching BIT/HWH inside the same XSA and the seven expected v5 HWH paths.

Evidence and scope: `analysis_results/awg_tuning_v5/PLAN.md`, `RUNNING.md`, and
fresh sum/native/basic/system/continuous-RC results. All nine recorded inputs were
also freshly recompiled with current software and PMEM/DMEM byte equality was
verified. System replay uses those unchanged inputs with the new RTL; it is not
a new v5-compatible GUI timing profile. The
direct native-command bench independently tests equalized hardware latency.
DC area compensation remains before the IIR; added DDS area and clipping are
outside its compensation scope. No board or analog measurement is performed.
