"""Frequency-response compensation for QICK RF sweeps.

The calibration notebooks store one row per ``(frequency, gain)`` point with
the measured output power in dBm.  Gain is linear in DAC voltage amplitude, so
the gain axis is removed analytically.  The remaining frequency response is
used only to build a relative gain-correction table for tProcessor DMEM; raw
power-versus-gain curves are never inverted point by point.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import sqlite3
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

import numpy as np

OUTPUT_BOARD_TYPES = ("DC_Out", "RF_Out")
INPUT_BOARD_TYPES = ("DC_In", "RF_In")
BOARD_TYPES = OUTPUT_BOARD_TYPES + INPUT_BOARD_TYPES
MAX_DMEM_GAIN_ENTRIES = 4000
GAIN_DMEM_BASE_ADDRESS = 16
MAX_QICK_GAIN = 32766


def _normalize_board_name(value: str) -> str:
    return "".join(character.lower() for character in str(value) if character.isalnum())


def _validate_board_type(board_type: str, *, output: Optional[bool] = None) -> str:
    board_type = str(board_type)
    choices = BOARD_TYPES
    if output is True:
        choices = OUTPUT_BOARD_TYPES
    elif output is False:
        choices = INPUT_BOARD_TYPES
    if board_type not in choices:
        raise ValueError(f"board_type must be one of {choices}")
    return board_type


def _quote_identifier(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _json_mapping(value: Any) -> Mapping[str, Any]:
    if value in (None, ""):
        return {}
    try:
        decoded = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return decoded if isinstance(decoded, Mapping) else {}


def _frequency_values_to_mhz(values: Any, declared_unit: str = "") -> np.ndarray:
    """Normalize legacy calibration frequencies to MHz.

    Early calibration notebooks labelled values such as ``400`` as Hz even
    though QICK interpreted them as MHz.  Values already expressed as ordinary
    RF frequencies (below 100 k) are therefore retained as MHz; only values
    that look like literal Hz are divided by 1e6.
    """
    array = np.asarray(values, dtype=float)
    finite = np.abs(array[np.isfinite(array)])
    if finite.size and float(np.nanmedian(finite)) >= 100_000.0:
        return array / 1_000_000.0
    return array


@dataclass(frozen=True)
class CalibrationRunSummary:
    database_path: Path
    run_id: int
    experiment_id: int
    board_type: str
    sample_name: str
    result_table_name: str
    frequency_min_mhz: float
    frequency_max_mhz: float
    frequency_count: int
    row_count: int
    calibration_att1_db: float = 0.0
    calibration_att2_db: float = 0.0
    input_attenuation_db: float = 0.0
    input_gain_db: float = 0.0
    source_output_run_id: int = 0
    path_loss_db: float = 0.0
    purpose: str = "output_power"
    output_nqz: Optional[int] = None
    output_filter_type: str = ""
    output_filter_cutoff_ghz: Optional[float] = None
    output_filter_bandwidth_ghz: Optional[float] = None

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "database_path": str(self.database_path),
            "run_id": self.run_id,
            "experiment_id": self.experiment_id,
            "board_type": self.board_type,
            "sample_name": self.sample_name,
            "result_table_name": self.result_table_name,
            "frequency_min_mhz": self.frequency_min_mhz,
            "frequency_max_mhz": self.frequency_max_mhz,
            "frequency_count": self.frequency_count,
            "row_count": self.row_count,
            "calibration_att1_db": self.calibration_att1_db,
            "calibration_att2_db": self.calibration_att2_db,
            "input_attenuation_db": self.input_attenuation_db,
            "input_gain_db": self.input_gain_db,
            "source_output_run_id": self.source_output_run_id,
            "path_loss_db": self.path_loss_db,
            "purpose": self.purpose,
            "output_nqz": self.output_nqz,
            "output_filter_type": self.output_filter_type,
            "output_filter_cutoff_ghz": self.output_filter_cutoff_ghz,
            "output_filter_bandwidth_ghz": self.output_filter_bandwidth_ghz,
        }


@dataclass(frozen=True)
class OutputCalibrationCandidate:
    """An output calibration run ranked against the requested RF path."""

    summary: CalibrationRunSummary
    full_frequency_coverage: bool
    frequency_overlap_mhz: float
    mismatches: Tuple[str, ...] = ()

    @property
    def exact_match(self) -> bool:
        return self.full_frequency_coverage and not self.mismatches

    @property
    def display_label(self) -> str:
        summary = self.summary
        nqz = "?" if summary.output_nqz is None else str(summary.output_nqz)
        filter_name = summary.output_filter_type or "unknown"
        cutoff = (
            "?"
            if summary.output_filter_cutoff_ghz is None
            else f"{summary.output_filter_cutoff_ghz:.6g}"
        )
        bandwidth = (
            "?"
            if summary.output_filter_bandwidth_ghz is None
            else f"{summary.output_filter_bandwidth_ghz:.6g}"
        )
        match = "exact match" if self.exact_match else "candidate"
        return (
            f"Run {summary.run_id} | PCB {summary.board_type} "
            f"[{summary.sample_name}] | "
            f"NQZ {nqz} | {filter_name} "
            f"(fc {cutoff} GHz, BW {bandwidth} GHz) | "
            f"{summary.frequency_min_mhz:.6g}.."
            f"{summary.frequency_max_mhz:.6g} MHz | {match}"
        )

    @property
    def detail_text(self) -> str:
        if self.exact_match:
            return "Exact PCB, frequency coverage, Nyquist zone, and filter match."
        return "; ".join(self.mismatches)


@dataclass(frozen=True)
class GainSchedule:
    """Frequency-compensated gain words stored in tProcessor DMEM."""

    gain_codes: np.ndarray
    representative_frequencies_mhz: np.ndarray
    representative_point_indices: np.ndarray
    frequency_point_count: int
    target_power_dbm: float
    nominal_gain_code: int
    reference_response_dbm: float
    correction_db: np.ndarray
    dmem_base_address: int = GAIN_DMEM_BASE_ADDRESS

    def __post_init__(self) -> None:
        gains = np.asarray(self.gain_codes, dtype=np.int32).reshape(-1)
        frequencies = np.asarray(
            self.representative_frequencies_mhz, dtype=float
        ).reshape(-1)
        indices = np.asarray(self.representative_point_indices, dtype=np.int64).reshape(
            -1
        )
        corrections = np.asarray(self.correction_db, dtype=float).reshape(-1)
        if gains.size < 1 or gains.size > MAX_DMEM_GAIN_ENTRIES:
            raise ValueError(
                f"gain schedule must contain 1..{MAX_DMEM_GAIN_ENTRIES} entries"
            )
        if (
            frequencies.size != gains.size
            or indices.size != gains.size
            or corrections.size != gains.size
        ):
            raise ValueError("gain schedule arrays must have equal lengths")
        if int(self.frequency_point_count) < gains.size:
            raise ValueError("frequency_point_count cannot be smaller than the table")
        if np.any(gains < 0) or np.any(gains > MAX_QICK_GAIN):
            raise ValueError("gain schedule contains an out-of-range QICK gain")
        if not 1 <= int(self.nominal_gain_code) <= MAX_QICK_GAIN:
            raise ValueError("nominal gain is outside the QICK gain range")
        if not np.isfinite(float(self.reference_response_dbm)):
            raise ValueError("reference frequency response must be finite")
        if not np.all(np.isfinite(corrections)):
            raise ValueError("frequency corrections must be finite")
        if np.any(corrections > 1.0e-9):
            raise ValueError("weakest-response normalization must not boost gain")
        if int(self.dmem_base_address) < 2:
            raise ValueError("gain DMEM must not overlap the acquisition counter")
        object.__setattr__(self, "gain_codes", np.ascontiguousarray(gains))
        object.__setattr__(
            self,
            "representative_frequencies_mhz",
            np.ascontiguousarray(frequencies),
        )
        object.__setattr__(
            self,
            "representative_point_indices",
            np.ascontiguousarray(indices),
        )
        object.__setattr__(
            self,
            "correction_db",
            np.ascontiguousarray(corrections),
        )

    @property
    def table_count(self) -> int:
        return int(self.gain_codes.size)

    @property
    def compressed(self) -> bool:
        return self.table_count < int(self.frequency_point_count)

    @property
    def point_table_indices(self) -> np.ndarray:
        points = np.arange(int(self.frequency_point_count), dtype=np.int64)
        return np.minimum(
            self.table_count - 1,
            (points * self.table_count) // int(self.frequency_point_count),
        )

    @property
    def expanded_gain_codes(self) -> np.ndarray:
        return np.ascontiguousarray(self.gain_codes[self.point_table_indices])

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "target_power_dbm": float(self.target_power_dbm),
            "nominal_gain_code": int(self.nominal_gain_code),
            "reference_response_dbm": float(self.reference_response_dbm),
            "correction_db_min": float(np.min(self.correction_db)),
            "correction_db_max": float(np.max(self.correction_db)),
            "calibration_model": (
                "nominal_gain * 10**((weakest_response_db - response_db(f))/20)"
            ),
            "normalization": "weakest frequency response in requested sweep",
            "dmem_base_address": int(self.dmem_base_address),
            "dmem_entry_count": self.table_count,
            "frequency_point_count": int(self.frequency_point_count),
            "compressed": self.compressed,
            "lookup": "floor(point_index * dmem_entry_count / frequency_point_count)",
            "representative_frequency_min_mhz": float(
                self.representative_frequencies_mhz[0]
            ),
            "representative_frequency_max_mhz": float(
                self.representative_frequencies_mhz[-1]
            ),
        }


class GainPowerCalibration:
    """Relative frequency response extracted from one output-board run."""

    def __init__(
        self,
        summary: CalibrationRunSummary,
        curves: Mapping[float, Tuple[np.ndarray, np.ndarray]],
    ):
        if summary.board_type not in OUTPUT_BOARD_TYPES:
            raise ValueError("frequency-response calibration requires an output board")
        if not curves:
            raise ValueError("calibration run contains no gain/power curves")
        self.summary = summary
        self._curves = {
            float(frequency): (
                np.ascontiguousarray(gains, dtype=float),
                np.ascontiguousarray(powers, dtype=float),
            )
            for frequency, (gains, powers) in curves.items()
        }
        self.frequencies_mhz = np.asarray(sorted(self._curves), dtype=float)
        self.reference_gain = MAX_QICK_GAIN
        self.frequency_response_levels_dbm = np.asarray(
            [
                self._estimate_frequency_response_dbm(*self._curves[float(frequency)])
                for frequency in self.frequencies_mhz
            ],
            dtype=float,
        )

    def _estimate_frequency_response_dbm(
        self, gains: np.ndarray, measured_powers_dbm: np.ndarray
    ) -> float:
        """Estimate full-scale power using the linear DAC-amplitude model.

        Gain is linear in voltage amplitude, hence power changes by
        ``20*log10(gain/reference_gain)``.  Low-gain scope points are commonly
        noise-floor limited, so the estimate uses the upper gain octave and a
        median rather than fitting those points.
        """
        gains = np.asarray(gains, dtype=float)
        powers = np.asarray(measured_powers_dbm, dtype=float)
        valid = np.isfinite(gains) & np.isfinite(powers) & (gains > 0.0)
        if not np.any(valid):
            raise ValueError("calibration curve has no positive finite gain")
        gains = gains[valid]
        powers = powers[valid]
        high_gain = gains >= 0.125 * float(np.max(gains))
        if np.count_nonzero(high_gain) < min(3, gains.size):
            order = np.argsort(gains)
            high_gain = np.zeros(gains.size, dtype=bool)
            high_gain[order[-min(8, gains.size) :]] = True
        normalized = powers[high_gain] - 20.0 * np.log10(
            gains[high_gain] / float(self.reference_gain)
        )
        return float(np.median(normalized))

    def frequency_response_dbm(self, frequency_mhz: Any) -> np.ndarray:
        """Return full-scale-equivalent response used only for relative offsets."""
        frequencies = np.asarray(frequency_mhz, dtype=float)
        if not np.all(np.isfinite(frequencies)):
            raise ValueError("frequencies must be finite")
        minimum = float(self.frequencies_mhz[0])
        maximum = float(self.frequencies_mhz[-1])
        tolerance = 1.0e-5
        if np.any(frequencies < minimum - tolerance) or np.any(
            frequencies > maximum + tolerance
        ):
            offending = float(
                frequencies[
                    (frequencies < minimum - tolerance)
                    | (frequencies > maximum + tolerance)
                ].reshape(-1)[0]
            )
            raise ValueError(
                f"frequency {offending:.9g} MHz is outside calibration Run "
                f"{self.summary.run_id} coverage {minimum:.9g}..{maximum:.9g} MHz"
            )
        frequencies = np.clip(frequencies, minimum, maximum)
        return np.asarray(
            np.interp(
                frequencies,
                self.frequencies_mhz,
                self.frequency_response_levels_dbm,
            ),
            dtype=float,
        )

    def nominal_gain_for_power(
        self,
        output_power_dbm: float,
        *,
        reference_response_dbm: float,
        output_att1_db: float = 0.0,
        output_att2_db: float = 0.0,
    ) -> int:
        """Map one target power to one nominal gain using the linear model.

        This is a scalar conversion at the weakest frequency response.  The
        calibration's gain samples are not interpolated or inverted.
        """
        attenuation_delta = (
            float(output_att1_db)
            + float(output_att2_db)
            - self.summary.calibration_att1_db
            - self.summary.calibration_att2_db
        )
        full_scale_output_power = float(reference_response_dbm) - attenuation_delta
        minimum_output_power = full_scale_output_power + 20.0 * np.log10(
            1.0 / float(self.reference_gain)
        )
        target = float(output_power_dbm)
        if target < minimum_output_power or target > full_scale_output_power:
            raise ValueError(
                f"requested {target:.6g} dBm "
                f"is outside linear gain range {minimum_output_power:.6g}.."
                f"{full_scale_output_power:.6g} dBm (Run {self.summary.run_id})"
            )
        mapped = int(
            np.rint(
                self.reference_gain
                * 10.0 ** ((target - full_scale_output_power) / 20.0)
            )
        )
        return max(1, min(MAX_QICK_GAIN, mapped))

    def output_power_dbm(
        self,
        frequency_mhz: Any,
        gain_code: Any,
        *,
        output_att1_db: float = 0.0,
        output_att2_db: float = 0.0,
    ) -> np.ndarray:
        """Calculate actual output power from linear DAC gain and RF response."""
        frequencies = np.asarray(frequency_mhz, dtype=float)
        gains = np.asarray(gain_code, dtype=float)
        frequencies, gains = np.broadcast_arrays(frequencies, gains)
        if np.any(~np.isfinite(gains)) or np.any(gains <= 0.0):
            raise ValueError("gain codes must be positive and finite")
        if np.any(gains > MAX_QICK_GAIN):
            raise ValueError("gain code exceeds the QICK generator limit")
        attenuation_delta = (
            float(output_att1_db)
            + float(output_att2_db)
            - self.summary.calibration_att1_db
            - self.summary.calibration_att2_db
        )
        return np.asarray(
            self.frequency_response_dbm(frequencies)
            + 20.0 * np.log10(gains / float(self.reference_gain))
            - attenuation_delta,
            dtype=float,
        )

    def build_gain_schedule(
        self,
        frequencies_mhz: Any,
        output_power_dbm: float,
        *,
        output_att1_db: float = 0.0,
        output_att2_db: float = 0.0,
        max_entries: int = MAX_DMEM_GAIN_ENTRIES,
        dmem_base_address: int = GAIN_DMEM_BASE_ADDRESS,
    ) -> GainSchedule:
        frequencies = np.asarray(frequencies_mhz, dtype=float).reshape(-1)
        if frequencies.size < 1:
            raise ValueError("at least one sweep frequency is required")
        if not np.all(np.isfinite(frequencies)):
            raise ValueError("sweep frequencies must be finite")
        max_entries = int(max_entries)
        if not 1 <= max_entries <= MAX_DMEM_GAIN_ENTRIES:
            raise ValueError(f"max_entries must be in 1..{MAX_DMEM_GAIN_ENTRIES}")
        table_count = min(int(frequencies.size), max_entries)
        starts = (
            np.arange(table_count, dtype=np.int64) * frequencies.size
        ) // table_count
        ends = (
            (np.arange(1, table_count + 1, dtype=np.int64) * frequencies.size)
            // table_count
        ) - 1
        representative_indices = (starts + ends) // 2
        representative_frequencies = frequencies[representative_indices]
        all_responses = self.frequency_response_dbm(frequencies)
        reference_response = float(np.min(all_responses))
        nominal_gain = self.nominal_gain_for_power(
            output_power_dbm,
            reference_response_dbm=reference_response,
            output_att1_db=output_att1_db,
            output_att2_db=output_att2_db,
        )
        representative_responses = self.frequency_response_dbm(
            representative_frequencies
        )
        correction_db = reference_response - representative_responses
        gains = np.rint(nominal_gain * np.power(10.0, correction_db / 20.0)).astype(
            np.int32
        )
        gains = np.clip(gains, 1, MAX_QICK_GAIN)
        return GainSchedule(
            gain_codes=gains,
            representative_frequencies_mhz=representative_frequencies,
            representative_point_indices=representative_indices,
            frequency_point_count=int(frequencies.size),
            target_power_dbm=float(output_power_dbm),
            nominal_gain_code=int(nominal_gain),
            reference_response_dbm=reference_response,
            correction_db=correction_db,
            dmem_base_address=int(dmem_base_address),
        )


class InputPowerCalibration:
    """Frequency-dependent ADC magnitude to physical input-power mapping."""

    def __init__(
        self,
        summary: CalibrationRunSummary,
        frequencies_mhz: Any,
        slopes: Any,
        intercepts_dbm: Any,
    ):
        if summary.board_type not in INPUT_BOARD_TYPES:
            raise ValueError("input-power calibration requires an input board")
        frequencies = np.asarray(frequencies_mhz, dtype=float).reshape(-1)
        slopes = np.asarray(slopes, dtype=float).reshape(-1)
        intercepts = np.asarray(intercepts_dbm, dtype=float).reshape(-1)
        if not (
            frequencies.size >= 1 and frequencies.size == slopes.size == intercepts.size
        ):
            raise ValueError("input calibration arrays must have equal nonzero length")
        if not all(
            np.all(np.isfinite(values))
            for values in (
                frequencies,
                slopes,
                intercepts,
            )
        ):
            raise ValueError("input calibration values must be finite")
        order = np.argsort(frequencies)
        frequencies = frequencies[order]
        if np.any(np.diff(frequencies) <= 0.0):
            raise ValueError("input calibration frequencies must be unique")
        self.summary = summary
        self.frequencies_mhz = np.ascontiguousarray(frequencies)
        self.slopes = np.ascontiguousarray(slopes[order])
        self.intercepts_dbm = np.ascontiguousarray(intercepts[order])

    def coefficients(self, frequency_mhz: Any) -> Tuple[np.ndarray, np.ndarray]:
        frequencies = np.asarray(frequency_mhz, dtype=float)
        if not np.all(np.isfinite(frequencies)):
            raise ValueError("frequencies must be finite")
        minimum = float(self.frequencies_mhz[0])
        maximum = float(self.frequencies_mhz[-1])
        tolerance = 1.0e-5
        if np.any(frequencies < minimum - tolerance) or np.any(
            frequencies > maximum + tolerance
        ):
            raise ValueError(
                f"input calibration Run {self.summary.run_id} does not cover "
                f"the requested frequency range"
            )
        frequencies = np.clip(frequencies, minimum, maximum)
        return (
            np.asarray(
                np.interp(frequencies, self.frequencies_mhz, self.slopes),
                dtype=float,
            ),
            np.asarray(
                np.interp(
                    frequencies,
                    self.frequencies_mhz,
                    self.intercepts_dbm,
                ),
                dtype=float,
            ),
        )

    def input_power_dbm(
        self,
        frequency_mhz: Any,
        adc_magnitude_db: Any,
        *,
        input_attenuation_db: float = 0.0,
        input_gain_db: float = 0.0,
    ) -> np.ndarray:
        """Convert ``20*log10(hypot(I,Q))`` to power at the input connector."""
        frequencies, measured = np.broadcast_arrays(
            np.asarray(frequency_mhz, dtype=float),
            np.asarray(adc_magnitude_db, dtype=float),
        )
        if np.any(np.isinf(measured)):
            raise ValueError("ADC magnitudes must be finite or NaN")
        slopes, intercepts = self.coefficients(frequencies)
        front_end_correction = (
            float(input_attenuation_db)
            - self.summary.input_attenuation_db
            - (float(input_gain_db) - self.summary.input_gain_db)
        )
        adjusted_measured = measured + front_end_correction
        return np.asarray(
            np.where(
                np.isfinite(adjusted_measured),
                slopes * adjusted_measured + intercepts,
                np.nan,
            ),
            dtype=float,
        )


class CalibrationDatabase:
    """Read-only catalog for legacy and current QCoDeS calibration databases."""

    def __init__(self, database_path: Any):
        self.database_path = Path(database_path).expanduser().resolve()
        if not self.database_path.is_file():
            raise FileNotFoundError(
                f"calibration database does not exist: {self.database_path}"
            )

    def _connect(self) -> sqlite3.Connection:
        uri = self.database_path.as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _table_columns(
        connection: sqlite3.Connection, table_name: str
    ) -> Tuple[str, ...]:
        return tuple(
            str(row[1])
            for row in connection.execute(
                f"PRAGMA table_info({_quote_identifier(table_name)})"
            )
        )

    @staticmethod
    def _frequency_unit(connection: sqlite3.Connection, run_id: int) -> str:
        try:
            row = connection.execute(
                "SELECT unit FROM layouts WHERE run_id = ? AND parameter = 'freq' "
                "ORDER BY layout_id DESC LIMIT 1",
                (int(run_id),),
            ).fetchone()
        except sqlite3.OperationalError:
            return ""
        return "" if row is None else str(row[0] or "")

    def _candidate_rows(
        self, connection: sqlite3.Connection, board_type: str
    ) -> Iterable[sqlite3.Row]:
        target = _normalize_board_name(board_type)
        query = (
            "SELECT r.*, e.sample_name FROM runs r "
            "JOIN experiments e ON e.exp_id = r.exp_id ORDER BY r.run_id"
        )
        for row in connection.execute(query):
            sample = _normalize_board_name(row["sample_name"])
            if sample.startswith(target):
                yield row

    @staticmethod
    def _attenuation(row: sqlite3.Row) -> Tuple[float, float]:
        fields = set(row.keys())
        metadata = _json_mapping(
            row["Attenuation"] if "Attenuation" in fields else None
        )
        return float(metadata.get("att1", 0.0)), float(metadata.get("att2", 0.0))

    @staticmethod
    def _metadata(row: sqlite3.Row, *names: str) -> Mapping[str, Any]:
        fields = {str(key).lower(): str(key) for key in row.keys()}
        for name in names:
            key = fields.get(str(name).lower())
            if key is not None:
                metadata = _json_mapping(row[key])
                if metadata:
                    return metadata
        return {}

    def _output_path_settings(
        self,
        row: sqlite3.Row,
    ) -> Tuple[Optional[int], str, Optional[float], Optional[float]]:
        metadata = self._metadata(row, "Calibration_Config")
        configuration = metadata.get("configuration", metadata)
        if not isinstance(configuration, Mapping):
            configuration = {}
        actual = metadata.get("rf_settings_actual", {})
        if not isinstance(actual, Mapping):
            actual = {}

        def first(*values):
            return next((value for value in values if value is not None), None)

        raw_nqz = first(
            actual.get("nqz"),
            actual.get("nyquist_zone"),
            configuration.get("nqz"),
            configuration.get("output_nqz"),
        )
        try:
            nqz = None if raw_nqz is None else int(raw_nqz)
        except (TypeError, ValueError):
            nqz = None
        filter_type = str(
            first(
                actual.get("filter_type"),
                actual.get("output_filter_type"),
                configuration.get("output_filter_type"),
            )
            or ""
        )

        def optional_float(*values):
            raw = first(*values)
            try:
                value = float(raw)
            except (TypeError, ValueError):
                return None
            return value if np.isfinite(value) else None

        cutoff = optional_float(
            actual.get("filter_cutoff_ghz"),
            actual.get("output_filter_cutoff_ghz"),
            configuration.get("output_filter_cutoff_ghz"),
        )
        bandwidth = optional_float(
            actual.get("filter_bandwidth_ghz"),
            actual.get("output_filter_bandwidth_ghz"),
            configuration.get("output_filter_bandwidth_ghz"),
        )
        return nqz, filter_type, cutoff, bandwidth

    @staticmethod
    def _output_setting_mismatches(
        actual: Tuple[Optional[int], str, Optional[float], Optional[float]],
        *,
        nqz: Optional[int],
        output_filter_type: Optional[str],
        output_filter_cutoff_ghz: Optional[float],
        output_filter_bandwidth_ghz: Optional[float],
    ) -> Tuple[str, ...]:
        actual_nqz, actual_filter, actual_cutoff, actual_bandwidth = actual
        mismatches = []
        if nqz is not None and actual_nqz != int(nqz):
            actual_text = "unknown" if actual_nqz is None else str(actual_nqz)
            mismatches.append(f"Nyquist zone {actual_text} != {int(nqz)}")
        if (
            output_filter_type is not None
            and actual_filter != str(output_filter_type)
        ):
            mismatches.append(
                f"filter {actual_filter or 'unknown'} != {output_filter_type}"
            )
        for label, actual_value, requested_value in (
            (
                "filter cutoff",
                actual_cutoff,
                output_filter_cutoff_ghz,
            ),
            (
                "filter bandwidth",
                actual_bandwidth,
                output_filter_bandwidth_ghz,
            ),
        ):
            if requested_value is None:
                continue
            if actual_value is None or not np.isclose(
                actual_value,
                float(requested_value),
                rtol=0.0,
                atol=1.0e-9,
            ):
                actual_text = (
                    "unknown" if actual_value is None else f"{actual_value:.9g} GHz"
                )
                mismatches.append(
                    f"{label} {actual_text} != {float(requested_value):.9g} GHz"
                )
        return tuple(mismatches)

    def output_calibration_candidates(
        self,
        board_type: str,
        requested_frequencies_mhz: Any,
        *,
        nqz: Optional[int] = None,
        output_filter_type: Optional[str] = None,
        output_filter_cutoff_ghz: Optional[float] = None,
        output_filter_bandwidth_ghz: Optional[float] = None,
    ) -> Tuple[OutputCalibrationCandidate, ...]:
        """List output-power runs, with the closest compatible run first."""
        board_type = _validate_board_type(board_type, output=True)
        requested = np.asarray(requested_frequencies_mhz, dtype=float).reshape(-1)
        if requested.size < 1 or not np.all(np.isfinite(requested)):
            raise ValueError("requested frequencies must be a nonempty finite array")
        requested_min = float(np.min(requested))
        requested_max = float(np.max(requested))
        frequency_tolerance_mhz = 1.0e-5
        candidates = []
        with self._connect() as connection:
            for candidate_board in OUTPUT_BOARD_TYPES:
                for row in self._candidate_rows(connection, candidate_board):
                    table_name = str(row["result_table_name"])
                    columns = self._table_columns(connection, table_name)
                    if not {"gain", "freq", "pwr"}.issubset(columns):
                        continue
                    records = connection.execute(
                        f"SELECT gain, freq, pwr FROM "
                        f"{_quote_identifier(table_name)} "
                        "WHERE gain IS NOT NULL AND freq IS NOT NULL "
                        "AND pwr IS NOT NULL"
                    ).fetchall()
                    if not records:
                        continue
                    raw = np.asarray(
                        [tuple(record) for record in records],
                        dtype=float,
                    )
                    frequencies = _frequency_values_to_mhz(
                        raw[:, 1],
                        self._frequency_unit(connection, int(row["run_id"])),
                    )
                    frequency_min = float(np.min(frequencies))
                    frequency_max = float(np.max(frequencies))
                    overlap = max(
                        0.0,
                        min(requested_max, frequency_max)
                        - max(requested_min, frequency_min),
                    )
                    full_coverage = (
                        requested_min >= frequency_min - frequency_tolerance_mhz
                        and requested_max
                        <= frequency_max + frequency_tolerance_mhz
                    )
                    output_settings = self._output_path_settings(row)
                    mismatches = []
                    if candidate_board != board_type:
                        mismatches.append(
                            f"PCB {candidate_board} != {board_type}"
                        )
                    mismatches.extend(
                        self._output_setting_mismatches(
                            output_settings,
                            nqz=nqz,
                            output_filter_type=output_filter_type,
                            output_filter_cutoff_ghz=(
                                output_filter_cutoff_ghz
                            ),
                            output_filter_bandwidth_ghz=(
                                output_filter_bandwidth_ghz
                            ),
                        )
                    )
                    if not full_coverage:
                        mismatches.append(
                            f"frequency range {frequency_min:.6g}.."
                            f"{frequency_max:.6g} MHz does not cover "
                            f"{requested_min:.6g}..{requested_max:.6g} MHz"
                        )
                    att1, att2 = self._attenuation(row)
                    summary = CalibrationRunSummary(
                        database_path=self.database_path,
                        run_id=int(row["run_id"]),
                        experiment_id=int(row["exp_id"]),
                        board_type=candidate_board,
                        sample_name=str(row["sample_name"]),
                        result_table_name=table_name,
                        frequency_min_mhz=frequency_min,
                        frequency_max_mhz=frequency_max,
                        frequency_count=int(np.unique(frequencies).size),
                        row_count=int(raw.shape[0]),
                        calibration_att1_db=float(att1),
                        calibration_att2_db=float(att2),
                        purpose="output_power",
                        output_nqz=output_settings[0],
                        output_filter_type=output_settings[1],
                        output_filter_cutoff_ghz=output_settings[2],
                        output_filter_bandwidth_ghz=output_settings[3],
                    )
                    candidates.append(
                        OutputCalibrationCandidate(
                            summary=summary,
                            full_frequency_coverage=full_coverage,
                            frequency_overlap_mhz=overlap,
                            mismatches=tuple(mismatches),
                        )
                    )
        candidates.sort(
            key=lambda candidate: (
                candidate.exact_match,
                candidate.summary.board_type == board_type,
                candidate.full_frequency_coverage,
                -len(candidate.mismatches),
                candidate.frequency_overlap_mhz,
                candidate.summary.run_id,
            ),
            reverse=True,
        )
        return tuple(candidates)

    def output_calibration(
        self,
        board_type: str,
        requested_frequencies_mhz: Any,
        *,
        run_id: Optional[int] = None,
        nqz: Optional[int] = None,
        output_filter_type: Optional[str] = None,
        output_filter_cutoff_ghz: Optional[float] = None,
        output_filter_bandwidth_ghz: Optional[float] = None,
    ) -> GainPowerCalibration:
        board_type = _validate_board_type(board_type, output=True)
        if run_id is not None:
            if isinstance(run_id, (bool, np.bool_)) or not isinstance(
                run_id, (int, np.integer)
            ):
                raise TypeError("run_id must be an integer")
            run_id = int(run_id)
            if run_id < 1:
                raise ValueError("run_id must be positive")
        if nqz is not None and int(nqz) not in (1, 2):
            raise ValueError("nqz must be 1 or 2")
        if output_filter_type is not None and str(output_filter_type) not in {
            "bypass",
            "lowpass",
            "highpass",
            "bandpass",
        }:
            raise ValueError("unsupported output filter type")
        for value, name in (
            (output_filter_cutoff_ghz, "output filter cutoff"),
            (output_filter_bandwidth_ghz, "output filter bandwidth"),
        ):
            if value is not None and (
                not np.isfinite(float(value)) or float(value) <= 0.0
            ):
                raise ValueError(f"{name} must be positive and finite")
        requested = np.asarray(requested_frequencies_mhz, dtype=float).reshape(-1)
        if requested.size < 1 or not np.all(np.isfinite(requested)):
            raise ValueError("requested frequencies must be a nonempty finite array")
        requested_min = float(np.min(requested))
        requested_max = float(np.max(requested))
        candidates = []
        incompatible_settings = []
        with self._connect() as connection:
            for row in self._candidate_rows(connection, board_type):
                candidate_run_id = int(row["run_id"])
                if run_id is not None and candidate_run_id != run_id:
                    continue
                table_name = str(row["result_table_name"])
                columns = self._table_columns(connection, table_name)
                if not {"gain", "freq", "pwr"}.issubset(columns):
                    continue
                records = connection.execute(
                    f"SELECT gain, freq, pwr FROM {_quote_identifier(table_name)} "
                    "WHERE gain IS NOT NULL AND freq IS NOT NULL AND pwr IS NOT NULL"
                ).fetchall()
                if not records:
                    continue
                raw = np.asarray([tuple(record) for record in records], dtype=float)
                frequencies = _frequency_values_to_mhz(
                    raw[:, 1], self._frequency_unit(connection, int(row["run_id"]))
                )
                frequency_min = float(np.min(frequencies))
                frequency_max = float(np.max(frequencies))
                overlap = max(
                    0.0,
                    min(requested_max, frequency_max)
                    - max(requested_min, frequency_min),
                )
                # Hardware sweeps quantize both the initial DDS word and the
                # increment.  Across long sweeps the accumulated endpoint can
                # differ by a few hertz from the nominal calibration boundary.
                frequency_tolerance_mhz = 1.0e-5
                full_coverage = (
                    requested_min >= frequency_min - frequency_tolerance_mhz
                    and requested_max <= frequency_max + frequency_tolerance_mhz
                )
                att1, att2 = self._attenuation(row)
                output_settings = self._output_path_settings(row)
                setting_mismatches = self._output_setting_mismatches(
                    output_settings,
                    nqz=nqz,
                    output_filter_type=output_filter_type,
                    output_filter_cutoff_ghz=output_filter_cutoff_ghz,
                    output_filter_bandwidth_ghz=output_filter_bandwidth_ghz,
                )
                if setting_mismatches:
                    incompatible_settings.append(
                        (candidate_run_id, setting_mismatches)
                    )
                    continue
                candidates.append(
                    (
                        full_coverage,
                        overlap,
                        candidate_run_id,
                        row,
                        raw[:, 0],
                        frequencies,
                        raw[:, 2],
                        att1,
                        att2,
                        output_settings,
                    )
                )
        if not candidates:
            if incompatible_settings:
                details = "; ".join(
                    f"Run {candidate_run_id}: {', '.join(reasons)}"
                    for candidate_run_id, reasons in incompatible_settings
                )
                raise LookupError(
                    f"no compatible {board_type} output calibration for the "
                    f"selected Nyquist/filter settings; {details}"
                )
            run_text = "" if run_id is None else f" Run {run_id}"
            raise LookupError(
                f"no gain/frequency/power calibration{run_text} exists for "
                f"{board_type} in {self.database_path}"
            )
        candidates.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        selected = candidates[0]
        if not selected[0]:
            available = ", ".join(
                f"Run {item[2]}: {float(np.min(item[5])):.6g}.."
                f"{float(np.max(item[5])):.6g} MHz"
                for item in candidates
            )
            raise LookupError(
                f"no {board_type} calibration run fully covers requested "
                f"{requested_min:.6g}..{requested_max:.6g} MHz; available {available}"
            )
        (
            _,
            _,
            selected_run_id,
            row,
            gains,
            frequencies,
            powers,
            att1,
            att2,
            output_settings,
        ) = selected
        curves: Dict[float, Tuple[np.ndarray, np.ndarray]] = {}
        for frequency in np.unique(frequencies):
            mask = np.isclose(frequencies, frequency, rtol=0.0, atol=1.0e-9)
            group_gain = gains[mask]
            group_power = powers[mask]
            unique_gain = np.unique(group_gain)
            averaged_power = np.asarray(
                [
                    float(np.mean(group_power[group_gain == gain]))
                    for gain in unique_gain
                ]
            )
            order = np.argsort(unique_gain)
            curves[float(frequency)] = (
                unique_gain[order],
                averaged_power[order],
            )
        summary = CalibrationRunSummary(
            database_path=self.database_path,
            run_id=int(selected_run_id),
            experiment_id=int(row["exp_id"]),
            board_type=board_type,
            sample_name=str(row["sample_name"]),
            result_table_name=str(row["result_table_name"]),
            frequency_min_mhz=float(np.min(frequencies)),
            frequency_max_mhz=float(np.max(frequencies)),
            frequency_count=len(curves),
            row_count=int(len(gains)),
            calibration_att1_db=float(att1),
            calibration_att2_db=float(att2),
            purpose="output_power",
            output_nqz=output_settings[0],
            output_filter_type=output_settings[1],
            output_filter_cutoff_ghz=output_settings[2],
            output_filter_bandwidth_ghz=output_settings[3],
        )
        return GainPowerCalibration(summary, curves)

    def input_calibration(
        self,
        board_type: str,
        requested_frequencies_mhz: Any,
        *,
        run_id: Optional[int] = None,
        input_attenuation_db: Optional[float] = None,
        attenuation_tolerance_db: float = 1.0e-6,
    ) -> InputPowerCalibration:
        """Load one input calibration covering the requested frequency span.

        ``run_id`` selects an exact run and takes precedence over attenuation
        matching.  Otherwise, ``input_attenuation_db`` restricts automatic
        selection to runs acquired with the same input attenuation, and the
        newest matching run is returned.
        """
        board_type = _validate_board_type(board_type, output=False)
        selected_run_id = None
        if run_id is not None:
            if isinstance(run_id, (bool, np.bool_)) or not isinstance(
                run_id, (int, np.integer)
            ):
                raise TypeError("run_id must be an integer")
            selected_run_id = int(run_id)
            if selected_run_id < 1:
                raise ValueError("run_id must be >= 1")
        selected_attenuation = None
        if input_attenuation_db is not None:
            selected_attenuation = float(input_attenuation_db)
            if not np.isfinite(selected_attenuation):
                raise ValueError("input_attenuation_db must be finite")
        attenuation_tolerance_db = float(attenuation_tolerance_db)
        if not np.isfinite(attenuation_tolerance_db):
            raise ValueError("attenuation_tolerance_db must be finite")
        if attenuation_tolerance_db < 0.0:
            raise ValueError("attenuation_tolerance_db must be nonnegative")
        requested = np.asarray(requested_frequencies_mhz, dtype=float).reshape(-1)
        if requested.size < 1 or not np.all(np.isfinite(requested)):
            raise ValueError("requested frequencies must be a nonempty finite array")
        requested_min = float(np.min(requested))
        requested_max = float(np.max(requested))
        matches = []
        with self._connect() as connection:
            for row in self._candidate_rows(connection, board_type):
                table_name = str(row["result_table_name"])
                columns = self._table_columns(connection, table_name)
                if "freq" not in columns:
                    continue
                accepted = {
                    "measured_value",
                    "meas_in_pwr",
                    "meas_slope",
                    "meas_intercept",
                }
                if not accepted.intersection(columns):
                    continue
                select_columns = ["freq"]
                for column in (
                    "measured_value",
                    "meas_in_pwr",
                    "meas_slope",
                    "meas_intercept",
                ):
                    select_columns.append(
                        column if column in columns else f"NULL AS {column}"
                    )
                records = connection.execute(
                    f"SELECT {', '.join(select_columns)} FROM "
                    f"{_quote_identifier(table_name)} "
                    "WHERE freq IS NOT NULL"
                ).fetchall()
                if not records:
                    continue
                raw = np.asarray(
                    [
                        [
                            np.nan if value is None else float(value)
                            for value in tuple(record)
                        ]
                        for record in records
                    ],
                    dtype=float,
                )
                frequencies = _frequency_values_to_mhz(
                    raw[:, 0],
                    self._frequency_unit(connection, int(row["run_id"])),
                )
                minimum = float(np.min(frequencies))
                maximum = float(np.max(frequencies))
                if requested_min < minimum - 1.0e-5 or requested_max > maximum + 1.0e-5:
                    continue
                coefficient_frequencies = []
                slopes = []
                intercepts = []
                for frequency in np.unique(frequencies):
                    mask = np.isclose(frequencies, frequency, rtol=0.0, atol=1.0e-9)
                    measured = raw[mask, 1]
                    input_power = raw[mask, 2]
                    stored_slopes = raw[mask, 3]
                    stored_intercepts = raw[mask, 4]
                    finite_slope = stored_slopes[np.isfinite(stored_slopes)]
                    finite_intercept = stored_intercepts[np.isfinite(stored_intercepts)]
                    if finite_slope.size and finite_intercept.size:
                        slope = float(np.mean(finite_slope))
                        intercept = float(np.mean(finite_intercept))
                    else:
                        finite = np.isfinite(measured) & np.isfinite(input_power)
                        if np.count_nonzero(finite) < 2:
                            continue
                        x_values = measured[finite]
                        y_values = input_power[finite]
                        if np.unique(x_values).size < 2:
                            continue
                        slope, intercept = np.polyfit(x_values, y_values, 1)
                    coefficient_frequencies.append(float(frequency))
                    slopes.append(float(slope))
                    intercepts.append(float(intercept))
                if not coefficient_frequencies:
                    continue
                config_metadata = self._metadata(
                    row,
                    "Calibration_Config",
                    "calibration_config",
                )
                result_metadata = self._metadata(
                    row,
                    "Calibration_Result",
                    "calibration_result",
                )
                att1, att2 = self._attenuation(row)
                if att1 == 0.0 and att2 == 0.0 and result_metadata:
                    att1 = float(result_metadata.get("att1", 0.0))
                    att2 = float(result_metadata.get("att2", 0.0))
                input_attenuation = float(
                    config_metadata.get(
                        "input_attenuation_db",
                        config_metadata.get("readout_attenuation_db", 0.0),
                    )
                )
                input_gain = float(
                    config_metadata.get(
                        "input_dc_gain_db",
                        config_metadata.get("readout_dc_gain_db", 0.0),
                    )
                )
                source_output_run_id = int(
                    config_metadata.get(
                        "output_run_id",
                        result_metadata.get("pwr_id", 0),
                    )
                )
                path_loss_db = float(config_metadata.get("path_loss_db", 0.0))
                summary = CalibrationRunSummary(
                    database_path=self.database_path,
                    run_id=int(row["run_id"]),
                    experiment_id=int(row["exp_id"]),
                    board_type=board_type,
                    sample_name=str(row["sample_name"]),
                    result_table_name=table_name,
                    frequency_min_mhz=minimum,
                    frequency_max_mhz=maximum,
                    frequency_count=int(np.unique(frequencies).size),
                    row_count=int(frequencies.size),
                    calibration_att1_db=att1,
                    calibration_att2_db=att2,
                    input_attenuation_db=input_attenuation,
                    input_gain_db=input_gain,
                    source_output_run_id=source_output_run_id,
                    path_loss_db=path_loss_db,
                    purpose="input_power",
                )
                matches.append(
                    (
                        int(row["run_id"]),
                        InputPowerCalibration(
                            summary,
                            coefficient_frequencies,
                            slopes,
                            intercepts,
                        ),
                    )
                )
        if not matches:
            run_description = (
                ""
                if selected_run_id is None
                else f" for requested Run {selected_run_id}"
            )
            raise LookupError(
                f"no {board_type} ADC-to-input-power calibration fully covers "
                f"{requested_min:.6g}..{requested_max:.6g} MHz{run_description}"
            )
        if selected_run_id is not None:
            for candidate_run_id, calibration in matches:
                if candidate_run_id == selected_run_id:
                    return calibration
            raise LookupError(
                f"input calibration Run {selected_run_id} is not a {board_type} "
                "run covering "
                f"{requested_min:.6g}..{requested_max:.6g} MHz"
            )
        if selected_attenuation is not None:
            attenuation_matches = [
                (candidate_run_id, calibration)
                for candidate_run_id, calibration in matches
                if abs(
                    calibration.summary.input_attenuation_db
                    - selected_attenuation
                )
                <= attenuation_tolerance_db
            ]
            if not attenuation_matches:
                available = ", ".join(
                    f"Run {candidate_run_id}: "
                    f"{calibration.summary.input_attenuation_db:.6g} dB"
                    for candidate_run_id, calibration in matches
                )
                raise LookupError(
                    f"no {board_type} input calibration acquired at "
                    f"{selected_attenuation:.6g} dB covers "
                    f"{requested_min:.6g}..{requested_max:.6g} MHz; "
                    f"available covering runs: {available}"
                )
            return max(attenuation_matches, key=lambda item: item[0])[1]
        return max(matches, key=lambda item: item[0])[1]

    def matching_input_run(
        self,
        board_type: str,
        requested_frequencies_mhz: Any,
        *,
        run_id: Optional[int] = None,
        input_attenuation_db: Optional[float] = None,
    ) -> Optional[CalibrationRunSummary]:
        """Return input calibration metadata, retaining the legacy API."""
        try:
            return self.input_calibration(
                board_type,
                requested_frequencies_mhz,
                run_id=run_id,
                input_attenuation_db=input_attenuation_db,
            ).summary
        except LookupError:
            return None


__all__ = [
    "BOARD_TYPES",
    "CalibrationDatabase",
    "CalibrationRunSummary",
    "GAIN_DMEM_BASE_ADDRESS",
    "GainPowerCalibration",
    "GainSchedule",
    "InputPowerCalibration",
    "INPUT_BOARD_TYPES",
    "MAX_DMEM_GAIN_ENTRIES",
    "MAX_QICK_GAIN",
    "OutputCalibrationCandidate",
    "OUTPUT_BOARD_TYPES",
]
