# Independent review addendum

The final GUI helper was reviewed at SHA256 `013463f2546130b8268a08e3ea04c9ce5b1734b8f8e8af0264bc630f4b27a7f7`; the batch helper is `bdb1bb90ced2674a51bbbbeaf140212378bbb255df5ae977bfdbcbf0ad5185ef`. The previously reviewed RTL adapter hashes are unchanged. No production source was edited and the 110-test regression was not repeated.

## Initial findings resolved

- **G1:** Lines 290-292 now require the independently requested SET/RAMP structure before interpreting commands.
- **G2:** Lines 190-194 construct requested times from case constants; lines 239-242 compare GUI committed times to that reference.
- **G3:** Lines 293-298 require the exact AWG command count and explicitly validate the allowed startup zero SET.

The final helper also independently checks matrix arithmetic, DAC/constant-increment rounding, fine plateau/tail mode and gain, envelope address and active/zero samples, and the explicit 30-clock RF command offset. Fine waveform width is not described as measured; the model checks commands and uploaded envelope memory. No additional blocking source-review finding remains.

## Preserved failures and unsupported input

Two SET-only GUI construction cases remain **unavailable**, not PASS. The tested mixed-matrix zero-ramp edit reaches the production invalid-edit warning path (`DCWaveform_Generator.py:2190`) and the offscreen process records an access violation in `gui_cases/smoke_set.log`. The identity version was not executed because the same zero-time transition is incompatible with the current strictly increasing waveform representation. This is a limitation of that exact GUI input, not a claim that all compiler/RTL SET commands are unavailable. No production fix was made.

The initial multi-window runner also exposed a pending scroll callback using a deleted QScrollArea (`DCWaveform_Generator.py:2450`, `gui_cases/smoke4.log`). The final runner uses one process per case; this isolates lifecycle effects but does not claim the production callback was fixed. Initial evidence is retained.

Earlier RF input attempts left the default 50 MHz/1 us values unchanged. The revised helper reveals the correct tab, ensures visibility/enabled state and focus, enables sweeps before typing their bounds, and verifies the committed values. The preserved `batch_smoke_input_fixed.json` contains three passes and one intended rejection, all exit0. The complete final batch was still running when this source review was frozen; its final counts and all process exits must be checked separately. A child exit0 by itself is insufficient because the helper can record a failed case and exit normally.

## Scope retained

The new coarse/fine RTL adapters compile fresh GUI input and current source into PMEM/DMEM/envelopes. Proven simulation infrastructure is reused; previous test inputs and PASS results are not replayed. Coarse matrix arithmetic is independent for initial SET targets, but other raw RTL expectations use compiled commands. Fine RTL active-width counts use independently requested sample counts; start times use model command cycles. The full 38-case GUI grid is a Qt-to-compiler-to-instruction-model grid, with separate representative actual RTL runs.

No live Run worker, board upload, scope waveform, analog timing/frequency measurement, ADC/FIR acquisition or zero-offset AWG/RF simultaneity was performed. Register-arithmetic fine duration and sweep grouping remain unavailable. See `independent_review_final.json` for reviewed file hashes and exact evidence references.
