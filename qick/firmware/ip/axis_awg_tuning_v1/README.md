# axis_awg_tuning_v1

`axis_awg_tuning_v1` is a tProcessor-v1-compatible realtime AXIS IP for AWG tuning values and linear ramp generation.

The AXIS command path remains the main SET/RAMP control path. The AXI-Lite slave is intentionally minimal and only provides software/debug current-value override plus current/status readback.

Default parameters are `N_PTS=16`, `B=16`, `FRAC=16`, `CMD_WIDTH=160`, `STEP_WIDTH=24`, `DURATION_WIDTH=23`, `FIXED_WIDTH=48`, and `EXTRA_Y_PIPE_STAGES=1`. `N_PTS` is the number of scalar samples packed into one output AXIS word.

`EXTRA_Y_PIPE_STAGES` is the pass-through pipeline depth after the DSP lane add stage. It is not a numeric scale factor and it does not multiply the output value.

## Interfaces

- `aclk` / `aresetn`: realtime AXIS data clock and reset.
- `s_axis_*`: 160-bit tProcessor command input.
- `m_axis_*`: `N_PTS*B` sample output.
- `s_axi_aclk` / `s_axi_aresetn`: AXI-Lite software/debug clock and reset.
- `s_axi_*`: 32-bit AXI-Lite slave.

The RFDC-facing AXIS output width remains `N_PTS*16` in the default configuration. Output samples are 16-bit words, but only the upper 14 bits are effective for the RF-DAC path. Bits `[1:0]` of every output lane are forced to `2'b00`.

## AXI-Lite Registers

| Offset | Name | Access | Description |
| --- | --- | --- | --- |
| `0x00` | `CURRENT_VALUE_REG` | RW | Write applies a signed 32-bit override. Read returns the current-value snapshot. |
| `0x04` | `STATUS_REG` | RO | Status snapshot. Writes are ignored. |

`CURRENT_VALUE_REG` write behavior:

- Replicates the signed override value across all `N_PTS` lanes after 16-bit saturation and 14-bit-effective MSB alignment.
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
| `[86:64]` | duration: unsigned 23-bit RAMP scalar samples, with 0 coerced to 1 |
| `[95:87]` | ignored duration extension bits |
| `[119:96]` | signed 24-bit fixed-point RAMP step, with `FRAC` fractional bits |
| `[127:120]` | ignored step extension bits |
| `[143:128]` | reserved |
| `[145:144]` | opcode: `00` NOP, `01` SET, `10` RAMP, `11` IDLE |
| `[146]` | SET hold mode: `0` hold target, `1` output zero after SET word |
| `[147]` | reserved, samples are always signed and saturated |
| `[148]` | deprecated clear field, ignored |
| `[159:149]` | reserved |

RAMP uses the software-provided signed 24-bit step directly. RTL does not divide by duration and does not compute the step internally. Software should compute and validate the step before packing the command.

## RAMP Datapath

The RAMP datapath uses explicit `DSP48E2` wrappers:

```text
word_inc_fixed = N_PTS * step

for each output word:
    inc[i]   = i * step
    y_add[i] = base_y_fixed + inc[i]
    y_pipe   = pass-through register stages only
    base_y_fixed = base_y_fixed + word_inc_fixed
```

The previous sample-index-wide multiply datapath is removed. The scalar word-base ramp value is accumulated once per output word, and each lane adds only its small precomputed lane increment.

With the default wrapper/register settings, the command-to-first-RAMP-output latency is:

```text
EXTRA_Y_PIPE_STAGES + 4 aclk cycles
```

For the default `EXTRA_Y_PIPE_STAGES=1`, the latency is 5 `aclk` cycles. Increasing `EXTRA_Y_PIPE_STAGES` only inserts additional `y <= y` registers after the lane add stage.

The final scalar sample of a ramp is forced to `y_target`. Any lanes after the final scalar sample in the final partial word are also forced to `y_target`. The forced target is saturated and MSB-aligned the same way as other output samples.

## Realtime Behavior

- The FSM has only `IDLE_ST` and `RAMP_ST`.
- `s_axis_tready` is always `1`.
- `m_axis_tready` is ignored.
- `m_axis_tvalid` is `1` after reset deassertion.
- SET executes only in `IDLE_ST`.
- RAMP starts from the current output value and emits one `N_PTS`-wide word per `aclk` after pipeline fill.
- Commands presented during `RAMP_ST` are intentionally dropped.
- OP_IDLE and OP_NOP are no-ops.

## Known Limitations

- Commands are not queued.
- RAMP assumes the provided 24-bit step and 23-bit duration do not overflow the 48-bit fixed-point datapath for the requested segment.
- The AXI-Lite interface is for override/readback only; it does not provide software SET/RAMP sequencing.
