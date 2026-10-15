"""QICK RF output and ADC input power calibration workflows.

Output calibration drives a periodic QICK tone and reads a Keysight/Agilent
oscilloscope FFT marker.  Input calibration uses either the FIR-DDR readout
or the AVG buffer and a previous output calibration to fit, at each frequency,

``input_power_dbm = slope * 20*log10(hypot(I, Q)) + intercept``.

The QCoDeS column names intentionally match the original calibration
notebooks so existing ``gain_pwr_calb.db`` files and new GUI-generated runs
can be consumed by the same :mod:`power_calibration` loader.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from math import isfinite
from numbers import Integral, Real
from pathlib import Path
import shutil
import time
from typing import Any, Callable, Mapping, Optional, Tuple

import numpy as np

try:
    from .input_power_estimate import OutputGainRegression
    from .power_calibration import (
        CalibrationDatabase,
        INPUT_BOARD_TYPES,
        MAX_QICK_GAIN,
        OUTPUT_BOARD_TYPES,
    )
    from .qick_qcodes_experiment import (
        QickConnectionConfig,
        _checkpoint_sqlite_database,
        _json_text,
        _prepare_local_database,
        _publish_local_database,
        connect_qick,
    )
    from .qick_sparameter_sweep import (
        ACQUISITION_SOURCES,
        FILTER_TYPES,
        SParameterSweepConfig,
        build_sparameter_program,
        configure_sparameter_rf_board,
    )
except ImportError:
    from input_power_estimate import OutputGainRegression
    from power_calibration import (
        CalibrationDatabase,
        INPUT_BOARD_TYPES,
        MAX_QICK_GAIN,
        OUTPUT_BOARD_TYPES,
    )
    from qick_qcodes_experiment import (
        QickConnectionConfig,
        _checkpoint_sqlite_database,
        _json_text,
        _prepare_local_database,
        _publish_local_database,
        connect_qick,
    )
    from qick_sparameter_sweep import (
        ACQUISITION_SOURCES,
        FILTER_TYPES,
        SParameterSweepConfig,
        build_sparameter_program,
        configure_sparameter_rf_board,
    )


ProgressCallback = Callable[[int, str], None]
CancellationCheck = Callable[[], None]
ToneRunner = Callable[[Any, Any, int, int, float, int, int], float]
MAX_RF_PERIODIC_WORD_CYCLES = 65535
RF_STOP_WORD_CYCLES = 3
MIN_VALID_OSCILLOSCOPE_POWER_DBM = -200.0
MAX_VALID_OSCILLOSCOPE_POWER_DBM = 100.0


class InvalidOscilloscopePowerError(RuntimeError):
    """Raised when an oscilloscope marker cannot be used as calibration data."""


def _valid_oscilloscope_power_dbm(value: Any) -> bool:
    try:
        power_dbm = float(value)
    except (TypeError, ValueError):
        return False
    return (
        np.isfinite(power_dbm)
        and MIN_VALID_OSCILLOSCOPE_POWER_DBM
        <= power_dbm
        <= MAX_VALID_OSCILLOSCOPE_POWER_DBM
    )


def _invalid_power_message(value: Any) -> str:
    return (
        f"oscilloscope power {value!r} dBm is outside the valid calibration "
        f"range {MIN_VALID_OSCILLOSCOPE_POWER_DBM:g}.."
        f"{MAX_VALID_OSCILLOSCOPE_POWER_DBM:g} dBm"
    )


def _emit_progress(
    callback: Optional[ProgressCallback], percent: int, message: str
) -> None:
    if callback is not None:
        callback(max(0, min(100, int(percent))), str(message))


def _check_cancel(callback: Optional[CancellationCheck]) -> None:
    if callback is not None:
        callback()


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


def _attenuation(value: Any, name: str) -> float:
    result = _finite(value, name)
    if not 0.0 <= result <= 31.75:
        raise ValueError(f"{name} must be in [0, 31.75] dB")
    return result


def _gain_axis(start: int, stop: int, points: int, scale: str) -> np.ndarray:
    start = _integer(start, "gain_start", 1)
    stop = _integer(stop, "gain_end", 1)
    points = _integer(points, "gain_points", 2)
    if start > MAX_QICK_GAIN or stop > MAX_QICK_GAIN:
        raise ValueError(f"gain must not exceed {MAX_QICK_GAIN}")
    if start == stop:
        raise ValueError("gain start and end must differ")
    if scale not in ("linear", "log"):
        raise ValueError("gain_scale must be 'linear' or 'log'")
    values = (
        np.linspace(start, stop, points, dtype=float)
        if scale == "linear"
        else np.geomspace(start, stop, points, dtype=float)
    )
    gains = np.rint(values).astype(np.int64)
    gains[0] = start
    gains[-1] = stop
    if np.unique(gains).size != points:
        raise ValueError("gain points collapse to duplicate integer codes")
    return gains


def _frequency_axis(start: float, stop: float, points: int) -> np.ndarray:
    start = _finite(start, "frequency_start_mhz")
    stop = _finite(stop, "frequency_end_mhz")
    points = _integer(points, "frequency_points", 2)
    if start == stop:
        raise ValueError("frequency start and end must differ")
    return np.linspace(start, stop, points, dtype=float)


def _sample_name(board_type: str, configured: str, frequencies: np.ndarray) -> str:
    configured = str(configured).strip()
    if configured:
        if not configured.lower().startswith(board_type.lower()):
            return f"{board_type}_{configured}"
        return configured
    start = f"{float(frequencies[0]):.9g}".replace("-", "m").replace(".", "p")
    stop = f"{float(frequencies[-1]):.9g}".replace("-", "m").replace(".", "p")
    return f"{board_type}_{start}_{stop}MHz"


@dataclass(frozen=True)
class OscilloscopeConfig:
    """Keysight/Agilent oscilloscope FFT marker settings."""

    visa_resource: str = ""
    channel: int = 2
    fft_function: int = 1
    span_mhz: float = 100.0
    average_count: int = 100
    settle_seconds: float = 2.0
    sample_interval_seconds: float = 0.01
    timeout_ms: int = 10_000

    def __post_init__(self) -> None:
        _integer(self.channel, "oscilloscope channel", 1)
        _integer(self.fft_function, "FFT function", 1)
        _finite(self.span_mhz, "FFT span", positive=True)
        _integer(self.average_count, "scope average_count", 1)
        if _finite(self.settle_seconds, "scope settle_seconds") < 0.0:
            raise ValueError("scope settle_seconds must be nonnegative")
        if (
            _finite(
                self.sample_interval_seconds,
                "scope sample_interval_seconds",
            )
            < 0.0
        ):
            raise ValueError("scope sample_interval_seconds must be nonnegative")
        _integer(self.timeout_ms, "scope timeout_ms", 1)


@dataclass(frozen=True)
class OutputPowerCalibrationConfig:
    """Periodic-tone output calibration measured by an oscilloscope."""

    database_path: str
    output_board_type: str = "RF_Out"
    output_ch: int = 0
    frequency_start_mhz: float = 400.0
    frequency_end_mhz: float = 500.0
    frequency_points: int = 11
    gain_start: int = 1000
    gain_end: int = MAX_QICK_GAIN
    gain_points: int = 16
    gain_scale: str = "linear"
    output_att1_db: float = 0.0
    output_att2_db: float = 0.0
    output_filter_type: str = "bypass"
    output_filter_cutoff_ghz: float = 2.5
    output_filter_bandwidth_ghz: float = 1.0
    nqz: int = 1
    tone_length_fabric_cycles: int = 16
    experiment_name: str = "QICK output power calibration"
    sample_name: str = ""
    notes: str = ""
    oscilloscope: OscilloscopeConfig = OscilloscopeConfig()

    def __post_init__(self) -> None:
        if not str(self.database_path).strip():
            raise ValueError("calibration database path must not be empty")
        if self.output_board_type not in OUTPUT_BOARD_TYPES:
            raise ValueError(f"output board must be one of {OUTPUT_BOARD_TYPES}")
        _integer(self.output_ch, "output_ch")
        self.frequencies_mhz
        self.gains
        _attenuation(self.output_att1_db, "output_att1_db")
        _attenuation(self.output_att2_db, "output_att2_db")
        if self.output_filter_type not in FILTER_TYPES:
            raise ValueError(f"output filter must be one of {FILTER_TYPES}")
        _finite(self.output_filter_cutoff_ghz, "output filter cutoff", positive=True)
        _finite(
            self.output_filter_bandwidth_ghz,
            "output filter bandwidth",
            positive=True,
        )
        if _integer(self.nqz, "nqz", 1) not in (1, 2):
            raise ValueError("nqz must be 1 or 2")
        _integer(self.tone_length_fabric_cycles, "tone length", 3)
        if not str(self.experiment_name).strip():
            raise ValueError("experiment_name must not be empty")
        if not isinstance(self.oscilloscope, OscilloscopeConfig):
            object.__setattr__(
                self,
                "oscilloscope",
                OscilloscopeConfig(**dict(self.oscilloscope)),
            )

    @property
    def frequencies_mhz(self) -> np.ndarray:
        return _frequency_axis(
            self.frequency_start_mhz,
            self.frequency_end_mhz,
            self.frequency_points,
        )

    @property
    def gains(self) -> np.ndarray:
        return _gain_axis(
            self.gain_start,
            self.gain_end,
            self.gain_points,
            self.gain_scale,
        )

    @property
    def effective_output_att1_db(self) -> float:
        return float(self.output_att1_db) if self.output_board_type == "RF_Out" else 0.0

    @property
    def effective_output_att2_db(self) -> float:
        return float(self.output_att2_db) if self.output_board_type == "RF_Out" else 0.0


@dataclass(frozen=True)
class InputPowerCalibrationConfig:
    """ADC magnitude calibration using a previously calibrated output path."""

    database_path: str
    output_board_type: str = "RF_Out"
    input_board_type: str = "RF_In"
    output_ch: int = 0
    readout_ch: int = 0
    frequency_start_mhz: float = 400.0
    frequency_end_mhz: float = 500.0
    frequency_points: int = 11
    gain_start: int = 1000
    gain_end: int = MAX_QICK_GAIN
    gain_points: int = 16
    gain_scale: str = "linear"
    acquisition_source: str = "fir_ddr"
    scan_time_us: float = 100.0
    output_att1_db: float = 0.0
    output_att2_db: float = 0.0
    input_attenuation_db: float = 0.0
    input_dc_gain_db: float = 0.0
    output_filter_type: str = "bypass"
    output_filter_cutoff_ghz: float = 2.5
    output_filter_bandwidth_ghz: float = 1.0
    readout_filter_type: str = "bypass"
    readout_filter_cutoff_ghz: float = 2.5
    readout_filter_bandwidth_ghz: float = 1.0
    path_loss_db: float = 0.0
    fit_trim_low: int = 0
    fit_trim_high: int = 0
    nqz: int = 1
    readout_nqz: int = 1
    margin_input_samples: int = 1024
    fpga_trigger_delay_us: Optional[float] = None
    settle_seconds: float = 0.05
    force_overwrite: bool = True
    experiment_name: str = "QICK ADC input power calibration"
    sample_name: str = ""
    notes: str = ""
    power_sweep_enabled: bool = False
    power_start_dbm: float = -40.0
    power_end_dbm: float = -20.0
    power_points: int = 16
    use_gain_regression: bool = False

    def __post_init__(self) -> None:
        if not str(self.database_path).strip():
            raise ValueError("calibration database path must not be empty")
        if self.output_board_type not in OUTPUT_BOARD_TYPES:
            raise ValueError(f"output board must be one of {OUTPUT_BOARD_TYPES}")
        if self.input_board_type not in INPUT_BOARD_TYPES:
            raise ValueError(f"input board must be one of {INPUT_BOARD_TYPES}")
        _integer(self.output_ch, "output_ch")
        _integer(self.readout_ch, "readout_ch")
        self.frequencies_mhz
        gains = self.target_powers_dbm if self.power_sweep_enabled else self.gains
        for name in ("power_sweep_enabled", "use_gain_regression"):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be boolean")
        self.target_powers_dbm
        if self.acquisition_source not in ACQUISITION_SOURCES:
            raise ValueError(
                "acquisition_source must be one of "
                f"{ACQUISITION_SOURCES}"
            )
        _finite(self.scan_time_us, "scan_time_us", positive=True)
        _attenuation(self.output_att1_db, "output_att1_db")
        _attenuation(self.output_att2_db, "output_att2_db")
        _attenuation(self.input_attenuation_db, "input_attenuation_db")
        input_dc_gain = _finite(self.input_dc_gain_db, "input_dc_gain_db")
        if not -6.0 <= input_dc_gain <= 26.0:
            raise ValueError("input_dc_gain_db must be in [-6, 26] dB")
        for value, name in (
            (self.output_filter_type, "output_filter_type"),
            (self.readout_filter_type, "readout_filter_type"),
        ):
            if value not in FILTER_TYPES:
                raise ValueError(f"{name} must be one of {FILTER_TYPES}")
        for value, name in (
            (self.output_filter_cutoff_ghz, "output filter cutoff"),
            (self.output_filter_bandwidth_ghz, "output filter bandwidth"),
            (self.readout_filter_cutoff_ghz, "readout filter cutoff"),
            (self.readout_filter_bandwidth_ghz, "readout filter bandwidth"),
        ):
            _finite(value, name, positive=True)
        _finite(self.path_loss_db, "path_loss_db")
        low = _integer(self.fit_trim_low, "fit_trim_low")
        high = _integer(self.fit_trim_high, "fit_trim_high")
        if low + high > gains.size - 2:
            raise ValueError("fit trimming must leave at least two gain points")
        if _integer(self.nqz, "nqz", 1) not in (1, 2):
            raise ValueError("nqz must be 1 or 2")
        if _integer(self.readout_nqz, "readout_nqz", 1) not in (1, 2):
            raise ValueError("readout_nqz must be 1 or 2")
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
        if _finite(self.settle_seconds, "settle_seconds") < 0.0:
            raise ValueError("settle_seconds must be nonnegative")
        if not isinstance(self.force_overwrite, bool):
            raise TypeError("force_overwrite must be boolean")
        if not str(self.experiment_name).strip():
            raise ValueError("experiment_name must not be empty")

    @property
    def frequencies_mhz(self) -> np.ndarray:
        return _frequency_axis(
            self.frequency_start_mhz,
            self.frequency_end_mhz,
            self.frequency_points,
        )

    @property
    def target_powers_dbm(self) -> np.ndarray:
        start = _finite(self.power_start_dbm, "power_start_dbm")
        stop = _finite(self.power_end_dbm, "power_end_dbm")
        points = _integer(self.power_points, "power_points", 2)
        if start == stop:
            raise ValueError("start and end output power must differ")
        return np.linspace(start, stop, points)

    @property
    def gains(self) -> np.ndarray:
        return _gain_axis(
            self.gain_start,
            self.gain_end,
            self.gain_points,
            self.gain_scale,
        )

    def sweep_config(self, gain: int) -> SParameterSweepConfig:
        return SParameterSweepConfig(
            output_ch=self.output_ch,
            readout_ch=self.readout_ch,
            frequency_start_mhz=self.frequency_start_mhz,
            frequency_end_mhz=self.frequency_end_mhz,
            frequency_points=self.frequency_points,
            gain=int(gain),
            acquisition_source=self.acquisition_source,
            scan_time_us=self.scan_time_us,
            # Input calibration already sweeps gain in software.  One AVG
            # capture per frequency/gain point keeps that sweep cardinality
            # unchanged; scan_time_us controls the FPGA integration length.
            avg_repetitions=1,
            output_att1_db=self.output_att1_db,
            output_att2_db=self.output_att2_db,
            output_board_type=self.output_board_type,
            input_board_type=self.input_board_type,
            output_filter_type=self.output_filter_type,
            output_filter_cutoff_ghz=self.output_filter_cutoff_ghz,
            output_filter_bandwidth_ghz=self.output_filter_bandwidth_ghz,
            readout_attenuation_db=self.input_attenuation_db,
            readout_dc_gain_db=self.input_dc_gain_db,
            readout_filter_type=self.readout_filter_type,
            readout_filter_cutoff_ghz=self.readout_filter_cutoff_ghz,
            readout_filter_bandwidth_ghz=self.readout_filter_bandwidth_ghz,
            nqz=self.nqz,
            readout_nqz=self.readout_nqz,
            margin_input_samples=self.margin_input_samples,
            fpga_trigger_delay_us=self.fpga_trigger_delay_us,
            force_overwrite=self.force_overwrite,
            settle_seconds=self.settle_seconds,
        )


@dataclass
class StoredCalibrationRun:
    run_id: int
    guid: str
    database_path: Path
    row_count: int
    board_type: str
    dataset: Any = None
    result: Optional[Mapping[str, Any]] = None


class KeysightFftPowerMeter:
    """Minimal PyVISA adapter for the calibration notebook's FFT marker flow."""

    def __init__(self, config: OscilloscopeConfig):
        self.config = config
        self.resource_manager = None
        self.instrument = None
        self.idn = ""
        self.last_reading_count = 0
        self.last_rejected_reading_count = 0
        self.cancel_check: Optional[CancellationCheck] = None

    def __enter__(self) -> "KeysightFftPowerMeter":
        if not self.config.visa_resource.strip():
            raise ValueError("oscilloscope VISA resource must not be empty")
        try:
            import pyvisa
        except ImportError as exc:
            raise RuntimeError(
                "PyVISA is required for oscilloscope power calibration; "
                "install PyVISA==1.16.2"
            ) from exc
        self.resource_manager = pyvisa.ResourceManager()
        self.instrument = self.resource_manager.open_resource(self.config.visa_resource)
        self.instrument.timeout = int(self.config.timeout_ms)
        self.instrument.write_termination = "\n"
        self.instrument.read_termination = "\n"
        self.idn = str(self.instrument.query("*IDN?")).strip()
        self.instrument.write(":RUN")
        self.instrument.write(f":CHANnel{int(self.config.channel)}:IMPedance FIFTy")
        return self

    def __exit__(self, *_exc) -> None:
        if self.instrument is not None:
            self.instrument.close()
            self.instrument = None
        if self.resource_manager is not None:
            self.resource_manager.close()
            self.resource_manager = None

    def configure_frequency(self, frequency_mhz: float) -> None:
        if self.instrument is None:
            raise RuntimeError("oscilloscope is not open")
        function = int(self.config.fft_function)
        channel = int(self.config.channel)
        frequency_hz = float(frequency_mhz) * 1.0e6
        span_hz = float(self.config.span_mhz) * 1.0e6
        commands = (
            f":FUNCtion{function}:DISPlay ON",
            f":FUNCtion{function}:OPERation FFT",
            f":FUNCtion{function}:SOURce CHANnel{channel}",
            f":FUNCtion{function}:CENTer {frequency_hz:.12g}",
            f":FUNCtion{function}:SPAN {span_hz:.12g}",
            ":SYSTem:PRECision ON",
            ":MARKer:MODE WAVeform",
            f":MARKer:X1Y1Source MATH{function}",
            f":MARKer:X1Position {frequency_hz:.12g}",
        )
        for command in commands:
            self.instrument.write(command)

    def measure_power_dbm(self, frequency_mhz: float) -> float:
        _check_cancel(self.cancel_check)
        self.configure_frequency(frequency_mhz)
        if self.config.settle_seconds:
            deadline = time.monotonic() + float(self.config.settle_seconds)
            while True:
                _check_cancel(self.cancel_check)
                remaining = deadline - time.monotonic()
                if remaining <= 0.0:
                    break
                time.sleep(min(0.05, remaining))
        readings = []
        for _index in range(int(self.config.average_count)):
            _check_cancel(self.cancel_check)
            response = self.instrument.query(":MARKer:Y1Position?")
            readings.append(float(str(response).strip()))
            if self.config.sample_interval_seconds:
                deadline = (
                    time.monotonic() + float(self.config.sample_interval_seconds)
                )
                while True:
                    _check_cancel(self.cancel_check)
                    remaining = deadline - time.monotonic()
                    if remaining <= 0.0:
                        break
                    time.sleep(min(0.05, remaining))
        values = np.asarray(readings, dtype=float)
        valid = np.asarray(
            [_valid_oscilloscope_power_dbm(value) for value in values],
            dtype=bool,
        )
        self.last_reading_count = int(values.size)
        self.last_rejected_reading_count = int(np.count_nonzero(~valid))
        valid_values = values[valid]
        if valid_values.size < 1:
            invalid_value = values[np.flatnonzero(~valid)[0]]
            raise InvalidOscilloscopePowerError(
                "all oscilloscope FFT readings were invalid; "
                + _invalid_power_message(float(invalid_value))
            )
        measured_power = float(np.mean(valid_values))
        if not _valid_oscilloscope_power_dbm(measured_power):
            raise InvalidOscilloscopePowerError(
                _invalid_power_message(measured_power)
            )
        return measured_power


def _run_tone_program(
    soc: Any,
    soccfg: Any,
    output_ch: int,
    nqz: int,
    frequency_mhz: float,
    gain: int,
    length_cycles: int,
) -> float:
    """Start or stop one generator using an ASM-v1 periodic/oneshot command.

    A nonzero-gain calibration tone runs periodically until a later stop
    program is issued. ``length_cycles`` therefore describes only the short
    repeated word and is clamped to the generator's 16-bit length field; it
    never limits the total oscilloscope acquisition time.
    """
    try:
        from qick.asm_v1 import QickProgram
    except ImportError as exc:
        raise RuntimeError("QICK ASM v1 is required for output calibration") from exc
    program = QickProgram(soccfg)
    program.declare_gen(ch=int(output_ch), nqz=int(nqz))
    frequency_word = program.freq2reg(float(frequency_mhz), gen_ch=int(output_ch))
    periodic = int(gain) != 0
    periodic_word_cycles = min(
        max(RF_STOP_WORD_CYCLES, int(length_cycles)),
        MAX_RF_PERIODIC_WORD_CYCLES,
    )
    program.set_pulse_registers(
        ch=int(output_ch),
        style="const",
        freq=frequency_word,
        phase=0,
        gain=int(gain),
        length=(periodic_word_cycles if periodic else RF_STOP_WORD_CYCLES),
        phrst=0,
        stdysel="last" if periodic else "zero",
        mode="periodic" if periodic else "oneshot",
    )
    program.pulse(ch=int(output_ch), t=0)
    program.end()
    program.run(soc)
    try:
        return float(program.reg2freq(frequency_word, gen_ch=int(output_ch)))
    except (AttributeError, TypeError):
        return float(frequency_mhz)


def _configure_output_chain(
    soc: Any, config: OutputPowerCalibrationConfig
) -> Mapping[str, Any]:
    if config.output_board_type == "RF_Out":
        actual_att1, actual_att2 = soc.rfb_set_gen_rf(
            config.output_ch,
            config.output_att1_db,
            config.output_att2_db,
        )
    else:
        soc.rfb_set_gen_dc(config.output_ch)
        actual_att1 = 0.0
        actual_att2 = 0.0
    if config.output_board_type == "RF_Out":
        soc.rfb_set_gen_filter(
            config.output_ch,
            fc=config.output_filter_cutoff_ghz,
            bw=config.output_filter_bandwidth_ghz,
            ftype=config.output_filter_type,
        )
    return {
        "output_ch": config.output_ch,
        "board_type": config.output_board_type,
        "att1_db": float(actual_att1),
        "att2_db": float(actual_att2),
        "attenuators_present": config.output_board_type == "RF_Out",
        "filter_type": config.output_filter_type,
        "filter_cutoff_ghz": config.output_filter_cutoff_ghz,
        "filter_bandwidth_ghz": config.output_filter_bandwidth_ghz,
    }


def _store_output_calibration(
    config: OutputPowerCalibrationConfig,
    frequencies_mhz: np.ndarray,
    gains: np.ndarray,
    powers_dbm: np.ndarray,
    *,
    rf_settings: Mapping[str, Any],
    scope_identity: str,
    excluded_points: Tuple[Mapping[str, Any], ...] = (),
) -> StoredCalibrationRun:
    valid_power = (
        np.isfinite(powers_dbm)
        & (powers_dbm >= MIN_VALID_OSCILLOSCOPE_POWER_DBM)
        & (powers_dbm <= MAX_VALID_OSCILLOSCOPE_POWER_DBM)
    )
    valid_count = int(np.count_nonzero(valid_power))
    excluded_count = int(valid_power.size - valid_count)
    if valid_count < 1:
        raise RuntimeError(
            "oscilloscope calibration produced no valid power points; "
            f"accepted range is {MIN_VALID_OSCILLOSCOPE_POWER_DBM:g}.."
            f"{MAX_VALID_OSCILLOSCOPE_POWER_DBM:g} dBm"
        )
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
            "QCoDeS==0.58.0 is required for calibration storage"
        ) from exc
    database_path = Path(config.database_path).expanduser().resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    staging, local_path = _prepare_local_database(database_path)
    try:
        initialise_or_create_database_at(str(local_path))
        sample_name = _sample_name(
            config.output_board_type,
            config.sample_name,
            frequencies_mhz,
        )
        experiment = load_or_create_experiment(config.experiment_name, sample_name)
        measurement = Measurement(exp=experiment, station=Station())
        gain_parameter = Parameter("gain", label="QICK DAC gain", unit="")
        frequency_parameter = Parameter("freq", label="Frequency", unit="MHz")
        power_parameter = Parameter("pwr", label="Output power", unit="dBm")
        measurement.register_parameter(gain_parameter)
        measurement.register_parameter(frequency_parameter)
        measurement.register_parameter(
            power_parameter,
            setpoints=(gain_parameter, frequency_parameter),
        )
        metadata = {
            "schema": "qstl-qick-output-power-calibration-v2",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "board_type": config.output_board_type,
            "configuration": {
                **asdict(config),
                "oscilloscope": asdict(config.oscilloscope),
            },
            "rf_settings_actual": dict(rf_settings),
            "oscilloscope_identity": scope_identity,
            "formula": "P(f,g)=response(f)+20*log10(g/32766)-attenuation_delta",
            "measurement_validation": {
                "minimum_power_dbm": MIN_VALID_OSCILLOSCOPE_POWER_DBM,
                "maximum_power_dbm": MAX_VALID_OSCILLOSCOPE_POWER_DBM,
                "valid_point_count": valid_count,
                "excluded_point_count": excluded_count,
                "excluded_points": [dict(point) for point in excluded_points],
            },
        }
        with measurement.run(
            write_in_background=False,
            in_memory_cache=False,
        ) as datasaver:
            dataset = datasaver.dataset
            dataset.add_metadata(
                "Attenuation",
                _json_text(
                    {
                        "att1": float(rf_settings["att1_db"]),
                        "att2": float(rf_settings["att2_db"]),
                    }
                ),
            )
            dataset.add_metadata("Calibration_Config", _json_text(metadata))
            if config.notes:
                dataset.add_metadata("calibration_notes", config.notes)
            for gain_index, gain in enumerate(gains):
                for frequency_index, frequency in enumerate(frequencies_mhz):
                    if not valid_power[gain_index, frequency_index]:
                        continue
                    datasaver.add_result(
                        (gain_parameter, int(gain)),
                        (frequency_parameter, float(frequency)),
                        (
                            power_parameter,
                            float(powers_dbm[gain_index, frequency_index]),
                        ),
                    )
            datasaver.flush_data_to_database()
        guid = str(dataset.guid)
        run_id = int(dataset.run_id)
        dataset.conn.close()
        _checkpoint_sqlite_database(local_path)
        _publish_local_database(local_path, database_path)
        initialise_or_create_database_at(str(database_path))
        final_dataset = load_by_guid(guid)
        return StoredCalibrationRun(
            run_id=run_id,
            guid=guid,
            database_path=database_path,
            row_count=valid_count,
            board_type=config.output_board_type,
            dataset=final_dataset,
            result={
                "frequencies_mhz": frequencies_mhz.tolist(),
                "gains": gains.tolist(),
                "powers_dbm": [
                    [
                        float(value) if valid_power[gain_index, frequency_index] else None
                        for frequency_index, value in enumerate(row)
                    ]
                    for gain_index, row in enumerate(powers_dbm)
                ],
                "valid_point_count": valid_count,
                "excluded_point_count": excluded_count,
                "excluded_points": [dict(point) for point in excluded_points],
            },
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def run_output_power_calibration(
    *,
    connection_config: QickConnectionConfig,
    calibration_config: OutputPowerCalibrationConfig,
    connector: Optional[Callable[..., Tuple[Any, Any]]] = None,
    power_meter_factory: Optional[Callable[[OscilloscopeConfig], Any]] = None,
    tone_runner: Optional[ToneRunner] = None,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_check: Optional[CancellationCheck] = None,
) -> StoredCalibrationRun:
    """Measure QICK output power over gain and frequency and save one run."""
    if (
        not calibration_config.oscilloscope.visa_resource.strip()
        and power_meter_factory is None
    ):
        raise ValueError("oscilloscope VISA resource must not be empty")
    tone_runner = tone_runner or _run_tone_program
    power_meter_factory = power_meter_factory or KeysightFftPowerMeter
    frequencies = calibration_config.frequencies_mhz
    gains = calibration_config.gains
    total = int(frequencies.size * gains.size)
    _check_cancel(cancel_check)
    _emit_progress(progress_callback, 0, "Connecting to QICK")
    soc, soccfg = connect_qick(connection_config, connector=connector)
    _check_cancel(cancel_check)
    _emit_progress(progress_callback, 3, "Configuring calibrated RF output chain")
    rf_settings = _configure_output_chain(soc, calibration_config)
    _check_cancel(cancel_check)
    measured = np.full((gains.size, frequencies.size), np.nan, dtype=float)
    actual_frequencies = np.empty(frequencies.size, dtype=float)
    completed = 0
    scope_identity = ""
    excluded_points = []
    try:
        with power_meter_factory(calibration_config.oscilloscope) as meter:
            if isinstance(meter, KeysightFftPowerMeter):
                meter.cancel_check = cancel_check
            scope_identity = str(getattr(meter, "idn", ""))
            for frequency_index, requested_frequency in enumerate(frequencies):
                for gain_index, gain in enumerate(gains):
                    _check_cancel(cancel_check)
                    actual_frequency = tone_runner(
                        soc,
                        soccfg,
                        calibration_config.output_ch,
                        calibration_config.nqz,
                        float(requested_frequency),
                        int(gain),
                        calibration_config.tone_length_fabric_cycles,
                    )
                    if gain_index == 0:
                        actual_frequencies[frequency_index] = actual_frequency
                    try:
                        measured_power = meter.measure_power_dbm(actual_frequency)
                    except InvalidOscilloscopePowerError as exc:
                        measured_power = np.nan
                        invalid_reason = str(exc)
                    else:
                        if _valid_oscilloscope_power_dbm(measured_power):
                            measured_power = float(measured_power)
                            invalid_reason = ""
                        else:
                            invalid_reason = _invalid_power_message(measured_power)
                            measured_power = np.nan
                    _check_cancel(cancel_check)
                    measured[gain_index, frequency_index] = measured_power
                    if invalid_reason:
                        excluded_points.append(
                            {
                                "frequency_mhz": float(actual_frequency),
                                "gain": int(gain),
                                "reason": invalid_reason,
                            }
                        )
                    completed += 1
                    _emit_progress(
                        progress_callback,
                        5 + round(83 * completed / total),
                        (
                            f"Excluded invalid scope point {completed}/{total}: "
                            f"{actual_frequency:.9g} MHz, gain {int(gain)}"
                            if invalid_reason
                            else (
                                f"Scope calibration {completed}/{total}: "
                                f"{actual_frequency:.9g} MHz, gain {int(gain)}"
                            )
                        ),
                    )
    finally:
        try:
            tone_runner(
                soc,
                soccfg,
                calibration_config.output_ch,
                calibration_config.nqz,
                float(frequencies[0]),
                0,
                3,
            )
        except Exception:
            pass
    _check_cancel(cancel_check)
    _emit_progress(progress_callback, 90, "Saving output calibration to QCoDeS")
    stored = _store_output_calibration(
        calibration_config,
        actual_frequencies,
        gains,
        measured,
        rf_settings=rf_settings,
        scope_identity=scope_identity,
        excluded_points=tuple(excluded_points),
    )
    _emit_progress(
        progress_callback,
        100,
        (
            f"Output calibration Run {stored.run_id} saved "
            f"({stored.row_count}/{total} valid points"
            + (
                f", {len(excluded_points)} excluded)"
                if excluded_points
                else ")"
            )
        ),
    )
    return stored


def _store_input_calibration(
    config: InputPowerCalibrationConfig,
    frequencies_mhz: np.ndarray,
    gains: np.ndarray,
    adc_magnitude_db: np.ndarray,
    input_power_dbm: np.ndarray,
    slopes: np.ndarray,
    intercepts: np.ndarray,
    *,
    output_run_id: int,
    rf_settings: Mapping[str, Any],
    acquisition_details: Mapping[str, Any],
    power_plan: Optional[Mapping[str, Any]] = None,
) -> StoredCalibrationRun:
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
            "QCoDeS==0.58.0 is required for calibration storage"
        ) from exc
    database_path = Path(config.database_path).expanduser().resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    staging, local_path = _prepare_local_database(database_path)
    try:
        initialise_or_create_database_at(str(local_path))
        sample_name = _sample_name(
            config.input_board_type,
            config.sample_name,
            frequencies_mhz,
        )
        experiment = load_or_create_experiment(config.experiment_name, sample_name)
        measurement = Measurement(exp=experiment, station=Station())
        gain_parameter = Parameter("gain", label="QICK DAC gain", unit="")
        frequency_parameter = Parameter("freq", label="Frequency", unit="MHz")
        measured_parameter = Parameter(
            "measured_value",
            label="ADC magnitude",
            unit="dB ADC",
        )
        input_power_parameter = Parameter(
            "meas_in_pwr",
            label="Known input power",
            unit="dBm",
        )
        slope_parameter = Parameter("meas_slope", label="ADC calibration slope")
        intercept_parameter = Parameter(
            "meas_intercept",
            label="ADC calibration intercept",
            unit="dBm",
        )
        measurement.register_parameter(gain_parameter)
        measurement.register_parameter(frequency_parameter)
        measurement.register_parameter(
            measured_parameter,
            setpoints=(gain_parameter, frequency_parameter),
        )
        measurement.register_parameter(
            input_power_parameter,
            setpoints=(gain_parameter, frequency_parameter),
        )
        measurement.register_parameter(
            slope_parameter, setpoints=(frequency_parameter,)
        )
        measurement.register_parameter(
            intercept_parameter,
            setpoints=(frequency_parameter,),
        )
        gain_codes = (np.broadcast_to(gains[:, None], adc_magnitude_db.shape)
                      if power_plan is None else power_plan["gain_codes"])
        power_estimation = ({} if power_plan is None else {
            **power_plan["model_metadata"],
            "warnings": power_plan["warnings"],
            "gain_codes": gain_codes.tolist(),
            "output_power_dbm": power_plan["output_power_dbm"].tolist(),
            "requested_output_powers_dbm": config.target_powers_dbm.tolist() if config.power_sweep_enabled else None,
        })
        result_metadata = {
            "freq": frequencies_mhz.tolist(),
            "att1": float(config.output_att1_db),
            "att2": float(config.output_att2_db),
            "pwr_id": int(output_run_id),
            "output_run_id": int(output_run_id),
            "out_ch": int(config.output_ch),
            "in_ch": int(config.readout_ch),
            "acquisition_source": str(config.acquisition_source),
        }
        config_metadata = {
            "schema": "qstl-qick-adc-input-power-calibration-v2",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "output_board_type": config.output_board_type,
            "input_board_type": config.input_board_type,
            "output_run_id": int(output_run_id),
            "output_ch": int(config.output_ch),
            "readout_ch": int(config.readout_ch),
            "output_att1_db": float(config.output_att1_db),
            "output_att2_db": float(config.output_att2_db),
            "input_attenuation_db": float(config.input_attenuation_db),
            "input_dc_gain_db": float(config.input_dc_gain_db),
            "path_loss_db": float(config.path_loss_db),
            "fit_trim_low": int(config.fit_trim_low),
            "fit_trim_high": int(config.fit_trim_high),
            "acquisition_source": str(config.acquisition_source),
            "acquisition_details": dict(acquisition_details),
            "formula": (
                "input_power_dbm = slope(f) * "
                "20*log10(hypot(mean_i,mean_q)) + intercept(f)"
            ),
            "configuration": asdict(config),
            "rf_settings_actual": dict(rf_settings),
            "output_power_estimation": power_estimation,
        }
        with measurement.run(
            write_in_background=False,
            in_memory_cache=False,
        ) as datasaver:
            dataset = datasaver.dataset
            dataset.add_metadata("Calibration_Result", _json_text(result_metadata))
            dataset.add_metadata("Calibration_Config", _json_text(config_metadata))
            dataset.add_metadata(
                "Attenuation",
                _json_text(
                    {
                        "att1": float(config.output_att1_db),
                        "att2": float(config.output_att2_db),
                    }
                ),
            )
            if config.notes:
                dataset.add_metadata("calibration_notes", config.notes)
            for gain_index, gain in enumerate(gains):
                for frequency_index, frequency in enumerate(frequencies_mhz):
                    datasaver.add_result(
                        (gain_parameter, int(gain_codes[gain_index, frequency_index])),
                        (frequency_parameter, float(frequency)),
                        (
                            measured_parameter,
                            float(adc_magnitude_db[gain_index, frequency_index]),
                        ),
                        (
                            input_power_parameter,
                            float(input_power_dbm[gain_index, frequency_index]),
                        ),
                    )
            for frequency_index, frequency in enumerate(frequencies_mhz):
                datasaver.add_result(
                    (frequency_parameter, float(frequency)),
                    (slope_parameter, float(slopes[frequency_index])),
                    (intercept_parameter, float(intercepts[frequency_index])),
                )
            datasaver.flush_data_to_database()
        guid = str(dataset.guid)
        run_id = int(dataset.run_id)
        dataset.conn.close()
        _checkpoint_sqlite_database(local_path)
        _publish_local_database(local_path, database_path)
        initialise_or_create_database_at(str(database_path))
        final_dataset = load_by_guid(guid)
        return StoredCalibrationRun(
            run_id=run_id,
            guid=guid,
            database_path=database_path,
            row_count=int(gains.size * frequencies_mhz.size + frequencies_mhz.size),
            board_type=config.input_board_type,
            dataset=final_dataset,
            result={
                "frequencies_mhz": frequencies_mhz.tolist(),
                "gains": gains.tolist(),
                "gain_codes": gain_codes.tolist(),
                "output_power_estimation": power_estimation,
                "adc_magnitude_db": adc_magnitude_db.tolist(),
                "input_power_dbm": input_power_dbm.tolist(),
                "slopes": slopes.tolist(),
                "intercepts_dbm": intercepts.tolist(),
                "output_run_id": int(output_run_id),
                "acquisition_source": str(config.acquisition_source),
                "acquisition_details": dict(acquisition_details),
            },
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def prepare_input_power_plan(config, frequencies_mhz=None, *, calibration=None,
                             output_att1_db=None, output_att2_db=None):
    """Resolve the same output powers and integer gains for preview and acquisition."""
    frequencies = np.asarray(
        config.frequencies_mhz if frequencies_mhz is None else frequencies_mhz, float
    )
    if calibration is None:
        calibration = CalibrationDatabase(config.database_path).output_calibration(
            config.output_board_type, frequencies, nqz=config.nqz,
            output_filter_type=config.output_filter_type,
            output_filter_cutoff_ghz=config.output_filter_cutoff_ghz,
            output_filter_bandwidth_ghz=config.output_filter_bandwidth_ghz,
        )
    attenuation = {
        "output_att1_db": (config.output_att1_db if output_att1_db is None else output_att1_db)
        if config.output_board_type == "RF_Out" else 0.0,
        "output_att2_db": (config.output_att2_db if output_att2_db is None else output_att2_db)
        if config.output_board_type == "RF_Out" else 0.0,
    }
    regression = OutputGainRegression(calibration) if (
        config.use_gain_regression or config.power_sweep_enabled
    ) else None
    model = regression or calibration
    if config.power_sweep_enabled:
        gains = regression.gains_for_power(
            frequencies[None, :], config.target_powers_dbm[:, None], **attenuation
        )
        if any(np.unique(column).size != gains.shape[0] for column in gains.T):
            raise ValueError("Selected powers collapse to duplicate integer DAC gains; use fewer or more widely spaced powers")
    else:
        gains = np.broadcast_to(config.gains[:, None], (config.gains.size, frequencies.size)).copy()
    powers = model.output_power_dbm(frequencies[None, :], gains, **attenuation)
    warnings = regression.warnings(frequencies[None, :], gains) if regression else []
    return {
        "calibration": calibration, "regression": regression,
        "frequencies_mhz": frequencies, "gain_codes": gains,
        "output_power_dbm": powers, "attenuation": attenuation,
        "warnings": warnings,
        "model_metadata": regression.metadata() if regression else {"model": "legacy_linear_amplitude"},
    }


def run_input_power_calibration(
    *,
    connection_config: QickConnectionConfig,
    calibration_config: InputPowerCalibrationConfig,
    tproc_mhz: Optional[float] = None,
    connector: Optional[Callable[..., Tuple[Any, Any]]] = None,
    program_factory: Optional[Callable[..., Any]] = None,
    acquisition_callback: Optional[Callable[[Any, Any], Any]] = None,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_check: Optional[CancellationCheck] = None,
) -> StoredCalibrationRun:
    """Fit ADC dB values to actual connector input power at each frequency."""
    _check_cancel(cancel_check)
    _emit_progress(progress_callback, 0, "Connecting to QICK")
    soc, soccfg = connect_qick(connection_config, connector=connector)
    _check_cancel(cancel_check)
    gains = (np.ones(calibration_config.power_points, dtype=np.int64)
             if calibration_config.power_sweep_enabled else calibration_config.gains)
    power_plan = None
    program_factory = program_factory or build_sparameter_program

    def make_program(gain_index: int) -> Any:
        _check_cancel(cancel_check)
        _emit_progress(
            progress_callback,
            (1 if power_plan is None else 6) if gain_index == 0 else 7 + round(76 * gain_index / gains.size),
            (
                f"Preparing ADC calibration gain {gain_index + 1}/"
                f"{gains.size}: {int(gains[gain_index])}"
            ),
        )
        sweep = calibration_config.sweep_config(int(gains[gain_index]))
        if calibration_config.power_sweep_enabled and power_plan is not None:
            codes = power_plan["gain_codes"][gain_index]
            relative_db = 20.0 * np.log10(codes / float(np.max(codes)))
            sweep = replace(
                sweep, gain=int(codes[0]),
                calibrated_gain_table=tuple(int(code) for code in codes),
                calibrated_frequency_point_count=int(codes.size),
                calibrated_output_power_dbm=float(calibration_config.target_powers_dbm[gain_index]),
                calibrated_nominal_gain_code=int(np.max(codes)),
                calibrated_reference_response_dbm=float(np.min(
                    power_plan["regression"].output_power_dbm(frequencies, MAX_QICK_GAIN, **power_plan["attenuation"])
                )),
                calibrated_correction_min_db=float(np.min(relative_db)),
                calibrated_correction_max_db=float(np.max(relative_db)),
                calibration_output_run_id=int(power_plan["calibration"].summary.run_id),
                calibration_output_sample_name=power_plan["calibration"].summary.sample_name,
            )
        return program_factory(
            soccfg,
            sweep,
            tproc_mhz=tproc_mhz,
        )

    # Build only the first gain up front.  Long input calibrations should reach
    # their first DDR arm immediately instead of materializing every program
    # before acquisition starts.
    first_program = make_program(0)
    _check_cancel(cancel_check)
    frequencies = np.asarray(first_program.frequencies_mhz, dtype=float)
    _emit_progress(progress_callback, 3, "Selecting matching output calibration")
    power_plan = prepare_input_power_plan(calibration_config, frequencies)
    output_calibration = power_plan["calibration"]
    _check_cancel(cancel_check)
    _emit_progress(progress_callback, 5, "Configuring RF output and input chains")
    rf_settings = configure_sparameter_rf_board(
        soc,
        calibration_config.sweep_config(int(gains[0])),
    )
    actual_output = dict(rf_settings.get("output", {}))
    actual_input = dict(rf_settings.get("readout", {}))
    output_att1 = float(
        actual_output.get("commanded_att1_db", calibration_config.output_att1_db)
    )
    output_att2 = float(
        actual_output.get("commanded_att2_db", calibration_config.output_att2_db)
    )
    input_attenuation = float(
        actual_input.get(
            "commanded_attenuation_db",
            (
                calibration_config.input_attenuation_db
                if calibration_config.input_board_type == "RF_In"
                else 0.0
            ),
        )
    )
    input_dc_gain = float(
        actual_input.get(
            "commanded_dc_gain_db",
            (
                calibration_config.input_dc_gain_db
                if calibration_config.input_board_type == "DC_In"
                else 0.0
            ),
        )
    )
    power_plan = prepare_input_power_plan(
        calibration_config, frequencies, calibration=output_calibration,
        output_att1_db=output_att1, output_att2_db=output_att2,
    )
    gains = power_plan["gain_codes"][:, 0]
    if calibration_config.power_sweep_enabled:
        first_program = make_program(0)
    for warning in power_plan["warnings"]:
        _emit_progress(progress_callback, 6, "Warning: " + warning)
    measured_db = np.empty((gains.size, frequencies.size), dtype=float)
    known_input_dbm = power_plan["output_power_dbm"] - float(calibration_config.path_loss_db)
    acquisition_details: dict[str, Any] = {}
    start_action = (
        "Arming FIR DDR"
        if calibration_config.acquisition_source == "fir_ddr"
        else "Starting AVG buffer"
    )
    point_label = (
        "FIR"
        if calibration_config.acquisition_source == "fir_ddr"
        else "AVG buffer"
    )
    for gain_index, gain in enumerate(gains):
        _check_cancel(cancel_check)
        program = first_program if gain_index == 0 else make_program(gain_index)
        if not np.array_equal(program.frequencies_mhz, frequencies):
            raise RuntimeError("input calibration frequency grids are inconsistent")

        progress_start = 7 + round(76 * gain_index / gains.size)
        progress_stop = 7 + round(76 * (gain_index + 1) / gains.size)
        _emit_progress(
            progress_callback,
            progress_start,
            (
                f"{start_action} for ADC calibration gain "
                f"{gain_index + 1}/{gains.size}: "
                f"{frequencies.size} points x "
                f"{calibration_config.scan_time_us:.9g} us"
            ),
        )

        def counter_progress(completed: int, total: int) -> None:
            _check_cancel(cancel_check)
            fraction = 1.0 if total <= 0 else completed / total
            fraction = max(0.0, min(1.0, float(fraction)))
            percent = progress_start + round(
                (progress_stop - progress_start) * fraction
            )
            if completed >= total > 0:
                if calibration_config.acquisition_source == "fir_ddr":
                    completion = "acquisition complete; reading FIR DDR"
                else:
                    completion = "AVG buffer acquisition complete"
                message = (
                    f"ADC calibration gain {gain_index + 1}/{gains.size}: "
                    f"{completion}"
                )
            else:
                message = (
                    f"ADC calibration gain {gain_index + 1}/{gains.size}: "
                    f"{point_label} point {completed}/{total}"
                )
            _emit_progress(progress_callback, percent, message)

        if acquisition_callback is not None:
            result = acquisition_callback(soc, program)
        elif calibration_config.acquisition_source == "fir_ddr":
            result = program.acquire_fir_ddr(
                soc,
                counter_progress=(
                    counter_progress if progress_callback is not None else None
                ),
                cancel_check=cancel_check,
            )
        else:
            result = program.acquire_avg_buffer(
                soc,
                counter_progress=(
                    counter_progress if progress_callback is not None else None
                ),
                cancel_check=cancel_check,
            )
        _check_cancel(cancel_check)
        result_source = str(
            getattr(result, "acquisition_source", calibration_config.acquisition_source)
        )
        if result_source != calibration_config.acquisition_source:
            raise RuntimeError(
                "input calibration acquisition source changed from "
                f"{calibration_config.acquisition_source!r} to {result_source!r}"
            )
        actual_integration_time_us = getattr(
            result,
            "integration_time_us",
            None,
        )
        if actual_integration_time_us is None:
            actual_integration_time_us = calibration_config.scan_time_us
        current_details = {
            "source": result_source,
            "requested_integration_time_us": float(
                calibration_config.scan_time_us
            ),
            "actual_integration_time_us": float(
                actual_integration_time_us
            ),
            "accumulation_repetitions": int(
                getattr(result, "accumulation_repetitions", 1)
            ),
        }
        if not acquisition_details:
            acquisition_details = current_details
        elif acquisition_details != current_details:
            raise RuntimeError(
                "input calibration acquisition timing changed between gain points"
            )
        if not np.array_equal(result.frequencies_mhz, frequencies):
            raise RuntimeError("acquired input-calibration frequency grid changed")
        measured_db[gain_index] = np.asarray(result.magnitude_db, dtype=float)
        _emit_progress(
            progress_callback,
            progress_stop,
            f"ADC calibration gain {gain_index + 1}/{gains.size}: {int(gain)}",
        )
    low = int(calibration_config.fit_trim_low)
    high = int(calibration_config.fit_trim_high)
    stop = gains.size - high if high else gains.size
    fit_slice = slice(low, stop)
    slopes = np.empty(frequencies.size, dtype=float)
    intercepts = np.empty(frequencies.size, dtype=float)
    for frequency_index in range(frequencies.size):
        _check_cancel(cancel_check)
        x_values = measured_db[fit_slice, frequency_index]
        y_values = known_input_dbm[fit_slice, frequency_index]
        if np.unique(x_values).size < 2:
            raise RuntimeError(
                f"ADC values at {frequencies[frequency_index]:.9g} MHz "
                "do not contain two distinct fit points"
            )
        slopes[frequency_index], intercepts[frequency_index] = np.polyfit(
            x_values,
            y_values,
            1,
        )
    adjusted_config = replace(
        calibration_config,
        input_attenuation_db=input_attenuation,
        input_dc_gain_db=input_dc_gain,
        output_att1_db=output_att1,
        output_att2_db=output_att2,
    )
    _check_cancel(cancel_check)
    _emit_progress(progress_callback, 86, "Saving ADC input calibration to QCoDeS")
    stored = _store_input_calibration(
        adjusted_config,
        frequencies,
        gains,
        measured_db,
        known_input_dbm,
        slopes,
        intercepts,
        output_run_id=output_calibration.summary.run_id,
        rf_settings=rf_settings,
        acquisition_details=acquisition_details,
        power_plan=power_plan,
    )
    _emit_progress(
        progress_callback, 100, f"Input calibration Run {stored.run_id} saved"
    )
    return stored


__all__ = [
    "InvalidOscilloscopePowerError",
    "InputPowerCalibrationConfig",
    "KeysightFftPowerMeter",
    "MAX_VALID_OSCILLOSCOPE_POWER_DBM",
    "MIN_VALID_OSCILLOSCOPE_POWER_DBM",
    "OscilloscopeConfig",
    "OutputPowerCalibrationConfig",
    "StoredCalibrationRun",
    "run_input_power_calibration",
    "run_output_power_calibration",
]
