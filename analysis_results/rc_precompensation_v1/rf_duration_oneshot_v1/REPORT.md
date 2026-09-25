# Direct RF duration RTL verification

Short RF pulses use their direct one-shot length. A duration axis uses periodic mode throughout if any executed point exceeds 65,535 generator clocks.
All four fixtures executed the production tProcessor/TMUX/AWG/RC/RF DDS RTL. RFDC and ARM are not included.

| Fixture | Points x repeats | RF mode | Widths (clocks) | Maximum requested-width error |
|---|---:|---|---|---:|
| short_extend | 400 x 2 | one-shot | 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125 | 0 clocks |
| short_fixed | 400 x 2 | one-shot | 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125 | 0 clocks |
| limit_oneshot | 4 x 2 | one-shot | 65534, 65535 | 0 clocks |
| limit_periodic | 4 x 2 | periodic (retained long-pulse behavior) | 65535, 65538 | 2 clocks |

- The GUI/shared-compiler software suite passed 229 tests before these RTL runs.
- Both full short-duration grids emitted 800 RF pulses each. Every requested length, including 35 and 40 clocks, matched the actual RF output width exactly.
- The boundary one-shot fixture checked 65,534 and 65,535 clocks. The periodic fixture checked 65,535 and 65,536 clocks, with all points in periodic mode.
- Long periodic output retains its block-boundary stop: 65,536 requested clocks produce 65,538 output clocks. This is preserved behavior, not an exact-timing pass.
- Every emitted command word and timestamp matched the instruction model. Both AWGs matched the independent RC integer recurrence and passed all per-repeat resets.
- Short-grid waveform traces are bounded to the first 12,000 clocks; command and sample checks cover every point. Boundary fixtures keep AWG values zero to isolate RF mode selection.
- The existing AWG voltage increment error and analog RC residuals are separate from this RF duration change.
- No production RTL, firmware bitstream, or physical RF calibration was changed by this fix.

Raw simulator outputs remain at the per-case paths recorded in status.json. Prior failing-duration evidence is retained unchanged.

## Analog RC residuals

These values compare the independent analog RC model with the delayed, quantized nominal AWG output. They are not RF pulse-width errors or a claim of zero analog error. Tau is 10 us; analog capacitor state persists across digital resets.

| Fixture | AWG 1 maximum error (mV) | AWG 2 maximum error (mV) |
|---|---:|---:|
| short_extend | 0.283945 | 0.113370 |
| short_fixed | 0.244093 | 0.060728 |
