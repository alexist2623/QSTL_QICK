# axis_fir_decim_300to1_v1 Testbench

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

Run:

```text
vivado -mode batch -source qick/firmware/ip/axis_fir_decim_300to1_v1/src/tb/run_xsim.tcl
```

The testbench reads generated vectors from `vectors/` and verifies:

- reset behavior,
- impulse response,
- passband tone response,
- noisy mixed signal response,
- output ready toggling while the FIR output continues,
- input valid gaps,
- trigger phase alignment after pre-trigger input data while preserving FIR history,
- reset during an active stream,
- no X/Z values on valid transfers,
- no X/Z values while `m_axis_tready` toggles.
