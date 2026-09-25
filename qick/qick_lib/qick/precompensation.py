"""Software-only RC coefficient conversion for firmware precompensation v1.

The scalar DAC rate (not the fabric clock) determines the coefficient.
The FPGA uses Q48 coefficients and a signed 72-bit history accumulator.
"""
import math
from numbers import Real, Integral

RC_FRAC_BITS = 48
RC_OUTPUT_LATENCY = 11
RC_TAU_MIN_US = 10.0
RC_TAU_MAX_US = 1_000_000.0


def rc_coefficient(tau_us, sample_rate_mhz):
    for value, name in ((tau_us, "tau_us"), (sample_rate_mhz, "scalar sample rate")):
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    if not RC_TAU_MIN_US <= tau_us <= RC_TAU_MAX_US:
        raise ValueError("RC tau must be between 10 us and 1000 ms")
    word = round((1 << RC_FRAC_BITS)/(2*float(tau_us)*float(sample_rate_mhz)))
    if not 1 <= word <= 0xffffffff:
        raise ValueError("RC coefficient cannot be represented at this sample rate")
    return word


def square_rc_increment(amplitude, tau_us, sample_rate_mhz):
    """Q48 half-step; the square core only adds/subtracts this increment."""
    if isinstance(amplitude, bool) or not isinstance(amplitude, Integral) or not 0 <= amplitude <= 32764:
        raise ValueError("SquarePulse amplitude must be a DAC magnitude in 0..32764")
    rc_coefficient(tau_us, sample_rate_mhz)  # Validate the supported range.
    step = round(int(amplitude)*(1 << RC_FRAC_BITS)/(2*float(tau_us)*float(sample_rate_mhz)))
    if not 0 <= step < (1 << 48):
        raise ValueError("SquarePulse RC increment exceeds 48 bits")
    return step


def awg_rc_words(coefficient=0, *, enable=False, reset=False, tmux_ch=None):
    if isinstance(coefficient, bool) or not isinstance(coefficient, Integral) or not 0 <= coefficient <= 0xffffffff:
        raise ValueError("RC coefficient must be unsigned 32 bits")
    if not isinstance(enable, bool) or not isinstance(reset, bool):
        raise ValueError("RC enable/reset must be bool")
    if enable and coefficient == 0:
        raise ValueError("enabled RC compensation requires a nonzero coefficient")
    control = (1 << 21) | (3 << 16) | (int(enable) << 18) | (int(reset) << 19)
    if tmux_ch is not None:
        if isinstance(tmux_ch, bool) or not isinstance(tmux_ch, Integral) or not 0 <= tmux_ch <= 255:
            raise ValueError("tmux_ch must be in 0..255")
        control |= int(tmux_ch) << 24
    return (int(coefficient), 0, 0, 0, control)
