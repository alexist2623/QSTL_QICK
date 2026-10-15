"""Interactive two-dimensional maps from Cartesian AWG tuning sweeps.

Saved runs may contain every repetition trace or one already-reduced I/Q pair
per Cartesian point. This module coherently reduces any retained repetition and
FIR-sample axes, then arranges two user-selected sweep variables on X and Y.
Every remaining sweep variable can either be fixed to one acquired value or
averaged independently at each selected X/Y coordinate.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
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
    from .dc_waveform_core import DEFAULT_QICK_FULL_SCALE_MV
    from .fir_ddr_profile import format_sample_rate_hz
    from .measurement_display import (
        ColorRangeControl,
        attach_color_bar,
        scale_iq_for_display,
    )
    from .qick_qcodes_experiment import load_qick_iq_arrays
except ImportError:
    from dc_waveform_core import DEFAULT_QICK_FULL_SCALE_MV
    from fir_ddr_profile import format_sample_rate_hz
    from measurement_display import (
        ColorRangeControl,
        attach_color_bar,
        scale_iq_for_display,
    )
    from qick_qcodes_experiment import load_qick_iq_arrays


SweepAxisKey = Tuple[str, str]
DEFAULT_AWG_SWEEP_DB_PATH = str(Path.home() / "qick_experiments.db")
DEFAULT_AWG_SWEEP_COLOR_RANGES = {
    "i": {"auto": True, "minimum": -1.0, "maximum": 1.0},
    "q": {"auto": True, "minimum": -1.0, "maximum": 1.0},
    "magnitude": {"auto": True, "minimum": 0.0, "maximum": 1.0},
    "angle": {"auto": False, "minimum": -180.0, "maximum": 180.0},
}
AWG_SWEEP_DATA_KEYS = ("i", "q", "magnitude", "angle")
DEFAULT_AWG_SWEEP_VISIBLE_DATA = AWG_SWEEP_DATA_KEYS


def normalize_awg_sweep_color_ranges(
    settings: Optional[Mapping[str, Any]],
) -> dict:
    """Validate persisted AWG map color ranges with backward-safe defaults."""
    if settings is None:
        settings = {}
    if not isinstance(settings, Mapping):
        raise TypeError("AWG sweep color_ranges must be a JSON object")
    normalized = {}
    for name, defaults in DEFAULT_AWG_SWEEP_COLOR_RANGES.items():
        raw = settings.get(name, defaults)
        if not isinstance(raw, Mapping):
            raise TypeError(f"AWG sweep {name} color range must be an object")
        auto = raw.get("auto", defaults["auto"])
        if not isinstance(auto, (bool, np.bool_)):
            raise TypeError(f"AWG sweep {name} auto range must be boolean")
        minimum = float(raw.get("minimum", defaults["minimum"]))
        maximum = float(raw.get("maximum", defaults["maximum"]))
        if (
            not np.isfinite(minimum)
            or not np.isfinite(maximum)
            or minimum >= maximum
        ):
            raise ValueError(
                f"AWG sweep {name} color minimum must be finite and below maximum"
            )
        normalized[name] = {
            "auto": bool(auto),
            "minimum": minimum,
            "maximum": maximum,
        }
    return normalized


def normalize_awg_sweep_visible_data(values: Any) -> Tuple[str, ...]:
    """Validate the ordered set of maps shown in the AWG 2-D result dock."""
    if values is None:
        return DEFAULT_AWG_SWEEP_VISIBLE_DATA
    if not isinstance(values, (list, tuple)):
        raise TypeError("AWG sweep visible_data must be a JSON array")
    normalized = []
    for value in values:
        key = str(value).strip().lower()
        if key not in AWG_SWEEP_DATA_KEYS:
            raise ValueError(f"unknown AWG sweep plot data {value!r}")
        if key not in normalized:
            normalized.append(key)
    if not normalized:
        raise ValueError("at least one AWG sweep plot must be visible")
    return tuple(normalized)


def sweep_axis_key(axis: Any) -> SweepAxisKey:
    """Return the stable ``(output_name, segment_name)`` key for one axis."""
    return str(axis.output_name), str(axis.segment_name)


def sweep_axis_label(axis: Any) -> str:
    """Return the compact user-facing name for one sweep variable."""
    output_name, segment_name = sweep_axis_key(axis)
    axis_kind = getattr(axis, "axis_kind", "amplitude")
    if axis_kind.startswith("square_"):
        return f"{output_name} / {segment_name} SquarePulse"
    if axis_kind == "rf_template_n":
        return f"{output_name} / {segment_name} template N"
    if axis_kind == "rf_template_tau":
        return f"{output_name} / {segment_name} template tau"
    if axis_kind == "rf_delay":
        return f"{output_name} / {segment_name} RF delay {axis.parameter_name}"
    if axis_kind == "rf_t2_duration":
        return f"{output_name} / {segment_name} T2 pi duration"
    if axis_kind == "rf_amplitude":
        return f"{output_name} / {segment_name} RF amplitude {axis.parameter_name}"
    if axis_kind == "rf_phase":
        return f"{output_name} / {segment_name} RF phase {axis.parameter_name}"
    if axis_kind == "rf_duration":
        return f"{output_name} / {segment_name} RF duration"
    if axis_kind == "rf_frequency":
        return f"{output_name} / {segment_name} RF frequency"
    if axis_kind == "rf_power":
        return f"{output_name} / {segment_name} RF power"
    if axis_kind == "ramp_duration":
        return f"{segment_name} RAMP duration (rate derived)"
    if axis_kind == "hold_duration":
        return f"{segment_name} SET hold duration"
    return f"{output_name} / {segment_name}"


def _axis_display_values(
    coordinates: np.ndarray,
    axis: Any,
    full_scale_mv: float,
) -> Tuple[np.ndarray, str]:
    axis_kind = getattr(axis, "axis_kind", "amplitude")
    if axis_kind.startswith("square_"):
        return np.asarray(coordinates, dtype=np.float64), {"square_frequency":"MHz", "square_amplitude":"mV", "square_phase":"deg"}[axis_kind]
    if axis_kind == "rf_template_n":
        return np.asarray(coordinates, dtype=np.float64), "count"
    if axis_kind == "rf_amplitude":
        return np.asarray(coordinates, dtype=np.float64), axis.coordinate_unit
    if axis_kind == "rf_phase":
        return np.asarray(coordinates, dtype=np.float64), "deg"
    if axis_kind in {
        "rf_template_tau",
        "rf_delay",
        "rf_t2_duration",
        "rf_duration",
        "ramp_duration",
        "hold_duration",
    }:
        return np.asarray(coordinates, dtype=np.float64), "us"
    if axis_kind == "rf_frequency":
        return np.asarray(coordinates, dtype=np.float64), "MHz"
    if axis_kind == "rf_power":
        return np.asarray(coordinates, dtype=np.float64), "dBm"
    return np.asarray(coordinates, dtype=np.float64) * full_scale_mv, "mV"


@dataclass(frozen=True)
class AwgSweepMapSource:
    """Unreduced Cartesian sweep data used for interactive reprojection."""

    sweep_axes: Tuple[Any, ...]
    sweep_points: np.ndarray
    iq_values: np.ndarray
    full_scale_mv: float
    value_unit: str
    measurement_mode: str
    sample_rate_hz: float
    source_label: str = ""
    database_path: str = ""
    run_id: int = 0


@dataclass(frozen=True)
class AwgSweepMapResult:
    """I/Q and derived values on two selected AWG sweep axes."""

    x_values: np.ndarray
    y_values: np.ndarray
    i_mean: np.ndarray
    q_mean: np.ndarray
    magnitude: np.ndarray
    angle_deg: np.ndarray
    x_axis_key: SweepAxisKey
    y_axis_key: SweepAxisKey
    x_axis_label: str
    y_axis_label: str
    x_unit: str
    y_unit: str
    value_unit: str
    base_value_unit: str
    display_scale: float
    measurement_mode: str
    repetition_count: int
    samples_per_trace: int
    averaged_axis_labels: Tuple[str, ...]
    source_points_per_cell: int
    sample_rate_hz: float
    source_label: str = ""
    database_path: str = ""
    run_id: int = 0
    fixed_axis_values: Tuple[Tuple[SweepAxisKey, float], ...] = ()
    fixed_axis_labels: Tuple[str, ...] = ()
    source: Optional[AwgSweepMapSource] = None

    @property
    def x_values_mv(self) -> np.ndarray:
        """Backward-compatible alias for pre-duration-sweep callers."""
        return self.x_values

    @property
    def y_values_mv(self) -> np.ndarray:
        """Backward-compatible alias for pre-duration-sweep callers."""
        return self.y_values


@dataclass(frozen=True)
class AwgSweepRunSummary:
    """Metadata-only description of one saved AWG Cartesian sweep."""

    database_path: str
    run_id: int
    created_at_utc: str
    x_axis_label: str
    y_axis_label: str
    x_points: int
    y_points: int
    sweep_axis_count: int
    iq_unit: str
    sample_rate_hz: float

    @property
    def display_label(self) -> str:
        timestamp = self.created_at_utc.replace("T", " ")[:19]
        timestamp_text = f" | {timestamp}" if timestamp else ""
        averaged_count = max(0, self.sweep_axis_count - 2)
        averaged_text = (
            f" | +{averaged_count} averaged axis/axes"
            if averaged_count
            else ""
        )
        return (
            f"Run {self.run_id}{timestamp_text} | "
            f"{self.x_axis_label} x {self.y_axis_label} | "
            f"{self.x_points} x {self.y_points}{averaged_text} | "
            f"{format_sample_rate_hz(self.sample_rate_hz)} | {self.iq_unit}"
        )


def _stored_sweep_axes(
    metadata: Mapping[str, Any],
) -> Tuple[Mapping[str, Any], ...]:
    layout = metadata.get("measurement_layout", {})
    if not isinstance(layout, Mapping):
        raise ValueError("stored QICK measurement layout is missing")
    raw_axes = layout.get("sweep_axes", ())
    if not isinstance(raw_axes, Sequence) or isinstance(raw_axes, (str, bytes)):
        raise ValueError("stored QICK sweep-axis metadata is invalid")
    axes = tuple(axis for axis in raw_axes if isinstance(axis, Mapping))
    if len(axes) < 2:
        raise ValueError("a saved AWG 2D map requires at least two sweep axes")
    return axes


def _stored_axis_key(axis: Mapping[str, Any]) -> SweepAxisKey:
    return str(axis.get("output_name", "")), str(axis.get("segment_name", ""))


def _stored_axis_label(axis: Mapping[str, Any]) -> str:
    output_name, segment_name = _stored_axis_key(axis)
    axis_kind = str(axis.get("axis_kind", "amplitude"))
    if axis_kind.startswith("square_"):
        return f"{output_name} / {segment_name} SquarePulse"
    if axis_kind == "rf_template_n":
        return f"{output_name} / {segment_name} template N"
    if axis_kind == "rf_template_tau":
        return f"{output_name} / {segment_name} template tau"
    if axis_kind == "rf_delay":
        return f"{output_name} / {segment_name} RF delay {axis.get('parameter_name', '')}"
    if axis_kind == "rf_t2_duration":
        return f"{output_name} / {segment_name} T2 pi duration"
    if axis_kind == "rf_amplitude":
        return f"{output_name} / {segment_name} RF amplitude {axis.get('parameter_name', '')}"
    if axis_kind == "rf_phase":
        return f"{output_name} / {segment_name} RF phase {axis.get('parameter_name', '')}"
    if axis_kind == "rf_duration":
        return f"{output_name} / {segment_name} RF duration"
    if axis_kind == "rf_frequency":
        return f"{output_name} / {segment_name} RF frequency"
    if axis_kind == "rf_power":
        return f"{output_name} / {segment_name} RF power"
    if axis_kind == "ramp_duration":
        return f"{segment_name} RAMP duration (rate derived)"
    if axis_kind == "hold_duration":
        return f"{segment_name} SET hold duration"
    return f"{output_name} / {segment_name}"


def _stored_selected_axes(
    metadata: Mapping[str, Any],
) -> Tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Resolve the X/Y axes selected when the QCoDeS run was saved."""
    axes = _stored_sweep_axes(metadata)
    by_key = {_stored_axis_key(axis): axis for axis in axes}
    gui_settings = metadata.get("gui_settings", {})
    experiment_settings = (
        gui_settings.get("experiment", {})
        if isinstance(gui_settings, Mapping)
        else {}
    )
    sweep_map_settings = (
        experiment_settings.get("sweep_map", {})
        if isinstance(experiment_settings, Mapping)
        else {}
    )
    if not isinstance(sweep_map_settings, Mapping):
        sweep_map_settings = {}

    requested = []
    for name in ("x_axis", "y_axis"):
        axis_settings = sweep_map_settings.get(name, {})
        if not isinstance(axis_settings, Mapping):
            requested.append(("", ""))
            continue
        requested.append(
            (
                str(axis_settings.get("output_name", "")),
                str(axis_settings.get("segment_name", "")),
            )
        )
    if (
        len(requested) == 2
        and requested[0] != requested[1]
        and all(key in by_key for key in requested)
    ):
        return by_key[requested[0]], by_key[requested[1]]
    return axes[0], axes[1]


def _is_awg_sweep_metadata(metadata: Mapping[str, Any]) -> bool:
    """Return true for regular AWG experiments with a plottable 2D sweep."""
    try:
        _stored_sweep_axes(metadata)
    except (TypeError, ValueError):
        return False
    gui_settings = metadata.get("gui_settings", {})
    qick_settings = (
        gui_settings.get("qick", {})
        if isinstance(gui_settings, Mapping)
        else {}
    )
    return not (
        isinstance(qick_settings, Mapping)
        and bool(qick_settings.get("fir_stability_capture_mode"))
    )


def list_awg_sweep_runs(
    database_path: Any,
) -> Tuple[AwgSweepRunSummary, ...]:
    """List compatible saved AWG sweep runs without loading trace arrays."""
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
            if not isinstance(metadata, Mapping) or not _is_awg_sweep_metadata(
                metadata
            ):
                continue
            axes = _stored_sweep_axes(metadata)
            x_axis, y_axis = _stored_selected_axes(metadata)
            layout = metadata.get("measurement_layout", {})
            sample_rate_hz = float(
                layout.get(
                    "sample_rate_hz",
                    1.0e6 / float(layout.get("sample_period_us", 1.0)),
                )
            )
            summaries.append(
                AwgSweepRunSummary(
                    database_path=str(path),
                    run_id=int(run_id),
                    created_at_utc=str(metadata.get("created_at_utc", "")),
                    x_axis_label=_stored_axis_label(x_axis),
                    y_axis_label=_stored_axis_label(y_axis),
                    x_points=int(x_axis.get("count", 0)),
                    y_points=int(y_axis.get("count", 0)),
                    sweep_axis_count=len(axes),
                    iq_unit=str(layout.get("iq_unit", "ADC units")),
                    sample_rate_hz=sample_rate_hz,
                )
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return tuple(summaries)


def _stored_full_scale_mv(metadata: Mapping[str, Any]) -> float:
    gui_settings = metadata.get("gui_settings", {})
    qick_settings = (
        gui_settings.get("qick", {})
        if isinstance(gui_settings, Mapping)
        else {}
    )
    full_scale_mv = float(
        qick_settings.get("full_scale_mv", DEFAULT_QICK_FULL_SCALE_MV)
    )
    if not np.isfinite(full_scale_mv) or full_scale_mv <= 0.0:
        raise ValueError("stored AWG full scale must be positive and finite")
    return full_scale_mv


def _stored_axis_native_values(
    values: Any,
    axis: Mapping[str, Any],
    *,
    full_scale_mv: float,
) -> np.ndarray:
    """Convert QCoDeS display units back to the in-memory sweep convention."""
    coordinates = np.asarray(values, dtype=np.float64)
    unit = str(axis.get("unit", "")).strip().lower()
    axis_kind = str(axis.get("axis_kind", "amplitude"))
    if axis_kind == "rf_amplitude":
        if unit in {"gain", "dbm"}:
            return coordinates
        raise ValueError(f"unsupported stored RF amplitude unit {axis.get('unit')!r}")
    if axis_kind == "rf_phase":
        if unit in {"deg", "degree", "degrees"}:
            return coordinates
        raise ValueError(f"unsupported stored RF phase unit {axis.get('unit')!r}")
    if axis_kind == "rf_template_n":
        if unit in {"", "count", "counts", "pulse", "pulses"}:
            return coordinates
        raise ValueError(
            f"unsupported stored RF template N unit {axis.get('unit')!r}"
        )
    if axis_kind in {
        "rf_template_tau",
        "rf_delay",
        "rf_t2_duration",
        "rf_duration",
        "ramp_duration",
        "hold_duration",
    }:
        duration_scales = {
            "": 1.0,
            "us": 1.0,
            "µs": 1.0,
            "μs": 1.0,
            "ns": 1.0e-3,
            "ms": 1.0e3,
            "s": 1.0e6,
        }
        try:
            return coordinates * duration_scales[unit]
        except KeyError as exc:
            raise ValueError(
                f"unsupported stored AWG duration unit {axis.get('unit')!r}"
            ) from exc

    if axis_kind in {"rf_frequency", "square_frequency"}:
        frequency_scales_to_mhz = {
            "": 1.0,
            "mhz": 1.0,
            "hz": 1.0e-6,
            "khz": 1.0e-3,
            "ghz": 1.0e3,
        }
        try:
            return coordinates * frequency_scales_to_mhz[unit]
        except KeyError as exc:
            raise ValueError(
                f"unsupported stored RF frequency unit {axis.get('unit')!r}"
            ) from exc

    if axis_kind == "rf_power":
        if unit in {"", "dbm"}:
            return coordinates
        raise ValueError(
            f"unsupported stored RF power unit {axis.get('unit')!r}"
        )

    if axis_kind == "square_amplitude":
        if unit == "mv": return coordinates
        if unit == "v": return coordinates * 1000
        raise ValueError("unsupported stored SquarePulse amplitude unit")
    if axis_kind == "square_phase":
        if unit in {"deg", "degree", "degrees"}: return coordinates
        raise ValueError("unsupported stored SquarePulse phase unit")
    if unit == "mv":
        return coordinates / full_scale_mv
    if unit == "v":
        return coordinates * 1_000.0 / full_scale_mv
    if unit in {"", "normalized", "fraction"}:
        return coordinates
    raise ValueError(
        f"unsupported stored AWG voltage unit {axis.get('unit')!r}"
    )


def awg_sweep_result_from_stored_arrays(
    arrays: Mapping[str, Any],
    *,
    database_path: Any,
    run_id: int,
) -> AwgSweepMapResult:
    """Reconstruct an AWG I/Q map from one split-array QCoDeS run."""
    metadata = arrays.get("metadata", {})
    if not isinstance(metadata, Mapping) or not _is_awg_sweep_metadata(metadata):
        raise ValueError(f"QCoDeS Run {run_id} is not an AWG 2D sweep run")
    axes_metadata = _stored_sweep_axes(metadata)
    selected_x, selected_y = _stored_selected_axes(metadata)
    sweep_coordinates = arrays.get("sweep_coordinates", {})
    if not isinstance(sweep_coordinates, Mapping):
        raise ValueError("stored AWG sweep coordinates are missing")

    iq = np.asarray(arrays["iq"])
    if iq.ndim != 4 or iq.shape[-1] != 2:
        raise ValueError(
            "stored AWG sweep IQ must have "
            "(point, repetition, sample, 2) shape"
        )
    full_scale_mv = _stored_full_scale_mv(metadata)
    coordinate_columns = []
    axis_objects = []
    for axis in axes_metadata:
        parameter_name = str(axis.get("parameter", ""))
        if not parameter_name or parameter_name not in sweep_coordinates:
            raise ValueError(
                "stored AWG coordinate parameters do not match metadata"
            )
        per_repetition = np.asarray(
            sweep_coordinates[parameter_name],
            dtype=np.float64,
        )
        if per_repetition.shape != iq.shape[:2]:
            raise ValueError(
                "stored AWG coordinate shape does not match I/Q traces"
            )
        if not np.allclose(per_repetition, per_repetition[:, :1]):
            raise ValueError(
                "stored AWG sweep coordinates change between repetitions"
            )
        native_values = _stored_axis_native_values(
            per_repetition[:, 0],
            axis,
            full_scale_mv=full_scale_mv,
        )
        coordinate_columns.append(native_values)
        axis_objects.append(
            SimpleNamespace(
                output_name=str(axis.get("output_name", "")),
                segment_name=str(axis.get("segment_name", "")),
                axis_kind=str(axis.get("axis_kind", "amplitude")),
                parameter_name=str(axis.get("parameter_name", "")),
                coordinate_unit=str(axis.get("unit", "")),
                start=float(np.min(native_values)),
                stop=float(np.max(native_values)),
                count=int(axis.get("count", np.unique(native_values).size)),
            )
        )

    layout = metadata.get("measurement_layout", {})
    sample_rate_hz = float(
        layout.get(
            "sample_rate_hz",
            1.0e6 / float(layout.get("sample_period_us", 1.0)),
        )
    )
    ddr_result = SimpleNamespace(
        sweep_axes=tuple(axis_objects),
        sweep_points=np.column_stack(coordinate_columns),
        iq=iq,
        sample_rate_hz=sample_rate_hz,
    )
    result = reduce_awg_sweep_map(
        ddr_result,
        x_axis_key=_stored_axis_key(selected_x),
        y_axis_key=_stored_axis_key(selected_y),
        full_scale_mv=full_scale_mv,
        iq_values=iq,
        value_unit=str(arrays.get("iq_unit", "ADC units")),
        measurement_mode=str(arrays.get("measurement_mode", "raw_iq")),
    )
    path = Path(database_path).expanduser().resolve()
    result_source = result.source
    if result_source is not None:
        result_source = replace(
            result_source,
            source_label=f"QCoDeS Run {int(run_id)}",
            database_path=str(path),
            run_id=int(run_id),
        )
    return replace(
        result,
        repetition_count=int(
            arrays.get("source_repetition_count", result.repetition_count)
        ),
        samples_per_trace=int(
            arrays.get("source_sample_count", result.samples_per_trace)
        ),
        source_label=f"QCoDeS Run {int(run_id)}",
        database_path=str(path),
        run_id=int(run_id),
        source=result_source,
    )


def load_awg_sweep_run(
    database_path: Any,
    run_id: int,
) -> AwgSweepMapResult:
    """Load and reduce one saved AWG 2D sweep QCoDeS run."""
    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"QCoDeS database does not exist: {path}")
    if isinstance(run_id, bool):
        raise TypeError("AWG sweep Run ID must be an integer")
    run_id = int(run_id)
    if run_id < 1:
        raise ValueError("AWG sweep Run ID must be at least 1")
    try:
        from qcodes import initialise_or_create_database_at, load_by_id
    except ImportError as exc:
        raise RuntimeError(
            "QCoDeS==0.58.0 is required to load AWG sweep runs"
        ) from exc
    initialise_or_create_database_at(str(path))
    dataset = load_by_id(run_id)
    arrays = load_qick_iq_arrays(dataset)
    return awg_sweep_result_from_stored_arrays(
        arrays,
        database_path=path,
        run_id=run_id,
    )


class AwgSweepMapLoadWorker(QtCore.QObject):
    """Load one saved AWG sweep without blocking the GUI thread."""

    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, database_path: str, run_id: int, parent=None):
        super().__init__(parent)
        self._database_path = str(database_path)
        self._run_id = int(run_id)

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            result = load_awg_sweep_run(
                self._database_path,
                self._run_id,
            )
        except Exception:
            self.failed.emit(traceback.format_exc())
            return
        self.finished.emit(result)


class AwgSweepRunSelector(QtWidgets.QGroupBox):
    """Select the database and saved run displayed in the AWG map dock."""

    load_requested = QtCore.pyqtSignal(str, int)
    latest_requested = QtCore.pyqtSignal()

    def __init__(
        self,
        parent=None,
        *,
        default_database_path: str = DEFAULT_AWG_SWEEP_DB_PATH,
    ):
        super().__init__("Saved AWG Sweep", parent)
        self._summaries: Tuple[AwgSweepRunSummary, ...] = ()
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(6, 4, 6, 4)
        outer.setSpacing(4)

        database_row = QtWidgets.QHBoxLayout()
        database_row.addWidget(QtWidgets.QLabel("QCoDeS DB:", self))
        self.database_path = QtWidgets.QLineEdit(
            str(default_database_path),
            self,
        )
        self.database_path.setPlaceholderText(
            "Select a QCoDeS database containing AWG sweep runs"
        )
        database_row.addWidget(self.database_path, 1)
        self.browse_button = QtWidgets.QToolButton(self)
        self.browse_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton)
        )
        self.browse_button.setToolTip("Choose an AWG sweep QCoDeS database")
        self.browse_button.clicked.connect(self._browse_database)
        database_row.addWidget(self.browse_button)
        self.refresh_button = QtWidgets.QPushButton("Refresh Runs", self)
        self.refresh_button.clicked.connect(self.refresh_runs)
        database_row.addWidget(self.refresh_button)
        outer.addLayout(database_row)

        selection_row = QtWidgets.QHBoxLayout()
        selection_row.addWidget(QtWidgets.QLabel("Run:", self))
        self.run_combo = QtWidgets.QComboBox(self)
        self.run_combo.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        self.run_combo.setMinimumContentsLength(38)
        selection_row.addWidget(self.run_combo, 1)
        self.load_button = QtWidgets.QPushButton("Load Saved Map", self)
        self.load_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton)
        )
        self.load_button.clicked.connect(self._emit_load_requested)
        selection_row.addWidget(self.load_button)
        self.latest_button = QtWidgets.QPushButton(
            "Use Latest Experiment",
            self,
        )
        self.latest_button.clicked.connect(self.latest_requested.emit)
        selection_row.addWidget(self.latest_button)
        outer.addLayout(selection_row)

        self.status = QtWidgets.QLabel(
            "The map follows the latest in-memory AWG experiment.",
            self,
        )
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        outer.addWidget(self.status)

    def _browse_database(self) -> None:
        selected, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select AWG sweep QCoDeS database",
            self.database_path.text().strip(),
            "SQLite databases (*.db *.sqlite *.sqlite3);;All files (*)",
        )
        if not selected:
            return
        self.database_path.setText(selected)
        self.refresh_runs()

    def refresh_runs(self) -> None:
        previous_run_id = self.run_combo.currentData()
        try:
            summaries = list_awg_sweep_runs(
                self.database_path.text().strip()
            )
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
                f"Found {len(summaries)} compatible AWG sweep run(s)."
            )
        else:
            self.status.setText(
                "This database contains no compatible AWG 2D sweep runs."
            )

    def _emit_load_requested(self) -> None:
        run_id = self.run_combo.currentData()
        if run_id is None:
            self.status.setText("Refresh the DB and select a saved run first.")
            return
        self.load_requested.emit(
            self.database_path.text().strip(),
            int(run_id),
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

    def show_loaded_result(self, result: AwgSweepMapResult) -> None:
        self.set_loading(False)
        self.status.setText(
            f"Displaying {result.source_label or 'saved AWG sweep'} from "
            f"{result.database_path}."
        )

    def show_latest_result(
        self,
        result: Optional[AwgSweepMapResult],
    ) -> None:
        self.set_loading(False)
        if result is None:
            self.status.setText(
                "Following latest experiment; no AWG 2D map is available yet."
            )
        else:
            source = result.source_label or "latest in-memory experiment"
            self.status.setText(f"Displaying {source}.")


def reduce_awg_sweep_map(
    ddr_result: Any,
    *,
    x_axis_key: SweepAxisKey,
    y_axis_key: SweepAxisKey,
    full_scale_mv: float,
    iq_values: Optional[Any] = None,
    value_unit: str = "ADC units",
    measurement_mode: str = "raw_iq",
    fixed_axis_values: Optional[Mapping[SweepAxisKey, float]] = None,
    source: Optional[AwgSweepMapSource] = None,
) -> AwgSweepMapResult:
    """Reduce one Cartesian FIR acquisition to a selected two-axis map.

    I and Q are averaged coherently over repetitions and FIR samples. A
    non-selected sweep axis can be fixed to one acquired value; all remaining
    non-selected axes are averaged. Magnitude and angle are calculated only
    after this complex averaging.
    """
    full_scale_mv = float(full_scale_mv)
    if not np.isfinite(full_scale_mv) or full_scale_mv <= 0.0:
        raise ValueError("AWG full scale must be positive and finite")

    axes = tuple(ddr_result.sweep_axes)
    if len(axes) < 2:
        raise ValueError("at least two AWG sweep variables are required")
    axis_keys = tuple(sweep_axis_key(axis) for axis in axes)
    x_axis_key = tuple(map(str, x_axis_key))
    y_axis_key = tuple(map(str, y_axis_key))
    if x_axis_key == y_axis_key:
        raise ValueError("X and Y must use different AWG sweep variables")
    try:
        x_column = axis_keys.index(x_axis_key)
        y_column = axis_keys.index(y_axis_key)
    except ValueError as exc:
        raise ValueError(
            "selected AWG map axes are not present in the acquired sweep"
        ) from exc

    iq = np.asarray(result_iq_in_input_units(ddr_result) if iq_values is None else iq_values)
    if iq.ndim != 4 or iq.shape[-1] != 2:
        raise ValueError(
            "AWG sweep FIR IQ must have shape "
            "(point, repetition, sample, 2)"
        )
    coordinates = np.asarray(ddr_result.sweep_points, dtype=np.float64)
    expected_coordinate_shape = (iq.shape[0], len(axes))
    if coordinates.shape != expected_coordinate_shape:
        raise ValueError(
            "AWG sweep-coordinate shape does not match the acquired FIR IQ"
        )
    if not np.all(np.isfinite(coordinates)):
        raise ValueError("AWG sweep coordinates must be finite")

    normalized_fixed = {}
    if fixed_axis_values is not None:
        if not isinstance(fixed_axis_values, Mapping):
            raise TypeError("fixed_axis_values must be a mapping")
        for raw_key, raw_value in fixed_axis_values.items():
            key = tuple(map(str, raw_key))
            if len(key) != 2:
                raise ValueError("fixed sweep-axis keys must contain two names")
            if key in (x_axis_key, y_axis_key):
                raise ValueError("X and Y sweep axes cannot also be fixed")
            if key not in axis_keys:
                raise ValueError(f"fixed AWG sweep axis {key!r} is not present")
            value = float(raw_value)
            if not np.isfinite(value):
                raise ValueError("fixed AWG sweep values must be finite")
            normalized_fixed[key] = value

    if source is None:
        source = AwgSweepMapSource(
            sweep_axes=axes,
            sweep_points=coordinates,
            iq_values=iq,
            full_scale_mv=full_scale_mv,
            value_unit=str(value_unit),
            measurement_mode=str(measurement_mode),
            sample_rate_hz=float(
                getattr(ddr_result, "sample_rate_hz", 1_000_000.0)
            ),
        )

    point_iq = iq.astype(np.float64, copy=False).mean(axis=(1, 2))
    if not np.all(np.isfinite(point_iq)):
        raise ValueError("AWG sweep I/Q contains NaN or infinity")
    display_i, display_q, display_scale = scale_iq_for_display(
        point_iq[:, 0],
        point_iq[:, 1],
        value_unit,
    )
    point_iq = np.column_stack((display_i, display_q))

    selected_points = np.ones(coordinates.shape[0], dtype=bool)
    for key, value in normalized_fixed.items():
        column = axis_keys.index(key)
        column_values = coordinates[:, column]
        matching = np.isclose(
            column_values,
            value,
            rtol=1.0e-10,
            atol=1.0e-12,
        )
        if not np.any(matching):
            raise ValueError(
                f"fixed value {value:g} is not present on sweep axis {key!r}"
            )
        selected_points &= matching
    if not np.any(selected_points):
        raise ValueError("fixed sweep-axis values select no acquired points")
    coordinates = coordinates[selected_points]
    point_iq = point_iq[selected_points]

    x_coordinates, x_unit = _axis_display_values(
        coordinates[:, x_column],
        axes[x_column],
        full_scale_mv,
    )
    y_coordinates, y_unit = _axis_display_values(
        coordinates[:, y_column],
        axes[y_column],
        full_scale_mv,
    )
    x_values = np.unique(x_coordinates)
    y_values = np.unique(y_coordinates)
    i_sum = np.zeros((y_values.size, x_values.size), dtype=np.float64)
    q_sum = np.zeros_like(i_sum)
    counts = np.zeros_like(i_sum, dtype=np.int64)

    for point_index, (x_value, y_value) in enumerate(
        zip(x_coordinates, y_coordinates)
    ):
        x_index = int(np.argmin(np.abs(x_values - x_value)))
        y_index = int(np.argmin(np.abs(y_values - y_value)))
        i_sum[y_index, x_index] += point_iq[point_index, 0]
        q_sum[y_index, x_index] += point_iq[point_index, 1]
        counts[y_index, x_index] += 1

    if np.any(counts == 0):
        raise ValueError("AWG result does not cover the selected X/Y grid")
    if not np.all(counts == counts.flat[0]):
        raise ValueError(
            "AWG result has an uneven number of points per selected X/Y cell"
        )
    i_mean = i_sum / counts
    q_mean = q_sum / counts
    magnitude = np.hypot(i_mean, q_mean)
    angle_deg = np.degrees(np.arctan2(q_mean, i_mean))
    averaged_axis_labels = tuple(
        sweep_axis_label(axis)
        for index, axis in enumerate(axes)
        if (
            index not in (x_column, y_column)
            and axis_keys[index] not in normalized_fixed
        )
    )
    ordered_fixed_axis_values = tuple(
        (axis_keys[index], normalized_fixed[axis_keys[index]])
        for index in range(len(axes))
        if axis_keys[index] in normalized_fixed
    )
    fixed_axis_labels = []
    for key, native_value in ordered_fixed_axis_values:
        index = axis_keys.index(key)
        display_value, unit = _axis_display_values(
            np.asarray([native_value], dtype=np.float64),
            axes[index],
            full_scale_mv,
        )
        fixed_axis_labels.append(
            f"{sweep_axis_label(axes[index])} = "
            f"{float(display_value[0]):.9g} {unit}"
        )

    return AwgSweepMapResult(
        x_values=x_values,
        y_values=y_values,
        i_mean=i_mean,
        q_mean=q_mean,
        magnitude=magnitude,
        angle_deg=angle_deg,
        x_axis_key=x_axis_key,
        y_axis_key=y_axis_key,
        x_axis_label=sweep_axis_label(axes[x_column]),
        y_axis_label=sweep_axis_label(axes[y_column]),
        x_unit=x_unit,
        y_unit=y_unit,
        value_unit=display_scale.unit,
        base_value_unit=display_scale.base_unit,
        display_scale=display_scale.factor,
        measurement_mode=str(measurement_mode),
        repetition_count=int(iq.shape[1]),
        samples_per_trace=int(iq.shape[2]),
        averaged_axis_labels=averaged_axis_labels,
        source_points_per_cell=int(counts.flat[0]),
        sample_rate_hz=float(
            getattr(ddr_result, "sample_rate_hz", 1_000_000.0)
        ),
        fixed_axis_values=ordered_fixed_axis_values,
        fixed_axis_labels=tuple(fixed_axis_labels),
        source=source,
    )


def reduce_awg_sweep_source(
    source: AwgSweepMapSource,
    *,
    x_axis_key: SweepAxisKey,
    y_axis_key: SweepAxisKey,
    fixed_axis_values: Optional[Mapping[SweepAxisKey, float]] = None,
) -> AwgSweepMapResult:
    """Reproject one retained Cartesian acquisition without reacquiring it."""
    ddr_result = SimpleNamespace(
        sweep_axes=source.sweep_axes,
        sweep_points=source.sweep_points,
        iq=source.iq_values,
        sample_rate_hz=source.sample_rate_hz,
    )
    result = reduce_awg_sweep_map(
        ddr_result,
        x_axis_key=x_axis_key,
        y_axis_key=y_axis_key,
        full_scale_mv=source.full_scale_mv,
        iq_values=source.iq_values,
        value_unit=source.value_unit,
        measurement_mode=source.measurement_mode,
        fixed_axis_values=fixed_axis_values,
        source=source,
    )
    return replace(
        result,
        source_label=source.source_label,
        database_path=source.database_path,
        run_id=source.run_id,
    )


if pg is not None:

    class AwgSweepMapPlotWidget(QtWidgets.QWidget):
        """Four synchronized image plots for I, Q, magnitude, and angle."""

        selection_changed = QtCore.pyqtSignal(object)

        _PLOT_SPECS = (
            ("i", "I", "CET-D1"),
            ("q", "Q", "CET-D1"),
            ("magnitude", "Magnitude", "viridis"),
            ("angle", "Angle", "CET-C7"),
        )

        def __init__(self, parent=None):
            super().__init__(parent)
            self._result: Optional[AwgSweepMapResult] = None
            self._source: Optional[AwgSweepMapSource] = None
            self._updating_axis_controls = False
            self._current_axis_keys: Optional[
                Tuple[SweepAxisKey, SweepAxisKey]
            ] = None
            self._preferred_axis_keys: Optional[
                Tuple[SweepAxisKey, SweepAxisKey]
            ] = None
            self._slice_selections = {}
            self._preferred_slice_selections = {}

            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            axis_layout = QtWidgets.QHBoxLayout()
            axis_layout.setContentsMargins(4, 2, 4, 2)
            axis_layout.addWidget(QtWidgets.QLabel("Plot axes:", self))
            axis_layout.addWidget(QtWidgets.QLabel("X", self))
            self.axis_x = QtWidgets.QComboBox(self)
            self.axis_x.setSizeAdjustPolicy(
                QtWidgets.QComboBox.AdjustToContents
            )
            axis_layout.addWidget(self.axis_x, 1)
            axis_layout.addWidget(QtWidgets.QLabel("Y", self))
            self.axis_y = QtWidgets.QComboBox(self)
            self.axis_y.setSizeAdjustPolicy(
                QtWidgets.QComboBox.AdjustToContents
            )
            axis_layout.addWidget(self.axis_y, 1)
            layout.addLayout(axis_layout)

            self.slice_scroll = QtWidgets.QScrollArea(self)
            self.slice_scroll.setWidgetResizable(True)
            self.slice_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
            self.slice_scroll.setVerticalScrollBarPolicy(
                QtCore.Qt.ScrollBarAlwaysOff
            )
            self.slice_scroll.setHorizontalScrollBarPolicy(
                QtCore.Qt.ScrollBarAsNeeded
            )
            self.slice_scroll.setMaximumHeight(62)
            self.slice_widget = QtWidgets.QWidget(self.slice_scroll)
            self.slice_layout = QtWidgets.QHBoxLayout(self.slice_widget)
            self.slice_layout.setContentsMargins(4, 0, 4, 2)
            self.slice_layout.setSpacing(8)
            self.slice_scroll.setWidget(self.slice_widget)
            self.slice_controls = {}
            self.slice_scroll.setVisible(False)
            layout.addWidget(self.slice_scroll)

            self.axis_x.currentIndexChanged.connect(
                lambda _index: self._on_axis_changed("x")
            )
            self.axis_y.currentIndexChanged.connect(
                lambda _index: self._on_axis_changed("y")
            )

            selector_layout = QtWidgets.QHBoxLayout()
            selector_layout.setContentsMargins(4, 2, 4, 2)
            selector_layout.addWidget(QtWidgets.QLabel("Displayed data:", self))
            self.data_selectors = {}
            for key, title, _color_map in self._PLOT_SPECS:
                selector = QtWidgets.QCheckBox(title, self)
                selector.setChecked(True)
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
            plot_grid = QtWidgets.QGridLayout()
            plot_grid.setContentsMargins(0, 0, 0, 0)
            plot_grid.setSpacing(4)
            layout.addLayout(plot_grid, 1)
            self.plot_grid = plot_grid

            self.plots = {}
            self.images = {}
            self.plot_cells = {}
            self.range_controls = {}
            self.color_bars = {}
            self.color_maps = {}
            self._mouse_connections = []
            for index, (key, title, color_map) in enumerate(self._PLOT_SPECS):
                cell = QtWidgets.QWidget(self)
                cell_layout = QtWidgets.QVBoxLayout(cell)
                cell_layout.setContentsMargins(0, 0, 0, 0)
                cell_layout.setSpacing(2)
                defaults = DEFAULT_AWG_SWEEP_COLOR_RANGES[key]
                unit = "deg" if key == "angle" else "ADC units"
                range_control = ColorRangeControl(
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
                plot.setLabel("bottom", "X sweep", units="mV")
                plot.setLabel("left", "Y sweep", units="mV")
                plot.showGrid(x=True, y=True, alpha=0.18)
                selected_map = self._color_map(color_map)
                image.setColorMap(selected_map)
                color_bar = attach_color_bar(
                    plot,
                    image,
                    selected_map,
                    unit=unit,
                    levels=(
                        defaults["minimum"],
                        defaults["maximum"],
                    ),
                    range_control=range_control,
                )
                cell_layout.addWidget(range_control)
                cell_layout.addWidget(plot, 1)
                plot_grid.addWidget(cell, index // 2, index % 2)
                self.plot_cells[key] = cell
                self.plots[key] = plot
                self.images[key] = image
                self.range_controls[key] = range_control
                self.color_bars[key] = color_bar
                self.color_maps[key] = selected_map
                range_control.levels_changed.connect(
                    lambda minimum, maximum, name=key: self._set_color_levels(
                        name,
                        minimum,
                        maximum,
                    )
                )
                slot = lambda event, source=plot: self._mouse_moved(
                    event, source
                )
                plot.scene().sigMouseMoved.connect(slot)
                self._mouse_connections.append(
                    (plot.scene().sigMouseMoved, slot)
                )

            self.hover_status = QtWidgets.QLabel(
                "Run an experiment with at least two AWG sweep variables",
                self,
            )
            self.hover_status.setWordWrap(True)
            self.hover_status.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse
            )
            layout.addWidget(self.hover_status)

        @staticmethod
        def _setting_axis_key(value: Any) -> Optional[SweepAxisKey]:
            if value is None:
                return None
            if isinstance(value, Mapping):
                key = (
                    str(value.get("output_name", "")),
                    str(value.get("segment_name", "")),
                )
            elif (
                isinstance(value, Sequence)
                and not isinstance(value, (str, bytes))
                and len(value) == 2
            ):
                key = str(value[0]), str(value[1])
            else:
                raise TypeError("AWG plot axis must identify output and segment")
            if not all(key):
                raise ValueError("AWG plot axis names cannot be empty")
            return key

        def _selected_axis_keys(
            self,
        ) -> Optional[Tuple[SweepAxisKey, SweepAxisKey]]:
            if self.axis_x.count() < 2 or self.axis_y.count() < 2:
                return None
            x_key = self._setting_axis_key(self.axis_x.currentData())
            y_key = self._setting_axis_key(self.axis_y.currentData())
            if x_key is None or y_key is None or x_key == y_key:
                return None
            return x_key, y_key

        def _axis_index(self, combo: QtWidgets.QComboBox, key) -> int:
            for index in range(combo.count()):
                if self._setting_axis_key(combo.itemData(index)) == key:
                    return index
            return -1

        def _populate_axis_controls(
            self,
            default_axes: Tuple[SweepAxisKey, SweepAxisKey],
        ) -> None:
            if self._source is None:
                return
            axes = tuple(self._source.sweep_axes)
            keys = tuple(sweep_axis_key(axis) for axis in axes)
            desired = self._preferred_axis_keys or default_axes
            if (
                desired[0] not in keys
                or desired[1] not in keys
                or desired[0] == desired[1]
            ):
                desired = (keys[0], keys[1])

            self._updating_axis_controls = True
            try:
                with QtCore.QSignalBlocker(
                    self.axis_x
                ), QtCore.QSignalBlocker(self.axis_y):
                    self.axis_x.clear()
                    self.axis_y.clear()
                    for axis, key in zip(axes, keys):
                        label = sweep_axis_label(axis)
                        self.axis_x.addItem(label, key)
                        self.axis_y.addItem(label, key)
                    self.axis_x.setCurrentIndex(keys.index(desired[0]))
                    self.axis_y.setCurrentIndex(keys.index(desired[1]))
                self._current_axis_keys = desired
                self._preferred_axis_keys = desired
                self._rebuild_slice_controls()
            finally:
                self._updating_axis_controls = False

        def _clear_slice_controls(self) -> None:
            while self.slice_layout.count():
                item = self.slice_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            self.slice_controls.clear()

        def _rebuild_slice_controls(self) -> None:
            if self._source is None:
                self._clear_slice_controls()
                self.slice_scroll.setVisible(False)
                return
            selected = self._selected_axis_keys()
            if selected is None:
                return
            for key, combo in self.slice_controls.items():
                self._slice_selections[key] = combo.currentData()
            self._clear_slice_controls()

            coordinates = np.asarray(
                self._source.sweep_points,
                dtype=np.float64,
            )
            for column, axis in enumerate(self._source.sweep_axes):
                key = sweep_axis_key(axis)
                if key in selected:
                    continue
                label = QtWidgets.QLabel(sweep_axis_label(axis), self.slice_widget)
                combo = QtWidgets.QComboBox(self.slice_widget)
                combo.addItem("Average all", None)
                native_values = np.unique(coordinates[:, column])
                display_values, unit = _axis_display_values(
                    native_values,
                    axis,
                    self._source.full_scale_mv,
                )
                for native_value, display_value in zip(
                    native_values,
                    display_values,
                ):
                    combo.addItem(
                        f"{float(display_value):.9g} {unit}",
                        float(native_value),
                    )
                desired = self._slice_selections.get(
                    key,
                    self._preferred_slice_selections.get(key),
                )
                if desired is not None:
                    for index in range(1, combo.count()):
                        if np.isclose(
                            float(combo.itemData(index)),
                            float(desired),
                            rtol=1.0e-10,
                            atol=1.0e-12,
                        ):
                            combo.setCurrentIndex(index)
                            break
                combo.currentIndexChanged.connect(
                    lambda _index, axis_key=key: self._on_slice_changed(
                        axis_key
                    )
                )
                self.slice_layout.addWidget(label)
                self.slice_layout.addWidget(combo)
                self.slice_controls[key] = combo
            self.slice_layout.addStretch(1)
            self.slice_scroll.setVisible(bool(self.slice_controls))

        def _on_axis_changed(self, changed_axis: str) -> None:
            if self._updating_axis_controls:
                return
            x_key = self._setting_axis_key(self.axis_x.currentData())
            y_key = self._setting_axis_key(self.axis_y.currentData())
            if x_key is None or y_key is None:
                return
            if x_key == y_key:
                old_axes = self._current_axis_keys
                replacement = None
                if old_axes is not None:
                    replacement = old_axes[0 if changed_axis == "x" else 1]
                    if replacement == x_key:
                        replacement = None
                target = self.axis_y if changed_axis == "x" else self.axis_x
                if replacement is None:
                    replacement = next(
                        self._setting_axis_key(target.itemData(index))
                        for index in range(target.count())
                        if self._setting_axis_key(target.itemData(index)) != x_key
                    )
                with QtCore.QSignalBlocker(target):
                    target.setCurrentIndex(self._axis_index(target, replacement))
                x_key = self._setting_axis_key(self.axis_x.currentData())
                y_key = self._setting_axis_key(self.axis_y.currentData())
            self._current_axis_keys = (x_key, y_key)
            self._preferred_axis_keys = (x_key, y_key)
            self._rebuild_slice_controls()
            self._reproject()

        def _on_slice_changed(self, key: SweepAxisKey) -> None:
            if self._updating_axis_controls:
                return
            combo = self.slice_controls.get(key)
            if combo is None:
                return
            self._slice_selections[key] = combo.currentData()
            self._preferred_slice_selections[key] = combo.currentData()
            self._reproject()

        def _reproject(self, *, emit: bool = True) -> None:
            if self._source is None:
                return
            selected = self._selected_axis_keys()
            if selected is None:
                return
            fixed = {
                key: float(combo.currentData())
                for key, combo in self.slice_controls.items()
                if combo.currentData() is not None
            }
            try:
                result = reduce_awg_sweep_source(
                    self._source,
                    x_axis_key=selected[0],
                    y_axis_key=selected[1],
                    fixed_axis_values=fixed,
                )
            except (TypeError, ValueError) as exc:
                self.hover_status.setText(f"Cannot update AWG map: {exc}")
                return
            self._display_result(result)
            if emit:
                self.selection_changed.emit(result)

        def axis_selection_settings(self) -> dict:
            selected = self._selected_axis_keys() or self._preferred_axis_keys
            if selected is None:
                return {}
            settings = {
                "x_axis": {
                    "output_name": selected[0][0],
                    "segment_name": selected[0][1],
                },
                "y_axis": {
                    "output_name": selected[1][0],
                    "segment_name": selected[1][1],
                },
                "slice_axes": [],
            }
            if self.slice_controls:
                slice_values = {
                    key: combo.currentData()
                    for key, combo in self.slice_controls.items()
                }
            else:
                slice_values = dict(self._preferred_slice_selections)
            for key, value in slice_values.items():
                entry = {
                    "output_name": key[0],
                    "segment_name": key[1],
                    "mode": "average" if value is None else "value",
                }
                if value is not None:
                    entry["value"] = float(value)
                settings["slice_axes"].append(entry)
            return settings

        def load_axis_selection_settings(
            self,
            settings: Mapping[str, Any],
        ) -> None:
            if not isinstance(settings, Mapping):
                raise TypeError("AWG plot axis settings must be an object")
            x_key = self._setting_axis_key(settings.get("x_axis"))
            y_key = self._setting_axis_key(settings.get("y_axis"))
            if x_key is not None and y_key is not None:
                if x_key == y_key:
                    raise ValueError("AWG plot X and Y axes must differ")
                self._preferred_axis_keys = (x_key, y_key)
            raw_slices = settings.get("slice_axes", ())
            if not isinstance(raw_slices, Sequence) or isinstance(
                raw_slices,
                (str, bytes),
            ):
                raise TypeError("AWG plot slice_axes must be an array")
            preferred_slices = {}
            for raw_slice in raw_slices:
                if not isinstance(raw_slice, Mapping):
                    raise TypeError("each AWG plot slice must be an object")
                key = self._setting_axis_key(raw_slice)
                mode = str(raw_slice.get("mode", "average")).lower()
                if mode == "average":
                    preferred_slices[key] = None
                elif mode == "value":
                    value = float(raw_slice["value"])
                    if not np.isfinite(value):
                        raise ValueError("AWG plot slice values must be finite")
                    preferred_slices[key] = value
                else:
                    raise ValueError(
                        "AWG plot slice mode must be 'average' or 'value'"
                    )
            self._preferred_slice_selections = preferred_slices
            self._slice_selections.update(preferred_slices)
            if self._source is not None and self._result is not None:
                self._populate_axis_controls(
                    (self._result.x_axis_key, self._result.y_axis_key)
                )
                self._reproject()

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
            if checked and self._result is not None:
                self.plots[name].enableAutoRange(x=True, y=True)

        def _reflow_visible_plots(self) -> None:
            visible = [
                key
                for key, _title, _color_map in self._PLOT_SPECS
                if self.data_selectors[key].isChecked()
            ]
            for cell in self.plot_cells.values():
                self.plot_grid.removeWidget(cell)
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
            visible = set(normalize_awg_sweep_visible_data(values))
            for key, selector in self.data_selectors.items():
                with QtCore.QSignalBlocker(selector):
                    selector.setChecked(key in visible)
                self.plot_cells[key].setVisible(key in visible)
            self._reflow_visible_plots()
            self.fit_view()

        @staticmethod
        def _color_map(name: str):
            try:
                return pg.colormap.get(name)
            except (FileNotFoundError, KeyError):
                return pg.colormap.get("viridis")

        def _set_color_levels(
            self,
            name: str,
            minimum: float,
            maximum: float,
        ) -> None:
            color_bar = self.color_bars[name]
            if color_bar is None:
                self.images[name].setLevels((minimum, maximum))
                return
            color_bar.setLevels((minimum, maximum))

        def color_range_settings(self) -> dict:
            return {
                name: control.settings_dict()
                for name, control in self.range_controls.items()
            }

        def load_color_range_settings(
            self,
            settings: Mapping[str, Any],
        ) -> None:
            normalized = normalize_awg_sweep_color_ranges(settings)
            for name, control in self.range_controls.items():
                control.load_settings(normalized[name])

        @staticmethod
        def _axis_edges(values: np.ndarray) -> Tuple[float, float]:
            if values.size == 1:
                return float(values[0] - 0.5), float(values[0] + 0.5)
            spacing = float(np.median(np.diff(values)))
            return (
                float(values[0] - spacing / 2.0),
                float(values[-1] + spacing / 2.0),
            )

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
        def _symmetric_levels(values: np.ndarray) -> Tuple[float, float]:
            limit = float(np.nanmax(np.abs(values)))
            if np.isclose(limit, 0.0):
                limit = 1.0
            return -limit, limit

        def set_result(self, result: AwgSweepMapResult) -> None:
            current_axes = self._selected_axis_keys()
            if current_axes is not None:
                self._preferred_axis_keys = current_axes
            self._source = result.source
            if self._source is not None and len(self._source.sweep_axes) >= 2:
                for key, value in result.fixed_axis_values:
                    self._slice_selections.setdefault(key, value)
                self._populate_axis_controls(
                    (result.x_axis_key, result.y_axis_key)
                )
                self._reproject(emit=False)
                return
            self._display_result(result)

        def _display_result(self, result: AwgSweepMapResult) -> None:
            self._result = result
            for plot in self.plots.values():
                plot.setLabel(
                    "bottom",
                    result.x_axis_label,
                    units=result.x_unit,
                )
                plot.setLabel(
                    "left",
                    result.y_axis_label,
                    units=result.y_unit,
                )
            self.plots["i"].setTitle(f"I [{result.value_unit}]")
            self.plots["q"].setTitle(f"Q [{result.value_unit}]")
            self.plots["magnitude"].setTitle(
                f"Magnitude [{result.value_unit}]"
            )
            self.plots["angle"].setTitle("Angle [deg]")

            x_low, x_high = self._axis_edges(result.x_values)
            y_low, y_high = self._axis_edges(result.y_values)
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
                "angle": result.angle_deg,
            }
            levels = {
                "i": self._symmetric_levels(result.i_mean),
                "q": self._symmetric_levels(result.q_mean),
                "magnitude": self._levels(result.magnitude),
                "angle": self._levels(result.angle_deg),
            }
            for key, values in image_values.items():
                self.images[key].setImage(
                    values,
                    autoLevels=False,
                )
                unit = "deg" if key == "angle" else result.value_unit
                self.range_controls[key].set_unit(unit)
                self.range_controls[key].set_data_levels(*levels[key])
                color_bar = self.color_bars[key]
                if color_bar is not None:
                    color_bar.setLabel("right", text=unit)
                self.images[key].setRect(rect)
            self.fit_view()

            averaged = (
                "none"
                if not result.averaged_axis_labels
                else ", ".join(result.averaged_axis_labels)
            )
            fixed = (
                "none"
                if not result.fixed_axis_labels
                else ", ".join(result.fixed_axis_labels)
            )
            self.hover_status.setText(
                f"{result.repetition_count} repetitions x "
                f"{result.samples_per_trace} FIR samples; "
                f"display {result.value_unit} "
                f"({result.display_scale:g} x {result.base_value_unit}); "
                f"fixed sweep axes: {fixed}; "
                f"averaged sweep axes: {averaged}"
            )

        def fit_view(self) -> None:
            for plot in self.plots.values():
                plot.enableAutoRange(x=True, y=True)

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
                np.argmin(np.abs(self._result.x_values - point.x()))
            )
            y_index = int(
                np.argmin(np.abs(self._result.y_values - point.y()))
            )
            self.hover_status.setText(
                f"{self._result.x_axis_label} "
                f"{self._result.x_values[x_index]:.6g} "
                f"{self._result.x_unit} | "
                f"{self._result.y_axis_label} "
                f"{self._result.y_values[y_index]:.6g} "
                f"{self._result.y_unit} | "
                f"I {self._result.i_mean[y_index, x_index]:.6g} "
                f"{self._result.value_unit} | "
                f"Q {self._result.q_mean[y_index, x_index]:.6g} "
                f"{self._result.value_unit} | "
                f"Mag {self._result.magnitude[y_index, x_index]:.6g} "
                f"{self._result.value_unit} | "
                f"Angle {self._result.angle_deg[y_index, x_index]:.6g} deg"
            )

else:

    class AwgSweepMapPlotWidget(QtWidgets.QLabel):
        """Dependency error displayed when pyqtgraph is unavailable."""

        def __init__(self, parent=None):
            super().__init__(
                "pyqtgraph is required for AWG two-dimensional sweep plots",
                parent,
            )
            self.setAlignment(QtCore.Qt.AlignCenter)
            self._color_ranges = normalize_awg_sweep_color_ranges(None)
            self._visible_data = DEFAULT_AWG_SWEEP_VISIBLE_DATA
            self._axis_settings = {}
            self._result = None

        def set_result(self, result: AwgSweepMapResult) -> None:
            self._result = result

        def axis_selection_settings(self) -> dict:
            return dict(self._axis_settings)

        def load_axis_selection_settings(
            self,
            settings: Mapping[str, Any],
        ) -> None:
            self._axis_settings = dict(settings)

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
            self._color_ranges = normalize_awg_sweep_color_ranges(settings)

        def visible_data(self) -> Tuple[str, ...]:
            return self._visible_data

        def load_visible_data(self, values: Any) -> None:
            self._visible_data = normalize_awg_sweep_visible_data(values)


__all__ = [
    "AwgSweepMapLoadWorker",
    "AwgSweepMapPlotWidget",
    "AwgSweepMapResult",
    "AwgSweepMapSource",
    "AwgSweepRunSelector",
    "AwgSweepRunSummary",
    "AWG_SWEEP_DATA_KEYS",
    "DEFAULT_AWG_SWEEP_DB_PATH",
    "DEFAULT_AWG_SWEEP_COLOR_RANGES",
    "DEFAULT_AWG_SWEEP_VISIBLE_DATA",
    "SweepAxisKey",
    "awg_sweep_result_from_stored_arrays",
    "list_awg_sweep_runs",
    "load_awg_sweep_run",
    "normalize_awg_sweep_color_ranges",
    "normalize_awg_sweep_visible_data",
    "reduce_awg_sweep_map",
    "reduce_awg_sweep_source",
    "sweep_axis_key",
    "sweep_axis_label",
]
