# Continuous square DDS

`QICK:QICK:axis_square_pulse_v1:1.0` accepts atomic, realtime 160-bit AXIS
commands. It emits 16 signed 16-bit samples per fabric clock in this project.
Sample zero occupies the least significant 16 bits and is the earliest sample.
At 300 MHz fabric clock this is a 4.8 GSPS scalar sample stream.

For each scalar sample, with all phase arithmetic modulo 2^32:

```
y[n] = MSB(acc[n] + phase_offset) ? -amplitude : +amplitude
acc[n+1] = acc[n] + frequency_word
frequency_hz = frequency_word * sample_rate_hz / 2^32
```

Changing frequency changes future increments, without clearing accumulated
phase. Changing phase changes only the added phase offset. Changing amplitude
does not change phase. Phase advances while muted. Clearing the accumulator
requires an explicit command flag; it is never implicit in a parameter update.
Zero frequency holds a DC level determined by the current accumulated phase and
offset. For a deterministic positive/negative DC level, explicitly clear phase
and use an offset of 0/180 degrees.

The MSB method implements a nominal 50% duty square. Sample-grid quantization
limits edge positions; DAC and analog-path bandwidth determine analog edges.
The API accepts nonnegative frequencies below scalar Nyquist. At 4.8 GSPS the
32-bit frequency resolution is about 1.1176 Hz. This is a square DDS, not an
RFDC sine generator or a programmable-duty PWM generator.

## Command and pipeline

| Word / bits | Meaning |
| --- | --- |
| 0 / 31:0 | 32-bit frequency increment per scalar sample |
| 1 / 63:32 | 32-bit phase offset (one turn = 2^32) |
| 2 / 95:64 | Unsigned peak amplitude; 0..32764, multiples of four |
| 3 / 127:96 | Reserved, zero |
| 4 bit 0 / 128 | Enable output; zero emits zero samples |
| 4 bit 1 / 129 | Clear accumulated phase once for this update |
| 4 bits 31:24 / 159:152 | Existing TMUX destination |

The two low DAC-code bits are unused by the existing DAC path. The IP clears
them before forming symmetric +/- values and clamps excessive magnitudes.
Software rejects unrepresentable codes rather than silently truncating them.

An accepted command affects its first output word four fabric clocks later.
The command register, partial lane products, summed lane offsets, phase sums,
and registered output sign selection maintain matching amplitude/phase state.
The constant lane products are split into base-four parts to shorten the carry
paths. Multiplication by +/-1 is sign selection and negation; no DSP amplitude
multiplier is needed. External TMUX, register-slice and RFDC delays are additional.

Like the existing AWG tuning IP, this is an uninterrupted sample stream.
`m_axis_tready` cannot pause phase or samples; connect it to the always-running
DAC path, not an intermittently stalled consumer. Commands are accepted every
clock while reset is inactive, including back-to-back updates.

## AXI-Lite and stopping

| Byte offset | Read | Write |
| --- | --- | --- |
| 0x00 | Identity `0x53515031` (`SQP1`) | Any nonempty byte strobe requests mute |
| 0x04 | Bit 0 enabled; bit 1 mute request pending | Error |
| 0x08 | Command latency: 4 fabric clocks | Error |
| 0x0c | Parallel sample count: 16 | Error |

Independent AW/W handshakes, response backpressure and a request/acknowledge
CDC are implemented. Stop the tProcessor before software mute so a queued new
command cannot re-enable the output. The Python `soc.stop_square_pulse(ch)`
performs both operations. `stop_tproc()` alone does not stop an autonomous DDS.
After the CDC and output pipeline drain, samples are zero, not the last level.

## Verification

Run Vivado 2023.1 batch mode with `run_xsim.tcl` and a fresh output directory.
The core testbench compares every scalar output against an independent
accumulator recurrence. It checks low frequency, 190 MHz, amplitude-only and
phase-only changes, phase wrap, DC, explicit phase reset, mute/enable, reset,
and randomized back-to-back commands. The wrapper testbench additionally checks
independent AXI write channels, stalled read responses, identity/status/latency,
asynchronous mute CDC and AXIS reset behavior.
