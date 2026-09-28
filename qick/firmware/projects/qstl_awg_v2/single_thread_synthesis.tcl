# Avoid the stalled Windows parallel-synthesis helper seen during DDR recovery.
# This changes host synthesis concurrency, not FPGA clocks or timing constraints.
set_param general.maxThreads 1
set_param synth.maxThreads 1
