# v5 software follow-up after successful build

Authorized by the user on 2026-10-14: review the build starting three hours later,
every ten minutes; after verifying success, modify Python and GUI support.
This note records read-only preparation. No software changes or extra test runs
were made for this preparation, and current build results were not inspected.

## Entry condition and scope

Require the existing workflow to finish successfully, with final routed timing,
matching candidate BIT/HWH/XSA, and unchanged functional source/evidence hashes.
Preserve these original snapshots before edits. Store subsequent software proof
separately. Use existing `awg_tuning_v4` branches, not new branches. No commit,
push, board access/update, GUI/server restart, RTL/XDC change or rebuild.
Functional or timing failure means stop/report without this software follow-up.

## Version-specific integration

- `qick/qick_lib/qick/output_sum.py`: recognize v1 and v2, validate the actual
  v2 parameters including AWG_DELAY_CYCLES=13. AWG v2 latency is16+13+2=31;
  RF is29+2=31. Preserve v1 AWG18/RF31 and no-combiner behavior. Repeated
  configuration must subtract the previously applied full extra latency.
- `qick/qick_lib/qick/ip.py`: recognize v2 during forward traversal.
- `qick/qick_lib/qick/dac_current.py`: validate consistently versioned HWH-linked
  pairs for v1/v2.
- GUI `qick_fine_tune_sweep.py`: segment anchors and RF timing already consume
  output_latency_cycles. Correct v5 metadata should remove the relative v4
  13-clock advance only for v5. Preserve original seven-clock RAMP startup,
  occupancy, command-arrival semantics and DC compensation behavior.
- GUI `qick_front_panel.py`: extend version1-only summed/baseband output consumers
  to verified v2 metadata while retaining the completed shared-DAC AWG selector fix.
- GUI `qick_update.py`: validate v5 topology in firmware selection, without
  initiating a board update or automatically selecting v5 for the running GUI.

## Shared-port timing issue requiring proof

Read-only review of the existing v4 HWH and BD, whose BD source matches v5,
confirmed the three pairs share tProcessor ports:

| AWG suffix | RF suffix | tProcessor output | AWG / RF TMUX outputs |
|---|---|---|---|
| 4 | 0 | m1 | m1 / m0 |
| 5 | 1 | m2 | m1 / m0 |
| 6 | 3 | m3 | m1 / m0 |

Each command path has one register slice. v5 changes the output stage, not this
routing. BD references: v4 `bd_2023-1.tcl` lines2543–2557,2578–2583,2595–2597.

With equal native latency, ordinary zero-offset HOLD/SET plus RF requests yield
equal shared-port timestamps. Existing compiler guards reject spacing below
three clocks (`qick_fine_tune_sweep.py` near5327 and5764). Thus equal native
latency and updated metadata alone do not prove simultaneous physical output
for these GUI requests. Verify actual tProcessor/TMUX command acceptance and
physical output boundaries; do not weaken guards or silently move timestamps.
If exact requested timing cannot be achieved under the fixed RTL/routing,
report the limitation rather than claim completion or modify the built RTL.

## Required postbuild verification

1. v1/v2/no-combiner HWH fixtures, all seven AWG outputs including four bypasses,
   three RF pairs, invalid parameters, idempotent configuration, legacy behavior.
2. Compiler/GUI tests for exact requested boundaries, zero-offset shared-port
   behavior, legal offsets, HOLD/RF duration sweeps, repetitions, RC and DDR.
3. Real GUI widgets/export -> compiled PMEM/DMEM -> actual tProcessor/TMUX,
   AWG/DDS and v2 sum RTL. Check accepted command cycles and output start/end,
   all16lanes and three pairs, including first/second10usHOLD RF and affected sweeps.
4. Existing v1 validation extension and `verify_gui_rtl.py` contain v1-specific
   source/oracle references. Use a validation-only v5 adapter that checks the
   delayed AWG contribution and sum output, not only raw pre-delay input edges.
   Replaying unchanged v4 timing inputs does not constitute this v5 GUI proof.

Record failures and environment-only retries distinctly. Keep the user's JSON,
prior successful/failed evidence and running hardware unchanged throughout.
