"""Render the actual loop editor offline; do not connect or run an experiment."""
from pathlib import Path
import json
from PyQt5 import QtWidgets, QtGui, QtCore
import DCWaveform_Generator as gui
from quantum_circuit_widgets import LoopEditor
from test_quantum_circuit_loops import loop_document

out = Path(__file__).parent
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
for filename in ('arial.ttf', 'arialbd.ttf'):
    QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + filename)
app.setFont(QtGui.QFont('Arial', 10))
document = loop_document(3, sweep=dict(start=1, stop=5, step=2))
window = gui.MainWindow()
window.resize(1800, 1050)
window._quantum_circuit_panel.load_document(document)
window._quantum_circuit_panel.preview_combo.setCurrentIndex(1)
window._quantum_circuit_panel.loop_list.setCurrentRow(0)
window._control_tabs.setCurrentWidget(window._quantum_circuit_panel)
window.show()
app.processEvents()
window.resizeDocks([window._dock_ctrl, window._dock_quantum_circuit], [470, 1330], QtCore.Qt.Horizontal)
window._quantum_circuit_view.fit_view()
app.processEvents()
window.grab().save(str(out/'loop_window.png'))
window._quantum_circuit_view.grab().save(str(out/'loop_timeline.png'))
dialog = LoopEditor(document, loop=document['loops'][0], parent=window)
dialog.show()
app.processEvents()
dialog.grab().save(str(out/'loop_editor.png'))
(out/'loop_example_document.json').write_text(json.dumps(document,indent=2)+'\n',encoding='utf-8')
dialog.close()
window.close()
window.deleteLater()
QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
