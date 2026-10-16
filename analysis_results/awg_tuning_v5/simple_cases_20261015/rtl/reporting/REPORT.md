# Fresh representative GUI to v5 RTL tests

All four fresh executions passed. This report covers observed digital simulation output, not physical board/scope measurements.

| Case | Points | Repetitions | Commands | Final DAC lane checks |
|---|---:|---:|---:|---:|
| hold_fixed_time | 4 | 2 | 233 | 882576 |
| ramp_fixed_time | 4 | 2 | 233 | 830448 |
| rf_frequency | 4 | 2 | 233 | 782064 |
| fine_duration94_97 | 4 | 2 | 205 | 1313856 |

Total: 16 points, 32 shots, 904 observed tProcessor commands; 3818544 sum-lane checks and 3808944 final-DAC-lane checks.

The first three cases enter the nonidentity 3x3 matrix and AWG sweep controls through actual Qt dialogs; RF settings are loaded through MainWindow settings. Fresh MainWindow Run Experiment input is compiled, and GUI/generated PMEM/DMEM match byte for byte. Independent C@V/integer-increment targets match the executed SET payload on all three ports. Raw AWG, IIR recurrence, DC area/reset, RF and sum/final slices are checked.

The exact grids are HOLD duration 1.0/1.9us x virtual AWG0 voltage 5/15mV; RAMP duration 0.1/0.4us x 5/15mV; RF0 frequency 180/225MHz x 5/15mV. Each Cartesian grid has four points and two repetitions. The last two RF ports remain at 190MHz in the coarse cases. Matrix coefficients and unequal 800/400/800mV channel scales are retained in independent_matrix_oracle.json.

The fine case loads actual MainWindow settings and commits RF0 duration start/stop/count through Qt keyboard input: 94, 95, 96, 97 DAC samples, each twice. RF2/RF4 remain 97 samples. All three use 0MHz/gain4000 for unambiguous exact active-window checks. Requested sample count is the independent width oracle; start time is checked against compiled/model command time plus the measured tProcessor offset and the established 32-cycle path. Real host AXI/AXIS transactions load the SG-v6 envelope BRAM; no hierarchical memory injection is used. Fine length spacing is 0.208333ns while command starts remain on the 3.333333ns fabric grid.

Offscreen Qt screenshots may omit text due to rendering limitations. Values are verified from committed settings, actual runtime specifications and PMEM/DMEM, not by reading screenshot labels. The two reporting PNGs are plots of numeric digital RTL traces.

RF +100ns offset is an explicit test input in all four cases. Exact simultaneous AWG/RF start is outside this test request. This is a new compilation and new RTL execution, not replay of previous PMEM results.

All 70 numeric trace files are archived losslessly, with original hashes, byte/row counts and decompressed hash verification. Originals remain at the external execution folders. See archive_manifest.json for per-file paths and hashes.

Initial failures: none. Controller logs, source/input fingerprints and static source hashes are retained. Mutable log/status hashes recorded at intermediate case completion are historical observations, not current source gates.

No production Python/RTL/XDC/user settings, firmware, board or live GUI process was changed. No new synthesis was run. Native logarithmic sweep, grouped sweep lifecycle and fine-DMEM compression remain future TODO work.
