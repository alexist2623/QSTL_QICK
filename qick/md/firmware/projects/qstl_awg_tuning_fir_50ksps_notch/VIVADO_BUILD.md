# Vivado 2023.1 Build Conditions

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

This document defines the reproducible implementation conditions for
`qstl_awg_tuning_fir_50ksps_notch`.

## Required environment

- Vivado: 2023.1
- FPGA part: `xczu49dr-ffvf1760-2-e`
- Board part: `xilinx.com:zcu216:part0:2.0`
- Repository IP catalog: `qick/firmware/ip`
- Constraints: `timing.xdc` and `ios.xdc`
- Synthesis strategy: `Vivado Synthesis Defaults`
- Implementation strategy: `Vivado Implementation Defaults`
- Manual placement and routing: disabled
- Windows build scratch directory: short local path, validated with
  `TEMP=C:\VivadoTemp` and `TMP=C:\VivadoTemp`

## Parallel execution

Two independent Vivado settings must both be set to 5:

```tcl
set jobs 5
set_param general.maxThreads 5
launch_runs synth_1 -jobs $jobs
launch_runs impl_1 -to_step write_bitstream -jobs $jobs
```

`launch_runs -jobs 5` controls concurrent run workers.
`general.maxThreads=5` controls threading inside synthesis and implementation.
Setting only `-jobs 5` is not equivalent to the previous timing-closed build.

Vivado 2023.1 may still report that `synth_design` uses a maximum of four
processes. This is an internal synthesis cap for that operation; it does not
mean that `general.maxThreads=5` or `launch_runs -jobs 5` was omitted. DRC and
timing-update logs should explicitly show five threads.

## Clean build

Use a new, empty output directory for every timing comparison. The build
script intentionally rejects a non-empty output directory so stale
checkpoints, generated IP, or cached run state cannot affect the result.

## Windows path-length requirement

Vivado 2023.1 debug-hub generation requires its implementation temporary path
to be no longer than 146 characters. Use a short physical output directory and
a short local `TEMP`/`TMP` directory. The validated physical output path below
produces a predicted implementation path of 126 characters.

From PowerShell:

```powershell
$env:TEMP = "C:\VivadoTemp"
$env:TMP = "C:\VivadoTemp"
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null

$out = "C:\JeonghyunPark\Workspace\Vivado_Output\q50r5c"
& "C:\Xilinx\Vivado\2023.1\bin\vivado.bat" `
  -mode batch `
  -log "C:\JeonghyunPark\Workspace\Vivado_Output\q50r5c_vivado.log" `
  -journal "C:\JeonghyunPark\Workspace\Vivado_Output\q50r5c_vivado.jou" `
  -source "C:\JeonghyunPark\Workspace\QSTL_QICK\qick\firmware\projects\qstl_awg_tuning_fir_50ksps_notch\build_vivado_2023_1_run5.tcl" `
  -tclargs $out
```

If a sufficiently short physical path is unavailable, a `subst` drive is a
fallback:

```powershell
subst W: "C:\JeonghyunPark\Workspace\Vivado_Output"
```

The script predicts the implementation temporary path and exits before project
creation if it exceeds 146 characters. It records the effective path, path
length, `TEMP`, and `TMP` in `build_conditions.txt`.

The failed long-path build from July 24, 2026 stopped at `opt_design` with
`Chipscope 16-302`; it was not an RTL, utilization, or timing failure.

## Vivado helper-process retry

DDR4 PHY regeneration launches a nested synthesis helper. On Windows,
Vivado 2023.1 can transiently fail with either of these messages even though
both installation files exist and are readable:

```text
couldn't read file ".../unimacro_verilog.tcl": No error
couldn't read file ".../unimacro_vhdl.tcl": No error
```

This is a Vivado helper-process failure, not an RTL or DDR4 configuration
error. The build and retry scripts pre-read both files as a validation and
cache-warming step. If the first implementation attempt still stops at
`Generate And Synthesize MIG Cores`, use the implementation-only retry below.
Do not rerun synthesis and do not reuse placement or routing.

## Implementation-only retry

If synthesis completed but implementation stopped because of a transient
Vivado tool error, restart only `impl_1` from the same clean project's
synthesized checkpoint:

```powershell
& "C:\Xilinx\Vivado\2023.1\bin\vivado.bat" `
  -mode batch `
  -log "C:\JeonghyunPark\Workspace\Vivado_Output\q50r5c_impl_retry.log" `
  -source "C:\JeonghyunPark\Workspace\QSTL_QICK\qick\firmware\projects\qstl_awg_tuning_fir_50ksps_notch\resume_vivado_2023_1_impl_run5.tcl" `
  -tclargs "C:\JeonghyunPark\Workspace\Vivado_Output\q50r5c"
```

The retry script verifies that `synth_1` is complete, resets `impl_1`, and uses
the same default implementation strategy, `launch_runs -jobs 5`, and
`general.maxThreads=5`. It does not reuse placement or routing from the failed
implementation attempt.

## Validated build on July 26, 2026

The conditions in this document were exercised on branch
`codex/qstl-fir-50ksps-notch20x2`. The source state is represented by the
commit containing this document. The clean project and reports are under:

```text
C:\JeonghyunPark\Workspace\Vivado_Output\q50r5f
```

The build used Vivado 2023.1, `launch_runs -jobs 5`,
`general.maxThreads=5`, the default synthesis and implementation strategies,
and no manual placement or routing. The 50 kSPS capture path contained:

```text
axis_fir_decim_300to1_v1
  -> axis_notch_decim_1m_to50k_v1
  -> axis_trigger_sync_v1
  -> axis_buffer_ddr_sample_v2
```

Synthesis completed successfully. The first implementation attempt stopped
during DDR4 PHY helper synthesis with the transient Vivado helper-process
failure described above. The implementation-only retry reset `impl_1`,
regenerated placement and routing, and completed bitstream generation.

Both setup and hold timing closed:

| Metric | Result |
| --- | ---: |
| Setup WNS | +0.014855 ns |
| Setup TNS | 0.000000 ns |
| Hold WHS | +0.009353 ns |
| Hold THS | 0.000000 ns |
| Timing closed | Yes |

The project-local deployment artifacts are exact copies of the final build
outputs:

| Artifact | Size (bytes) | SHA-256 |
| --- | ---: | --- |
| `bitstream.bit` | 34,437,473 | `53C0BDA320A271150017429A0B3DB47B63507B20F26E48E58313D03116A8CC79` |
| `bitstream.hwh` | 2,614,924 | `DAAA905F04755B9D0D399FF052E9EF59AB8605B4E383263E5F67EC25D91F681C` |
| `bitstream.xsa` | 18,327,860 | `6235605D839E78C4023E33EBFD9A435F2EA9EC8D002D5CC0CE36EE9599789430` |

## Generated artifacts and reports

The output directory contains:

- `bitstream.bit`
- `bitstream.hwh`
- `bitstream.xsa`
- `build_conditions.txt`
- `build_result.txt`
- `timing_summary_postsynth.rpt`
- `timing_summary_postroute.rpt`
- `timing_paths_postroute.rpt`
- `utilization_postsynth.rpt`
- `utilization_postroute.rpt`
- `utilization_hierarchical_postroute.rpt`
- `route_status_postroute.rpt`
- `drc_postroute.rpt`
- `methodology_postroute.rpt`

Timing closure requires non-negative setup WNS and hold WHS. Bitstream
generation alone does not prove timing closure; always inspect
`build_result.txt` and `timing_summary_postroute.rpt`.

## Up to ten independent timing attempts

Use `run_vivado_2023_1_until_timing_closure.ps1` to perform repeated clean
builds. Every attempt starts from synthesis in a new output directory. The
script stops as soon as both setup and hold timing close, or after the requested
limit (maximum 10):

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\run_vivado_2023_1_until_timing_closure.ps1 `
  -MaxAttempts 10
```

With the default prefix, the clean projects are written to
`C:\JeonghyunPark\Workspace\Vivado_Output\q50tc01` through `q50tc10`.
Existing attempt directories are never deleted or reused. Results are updated
after every attempt in:

```text
C:\JeonghyunPark\Workspace\Vivado_Output\q50tc_summary.csv
C:\JeonghyunPark\Workspace\Vivado_Output\q50tc_summary.md
```

The wrapper uses the same Vivado 2023.1, Run=5, default synthesis and
implementation strategies, short `TEMP`/`TMP` path, and no manual placement or
routing. It invokes the implementation-only retry only for the documented
transient Vivado implementation failure; a new numbered attempt always begins
again from synthesis.
