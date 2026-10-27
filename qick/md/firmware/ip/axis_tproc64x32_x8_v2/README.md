# Queued timed dispatcher (IP version 2.0)

This IP retains the tProcessor ISA, top-level module, port names, memory ABI,
CPU instruction controller and upstream timed FIFO from version 1.0. Its VLNV
is `QICK:QICK:axis_tproc64x32_x8:2.0`. Use this core in a separate project; do
not compile both versions' identically named internal modules into one design.

The dispatcher prefetches the synchronous BRAM FIFO into two local entries and
reserves space for its pending read response. One registered output stage
issues queued commands on consecutive clock cycles. An instruction already
queued for timestamp T is compared at the edge with t_cnt=T, becomes valid
after that edge and is sampled downstream at t_cnt=T+1. This is the same
registered timestamp-to-output latency as version 1.0; no pipeline stage is
bypassed and no timestamp is rewritten.

## Instruction behavior

- SET and SETI produce one clock of valid regardless of ready, preserving their
  nonblocking ISA behavior. SETI zero-extends its 32-bit payload.
- SETB and SETBI retain valid and the complete payload until ready is asserted.
- WAIT and WAITI retain waitt until waitt_ack, blocking later commands on that
  channel. They do not flush the prefetch queue.
- Equal and late timestamps retain FIFO order. At most one command per channel
  can be issued each clock; equal timestamps cannot produce simultaneous
  commands on the same channel. An unknown opcode is consumed without output.
- A synchronous reset clears the prefetch, pending read and registered issue.
  The counter's reset/epoch policy is unchanged: changing t_cnt alone does not
  flush commands. Programs must drain an epoch before restarting without rstn.
- Timestamp comparison remains unsigned 48-bit comparison, not modular ordering
  across wraparound. A paused counter does not prevent already-due commands.

Consecutive output requires commands to arrive early enough. This does not
increase the CPU instruction issue rate or make FIFO capacity unlimited. Cold
arrival into an empty queue includes one additional prefetch-register clock
relative to v1, so an already-late command is not a fixed-latency operation.
The original external FIFO is unchanged; local prefetch adds up to two buffered
instructions in addition to the registered issue. Downstream TMUX, AWG, DDS and
sum pipelines must be validated in the complete system separately.

## Validation

`src/tb/run_timed_unit.ps1 -BuildDir F:/Vivado_Output/a6timed_unitNN` creates a
fresh isolated xsim compilation library and preserves logs, source hashes and
CSV output events. Vivado 2023.1 defaults to F:/Xilinx/Vivado/2023.1; override
-VivadoRoot when necessary. Existing output directories are rejected.

The test uses the actual synchronous BRAM FIFO, compares isolated operations
against a verbatim v1 dispatcher with only its entity name changed, and checks
consecutive timestamps, equal/late order, empty FIFO, blocking and nonblocking
ready behavior, WAIT acknowledgements, reset, counter rollback/pause and
unsigned 48-bit timestamps.

`validate_package.tcl` refreshes and validates only this new core's packaging
checksums. The v1 core is preserved. Python driver binding for the new VLNV is
a separate integration task; this IP does not modify host software.
