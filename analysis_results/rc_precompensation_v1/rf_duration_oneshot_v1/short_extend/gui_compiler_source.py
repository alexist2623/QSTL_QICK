"""Build multi-output AWG-tuning amplitude sweeps for QICK ASM v1.

Normalized amplitudes use the user-facing range [-1.0, 1.0].  They are
converted to the 16-bit, 14-effective-bit DAC codes used by
``axis_awg_tuning_v1``.  SET segments define levels for one to eight AWG
tuning outputs.  RAMP segments define only transition duration: each RAMP
automatically targets the following SET level.  ``None`` on a SET means that
an output holds its previous value.

Independent sweep axes are expanded as a Cartesian product, with the last
axis varying fastest.  Sweep points and repetitions execute as nested
tProcessor hardware loops.  SET target and dependent RAMP target/step values
are held in tProcessor registers and advanced directly with add instructions;
there is no point table and no sweep-point PMEM unrolling.

An optional cross-capacitance matrix maps all virtual SET/RAMP waveforms to
the physical AWG outputs with ``physical = matrix @ virtual``.  It therefore
applies to fixed pulses as well as swept coordinates.

Optional normal RF generator pulses and a FIR-decimated DDR readout can be
attached to named SET segments.  Each sweep point may be repeated N times;
the returned DDR array is grouped as ``(point, repetition, sample, I/Q)`` and
``iq_grid`` restores the original Cartesian sweep dimensions.

Optional Bias-T compensation has two distinct modes. DC compensation appends
the existing opposite-polarity physical-AWG SET after each shot and can keep
either voltage or duration fixed. Filter compensation treats the Bias-T as a
first-order high-pass and replaces each physical flat with a SET followed by a
linear ``target/tau`` slew. Both modes reuse tProcessor hardware loops without
expanding sweep points in PMEM.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import product
from math import ceil, isclose, isfinite
from numbers import Integral, Real
from typing import Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union

import numpy as np

from qick.averager_program import RAveragerProgram

try:
    from .fir_ddr_profile import resolve_fir_ddr_profile
    from .qick_square_dds import SquarePulseProgramMixin, OutputTriggerConfig
    from .qick_output_triggers import OutputTriggerProgramMixin
except ImportError:
    from fir_ddr_profile import resolve_fir_ddr_profile
    from qick_square_dds import SquarePulseProgramMixin, OutputTriggerConfig
    from qick_output_triggers import OutputTriggerProgramMixin


MAX_OUTPUTS = 8
MAX_RF_ONESHOT_CYCLES = 65535
RF_PERIODIC_WORD_CYCLES = 3
RF_STOP_WORD_CYCLES = 3
OP_SET = 0b01
OP_RAMP = 0b10
COMMAND_REGISTER_NAMES = (
    "target",
    "reserved_start",
    "duration",
    "step",
    "control",
)
DEFAULT_BIAS_T_DURATION_FRAC_BITS = 8
BIAS_T_INSTRUCTION_LEAD_PER_OUTPUT = 32
BIAS_T_COMPENSATION_MODES = ("fixed_voltage", "fixed_time")
BIAS_T_COMPENSATION_TYPES = ("dc", "filter", "dc_rc")
DEFAULT_DDR_READBACK_TRIGGER_CHUNK = 100_000
COMPILE_VALIDATION_FULL = "full"
COMPILE_VALIDATION_BOUNDARY = "boundary"
COMPILE_VALIDATION_MODES = (
    COMPILE_VALIDATION_BOUNDARY,
    COMPILE_VALIDATION_FULL,
)
DEFAULT_COMPILE_VALIDATION_MODE = COMPILE_VALIDATION_FULL


def normalize_compile_validation_mode(value) -> str:
    """Return a supported sweep compiler validation mode."""
    mode = str(value or DEFAULT_COMPILE_VALIDATION_MODE).strip().lower()
    if mode not in COMPILE_VALIDATION_MODES:
        raise ValueError(
            "compile validation mode must be one of "
            f"{COMPILE_VALIDATION_MODES}"
        )
    return mode


def _require_int(value, name: str, minimum: Optional[int] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer")
    value = int(value)
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _require_positive_real(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    value = float(value)
    if not isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be positive and finite")
    return value


def _require_amplitude(value, name: str = "amplitude") -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")
    if value < -1.0 or value > 1.0:
        raise ValueError(f"{name}={value} is outside [-1.0, 1.0]")
    return value


def cycles_from_ns(duration_ns: Real, fabric_mhz: Real) -> int:
    """Round a nanosecond duration up to whole fabric-clock cycles."""
    duration_ns = float(duration_ns)
    fabric_mhz = float(fabric_mhz)
    if duration_ns <= 0 or fabric_mhz <= 0:
        raise ValueError("duration_ns and fabric_mhz must be positive")
    exact_cycles = duration_ns * fabric_mhz / 1000.0
    nearest_cycle = round(exact_cycles)
    if isclose(exact_cycles, nearest_cycle, rel_tol=1e-12, abs_tol=1e-12):
        return max(1, int(nearest_cycle))
    return max(1, int(ceil(exact_cycles)))


def cycles_from_us(duration_us: Real, fabric_mhz: Real) -> int:
    """Round a microsecond duration up to whole fabric-clock cycles."""
    duration_us = float(duration_us)
    fabric_mhz = float(fabric_mhz)
    if duration_us <= 0 or fabric_mhz <= 0:
        raise ValueError("duration_us and fabric_mhz must be positive")
    exact_cycles = duration_us * fabric_mhz
    nearest_cycle = round(exact_cycles)
    if isclose(exact_cycles, nearest_cycle, rel_tol=1e-12, abs_tol=1e-12):
        return max(1, int(nearest_cycle))
    return max(1, int(ceil(exact_cycles)))


def normalized_to_dac(
    amplitude: Real,
    *,
    min_code: int = -32768,
    max_code: int = 32764,
    invalid_lsb: int = 2,
) -> int:
    """Convert [-1, 1] to a signed, MSB-aligned DAC code.

    The conversion uses a symmetric 32768 scale, rounds to the nearest legal
    code, clamps positive full scale to 32764, and keeps the lower two bits at
    zero for the default 14-effective-bit RF-DAC input format.
    """
    amplitude = _require_amplitude(amplitude)
    min_code = int(min_code)
    max_code = int(max_code)
    invalid_lsb = _require_int(invalid_lsb, "invalid_lsb", 0)
    quantum = 1 << invalid_lsb
    full_scale = max(abs(min_code), max_code + quantum)
    code = int(round(amplitude * full_scale / quantum)) * quantum
    code = max(min_code, min(max_code, code))
    return code


def dac_to_normalized(code: Integral, *, full_scale: int = 32768) -> float:
    """Convert a signed DAC code back to the normalized display scale."""
    code = _require_int(code, "code")
    return float(code) / float(full_scale)


def _div_trunc_zero(numerator: int, denominator: int) -> int:
    if denominator == 0:
        raise ZeroDivisionError("division by zero")
    sign = -1 if (numerator < 0) ^ (denominator < 0) else 1
    return sign * (abs(numerator) // abs(denominator))


def _round_div_nearest(numerator: int, denominator: int) -> int:
    """Round an integer ratio to nearest, with ties away from zero."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    sign = -1 if numerator < 0 else 1
    return sign * ((abs(int(numerator)) + denominator // 2) // denominator)


@dataclass(frozen=True)
class PulseSegment:
    name: str
    kind: str
    amplitudes: Tuple[Optional[float], ...]
    duration_cycles: int


@dataclass(frozen=True)
class AmplitudeSweep:
    segment_name: str
    output_name: str
    start: float
    stop: float
    count: int

    @property
    def points(self) -> Tuple[float, ...]:
        if self.count == 1:
            return (self.start,)
        values = [
            self.start + (self.stop - self.start) * index / (self.count - 1)
            for index in range(self.count)
        ]
        values[0] = self.start
        values[-1] = self.stop
        return tuple(values)

    @property
    def axis_kind(self) -> str:
        return "amplitude"

    @property
    def coordinate_unit(self) -> str:
        return "normalized"


@dataclass(frozen=True)
class RfDurationSweep:
    """RF pulse-duration sweep coordinated with one AWG SET segment.

    Coordinates are stored in microseconds for user-facing plots and QCoDeS.
    ``fixed`` leaves the AWG segment timing unchanged. In
    ``extend_by_rf_duration`` mode the effective AWG segment duration is the
    original duration plus the current RF pulse duration.
    """

    segment_name: str
    output_name: str
    gen_ch: int
    start: float
    stop: float
    count: int
    segment_length_mode: str
    sequence_fabric_mhz: float
    parameter_name: str = ""

    def __post_init__(self):
        if not str(self.segment_name):
            raise ValueError("RF duration sweep segment_name must not be empty")
        if not str(self.output_name):
            raise ValueError("RF duration sweep output_name must not be empty")
        if self.parameter_name and not str(self.parameter_name).isidentifier():
            raise ValueError(
                "RF duration sweep parameter_name must be an identifier"
            )
        _require_int(self.gen_ch, "RF duration sweep gen_ch", 0)
        _require_positive_real(self.start, "RF duration sweep start")
        _require_positive_real(self.stop, "RF duration sweep stop")
        _require_int(self.count, "RF duration sweep count", 1)
        _require_positive_real(
            self.sequence_fabric_mhz,
            "RF duration sweep sequence_fabric_mhz",
        )
        if self.segment_length_mode not in {
            "fixed",
            "extend_by_rf_duration",
        }:
            raise ValueError(
                "RF duration sweep segment_length_mode must be "
                "'fixed' or 'extend_by_rf_duration'"
            )

    @property
    def points(self) -> Tuple[float, ...]:
        if self.count == 1:
            return (float(self.start),)
        values = [
            self.start + (self.stop - self.start) * index / (self.count - 1)
            for index in range(self.count)
        ]
        values[0] = self.start
        values[-1] = self.stop
        return tuple(float(value) for value in values)

    @property
    def axis_kind(self) -> str:
        return "rf_duration"

    @property
    def coordinate_unit(self) -> str:
        return "us"


@dataclass(frozen=True)
class RfSegmentLengthExtension:
    """Aggregate RF-pulse time added to one AWG SET segment.

    ``base_duration_cycles`` is the sum of every pulse duration at the first
    Cartesian sweep point. ``parameter_multiplicities`` records how many
    pulses reference each named duration parameter, so subsequent sweep
    points can adjust the segment by the matching duration delta without
    materializing the Cartesian sweep.
    """

    segment_name: str
    gen_ch: int
    base_duration_cycles: int
    parameter_multiplicities: Tuple[Tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        if not str(self.segment_name):
            raise ValueError("RF segment extension name must not be empty")
        _require_int(self.gen_ch, "RF segment extension gen_ch", 0)
        _require_int(
            self.base_duration_cycles,
            "RF segment extension base_duration_cycles",
            1,
        )
        normalized = tuple(
            (str(name), _require_int(count, "RF duration reference count", 1))
            for name, count in self.parameter_multiplicities
        )
        names = tuple(name for name, _count in normalized)
        if any(name and not name.isidentifier() for name in names):
            raise ValueError(
                "RF segment extension parameter names must be identifiers"
            )
        if len(set(names)) != len(names):
            raise ValueError(
                "RF segment extension parameter names must be unique"
            )
        object.__setattr__(self, "parameter_multiplicities", normalized)

    def multiplier(self, parameter_name: str) -> int:
        """Return the number of pulses using one duration parameter."""
        parameter_name = str(parameter_name)
        return next(
            (
                int(count)
                for name, count in self.parameter_multiplicities
                if name == parameter_name
            ),
            0,
        )


@dataclass(frozen=True)
class RfFrequencySweep:
    """Hardware RF-generator frequency sweep in MHz."""

    segment_name: str
    output_name: str
    gen_ch: int
    start: float
    stop: float
    count: int
    parameter_name: str = ""

    def __post_init__(self):
        if not str(self.segment_name):
            raise ValueError("RF frequency sweep segment_name must not be empty")
        if not str(self.output_name):
            raise ValueError("RF frequency sweep output_name must not be empty")
        if self.parameter_name and not str(self.parameter_name).isidentifier():
            raise ValueError(
                "RF frequency sweep parameter_name must be an identifier"
            )
        _require_int(self.gen_ch, "RF frequency sweep gen_ch", 0)
        for value, name in (
            (self.start, "RF frequency sweep start"),
            (self.stop, "RF frequency sweep stop"),
        ):
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"{name} must be a real number")
            if not isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
        _require_int(self.count, "RF frequency sweep count", 1)

    @property
    def points(self) -> Tuple[float, ...]:
        if self.count == 1:
            return (float(self.start),)
        values = np.linspace(
            float(self.start),
            float(self.stop),
            int(self.count),
            dtype=np.float64,
        )
        values[0] = float(self.start)
        values[-1] = float(self.stop)
        return tuple(float(value) for value in values)

    @property
    def axis_kind(self) -> str:
        return "rf_frequency"

    @property
    def coordinate_unit(self) -> str:
        return "MHz"


@dataclass(frozen=True)
class RfPowerSweep:
    """Calibrated RF connector-power sweep in dBm."""

    segment_name: str
    output_name: str
    gen_ch: int
    start: float
    stop: float
    count: int

    def __post_init__(self):
        if not str(self.segment_name):
            raise ValueError("RF power sweep segment_name must not be empty")
        if not str(self.output_name):
            raise ValueError("RF power sweep output_name must not be empty")
        _require_int(self.gen_ch, "RF power sweep gen_ch", 0)
        for value, name in (
            (self.start, "RF power sweep start"),
            (self.stop, "RF power sweep stop"),
        ):
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"{name} must be a real number")
            if not isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
        _require_int(self.count, "RF power sweep count", 1)

    @property
    def points(self) -> Tuple[float, ...]:
        if self.count == 1:
            return (float(self.start),)
        values = np.linspace(
            float(self.start),
            float(self.stop),
            int(self.count),
            dtype=np.float64,
        )
        values[0] = float(self.start)
        values[-1] = float(self.stop)
        return tuple(float(value) for value in values)

    @property
    def axis_kind(self) -> str:
        return "rf_power"

    @property
    def coordinate_unit(self) -> str:
        return "dBm"


@dataclass(frozen=True)
class RampDurationSweep:
    """Sweep one AWG RAMP duration and derive every lane rate automatically.

    User coordinates are microseconds.  They are quantized to an arithmetic
    progression of fabric-clock cycles so the tProcessor can keep exact event
    timing with one outer loop.  The selected RAMP target still comes from its
    following SET, including all amplitude and cross-capacitance sweeps.
    """

    segment_name: str
    start: float
    stop: float
    count: int
    sequence_fabric_mhz: float

    def __post_init__(self):
        if not str(self.segment_name):
            raise ValueError("RAMP duration sweep segment_name must not be empty")
        _require_positive_real(self.start, "RAMP duration sweep start")
        _require_positive_real(self.stop, "RAMP duration sweep stop")
        _require_int(self.count, "RAMP duration sweep count", 1)
        _require_positive_real(
            self.sequence_fabric_mhz,
            "RAMP duration sweep sequence_fabric_mhz",
        )
        if self.count > 1 and self.duration_step_cycles == 0:
            raise ValueError(
                "RAMP duration sweep range is smaller than one fabric cycle "
                "per requested point"
            )
        if any(value < 1 for value in self.duration_cycles_points):
            raise ValueError("every RAMP duration sweep point must be positive")

    @property
    def output_name(self) -> str:
        return "all_awg_outputs"

    @property
    def start_cycles(self) -> int:
        return cycles_from_us(self.start, self.sequence_fabric_mhz)

    @property
    def stop_cycles(self) -> int:
        return cycles_from_us(self.stop, self.sequence_fabric_mhz)

    @property
    def duration_step_cycles(self) -> int:
        if self.count <= 1:
            return 0
        return _round_div_nearest(
            self.stop_cycles - self.start_cycles,
            self.count - 1,
        )

    @property
    def duration_cycles_points(self) -> Tuple[int, ...]:
        return tuple(
            self.start_cycles + index * self.duration_step_cycles
            for index in range(self.count)
        )

    @property
    def points(self) -> Tuple[float, ...]:
        return tuple(
            float(cycles) / float(self.sequence_fabric_mhz)
            for cycles in self.duration_cycles_points
        )

    @property
    def axis_kind(self) -> str:
        return "ramp_duration"

    @property
    def coordinate_unit(self) -> str:
        return "us"


@dataclass(frozen=True)
class HoldDurationSweep:
    """Sweep one SET segment's hold duration in microseconds.

    User coordinates are quantized to an arithmetic progression of AWG
    fabric-clock cycles. The SET command still executes at the segment start;
    this axis moves every later command, RF event, and DDR trigger without
    unrolling Cartesian sweep points in tProcessor PMEM.
    """

    segment_name: str
    start: float
    stop: float
    count: int
    sequence_fabric_mhz: float

    def __post_init__(self):
        if not str(self.segment_name):
            raise ValueError("SET hold sweep segment_name must not be empty")
        _require_positive_real(self.start, "SET hold sweep start")
        _require_positive_real(self.stop, "SET hold sweep stop")
        _require_int(self.count, "SET hold sweep count", 1)
        _require_positive_real(
            self.sequence_fabric_mhz,
            "SET hold sweep sequence_fabric_mhz",
        )
        if self.count > 1 and self.duration_step_cycles == 0:
            raise ValueError(
                "SET hold sweep range is smaller than one fabric cycle "
                "per requested point"
            )
        if any(value < 1 for value in self.duration_cycles_points):
            raise ValueError("every SET hold sweep point must be positive")

    @property
    def output_name(self) -> str:
        return "all_awg_outputs"

    @property
    def start_cycles(self) -> int:
        return cycles_from_us(self.start, self.sequence_fabric_mhz)

    @property
    def stop_cycles(self) -> int:
        return cycles_from_us(self.stop, self.sequence_fabric_mhz)

    @property
    def duration_step_cycles(self) -> int:
        if self.count <= 1:
            return 0
        return _round_div_nearest(
            self.stop_cycles - self.start_cycles,
            self.count - 1,
        )

    @property
    def duration_cycles_points(self) -> Tuple[int, ...]:
        return tuple(
            self.start_cycles + index * self.duration_step_cycles
            for index in range(self.count)
        )

    @property
    def points(self) -> Tuple[float, ...]:
        return tuple(
            float(cycles) / float(self.sequence_fabric_mhz)
            for cycles in self.duration_cycles_points
        )

    @property
    def axis_kind(self) -> str:
        return "hold_duration"

    @property
    def coordinate_unit(self) -> str:
        return "us"


@dataclass(frozen=True)
class BiasTCompensationConfig:
    """Per-shot opposite-polarity area compensation settings.

    In ``fixed_voltage`` mode, ``amplitude`` is a positive normalized
    physical-AWG voltage and the compensation duration varies with pulse area.
    In ``fixed_time`` mode, ``fixed_duration_cycles`` is held constant and the
    opposite-polarity voltage varies with pulse area. Every independent output
    starts at one common time.
    """

    amplitude: float
    mode: str = "fixed_voltage"
    fixed_duration_cycles: Optional[int] = None
    duration_frac_bits: int = DEFAULT_BIAS_T_DURATION_FRAC_BITS
    # Legacy API name: this is now one common pre-compensation guard, not a
    # delay inserted between outputs.
    inter_output_gap_cycles: int = 1

    def __post_init__(self):
        amplitude = _require_amplitude(self.amplitude, "Bias-T compensation amplitude")
        if amplitude <= 0.0:
            raise ValueError("Bias-T compensation amplitude must be positive")
        if self.mode not in BIAS_T_COMPENSATION_MODES:
            raise ValueError(
                f"Bias-T compensation mode must be one of "
                f"{BIAS_T_COMPENSATION_MODES}"
            )
        if self.mode == "fixed_time":
            _require_int(
                self.fixed_duration_cycles,
                "Bias-T fixed duration cycles",
                1,
            )
        elif self.fixed_duration_cycles is not None:
            _require_int(
                self.fixed_duration_cycles,
                "Bias-T fixed duration cycles",
                1,
            )
        frac_bits = _require_int(
            self.duration_frac_bits,
            "Bias-T duration fractional bits",
            1,
        )
        if frac_bits > 24:
            raise ValueError("Bias-T duration fractional bits must be <= 24")
        _require_int(
            self.inter_output_gap_cycles,
            "Bias-T common guard cycles",
            0,
        )

    @property
    def compensation_type(self) -> str:
        return "dc"


@dataclass(frozen=True)
class RCCompensationConfig:
    """Continuous FPGA high-pass inverse, independent of the DC area pulse."""

    tau_us: float

    def __post_init__(self):
        _require_positive_real(self.tau_us, "RC tau_us")
        if not 10 <= self.tau_us <= 1_000_000:
            raise ValueError("RC tau must be between 10 us and 1000 ms")


@dataclass(frozen=True)
class BiasTCompensationPreview:
    """Ideal physical-AWG area and its quantized compensation pulse."""

    output_index: int
    output_name: str
    pulse_area: float
    target_amplitude: float
    duration_cycles: int
    residual_area: float


@dataclass(frozen=True)
class ReadoutConfig:
    """Optional readout/trigger configuration for each sweep experiment."""

    ro_ch: int
    length: int
    freq: int = 0
    freq_mhz: Optional[float] = None
    phrst: int = 0
    at_segment: Optional[str] = None
    timing_reference: str = "segment_end"
    measure_delay_tproc_cycles: int = 0
    trigger_width_tproc_cycles: int = 10
    wait: bool = True

    def __post_init__(self):
        _require_int(self.ro_ch, "ro_ch", 0)
        _require_int(self.length, "length", 1)
        if self.freq_mhz is not None and not isfinite(float(self.freq_mhz)):
            raise ValueError("readout freq_mhz must be finite")
        if _require_int(self.phrst, "readout phrst", 0) != 0:
            raise ValueError("readout phrst is fixed to 0")
        if self.timing_reference not in {"segment_start", "segment_end"}:
            raise ValueError(
                "readout timing_reference must be segment_start or segment_end"
            )
        _require_int(self.measure_delay_tproc_cycles, "measure_delay_tproc_cycles", 0)
        _require_int(self.trigger_width_tproc_cycles, "trigger_width_tproc_cycles", 1)


@dataclass(frozen=True)
class RfPulseConfig:
    """RF pulse emitted during a named SET/gate segment.

    Pulses up to 65,535 generator-fabric cycles use the regular one-shot
    command. Longer pulses use a short periodic word followed by a timed
    zero-gain one-shot stop command, avoiding the 16-bit length-field limit.
    A duration sweep uses one-shot length words when all its points fit;
    if any point is longer, the entire duration axis uses periodic mode.
    """

    gen_ch: int
    at_segment: str
    length_cycles: int
    gain: int
    freq_mhz: float = 0.0
    phase_degrees: float = 0.0
    nqz: int = 1
    delay_tproc_cycles: int = 0
    phrst: int = 0
    stdysel: str = "zero"
    require_within_segment: bool = True
    sweep_gain_codes: Tuple[int, ...] = ()
    sweep_gain_shape: Tuple[int, int] = (0, 0)
    power_calibration_run_id: Optional[int] = None
    event_id: str = ""
    pulse_name: str = "RF pulse"
    frequency_parameter: str = ""
    duration_parameter: str = ""
    preceding_duration_parameters: Tuple[str, ...] = ()

    def __post_init__(self):
        _require_int(self.gen_ch, "gen_ch", 0)
        _require_int(self.length_cycles, "length_cycles", 1)
        _require_int(self.gain, "gain")
        _require_int(self.nqz, "nqz", 1)
        _require_int(self.delay_tproc_cycles, "delay_tproc_cycles", 0)
        if _require_int(self.phrst, "RF output phrst", 0) != 0:
            raise ValueError("RF output phrst is fixed to 0")
        if not str(self.at_segment):
            raise ValueError("at_segment must not be empty")
        if not str(self.event_id):
            object.__setattr__(
                self,
                "event_id",
                f"rf_gen_{int(self.gen_ch)}_single",
            )
        if not str(self.pulse_name):
            raise ValueError("RF pulse_name must not be empty")
        if self.frequency_parameter and not str(
            self.frequency_parameter
        ).isidentifier():
            raise ValueError("RF frequency_parameter must be an identifier")
        if self.duration_parameter and not str(
            self.duration_parameter
        ).isidentifier():
            raise ValueError("RF duration_parameter must be an identifier")
        preceding = tuple(str(item) for item in self.preceding_duration_parameters)
        if any(not item.isidentifier() for item in preceding):
            raise ValueError(
                "RF preceding_duration_parameters must contain identifiers"
            )
        object.__setattr__(self, "preceding_duration_parameters", preceding)
        if not isfinite(float(self.freq_mhz)):
            raise ValueError("freq_mhz must be finite")
        if not isfinite(float(self.phase_degrees)):
            raise ValueError("phase_degrees must be finite")
        gain_codes = tuple(
            _require_int(value, "RF sweep gain code", 1)
            for value in self.sweep_gain_codes
        )
        if any(value > 32767 for value in gain_codes):
            raise ValueError("RF sweep gain code exceeds 32767")
        gain_shape = tuple(
            _require_int(value, "RF sweep gain shape", 0)
            for value in self.sweep_gain_shape
        )
        if len(gain_shape) != 2:
            raise ValueError("RF sweep gain shape must contain frequency and power counts")
        if gain_codes:
            if any(value < 1 for value in gain_shape):
                raise ValueError("RF sweep gain shape entries must be positive")
            if int(np.prod(gain_shape, dtype=np.int64)) != len(gain_codes):
                raise ValueError(
                    "RF sweep gain table size does not match sweep_gain_shape"
                )
        elif gain_shape != (0, 0):
            raise ValueError(
                "RF sweep gain shape must be (0, 0) when no gain table is supplied"
            )
        if self.power_calibration_run_id is not None:
            _require_int(
                self.power_calibration_run_id,
                "RF power calibration run ID",
                1,
            )


@dataclass(frozen=True)
class DdrFirReadoutConfig:
    """HWH-selected FIR-DDR capture performed once per repetition."""

    ro_ch: int
    samples_per_trigger: int
    at_segment: str
    readout_freq_mhz: float = 0.0
    trigger_delay_tproc_cycles: int = 0
    trigger_width_tproc_cycles: int = 12
    readout_period_cycles: int = 65535
    margin_input_samples: int = 1024
    address: int = 0
    stride_bytes: Optional[int] = None
    force_overwrite: bool = False
    settle_seconds: float = 0.05
    fpga_trigger_delay_samples: Optional[int] = None

    def __post_init__(self):
        _require_int(self.ro_ch, "ro_ch", 0)
        _require_int(self.samples_per_trigger, "samples_per_trigger", 1)
        if self.fpga_trigger_delay_samples is not None:
            _require_int(
                self.fpga_trigger_delay_samples,
                "fpga_trigger_delay_samples",
                0,
            )
            if self.fpga_trigger_delay_samples > 0xFFFF_FFFF:
                raise ValueError("fpga_trigger_delay_samples must fit in 32 bits")
        _require_int(self.trigger_delay_tproc_cycles, "trigger_delay_tproc_cycles", 0)
        _require_int(self.trigger_width_tproc_cycles, "trigger_width_tproc_cycles", 1)
        period = _require_int(self.readout_period_cycles, "readout_period_cycles", 1)
        if period > 65535:
            raise ValueError("readout_period_cycles must fit in 16 bits")
        _require_int(self.margin_input_samples, "margin_input_samples", 0)
        _require_int(self.address, "address", 0)
        if self.stride_bytes is not None:
            _require_int(self.stride_bytes, "stride_bytes", 1)
        if not str(self.at_segment):
            raise ValueError("at_segment must not be empty")
        if not isfinite(float(self.readout_freq_mhz)):
            raise ValueError("readout_freq_mhz must be finite")
        if float(self.settle_seconds) < 0:
            raise ValueError("settle_seconds must be nonnegative")


@dataclass(frozen=True)
class FineTuneDdrResult:
    """I/Q samples grouped by Cartesian point and repetition."""

    sweep_points: np.ndarray
    iq: np.ndarray
    reserved_physical_words: Optional[int] = None
    sweep_axes: Tuple[
        Union[
            AmplitudeSweep,
            HoldDurationSweep,
            RampDurationSweep,
            RfDurationSweep,
            RfFrequencySweep,
            RfPowerSweep,
        ],
        ...,
    ] = ()
    sweep_shape: Tuple[int, ...] = (1,)
    cross_capacitance: Optional[np.ndarray] = None
    sample_rate_hz: float = 1_000_000.0
    fir_rate_profile: str = "1_msps"
    acquisition_source: str = "fir_ddr"
    accumulation_repetitions: int = 1
    iq_scale_log2: int = 0
    iq_component_bits: int = 16

    @property
    def analysis_iq(self) -> np.ndarray:
        """Input-code units for plots/calibration; ``iq`` stays raw integer."""
        return np.ldexp(self.iq.astype(np.float64), -self.iq_scale_log2)

    @property
    def mean_iq(self) -> np.ndarray:
        """Average the N repetitions while preserving sample and I/Q axes."""
        return self.analysis_iq.mean(axis=1)

    @property
    def i(self) -> np.ndarray:
        return self.iq[..., 0]

    @property
    def q(self) -> np.ndarray:
        return self.iq[..., 1]

    @property
    def iq_grid(self) -> np.ndarray:
        """IQ reshaped to ``(*sweep_shape, repetitions, samples, I/Q)``."""
        return self.iq.reshape(*self.sweep_shape, *self.iq.shape[1:])

    @property
    def mean_iq_grid(self) -> np.ndarray:
        """Repetition-averaged IQ retaining all Cartesian sweep axes."""
        return np.ldexp(self.iq_grid.astype(np.float64), -self.iq_scale_log2).mean(axis=len(self.sweep_shape))


@dataclass(frozen=True)
class CompiledCommand:
    point_index: int
    segment_index: int
    segment_name: str
    output_index: int
    output_name: str
    gen_ch: int
    kind: str
    target_code: int
    duration_samples: int
    step: int
    words: Tuple[int, int, int, int, int]
    command_slot: int = 0


@dataclass(frozen=True)
class CompiledPoint:
    sweep_value: Union[float, Tuple[float, ...]]
    segment_commands: Tuple[Tuple[CompiledCommand, ...], ...]


class FineTuneSequence:
    """A named multi-output sequence composed of SET and RAMP segments."""

    def __init__(self, outputs: Union[int, Sequence[str]]):
        if isinstance(outputs, Integral):
            count = _require_int(outputs, "outputs", 1)
            output_names = tuple(f"out{index}" for index in range(count))
        else:
            output_names = tuple(str(name) for name in outputs)
        if not output_names:
            raise ValueError("at least one output is required")
        if len(output_names) > MAX_OUTPUTS:
            raise ValueError(f"at most {MAX_OUTPUTS} outputs are supported")
        if len(set(output_names)) != len(output_names):
            raise ValueError("output names must be unique")
        if any(not name for name in output_names):
            raise ValueError("output names must not be empty")

        self.output_names = output_names
        self.segments = []
        self.sweeps = []
        self.rf_segment_length_extensions = []
        self._sweep_coordinate_cache: Optional[np.ndarray] = None
        self.cross_capacitance = np.eye(self.n_outputs, dtype=float)
        self.bias_t_compensation: Optional[BiasTCompensationConfig] = None
        self.rc_compensation = None

    @property
    def n_outputs(self) -> int:
        return len(self.output_names)

    def set_cross_capacitance(self, matrix):
        """Set the virtual-gate to physical-AWG linear transform.

        Every SET and its dependent RAMP use ``physical = matrix @ virtual``.
        ``matrix[dst, src]`` is therefore the contribution of virtual gate
        ``src`` to physical AWG output ``dst``.  Diagonal entries remain one.
        """
        values = np.asarray(matrix, dtype=float)
        expected_shape = (self.n_outputs, self.n_outputs)
        if values.shape != expected_shape:
            raise ValueError(
                f"cross-capacitance matrix shape must be {expected_shape}, "
                f"received {values.shape}"
            )
        if not np.all(np.isfinite(values)):
            raise ValueError("cross-capacitance coefficients must be finite")
        if not np.allclose(np.diag(values), 1.0, rtol=0.0, atol=1.0e-12):
            raise ValueError("cross-capacitance diagonal entries must equal 1")
        self.cross_capacitance = values.copy()
        return self

    def set_rc_compensation(self, tau_us: Real, *, enabled: bool = True):
        """Enable stateful FPGA compensation; no software waveform rewriting."""
        if not isinstance(enabled, (bool, np.bool_)):
            raise TypeError("RC compensation enabled must be boolean")
        self.rc_compensation = RCCompensationConfig(float(tau_us)) if enabled else None
        return self

    def set_bias_t_compensation(
        self,
        amplitude: Real = 0.1,
        *,
        enabled: bool = True,
        mode: str = "fixed_voltage",
        fixed_duration_cycles: Optional[int] = None,
        duration_frac_bits: int = DEFAULT_BIAS_T_DURATION_FRAC_BITS,
        inter_output_gap_cycles: int = 1,
    ):
        """Enable opposite-polarity Bias-T area compensation per shot.

        The supplied positive amplitude is in normalized physical-AWG units.
        ``fixed_time`` ignores it for output generation and calculates the
        required voltage for ``fixed_duration_cycles``. Compensation is
        applied after the pulse/readout portion of each shot. Disabling the
        option restores the original sequence behavior exactly.
        """
        if not isinstance(enabled, (bool, np.bool_)):
            raise TypeError("Bias-T compensation enabled must be boolean")
        if not enabled:
            self.bias_t_compensation = None
            return self
        self.bias_t_compensation = BiasTCompensationConfig(
            amplitude=float(amplitude),
            mode=str(mode),
            fixed_duration_cycles=fixed_duration_cycles,
            duration_frac_bits=duration_frac_bits,
            inter_output_gap_cycles=inter_output_gap_cycles,
        )
        return self


    @property
    def sweep(self) -> Optional[AmplitudeSweep]:
        """Legacy view of the first sweep axis, retained for single-sweep code."""
        return next(
            (
                sweep
                for sweep in self.sweeps
                if isinstance(sweep, AmplitudeSweep)
            ),
            None,
        )

    @sweep.setter
    def sweep(self, value: Optional[AmplitudeSweep]) -> None:
        self.sweeps = [] if value is None else [value]
        self._sweep_coordinate_cache = None

    def _coerce_amplitudes(
        self,
        amplitudes: Union[Real, Sequence[Optional[Real]], Mapping[str, Optional[Real]]],
    ) -> Tuple[Optional[float], ...]:
        if isinstance(amplitudes, Mapping):
            unknown = set(amplitudes) - set(self.output_names)
            if unknown:
                raise KeyError(f"unknown output name(s): {sorted(unknown)}")
            raw = [amplitudes.get(name) for name in self.output_names]
        elif isinstance(amplitudes, Real) and not isinstance(amplitudes, bool):
            if self.n_outputs != 1:
                raise ValueError("a scalar amplitude is valid only for a one-output sequence")
            raw = [amplitudes]
        else:
            raw = list(amplitudes)
            if len(raw) != self.n_outputs:
                raise ValueError(
                    f"expected {self.n_outputs} amplitudes, received {len(raw)}"
                )

        converted = []
        for index, value in enumerate(raw):
            if value is None:
                converted.append(None)
            else:
                converted.append(
                    _require_amplitude(value, f"amplitude[{self.output_names[index]}]")
                )
        if all(value is None for value in converted):
            raise ValueError("a segment must update at least one output")
        return tuple(converted)

    def _add_segment(self, kind: str, name: str, amplitudes, duration_cycles: int):
        name = str(name)
        if not name:
            raise ValueError("segment name must not be empty")
        if any(segment.name == name for segment in self.segments):
            raise ValueError(f"duplicate segment name {name!r}")
        duration_cycles = _require_int(duration_cycles, "duration_cycles", 1)
        if kind == "ramp":
            values = (None,) * self.n_outputs
        else:
            values = self._coerce_amplitudes(amplitudes)
        self.segments.append(PulseSegment(name, kind, values, duration_cycles))
        return self

    def add_set(self, name: str, amplitudes, duration_cycles: int):
        """Immediately set selected outputs, then hold for fabric cycles."""
        return self._add_segment("set", name, amplitudes, duration_cycles)

    def add_ramp(self, name: str, duration_cycles: int):
        """Transition to the following SET levels over fabric-clock cycles.

        A RAMP carries no independent amplitude.  Its target is resolved from
        the immediately following SET, so changing or sweeping that SET also
        updates the incoming RAMP target and the outgoing RAMP start value.
        """
        return self._add_segment("ramp", name, None, duration_cycles)

    def set_amplitude_sweep(
        self,
        segment: str,
        output: Union[str, int],
        start: Real,
        stop: Real,
        count: int,
    ):
        """Replace all sweep axes with one axis for backward compatibility."""
        previous_sweeps = self.sweeps
        self.sweeps = []
        self._sweep_coordinate_cache = None
        try:
            return self.add_amplitude_sweep(segment, output, start, stop, count)
        except Exception:
            self.sweeps = previous_sweeps
            self._sweep_coordinate_cache = None
            raise

    def add_amplitude_sweep(
        self,
        segment: str,
        output: Union[str, int],
        start: Real,
        stop: Real,
        count: int,
    ):
        """Add one independent Cartesian sweep axis.

        Re-adding the same ``(segment, output)`` target updates that axis while
        preserving the order of all other axes.  The last axis varies fastest.
        """
        segment_name = str(segment)
        if not segment_name:
            raise ValueError("swept SET segment name must not be empty")

        if isinstance(output, Integral):
            output_index = _require_int(output, "output", 0)
            if output_index >= self.n_outputs:
                raise IndexError("output index is out of range")
            output_name = self.output_names[output_index]
        else:
            output_name = str(output)
            if output_name not in self.output_names:
                raise KeyError(f"unknown output name {output_name!r}")
            output_index = self.output_names.index(output_name)

        by_name = {item.name: item for item in self.segments}
        if segment_name not in by_name:
            raise KeyError(f"unknown segment name {segment_name!r}")
        swept_segment = by_name[segment_name]
        if swept_segment.kind != "set":
            raise ValueError("amplitude sweep must select a SET segment")
        if swept_segment.amplitudes[output_index] is None:
            raise ValueError(
                f"SET segment {segment_name!r} does not update output {output_name!r}"
            )

        count = _require_int(count, "count", 1)
        start = _require_amplitude(start, "sweep start")
        stop = _require_amplitude(stop, "sweep stop")
        new_sweep = AmplitudeSweep(segment_name, output_name, start, stop, count)
        target = (segment_name, output_name)
        for index, current in enumerate(self.sweeps):
            if (current.segment_name, current.output_name) == target:
                self.sweeps[index] = new_sweep
                break
        else:
            self.sweeps.append(new_sweep)
        self._sweep_coordinate_cache = None
        return self

    def clear_amplitude_sweeps(self):
        self.sweeps = [
            sweep
            for sweep in self.sweeps
            if not isinstance(sweep, AmplitudeSweep)
        ]
        self._sweep_coordinate_cache = None
        return self

    def set_rf_segment_length_extension(
        self,
        segment: str,
        gen_ch: int,
        base_duration_cycles: int,
        *,
        parameter_multiplicities: Mapping[str, int] = (),
    ):
        """Extend one SET by the aggregate duration of one RF sequence.

        Only one RF generator owns automatic extension of a SET segment. A
        composite sequence may use any number of named duration parameters;
        their multiplicities capture shared parameters without adding sweep
        points or DMEM tables.
        """
        segment_name = str(segment)
        by_name = {item.name: item for item in self.segments}
        if segment_name not in by_name:
            raise KeyError(f"unknown segment name {segment_name!r}")
        if by_name[segment_name].kind != "set":
            raise ValueError("RF segment extension must select a SET segment")
        gen_ch = _require_int(gen_ch, "RF segment extension gen_ch", 0)
        if isinstance(parameter_multiplicities, Mapping):
            multiplicities = tuple(parameter_multiplicities.items())
        else:
            multiplicities = tuple(parameter_multiplicities)
        extension = RfSegmentLengthExtension(
            segment_name=segment_name,
            gen_ch=gen_ch,
            base_duration_cycles=_require_int(
                base_duration_cycles,
                "RF segment extension base_duration_cycles",
                1,
            ),
            parameter_multiplicities=multiplicities,
        )
        conflicting = [
            current
            for current in self.rf_segment_length_extensions
            if current.segment_name == segment_name
            and current.gen_ch != gen_ch
        ]
        if conflicting:
            raise ValueError(
                "only one RF generator may automatically extend a given "
                "AWG segment"
            )
        for index, current in enumerate(self.rf_segment_length_extensions):
            if (
                current.segment_name,
                current.gen_ch,
            ) == (segment_name, gen_ch):
                self.rf_segment_length_extensions[index] = extension
                break
        else:
            self.rf_segment_length_extensions.append(extension)
        return self

    def _rf_segment_length_extension(
        self,
        segment_name: str,
        gen_ch: Optional[int] = None,
    ) -> Optional[RfSegmentLengthExtension]:
        matches = [
            extension
            for extension in self.rf_segment_length_extensions
            if extension.segment_name == str(segment_name)
            and (gen_ch is None or extension.gen_ch == int(gen_ch))
        ]
        if len(matches) > 1:
            raise RuntimeError(
                f"SET segment {segment_name!r} has multiple RF extension owners"
            )
        return matches[0] if matches else None

    def rf_duration_extension_multiplier(self, axis: RfDurationSweep) -> int:
        """Return an axis's contribution count to its SET extension."""
        extension = self._rf_segment_length_extension(
            axis.segment_name,
            axis.gen_ch,
        )
        if extension is None:
            return 1
        return extension.multiplier(axis.parameter_name)

    def add_rf_duration_sweep(
        self,
        segment: str,
        gen_ch: int,
        start_us: Real,
        stop_us: Real,
        count: int,
        *,
        segment_length_mode: str = "fixed",
        sequence_fabric_mhz: Real = 300.0,
        parameter_name: str = "",
        output_name: Optional[str] = None,
    ):
        """Add or replace one RF pulse-duration Cartesian sweep axis."""
        segment_name = str(segment)
        by_name = {item.name: item for item in self.segments}
        if segment_name not in by_name:
            raise KeyError(f"unknown segment name {segment_name!r}")
        if by_name[segment_name].kind != "set":
            raise ValueError("RF duration sweep must select a SET segment")
        gen_ch = _require_int(gen_ch, "RF duration sweep gen_ch", 0)
        parameter_name = str(parameter_name)
        if parameter_name and not parameter_name.isidentifier():
            raise ValueError(
                "RF duration sweep parameter_name must be an identifier"
            )
        if output_name is None:
            output_name = (
                f"rf_gen_{gen_ch}_{parameter_name}_duration"
                if parameter_name
                else f"rf_gen_{gen_ch}"
            )
        new_sweep = RfDurationSweep(
            segment_name=segment_name,
            output_name=str(output_name),
            gen_ch=gen_ch,
            start=float(start_us),
            stop=float(stop_us),
            count=_require_int(count, "RF duration sweep count", 1),
            segment_length_mode=str(segment_length_mode),
            sequence_fabric_mhz=float(sequence_fabric_mhz),
            parameter_name=parameter_name,
        )
        if new_sweep.segment_length_mode == "extend_by_rf_duration":
            conflicting = [
                sweep
                for sweep in self.sweeps
                if isinstance(sweep, RfDurationSweep)
                and sweep.segment_name == segment_name
                and sweep.gen_ch != gen_ch
                and sweep.segment_length_mode == "extend_by_rf_duration"
            ]
            if conflicting:
                raise ValueError(
                    "only one RF generator may automatically extend a given "
                    "AWG segment"
                )
        target = (segment_name, gen_ch, parameter_name)
        for index, current in enumerate(self.sweeps):
            if (
                isinstance(current, RfDurationSweep)
                and (
                    current.segment_name,
                    current.gen_ch,
                    current.parameter_name,
                ) == target
            ):
                self.sweeps[index] = new_sweep
                break
        else:
            self.sweeps.append(new_sweep)
        self._sweep_coordinate_cache = None
        return self

    def add_rf_frequency_sweep(
        self,
        segment: str,
        gen_ch: int,
        start_mhz: Real,
        stop_mhz: Real,
        count: int,
        parameter_name: str = "",
        output_name: Optional[str] = None,
    ):
        """Add or replace one RF-generator frequency sweep axis."""
        segment_name = str(segment)
        by_name = {item.name: item for item in self.segments}
        if segment_name not in by_name:
            raise KeyError(f"unknown segment name {segment_name!r}")
        if by_name[segment_name].kind != "set":
            raise ValueError("RF frequency sweep must select a SET segment")
        gen_ch = _require_int(gen_ch, "RF frequency sweep gen_ch", 0)
        parameter_name = str(parameter_name)
        if parameter_name and not parameter_name.isidentifier():
            raise ValueError("RF frequency parameter name must be an identifier")
        new_sweep = RfFrequencySweep(
            segment_name=segment_name,
            output_name=(
                str(output_name)
                if output_name is not None
                else (
                    f"rf_gen_{gen_ch}_{parameter_name}_frequency"
                    if parameter_name
                    else f"rf_gen_{gen_ch}_frequency"
                )
            ),
            gen_ch=gen_ch,
            start=float(start_mhz),
            stop=float(stop_mhz),
            count=_require_int(count, "RF frequency sweep count", 1),
            parameter_name=parameter_name,
        )
        target = (segment_name, gen_ch, parameter_name)
        for index, current in enumerate(self.sweeps):
            if (
                isinstance(current, RfFrequencySweep)
                and (
                    current.segment_name,
                    current.gen_ch,
                    current.parameter_name,
                ) == target
            ):
                self.sweeps[index] = new_sweep
                break
        else:
            self.sweeps.append(new_sweep)
        self._sweep_coordinate_cache = None
        return self

    def add_rf_power_sweep(
        self,
        segment: str,
        gen_ch: int,
        start_dbm: Real,
        stop_dbm: Real,
        count: int,
    ):
        """Add or replace one calibrated RF connector-power sweep axis."""
        segment_name = str(segment)
        by_name = {item.name: item for item in self.segments}
        if segment_name not in by_name:
            raise KeyError(f"unknown segment name {segment_name!r}")
        if by_name[segment_name].kind != "set":
            raise ValueError("RF power sweep must select a SET segment")
        gen_ch = _require_int(gen_ch, "RF power sweep gen_ch", 0)
        new_sweep = RfPowerSweep(
            segment_name=segment_name,
            output_name=f"rf_gen_{gen_ch}_power",
            gen_ch=gen_ch,
            start=float(start_dbm),
            stop=float(stop_dbm),
            count=_require_int(count, "RF power sweep count", 1),
        )
        target = (segment_name, gen_ch)
        for index, current in enumerate(self.sweeps):
            if (
                isinstance(current, RfPowerSweep)
                and (current.segment_name, current.gen_ch) == target
            ):
                self.sweeps[index] = new_sweep
                break
        else:
            self.sweeps.append(new_sweep)
        self._sweep_coordinate_cache = None
        return self

    def add_ramp_duration_sweep(
        self,
        segment: str,
        start_us: Real,
        stop_us: Real,
        count: int,
        *,
        sequence_fabric_mhz: Real = 300.0,
    ):
        """Add or replace one RAMP segment's duration/rate sweep axis.

        All RAMP duration axes are kept before voltage and RF-duration axes.
        Each RAMP owns an independent coefficient table, so the tProcessor
        never stores the full Cartesian point table.
        """
        segment_name = str(segment)
        by_name = {item.name: item for item in self.segments}
        if segment_name not in by_name:
            raise KeyError(f"unknown segment name {segment_name!r}")
        if by_name[segment_name].kind != "ramp":
            raise ValueError("RAMP duration sweep must select a RAMP segment")
        new_sweep = RampDurationSweep(
            segment_name=segment_name,
            start=float(start_us),
            stop=float(stop_us),
            count=_require_int(count, "RAMP duration sweep count", 1),
            sequence_fabric_mhz=float(sequence_fabric_mhz),
        )
        ramp_axes = [
            sweep
            for sweep in self.sweeps
            if isinstance(sweep, RampDurationSweep)
        ]
        for index, sweep in enumerate(ramp_axes):
            if sweep.segment_name == segment_name:
                ramp_axes[index] = new_sweep
                break
        else:
            ramp_axes.append(new_sweep)
        self.sweeps = ramp_axes + [
            sweep
            for sweep in self.sweeps
            if not isinstance(sweep, RampDurationSweep)
        ]
        self._sweep_coordinate_cache = None
        return self

    def add_hold_duration_sweep(
        self,
        segment: str,
        start_us: Real,
        stop_us: Real,
        count: int,
        *,
        sequence_fabric_mhz: Real = 300.0,
    ):
        """Add or replace one SET segment's hold-duration sweep axis.

        Duration-controlled axes stay outside voltage and RF-duration axes.
        RAMP duration axes remain first because their coefficient tables use
        that established ordering.
        """
        segment_name = str(segment)
        by_name = {item.name: item for item in self.segments}
        if segment_name not in by_name:
            raise KeyError(f"unknown segment name {segment_name!r}")
        if by_name[segment_name].kind != "set":
            raise ValueError("SET hold sweep must select a SET segment")
        new_sweep = HoldDurationSweep(
            segment_name=segment_name,
            start=float(start_us),
            stop=float(stop_us),
            count=_require_int(count, "SET hold sweep count", 1),
            sequence_fabric_mhz=float(sequence_fabric_mhz),
        )
        ramp_axes = [
            sweep
            for sweep in self.sweeps
            if isinstance(sweep, RampDurationSweep)
        ]
        hold_axes = [
            sweep
            for sweep in self.sweeps
            if isinstance(sweep, HoldDurationSweep)
        ]
        for index, sweep in enumerate(hold_axes):
            if sweep.segment_name == segment_name:
                hold_axes[index] = new_sweep
                break
        else:
            hold_axes.append(new_sweep)
        self.sweeps = ramp_axes + hold_axes + [
            sweep
            for sweep in self.sweeps
            if not isinstance(
                sweep,
                (RampDurationSweep, HoldDurationSweep),
            )
        ]
        self._sweep_coordinate_cache = None
        return self

    def clear_ramp_duration_sweep(self, segment: Optional[str] = None):
        segment_name = None if segment is None else str(segment)
        self.sweeps = [
            sweep
            for sweep in self.sweeps
            if not isinstance(sweep, RampDurationSweep)
            or (
                segment_name is not None
                and sweep.segment_name != segment_name
            )
        ]
        self._sweep_coordinate_cache = None
        return self

    def clear_hold_duration_sweep(self, segment: Optional[str] = None):
        segment_name = None if segment is None else str(segment)
        self.sweeps = [
            sweep
            for sweep in self.sweeps
            if not isinstance(sweep, HoldDurationSweep)
            or (
                segment_name is not None
                and sweep.segment_name != segment_name
            )
        ]
        self._sweep_coordinate_cache = None
        return self

    def clear_rf_duration_sweeps(self):
        self.sweeps = [
            sweep
            for sweep in self.sweeps
            if not isinstance(sweep, RfDurationSweep)
        ]
        self._sweep_coordinate_cache = None
        return self

    def clear_rf_frequency_sweeps(self):
        self.sweeps = [
            sweep
            for sweep in self.sweeps
            if not isinstance(sweep, RfFrequencySweep)
        ]
        self._sweep_coordinate_cache = None
        return self

    def clear_rf_power_sweeps(self):
        self.sweeps = [
            sweep
            for sweep in self.sweeps
            if not isinstance(sweep, RfPowerSweep)
        ]
        self._sweep_coordinate_cache = None
        return self

    @property
    def sweep_axes(
        self,
    ) -> Tuple[
        Union[
            AmplitudeSweep,
            HoldDurationSweep,
            RampDurationSweep,
            RfDurationSweep,
            RfFrequencySweep,
            RfPowerSweep,
        ],
        ...,
    ]:
        return tuple(self.sweeps)

    def segment_duration_cycles_at(
        self,
        point_index: int,
        segment_index: int,
    ) -> int:
        """Return the point-specific AWG segment length in fabric cycles."""
        point_index = _require_int(point_index, "point_index", 0)
        segment_index = _require_int(segment_index, "segment_index", 0)
        if segment_index >= len(self.segments):
            raise IndexError("segment_index is out of range")
        segment = self.segments[segment_index]
        duration = int(segment.duration_cycles)
        extension = self._rf_segment_length_extension(segment.name)
        if extension is not None:
            duration += int(extension.base_duration_cycles)
        coordinate = self.sweep_coordinate(point_index)
        for axis_index, sweep in enumerate(self.sweeps):
            if (
                isinstance(sweep, RampDurationSweep)
                and sweep.segment_name == self.segments[segment_index].name
            ):
                duration = int(sweep.duration_cycles_points[
                    np.unravel_index(
                        point_index,
                        self.sweep_shape,
                        order="C",
                    )[axis_index]
                ])
            elif (
                isinstance(sweep, HoldDurationSweep)
                and sweep.segment_name == self.segments[segment_index].name
            ):
                duration = int(sweep.duration_cycles_points[
                    np.unravel_index(
                        point_index,
                        self.sweep_shape,
                        order="C",
                    )[axis_index]
                ])
            elif (
                isinstance(sweep, RfDurationSweep)
                and sweep.segment_length_mode == "extend_by_rf_duration"
                and sweep.segment_name == segment.name
            ):
                if extension is None:
                    # Backward-compatible direct API behavior: without an
                    # aggregate extension registration, this axis contributes
                    # its complete duration as before.
                    duration += cycles_from_us(
                        coordinate[axis_index],
                        sweep.sequence_fabric_mhz,
                    )
                else:
                    multiplier = extension.multiplier(sweep.parameter_name)
                    if multiplier:
                        current_cycles = cycles_from_us(
                            coordinate[axis_index],
                            sweep.sequence_fabric_mhz,
                        )
                        initial_cycles = cycles_from_us(
                            sweep.start,
                            sweep.sequence_fabric_mhz,
                        )
                        duration += multiplier * (
                            current_cycles - initial_cycles
                        )
        if duration < 1:
            raise ValueError(
                f"RF-extended SET segment {segment.name!r} has invalid "
                f"duration {duration} cycles"
            )
        return duration

    @property
    def sweep_shape(self) -> Tuple[int, ...]:
        return tuple(item.count for item in self.sweeps) or (1,)

    @property
    def sweep_coordinates(self) -> np.ndarray:
        """Cartesian coordinates with shape ``(point_count, axis_count)``."""
        if self._sweep_coordinate_cache is None:
            if not self.sweeps:
                coordinates = np.empty((1, 0), dtype=float)
            else:
                shape = tuple(int(item.count) for item in self.sweeps)
                point_count = int(np.prod(shape, dtype=np.int64))
                coordinates = np.empty(
                    (point_count, len(self.sweeps)),
                    dtype=float,
                )
                for axis_index, item in enumerate(self.sweeps):
                    repeats = int(
                        np.prod(shape[axis_index + 1:] or (1,), dtype=np.int64)
                    )
                    tiles = int(
                        np.prod(shape[:axis_index] or (1,), dtype=np.int64)
                    )
                    coordinates[:, axis_index] = np.tile(
                        np.repeat(np.asarray(item.points, dtype=float), repeats),
                        tiles,
                    )
            self._sweep_coordinate_cache = coordinates
        return self._sweep_coordinate_cache

    @property
    def sweep_point_count(self) -> int:
        return int(np.prod(self.sweep_shape, dtype=np.int64))

    def sweep_coordinate(self, point_index: int) -> Tuple[float, ...]:
        point_index = _require_int(point_index, "point_index", 0)
        if point_index >= self.sweep_point_count:
            raise IndexError("point_index is out of range")
        if not self.sweeps:
            return ()
        indices = np.unravel_index(
            point_index,
            self.sweep_shape,
            order="C",
        )
        return tuple(
            float(axis.points[axis_index])
            for axis, axis_index in zip(self.sweeps, indices)
        )

    @property
    def sweep_points(self) -> np.ndarray:
        if not self.sweeps:
            return np.array([0.0], dtype=float)
        if len(self.sweeps) == 1:
            return self.sweep_coordinates[:, 0].copy()
        return self.sweep_coordinates.copy()

    def _validate(self):
        if not self.segments:
            raise ValueError("the sequence has no segments")
        ramp_duration_axes = [
            axis
            for axis in self.sweeps
            if isinstance(axis, RampDurationSweep)
        ]
        ramp_targets = [axis.segment_name for axis in ramp_duration_axes]
        if len(set(ramp_targets)) != len(ramp_targets):
            raise ValueError(
                "each RAMP segment may have only one duration/rate sweep"
            )
        ramp_axis_count = len(ramp_duration_axes)
        if any(
            not isinstance(axis, RampDurationSweep)
            for axis in self.sweeps[:ramp_axis_count]
        ):
            raise ValueError(
                "RAMP duration/rate sweeps must be the outermost sweep axes"
            )
        hold_duration_axes = [
            axis
            for axis in self.sweeps
            if isinstance(axis, HoldDurationSweep)
        ]
        hold_targets = [axis.segment_name for axis in hold_duration_axes]
        if len(set(hold_targets)) != len(hold_targets):
            raise ValueError(
                "each SET segment may have only one hold-duration sweep"
            )
        duration_axis_count = ramp_axis_count + len(hold_duration_axes)
        if any(
            not isinstance(axis, (RampDurationSweep, HoldDurationSweep))
            for axis in self.sweeps[:duration_axis_count]
        ):
            raise ValueError(
                "RAMP and SET hold duration sweeps must be the outermost "
                "sweep axes"
            )
        if any(
            isinstance(axis, RampDurationSweep)
            for axis in self.sweeps[
                ramp_axis_count:duration_axis_count
            ]
        ):
            raise ValueError(
                "RAMP duration axes must precede SET hold-duration axes"
            )
        segment_by_name = {
            segment.name: segment for segment in self.segments
        }
        for axis in hold_duration_axes:
            segment = segment_by_name.get(axis.segment_name)
            if segment is None or segment.kind != "set":
                raise ValueError(
                    f"unknown SET hold sweep segment {axis.segment_name!r}"
                )
        for axis_type, label in (
            (RfDurationSweep, "duration"),
            (RfFrequencySweep, "frequency"),
            (RfPowerSweep, "power"),
        ):
            axes = [
                axis for axis in self.sweeps if isinstance(axis, axis_type)
            ]
            targets = [
                (
                    int(axis.gen_ch),
                    str(axis.segment_name),
                    str(axis.parameter_name)
                    if isinstance(axis, (RfDurationSweep, RfFrequencySweep))
                    else "",
                )
                for axis in axes
            ]
            if len(set(targets)) != len(targets):
                raise ValueError(
                    f"each RF pulse may have only one {label} sweep"
                )
            for axis in axes:
                segment = segment_by_name.get(axis.segment_name)
                if segment is None or segment.kind != "set":
                    raise ValueError(
                        f"unknown RF {label} sweep segment "
                        f"{axis.segment_name!r}"
                    )
        first = self.segments[0]
        if first.kind != "set" or any(value is None for value in first.amplitudes):
            raise ValueError(
                "the first segment must be a SET with values for every output"
            )
        for index, segment in enumerate(self.segments):
            if segment.kind != "ramp":
                continue
            if index + 1 >= len(self.segments) or self.segments[index + 1].kind != "set":
                raise ValueError(
                    f"RAMP {segment.name!r} must be immediately followed by a SET; "
                    "that SET defines the RAMP target"
                )

    def _virtual_set_amplitudes_at(
        self, point_index: int, segment_index: int
    ) -> Tuple[Optional[float], ...]:
        segment = self.segments[segment_index]
        if segment.kind != "set":
            raise ValueError("_virtual_set_amplitudes_at requires a SET segment")
        values = list(segment.amplitudes)
        coordinate = self.sweep_coordinate(point_index)
        for axis_index, sweep in enumerate(self.sweeps):
            if not isinstance(sweep, AmplitudeSweep):
                continue
            if segment.name == sweep.segment_name:
                source_index = self.output_names.index(sweep.output_name)
                if values[source_index] is None:
                    raise ValueError(
                        f"cross-capacitance source {sweep.output_name!r} has no "
                        f"nominal value in SET {segment.name!r}"
                    )
                values[source_index] = coordinate[axis_index]
        return tuple(values)

    def _set_amplitudes_at(
        self, point_index: int, segment_index: int
    ) -> Tuple[Optional[float], ...]:
        requested_values = self._virtual_set_amplitudes_at(point_index, segment_index)
        if np.allclose(
            self.cross_capacitance,
            np.eye(self.n_outputs),
            rtol=0.0,
            atol=1.0e-12,
        ):
            return requested_values
        virtual_values = self._effective_virtual_set_amplitudes_at(
            point_index, segment_index
        )
        physical_values = self.cross_capacitance @ np.asarray(
            virtual_values, dtype=float
        )
        return tuple(
            _require_amplitude(
                float(value),
                f"physical amplitude[{self.output_names[index]}]",
            )
            for index, value in enumerate(physical_values)
        )

    def _effective_physical_set_amplitudes_at(
        self,
        point_index: int,
        segment_index: int,
    ) -> Tuple[float, ...]:
        """Resolve held virtual levels and apply cross-capacitance."""
        virtual_values = self._effective_virtual_set_amplitudes_at(
            point_index,
            segment_index,
        )
        physical_values = self.cross_capacitance @ np.asarray(
            virtual_values,
            dtype=float,
        )
        return tuple(
            _require_amplitude(
                float(value),
                f"physical amplitude[{self.output_names[index]}]",
            )
            for index, value in enumerate(physical_values)
        )


    def _effective_virtual_set_amplitudes_at(
        self, point_index: int, segment_index: int
    ) -> Tuple[float, ...]:
        """Resolve held virtual outputs before applying cross-capacitance."""
        values = list(self._virtual_set_amplitudes_at(point_index, segment_index))
        if not any(value is None for value in values):
            return tuple(float(value) for value in values)
        previous_index = next(
            (
                index
                for index in range(segment_index - 1, -1, -1)
                if self.segments[index].kind == "set"
            ),
            None,
        )
        if previous_index is None:
            raise ValueError("the first SET must define every virtual output")
        previous = self._effective_virtual_set_amplitudes_at(
            point_index, previous_index
        )
        return tuple(
            previous[index] if value is None else float(value)
            for index, value in enumerate(values)
        )

    def virtual_amplitudes_at(
        self, point_index: int, segment_index: int
    ) -> Tuple[Optional[float], ...]:
        """Return pre-compensation virtual amplitudes for one segment."""
        point_index = _require_int(point_index, "point_index", 0)
        segment_index = _require_int(segment_index, "segment_index", 0)
        if point_index >= self.sweep_point_count:
            raise IndexError("point_index is out of range")
        if segment_index >= len(self.segments):
            raise IndexError("segment_index is out of range")
        segment = self.segments[segment_index]
        if segment.kind == "ramp":
            if segment_index + 1 >= len(self.segments):
                raise ValueError(f"RAMP {segment.name!r} has no following SET")
            return self._effective_virtual_set_amplitudes_at(
                point_index, segment_index + 1
            )
        return self._effective_virtual_set_amplitudes_at(point_index, segment_index)

    def amplitudes_at(self, point_index: int, segment_index: int) -> Tuple[Optional[float], ...]:
        point_index = _require_int(point_index, "point_index", 0)
        segment_index = _require_int(segment_index, "segment_index", 0)
        if point_index >= self.sweep_point_count:
            raise IndexError("point_index is out of range")
        if segment_index >= len(self.segments):
            raise IndexError("segment_index is out of range")
        segment = self.segments[segment_index]
        if segment.kind == "ramp":
            if segment_index + 1 >= len(self.segments):
                raise ValueError(f"RAMP {segment.name!r} has no following SET")
            next_segment = self.segments[segment_index + 1]
            if next_segment.kind != "set":
                raise ValueError(
                    f"RAMP {segment.name!r} must be immediately followed by a SET"
                )
            return self._set_amplitudes_at(point_index, segment_index + 1)
        return self._set_amplitudes_at(point_index, segment_index)

    def waveform_vertices(
        self,
        point_index: int = 0,
        *,
        space: str = "physical",
    ):
        """Return the minimum ordered vertices needed to reconstruct a pulse.

        Adjacent vertices are joined by straight lines. Equal adjacent times
        with different values represent an instantaneous SET transition.
        RAMP interiors are intentionally omitted because their two endpoints
        fully define the linear segment.
        """
        self._validate()
        if space == "physical":
            amplitude_getter = self.amplitudes_at
        elif space == "virtual":
            amplitude_getter = self.virtual_amplitudes_at
        else:
            raise ValueError("space must be 'physical' or 'virtual'")

        current = np.asarray(amplitude_getter(point_index, 0), dtype=float)
        times = []
        vertices = []
        boundaries = []

        def append_vertex(time_value: float) -> None:
            if (
                times
                and time_value == times[-1]
                and np.array_equal(current, vertices[-1])
            ):
                return
            times.append(float(time_value))
            vertices.append(current.copy())

        time_now = 0.0
        append_vertex(time_now)
        for segment_index, segment in enumerate(self.segments):
            start_time = time_now
            targets = amplitude_getter(point_index, segment_index)
            if segment.kind == "set":
                if segment_index != 0:
                    for output_index, target in enumerate(targets):
                        if target is not None:
                            current[output_index] = float(target)
                    append_vertex(time_now)
                time_now += self.segment_duration_cycles_at(
                    point_index,
                    segment_index,
                )
                append_vertex(time_now)
            else:
                for output_index, target in enumerate(targets):
                    if target is not None:
                        current[output_index] = float(target)
                time_now += self.segment_duration_cycles_at(
                    point_index,
                    segment_index,
                )
                append_vertex(time_now)
            boundaries.append((segment.name, start_time, time_now))

        vertex_matrix = np.asarray(vertices, dtype=float).T
        return (
            np.asarray(times, dtype=float),
            {
                name: vertex_matrix[index]
                for index, name in enumerate(self.output_names)
            },
            tuple(boundaries),
        )

    def bias_t_compensation_preview(
        self,
        point_index: int = 0,
    ) -> Tuple[BiasTCompensationPreview, ...]:
        """Calculate ideal physical-output compensation pulses for one point.

        SET intervals contribute ``level * duration`` and RAMP intervals use
        the exact trapezoid area ``(start + target) * duration / 2``. The
        In fixed-voltage mode, duration is rounded to the nearest whole AWG
        fabric cycle. In fixed-time mode, voltage is rounded to the nearest
        legal 14-effective-bit DAC code for the selected duration.
        """
        self._validate()
        config = self.bias_t_compensation
        if config is None:
            return ()

        current = np.asarray(self.amplitudes_at(point_index, 0), dtype=float)
        areas = np.zeros(self.n_outputs, dtype=float)
        for segment_index, segment in enumerate(self.segments):
            targets = self.amplitudes_at(point_index, segment_index)
            duration = self.segment_duration_cycles_at(
                point_index,
                segment_index,
            )
            if segment.kind == "set":
                for output_index, target in enumerate(targets):
                    if target is not None:
                        current[output_index] = float(target)
                areas += current * duration
            else:
                next_values = current.copy()
                for output_index, target in enumerate(targets):
                    if target is not None:
                        next_values[output_index] = float(target)
                areas += (
                    (current + next_values)
                    * duration
                    / 2.0
                )
                current = next_values

        previews = []
        for output_index, area in enumerate(areas):
            if np.isclose(area, 0.0, rtol=0.0, atol=1.0e-15):
                target = 0.0
                duration = 0
            elif config.mode == "fixed_time":
                duration = int(config.fixed_duration_cycles)
                ideal_target = -float(area) / duration
                if abs(ideal_target) > 1.0:
                    raise ValueError(
                        "Bias-T fixed compensation time is too short for "
                        f"{self.output_names[output_index]}; required voltage "
                        f"is {ideal_target:+.6g} full scale"
                    )
                target_code = normalized_to_dac(ideal_target)
                target = dac_to_normalized(target_code)
                if target_code == 0:
                    duration = 0
            else:
                target = -config.amplitude if area > 0.0 else config.amplitude
                duration = max(1, int(np.floor(abs(area) / config.amplitude + 0.5)))
            previews.append(BiasTCompensationPreview(
                output_index=output_index,
                output_name=self.output_names[output_index],
                pulse_area=float(area),
                target_amplitude=float(target),
                duration_cycles=duration,
                residual_area=float(area + target * duration),
            ))
        return tuple(previews)


    def compensated_waveform_vertices(self, point_index: int = 0):
        """Return physical pulse vertices with simultaneous Bias-T starts.

        Physical outputs first return to zero at the end of the user pulse.
        Every active output then receives its opposite-polarity SET at one
        common start time. Each output independently returns to zero after its
        own compensation duration.
        """
        times, waveforms, boundaries = self.waveform_vertices(
            point_index,
            space="physical",
        )
        previews = self.bias_t_compensation_preview(point_index)
        if not previews:
            return times, waveforms, boundaries

        time_values = list(np.asarray(times, dtype=float))
        value_matrix = np.vstack(
            [np.asarray(waveforms[name], dtype=float) for name in self.output_names]
        )
        columns = [value_matrix[:, index].copy() for index in range(value_matrix.shape[1])]
        current = columns[-1].copy()
        boundary_values = list(boundaries)
        time_now = float(time_values[-1])

        def append_vertex(time_value: float, *, force: bool = False) -> None:
            if (
                not force
                and time_values
                and time_value == time_values[-1]
                and np.array_equal(current, columns[-1])
            ):
                return
            time_values.append(float(time_value))
            columns.append(current.copy())

        current[:] = 0.0
        append_vertex(time_now)
        active = [preview for preview in previews if preview.duration_cycles > 0]
        gap = int(self.bias_t_compensation.inter_output_gap_cycles)
        lead = BIAS_T_INSTRUCTION_LEAD_PER_OUTPUT * self.n_outputs
        if active and (gap or lead):
            time_now += gap + lead
            append_vertex(time_now)

        start_time = time_now
        for preview in active:
            current[preview.output_index] = preview.target_amplitude
        if active:
            append_vertex(start_time, force=True)

        for duration in sorted({preview.duration_cycles for preview in active}):
            time_now = start_time + duration
            append_vertex(time_now)
            for preview in active:
                if preview.duration_cycles == duration:
                    current[preview.output_index] = 0.0
            append_vertex(time_now, force=True)

        for preview in active:
            boundary_values.append((
                f"bias_t_comp_{preview.output_name}",
                start_time,
                start_time + preview.duration_cycles,
            ))

        matrix = np.asarray(columns, dtype=float).T
        return (
            np.asarray(time_values, dtype=float),
            {
                name: matrix[index]
                for index, name in enumerate(self.output_names)
            },
            tuple(boundary_values),
        )

    def sample_waveforms(
        self,
        point_index: int = 0,
        points_per_ramp: int = 64,
        *,
        space: str = "physical",
    ):
        """Return an ideal preview in physical or virtual voltage space."""
        self._validate()
        points_per_ramp = _require_int(points_per_ramp, "points_per_ramp", 2)
        if space == "physical":
            amplitude_getter = self.amplitudes_at
        elif space == "virtual":
            amplitude_getter = self.virtual_amplitudes_at
        else:
            raise ValueError("space must be 'physical' or 'virtual'")
        current = list(amplitude_getter(point_index, 0))
        times = [0.0]
        values = {name: [float(current[index])] for index, name in enumerate(self.output_names)}
        boundaries = []
        time_now = 0.0

        for segment_index, segment in enumerate(self.segments):
            targets = amplitude_getter(point_index, segment_index)
            start_time = time_now
            duration = self.segment_duration_cycles_at(
                point_index,
                segment_index,
            )
            if segment.kind == "set":
                if segment_index != 0:
                    times.append(time_now)
                    for index, name in enumerate(self.output_names):
                        values[name].append(float(current[index]))
                    for index, target in enumerate(targets):
                        if target is not None:
                            current[index] = target
                    times.append(time_now)
                    for index, name in enumerate(self.output_names):
                        values[name].append(float(current[index]))
                time_now += duration
                times.append(time_now)
                for index, name in enumerate(self.output_names):
                    values[name].append(float(current[index]))
            else:
                starts = list(current)
                for sample_index in range(1, points_per_ramp + 1):
                    fraction = sample_index / points_per_ramp
                    times.append(time_now + duration * fraction)
                    for index, name in enumerate(self.output_names):
                        target = targets[index]
                        if target is None:
                            value = starts[index]
                        else:
                            value = starts[index] + (target - starts[index]) * fraction
                        values[name].append(float(value))
                for index, target in enumerate(targets):
                    if target is not None:
                        current[index] = target
                time_now += duration
            boundaries.append((segment.name, start_time, time_now))

        return (
            np.asarray(times, dtype=float),
            {name: np.asarray(samples, dtype=float) for name, samples in values.items()},
            tuple(boundaries),
        )

    def plot_preview(self, point_indices: Optional[Iterable[int]] = None, *, show=True):
        """Plot ideal normalized waveforms for selected sweep points."""
        try:
            import matplotlib.pyplot as plt
        except ImportError as exc:
            raise RuntimeError("matplotlib is required for plot_preview()") from exc

        if point_indices is None:
            count = self.sweep_point_count
            point_indices = sorted(set((0, count // 2, count - 1)))
        point_indices = tuple(int(index) for index in point_indices)
        fig, axes = plt.subplots(self.n_outputs, 1, sharex=True, squeeze=False)
        for point_index in point_indices:
            if self.bias_t_compensation is None:
                times, waveforms, boundaries = self.sample_waveforms(point_index)
            else:
                times, waveforms, boundaries = self.compensated_waveform_vertices(
                    point_index
                )
            coordinate = self.sweep_coordinate(point_index)
            if not self.sweeps:
                label = "fixed"
            else:
                label = ", ".join(
                    f"{sweep.output_name}/{sweep.segment_name}={coordinate[index]:.4f}"
                    for index, sweep in enumerate(self.sweeps)
                )
            for output_index, output_name in enumerate(self.output_names):
                axes[output_index, 0].plot(times, waveforms[output_name], label=label)
        for output_index, output_name in enumerate(self.output_names):
            axis = axes[output_index, 0]
            axis.set_ylabel(output_name)
            axis.set_ylim(-1.05, 1.05)
            axis.grid(True, alpha=0.3)
            axis.legend(loc="best")
            for _, start, _ in boundaries:
                axis.axvline(start, color="0.75", linewidth=0.7, linestyle="--")
        axes[-1, 0].set_xlabel("AWG fabric cycles (ideal sequence time)")
        fig.tight_layout()
        if show:
            plt.show()
        return fig, axes[:, 0]

    def make_program(
        self,
        soccfg,
        awg_channels: Union[Sequence[int], Mapping[str, int]],
        *,
        tproc_mhz: Optional[Real] = None,
        repetitions_per_sweep: int = 1,
        reps: Optional[int] = None,
        readout: Optional[ReadoutConfig] = None,
        rf_pulse: Optional[RfPulseConfig] = None,
        rf_pulses: Optional[Sequence[RfPulseConfig]] = None,
        ddr_readout: Optional[DdrFirReadoutConfig] = None,
        command_lead_tproc_cycles: int = 128,
        command_spacing_tproc_cycles: int = 1,
        recovery_tproc_cycles: int = 20,
        compile_validation_mode: str = DEFAULT_COMPILE_VALIDATION_MODE,
        cancel_check: Optional[Callable[[], None]] = None,
    ):
        return FineTuneAmplitudeSweepProgram(
            soccfg,
            self,
            awg_channels,
            tproc_mhz=tproc_mhz,
            repetitions_per_sweep=repetitions_per_sweep,
            reps=reps,
            readout=readout,
            rf_pulse=rf_pulse,
            rf_pulses=rf_pulses,
            ddr_readout=ddr_readout,
            command_lead_tproc_cycles=command_lead_tproc_cycles,
            command_spacing_tproc_cycles=command_spacing_tproc_cycles,
            recovery_tproc_cycles=recovery_tproc_cycles,
            compile_validation_mode=compile_validation_mode,
            cancel_check=cancel_check,
        )


def _resolve_awg_channels(sequence: FineTuneSequence, awg_channels) -> Tuple[int, ...]:
    if isinstance(awg_channels, Mapping):
        missing = set(sequence.output_names) - set(awg_channels)
        extra = set(awg_channels) - set(sequence.output_names)
        if missing or extra:
            raise ValueError(
                f"AWG channel map mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
            )
        channels = tuple(int(awg_channels[name]) for name in sequence.output_names)
    else:
        channels = tuple(int(ch) for ch in awg_channels)
        if len(channels) != sequence.n_outputs:
            raise ValueError(
                f"expected {sequence.n_outputs} AWG channels, received {len(channels)}"
            )
    if len(set(channels)) != len(channels):
        raise ValueError("AWG channels must be unique")
    if any(ch < 0 for ch in channels):
        raise ValueError("AWG channel indices must be nonnegative")
    return channels


def _validate_gen_config(gen_ch: int, gen_cfg: Mapping) -> None:
    if gen_cfg.get("type") != "axis_awg_tuning_v1" and gen_cfg.get("gen_type") != "awg_tuning":
        raise ValueError(f"generator channel {gen_ch} is not axis_awg_tuning_v1")
    required = ("tproc_ch", "f_fabric", "n_pts", "frac")
    missing = [name for name in required if name not in gen_cfg]
    if missing:
        raise KeyError(f"generator channel {gen_ch} is missing config fields {missing}")


def _pack_command_words(gen_cfg: Mapping, target: int, duration: int, step: int, opcode: int):
    if target < -(1 << 31) or target > (1 << 31) - 1:
        raise ValueError("target does not fit signed 32 bits")
    if duration < 0 or duration > (1 << 23) - 1:
        raise ValueError("RAMP duration does not fit unsigned 23 bits")
    if step < -(1 << 23) or step > (1 << 23) - 1:
        raise ValueError("RAMP step does not fit signed 24 bits")
    control = (int(opcode) & 0x3) << 16
    tmux_ch = gen_cfg.get("tmux_ch")
    if tmux_ch is not None:
        control |= (int(tmux_ch) & 0xFF) << 24
    return (
        target & 0xFFFFFFFF,
        0,
        duration & 0x7FFFFF,
        step & 0xFFFFFF,
        control & 0xFFFFFFFF,
    )


def _target_code(gen_cfg: Mapping, amplitude: Real) -> int:
    return normalized_to_dac(
        amplitude,
        min_code=int(gen_cfg.get("minv", -32768)),
        max_code=int(gen_cfg.get("maxv", 32764)),
        invalid_lsb=int(gen_cfg.get("dac_invalid_lsb", 2)),
    )


def _ramp_step(
    gen_cfg: Mapping,
    start_code: int,
    target_code: int,
    duration_cycles: int,
    segment_name: str,
) -> Tuple[int, int]:
    duration_samples = int(duration_cycles) * int(gen_cfg["n_pts"])
    if duration_samples > (1 << 23) - 1:
        raise ValueError(
            f"RAMP {segment_name!r} duration expands to {duration_samples} "
            "scalar samples, exceeding the 23-bit command field"
        )
    denominator = max(1, duration_samples - 1)
    numerator = (int(target_code) - int(start_code)) << int(gen_cfg["frac"])
    step = _div_trunc_zero(numerator, denominator)
    if step < -(1 << 23) or step > (1 << 23) - 1:
        raise ValueError(
            f"RAMP {segment_name!r} step {step} exceeds signed 24 bits; "
            "increase duration_cycles or reduce the amplitude span"
        )
    return duration_samples, step




def compile_sequence(
    sequence: FineTuneSequence,
    soccfg,
    awg_channels: Union[Sequence[int], Mapping[str, int]],
    *,
    point_indices: Optional[Iterable[int]] = None,
    cancel_check: Optional[Callable[[], None]] = None,
) -> Tuple[Tuple[int, ...], Tuple[CompiledPoint, ...]]:
    """Compile selected sweep points into exact five-word AWG commands."""
    sequence._validate()
    channels = _resolve_awg_channels(sequence, awg_channels)
    gens = soccfg["gens"]
    gen_cfgs = []
    for gen_ch in channels:
        if gen_ch >= len(gens):
            raise IndexError(f"generator channel {gen_ch} is out of range")
        gen_cfg = gens[gen_ch]
        _validate_gen_config(gen_ch, gen_cfg)
        if sequence.rc_compensation is not None and not gen_cfg.get("rc_precomp_version", 0):
            raise ValueError(f"generator {gen_ch} firmware does not support FPGA RC compensation")
        gen_cfgs.append(gen_cfg)

    if point_indices is None:
        point_indices = range(sequence.sweep_point_count)
    compiled_points = []
    for point_index in point_indices:
        if cancel_check is not None:
            cancel_check()
        point_index = _require_int(point_index, "point_index", 0)
        if point_index >= sequence.sweep_point_count:
            raise IndexError("point_index is out of range")
        sweep_coordinate = sequence.sweep_coordinate(point_index)
        current_codes = [None] * sequence.n_outputs
        compiled_segments = []
        for segment_index, segment in enumerate(sequence.segments):
            amplitudes = sequence.amplitudes_at(point_index, segment_index)
            commands = []
            for output_index, amplitude in enumerate(amplitudes):
                if amplitude is None:
                    continue
                gen_cfg = gen_cfgs[output_index]
                target = _target_code(gen_cfg, amplitude)
                if segment.kind == "set":
                    duration_samples = 0
                    step = 0
                    opcode = OP_SET
                else:
                    if current_codes[output_index] is None:
                        raise ValueError(
                            f"RAMP {segment.name!r} has no known start value for "
                            f"output {sequence.output_names[output_index]!r}"
                        )
                    duration_samples, step = _ramp_step(
                        gen_cfg,
                        int(current_codes[output_index]),
                        target,
                        sequence.segment_duration_cycles_at(
                            point_index,
                            segment_index,
                        ),
                        segment.name,
                    )
                    opcode = OP_RAMP
                words = _pack_command_words(gen_cfg, target, duration_samples, step, opcode)
                commands.append(
                    CompiledCommand(
                        point_index=point_index,
                        segment_index=segment_index,
                        segment_name=segment.name,
                        output_index=output_index,
                        output_name=sequence.output_names[output_index],
                        gen_ch=channels[output_index],
                        kind=segment.kind,
                        target_code=target,
                        duration_samples=duration_samples,
                        step=step,
                        words=words,
                    )
                )
                current_codes[output_index] = target
            compiled_segments.append(tuple(commands))
        if len(sweep_coordinate) == 1:
            sweep_value = sweep_coordinate[0]
        elif sweep_coordinate:
            sweep_value = sweep_coordinate
        else:
            sweep_value = 0.0
        compiled_points.append(CompiledPoint(sweep_value, tuple(compiled_segments)))
    return channels, tuple(compiled_points)


class FineTuneAmplitudeSweepProgram(SquarePulseProgramMixin, OutputTriggerProgramMixin, RAveragerProgram):
    """ASM v1 program generated from :class:`FineTuneSequence`.

    Sweep points and repetitions are both hardware loops.  Variable SET
    targets and dependent RAMP target/step fields live in tProcessor
    registers.  Nested Cartesian loops advance and reset those fields with
    register adds; no per-point command or delta table is stored.
    Commands sharing one tProcessor AXIS port are separated by the configured
    number of tProcessor cycles, which supports TMUX fanout to as many as
    eight AWG tuning outputs without same-port/same-cycle collisions.
    """

    def __init__(
        self,
        soccfg,
        sequence: FineTuneSequence,
        awg_channels,
        *,
        tproc_mhz: Optional[Real] = None,
        repetitions_per_sweep: int = 1,
        reps: Optional[int] = None,
        readout: Optional[ReadoutConfig] = None,
        rf_pulse: Optional[RfPulseConfig] = None,
        rf_pulses: Optional[Sequence[RfPulseConfig]] = None,
        ddr_readout: Optional[DdrFirReadoutConfig] = None,
        command_lead_tproc_cycles: int = 128,
        command_spacing_tproc_cycles: int = 1,
        recovery_tproc_cycles: int = 20,
        compile_validation_mode: str = DEFAULT_COMPILE_VALIDATION_MODE,
        cancel_check: Optional[Callable[[], None]] = None,
    ):
        self.cancel_check = cancel_check
        self._check_cancel()
        sequence._validate()
        self.sequence = sequence
        self.awg_channel_spec = awg_channels
        self.hwh_tproc_mhz = _require_positive_real(
            soccfg["tprocs"][0]["f_time"], "HWH tProcessor clock"
        )
        self.tproc_mhz = (
            self.hwh_tproc_mhz
            if tproc_mhz is None
            else _require_positive_real(tproc_mhz, "tproc_mhz")
        )
        self.tproc_clock_is_manual = tproc_mhz is not None
        self.readout_config = readout
        if rf_pulse is not None and rf_pulses is not None:
            raise ValueError("use either rf_pulse or rf_pulses, not both")
        self.rf_pulse_configs = tuple(
            rf_pulses
            if rf_pulses is not None
            else (() if rf_pulse is None else (rf_pulse,))
        )
        if any(not isinstance(item, RfPulseConfig) for item in self.rf_pulse_configs):
            raise TypeError("every RF pulse entry must be an RfPulseConfig")
        event_ids = tuple(item.event_id for item in self.rf_pulse_configs)
        if len(set(event_ids)) != len(event_ids):
            raise ValueError("each RF pulse event_id must be unique")
        # Retain the singular attribute for older callers which inspect it.
        self.rf_pulse_config = (
            self.rf_pulse_configs[0] if len(self.rf_pulse_configs) == 1 else None
        )
        self.ddr_readout_config = ddr_readout
        self.compile_validation_mode = normalize_compile_validation_mode(
            compile_validation_mode
        )
        if readout is not None and ddr_readout is not None:
            raise ValueError("readout and ddr_readout cannot be enabled together")
        self.command_lead_tproc_cycles = _require_int(
            command_lead_tproc_cycles, "command_lead_tproc_cycles", 0
        )
        self.command_spacing_tproc_cycles = _require_int(
            command_spacing_tproc_cycles, "command_spacing_tproc_cycles", 1
        )
        self.recovery_tproc_cycles = _require_int(
            recovery_tproc_cycles, "recovery_tproc_cycles", 0
        )
        repetitions_per_sweep = _require_int(
            repetitions_per_sweep, "repetitions_per_sweep", 1
        )
        if reps is not None:
            reps = _require_int(reps, "reps", 1)
            if repetitions_per_sweep != 1 and repetitions_per_sweep != reps:
                raise ValueError("reps and repetitions_per_sweep disagree")
            repetitions_per_sweep = reps
        if len(sequence.sweep_axes) <= 1:
            axis_points = (
                np.array([0.0], dtype=float)
                if not sequence.sweep_axes
                else sequence.sweep_axes[0].points
            )
            cfg_start = float(axis_points[0])
            nominal_step = (
                0.0
                if len(axis_points) < 2
                else float(axis_points[1] - axis_points[0])
            )
        else:
            # RAveragerProgram requires scalar start/step metadata.  Cartesian
            # coordinates are returned by get_expt_pts() instead.
            cfg_start = 0.0
            nominal_step = 1.0
        cfg = {
            "reps": repetitions_per_sweep,
            "expts": sequence.sweep_point_count,
            "start": cfg_start,
            "step": nominal_step,
        }
        super().__init__(soccfg, cfg)

    def _check_cancel(self) -> None:
        if self.cancel_check is not None:
            self.cancel_check()

    def get_expt_pts(self):
        return self.sequence.sweep_points.copy()

    def _boundary_validation_indices(self) -> Tuple[int, ...]:
        """Return corners plus rows required by duration-conditioned tables."""
        axes = self.sequence.sweep_axes
        if not axes:
            return (0,)
        shape = tuple(int(axis.count) for axis in axes)
        selected = {
            int(np.ravel_multi_index(indices, shape, order="C"))
            for indices in product(
                *((0,) if count <= 1 else (0, count - 1) for count in shape)
            )
        }
        duration_axes = self._bias_t_conditioning_axis_indices(axes)
        if duration_axes:
            duration_shape = tuple(shape[index] for index in duration_axes)
            non_duration_axes = tuple(
                index for index in range(len(axes))
                if index not in duration_axes and shape[index] > 1
            )
            for duration_indices in np.ndindex(duration_shape):
                base = [0] * len(axes)
                for axis_index, value in zip(
                    duration_axes,
                    duration_indices,
                ):
                    base[axis_index] = int(value)
                selected.add(
                    int(np.ravel_multi_index(tuple(base), shape, order="C"))
                )
                for axis_index in non_duration_axes:
                    endpoint = list(base)
                    endpoint[axis_index] = shape[axis_index] - 1
                    selected.add(
                        int(
                            np.ravel_multi_index(
                                tuple(endpoint),
                                shape,
                                order="C",
                            )
                        )
                    )
        return tuple(sorted(selected))

    def _compile_boundary_points(self) -> None:
        indices = self._boundary_validation_indices()
        self.awg_channels, points = compile_sequence(
            self.sequence,
            self.soccfg,
            self.awg_channel_spec,
            point_indices=indices,
            cancel_check=self.cancel_check,
        )
        self._compiled_point_by_index = dict(zip(indices, points))
        self._compile_validation_point_indices = indices
        self.compiled_points = points

    def initialize(self):
        self._check_cancel()
        # QICK's pulse/readout helpers use self.tproccfg for timestamp math.
        # Keep the hardware description intact and override only this program's
        # local timing view when the caller supplied a manual clock.
        self.tproccfg = dict(self.tproccfg)
        self.tproccfg["f_time"] = self.tproc_mhz
        if self.compile_validation_mode == COMPILE_VALIDATION_FULL:
            self.awg_channels, self.compiled_points = compile_sequence(
                self.sequence,
                self.soccfg,
                self.awg_channel_spec,
                cancel_check=self.cancel_check,
            )
            self._compiled_point_by_index = None
            self._compile_validation_point_indices = range(
                len(self.compiled_points)
            )
        else:
            self._compile_boundary_points()
        self._check_cancel()
        self._validate_bias_t_tproc_ports()
        self.bias_t_simultaneous_start_lead_cycles = (
            BIAS_T_INSTRUCTION_LEAD_PER_OUTPUT * len(self.awg_channels)
            if isinstance(
                self.sequence.bias_t_compensation,
                BiasTCompensationConfig,
            )
            else 0
        )
        self._channel_slots = self._build_channel_slots()
        self.aux_timing = {}
        self._rf_runtime = {}
        self._declared_rf_channels = set()
        self._configure_square_pulse()
        self._configure_output_trigger()
        self._validate_rf_sweeps()
        for rf_index, rf_config in enumerate(self.rf_pulse_configs):
            self._configure_rf_pulse(rf_index, rf_config)
        if self.ddr_readout_config is not None:
            self._configure_ddr_readout()
        self.timing = self._build_timing()
        latencies = {
            self._fabric_to_tproc(ch, int(self.soccfg["gens"][ch].get("output_latency_cycles", 0)))
            if self.soccfg["gens"][ch].get("output_latency_cycles", 0) else 0
            for ch in self.awg_channels
        }
        if len(latencies) != 1:
            raise ValueError("Selected AWG outputs must have matching output pipeline latency")
        self.awg_output_latency_tproc = latencies.pop()
        # Segment anchors describe the physical DAC output. Core occupancy and
        # command timestamps are unchanged, including DC compensation widths.
        for key in ("segment_starts", "segment_ends"):
            self.timing[key] = tuple(v + self.awg_output_latency_tproc for v in self.timing[key])
        self.timing["point_end"] += self.awg_output_latency_tproc
        if self.rf_pulse_configs or self.ddr_readout_config is not None:
            self._build_aux_timing()
        self._build_sweep_register_plan()
        from qick_rc_validation import validate_program_rc_range
        self.rc_output_range_validation = validate_program_rc_range(self)
        self._check_cancel()

        if self.readout_config is not None:
            ro = self.readout_config
            self.declare_readout(ch=ro.ro_ch, length=ro.length)
            freq_word = int(ro.freq)
            if ro.freq_mhz is not None:
                ro_cfg = self.soccfg["readouts"][ro.ro_ch]
                gen_ch = (
                    self.rf_pulse_configs[0].gen_ch
                    if self.rf_pulse_configs
                    else None
                )
                try:
                    freq_word = int(
                        self.freq2reg_adc(
                            float(ro.freq_mhz),
                            ro_ch=ro.ro_ch,
                            gen_ch=gen_ch,
                        )
                    )
                except KeyError as exc:
                    if exc.args != ("refclk_freq",):
                        raise
                    b_dds = int(ro_cfg["b_dds"])
                    freq_word = int(
                        round(
                            float(ro.freq_mhz)
                            * (1 << b_dds)
                            / float(ro_cfg["f_dds"])
                        )
                    ) % (1 << b_dds)
            self.set_readout_registers(
                ch=ro.ro_ch,
                freq=freq_word,
                length=ro.length,
                phrst=0,
            )

    def _initialize_rc_compensation(self):
        rc = self.sequence.rc_compensation
        for gen_ch in self.awg_channels:
            gen = self.soccfg["gens"][gen_ch]
            if not gen.get("rc_precomp_version", 0):
                continue
            from qick.precompensation import rc_coefficient
            scalar_mhz = float(gen["f_fabric"]) * int(gen.get("samps_per_clk", 16))
            self.set_pulse_registers(ch=gen_ch, style="awg_rc",
                coefficient=rc_coefficient(rc.tau_us, scalar_mhz) if rc else 0,
                enable=rc is not None, reset=True)
            self.pulse(ch=gen_ch, t=4 * int(self._channel_slots[gen_ch]))
        # Advance the time origin past configuration before any waveform.
        self.synci(100)

    def _emit_rc_repeat_reset(self):
        """Clear AWG IIR history after every completed shot at nominal zero."""
        rc = self.sequence.rc_compensation
        if rc is None:
            return
        from qick.precompensation import rc_coefficient

        # Reserve instruction lookahead after the last SET-zero/DC stop.
        # Only command registers are changed; hardware sweep state is retained.
        lead = 32 * len(self.awg_channels)
        self.synci(lead, "lookahead for per-repeat AWG RC reset")
        last_command = 0
        for gen_ch in self.awg_channels:
            gen = self.soccfg["gens"][gen_ch]
            scalar_mhz = float(gen["f_fabric"]) * int(gen.get("samps_per_clk", 16))
            self.set_pulse_registers(
                ch=gen_ch, style="awg_rc",
                coefficient=rc_coefficient(rc.tau_us, scalar_mhz),
                enable=True, reset=True,
            )
            timestamp = int(self._channel_slots[gen_ch])
            self.pulse(ch=gen_ch, t=timestamp)
            last_command = max(last_command, timestamp)
        # Cover command transport and the matched RC output pipeline before
        # the recovery interval/end marker/next waveform can begin.
        flush = last_command + max(
            self._fabric_to_tproc(
                ch, int(self.soccfg["gens"][ch].get("output_latency_cycles", 11)) + 4,
            )
            for ch in self.awg_channels
        )
        self.synci(flush, "flush per-repeat AWG RC reset")
        self.reset_timestamps()

    @staticmethod
    def _command_key(command: CompiledCommand) -> Tuple[int, int, int]:
        return (
            command.segment_index,
            command.output_index,
            command.command_slot,
        )

    @staticmethod
    def _timing_key(command: CompiledCommand):
        """Keep legacy two-item keys for the primary command slot."""
        if command.command_slot == 0:
            return command.segment_index, command.output_index
        return (
            command.segment_index,
            command.output_index,
            command.command_slot,
        )

    def _validate_bias_t_tproc_ports(self):
        """Require independent tProcessor outputs for exact simultaneous SETs."""
        if not isinstance(
            self.sequence.bias_t_compensation,
            BiasTCompensationConfig,
        ):
            return
        channels_by_port = {}
        for output_name, gen_ch in zip(self.sequence.output_names, self.awg_channels):
            port = int(self.soccfg["gens"][gen_ch]["tproc_ch"])
            channels_by_port.setdefault(port, []).append((output_name, gen_ch))
        conflicts = {
            port: channels
            for port, channels in channels_by_port.items()
            if len(channels) > 1
        }
        if conflicts:
            details = "; ".join(
                f"tproc_ch {port}: "
                + ", ".join(f"{name} (gen {gen_ch})" for name, gen_ch in channels)
                for port, channels in sorted(conflicts.items())
            )
            raise ValueError(
                "simultaneous Bias-T compensation requires one independent "
                f"tProcessor output per AWG; shared TMUX ports found: {details}"
            )

    def _compiled_point_area2(
        self,
        point_index: int,
        point: CompiledPoint,
    ) -> Tuple[int, ...]:
        """Return twice the ideal pulse area in DAC-code fabric cycles."""
        current = [None] * self.sequence.n_outputs
        area2 = [0] * self.sequence.n_outputs
        for segment_index, (segment, commands) in enumerate(zip(
            self.sequence.segments,
            point.segment_commands,
        )):
            targets = {command.output_index: command.target_code for command in commands}
            duration = self.sequence.segment_duration_cycles_at(
                point_index,
                segment_index,
            )
            if segment.kind == "set":
                for output_index, target in targets.items():
                    current[output_index] = int(target)
                if any(value is None for value in current):
                    raise RuntimeError("the first compiled SET must initialize every output")
                for output_index, value in enumerate(current):
                    area2[output_index] += 2 * int(value) * duration
            else:
                for output_index, start in enumerate(current):
                    if start is None:
                        raise RuntimeError("compiled RAMP has no known start value")
                    target = int(targets.get(output_index, start))
                    area2[output_index] += (int(start) + target) * duration
                    current[output_index] = target
        return tuple(area2)

    @staticmethod
    def _ramp_duration_axis_indices(sweep_axes) -> Tuple[int, ...]:
        matches = tuple(
            index
            for index, axis in enumerate(sweep_axes)
            if isinstance(axis, RampDurationSweep)
        )
        if matches != tuple(range(len(matches))):
            raise RuntimeError(
                "RAMP duration sweeps must be the outermost sweep axes"
            )
        segments = [sweep_axes[index].segment_name for index in matches]
        if len(set(segments)) != len(segments):
            raise RuntimeError(
                "each RAMP segment may have only one duration sweep axis"
            )
        return matches

    @staticmethod
    def _duration_axis_indices(sweep_axes) -> Tuple[int, ...]:
        """Return all RAMP and SET-hold duration axes in outer-axis order."""
        matches = tuple(
            index
            for index, axis in enumerate(sweep_axes)
            if isinstance(axis, (RampDurationSweep, HoldDurationSweep))
        )
        if matches != tuple(range(len(matches))):
            raise RuntimeError(
                "RAMP and SET hold duration sweeps must be the outermost "
                "sweep axes"
            )
        return matches

    def _bias_t_conditioning_axis_indices(self, sweep_axes) -> Tuple[int, ...]:
        """Factor voltage * RF-extension area without a Cartesian point table.

        Condition on the earlier axis of every voltage/extension pair. The
        later axis remains a register add with the correct row-dependent
        coefficient. This preserves the caller's axis order and supports
        voltage-outer/RF-inner as well as RF-outer/voltage-inner loops.
        """
        selected = set(self._duration_axis_indices(sweep_axes))
        if self.sequence.bias_t_compensation is not None:
            voltage_axes = [i for i, axis in enumerate(sweep_axes)
                            if isinstance(axis, AmplitudeSweep) and axis.count > 1]
            rf_extension_axes = [i for i, axis in enumerate(sweep_axes)
                if isinstance(axis, RfDurationSweep) and axis.count > 1
                and axis.segment_length_mode == "extend_by_rf_duration"]
            selected.update(min(voltage, duration)
                            for voltage in voltage_axes for duration in rf_extension_axes)
        return tuple(sorted(selected))

    @classmethod
    def _ramp_duration_axis_by_segment(cls, sweep_axes) -> Dict[str, int]:
        return {
            str(sweep_axes[index].segment_name): int(index)
            for index in cls._ramp_duration_axis_indices(sweep_axes)
        }

    def _duration_conditioned_values(
        self,
        requested_values,
        sweep_axes,
        sweep_shape,
        *,
        duration_axis_index: int,
        quantum: int = 1,
    ):
        """Compress one nonlinear duration-dependent field into coefficients."""
        return self._duration_axes_conditioned_values(
            requested_values,
            sweep_axes,
            sweep_shape,
            duration_axis_indices=(duration_axis_index,),
            quantum=quantum,
        )

    def _duration_axes_conditioned_values(
        self,
        requested_values,
        sweep_axes,
        sweep_shape,
        *,
        duration_axis_indices,
        quantum: int = 1,
    ):
        """Compress a field over one or more duration-controlled axes.

        One row is retained per Cartesian combination of RAMP and/or SET hold
        durations. Each row contains the field base plus one constant increment
        for every non-duration axis. This avoids storing the full Cartesian
        sweep while preserving duration-axis interactions exactly.
        """
        requested = np.asarray(requested_values, dtype=np.int64).reshape(-1)
        duration_axis_indices = tuple(
            int(axis_index) for axis_index in duration_axis_indices
        )
        if not duration_axis_indices:
            raise ValueError("at least one duration axis is required")
        if len(set(duration_axis_indices)) != len(duration_axis_indices):
            raise ValueError("duration axis indices must be unique")
        for axis_index in duration_axis_indices:
            if not 0 <= axis_index < len(sweep_axes):
                raise IndexError("duration axis index is out of range")
            if not isinstance(
                sweep_axes[axis_index],
                (RampDurationSweep, HoldDurationSweep, AmplitudeSweep, RfDurationSweep),
            ):
                raise ValueError(
                    "conditioned model requires voltage or duration axes"
                )
        duration_shape = tuple(
            int(sweep_axes[axis_index].count)
            for axis_index in duration_axis_indices
        )
        bases = []
        axis_rows = {
            axis_index: []
            for axis_index, axis in enumerate(sweep_axes)
            if axis_index not in duration_axis_indices and axis.count > 1
        }
        for duration_indices in np.ndindex(duration_shape):
            base_indices = [0] * len(sweep_axes)
            for axis_index, duration_index in zip(
                duration_axis_indices,
                duration_indices,
            ):
                base_indices[axis_index] = int(duration_index)
            base_point = int(
                np.ravel_multi_index(
                    tuple(base_indices),
                    sweep_shape,
                    order="C",
                )
            )
            base = int(requested[base_point])
            bases.append(base)
            for axis_index in axis_rows:
                endpoint_indices = list(base_indices)
                endpoint_indices[axis_index] = sweep_axes[axis_index].count - 1
                endpoint_point = int(
                    np.ravel_multi_index(
                        tuple(endpoint_indices),
                        sweep_shape,
                        order="C",
                    )
                )
                units = _round_div_nearest(
                    int(requested[endpoint_point]) - base,
                    (sweep_axes[axis_index].count - 1) * int(quantum),
                )
                axis_rows[axis_index].append(units * int(quantum))

        actual = np.empty_like(requested)
        max_error = 0
        for point_index in range(requested.size):
            self._check_cancel()
            indices = np.unravel_index(point_index, sweep_shape, order="C")
            duration_indices = tuple(
                int(indices[axis_index])
                for axis_index in duration_axis_indices
            )
            duration_row = int(
                np.ravel_multi_index(
                    duration_indices,
                    duration_shape,
                    order="C",
                )
            )
            value = int(bases[duration_row])
            for axis_index, deltas in axis_rows.items():
                value += int(indices[axis_index]) * int(deltas[duration_row])
            actual[point_index] = value
            max_error = max(
                max_error,
                abs(value - int(requested[point_index])),
            )
        return (
            tuple(int(value) for value in bases),
            {
                int(axis_index): tuple(int(value) for value in values)
                for axis_index, values in axis_rows.items()
            },
            actual,
            int(max_error),
        )

    def _linear_bias_t_models(
        self,
        requested_array,
        sweep_axes,
        sweep_shape,
        *,
        register_name,
        metadata,
    ):
        """Represent a linear per-output Bias-T state with sweep-axis adds."""
        duration_axis_indices = self._bias_t_conditioning_axis_indices(sweep_axes)
        models = []
        actual = np.empty_like(requested_array)
        max_error = 0
        for output_index in range(self.sequence.n_outputs):
            quantum = int(metadata[output_index].get("quantum", 1))
            if duration_axis_indices:
                bases, table_axis_deltas, output_actual, output_error = (
                    self._duration_axes_conditioned_values(
                        requested_array[:, output_index],
                        sweep_axes,
                        sweep_shape,
                        duration_axis_indices=duration_axis_indices,
                        quantum=quantum,
                    )
                )
                model = {
                    "key": ("bias_t", output_index, register_name),
                    "register_name": register_name,
                    "base": int(bases[0]),
                    "axis_deltas": tuple(0 for _axis in sweep_axes),
                    "duration_table_bases": bases,
                    "duration_table_axis_deltas": table_axis_deltas,
                    "duration_axis_index": duration_axis_indices[0],
                    "duration_axis_indices": duration_axis_indices,
                    "duration_table_shape": tuple(
                        int(sweep_axes[axis_index].count)
                        for axis_index in duration_axis_indices
                    ),
                    "output_index": output_index,
                    "gen_ch": self.awg_channels[output_index],
                }
                model.update(metadata[output_index])
                models.append(model)
                actual[:, output_index] = output_actual
                max_error = max(max_error, output_error)
                continue

            base = int(requested_array[0, output_index])
            axis_deltas = []
            for axis_index, axis in enumerate(sweep_axes):
                if axis.count <= 1:
                    axis_deltas.append(0)
                    continue
                indices = [0] * len(sweep_axes)
                indices[axis_index] = axis.count - 1
                endpoint_index = int(
                    np.ravel_multi_index(tuple(indices), sweep_shape, order="C")
                )
                endpoint = int(requested_array[endpoint_index, output_index])
                units = _round_div_nearest(
                    endpoint - base,
                    (axis.count - 1) * quantum,
                )
                axis_deltas.append(units * quantum)
            model = {
                "key": ("bias_t", output_index, register_name),
                "register_name": register_name,
                "base": base,
                "axis_deltas": tuple(axis_deltas),
                "output_index": output_index,
                "gen_ch": self.awg_channels[output_index],
            }
            model.update(metadata[output_index])
            models.append(model)
            for point_index in range(len(self.compiled_points)):
                self._check_cancel()
                indices = (
                    np.unravel_index(point_index, sweep_shape, order="C")
                    if sweep_axes
                    else ()
                )
                value = int(model["base"]) + sum(
                    int(index) * int(delta)
                    for index, delta in zip(indices, model["axis_deltas"])
                )
                actual[point_index, output_index] = value
                max_error = max(
                    max_error,
                    abs(value - int(requested_array[point_index, output_index])),
                )
        return tuple(models), actual, int(max_error)

    def _build_bias_t_models(self, sweep_axes, sweep_shape):
        """Build fixed-voltage duration or fixed-time target-code states."""
        config = self.sequence.bias_t_compensation
        self._bias_t_mode = (
            None
            if config is None
            else config.mode
        )
        self._bias_t_comp_codes = ()
        self._bias_t_duration_q_requested = np.empty((0, 0), dtype=np.int64)
        self._bias_t_duration_q_actual = np.empty((0, 0), dtype=np.int64)
        self._bias_t_target_code_requested = np.empty((0, 0), dtype=np.int64)
        self._bias_t_target_code_actual = np.empty((0, 0), dtype=np.int64)
        self._bias_t_max_duration_q_error = 0
        self._bias_t_max_target_code_error = 0
        if config is None:
            self._bias_t_fields = ()
            return ()

        if config.mode == "fixed_time":
            duration = int(config.fixed_duration_cycles)
            metadata = []
            limits = []
            for gen_ch in self.awg_channels:
                gen_cfg = self.soccfg["gens"][gen_ch]
                minimum = int(gen_cfg.get("minv", -32768))
                maximum = int(gen_cfg.get("maxv", 32764))
                quantum = 1 << int(gen_cfg.get("dac_invalid_lsb", 2))
                fabric_mhz = Fraction(str(gen_cfg["f_fabric"]))
                duration_ratio = (
                    Fraction(duration) * Fraction(str(self.tproc_mhz)) / fabric_mhz
                )
                duration_tproc = max(
                    1,
                    (duration_ratio.numerator + duration_ratio.denominator - 1)
                    // duration_ratio.denominator,
                )
                limits.append((minimum, maximum, quantum))
                metadata.append(
                    {
                        "fixed_duration_fabric_cycles": duration,
                        "fixed_duration_tproc_cycles": int(duration_tproc),
                        "quantum": quantum,
                    }
                )

            requested = []
            for point_index, point in enumerate(self.compiled_points):
                self._check_cancel()
                point_values = []
                for output_index, signed_area2 in enumerate(
                    self._compiled_point_area2(point_index, point)
                ):
                    minimum, maximum, quantum = limits[output_index]
                    units = _round_div_nearest(
                        -int(signed_area2),
                        2 * duration * quantum,
                    )
                    target_code = units * quantum
                    if target_code < minimum or target_code > maximum:
                        raise ValueError(
                            "Bias-T fixed compensation time is too short for "
                            f"{self.sequence.output_names[output_index]}; required "
                            f"DAC code {target_code} is outside "
                            f"[{minimum}, {maximum}]"
                        )
                    point_values.append(target_code)
                requested.append(tuple(point_values))
            requested_array = np.asarray(requested, dtype=np.int64)
            models, actual, max_error = self._linear_bias_t_models(
                requested_array,
                sweep_axes,
                sweep_shape,
                register_name="bias_t_target_code",
                metadata=metadata,
            )
            self._bias_t_target_code_requested = requested_array
            self._bias_t_target_code_actual = actual
            self._bias_t_max_target_code_error = max_error
            return models

        scale = 1 << int(config.duration_frac_bits)
        rounding = scale >> 1
        comp_codes = []
        metadata = []
        for gen_ch in self.awg_channels:
            gen_cfg = self.soccfg["gens"][gen_ch]
            kwargs = {
                "min_code": int(gen_cfg.get("minv", -32768)),
                "max_code": int(gen_cfg.get("maxv", 32764)),
                "invalid_lsb": int(gen_cfg.get("dac_invalid_lsb", 2)),
            }
            positive = normalized_to_dac(config.amplitude, **kwargs)
            negative = normalized_to_dac(-config.amplitude, **kwargs)
            if positive <= 0 or negative >= 0:
                raise ValueError(
                    "Bias-T compensation voltage is below one legal DAC code"
                )
            comp_codes.append((positive, negative))
            metadata.append(
                {
                    "positive_code": int(positive),
                    "negative_code": int(negative),
                    "duration_frac_bits": int(config.duration_frac_bits),
                }
            )

        requested = []
        for point_index, point in enumerate(self.compiled_points):
            self._check_cancel()
            area2 = self._compiled_point_area2(point_index, point)
            point_values = []
            for output_index, signed_area2 in enumerate(area2):
                if signed_area2 == 0:
                    duration_q = 0
                else:
                    positive, negative = comp_codes[output_index]
                    target_magnitude = abs(negative) if signed_area2 > 0 else positive
                    gen_ch = self.awg_channels[output_index]
                    fabric_mhz = Fraction(
                        str(self.soccfg["gens"][gen_ch]["f_fabric"])
                    )
                    ratio = Fraction(
                        int(signed_area2) * scale,
                        2 * int(target_magnitude),
                    ) * Fraction(str(self.tproc_mhz)) / fabric_mhz
                    duration_q = _round_div_nearest(
                        ratio.numerator,
                        ratio.denominator,
                    )
                if abs(duration_q) + rounding > (1 << 31) - 1:
                    raise ValueError(
                        "Bias-T compensation duration exceeds the signed 32-bit "
                        "tProcessor fixed-point range; increase compensation voltage"
                    )
                point_values.append(duration_q)
            requested.append(tuple(point_values))
        requested_array = np.asarray(requested, dtype=np.int64)
        models, actual, max_error = self._linear_bias_t_models(
            requested_array,
            sweep_axes,
            sweep_shape,
            register_name="bias_t_duration_q",
            metadata=metadata,
        )
        self._bias_t_comp_codes = tuple(comp_codes)
        self._bias_t_duration_q_requested = requested_array
        self._bias_t_duration_q_actual = actual
        self._bias_t_max_duration_q_error = max_error
        return models

    def _boundary_bias_models_from_values(
        self,
        sweep_axes,
        sweep_shape,
        *,
        register_name,
        metadata,
        value_at,
    ):
        """Build and check Bias-T models without expanding Cartesian points."""
        validation_indices = self._compile_validation_point_indices
        duration_axes = self._bias_t_conditioning_axis_indices(sweep_axes)
        requested = np.asarray(
            [
                [
                    int(value_at(point_index, output_index))
                    for output_index in range(self.sequence.n_outputs)
                ]
                for point_index in validation_indices
            ],
            dtype=np.int64,
        )
        actual = np.empty_like(requested)
        models = []
        max_error = 0

        for output_index in range(self.sequence.n_outputs):
            quantum = int(metadata[output_index].get("quantum", 1))
            if duration_axes:
                duration_shape = tuple(
                    int(sweep_axes[axis_index].count)
                    for axis_index in duration_axes
                )
                bases = []
                axis_rows = {
                    axis_index: []
                    for axis_index, axis in enumerate(sweep_axes)
                    if axis_index not in duration_axes and axis.count > 1
                }
                for duration_indices in np.ndindex(duration_shape):
                    base_indices = [0] * len(sweep_axes)
                    for axis_index, duration_index in zip(
                        duration_axes,
                        duration_indices,
                    ):
                        base_indices[axis_index] = int(duration_index)
                    base_point = int(
                        np.ravel_multi_index(
                            tuple(base_indices),
                            sweep_shape,
                            order="C",
                        )
                    )
                    base = int(value_at(base_point, output_index))
                    bases.append(base)
                    for axis_index in axis_rows:
                        endpoint_indices = list(base_indices)
                        endpoint_indices[axis_index] = (
                            sweep_axes[axis_index].count - 1
                        )
                        endpoint_point = int(
                            np.ravel_multi_index(
                                tuple(endpoint_indices),
                                sweep_shape,
                                order="C",
                            )
                        )
                        units = _round_div_nearest(
                            int(value_at(endpoint_point, output_index)) - base,
                            (
                                sweep_axes[axis_index].count - 1
                            ) * quantum,
                        )
                        axis_rows[axis_index].append(units * quantum)
                model = {
                    "key": ("bias_t", output_index, register_name),
                    "register_name": register_name,
                    "base": int(bases[0]),
                    "axis_deltas": tuple(0 for _axis in sweep_axes),
                    "duration_table_bases": tuple(bases),
                    "duration_table_axis_deltas": {
                        int(axis_index): tuple(values)
                        for axis_index, values in axis_rows.items()
                    },
                    "duration_axis_index": duration_axes[0],
                    "duration_axis_indices": duration_axes,
                    "duration_table_shape": duration_shape,
                    "output_index": output_index,
                    "gen_ch": self.awg_channels[output_index],
                }
            else:
                base = int(value_at(0, output_index))
                axis_deltas = []
                for axis_index, axis in enumerate(sweep_axes):
                    if axis.count <= 1:
                        axis_deltas.append(0)
                        continue
                    endpoint_indices = [0] * len(sweep_axes)
                    endpoint_indices[axis_index] = axis.count - 1
                    endpoint_point = int(
                        np.ravel_multi_index(
                            tuple(endpoint_indices),
                            sweep_shape,
                            order="C",
                        )
                    )
                    units = _round_div_nearest(
                        int(value_at(endpoint_point, output_index)) - base,
                        (axis.count - 1) * quantum,
                    )
                    axis_deltas.append(units * quantum)
                model = {
                    "key": ("bias_t", output_index, register_name),
                    "register_name": register_name,
                    "base": base,
                    "axis_deltas": tuple(axis_deltas),
                    "output_index": output_index,
                    "gen_ch": self.awg_channels[output_index],
                }
            model.update(metadata[output_index])
            models.append(model)

            for row, point_index in enumerate(validation_indices):
                indices = (
                    np.unravel_index(point_index, sweep_shape, order="C")
                    if sweep_axes
                    else ()
                )
                if "duration_table_bases" in model:
                    duration_indices = tuple(
                        int(indices[axis_index])
                        for axis_index in duration_axes
                    )
                    duration_row = int(
                        np.ravel_multi_index(
                            duration_indices,
                            model["duration_table_shape"],
                            order="C",
                        )
                    )
                    value = int(
                        model["duration_table_bases"][duration_row]
                    )
                    for axis_index, deltas in model[
                        "duration_table_axis_deltas"
                    ].items():
                        value += (
                            int(indices[axis_index])
                            * int(deltas[duration_row])
                        )
                else:
                    value = int(model["base"]) + sum(
                        int(index) * int(delta)
                        for index, delta in zip(
                            indices,
                            model["axis_deltas"],
                        )
                    )
                actual[row, output_index] = value
                max_error = max(
                    max_error,
                    abs(
                        value
                        - int(value_at(point_index, output_index))
                    ),
                )

        return tuple(models), requested, actual, int(max_error)

    def _build_bias_t_models_boundary(self, sweep_axes, sweep_shape):
        """Build Bias-T state from boundary and duration-table points only."""
        config = self.sequence.bias_t_compensation
        self._bias_t_mode = (
            None
            if config is None
            else config.mode
        )
        self._bias_t_comp_codes = ()
        self._bias_t_duration_q_requested = np.empty((0, 0), dtype=np.int64)
        self._bias_t_duration_q_actual = np.empty((0, 0), dtype=np.int64)
        self._bias_t_target_code_requested = np.empty((0, 0), dtype=np.int64)
        self._bias_t_target_code_actual = np.empty((0, 0), dtype=np.int64)
        self._bias_t_max_duration_q_error = 0
        self._bias_t_max_target_code_error = 0
        if config is None:
            self._bias_t_fields = ()
            return ()

        area_cache = {
            point_index: self._compiled_point_area2(
                point_index,
                self._compiled_point_by_index[point_index],
            )
            for point_index in self._compile_validation_point_indices
        }

        if config.mode == "fixed_time":
            duration = int(config.fixed_duration_cycles)
            metadata = []
            limits = []
            for gen_ch in self.awg_channels:
                gen_cfg = self.soccfg["gens"][gen_ch]
                minimum = int(gen_cfg.get("minv", -32768))
                maximum = int(gen_cfg.get("maxv", 32764))
                quantum = 1 << int(gen_cfg.get("dac_invalid_lsb", 2))
                fabric_mhz = Fraction(str(gen_cfg["f_fabric"]))
                duration_ratio = (
                    Fraction(duration)
                    * Fraction(str(self.tproc_mhz))
                    / fabric_mhz
                )
                duration_tproc = max(
                    1,
                    (
                        duration_ratio.numerator
                        + duration_ratio.denominator
                        - 1
                    ) // duration_ratio.denominator,
                )
                limits.append((minimum, maximum, quantum))
                metadata.append({
                    "fixed_duration_fabric_cycles": duration,
                    "fixed_duration_tproc_cycles": int(duration_tproc),
                    "quantum": quantum,
                })

            def target_at(point_index, output_index):
                minimum, maximum, quantum = limits[output_index]
                units = _round_div_nearest(
                    -int(area_cache[int(point_index)][output_index]),
                    2 * duration * quantum,
                )
                target = units * quantum
                if target < minimum or target > maximum:
                    raise ValueError(
                        "Bias-T fixed compensation time is too short for "
                        f"{self.sequence.output_names[output_index]}; required "
                        f"DAC code {target} is outside [{minimum}, {maximum}]"
                    )
                return target

            models, requested, actual, max_error = (
                self._boundary_bias_models_from_values(
                    sweep_axes,
                    sweep_shape,
                    register_name="bias_t_target_code",
                    metadata=metadata,
                    value_at=target_at,
                )
            )
            self._bias_t_target_code_requested = requested
            self._bias_t_target_code_actual = actual
            self._bias_t_max_target_code_error = max_error
            return models

        scale = 1 << int(config.duration_frac_bits)
        rounding = scale >> 1
        comp_codes = []
        metadata = []
        for gen_ch in self.awg_channels:
            gen_cfg = self.soccfg["gens"][gen_ch]
            kwargs = {
                "min_code": int(gen_cfg.get("minv", -32768)),
                "max_code": int(gen_cfg.get("maxv", 32764)),
                "invalid_lsb": int(gen_cfg.get("dac_invalid_lsb", 2)),
            }
            positive = normalized_to_dac(config.amplitude, **kwargs)
            negative = normalized_to_dac(-config.amplitude, **kwargs)
            if positive <= 0 or negative >= 0:
                raise ValueError(
                    "Bias-T compensation voltage is below one legal DAC code"
                )
            comp_codes.append((positive, negative))
            metadata.append({
                "positive_code": int(positive),
                "negative_code": int(negative),
                "duration_frac_bits": int(config.duration_frac_bits),
            })

        def duration_at(point_index, output_index):
            signed_area2 = int(area_cache[int(point_index)][output_index])
            if signed_area2 == 0:
                duration_q = 0
            else:
                positive, negative = comp_codes[output_index]
                target_magnitude = (
                    abs(negative) if signed_area2 > 0 else positive
                )
                gen_ch = self.awg_channels[output_index]
                fabric_mhz = Fraction(
                    str(self.soccfg["gens"][gen_ch]["f_fabric"])
                )
                ratio = Fraction(
                    signed_area2 * scale,
                    2 * int(target_magnitude),
                ) * Fraction(str(self.tproc_mhz)) / fabric_mhz
                duration_q = _round_div_nearest(
                    ratio.numerator,
                    ratio.denominator,
                )
            if abs(duration_q) + rounding > (1 << 31) - 1:
                raise ValueError(
                    "Bias-T compensation duration exceeds the signed 32-bit "
                    "tProcessor fixed-point range; increase compensation voltage"
                )
            return duration_q

        models, requested, actual, max_error = (
            self._boundary_bias_models_from_values(
                sweep_axes,
                sweep_shape,
                register_name="bias_t_duration_q",
                metadata=metadata,
                value_at=duration_at,
            )
        )
        self._bias_t_comp_codes = tuple(comp_codes)
        self._bias_t_duration_q_requested = requested
        self._bias_t_duration_q_actual = actual
        self._bias_t_max_duration_q_error = max_error
        return models

    def _build_rf_point_table_models(self, sweep_axes):
        """Build compact DMEM tables for exact RF frequency, gain and length."""
        tables = []
        frequency_table_keys = set()
        axis_positions = {
            id(axis): int(index) for index, axis in enumerate(sweep_axes)
        }
        for rf_index, rf in enumerate(self.rf_pulse_configs):
            runtime = self._rf_runtime[rf_index]
            duration_axis = runtime["duration_axis"]
            if (duration_axis is not None and duration_axis.count > 1
                    and not runtime["periodic"]):
                page, command_register = self._gen_regmap[(rf.gen_ch, "mode")]
                tables.append({
                    "key": ("rf_point_table", int(rf_index), "duration"),
                    "register_name": "rf_duration",
                    "gen_ch": int(rf.gen_ch),
                    "event_indices": (int(rf_index),),
                    "page": int(page),
                    "command_register": int(command_register),
                    "axis_indices": (axis_positions[id(duration_axis)],),
                    "axis_shape": (int(duration_axis.count),),
                    # Use the generator manager to retain its mode/TMUX bits.
                    "values": tuple(
                        self._gen_mgrs[rf.gen_ch].get_mode_code(
                            length=self._rf_duration_fabric_cycles(rf, value),
                            mode="oneshot", outsel="dds", stdysel=rf.stdysel,
                            phrst=0,
                        )
                        for value in duration_axis.points
                    ),
                })
            frequency_axis = self._rf_frequency_axis(rf)
            power_axis = self._rf_power_axis(rf.gen_ch)
            frequency_axis_index = (
                None
                if frequency_axis is None
                else axis_positions[id(frequency_axis)]
            )
            power_axis_index = (
                None if power_axis is None else axis_positions[id(power_axis)]
            )

            frequency_table_key = (
                int(rf.gen_ch),
                str(rf.frequency_parameter),
            )
            if (
                frequency_axis is not None
                and frequency_axis.count > 1
                and frequency_table_key not in frequency_table_keys
            ):
                frequency_table_keys.add(frequency_table_key)
                page, command_register = self._gen_regmap[
                    (rf.gen_ch, "freq")
                ]
                event_indices = tuple(
                    index
                    for index, candidate in enumerate(self.rf_pulse_configs)
                    if int(candidate.gen_ch) == int(rf.gen_ch)
                    and str(candidate.frequency_parameter)
                    == str(rf.frequency_parameter)
                )
                tables.append({
                    "key": (
                        "rf_point_table",
                        int(rf.gen_ch),
                        str(rf.frequency_parameter),
                        "frequency",
                    ),
                    "register_name": "rf_frequency",
                    "gen_ch": int(rf.gen_ch),
                    "event_indices": event_indices,
                    "page": int(page),
                    "command_register": int(command_register),
                    "axis_indices": (int(frequency_axis_index),),
                    "axis_shape": (int(frequency_axis.count),),
                    "values": tuple(
                        self._rf_frequency_word(rf, value)
                        for value in frequency_axis.points
                    ),
                })

            if not rf.sweep_gain_codes:
                continue
            frequency_count, power_count = tuple(rf.sweep_gain_shape)
            relevant = []
            if frequency_axis is not None and frequency_axis.count > 1:
                relevant.append((
                    int(frequency_axis_index),
                    "frequency",
                    int(frequency_axis.count),
                ))
            if power_axis is not None and power_axis.count > 1:
                relevant.append((
                    int(power_axis_index),
                    "power",
                    int(power_axis.count),
                ))
            relevant.sort(key=lambda item: item[0])
            if not relevant:
                continue

            table_values = []
            relevant_shape = tuple(item[2] for item in relevant)
            for coordinate in product(
                *(range(count) for count in relevant_shape)
            ):
                selected = {
                    kind: int(coordinate[position])
                    for position, (_axis, kind, _count) in enumerate(relevant)
                }
                frequency_index = selected.get("frequency", 0)
                power_index = selected.get("power", 0)
                table_values.append(
                    int(
                        rf.sweep_gain_codes[
                            frequency_index * power_count + power_index
                        ]
                    )
                )
            if len(table_values) != int(np.prod(relevant_shape, dtype=np.int64)):
                raise RuntimeError("RF gain point-table shape is inconsistent")
            if frequency_count != (
                1 if frequency_axis is None else frequency_axis.count
            ):
                raise RuntimeError("RF gain table frequency dimension is inconsistent")

            page, command_register = self._gen_regmap[
                (rf.gen_ch, "gain")
            ]
            tables.append({
                "key": (
                    "rf_point_table",
                    int(rf.gen_ch),
                    str(rf.event_id),
                    "gain",
                ),
                "register_name": "rf_gain",
                "gen_ch": int(rf.gen_ch),
                "event_indices": (int(rf_index),),
                "page": int(page),
                "command_register": int(command_register),
                "axis_indices": tuple(item[0] for item in relevant),
                "axis_shape": relevant_shape,
                "values": tuple(table_values),
            })
        return tables

    def _build_sweep_register_plan(self):
        """Map Cartesian sweep axes to tProcessor register increments."""
        validation_indices = tuple(self._compile_validation_point_indices)
        command_maps = {}
        command_order = []
        for validation_position, (point_index, point) in enumerate(zip(
            validation_indices,
            self.compiled_points,
        )):
            self._check_cancel()
            point_map = {}
            for commands in point.segment_commands:
                for command in commands:
                    key = self._command_key(command)
                    if key in point_map:
                        raise RuntimeError(f"duplicate compiled command key {key}")
                    point_map[key] = command
                    if validation_position == 0:
                        command_order.append(key)
            command_maps[int(point_index)] = point_map

        expected_keys = set(command_order)
        for point_index in validation_indices[1:]:
            point_map = command_maps[int(point_index)]
            if set(point_map) != expected_keys:
                raise RuntimeError(
                    f"sweep point {point_index} changes the active AWG command set"
                )

        sweep_axes = self.sequence.sweep_axes
        sweep_shape = tuple(axis.count for axis in sweep_axes)
        ramp_duration_axes = self._ramp_duration_axis_by_segment(sweep_axes)
        models = {}
        for key in command_order:
            first_command = command_maps[0][key]
            selected_ramp_axis_index = (
                ramp_duration_axes.get(first_command.segment_name)
                if first_command.kind == "ramp"
                else None
            )
            field_specs = [("target", 0), ("step", 3)]
            if selected_ramp_axis_index is not None:
                field_specs.append(("duration", 2))
            for register_name, word_index in field_specs:
                if register_name == "target":
                    base = int(first_command.target_code)
                    quantum = 1 << int(
                        self.soccfg["gens"][first_command.gen_ch].get(
                            "dac_invalid_lsb", 2
                        )
                    )
                elif register_name == "step":
                    base = int(first_command.step)
                    quantum = 1
                else:
                    base = int(first_command.duration_samples)
                    quantum = 1

                def requested_value(point_index):
                    command = command_maps[int(point_index)][key]
                    if register_name == "target":
                        return int(command.target_code)
                    if register_name == "step":
                        return int(command.step)
                    return int(command.duration_samples)

                if selected_ramp_axis_index is not None and register_name == "step":
                    if self.compile_validation_mode == COMPILE_VALIDATION_FULL:
                        requested_values = np.asarray(
                            [
                                requested_value(point_index)
                                for point_index in validation_indices
                            ],
                            dtype=np.int64,
                        )
                        (
                            table_bases,
                            table_axis_deltas,
                            _actual,
                            _max_error,
                        ) = self._duration_conditioned_values(
                            requested_values,
                            sweep_axes,
                            sweep_shape,
                            duration_axis_index=selected_ramp_axis_index,
                            quantum=quantum,
                        )
                    else:
                        table_bases = []
                        table_axis_deltas = {
                            axis_index: []
                            for axis_index, axis in enumerate(sweep_axes)
                            if (
                                axis_index != selected_ramp_axis_index
                                and axis.count > 1
                            )
                        }
                        for duration_index in range(
                            sweep_axes[selected_ramp_axis_index].count
                        ):
                            base_indices = [0] * len(sweep_axes)
                            base_indices[
                                selected_ramp_axis_index
                            ] = duration_index
                            base_point = int(
                                np.ravel_multi_index(
                                    tuple(base_indices),
                                    sweep_shape,
                                    order="C",
                                )
                            )
                            row_base = requested_value(base_point)
                            table_bases.append(row_base)
                            for axis_index in table_axis_deltas:
                                endpoint_indices = list(base_indices)
                                endpoint_indices[axis_index] = (
                                    sweep_axes[axis_index].count - 1
                                )
                                endpoint_point = int(
                                    np.ravel_multi_index(
                                        tuple(endpoint_indices),
                                        sweep_shape,
                                        order="C",
                                    )
                                )
                                units = _round_div_nearest(
                                    requested_value(endpoint_point) - row_base,
                                    (
                                        sweep_axes[axis_index].count - 1
                                    ) * quantum,
                                )
                                table_axis_deltas[axis_index].append(
                                    units * quantum
                                )
                        table_bases = tuple(table_bases)
                        table_axis_deltas = {
                            int(axis_index): tuple(values)
                            for axis_index, values
                            in table_axis_deltas.items()
                        }
                    models[(*key, register_name)] = {
                        "key": (*key, register_name),
                        "command_key": key,
                        "register_name": register_name,
                        "word_index": word_index,
                        "base": int(table_bases[0]),
                        "axis_deltas": tuple(0 for _axis in sweep_axes),
                        "duration_table_bases": table_bases,
                        "duration_table_axis_deltas": table_axis_deltas,
                        "duration_axis_index": selected_ramp_axis_index,
                        "duration_axis_indices": (selected_ramp_axis_index,),
                        "duration_table_shape": (
                            int(sweep_axes[selected_ramp_axis_index].count),
                        ),
                    }
                    continue

                axis_deltas = []
                for axis_index, axis in enumerate(sweep_axes):
                    if axis.count <= 1:
                        axis_deltas.append(0)
                        continue
                    indices = [0] * len(sweep_axes)
                    indices[axis_index] = axis.count - 1
                    endpoint_index = int(
                        np.ravel_multi_index(tuple(indices), sweep_shape, order="C")
                    )
                    endpoint = requested_value(endpoint_index)
                    units = _round_div_nearest(
                        endpoint - base,
                        (axis.count - 1) * quantum,
                    )
                    axis_deltas.append(units * quantum)
                models[(*key, register_name)] = {
                    "key": (*key, register_name),
                    "command_key": key,
                    "register_name": register_name,
                    "word_index": word_index,
                    "base": base,
                    "axis_deltas": tuple(axis_deltas),
                }

        requested_points = self.compiled_points
        actual_points = []
        actual_point_indices = []
        max_target_error = 0
        max_step_error = 0
        max_duration_error = 0

        def model_value(model, indices):
            if "duration_table_bases" not in model:
                return int(model["base"]) + sum(
                    int(index) * int(delta)
                    for index, delta in zip(indices, model["axis_deltas"])
                )
            duration_axis_indices = tuple(
                int(axis_index)
                for axis_index in model.get(
                    "duration_axis_indices",
                    (model["duration_axis_index"],),
                )
            )
            duration_shape = tuple(
                int(value)
                for value in model.get(
                    "duration_table_shape",
                    tuple(
                        int(sweep_axes[axis_index].count)
                        for axis_index in duration_axis_indices
                    ),
                )
            )
            duration_indices = tuple(
                int(indices[axis_index])
                for axis_index in duration_axis_indices
            )
            duration_row = int(
                np.ravel_multi_index(
                    duration_indices,
                    duration_shape,
                    order="C",
                )
            )
            value = int(model["duration_table_bases"][duration_row])
            for axis_index, deltas in model[
                "duration_table_axis_deltas"
            ].items():
                value += int(indices[axis_index]) * int(deltas[duration_row])
            return value

        for point_index, requested_point in zip(
            validation_indices,
            requested_points,
        ):
            self._check_cancel()
            if sweep_axes:
                indices = np.unravel_index(point_index, sweep_shape, order="C")
            else:
                indices = ()
            actual_segments = []
            for commands in requested_point.segment_commands:
                actual_commands = []
                for command in commands:
                    command_key = self._command_key(command)
                    target_model = models[(*command_key, "target")]
                    step_model = models[(*command_key, "step")]
                    duration_model = models.get((*command_key, "duration"))
                    target = model_value(target_model, indices)
                    step = model_value(step_model, indices)
                    duration_samples = (
                        int(command.duration_samples)
                        if duration_model is None
                        else model_value(duration_model, indices)
                    )
                    gen_cfg = self.soccfg["gens"][command.gen_ch]
                    opcode = OP_SET if command.kind == "set" else OP_RAMP
                    words = _pack_command_words(
                        gen_cfg,
                        target,
                        duration_samples,
                        step,
                        opcode,
                    )
                    actual_commands.append(
                        replace(
                            command,
                            target_code=target,
                            duration_samples=duration_samples,
                            step=step,
                            words=words,
                        )
                    )
                    max_target_error = max(
                        max_target_error, abs(target - int(command.target_code))
                    )
                    max_step_error = max(max_step_error, abs(step - int(command.step)))
                    max_duration_error = max(
                        max_duration_error,
                        abs(duration_samples - int(command.duration_samples)),
                    )
                actual_segments.append(tuple(actual_commands))
            actual_points.append(
                replace(requested_point, segment_commands=tuple(actual_segments))
            )
            actual_point_indices.append(int(point_index))

        self.requested_compiled_points = requested_points
        if self.compile_validation_mode == COMPILE_VALIDATION_FULL:
            self.compiled_points = tuple(actual_points)
        else:
            self._compiled_point_by_index = {
                point_index: point
                for point_index, point in zip(
                    actual_point_indices,
                    actual_points,
                )
            }
            self.compiled_points = (self._compiled_point_by_index[0],)

        if self.compile_validation_mode == COMPILE_VALIDATION_FULL:
            bias_t_models = self._build_bias_t_models(
                sweep_axes,
                sweep_shape,
            )
        else:
            bias_t_models = self._build_bias_t_models_boundary(
                sweep_axes,
                sweep_shape,
            )
        event_timing_models = self._build_event_timing_models()

        fields = []
        for model in models.values():
            if (
                not any(model["axis_deltas"])
                and "duration_table_bases" not in model
            ):
                continue
            first_command = command_maps[0][model["command_key"]]
            page, command_register = self._gen_regmap[
                (first_command.gen_ch, model["register_name"])
            ]
            field = dict(model)
            field.update({
                "page": int(page),
                "command_register": int(command_register),
            })
            fields.append(field)
        for model in bias_t_models:
            page, _target_register = self._gen_regmap[
                (int(model["gen_ch"]), "target")
            ]
            field = dict(model)
            field["page"] = int(page)
            fields.append(field)
        fields.extend(
            dict(model)
            for model in event_timing_models
            if not model.get("timing_only")
        )
        rf_point_tables = self._build_rf_point_table_models(sweep_axes)
        rf_point_tables.extend(self._square_point_table_models(sweep_axes))

        occupied = {page: {0} for page in range(8)}
        for register_map in (self._gen_regmap, self._ro_regmap):
            for page, register in register_map.values():
                occupied[int(page)].add(int(register))
        # These are used below for the shot count and repetition loop.
        occupied[0].update((13, 15))
        if self._marker is not None:
            occupied[0].update((16, 17, 18, 19, 20))
        if (self._marker is not None or self.square_pulse_config is not None
                or self.sequence.rc_compensation is not None):
            occupied[0].add(14)
            # The inherited trigger() helper writes page-zero register 16.
            # Keep new sweep state out of it even without an external marker.
            occupied[0].add(16)
        for field in fields:
            page = int(field["page"])
            allocations = (
                (
                    "allocate_command_register",
                    "command_register",
                    "dynamic event-time",
                ),
                (
                    "allocate_output_register",
                    "output_register",
                    "dynamic output-data",
                ),
            )
            for flag, destination, description in allocations:
                if not field.pop(flag, False):
                    continue
                available = [
                    register
                    for register in range(1, 32)
                    if register not in occupied[page]
                ]
                if not available:
                    raise RuntimeError(
                        f"register page {page} has no {description} register"
                    )
                field[destination] = int(available[0])
                occupied[page].add(int(available[0]))

        for table in rf_point_tables:
            page = int(table["page"])
            available = [
                register
                for register in range(1, 32)
                if register not in occupied[page]
            ]
            if not available:
                raise RuntimeError(
                    f"register page {page} has no RF point-table pointer register"
                )
            table["pointer_register"] = int(available[0])
            occupied[page].add(int(available[0]))

        dmem_size = int(self.tproccfg.get("dmem_size", 0))
        next_dmem_addr = dmem_size - 1

        def assign_dmem(field, work_register):
            nonlocal next_dmem_addr
            # DMEM address 1 is owned by the acquisition counter. Allocate
            # sweep backing words downward from the end of memory.
            if next_dmem_addr <= 1:
                raise RuntimeError(
                    "tProcessor DMEM has no room for spilled sweep state"
                )
            field["storage"] = "dmem"
            field["dmem_addr"] = next_dmem_addr
            field["work_register"] = int(work_register)
            next_dmem_addr -= 1

        for field in fields:
            page = field["page"]
            if field.get("register_name") in {
                "bias_t_duration_q",
                "bias_t_target_code",
            }:
                work_page, work_register = self._gen_regmap[
                    (int(field["gen_ch"]), "duration")
                ]
                if int(work_page) != page:
                    raise RuntimeError(
                        "AWG duration and Bias-T state registers must share one page"
                    )
                # Compensation uses OP_SET, whose duration field is ignored by
                # the AWG RTL. It is therefore a safe calculation scratch reg.
                assign_dmem(field, work_register)
                field["work_register_source"] = "awg_duration_command"
                continue

            available = [
                register for register in range(1, 32) if register not in occupied[page]
            ]
            if not available:
                # Arithmetic cannot operate on DMEM directly, so use the
                # destination command register as a temporary load/add/store
                # register when this state is consumed or advanced.
                assign_dmem(field, int(field["command_register"]))
                field["work_register_source"] = "awg_command"
                continue
            field["storage"] = "register"
            field["state_register"] = available[0]
            occupied[page].add(available[0])

        if bias_t_models:
            if next_dmem_addr <= 1:
                raise RuntimeError(
                    "tProcessor DMEM has no room for the Bias-T maximum duration"
                )
            self._bias_t_max_duration_dmem_addr = next_dmem_addr
            next_dmem_addr -= 1
        else:
            self._bias_t_max_duration_dmem_addr = None

        dynamic_duration_fields = [
            field
            for field in fields
            if "duration_table_bases" in field
        ]
        for field in dynamic_duration_fields:
            field["duration_delta_slots"] = {}
            for axis_index, deltas in field[
                "duration_table_axis_deltas"
            ].items():
                if not any(int(value) for value in deltas):
                    continue
                if next_dmem_addr - 1 <= 1:
                    raise RuntimeError(
                        "tProcessor DMEM has no room for RAMP-rate deltas"
                    )
                advance_addr = next_dmem_addr
                reset_addr = next_dmem_addr - 1
                next_dmem_addr -= 2
                field["duration_delta_slots"][int(axis_index)] = {
                    "advance": int(advance_addr),
                    "reset": int(reset_addr),
                }

        table_groups = {}
        for field in dynamic_duration_fields:
            page = int(field["page"])
            duration_axis_indices = tuple(
                int(axis_index)
                for axis_index in field.get(
                    "duration_axis_indices",
                    (field["duration_axis_index"],),
                )
            )
            duration_shape = tuple(
                int(value)
                for value in field.get(
                    "duration_table_shape",
                    tuple(
                        int(sweep_axes[axis_index].count)
                        for axis_index in duration_axis_indices
                    ),
                )
            )
            group_key = (duration_axis_indices, page)
            group_info = table_groups.setdefault(
                group_key,
                {
                    # Keep axis_index for existing diagnostics that inspect
                    # single-axis RAMP coefficient groups.
                    "axis_index": duration_axis_indices[0],
                    "axis_indices": duration_axis_indices,
                    "axis_shape": duration_shape,
                    "page": page,
                    "columns": [],
                },
            )
            if (
                tuple(group_info["axis_indices"]) != duration_axis_indices
                or tuple(group_info["axis_shape"]) != duration_shape
            ):
                raise RuntimeError("incompatible RAMP-duration table fields")
            group_info["columns"].append({
                "kind": "base",
                "field": field,
                "values": tuple(field["duration_table_bases"]),
            })
            for axis_index, slots in field["duration_delta_slots"].items():
                deltas = tuple(
                    int(value)
                    for value in field[
                        "duration_table_axis_deltas"
                    ][axis_index]
                )
                if axis_index < duration_axis_indices[0] and any(deltas):
                    raise ValueError(
                        "a RAMP-rate coefficient table depends on an outer "
                        "RAMP duration axis; use independent RAMP segments "
                        "without cross-duration coefficient coupling"
                    )
                group_info["columns"].append({
                    "kind": "delta",
                    "field": field,
                    "axis_index": int(axis_index),
                    "slot": int(slots["advance"]),
                    "values": deltas,
                })
                group_info["columns"].append({
                    "kind": "reset_delta",
                    "field": field,
                    "axis_index": int(axis_index),
                    "slot": int(slots["reset"]),
                    "values": tuple(
                        -value * (int(sweep_axes[axis_index].count) - 1)
                        for value in deltas
                    ),
                })

        table_page_resources = {}
        for page in sorted({key[1] for key in table_groups}):
            available = [
                register
                for register in range(1, 32)
                if register not in occupied[page]
            ]
            if not available:
                candidate = next(
                    (
                        field
                        # Any stored sweep value can use its destination
                        # register as scratch. DC-only table fields are
                        # already in DMEM, so restricting this to table
                        # fields can fail on a crowded dual-AWG/RF page.
                        for field in fields
                        if int(field["page"]) == page
                        and field.get("storage") == "register"
                    ),
                    None,
                )
                if candidate is None:
                    raise RuntimeError(
                        f"register page {page} has no RAMP-rate DMEM pointer register"
                    )
                pointer_register = int(candidate["state_register"])
                occupied[page].remove(pointer_register)
                assign_dmem(candidate, int(candidate["command_register"]))
                candidate.pop("state_register", None)
                available = [pointer_register]
            pointer_register = int(available[0])
            occupied[page].add(pointer_register)
            scratch_candidates = [
                int(register)
                for (gen_ch, name), (reg_page, register) in self._gen_regmap.items()
                if int(reg_page) == page and name == "reserved_start"
            ]
            if not scratch_candidates:
                raise RuntimeError(
                    f"register page {page} has no AWG scratch register for "
                    "RAMP-rate coefficient loading"
                )
            table_page_resources[page] = {
                "pointer_register": pointer_register,
                "scratch_register": scratch_candidates[0],
            }

        for group_key in sorted(table_groups):
            if next_dmem_addr <= 1:
                raise RuntimeError(
                    "tProcessor DMEM has no room for RAMP-rate table pointers"
                )
            group_info = table_groups[group_key]
            group_info["pointer_state_addr"] = int(next_dmem_addr)
            next_dmem_addr -= 1
            group_info.update(table_page_resources[int(group_info["page"])])

        runtime_table_base = 16
        runtime_table_words = []
        table_cursor = runtime_table_base
        for group_key in sorted(table_groups):
            group_info = table_groups[group_key]
            columns = group_info["columns"]
            duration_count = int(
                np.prod(
                    tuple(int(value) for value in group_info["axis_shape"]),
                    dtype=np.int64,
                )
            )
            group_info["base_address"] = table_cursor
            group_info["row_width"] = len(columns)
            axis_row_strides = {}
            for position, axis_index in enumerate(group_info["axis_indices"]):
                axis_row_strides[int(axis_index)] = int(
                    np.prod(
                        tuple(
                            int(value)
                            for value in group_info["axis_shape"][position + 1:]
                        ),
                        dtype=np.int64,
                    )
                )
            group_info["axis_row_strides"] = axis_row_strides
            for duration_index in range(duration_count):
                runtime_table_words.extend(
                    int(column["values"][duration_index])
                    for column in columns
                )
            table_cursor += duration_count * len(columns)
        ramp_runtime_table_word_count = len(runtime_table_words)
        for table in rf_point_tables:
            table["base_address"] = int(table_cursor)
            axis_shape = tuple(int(value) for value in table["axis_shape"])
            axis_strides = {}
            for position, axis_index in enumerate(table["axis_indices"]):
                axis_strides[int(axis_index)] = int(
                    np.prod(
                        axis_shape[position + 1:],
                        dtype=np.int64,
                    )
                )
            table["axis_strides"] = axis_strides
            runtime_table_words.extend(int(value) for value in table["values"])
            table_cursor += len(table["values"])
        if runtime_table_words and table_cursor - 1 > next_dmem_addr:
            raise RuntimeError(
                "runtime sweep tables do not fit tProcessor DMEM: "
                f"low table ends at {table_cursor - 1}, high state uses down "
                f"through {next_dmem_addr + 1}"
            )

        axis_runtime = {}
        for axis_index, axis in enumerate(sweep_axes):
            if axis.count <= 1:
                continue
            allocated = None
            for page in range(8):
                available = [
                    register
                    for register in range(1, 32)
                    if register not in occupied[page]
                ]
                if available:
                    allocated = (page, available[0])
                    occupied[page].add(available[0])
                    break
            if allocated is None:
                raise RuntimeError(
                    f"no tProcessor register is available for sweep axis {axis_index}"
                )
            axis_runtime[axis_index] = {
                "counter_page": allocated[0],
                "counter_register": allocated[1],
                "count": int(axis.count),
            }

        self._sweep_models = models
        self._event_timing_models = event_timing_models
        self._sweep_fields = tuple(fields)
        self._sweep_field_by_key = {field["key"]: field for field in fields}
        self._bias_t_fields = tuple(
            field
            for field in fields
            if str(field.get("register_name", "")).startswith("bias_t_")
        )
        self._sweep_axis_runtime = axis_runtime
        self._ramp_duration_axis_indices_runtime = tuple(sorted({
            index for group in table_groups.values() for index in group["axis_indices"]
        }))
        self._ramp_duration_table_groups = table_groups
        self._ramp_duration_table_page_resources = table_page_resources
        self._rf_point_tables = tuple(rf_point_tables)
        self._rf_point_tables_by_event = {
            int(rf_index): tuple(
                table
                for table in rf_point_tables
                if int(rf_index) in tuple(table["event_indices"])
            )
            for rf_index, _rf in enumerate(self.rf_pulse_configs)
        }
        self._runtime_dmem_base = (
            runtime_table_base if runtime_table_words else None
        )
        self._runtime_dmem_words = tuple(runtime_table_words)
        self._runtime_dmem_last_address = (
            table_cursor - 1 if runtime_table_words else None
        )
        self._ramp_runtime_table_word_count = int(
            ramp_runtime_table_word_count
        )
        self._rf_runtime_table_word_count = int(
            len(runtime_table_words) - ramp_runtime_table_word_count
        )
        self._sweep_max_target_error = int(max_target_error)
        self._sweep_max_step_error = int(max_step_error)
        self._sweep_max_duration_error = int(max_duration_error)
        self._validate_dynamic_event_order()

    def _segment_index(self, name: str, *, require_set: bool = False) -> int:
        names = [segment.name for segment in self.sequence.segments]
        if name not in names:
            raise KeyError(f"unknown sequence segment {name!r}")
        index = names.index(name)
        if require_set and self.sequence.segments[index].kind != "set":
            raise ValueError(f"segment {name!r} must be a SET segment")
        return index

    def _rf_duration_axis(
        self,
        rf_or_gen_ch,
        parameter_name: Optional[str] = None,
    ) -> Optional[RfDurationSweep]:
        if isinstance(rf_or_gen_ch, RfPulseConfig):
            gen_ch = int(rf_or_gen_ch.gen_ch)
            parameter_name = str(rf_or_gen_ch.duration_parameter)
        else:
            gen_ch = int(rf_or_gen_ch)
            parameter_name = "" if parameter_name is None else str(parameter_name)
        matches = [
            axis
            for axis in self.sequence.sweep_axes
            if isinstance(axis, RfDurationSweep)
            and axis.gen_ch == gen_ch
            and str(axis.parameter_name) == parameter_name
        ]
        if len(matches) > 1:
            raise RuntimeError(
                f"RF generator {gen_ch} duration parameter "
                f"{parameter_name!r} has more than one sweep axis"
            )
        return matches[0] if matches else None

    def _rf_frequency_axis(
        self,
        rf_or_gen_ch,
        parameter_name: Optional[str] = None,
    ) -> Optional[RfFrequencySweep]:
        if isinstance(rf_or_gen_ch, RfPulseConfig):
            gen_ch = int(rf_or_gen_ch.gen_ch)
            parameter_name = str(rf_or_gen_ch.frequency_parameter)
        else:
            gen_ch = int(rf_or_gen_ch)
            parameter_name = "" if parameter_name is None else str(parameter_name)
        matches = [
            axis
            for axis in self.sequence.sweep_axes
            if isinstance(axis, RfFrequencySweep)
            and axis.gen_ch == gen_ch
            and str(axis.parameter_name) == parameter_name
        ]
        if len(matches) > 1:
            raise RuntimeError(
                f"RF generator {gen_ch} frequency parameter "
                f"{parameter_name!r} has more than one sweep axis"
            )
        return matches[0] if matches else None

    def _rf_power_axis(self, gen_ch: int) -> Optional[RfPowerSweep]:
        matches = [
            axis
            for axis in self.sequence.sweep_axes
            if isinstance(axis, RfPowerSweep)
            and axis.gen_ch == int(gen_ch)
        ]
        if len(matches) > 1:
            raise RuntimeError(
                f"RF generator {gen_ch} has more than one power sweep axis"
            )
        return matches[0] if matches else None

    def _validate_rf_sweeps(self) -> None:
        configs_by_gen = {}
        for rf in self.rf_pulse_configs:
            configs_by_gen.setdefault(int(rf.gen_ch), []).append(rf)
        for axis in self.sequence.sweep_axes:
            if not isinstance(
                axis,
                (RfDurationSweep, RfFrequencySweep, RfPowerSweep),
            ):
                continue
            configs = configs_by_gen.get(int(axis.gen_ch), [])
            if isinstance(axis, RfFrequencySweep):
                configs = [
                    rf for rf in configs
                    if str(rf.frequency_parameter) == str(axis.parameter_name)
                ]
            if isinstance(axis, RfDurationSweep):
                configs = [
                    rf for rf in configs
                    if str(rf.duration_parameter) == str(axis.parameter_name)
                ]
            if not configs:
                raise ValueError(
                    f"RF {axis.axis_kind} sweep for generator {axis.gen_ch} has no "
                    "matching RF pulse configuration"
                )
            if any(rf.at_segment != axis.segment_name for rf in configs):
                raise ValueError(
                    f"RF {axis.axis_kind} sweep for generator {axis.gen_ch} targets "
                    f"{axis.segment_name!r}, but a matching RF pulse targets "
                    "another segment"
                )
        for rf in self.rf_pulse_configs:
            frequency_axis = self._rf_frequency_axis(rf)
            power_axis = self._rf_power_axis(rf.gen_ch)
            expected_shape = (
                1 if frequency_axis is None else int(frequency_axis.count),
                1 if power_axis is None else int(power_axis.count),
            )
            if power_axis is not None and not rf.sweep_gain_codes:
                raise ValueError(
                    f"RF power sweep for generator {rf.gen_ch} requires a "
                    "calibrated gain-code table"
                )
            if rf.sweep_gain_codes and tuple(rf.sweep_gain_shape) != expected_shape:
                raise ValueError(
                    f"RF gain-code table for generator {rf.gen_ch} has shape "
                    f"{tuple(rf.sweep_gain_shape)}, expected {expected_shape}"
                )

    def _rf_duration_fabric_cycles(
        self,
        rf: RfPulseConfig,
        duration_us: float,
    ) -> int:
        return cycles_from_us(
            duration_us,
            float(self.soccfg["gens"][rf.gen_ch]["f_fabric"]),
        )

    def _rf_frequency_word(self, rf: RfPulseConfig, freq_mhz: float) -> int:
        gen_cfg = self.soccfg["gens"][rf.gen_ch]
        ro_ch = (
            self.ddr_readout_config.ro_ch
            if self.ddr_readout_config is not None
            else None
        )
        try:
            return int(
                self.freq2reg(
                    float(freq_mhz),
                    gen_ch=rf.gen_ch,
                    ro_ch=ro_ch,
                )
            )
        except KeyError as exc:
            if exc.args != ("refclk_freq",):
                raise
            b_dds = int(gen_cfg["b_dds"])
            value = int(
                round(
                    float(freq_mhz)
                    * (1 << b_dds)
                    / float(gen_cfg["f_dds"])
                )
            )
            return value % (1 << b_dds)

    def _configure_rf_pulse(self, rf_index: int, rf: RfPulseConfig):
        if rf.gen_ch in self.awg_channels:
            raise ValueError("RF generator channel must be separate from AWG tuning channels")
        if rf.gen_ch >= len(self.soccfg["gens"]):
            raise IndexError("RF generator channel is out of range")
        gen_cfg = self.soccfg["gens"][rf.gen_ch]
        if gen_cfg.get("type") == "axis_awg_tuning_v1" or gen_cfg.get("gen_type") == "awg_tuning":
            raise ValueError("rf_pulse requires a normal QICK RF signal generator")
        self._segment_index(rf.at_segment, require_set=True)

        if rf.gen_ch not in self._declared_rf_channels:
            self.declare_gen(ch=rf.gen_ch, nqz=rf.nqz)
            self._declared_rf_channels.add(rf.gen_ch)
        frequency_axis = self._rf_frequency_axis(rf)
        initial_frequency_mhz = (
            float(rf.freq_mhz)
            if frequency_axis is None
            else float(frequency_axis.points[0])
        )
        freq_word = self._rf_frequency_word(rf, initial_frequency_mhz)
        phase_word = self.deg2reg(rf.phase_degrees, gen_ch=rf.gen_ch)
        duration_axis = self._rf_duration_axis(rf)
        power_axis = self._rf_power_axis(rf.gen_ch)
        initial_gain = (
            int(rf.gain)
            if not rf.sweep_gain_codes
            else int(rf.sweep_gain_codes[0])
        )
        base_length_cycles = (
            rf.length_cycles
            if duration_axis is None
            else self._rf_duration_fabric_cycles(rf, duration_axis.start)
        )
        # Choose one mode for the entire duration axis, including descending
        # sweeps. A count-one sweep executes only its start coordinate.
        maximum_length_cycles = base_length_cycles
        if duration_axis is not None and duration_axis.count > 1:
            maximum_length_cycles = max(
                base_length_cycles,
                self._rf_duration_fabric_cycles(rf, duration_axis.stop),
            )
        periodic = maximum_length_cycles > MAX_RF_ONESHOT_CYCLES
        self._rf_runtime[int(rf_index)] = {
            "freq": int(freq_word),
            "phase": int(phase_word),
            "periodic": bool(periodic),
            "duration_axis": duration_axis,
            "frequency_axis": frequency_axis,
            "power_axis": power_axis,
            "gain": int(initial_gain),
            "base_length_cycles": int(base_length_cycles),
        }
        self.set_pulse_registers(
            ch=rf.gen_ch,
            style="const",
            freq=freq_word,
            phase=phase_word,
            gain=initial_gain,
            length=(
                RF_PERIODIC_WORD_CYCLES if periodic else base_length_cycles
            ),
            phrst=0,
            stdysel="last" if periodic else rf.stdysel,
            mode="periodic" if periodic else "oneshot",
        )

    def _emit_rf_start(
        self,
        rf_index: int,
        rf: RfPulseConfig,
        tproc_time: int,
    ) -> None:
        runtime = self._rf_runtime[int(rf_index)]
        # Rebuild the command registers for every event. Composite pulses on
        # one generator can have independent gain/phase/duration while sharing
        # a named frequency table.
        self.set_pulse_registers(
            ch=rf.gen_ch,
            style="const",
            freq=runtime["freq"],
            phase=runtime["phase"],
            gain=runtime["gain"],
            length=(
                RF_PERIODIC_WORD_CYCLES
                if runtime["periodic"]
                else runtime["base_length_cycles"]
            ),
            phrst=0,
            stdysel="last" if runtime["periodic"] else rf.stdysel,
            mode="periodic" if runtime["periodic"] else "oneshot",
        )
        for table in self._rf_point_tables_by_event.get(int(rf_index), ()):
            self.memr(
                int(table["page"]),
                int(table["command_register"]),
                int(table["pointer_register"]),
                f"load swept {table['register_name']} from DMEM",
            )
        self._emit_rf_pulse_at(
            rf.gen_ch,
            tproc_time,
            ("event_time", "rf_start", rf_index),
            "RF duration-sweep start",
        )

    def _emit_rf_stop(
        self,
        rf_index: int,
        rf: RfPulseConfig,
        tproc_time: int,
    ) -> None:
        runtime = self._rf_runtime[int(rf_index)]
        self.set_pulse_registers(
            ch=rf.gen_ch,
            style="const",
            freq=runtime["freq"],
            phase=runtime["phase"],
            gain=0,
            length=RF_STOP_WORD_CYCLES,
            phrst=0,
            stdysel="zero",
            mode="oneshot",
        )
        self._emit_rf_pulse_at(
            rf.gen_ch,
            tproc_time,
            ("event_time", "rf_stop", rf_index),
            "RF duration-sweep stop",
        )

    def _emit_rf_pulse_at(
        self,
        gen_ch: int,
        tproc_time: int,
        field_key: tuple,
        comment: str,
    ) -> None:
        page, time_register = self._gen_regmap[(gen_ch, "t")]
        self._write_swept_or_static_register(
            field_key,
            int(page),
            int(time_register),
            int(tproc_time),
            comment,
        )
        next_pulse = self._gen_mgrs[gen_ch].next_pulse
        if next_pulse is None:
            raise RuntimeError(f"RF generator {gen_ch} has no configured pulse")
        for registers in next_pulse["regs"]:
            self.set(
                int(self.soccfg["gens"][gen_ch]["tproc_ch"]),
                int(page),
                *registers,
                int(time_register),
                comment,
            )

    def _configure_ddr_readout(self):
        ddr = self.ddr_readout_config
        self._segment_index(ddr.at_segment, require_set=True)
        profile = resolve_fir_ddr_profile(
            self.soccfg,
            context="AWG/experiment FIR DDR readout",
        )
        ddr_cfg = profile.config
        if ddr.ro_ch >= len(self.soccfg["readouts"]):
            raise IndexError("DDR readout channel is out of range")

        ro_cfg = self.soccfg["readouts"][ddr.ro_ch]
        monitor_length = min(
            ddr.samples_per_trigger,
            int(ro_cfg.get("buf_maxlen", ddr.samples_per_trigger)),
        )
        self.declare_readout(ch=ddr.ro_ch, length=max(1, monitor_length))
        gen_ch = self.rf_pulse_configs[0].gen_ch if self.rf_pulse_configs else None
        try:
            freq_word = self.freq2reg_adc(
                ddr.readout_freq_mhz,
                ro_ch=ddr.ro_ch,
                gen_ch=gen_ch,
            )
        except KeyError as exc:
            if exc.args != ("refclk_freq",):
                raise
            b_dds = int(ro_cfg["b_dds"])
            freq_word = int(
                round(float(ddr.readout_freq_mhz) * (1 << b_dds) / float(ro_cfg["f_dds"]))
            )
            freq_word %= 1 << b_dds
        self.set_readout_registers(
            ch=ddr.ro_ch,
            freq=freq_word,
            length=ddr.readout_period_cycles,
            mode="periodic",
            phrst=0,
        )
        trigger_delay_samples = (
            profile.trigger_delay_samples
            if ddr.fpga_trigger_delay_samples is None
            else int(ddr.fpga_trigger_delay_samples)
        )
        if not profile.uses_fpga_trigger_delay:
            if trigger_delay_samples:
                raise ValueError(
                    "fpga_trigger_delay_samples requires 50 kSPS DDR V2 firmware"
                )
            trigger_delay_samples = 0
        trigger_delay_input_cycles = profile.trigger_delay_input_cycles_for(
            trigger_delay_samples
        )
        trigger_delay_arm_kwargs = profile.trigger_delay_arm_kwargs(
            trigger_delay_samples
        )
        self._fir_cfg = {
            "iq_scale_log2": profile.iq_scale_log2,
            "iq_component_bits": profile.iq_component_bits,
            "rate_profile": profile.name,
            "decimation": profile.decimation,
            "group_delay_input_samples": int(ceil(profile.group_delay_input_samples)),
            "input_fs_mhz": profile.input_rate_mhz,
            "output_fs_mhz": profile.sample_rate_msps,
            "output_sample_rate_hz": profile.sample_rate_hz,
            "software_warmup_compensation": profile.software_warmup_compensation,
            "software_trigger_delay_output_samples": (
                profile.software_trigger_delay_output_samples
            ),
            "software_trigger_delay_input_samples": (
                profile.software_trigger_delay_input_samples
            ),
            "software_aligned_trigger_input_samples": (
                profile.software_aligned_trigger_input_samples
            ),
            "software_trigger_delay_us": profile.software_trigger_delay_us,
            "uses_fpga_trigger_delay": profile.uses_fpga_trigger_delay,
            "trigger_delay_samples": trigger_delay_samples,
            "trigger_delay_units": profile.trigger_delay_units,
            "trigger_delay_input_cycles": trigger_delay_input_cycles,
            "trigger_delay_arm_kwargs": trigger_delay_arm_kwargs,
            "profile_default_trigger_delay_samples": profile.trigger_delay_samples,
        }

    def _shift_timing(self, delta: int):
        if delta <= 0:
            return
        self.timing["command_times"] = {
            key: value + delta for key, value in self.timing["command_times"].items()
        }
        self.timing["segment_starts"] = tuple(
            value + delta for value in self.timing["segment_starts"]
        )
        self.timing["segment_ends"] = tuple(
            value + delta for value in self.timing["segment_ends"]
        )
        self.timing["point_end"] += delta

    def _build_aux_timing(self):
        f_time = self.tproc_mhz

        if self.ddr_readout_config is not None:
            ddr = self.ddr_readout_config
            segment_index = self._segment_index(ddr.at_segment, require_set=True)
            trigger_time = (
                self.timing["segment_starts"][segment_index]
                + ddr.trigger_delay_tproc_cycles
            )
            input_fs = self._fir_cfg["input_fs_mhz"]
            group_delay = self._fir_cfg["group_delay_input_samples"]
            decimation = self._fir_cfg["decimation"]
            if self._fir_cfg["software_warmup_compensation"]:
                warmup_cycles = int(ceil(group_delay * f_time / input_fs))
                readout_start = trigger_time - warmup_cycles
                if readout_start < 0:
                    shift = -readout_start
                    self._shift_timing(shift)
                    trigger_time += shift
                    readout_start += shift

                software_trigger_delay_cycles = int(ceil(
                    self._fir_cfg["software_trigger_delay_input_samples"]
                    * f_time
                    / input_fs
                ))
                trigger_time += software_trigger_delay_cycles

                feed_input_samples = (
                    ddr.samples_per_trigger * decimation
                    + group_delay
                    + self._fir_cfg["software_trigger_delay_input_samples"]
                    + ddr.margin_input_samples
                )
                feed_tproc_cycles = int(
                    ceil(feed_input_samples * f_time / input_fs)
                )
                capture_end = readout_start + feed_tproc_cycles
            else:
                # The 50 kSPS HWH keeps filtering continuously and delays DDR
                # storage in axis_buffer_ddr_sample_v2. Do not move any AWG,
                # readout, or trigger event by the FIR group delay in tProcessor
                # code. The FIR group delay is pipeline latency, not per-point
                # occupancy: waiting for it here would insert the same delay
                # between every hardware-sweep point and defeat queued triggers.
                warmup_cycles = 0
                software_trigger_delay_cycles = 0
                readout_start = 0
                capture_input_samples = (
                    ddr.samples_per_trigger * decimation
                    + ddr.margin_input_samples
                )
                queued_input_samples = (
                    self._fir_cfg["trigger_delay_input_cycles"]
                    + capture_input_samples
                )
                post_trigger_cycles = int(
                    ceil(capture_input_samples * f_time / input_fs)
                )
                capture_end = trigger_time + post_trigger_cycles
                feed_input_samples = group_delay + queued_input_samples
            self.aux_timing.update({
                "ddr_readout_start": int(readout_start),
                "ddr_trigger_time": int(trigger_time),
                "ddr_capture_end": int(capture_end),
                "fir_warmup_tproc_cycles": int(warmup_cycles),
                "fir_software_trigger_delay_tproc_cycles": int(
                    software_trigger_delay_cycles
                ),
                "fir_software_trigger_delay_output_samples": self._fir_cfg[
                    "software_trigger_delay_output_samples"
                ],
                "fir_software_trigger_delay_input_samples": self._fir_cfg[
                    "software_trigger_delay_input_samples"
                ],
                "fir_feed_input_samples": int(feed_input_samples),
                "fir_rate_profile": self._fir_cfg["rate_profile"],
                "fir_output_sample_rate_hz": self._fir_cfg["output_sample_rate_hz"],
                "fir_software_warmup_compensation": self._fir_cfg[
                    "software_warmup_compensation"
                ],
                "fir_fpga_trigger_delay_samples": self._fir_cfg[
                    "trigger_delay_samples"
                ],
                "fir_fpga_trigger_delay_units": self._fir_cfg[
                    "trigger_delay_units"
                ],
            })
            self.timing["point_end"] = max(self.timing["point_end"], capture_end)

        rf_timings = []
        occupied_by_port = {}
        for timing_key, command_time in self.timing["command_times"].items():
            output_index = int(timing_key[1])
            awg_ch = self.awg_channels[output_index]
            awg_port = int(self.soccfg["gens"][awg_ch]["tproc_ch"])
            occupied_by_port.setdefault(awg_port, set()).add(int(command_time))
        if self.ddr_readout_config is not None:
            ro_cfg = self.soccfg["readouts"][self.ddr_readout_config.ro_ch]
            occupied_by_port.setdefault(int(ro_cfg["tproc_ctrl"]), set()).add(
                int(self.aux_timing["ddr_readout_start"])
            )

        for rf_index, rf in enumerate(self.rf_pulse_configs):
            segment_index = self._segment_index(rf.at_segment, require_set=True)
            requested_start = (
                self.timing["segment_starts"][segment_index] + rf.delay_tproc_cycles
            )
            rf_port = int(self.soccfg["gens"][rf.gen_ch]["tproc_ch"])
            occupied = occupied_by_port.setdefault(rf_port, set())
            rf_start = int(requested_start)
            while rf_start in occupied:
                rf_start += self.command_spacing_tproc_cycles
            occupied.add(rf_start)
            requested_end = rf_start + self._fabric_to_tproc(
                rf.gen_ch,
                int(self._rf_runtime[rf_index]["base_length_cycles"]),
            )
            periodic = bool(self._rf_runtime[rf_index]["periodic"])
            rf_end = int(requested_end)
            if periodic:
                while rf_end in occupied:
                    rf_end += self.command_spacing_tproc_cycles
                occupied.add(rf_end)
            if rf.require_within_segment and rf_end > self.timing["segment_ends"][segment_index]:
                raise ValueError(
                    f"RF pulse ends at t={rf_end}, after SET segment {rf.at_segment!r} "
                    f"ends at t={self.timing['segment_ends'][segment_index]}"
                )
            timing = {
                "index": rf_index,
                "gen_ch": rf.gen_ch,
                "requested_start": int(requested_start),
                "start": int(rf_start),
                "requested_end": int(requested_end),
                "end": int(rf_end),
                "mode": "periodic_timed_stop" if periodic else "oneshot",
                "command_skew_tproc_cycles": int(rf_start - requested_start),
                "stop_skew_tproc_cycles": int(rf_end - requested_end),
            }
            rf_timings.append(timing)
            self.aux_timing.update({
                f"rf_{rf_index}_requested_start": timing["requested_start"],
                f"rf_{rf_index}_start": timing["start"],
                f"rf_{rf_index}_end": timing["end"],
                f"rf_{rf_index}_mode": timing["mode"],
                f"rf_{rf_index}_command_skew_tproc_cycles": (
                    timing["command_skew_tproc_cycles"]
                ),
                f"rf_{rf_index}_stop_skew_tproc_cycles": (
                    timing["stop_skew_tproc_cycles"]
                ),
            })
            self.timing["point_end"] = max(self.timing["point_end"], rf_end)
        self.aux_timing["rf_pulses"] = tuple(rf_timings)
        if len(rf_timings) == 1:
            timing = rf_timings[0]
            self.aux_timing.update({
                "rf_requested_start": timing["requested_start"],
                "rf_start": timing["start"],
                "rf_end": timing["end"],
                "rf_mode": timing["mode"],
                "rf_command_skew_tproc_cycles": timing["command_skew_tproc_cycles"],
                "rf_stop_skew_tproc_cycles": timing["stop_skew_tproc_cycles"],
            })

    def _rf_axis_step_tproc(self, axis: RfDurationSweep) -> int:
        if axis.count <= 1:
            return 0
        start = cycles_from_us(axis.start, self.tproc_mhz)
        stop = cycles_from_us(axis.stop, self.tproc_mhz)
        return _round_div_nearest(stop - start, axis.count - 1)

    def _ramp_axis_step_tproc(self, axis: RampDurationSweep) -> int:
        """Return the exact per-point RAMP duration increment in tProc cycles."""
        if axis.count <= 1:
            return 0
        converted = tuple(
            cycles_from_us(duration_us, self.tproc_mhz)
            for duration_us in axis.points
        )
        step = converted[1] - converted[0]
        expected = tuple(converted[0] + index * step for index in range(axis.count))
        if converted != expected:
            raise ValueError(
                "RAMP duration points do not form an arithmetic progression "
                "at the configured tProcessor clock; use compatible AWG and "
                "tProcessor clocks or adjust the duration range"
            )
        return int(step)

    def _hold_axis_step_tproc(self, axis: HoldDurationSweep) -> int:
        """Return the exact per-point SET hold increment in tProc cycles."""
        if axis.count <= 1:
            return 0
        converted = tuple(
            cycles_from_us(duration_us, self.tproc_mhz)
            for duration_us in axis.points
        )
        step = converted[1] - converted[0]
        expected = tuple(
            converted[0] + index * step for index in range(axis.count)
        )
        if converted != expected:
            raise ValueError(
                "SET hold duration points do not form an arithmetic "
                "progression at the configured tProcessor clock; use "
                "compatible AWG and tProcessor clocks or adjust the range"
            )
        return int(step)

    def _extension_axis_deltas(
        self,
        segment_index: int,
        *,
        include_current: bool,
    ) -> Tuple[int, ...]:
        deltas = []
        for axis in self.sequence.sweep_axes:
            delta = 0
            if (
                isinstance(axis, RfDurationSweep)
                and axis.segment_length_mode == "extend_by_rf_duration"
            ):
                anchor_index = self._segment_index(axis.segment_name)
                if anchor_index < segment_index or (
                    include_current and anchor_index == segment_index
                ):
                    delta = (
                        self._rf_axis_step_tproc(axis)
                        * self.sequence.rf_duration_extension_multiplier(axis)
                    )
            elif isinstance(axis, RampDurationSweep):
                ramp_index = self._segment_index(axis.segment_name)
                if ramp_index < segment_index or (
                    include_current and ramp_index == segment_index
                ):
                    delta = self._ramp_axis_step_tproc(axis)
            elif isinstance(axis, HoldDurationSweep):
                hold_index = self._segment_index(
                    axis.segment_name,
                    require_set=True,
                )
                if hold_index < segment_index or (
                    include_current and hold_index == segment_index
                ):
                    delta = self._hold_axis_step_tproc(axis)
            deltas.append(int(delta))
        return tuple(deltas)

    @staticmethod
    def _model_maximum(model: Mapping, axes: Sequence) -> int:
        value = int(model["base"])
        for delta, axis in zip(model["axis_deltas"], axes):
            value += max(0, int(delta) * (int(axis.count) - 1))
        return value

    def _build_event_timing_models(self) -> Tuple[dict, ...]:
        """Build linear timestamp states for variable-length sweep axes."""
        axes = self.sequence.sweep_axes
        if not any(
            isinstance(
                axis,
                (RfDurationSweep, RampDurationSweep, HoldDurationSweep),
            )
            for axis in axes
        ):
            self._dynamic_point_end = int(self.timing["point_end"])
            return ()

        extension_indices = {
            self._segment_index(axis.segment_name)
            for axis in axes
            if (
                isinstance(axis, RfDurationSweep)
                and axis.segment_length_mode == "extend_by_rf_duration"
                and axis.count > 1
                and (
                    self._rf_axis_step_tproc(axis)
                    * self.sequence.rf_duration_extension_multiplier(axis)
                ) != 0
            )
        }
        has_awg_duration = any(
            isinstance(axis, (RampDurationSweep, HoldDurationSweep))
            for axis in axes
        )
        if self.ddr_readout_config is not None and not has_awg_duration:
            trigger_index = self._segment_index(
                self.ddr_readout_config.at_segment
            )
            if any(index < trigger_index for index in extension_indices):
                raise ValueError(
                    "an RF duration sweep that extends an earlier AWG segment "
                    "would require a dynamic DDR trigger timestamp; anchor the "
                    "DDR readout at or before the extended segment"
                )
        if self.readout_config is not None and extension_indices:
            if self.readout_config.at_segment is None:
                raise ValueError(
                    "readout at the variable sequence end is not supported with "
                    "RF segment-extension sweep mode"
                )
            measure_index = self._segment_index(
                self.readout_config.at_segment
            )
            if any(index <= measure_index for index in extension_indices):
                raise ValueError(
                    "the selected readout timestamp depends on an RF-extended "
                    "segment; use DDR readout anchored at or before that segment"
                )

        models = []
        first_point = self.compiled_points[0]
        for commands in first_point.segment_commands:
            for command in commands:
                deltas = self._extension_axis_deltas(
                    command.segment_index,
                    include_current=False,
                )
                if not any(deltas):
                    continue
                gen_ch = int(command.gen_ch)
                page, time_register = self._gen_regmap[(gen_ch, "t")]
                models.append({
                    "key": (
                        "event_time",
                        "awg",
                        *self._command_key(command),
                    ),
                    "register_name": "event_time",
                    "base": int(
                        self.timing["command_times"][self._timing_key(command)]
                    ),
                    "axis_deltas": deltas,
                    "page": int(page),
                    "command_register": int(time_register),
                    "gen_ch": gen_ch,
                })

        if self.ddr_readout_config is not None:
            ddr = self.ddr_readout_config
            trigger_index = self._segment_index(ddr.at_segment)
            trigger_deltas = self._extension_axis_deltas(
                trigger_index,
                include_current=False,
            )
            if any(trigger_deltas):
                models.append({
                    "key": ("event_time", "ddr_trigger"),
                    "register_name": "event_time",
                    "base": int(self.aux_timing["ddr_trigger_time"]),
                    "axis_deltas": trigger_deltas,
                    "page": 0,
                    "command_register": None,
                    "allocate_command_register": True,
                    "allocate_output_register": True,
                })
                if int(self.aux_timing["ddr_readout_start"]) != 0:
                    page, time_register = self._ro_regmap[(ddr.ro_ch, "t")]
                    models.append({
                        "key": ("event_time", "ddr_readout"),
                        "register_name": "event_time",
                        "base": int(self.aux_timing["ddr_readout_start"]),
                        "axis_deltas": trigger_deltas,
                        "page": int(page),
                        "command_register": int(time_register),
                    })
                models.append({
                    "key": ("timing_only", "ddr_capture_end"),
                    "register_name": "timing_only",
                    "base": int(self.aux_timing["ddr_capture_end"]),
                    "axis_deltas": trigger_deltas,
                    "timing_only": True,
                })

        for rf_index, rf in enumerate(self.rf_pulse_configs):
            segment_index = self._segment_index(rf.at_segment)
            start_deltas = list(
                self._extension_axis_deltas(
                    segment_index,
                    include_current=False,
                )
            )
            end_deltas = list(start_deltas)
            for parameter_name in rf.preceding_duration_parameters:
                preceding_axis = self._rf_duration_axis(
                    rf.gen_ch,
                    parameter_name,
                )
                if preceding_axis is None:
                    continue
                axis_index = axes.index(preceding_axis)
                axis_step = self._rf_axis_step_tproc(preceding_axis)
                start_deltas[axis_index] += axis_step
                end_deltas[axis_index] += axis_step
            duration_axis = self._rf_duration_axis(rf)
            if duration_axis is not None:
                duration_axis_index = axes.index(duration_axis)
                end_deltas[duration_axis_index] += self._rf_axis_step_tproc(
                    duration_axis
                )
            if rf.require_within_segment:
                segment_end_deltas = self._extension_axis_deltas(
                    segment_index,
                    include_current=True,
                )
                maximum_excess = (
                    int(self.aux_timing[f"rf_{rf_index}_end"])
                    - int(self.timing["segment_ends"][segment_index])
                )
                for event_delta, segment_delta, axis in zip(
                    end_deltas,
                    segment_end_deltas,
                    axes,
                ):
                    maximum_excess += max(
                        0,
                        (int(event_delta) - int(segment_delta))
                        * (int(axis.count) - 1),
                    )
                if maximum_excess > 0:
                    raise ValueError(
                        f"RF pulse for generator {rf.gen_ch} exceeds SET "
                        f"segment {rf.at_segment!r} by up to "
                        f"{maximum_excess} tProcessor cycles"
                    )
            page, time_register = self._gen_regmap[(rf.gen_ch, "t")]
            for event_name, base_key, deltas in (
                ("rf_start", f"rf_{rf_index}_start", tuple(start_deltas)),
                ("rf_stop", f"rf_{rf_index}_end", tuple(end_deltas)),
            ):
                if not any(deltas):
                    continue
                models.append({
                    "key": ("event_time", event_name, rf_index),
                    "register_name": "event_time",
                    "base": int(self.aux_timing[base_key]),
                    "axis_deltas": deltas,
                    "page": int(page),
                    "command_register": int(time_register),
                    "gen_ch": int(rf.gen_ch),
                })

        if self.sequence.bias_t_compensation is not None or self.sequence.rc_compensation is not None:
            final_index = len(self.sequence.segments) - 1
            deltas = self._extension_axis_deltas(
                final_index,
                include_current=True,
            )
            if any(deltas):
                pulse_end = int(self.timing["segment_ends"][-1]) - self.awg_output_latency_tproc
                for output_index, gen_ch in enumerate(self.awg_channels):
                    page, time_register = self._gen_regmap[(gen_ch, "t")]
                    models.append({
                        "key": (
                            "event_time",
                            "bias_pre_zero",
                            output_index,
                        ),
                        "register_name": "event_time",
                        "base": pulse_end + int(self._channel_slots[gen_ch]),
                        "axis_deltas": deltas,
                        "page": int(page),
                        "command_register": int(time_register),
                        "gen_ch": int(gen_ch),
                    })

        sequence_end_model = {
            "base": int(self.timing["segment_ends"][-1]),
            "axis_deltas": self._extension_axis_deltas(
                len(self.sequence.segments) - 1,
                include_current=True,
            ),
        }
        dynamic_end = max(
            int(self.timing["point_end"]),
            self._model_maximum(sequence_end_model, axes),
            *(
                self._model_maximum(model, axes)
                for model in models
            ),
        )
        self._dynamic_point_end = int(dynamic_end)
        return tuple(models)

    def _validate_dynamic_event_order(self) -> None:
        """Ensure one tProcessor port never receives decreasing timestamps."""
        if not self._event_timing_models:
            return
        model_by_key = {
            model["key"]: model for model in self._event_timing_models
        }
        events = []
        order = 0

        def append(base, priority, gen_ch, field_key):
            nonlocal order
            events.append((
                int(base),
                int(priority),
                order,
                int(self.soccfg["gens"][gen_ch]["tproc_ch"]),
                field_key,
            ))
            order += 1

        for commands in self.compiled_points[0].segment_commands:
            for command in commands:
                append(
                    self.timing["command_times"][
                        self._timing_key(command)
                    ],
                    10,
                    command.gen_ch,
                    (
                        "event_time",
                        "awg",
                        *self._command_key(command),
                    ),
                )
        for rf_index, rf in enumerate(self.rf_pulse_configs):
            append(
                self.aux_timing[f"rf_{rf_index}_start"],
                10,
                rf.gen_ch,
                ("event_time", "rf_start", rf_index),
            )
            if self._rf_runtime[rf_index]["periodic"]:
                append(
                    self.aux_timing[f"rf_{rf_index}_end"],
                    15,
                    rf.gen_ch,
                    ("event_time", "rf_stop", rf_index),
                )
        events.sort(key=lambda event: event[:3])
        shape = tuple(axis.count for axis in self.sequence.sweep_axes)
        point_indices = (
            range(self.sequence.sweep_point_count)
            if self.compile_validation_mode == COMPILE_VALIDATION_FULL
            else self._compile_validation_point_indices
        )
        for point_index in point_indices:
            self._check_cancel()
            indices = (
                np.unravel_index(point_index, shape, order="C")
                if self.sequence.sweep_axes
                else ()
            )
            previous_by_port = {}
            for base, _priority, _order, port, field_key in events:
                model = model_by_key.get(field_key)
                timestamp = int(base)
                if model is not None:
                    timestamp = int(model["base"]) + sum(
                        int(index) * int(delta)
                        for index, delta in zip(
                            indices,
                            model["axis_deltas"],
                        )
                    )
                previous = previous_by_port.get(port)
                if previous is not None and timestamp < previous:
                    raise ValueError(
                        "RF duration sweep changes the order of commands on "
                        f"tProcessor output {port} at sweep point "
                        f"{point_index}; keep RF pulses inside their anchor "
                        "segment or use independent tProcessor outputs"
                    )
                previous_by_port[port] = timestamp

    def _build_channel_slots(self) -> Dict[int, int]:
        next_slot: Dict[int, int] = {}
        slots = {}
        for gen_ch in self.awg_channels:
            port = int(self.soccfg["gens"][gen_ch]["tproc_ch"])
            slot = next_slot.get(port, 0)
            slots[gen_ch] = slot * self.command_spacing_tproc_cycles
            next_slot[port] = slot + 1
        return slots

    def _fabric_to_tproc(self, gen_ch: int, fabric_cycles: int) -> int:
        f_time = self.tproc_mhz
        f_fabric = float(self.soccfg["gens"][gen_ch]["f_fabric"])
        if f_time <= 0 or f_fabric <= 0:
            raise ValueError("tProcessor and AWG fabric clocks must be positive")
        return max(1, int(ceil(fabric_cycles * f_time / f_fabric - 1e-12)))


    def _build_timing(self):
        first_point = self.compiled_points[0]
        command_times = {}
        segment_starts = []
        segment_ends = []
        # Command timestamps are point-relative. The startup lead is applied
        # once with synci before entering the hardware sweep loops, rather than
        # being inserted again before every SET at every point/repetition.
        time_now = 0
        for segment_index, segment in enumerate(self.sequence.segments):
            duration_cycles = self.sequence.segment_duration_cycles_at(
                0,
                segment_index,
            )
            segment_starts.append(time_now)
            active = {
                command.output_index: command
                for command in first_point.segment_commands[segment_index]
            }
            output_end_times = []
            for output_index, gen_ch in enumerate(self.awg_channels):
                command = active.get(output_index)
                if command is None:
                    output_end_times.append(
                        time_now + self._fabric_to_tproc(gen_ch, duration_cycles)
                    )
                    continue
                if segment.kind == "ramp":
                    gen_cfg = self.soccfg["gens"][gen_ch]
                    startup_cycles = int(
                        gen_cfg.get("ramp_startup_latency_cycles", 5)
                    )
                    startup_tproc = self._fabric_to_tproc(
                        gen_ch, startup_cycles
                    )
                    # Dispatch the RAMP before the logical segment boundary.
                    # Its pipeline then starts changing the DAC at the end of
                    # the preceding SET instead of extending that SET.
                    command_time = (
                        time_now
                        - startup_tproc
                        + self._channel_slots[gen_ch]
                    )
                    if command_time < 0:
                        raise ValueError(
                            "the first SET is too short to hide AWG RAMP startup latency"
                        )
                    occupancy = (
                        duration_cycles
                        + startup_cycles
                        + int(gen_cfg.get("ramp_guard_cycles", 1))
                    )
                else:
                    command_time = time_now + self._channel_slots[gen_ch]
                    occupancy = duration_cycles
                command_times[self._timing_key(command)] = command_time
                output_end_times.append(
                    command_time + self._fabric_to_tproc(gen_ch, occupancy)
                )
            time_now = max(output_end_times)
            segment_ends.append(time_now)

        return {
            "command_times": command_times,
            "segment_starts": tuple(segment_starts),
            "segment_ends": tuple(segment_ends),
            "point_end": int(time_now),
        }

    def _write_swept_or_static_register(
        self,
        field_key: tuple,
        page: int,
        destination_register: int,
        static_value: int,
        comment: str,
    ) -> None:
        field = self._sweep_field_by_key.get(field_key)
        if field is None:
            self.safe_regwi(
                page,
                destination_register,
                int(static_value),
                comment,
            )
        elif field.get("storage") == "dmem":
            self.memri(
                page,
                destination_register,
                int(field["dmem_addr"]),
                f"load swept {comment}",
            )
        else:
            self.mathi(
                page,
                destination_register,
                int(field["state_register"]),
                "+",
                0,
                f"copy swept {comment}",
            )

    def _emit_command(
        self,
        command: CompiledCommand,
        tproc_time: int,
        *,
        event_field_key: Optional[tuple] = None,
    ):
        """Emit one command, copying swept fields from tProcessor state regs."""
        gen_ch = command.gen_ch
        page = self._gen_regmap[(gen_ch, "target")][0]
        regs = []
        for register_name, word in zip(COMMAND_REGISTER_NAMES, command.words):
            reg_page, reg = self._gen_regmap[(gen_ch, register_name)]
            if reg_page != page:
                raise RuntimeError("AWG command registers must share one register page")
            field = self._sweep_field_by_key.get(
                (*self._command_key(command), register_name)
            )
            comment = f"{command.output_name}:{command.segment_name}:{register_name}"
            if field is None:
                self.safe_regwi(page, reg, int(word), comment)
            elif field.get("storage") == "dmem":
                self.memri(
                    page,
                    reg,
                    int(field["dmem_addr"]),
                    f"load spilled {comment}",
                )
                if register_name == "step":
                    self.bitwi(
                        page,
                        reg,
                        reg,
                        "&",
                        0xFFFFFF,
                        comment,
                    )
            elif register_name == "step":
                self.bitwi(
                    page,
                    reg,
                    int(field["state_register"]),
                    "&",
                    0xFFFFFF,
                    comment,
                )
            else:
                self.mathi(
                    page,
                    reg,
                    int(field["state_register"]),
                    "+",
                    0,
                    comment,
                )
            regs.append(reg)
        _, time_reg = self._gen_regmap[(gen_ch, "t")]
        if event_field_key is None:
            event_field_key = (
                "event_time",
                "awg",
                *self._command_key(command),
            )
        self._write_swept_or_static_register(
            event_field_key,
            int(page),
            int(time_reg),
            int(tproc_time),
            f"{command.segment_name} t",
        )
        self.set(
            int(self.soccfg["gens"][gen_ch]["tproc_ch"]),
            page,
            *regs,
            time_reg,
            f"{command.output_name}:{command.segment_name}",
        )

    def _emit_readout_at(
        self,
        ro_ch: int,
        tproc_time: int,
        field_key: tuple,
    ) -> None:
        """Queue a readout command at a static or swept timestamp."""
        page, time_register = self._ro_regmap[(int(ro_ch), "t")]
        self._write_swept_or_static_register(
            field_key,
            int(page),
            int(time_register),
            int(tproc_time),
            f"readout {ro_ch} t",
        )
        next_pulse = self._ro_mgrs[int(ro_ch)].next_pulse
        if next_pulse is None:
            raise RuntimeError(
                f"no pulse has been set up for readout channel {ro_ch}"
            )
        tproc_ch = int(self.soccfg["readouts"][int(ro_ch)]["tproc_ctrl"])
        for registers in next_pulse["regs"]:
            self.set(
                tproc_ch,
                int(page),
                *registers,
                int(time_register),
                f"readout {ro_ch}",
            )

    def _emit_ddr_trigger(
        self,
        ddr: DdrFirReadoutConfig,
        tproc_time: int,
    ) -> None:
        """Queue the DDR trigger, using a register timestamp when swept."""
        field_key = ("event_time", "ddr_trigger")
        field = self._sweep_field_by_key.get(field_key)
        if field is None:
            self.trigger(
                ddr4=True,
                adc_trig_offset=0,
                t=int(tproc_time),
                width=ddr.trigger_width_tproc_cycles,
            )
            return

        trigger_cfg = self.soccfg["ddr4_buf"]
        trigger_port = int(trigger_cfg["trigger_port"])
        page = int(field["page"])
        time_register = int(field["command_register"])
        output_register = int(field["output_register"])
        self._write_swept_or_static_register(
            field_key,
            page,
            time_register,
            int(tproc_time),
            "DDR trigger t",
        )
        trigger_word = 1 << int(trigger_cfg["trigger_bit"])
        self.safe_regwi(
            page,
            output_register,
            trigger_word,
            "assert DDR trigger",
        )
        # SET carries an explicit tProcessor output port, unlike SETB. The
        # remaining words stay zero because qick_vec2bit consumes the low bits
        # of the 160-bit axis_set_reg word.
        self.set(
            trigger_port,
            page,
            output_register,
            0,
            0,
            0,
            0,
            time_register,
            "register-timed DDR trigger high",
        )
        self.mathi(
            page,
            time_register,
            time_register,
            "+",
            int(ddr.trigger_width_tproc_cycles),
            "DDR trigger falling edge t",
        )
        self.set(
            trigger_port,
            page,
            0,
            0,
            0,
            0,
            0,
            time_register,
            "register-timed DDR trigger low",
        )

    def _static_set_command(
        self,
        output_index: int,
        target_code: int,
        segment_name: str,
    ) -> CompiledCommand:
        """Build an unswept SET command used by the compensation epilogue."""
        gen_ch = self.awg_channels[output_index]
        words = _pack_command_words(
            self.soccfg["gens"][gen_ch],
            int(target_code),
            0,
            0,
            OP_SET,
        )
        return CompiledCommand(
            point_index=0,
            segment_index=-1,
            segment_name=segment_name,
            output_index=output_index,
            output_name=self.sequence.output_names[output_index],
            gen_ch=gen_ch,
            kind="set",
            target_code=int(target_code),
            duration_samples=0,
            step=0,
            words=words,
        )

    def _emit_bias_t_compensation(self):
        """Schedule simultaneous SET starts and per-channel SET-zero stops."""
        config = self.sequence.bias_t_compensation
        if config is None:
            return
        if config.mode == "fixed_time":
            self._emit_bias_t_fixed_time()
            return

        max_duration_addr = int(self._bias_t_max_duration_dmem_addr)
        first_field = self._bias_t_fields[0]
        first_page = int(first_field["page"])
        first_target_register = self._gen_regmap[
            (int(first_field["gen_ch"]), "target")
        ][1]
        self.safe_regwi(
            first_page,
            first_target_register,
            0,
            "clear maximum Bias-T duration",
        )
        self.memwi(
            first_page,
            first_target_register,
            max_duration_addr,
            "store cleared maximum Bias-T duration",
        )

        for field in self._bias_t_fields:
            output_index = int(field["output_index"])
            output_name = self.sequence.output_names[output_index]
            gen_ch = int(field["gen_ch"])
            page = int(field["page"])
            work_register = int(field["work_register"])
            target_register = self._gen_regmap[(gen_ch, "target")][1]
            register_names = COMMAND_REGISTER_NAMES[1:]
            command_words = _pack_command_words(
                self.soccfg["gens"][gen_ch],
                0,
                0,
                0,
                OP_SET,
            )
            for register_name, word in zip(register_names, command_words[1:]):
                reg_page, register = self._gen_regmap[(gen_ch, register_name)]
                if int(reg_page) != page:
                    raise RuntimeError("AWG command registers must share one page")
                self.safe_regwi(
                    page,
                    register,
                    int(word),
                    f"{output_name} Bias-T {register_name}",
                )
            _, time_register = self._gen_regmap[(gen_ch, "t")]
            self.safe_regwi(
                page,
                time_register,
                self.bias_t_simultaneous_start_lead_cycles,
                f"{output_name} common Bias-T start offset",
            )
            self.memri(
                page,
                work_register,
                int(field["dmem_addr"]),
                f"load signed Bias-T duration for {output_name}",
            )

            negative_label = f"BIAS_T_NEGATIVE_AREA_{output_index}"
            ready_label = f"BIAS_T_DURATION_READY_{output_index}"
            max_ready_label = f"BIAS_T_MAX_READY_{output_index}"
            done_label = f"BIAS_T_DONE_{output_index}"
            self.condj(
                page,
                work_register,
                "==",
                0,
                done_label,
                f"skip zero-area Bias-T output {output_name}",
            )
            self.condj(
                page,
                work_register,
                "<",
                0,
                negative_label,
                f"select Bias-T polarity for {output_name}",
            )
            # Positive pulse area requires a negative compensation voltage.
            self.safe_regwi(
                page,
                target_register,
                int(field["negative_code"]),
                f"{output_name} negative Bias-T target",
            )
            self.condj(page, 0, "==", 0, ready_label, "Bias-T polarity ready")

            self.label(negative_label)
            self.math(
                page,
                work_register,
                0,
                "-",
                work_register,
                f"absolute Bias-T duration for {output_name}",
            )
            self.safe_regwi(
                page,
                target_register,
                int(field["positive_code"]),
                f"{output_name} positive Bias-T target",
            )

            self.label(ready_label)
            frac_bits = int(field["duration_frac_bits"])
            self.mathi(
                page,
                work_register,
                work_register,
                "+",
                1 << (frac_bits - 1),
                f"round Bias-T duration for {output_name}",
            )
            self.bitwi(
                page,
                work_register,
                work_register,
                ">>",
                frac_bits,
                f"Bias-T duration in tProcessor cycles for {output_name}",
            )
            self.condj(
                page,
                work_register,
                "==",
                0,
                done_label,
                f"skip sub-cycle Bias-T output {output_name}",
            )
            command_registers = [
                self._gen_regmap[(gen_ch, name)][1]
                for name in COMMAND_REGISTER_NAMES
            ]
            self.set(
                int(self.soccfg["gens"][gen_ch]["tproc_ch"]),
                page,
                *command_registers,
                time_register,
                f"start Bias-T compensation on {output_name}",
            )
            self.safe_regwi(
                page,
                target_register,
                0,
                f"{output_name} return to zero after Bias-T compensation",
            )
            self.mathi(
                page,
                time_register,
                work_register,
                "+",
                self.bias_t_simultaneous_start_lead_cycles,
                f"{output_name} Bias-T stop offset",
            )
            self.set(
                int(self.soccfg["gens"][gen_ch]["tproc_ch"]),
                page,
                *command_registers,
                time_register,
                f"finish Bias-T compensation on {output_name}",
            )

            # The target word is no longer needed after both commands have
            # been queued, so reuse its register for the running maximum.
            self.memri(
                page,
                target_register,
                max_duration_addr,
                f"load maximum Bias-T duration for {output_name}",
            )
            self.condj(
                page,
                work_register,
                "<=",
                target_register,
                max_ready_label,
                f"keep maximum Bias-T duration after {output_name}",
            )
            self.memwi(
                page,
                work_register,
                max_duration_addr,
                f"update maximum Bias-T duration from {output_name}",
            )
            self.label(max_ready_label)
            self.mathi(
                page,
                work_register,
                work_register,
                "+",
                0,
                f"maximum Bias-T duration checked for {output_name}",
            )

            self.label(done_label)
            self.mathi(
                page,
                work_register,
                work_register,
                "+",
                0,
                f"Bias-T output {output_name} complete",
            )

        final_page = int(first_field["page"])
        final_register = int(first_field["work_register"])
        no_compensation_label = "BIAS_T_NO_ACTIVE_OUTPUT"
        self.memri(
            final_page,
            final_register,
            max_duration_addr,
            "load maximum Bias-T duration",
        )
        self.condj(
            final_page,
            final_register,
            "==",
            0,
            no_compensation_label,
            "skip Bias-T timing advance when all areas are zero",
        )
        self.mathi(
            final_page,
            final_register,
            final_register,
            "+",
            self.bias_t_simultaneous_start_lead_cycles,
            "include common Bias-T command lead",
        )
        # RTL sync is additive: advance once to the latest channel stop.
        self.sync(
            final_page,
            final_register,
            "advance to latest simultaneous Bias-T stop",
        )
        self.label(no_compensation_label)
        self.mathi(
            final_page,
            final_register,
            final_register,
            "+",
            0,
            "simultaneous Bias-T compensation complete",
        )

    def _emit_bias_t_fixed_time(self):
        """Emit fixed-time compensation with a sweep-dependent SET voltage."""
        active_addr = int(self._bias_t_max_duration_dmem_addr)
        first_field = self._bias_t_fields[0]
        first_page = int(first_field["page"])
        first_target_register = self._gen_regmap[
            (int(first_field["gen_ch"]), "target")
        ][1]
        self.safe_regwi(
            first_page,
            first_target_register,
            0,
            "clear fixed-time Bias-T active marker",
        )
        self.memwi(
            first_page,
            first_target_register,
            active_addr,
            "store cleared fixed-time Bias-T active marker",
        )

        for field in self._bias_t_fields:
            output_index = int(field["output_index"])
            output_name = self.sequence.output_names[output_index]
            gen_ch = int(field["gen_ch"])
            page = int(field["page"])
            work_register = int(field["work_register"])
            target_register = self._gen_regmap[(gen_ch, "target")][1]
            _, time_register = self._gen_regmap[(gen_ch, "t")]
            command_words = _pack_command_words(
                self.soccfg["gens"][gen_ch],
                0,
                0,
                0,
                OP_SET,
            )
            for register_name, word in zip(
                COMMAND_REGISTER_NAMES[1:],
                command_words[1:],
            ):
                reg_page, register = self._gen_regmap[(gen_ch, register_name)]
                if int(reg_page) != page:
                    raise RuntimeError("AWG command registers must share one page")
                self.safe_regwi(
                    page,
                    register,
                    int(word),
                    f"{output_name} fixed-time Bias-T {register_name}",
                )

            self.safe_regwi(
                page,
                time_register,
                self.bias_t_simultaneous_start_lead_cycles,
                f"{output_name} common fixed-time Bias-T start offset",
            )
            self.memri(
                page,
                work_register,
                int(field["dmem_addr"]),
                f"load fixed-time Bias-T target for {output_name}",
            )
            done_label = f"BIAS_T_FIXED_TIME_DONE_{output_index}"
            self.condj(
                page,
                work_register,
                "==",
                0,
                done_label,
                f"skip zero-area fixed-time Bias-T output {output_name}",
            )
            self.mathi(
                page,
                target_register,
                work_register,
                "+",
                0,
                f"apply fixed-time Bias-T target for {output_name}",
            )
            command_registers = [
                self._gen_regmap[(gen_ch, name)][1]
                for name in COMMAND_REGISTER_NAMES
            ]
            self.set(
                int(self.soccfg["gens"][gen_ch]["tproc_ch"]),
                page,
                *command_registers,
                time_register,
                f"start fixed-time Bias-T compensation on {output_name}",
            )
            self.safe_regwi(
                page,
                target_register,
                0,
                f"{output_name} return to zero after fixed-time Bias-T",
            )
            self.safe_regwi(
                page,
                time_register,
                self.bias_t_simultaneous_start_lead_cycles
                + int(field["fixed_duration_tproc_cycles"]),
                f"{output_name} fixed-time Bias-T stop offset",
            )
            self.set(
                int(self.soccfg["gens"][gen_ch]["tproc_ch"]),
                page,
                *command_registers,
                time_register,
                f"finish fixed-time Bias-T compensation on {output_name}",
            )
            self.memwi(
                page,
                work_register,
                active_addr,
                f"mark fixed-time Bias-T active for {output_name}",
            )
            self.label(done_label)
            self.mathi(
                page,
                work_register,
                work_register,
                "+",
                0,
                f"fixed-time Bias-T output {output_name} complete",
            )

        final_page = int(first_field["page"])
        final_register = int(first_field["work_register"])
        no_compensation_label = "BIAS_T_FIXED_TIME_NO_ACTIVE_OUTPUT"
        self.memri(
            final_page,
            final_register,
            active_addr,
            "load fixed-time Bias-T active marker",
        )
        self.condj(
            final_page,
            final_register,
            "==",
            0,
            no_compensation_label,
            "skip fixed-time Bias-T advance when all areas are zero",
        )
        final_offset = self.bias_t_simultaneous_start_lead_cycles + max(
            int(field["fixed_duration_tproc_cycles"])
            for field in self._bias_t_fields
        )
        self.safe_regwi(
            final_page,
            final_register,
            final_offset,
            "fixed-time Bias-T latest stop offset",
        )
        self.sync(
            final_page,
            final_register,
            "advance to fixed-time Bias-T stop",
        )
        self.label(no_compensation_label)
        self.mathi(
            final_page,
            final_register,
            final_register,
            "+",
            0,
            "fixed-time Bias-T compensation complete",
        )

    def _emit_point(self):
        self._emit_unshared_start_marker()
        # Timed-output queues are FIFO ordered. Generators behind the same TMUX
        # therefore must be enqueued in timestamp order, even when their
        # commands target different downstream IPs.
        scheduled_events = []
        insertion_order = 0

        def schedule(time, priority, kind, payload):
            nonlocal insertion_order
            scheduled_events.append((
                int(time),
                int(priority),
                insertion_order,
                kind,
                payload,
            ))
            insertion_order += 1

        # The instruction body is point-independent. Swept SET/RAMP fields are
        # copied from state registers immediately before each command.
        point = self.compiled_points[0]
        for segment_index, commands in enumerate(point.segment_commands):
            for command in commands:
                command_time = self.timing["command_times"][
                    self._timing_key(command)
                ]
                schedule(command_time, 10, "awg", (command, None))

        if self.ddr_readout_config is not None:
            ddr = self.ddr_readout_config
            schedule(
                self.aux_timing["ddr_readout_start"],
                0,
                "ddr_readout",
                ddr.ro_ch,
            )
            schedule(
                self.aux_timing["ddr_trigger_time"],
                20,
                "ddr_trigger",
                ddr,
            )

        for rf_index, rf_config in enumerate(self.rf_pulse_configs):
            schedule(
                self.aux_timing[f"rf_{rf_index}_start"],
                10,
                "rf_start",
                (rf_index, rf_config),
            )
            if self._rf_runtime[rf_index]["periodic"]:
                schedule(
                    self.aux_timing[f"rf_{rf_index}_end"],
                    15,
                    "rf_stop",
                    (rf_index, rf_config),
                )

        point_end = int(self.timing["point_end"])
        point_end_barrier = int(
            getattr(self, "_dynamic_point_end", point_end)
        )
        if self._marker_start_enabled():
            point_end_barrier = max(point_end_barrier, self._marker_start_time() + self._marker["width"] + 1)
        bias_t_static_end = point_end_barrier
        if self.sequence.bias_t_compensation is not None or self.sequence.rc_compensation is not None:
            # End the user-defined AWG pulse before DC compensation/RC reset.
            # This also prevents a long FIR/readout window from adding an
            # unmodeled final-level hold to the area being compensated.
            pulse_end = int(self.timing["segment_ends"][-1]) - self.awg_output_latency_tproc
            for output_index, gen_ch in enumerate(self.awg_channels):
                zero_time = pulse_end + int(self._channel_slots[gen_ch])
                schedule(
                    zero_time,
                    30,
                    "awg",
                    (
                        self._static_set_command(
                            output_index,
                            0,
                            "bias_t_pre_zero",
                        ),
                        (
                            "event_time",
                            "bias_pre_zero",
                            output_index,
                        ),
                    ),
                )
                bias_t_static_end = max(
                    bias_t_static_end,
                    point_end_barrier,
                )
            self.aux_timing["bias_t_user_pulse_end"] = pulse_end
            self.aux_timing["bias_t_static_end"] = bias_t_static_end

        if self.readout_config is not None:
            ro = self.readout_config
            if ro.at_segment is None:
                measure_time = point_end
            else:
                names = [segment.name for segment in self.sequence.segments]
                if ro.at_segment not in names:
                    raise KeyError(f"unknown readout segment {ro.at_segment!r}")
                timing_key = (
                    "segment_starts"
                    if ro.timing_reference == "segment_start"
                    else "segment_ends"
                )
                measure_time = self.timing[timing_key][names.index(ro.at_segment)]
            measure_time += ro.measure_delay_tproc_cycles
            schedule(measure_time, 0, "readout", ro.ro_ch)
            schedule(
                measure_time,
                20,
                "adc_trigger",
                ro,
            )

        for event_time, _priority, _order, kind, payload in sorted(
            scheduled_events,
            key=lambda item: item[:3],
        ):
            if kind == "awg":
                command, event_field_key = payload
                self._emit_command(
                    command,
                    event_time,
                    event_field_key=event_field_key,
                )
            elif kind == "readout":
                self.readout(ch=payload, t=event_time)
            elif kind == "ddr_readout":
                self._emit_readout_at(
                    payload,
                    event_time,
                    ("event_time", "ddr_readout"),
                )
            elif kind == "rf_start":
                rf_index, rf_config = payload
                self._emit_rf_start(rf_index, rf_config, event_time)
            elif kind == "rf_stop":
                rf_index, rf_config = payload
                self._emit_rf_stop(rf_index, rf_config, event_time)
            elif kind == "ddr_trigger":
                cfg = self.soccfg["ddr4_buf"]
                self._emit_marker_readout_trigger(
                    lambda: self._emit_ddr_trigger(payload, event_time),
                    t=event_time, width=payload.trigger_width_tproc_cycles,
                    port=cfg["trigger_port"], bit=cfg["trigger_bit"],
                    field_key=("event_time", "ddr_trigger"),
                )
            elif kind == "adc_trigger":
                cfg = self.soccfg["readouts"][payload.ro_ch]
                self._emit_marker_readout_trigger(
                    lambda: self.trigger(adcs=[payload.ro_ch], adc_trig_offset=event_time,
                                         t=0, width=payload.trigger_width_tproc_cycles),
                    t=event_time, width=payload.trigger_width_tproc_cycles,
                    port=cfg["trigger_port"], bit=cfg["trigger_bit"], ro_ch=payload.ro_ch,
                )
            else:
                raise RuntimeError(f"unknown scheduled event kind {kind!r}")

        for gen_ch in (
            tuple(self.awg_channels)
            + tuple(rf.gen_ch for rf in self.rf_pulse_configs)
        ):
            self.set_timestamp(bias_t_static_end, gen_ch=gen_ch)

        if self.readout_config is not None:
            ro = self.readout_config
            if ro.wait:
                self.wait_all()

        if self.sequence.bias_t_compensation is None and self.sequence.rc_compensation is None:
            self.sync_all(self.recovery_tproc_cycles)
        else:
            # Move the reference beyond all statically timed AWG/RF/readout
            # events. Dynamic compensation uses one common start timestamp,
            # channel-specific stop timestamps, and one final max-duration sync.
            self.sync_all(0)
            if self.sequence.bias_t_compensation is not None:
                if self.sequence.bias_t_compensation.inter_output_gap_cycles:
                    self.synci(
                        int(self.sequence.bias_t_compensation.inter_output_gap_cycles),
                        "common Bias-T guard after pre-compensation zero",
                    )
                self._emit_bias_t_compensation()
                # Keep the next command off the SET-zero stop timestamp.
                self.synci(
                    1,
                    "separate Bias-T stop from the next sweep point",
                )
            self._emit_rc_repeat_reset()
            if self.recovery_tproc_cycles:
                self.synci(
                    self.recovery_tproc_cycles,
                    "post Bias-T shot recovery",
                )

    def _emit_ramp_duration_group_row(
        self,
        group,
        *,
        action: str,
    ) -> None:
        """Load the table row addressed by a group's pointer register."""
        page = int(group["page"])
        pointer = int(group["pointer_register"])
        scratch = int(group["scratch_register"])
        for column_index, column in enumerate(group["columns"]):
            field = column["field"]
            if column["kind"] == "base":
                if field.get("storage") == "dmem":
                    destination = int(field["work_register"])
                else:
                    destination = int(field["state_register"])
                self.memr(
                    page,
                    destination,
                    pointer,
                    f"load {action} RAMP-rate row {field['key']}",
                )
                if field.get("storage") == "dmem":
                    self.memwi(
                        page,
                        destination,
                        int(field["dmem_addr"]),
                        f"store {action} RAMP-rate row {field['key']}",
                    )
            else:
                self.memr(
                    page,
                    scratch,
                    pointer,
                    f"load {action} RAMP-rate axis coefficient",
                )
                self.memwi(
                    page,
                    scratch,
                    int(column["slot"]),
                    f"store {action} RAMP-rate axis coefficient",
                )
            self.mathi(
                page,
                pointer,
                pointer,
                "+",
                1,
                f"advance {action} RAMP-rate column {column_index}",
            )
        self.memwi(
            page,
            pointer,
            int(group["pointer_state_addr"]),
            f"store {action} RAMP-rate table pointer",
        )

    def _initialize_ramp_duration_tables(self) -> None:
        """Load row zero once for every single- or multi-duration table."""
        for _group_key, group in sorted(
            self._ramp_duration_table_groups.items()
        ):
            page = int(group["page"])
            pointer = int(group["pointer_register"])
            self.safe_regwi(
                page,
                pointer,
                int(group["base_address"]),
                "initialize RAMP-rate table pointer",
            )
            self._emit_ramp_duration_group_row(
                group,
                action="initial",
            )

    def _emit_ramp_duration_table_load(
        self,
        axis_index: int,
        *,
        reset: bool = False,
    ) -> None:
        """Move and load tables conditioned by the changed RAMP axis."""
        axis_index = int(axis_index)
        groups = [
            group
            for _group_key, group in sorted(
                self._ramp_duration_table_groups.items()
            )
            if axis_index in tuple(
                int(value) for value in group["axis_indices"]
            )
        ]
        for group in groups:
            page = int(group["page"])
            pointer = int(group["pointer_register"])
            self.memri(
                page,
                pointer,
                int(group["pointer_state_addr"]),
                f"load RAMP-rate axis {axis_index} table pointer",
            )
            stride_rows = int(group["axis_row_strides"][axis_index])
            axis_count = int(self.sequence.sweep_axes[axis_index].count)
            row_delta = (
                -(axis_count - 1) * stride_rows
                if reset
                else stride_rows
            )
            # The saved pointer is immediately after the current row. Move it
            # to the next row's first word before consuming that row.
            pointer_adjustment = (
                row_delta - 1
            ) * int(group["row_width"])
            if pointer_adjustment:
                self.mathi(
                    page,
                    pointer,
                    pointer,
                    "+",
                    int(pointer_adjustment),
                    f"move RAMP-rate axis {axis_index} table pointer",
                )
            self._emit_ramp_duration_group_row(
                group,
                action=(
                    f"axis {axis_index} reset"
                    if reset
                    else f"axis {axis_index} advance"
                ),
            )

    def _emit_axis_adds(self, axis_index: int, *, reset: bool = False):
        """Advance or reset one Cartesian axis using register-immediate adds."""
        axis = self.sequence.sweep_axes[axis_index]
        multiplier = -(axis.count - 1) if reset else 1
        action = "reset" if reset else "advance"
        for table in self._rf_point_tables:
            stride = table["axis_strides"].get(int(axis_index))
            if stride is None:
                continue
            amount = int(stride) * int(multiplier)
            if amount:
                self.mathi(
                    int(table["page"]),
                    int(table["pointer_register"]),
                    int(table["pointer_register"]),
                    "+",
                    amount,
                    f"{action} axis {axis_index} {table['key']} pointer",
                )
        for field in self._sweep_fields:
            if "duration_table_bases" in field:
                duration_axis_indices = tuple(
                    int(value)
                    for value in field.get(
                        "duration_axis_indices",
                        (field["duration_axis_index"],),
                    )
                )
                if axis_index in duration_axis_indices:
                    continue
                slots = field["duration_delta_slots"].get(axis_index)
                if slots is None:
                    continue
                page = int(field["page"])
                scratch = int(
                    self._ramp_duration_table_page_resources[page][
                        "scratch_register"
                    ]
                )
                self.memri(
                    page,
                    scratch,
                    int(slots["reset" if reset else "advance"]),
                    f"load RAMP-rate {action} axis {axis_index} coefficient",
                )
                if field.get("storage") == "dmem":
                    work_register = int(field["work_register"])
                    self.memri(
                        page,
                        work_register,
                        int(field["dmem_addr"]),
                        f"load RAMP-rate {action} state {field['key']}",
                    )
                    self.math(
                        page,
                        work_register,
                        work_register,
                        "+",
                        scratch,
                        f"RAMP-rate {action} axis {axis_index} {field['key']}",
                    )
                    self.memwi(
                        page,
                        work_register,
                        int(field["dmem_addr"]),
                        f"store RAMP-rate {action} state {field['key']}",
                    )
                else:
                    state_register = int(field["state_register"])
                    self.math(
                        page,
                        state_register,
                        state_register,
                        "+",
                        scratch,
                        f"RAMP-rate {action} axis {axis_index} {field['key']}",
                    )
                continue
            amount = int(field["axis_deltas"][axis_index]) * multiplier
            if amount == 0:
                continue
            page = int(field["page"])
            if field.get("storage") == "dmem":
                work_register = int(field["work_register"])
                dmem_addr = int(field["dmem_addr"])
                self.memri(
                    page,
                    work_register,
                    dmem_addr,
                    f"load {action} axis {axis_index} {field['key']}",
                )
                self.mathi(
                    page,
                    work_register,
                    work_register,
                    "+",
                    amount,
                    f"{action} axis {axis_index} {field['key']}",
                )
                self.memwi(
                    page,
                    work_register,
                    dmem_addr,
                    f"store {action} axis {axis_index} {field['key']}",
                )
                continue
            state_register = int(field["state_register"])
            self.mathi(
                page,
                state_register,
                state_register,
                "+",
                amount,
                f"{action} axis {axis_index} {field['key']}",
            )
        if (
            axis_index in self._ramp_duration_axis_indices_runtime
            and self._ramp_duration_table_groups
        ):
            self._emit_ramp_duration_table_load(
                axis_index,
                reset=reset,
            )

    def make_program(self):
        """Emit nested point/repetition loops and register-add sweep updates."""
        rcount = 13
        rrep = 15
        self.initialize()
        if any(self.soccfg["gens"][ch].get("rc_precomp_version", 0) for ch in self.awg_channels):
            self.synci(200)
            self._initialize_rc_compensation()
        self.regwi(0, rcount, 0)
        extended_epilogue = (
            self._marker is not None or self.square_pulse_config is not None
            or self.sequence.rc_compensation is not None
        )
        if extended_epilogue:
            self.safe_regwi(0, 14, self.cfg["expts"] * self.cfg["reps"], "final acquisition count")
        for field in self._sweep_fields:
            page = int(field["page"])
            if field.get("storage") == "dmem":
                work_register = int(field["work_register"])
                self.safe_regwi(
                    page,
                    work_register,
                    int(field["base"]),
                    f"initialize DMEM sweep state {field['key']}",
                )
                self.memwi(
                    page,
                    work_register,
                    int(field["dmem_addr"]),
                    f"store initial DMEM sweep state {field['key']}",
                )
            else:
                self.safe_regwi(
                    page,
                    int(field["state_register"]),
                    int(field["base"]),
                    f"initialize direct sweep state {field['key']}",
                )
        for table in self._rf_point_tables:
            self.safe_regwi(
                int(table["page"]),
                int(table["pointer_register"]),
                int(table["base_address"]),
                f"initialize {table['key']} DMEM pointer",
            )
        self._initialize_ramp_duration_tables()
        active_axes = tuple(sorted(self._sweep_axis_runtime))
        for axis_index in active_axes:
            runtime = self._sweep_axis_runtime[axis_index]
            self.safe_regwi(
                int(runtime["counter_page"]),
                int(runtime["counter_register"]),
                int(runtime["count"]) - 1,
                f"initialize sweep axis {axis_index} counter",
            )
        if self.command_lead_tproc_cycles:
            self.synci(self.command_lead_tproc_cycles)
        self.square_marker_startup_lead = (
            128 * int(self.square_pulse_config is not None)
            + 128 * int(self._marker is not None)
        )
        if self.square_marker_startup_lead:
            self.synci(self.square_marker_startup_lead,
                       "initial lookahead for SquarePulse and external markers")

        self.label("FINE_TUNE_POINT")
        self.regwi(0, rrep, self.cfg["reps"] - 1)
        self.label("FINE_TUNE_REP")
        self._emit_square_update()
        self._emit_point()
        self._emit_end_marker("loop")
        self.mathi(0, rcount, rcount, "+", 1)
        if extended_epilogue:
            self.condj(0, rcount, "==", 14, "DEFER_FINAL_ACQUISITION_COUNT")
        self.memwi(0, rcount, self.COUNTER_ADDR)
        if extended_epilogue:
            self.label("DEFER_FINAL_ACQUISITION_COUNT")
        self.loopnz(0, rrep, "FINE_TUNE_REP")

        # The last axis varies fastest. A finished inner loop is reset before
        # the next outer axis is advanced, matching itertools.product order.
        for position in range(len(active_axes) - 1, -1, -1):
            axis_index = active_axes[position]
            runtime = self._sweep_axis_runtime[axis_index]
            page = int(runtime["counter_page"])
            register = int(runtime["counter_register"])
            self.loopnz(page, register, f"FINE_TUNE_ADVANCE_{axis_index}")
            if position > 0:
                self.safe_regwi(
                    page,
                    register,
                    int(runtime["count"]) - 1,
                    f"reload sweep axis {axis_index} counter",
                )
                self._emit_axis_adds(axis_index, reset=True)
        if self.square_pulse_config is not None and self.square_pulse_config.mute_on_finish:
            self._emit_square_update(stop=True)
        self._emit_end_marker("experiment")
        if extended_epilogue:
            self.waiti(0, 0, "wait for experiment epilogue")
            self.memwi(0, rcount, self.COUNTER_ADDR)
        self.end()

        for axis_index in active_axes:
            self.label(f"FINE_TUNE_ADVANCE_{axis_index}")
            self._emit_axis_adds(axis_index)
            self.condj(0, 0, "==", 0, "FINE_TUNE_POINT")

    def body(self):
        raise RuntimeError(
            "FineTuneAmplitudeSweepProgram uses nested hardware loops in make_program()"
        )

    def update(self):
        pass

    def _load_runtime_dmem(self, soc, *, reload_mem: bool = False) -> None:
        """Restore compiled DMEM and then install RAMP-rate coefficients."""
        if reload_mem:
            soc.reload_mem()
        if not self._runtime_dmem_words:
            return
        if not hasattr(soc, "load_mem"):
            raise RuntimeError(
                "QICK SoC does not expose load_mem required by RAMP-rate sweep"
            )
        soc.load_mem(
            [int(value) for value in self._runtime_dmem_words],
            mem_sel="dmem",
            addr=int(self._runtime_dmem_base),
        )

    def load_runtime_dmem_into_model(self, model) -> None:
        """Preload the Python tProcessor behavior model for self-checking tests."""
        if not hasattr(model, "dmem"):
            raise TypeError("model must expose a dmem mapping")
        if self._runtime_dmem_base is None:
            return
        for offset, value in enumerate(self._runtime_dmem_words):
            model.dmem[int(self._runtime_dmem_base) + offset] = (
                int(value) & 0xFFFFFFFF
            )

    def prepare_round(self):
        """Use QICK's normal round setup, then restore the coefficient table."""
        super().prepare_round()
        self._load_runtime_dmem(
            self.acquire_params["soc"],
            reload_mem=False,
        )

    def _run_rounds_with_counter_progress(
        self,
        soc,
        progress_callback,
        *,
        poll_interval_seconds: float = 0.02,
        cancel_check: Optional[Callable[[], None]] = None,
    ) -> None:
        """Run without readout streaming and report the real tProc loop count."""
        import time

        total_per_round = int(np.prod(self.loop_dims, dtype=np.int64))
        rounds = int(self.rounds)
        total = total_per_round * rounds
        if cancel_check is not None:
            cancel_check()
        self.config_all(soc, load_envelopes=True, load_mem=False)
        progress_callback(0, total)
        completed_rounds = 0
        tproc_running = False
        try:
            for _round_index in range(rounds):
                if cancel_check is not None:
                    cancel_check()
                self._load_runtime_dmem(soc, reload_mem=True)
                soc.clear_tproc_counter(addr=self.counter_addr)
                soc.start_src("internal")
                soc.start_tproc()
                tproc_running = True
                count = 0
                while count < total_per_round:
                    if cancel_check is not None:
                        cancel_check()
                    count = min(
                        total_per_round,
                        int(soc.get_tproc_counter(addr=self.counter_addr)),
                    )
                    progress_callback(completed_rounds + count, total)
                    if count < total_per_round:
                        time.sleep(poll_interval_seconds)
                tproc_running = False
                completed_rounds += total_per_round
        finally:
            if tproc_running:
                try:
                    soc.stop_tproc()
                except Exception:
                    pass
            soc.start_src("internal")

    def acquire_fir_ddr(
        self,
        soc,
        *,
        progress: bool = True,
        counter_progress=None,
        readback_progress=None,
        phase_callback=None,
        cancel_check: Optional[Callable[[], None]] = None,
        readback_chunk_triggers: int = DEFAULT_DDR_READBACK_TRIGGER_CHUNK,
        **run_kwargs,
    ):
        """Arm DDR and return IQ grouped at the HWH-selected FIR sample rate.

        The nested hardware loops run Cartesian-point-major and
        repetition-minor, so the flat DDR stream is reshaped to
        ``(point_count, N, samples, I/Q)``.  ``result.iq_grid`` restores the
        independent sweep axes before the repetition dimension.
        """
        if self.ddr_readout_config is None:
            raise RuntimeError("acquire_fir_ddr requires ddr_readout configuration")
        import time

        ddr = self.ddr_readout_config
        n_points = self.sequence.sweep_point_count
        repetitions = int(self.cfg["reps"])
        n_triggers = n_points * repetitions

        def emit_phase(key, state, message):
            if phase_callback is not None:
                phase_callback(str(key), str(state), str(message))

        def check_cancel():
            if cancel_check is not None:
                cancel_check()

        check_cancel()
        readback_chunk_triggers = _require_int(
            readback_chunk_triggers,
            "readback_chunk_triggers",
            1,
        )
        arm_kwargs = dict(
            ch=ddr.ro_ch,
            n_samples=ddr.samples_per_trigger,
            n_triggers=n_triggers,
            address=ddr.address,
            stride_bytes=ddr.stride_bytes,
            force_overwrite=ddr.force_overwrite,
        )
        if self._fir_cfg["uses_fpga_trigger_delay"]:
            arm_kwargs.update(self._fir_cfg["trigger_delay_arm_kwargs"])
        emit_phase(
            "ddr_arm",
            "started",
            f"Arming FIR DDR for {n_triggers:,} trigger(s)",
        )
        reserved = soc.arm_ddr4_fir_samples(**arm_kwargs)
        check_cancel()
        emit_phase(
            "ddr_arm",
            "completed",
            f"FIR DDR armed; reserved {reserved:,} physical 32-bit word(s)",
        )
        emit_phase(
            "acquisition",
            "started",
            (
                f"Starting {n_points:,} sweep point(s) x "
                f"{repetitions:,} repetition(s)"
            ),
        )
        if counter_progress is None and cancel_check is None:
            self.run_rounds(soc, progress=progress, **run_kwargs)
        else:
            if run_kwargs:
                unexpected = ", ".join(sorted(run_kwargs))
                raise TypeError(
                    "counter-progress execution does not support extra run "
                    f"arguments: {unexpected}"
                )
            self._run_rounds_with_counter_progress(
                soc,
                counter_progress or (lambda _completed, _total: None),
                cancel_check=cancel_check,
            )
        check_cancel()
        emit_phase(
            "acquisition",
            "completed",
            f"All {n_triggers:,} acquisition trigger(s) completed",
        )
        if ddr.settle_seconds:
            emit_phase(
                "ddr_wait",
                "started",
                (
                    "Waiting before DDR readback "
                    f"({float(ddr.settle_seconds):g} s)"
                ),
            )
            deadline = time.monotonic() + float(ddr.settle_seconds)
            while True:
                check_cancel()
                remaining = deadline - time.monotonic()
                if remaining <= 0.0:
                    break
                time.sleep(min(0.05, remaining))
            emit_phase(
                "ddr_wait",
                "completed",
                "Post-acquisition DDR read delay completed",
            )

        if reserved % n_triggers:
            raise RuntimeError(
                "reserved DDR words are not divisible by the trigger count"
            )
        physical_words_per_trigger = reserved // n_triggers
        if ddr.address % 4:
            raise ValueError("DDR byte address must be aligned to a 32-bit word")
        base_word = ddr.address // 4
        if ddr.stride_bytes is None:
            stride_words = physical_words_per_trigger
        else:
            if ddr.stride_bytes % 4:
                raise ValueError("DDR stride_bytes must be a multiple of 4")
            stride_words = ddr.stride_bytes // 4

        expected_shape = (n_triggers * ddr.samples_per_trigger, 2)
        raw = None
        readback_chunks = (
            n_triggers + readback_chunk_triggers - 1
        ) // readback_chunk_triggers
        emit_phase(
            "ddr_readback",
            "started",
            (
                f"Reading {n_triggers:,} DDR trace(s) in "
                f"{readback_chunks:,} chunk(s)"
            ),
        )
        if readback_progress is not None:
            readback_progress(0, n_triggers)
        for first_trigger in range(
            0,
            n_triggers,
            readback_chunk_triggers,
        ):
            check_cancel()
            chunk_trigger_count = min(
                readback_chunk_triggers,
                n_triggers - first_trigger,
            )
            chunk_start_word = base_word + first_trigger * stride_words
            chunk = np.asarray(soc.get_ddr4_fir_samples(
                n_samples=ddr.samples_per_trigger,
                n_triggers=chunk_trigger_count,
                start=chunk_start_word,
                stride_bytes=ddr.stride_bytes,
            ))
            check_cancel()
            expected_chunk_shape = (
                chunk_trigger_count * ddr.samples_per_trigger,
                2,
            )
            if self._fir_cfg["iq_component_bits"] == 64 and chunk.dtype != np.dtype("int64"):
                raise RuntimeError("IQ64 firmware did not return raw signed-int64 samples")
            if chunk.shape != expected_chunk_shape:
                raise RuntimeError(
                    f"unexpected DDR IQ chunk shape {chunk.shape}; expected "
                    f"{expected_chunk_shape} for triggers "
                    f"{first_trigger}.."
                    f"{first_trigger + chunk_trigger_count - 1}"
                )
            if raw is None:
                raw = np.empty(expected_shape, dtype=chunk.dtype)
            first_sample = first_trigger * ddr.samples_per_trigger
            last_sample = (
                first_trigger + chunk_trigger_count
            ) * ddr.samples_per_trigger
            raw[first_sample:last_sample] = chunk
            if readback_progress is not None:
                readback_progress(
                    first_trigger + chunk_trigger_count,
                    n_triggers,
                )

        if raw is None:
            raise RuntimeError("DDR readback produced no chunks")
        check_cancel()
        emit_phase(
            "ddr_readback",
            "completed",
            (
                f"FIR DDR readback completed: "
                f"{expected_shape[0]:,} I/Q sample pair(s)"
            ),
        )
        iq = raw.reshape(
            n_points,
            repetitions,
            ddr.samples_per_trigger,
            2,
        )
        return FineTuneDdrResult(
            sweep_points=self.get_expt_pts(),
            iq=iq,
            reserved_physical_words=reserved,
            sweep_axes=self.sequence.sweep_axes,
            sweep_shape=self.sequence.sweep_shape,
            cross_capacitance=self.sequence.cross_capacitance.copy(),
            sample_rate_hz=self._fir_cfg["output_sample_rate_hz"],
            fir_rate_profile=self._fir_cfg["rate_profile"],
            iq_scale_log2=self._fir_cfg["iq_scale_log2"],
            iq_component_bits=self._fir_cfg["iq_component_bits"],
            acquisition_source="fir_ddr",
            accumulation_repetitions=repetitions,
        )

    def acquire_avg_buffer(
        self,
        soc,
        *,
        progress: bool = False,
        counter_progress=None,
        cancel_check: Optional[Callable[[], None]] = None,
    ):
        """Return one repetition-averaged AVG-buffer I/Q value per point.

        Cartesian points and repetitions remain tProcessor hardware loops.
        QICK's averager normalizes the accumulated readout by both integration
        length and repetition count, so the returned array contains one
        coherent mean I/Q pair for every Cartesian coordinate.
        """
        if self.readout_config is None:
            raise RuntimeError(
                "acquire_avg_buffer requires readout configuration"
            )
        if self.ddr_readout_config is not None:
            raise RuntimeError(
                "AVG-buffer acquisition cannot share the FIR DDR readout path"
            )

        n_points = self.sequence.sweep_point_count
        repetitions = int(self.cfg["reps"])
        total = n_points * repetitions
        if cancel_check is not None:
            cancel_check()
        if counter_progress is not None:
            counter_progress(0, total)
        _expt_points, avg_di, avg_dq = super().acquire(
            soc,
            progress=progress,
        )
        if cancel_check is not None:
            cancel_check()
        if counter_progress is not None:
            counter_progress(total, total)
        if len(avg_di) != 1 or len(avg_dq) != 1:
            raise RuntimeError(
                "AVG-buffer stability acquisition expected exactly one "
                f"readout channel, received I/Q channel counts "
                f"{len(avg_di)}/{len(avg_dq)}"
            )
        mean_i = np.asarray(avg_di[0], dtype=np.float64).reshape(-1)
        mean_q = np.asarray(avg_dq[0], dtype=np.float64).reshape(-1)
        if mean_i.size != n_points or mean_q.size != n_points:
            raise RuntimeError(
                "unexpected AVG-buffer Cartesian result shape: "
                f"I={np.asarray(avg_di[0]).shape}, "
                f"Q={np.asarray(avg_dq[0]).shape}; expected {n_points} point(s)"
            )
        iq = np.stack((mean_i, mean_q), axis=-1)[:, None, None, :]
        ro_cfg = self.soccfg["readouts"][self.readout_config.ro_ch]
        sample_rate_hz = float(
            ro_cfg.get("f_output", ro_cfg.get("f_fabric", 1.0))
        ) * 1_000_000.0
        return FineTuneDdrResult(
            sweep_points=self.get_expt_pts(),
            iq=iq,
            reserved_physical_words=0,
            sweep_axes=self.sequence.sweep_axes,
            sweep_shape=self.sequence.sweep_shape,
            cross_capacitance=self.sequence.cross_capacitance.copy(),
            sample_rate_hz=sample_rate_hz,
            fir_rate_profile="avg_buffer",
            acquisition_source="avg_buffer",
            accumulation_repetitions=repetitions,
        )

    def summary(self):
        dmem_addresses = {
            int(field["dmem_addr"])
            for field in self._sweep_fields
            if field.get("storage") == "dmem"
        }
        if self._bias_t_max_duration_dmem_addr is not None:
            dmem_addresses.add(int(self._bias_t_max_duration_dmem_addr))
        if self._runtime_dmem_base is not None:
            dmem_addresses.update(
                range(
                    int(self._runtime_dmem_base),
                    int(self._runtime_dmem_last_address) + 1,
                )
            )
        for instruction in self.prog_list:
            if instruction.get("name") in {"memri", "memwi"}:
                args = instruction.get("args", ())
                if len(args) >= 3:
                    dmem_addresses.add(int(args[2]))
        compensation = self.sequence.bias_t_compensation
        compensation_type = (
            None
            if compensation is None
            else compensation.compensation_type
        )
        pmem_words = len(self.prog_list)
        return {
            "outputs": self.sequence.output_names,
            "awg_channels": self.awg_channels,
            "sweep_points": self.get_expt_pts(),
            "sweep_axes": self.sequence.sweep_axes,
            "sweep_shape": self.sequence.sweep_shape,
            "cartesian_point_count": self.sequence.sweep_point_count,
            "compile_validation_mode": self.compile_validation_mode,
            "compile_validation_point_count": len(
                self._compile_validation_point_indices
            ),
            "compile_validation_point_indices": (
                None
                if self.compile_validation_mode == COMPILE_VALIDATION_FULL
                else self._compile_validation_point_indices
            ),
            "cross_capacitance": self.sequence.cross_capacitance.copy(),
            "segments": tuple(segment.name for segment in self.sequence.segments),
            "repetitions_per_sweep": self.cfg["reps"],
            "repetitions_per_sweep_point": self.cfg["reps"],
            "total_acquisitions": (
                self.sequence.sweep_point_count * self.cfg["reps"]
            ),
            "commands_per_point": sum(
                len(commands) for commands in self.compiled_points[0].segment_commands
            ),
            "sweep_execution": (
                "tproc_loop_add_with_ramp_rate_coefficients"
                if self._runtime_dmem_words
                else "tproc_loop_and_add"
            ),
            "sweep_dynamic_register_fields": sum(
                field.get("storage") != "dmem" for field in self._sweep_fields
            ),
            "sweep_dynamic_dmem_fields": sum(
                field.get("storage") == "dmem" for field in self._sweep_fields
            ),
            "sweep_uses_point_table": bool(self._rf_point_tables),
            **self._square_settings_metadata(),
            **self._trigger_settings_metadata(),
            "rf_point_table_count": len(self._rf_point_tables),
            "rf_point_table_words": self._rf_runtime_table_word_count,
            "rf_frequency_sweeps": sum(
                isinstance(axis, RfFrequencySweep)
                for axis in self.sequence.sweep_axes
            ),
            "rf_power_sweeps": sum(
                isinstance(axis, RfPowerSweep)
                for axis in self.sequence.sweep_axes
            ),
            "ramp_rate_coefficient_table_words": len(
                self._runtime_dmem_words[:self._ramp_runtime_table_word_count]
            ),
            "runtime_sweep_table_words": len(self._runtime_dmem_words),
            "ramp_rate_coefficient_table_base": self._runtime_dmem_base,
            "ramp_rate_coefficient_table_last": (
                self._runtime_dmem_last_address
            ),
            "sweep_max_target_quantization_error": self._sweep_max_target_error,
            "sweep_max_step_quantization_error": self._sweep_max_step_error,
            "sweep_max_duration_quantization_error": (
                self._sweep_max_duration_error
            ),
            "bias_t_compensation": self.sequence.bias_t_compensation is not None,
            "bias_t_compensation_type": compensation_type,
            "rc_compensation": self.sequence.rc_compensation,
            "rc_reset_each_repeat": self.sequence.rc_compensation is not None,
            "rc_output_range_validation": self.rc_output_range_validation,
            "awg_output_latency_tproc_cycles": self.awg_output_latency_tproc,
            "bias_t_compensation_config": self.sequence.bias_t_compensation,
            "bias_t_compensation_mode": self._bias_t_mode,
            "bias_t_duration_execution": (
                None
                if self.sequence.bias_t_compensation is None
                else (
                    "tproc_fixed_time_dynamic_voltage"
                    if self._bias_t_mode == "fixed_time"
                    else "tproc_simultaneous_set_and_max_sync"
                )
            ),
            "bias_t_dynamic_register_fields": 0,
            "bias_t_dynamic_dmem_fields": len(self._bias_t_fields),
            "bias_t_dmem_addresses": tuple(
                int(field["dmem_addr"]) for field in self._bias_t_fields
            ),
            "bias_t_max_duration_q_error": self._bias_t_max_duration_q_error,
            "bias_t_max_target_code_error": self._bias_t_max_target_code_error,
            "bias_t_simultaneous_start": (
                isinstance(
                    self.sequence.bias_t_compensation,
                    BiasTCompensationConfig,
                )
            ),
            "bias_t_simultaneous_start_lead_cycles": (
                self.bias_t_simultaneous_start_lead_cycles
            ),
            "bias_t_max_duration_dmem_address": (
                self._bias_t_max_duration_dmem_addr
            ),
            "startup_lead_tproc_cycles_once": self.command_lead_tproc_cycles,
            "square_marker_startup_lead_tproc_cycles_once": self.square_marker_startup_lead,
            "tproc_mhz": self.tproc_mhz,
            "hwh_tproc_mhz": self.hwh_tproc_mhz,
            "tproc_clock_is_manual": self.tproc_clock_is_manual,
            "point_end_tproc_cycles": self.timing["point_end"],
            "point_end_tproc_cycles_max": int(
                getattr(
                    self,
                    "_dynamic_point_end",
                    self.timing["point_end"],
                )
            ),
            "program_instructions": len(self.prog_list),
            "tproc_pmem_words_used": pmem_words,
            "tproc_dmem_words_reserved": len(dmem_addresses),
            "tproc_dmem_words_required": (
                max(dmem_addresses) + 1 if dmem_addresses else 0
            ),
            "tproc_dmem_addresses": tuple(sorted(dmem_addresses)),
            "tproc_pmem_capacity": int(self.tproccfg.get("pmem_size", 0)),
            "tproc_dmem_capacity": int(self.tproccfg.get("dmem_size", 0)),
            "tproc_memory_within_4096": (
                pmem_words < 4096
                and all(0 <= address < 4096 for address in dmem_addresses)
            ),
            "rf_pulse": bool(self.rf_pulse_configs),
            "rf_pulse_count": len(self.rf_pulse_configs),
            "rf_duration_sweeps": tuple(
                axis
                for axis in self.sequence.sweep_axes
                if isinstance(axis, RfDurationSweep)
            ),
            "ramp_duration_sweeps": tuple(
                axis
                for axis in self.sequence.sweep_axes
                if isinstance(axis, RampDurationSweep)
            ),
            "hold_duration_sweeps": tuple(
                axis
                for axis in self.sequence.sweep_axes
                if isinstance(axis, HoldDurationSweep)
            ),
            "fir_ddr_readout": self.ddr_readout_config is not None,
            "avg_buffer_readout": self.readout_config is not None,
            "acquisition_source": (
                "fir_ddr"
                if self.ddr_readout_config is not None
                else ("avg_buffer" if self.readout_config is not None else None)
            ),
            "fir_rate_profile": (
                self._fir_cfg["rate_profile"]
                if self.ddr_readout_config is not None
                else None
            ),
            "fir_output_sample_rate_hz": (
                self._fir_cfg["output_sample_rate_hz"]
                if self.ddr_readout_config is not None
                else None
            ),
            "fir_software_warmup_compensation": (
                self._fir_cfg["software_warmup_compensation"]
                if self.ddr_readout_config is not None
                else None
            ),
            "fir_software_trigger_delay_output_samples": (
                self._fir_cfg["software_trigger_delay_output_samples"]
                if self.ddr_readout_config is not None
                else None
            ),
            "fir_software_trigger_delay_input_samples": (
                self._fir_cfg["software_trigger_delay_input_samples"]
                if self.ddr_readout_config is not None
                else None
            ),
            "fir_software_trigger_delay_tproc_cycles": (
                self.aux_timing.get("fir_software_trigger_delay_tproc_cycles")
                if self.ddr_readout_config is not None
                else None
            ),
            "fir_fpga_trigger_delay_samples": (
                self._fir_cfg["trigger_delay_samples"]
                if self.ddr_readout_config is not None
                else None
            ),
            "fir_fpga_trigger_delay_units": (
                self._fir_cfg["trigger_delay_units"]
                if self.ddr_readout_config is not None
                else None
            ),
            "total_ddr_triggers": (
                self.sequence.sweep_point_count * self.cfg["reps"]
                if self.ddr_readout_config is not None
                else 0
            ),
            "aux_timing": dict(self.aux_timing),
        }


__all__ = [
    "AmplitudeSweep",
    "BIAS_T_COMPENSATION_TYPES",
    "BiasTCompensationConfig",
    "BiasTCompensationPreview",
    "RCCompensationConfig",
    "COMPILE_VALIDATION_BOUNDARY",
    "COMPILE_VALIDATION_FULL",
    "COMPILE_VALIDATION_MODES",
    "CompiledCommand",
    "CompiledPoint",
    "DEFAULT_COMPILE_VALIDATION_MODE",
    "DdrFirReadoutConfig",
    "DEFAULT_BIAS_T_DURATION_FRAC_BITS",
    "FineTuneAmplitudeSweepProgram",
    "FineTuneDdrResult",
    "FineTuneSequence",
    "HoldDurationSweep",
    "MAX_OUTPUTS",
    "PulseSegment",
    "RampDurationSweep",
    "ReadoutConfig",
    "RfDurationSweep",
    "RfFrequencySweep",
    "RfPowerSweep",
    "RfPulseConfig",
    "RfSegmentLengthExtension",
    "compile_sequence",
    "cycles_from_ns",
    "normalize_compile_validation_mode",
    "cycles_from_us",
    "dac_to_normalized",
    "normalized_to_dac",
]
