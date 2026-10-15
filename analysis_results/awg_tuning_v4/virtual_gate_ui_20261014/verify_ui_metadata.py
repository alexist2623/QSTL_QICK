"""Inspect the real matrix dialog and verify saved QCoDeS metadata without hardware."""
import hashlib
import json
from pathlib import Path
import tempfile
import numpy as np
from qick.sim import QickSim  # Existing desktop import bootstrap; no board connection.
from PyQt5 import QtCore, QtGui, QtTest, QtWidgets
from qcodes.dataset import load_by_id
from qcodes.dataset.sqlite.database import connect
import DCWaveform_Generator as gui
from qick_fine_tune_sweep import FineTuneSequence
from qick_qcodes_experiment import (
    QcodesRunConfig, QickConnectionConfig, build_awg_waveform_recipe, store_qick_result,
)
from test_qick_qcodes_experiment import _ddr_result

OUT = Path(__file__).resolve().parent
MATRIX = np.array([[1.0, 0.25], [-0.125, 1.0]])
app = QtWidgets.QApplication([])
QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
app.setFont(QtGui.QFont('Segoe UI', 10))
window = gui.MainWindow()
window._add_port()
checks = []
callback_errors = []

def edit_real_dialog():
    try:
        dialog = app.activeModalWidget()
        assert isinstance(dialog, gui.CrossCapacitanceDialog)
        for row, column in [(0, 1), (1, 0)]:
            editor = dialog._editors[row][column]
            editor.setFocus()
            editor.selectAll()
            QtTest.QTest.keyClicks(editor, str(MATRIX[row, column]))
            QtTest.QTest.keyClick(editor, QtCore.Qt.Key_Tab)
            assert f'Virtual awg_{column} input -> Physical awg_{row} output' in editor.toolTip()
        np.testing.assert_array_equal(dialog.matrix(), MATRIX)
        app.processEvents()
        assert dialog.grab().save(str(OUT / 'matrix_2_outputs.png'))
        dialog.findChild(QtWidgets.QDialogButtonBox).button(QtWidgets.QDialogButtonBox.Ok).click()
    except Exception as exc:
        callback_errors.append(repr(exc))
        app.activeModalWidget().reject()

QtCore.QTimer.singleShot(100, edit_real_dialog)
window._configure_cross_capacitance()
assert not callback_errors, callback_errors
np.testing.assert_array_equal(window._cross_capacitance, MATRIX)
checks.append('Real MainWindow dialog: keyboard editing and OK preserve row/column orientation')
settings = window._settings_to_dict()
assert settings['awg']['cross_capacitance'] == MATRIX.tolist()
checks.append('MainWindow canonical experiment settings contain the exact nonidentity matrix')

def cancel_edit():
    try:
        dialog = app.activeModalWidget()
        dialog._editors[0][1].setValue(9.0)
        dialog.findChild(QtWidgets.QDialogButtonBox).button(QtWidgets.QDialogButtonBox.Cancel).click()
    except Exception as exc:
        callback_errors.append(repr(exc))
        app.activeModalWidget().reject()
QtCore.QTimer.singleShot(100, cancel_edit)
window._configure_cross_capacitance()
assert not callback_errors, callback_errors
np.testing.assert_array_equal(window._cross_capacitance, MATRIX)
checks.append('Cancel leaves the accepted matrix unchanged')

matrix7 = np.eye(7)
matrix7[0, 1] = 0.25
matrix7[1, 0] = -0.125
dialog7 = gui.CrossCapacitanceDialog(7, matrix7)
dialog7.show()
app.processEvents()
assert dialog7.grab().save(str(OUT / 'matrix_7_outputs.png'))
for index in range(7):
    assert dialog7._editors[index][index].isReadOnly()
    assert dialog7._editors[index][index].value() == 1.0
next(b for b in dialog7.findChildren(QtWidgets.QPushButton) if b.text() == 'Reset identity').click()
np.testing.assert_array_equal(dialog7.matrix(), np.eye(7))
checks.append('Seven-output rendering, diagonal lock, and Reset identity')

sequence = FineTuneSequence(('awg_0', 'awg_1'))
sequence.set_cross_capacitance(MATRIX)
sequence.add_set('set_1', (0.2, 0.1), 300)
np.testing.assert_allclose(sequence._effective_physical_set_amplitudes_at(0, 0), (0.225, 0.075))
checks.append('Existing physical=C@virtual transform: [0.2, 0.1] -> [0.225, 0.075]')
sequence.set_amplitude_sweep('set_1', 'awg_0', -0.5, 0.5, 2)
settings['awg_waveform_recipe'] = build_awg_waveform_recipe(sequence, fabric_mhz=300.0, full_scale_mv=800.0)
result = _ddr_result()
# The IQ acquisition is synthetic. Production persistence receives the actual GUI settings.
with tempfile.TemporaryDirectory(prefix='virtual_gate_metadata_') as temporary:
    database_path = Path(temporary) / 'matrix.db'
    dataset, row_count = store_qick_result(
        result,
        run_config=QcodesRunConfig(str(database_path), experiment_name='Virtual gate metadata verification', sample_name='synthetic'),
        connection_config=QickConnectionConfig(), program_summary={}, gui_settings=settings, rf_settings={},
    )
    run_id = dataset.run_id
    dataset.conn.close()
    connection = connect(str(database_path))
    restored = load_by_id(run_id, conn=connection)
    persisted = {
        'cross_capacitance_json': json.loads(restored.get_metadata('cross_capacitance_json')),
        'qick_experiment_json.gui_settings.awg.cross_capacitance': json.loads(restored.get_metadata('qick_experiment_json'))['gui_settings']['awg']['cross_capacitance'],
        'awg_waveform_recipe_json.cross_capacitance': json.loads(restored.get_metadata('awg_waveform_recipe_json'))['cross_capacitance'],
    }
    assert all(value == MATRIX.tolist() for value in persisted.values()), persisted
    connection.close()
checks.append('Real QCoDeS SQLite save, close, reopen: all three metadata copies match the asymmetric matrix exactly')

for widget in [dialog7, window]:
    widget.close()
    widget.deleteLater()
app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
sources = [Path(gui.__file__), Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI/qick_qcodes_experiment.py')]
(OUT / 'ui_metadata_results.json').write_text(json.dumps({
    'passed': True, 'checks': checks, 'saved_metadata': persisted, 'iq_rows': row_count,
    'board_connection': False, 'hardware_experiment': False,
    'source_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
}, indent=2), encoding='utf-8')
print('PASS:', len(checks), 'UI / orientation / metadata checks; no board connection', flush=True)
