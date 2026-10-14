"""Render the actual Qt circuit editor with illustrative pulse settings, offline."""
import json
from pathlib import Path
from PyQt5 import QtWidgets, QtCore, QtGui
import DCWaveform_Generator as gui
from quantum_circuit_model import default_document
from quantum_circuit_widgets import GateEditor

out = Path(__file__).parent
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
for font in ('arial.ttf', 'arialbd.ttf'):
    assert QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + font) >= 0
app.setFont(QtGui.QFont('Arial', 10))
document = default_document()
document['qubits'].append({'id': 'q2', 'name': 'q2'})
document['awg_baselines'].append({'channel': 2, 'voltage_mv': 0.})

def awg(channel, value, mode='absolute', ramp=1.):
    return dict(channel=channel, mode=mode, value_mv=value, ramp_us=ramp)

def rf(channel, phase=0., duration=1., delay=.25):
    return dict(channel=channel, delay_us=delay, duration_us=duration,
                frequency_mhz=100., phase_deg=phase, gain=1000)

def gate(name, qubits, start, duration, awgs=(), rfs=(), acquisition=None):
    document['gates'].append(dict(id='g'+str(len(document['gates'])+1),
        name=name, qubits=qubits, start_us=start, duration_us=duration,
        awg=list(awgs), rf=list(rfs), acquisition=acquisition))

gate('Init', ['q1', 'q2'], 0., 4., [awg(1, -100.), awg(2, -150.)])
gate('X', ['q1'], 6., 2., rfs=[rf(1)])
gate('X', ['q2'], 9., 2., rfs=[rf(2)])
gate('Y', ['q2'], 12., 2., rfs=[rf(2, 90.)])
gate('CNOT', ['q1', 'q2'], 16., 2., rfs=[rf(1), rf(2)])
gate('Readout', ['q1', 'q2'], 21., 10.,
     [awg(1, 50., 'relative'), awg(2, 100., 'relative')],
     [rf(3, duration=7., delay=2.)], dict(delay_us=2., duration_us=8.))
(out/'example_circuit.json').write_text(json.dumps(document, indent=2)+'\n', encoding='utf-8')
window = gui.MainWindow()
window.resize(1760, 1040)
window._quantum_circuit_panel.load_document(document)
window._control_tabs.setCurrentWidget(window._quantum_circuit_panel)
window.show()
app.processEvents()
window.resizeDocks([window._dock_ctrl, window._dock_quantum_circuit], [380, 1300], QtCore.Qt.Horizontal)
window._quantum_circuit_view.fit_view()
app.processEvents()
window.grab().save(str(out/'quantum_circuit_window.png'))
window._quantum_circuit_view.grab().save(str(out/'quantum_circuit_view.png'))
editor = GateEditor(document, document['gates'][-1], window)
editor.show()
app.processEvents()
editor.grab().save(str(out/'gate_editor.png'))
editor.close()
window.close()
window.deleteLater()
QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
