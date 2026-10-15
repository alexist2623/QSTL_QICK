"""Execute a QICK fine-tune program and persist its IQ trace with QCoDeS.

QCoDeS and the QICK Pyro client are imported only when an experiment runs, so
the waveform editor remains usable on machines without laboratory packages.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass, replace
from datetime import datetime, timezone
from itertools import product
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple

import numpy as np
try:
    from .fir_ddr_profile import result_iq_in_input_units
except ImportError:
    from fir_ddr_profile import result_iq_in_input_units


ProgressCallback = Callable[[int, str], None]
ExperimentEventCallback = Callable[[str, str, str], None]
CancellationCheck = Callable[[], None]
DEFAULT_QCODES_BATCH_ROWS = 8192
QCODES_STAGING_ENV = "QSTL_QCODES_STAGING_DIR"
# Legacy packed-IQ parameter used by runs written before split trace storage.
IQ_TRACE_PARAMETER = "iq_trace"
I_TRACE_PARAMETER = "i_trace"
Q_TRACE_PARAMETER = "q_trace"
I_MEAN_PARAMETER = "i_mean"
Q_MEAN_PARAMETER = "q_mean"
SAMPLE_INDEX_PARAMETER = "sample_index"
IQ_STORAGE_FULL_TRACES = "full_traces"
IQ_STORAGE_MEAN_IQ = "mean_iq"
IQ_STORAGE_MODES = (
    IQ_STORAGE_FULL_TRACES,
    IQ_STORAGE_MEAN_IQ,
)
DEFAULT_IQ_STORAGE_MODE = IQ_STORAGE_FULL_TRACES
AWG_METADATA_MODE_PARAMETRIC = "parametric"
AWG_METADATA_MODE_EXPANDED = "expanded"
AWG_METADATA_MODES = (
    AWG_METADATA_MODE_PARAMETRIC,
    AWG_METADATA_MODE_EXPANDED,
)
DEFAULT_AWG_METADATA_MODE = AWG_METADATA_MODE_PARAMETRIC
COMPILE_VALIDATION_BOUNDARY = "boundary"
COMPILE_VALIDATION_FULL = "full"
COMPILE_VALIDATION_MODES = (
    COMPILE_VALIDATION_BOUNDARY,
    COMPILE_VALIDATION_FULL,
)
DEFAULT_COMPILE_VALIDATION_MODE = COMPILE_VALIDATION_FULL


class ExperimentCancelled(RuntimeError):
    """Raised when the user requests cooperative experiment cancellation."""


def _check_cancel(cancel_check: Optional[CancellationCheck]) -> None:
    if cancel_check is not None:
        cancel_check()

try:
    from .dc_waveform_core import (
        DEFAULT_QICK_FULL_SCALE_MV,
        DEFAULT_QICK_TPROC_MHZ,
        QickDdrReadoutSpec,
        QickRfPulseSpec,
        QickRfSoftwareSweepAxisSpec,
        adc_iq_to_voltage,
        dc_iq_to_current,
    )
    from .dc_voltage_calibration import load_dc_voltage_calibration
    from .fir_ddr_profile import resolve_fir_ddr_profile
    from .power_calibration import (
        CalibrationDatabase,
        MAX_DMEM_GAIN_ENTRIES,
    )
except ImportError:
    from dc_waveform_core import (
        DEFAULT_QICK_FULL_SCALE_MV,
        DEFAULT_QICK_TPROC_MHZ,
        QickDdrReadoutSpec,
        QickRfPulseSpec,
        QickRfSoftwareSweepAxisSpec,
        adc_iq_to_voltage,
        dc_iq_to_current,
    )
    from dc_voltage_calibration import load_dc_voltage_calibration
    from fir_ddr_profile import resolve_fir_ddr_profile
    from power_calibration import CalibrationDatabase, MAX_DMEM_GAIN_ENTRIES


def _runtime_types():
    try:
        from .qick_fine_tune_sweep import (
            DdrFirReadoutConfig,
            RfPulseConfig,
            cycles_from_us,
        )
    except ImportError:
        from qick_fine_tune_sweep import (
            DdrFirReadoutConfig,
            RfPulseConfig,
            cycles_from_us,
        )
    return DdrFirReadoutConfig, RfPulseConfig, cycles_from_us


def _runtime_readout_type():
    try:
        from .qick_fine_tune_sweep import ReadoutConfig
    except ImportError:
        from qick_fine_tune_sweep import ReadoutConfig
    return ReadoutConfig


def _resolve_tproc_mhz(soccfg, tproc_mhz: Optional[float]) -> float:
    value = (
        soccfg["tprocs"][0]["f_time"]
        if tproc_mhz is None
        else tproc_mhz
    )
    value = float(value)
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError("tProcessor clock must be positive and finite")
    return value


@dataclass(frozen=True)
class QickConnectionConfig:
    """Pyro nameserver location used to obtain ``soc`` and ``soccfg``."""

    host: str = "192.168.2.99"
    ns_port: int = 8888
    proxy_name: str = "myqick"

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise ValueError("QICK host/IP must not be empty")
        if isinstance(self.ns_port, bool) or not 1 <= int(self.ns_port) <= 65535:
            raise ValueError("QICK nameserver port must be in [1, 65535]")
        if not self.proxy_name.strip():
            raise ValueError("QICK proxy name must not be empty")


@dataclass(frozen=True)
class QcodesRunConfig:
    """QCoDeS database and experiment naming settings."""

    database_path: str
    experiment_name: str = "QICK pulse experiment"
    sample_name: str = "PulseGenerator"
    notes: str = ""
    sample_rate_hz: float = 1_000_000.0

    def __post_init__(self) -> None:
        if not str(self.database_path).strip():
            raise ValueError("QCoDeS database path must not be empty")
        if not self.experiment_name.strip():
            raise ValueError("QCoDeS experiment name must not be empty")
        if not self.sample_name.strip():
            raise ValueError("QCoDeS sample name must not be empty")
        if not np.isfinite(self.sample_rate_hz) or self.sample_rate_hz <= 0.0:
            raise ValueError("sample_rate_hz must be positive and finite")

    @property
    def resolved_database_path(self) -> Path:
        path = Path(self.database_path).expanduser()
        if path.suffix.lower() != ".db":
            path = path.with_suffix(".db")
        return path.resolve()


@dataclass
class StoredQickExperiment:
    """Objects and identifiers produced by one hardware/database run."""

    run_id: int
    guid: str
    database_path: Path
    row_count: int
    dataset: Any
    program: Any
    ddr_result: Any
    rf_settings: Mapping[str, Any]
    iq_storage_mode: str = DEFAULT_IQ_STORAGE_MODE

    def detach_dataset(self) -> "StoredQickExperiment":
        """Close and discard the QCoDeS connection before crossing threads."""

        dataset = self.dataset
        if dataset is None:
            return self
        try:
            connection = getattr(dataset, "conn", None)
            close = getattr(connection, "close", None)
            if callable(close):
                close()
        finally:
            self.dataset = None
        return self


def _json_ready(value: Any) -> Any:
    """Convert NumPy, dataclass, and QICK objects to strict JSON values."""
    if is_dataclass(value):
        return _json_ready(asdict(value))
    if isinstance(value, np.ndarray):
        return _json_ready(value.tolist())
    if isinstance(value, np.generic):
        return _json_ready(value.item())
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_ready(item) for item in value]
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if hasattr(value, "__dict__"):
        return _json_ready(vars(value))
    return repr(value)


def _json_text(value: Any) -> str:
    return json.dumps(
        _json_ready(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )


def _emit_progress(
    callback: Optional[ProgressCallback],
    percent: int,
    message: str,
) -> None:
    if callback is not None:
        callback(max(0, min(100, int(percent))), str(message))


def _emit_experiment_event(
    callback: Optional[ExperimentEventCallback],
    key: str,
    state: str,
    message: str,
) -> None:
    if callback is not None:
        callback(str(key), str(state), str(message))


def normalize_awg_metadata_mode(value: Any) -> str:
    """Return a supported AWG waveform metadata storage mode."""
    mode = str(value or DEFAULT_AWG_METADATA_MODE).strip().lower()
    if mode not in AWG_METADATA_MODES:
        raise ValueError(
            f"AWG waveform metadata mode must be one of {AWG_METADATA_MODES}"
        )
    return mode


def normalize_iq_storage_mode(value: Any) -> str:
    """Return a supported QCoDeS I/Q storage mode."""
    mode = str(value or DEFAULT_IQ_STORAGE_MODE).strip().lower()
    if mode not in IQ_STORAGE_MODES:
        raise ValueError(f"I/Q storage mode must be one of {IQ_STORAGE_MODES}")
    return mode


def normalize_compile_validation_mode(value: Any) -> str:
    """Return a supported tProcessor compile validation mode."""
    mode = str(value or DEFAULT_COMPILE_VALIDATION_MODE).strip().lower()
    if mode not in COMPILE_VALIDATION_MODES:
        raise ValueError(
            "compile validation mode must be one of "
            f"{COMPILE_VALIDATION_MODES}"
        )
    return mode


def build_awg_waveform_recipe(
    sequence: Any,
    *,
    fabric_mhz: float,
    full_scale_mv: float,
) -> Mapping[str, Any]:
    """Serialize the base waveform and sweep rules without expanding points."""
    fabric_mhz = float(fabric_mhz)
    full_scale_mv = float(full_scale_mv)
    if not np.isfinite(fabric_mhz) or fabric_mhz <= 0.0:
        raise ValueError("fabric_mhz must be positive and finite")
    if not np.isfinite(full_scale_mv) or full_scale_mv <= 0.0:
        raise ValueError("full_scale_mv must be positive and finite")

    output_names = tuple(str(name) for name in sequence.output_names)
    sweep_axes = []
    for axis in sequence.sweep_axes:
        axis_data = dict(_json_ready(axis))
        axis_data.update({
            "axis_kind": str(getattr(axis, "axis_kind", "amplitude")),
            "output_name": str(getattr(axis, "output_name", "")),
            "coordinate_unit": str(getattr(axis, "coordinate_unit", "")),
        })
        sweep_axes.append(axis_data)

    compensation = getattr(sequence, "bias_t_compensation", None)
    compensation_data = None
    if compensation is not None:
        compensation_data = dict(_json_ready(compensation))
        compensation_data["kind"] = (
            "filter" if hasattr(compensation, "tau_cycles") else "dc"
        )

    sweep_shape = [int(axis.count) for axis in sequence.sweep_axes]
    point_count = int(np.prod(sweep_shape or [1], dtype=np.int64))
    return {
        "schema": "qick-awg-waveform-recipe-v1",
        "metadata_mode": AWG_METADATA_MODE_PARAMETRIC,
        "output_names": list(output_names),
        "segments": _json_ready(sequence.segments),
        "cross_capacitance": np.asarray(
            sequence.cross_capacitance,
            dtype=float,
        ).tolist(),
        "bias_t_compensation": compensation_data,
        "sweep_axes": sweep_axes,
        "sweep_shape": sweep_shape,
        "point_count": point_count,
        "fabric_mhz": fabric_mhz,
        "full_scale_mv": full_scale_mv,
        "output_full_scales_mv": getattr(sequence, "output_full_scales_mv", None),
        "time_reference": "start of each pulse sequence repetition",
        "vertex_rule": (
            "Connect adjacent vertices in order; equal adjacent times encode "
            "an instantaneous SET transition."
        ),
        "reconstruction": (
            "Apply each Cartesian sweep coordinate to the named base segment, "
            "then apply the cross-capacitance matrix and segment timing rules."
        ),
    }


def _awg_point_indices(
    sequence: Any,
    point_indices: Optional[Sequence[int]],
) -> Sequence[int]:
    point_count = int(sequence.sweep_point_count)
    if point_indices is None:
        return range(point_count)
    normalized = tuple(int(index) for index in point_indices)
    if not normalized:
        raise ValueError("point_indices must not be empty")
    if len(set(normalized)) != len(normalized):
        raise ValueError("point_indices must not contain duplicates")
    if any(index < 0 or index >= point_count for index in normalized):
        raise IndexError("AWG metadata point index is out of range")
    return normalized


def build_awg_vertex_record(
    sequence: Any,
    point_index: int,
    *,
    fabric_mhz: float,
    full_scale_mv: float,
) -> Mapping[str, Any]:
    """Expand one Cartesian sweep point into virtual and physical vertices."""
    point_index = int(point_index)
    if not 0 <= point_index < int(sequence.sweep_point_count):
        raise IndexError("AWG metadata point index is out of range")
    virtual_times, virtual_values, boundaries = sequence.waveform_vertices(
        point_index,
        space="virtual",
    )
    physical_times, physical_values, _ = sequence.waveform_vertices(
        point_index,
        space="physical",
    )
    if not np.array_equal(virtual_times, physical_times):
        raise RuntimeError("virtual and physical AWG vertex times differ")
    output_names = tuple(str(name) for name in sequence.output_names)
    times = np.asarray(virtual_times, dtype=float)
    return {
        "schema": "qick-awg-waveform-vertex-record-v1",
        "point_index": point_index,
        "sweep_coordinate": list(sequence.sweep_coordinate(point_index)),
        "time_cycles": times.tolist(),
        "time_us": (times / float(fabric_mhz)).tolist(),
        "segment_boundaries": _json_ready(boundaries),
        "output_names": list(output_names),
        "virtual_values_mv": {
            name: (
                np.asarray(virtual_values[name], dtype=float) * float(full_scale_mv)
            ).tolist()
            for name in output_names
        },
        "physical_values_mv": {
            name: (
                np.asarray(physical_values[name], dtype=float) * (
                    sequence.output_full_scales_mv[output_names.index(name)]
                    if sequence.output_full_scales_mv else float(full_scale_mv))
            ).tolist()
            for name in output_names
        },
        "amplitude_unit": "mV",
    }


def build_awg_vertex_metadata(
    sequence: Any,
    *,
    fabric_mhz: float,
    full_scale_mv: float,
    point_indices: Optional[Sequence[int]] = None,
    cancel_check: Optional[CancellationCheck] = None,
) -> Mapping[str, Any]:
    """Build compact virtual/physical AWG vertices for every sweep point."""
    fabric_mhz = float(fabric_mhz)
    full_scale_mv = float(full_scale_mv)
    if not np.isfinite(fabric_mhz) or fabric_mhz <= 0.0:
        raise ValueError("fabric_mhz must be positive and finite")
    if not np.isfinite(full_scale_mv) or full_scale_mv <= 0.0:
        raise ValueError("full_scale_mv must be positive and finite")

    output_names = tuple(sequence.output_names)
    selected_indices = _awg_point_indices(sequence, point_indices)
    point_count = len(selected_indices)
    point_times = []
    virtual_points = []
    physical_points = []
    coordinates = []
    for point_index in selected_indices:
        _check_cancel(cancel_check)
        virtual_times, virtual_values, _ = sequence.waveform_vertices(
            point_index, space="virtual"
        )
        physical_times, physical_values, _ = sequence.waveform_vertices(
            point_index, space="physical"
        )
        if not np.array_equal(virtual_times, physical_times):
            raise RuntimeError("virtual and physical AWG vertex times differ")
        point_times.append(np.asarray(virtual_times, dtype=float))
        virtual_points.append(
            np.vstack([virtual_values[name] for name in output_names])
            * full_scale_mv
        )
        physical_points.append(
            np.vstack([physical_values[name] for name in output_names])
            * (np.asarray(sequence.output_full_scales_mv)[:, None]
               if sequence.output_full_scales_mv else full_scale_mv)
        )
        coordinates.append(sequence.sweep_coordinate(point_index))

    if not point_times:
        raise ValueError("the AWG sequence has no waveform vertices")
    vertex_count = int(point_times[0].size)
    if any(times.size != vertex_count for times in point_times):
        raise RuntimeError("AWG vertex counts differ between sweep points")
    point_times = np.asarray(point_times, dtype=float)
    shared_times = bool(np.all(point_times == point_times[0]))
    stored_times = point_times[0] if shared_times else point_times
    coordinates = np.asarray(coordinates, dtype=float).reshape(
        point_count,
        len(sequence.sweep_axes),
    )
    shared = {
        "schema": (
            "qick-awg-waveform-vertices-v1"
            if shared_times
            else "qick-awg-waveform-vertices-v2"
        ),
        "output_names": list(output_names),
        "point_index": list(selected_indices),
        "sweep_coordinates": coordinates.tolist(),
        "sweep_axes": _json_ready(sequence.sweep_axes),
        "time_cycles": stored_times.tolist(),
        "time_us": (stored_times / fabric_mhz).tolist(),
        "time_reference": "start of each pulse sequence repetition",
        "amplitude_unit": "mV",
        "full_scale_mv": full_scale_mv,
        "output_full_scales_mv": getattr(sequence, "output_full_scales_mv", None),
        "vertex_rule": (
            "Connect adjacent vertices in order; equal adjacent times encode "
            "an instantaneous SET transition."
        ),
        "value_shape": [point_count, len(output_names), vertex_count],
    }
    return {
        "virtual": {
            **shared,
            "voltage_space": "virtual",
            "values_mv": np.asarray(virtual_points).tolist(),
        },
        "physical": {
            **shared,
            "voltage_space": "physical",
            "values_mv": np.asarray(physical_points).tolist(),
        },
    }


def write_awg_vertex_metadata_jsonl(
    sequence: Any,
    path: Any,
    *,
    fabric_mhz: float,
    full_scale_mv: float,
    point_indices: Optional[Sequence[int]] = None,
    progress_callback: Optional[Callable[[int, int], bool]] = None,
) -> Path:
    """Stream expanded AWG vertices to JSONL without retaining every point."""
    output_path = Path(path)
    if output_path.suffix.lower() != ".jsonl":
        output_path = output_path.with_suffix(".jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    selected_indices = _awg_point_indices(sequence, point_indices)
    recipe = build_awg_waveform_recipe(
        sequence,
        fabric_mhz=fabric_mhz,
        full_scale_mv=full_scale_mv,
    )
    header = {
        "schema": "qick-awg-waveform-vertices-jsonl-v1",
        "record_type": "header",
        "selected_point_count": len(selected_indices),
        "recipe": recipe,
    }
    with output_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(_json_text(header) + "\n")
        for completed, point_index in enumerate(selected_indices, start=1):
            record = build_awg_vertex_record(
                sequence,
                point_index,
                fabric_mhz=fabric_mhz,
                full_scale_mv=full_scale_mv,
            )
            stream.write(
                _json_text({
                    "record_type": "waveform_point",
                    **record,
                })
                + "\n"
            )
            if progress_callback is not None and (
                completed == len(selected_indices)
                or completed == 1
                or completed % max(1, len(selected_indices) // 100) == 0
            ):
                if progress_callback(completed, len(selected_indices)) is False:
                    raise RuntimeError("AWG metadata export canceled")
    return output_path


def _coerce_awg_vertex_data(
    awg_vertices: Mapping[str, Any],
    *,
    point_count: int,
):
    """Validate compact AWG vertices and return arrays for QCoDeS storage."""
    if not awg_vertices:
        return None
    try:
        virtual = awg_vertices["virtual"]
        physical = awg_vertices["physical"]
        output_names = tuple(str(name) for name in virtual["output_names"])
        time_us = np.asarray(virtual["time_us"], dtype=float)
        virtual_mv = np.asarray(virtual["values_mv"], dtype=float)
        physical_mv = np.asarray(physical["values_mv"], dtype=float)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid AWG waveform vertex data") from exc

    if not output_names or time_us.ndim not in (1, 2) or time_us.size < 1:
        raise ValueError("AWG vertex output names and times must not be empty")
    if time_us.ndim == 1:
        time_us = np.broadcast_to(
            time_us,
            (point_count, time_us.size),
        ).copy()
    if time_us.shape[0] != point_count:
        raise ValueError(
            "AWG vertex time arrays must contain one row per sweep point"
        )
    expected_shape = (
        point_count,
        len(output_names),
        time_us.shape[1],
    )
    if virtual_mv.shape != expected_shape or physical_mv.shape != expected_shape:
        raise ValueError(
            "AWG vertex arrays must have shape "
            f"{expected_shape}, received {virtual_mv.shape} and {physical_mv.shape}"
        )
    if tuple(str(name) for name in physical.get("output_names", ())) != output_names:
        raise ValueError("virtual and physical AWG output names differ")
    physical_time_us = np.asarray(physical.get("time_us", ()), dtype=float)
    if physical_time_us.ndim == 1:
        physical_time_us = np.broadcast_to(
            physical_time_us,
            time_us.shape,
        )
    if not np.array_equal(time_us, physical_time_us):
        raise ValueError("virtual and physical AWG vertex times differ")
    if not all(np.all(np.isfinite(values)) for values in (
        time_us,
        virtual_mv,
        physical_mv,
    )):
        raise ValueError("AWG vertex times and voltages must be finite")
    return output_names, time_us, virtual_mv, physical_mv


def connect_qick(
    config: QickConnectionConfig,
    *,
    connector: Optional[Callable[..., Tuple[Any, Any]]] = None,
) -> Tuple[Any, Any]:
    """Connect to a QICK Pyro server, with injection support for tests."""
    if connector is None:
        try:
            from qick.pyro import make_proxy
        except ImportError as exc:
            raise RuntimeError(
                "QICK Python library is required for hardware execution"
            ) from exc
        connector = make_proxy
    return connector(
        ns_host=config.host,
        ns_port=config.ns_port,
        proxy_name=config.proxy_name,
    )


def _validate_summed_rf_spec(gen_cfg, spec):
    """Prevent reuse of a dedicated RF connector's calibration on a v4 AWG DAC."""
    if gen_cfg.get('output_sum_role') != 'rf':
        return
    if (spec.power_calibration_enabled or spec.power_sweep_enabled
            or any(event.power_calibration_enabled for event in spec.pulse_events)):
        raise ValueError('This v4 RF generator is summed into the AWG physical output. '
                         'RF connector power calibration cannot be used on this path; '
                         'disable power calibration and use raw DDS gain.')
    if spec.att1_db or spec.att2_db or spec.filter_type != 'bypass':
        raise ValueError('This v4 RF generator uses the AWG physical output, which has '
                         'no RF attenuator/filter. Select zero attenuation and bypass.')


def build_runtime_rf_pulses(
    soccfg,
    specs: Sequence[QickRfPulseSpec],
    *,
    tproc_mhz: Optional[float] = None,
) -> Tuple[Any, ...]:
    """Convert GUI RF timing in microseconds to actual QICK clock cycles."""
    _ddr_type, rf_type, cycles_from_us = _runtime_types()
    tproc_mhz = _resolve_tproc_mhz(soccfg, tproc_mhz)
    pulses = []
    for spec in specs:
        gen_cfg = soccfg["gens"][spec.gen_ch]
        _validate_summed_rf_spec(gen_cfg, spec)
        parameter_by_name = {
            parameter.name: parameter
            for parameter in spec.frequency_parameters
        }
        legacy_power_points = np.asarray(
            (
                np.linspace(
                    spec.power_sweep_start_dbm,
                    spec.power_sweep_stop_dbm,
                    spec.power_sweep_count,
                    dtype=np.float64,
                )
                if spec.power_sweep_enabled
                else [spec.target_output_power_dbm]
            ),
            dtype=np.float64,
        ).reshape(-1)
        for event in spec.pulse_events:
            if spec.pulse_mode == "composite":
                calibration_enabled = bool(
                    event.power_calibration_enabled
                )
                calibration_database_path = str(
                    event.power_calibration_database_path
                )
                requested_calibration_run_id = int(
                    event.power_calibration_run_id
                )
                power_points = np.asarray(
                    [event.target_output_power_dbm],
                    dtype=np.float64,
                )
            else:
                calibration_enabled = bool(spec.power_calibration_enabled)
                calibration_database_path = str(
                    spec.power_calibration_database_path
                )
                requested_calibration_run_id = int(
                    spec.power_calibration_run_id
                )
                power_points = legacy_power_points
            if event.frequency_parameter:
                parameter = parameter_by_name[event.frequency_parameter]
                frequency_points = np.asarray(
                    (
                        np.linspace(
                            parameter.sweep_start_mhz,
                            parameter.sweep_stop_mhz,
                            parameter.sweep_count,
                            dtype=np.float64,
                        )
                        if parameter.sweep_enabled
                        else [parameter.frequency_mhz]
                    ),
                    dtype=np.float64,
                ).reshape(-1)
                frequency_sweep_enabled = bool(parameter.sweep_enabled)
            else:
                frequency_points = np.asarray(
                    (
                        np.linspace(
                            spec.frequency_sweep_start_mhz,
                            spec.frequency_sweep_stop_mhz,
                            spec.frequency_sweep_count,
                            dtype=np.float64,
                        )
                        if spec.frequency_sweep_enabled
                        else [event.frequency_mhz]
                    ),
                    dtype=np.float64,
                ).reshape(-1)
                frequency_sweep_enabled = bool(spec.frequency_sweep_enabled)
            sweep_gain_codes = ()
            sweep_gain_shape = (0, 0)
            calibration_run_id = None
            runtime_gain = int(event.gain)
            if calibration_enabled:
                table_words = int(frequency_points.size * power_points.size)
                frequency_table_words = (
                    int(frequency_points.size)
                    if frequency_sweep_enabled and frequency_points.size > 1
                    else 0
                )
                gain_table_words = (
                    table_words
                    if frequency_points.size > 1 or power_points.size > 1
                    else 0
                )
                total_rf_table_words = frequency_table_words + gain_table_words
                if total_rf_table_words > MAX_DMEM_GAIN_ENTRIES:
                    raise ValueError(
                        "RF frequency/power sweep requires "
                        f"{total_rf_table_words} frequency/gain words, "
                        "exceeding the tProcessor "
                        f"DMEM table limit {MAX_DMEM_GAIN_ENTRIES}; reduce RF "
                        "frequency or power sweep points"
                    )
                catalog = CalibrationDatabase(
                    calibration_database_path
                )
                calibration = catalog.output_calibration(
                    spec.output_board_type,
                    frequency_points,
                    run_id=(
                        None
                        if requested_calibration_run_id == 0
                        else requested_calibration_run_id
                    ),
                    nqz=int(spec.nqz),
                    output_filter_type=str(spec.filter_type),
                    output_filter_cutoff_ghz=float(spec.filter_cutoff),
                    output_filter_bandwidth_ghz=float(spec.filter_bandwidth),
                )
                gain_matrix = np.empty(
                    (frequency_points.size, power_points.size),
                    dtype=np.int32,
                )
                for power_index, target_power_dbm in enumerate(power_points):
                    schedule = calibration.build_gain_schedule(
                        frequency_points,
                        float(target_power_dbm),
                        output_att1_db=float(spec.effective_att1_db),
                        output_att2_db=float(spec.effective_att2_db),
                        max_entries=int(frequency_points.size),
                    )
                    if len(schedule.gain_codes) != frequency_points.size:
                        raise RuntimeError(
                            "RF calibration gain schedule was unexpectedly compressed"
                        )
                    gain_matrix[:, power_index] = schedule.gain_codes
                sweep_gain_codes = tuple(
                    int(value) for value in gain_matrix.reshape(-1)
                )
                sweep_gain_shape = tuple(
                    int(value) for value in gain_matrix.shape
                )
                calibration_run_id = int(calibration.summary.run_id)
                runtime_gain = int(gain_matrix[0, 0])
            delay_cycles = (
                0
                if event.delay_us <= 0.0
                else cycles_from_us(event.delay_us, tproc_mhz)
            )
            pulses.append(rf_type(
                gen_ch=spec.gen_ch,
                at_segment=spec.segment_name,
                length_cycles=cycles_from_us(
                    (
                        spec.duration_sweep_start_us
                        if spec.duration_sweep_enabled
                        else event.duration_us
                    ),
                    float(gen_cfg["f_fabric"]),
                ),
                gain=runtime_gain,
                freq_mhz=float(frequency_points[0]),
                phase_degrees=event.phase_degrees,
                nqz=spec.nqz,
                delay_tproc_cycles=delay_cycles,
                require_within_segment=spec.require_within_segment,
                sweep_gain_codes=sweep_gain_codes,
                sweep_gain_shape=sweep_gain_shape,
                power_calibration_run_id=calibration_run_id,
                event_id=event.event_id,
                pulse_name=event.name,
                frequency_parameter=event.frequency_parameter,
                duration_parameter=event.duration_parameter,
                preceding_duration_parameters=(
                    event.preceding_duration_parameters
                ),
            ))
    return tuple(pulses)


def build_runtime_ddr_readout(
    soccfg,
    spec: QickDdrReadoutSpec,
    *,
    tproc_mhz: Optional[float] = None,
) -> Any:
    """Convert the GUI's FIR DDR readout settings to program timing."""
    ddr_type, _rf_type, cycles_from_us = _runtime_types()
    tproc_mhz = _resolve_tproc_mhz(soccfg, tproc_mhz)
    delay_cycles = (
        0
        if spec.delay_us <= 0.0
        else cycles_from_us(spec.delay_us, tproc_mhz)
    )
    fpga_trigger_delay = spec.fpga_trigger_delay_samples
    if spec.fpga_trigger_delay_us is not None:
        fir_profile = resolve_fir_ddr_profile(
            soccfg,
            context="QICK experiment FIR DDR",
        )
        fpga_trigger_delay = fir_profile.trigger_delay_value_for_us(
            spec.fpga_trigger_delay_us
        )
    return ddr_type(
        ro_ch=spec.ro_ch,
        samples_per_trigger=spec.samples_per_trigger,
        at_segment=spec.segment_name,
        fpga_trigger_delay_samples=fpga_trigger_delay,
        readout_freq_mhz=spec.readout_frequency_mhz,
        trigger_delay_tproc_cycles=delay_cycles,
        margin_input_samples=spec.margin_input_samples,
        address=spec.address,
        force_overwrite=spec.force_overwrite,
        settle_seconds=spec.post_run_read_delay_seconds,
        dc_compensation_timing=spec.dc_compensation_timing,
    )


def build_runtime_avg_readout(
    soccfg,
    spec: QickDdrReadoutSpec,
    *,
    tproc_mhz: Optional[float] = None,
) -> Any:
    """Convert shared GUI readout settings to an AVG-buffer trigger."""
    readout_type = _runtime_readout_type()
    _ddr_type, _rf_type, cycles_from_us = _runtime_types()
    tproc_mhz = _resolve_tproc_mhz(soccfg, tproc_mhz)
    delay_cycles = (
        0
        if spec.delay_us <= 0.0
        else cycles_from_us(spec.delay_us, tproc_mhz)
    )
    return readout_type(
        ro_ch=spec.ro_ch,
        length=spec.samples_per_trigger,
        freq_mhz=spec.readout_frequency_mhz,
        at_segment=spec.segment_name,
        timing_reference="segment_start",
        measure_delay_tproc_cycles=delay_cycles,
        phrst=0,
    )


def build_qick_program(
    soccfg,
    sequence,
    *,
    awg_channels: Sequence[int],
    repetitions_per_sweep: int,
    tproc_mhz: Optional[float] = None,
    rf_specs: Sequence[QickRfPulseSpec] = (),
    readout_spec: Optional[QickDdrReadoutSpec] = None,
    acquisition_source: str = "fir_ddr",
    hardware_rep_delay_us: float = 0.0,
    compile_validation_mode: str = DEFAULT_COMPILE_VALIDATION_MODE,
    cancel_check: Optional[CancellationCheck] = None,
):
    """Build the tProcessor program without configuring or running hardware."""
    effective_tproc_mhz = _resolve_tproc_mhz(soccfg, tproc_mhz)
    acquisition_source = str(acquisition_source)
    if acquisition_source not in {"fir_ddr", "avg_buffer"}:
        raise ValueError(
            "acquisition_source must be fir_ddr or avg_buffer"
        )
    hardware_rep_delay_us = float(hardware_rep_delay_us)
    if not np.isfinite(hardware_rep_delay_us) or hardware_rep_delay_us < 0.0:
        raise ValueError("hardware_rep_delay_us must be nonnegative and finite")
    _ddr_type, _rf_type, cycles_from_us = _runtime_types()
    recovery_tproc_cycles = 20 + (
        0
        if hardware_rep_delay_us == 0.0
        else cycles_from_us(hardware_rep_delay_us, effective_tproc_mhz)
    )
    program_kwargs = {
        "awg_channels": tuple(int(channel) for channel in awg_channels),
        "tproc_mhz": effective_tproc_mhz,
        "repetitions_per_sweep": int(repetitions_per_sweep),
        "compile_validation_mode": normalize_compile_validation_mode(
            compile_validation_mode
        ),
        "rf_pulses": build_runtime_rf_pulses(
            soccfg, rf_specs, tproc_mhz=effective_tproc_mhz
        ),
        "recovery_tproc_cycles": recovery_tproc_cycles,
    }
    if readout_spec is not None:
        if acquisition_source == "fir_ddr":
            program_kwargs["ddr_readout"] = build_runtime_ddr_readout(
                soccfg, readout_spec, tproc_mhz=effective_tproc_mhz
            )
        else:
            program_kwargs["readout"] = build_runtime_avg_readout(
                soccfg, readout_spec, tproc_mhz=effective_tproc_mhz
            )
    if cancel_check is not None:
        program_kwargs["cancel_check"] = cancel_check
    _check_cancel(cancel_check)
    return sequence.make_program(soccfg, **program_kwargs)


def _rf_output_details(
    spec: QickRfPulseSpec,
    actual_att1: float,
    actual_att2: float,
) -> Mapping[str, Any]:
    return {
        "gen_ch": int(spec.gen_ch),
        "board_type": str(spec.output_board_type),
        "attenuators_present": spec.output_board_type == "RF_Out",
        "requested_att1_db": float(spec.att1_db),
        "requested_att2_db": float(spec.att2_db),
        "commanded_att1_db": float(actual_att1),
        "commanded_att2_db": float(actual_att2),
        "filter_type": str(spec.filter_type),
        "filter_cutoff_ghz": float(spec.filter_cutoff),
        "filter_bandwidth_ghz": float(spec.filter_bandwidth),
    }


def describe_rf_output(spec: QickRfPulseSpec) -> Mapping[str, Any]:
    """Describe an output setting without writing the RF-board hardware."""
    if spec.output_board_type == "RF_Out":
        actual_att1 = float(spec.att1_db)
        actual_att2 = float(spec.att2_db)
    else:
        actual_att1 = 0.0
        actual_att2 = 0.0
    return _rf_output_details(spec, actual_att1, actual_att2)


def configure_rf_output(
    soc,
    spec: QickRfPulseSpec,
) -> Mapping[str, Any]:
    """Apply one RF-board output setting when the user commits it."""
    config = soc.get_cfg() if hasattr(soc, 'get_cfg') else None
    if config is not None and config['gens'][spec.gen_ch].get('output_sum_role') == 'rf':
        _validate_summed_rf_spec(config['gens'][spec.gen_ch], spec)
        soc.rfb_set_gen_dc(spec.gen_ch)
        return _rf_output_details(replace(spec, output_board_type='DC_Out'), 0., 0.)
    if spec.output_board_type == "RF_Out":
        actual_attenuation = soc.rfb_set_gen_rf(
            spec.gen_ch, spec.att1_db, spec.att2_db
        )
        try:
            actual_att1, actual_att2 = (
                float(actual_attenuation[0]),
                float(actual_attenuation[1]),
            )
        except (IndexError, TypeError, ValueError) as exc:
            raise RuntimeError(
                f"RF generator {spec.gen_ch} returned an invalid attenuation "
                f"result: {actual_attenuation!r}"
            ) from exc
        soc.rfb_set_gen_filter(
            spec.gen_ch,
            fc=spec.filter_cutoff,
            bw=spec.filter_bandwidth,
            ftype=spec.filter_type,
        )
    else:
        soc.rfb_set_gen_dc(spec.gen_ch)
        actual_att1 = 0.0
        actual_att2 = 0.0
    return _rf_output_details(spec, actual_att1, actual_att2)


def configure_rf_readout(
    soc,
    readout_spec: QickDdrReadoutSpec,
) -> Mapping[str, Any]:
    """Apply ADC-side Nyquist, gain/attenuation, and filter settings."""
    set_nyquist = getattr(soc, "set_nyquist", None)
    if set_nyquist is None:
        if readout_spec.nqz != 1:
            raise RuntimeError(
                "ADC Nyquist-zone control requires an updated QICK server"
            )
    else:
        try:
            set_nyquist(
                readout_spec.ro_ch,
                readout_spec.nqz,
                blocktype="adc",
            )
        except TypeError as exc:
            if readout_spec.nqz != 1:
                raise RuntimeError(
                    "ADC Nyquist-zone control requires an updated QICK server"
                ) from exc
    if readout_spec.input_board_type == "RF_In":
        readout_setting = float(
            soc.rfb_set_ro_rf(
                readout_spec.ro_ch,
                readout_spec.attenuation_db,
            )
        )
        readout_attenuation = readout_setting
        readout_dc_gain = 0.0
    else:
        readout_setting = float(
            soc.rfb_set_ro_dc(
                readout_spec.ro_ch,
                readout_spec.dc_gain_db,
            )
        )
        readout_attenuation = 0.0
        readout_dc_gain = readout_setting
    if readout_spec.input_board_type == "RF_In":
        soc.rfb_set_ro_filter(
            readout_spec.ro_ch,
            fc=readout_spec.filter_cutoff,
            bw=readout_spec.filter_bandwidth,
            ftype=readout_spec.filter_type,
        )
    return {
        "readout": readout_setting,
        "readout_details": {
            "ro_ch": int(readout_spec.ro_ch),
            "board_type": str(readout_spec.input_board_type),
            "nyquist_zone": int(readout_spec.nqz),
            "attenuator_present": readout_spec.input_board_type == "RF_In",
            "requested_attenuation_db": float(readout_spec.attenuation_db),
            "commanded_attenuation_db": readout_attenuation,
            "requested_dc_gain_db": float(readout_spec.dc_gain_db),
            "commanded_dc_gain_db": readout_dc_gain,
            "dc_measure_mode": bool(readout_spec.dc_measure_mode),
            "dc_measure_gain_v_per_a": float(
                readout_spec.dc_measure_gain_v_per_a
            ),
            "dc_voltage_calibration_enabled": bool(
                readout_spec.dc_voltage_calibration_enabled
            ),
            "dc_voltage_calibration_database_path": str(
                readout_spec.dc_voltage_calibration_database_path
            ),
            "dc_voltage_calibration_run_id": int(
                readout_spec.dc_voltage_calibration_run_id
            ),
            "measurement_representation": str(
                readout_spec.effective_measurement_representation
            ),
            "post_run_read_delay_seconds": float(
                readout_spec.post_run_read_delay_seconds
            ),
            "adc_to_voltage_conversion": (
                "qcodes_dc_voltage_calibration"
                if readout_spec.dc_voltage_calibration_enabled
                else "identity"
            ),
            "measurement_unit": readout_spec.measurement_unit,
            "filter_type": str(readout_spec.filter_type),
            "filter_cutoff_ghz": float(readout_spec.filter_cutoff),
            "filter_bandwidth_ghz": float(readout_spec.filter_bandwidth),
        },
    }


def configure_rf_board(
    soc,
    rf_specs: Sequence[QickRfPulseSpec],
    readout_spec: QickDdrReadoutSpec,
) -> Mapping[str, Any]:
    """Apply RF-board output and input settings explicitly."""
    output_details = tuple(
        configure_rf_output(soc, spec) for spec in rf_specs
    )
    readout_settings = configure_rf_readout(soc, readout_spec)
    return {
        "outputs": tuple(
            (
                float(details["commanded_att1_db"]),
                float(details["commanded_att2_db"]),
            )
            for details in output_details
        ),
        "output_details": output_details,
        **readout_settings,
    }


def _execute_qick_sequence_once(
    soc,
    soccfg,
    sequence,
    *,
    awg_channels: Sequence[int],
    repetitions_per_sweep: int,
    tproc_mhz: Optional[float] = None,
    rf_specs: Sequence[QickRfPulseSpec],
    readout_spec: QickDdrReadoutSpec,
    acquisition_source: str = "fir_ddr",
    hardware_rep_delay_us: float = 0.0,
    compile_validation_mode: str = DEFAULT_COMPILE_VALIDATION_MODE,
    progress: bool = False,
    progress_callback: Optional[ProgressCallback] = None,
    event_callback: Optional[ExperimentEventCallback] = None,
    cancel_check: Optional[CancellationCheck] = None,
) -> Tuple[Any, Any, Mapping[str, Any]]:
    """Configure and execute one FIR-DDR or AVG-buffer acquisition."""
    acquisition_source = str(acquisition_source)
    if acquisition_source not in {"fir_ddr", "avg_buffer"}:
        raise ValueError(
            "acquisition_source must be fir_ddr or avg_buffer"
        )
    _check_cancel(cancel_check)
    _emit_progress(progress_callback, 5, "Configuring RF readout hardware")
    _emit_experiment_event(
        event_callback,
        "rf_setup",
        "started",
        "Configuring RF readout hardware",
    )
    readout_settings = configure_rf_readout(soc, readout_spec)
    _check_cancel(cancel_check)
    _emit_experiment_event(
        event_callback,
        "rf_setup",
        "completed",
        "RF readout hardware configured",
    )
    output_details = tuple(describe_rf_output(spec) for spec in rf_specs)
    rf_settings = {
        "outputs": tuple(
            (
                float(details["commanded_att1_db"]),
                float(details["commanded_att2_db"]),
            )
            for details in output_details
        ),
        "output_details": output_details,
        **readout_settings,
    }
    _emit_progress(progress_callback, 8, "Compiling the tProcessor program")
    _emit_experiment_event(
        event_callback,
        "compile",
        "started",
        "Compiling the tProcessor program",
    )
    program = build_qick_program(
        soccfg,
        sequence,
        awg_channels=tuple(int(channel) for channel in awg_channels),
        tproc_mhz=tproc_mhz,
        repetitions_per_sweep=int(repetitions_per_sweep),
        rf_specs=rf_specs,
        readout_spec=readout_spec,
        acquisition_source=acquisition_source,
        hardware_rep_delay_us=hardware_rep_delay_us,
        compile_validation_mode=compile_validation_mode,
        cancel_check=cancel_check,
    )
    _check_cancel(cancel_check)
    _emit_experiment_event(
        event_callback,
        "compile",
        "completed",
        "tProcessor program compiled",
    )
    sweep_point_count = int(getattr(
        sequence,
        "sweep_point_count",
        getattr(program, "cfg", {}).get("expts", 1),
    ))
    _emit_progress(
        progress_callback,
        10,
        (
            "Running pulse sequence: "
            f"{sweep_point_count:,} sweep points x "
            f"{int(repetitions_per_sweep):,} repetitions"
        ),
    )

    def counter_progress(completed: int, total: int) -> None:
        _check_cancel(cancel_check)
        fraction = 1.0 if total <= 0 else completed / total
        percent = 10 + round(max(0.0, min(1.0, fraction)) * 45)
        _emit_progress(
            progress_callback,
            percent,
            (
                f"Running acquisitions {completed:,}/{total:,} "
                f"({sweep_point_count:,} sweep points x "
                f"{int(repetitions_per_sweep):,} repetitions)"
            ),
        )

    def readback_progress(completed: int, total: int) -> None:
        _check_cancel(cancel_check)
        fraction = 1.0 if total <= 0 else completed / total
        fraction = max(0.0, min(1.0, fraction))
        percent = 55 + round(fraction * 9)
        samples_per_trigger = int(readout_spec.samples_per_trigger)
        completed_samples = int(completed) * samples_per_trigger
        total_samples = int(total) * samples_per_trigger
        _emit_progress(
            progress_callback,
            percent,
            (
                f"Reading FIR DDR traces {completed:,}/{total:,} "
                f"({100.0 * fraction:.1f}% readback; "
                f"{completed_samples:,}/{total_samples:,} I/Q sample pairs)"
            ),
        )

    acquire_kwargs = {
        "progress": progress,
        "counter_progress": (
            counter_progress
            if progress_callback is not None or event_callback is not None
            else None
        ),
    }
    if cancel_check is not None:
        acquire_kwargs["cancel_check"] = cancel_check
    from qick_square_dds import get_square_configs
    squares = get_square_configs(sequence)
    if squares:
        if not hasattr(soc, "stop_square_pulse"):
            raise RuntimeError("Update the board QSTL_QICK library: stop_square_pulse is required")
        for square in squares:
            soc.rfb_set_gen_dc(square.gen_ch)
    completed = False
    try:
        if acquisition_source == "fir_ddr":
            acquire_kwargs["readback_progress"] = (
                readback_progress if progress_callback is not None else None
            )
            if event_callback is not None:
                acquire_kwargs["phase_callback"] = event_callback
            ddr_result = program.acquire_fir_ddr(soc, **acquire_kwargs)
            completion_message = "FIR DDR acquisition and readback completed"
        else:
            ddr_result = program.acquire_avg_buffer(soc, **acquire_kwargs)
            completion_message = "AVG-buffer hardware accumulation completed"
        _check_cancel(cancel_check)
        completed = True
    finally:
        # Keep autonomous output only after a successful run when requested.
        # Cancellation and acquisition errors still stop the selected output.
        for square in squares:
            if not completed or square.mute_on_finish:
                soc.stop_square_pulse(square.gen_ch)
    _check_cancel(cancel_check)
    _emit_progress(
        progress_callback,
        64,
        completion_message,
    )
    return program, ddr_result, rf_settings


@dataclass(frozen=True)
class SoftwareSweepProgramBundle:
    """Programs compiled for a predefined composite RF software sweep."""

    programs: Tuple[Any, ...]
    sweep_axes: Tuple[QickRfSoftwareSweepAxisSpec, ...]
    sweep_coordinates: np.ndarray

    def summary(self) -> Mapping[str, Any]:
        base = dict(self.programs[-1].summary())
        base.update({
            "software_sweep_program_count": len(self.programs),
            "software_sweep_axes": [asdict(axis) for axis in self.sweep_axes],
            "software_sweep_coordinates": self.sweep_coordinates.tolist(),
            "software_sweep_execution": (
                "one tProcessor compile/acquisition per predefined RF point"
            ),
        })
        return base

    def __getattr__(self, name: str) -> Any:
        return getattr(self.programs[-1], name)


def _rf_software_sweep_bindings(
    rf_specs: Sequence[QickRfPulseSpec],
) -> Tuple[Tuple[int, QickRfSoftwareSweepAxisSpec], ...]:
    return tuple(
        (spec_index, axis)
        for spec_index, spec in enumerate(rf_specs)
        for axis in spec.software_sweep_axes
    )


def _software_sweep_coordinates(
    bindings: Sequence[Tuple[int, QickRfSoftwareSweepAxisSpec]],
) -> np.ndarray:
    if not bindings:
        return np.empty((1, 0), dtype=np.float64)
    rows = tuple(product(*(axis.points for _index, axis in bindings)))
    return np.asarray(rows, dtype=np.float64).reshape(len(rows), len(bindings))


def _rf_specs_at_software_coordinate(
    rf_specs: Sequence[QickRfPulseSpec],
    bindings: Sequence[Tuple[int, QickRfSoftwareSweepAxisSpec]],
    coordinate: Sequence[float],
) -> Tuple[QickRfPulseSpec, ...]:
    updates = {}
    for (spec_index, axis), value in zip(bindings, coordinate):
        point = updates.setdefault(spec_index, {})
        if axis.axis_kind == "rf_template_n":
            point["n_pulses"] = int(round(float(value)))
        elif axis.axis_kind == "rf_template_tau":
            point["tau_us"] = float(value)
        else:
            raise ValueError(
                f"unsupported RF software sweep kind {axis.axis_kind!r}"
            )
    return tuple(
        spec.with_predefined_parameters(**updates[index])
        if index in updates
        else spec
        for index, spec in enumerate(rf_specs)
    )


def _sequence_at_rf_software_coordinate(
    sequence: Any,
    rf_specs: Sequence[QickRfPulseSpec],
    *,
    fabric_mhz: float,
) -> Any:
    """Clone a sequence and update RF-driven SET extension durations."""
    concrete = deepcopy(sequence)
    _ddr_type, _rf_type, cycles_from_us = _runtime_types()
    for spec in rf_specs:
        if spec.segment_length_mode != "extend_by_rf_duration":
            continue
        concrete.set_rf_segment_length_extension(
            segment=spec.segment_name,
            gen_ch=spec.gen_ch,
            base_duration_cycles=sum(
                cycles_from_us(duration_us, fabric_mhz)
                for duration_us in spec.segment_extension_components_us
            ),
            parameter_multiplicities=dict(
                spec.duration_parameter_reference_counts
            ),
        )
    concrete._validate()
    return concrete


def _result_sweep_coordinates(result: Any) -> np.ndarray:
    axes = tuple(result.sweep_axes)
    point_count = int(np.asarray(result.iq).shape[0])
    if not axes:
        return np.empty((point_count, 0), dtype=np.float64)
    coordinates = np.asarray(result.sweep_points, dtype=np.float64)
    if len(axes) == 1:
        coordinates = coordinates.reshape(-1, 1)
    if coordinates.shape != (point_count, len(axes)):
        raise ValueError("hardware sweep result has inconsistent coordinates")
    return coordinates


def _combine_software_sweep_results(
    results: Sequence[Any],
    bindings: Sequence[Tuple[int, QickRfSoftwareSweepAxisSpec]],
    software_coordinates: np.ndarray,
) -> Any:
    if not results:
        raise RuntimeError("RF software sweep produced no acquisition results")
    first = results[0]
    first_iq = np.asarray(first.iq)
    hardware_coordinates = _result_sweep_coordinates(first)
    hardware_axes = tuple(first.sweep_axes)
    hardware_point_count = first_iq.shape[0]
    for result in results[1:]:
        if np.asarray(result.iq).shape != first_iq.shape:
            raise RuntimeError(
                "RF software sweep points returned different DDR IQ shapes"
            )
        if tuple(result.sweep_axes) != hardware_axes:
            raise RuntimeError(
                "RF software sweep changed the hardware sweep axes"
            )
        if not np.array_equal(
            _result_sweep_coordinates(result),
            hardware_coordinates,
        ):
            raise RuntimeError(
                "RF software sweep changed hardware sweep coordinates"
            )
    software_expanded = np.repeat(
        software_coordinates,
        hardware_point_count,
        axis=0,
    )
    hardware_expanded = np.tile(
        hardware_coordinates,
        (len(results), 1),
    )
    all_coordinates = np.column_stack((software_expanded, hardware_expanded))
    final_axes = tuple(axis for _index, axis in bindings) + hardware_axes
    final_points = (
        all_coordinates[:, 0]
        if len(final_axes) == 1
        else all_coordinates
    )
    hardware_shape = tuple(int(axis.count) for axis in hardware_axes)
    software_shape = tuple(int(axis.count) for _index, axis in bindings)
    reserved_values = [
        getattr(result, "reserved_physical_words", None)
        for result in results
    ]
    reserved = (
        max(int(value) for value in reserved_values)
        if all(value is not None for value in reserved_values)
        else None
    )
    return replace(
        first,
        sweep_points=final_points,
        iq=np.concatenate(
            [np.asarray(result.iq) for result in results],
            axis=0,
        ),
        reserved_physical_words=reserved,
        sweep_axes=final_axes,
        sweep_shape=software_shape + hardware_shape,
    )


def execute_qick_sequence(
    soc,
    soccfg,
    sequence,
    *,
    awg_channels: Sequence[int],
    repetitions_per_sweep: int,
    tproc_mhz: Optional[float] = None,
    rf_specs: Sequence[QickRfPulseSpec],
    readout_spec: QickDdrReadoutSpec,
    acquisition_source: str = "fir_ddr",
    hardware_rep_delay_us: float = 0.0,
    sequence_fabric_mhz: float = 300.0,
    compile_validation_mode: str = DEFAULT_COMPILE_VALIDATION_MODE,
    progress: bool = False,
    progress_callback: Optional[ProgressCallback] = None,
    event_callback: Optional[ExperimentEventCallback] = None,
    cancel_check: Optional[CancellationCheck] = None,
) -> Tuple[Any, Any, Mapping[str, Any]]:
    """Execute once, or recompile once per predefined CPMG/UDD point."""
    rf_specs = tuple(rf_specs)
    bindings = _rf_software_sweep_bindings(rf_specs)
    if not bindings:
        return _execute_qick_sequence_once(
            soc,
            soccfg,
            sequence,
            awg_channels=awg_channels,
            repetitions_per_sweep=repetitions_per_sweep,
            tproc_mhz=tproc_mhz,
            rf_specs=rf_specs,
            readout_spec=readout_spec,
            acquisition_source=acquisition_source,
            hardware_rep_delay_us=hardware_rep_delay_us,
            compile_validation_mode=compile_validation_mode,
            progress=progress,
            progress_callback=progress_callback,
            event_callback=event_callback,
            cancel_check=cancel_check,
        )

    coordinates = _software_sweep_coordinates(bindings)
    programs = []
    results = []
    first_rf_settings = None
    total = coordinates.shape[0]
    for point_index, coordinate in enumerate(coordinates):
        _check_cancel(cancel_check)
        concrete_specs = _rf_specs_at_software_coordinate(
            rf_specs,
            bindings,
            coordinate,
        )
        concrete_sequence = _sequence_at_rf_software_coordinate(
            sequence,
            concrete_specs,
            fabric_mhz=float(sequence_fabric_mhz),
        )

        def point_progress(percent: int, message: str) -> None:
            local_fraction = max(
                0.0,
                min(1.0, (float(percent) - 5.0) / 59.0),
            )
            global_percent = 5 + round(
                ((point_index + local_fraction) / total) * 59
            )
            _emit_progress(
                progress_callback,
                global_percent,
                f"RF software sweep {point_index + 1:,}/{total:,}: {message}",
            )

        def point_event(key: str, state: str, message: str) -> None:
            _emit_experiment_event(
                event_callback,
                key,
                state,
                f"RF software sweep {point_index + 1:,}/{total:,}: {message}",
            )

        program, result, rf_settings = _execute_qick_sequence_once(
            soc,
            soccfg,
            concrete_sequence,
            awg_channels=awg_channels,
            repetitions_per_sweep=repetitions_per_sweep,
            tproc_mhz=tproc_mhz,
            rf_specs=concrete_specs,
            readout_spec=readout_spec,
            acquisition_source=acquisition_source,
            hardware_rep_delay_us=hardware_rep_delay_us,
            compile_validation_mode=compile_validation_mode,
            progress=progress,
            progress_callback=point_progress,
            event_callback=point_event,
            cancel_check=cancel_check,
        )
        programs.append(program)
        results.append(result)
        if first_rf_settings is None:
            first_rf_settings = dict(rf_settings)

    combined = _combine_software_sweep_results(
        results,
        bindings,
        coordinates,
    )
    bundle = SoftwareSweepProgramBundle(
        programs=tuple(programs),
        sweep_axes=tuple(axis for _index, axis in bindings),
        sweep_coordinates=coordinates,
    )
    first_rf_settings.update({
        "predefined_software_sweep": {
            "execution": "host software sweep",
            "program_count": total,
            "axes": [asdict(axis) for _index, axis in bindings],
            "coordinates": coordinates.tolist(),
        },
    })
    return bundle, combined, first_rf_settings


def _sweep_coordinates(ddr_result: Any) -> np.ndarray:
    axis_count = len(tuple(ddr_result.sweep_axes))
    point_count = int(np.asarray(ddr_result.iq).shape[0])
    if axis_count == 0:
        return np.empty((point_count, 0), dtype=float)
    coordinates = np.asarray(ddr_result.sweep_points, dtype=float)
    if axis_count == 1:
        coordinates = coordinates.reshape(-1, 1)
    if coordinates.shape != (point_count, axis_count):
        raise ValueError(
            "sweep coordinate shape does not match DDR point/axis counts"
        )
    return coordinates


def _qcodes_identifier(value: Any) -> str:
    """Convert a user-facing output/segment label to a QCoDeS-safe name."""
    identifier = re.sub(r"[^0-9A-Za-z_]+", "_", str(value)).strip("_").lower()
    if not identifier:
        identifier = "unnamed"
    if identifier[0].isdigit():
        identifier = f"p_{identifier}"
    return identifier


def _sweep_parameter_names(axes: Sequence[Any]) -> Tuple[str, ...]:
    """Name sweep axes by their physical output and segment target."""
    used = set()
    names = []
    for axis in axes:
        axis_kind = getattr(axis, "axis_kind", "amplitude")
        suffix = {
            "rf_template_n": "pulse_count_n",
            "rf_template_tau": "tau_us",
            "rf_duration": "duration_us",
            "rf_frequency": "frequency_mhz",
            "rf_power": "output_power_dbm",
            "square_frequency": "frequency_mhz",
            "square_amplitude": "amplitude_mv",
            "square_phase": "phase_deg",
            "ramp_duration": "ramp_duration_us",
            "hold_duration": "hold_duration_us",
        }.get(axis_kind, "voltage_mv")
        base = (
            f"{_qcodes_identifier(axis.output_name)}_"
            f"{_qcodes_identifier(axis.segment_name)}_{suffix}"
        )
        name = base
        suffix = 2
        while name in used:
            name = f"{base}_{suffix}"
            suffix += 1
        used.add(name)
        names.append(name)
    return tuple(names)


def _sweep_axis_display(axis: Any, full_scale_mv: float) -> Tuple[str, str, float]:
    axis_kind = getattr(axis, "axis_kind", "amplitude")
    if axis_kind.startswith("square_"):
        return "SquarePulse " + axis.parameter, axis.coordinate_unit, 1.0
    if axis_kind == "rf_template_n":
        return "predefined RF pulse count N", "", 1.0
    if axis_kind == "rf_template_tau":
        return "predefined RF tau", "us", 1.0
    if axis_kind == "rf_duration":
        return "RF pulse duration", "us", 1.0
    if axis_kind == "rf_frequency":
        return "RF frequency", "MHz", 1.0
    if axis_kind == "rf_power":
        return "Calibrated RF connector power", "dBm", 1.0
    if axis_kind == "ramp_duration":
        return "RAMP duration (rate derived)", "us", 1.0
    if axis_kind == "hold_duration":
        return "SET hold duration", "us", 1.0
    return "voltage", "mV", float(full_scale_mv)


def _sweep_axis_meaning(axis: Any) -> str:
    """Describe one stored Cartesian coordinate without nested UI logic."""
    axis_kind = getattr(axis, "axis_kind", "amplitude")
    if axis_kind.startswith("square_"):
        return f"SquarePulse generator {axis.gen_ch} {axis.parameter}; tProcessor hardware sweep."
    if axis_kind == "rf_template_n":
        meaning = (
            f"Predefined composite RF pulse count N for {axis.output_name}/"
            f"{axis.segment_name}; each coordinate is a host software run"
        )
    elif axis_kind == "rf_template_tau":
        meaning = (
            f"Predefined composite RF tau for {axis.output_name}/"
            f"{axis.segment_name}; each coordinate is a host software run"
        )
    elif axis_kind == "rf_duration":
        meaning = (
            f"RF pulse duration for {axis.output_name}/"
            f"{axis.segment_name}"
        )
    elif axis_kind == "rf_frequency":
        meaning = (
            f"RF generator frequency for {axis.output_name}/"
            f"{axis.segment_name}"
        )
    elif axis_kind == "rf_power":
        meaning = (
            f"Calibrated RF connector power for {axis.output_name}/"
            f"{axis.segment_name}"
        )
    elif axis_kind == "ramp_duration":
        meaning = (
            f"RAMP duration for {axis.segment_name}; RAMP rate is "
            "derived from its adjacent SET voltages"
        )
    elif axis_kind == "hold_duration":
        meaning = f"SET hold duration for {axis.segment_name}"
    else:
        meaning = (
            f"Voltage applied to {axis.output_name}/"
            f"{axis.segment_name}"
        )
    return meaning + "; this is a directly selectable Cartesian sweep axis."


def _full_scale_mv(gui_settings: Mapping[str, Any]) -> float:
    qick_settings = gui_settings.get("qick", {})
    if not isinstance(qick_settings, Mapping):
        raise ValueError("GUI qick settings must be a mapping")
    value = float(
        qick_settings.get("full_scale_mv", DEFAULT_QICK_FULL_SCALE_MV)
    )
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError("QICK full_scale_mv must be finite and positive")
    return value


def _qcodes_staging_root() -> Path:
    configured = os.environ.get(QCODES_STAGING_ENV)
    if configured:
        root = Path(configured).expanduser().resolve()
    else:
        local_root = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        root = Path(local_root) / "QSTL_PulseGenerator" / "qcodes_staging"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _backup_sqlite_database(
    source: Path,
    destination: Path,
    *,
    cancel_check: Optional[CancellationCheck] = None,
) -> None:
    """Copy a live SQLite database, including committed WAL content."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_uri = source.resolve().as_uri() + "?mode=ro"
    source_connection = sqlite3.connect(source_uri, uri=True, timeout=60.0)
    destination_connection = sqlite3.connect(str(destination), timeout=60.0)
    try:
        source_connection.backup(
            destination_connection,
            pages=4096,
            sleep=0.01,
            progress=(
                None
                if cancel_check is None
                else lambda _status, _remaining, _total: _check_cancel(
                    cancel_check
                )
            ),
        )
        destination_connection.commit()
    finally:
        destination_connection.close()
        source_connection.close()


def _prepare_local_database(
    database_path: Path,
    *,
    cancel_check: Optional[CancellationCheck] = None,
) -> Tuple[Path, Path]:
    staging_directory = Path(tempfile.mkdtemp(
        prefix="qick_qcodes_",
        dir=str(_qcodes_staging_root()),
    ))
    local_database_path = staging_directory / database_path.name
    try:
        _check_cancel(cancel_check)
        if database_path.exists() and database_path.stat().st_size > 0:
            _backup_sqlite_database(
                database_path,
                local_database_path,
                cancel_check=cancel_check,
            )
        _check_cancel(cancel_check)
    except Exception:
        shutil.rmtree(staging_directory, ignore_errors=True)
        raise
    return staging_directory, local_database_path


def _checkpoint_sqlite_database(database_path: Path) -> None:
    connection = sqlite3.connect(str(database_path), timeout=60.0)
    try:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.commit()
    finally:
        connection.close()


def _publish_local_database(local_path: Path, database_path: Path) -> None:
    """Publish the completed local database with SQLite's backup API."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    source_uri = local_path.resolve().as_uri() + "?mode=ro"
    source_connection = sqlite3.connect(source_uri, uri=True, timeout=60.0)
    destination_connection = sqlite3.connect(str(database_path), timeout=60.0)
    try:
        destination_connection.execute("PRAGMA busy_timeout=60000")
        source_connection.backup(destination_connection, pages=4096, sleep=0.01)
        destination_connection.commit()
        destination_connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        destination_connection.commit()
    finally:
        destination_connection.close()
        source_connection.close()


def _first_value_per_trace(values: Any, trace_count: int) -> np.ndarray:
    array = np.asarray(values)
    if array.shape[0] != trace_count:
        raise ValueError("QCoDeS trace setpoint count does not match IQ traces")
    return array.reshape(trace_count, -1)[:, 0]


def load_qick_iq_arrays(dataset: Any) -> Mapping[str, Any]:
    """Load split or legacy packed IQ trace arrays and derived quantities."""
    metadata = json.loads(dataset.get_metadata("qick_experiment_json"))
    layout = metadata["measurement_layout"]
    expected_shape = tuple(int(value) for value in layout["iq_shape"])
    if len(expected_shape) != 4 or expected_shape[-1] != 2:
        raise ValueError("stored IQ shape must be (point, repetition, sample, 2)")

    trace_count = expected_shape[0] * expected_shape[1]
    parameter_names = {parameter.name for parameter in dataset.get_parameters()}
    storage_mode = normalize_iq_storage_mode(
        layout.get(
            "iq_storage_mode",
            (
                IQ_STORAGE_MEAN_IQ
                if {I_MEAN_PARAMETER, Q_MEAN_PARAMETER}.issubset(parameter_names)
                else IQ_STORAGE_FULL_TRACES
            ),
        )
    )
    if {I_MEAN_PARAMETER, Q_MEAN_PARAMETER}.issubset(parameter_names):
        i_parameter_data = dataset.get_parameter_data(I_MEAN_PARAMETER)
        q_parameter_data = dataset.get_parameter_data(Q_MEAN_PARAMETER)
        trace_data = i_parameter_data[I_MEAN_PARAMETER]
        flat_i = np.asarray(trace_data[I_MEAN_PARAMETER]).reshape(-1)
        flat_q = np.asarray(
            q_parameter_data[Q_MEAN_PARAMETER][Q_MEAN_PARAMETER]
        ).reshape(-1)
        expected_flat_shape = (trace_count,)
        if (
            flat_i.shape != expected_flat_shape
            or flat_q.shape != expected_flat_shape
        ):
            raise ValueError(
                "stored mean I/Q arrays have shapes "
                f"{flat_i.shape} and {flat_q.shape}, expected "
                f"{expected_flat_shape}"
            )
        iq = np.stack((flat_i, flat_q), axis=-1).reshape(expected_shape)
    elif {I_TRACE_PARAMETER, Q_TRACE_PARAMETER}.issubset(parameter_names):
        i_parameter_data = dataset.get_parameter_data(I_TRACE_PARAMETER)
        q_parameter_data = dataset.get_parameter_data(Q_TRACE_PARAMETER)
        trace_data = i_parameter_data[I_TRACE_PARAMETER]
        flat_i = np.asarray(trace_data[I_TRACE_PARAMETER])
        flat_q = np.asarray(
            q_parameter_data[Q_TRACE_PARAMETER][Q_TRACE_PARAMETER]
        )
        expected_flat_shape = (trace_count, expected_shape[2])
        if (
            flat_i.shape != expected_flat_shape
            or flat_q.shape != expected_flat_shape
        ):
            raise ValueError(
                "stored split IQ arrays have shapes "
                f"{flat_i.shape} and {flat_q.shape}, expected "
                f"{expected_flat_shape}"
            )
        iq = np.stack((flat_i, flat_q), axis=-1).reshape(expected_shape)
    elif IQ_TRACE_PARAMETER in parameter_names:
        parameter_data = dataset.get_parameter_data(IQ_TRACE_PARAMETER)
        trace_data = parameter_data[IQ_TRACE_PARAMETER]
        flat_iq = np.asarray(trace_data[IQ_TRACE_PARAMETER])
        expected_flat_shape = (trace_count, expected_shape[2], 2)
        if flat_iq.shape != expected_flat_shape:
            raise ValueError(
                f"stored IQ arrays have shape {flat_iq.shape}, expected "
                f"{expected_flat_shape}"
            )
        iq = flat_iq.reshape(expected_shape)
    else:
        raise ValueError("dataset does not contain supported IQ trace storage")

    i_values = iq[..., 0]
    q_values = iq[..., 1]
    sample_index_parameter = layout.get(
        "sample_index_parameter",
        SAMPLE_INDEX_PARAMETER,
    )
    if sample_index_parameter in trace_data:
        flat_sample_index = np.asarray(trace_data[sample_index_parameter])
        expected_index_shape = (trace_count, expected_shape[2])
        if flat_sample_index.shape != expected_index_shape:
            raise ValueError(
                f"stored sample-index arrays have shape {flat_sample_index.shape}, "
                f"expected {expected_index_shape}"
            )
        sample_index = flat_sample_index[0].astype(np.int64, copy=False)
        if not np.all(flat_sample_index == sample_index[None, :]):
            raise ValueError("stored sample-index axes are inconsistent between traces")
    else:
        # Compatibility with v1/v2 datasets, which omitted the array axis.
        sample_index = np.arange(expected_shape[2], dtype=np.int64)
    sample_period_us = float(layout["sample_period_us"])

    sweep_coordinates = {}
    for axis in layout.get("sweep_axes", []):
        parameter_name = axis["parameter"]
        sweep_coordinates[parameter_name] = _first_value_per_trace(
            trace_data[parameter_name],
            trace_count,
        ).reshape(expected_shape[0], expected_shape[1])
    if "repetition_index" in trace_data:
        repetitions = _first_value_per_trace(
            trace_data["repetition_index"],
            trace_count,
        ).astype(np.int64).reshape(expected_shape[0], expected_shape[1])
    else:
        repetitions = np.zeros(expected_shape[:2], dtype=np.int64)

    return {
        "iq": iq,
        "i": i_values,
        "q": q_values,
        "magnitude": np.hypot(i_values.astype(float), q_values.astype(float)),
        "phase_deg": np.degrees(np.arctan2(q_values, i_values)),
        "sample_index": sample_index,
        "time_us": sample_index * sample_period_us,
        "repetition_index": repetitions,
        "sweep_coordinates": sweep_coordinates,
        # Compatibility alias; inspect measurement_layout.sweep_axes[*].unit
        # before assuming every coordinate is a voltage.
        "sweep_coordinates_mv": sweep_coordinates,
        "iq_unit": str(layout.get("iq_unit", "ADC units")),
        "measurement_mode": str(layout.get("measurement_mode", "raw_iq")),
        "storage_mode": storage_mode,
        "source_repetition_count": int(
            layout.get("source_repetition_count", expected_shape[1])
        ),
        "source_sample_count": int(
            layout.get("source_sample_count", expected_shape[2])
        ),
        "metadata": metadata,
    }


def load_qick_raw_int64_arrays(dataset, *, shape=None):
    """Load exact IQ64 arrays, including all pre-average repetitions.

    Pass the ``raw_iq_shape`` from the run's acquisition metadata to restore
    the original (point, repetition, sample, IQ) shape. Without it the result
    is a flat (sample, IQ) array. No floating conversion is performed.
    """
    lanes = []
    for name in ("i_raw_int64", "q_raw_int64"):
        values = np.asarray(dataset.get_parameter_data(name)[name][name])
        if values.dtype == object:
            values = np.concatenate([np.asarray(row).reshape(-1) for row in values])
        if values.dtype != np.dtype("int64"):
            raise RuntimeError("Stored raw IQ is not signed int64")
        lanes.append(values.reshape(-1))
    result = np.stack(lanes, axis=-1)
    return result if shape is None else result.reshape(tuple(shape))


def _measurement_iq_values(
    iq: Any,
    rf_settings: Mapping[str, Any],
) -> Tuple[np.ndarray, str, str, Mapping[str, Any]]:
    """Apply the selected readout-domain representation before storage."""
    raw_iq = np.asarray(iq)
    readout_details = rf_settings.get("readout_details", {})
    if not isinstance(readout_details, Mapping):
        readout_details = {}
    representation = str(
        readout_details.get("measurement_representation", "auto")
    )
    if representation == "auto":
        representation = (
            "current"
            if bool(readout_details.get("dc_measure_mode", False))
            else (
                "voltage"
                if bool(
                    readout_details.get(
                        "dc_voltage_calibration_enabled",
                        False,
                    )
                )
                else "adc"
            )
        )
    if representation not in {"adc", "voltage", "current"}:
        raise ValueError(
            "readout measurement representation must be adc, voltage, or current"
        )
    calibration_enabled = bool(
        readout_details.get("dc_voltage_calibration_enabled", False)
    )
    if representation == "adc":
        return raw_iq, "ADC units", "raw_iq", {
            "adc_to_voltage": "not_applied",
            "voltage_to_current": "not_applied",
        }
    if readout_details.get("board_type") != "DC_In":
        raise ValueError("DC measure mode requires a DC_In readout")
    calibration = None
    calibration_metadata = {}
    if calibration_enabled:
        calibration = load_dc_voltage_calibration(
            readout_details.get("dc_voltage_calibration_database_path", ""),
            readout_ch=int(readout_details.get("ro_ch", 0)),
            input_dc_gain_db=float(
                readout_details.get(
                    "commanded_dc_gain_db",
                    readout_details.get("requested_dc_gain_db", 0.0),
                )
            ),
            run_id=int(readout_details.get("dc_voltage_calibration_run_id", 0)),
        )
        calibration_metadata = {
            "dc_voltage_calibration_run_id": int(calibration.run_id),
            "dc_voltage_calibration_database_path": str(
                calibration.database_path
            ),
            "dc_voltage_calibration_r_squared": float(
                calibration.r_squared
            ),
            "dc_voltage_calibration_formula": calibration.as_dict()["formula"],
        }
    voltage_iq = adc_iq_to_voltage(raw_iq, calibration=calibration)
    if representation == "voltage":
        return voltage_iq, "V", "dc_voltage_iq", {
            "adc_to_voltage": (
                "fitted_scalar_adc_i" if calibration is not None else "identity"
            ),
            "voltage_to_current": "not_applied",
            **calibration_metadata,
        }
    gain_v_per_a = float(readout_details.get("dc_measure_gain_v_per_a", 1.0))
    current_iq = dc_iq_to_current(
        raw_iq,
        gain_v_per_a,
        calibration=calibration,
    )
    return current_iq, "A", "dc_current_iq", {
        "adc_to_voltage": (
            "fitted_scalar_adc_i" if calibration is not None else "identity"
        ),
        "voltage_to_current": "current_a = voltage_v / gain_v_per_a",
        "gain_v_per_a": gain_v_per_a,
        **calibration_metadata,
    }


def measurement_iq_values(
    iq: Any,
    rf_settings: Mapping[str, Any],
) -> Tuple[np.ndarray, str, str, Mapping[str, Any]]:
    """Return the same calibrated I/Q representation used for QCoDeS storage."""
    return _measurement_iq_values(iq, rf_settings)


def store_qick_result(
    ddr_result: Any,
    *,
    run_config: QcodesRunConfig,
    connection_config: QickConnectionConfig,
    program_summary: Mapping[str, Any],
    gui_settings: Mapping[str, Any],
    rf_settings: Mapping[str, Any],
    progress_callback: Optional[ProgressCallback] = None,
    progress_start: int = 65,
    progress_end: int = 99,
    batch_rows: int = DEFAULT_QCODES_BATCH_ROWS,
    iq_storage_mode: str = DEFAULT_IQ_STORAGE_MODE,
    cancel_check: Optional[CancellationCheck] = None,
) -> Tuple[Any, int]:
    """Store full repetition traces or one mean I/Q pair per sweep point."""
    try:
        from qcodes import (
            Measurement,
            Parameter,
            Station,
            initialise_or_create_database_at,
            load_by_guid,
            load_or_create_experiment,
        )
    except ImportError as exc:
        raise RuntimeError(
            "QCoDeS is required to save experiments; install qcodes==0.58.0"
        ) from exc

    _check_cancel(cancel_check)
    iq_storage_mode = normalize_iq_storage_mode(iq_storage_mode)
    raw_iq = np.asarray(ddr_result.iq)
    raw_scale_log2 = int(getattr(ddr_result, "iq_scale_log2", 0))
    is_iq64 = raw_scale_log2 != 0
    if is_iq64 and raw_iq.dtype != np.dtype("int64"):
        raise RuntimeError("IQ64 capture must retain signed-int64 raw data")
    # Mean-only storage must not persist the pre-average IQ64 traces either.
    store_raw_int64 = is_iq64 and iq_storage_mode == IQ_STORAGE_FULL_TRACES
    iq, iq_unit, measurement_mode, measurement_conversion = (
        _measurement_iq_values(result_iq_in_input_units(ddr_result), rf_settings)
    )
    _check_cancel(cancel_check)
    if iq.ndim != 4 or iq.shape[-1] != 2:
        raise ValueError("DDR IQ must have shape (point, repetition, sample, 2)")
    if isinstance(batch_rows, bool) or int(batch_rows) < 1:
        raise ValueError("batch_rows must be a positive integer")
    batch_rows = int(batch_rows)
    progress_start = int(progress_start)
    progress_end = int(progress_end)
    if not 0 <= progress_start <= progress_end <= 100:
        raise ValueError("progress range must satisfy 0 <= start <= end <= 100")
    point_count, repetition_count, sample_count, _ = iq.shape
    total_rows = point_count * repetition_count * sample_count
    if total_rows < 1:
        raise ValueError("DDR IQ result contains no samples")

    stored_gui_settings = dict(gui_settings)
    qick_settings = stored_gui_settings.get("qick", {})
    if not isinstance(qick_settings, Mapping):
        raise TypeError("gui_settings['qick'] must be a mapping")
    stored_qick_settings = dict(qick_settings)
    stored_qick_settings["iq_storage_mode"] = iq_storage_mode
    stored_gui_settings["qick"] = stored_qick_settings
    awg_vertices = stored_gui_settings.pop("awg_waveform_vertices", {})
    awg_recipe = stored_gui_settings.get("awg_waveform_recipe", {})
    vertex_data = _coerce_awg_vertex_data(
        awg_vertices,
        point_count=point_count,
    )

    _emit_progress(progress_callback, progress_start, "Preparing QCoDeS database")
    sweep_axes = tuple(ddr_result.sweep_axes)
    coordinates = _sweep_coordinates(ddr_result)
    if not sweep_axes and point_count != 1:
        raise ValueError(
            "multiple DDR sweep points require at least one named sweep axis"
        )
    full_scale_mv = _full_scale_mv(stored_gui_settings)
    coordinates_display = coordinates.copy()
    for axis_index, axis in enumerate(sweep_axes):
        _quantity, _unit, scale = _sweep_axis_display(
            axis,
            full_scale_mv,
        )
        coordinates_display[:, axis_index] *= scale
    database_path = run_config.resolved_database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)
    staging_directory, local_database_path = _prepare_local_database(
        database_path,
        cancel_check=cancel_check,
    )
    initialise_or_create_database_at(str(local_database_path))
    experiment = load_or_create_experiment(
        run_config.experiment_name,
        run_config.sample_name,
    )
    measurement = Measurement(exp=experiment, station=Station())

    setpoint_parameters = []
    sweep_parameters = []
    sweep_parameter_names = _sweep_parameter_names(sweep_axes)
    for axis, parameter_name in zip(sweep_axes, sweep_parameter_names):
        quantity, unit, _scale = _sweep_axis_display(
            axis,
            full_scale_mv,
        )
        parameter = Parameter(
            parameter_name,
            label=f"{axis.output_name} / {axis.segment_name} {quantity}",
            unit=unit,
        )
        sweep_parameters.append(parameter)
        setpoint_parameters.append(parameter)
    for parameter in setpoint_parameters:
        measurement.register_parameter(parameter)
    repetition_index = None
    sample_index = None
    i_trace = None
    q_trace = None
    i_mean = None
    q_mean = None
    if iq_storage_mode == IQ_STORAGE_FULL_TRACES:
        repetition_index = Parameter(
            "repetition_index",
            label="Repetition",
            unit="",
        )
        sample_index = Parameter(
            SAMPLE_INDEX_PARAMETER,
            label="Sample index",
            unit="",
        )
        measurement.register_parameter(repetition_index)
        measurement.register_parameter(sample_index, paramtype="array")
        trace_setpoints = (*setpoint_parameters, repetition_index, sample_index)
        i_trace = Parameter(
            I_TRACE_PARAMETER,
            label="I current trace" if iq_unit == "A" else "I trace",
            unit=iq_unit,
        )
        q_trace = Parameter(
            Q_TRACE_PARAMETER,
            label="Q current trace" if iq_unit == "A" else "Q trace",
            unit=iq_unit,
        )
        for parameter in (i_trace, q_trace):
            measurement.register_parameter(
                parameter,
                # Plottr assigns the final dimension to the x-axis by default.
                setpoints=trace_setpoints,
                paramtype="array",
            )
    else:
        i_mean = Parameter(
            I_MEAN_PARAMETER,
            label="Mean I current" if iq_unit == "A" else "Mean I",
            unit=iq_unit,
        )
        q_mean = Parameter(
            Q_MEAN_PARAMETER,
            label="Mean Q current" if iq_unit == "A" else "Mean Q",
            unit=iq_unit,
        )
        for parameter in (i_mean, q_mean):
            if setpoint_parameters:
                measurement.register_parameter(
                    parameter,
                    setpoints=tuple(setpoint_parameters),
                )
            else:
                measurement.register_parameter(parameter)

    raw_parameters = []
    if store_raw_int64:
        for lane in ("i", "q"):
            parameter = Parameter(f"{lane}_raw_int64", label=f"Raw {lane.upper()} integer", unit="integer codes")
            measurement.register_parameter(parameter, setpoints=tuple(setpoint_parameters), paramtype="array")
            raw_parameters.append(parameter)

    vertex_parameters = []
    if vertex_data is not None:
        output_names, vertex_time_us, _virtual_mv, _physical_mv = vertex_data
        used_prefixes = set()
        for output_index, output_name in enumerate(output_names):
            base_prefix = _qcodes_identifier(output_name)
            prefix = base_prefix
            suffix = 2
            while prefix in used_prefixes:
                prefix = f"{base_prefix}_{suffix}"
                suffix += 1
            used_prefixes.add(prefix)
            time_parameter = Parameter(
                f"{prefix}_vertex_time_us",
                label=f"{output_name} AWG vertex time",
                unit="us",
            )
            measurement.register_parameter(
                time_parameter,
                paramtype="array",
            )
            # Keep time last so Plottr opens a waveform against time.
            vertex_setpoints = (*sweep_parameters, time_parameter)
            virtual_parameter = Parameter(
                f"{prefix}_virtual_vertices_mv",
                label=f"{output_name} virtual AWG waveform vertices",
                unit="mV",
            )
            physical_parameter = Parameter(
                f"{prefix}_physical_vertices_mv",
                label=f"{output_name} physical AWG waveform vertices",
                unit="mV",
            )
            for parameter in (virtual_parameter, physical_parameter):
                measurement.register_parameter(
                    parameter,
                    setpoints=vertex_setpoints,
                    paramtype="array",
                )
            vertex_parameters.append({
                "output_index": output_index,
                "output_name": output_name,
                "time": time_parameter,
                "virtual": virtual_parameter,
                "physical": physical_parameter,
                "time_values": np.ascontiguousarray(
                    vertex_time_us,
                    dtype=float,
                ),
            })

    sweep_axis_metadata = []
    for axis, parameter in zip(sweep_axes, sweep_parameters):
        quantity, unit, scale = _sweep_axis_display(axis, full_scale_mv)
        axis_metadata = {
            "parameter": parameter.name,
            "output_name": axis.output_name,
            "segment_name": axis.segment_name,
            "axis_kind": getattr(axis, "axis_kind", "amplitude"),
            "quantity": quantity,
            "unit": unit,
            "start": float(axis.start) * scale,
            "stop": float(axis.stop) * scale,
            "count": int(axis.count),
        }
        axis_kind = getattr(axis, "axis_kind", "amplitude")
        if axis_kind.startswith("square_"):
            axis_metadata.update({"gen_ch": int(axis.gen_ch), "square_parameter": axis.parameter,
                                  "execution": "tProcessor hardware sweep with exact DMEM words"})
        elif axis_kind in {"rf_template_n", "rf_template_tau"}:
            axis_metadata.update({
                "parameter_name": str(axis.parameter_name),
                "execution": (
                    "host software sweep; compile and acquire once per point"
                ),
            })
        elif axis_kind == "rf_duration":
            axis_metadata.update({
                "duration_start_us": float(axis.start),
                "duration_stop_us": float(axis.stop),
                "segment_length_mode": axis.segment_length_mode,
            })
        elif axis_kind == "rf_frequency":
            axis_metadata.update({
                "frequency_start_mhz": float(axis.start),
                "frequency_stop_mhz": float(axis.stop),
                "execution": "tProcessor DMEM frequency-word sweep",
            })
        elif axis_kind == "rf_power":
            axis_metadata.update({
                "power_start_dbm": float(axis.start),
                "power_stop_dbm": float(axis.stop),
                "execution": (
                    "tProcessor DMEM gain-code sweep from RF calibration"
                ),
            })
        elif axis_kind == "ramp_duration":
            axis_metadata.update({
                "duration_start_us": float(axis.start),
                "duration_stop_us": float(axis.stop),
                "rate_semantics": (
                    "The following SET is the target; the signed RAMP step is "
                    "derived for every duration and voltage-sweep coordinate."
                ),
            })
        elif axis_kind == "hold_duration":
            axis_metadata.update({
                "duration_start_us": float(axis.start),
                "duration_stop_us": float(axis.stop),
                "timing_semantics": (
                    "The selected SET level is held for this duration; all "
                    "later AWG, RF, and DDR events move with the sweep."
                ),
            })
        else:
            axis_metadata.update({
                "normalized_start": float(axis.start),
                "normalized_stop": float(axis.stop),
                "voltage_start_mv": float(axis.start) * full_scale_mv,
                "voltage_stop_mv": float(axis.stop) * full_scale_mv,
            })
        sweep_axis_metadata.append(axis_metadata)
    setpoint_meanings = {
        parameter.name: _sweep_axis_meaning(axis)
        for axis, parameter in zip(sweep_axes, sweep_parameters)
    }
    sample_period_us = 1_000_000.0 / run_config.sample_rate_hz
    mean_iq_values = None
    if iq_storage_mode == IQ_STORAGE_FULL_TRACES:
        setpoint_meanings.update({
            SAMPLE_INDEX_PARAMETER: (
                "Zero-based index of each sample within the captured I/Q trace."
            ),
            "repetition_index": (
                "Zero-based repetition within one sweep coordinate."
            ),
        })
        sample_index_values = np.arange(sample_count, dtype=np.int32)
        measurement_layout = {
            "iq_shape": list(iq.shape),
            "iq_trace_parameters": {
                "i": I_TRACE_PARAMETER,
                "q": Q_TRACE_PARAMETER,
            },
            "iq_trace_shape": [sample_count],
            "iq_trace_dtypes": {
                "i": str(iq[..., 0].dtype),
                "q": str(iq[..., 1].dtype),
            },
            "storage_format": "qcodes_split_array_per_trace_v3",
            "trace_count": point_count * repetition_count,
            "sql_rows_per_trace": 2,
            "sample_index_parameter": SAMPLE_INDEX_PARAMETER,
            "row_order": (
                "sweep_axes,repetition" if sweep_axes else "repetition"
            ),
            "time_reconstruction": (
                f"{SAMPLE_INDEX_PARAMETER} is stored as the array setpoint for "
                "every I/Q trace; time_us = sample_index * sample_period_us."
            ),
            "derived_quantities": {
                "magnitude": "hypot(i_trace, q_trace)",
                "phase_deg": "degrees(arctan2(q_trace, i_trace))",
            },
        }
    else:
        mean_iq_values = np.mean(iq, axis=(1, 2), dtype=np.float64)
        sample_index_values = None
        measurement_layout = {
            # Keep the common loader contract while making it explicit that
            # repetition and sample axes were reduced before persistence.
            "iq_shape": [point_count, 1, 1, 2],
            "iq_mean_parameters": {
                "i": I_MEAN_PARAMETER,
                "q": Q_MEAN_PARAMETER,
            },
            "iq_mean_dtype": str(mean_iq_values.dtype),
            "storage_format": "qcodes_mean_iq_per_point_v1",
            "stored_point_count": point_count,
            "sql_rows_per_point": 2,
            "row_order": "sweep_axes" if sweep_axes else "single_point",
            "time_reconstruction": (
                "No time trace is stored. Each value is the arithmetic mean "
                "over all acquired repetitions and samples for one sweep point."
            ),
            "derived_quantities": {
                "magnitude": "hypot(i_mean, q_mean)",
                "phase_deg": "degrees(arctan2(q_mean, i_mean))",
            },
        }
    measurement_layout.update({
        "iq_storage_mode": iq_storage_mode,
        "source_iq_shape": list(iq.shape),
        "source_repetition_count": repetition_count,
        "source_sample_count": sample_count,
        "raw_iq_dtype": str(raw_iq.dtype),
        "raw_iq_scale_log2": raw_scale_log2,
        "raw_iq_shape": list(raw_iq.shape),
        "raw_iq_parameters": [p.name for p in raw_parameters],
        "raw_iq_storage": (
            "omitted_mean_iq" if iq_storage_mode == IQ_STORAGE_MEAN_IQ
            else "exact_int64_arrays" if store_raw_int64 else "legacy"
        ),
        "iq_unit": iq_unit,
        "measurement_mode": measurement_mode,
        "measurement_conversion": dict(measurement_conversion),
        "cartesian_point_count": point_count,
        "sample_rate_hz": run_config.sample_rate_hz,
        "sample_period_us": sample_period_us,
        "sweep_axes": sweep_axis_metadata,
        "setpoint_meanings": setpoint_meanings,
    })
    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "qick_connection": asdict(connection_config),
        "qcodes_run": {
            **asdict(run_config),
            "database_path": str(database_path),
            "write_mode": "local_staging_then_sqlite_backup",
        },
        "gui_settings": stored_gui_settings,
        "awg_waveform_metadata": {
            "mode": normalize_awg_metadata_mode(
                stored_gui_settings.get("qick", {}).get(
                    "awg_metadata_mode",
                    DEFAULT_AWG_METADATA_MODE,
                )
            ),
            "recipe_schema": (
                awg_recipe.get("schema")
                if isinstance(awg_recipe, Mapping)
                else None
            ),
            "expanded_vertices_stored": vertex_data is not None,
        },
        "program_summary": program_summary,
        "rf_settings_actual": rf_settings,
        "measurement_layout": measurement_layout,
    }
    if vertex_data is not None:
        output_names, vertex_time_us, virtual_mv, _physical_mv = vertex_data
        parameter_by_output = {
            entry["output_name"]: entry for entry in vertex_parameters
        }
        common_vertex_times = bool(
            np.all(vertex_time_us == vertex_time_us[0])
        )
        vertex_channels = {}
        for output_name in output_names:
            channel = {
                "time_parameter": parameter_by_output[output_name][
                    "time"
                ].name,
                "virtual_parameter": parameter_by_output[output_name][
                    "virtual"
                ].name,
                "physical_parameter": parameter_by_output[output_name][
                    "physical"
                ].name,
                "vertex_count": int(vertex_time_us.shape[1]),
            }
            if common_vertex_times:
                channel["time_us"] = vertex_time_us[0].tolist()
            else:
                channel["time_us_by_sweep_point"] = (
                    vertex_time_us.tolist()
                )
            vertex_channels[output_name] = channel
        metadata["measurement_layout"].update({
            "awg_vertex_shape": list(virtual_mv.shape),
            "awg_vertex_storage": "per_channel_timed_qcodes_array_v2",
            "awg_vertex_row_order": "one array per sweep point and channel",
            "awg_output_names": list(output_names),
            "awg_vertex_time_reference": "start of each pulse sequence repetition",
            "awg_vertex_channels": vertex_channels,
        })

    row_count = 0
    cancellation_error = None

    def cancellation_requested() -> bool:
        nonlocal cancellation_error
        if cancellation_error is not None:
            return True
        try:
            _check_cancel(cancel_check)
        except ExperimentCancelled as exc:
            cancellation_error = exc
            return True
        return False

    with measurement.run(
        write_in_background=False,
        in_memory_cache=False,
    ) as datasaver:
        dataset = datasaver.dataset
        dataset.add_metadata("qick_experiment_json", _json_text(metadata))
        dataset.add_metadata(
            "output_waveforms_json",
            _json_text(
                stored_gui_settings.get("waveforms")
                or stored_gui_settings.get("awg", {}).get("outputs", [])
            ),
        )
        dataset.add_metadata(
            "cross_capacitance_json",
            _json_text(
                stored_gui_settings.get("awg", {}).get("cross_capacitance", [])
            ),
        )
        if awg_recipe:
            dataset.add_metadata(
                "awg_waveform_recipe_json",
                _json_text(awg_recipe),
            )
        dataset.add_metadata(
            "rf_configuration_json",
            _json_text({
                "outputs": stored_gui_settings.get("rf_outputs", []),
                "readout": stored_gui_settings.get("rf_readout", {}),
            }),
        )
        if run_config.notes:
            dataset.add_metadata("experiment_notes", run_config.notes)

        if vertex_data is not None:
            output_names, _vertex_time_us, virtual_mv, physical_mv = vertex_data
            for point_index in range(point_count):
                if cancellation_requested():
                    break
                coordinate_results = [
                    (
                        parameter,
                        float(
                            coordinates_display[point_index, axis_index]
                        ),
                    )
                    for axis_index, parameter in enumerate(sweep_parameters)
                ]
                channel_results = []
                for entry in vertex_parameters:
                    output_index = entry["output_index"]
                    channel_results.extend((
                        (
                            entry["time"],
                            np.ascontiguousarray(
                                entry["time_values"][point_index],
                                dtype=float,
                            ),
                        ),
                        (
                            entry["virtual"],
                            np.ascontiguousarray(
                                virtual_mv[point_index, output_index],
                                dtype=float,
                            ),
                        ),
                        (
                            entry["physical"],
                            np.ascontiguousarray(
                                physical_mv[point_index, output_index],
                                dtype=float,
                            ),
                        ),
                    ))
                datasaver.add_result(
                    *coordinate_results,
                    *channel_results,
                )
            if cancellation_error is None:
                datasaver.flush_data_to_database()
                _emit_progress(
                    progress_callback,
                    progress_start,
                    f"Saved per-channel AWG vertex arrays for "
                    f"{point_count:,} sweep points",
                )

        data_progress_end = max(progress_start, progress_end - 4)
        if iq_storage_mode == IQ_STORAGE_FULL_TRACES:
            trace_count = point_count * repetition_count
            traces_per_flush = max(1, batch_rows // sample_count)
            traces_written = 0
            for point_index in range(point_count):
                if cancellation_requested():
                    break
                coordinate_results = [
                    (
                        parameter,
                        float(coordinates_display[point_index, axis_index]),
                    )
                    for axis_index, parameter in enumerate(sweep_parameters)
                ]
                for repetition in range(repetition_count):
                    if cancellation_requested():
                        break
                    raw_results = [
                        (parameter, np.ascontiguousarray(raw_iq[point_index, repetition, :, lane]))
                        for lane, parameter in enumerate(raw_parameters)
                    ]
                    datasaver.add_result(
                        *coordinate_results,
                        (repetition_index, repetition),
                        (sample_index, sample_index_values),
                        *raw_results,
                        (
                            i_trace,
                            np.ascontiguousarray(
                                iq[point_index, repetition, :, 0]
                            ),
                        ),
                        (
                            q_trace,
                            np.ascontiguousarray(
                                iq[point_index, repetition, :, 1]
                            ),
                        ),
                    )
                    traces_written += 1
                    row_count += sample_count
                    if (
                        traces_written % traces_per_flush == 0
                        or traces_written == trace_count
                    ):
                        datasaver.flush_data_to_database()
                        fraction = traces_written / trace_count
                        percent = progress_start + round(
                            fraction * (data_progress_end - progress_start)
                        )
                        _emit_progress(
                            progress_callback,
                            percent,
                            f"Saving split I/Q trace arrays {traces_written:,}/"
                            f"{trace_count:,} "
                            f"({row_count:,}/{total_rows:,} samples)",
                        )
        else:
            points_per_flush = max(1, batch_rows // 2)
            for point_index in range(point_count):
                if cancellation_requested():
                    break
                coordinate_results = [
                    (
                        parameter,
                        float(coordinates_display[point_index, axis_index]),
                    )
                    for axis_index, parameter in enumerate(sweep_parameters)
                ]
                datasaver.add_result(
                    *coordinate_results,
                    (i_mean, float(mean_iq_values[point_index, 0])),
                    (q_mean, float(mean_iq_values[point_index, 1])),
                )
                row_count += 1
                if (
                    row_count % points_per_flush == 0
                    or row_count == point_count
                ):
                    datasaver.flush_data_to_database()
                    percent = progress_start + round(
                        (row_count / point_count)
                        * (data_progress_end - progress_start)
                    )
                    _emit_progress(
                        progress_callback,
                        percent,
                        f"Saving mean I/Q points {row_count:,}/{point_count:,}",
                    )

    if cancellation_error is not None:
        try:
            dataset.conn.close()
        finally:
            shutil.rmtree(staging_directory, ignore_errors=True)
        raise cancellation_error

    local_guid = str(dataset.guid)
    dataset.conn.close()
    try:
        _check_cancel(cancel_check)
    except ExperimentCancelled:
        shutil.rmtree(staging_directory, ignore_errors=True)
        raise
    _emit_progress(
        progress_callback,
        max(progress_start, progress_end - 3),
        "Checkpointing local QCoDeS database",
    )
    _checkpoint_sqlite_database(local_database_path)
    try:
        _check_cancel(cancel_check)
    except ExperimentCancelled:
        shutil.rmtree(staging_directory, ignore_errors=True)
        raise
    _emit_progress(
        progress_callback,
        max(progress_start, progress_end - 2),
        "Copying completed QCoDeS database to the configured path",
    )
    _publish_local_database(local_database_path, database_path)
    initialise_or_create_database_at(str(database_path))
    dataset = load_by_guid(local_guid)
    shutil.rmtree(staging_directory)
    _emit_progress(
        progress_callback,
        progress_end,
        "QCoDeS database copied and WAL checkpoint completed",
    )
    return dataset, row_count


def run_qick_qcodes_experiment(
    *,
    connection_config: QickConnectionConfig,
    run_config: QcodesRunConfig,
    sequence: Any,
    awg_channels: Sequence[int],
    repetitions_per_sweep: int,
    rf_specs: Sequence[QickRfPulseSpec],
    readout_spec: QickDdrReadoutSpec,
    gui_settings: Mapping[str, Any],
    iq_storage_mode: str = DEFAULT_IQ_STORAGE_MODE,
    compile_validation_mode: str = DEFAULT_COMPILE_VALIDATION_MODE,
    progress: bool = False,
    connector: Optional[Callable[..., Tuple[Any, Any]]] = None,
    progress_callback: Optional[ProgressCallback] = None,
    event_callback: Optional[ExperimentEventCallback] = None,
    cancel_check: Optional[CancellationCheck] = None,
) -> StoredQickExperiment:
    """Connect, execute, acquire FIR DDR IQ, and commit one QCoDeS run."""
    _check_cancel(cancel_check)
    _emit_progress(progress_callback, 0, "Starting QICK experiment")
    _emit_progress(progress_callback, 2, "Connecting to QICK Pyro server")
    _emit_experiment_event(
        event_callback,
        "connection",
        "started",
        "Connecting to QICK Pyro server",
    )
    soc, soccfg = connect_qick(connection_config, connector=connector)
    _check_cancel(cancel_check)
    _emit_experiment_event(
        event_callback,
        "connection",
        "completed",
        "QICK Pyro connection completed",
    )
    fir_profile = resolve_fir_ddr_profile(
        soccfg,
        context="QCoDeS experiment",
    )
    if readout_spec.fpga_trigger_delay_samples is not None:
        selected_trigger_delay = readout_spec.fpga_trigger_delay_samples
    else:
        selected_trigger_delay = fir_profile.selected_trigger_delay_value(
            readout_spec.fpga_trigger_delay_us
        )
    effective_run_config = replace(
        run_config,
        sample_rate_hz=fir_profile.sample_rate_hz,
    )
    stored_gui_settings = dict(gui_settings)
    qick_settings = gui_settings.get("qick", {})
    if not isinstance(qick_settings, Mapping):
        raise TypeError("gui_settings['qick'] must be a mapping")
    stored_qick_settings = dict(qick_settings)
    stored_qick_settings.update({
        "fir_rate_profile": fir_profile.name,
        "fir_sample_rate_hz": fir_profile.sample_rate_hz,
        "fir_sample_period_us": fir_profile.sample_period_us,
        "fir_fpga_trigger_delay_samples": selected_trigger_delay,
        "fir_fpga_trigger_delay_units": fir_profile.trigger_delay_units,
        "fir_fpga_trigger_delay_us": fir_profile.trigger_delay_us_for(
            selected_trigger_delay
        ),
        "fir_software_warmup_compensation": (
            fir_profile.software_warmup_compensation
        ),
    })
    stored_gui_settings["qick"] = stored_qick_settings
    tproc_mhz = float(
        qick_settings.get("tproc_mhz", DEFAULT_QICK_TPROC_MHZ)
    )
    iq_storage_mode = normalize_iq_storage_mode(iq_storage_mode)
    stored_qick_settings["iq_storage_mode"] = iq_storage_mode
    metadata_mode = normalize_awg_metadata_mode(
        qick_settings.get("awg_metadata_mode", DEFAULT_AWG_METADATA_MODE)
    )
    stored_qick_settings["awg_metadata_mode"] = metadata_mode
    compile_validation_mode = normalize_compile_validation_mode(
        compile_validation_mode
    )
    stored_qick_settings["compile_validation_mode"] = compile_validation_mode
    software_bindings = _rf_software_sweep_bindings(rf_specs)
    software_coordinates = _software_sweep_coordinates(software_bindings)
    if software_bindings:
        stored_gui_settings["rf_predefined_software_sweep"] = {
            "execution": "host software sweep",
            "axes": [asdict(axis) for _index, axis in software_bindings],
            "coordinates": software_coordinates.tolist(),
            "program_count": int(software_coordinates.shape[0]),
        }
    fabric_mhz = float(qick_settings.get("fabric_mhz", 300.0))
    if hasattr(sequence, "waveform_vertices"):
        _check_cancel(cancel_check)
        full_scale_mv = float(
            qick_settings.get(
                "full_scale_mv",
                DEFAULT_QICK_FULL_SCALE_MV,
            )
        )
        _emit_progress(progress_callback, 4, "Preparing parametric AWG waveform recipe")
        _emit_experiment_event(
            event_callback,
            "awg_recipe",
            "started",
            "Preparing parametric AWG waveform recipe",
        )
        awg_recipe = dict(build_awg_waveform_recipe(
            sequence,
            fabric_mhz=fabric_mhz,
            full_scale_mv=full_scale_mv,
        ))
        if software_bindings:
            software_axes = [
                {
                    **asdict(axis),
                    "execution": "host software sweep",
                }
                for _index, axis in software_bindings
            ]
            awg_recipe["sweep_axes"] = (
                software_axes + list(awg_recipe["sweep_axes"])
            )
            awg_recipe["sweep_shape"] = (
                [int(axis.count) for _index, axis in software_bindings]
                + list(awg_recipe["sweep_shape"])
            )
            awg_recipe["point_count"] = int(
                awg_recipe["point_count"] * software_coordinates.shape[0]
            )
            awg_recipe["reconstruction"] += (
                " Predefined RF N/tau axes are host software sweeps; RF-driven "
                "SET extension timing is rebuilt for each coordinate."
            )
        stored_gui_settings["awg_waveform_recipe"] = awg_recipe
        _check_cancel(cancel_check)
        _emit_experiment_event(
            event_callback,
            "awg_recipe",
            "completed",
            "Parametric AWG waveform recipe prepared",
        )
        if metadata_mode == AWG_METADATA_MODE_EXPANDED and software_bindings:
            # Expanded AWG vertices would require one potentially very large
            # duplicate array per host RF point.  Preserve the exact compact
            # recipe and make this storage downgrade explicit in metadata.
            stored_gui_settings["awg_waveform_vertices_omitted"] = {
                "reason": (
                    "expanded AWG vertices are omitted for predefined RF "
                    "software sweeps; reconstruct from the compact recipe"
                ),
                "requested_mode": AWG_METADATA_MODE_EXPANDED,
            }
        elif metadata_mode == AWG_METADATA_MODE_EXPANDED:
            _emit_progress(progress_callback, 4, "Building expanded AWG vertices")
            _emit_experiment_event(
                event_callback,
                "awg_vertices",
                "started",
                "Building expanded AWG vertices",
            )
            stored_gui_settings["awg_waveform_vertices"] = build_awg_vertex_metadata(
                sequence,
                fabric_mhz=fabric_mhz,
                full_scale_mv=full_scale_mv,
                cancel_check=cancel_check,
            )
            _emit_experiment_event(
                event_callback,
                "awg_vertices",
                "completed",
                "Expanded AWG vertices built",
            )
    program, ddr_result, rf_settings = execute_qick_sequence(
        soc,
        soccfg,
        sequence,
        awg_channels=awg_channels,
        repetitions_per_sweep=repetitions_per_sweep,
        tproc_mhz=tproc_mhz,
        rf_specs=rf_specs,
        readout_spec=readout_spec,
        sequence_fabric_mhz=fabric_mhz,
        compile_validation_mode=compile_validation_mode,
        progress=progress,
        progress_callback=progress_callback,
        event_callback=event_callback,
        cancel_check=cancel_check,
    )
    _check_cancel(cancel_check)
    _emit_experiment_event(
        event_callback,
        "qcodes_save",
        "started",
        "Saving acquisition data to QCoDeS",
    )
    dataset, row_count = store_qick_result(
        ddr_result,
        run_config=effective_run_config,
        connection_config=connection_config,
        program_summary=program.summary(),
        gui_settings=stored_gui_settings,
        rf_settings=rf_settings,
        iq_storage_mode=iq_storage_mode,
        progress_callback=progress_callback,
        cancel_check=cancel_check,
    )
    _emit_experiment_event(
        event_callback,
        "qcodes_save",
        "completed",
        "QCoDeS database saved, checkpointed, and published",
    )
    _emit_progress(progress_callback, 100, "Experiment saved")
    return StoredQickExperiment(
        run_id=int(dataset.run_id),
        guid=str(dataset.guid),
        database_path=effective_run_config.resolved_database_path,
        row_count=row_count,
        dataset=dataset,
        program=program,
        ddr_result=ddr_result,
        rf_settings=rf_settings,
        iq_storage_mode=iq_storage_mode,
    )


__all__ = [
    "AWG_METADATA_MODE_EXPANDED",
    "AWG_METADATA_MODE_PARAMETRIC",
    "AWG_METADATA_MODES",
    "COMPILE_VALIDATION_BOUNDARY",
    "COMPILE_VALIDATION_FULL",
    "COMPILE_VALIDATION_MODES",
    "DEFAULT_COMPILE_VALIDATION_MODE",
    "DEFAULT_AWG_METADATA_MODE",
    "DEFAULT_IQ_STORAGE_MODE",
    "DEFAULT_QCODES_BATCH_ROWS",
    "CancellationCheck",
    "ExperimentCancelled",
    "ExperimentEventCallback",
    "I_TRACE_PARAMETER",
    "I_MEAN_PARAMETER",
    "IQ_TRACE_PARAMETER",
    "IQ_STORAGE_FULL_TRACES",
    "IQ_STORAGE_MEAN_IQ",
    "IQ_STORAGE_MODES",
    "Q_TRACE_PARAMETER",
    "Q_MEAN_PARAMETER",
    "QCODES_STAGING_ENV",
    "ProgressCallback",
    "QcodesRunConfig",
    "QickConnectionConfig",
    "SoftwareSweepProgramBundle",
    "StoredQickExperiment",
    "build_awg_vertex_record",
    "build_awg_vertex_metadata",
    "build_awg_waveform_recipe",
    "build_qick_program",
    "build_runtime_ddr_readout",
    "build_runtime_rf_pulses",
    "configure_rf_board",
    "configure_rf_output",
    "configure_rf_readout",
    "connect_qick",
    "describe_rf_output",
    "execute_qick_sequence",
    "load_qick_iq_arrays",
    "load_qick_raw_int64_arrays",
    "measurement_iq_values",
    "normalize_awg_metadata_mode",
    "normalize_iq_storage_mode",
    "normalize_compile_validation_mode",
    "run_qick_qcodes_experiment",
    "store_qick_result",
    "write_awg_vertex_metadata_jsonl",
]
