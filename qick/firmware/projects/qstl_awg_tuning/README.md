# qstl_awg_tuning

This project variant is recreated from `qick/firmware/projects/qstl`.
The original `qstl` project is not modified.

Only the `axis_signal_gen_v6` instances whose original property block
explicitly contained `CONFIG.GEN_DDS {FALSE}` are replaced:

- Replaced: `axis_signal_gen_v6_4` through `axis_signal_gen_v6_11`
- Replacement IP: `axis_awg_tuning_v1_4` through `axis_awg_tuning_v1_11`
- Parameters: `N_DDS=16`, `B=16`, `FRAC=16`, `CMD_WIDTH=160`

The DDS-enabled generators remain unchanged:

- Preserved: `axis_signal_gen_v6_0` through `axis_signal_gen_v6_3`

Preserved blocks and paths:

- `axis_tproc64x32_x8_0/m8_axis` still drives `axis_set_reg_0/s_axis`
- `axis_set_reg_0/dout` still drives `qick_vec2bit_0/din`
- `qick_vec2bit_0/dout[0..6]` remains the trigger fanout
- `axis_set_reg_0` and `qick_vec2bit_0` are unchanged
- readout IPs, readout tmux paths, avg buffers, `mr_buffer`, DDR4, RFDC, DMA, PS, clock/reset, and interrupt blocks are not replaced
- RFDC DAC slice assignments remain the same

Removed only for the replaced DDS-disabled generators:

- waveform-load `s0_axis` connections
- AXI-Lite `s_axi` connections
- `s0_axis_*` and `s_axi_*` clock/reset pins
- stale address assignments

The Vivado project script computes the repository root from this script
location and creates the batch project under the parent workspace:

```text
C:\JeonghyunPark\Workspace\Vivado_Output\qstl_awg_tuning
```

## Routing

```mermaid
flowchart LR
  TP["axis_tproc64x32_x8_0"]

  TP -- "m1_axis" --> TM0["axis_tmux_v1_0"]
  TP -- "m2_axis" --> TM1["axis_tmux_v1_1"]
  TP -- "m3_axis" --> TM2["axis_tmux_v1_2"]
  TP -- "m4_axis" --> TM3["axis_tmux_v1_3"]
  TP -- "m5_axis" --> TM4["axis_tmux_v1_4"]
  TP -- "m6_axis" --> TM5["axis_tmux_v1_5"]
  TP -- "m7_axis" --> TM6["axis_tmux_v1_6"]

  TP -- "m8_axis" --> SET["axis_set_reg_0/s_axis"]
  SET -- "dout" --> VEC["qick_vec2bit_0/din"]
  VEC -- "dout[0..6]" --> TRIG["trigger outputs"]

  TM0 -- "m0" --> CMD0["axis_register_slice_4"] --> SG0["axis_signal_gen_v6_0"] --> OUT0["axis_register_slice_0"] --> DAC00["RFDC s00_axis"]
  TM1 -- "m0" --> CMD1["axis_register_slice_5"] --> SG1["axis_signal_gen_v6_1"] --> OUT1["axis_register_slice_1"] --> DAC01["RFDC s01_axis"]
  TM3 -- "m0" --> CMD2["axis_register_slice_6"] --> SG2["axis_signal_gen_v6_2"] --> OUT2["axis_register_slice_2"] --> DAC02["RFDC s02_axis"]
  TM2 -- "m0" --> CMD3["axis_register_slice_7"] --> SG3["axis_signal_gen_v6_3"] --> OUT3["axis_register_slice_3"] --> DAC03["RFDC s03_axis"]

  TM0 -- "m1" --> CMD4["axis_register_slice_9"] --> AWG4["axis_awg_tuning_v1_4"] --> OUT4["axis_register_slice_8"] --> DAC10["RFDC s10_axis"]
  TM1 -- "m1" --> CMD5["axis_register_slice_21"] --> AWG5["axis_awg_tuning_v1_5"] --> OUT5["axis_register_slice_10"] --> DAC11["RFDC s11_axis"]
  TM2 -- "m1" --> CMD6["axis_register_slice_22"] --> AWG6["axis_awg_tuning_v1_6"] --> OUT6["axis_register_slice_11"] --> DAC12["RFDC s12_axis"]
  TM3 -- "m1" --> CMD7["axis_register_slice_23"] --> AWG7["axis_awg_tuning_v1_7"] --> OUT7["axis_register_slice_12"] --> DAC13["RFDC s13_axis"]
  TM4 -- "m1" --> CMD8["axis_register_slice_24"] --> AWG8["axis_awg_tuning_v1_8"] --> OUT8["axis_register_slice_13"] --> DAC20["RFDC s20_axis"]
  TM5 -- "m1" --> CMD9["axis_register_slice_25"] --> AWG9["axis_awg_tuning_v1_9"] --> OUT9["axis_register_slice_14"] --> DAC21["RFDC s21_axis"]
  TM6 -- "m0" --> CMD10["axis_register_slice_26"] --> AWG10["axis_awg_tuning_v1_10"] --> OUT10["axis_register_slice_15"] --> DAC22["RFDC s22_axis"]
  TM6 -- "m2" --> CMD11["axis_register_slice_27"] --> AWG11["axis_awg_tuning_v1_11"] --> OUT11["axis_register_slice_16"] --> DAC23["RFDC s23_axis"]

  TM4 -- "m0" --> RO0["axis_dyn_readout_v1_0/s0_axis"]
  TM5 -- "m0" --> RO1["axis_dyn_readout_v1_1/s0_axis"]
  TM6 -- "m1" --> RO2["axis_dyn_readout_v1_2/s0_axis"]
  TM6 -- "m3" --> RO3["axis_dyn_readout_v1_3/s0_axis"]

  ADC20["RFDC m20_axis"] --> RO0
  ADC21["RFDC m21_axis"] --> RO1
  ADC22["RFDC m22_axis"] --> RO2
  ADC23["RFDC m23_axis"] --> RO3
  RO0 --> BR0["axis_broadcaster_0 and axis_switch_mr"]
  RO1 --> BR1["axis_broadcaster_1 and axis_switch_mr"]
  RO2 --> BR2["axis_broadcaster_2 and axis_switch_mr"]
  RO3 --> BR3["axis_broadcaster_3 and axis_switch_mr"]
```
