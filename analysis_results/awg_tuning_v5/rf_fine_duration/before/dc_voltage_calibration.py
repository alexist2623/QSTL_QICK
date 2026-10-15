"""DC_Out-to-DC_In voltage calibration and QCoDeS persistence.

The calibration sweeps one AWG-tuning DC output across a known connector
voltage range and records the zero-frequency FIR-decimated DC input I value.
A scalar linear model is fitted as::

    adc_value = offset + response * voltage

The Q component is not used for DC calibration.  Compatibility helpers keep
the existing two-column trace shape by placing calibrated voltage in column I
and zero in column Q.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from dataclasses import InitVar, asdict, dataclass, replace
from datetime import datetime, timezone
import json
from math import ceil, isfinite
from numbers import Integral, Real
from pathlib import Path
import shutil
import sqlite3
from typing import Any, Callable, Mapping, Optional, Tuple

import numpy as np
try:
    from .fir_ddr_profile import result_iq_in_input_units
except ImportError:
    from fir_ddr_profile import result_iq_in_input_units


ProgressCallback = Callable[[int, str], None]
CancellationCheck = Callable[[], None]
DC_VOLTAGE_CALIBRATION_SCHEMA = "qstl-qick-dc-voltage-calibration-v1"
DEFAULT_DC_VOLTAGE_START_MV = -800.0
DEFAULT_DC_VOLTAGE_STOP_MV = 800.0
DEFAULT_DC_VOLTAGE_POINTS = 33
DEFAULT_DC_VOLTAGE_FULL_SCALE_MV = 800.0
MAX_DC_VOLTAGE_SAMPLES_PER_POINT = 1_000_000
MIN_DC_VOLTAGE_CALIBRATION_R_SQUARED = 0.95


def _finite(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")
    if positive and result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer")
    result = int(value)
    if result < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return result


def _emit_progress(
    callback: Optional[ProgressCallback], percent: int, message: str
) -> None:
    if callback is not None:
        callback(max(0, min(100, int(percent))), str(message))


def _check_cancel(callback: Optional[CancellationCheck]) -> None:
    if callback is not None:
        callback()


def _json_mapping(value: Any) -> Mapping[str, Any]:
    if value in (None, ""):
        return {}
    try:
        decoded = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return decoded if isinstance(decoded, Mapping) else {}


def _quote_identifier(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


@dataclass(frozen=True)
class DcVoltageCalibrationConfig:
    """Known DC output sweep and FIR-DDR acquisition settings."""

    database_path: str
    output_ch: int = 1
    readout_ch: int = 0
    voltage_start_mv: float = DEFAULT_DC_VOLTAGE_START_MV
    voltage_stop_mv: float = DEFAULT_DC_VOLTAGE_STOP_MV
    voltage_points: int = DEFAULT_DC_VOLTAGE_POINTS
    output_full_scale_mv: float = DEFAULT_DC_VOLTAGE_FULL_SCALE_MV
    samples_per_point: int = 128
    repetitions_per_point: int = 4
    input_dc_gain_db: float = 0.0
    settle_us: float = 5.0
    margin_input_samples: int = 1024
    fpga_trigger_delay_us: Optional[float] = None
    force_overwrite: bool = True
    experiment_name: str = "QICK DC input voltage calibration"
    sample_name: str = ""
    notes: str = ""
    dac_current_settings: Optional[Mapping[str, Any]] = None
    validate_output_range: InitVar[bool] = True

    def __post_init__(self, validate_output_range: bool) -> None:
        if not str(self.database_path).strip():
            raise ValueError("calibration database path must not be empty")
        _integer(self.output_ch, "output_ch")
        _integer(self.readout_ch, "readout_ch")
        start = _finite(self.voltage_start_mv, "voltage_start_mv")
        stop = _finite(self.voltage_stop_mv, "voltage_stop_mv")
        if start == stop:
            raise ValueError("DC calibration voltage endpoints must differ")
        _integer(self.voltage_points, "voltage_points", 2)
        full_scale = _finite(
            self.output_full_scale_mv,
            "output_full_scale_mv",
            positive=True,
        )
        if validate_output_range and max(abs(start), abs(stop)) > full_scale:
            raise ValueError(
                "DC calibration endpoints must fit inside the configured "
                "+/- output full scale"
            )
        samples = _integer(self.samples_per_point, "samples_per_point", 1)
        if samples > MAX_DC_VOLTAGE_SAMPLES_PER_POINT:
            raise ValueError(
                "samples_per_point must be <= "
                f"{MAX_DC_VOLTAGE_SAMPLES_PER_POINT}"
            )
        _integer(self.repetitions_per_point, "repetitions_per_point", 1)
        gain = _finite(self.input_dc_gain_db, "input_dc_gain_db")
        if not -6.0 <= gain <= 26.0:
            raise ValueError("input_dc_gain_db must be in [-6, 26] dB")
        if _finite(self.settle_us, "settle_us") < 0.0:
            raise ValueError("settle_us must be nonnegative")
        _integer(self.margin_input_samples, "margin_input_samples")
        if self.fpga_trigger_delay_us is not None:
            delay_us = _finite(
                self.fpga_trigger_delay_us,
                "fpga_trigger_delay_us",
            )
            if delay_us < 0.0:
                raise ValueError(
                    "fpga_trigger_delay_us must be nonnegative"
                )
        if not isinstance(self.force_overwrite, bool):
            raise TypeError("force_overwrite must be boolean")
        if not str(self.experiment_name).strip():
            raise ValueError("experiment_name must not be empty")

    @property
    def voltages_mv(self) -> np.ndarray:
        return np.linspace(
            float(self.voltage_start_mv),
            float(self.voltage_stop_mv),
            int(self.voltage_points),
            dtype=float,
        )

    @property
    def normalized_amplitudes(self) -> np.ndarray:
        return self.voltages_mv / float(self.output_full_scale_mv)


@dataclass(frozen=True)
class DcVoltageCalibration:
    """Linear scalar ADC response for one DC input channel and gain setting."""

    database_path: Path
    run_id: int
    output_ch: int
    readout_ch: int
    input_dc_gain_db: float
    voltage_min_mv: float
    voltage_max_mv: float
    voltage_points: int
    offset_adc: float
    response_adc_per_v: float
    rmse_adc: float
    r_squared: float

    def __post_init__(self) -> None:
        response = float(self.response_adc_per_v)
        if not np.isfinite(response) or response == 0.0:
            raise ValueError("DC voltage calibration response must be nonzero")

    @classmethod
    def fit(
        cls,
        voltages_mv: Any,
        mean_adc: Any,
        *,
        database_path: Any = "",
        run_id: int = 0,
        output_ch: int = 0,
        readout_ch: int = 0,
        input_dc_gain_db: float = 0.0,
    ) -> "DcVoltageCalibration":
        voltage_mv = np.asarray(voltages_mv, dtype=float).reshape(-1)
        mean_adc = np.asarray(mean_adc, dtype=float).reshape(-1)
        if voltage_mv.size < 2:
            raise ValueError("DC voltage calibration requires at least two points")
        if mean_adc.shape != voltage_mv.shape:
            raise ValueError("voltage and ADC calibration arrays must have equal length")
        if not all(np.all(np.isfinite(values)) for values in (voltage_mv, mean_adc)):
            raise ValueError("DC voltage calibration arrays must be finite")
        if np.unique(voltage_mv).size < 2:
            raise ValueError("DC voltage calibration requires distinct voltages")

        voltage_v = voltage_mv / 1000.0
        design = np.column_stack((np.ones(voltage_v.size), voltage_v))
        offset, response = np.linalg.lstsq(design, mean_adc, rcond=None)[0]
        predicted = offset + response * voltage_v
        residual_power = np.square(mean_adc - predicted)
        centered_power = np.square(mean_adc - np.mean(mean_adc))
        denominator = float(np.sum(centered_power))
        r_squared = (
            1.0
            if denominator == 0.0
            else 1.0 - float(np.sum(residual_power)) / denominator
        )
        return cls(
            database_path=Path(database_path).expanduser(),
            run_id=int(run_id),
            output_ch=int(output_ch),
            readout_ch=int(readout_ch),
            input_dc_gain_db=float(input_dc_gain_db),
            voltage_min_mv=float(np.min(voltage_mv)),
            voltage_max_mv=float(np.max(voltage_mv)),
            voltage_points=int(voltage_mv.size),
            offset_adc=float(offset),
            response_adc_per_v=float(response),
            rmse_adc=float(np.sqrt(np.mean(residual_power))),
            r_squared=float(r_squared),
        )

    def convert_adc(self, adc_value: Any) -> np.ndarray:
        """Convert scalar ADC values to connector volts."""
        values = np.asarray(adc_value, dtype=np.float64)
        if not np.all(np.isfinite(values)):
            raise ValueError("DC input ADC values must be finite")
        return (values - float(self.offset_adc)) / float(
            self.response_adc_per_v
        )

    def convert_iq(self, iq: Any) -> np.ndarray:
        """Compatibility shape: calibrated scalar voltage in I, Q forced zero."""
        values = np.asarray(iq, dtype=np.float64)
        if values.ndim < 1 or values.shape[-1] != 2:
            raise ValueError("DC input I/Q must have a final dimension of length 2")
        if not np.all(np.isfinite(values)):
            raise ValueError("DC input I/Q values must be finite")
        converted = np.zeros_like(values, dtype=np.float64)
        converted[..., 0] = self.convert_adc(values[..., 0])
        return converted

    def as_dict(self) -> Mapping[str, Any]:
        values = asdict(self)
        values["database_path"] = str(self.database_path)
        values["schema"] = DC_VOLTAGE_CALIBRATION_SCHEMA
        values["formula"] = (
            "voltage_v = (adc_i - offset_adc) / response_adc_per_v; "
            "adc_q is ignored"
        )
        return values


@dataclass
class StoredDcVoltageCalibrationRun:
    run_id: int
    guid: str
    database_path: Path
    row_count: int
    board_type: str = "DC_In"
    dataset: Any = None
    result: Optional[Mapping[str, Any]] = None


def build_dc_voltage_calibration_program(
    soccfg: Any,
    config: DcVoltageCalibrationConfig,
    *,
    tproc_mhz: Optional[float] = None,
) -> Any:
    """Build the hardware amplitude sweep used for DC voltage calibration."""
    # Saved GUI settings may retain endpoints outside a newly reduced DAC
    # range. They remain editable, but may never be sent to the hardware.
    if max(abs(config.voltage_start_mv), abs(config.voltage_stop_mv)) > config.output_full_scale_mv:
        raise ValueError("DC calibration endpoints must fit inside the configured +/- output full scale")
    try:
        from .qick_fine_tune_sweep import DdrFirReadoutConfig, FineTuneSequence, normalized_to_dac
        from .fir_ddr_profile import resolve_fir_ddr_profile
    except ImportError:
        from qick_fine_tune_sweep import DdrFirReadoutConfig, FineTuneSequence, normalized_to_dac
        from fir_ddr_profile import resolve_fir_ddr_profile

    effective_tproc_mhz = (
        float(soccfg["tprocs"][0]["f_time"])
        if tproc_mhz is None
        else _finite(tproc_mhz, "tproc_mhz", positive=True)
    )
    gen_cfg = soccfg["gens"][int(config.output_ch)]
    fabric_mhz = _finite(gen_cfg["f_fabric"], "AWG fabric clock", positive=True)
    fir_profile = resolve_fir_ddr_profile(
        soccfg,
        context="DC voltage calibration",
    )
    fpga_trigger_delay_value = fir_profile.selected_trigger_delay_value(
        config.fpga_trigger_delay_us
    )
    fpga_trigger_delay_us = fir_profile.trigger_delay_us_for(
        fpga_trigger_delay_value
    )
    # Keep the swept SET active through FIR readiness and the complete FIR-DDR
    # capture. The 50 kSPS HWH additionally delays capture in FPGA valid-sample
    # units, so the SET must cover that interval without moving the tProcessor
    # trigger. The following SET returns the DC output to zero every point.
    capture_hold_us = (
        float(config.settle_us)
        + fpga_trigger_delay_us
        + float(config.samples_per_point) * fir_profile.sample_period_us
        + float(config.margin_input_samples) / fir_profile.input_rate_mhz
        + 2.0
    )
    hold_fabric_cycles = max(1, int(ceil(capture_hold_us * fabric_mhz)))
    trigger_delay = max(0, int(ceil(float(config.settle_us) * effective_tproc_mhz)))
    if max(hold_fabric_cycles, trigger_delay) > 0x7FFF_FFFF:
        raise ValueError(
            "DC calibration timing exceeds the signed 32-bit tProcessor "
            "interval; reduce FIR samples per point or settle time"
        )

    sequence = FineTuneSequence(("dc_cal_out",))
    sequence.dac_current_settings = dict(config.dac_current_settings or {})
    sequence.add_set("dc_calibration", (0.0,), hold_fabric_cycles)
    sequence.add_set("return_zero", (0.0,), 1)
    amplitudes = config.normalized_amplitudes
    start_code, stop_code = (normalized_to_dac(float(value)) for value in (amplitudes[0], amplitudes[-1]))
    quantum = 1 << int(gen_cfg.get("dac_invalid_lsb", 2))
    divisor = (int(amplitudes.size) - 1) * quantum
    span = stop_code - start_code
    direction = 1 if span >= 0 else -1
    step = direction * ((abs(span) + divisor // 2) // divisor) * quantum
    last_code = start_code + step * (int(amplitudes.size) - 1)
    start, stop = float(amplitudes[0]), float(amplitudes[-1])
    if not int(gen_cfg.get("minv", -32768)) <= last_code <= int(gen_cfg.get("maxv", 32764)):
        # A full-scale endpoint can round one step past the positive rail.
        # Keep a constant hardware increment, one quantum smaller, and use
        # its actual voltages for both the fit and stored setpoints.
        step = direction * (abs(span) // divisor) * quantum
        start = start_code / 32768.0
        stop = (start_code + step * (int(amplitudes.size) - 1)) / 32768.0
    sequence.add_amplitude_sweep(
        "dc_calibration",
        "dc_cal_out",
        start,
        stop,
        int(amplitudes.size),
    )
    ddr = DdrFirReadoutConfig(
        ro_ch=int(config.readout_ch),
        samples_per_trigger=int(config.samples_per_point),
        at_segment="dc_calibration",
        readout_freq_mhz=0.0,
        trigger_delay_tproc_cycles=trigger_delay,
        readout_period_cycles=65535,
        margin_input_samples=int(config.margin_input_samples),
        fpga_trigger_delay_samples=(
            fpga_trigger_delay_value
            if config.fpga_trigger_delay_us is not None
            else None
        ),
        force_overwrite=bool(config.force_overwrite),
    )
    program = sequence.make_program(
        soccfg,
        awg_channels=(int(config.output_ch),),
        tproc_mhz=effective_tproc_mhz,
        repetitions_per_sweep=int(config.repetitions_per_point),
        ddr_readout=ddr,
    )
    # Fit against the SET words actually sent by the hardware loop. Its
    # constant integer increment need not land on the requested linspace.
    model = program._sweep_models[(0, 0, 0, "target")]
    codes = np.asarray([
        program._sweep_model_value(model, point)
        for point in range(sequence.sweep_point_count)
    ], dtype=np.int64)
    program.dc_calibration_voltages_mv = codes * float(config.output_full_scale_mv) / 32768.0
    return program


def _runtime_storage_helpers():
    try:
        from .qick_qcodes_experiment import (
            _checkpoint_sqlite_database,
            _json_text,
            _prepare_local_database,
            _publish_local_database,
            connect_qick,
        )
    except ImportError:
        from qick_qcodes_experiment import (
            _checkpoint_sqlite_database,
            _json_text,
            _prepare_local_database,
            _publish_local_database,
            connect_qick,
        )
    return (
        _checkpoint_sqlite_database,
        _json_text,
        _prepare_local_database,
        _publish_local_database,
        connect_qick,
    )


def _store_dc_voltage_calibration(
    config: DcVoltageCalibrationConfig,
    voltages_mv: np.ndarray,
    mean_adc: np.ndarray,
    std_adc: np.ndarray,
    calibration: DcVoltageCalibration,
    *,
    voltage_reference: str = "requested_grid",
) -> StoredDcVoltageCalibrationRun:
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
            "QCoDeS==0.58.0 is required for DC voltage calibration storage"
        ) from exc
    (
        checkpoint_database,
        json_text,
        prepare_local_database,
        publish_local_database,
        _connect_qick,
    ) = _runtime_storage_helpers()

    database_path = Path(config.database_path).expanduser().resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    staging, local_path = prepare_local_database(database_path)
    try:
        initialise_or_create_database_at(str(local_path))
        sample_name = str(config.sample_name).strip() or (
            f"DC_In_voltage_ch{int(config.readout_ch)}_"
            f"gain{float(config.input_dc_gain_db):g}dB"
        )
        if not sample_name.lower().startswith("dc_in"):
            sample_name = f"DC_In_{sample_name}"
        experiment = load_or_create_experiment(config.experiment_name, sample_name)
        measurement = Measurement(exp=experiment, station=Station())
        voltage = Parameter(
            "dc_voltage_mv",
            label="Known DC output voltage",
            unit="mV",
        )
        mean_value = Parameter(
            "mean_adc",
            label="Mean zero-frequency DC input",
            unit="ADC",
        )
        std_value = Parameter(
            "std_adc",
            label="DC input standard deviation",
            unit="ADC",
        )
        measurement.register_parameter(voltage)
        for parameter in (mean_value, std_value):
            measurement.register_parameter(parameter, setpoints=(voltage,))

        config_metadata = {
            "schema": DC_VOLTAGE_CALIBRATION_SCHEMA,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "purpose": "dc_input_voltage",
            "output_board_type": "DC_Out",
            "input_board_type": "DC_In",
            "output_ch": int(config.output_ch),
            "readout_ch": int(config.readout_ch),
            "input_dc_gain_db": float(config.input_dc_gain_db),
            "configuration": asdict(config),
            "voltage_reference": voltage_reference,
            "requested_voltages_mv": config.voltages_mv.tolist(),
            "fit_voltages_mv": voltages_mv.tolist(),
        }
        with measurement.run(
            write_in_background=False,
            in_memory_cache=False,
        ) as datasaver:
            dataset = datasaver.dataset
            dataset.add_metadata(
                "DC_Voltage_Calibration_Config",
                json_text(config_metadata),
            )
            dataset.add_metadata(
                "DC_Voltage_Calibration_Result",
                json_text(calibration.as_dict()),
            )
            if config.notes:
                dataset.add_metadata("calibration_notes", config.notes)
            for index, value_mv in enumerate(voltages_mv):
                datasaver.add_result(
                    (voltage, float(value_mv)),
                    (mean_value, float(mean_adc[index])),
                    (std_value, float(std_adc[index])),
                )
            datasaver.flush_data_to_database()
        guid = str(dataset.guid)
        run_id = int(dataset.run_id)
        dataset.conn.close()
        checkpoint_database(local_path)
        publish_local_database(local_path, database_path)
        initialise_or_create_database_at(str(database_path))
        final_dataset = load_by_guid(guid)
        final_calibration = replace(
            calibration,
            database_path=database_path,
            run_id=run_id,
        )
        return StoredDcVoltageCalibrationRun(
            run_id=run_id,
            guid=guid,
            database_path=database_path,
            row_count=int(voltages_mv.size),
            dataset=final_dataset,
            result={
                "voltages_mv": voltages_mv.tolist(),
                "mean_adc": mean_adc.tolist(),
                "std_adc": std_adc.tolist(),
                "calibration": dict(final_calibration.as_dict()),
            },
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def run_dc_voltage_calibration(
    *,
    connection_config: Any,
    calibration_config: DcVoltageCalibrationConfig,
    tproc_mhz: Optional[float] = None,
    connector: Optional[Callable[..., Tuple[Any, Any]]] = None,
    program_factory: Optional[Callable[..., Any]] = None,
    acquisition_callback: Optional[Callable[[Any, Any], Any]] = None,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_check: Optional[CancellationCheck] = None,
) -> StoredDcVoltageCalibrationRun:
    """Sweep DC_Out, acquire DC_In FIR samples, fit, and save calibration."""
    _check_cancel(cancel_check)
    *_storage, connect_qick = _runtime_storage_helpers()
    _emit_progress(progress_callback, 0, "Connecting to QICK")
    soc, soccfg = connect_qick(connection_config, connector=connector)
    _check_cancel(cancel_check)
    _emit_progress(progress_callback, 4, "Configuring DC output and DC input")
    soc.rfb_set_gen_dc(int(calibration_config.output_ch))
    actual_gain = float(
        soc.rfb_set_ro_dc(
            int(calibration_config.readout_ch),
            float(calibration_config.input_dc_gain_db),
        )
    )
    adjusted_config = replace(calibration_config, input_dc_gain_db=actual_gain)
    _check_cancel(cancel_check)
    factory = program_factory or build_dc_voltage_calibration_program
    _emit_progress(progress_callback, 8, "Compiling hardware voltage sweep")
    program = factory(soccfg, adjusted_config, tproc_mhz=tproc_mhz)
    _check_cancel(cancel_check)
    _emit_progress(
        progress_callback,
        12,
        (
            f"Acquiring {adjusted_config.voltage_points} voltages x "
            f"{adjusted_config.repetitions_per_point} repetitions"
        ),
    )
    if acquisition_callback is not None:
        result = acquisition_callback(soc, program)
    else:
        result = program.acquire_fir_ddr(soc, cancel_check=cancel_check)
    _check_cancel(cancel_check)
    iq = result_iq_in_input_units(result).astype(np.float64, copy=False)
    expected_shape = (
        int(adjusted_config.voltage_points),
        int(adjusted_config.repetitions_per_point),
        int(adjusted_config.samples_per_point),
        2,
    )
    if iq.shape != expected_shape:
        raise RuntimeError(
            f"unexpected DC calibration IQ shape {iq.shape}; expected {expected_shape}"
        )
    flattened = iq.reshape(iq.shape[0], -1, 2)
    mean_adc = flattened[..., 0].mean(axis=1)
    std_adc = flattened[..., 0].std(axis=1)
    voltage_reference = "compiled_set_codes" if hasattr(program, "dc_calibration_voltages_mv") else "requested_grid"
    voltages_mv = np.asarray(getattr(program, "dc_calibration_voltages_mv", adjusted_config.voltages_mv), dtype=float)
    if voltages_mv.shape != mean_adc.shape or not np.all(np.isfinite(voltages_mv)):
        raise RuntimeError("DC calibration voltage reference does not match acquired points")
    calibration = DcVoltageCalibration.fit(
        voltages_mv,
        mean_adc,
        database_path=adjusted_config.database_path,
        output_ch=adjusted_config.output_ch,
        readout_ch=adjusted_config.readout_ch,
        input_dc_gain_db=actual_gain,
    )
    _check_cancel(cancel_check)
    if calibration.r_squared < MIN_DC_VOLTAGE_CALIBRATION_R_SQUARED:
        raise RuntimeError(
            "DC voltage calibration did not detect a linear loopback response: "
            f"output generator {adjusted_config.output_ch} -> readout "
            f"{adjusted_config.readout_ch}, response "
            f"{calibration.response_adc_per_v:.6g} ADC/V, "
            f"R^2={calibration.r_squared:.6f}. Verify the selected front-panel "
            "SMA pair and cable. The invalid calibration was not saved."
        )
    _emit_progress(
        progress_callback,
        85,
        f"Fitted DC response (R^2={calibration.r_squared:.8f})",
    )
    _check_cancel(cancel_check)
    stored = _store_dc_voltage_calibration(
        adjusted_config,
        voltages_mv,
        mean_adc,
        std_adc,
        calibration,
        voltage_reference=voltage_reference,
    )
    _emit_progress(
        progress_callback,
        100,
        f"DC voltage calibration Run {stored.run_id} saved",
    )
    return stored


def load_dc_voltage_calibration(
    database_path: Any,
    *,
    readout_ch: int,
    input_dc_gain_db: float,
    run_id: Optional[int] = None,
    gain_tolerance_db: float = 1.0e-6,
) -> DcVoltageCalibration:
    """Load an exact run or the latest channel/gain-compatible DC calibration."""
    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"calibration database does not exist: {path}")
    readout_ch = _integer(readout_ch, "readout_ch")
    input_dc_gain_db = _finite(input_dc_gain_db, "input_dc_gain_db")
    if run_id in (None, 0):
        selected_run_id = None
    else:
        selected_run_id = _integer(run_id, "run_id", 1)
    gain_tolerance_db = _finite(gain_tolerance_db, "gain_tolerance_db")
    if gain_tolerance_db < 0.0:
        raise ValueError("gain_tolerance_db must be nonnegative")

    uri = path.as_uri() + "?mode=ro"
    matches = []
    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT r.*, e.sample_name FROM runs r "
            "JOIN experiments e ON e.exp_id = r.exp_id ORDER BY r.run_id DESC"
        ).fetchall()
        for row in rows:
            candidate_run_id = int(row["run_id"])
            if selected_run_id is not None and candidate_run_id != selected_run_id:
                continue
            table_name = str(row["result_table_name"])
            columns = {
                str(item[1])
                for item in connection.execute(
                    f"PRAGMA table_info({_quote_identifier(table_name)})"
                )
            }
            required = {"dc_voltage_mv", "mean_adc"}
            if not required.issubset(columns):
                continue
            fields = {str(key).lower(): str(key) for key in row.keys()}
            config_key = fields.get("dc_voltage_calibration_config")
            metadata = _json_mapping(row[config_key]) if config_key else {}
            if metadata.get("schema") != DC_VOLTAGE_CALIBRATION_SCHEMA:
                continue
            candidate_channel = int(metadata.get("readout_ch", -1))
            candidate_gain = float(metadata.get("input_dc_gain_db", np.nan))
            if candidate_channel != readout_ch or not np.isfinite(candidate_gain):
                continue
            if abs(candidate_gain - input_dc_gain_db) > gain_tolerance_db:
                continue
            records = connection.execute(
                f"SELECT dc_voltage_mv, mean_adc FROM "
                f"{_quote_identifier(table_name)} "
                "WHERE dc_voltage_mv IS NOT NULL AND mean_adc IS NOT NULL "
                "ORDER BY dc_voltage_mv"
            ).fetchall()
            if len(records) < 2:
                continue
            values = np.asarray([tuple(record) for record in records], dtype=float)
            matches.append((candidate_run_id, metadata, values))

    if not matches:
        selector = (
            f"Run {selected_run_id}"
            if selected_run_id is not None
            else "a compatible run"
        )
        raise LookupError(
            f"could not find {selector} for DC_In readout {readout_ch} at "
            f"{input_dc_gain_db:g} dB in {path}"
        )
    candidate_run_id, metadata, values = max(matches, key=lambda item: item[0])
    return DcVoltageCalibration.fit(
        values[:, 0],
        values[:, 1],
        database_path=path,
        run_id=candidate_run_id,
        output_ch=int(metadata.get("output_ch", 0)),
        readout_ch=readout_ch,
        input_dc_gain_db=input_dc_gain_db,
    )


__all__ = [
    "DC_VOLTAGE_CALIBRATION_SCHEMA",
    "MAX_DC_VOLTAGE_SAMPLES_PER_POINT",
    "MIN_DC_VOLTAGE_CALIBRATION_R_SQUARED",
    "DEFAULT_DC_VOLTAGE_FULL_SCALE_MV",
    "DEFAULT_DC_VOLTAGE_POINTS",
    "DEFAULT_DC_VOLTAGE_START_MV",
    "DEFAULT_DC_VOLTAGE_STOP_MV",
    "DcVoltageCalibration",
    "DcVoltageCalibrationConfig",
    "StoredDcVoltageCalibrationRun",
    "build_dc_voltage_calibration_program",
    "load_dc_voltage_calibration",
    "run_dc_voltage_calibration",
]
