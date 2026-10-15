"""Bias-sweep measurement back end for DAC11001, SR860, and QICK ADC.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from math import atan2, ceil, hypot, isfinite, prod
from numbers import Integral, Real
from pathlib import Path
import time
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple

import numpy as np

try:
    from .fir_ddr_profile import resolve_fir_ddr_profile
    from .noise_acquisition import (
        NoiseAcquisitionConfig,
        build_noise_fir_program,
    )
    from .qick_qcodes_experiment import (
        QickConnectionConfig,
        configure_rf_board,
        connect_qick,
    )
except ImportError:
    from fir_ddr_profile import resolve_fir_ddr_profile
    from noise_acquisition import NoiseAcquisitionConfig, build_noise_fir_program
    from qick_qcodes_experiment import (
        QickConnectionConfig,
        configure_rf_board,
        connect_qick,
    )


BIAS_MEASUREMENT_SCHEMA = "qstl-qick-bias-measurement-v1"
BIAS_MEASUREMENT_KINDS = (
    "two_point", "gate", "wall_wall", "nested", "time_trace",
)
CURRENT_MEASUREMENT_MODES = ("sr860", "qick_adc")
BIAS_CHANNEL_COUNT = 8
BIAS_HARDWARE_MAX_V = 10.0
SR860_TIME_CONSTANTS_S = (
    1e-6, 3e-6, 10e-6, 30e-6, 100e-6, 300e-6,
    1e-3, 3e-3, 10e-3, 30e-3, 100e-3, 300e-3,
    1.0, 3.0, 10.0, 30.0, 100.0, 300.0,
)
SR860_CURRENT_SENSITIVITIES_A = (
    1e-15, 2e-15, 5e-15, 10e-15, 20e-15, 50e-15,
    100e-15, 200e-15, 500e-15, 1e-12, 2e-12, 5e-12,
    10e-12, 20e-12, 50e-12, 100e-12, 200e-12, 500e-12,
    1e-9, 2e-9, 5e-9, 10e-9, 20e-9, 50e-9,
    100e-9, 200e-9, 500e-9, 1e-6,
)
SR860_QUERY_PAUSE_S = 0.05
SR860_RECONNECT_PAUSE_S = 1.0
CANCEL_POLL_INTERVAL_S = 0.1


class BiasMeasurementCancelled(RuntimeError):
    """Raised at a safe boundary after a Bias stop request."""


def _check_cancel(cancel_check: Optional[Callable[[], None]]) -> None:
    if cancel_check is not None:
        cancel_check()


def _sleep_with_cancel(
    duration_s: float,
    *,
    sleeper: Callable[[float], None],
    cancel_check: Optional[Callable[[], None]],
) -> None:
    """Sleep in short intervals so a worker stop request remains responsive."""
    duration_s = max(0.0, float(duration_s))
    if duration_s == 0.0:
        _check_cancel(cancel_check)
        return
    if cancel_check is None:
        sleeper(duration_s)
        return
    remaining = duration_s
    while remaining > 0.0:
        _check_cancel(cancel_check)
        interval = min(CANCEL_POLL_INTERVAL_S, remaining)
        sleeper(interval)
        remaining -= interval
    _check_cancel(cancel_check)


def _is_visa_transport_error(exc: BaseException) -> bool:
    """Recognize PyVISA/SRS transport failures without importing either package."""
    error_type = type(exc)
    return (
        isinstance(exc, (TimeoutError, OSError))
        or (
            error_type.__name__ == "VisaIOError"
            and error_type.__module__.startswith("pyvisa")
        )
        or (
            error_type.__name__ in {
                "InstCommunicationError",
                "InstQueryError",
            }
            and error_type.__module__.startswith("srsgui")
        )
    )


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer")
    result = int(value)
    if result < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return result


def _deep_merge(base: Mapping[str, Any], update: Mapping[str, Any]) -> dict:
    result = dict(base)
    for key, value in update.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _common_defaults(experiment_name: str) -> dict:
    return {
        "database_path": str(Path.home() / "qick_bias_measurements.db"),
        "experiment_name": experiment_name,
        "sample_name": "BiasMeasurement",
        "notes": "",
        "current_mode": "sr860",
        "repetitions_per_point": 1,
        "settle_s": 0.01,
        "ramp_max_step_v": 0.001,
        "ramp_pause_s": 0.01,
        "restore_bias_after_run": True,
        "sr860": {
            "visa_address": "GPIB0::4::INSTR",
            "frequency_hz": 43.5371,
            "phase_deg": 0.0,
            "time_constant_s": 0.1,
            "filter_slope_db_oct": 24,
            "sensitivity_a": 100e-9,
            "sine_bias_v": 100e-6,
            "settle_time_constants": 3.0,
            "input_gain_ohm": 100e6,
        },
        "qick_adc": {
            "readout_ch": 0,
            "input_board_type": "DC_In",
            "nqz": 1,
            "fir_samples": 100,
            "readout_frequency_mhz": 0.0,
            "attenuation_db": 20.0,
            "dc_gain_db": 0.0,
            "filter_type": "bypass",
            "filter_cutoff_ghz": 2.5,
            "filter_bandwidth_ghz": 1.0,
            "margin_input_samples": 1024,
            "fpga_trigger_delay_us": None,
            "post_run_read_delay_seconds": 0.1,
            "adc_units_per_amp": 1.0,
        },
    }


def default_bias_measurement_settings() -> dict:
    """Return JSON-safe defaults for all Bias measurement tabs."""
    two_point = _common_defaults("QICK 2P bias sweep")
    two_point.update({
        "bias_start_v": 0.0,
        "bias_stop_v": 200e-6,
        "points": 101,
    })
    gate = _common_defaults("QICK gate-controlled sweep")
    gate.update({
        "gate_channels": [0],
        "gate_start_v": 0.0,
        "gate_stop_v": -0.7,
        "points_per_leg": 41,
        "loops": 1,
        "return_leg": True,
        "largest_loop_first": False,
        "restore_bias_after_run": False,
    })
    wall = _common_defaults("QICK wall-wall sweep")
    wall.update({
        "slow_channel": 0,
        "fast_channel": 1,
        "slow_start_v": -0.65,
        "slow_stop_v": -0.72,
        "slow_points": 41,
        "fast_start_v": -0.65,
        "fast_stop_v": -0.72,
        "fast_points": 41,
    })
    nested = _common_defaults("QICK general nested bias sweep")
    nested.update({
        "axes": [
            {
                "name": "outer",
                "channels": [2],
                "start_v": [-0.1],
                "stop_v": [0.1],
                "points": 11,
            },
            {
                "name": "inner_vector",
                "channels": [0, 1],
                "start_v": [-0.1, -0.1],
                "stop_v": [0.1, 0.1],
                "points": 11,
            },
        ],
    })
    time_trace = _common_defaults("QICK bias current time trace")
    time_trace.update({
        "samples": 1_000,
        "sample_interval_s": 0.1,
        "repetitions_per_point": 1,
        "restore_bias_after_run": False,
    })
    return {
        "two_point": two_point,
        "gate": gate,
        "wall_wall": wall,
        "nested": nested,
        "time_trace": time_trace,
    }


def _normalize_nested_axes(raw_axes: Any) -> list:
    if (
        not isinstance(raw_axes, Sequence)
        or isinstance(raw_axes, (str, bytes))
        or not raw_axes
    ):
        raise ValueError("nested sweep must contain at least one axis")
    if len(raw_axes) > BIAS_CHANNEL_COUNT:
        raise ValueError("nested sweep supports at most eight axes")

    normalized = []
    used_channels = set()
    used_names = set()
    for axis_index, raw_axis in enumerate(raw_axes):
        if not isinstance(raw_axis, Mapping):
            raise TypeError(f"nested axis {axis_index} must be a JSON object")
        name = str(raw_axis.get("name", f"axis_{axis_index}")).strip()
        if not name:
            raise ValueError(f"nested axis {axis_index} name must not be empty")
        if name in used_names:
            raise ValueError(f"nested axis name {name!r} is duplicated")
        used_names.add(name)

        raw_channels = raw_axis.get("channels")
        if (
            not isinstance(raw_channels, Sequence)
            or isinstance(raw_channels, (str, bytes))
            or not raw_channels
        ):
            raise ValueError(f"nested axis {name!r} needs at least one channel")
        channels = []
        for raw_channel in raw_channels:
            channel = _integer(raw_channel, f"nested axis {name} channel")
            if channel >= BIAS_CHANNEL_COUNT:
                raise ValueError("nested Bias channels must be between 0 and 7")
            if channel in channels:
                raise ValueError(
                    f"BIAS{channel} is duplicated inside nested axis {name!r}"
                )
            if channel in used_channels:
                raise ValueError(
                    f"BIAS{channel} is assigned to more than one nested axis"
                )
            channels.append(channel)
            used_channels.add(channel)

        vectors = {}
        for key in ("start_v", "stop_v"):
            raw_vector = raw_axis.get(key)
            if (
                not isinstance(raw_vector, Sequence)
                or isinstance(raw_vector, (str, bytes))
                or len(raw_vector) != len(channels)
            ):
                raise ValueError(
                    f"nested axis {name!r} {key} must contain "
                    f"{len(channels)} voltage values"
                )
            vectors[key] = [
                _finite(value, f"nested axis {name} {key}[{index}]")
                for index, value in enumerate(raw_vector)
            ]
        normalized.append({
            "name": name,
            "channels": channels,
            "start_v": vectors["start_v"],
            "stop_v": vectors["stop_v"],
            "points": _integer(
                raw_axis.get("points"), f"nested axis {name} points", 2
            ),
        })
    return normalized


def _normalize_common(raw: Mapping[str, Any], defaults: Mapping[str, Any]) -> dict:
    values = _deep_merge(defaults, raw)
    for name in ("database_path", "experiment_name", "sample_name"):
        values[name] = str(values[name]).strip()
        if not values[name]:
            raise ValueError(f"Bias measurement {name} must not be empty")
    values["notes"] = str(values.get("notes", ""))
    mode = str(values["current_mode"])
    if mode not in CURRENT_MEASUREMENT_MODES:
        raise ValueError(f"unsupported Bias current mode {mode!r}")
    values["current_mode"] = mode
    values["repetitions_per_point"] = _integer(
        values["repetitions_per_point"], "repetitions_per_point", 1
    )
    for name in ("settle_s", "ramp_max_step_v", "ramp_pause_s"):
        values[name] = _finite(values[name], name)
    if values["settle_s"] < 0.0 or values["ramp_pause_s"] < 0.0:
        raise ValueError("settle and ramp pause times must be nonnegative")
    if values["ramp_max_step_v"] <= 0.0:
        raise ValueError("ramp_max_step_v must be positive")
    if not isinstance(values["restore_bias_after_run"], bool):
        raise TypeError("restore_bias_after_run must be boolean")

    sr = dict(values["sr860"])
    sr["visa_address"] = str(sr["visa_address"]).strip()
    if not sr["visa_address"]:
        raise ValueError("SR860 VISA address must not be empty")
    for name in (
        "frequency_hz", "phase_deg", "time_constant_s", "sensitivity_a",
        "sine_bias_v", "settle_time_constants", "input_gain_ohm",
    ):
        sr[name] = _finite(sr[name], f"SR860 {name}")
    if sr["frequency_hz"] <= 0.0:
        raise ValueError("SR860 frequency must be positive")
    if sr["time_constant_s"] not in SR860_TIME_CONSTANTS_S:
        raise ValueError("SR860 time constant is not supported by the driver")
    if sr["sensitivity_a"] not in SR860_CURRENT_SENSITIVITIES_A:
        raise ValueError("SR860 current sensitivity is not supported")
    if not 0.0 <= sr["sine_bias_v"] <= 2.0:
        raise ValueError("SR860 sine bias must be in [0, 2] V")
    if sr["settle_time_constants"] < 0.0:
        raise ValueError("SR860 settling multiplier must be nonnegative")
    if sr["input_gain_ohm"] not in {1e6, 100e6}:
        raise ValueError("SR860 current input gain must be 1e6 or 100e6 ohm")
    sr["filter_slope_db_oct"] = _integer(
        sr["filter_slope_db_oct"], "SR860 filter slope", 1
    )
    if sr["filter_slope_db_oct"] not in {6, 12, 18, 24}:
        raise ValueError("SR860 filter slope must be 6, 12, 18, or 24 dB/oct")
    values["sr860"] = sr

    adc = dict(values["qick_adc"])
    for name in ("readout_ch", "nqz", "fir_samples", "margin_input_samples"):
        adc[name] = _integer(adc[name], f"QICK ADC {name}", 0)
    if adc["nqz"] not in {1, 2}:
        raise ValueError("QICK ADC Nyquist zone must be 1 or 2")
    if adc["fir_samples"] < 1:
        raise ValueError("QICK FIR samples must be positive")
    adc["input_board_type"] = str(adc["input_board_type"])
    if adc["input_board_type"] not in {"RF_In", "DC_In"}:
        raise ValueError("QICK ADC board must be RF_In or DC_In")
    adc["filter_type"] = str(adc["filter_type"])
    if adc["filter_type"] not in {"bypass", "lowpass", "highpass", "bandpass"}:
        raise ValueError("unsupported QICK ADC input filter")
    for name in (
        "readout_frequency_mhz", "attenuation_db", "dc_gain_db",
        "filter_cutoff_ghz", "filter_bandwidth_ghz",
        "post_run_read_delay_seconds", "adc_units_per_amp",
    ):
        adc[name] = _finite(adc[name], f"QICK ADC {name}")
    if adc["adc_units_per_amp"] == 0.0:
        raise ValueError("QICK ADC units per amp must be nonzero")
    delay = adc.get("fpga_trigger_delay_us")
    adc["fpga_trigger_delay_us"] = (
        None if delay is None else _finite(delay, "QICK FPGA trigger delay")
    )
    values["qick_adc"] = adc
    return values


def normalize_bias_measurement_settings(settings: Any) -> dict:
    """Normalize settings while preserving compatibility with older JSON files."""
    if settings is None:
        settings = {}
    if not isinstance(settings, Mapping):
        raise TypeError("bias measurements must be a JSON object")
    defaults = default_bias_measurement_settings()
    normalized = {}
    for kind in BIAS_MEASUREMENT_KINDS:
        raw = settings.get(kind, {})
        if not isinstance(raw, Mapping):
            raise TypeError(f"bias {kind} settings must be a JSON object")
        if kind == "gate":
            raw = dict(raw)
            if "gate_channels" not in raw and "gate_channel" in raw:
                raw["gate_channels"] = [raw["gate_channel"]]
        values = _normalize_common(raw, defaults[kind])
        if kind == "two_point":
            for name in ("bias_start_v", "bias_stop_v"):
                values[name] = _finite(values[name], name)
            if min(values["bias_start_v"], values["bias_stop_v"]) < 0.0:
                raise ValueError("SR860 sine bias sweep cannot use negative amplitude")
            if max(values["bias_start_v"], values["bias_stop_v"]) > 2.0:
                raise ValueError("SR860 sine bias sweep cannot exceed 2 V")
            values["points"] = _integer(values["points"], "2P points", 2)
        elif kind == "gate":
            raw_channels = values.get("gate_channels")
            if (
                not isinstance(raw_channels, Sequence)
                or isinstance(raw_channels, (str, bytes))
                or not raw_channels
            ):
                raise ValueError("gate sweep needs at least one checked channel")
            gate_channels = []
            for raw_channel in raw_channels:
                channel = _integer(raw_channel, "gate channel")
                if channel >= BIAS_CHANNEL_COUNT:
                    raise ValueError("gate channels must be between 0 and 7")
                if channel in gate_channels:
                    raise ValueError(f"BIAS{channel} is duplicated in gate channels")
                gate_channels.append(channel)
            values["gate_channels"] = gate_channels
            values.pop("gate_channel", None)
            # A gate scan leaves the selected DACs at the final trajectory point.
            # Include-return-leg remains an explicit trajectory option.
            values["restore_bias_after_run"] = False
            for name in ("gate_start_v", "gate_stop_v"):
                values[name] = _finite(values[name], name)
            values["points_per_leg"] = _integer(
                values["points_per_leg"], "gate points per leg", 2
            )
            values["loops"] = _integer(values["loops"], "gate loops", 1)
            for name in ("return_leg", "largest_loop_first"):
                if not isinstance(values[name], bool):
                    raise TypeError(f"{name} must be boolean")
        elif kind == "wall_wall":
            for name in ("slow_channel", "fast_channel"):
                values[name] = _integer(values[name], name)
                if values[name] >= BIAS_CHANNEL_COUNT:
                    raise ValueError(f"{name} must be between 0 and 7")
            if values["slow_channel"] == values["fast_channel"]:
                raise ValueError("wall-wall slow and fast channels must differ")
            for name in (
                "slow_start_v", "slow_stop_v", "fast_start_v", "fast_stop_v"
            ):
                values[name] = _finite(values[name], name)
            values["slow_points"] = _integer(
                values["slow_points"], "wall-wall slow points", 2
            )
            values["fast_points"] = _integer(
                values["fast_points"], "wall-wall fast points", 2
            )
        elif kind == "nested":
            values["axes"] = _normalize_nested_axes(values.get("axes"))
        else:
            values["samples"] = _integer(
                values["samples"], "time trace samples", 1
            )
            values["sample_interval_s"] = _finite(
                values["sample_interval_s"], "time trace sample interval"
            )
            if values["sample_interval_s"] < 0.0:
                raise ValueError("time trace sample interval must be nonnegative")
            values["repetitions_per_point"] = 1
            values["restore_bias_after_run"] = False
        normalized[kind] = values
    return normalized


def make_gate_sweep(
    start_v: float,
    stop_v: float,
    points_per_leg: int,
    loops: int,
    *,
    return_leg: bool,
    largest_loop_first: bool,
) -> np.ndarray:
    """Build nested down/up gate legs, matching the inspected notebook intent."""
    start_v = float(start_v)
    stop_v = float(stop_v)
    points_per_leg = int(points_per_leg)
    loops = int(loops)
    fractions = np.linspace(1.0 / loops, 1.0, loops)
    if largest_loop_first:
        fractions = fractions[::-1]
    values = []
    for fraction in fractions:
        end_v = start_v + fraction * (stop_v - start_v)
        outbound = np.linspace(start_v, end_v, points_per_leg, dtype=float)
        values.extend(outbound.tolist())
        if return_leg:
            inbound = np.linspace(end_v, start_v, points_per_leg, dtype=float)[1:]
            values.extend(inbound.tolist())
    return np.asarray(values, dtype=np.float64)


def ramp_bias_channel(
    soc: Any,
    channel: int,
    target_v: float,
    *,
    max_step_v: float,
    pause_s: float,
    voltage_limit_v: float,
    sleeper: Callable[[float], None] = time.sleep,
    cancel_check: Optional[Callable[[], None]] = None,
) -> float:
    """Move one DAC11001 channel to a target using bounded voltage increments."""
    result = ramp_bias_channels(
        soc,
        {int(channel): float(target_v)},
        max_step_v=max_step_v,
        pause_s=pause_s,
        voltage_limit_v=voltage_limit_v,
        sleeper=sleeper,
        cancel_check=cancel_check,
    )
    return result[int(channel)]


def ramp_bias_channels(
    soc: Any,
    targets_v: Mapping[int, float],
    *,
    max_step_v: float,
    pause_s: float,
    voltage_limit_v: float,
    sleeper: Callable[[float], None] = time.sleep,
    cancel_check: Optional[Callable[[], None]] = None,
) -> dict:
    """Ramp several Bias channels along one shared linear interpolation path."""
    if not targets_v:
        raise ValueError("at least one Bias target is required")
    max_step_v = _finite(max_step_v, "maximum Bias ramp step")
    pause_s = _finite(pause_s, "Bias ramp pause")
    voltage_limit_v = _finite(voltage_limit_v, "Bias voltage limit")
    if max_step_v <= 0.0:
        raise ValueError("maximum Bias ramp step must be positive")
    if pause_s < 0.0:
        raise ValueError("Bias ramp pause must be nonnegative")
    if not 0.0 < voltage_limit_v <= BIAS_HARDWARE_MAX_V:
        raise ValueError(
            "Bias voltage limit must be in "
            f"(0, {BIAS_HARDWARE_MAX_V:g}] V"
        )

    targets = {}
    starts = {}
    for raw_channel, raw_target in targets_v.items():
        channel = _integer(raw_channel, "bias channel")
        if channel >= BIAS_CHANNEL_COUNT:
            raise ValueError("bias channel must be between 0 and 7")
        target = _finite(raw_target, f"BIAS{channel} target")
        if abs(target) > voltage_limit_v:
            raise ValueError(
                f"BIAS{channel} target {target:g} V exceeds "
                f"+/-{voltage_limit_v:g} V"
            )
        targets[channel] = target
        start = _finite(
            soc.rfb_get_bias(channel), f"BIAS{channel} current voltage"
        )
        if abs(start) > voltage_limit_v:
            raise ValueError(
                f"BIAS{channel} current voltage {start:g} V is outside "
                f"the +/-{voltage_limit_v:g} V limit; no ramp was started"
            )
        starts[channel] = start

    steps = max(
        1,
        max(
            int(ceil(abs(targets[channel] - starts[channel]) / max_step_v))
            for channel in targets
        ),
    )
    for step in range(1, steps + 1):
        _check_cancel(cancel_check)
        fraction = step / steps
        for channel in sorted(targets):
            value = starts[channel] + fraction * (
                targets[channel] - starts[channel]
            )
            if abs(value) > voltage_limit_v:
                raise RuntimeError(
                    f"BIAS{channel} interpolated voltage {value:g} V "
                    f"exceeds +/-{voltage_limit_v:g} V"
                )
            soc.rfb_set_bias(channel, float(value))
        if pause_s > 0.0:
            _sleep_with_cancel(
                pause_s,
                sleeper=sleeper,
                cancel_check=cancel_check,
            )
    _check_cancel(cancel_check)
    return {
        channel: float(soc.rfb_get_bias(channel))
        for channel in sorted(targets)
    }


def read_bias_snapshot(soc: Any, channel_names: Sequence[str]) -> dict:
    """Read all DAC11001 voltages for mandatory dataset metadata."""
    if len(channel_names) != BIAS_CHANNEL_COUNT:
        raise ValueError("bias channel_names must contain eight names")
    channels = []
    for channel in range(BIAS_CHANNEL_COUNT):
        channels.append({
            "channel": channel,
            "name": str(channel_names[channel]),
            "voltage_v": float(soc.rfb_get_bias(channel)),
        })
    return {
        "read_at_utc": datetime.now(timezone.utc).isoformat(),
        "channels": channels,
    }


def validate_bias_sweep_voltage_limit(
    kind: str,
    config: Mapping[str, Any],
    voltage_limit_v: float,
) -> None:
    """Reject a complete DAC11001 sweep before any hardware operation."""
    voltage_limit_v = _finite(voltage_limit_v, "bias voltage limit")
    if not 0.0 < voltage_limit_v <= BIAS_HARDWARE_MAX_V:
        raise ValueError(
            "bias voltage limit must be in "
            f"(0, {BIAS_HARDWARE_MAX_V:g}] V"
        )

    endpoints = []
    if kind == "two_point":
        # This axis is the SR860 sine-output amplitude, not a DAC11001 BIAS.
        return
    if kind == "gate":
        endpoints = []
        for channel in config["gate_channels"]:
            endpoints.extend((
                (f"BIAS{channel} gate start", config["gate_start_v"]),
                (f"BIAS{channel} gate stop", config["gate_stop_v"]),
            ))
    elif kind == "wall_wall":
        endpoints = [
            (f"BIAS{config['slow_channel']} slow start", config["slow_start_v"]),
            (f"BIAS{config['slow_channel']} slow stop", config["slow_stop_v"]),
            (f"BIAS{config['fast_channel']} fast start", config["fast_start_v"]),
            (f"BIAS{config['fast_channel']} fast stop", config["fast_stop_v"]),
        ]
    elif kind == "nested":
        for axis in config["axes"]:
            for endpoint_name in ("start_v", "stop_v"):
                for channel, value in zip(
                    axis["channels"], axis[endpoint_name]
                ):
                    endpoints.append((
                        f"nested axis {axis['name']!r} BIAS{channel} "
                        f"{endpoint_name}",
                        value,
                    ))
    elif kind == "time_trace":
        return
    else:
        raise ValueError(f"unsupported Bias measurement kind {kind!r}")

    for label, raw_value in endpoints:
        value = _finite(raw_value, label)
        if abs(value) > voltage_limit_v:
            raise ValueError(
                f"{label} {value:g} V exceeds the configured "
                f"+/-{voltage_limit_v:g} V limit"
            )


@dataclass(frozen=True)
class CurrentReading:
    x_a: float
    y_a: float
    r_a: float
    theta_deg: float


class Sr860CurrentReader:
    """Small SR860 adapter with explicit, metadata-friendly configuration."""

    def __init__(
        self,
        settings: Mapping[str, Any],
        *,
        instrument_factory: Optional[Callable[..., Any]] = None,
        sleeper: Callable[[float], None] = time.sleep,
        cancel_check: Optional[Callable[[], None]] = None,
        retry_callback: Optional[Callable[[int, BaseException], None]] = None,
    ):
        if instrument_factory is None:
            try:
                from srsinst.sr860 import SR860
            except (ImportError, ValueError) as exc:
                raise RuntimeError(
                    "srsinst.sr860 and a working VISA implementation are required "
                    "for SR860 current measurement"
                ) from exc
            instrument_factory = SR860
        self.settings = dict(settings)
        self._sleeper = sleeper
        self._instrument_factory = instrument_factory
        self._cancel_check = cancel_check
        self._retry_callback = retry_callback
        self._bias_v = float(self.settings["sine_bias_v"])
        self._initial_amplitude_v = None
        self.instrument = None
        self._connect_with_retry(capture_initial_amplitude=True)

    def _configure_instrument(self, *, capture_initial_amplitude: bool) -> None:
        if capture_initial_amplitude:
            self._initial_amplitude_v = float(
                self.instrument.ref.sine_out_amplitude
            )
        self.instrument.ref.reference_source = "internal"
        self.instrument.ref.frequency = float(self.settings["frequency_hz"])
        self.instrument.ref.phase = float(self.settings["phase_deg"])
        self.instrument.signal.input_mode = "current"
        self.instrument.signal.current_input_gain = float(
            self.settings["input_gain_ohm"]
        )
        self.instrument.signal.current_sensitivity = float(
            self.settings["sensitivity_a"]
        )
        self.instrument.signal.filter_slope = int(
            self.settings["filter_slope_db_oct"]
        )
        self.instrument.signal.time_constant = float(
            self.settings["time_constant_s"]
        )
        self.instrument.ref.sine_out_amplitude = self._bias_v

    def _safe_close_instrument(self) -> None:
        instrument, self.instrument = self.instrument, None
        if instrument is None:
            return
        try:
            instrument.disconnect()
        except Exception:
            pass

    def _report_retry(self, attempt: int, exc: BaseException) -> None:
        if self._retry_callback is not None:
            self._retry_callback(int(attempt), exc)

    def _connect_with_retry(self, *, capture_initial_amplitude: bool) -> None:
        attempt = 0
        while True:
            _check_cancel(self._cancel_check)
            try:
                self.instrument = self._instrument_factory(
                    "visa",
                    self.settings["visa_address"],
                )
                self._configure_instrument(
                    capture_initial_amplitude=capture_initial_amplitude
                )
                return
            except Exception as exc:
                self._safe_close_instrument()
                if not _is_visa_transport_error(exc):
                    raise
                attempt += 1
                self._report_retry(attempt, exc)
                _sleep_with_cancel(
                    SR860_RECONNECT_PAUSE_S,
                    sleeper=self._sleeper,
                    cancel_check=self._cancel_check,
                )

    def set_bias(self, voltage_v: float) -> None:
        self._bias_v = float(voltage_v)
        self.instrument.ref.sine_out_amplitude = self._bias_v

    def read(self) -> CurrentReading:
        delay = (
            float(self.settings["time_constant_s"])
            * float(self.settings["settle_time_constants"])
        )
        if delay > 0.0:
            _sleep_with_cancel(
                delay,
                sleeper=self._sleeper,
                cancel_check=self._cancel_check,
            )
        attempt = 0
        while True:
            _check_cancel(self._cancel_check)
            try:
                x, y = self.instrument.data.get_values("X", "Y")
                _sleep_with_cancel(
                    SR860_QUERY_PAUSE_S,
                    sleeper=self._sleeper,
                    cancel_check=self._cancel_check,
                )
                r, theta = self.instrument.data.get_values("R", "Theta")
                return CurrentReading(float(x), float(y), float(r), float(theta))
            except Exception as exc:
                if not _is_visa_transport_error(exc):
                    raise
                attempt += 1
                self._report_retry(attempt, exc)
                self._safe_close_instrument()
                _sleep_with_cancel(
                    SR860_RECONNECT_PAUSE_S,
                    sleeper=self._sleeper,
                    cancel_check=self._cancel_check,
                )
                self._connect_with_retry(capture_initial_amplitude=False)

    def close(self, *, restore_amplitude: bool = True) -> None:
        try:
            if (
                restore_amplitude
                and self.instrument is not None
                and self._initial_amplitude_v is not None
            ):
                self.instrument.ref.sine_out_amplitude = (
                    self._initial_amplitude_v
                )
        except Exception:
            pass
        finally:
            self._safe_close_instrument()


class QickAdcCurrentReader:
    """Reusable one-point FIR-DDR reader for a connected QICK instance."""

    def __init__(
        self,
        soc: Any,
        soccfg: Any,
        connection: QickConnectionConfig,
        settings: Mapping[str, Any],
        *,
        sleeper: Callable[[float], None] = time.sleep,
        program_factory: Optional[Callable[..., Any]] = None,
    ):
        self.soc = soc
        self.soccfg = soccfg
        self.settings = dict(settings)
        self._sleeper = sleeper
        self.profile = resolve_fir_ddr_profile(soccfg, context="Bias measurement")
        self.config = NoiseAcquisitionConfig(
            host=connection.host,
            ns_port=connection.ns_port,
            proxy_name=connection.proxy_name,
            ro_ch=int(self.settings["readout_ch"]),
            input_board_type=str(self.settings["input_board_type"]),
            nqz=int(self.settings["nqz"]),
            fir_samples=int(self.settings["fir_samples"]),
            readout_frequency_mhz=float(self.settings["readout_frequency_mhz"]),
            attenuation_db=float(self.settings["attenuation_db"]),
            dc_gain_db=float(self.settings["dc_gain_db"]),
            filter_type=str(self.settings["filter_type"]),
            filter_cutoff_ghz=float(self.settings["filter_cutoff_ghz"]),
            filter_bandwidth_ghz=float(self.settings["filter_bandwidth_ghz"]),
            margin_input_samples=int(self.settings["margin_input_samples"]),
            fpga_trigger_delay_us=self.settings.get("fpga_trigger_delay_us"),
            post_run_read_delay_seconds=float(
                self.settings["post_run_read_delay_seconds"]
            ),
        )
        configure_rf_board(soc, (), self.config.readout_spec())
        factory = build_noise_fir_program if program_factory is None else program_factory
        self.program = factory(soccfg, self.config)
        trigger_value = self.profile.selected_trigger_delay_value(
            self.config.fpga_trigger_delay_us
        )
        self.trigger_delay_value = trigger_value
        self.capture_seconds = (
            self.config.fir_samples / self.profile.sample_rate_hz
            + self.profile.trigger_delay_us_for(trigger_value) / 1.0e6
            + (
                self.profile.group_delay_input_samples
                + self.config.margin_input_samples
            ) / (self.profile.input_rate_mhz * 1.0e6)
        )

    def read(self) -> CurrentReading:
        arm_kwargs = dict(
            ch=self.config.ro_ch,
            n_samples=self.config.fir_samples,
            n_triggers=1,
            address=self.config.address,
            stride_bytes=None,
            force_overwrite=self.config.force_overwrite,
        )
        if self.profile.uses_fpga_trigger_delay:
            arm_kwargs.update(
                self.profile.trigger_delay_arm_kwargs(self.trigger_delay_value)
            )
        self.soc.arm_ddr4_fir_samples(**arm_kwargs)
        self.program.run_rounds(self.soc, progress=False)
        self._sleeper(
            self.capture_seconds + self.config.post_run_read_delay_seconds
        )
        iq = np.asarray(self.soc.get_ddr4_fir_samples(
            n_samples=self.config.fir_samples,
            n_triggers=1,
            start=self.config.address,
            stride_bytes=None,
        ), dtype=np.float64)
        expected = (self.config.fir_samples, 2)
        if iq.shape != expected:
            raise RuntimeError(f"unexpected Bias FIR DDR shape {iq.shape}; expected {expected}")
        scale = float(self.settings["adc_units_per_amp"])
        x = float(np.mean(iq[:, 0])) / scale
        y = float(np.mean(iq[:, 1])) / scale
        return CurrentReading(x, y, hypot(x, y), np.degrees(atan2(y, x)))

    def close(self, **_kwargs) -> None:
        return None


@dataclass(frozen=True)
class BiasMeasurementResult:
    kind: str
    database_path: str
    run_id: int
    guid: str
    x_values: np.ndarray
    magnitude_a: np.ndarray
    x_label: str
    y_values: Optional[np.ndarray] = None
    y_label: str = ""


@dataclass(frozen=True)
class BiasMeasurementLiveLayout:
    """Coordinates and shape for a live Bias measurement plot."""

    kind: str
    x_values: np.ndarray
    x_label: str
    data_shape: Tuple[int, ...]
    y_values: Optional[np.ndarray] = None
    y_label: str = ""


@dataclass(frozen=True)
class BiasMeasurementLivePoint:
    """One current reading mapped onto the displayed live-plot cell."""

    kind: str
    plot_index: Tuple[int, ...]
    repetition_index: int
    magnitude_a: float
    completed_reads: int
    total_reads: int


def _safe_transport(current_a: float, bias_v: float) -> Tuple[float, float]:
    if not isfinite(bias_v) or bias_v == 0.0 or current_a == 0.0:
        return np.nan, np.nan
    return current_a / bias_v, bias_v / current_a


def _json_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _register_measurement_parameters(
    measurement: Any,
    kind: str,
    config: Mapping[str, Any],
):
    from qcodes import Parameter

    repetition = Parameter("repetition_index", label="Repetition", unit="")
    if kind == "two_point":
        axes = [Parameter("source_bias_v", label="SR860 sine bias", unit="V")]
    elif kind == "gate":
        axes = [
            Parameter("gate_point_index", label="Gate point", unit=""),
            Parameter("gate_voltage_v", label="Gate voltage", unit="V"),
        ]
    elif kind == "wall_wall":
        axes = [
            Parameter("slow_voltage_v", label="Slow wall voltage", unit="V"),
            Parameter("fast_voltage_v", label="Fast wall voltage", unit="V"),
        ]
    elif kind == "time_trace":
        axes = [
            Parameter("sample_index", label="Sample index", unit=""),
            Parameter("elapsed_time_s", label="Elapsed time", unit="s"),
        ]
    else:
        axes = []
        flat_axes = []
        for axis_index, axis in enumerate(config["axes"]):
            index_parameter = Parameter(
                f"nested_axis_{axis_index}_index",
                label=f"{axis['name']} point",
                unit="",
            )
            voltage_parameters = tuple(
                Parameter(
                    f"nested_axis_{axis_index}_bias{channel}_voltage_v",
                    label=f"{axis['name']} BIAS{channel} voltage",
                    unit="V",
                )
                for channel in axis["channels"]
            )
            axes.append({
                "index": index_parameter,
                "voltages": voltage_parameters,
            })
            flat_axes.extend((index_parameter, *voltage_parameters))
    registered_axes = flat_axes if kind == "nested" else axes
    for parameter in (*registered_axes, repetition):
        measurement.register_parameter(parameter)
    setpoints = tuple((*registered_axes, repetition))
    measured = [
        Parameter("i_x_a", label="Current X", unit="A"),
        Parameter("i_y_a", label="Current Y", unit="A"),
        Parameter("i_r_a", label="Current magnitude", unit="A"),
        Parameter("i_theta_deg", label="Current phase", unit="deg"),
        Parameter("conductance_s", label="Conductance", unit="S"),
        Parameter("resistance_ohm", label="Resistance", unit="Ohm"),
    ]
    for parameter in measured:
        measurement.register_parameter(parameter, setpoints=setpoints)
    return axes, repetition, measured


def run_bias_measurement(
    *,
    connection_config: QickConnectionConfig,
    kind: str,
    settings: Mapping[str, Any],
    channel_names: Sequence[str],
    voltage_limit_v: float,
    connector: Optional[Callable[..., Tuple[Any, Any]]] = None,
    sr860_factory: Optional[Callable[..., Any]] = None,
    adc_reader_factory: Optional[Callable[..., Any]] = None,
    sleeper: Callable[[float], None] = time.sleep,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    live_layout_callback: Optional[
        Callable[[BiasMeasurementLiveLayout], None]
    ] = None,
    live_point_callback: Optional[
        Callable[[BiasMeasurementLivePoint], None]
    ] = None,
    cancel_check: Optional[Callable[[], None]] = None,
    clock: Callable[[], float] = time.monotonic,
) -> BiasMeasurementResult:
    """Execute one Bias measurement and persist point data plus hardware metadata."""
    if kind not in BIAS_MEASUREMENT_KINDS:
        raise ValueError(f"unsupported Bias measurement kind {kind!r}")
    all_settings = normalize_bias_measurement_settings({kind: settings})
    config = all_settings[kind]
    voltage_limit_v = _finite(voltage_limit_v, "bias voltage limit")
    validate_bias_sweep_voltage_limit(kind, config, voltage_limit_v)
    if len(channel_names) != BIAS_CHANNEL_COUNT:
        raise ValueError("channel_names must contain eight names")

    progress_state = {"percent": 0}

    def progress(percent: int, message: str) -> None:
        progress_state["percent"] = max(
            progress_state["percent"],
            int(percent),
        )
        if progress_callback is not None:
            progress_callback(progress_state["percent"], str(message))

    _check_cancel(cancel_check)
    progress(1, "Connecting to QICK and reading all BIAS voltages")
    soc, soccfg = connect_qick(connection_config, connector=connector)
    _check_cancel(cancel_check)
    initial_snapshot = read_bias_snapshot(soc, channel_names)
    initial_voltages = {
        item["channel"]: item["voltage_v"]
        for item in initial_snapshot["channels"]
    }

    sr_reader = None
    current_reader = None
    if kind == "two_point" or config["current_mode"] == "sr860":
        progress(3, "Connecting and configuring SR860")
        sr_reader = Sr860CurrentReader(
            config["sr860"],
            instrument_factory=sr860_factory,
            sleeper=sleeper,
            cancel_check=cancel_check,
            retry_callback=lambda attempt, exc: progress(
                progress_state["percent"],
                "SR860 communication failed; reconnecting "
                f"(attempt {attempt}: {exc})",
            ),
        )
    if config["current_mode"] == "sr860":
        current_reader = sr_reader
    else:
        progress(5, "Configuring QICK FIR-DDR current readout")
        factory = QickAdcCurrentReader if adc_reader_factory is None else adc_reader_factory
        current_reader = factory(
            soc,
            soccfg,
            connection_config,
            config["qick_adc"],
            sleeper=sleeper,
        )

    if kind == "two_point":
        x_values = np.linspace(
            config["bias_start_v"], config["bias_stop_v"], config["points"]
        )
        points = [(float(value),) for value in x_values]
        x_label = "SR860 sine bias [V]"
        y_values = None
        y_label = ""
    elif kind == "gate":
        x_values = make_gate_sweep(
            config["gate_start_v"],
            config["gate_stop_v"],
            config["points_per_leg"],
            config["loops"],
            return_leg=config["return_leg"],
            largest_loop_first=config["largest_loop_first"],
        )
        points = [(index, float(value)) for index, value in enumerate(x_values)]
        selected_labels = []
        for channel in config["gate_channels"]:
            name = str(channel_names[channel]).strip()
            selected_labels.append(
                name if name else f"BIAS{channel}"
            )
        x_label = f"{', '.join(selected_labels)} gate voltage [V]"
        y_values = None
        y_label = ""
    elif kind == "wall_wall":
        y_values = np.linspace(
            config["slow_start_v"], config["slow_stop_v"], config["slow_points"]
        )
        x_values = np.linspace(
            config["fast_start_v"], config["fast_stop_v"], config["fast_points"]
        )
        points = [
            (float(slow_v), float(fast_v))
            for slow_v in y_values
            for fast_v in x_values
        ]
        x_label = f"BIAS{config['fast_channel']} fast voltage [V]"
        y_label = f"BIAS{config['slow_channel']} slow voltage [V]"
    elif kind == "nested":
        nested_axes = config["axes"]
        nested_grids = [
            np.linspace(
                np.asarray(axis["start_v"], dtype=np.float64),
                np.asarray(axis["stop_v"], dtype=np.float64),
                int(axis["points"]),
                axis=0,
            )
            for axis in nested_axes
        ]
        nested_shape = tuple(int(axis["points"]) for axis in nested_axes)
        total_nested_points = int(prod(nested_shape))

        def nested_plot_coordinate(axis_index: int) -> Tuple[np.ndarray, str]:
            axis = nested_axes[axis_index]
            grid = nested_grids[axis_index]
            if len(axis["channels"]) == 1:
                return (
                    np.asarray(grid[:, 0], dtype=np.float64),
                    f"{axis['name']}: BIAS{axis['channels'][0]} voltage [V]",
                )
            return (
                np.arange(axis["points"], dtype=np.float64),
                f"{axis['name']} vector point",
            )

        x_values, x_label = nested_plot_coordinate(len(nested_axes) - 1)
        if len(nested_axes) >= 2:
            y_values, y_label = nested_plot_coordinate(len(nested_axes) - 2)
        else:
            y_values = None
            y_label = ""
        points = None
    else:
        x_values = (
            np.arange(config["samples"], dtype=np.float64)
            * float(config["sample_interval_s"])
        )
        points = [(index,) for index in range(config["samples"])]
        x_label = "Elapsed time [s]"
        y_values = None
        y_label = ""

    if kind == "nested":
        total_reads = total_nested_points * int(config["repetitions_per_point"])
        magnitude_sum = np.zeros(nested_shape, dtype=np.float64)
    else:
        total_reads = len(points) * int(config["repetitions_per_point"])
        magnitude_sum = np.zeros(len(points), dtype=np.float64)
    live_shape = (
        (len(x_values),)
        if y_values is None
        else (len(y_values), len(x_values))
    )
    if live_layout_callback is not None:
        live_layout_callback(BiasMeasurementLiveLayout(
            kind=kind,
            x_values=np.asarray(x_values, dtype=np.float64).copy(),
            x_label=x_label,
            data_shape=tuple(map(int, live_shape)),
            y_values=(
                None
                if y_values is None
                else np.asarray(y_values, dtype=np.float64).copy()
            ),
            y_label=y_label,
        ))
    database_path = Path(config["database_path"]).expanduser().resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from qcodes import (
            Measurement,
            Station,
            initialise_or_create_database_at,
            load_or_create_experiment,
        )
    except ImportError as exc:
        raise RuntimeError("QCoDeS==0.58.0 is required for Bias measurements") from exc

    initialise_or_create_database_at(str(database_path))
    experiment = load_or_create_experiment(
        config["experiment_name"], config["sample_name"]
    )
    measurement = Measurement(exp=experiment, station=Station())
    axes, repetition_parameter, measured = _register_measurement_parameters(
        measurement, kind, config
    )
    changed_channels = []
    if kind == "gate":
        changed_channels = list(map(int, config["gate_channels"]))
    elif kind == "wall_wall":
        changed_channels = [int(config["slow_channel"]), int(config["fast_channel"])]
    elif kind == "nested":
        changed_channels = sorted({
            int(channel)
            for axis in config["axes"]
            for channel in axis["channels"]
        })
    swept_bias_channels = [
        {
            "channel": channel,
            "hardware_name": f"BIAS{channel}",
            "name": str(channel_names[channel]).strip(),
        }
        for channel in changed_channels
    ]

    run_metadata = {
        "schema": BIAS_MEASUREMENT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "configuration": config,
        "current_mode": config["current_mode"],
        "bias_channel_names": list(map(str, channel_names)),
        "swept_bias_channels": swept_bias_channels,
        "bias_initial_snapshot": initial_snapshot,
        "qick_connection": {
            "host": connection_config.host,
            "ns_port": connection_config.ns_port,
            "proxy_name": connection_config.proxy_name,
        },
    }

    dataset = None
    try:
        with measurement.run(
            write_in_background=False,
            in_memory_cache=False,
        ) as datasaver:
            dataset = datasaver.dataset
            dataset.add_metadata("bias_measurement_json", _json_text(run_metadata))
            dataset.add_metadata(
                "bias_channel_voltages_initial_json", _json_text(initial_snapshot)
            )
            dataset.add_metadata(
                "bias_voltage_metadata_json", _json_text(initial_snapshot)
            )
            dataset.add_metadata(
                "swept_bias_channels_json", _json_text(swept_bias_channels)
            )
            dataset.add_metadata("sr860_settings_json", _json_text(config["sr860"]))
            dataset.add_metadata("qick_adc_settings_json", _json_text(config["qick_adc"]))
            if config["notes"]:
                dataset.add_metadata("measurement_notes", config["notes"])

            completed = 0
            current_slow = None
            time_trace_started_at = (
                clock() if kind == "time_trace" else None
            )
            point_iterator = (
                ((index_tuple, index_tuple) for index_tuple in np.ndindex(nested_shape))
                if kind == "nested"
                else enumerate(points)
            )
            for point_index, point in point_iterator:
                _check_cancel(cancel_check)
                if kind == "two_point":
                    sr_reader.set_bias(point[0])
                    axis_results = ((axes[0], point[0]),)
                    excitation_v = point[0]
                elif kind == "gate":
                    ramp_bias_channels(
                        soc,
                        {
                            channel: point[1]
                            for channel in config["gate_channels"]
                        },
                        max_step_v=config["ramp_max_step_v"],
                        pause_s=config["ramp_pause_s"],
                        voltage_limit_v=voltage_limit_v,
                        sleeper=sleeper,
                        cancel_check=cancel_check,
                    )
                    if config["settle_s"] > 0.0:
                        _sleep_with_cancel(
                            config["settle_s"],
                            sleeper=sleeper,
                            cancel_check=cancel_check,
                        )
                    axis_results = ((axes[0], point[0]), (axes[1], point[1]))
                    excitation_v = (
                        float(config["sr860"]["sine_bias_v"])
                        if config["current_mode"] == "sr860"
                        else np.nan
                    )
                elif kind == "wall_wall":
                    slow_v, fast_v = point
                    if current_slow != slow_v:
                        ramp_bias_channel(
                            soc,
                            config["slow_channel"],
                            slow_v,
                            max_step_v=config["ramp_max_step_v"],
                            pause_s=config["ramp_pause_s"],
                            voltage_limit_v=voltage_limit_v,
                            sleeper=sleeper,
                            cancel_check=cancel_check,
                        )
                        ramp_bias_channel(
                            soc,
                            config["fast_channel"],
                            config["fast_start_v"],
                            max_step_v=config["ramp_max_step_v"],
                            pause_s=config["ramp_pause_s"],
                            voltage_limit_v=voltage_limit_v,
                            sleeper=sleeper,
                            cancel_check=cancel_check,
                        )
                        current_slow = slow_v
                    ramp_bias_channel(
                        soc,
                        config["fast_channel"],
                        fast_v,
                        max_step_v=config["ramp_max_step_v"],
                        pause_s=config["ramp_pause_s"],
                        voltage_limit_v=voltage_limit_v,
                        sleeper=sleeper,
                        cancel_check=cancel_check,
                    )
                    if config["settle_s"] > 0.0:
                        _sleep_with_cancel(
                            config["settle_s"],
                            sleeper=sleeper,
                            cancel_check=cancel_check,
                        )
                    axis_results = ((axes[0], slow_v), (axes[1], fast_v))
                    excitation_v = (
                        float(config["sr860"]["sine_bias_v"])
                        if config["current_mode"] == "sr860"
                        else np.nan
                    )
                elif kind == "nested":
                    targets = {}
                    axis_results = []
                    for axis_index, (axis, grid, parameters) in enumerate(zip(
                        config["axes"], nested_grids, axes
                    )):
                        axis_point = int(point[axis_index])
                        axis_results.append((parameters["index"], axis_point))
                        for channel, voltage, parameter in zip(
                            axis["channels"],
                            grid[axis_point],
                            parameters["voltages"],
                        ):
                            targets[int(channel)] = float(voltage)
                            axis_results.append((parameter, float(voltage)))
                    ramp_bias_channels(
                        soc,
                        targets,
                        max_step_v=config["ramp_max_step_v"],
                        pause_s=config["ramp_pause_s"],
                        voltage_limit_v=voltage_limit_v,
                        sleeper=sleeper,
                        cancel_check=cancel_check,
                    )
                    if config["settle_s"] > 0.0:
                        _sleep_with_cancel(
                            config["settle_s"],
                            sleeper=sleeper,
                            cancel_check=cancel_check,
                        )
                    excitation_v = (
                        float(config["sr860"]["sine_bias_v"])
                        if config["current_mode"] == "sr860"
                        else np.nan
                    )
                else:
                    sample_index = int(point[0])
                    target_elapsed_s = (
                        sample_index * float(config["sample_interval_s"])
                    )
                    elapsed_s = max(0.0, clock() - time_trace_started_at)
                    if target_elapsed_s > elapsed_s:
                        _sleep_with_cancel(
                            target_elapsed_s - elapsed_s,
                            sleeper=sleeper,
                            cancel_check=cancel_check,
                        )
                    elapsed_s = max(0.0, clock() - time_trace_started_at)
                    x_values[sample_index] = elapsed_s
                    axis_results = (
                        (axes[0], sample_index),
                        (axes[1], elapsed_s),
                    )
                    excitation_v = (
                        float(config["sr860"]["sine_bias_v"])
                        if config["current_mode"] == "sr860"
                        else np.nan
                    )

                for repetition in range(config["repetitions_per_point"]):
                    _check_cancel(cancel_check)
                    reading = current_reader.read()
                    _check_cancel(cancel_check)
                    conductance, resistance = _safe_transport(
                        reading.r_a, excitation_v
                    )
                    datasaver.add_result(
                        *axis_results,
                        (repetition_parameter, repetition),
                        (measured[0], reading.x_a),
                        (measured[1], reading.y_a),
                        (measured[2], reading.r_a),
                        (measured[3], reading.theta_deg),
                        (measured[4], conductance),
                        (measured[5], resistance),
                    )
                    magnitude_sum[point_index] += reading.r_a
                    completed += 1
                    if live_point_callback is not None:
                        if kind in {"two_point", "gate", "time_trace"}:
                            plot_index = (int(point_index),)
                        elif kind == "wall_wall":
                            plot_index = divmod(
                                int(point_index),
                                len(x_values),
                            )
                        elif len(point_index) == 1:
                            plot_index = (int(point_index[0]),)
                        else:
                            plot_index = tuple(
                                map(int, point_index[-2:])
                            )
                        live_point_callback(BiasMeasurementLivePoint(
                            kind=kind,
                            plot_index=plot_index,
                            repetition_index=int(repetition),
                            magnitude_a=float(reading.r_a),
                            completed_reads=completed,
                            total_reads=total_reads,
                        ))
                    progress(
                        8 + int(84 * completed / total_reads),
                        f"Measured {completed:,}/{total_reads:,} current readings",
                    )
            final_snapshot = read_bias_snapshot(soc, channel_names)
            dataset.add_metadata(
                "bias_channel_voltages_final_json", _json_text(final_snapshot)
            )
            datasaver.flush_data_to_database()
        run_id = int(dataset.run_id)
        guid = str(dataset.guid)
    finally:
        if kind != "gate" and config["restore_bias_after_run"]:
            for channel in changed_channels:
                try:
                    ramp_bias_channel(
                        soc,
                        channel,
                        initial_voltages[channel],
                        max_step_v=config["ramp_max_step_v"],
                        pause_s=config["ramp_pause_s"],
                        voltage_limit_v=voltage_limit_v,
                        sleeper=sleeper,
                    )
                except Exception:
                    pass
        if current_reader is not None and current_reader is not sr_reader:
            current_reader.close()
        if sr_reader is not None:
            sr_reader.close(restore_amplitude=True)

    magnitude = magnitude_sum / float(config["repetitions_per_point"])
    if kind == "wall_wall":
        magnitude = magnitude.reshape(len(y_values), len(x_values))
    elif kind == "nested":
        while magnitude.ndim > 2:
            magnitude = np.mean(magnitude, axis=0)
    progress(100, f"Bias measurement Run {run_id} saved")
    return BiasMeasurementResult(
        kind=kind,
        database_path=str(database_path),
        run_id=run_id,
        guid=guid,
        x_values=np.asarray(x_values, dtype=np.float64),
        magnitude_a=magnitude,
        x_label=x_label,
        y_values=(None if y_values is None else np.asarray(y_values, dtype=np.float64)),
        y_label=y_label,
    )


__all__ = [
    "BIAS_MEASUREMENT_KINDS",
    "BIAS_MEASUREMENT_SCHEMA",
    "BiasMeasurementCancelled",
    "CURRENT_MEASUREMENT_MODES",
    "SR860_CURRENT_SENSITIVITIES_A",
    "SR860_QUERY_PAUSE_S",
    "SR860_RECONNECT_PAUSE_S",
    "SR860_TIME_CONSTANTS_S",
    "BiasMeasurementLiveLayout",
    "BiasMeasurementLivePoint",
    "BiasMeasurementResult",
    "CurrentReading",
    "QickAdcCurrentReader",
    "Sr860CurrentReader",
    "default_bias_measurement_settings",
    "make_gate_sweep",
    "normalize_bias_measurement_settings",
    "ramp_bias_channel",
    "ramp_bias_channels",
    "read_bias_snapshot",
    "run_bias_measurement",
    "validate_bias_sweep_voltage_limit",
]
