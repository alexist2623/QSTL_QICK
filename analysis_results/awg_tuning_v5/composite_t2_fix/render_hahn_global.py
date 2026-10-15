from pathlib import Path
from qick.sim import QickSim
from PyQt5 import QtCore, QtGui, QtWidgets, sip
import DCWaveform_Generator as gui
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
panel._add_delay_parameter()
for row in (0, 2):
    panel.composite_item_table.cellWidget(row, 8).setCurrentText('tau')
panel.delay_parameter_table.cellWidget(0, 2).setChecked(True)
preview = panel.composite_group
preview.setParent(None)
preview.resize(1280, 1180)
preview.show()
app.processEvents()
output = Path(__file__).with_name('custom_t2_global_editor.png')
assert preview.grab().save(str(output))
print(str(output), flush=True)
preview.close()
window.close()
preview.deleteLater()
window.deleteLater()
app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
QtCore.QTimer.singleShot(0, app.quit)
app.exec_()
sip.delete(app)
