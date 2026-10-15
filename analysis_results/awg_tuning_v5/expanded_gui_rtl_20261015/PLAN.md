# Current v5 expanded GUI to RTL validation

User request on 2026-10-15: execute the prior virtual-matrix/sweep 21 cases,
the compiler 17 combinations, and composite 7 cases against current production
Python/GUI and the successfully built v5 RTL. Exact simultaneous AWG/RF start
is explicitly excluded from fixes. This is a new validation run, separate from
the completed build and prior postbuild evidence.

## Required execution and honest accounting

- Virtual matrix21: original asymmetric fully coupled 3x3 matrix, physical
  scales800/400/800mV, original sweep coordinates/directions and compensation
  modes, actual MainWindow/dialog input and Run Experiment PMEM/DMEM comparison.
- Composite7: original six tau-by-pi coordinates plus Hahn-to-Custom with
  named amplitude/phase, actual GUI/normal host coordinate resolution, all3pairs.
- Compiler17: six expected summed-output Calibration rejections, four CPMG
  coordinates, four UDD coordinates, Quantum Loop n0/1/3.
  Capture current GUI/compiler outcomes for all17; run accepted distinct
  waveforms through RTL. A rejected or compiler-only condition is not RTL PASS.
  The CPMG N/tau coordinates overlap matrix21, but compiler17 retains the
  original nine-point HOLD/voltage grid while matrix21 uses two amplitude
  points. These are distinct inputs and need separate fresh RTL executions.
- Use actual candidate HWH metadata, current production v5 latency31/31 and
  unchanged real tProcessor/TMUX/AWG/DDS/sum-v2. Independently check the13-cycle
  AWG history, output sum and final digital slice where the harness supports it.
  Retain the original independent matrix/integer/area/RC/reset/RF/Square checks.
- First attempt original requested timing. Preserve any production guard
  rejection. For cases blocked by the explicitly excluded zero-offset issue,
  a separately tagged +100ns outer RF offset fixture may exercise the requested
  matrix/sweep/composite behavior. This variation was disclosed to the user.
  Record the exact input difference and never count the original rejected case
  as passed. Do not alter internal tau/pi/phase or weaken command spacing.
- Record source/input/evidence hashes and process exit codes. Preserve first
  failures and test-environment fixes. No tolerance relaxation or production
  repair is part of this request.

## Isolation and ownership

- matrix21: F:/Vivado_Output/a5matrix1, one xsim slot.
- composite7: F:/Vivado_Output/a5composite1, one xsim slot.
- compiler17: separate preparation; start RTL only after a slot is released.
- Maximum2xsim processes. Copy simulation libraries before preparation and
  compile only isolated copies; do not modify shared prior build libraries.
- Python qcodes2, explicit repository working directories, offscreen Qt with
  clean teardown, no board-I/O except local compiler substitutes.

No production source, RTL/XDC, user JSON, firmware, live GUI/server, board,
branch, commit/push or new FPGA synthesis changes. Existing automations remain
PAUSED. Root owns before/after production/input/artifact audit and final report;
each worker owns only its new verification subfolder and external run folder.

## Later local package request

The user subsequently asked why v5 was absent from the updater and whether its
BIT/HWH files had been copied. Four previously absent local files were published
under qick/firmware/projects/qstl_awg_v5: bitstream.bit/.hwh/.xsa and
build_manifest.json. See ../local_firmware_package_20261015/result.json for exact
hashes and the successful production package review. No board upload or existing
firmware overwrite occurred. The after-audit permits only these four new exact
files; all original source, settings, build and firmware hashes remain required.
The package manifest explicitly records this expanded validation as still running.
