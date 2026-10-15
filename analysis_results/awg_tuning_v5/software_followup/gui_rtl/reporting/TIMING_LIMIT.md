# v5 shared-port timing diagnostic

The production GUI/compiler rejects a zero-offset HOLD SET + RF pair on the same tProcessor port. Eight real MainWindow negative cases (first/second HOLD × RF channels 0,2,4 individually/all together) retain the original three-clock guard. These are expected-rejection checks, not successful simultaneous output experiments.

A separate low-level diagnostic deliberately emits identical timestamps through the existing real tProcessor/TMUX RTL. It does not change or bypass the production GUI guard in application code. Across all three ports and both command orders, the first command is delivered on time and the second command is delivered 3 fabric clocks later. At 300 MHz this is 10 ns. The native AWG/RF latency remains equal at 31 clocks; identical native latency does not remove shared dispatcher serialization.

| Raw command order | First lateness | Second lateness | Inferred RF minus AWG physical start |
|---|---:|---:|---:|
| AWG then RF | 0 clocks | 3 clocks | +3 clocks (+10 ns) |
| RF then AWG | 0 clocks | 3 clocks | −3 clocks (−10 ns) |

The diagnostic directly observes tProcessor dispatch and the AWG/RF sum-input edges. The physical component timestamps are **inferred** using separately verified downstream delays (AWG 25 clocks, RF 12 clocks to final output), because two components cannot be observed separately after addition. The actual sum output is independently checked on every lane; its oracle reports zero errors. The diagnostic result is in `F:/Vivado_Output/a5post_fine_rtl1/raw_same_timestamp/result.json` and the immutable input/RTL traces are beside it.

The legal first/second HOLD tests explicitly request RF **100 ns after the actual HOLD SET anchor**, with RF width **9.9 us**, inside the 10 us HOLD. Their `requested_timing_error_cycles=0` means that explicit anchor-relative request passed. It does not assert exact zero-offset operation or erase the existing 7-clock RAMP startup and one-clock guard. The 10 us RAMP/HOLD/RAMP/HOLD settings remain represented by the real GUI; no source timestamps are silently moved.

Fine RF pulse **duration** is on the 1/4.8 GHz = 0.208333 ns sample grid. Start/delay scheduling remains on the 1/300 MHz = 3.333333 ns fabric grid. The additional requested-parameter audit uses the actual production ceil-to-cycle rule, records raw input, GUI-normalized values, quantized delay cycles, and compiled command timestamps, and observes no cycle differences for its five fixtures. Each GUI duration/delay editor keeps 9 decimal places in microseconds; cumulative roundoff is bounded by the sum of per-editor half units. Earlier audit attempts that incorrectly used round-to-nearest are preserved separately.

No board access, analog measurement, RTL/XDC modification, or new synthesis was performed by this diagnostic.
