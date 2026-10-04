"""Hardware-independent command conversion for the realtime square DDS.

Frequency is in MHz, phase is in degrees, amplitude is an unsigned peak DAC
code (0..32764, multiples of four). FTW advances per scalar DAC sample, not
per 16-sample fabric word. A command changes all fields atomically; only an
explicit ``reset_phase=True`` clears the accumulator.

The board driver is loaded only when ``AxisSquarePulseV1`` is requested.
Desktop compilation of command words does not require PYNQ.
"""
import math
from numbers import Integral, Real

__all__ = ["frequency_word", "phase_word", "square_words", "AxisSquarePulseV1"]

def _integer(value, name, maximum):
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer")
    value = int(value)
    if not 0 <= value <= maximum:
        raise ValueError(f"{name} must be in 0..{maximum}")
    return value


def square_words(freq, phase, amplitude, *, enable=True, reset_phase=False, tmux_ch=None,
                 rc_enable=False, rc_increment=0, reset_rc=False):
    """Return the five low-to-high 32-bit AXIS command words."""
    freq = _integer(freq, "freq word", 0xffffffff)
    phase = _integer(phase, "phase word", 0xffffffff)
    amplitude = _integer(amplitude, "amplitude", 32764)
    if amplitude % 4:
        raise ValueError("amplitude must be a multiple of four DAC codes")
    if not isinstance(enable, bool) or not isinstance(reset_phase, bool):
        raise ValueError("enable and reset_phase must be bool")
    control = int(enable) | (int(reset_phase) << 1)
    if not isinstance(rc_enable, bool) or not isinstance(reset_rc, bool):
        raise ValueError("RC enable/reset must be bool")
    rc_increment = _integer(rc_increment, "RC increment", (1 << 48)-1)
    control |= (int(rc_enable) << 2) | (int(reset_rc) << 3)
    if tmux_ch is not None:
        control |= _integer(tmux_ch, "tmux_ch", 255) << 24
    return (freq, phase, amplitude | ((rc_increment & 0xffff) << 16), rc_increment >> 16, control)


def frequency_word(freq_mhz, sample_rate_mhz):
    """Quantize a nonnegative frequency below scalar-sample Nyquist."""
    for value, name in ((freq_mhz, "frequency"), (sample_rate_mhz, "sample rate")):
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
    if sample_rate_mhz <= 0 or not 0 <= freq_mhz < sample_rate_mhz / 2:
        raise ValueError("frequency must satisfy 0 <= frequency < sample_rate / 2")
    word = round(freq_mhz * 2**32 / sample_rate_mhz)
    if word >= 2**31:
        raise ValueError("rounded frequency reaches Nyquist")
    return word


def phase_word(phase_deg):
    if isinstance(phase_deg, bool) or not isinstance(phase_deg, Real) or not math.isfinite(phase_deg):
        raise ValueError("phase must be finite")
    return round((phase_deg % 360.0) * 2**32 / 360.0) % 2**32


def __getattr__(name):
    # Preserve the public driver import path for existing board-side code.
    if name == "AxisSquarePulseV1":
        from .drivers.square_pulse import AxisSquarePulseV1
        globals()[name] = AxisSquarePulseV1
        return AxisSquarePulseV1
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
