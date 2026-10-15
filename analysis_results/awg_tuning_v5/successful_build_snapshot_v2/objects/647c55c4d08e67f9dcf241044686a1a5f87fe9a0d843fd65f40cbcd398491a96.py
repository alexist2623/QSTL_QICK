"""Fast PyQtGraph widgets for the DC waveform editor.

The waveform plot updates existing graphics items in place.  It does not clear
and rebuild axes while dragging, and the X/Y trace widget reuses one curve.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from math import hypot
from typing import List, Optional, Sequence, Tuple

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets, sip

try:
    from .dc_waveform_core import PulseSequence
except ImportError:
    from dc_waveform_core import PulseSequence


pg.setConfigOptions(antialias=False)

TIME_UNIT_SCALE = {"ns": 1.0, "us": 1.0e-3, "ms": 1.0e-6, "s": 1.0e-9}


def _plot_color(index: int) -> QtGui.QColor:
    return QtGui.QColor(pg.intColor(index, hues=8, values=1, minValue=110, maxValue=220))


def _trace_point_records(
    pulse_x: PulseSequence,
    pulse_y: PulseSequence,
) -> Tuple[dict, ...]:
    """Return logical SET points and their per-axis timing metadata."""
    point_count = min(pulse_x.set_count, pulse_y.set_count)
    records = []
    for point_index in range(point_count):
        flat_index = 2 * point_index
        record = {
            "point_index": point_index,
            "x_segment_name": pulse_x.segment_name(point_index),
            "y_segment_name": pulse_y.segment_name(point_index),
            "x_mv": float(pulse_x.v[flat_index]),
            "y_mv": float(pulse_y.v[flat_index]),
            "hold_x_ns": float(
                pulse_x.t[flat_index + 1] - pulse_x.t[flat_index]
            ),
            "hold_y_ns": float(
                pulse_y.t[flat_index + 1] - pulse_y.t[flat_index]
            ),
            "ramp_x_ns": None,
            "ramp_y_ns": None,
        }
        if record["x_segment_name"] == record["y_segment_name"]:
            record["point_name"] = record["x_segment_name"]
        else:
            record["point_name"] = (
                f"X {record['x_segment_name']} / "
                f"Y {record['y_segment_name']}"
            )
        if point_index:
            record["ramp_x_ns"] = float(
                pulse_x.t[flat_index] - pulse_x.t[flat_index - 1]
            )
            record["ramp_y_ns"] = float(
                pulse_y.t[flat_index] - pulse_y.t[flat_index - 1]
            )
        records.append(record)
    return tuple(records)


def _duration_pair_text(
    x_ns: Optional[float],
    y_ns: Optional[float],
    unit: str,
) -> str:
    if x_ns is None or y_ns is None:
        return "initial"
    scale = TIME_UNIT_SCALE[unit]
    x_value = float(x_ns) * scale
    y_value = float(y_ns) * scale
    if np.isclose(x_value, y_value, rtol=0.0, atol=1.0e-12):
        return f"{x_value:.6g} {unit}"
    return f"X {x_value:.6g} / Y {y_value:.6g} {unit}"


class _ClickableTraceLabel(pg.TextItem):
    """Trace annotation that can be dragged and edited with a click."""

    clicked = QtCore.pyqtSignal(int)
    moved = QtCore.pyqtSignal(float, float)

    def __init__(self, segment_index: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.segment_index = int(segment_index)
        self._drag_start_position: Optional[QtCore.QPointF] = None
        self._drag_start_view_position: Optional[QtCore.QPointF] = None
        self.textItem.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self.textItem.setAcceptHoverEvents(False)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setAcceptHoverEvents(True)
        self.setCursor(QtGui.QCursor(QtCore.Qt.SizeAllCursor))

    def move_to(self, x_value: float, y_value: float) -> None:
        """Move in plot coordinates and notify the connector owner."""
        self.setPos(float(x_value), float(y_value))
        self.moved.emit(float(x_value), float(y_value))

    def hoverEvent(self, event) -> None:
        event.acceptClicks(QtCore.Qt.LeftButton)
        event.acceptDrags(QtCore.Qt.LeftButton)
        self.setCursor(QtGui.QCursor(QtCore.Qt.SizeAllCursor))

    def mouseDragEvent(self, event) -> None:
        if event.button() != QtCore.Qt.LeftButton:
            event.ignore()
            return
        view_box = self.getViewBox()
        if view_box is None:
            event.ignore()
            return
        if event.isStart():
            self._drag_start_position = QtCore.QPointF(self.pos())
            self._drag_start_view_position = view_box.mapSceneToView(
                event.buttonDownScenePos()
            )
            self.setCursor(QtGui.QCursor(QtCore.Qt.ClosedHandCursor))
        if (
            self._drag_start_position is None
            or self._drag_start_view_position is None
        ):
            event.ignore()
            return
        current_view_position = view_box.mapSceneToView(event.scenePos())
        delta = current_view_position - self._drag_start_view_position
        self.move_to(
            self._drag_start_position.x() + delta.x(),
            self._drag_start_position.y() + delta.y(),
        )
        if event.isFinish():
            self._drag_start_position = None
            self._drag_start_view_position = None
            self.setCursor(QtGui.QCursor(QtCore.Qt.SizeAllCursor))
        event.accept()

    def mouseClickEvent(self, event) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.segment_index)
            event.accept()
            return
        event.ignore()


class TracePlotWidget(pg.PlotWidget):
    """Voltage trace with point timing and a last-stability-map underlay."""

    hold_edit_requested = QtCore.pyqtSignal(int)
    ramp_edit_requested = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setBackground("w")
        self.showGrid(x=True, y=True, alpha=0.25)
        self.setLabel("bottom", "Pulse-X", units="mV")
        self.setLabel("left", "Pulse-Y", units="mV")
        self.getPlotItem().hideButtons()
        self._stability_color_map = pg.colormap.get("viridis")
        self._stability_image = pg.ImageItem(axisOrder="row-major")
        self._stability_image.setColorMap(self._stability_color_map)
        self._stability_image.setOpacity(0.52)
        self._stability_image.setZValue(-20)
        self.addItem(self._stability_image)
        self._stability_color_bar = None
        self._stability_image.hide()
        self._trace_shadow = self.plot(
            [],
            [],
            pen=pg.mkPen((20, 20, 20, 190), width=4.0),
        )
        self._trace_shadow.setZValue(8)
        self._curve = self.plot(
            [],
            [],
            pen=pg.mkPen(_plot_color(0), width=1.8),
        )
        self._curve.setZValue(9)
        point_color = _plot_color(0)
        self._point_scatter = pg.ScatterPlotItem(
            pen=pg.mkPen((20, 20, 20), width=1.2),
            brush=pg.mkBrush(point_color),
            symbolSize=6,
            hoverable=True,
            hoverBrush=pg.mkBrush(255, 215, 0),
            hoverSize=10,
            tip=self._point_tooltip,
        )
        self._point_scatter.setZValue(12)
        self.addItem(self._point_scatter)
        self._point_scatter.sigHovered.connect(self._points_hovered)
        self._point_scatter.sigClicked.connect(self._points_clicked)
        self.x_idx: Optional[int] = None
        self.y_idx: Optional[int] = None
        self._pulses: Sequence[PulseSequence] = ()
        self._time_unit = "us"
        self._point_records: Tuple[dict, ...] = ()
        self._point_labels: List[pg.TextItem] = []
        self._ramp_labels: List[pg.TextItem] = []
        self._point_connectors: List[pg.PlotCurveItem] = []
        self._ramp_connectors: List[pg.PlotCurveItem] = []
        self._trace_label_offsets = {}
        self._hover_label = pg.TextItem(
            text="",
            color=(18, 18, 18),
            anchor=(0.5, 1.0),
            border=pg.mkPen((45, 45, 45, 190)),
            fill=pg.mkBrush(255, 255, 230, 235),
        )
        self._hover_label.setZValue(20)
        self.addItem(self._hover_label, ignoreBounds=True)
        self._hover_label.hide()
        self._stability_result = None
        self._stability_quantity = "magnitude"
        self._stability_overlay_active = False
        self._stability_bounds: Optional[
            Tuple[float, float, float, float]
        ] = None
        self._default_title = "Select X/Y outputs"

    @property
    def has_selection(self) -> bool:
        return (
            self.x_idx is not None
            and self.y_idx is not None
            and self.x_idx < len(self._pulses)
            and self.y_idx < len(self._pulses)
        )

    def uses_port(self, index: int) -> bool:
        return index == self.x_idx or index == self.y_idx

    def set_time_unit(self, unit: str) -> None:
        if unit not in TIME_UNIT_SCALE:
            raise ValueError(f"unsupported trace time unit {unit!r}")
        self._time_unit = unit
        if self._pulses:
            self.refresh_trace(self._pulses)

    def _point_timing_text(self, record: dict) -> str:
        return (
            "Hold "
            + _duration_pair_text(
                record["hold_x_ns"],
                record["hold_y_ns"],
                self._time_unit,
            )
        )

    def _ramp_timing_text(self, record: dict) -> str:
        return (
            "Ramp "
            + _duration_pair_text(
                record["ramp_x_ns"],
                record["ramp_y_ns"],
                self._time_unit,
            )
        )

    def _point_tooltip(self, _x, _y, data) -> str:
        if not isinstance(data, dict):
            return ""
        return (
            f"{data['point_name']} | "
            f"X {data['x_mv']:.6g} mV | Y {data['y_mv']:.6g} mV | "
            f"{self._point_timing_text(data)}"
        )

    def _points_hovered(self, _item, points, _event) -> None:
        if len(points) > 0:
            point = points[0]
            data = point.data()
            tooltip = self._point_tooltip(
                point.pos().x(),
                point.pos().y(),
                data,
            )
            self.setTitle(tooltip)
            if isinstance(data, dict):
                self._hover_label.setText(
                    f"{data['point_name']}\n"
                    f"X {data['x_mv']:.6g} mV\n"
                    f"Y {data['y_mv']:.6g} mV\n"
                    f"{self._point_timing_text(data)}"
                )
                self._hover_label.setPos(point.pos().x(), point.pos().y())
                self._hover_label.show()
        else:
            self._hover_label.hide()
            self.setTitle(self._default_title)

    def _points_clicked(self, _item, points, event) -> None:
        if len(points) == 0:
            return
        record = points[0].data()
        if not isinstance(record, dict):
            return
        self.hold_edit_requested.emit(int(record["point_index"]))
        if event is not None:
            event.accept()

    def _clear_point_labels(self) -> None:
        for label in self._point_labels:
            self.removeItem(label)
        self._point_labels.clear()
        for label in self._ramp_labels:
            self.removeItem(label)
        self._ramp_labels.clear()
        for connector in self._point_connectors:
            self.removeItem(connector)
        self._point_connectors.clear()
        for connector in self._ramp_connectors:
            self.removeItem(connector)
        self._ramp_connectors.clear()
        self._hover_label.hide()

    def _trace_label_key(
        self,
        kind: str,
        record: dict,
        previous: Optional[dict] = None,
    ) -> tuple:
        key = (
            self.x_idx,
            self.y_idx,
            str(kind),
            record["x_segment_name"],
            record["y_segment_name"],
        )
        if previous is not None:
            key += (
                previous["x_segment_name"],
                previous["y_segment_name"],
            )
        return key

    @staticmethod
    def _trace_label_spacing(
        records: Sequence[dict],
    ) -> Tuple[float, float]:
        x_values = np.asarray([record["x_mv"] for record in records], dtype=float)
        y_values = np.asarray([record["y_mv"] for record in records], dtype=float)
        x_span = float(np.ptp(x_values)) if x_values.size else 0.0
        y_span = float(np.ptp(y_values)) if y_values.size else 0.0
        x_reference = float(np.max(np.abs(x_values))) if x_values.size else 0.0
        y_reference = float(np.max(np.abs(y_values))) if y_values.size else 0.0
        return (
            max(4.0, 0.05 * x_span, 0.01 * x_reference),
            max(4.0, 0.07 * y_span, 0.01 * y_reference),
        )

    @staticmethod
    def _inward_label_offset(
        target: Tuple[float, float],
        center: Tuple[float, float],
        x_distance: float,
        y_distance: float,
        index: int,
    ) -> Tuple[float, float]:
        fallback_x = 1.0 if index % 2 == 0 else -1.0
        fallback_y = -fallback_x
        if target[0] < center[0]:
            x_direction = 1.0
        elif target[0] > center[0]:
            x_direction = -1.0
        else:
            x_direction = fallback_x
        if target[1] < center[1]:
            y_direction = 1.0
        elif target[1] > center[1]:
            y_direction = -1.0
        else:
            y_direction = fallback_y
        return (
            x_direction * float(x_distance),
            y_direction * float(y_distance),
        )

    def _trace_label_moved(
        self,
        key: tuple,
        target: Tuple[float, float],
        label: _ClickableTraceLabel,
        connector: pg.PlotCurveItem,
        x_value: float,
        y_value: float,
    ) -> None:
        self._trace_label_offsets[key] = (
            float(x_value) - target[0],
            float(y_value) - target[1],
        )
        self._set_trace_label_anchor(
            label,
            target,
            (float(x_value), float(y_value)),
        )
        connector.setData(
            [target[0], float(x_value)],
            [target[1], float(y_value)],
        )

    @staticmethod
    def _set_trace_label_anchor(
        label: _ClickableTraceLabel,
        target: Tuple[float, float],
        label_position: Tuple[float, float],
    ) -> None:
        label.setAnchor((
            0.0 if label_position[0] >= target[0] else 1.0,
            1.0 if label_position[1] >= target[1] else 0.0,
        ))

    def _add_trace_connector(
        self,
        *,
        target: Tuple[float, float],
        label: _ClickableTraceLabel,
        label_position: Tuple[float, float],
        key: tuple,
        pen,
        connectors: List[pg.PlotCurveItem],
    ) -> None:
        connector = pg.PlotCurveItem(
            [target[0], label_position[0]],
            [target[1], label_position[1]],
            pen=pen,
        )
        connector.setZValue(13)
        self.addItem(connector, ignoreBounds=True)
        connectors.append(connector)
        self._set_trace_label_anchor(label, target, label_position)
        label.trace_target = QtCore.QPointF(*target)
        label.trace_connector = connector
        label.moved.connect(
            lambda x_value, y_value, *, _key=key, _target=target,
            _connector=connector, _label=label: self._trace_label_moved(
                _key,
                _target,
                _label,
                _connector,
                x_value,
                y_value,
            )
        )

    def _refresh_point_items(
        self,
        pulse_x: PulseSequence,
        pulse_y: PulseSequence,
    ) -> None:
        self._point_records = _trace_point_records(pulse_x, pulse_y)
        self._clear_point_labels()
        point_dx, point_dy = self._trace_label_spacing(self._point_records)
        x_values = [record["x_mv"] for record in self._point_records]
        y_values = [record["y_mv"] for record in self._point_records]
        trace_center = (
            0.5 * (min(x_values) + max(x_values)),
            0.5 * (min(y_values) + max(y_values)),
        )
        spots = []
        for record in self._point_records:
            spots.append({
                "pos": (record["x_mv"], record["y_mv"]),
                "data": record,
            })
            label = _ClickableTraceLabel(
                record["point_index"],
                text=(
                    f"{record['point_name']}\n"
                    + self._point_timing_text(record)
                ),
                color=(18, 18, 18),
                anchor=(0.0, 1.0),
                border=pg.mkPen((45, 45, 45, 150)),
                fill=pg.mkBrush(255, 255, 255, 185),
            )
            label.setToolTip(
                "Drag to reposition; click to edit X, Y, and hold duration"
            )
            label.clicked.connect(self.hold_edit_requested.emit)
            label.setZValue(14)
            point_key = self._trace_label_key("hold", record)
            point_offset = self._trace_label_offsets.get(
                point_key,
                self._inward_label_offset(
                    (record["x_mv"], record["y_mv"]),
                    trace_center,
                    point_dx,
                    point_dy,
                    record["point_index"],
                ),
            )
            point_target = (record["x_mv"], record["y_mv"])
            point_label_position = (
                point_target[0] + point_offset[0],
                point_target[1] + point_offset[1],
            )
            label.setPos(*point_label_position)
            self._add_trace_connector(
                target=point_target,
                label=label,
                label_position=point_label_position,
                key=point_key,
                pen=pg.mkPen(
                    (55, 55, 55, 185),
                    width=1.1,
                    style=QtCore.Qt.DashLine,
                ),
                connectors=self._point_connectors,
            )
            self.addItem(label, ignoreBounds=True)
            self._point_labels.append(label)
            if record["point_index"]:
                previous = self._point_records[record["point_index"] - 1]
                ramp_label = _ClickableTraceLabel(
                    record["point_index"],
                    text=self._ramp_timing_text(record),
                    color=(18, 18, 18),
                    anchor=(0.5, 1.0),
                    border=pg.mkPen((125, 90, 0, 150)),
                    fill=pg.mkBrush(255, 248, 205, 205),
                )
                ramp_label.setToolTip(
                    "Drag to reposition; click to edit ramp duration"
                )
                ramp_label.clicked.connect(self.ramp_edit_requested.emit)
                ramp_label.setZValue(15)
                ramp_target = (
                    0.5 * (previous["x_mv"] + record["x_mv"]),
                    0.5 * (previous["y_mv"] + record["y_mv"]),
                )
                ramp_key = self._trace_label_key(
                    "ramp",
                    record,
                    previous,
                )
                ramp_offset = self._trace_label_offsets.get(
                    ramp_key,
                    self._inward_label_offset(
                        ramp_target,
                        trace_center,
                        2.0 * point_dx,
                        3.2 * point_dy,
                        record["point_index"],
                    ),
                )
                ramp_label_position = (
                    ramp_target[0] + ramp_offset[0],
                    ramp_target[1] + ramp_offset[1],
                )
                ramp_label.setPos(*ramp_label_position)
                self._add_trace_connector(
                    target=ramp_target,
                    label=ramp_label,
                    label_position=ramp_label_position,
                    key=ramp_key,
                    pen=pg.mkPen(
                        (125, 90, 0, 205),
                        width=1.2,
                        style=QtCore.Qt.DashLine,
                    ),
                    connectors=self._ramp_connectors,
                )
                self.addItem(ramp_label, ignoreBounds=True)
                self._ramp_labels.append(ramp_label)
        self._point_scatter.setData(spots)

    @staticmethod
    def _axis_edges(values: np.ndarray) -> Tuple[float, float]:
        values = np.asarray(values, dtype=float)
        if values.size == 1:
            return float(values[0] - 0.5), float(values[0] + 0.5)
        step = float(np.median(np.diff(values)))
        return float(values[0] - step / 2.0), float(values[-1] + step / 2.0)

    @staticmethod
    def _finite_levels(values: np.ndarray) -> Tuple[float, float]:
        finite = np.asarray(values, dtype=float)
        finite = finite[np.isfinite(finite)]
        if finite.size == 0:
            return 0.0, 1.0
        low = float(np.min(finite))
        high = float(np.max(finite))
        if np.isclose(low, high):
            delta = max(1.0, abs(low) * 0.01)
            low -= delta
            high += delta
        return low, high

    def set_stability_overlay(self, result, quantity: str = "magnitude") -> None:
        """Show one selected Stability Diagram quantity below the trace."""
        if quantity not in {"i", "q", "magnitude", "phase"}:
            raise ValueError(f"unsupported Stability overlay data {quantity!r}")
        self._stability_result = result
        self._stability_quantity = quantity
        self._refresh_stability_overlay()

    def _stability_values(self, result) -> Tuple[np.ndarray, str, str]:
        if self._stability_quantity == "i":
            return np.asarray(result.i_mean, dtype=float), "I", result.value_unit
        if self._stability_quantity == "q":
            return np.asarray(result.q_mean, dtype=float), "Q", result.value_unit
        if self._stability_quantity == "phase":
            return (
                np.asarray(result.phase_deg, dtype=float),
                "Phase",
                "deg",
            )
        return (
            np.asarray(result.magnitude, dtype=float),
            "Magnitude",
            result.value_unit,
        )

    def _refresh_stability_overlay(self) -> None:
        self._stability_overlay_active = False
        self._stability_bounds = None
        self._stability_image.hide()
        result = self._stability_result
        if result is None:
            self._default_title = (
                "Click a P#/Hold or Ramp label to edit segment values"
            )
            self.setTitle(self._default_title)
            return
        if not self.has_selection:
            self._default_title = "Select X/Y outputs to overlay the last stability scan"
            self.setTitle(self._default_title)
            return

        trace_axes = (f"awg_{self.x_idx}", f"awg_{self.y_idx}")
        result_axes = (str(result.x_axis_label), str(result.y_axis_label))
        overlay, quantity_label, quantity_unit = self._stability_values(result)
        if result_axes == trace_axes:
            x_values = np.asarray(result.x_voltage_mv, dtype=float)
            y_values = np.asarray(result.y_voltage_mv, dtype=float)
        elif result_axes == trace_axes[::-1]:
            x_values = np.asarray(result.y_voltage_mv, dtype=float)
            y_values = np.asarray(result.x_voltage_mv, dtype=float)
            overlay = overlay.T
        else:
            self._default_title = (
                "Last stability scan axes "
                f"{result_axes[0]}/{result_axes[1]} do not match "
                f"{trace_axes[0]}/{trace_axes[1]}"
            )
            self.setTitle(self._default_title)
            return

        x_low, x_high = self._axis_edges(x_values)
        y_low, y_high = self._axis_edges(y_values)
        self._stability_image.setImage(overlay, autoLevels=False)
        self._stability_image.setRect(
            QtCore.QRectF(
                x_low,
                y_low,
                x_high - x_low,
                y_high - y_low,
            )
        )
        levels = self._finite_levels(overlay)
        self._stability_image.setLevels(levels)
        self._stability_image.show()
        self._stability_overlay_active = True
        self._stability_bounds = (x_low, x_high, y_low, y_high)
        source_label = (
            str(getattr(result, "source_label", "")).strip()
            or f"Stability scan {result.iteration}"
        )
        self._default_title = (
            f"Trace over {source_label} {quantity_label} [{quantity_unit}]"
        )
        self.setTitle(self._default_title)

    def refresh_trace(self, pulses: Sequence[PulseSequence]) -> None:
        """Update the existing curve; interpolation runs only when X/Y exist."""
        self._pulses = pulses
        if not self.has_selection:
            self._trace_shadow.setData([], [])
            self._curve.setData([], [])
            self._point_scatter.setData([])
            self._clear_point_labels()
            self._refresh_stability_overlay()
            return
        pulse_x = pulses[self.x_idx]
        pulse_y = pulses[self.y_idx]
        time_union = np.union1d(pulse_x.t, pulse_y.t)
        voltage_x = np.interp(time_union, pulse_x.t, pulse_x.v)
        voltage_y = np.interp(time_union, pulse_y.t, pulse_y.v)
        self._trace_shadow.setData(voltage_x, voltage_y)
        self._curve.setData(voltage_x, voltage_y)
        self._refresh_point_items(pulse_x, pulse_y)
        self.setLabel("bottom", f"Pulse {self.x_idx + 1}", units="mV")
        self.setLabel("left", f"Pulse {self.y_idx + 1}", units="mV")
        self._refresh_stability_overlay()

    def fit_view(self) -> None:
        if not self.has_selection:
            return
        if (
            self._stability_overlay_active
            and self._stability_bounds is not None
        ):
            x_low, x_high, y_low, y_high = self._stability_bounds
            self.setXRange(x_low, x_high, padding=0.0)
            self.setYRange(y_low, y_high, padding=0.0)
            return
        self.getPlotItem().autoRange(padding=0.08)


class RfPulsePreviewWidget(pg.PlotWidget):
    """Preview a DDS RF pulse without rendering every RF sample.

    Short pulses use a bounded number of representative carrier points.  Long
    or high-frequency pulses use a six-point amplitude envelope, which keeps
    interactive edits independent of the underlying RF sample count.
    """

    MAX_CARRIER_CYCLES = 32.0
    MAX_CARRIER_POINTS = 768

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setBackground("w")
        self.showGrid(x=True, y=True, alpha=0.25)
        self.setLabel("bottom", "sequence time", units="us")
        self.setLabel("left", "DAC code (pre-attenuation)")
        self.getPlotItem().hideButtons()
        self.getPlotItem().setMenuEnabled(False)
        color = _plot_color(1)
        self._carrier_curve = self.plot([], [], pen=pg.mkPen(color, width=1.4))
        # Keep the previous attribute as an alias for callers which inspect the
        # preview curve in tests or notebooks.
        self._curve = self._carrier_curve
        self._upper_curve = self.plot([], [], pen=pg.mkPen(color, width=1.0))
        self._lower_curve = self.plot([], [], pen=pg.mkPen(color, width=1.0))
        self._envelope_fill = pg.FillBetweenItem(
            self._upper_curve,
            self._lower_curve,
            brush=pg.mkBrush(color.red(), color.green(), color.blue(), 42),
        )
        self.addItem(self._envelope_fill)
        self._start_line = pg.InfiniteLine(angle=90, pen=pg.mkPen(color, style=QtCore.Qt.DashLine))
        self._end_line = pg.InfiniteLine(angle=90, pen=pg.mkPen(color, style=QtCore.Qt.DashLine))
        self.addItem(self._start_line)
        self.addItem(self._end_line)
        self._start_line.hide()
        self._end_line.hide()
        self.preview_mode = "empty"

    def clear_preview(self) -> None:
        self._carrier_curve.setData([], [])
        self._upper_curve.setData([], [])
        self._lower_curve.setData([], [])
        self._start_line.hide()
        self._end_line.hide()
        self.setTitle("")
        self.preview_mode = "empty"

    def set_pulse(
        self,
        *,
        start_us: float,
        duration_us: float,
        frequency_mhz: float,
        gain: int,
        phase_degrees: float,
        att1_db: float,
        att2_db: float,
    ) -> None:
        end_us = start_us + duration_us
        padding = max(0.02, duration_us * 0.08)
        cycle_count = abs(frequency_mhz) * duration_us
        if cycle_count <= self.MAX_CARRIER_CYCLES:
            points = min(
                self.MAX_CARRIER_POINTS,
                max(64, int(cycle_count * 16) + 2),
            )
            pulse_time = np.linspace(start_us, end_us, points, dtype=float)
            phase = np.deg2rad(phase_degrees)
            pulse_values = float(gain) * np.cos(
                2.0 * np.pi * frequency_mhz * (pulse_time - start_us) + phase
            )
            time_us = np.concatenate(
                ([start_us - padding, start_us], pulse_time, [end_us, end_us + padding])
            )
            values = np.concatenate(([0.0, 0.0], pulse_values, [0.0, 0.0]))
            self._carrier_curve.setData(time_us, values)
            self._upper_curve.setData([], [])
            self._lower_curve.setData([], [])
            self.preview_mode = "carrier"
            mode_text = f"representative carrier ({points} points)"
        else:
            amplitude = abs(float(gain))
            envelope_time = np.asarray(
                [
                    start_us - padding,
                    start_us,
                    start_us,
                    end_us,
                    end_us,
                    end_us + padding,
                ],
                dtype=float,
            )
            upper = np.asarray([0.0, 0.0, amplitude, amplitude, 0.0, 0.0])
            lower = -upper
            self._carrier_curve.setData([], [])
            self._upper_curve.setData(envelope_time, upper)
            self._lower_curve.setData(envelope_time, lower)
            self.preview_mode = "envelope"
            mode_text = "amplitude envelope"
        self._start_line.setPos(start_us)
        self._end_line.setPos(end_us)
        self._start_line.show()
        self._end_line.show()
        self.setTitle(
            f"{frequency_mhz:.6g} MHz, gain {gain}, "
            f"ATT1 {att1_db:.2f} dB, ATT2 {att2_db:.2f} dB - {mode_text}"
        )
        y_limit = max(1.0, abs(float(gain)) * 1.08)
        self.setXRange(start_us - padding, end_us + padding, padding=0.0)
        self.setYRange(-y_limit, y_limit, padding=0.0)


class RfPulseTimelineWidget(pg.PlotWidget):
    """One RF-generator lane containing every pulse on a shared time axis."""

    MAX_CARRIER_CYCLES = RfPulsePreviewWidget.MAX_CARRIER_CYCLES
    MAX_CARRIER_POINTS = RfPulsePreviewWidget.MAX_CARRIER_POINTS

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setBackground("w")
        self.showGrid(x=True, y=True, alpha=0.2)
        self.setLabel("bottom", "sequence time", units="ns")
        self.setLabel("left", "RF DAC code")
        self.getPlotItem().hideButtons()
        self.getPlotItem().setMenuEnabled(False)
        self.setMouseEnabled(x=True, y=False)
        self.setMinimumHeight(120)
        self.setMaximumHeight(260)

        self._pulse_graphics = []
        self._pulse_labels = []
        self.pulse_names = ()
        self.preview_mode = "empty"
        self._time_unit = "ns"
        self.start_ns = 0.0
        self.end_ns = 0.0
        self.clear_pulse()

    def set_time_unit(self, unit: str) -> None:
        if unit not in TIME_UNIT_SCALE:
            raise ValueError(f"unsupported time unit {unit!r}")
        self._time_unit = unit
        axis = self.getPlotItem().getAxis("bottom")
        axis.enableAutoSIPrefix(False)
        axis.setScale(TIME_UNIT_SCALE[unit])
        axis.setLabel(f"sequence time [{unit}]")

    def clear_pulse(self) -> None:
        for item in reversed(self._pulse_graphics):
            self.removeItem(item)
        self._pulse_graphics.clear()
        self._pulse_labels.clear()
        self.pulse_names = ()
        self.setTitle("")
        self.preview_mode = "empty"

    def _add_graphic(self, item) -> None:
        self.addItem(item)
        self._pulse_graphics.append(item)

    def set_pulses(
        self,
        *,
        gen_ch: int,
        pulses: Sequence[dict],
        att1_db: float,
        att2_db: float,
    ) -> None:
        """Render an ordered RF sequence in one generator timeline.

        Delay entries are already represented by gaps between ``start_ns``
        values. Pulse names are drawn inside their corresponding envelopes, and
        repeated names use the same color (for example, every ``X`` pulse).
        """
        self.clear_pulse()
        if not pulses:
            return

        normalized = tuple(dict(pulse) for pulse in pulses)
        self.start_ns = min(float(pulse["start_ns"]) for pulse in normalized)
        self.end_ns = max(
            float(pulse["start_ns"]) + float(pulse["duration_ns"])
            for pulse in normalized
        )
        max_amplitude = max(
            1.0,
            *(abs(float(pulse["gain"])) for pulse in normalized),
        )
        color = _plot_color(6)
        modes = []
        names = []

        for pulse_index, pulse in enumerate(normalized):
            name = str(pulse.get("pulse_name", "")).strip()
            if not name:
                name = f"pulse_{pulse_index}"
            names.append(name)

            start_ns = float(pulse["start_ns"])
            duration_ns = float(pulse["duration_ns"])
            end_ns = start_ns + duration_ns
            frequency_mhz = float(pulse["frequency_mhz"])
            gain = int(pulse["gain"])
            phase_degrees = float(pulse["phase_degrees"])
            cycle_count = abs(frequency_mhz) * duration_ns / 1000.0

            if cycle_count <= self.MAX_CARRIER_CYCLES:
                points = min(
                    self.MAX_CARRIER_POINTS,
                    max(64, int(cycle_count * 16) + 2),
                )
                pulse_time = np.linspace(start_ns, end_ns, points, dtype=float)
                phase = np.deg2rad(phase_degrees)
                pulse_values = float(gain) * np.cos(
                    2.0
                    * np.pi
                    * frequency_mhz
                    * (pulse_time - start_ns)
                    / 1000.0
                    + phase
                )
                time_ns = np.concatenate(
                    ([start_ns, start_ns], pulse_time, [end_ns, end_ns])
                )
                values = np.concatenate(
                    ([0.0, 0.0], pulse_values, [0.0, 0.0])
                )
                curve = pg.PlotDataItem(
                    time_ns,
                    values,
                    pen=pg.mkPen(color, width=1.2),
                )
                self._add_graphic(curve)
                modes.append("carrier")
            else:
                amplitude = abs(float(gain))
                envelope_time = np.asarray(
                    [start_ns, start_ns, end_ns, end_ns],
                    dtype=float,
                )
                upper = np.asarray([0.0, amplitude, amplitude, 0.0])
                lower = -upper
                upper_curve = pg.PlotDataItem(
                    envelope_time,
                    upper,
                    pen=pg.mkPen(color, width=1.0),
                )
                lower_curve = pg.PlotDataItem(
                    envelope_time,
                    lower,
                    pen=pg.mkPen(color, width=1.0),
                )
                fill = pg.FillBetweenItem(
                    upper_curve,
                    lower_curve,
                    brush=pg.mkBrush(
                        color.red(), color.green(), color.blue(), 34
                    ),
                )
                self._add_graphic(upper_curve)
                self._add_graphic(lower_curve)
                self._add_graphic(fill)
                modes.append("envelope")

            label = pg.TextItem(
                text=name,
                color=color,
                anchor=(0.5, 0.5),
                fill=pg.mkBrush(255, 255, 255, 220),
                border=pg.mkPen(color, width=1.0),
            )
            label.textItem.document().setDocumentMargin(1.0)
            label.setPos((start_ns + end_ns) / 2.0, 0.0)
            label.setZValue(20)
            label.setToolTip(
                f"{name}: {frequency_mhz:.6g} MHz, gain {gain}, "
                f"phase {phase_degrees:.6g} deg"
            )
            self._add_graphic(label)
            self._pulse_labels.append(label)

        self.pulse_names = tuple(names)
        unique_modes = set(modes)
        self.preview_mode = (
            next(iter(unique_modes)) if len(unique_modes) == 1 else "mixed"
        )
        self.setTitle(
            f"RF gen {gen_ch}: {len(normalized)} pulse(s), "
            f"ATT1/ATT2 {att1_db:.2f}/{att2_db:.2f} dB"
        )
        self.setYRange(
            -max_amplitude * 1.12,
            max_amplitude * 1.35,
            padding=0.0,
        )

    def set_pulse(
        self,
        *,
        gen_ch: int,
        pulse_name: str = "",
        start_ns: float,
        duration_ns: float,
        frequency_mhz: float,
        gain: int,
        phase_degrees: float,
        att1_db: float,
        att2_db: float,
    ) -> None:
        self.set_pulses(
            gen_ch=gen_ch,
            pulses=(
                {
                    "pulse_name": pulse_name,
                    "start_ns": start_ns,
                    "duration_ns": duration_ns,
                    "frequency_mhz": frequency_mhz,
                    "gain": gain,
                    "phase_degrees": phase_degrees,
                },
            ),
            att1_db=att1_db,
            att2_db=att2_db,
        )


class _WaveformTimeAxis(pg.AxisItem):
    """Keep nearby timestamps distinct when zoomed into a late pulse."""

    def tickStrings(self, values, scale, spacing):
        if self.logMode:
            return super().tickStrings(values, scale, spacing)
        # AxisItem's default %g format only keeps six significant digits for
        # large values, so separate ticks can all read e.g. '1e+09'. Precision
        # must follow tick spacing even when the absolute timestamp is large.
        places = max(0, int(np.ceil(-np.log10(spacing * scale))))
        return [f"{value * scale:.{places}f}" for value in values]


class AcquisitionTimelineWidget(pg.PlotWidget):
    """FIR input measurement coverage on the AWG time axis."""

    def __init__(self, parent=None):
        super().__init__(parent=parent, axisItems={
            "bottom": _WaveformTimeAxis(orientation="bottom")})
        self.setBackground("w")
        self.showGrid(x=True, y=False, alpha=0.2)
        self.setMouseEnabled(x=True, y=False)
        self.getPlotItem().hideButtons()
        self.getPlotItem().setMenuEnabled(False)
        self.getPlotItem().hideAxis("left")
        self.setMinimumHeight(165)
        self.setMaximumHeight(260)
        self.window = None
        self._time_unit = "us"
        self._graphics = []
        self.getPlotItem().vb.sigXRangeChanged.connect(self._refresh_units)
        self.setYRange(.5, 1.5, padding=0)
        self.setLabel("bottom", "sequence time [us]")

    def set_time_unit(self, _unit):
        self._refresh_units()

    def set_window(self, window=None, *, message=""):
        for item in self._graphics:
            self.removeItem(item)
        self._graphics.clear()
        self.window = window
        self.setTitle("Acquisition", color="#174f63", size="10pt")
        if window is None:
            self.start_ns = self.end_ns = 0.0
            self.setToolTip(message)
            return
        self.start_ns = window["input_start_us"] * 1000
        self.end_ns = window["input_end_us"] * 1000
        bar = pg.BarGraphItem(
            x0=[window["input_start_us"] * 1000],
            x1=[window["input_end_us"] * 1000], y0=[.85], height=[.3],
            brush=pg.mkBrush(20, 135, 165, 115), pen=pg.mkPen(20, 135, 165, width=1.4))
        self.addItem(bar)
        self._graphics.append(bar)
        self.setYRange(.5, 1.5, padding=0)
        self._refresh_units()

    def _refresh_units(self, *_args):
        bounds = self.getPlotItem().vb.viewRange()[0]
        span = abs(bounds[1] - bounds[0])
        self._time_unit = "ns"
        for unit, scale in TIME_UNIT_SCALE.items():
            if span * scale >= 1:
                self._time_unit = unit
        axis = self.getPlotItem().getAxis("bottom")
        axis.enableAutoSIPrefix(False)
        axis.setScale(TIME_UNIT_SCALE[self._time_unit])
        axis.setLabel(f"sequence time [{self._time_unit}]", units="")
        if self.window is not None:
            data = self.window
            scale = 1000 * TIME_UNIT_SCALE[self._time_unit]
            tooltip = (
                f"{data['input_start_us'] * scale:.6g}–{data['input_end_us'] * scale:.6g} "
                f"{self._time_unit} ({data['duration_us'] * scale:.6g} {self._time_unit})")
            self.setToolTip(tooltip)
            for item in self._graphics:
                item.setToolTip(tooltip)


class WaveformPlotWidget(pg.PlotWidget):
    """Interactive multi-output waveform editor backed by PyQtGraph."""

    flat_moved = QtCore.pyqtSignal(int, int, float)
    point_moved = QtCore.pyqtSignal(int, int, float)

    def __init__(self, pulse: PulseSequence, parent=None):
        super().__init__(parent=parent, axisItems={
            "bottom": _WaveformTimeAxis(orientation="bottom"),
        })
        self.setBackground("w")
        self.showGrid(x=True, y=True, alpha=0.25)
        self.setLabel("bottom", "time [ns]")
        self.setLabel("left", "voltage", units="mV")
        self.getPlotItem().hideButtons()
        self.getPlotItem().setMenuEnabled(False)
        self.setMouseEnabled(x=True, y=True)

        self._pulses: List[PulseSequence] = [pulse]
        # Preserve the old attribute names used by MainWindow while switching
        # their contents from Matplotlib lines to PlotDataItem objects.
        self._pulse = self._pulses
        self._line: List[pg.PlotDataItem] = []
        self._physical_line: List[pg.PlotDataItem] = []
        self._rc_line: List[pg.PlotDataItem] = []
        self._rc_time_ns = np.asarray([], dtype=float)
        self._rc_values_mv = np.empty((0, 0), dtype=float)
        self._orig_colors: List[QtGui.QColor] = []
        self._selected_port_idx = 0
        self._default_width = 1.5
        self._highlight_width = 2.8
        self._physical_width = 1.6
        self._voltage_view = "both"
        self._time_unit = "ns"
        self._physical_time_ns = np.asarray([], dtype=float)
        self._physical_values_mv = np.empty((0, 0), dtype=float)
        self._virtual_preview = None
        self._drag_flat: Optional[Tuple[int, int]] = None
        self._drag_point: Optional[Tuple[int, int]] = None
        self._grid_time_ns = 10.0
        self._grid_voltage_mv = 10.0
        self._grid_snap_enabled = False
        self._grid_visible = True
        self._sweep_port_index: Optional[int] = None
        self._sweep_time_ns = np.asarray([], dtype=float)
        self._sweep_lower_mv = np.asarray([], dtype=float)
        self._sweep_upper_mv = np.asarray([], dtype=float)

        sweep_color = _plot_color(0)
        self._sweep_lower_curve = self.plot(
            [],
            [],
            pen=pg.mkPen(sweep_color, width=1.0, style=QtCore.Qt.DotLine),
        )
        self._sweep_upper_curve = self.plot(
            [],
            [],
            pen=pg.mkPen(sweep_color, width=1.0, style=QtCore.Qt.DotLine),
        )
        self._sweep_fill = pg.FillBetweenItem(
            self._sweep_upper_curve,
            self._sweep_lower_curve,
            brush=pg.mkBrush(
                sweep_color.red(),
                sweep_color.green(),
                sweep_color.blue(),
                24,
            ),
        )
        self.addItem(self._sweep_fill)
        self._sweep_fill.setZValue(0.1)
        self._sweep_lower_curve.setZValue(0.8)
        self._sweep_upper_curve.setZValue(0.8)
        self._sweep_graphics = {}

        self._annotation = pg.TextItem(
            text="",
            color=QtGui.QColor("black"),
            fill=pg.mkBrush(255, 255, 255, 225),
            border=pg.mkPen(120, 120, 120),
            anchor=(0.0, 1.0),
        )
        self.addItem(self._annotation, ignoreBounds=True)
        self._annotation.hide()

        self._append_curve(pulse)
        self.set_physical_waveforms(pulse.t, np.asarray([pulse.v]))
        # QAbstractScrollArea delivers pointer events through its viewport.
        # Filtering it makes drag editing deterministic across Qt/PyQtGraph
        # versions while unhandled events still reach the normal pan/zoom path.
        self.viewport().installEventFilter(self)
        self.getPlotItem().vb.sigRangeChanged.connect(self._refresh_grid_tick_spacing)
        self.set_grid(
            time_step_ns=self._grid_time_ns,
            voltage_step_mv=self._grid_voltage_mv,
            snap_enabled=self._grid_snap_enabled,
            visible=self._grid_visible,
        )
        self.fit_view()

    def set_time_unit(self, unit: str) -> None:
        """Refresh after an editor-unit change; this plot scales with its view.

        MainWindow still sends the input controls' unit here. Keep the plot's
        automatic display independent of that setting and of the stored ns data.
        """
        if unit not in TIME_UNIT_SCALE:
            raise ValueError(f"unsupported time unit {unit!r}")
        self._refresh_grid_tick_spacing()

    def _refresh_time_axis_unit(self) -> None:
        lower, upper = self.getPlotItem().vb.viewRange()[0]
        span_ns = upper - lower
        if not np.isfinite(span_ns) or span_ns <= 0:
            return
        # Use the visible span, not its absolute timestamp: zooming into a late
        # pulse must expose small time differences just as it does near zero.
        unit = "ns"
        for candidate, scale in TIME_UNIT_SCALE.items():
            if span_ns * scale >= 1.0:
                unit = candidate
        if unit == self._time_unit:
            return
        self._time_unit = unit
        axis = self.getPlotItem().getAxis("bottom")
        axis.enableAutoSIPrefix(False)
        axis.setScale(TIME_UNIT_SCALE[unit])
        axis.setLabel(f"time [{unit}]", units="")

    @staticmethod
    def _nearest_grid_value(value: float, step: float) -> float:
        """Round to a zero-anchored grid, with half steps away from zero."""
        scaled = value / step
        if scaled >= 0.0:
            return float(np.floor(scaled + 0.5) * step)
        return float(np.ceil(scaled - 0.5) * step)

    def set_grid(
        self,
        *,
        time_step_ns: float,
        voltage_step_mv: float,
        snap_enabled: bool,
        visible: bool,
    ) -> None:
        """Set drag snapping and grid visibility independently of axis ticks."""
        if not np.isfinite(time_step_ns) or time_step_ns <= 0.0:
            raise ValueError("time grid spacing must be a positive finite value")
        if not np.isfinite(voltage_step_mv) or voltage_step_mv <= 0.0:
            raise ValueError("voltage grid spacing must be a positive finite value")
        self._grid_time_ns = float(time_step_ns)
        self._grid_voltage_mv = float(voltage_step_mv)
        self._grid_snap_enabled = bool(snap_enabled)
        self._grid_visible = bool(visible)
        self._refresh_grid_tick_spacing()
        self.showGrid(x=self._grid_visible, y=self._grid_visible, alpha=0.25)

    def _refresh_grid_tick_spacing(self, *_args) -> None:
        self._refresh_time_axis_unit()
        # AxisItem chooses ticks from the visible range and display scale.
        # Snapping remains anchored to the user grid, independently of zoom.
        # In particular, time ticks must not treat internal ns as displayed us.
        for name in ("bottom", "left"):
            axis = self.getPlotItem().getAxis(name)
            axis.enableAutoSIPrefix(False)
            axis.setTickSpacing()

    @property
    def grid_settings(self) -> Tuple[float, float, bool, bool]:
        return (
            self._grid_time_ns,
            self._grid_voltage_mv,
            self._grid_snap_enabled,
            self._grid_visible,
        )

    def _snap_voltage(self, value: float, pulse: PulseSequence) -> float:
        value = float(np.clip(value, pulse.v_bounds[0], pulse.v_bounds[1]))
        if not self._grid_snap_enabled:
            return value
        lower = np.ceil(pulse.v_bounds[0] / self._grid_voltage_mv) * self._grid_voltage_mv
        upper = np.floor(pulse.v_bounds[1] / self._grid_voltage_mv) * self._grid_voltage_mv
        return float(
            np.clip(
                self._nearest_grid_value(value, self._grid_voltage_mv),
                lower,
                upper,
            )
        )

    def _snap_time(self, value: float, pulse: PulseSequence, point_index: int) -> float:
        if not self._grid_snap_enabled or point_index == 0:
            return value
        snapped = self._nearest_grid_value(value, self._grid_time_ns)
        minimum = np.nextafter(float(pulse.t[point_index - 1]), np.inf)
        if snapped < minimum:
            snapped = float(np.ceil(minimum / self._grid_time_ns) * self._grid_time_ns)
        return snapped

    def _append_curve(self, pulse: PulseSequence) -> None:
        index = len(self._line)
        color = _plot_color(index)
        physical_curve = self.plot(
            pulse.t,
            pulse.v,
            pen=pg.mkPen(
                color,
                width=self._physical_width,
                style=QtCore.Qt.DashLine,
            ),
        )
        physical_curve.setZValue(index + 0.5)
        curve = self.plot(
            pulse.t,
            pulse.v,
            pen=pg.mkPen(color, width=self._default_width),
            symbol="o",
            symbolSize=7,
            symbolPen=pg.mkPen(color),
            symbolBrush=pg.mkBrush(color),
        )
        curve.setZValue(index + 1)
        curve.setVisible(self._voltage_view in {"both", "virtual"})
        physical_curve.setVisible(self._voltage_view in {"both", "physical"})
        self._physical_line.append(physical_curve)
        self._line.append(curve)
        self._orig_colors.append(color)

    def line_color(self, index: int) -> QtGui.QColor:
        return QtGui.QColor(self._orig_colors[index])

    @property
    def voltage_view(self) -> str:
        return self._voltage_view

    def set_physical_waveforms(
        self,
        time_ns: Sequence[float],
        waveforms_mv,
    ) -> None:
        """Update dashed physical-AWG traces on a common time grid."""
        time_values = np.asarray(time_ns, dtype=float)
        waveform_values = np.asarray(waveforms_mv, dtype=float)
        expected_shape = (len(self._pulses), time_values.size)
        if time_values.ndim != 1 or waveform_values.shape != expected_shape:
            raise ValueError(
                "physical waveforms must have shape "
                f"{expected_shape}, received {waveform_values.shape}"
            )
        self._physical_time_ns = time_values.copy()
        self._physical_values_mv = waveform_values.copy()
        for index, curve in enumerate(self._physical_line):
            curve.setData(time_values, waveform_values[index])

    def set_virtual_preview(self, time_ns=None, waveforms_mv=None) -> None:
        """Show a sweep point without changing the editable base waveform."""
        # Deferred physical-waveform updates call this during a base-waveform
        # drag. Only a real preview transition should cancel that edit.
        if time_ns is not None or self._virtual_preview is not None:
            self._finish_drag()
        if time_ns is None:
            self._virtual_preview = None
        else:
            times = np.asarray(time_ns, dtype=float)
            values = np.asarray(waveforms_mv, dtype=float)
            if times.ndim != 1 or values.shape != (len(self._pulses), times.size):
                raise ValueError("virtual preview must match the output count and time grid")
            self._virtual_preview = (times.copy(), values.copy())
        for curve in self._line:
            curve.setSymbol("o" if self._virtual_preview is None else None)
        self.refresh()

    def set_voltage_view(self, mode: str) -> None:
        """Select virtual, physical, or simultaneous voltage rendering."""
        if mode not in {"both", "virtual", "physical"}:
            raise ValueError("voltage view must be 'both', 'virtual', or 'physical'")
        self._voltage_view = mode
        self._finish_drag()
        for curve in self._line:
            curve.setVisible(mode in {"both", "virtual"})
        for curve in self._physical_line:
            curve.setVisible(mode in {"both", "physical"})
        for curve in self._rc_line:
            curve.setVisible(bool(self._rc_time_ns.size) and mode in {"both", "physical"})
        for graphics in self._sweep_graphics.values():
            visible = mode in {"both", "physical"}
            graphics["lower_curve"].setVisible(visible)
            graphics["upper_curve"].setVisible(visible)
            graphics["fill"].setVisible(visible)
        self._update_highlight()
        self.fit_view()

    def set_rc_waveforms(self, time_ns, waveforms_mv) -> None:
        """Overlay the estimated RC-corrected DAC drive in each port's color."""
        self._rc_time_ns = np.asarray(time_ns, dtype=float)
        self._rc_values_mv = np.asarray(waveforms_mv, dtype=float)
        while len(self._rc_line) > len(self._pulses):
            self.removeItem(self._rc_line.pop())
        while len(self._rc_line) < len(self._pulses):
            self._rc_line.append(self.plot([], []))
        for index, curve in enumerate(self._rc_line):
            curve.setPen(pg.mkPen(self.line_color(index), width=2.2,
                                 style=QtCore.Qt.DashDotLine))
            curve.setZValue(index + 1.2)
            curve.setData(self._rc_time_ns,
                          self._rc_values_mv[index] if self._rc_time_ns.size else [])
            curve.setVisible(bool(self._rc_time_ns.size)
                             and self._voltage_view in {"both", "physical"})

    def set_sweep_envelope(
        self,
        port_index: int,
        time_ns: Sequence[float],
        endpoint_a_mv: Sequence[float],
        endpoint_b_mv: Sequence[float],
    ) -> None:
        """Backward-compatible single-envelope wrapper."""
        self.set_sweep_envelopes(
            (("legacy", port_index, time_ns, endpoint_a_mv, endpoint_b_mv),)
        )

    def _create_sweep_graphics(self):
        if not self._sweep_graphics:
            return {
                "lower_curve": self._sweep_lower_curve,
                "upper_curve": self._sweep_upper_curve,
                "fill": self._sweep_fill,
            }
        color = _plot_color(0)
        lower_curve = self.plot(
            [],
            [],
            pen=pg.mkPen(color, width=1.0, style=QtCore.Qt.DotLine),
        )
        upper_curve = self.plot(
            [],
            [],
            pen=pg.mkPen(color, width=1.0, style=QtCore.Qt.DotLine),
        )
        fill = pg.FillBetweenItem(
            upper_curve,
            lower_curve,
            brush=pg.mkBrush(color.red(), color.green(), color.blue(), 24),
        )
        self.addItem(fill)
        fill.setZValue(0.1)
        lower_curve.setZValue(0.8)
        upper_curve.setZValue(0.8)
        return {"lower_curve": lower_curve, "upper_curve": upper_curve, "fill": fill}

    def set_sweep_envelopes(self, envelopes) -> None:
        """Draw independent sweep endpoint/fill graphics for multiple targets."""
        active_keys = set()
        bounds_time = []
        bounds_lower = []
        bounds_upper = []
        first = None
        for key, port_index, time_ns, endpoint_a_mv, endpoint_b_mv in envelopes:
            if port_index < 0 or port_index >= len(self._pulses):
                raise IndexError("sweep port index is out of range")
            time_values = np.asarray(time_ns, dtype=float)
            endpoint_a = np.asarray(endpoint_a_mv, dtype=float)
            endpoint_b = np.asarray(endpoint_b_mv, dtype=float)
            if (
                time_values.ndim != 1
                or endpoint_a.shape != time_values.shape
                or endpoint_b.shape != time_values.shape
            ):
                raise ValueError("sweep endpoint traces must be equal-length vectors")
            lower = np.minimum(endpoint_a, endpoint_b)
            upper = np.maximum(endpoint_a, endpoint_b)
            graphics = self._sweep_graphics.get(key)
            if graphics is None:
                graphics = self._create_sweep_graphics()
                self._sweep_graphics[key] = graphics
            color = self.line_color(port_index)
            endpoint_pen = pg.mkPen(color, width=1.0, style=QtCore.Qt.DotLine)
            graphics["lower_curve"].setPen(endpoint_pen)
            graphics["upper_curve"].setPen(endpoint_pen)
            graphics["fill"].setBrush(
                pg.mkBrush(color.red(), color.green(), color.blue(), 24)
            )
            graphics["lower_curve"].setData(time_values, lower)
            graphics["upper_curve"].setData(time_values, upper)
            visible = self._voltage_view in {"both", "physical"}
            graphics["lower_curve"].setVisible(visible)
            graphics["upper_curve"].setVisible(visible)
            graphics["fill"].setVisible(visible)
            graphics.update(
                port_index=port_index,
                time_ns=time_values,
                lower_mv=lower,
                upper_mv=upper,
            )
            active_keys.add(key)
            bounds_time.append(time_values)
            bounds_lower.append(lower)
            bounds_upper.append(upper)
            if first is None:
                first = graphics

        for key, graphics in self._sweep_graphics.items():
            if key not in active_keys:
                graphics["lower_curve"].setData([], [])
                graphics["upper_curve"].setData([], [])
                graphics["lower_curve"].setVisible(False)
                graphics["upper_curve"].setVisible(False)
                graphics["fill"].setVisible(False)

        if first is None:
            self._sweep_port_index = None
            self._sweep_time_ns = np.asarray([], dtype=float)
            self._sweep_lower_mv = np.asarray([], dtype=float)
            self._sweep_upper_mv = np.asarray([], dtype=float)
            self.update()
            return

        # Preserve the original single-sweep inspection attributes.
        self._sweep_lower_curve = first["lower_curve"]
        self._sweep_upper_curve = first["upper_curve"]
        self._sweep_fill = first["fill"]
        self._sweep_port_index = first["port_index"]
        self._sweep_time_ns = np.concatenate(bounds_time)
        self._sweep_lower_mv = np.concatenate(bounds_lower)
        self._sweep_upper_mv = np.concatenate(bounds_upper)
        self.update()

    def clear_sweep_envelope(self) -> None:
        self.set_sweep_envelopes(())

    def fit_view(self) -> None:
        if not self._pulses:
            return
        x_values = []
        y_values = []
        if self._voltage_view in {"both", "virtual"}:
            if self._virtual_preview is None:
                x_values.extend(pulse.t for pulse in self._pulses)
                y_values.extend(pulse.v for pulse in self._pulses)
            else:
                x_values.append(self._virtual_preview[0])
                y_values.extend(self._virtual_preview[1])
        if (
            self._voltage_view in {"both", "physical"}
            and self._physical_time_ns.size
            and self._physical_values_mv.size
        ):
            x_values.append(self._physical_time_ns)
            y_values.extend(self._physical_values_mv)
        if self._voltage_view in {"both", "physical"} and self._rc_time_ns.size:
            x_values.append(self._rc_time_ns)
            y_values.extend(self._rc_values_mv)
        if not x_values or not y_values:
            return
        x_min = min(float(np.min(values)) for values in x_values)
        x_max = max(float(np.max(values)) for values in x_values)
        y_min = min(float(np.min(values)) for values in y_values)
        y_max = max(float(np.max(values)) for values in y_values)
        if self._sweep_time_ns.size:
            x_min = min(x_min, float(np.min(self._sweep_time_ns)))
            x_max = max(x_max, float(np.max(self._sweep_time_ns)))
            y_min = min(y_min, float(np.min(self._sweep_lower_mv)))
            y_max = max(y_max, float(np.max(self._sweep_upper_mv)))
        x_margin = max(1.0, 0.03 * max(1.0, x_max - x_min))
        y_margin = max(0.5, 0.10 * max(1.0, y_max - y_min))
        self.setXRange(x_min - x_margin, x_max + x_margin, padding=0.0)
        self.setYRange(y_min - y_margin, y_max + y_margin, padding=0.0)

    def refresh(self, index: Optional[int] = None) -> None:
        """Update existing curves without rebuilding axes or graphics items."""
        indices = range(len(self._pulses)) if index is None else (index,)
        for pulse_index in indices:
            pulse = self._pulses[pulse_index]
            if self._virtual_preview is None:
                self._line[pulse_index].setData(pulse.t, pulse.v)
            else:
                times, values = self._virtual_preview
                self._line[pulse_index].setData(times, values[pulse_index])

    def add_pulse(self, pulse: PulseSequence) -> None:
        self._finish_drag()
        self.set_virtual_preview()
        self._pulses.append(pulse)
        self._append_curve(pulse)
        self._selected_port_idx = len(self._pulses) - 1
        self._update_highlight()
        self.fit_view()

    def get_selected_port_idx(self) -> int:
        return self._selected_port_idx

    def set_selected_port_idx(self, index: int) -> None:
        if index < 0 or index >= len(self._pulses):
            raise IndexError("selected port index is out of range")
        self._finish_drag()
        self._selected_port_idx = index
        self._update_highlight()

    def remove_pulse(self, index: int) -> None:
        if index < 0 or index >= len(self._pulses):
            raise IndexError("pulse index is out of range")
        self._finish_drag()
        self.set_virtual_preview()
        curve = self._line.pop(index)
        self.removeItem(curve)
        physical_curve = self._physical_line.pop(index)
        self.removeItem(physical_curve)
        self._pulses.pop(index)
        self._orig_colors.pop(index)
        self._physical_time_ns = np.asarray([], dtype=float)
        self._physical_values_mv = np.empty((0, 0), dtype=float)
        self._selected_port_idx = min(self._selected_port_idx, len(self._pulses) - 1)
        self._update_highlight()

    def _scene_position(self, event) -> QtCore.QPointF:
        return self.mapToScene(event.pos())

    def _view_position(self, event) -> QtCore.QPointF:
        return self.getPlotItem().vb.mapSceneToView(self._scene_position(event))

    def _locate_point(self, event, tolerance_px: float = 9.0) -> Optional[Tuple[int, int]]:
        scene_position = self._scene_position(event)
        pulse = self._pulses[self._selected_port_idx]
        view_box = self.getPlotItem().vb
        for index, (time_ns, voltage_mv) in enumerate(zip(pulse.t, pulse.v)):
            point = view_box.mapViewToScene(
                QtCore.QPointF(float(time_ns), float(voltage_mv))
            )
            if hypot(point.x() - scene_position.x(), point.y() - scene_position.y()) <= tolerance_px:
                return index, min(index + 1, len(pulse.t) - 1)
        return None

    def _locate_flat(self, event, tolerance_px: float = 9.0) -> Optional[Tuple[int, int]]:
        scene_position = self._scene_position(event)
        pulse = self._pulses[self._selected_port_idx]
        view_box = self.getPlotItem().vb
        for start_index, end_index in pulse.flat_segments():
            start = view_box.mapViewToScene(
                QtCore.QPointF(float(pulse.t[start_index]), float(pulse.v[start_index]))
            )
            end = view_box.mapViewToScene(
                QtCore.QPointF(float(pulse.t[end_index]), float(pulse.v[end_index]))
            )
            left, right = sorted((start.x(), end.x()))
            inner_left = left + 0.18 * (right - left)
            inner_right = right - 0.18 * (right - left)
            if (
                inner_left <= scene_position.x() <= inner_right
                and abs(scene_position.y() - start.y()) <= tolerance_px
            ):
                return start_index, end_index
        return None

    def _finish_drag(self) -> None:
        self._drag_flat = self._drag_point = None
        self._hide_annotation()
        self.unsetCursor()

    def _hide_annotation(self) -> None:
        # Qt may send a final hide/leave while the scene is being destroyed.
        if not sip.isdeleted(self._annotation):
            self._annotation.hide()

    def event(self, event):
        # A tab change or loss of window activation can swallow the release.
        if hasattr(self, "_annotation") and event.type() in (
            QtCore.QEvent.Hide, QtCore.QEvent.WindowDeactivate,
        ):
            self._finish_drag()
        return super().event(event)

    def eventFilter(self, watched, event):
        if watched is self.viewport():
            if event.type() == QtCore.QEvent.Leave:
                self._hide_annotation()
            elif event.type() == QtCore.QEvent.UngrabMouse:
                self._finish_drag()
            elif event.type() == QtCore.QEvent.MouseButtonRelease:
                if self._drag_flat is not None or self._drag_point is not None:
                    self.mouseReleaseEvent(event)
                    return True
                self._finish_drag()
        if self._voltage_view == "physical" or self._virtual_preview is not None:
            return super().eventFilter(watched, event)
        if watched is self.viewport():
            if event.type() == QtCore.QEvent.MouseButtonPress:
                if event.button() == QtCore.Qt.LeftButton:
                    point = self._locate_point(event)
                    flat = None if point is not None else self._locate_flat(event)
                    if point is not None:
                        self._drag_point = point
                        self.setCursor(QtCore.Qt.SizeHorCursor)
                        return True
                    if flat is not None:
                        self._drag_flat = flat
                        self.setCursor(QtCore.Qt.SizeVerCursor)
                        return True
            elif event.type() == QtCore.QEvent.MouseMove:
                if self._drag_flat is not None or self._drag_point is not None:
                    self.mouseMoveEvent(event)
                    return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event) -> None:
        if self._voltage_view == "physical" or self._virtual_preview is not None:
            super().mousePressEvent(event)
            return
        if event.button() == QtCore.Qt.LeftButton:
            point = self._locate_point(event)
            flat = None if point is not None else self._locate_flat(event)
            if point is not None:
                self._drag_point = point
                self.setCursor(QtCore.Qt.SizeHorCursor)
                event.accept()
                return
            if flat is not None:
                self._drag_flat = flat
                self.setCursor(QtCore.Qt.SizeVerCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if not (event.buttons() & QtCore.Qt.LeftButton):
            self._finish_drag()
            super().mouseMoveEvent(event)
            return
        if self._drag_flat is not None:
            pulse = self._pulses[self._selected_port_idx]
            position = self._view_position(event)
            new_voltage = self._snap_voltage(float(position.y()), pulse)
            start_index, end_index = self._drag_flat
            pulse.update_flat(self._drag_flat, new_voltage)
            self.refresh(self._selected_port_idx)
            self._show_annotation(
                float(pulse.t[start_index]),
                new_voltage,
                f"{pulse.t[start_index] * TIME_UNIT_SCALE[self._time_unit]:.6g} "
                f"{self._time_unit}\n{new_voltage:.6g} mV",
            )
            self.flat_moved.emit(start_index, end_index, new_voltage)
            event.accept()
            return
        if self._drag_point is not None:
            pulse = self._pulses[self._selected_port_idx]
            position = self._view_position(event)
            x_range = self.getPlotItem().vb.viewRange()[0]
            new_time = float(np.clip(position.x(), x_range[0], x_range[1]))
            start_index, end_index = self._drag_point
            new_time = self._snap_time(new_time, pulse, start_index)
            pulse.update_point(self._drag_point, new_time)
            actual_time = float(pulse.t[start_index])
            self.refresh(self._selected_port_idx)
            self._show_annotation(
                actual_time,
                float(pulse.v[start_index]),
                f"{actual_time * TIME_UNIT_SCALE[self._time_unit]:.6g} "
                f"{self._time_unit}\n{pulse.v[start_index]:.6g} mV",
            )
            self.point_moved.emit(start_index, end_index, actual_time)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        was_dragging = self._drag_flat is not None or self._drag_point is not None
        self._finish_drag()
        if was_dragging:
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        view_box = self.getPlotItem().vb
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers & QtCore.Qt.ControlModifier:
            view_box.setMouseEnabled(x=True, y=False)
        elif modifiers & QtCore.Qt.ShiftModifier:
            view_box.setMouseEnabled(x=False, y=True)
        else:
            view_box.setMouseEnabled(x=True, y=True)
        try:
            super().wheelEvent(event)
        finally:
            view_box.setMouseEnabled(x=True, y=True)

    def _show_annotation(self, x: float, y: float, text: str) -> None:
        self._annotation.setText(text)
        self._annotation.setPos(x, y)
        self._annotation.show()

    def _update_highlight(self) -> None:
        for index, curve in enumerate(self._line):
            base = QtGui.QColor(self._orig_colors[index])
            if index == self._selected_port_idx:
                color = base
                width = self._highlight_width
                curve.setZValue(100)
            else:
                color = base.lighter(125)
                color.setAlpha(165)
                width = self._default_width
                curve.setZValue(index + 1)
            curve.setPen(pg.mkPen(color, width=width))
            curve.setSymbolPen(pg.mkPen(color))
            curve.setSymbolBrush(pg.mkBrush(color))
            physical = self._physical_line[index]
            physical_color = QtGui.QColor(color)
            physical_color.setAlpha(220 if index == self._selected_port_idx else 145)
            physical.setPen(
                pg.mkPen(
                    physical_color,
                    width=(
                        self._physical_width + 0.5
                        if index == self._selected_port_idx
                        else self._physical_width
                    ),
                    style=QtCore.Qt.DashLine,
                )
            )
            physical.setZValue(99 if index == self._selected_port_idx else index + 0.5)

    def _restore_full_intensity(self) -> None:
        for index, curve in enumerate(self._line):
            color = self._orig_colors[index]
            curve.setPen(pg.mkPen(color, width=self._default_width))
            curve.setSymbolPen(pg.mkPen(color))
            curve.setSymbolBrush(pg.mkBrush(color))
            curve.setZValue(index + 1)
            physical = self._physical_line[index]
            physical.setPen(
                pg.mkPen(
                    color,
                    width=self._physical_width,
                    style=QtCore.Qt.DashLine,
                )
            )
            physical.setZValue(index + 0.5)


__all__ = [
    "AcquisitionTimelineWidget",
    "RfPulsePreviewWidget",
    "RfPulseTimelineWidget",
    "TracePlotWidget",
    "WaveformPlotWidget",
]
