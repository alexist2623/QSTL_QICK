"""Shared measurement scaling and image-color controls.

The acquisition and QCoDeS layers keep values in their canonical units.  This
module only selects a human-readable SI prefix for plots and keeps numeric
color-range editors synchronized with pyqtgraph color bars.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple

import numpy as np
from PyQt5 import QtCore, QtWidgets

try:
    import pyqtgraph as pg
except ImportError:
    pg = None


@dataclass(frozen=True)
class MeasurementDisplayScale:
    """Multiplier and label used to display one canonical measurement unit."""

    factor: float
    unit: str
    base_unit: str


_SI_DISPLAY_SCALES = {
    "V": (
        (1.0, "V"),
        (1.0e3, "mV"),
        (1.0e6, "uV"),
        (1.0e9, "nV"),
        (1.0e12, "pV"),
    ),
    "A": (
        (1.0, "A"),
        (1.0e3, "mA"),
        (1.0e6, "uA"),
        (1.0e9, "nA"),
        (1.0e12, "pA"),
        (1.0e15, "fA"),
    ),
}


def measurement_display_scale(
    values: Any,
    unit: str,
) -> MeasurementDisplayScale:
    """Choose an SI prefix that keeps the largest value near 1 to 1000."""
    base_unit = str(unit)
    scales = _SI_DISPLAY_SCALES.get(base_unit)
    if scales is None:
        return MeasurementDisplayScale(1.0, base_unit, base_unit)

    array = np.asarray(values, dtype=np.float64)
    finite = np.abs(array[np.isfinite(array)])
    reference = float(np.max(finite)) if finite.size else 0.0
    if reference == 0.0:
        return MeasurementDisplayScale(1.0, base_unit, base_unit)

    selected_factor, selected_unit = scales[-1]
    for factor, display_unit in scales:
        if reference * factor >= 1.0:
            selected_factor, selected_unit = factor, display_unit
            break
    return MeasurementDisplayScale(
        float(selected_factor),
        str(selected_unit),
        base_unit,
    )


def scale_iq_for_display(
    i_values: Any,
    q_values: Any,
    unit: str,
) -> Tuple[np.ndarray, np.ndarray, MeasurementDisplayScale]:
    """Scale I and Q together so every derived plot uses one common prefix."""
    i_array = np.asarray(i_values, dtype=np.float64)
    q_array = np.asarray(q_values, dtype=np.float64)
    if i_array.shape != q_array.shape:
        raise ValueError("I and Q display arrays must have equal shapes")
    if not np.all(np.isfinite(i_array)) or not np.all(np.isfinite(q_array)):
        raise ValueError("I and Q display arrays must be finite")
    scale = measurement_display_scale(
        np.concatenate((i_array.reshape(-1), q_array.reshape(-1))),
        unit,
    )
    return i_array * scale.factor, q_array * scale.factor, scale


class ColorRangeControl(QtWidgets.QGroupBox):
    """Compact numeric editor for one image's applied color levels."""

    levels_changed = QtCore.pyqtSignal(float, float)

    def __init__(
        self,
        title: str,
        *,
        auto: bool,
        minimum: float,
        maximum: float,
        unit: str,
        parent=None,
    ):
        super().__init__(title, parent)
        self._unit = str(unit)
        self._data_levels = (float(minimum), float(maximum))
        grid = QtWidgets.QGridLayout(self)
        grid.setContentsMargins(6, 4, 6, 4)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(2)

        self.auto_range = QtWidgets.QCheckBox("Auto from data", self)
        self.minimum = self._level_spin(minimum)
        self.maximum = self._level_spin(maximum)
        self.range_status = QtWidgets.QLabel(self)
        self.range_status.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self.range_status.setWordWrap(True)
        grid.addWidget(self.auto_range, 0, 0, 1, 4)
        grid.addWidget(QtWidgets.QLabel("Min:", self), 1, 0)
        grid.addWidget(self.minimum, 1, 1)
        grid.addWidget(QtWidgets.QLabel("Max:", self), 1, 2)
        grid.addWidget(self.maximum, 1, 3)
        grid.addWidget(self.range_status, 2, 0, 1, 4)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        self.auto_range.setChecked(bool(auto))
        self.auto_range.toggled.connect(self._auto_toggled)
        self.minimum.editingFinished.connect(self._manual_edited)
        self.maximum.editingFinished.connect(self._manual_edited)
        self._update_editable()
        self._refresh_status()

    def _level_spin(self, value: float) -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox(self)
        spin.setRange(-1.0e15, 1.0e15)
        spin.setDecimals(12)
        spin.setValue(float(value))
        spin.setKeyboardTracking(False)
        spin.setMinimumWidth(90)
        spin.setMaximumWidth(150)
        spin.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed,
        )
        if hasattr(QtWidgets.QAbstractSpinBox, "AdaptiveDecimalStepType"):
            spin.setStepType(QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        return spin

    @staticmethod
    def _format(value: float) -> str:
        return f"{float(value):.8g}"

    def _set_editor_levels(self, minimum: float, maximum: float) -> None:
        with QtCore.QSignalBlocker(self.minimum), QtCore.QSignalBlocker(
            self.maximum
        ):
            self.minimum.setValue(float(minimum))
            self.maximum.setValue(float(maximum))

    def _update_editable(self) -> None:
        manual = not self.auto_range.isChecked()
        self.minimum.setEnabled(manual)
        self.maximum.setEnabled(manual)

    def _valid_levels(self) -> Optional[Tuple[float, float]]:
        minimum = float(self.minimum.value())
        maximum = float(self.maximum.value())
        if not np.isfinite(minimum) or not np.isfinite(maximum):
            return None
        if minimum >= maximum:
            return None
        return minimum, maximum

    def _refresh_status(self) -> None:
        levels = self._valid_levels()
        if levels is None:
            self.range_status.setText("Min must be below Max")
            self.range_status.setStyleSheet("QLabel { color: #b3261e; }")
            return
        self.range_status.setStyleSheet("")
        minimum, maximum = levels
        data_minimum, data_maximum = self._data_levels
        self.range_status.setText(
            f"Applied: {self._format(minimum)} to "
            f"{self._format(maximum)} {self._unit} | "
            f"Data: {self._format(data_minimum)} to "
            f"{self._format(data_maximum)} {self._unit}"
        )

    def _emit_levels(self) -> None:
        levels = self._valid_levels()
        self._refresh_status()
        if levels is not None:
            self.levels_changed.emit(*levels)

    def _auto_toggled(self, checked: bool) -> None:
        self._update_editable()
        if checked:
            self._set_editor_levels(*self._data_levels)
        self._emit_levels()

    def _manual_edited(self) -> None:
        self._emit_levels()

    def set_unit(self, unit: str) -> None:
        self._unit = str(unit)
        self._refresh_status()

    def set_data_levels(self, minimum: float, maximum: float) -> None:
        self._data_levels = (float(minimum), float(maximum))
        if self.auto_range.isChecked():
            self._set_editor_levels(minimum, maximum)
        self._emit_levels()

    def set_manual_levels(
        self,
        minimum: float,
        maximum: float,
        *,
        emit: bool = True,
    ) -> None:
        minimum = float(minimum)
        maximum = float(maximum)
        if (
            not np.isfinite(minimum)
            or not np.isfinite(maximum)
            or minimum >= maximum
        ):
            raise ValueError("color minimum must be finite and below maximum")
        with QtCore.QSignalBlocker(self.auto_range):
            self.auto_range.setChecked(False)
        self._set_editor_levels(minimum, maximum)
        self._update_editable()
        self._refresh_status()
        if emit:
            self.levels_changed.emit(minimum, maximum)

    def levels(self) -> Tuple[float, float]:
        levels = self._valid_levels()
        if levels is None:
            raise ValueError("color minimum must be below maximum")
        return levels

    def settings_dict(self) -> dict:
        minimum, maximum = self.levels()
        return {
            "auto": self.auto_range.isChecked(),
            "minimum": minimum,
            "maximum": maximum,
        }

    def load_settings(self, settings: Mapping[str, Any]) -> None:
        with QtCore.QSignalBlocker(self.auto_range):
            self.auto_range.setChecked(bool(settings["auto"]))
        self._set_editor_levels(
            float(settings["minimum"]),
            float(settings["maximum"]),
        )
        self._update_editable()
        if self.auto_range.isChecked():
            self._set_editor_levels(*self._data_levels)
        self._emit_levels()


def attach_color_bar(
    plot,
    image,
    color_map,
    *,
    unit: str,
    levels: Tuple[float, float],
    range_control=None,
):
    """Attach a draggable color bar and optionally synchronize its editor."""
    if pg is None:
        return None
    color_bar = pg.ColorBarItem(
        values=tuple(map(float, levels)),
        width=22,
        colorMap=color_map,
        interactive=True,
        rounding=1.0e-12,
        colorMapMenu=False,
    )
    color_bar.setImageItem(image, insert_in=plot.getPlotItem())
    color_bar.setLabel("right", text=str(unit))
    color_bar.setToolTip(
        "Drag the lower or upper handle to set the color minimum or maximum. "
        "Drag between the handles to move both limits."
    )
    if range_control is not None:
        def sync_range_control(source) -> None:
            minimum, maximum = map(float, source.levels())
            if (
                np.isfinite(minimum)
                and np.isfinite(maximum)
                and minimum < maximum
            ):
                range_control.set_manual_levels(
                    minimum,
                    maximum,
                    emit=False,
                )

        color_bar.sigLevelsChanged.connect(sync_range_control)
        # Keep an explicit reference for bindings where Python callable
        # lifetime is not retained by the Qt signal connection.
        color_bar._range_control_sync_slot = sync_range_control
    return color_bar


__all__ = [
    "ColorRangeControl",
    "MeasurementDisplayScale",
    "attach_color_bar",
    "measurement_display_scale",
    "scale_iq_for_display",
]
