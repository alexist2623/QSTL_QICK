# AWG tuning v2 recovery status

Updated: 2026-09-27 17:12 America/Vancouver. Implementation, publication and final validation completed.

- QICK checkout: `C:/JeonghyunPark/Workspace/QSTL_QICK`, branch `awg_tuning_v2`.
- GUI checkout: `C:/JeonghyunPark/Workspace/PulseGenerator-qick`, branch `awg_tuning_v2`.
- At this validation checkpoint, no new commit or push had been performed. Do not use the separate QCS checkout.
- Completed build: `C:/JeonghyunPark/Workspace/Vivado_Output/awg2b`.
- Root log: `C:/JeonghyunPark/Workspace/Vivado_Output/awg2b_resume.log`.
- Implementation log: `awg2b/qstl_awg_v2.runs/impl_1/runme.log`.
- Vivado parent and implementation workers exited normally; unified-exec session 98209 returned exit code 0. No build or simulation from this task remains running.
- All 130 IP synthesis jobs, top-level synthesis, placement, routing and bitstream generation completed. Final setup WNS is +0.006120 ns and hold WHS is +0.009412 ns. Pulse-width and all 14 bus-skew constraints pass (minimum skew slack +2.532 ns). No-clock and unconstrained internal endpoint counts are zero. External I/O delay and methodology warnings remain documented in the reports.
- The seven production-RTL validation cases in REPORT.md completed successfully. Their saved evidence was reanalyzed against the current GUI compiler and RTL. Do not rerun them unless functional source changes.
- Standalone AWG RTL: 170 cases / 117,200 samples passed.
- The legacy `src/tb/run_tb_simple.tcl` entry point now invokes the same production validation suite, and its rerun passed all 170 cases. This is duplicate coverage, not 170 additional cases.
- GUI regressions: 210 passed, plus one full 200 x 200 x 2 tProcessor instruction-model test. Driver/model regressions: 14 passed.
- Integer voltage increment drift is fixed: targets are independently rounded per requested point; dependent ramp/DC payloads follow those targets. 20-point 5 to 15 mV scan now ends at 15.0390625 mV, versus 14.2578125 mV before.
- `REPORT.md`, `voltage_grid_before_after.png`, `single_clock_ramps.png` and `gui_v2_front_panel.png` are current. The published HWH passed GUI AWG/Stability recognition and seven v2 DAC-route checks. This is offline validation, not a board measurement.
- Published BIT/HWH/XSA: `qick/firmware/projects/qstl_awg_v2/`. BIT and HWH were extracted from the same XSA and match its members byte for byte. `build_manifest.json` records hashes and source versions.
- Final recovery audit passed for both Git databases, 38 source files, 135 DCP CRC checks, XPR/HWH XML, XSA CRC and published artifact hashes. See `recovery_audit_final.json`. Both Git diff whitespace checks passed.
- The completed build occupies 2.76 GiB, and the GUI RTL workspace is about 1.13 GiB. Full waveforms were not dumped. No prior firmware, source or denied-deletion temporary directories were removed.

Remaining work at this validation checkpoint: none for the requested implementation and digital validation. Commit/push and live-board measurements had not yet been performed.

Python: `C:/Users/박정현/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.

Python environment: `PYTHONPATH=C:/JeonghyunPark/Workspace/QSTL_QICK/qick/qick_lib;C:/JeonghyunPark/Workspace/QSTL_QICK/tmp/iq64_gui_python_deps`, `PYTHONUTF8=1`, `QT_QPA_PLATFORM=offscreen`.

Vivado 2023.1 uses the existing `C:/Xilinx/Xilinx.lic`, `TEMP=C:/VivadoTemp`, `TMP=C:/VivadoTemp`. The first DDR synthesis worker stalled; its retry passed with the saved single-thread synthesis hook. The older `awg2` generated project is incomplete and is not the active build. Preserve it; resume the readable `awg2b` project only after checking that no process is using it.
