"""Offscreen visual check of the changed display widgets; no board access."""
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
from dc_waveform_core import PulseSequence
from dc_waveform_widgets import WaveformPlotWidget, RfPulseTimelineWidget

app = QtWidgets.QApplication([])
# The offscreen Qt plugin has no system font discovery on this desktop.
font_id = QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
assert font_id >= 0
app.setFont(QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(font_id)[0], 9))
window = QtWidgets.QWidget()
layout = QtWidgets.QVBoxLayout(window)
layout.addWidget(QtWidgets.QLabel('AWG waveform - edit annotation cleared after release'))
pulse = PulseSequence(initial_voltage=0, initial_duration_ns=1000)
pulse.add_flat_ramp(100, 5000, 400)
pulse.add_flat_ramp(100, 1000, 0)
waveform = WaveformPlotWidget(pulse)
layout.addWidget(waveform, 1)
timeline = RfPulseTimelineWidget()
timeline.set_time_unit('us')
timeline.set_pulses(gen_ch=2, pulses=[
    dict(pulse_name='RF1', start_ns=1600, duration_ns=1000,
         frequency_mhz=250, gain=22000, phase_degrees=0),
    dict(pulse_name='RF2', start_ns=3600, duration_ns=1000,
         frequency_mhz=250, gain=22000, phase_degrees=0),
], att1_db=0, att2_db=0)
timeline.setFixedHeight(140)
layout.addWidget(timeline)
for plot in (waveform, timeline):
    plot.setXRange(0, 18000, padding=0)
window.resize(1100, 630)
window.show()
app.processEvents()
assert not waveform._annotation.isVisible()
for label in timeline._pulse_labels:
    assert timeline.getPlotItem().vb.sceneBoundingRect().contains(label.sceneBoundingRect())
path = Path(__file__).with_name('waveform_labels.png')
assert window.grab().save(str(path))
print(path)
window.close()
window.deleteLater()
app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
