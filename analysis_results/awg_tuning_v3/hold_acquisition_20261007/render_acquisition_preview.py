"""Reproducible offscreen capture of the real GUI's acquisition timeline."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from PyQt5 import QtWidgets, QtCore, QtGui
import DCWaveform_Generator as gui
from test_acquisition_preview import configure_window

output = Path(__file__).resolve().parent
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
for font in ('arial.ttf', 'arialbd.ttf'):
    assert QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + font) >= 0
app.setFont(QtGui.QFont('Arial', 10))
window = gui.MainWindow()
configure_window(window, samples=64)
window._show_dc_compensation.setChecked(False)
window._show_rc_compensation.setChecked(False)
window._waveform_point_index.setValue(2)
window._dock_plot.setFloating(True)
window._dock_plot.resize(1250, 1000)
window._dock_plot.show()
for _ in range(4):
    app.processEvents()
window._fit_view()
for _ in range(4):
    app.processEvents()
assert window._waveform_container.grab().save(str(output / 'acquisition_waveform.png'))
window._dock_plot.resize(600, 1000)
for _ in range(4):
    app.processEvents()
assert window._waveform_container.grab().save(str(output / 'acquisition_narrow.png'))
print('Narrow dock width:', window._dock_plot.width())
window._dock_plot.resize(1250, 1000)
window._plot.setXRange(32950, 33350, padding=0)
for _ in range(4):
    app.processEvents()
assert window._waveform_container.grab().save(str(output / 'acquisition_zoom.png'))
window.close()
window.deleteLater()
app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
print('Saved acquisition_waveform.png and acquisition_zoom.png')
