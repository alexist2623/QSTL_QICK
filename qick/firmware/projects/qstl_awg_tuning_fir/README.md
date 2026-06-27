# qstl_awg_tuning_fir

This variant is copied from qstl_awg_tuning.
Only axis_signal_gen_v6 instances with GEN_DDS FALSE are replaced by axis_awg_tuning_v1.
m8_axis remains the original trigger/control path.
Readout paths are unchanged.
DDS-enabled signal generators are unchanged.
RFDC DAC endpoint assignments are preserved.

The DDR capture hierarchy replaces the original Xilinx AXIS width converter
with QICK:QICK:axis_triggered_pack_32to256_v1:1.0. The custom packer drops
pre-trigger samples, starts a fresh 8-sample pack on each trigger rising edge,
packs eight 32-bit readout samples into one 256-bit AXIS beat, and discards
partial packs when trigger falls. The existing axis_clock_converter_0,
axis_buffer_ddr_v1_0, AXI SmartConnect, and DDR4 controller are unchanged.

## Replacements

| Original | New | Command source preserved | RFDC DAC endpoint preserved |
| --- | --- | --- | --- |
| axis_signal_gen_v6_4 | axis_awg_tuning_v1_4 | axis_tmux_v1_0/m1_axis -> axis_register_slice_9 | usp_rf_data_converter_0/s10_axis |
| axis_signal_gen_v6_5 | axis_awg_tuning_v1_5 | axis_tmux_v1_1/m1_axis -> axis_register_slice_21 | usp_rf_data_converter_0/s11_axis |
| axis_signal_gen_v6_6 | axis_awg_tuning_v1_6 | axis_tmux_v1_2/m1_axis -> axis_register_slice_22 | usp_rf_data_converter_0/s12_axis |
| axis_signal_gen_v6_7 | axis_awg_tuning_v1_7 | axis_tmux_v1_3/m1_axis -> axis_register_slice_23 | usp_rf_data_converter_0/s13_axis |
| axis_signal_gen_v6_8 | axis_awg_tuning_v1_8 | axis_tmux_v1_4/m1_axis -> axis_register_slice_24 | usp_rf_data_converter_0/s20_axis |
| axis_signal_gen_v6_9 | axis_awg_tuning_v1_9 | axis_tmux_v1_5/m1_axis -> axis_register_slice_25 | usp_rf_data_converter_0/s21_axis |
| axis_signal_gen_v6_10 | axis_awg_tuning_v1_10 | axis_tmux_v1_6/m0_axis -> axis_register_slice_26 | usp_rf_data_converter_0/s22_axis |
| axis_signal_gen_v6_11 | axis_awg_tuning_v1_11 | axis_tmux_v1_6/m2_axis -> axis_register_slice_27 | usp_rf_data_converter_0/s23_axis |

## Routing

```mermaid
flowchart LR
  tproc["axis_tproc64x32_x8_0"]

  tproc -- "m1_axis" --> tmux0["axis_tmux_v1_0"]
  tproc -- "m2_axis" --> tmux1["axis_tmux_v1_1"]
  tproc -- "m3_axis" --> tmux2["axis_tmux_v1_2"]
  tproc -- "m4_axis" --> tmux3["axis_tmux_v1_3"]
  tproc -- "m5_axis" --> tmux4["axis_tmux_v1_4"]
  tproc -- "m6_axis" --> tmux5["axis_tmux_v1_5"]
  tproc -- "m7_axis" --> tmux6["axis_tmux_v1_6"]

  tmux0 -- "m0_axis" --> gen0["axis_signal_gen_v6_0"]
  tmux1 -- "m0_axis" --> gen1["axis_signal_gen_v6_1"]
  tmux3 -- "m0_axis" --> gen2["axis_signal_gen_v6_2"]
  tmux2 -- "m0_axis" --> gen3["axis_signal_gen_v6_3"]

  tmux0 -- "m1_axis" --> awg4["axis_awg_tuning_v1_4"]
  tmux1 -- "m1_axis" --> awg5["axis_awg_tuning_v1_5"]
  tmux2 -- "m1_axis" --> awg6["axis_awg_tuning_v1_6"]
  tmux3 -- "m1_axis" --> awg7["axis_awg_tuning_v1_7"]
  tmux4 -- "m1_axis" --> awg8["axis_awg_tuning_v1_8"]
  tmux5 -- "m1_axis" --> awg9["axis_awg_tuning_v1_9"]
  tmux6 -- "m0_axis" --> awg10["axis_awg_tuning_v1_10"]
  tmux6 -- "m2_axis" --> awg11["axis_awg_tuning_v1_11"]

  tmux4 -- "m0_axis" --> ro0["axis_dyn_readout_v1_0"]
  tmux5 -- "m0_axis" --> ro1["axis_dyn_readout_v1_1"]
  tmux6 -- "m1_axis" --> ro2["axis_dyn_readout_v1_2"]
  tmux6 -- "m3_axis" --> ro3["axis_dyn_readout_v1_3"]

  tproc -- "m8_axis" --> setreg["axis_set_reg_0"]
  setreg -- "dout" --> vec2bit["qick_vec2bit_0"]
  vec2bit --> trig0["axis_avg_buffer_0 trigger"]
  vec2bit --> trig1["axis_avg_buffer_1 trigger"]
  vec2bit --> trig2["axis_avg_buffer_2 trigger"]
  vec2bit --> trig3["axis_avg_buffer_3 trigger"]
  vec2bit --> trig4["mr_buffer_et_0 trigger"]
  vec2bit --> trig5["ddr4 trigger"]
  vec2bit --> spare["SPARE1_1V8"]

  gen0 --> rfdc00["RFDC s00_axis"]
  gen1 --> rfdc01["RFDC s01_axis"]
  gen2 --> rfdc02["RFDC s02_axis"]
  gen3 --> rfdc03["RFDC s03_axis"]
  awg4 --> rfdc10["RFDC s10_axis"]
  awg5 --> rfdc11["RFDC s11_axis"]
  awg6 --> rfdc12["RFDC s12_axis"]
  awg7 --> rfdc13["RFDC s13_axis"]
  awg8 --> rfdc20["RFDC s20_axis"]
  awg9 --> rfdc21["RFDC s21_axis"]
  awg10 --> rfdc22["RFDC s22_axis"]
  awg11 --> rfdc23["RFDC s23_axis"]
```
