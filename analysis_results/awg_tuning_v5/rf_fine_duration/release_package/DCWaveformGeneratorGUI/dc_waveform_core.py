"""Core waveform model and QCS/QICK code generators.

The GUI stores time in nanoseconds and voltage in millivolts.  Keeping those
units inside this module prevents UI code from mixing SI seconds with display
values.  QICK export maps the configured millivolt full scale to the normalized
[-1.0, 1.0] range used by :mod:`qick_fine_tune_sweep`.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from math import ceil, isfinite, pi, sin
from numbers import Integral, Real
import keyword
import re
from typing import Mapping, Optional, Sequence, Tuple, Union

import numpy as np


DEFAULT_INITIAL_VOLTAGE_MV = 100.0
DEFAULT_INITIAL_DURATION_NS = 100.0
DEFAULT_INSERT_RAMP_NS = 50.0
DEFAULT_INSERT_FLAT_NS = 100.0
DEFAULT_MIN_DURATION_NS = 1.0e-6
DEFAULT_QCS_FULL_SCALE_V = 5.0
DEFAULT_QICK_FABRIC_MHZ = 300.0
DEFAULT_QICK_TPROC_MHZ = 300.0
DEFAULT_QICK_FULL_SCALE_MV = 800.0
DEFAULT_DC_MEASURE_GAIN_V_PER_A = 1.0
DEFAULT_BIAS_T_COMPENSATION_FRACTION = 0.1
DEFAULT_BIAS_T_COMPENSATION_DURATION_US = 1.0
DEFAULT_BIAS_T_FILTER_TAU_US = 100.0
BIAS_T_COMPENSATION_MODES = ("fixed_voltage", "fixed_time")
BIAS_T_COMPENSATION_TYPES = ("dc", "filter", "dc_rc")
RF_SEGMENT_LENGTH_MODES = ("fixed", "extend_by_rf_duration")
RF_PREDEFINED_COMPOSITE_TEMPLATES = ("custom", "cpmg", "udd", "hahn_echo")
MAX_QICK_OUTPUTS = 8
QICK_OUTPUT_BOARD_TYPES = ("RF_Out", "DC_Out")
QICK_INPUT_BOARD_TYPES = ("RF_In", "DC_In")
MEASUREMENT_REPRESENTATIONS = ("auto", "adc", "voltage", "current")


def _finite_real(value: Real, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _positive_real(value: Real, name: str) -> float:
    value = _finite_real(value, name)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def adc_iq_to_voltage(iq, calibration=None) -> np.ndarray:
    """Convert ADC I/Q values to volts using an optional fitted calibration.

    With no calibration, the legacy identity conversion is retained for old
    settings files and scripts.  A calibration object must provide
    ``convert_iq(values)`` and return the same final I/Q dimension.
    """
    values = np.asarray(iq, dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("ADC I/Q values must be finite")
    if calibration is None:
        return values
    converter = getattr(calibration, "convert_iq", None)
    if not callable(converter):
        raise TypeError("DC voltage calibration must provide convert_iq()")
    converted = np.asarray(converter(values), dtype=np.float64)
    if converted.shape != values.shape or not np.all(np.isfinite(converted)):
        raise ValueError("calibrated DC voltage I/Q has an invalid shape or value")
    return converted


def dc_iq_to_current(
    iq,
    gain_v_per_a: Real = DEFAULT_DC_MEASURE_GAIN_V_PER_A,
    calibration=None,
) -> np.ndarray:
    """Convert DC-input I/Q to amperes using calibrated ``voltage / gain``."""
    gain = _positive_real(gain_v_per_a, "DC measurement gain_v_per_a")
    return adc_iq_to_voltage(iq, calibration=calibration) / gain


def _nonnegative_real(value: Real, name: str) -> float:
    value = _finite_real(value, name)
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _positive_int(value: Integral, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer")
    value = int(value)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _bounded_int(value: Integral, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer")
    value = int(value)
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be in [{minimum}, {maximum}]")
    return value


def _identifier(value: str, fallback: str) -> str:
    text = re.sub(r"\W+", "_", str(value).strip())
    if not text:
        text = fallback
    if text[0].isdigit():
        text = f"_{text}"
    if keyword.iskeyword(text):
        text = f"{text}_channel"
    return text


def _unique_names(names: Sequence[str], fallback_prefix: str) -> Tuple[str, ...]:
    result = []
    used = set()
    for index, raw_name in enumerate(names):
        base = _identifier(raw_name, f"{fallback_prefix}_{index + 1}")
        name = base
        suffix = 2
        while name in used:
            name = f"{base}_{suffix}"
            suffix += 1
        used.add(name)
        result.append(name)
    return tuple(result)


@dataclass(frozen=True)
class WaveformInterval:
    """One interval in a piecewise-linear pulse."""

    index: int
    kind: str
    start_ns: float
    end_ns: float
    start_mv: float
    end_mv: float

    @property
    def duration_ns(self) -> float:
        return self.end_ns - self.start_ns


@dataclass(frozen=True)
class QickSweepSpec:
    """Optional amplitude sweep applied to one generated QICK SET segment."""

    segment_name: str
    output_name: str
    start: float
    stop: float
    count: int

    def __post_init__(self) -> None:
        if not str(self.segment_name):
            raise ValueError("segment_name must not be empty")
        if not str(self.output_name):
            raise ValueError("output_name must not be empty")
        start = _finite_real(self.start, "sweep start")
        stop = _finite_real(self.stop, "sweep stop")
        if not -1.0 <= start <= 1.0 or not -1.0 <= stop <= 1.0:
            raise ValueError("sweep endpoints must be inside [-1.0, 1.0]")
        _positive_int(self.count, "sweep count")

    @property
    def axis_kind(self) -> str:
        return "amplitude"

    @property
    def coordinate_unit(self) -> str:
        return "normalized"


@dataclass(frozen=True)
class QickRampRateSweepSpec:
    """Sweep one RAMP's duration while deriving its rate from adjacent SETs.

    ``start`` and ``stop`` are RAMP durations in microseconds.  The AWG target
    remains the following SET value, so every voltage-sweep point automatically
    receives the corresponding signed 24-bit RAMP step.
    """

    segment_name: str
    start: float
    stop: float
    count: int

    def __post_init__(self) -> None:
        if not str(self.segment_name):
            raise ValueError("RAMP segment_name must not be empty")
        _positive_real(self.start, "RAMP duration sweep start")
        _positive_real(self.stop, "RAMP duration sweep stop")
        _positive_int(self.count, "RAMP duration sweep count")

    @property
    def output_name(self) -> str:
        return "all_awg_outputs"

    @property
    def axis_kind(self) -> str:
        return "ramp_duration"

    @property
    def coordinate_unit(self) -> str:
        return "us"


@dataclass(frozen=True)
class QickHoldDurationSweepSpec:
    """Sweep one SET segment's hold duration in microseconds."""

    segment_name: str
    start: float
    stop: float
    count: int

    def __post_init__(self) -> None:
        if not str(self.segment_name):
            raise ValueError("SET segment_name must not be empty")
        _positive_real(self.start, "SET hold sweep start")
        _positive_real(self.stop, "SET hold sweep stop")
        _positive_int(self.count, "SET hold sweep count")

    @property
    def output_name(self) -> str:
        return "all_awg_outputs"

    @property
    def axis_kind(self) -> str:
        return "hold_duration"

    @property
    def coordinate_unit(self) -> str:
        return "us"


QickSweepAxisSpec = Union[
    QickSweepSpec,
    QickRampRateSweepSpec,
    QickHoldDurationSweepSpec,
]


def _coerce_sweep_specs(
    sweep: Optional[QickSweepAxisSpec],
    sweeps: Optional[Sequence[QickSweepAxisSpec]],
) -> Tuple[QickSweepAxisSpec, ...]:
    """Normalize legacy singular and Cartesian multi-sweep arguments."""
    if sweep is not None and sweeps is not None:
        raise ValueError("use either sweep or sweeps, not both")
    if sweeps is None:
        normalized = () if sweep is None else (sweep,)
    else:
        normalized = tuple(sweeps)
    allowed = (
        QickSweepSpec,
        QickRampRateSweepSpec,
        QickHoldDurationSweepSpec,
    )
    if any(not isinstance(item, allowed) for item in normalized):
        raise TypeError(
            "every sweep entry must be a QickSweepSpec, "
            "QickRampRateSweepSpec, or QickHoldDurationSweepSpec"
        )
    ramp_sweeps = [
        item for item in normalized if isinstance(item, QickRampRateSweepSpec)
    ]
    ramp_targets = [item.segment_name for item in ramp_sweeps]
    if len(set(ramp_targets)) != len(ramp_targets):
        raise ValueError("each RAMP segment may have only one duration/rate sweep")
    hold_sweeps = [
        item
        for item in normalized
        if isinstance(item, QickHoldDurationSweepSpec)
    ]
    hold_targets = [item.segment_name for item in hold_sweeps]
    if len(set(hold_targets)) != len(hold_targets):
        raise ValueError("each SET segment may have only one hold-duration sweep")
    targets = [
        (item.segment_name, item.output_name)
        for item in normalized
        if isinstance(item, QickSweepSpec)
    ]
    if len(set(targets)) != len(targets):
        raise ValueError("each (segment, output) sweep target must be unique")
    # Duration axes are deliberately outermost. RAMP axes remain first for
    # their established coefficient-table ordering; inner voltage combinations
    # use register adds without storing a full Cartesian point table.
    return tuple(ramp_sweeps) + tuple(hold_sweeps) + tuple(
        item for item in normalized if isinstance(item, QickSweepSpec)
    )


def _coerce_cross_capacitance(matrix, output_count: int) -> Tuple[Tuple[float, ...], ...]:
    if matrix is None:
        values = np.eye(output_count, dtype=float)
    else:
        values = np.asarray(matrix, dtype=float)
    expected_shape = (output_count, output_count)
    if values.shape != expected_shape:
        raise ValueError(
            f"cross-capacitance matrix shape must be {expected_shape}, "
            f"received {values.shape}"
        )
    if not np.all(np.isfinite(values)):
        raise ValueError("cross-capacitance coefficients must be finite")
    if not np.allclose(np.diag(values), 1.0, rtol=0.0, atol=1.0e-12):
        raise ValueError("cross-capacitance diagonal entries must equal 1")
    return tuple(tuple(float(value) for value in row) for row in values)


@dataclass(frozen=True)
class QickRfSweepAxisSpec:
    """Read-only RF sweep-axis view used by plotting and QCoDeS."""

    segment_name: str
    output_name: str
    gen_ch: int
    start: float
    stop: float
    count: int
    axis_kind: str
    coordinate_unit: str
    parameter_name: str = ""


@dataclass(frozen=True)
class QickRfSoftwareSweepAxisSpec:
    """RF template or named parameter varied by recompiling per coordinate.

    Unlike :class:`QickRfSweepAxisSpec`, this axis is intentionally excluded
    from the tProcessor Cartesian sweep.  CPMG/UDD pulse counts change the
    number of emitted RF commands, so every point must be compiled and run as
    a separate hardware acquisition.
    """

    segment_name: str
    output_name: str
    gen_ch: int
    start: float
    stop: float
    count: int
    axis_kind: str
    coordinate_unit: str
    parameter_name: str

    @property
    def points(self) -> np.ndarray:
        if self.axis_kind == "rf_amplitude" and self.coordinate_unit == "gain":
            values = np.rint(
                np.linspace(self.start, self.stop, self.count, dtype=np.float64)
            ).astype(np.int64)
            if np.unique(values).size != values.size:
                raise ValueError("RF amplitude sweep points must map to unique integer gain codes")
            return values
        if self.axis_kind == "rf_template_n":
            values = np.rint(
                np.linspace(self.start, self.stop, self.count, dtype=np.float64)
            ).astype(np.int64)
            if np.unique(values).size != values.size:
                raise ValueError(
                    "predefined RF N sweep points must map to unique integers"
                )
            if np.any(values < 1):
                raise ValueError("predefined RF N sweep values must be positive")
            return values
        return np.linspace(
            self.start,
            self.stop,
            self.count,
            dtype=np.float64,
        )


def build_predefined_composite_items(
    template: str,
    *,
    n_pulses: int,
    tau_us: Real,
    frequency_parameter: str,
    duration_parameter: str,
    gain: int = 20000,
    phase_degrees: Real = 0.0,
    amplitude_parameter: str = "",
    phase_parameter: str = "",
) -> Tuple["QickRfCompositeItemSpec", ...]:
    """Build CPMG, UDD, or Hahn echo pulse/delay entries.

    CPMG ``tau_us`` is the free-evolution interval; the edge intervals are
    ``tau/2``.  UDD ``tau_us`` is the complete free-evolution window and uses
    ``t_j = tau * sin^2(pi*j/(2*N+2))``.  RF pulse widths are represented by
    the independent named duration parameter and therefore add to these free
    evolution intervals.
    Hahn echo has one pi pulse between two ``tau/2`` delays, with ``tau_us``
    specifying its total free-evolution time.
    """
    template = str(template).strip().lower()
    if template not in {"cpmg", "udd", "hahn_echo"}:
        raise ValueError("predefined RF template must be 'cpmg', 'udd', or 'hahn_echo'")
    n_pulses = _positive_int(n_pulses, "predefined RF pulse count N")
    if template == "hahn_echo":
        n_pulses = 1
    tau_us = _positive_real(tau_us, "predefined RF tau_us")
    frequency_parameter = str(frequency_parameter).strip()
    duration_parameter = str(duration_parameter).strip()
    if not frequency_parameter:
        raise ValueError("predefined RF template requires a frequency parameter")
    if not duration_parameter:
        raise ValueError("predefined RF template requires a duration parameter")
    gain = _bounded_int(gain, "predefined RF gain", -32768, 32767)
    phase_degrees = _finite_real(
        phase_degrees,
        "predefined RF phase_degrees",
    )

    if template == "hahn_echo":
        free_intervals = [tau_us / 2.0, tau_us / 2.0]
        prefix = "Hahn"
    elif template == "cpmg":
        free_intervals = (
            [tau_us / 2.0]
            + [tau_us] * max(0, n_pulses - 1)
            + [tau_us / 2.0]
        )
        prefix = "CPMG"
    else:
        centers = [
            tau_us * sin(pi * index / (2.0 * n_pulses + 2.0)) ** 2
            for index in range(1, n_pulses + 1)
        ]
        free_intervals = (
            [centers[0]]
            + [
                centers[index] - centers[index - 1]
                for index in range(1, len(centers))
            ]
            + [tau_us - centers[-1]]
        )
        prefix = "UDD"

    items = []
    for pulse_index in range(n_pulses):
        items.append(QickRfCompositeItemSpec(
            kind="delay",
            name=f"{prefix}_delay_{pulse_index}",
            duration_us=float(free_intervals[pulse_index]),
        ))
        items.append(QickRfCompositeItemSpec(
            kind="pulse",
            name=f"{prefix}_X{pulse_index + 1}",
            duration_us=1.0,
            frequency_parameter=frequency_parameter,
            duration_parameter=duration_parameter,
            gain=gain,
            phase_degrees=phase_degrees,
            amplitude_parameter=amplitude_parameter,
            phase_parameter=phase_parameter,
        ))
    items.append(QickRfCompositeItemSpec(
        kind="delay",
        name=f"{prefix}_delay_{n_pulses}",
        duration_us=float(free_intervals[-1]),
    ))
    return tuple(items)


@dataclass(frozen=True)
class QickRfFrequencyParameterSpec:
    """Named RF frequency shared by composite pulses on one generator.

    A swept parameter is represented by one tProcessor DMEM table regardless
    of how many composite pulse entries reference it.
    """

    name: str
    frequency_mhz: float
    sweep_enabled: bool = False
    sweep_start_mhz: float = 50.0
    sweep_stop_mhz: float = 50.0
    sweep_count: int = 1

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None:
            raise ValueError(
                "RF frequency parameter names must be Python-style identifiers"
            )
        object.__setattr__(self, "name", name)
        _finite_real(self.frequency_mhz, f"RF frequency parameter {name}")
        if not isinstance(self.sweep_enabled, bool):
            raise TypeError("RF frequency parameter sweep_enabled must be bool")
        _finite_real(self.sweep_start_mhz, f"RF frequency parameter {name} start")
        _finite_real(self.sweep_stop_mhz, f"RF frequency parameter {name} stop")
        _positive_int(self.sweep_count, f"RF frequency parameter {name} count")


@dataclass(frozen=True)
class QickRfDurationParameterSpec:
    """Named duration shared by RF pulses, or by delays in their own namespace."""

    name: str
    duration_us: float
    sweep_enabled: bool = False
    sweep_start_us: float = 1.0
    sweep_stop_us: float = 1.0
    sweep_count: int = 1

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None:
            raise ValueError(
                "RF duration parameter names must be Python-style identifiers"
            )
        object.__setattr__(self, "name", name)
        _positive_real(self.duration_us, f"RF duration parameter {name}")
        if not isinstance(self.sweep_enabled, bool):
            raise TypeError("RF duration parameter sweep_enabled must be bool")
        _positive_real(self.sweep_start_us, f"RF duration parameter {name} start")
        _positive_real(self.sweep_stop_us, f"RF duration parameter {name} stop")
        _positive_int(self.sweep_count, f"RF duration parameter {name} count")

    @property
    def initial_duration_us(self) -> float:
        """Duration used by the first hardware-sweep point."""
        return float(self.sweep_start_us if self.sweep_enabled else self.duration_us)


@dataclass(frozen=True, eq=False)
class QickRfDelayParameterSpec(QickRfDurationParameterSpec):
    """Named nonnegative delay; zero denotes no free-evolution gap."""

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None:
            raise ValueError("RF delay parameter names must be Python-style identifiers")
        object.__setattr__(self, "name", name)
        _nonnegative_real(self.duration_us, f"RF delay parameter {name}")
        if not isinstance(self.sweep_enabled, bool):
            raise TypeError("RF delay parameter sweep_enabled must be bool")
        _nonnegative_real(self.sweep_start_us, f"RF delay parameter {name} start")
        _nonnegative_real(self.sweep_stop_us, f"RF delay parameter {name} stop")
        _positive_int(self.sweep_count, f"RF delay parameter {name} count")

    def __eq__(self, other):
        if not isinstance(other, QickRfDurationParameterSpec):
            return NotImplemented
        return asdict(self) == asdict(other)

    __hash__ = QickRfDurationParameterSpec.__hash__


@dataclass(frozen=True)
class QickRfAmplitudeParameterSpec:
    """Named gain code or calibrated dBm value, interpreted by the RF mode."""

    name: str
    value: float
    sweep_enabled: bool = False
    sweep_start: float = 20000.0
    sweep_stop: float = 20000.0
    sweep_count: int = 1

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None:
            raise ValueError("RF amplitude parameter names must be Python-style identifiers")
        object.__setattr__(self, "name", name)
        _finite_real(self.value, f"RF amplitude parameter {name}")
        if not isinstance(self.sweep_enabled, bool):
            raise TypeError("RF amplitude parameter sweep_enabled must be bool")
        _finite_real(self.sweep_start, f"RF amplitude parameter {name} start")
        _finite_real(self.sweep_stop, f"RF amplitude parameter {name} stop")
        _positive_int(self.sweep_count, f"RF amplitude parameter {name} count")

    @property
    def initial_value(self) -> float:
        return float(self.sweep_start if self.sweep_enabled else self.value)


@dataclass(frozen=True)
class QickRfPhaseParameterSpec:
    """Named RF phase in degrees, optionally swept on the host."""

    name: str
    phase_degrees: float
    sweep_enabled: bool = False
    sweep_start_degrees: float = 0.0
    sweep_stop_degrees: float = 0.0
    sweep_count: int = 1

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None:
            raise ValueError("RF phase parameter names must be Python-style identifiers")
        object.__setattr__(self, "name", name)
        _finite_real(self.phase_degrees, f"RF phase parameter {name}")
        if not isinstance(self.sweep_enabled, bool):
            raise TypeError("RF phase parameter sweep_enabled must be bool")
        _finite_real(self.sweep_start_degrees, f"RF phase parameter {name} start")
        _finite_real(self.sweep_stop_degrees, f"RF phase parameter {name} stop")
        _positive_int(self.sweep_count, f"RF phase parameter {name} count")

    @property
    def initial_phase_degrees(self) -> float:
        return float(self.sweep_start_degrees if self.sweep_enabled else self.phase_degrees)


def _manual_rf_gain(value: Real, label: str) -> int:
    value = _finite_real(value, label)
    if not value.is_integer():
        raise ValueError(f"{label} must be an integer gain code")
    return _bounded_int(int(value), label, -32768, 32767)


@dataclass(frozen=True)
class QickRfCompositeItemSpec:
    """One ordered pulse or delay in a composite RF output sequence."""

    kind: str
    name: str
    duration_us: float
    frequency_parameter: str = ""
    gain: int = 20000
    phase_degrees: float = 0.0
    power_calibration_enabled: bool = False
    power_calibration_database_path: str = ""
    power_calibration_run_id: int = 0
    target_output_power_dbm: float = -20.0
    duration_parameter: str = ""
    delay_parameter: str = ""
    amplitude_parameter: str = ""
    phase_parameter: str = ""

    def __post_init__(self) -> None:
        kind = str(self.kind).strip().lower()
        if kind not in {"pulse", "delay"}:
            raise ValueError("composite RF item kind must be 'pulse' or 'delay'")
        name = str(self.name).strip()
        if not name:
            raise ValueError("composite RF item name must not be empty")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "name", name)
        (_nonnegative_real if kind == "delay" else _positive_real)(
            self.duration_us, f"composite RF {kind} duration_us")
        _bounded_int(self.gain, "composite RF gain", -32768, 32767)
        _finite_real(self.phase_degrees, "composite RF phase_degrees")
        if not isinstance(self.power_calibration_enabled, bool):
            raise TypeError(
                "composite RF power_calibration_enabled must be bool"
            )
        _bounded_int(
            self.power_calibration_run_id,
            "composite RF power_calibration_run_id",
            0,
            (1 << 31) - 1,
        )
        _finite_real(
            self.target_output_power_dbm,
            "composite RF target_output_power_dbm",
        )
        if kind == "pulse" and not str(self.frequency_parameter).strip():
            raise ValueError("composite RF pulse requires a frequency parameter")
        if self.duration_parameter and not str(self.duration_parameter).isidentifier():
            raise ValueError("composite RF duration_parameter must be an identifier")
        if self.delay_parameter and not str(self.delay_parameter).isidentifier():
            raise ValueError("composite RF delay_parameter must be an identifier")
        if kind != "delay" and self.delay_parameter:
            raise ValueError("composite RF delay_parameter is available only for delays")
        for reference in ("amplitude_parameter", "phase_parameter"):
            value = getattr(self, reference)
            if value and not str(value).isidentifier():
                raise ValueError(f"composite RF {reference} must be an identifier")
            if value and kind != "pulse":
                raise ValueError(f"composite RF {reference} is available only for pulses")
        if kind == "delay" and self.power_calibration_enabled:
            raise ValueError("composite RF delay cannot use power calibration")
        if (
            self.power_calibration_enabled
            and not str(self.power_calibration_database_path).strip()
        ):
            raise ValueError(
                "composite RF calibrated pulse requires a calibration database"
            )


@dataclass(frozen=True)
class QickRfPulseEventSpec:
    """Resolved RF pulse event; delays have already become time offsets."""

    event_id: str
    name: str
    delay_us: float
    duration_us: float
    frequency_mhz: float
    frequency_parameter: str
    gain: int
    phase_degrees: float
    power_calibration_enabled: bool = False
    power_calibration_database_path: str = ""
    power_calibration_run_id: int = 0
    target_output_power_dbm: float = -20.0
    duration_parameter: str = ""
    preceding_duration_parameters: Tuple[str, ...] = ()


@dataclass(frozen=True)
class QickRfPulseSpec:
    """RF pulse and RF-board output attenuation/filter settings.

    ``delay_us`` is relative to the start of ``segment_name``.  Pulse duration
    is converted to the selected RF generator's fabric clock when the generated
    module receives ``soccfg``. ``fine_duration`` opts this entire RF port into
    DAC-sample duration resolution; the runtime derives that grid from ``soccfg``.
    """

    gen_ch: int
    segment_name: str
    delay_us: float
    duration_us: float
    frequency_mhz: float
    gain: int
    att1_db: float
    att2_db: float
    phase_degrees: float = 0.0
    nqz: int = 1
    require_within_segment: bool = True
    filter_type: str = "bypass"
    filter_cutoff: float = 2.5
    filter_bandwidth: float = 1.0
    output_board_type: str = "RF_Out"
    duration_sweep_enabled: bool = False
    duration_sweep_start_us: float = 1.0
    duration_sweep_stop_us: float = 1.0
    duration_sweep_count: int = 1
    segment_length_mode: str = "fixed"
    frequency_sweep_enabled: bool = False
    frequency_sweep_start_mhz: float = 50.0
    frequency_sweep_stop_mhz: float = 50.0
    frequency_sweep_count: int = 1
    power_sweep_enabled: bool = False
    power_sweep_start_dbm: float = -20.0
    power_sweep_stop_dbm: float = -20.0
    power_sweep_count: int = 1
    power_calibration_enabled: bool = False
    power_calibration_database_path: str = ""
    power_calibration_run_id: int = 0
    target_output_power_dbm: float = -20.0
    pulse_mode: str = "single"
    pulse_name: str = "RF pulse"
    frequency_parameters: Tuple[QickRfFrequencyParameterSpec, ...] = ()
    duration_parameters: Tuple[QickRfDurationParameterSpec, ...] = ()
    composite_items: Tuple[QickRfCompositeItemSpec, ...] = ()
    predefined_template: str = "custom"
    predefined_n: int = 4
    predefined_tau_us: float = 10.0
    predefined_frequency_parameter: str = "f0"
    predefined_duration_parameter: str = "d0"
    predefined_gain: int = 20000
    predefined_phase_degrees: float = 0.0
    predefined_n_sweep_enabled: bool = False
    predefined_n_sweep_start: int = 1
    predefined_n_sweep_stop: int = 4
    predefined_n_sweep_count: int = 4
    predefined_tau_sweep_enabled: bool = False
    predefined_tau_sweep_start_us: float = 1.0
    predefined_tau_sweep_stop_us: float = 10.0
    predefined_tau_sweep_count: int = 10
    delay_parameters: Tuple[QickRfDurationParameterSpec, ...] = ()
    t2_initial_pi2: bool = False
    t2_final_pi2: bool = False
    t2_frequency_parameter: str = "f0"
    t2_duration_parameter: str = "d0"
    t2_gain: int = 20000
    t2_initial_phase_degrees: float = 0.0
    t2_final_phase_degrees: float = 0.0
    global_frequency_parameter: str = ""
    global_gain: Optional[int] = None
    amplitude_parameters: Tuple[QickRfAmplitudeParameterSpec, ...] = ()
    phase_parameters: Tuple[QickRfPhaseParameterSpec, ...] = ()
    global_amplitude_mode: str = "legacy"
    global_amplitude_parameter: str = ""
    global_calibration_database_path: str = ""
    global_calibration_run_id: int = 0
    t2_amplitude_parameter: str = ""
    t2_initial_phase_parameter: str = ""
    t2_final_phase_parameter: str = ""
    predefined_amplitude_parameter: str = ""
    predefined_phase_parameter: str = ""
    fine_duration: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.fine_duration, bool):
            raise TypeError("RF fine_duration must be bool")
        pulse_mode = str(self.pulse_mode).strip().lower()
        if pulse_mode not in {"single", "composite"}:
            raise ValueError("RF pulse_mode must be 'single' or 'composite'")
        object.__setattr__(self, "pulse_mode", pulse_mode)
        pulse_name = str(self.pulse_name).strip()
        if not pulse_name:
            raise ValueError("RF pulse_name must not be empty")
        object.__setattr__(self, "pulse_name", pulse_name)
        parameters = tuple(
            item
            if isinstance(item, QickRfFrequencyParameterSpec)
            else QickRfFrequencyParameterSpec(**dict(item))
            for item in self.frequency_parameters
        )
        duration_parameters = tuple(
            item
            if isinstance(item, QickRfDurationParameterSpec) and not isinstance(item, QickRfDelayParameterSpec)
            else QickRfDurationParameterSpec(**(
                asdict(item) if isinstance(item, QickRfDelayParameterSpec) else dict(item)
            ))
            for item in self.duration_parameters
        )
        delay_parameters = tuple(
            item
            if isinstance(item, QickRfDurationParameterSpec)
            else QickRfDelayParameterSpec(**dict(item))
            for item in self.delay_parameters
        )
        amplitude_parameters = tuple(
            item if isinstance(item, QickRfAmplitudeParameterSpec)
            else QickRfAmplitudeParameterSpec(**dict(item))
            for item in self.amplitude_parameters
        )
        phase_parameters = tuple(
            item if isinstance(item, QickRfPhaseParameterSpec)
            else QickRfPhaseParameterSpec(**dict(item))
            for item in self.phase_parameters
        )
        items = tuple(
            item
            if isinstance(item, QickRfCompositeItemSpec)
            else QickRfCompositeItemSpec(**dict(item))
            for item in self.composite_items
        )
        predefined_template = str(self.predefined_template).strip().lower()
        if predefined_template not in RF_PREDEFINED_COMPOSITE_TEMPLATES:
            raise ValueError(
                "RF predefined_template must be custom, cpmg, udd, or hahn_echo"
            )
        object.__setattr__(self, "predefined_template", predefined_template)
        if predefined_template == "hahn_echo":
            object.__setattr__(self, "predefined_n", 1)
            object.__setattr__(self, "predefined_n_sweep_enabled", False)
        if pulse_mode == "composite" and any(
            item.kind == "pulse" and not item.duration_parameter
            for item in items
        ):
            used_names = {item.name for item in duration_parameters}
            migrated_items = []
            migrated_parameters = list(duration_parameters)
            next_index = 0
            for item in items:
                if item.kind != "pulse" or item.duration_parameter:
                    migrated_items.append(item)
                    continue
                while f"d{next_index}" in used_names:
                    next_index += 1
                parameter_name = f"d{next_index}"
                used_names.add(parameter_name)
                migrated_parameters.append(
                    QickRfDurationParameterSpec(
                        name=parameter_name,
                        duration_us=float(item.duration_us),
                        sweep_start_us=float(item.duration_us),
                        sweep_stop_us=float(item.duration_us),
                    )
                )
                migrated_items.append(
                    replace(item, duration_parameter=parameter_name)
                )
                next_index += 1
            duration_parameters = tuple(migrated_parameters)
            items = tuple(migrated_items)
        object.__setattr__(self, "frequency_parameters", parameters)
        object.__setattr__(self, "duration_parameters", duration_parameters)
        object.__setattr__(self, "delay_parameters", delay_parameters)
        object.__setattr__(self, "amplitude_parameters", amplitude_parameters)
        object.__setattr__(self, "phase_parameters", phase_parameters)
        amplitude_mode = str(self.global_amplitude_mode).strip().lower()
        if amplitude_mode not in {"legacy", "manual", "calibration"}:
            raise ValueError("global RF amplitude mode must be legacy, manual, or calibration")
        object.__setattr__(self, "global_amplitude_mode", amplitude_mode)
        for field_name in (
            "global_amplitude_parameter", "t2_amplitude_parameter",
            "t2_initial_phase_parameter", "t2_final_phase_parameter",
            "predefined_amplitude_parameter", "predefined_phase_parameter",
        ):
            reference = str(getattr(self, field_name)).strip()
            if reference and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", reference) is None:
                raise ValueError(f"{field_name} must be an identifier")
            object.__setattr__(self, field_name, reference)
        _bounded_int(self.global_calibration_run_id, "global RF calibration run ID", 0, (1 << 31) - 1)
        for collection, label in ((amplitude_parameters, "amplitude"), (phase_parameters, "phase")):
            names = tuple(parameter.name for parameter in collection)
            if len(set(names)) != len(names):
                raise ValueError(f"composite RF {label} parameter names must be unique")
        if amplitude_mode == "manual":
            for parameter in amplitude_parameters:
                _manual_rf_gain(parameter.value, f"RF amplitude parameter {parameter.name}")
                if parameter.sweep_enabled:
                    _manual_rf_gain(parameter.sweep_start, f"RF amplitude parameter {parameter.name} start")
                    _manual_rf_gain(parameter.sweep_stop, f"RF amplitude parameter {parameter.name} stop")
        global_frequency = str(self.global_frequency_parameter).strip()
        object.__setattr__(self, "global_frequency_parameter", global_frequency)
        if global_frequency and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", global_frequency) is None:
            raise ValueError("global RF frequency parameter must be an identifier")
        if pulse_mode == "composite" and global_frequency and global_frequency not in {item.name for item in parameters}:
            raise ValueError("global RF frequency references an unknown frequency parameter")
        if self.global_gain is not None:
            _bounded_int(self.global_gain, "global RF gain", -32768, 32767)
        for enabled, label in (
            (self.t2_initial_pi2, "T2 initial pi/2"),
            (self.t2_final_pi2, "T2 final pi/2"),
        ):
            if not isinstance(enabled, bool):
                raise TypeError(f"{label} enabled must be bool")
        _bounded_int(self.t2_gain, "T2 pi/2 gain", -32768, 32767)
        _finite_real(self.t2_initial_phase_degrees, "T2 initial pi/2 phase")
        _finite_real(self.t2_final_phase_degrees, "T2 final pi/2 phase")
        if self.t2_initial_pi2 or self.t2_final_pi2:
            if pulse_mode != "composite":
                raise ValueError("T2 pi/2 pulses require composite pulse mode")
            if not global_frequency and self.t2_frequency_parameter not in {item.name for item in parameters}:
                raise ValueError("T2 pi/2 references an unknown frequency parameter")
            if self.t2_duration_parameter not in {item.name for item in duration_parameters}:
                raise ValueError("T2 pi/2 references an unknown duration parameter")
        _positive_int(self.predefined_n, "predefined RF pulse count N")
        _positive_real(self.predefined_tau_us, "predefined RF tau_us")
        _bounded_int(self.predefined_gain, "predefined RF gain", -32768, 32767)
        _finite_real(
            self.predefined_phase_degrees,
            "predefined RF phase_degrees",
        )
        for enabled, label in (
            (self.predefined_n_sweep_enabled, "predefined RF N sweep"),
            (self.predefined_tau_sweep_enabled, "predefined RF tau sweep"),
        ):
            if not isinstance(enabled, bool):
                raise TypeError(f"{label} enabled must be bool")
        _positive_int(self.predefined_n_sweep_start, "predefined RF N start")
        _positive_int(self.predefined_n_sweep_stop, "predefined RF N stop")
        _positive_int(self.predefined_n_sweep_count, "predefined RF N count")
        _positive_real(
            self.predefined_tau_sweep_start_us,
            "predefined RF tau start",
        )
        _positive_real(
            self.predefined_tau_sweep_stop_us,
            "predefined RF tau stop",
        )
        _positive_int(
            self.predefined_tau_sweep_count,
            "predefined RF tau count",
        )
        if predefined_template != "custom":
            if pulse_mode != "composite":
                raise ValueError(
                    "predefined RF templates require composite pulse mode"
                )
            frequency_names = {item.name for item in parameters}
            duration_names = {item.name for item in duration_parameters}
            if not global_frequency and self.predefined_frequency_parameter not in frequency_names:
                raise ValueError(
                    "predefined RF template references an unknown frequency "
                    "parameter"
                )
            if self.predefined_duration_parameter not in duration_names:
                raise ValueError(
                    "predefined RF template references an unknown duration "
                    "parameter"
                )
            items = build_predefined_composite_items(
                predefined_template,
                n_pulses=int(self.predefined_n),
                tau_us=float(self.predefined_tau_us),
                frequency_parameter=str(self.predefined_frequency_parameter or global_frequency),
                duration_parameter=str(self.predefined_duration_parameter),
                gain=int(self.predefined_gain),
                phase_degrees=float(self.predefined_phase_degrees),
                amplitude_parameter=self.predefined_amplitude_parameter,
                phase_parameter=self.predefined_phase_parameter,
            )
        object.__setattr__(self, "composite_items", items)
        _bounded_int(self.gen_ch, "RF generator channel", 0, 1_000_000)
        if not str(self.segment_name):
            raise ValueError("RF segment_name must not be empty")
        _nonnegative_real(self.delay_us, "RF delay_us")
        _positive_real(self.duration_us, "RF duration_us")
        _finite_real(self.frequency_mhz, "RF frequency_mhz")
        _bounded_int(self.gain, "RF gain", -32768, 32767)
        for name, value in (("RF att1_db", self.att1_db), ("RF att2_db", self.att2_db)):
            value = _finite_real(value, name)
            if value < 0.0 or value > 31.75:
                raise ValueError(f"{name} must be in [0, 31.75] dB")
        _finite_real(self.phase_degrees, "RF phase_degrees")
        _bounded_int(self.nqz, "RF nqz", 1, 2)
        if not isinstance(self.require_within_segment, bool):
            raise TypeError("require_within_segment must be bool")
        if self.filter_type not in {"bypass", "lowpass", "highpass", "bandpass"}:
            raise ValueError(
                "RF output filter_type must be bypass, lowpass, highpass, or bandpass"
            )
        _nonnegative_real(self.filter_cutoff, "RF output filter_cutoff")
        _positive_real(self.filter_bandwidth, "RF output filter_bandwidth")
        if self.output_board_type not in QICK_OUTPUT_BOARD_TYPES:
            raise ValueError(
                f"output_board_type must be one of {QICK_OUTPUT_BOARD_TYPES}"
            )
        if not isinstance(self.duration_sweep_enabled, bool):
            raise TypeError("RF duration_sweep_enabled must be bool")
        _positive_real(
            self.duration_sweep_start_us,
            "RF duration_sweep_start_us",
        )
        _positive_real(
            self.duration_sweep_stop_us,
            "RF duration_sweep_stop_us",
        )
        _positive_int(self.duration_sweep_count, "RF duration_sweep_count")
        if self.segment_length_mode not in RF_SEGMENT_LENGTH_MODES:
            raise ValueError(
                "RF segment_length_mode must be one of "
                f"{RF_SEGMENT_LENGTH_MODES}"
            )
        if not isinstance(self.frequency_sweep_enabled, bool):
            raise TypeError("RF frequency_sweep_enabled must be bool")
        _finite_real(
            self.frequency_sweep_start_mhz,
            "RF frequency_sweep_start_mhz",
        )
        _finite_real(
            self.frequency_sweep_stop_mhz,
            "RF frequency_sweep_stop_mhz",
        )
        _positive_int(
            self.frequency_sweep_count,
            "RF frequency_sweep_count",
        )
        if not isinstance(self.power_sweep_enabled, bool):
            raise TypeError("RF power_sweep_enabled must be bool")
        _finite_real(self.power_sweep_start_dbm, "RF power_sweep_start_dbm")
        _finite_real(self.power_sweep_stop_dbm, "RF power_sweep_stop_dbm")
        _positive_int(self.power_sweep_count, "RF power_sweep_count")
        if not isinstance(self.power_calibration_enabled, bool):
            raise TypeError("RF power_calibration_enabled must be bool")
        _bounded_int(
            self.power_calibration_run_id,
            "RF power_calibration_run_id",
            0,
            (1 << 31) - 1,
        )
        _finite_real(
            self.target_output_power_dbm,
            "RF target_output_power_dbm",
        )
        if self.power_sweep_enabled and not self.power_calibration_enabled:
            raise ValueError(
                "RF power sweep requires calibrated output power"
            )
        if self.power_calibration_enabled:
            if self.output_board_type != "RF_Out":
                raise ValueError(
                    "RF output-power calibration requires an RF_Out board"
                )
            if not str(self.power_calibration_database_path).strip():
                raise ValueError(
                    "RF output-power calibration database path is required"
                )
        if pulse_mode == "composite":
            effective_items = self.effective_composite_items
            if not parameters:
                raise ValueError(
                    "composite RF mode requires at least one frequency parameter"
                )
            parameter_names = tuple(item.name for item in parameters)
            if len(set(parameter_names)) != len(parameter_names):
                raise ValueError("composite RF frequency parameter names must be unique")
            if not effective_items or not any(item.kind == "pulse" for item in effective_items):
                raise ValueError("composite RF mode requires at least one pulse item")
            item_names = tuple(item.name for item in items)
            if len(set(item_names)) != len(item_names):
                raise ValueError("composite RF item names must be unique")
            unknown = sorted({
                item.frequency_parameter
                for item in effective_items
                if item.kind == "pulse"
                and item.frequency_parameter not in parameter_names
            })
            if unknown:
                raise ValueError(
                    "composite RF pulse references unknown frequency parameter(s): "
                    + ", ".join(unknown)
                )
            duration_parameter_names = tuple(
                item.name for item in duration_parameters
            )
            if len(set(duration_parameter_names)) != len(duration_parameter_names):
                raise ValueError("composite RF duration parameter names must be unique")
            unknown_durations = sorted({
                item.duration_parameter
                for item in effective_items
                if item.kind == "pulse"
                and item.duration_parameter
                and item.duration_parameter not in duration_parameter_names
            })
            if unknown_durations:
                raise ValueError(
                    "composite RF pulse references unknown duration parameter(s): "
                    + ", ".join(unknown_durations)
                )
            delay_names = tuple(item.name for item in delay_parameters)
            if len(set(delay_names)) != len(delay_names):
                raise ValueError("composite RF delay parameter names must be unique")
            unknown_delays = sorted({
                item.delay_parameter
                for item in items
                if item.kind == "delay" and item.delay_parameter
                and item.delay_parameter not in delay_names
            })
            if unknown_delays:
                raise ValueError(
                    "composite RF delay references unknown delay parameter(s): "
                    + ", ".join(unknown_delays)
                )
            if self.duration_sweep_enabled:
                raise ValueError(
                    "legacy RF duration sweep is available only in single pulse mode"
                )
            if self.frequency_sweep_enabled:
                raise ValueError(
                    "use named frequency-parameter sweeps in composite pulse mode"
                )
            if self.power_sweep_enabled or self.power_calibration_enabled:
                raise ValueError(
                    "legacy calibrated RF power controls are available only "
                    "in single pulse mode; configure calibration per composite pulse"
                )
            if (
                self.output_board_type != "RF_Out"
                and any(item.power_calibration_enabled for item in effective_items)
            ):
                raise ValueError(
                    "composite RF output-power calibration requires an RF_Out board"
                )

        # Evaluate integer coordinates now so invalid duplicate N points fail
        # while settings are validated, before any hardware is contacted.
        for axis in self.software_sweep_axes:
            _ = axis.points

    @property
    def effective_att1_db(self) -> float:
        return float(self.att1_db) if self.output_board_type == "RF_Out" else 0.0

    @property
    def effective_att2_db(self) -> float:
        return float(self.att2_db) if self.output_board_type == "RF_Out" else 0.0

    @property
    def output_name(self) -> str:
        """Stable sweep-axis name used by QCoDeS and the 2-D map."""
        return f"rf_gen_{int(self.gen_ch)}"

    @property
    def effective_composite_items(self) -> Tuple[QickRfCompositeItemSpec, ...]:
        """Body and T2 endpoints with global overrides; stored rows stay intact."""
        items = tuple(self.composite_items)
        if self.pulse_mode != "composite":
            return items
        used_names = {item.name for item in items}

        def endpoint(name: str, phase: float, phase_parameter: str) -> QickRfCompositeItemSpec:
            unique_name = name
            suffix = 2
            while unique_name in used_names:
                unique_name = f"{name}_{suffix}"
                suffix += 1
            used_names.add(unique_name)
            pi_duration = next(
                parameter.initial_duration_us for parameter in self.duration_parameters
                if parameter.name == self.t2_duration_parameter
            )
            return QickRfCompositeItemSpec(
                kind="pulse", name=unique_name, duration_us=pi_duration / 2.0,
                frequency_parameter=self.global_frequency_parameter or self.t2_frequency_parameter,
                gain=self.t2_gain, phase_degrees=phase,
                amplitude_parameter=self.t2_amplitude_parameter,
                phase_parameter=phase_parameter,
            )

        initial = (endpoint("T2_initial_pi2", self.t2_initial_phase_degrees, self.t2_initial_phase_parameter),) if self.t2_initial_pi2 else ()
        final = (endpoint("T2_final_pi2", self.t2_final_phase_degrees, self.t2_final_phase_parameter),) if self.t2_final_pi2 else ()
        effective = initial + items + final
        amplitudes = {parameter.name: parameter for parameter in self.amplitude_parameters}
        phases = {parameter.name: parameter for parameter in self.phase_parameters}
        resolved_items = []
        for item in effective:
            if item.kind != "pulse":
                resolved_items.append(item)
                continue
            amplitude_name = self.global_amplitude_parameter or item.amplitude_parameter
            if amplitude_name and self.global_amplitude_mode == "legacy":
                raise ValueError("named RF amplitude parameters require manual or calibration amplitude mode")
            if amplitude_name and amplitude_name not in amplitudes:
                raise ValueError(f"composite RF pulse references unknown amplitude parameter: {amplitude_name}")
            if item.phase_parameter and item.phase_parameter not in phases:
                raise ValueError(f"composite RF pulse references unknown phase parameter: {item.phase_parameter}")
            changes = dict(
                frequency_parameter=self.global_frequency_parameter or item.frequency_parameter,
                amplitude_parameter=amplitude_name,
                phase_degrees=(phases[item.phase_parameter].initial_phase_degrees
                               if item.phase_parameter else item.phase_degrees),
            )
            amplitude_value = amplitudes[amplitude_name].initial_value if amplitude_name else None
            if self.global_amplitude_mode == "calibration":
                if not str(self.global_calibration_database_path).strip():
                    raise ValueError("global RF calibration database path is required")
                changes.update(
                    power_calibration_enabled=True,
                    power_calibration_database_path=self.global_calibration_database_path,
                    power_calibration_run_id=self.global_calibration_run_id,
                    target_output_power_dbm=(item.target_output_power_dbm
                                             if amplitude_value is None else amplitude_value),
                )
            elif self.global_amplitude_mode == "manual":
                changes.update(
                    gain=(_manual_rf_gain(amplitude_value, f"RF amplitude parameter {amplitude_name}")
                          if amplitude_value is not None else
                          item.gain if self.global_gain is None else self.global_gain),
                    power_calibration_enabled=False,
                )
            elif self.global_gain is not None:
                changes.update(gain=self.global_gain, power_calibration_enabled=False)
            resolved_items.append(replace(item, **changes))
        return tuple(resolved_items)

    def _composite_delay_us(self, item: QickRfCompositeItemSpec) -> float:
        if item.delay_parameter:
            return next(
                parameter.initial_duration_us for parameter in self.delay_parameters
                if parameter.name == item.delay_parameter
            )
        return float(item.duration_us)

    @property
    def t2_host_duration_parameter(self) -> str:
        """The pi duration is host-swept so both pi/2 widths follow exactly."""
        if self.pulse_mode == "composite" and (self.t2_initial_pi2 or self.t2_final_pi2):
            return self.t2_duration_parameter
        return ""

    @property
    def pulse_events(self) -> Tuple[QickRfPulseEventSpec, ...]:
        """Return ordered pulse events with interleaved delays resolved."""
        if self.pulse_mode == "single":
            return (
                QickRfPulseEventSpec(
                    event_id=f"rf_gen_{int(self.gen_ch)}_single",
                    name=self.pulse_name,
                    delay_us=float(self.delay_us),
                    duration_us=float(self.duration_us),
                    frequency_mhz=float(self.frequency_mhz),
                    frequency_parameter="",
                    gain=int(self.gain),
                    phase_degrees=float(self.phase_degrees),
                    power_calibration_enabled=bool(
                        self.power_calibration_enabled
                    ),
                    power_calibration_database_path=str(
                        self.power_calibration_database_path
                    ),
                    power_calibration_run_id=int(
                        self.power_calibration_run_id
                    ),
                    target_output_power_dbm=float(
                        self.target_output_power_dbm
                    ),
                    duration_parameter="",
                    preceding_duration_parameters=(),
                ),
            )

        parameters = {item.name: item for item in self.frequency_parameters}
        durations = {item.name: item for item in self.duration_parameters}
        offset_us = float(self.delay_us)
        pulse_index = 0
        preceding_duration_parameters = []
        events = []
        for item in self.effective_composite_items:
            if item.kind == "delay":
                offset_us += self._composite_delay_us(item)
                continue
            parameter = parameters[item.frequency_parameter]
            duration_parameter = durations.get(item.duration_parameter)
            duration_us = (
                duration_parameter.initial_duration_us
                if duration_parameter is not None else float(item.duration_us)
            )
            events.append(
                QickRfPulseEventSpec(
                    event_id=(
                        f"rf_gen_{int(self.gen_ch)}_composite_{pulse_index}"
                    ),
                    name=item.name,
                    delay_us=offset_us,
                    duration_us=float(duration_us),
                    frequency_mhz=float(parameter.frequency_mhz),
                    frequency_parameter=parameter.name,
                    gain=int(item.gain),
                    phase_degrees=float(item.phase_degrees),
                    power_calibration_enabled=bool(
                        item.power_calibration_enabled
                    ),
                    power_calibration_database_path=str(
                        item.power_calibration_database_path
                    ),
                    power_calibration_run_id=int(
                        item.power_calibration_run_id
                    ),
                    target_output_power_dbm=float(
                        item.target_output_power_dbm
                    ),
                    duration_parameter=item.duration_parameter,
                    preceding_duration_parameters=tuple(
                        preceding_duration_parameters
                    ),
                )
            )
            pulse_index += 1
            offset_us += float(duration_us)
            if item.duration_parameter:
                preceding_duration_parameters.append(item.duration_parameter)
        return tuple(events)

    @property
    def segment_extension_components_us(self) -> Tuple[float, ...]:
        """Composite timeline components added at the first sweep point."""
        if self.segment_length_mode != "extend_by_rf_duration":
            return ()
        if self.pulse_mode == "single":
            return (float(
                self.duration_sweep_start_us
                if self.duration_sweep_enabled
                else self.duration_us
            ),)
        durations = {item.name: item for item in self.duration_parameters}
        components = []
        if self.delay_us > 0.0:
            components.append(float(self.delay_us))
        components.extend(
            self._composite_delay_us(item)
            if item.kind == "delay"
            else float(
                durations[item.duration_parameter].initial_duration_us
                if item.duration_parameter else item.duration_us
            )
            for item in self.effective_composite_items
        )
        return tuple(component for component in components if component > 0.0)

    @property
    def segment_extension_duration_us(self) -> float:
        """Total RF timeline added to the anchor SET at the first point."""
        return float(sum(self.segment_extension_components_us))

    @property
    def duration_parameter_reference_counts(self) -> Tuple[Tuple[str, int], ...]:
        """Return sweep-extension multiplicities in stable parameter order."""
        if self.segment_length_mode != "extend_by_rf_duration":
            return ()
        if self.pulse_mode == "single":
            return (("", 1),) if self.duration_sweep_enabled else ()
        counts = {
            parameter.name: sum(
                1
                for item in self.effective_composite_items
                if item.kind == "pulse"
                and item.duration_parameter == parameter.name
            )
            for parameter in self.duration_parameters
            if parameter.sweep_enabled
            and parameter.name != self.t2_host_duration_parameter
        }
        return tuple(
            (parameter.name, counts[parameter.name])
            for parameter in self.duration_parameters
            if counts.get(parameter.name, 0) > 0
        )

    @property
    def start(self) -> float:
        return float(self.duration_sweep_start_us)

    @property
    def stop(self) -> float:
        return float(self.duration_sweep_stop_us)

    @property
    def count(self) -> int:
        return int(self.duration_sweep_count)

    @property
    def axis_kind(self) -> str:
        return "rf_duration"

    @property
    def coordinate_unit(self) -> str:
        return "us"

    @property
    def sweep_axes(self) -> Tuple[QickRfSweepAxisSpec, ...]:
        axes = []
        if self.pulse_mode == "composite":
            referenced_durations = {
                item.duration_parameter
                for item in self.effective_composite_items
                if item.kind == "pulse"
            }
            referenced_frequencies = {
                item.frequency_parameter
                for item in self.effective_composite_items
                if item.kind == "pulse"
            }
            for parameter in self.duration_parameters:
                if (
                    not parameter.sweep_enabled
                    or parameter.name not in referenced_durations
                    or parameter.name == self.t2_host_duration_parameter
                ):
                    continue
                axes.append(
                    QickRfSweepAxisSpec(
                        segment_name=self.segment_name,
                        output_name=(
                            f"{self.output_name}_{parameter.name}_duration"
                        ),
                        gen_ch=int(self.gen_ch),
                        start=float(parameter.sweep_start_us),
                        stop=float(parameter.sweep_stop_us),
                        count=int(parameter.sweep_count),
                        axis_kind="rf_duration",
                        coordinate_unit="us",
                        parameter_name=parameter.name,
                    )
                )
            for parameter in self.frequency_parameters:
                if (
                    not parameter.sweep_enabled
                    or parameter.name not in referenced_frequencies
                ):
                    continue
                axes.append(
                    QickRfSweepAxisSpec(
                        segment_name=self.segment_name,
                        output_name=(
                            f"{self.output_name}_{parameter.name}_frequency"
                        ),
                        gen_ch=int(self.gen_ch),
                        start=float(parameter.sweep_start_mhz),
                        stop=float(parameter.sweep_stop_mhz),
                        count=int(parameter.sweep_count),
                        axis_kind="rf_frequency",
                        coordinate_unit="MHz",
                        parameter_name=parameter.name,
                    )
                )
            return tuple(axes)
        if self.duration_sweep_enabled:
            axes.append(
                QickRfSweepAxisSpec(
                    segment_name=self.segment_name,
                    output_name=self.output_name,
                    gen_ch=int(self.gen_ch),
                    start=float(self.duration_sweep_start_us),
                    stop=float(self.duration_sweep_stop_us),
                    count=int(self.duration_sweep_count),
                    axis_kind="rf_duration",
                    coordinate_unit="us",
                )
            )
        if self.frequency_sweep_enabled:
            axes.append(
                QickRfSweepAxisSpec(
                    segment_name=self.segment_name,
                    output_name=f"{self.output_name}_frequency",
                    gen_ch=int(self.gen_ch),
                    start=float(self.frequency_sweep_start_mhz),
                    stop=float(self.frequency_sweep_stop_mhz),
                    count=int(self.frequency_sweep_count),
                    axis_kind="rf_frequency",
                    coordinate_unit="MHz",
                )
            )
        if self.power_sweep_enabled:
            axes.append(
                QickRfSweepAxisSpec(
                    segment_name=self.segment_name,
                    output_name=f"{self.output_name}_power",
                    gen_ch=int(self.gen_ch),
                    start=float(self.power_sweep_start_dbm),
                    stop=float(self.power_sweep_stop_dbm),
                    count=int(self.power_sweep_count),
                    axis_kind="rf_power",
                    coordinate_unit="dBm",
                )
            )
        return tuple(axes)

    @property
    def software_sweep_axes(self) -> Tuple[QickRfSoftwareSweepAxisSpec, ...]:
        """Return template and named-parameter axes run outside the tProcessor."""
        if self.pulse_mode != "composite":
            return ()
        axes = []
        if self.predefined_template != "custom" and self.predefined_n_sweep_enabled:
            axes.append(QickRfSoftwareSweepAxisSpec(
                segment_name=self.segment_name,
                output_name=f"{self.output_name}_{self.predefined_template}_N",
                gen_ch=int(self.gen_ch),
                start=float(self.predefined_n_sweep_start),
                stop=float(self.predefined_n_sweep_stop),
                count=int(self.predefined_n_sweep_count),
                axis_kind="rf_template_n",
                coordinate_unit="count",
                parameter_name="N",
            ))
        if self.predefined_template != "custom" and self.predefined_tau_sweep_enabled:
            axes.append(QickRfSoftwareSweepAxisSpec(
                segment_name=self.segment_name,
                output_name=(
                    f"{self.output_name}_{self.predefined_template}_tau"
                ),
                gen_ch=int(self.gen_ch),
                start=float(self.predefined_tau_sweep_start_us),
                stop=float(self.predefined_tau_sweep_stop_us),
                count=int(self.predefined_tau_sweep_count),
                axis_kind="rf_template_tau",
                coordinate_unit="us",
                parameter_name="tau",
            ))
        referenced_delays = {
            item.delay_parameter for item in self.composite_items
            if item.kind == "delay" and item.delay_parameter
        }
        for parameter in self.delay_parameters:
            if parameter.sweep_enabled and parameter.name in referenced_delays:
                axes.append(QickRfSoftwareSweepAxisSpec(
                    segment_name=self.segment_name,
                    output_name=f"{self.output_name}_{parameter.name}_delay",
                    gen_ch=int(self.gen_ch),
                    start=float(parameter.sweep_start_us),
                    stop=float(parameter.sweep_stop_us),
                    count=int(parameter.sweep_count),
                    axis_kind="rf_delay",
                    coordinate_unit="us",
                    parameter_name=parameter.name,
                ))
        for parameter in self.duration_parameters:
            if parameter.sweep_enabled and parameter.name == self.t2_host_duration_parameter:
                axes.append(QickRfSoftwareSweepAxisSpec(
                    segment_name=self.segment_name,
                    output_name=f"{self.output_name}_{parameter.name}_duration",
                    gen_ch=int(self.gen_ch),
                    start=float(parameter.sweep_start_us),
                    stop=float(parameter.sweep_stop_us),
                    count=int(parameter.sweep_count),
                    axis_kind="rf_t2_duration",
                    coordinate_unit="us",
                    parameter_name=parameter.name,
                ))
        effective_pulses = tuple(item for item in self.effective_composite_items if item.kind == "pulse")
        referenced_amplitudes = {item.amplitude_parameter for item in effective_pulses}
        for parameter in self.amplitude_parameters:
            if parameter.sweep_enabled and parameter.name in referenced_amplitudes:
                axes.append(QickRfSoftwareSweepAxisSpec(
                    segment_name=self.segment_name,
                    output_name=f"{self.output_name}_{parameter.name}_amplitude",
                    gen_ch=int(self.gen_ch),
                    start=float(parameter.sweep_start), stop=float(parameter.sweep_stop),
                    count=int(parameter.sweep_count), axis_kind="rf_amplitude",
                    coordinate_unit="gain" if self.global_amplitude_mode == "manual" else "dBm",
                    parameter_name=parameter.name,
                ))
        referenced_phases = {item.phase_parameter for item in effective_pulses}
        for parameter in self.phase_parameters:
            if parameter.sweep_enabled and parameter.name in referenced_phases:
                axes.append(QickRfSoftwareSweepAxisSpec(
                    segment_name=self.segment_name,
                    output_name=f"{self.output_name}_{parameter.name}_phase",
                    gen_ch=int(self.gen_ch),
                    start=float(parameter.sweep_start_degrees), stop=float(parameter.sweep_stop_degrees),
                    count=int(parameter.sweep_count), axis_kind="rf_phase",
                    coordinate_unit="deg", parameter_name=parameter.name,
                ))
        return tuple(axes)

    def with_duration_parameters(
        self, values: Mapping[str, Real],
    ) -> "QickRfPulseSpec":
        """Resolve a host-swept pi duration and its derived pi/2 endpoints."""
        unknown = set(values) - {parameter.name for parameter in self.duration_parameters}
        if unknown:
            raise ValueError("unknown RF duration parameter(s): " + ", ".join(sorted(unknown)))
        resolved = {
            name: _positive_real(value, f"RF duration parameter {name}")
            for name, value in values.items()
        }
        return replace(self, duration_parameters=tuple(
            replace(parameter, duration_us=resolved[parameter.name], sweep_enabled=False)
            if parameter.name in resolved else parameter
            for parameter in self.duration_parameters
        ))

    def with_delay_parameters(
        self, values: Mapping[str, Real],
    ) -> "QickRfPulseSpec":
        """Resolve named host-delay coordinates without changing hardware axes."""
        unknown = set(values) - {parameter.name for parameter in self.delay_parameters}
        if unknown:
            raise ValueError("unknown RF delay parameter(s): " + ", ".join(sorted(unknown)))
        resolved = {
            name: _nonnegative_real(value, f"RF delay parameter {name}")
            for name, value in values.items()
        }
        return replace(self, delay_parameters=tuple(
            QickRfDelayParameterSpec(**dict(asdict(parameter), duration_us=resolved[parameter.name], sweep_enabled=False))
            if parameter.name in resolved else parameter
            for parameter in self.delay_parameters
        ))

    def with_amplitude_parameters(
        self, values: Mapping[str, Real],
    ) -> "QickRfPulseSpec":
        """Resolve host amplitude coordinates in the selected common mode."""
        unknown = set(values) - {parameter.name for parameter in self.amplitude_parameters}
        if unknown:
            raise ValueError("unknown RF amplitude parameter(s): " + ", ".join(sorted(unknown)))
        return replace(self, amplitude_parameters=tuple(
            replace(parameter, value=_finite_real(values[parameter.name], f"RF amplitude parameter {parameter.name}"), sweep_enabled=False)
            if parameter.name in values else parameter
            for parameter in self.amplitude_parameters
        ))

    def with_phase_parameters(
        self, values: Mapping[str, Real],
    ) -> "QickRfPulseSpec":
        """Resolve host phase coordinates without changing frequency sweeps."""
        unknown = set(values) - {parameter.name for parameter in self.phase_parameters}
        if unknown:
            raise ValueError("unknown RF phase parameter(s): " + ", ".join(sorted(unknown)))
        return replace(self, phase_parameters=tuple(
            replace(parameter, phase_degrees=_finite_real(values[parameter.name], f"RF phase parameter {parameter.name}"), sweep_enabled=False)
            if parameter.name in values else parameter
            for parameter in self.phase_parameters
        ))

    def with_predefined_parameters(
        self,
        *,
        n_pulses: Optional[int] = None,
        tau_us: Optional[Real] = None,
    ) -> "QickRfPulseSpec":
        """Return one concrete template point for software execution."""
        if self.predefined_template == "custom":
            if n_pulses is not None or tau_us is not None:
                raise ValueError("custom RF sequence has no predefined parameters")
            return self
        return replace(
            self,
            predefined_n=(
                int(self.predefined_n) if n_pulses is None else int(n_pulses)
            ),
            predefined_tau_us=(
                float(self.predefined_tau_us)
                if tau_us is None
                else float(tau_us)
            ),
            predefined_n_sweep_enabled=False,
            predefined_tau_sweep_enabled=False,
        )


@dataclass(frozen=True)
class QickDdrReadoutSpec:
    """FIR-decimated DRAM capture settings; HWH selects the stored rate."""

    ro_ch: int
    segment_name: str
    delay_us: float
    samples_per_trigger: int
    readout_frequency_mhz: float = 0.0
    margin_input_samples: int = 1024
    address: int = 0
    force_overwrite: bool = False
    post_run_read_delay_seconds: float = 0.1
    attenuation_db: float = 20.0
    filter_type: str = "bypass"
    filter_cutoff: float = 2.5
    filter_bandwidth: float = 1.0
    input_board_type: str = "RF_In"
    dc_gain_db: float = 0.0
    dc_measure_mode: bool = False
    dc_measure_gain_v_per_a: float = DEFAULT_DC_MEASURE_GAIN_V_PER_A
    dc_voltage_calibration_enabled: bool = False
    dc_voltage_calibration_database_path: str = ""
    dc_voltage_calibration_run_id: int = 0
    measurement_representation: str = "auto"
    nqz: int = 1
    fpga_trigger_delay_samples: Optional[int] = None
    fpga_trigger_delay_us: Optional[float] = None
    dc_compensation_timing: str = "after_readout"

    def __post_init__(self) -> None:
        _bounded_int(self.ro_ch, "DDR readout channel", 0, 1_000_000)
        if self.dc_compensation_timing not in ("after_readout", "overlap_readout"):
            raise ValueError("dc_compensation_timing must be after_readout or overlap_readout")
        if not str(self.segment_name):
            raise ValueError("DDR segment_name must not be empty")
        _nonnegative_real(self.delay_us, "DDR delay_us")
        _positive_int(self.samples_per_trigger, "DDR samples_per_trigger")
        if self.fpga_trigger_delay_samples is not None:
            _bounded_int(
                self.fpga_trigger_delay_samples,
                "DDR fpga_trigger_delay_samples",
                0,
                (1 << 32) - 1,
            )
        if self.fpga_trigger_delay_us is not None:
            _nonnegative_real(
                self.fpga_trigger_delay_us,
                "DDR fpga_trigger_delay_us",
            )
        if (
            self.fpga_trigger_delay_samples is not None
            and self.fpga_trigger_delay_us is not None
        ):
            raise ValueError(
                "set only one of fpga_trigger_delay_samples and "
                "fpga_trigger_delay_us"
            )
        _finite_real(self.readout_frequency_mhz, "DDR readout_frequency_mhz")
        _bounded_int(self.nqz, "DDR readout nqz", 1, 2)
        _bounded_int(self.margin_input_samples, "DDR margin_input_samples", 0, 1 << 30)
        _bounded_int(self.address, "DDR address", 0, (1 << 63) - 1)
        if not isinstance(self.force_overwrite, bool):
            raise TypeError("force_overwrite must be bool")
        _nonnegative_real(
            self.post_run_read_delay_seconds,
            "DDR post_run_read_delay_seconds",
        )
        attenuation = _finite_real(self.attenuation_db, "RF input attenuation_db")
        if attenuation < 0.0 or attenuation > 31.75:
            raise ValueError("RF input attenuation_db must be in [0, 31.75] dB")
        if self.filter_type not in {"bypass", "lowpass", "highpass", "bandpass"}:
            raise ValueError(
                "RF input filter_type must be bypass, lowpass, highpass, or bandpass"
            )
        _nonnegative_real(self.filter_cutoff, "RF input filter_cutoff")
        _positive_real(self.filter_bandwidth, "RF input filter_bandwidth")
        if self.input_board_type not in QICK_INPUT_BOARD_TYPES:
            raise ValueError(
                f"input_board_type must be one of {QICK_INPUT_BOARD_TYPES}"
            )
        dc_gain = _finite_real(self.dc_gain_db, "DC input dc_gain_db")
        if dc_gain < -6.0 or dc_gain > 26.0:
            raise ValueError("DC input dc_gain_db must be in [-6, 26] dB")
        if not isinstance(self.dc_measure_mode, bool):
            raise TypeError("DC measure mode must be bool")
        _positive_real(
            self.dc_measure_gain_v_per_a,
            "DC measurement gain_v_per_a",
        )
        if self.dc_measure_mode and self.input_board_type != "DC_In":
            raise ValueError("DC measure mode requires the DC_In input board")
        if not isinstance(self.dc_voltage_calibration_enabled, bool):
            raise TypeError("DC voltage calibration enabled must be bool")
        _bounded_int(
            self.dc_voltage_calibration_run_id,
            "DC voltage calibration run_id",
            0,
            (1 << 31) - 1,
        )
        if self.dc_voltage_calibration_enabled:
            if self.input_board_type != "DC_In":
                raise ValueError("DC voltage calibration requires the DC_In input board")
            if not str(self.dc_voltage_calibration_database_path).strip():
                raise ValueError("DC voltage calibration database path must not be empty")
        if self.measurement_representation not in MEASUREMENT_REPRESENTATIONS:
            raise ValueError(
                "measurement_representation must be one of "
                f"{MEASUREMENT_REPRESENTATIONS}"
            )
        if (
            self.effective_measurement_representation != "adc"
            and self.input_board_type != "DC_In"
        ):
            raise ValueError(
                "voltage/current measurement representation requires DC_In"
            )

    @property
    def effective_attenuation_db(self) -> float:
        return float(self.attenuation_db) if self.input_board_type == "RF_In" else 0.0

    @property
    def effective_dc_gain_db(self) -> float:
        return float(self.dc_gain_db) if self.input_board_type == "DC_In" else 0.0

    @property
    def effective_measurement_representation(self) -> str:
        if self.measurement_representation != "auto":
            return self.measurement_representation
        if self.dc_measure_mode:
            return "current"
        if self.dc_voltage_calibration_enabled:
            return "voltage"
        return "adc"

    @property
    def measurement_unit(self) -> str:
        return {
            "adc": "ADC units",
            "voltage": "V",
            "current": "A",
        }[self.effective_measurement_representation]


@dataclass(frozen=True)
class QickSegmentSpec:
    """Dependency-free representation of a FineTuneSequence segment."""

    name: str
    kind: str
    amplitudes: Tuple[Optional[float], ...]
    duration_cycles: int


class PulseSequence:
    """Piecewise-linear voltage waveform using ns and mV internally.

    The point layout is ``SET, RAMP, SET, ...``.  Consequently, even-numbered
    intervals are flat SET intervals and odd-numbered intervals are ramps to
    the next SET level.  This is the same layout expected by FineTuneSequence.
    """

    def __init__(
        self,
        initial_voltage: Real = 0.0,
        initial_duration_ns: Real = DEFAULT_INITIAL_DURATION_NS,
    ) -> None:
        initial_voltage = _finite_real(initial_voltage, "initial_voltage")
        initial_duration_ns = _positive_real(initial_duration_ns, "initial_duration_ns")
        self.t = np.asarray([0.0, initial_duration_ns], dtype=float)
        self.v = np.asarray([initial_voltage, initial_voltage], dtype=float)
        self.v_bounds = (
            -DEFAULT_QICK_FULL_SCALE_MV,
            DEFAULT_QICK_FULL_SCALE_MV,
        )
        self.segment_names = ["set_0"]

    @property
    def duration_ns(self) -> float:
        return float(self.t[-1] - self.t[0])

    @property
    def set_count(self) -> int:
        return (len(self.t) + 1) // 2

    @staticmethod
    def _normalize_segment_name(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("segment name must be a string")
        name = value.strip()
        if not name:
            raise ValueError("segment name must not be empty")
        if "\n" in name or "\r" in name:
            raise ValueError("segment name must not contain line breaks")
        return name

    def _unused_default_segment_name(self, index: int) -> str:
        used = set(self.segment_names)
        base = f"set_{int(index)}"
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}_{suffix}"
            suffix += 1
        return candidate

    def _ensure_segment_names(self) -> None:
        """Keep display names aligned after legacy direct array edits."""
        names = list(getattr(self, "segment_names", ()))
        if len(names) > self.set_count:
            names = names[:self.set_count]
        self.segment_names = [
            self._normalize_segment_name(name) for name in names
        ]
        while len(self.segment_names) < self.set_count:
            self.segment_names.append(
                self._unused_default_segment_name(len(self.segment_names))
            )

    def segment_name(self, segment_index: int) -> str:
        self._ensure_segment_names()
        segment_index = int(segment_index)
        if not 0 <= segment_index < self.set_count:
            raise IndexError("segment index is out of range")
        return self.segment_names[segment_index]

    def rename_segment(self, segment_index: int, name: str) -> None:
        self._ensure_segment_names()
        segment_index = int(segment_index)
        if not 0 <= segment_index < self.set_count:
            raise IndexError("segment index is out of range")
        self.segment_names[segment_index] = self._normalize_segment_name(name)

    def copy(self) -> "PulseSequence":
        self._ensure_segment_names()
        duplicate = PulseSequence(float(self.v[0]), float(self.t[1] - self.t[0]))
        duplicate.t = self.t.copy()
        duplicate.v = self.v.copy()
        duplicate.v_bounds = tuple(self.v_bounds)
        duplicate.segment_names = list(self.segment_names)
        return duplicate

    def validate(self) -> None:
        if self.t.ndim != 1 or self.v.ndim != 1 or len(self.t) != len(self.v):
            raise ValueError("time and voltage arrays must be one-dimensional and equal length")
        if len(self.t) < 2 or len(self.t) % 2:
            raise ValueError("waveform must contain SET/RAMP/SET point pairs")
        if not np.all(np.isfinite(self.t)) or not np.all(np.isfinite(self.v)):
            raise ValueError("waveform points must be finite")
        if np.any(np.diff(self.t) <= 0):
            raise ValueError("waveform times must be strictly increasing")
        for index in range(0, len(self.t) - 1, 2):
            if not np.isclose(self.v[index], self.v[index + 1], rtol=0.0, atol=1.0e-12):
                raise ValueError(f"SET interval {index // 2} is not flat")
        self._ensure_segment_names()

    def _clip_voltage(self, value: Real) -> float:
        value = _finite_real(value, "voltage")
        return float(np.clip(value, self.v_bounds[0], self.v_bounds[1]))

    def edit_ramp(self, flat_idx: int, new_ramp: Real) -> bool:
        """Change the incoming ramp duration for one SET interval."""
        if flat_idx <= 0 or flat_idx >= len(self.t) - 1 or flat_idx % 2:
            return False
        try:
            new_ramp = _positive_real(new_ramp, "ramp duration")
        except (TypeError, ValueError):
            return False
        old_ramp = self.t[flat_idx] - self.t[flat_idx - 1]
        self.t[flat_idx:] += new_ramp - old_ramp
        return True

    def edit_flat(self, flat_idx: int, new_flat: Real) -> bool:
        """Change one SET hold duration and shift all following intervals."""
        if flat_idx < 0 or flat_idx >= len(self.t) - 1 or flat_idx % 2:
            return False
        try:
            new_flat = _positive_real(new_flat, "flat duration")
        except (TypeError, ValueError):
            return False
        old_flat = self.t[flat_idx + 1] - self.t[flat_idx]
        self.t[flat_idx + 1:] += new_flat - old_flat
        return True

    def edit_voltage(self, flat_idx: int, new_v: Real) -> bool:
        """Change one SET level, preserving adjacent automatic ramps."""
        if flat_idx < 0 or flat_idx >= len(self.v) - 1 or flat_idx % 2:
            return False
        self.v[flat_idx:flat_idx + 2] = self._clip_voltage(new_v)
        return True

    def add_flat_ramp(self, ramp: Real, flat: Real, target_v: Real) -> None:
        """Append a ramp followed by a flat SET interval."""
        ramp = _positive_real(ramp, "ramp duration")
        flat = _positive_real(flat, "flat duration")
        target_v = self._clip_voltage(target_v)
        self._ensure_segment_names()
        new_name = self._unused_default_segment_name(self.set_count)
        t0 = float(self.t[-1])
        self.t = np.append(self.t, [t0 + ramp, t0 + ramp + flat])
        self.v = np.append(self.v, [target_v, target_v])
        self.segment_names.append(new_name)

    def flat_segments(self) -> Tuple[Tuple[int, int], ...]:
        return tuple((index, index + 1) for index in range(0, len(self.t) - 1, 2))

    def intervals(self) -> Tuple[WaveformInterval, ...]:
        self.validate()
        return tuple(
            WaveformInterval(
                index=index,
                kind="set" if index % 2 == 0 else "ramp",
                start_ns=float(self.t[index]),
                end_ns=float(self.t[index + 1]),
                start_mv=float(self.v[index]),
                end_mv=float(self.v[index + 1]),
            )
            for index in range(len(self.t) - 1)
        )

    def update_flat(self, rng: Tuple[int, int], new_v: Real) -> None:
        i0, _ = rng
        if not self.edit_voltage(i0, new_v):
            raise ValueError("invalid SET interval")

    def update_point(self, rng: Tuple[int, int], new_t: Real) -> None:
        """Move one boundary while retaining all following interval lengths."""
        i0, _ = rng
        if i0 == 0:
            return
        new_t = _finite_real(new_t, "time")
        new_t = max(new_t, float(self.t[i0 - 1]) + DEFAULT_MIN_DURATION_NS)
        delta = new_t - float(self.t[i0])
        self.t[i0:] += delta

    def delete_flat_ramp(self, flat_idx: int) -> bool:
        """Delete one noninitial SET and its incoming ramp."""
        if flat_idx <= 0 or flat_idx + 1 >= len(self.t) or flat_idx % 2:
            return False
        self._ensure_segment_names()
        del self.segment_names[flat_idx // 2]
        shrink = self.t[flat_idx + 1] - self.t[flat_idx - 1]
        self.t = np.delete(self.t, [flat_idx, flat_idx + 1])
        self.v = np.delete(self.v, [flat_idx, flat_idx + 1])
        if flat_idx < len(self.t):
            self.t[flat_idx:] -= shrink
        return True

    def insert_flat_ramp(
        self,
        flat_idx: int,
        ramp_ns: Real = DEFAULT_INSERT_RAMP_NS,
        flat_ns: Real = DEFAULT_INSERT_FLAT_NS,
    ) -> bool:
        """Insert an editable SET and incoming ramp before ``flat_idx``."""
        if flat_idx < 2 or flat_idx > len(self.t) or flat_idx % 2:
            return False
        ramp_ns = _positive_real(ramp_ns, "ramp_ns")
        flat_ns = _positive_real(flat_ns, "flat_ns")
        self._ensure_segment_names()
        segment_index = flat_idx // 2
        new_name = self._unused_default_segment_name(segment_index)
        target_v = float(self.v[flat_idx - 1])
        t0 = float(self.t[flat_idx - 1])
        self.t[flat_idx:] += ramp_ns + flat_ns
        self.t = np.insert(self.t, flat_idx, [t0 + ramp_ns, t0 + ramp_ns + flat_ns])
        self.v = np.insert(self.v, flat_idx, [target_v, target_v])
        self.segment_names.insert(segment_index, new_name)
        return True

    def to_dict(self) -> dict:
        self._ensure_segment_names()
        return {
            "time_ns": self.t.tolist(),
            "voltage_mv": self.v.tolist(),
            "voltage_bounds_mv": list(self.v_bounds),
            "segment_names": list(self.segment_names),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PulseSequence":
        pulse = cls()
        pulse.t = np.asarray(data["time_ns"], dtype=float)
        pulse.v = np.asarray(data["voltage_mv"], dtype=float)
        if "voltage_bounds_mv" in data:
            bounds = tuple(float(item) for item in data["voltage_bounds_mv"])
            if len(bounds) != 2 or bounds[0] >= bounds[1]:
                raise ValueError("voltage_bounds_mv must contain increasing min/max values")
            pulse.v_bounds = bounds
        if "segment_names" in data:
            names = data["segment_names"]
            if not isinstance(names, list):
                raise TypeError("segment_names must be a JSON array")
            if len(names) != pulse.set_count:
                raise ValueError(
                    "segment_names must contain one name per SET segment"
                )
            pulse.segment_names = [
                pulse._normalize_segment_name(name) for name in names
            ]
        else:
            pulse.segment_names = []
        pulse.validate()
        return pulse

    def to_qcs_dcwaveform(self, ch_name: str) -> str:
        """Return QCS statements for this channel (legacy-compatible API)."""
        return _qcs_channel_code(self, _identifier(ch_name, "dc_ch"))


def _normalize_mv(value_mv: Real, full_scale_mv: Real) -> float:
    value_mv = _finite_real(value_mv, "voltage_mv")
    full_scale_mv = _positive_real(full_scale_mv, "full_scale_mv")
    normalized = value_mv / full_scale_mv
    if normalized < -1.0 - 1.0e-12 or normalized > 1.0 + 1.0e-12:
        raise ValueError(
            f"voltage {value_mv:g} mV exceeds configured QICK full scale "
            f"+/-{full_scale_mv:g} mV"
        )
    return float(np.clip(normalized, -1.0, 1.0))


def _cycles_from_ns(duration_ns: Real, fabric_mhz: Real) -> int:
    duration_ns = _positive_real(duration_ns, "duration_ns")
    fabric_mhz = _positive_real(fabric_mhz, "fabric_mhz")
    return max(1, int(ceil(duration_ns * fabric_mhz / 1000.0)))


def _validate_aligned_pulses(pulses: Sequence[PulseSequence]) -> None:
    if not pulses:
        raise ValueError("at least one pulse is required")
    if len(pulses) > MAX_QICK_OUTPUTS:
        raise ValueError(f"QICK supports at most {MAX_QICK_OUTPUTS} AWG tuning outputs")
    reference = pulses[0].t
    for index, pulse in enumerate(pulses):
        pulse.validate()
        if pulse.t.shape != reference.shape or not np.allclose(
            pulse.t, reference, rtol=0.0, atol=1.0e-9
        ):
            raise ValueError(
                "QICK export requires all ports to use the same SET/RAMP timing; "
                f"port {index + 1} does not match port 1"
            )


def transform_virtual_waveforms(
    pulses: Sequence[PulseSequence],
    cross_capacitance=None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return aligned virtual and physical waveforms in millivolts.

    The configured GUI traces are virtual-gate voltages.  The values sent to
    the AWG outputs are physical voltages computed point-by-point as
    ``physical = cross_capacitance @ virtual``.  Rows identify physical AWG
    outputs and columns identify virtual gates.  A union time grid preserves
    transitions from ports whose editable timing grids are not yet aligned.
    """
    pulses = tuple(pulses)
    if not pulses:
        raise ValueError("at least one pulse is required")
    for pulse in pulses:
        pulse.validate()
    matrix = np.asarray(
        _coerce_cross_capacitance(cross_capacitance, len(pulses)),
        dtype=float,
    )
    time_ns = np.unique(np.concatenate([pulse.t for pulse in pulses])).astype(
        float, copy=False
    )
    virtual_mv = np.vstack(
        [np.interp(time_ns, pulse.t, pulse.v) for pulse in pulses]
    )
    physical_mv = matrix @ virtual_mv
    return time_ns, virtual_mv, physical_mv


def qick_set_segment_names(pulse: PulseSequence) -> Tuple[str, ...]:
    pulse.validate()
    return tuple(f"set_{index}" for index in range(pulse.set_count))


def make_qick_segment_specs(
    pulses: Sequence[PulseSequence],
    *,
    fabric_mhz: Real = DEFAULT_QICK_FABRIC_MHZ,
    full_scale_mv: Real = DEFAULT_QICK_FULL_SCALE_MV,
) -> Tuple[QickSegmentSpec, ...]:
    """Convert aligned GUI pulses into dependency-free QICK segment specs."""
    pulses = tuple(pulses)
    _validate_aligned_pulses(pulses)
    fabric_mhz = _positive_real(fabric_mhz, "fabric_mhz")
    full_scale_mv = _positive_real(full_scale_mv, "full_scale_mv")
    specs = []
    for interval_index in range(len(pulses[0].t) - 1):
        duration_ns = pulses[0].t[interval_index + 1] - pulses[0].t[interval_index]
        duration_cycles = _cycles_from_ns(duration_ns, fabric_mhz)
        if interval_index % 2 == 0:
            set_index = interval_index // 2
            amplitudes = tuple(
                _normalize_mv(pulse.v[interval_index], full_scale_mv) for pulse in pulses
            )
            specs.append(QickSegmentSpec(f"set_{set_index}", "set", amplitudes, duration_cycles))
        else:
            ramp_index = interval_index // 2
            specs.append(
                QickSegmentSpec(
                    f"ramp_{ramp_index}_to_{ramp_index + 1}",
                    "ramp",
                    (None,) * len(pulses),
                    duration_cycles,
                )
            )
    return tuple(specs)


def build_qick_sequence(
    pulses: Sequence[PulseSequence],
    *,
    output_names: Optional[Sequence[str]] = None,
    fabric_mhz: Real = DEFAULT_QICK_FABRIC_MHZ,
    full_scale_mv: Real = DEFAULT_QICK_FULL_SCALE_MV,
    output_full_scales_mv=None,
    dac_current_settings=None,
    sweep: Optional[QickSweepAxisSpec] = None,
    sweeps: Optional[Sequence[QickSweepAxisSpec]] = None,
    rf_pulse_specs: Optional[Sequence[QickRfPulseSpec]] = None,
    cross_capacitance=None,
    bias_t_compensation_enabled: bool = False,
    bias_t_compensation_type: str = "dc",
    bias_t_compensation_voltage_mv: Optional[Real] = None,
    bias_t_compensation_mode: str = "fixed_voltage",
    bias_t_compensation_duration_us: Real = DEFAULT_BIAS_T_COMPENSATION_DURATION_US,
    bias_t_filter_tau_us: Real = DEFAULT_BIAS_T_FILTER_TAU_US,
    validate_rc_range: bool = True,
):
    """Build a real qick_fine_tune_sweep.FineTuneSequence instance."""
    pulses = tuple(pulses)
    if output_names is None:
        output_names = tuple(f"awg_{index}" for index in range(len(pulses)))
    output_names = _unique_names(tuple(output_names), "awg")
    if len(output_names) != len(pulses):
        raise ValueError("output_names length must match the pulse count")
    full_scale_mv = _positive_real(full_scale_mv, "full_scale_mv")
    specs = make_qick_segment_specs(
        pulses, fabric_mhz=fabric_mhz, full_scale_mv=full_scale_mv
    )

    from qick_fine_tune_sweep import FineTuneSequence

    sequence = FineTuneSequence(output_names)
    if output_full_scales_mv is not None:
        sequence.set_voltage_scales(full_scale_mv, output_full_scales_mv)
    sequence.dac_current_settings = dict(dac_current_settings or {})
    sequence.set_cross_capacitance(
        _coerce_cross_capacitance(cross_capacitance, len(output_names))
    )
    if not isinstance(bias_t_compensation_enabled, (bool, np.bool_)):
        raise TypeError("bias_t_compensation_enabled must be boolean")
    if bias_t_compensation_type not in BIAS_T_COMPENSATION_TYPES:
        raise ValueError(
            "bias_t_compensation_type must be one of "
            f"{BIAS_T_COMPENSATION_TYPES}"
        )
    if bias_t_compensation_voltage_mv is None:
        bias_t_compensation_voltage_mv = (
            full_scale_mv * DEFAULT_BIAS_T_COMPENSATION_FRACTION
        )
    compensation_mv = _positive_real(
        bias_t_compensation_voltage_mv,
        "bias_t_compensation_voltage_mv",
    )
    if compensation_mv > full_scale_mv:
        raise ValueError("Bias-T compensation voltage exceeds QICK full scale")
    if bias_t_compensation_mode not in BIAS_T_COMPENSATION_MODES:
        raise ValueError(
            f"bias_t_compensation_mode must be one of {BIAS_T_COMPENSATION_MODES}"
        )
    compensation_duration_us = _positive_real(
        bias_t_compensation_duration_us,
        "bias_t_compensation_duration_us",
    )
    compensation_duration_cycles = _cycles_from_ns(
        compensation_duration_us * 1000.0,
        fabric_mhz,
    )
    filter_tau_us = _positive_real(
        bias_t_filter_tau_us,
        "bias_t_filter_tau_us",
    )
    sequence.set_rc_compensation(
        filter_tau_us,
        enabled=bool(bias_t_compensation_enabled and bias_t_compensation_type in ("filter", "dc_rc")),
    )
    sequence.set_bias_t_compensation(
        compensation_mv / full_scale_mv,
        enabled=bool(bias_t_compensation_enabled and bias_t_compensation_type in ("dc", "dc_rc")),
        mode=bias_t_compensation_mode,
        fixed_duration_cycles=compensation_duration_cycles if bias_t_compensation_mode == "fixed_time" else None,
    )
    for spec in specs:
        if spec.kind == "set":
            sequence.add_set(spec.name, spec.amplitudes, spec.duration_cycles)
        else:
            sequence.add_ramp(spec.name, spec.duration_cycles)
    for sweep_spec in _coerce_sweep_specs(sweep, sweeps):
        if isinstance(sweep_spec, QickRampRateSweepSpec):
            sequence.add_ramp_duration_sweep(
                segment=sweep_spec.segment_name,
                start_us=sweep_spec.start,
                stop_us=sweep_spec.stop,
                count=sweep_spec.count,
                sequence_fabric_mhz=fabric_mhz,
            )
        elif isinstance(sweep_spec, QickHoldDurationSweepSpec):
            sequence.add_hold_duration_sweep(
                segment=sweep_spec.segment_name,
                start_us=sweep_spec.start,
                stop_us=sweep_spec.stop,
                count=sweep_spec.count,
                sequence_fabric_mhz=fabric_mhz,
            )
        else:
            sequence.add_amplitude_sweep(
                segment=sweep_spec.segment_name,
                output=sweep_spec.output_name,
                start=sweep_spec.start,
                stop=sweep_spec.stop,
                count=sweep_spec.count,
            )
    normalized_rf_specs = tuple(rf_pulse_specs or ())
    if any(not isinstance(spec, QickRfPulseSpec) for spec in normalized_rf_specs):
        raise TypeError("every RF pulse entry must be a QickRfPulseSpec")
    for rf_spec in normalized_rf_specs:
        if rf_spec.segment_length_mode != "extend_by_rf_duration":
            continue
        base_extension_cycles = sum(
            _cycles_from_ns(duration_us * 1000.0, fabric_mhz)
            for duration_us in rf_spec.segment_extension_components_us
        )
        sequence.set_rf_segment_length_extension(
            segment=rf_spec.segment_name,
            gen_ch=rf_spec.gen_ch,
            base_duration_cycles=base_extension_cycles,
            parameter_multiplicities=dict(
                rf_spec.duration_parameter_reference_counts
            ),
        )
    for rf_spec in normalized_rf_specs:
        for duration_axis in (
            axis
            for axis in rf_spec.sweep_axes
            if axis.axis_kind == "rf_duration"
        ):
            sequence.add_rf_duration_sweep(
                segment=rf_spec.segment_name,
                gen_ch=rf_spec.gen_ch,
                start_us=duration_axis.start,
                stop_us=duration_axis.stop,
                count=duration_axis.count,
                segment_length_mode=rf_spec.segment_length_mode,
                sequence_fabric_mhz=fabric_mhz,
                parameter_name=duration_axis.parameter_name,
                output_name=duration_axis.output_name,
            )
        for frequency_axis in (
            axis
            for axis in rf_spec.sweep_axes
            if axis.axis_kind == "rf_frequency"
        ):
            sequence.add_rf_frequency_sweep(
                segment=rf_spec.segment_name,
                gen_ch=rf_spec.gen_ch,
                start_mhz=frequency_axis.start,
                stop_mhz=frequency_axis.stop,
                count=frequency_axis.count,
                parameter_name=frequency_axis.parameter_name,
                output_name=frequency_axis.output_name,
            )
        if rf_spec.power_sweep_enabled:
            sequence.add_rf_power_sweep(
                segment=rf_spec.segment_name,
                gen_ch=rf_spec.gen_ch,
                start_dbm=rf_spec.power_sweep_start_dbm,
                stop_dbm=rf_spec.power_sweep_stop_dbm,
                count=rf_spec.power_sweep_count,
            )
    sequence._validate()
    from qick_rc_validation import validate_sequence_rc_range, validate_channel_voltage_ranges
    validate_channel_voltage_ranges(sequence)
    sequence.output_full_scale_mv = float(full_scale_mv)
    # The display may show an out-of-range RC curve; execution/export retain
    # the default preflight and the compiler also checks actual DAC words.
    sequence.rc_output_range_preview = (validate_sequence_rc_range(
        sequence, float(fabric_mhz), float(full_scale_mv)) if validate_rc_range else ())
    return sequence


def _qcs_channel_code(pulse: PulseSequence, channel_name: str) -> str:
    pulse.validate()
    return _qcs_channel_samples_code(pulse.t, pulse.v, channel_name)


def _qcs_channel_samples_code(time_ns, voltage_mv, channel_name: str) -> str:
    """Generate QCS segments from an arbitrary piecewise-linear trace."""
    time_values = np.asarray(time_ns, dtype=float)
    voltage_values = np.asarray(voltage_mv, dtype=float)
    if (
        time_values.ndim != 1
        or voltage_values.shape != time_values.shape
        or time_values.size < 2
    ):
        raise ValueError("QCS time and voltage traces must be equal-length vectors")
    if not np.all(np.isfinite(time_values)) or not np.all(np.isfinite(voltage_values)):
        raise ValueError("QCS waveform points must be finite")
    if np.any(np.diff(time_values) <= 0.0):
        raise ValueError("QCS waveform times must be strictly increasing")

    lines = []
    for index in range(time_values.size - 1):
        duration_name = f"{channel_name}_dc_segment_duration_{index}"
        duration_ns = float(time_values[index + 1] - time_values[index])
        lines.extend(
            [
                f"    {duration_name} = qcs.Scalar(",
                f"        name={duration_name!r},",
                f"        value={duration_ns:.12g} * ns,",
                "        dtype=float,",
                "    )",
            ]
        )
    for index in range(time_values.size - 1):
        duration_name = f"{channel_name}_dc_segment_duration_{index}"
        waveform_name = f"{channel_name}_dc_segment_{index}"
        start_mv = float(voltage_values[index])
        end_mv = float(voltage_values[index + 1])
        if np.isclose(start_mv, end_mv, rtol=0.0, atol=1.0e-12):
            lines.extend(
                [
                    f"    {waveform_name} = qcs.DCWaveform(",
                    f"        duration={duration_name},",
                    "        envelope=qcs.ConstantEnvelope(),",
                    f"        amplitude={start_mv:.12g} * mV,",
                    "    )",
                    "",
                ]
            )
        else:
            peak_mv = max(abs(start_mv), abs(end_mv))
            if peak_mv == 0:
                start_shape = end_shape = 0.0
            else:
                start_shape = start_mv / peak_mv
                end_shape = end_mv / peak_mv
            lines.extend(
                [
                    f"    {waveform_name} = qcs.DCWaveform(",
                    f"        duration={duration_name},",
                    "        envelope=qcs.ArbitraryEnvelope(",
                    f"            [0.0, 1.0], [{start_shape:.12g}, {end_shape:.12g}],",
                    "        ),",
                    f"        amplitude={peak_mv:.12g} * mV,",
                    "    )",
                    "",
                ]
            )
    for index in range(time_values.size - 1):
        lines.append(
            f"    program.add_waveform({channel_name}_dc_segment_{index}, {channel_name})"
        )
    lines.append("")
    return "\n".join(lines)


def generate_qcs_program_code(
    pulses: Sequence[PulseSequence],
    *,
    channel_names: Optional[Sequence[str]] = None,
    full_scale_v: Real = DEFAULT_QCS_FULL_SCALE_V,
    cross_capacitance=None,
) -> str:
    """Generate Keysight QCS code for physical, cross-compensated outputs."""
    pulses = tuple(pulses)
    if not pulses:
        raise ValueError("at least one pulse is required")
    full_scale_v = _positive_real(full_scale_v, "full_scale_v")
    if channel_names is None:
        channel_names = tuple(f"dc_ch_{index + 1}" for index in range(len(pulses)))
    channel_names = _unique_names(tuple(channel_names), "dc_ch")
    if len(channel_names) != len(pulses):
        raise ValueError("channel_names length must match the pulse count")
    matrix = _coerce_cross_capacitance(cross_capacitance, len(pulses))
    if np.allclose(matrix, np.eye(len(pulses)), rtol=0.0, atol=1.0e-12):
        traces = tuple((pulse.t, pulse.v) for pulse in pulses)
    else:
        time_ns, _virtual_mv, physical_mv = transform_virtual_waveforms(
            pulses,
            matrix,
        )
        traces = tuple((time_ns, physical_mv[index]) for index in range(len(pulses)))

    lines = [
        '"""Generated Keysight QCS DC waveforms."""',
        "",
        "import keysight.qcs as qcs",
        "",
        "ns = 1e-9",
        f"QCS_FULL_SCALE_V = {full_scale_v:.12g}",
        f"CROSS_CAPACITANCE = {matrix!r}",
        "mV = 1.0 / (QCS_FULL_SCALE_V * 1000.0)",
        "",
        "",
        "def generate_dc_waveforms(",
        "    program: qcs.Program,",
    ]
    for name in channel_names:
        lines.append(f"    {name}: qcs.Channels,")
    lines.extend([") -> qcs.Program:", "    # RAMP envelopes are unit-normalized; amplitude carries physical scale."])
    for (time_ns, voltage_mv), name in zip(traces, channel_names):
        lines.append(
            _qcs_channel_samples_code(time_ns, voltage_mv, name).rstrip()
        )
    lines.extend(["    return program", ""])
    return "\n".join(lines)


def generate_qick_program_code(
    pulses: Sequence[PulseSequence],
    *,
    output_names: Optional[Sequence[str]] = None,
    awg_channels: Optional[Sequence[int]] = None,
    fabric_mhz: Real = DEFAULT_QICK_FABRIC_MHZ,
    tproc_mhz: Real = DEFAULT_QICK_TPROC_MHZ,
    full_scale_mv: Real = DEFAULT_QICK_FULL_SCALE_MV,
    output_full_scales_mv=None,
    dac_current_settings=None,
    square_full_scale_mv=None,
    square_current_settings=None,
    repetitions_per_sweep: Integral = 1,
    sweep: Optional[QickSweepAxisSpec] = None,
    sweeps: Optional[Sequence[QickSweepAxisSpec]] = None,
    cross_capacitance=None,
    rf_pulse_spec: Optional[QickRfPulseSpec] = None,
    rf_pulse_specs: Optional[Sequence[QickRfPulseSpec]] = None,
    ddr_readout_spec: Optional[QickDdrReadoutSpec] = None,
    bias_t_compensation_enabled: bool = False,
    bias_t_compensation_type: str = "dc",
    bias_t_compensation_voltage_mv: Optional[Real] = None,
    bias_t_compensation_mode: str = "fixed_voltage",
    bias_t_compensation_duration_us: Real = DEFAULT_BIAS_T_COMPENSATION_DURATION_US,
    bias_t_filter_tau_us: Real = DEFAULT_BIAS_T_FILTER_TAU_US,
    square_pulse_settings=None,
    output_trigger_settings=None,
) -> str:
    """Generate a QICK builder/execution module.

    The generated ``run_experiment()`` helper optionally configures RF-board
    attenuators, executes the pulse program, and returns FIR-decimated
    DDR IQ data grouped by sweep point and repetition.
    """
    pulses = tuple(pulses)
    if output_names is None:
        output_names = tuple(f"awg_{index}" for index in range(len(pulses)))
    output_names = _unique_names(tuple(output_names), "awg")
    if len(output_names) != len(pulses):
        raise ValueError("output_names length must match the pulse count")
    if awg_channels is None:
        awg_channels = tuple(range(len(pulses)))
    awg_channels = tuple(int(channel) for channel in awg_channels)
    if len(awg_channels) != len(pulses):
        raise ValueError("awg_channels length must match the pulse count")
    if len(set(awg_channels)) != len(awg_channels) or any(channel < 0 for channel in awg_channels):
        raise ValueError("AWG channels must be unique nonnegative integers")
    tproc_mhz = _positive_real(tproc_mhz, "tproc_mhz")
    full_scale_mv = _positive_real(full_scale_mv, "full_scale_mv")
    square_full_scale_mv = full_scale_mv if square_full_scale_mv is None else square_full_scale_mv
    dac_current_settings = dict(dac_current_settings or {})
    from qick_square_dds import decode_square_outputs
    square_configs, _ = decode_square_outputs(square_pulse_settings, square_full_scale_mv)
    if square_configs:
        dac_current_settings.update(square_current_settings or {})
    if not isinstance(bias_t_compensation_enabled, (bool, np.bool_)):
        raise TypeError("bias_t_compensation_enabled must be boolean")
    if bias_t_compensation_type not in BIAS_T_COMPENSATION_TYPES:
        raise ValueError(
            "bias_t_compensation_type must be one of "
            f"{BIAS_T_COMPENSATION_TYPES}"
        )
    if bias_t_compensation_voltage_mv is None:
        bias_t_compensation_voltage_mv = (
            full_scale_mv * DEFAULT_BIAS_T_COMPENSATION_FRACTION
        )
    bias_t_compensation_voltage_mv = _positive_real(
        bias_t_compensation_voltage_mv,
        "bias_t_compensation_voltage_mv",
    )
    if bias_t_compensation_voltage_mv > full_scale_mv:
        raise ValueError("Bias-T compensation voltage exceeds QICK full scale")
    if bias_t_compensation_mode not in BIAS_T_COMPENSATION_MODES:
        raise ValueError(
            f"bias_t_compensation_mode must be one of {BIAS_T_COMPENSATION_MODES}"
        )
    bias_t_compensation_duration_us = _positive_real(
        bias_t_compensation_duration_us,
        "bias_t_compensation_duration_us",
    )
    bias_t_compensation_duration_cycles = _cycles_from_ns(
        bias_t_compensation_duration_us * 1000.0,
        fabric_mhz,
    )
    bias_t_filter_tau_us = _positive_real(
        bias_t_filter_tau_us,
        "bias_t_filter_tau_us",
    )
    repetitions_per_sweep = _positive_int(repetitions_per_sweep, "repetitions_per_sweep")
    sweep_specs = _coerce_sweep_specs(sweep, sweeps)
    if rf_pulse_spec is not None and rf_pulse_specs is not None:
        if tuple(rf_pulse_specs) != (rf_pulse_spec,):
            raise ValueError("use either rf_pulse_spec or rf_pulse_specs, not both")
        rf_pulse_spec = None
    normalized_rf_specs = tuple(
        rf_pulse_specs
        if rf_pulse_specs is not None
        else (() if rf_pulse_spec is None else (rf_pulse_spec,))
    )
    if any(not isinstance(spec, QickRfPulseSpec) for spec in normalized_rf_specs):
        raise TypeError("every RF pulse entry must be a QickRfPulseSpec")
    rf_channels = tuple(spec.gen_ch for spec in normalized_rf_specs)
    if len(set(rf_channels)) != len(rf_channels):
        raise ValueError("each RF pulse must use a unique generator channel")
    cross_capacitance = _coerce_cross_capacitance(
        cross_capacitance, len(output_names)
    )
    specs = make_qick_segment_specs(
        pulses, fabric_mhz=fabric_mhz, full_scale_mv=full_scale_mv
    )
    valid_set_names = {spec.name for spec in specs if spec.kind == "set"}
    valid_ramp_names = {spec.name for spec in specs if spec.kind == "ramp"}
    for sweep_spec in sweep_specs:
        if isinstance(sweep_spec, QickRampRateSweepSpec):
            if sweep_spec.segment_name not in valid_ramp_names:
                raise ValueError(
                    f"unknown QICK RAMP segment {sweep_spec.segment_name!r}"
                )
        elif isinstance(sweep_spec, QickHoldDurationSweepSpec):
            if sweep_spec.segment_name not in valid_set_names:
                raise ValueError(
                    f"unknown QICK SET segment {sweep_spec.segment_name!r}"
                )
        else:
            if sweep_spec.segment_name not in valid_set_names:
                raise ValueError(
                    f"unknown QICK SET segment {sweep_spec.segment_name!r}"
                )
            if sweep_spec.output_name not in output_names:
                raise ValueError(
                    f"unknown QICK output {sweep_spec.output_name!r}"
                )
    for rf_spec in normalized_rf_specs:
        if rf_spec.segment_name not in valid_set_names:
            raise ValueError(f"unknown RF SET segment {rf_spec.segment_name!r}")
        if rf_spec.gen_ch in awg_channels:
            raise ValueError("RF generator channels must be separate from AWG tuning channels")
    if ddr_readout_spec is not None:
        if ddr_readout_spec.segment_name not in valid_set_names:
            raise ValueError(f"unknown DDR SET segment {ddr_readout_spec.segment_name!r}")

    channel_map = dict(zip(output_names, awg_channels))
    sweep_config = tuple(
        {
            "axis_kind": item.axis_kind,
            "segment_name": item.segment_name,
            "output_name": item.output_name,
            "start": float(item.start),
            "stop": float(item.stop),
            "count": int(item.count),
        }
        for item in sweep_specs
    )
    rf_configs = tuple(asdict(spec) for spec in normalized_rf_specs)
    ddr_config = None if ddr_readout_spec is None else asdict(ddr_readout_spec)
    lines = [
        '"""Generated QICK AWG-tuning, RF pulse, and HWH-rate DDR program."""',
        "",
        "from qick_fine_tune_sweep import (",
        "    DdrFirReadoutConfig,",
        "    FineTuneSequence,",
        "    RfPulseConfig,",
        "    cycles_from_us,",
        ")",
        "from dc_waveform_core import QickDdrReadoutSpec, QickRfPulseSpec",
        "from qick_qcodes_experiment import build_runtime_rf_pulses, execute_qick_sequence",
        "",
        f"OUTPUT_NAMES = {output_names!r}",
        f"AWG_CHANNELS = {channel_map!r}",
        f"FABRIC_MHZ = {float(fabric_mhz)!r}",
        f"TPROC_MHZ = {tproc_mhz!r}",
        f"FULL_SCALE_MV = {float(full_scale_mv)!r}",
        f"OUTPUT_FULL_SCALES_MV = {output_full_scales_mv!r}",
        f"DAC_CURRENT_SETTINGS = {dict(dac_current_settings or {})!r}",
        f"BIAS_T_COMPENSATION_ENABLED = {bool(bias_t_compensation_enabled)!r}",
        f"BIAS_T_COMPENSATION_TYPE = {bias_t_compensation_type!r}",
        f"BIAS_T_COMPENSATION_VOLTAGE_MV = {float(bias_t_compensation_voltage_mv)!r}",
        f"BIAS_T_COMPENSATION_MODE = {bias_t_compensation_mode!r}",
        f"BIAS_T_COMPENSATION_DURATION_US = {float(bias_t_compensation_duration_us)!r}",
        f"BIAS_T_COMPENSATION_DURATION_CYCLES = {bias_t_compensation_duration_cycles}",
        f"BIAS_T_FILTER_TAU_US = {float(bias_t_filter_tau_us)!r}",
        f"BIAS_T_FILTER_TAU_CYCLES = {float(bias_t_filter_tau_us * fabric_mhz)!r}",
        f"REPETITIONS_PER_SWEEP = {repetitions_per_sweep}",
        f"SWEEP_SPECS = {sweep_config!r}",
        f"CROSS_CAPACITANCE = {cross_capacitance!r}",
        f"RF_CONFIGS = {rf_configs!r}",
        "RF_CONFIG = RF_CONFIGS[0] if len(RF_CONFIGS) == 1 else None",
        f"FIR_DDR_CONFIG = {ddr_config!r}",
        "",
        "",
        "def build_sequence() -> FineTuneSequence:",
        "    sequence = FineTuneSequence(OUTPUT_NAMES)",
        "    sequence.output_full_scale_mv = FULL_SCALE_MV",
        "    if OUTPUT_FULL_SCALES_MV is not None:",
        "        sequence.set_voltage_scales(FULL_SCALE_MV, OUTPUT_FULL_SCALES_MV)",
        "    sequence.dac_current_settings = DAC_CURRENT_SETTINGS",
        "    sequence.set_cross_capacitance(CROSS_CAPACITANCE)",
        "    sequence.set_rc_compensation(",
        "        BIAS_T_FILTER_TAU_US,",
        "        enabled=BIAS_T_COMPENSATION_ENABLED and BIAS_T_COMPENSATION_TYPE in ('filter', 'dc_rc'),",
        "    )",
        "    sequence.set_bias_t_compensation(",
        "        BIAS_T_COMPENSATION_VOLTAGE_MV / FULL_SCALE_MV,",
        "        enabled=BIAS_T_COMPENSATION_ENABLED and BIAS_T_COMPENSATION_TYPE in ('dc', 'dc_rc'),",
        "        mode=BIAS_T_COMPENSATION_MODE,",
        "        fixed_duration_cycles=(",
        "            BIAS_T_COMPENSATION_DURATION_CYCLES",
        "            if BIAS_T_COMPENSATION_MODE == 'fixed_time' else None",
        "        ),",
        "    )",
    ]
    for spec in specs:
        if spec.kind == "set":
            lines.append(
                f"    sequence.add_set({spec.name!r}, {spec.amplitudes!r}, "
                f"duration_cycles={spec.duration_cycles})"
            )
        else:
            lines.append(
                f"    sequence.add_ramp({spec.name!r}, duration_cycles={spec.duration_cycles})"
            )
    for sweep_spec in sweep_specs:
        if isinstance(sweep_spec, QickRampRateSweepSpec):
            lines.extend(
                [
                    "    sequence.add_ramp_duration_sweep(",
                    f"        segment={sweep_spec.segment_name!r},",
                    f"        start_us={float(sweep_spec.start)!r},",
                    f"        stop_us={float(sweep_spec.stop)!r},",
                    f"        count={int(sweep_spec.count)},",
                    "        sequence_fabric_mhz=FABRIC_MHZ,",
                    "    )",
                ]
            )
        elif isinstance(sweep_spec, QickHoldDurationSweepSpec):
            lines.extend(
                [
                    "    sequence.add_hold_duration_sweep(",
                    f"        segment={sweep_spec.segment_name!r},",
                    f"        start_us={float(sweep_spec.start)!r},",
                    f"        stop_us={float(sweep_spec.stop)!r},",
                    f"        count={int(sweep_spec.count)},",
                    "        sequence_fabric_mhz=FABRIC_MHZ,",
                    "    )",
                ]
            )
        else:
            lines.extend(
                [
                    "    sequence.add_amplitude_sweep(",
                    f"        segment={sweep_spec.segment_name!r},",
                    f"        output={sweep_spec.output_name!r},",
                    f"        start={float(sweep_spec.start)!r},",
                    f"        stop={float(sweep_spec.stop)!r},",
                    f"        count={int(sweep_spec.count)},",
                    "    )",
                ]
            )
    for rf_spec in normalized_rf_specs:
        if rf_spec.segment_length_mode != "extend_by_rf_duration":
            continue
        base_extension_cycles = sum(
            _cycles_from_ns(duration_us * 1000.0, fabric_mhz)
            for duration_us in rf_spec.segment_extension_components_us
        )
        lines.extend(
            [
                "    sequence.set_rf_segment_length_extension(",
                f"        segment={rf_spec.segment_name!r},",
                f"        gen_ch={int(rf_spec.gen_ch)},",
                f"        base_duration_cycles={base_extension_cycles},",
                "        parameter_multiplicities="
                f"{dict(rf_spec.duration_parameter_reference_counts)!r},",
                "    )",
            ]
        )
    for rf_spec in normalized_rf_specs:
        for duration_axis in (
            axis
            for axis in rf_spec.sweep_axes
            if axis.axis_kind == "rf_duration"
        ):
            lines.extend(
                [
                    "    sequence.add_rf_duration_sweep(",
                    f"        segment={rf_spec.segment_name!r},",
                    f"        gen_ch={int(rf_spec.gen_ch)},",
                    f"        start_us={float(duration_axis.start)!r},",
                    f"        stop_us={float(duration_axis.stop)!r},",
                    f"        count={int(duration_axis.count)},",
                    f"        segment_length_mode={rf_spec.segment_length_mode!r},",
                    "        sequence_fabric_mhz=FABRIC_MHZ,",
                    f"        parameter_name={duration_axis.parameter_name!r},",
                    f"        output_name={duration_axis.output_name!r},",
                    "    )",
                ]
            )
        for frequency_axis in (
            axis
            for axis in rf_spec.sweep_axes
            if axis.axis_kind == "rf_frequency"
        ):
            lines.extend(
                [
                    "    sequence.add_rf_frequency_sweep(",
                    f"        segment={rf_spec.segment_name!r},",
                    f"        gen_ch={int(rf_spec.gen_ch)},",
                    f"        start_mhz={float(frequency_axis.start)!r},",
                    f"        stop_mhz={float(frequency_axis.stop)!r},",
                    f"        count={int(frequency_axis.count)},",
                    f"        parameter_name={frequency_axis.parameter_name!r},",
                    f"        output_name={frequency_axis.output_name!r},",
                    "    )",
                ]
            )
        if rf_spec.power_sweep_enabled:
            lines.extend(
                [
                    "    sequence.add_rf_power_sweep(",
                    f"        segment={rf_spec.segment_name!r},",
                    f"        gen_ch={int(rf_spec.gen_ch)},",
                    f"        start_dbm={float(rf_spec.power_sweep_start_dbm)!r},",
                    f"        stop_dbm={float(rf_spec.power_sweep_stop_dbm)!r},",
                    f"        count={int(rf_spec.power_sweep_count)},",
                    "    )",
                ]
            )
    if square_pulse_settings is not None or output_trigger_settings is not None:
        from qick_square_dds import OutputTriggerConfig
        OutputTriggerConfig(**(output_trigger_settings or {}))
        lines.extend([
            "    from qick_square_dds import decode_square_outputs, OutputTriggerConfig, attach_square_settings",
            f"    square_config, square_axes = decode_square_outputs({square_pulse_settings!r}, {square_full_scale_mv!r})",
            f"    attach_square_settings(sequence, square_config, square_axes, OutputTriggerConfig(**{output_trigger_settings or {}!r}), follow_experiment_rc=True)",
        ])
    lines.extend(
        [
            "    from qick_rc_validation import validate_sequence_rc_range, validate_channel_voltage_ranges",
            "    validate_channel_voltage_ranges(sequence)",
            "    sequence.rc_output_range_preview = validate_sequence_rc_range(sequence, FABRIC_MHZ, FULL_SCALE_MV)",
            "    return sequence",
            "",
            "",
            "def _delay_cycles(duration_us, clock_mhz):",
            "    return 0 if duration_us <= 0 else cycles_from_us(duration_us, clock_mhz)",
            "",
            "",
            "def build_rf_pulses(soccfg):",
            "    specs = tuple(QickRfPulseSpec(**cfg) for cfg in RF_CONFIGS)",
            "    return build_runtime_rf_pulses(",
            "        soccfg, specs, tproc_mhz=TPROC_MHZ",
            "    )",
            "",
            "",
            "def execute_sequence(soc, soccfg, *, progress=True, **execution_kwargs):",
            "    \"\"\"Acquire all host and hardware sweep coordinates with generated settings.\"\"\"",
            "    if FIR_DDR_CONFIG is None:",
            "        raise ValueError('Host RF sweeps require a configured readout for acquisition')",
            "    return execute_qick_sequence(",
            "        soc, soccfg, build_sequence(),",
            "        awg_channels=tuple(AWG_CHANNELS[name] for name in OUTPUT_NAMES),",
            "        repetitions_per_sweep=REPETITIONS_PER_SWEEP,",
            "        tproc_mhz=TPROC_MHZ,",
            "        rf_specs=tuple(QickRfPulseSpec(**cfg) for cfg in RF_CONFIGS),",
            "        readout_spec=QickDdrReadoutSpec(**FIR_DDR_CONFIG),",
            "        sequence_fabric_mhz=FABRIC_MHZ,",
            "        progress=progress, **execution_kwargs,",
            "    )",
            "",
            "",
            "def build_rf_pulse(soccfg):",
            "    pulses = build_rf_pulses(soccfg)",
            "    return pulses[0] if len(pulses) == 1 else None",
            "",
            "",
            "def build_ddr_readout(soccfg):",
            "    if FIR_DDR_CONFIG is None:",
            "        return None",
            "    cfg = FIR_DDR_CONFIG",
            "    fpga_delay = cfg.get('fpga_trigger_delay_samples')",
            "    if cfg.get('fpga_trigger_delay_us') is not None:",
            "        from fir_ddr_profile import resolve_fir_ddr_profile",
            "        fpga_delay = resolve_fir_ddr_profile(soccfg).trigger_delay_value_for_us(cfg['fpga_trigger_delay_us'])",
            "    return DdrFirReadoutConfig(",
            "        ro_ch=cfg['ro_ch'],",
            "        samples_per_trigger=cfg['samples_per_trigger'],",
            "        at_segment=cfg['segment_name'],",
            "        dc_compensation_timing=cfg.get('dc_compensation_timing', 'after_readout'),",
            "        fpga_trigger_delay_samples=fpga_delay,",
            "        settle_seconds=cfg['post_run_read_delay_seconds'],",
            "        readout_freq_mhz=cfg['readout_frequency_mhz'],",
            "        trigger_delay_tproc_cycles=_delay_cycles(",
            "            cfg['delay_us'], TPROC_MHZ",
            "        ),",
            "        margin_input_samples=cfg['margin_input_samples'],",
            "        address=cfg['address'],",
            "        force_overwrite=cfg['force_overwrite'],",
            "    )",
            "",
            "",
            "def build_program(",
            "    soccfg,",
            "    *,",
            "    awg_channels=AWG_CHANNELS,",
            "    repetitions_per_sweep=REPETITIONS_PER_SWEEP,",
            "    readout=None,",
            "    rf_pulse=None,",
            "    rf_pulses=None,",
            "    ddr_readout=None,",
            "    use_generated_aux=True,",
            "):",
            "    if use_generated_aux:",
            "        if rf_pulse is None and rf_pulses is None:",
            "            rf_pulses = build_rf_pulses(soccfg)",
            "        if ddr_readout is None:",
            "            ddr_readout = build_ddr_readout(soccfg)",
            "    return build_sequence().make_program(",
            "        soccfg,",
            "        awg_channels=awg_channels,",
            "        tproc_mhz=TPROC_MHZ,",
            "        repetitions_per_sweep=repetitions_per_sweep,",
            "        readout=readout,",
            "        rf_pulse=rf_pulse,",
            "        rf_pulses=rf_pulses,",
            "        ddr_readout=ddr_readout,",
            "    )",
            "",
            "",
            "def configure_rf_chain(soc):",
            "    if not RF_CONFIGS:",
            "        return None",
            "    actual = []",
            "    for cfg in RF_CONFIGS:",
            "        if cfg['output_board_type'] == 'RF_Out':",
            "            configured = soc.rfb_set_gen_rf(",
            "                cfg['gen_ch'], cfg['att1_db'], cfg['att2_db']",
            "            )",
            "        else:",
            "            soc.rfb_set_gen_dc(cfg['gen_ch'])",
            "            configured = (0.0, 0.0)",
            "        actual.append(configured)",
            "        if cfg['output_board_type'] == 'RF_Out':",
            "            soc.rfb_set_gen_filter(",
            "                cfg['gen_ch'],",
            "                fc=cfg['filter_cutoff'],",
            "                bw=cfg['filter_bandwidth'],",
            "                ftype=cfg['filter_type'],",
            "            )",
            "    actual = tuple(actual)",
            "    return actual[0] if len(actual) == 1 else actual",
            "",
            "",
            "def configure_readout_chain(soc):",
            "    if FIR_DDR_CONFIG is None:",
            "        return None",
            "    cfg = FIR_DDR_CONFIG",
            "    if cfg['input_board_type'] == 'RF_In':",
            "        configured = soc.rfb_set_ro_rf(cfg['ro_ch'], cfg['attenuation_db'])",
            "    else:",
            "        configured = soc.rfb_set_ro_dc(cfg['ro_ch'], cfg['dc_gain_db'])",
            "    if cfg['input_board_type'] == 'RF_In':",
            "        soc.rfb_set_ro_filter(",
            "            cfg['ro_ch'],",
            "            fc=cfg['filter_cutoff'],",
            "            bw=cfg['filter_bandwidth'],",
            "            ftype=cfg['filter_type'],",
            "        )",
            "    return configured",
            "",
            "",
            "def run_experiment(soc, soccfg, *, progress=True, configure_rf=True, **run_kwargs):",
            "    specs = tuple(QickRfPulseSpec(**cfg) for cfg in RF_CONFIGS)",
            "    if any(spec.software_sweep_axes for spec in specs):",
            "        if not configure_rf:",
            "            raise ValueError('Host RF sweeps configure the RF chain; use configure_rf=True')",
            "        return execute_sequence(soc, soccfg, progress=progress, **run_kwargs)",
            "    actual_outputs = configure_rf_chain(soc) if configure_rf else None",
            "    actual_input = configure_readout_chain(soc) if configure_rf else None",
            "    program = build_program(soccfg)",
            "    from qick_square_dds import get_square_configs",
            "    squares = get_square_configs(program)",
            "    if configure_rf:",
            "        for square in squares:",
            "            soc.rfb_set_gen_dc(square.gen_ch)",
            "    completed = False",
            "    try:",
            "        if FIR_DDR_CONFIG is not None:",
            "            ddr_result = program.acquire_fir_ddr(",
            "                soc, progress=progress, **run_kwargs",
            "            )",
            "        else:",
            "            program.run_rounds(soc, progress=progress, **run_kwargs)",
            "            ddr_result = None",
            "        completed = True",
            "    finally:",
            "        for square in squares:",
            "            if not completed or square.mute_on_finish:",
            "                soc.stop_square_pulse(square.gen_ch)",
            "    rf_settings = {'outputs': actual_outputs, 'readout': actual_input}",
            "    return program, ddr_result, rf_settings",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "BIAS_T_COMPENSATION_MODES",
    "BIAS_T_COMPENSATION_TYPES",
    "DEFAULT_BIAS_T_COMPENSATION_DURATION_US",
    "DEFAULT_BIAS_T_COMPENSATION_FRACTION",
    "DEFAULT_BIAS_T_FILTER_TAU_US",
    "DEFAULT_DC_MEASURE_GAIN_V_PER_A",
    "DEFAULT_INITIAL_DURATION_NS",
    "DEFAULT_INITIAL_VOLTAGE_MV",
    "DEFAULT_INSERT_FLAT_NS",
    "DEFAULT_INSERT_RAMP_NS",
    "DEFAULT_QCS_FULL_SCALE_V",
    "DEFAULT_QICK_FABRIC_MHZ",
    "DEFAULT_QICK_TPROC_MHZ",
    "DEFAULT_QICK_FULL_SCALE_MV",
    "PulseSequence",
    "QickDdrReadoutSpec",
    "QickHoldDurationSweepSpec",
    "QickRampRateSweepSpec",
    "QickRfAmplitudeParameterSpec",
    "QickRfCompositeItemSpec",
    "QickRfDelayParameterSpec",
    "QickRfDurationParameterSpec",
    "QickRfFrequencyParameterSpec",
    "QickRfPhaseParameterSpec",
    "QickRfPulseEventSpec",
    "QickRfPulseSpec",
    "QickRfSoftwareSweepAxisSpec",
    "QickRfSweepAxisSpec",
    "RF_PREDEFINED_COMPOSITE_TEMPLATES",
    "QickSegmentSpec",
    "QickSweepAxisSpec",
    "QickSweepSpec",
    "WaveformInterval",
    "adc_iq_to_voltage",
    "build_qick_sequence",
    "build_predefined_composite_items",
    "dc_iq_to_current",
    "generate_qcs_program_code",
    "generate_qick_program_code",
    "make_qick_segment_specs",
    "qick_set_segment_names",
    "transform_virtual_waveforms",
]
