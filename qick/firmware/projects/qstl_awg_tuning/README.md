# qstl_awg_tuning

`qstl_awg_tuning` is an isolated Vivado block-design variant copied from
`qick/firmware/projects/qstl` for bringing up `axis_awg_tuning_v1` without
changing the original `qstl` project.

The variant reserves DAC23 / RFDC `s23_axis` for the AWG tuning path:

- `axis_tproc64x32_x8_0/m8_axis -> axis_awg_tuning_v1_0/s_axis`
- `axis_awg_tuning_v1_0/m_axis -> axis_register_slice_16/s_axis`
- `axis_register_slice_16/m_axis -> usp_rf_data_converter_0/s23_axis`

`axis_awg_tuning_v1_0` is explicitly configured in `bd_2023-1.tcl` with:

| Parameter | Value |
| --- | ---: |
| `CONFIG.N_DDS` | 16 |
| `CONFIG.B` | 16 |
| `CONFIG.FRAC` | 16 |
| `CONFIG.CMD_WIDTH` | 160 |

The AWG IP uses the same DAC realtime domain as the DAC generator paths:

| AWG pin | BD net source |
| --- | --- |
| `aclk` | `usp_rf_data_converter_0_clk_dac2`, sourced from `dac_clk_buf/BUFG_O` |
| `aresetn` | `rst_dac2_peripheral_aresetn`, sourced from `rst_dac0/peripheral_aresetn` |

```mermaid
flowchart LR
  TP["tProcessor v1<br/>axis_tproc64x32_x8_0"]

  TP -- "m1_axis" --> TM0["axis_tmux_v1_0"]
  TM0 -- "m0" --> G0["axis_signal_gen_v6_0"] --> R0["axis_register_slice_0"] --> DAC00["RFDC s00_axis"]
  TM0 -- "m1" --> G4["axis_signal_gen_v6_4"] --> R8["axis_register_slice_8"] --> DAC10["RFDC s10_axis"]

  TP -- "m2_axis" --> TM1["axis_tmux_v1_1"]
  TM1 -- "m0" --> G1["axis_signal_gen_v6_1"] --> R1["axis_register_slice_1"] --> DAC01["RFDC s01_axis"]
  TM1 -- "m1" --> G5["axis_signal_gen_v6_5"] --> R10["axis_register_slice_10"] --> DAC11["RFDC s11_axis"]

  TP -- "m3_axis" --> TM2["axis_tmux_v1_2"]
  TM2 -- "m0" --> G3["axis_signal_gen_v6_3"] --> R3["axis_register_slice_3"] --> DAC03["RFDC s03_axis"]
  TM2 -- "m1" --> G6["axis_signal_gen_v6_6"] --> R11["axis_register_slice_11"] --> DAC12["RFDC s12_axis"]

  TP -- "m4_axis" --> TM3["axis_tmux_v1_3"]
  TM3 -- "m0" --> G2["axis_signal_gen_v6_2"] --> R2["axis_register_slice_2"] --> DAC02["RFDC s02_axis"]
  TM3 -- "m1" --> G7["axis_signal_gen_v6_7"] --> R12["axis_register_slice_12"] --> DAC13["RFDC s13_axis"]

  TP -- "m5_axis" --> TM4["axis_tmux_v1_4"]
  TM4 -- "m0" --> RO0["axis_dyn_readout_v1_0 command"]
  TM4 -- "m1" --> G8["axis_signal_gen_v6_8"] --> R13["axis_register_slice_13"] --> DAC20["RFDC s20_axis"]

  TP -- "m6_axis" --> TM5["axis_tmux_v1_5"]
  TM5 -- "m0" --> RO1["axis_dyn_readout_v1_1 command"]
  TM5 -- "m1" --> G9["axis_signal_gen_v6_9"] --> R14["axis_register_slice_14"] --> DAC21["RFDC s21_axis"]

  TP -- "m7_axis" --> TM6["axis_tmux_v1_6"]
  TM6 -- "m0" --> G10["axis_signal_gen_v6_10"] --> R15["axis_register_slice_15"] --> DAC22["RFDC s22_axis"]
  TM6 -- "m1" --> RO2["axis_dyn_readout_v1_2 command"]
  TM6 -- "m2" --> OLDG11["axis_signal_gen_v6_11<br/>unused for DAC23"]
  TM6 -- "m3" --> RO3["axis_dyn_readout_v1_3 command"]

  TP -- "m8_axis" --> AWG["axis_awg_tuning_v1_0"]
  AWG --> R16["axis_register_slice_16"] --> DAC23["RFDC s23_axis"]
```

## tProcessor realtime outputs

| tProcessor output | Destination in this BD | Notes |
| --- | --- | --- |
| `m0_axis` | `axi_dma_tproc/S_AXIS_S2MM` | tProcessor data readback path |
| `m1_axis` | `axis_tmux_v1_0/s_axis` | Commands gen0 and gen4 |
| `m2_axis` | `axis_tmux_v1_1/s_axis` | Commands gen1 and gen5 |
| `m3_axis` | `axis_tmux_v1_2/s_axis` | Commands gen3 and gen6 |
| `m4_axis` | `axis_tmux_v1_3/s_axis` | Commands gen2 and gen7 |
| `m5_axis` | `axis_tmux_v1_4/s_axis` | Commands readout0 and gen8 |
| `m6_axis` | `axis_tmux_v1_5/s_axis` | Commands readout1 and gen9 |
| `m7_axis` | `axis_tmux_v1_6/s_axis` | Legacy commands for gen10, readout2, gen11, readout3 |
| `m8_axis` | `axis_awg_tuning_v1_0/s_axis` | AWG tuning command path |

`axis_tproc64x32_x8_0` exposes 160-bit realtime output words on `m1_axis`
through `m8_axis`. In this variant, `m8_axis` is dedicated to AWG tuning
commands and matches `axis_awg_tuning_v1_0` `CMD_WIDTH = 160`.

## DAC output mapping

| RFDC input | DAC path source | Register slice |
| --- | --- | --- |
| `s00_axis` | `axis_signal_gen_v6_0/m_axis` | `axis_register_slice_0` |
| `s01_axis` | `axis_signal_gen_v6_1/m_axis` | `axis_register_slice_1` |
| `s02_axis` | `axis_signal_gen_v6_2/m_axis` | `axis_register_slice_2` |
| `s03_axis` | `axis_signal_gen_v6_3/m_axis` | `axis_register_slice_3` |
| `s10_axis` | `axis_signal_gen_v6_4/m_axis` | `axis_register_slice_8` |
| `s11_axis` | `axis_signal_gen_v6_5/m_axis` | `axis_register_slice_10` |
| `s12_axis` | `axis_signal_gen_v6_6/m_axis` | `axis_register_slice_11` |
| `s13_axis` | `axis_signal_gen_v6_7/m_axis` | `axis_register_slice_12` |
| `s20_axis` | `axis_signal_gen_v6_8/m_axis` | `axis_register_slice_13` |
| `s21_axis` | `axis_signal_gen_v6_9/m_axis` | `axis_register_slice_14` |
| `s22_axis` | `axis_signal_gen_v6_10/m_axis` | `axis_register_slice_15` |
| `s23_axis` | `axis_awg_tuning_v1_0/m_axis` | `axis_register_slice_16` |

## ADC/readout mapping

| RFDC output | Readout IP input | Readout command input |
| --- | --- | --- |
| `m20_axis` | `axis_dyn_readout_v1_0/s1_axis` | `axis_tmux_v1_4/m0_axis -> s0_axis` |
| `m21_axis` | `axis_dyn_readout_v1_1/s1_axis` | `axis_tmux_v1_5/m0_axis -> s0_axis` |
| `m22_axis` | `axis_dyn_readout_v1_2/s1_axis` | `axis_tmux_v1_6/m1_axis -> s0_axis` |
| `m23_axis` | `axis_dyn_readout_v1_3/s1_axis` | `axis_tmux_v1_6/m3_axis -> s0_axis` |

## Legacy gen11 status

`axis_signal_gen_v6_11` is intentionally kept instantiated to minimize BD
churn around the existing generator DMA, AXI-Lite, tProcessor tmux, clock, and
reset plumbing. It still has:

- waveform DMA input from `axis_switch_gen/M11_AXIS` to `s0_axis`
- command input from `axis_tproc64x32_x8_0/m7_axis` through
  `axis_tmux_v1_6/m2_axis` and `axis_register_slice_27`
- AXI-Lite mapping at `0xA0160000`

However, `axis_signal_gen_v6_11/m_axis` is not connected to
`axis_register_slice_16/s_axis` in this variant. DAC23 is driven only by
`axis_awg_tuning_v1_0`.

Summary rules for this variant:

- DAC23 is AWG tuning output.
- tProcessor `m8_axis` is reserved for AWG tuning commands.
- Do not use the old gen11 path unless the BD is changed.
- The old `m8_axis -> axis_set_reg_0 -> qick_vec2bit_0` trigger path is
  removed; `qick_vec2bit_0/din` is tied low with `xlconstant_5`.

## Vivado invocation note

To avoid leaving Vivado-generated files in the repository, run project creation
from an external working directory and set `::origin_dir_loc` to the repository
root before sourcing `proj.tcl`:

```tcl
set repo_root {C:/path/to/QSTL_QICK}
set ::origin_dir_loc $repo_root
source "$repo_root/qick/firmware/projects/qstl_awg_tuning/proj.tcl"
validate_bd_design
report_ip_status
```

This variant is intended for Vivado wiring validation and firmware bring-up.
It intentionally does not add Python driver or assembler support.
