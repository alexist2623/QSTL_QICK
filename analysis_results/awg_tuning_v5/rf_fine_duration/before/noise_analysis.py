"""Current-noise analysis for QICK I traces.

The panel mirrors the common laboratory workflow::

    current = input_trace * input_scale / transimpedance_gain
    ASD = sqrt(periodogram(current, scaling="density"))

It can acquire an independent FIR-DDR trace directly from QICK or load a
previously saved QCoDeS run.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
import sqlite3
import traceback
from typing import Any, Mapping, Optional

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
    from .qick_qcodes_experiment import load_qick_iq_arrays
    from .dc_voltage_calibration import load_dc_voltage_calibration
    from .noise_acquisition import (
        NoiseAcquisitionConfig,
        acquire_noise_fir_trace,
    )
    from .qick_front_panel import QickFrontPanelPreview
except ImportError:
    from qick_qcodes_experiment import load_qick_iq_arrays
    from dc_voltage_calibration import load_dc_voltage_calibration
    from noise_acquisition import (
        NoiseAcquisitionConfig,
        acquire_noise_fir_trace,
    )
    from qick_front_panel import QickFrontPanelPreview


INPUT_MODES = ("voltage", "adc", "current")
WINDOWS = ("flattop", "hann", "blackmanharris", "boxcar")
DETREND_MODES = ("constant", "linear", "none")
DEFAULT_NOISE_ANALYSIS_SETTINGS = {
    "acquisition_host": "192.168.2.99",
    "acquisition_ns_port": 8888,
    "acquisition_proxy_name": "myqick",
    "acquisition_readout_ch": 0,
    "acquisition_input_board_type": "RF_In",
    "acquisition_nqz": 1,
    "acquisition_fir_samples": 1_000_000,
    "acquisition_readout_frequency_mhz": 0.0,
    "acquisition_input_attenuation_db": 20.0,
    "acquisition_dc_gain_db": 0.0,
    "acquisition_filter_type": "bypass",
    "acquisition_filter_cutoff_ghz": 2.5,
    "acquisition_filter_bandwidth_ghz": 1.0,
    "acquisition_margin_input_samples": 1024,
    "acquisition_fpga_trigger_delay_us": None,
    "acquisition_force_overwrite": True,
    "acquisition_post_run_read_delay_seconds": 0.1,
    "database_path": str(Path.home() / "qick_experiments.db"),
    "run_id": 0,
    "point_index": 0,
    "repetition_index": 0,
    "input_mode": "voltage",
    "transimpedance_gain_v_per_a": 1.0e8,
    "input_scale_v_per_unit": 1.0,
    "sample_rate_hz": 1.0e6,
    "window": "flattop",
    "detrend": "constant",
    "nfft": 0,
    "dc_voltage_calibration_enabled": False,
    "dc_voltage_calibration_database_path": "",
    "dc_voltage_calibration_run_id": 0,
    "dc_voltage_calibration_readout_ch": 0,
    "dc_voltage_calibration_input_gain_db": 0.0,
}


def _finite_positive(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be positive and finite")
    return result


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _nonnegative_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    result = int(value)
    if result < 0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def normalize_noise_analysis_settings(
    values: Optional[Mapping[str, Any]],
) -> dict:
    """Fill defaults and validate JSON-compatible noise settings."""
    if values is None:
        values = {}
    if not isinstance(values, Mapping):
        raise TypeError("noise_analysis must be a JSON object")
    settings = {**DEFAULT_NOISE_ANALYSIS_SETTINGS, **dict(values)}
    settings["database_path"] = str(settings["database_path"]).strip()
    if not settings["database_path"]:
        raise ValueError("noise-analysis database path must not be empty")
    for name in (
        "acquisition_readout_ch",
        "acquisition_fir_samples",
        "acquisition_margin_input_samples",
        "run_id",
        "point_index",
        "repetition_index",
        "nfft",
        "dc_voltage_calibration_run_id",
        "dc_voltage_calibration_readout_ch",
    ):
        settings[name] = _nonnegative_integer(settings[name], name)
    settings["acquisition_ns_port"] = _nonnegative_integer(
        settings["acquisition_ns_port"],
        "acquisition_ns_port",
    )
    if not 1 <= settings["acquisition_ns_port"] <= 65535:
        raise ValueError("acquisition_ns_port must be in [1, 65535]")
    if settings["acquisition_fir_samples"] < 2:
        raise ValueError("acquisition_fir_samples must be at least 2")
    if settings["acquisition_fir_samples"] > 100_000_000:
        raise ValueError("acquisition_fir_samples must not exceed 100000000")
    settings["acquisition_host"] = str(settings["acquisition_host"]).strip()
    settings["acquisition_proxy_name"] = str(
        settings["acquisition_proxy_name"]
    ).strip()
    if not settings["acquisition_host"]:
        raise ValueError("acquisition_host must not be empty")
    if not settings["acquisition_proxy_name"]:
        raise ValueError("acquisition_proxy_name must not be empty")
    settings["acquisition_input_board_type"] = str(
        settings["acquisition_input_board_type"]
    )
    if settings["acquisition_input_board_type"] not in {"RF_In", "DC_In"}:
        raise ValueError("acquisition_input_board_type must be RF_In or DC_In")
    settings["acquisition_nqz"] = _nonnegative_integer(
        settings["acquisition_nqz"],
        "acquisition_nqz",
    )
    if settings["acquisition_nqz"] not in {1, 2}:
        raise ValueError("acquisition_nqz must be 1 or 2")
    for name in (
        "acquisition_readout_frequency_mhz",
        "acquisition_input_attenuation_db",
        "acquisition_dc_gain_db",
        "acquisition_filter_cutoff_ghz",
        "acquisition_filter_bandwidth_ghz",
        "acquisition_post_run_read_delay_seconds",
    ):
        settings[name] = _finite(settings[name], name)
    raw_fpga_delay = settings["acquisition_fpga_trigger_delay_us"]
    settings["acquisition_fpga_trigger_delay_us"] = (
        None
        if raw_fpga_delay is None
        else _finite(raw_fpga_delay, "acquisition_fpga_trigger_delay_us")
    )
    if (
        settings["acquisition_fpga_trigger_delay_us"] is not None
        and settings["acquisition_fpga_trigger_delay_us"] < 0.0
    ):
        raise ValueError(
            "acquisition_fpga_trigger_delay_us must be nonnegative"
        )
    if not 0.0 <= settings["acquisition_input_attenuation_db"] <= 31.75:
        raise ValueError("acquisition_input_attenuation_db must be in [0, 31.75]")
    if not -6.0 <= settings["acquisition_dc_gain_db"] <= 26.0:
        raise ValueError("acquisition_dc_gain_db must be in [-6, 26]")
    if settings["acquisition_filter_cutoff_ghz"] < 0.0:
        raise ValueError("acquisition_filter_cutoff_ghz must be nonnegative")
    if settings["acquisition_filter_bandwidth_ghz"] <= 0.0:
        raise ValueError("acquisition_filter_bandwidth_ghz must be positive")
    if settings["acquisition_post_run_read_delay_seconds"] < 0.0:
        raise ValueError(
            "acquisition_post_run_read_delay_seconds must be nonnegative"
        )
    settings["acquisition_filter_type"] = str(
        settings["acquisition_filter_type"]
    ).lower()
    if settings["acquisition_filter_type"] not in {
        "bypass", "lowpass", "highpass", "bandpass"
    }:
        raise ValueError("unsupported acquisition_filter_type")
    force_overwrite = settings["acquisition_force_overwrite"]
    if not isinstance(force_overwrite, (bool, np.bool_)):
        raise TypeError("acquisition_force_overwrite must be boolean")
    settings["acquisition_force_overwrite"] = bool(force_overwrite)
    settings["transimpedance_gain_v_per_a"] = _finite_positive(
        settings["transimpedance_gain_v_per_a"],
        "transimpedance_gain_v_per_a",
    )
    settings["input_scale_v_per_unit"] = _finite_positive(
        settings["input_scale_v_per_unit"],
        "input_scale_v_per_unit",
    )
    settings["sample_rate_hz"] = _finite_positive(
        settings["sample_rate_hz"],
        "sample_rate_hz",
    )
    calibration_enabled = settings["dc_voltage_calibration_enabled"]
    if not isinstance(calibration_enabled, (bool, np.bool_)):
        raise TypeError("dc_voltage_calibration_enabled must be boolean")
    settings["dc_voltage_calibration_enabled"] = bool(calibration_enabled)
    settings["dc_voltage_calibration_database_path"] = str(
        settings["dc_voltage_calibration_database_path"]
    ).strip()
    if (
        settings["dc_voltage_calibration_enabled"]
        and not settings["dc_voltage_calibration_database_path"]
    ):
        raise ValueError(
            "DC voltage calibration database path must not be empty"
        )
    settings["dc_voltage_calibration_input_gain_db"] = _finite(
        settings["dc_voltage_calibration_input_gain_db"],
        "dc_voltage_calibration_input_gain_db",
    )
    settings["input_mode"] = str(settings["input_mode"]).lower()
    settings["window"] = str(settings["window"]).lower()
    settings["detrend"] = str(settings["detrend"]).lower()
    if settings["input_mode"] not in INPUT_MODES:
        raise ValueError(f"input_mode must be one of {INPUT_MODES}")
    if settings["window"] not in WINDOWS:
        raise ValueError(f"window must be one of {WINDOWS}")
    if settings["detrend"] not in DETREND_MODES:
        raise ValueError(f"detrend must be one of {DETREND_MODES}")
    return settings


@dataclass(frozen=True)
class NoiseAnalysisConfig:
    """Numerical conversion and periodogram settings."""

    input_mode: str = "voltage"
    transimpedance_gain_v_per_a: float = 1.0e8
    input_scale_v_per_unit: float = 1.0
    sample_rate_hz: float = 1.0e6
    window: str = "flattop"
    detrend: str = "constant"
    nfft: int = 0

    def __post_init__(self) -> None:
        normalize_noise_analysis_settings({
            **DEFAULT_NOISE_ANALYSIS_SETTINGS,
            "input_mode": self.input_mode,
            "transimpedance_gain_v_per_a": self.transimpedance_gain_v_per_a,
            "input_scale_v_per_unit": self.input_scale_v_per_unit,
            "sample_rate_hz": self.sample_rate_hz,
            "window": self.window,
            "detrend": self.detrend,
            "nfft": self.nfft,
        })


@dataclass(frozen=True)
class NoiseAnalysisResult:
    """Time-domain current and one-sided amplitude spectral density."""

    input_trace: np.ndarray
    time_s: np.ndarray
    current_a: np.ndarray
    frequency_hz: np.ndarray
    asd_a_per_sqrt_hz: np.ndarray
    config: NoiseAnalysisConfig
    source: str = ""
    input_unit: str = ""

    @property
    def mean_current_a(self) -> float:
        return float(np.mean(self.current_a))

    @property
    def rms_current_a(self) -> float:
        return float(np.sqrt(np.mean(np.square(self.current_a))))

    @property
    def std_current_a(self) -> float:
        return float(np.std(self.current_a))


@dataclass(frozen=True)
class NoiseTraceCollection:
    """A selectable set of point/repetition I traces."""

    i_traces: np.ndarray
    sample_rate_hz: float
    unit: str = "ADC units"
    source: str = ""
    database_path: str = ""
    run_id: int = 0
    raw_iq: np.ndarray | None = None
    iq_scale_log2: int = 0

    def __post_init__(self) -> None:
        traces = np.asarray(self.i_traces)
        if traces.ndim != 3:
            raise ValueError("I traces must have shape (point, repetition, sample)")
        if traces.size < 2 or traces.shape[-1] < 2:
            raise ValueError("noise analysis requires at least two I samples")
        if not np.all(np.isfinite(traces)):
            raise ValueError("I traces must contain only finite values")
        _finite_positive(self.sample_rate_hz, "sample_rate_hz")

    @property
    def point_count(self) -> int:
        return int(np.asarray(self.i_traces).shape[0])

    @property
    def repetition_count(self) -> int:
        return int(np.asarray(self.i_traces).shape[1])

    @property
    def sample_count(self) -> int:
        return int(np.asarray(self.i_traces).shape[2])

    def trace(self, point_index: int, repetition_index: int) -> np.ndarray:
        return np.asarray(
            self.i_traces[int(point_index), int(repetition_index)],
            dtype=np.float64,
        )


def analyze_i_trace(
    i_trace: Any,
    config: NoiseAnalysisConfig,
    *,
    source: str = "",
    input_unit: str = "",
) -> NoiseAnalysisResult:
    """Convert one I trace to current and calculate its one-sided ASD."""
    values = np.asarray(i_trace, dtype=np.float64).reshape(-1)
    if values.size < 2:
        raise ValueError("noise analysis requires at least two I samples")
    if not np.all(np.isfinite(values)):
        raise ValueError("I trace must contain only finite values")

    mode = str(config.input_mode).lower()
    if mode == "current":
        current = values.copy()
    elif mode == "voltage":
        current = values / float(config.transimpedance_gain_v_per_a)
    elif mode == "adc":
        current = (
            values
            * float(config.input_scale_v_per_unit)
            / float(config.transimpedance_gain_v_per_a)
        )
    else:
        raise ValueError(f"unsupported input mode {config.input_mode!r}")

    try:
        from scipy import signal
    except ImportError as exc:
        raise RuntimeError(
            "SciPy is required for noise analysis; install scipy==1.17.1"
        ) from exc

    nfft = values.size if int(config.nfft) == 0 else max(
        values.size, int(config.nfft)
    )
    detrend = False if config.detrend == "none" else config.detrend
    frequency, density = signal.periodogram(
        current,
        fs=float(config.sample_rate_hz),
        window=str(config.window),
        detrend=detrend,
        nfft=nfft,
        scaling="density",
        return_onesided=True,
    )
    density = np.maximum(np.asarray(density, dtype=np.float64), 0.0)
    return NoiseAnalysisResult(
        input_trace=values,
        time_s=np.arange(values.size, dtype=np.float64)
        / float(config.sample_rate_hz),
        current_a=current,
        frequency_hz=np.asarray(frequency, dtype=np.float64),
        asd_a_per_sqrt_hz=np.sqrt(density),
        config=config,
        source=str(source),
        input_unit=str(input_unit),
    )


def _latest_run_id(database_path: Path) -> int:
    """Return the latest run containing QICK split/legacy IQ metadata."""
    connection = sqlite3.connect(str(database_path), timeout=30.0)
    try:
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(runs)")
        }
        row = (
            connection.execute(
                "SELECT run_id FROM runs "
                "WHERE qick_experiment_json IS NOT NULL "
                "AND qick_experiment_json != '' "
                "ORDER BY run_id DESC LIMIT 1"
            ).fetchone()
            if "qick_experiment_json" in columns
            else None
        )
    finally:
        connection.close()
    if row is None:
        raise ValueError(
            "QCoDeS database contains no compatible QICK I-trace runs: "
            f"{database_path}"
        )
    return int(row[0])


def load_noise_trace_collection(
    database_path: Any,
    run_id: int = 0,
) -> NoiseTraceCollection:
    """Load I traces and sample timing from a saved QCoDeS experiment."""
    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"QCoDeS database does not exist: {path}")
    selected_run = _nonnegative_integer(run_id, "run_id")
    if selected_run == 0:
        selected_run = _latest_run_id(path)
    try:
        from qcodes import initialise_or_create_database_at, load_by_id
    except ImportError as exc:
        raise RuntimeError(
            "QCoDeS==0.58.0 is required to load saved noise traces"
        ) from exc
    initialise_or_create_database_at(str(path))
    dataset = load_by_id(selected_run)
    arrays = load_qick_iq_arrays(dataset)
    metadata = arrays.get("metadata", {})
    layout = metadata.get("measurement_layout", {})
    sample_rate_hz = float(
        layout.get(
            "sample_rate_hz",
            1.0e6 / float(layout.get("sample_period_us", 1.0)),
        )
    )
    return NoiseTraceCollection(
        i_traces=np.asarray(arrays["i"], dtype=np.float64),
        sample_rate_hz=sample_rate_hz,
        unit=str(arrays.get("iq_unit", "ADC units")),
        source=f"QCoDeS Run {selected_run}",
        database_path=str(path),
        run_id=selected_run,
    )


class NoiseTraceLoadWorker(QtCore.QObject):
    """Load a QCoDeS run without blocking the GUI thread."""

    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, database_path: str, run_id: int, parent=None):
        super().__init__(parent)
        self._database_path = str(database_path)
        self._run_id = int(run_id)

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            collection = load_noise_trace_collection(
                self._database_path,
                self._run_id,
            )
        except Exception:
            self.failed.emit(traceback.format_exc())
            return
        self.finished.emit(collection)


class NoiseAcquisitionWorker(QtCore.QObject):
    """Run the tab-local QICK FIR-DDR acquisition off the GUI thread."""

    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    progress_changed = QtCore.pyqtSignal(int, str)

    def __init__(self, config: NoiseAcquisitionConfig, parent=None):
        super().__init__(parent)
        self._config = config

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            result = acquire_noise_fir_trace(
                self._config,
                progress_callback=self.progress_changed.emit,
            )
            collection = NoiseTraceCollection(
                i_traces=result_iq_in_input_units(result)[:, 0].astype(np.float64, copy=False).reshape(
                    1, 1, -1
                ),
                sample_rate_hz=result.sample_rate_hz,
                unit="ADC units",
                source=result.source,
                raw_iq=result.iq,
                iq_scale_log2=int(getattr(result, "iq_scale_log2", 0)),
            )
        except Exception:
            self.failed.emit(traceback.format_exc())
            return
        self.finished.emit(collection)


if pg is not None:

    class NoiseAnalysisPlotWidget(QtWidgets.QWidget):
        """Time-current and log-log current-ASD plots."""

        MAX_DISPLAY_POINTS = 120_000

        def __init__(self, parent=None):
            super().__init__(parent)
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self)
            self.time_plot = pg.PlotWidget(splitter)
            self.spectrum_plot = pg.PlotWidget(splitter)
            splitter.addWidget(self.time_plot)
            splitter.addWidget(self.spectrum_plot)
            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 1)
            layout.addWidget(splitter)
            self.time_plot.setLabel("bottom", "Time", units="s")
            self.time_plot.setLabel("left", "Current", units="A")
            self.spectrum_plot.setLabel("bottom", "Frequency", units="Hz")
            self.spectrum_plot.setLabel(
                "left", "Current ASD", units="A/sqrt(Hz)"
            )
            self.spectrum_plot.setLogMode(x=True, y=True)
            for plot in (self.time_plot, self.spectrum_plot):
                plot.showGrid(x=True, y=True, alpha=0.25)
            self._time_curve = self.time_plot.plot(
                pen=pg.mkPen("#2878b5", width=1.4)
            )
            self._spectrum_curve = self.spectrum_plot.plot(
                pen=pg.mkPen("#c43c39", width=1.4)
            )

        @classmethod
        def _linear_display_slice(cls, count: int) -> slice:
            step = max(1, int(np.ceil(count / cls.MAX_DISPLAY_POINTS)))
            return slice(None, None, step)

        @classmethod
        def _log_display_indices(cls, count: int) -> np.ndarray:
            if count <= cls.MAX_DISPLAY_POINTS:
                return np.arange(count, dtype=np.int64)
            return np.unique(
                np.geomspace(1, count, cls.MAX_DISPLAY_POINTS).astype(np.int64) - 1
            )

        def set_result(self, result: NoiseAnalysisResult) -> None:
            time_slice = self._linear_display_slice(result.time_s.size)
            self._time_curve.setData(
                result.time_s[time_slice], result.current_a[time_slice]
            )
            valid = (
                (result.frequency_hz > 0.0)
                & np.isfinite(result.asd_a_per_sqrt_hz)
                & (result.asd_a_per_sqrt_hz > 0.0)
            )
            frequency = result.frequency_hz[valid]
            asd = result.asd_a_per_sqrt_hz[valid]
            indices = self._log_display_indices(frequency.size)
            self._spectrum_curve.setData(frequency[indices], asd[indices])
            suffix = f" - {result.source}" if result.source else ""
            self.time_plot.setTitle(f"Input current vs time{suffix}")
            self.spectrum_plot.setTitle(
                f"Current noise amplitude spectral density{suffix}"
            )
            self.fit_view()

        def clear(self) -> None:
            self._time_curve.setData([], [])
            self._spectrum_curve.setData([], [])

        def fit_view(self) -> None:
            self.time_plot.enableAutoRange(x=True, y=True)
            self.spectrum_plot.enableAutoRange(x=True, y=True)

else:

    class NoiseAnalysisPlotWidget(QtWidgets.QLabel):
        """Dependency error used when PyQtGraph is unavailable."""

        def __init__(self, parent=None):
            super().__init__("pyqtgraph is required for noise-analysis plots", parent)
            self.setAlignment(QtCore.Qt.AlignCenter)

        def set_result(self, _result: NoiseAnalysisResult) -> None:
            return

        def clear(self) -> None:
            return

        def fit_view(self) -> None:
            return


class NoiseAnalysisPanel(QtWidgets.QWidget):
    """Independent FIR acquisition and current-noise analysis controls."""

    load_requested = QtCore.pyqtSignal(str, int)
    acquire_requested = QtCore.pyqtSignal(object)
    front_panel_requested = QtCore.pyqtSignal(object)

    def __init__(self, parent=None, *, default_database_path: str = ""):
        super().__init__(parent)
        self._collection: Optional[NoiseTraceCollection] = None
        self._result: Optional[NoiseAnalysisResult] = None
        self._dc_calibration_cache_key = None
        self._dc_calibration_cache = None
        page_layout = QtWidgets.QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        control_scroll = QtWidgets.QScrollArea(self)
        control_scroll.setWidgetResizable(True)
        control_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._control_scroll = control_scroll
        control_content = QtWidgets.QWidget(control_scroll)
        outer = QtWidgets.QVBoxLayout(control_content)
        control_scroll.setWidget(control_content)
        page_layout.addWidget(control_scroll, 1)

        acquisition_group = QtWidgets.QGroupBox(
            "Direct FIR-DDR Acquisition",
            self,
        )
        acquisition_form = QtWidgets.QFormLayout(acquisition_group)
        self.acquisition_status = QtWidgets.QLabel(
            "Independent capture is ready",
            acquisition_group,
        )
        self.acquisition_status.setWordWrap(True)
        self.acquisition_host = QtWidgets.QLineEdit(
            DEFAULT_NOISE_ANALYSIS_SETTINGS["acquisition_host"],
            acquisition_group,
        )
        self.acquisition_port = QtWidgets.QSpinBox(acquisition_group)
        self.acquisition_port.setRange(1, 65535)
        self.acquisition_port.setValue(
            DEFAULT_NOISE_ANALYSIS_SETTINGS["acquisition_ns_port"]
        )
        self.acquisition_proxy = QtWidgets.QLineEdit(
            DEFAULT_NOISE_ANALYSIS_SETTINGS["acquisition_proxy_name"],
            acquisition_group,
        )
        # QICK connection values are edited in the shared Setup dialog. Keep
        # these widgets as synchronized storage for acquisition_config(), but
        # do not leave unlayouted child widgets floating over this group box.
        for connection_widget in (
            self.acquisition_host,
            self.acquisition_port,
            self.acquisition_proxy,
        ):
            connection_widget.hide()
        self.front_panel_preview = QickFrontPanelPreview(acquisition_group)
        self.readout_channel = QtWidgets.QSpinBox(acquisition_group)
        self.readout_channel.setRange(0, 255)
        self.input_board = QtWidgets.QComboBox(acquisition_group)
        self.input_board.addItems(("RF_In", "DC_In"))
        self.input_nqz = QtWidgets.QSpinBox(acquisition_group)
        self.input_nqz.setRange(1, 2)
        input_row = QtWidgets.QHBoxLayout()
        input_row.addWidget(QtWidgets.QLabel("Readout:"))
        input_row.addWidget(self.readout_channel)
        input_row.addWidget(QtWidgets.QLabel("Board:"))
        input_row.addWidget(self.input_board, 1)
        input_row.addWidget(QtWidgets.QLabel("ADC Nyquist:"))
        input_row.addWidget(self.input_nqz)

        self.fir_samples = QtWidgets.QSpinBox(acquisition_group)
        self.fir_samples.setRange(2, 100_000_000)
        self.fir_samples.setValue(
            DEFAULT_NOISE_ANALYSIS_SETTINGS["acquisition_fir_samples"]
        )
        self.fir_samples.setGroupSeparatorShown(True)
        self.capture_duration = QtWidgets.QLabel(acquisition_group)
        samples_row = QtWidgets.QHBoxLayout()
        samples_row.addWidget(self.fir_samples)
        samples_row.addWidget(self.capture_duration, 1)
        self.readout_frequency = QtWidgets.QDoubleSpinBox(acquisition_group)
        self.readout_frequency.setRange(-100_000.0, 100_000.0)
        self.readout_frequency.setDecimals(9)
        self.readout_frequency.setSuffix(" MHz")

        self.input_attenuation = QtWidgets.QDoubleSpinBox(acquisition_group)
        self.input_attenuation.setRange(0.0, 31.75)
        self.input_attenuation.setSingleStep(0.25)
        self.input_attenuation.setDecimals(2)
        self.input_attenuation.setValue(20.0)
        self.input_attenuation.setSuffix(" dB")
        self.input_dc_gain = QtWidgets.QDoubleSpinBox(acquisition_group)
        self.input_dc_gain.setRange(-6.0, 26.0)
        self.input_dc_gain.setDecimals(2)
        self.input_dc_gain.setSuffix(" dB")
        board_setting_row = QtWidgets.QHBoxLayout()
        board_setting_row.addWidget(QtWidgets.QLabel("RF ATT:"))
        board_setting_row.addWidget(self.input_attenuation)
        board_setting_row.addWidget(QtWidgets.QLabel("DC gain:"))
        board_setting_row.addWidget(self.input_dc_gain)

        self.input_filter = QtWidgets.QComboBox(acquisition_group)
        self.input_filter.addItems(("bypass", "lowpass", "highpass", "bandpass"))
        self.filter_cutoff = QtWidgets.QDoubleSpinBox(acquisition_group)
        self.filter_cutoff.setRange(0.0, 20.0)
        self.filter_cutoff.setDecimals(6)
        self.filter_cutoff.setValue(2.5)
        self.filter_cutoff.setSuffix(" GHz")
        self.filter_bandwidth = QtWidgets.QDoubleSpinBox(acquisition_group)
        self.filter_bandwidth.setRange(0.001, 20.0)
        self.filter_bandwidth.setDecimals(6)
        self.filter_bandwidth.setValue(1.0)
        self.filter_bandwidth.setSuffix(" GHz")
        filter_row = QtWidgets.QHBoxLayout()
        filter_row.addWidget(self.input_filter, 1)
        filter_row.addWidget(QtWidgets.QLabel("Cutoff/center:"))
        filter_row.addWidget(self.filter_cutoff)
        filter_row.addWidget(QtWidgets.QLabel("Bandwidth:"))
        filter_row.addWidget(self.filter_bandwidth)

        self.input_margin = QtWidgets.QSpinBox(acquisition_group)
        self.input_margin.setRange(0, 1 << 30)
        self.input_margin.setValue(1024)
        self.input_margin.setGroupSeparatorShown(True)
        self._fir_trigger_delay_us = 0.0
        self._fir_uses_fpga_trigger_delay: Optional[bool] = None
        self.override_fpga_trigger_delay = QtWidgets.QCheckBox(
            "Override HWH default",
            acquisition_group,
        )
        self.fpga_trigger_delay_us = QtWidgets.QDoubleSpinBox(
            acquisition_group
        )
        self.fpga_trigger_delay_us.setRange(0.0, 10_000_000.0)
        self.fpga_trigger_delay_us.setDecimals(6)
        self.fpga_trigger_delay_us.setSuffix(" us")
        self.fpga_trigger_delay_us.setToolTip(
            "FPGA delay from trigger arrival to FIR-DDR storage"
        )
        fpga_delay_row = QtWidgets.QHBoxLayout()
        fpga_delay_row.addWidget(self.override_fpga_trigger_delay)
        fpga_delay_row.addWidget(self.fpga_trigger_delay_us, 1)
        self.post_read_delay = QtWidgets.QDoubleSpinBox(acquisition_group)
        self.post_read_delay.setRange(0.0, 60.0)
        self.post_read_delay.setDecimals(6)
        self.post_read_delay.setValue(0.1)
        self.post_read_delay.setSuffix(" s")
        advanced_row = QtWidgets.QHBoxLayout()
        advanced_row.addWidget(QtWidgets.QLabel("Input margin:"))
        advanced_row.addWidget(self.input_margin)
        advanced_row.addWidget(QtWidgets.QLabel("Read delay:"))
        advanced_row.addWidget(self.post_read_delay)
        self.force_overwrite = QtWidgets.QCheckBox(
            "Allow overwrite of reserved DDR range",
            acquisition_group,
        )
        self.force_overwrite.setChecked(True)
        advanced_row.addWidget(self.force_overwrite)
        self.fir_profile_status = QtWidgets.QLabel(
            "Identify QICK to show the FIR DDR timing",
            acquisition_group,
        )
        self.fir_profile_status.setWordWrap(True)

        self.acquire_button = QtWidgets.QPushButton(
            "Acquire FIR Trace and Analyze",
            acquisition_group,
        )
        self.acquire_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay)
        )
        front_panel_row = QtWidgets.QVBoxLayout()
        front_panel_row.setContentsMargins(0, 0, 0, 0)
        front_panel_row.setSpacing(2)
        front_panel_row.addWidget(QtWidgets.QLabel("Front panel:"))
        front_panel_row.addWidget(self.front_panel_preview)
        acquisition_form.addRow(front_panel_row)
        acquisition_form.addRow("Input:", input_row)
        acquisition_form.addRow("Stored FIR samples:", samples_row)
        acquisition_form.addRow("Readout/DDC frequency:", self.readout_frequency)
        acquisition_form.addRow("Input board setting:", board_setting_row)
        acquisition_form.addRow("Input filter:", filter_row)
        acquisition_form.addRow("Advanced:", advanced_row)
        acquisition_form.addRow(
            "FPGA trigger-to-store delay:",
            fpga_delay_row,
        )
        acquisition_form.addRow("HWH FIR DDR:", self.fir_profile_status)
        acquisition_form.addRow(self.acquire_button)
        acquisition_form.addRow("Status:", self.acquisition_status)
        outer.addWidget(acquisition_group)

        source_group = QtWidgets.QGroupBox("Saved I Trace (Optional)", self)
        source_form = QtWidgets.QFormLayout(source_group)
        self.source_status = QtWidgets.QLabel("No I trace loaded", source_group)
        self.source_status.setWordWrap(True)
        self.database_path = QtWidgets.QLineEdit(
            str(default_database_path or DEFAULT_NOISE_ANALYSIS_SETTINGS["database_path"])
        )
        self.browse_database = QtWidgets.QToolButton(source_group)
        self.browse_database.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton)
        )
        self.browse_database.setToolTip("Select a QCoDeS database")
        database_row = QtWidgets.QHBoxLayout()
        database_row.addWidget(self.database_path, 1)
        database_row.addWidget(self.browse_database)
        self.run_id = QtWidgets.QSpinBox(source_group)
        self.run_id.setRange(0, 2_147_483_647)
        self.run_id.setSpecialValueText("Latest saved I-trace run")
        self.run_id.setToolTip(
            "Use 0 for the latest compatible QICK I-trace run, or enter a Run ID"
        )
        self.load_button = QtWidgets.QPushButton("Load Saved Run", source_group)
        self.load_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton)
        )
        load_row = QtWidgets.QHBoxLayout()
        load_row.addWidget(self.run_id, 1)
        load_row.addWidget(self.load_button)
        source_form.addRow("Source:", self.source_status)
        source_form.addRow("QCoDeS DB:", database_row)
        source_form.addRow("Saved run:", load_row)
        outer.addWidget(source_group)

        selector_group = QtWidgets.QGroupBox("Trace Selection", self)
        selector_form = QtWidgets.QFormLayout(selector_group)
        self.point_index = QtWidgets.QSpinBox(selector_group)
        self.repetition_index = QtWidgets.QSpinBox(selector_group)
        for widget in (self.point_index, self.repetition_index):
            # Preserve JSON selections before a run is loaded; set_collection()
            # narrows these bounds to the actual trace dimensions.
            widget.setRange(0, 2_147_483_647)
        selector_form.addRow("Sweep point index:", self.point_index)
        selector_form.addRow("Repetition index:", self.repetition_index)
        outer.addWidget(selector_group)

        conversion_group = QtWidgets.QGroupBox("Current Conversion", self)
        conversion_form = QtWidgets.QFormLayout(conversion_group)
        self.input_mode = QtWidgets.QComboBox(conversion_group)
        self.input_mode.addItem("Voltage trace (V)", "voltage")
        self.input_mode.addItem("ADC units scaled to volts", "adc")
        self.input_mode.addItem("Current trace already in A", "current")
        self.transimpedance_gain = QtWidgets.QDoubleSpinBox(conversion_group)
        self.transimpedance_gain.setRange(1.0e-12, 1.0e20)
        self.transimpedance_gain.setDecimals(6)
        self.transimpedance_gain.setValue(1.0e8)
        self.transimpedance_gain.setSuffix(" V/A")
        self.input_scale = QtWidgets.QDoubleSpinBox(conversion_group)
        self.input_scale.setRange(1.0e-18, 1.0e12)
        self.input_scale.setDecimals(12)
        self.input_scale.setValue(1.0)
        self.input_scale.setSuffix(" V/unit")
        conversion_form.addRow("I trace representation:", self.input_mode)
        conversion_form.addRow("Transimpedance gain:", self.transimpedance_gain)
        conversion_form.addRow("ADC input scale:", self.input_scale)
        outer.addWidget(conversion_group)

        self.dc_calibration_group = QtWidgets.QGroupBox(
            "Apply DC Input Voltage Calibration",
            self,
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
        self.dc_calibration_browse.setText("...")
        self.dc_calibration_browse.setToolTip(
            "Select a DC voltage calibration database"
        )
        calibration_path_row = QtWidgets.QHBoxLayout()
        calibration_path_row.addWidget(self.dc_calibration_path, 1)
        calibration_path_row.addWidget(self.dc_calibration_browse)
        self.dc_calibration_run_id = QtWidgets.QSpinBox(
            self.dc_calibration_group
        )
        self.dc_calibration_run_id.setRange(0, 2_147_483_647)
        self.dc_calibration_run_id.setSpecialValueText(
            "Latest matching channel/gain"
        )
        self.dc_calibration_readout_ch = QtWidgets.QSpinBox(
            self.dc_calibration_group
        )
        self.dc_calibration_readout_ch.setRange(0, 255)
        self.dc_calibration_input_gain = QtWidgets.QDoubleSpinBox(
            self.dc_calibration_group
        )
        self.dc_calibration_input_gain.setRange(-6.0, 26.0)
        self.dc_calibration_input_gain.setDecimals(2)
        self.dc_calibration_input_gain.setSuffix(" dB")
        self.dc_calibration_status = QtWidgets.QLabel(
            "Disabled",
            self.dc_calibration_group,
        )
        self.dc_calibration_status.setWordWrap(True)
        calibration_form.addRow("Calibration DB:", calibration_path_row)
        calibration_form.addRow("Run ID:", self.dc_calibration_run_id)
        calibration_form.addRow(
            "Readout channel:",
            self.dc_calibration_readout_ch,
        )
        calibration_form.addRow(
            "DC input gain:",
            self.dc_calibration_input_gain,
        )
        calibration_form.addRow("Status:", self.dc_calibration_status)
        outer.addWidget(self.dc_calibration_group)

        spectrum_group = QtWidgets.QGroupBox("Spectrum", self)
        spectrum_form = QtWidgets.QFormLayout(spectrum_group)
        self.sample_rate = QtWidgets.QDoubleSpinBox(spectrum_group)
        self.sample_rate.setRange(1.0e-9, 1.0e12)
        self.sample_rate.setDecimals(6)
        self.sample_rate.setValue(1.0e6)
        self.sample_rate.setSuffix(" Hz")
        self.window = QtWidgets.QComboBox(spectrum_group)
        self.window.addItems(list(WINDOWS))
        self.detrend = QtWidgets.QComboBox(spectrum_group)
        self.detrend.addItems(list(DETREND_MODES))
        self.nfft = QtWidgets.QSpinBox(spectrum_group)
        self.nfft.setRange(0, 100_000_000)
        self.nfft.setSpecialValueText("Trace length")
        spectrum_form.addRow("Sampling rate:", self.sample_rate)
        spectrum_form.addRow("Window:", self.window)
        spectrum_form.addRow("Detrend:", self.detrend)
        spectrum_form.addRow("NFFT (zero pads only):", self.nfft)
        outer.addWidget(spectrum_group)

        self.analyze_button = QtWidgets.QPushButton("Analyze I Trace", self)
        self.analyze_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay)
        )
        outer.addWidget(self.analyze_button)
        self.statistics = QtWidgets.QLabel("Load an I trace to calculate noise.", self)
        self.statistics.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.statistics.setWordWrap(True)
        outer.addWidget(self.statistics)

        self.plot = NoiseAnalysisPlotWidget(self)
        page_layout.addWidget(self.plot, 1)

        self.front_panel_preview.activated.connect(
            lambda: self.front_panel_requested.emit(self)
        )
        self.acquire_button.clicked.connect(self._request_acquisition)
        self.fir_samples.valueChanged.connect(self._update_capture_duration)
        self.override_fpga_trigger_delay.toggled.connect(
            self._update_fpga_trigger_delay_controls
        )
        self.fpga_trigger_delay_us.valueChanged.connect(
            self._update_capture_duration
        )
        self.sample_rate.valueChanged.connect(self._update_capture_duration)
        self.input_board.currentTextChanged.connect(
            self._update_input_board_controls
        )
        self.readout_channel.valueChanged.connect(
            lambda value: self.front_panel_preview.set_channels(input_ch=value)
        )
        self.browse_database.clicked.connect(self._browse_database)
        self.load_button.clicked.connect(self._request_load)
        self.analyze_button.clicked.connect(self.analyze_selected_trace)
        self.point_index.valueChanged.connect(self._selection_changed)
        self.repetition_index.valueChanged.connect(self._selection_changed)
        self.input_mode.currentIndexChanged.connect(self._update_mode_controls)
        self.dc_calibration_group.toggled.connect(
            self._calibration_controls_changed
        )
        self.dc_calibration_path.editingFinished.connect(
            self._calibration_controls_changed
        )
        self.dc_calibration_run_id.valueChanged.connect(
            self._calibration_controls_changed
        )
        self.dc_calibration_readout_ch.valueChanged.connect(
            self._calibration_controls_changed
        )
        self.dc_calibration_input_gain.valueChanged.connect(
            self._calibration_controls_changed
        )
        self.dc_calibration_browse.clicked.connect(
            self._browse_dc_calibration
        )
        self._update_capture_duration()
        self._update_input_board_controls()
        self._update_mode_controls()
        self._update_fpga_trigger_delay_controls()

    def connection_config(self):
        """Return the QICK connection mirrored from the shared Setup menu."""
        return self.acquisition_config().connection_config

    def set_connection_values(self, connection) -> None:
        """Mirror the application-wide QICK connection into this tab."""
        self.acquisition_host.setText(str(connection.host))
        self.acquisition_port.setValue(int(connection.ns_port))
        self.acquisition_proxy.setText(str(connection.proxy_name))

    def acquisition_config(self) -> NoiseAcquisitionConfig:
        return NoiseAcquisitionConfig(
            host=self.acquisition_host.text().strip(),
            ns_port=self.acquisition_port.value(),
            proxy_name=self.acquisition_proxy.text().strip(),
            ro_ch=self.readout_channel.value(),
            input_board_type=self.input_board.currentText(),
            nqz=self.input_nqz.value(),
            fir_samples=self.fir_samples.value(),
            readout_frequency_mhz=self.readout_frequency.value(),
            attenuation_db=self.input_attenuation.value(),
            dc_gain_db=self.input_dc_gain.value(),
            filter_type=self.input_filter.currentText(),
            filter_cutoff_ghz=self.filter_cutoff.value(),
            filter_bandwidth_ghz=self.filter_bandwidth.value(),
            margin_input_samples=self.input_margin.value(),
            fpga_trigger_delay_us=(
                self.fpga_trigger_delay_us.value()
                if (
                    self.override_fpga_trigger_delay.isChecked()
                    and self._fir_uses_fpga_trigger_delay is not False
                )
                else None
            ),
            force_overwrite=self.force_overwrite.isChecked(),
            post_run_read_delay_seconds=self.post_read_delay.value(),
        )

    def configured_spec(self):
        """Expose the selected input through the shared front-panel API."""
        return self.acquisition_config().readout_spec()

    def apply_front_panel_settings(self, values: Mapping[str, object]) -> None:
        """Apply one graphical ADC selection only to this Noise tab."""
        self.readout_channel.setValue(int(values["readout_ch"]))
        board = str(values["input_board_type"])
        board_index = self.input_board.findText(board)
        if board_index < 0:
            raise ValueError(f"unsupported input board {board!r}")
        self.input_board.setCurrentIndex(board_index)
        self.input_nqz.setValue(int(values.get("readout_nqz", 1)))
        self.input_attenuation.setValue(float(
            values.get("readout_attenuation_db", self.input_attenuation.value())
        ))
        self.input_dc_gain.setValue(float(
            values.get("readout_dc_gain_db", self.input_dc_gain.value())
        ))
        filter_type = str(values.get(
            "readout_filter_type", self.input_filter.currentText()
        ))
        filter_index = self.input_filter.findText(filter_type)
        if filter_index >= 0:
            self.input_filter.setCurrentIndex(filter_index)
        self.filter_cutoff.setValue(float(values.get(
            "readout_filter_cutoff_ghz", self.filter_cutoff.value()
        )))
        self.filter_bandwidth.setValue(float(values.get(
            "readout_filter_bandwidth_ghz", self.filter_bandwidth.value()
        )))
        self.dc_calibration_readout_ch.setValue(self.readout_channel.value())
        self.dc_calibration_input_gain.setValue(self.input_dc_gain.value())
        self.front_panel_preview.set_channels(input_ch=self.readout_channel.value())

    def set_front_panel_configuration(self, configuration) -> None:
        self.front_panel_preview.set_configuration(configuration)
        self.front_panel_preview.set_channels(input_ch=self.readout_channel.value())
        sample_rate_hz = getattr(configuration, "fir_sample_rate_hz", None)
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
        if sample_rate_hz is not None:
            self.sample_rate.setValue(float(sample_rate_hz))
            self.fir_profile_status.setText(str(configuration.fir_rate_label))
        else:
            self.fir_profile_status.setText(
                "HWH FIR DDR sample rate is unavailable"
            )
        self._update_fpga_trigger_delay_controls()
        self._update_capture_duration()

    def _update_fpga_trigger_delay_controls(self, *_args) -> None:
        supported = self._fir_uses_fpga_trigger_delay is not False
        self.override_fpga_trigger_delay.setEnabled(supported)
        self.fpga_trigger_delay_us.setEnabled(
            supported and self.override_fpga_trigger_delay.isChecked()
        )
        self._update_capture_duration()

    def _update_capture_duration(self, _value: float = 0.0) -> None:
        sample_rate_hz = float(self.sample_rate.value())
        seconds = self.fir_samples.value() / sample_rate_hz
        if np.isclose(sample_rate_hz, 1_000_000.0):
            rate_label = "1 MSPS"
        elif np.isclose(sample_rate_hz, 50_000.0):
            rate_label = "50 kSPS"
        else:
            rate_label = f"{sample_rate_hz:g} S/s"
        if self._fir_uses_fpga_trigger_delay:
            if self.override_fpga_trigger_delay.isChecked():
                delay = (
                    f", FPGA delay override "
                    f"{self.fpga_trigger_delay_us.value():g} us"
                )
            else:
                delay = f", HWH FPGA delay {self._fir_trigger_delay_us:g} us"
        else:
            delay = ""
        self.capture_duration.setText(
            f"{seconds:g} s at {rate_label}{delay}"
        )

    def _update_input_board_controls(self, _board: str = "") -> None:
        is_rf = self.input_board.currentText() == "RF_In"
        self.input_attenuation.setEnabled(is_rf)
        self.input_filter.setEnabled(is_rf)
        self.filter_cutoff.setEnabled(is_rf)
        self.filter_bandwidth.setEnabled(is_rf)
        self.input_dc_gain.setEnabled(not is_rf)

    def _request_acquisition(self) -> None:
        try:
            config = self.acquisition_config()
        except (TypeError, ValueError) as exc:
            QtWidgets.QMessageBox.warning(
                self,
                "Cannot acquire noise trace",
                str(exc),
            )
            return
        self.acquire_requested.emit(config)

    def _browse_database(self) -> None:
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select QCoDeS database",
            self.database_path.text(),
            "SQLite database (*.db);;All files (*)",
        )
        if path:
            self.database_path.setText(path)

    def _request_load(self) -> None:
        path = self.database_path.text().strip()
        if not path:
            QtWidgets.QMessageBox.warning(
                self, "Cannot load I trace", "QCoDeS database path is empty."
            )
            return
        self.load_requested.emit(path, self.run_id.value())

    def _browse_dc_calibration(self) -> None:
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select DC voltage calibration database",
            self.dc_calibration_path.text().strip(),
            "SQLite database (*.db);;All files (*)",
        )
        if path:
            self.dc_calibration_path.setText(path)
            self._calibration_controls_changed()

    def _calibration_controls_changed(self, *_args) -> None:
        self._dc_calibration_cache_key = None
        self._dc_calibration_cache = None
        if not self.dc_calibration_group.isChecked():
            self.dc_calibration_status.setText("Disabled")
        elif self._collection is not None:
            self.analyze_selected_trace()

    def _selected_dc_calibration(self, config: NoiseAnalysisConfig):
        if not self.dc_calibration_group.isChecked():
            self.dc_calibration_status.setText("Disabled")
            return None
        unit = "" if self._collection is None else self._collection.unit
        if str(unit).strip().lower() in {"v", "a"}:
            self.dc_calibration_status.setText(
                f"Not applied: loaded trace is already stored in {unit}"
            )
            return None
        if config.input_mode != "adc":
            self.dc_calibration_status.setText(
                "Not applied: select 'ADC units scaled to volts' for a raw trace"
            )
            return None
        path = self.dc_calibration_path.text().strip()
        if not path:
            raise ValueError("DC voltage calibration database path is empty")
        key = (
            str(Path(path).expanduser()),
            self.dc_calibration_run_id.value(),
            self.dc_calibration_readout_ch.value(),
            self.dc_calibration_input_gain.value(),
        )
        if key != self._dc_calibration_cache_key:
            self._dc_calibration_cache = load_dc_voltage_calibration(
                path,
                readout_ch=self.dc_calibration_readout_ch.value(),
                input_dc_gain_db=self.dc_calibration_input_gain.value(),
                run_id=self.dc_calibration_run_id.value(),
            )
            self._dc_calibration_cache_key = key
        calibration = self._dc_calibration_cache
        self.dc_calibration_status.setText(
            f"Run {calibration.run_id}: subtract offset "
            f"{calibration.offset_adc:.6g} ADC, divide by "
            f"{calibration.response_adc_per_v:.6g} ADC/V"
        )
        return calibration

    def _selection_changed(self, _value: int) -> None:
        if self._collection is not None:
            self.analyze_selected_trace()

    def _update_mode_controls(self, _index: int = 0) -> None:
        mode = self.input_mode.currentData()
        self.transimpedance_gain.setEnabled(mode != "current")
        self.input_scale.setEnabled(mode == "adc")

    def _config(self) -> NoiseAnalysisConfig:
        return NoiseAnalysisConfig(
            input_mode=str(self.input_mode.currentData()),
            transimpedance_gain_v_per_a=self.transimpedance_gain.value(),
            input_scale_v_per_unit=self.input_scale.value(),
            sample_rate_hz=self.sample_rate.value(),
            window=self.window.currentText(),
            detrend=self.detrend.currentText(),
            nfft=self.nfft.value(),
        )

    def _set_input_mode_for_unit(self, unit: str) -> None:
        normalized = str(unit).strip().lower()
        mode = "current" if normalized == "a" else (
            "voltage" if normalized == "v" else "adc"
        )
        index = self.input_mode.findData(mode)
        if index >= 0:
            self.input_mode.setCurrentIndex(index)

    def set_collection(self, collection: NoiseTraceCollection) -> None:
        self._collection = collection
        self.database_path.setText(
            collection.database_path or self.database_path.text()
        )
        if collection.run_id:
            self.run_id.setValue(collection.run_id)
        with QtCore.QSignalBlocker(self.point_index):
            self.point_index.setRange(0, collection.point_count - 1)
            self.point_index.setValue(
                min(self.point_index.value(), collection.point_count - 1)
            )
        with QtCore.QSignalBlocker(self.repetition_index):
            self.repetition_index.setRange(0, collection.repetition_count - 1)
            self.repetition_index.setValue(
                min(
                    self.repetition_index.value(),
                    collection.repetition_count - 1,
                )
            )
        self.sample_rate.setValue(float(collection.sample_rate_hz))
        self._set_input_mode_for_unit(collection.unit)
        self.source_status.setText(
            f"{collection.source or 'I trace'} | {collection.point_count} point(s) x "
            f"{collection.repetition_count} repetition(s) x "
            f"{collection.sample_count} samples | {collection.unit}"
        )
        if collection.source.startswith("Direct FIR-DDR"):
            self.acquisition_status.setText(
                f"Completed: {collection.sample_count:,} FIR samples from "
                f"readout {self.readout_channel.value()}"
            )
        self.set_loading(False)
        self.analyze_selected_trace()

    def set_experiment_result(self, stored: Any) -> None:
        dataset = getattr(stored, "dataset", None)
        if dataset is None:
            self.set_collection(load_noise_trace_collection(
                stored.database_path,
                stored.run_id,
            ))
            return
        arrays = load_qick_iq_arrays(dataset)
        metadata = arrays.get("metadata", {})
        layout = metadata.get("measurement_layout", {})
        sample_rate_hz = float(
            layout.get(
                "sample_rate_hz",
                1.0e6 / float(layout.get("sample_period_us", 1.0)),
            )
        )
        self.set_collection(NoiseTraceCollection(
            i_traces=np.asarray(arrays["i"], dtype=np.float64),
            sample_rate_hz=sample_rate_hz,
            unit=str(arrays.get("iq_unit", "ADC units")),
            source=f"Latest Experiment Run {int(stored.run_id)}",
            database_path=str(stored.database_path),
            run_id=int(stored.run_id),
        ))

    def analyze_selected_trace(self) -> Optional[NoiseAnalysisResult]:
        if self._collection is None:
            self.statistics.setText("Load an I trace to calculate noise.")
            return None
        try:
            trace = self._collection.trace(
                self.point_index.value(), self.repetition_index.value()
            )
            config = self._config()
            input_unit = self._collection.unit
            calibration = self._selected_dc_calibration(config)
            if calibration is not None:
                trace = calibration.convert_adc(trace)
                config = NoiseAnalysisConfig(
                    input_mode="voltage",
                    transimpedance_gain_v_per_a=(
                        config.transimpedance_gain_v_per_a
                    ),
                    input_scale_v_per_unit=1.0,
                    sample_rate_hz=config.sample_rate_hz,
                    window=config.window,
                    detrend=config.detrend,
                    nfft=config.nfft,
                )
                input_unit = f"V (DC calibration Run {calibration.run_id})"
            result = analyze_i_trace(
                trace,
                config,
                source=(
                    f"{self._collection.source}, point {self.point_index.value()}, "
                    f"rep {self.repetition_index.value()}"
                ),
                input_unit=input_unit,
            )
        except (LookupError, OSError, RuntimeError, TypeError, ValueError) as exc:
            self.statistics.setText(f"Analysis failed: {exc}")
            return None
        self._result = result
        self.plot.set_result(result)
        self.statistics.setText(
            f"Mean {result.mean_current_a:.6e} A | "
            f"RMS {result.rms_current_a:.6e} A | "
            f"Std {result.std_current_a:.6e} A | "
            f"Duration {result.time_s[-1]:.6g} s | "
            f"Resolution {result.config.sample_rate_hz / max(1, result.frequency_hz.size * 2 - 2):.6g} Hz"
        )
        return result

    def set_loading(self, loading: bool, message: str = "") -> None:
        self.load_button.setEnabled(not loading)
        self.run_id.setEnabled(not loading)
        self.database_path.setEnabled(not loading)
        self.browse_database.setEnabled(not loading)
        self.acquire_button.setEnabled(not loading)
        self.analyze_button.setEnabled(not loading)
        if message:
            self.source_status.setText(str(message))

    def set_acquiring(self, acquiring: bool, message: str = "") -> None:
        self.acquire_button.setEnabled(not acquiring)
        self.load_button.setEnabled(not acquiring)
        self.analyze_button.setEnabled(not acquiring)
        if message:
            self.acquisition_status.setText(str(message))

    def update_acquisition_progress(self, percent: int, message: str) -> None:
        self.acquisition_status.setText(f"{int(percent)}% | {message}")

    def show_acquisition_error(self, message: str) -> None:
        self.set_acquiring(False, f"Acquisition failed: {message}")

    def show_load_error(self, message: str) -> None:
        self.set_loading(False, f"Load failed: {message}")

    def detach_plot(self) -> NoiseAnalysisPlotWidget:
        self.layout().removeWidget(self.plot)
        self.plot.setParent(None)
        return self.plot

    def settings_dict(self) -> dict:
        return {
            "acquisition_host": self.acquisition_host.text().strip(),
            "acquisition_ns_port": self.acquisition_port.value(),
            "acquisition_proxy_name": self.acquisition_proxy.text().strip(),
            "acquisition_readout_ch": self.readout_channel.value(),
            "acquisition_input_board_type": self.input_board.currentText(),
            "acquisition_nqz": self.input_nqz.value(),
            "acquisition_fir_samples": self.fir_samples.value(),
            "acquisition_readout_frequency_mhz": self.readout_frequency.value(),
            "acquisition_input_attenuation_db": self.input_attenuation.value(),
            "acquisition_dc_gain_db": self.input_dc_gain.value(),
            "acquisition_filter_type": self.input_filter.currentText(),
            "acquisition_filter_cutoff_ghz": self.filter_cutoff.value(),
            "acquisition_filter_bandwidth_ghz": self.filter_bandwidth.value(),
            "acquisition_margin_input_samples": self.input_margin.value(),
            "acquisition_fpga_trigger_delay_us": (
                self.fpga_trigger_delay_us.value()
                if self.override_fpga_trigger_delay.isChecked()
                else None
            ),
            "acquisition_force_overwrite": self.force_overwrite.isChecked(),
            "acquisition_post_run_read_delay_seconds": self.post_read_delay.value(),
            "database_path": self.database_path.text().strip(),
            "run_id": self.run_id.value(),
            "point_index": self.point_index.value(),
            "repetition_index": self.repetition_index.value(),
            "input_mode": str(self.input_mode.currentData()),
            "transimpedance_gain_v_per_a": self.transimpedance_gain.value(),
            "input_scale_v_per_unit": self.input_scale.value(),
            "sample_rate_hz": self.sample_rate.value(),
            "window": self.window.currentText(),
            "detrend": self.detrend.currentText(),
            "nfft": self.nfft.value(),
            "dc_voltage_calibration_enabled": (
                self.dc_calibration_group.isChecked()
            ),
            "dc_voltage_calibration_database_path": (
                self.dc_calibration_path.text().strip()
            ),
            "dc_voltage_calibration_run_id": (
                self.dc_calibration_run_id.value()
            ),
            "dc_voltage_calibration_readout_ch": (
                self.dc_calibration_readout_ch.value()
            ),
            "dc_voltage_calibration_input_gain_db": (
                self.dc_calibration_input_gain.value()
            ),
        }

    def load_settings(self, values: Mapping[str, Any]) -> None:
        settings = normalize_noise_analysis_settings(values)
        self.acquisition_host.setText(settings["acquisition_host"])
        self.acquisition_port.setValue(settings["acquisition_ns_port"])
        self.acquisition_proxy.setText(settings["acquisition_proxy_name"])
        self.readout_channel.setValue(settings["acquisition_readout_ch"])
        self.input_board.setCurrentText(
            settings["acquisition_input_board_type"]
        )
        self.input_nqz.setValue(settings["acquisition_nqz"])
        self.fir_samples.setValue(settings["acquisition_fir_samples"])
        self.readout_frequency.setValue(
            settings["acquisition_readout_frequency_mhz"]
        )
        self.input_attenuation.setValue(
            settings["acquisition_input_attenuation_db"]
        )
        self.input_dc_gain.setValue(settings["acquisition_dc_gain_db"])
        self.input_filter.setCurrentText(settings["acquisition_filter_type"])
        self.filter_cutoff.setValue(
            settings["acquisition_filter_cutoff_ghz"]
        )
        self.filter_bandwidth.setValue(
            settings["acquisition_filter_bandwidth_ghz"]
        )
        self.input_margin.setValue(
            settings["acquisition_margin_input_samples"]
        )
        saved_fpga_delay = settings["acquisition_fpga_trigger_delay_us"]
        self.override_fpga_trigger_delay.setChecked(
            saved_fpga_delay is not None
        )
        if saved_fpga_delay is not None:
            self.fpga_trigger_delay_us.setValue(saved_fpga_delay)
        elif self.sample_rate.value() > 0.0:
            self.fpga_trigger_delay_us.setValue(
                self._fir_trigger_delay_us
            )
        self.force_overwrite.setChecked(
            settings["acquisition_force_overwrite"]
        )
        self.post_read_delay.setValue(
            settings["acquisition_post_run_read_delay_seconds"]
        )
        self.database_path.setText(settings["database_path"])
        self.run_id.setValue(settings["run_id"])
        self.point_index.setValue(settings["point_index"])
        self.repetition_index.setValue(settings["repetition_index"])
        mode_index = self.input_mode.findData(settings["input_mode"])
        self.input_mode.setCurrentIndex(mode_index)
        self.transimpedance_gain.setValue(
            settings["transimpedance_gain_v_per_a"]
        )
        self.input_scale.setValue(settings["input_scale_v_per_unit"])
        self.sample_rate.setValue(settings["sample_rate_hz"])
        self.window.setCurrentText(settings["window"])
        self.detrend.setCurrentText(settings["detrend"])
        self.nfft.setValue(settings["nfft"])
        with QtCore.QSignalBlocker(self.dc_calibration_group):
            self.dc_calibration_group.setChecked(
                settings["dc_voltage_calibration_enabled"]
            )
        with QtCore.QSignalBlocker(self.dc_calibration_path):
            self.dc_calibration_path.setText(
                settings["dc_voltage_calibration_database_path"]
            )
        with QtCore.QSignalBlocker(self.dc_calibration_run_id):
            self.dc_calibration_run_id.setValue(
                settings["dc_voltage_calibration_run_id"]
            )
        with QtCore.QSignalBlocker(self.dc_calibration_readout_ch):
            self.dc_calibration_readout_ch.setValue(
                settings["dc_voltage_calibration_readout_ch"]
            )
        with QtCore.QSignalBlocker(self.dc_calibration_input_gain):
            self.dc_calibration_input_gain.setValue(
                settings["dc_voltage_calibration_input_gain_db"]
            )
        self._calibration_controls_changed()
        self._update_capture_duration()
        self._update_input_board_controls()
        self._update_mode_controls()
        self._update_fpga_trigger_delay_controls()


__all__ = [
    "DEFAULT_NOISE_ANALYSIS_SETTINGS",
    "NoiseAnalysisConfig",
    "NoiseAnalysisPanel",
    "NoiseAnalysisPlotWidget",
    "NoiseAnalysisResult",
    "NoiseTraceCollection",
    "NoiseAcquisitionWorker",
    "NoiseTraceLoadWorker",
    "analyze_i_trace",
    "load_noise_trace_collection",
    "normalize_noise_analysis_settings",
]
