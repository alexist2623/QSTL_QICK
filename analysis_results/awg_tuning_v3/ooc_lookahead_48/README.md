# Compensation lookahead pipeline: area-engine OOC only

300 MHz / 48 bits: setup +0.397 ns; internal hold +0.029 ns. The all-port virtual-boundary hold is -0.080 ns and is preserved in the report. This is not a full-FPGA timing-closure result. Real clock placement, upstream data and seven-instance routing must be verified in the whole design.

Four unit benches passed after this pipeline change. The full GUI/system and 32/48/64 analog-RC comparisons are being repeated. First full-build failure and earlier system evidence remain in ../timing_failure_r1.
