"""Qt controls for dedicated and general nested Bias measurements.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
from PyQt5 import QtCore, QtWidgets

try:
    import pyqtgraph as pg
except ImportError:  # pragma: no cover - runtime dependency is documented
    pg = None

try:
    from .bias_measurement import (
        BIAS_MEASUREMENT_KINDS,
        SR860_CURRENT_SENSITIVITIES_A,
        SR860_TIME_CONSTANTS_S,
        BiasMeasurementLiveLayout,
        BiasMeasurementLivePoint,
        default_bias_measurement_settings,
        normalize_bias_measurement_settings,
    )
except ImportError:
    from bias_measurement import (
        BIAS_MEASUREMENT_KINDS,
        SR860_CURRENT_SENSITIVITIES_A,
        SR860_TIME_CONSTANTS_S,
        BiasMeasurementLiveLayout,
        BiasMeasurementLivePoint,
        default_bias_measurement_settings,
        normalize_bias_measurement_settings,
    )


LIVE_PLOT_REFRESH_MS = 75


def _double(
    minimum: float,
    maximum: float,
    value: float,
    *,
    decimals: int = 6,
    suffix: str = "",
    step: float = 0.001,
) -> QtWidgets.QDoubleSpinBox:
    widget = QtWidgets.QDoubleSpinBox()
    widget.setRange(float(minimum), float(maximum))
    widget.setDecimals(int(decimals))
    widget.setSingleStep(float(step))
    widget.setSuffix(str(suffix))
    widget.setValue(float(value))
    widget.setKeyboardTracking(False)
    return widget


def _integer(
    minimum: int,
    maximum: int,
    value: int,
    *,
    suffix: str = "",
) -> QtWidgets.QSpinBox:
    widget = QtWidgets.QSpinBox()
    widget.setRange(int(minimum), int(maximum))
    widget.setValue(int(value))
    widget.setSuffix(str(suffix))
    widget.setKeyboardTracking(False)
    return widget


def _engineering(value: float, unit: str) -> str:
    value = float(value)
    for scale, prefix in (
        (1e-12, "p"),
        (1e-9, "n"),
        (1e-6, "u"),
        (1e-3, "m"),
        (1.0, ""),
    ):
        if abs(value) < scale * 999.5 or scale == 1.0:
            return f"{value / scale:g} {prefix}{unit}"
    return f"{value:g} {unit}"


class CurrentMeasurementSettings(QtWidgets.QGroupBox):
    """Instrument settings shared by all Bias measurement types."""

    def __init__(self, *, two_point: bool, parent=None):
        super().__init__("Current Measurement", parent)
        self._two_point = bool(two_point)
        defaults = default_bias_measurement_settings()[
            "two_point" if two_point else "gate"
        ]
        layout = QtWidgets.QVBoxLayout(self)
        mode_row = QtWidgets.QFormLayout()
        self.mode = QtWidgets.QComboBox(self)
        self.mode.addItem("SR860 lock-in", "sr860")
        self.mode.addItem("QICK FIR-DDR ADC", "qick_adc")
        mode_row.addRow("Measure current with:", self.mode)
        layout.addLayout(mode_row)

        self.sr_group = QtWidgets.QGroupBox("SR860", self)
        sr = QtWidgets.QFormLayout(self.sr_group)
        self.sr_address = QtWidgets.QLineEdit(defaults["sr860"]["visa_address"])
        self.sr_frequency = _double(
            0.001, 500_000.0, defaults["sr860"]["frequency_hz"],
            decimals=6, suffix=" Hz", step=1.0,
        )
        self.sr_phase = _double(
            -360_000.0, 360_000.0, defaults["sr860"]["phase_deg"],
            decimals=4, suffix=" deg", step=1.0,
        )
        self.sr_bias = _double(
            0.0, 2.0, defaults["sr860"]["sine_bias_v"],
            decimals=9, suffix=" V", step=1e-6,
        )
        self.sr_time_constant = QtWidgets.QComboBox(self.sr_group)
        for value in SR860_TIME_CONSTANTS_S:
            self.sr_time_constant.addItem(_engineering(value, "s"), value)
        self.sr_time_constant.setCurrentIndex(
            self.sr_time_constant.findData(defaults["sr860"]["time_constant_s"])
        )
        self.sr_filter_slope = QtWidgets.QComboBox(self.sr_group)
        for value in (6, 12, 18, 24):
            self.sr_filter_slope.addItem(f"{value} dB/oct", value)
        self.sr_filter_slope.setCurrentIndex(
            self.sr_filter_slope.findData(defaults["sr860"]["filter_slope_db_oct"])
        )
        self.sr_sensitivity = QtWidgets.QComboBox(self.sr_group)
        for value in SR860_CURRENT_SENSITIVITIES_A:
            self.sr_sensitivity.addItem(_engineering(value, "A"), value)
        self.sr_sensitivity.setCurrentIndex(
            self.sr_sensitivity.findData(defaults["sr860"]["sensitivity_a"])
        )
        self.sr_settle_tc = _double(
            0.0, 100.0, defaults["sr860"]["settle_time_constants"],
            decimals=3, suffix=" x tau", step=0.5,
        )
        self.sr_input_gain = QtWidgets.QComboBox(self.sr_group)
        self.sr_input_gain.addItem("1 Mohm", 1e6)
        self.sr_input_gain.addItem("100 Mohm", 100e6)
        self.sr_input_gain.setCurrentIndex(
            self.sr_input_gain.findData(defaults["sr860"]["input_gain_ohm"])
        )
        sr.addRow("VISA resource:", self.sr_address)
        sr.addRow("Reference frequency:", self.sr_frequency)
        sr.addRow("Reference phase:", self.sr_phase)
        if not self._two_point:
            sr.addRow("Sine bias:", self.sr_bias)
        sr.addRow("Time constant:", self.sr_time_constant)
        sr.addRow("Filter slope:", self.sr_filter_slope)
        sr.addRow("Current sensitivity:", self.sr_sensitivity)
        sr.addRow("Current input gain:", self.sr_input_gain)
        sr.addRow("Settle before read:", self.sr_settle_tc)
        layout.addWidget(self.sr_group)

        self.adc_group = QtWidgets.QGroupBox("QICK FIR-DDR ADC", self)
        adc = QtWidgets.QFormLayout(self.adc_group)
        adc_defaults = defaults["qick_adc"]
        self.adc_ro_ch = _integer(0, 255, adc_defaults["readout_ch"])
        self.adc_board = QtWidgets.QComboBox(self.adc_group)
        self.adc_board.addItem("DC In", "DC_In")
        self.adc_board.addItem("RF In", "RF_In")
        self.adc_nqz = _integer(1, 2, adc_defaults["nqz"])
        self.adc_samples = _integer(1, 100_000_000, adc_defaults["fir_samples"])
        self.adc_frequency = _double(
            -10_000.0, 10_000.0, adc_defaults["readout_frequency_mhz"],
            decimals=9, suffix=" MHz", step=1.0,
        )
        self.adc_attenuation = _double(
            0.0, 31.75, adc_defaults["attenuation_db"],
            decimals=2, suffix=" dB", step=0.25,
        )
        self.adc_dc_gain = _double(
            -6.0, 26.0, adc_defaults["dc_gain_db"],
            decimals=2, suffix=" dB", step=1.0,
        )
        self.adc_filter = QtWidgets.QComboBox(self.adc_group)
        for value in ("bypass", "lowpass", "highpass", "bandpass"):
            self.adc_filter.addItem(value, value)
        self.adc_cutoff = _double(
            0.0, 20.0, adc_defaults["filter_cutoff_ghz"],
            decimals=6, suffix=" GHz", step=0.1,
        )
        self.adc_bandwidth = _double(
            1e-6, 20.0, adc_defaults["filter_bandwidth_ghz"],
            decimals=6, suffix=" GHz", step=0.1,
        )
        self.adc_margin = _integer(
            0, 1 << 30, adc_defaults["margin_input_samples"]
        )
        self.adc_read_delay = _double(
            0.0, 3600.0, adc_defaults["post_run_read_delay_seconds"],
            decimals=6, suffix=" s", step=0.01,
        )
        self.adc_units_per_amp = _double(
            -1e18, 1e18, adc_defaults["adc_units_per_amp"],
            decimals=9, suffix=" ADC/A", step=1.0,
        )
        adc.addRow("Readout channel:", self.adc_ro_ch)
        adc.addRow("Input board:", self.adc_board)
        adc.addRow("ADC Nyquist:", self.adc_nqz)
        adc.addRow("FIR samples / point:", self.adc_samples)
        adc.addRow("Readout/DDC frequency:", self.adc_frequency)
        adc.addRow("RF input ATT:", self.adc_attenuation)
        adc.addRow("DC input gain:", self.adc_dc_gain)
        adc.addRow("Input filter:", self.adc_filter)
        adc.addRow("Cutoff/center:", self.adc_cutoff)
        adc.addRow("Bandwidth:", self.adc_bandwidth)
        adc.addRow("FIR input margin:", self.adc_margin)
        adc.addRow("Read delay after trigger:", self.adc_read_delay)
        adc.addRow("Current conversion:", self.adc_units_per_amp)
        layout.addWidget(self.adc_group)
        self.mode.currentIndexChanged.connect(self._update_mode)
        self._update_mode()


    def _update_mode(self, *_args) -> None:
        adc = self.mode.currentData() == "qick_adc"
        self.adc_group.setVisible(adc)
        self.sr_group.setVisible(not adc)

    def settings_dict(self) -> dict:
        return {
            "current_mode": str(self.mode.currentData()),
            "sr860": {
                "visa_address": self.sr_address.text().strip(),
                "frequency_hz": self.sr_frequency.value(),
                "phase_deg": self.sr_phase.value(),
                "time_constant_s": float(self.sr_time_constant.currentData()),
                "filter_slope_db_oct": int(self.sr_filter_slope.currentData()),
                "sensitivity_a": float(self.sr_sensitivity.currentData()),
                "sine_bias_v": self.sr_bias.value(),
                "settle_time_constants": self.sr_settle_tc.value(),
                "input_gain_ohm": float(self.sr_input_gain.currentData()),
            },
            "qick_adc": {
                "readout_ch": self.adc_ro_ch.value(),
                "input_board_type": str(self.adc_board.currentData()),
                "nqz": self.adc_nqz.value(),
                "fir_samples": self.adc_samples.value(),
                "readout_frequency_mhz": self.adc_frequency.value(),
                "attenuation_db": self.adc_attenuation.value(),
                "dc_gain_db": self.adc_dc_gain.value(),
                "filter_type": str(self.adc_filter.currentData()),
                "filter_cutoff_ghz": self.adc_cutoff.value(),
                "filter_bandwidth_ghz": self.adc_bandwidth.value(),
                "margin_input_samples": self.adc_margin.value(),
                "fpga_trigger_delay_us": None,
                "post_run_read_delay_seconds": self.adc_read_delay.value(),
                "adc_units_per_amp": self.adc_units_per_amp.value(),
            },
        }

    def load_settings(self, settings: Mapping[str, object]) -> None:
        mode_index = self.mode.findData(str(settings["current_mode"]))
        if mode_index < 0:
            raise ValueError("saved Bias current mode is invalid")
        self.mode.setCurrentIndex(mode_index)
        sr = settings["sr860"]
        self.sr_address.setText(str(sr["visa_address"]))
        self.sr_frequency.setValue(float(sr["frequency_hz"]))
        self.sr_phase.setValue(float(sr["phase_deg"]))
        self.sr_bias.setValue(float(sr["sine_bias_v"]))
        self.sr_time_constant.setCurrentIndex(
            self.sr_time_constant.findData(float(sr["time_constant_s"]))
        )
        self.sr_filter_slope.setCurrentIndex(
            self.sr_filter_slope.findData(int(sr["filter_slope_db_oct"]))
        )
        self.sr_sensitivity.setCurrentIndex(
            self.sr_sensitivity.findData(float(sr["sensitivity_a"]))
        )
        self.sr_settle_tc.setValue(float(sr["settle_time_constants"]))
        self.sr_input_gain.setCurrentIndex(
            self.sr_input_gain.findData(float(sr["input_gain_ohm"]))
        )
        adc = settings["qick_adc"]
        self.adc_ro_ch.setValue(int(adc["readout_ch"]))
        self.adc_board.setCurrentIndex(
            self.adc_board.findData(str(adc["input_board_type"]))
        )
        self.adc_nqz.setValue(int(adc["nqz"]))
        self.adc_samples.setValue(int(adc["fir_samples"]))
        self.adc_frequency.setValue(float(adc["readout_frequency_mhz"]))
        self.adc_attenuation.setValue(float(adc["attenuation_db"]))
        self.adc_dc_gain.setValue(float(adc["dc_gain_db"]))
        self.adc_filter.setCurrentIndex(
            self.adc_filter.findData(str(adc["filter_type"]))
        )
        self.adc_cutoff.setValue(float(adc["filter_cutoff_ghz"]))
        self.adc_bandwidth.setValue(float(adc["filter_bandwidth_ghz"]))
        self.adc_margin.setValue(int(adc["margin_input_samples"]))
        self.adc_read_delay.setValue(float(adc["post_run_read_delay_seconds"]))
        self.adc_units_per_amp.setValue(float(adc["adc_units_per_amp"]))
        self._update_mode()


class NestedSweepChannelRow(QtWidgets.QWidget):
    """One independently editable channel inside a nested sweep axis."""

    remove_requested = QtCore.pyqtSignal(object)
    channel_changed = QtCore.pyqtSignal()

    def __init__(
        self,
        channel: int,
        start_v: float,
        stop_v: float,
        parent=None,
    ):
        super().__init__(parent)
        self._channel_names = [""] * 8
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        row.addWidget(QtWidgets.QLabel("Channel:", self))
        self.channel = QtWidgets.QComboBox(self)
        self.channel.setMinimumWidth(150)
        row.addWidget(self.channel, 2)

        row.addWidget(QtWidgets.QLabel("Start:", self))
        self.start_v = _double(
            -10.0, 10.0, float(start_v),
            decimals=9, suffix=" V", step=0.001,
        )
        self.start_v.setMinimumWidth(125)
        row.addWidget(self.start_v, 1)

        row.addWidget(QtWidgets.QLabel("Stop:", self))
        self.stop_v = _double(
            -10.0, 10.0, float(stop_v),
            decimals=9, suffix=" V", step=0.001,
        )
        self.stop_v.setMinimumWidth(125)
        row.addWidget(self.stop_v, 1)

        self.remove_button = QtWidgets.QToolButton(self)
        self.remove_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_TrashIcon)
        )
        self.remove_button.setToolTip("Remove this channel from the axis")
        row.addWidget(self.remove_button)

        self.set_channel_names(self._channel_names)
        self.set_channel(channel)
        self.channel.currentIndexChanged.connect(
            lambda _index: self.channel_changed.emit()
        )
        self.remove_button.clicked.connect(
            lambda: self.remove_requested.emit(self)
        )

    @property
    def selected_channel(self) -> int:
        return int(self.channel.currentData())

    def set_channel(self, channel: int) -> None:
        index = self.channel.findData(int(channel))
        if index < 0:
            raise ValueError("nested Bias channel must be between 0 and 7")
        self.channel.setCurrentIndex(index)

    def set_channel_names(self, names: Sequence[str]) -> None:
        if len(names) != 8:
            raise ValueError("Bias channel names must contain eight entries")
        selected = self.channel.currentData()
        self._channel_names = list(map(str, names))
        with QtCore.QSignalBlocker(self.channel):
            self.channel.clear()
            for channel, raw_name in enumerate(self._channel_names):
                name = raw_name.strip()
                label = (
                    f"{name} (BIAS{channel})" if name else f"BIAS{channel}"
                )
                self.channel.addItem(label, channel)
            index = self.channel.findData(selected)
            self.channel.setCurrentIndex(max(0, index))

    def set_removable(self, removable: bool) -> None:
        self.remove_button.setEnabled(bool(removable))


class NestedAxisEditor(QtWidgets.QGroupBox):
    """Edit one outer-to-inner vector sweep axis."""

    remove_requested = QtCore.pyqtSignal(object)
    move_requested = QtCore.pyqtSignal(object, int)

    def __init__(self, axis: Mapping[str, object], parent=None):
        super().__init__(parent)
        self._channel_names = [""] * 8
        self.channel_rows = []
        layout = QtWidgets.QVBoxLayout(self)

        header = QtWidgets.QHBoxLayout()
        self.order_label = QtWidgets.QLabel(self)
        header.addWidget(self.order_label)
        header.addStretch(1)
        self.move_up = QtWidgets.QToolButton(self)
        self.move_up.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_ArrowUp)
        )
        self.move_up.setToolTip("Move this axis outward (slower)")
        self.move_down = QtWidgets.QToolButton(self)
        self.move_down.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_ArrowDown)
        )
        self.move_down.setToolTip("Move this axis inward (faster)")
        self.remove_button = QtWidgets.QToolButton(self)
        self.remove_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_TrashIcon)
        )
        self.remove_button.setToolTip("Remove this nested axis")
        header.addWidget(self.move_up)
        header.addWidget(self.move_down)
        header.addWidget(self.remove_button)
        layout.addLayout(header)

        form = QtWidgets.QFormLayout()
        self.name = QtWidgets.QLineEdit(self)
        self.points = _integer(2, 1_000_000, 11)
        form.addRow("Axis name:", self.name)
        form.addRow("Points:", self.points)
        layout.addLayout(form)

        self.channel_rows_layout = QtWidgets.QVBoxLayout()
        self.channel_rows_layout.setSpacing(5)
        layout.addLayout(self.channel_rows_layout)

        self.add_channel_button = QtWidgets.QPushButton(
            "Add sweep channel", self
        )
        self.add_channel_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogNewFolder)
        )
        self.add_channel_button.clicked.connect(self._add_channel_row)
        layout.addWidget(self.add_channel_button)

        self.channel_summary = QtWidgets.QLabel(self)
        self.channel_summary.setWordWrap(True)
        layout.addWidget(self.channel_summary)

        self.move_up.clicked.connect(
            lambda: self.move_requested.emit(self, -1)
        )
        self.move_down.clicked.connect(
            lambda: self.move_requested.emit(self, 1)
        )
        self.remove_button.clicked.connect(
            lambda: self.remove_requested.emit(self)
        )
        self.load_settings(axis)

    def set_order(self, index: int, count: int) -> None:
        if index == 0:
            role = "outermost / slowest"
        elif index == count - 1:
            role = "innermost / fastest"
        else:
            role = "nested"
        self.setTitle(f"Axis {index + 1}: {role}")
        self.order_label.setText(
            "All channels below move together, each with its own voltage range."
        )
        self.move_up.setEnabled(index > 0)
        self.move_down.setEnabled(index < count - 1)
        self.remove_button.setEnabled(count > 1)

    def set_channel_names(self, names: Sequence[str]) -> None:
        if len(names) != 8:
            raise ValueError("Bias channel names must contain eight entries")
        self._channel_names = list(map(str, names))
        for row in self.channel_rows:
            row.set_channel_names(self._channel_names)
        self._update_channel_summary()

    def _next_unused_channel(self) -> int:
        used = {row.selected_channel for row in self.channel_rows}
        return next(
            (channel for channel in range(8) if channel not in used),
            0,
        )

    def _add_channel_row(
        self,
        _checked: bool = False,
        *,
        channel: int | None = None,
        start_v: float = 0.0,
        stop_v: float = 0.0,
    ) -> None:
        if len(self.channel_rows) >= 8:
            return
        if channel is None:
            channel = self._next_unused_channel()
        row = NestedSweepChannelRow(
            channel, start_v, stop_v, parent=self
        )
        row.set_channel_names(self._channel_names)
        row.channel_changed.connect(self._update_channel_summary)
        row.remove_requested.connect(self._remove_channel_row)
        self.channel_rows.append(row)
        self.channel_rows_layout.addWidget(row)
        self._refresh_channel_rows()

    def _remove_channel_row(self, row: NestedSweepChannelRow) -> None:
        if len(self.channel_rows) <= 1 or row not in self.channel_rows:
            return
        self.channel_rows.remove(row)
        self.channel_rows_layout.removeWidget(row)
        row.deleteLater()
        self._refresh_channel_rows()

    def _clear_channel_rows(self) -> None:
        for row in self.channel_rows:
            self.channel_rows_layout.removeWidget(row)
            row.deleteLater()
        self.channel_rows = []

    def _refresh_channel_rows(self) -> None:
        removable = len(self.channel_rows) > 1
        for row in self.channel_rows:
            row.set_removable(removable)
        self.add_channel_button.setEnabled(len(self.channel_rows) < 8)
        self._update_channel_summary()

    def _update_channel_summary(self, *_args) -> None:
        labels = []
        for row in self.channel_rows:
            channel = row.selected_channel
            name = self._channel_names[channel].strip()
            labels.append(
                f"{name} (BIAS{channel})" if name else f"BIAS{channel}"
            )
        self.channel_summary.setText("Vector: " + " + ".join(labels))

    def settings_dict(self) -> dict:
        return {
            "name": self.name.text().strip(),
            "channels": [row.selected_channel for row in self.channel_rows],
            "start_v": [row.start_v.value() for row in self.channel_rows],
            "stop_v": [row.stop_v.value() for row in self.channel_rows],
            "points": self.points.value(),
        }

    def load_settings(self, axis: Mapping[str, object]) -> None:
        channels = list(axis["channels"])
        start_v = list(axis["start_v"])
        stop_v = list(axis["stop_v"])
        if not channels or not (
            len(channels) == len(start_v) == len(stop_v)
        ):
            raise ValueError(
                "nested axis channels, start_v, and stop_v must have "
                "the same nonzero length"
            )
        self.name.setText(str(axis["name"]))
        self.points.setValue(int(axis["points"]))
        self._clear_channel_rows()
        for channel, start, stop in zip(channels, start_v, stop_v):
            self._add_channel_row(
                channel=int(channel),
                start_v=float(start),
                stop_v=float(stop),
            )
        self._refresh_channel_rows()


class BiasMeasurementPage(QtWidgets.QWidget):
    """One fully independent Bias measurement configuration page."""

    run_requested = QtCore.pyqtSignal(str, object)
    stop_requested = QtCore.pyqtSignal(str)

    LABELS = {
        "two_point": "2P Sweep",
        "gate": "Gate-Controlled Sweep",
        "wall_wall": "Wall-Wall Plot",
        "nested": "Nested Sweep",
        "time_trace": "Time Trace",
    }

    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self.kind = str(kind)
        defaults = default_bias_measurement_settings()[self.kind]
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget(scroll)
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(6, 6, 6, 6)
        self._content = content
        self._content_layout = layout

        self._channel_names = [""] * 8
        self.channel_combos = []
        self.nested_axis_editors = []
        self._live_layout = None
        self._live_sum = None
        self._live_count = None
        self._live_values = None
        self._live_curve = None
        self._live_image = None
        self._live_dirty = False
        self._live_completed_reads = 0
        self._live_total_reads = 0
        self._live_timer = QtCore.QTimer(self)
        self._live_timer.setInterval(LIVE_PLOT_REFRESH_MS)
        self._live_timer.timeout.connect(self._flush_live_plot)
        sweep_group = QtWidgets.QGroupBox(self.LABELS[self.kind], content)
        if self.kind == "nested":
            nested_layout = QtWidgets.QVBoxLayout(sweep_group)
            description = QtWidgets.QLabel(
                "Axes run from top (outermost/slowest) to bottom "
                "(innermost/fastest). Each axis can move one or more "
                "BIAS channels together between voltage vectors.",
                sweep_group,
            )
            description.setWordWrap(True)
            nested_layout.addWidget(description)
            self.nested_axes_layout = QtWidgets.QVBoxLayout()
            nested_layout.addLayout(self.nested_axes_layout)
            self.nested_total = QtWidgets.QLabel(sweep_group)
            self.nested_total.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse
            )
            nested_layout.addWidget(self.nested_total)
            self.add_nested_axis_button = QtWidgets.QPushButton(
                "Add nested axis", sweep_group
            )
            self.add_nested_axis_button.setIcon(
                self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogNewFolder)
            )
            self.add_nested_axis_button.clicked.connect(
                lambda: self._add_nested_axis()
            )
            nested_layout.addWidget(self.add_nested_axis_button)
            for axis in defaults["axes"]:
                self._add_nested_axis(axis)
        else:
            form = QtWidgets.QFormLayout(sweep_group)
        if self.kind == "two_point":
            self.bias_start_uv = _double(
                0.0, 2e6, defaults["bias_start_v"] * 1e6,
                decimals=6, suffix=" uV", step=1.0,
            )
            self.bias_stop_uv = _double(
                0.0, 2e6, defaults["bias_stop_v"] * 1e6,
                decimals=6, suffix=" uV", step=1.0,
            )
            self.points = _integer(2, 1_000_000, defaults["points"])
            form.addRow("Sine bias start:", self.bias_start_uv)
            form.addRow("Sine bias stop:", self.bias_stop_uv)
            form.addRow("Points:", self.points)
        elif self.kind == "gate":
            self.gate_channels_widget = QtWidgets.QWidget(sweep_group)
            gate_channels_layout = QtWidgets.QGridLayout(
                self.gate_channels_widget
            )
            gate_channels_layout.setContentsMargins(0, 0, 0, 0)
            gate_channels_layout.setHorizontalSpacing(12)
            gate_channels_layout.setVerticalSpacing(4)
            self.gate_channel_checks = []
            for channel in range(8):
                checkbox = QtWidgets.QCheckBox(
                    f"BIAS{channel}", self.gate_channels_widget
                )
                checkbox.setProperty("bias_channel", channel)
                checkbox.setChecked(channel in defaults["gate_channels"])
                self.gate_channel_checks.append(checkbox)
                gate_channels_layout.addWidget(
                    checkbox, channel // 4, channel % 4
                )
            gate_channel_buttons = QtWidgets.QHBoxLayout()
            select_all = QtWidgets.QToolButton(self.gate_channels_widget)
            select_all.setText("Select all")
            clear_all = QtWidgets.QToolButton(self.gate_channels_widget)
            clear_all.setText("Clear")
            select_all.clicked.connect(
                lambda: self._set_all_gate_channels(True)
            )
            clear_all.clicked.connect(
                lambda: self._set_all_gate_channels(False)
            )
            gate_channel_buttons.addWidget(select_all)
            gate_channel_buttons.addWidget(clear_all)
            gate_channel_buttons.addStretch(1)
            gate_channels_layout.addLayout(gate_channel_buttons, 2, 0, 1, 4)
            self.gate_start = _double(-10.0, 10.0, defaults["gate_start_v"], suffix=" V")
            self.gate_stop = _double(-10.0, 10.0, defaults["gate_stop_v"], suffix=" V")
            self.points_per_leg = _integer(2, 1_000_000, defaults["points_per_leg"])
            self.loops = _integer(1, 100_000, defaults["loops"])
            self.return_leg = QtWidgets.QCheckBox("Include return leg", sweep_group)
            self.return_leg.setChecked(defaults["return_leg"])
            self.largest_first = QtWidgets.QCheckBox(
                "Largest loop first", sweep_group
            )
            self.largest_first.setChecked(defaults["largest_loop_first"])
            form.addRow("Gate BIAS channels:", self.gate_channels_widget)
            form.addRow("Start:", self.gate_start)
            form.addRow("Stop:", self.gate_stop)
            form.addRow("Points / leg:", self.points_per_leg)
            form.addRow("Nested loops:", self.loops)
            form.addRow(self.return_leg)
            form.addRow(self.largest_first)
        elif self.kind == "wall_wall":
            self.slow_channel = QtWidgets.QComboBox(sweep_group)
            self.fast_channel = QtWidgets.QComboBox(sweep_group)
            self.channel_combos.extend((self.slow_channel, self.fast_channel))
            self.slow_start = _double(-10.0, 10.0, defaults["slow_start_v"], suffix=" V")
            self.slow_stop = _double(-10.0, 10.0, defaults["slow_stop_v"], suffix=" V")
            self.slow_points = _integer(2, 100_000, defaults["slow_points"])
            self.fast_start = _double(-10.0, 10.0, defaults["fast_start_v"], suffix=" V")
            self.fast_stop = _double(-10.0, 10.0, defaults["fast_stop_v"], suffix=" V")
            self.fast_points = _integer(2, 100_000, defaults["fast_points"])
            form.addRow("Slow BIAS channel:", self.slow_channel)
            form.addRow("Slow start:", self.slow_start)
            form.addRow("Slow stop:", self.slow_stop)
            form.addRow("Slow points:", self.slow_points)
            form.addRow("Fast BIAS channel:", self.fast_channel)
            form.addRow("Fast start:", self.fast_start)
            form.addRow("Fast stop:", self.fast_stop)
            form.addRow("Fast points:", self.fast_points)
        elif self.kind == "time_trace":
            self.time_samples = _integer(
                1, 100_000_000, defaults["samples"]
            )
            self.time_interval = _double(
                0.0, 3600.0, defaults["sample_interval_s"],
                decimals=9, suffix=" s", step=0.01,
            )
            self.time_trace_summary = QtWidgets.QLabel(sweep_group)
            self.time_trace_summary.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse
            )
            self.time_samples.valueChanged.connect(
                self._update_time_trace_summary
            )
            self.time_interval.valueChanged.connect(
                self._update_time_trace_summary
            )
            form.addRow("Current samples:", self.time_samples)
            form.addRow("Requested interval:", self.time_interval)
            form.addRow("Requested span:", self.time_trace_summary)
            self._update_time_trace_summary()
        self.set_channel_names([""] * 8)
        if self.kind == "wall_wall":
            self.slow_channel.setCurrentIndex(
                self.slow_channel.findData(defaults["slow_channel"])
            )
            self.fast_channel.setCurrentIndex(
                self.fast_channel.findData(defaults["fast_channel"])
            )
        layout.addWidget(sweep_group)

        timing_group = QtWidgets.QGroupBox("Sweep Timing", content)
        timing = QtWidgets.QFormLayout(timing_group)
        self.repetitions = _integer(
            1, 1_000_000, defaults["repetitions_per_point"]
        )
        self.settle = _double(
            0.0, 3600.0, defaults["settle_s"],
            decimals=6, suffix=" s", step=0.01,
        )
        self.ramp_step = _double(
            1e-9, 20.0, defaults["ramp_max_step_v"],
            decimals=9, suffix=" V", step=0.001,
        )
        self.ramp_pause = _double(
            0.0, 60.0, defaults["ramp_pause_s"],
            decimals=6, suffix=" s", step=0.001,
        )
        self.restore = QtWidgets.QCheckBox("Restore starting BIAS voltages", timing_group)
        self.restore.setChecked(defaults["restore_bias_after_run"])
        self.repetitions.valueChanged.connect(self._update_nested_total)
        timing.addRow("Repetitions / point:", self.repetitions)
        timing.addRow("Settle after BIAS move:", self.settle)
        timing.addRow("Maximum ramp step:", self.ramp_step)
        timing.addRow("Pause / ramp step:", self.ramp_pause)
        if self.kind == "gate":
            self.restore.hide()
            final_voltage_note = QtWidgets.QLabel(
                "Keep the final measured sweep voltage. An enabled return "
                "leg ends at the configured start voltage.",
                timing_group,
            )
            final_voltage_note.setWordWrap(True)
            timing.addRow("After sweep:", final_voltage_note)
        else:
            timing.addRow(self.restore)
        layout.addWidget(timing_group)
        if self.kind == "time_trace":
            timing_group.hide()

        self.current = CurrentMeasurementSettings(
            two_point=self.kind == "two_point", parent=content
        )
        layout.addWidget(self.current)

        storage_group = QtWidgets.QGroupBox("QCoDeS Storage", content)
        storage = QtWidgets.QFormLayout(storage_group)
        self.database_path = QtWidgets.QLineEdit(defaults["database_path"])
        browse = QtWidgets.QToolButton(storage_group)
        browse.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton))
        browse.clicked.connect(self._browse_database)
        database_row = QtWidgets.QHBoxLayout()
        database_row.addWidget(self.database_path, 1)
        database_row.addWidget(browse)
        self.experiment_name = QtWidgets.QLineEdit(defaults["experiment_name"])
        self.sample_name = QtWidgets.QLineEdit(defaults["sample_name"])
        self.notes = QtWidgets.QPlainTextEdit(defaults["notes"])
        self.notes.setMaximumHeight(70)
        storage.addRow("Database:", database_row)
        storage.addRow("Experiment:", self.experiment_name)
        storage.addRow("Sample:", self.sample_name)
        storage.addRow("Notes:", self.notes)
        layout.addWidget(storage_group)

        self.run_button = QtWidgets.QPushButton(
            f"Run {self.LABELS[self.kind]}", content
        )
        self.run_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.run_button.clicked.connect(self._run)
        self.stop_button = QtWidgets.QPushButton("Stop", content)
        self.stop_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_MediaStop)
        )
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(
            lambda: self.stop_requested.emit(self.kind)
        )
        run_row = QtWidgets.QHBoxLayout()
        run_row.addWidget(self.run_button, 1)
        run_row.addWidget(self.stop_button)
        layout.addLayout(run_row)
        self.progress = QtWidgets.QProgressBar(content)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.status = QtWidgets.QLabel("Ready", content)
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.status)

        self.plot = None
        layout.addStretch(1)
        if pg is not None and self.kind != "time_trace":
            self._ensure_plot()
        scroll.setWidget(content)
        root.addWidget(scroll)
        self._update_nested_total()

    def _default_nested_axis(self) -> dict:
        used = {
            channel
            for editor in self.nested_axis_editors
            for channel in editor.settings_dict().get("channels", [])
        }
        channel = next(
            (candidate for candidate in range(8) if candidate not in used),
            0,
        )
        return {
            "name": f"axis_{len(self.nested_axis_editors)}",
            "channels": [channel],
            "start_v": [0.0],
            "stop_v": [0.1],
            "points": 11,
        }

    def _add_nested_axis(
        self,
        axis: Mapping[str, object] | None = None,
    ) -> None:
        if len(self.nested_axis_editors) >= 8:
            return
        if axis is None:
            try:
                axis = self._default_nested_axis()
            except ValueError:
                axis = {
                    "name": f"axis_{len(self.nested_axis_editors)}",
                    "channels": [0],
                    "start_v": [0.0],
                    "stop_v": [0.1],
                    "points": 11,
                }
        editor = NestedAxisEditor(axis, self)
        editor.set_channel_names(self._channel_names)
        editor.remove_requested.connect(self._remove_nested_axis)
        editor.move_requested.connect(self._move_nested_axis)
        editor.points.valueChanged.connect(self._update_nested_total)
        self.nested_axis_editors.append(editor)
        self.nested_axes_layout.addWidget(editor)
        self._refresh_nested_axes()

    def _remove_nested_axis(self, editor: NestedAxisEditor) -> None:
        if len(self.nested_axis_editors) <= 1:
            return
        self.nested_axis_editors.remove(editor)
        self.nested_axes_layout.removeWidget(editor)
        editor.deleteLater()
        self._refresh_nested_axes()

    def _move_nested_axis(
        self,
        editor: NestedAxisEditor,
        direction: int,
    ) -> None:
        index = self.nested_axis_editors.index(editor)
        target = index + int(direction)
        if not 0 <= target < len(self.nested_axis_editors):
            return
        self.nested_axis_editors[index], self.nested_axis_editors[target] = (
            self.nested_axis_editors[target],
            self.nested_axis_editors[index],
        )
        self._refresh_nested_axes()

    def _refresh_nested_axes(self) -> None:
        if self.kind != "nested":
            return
        for editor in self.nested_axis_editors:
            self.nested_axes_layout.removeWidget(editor)
        count = len(self.nested_axis_editors)
        for index, editor in enumerate(self.nested_axis_editors):
            self.nested_axes_layout.addWidget(editor)
            editor.set_order(index, count)
        self.add_nested_axis_button.setEnabled(count < 8)
        self._update_nested_total()

    def _update_nested_total(self, *_args) -> None:
        if self.kind != "nested" or not hasattr(self, "nested_total"):
            return
        total = 1
        for editor in self.nested_axis_editors:
            total *= editor.points.value()
        repetitions = (
            self.repetitions.value() if hasattr(self, "repetitions") else 1
        )
        self.nested_total.setText(
            f"Cartesian sweep: {total:,} points x {repetitions:,} "
            f"repetitions = {total * repetitions:,} current readings"
        )

    def set_channel_names(self, names: Sequence[str]) -> None:
        if len(names) != 8:
            raise ValueError("Bias channel names must contain eight entries")
        self._channel_names = list(map(str, names))
        if self.kind == "gate":
            for channel, checkbox in enumerate(self.gate_channel_checks):
                name = str(names[channel]).strip()
                checkbox.setText(
                    name if name else f"BIAS{channel}"
                )
                checkbox.setToolTip(
                    f"BIAS{channel}" + (f" | {name}" if name else "")
                )
        for combo in self.channel_combos:
            selected = combo.currentData()
            combo.clear()
            for channel, name in enumerate(names):
                label = f"BIAS{channel}"
                if str(name).strip():
                    label += f" ({str(name).strip()})"
                combo.addItem(label, channel)
            index = combo.findData(selected)
            combo.setCurrentIndex(max(0, index))
        for editor in self.nested_axis_editors:
            editor.set_channel_names(self._channel_names)

    def _set_all_gate_channels(self, checked: bool) -> None:
        if self.kind != "gate":
            return
        for checkbox in self.gate_channel_checks:
            checkbox.setChecked(bool(checked))

    def _update_time_trace_summary(self, *_args) -> None:
        if self.kind != "time_trace":
            return
        span_s = max(0, self.time_samples.value() - 1) * self.time_interval.value()
        if self.time_interval.value() == 0.0:
            self.time_trace_summary.setText(
                "As fast as the selected current reader permits"
            )
        else:
            self.time_trace_summary.setText(f"{span_s:g} s")

    def _browse_database(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Choose Bias measurement database",
            self.database_path.text().strip(),
            "QCoDeS SQLite database (*.db);;All files (*)",
        )
        if path:
            selected = Path(path)
            if selected.suffix.lower() != ".db":
                selected = selected.with_suffix(".db")
            self.database_path.setText(str(selected))

    def settings_dict(self) -> dict:
        result = {
            "database_path": self.database_path.text().strip(),
            "experiment_name": self.experiment_name.text().strip(),
            "sample_name": self.sample_name.text().strip(),
            "notes": self.notes.toPlainText(),
            "repetitions_per_point": self.repetitions.value(),
            "settle_s": self.settle.value(),
            "ramp_max_step_v": self.ramp_step.value(),
            "ramp_pause_s": self.ramp_pause.value(),
            "restore_bias_after_run": self.restore.isChecked(),
            **self.current.settings_dict(),
        }
        if self.kind == "two_point":
            result.update({
                "bias_start_v": self.bias_start_uv.value() / 1e6,
                "bias_stop_v": self.bias_stop_uv.value() / 1e6,
                "points": self.points.value(),
            })
        elif self.kind == "gate":
            result.update({
                "gate_channels": [
                    channel
                    for channel, checkbox in enumerate(self.gate_channel_checks)
                    if checkbox.isChecked()
                ],
                "gate_start_v": self.gate_start.value(),
                "gate_stop_v": self.gate_stop.value(),
                "points_per_leg": self.points_per_leg.value(),
                "loops": self.loops.value(),
                "return_leg": self.return_leg.isChecked(),
                "largest_loop_first": self.largest_first.isChecked(),
            })
        elif self.kind == "wall_wall":
            result.update({
                "slow_channel": int(self.slow_channel.currentData()),
                "fast_channel": int(self.fast_channel.currentData()),
                "slow_start_v": self.slow_start.value(),
                "slow_stop_v": self.slow_stop.value(),
                "slow_points": self.slow_points.value(),
                "fast_start_v": self.fast_start.value(),
                "fast_stop_v": self.fast_stop.value(),
                "fast_points": self.fast_points.value(),
            })
        elif self.kind == "nested":
            result["axes"] = [
                editor.settings_dict()
                for editor in self.nested_axis_editors
            ]
        else:
            result.update({
                "samples": self.time_samples.value(),
                "sample_interval_s": self.time_interval.value(),
            })
        return normalize_bias_measurement_settings({self.kind: result})[self.kind]

    def load_settings(self, settings: Mapping[str, object]) -> None:
        values = normalize_bias_measurement_settings({self.kind: settings})[self.kind]
        self.database_path.setText(values["database_path"])
        self.experiment_name.setText(values["experiment_name"])
        self.sample_name.setText(values["sample_name"])
        self.notes.setPlainText(values["notes"])
        self.repetitions.setValue(values["repetitions_per_point"])
        self.settle.setValue(values["settle_s"])
        self.ramp_step.setValue(values["ramp_max_step_v"])
        self.ramp_pause.setValue(values["ramp_pause_s"])
        self.restore.setChecked(values["restore_bias_after_run"])
        self.current.load_settings(values)
        if self.kind == "two_point":
            self.bias_start_uv.setValue(values["bias_start_v"] * 1e6)
            self.bias_stop_uv.setValue(values["bias_stop_v"] * 1e6)
            self.points.setValue(values["points"])
        elif self.kind == "gate":
            selected_channels = set(values["gate_channels"])
            for channel, checkbox in enumerate(self.gate_channel_checks):
                checkbox.setChecked(channel in selected_channels)
            self.gate_start.setValue(values["gate_start_v"])
            self.gate_stop.setValue(values["gate_stop_v"])
            self.points_per_leg.setValue(values["points_per_leg"])
            self.loops.setValue(values["loops"])
            self.return_leg.setChecked(values["return_leg"])
            self.largest_first.setChecked(values["largest_loop_first"])
        elif self.kind == "wall_wall":
            self.slow_channel.setCurrentIndex(
                self.slow_channel.findData(values["slow_channel"])
            )
            self.fast_channel.setCurrentIndex(
                self.fast_channel.findData(values["fast_channel"])
            )
            self.slow_start.setValue(values["slow_start_v"])
            self.slow_stop.setValue(values["slow_stop_v"])
            self.slow_points.setValue(values["slow_points"])
            self.fast_start.setValue(values["fast_start_v"])
            self.fast_stop.setValue(values["fast_stop_v"])
            self.fast_points.setValue(values["fast_points"])
        elif self.kind == "nested":
            for editor in tuple(self.nested_axis_editors):
                self.nested_axes_layout.removeWidget(editor)
                editor.deleteLater()
            self.nested_axis_editors.clear()
            for axis in values["axes"]:
                self._add_nested_axis(axis)
            self._refresh_nested_axes()
        else:
            self.time_samples.setValue(values["samples"])
            self.time_interval.setValue(values["sample_interval_s"])
            self._update_time_trace_summary()

    def _run(self) -> None:
        try:
            settings = self.settings_dict()
        except (TypeError, ValueError) as exc:
            QtWidgets.QMessageBox.warning(self, "Invalid Bias sweep", str(exc))
            return
        self.run_requested.emit(self.kind, settings)

    def _ensure_plot(self):
        """Create the pyqtgraph widget only when this page needs it."""
        if self.plot is not None or pg is None:
            return self.plot
        self.plot = pg.PlotWidget(self._content)
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        self.plot.setMinimumHeight(260)
        self._content_layout.insertWidget(
            max(0, self._content_layout.count() - 1),
            self.plot,
        )
        return self.plot

    def begin_live_plot(self, layout: BiasMeasurementLiveLayout) -> None:
        """Initialize an empty line or image for an active measurement."""
        if str(layout.kind) != self.kind:
            return
        shape = tuple(map(int, layout.data_shape))
        expected_shape = (
            (len(layout.x_values),)
            if layout.y_values is None
            else (len(layout.y_values), len(layout.x_values))
        )
        if shape != expected_shape or len(shape) not in {1, 2}:
            self.status.setText(
                f"Live plot shape {shape} does not match coordinates "
                f"{expected_shape}"
            )
            return

        self._live_layout = layout
        self._live_sum = np.zeros(shape, dtype=np.float64)
        self._live_count = np.zeros(shape, dtype=np.int64)
        self._live_values = np.full(shape, np.nan, dtype=np.float64)
        self._live_curve = None
        self._live_image = None
        self._live_dirty = False
        self._live_completed_reads = 0
        self._live_total_reads = 0
        if self._ensure_plot() is None:
            return

        self.plot.clear()
        self.plot.setTitle("Live current magnitude")
        if layout.y_values is None:
            self._live_curve = self.plot.plot(
                np.asarray(layout.x_values, dtype=np.float64),
                self._live_values,
                pen=pg.mkPen("#087f8c", width=2),
                symbol="o",
                symbolSize=5,
                symbolBrush="#087f8c",
                connect="finite",
            )
            self.plot.setLabel("bottom", layout.x_label)
            self.plot.setLabel("left", "Current magnitude", units="A")
        else:
            self._live_image = pg.ImageItem(axisOrder="row-major")
            self._live_image.setColorMap(pg.colormap.get("viridis"))
            x = np.asarray(layout.x_values, dtype=np.float64)
            y = np.asarray(layout.y_values, dtype=np.float64)
            self._live_image.setRect(QtCore.QRectF(
                float(x[0]),
                float(y[0]),
                float(x[-1] - x[0]),
                float(y[-1] - y[0]),
            ))
            self.plot.addItem(self._live_image)
            self.plot.setLabel("bottom", layout.x_label)
            self.plot.setLabel("left", layout.y_label)
        self._live_timer.start()

    def update_live_point(self, point: BiasMeasurementLivePoint) -> None:
        """Accumulate one reading and defer the visual redraw to the timer."""
        if self._live_layout is None or str(point.kind) != self.kind:
            return
        index = tuple(map(int, point.plot_index))
        if len(index) != len(self._live_values.shape):
            return
        if any(
            coordinate < 0 or coordinate >= extent
            for coordinate, extent in zip(index, self._live_values.shape)
        ):
            return
        magnitude = float(point.magnitude_a)
        if not np.isfinite(magnitude):
            return
        self._live_sum[index] += magnitude
        self._live_count[index] += 1
        self._live_values[index] = (
            self._live_sum[index] / self._live_count[index]
        )
        self._live_completed_reads = int(point.completed_reads)
        self._live_total_reads = int(point.total_reads)
        self._live_dirty = True

    def _flush_live_plot(self) -> None:
        if not self._live_dirty or self.plot is None:
            return
        if self._live_curve is not None:
            self._live_curve.setData(
                np.asarray(self._live_layout.x_values, dtype=np.float64),
                self._live_values,
                connect="finite",
            )
        elif self._live_image is not None:
            finite_values = self._live_values[
                np.isfinite(self._live_values)
            ]
            if finite_values.size:
                low = float(np.min(finite_values))
                high = float(np.max(finite_values))
                if low == high:
                    padding = max(abs(low) * 0.01, 1.0e-18)
                    low -= padding
                    high += padding
                self._live_image.setImage(
                    self._live_values,
                    autoLevels=False,
                    levels=(low, high),
                )
        self.plot.setTitle(
            "Live current magnitude | "
            f"{self._live_completed_reads:,}/{self._live_total_reads:,} reads"
        )
        self._live_dirty = False

    def _finish_live_plot(self) -> None:
        self._flush_live_plot()
        self._live_timer.stop()
        self._live_layout = None
        self._live_sum = None
        self._live_count = None
        self._live_values = None
        self._live_curve = None
        self._live_image = None
        self._live_dirty = False

    def set_running(self, running: bool, message: str) -> None:
        self.run_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.status.setText(str(message))
        if running:
            self.progress.setValue(0)
        else:
            self._finish_live_plot()

    def set_stopping(self, message: str) -> None:
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.status.setText(str(message))

    def update_progress(self, percent: int, message: str) -> None:
        self.progress.setValue(int(percent))
        self.status.setText(str(message))

    def show_result(self, result) -> None:
        self.set_running(
            False,
            f"QCoDeS Run {result.run_id} saved to {result.database_path}",
        )
        self.progress.setValue(100)
        if self._ensure_plot() is None:
            return
        self.plot.clear()
        self.plot.setTitle("")
        if result.y_values is None:
            self.plot.plot(
                np.asarray(result.x_values),
                np.asarray(result.magnitude_a),
                pen=pg.mkPen("#087f8c", width=2),
            )
            self.plot.setLabel("bottom", result.x_label)
            self.plot.setLabel("left", "Current magnitude", units="A")
        else:
            image = pg.ImageItem(np.asarray(result.magnitude_a), axisOrder="row-major")
            x = np.asarray(result.x_values)
            y = np.asarray(result.y_values)
            image.setRect(QtCore.QRectF(
                float(x[0]), float(y[0]),
                float(x[-1] - x[0]), float(y[-1] - y[0]),
            ))
            image.setColorMap(pg.colormap.get("viridis"))
            self.plot.addItem(image)
            self.plot.setLabel("bottom", result.x_label)
            self.plot.setLabel("left", result.y_label)


class BiasMeasurementTabs(QtWidgets.QTabWidget):
    """Own and coordinate the independent Bias measurement pages."""

    run_requested = QtCore.pyqtSignal(str, object)
    stop_requested = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, *, kinds: Sequence[str] | None = None):
        super().__init__(parent)
        requested_kinds = (
            tuple(
                kind
                for kind in BIAS_MEASUREMENT_KINDS
                if kind != "time_trace"
            )
            if kinds is None
            else tuple(map(str, kinds))
        )
        unknown = set(requested_kinds).difference(BIAS_MEASUREMENT_KINDS)
        if unknown:
            raise ValueError(f"unknown Bias measurement kinds: {sorted(unknown)}")
        self.pages = {
            kind: BiasMeasurementPage(kind, self)
            for kind in requested_kinds
        }
        for kind in requested_kinds:
            page = self.pages[kind]
            page.run_requested.connect(self.run_requested.emit)
            page.stop_requested.connect(self.stop_requested.emit)
            self.addTab(page, page.LABELS[kind])

    def set_channel_names(self, names: Sequence[str]) -> None:
        for page in self.pages.values():
            page.set_channel_names(names)

    def settings_dict(self) -> dict:
        return normalize_bias_measurement_settings({
            kind: page.settings_dict()
            for kind, page in self.pages.items()
        })

    def load_settings(self, settings: Mapping[str, object]) -> None:
        normalized = normalize_bias_measurement_settings(settings)
        for kind, page in self.pages.items():
            page.load_settings(normalized[kind])

    def set_running(self, kind: str, running: bool, message: str) -> None:
        page = self.pages[str(kind)]
        page.set_running(running, message)
        for other_kind, other_page in self.pages.items():
            if other_kind != kind:
                other_page.run_button.setEnabled(not running)

    def update_progress(self, kind: str, percent: int, message: str) -> None:
        self.pages[str(kind)].update_progress(percent, message)

    def set_stopping(self, kind: str, message: str) -> None:
        self.pages[str(kind)].set_stopping(message)

    def begin_live_plot(self, layout: BiasMeasurementLiveLayout) -> None:
        self.pages[str(layout.kind)].begin_live_plot(layout)

    def update_live_point(self, point: BiasMeasurementLivePoint) -> None:
        self.pages[str(point.kind)].update_live_point(point)

    def show_result(self, result) -> None:
        self.pages[result.kind].show_result(result)
        for kind, page in self.pages.items():
            if kind != result.kind:
                page.run_button.setEnabled(True)

__all__ = [
    "BiasMeasurementPage",
    "BiasMeasurementTabs",
    "CurrentMeasurementSettings",
    "NestedAxisEditor",
]
