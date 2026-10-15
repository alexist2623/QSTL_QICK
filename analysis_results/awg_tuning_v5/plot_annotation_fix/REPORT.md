# AWG edit feedback, voltage dragging and RF pulse labels

User-requested display/editor correction, 2026-10-14. Both repositories remain
on awg_tuning_v4; no RTL, XDC, timing compiler, driver or firmware was changed.
No running GUI/server was restarted and no board action was performed.

## Changes

- Preserve an active HOLD voltage/time drag when the deferred preview refresh
  remains in the editable base waveform. Previously that refresh cleared the
  drag flags, stopping the edit and leaving its annotation visible.
- Clear annotation and cursor on release, actual preview/view/output changes,
  hide/deactivation and lost mouse capture. Recover a lost release on a move
  with no left button held. Final scene teardown tolerates already deleted text.
- Center RF pulse names inside the envelope at y=0, with compact text padding.

HOLD voltage is edited by dragging the middle of the horizontal HOLD line up
or down. Endpoint dragging continues to edit time. This correction preserves
these existing interaction meanings.

## Verification

- `targeted.xml` / `targeted.log`: 79 passed, process exit0, explicit Qt teardown
  complete, no Qt callback exceptions. Includes 16 new event/geometry cases.
- Real MainWindow tests for both selected AWG outputs: repeated vertical moves
  across the deferred refresh update the selected HOLD, its table and exported
  sequence amplitudes. Times, other HOLDs and the other AWG are unchanged.
- Real viewport mouse events exercise time dragging, cancellation, release,
  interrupted capture, and switching display mode during an edit callback.
- RF carrier/envelope label bounds are checked at the minimum lane height.
- Current GUI/compiler inputs regenerated in `F:/Vivado_Output/a5gui_plotfix2`:
  all nine cases have identical PMEM/DMEM to the running v5 RTL replay input.
  See the parent `compiler_equivalence.json` and `compiler.log`. No new RTL
  simulation or synthesis was launched for this display-only correction.
- `waveform_labels.png` was rendered offscreen with an installed Segoe UI font
  and opened for visual review. The user's live GUI was not used or restarted.

## Broader check and separate outstanding issue

The larger five-module run had 157 passing test assertions, but the strict Qt
callback check returned exit1 for a separate `KeyError: 'd1'` in RF duration
parameter renaming. Therefore this broader run is **not an overall PASS**.
Full evidence is in `tests.log` / `tests.xml`.

Static inspection of unchanged `DCWaveform_Generator.py` shows duration-name
textChanged triggers spec collection before editingFinished updates the pulse's
duration-parameter reference. The dictionary has the new name while the pulse
still references d1. This is separate from the plot fixes and was not modified.
Original-widget isolated reproduction terminated during Qt startup with
0xC0000409, so runtime reproduction against that backup is not confirmed;
the reproduction scripts/logs are preserved, not presented as passing evidence.

The first display run is also preserved as `initial_tests.log/xml`: RF label
geometry failed at minimum height and final scene teardown raised deleted-text
exceptions. Compact label padding and guarded teardown fix these; the test
runner additionally loads an actual font because the offscreen platform exposed
no system fonts. All 79 affected regression tests then passed without exceptions.

## Build evidence preservation

The original widget, authorization, compiler proof, compiler harness and logs
are preserved here with before/initial names. `protected_before.json` remains
unchanged. The exact hashes of the user-authorized widget/test changes are added
to `authorized_gui_fix.json`; no broad source exception is introduced.
The existing compiler harness only gains a selectable external output directory
so the new proof does not overwrite earlier compiled input files.
The v5 scheduled build review still begins at 23:02:58 local, every ten minutes.
