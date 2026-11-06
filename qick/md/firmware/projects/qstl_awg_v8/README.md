# AWG Tuning v8: DDR abort and output limits

Branch: `awg_tuning_v8`. This project is derived from the three-AWG v7 project.
DAC4/5/6 retain AWG + RF, DAC7 retains Square Pulse, and DAC8/9/10/11 retain digital zero.
The AXI master count remains 34. Existing v7 IP, project and firmware are unchanged.

## DDR capture abort

`axis_buffer_ddr_sample_v4` retains the IQ64 format and v3 register layout and adds one
32-bit register at byte offset **0x38**. The current BD maps it at **0xA00A0038**.
Software obtains the base from HWH; do not hardcode physical addresses in applications.

| Offset | Write | Read |
|---|---|---|
| 0x38 | bit 0 = request abort | `0xAB040000`, bit 0 pending, bit 1 acknowledged |

Stop the trigger producer first. Abort rejects additional capture triggers, clears the
trigger queue and partial sample pack, and drains an already issued AXI write through
its AW/W/B handshakes. Only after the source is quiescent and outstanding writes have
finished are both FIFO domains reset and acknowledged. ARM is ignored while abort is
pending; STATUS busy also includes abort pending. Duplicate requests are ignored until
the first completes. The previous CONTROL bit 1 soft-reset command aliases this same
safe abort protocol; it no longer withdraws a live AXI transaction.

Abort does not erase DRAM, reset the MIG controller or reset the entire FPGA. A cancelled
capture is invalid data even if some samples reached memory. If the AXI slave does not
respond, abort remains pending and the driver raises a timeout; it must not report a
successful stop or attempt another ARM. A request while idle is also acknowledged.

Driver API: `soc.abort_ddr4_capture(timeout=2.0)`. Status includes `pending`,
`acknowledged`, `busy`, and `armed`. The driver checks the v4 register signature.

## AWG output clipping

`axis_awg_tuning_v8` clamps each of the 16 scalar DAC lanes **after DC/RC compensation
and before the RF sum**. Thus these are AWG limits, not limits on AWG + RF or on an
external amplifier. No register stage was added to the sample path: core latency 11,
AWG wrapper 27 and combined AWG/RF output latency 31 clocks remain unchanged.

| Offset | Meaning |
|---|---|
| 0x00, 0x04 | Existing override and status, unchanged |
| 0x08 | Minimum signed 32-bit shadow code |
| 0x0C | Maximum signed 32-bit shadow code |
| 0x10 write | bit 1 APPLY, bit 0 ENABLE |
| 0x10 read | `0xC1080000`; bit 0 enabled, bit 1 pending, bit 2 config error, bit 3 clipped sticky |

Bounds are effective DAC codes (multiples of 4), within -32768..32764, and must include
zero so idle/stop can output zero. Default is disabled/full range. APPLY transfers both
bounds and enable atomically across the clock domains and clears the clipping sticky
flag. Invalid bounds return SLVERR and leave the active configuration unchanged.
The bound registers are shadows; after a completed APPLY their values match the applied
configuration. Do not modify the shadows concurrently with another client.

Driver API: `soc.set_awg_output_limits(ch, min_code, max_code, enabled=True)` and
`soc.get_awg_output_limits(ch)`. The setter validates, applies, waits for acknowledgement
and checks readback. The IP's ordinary status also exposes enable/sticky at bits 10/11.

Clipping does not modify the DC-area or RC integral. It can change charge balance and
the compensated waveform; no anti-windup or physical voltage accuracy is claimed.

## Verification and publication

RTL checks cover abort during missing triggers, partial packs, independent AW/W stalls,
B-response stalls, duplicate requests, queued triggers, random clock phases and a fresh
capture after every abort. Clipping checks cover all lanes, signed bounds, atomic commits,
invalid bounds, fine RAMP edges crossing a word boundary, RC/DC compensation and override.
The previous SET/RAMP/DC/timing regression and full-CPU fine-edge/legacy vectors also run.

The build scripts require the recorded functional gate and frozen source hashes before
synthesis. BIT/HWH/XSA publication requires post-route timing and artifact-pair checks.
The final build manifest records the actual results; starting synthesis is not a pass.
No board deployment or physical measurement is performed by this implementation task.

### Routed validation, 2026-11-06

The `a8full02` implementation meets the unchanged v7 timing constraints: setup WNS
0.036819 ns, hold WHS 0.009329 ns, zero setup/hold/pulse-width failing endpoints,
14/14 bus-skew checks met, and zero routing errors. The build manifest and matching
XSA identify the published artifacts; a successful routed report alone is not a release.

| Post-route resources | Previous v7, three AWGs | v8, three AWGs |
| --- | ---: | ---: |
| Whole-design LUTs | 234,976 | 236,770 |
| Whole-design FFs | 320,581 | 321,326 |
| Whole-design DSPs | 2,456 | 2,456 |
| Whole-design BRAM tiles | 442.5 | 442.5 |
| AWG IP LUTs, three instances combined | 58,548 | 60,413 |
| AWG IP FFs, three instances combined | 39,095 | 39,652 |
| AWG IP DSPs, three instances combined | 342 | 342 |

Existing constraint/CDC warnings remain: four inputs and 24 outputs have no I/O delay,
and the implementation retains the same 68 critical-warning codes/counts. There are
no clockless or unconstrained internal endpoints. Methodology warning text matches
v7 after IP-name normalization. Two additional DSP input-pipeline warnings occur in
vendor RF DDS phase-accumulator lanes 2 and 5; all constrained paths still meet timing.
This is not a claim that all CDC/I/O constraints or physical operation are qualified.


## Measurement-free output loop

The matching GUI has a separate Run forever action. It compiles a repeated complete
reps × hardware sweep grid with no ADC/DDR acquisition and a shot-boundary zero-output
stop epilogue. The server API owns a renewable lease (`begin_output_forever`,
`renew_output_forever`, `stop_output_forever`, `output_forever_status`) and prevents
another AWG Tuning/Stability program configuration while that session is active or
locked after cleanup failure. This is not global arbitration of every manual output
API or other client connected to the board.
The tProcessor program reserves DMEM words 2/3 for stop request/acknowledgement; these
are software mailboxes, not additional AXI registers. Runtime tables begin at 16 and
spilled sweep state is checked not to overlap the mailboxes.

The compiler inserts an instruction-preparation gap at each shot and grid boundary
after checking Stop. Its cycle/time value is recorded in program metadata and the
start log. This keeps short fine-edge commands on time after the wait, while retaining
the relative pulse/compensation timing inside a shot. The resulting repetition period
differs from finite acquisition mode; this is not gap-free waveform playback.

The watchdog runs in board Python. It handles a lost host lease while the server and
FPGA remain operational. No independent analog-zero or failed-server safety guarantee
is made. See the GUI document for lease, timeout, output and verification limitations.
