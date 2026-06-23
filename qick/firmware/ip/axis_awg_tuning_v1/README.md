# axis_awg_tuning_v1

`axis_awg_tuning_v1` is a tProcessor-v1-compatible realtime AXIS IP for AWG tuning values and linear ramp generation.

The AXIS command path remains the main SET/RAMP control path. The AXI-Lite slave is intentionally minimal and only provides software/debug current-value override plus current/status readback.

Default parameters are `N_PTS=16`, `B=16`, `FRAC=16`, and `CMD_WIDTH=160`. `N_PTS` is the number of scalar samples packed into one output AXIS word.

## Interfaces

- `aclk` / `aresetn`: realtime AXIS data clock and reset.
- `s_axis_*`: 160-bit tProcessor command input.
- `m_axis_*`: `N_PTS*B` sample output.
- `s_axi_aclk` / `s_axi_aresetn`: AXI-Lite software/debug clock and reset.
- `s_axi_*`: 32-bit AXI-Lite slave.

## AXI-Lite Registers

| Offset | Name | Access | Description |
| --- | --- | --- | --- |
| `0x00` | `CURRENT_VALUE_REG` | RW | Write applies a signed 32-bit override. Read returns the current-value snapshot. |
| `0x04` | `STATUS_REG` | RO | Status snapshot. Writes are ignored. |

`CURRENT_VALUE_REG` write behavior:

- Replicates the signed override value across all `N_PTS` lanes, saturated to `B` bits.
- Forces the FSM to `IDLE_ST`.
- Aborts an active ramp.
- Becomes the start value for the next AXIS RAMP command.
- Has priority over a same-cycle AXIS command, so that AXIS command is dropped.

`STATUS_REG` bits:

| Bit | Meaning |
| --- | --- |
| 0 | AXIS core is idle |
| 1 | AXIS core is ramping |
| 2 | `m_axis_tvalid` |
| 3 | `s_axis_tready` |
| 4 | AXI override write is pending CDC acknowledgement |
| 5 | At least one AXI override write has been acknowledged |

Readback is synchronized between clock domains and can lag the realtime AXIS domain by a few cycles. During `RAMP_ST`, `CURRENT_VALUE_REG` reads lane 0 of the most recently emitted word; otherwise it reads the held logical scalar value.

## AXIS Command Format

The command word is 160 bits to match `axis_tproc64x32_x8_v1` realtime master outputs.

| Bits | Field |
| --- | --- |
| `[31:0]` | `y_target` for SET/RAMP, signed integer |
| `[63:32]` | reserved/deprecated `y_start` field, ignored by RAMP |
| `[95:64]` | duration: RAMP scalar samples, with 0 coerced to 1 |
| `[127:96]` | reserved/deprecated software step field, ignored by RAMP |
| `[143:128]` | reserved |
| `[145:144]` | opcode: `00` NOP, `01` SET, `10` RAMP, `11` IDLE |
| `[146]` | SET hold mode: `0` hold target, `1` output zero after SET word |
| `[147]` | reserved, samples are always signed and saturated |
| `[148]` | deprecated clear field, ignored |
| `[159:149]` | reserved |

RAMP ignores the deprecated start and step fields. For `duration > 1`, the IP computes one signed fixed-point step when a RAMP command is accepted:

```text
step = trunc(((y_target - current_value) <<< FRAC) / (duration - 1))
```

For `duration <= 1`, the step is forced to zero and the emitted output is clamped directly to `y_target`.

## Realtime Behavior

- The FSM has only `IDLE_ST` and `RAMP_ST`.
- `s_axis_tready` is always `1`.
- `m_axis_tready` is ignored.
- `m_axis_tvalid` is `1` after reset deassertion.
- SET executes only in `IDLE_ST`.
- RAMP starts from the current output value and emits one `N_PTS`-wide word per `aclk`.
- Commands presented during `RAMP_ST` are intentionally dropped.
- OP_IDLE and OP_NOP are no-ops.

For lane `i` in an output word:

```text
sample_index = word_base_index + i
sample = current_value_at_ramp_start + sample_index * step
```

The final scalar sample, and any lanes after it in the final partial word, are forced to `y_target`.

## Known Limitations

- Commands are not queued.
- RAMP uses an inferred signed divider at command acceptance to compute the segment step.
- The AXI-Lite interface is for override/readback only; it does not provide software SET/RAMP sequencing.
