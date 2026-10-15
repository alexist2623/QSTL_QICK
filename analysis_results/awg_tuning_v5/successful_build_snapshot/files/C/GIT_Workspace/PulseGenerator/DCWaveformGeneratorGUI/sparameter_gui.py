"""Independent RF S-parameter sweep controls and result plotting.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import traceback
from typing import Any, Mapping

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

try:
    import pyqtgraph as pg
except ImportError:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
    from matplotlib.figure import Figure
    from matplotlib.widgets import SpanSelector

    _USE_PYQTGRAPH = False
else:
    _USE_PYQTGRAPH = True

try:
    from .qick_sparameter_sweep import (
        ACQUISITION_SOURCES,
        AVG_SWEEP_MODES,
        FILTER_TYPES,
        INPUT_CALIBRATION_SELECTIONS,
        MAGNITUDE_DISPLAY_MODES,
        MAX_RF_OUTPUT_GAIN,
        POWER_SCALES,
        SParameterSweepConfig,
        load_sparameter_run,
        run_sparameter_sweep,
    )
    from .power_calibration import (
        CalibrationDatabase,
        INPUT_BOARD_TYPES,
        OUTPUT_BOARD_TYPES,
    )
    from .qick_front_panel import QickFrontPanelPreview
    from .fir_ddr_profile import format_sample_rate_hz
except ImportError:
    from qick_sparameter_sweep import (
        ACQUISITION_SOURCES,
        AVG_SWEEP_MODES,
        FILTER_TYPES,
        INPUT_CALIBRATION_SELECTIONS,
        MAGNITUDE_DISPLAY_MODES,
        MAX_RF_OUTPUT_GAIN,
        POWER_SCALES,
        SParameterSweepConfig,
        load_sparameter_run,
        run_sparameter_sweep,
    )
    from power_calibration import (
        CalibrationDatabase,
        INPUT_BOARD_TYPES,
        OUTPUT_BOARD_TYPES,
    )
    from qick_front_panel import QickFrontPanelPreview
    from fir_ddr_profile import format_sample_rate_hz


DEFAULT_SPARAMETER_DB_PATH = str(Path.home() / "qick_sparameter_experiments.db")


class _PathComponent(QtWidgets.QFrame):
    """Compact control block placed directly on the RF path diagram."""

    def __init__(self, title: str, widget: QtWidgets.QWidget, parent=None):
        super().__init__(parent)
        self.setObjectName("rfPathComponent")
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Fixed,
        )
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 7)
        layout.setSpacing(4)
        self.title = QtWidgets.QLabel(title)
        self.title.setAlignment(QtCore.Qt.AlignCenter)
        font = self.title.font()
        font.setBold(True)
        self.title.setFont(font)
        layout.addWidget(self.title)
        layout.addWidget(widget)
        self.setStyleSheet(
            "QFrame#rfPathComponent {"
            "  background: #ffffff;"
            "  border: 1px solid #aeb7c2;"
            "  border-radius: 4px;"
            "}"
            "QFrame#rfPathComponent QLabel {"
            "  color: #20252b; border: none; background: transparent;"
            "}"
        )

    def set_title(self, title: str) -> None:
        self.title.setText(title)


class RfPathCorrectionWidget(QtWidgets.QGroupBox):
    """Two-column output-to-DUT-to-input path with a top panel preview."""

    settings_applied = QtCore.pyqtSignal(object)
    front_panel_requested = QtCore.pyqtSignal()

    def __init__(self, parent=None, *, compact: bool = False):
        super().__init__("RF Path and DUT De-embedding", parent)
        self._front_panel_configuration = None
        self._compact = bool(compact)
        self.setMinimumHeight(500 if self._compact else 540)
        self.setStyleSheet(
            "QGroupBox { color: #20252b; font-weight: 600; }"
            "QLabel { color: #20252b; }"
            "QSpinBox, QDoubleSpinBox, QComboBox {"
            "  color: #20252b; background: #ffffff;"
            "}"
        )

        self.output_ch = self._channel_spin()
        self.readout_ch = self._channel_spin()
        self.output_nqz = self._nyquist_spin()
        self.readout_nqz = self._nyquist_spin()
        self.output_board_type = self._board_combo(OUTPUT_BOARD_TYPES, "RF_Out")
        self.input_board_type = self._board_combo(INPUT_BOARD_TYPES, "DC_In")

        self.output_att1_db = self._attenuation_spin(10.0)
        self.output_att2_db = self._attenuation_spin(10.0)
        self.readout_attenuation_db = self._attenuation_spin(20.0)
        self.readout_dc_gain_db = self._db_spin(0.0, -6.0, 26.0, 1.0)
        self.loss1_db = self._db_spin(0.0, 0.0, 200.0, 0.1)
        self.loss2_db = self._db_spin(0.0, 0.0, 200.0, 0.1)
        self.amplifier_gain_db = self._db_spin(0.0, -200.0, 200.0, 0.1)

        self.input_endpoint = _PathComponent(
            "RF IN",
            self._endpoint_form(
                ("Readout channel", self.readout_ch),
                ("Input board", self.input_board_type),
                ("ADC Nyquist", self.readout_nqz),
            ),
            self,
        )
        self.output_endpoint = _PathComponent(
            "RF OUT",
            self._endpoint_form(
                ("Output channel", self.output_ch),
                ("Output board", self.output_board_type),
                ("DAC Nyquist", self.output_nqz),
            ),
            self,
        )
        self.input_condition_stack = QtWidgets.QStackedWidget(self)
        self.input_condition_stack.addWidget(self.readout_attenuation_db)
        self.input_condition_stack.addWidget(self.readout_dc_gain_db)
        self.input_condition_stack.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Fixed,
        )
        self.input_condition_stack.setFixedHeight(
            max(
                self.readout_attenuation_db.sizeHint().height(),
                self.readout_dc_gain_db.sizeHint().height(),
            )
        )
        self.input_condition = _PathComponent(
            "INPUT ATT",
            self.input_condition_stack,
            self,
        )
        self.output_att1_component = _PathComponent("ATT1", self.output_att1_db, self)
        self.output_att2_component = _PathComponent("ATT2", self.output_att2_db, self)
        self.loss1_component = _PathComponent("LOSS1", self.loss1_db, self)
        self.loss2_component = _PathComponent("LOSS2", self.loss2_db, self)
        self.amplifier_component = _PathComponent(
            "AMP GAIN", self.amplifier_gain_db, self
        )
        dut_label = QtWidgets.QLabel("Device under test")
        dut_label.setAlignment(QtCore.Qt.AlignCenter)
        self.dut_component = _PathComponent("DUT", dut_label, self)
        self.dut_component.setMinimumWidth(180)

        self.front_panel_preview = QickFrontPanelPreview(self)
        self.front_panel_preview.activated.connect(self.front_panel_requested.emit)
        self.update_button = QtWidgets.QPushButton("Update", self)
        self.update_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload)
        )
        self.update_button.setToolTip(
            "Apply this RF path only to the current measurement tab"
        )
        self.apply_status = QtWidgets.QLabel("Applied", self)
        self.apply_status.setAlignment(QtCore.Qt.AlignCenter)
        self.apply_status.setStyleSheet(
            "QLabel { color: #2f6f4e; background: transparent; font-weight: 600; }"
        )
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(12, 20, 12, 12)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.addWidget(self.front_panel_preview, 0, 0, 1, 2)
        layout.addWidget(self.input_endpoint, 1, 0)
        layout.addWidget(self.output_endpoint, 1, 1)
        layout.addWidget(self.input_condition, 2, 0)
        layout.addWidget(self.output_att1_component, 2, 1)
        layout.addWidget(self.amplifier_component, 3, 0)
        layout.addWidget(self.output_att2_component, 3, 1)
        layout.addWidget(self.loss2_component, 4, 0)
        layout.addWidget(self.loss1_component, 4, 1)
        layout.addWidget(
            self.dut_component,
            5,
            0,
            1,
            2,
            QtCore.Qt.AlignHCenter,
        )
        layout.addWidget(self.update_button, 6, 0, 1, 2)
        layout.addWidget(self.apply_status, 7, 0, 1, 2)

        self.output_board_type.currentTextChanged.connect(self._update_board_controls)
        self.input_board_type.currentTextChanged.connect(self._update_board_controls)
        for widget in (
            self.output_ch,
            self.readout_ch,
            self.output_nqz,
            self.readout_nqz,
            self.output_att1_db,
            self.output_att2_db,
            self.readout_attenuation_db,
            self.readout_dc_gain_db,
            self.loss1_db,
            self.loss2_db,
            self.amplifier_gain_db,
        ):
            widget.valueChanged.connect(self._mark_dirty)
        self.output_board_type.currentTextChanged.connect(self._mark_dirty)
        self.input_board_type.currentTextChanged.connect(self._mark_dirty)
        self.output_ch.valueChanged.connect(self._sync_front_panel_selection)
        self.readout_ch.valueChanged.connect(self._sync_front_panel_selection)
        self.update_button.clicked.connect(self.apply_settings)
        self._applied_values = {}
        self._update_board_controls()
        self.apply_settings(emit=False)

    @staticmethod
    def _channel_spin() -> QtWidgets.QSpinBox:
        widget = QtWidgets.QSpinBox()
        widget.setRange(0, 255)
        return widget

    @staticmethod
    def _nyquist_spin() -> QtWidgets.QSpinBox:
        widget = QtWidgets.QSpinBox()
        widget.setRange(1, 2)
        widget.setValue(1)
        widget.setToolTip("RFDC Nyquist zone; supported values are 1 and 2")
        return widget

    @staticmethod
    def _board_combo(values, selected: str) -> QtWidgets.QComboBox:
        widget = QtWidgets.QComboBox()
        widget.addItems(values)
        widget.setCurrentText(selected)
        return widget

    @staticmethod
    def _attenuation_spin(value: float) -> QtWidgets.QDoubleSpinBox:
        return RfPathCorrectionWidget._db_spin(value, 0.0, 31.75, 0.25)

    @staticmethod
    def _db_spin(
        value: float,
        minimum: float,
        maximum: float,
        step: float,
    ) -> QtWidgets.QDoubleSpinBox:
        widget = QtWidgets.QDoubleSpinBox()
        widget.setRange(minimum, maximum)
        widget.setDecimals(2)
        widget.setSingleStep(step)
        widget.setValue(value)
        widget.setSuffix(" dB")
        widget.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Fixed,
        )
        return widget

    @staticmethod
    def _endpoint_form(*rows) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        for label, control in rows:
            layout.addRow(label, control)
        return widget

    def _update_board_controls(self, *_args) -> None:
        rf_output = self.output_board_type.currentText() == "RF_Out"
        self.output_att1_component.setVisible(rf_output)
        self.output_att2_component.setVisible(rf_output)
        rf_input = self.input_board_type.currentText() == "RF_In"
        self.input_condition_stack.setCurrentIndex(0 if rf_input else 1)
        self.input_condition.set_title("INPUT ATT" if rf_input else "DC INPUT GAIN")
        self._update_summary()
        self.updateGeometry()
        self.update()

    def _editor_values(self) -> dict[str, Any]:
        return {
            "output_ch": self.output_ch.value(),
            "readout_ch": self.readout_ch.value(),
            "output_nqz": self.output_nqz.value(),
            "readout_nqz": self.readout_nqz.value(),
            "output_board_type": self.output_board_type.currentText(),
            "input_board_type": self.input_board_type.currentText(),
            "output_att1_db": self.output_att1_db.value(),
            "output_att2_db": self.output_att2_db.value(),
            "readout_attenuation_db": self.readout_attenuation_db.value(),
            "readout_dc_gain_db": self.readout_dc_gain_db.value(),
            "loss1_db": self.loss1_db.value(),
            "loss2_db": self.loss2_db.value(),
            "amplifier_gain_db": self.amplifier_gain_db.value(),
        }

    def applied_values(self) -> dict[str, Any]:
        """Return the last values committed with the Update button."""
        return dict(self._applied_values)

    def apply_external_settings(self, values: Mapping[str, Any]) -> None:
        """Adopt a committed path without emitting another update."""
        assignments = (
            (self.output_ch, "output_ch"),
            (self.readout_ch, "readout_ch"),
            (self.output_nqz, "output_nqz"),
            (self.readout_nqz, "readout_nqz"),
            (self.output_att1_db, "output_att1_db"),
            (self.output_att2_db, "output_att2_db"),
            (self.readout_attenuation_db, "readout_attenuation_db"),
            (self.readout_dc_gain_db, "readout_dc_gain_db"),
            (self.loss1_db, "loss1_db"),
            (self.loss2_db, "loss2_db"),
            (self.amplifier_gain_db, "amplifier_gain_db"),
        )
        for widget, key in assignments:
            if key in values:
                widget.setValue(values[key])
        if "output_board_type" in values:
            self.output_board_type.setCurrentText(str(values["output_board_type"]))
        if "input_board_type" in values:
            self.input_board_type.setCurrentText(str(values["input_board_type"]))
        self._update_board_controls()
        self.apply_settings(emit=False)

    def apply_settings(self, _checked=False, *, emit: bool = True) -> None:
        """Commit edited path values and optionally notify linked panels."""
        self._applied_values = self._editor_values()
        self.update_button.setEnabled(False)
        self.apply_status.setText("Applied to this measurement tab")
        self.apply_status.setStyleSheet(
            "QLabel { color: #2f6f4e; background: transparent; font-weight: 600; }"
        )
        self._update_summary()
        if emit:
            self.settings_applied.emit(self.applied_values())

    def _mark_dirty(self, *_args) -> None:
        if not self._applied_values:
            return
        dirty = self._editor_values() != self._applied_values
        self.update_button.setEnabled(dirty)
        if dirty:
            self.apply_status.setText("Pending changes - click Update")
            self.apply_status.setStyleSheet(
                "QLabel { color: #9a5a16; background: transparent; font-weight: 600; }"
            )
        else:
            self.apply_status.setText("Applied")
            self.apply_status.setStyleSheet(
                "QLabel { color: #2f6f4e; background: transparent; font-weight: 600; }"
            )

    def _update_summary(self, *_args) -> None:
        values = self._editor_values()
        self.front_panel_preview.set_channels(
            output_ch=int(values["output_ch"]),
            input_ch=int(values["readout_ch"]),
        )

    def set_front_panel_configuration(self, configuration) -> None:
        """Display live HWH routing and adopt detected board types by channel."""
        self._front_panel_configuration = configuration
        self.front_panel_preview.set_configuration(configuration)
        self._sync_front_panel_selection()

    def _sync_front_panel_selection(self, *_args) -> None:
        if self._front_panel_configuration is None:
            return
        configuration = self._front_panel_configuration
        self._adopt_detected_board(
            configuration.outputs,
            self.output_ch.value(),
            self.output_board_type,
        )
        self._adopt_detected_board(
            configuration.inputs,
            self.readout_ch.value(),
            self.input_board_type,
        )
        self._update_board_controls()

    @staticmethod
    def _adopt_detected_board(ports, channel: int, combo: QtWidgets.QComboBox) -> None:
        for port in ports:
            if channel in port.qick_channels and port.board_type is not None:
                combo.setCurrentText(port.board_type)
                return

    @staticmethod
    def _top_center(widget: QtWidgets.QWidget) -> QtCore.QPointF:
        geometry = widget.geometry()
        return QtCore.QPointF(geometry.center().x(), geometry.top())

    @staticmethod
    def _bottom_center(widget: QtWidgets.QWidget) -> QtCore.QPointF:
        geometry = widget.geometry()
        return QtCore.QPointF(geometry.center().x(), geometry.bottom())

    @staticmethod
    def _left_center(widget: QtWidgets.QWidget) -> QtCore.QPointF:
        geometry = widget.geometry()
        return QtCore.QPointF(geometry.left(), geometry.center().y())

    @staticmethod
    def _right_center(widget: QtWidgets.QWidget) -> QtCore.QPointF:
        geometry = widget.geometry()
        return QtCore.QPointF(geometry.right(), geometry.center().y())

    @staticmethod
    def _draw_arrow(
        painter: QtGui.QPainter,
        points,
        color: QtGui.QColor,
    ) -> None:
        if len(points) < 2:
            return
        pen = QtGui.QPen(color, 2.0)
        pen.setJoinStyle(QtCore.Qt.MiterJoin)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        path = QtGui.QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)
        painter.drawPath(path)
        start = points[-2]
        end = points[-1]
        direction = end - start
        length = max(1.0, (direction.x() ** 2 + direction.y() ** 2) ** 0.5)
        unit = QtCore.QPointF(direction.x() / length, direction.y() / length)
        normal = QtCore.QPointF(-unit.y(), unit.x())
        arrow = QtGui.QPolygonF(
            [
                end,
                end - unit * 8.0 + normal * 4.0,
                end - unit * 8.0 - normal * 4.0,
            ]
        )
        painter.setBrush(color)
        painter.drawPolygon(arrow)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        output_color = QtGui.QColor("#b85f26")
        input_color = QtGui.QColor("#237a72")

        output_nodes = [self.output_endpoint]
        output_nodes.extend(
            node
            for node in (self.output_att1_component, self.output_att2_component)
            if node.isVisible()
        )
        output_nodes.append(self.loss1_component)
        for first, second in zip(output_nodes, output_nodes[1:]):
            self._draw_arrow(
                painter,
                [self._bottom_center(first), self._top_center(second)],
                output_color,
            )

        loss1_bottom = self._bottom_center(self.loss1_component)
        dut_right = self._right_center(self.dut_component)
        self._draw_arrow(
            painter,
            [
                loss1_bottom,
                QtCore.QPointF(loss1_bottom.x(), dut_right.y()),
                dut_right,
            ],
            output_color,
        )

        dut_left = self._left_center(self.dut_component)
        loss2_bottom = self._bottom_center(self.loss2_component)
        self._draw_arrow(
            painter,
            [
                dut_left,
                QtCore.QPointF(loss2_bottom.x(), dut_left.y()),
                loss2_bottom,
            ],
            input_color,
        )
        input_nodes = [
            self.loss2_component,
            self.amplifier_component,
            self.input_condition,
            self.input_endpoint,
        ]
        for first, second in zip(input_nodes, input_nodes[1:]):
            self._draw_arrow(
                painter,
                [self._top_center(first), self._bottom_center(second)],
                input_color,
            )


class SParameterSweepPanel(QtWidgets.QWidget):
    """Controls for an RF-only generator/readout hardware frequency sweep."""

    run_requested = QtCore.pyqtSignal()
    phase_display_changed = QtCore.pyqtSignal(str)
    magnitude_display_changed = QtCore.pyqtSignal(str)
    load_requested = QtCore.pyqtSignal(int)
    path_settings_applied = QtCore.pyqtSignal(object)
    front_panel_requested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fir_sample_rate_hz = None
        self._fir_trigger_delay_us = 0.0
        self._fir_uses_fpga_trigger_delay = None
        outer = QtWidgets.QVBoxLayout(self)
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget(scroll)
        content_layout = QtWidgets.QVBoxLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.path_diagram = RfPathCorrectionWidget(content)
        self.output_ch = self.path_diagram.output_ch
        self.readout_ch = self.path_diagram.readout_ch
        self.output_nqz = self.path_diagram.output_nqz
        self.readout_nqz = self.path_diagram.readout_nqz
        self.output_board_type = self.path_diagram.output_board_type
        self.input_board_type = self.path_diagram.input_board_type
        self.output_att1_db = self.path_diagram.output_att1_db
        self.output_att2_db = self.path_diagram.output_att2_db
        self.readout_attenuation_db = self.path_diagram.readout_attenuation_db
        self.readout_dc_gain_db = self.path_diagram.readout_dc_gain_db
        self.loss1_db = self.path_diagram.loss1_db
        self.loss2_db = self.path_diagram.loss2_db
        self.amplifier_gain_db = self.path_diagram.amplifier_gain_db
        self.path_diagram.settings_applied.connect(self._forward_path_settings)
        self.path_diagram.front_panel_requested.connect(
            self.front_panel_requested.emit
        )
        content_layout.addWidget(self.path_diagram)
        path_hint = QtWidgets.QLabel(
            "ATT, RF filters, board selection, and Nyquist zones belong to "
            "this S-parameter tab and its HWH-backed front-panel editor."
        )
        path_hint.setWordWrap(True)
        path_hint.setStyleSheet("QLabel { color: #4f5b66; padding: 2px 6px; }")
        content_layout.addWidget(path_hint)

        sweep_group = QtWidgets.QGroupBox("Frequency Sweep")
        sweep_form = QtWidgets.QFormLayout(sweep_group)
        self.frequency_start_mhz = self._frequency_spin(10.0)
        self.frequency_end_mhz = self._frequency_spin(100.0)
        self.frequency_points = QtWidgets.QSpinBox()
        self.frequency_points.setRange(2, 1_000_000)
        self.frequency_points.setValue(101)
        self.gain = QtWidgets.QSpinBox()
        self.gain.setRange(0, MAX_RF_OUTPUT_GAIN)
        self.gain.setValue(20000)
        self.gain.setSuffix(f" / {MAX_RF_OUTPUT_GAIN}")
        self.output_power_dbm = self._power_spin(-20.0)
        self.calculated_gain_status = QtWidgets.QLabel(
            "Enable frequency-response compensation to calculate gain"
        )
        self.calculated_gain_status.setWordWrap(True)
        self.calculated_gain_status.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self.calculated_gain_status.setToolTip(
            "Nominal gain is the gain at the weakest calibrated frequency. "
            "The applied range includes the per-frequency correction loaded "
            "into tProcessor DMEM."
        )
        self._gain_preview_timer = QtCore.QTimer(self)
        self._gain_preview_timer.setSingleShot(True)
        self._gain_preview_timer.setInterval(200)
        self._gain_preview_timer.timeout.connect(
            self._update_calibrated_gain_preview
        )
        self.scan_time_us = QtWidgets.QDoubleSpinBox()
        self.scan_time_us.setRange(0.001, 1.0e6)
        self.scan_time_us.setDecimals(6)
        self.scan_time_us.setValue(10.0)
        self.scan_time_us.setSuffix(" us")
        sweep_form.addRow("Start frequency:", self.frequency_start_mhz)
        sweep_form.addRow("End frequency:", self.frequency_end_mhz)
        sweep_form.addRow("Frequency points:", self.frequency_points)
        sweep_form.addRow("Manual output gain:", self.gain)
        sweep_form.addRow("Single target power:", self.output_power_dbm)
        sweep_form.addRow("dBm -> applied gain:", self.calculated_gain_status)
        sweep_form.addRow("Scan time per point:", self.scan_time_us)
        content_layout.addWidget(sweep_group)

        self.power_calibration_enabled = QtWidgets.QGroupBox(
            "Frequency Response Compensation"
        )
        self.power_calibration_enabled.setCheckable(True)
        self.power_calibration_enabled.setChecked(False)
        calibration_form = QtWidgets.QFormLayout(self.power_calibration_enabled)
        self.calibration_database_path = QtWidgets.QLineEdit()
        self.calibration_database_path.setPlaceholderText("Select gain_pwr_calb.db")
        self.browse_calibration_database = QtWidgets.QToolButton()
        self.browse_calibration_database.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton)
        )
        self.browse_calibration_database.setToolTip(
            "Choose a QCoDeS frequency-response calibration database"
        )
        self.browse_calibration_database.clicked.connect(
            self._browse_calibration_database
        )
        calibration_path_row = QtWidgets.QHBoxLayout()
        calibration_path_row.addWidget(self.calibration_database_path, 1)
        calibration_path_row.addWidget(self.browse_calibration_database)
        self.calibration_hint = QtWidgets.QLabel(
            "Same-board response; normalized to the weakest frequency in the sweep."
        )
        self.calibration_hint.setWordWrap(True)
        self.input_calibration_selection = QtWidgets.QComboBox()
        selection_labels = {
            "latest_matching_attenuation": "Latest with same input ATT",
            "manual_run_id": "Manual Run ID",
        }
        for selection in INPUT_CALIBRATION_SELECTIONS:
            self.input_calibration_selection.addItem(
                selection_labels[selection], selection
            )
        self.input_calibration_selection.setToolTip(
            "Automatically use the newest covering input calibration acquired "
            "at the current input attenuation, or choose a specific QCoDeS Run ID."
        )
        self.requested_input_calibration_run_id = QtWidgets.QSpinBox()
        self.requested_input_calibration_run_id.setRange(0, 2_147_483_647)
        self.requested_input_calibration_run_id.setSpecialValueText(
            "Select Run ID"
        )
        self.requested_input_calibration_run_id.setToolTip(
            "Input-power calibration QCoDeS Run ID used in manual mode"
        )
        calibration_form.addRow("Calibration DB:", calibration_path_row)
        calibration_form.addRow(
            "Input calibration:", self.input_calibration_selection
        )
        calibration_form.addRow(
            "Input calibration Run ID:",
            self.requested_input_calibration_run_id,
        )
        calibration_form.addRow(self.calibration_hint)
        content_layout.addWidget(self.power_calibration_enabled)

        self.power_sweep_enabled = QtWidgets.QGroupBox("Power Sweep (Software)")
        self.power_sweep_enabled.setCheckable(True)
        self.power_sweep_enabled.setChecked(False)
        power_form = QtWidgets.QFormLayout(self.power_sweep_enabled)
        self.power_start_gain = self._gain_spin(1000)
        self.power_end_gain = self._gain_spin(20000)
        self.power_start_dbm = self._power_spin(-30.0)
        self.power_end_dbm = self._power_spin(-10.0)
        self.power_points = QtWidgets.QSpinBox()
        self.power_points.setRange(2, 100_000)
        self.power_points.setValue(5)
        self.power_scale = QtWidgets.QComboBox()
        scale_labels = {"linear": "Linear", "log": "Logarithmic"}
        for scale in POWER_SCALES:
            self.power_scale.addItem(scale_labels[scale], scale)
        power_form.addRow("Start gain code:", self.power_start_gain)
        power_form.addRow("End gain code:", self.power_end_gain)
        power_form.addRow("Start target power:", self.power_start_dbm)
        power_form.addRow("End target power:", self.power_end_dbm)
        power_form.addRow("Power points:", self.power_points)
        power_form.addRow("Spacing:", self.power_scale)
        self.power_sweep_enabled.toggled.connect(self._update_power_control_state)
        self.power_calibration_enabled.toggled.connect(self._update_power_control_state)
        self.input_calibration_selection.currentIndexChanged.connect(
            self._update_power_control_state
        )
        for widget in (
            self.frequency_start_mhz,
            self.frequency_end_mhz,
            self.frequency_points,
            self.output_power_dbm,
            self.power_start_dbm,
            self.power_end_dbm,
            self.power_points,
        ):
            widget.valueChanged.connect(self._schedule_calibrated_gain_preview)
        self.power_scale.currentIndexChanged.connect(
            self._schedule_calibrated_gain_preview
        )
        self.calibration_database_path.textChanged.connect(
            self._schedule_calibrated_gain_preview
        )
        content_layout.addWidget(self.power_sweep_enabled)
        self._update_power_control_state(False)

        output_group = QtWidgets.QGroupBox("Output Filter")
        output_form = QtWidgets.QFormLayout(output_group)
        self.output_filter_type = self._filter_combo()
        self.output_filter_cutoff_ghz = self._filter_spin(2.5)
        self.output_filter_bandwidth_ghz = self._filter_spin(1.0)
        output_form.addRow("Filter:", self.output_filter_type)
        output_form.addRow("Cutoff/center:", self.output_filter_cutoff_ghz)
        output_form.addRow("Bandwidth:", self.output_filter_bandwidth_ghz)
        content_layout.addWidget(output_group)
        output_group.hide()

        readout_group = QtWidgets.QGroupBox("Input Filter")
        readout_form = QtWidgets.QFormLayout(readout_group)
        self.readout_filter_type = self._filter_combo()
        self.readout_filter_cutoff_ghz = self._filter_spin(2.5)
        self.readout_filter_bandwidth_ghz = self._filter_spin(1.0)
        readout_form.addRow("Filter:", self.readout_filter_type)
        readout_form.addRow("Cutoff/center:", self.readout_filter_cutoff_ghz)
        readout_form.addRow("Bandwidth:", self.readout_filter_bandwidth_ghz)
        content_layout.addWidget(readout_group)
        readout_group.hide()
        self.output_board_type.currentTextChanged.connect(
            self._update_filter_control_state
        )
        self.input_board_type.currentTextChanged.connect(
            self._update_filter_control_state
        )
        self._update_filter_control_state()

        capture_group = QtWidgets.QGroupBox("I/Q Acquisition")
        capture_form = QtWidgets.QFormLayout(capture_group)
        self.acquisition_source = QtWidgets.QComboBox()
        acquisition_labels = {
            "fir_ddr": "FIR DDR trace mean",
            "avg_buffer": "AVG buffer accumulated I/Q",
        }
        for source in ACQUISITION_SOURCES:
            self.acquisition_source.addItem(acquisition_labels[source], source)
        self.acquisition_source.setToolTip(
            "FIR DDR stores a decimated I/Q trace and averages it in Python. "
            "AVG buffer integrates the readout window in FPGA and averages "
            "repeated captures for one I/Q value per frequency."
        )
        self.avg_repetitions = QtWidgets.QSpinBox()
        self.avg_repetitions.setRange(1, 10_000_000)
        self.avg_repetitions.setValue(100)
        self.avg_repetitions.setToolTip(
            "Number of repeated AVG-buffer integrations accumulated at every "
            "frequency. QICK returns the result normalized by integration "
            "length and repetitions."
        )
        self.avg_sweep_mode = QtWidgets.QComboBox()
        self.avg_sweep_mode.addItem(
            "Hardware repetitions (tProcessor)",
            "hardware",
        )
        self.avg_sweep_mode.addItem(
            "Software repetitions (host rounds)",
            "software",
        )
        self.avg_sweep_mode.setToolTip(
            "Hardware mode repeats every frequency point inside the "
            "tProcessor loop. Software mode repeats the complete hardware "
            "frequency sweep as host-controlled averaging rounds."
        )
        self.avg_hardware_rep_delay_us = QtWidgets.QDoubleSpinBox()
        self.avg_hardware_rep_delay_us.setRange(0.0, 1.0e9)
        self.avg_hardware_rep_delay_us.setDecimals(6)
        self.avg_hardware_rep_delay_us.setSuffix(" us")
        self.avg_hardware_rep_delay_us.setToolTip(
            "Fixed pacing guard after every hardware AVG repetition; this "
            "is not a PC readback handshake."
        )
        self.margin_input_samples = QtWidgets.QSpinBox()
        self.margin_input_samples.setRange(0, 10_000_000)
        self.margin_input_samples.setValue(1024)
        self.override_fpga_trigger_delay = QtWidgets.QCheckBox(
            "Override HWH default"
        )
        self.fpga_trigger_delay_us = QtWidgets.QDoubleSpinBox()
        self.fpga_trigger_delay_us.setRange(0.0, 10_000_000.0)
        self.fpga_trigger_delay_us.setDecimals(6)
        self.fpga_trigger_delay_us.setSuffix(" us")
        self.fpga_trigger_delay_us.setToolTip(
            "FPGA delay from trigger arrival to FIR-DDR storage"
        )
        fpga_delay_row = QtWidgets.QHBoxLayout()
        fpga_delay_row.setContentsMargins(0, 0, 0, 0)
        fpga_delay_row.addWidget(self.override_fpga_trigger_delay)
        fpga_delay_row.addWidget(self.fpga_trigger_delay_us, 1)
        self.address = QtWidgets.QSpinBox()
        self.address.setRange(0, 2_147_483_647)
        self.stride_bytes = QtWidgets.QSpinBox()
        self.stride_bytes.setRange(0, 2_147_483_647)
        self.stride_bytes.setSpecialValueText("Automatic")
        self.force_overwrite = QtWidgets.QCheckBox("Allow DDR overwrite")
        self.fir_profile_status = QtWidgets.QLabel(
            "Identify QICK to show the FIR DDR timing"
        )
        self.fir_profile_status.setWordWrap(True)
        self.fir_profile_status.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        capture_form.addRow("Source:", self.acquisition_source)
        capture_form.addRow("AVG repetitions / frequency:", self.avg_repetitions)
        capture_form.addRow("AVG repetition mode:", self.avg_sweep_mode)
        capture_form.addRow(
            "Hardware repetition guard:",
            self.avg_hardware_rep_delay_us,
        )
        capture_form.addRow("FIR input margin:", self.margin_input_samples)
        capture_form.addRow(
            "FPGA trigger-to-store delay:",
            fpga_delay_row,
        )
        capture_form.addRow("DDR start address:", self.address)
        capture_form.addRow("Trigger stride (bytes):", self.stride_bytes)
        capture_form.addRow("Acquisition details:", self.fir_profile_status)
        capture_form.addRow(self.force_overwrite)
        content_layout.addWidget(capture_group)
        self._fir_capture_widgets = (
            self.margin_input_samples,
            self.override_fpga_trigger_delay,
            self.fpga_trigger_delay_us,
            self.address,
            self.stride_bytes,
            self.force_overwrite,
        )
        self.acquisition_source.currentIndexChanged.connect(
            self._update_acquisition_source_state
        )
        self.avg_repetitions.valueChanged.connect(
            self._update_fir_profile_status
        )
        self.avg_sweep_mode.currentIndexChanged.connect(
            self._update_acquisition_source_state
        )
        self.override_fpga_trigger_delay.toggled.connect(
            self._update_fpga_trigger_delay_controls
        )
        self.fpga_trigger_delay_us.valueChanged.connect(
            self._update_fir_profile_status
        )

        display_group = QtWidgets.QGroupBox("Plot Display")
        display_form = QtWidgets.QFormLayout(display_group)
        self.phase_display = QtWidgets.QComboBox()
        self.phase_display.addItem("Unwrapped", "unwrapped")
        self.phase_display.addItem("Wrapped (-180 to 180 deg)", "wrapped")
        self.phase_display.setToolTip("Wrapped phase uses atan2(mean Q, mean I), without unwrapping or phase-line subtraction.")
        self.phase_display.currentIndexChanged.connect(
            lambda: self.phase_display_changed.emit(str(self.phase_display.currentData()))
        )
        display_form.addRow("Phase:", self.phase_display)
        self.magnitude_display = QtWidgets.QComboBox()
        for label, mode in (
            ("Response (dB, existing display)", "response_db"),
            ("ADC units (linear axis)", "adc_linear"),
            ("ADC units (log axis)", "adc_log"),
            ("ADC magnitude (20 log10, dB)", "adc_db"),
        ):
            self.magnitude_display.addItem(label, mode)
        self.magnitude_display.setToolTip(
            "ADC magnitude is hypot(mean I, mean Q), before power calibration. "
            "Log axis retains ADC-unit values; dB uses 20*log10(magnitude). "
            "Zero is shown on the linear axis and omitted on logarithmic displays."
        )
        self.magnitude_display.currentIndexChanged.connect(
            lambda: self.magnitude_display_changed.emit(str(self.magnitude_display.currentData()))
        )
        display_form.addRow("Magnitude:", self.magnitude_display)
        content_layout.addWidget(display_group)

        storage_group = QtWidgets.QGroupBox("S-Parameter Database")
        storage_form = QtWidgets.QFormLayout(storage_group)
        self.save_to_qcodes = QtWidgets.QCheckBox("Save measurement to QCoDeS DB")
        self.save_to_qcodes.setChecked(True)
        self.save_to_qcodes.setToolTip("Save I/Q, magnitude, wrapped phase and unwrapped phase. When off, results remain in memory only.")
        storage_form.addRow(self.save_to_qcodes)
        self.database_path = QtWidgets.QLineEdit(DEFAULT_SPARAMETER_DB_PATH)
        self.browse_database = QtWidgets.QToolButton()
        self.browse_database.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton)
        )
        self.browse_database.setToolTip("Choose RF S-parameter QCoDeS SQLite database")
        self.browse_database.clicked.connect(self._browse_database)
        database_row = QtWidgets.QHBoxLayout()
        database_row.addWidget(self.database_path, 1)
        database_row.addWidget(self.browse_database)
        storage_form.addRow("QCoDeS DB file:", database_row)
        content_layout.addWidget(storage_group)
        content_layout.addStretch(1)

        self.run_button = QtWidgets.QPushButton("Run RF S-Parameter Sweep")
        self.run_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay)
        )
        self.run_button.clicked.connect(self.run_requested.emit)
        self.run_id = QtWidgets.QSpinBox()
        self.run_id.setRange(0, 2_147_483_647)
        self.run_id.setSpecialValueText("Latest S-parameter run")
        self.load_button = QtWidgets.QPushButton("Load Saved Run")
        self.load_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton)
        )
        self.load_button.clicked.connect(
            lambda: self.load_requested.emit(self.run_id.value())
        )
        load_row = QtWidgets.QHBoxLayout()
        load_row.addWidget(self.run_id, 1)
        load_row.addWidget(self.load_button)
        outer.addWidget(self.run_button)
        outer.addLayout(load_row)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.hide()
        outer.addWidget(self.progress)
        self.status = QtWidgets.QLabel("Ready")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        self.scan_time_us.valueChanged.connect(self._update_fir_profile_status)

        self._internal_settings = {
            "settle_seconds": 0.05,
            "trigger_width_tproc_cycles": 12,
            "recovery_tproc_cycles": 20,
        }
        self._update_acquisition_source_state()

    @staticmethod
    def _frequency_spin(value: float) -> QtWidgets.QDoubleSpinBox:
        widget = QtWidgets.QDoubleSpinBox()
        widget.setRange(-100_000.0, 100_000.0)
        widget.setDecimals(9)
        widget.setValue(value)
        widget.setSuffix(" MHz")
        return widget

    @staticmethod
    def _gain_spin(value: int) -> QtWidgets.QSpinBox:
        widget = QtWidgets.QSpinBox()
        widget.setRange(0, MAX_RF_OUTPUT_GAIN)
        widget.setValue(value)
        widget.setSuffix(f" / {MAX_RF_OUTPUT_GAIN}")
        return widget

    @staticmethod
    def _power_spin(value: float) -> QtWidgets.QDoubleSpinBox:
        widget = QtWidgets.QDoubleSpinBox()
        widget.setRange(-200.0, 100.0)
        widget.setDecimals(6)
        widget.setValue(value)
        widget.setSuffix(" dBm")
        return widget

    @staticmethod
    def _attenuation_spin(value: float) -> QtWidgets.QDoubleSpinBox:
        widget = QtWidgets.QDoubleSpinBox()
        widget.setRange(0.0, 31.75)
        widget.setDecimals(2)
        widget.setSingleStep(0.25)
        widget.setValue(value)
        widget.setSuffix(" dB")
        return widget

    @staticmethod
    def _filter_spin(value: float) -> QtWidgets.QDoubleSpinBox:
        widget = QtWidgets.QDoubleSpinBox()
        widget.setRange(0.001, 100.0)
        widget.setDecimals(6)
        widget.setValue(value)
        widget.setSuffix(" GHz")
        return widget

    @staticmethod
    def _filter_combo() -> QtWidgets.QComboBox:
        widget = QtWidgets.QComboBox()
        widget.addItems(FILTER_TYPES)
        return widget

    def _update_power_control_state(self, _enabled: bool) -> None:
        sweep_enabled = self.power_sweep_enabled.isChecked()
        calibrated = self.power_calibration_enabled.isChecked()
        self.gain.setEnabled(not sweep_enabled and not calibrated)
        self.output_power_dbm.setEnabled(not sweep_enabled and calibrated)
        for widget in (
            self.power_start_gain,
            self.power_end_gain,
        ):
            widget.setEnabled(sweep_enabled and not calibrated)
        for widget in (self.power_start_dbm, self.power_end_dbm):
            widget.setEnabled(sweep_enabled and calibrated)
        self.power_points.setEnabled(sweep_enabled)
        self.power_scale.setEnabled(sweep_enabled)
        for widget in (
            self.calibration_database_path,
            self.browse_calibration_database,
            self.input_calibration_selection,
        ):
            widget.setEnabled(calibrated)
        manual_input_run = (
            self.input_calibration_selection.currentData() == "manual_run_id"
        )
        self.requested_input_calibration_run_id.setEnabled(
            calibrated and manual_input_run
        )
        self._schedule_calibrated_gain_preview()

    def _schedule_calibrated_gain_preview(self, *_args) -> None:
        self._gain_preview_timer.start()

    def _update_calibrated_gain_preview(self) -> None:
        if not self.power_calibration_enabled.isChecked():
            self.calculated_gain_status.setText(
                f"Manual gain {self.gain.value():,} / {MAX_RF_OUTPUT_GAIN:,}"
            )
            self.calculated_gain_status.setStyleSheet("")
            return

        database_path = self.calibration_database_path.text().strip()
        if not database_path:
            self.calculated_gain_status.setText("Select a calibration DB")
            self.calculated_gain_status.setStyleSheet(
                "QLabel { color: #9a5b00; font-weight: 600; }"
            )
            return

        try:
            point_count = min(self.frequency_points.value(), 4000)
            frequencies = np.linspace(
                self.frequency_start_mhz.value(),
                self.frequency_end_mhz.value(),
                point_count,
                dtype=float,
            )
            calibration = CalibrationDatabase(database_path).output_calibration(
                self.output_board_type.currentText(),
                frequencies,
            )
            if self.power_sweep_enabled.isChecked():
                targets = (
                    self.power_start_dbm.value(),
                    self.power_end_dbm.value(),
                )
            else:
                targets = (self.output_power_dbm.value(),)

            path = self.path_diagram.applied_values()
            schedules = [
                calibration.build_gain_schedule(
                    frequencies,
                    target,
                    output_att1_db=path["output_att1_db"],
                    output_att2_db=path["output_att2_db"],
                )
                for target in targets
            ]
            nominal_min = min(schedule.nominal_gain_code for schedule in schedules)
            nominal_max = max(schedule.nominal_gain_code for schedule in schedules)
            applied_min = min(int(np.min(schedule.gain_codes)) for schedule in schedules)
            applied_max = max(int(np.max(schedule.gain_codes)) for schedule in schedules)
            nominal_text = (
                f"{nominal_min:,}"
                if nominal_min == nominal_max
                else f"{nominal_min:,}-{nominal_max:,}"
            )
            applied_text = (
                f"{applied_min:,}"
                if applied_min == applied_max
                else f"{applied_min:,}-{applied_max:,}"
            )
            self.calculated_gain_status.setText(
                f"Nominal {nominal_text}; applied {applied_text} / "
                f"{MAX_RF_OUTPUT_GAIN:,} (calibration Run "
                f"{calibration.summary.run_id})"
            )
            self.calculated_gain_status.setStyleSheet(
                "QLabel { color: #176b38; font-weight: 600; }"
            )
        except Exception as exc:
            self.calculated_gain_status.setText(f"Gain unavailable: {exc}")
            self.calculated_gain_status.setStyleSheet(
                "QLabel { color: #a32626; font-weight: 600; }"
            )

    def _update_filter_control_state(self, *_args) -> None:
        output_rf = self.output_board_type.currentText() == "RF_Out"
        input_rf = self.input_board_type.currentText() == "RF_In"
        for widget in (
            self.output_filter_type,
            self.output_filter_cutoff_ghz,
            self.output_filter_bandwidth_ghz,
        ):
            widget.setEnabled(output_rf)
        for widget in (
            self.readout_filter_type,
            self.readout_filter_cutoff_ghz,
            self.readout_filter_bandwidth_ghz,
        ):
            widget.setEnabled(input_rf)

    def _browse_calibration_database(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Choose frequency-response calibration database",
            self.calibration_database_path.text().strip(),
            "QCoDeS SQLite database (*.db)",
        )
        if path:
            self.calibration_database_path.setText(path)

    def _browse_database(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Choose RF S-parameter database",
            self.database_path.text().strip() or DEFAULT_SPARAMETER_DB_PATH,
            "QCoDeS SQLite database (*.db)",
        )
        if path:
            if Path(path).suffix.lower() != ".db":
                path = str(Path(path).with_suffix(".db"))
            self.database_path.setText(path)

    def database_path_value(self) -> str:
        value = self.database_path.text().strip()
        if not value:
            raise ValueError("RF S-parameter database path must not be empty")
        path = Path(value).expanduser()
        if path.suffix.lower() != ".db":
            path = path.with_suffix(".db")
        return str(path)

    def _forward_path_settings(self, values: Mapping[str, Any]) -> None:
        """Report this tab's committed path without changing another tab."""
        linked = dict(values)
        linked.update(
            {
                "output_filter_type": self.output_filter_type.currentText(),
                "output_filter_cutoff_ghz": self.output_filter_cutoff_ghz.value(),
                "output_filter_bandwidth_ghz": (
                    self.output_filter_bandwidth_ghz.value()
                ),
                "readout_filter_type": self.readout_filter_type.currentText(),
                "readout_filter_cutoff_ghz": (
                    self.readout_filter_cutoff_ghz.value()
                ),
                "readout_filter_bandwidth_ghz": (
                    self.readout_filter_bandwidth_ghz.value()
                ),
            }
        )
        self.path_settings_applied.emit(linked)
        self._schedule_calibrated_gain_preview()

    def front_panel_values(self) -> Mapping[str, Any]:
        """Return this tab's complete RF path for the graphical editor."""
        values = self.path_diagram._editor_values()
        values.update(
            {
                "output_filter_type": self.output_filter_type.currentText(),
                "output_filter_cutoff_ghz": self.output_filter_cutoff_ghz.value(),
                "output_filter_bandwidth_ghz": (
                    self.output_filter_bandwidth_ghz.value()
                ),
                "readout_filter_type": self.readout_filter_type.currentText(),
                "readout_filter_cutoff_ghz": (
                    self.readout_filter_cutoff_ghz.value()
                ),
                "readout_filter_bandwidth_ghz": (
                    self.readout_filter_bandwidth_ghz.value()
                ),
            }
        )
        return values

    def apply_front_panel_settings(self, values: Mapping[str, Any]) -> None:
        """Apply graphical SMA settings only to this S-parameter tab."""
        self.path_diagram.apply_external_settings(values)
        self.output_filter_type.setCurrentText(str(values["output_filter_type"]))
        self.output_filter_cutoff_ghz.setValue(
            float(values["output_filter_cutoff_ghz"])
        )
        self.output_filter_bandwidth_ghz.setValue(
            float(values["output_filter_bandwidth_ghz"])
        )
        self.readout_filter_type.setCurrentText(str(values["readout_filter_type"]))
        self.readout_filter_cutoff_ghz.setValue(
            float(values["readout_filter_cutoff_ghz"])
        )
        self.readout_filter_bandwidth_ghz.setValue(
            float(values["readout_filter_bandwidth_ghz"])
        )
        self._schedule_calibrated_gain_preview()
        self.path_diagram._update_board_controls()
        self.path_diagram.apply_settings(emit=False)

    def set_front_panel_configuration(self, configuration) -> None:
        self.path_diagram.set_front_panel_configuration(configuration)
        self._fir_sample_rate_hz = getattr(
            configuration,
            "fir_sample_rate_hz",
            None,
        )
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
        self._update_fpga_trigger_delay_controls()
        self._update_fir_profile_status()

    def _update_fpga_trigger_delay_controls(self, *_args) -> None:
        supported = (
            self.acquisition_source.currentData() == "fir_ddr"
            and self._fir_uses_fpga_trigger_delay is not False
        )
        self.override_fpga_trigger_delay.setEnabled(supported)
        self.fpga_trigger_delay_us.setEnabled(
            supported and self.override_fpga_trigger_delay.isChecked()
        )
        self._update_fir_profile_status()

    def _update_acquisition_source_state(self, *_args) -> None:
        uses_fir = self.acquisition_source.currentData() == "fir_ddr"
        self.avg_repetitions.setEnabled(not uses_fir)
        self.avg_sweep_mode.setEnabled(not uses_fir)
        self.avg_hardware_rep_delay_us.setEnabled(
            not uses_fir and self.avg_sweep_mode.currentData() == "hardware"
        )
        for widget in self._fir_capture_widgets:
            widget.setEnabled(uses_fir)
        self._update_fpga_trigger_delay_controls()
        self._update_fir_profile_status()

    def _update_fir_profile_status(self, *_args) -> None:
        if self.acquisition_source.currentData() == "avg_buffer":
            integration_us = self.scan_time_us.value()
            repetitions = self.avg_repetitions.value()
            self.fir_profile_status.setStyleSheet("")
            self.fir_profile_status.setText(
                "AVG buffer: "
                f"{integration_us:g} us integration x {repetitions:,} "
                f"{self.avg_sweep_mode.currentData()} repetitions per "
                "frequency; returned I/Q is normalized by "
                "the integration length and repetition count. DDR is unused."
            )
            return
        if self._fir_sample_rate_hz is None:
            self.fir_profile_status.setText(
                "Identify QICK to show the FIR DDR timing"
            )
            return
        requested_sample_count = max(
            1,
            int(
                np.ceil(
                    self.scan_time_us.value()
                    * float(self._fir_sample_rate_hz)
                    / 1_000_000.0
                )
            ),
        )
        sample_count = requested_sample_count
        actual_time_us = (
            sample_count * 1_000_000.0 / float(self._fir_sample_rate_hz)
        )
        if self._fir_uses_fpga_trigger_delay:
            if self.override_fpga_trigger_delay.isChecked():
                delay = (
                    f"; FPGA delay override "
                    f"{self.fpga_trigger_delay_us.value():g} us"
                )
            else:
                delay = f"; HWH FPGA delay {self._fir_trigger_delay_us:g} us"
        else:
            delay = "; no FPGA trigger-delay register"
        sample_text = f"{sample_count:,} samples = {actual_time_us:g} us actual"
        self.fir_profile_status.setStyleSheet("")
        self.fir_profile_status.setText(
            f"{format_sample_rate_hz(self._fir_sample_rate_hz)}, "
            f"{sample_text}{delay}"
        )

    def config(self) -> SParameterSweepConfig:
        path = self.path_diagram.applied_values()
        return SParameterSweepConfig(
            output_ch=path["output_ch"],
            readout_ch=path["readout_ch"],
            frequency_start_mhz=self.frequency_start_mhz.value(),
            frequency_end_mhz=self.frequency_end_mhz.value(),
            frequency_points=self.frequency_points.value(),
            gain=self.gain.value(),
            power_calibration_enabled=(self.power_calibration_enabled.isChecked()),
            calibration_database_path=(self.calibration_database_path.text().strip()),
            input_calibration_selection=str(
                self.input_calibration_selection.currentData()
            ),
            requested_input_calibration_run_id=(
                self.requested_input_calibration_run_id.value()
            ),
            output_board_type=path["output_board_type"],
            input_board_type=path["input_board_type"],
            output_power_dbm=self.output_power_dbm.value(),
            power_sweep_enabled=self.power_sweep_enabled.isChecked(),
            power_start_gain=self.power_start_gain.value(),
            power_end_gain=self.power_end_gain.value(),
            power_start_dbm=self.power_start_dbm.value(),
            power_end_dbm=self.power_end_dbm.value(),
            power_points=self.power_points.value(),
            power_scale=str(self.power_scale.currentData()),
            acquisition_source=str(self.acquisition_source.currentData()),
            scan_time_us=self.scan_time_us.value(),
            minimum_coherent_samples=1,
            avg_repetitions=self.avg_repetitions.value(),
            avg_sweep_mode=str(self.avg_sweep_mode.currentData()),
            avg_hardware_rep_delay_us=(
                self.avg_hardware_rep_delay_us.value()
            ),
            output_att1_db=path["output_att1_db"],
            output_att2_db=path["output_att2_db"],
            output_filter_type=self.output_filter_type.currentText(),
            output_filter_cutoff_ghz=self.output_filter_cutoff_ghz.value(),
            output_filter_bandwidth_ghz=(self.output_filter_bandwidth_ghz.value()),
            readout_attenuation_db=path["readout_attenuation_db"],
            readout_dc_gain_db=path["readout_dc_gain_db"],
            readout_filter_type=self.readout_filter_type.currentText(),
            readout_filter_cutoff_ghz=self.readout_filter_cutoff_ghz.value(),
            readout_filter_bandwidth_ghz=(self.readout_filter_bandwidth_ghz.value()),
            loss1_db=path["loss1_db"],
            loss2_db=path["loss2_db"],
            amplifier_gain_db=path["amplifier_gain_db"],
            nqz=path["output_nqz"],
            readout_nqz=path["readout_nqz"],
            margin_input_samples=self.margin_input_samples.value(),
            fpga_trigger_delay_us=(
                self.fpga_trigger_delay_us.value()
                if (
                    self.acquisition_source.currentData() == "fir_ddr"
                    and
                    self.override_fpga_trigger_delay.isChecked()
                    and self._fir_uses_fpga_trigger_delay is not False
                )
                else None
            ),
            address=self.address.value(),
            stride_bytes=(
                None if self.stride_bytes.value() == 0 else self.stride_bytes.value()
            ),
            force_overwrite=self.force_overwrite.isChecked(),
            phase_display=str(self.phase_display.currentData()),
            magnitude_display=str(self.magnitude_display.currentData()),
            save_to_qcodes=self.save_to_qcodes.isChecked(),
            **self._internal_settings,
        )

    def settings_dict(self) -> Mapping[str, Any]:
        return {
            "database_path": (self.database_path_value() if self.database_path.text().strip()
                              or self.save_to_qcodes.isChecked() else ""),
            **asdict(self.config()),
        }

    def load_settings(self, settings: Mapping[str, Any]) -> None:
        values = dict(settings)
        # Older settings may contain the retired capture-floor control.
        values["minimum_coherent_samples"] = 1
        values.setdefault("acquisition_source", "fir_ddr")
        values.setdefault("avg_repetitions", 100)
        values.setdefault("avg_sweep_mode", "hardware")
        values.setdefault("avg_hardware_rep_delay_us", 0.0)
        database_path = str(
            values.pop("database_path", DEFAULT_SPARAMETER_DB_PATH)
        ).strip()
        config = SParameterSweepConfig(**values)
        if not database_path and config.save_to_qcodes:
            raise ValueError("RF S-parameter database path must not be empty")
        widgets = (
            (self.output_ch, config.output_ch),
            (self.readout_ch, config.readout_ch),
            (self.output_nqz, config.nqz),
            (self.readout_nqz, config.readout_nqz),
            (self.frequency_start_mhz, config.frequency_start_mhz),
            (self.frequency_end_mhz, config.frequency_end_mhz),
            (self.frequency_points, config.frequency_points),
            (self.gain, config.gain),
            (self.output_power_dbm, config.output_power_dbm),
            (self.power_start_gain, config.power_start_gain),
            (self.power_end_gain, config.power_end_gain),
            (self.power_start_dbm, config.power_start_dbm),
            (self.power_end_dbm, config.power_end_dbm),
            (self.power_points, config.power_points),
            (self.scan_time_us, config.scan_time_us),
            (self.avg_repetitions, config.avg_repetitions),
            (
                self.avg_hardware_rep_delay_us,
                config.avg_hardware_rep_delay_us,
            ),
            (self.output_att1_db, config.output_att1_db),
            (self.output_att2_db, config.output_att2_db),
            (self.output_filter_cutoff_ghz, config.output_filter_cutoff_ghz),
            (
                self.output_filter_bandwidth_ghz,
                config.output_filter_bandwidth_ghz,
            ),
            (self.readout_attenuation_db, config.readout_attenuation_db),
            (self.readout_dc_gain_db, config.readout_dc_gain_db),
            (self.readout_filter_cutoff_ghz, config.readout_filter_cutoff_ghz),
            (
                self.readout_filter_bandwidth_ghz,
                config.readout_filter_bandwidth_ghz,
            ),
            (self.loss1_db, config.loss1_db),
            (self.loss2_db, config.loss2_db),
            (self.amplifier_gain_db, config.amplifier_gain_db),
            (self.margin_input_samples, config.margin_input_samples),
            (self.address, config.address),
            (self.stride_bytes, config.stride_bytes or 0),
            (
                self.requested_input_calibration_run_id,
                config.requested_input_calibration_run_id,
            ),
        )
        for widget, value in widgets:
            widget.setValue(value)
        self.override_fpga_trigger_delay.setChecked(
            config.fpga_trigger_delay_us is not None
        )
        if config.fpga_trigger_delay_us is not None:
            self.fpga_trigger_delay_us.setValue(
                config.fpga_trigger_delay_us
            )
        elif self._fir_sample_rate_hz is not None:
            self.fpga_trigger_delay_us.setValue(
                self._fir_trigger_delay_us
            )
        self.output_filter_type.setCurrentText(config.output_filter_type)
        self.readout_filter_type.setCurrentText(config.readout_filter_type)
        self.calibration_database_path.setText(config.calibration_database_path)
        self.output_board_type.setCurrentText(config.output_board_type)
        self.input_board_type.setCurrentText(config.input_board_type)
        self.path_diagram._update_board_controls()
        self.path_diagram.apply_settings(emit=False)
        self.database_path.setText(database_path)
        self.save_to_qcodes.setChecked(config.save_to_qcodes)
        self.phase_display.setCurrentIndex(self.phase_display.findData(config.phase_display))
        self.magnitude_display.setCurrentIndex(self.magnitude_display.findData(config.magnitude_display))
        power_scale_index = self.power_scale.findData(config.power_scale)
        if power_scale_index < 0:
            raise ValueError(f"unsupported power scale {config.power_scale!r}")
        self.power_scale.setCurrentIndex(power_scale_index)
        source_index = self.acquisition_source.findData(config.acquisition_source)
        if source_index < 0:
            raise ValueError(
                f"unsupported acquisition source {config.acquisition_source!r}"
            )
        self.acquisition_source.setCurrentIndex(source_index)
        avg_mode_index = self.avg_sweep_mode.findData(config.avg_sweep_mode)
        if avg_mode_index < 0:
            raise ValueError(
                f"unsupported AVG sweep mode {config.avg_sweep_mode!r}"
            )
        self.avg_sweep_mode.setCurrentIndex(avg_mode_index)
        selection_index = self.input_calibration_selection.findData(
            config.input_calibration_selection
        )
        if selection_index < 0:
            raise ValueError(
                "unsupported input calibration selection "
                f"{config.input_calibration_selection!r}"
            )
        self.input_calibration_selection.setCurrentIndex(selection_index)
        self.power_calibration_enabled.setChecked(config.power_calibration_enabled)
        self.power_sweep_enabled.setChecked(config.power_sweep_enabled)
        self._update_power_control_state(config.power_sweep_enabled)
        self.force_overwrite.setChecked(config.force_overwrite)
        self._internal_settings = {
            "settle_seconds": config.settle_seconds,
            "trigger_width_tproc_cycles": config.trigger_width_tproc_cycles,
            "recovery_tproc_cycles": config.recovery_tproc_cycles,
        }
        self._update_fpga_trigger_delay_controls()
        self._update_acquisition_source_state()

    def set_running(self, running: bool, message: str) -> None:
        self.save_to_qcodes.setEnabled(not running)
        self.run_button.setEnabled(not running)
        self.load_button.setEnabled(not running)
        self.database_path.setEnabled(not running)
        self.browse_database.setEnabled(not running)
        self.power_calibration_enabled.setEnabled(not running)
        self.path_diagram.setEnabled(not running)
        self.acquisition_source.setEnabled(not running)
        uses_fir = self.acquisition_source.currentData() == "fir_ddr"
        self.avg_repetitions.setEnabled(not running and not uses_fir)
        self.avg_sweep_mode.setEnabled(not running and not uses_fir)
        self.avg_hardware_rep_delay_us.setEnabled(
            not running
            and not uses_fir
            and self.avg_sweep_mode.currentData() == "hardware"
        )
        for widget in self._fir_capture_widgets:
            widget.setEnabled(not running and uses_fir)
        self.override_fpga_trigger_delay.setEnabled(
            not running
            and uses_fir
            and self._fir_uses_fpga_trigger_delay is not False
        )
        self.fpga_trigger_delay_us.setEnabled(
            not running
            and uses_fir
            and self._fir_uses_fpga_trigger_delay is not False
            and self.override_fpga_trigger_delay.isChecked()
        )
        self.progress.setVisible(running)
        if running:
            self.progress.setValue(0)
        self.status.setText(message)

    def update_progress(self, percent: int, message: str) -> None:
        percent = max(0, min(100, int(percent)))
        self.progress.setValue(percent)
        self.status.setText(f"{percent}% - {message}")

    def show_result(self, stored) -> None:
        result = stored.result
        if stored.run_id is not None:
            self.run_id.setValue(stored.run_id)
        power_count = int(getattr(result, "power_count", 1))
        sample_rate_hz = float(
            getattr(result, "sample_rate_hz", 1_000_000.0)
        )
        trace_time_us = result.sample_count * 1_000_000.0 / sample_rate_hz
        source = getattr(result, "acquisition_source", "fir_ddr")
        if source == "avg_buffer":
            acquisition_text = (
                f"AVG buffer, {float(result.integration_time_us):g} us x "
                f"{int(result.accumulation_repetitions):,} repetitions"
            )
        else:
            acquisition_text = (
                f"{result.sample_count} FIR samples per point at "
                f"{format_sample_rate_hz(sample_rate_hz)} "
                f"({trace_time_us:g} us)"
            )
        self.set_running(
            False,
            (
                f"{'Not saved' if stored.run_id is None else f'Run {stored.run_id}'}: {power_count} power point(s) x "
                f"{result.frequencies_mhz.size} frequency points, "
                f"{acquisition_text}\n"
                f"{stored.database_path if stored.run_id is not None else 'QCoDeS saving off; result is in memory only'}"
            ),
        )

    def show_partial_result(self, stored) -> None:
        result = stored.result
        if stored.run_id is not None:
            self.run_id.setValue(stored.run_id)
        power_count = int(getattr(result, "power_count", 1))
        self.status.setText(
            (f"Run {stored.run_id}: {power_count} power point(s) saved to DB"
             if stored.run_id is not None else f"{power_count} power point(s) acquired; QCoDeS saving off")
        )


def subtract_phase_linear_fit(
    frequency_mhz: Any,
    phase_deg: Any,
    start_mhz: float,
    stop_mhz: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Subtract one least-squares phase line per trace using a selected range."""
    frequency = np.asarray(frequency_mhz, dtype=float).reshape(-1)
    phase = np.asarray(phase_deg, dtype=float)
    original_shape = phase.shape
    if phase.ndim == 1:
        rows = phase.reshape(1, -1)
    elif phase.ndim == 2:
        rows = phase
    else:
        raise ValueError("phase data must be one- or two-dimensional")
    if frequency.size != rows.shape[1]:
        raise ValueError("phase point count must match the frequency axis")
    if frequency.size < 2 or not np.all(np.isfinite(frequency)):
        raise ValueError("phase fitting requires at least two finite frequencies")
    if np.any(np.isinf(rows)):
        raise ValueError("phase data must contain finite values or NaN")
    low, high = sorted((float(start_mhz), float(stop_mhz)))
    selected = (frequency >= low) & (frequency <= high)
    if np.count_nonzero(selected) < 2:
        raise ValueError("phase fit range must contain at least two frequency points")
    corrected = np.empty_like(rows, dtype=float)
    slopes = np.empty(rows.shape[0], dtype=float)
    intercepts = np.empty(rows.shape[0], dtype=float)
    for index, values in enumerate(rows):
        usable = selected & np.isfinite(values)
        if np.count_nonzero(usable) < 2:
            raise ValueError(
                f"phase trace {index + 1} has fewer than two measurable points "
                "inside the fit range"
            )
        selected_frequency = frequency[usable]
        if np.unique(selected_frequency).size < 2:
            raise ValueError("phase fit range must contain two distinct frequencies")
        design = np.column_stack(
            (selected_frequency, np.ones(selected_frequency.size, dtype=float))
        )
        slope, intercept = np.linalg.lstsq(
            design,
            values[usable],
            rcond=None,
        )[0]
        slopes[index] = slope
        intercepts[index] = intercept
        corrected[index] = values - (slope * frequency + intercept)
    return corrected.reshape(original_shape), slopes, intercepts


def nearest_sparameter_point(
    frequency_mhz: Any,
    values: Any,
    x_mhz: float,
    y_value: float,
) -> tuple[int, int, float, float]:
    """Return the curve and point nearest to a plot-space cursor position."""
    frequency = np.asarray(frequency_mhz, dtype=float).reshape(-1)
    rows = np.asarray(values, dtype=float)
    if rows.ndim == 1:
        rows = rows.reshape(1, -1)
    if rows.ndim != 2 or rows.shape[1] != frequency.size or frequency.size == 0:
        raise ValueError("marker data must have shape (trace, frequency)")
    finite = np.isfinite(rows)
    if not np.any(finite):
        raise ValueError("marker data contains no measurable points")
    point_index = None
    for candidate in np.argsort(np.abs(frequency - float(x_mhz))):
        if np.any(finite[:, candidate]):
            point_index = int(candidate)
            break
    if point_index is None:  # pragma: no cover - guarded by np.any(finite)
        raise ValueError("marker data contains no measurable points")
    candidate_curves = np.flatnonzero(finite[:, point_index])
    nearest_candidate = int(
        np.argmin(np.abs(rows[candidate_curves, point_index] - float(y_value)))
    )
    curve_index = int(candidate_curves[nearest_candidate])
    return (
        curve_index,
        point_index,
        float(frequency[point_index]),
        float(rows[curve_index, point_index]),
    )


class _SParameterPlotMixin:
    """Shared state and controls for the PyQtGraph and Matplotlib plots."""

    def _initialize_plot_tools(self) -> None:
        self._frequency = np.empty(0, dtype=float)
        self._magnitude_values = np.empty((0, 0), dtype=float)
        self._magnitude_response_db = np.empty((0, 0), dtype=float)
        self._adc_magnitude_units = np.empty((0, 0), dtype=float)
        self._adc_magnitude_db = np.empty((0, 0), dtype=float)
        self._magnitude_mode = "response_db"
        self._phase_original = np.empty((0, 0), dtype=float)
        self._phase_display = np.empty((0, 0), dtype=float)
        self._phase_unwrapped = np.empty((0, 0), dtype=float)
        self._phase_wrapped = np.empty((0, 0), dtype=float)
        self._phase_mode = "unwrapped"
        self._curve_labels = []
        self._visible_curve_indices = np.empty(0, dtype=np.int64)
        self._physical_power_calibrated = False
        self._phase_fit_region = None
        self._phase_fit_applied = False
        self._markers_enabled = True

    def _create_control_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget(self)
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        self.power_selector = QtWidgets.QComboBox(bar)
        self.power_selector.addItem("Single sweep", 0)
        self.power_selector.setEnabled(False)
        self.power_selector.setToolTip(
            "Show all power-sweep traces or select one output power"
        )
        self.marker_button = QtWidgets.QToolButton(bar)
        self.marker_button.setText("Markers")
        self.marker_button.setCheckable(True)
        self.marker_button.setChecked(True)
        self.marker_button.setToolTip(
            "Show the nearest frequency/value marker; left-click a point to pin it"
        )
        self.clear_markers_button = QtWidgets.QToolButton(bar)
        self.clear_markers_button.setText("Clear markers")
        self.clear_markers_button.setToolTip("Remove pinned S-parameter markers")
        self.phase_range_button = QtWidgets.QToolButton(bar)
        self.phase_range_button.setText("Phase fit range")
        self.phase_range_button.setCheckable(True)
        self.phase_range_button.setToolTip(
            "Show a draggable frequency interval on the phase plot"
        )
        self.phase_subtract_button = QtWidgets.QToolButton(bar)
        self.phase_subtract_button.setText("Fit && subtract")
        self.phase_subtract_button.setToolTip(
            "Fit phase versus frequency in the selected interval and subtract it"
        )
        self.phase_reset_button = QtWidgets.QToolButton(bar)
        self.phase_reset_button.setText("Reset phase")
        self.phase_reset_button.setToolTip("Restore the measured phase in the selected display mode")
        self.plot_status = QtWidgets.QLabel("No S-parameter result loaded", bar)
        self.plot_status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        layout.addWidget(QtWidgets.QLabel("Power:", bar))
        layout.addWidget(self.power_selector)
        layout.addSpacing(8)
        layout.addWidget(self.marker_button)
        layout.addWidget(self.clear_markers_button)
        layout.addSpacing(8)
        layout.addWidget(self.phase_range_button)
        layout.addWidget(self.phase_subtract_button)
        layout.addWidget(self.phase_reset_button)
        layout.addStretch(1)
        layout.addWidget(self.plot_status)

        self.power_selector.currentIndexChanged.connect(
            self._on_power_selection_changed
        )
        self.marker_button.toggled.connect(self._set_markers_enabled)
        self.clear_markers_button.clicked.connect(self.clear_markers)
        self.phase_range_button.toggled.connect(self._set_phase_region_visible)
        self.phase_subtract_button.clicked.connect(self.subtract_phase_fit)
        self.phase_reset_button.clicked.connect(self.reset_phase)
        self._set_data_controls_enabled(False)
        return bar

    def _set_data_controls_enabled(self, enabled: bool) -> None:
        self.marker_button.setEnabled(enabled)
        self.clear_markers_button.setEnabled(enabled)
        self.phase_range_button.setEnabled(enabled and self._phase_mode == "unwrapped")
        self.phase_subtract_button.setEnabled(enabled and self._phase_mode == "unwrapped")
        self.phase_reset_button.setEnabled(enabled)

    def _set_phase_label(self) -> None:
        label = "Unwrapped phase" if self._phase_mode == "unwrapped" else "Wrapped phase"
        if hasattr(self.phase_plot, "setLabel"):
            self.phase_plot.setLabel("left", label, units="deg")
        else:
            self.phase_plot.set_ylabel(f"{label} [deg]")

    def _select_magnitude_values(self) -> None:
        if self._magnitude_mode == "response_db":
            values = self._magnitude_response_db
        elif self._magnitude_mode == "adc_db":
            values = self._adc_magnitude_db
        else:
            values = self._adc_magnitude_units
        self._magnitude_values = np.array(values, dtype=float, copy=True)
        if self._magnitude_mode == "adc_log":
            self._magnitude_values[self._magnitude_values <= 0] = np.nan

    def _set_magnitude_axis(self) -> None:
        adc_units = self._magnitude_mode in ("adc_linear", "adc_log")
        label = ("S21 (P input / P output)" if self._magnitude_mode == "response_db"
                 and self._physical_power_calibrated else "ADC magnitude")
        unit = "ADC units" if adc_units else "dB"
        log_axis = self._magnitude_mode == "adc_log"
        if _USE_PYQTGRAPH:
            self.magnitude_plot.setLabel("left", label, units=unit)
            self.magnitude_plot.setLogMode(x=False, y=log_axis)
        else:
            self.magnitude_plot.set_ylabel(f"{label} [{unit}]")
            if log_axis and not np.any(np.isfinite(self._magnitude_values)):
                self.magnitude_plot.set_ylim(0.1, 1.0)
            self.magnitude_plot.set_yscale("log" if log_axis else "linear")

    def set_magnitude_display(self, mode: str) -> None:
        if mode not in MAGNITUDE_DISPLAY_MODES:
            raise ValueError(f"magnitude display must be one of {MAGNITUDE_DISPLAY_MODES}")
        if mode == self._magnitude_mode:
            return
        self._magnitude_mode = mode
        self._select_magnitude_values()
        if self._frequency.size:
            self.clear_markers()
            self._render_curves()
            self._set_result_status()
            self.fit_view()
        else:
            self._set_magnitude_axis()

    def _nearest_plot_point(self, name, values, x, y, *, log_coordinates=False):
        """Choose by displayed distance, but always return the actual unit value."""
        shown = self._visible_values(values)
        log_axis = name == "Magnitude" and self._magnitude_mode == "adc_log"
        if log_axis:
            with np.errstate(divide="ignore", invalid="ignore"):
                coordinates = np.log10(shown)
                target_y = y if log_coordinates else (None if y is None else np.log10(y))
        else:
            coordinates, target_y = shown, y
        curve, point, frequency, _value = nearest_sparameter_point(
            self._frequency, coordinates, x, target_y
        )
        return self._original_curve_index(curve), point, frequency, float(shown[curve, point])

    def _pyqtgraph_marker_y(self, name, value):
        return np.log10(value) if name == "Magnitude" and self._magnitude_mode == "adc_log" else value

    def set_phase_display(self, mode: str) -> None:
        if mode not in ("unwrapped", "wrapped"):
            raise ValueError("phase display must be unwrapped or wrapped")
        if self._phase_mode == mode:
            return
        self._phase_mode = mode
        self._phase_original = (self._phase_unwrapped if mode == "unwrapped" else self._phase_wrapped).copy()
        self._phase_display = self._phase_original.copy()
        self._phase_fit_applied = False
        self._set_data_controls_enabled(self._frequency.size > 0)
        if mode == "wrapped":
            self.phase_range_button.setChecked(False)
        self._set_phase_label()
        if self._frequency.size:
            self.clear_markers()
            self._render_phase_values()
            self._set_result_status()

    def _load_result_arrays(self, result) -> None:
        frequency = np.asarray(result.frequencies_mhz, dtype=float).reshape(-1)
        magnitude = np.asarray(result.magnitude_db, dtype=float)
        phase = np.asarray(result.phase_unwrapped_deg, dtype=float)
        if magnitude.ndim == 1:
            magnitude = magnitude.reshape(1, -1)
            phase = phase.reshape(1, -1)
            output_power = getattr(result, "output_power_dbm", None)
            labels = [
                None if output_power is None else f"{float(output_power):.6g} dBm"
            ]
        elif magnitude.ndim == 2:
            output_powers = getattr(result, "output_powers_dbm", None)
            if output_powers is None:
                labels = [f"gain {int(gain)}" for gain in result.power_gains]
            else:
                labels = [f"{float(power):.6g} dBm" for power in output_powers]
        else:
            raise ValueError("S-parameter data must be one- or two-dimensional")
        if magnitude.shape != phase.shape or magnitude.shape[1] != frequency.size:
            raise ValueError("S-parameter magnitude/phase shapes do not match")
        self._frequency = np.ascontiguousarray(frequency)
        self._magnitude_response_db = np.ascontiguousarray(magnitude)
        if hasattr(result, "mean_i") and hasattr(result, "mean_q"):
            adc_units = np.hypot(np.asarray(result.mean_i, float), np.asarray(result.mean_q, float))
        else:
            adc_db = getattr(result, "adc_magnitude_db", None)
            if adc_db is None and not getattr(result, "physical_power_calibrated", False):
                adc_db = magnitude
            # Legacy external result objects may lack I/Q. Never interpret S21 as ADC units.
            adc_units = (np.full(magnitude.shape, np.nan) if adc_db is None else
                         np.power(10.0, np.asarray(adc_db, float) / 20.0))
        if adc_units.size != magnitude.size:
            raise ValueError("ADC magnitude shape does not match the frequency/power axes")
        self._adc_magnitude_units = np.asarray(adc_units, float).reshape(magnitude.shape).copy()
        self._adc_magnitude_units[~np.isfinite(self._adc_magnitude_units)] = np.nan
        with np.errstate(divide="ignore", invalid="ignore"):
            self._adc_magnitude_db = np.where(
                self._adc_magnitude_units > 0, 20.0 * np.log10(self._adc_magnitude_units), np.nan
            )
        self._select_magnitude_values()
        self._phase_unwrapped = np.ascontiguousarray(phase)
        wrapped = getattr(result, "phase_wrapped_deg", (phase + 180.0) % 360.0 - 180.0)
        self._phase_wrapped = np.ascontiguousarray(wrapped, dtype=float).reshape(phase.shape)
        self._phase_original = (self._phase_unwrapped if self._phase_mode == "unwrapped"
                                else self._phase_wrapped).copy()
        self._phase_display = self._phase_original.copy()
        self._curve_labels = labels
        self._physical_power_calibrated = bool(
            getattr(result, "physical_power_calibrated", False)
        )
        self._configure_power_selector()
        self._phase_fit_applied = False
        low = float(frequency[0])
        high = float(frequency[-1])
        if high < low:
            low, high = high, low
        span = high - low
        self._phase_fit_region = (
            (low + 0.25 * span, low + 0.75 * span)
            if span > 0.0
            else (low, high)
        )
        self._set_data_controls_enabled(frequency.size > 0)

    def _configure_power_selector(self) -> None:
        self.power_selector.blockSignals(True)
        self.power_selector.clear()
        curve_count = len(self._curve_labels)
        if curve_count > 1:
            self.power_selector.addItem("All powers", None)
            for index in range(curve_count):
                self.power_selector.addItem(self._curve_name(index), index)
            self.power_selector.setEnabled(True)
            self._visible_curve_indices = np.arange(curve_count, dtype=np.int64)
        else:
            label = self._curve_name(0) if curve_count else "Single sweep"
            self.power_selector.addItem(label, 0)
            self.power_selector.setEnabled(False)
            self._visible_curve_indices = np.asarray([0], dtype=np.int64)
        self.power_selector.setCurrentIndex(0)
        self.power_selector.blockSignals(False)

    def _on_power_selection_changed(self, *_args) -> None:
        if not self._curve_labels:
            return
        selected = self.power_selector.currentData()
        self._visible_curve_indices = (
            np.arange(len(self._curve_labels), dtype=np.int64)
            if selected is None
            else np.asarray([int(selected)], dtype=np.int64)
        )
        self.clear_markers()
        self._render_curves()
        self._set_result_status()
        self.fit_view()

    def _set_result_status(self) -> None:
        if self._frequency.size == 0:
            return
        if len(self._curve_labels) > 1:
            selected = self.power_selector.currentData()
            power_text = (
                f"all {len(self._curve_labels)} powers"
                if selected is None
                else self._curve_name(int(selected))
            )
            power_text = f" | {power_text}"
        else:
            power_text = ""
        visible_magnitude = self._visible_values(self._magnitude_values)
        unavailable = int(np.count_nonzero(~np.isfinite(visible_magnitude)))
        unavailable_text = (
            ""
            if unavailable == 0
            else f" | {unavailable:,} zero or unavailable point(s) cannot be shown in this scale"
        )
        self.plot_status.setText(
            f"{self._frequency.size:,} frequency points{power_text} | "
            f"hover for values; left-click to pin{unavailable_text}"
        )

    def _visible_values(self, values: np.ndarray) -> np.ndarray:
        return np.asarray(values)[self._visible_curve_indices]

    def _original_curve_index(self, visible_curve_index: int) -> int:
        return int(self._visible_curve_indices[int(visible_curve_index)])

    def _curve_name(self, curve_index: int) -> str:
        label = self._curve_labels[curve_index]
        return label if label is not None else f"trace {curve_index + 1}"

    def _marker_text(
        self,
        plot_name: str,
        curve_index: int,
        frequency: float,
        value: float,
    ) -> str:
        unit = ("ADC units" if self._magnitude_mode in ("adc_linear", "adc_log") else "dB") if plot_name == "Magnitude" else "deg"
        return (
            f"{self._curve_name(curve_index)} | {frequency:.9g} MHz | "
            f"{plot_name} {value:.9g} {unit}"
        )

    def _set_markers_enabled(self, enabled: bool) -> None:
        self._markers_enabled = bool(enabled)
        if not enabled:
            self._hide_hover_markers()

    def subtract_phase_fit(self) -> None:
        if self._frequency.size == 0 or self._phase_mode == "wrapped":
            return
        try:
            start, stop = self._phase_fit_bounds()
            corrected, slopes, _intercepts = subtract_phase_linear_fit(
                self._frequency,
                self._phase_original,
                start,
                stop,
            )
        except (TypeError, ValueError) as exc:
            self.plot_status.setText(str(exc))
            return
        self._phase_display = np.asarray(corrected, dtype=float).reshape(
            self._phase_original.shape
        )
        self._phase_fit_applied = True
        self._render_phase_values()
        slope_text = ", ".join(
            f"{self._curve_name(index)} {slope:+.6g} deg/MHz"
            for index, slope in enumerate(slopes)
            if index in self._visible_curve_indices
        )
        self.plot_status.setText(
            f"Phase line removed over {min(start, stop):.9g}.."
            f"{max(start, stop):.9g} MHz | {slope_text}"
        )

    def reset_phase(self) -> None:
        if self._frequency.size == 0:
            return
        self._phase_display = self._phase_original.copy()
        self._phase_fit_applied = False
        self._render_phase_values()
        self.plot_status.setText(f"Measured {self._phase_mode} phase restored")


if _USE_PYQTGRAPH:

    class SParameterPlotWidget(_SParameterPlotMixin, QtWidgets.QWidget):
        """Interactive magnitude and phase plots sharing one frequency axis."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self._initialize_plot_tools()
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            layout.addWidget(self._create_control_bar())
            self.graph = pg.GraphicsLayoutWidget(self)
            self.graph.setBackground("w")
            layout.addWidget(self.graph, 1)

            self.magnitude_plot = self.graph.addPlot(row=0, col=0)
            self.phase_plot = self.graph.addPlot(row=1, col=0)
            self.phase_plot.setXLink(self.magnitude_plot)
            self.magnitude_plot.showGrid(x=True, y=True, alpha=0.25)
            self.phase_plot.showGrid(x=True, y=True, alpha=0.25)
            self.magnitude_plot.setLabel("left", "Magnitude", units="dB")
            self.phase_plot.setLabel("left", "Unwrapped phase", units="deg")
            self.phase_plot.setLabel("bottom", "RF frequency", units="MHz")
            self._magnitude_legend = self.magnitude_plot.addLegend(offset=(10, 10))
            self._phase_legend = self.phase_plot.addLegend(offset=(10, 10))
            self._magnitude_curves = []
            self._phase_curves = []
            self._pinned_markers = []

            self._phase_region = pg.LinearRegionItem(
                values=(0.0, 1.0),
                orientation="vertical",
                movable=True,
                brush=pg.mkBrush(62, 126, 180, 42),
                pen=pg.mkPen(62, 126, 180, width=1.5),
            )
            self._phase_region.setZValue(20)
            self.phase_plot.addItem(self._phase_region, ignoreBounds=True)
            self._phase_region.hide()

            self._hover_items = {}
            for name, plot in (
                ("Magnitude", self.magnitude_plot),
                ("Phase", self.phase_plot),
            ):
                marker = pg.ScatterPlotItem(
                    size=11,
                    pen=pg.mkPen("#20252b", width=1.5),
                    brush=pg.mkBrush("#ffd54f"),
                )
                label = pg.TextItem(color="#20252b", anchor=(0.0, 1.0))
                marker.setZValue(40)
                label.setZValue(41)
                plot.addItem(marker, ignoreBounds=True)
                plot.addItem(label, ignoreBounds=True)
                marker.hide()
                label.hide()
                self._hover_items[name] = (marker, label)

            self._mouse_proxy = pg.SignalProxy(
                self.graph.scene().sigMouseMoved,
                rateLimit=60,
                slot=self._on_mouse_moved,
            )
            self.graph.scene().sigMouseClicked.connect(self._on_mouse_clicked)

        def _plot_at_scene_position(self, scene_position):
            for name, plot, values in (
                ("Magnitude", self.magnitude_plot, self._magnitude_values),
                ("Phase", self.phase_plot, self._phase_display),
            ):
                if plot.sceneBoundingRect().contains(scene_position):
                    view_position = plot.vb.mapSceneToView(scene_position)
                    try:
                        nearest = self._nearest_plot_point(
                            name, values, view_position.x(), view_position.y(),
                            log_coordinates=True,
                        )
                    except ValueError:
                        return None
                    return name, plot, nearest
            return None

        def _on_mouse_moved(self, event) -> None:
            if not self._markers_enabled or self._frequency.size == 0:
                return
            scene_position = event[0] if isinstance(event, tuple) else event
            nearest = self._plot_at_scene_position(scene_position)
            if nearest is None:
                self._hide_hover_markers()
                return
            name, _plot, (curve_index, _point_index, frequency, value) = nearest
            for other_name, (marker, label) in self._hover_items.items():
                visible = other_name == name
                marker.setVisible(visible)
                label.setVisible(visible)
            marker, label = self._hover_items[name]
            marker_y = self._pyqtgraph_marker_y(name, value)
            marker.setData([frequency], [marker_y])
            text = self._marker_text(name, curve_index, frequency, value)
            label.setHtml(
                "<div style='background-color:rgba(255,255,255,220);"
                "border:1px solid #68717a;padding:3px;'>"
                + text
                + "</div>"
            )
            label.setPos(frequency, marker_y)
            self.plot_status.setText(text)

        def _on_mouse_clicked(self, event) -> None:
            if (
                not self._markers_enabled
                or self._frequency.size == 0
                or event.button() != QtCore.Qt.LeftButton
            ):
                return
            nearest = self._plot_at_scene_position(event.scenePos())
            if nearest is None:
                return
            name, plot, (curve_index, _point_index, frequency, value) = nearest
            marker_y = self._pyqtgraph_marker_y(name, value)
            marker = pg.ScatterPlotItem(
                [frequency],
                [marker_y],
                size=10,
                pen=pg.mkPen("#20252b", width=1.5),
                brush=pg.mkBrush("#ff7043"),
            )
            text = self._marker_text(name, curve_index, frequency, value)
            label = pg.TextItem(color="#20252b", anchor=(0.0, 1.0))
            label.setHtml(
                "<div style='background-color:rgba(255,255,255,230);"
                "border:1px solid #d0522e;padding:3px;'>"
                + text
                + "</div>"
            )
            label.setPos(frequency, marker_y)
            marker.setZValue(35)
            label.setZValue(36)
            plot.addItem(marker, ignoreBounds=True)
            plot.addItem(label, ignoreBounds=True)
            self._pinned_markers.append((plot, marker, label))
            self.plot_status.setText(f"Pinned | {text}")

        def _hide_hover_markers(self) -> None:
            for marker, label in self._hover_items.values():
                marker.hide()
                label.hide()

        def clear_markers(self) -> None:
            for plot, marker, label in self._pinned_markers:
                plot.removeItem(marker)
                plot.removeItem(label)
            self._pinned_markers.clear()
            self._hide_hover_markers()
            if self._frequency.size:
                self.plot_status.setText("Pinned markers cleared")

        def _phase_fit_bounds(self) -> tuple[float, float]:
            return tuple(float(value) for value in self._phase_region.getRegion())

        def _set_phase_region_visible(self, visible: bool) -> None:
            if visible and self._frequency.size:
                self._phase_region.show()
            else:
                self._phase_region.hide()

        def _render_phase_values(self) -> None:
            for curve, curve_index in zip(
                self._phase_curves,
                self._visible_curve_indices,
            ):
                curve.setData(self._frequency, self._phase_display[curve_index])
            self._hide_hover_markers()
            self.phase_plot.autoRange()

        def fit_view(self) -> None:
            if self._frequency.size == 0:
                return
            self.magnitude_plot.autoRange()
            self.phase_plot.autoRange()

        def _render_curves(self) -> None:
            self._set_magnitude_axis()
            for curve in self._magnitude_curves:
                self.magnitude_plot.removeItem(curve)
            for curve in self._phase_curves:
                self.phase_plot.removeItem(curve)
            self._magnitude_curves.clear()
            self._phase_curves.clear()
            self._magnitude_legend.clear()
            self._phase_legend.clear()
            count = len(self._curve_labels)
            for curve_index in self._visible_curve_indices:
                name = self._curve_labels[curve_index]
                color = pg.intColor(curve_index, hues=max(1, count), values=1)
                self._magnitude_curves.append(
                    self.magnitude_plot.plot(
                        self._frequency,
                        self._magnitude_values[curve_index],
                        pen=pg.mkPen(color, width=2),
                        name=name,
                    )
                )
                self._phase_curves.append(
                    self.phase_plot.plot(
                        self._frequency,
                        self._phase_display[curve_index],
                        pen=pg.mkPen(color, width=2),
                        name=name,
                    )
                )

        def set_result(self, result) -> None:
            self._load_result_arrays(result)
            self.clear_markers()
            self._render_curves()
            self._set_phase_label()
            self._phase_region.setRegion(self._phase_fit_region)
            self._set_phase_region_visible(self.phase_range_button.isChecked())
            self._set_result_status()
            self.fit_view()

else:

    class SParameterPlotWidget(_SParameterPlotMixin, QtWidgets.QWidget):
        """Matplotlib fallback with the same marker and phase-fit controls."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self._initialize_plot_tools()
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            layout.addWidget(self._create_control_bar())
            self.figure = Figure(tight_layout=True)
            self.canvas = Canvas(self.figure)
            layout.addWidget(self.canvas, 1)
            self.magnitude_plot, self.phase_plot = self.figure.subplots(
                2, 1, sharex=True
            )
            self._magnitude_curves = []
            self._phase_curves = []
            self._pinned_markers = []
            self._hover_artists = {}
            self._span_selector = None
            self.canvas.mpl_connect("motion_notify_event", self._on_mouse_moved)
            self.canvas.mpl_connect("button_press_event", self._on_mouse_clicked)

        def _install_span_selector(self) -> None:
            self._span_selector = SpanSelector(
                self.phase_plot,
                self._on_phase_span,
                "horizontal",
                useblit=True,
                props={"facecolor": "tab:blue", "alpha": 0.18},
                interactive=True,
                drag_from_anywhere=True,
            )
            self._span_selector.set_active(self.phase_range_button.isChecked())
            if self._phase_fit_region is not None:
                self._span_selector.extents = self._phase_fit_region
            self._span_selector.set_visible(self.phase_range_button.isChecked())

        def _on_phase_span(self, start: float, stop: float) -> None:
            self._phase_fit_region = (float(start), float(stop))
            self.plot_status.setText(
                f"Phase fit range {min(start, stop):.9g}.."
                f"{max(start, stop):.9g} MHz"
            )

        def _phase_fit_bounds(self) -> tuple[float, float]:
            if self._phase_fit_region is None:
                raise ValueError("select a phase fit range first")
            return self._phase_fit_region

        def _set_phase_region_visible(self, visible: bool) -> None:
            if self._span_selector is not None:
                self._span_selector.set_active(bool(visible))
                self._span_selector.set_visible(bool(visible))
                self.canvas.draw_idle()

        def _render_phase_values(self) -> None:
            for curve, curve_index in zip(
                self._phase_curves,
                self._visible_curve_indices,
            ):
                curve.set_ydata(self._phase_display[curve_index])
            self.phase_plot.relim()
            self.phase_plot.autoscale_view()
            self._hide_hover_markers()
            self.canvas.draw_idle()

        def _nearest_from_event(self, event):
            if event.inaxes is self.magnitude_plot:
                name = "Magnitude"
                values = self._magnitude_values
            elif event.inaxes is self.phase_plot:
                name = "Phase"
                values = self._phase_display
            else:
                return None
            try:
                nearest = self._nearest_plot_point(name, values, event.xdata, event.ydata)
            except ValueError:
                return None
            return name, event.inaxes, nearest

        def _on_mouse_moved(self, event) -> None:
            if not self._markers_enabled or self._frequency.size == 0:
                return
            nearest = self._nearest_from_event(event)
            if nearest is None:
                self._hide_hover_markers()
                return
            name, axis, (curve_index, _point_index, frequency, value) = nearest
            self._hide_hover_markers()
            marker, annotation = self._hover_artists[name]
            marker.set_data([frequency], [value])
            annotation.xy = (frequency, value)
            annotation.set_text(
                self._marker_text(name, curve_index, frequency, value)
            )
            marker.set_visible(True)
            annotation.set_visible(True)
            self.plot_status.setText(annotation.get_text())
            axis.figure.canvas.draw_idle()

        def _on_mouse_clicked(self, event) -> None:
            if (
                not self._markers_enabled
                or self._frequency.size == 0
                or event.button != 1
            ):
                return
            nearest = self._nearest_from_event(event)
            if nearest is None:
                return
            name, axis, (curve_index, _point_index, frequency, value) = nearest
            marker = axis.plot(
                [frequency], [value], "o", color="tab:orange", zorder=20
            )[0]
            text = self._marker_text(name, curve_index, frequency, value)
            annotation = axis.annotate(
                text,
                (frequency, value),
                xytext=(8, 8),
                textcoords="offset points",
                bbox={"boxstyle": "round", "fc": "white", "alpha": 0.9},
            )
            self._pinned_markers.append((marker, annotation))
            self.plot_status.setText(f"Pinned | {text}")
            self.canvas.draw_idle()

        def _hide_hover_markers(self) -> None:
            for marker, annotation in self._hover_artists.values():
                marker.set_visible(False)
                annotation.set_visible(False)
            self.canvas.draw_idle()

        def clear_markers(self) -> None:
            for marker, annotation in self._pinned_markers:
                marker.remove()
                annotation.remove()
            self._pinned_markers.clear()
            if self._hover_artists:
                self._hide_hover_markers()
            if self._frequency.size:
                self.plot_status.setText("Pinned markers cleared")

        def fit_view(self) -> None:
            if self._frequency.size == 0:
                return
            for axis in (self.magnitude_plot, self.phase_plot):
                axis.relim()
                axis.autoscale_view()
            self.canvas.draw_idle()

        def _render_curves(self) -> None:
            if self._span_selector is not None:
                self._span_selector.disconnect_events()
            self.magnitude_plot.clear()
            self.phase_plot.clear()
            self._pinned_markers.clear()
            self._hover_artists.clear()
            for axis in (self.magnitude_plot, self.phase_plot):
                axis.grid(True, alpha=0.25)
            self._magnitude_curves = []
            self._phase_curves = []
            count = len(self._curve_labels)
            for curve_index in self._visible_curve_indices:
                label = self._curve_labels[curve_index]
                color = f"C{curve_index % max(1, min(count, 10))}"
                self._magnitude_curves.append(
                    self.magnitude_plot.plot(
                        self._frequency,
                        self._magnitude_values[curve_index],
                        "-",
                        color=color,
                        label=label,
                    )[0]
                )
                self._phase_curves.append(
                    self.phase_plot.plot(
                        self._frequency,
                        self._phase_display[curve_index],
                        "-",
                        color=color,
                        label=label,
                    )[0]
                )
            if any(
                self._curve_labels[index] is not None
                for index in self._visible_curve_indices
            ):
                self.magnitude_plot.legend()
                self.phase_plot.legend()
            self._set_magnitude_axis()
            self._set_phase_label()
            self.phase_plot.set_xlabel("RF frequency [MHz]")
            self._hover_artists = {
                "Magnitude": (
                    self.magnitude_plot.plot([], [], "o", color="gold", zorder=30)[0],
                    self.magnitude_plot.annotate(
                        "",
                        (0, 0),
                        xytext=(8, 8),
                        textcoords="offset points",
                        bbox={"boxstyle": "round", "fc": "white", "alpha": 0.9},
                    ),
                ),
                "Phase": (
                    self.phase_plot.plot([], [], "o", color="gold", zorder=30)[0],
                    self.phase_plot.annotate(
                        "",
                        (0, 0),
                        xytext=(8, 8),
                        textcoords="offset points",
                        bbox={"boxstyle": "round", "fc": "white", "alpha": 0.9},
                    ),
                ),
            }
            self._hide_hover_markers()
            self._install_span_selector()

        def set_result(self, result) -> None:
            self._load_result_arrays(result)
            self._render_curves()
            self._set_result_status()
            self.fit_view()


class SParameterSweepWorker(QtCore.QObject):
    """Run blocking QICK RF sweep and QCoDeS operations off the GUI thread."""

    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    progress_changed = QtCore.pyqtSignal(int, str)
    partial_result = QtCore.pyqtSignal(object)
    warning_raised = QtCore.pyqtSignal(str)

    def __init__(self, kwargs: Mapping[str, Any], parent=None):
        super().__init__(parent)
        self._kwargs = dict(kwargs)

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            kwargs = dict(self._kwargs)
            kwargs["progress_callback"] = self.progress_changed.emit
            kwargs["partial_callback"] = self.partial_result.emit
            kwargs["warning_callback"] = self.warning_raised.emit
            stored = run_sparameter_sweep(**kwargs)
        except Exception:
            self.failed.emit(traceback.format_exc())
            return
        self.finished.emit(stored)


class SParameterLoadWorker(QtCore.QObject):
    """Load a saved RF S-parameter run off the GUI thread."""

    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, database_path: str, run_id: int, parent=None):
        super().__init__(parent)
        self._database_path = database_path
        self._run_id = int(run_id)

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            stored = load_sparameter_run(self._database_path, self._run_id)
        except Exception:
            self.failed.emit(traceback.format_exc())
            return
        self.finished.emit(stored)


__all__ = [
    "DEFAULT_SPARAMETER_DB_PATH",
    "SParameterLoadWorker",
    "SParameterPlotWidget",
    "SParameterSweepPanel",
    "SParameterSweepWorker",
]
