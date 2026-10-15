"""Qt behavior for the standalone circuit editor and linked pulse canvas."""
import copy

import pytest
from PyQt5 import QtCore, QtWidgets

from quantum_circuit_model import default_document
from quantum_circuit_widgets import GateEditor, BaselineEditor, QuantumCircuitPanel, QuantumCircuitView


@pytest.fixture(scope='module')
def app():
    instance = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield instance


def gate(gate_id='g1', start=0.):
    return dict(id=gate_id, name='X', qubits=['q1'], start_us=start, duration_us=2.,
                awg=[dict(channel=1, mode='relative', value_mv=15., ramp_us=.2)],
                rf=[dict(channel=1, delay_us=.5, duration_us=.8, frequency_mhz=50., gain=1234, phase_deg=90.)],
                acquisition=dict(delay_us=1.5, duration_us=.5))


def document():
    data = default_document()
    data['gates'] = [gate()]
    return data


def test_load_is_transactional_deep_copy_and_signals(app):
    panel = QuantumCircuitPanel()
    emitted = []
    panel.document_changed.connect(emitted.append)
    data = document()
    panel.load_document(data)
    data['gates'][0]['name'] = 'not shared'
    assert panel.document()['gates'][0]['name'] == 'X'
    emitted[0]['gates'][0]['name'] = 'not shared either'
    assert panel.document()['gates'][0]['name'] == 'X'
    invalid = panel.document()
    invalid['gates'][0]['qubits'] = ['missing']
    with pytest.raises(ValueError):
        panel.load_document(invalid)
    assert panel.document()['gates'][0]['name'] == 'X'
    panel.close()


def test_add_rename_remove_qubit_keeps_referenced_qubit(app):
    panel = QuantumCircuitPanel()
    panel.load_document(document())
    panel.add_qubit()
    assert len(panel.document()['qubits']) == 2
    panel.qubit_list.item(1).setText('spin B')
    assert panel.document()['qubits'][1]['name'] == 'spin B'
    panel.qubit_list.setCurrentRow(0)
    panel.remove_qubit()
    assert len(panel.document()['qubits']) == 2
    assert 'used by a gate' in panel.error_label.text()
    panel.qubit_list.setCurrentRow(1)
    panel.remove_qubit()
    assert len(panel.document()['qubits']) == 1
    panel.close()


def test_invalid_qubit_rename_restores_visible_name(app):
    panel = QuantumCircuitPanel()
    panel.qubit_list.item(0).setText('')
    assert panel.document()['qubits'][0]['name'] == 'q1'
    assert panel.qubit_list.item(0).text() == 'q1'
    assert panel.error_label.text()
    panel.close()


def test_gate_dialog_preserves_all_pulse_fields(app):
    data = document()
    editor = GateEditor(data, data['gates'][0])
    assert editor.gate_data() == data['gates'][0]
    editor.awg_table.cellWidget(0, 1).setCurrentIndex(0)
    editor.awg_table.cellWidget(0, 2).setValue(-30.)
    editor.name_edit.setCurrentText('Init')
    editor.accept()
    assert editor.result() == QtWidgets.QDialog.Accepted
    result = editor.gate_data()
    assert result['awg'][0]['mode'] == 'absolute'
    assert result['awg'][0]['value_mv'] == -30.
    assert result['rf'] == data['gates'][0]['rf']
    assert data['gates'][0]['awg'][0]['value_mv'] == 15.
    editor.close()


@pytest.mark.parametrize('kind', ['no_qubits', 'outside_rf', 'outside_ramp', 'outside_acquisition', 'overlap'])
def test_gate_dialog_rejects_invalid_edits_without_changing_document(app, kind):
    data = document()
    data['gates'].append(gate('g2', 3.))
    original = copy.deepcopy(data)
    editor = GateEditor(data, data['gates'][0])
    if kind == 'no_qubits':
        editor.qubit_list.item(0).setCheckState(QtCore.Qt.Unchecked)
    elif kind == 'outside_rf':
        editor.rf_table.cellWidget(0, 2).setValue(3.)
    elif kind == 'outside_ramp':
        editor.awg_table.cellWidget(0, 3).setValue(3.)
    elif kind == 'outside_acquisition':
        editor.acquisition_duration.setValue(3.)
    else:
        editor.start_spin.setValue(3.)
    editor.accept()
    assert editor.result() != QtWidgets.QDialog.Accepted
    assert editor.error_label.text()
    assert data == original
    editor.close()


def test_awg_rf_add_remove_and_acquisition_toggle(app):
    editor = GateEditor(default_document())
    editor.add_awg()
    editor.add_awg()
    editor.add_rf()
    assert len(editor.gate_data()['awg']) == 2
    editor.awg_table.selectRow(0)
    editor._remove_selected(editor.awg_table)
    assert editor.gate_data()['awg'][0]['channel'] == 2
    editor.acquisition_check.setChecked(True)
    assert editor.acquisition_delay.isEnabled()
    assert editor.gate_data()['acquisition']['duration_us'] == 1.
    editor.acquisition_check.setChecked(False)
    assert editor.gate_data()['acquisition'] is None
    editor.close()


def test_panel_actual_add_edit_delete_dialog_path(app, monkeypatch):
    panel = QuantumCircuitPanel()
    emitted = []
    panel.document_changed.connect(emitted.append)
    def accept_new(editor):
        editor.add_awg(dict(channel=1, mode='relative', value_mv=25., ramp_us=.1))
        editor.accept()
        return editor.result()
    monkeypatch.setattr(GateEditor, 'exec_', accept_new)
    panel.add_gate()
    first = panel.document()['gates'][0]
    assert first['awg'][0]['value_mv'] == 25.
    assert panel.selected_gate_id() == first['id']
    def accept_edit(editor):
        editor.name_edit.setCurrentText('Y')
        editor.awg_table.cellWidget(0, 1).setCurrentIndex(0)
        editor.awg_table.cellWidget(0, 2).setValue(-45.)
        editor.accept()
        return editor.result()
    monkeypatch.setattr(GateEditor, 'exec_', accept_edit)
    panel.edit_gate(first['id'])
    changed = panel.document()['gates'][0]
    assert changed['name'] == 'Y'
    assert changed['awg'][0]['mode'] == 'absolute'
    assert changed['awg'][0]['value_mv'] == -45.
    panel.delete_gate(first['id'])
    assert panel.document()['gates'] == []
    assert len(emitted) == 3
    panel.close()


def test_cancelled_edit_is_noop(app, monkeypatch):
    panel = QuantumCircuitPanel()
    panel.load_document(document())
    before = panel.document()
    def cancel(editor):
        editor.name_edit.setCurrentText('Z')
        return QtWidgets.QDialog.Rejected
    monkeypatch.setattr(GateEditor, 'exec_', cancel)
    panel.edit_gate('g1')
    panel.add_gate()
    assert panel.document() == before
    panel.close()


def test_baseline_editor_rejects_duplicate_and_accepts_negative(app):
    editor = BaselineEditor(default_document())
    editor.add_row(1, 12.)
    editor.accept()
    assert editor.result() != QtWidgets.QDialog.Accepted
    assert 'Duplicate' in editor.error_label.text()
    editor.table.cellWidget(1, 0).setValue(2)
    editor.table.cellWidget(1, 1).setValue(-123.)
    editor.accept()
    assert editor.result() == QtWidgets.QDialog.Accepted
    assert editor.result_document['awg_baselines'][1] == dict(channel=2, voltage_mv=-123.)
    editor.close()


def test_shots_run_stop_settings_and_running_edit_guards(app, monkeypatch):
    panel = QuantumCircuitPanel()
    panel.load_document(document())
    panel.shots_spin.setValue(25)
    assert panel.document()['shots'] == 25
    called = []
    panel.run_requested.connect(lambda: called.append('run'))
    panel.stop_requested.connect(lambda: called.append('stop'))
    panel.execution_settings_requested.connect(lambda: called.append('settings'))
    panel.settings_button.click()
    panel.run_button.click()
    before = panel.document()
    panel.set_running(True)
    assert not panel.edit_controls.isEnabled()
    assert not panel.run_button.isEnabled()
    panel.add_gate()
    panel.edit_gate('g1')
    panel.delete_gate('g1')
    panel.add_qubit()
    assert panel.document() == before
    panel.stop_button.click()
    assert called == ['settings', 'run', 'stop']
    panel.set_running(False)
    assert panel.run_button.isEnabled()
    panel.close()


@pytest.mark.parametrize('action', ['Edit', 'Delete'])
def test_canvas_context_menu_is_exact_and_emits_gate_id(app, monkeypatch, action):
    view = QuantumCircuitView()
    view.set_document(document())
    emitted = []
    view.edit_requested.connect(lambda value: emitted.append(('Edit', value)))
    view.delete_requested.connect(lambda value: emitted.append(('Delete', value)))
    def choose(menu, position):
        assert [item.text() for item in menu.actions()] == ['Edit', 'Delete']
        return next(item for item in menu.actions() if item.text() == action)
    monkeypatch.setattr(QtWidgets.QMenu, 'exec_', choose)
    view.graphics_view._show_gate_menu('g1', QtCore.QPoint())
    assert emitted == [(action, 'g1')]
    view.close()


def test_canvas_has_linked_lanes_and_acquisition_only_label(app):
    view = QuantumCircuitView()
    view.resize(950, 800)
    view.show()
    view.set_document(document())
    app.processEvents()
    labels = [item.text() for item in view.graphics_view.scene().items()
              if isinstance(item, QtWidgets.QGraphicsSimpleTextItem)]
    assert 'Acquisition' in labels
    assert 'AWG 1' in labels
    assert 'RF 1' in labels
    assert not any('DDR' in label or 'trigger' in label for label in labels)
    assert 'q1' in labels
    assert 'X' in labels
    hits = [item for item in view.graphics_view.scene().items() if item.data(0) == 'g1']
    assert len(hits) >= 5
    view.close()


def test_canvas_cnot_and_multiqubit_readout_render(app):
    data = default_document()
    data['qubits'].append(dict(id='q2', name='spin B'))
    data['gates'] = [dict(gate(), name='CNOT', qubits=['q1', 'q2']),
                     dict(gate('g2', 3.), name='Readout', qubits=['q1', 'q2'])]
    view = QuantumCircuitView()
    view.set_document(data)
    gate_ids = {item.data(0) for item in view.graphics_view.scene().items() if item.data(0)}
    assert gate_ids == {'g1', 'g2'}
    view.close()


def test_cnot_editor_retains_and_reverses_control(app):
    data = document()
    data['qubits'].append(dict(id='q2', name='spin B'))
    data['gates'][0].update(name='CNOT', qubits=['q2', 'q1'])
    editor = GateEditor(data, data['gates'][0])
    assert editor.control_combo.currentData() == 'q2'
    assert editor.gate_data()['qubits'] == ['q2', 'q1']
    editor.control_combo.setCurrentIndex(editor.control_combo.findData('q1'))
    editor.accept()
    assert editor.result() == QtWidgets.QDialog.Accepted
    assert editor.gate_data()['qubits'] == ['q1', 'q2']
    assert data['gates'][0]['qubits'] == ['q2', 'q1']
    editor.close()


def test_cnot_editor_requires_two_qubits(app):
    editor = GateEditor(default_document())
    editor.name_edit.setCurrentText('CNOT')
    editor.accept()
    assert editor.result() != QtWidgets.QDialog.Accepted
    assert 'exactly two' in editor.error_label.text()
    editor.close()


def test_wait_preset_accepts_a_timed_gate_without_pulses(app):
    editor = GateEditor(default_document())
    assert editor.name_edit.findText('Wait') >= 0
    editor.name_edit.setCurrentText('Wait')
    editor.accept()
    assert editor.result() == QtWidgets.QDialog.Accepted
    data = editor.gate_data()
    assert data['name'] == 'Wait'
    assert data['awg'] == data['rf'] == []
    assert data['acquisition'] is None
    editor.close()


def test_unchanged_editor_preserves_imported_clock_exact_timing_and_values(app):
    data = document()
    data['gates'][0]['start_us'] = 31 / 300
    data['gates'][0]['awg'][0]['ramp_us'] = 7 / 300
    data['gates'][0]['awg'][0]['value_mv'] = 1.2345678912345678
    data['gates'][0]['rf'][0]['delay_us'] = 11 / 300
    editor = GateEditor(data, data['gates'][0])
    assert editor.gate_data() == data['gates'][0]
    editor.accept()
    assert editor.result() == QtWidgets.QDialog.Accepted
    assert editor.gate_data() == data['gates'][0]
    # An actual edit still updates the value rather than retaining the import.
    second = GateEditor(data, data['gates'][0])
    second.awg_table.cellWidget(0, 3).setValue(9 / 300)
    assert second.gate_data()['awg'][0]['ramp_us'] == 9 / 300
    editor.close()
    second.close()


def test_imported_finite_voltage_is_not_silently_clamped_by_editor(app):
    data = document()
    data['gates'][0]['awg'][0]['value_mv'] = 2e10 + .125
    editor = GateEditor(data, data['gates'][0])
    assert editor.gate_data()['awg'][0]['value_mv'] == 2e10 + .125
    editor.close()
    data['awg_baselines'][0]['voltage_mv'] = -2e10 - .125
    baseline = BaselineEditor(data)
    baseline.accept()
    assert baseline.result_document['awg_baselines'][0]['voltage_mv'] == -2e10 - .125
    baseline.close()


def test_nonadjacent_gate_does_not_cover_unselected_middle_qubit(app):
    data = default_document()
    data['qubits'] += [dict(id='q2', name='q2'), dict(id='q3', name='q3')]
    data['gates'] = [dict(id='outer', name='Init', qubits=['q1', 'q3'],
                          start_us=0., duration_us=2., awg=[], rf=[], acquisition=None),
                     dict(id='middle', name='H', qubits=['q2'],
                          start_us=0., duration_us=2., awg=[], rf=[], acquisition=None)]
    view = QuantumCircuitView()
    view.set_document(data)
    items = view.graphics_view.scene().items()
    q2_label = next(item for item in items
                    if isinstance(item, QtWidgets.QGraphicsSimpleTextItem) and item.text() == 'q2')
    q2_y = q2_label.pos().y() + 12.
    outer_boxes = [item for item in items if isinstance(item, QtWidgets.QGraphicsRectItem)
                   and item.data(0) == 'outer']
    assert len(outer_boxes) == 2
    assert all(not (box.rect().top() < q2_y < box.rect().bottom()) for box in outer_boxes)
    assert any(isinstance(item, QtWidgets.QGraphicsSimpleTextItem) and item.text() == 'H' for item in items)
    view.close()
