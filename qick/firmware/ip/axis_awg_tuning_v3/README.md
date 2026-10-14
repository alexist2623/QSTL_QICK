# AWG tuning v3 — shot area before the RC IIR

Implementation and system integration are in progress. Do not deploy this source
with the v2 BIT/HWH. Full-project timing closure and RF/DDR integration evidence
are required before publishing v3 firmware.

The 160-bit SET/RAMP ABI remains v2: signed 32-bit Q18 step, 16 parallel samples,
16-bit transport with 14 effective DAC bits. The new DC engine sums the actual
effective samples before the IIR. It does not sum RC-corrected DAC ramp/offset
area and does not change the existing integer voltage sweep increment policy.

## Width decision

The same 100-point voltage sweep was run in both DC modes for 32/48/64-bit area
registers, followed by the production IIR and an independent analog RC model.
The 48/64-bit numeric results match for all 200 shots. Both have exactly zero
digital residual area; 32 bits overflowed in 34 shots. Per user direction the
packaged IP fixes `DC_AREA_BITS=48`. This stores about 3.579 seconds of full-scale
one-sign samples at 4.8 GSPS. Every-prefix software validation and a hardware
overflow fault are required. The internal Q64 reciprocal and the existing
Q48/72-bit IIR state have different roles and are unchanged.

Historical width-selection CSV/plots/report:
`analysis_results/awg_tuning_v3/width_comparison/` at repository root.
The current production regression runs only 48 bits (`--width 48`); its results
are published separately under `selected48_validation` when complete.

## Commands and compensation

IDLE opcode (`145:144=3`) plus bit 150 selects DC commands; bit 149 remains RC.
Bits `147:146` select ARM (0), fixed voltage (1), fixed time (2), DISABLE (3).

- ARM/DISABLE: raw AWG output must already be zero and the pipeline drained.
- Fixed voltage: word 0 is a positive aligned transport amplitude. The engine
  emits opposite-polarity full samples and at most one partial scalar sample,
  then pads the last 16-lane word with zero.
- Fixed time: word 2 is the positive fabric-word count. Words 0/1 contain
  `floor(2^64/(16*word_count))`, calculated in Python. Pipelined multiplication,
  integer remainder correction, and adjacent DAC codes cancel the area exactly
  within the given word count. No RTL division is used.
- Every completed shot sends a zero word through the IIR for the final
  trapezoidal edge before clearing area and IIR history. This does not reset the
  physical analog capacitor; the RC validation retains that state across shots.

In the current verified RTL, normal/bypass latency is 5 clocks for the area
engine plus 11 for the existing IIR. DC begins 17 clocks after its command is
accepted and has two zero/reset clocks after the last word. Pipeline changes
for timing closure must update these values and repeat timing tests.

The routed-build correction registers the next compensation word and its signed
area delta one cycle before emission. The planner advances the unqueued tail,
while the ledger changes only when a registered word is actually emitted.
PREPARE fills this register before EMIT, preserving the 17-clock startup.
Capturing the final raw area and converting its absolute value use separate
cycles. Overflow uses an 18-bit low carry plus the signed upper-boundary pattern;
the area itself remains a full-width exact accumulator. These changes require
new GUI/RTL evidence and do not claim that the first full build closed timing.

The next routed-path correction precomputes signed amplitude/base/base+1 during
PREPARE and uses a single directed subtraction for a partial voltage lane.
Fixed-voltage remaining-area feedback no longer depends on the fixed-time
remainder. The -2^63 guard is generated only for the 64-bit test candidate.
Existing SET/override/RAMP and SquarePulse arithmetic has been restored to the
original v2/shared logic per user direction. Only the new pre-IIR area engine is
changed for timing. The 16/17-clock external latency contract remains unchanged.
`legacy_logic_guard.py` checks 53 protected source files before publication.
The second routed build still failed setup (-0.092 ns); these corrections need
fresh functional evidence and a new complete routed build before publication.

Status bits 16/17/18 are enabled/busy/fault. Overflow does not wrap. Nonzero raw
input or conflicting commands during compensation latch a fault and do not
count a completed shot. ARM/DISABLE or AXI stop clears the fault.

## Validation scope

`validation/run_width_comparison.py --width 48` runs the selected engine's long
scalar RC validation. Do not rerun width selection for the current task.
`run_unit_bench.py` supports production SET/RAMP/IIR, arithmetic boundary,
short-compensation, invalid-command, and abort tests. Boundary tests that seed
the area register directly are arithmetic tests, not hours-long waveform runs.
`run_ooc_widths.py` defaults to the selected 48-bit engine at 300 MHz; an OOC
pass alone does not establish complete FPGA timing closure.

`rc_precomp_validation/verify_gui_rtl.py --awg-v3 --verify-gui-widgets` also
restores real MainWindow inputs, calls the Run Experiment compiler path, and
requires byte-identical PMEM/DMEM before the actual tProcessor/TMUX/RF/DDR RTL
run. `validation/report_system_validation.py` collects all 100-point results.
The independent monitor counts every pre-IIR DAC sample, checks each shot's
digital residual and reset, and retains first-sample/width/capture timing.
DDR tests use timestamp samples at the FIR cadence, not measured ADC data.
