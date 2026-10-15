# Fine RF compiler review

All changes remain in the staging directory.

- Initial focused execution exposed an incorrect MRO: the old concrete methods shadowed the new mixin. The final program class now wraps the unchanged coarse class with the fine mixin first. Fine-disabled compiler byte equality was checked separately.
- One initial periodic-boundary test incorrectly expected a 65535-clock plateau to require periodic mode. 65535 is legal oneshot, so the test boundary was corrected without changing the duration rule.
- Manual review found overlap-readout DC compensation using the fine masked-tail start as RF end. The new override waits for the maximum padded RF endpoint across hardware coordinates. Two executed tProcessor cases cover fixed and swept RF extending beyond HOLD.
- Periodic long plateaus stop only at three-clock boundaries; the tail now includes three to five full words, preserving arbitrary lengths without a FIFO boundary delay.
- Short envelopes occupy at least three clocks. Exact active duration is distinct from padded generator busy time and is explicitly reported.
- Pattern envelope multiplication uses doubled gain and can differ from a DDS-only plateau by integer quantization. Gains above 16383 in magnitude are rejected.

Final manual audit and focused validation:

- 197 tests PASS: 132 new fine compiler checks, 16 legacy oneshot checks, and 49 non-Qt DDR/DC timing checks. Four GUI-dependent tests were excluded here; root owns the full affected suite.
- Fine table timing now includes final AWG pre-compensation SET-zero, DDR readout control, and ordinary readout control when they share a timed port. Conflicting commands fail compilation.
- Actual compact RTL exposed initial area-clear commands becoming late with many RF events. Each fine event unnecessarily emitted five initialization register writes before the existing fixed-time clear. Removing those unused writes keeps the startup instruction prefix independent of the number of fine events; each output event still initializes every required register immediately before use. Original failed RTL evidence is retained by the RTL task.
- The new startup regression initially assumed the first instruction was synci; the mock firmware instead starts with a shared counter initialization. The corrected assertion compares the complete startup instruction prefix between one and 33 events. No program behavior was weakened.
- Exhaustive signed DDS values (-32768 through32767) at gains ±4000 and ±16383 give maximum absolute plateau-versus-product quantization error of one DAC code. Exact formulas and all results are in gain_quantization_exhaustive.json. Nonstandard SGv6 maxv values are rejected because the doubled-gain normalization assumes32766.
- Square updates run before the point timeline with their existing guard/synci. RC reset, final mute, and end markers run after the output completion barrier. The new feature does not perform MMIO updates per sweep point; normal envelope preload is used once.
- Fine mode preserves phase-reset=0, applies the same frequency/phase word to plateau and tail, and rejects gain beyond the signed doubled-gain range.
- Fixed-duration start times remain fabric-clock aligned; only active ending time is sample-granular. Fine hardware duration sweeps require a fixed HOLD anchor; swept HOLD extension is explicitly rejected.
- All source modifications remain in staging. final_compiler_source_hashes.json identifies the final source tested by this focused run.

## Subsequent actual-RTL instruction-throughput correction

The startup correction alone did not close actual RTL timing: the compact33-event fixture first missed RF port2 timestamp2044 (observed2048), then consecutive long tails became later. These original failures are retained under the isolated compact2 RTL evidence.

The previous emitter rewrote the full carrier and duration row before every tail, including short cases that emitted no tail command. The corrected emitter omits all-short tails at compile time, writes exact start registers without default addr/mode overwrites, and reuses preserved carrier/address registers for the tail. Dynamic tails directly use mode2/addr2 in SET. A per-generator ownership check rejects any unexpected intervening same-generator state overwrite.

After this correction,199 focused checks PASS (134 fine,16 legacy oneshot,49 DDR/DC). The before/after requested RF command streams are identical in four additional behavior-model cases; instruction counts are recorded in throughput_command_equivalence.json. This equivalence does not prove actual RTL issue deadlines; strict RTL command-time checking remains required.

Actual RTL confirmation of the throughput correction: F:/Vivado_Output/a5fine_rtl_compact3/composite_short_gain4000/result.json is passed=true. The unchanged strict command-time/value oracle passed all three RF/AWG pairs and both repetitions, including short widths1/15/16/17/47/48/49/95, width97 plateau+tail, and negative4000/maximum16383 gain. Exact active windows and summed lanes passed. This confirms zero tardiness for this compact case. The separate phase and full hardware-sweep RTL matrix remain gated by their own reports.

## DDS capability guard after frozen-source review

The independent review found that has_dds=False bypassed the normal manager capability check in the fine emitter. After freeze release, the helper now requires has_dds is True; emitted-command code is unchanged. The exact09fd source and its evidence are preserved separately. Final helper18d262cf passes201 focused tests (136 fine,16 legacy oneshot,49 DDR/DC) with4 GUI-dependent deselected. Seven independent bounded checks were repeated successfully. See INDEPENDENT_REVIEW.md and independent_review.json.
