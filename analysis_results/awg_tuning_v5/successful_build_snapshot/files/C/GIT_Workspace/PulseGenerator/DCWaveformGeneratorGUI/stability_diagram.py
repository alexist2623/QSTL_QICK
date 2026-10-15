"""Two-electrode QICK stability-diagram acquisition and display.

Continuous acquisition intentionally bypasses QCoDeS. A saved single shot can
retain every FIR DDR repetition trace or persist only the coherent mean I/Q pair
for each X/Y point.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

try:
    from .qick_compensation_controls import CompensationGroup, CompensationSelector
except ImportError:
    from qick_compensation_controls import CompensationGroup, CompensationSelector
from copy import deepcopy
from dataclasses import dataclass, replace
import json
from pathlib import Path
import sqlite3
from threading import Event
import traceback
from typing import Any, Mapping, Optional, Sequence, Tuple

import numpy as np
try:
    from .fir_ddr_profile import result_iq_in_input_units
except ImportError:
    from fir_ddr_profile import result_iq_in_input_units
from PyQt5 import QtCore, QtWidgets

try:
    import pyqtgraph as pg
except ImportError:
    pg = None

try:
    from .dc_waveform_core import (
        BIAS_T_COMPENSATION_MODES,
        BIAS_T_COMPENSATION_TYPES,
        DEFAULT_BIAS_T_COMPENSATION_DURATION_US,
        DEFAULT_BIAS_T_COMPENSATION_FRACTION,
        DEFAULT_BIAS_T_FILTER_TAU_US,
        DEFAULT_QICK_FULL_SCALE_MV,
        PulseSequence,
        QickSweepSpec,
        adc_iq_to_voltage,
        build_qick_sequence,
        dc_iq_to_current,
    )
    from .dc_voltage_calibration import load_dc_voltage_calibration
    from .fir_ddr_profile import format_sample_rate_hz, resolve_fir_ddr_profile
    from .measurement_display import attach_color_bar, scale_iq_for_display
    from .power_calibration import CalibrationDatabase
    from .qick_qcodes_experiment import (
        StoredQickExperiment,
        AWG_METADATA_MODE_EXPANDED,
        DEFAULT_AWG_METADATA_MODE,
        DEFAULT_IQ_STORAGE_MODE,
        IQ_STORAGE_FULL_TRACES,
        IQ_STORAGE_MEAN_IQ,
        build_awg_vertex_metadata,
        build_awg_waveform_recipe,
        normalize_awg_metadata_mode,
        normalize_iq_storage_mode,
        connect_qick,
        execute_qick_sequence,
        load_qick_iq_arrays,
        store_qick_result,
    )
    from .sparameter_gui import RfPathCorrectionWidget
    from .qick_front_panel import square_pulse_output_channels, validate_awg_output_channels
except ImportError:
    from dc_waveform_core import (
        BIAS_T_COMPENSATION_MODES,
        BIAS_T_COMPENSATION_TYPES,
        DEFAULT_BIAS_T_COMPENSATION_DURATION_US,
        DEFAULT_BIAS_T_COMPENSATION_FRACTION,
        DEFAULT_BIAS_T_FILTER_TAU_US,
        DEFAULT_QICK_FULL_SCALE_MV,
        PulseSequence,
        QickSweepSpec,
        adc_iq_to_voltage,
        build_qick_sequence,
        dc_iq_to_current,
    )
    from dc_voltage_calibration import load_dc_voltage_calibration
    from fir_ddr_profile import format_sample_rate_hz, resolve_fir_ddr_profile
    from measurement_display import attach_color_bar, scale_iq_for_display
    from power_calibration import CalibrationDatabase
    from qick_qcodes_experiment import (
        StoredQickExperiment,
        AWG_METADATA_MODE_EXPANDED,
        DEFAULT_AWG_METADATA_MODE,
        DEFAULT_IQ_STORAGE_MODE,
        IQ_STORAGE_FULL_TRACES,
        IQ_STORAGE_MEAN_IQ,
        build_awg_vertex_metadata,
        build_awg_waveform_recipe,
        normalize_awg_metadata_mode,
        normalize_iq_storage_mode,
        connect_qick,
        execute_qick_sequence,
        load_qick_iq_arrays,
        store_qick_result,
    )
    from sparameter_gui import RfPathCorrectionWidget
    from qick_front_panel import square_pulse_output_channels, validate_awg_output_channels


DEFAULT_STABILITY_START_MV = -100.0
DEFAULT_STABILITY_STOP_MV = 100.0
DEFAULT_STABILITY_POINTS = 51
DEFAULT_STABILITY_REPETITIONS = 1
DEFAULT_STABILITY_TRACE_SAMPLES = 64
DEFAULT_STABILITY_SETTLE_US = 50.0
DEFAULT_STABILITY_POINT_GUARD_US = 1.0
DEFAULT_STABILITY_RF_START_GUARD_TPROC_CYCLES = 1
DEFAULT_STABILITY_MODULATION_FREQUENCY_MHZ = 50.0
DEFAULT_STABILITY_MODULATION_GAIN = 20_000
DEFAULT_STABILITY_TARGET_POWER_DBM = -20.0
STABILITY_ACQUISITION_SOURCES = ("fir_ddr", "avg_buffer")
STABILITY_SWEEP_MODES = ("hardware", "software")
DEFAULT_STABILITY_HARDWARE_REP_DELAY_US = 0.0
DEFAULT_STABILITY_POWER_CALIBRATION_DB_PATH = str(
    Path.home() / "gain_pwr_calb.db"
)
STABILITY_HOLD_SEGMENT = "set_0"
DEFAULT_STABILITY_BIAS_T_COMPENSATION_MV = (
    DEFAULT_QICK_FULL_SCALE_MV * DEFAULT_BIAS_T_COMPENSATION_FRACTION
)
DEFAULT_STABILITY_DB_PATH = str(Path.home() / "qick_stability_diagrams.db")
DEFAULT_STABILITY_RF_PATH = {
    "output_ch": 0,
    "readout_ch": 0,
    "output_nqz": 1,
    "readout_nqz": 1,
    "output_board_type": "RF_Out",
    "input_board_type": "DC_In",
    "output_att1_db": 10.0,
    "output_att2_db": 10.0,
    "readout_attenuation_db": 20.0,
    "readout_dc_gain_db": 0.0,
    "loss1_db": 0.0,
    "loss2_db": 0.0,
    "amplifier_gain_db": 0.0,
    "output_filter_type": "bypass",
    "output_filter_cutoff_ghz": 2.5,
    "output_filter_bandwidth_ghz": 1.0,
    "readout_filter_type": "bypass",
    "readout_filter_cutoff_ghz": 2.5,
    "readout_filter_bandwidth_ghz": 1.0,
}
DEFAULT_STABILITY_COLOR_RANGES = {
    "i": {
        "auto": True,
        "minimum": -1.0,
        "maximum": 1.0,
    },
    "q": {
        "auto": True,
        "minimum": -1.0,
        "maximum": 1.0,
    },
    "magnitude": {
        "auto": True,
        "minimum": 0.0,
        "maximum": 1.0,
    },
    "phase": {
        "auto": False,
        "minimum": -180.0,
        "maximum": 180.0,
    },
}
STABILITY_DATA_KEYS = ("i", "q", "magnitude", "phase")
DEFAULT_STABILITY_VISIBLE_DATA = ("magnitude", "phase")


def _finite_float(value: Any, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _integer(value: Any, name: str, minimum: int) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, np.integer)
    ):
        raise TypeError(f"{name} must be an integer")
    result = int(value)
    if result < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return result


def _normalize_color_range(
    settings: Any,
    *,
    defaults: Mapping[str, Any],
    label: str,
) -> dict:
    if not isinstance(settings, Mapping):
        raise TypeError(f"stability {label} color range must be a JSON object")
    auto = settings.get("auto", defaults["auto"])
    if not isinstance(auto, (bool, np.bool_)):
        raise TypeError(f"stability {label} color auto range must be boolean")
    minimum = _finite_float(
        settings.get("minimum", defaults["minimum"]),
        f"stability {label} color minimum",
    )
    maximum = _finite_float(
        settings.get("maximum", defaults["maximum"]),
        f"stability {label} color maximum",
    )
    if minimum >= maximum:
        raise ValueError(
            f"stability {label} color minimum must be below maximum"
        )
    return {
        "auto": bool(auto),
        "minimum": minimum,
        "maximum": maximum,
    }


def normalize_stability_color_ranges(settings: Any) -> dict:
    """Validate map ranges while accepting ``angle`` as a UI-name alias."""
    if settings is None:
        settings = {}
    if not isinstance(settings, Mapping):
        raise TypeError("stability color_ranges must be a JSON object")
    normalized = {}
    for name, defaults in DEFAULT_STABILITY_COLOR_RANGES.items():
        raw = settings.get(name)
        if raw is None and name == "phase":
            raw = settings.get("angle")
        if raw is None:
            raw = defaults
        normalized[name] = _normalize_color_range(
            raw,
            defaults=defaults,
            label=name,
        )
    return normalized


def normalize_stability_visible_data(values: Any) -> Tuple[str, ...]:
    """Validate the ordered set of maps shown in the Stability result dock."""
    if values is None:
        return DEFAULT_STABILITY_VISIBLE_DATA
    if not isinstance(values, (list, tuple)):
        raise TypeError("stability visible_data must be a JSON array")
    normalized = []
    for value in values:
        key = str(value).strip().lower()
        if key == "angle":
            key = "phase"
        if key not in STABILITY_DATA_KEYS:
            raise ValueError(f"unknown Stability plot data {value!r}")
        if key not in normalized:
            normalized.append(key)
    if not normalized:
        raise ValueError("at least one Stability plot must be visible")
    return tuple(normalized)


@dataclass(frozen=True)
class StabilitySweepAxis:
    """One virtual-electrode voltage axis of a stability diagram."""

    output_name: str
    start_mv: float
    stop_mv: float
    points: int

    def __post_init__(self) -> None:
        if not str(self.output_name):
            raise ValueError("stability output name must not be empty")
        _finite_float(self.start_mv, "stability start voltage")
        _finite_float(self.stop_mv, "stability stop voltage")
        _integer(self.points, "stability point count", 2)

    @property
    def voltages_mv(self) -> np.ndarray:
        return np.linspace(
            float(self.start_mv),
            float(self.stop_mv),
            int(self.points),
            dtype=float,
        )

    @property
    def segment_name(self) -> str:
        """Internal SET anchor used by the dedicated Stability sequence."""
        return STABILITY_HOLD_SEGMENT


@dataclass(frozen=True)
class StabilityDiagramConfig:
    """Two-axis sweep and coherent FIR/AVG reduction settings."""

    x_axis: StabilitySweepAxis
    y_axis: StabilitySweepAxis
    repetitions_per_point: int = DEFAULT_STABILITY_REPETITIONS
    trace_samples_per_point: int = DEFAULT_STABILITY_TRACE_SAMPLES
    settle_time_us: float = DEFAULT_STABILITY_SETTLE_US
    fpga_trigger_delay_us: Optional[float] = None
    acquisition_source: str = "fir_ddr"
    sweep_mode: str = "hardware"
    hardware_rep_delay_us: float = DEFAULT_STABILITY_HARDWARE_REP_DELAY_US
    modulation_frequency_mhz: float = DEFAULT_STABILITY_MODULATION_FREQUENCY_MHZ
    modulation_gain: int = DEFAULT_STABILITY_MODULATION_GAIN
    modulation_power_calibration_enabled: bool = False
    modulation_power_calibration_database_path: str = (
        DEFAULT_STABILITY_POWER_CALIBRATION_DB_PATH
    )
    modulation_power_calibration_run_id: int = 0
    modulation_target_power_dbm: float = DEFAULT_STABILITY_TARGET_POWER_DBM
    bias_t_compensation_enabled: bool = False
    bias_t_compensation_type: str = "dc"
    bias_t_compensation_voltage_mv: float = DEFAULT_STABILITY_BIAS_T_COMPENSATION_MV
    bias_t_compensation_mode: str = "fixed_voltage"
    bias_t_compensation_duration_us: float = DEFAULT_BIAS_T_COMPENSATION_DURATION_US
    bias_t_filter_tau_us: float = DEFAULT_BIAS_T_FILTER_TAU_US

    def __post_init__(self) -> None:
        if self.x_axis.output_name == self.y_axis.output_name:
            raise ValueError("X and Y stability axes must use different AWG outputs")
        _integer(
            self.repetitions_per_point,
            "stability repetitions per point",
            1,
        )
        if _finite_float(self.settle_time_us, "stability settle time") < 0.0:
            raise ValueError("stability settle time must not be negative")
        if self.acquisition_source not in STABILITY_ACQUISITION_SOURCES:
            raise ValueError(
                "stability acquisition source must be one of "
                f"{STABILITY_ACQUISITION_SOURCES}"
            )
        if self.sweep_mode not in STABILITY_SWEEP_MODES:
            raise ValueError(
                "stability sweep mode must be one of "
                f"{STABILITY_SWEEP_MODES}"
            )
        if (
            _finite_float(
                self.hardware_rep_delay_us,
                "stability hardware repetition delay",
            )
            < 0.0
        ):
            raise ValueError(
                "stability hardware repetition delay must not be negative"
            )
        if (
            self.fpga_trigger_delay_us is not None
            and _finite_float(
                self.fpga_trigger_delay_us,
                "stability FPGA trigger delay",
            )
            < 0.0
        ):
            raise ValueError(
                "stability FPGA trigger delay must not be negative"
            )
        _integer(
            self.trace_samples_per_point,
            "stability FIR trace samples per point",
            1,
        )
        _finite_float(
            self.modulation_frequency_mhz,
            "stability modulation frequency",
        )
        modulation_gain = _integer(
            self.modulation_gain,
            "stability modulation gain",
            0,
        )
        if modulation_gain > 32767:
            raise ValueError("stability modulation gain must not exceed 32767")
        if not isinstance(
            self.modulation_power_calibration_enabled,
            (bool, np.bool_),
        ):
            raise TypeError(
                "stability modulation power calibration enabled must be boolean"
            )
        calibration_run_id = _integer(
            self.modulation_power_calibration_run_id,
            "stability modulation power calibration Run ID",
            0,
        )
        if calibration_run_id > (1 << 31) - 1:
            raise ValueError(
                "stability modulation power calibration Run ID is too large"
            )
        _finite_float(
            self.modulation_target_power_dbm,
            "stability modulation target output power",
        )
        if (
            self.modulation_power_calibration_enabled
            and not str(
                self.modulation_power_calibration_database_path
            ).strip()
        ):
            raise ValueError(
                "stability modulation power calibration database path is required"
            )
        if not isinstance(self.bias_t_compensation_enabled, (bool, np.bool_)):
            raise TypeError("stability Bias-T compensation enabled must be boolean")
        if self.bias_t_compensation_type not in BIAS_T_COMPENSATION_TYPES:
            raise ValueError(
                "stability Bias-T compensation type must be one of "
                f"{BIAS_T_COMPENSATION_TYPES}"
            )
        if self.bias_t_compensation_mode not in BIAS_T_COMPENSATION_MODES:
            raise ValueError(
                "stability Bias-T compensation mode must be one of "
                f"{BIAS_T_COMPENSATION_MODES}"
            )
        for value, label in (
            (
                self.bias_t_compensation_voltage_mv,
                "stability Bias-T compensation voltage",
            ),
            (
                self.bias_t_compensation_duration_us,
                "stability Bias-T compensation duration",
            ),
            (self.bias_t_filter_tau_us, "stability Bias-T filter tau"),
        ):
            if _finite_float(value, label) <= 0.0:
                raise ValueError(f"{label} must be positive")

    @property
    def point_count(self) -> int:
        return int(self.x_axis.points) * int(self.y_axis.points)

    def validate_full_scale(self, full_scale_mv: float) -> None:
        full_scale_mv = _finite_float(full_scale_mv, "AWG full scale")
        if full_scale_mv <= 0.0:
            raise ValueError("AWG full scale must be positive")
        for label, axis in (("X", self.x_axis), ("Y", self.y_axis)):
            if max(abs(float(axis.start_mv)), abs(float(axis.stop_mv))) > full_scale_mv:
                raise ValueError(
                    f"{label} stability sweep exceeds +/-{full_scale_mv:g} mV "
                    "AWG full scale"
                )
        if (
            self.bias_t_compensation_enabled
            and self.bias_t_compensation_type in ("dc", "dc_rc")
            and self.bias_t_compensation_mode == "fixed_voltage"
            and self.bias_t_compensation_voltage_mv > full_scale_mv
        ):
            raise ValueError(
                "stability Bias-T compensation voltage exceeds AWG full scale"
            )


@dataclass(frozen=True)
class StabilityDiagramResult:
    """One complete diagram reduced from FIR I/Q traces."""

    x_voltage_mv: np.ndarray
    y_voltage_mv: np.ndarray
    i_mean: np.ndarray
    q_mean: np.ndarray
    magnitude: np.ndarray
    phase_deg: np.ndarray
    x_axis_label: str
    y_axis_label: str
    value_unit: str
    base_value_unit: str
    display_scale: float
    measurement_mode: str
    iteration: int
    repetition_count: int
    samples_per_trace: int
    sample_rate_hz: float = 1_000_000.0
    fir_rate_profile: str = "1_msps"
    source_label: str = ""
    database_path: str = ""
    run_id: int = 0


@dataclass(frozen=True)
class StoredStabilityDiagram:
    """Displayed diagram paired with its full QCoDeS single-shot run."""

    diagram: StabilityDiagramResult
    experiment: StoredQickExperiment

    @property
    def run_id(self) -> int:
        return int(self.experiment.run_id)

    @property
    def database_path(self):
        return self.experiment.database_path


@dataclass(frozen=True)
class StabilityRunSummary:
    """Small metadata-only description used by the Trace Plot run selector."""

    database_path: str
    run_id: int
    created_at_utc: str
    x_axis_label: str
    y_axis_label: str
    x_points: int
    y_points: int
    iq_unit: str
    sample_rate_hz: float

    @property
    def display_label(self) -> str:
        timestamp = self.created_at_utc.replace("T", " ")[:19]
        timestamp_text = f" | {timestamp}" if timestamp else ""
        return (
            f"Run {self.run_id}{timestamp_text} | "
            f"{self.x_axis_label} x {self.y_axis_label} | "
            f"{self.x_points} x {self.y_points} | "
            f"{format_sample_rate_hz(self.sample_rate_hz)} | {self.iq_unit}"
        )


def _stability_axis_metadata(
    metadata: Mapping[str, Any],
) -> Tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Return the stored X/Y axis metadata in the original GUI order."""
    layout = metadata.get("measurement_layout", {})
    if not isinstance(layout, Mapping):
        raise ValueError("stored QICK measurement layout is missing")
    raw_axes = layout.get("sweep_axes", ())
    if not isinstance(raw_axes, Sequence) or isinstance(raw_axes, (str, bytes)):
        raise ValueError("stored QICK sweep-axis metadata is invalid")
    axes = tuple(axis for axis in raw_axes if isinstance(axis, Mapping))
    if len(axes) != 2:
        raise ValueError(
            "a Stability Diagram overlay requires exactly two stored sweep axes"
        )

    gui_settings = metadata.get("gui_settings", {})
    stability_settings = (
        gui_settings.get("stability_diagram", {})
        if isinstance(gui_settings, Mapping)
        else {}
    )
    requested_names = []
    if isinstance(stability_settings, Mapping):
        for key in ("x_axis", "y_axis"):
            axis_settings = stability_settings.get(key, {})
            requested_names.append(
                str(axis_settings.get("output_name", ""))
                if isinstance(axis_settings, Mapping)
                else ""
            )
    if len(requested_names) == 2 and all(requested_names):
        by_output = {
            str(axis.get("output_name", "")): axis
            for axis in axes
        }
        if (
            requested_names[0] in by_output
            and requested_names[1] in by_output
            and requested_names[0] != requested_names[1]
        ):
            return by_output[requested_names[0]], by_output[requested_names[1]]
    return axes[0], axes[1]


def _is_stability_metadata(metadata: Mapping[str, Any]) -> bool:
    """Recognize every saved Stability capture implementation revision."""
    gui_settings = metadata.get("gui_settings", {})
    if not isinstance(gui_settings, Mapping):
        return False
    qick_settings = gui_settings.get("qick", {})
    return (
        isinstance(qick_settings, Mapping)
        and bool(qick_settings.get("fir_stability_capture_mode"))
    )


def list_stability_runs(database_path: Any) -> Tuple[StabilityRunSummary, ...]:
    """List saved Stability Diagram runs without loading their I/Q arrays."""
    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"QCoDeS database does not exist: {path}")

    connection = sqlite3.connect(str(path), timeout=30.0)
    try:
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(runs)")
        }
        if "qick_experiment_json" not in columns:
            return ()
        rows = connection.execute(
            "SELECT run_id, qick_experiment_json FROM runs "
            "WHERE qick_experiment_json IS NOT NULL "
            "AND qick_experiment_json != '' "
            "ORDER BY run_id DESC"
        ).fetchall()
    finally:
        connection.close()

    summaries = []
    for run_id, payload_text in rows:
        try:
            metadata = json.loads(payload_text)
            if not isinstance(metadata, Mapping) or not _is_stability_metadata(
                metadata
            ):
                continue
            x_axis, y_axis = _stability_axis_metadata(metadata)
            layout = metadata.get("measurement_layout", {})
            sample_rate_hz = float(
                layout.get(
                    "sample_rate_hz",
                    1.0e6 / float(layout.get("sample_period_us", 1.0)),
                )
            )
            summaries.append(
                StabilityRunSummary(
                    database_path=str(path),
                    run_id=int(run_id),
                    created_at_utc=str(metadata.get("created_at_utc", "")),
                    x_axis_label=str(x_axis.get("output_name", "X")),
                    y_axis_label=str(y_axis.get("output_name", "Y")),
                    x_points=int(x_axis.get("count", 0)),
                    y_points=int(y_axis.get("count", 0)),
                    iq_unit=str(layout.get("iq_unit", "ADC units")),
                    sample_rate_hz=sample_rate_hz,
                )
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return tuple(summaries)


def _stored_coordinate_mv(
    values: Any,
    axis: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> np.ndarray:
    coordinates = np.asarray(values, dtype=np.float64)
    unit = str(axis.get("unit", "")).strip().lower()
    if unit == "mv":
        return coordinates
    if unit == "v":
        return coordinates * 1_000.0
    if unit in {"", "normalized", "fraction"}:
        gui_settings = metadata.get("gui_settings", {})
        qick_settings = (
            gui_settings.get("qick", {})
            if isinstance(gui_settings, Mapping)
            else {}
        )
        full_scale_mv = float(
            qick_settings.get("full_scale_mv", DEFAULT_QICK_FULL_SCALE_MV)
        )
        return coordinates * full_scale_mv
    raise ValueError(
        f"unsupported stored Stability Diagram voltage unit {axis.get('unit')!r}"
    )


def stability_result_from_stored_arrays(
    arrays: Mapping[str, Any],
    *,
    database_path: Any,
    run_id: int,
) -> StabilityDiagramResult:
    """Reduce a saved split-array QCoDeS run into a Stability Diagram grid."""
    metadata = arrays.get("metadata", {})
    if not isinstance(metadata, Mapping) or not _is_stability_metadata(metadata):
        raise ValueError(f"QCoDeS Run {run_id} is not a Stability Diagram run")
    x_axis, y_axis = _stability_axis_metadata(metadata)
    sweep_coordinates = arrays.get("sweep_coordinates", {})
    if not isinstance(sweep_coordinates, Mapping):
        raise ValueError("stored Stability Diagram sweep coordinates are missing")

    x_parameter = str(x_axis["parameter"])
    y_parameter = str(y_axis["parameter"])
    try:
        x_per_repetition = np.asarray(
            sweep_coordinates[x_parameter],
            dtype=np.float64,
        )
        y_per_repetition = np.asarray(
            sweep_coordinates[y_parameter],
            dtype=np.float64,
        )
    except KeyError as exc:
        raise ValueError(
            "stored Stability Diagram coordinate parameters do not match metadata"
        ) from exc
    if (
        x_per_repetition.ndim != 2
        or y_per_repetition.shape != x_per_repetition.shape
    ):
        raise ValueError(
            "stored Stability Diagram coordinates must have "
            "(point, repetition) shape"
        )
    if not (
        np.allclose(x_per_repetition, x_per_repetition[:, :1])
        and np.allclose(y_per_repetition, y_per_repetition[:, :1])
    ):
        raise ValueError(
            "stored Stability Diagram coordinates change between repetitions"
        )

    x_point_mv = _stored_coordinate_mv(
        x_per_repetition[:, 0],
        x_axis,
        metadata,
    )
    y_point_mv = _stored_coordinate_mv(
        y_per_repetition[:, 0],
        y_axis,
        metadata,
    )
    iq = np.asarray(arrays["iq"])
    if iq.ndim != 4 or iq.shape[-1] != 2:
        raise ValueError(
            "stored Stability Diagram IQ must have "
            "(point, repetition, sample, 2) shape"
        )
    if iq.shape[:2] != x_per_repetition.shape:
        raise ValueError(
            "stored Stability Diagram IQ and sweep-coordinate shapes differ"
        )
    point_iq = iq.astype(np.float64, copy=False).mean(axis=(1, 2))
    x_voltage_mv = np.unique(x_point_mv)
    y_voltage_mv = np.unique(y_point_mv)
    expected_points = int(x_voltage_mv.size * y_voltage_mv.size)
    if expected_points != iq.shape[0]:
        raise ValueError(
            "stored Stability Diagram coordinates do not form one complete "
            "Cartesian grid"
        )

    i_mean = np.full((y_voltage_mv.size, x_voltage_mv.size), np.nan)
    q_mean = np.full_like(i_mean, np.nan)
    populated = np.zeros_like(i_mean, dtype=bool)
    for point_index, (x_mv, y_mv) in enumerate(
        zip(x_point_mv, y_point_mv)
    ):
        x_index = int(np.argmin(np.abs(x_voltage_mv - x_mv)))
        y_index = int(np.argmin(np.abs(y_voltage_mv - y_mv)))
        if populated[y_index, x_index]:
            raise ValueError(
                "stored Stability Diagram contains a duplicate Cartesian point"
            )
        populated[y_index, x_index] = True
        i_mean[y_index, x_index] = point_iq[point_index, 0]
        q_mean[y_index, x_index] = point_iq[point_index, 1]
    if not np.all(populated):
        raise ValueError("stored Stability Diagram Cartesian grid is incomplete")

    iq_unit = str(arrays.get("iq_unit", "ADC units"))
    i_mean, q_mean, display_scale = scale_iq_for_display(
        i_mean,
        q_mean,
        iq_unit,
    )
    layout = metadata.get("measurement_layout", {})
    sample_rate_hz = float(
        layout.get(
            "sample_rate_hz",
            1.0e6 / float(layout.get("sample_period_us", 1.0)),
        )
    )
    gui_settings = metadata.get("gui_settings", {})
    qick_settings = (
        gui_settings.get("qick", {})
        if isinstance(gui_settings, Mapping)
        else {}
    )
    path = Path(database_path).expanduser().resolve()
    return StabilityDiagramResult(
        x_voltage_mv=x_voltage_mv,
        y_voltage_mv=y_voltage_mv,
        i_mean=i_mean,
        q_mean=q_mean,
        magnitude=np.hypot(i_mean, q_mean),
        phase_deg=np.degrees(np.arctan2(q_mean, i_mean)),
        x_axis_label=str(x_axis.get("output_name", "X")),
        y_axis_label=str(y_axis.get("output_name", "Y")),
        value_unit=display_scale.unit,
        base_value_unit=display_scale.base_unit,
        display_scale=display_scale.factor,
        measurement_mode=str(arrays.get("measurement_mode", "raw_iq")),
        iteration=1,
        repetition_count=int(
            arrays.get("source_repetition_count", iq.shape[1])
        ),
        samples_per_trace=int(arrays.get("source_sample_count", iq.shape[2])),
        sample_rate_hz=sample_rate_hz,
        fir_rate_profile=str(
            qick_settings.get(
                "fir_rate_profile",
                "50_ksps" if np.isclose(sample_rate_hz, 50_000.0) else "1_msps",
            )
        ),
        source_label=f"QCoDeS Run {int(run_id)}",
        database_path=str(path),
        run_id=int(run_id),
    )


def load_stability_diagram_run(
    database_path: Any,
    run_id: int,
) -> StabilityDiagramResult:
    """Load one saved Stability Diagram QCoDeS run."""
    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"QCoDeS database does not exist: {path}")
    run_id = _integer(run_id, "Stability Diagram Run ID", 1)
    try:
        from qcodes import initialise_or_create_database_at, load_by_id
    except ImportError as exc:
        raise RuntimeError(
            "QCoDeS==0.58.0 is required to load Stability Diagram runs"
        ) from exc
    initialise_or_create_database_at(str(path))
    dataset = load_by_id(run_id)
    arrays = load_qick_iq_arrays(dataset)
    return stability_result_from_stored_arrays(
        arrays,
        database_path=path,
        run_id=run_id,
    )


class StabilityOverlayLoadWorker(QtCore.QObject):
    """Load one saved Stability Diagram without blocking the GUI."""

    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, database_path: str, run_id: int, parent=None):
        super().__init__(parent)
        self._database_path = str(database_path)
        self._run_id = int(run_id)

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            result = load_stability_diagram_run(
                self._database_path,
                self._run_id,
            )
        except Exception:
            self.failed.emit(traceback.format_exc())
            return
        self.finished.emit(result)


class StabilityOverlaySelector(QtWidgets.QGroupBox):
    """Choose the saved Stability Diagram rendered below the AWG trace."""

    load_requested = QtCore.pyqtSignal(str, int, str)
    latest_requested = QtCore.pyqtSignal()
    quantity_changed = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Stability Diagram Overlay", parent)
        self._summaries: Tuple[StabilityRunSummary, ...] = ()
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(6, 4, 6, 4)
        outer.setSpacing(4)

        database_row = QtWidgets.QHBoxLayout()
        database_row.addWidget(QtWidgets.QLabel("DB:"))
        self.database_path = QtWidgets.QLineEdit(DEFAULT_STABILITY_DB_PATH, self)
        self.database_path.setPlaceholderText(
            "Select a QCoDeS database containing Stability Diagram runs"
        )
        database_row.addWidget(self.database_path, 1)
        self.browse_button = QtWidgets.QToolButton(self)
        self.browse_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton)
        )
        self.browse_button.setToolTip("Choose a Stability Diagram QCoDeS database")
        self.browse_button.clicked.connect(self._browse_database)
        database_row.addWidget(self.browse_button)
        self.refresh_button = QtWidgets.QPushButton("Refresh Runs", self)
        self.refresh_button.clicked.connect(self.refresh_runs)
        database_row.addWidget(self.refresh_button)
        outer.addLayout(database_row)

        selection_row = QtWidgets.QHBoxLayout()
        selection_row.addWidget(QtWidgets.QLabel("Saved data:"))
        self.run_combo = QtWidgets.QComboBox(self)
        self.run_combo.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        self.run_combo.setMinimumContentsLength(32)
        selection_row.addWidget(self.run_combo, 1)
        selection_row.addWidget(QtWidgets.QLabel("Plot:"))
        self.quantity_combo = QtWidgets.QComboBox(self)
        for label, key in (
            ("I", "i"),
            ("Q", "q"),
            ("Magnitude", "magnitude"),
            ("Phase", "phase"),
        ):
            self.quantity_combo.addItem(label, key)
        self.quantity_combo.setCurrentIndex(
            self.quantity_combo.findData("magnitude")
        )
        self.quantity_combo.currentIndexChanged.connect(
            self._emit_quantity_changed
        )
        selection_row.addWidget(self.quantity_combo)
        self.load_button = QtWidgets.QPushButton("Load Overlay", self)
        self.load_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton)
        )
        self.load_button.clicked.connect(self._emit_load_requested)
        selection_row.addWidget(self.load_button)
        self.latest_button = QtWidgets.QPushButton("Use Latest Scan", self)
        self.latest_button.clicked.connect(self.latest_requested.emit)
        selection_row.addWidget(self.latest_button)
        outer.addLayout(selection_row)

        self.status = QtWidgets.QLabel(
            "Using the latest in-memory Stability Diagram scan.",
            self,
        )
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        outer.addWidget(self.status)

    @property
    def quantity(self) -> str:
        return str(self.quantity_combo.currentData())

    def _browse_database(self) -> None:
        current = self.database_path.text().strip()
        selected, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Stability Diagram QCoDeS database",
            current,
            "SQLite databases (*.db *.sqlite *.sqlite3);;All files (*)",
        )
        if not selected:
            return
        self.database_path.setText(selected)
        self.refresh_runs()

    def refresh_runs(self) -> None:
        previous_run_id = self.run_combo.currentData()
        try:
            summaries = list_stability_runs(self.database_path.text().strip())
        except Exception as exc:
            self._summaries = ()
            self.run_combo.clear()
            self.status.setText(str(exc))
            return
        self._summaries = summaries
        self.run_combo.clear()
        for summary in summaries:
            self.run_combo.addItem(summary.display_label, summary.run_id)
        if previous_run_id is not None:
            previous_index = self.run_combo.findData(previous_run_id)
            if previous_index >= 0:
                self.run_combo.setCurrentIndex(previous_index)
        if summaries:
            self.status.setText(
                f"Found {len(summaries)} saved Stability Diagram run(s)."
            )
        else:
            self.status.setText(
                "This database contains no saved Stability Diagram runs."
            )

    def _emit_quantity_changed(self) -> None:
        self.quantity_changed.emit(self.quantity)

    def _emit_load_requested(self) -> None:
        run_id = self.run_combo.currentData()
        if run_id is None:
            self.status.setText("Refresh the DB and select a saved run first.")
            return
        self.load_requested.emit(
            self.database_path.text().strip(),
            int(run_id),
            self.quantity,
        )

    def set_loading(self, loading: bool, *, run_id: int = 0) -> None:
        for widget in (
            self.database_path,
            self.browse_button,
            self.refresh_button,
            self.run_combo,
            self.load_button,
            self.latest_button,
        ):
            widget.setEnabled(not loading)
        if loading:
            self.status.setText(f"Loading QCoDeS Run {run_id}...")

    def show_loaded_result(self, result: StabilityDiagramResult) -> None:
        self.set_loading(False)
        self.status.setText(
            f"Pinned {result.source_label or 'saved Stability Diagram'} from "
            f"{result.database_path}; new scans will not replace it."
        )

    def show_latest_result(self, result: Optional[StabilityDiagramResult]) -> None:
        self.set_loading(False)
        if result is None:
            self.status.setText(
                "Using latest scan; no Stability Diagram has been acquired yet."
            )
        else:
            self.status.setText(
                f"Using latest in-memory Stability Diagram scan "
                f"{result.iteration}."
            )


def default_stability_settings(
    output_names: Sequence[str] = ("awg_0", "awg_1"),
    segment_names: Sequence[str] = ("set_0",),
) -> dict:
    """Return settings that remain loadable even before two ports exist.

    ``segment_names`` is accepted for old callers but intentionally ignored.
    Stability scans use their own internal SET/hold segment and never reuse an
    AWG Tuning waveform segment.
    """
    outputs = tuple(str(value) for value in output_names) or ("awg_0",)
    return {
        "x_axis": {
            "output_name": outputs[0],
            "start_mv": DEFAULT_STABILITY_START_MV,
            "stop_mv": DEFAULT_STABILITY_STOP_MV,
            "points": DEFAULT_STABILITY_POINTS,
        },
        "y_axis": {
            "output_name": outputs[1] if len(outputs) > 1 else outputs[0],
            "start_mv": DEFAULT_STABILITY_START_MV,
            "stop_mv": DEFAULT_STABILITY_STOP_MV,
            "points": DEFAULT_STABILITY_POINTS,
        },
        "repetitions_per_point": DEFAULT_STABILITY_REPETITIONS,
        "trace_samples_per_point": DEFAULT_STABILITY_TRACE_SAMPLES,
        "settle_time_us": DEFAULT_STABILITY_SETTLE_US,
        "fpga_trigger_delay_us": None,
        "acquisition_source": "fir_ddr",
        "sweep_mode": "hardware",
        "hardware_rep_delay_us": DEFAULT_STABILITY_HARDWARE_REP_DELAY_US,
        "modulation_frequency_mhz": DEFAULT_STABILITY_MODULATION_FREQUENCY_MHZ,
        "modulation_gain": DEFAULT_STABILITY_MODULATION_GAIN,
        "modulation_power_calibration": {
            "enabled": False,
            "database_path": DEFAULT_STABILITY_POWER_CALIBRATION_DB_PATH,
            "run_id": 0,
            "target_power_dbm": DEFAULT_STABILITY_TARGET_POWER_DBM,
        },
        "bias_t_compensation": {
            "enabled": False,
            "type": "dc",
            "mode": "fixed_voltage",
            "voltage_mv": DEFAULT_STABILITY_BIAS_T_COMPENSATION_MV,
            "duration_us": DEFAULT_BIAS_T_COMPENSATION_DURATION_US,
            "filter_tau_us": DEFAULT_BIAS_T_FILTER_TAU_US,
        },
        "rf_path": dict(DEFAULT_STABILITY_RF_PATH),
        "color_ranges": {
            name: dict(values)
            for name, values in DEFAULT_STABILITY_COLOR_RANGES.items()
        },
        "visible_data": list(DEFAULT_STABILITY_VISIBLE_DATA),
        "database_path": DEFAULT_STABILITY_DB_PATH,
        "iq_storage_mode": DEFAULT_IQ_STORAGE_MODE,
        "saved_plot_database_path": DEFAULT_STABILITY_DB_PATH,
        "saved_plot_run_id": 0,
        "saved_plot_data": "magnitude",
        "measurement_representation": "adc",
        "dc_measure_gain_v_per_a": 1.0,
        "dc_voltage_calibration_enabled": False,
        "dc_voltage_calibration_database_path": "",
        "dc_voltage_calibration_run_id": 0,
    }


def normalize_stability_settings(
    settings: Optional[Mapping[str, Any]],
    *,
    output_names: Sequence[str],
    segment_names: Sequence[str] = (),
) -> dict:
    """Validate a JSON settings object without requiring runnable hardware.

    Legacy ``segment_name`` entries and ``segment_names`` are ignored. They
    referred to AWG Tuning waveform segments, which are no longer part of a
    Stability Diagram acquisition.
    """
    outputs = tuple(str(value) for value in output_names)
    defaults = default_stability_settings(outputs)
    if settings is None:
        return defaults
    if not isinstance(settings, Mapping):
        raise TypeError("stability_diagram must be a JSON object")

    normalized = {}
    for key, label in (("x_axis", "X"), ("y_axis", "Y")):
        raw_axis = settings.get(key, defaults[key])
        if not isinstance(raw_axis, Mapping):
            raise TypeError(f"stability {label} axis must be a JSON object")
        output_name = str(raw_axis.get("output_name", defaults[key]["output_name"]))
        gen_ch = raw_axis.get("gen_ch")
        if gen_ch is not None:
            gen_ch = _integer(gen_ch, f"stability {label} generator", 0)
            if gen_ch > 255 or not output_name:
                raise ValueError(f"invalid stability {label} electrode")
        if output_name not in outputs and gen_ch is None:
            raise ValueError(
                f"stability {label} output {output_name!r} is not present"
            )
        normalized[key] = {
            "output_name": output_name,
            "start_mv": _finite_float(
                raw_axis.get("start_mv", defaults[key]["start_mv"]),
                f"stability {label} start voltage",
            ),
            "stop_mv": _finite_float(
                raw_axis.get("stop_mv", defaults[key]["stop_mv"]),
                f"stability {label} stop voltage",
            ),
            "points": _integer(
                raw_axis.get("points", defaults[key]["points"]),
                f"stability {label} point count",
                2,
            ),
        }
        if gen_ch is not None:
            normalized[key]["gen_ch"] = gen_ch
    normalized["repetitions_per_point"] = _integer(
        settings.get(
            "repetitions_per_point",
            defaults["repetitions_per_point"],
        ),
        "stability repetitions per point",
        1,
    )
    normalized["trace_samples_per_point"] = _integer(
        settings.get(
            "trace_samples_per_point",
            defaults["trace_samples_per_point"],
        ),
        "stability FIR trace samples per point",
        1,
    )
    normalized["settle_time_us"] = _finite_float(
        settings.get("settle_time_us", defaults["settle_time_us"]),
        "stability settle time",
    )
    if normalized["settle_time_us"] < 0.0:
        raise ValueError("stability settle time must not be negative")
    normalized["acquisition_source"] = str(
        settings.get("acquisition_source", defaults["acquisition_source"])
    )
    if normalized["acquisition_source"] not in STABILITY_ACQUISITION_SOURCES:
        raise ValueError(
            "stability acquisition source must be one of "
            f"{STABILITY_ACQUISITION_SOURCES}"
        )
    normalized["sweep_mode"] = str(
        settings.get("sweep_mode", defaults["sweep_mode"])
    )
    if normalized["sweep_mode"] not in STABILITY_SWEEP_MODES:
        raise ValueError(
            "stability sweep mode must be one of "
            f"{STABILITY_SWEEP_MODES}"
        )
    normalized["hardware_rep_delay_us"] = _finite_float(
        settings.get(
            "hardware_rep_delay_us",
            defaults["hardware_rep_delay_us"],
        ),
        "stability hardware repetition delay",
    )
    if normalized["hardware_rep_delay_us"] < 0.0:
        raise ValueError(
            "stability hardware repetition delay must not be negative"
        )
    raw_fpga_delay = settings.get(
        "fpga_trigger_delay_us",
        defaults["fpga_trigger_delay_us"],
    )
    normalized["fpga_trigger_delay_us"] = (
        None
        if raw_fpga_delay is None
        else _finite_float(
            raw_fpga_delay,
            "stability FPGA trigger delay",
        )
    )
    if (
        normalized["fpga_trigger_delay_us"] is not None
        and normalized["fpga_trigger_delay_us"] < 0.0
    ):
        raise ValueError(
            "stability FPGA trigger delay must not be negative"
        )
    normalized["modulation_frequency_mhz"] = _finite_float(
        settings.get(
            "modulation_frequency_mhz",
            defaults["modulation_frequency_mhz"],
        ),
        "stability modulation frequency",
    )
    normalized["modulation_gain"] = _integer(
        settings.get("modulation_gain", defaults["modulation_gain"]),
        "stability modulation gain",
        0,
    )
    if normalized["modulation_gain"] > 32767:
        raise ValueError("stability modulation gain must not exceed 32767")
    raw_modulation_calibration = settings.get(
        "modulation_power_calibration",
        defaults["modulation_power_calibration"],
    )
    if not isinstance(raw_modulation_calibration, Mapping):
        raise TypeError(
            "stability modulation power calibration must be a JSON object"
        )
    modulation_calibration_enabled = raw_modulation_calibration.get(
        "enabled",
        defaults["modulation_power_calibration"]["enabled"],
    )
    if not isinstance(
        modulation_calibration_enabled,
        (bool, np.bool_),
    ):
        raise TypeError(
            "stability modulation power calibration enabled must be boolean"
        )
    modulation_calibration_path = str(
        raw_modulation_calibration.get(
            "database_path",
            defaults["modulation_power_calibration"]["database_path"],
        )
    )
    if modulation_calibration_enabled and not modulation_calibration_path.strip():
        raise ValueError(
            "stability modulation power calibration database path is required"
        )
    modulation_calibration_run_id = _integer(
        raw_modulation_calibration.get(
            "run_id",
            defaults["modulation_power_calibration"]["run_id"],
        ),
        "stability modulation power calibration Run ID",
        0,
    )
    if modulation_calibration_run_id > (1 << 31) - 1:
        raise ValueError(
            "stability modulation power calibration Run ID is too large"
        )
    normalized["modulation_power_calibration"] = {
        "enabled": bool(modulation_calibration_enabled),
        "database_path": modulation_calibration_path,
        "run_id": modulation_calibration_run_id,
        "target_power_dbm": _finite_float(
            raw_modulation_calibration.get(
                "target_power_dbm",
                defaults["modulation_power_calibration"]["target_power_dbm"],
            ),
            "stability modulation target output power",
        ),
    }
    raw_bias_t = settings.get(
        "bias_t_compensation",
        defaults["bias_t_compensation"],
    )
    if not isinstance(raw_bias_t, Mapping):
        raise TypeError("stability Bias-T compensation must be a JSON object")
    bias_t_enabled = raw_bias_t.get(
        "enabled",
        defaults["bias_t_compensation"]["enabled"],
    )
    if not isinstance(bias_t_enabled, (bool, np.bool_)):
        raise TypeError("stability Bias-T compensation enabled must be boolean")
    bias_t_type = str(
        raw_bias_t.get("type", defaults["bias_t_compensation"]["type"])
    )
    if bias_t_type not in BIAS_T_COMPENSATION_TYPES:
        raise ValueError(
            "stability Bias-T compensation type must be one of "
            f"{BIAS_T_COMPENSATION_TYPES}"
        )
    bias_t_mode = str(
        raw_bias_t.get("mode", defaults["bias_t_compensation"]["mode"])
    )
    if bias_t_mode not in BIAS_T_COMPENSATION_MODES:
        raise ValueError(
            "stability Bias-T compensation mode must be one of "
            f"{BIAS_T_COMPENSATION_MODES}"
        )
    normalized_bias_t = {
        "enabled": bool(bias_t_enabled),
        "type": bias_t_type,
        "mode": bias_t_mode,
    }
    for key, label in (
        ("voltage_mv", "stability Bias-T compensation voltage"),
        ("duration_us", "stability Bias-T compensation duration"),
        ("filter_tau_us", "stability Bias-T filter tau"),
    ):
        value = _finite_float(
            raw_bias_t.get(key, defaults["bias_t_compensation"][key]),
            label,
        )
        if value <= 0.0:
            raise ValueError(f"{label} must be positive")
        normalized_bias_t[key] = value
    if bias_t_enabled and bias_t_type in ("filter", "dc_rc") and not 10 <= normalized_bias_t["filter_tau_us"] <= 1_000_000:
        raise ValueError("RC tau must be between 10 us and 1000 ms")
    normalized["bias_t_compensation"] = normalized_bias_t
    raw_rf_path = settings.get("rf_path", defaults["rf_path"])
    if not isinstance(raw_rf_path, Mapping):
        raise TypeError("stability RF path must be a JSON object")
    rf_path = dict(defaults["rf_path"])
    rf_path.update({key: raw_rf_path[key] for key in rf_path.keys() & raw_rf_path.keys()})
    for key in ("output_ch", "readout_ch"):
        rf_path[key] = _integer(rf_path[key], f"stability RF path {key}", 0)
    for key in ("output_nqz", "readout_nqz"):
        rf_path[key] = _integer(rf_path[key], f"stability RF path {key}", 1)
        if rf_path[key] > 2:
            raise ValueError(f"stability RF path {key} must be 1 or 2")
    for key in (
        "output_att1_db",
        "output_att2_db",
        "readout_attenuation_db",
        "readout_dc_gain_db",
        "loss1_db",
        "loss2_db",
        "amplifier_gain_db",
        "output_filter_cutoff_ghz",
        "output_filter_bandwidth_ghz",
        "readout_filter_cutoff_ghz",
        "readout_filter_bandwidth_ghz",
    ):
        rf_path[key] = _finite_float(rf_path[key], f"stability RF path {key}")
    for key in ("output_filter_type", "readout_filter_type"):
        rf_path[key] = str(rf_path[key])
        if rf_path[key] not in {"bypass", "lowpass", "highpass", "bandpass"}:
            raise ValueError(f"stability RF path {key} is invalid")
    rf_path["output_board_type"] = str(rf_path["output_board_type"])
    rf_path["input_board_type"] = str(rf_path["input_board_type"])
    normalized["rf_path"] = rf_path
    raw_color_ranges = settings.get(
        "color_ranges",
        defaults["color_ranges"],
    )
    normalized["color_ranges"] = normalize_stability_color_ranges(
        raw_color_ranges
    )
    normalized["visible_data"] = list(
        normalize_stability_visible_data(settings.get("visible_data"))
    )
    database_path = str(
        settings.get("database_path", defaults["database_path"])
    ).strip()
    if not database_path:
        raise ValueError("stability database path must not be empty")
    normalized["database_path"] = database_path
    normalized["iq_storage_mode"] = normalize_iq_storage_mode(
        settings.get("iq_storage_mode", defaults["iq_storage_mode"])
    )
    saved_plot_database_path = str(
        settings.get("saved_plot_database_path", database_path)
    ).strip()
    if not saved_plot_database_path:
        raise ValueError(
            "saved Stability Diagram database path must not be empty"
        )
    normalized["saved_plot_database_path"] = saved_plot_database_path
    normalized["saved_plot_run_id"] = _integer(
        settings.get(
            "saved_plot_run_id",
            defaults["saved_plot_run_id"],
        ),
        "saved Stability Diagram Run ID",
        0,
    )
    saved_plot_data = str(
        settings.get(
            "saved_plot_data",
            defaults["saved_plot_data"],
        )
    )
    if saved_plot_data not in {"i", "q", "magnitude", "phase"}:
        raise ValueError(
            "saved Stability Diagram plot data must be "
            "i, q, magnitude, or phase"
        )
    normalized["saved_plot_data"] = saved_plot_data
    representation = str(
        settings.get(
            "measurement_representation",
            defaults["measurement_representation"],
        )
    )
    if representation not in {"adc", "voltage", "current"}:
        raise ValueError(
            "stability measurement_representation must be adc, voltage, or current"
        )
    normalized["measurement_representation"] = representation
    measurement_gain = _finite_float(
        settings.get(
            "dc_measure_gain_v_per_a",
            defaults["dc_measure_gain_v_per_a"],
        ),
        "stability DC measurement gain",
    )
    if measurement_gain <= 0.0:
        raise ValueError("stability DC measurement gain must be positive")
    normalized["dc_measure_gain_v_per_a"] = measurement_gain
    calibration_enabled = settings.get(
        "dc_voltage_calibration_enabled",
        defaults["dc_voltage_calibration_enabled"],
    )
    if not isinstance(calibration_enabled, (bool, np.bool_)):
        raise TypeError(
            "stability DC voltage calibration enabled must be boolean"
        )
    calibration_path = str(
        settings.get(
            "dc_voltage_calibration_database_path",
            defaults["dc_voltage_calibration_database_path"],
        )
    ).strip()
    if calibration_enabled and not calibration_path:
        raise ValueError(
            "stability DC voltage calibration database path must not be empty"
        )
    normalized["dc_voltage_calibration_enabled"] = bool(calibration_enabled)
    normalized["dc_voltage_calibration_database_path"] = calibration_path
    normalized["dc_voltage_calibration_run_id"] = _integer(
        settings.get(
            "dc_voltage_calibration_run_id",
            defaults["dc_voltage_calibration_run_id"],
        ),
        "stability DC voltage calibration Run ID",
        0,
    )
    return normalized


def build_stability_hold_sequence(
    config: StabilityDiagramConfig,
    *,
    output_names: Sequence[str],
    fabric_mhz: float,
    full_scale_mv: float,
    cross_capacitance=None,
    output_full_scales_mv=None,
    dac_current_settings=None,
    sample_period_us: float = 1.0,
):
    """Build the dedicated SET-and-hold sequence for one Cartesian scan.

    Each hardware sweep point issues one SET on ``set_0`` and holds that
    voltage through the settle interval and the complete HWH-selected FIR capture.
    Stability capture reads the continuously running FIR stream immediately;
    it does not add the DDR V2 event-alignment delay to every point.
    No RAMP or SET segment from the AWG Tuning tab is copied into this path.
    """
    config.validate_full_scale(full_scale_mv)
    names = tuple(str(name) for name in output_names)
    if not names:
        raise ValueError("stability diagram requires AWG output names")
    for axis in (config.x_axis, config.y_axis):
        if axis.output_name not in names:
            raise ValueError(
                f"stability output {axis.output_name!r} is not present"
            )

    sample_period_us = _finite_float(
        sample_period_us,
        "stability FIR sample period",
    )
    if sample_period_us <= 0.0:
        raise ValueError("stability FIR sample period must be positive")
    hold_duration_us = (
        float(config.settle_time_us)
        + float(config.trace_samples_per_point) * sample_period_us
        + DEFAULT_STABILITY_POINT_GUARD_US
    )
    pulses = tuple(
        PulseSequence(
            initial_voltage=0.0,
            initial_duration_ns=hold_duration_us * 1000.0,
        )
        for _name in names
    )
    sweeps = tuple(
        QickSweepSpec(
            segment_name=STABILITY_HOLD_SEGMENT,
            output_name=axis.output_name,
            start=axis.start_mv / full_scale_mv,
            stop=axis.stop_mv / full_scale_mv,
            count=axis.points,
        )
        for axis in (config.x_axis, config.y_axis)
    )
    return build_qick_sequence(
        pulses,
        output_names=names,
        fabric_mhz=fabric_mhz,
        full_scale_mv=full_scale_mv,
        output_full_scales_mv=output_full_scales_mv,
        dac_current_settings=dac_current_settings,
        sweeps=sweeps,
        cross_capacitance=cross_capacitance,
        bias_t_compensation_enabled=config.bias_t_compensation_enabled,
        bias_t_compensation_type=config.bias_t_compensation_type,
        bias_t_compensation_voltage_mv=(
            config.bias_t_compensation_voltage_mv
            if config.bias_t_compensation_enabled
            and config.bias_t_compensation_type in ("dc", "dc_rc")
            and config.bias_t_compensation_mode == "fixed_voltage"
            else None
        ),
        bias_t_compensation_mode=config.bias_t_compensation_mode,
        bias_t_compensation_duration_us=config.bias_t_compensation_duration_us,
        bias_t_filter_tau_us=config.bias_t_filter_tau_us,
    )


def _stability_sequence_at_point(sequence: Any, point_index: int) -> Any:
    """Return a fixed-voltage clone for one host-software sweep point."""
    point_index = _integer(point_index, "stability point index", 0)
    coordinates = np.asarray(sequence.sweep_coordinates, dtype=float)
    if point_index >= coordinates.shape[0]:
        raise IndexError("stability point index is out of range")
    concrete = deepcopy(sequence)
    values = list(concrete.segments[0].amplitudes)
    for axis, value in zip(sequence.sweep_axes, coordinates[point_index]):
        if axis.segment_name != STABILITY_HOLD_SEGMENT:
            raise ValueError(
                "stability software sweep encountered an unexpected segment"
            )
        output_index = concrete.output_names.index(axis.output_name)
        values[output_index] = float(value)
    concrete.segments[0] = replace(
        concrete.segments[0],
        amplitudes=tuple(values),
    )
    concrete.sweeps = []
    concrete._sweep_coordinate_cache = None
    concrete._validate()
    return concrete


@dataclass(frozen=True)
class StabilitySoftwareSweepProgramBundle:
    """One compiled tProcessor program per host-controlled Cartesian point."""

    programs: Tuple[Any, ...]
    sweep_points: np.ndarray

    def summary(self) -> Mapping[str, Any]:
        base = dict(self.programs[-1].summary())
        base.update({
            "stability_sweep_mode": "software",
            "software_sweep_program_count": len(self.programs),
            "software_sweep_points": np.asarray(
                self.sweep_points,
                dtype=float,
            ).tolist(),
        })
        return base

    def __getattr__(self, name: str) -> Any:
        return getattr(self.programs[-1], name)


def _combine_stability_point_results(
    sequence: Any,
    results: Sequence[Any],
) -> Any:
    """Restore a software-point run to the normal Cartesian result shape."""
    if not results:
        raise RuntimeError("stability software sweep produced no results")
    iq_parts = tuple(np.asarray(result.iq) for result in results)
    if any(part.shape[0] != 1 for part in iq_parts):
        raise RuntimeError(
            "each stability software-sweep result must contain one point"
        )
    reference_shape = iq_parts[0].shape[1:]
    if any(part.shape[1:] != reference_shape for part in iq_parts):
        raise RuntimeError(
            "stability software-sweep point results have inconsistent I/Q shapes"
        )
    reserved_values = tuple(
        getattr(result, "reserved_physical_words", None)
        for result in results
    )
    reserved = (
        sum(int(value) for value in reserved_values)
        if all(value is not None for value in reserved_values)
        else None
    )
    return replace(
        results[0],
        sweep_points=sequence.sweep_points.copy(),
        iq=np.concatenate(iq_parts, axis=0),
        reserved_physical_words=reserved,
        sweep_axes=sequence.sweep_axes,
        sweep_shape=sequence.sweep_shape,
        cross_capacitance=sequence.cross_capacitance.copy(),
    )


def reduce_fir_stability_result(
    ddr_result: Any,
    config: StabilityDiagramConfig,
    *,
    full_scale_mv: float,
    iteration: int = 1,
    readout_spec: Optional[Any] = None,
) -> StabilityDiagramResult:
    """Coherently average FIR/AVG I/Q and restore the two voltage axes.

    The arithmetic mean is taken independently on I and Q over all
    repetitions and all FIR-output samples at each Cartesian coordinate.
    Magnitude and phase are then derived from that complex mean.
    """
    config.validate_full_scale(full_scale_mv)
    iq = result_iq_in_input_units(ddr_result)
    if iq.ndim != 4 or iq.shape[-1] != 2:
        raise ValueError(
            "stability I/Q must have shape "
            "(point, repetition, sample, 2)"
        )
    if iq.shape[0] != config.point_count:
        raise ValueError(
            f"received {iq.shape[0]} Cartesian points; "
            f"expected {config.point_count}"
        )

    sweep_axes = tuple(ddr_result.sweep_axes)
    axis_keys = [
        (str(axis.output_name), str(axis.segment_name)) for axis in sweep_axes
    ]
    x_key = (config.x_axis.output_name, config.x_axis.segment_name)
    y_key = (config.y_axis.output_name, config.y_axis.segment_name)
    try:
        x_column = axis_keys.index(x_key)
        y_column = axis_keys.index(y_key)
    except ValueError as exc:
        raise ValueError(
            "acquisition sweep axes do not match the selected stability electrodes"
        ) from exc
    if x_column == y_column:
        raise ValueError("stability result requires two independent sweep axes")

    coordinates = np.asarray(ddr_result.sweep_points, dtype=float)
    if coordinates.ndim != 2 or coordinates.shape != (
        config.point_count,
        len(sweep_axes),
    ):
        raise ValueError(
            "stability sweep-coordinate shape does not match acquisition I/Q"
        )

    point_iq = iq.astype(np.float64, copy=False).mean(axis=(1, 2))
    representation = str(
        getattr(
            readout_spec,
            "effective_measurement_representation",
            "auto",
        )
    )
    if representation == "auto":
        representation = (
            "current"
            if bool(getattr(readout_spec, "dc_measure_mode", False))
            else (
                "voltage"
                if bool(
                    getattr(
                        readout_spec,
                        "dc_voltage_calibration_enabled",
                        False,
                    )
                )
                else "adc"
            )
        )
    if representation not in {"adc", "voltage", "current"}:
        raise ValueError(
            "stability measurement representation must be adc, voltage, or current"
        )
    calibration_enabled = bool(
        getattr(readout_spec, "dc_voltage_calibration_enabled", False)
    )
    if representation != "adc":
        if getattr(readout_spec, "input_board_type", None) != "DC_In":
            raise ValueError("voltage/current display requires a DC_In readout")
        calibration = None
        if calibration_enabled:
            calibration = load_dc_voltage_calibration(
                getattr(
                    readout_spec,
                    "dc_voltage_calibration_database_path",
                    "",
                ),
                readout_ch=int(getattr(readout_spec, "ro_ch", 0)),
                input_dc_gain_db=float(
                    getattr(readout_spec, "dc_gain_db", 0.0)
                ),
                run_id=int(
                    getattr(readout_spec, "dc_voltage_calibration_run_id", 0)
                ),
            )
        if representation == "current":
            point_iq = dc_iq_to_current(
                point_iq,
                getattr(readout_spec, "dc_measure_gain_v_per_a", 1.0),
                calibration=calibration,
            )
            value_unit = "A"
            measurement_mode = "dc_current_iq"
        else:
            point_iq = adc_iq_to_voltage(point_iq, calibration=calibration)
            value_unit = "V"
            measurement_mode = "dc_voltage_iq"
    else:
        value_unit = "ADC units"
        measurement_mode = "raw_iq"
    requested_x = config.x_axis.voltages_mv
    requested_y = config.y_axis.voltages_mv
    x_voltage_mv = np.sort(requested_x)
    y_voltage_mv = np.sort(requested_y)
    i_mean = np.full((y_voltage_mv.size, x_voltage_mv.size), np.nan, dtype=float)
    q_mean = np.full_like(i_mean, np.nan)
    populated = np.zeros_like(i_mean, dtype=bool)

    x_coordinates_mv = coordinates[:, x_column] * float(full_scale_mv)
    y_coordinates_mv = coordinates[:, y_column] * float(full_scale_mv)
    x_tolerance = max(
        1.0e-8,
        abs(float(config.x_axis.stop_mv) - float(config.x_axis.start_mv))
        * 1.0e-8,
    )
    y_tolerance = max(
        1.0e-8,
        abs(float(config.y_axis.stop_mv) - float(config.y_axis.start_mv))
        * 1.0e-8,
    )
    for point_index, (x_mv, y_mv) in enumerate(
        zip(x_coordinates_mv, y_coordinates_mv)
    ):
        x_index = int(np.argmin(np.abs(x_voltage_mv - x_mv)))
        y_index = int(np.argmin(np.abs(y_voltage_mv - y_mv)))
        if abs(float(x_voltage_mv[x_index]) - float(x_mv)) > x_tolerance:
            raise ValueError(f"unexpected X sweep coordinate {x_mv:g} mV")
        if abs(float(y_voltage_mv[y_index]) - float(y_mv)) > y_tolerance:
            raise ValueError(f"unexpected Y sweep coordinate {y_mv:g} mV")
        if populated[y_index, x_index]:
            raise ValueError("duplicate Cartesian coordinate in acquisition result")
        populated[y_index, x_index] = True
        i_mean[y_index, x_index] = point_iq[point_index, 0]
        q_mean[y_index, x_index] = point_iq[point_index, 1]
    if not np.all(populated):
        raise ValueError("acquisition result does not cover the full stability grid")

    i_mean, q_mean, display_scale = scale_iq_for_display(
        i_mean,
        q_mean,
        value_unit,
    )
    magnitude = np.hypot(i_mean, q_mean)
    phase_deg = np.degrees(np.arctan2(q_mean, i_mean))
    return StabilityDiagramResult(
        x_voltage_mv=x_voltage_mv,
        y_voltage_mv=y_voltage_mv,
        i_mean=i_mean,
        q_mean=q_mean,
        magnitude=magnitude,
        phase_deg=phase_deg,
        x_axis_label=config.x_axis.output_name,
        y_axis_label=config.y_axis.output_name,
        value_unit=display_scale.unit,
        base_value_unit=display_scale.base_unit,
        display_scale=display_scale.factor,
        measurement_mode=measurement_mode,
        iteration=_integer(iteration, "stability iteration", 1),
        repetition_count=int(
            getattr(ddr_result, "accumulation_repetitions", iq.shape[1])
        ),
        samples_per_trace=int(iq.shape[2]),
        sample_rate_hz=float(
            getattr(ddr_result, "sample_rate_hz", 1_000_000.0)
        ),
        fir_rate_profile=str(
            getattr(ddr_result, "fir_rate_profile", "1_msps")
        ),
    )


def _stored_gui_settings_with_vertices(
    gui_settings: Mapping[str, Any],
    sequence: Any,
) -> dict:
    stored = dict(gui_settings)
    if not hasattr(sequence, "waveform_vertices"):
        return stored
    qick_settings = stored.get("qick", {})
    if not isinstance(qick_settings, Mapping):
        return stored
    fabric_mhz = float(qick_settings.get("fabric_mhz", 300.0))
    full_scale_mv = float(
        qick_settings.get(
            "full_scale_mv",
            DEFAULT_QICK_FULL_SCALE_MV,
        )
    )
    stored["awg_waveform_recipe"] = build_awg_waveform_recipe(
        sequence,
        fabric_mhz=fabric_mhz,
        full_scale_mv=full_scale_mv,
    )
    metadata_mode = normalize_awg_metadata_mode(
        qick_settings.get("awg_metadata_mode", DEFAULT_AWG_METADATA_MODE)
    )
    if metadata_mode == AWG_METADATA_MODE_EXPANDED:
        stored["awg_waveform_vertices"] = build_awg_vertex_metadata(
            sequence,
            fabric_mhz=fabric_mhz,
            full_scale_mv=full_scale_mv,
        )
    return stored


class StabilityDiagramWorker(QtCore.QObject):
    """Run one saved scan or repeated non-persistent scans off the GUI thread."""

    scan_ready = QtCore.pyqtSignal(object)
    single_finished = QtCore.pyqtSignal(object)
    stopped = QtCore.pyqtSignal()
    failed = QtCore.pyqtSignal(str)
    progress_changed = QtCore.pyqtSignal(int, str)

    def __init__(
        self,
        kwargs: Mapping[str, Any],
        *,
        continuous: bool,
        parent=None,
    ):
        super().__init__(parent)
        self._kwargs = dict(kwargs)
        self._continuous = bool(continuous)
        self._stop_event = Event()

    def request_stop(self) -> None:
        """Stop after the active full hardware scan reaches a safe boundary."""
        self._stop_event.set()

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            self._run()
        except Exception:
            self.failed.emit(traceback.format_exc())

    def _run(self) -> None:
        kwargs = dict(self._kwargs)
        connector = kwargs.pop("connector", None)
        connection_config = kwargs.pop("connection_config")
        run_config = kwargs.pop("run_config", None)
        gui_settings = kwargs.pop("gui_settings", None)
        iq_storage_mode = normalize_iq_storage_mode(
            kwargs.pop("iq_storage_mode", DEFAULT_IQ_STORAGE_MODE)
        )
        stability_config = kwargs.pop("stability_config")
        full_scale_mv = float(kwargs.pop("full_scale_mv"))
        sequence = kwargs["sequence"]
        readout_spec = kwargs["readout_spec"]
        stability_fabric_mhz = float(
            kwargs.pop("stability_fabric_mhz", 300.0)
        )

        self.progress_changed.emit(1, "Connecting to QICK")
        soc, soccfg = connect_qick(connection_config, connector=connector)
        acquisition_source = stability_config.acquisition_source
        fir_profile = None
        if acquisition_source == "fir_ddr":
            fir_profile = resolve_fir_ddr_profile(
                soccfg,
                context="stability diagram",
            )
            sample_rate_hz = float(fir_profile.sample_rate_hz)
            sample_period_us = float(fir_profile.sample_period_us)
        else:
            ro_ch = int(readout_spec.ro_ch)
            if ro_ch >= len(soccfg["readouts"]):
                raise IndexError("stability AVG readout channel is out of range")
            ro_cfg = soccfg["readouts"][ro_ch]
            sample_rate_hz = float(
                ro_cfg.get("f_output", ro_cfg.get("f_fabric", 0.0))
            ) * 1_000_000.0
            if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0.0:
                raise RuntimeError(
                    "selected AVG readout has no valid output sample rate"
                )
            sample_period_us = 1_000_000.0 / sample_rate_hz
        effective_run_config = (
            None
            if run_config is None
            else replace(run_config, sample_rate_hz=sample_rate_hz)
        )
        template_sequence = sequence
        if hasattr(template_sequence, "output_names") and hasattr(
            template_sequence,
            "cross_capacitance",
        ):
            sequence = build_stability_hold_sequence(
                stability_config,
                output_names=template_sequence.output_names,
                fabric_mhz=stability_fabric_mhz,
                full_scale_mv=full_scale_mv,
                output_full_scales_mv=getattr(sequence, 'output_full_scales_mv', None),
                dac_current_settings=getattr(sequence, 'dac_current_settings', None),
                cross_capacitance=template_sequence.cross_capacitance,
                sample_period_us=sample_period_us,
            )
            kwargs["sequence"] = sequence
        capture_window_us = (
            stability_config.trace_samples_per_point
            * sample_period_us
        )
        kwargs["rf_specs"] = tuple(
            replace(
                spec,
                duration_us=max(
                    sample_period_us,
                    float(stability_config.settle_time_us)
                    + capture_window_us,
                ),
            )
            for spec in kwargs.get("rf_specs", ())
        )
        if fir_profile is not None:
            selected_delay_value = fir_profile.selected_trigger_delay_value(
                stability_config.fpga_trigger_delay_us
            )
            selected_delay_us = fir_profile.trigger_delay_us_for(
                selected_delay_value
            )
        else:
            selected_delay_value = 0
            selected_delay_us = 0.0
        if hasattr(kwargs["readout_spec"], "__dataclass_fields__"):
            kwargs["readout_spec"] = replace(
                kwargs["readout_spec"],
                fpga_trigger_delay_samples=None,
                fpga_trigger_delay_us=(
                    stability_config.fpga_trigger_delay_us
                    if fir_profile is not None
                    else None
                ),
            )
        kwargs["acquisition_source"] = acquisition_source
        kwargs["hardware_rep_delay_us"] = (
            stability_config.hardware_rep_delay_us
            if stability_config.sweep_mode == "hardware"
            else 0.0
        )
        if fir_profile is not None:
            timing_message = (
                f"HWH FIR DDR: "
                f"{getattr(fir_profile, 'rate_label', format_sample_rate_hz(sample_rate_hz))} "
                f"({sample_period_us:g} us/sample); "
                f"{stability_config.trace_samples_per_point:,} samples = "
                f"{capture_window_us:g} us; FPGA trigger-to-store delay "
                f"{selected_delay_us:g} us"
            )
        else:
            timing_message = (
                f"AVG buffer: {format_sample_rate_hz(sample_rate_hz)} input, "
                f"{stability_config.trace_samples_per_point:,} integration "
                f"samples = {capture_window_us:g} us; "
                f"{stability_config.repetitions_per_point:,} coherent "
                "repetition(s)"
            )
        self.progress_changed.emit(
            2,
            f"{timing_message}; {stability_config.sweep_mode} sweep",
        )
        if self._stop_event.is_set():
            self.stopped.emit()
            return

        iteration = 0
        while not self._stop_event.is_set():
            iteration += 1

            def scan_progress(percent: int, message: str) -> None:
                self.progress_changed.emit(
                    int(percent),
                    f"Scan {iteration}: {message}",
                )

            if stability_config.sweep_mode == "hardware":
                program, ddr_result, rf_settings = execute_qick_sequence(
                    soc,
                    soccfg,
                    progress_callback=scan_progress,
                    **kwargs,
                )
            else:
                coordinates = np.asarray(sequence.sweep_coordinates, dtype=float)
                programs = []
                point_results = []
                rf_settings = None
                point_total = coordinates.shape[0]
                for point_index in range(point_total):
                    if self._stop_event.is_set():
                        self.stopped.emit()
                        return
                    point_sequence = _stability_sequence_at_point(
                        sequence,
                        point_index,
                    )
                    point_kwargs = dict(kwargs)
                    point_kwargs["sequence"] = point_sequence
                    point_kwargs["hardware_rep_delay_us"] = 0.0

                    def point_progress(percent: int, message: str) -> None:
                        fraction = max(0.0, min(1.0, float(percent) / 100.0))
                        overall = round(
                            100.0
                            * (point_index + fraction)
                            / max(1, point_total)
                        )
                        self.progress_changed.emit(
                            overall,
                            (
                                f"Scan {iteration}, software point "
                                f"{point_index + 1:,}/{point_total:,}: {message}"
                            ),
                        )

                    point_program, point_result, point_rf_settings = (
                        execute_qick_sequence(
                            soc,
                            soccfg,
                            progress_callback=point_progress,
                            **point_kwargs,
                        )
                    )
                    programs.append(point_program)
                    point_results.append(point_result)
                    if rf_settings is None:
                        rf_settings = dict(point_rf_settings)
                ddr_result = _combine_stability_point_results(
                    sequence,
                    point_results,
                )
                program = StabilitySoftwareSweepProgramBundle(
                    programs=tuple(programs),
                    sweep_points=sequence.sweep_points.copy(),
                )
                rf_settings = {} if rf_settings is None else rf_settings
            diagram = reduce_fir_stability_result(
                ddr_result,
                stability_config,
                full_scale_mv=full_scale_mv,
                iteration=iteration,
                readout_spec=readout_spec,
            )
            self.scan_ready.emit(diagram)

            if self._continuous:
                self.progress_changed.emit(
                    100,
                    f"Scan {iteration} complete; starting next scan",
                )
                continue

            if run_config is None or gui_settings is None:
                raise RuntimeError(
                    "single-shot stability acquisition requires QCoDeS settings"
                )
            stored_settings = _stored_gui_settings_with_vertices(
                gui_settings,
                sequence,
            )
            stored_qick = dict(stored_settings.get("qick", {}))
            stored_qick.update({
                "iq_storage_mode": iq_storage_mode,
                "stability_acquisition_source": acquisition_source,
                "stability_sweep_mode": stability_config.sweep_mode,
                "stability_hardware_rep_delay_us": (
                    stability_config.hardware_rep_delay_us
                ),
                "acquisition_sample_rate_hz": sample_rate_hz,
                "acquisition_sample_period_us": sample_period_us,
                "fir_rate_profile": (
                    None if fir_profile is None else fir_profile.name
                ),
                "fir_sample_rate_hz": (
                    None if fir_profile is None else fir_profile.sample_rate_hz
                ),
                "fir_sample_period_us": (
                    None if fir_profile is None else fir_profile.sample_period_us
                ),
                "fir_fpga_trigger_delay_samples": selected_delay_value,
                "fir_fpga_trigger_delay_units": (
                    "none"
                    if fir_profile is None
                    else fir_profile.trigger_delay_units
                ),
                "fir_fpga_trigger_delay_us": selected_delay_us,
                "fir_profile_default_trigger_delay_samples": (
                    0
                    if fir_profile is None
                    else fir_profile.trigger_delay_samples
                ),
                "fir_stability_capture_mode": (
                    "not_applicable_avg_buffer"
                    if fir_profile is None
                    else "programmable_fpga_delay"
                ),
                "fir_software_warmup_compensation": (
                    False
                    if fir_profile is None
                    else fir_profile.software_warmup_compensation
                ),
            })
            stored_settings["qick"] = stored_qick
            dataset, row_count = store_qick_result(
                ddr_result,
                run_config=effective_run_config,
                connection_config=connection_config,
                program_summary=program.summary(),
                gui_settings=stored_settings,
                rf_settings=rf_settings,
                iq_storage_mode=iq_storage_mode,
                progress_callback=self.progress_changed.emit,
            )
            experiment = StoredQickExperiment(
                run_id=int(dataset.run_id),
                guid=str(dataset.guid),
                database_path=effective_run_config.resolved_database_path,
                row_count=int(row_count),
                dataset=dataset,
                program=program,
                ddr_result=ddr_result,
                rf_settings=rf_settings,
                iq_storage_mode=iq_storage_mode,
            ).detach_dataset()
            self.single_finished.emit(
                StoredStabilityDiagram(diagram=diagram, experiment=experiment)
            )
            return
        self.stopped.emit()


class _StabilityAxisEditor(QtWidgets.QGroupBox):
    """Compact editor for one voltage axis."""

    front_panel_requested = QtCore.pyqtSignal(object)

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        form = QtWidgets.QFormLayout(self)
        self.output = QtWidgets.QComboBox(self)
        self._front_panel_configuration = None
        self.front_panel_button = QtWidgets.QPushButton(
            "Select DAC SMA on Front Panel",
            self,
        )
        self.front_panel_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton)
        )
        self.front_panel_button.clicked.connect(
            lambda: self.front_panel_requested.emit(self)
        )
        self.front_panel_status = QtWidgets.QLabel("Not identified", self)
        self.front_panel_status.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        front_panel_row = QtWidgets.QHBoxLayout()
        front_panel_row.addWidget(self.front_panel_button)
        front_panel_row.addWidget(self.front_panel_status, 1)
        self.start_mv = self._voltage_spin(DEFAULT_STABILITY_START_MV)
        self.stop_mv = self._voltage_spin(DEFAULT_STABILITY_STOP_MV)
        self.points = QtWidgets.QSpinBox(self)
        self.points.setRange(2, 1_000_000)
        self.points.setValue(DEFAULT_STABILITY_POINTS)
        form.addRow("Electrode SMA:", front_panel_row)
        form.addRow("AWG electrode:", self.output)
        form.addRow("Start:", self.start_mv)
        form.addRow("Stop:", self.stop_mv)
        form.addRow("Points:", self.points)
        self.output.currentIndexChanged.connect(self._sync_front_panel_status)

    @staticmethod
    def _voltage_spin(value: float) -> QtWidgets.QDoubleSpinBox:
        widget = QtWidgets.QDoubleSpinBox()
        widget.setRange(-1.0e6, 1.0e6)
        widget.setDecimals(6)
        widget.setValue(float(value))
        widget.setSuffix(" mV")
        return widget

    def refresh_targets(
        self,
        outputs: Sequence[Tuple[str, int]],
        *,
        preferred_output_index: int,
    ) -> None:
        previous_output = self.output.currentData()
        previous_generator = self.current_gen_ch()
        with QtCore.QSignalBlocker(self.output):
            self.output.clear()
            for output_name, gen_ch in outputs:
                self.output.addItem(f"{output_name} (gen {gen_ch})", output_name)
                self.output.setItemData(
                    self.output.count() - 1,
                    int(gen_ch),
                    QtCore.Qt.UserRole + 1,
                )
            output_index = self.output.findData(previous_output)
            # Keep the selected physical DAC when AWG Tuning is remapped.
            if previous_generator >= 0:
                output_index = self.output.findData(
                    previous_generator, QtCore.Qt.UserRole + 1,
                )
            if output_index < 0 and self.output.count():
                output_index = min(preferred_output_index, self.output.count() - 1)
            self.output.setCurrentIndex(output_index)
        self._sync_front_panel_status()

    def current_gen_ch(self) -> int:
        value = self.output.currentData(QtCore.Qt.UserRole + 1)
        return -1 if value is None else int(value)

    def front_panel_values(self) -> Mapping[str, Any]:
        return {
            "output_ch": self.current_gen_ch(),
            "output_board_type": "DC_Out",
            "output_nqz": 1,
            "output_att1_db": 0.0,
            "output_att2_db": 0.0,
            "output_filter_type": "bypass",
            "output_filter_cutoff_ghz": 2.5,
            "output_filter_bandwidth_ghz": 1.0,
        }

    def apply_front_panel_settings(self, values: Mapping[str, Any]) -> None:
        generator = int(values["output_ch"])
        validate_awg_output_channels(self._front_panel_configuration, (generator,))
        match = -1
        for index in range(self.output.count()):
            if int(self.output.itemData(index, QtCore.Qt.UserRole + 1)) == generator:
                match = index
                break
        if match < 0:
            raise ValueError(
                f"generator {generator} is not an available AWG Tuning output"
            )
        self.output.setCurrentIndex(match)
        panel_port = values.get("output_panel_port")
        self.front_panel_status.setText(
            f"DAC{int(panel_port)} / gen {generator}"
            if panel_port is not None
            else f"generator {generator}"
        )

    def set_front_panel_configuration(self, configuration) -> None:
        self._front_panel_configuration = configuration
        self._sync_front_panel_status()

    def _sync_front_panel_status(self, *_args) -> None:
        generator = self.current_gen_ch()
        if self._front_panel_configuration is not None:
            for port in self._front_panel_configuration.outputs:
                if generator in port.qick_channels:
                    self.front_panel_status.setText(
                        f"{port.label} / gen {generator} / {port.board_label}"
                    )
                    return
        self.front_panel_status.setText(
            "Not identified" if generator < 0 else f"generator {generator}"
        )

    def settings_dict(self) -> dict:
        return {
            "output_name": str(self.output.currentData() or ""),
            "gen_ch": self.current_gen_ch(),
            "start_mv": self.start_mv.value(),
            "stop_mv": self.stop_mv.value(),
            "points": self.points.value(),
        }

    def load_settings(self, settings: Mapping[str, Any]) -> None:
        output_index = self.output.findData(str(settings["output_name"]))
        if settings.get("gen_ch") is not None:
            generator = _integer(settings["gen_ch"], "stability generator", 0)
            validate_awg_output_channels(self._front_panel_configuration, (generator,))
            output_index = self.output.findData(generator, QtCore.Qt.UserRole + 1)
            if output_index < 0 and self._front_panel_configuration is None:
                name = f"gen_{generator}"
                self.output.addItem(f"{name} (gen {generator})", name)
                output_index = self.output.count() - 1
                self.output.setItemData(output_index, generator, QtCore.Qt.UserRole + 1)
        if output_index < 0:
            raise ValueError("saved stability electrode is not present")
        self.output.setCurrentIndex(output_index)
        self.start_mv.setValue(float(settings["start_mv"]))
        self.stop_mv.setValue(float(settings["stop_mv"]))
        self.points.setValue(int(settings["points"]))

    def value(self) -> StabilitySweepAxis:
        return StabilitySweepAxis(
            output_name=str(self.output.currentData() or ""),
            start_mv=self.start_mv.value(),
            stop_mv=self.stop_mv.value(),
            points=self.points.value(),
        )


if pg is not None:

    class _StabilityColorRangeControl(QtWidgets.QGroupBox):
        """Compact numeric editor for one image's applied color levels."""

        levels_changed = QtCore.pyqtSignal(float, float)

        def __init__(
            self,
            title: str,
            *,
            auto: bool,
            minimum: float,
            maximum: float,
            unit: str,
            parent=None,
        ):
            super().__init__(title, parent)
            self._unit = str(unit)
            self._data_levels = (float(minimum), float(maximum))
            grid = QtWidgets.QGridLayout(self)
            grid.setContentsMargins(6, 4, 6, 4)
            grid.setHorizontalSpacing(6)
            grid.setVerticalSpacing(2)

            self.auto_range = QtWidgets.QCheckBox("Auto from data", self)
            self.minimum = self._level_spin(minimum)
            self.maximum = self._level_spin(maximum)
            self.range_status = QtWidgets.QLabel(self)
            self.range_status.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse
            )
            self.range_status.setWordWrap(True)
            grid.addWidget(self.auto_range, 0, 0, 1, 4)
            grid.addWidget(QtWidgets.QLabel("Min:", self), 1, 0)
            grid.addWidget(self.minimum, 1, 1)
            grid.addWidget(QtWidgets.QLabel("Max:", self), 1, 2)
            grid.addWidget(self.maximum, 1, 3)
            grid.addWidget(self.range_status, 2, 0, 1, 4)
            grid.setColumnStretch(1, 1)
            grid.setColumnStretch(3, 1)

            self.auto_range.setChecked(bool(auto))
            self.auto_range.toggled.connect(self._auto_toggled)
            self.minimum.editingFinished.connect(self._manual_edited)
            self.maximum.editingFinished.connect(self._manual_edited)
            self._update_editable()
            self._refresh_status()

        def _level_spin(self, value: float) -> QtWidgets.QDoubleSpinBox:
            spin = QtWidgets.QDoubleSpinBox(self)
            spin.setRange(-1.0e15, 1.0e15)
            spin.setDecimals(12)
            spin.setValue(float(value))
            spin.setKeyboardTracking(False)
            spin.setMinimumWidth(90)
            spin.setMaximumWidth(150)
            spin.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Fixed,
            )
            if hasattr(
                QtWidgets.QAbstractSpinBox,
                "AdaptiveDecimalStepType",
            ):
                spin.setStepType(
                    QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType
                )
            return spin

        @staticmethod
        def _format(value: float) -> str:
            return f"{float(value):.8g}"

        def _set_editor_levels(self, minimum: float, maximum: float) -> None:
            with QtCore.QSignalBlocker(self.minimum), QtCore.QSignalBlocker(
                self.maximum
            ):
                self.minimum.setValue(float(minimum))
                self.maximum.setValue(float(maximum))

        def _update_editable(self) -> None:
            manual = not self.auto_range.isChecked()
            self.minimum.setEnabled(manual)
            self.maximum.setEnabled(manual)

        def _valid_levels(self) -> Optional[Tuple[float, float]]:
            minimum = float(self.minimum.value())
            maximum = float(self.maximum.value())
            if not np.isfinite(minimum) or not np.isfinite(maximum):
                return None
            if minimum >= maximum:
                return None
            return minimum, maximum

        def _refresh_status(self) -> None:
            levels = self._valid_levels()
            if levels is None:
                self.range_status.setText("Min must be below Max")
                self.range_status.setStyleSheet("QLabel { color: #b3261e; }")
                return
            self.range_status.setStyleSheet("")
            minimum, maximum = levels
            data_minimum, data_maximum = self._data_levels
            self.range_status.setText(
                f"Applied: {self._format(minimum)} to "
                f"{self._format(maximum)} {self._unit} | "
                f"Data: {self._format(data_minimum)} to "
                f"{self._format(data_maximum)} {self._unit}"
            )

        def _emit_levels(self) -> None:
            levels = self._valid_levels()
            self._refresh_status()
            if levels is not None:
                self.levels_changed.emit(*levels)

        def _auto_toggled(self, checked: bool) -> None:
            self._update_editable()
            if checked:
                self._set_editor_levels(*self._data_levels)
            self._emit_levels()

        def _manual_edited(self) -> None:
            self._emit_levels()

        def set_unit(self, unit: str) -> None:
            self._unit = str(unit)
            self._refresh_status()

        def set_data_levels(self, minimum: float, maximum: float) -> None:
            self._data_levels = (float(minimum), float(maximum))
            if self.auto_range.isChecked():
                self._set_editor_levels(minimum, maximum)
            self._emit_levels()

        def set_manual_levels(
            self,
            minimum: float,
            maximum: float,
            *,
            emit: bool = True,
        ) -> None:
            minimum = float(minimum)
            maximum = float(maximum)
            if (
                not np.isfinite(minimum)
                or not np.isfinite(maximum)
                or minimum >= maximum
            ):
                raise ValueError("color minimum must be finite and below maximum")
            with QtCore.QSignalBlocker(self.auto_range):
                self.auto_range.setChecked(False)
            self._set_editor_levels(minimum, maximum)
            self._update_editable()
            self._refresh_status()
            if emit:
                self.levels_changed.emit(minimum, maximum)

        def levels(self) -> Tuple[float, float]:
            levels = self._valid_levels()
            if levels is None:
                raise ValueError("color minimum must be below maximum")
            return levels

        def settings_dict(self) -> dict:
            minimum, maximum = self.levels()
            return {
                "auto": self.auto_range.isChecked(),
                "minimum": minimum,
                "maximum": maximum,
            }

        def load_settings(self, settings: Mapping[str, Any]) -> None:
            with QtCore.QSignalBlocker(self.auto_range):
                self.auto_range.setChecked(bool(settings["auto"]))
            self._set_editor_levels(
                float(settings["minimum"]),
                float(settings["maximum"]),
            )
            self._update_editable()
            if self.auto_range.isChecked():
                self._set_editor_levels(*self._data_levels)
            self._emit_levels()


    class StabilityDiagramPlotWidget(QtWidgets.QWidget):
        """Selectable I, Q, magnitude, and angle image plots."""

        _PLOT_SPECS = (
            ("i", "I", "CET-D1"),
            ("q", "Q", "CET-D1"),
            ("magnitude", "Magnitude", "viridis"),
            ("phase", "Angle", "CET-C7"),
        )

        def __init__(self, parent=None):
            super().__init__(parent)
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            selector_layout = QtWidgets.QHBoxLayout()
            selector_layout.setContentsMargins(4, 2, 4, 2)
            selector_layout.addWidget(QtWidgets.QLabel("Displayed data:", self))
            self.data_selectors = {}
            for key, title, _color_map in self._PLOT_SPECS:
                selector = QtWidgets.QCheckBox(title, self)
                selector.setChecked(key in DEFAULT_STABILITY_VISIBLE_DATA)
                selector.toggled.connect(
                    lambda checked, name=key: self._set_plot_visible(
                        name,
                        checked,
                    )
                )
                selector_layout.addWidget(selector)
                self.data_selectors[key] = selector
            selector_layout.addStretch(1)
            layout.addLayout(selector_layout)

            self.plot_grid = QtWidgets.QGridLayout()
            self.plot_grid.setContentsMargins(0, 0, 0, 0)
            self.plot_grid.setSpacing(4)
            layout.addLayout(self.plot_grid, 1)
            self.plots = {}
            self.images = {}
            self.range_controls = {}
            self.color_bars = {}
            self.plot_cells = {}
            self._mouse_connections = []
            for key, title, color_map_name in self._PLOT_SPECS:
                defaults = DEFAULT_STABILITY_COLOR_RANGES[key]
                unit = "deg" if key == "phase" else "ADC units"
                cell = QtWidgets.QWidget(self)
                cell_layout = QtWidgets.QVBoxLayout(cell)
                cell_layout.setContentsMargins(0, 0, 0, 0)
                cell_layout.setSpacing(2)
                range_control = _StabilityColorRangeControl(
                    f"{title} color range",
                    auto=defaults["auto"],
                    minimum=defaults["minimum"],
                    maximum=defaults["maximum"],
                    unit=unit,
                    parent=cell,
                )
                plot = pg.PlotWidget(cell)
                image = pg.ImageItem(axisOrder="row-major")
                plot.addItem(image)
                plot.setTitle(title)
                plot.setLabel("bottom", "X electrode", units="mV")
                plot.setLabel("left", "Y electrode", units="mV")
                plot.showGrid(x=True, y=True, alpha=0.18)
                color_map = self._color_map(color_map_name)
                image.setColorMap(color_map)
                color_bar = attach_color_bar(
                    plot,
                    image,
                    color_map,
                    unit=unit,
                    levels=(defaults["minimum"], defaults["maximum"]),
                    range_control=range_control,
                )
                cell_layout.addWidget(range_control)
                cell_layout.addWidget(plot, 1)
                self.plots[key] = plot
                self.images[key] = image
                self.range_controls[key] = range_control
                self.color_bars[key] = color_bar
                self.plot_cells[key] = cell
                range_control.levels_changed.connect(
                    lambda minimum, maximum, name=key: self._set_color_levels(
                        name,
                        minimum,
                        maximum,
                    )
                )
                slot = lambda event, source=plot: self._mouse_moved(
                    event,
                    source,
                )
                plot.scene().sigMouseMoved.connect(slot)
                self._mouse_connections.append(
                    (plot.scene().sigMouseMoved, slot)
                )

            self.magnitude_range_control = self.range_controls["magnitude"]
            self.phase_range_control = self.range_controls["phase"]
            self.magnitude_plot = self.plots["magnitude"]
            self.phase_plot = self.plots["phase"]
            self.magnitude_image = self.images["magnitude"]
            self.phase_image = self.images["phase"]
            self.magnitude_color_bar = self.color_bars["magnitude"]
            self.phase_color_bar = self.color_bars["phase"]
            self._reflow_visible_plots()
            self.hover_status = QtWidgets.QLabel("No stability scan acquired", self)
            self.hover_status.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse
            )
            layout.addWidget(self.hover_status)
            self._result: Optional[StabilityDiagramResult] = None
            self._setting_color_levels = False

        def _set_plot_visible(self, name: str, checked: bool) -> None:
            if not checked and not any(
                selector.isChecked()
                for key, selector in self.data_selectors.items()
                if key != name
            ):
                with QtCore.QSignalBlocker(self.data_selectors[name]):
                    self.data_selectors[name].setChecked(True)
                checked = True
            self.plot_cells[name].setVisible(checked)
            self._reflow_visible_plots()
            if checked and getattr(self, "_result", None) is not None:
                self.plots[name].enableAutoRange(x=True, y=True)

        def _reflow_visible_plots(self) -> None:
            visible = [
                key
                for key, _title, _color_map in self._PLOT_SPECS
                if self.data_selectors[key].isChecked()
            ]
            for cell in self.plot_cells.values():
                self.plot_grid.removeWidget(cell)
                cell.setVisible(cell in [self.plot_cells[key] for key in visible])
            columns = 2 if len(visible) > 1 else 1
            for index, key in enumerate(visible):
                self.plot_grid.addWidget(
                    self.plot_cells[key],
                    index // columns,
                    index % columns,
                )

        def visible_data(self) -> Tuple[str, ...]:
            return tuple(
                key
                for key, _title, _color_map in self._PLOT_SPECS
                if self.data_selectors[key].isChecked()
            )

        def load_visible_data(self, values: Any) -> None:
            visible = set(normalize_stability_visible_data(values))
            for key, selector in self.data_selectors.items():
                with QtCore.QSignalBlocker(selector):
                    selector.setChecked(key in visible)
            self._reflow_visible_plots()
            self.fit_view()

        @staticmethod
        def _color_map(name: str):
            try:
                return pg.colormap.get(name)
            except (FileNotFoundError, KeyError):
                return pg.colormap.get("viridis")

        def _color_items(self, name: str):
            if name == "angle":
                name = "phase"
            if name not in self.images:
                raise KeyError(f"unknown stability color range {name!r}")
            return (
                self.images[name],
                self.range_controls[name],
                self.color_bars[name],
            )

        def _set_color_levels(
            self,
            name: str,
            minimum: float,
            maximum: float,
        ) -> None:
            image, _control, color_bar = self._color_items(name)
            self._setting_color_levels = True
            try:
                if color_bar is None:
                    image.setLevels((minimum, maximum))
                else:
                    color_bar.setLevels((minimum, maximum))
            finally:
                self._setting_color_levels = False

        def color_range_settings(self) -> dict:
            return {
                name: control.settings_dict()
                for name, control in self.range_controls.items()
            }

        def load_color_range_settings(
            self,
            settings: Mapping[str, Any],
        ) -> None:
            normalized = normalize_stability_color_ranges(settings)
            for name, control in self.range_controls.items():
                control.load_settings(normalized[name])

        @staticmethod
        def _levels(values: np.ndarray) -> Tuple[float, float]:
            low = float(np.nanmin(values))
            high = float(np.nanmax(values))
            if np.isclose(low, high):
                delta = max(1.0, abs(low) * 0.01)
                low -= delta
                high += delta
            return low, high

        @staticmethod
        def _axis_edges(values: np.ndarray) -> Tuple[float, float]:
            if values.size == 1:
                return float(values[0] - 0.5), float(values[0] + 0.5)
            step = float(np.median(np.diff(values)))
            return float(values[0] - step / 2.0), float(values[-1] + step / 2.0)

        def set_result(self, result: StabilityDiagramResult) -> None:
            self._result = result
            self.plots["i"].setTitle(f"I [{result.value_unit}]")
            self.plots["q"].setTitle(f"Q [{result.value_unit}]")
            self.plots["magnitude"].setTitle(
                f"Magnitude [{result.value_unit}]"
            )
            self.plots["phase"].setTitle("Angle [deg]")
            for plot in self.plots.values():
                plot.setLabel("bottom", result.x_axis_label, units="mV")
                plot.setLabel("left", result.y_axis_label, units="mV")
            x_low, x_high = self._axis_edges(result.x_voltage_mv)
            y_low, y_high = self._axis_edges(result.y_voltage_mv)
            rect = QtCore.QRectF(
                x_low,
                y_low,
                x_high - x_low,
                y_high - y_low,
            )
            image_values = {
                "i": result.i_mean,
                "q": result.q_mean,
                "magnitude": result.magnitude,
                "phase": result.phase_deg,
            }
            levels = {
                "i": self._symmetric_levels(result.i_mean),
                "q": self._symmetric_levels(result.q_mean),
                "magnitude": self._levels(result.magnitude),
                "phase": self._levels(result.phase_deg),
            }
            for key, values in image_values.items():
                self.images[key].setImage(values, autoLevels=False)
                unit = "deg" if key == "phase" else result.value_unit
                self.range_controls[key].set_unit(unit)
                self.range_controls[key].set_data_levels(*levels[key])
                color_bar = self.color_bars[key]
                if color_bar is not None:
                    color_bar.setLabel("right", text=unit)
                self.images[key].setRect(rect)
            self.fit_view()
            source_label = (
                result.source_label or f"Scan {result.iteration}"
            )
            self.hover_status.setText(
                f"{source_label}: {result.repetition_count} repetitions, "
                f"{result.samples_per_trace} FIR samples per point; "
                f"display {result.value_unit} "
                f"({result.display_scale:g} x {result.base_value_unit})"
            )

        def fit_view(self) -> None:
            for key, plot in self.plots.items():
                if self.data_selectors[key].isChecked():
                    plot.enableAutoRange(x=True, y=True)

        @staticmethod
        def _symmetric_levels(values: np.ndarray) -> Tuple[float, float]:
            limit = float(np.nanmax(np.abs(values)))
            if np.isclose(limit, 0.0):
                limit = 1.0
            return -limit, limit

        def closeEvent(self, event) -> None:
            for signal, slot in self._mouse_connections:
                try:
                    signal.disconnect(slot)
                except (RuntimeError, TypeError):
                    pass
            self._mouse_connections.clear()
            super().closeEvent(event)

        def _mouse_moved(self, event, plot) -> None:
            if self._result is None:
                return
            position = event[0] if isinstance(event, tuple) else event
            if not plot.sceneBoundingRect().contains(position):
                return
            point = plot.plotItem.vb.mapSceneToView(position)
            x_index = int(
                np.argmin(np.abs(self._result.x_voltage_mv - point.x()))
            )
            y_index = int(
                np.argmin(np.abs(self._result.y_voltage_mv - point.y()))
            )
            self.hover_status.setText(
                f"{self._result.x_axis_label} "
                f"{self._result.x_voltage_mv[x_index]:.6g} mV | "
                f"{self._result.y_axis_label} "
                f"{self._result.y_voltage_mv[y_index]:.6g} mV | "
                f"I {self._result.i_mean[y_index, x_index]:.6g} "
                f"{self._result.value_unit} | "
                f"Q {self._result.q_mean[y_index, x_index]:.6g} "
                f"{self._result.value_unit} | "
                f"Mag {self._result.magnitude[y_index, x_index]:.6g} "
                f"{self._result.value_unit} | "
                f"Phase {self._result.phase_deg[y_index, x_index]:.6g} deg"
            )

else:

    class StabilityDiagramPlotWidget(QtWidgets.QLabel):
        """Dependency error shown only when the required plot package is absent."""

        def __init__(self, parent=None):
            super().__init__("pyqtgraph is required for stability-diagram plots", parent)
            self.setAlignment(QtCore.Qt.AlignCenter)
            self._color_ranges = {
                name: dict(values)
                for name, values in DEFAULT_STABILITY_COLOR_RANGES.items()
            }
            self._visible_data = DEFAULT_STABILITY_VISIBLE_DATA

        def set_result(self, _result: StabilityDiagramResult) -> None:
            return

        def fit_view(self) -> None:
            return

        def color_range_settings(self) -> dict:
            return {
                name: dict(values)
                for name, values in self._color_ranges.items()
            }

        def load_color_range_settings(
            self,
            settings: Mapping[str, Any],
        ) -> None:
            self._color_ranges = normalize_stability_color_ranges(settings)

        def visible_data(self) -> Tuple[str, ...]:
            return self._visible_data

        def load_visible_data(self, values: Any) -> None:
            self._visible_data = normalize_stability_visible_data(values)


class StabilityDiagramPanel(QtWidgets.QWidget):
    """Controls and live plots for a two-electrode hardware sweep."""

    start_requested = QtCore.pyqtSignal()
    stop_requested = QtCore.pyqtSignal()
    single_shot_requested = QtCore.pyqtSignal()
    saved_run_requested = QtCore.pyqtSignal(str, int)
    dc_measure_changed = QtCore.pyqtSignal(bool, float)
    dc_calibration_changed = QtCore.pyqtSignal(bool, str, int)
    path_settings_applied = QtCore.pyqtSignal(object)
    front_panel_requested = QtCore.pyqtSignal()
    electrode_front_panel_requested = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._front_panel_configuration = None
        self._awg_targets = ((), ())
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        self.controls_scroll = QtWidgets.QScrollArea(self)
        self.controls_scroll.setWidgetResizable(True)
        self.controls_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        controls_content = QtWidgets.QWidget(self.controls_scroll)
        controls = QtWidgets.QVBoxLayout(controls_content)
        controls.setContentsMargins(2, 2, 2, 2)
        controls.setSpacing(6)

        self.path_diagram = RfPathCorrectionWidget(controls_content, compact=True)
        self.path_diagram.settings_applied.connect(self._apply_local_path_settings)
        self.path_diagram.front_panel_requested.connect(
            self.front_panel_requested.emit
        )
        self.front_panel_preview = self.path_diagram.front_panel_preview
        self.path_diagram.layout().removeWidget(self.front_panel_preview)
        self.front_panel_preview.setParent(self)
        outer.addWidget(self.front_panel_preview)
        controls.addWidget(self.path_diagram)
        self._path_aux = {
            key: value
            for key, value in DEFAULT_STABILITY_RF_PATH.items()
            if "filter" in key
        }

        self.x_axis = _StabilityAxisEditor("X Electrode", controls_content)
        self.y_axis = _StabilityAxisEditor("Y Electrode", controls_content)
        self.x_axis.front_panel_requested.connect(
            self.electrode_front_panel_requested.emit
        )
        self.y_axis.front_panel_requested.connect(
            self.electrode_front_panel_requested.emit
        )
        controls.addWidget(self.x_axis)
        controls.addWidget(self.y_axis)

        acquisition = QtWidgets.QGroupBox("Acquisition", controls_content)
        acquisition_form = QtWidgets.QFormLayout(acquisition)
        self.repetitions = QtWidgets.QSpinBox(acquisition)
        self.repetitions.setRange(1, 1_000_000)
        self.repetitions.setValue(DEFAULT_STABILITY_REPETITIONS)
        self.trace_samples = QtWidgets.QSpinBox(acquisition)
        self.trace_samples.setRange(1, 10_000_000)
        self.trace_samples.setValue(DEFAULT_STABILITY_TRACE_SAMPLES)
        self.trace_samples.setToolTip(
            "FIR DDR: stored samples per repetition. AVG buffer: input "
            "samples integrated into one coherent I/Q value per repetition."
        )
        self.acquisition_source = QtWidgets.QComboBox(acquisition)
        self.acquisition_source.addItem("FIR DDR traces", "fir_ddr")
        self.acquisition_source.addItem(
            "AVG buffer accumulated I/Q",
            "avg_buffer",
        )
        self.acquisition_source.setToolTip(
            "FIR DDR stores a trace. AVG buffer integrates the selected "
            "readout window and returns one coherently averaged I/Q value."
        )
        self.sweep_mode = QtWidgets.QComboBox(acquisition)
        self.sweep_mode.addItem(
            "Hardware Cartesian (tProcessor)",
            "hardware",
        )
        self.sweep_mode.addItem(
            "Software Cartesian (host PC)",
            "software",
        )
        self.sweep_mode.setToolTip(
            "Hardware mode executes X, Y, and repetition loops in one "
            "tProcessor program. Software mode runs one fixed X/Y point per "
            "host request; repetitions remain coherently accumulated in AVG."
        )
        self.hardware_rep_delay_us = QtWidgets.QDoubleSpinBox(acquisition)
        self.hardware_rep_delay_us.setRange(0.0, 1.0e9)
        self.hardware_rep_delay_us.setDecimals(6)
        self.hardware_rep_delay_us.setSuffix(" us")
        self.hardware_rep_delay_us.setValue(
            DEFAULT_STABILITY_HARDWARE_REP_DELAY_US
        )
        self.hardware_rep_delay_us.setToolTip(
            "Fixed tProcessor pacing guard after every hardware repetition. "
            "This is not a host-read handshake."
        )
        self._fir_sample_rate_hz: Optional[float] = None
        self._fir_trigger_delay_us = 0.0
        self._fir_uses_fpga_trigger_delay: Optional[bool] = None
        self.fir_profile_status = QtWidgets.QLabel(
            "Identify QICK to show the FIR DDR timing",
            acquisition,
        )
        self.fir_profile_status.setWordWrap(True)
        self.fir_profile_status.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self.settle_time_us = QtWidgets.QDoubleSpinBox(acquisition)
        self.settle_time_us.setRange(0.0, 1.0e9)
        self.settle_time_us.setDecimals(6)
        self.settle_time_us.setValue(DEFAULT_STABILITY_SETTLE_US)
        self.settle_time_us.setSuffix(" us")
        self.settle_time_us.setToolTip(
            "Time to hold each new X/Y voltage before readout begins. RF "
            "modulation starts one tProcessor clock after the AWG SET "
            "dispatch and remains active through this settle interval."
        )
        self.override_fpga_trigger_delay = QtWidgets.QCheckBox(
            "Override HWH default",
            acquisition,
        )
        self.fpga_trigger_delay_us = QtWidgets.QDoubleSpinBox(acquisition)
        self.fpga_trigger_delay_us.setRange(0.0, 10_000_000.0)
        self.fpga_trigger_delay_us.setDecimals(6)
        self.fpga_trigger_delay_us.setSuffix(" us")
        self.fpga_trigger_delay_us.setToolTip(
            "FPGA delay from trigger arrival to FIR-DDR storage"
        )
        fpga_delay_row = QtWidgets.QHBoxLayout()
        fpga_delay_row.setContentsMargins(0, 0, 0, 0)
        fpga_delay_row.addWidget(self.override_fpga_trigger_delay)
        fpga_delay_row.addWidget(self.fpga_trigger_delay_us, 1)
        self.modulation_frequency_mhz = QtWidgets.QDoubleSpinBox(acquisition)
        self.modulation_frequency_mhz.setRange(-10_000.0, 10_000.0)
        self.modulation_frequency_mhz.setDecimals(9)
        self.modulation_frequency_mhz.setValue(
            DEFAULT_STABILITY_MODULATION_FREQUENCY_MHZ
        )
        self.modulation_frequency_mhz.setSuffix(" MHz")
        self.modulation_frequency_mhz.setToolTip(
            "Shared DDS/DDC modulation frequency. The same value configures "
            "the selected RF or DC output and input; use 0 MHz for DC."
        )
        self.modulation_gain = QtWidgets.QSpinBox(acquisition)
        self.modulation_gain.setRange(0, 32767)
        self.modulation_gain.setValue(DEFAULT_STABILITY_MODULATION_GAIN)
        self.modulation_gain.setToolTip(
            "DAC gain code for the measurement modulation output"
        )
        self.point_count = QtWidgets.QLabel("2,601", acquisition)
        self.point_count.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.dc_measure_mode = QtWidgets.QCheckBox("DC measure mode", acquisition)
        self.dc_measure_mode.setToolTip(
            "DC_In only: convert FIR I/Q to current using voltage / gain"
        )
        self.measurement_unit = QtWidgets.QComboBox(acquisition)
        self.measurement_unit.addItem("ADC units", "adc")
        self.measurement_unit.addItem("Voltage", "voltage")
        self.measurement_unit.addItem("Current", "current")
        self.measurement_unit.setToolTip(
            "Choose the Stability Diagram map representation. Voltage and "
            "current require a DC_In path; current divides voltage by the "
            "measurement gain."
        )
        self.dc_measure_gain_v_per_a = QtWidgets.QDoubleSpinBox(acquisition)
        self.dc_measure_gain_v_per_a.setRange(1.0e-9, 1.0e15)
        self.dc_measure_gain_v_per_a.setDecimals(6)
        self.dc_measure_gain_v_per_a.setValue(1.0)
        self.dc_measure_gain_v_per_a.setSuffix(" V/A")
        acquisition_form.addRow("Source:", self.acquisition_source)
        acquisition_form.addRow("Sweep execution:", self.sweep_mode)
        acquisition_form.addRow("Repetitions / point:", self.repetitions)
        acquisition_form.addRow("Samples / integration:", self.trace_samples)
        acquisition_form.addRow(
            "Hardware repetition guard:",
            self.hardware_rep_delay_us,
        )
        acquisition_form.addRow("Settle before readout:", self.settle_time_us)
        acquisition_form.addRow(
            "FPGA trigger-to-store delay:",
            fpga_delay_row,
        )
        acquisition_form.addRow(
            "Modulation frequency:",
            self.modulation_frequency_mhz,
        )
        acquisition_form.addRow("Modulation gain:", self.modulation_gain)
        acquisition_form.addRow("Cartesian points:", self.point_count)
        acquisition_form.addRow("HWH FIR DDR:", self.fir_profile_status)
        acquisition_form.addRow("Display unit:", self.measurement_unit)
        acquisition_form.addRow(
            "DC measurement gain:",
            self.dc_measure_gain_v_per_a,
        )
        controls.addWidget(acquisition)

        self.modulation_power_calibration_group = QtWidgets.QGroupBox(
            "Use Calibrated Modulation Power",
            controls_content,
        )
        self.modulation_power_calibration_group.setCheckable(True)
        self.modulation_power_calibration_group.setChecked(False)
        self.modulation_power_calibration_group.setToolTip(
            "Convert the requested connector power in dBm to a DAC gain code "
            "using an RF_Out calibration matched to modulation frequency, "
            "Nyquist zone, output filter, and ATT1/ATT2."
        )
        modulation_calibration_form = QtWidgets.QFormLayout(
            self.modulation_power_calibration_group
        )
        self.modulation_target_power_dbm = QtWidgets.QDoubleSpinBox(
            self.modulation_power_calibration_group
        )
        self.modulation_target_power_dbm.setRange(-300.0, 100.0)
        self.modulation_target_power_dbm.setDecimals(6)
        self.modulation_target_power_dbm.setSuffix(" dBm")
        self.modulation_target_power_dbm.setValue(
            DEFAULT_STABILITY_TARGET_POWER_DBM
        )
        self.modulation_power_calibration_path = QtWidgets.QLineEdit(
            DEFAULT_STABILITY_POWER_CALIBRATION_DB_PATH,
            self.modulation_power_calibration_group,
        )
        self.modulation_power_calibration_path.setPlaceholderText(
            "QCoDeS DB containing RF_Out gain/power calibration"
        )
        self.modulation_power_calibration_browse = QtWidgets.QToolButton(
            self.modulation_power_calibration_group
        )
        self.modulation_power_calibration_browse.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton)
        )
        self.modulation_power_calibration_browse.setToolTip(
            "Choose the RF output-power calibration database"
        )
        modulation_calibration_path_row = QtWidgets.QHBoxLayout()
        modulation_calibration_path_row.setContentsMargins(0, 0, 0, 0)
        modulation_calibration_path_row.addWidget(
            self.modulation_power_calibration_path,
            1,
        )
        modulation_calibration_path_row.addWidget(
            self.modulation_power_calibration_browse
        )
        self.modulation_power_calibration_run_id = QtWidgets.QSpinBox(
            self.modulation_power_calibration_group
        )
        self.modulation_power_calibration_run_id.setRange(0, (1 << 31) - 1)
        self.modulation_power_calibration_run_id.setSpecialValueText(
            "Best compatible Run"
        )
        self.resolve_modulation_gain_button = QtWidgets.QPushButton(
            "Resolve Gain",
            self.modulation_power_calibration_group,
        )
        self.resolve_modulation_gain_button.setToolTip(
            "Find a compatible calibration and update Modulation gain"
        )
        self.modulation_power_calibration_status = QtWidgets.QLabel(
            "Enable calibrated power to resolve a gain code.",
            self.modulation_power_calibration_group,
        )
        self.modulation_power_calibration_status.setWordWrap(True)
        self.modulation_power_calibration_status.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        modulation_calibration_form.addRow(
            "Target connector power:",
            self.modulation_target_power_dbm,
        )
        modulation_calibration_form.addRow(
            "Calibration DB:",
            modulation_calibration_path_row,
        )
        modulation_calibration_form.addRow(
            "Calibration Run ID:",
            self.modulation_power_calibration_run_id,
        )
        modulation_calibration_form.addRow(
            self.resolve_modulation_gain_button
        )
        modulation_calibration_form.addRow(
            "Resolved gain:",
            self.modulation_power_calibration_status,
        )
        controls.addWidget(self.modulation_power_calibration_group)

        self.bias_t_group = CompensationGroup(
            "Bias-T compensation",
            controls_content,
        )
        self.bias_t_group.setCheckable(True)
        self.bias_t_group.setChecked(False)
        self.bias_t_group.setToolTip(
            "Apply Stability Diagram-specific compensation to every hardware "
            "sweep shot"
        )
        bias_t_form = QtWidgets.QFormLayout(self.bias_t_group)
        self.bias_t_type = CompensationSelector(self.bias_t_group)
        self.bias_t_type.addItem("DC compensation", "dc")
        self.bias_t_type.addItem("RC compensation", "filter")
        self.bias_t_mode = QtWidgets.QComboBox(self.bias_t_group)
        self.bias_t_mode.addItem("Fixed voltage (adjust time)", "fixed_voltage")
        self.bias_t_mode.addItem("Fixed time (adjust voltage)", "fixed_time")
        self.bias_t_compensation_mv = QtWidgets.QDoubleSpinBox(self.bias_t_group)
        self.bias_t_compensation_mv.setRange(0.001, 1.0e6)
        self.bias_t_compensation_mv.setDecimals(6)
        self.bias_t_compensation_mv.setSuffix(" mV")
        self.bias_t_compensation_mv.setValue(
            DEFAULT_STABILITY_BIAS_T_COMPENSATION_MV
        )
        self.bias_t_duration_us = QtWidgets.QDoubleSpinBox(self.bias_t_group)
        self.bias_t_duration_us.setRange(1.0e-6, 1.0e9)
        self.bias_t_duration_us.setDecimals(6)
        self.bias_t_duration_us.setSuffix(" us")
        self.bias_t_duration_us.setValue(DEFAULT_BIAS_T_COMPENSATION_DURATION_US)
        self.bias_t_filter_tau_us = QtWidgets.QDoubleSpinBox(self.bias_t_group)
        self.bias_t_filter_tau_us.setRange(10.0, 1_000_000.0)
        self.bias_t_filter_tau_us.setDecimals(6)
        self.bias_t_filter_tau_us.setSuffix(" us")
        self.bias_t_filter_tau_us.setValue(DEFAULT_BIAS_T_FILTER_TAU_US)
        bias_t_form.addRow(self.bias_t_type)
        bias_t_form.addRow("DC control mode:", self.bias_t_mode)
        bias_t_form.addRow("DC voltage:", self.bias_t_compensation_mv)
        bias_t_form.addRow("DC time:", self.bias_t_duration_us)
        bias_t_form.addRow("RC time constant (tau):", self.bias_t_filter_tau_us)
        controls.addWidget(self.bias_t_group)

        self.dc_calibration_group = QtWidgets.QGroupBox(
            "Apply DC Input Voltage Calibration",
            controls_content,
        )
        self.dc_calibration_group.setCheckable(True)
        self.dc_calibration_group.setChecked(False)
        calibration_form = QtWidgets.QFormLayout(self.dc_calibration_group)
        self.dc_calibration_path = QtWidgets.QLineEdit(
            self.dc_calibration_group
        )
        self.dc_calibration_path.setPlaceholderText(
            "QCoDeS DB containing a DC Voltage calibration run"
        )
        self.dc_calibration_browse = QtWidgets.QToolButton(
            self.dc_calibration_group
        )
        self.dc_calibration_browse.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton)
        )
        self.dc_calibration_browse.setToolTip(
            "Choose the DC voltage calibration database"
        )
        calibration_path_row = QtWidgets.QHBoxLayout()
        calibration_path_row.addWidget(self.dc_calibration_path, 1)
        calibration_path_row.addWidget(self.dc_calibration_browse)
        self.dc_calibration_run_id = QtWidgets.QSpinBox(
            self.dc_calibration_group
        )
        self.dc_calibration_run_id.setRange(0, (1 << 31) - 1)
        self.dc_calibration_run_id.setSpecialValueText(
            "Latest matching channel/gain"
        )
        calibration_form.addRow("Calibration DB:", calibration_path_row)
        calibration_form.addRow("Run ID:", self.dc_calibration_run_id)
        controls.addWidget(self.dc_calibration_group)

        database_group = QtWidgets.QGroupBox(
            "Single Shot Save Database",
            controls_content,
        )
        database_form = QtWidgets.QFormLayout(database_group)
        self.database_path = QtWidgets.QLineEdit(
            DEFAULT_STABILITY_DB_PATH,
            database_group,
        )
        self.browse_database = QtWidgets.QToolButton(database_group)
        self.browse_database.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton)
        )
        self.browse_database.setToolTip("Choose the stability-diagram QCoDeS DB")
        self.browse_database.clicked.connect(self._browse_database)
        database_row = QtWidgets.QHBoxLayout()
        database_row.addWidget(self.database_path, 1)
        database_row.addWidget(self.browse_database)
        database_form.addRow("QCoDeS DB file:", database_row)
        self.iq_storage_mode = QtWidgets.QComboBox(database_group)
        self.iq_storage_mode.addItem(
            "Full traces for every repetition",
            IQ_STORAGE_FULL_TRACES,
        )
        self.iq_storage_mode.addItem(
            "Mean I/Q only for each sweep point",
            IQ_STORAGE_MEAN_IQ,
        )
        self.iq_storage_mode.setCurrentIndex(
            self.iq_storage_mode.findData(DEFAULT_IQ_STORAGE_MODE)
        )
        self.iq_storage_mode.setToolTip(
            "This applies only to Single Shot & Save. Mean mode stores one "
            "I/Q pair per X/Y point after averaging every repetition and FIR "
            "sample; continuous scans are unchanged."
        )
        database_form.addRow("QCoDeS I/Q storage:", self.iq_storage_mode)
        controls.addWidget(database_group)

        saved_plot_group = QtWidgets.QGroupBox(
            "Plot Saved Stability Diagram",
            controls_content,
        )
        saved_plot_form = QtWidgets.QFormLayout(saved_plot_group)
        self.saved_database_path = QtWidgets.QLineEdit(
            DEFAULT_STABILITY_DB_PATH,
            saved_plot_group,
        )
        self.saved_database_path.setPlaceholderText(
            "QCoDeS DB containing saved Stability Diagram runs"
        )
        self.browse_saved_database = QtWidgets.QToolButton(saved_plot_group)
        self.browse_saved_database.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton)
        )
        self.browse_saved_database.setToolTip(
            "Choose a database to inspect without changing the save DB"
        )
        self.browse_saved_database.clicked.connect(
            self._browse_saved_database
        )
        saved_database_row = QtWidgets.QHBoxLayout()
        saved_database_row.addWidget(self.saved_database_path, 1)
        saved_database_row.addWidget(self.browse_saved_database)
        saved_plot_form.addRow("Source DB:", saved_database_row)

        self.saved_run_combo = QtWidgets.QComboBox(saved_plot_group)
        self.saved_run_combo.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        self.saved_run_combo.setMinimumContentsLength(28)
        self.refresh_saved_runs_button = QtWidgets.QPushButton(
            "Refresh Runs",
            saved_plot_group,
        )
        self.refresh_saved_runs_button.clicked.connect(
            self.refresh_saved_runs
        )
        saved_run_row = QtWidgets.QHBoxLayout()
        saved_run_row.addWidget(self.saved_run_combo, 1)
        saved_run_row.addWidget(self.refresh_saved_runs_button)
        saved_plot_form.addRow("Run:", saved_run_row)
        self.saved_plot_data = QtWidgets.QComboBox(saved_plot_group)
        for label, key in (
            ("I", "i"),
            ("Q", "q"),
            ("Magnitude", "magnitude"),
            ("Angle", "phase"),
        ):
            self.saved_plot_data.addItem(label, key)
        self.saved_plot_data.setCurrentIndex(
            self.saved_plot_data.findData("magnitude")
        )
        self.saved_plot_data.setToolTip(
            "Select the map shown after loading. Additional maps can be "
            "enabled with the checkboxes above the Stability Diagram plot."
        )
        saved_plot_form.addRow("Plot data:", self.saved_plot_data)
        self.load_saved_run_button = QtWidgets.QPushButton(
            "Load Saved Diagram",
            saved_plot_group,
        )
        self.load_saved_run_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton)
        )
        self.load_saved_run_button.clicked.connect(
            self._request_saved_run
        )
        saved_plot_form.addRow(self.load_saved_run_button)
        self.saved_run_status = QtWidgets.QLabel(
            "Choose a DB and refresh its Stability Diagram runs.",
            saved_plot_group,
        )
        self.saved_run_status.setWordWrap(True)
        self.saved_run_status.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        saved_plot_form.addRow(self.saved_run_status)
        controls.addWidget(saved_plot_group)

        self.start_button = QtWidgets.QPushButton("Start", controls_content)
        self.start_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay)
        )
        self.start_button.setToolTip(
            "Continuously repeat full hardware scans without writing QCoDeS"
        )
        self.stop_button = QtWidgets.QPushButton("Stop", controls_content)
        self.stop_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_MediaStop)
        )
        self.stop_button.setToolTip(
            "Stop after the currently active full hardware scan completes"
        )
        self.stop_button.setEnabled(False)
        self.single_shot_button = QtWidgets.QPushButton(
            "Single Shot && Save",
            controls_content,
        )
        self.single_shot_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton)
        )
        self.single_shot_button.setToolTip(
            "Acquire one full stability diagram and save its FIR I/Q traces "
            "to the database selected above"
        )
        self.fit_button = QtWidgets.QPushButton("Fit", controls_content)
        self.fit_button.setText("Fit")
        self.fit_button.setToolTip("Fit both stability plots to the full sweep")
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.single_shot_button)
        controls.addWidget(self.fit_button)

        self.progress = QtWidgets.QProgressBar(controls_content)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.hide()
        controls.addWidget(self.progress)
        self.status = QtWidgets.QLabel("Ready", controls_content)
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        controls.addWidget(self.status)
        controls.addStretch(1)
        self.controls_scroll.setWidget(controls_content)
        outer.addWidget(self.controls_scroll, 1)

        self.plot = StabilityDiagramPlotWidget(self)
        outer.addWidget(self.plot, 1)

        self.start_button.clicked.connect(self.start_requested.emit)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.single_shot_button.clicked.connect(self.single_shot_requested.emit)
        self.fit_button.clicked.connect(self.plot.fit_view)
        self.x_axis.points.valueChanged.connect(self._update_point_count)
        self.y_axis.points.valueChanged.connect(self._update_point_count)
        self.trace_samples.valueChanged.connect(self._update_fir_trace_duration)
        self.acquisition_source.currentIndexChanged.connect(
            self._update_acquisition_controls
        )
        self.sweep_mode.currentIndexChanged.connect(
            self._update_acquisition_controls
        )
        self.override_fpga_trigger_delay.toggled.connect(
            self._update_fpga_trigger_delay_controls
        )
        self.fpga_trigger_delay_us.valueChanged.connect(
            self._update_fir_trace_duration
        )
        self.modulation_power_calibration_group.toggled.connect(
            self._modulation_power_calibration_changed
        )
        self.modulation_frequency_mhz.valueChanged.connect(
            self._invalidate_modulation_power_calibration
        )
        self._update_acquisition_controls()
        self.modulation_target_power_dbm.valueChanged.connect(
            self._invalidate_modulation_power_calibration
        )
        self.modulation_power_calibration_path.editingFinished.connect(
            self._invalidate_modulation_power_calibration
        )
        self.modulation_power_calibration_run_id.valueChanged.connect(
            self._invalidate_modulation_power_calibration
        )
        self.modulation_power_calibration_browse.clicked.connect(
            self._browse_modulation_power_calibration
        )
        self.resolve_modulation_gain_button.clicked.connect(
            self.resolve_modulation_gain
        )
        self.measurement_unit.currentIndexChanged.connect(
            self._measurement_representation_changed
        )
        self.dc_measure_mode.toggled.connect(
            self._legacy_dc_measure_mode_changed
        )
        self.dc_measure_gain_v_per_a.valueChanged.connect(
            self._emit_dc_measure_changed
        )
        self.dc_calibration_group.toggled.connect(
            self._emit_dc_calibration_changed
        )
        self.dc_calibration_path.editingFinished.connect(
            self._emit_dc_calibration_changed
        )
        self.dc_calibration_run_id.valueChanged.connect(
            self._emit_dc_calibration_changed
        )
        self.dc_calibration_browse.clicked.connect(
            self._browse_dc_calibration
        )
        self.bias_t_group.toggled.connect(self._update_bias_t_controls)
        self.bias_t_type.currentIndexChanged.connect(
            self._update_bias_t_controls
        )
        self.bias_t_mode.currentIndexChanged.connect(
            self._update_bias_t_controls
        )
        self._targets_available = False
        self._dc_input_available = False
        self._saved_run_loading = False
        self._preferred_saved_run_id = 0
        self._resolved_modulation_power_signature = None
        self._resolved_modulation_power_run_id = None
        self._update_point_count()
        self._update_modulation_power_calibration_controls()
        self._update_dc_measure_controls()
        self._update_bias_t_controls()

    def _modulation_power_calibration_changed(self, *_args) -> None:
        self._resolved_modulation_power_signature = None
        self._resolved_modulation_power_run_id = None
        self._update_modulation_power_calibration_controls()
        if self.modulation_power_calibration_group.isChecked():
            self.modulation_power_calibration_status.setText(
                "Not resolved. Click Resolve Gain or start a scan."
            )
            self.modulation_power_calibration_status.setStyleSheet(
                "color: #9a6700;"
            )
        else:
            self.modulation_power_calibration_status.setText(
                "Manual modulation gain code is active."
            )
            self.modulation_power_calibration_status.setStyleSheet("")

    def _update_modulation_power_calibration_controls(self) -> None:
        path = self.front_panel_values()
        rf_output = str(path.get("output_board_type", "")) == "RF_Out"
        editable = not self._running
        enabled = (
            editable
            and rf_output
            and self.modulation_power_calibration_group.isChecked()
        )
        self.modulation_power_calibration_group.setEnabled(
            editable and rf_output
        )
        self.modulation_gain.setEnabled(
            editable
            and not self.modulation_power_calibration_group.isChecked()
        )
        for widget in (
            self.modulation_target_power_dbm,
            self.modulation_power_calibration_path,
            self.modulation_power_calibration_browse,
            self.modulation_power_calibration_run_id,
            self.resolve_modulation_gain_button,
        ):
            widget.setEnabled(enabled)
        if not rf_output:
            self.modulation_power_calibration_group.setToolTip(
                "Calibrated dBm output requires an RF_Out board."
            )
        else:
            self.modulation_power_calibration_group.setToolTip(
                "Convert target connector power to DAC gain using a matching "
                "RF_Out calibration, including ATT1/ATT2, filter, and Nyquist."
            )

    def _modulation_power_signature(self) -> tuple:
        path = self.front_panel_values()
        return (
            str(Path(
                self.modulation_power_calibration_path.text().strip()
            ).expanduser()),
            int(self.modulation_power_calibration_run_id.value()),
            float(self.modulation_frequency_mhz.value()),
            float(self.modulation_target_power_dbm.value()),
            int(path["output_ch"]),
            str(path["output_board_type"]),
            int(path["output_nqz"]),
            float(path["output_att1_db"]),
            float(path["output_att2_db"]),
            str(path["output_filter_type"]),
            float(path["output_filter_cutoff_ghz"]),
            float(path["output_filter_bandwidth_ghz"]),
        )

    def _invalidate_modulation_power_calibration(self, *_args) -> None:
        if not hasattr(self, "_resolved_modulation_power_signature"):
            return
        self._resolved_modulation_power_signature = None
        self._resolved_modulation_power_run_id = None
        if self.modulation_power_calibration_group.isChecked():
            self.modulation_power_calibration_status.setText(
                "Settings changed; resolve the gain again."
            )
            self.modulation_power_calibration_status.setStyleSheet(
                "color: #9a6700;"
            )

    def _browse_modulation_power_calibration(self) -> None:
        path, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Choose RF output-power calibration database",
            self.modulation_power_calibration_path.text().strip(),
            "QCoDeS SQLite database (*.db)",
        )
        if path:
            self.modulation_power_calibration_path.setText(path)
            self._invalidate_modulation_power_calibration()

    def resolve_modulation_gain(
        self,
        *_args,
        raise_on_error: bool = False,
    ) -> int:
        """Resolve target connector dBm to a gain code for this RF path."""
        if not self.modulation_power_calibration_group.isChecked():
            return int(self.modulation_gain.value())
        try:
            path = self.front_panel_values()
            if str(path["output_board_type"]) != "RF_Out":
                raise ValueError(
                    "calibrated modulation power requires an RF_Out board"
                )
            database_path = (
                self.modulation_power_calibration_path.text().strip()
            )
            if not database_path:
                raise ValueError(
                    "modulation power calibration database path is required"
                )
            frequency_mhz = float(self.modulation_frequency_mhz.value())
            target_power_dbm = float(
                self.modulation_target_power_dbm.value()
            )
            requested_run_id = int(
                self.modulation_power_calibration_run_id.value()
            )
            calibration = CalibrationDatabase(
                database_path
            ).output_calibration(
                "RF_Out",
                [frequency_mhz],
                run_id=(None if requested_run_id == 0 else requested_run_id),
                nqz=int(path["output_nqz"]),
                output_filter_type=str(path["output_filter_type"]),
                output_filter_cutoff_ghz=float(
                    path["output_filter_cutoff_ghz"]
                ),
                output_filter_bandwidth_ghz=float(
                    path["output_filter_bandwidth_ghz"]
                ),
            )
            schedule = calibration.build_gain_schedule(
                [frequency_mhz],
                target_power_dbm,
                output_att1_db=float(path["output_att1_db"]),
                output_att2_db=float(path["output_att2_db"]),
                max_entries=1,
            )
            gain = int(np.asarray(schedule.gain_codes).reshape(-1)[0])
            if gain < 0 or gain > 32767:
                raise ValueError(
                    f"calibrated modulation gain {gain} is outside 0..32767"
                )
            predicted_power_dbm = float(
                calibration.output_power_dbm(
                    [frequency_mhz],
                    [gain],
                    output_att1_db=float(path["output_att1_db"]),
                    output_att2_db=float(path["output_att2_db"]),
                )[0]
            )
            with QtCore.QSignalBlocker(self.modulation_gain):
                self.modulation_gain.setValue(gain)
            self._resolved_modulation_power_signature = (
                self._modulation_power_signature()
            )
            self._resolved_modulation_power_run_id = int(
                calibration.summary.run_id
            )
            self.modulation_power_calibration_status.setText(
                f"Run {calibration.summary.run_id}: {target_power_dbm:g} dBm "
                f"-> gain {gain}; predicted {predicted_power_dbm:.6g} dBm at "
                f"{frequency_mhz:g} MHz."
            )
            self.modulation_power_calibration_status.setStyleSheet(
                "color: #1a7f37;"
            )
            return gain
        except (
            FileNotFoundError,
            LookupError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            self._resolved_modulation_power_signature = None
            self._resolved_modulation_power_run_id = None
            self.modulation_power_calibration_status.setText(str(exc))
            self.modulation_power_calibration_status.setStyleSheet(
                "color: #cf222e;"
            )
            if raise_on_error:
                raise ValueError(str(exc)) from exc
            return int(self.modulation_gain.value())

    def _update_dc_measure_controls(self) -> None:
        editable = self._dc_input_available and not self._running
        self.measurement_unit.setEnabled(editable)
        self.dc_measure_mode.setEnabled(editable)
        self.dc_measure_gain_v_per_a.setEnabled(
            editable and self.measurement_unit.currentData() == "current"
        )
        self.dc_calibration_group.setEnabled(editable)

    def _update_bias_t_controls(self, *_args) -> None:
        editable = not self._running and self.bias_t_group.isChecked()
        filter_mode = self.bias_t_type.currentData() == "filter"
        fixed_time = self.bias_t_mode.currentData() == "fixed_time"
        self.bias_t_type.setEnabled(not self._running)
        self.bias_t_mode.setEnabled(editable and not filter_mode)
        self.bias_t_compensation_mv.setEnabled(
            editable and not filter_mode and not fixed_time
        )
        self.bias_t_duration_us.setEnabled(
            editable and not filter_mode and fixed_time
        )
        self.bias_t_filter_tau_us.setEnabled(editable and self.bias_t_type.currentData() in ("filter", "dc_rc"))

    def _emit_dc_measure_changed(self, *_args) -> None:
        self._update_dc_measure_controls()
        self.dc_measure_changed.emit(
            self.measurement_unit.currentData() == "current",
            self.dc_measure_gain_v_per_a.value(),
        )

    def _emit_dc_calibration_changed(self, *_args) -> None:
        if (
            self.dc_calibration_group.isChecked()
            and self._dc_input_available
            and self.measurement_unit.currentData() == "adc"
        ):
            with QtCore.QSignalBlocker(self.measurement_unit):
                self.measurement_unit.setCurrentIndex(
                    self.measurement_unit.findData("voltage")
                )
            with QtCore.QSignalBlocker(self.dc_measure_mode):
                self.dc_measure_mode.setChecked(False)
        self._update_dc_measure_controls()
        self.dc_calibration_changed.emit(
            self.dc_calibration_group.isChecked(),
            self.dc_calibration_path.text().strip(),
            self.dc_calibration_run_id.value(),
        )

    def _measurement_representation_changed(self, *_args) -> None:
        representation = str(self.measurement_unit.currentData())
        with QtCore.QSignalBlocker(self.dc_measure_mode):
            self.dc_measure_mode.setChecked(representation == "current")
        self._emit_dc_measure_changed()

    def _legacy_dc_measure_mode_changed(self, checked: bool) -> None:
        representation = (
            "current"
            if checked
            else (
                "voltage"
                if self.dc_calibration_group.isChecked()
                else "adc"
            )
        )
        with QtCore.QSignalBlocker(self.measurement_unit):
            self.measurement_unit.setCurrentIndex(
                self.measurement_unit.findData(representation)
            )
        self._emit_dc_measure_changed()

    def _browse_dc_calibration(self) -> None:
        path, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Choose DC voltage calibration database",
            self.dc_calibration_path.text().strip(),
            "QCoDeS SQLite database (*.db)",
        )
        if path:
            self.dc_calibration_path.setText(path)
            self._emit_dc_calibration_changed()

    def set_dc_measure_context(
        self,
        input_board_type: str,
        enabled: bool,
        gain_v_per_a: float,
        calibration_enabled: bool = False,
        calibration_database_path: str = "",
        calibration_run_id: int = 0,
    ) -> None:
        """Mirror this Stability tab's FIR readout settings."""
        self._dc_input_available = str(input_board_type) == "DC_In"
        with QtCore.QSignalBlocker(self.dc_measure_mode):
            self.dc_measure_mode.setChecked(
                bool(enabled) if self._dc_input_available else False
            )
        representation = (
            "current"
            if self._dc_input_available and enabled
            else (
                "voltage"
                if self._dc_input_available and calibration_enabled
                else "adc"
            )
        )
        with QtCore.QSignalBlocker(self.measurement_unit):
            self.measurement_unit.setCurrentIndex(
                self.measurement_unit.findData(representation)
            )
        with QtCore.QSignalBlocker(self.dc_measure_gain_v_per_a):
            self.dc_measure_gain_v_per_a.setValue(float(gain_v_per_a))
        with QtCore.QSignalBlocker(self.dc_calibration_group):
            self.dc_calibration_group.setChecked(
                bool(calibration_enabled) if self._dc_input_available else False
            )
        with QtCore.QSignalBlocker(self.dc_calibration_path):
            self.dc_calibration_path.setText(str(calibration_database_path))
        with QtCore.QSignalBlocker(self.dc_calibration_run_id):
            self.dc_calibration_run_id.setValue(int(calibration_run_id))
        self._update_dc_measure_controls()

    def refresh_targets(
        self,
        output_names: Sequence[str],
        awg_channels: Sequence[int],
        segment_names: Sequence[str] = (),
    ) -> None:
        # ``segment_names`` remains accepted for compatibility with older GUI
        # callers. Stability scans always use their own internal SET segment.
        self._awg_targets = (tuple(output_names), tuple(awg_channels))
        excluded = square_pulse_output_channels(self._front_panel_configuration)
        available = set(getattr(self._front_panel_configuration, "awg_tuning_channels", ()))
        for port in getattr(self._front_panel_configuration, "outputs", ()):
            available.update(channel for channel, path in zip(port.qick_channels, port.block_paths)
                             if "axis_awg_tuning" in path.lower())
        outputs = [(name, channel) for name, channel in zip(*self._awg_targets)
                   if channel not in excluded and (not available or channel in available)]
        if self._front_panel_configuration is None:
            # Preserve independently selected DACs when loading a saved setup offline.
            available.update(axis.current_gen_ch() for axis in (self.x_axis, self.y_axis)
                             if axis.current_gen_ch() >= 0)
        assigned = set(channel for _, channel in outputs)
        outputs.extend((f"gen_{channel}", channel)
                       for channel in sorted(available - assigned - excluded))
        self.x_axis.refresh_targets(outputs, preferred_output_index=0)
        self.y_axis.refresh_targets(outputs, preferred_output_index=1)
        if (
            len(outputs) >= 2
            and self.x_axis.output.currentData() == self.y_axis.output.currentData()
        ):
            for index in range(self.y_axis.output.count()):
                if (
                    self.y_axis.output.itemData(index)
                    != self.x_axis.output.currentData()
                ):
                    self.y_axis.output.setCurrentIndex(index)
                    break
        self._targets_available = len(outputs) >= 2
        if not self._targets_available:
            self.status.setText("Identify QICK to select two AWG DACs for a stability scan")
        self._set_idle_button_state()

    def run_output_mapping(self):
        """Retain the virtual-gate matrix and add only independently selected DACs."""
        allowed = {self.x_axis.output.itemData(index, QtCore.Qt.UserRole + 1)
                   for index in range(self.x_axis.output.count())}
        outputs = {name: channel for name, channel in zip(*self._awg_targets)
                   if channel in allowed}
        for axis in (self.x_axis, self.y_axis):
            name, channel = axis.output.currentData(), axis.current_gen_ch()
            if not name or channel < 0:
                raise ValueError("select both stability electrodes")
            outputs[str(name)] = channel
        if self.x_axis.current_gen_ch() == self.y_axis.current_gen_ch():
            raise ValueError("X and Y stability axes must use different DACs")
        validate_awg_output_channels(self._front_panel_configuration, outputs.values())
        if len(set(outputs.values())) != len(outputs):
            raise ValueError("stability electrodes contain duplicate DAC assignments")
        return tuple(outputs), tuple(outputs.values())

    def _browse_database(self) -> None:
        path, _selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Choose stability-diagram database",
            self.database_path.text().strip() or DEFAULT_STABILITY_DB_PATH,
            "QCoDeS SQLite database (*.db)",
        )
        if path:
            selected = Path(path)
            if selected.suffix.lower() != ".db":
                selected = selected.with_suffix(".db")
            self.database_path.setText(str(selected))

    def _browse_saved_database(self) -> None:
        path, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Choose saved Stability Diagram database",
            self.saved_database_path.text().strip()
            or self.database_path.text().strip()
            or DEFAULT_STABILITY_DB_PATH,
            "QCoDeS SQLite database (*.db);;All files (*)",
        )
        if path:
            self.saved_database_path.setText(path)
            self.refresh_saved_runs()

    def database_path_value(self) -> str:
        value = self.database_path.text().strip()
        if not value:
            raise ValueError("stability database path must not be empty")
        path = Path(value).expanduser()
        if path.suffix.lower() != ".db":
            path = path.with_suffix(".db")
        return str(path)

    def iq_storage_mode_value(self) -> str:
        return normalize_iq_storage_mode(self.iq_storage_mode.currentData())

    def saved_database_path_value(self) -> str:
        value = self.saved_database_path.text().strip()
        if not value:
            raise ValueError(
                "saved Stability Diagram database path must not be empty"
            )
        return str(Path(value).expanduser())

    def refresh_saved_runs(self) -> None:
        previous_run_id = (
            self.saved_run_combo.currentData()
            if self.saved_run_combo.currentData() is not None
            else self._preferred_saved_run_id
        )
        try:
            summaries = list_stability_runs(
                self.saved_database_path_value()
            )
        except Exception as exc:
            self.saved_run_combo.clear()
            self.saved_run_status.setText(str(exc))
            return
        self.saved_run_combo.clear()
        for summary in summaries:
            self.saved_run_combo.addItem(
                summary.display_label,
                summary.run_id,
            )
        if previous_run_id is not None:
            previous_index = self.saved_run_combo.findData(previous_run_id)
            if previous_index >= 0:
                self.saved_run_combo.setCurrentIndex(previous_index)
        self._preferred_saved_run_id = int(
            self.saved_run_combo.currentData() or 0
        )
        if summaries:
            self.saved_run_status.setText(
                f"Found {len(summaries)} saved Stability Diagram run(s)."
            )
        else:
            self.saved_run_status.setText(
                "This database contains no saved Stability Diagram runs."
            )

    def _request_saved_run(self) -> None:
        run_id = self.saved_run_combo.currentData()
        if run_id is None:
            self.saved_run_status.setText(
                "Refresh the DB and select a saved Stability Diagram first."
            )
            return
        plot_data = str(self.saved_plot_data.currentData())
        self.plot.load_visible_data((plot_data,))
        self._preferred_saved_run_id = int(run_id)
        self.saved_run_requested.emit(
            self.saved_database_path_value(),
            int(run_id),
        )

    def set_saved_run_loading(self, loading: bool, *, run_id: int = 0) -> None:
        self._saved_run_loading = bool(loading)
        idle_enabled = (
            not self._saved_run_loading
            and not self._running
            and self._targets_available
        )
        self.start_button.setEnabled(idle_enabled)
        self.single_shot_button.setEnabled(idle_enabled)
        for widget in (
            self.saved_database_path,
            self.browse_saved_database,
            self.saved_run_combo,
            self.saved_plot_data,
            self.refresh_saved_runs_button,
            self.load_saved_run_button,
        ):
            widget.setEnabled(not loading and not self._running)
        if loading:
            self.saved_run_status.setText(
                f"Loading QCoDeS Run {int(run_id)}..."
            )

    def set_front_panel_configuration(self, configuration) -> None:
        self._front_panel_configuration = configuration
        self.path_diagram.set_front_panel_configuration(configuration)
        self.x_axis.set_front_panel_configuration(configuration)
        self.y_axis.set_front_panel_configuration(configuration)
        self.refresh_targets(*self._awg_targets)
        self._fir_sample_rate_hz = getattr(
            configuration,
            "fir_sample_rate_hz",
            None,
        )
        self._fir_trigger_delay_us = float(
            getattr(configuration, "fir_trigger_delay_us", 0.0)
        )
        self._fir_uses_fpga_trigger_delay = (
            str(
                getattr(
                    configuration,
                    "fir_trigger_delay_units",
                    "none",
                )
            )
            != "none"
        )
        if not self.override_fpga_trigger_delay.isChecked():
            with QtCore.QSignalBlocker(self.fpga_trigger_delay_us):
                self.fpga_trigger_delay_us.setValue(
                    self._fir_trigger_delay_us
                )
        self._update_fpga_trigger_delay_controls()
        self._update_fir_trace_duration()

    def _update_fpga_trigger_delay_controls(self, *_args) -> None:
        supported = (
            self.acquisition_source.currentData() == "fir_ddr"
            and self._fir_uses_fpga_trigger_delay is not False
        )
        self.override_fpga_trigger_delay.setEnabled(supported)
        self.fpga_trigger_delay_us.setEnabled(
            supported and self.override_fpga_trigger_delay.isChecked()
        )
        self._update_fir_trace_duration()

    def _update_acquisition_controls(self, *_args) -> None:
        uses_fir = self.acquisition_source.currentData() == "fir_ddr"
        hardware = self.sweep_mode.currentData() == "hardware"
        self.hardware_rep_delay_us.setEnabled(
            not self._running and hardware
        )
        self.override_fpga_trigger_delay.setVisible(uses_fir)
        self.fpga_trigger_delay_us.setVisible(uses_fir)
        self._update_fpga_trigger_delay_controls()

    def _update_fir_trace_duration(self, *_args) -> None:
        if self.acquisition_source.currentData() == "avg_buffer":
            self.fir_profile_status.setText(
                "AVG integration rate is read from the selected readout in "
                "the active HWH when the scan starts."
            )
            return
        if self._fir_sample_rate_hz is None:
            self.fir_profile_status.setText(
                "Identify QICK to show the FIR DDR timing"
            )
            return
        sample_period_us = 1_000_000.0 / self._fir_sample_rate_hz
        trace_us = self.trace_samples.value() * sample_period_us
        if self._fir_uses_fpga_trigger_delay:
            if self.override_fpga_trigger_delay.isChecked():
                delay = (
                    f"; FPGA delay override "
                    f"{self.fpga_trigger_delay_us.value():g} us"
                )
            else:
                delay = f"; HWH FPGA delay {self._fir_trigger_delay_us:g} us"
        else:
            delay = "; no FPGA trigger-delay register"
        self.fir_profile_status.setText(
            f"{format_sample_rate_hz(self._fir_sample_rate_hz)}, "
            f"{self.trace_samples.value():,} samples = {trace_us:g} us"
            f"{delay}"
        )

    def front_panel_values(self) -> Mapping[str, Any]:
        """Return the complete Stability-only measurement path."""
        values = self.path_diagram._editor_values()
        values.update(self._path_aux)
        return values

    def apply_front_panel_settings(self, values: Mapping[str, Any]) -> None:
        """Apply graphical SMA settings only to this Stability tab."""
        self.apply_path_settings(values)

    def apply_path_settings(self, values: Mapping[str, Any]) -> None:
        complete = self.front_panel_values()
        complete.update(values)
        for key in tuple(self._path_aux):
            if key in complete:
                self._path_aux[key] = complete[key]
        self.path_diagram.apply_external_settings(complete)
        if (
            str(complete["output_board_type"]) != "RF_Out"
            and self.modulation_power_calibration_group.isChecked()
        ):
            with QtCore.QSignalBlocker(
                self.modulation_power_calibration_group
            ):
                self.modulation_power_calibration_group.setChecked(False)
        self._invalidate_modulation_power_calibration()
        self._update_modulation_power_calibration_controls()
        self._dc_input_available = str(complete["input_board_type"]) == "DC_In"
        if not self._dc_input_available:
            with QtCore.QSignalBlocker(self.dc_measure_mode):
                self.dc_measure_mode.setChecked(False)
            with QtCore.QSignalBlocker(self.measurement_unit):
                self.measurement_unit.setCurrentIndex(
                    self.measurement_unit.findData("adc")
                )
            with QtCore.QSignalBlocker(self.dc_calibration_group):
                self.dc_calibration_group.setChecked(False)
        self._update_dc_measure_controls()

    def _apply_local_path_settings(self, values: Mapping[str, Any]) -> None:
        self.apply_path_settings(values)
        self.path_settings_applied.emit(dict(self.front_panel_values()))

    def config(self, *, full_scale_mv: float) -> StabilityDiagramConfig:
        if not self._targets_available:
            raise ValueError("stability diagram requires at least two AWG outputs")
        config = StabilityDiagramConfig(
            x_axis=self.x_axis.value(),
            y_axis=self.y_axis.value(),
            repetitions_per_point=self.repetitions.value(),
            trace_samples_per_point=self.trace_samples.value(),
            settle_time_us=self.settle_time_us.value(),
            acquisition_source=str(self.acquisition_source.currentData()),
            sweep_mode=str(self.sweep_mode.currentData()),
            hardware_rep_delay_us=self.hardware_rep_delay_us.value(),
            fpga_trigger_delay_us=(
                self.fpga_trigger_delay_us.value()
                if (
                    self.override_fpga_trigger_delay.isChecked()
                    and self._fir_uses_fpga_trigger_delay is not False
                )
                else None
            ),
            modulation_frequency_mhz=self.modulation_frequency_mhz.value(),
            modulation_gain=self.modulation_gain.value(),
            modulation_power_calibration_enabled=(
                self.modulation_power_calibration_group.isChecked()
            ),
            modulation_power_calibration_database_path=(
                self.modulation_power_calibration_path.text().strip()
            ),
            modulation_power_calibration_run_id=(
                self.modulation_power_calibration_run_id.value()
            ),
            modulation_target_power_dbm=(
                self.modulation_target_power_dbm.value()
            ),
            bias_t_compensation_enabled=self.bias_t_group.isChecked(),
            bias_t_compensation_type=str(self.bias_t_type.currentData()),
            bias_t_compensation_voltage_mv=self.bias_t_compensation_mv.value(),
            bias_t_compensation_mode=str(self.bias_t_mode.currentData()),
            bias_t_compensation_duration_us=self.bias_t_duration_us.value(),
            bias_t_filter_tau_us=self.bias_t_filter_tau_us.value(),
        )
        config.validate_full_scale(full_scale_mv)
        return config

    def settings_dict(self) -> dict:
        return {
            "x_axis": self.x_axis.settings_dict(),
            "y_axis": self.y_axis.settings_dict(),
            "repetitions_per_point": self.repetitions.value(),
            "trace_samples_per_point": self.trace_samples.value(),
            "settle_time_us": self.settle_time_us.value(),
            "acquisition_source": str(self.acquisition_source.currentData()),
            "sweep_mode": str(self.sweep_mode.currentData()),
            "hardware_rep_delay_us": self.hardware_rep_delay_us.value(),
            "fpga_trigger_delay_us": (
                self.fpga_trigger_delay_us.value()
                if self.override_fpga_trigger_delay.isChecked()
                else None
            ),
            "modulation_frequency_mhz": self.modulation_frequency_mhz.value(),
            "modulation_gain": self.modulation_gain.value(),
            "modulation_power_calibration": {
                "enabled": (
                    self.modulation_power_calibration_group.isChecked()
                ),
                "database_path": (
                    self.modulation_power_calibration_path.text().strip()
                ),
                "run_id": self.modulation_power_calibration_run_id.value(),
                "target_power_dbm": (
                    self.modulation_target_power_dbm.value()
                ),
            },
            "bias_t_compensation": {
                "enabled": self.bias_t_group.isChecked(),
                "type": str(self.bias_t_type.currentData()),
                "mode": str(self.bias_t_mode.currentData()),
                "voltage_mv": self.bias_t_compensation_mv.value(),
                "duration_us": self.bias_t_duration_us.value(),
                "filter_tau_us": self.bias_t_filter_tau_us.value(),
            },
            "rf_path": dict(self.front_panel_values()),
            "color_ranges": self.plot.color_range_settings(),
            "visible_data": list(self.plot.visible_data()),
            "database_path": self.database_path_value(),
            "iq_storage_mode": self.iq_storage_mode_value(),
            "saved_plot_database_path": (
                self.saved_database_path_value()
            ),
            "saved_plot_run_id": int(
                self.saved_run_combo.currentData()
                or self._preferred_saved_run_id
            ),
            "saved_plot_data": str(self.saved_plot_data.currentData()),
            "measurement_representation": str(
                self.measurement_unit.currentData()
            ),
            "dc_measure_gain_v_per_a": (
                self.dc_measure_gain_v_per_a.value()
            ),
            "dc_voltage_calibration_enabled": (
                self.dc_calibration_group.isChecked()
            ),
            "dc_voltage_calibration_database_path": (
                self.dc_calibration_path.text().strip()
            ),
            "dc_voltage_calibration_run_id": (
                self.dc_calibration_run_id.value()
            ),
        }

    def load_settings(self, settings: Mapping[str, Any]) -> None:
        self.x_axis.load_settings(settings["x_axis"])
        self.y_axis.load_settings(settings["y_axis"])
        self.refresh_targets(*self._awg_targets)
        self.repetitions.setValue(int(settings["repetitions_per_point"]))
        self.trace_samples.setValue(
            int(
                settings.get(
                    "trace_samples_per_point",
                    DEFAULT_STABILITY_TRACE_SAMPLES,
                )
            )
        )
        self.settle_time_us.setValue(
            float(settings.get("settle_time_us", DEFAULT_STABILITY_SETTLE_US))
        )
        source_index = self.acquisition_source.findData(
            str(settings.get("acquisition_source", "fir_ddr"))
        )
        if source_index < 0:
            raise ValueError("saved Stability acquisition source is invalid")
        self.acquisition_source.setCurrentIndex(source_index)
        sweep_mode_index = self.sweep_mode.findData(
            str(settings.get("sweep_mode", "hardware"))
        )
        if sweep_mode_index < 0:
            raise ValueError("saved Stability sweep mode is invalid")
        self.sweep_mode.setCurrentIndex(sweep_mode_index)
        self.hardware_rep_delay_us.setValue(
            float(
                settings.get(
                    "hardware_rep_delay_us",
                    DEFAULT_STABILITY_HARDWARE_REP_DELAY_US,
                )
            )
        )
        saved_fpga_delay = settings.get("fpga_trigger_delay_us")
        self.override_fpga_trigger_delay.setChecked(
            saved_fpga_delay is not None
        )
        if saved_fpga_delay is not None:
            self.fpga_trigger_delay_us.setValue(float(saved_fpga_delay))
        elif self._fir_sample_rate_hz is not None:
            self.fpga_trigger_delay_us.setValue(
                self._fir_trigger_delay_us
            )
        self.modulation_frequency_mhz.setValue(
            float(
                settings.get(
                    "modulation_frequency_mhz",
                    DEFAULT_STABILITY_MODULATION_FREQUENCY_MHZ,
                )
            )
        )
        self.modulation_gain.setValue(
            int(settings.get("modulation_gain", DEFAULT_STABILITY_MODULATION_GAIN))
        )
        modulation_calibration = settings.get(
            "modulation_power_calibration",
            default_stability_settings()["modulation_power_calibration"],
        )
        with QtCore.QSignalBlocker(
            self.modulation_power_calibration_group
        ), QtCore.QSignalBlocker(
            self.modulation_power_calibration_path
        ), QtCore.QSignalBlocker(
            self.modulation_power_calibration_run_id
        ), QtCore.QSignalBlocker(
            self.modulation_target_power_dbm
        ):
            self.modulation_power_calibration_group.setChecked(
                bool(modulation_calibration["enabled"])
            )
            self.modulation_power_calibration_path.setText(
                str(modulation_calibration["database_path"])
            )
            self.modulation_power_calibration_run_id.setValue(
                int(modulation_calibration["run_id"])
            )
            self.modulation_target_power_dbm.setValue(
                float(modulation_calibration["target_power_dbm"])
            )
        self._resolved_modulation_power_signature = None
        self._resolved_modulation_power_run_id = None
        bias_t = settings.get(
            "bias_t_compensation",
            default_stability_settings()["bias_t_compensation"],
        )
        bias_t_type_index = self.bias_t_type.findData(str(bias_t["type"]))
        if bias_t_type_index < 0:
            raise ValueError("saved Stability Bias-T compensation type is invalid")
        bias_t_mode_index = self.bias_t_mode.findData(str(bias_t["mode"]))
        if bias_t_mode_index < 0:
            raise ValueError("saved Stability Bias-T compensation mode is invalid")
        with QtCore.QSignalBlocker(self.bias_t_group), QtCore.QSignalBlocker(
            self.bias_t_type
        ), QtCore.QSignalBlocker(self.bias_t_mode), QtCore.QSignalBlocker(
            self.bias_t_compensation_mv
        ), QtCore.QSignalBlocker(self.bias_t_duration_us), QtCore.QSignalBlocker(
            self.bias_t_filter_tau_us
        ):
            self.bias_t_group.setChecked(bool(bias_t["enabled"]))
            self.bias_t_type.setCurrentIndex(bias_t_type_index)
            self.bias_t_mode.setCurrentIndex(bias_t_mode_index)
            self.bias_t_compensation_mv.setValue(float(bias_t["voltage_mv"]))
            self.bias_t_duration_us.setValue(float(bias_t["duration_us"]))
            self.bias_t_filter_tau_us.setValue(float(bias_t["filter_tau_us"]))
        self.apply_path_settings(
            settings.get("rf_path", DEFAULT_STABILITY_RF_PATH)
        )
        self.plot.load_color_range_settings(
            settings.get(
                "color_ranges",
                default_stability_settings()["color_ranges"],
            )
        )
        self.plot.load_visible_data(
            settings.get(
                "visible_data",
                default_stability_settings()["visible_data"],
            )
        )
        self.database_path.setText(
            str(settings.get("database_path", DEFAULT_STABILITY_DB_PATH))
        )
        storage_mode = normalize_iq_storage_mode(
            settings.get("iq_storage_mode", DEFAULT_IQ_STORAGE_MODE)
        )
        storage_index = self.iq_storage_mode.findData(storage_mode)
        if storage_index < 0:
            raise ValueError(f"unsupported Stability I/Q storage mode {storage_mode!r}")
        self.iq_storage_mode.setCurrentIndex(storage_index)
        self.saved_database_path.setText(
            str(
                settings.get(
                    "saved_plot_database_path",
                    settings.get(
                        "database_path",
                        DEFAULT_STABILITY_DB_PATH,
                    ),
                )
            )
        )
        self._preferred_saved_run_id = int(
            settings.get("saved_plot_run_id", 0)
        )
        saved_plot_data_index = self.saved_plot_data.findData(
            str(settings.get("saved_plot_data", "magnitude"))
        )
        if saved_plot_data_index < 0:
            raise ValueError(
                "saved Stability Diagram plot data is invalid"
            )
        self.saved_plot_data.setCurrentIndex(saved_plot_data_index)
        representation = str(
            settings.get(
                "measurement_representation",
                (
                    "current"
                    if self.dc_measure_mode.isChecked()
                    else (
                        "voltage"
                        if settings.get(
                            "dc_voltage_calibration_enabled",
                            False,
                        )
                        else "adc"
                    )
                ),
            )
        )
        unit_index = self.measurement_unit.findData(representation)
        if unit_index < 0:
            raise ValueError(
                "saved Stability measurement representation is invalid"
            )
        with QtCore.QSignalBlocker(self.measurement_unit):
            self.measurement_unit.setCurrentIndex(unit_index)
        with QtCore.QSignalBlocker(self.dc_measure_mode):
            self.dc_measure_mode.setChecked(representation == "current")
        with QtCore.QSignalBlocker(self.dc_measure_gain_v_per_a):
            self.dc_measure_gain_v_per_a.setValue(
                float(settings.get("dc_measure_gain_v_per_a", 1.0))
            )
        with QtCore.QSignalBlocker(self.dc_calibration_group):
            self.dc_calibration_group.setChecked(
                bool(settings.get("dc_voltage_calibration_enabled", False))
            )
        with QtCore.QSignalBlocker(self.dc_calibration_path):
            self.dc_calibration_path.setText(
                str(
                    settings.get(
                        "dc_voltage_calibration_database_path",
                        "",
                    )
                )
            )
        with QtCore.QSignalBlocker(self.dc_calibration_run_id):
            self.dc_calibration_run_id.setValue(
                int(settings.get("dc_voltage_calibration_run_id", 0))
            )
        self._update_point_count()
        self._update_modulation_power_calibration_controls()
        self._modulation_power_calibration_changed()
        self._update_dc_measure_controls()
        self._update_bias_t_controls()
        self._update_fpga_trigger_delay_controls()
        self._update_acquisition_controls()

    def set_running(self, running: bool, message: str) -> None:
        self._running = bool(running)
        idle_enabled = (
            not running
            and not self._saved_run_loading
            and self._targets_available
        )
        self.start_button.setEnabled(idle_enabled)
        self.single_shot_button.setEnabled(idle_enabled)
        self.stop_button.setEnabled(running)
        for editor in (self.x_axis, self.y_axis):
            editor.setEnabled(not running)
        self.repetitions.setEnabled(not running)
        self.trace_samples.setEnabled(not running)
        self.settle_time_us.setEnabled(not running)
        self.acquisition_source.setEnabled(not running)
        self.sweep_mode.setEnabled(not running)
        self.hardware_rep_delay_us.setEnabled(
            not running and self.sweep_mode.currentData() == "hardware"
        )
        self.override_fpga_trigger_delay.setEnabled(
            not running
            and self.acquisition_source.currentData() == "fir_ddr"
            and self._fir_uses_fpga_trigger_delay is not False
        )
        self.fpga_trigger_delay_us.setEnabled(
            not running
            and self.acquisition_source.currentData() == "fir_ddr"
            and self._fir_uses_fpga_trigger_delay is not False
            and self.override_fpga_trigger_delay.isChecked()
        )
        self.modulation_frequency_mhz.setEnabled(not running)
        self.modulation_gain.setEnabled(not running)
        self.bias_t_group.setEnabled(not running)
        self.path_diagram.setEnabled(not running)
        database_enabled = not running and not self._saved_run_loading
        for widget in (
            self.database_path,
            self.browse_database,
            self.saved_database_path,
            self.browse_saved_database,
            self.saved_run_combo,
            self.saved_plot_data,
            self.refresh_saved_runs_button,
            self.load_saved_run_button,
        ):
            widget.setEnabled(database_enabled)
        self._update_dc_measure_controls()
        self._update_modulation_power_calibration_controls()
        self._update_bias_t_controls()
        self._update_acquisition_controls()
        self.progress.setVisible(running)
        if not running:
            self.progress.setValue(0)
        self.status.setText(message)

    def set_stopping(self) -> None:
        self.stop_button.setEnabled(False)
        self.status.setText("Stopping after the active full scan completes...")

    def update_progress(self, percent: int, message: str) -> None:
        self.progress.setValue(max(0, min(100, int(percent))))
        self.status.setText(f"{int(percent)}% - {message}")

    def show_result(self, result: StabilityDiagramResult) -> None:
        self.plot.set_result(result)
        rate_label = format_sample_rate_hz(result.sample_rate_hz)
        trace_us = (
            result.samples_per_trace * 1_000_000.0 / result.sample_rate_hz
        )
        self.status.setText(
            f"{result.source_label or f'Scan {result.iteration}'} complete: "
            f"{result.magnitude.shape[1]} x {result.magnitude.shape[0]} points "
            f"({result.value_unit}); {result.samples_per_trace:,} samples at "
            f"{rate_label} = {trace_us:g} us / trace"
        )

    def show_loaded_run(self, result: StabilityDiagramResult) -> None:
        self.set_saved_run_loading(False)
        self.plot.set_result(result)
        self.saved_run_status.setText(
            f"Loaded {result.source_label} from {result.database_path}."
        )
        self.status.setText(
            f"Displaying {result.source_label}: "
            f"{result.magnitude.shape[1]} x {result.magnitude.shape[0]} points, "
            f"{result.repetition_count} repetitions x "
            f"{result.samples_per_trace} FIR samples."
        )

    def show_saved_result(self, stored: StoredStabilityDiagram) -> None:
        self.plot.set_result(stored.diagram)
        self.set_running(
            False,
            f"QCoDeS Run {stored.run_id} saved to {stored.database_path}",
        )

    def detach_plot(self) -> StabilityDiagramPlotWidget:
        """Remove the plot from this panel for use in a main-window dock."""
        self.layout().removeWidget(self.plot)
        self.plot.setParent(None)
        return self.plot

    def _set_idle_button_state(self) -> None:
        if self.stop_button.isEnabled():
            return
        self.start_button.setEnabled(self._targets_available)
        self.single_shot_button.setEnabled(self._targets_available)

    def _update_point_count(self, *_args) -> None:
        self.point_count.setText(
            f"{self.x_axis.points.value() * self.y_axis.points.value():,}"
        )


__all__ = [
    "DEFAULT_STABILITY_BIAS_T_COMPENSATION_MV",
    "DEFAULT_STABILITY_COLOR_RANGES",
    "DEFAULT_STABILITY_VISIBLE_DATA",
    "DEFAULT_STABILITY_POINTS",
    "DEFAULT_STABILITY_REPETITIONS",
    "DEFAULT_STABILITY_MODULATION_FREQUENCY_MHZ",
    "DEFAULT_STABILITY_MODULATION_GAIN",
    "DEFAULT_STABILITY_POWER_CALIBRATION_DB_PATH",
    "DEFAULT_STABILITY_RF_PATH",
    "DEFAULT_STABILITY_TARGET_POWER_DBM",
    "DEFAULT_STABILITY_TRACE_SAMPLES",
    "DEFAULT_STABILITY_START_MV",
    "DEFAULT_STABILITY_STOP_MV",
    "StabilityDiagramConfig",
    "StabilityDiagramPanel",
    "StabilityDiagramPlotWidget",
    "StabilityDiagramResult",
    "StabilityDiagramWorker",
    "StabilityOverlayLoadWorker",
    "StabilityOverlaySelector",
    "StabilityRunSummary",
    "StabilitySweepAxis",
    "STABILITY_DATA_KEYS",
    "StoredStabilityDiagram",
    "default_stability_settings",
    "list_stability_runs",
    "load_stability_diagram_run",
    "normalize_stability_settings",
    "normalize_stability_color_ranges",
    "normalize_stability_visible_data",
    "reduce_fir_stability_result",
    "stability_result_from_stored_arrays",
]
