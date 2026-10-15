# Local v5 firmware package publication

The user requested that the built v5 firmware appear in the GUI update list.
Four new local files were copied into `qick/firmware/projects/qstl_awg_v5`:
`bitstream.bit`, `bitstream.hwh`, `bitstream.xsa`, and `build_manifest.json`.
No existing firmware was overwritten. No board connection, upload, overlay
load, server restart or live GUI restart was performed.

`result.json` records exact hashes, same-XSA BIT/HWH verification, HWH topology
checks, the previous routed timing result and the successful production
`review_package` result. The source v5 build was not repeated. The manifest links
the completed prior software integration and explicitly marks the newly
requested expanded validation as still running.

An isolated offscreen instance of the actual `QickUpdateDialog` found 20 local
firmware versions, including `qstl_awg_v5` mapped to
`projects/qstl_awg_v5/bitstream.bit`. Network access and `BoardUpdater.__enter__`
were forbidden during this check. The test exited 0 after explicit Qt teardown.
See `gui_discovery.json` and `check_gui_discovery.py`.

`build_manifest.json` is a custom GUI validation artifact, not a Vivado/QICK
requirement. The current GUI discovers matching BIT/HWH file pairs, not BIT/XSA
pairs. It does not extract HWH from XSA automatically. It additionally requires
a validated manifest for v5 update. These are separate from the board runtime's
need for a matching BIT/HWH pair and compatible QICK Python driver. Manifestless
BIT/XSA import has not been implemented or requested in this step.
