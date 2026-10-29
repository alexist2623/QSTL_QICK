# AWG tuning v7: sample-position RAMP

This is a separate project/IP revision. The v6 project, AWG v4 IP and output-sum
v3 IP remain unchanged. It adds no FAST_RAMP opcode: opcode `10` remains RAMP,
and command bit 151 selects the new payload. Legacy packets retain their ABI.

## Waveform contract

At the 300 MHz fabric clock a word contains 16 DAC samples: 3.333333 ns per
word and 0.208333 ns per sample. Times are integer sample indices, not rounded
decimal values such as 3.33 ns. One command describes one transition to a turn
voltage, an optional hold, and an optional transition to a terminal voltage.
Either transition may increase or decrease the voltage.

The initial voltage is the preceding accepted command's terminal state. For
an edge from `a` to `b` over `k` sample intervals, the signed Q18 increment is
`sign(b-a) * ceil(abs((b-a)*2^18)/k)`. The output is bounded to the target.
Both endpoints are included: indices 2 through 7 contain five intervals.
Quantization retains the existing effective 14-bit DAC code, a multiple of 4.
Different voltages at the same sample index are rejected by the encoder.

The rise begins at lane 0..15. Falling uses a word offset and lane; its slope
continues across word boundaries without restarting or snapping to its final
voltage. The total sample count includes the terminal sample; trailing lanes
and subsequent idle words hold that terminal voltage. `fall_start=None`
encodes `11111` (31), so lane 15 remains available as a real falling position.

RAMPs occupy `ceil(sample_count/16)` issue clocks. The next command can be
accepted on the next issue clock even while earlier words drain through the
pipeline. SET deliberately changes voltage discontinuously; it must not erase
an earlier RAMP's last word. Timed commands must already be queued: CPU work
that delivers a command after its timestamp is a different issue from AWG
throughput. The tested tProcessor v2 timed FIFO dispatches prequeued commands
one per clock, not one per three clocks.

## Extended 160-bit payload

| Bits | Meaning |
|---|---|
| 15:0 | Signed turn target, DAC code |
| 31:16 | Signed terminal target, DAC code |
| 66:32 | Signed first increment, Q18, 35 bits |
| 101:67 | Signed second increment, Q18, 35 bits |
| 105:102 | First-edge starting lane, 0..15 |
| 110:106 | Second-edge starting lane, 0..15; 31 disables it |
| 133:111 | Total scalar sample count, 1..8,388,607 |
| 143:134 | Second-edge starting word offset, 0..1023 |
| 145:144 | RAMP opcode, binary 10 |
| 150:146 | Zero in an extended RAMP |
| 151 | One selects this payload |
| 159:152 | Existing TMUX destination |

The second-edge start can be at sample 0..16,383. Its endpoint can be later,
up to the sample-count limit. A no-fall edge can use the full count range.
Codes must be multiples of 4 in -32768..32764. Maximum voltage depends on the
DAC current and analogue load; this RTL does not certify a voltage in volts.

## Pipeline and RF alignment

| Path | Cycles from its IP command input |
|---|---:|
| SET / legacy RAMP / extended RAMP core | 11 |
| AWG after DC (5) and RC (11) stages | 27 |
| Existing DDS path | 29 |
| AWG after added delay (2) and sum (2) | 31 |
| DDS after sum (2) | 31 |

The three retained AWGs on front-panel DAC4, DAC5 and DAC6 receive the same
two-clock alignment delay. DC/RC control tags are delayed with the core data.
The CPU fixture separately checks the tProcessor timestamp dispatch and TMUX
transport, rather than hiding those delays in an arbitrary RF offset.

Each lane splits the signed 35-bit slope into a signed high 18-bit part and an
unsigned low 17-bit part. Two 25x18 multipliers fit individual DSP48E2s. Their
registered products are recombined, then added to the voltage origin; target
selection, valid, hold and last-word tags travel with the arithmetic.

An added long-HOLD regression reproduced a sign reversal when a large slope
was evaluated far beyond its endpoint and the product wrapped at 48 bits.
V7 preserves the full product's upper bits through recombination. For an
extended RAMP it caps an excessively large increment at +/-2^35 before the
origin addition; all legal DAC differences are smaller. The existing endpoint
clamp therefore makes the correct decision without a wraparound. This does
not change the 11-cycle latency. Legacy arithmetic remains unchanged.

## Software use

`qick.ramp_v7.ramp_packet()` exposes an offline encoder. In the normal
`QickProgram` manager, initialize the current value with `awg_set`, then use
the existing `awg_ramp` style with sample-position fields:

```python
prog.set_pulse_registers(ch, style="awg_set", value=0, duration=1)
# Issue the SET at the intended preceding timestamp.
prog.set_pulse_registers(ch, style="awg_ramp", target=16000,
                         rise_start=2, rise_end=5,
                         fall_start=14, fall_end=20, end_target=400)
# This reserves two output words and holds code 400 afterward.
```

The v7 driver reports native latency 27 and output-sum discovery adds 4 once.
The older `awg_ramp(target=..., duration=...)` form remains available. The
public `awg_ramp()` convenience method also accepts the sample-position fields
shown above; omit `duration` and `step` in that form.

PulseGenerator's `awg_tuning_v7` branch now provides **Edit RAMP sample positions
(v7)...** in the AWG segment table's context menu. Sample indices and ns are
editable on the 1/16-word grid, with an optional second edge, arbitrary signed
turn/final voltages, and cross-word continuation. Save/load, preview, Python
export and the normal queued execution path use the same packet encoder.
Fine edge positions/voltages are fixed within a hardware sweep; HOLD/RF sweeps
and repetitions remain supported. Voltage/RAMP-duration sweeps and nonidentity
cross-capacitance matrices are rejected for fine RAMP. See PulseGenerator
`DCWaveformGeneratorGUI/md/AWG_TUNING_V7_FINE.md` for the editor contract.

QickSim's old waveform model rejects v7 execution explicitly; it must not
decode a v7 packet using legacy field positions or report legacy timing.
Command compilation and the full-CPU RTL fixture are supported. The software
integration was checked offline; the new image has not been deployed or
measured on the board as part of this task.

## Verification and build

The reduced project has three AWG/RF pairs. DAC7 retains its Square Pulse IP.
The AWG generators, sums and command slices for DAC8..11 are removed; their
RFDC inputs receive valid digital-zero words. The AXI interconnect has 34
masters instead of 38, with all surviving slave addresses unchanged. Readout
TMUX destination indices and the retained AWG/RF pipeline are unchanged.
`validate_topology.tcl` checks the actual BD connections before synthesis.

RTL benches live in `firmware/ip/axis_awg_tuning_v7/test/`; full CPU fixtures
live in `firmware/projects/qstl_awg_v7/test/`. The source-hashed functional gate
requires both old and new command traces, all 256 first/fall lane pairs with
both polarities, cross-word tails, long holds, immediate SET transitions,
readback/override, saturation, DC/RC control alignment and software tests.
Fixed/random cases are regression coverage, not an exhaustive formal proof of
every possible 160-bit input.

Build with Vivado 2023.1 and `QICK_V7_EVIDENCE_ROOT` pointing to fresh evidence.
`build_vivado_2023_1.tcl` copies unchanged constraints and builds in a fresh
directory outside Git. It refuses bitstream export until final routed setup,
hold, pulse-width, bus-skew and routing checks pass. The exported BIT and HWH
must match the same XSA. Build success and deployment are separate: this task
does not deploy firmware or perform an analogue measurement.

Current evidence root:
`F:/QICK_Private_Analysis/awg_tuning_v7/three_awg_20261027_142612Z`.
The original seven-AWG build and functional-test evidence are preserved in
`F:/QICK_Private_Analysis/awg_tuning_v7/implementation_20261027_071810Z`.
Final routed numbers and artifact hashes belong in its completion record;
functional simulation alone is not timing closure.
