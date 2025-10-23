from __future__ import annotations
from typing import (
    Iterable,
)
import numpy as np

from qstl_variable import (
    Variable,
    Scalar,
)

class BaseOperation:
    r"""
    A base class for operations acting on QICK.
    """
    def __init__(self):
        self.name = None

class HardwareOperation(BaseOperation):
    r"""
    A base class for hardware operations.

    :param duration: The duration of the operation in seconds.
    """
    def __init__(self):
        super().__init__()
        self.duration = None

    def n_samples(self, sample_rate: float) -> int:
        r"""
        The number of samples in this operation when sampled at a specific rate.

        :param sample_rate: The sample rate in Hz.
        """
        raise NotImplementedError

    def sampled_duration(self, sample_rate: float) -> float:
        r"""
        The duration of the operation in seconds when sampled at a specified rate.

        :param sample_rate: The rate at which to sample the operation in Hz.
        """
        raise NotImplementedError

class BaseWaveform(HardwareOperation):
    r"""
    A base class for waveforms.

    :param duration: The duration of the waveform in seconds.
    """
    def __init__(self):
        super().__init__()
        self.amplitudes: list[Variable] = None
        self.envelopes: dict[Envelope, Variable] = None

    def to_flattop(
        self,
        hold_duration: float | Iterable[float] | Variable,
        fraction: float = 0.5,
    ) -> list[HardwareOperation]:
        r"""
        No reason to use this in QICK
        """
        raise NotImplementedError

class Delay(HardwareOperation):
    r"""
    A :py:class:`~keysight.qcs.channels.HardwareOperation` representing a delay.

    When a delay is present in a series of waveforms, the next RF waveform is modulated
    by the phase accumulated during the delay, which depends on the frequency of the
    next RF waveform. This ensures that channels can track phase evolution.

    The value of the phase is ``exp(1j * sampled_delay * int_freq)`` where
    ``sampled_delay`` is the exact duration of the delay accounting for finite sampling
    effects (that is, the output of ``delay.sampled_duration(sample_rate)``) and
    ``int_freq`` is the output of ``waveform.intermediate_frequency(lo_frequency)``\.

    :param duration: The duration of the delay in seconds.
    :param name: An optional name for this.
    """
    def __init__(
        self,
        duration: float | Iterable[float] | Variable,
        name: str | None = None,
    ) -> None:
        super().__init__()
        self.duration = duration
        self.name = name

class Synchronize(HardwareOperation):
    def __init__(self):
        pass

class Envelope:
    r"""
    An abstract base class for envelopes.
    """
    def __init__(self):
        self.name = None

class ConstantEnvelope(Envelope):
    r"""
    Represents a constant envelope :math:`E(t) = 1`.

    .. jupyter-execute::

        import keysight.qcs as qcs

        # initialize a ConstantEnvelope
        pulse = qcs.ConstantEnvelope()

    """
    def __init__(self):
        super().__init__()
        self.name = "ConstantEnvelope"

class GaussianEnvelope(Envelope):
    r"""
    Represents a truncated Gaussian envelope shifted and rescaled to satisfy
    :math:`E(0) = E(1) = 0` and :math:`E(0.5) = 1`.

    The envelope :math:`E(t)` at time :math:`t` is

    .. math::

        E(t) = (1 + \alpha)\exp\left(-(2 * t - 1)^2 n_\sigma^2 / 2 \right) - \alpha\:,

    where :math:`n_\sigma` is the number of standard deviations included in the envelope
    and :math:`\alpha` is the scale factor.

    .. jupyter-execute::

        import keysight.qcs as qcs

        # initialize a GaussianEnvelope with three standard deviations
        pulse = qcs.GaussianEnvelope(3)

    :param num_sigma: The number of standard deviations to include in the envelope.
    :raises ValueError: If ``num_sigma`` is less than 2.
    """
    def __init__(
        self,
        num_sigma: float = 2
    ):
        super().__init__()
        self.num_sigma = num_sigma
        self.alpha = 1.0
        self.name = "GaussianEnvelope"

class DCWaveform(BaseWaveform):
    r"""
    A class for unmodulated waveforms.

    :param duration: The duration of the waveform.
    :param envelope: The shape of the waveform.
    :param amplitude: The amplitude of the waveform relative to the range of the signal
        generator.
    :param name: An optional name for this.
    """
    def __init__(
        self,
        duration: float | Iterable[float] | Variable,
        envelope: Envelope,
        amplitude: float | Variable,
        name: str | None = None,
    ) -> None:
        super().__init__()
        self.amplitude = amplitude
        self.duration = duration
        self.envelope = envelope
        self.name = "DCWaveform" if name is None else name

class RFWaveform(BaseWaveform):
    r"""
    Represents a waveform with target frequency or frequencies.

    The signal :math:`V(t)` at time :math:`t` after modulating an envelope
    :math:`E(t)` by a frequency :math:`f` and a phase :math:`\phi` is

    .. math::

        V(t) = E(t) \exp(2 \pi j f t + \phi).

    .. jupyter-execute::

        import keysight.qcs as qcs

        # initialize a 100ns base envelope
        base = qcs.ConstantEnvelope()

        # initialize an RFWaveform with an amplitude of 0.3 and a frequency of 5 GHz
        pulse1 = qcs.RFWaveform(100e-9, base, 0.3, 5e9)

        # initialize a sliceable RFWaveform with different frequencies
        rf = qcs.Array("rf", value=[5e9, 6e9])
        pulse2 = qcs.RFWaveform(100e-9, base, 0.3, rf)

    .. note::

        If ``rf_frequency`` and ``instantaneous_phase`` are given as ``float``\s, they
        are converted to a scalar. Otherwise, if they are given as scalar or array,
        they are stored as provided.

    :param duration: The duration of the waveform.
    :param envelope: The envelope of the waveform before modulation.
    :param amplitude: The amplitude of the waveform relative to the range of the signal
        generator.
    :param rf_frequency: The RF frequency of the output pulse in Hz.
    :param instantaneous_phase: The amount (in radians) by which the phase of this
        waveform is shifted, relative to the rotating frame set by ``rf_frequency``.
    :param post_phase: The amount (in radians) by which the phase of all subsequent
        RF waveforms are shifted relative to the rotating frame.
    :param name: An optional name for this.

    :raises ValueError: If ``rf_frequency`, ``instantaneous_phase``, and ``post_phase``
        have invalid (not one-dimensional) or inconsistent shapes.
    """
    def __init__(
        self,
        duration: float | Iterable[float] | Scalar[float],
        envelope: Envelope,
        amplitude: float | Variable,
        rf_frequency: float | Variable,
        instantaneous_phase: float | Variable = 0.0,
        post_phase: float | Variable = 0.0,
        name: str | None = None,
    ) -> None:
        super().__init__()
        self.amplitude = amplitude
        self.envelope = envelope
        self.duration = duration
        self.name = name
        self.rf_frequency = rf_frequency
        self.instantaneous_phase = instantaneous_phase
        self.post_phase = post_phase
        self.name = name

    def phase_update(self, sample_rate: float, lo_frequency: float = 0.0) -> complex:
        r"""
        No reason to use this in QICK
        """
        raise NotImplementedError

    def phase_per_fractional_sample(
        self,
        sample_rate: float,
        lo_frequency: float = 0.0,
        fraction: float = 1
    ) -> complex:
        r"""
        No reason to use this in QICK
        """
        raise NotImplementedError
