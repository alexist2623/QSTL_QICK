# Continuous RC precompensation v1

The production AWG wrapper applies the requested inverse high-pass after the
existing SET/RAMP core. For scalar DAC samples (4.8 GSPS in this project):

```
q[n] = q[n-1] + (x[n] + x[n-1]) / (2*tau*fs)
y[n] = x[n] + q[n]
```

Python computes `round(2**48/(2*tau*fs))`. The FPGA multiplies and adds; it
contains no division. All 16 samples in a 300 MHz fabric word participate in
the integral, including transitions between lanes and between words.

SquarePulse uses the known sign of its raw square waveform and a software
half-step `round(amplitude*2**48/(2*tau*fs))`. Adjacent signed half-steps are
added. This produces linear compensation within each half-period, without a
general multiplier filter. The new increment and amplitude change atomically.
Frequency/phase-offset changes preserve both phase and compensation history.

## Arithmetic, delay, and limits

- Tau range: 10 us through 1,000,000 us (1000 ms).
- Coefficient: unsigned 32 bits with 48 fractional bits; Square half-step:
  unsigned 48 bits with 48 fractional bits.
- History: signed 72 bits, 48 fractional bits, saturating arithmetic.
  Fractional precision is internal; the DAC output is still signed 16-bit
  integer samples with 14 effective bits (multiples of four).
- Parallel prefix sums have four pipeline stages; the AWG multiplier has
  three register stages. Both compensation paths add **11 fabric clocks**,
  including bypass: 36.667 ns at 300 MHz. Square commands become visible in
  4 + 11 = **15 clocks**. Existing AWG RAMP startup/busy time remains unchanged.
- DAC output rounds to the nearest effective DAC code and saturates at
  -32768/+32764. A sticky status reports clipping. An explicit history reset
  clears the flag and history. No arithmetic wraps at the history rail.
- A persistent nonzero mean integrates into a growing DAC offset and eventually
  clips. Finite DAC headroom still applies. Existing DC area-compensation pulses
  close the nominal waveform area; they are not changed into a new algorithm.
- Analog verification assumes a single ideal first-order RC circuit, the
  specified tau, and initially relaxed capacitor state. Board bandwidth,
  multiple poles, calibration error and analog noise require physical validation.

The AWG IP retains its history until explicitly reset. The current GUI compiler
configures it before an experiment and resets it after each repetition, including
sweep points. The analog RC capacitor state is not reset by that digital command.
Square state survives ordinary parameter updates and
mute. Use explicit `reset_rc=True` when starting a new, relaxed RC history;
do not reset it on every continuous-wave update. Bypass preserves history;
switching modes is not a claim of bumpless analog transfer.

## AXIS ABI

AWG has a new `awg_rc` configuration command. It is an IDLE/no-op to the old
waveform core and is recognized only by the wrapper:

| Bits | Meaning |
|---|---|
| 31:0 | Q48 reciprocal coefficient |
| 145:144 | `3` (IDLE opcode) |
| 146 | RC enable |
| 147 | Clear RC history |
| 149 | RC configuration marker |
| 159:152 | Existing TMUX destination |

Square command fields remain frequency 31:0, phase 63:32, amplitude 79:64.
The half-step occupies 127:80. Control bits 128/129 retain enable/phase reset;
130/131 add RC enable/history reset. All five words update atomically.

HWH parameter `RC_PRECOMP_VERSION=1` identifies this ABI and latency. An absent
parameter means legacy firmware. New RC commands are rejected for legacy
firmware; ordinary SET/RAMP, DC compensation, and uncorrected SquarePulse work.
AWG status bits 8/9 report RC enable/clipping. Square status bit 2 is clipping.
AWG current-value readback remains the nominal SET/RAMP core value.

Example, inside a QICK program:

```python
from qick.precompensation import rc_coefficient, square_rc_increment

gen = self.soccfg['gens'][awg_ch]
fs_mhz = gen['f_fabric'] * gen['samps_per_clk']
self.set_pulse_registers(ch=awg_ch, style='awg_rc',
    coefficient=rc_coefficient(tau_us, fs_mhz), enable=True, reset=True)
self.pulse(ch=awg_ch, t=0)

# On each Square amplitude update, calculate and transmit a matching step.
step = square_rc_increment(gain, tau_us, self.soccfg['gens'][sq_ch]['f_dds'])
self.set_pulse_registers(ch=sq_ch, style='square', freq=ftw, phase=phase_word,
    gain=gain, rc_enable=True, rc_increment=step, reset_rc=False)
```

## Validation and reproduction

- `prepare_testbench.py` creates `tb_rc_precomp.sv`: actual AWG/Square IPs,
  independent scalar integer oracle, and exact zero-order-hold RC circuit.
  Five tau values, repeats, SET/RAMP, and amplitude/frequency/phase changes.
- `tb_rc_limits.sv`: actual IP clipping, 72-bit history rail, history reset,
  cycle-exact bypass changes, and mute with nonzero history.
- `verify_gui_rtl.py`: actual GUI export -> binary instruction memory ->
  production tProcessor/TMUX/register slices -> two AWG and one Square IP.
  10 x 10 voltage sweep, two repeats, simultaneous DC+RC, output triggers,
  500 us Square period. ARM and RFDC are absent from the simulation boundary.
- `synth.tcl`: routed 300 MHz OOC timing checks. Full-project timing must also
  pass; OOC timing alone does not publish firmware.
- `plot_results.py` plots actual simulator output and the independent RC model.

Run `prepare_testbench.py`, then Vivado 2023.1 batch with `run.tcl`, passing a
fresh output directory. An optional second argument selects `tb_rc_limits`.
Run `verify_gui_rtl.py --build <existing qstl_gui_rtl_sim build> --gui <QICK GUI repo>`.
The reusable simulation build includes production routing and generated vendor
simulation libraries. No behavioral generator replaces the tested RTL.

Test evidence is summarized in `analysis_results/rc_precompensation_v1` at the
repository root. New production artifacts are published only from a timing-
closed XSA using the project's `publish_build.py`.

The `sweep_matrix_20x20` report retains the original RF duration findings.
The subsequent `rf_duration_oneshot_v1` report records the software fix and
its full 20 x 20 reruns; long periodic pulses retain their block-boundary stop.
Per-channel current scaling and compensation checks are summarized separately
in `analysis_results/dac_current_v1`. These do not claim physical RFDC current
measurements or a fix for the existing integer voltage-sweep increment error.
