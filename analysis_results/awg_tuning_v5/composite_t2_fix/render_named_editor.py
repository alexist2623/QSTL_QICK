"""Render an owned offscreen editor; never open the live GUI or connect a board."""
from pathlib import Path
import gc
from qick.sim import QickSim
from PyQt5 import QtCore, QtGui, QtWidgets, sip
import DCWaveform_Generator as gui
from dc_waveform_core import QickRfAmplitudeParameterSpec, QickRfPhaseParameterSpec

app = QtWidgets.QApplication([])
font_id = QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
app.setFont(QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(font_id)[0], 9))
window = gui.MainWindow()
panel = window._rf_ports_panel._panels[0]
panel.setChecked(True)
panel.composite_mode.setChecked(True)
panel.predefined_template.setCurrentIndex(panel.predefined_template.findData('hahn_echo'))
panel.t2_initial_pi2.setChecked(True)
panel.t2_final_pi2.setChecked(True)
panel.predefined_template.setCurrentIndex(panel.predefined_template.findData('custom'))
panel._add_numeric_parameter('amplitude', QickRfAmplitudeParameterSpec('a1', 12000))
panel._add_numeric_parameter('phase', QickRfPhaseParameterSpec('p1', 90))
panel.composite_item_table.cellWidget(1, 5).setCurrentText('a1')
panel.composite_item_table.cellWidget(1, 7).setCurrentText('p1')
preview = panel.composite_group
preview.setParent(None)
preview.resize(1350, 1650)
preview.show()
app.processEvents()
for mode in ('manual', 'calibration'):
    if mode == 'calibration':
        panel.amplitude_calibration_enabled.setChecked(True)
        # An empty DB field intentionally makes no database or board request.
    app.processEvents()
    output = Path(__file__).with_name(f'custom_named_{mode}_editor.png')
    assert preview.grab().save(str(output))
    print(output, flush=True)
preview.close()
window.close()
preview.deleteLater()
window.deleteLater()
app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
del preview, panel, window
gc.collect()
QtCore.QTimer.singleShot(0, app.quit)
app.exec_()
sip.delete(app)
print('QT_EXPLICIT_TEARDOWN_COMPLETE', flush=True)
