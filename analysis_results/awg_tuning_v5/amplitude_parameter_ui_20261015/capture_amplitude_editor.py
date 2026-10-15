"""Render the actual amplitude editor in an isolated offscreen process."""
from dataclasses import asdict
from pathlib import Path
import gc
import hashlib
import json
import socket
import sys

HERE = Path(__file__).resolve().parent
GUI = Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')
assert not (HERE / 'screenshots.json').exists(), 'Preserve prior screenshots'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

json_before = {str(p): sha(p) for p in GUI.glob('*.json')}
source = GUI / 'DCWaveform_Generator.py'
source_before = sha(source)

def forbidden(*args, **kwargs):
    raise AssertionError('No network access is allowed in editor screenshots')
socket.create_connection = forbidden
socket.socket.connect = forbidden
socket.socket.connect_ex = forbidden

from qick.sim import QickSim
from PyQt5 import QtCore, QtGui, QtWidgets, sip
import DCWaveform_Generator as gui
from dc_waveform_core import QickRfAmplitudeParameterSpec, QickRfCompositeItemSpec, QickRfDurationParameterSpec

app = QtWidgets.QApplication([])
assert app.platformName() == 'offscreen'
app.setQuitOnLastWindowClosed(False)
app.setFont(QtGui.QFont('Segoe UI', 9))
window = gui.MainWindow()
panel = window._rf_ports_panel._panels[0]
panel.load_settings({**gui.DEFAULT_RF_OUTPUT_SETTINGS,
    'enabled': True, 'pulse_mode': 'composite',
    'duration_parameters': [asdict(QickRfDurationParameterSpec('d_pi', 0.4))],
    'composite_items': [asdict(QickRfCompositeItemSpec('pulse', 'X', 0.4, 'f0', duration_parameter='d_pi'))]})

def select(widget, value):
    index = widget.findData(value)
    assert index >= 0, value
    widget.setCurrentIndex(index)

select(panel.predefined_template, 'hahn_echo')
panel.predefined_tau.setValue(4.0)
panel.t2_initial_pi2.setChecked(True)
panel.t2_final_pi2.setChecked(True)
panel._add_numeric_parameter('amplitude', QickRfAmplitudeParameterSpec('a_shared', 12000))
select(panel.global_amplitude_parameter, 'a_shared')

# Only this private offscreen widget is reparented to make its full layout visible.
group = panel.composite_group
group.setParent(None)
captures = []
def capture(name):
    group.resize(1250, group.sizeHint().height())
    group.show()
    app.processEvents()
    group.resize(1250, group.sizeHint().height())
    app.processEvents()
    path = HERE / name
    assert not path.exists(), 'Preserve prior screenshot'
    assert group.grab().save(str(path))
    captures.append(dict(path=str(path), sha256=sha(path),
                         width=group.width(), height=group.height(),
                         settings=panel.settings_dict(),
                         named_amplitude_mode=panel.configured_spec().global_amplitude_mode,
                         numeric_global_gain_hidden=panel.global_gain.isHidden(),
                         individual_power_column_hidden=panel.composite_item_table.isColumnHidden(6)))

capture('preset_hahn_manual.png')
select(panel.predefined_template, 'custom')
panel.global_calibration_database_path.setText('example-output-calibration.db')
panel.global_calibration_run_id.setValue(12)
panel.amplitude_calibration_enabled.setChecked(True)
panel._add_numeric_parameter('amplitude', QickRfAmplitudeParameterSpec('a_body', -18.0, True, -25, -15, 5))
for row in range(panel.composite_item_table.rowCount()):
    if panel.composite_item_table.cellWidget(row, 0).currentData() == 'pulse':
        select(panel.composite_item_table.cellWidget(row, 5), 'a_body')
capture('custom_calibration.png')

assert sha(source) == source_before
assert {str(p): sha(p) for p in GUI.glob('*.json')} == json_before
group.close()
group.deleteLater()
window.close()
window.deleteLater()
app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
del group, panel, window
gc.collect()
sip.delete(app)
(HERE / 'screenshots.json').write_text(json.dumps(dict(
    passed=True, platform='offscreen', board_access=False, live_gui_control=False,
    source_path=str(source), source_sha256=source_before, user_json_unchanged=True,
    script_sha256=sha(__file__), images=captures), indent=2), encoding='utf-8')
print(json.dumps({'passed': True, 'images': [item['path'] for item in captures]}))
