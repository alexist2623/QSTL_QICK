"""Autonomous SquarePulse output controls and legacy waveform configuration."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from threading import Event
import traceback

from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg

try:
    from .qick_qcodes_experiment import connect_qick
    from .dc_waveform_core import DEFAULT_QICK_FULL_SCALE_MV
    from .qick_fine_tune_sweep import normalized_to_dac
    from .qick_square_dds import SquarePulseConfig
    from .qick_square_output import SquareOutputSelector
except ImportError:
    from qick_qcodes_experiment import connect_qick
    from dc_waveform_core import DEFAULT_QICK_FULL_SCALE_MV
    from qick_fine_tune_sweep import normalized_to_dac
    from qick_square_dds import SquarePulseConfig
    from qick_square_output import SquareOutputSelector


@dataclass(frozen=True)
class SquareWaveConfig:
    gen_ch: int = 1
    frequency_hz: float = 40_000.0
    amplitude_mv: float = 10.0
    offset_mv: float = 0.0
    duty_percent: float = 50.0
    full_scale_mv: float = DEFAULT_QICK_FULL_SCALE_MV
    zero_code: float = 1120.0
    phase_deg: float = 0.0
    rc_enabled: bool = False
    rc_tau_us: float = 1000.0

    def __post_init__(self):
        if isinstance(self.gen_ch, bool) or not isinstance(self.gen_ch, int) or self.gen_ch < 0:
            raise ValueError("Generator channel must be a nonnegative integer")
        if not isinstance(self.rc_enabled, bool):
            raise ValueError("RC enabled must be boolean")
        if not 10 <= self.rc_tau_us <= 1_000_000:
            raise ValueError("RC tau must be between 10 us and 1000 ms")
        for name, value in asdict(self).items():
            if name == "rc_enabled":
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if self.frequency_hz <= 0 or self.amplitude_mv <= 0:
            raise ValueError("Frequency and peak amplitude must be positive")
        if not 0 < self.duty_percent < 100:
            raise ValueError("Duty cycle must be between 0 and 100 percent")
        if self.full_scale_mv <= 0:
            raise ValueError("Output full scale must be positive")

    def codes(self, gen_cfg):
        invalid_lsb = int(gen_cfg.get("dac_invalid_lsb", 0))
        quantum = 1 << invalid_lsb
        min_code, max_code = int(gen_cfg["minv"]), int(gen_cfg["maxv"])
        full_scale_code = max(abs(min_code), max_code + quantum)
        result = []
        for label, voltage in (("High", self.offset_mv + self.amplitude_mv),
                               ("Low", self.offset_mv - self.amplitude_mv)):
            if abs(voltage) > self.full_scale_mv:
                raise ValueError(f"{label} voltage exceeds +/-{self.full_scale_mv:g} mV output full scale")
            # Use the AWG Tuning conversion, adding offset before quantization.
            amplitude = voltage / self.full_scale_mv + self.zero_code / full_scale_code
            if not isfinite(amplitude) or not -1.0 <= amplitude <= 1.0:
                raise ValueError(f"{label} DAC level including offset compensation exceeds the channel range")
            code = normalized_to_dac(amplitude, min_code=min_code,
                                     max_code=max_code, invalid_lsb=invalid_lsb)
            result.append(code)
        if result[0] == result[1]:
            raise ValueError("The two levels quantize to the same DAC code; increase amplitude")
        return tuple(result)


def normalize_square_wave_settings(settings=None):
    if settings is not None and not isinstance(settings, dict):
        raise TypeError("Square-wave settings must be a JSON object")
    values = dict(settings or {})
    # Older square-wave settings used measured power or a manual slope.
    # Preserve waveform values while migrating to the explicit output range.
    for obsolete in ("codes_per_mv", "calibration_database_path",
                     "calibration_run_id", "calibration_reference_ohm"):
        values.pop(obsolete, None)
    return asdict(SquareWaveConfig(**values))


def build_square_wave_program(soccfg, config, *, tproc_mhz=None):
    """Build an output-only ASM v1 loop; edge times do not depend on pulse caches."""
    from qick.asm_v1 import QickProgram

    if soccfg["tprocs"][0]["type"] != "axis_tproc64x32_x8":
        raise ValueError("Square-wave output requires QICK tProcessor v1")
    if config.gen_ch >= len(soccfg["gens"]):
        raise ValueError("Selected generator is absent from the loaded firmware")
    gen_cfg = soccfg["gens"][config.gen_ch]
    if gen_cfg.get("type") == "axis_square_pulse_v1":
        return build_square_dds_program(soccfg, config, tproc_mhz=tproc_mhz)
    if gen_cfg.get("type") not in ("axis_awg_tuning_v1", "axis_awg_tuning_v2"):
        raise ValueError("Select an AWG tuning DAC generator")
    clock = float(soccfg["tprocs"][0]["f_time"] if tproc_mhz is None else tproc_mhz)
    if not isfinite(clock) or clock <= 0:
        raise ValueError("tProcessor clock must be positive and finite")
    period = int(round(clock * 1e6 / config.frequency_hz))
    high_ticks = int(round(period * config.duty_percent / 100.0))
    lead = 512
    if period < 512:
        raise ValueError(f"Frequency is too high; maximum is {clock * 1e6 / 512:g} Hz")
    if period + lead >= 2**31:
        raise ValueError("Period exceeds the tProcessor timestamp range")
    fabric_mhz = float(gen_cfg["f_fabric"])
    if min(high_ticks, period - high_ticks) * fabric_mhz / clock < 16:
        raise ValueError("Each level must last at least 16 DAC fabric clocks")
    high_code, low_code = config.codes(gen_cfg)

    class SquareWaveProgram(QickProgram):
        def __init__(self):
            super().__init__(soccfg)
            # Match the shared Setup clock override used by the other QICK tabs.
            self.tproccfg = dict(self.tproccfg, f_time=clock)
            self.declare_gen(ch=config.gen_ch)
            self.synci(lead)
            self.label("SQUARE_FOREVER")
            # SET holds its value until the next SET. Explicit edge timestamps
            # avoid Python length-cache and runtime memri scheduling mismatches.
            self.set_pulse_registers(ch=config.gen_ch, style="awg_set", value=high_code, duration=1)
            self.pulse(ch=config.gen_ch, t=lead)
            self.set_pulse_registers(ch=config.gen_ch, style="awg_set", value=low_code, duration=1)
            self.pulse(ch=config.gen_ch, t=lead + high_ticks)
            # Bound look-ahead. Short waits also let the v1 stop API's END
            # overwrite be fetched at low frequencies instead of sitting in
            # one long WAIT until after the API reloads the program memory.
            # WAIT shares SET's FIFO, so pace on a port unused by this program.
            wait_port = (int(gen_cfg["tproc_ch"]) + 1) % 8
            self.regwi(0, 1, 0)
            self.safe_regwi(0, 2, period // 256 - 1)
            self.label("SQUARE_PACE")
            self.mathi(0, 1, 1, "+", 256)
            self.wait(0, wait_port, 1)
            self.loopnz(0, 2, "SQUARE_PACE")
            self.waiti(wait_port, period)
            self.synci(period)
            self.condj(0, 0, "==", 0, "SQUARE_FOREVER")
            self.summary = dict(requested_frequency_hz=config.frequency_hz,
                                actual_frequency_hz=clock * 1e6 / period,
                                period_cycles=period, high_cycles=high_ticks,
                                low_cycles=period-high_ticks, tproc_mhz=clock,
                                high_code=high_code, low_code=low_code,
                                actual_duty_percent=100.0*high_ticks/period,
                                full_scale_mv=config.full_scale_mv)

    program = SquareWaveProgram()
    program.compile()
    return program


def build_square_dds_program(soccfg, config, *, tproc_mhz=None):
    """Enable the autonomous IP once, then let tProcessor reach END."""
    from qick.asm_v1 import QickProgram
    if config.duty_percent != 50 or config.offset_mv != 0 or config.zero_code != 0:
        raise ValueError("SquarePulse IP uses 50% duty and symmetric +/- amplitude without DC offset")
    gen = soccfg['gens'][config.gen_ch]
    clock = float(soccfg['tprocs'][0]['f_time'] if tproc_mhz is None else tproc_mhz)
    if not isfinite(clock) or clock <= 0:
        raise ValueError("tProcessor clock must be positive and finite")
    settings = SquarePulseConfig(config.gen_ch, config.frequency_hz / 1e6,
                                 config.amplitude_mv, config.phase_deg, config.full_scale_mv,
                                 mute_on_finish=False, rc_enabled=config.rc_enabled, rc_tau_us=config.rc_tau_us)
    freq = settings.word('frequency', settings.frequency_mhz, gen)
    phase = settings.word('phase', settings.phase_deg, gen)
    gain = settings.word('amplitude', settings.amplitude_mv, gen)
    if freq == 0 or gain == 0:
        raise ValueError("Frequency or amplitude rounds to zero for this SquarePulse IP")
    program = QickProgram(soccfg)
    program.tproccfg = dict(program.tproccfg, f_time=clock)
    program.declare_gen(ch=config.gen_ch, nqz=1)
    program.synci(128)
    rc_params = {} if not config.rc_enabled else dict(rc_enable=True, rc_increment=settings.rc_step(gain, gen))
    program.set_pulse_registers(ch=config.gen_ch, style='square', freq=freq, phase=phase,
                                gain=gain, enable=True, reset_phase=False, **rc_params)
    program.pulse(ch=config.gen_ch, t=0)
    program.waiti(int(gen['tproc_ch']), 32)
    program.end()
    program.compile()
    program.summary = dict(output_type='square_pulse', requested_frequency_hz=config.frequency_hz,
                           actual_frequency_hz=freq*float(gen['f_dds'])*1e6/2**32,
                           actual_duty_percent=50., high_code=gain, low_code=-gain,
                           tproc_mhz=clock, full_scale_mv=config.full_scale_mv,
                           phase_deg=phase*360/2**32, rc_enabled=config.rc_enabled, rc_tau_us=config.rc_tau_us)
    return program


class SquareWaveWorker(QtCore.QObject):
    """Configure autonomous output without occupying the next experiment's worker."""
    started = QtCore.pyqtSignal(object)
    finished = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str)
    stop_failed = QtCore.pyqtSignal(str)

    def __init__(self, connection, config, *, tproc_mhz, connector=None, program_factory=None, mute_only=False, current_settings=None):
        super().__init__()
        self.connection, self.config = connection, config
        self.tproc_mhz = tproc_mhz
        self.connector = connector or connect_qick
        self.program_factory = program_factory or build_square_wave_program
        self._stop = Event()
        self.mute_only = mute_only
        self.current_settings = dict(current_settings or {})

    def request_stop(self):
        # Called directly by the GUI: no queued slot while run() is waiting.
        self._stop.set()

    @QtCore.pyqtSlot()
    def run(self):
        soc = None
        touched_hardware = False
        square_ip = False
        error = None
        try:
            if self._stop.is_set():
                self.finished.emit("Start cancelled")
                return
            soc, soccfg = self.connector(self.connection)
            if (self.config.gen_ch >= len(soccfg['gens'])
                    or soccfg['gens'][self.config.gen_ch].get('type') != 'axis_square_pulse_v1'):
                raise ValueError("This tab requires a dedicated SquarePulse IP output")
            square_ip = True
            if not callable(getattr(soc, 'stop_square_pulse', None)):
                raise RuntimeError("Update the board QSTL_QICK library: stop_square_pulse is required")
            if self.mute_only:
                soc.stop_square_pulse(self.config.gen_ch)
                self.finished.emit("Muted: SquarePulse output is zero")
                return
            from qick_dac_current import verify_current_settings
            verify_current_settings(soc, self.current_settings)
            program = self.program_factory(soccfg, self.config, tproc_mhz=self.tproc_mhz)
            if self._stop.is_set():
                self.finished.emit("Start cancelled")
                return
            touched_hardware = True
            program.config_all(soc, reset=True)
            configure_dc = getattr(soc, "rfb_set_gen_dc", None)
            if callable(configure_dc):
                configure_dc(self.config.gen_ch)
            if not self._stop.is_set():
                soc.start_src("internal")
                soc.start_tproc()
                self.started.emit(program.summary)
                if not self._stop.is_set():
                    self.finished.emit("SquarePulse output enabled")
                    return
        except Exception:
            error = traceback.format_exc()
        if touched_hardware:
            while True:
                self._stop.clear()
                try:
                    # lazy=True is a no-op for tProcessor v1 and must not be used.
                    if square_ip:
                        soc.stop_square_pulse(self.config.gen_ch)
                    else:
                        soc.stop_tproc()
                    break
                except Exception:
                    self.stop_failed.emit(traceback.format_exc())
                    self._stop.wait()
        if error:
            self.failed.emit(error)
        else:
            self.finished.emit("Muted: SquarePulse output is zero" if square_ip
                               else "Stopped: soc.stop_tproc() completed")


class SquareWavePanel(QtWidgets.QWidget):
    start_requested = QtCore.pyqtSignal(object)
    stop_requested = QtCore.pyqtSignal()
    front_panel_requested = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        content = QtWidgets.QWidget()
        scroll.setWidget(content)
        editor = QtWidgets.QVBoxLayout(content)
        editor.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll, 1)
        note = QtWidgets.QLabel("Continuous QICK DAC output. Uses the QICK connection and tProcessor clock in Setup.")
        note.setWordWrap(True)
        editor.addWidget(note)
        self.output_selector = SquareOutputSelector(self, channel=0)
        self.output_selector.requested.connect(lambda: self.front_panel_requested.emit(self))
        self.gen_ch = self.output_selector.channel
        editor.addWidget(self.output_selector)
        self.controls = QtWidgets.QGroupBox("Square wave")
        form = QtWidgets.QFormLayout(self.controls)
        definitions = (("frequency_hz", "Frequency (Hz)", 0.2, 1e10, 6),
                       ("amplitude_mv", "Peak amplitude (mV)", 0.000001, 1e5, 6),
                       ("offset_mv", "Waveform offset (mV)", -1e5, 1e5, 6),
                       ("duty_percent", "High-level duty (%)", 0.001, 99.999, 3),
                       ("zero_code", "DAC offset compensation (codes)", -1e9, 1e9, 6),
                       ("full_scale_mv", "Maximum output (+/- mV)", 1.0, 1e6, 6),
                       ("phase_deg", "Phase offset (deg)", -1e6, 1e6, 6),
                       ("rc_tau_us", "RC time constant (us)", 10.0, 1_000_000.0, 6))
        for name, label, minimum, maximum, decimals in definitions:
            widget = QtWidgets.QDoubleSpinBox()
            widget.setRange(minimum, maximum)
            widget.setDecimals(decimals)
            widget.setKeyboardTracking(False)
            setattr(self, name, widget)
            form.addRow(label, widget)
            if name in ('offset_mv', 'zero_code', 'full_scale_mv'):
                form.labelForField(widget).hide()
                widget.hide()
        self.rc_enabled = QtWidgets.QCheckBox("RC compensation")
        form.addRow(self.rc_enabled)
        self.rc_enabled.toggled.connect(self.rc_tau_us.setEnabled)
        editor.addWidget(self.controls)
        self.output_note = QtWidgets.QLabel(
            "Maximum output sets the +/- voltage range, as in AWG Tuning. "
            "Peak amplitude is half the peak-to-peak voltage; High/Low = waveform "
            "offset +/- peak amplitude. DAC offset compensation is added separately. "
            "This tab uses its own maximum output setting.")
        self.output_note.setWordWrap(True)
        editor.addWidget(self.output_note)
        self.plot = pg.PlotWidget()
        self.plot.setLabel("bottom", "Time", units="us")
        self.plot.setLabel("left", "Requested voltage", units="mV")
        self.plot.setMinimumHeight(160)
        self.plot.setMaximumHeight(280)
        self.curve = self.plot.plot(pen=pg.mkPen("#338bd6", width=2))
        editor.addWidget(self.plot, 1)
        row = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton("Start continuous output")
        self.stop_button = QtWidgets.QPushButton("Stop")
        row.addWidget(self.start_button)
        row.addWidget(self.stop_button)
        layout.addLayout(row)
        self.status = QtWidgets.QLabel("Ready")
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.status)
        self.stop_note = QtWidgets.QLabel()
        self.stop_note.setWordWrap(True)
        layout.addWidget(self.stop_note)
        self.load_settings({})
        for name in ("gen_ch", "frequency_hz", "amplitude_mv", "offset_mv", "duty_percent",
                     "zero_code", "full_scale_mv", "phase_deg"):
            getattr(self, name).valueChanged.connect(self.update_preview)
        self.start_button.clicked.connect(self._start)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.set_running(False)
        self.gen_ch.valueChanged.connect(self._sync_output_mode)
        self._sync_output_mode()

    def set_current_state(self, state):
        self._current_state = state
        state.changed.connect(self._refresh_current_scale)
        self.gen_ch.valueChanged.connect(self._refresh_current_scale)
        self._refresh_current_scale()

    def _refresh_current_scale(self, *_args):
        if hasattr(self, '_current_state'):
            self.full_scale_mv.setValue(self._current_state.scale(self.gen_ch.value()))

    def settings_dict(self):
        values = {name: getattr(self, name).value() for name in
                  ("gen_ch", "frequency_hz", "amplitude_mv", "offset_mv", "duty_percent",
                   "zero_code", "full_scale_mv", "phase_deg", "rc_tau_us")}
        values["rc_enabled"] = self.rc_enabled.isChecked()
        return normalize_square_wave_settings(values)

    def resolved_config(self):
        self._refresh_current_scale()
        if self.output_selector.configuration is None:
            raise ValueError("Identify QICK and select the physical SquarePulse output first")
        self.output_selector.validate()
        return SquareWaveConfig(**self.settings_dict())

    def load_settings(self, settings):
        values = normalize_square_wave_settings(settings)
        for name, value in values.items():
            widget = getattr(self, name)
            if name == "rc_enabled":
                continue
            if not widget.minimum() <= value <= widget.maximum():
                raise ValueError(f"{name} is outside the square-wave control range")
        for name, value in values.items():
            widget = getattr(self, name)
            with QtCore.QSignalBlocker(widget):
                if name == "rc_enabled":
                    widget.setChecked(value)
                else:
                    widget.setValue(value)
        self.rc_tau_us.setEnabled(self.rc_enabled.isChecked())
        self.output_selector.load_channel(values['gen_ch'], explicit=bool(settings))
        self._sync_output_mode()
        self._refresh_current_scale()
        self.update_preview()

    def allowed_output_channels(self, configuration):
        return self.output_selector.allowed_channels(configuration)

    def front_panel_values(self):
        return dict(output_ch=self.gen_ch.value(), output_nqz=1)

    def apply_front_panel_settings(self, values):
        if not self.controls.isEnabled():
            raise ValueError("Stop continuous output before changing its port")
        self.output_selector.apply(values)
        self._sync_output_mode()

    def set_configuration(self, configuration):
        self.output_selector.set_configuration(configuration)
        self._sync_output_mode()

    def _sync_output_mode(self):
        fields = ('offset_mv', 'zero_code', 'duty_percent')
        for name, value in zip(fields, (0., 0., 50.)):
            widget = getattr(self, name)
            with QtCore.QSignalBlocker(widget):
                widget.setValue(value)
            widget.setEnabled(False)
        self.phase_deg.setEnabled(True)
        self.output_note.setText(
            "SquarePulse IP: continuous 50% duty, +/- peak amplitude. Phase is an offset; "
            "starting updates the parameters without resetting accumulated phase. "
            "Maximum output sets this tab's voltage range.")
        self.stop_note.setText("Stop mutes the selected SquarePulse IP to zero, including output left running by an AWG experiment.")
        if self.controls.isEnabled():
            self.set_running(False)
        self.update_preview()

    def update_preview(self):
        period = 1e6 / self.frequency_hz.value()
        high_time = period * self.duty_percent.value() / 100
        high = self.offset_mv.value() + self.amplitude_mv.value()
        low = self.offset_mv.value() - self.amplitude_mv.value()
        if self.phase_deg.isEnabled():
            import numpy as np
            x = np.linspace(0, 2*period, 2001)
            y = np.where((x/period+self.phase_deg.value()/360) % 1 < .5, high, low)
            self.curve.setData(x, y)
        else:
            self.curve.setData([0, high_time, high_time, period, period,
                                period+high_time, period+high_time, 2*period],
                               [high, high, low, low, high, high, low, low])
        if self.controls.isEnabled():
            full_scale = self.full_scale_mv.value()
            if max(abs(high), abs(low)) > full_scale:
                self.status.setText(f"High/Low voltage exceeds +/-{full_scale:g} mV maximum output.")
            else:
                self.status.setText(f"Ready: maximum output +/-{full_scale:g} mV; High/Low {high:g} / {low:g} mV.")

    def _start(self):
        try:
            self.start_requested.emit(self.resolved_config())
        except (TypeError, ValueError) as exc:
            self.status.setText(str(exc))

    def set_running(self, running, message=None):
        self.controls.setEnabled(not running)
        self.output_selector.setEnabled(not running)
        configuration = self.output_selector.configuration
        selected = (configuration is not None and self.gen_ch.value()
                    in self.output_selector.allowed_channels(configuration))
        self.start_button.setEnabled(not running and selected)
        self.stop_button.setEnabled(running or selected)
        if message is not None:
            self.status.setText(message)
