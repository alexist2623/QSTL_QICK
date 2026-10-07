"""Render real WaveformPlotWidgets and exercise wheel zoom without a board."""
import json
from pathlib import Path

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

from dc_waveform_core import PulseSequence
from dc_waveform_widgets import WaveformPlotWidget
from qick_waveform_preview import rc_precompensated_vertices


out = Path(__file__).parent
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
app.setFont(QtGui.QFont('Segoe UI', 10))
panel = QtWidgets.QWidget()
panel.setWindowTitle('Waveform Plot: automatic time units')
panel.setStyleSheet('QWidget { background: white; color: #25364b; }')
layout = QtWidgets.QGridLayout(panel)
title = QtWidgets.QLabel('Same waveform data — only the visible time range changes')
title.setStyleSheet('font-size: 18px; font-weight: bold; padding: 8px;')
layout.addWidget(title, 0, 0, 1, 2)
pulse = PulseSequence()
pulse.t = np.array([0., 300000., 300500., 499500., 500000., 800000.])
pulse.v = np.array([0., 0., 100., 100., -100., -100.])
physical = np.array([pulse.v * .8])
rc_t, rc_v = rc_precompensated_vertices(pulse.t, physical, 300)
plots = []
views = [
    ('Fit: full waveform', None, 'us'),
    ('Zoom in: 800 ns around the rising ramp', (299850., 300650.), 'ns'),
    ('Zoom out: 4 ms', (-1000000., 3000000.), 'ms'),
    ('Zoom out: 2 s', (-100000000., 1900000000.), 's'),
]
for i, (label, limits, expected) in enumerate(views):
    plot = WaveformPlotWidget(pulse.copy())
    plot.set_physical_waveforms(pulse.t, physical)
    plot.set_rc_waveforms(rc_t, rc_v)
    plot.setTitle(label, color='#25364b', size='12pt')
    plot.fit_view()
    if limits is not None:
        plot.setXRange(*limits, padding=0)
    layout.addWidget(plot, i//2 + 1, i%2)
    plots.append(plot)
panel.resize(1400, 1000)
panel.show()
for _ in range(4):
    app.processEvents()
records = []
for plot, (_, _, expected) in zip(plots, views):
    assert plot._time_unit == expected
    assert plot.getAxis('bottom').labelUnits == ''
    np.testing.assert_array_equal(plot._line[0].xData, pulse.t)
    records.append({'unit': plot._time_unit, 'range_ns': plot.viewRange()[0],
                    'label': plot.getAxis('bottom').labelText})
assert panel.grab().save(str(out/'waveform_time_units.png'))

# Actual Qt wheel events (rather than direct range assignment) must switch
# units in both directions, then Fit must restore the full-waveform scale.
plot = plots[0]
plot.setXRange(0, 1200, padding=0)
seen = [plot._time_unit]
for delta in [120]*8 + [-120]*8:
    center = plot.viewport().rect().center()
    event = QtGui.QWheelEvent(
        QtCore.QPointF(center), QtCore.QPointF(plot.viewport().mapToGlobal(center)),
        QtCore.QPoint(), QtCore.QPoint(0, delta), QtCore.Qt.NoButton,
        QtCore.Qt.NoModifier, QtCore.Qt.ScrollUpdate, False)
    QtWidgets.QApplication.sendEvent(plot.viewport(), event)
    app.processEvents()
    seen.append(plot._time_unit)
assert 'ns' in seen and seen[-1] == 'us', seen
np.testing.assert_array_equal(plot._pulses[0].t, pulse.t)
plot.fit_view()
app.processEvents()
assert plot._time_unit == 'us'
(out/'zoom_checks.json').write_text(json.dumps({
    'views': records, 'wheel_zoom_units': seen, 'fit_unit': plot._time_unit,
    'waveform_time_arrays_unchanged': True,
    'environment': 'Windows / qcodes2 Python 3.12 / Qt offscreen',
}, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'rendered': str(out/'waveform_time_units.png'), 'wheel_units': seen}))
panel.close()
panel.deleteLater()
app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
