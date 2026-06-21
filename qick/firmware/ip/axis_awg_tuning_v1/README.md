# axis_awg_tuning_v1

`axis_awg_tuning_v1` is a tProcessor-v1-compatible realtime AXIS IP for AWG tuning values and linear ramp generation.

The IP accepts one 160-bit AXIS command stream and emits one `N_DDS*16` AXIS sample word per accepted output clock. By default, `N_DDS=16`, `B=16`, and `FRAC=16`.

## Interfaces

The IP uses one clock/reset domain:

- `aclk`
- `aresetn`, active low
- `s_axis_*`, 160-bit command input by default
- `m_axis_*`, `N_DDS*B` sample output

There is no AXI-Lite interface and no waveform memory-loading interface.

## Command Format

The command word is 160 bits to match `axis_tproc64x32_x8_v1` realtime master outputs.

| Bits | Field |
| --- | --- |
| `[31:0]` | `y_target` for SET/RAMP, signed integer |
| `[63:32]` | reserved/deprecated `y_start` field, ignored by continuous RAMP |
| `[95:64]` | duration: RAMP scalar samples, IDLE slow cycles, with 0 coerced to 1 |
| `[127:96]` | reserved/deprecated software step field, ignored by continuous RAMP |
| `[143:128]` | reserved |
| `[145:144]` | opcode: `00` NOP, `01` SET, `10` RAMP, `11` IDLE |
| `[146]` | hold mode: `0` hold final value, `1` output zero after command |
| `[147]` | reserved, samples are always signed and saturated |
| `[148]` | clear held output state before SET; ignored by RAMP/IDLE/NOP |
| `[159:149]` | reserved |

RAMP no longer uses the deprecated start or step fields. For `duration > 1`, the IP computes one signed fixed-point step when a RAMP command is accepted:

```text
step = trunc(((y_target - current_value) <<< FRAC) / (duration - 1))
```

The division is not performed per output sample. For `duration <= 1`, the step is forced to zero and the emitted output is clamped directly to `y_target`.

`current_value` tracks the logical value represented by the currently held output. When hold-zero mode is requested, `current_value` becomes zero after the command so the next continuous RAMP starts from the visible zero output.

## Timing Behavior

For RAMP, `duration` is counted in scalar output samples. One `m_axis` handshake emits one vector word containing `N_DDS` consecutive scalar ramp samples.

For lane `i` in an output word:

```text
sample_index = word_base_index + i
sample = current_value_at_ramp_start + sample_index * step
```

The final scalar sample, and any lanes after it in the final partial word, are forced to `y_target`. This prevents accumulated fixed-point rounding error at segment end.

## SET Mode

Opcode `01` emits one `m_axis` word with the set value replicated across all `N_DDS` lanes. The value is saturated to signed `B`-bit range.

After the SET word is accepted:

- hold bit `0`: the IP continuously emits the set value while downstream is ready.
- hold bit `1`: the IP continuously emits zero while downstream is ready.

## RAMP Mode

Opcode `10` ignores the deprecated `y_start` and software `step` fields. It starts from the current held output value, targets `y_target`, computes a fixed-point step once, and emits `ceil(duration / N_DDS)` output words.

Positive and negative ramps are both supported. All output samples are saturated to signed `B`-bit range.

Normal RAMP commands are continuous. Only SET commands are intended to create instantaneous output jumps. The `duration <= 1` RAMP case emits the target directly and can therefore look instantaneous by definition.

## IDLE Mode

Opcode `11` accepts the command and waits for `[95:64]` slow sequencer cycles. In this mode a slow cycle is one `aclk` cycle spent in the timed wait state, not an accepted `m_axis` output word.

During IDLE, `m_axis_tvalid` is deasserted and `m_axis_tdata` holds the previous stable held-output value. The current held output, ramp accumulator/configuration, slope, and target are not changed. After the wait expires, normal command readiness resumes; if a held output is active, `s_axis_tready` again follows `m_axis_tready`.

## Backpressure And Command Acceptance

`m_axis_tdata` remains stable while `m_axis_tvalid=1` and `m_axis_tready=0`.

Commands are not queued. `s_axis_tready` is deasserted while SET or RAMP output is active. In HOLD state, `s_axis_tready` follows `m_axis_tready` so a new command is only accepted on a cycle where the held output can also handshake.

## Example Commands

SET to `1000`, hold last:

```text
cmd[31:0]    = 1000
cmd[145:144] = 2'b01
cmd[146]     = 0
```

RAMP continuously from the current held value to `1000` in 64 scalar samples:

```text
cmd[31:0]    = 1000
cmd[63:32]   = ignored
cmd[95:64]   = 64
cmd[127:96]  = ignored
cmd[145:144] = 2'b10
cmd[146]     = 0
```

## Known Limitations

- Commands are stalled, not queued.
- RAMP uses an inferred signed divider at command acceptance to compute the segment step.
- The IP emits consecutive ramp samples across lanes. SET and HOLD output replicate one scalar value across all lanes.
- Python driver and assembler support are intentionally left as future work.
