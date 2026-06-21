# qstl_awg_tuning

This is an isolated block-design variant for bringing up `axis_awg_tuning_v1`.

It is copied from `qick/firmware/projects/qstl` and keeps the original project untouched. The variant adds `QICK:QICK:axis_awg_tuning_v1:1.0` to the IP catalog check list, instantiates `axis_awg_tuning_v1_0`, and places it in the same DAC realtime `aclk`/`aresetn` domain as the signal generator path.

For this first integration hook:

- `axis_tproc64x32_x8_0/m8_axis` is connected to `axis_awg_tuning_v1_0/s_axis`.
- `axis_awg_tuning_v1_0/m_axis` is routed into `axis_register_slice_16/s_axis`, which is analogous to a signal-generator-to-DAC path.
- The original `qstl` project remains unchanged.

This variant is intended for Vivado wiring validation and firmware bring-up. It intentionally does not add Python driver or assembler support.
