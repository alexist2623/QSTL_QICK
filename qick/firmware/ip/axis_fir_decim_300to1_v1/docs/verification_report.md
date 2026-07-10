# Verification Report

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

This file is updated as validation commands are run.

## Python Validation

Command:

```text
python qick/firmware/ip/axis_fir_decim_300to1_v1/scripts/verify_fir_decim_300to1_python.py
```

Result: PASS

Summary file:

```text
qick/firmware/ip/axis_fir_decim_300to1_v1/reports/python_validation_summary.txt
```

## SystemVerilog Validation

Command:

```text
C:/Xilinx/Vivado/2023.1/bin/vivado.bat -mode batch -source qick/firmware/ip/axis_fir_decim_300to1_v1/src/tb/run_xsim.tcl
```

Result: PASS

Observed simulator PASS line:

```text
PASS: axis_fir_decim_300to1_v1 max_lane_error=0
```

Directed cases covered:

- reset behavior
- impulse vector
- tone vector
- noisy in-band plus out-of-band vector
- output ready toggling with FIR output continuing independently of `m_axis_tready`
- input valid gaps
- trigger phase alignment after pre-trigger input data while preserving FIR history
- reset in the middle of a stream
- output X/Z check

## Previous Post-Synthesis Timing Snapshot

Command:

```text
C:/Xilinx/Vivado/2023.1/bin/vivado.bat -mode batch -source C:/JeonghyunPark/Workspace/Vivado_Output/qstl_awg_tuning_fir_run_synth.tcl
```

Result: synthesis completed, but timing constraints were not fully met.

Note: this snapshot was taken before the trigger-alignment port was added.
After the trigger-alignment update, RTL simulation and BD validation were rerun;
full synthesis has not been rerun to completion in this report.

The previous FIFO-ready-to-FIR-DSP-enable path was removed by making the FIR
pipeline ignore `m_axis_tready`.

Current summary:

```text
WNS = -0.014 ns
TNS = -10.374 ns
Register as Latch = 0
```

Current worst setup path is reset fanout into the FIR DSP output reset:

```text
rst_adc2/.../ACTIVE_LOW_PR_OUT_DFF[0]
  -> ddr4/axis_fir_decim_300to1_v1_0/inst/stage0_i/sum0_l1_reg[0]/DSP_OUTPUT_INST/RSTP
```
