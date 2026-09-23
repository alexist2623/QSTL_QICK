"""Realtime phase-continuous square DDS command conversion and IP driver.

Frequency is in MHz, phase is in degrees, amplitude is an unsigned peak DAC
code (0..32764, multiples of four). FTW advances per scalar DAC sample, not
per 16-sample fabric word. A command changes all fields atomically; only an
explicit ``reset_phase=True`` clears the accumulator.
"""
import math
from numbers import Integral, Real

from .drivers.generator import AbsPulsedSignalGen


def _integer(value, name, maximum):
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer")
    value = int(value)
    if not 0 <= value <= maximum:
        raise ValueError(f"{name} must be in 0..{maximum}")
    return value


def square_words(freq, phase, amplitude, *, enable=True, reset_phase=False, tmux_ch=None):
    """Return the five low-to-high 32-bit AXIS command words."""
    freq = _integer(freq, "freq word", 0xffffffff)
    phase = _integer(phase, "phase word", 0xffffffff)
    amplitude = _integer(amplitude, "amplitude", 32764)
    if amplitude % 4:
        raise ValueError("amplitude must be a multiple of four DAC codes")
    if not isinstance(enable, bool) or not isinstance(reset_phase, bool):
        raise ValueError("enable and reset_phase must be bool")
    control = int(enable) | (int(reset_phase) << 1)
    if tmux_ch is not None:
        control |= _integer(tmux_ch, "tmux_ch", 255) << 24
    return (freq, phase, amplitude, 0, control)


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


class AxisSquarePulseV1(AbsPulsedSignalGen):
    bindto = ["QICK:QICK:axis_square_pulse_v1:1.0"]
    TPROC_PORT = "s_axis"
    HAS_MIXER = False
    HAS_DDS = True
    B_DDS = B_PHASE = 32
    MAXV = 32764

    def _init_config(self, description):
        super()._init_config(description)
        params = description.get("parameters", {})
        n = int(params.get("N_PTS", 16))
        if n not in (1, 2, 4, 8, 16) or int(params.get("B", 16)) != 16 or int(params.get("CMD_WIDTH", 160)) != 160:
            raise ValueError("unsupported square DDS hardware parameters")
        self.REGISTERS = {"mute_reg": 0, "identity_reg": 0, "status_reg": 1, "latency_reg": 2}
        self.cfg.update(gen_type="square_pulse", n_pts=n, samps_per_clk=n,
                        cmd_width=160, minv=-32764, dac_invalid_lsb=2,
                        dac_effective_bits=14, continuous_output=True,
                        command_latency_cycles=4, phase_continuous=True)

    def mute(self):
        """Mute independently of tProc; stop_tproc() first to prevent re-enable."""
        self.mute_reg = 0

    def words(self, freq_mhz, amplitude, phase_deg=0.0, *, enable=True, reset_phase=False):
        return square_words(frequency_word(freq_mhz, self["f_dds"]),
                            phase_word(phase_deg), amplitude, enable=enable,
                            reset_phase=reset_phase, tmux_ch=self.cfg.get("tmux_ch"))
