"""Independent DAC11001 bias-output controls for the QICK RF board.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from math import isfinite
import threading
import traceback
from typing import Mapping, Optional, Sequence

from PyQt5 import QtCore, QtWidgets

try:
    from .bias_measurement import (
        BIAS_MEASUREMENT_KINDS,
        BiasMeasurementCancelled,
        default_bias_measurement_settings,
        normalize_bias_measurement_settings,
        ramp_bias_channels,
        run_bias_measurement,
    )
    from .bias_measurement_gui import BiasMeasurementPage, BiasMeasurementTabs
    from .qick_front_panel import (
        QickFrontPanelCanvas,
        QickFrontPanelConfiguration,
    )
    from .qick_qcodes_experiment import (
        QickConnectionConfig,
        connect_qick,
    )
except ImportError:
    from bias_measurement import (
        BIAS_MEASUREMENT_KINDS,
        BiasMeasurementCancelled,
        default_bias_measurement_settings,
        normalize_bias_measurement_settings,
        ramp_bias_channels,
        run_bias_measurement,
    )
    from bias_measurement_gui import BiasMeasurementPage, BiasMeasurementTabs
    from qick_front_panel import (
        QickFrontPanelCanvas,
        QickFrontPanelConfiguration,
    )
    from qick_qcodes_experiment import (
        QickConnectionConfig,
        connect_qick,
    )


BIAS_CHANNEL_COUNT = 8
BIAS_MIN_V = -10.0
BIAS_MAX_V = 10.0
BIAS_DEFAULT_V = 0.0
BIAS_DEFAULT_LIMIT_V = 10.0
BIAS_DEFAULT_RAMP_MAX_STEP_V = 0.001
BIAS_DEFAULT_RAMP_PAUSE_S = 0.01
BIAS_NAME_MAX_LENGTH = 32


class BiasChannelEditor(QtWidgets.QFrame):
    """One DAC11001 channel setpoint editor."""

    selected = QtCore.pyqtSignal(int)
    apply_requested = QtCore.pyqtSignal(int, float)
    name_changed = QtCore.pyqtSignal(int, str)

    def __init__(self, channel: int, parent=None):
        super().__init__(parent)
        self.channel = int(channel)
        self.setObjectName("biasChannelEditor")
        self.setProperty("selected", False)
        self.setMinimumWidth(178)
        self.setMaximumWidth(220)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setCursor(QtCore.Qt.PointingHandCursor)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(11, 9, 11, 9)
        layout.setSpacing(6)

        title_row = QtWidgets.QHBoxLayout()
        self.channel_label = QtWidgets.QLabel(f"BIAS{self.channel}")
        title_font = self.channel_label.font()
        title_font.setBold(True)
        self.channel_label.setFont(title_font)
        self.device_label = QtWidgets.QLabel("DAC11001")
        self.device_label.setStyleSheet("QLabel { color: #56616d; }")
        title_row.addWidget(self.channel_label)
        title_row.addStretch(1)
        title_row.addWidget(self.device_label)
        layout.addLayout(title_row)

        self.name_edit = QtWidgets.QLineEdit(self)
        self.name_edit.setPlaceholderText("Channel name (e.g. BL)")
        self.name_edit.setMaxLength(BIAS_NAME_MAX_LENGTH)
        self.name_edit.setClearButtonEnabled(True)
        layout.addWidget(self.name_edit)

        self.voltage = QtWidgets.QDoubleSpinBox(self)
        self.voltage.setRange(BIAS_MIN_V, BIAS_MAX_V)
        self.voltage.setDecimals(6)
        self.voltage.setSingleStep(0.001)
        self.voltage.setSuffix(" V")
        self.voltage.setValue(BIAS_DEFAULT_V)
        self.voltage.setKeyboardTracking(False)
        layout.addWidget(self.voltage)

        self.actual_label = QtWidgets.QLabel("Setpoint: not read")
        self.actual_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        layout.addWidget(self.actual_label)

        self.apply_button = QtWidgets.QPushButton("Apply", self)
        self.apply_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)
        )
        layout.addWidget(self.apply_button)

        self.apply_button.clicked.connect(self._apply)
        self.voltage.valueChanged.connect(
            lambda _value: self.selected.emit(self.channel)
        )
        self.name_edit.textEdited.connect(self._name_edited)
        self.name_edit.installEventFilter(self)
        self.voltage.installEventFilter(self)
        self.apply_button.installEventFilter(self)
        self._refresh_style()

    def eventFilter(self, watched, event) -> bool:
        if (
            watched in (self.name_edit, self.voltage, self.apply_button)
            and event.type() == QtCore.QEvent.MouseButtonPress
        ):
            self.selected.emit(self.channel)
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.selected.emit(self.channel)
        super().mousePressEvent(event)

    def _apply(self) -> None:
        self.selected.emit(self.channel)
        self.apply_requested.emit(self.channel, self.voltage.value())

    def _name_edited(self, text: str) -> None:
        self.selected.emit(self.channel)
        self.name_changed.emit(self.channel, str(text).strip())

    @property
    def channel_name(self) -> str:
        return self.name_edit.text().strip()

    def set_channel_name(self, name: str) -> None:
        name = str(name).strip()
        if len(name) > BIAS_NAME_MAX_LENGTH:
            raise ValueError(
                f"bias channel name must be at most {BIAS_NAME_MAX_LENGTH} characters"
            )
        with QtCore.QSignalBlocker(self.name_edit):
            self.name_edit.setText(name)

    def set_selected(self, selected: bool) -> None:
        selected = bool(selected)
        if bool(self.property("selected")) == selected:
            return
        self.setProperty("selected", selected)
        self._refresh_style()

    def _refresh_style(self) -> None:
        selected = bool(self.property("selected"))
        border_width = 4 if selected else 1
        border_color = "#1696b6" if selected else "#aeb7c2"
        background = "#eefbff" if selected else "#f7f9fb"
        self.setStyleSheet(
            "QFrame#biasChannelEditor {"
            f"border: {border_width}px solid {border_color};"
            "border-radius: 6px;"
            f"background: {background};"
            "}"
            "QFrame#biasChannelEditor QLabel, "
            "QFrame#biasChannelEditor QLineEdit, "
            "QFrame#biasChannelEditor QDoubleSpinBox, "
            "QFrame#biasChannelEditor QPushButton {"
            "border: none;"
            "background: transparent;"
            "}"
            "QFrame#biasChannelEditor QLineEdit, "
            "QFrame#biasChannelEditor QDoubleSpinBox {"
            "background: white;"
            "border: 1px solid #9ea8b3;"
            "padding: 3px;"
            "}"
            "QFrame#biasChannelEditor QPushButton {"
            "background: #e8edf2;"
            "border: 1px solid #9ea8b3;"
            "padding: 4px;"
            "}"
        )

    def set_actual_voltage(self, voltage: float) -> None:
        voltage = float(voltage)
        with QtCore.QSignalBlocker(self.voltage):
            self.voltage.setValue(voltage)
        self.actual_label.setText(f"Setpoint: {voltage:+.6f} V")

    def set_voltage_limit(self, voltage_limit_v: float) -> None:
        voltage_limit_v = float(voltage_limit_v)
        self.voltage.setRange(-voltage_limit_v, voltage_limit_v)

    def set_busy(self, busy: bool) -> None:
        self.name_edit.setEnabled(not busy)
        self.voltage.setEnabled(not busy)
        self.apply_button.setEnabled(not busy)


class BiasControlPanel(QtWidgets.QWidget):
    """Front-panel-centric editor for all eight QICK bias outputs."""

    read_requested = QtCore.pyqtSignal()
    set_requested = QtCore.pyqtSignal(int, float)
    set_all_requested = QtCore.pyqtSignal(object)
    measurement_requested = QtCore.pyqtSignal(str, object)
    measurement_stop_requested = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        self._configuration: Optional[QickFrontPanelConfiguration] = None
        self._selected_channel = 0
        self._busy = False

        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        self.bias_tabs = QtWidgets.QTabWidget(self)
        outer_layout.addWidget(self.bias_tabs)

        self.setpoint_page = QtWidgets.QWidget(self.bias_tabs)
        layout = QtWidgets.QVBoxLayout(self.setpoint_page)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("DAC11001 Bias Outputs")
        title_font = title.font()
        title_font.setBold(True)
        title.setFont(title_font)
        self.device_label = QtWidgets.QLabel(
            "8 channels | -10 V to +10 V | 20-bit"
        )
        self.read_button = QtWidgets.QPushButton("Read All Setpoints")
        self.read_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload)
        )
        self.apply_all_button = QtWidgets.QPushButton("Apply All")
        self.apply_all_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)
        )
        self.time_trace_button = QtWidgets.QPushButton("Current vs Time")
        self.time_trace_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon)
        )
        self.voltage_limit = QtWidgets.QDoubleSpinBox(self)
        self.voltage_limit.setRange(1.0e-6, BIAS_MAX_V)
        self.voltage_limit.setDecimals(6)
        self.voltage_limit.setSingleStep(0.1)
        self.voltage_limit.setSuffix(" V")
        self.voltage_limit.setValue(BIAS_DEFAULT_LIMIT_V)
        self.voltage_limit.setKeyboardTracking(False)
        self.voltage_limit.setToolTip(
            "Maximum allowed absolute value for every BIAS setpoint"
        )
        header.addWidget(title)
        header.addWidget(self.device_label)
        header.addStretch(1)
        header.addWidget(QtWidgets.QLabel("Voltage limit (+/-):"))
        header.addWidget(self.voltage_limit)
        header.addWidget(self.read_button)
        header.addWidget(self.apply_all_button)
        header.addWidget(self.time_trace_button)
        layout.addLayout(header)

        ramp_row = QtWidgets.QHBoxLayout()
        ramp_label = QtWidgets.QLabel("Setpoint ramp")
        ramp_font = ramp_label.font()
        ramp_font.setBold(True)
        ramp_label.setFont(ramp_font)
        self.ramp_max_step = QtWidgets.QDoubleSpinBox(self)
        self.ramp_max_step.setRange(1.0e-6, BIAS_MAX_V)
        self.ramp_max_step.setDecimals(6)
        self.ramp_max_step.setSingleStep(0.001)
        self.ramp_max_step.setSuffix(" V/step")
        self.ramp_max_step.setValue(BIAS_DEFAULT_RAMP_MAX_STEP_V)
        self.ramp_max_step.setKeyboardTracking(False)
        self.ramp_max_step.setToolTip(
            "Maximum voltage change written in each DAC11001 ramp step"
        )
        self.ramp_pause = QtWidgets.QDoubleSpinBox(self)
        self.ramp_pause.setRange(0.0, 60.0)
        self.ramp_pause.setDecimals(6)
        self.ramp_pause.setSingleStep(0.001)
        self.ramp_pause.setSuffix(" s/step")
        self.ramp_pause.setValue(BIAS_DEFAULT_RAMP_PAUSE_S)
        self.ramp_pause.setKeyboardTracking(False)
        self.ramp_pause.setToolTip(
            "Software wait inserted after each DAC11001 ramp step"
        )
        self.ramp_rate_label = QtWidgets.QLabel(self)
        ramp_row.addWidget(ramp_label)
        ramp_row.addWidget(QtWidgets.QLabel("Maximum step:"))
        ramp_row.addWidget(self.ramp_max_step)
        ramp_row.addWidget(QtWidgets.QLabel("Pause:"))
        ramp_row.addWidget(self.ramp_pause)
        ramp_row.addWidget(self.ramp_rate_label)
        ramp_row.addStretch(1)
        layout.addLayout(ramp_row)

        self.front_panel = QickFrontPanelCanvas(self)
        self.front_panel.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        self.front_panel.setMinimumHeight(220)
        self.front_panel.setMaximumHeight(360)
        self.front_panel.port_clicked.connect(self._front_panel_clicked)
        layout.addWidget(self.front_panel)

        self.editor_scroll = QtWidgets.QScrollArea(self)
        self.editor_scroll.setWidgetResizable(True)
        self.editor_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAsNeeded
        )
        self.editor_scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )
        self.editor_scroll.setMinimumHeight(150)
        editor_content = QtWidgets.QWidget(self.editor_scroll)
        editor_layout = QtWidgets.QHBoxLayout(editor_content)
        editor_layout.setContentsMargins(2, 2, 2, 2)
        editor_layout.setSpacing(7)
        self.editors = []
        for channel in range(BIAS_CHANNEL_COUNT):
            editor = BiasChannelEditor(channel, editor_content)
            editor.selected.connect(
                lambda channel: self.select_channel(channel, focus=False)
            )
            editor.apply_requested.connect(self.set_requested.emit)
            editor.name_changed.connect(self._channel_name_changed)
            self.editors.append(editor)
            editor_layout.addWidget(editor)
        editor_layout.addStretch(1)
        self.editor_scroll.setWidget(editor_content)
        layout.addWidget(self.editor_scroll)

        self.status = QtWidgets.QLabel(
            "Ready | selected BIAS0 | hardware setpoints not read"
        )
        self.status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.status.setStyleSheet(
            "QLabel { color: #20252b; background: #f3f6f8; "
            "border: 1px solid #aeb7c2; padding: 6px; }"
        )
        layout.addWidget(self.status)

        self.read_button.clicked.connect(self.read_requested.emit)
        self.apply_all_button.clicked.connect(self._apply_all)
        self.voltage_limit.valueChanged.connect(self.set_voltage_limit)
        self.ramp_max_step.valueChanged.connect(self._update_ramp_rate_label)
        self.ramp_pause.valueChanged.connect(self._update_ramp_rate_label)
        self._update_ramp_rate_label()
        self.select_channel(0, focus=False)

        self.bias_tabs.addTab(self.setpoint_page, "Setpoints")
        eager_measurements = tuple(
            kind for kind in BIAS_MEASUREMENT_KINDS if kind != "time_trace"
        )
        self.measurements = BiasMeasurementTabs(self, kinds=eager_measurements)
        self._time_trace_settings = default_bias_measurement_settings()[
            "time_trace"
        ]
        for kind in eager_measurements:
            page = self.measurements.pages[kind]
            self.measurements.removeTab(self.measurements.indexOf(page))
            self.bias_tabs.addTab(page, page.LABELS[kind])
        self.measurements.hide()
        self._time_trace_dialog = None
        self.time_trace_button.clicked.connect(self._show_time_trace_dialog)
        self.measurements.run_requested.connect(self.measurement_requested.emit)
        self.measurements.stop_requested.connect(
            self.measurement_stop_requested.emit
        )
        self.measurements.set_channel_names(
            [editor.channel_name for editor in self.editors]
        )

    def _show_time_trace_dialog(self) -> None:
        """Open the independent current-versus-time acquisition controls."""
        if self._time_trace_dialog is not None:
            self._time_trace_dialog.show()
            self._time_trace_dialog.raise_()
            self._time_trace_dialog.activateWindow()
            return
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Bias Current vs Time")
        dialog.resize(760, 820)
        dialog_layout = QtWidgets.QVBoxLayout(dialog)
        page = BiasMeasurementPage("time_trace", dialog)
        page.set_channel_names(
            [editor.channel_name for editor in self.editors]
        )
        page.load_settings(self._time_trace_settings)
        page.run_requested.connect(self.measurement_requested.emit)
        page.stop_requested.connect(self.measurement_stop_requested.emit)
        self.measurements.pages["time_trace"] = page
        dialog_layout.addWidget(page)
        dialog.finished.connect(dialog.hide)
        self._time_trace_dialog = dialog
        dialog.show()

    def prepare_for_settings_load(self) -> None:
        """Close the lazy Time Trace window before rebuilding GUI settings."""
        if self._time_trace_dialog is None:
            return
        dialog = self._time_trace_dialog
        dialog.hide()
        page = self.measurements.pages.pop("time_trace", None)
        if page is not None:
            self._time_trace_settings = page.settings_dict()
            page._finish_live_plot()
            page.setParent(None)
            page.deleteLater()
        dialog.deleteLater()
        self._time_trace_dialog = None
        QtWidgets.QApplication.sendPostedEvents(
            None,
            QtCore.QEvent.DeferredDelete,
        )

    @property
    def selected_channel(self) -> int:
        return self._selected_channel

    @property
    def voltage_limit_v(self) -> float:
        return float(self.voltage_limit.value())

    @property
    def ramp_max_step_v(self) -> float:
        return float(self.ramp_max_step.value())

    @property
    def ramp_pause_s(self) -> float:
        return float(self.ramp_pause.value())

    def _update_ramp_rate_label(self, *_args) -> None:
        if self.ramp_pause_s > 0.0:
            rate = self.ramp_max_step_v / self.ramp_pause_s
            self.ramp_rate_label.setText(f"Maximum nominal rate: {rate:g} V/s")
        else:
            self.ramp_rate_label.setText("No programmed step pause")

    def set_configuration(
        self,
        configuration: QickFrontPanelConfiguration,
    ) -> None:
        self._configuration = configuration
        self.front_panel.set_configuration(configuration)
        self.device_label.setText(
            f"{configuration.board} | 8 DAC11001 channels | "
            f"limit +/-{self.voltage_limit_v:g} V"
        )

    @QtCore.pyqtSlot(float)
    def set_voltage_limit(self, voltage_limit_v: float) -> None:
        voltage_limit_v = float(voltage_limit_v)
        if not 0.0 < voltage_limit_v <= BIAS_MAX_V:
            raise ValueError(
                f"bias voltage limit must be in (0, {BIAS_MAX_V:g}] V"
            )
        with QtCore.QSignalBlocker(self.voltage_limit):
            self.voltage_limit.setValue(voltage_limit_v)
        for editor in self.editors:
            editor.set_voltage_limit(voltage_limit_v)
        if self._configuration is not None:
            self.device_label.setText(
                f"{self._configuration.board} | 8 DAC11001 channels | "
                f"limit +/-{voltage_limit_v:g} V"
            )
        self.status.setText(
            f"Voltage limit +/-{voltage_limit_v:g} V | "
            f"selected BIAS{self._selected_channel}"
        )

    def _front_panel_clicked(self, direction: str, channel: int) -> None:
        if direction == "bias":
            self.select_channel(channel)

    def channel_description(self, channel: int) -> str:
        channel = int(channel)
        if not 0 <= channel < BIAS_CHANNEL_COUNT:
            raise IndexError("bias channel must be between 0 and 7")
        name = self.editors[channel].channel_name
        return f"BIAS{channel} ({name})" if name else f"BIAS{channel}"

    @QtCore.pyqtSlot(int, str)
    def _channel_name_changed(self, channel: int, _name: str) -> None:
        self.measurements.set_channel_names(
            [editor.channel_name for editor in self.editors]
        )
        if int(channel) == self._selected_channel:
            selected = self.editors[self._selected_channel]
            self.status.setText(
                f"Ready | selected {self.channel_description(channel)} | "
                f"requested {selected.voltage.value():+.6f} V"
            )

    @QtCore.pyqtSlot(int)
    def select_channel(self, channel: int, *, focus: bool = True) -> None:
        channel = int(channel)
        if not 0 <= channel < BIAS_CHANNEL_COUNT:
            raise IndexError("bias channel must be between 0 and 7")
        self._selected_channel = channel
        self.front_panel.set_selected("bias", channel)
        for index, editor in enumerate(self.editors):
            editor.set_selected(index == channel)
        selected = self.editors[channel]
        if channel == 0:
            self.editor_scroll.horizontalScrollBar().setValue(0)
        else:
            self.editor_scroll.ensureWidgetVisible(selected, 20, 10)
        if focus:
            selected.voltage.setFocus(QtCore.Qt.MouseFocusReason)
        self.status.setText(
            f"Ready | selected {self.channel_description(channel)} | "
            f"requested {selected.voltage.value():+.6f} V"
        )

    def _apply_all(self) -> None:
        values = tuple(editor.voltage.value() for editor in self.editors)
        self.set_all_requested.emit(values)

    def set_busy(self, busy: bool, message: str) -> None:
        self._busy = bool(busy)
        scrollbar = self.editor_scroll.horizontalScrollBar()
        scroll_position = scrollbar.value()
        focus_widget = QtWidgets.QApplication.focusWidget()
        if (
            focus_widget is not None
            and self.editor_scroll.isAncestorOf(focus_widget)
        ):
            # Disabling the focused Apply button otherwise advances focus through
            # every channel editor and scrolls the viewport to the final channel.
            focus_widget.clearFocus()
        self.read_button.setEnabled(not busy)
        self.apply_all_button.setEnabled(not busy)
        self.voltage_limit.setEnabled(not busy)
        self.ramp_max_step.setEnabled(not busy)
        self.ramp_pause.setEnabled(not busy)
        for editor in self.editors:
            editor.set_busy(busy)
        for page in self.measurements.pages.values():
            page.setEnabled(not busy)
        scrollbar.setValue(scroll_position)
        self.status.setText(str(message))

    def set_measurement_running(
        self,
        kind: str,
        running: bool,
        message: str,
    ) -> None:
        """Update the selected measurement page without disabling its status."""
        self.measurements.set_running(kind, running, message)
        self.read_button.setEnabled(not running)
        self.apply_all_button.setEnabled(not running)
        self.voltage_limit.setEnabled(not running)
        self.ramp_max_step.setEnabled(not running)
        self.ramp_pause.setEnabled(not running)
        for editor in self.editors:
            editor.set_busy(running)

    def update_measurement_progress(
        self,
        kind: str,
        percent: int,
        message: str,
    ) -> None:
        self.measurements.update_progress(kind, percent, message)

    def set_measurement_stopping(self, kind: str, message: str) -> None:
        self.measurements.set_stopping(kind, message)

    @QtCore.pyqtSlot(object)
    def begin_measurement_live_plot(self, layout) -> None:
        self.measurements.begin_live_plot(layout)

    @QtCore.pyqtSlot(object)
    def update_measurement_live_point(self, point) -> None:
        self.measurements.update_live_point(point)

    def show_measurement_result(self, result) -> None:
        self.measurements.show_result(result)
        self.read_button.setEnabled(True)
        self.apply_all_button.setEnabled(True)
        self.voltage_limit.setEnabled(True)
        self.ramp_max_step.setEnabled(True)
        self.ramp_pause.setEnabled(True)
        for editor in self.editors:
            editor.set_busy(False)

    def apply_hardware_values(self, values: Mapping[int, float]) -> None:
        for channel, voltage in values.items():
            channel = int(channel)
            if 0 <= channel < len(self.editors):
                self.editors[channel].set_actual_voltage(float(voltage))
        selected_voltage = self.editors[
            self._selected_channel
        ].voltage.value()
        self.status.setText(
            f"Updated {len(values)} channel(s) | selected "
            f"{self.channel_description(self._selected_channel)} = "
            f"{selected_voltage:+.6f} V"
        )

    def settings_dict(self) -> dict:
        measurements = self.measurements.settings_dict()
        measurements.setdefault(
            "time_trace",
            dict(self._time_trace_settings),
        )
        return {
            "selected_channel": self._selected_channel,
            "voltage_limit_v": self.voltage_limit_v,
            "ramp_max_step_v": self.ramp_max_step_v,
            "ramp_pause_s": self.ramp_pause_s,
            "channel_names": [editor.channel_name for editor in self.editors],
            "setpoints_v": [
                editor.voltage.value() for editor in self.editors
            ],
            "measurements": measurements,
        }

    def load_settings(self, settings: Mapping[str, object]) -> None:
        voltage_limit_v = float(
            settings.get("voltage_limit_v", BIAS_DEFAULT_LIMIT_V)
        )
        if not 0.0 < voltage_limit_v <= BIAS_MAX_V:
            raise ValueError(
                f"bias voltage_limit_v must be in (0, {BIAS_MAX_V:g}] V"
            )
        ramp_max_step_v = float(
            settings.get(
                "ramp_max_step_v",
                BIAS_DEFAULT_RAMP_MAX_STEP_V,
            )
        )
        ramp_pause_s = float(
            settings.get("ramp_pause_s", BIAS_DEFAULT_RAMP_PAUSE_S)
        )
        if not isfinite(ramp_max_step_v) or ramp_max_step_v <= 0.0:
            raise ValueError("bias ramp_max_step_v must be finite and positive")
        if not isfinite(ramp_pause_s) or ramp_pause_s < 0.0:
            raise ValueError("bias ramp_pause_s must be finite and nonnegative")
        names = settings.get("channel_names", [""] * BIAS_CHANNEL_COUNT)
        if (
            not isinstance(names, Sequence)
            or isinstance(names, (str, bytes))
            or len(names) != BIAS_CHANNEL_COUNT
        ):
            raise ValueError("bias channel_names must contain eight names")
        parsed_names = []
        for channel, name in enumerate(names):
            if not isinstance(name, str):
                raise TypeError(f"BIAS{channel} channel name must be a string")
            name = name.strip()
            if len(name) > BIAS_NAME_MAX_LENGTH:
                raise ValueError(
                    f"BIAS{channel} channel name must be at most "
                    f"{BIAS_NAME_MAX_LENGTH} characters"
                )
            parsed_names.append(name)
        values = settings.get(
            "setpoints_v",
            [BIAS_DEFAULT_V] * BIAS_CHANNEL_COUNT,
        )
        if (
            not isinstance(values, Sequence)
            or isinstance(values, (str, bytes))
            or len(values) != BIAS_CHANNEL_COUNT
        ):
            raise ValueError("bias setpoints_v must contain eight values")
        parsed_values = []
        for editor, value in zip(self.editors, values):
            value = float(value)
            if abs(value) > voltage_limit_v:
                raise ValueError(
                    "bias setpoint absolute values must not exceed "
                    f"voltage_limit_v ({voltage_limit_v:g} V)"
                )
            parsed_values.append((editor, value))
        self.set_voltage_limit(voltage_limit_v)
        self.ramp_max_step.setValue(ramp_max_step_v)
        self.ramp_pause.setValue(ramp_pause_s)
        for editor, name in zip(self.editors, parsed_names):
            editor.set_channel_name(name)
        for editor, value in parsed_values:
            with QtCore.QSignalBlocker(editor.voltage):
                editor.voltage.setValue(value)
        self.measurements.set_channel_names(parsed_names)
        measurement_settings = normalize_bias_measurement_settings(
            settings.get("measurements", {})
        )
        self._time_trace_settings = measurement_settings["time_trace"]
        self.measurements.load_settings(measurement_settings)
        self.select_channel(
            int(settings.get("selected_channel", 0)),
            focus=False,
        )


class BiasHardwareWorker(QtCore.QObject):
    """Read or update DAC11001 setpoints without blocking the Qt GUI."""

    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(
        self,
        connection_config: QickConnectionConfig,
        operation: str,
        values: Optional[Mapping[int, float]] = None,
        voltage_limit_v: float = BIAS_DEFAULT_LIMIT_V,
        ramp_max_step_v: float = BIAS_DEFAULT_RAMP_MAX_STEP_V,
        ramp_pause_s: float = BIAS_DEFAULT_RAMP_PAUSE_S,
        parent=None,
    ):
        super().__init__(parent)
        if operation not in {"read", "set"}:
            raise ValueError("bias operation must be read or set")
        self._connection_config = connection_config
        self._operation = operation
        self._voltage_limit_v = float(voltage_limit_v)
        if not 0.0 < self._voltage_limit_v <= BIAS_MAX_V:
            raise ValueError(
                f"bias voltage limit must be in (0, {BIAS_MAX_V:g}] V"
            )
        self._ramp_max_step_v = float(ramp_max_step_v)
        self._ramp_pause_s = float(ramp_pause_s)
        if not isfinite(self._ramp_max_step_v) or self._ramp_max_step_v <= 0.0:
            raise ValueError("bias ramp maximum step must be finite and positive")
        if not isfinite(self._ramp_pause_s) or self._ramp_pause_s < 0.0:
            raise ValueError("bias ramp pause must be finite and nonnegative")
        self._values = {
            int(channel): float(voltage)
            for channel, voltage in (values or {}).items()
        }
        for channel, voltage in self._values.items():
            if not 0 <= channel < BIAS_CHANNEL_COUNT:
                raise ValueError("bias channel must be between 0 and 7")
            if abs(voltage) > self._voltage_limit_v:
                raise ValueError(
                    f"BIAS{channel} setpoint {voltage:g} V exceeds "
                    f"the +/-{self._voltage_limit_v:g} V limit"
                )

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            soc, _soccfg = connect_qick(self._connection_config)
            if self._operation == "read":
                values = {
                    channel: float(soc.rfb_get_bias(channel))
                    for channel in range(BIAS_CHANNEL_COUNT)
                }
            else:
                values = ramp_bias_channels(
                    soc,
                    self._values,
                    max_step_v=self._ramp_max_step_v,
                    pause_s=self._ramp_pause_s,
                    voltage_limit_v=self._voltage_limit_v,
                )
        except Exception:
            self.failed.emit(traceback.format_exc())
            return
        self.finished.emit(values)


class BiasMeasurementWorker(QtCore.QObject):
    """Execute one Bias sweep and QCoDeS save outside the GUI thread."""

    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    cancelled = QtCore.pyqtSignal(str)
    progress_changed = QtCore.pyqtSignal(int, str)
    live_layout_ready = QtCore.pyqtSignal(object)
    live_point_ready = QtCore.pyqtSignal(object)

    def __init__(
        self,
        connection_config: QickConnectionConfig,
        kind: str,
        settings: Mapping[str, object],
        *,
        channel_names: Sequence[str],
        voltage_limit_v: float,
        parent=None,
    ):
        super().__init__(parent)
        self._connection_config = connection_config
        self._kind = str(kind)
        self._settings = dict(settings)
        self._channel_names = tuple(map(str, channel_names))
        self._voltage_limit_v = float(voltage_limit_v)
        self._cancel_event = threading.Event()

    def request_cancel(self) -> None:
        """Thread-safe cooperative stop request."""
        self._cancel_event.set()

    def _check_cancel(self) -> None:
        if self._cancel_event.is_set():
            raise BiasMeasurementCancelled("Bias measurement stopped by user")

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            result = run_bias_measurement(
                connection_config=self._connection_config,
                kind=self._kind,
                settings=self._settings,
                channel_names=self._channel_names,
                voltage_limit_v=self._voltage_limit_v,
                progress_callback=self.progress_changed.emit,
                live_layout_callback=self.live_layout_ready.emit,
                live_point_callback=self.live_point_ready.emit,
                cancel_check=self._check_cancel,
            )
        except BiasMeasurementCancelled as exc:
            self.cancelled.emit(str(exc))
            return
        except Exception:
            self.failed.emit(traceback.format_exc())
            return
        self.finished.emit(result)


__all__ = [
    "BIAS_CHANNEL_COUNT",
    "BIAS_DEFAULT_V",
    "BIAS_DEFAULT_LIMIT_V",
    "BIAS_DEFAULT_RAMP_MAX_STEP_V",
    "BIAS_DEFAULT_RAMP_PAUSE_S",
    "BIAS_MAX_V",
    "BIAS_MIN_V",
    "BIAS_NAME_MAX_LENGTH",
    "BiasChannelEditor",
    "BiasControlPanel",
    "BiasHardwareWorker",
    "BiasMeasurementWorker",
]
