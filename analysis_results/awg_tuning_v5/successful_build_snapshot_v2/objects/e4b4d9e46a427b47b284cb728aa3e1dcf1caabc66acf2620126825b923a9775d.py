"""Quantum circuit editor and linked AWG/RF/acquisition timeline widgets.

This module edits a standalone document. Execution is owned by MainWindow;
none of the widgets talks directly to an instrument or changes AWG settings.
"""
from __future__ import annotations

import copy
import uuid

from PyQt5 import QtCore, QtGui, QtWidgets

try:
    from .quantum_circuit_model import default_document, validate_document, build_timeline
except ImportError:
    from quantum_circuit_model import default_document, validate_document, build_timeline
try:
    from .quantum_circuit_loops import sweep_axis, point_document
except ImportError:
    from quantum_circuit_loops import sweep_axis, point_document


GATE_PRESETS = ('Init', 'X', 'Y', 'Z', 'H', 'CNOT', 'CZ', 'Readout', 'Wait', 'Custom')
AWG_COLORS = ('#c54b48', '#bf8715', '#8c62b2', '#388165', '#527abb')


class _ExactDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    """Keep an imported float intact until the user actually changes the field.

    Qt rounds its internal value to the visible decimal precision. Timing from
    an existing clock grid must not be changed just by opening and accepting an
    editor, even when that rational number has no finite decimal expansion.
    """

    def __init__(self):
        super().__init__()
        self._exact_value = None
        self._display_value = None
        self.valueChanged.connect(self._changed)

    def _changed(self, _value):
        self._exact_value = None

    def setValue(self, value):
        super().setValue(value)
        self._display_value = super().value()
        self._exact_value = (float(value) if self.minimum() <= value <= self.maximum()
                             else self._display_value)

    def value(self):
        displayed = super().value()
        if self._exact_value is not None and displayed == self._display_value:
            return self._exact_value
        return displayed

    def textFromValue(self, value):
        # Compact display remains readable with enough precision for the loaded
        # tProcessor grids; the original float above is retained independently.
        return format(float(value), '.12g')


def _number(value=0., low=-1e9, high=1e9, decimals=12, suffix=''):
    widget = _ExactDoubleSpinBox()
    widget.setDecimals(decimals)
    # The model accepts finite imported values. Do not clamp a valid setting to
    # the ordinary editor range merely because its dialog was opened.
    widget.setRange(min(low, value), max(high, value))
    widget.setValue(value)
    widget.setSuffix(suffix)
    widget.setKeyboardTracking(False)
    return widget


def _channel(value=1):
    widget = QtWidgets.QSpinBox()
    widget.setRange(1, 64)
    widget.setValue(value)
    widget.setToolTip('Front-panel channel number (AWG 1 / RF 1).')
    return widget


def _button_row(*buttons):
    layout = QtWidgets.QHBoxLayout()
    for button in buttons:
        layout.addWidget(button)
    layout.addStretch(1)
    return layout


def _table(headers):
    table = QtWidgets.QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    table.verticalHeader().hide()
    table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
    table.horizontalHeader().setStretchLastSection(True)
    table.setMinimumHeight(125)
    return table


class GateEditor(QtWidgets.QDialog):
    """Transactional gate editor; invalid edits never change the document."""

    def __init__(self, document, gate=None, parent=None):
        super().__init__(parent)
        self._document = copy.deepcopy(document)
        self._original_id = gate.get('id') if gate else None
        self._gate_id = self._original_id or 'g_' + uuid.uuid4().hex[:12]
        self._result = None
        self.setWindowTitle('Edit Gate' if gate else 'Add Gate')
        self.resize(850, 670)
        self.setMinimumSize(590, 500)
        gate = gate or {
            'name': 'X', 'qubits': [document['qubits'][0]['id']],
            'start_us': max((g['start_us'] + g['duration_us']
                             for g in document['gates']), default=0.),
            'duration_us': 1., 'awg': [], 'rf': [], 'acquisition': None,
        }
        self._qubit_order = list(gate['qubits'])
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QComboBox()
        self.name_edit.setEditable(True)
        self.name_edit.addItems(GATE_PRESETS)
        self.name_edit.setCurrentText(gate['name'])
        form.addRow('Gate', self.name_edit)
        self.qubit_list = QtWidgets.QListWidget()
        self.qubit_list.setMaximumHeight(90)
        self.qubit_list.setToolTip('Choose the qubits acted on by this gate.')
        for qubit in document['qubits']:
            item = QtWidgets.QListWidgetItem(qubit['name'])
            item.setData(QtCore.Qt.UserRole, qubit['id'])
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked if qubit['id'] in gate['qubits']
                               else QtCore.Qt.Unchecked)
            self.qubit_list.addItem(item)
        form.addRow('Qubits', self.qubit_list)
        self.control_combo = QtWidgets.QComboBox()
        self.control_combo.setToolTip('The other selected qubit is the target.')
        form.addRow('Control (CNOT / CZ)', self.control_combo)
        self.qubit_list.itemChanged.connect(self._update_control)
        self.name_edit.currentTextChanged.connect(self._update_control)
        self._update_control()
        timing = QtWidgets.QWidget()
        timing_layout = QtWidgets.QHBoxLayout(timing)
        timing_layout.setContentsMargins(0, 0, 0, 0)
        self.start_spin = _number(gate['start_us'], 0., suffix=' µs')
        self.duration_spin = _number(gate['duration_us'], .000001, suffix=' µs')
        timing_layout.addWidget(QtWidgets.QLabel('Start'))
        timing_layout.addWidget(self.start_spin)
        timing_layout.addWidget(QtWidgets.QLabel('Duration'))
        timing_layout.addWidget(self.duration_spin)
        form.addRow('Timing', timing)
        layout.addLayout(form)
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs, 1)
        awg_page = QtWidgets.QWidget()
        awg_layout = QtWidgets.QVBoxLayout(awg_page)
        note = QtWidgets.QLabel('Absolute sets the voltage. Relative adds to the previous voltage on that AWG.\n'
                               'The voltage is held after the gate; ramp time starts at the gate start.')
        note.setWordWrap(True)
        awg_layout.addWidget(note)
        self.awg_table = _table(['AWG', 'Mode', 'Voltage / change (mV)', 'Ramp (µs)'])
        awg_layout.addWidget(self.awg_table, 1)
        add_awg = QtWidgets.QPushButton('Add AWG')
        remove_awg = QtWidgets.QPushButton('Remove')
        add_awg.clicked.connect(lambda: self.add_awg())
        remove_awg.clicked.connect(lambda: self._remove_selected(self.awg_table))
        awg_layout.addLayout(_button_row(add_awg, remove_awg))
        self.tabs.addTab(awg_page, 'AWG')
        rf_page = QtWidgets.QWidget()
        rf_layout = QtWidgets.QVBoxLayout(rf_page)
        rf_note = QtWidgets.QLabel('Delay is measured from the gate start. RF pulses must fit inside the gate.')
        rf_note.setWordWrap(True)
        rf_layout.addWidget(rf_note)
        self.rf_table = _table(['RF', 'Delay (µs)', 'Duration (µs)', 'Frequency (MHz)', 'Gain', 'Phase (°)'])
        self.rf_table.setToolTip('Attenuation and filter settings: AWG Tuning → RF Outputs.')
        rf_layout.addWidget(self.rf_table, 1)
        add_rf = QtWidgets.QPushButton('Add RF')
        remove_rf = QtWidgets.QPushButton('Remove')
        add_rf.clicked.connect(lambda: self.add_rf())
        remove_rf.clicked.connect(lambda: self._remove_selected(self.rf_table))
        rf_layout.addLayout(_button_row(add_rf, remove_rf))
        self.tabs.addTab(rf_page, 'RF')
        acquisition_page = QtWidgets.QWidget()
        acquisition_layout = QtWidgets.QFormLayout(acquisition_page)
        self.acquisition_check = QtWidgets.QCheckBox('Acquisition')
        acquisition = gate.get('acquisition')
        self.acquisition_check.setChecked(acquisition is not None)
        self.acquisition_delay = _number((acquisition or {}).get('delay_us', 0.), 0., suffix=' µs')
        self.acquisition_duration = _number((acquisition or {}).get('duration_us', gate['duration_us']),
                                            .000001, suffix=' µs')
        acquisition_layout.addRow(self.acquisition_check)
        acquisition_layout.addRow('Delay', self.acquisition_delay)
        acquisition_layout.addRow('Duration', self.acquisition_duration)
        self.acquisition_check.toggled.connect(self.acquisition_delay.setEnabled)
        self.acquisition_check.toggled.connect(self.acquisition_duration.setEnabled)
        self.acquisition_delay.setEnabled(acquisition is not None)
        self.acquisition_duration.setEnabled(acquisition is not None)
        self.tabs.addTab(acquisition_page, 'Acquisition')
        for event in gate.get('awg', []):
            self.add_awg(event)
        for event in gate.get('rf', []):
            self.add_rf(event)
        self.error_label = QtWidgets.QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet('color: #c54848;')
        layout.addWidget(self.error_label)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_awg(self, event=None):
        event = event or {}
        row = self.awg_table.rowCount()
        self.awg_table.insertRow(row)
        mode = QtWidgets.QComboBox()
        mode.addItem('Absolute', 'absolute')
        mode.addItem('Relative', 'relative')
        mode.setCurrentIndex(1 if event.get('mode') == 'relative' else 0)
        for column, widget in enumerate((
                _channel(event.get('channel', row + 1)), mode,
                _number(event.get('value_mv', 0.)), _number(event.get('ramp_us', 0.), 0.))):
            self.awg_table.setCellWidget(row, column, widget)
        self.awg_table.selectRow(row)

    def add_rf(self, event=None):
        event = event or {}
        row = self.rf_table.rowCount()
        self.rf_table.insertRow(row)
        gain = QtWidgets.QSpinBox()
        gain.setRange(-32768, 32767)
        gain.setValue(event.get('gain', 1000))
        for column, widget in enumerate((
                _channel(event.get('channel', row + 1)),
                _number(event.get('delay_us', 0.), 0.),
                _number(event.get('duration_us', self.duration_spin.value()), .000001),
                _number(event.get('frequency_mhz', 100.), 0.), gain,
                _number(event.get('phase_deg', 0.)))):
            self.rf_table.setCellWidget(row, column, widget)
        self.rf_table.selectRow(row)

    @staticmethod
    def _remove_selected(table):
        if table.currentRow() >= 0:
            table.removeRow(table.currentRow())

    def gate_data(self):
        if self._result is not None:
            return copy.deepcopy(self._result)
        qubits = [self.qubit_list.item(i).data(QtCore.Qt.UserRole)
                  for i in range(self.qubit_list.count())
                  if self.qubit_list.item(i).checkState() == QtCore.Qt.Checked]
        # Retain ordered qubit roles when editing an existing gate. CNOT/CZ may
        # explicitly reverse control and target without renaming physical qubits.
        order = {identifier: index for index, identifier in enumerate(self._qubit_order)}
        qubits.sort(key=lambda identifier: order.get(identifier, len(order)))
        if self.name_edit.currentText().strip().upper() in ('CNOT', 'CZ'):
            control = self.control_combo.currentData()
            if control in qubits:
                qubits = [control] + [identifier for identifier in qubits if identifier != control]
        awg = []
        for row in range(self.awg_table.rowCount()):
            awg.append(dict(channel=self.awg_table.cellWidget(row, 0).value(),
                            mode=self.awg_table.cellWidget(row, 1).currentData(),
                            value_mv=self.awg_table.cellWidget(row, 2).value(),
                            ramp_us=self.awg_table.cellWidget(row, 3).value()))
        rf = []
        for row in range(self.rf_table.rowCount()):
            rf.append(dict(zip(('channel', 'delay_us', 'duration_us', 'frequency_mhz', 'gain', 'phase_deg'),
                               (self.rf_table.cellWidget(row, c).value() for c in range(6)))))
        acquisition = (dict(delay_us=self.acquisition_delay.value(), duration_us=self.acquisition_duration.value())
                       if self.acquisition_check.isChecked() else None)
        return dict(id=self._gate_id, name=self.name_edit.currentText().strip(), qubits=qubits,
                    start_us=self.start_spin.value(), duration_us=self.duration_spin.value(),
                    awg=awg, rf=rf, acquisition=acquisition)

    def accept(self):
        gate = self.gate_data()
        if gate['name'].upper() in ('CNOT', 'CZ') and len(gate['qubits']) != 2:
            self.error_label.setText('Select exactly two qubits for CNOT / CZ, then choose the control.')
            return
        candidate = copy.deepcopy(self._document)
        candidate['gates'] = [g for g in candidate['gates'] if g['id'] != self._gate_id] + [gate]
        try:
            validated = validate_document(candidate)
        except ValueError as error:
            self.error_label.setText(str(error))
            return
        self._result = next(g for g in validated['gates'] if g['id'] == self._gate_id)
        super().accept()

    def _update_control(self, *unused):
        del unused
        selected = [(self.qubit_list.item(i).data(QtCore.Qt.UserRole), self.qubit_list.item(i).text())
                    for i in range(self.qubit_list.count())
                    if self.qubit_list.item(i).checkState() == QtCore.Qt.Checked]
        control = self.control_combo.currentData()
        if control is None and self._qubit_order:
            control = self._qubit_order[0]
        self.control_combo.clear()
        for identifier, name in selected:
            self.control_combo.addItem(name, identifier)
        index = self.control_combo.findData(control)
        if index >= 0:
            self.control_combo.setCurrentIndex(index)
        self.control_combo.setEnabled(self.name_edit.currentText().strip().upper() in ('CNOT', 'CZ'))


class BaselineEditor(QtWidgets.QDialog):
    def __init__(self, document, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Initial AWG voltages')
        self.resize(480, 340)
        self._document = copy.deepcopy(document)
        self.result_document = None
        layout = QtWidgets.QVBoxLayout(self)
        note = QtWidgets.QLabel('Relative changes start from these voltages. Unlisted AWGs start at 0 mV.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.table = _table(['AWG', 'Initial voltage (mV)'])
        layout.addWidget(self.table)
        for row in document.get('awg_baselines', []):
            self.add_row(row['channel'], row['voltage_mv'])
        add = QtWidgets.QPushButton('Add AWG')
        remove = QtWidgets.QPushButton('Remove')
        add.clicked.connect(lambda: self.add_row())
        remove.clicked.connect(lambda: GateEditor._remove_selected(self.table))
        layout.addLayout(_button_row(add, remove))
        self.error_label = QtWidgets.QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet('color: #c54848;')
        layout.addWidget(self.error_label)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_row(self, channel=None, voltage=0.):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setCellWidget(row, 0, _channel(channel or row + 1))
        self.table.setCellWidget(row, 1, _number(voltage))
        self.table.selectRow(row)

    def accept(self):
        candidate = copy.deepcopy(self._document)
        candidate['awg_baselines'] = [
            dict(channel=self.table.cellWidget(row, 0).value(), voltage_mv=self.table.cellWidget(row, 1).value())
            for row in range(self.table.rowCount())]
        try:
            self.result_document = validate_document(candidate)
        except ValueError as error:
            self.error_label.setText(str(error))
            return
        super().accept()


class LoopEditor(QtWidgets.QDialog):
    """Select a complete time block and its integer repeat/sweep counts."""

    def __init__(self, document, loop=None, selected=(), parent=None):
        super().__init__(parent)
        self._document = copy.deepcopy(document)
        self._id = loop['id'] if loop else 'l_' + uuid.uuid4().hex[:12]
        row = loop or dict(name='Loop', gate_ids=list(selected), count=2, sweep=None)
        self.result_document = None
        self.setWindowTitle('Edit Loop' if loop else 'Add Loop')
        self.resize(600, 530)
        layout = QtWidgets.QVBoxLayout(self)
        note = QtWidgets.QLabel('Select every gate in the repeated time interval. Gates after the block move with n.\n'
                               'Relative AWG changes continue from the preceding iteration. n = 0 skips the block.')
        note.setWordWrap(True)
        layout.addWidget(note)
        form = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit(row['name'])
        form.addRow('Name', self.name_edit)
        self.count_spin = QtWidgets.QSpinBox()
        self.count_spin.setRange(0, 1000000)
        self.count_spin.setValue(row['count'])
        form.addRow('Repeat n', self.count_spin)
        layout.addLayout(form)
        self.gate_list = QtWidgets.QListWidget()
        for gate in sorted(document['gates'], key=lambda g: (g['start_us'], g['id'])):
            item = QtWidgets.QListWidgetItem(f"{gate['name']} · {gate['start_us']:g}–{gate['start_us'] + gate['duration_us']:g} µs")
            item.setData(QtCore.Qt.UserRole, gate['id'])
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked if gate['id'] in row['gate_ids'] else QtCore.Qt.Unchecked)
            self.gate_list.addItem(item)
        layout.addWidget(self.gate_list, 1)
        self.sweep_group = QtWidgets.QGroupBox('Sweep n (inclusive integer range)')
        self.sweep_group.setCheckable(True)
        self.sweep_group.setChecked(row.get('sweep') is not None)
        sweep_form = QtWidgets.QFormLayout(self.sweep_group)
        self.sweep_spins = {}
        for key, default in (('start', 0), ('stop', 10), ('step', 1)):
            spin = QtWidgets.QSpinBox()
            spin.setRange(-1000000 if key == 'step' else 0, 1000000)
            spin.setValue((row.get('sweep') or {}).get(key, default))
            self.sweep_spins[key] = spin
            sweep_form.addRow(key.title(), spin)
        layout.addWidget(self.sweep_group)
        self.error_label = QtWidgets.QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet('color: #c54848;')
        layout.addWidget(self.error_label)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        candidate = copy.deepcopy(self._document)
        candidate['version'] = 2
        row = dict(id=self._id, name=self.name_edit.text(), count=self.count_spin.value(),
                   gate_ids=[self.gate_list.item(i).data(QtCore.Qt.UserRole)
                             for i in range(self.gate_list.count())
                             if self.gate_list.item(i).checkState() == QtCore.Qt.Checked],
                   sweep={key: spin.value() for key, spin in self.sweep_spins.items()}
                   if self.sweep_group.isChecked() else None)
        candidate['loops'] = [l for l in candidate.get('loops', []) if l['id'] != self._id] + [row]
        try:
            self.result_document = validate_document(candidate)
        except ValueError as error:
            self.error_label.setText(str(error))
            return
        super().accept()


class QuantumCircuitPanel(QtWidgets.QWidget):
    document_changed = QtCore.pyqtSignal(object)
    preview_changed = QtCore.pyqtSignal(object)
    selection_changed = QtCore.pyqtSignal(str)
    run_requested = QtCore.pyqtSignal()
    stop_requested = QtCore.pyqtSignal()
    show_program_requested = QtCore.pyqtSignal()
    execution_settings_requested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._document = default_document()
        self._loading = False
        self._running = False
        layout = QtWidgets.QVBoxLayout(self)
        self.edit_controls = QtWidgets.QWidget()
        edit_layout = QtWidgets.QVBoxLayout(self.edit_controls)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.addWidget(QtWidgets.QLabel('Qubits'))
        self.qubit_list = QtWidgets.QListWidget()
        self.qubit_list.setMaximumHeight(130)
        self.qubit_list.itemChanged.connect(self._rename_qubit)
        edit_layout.addWidget(self.qubit_list)
        self.add_qubit_button = QtWidgets.QPushButton('Add Qubit')
        self.remove_qubit_button = QtWidgets.QPushButton('Remove')
        self.add_qubit_button.clicked.connect(self.add_qubit)
        self.remove_qubit_button.clicked.connect(self.remove_qubit)
        edit_layout.addLayout(_button_row(self.add_qubit_button, self.remove_qubit_button))
        edit_layout.addWidget(QtWidgets.QLabel('Gates (one-pass times)'))
        self.gate_list = QtWidgets.QListWidget()
        self.gate_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.gate_list.setMinimumHeight(155)
        self.gate_list.itemDoubleClicked.connect(lambda item: self.edit_gate(item.data(QtCore.Qt.UserRole)))
        self.gate_list.currentItemChanged.connect(self._selection_changed)
        self.gate_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.gate_list.customContextMenuRequested.connect(self._gate_context_menu)
        edit_layout.addWidget(self.gate_list, 1)
        self.add_gate_button = QtWidgets.QPushButton('Add Gate')
        self.edit_gate_button = QtWidgets.QPushButton('Edit')
        self.delete_gate_button = QtWidgets.QPushButton('Delete')
        self.add_gate_button.clicked.connect(self.add_gate)
        self.edit_gate_button.clicked.connect(lambda: self.edit_gate(self.selected_gate_id()))
        self.delete_gate_button.clicked.connect(lambda: self.delete_gate(self.selected_gate_id()))
        edit_layout.addLayout(_button_row(self.add_gate_button, self.edit_gate_button, self.delete_gate_button))
        self.loop_list = QtWidgets.QListWidget()
        self.loop_list.setMaximumHeight(85)
        self.loop_list.itemDoubleClicked.connect(lambda item: self.edit_loop(item.data(QtCore.Qt.UserRole)))
        edit_layout.addWidget(self.loop_list)
        self.add_loop_button = QtWidgets.QPushButton('Add Loop')
        self.edit_loop_button = QtWidgets.QPushButton('Edit Loop')
        self.delete_loop_button = QtWidgets.QPushButton('Remove Loop')
        self.add_loop_button.clicked.connect(self.add_loop)
        self.edit_loop_button.clicked.connect(lambda: self.edit_loop(self.selected_loop_id()))
        self.delete_loop_button.clicked.connect(lambda: self.delete_loop(self.selected_loop_id()))
        edit_layout.addLayout(_button_row(self.add_loop_button, self.edit_loop_button, self.delete_loop_button))
        preview_row = QtWidgets.QHBoxLayout()
        preview_row.addWidget(QtWidgets.QLabel('Preview n'))
        self.preview_combo = QtWidgets.QComboBox()
        self.preview_combo.setToolTip('Preview one n value. Run executes every enabled sweep point, each as a linked QCoDeS Run.')
        self.preview_combo.currentIndexChanged.connect(self._preview_changed)
        preview_row.addWidget(self.preview_combo, 1)
        edit_layout.addLayout(preview_row)
        self.baselines_button = QtWidgets.QPushButton('Initial AWG voltages…')
        self.baselines_button.clicked.connect(self.edit_baselines)
        edit_layout.addWidget(self.baselines_button)
        self.baseline_label = QtWidgets.QLabel('Unlisted AWGs start at 0 mV.')
        self.baseline_label.setWordWrap(True)
        edit_layout.addWidget(self.baseline_label)
        shot_layout = QtWidgets.QFormLayout()
        self.shots_spin = QtWidgets.QSpinBox()
        self.shots_spin.setRange(1, 1000000)
        self.shots_spin.valueChanged.connect(self._shots_changed)
        shot_layout.addRow('Shots', self.shots_spin)
        edit_layout.addLayout(shot_layout)
        self.settings_button = QtWidgets.QPushButton('Execution settings…')
        self.settings_button.clicked.connect(self.execution_settings_requested)
        edit_layout.addWidget(self.settings_button)
        settings_note = QtWidgets.QLabel('AWG Tuning settings:\nConnection / compensation: Experiment\n'
                                        'RF routing / readout: RF Outputs / RF Readout')
        settings_note.setWordWrap(True)
        edit_layout.addWidget(settings_note)
        layout.addWidget(self.edit_controls, 1)
        self.error_label = QtWidgets.QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet('color: #c54848;')
        layout.addWidget(self.error_label)
        self.status_label = QtWidgets.QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.run_button = QtWidgets.QPushButton('Run')
        self.run_button.setToolTip('Run the circuit, or all n values when Loop sweep is enabled. Shots applies to every n.')
        self.stop_button = QtWidgets.QPushButton('Stop')
        self.run_button.clicked.connect(self.run_requested)
        self.stop_button.clicked.connect(self.stop_requested)
        self.stop_button.setEnabled(False)
        layout.addLayout(_button_row(self.run_button, self.stop_button))
        self._refresh()

    def document(self):
        return copy.deepcopy(self._document)

    def load_document(self, data):
        validated = validate_document(data)
        self._document = validated
        self.error_label.clear()
        self._refresh()
        self.document_changed.emit(self.document())
        self._preview_changed()

    def _commit(self, data, selected=None):
        try:
            validated = validate_document(data)
        except ValueError as error:
            self.error_label.setText(str(error))
            return False
        self._document = validated
        self.error_label.clear()
        self._refresh(selected)
        self.document_changed.emit(self.document())
        self._preview_changed()
        return True

    def _refresh(self, selected=None):
        self._loading = True
        selected = selected or self.selected_gate_id()
        self.qubit_list.clear()
        for qubit in self._document['qubits']:
            item = QtWidgets.QListWidgetItem(qubit['name'])
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            item.setData(QtCore.Qt.UserRole, qubit['id'])
            self.qubit_list.addItem(item)
        self.gate_list.clear()
        names = {q['id']: q['name'] for q in self._document['qubits']}
        for gate in sorted(self._document['gates'], key=lambda g: (g['start_us'], g['id'])):
            text = f"{gate['name']}  ·  {', '.join(names[q] for q in gate['qubits'])}\n{gate['start_us']:g}–{gate['start_us'] + gate['duration_us']:g} µs"
            item = QtWidgets.QListWidgetItem(text)
            item.setData(QtCore.Qt.UserRole, gate['id'])
            self.gate_list.addItem(item)
            if gate['id'] == selected:
                self.gate_list.setCurrentItem(item)
        self.shots_spin.setValue(self._document.get('shots', 1))
        selected_loop = self.selected_loop_id()
        self.loop_list.clear()
        for row in self._document.get('loops', []):
            sweep = row.get('sweep')
            description = f"n {sweep['start']} → {sweep['stop']} (step {sweep['step']})" if sweep else f"×{row['count']}"
            item = QtWidgets.QListWidgetItem(f"{row['name']} · {description}")
            item.setData(QtCore.Qt.UserRole, row['id'])
            self.loop_list.addItem(item)
            if row['id'] == selected_loop:
                self.loop_list.setCurrentItem(item)
        preview_index = max(0, self.preview_combo.currentIndex())
        self.preview_combo.clear()
        _, values = sweep_axis(self._document)
        for index, value in enumerate(values):
            self.preview_combo.addItem(f'{value}  (point {index + 1}/{len(values)})', index)
        if not values:
            self.preview_combo.addItem('Fixed counts', 0)
        self.preview_combo.setCurrentIndex(min(preview_index, self.preview_combo.count() - 1))
        self.preview_combo.setEnabled(bool(values))
        rows = self._document.get('awg_baselines', [])
        self.baseline_label.setText((' · '.join(f"AWG {r['channel']}: {r['voltage_mv']:g} mV" for r in rows) + '\n'
                                     if rows else '') + 'Unlisted AWGs start at 0 mV.')
        self.remove_qubit_button.setEnabled(len(self._document['qubits']) > 1)
        self._loading = False
        self._selection_changed(self.gate_list.currentItem(), None)
        self.run_button.setEnabled(bool(self._document['gates']) and not self._running)

    def selected_gate_id(self):
        item = self.gate_list.currentItem()
        return item.data(QtCore.Qt.UserRole) if item else ''

    def select_gate(self, gate_id):
        for index in range(self.gate_list.count()):
            item = self.gate_list.item(index)
            if item.data(QtCore.Qt.UserRole) == gate_id:
                self.gate_list.setCurrentItem(item)
                return

    def _selection_changed(self, item, previous):
        del previous
        valid = item is not None
        self.edit_gate_button.setEnabled(valid)
        self.delete_gate_button.setEnabled(valid)
        if valid and not self._loading:
            self.selection_changed.emit(item.data(QtCore.Qt.UserRole))

    def add_qubit(self):
        if self._running:
            return
        document = self.document()
        ids = {q['id'] for q in document['qubits']}
        names = {q['name'] for q in document['qubits']}
        index = 1
        while f'q{index}' in ids or f'q{index}' in names:
            index += 1
        document['qubits'].append(dict(id=f'q{index}', name=f'q{index}'))
        self._commit(document)
        self.qubit_list.setCurrentRow(self.qubit_list.count() - 1)

    def remove_qubit(self):
        if self._running or len(self._document['qubits']) <= 1:
            return
        item = self.qubit_list.currentItem()
        if not item:
            return
        qubit_id = item.data(QtCore.Qt.UserRole)
        if any(qubit_id in g['qubits'] for g in self._document['gates']):
            self.error_label.setText('This qubit is used by a gate. Edit or delete that gate first.')
            return
        document = self.document()
        document['qubits'] = [q for q in document['qubits'] if q['id'] != qubit_id]
        self._commit(document)

    def _rename_qubit(self, item):
        if self._loading or self._running:
            return
        document = self.document()
        for qubit in document['qubits']:
            if qubit['id'] == item.data(QtCore.Qt.UserRole):
                qubit['name'] = item.text().strip()
        if not self._commit(document):
            error = self.error_label.text()
            self._refresh()
            self.error_label.setText(error)

    def add_gate(self):
        if self._running:
            return
        dialog = GateEditor(self._document, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            gate = dialog.gate_data()
            document = self.document()
            document['gates'].append(gate)
            self._commit(document, gate['id'])

    def edit_gate(self, gate_id):
        if self._running:
            return
        gate = next((g for g in self._document['gates'] if g['id'] == gate_id), None)
        if gate is None:
            return
        dialog = GateEditor(self._document, gate, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            document = self.document()
            document['gates'] = [dialog.gate_data() if g['id'] == gate_id else g for g in document['gates']]
            self._commit(document, gate_id)

    def delete_gate(self, gate_id):
        if self._running or not gate_id:
            return
        document = self.document()
        document['gates'] = [g for g in document['gates'] if g['id'] != gate_id]
        if 'loops' in document:
            for row in document['loops']:
                row['gate_ids'] = [identifier for identifier in row['gate_ids'] if identifier != gate_id]
            document['loops'] = [row for row in document['loops'] if row['gate_ids']]
        self._commit(document)

    def selected_loop_id(self):
        item = self.loop_list.currentItem()
        return item.data(QtCore.Qt.UserRole) if item else ''

    def add_loop(self):
        if self._running:
            return
        selected = [item.data(QtCore.Qt.UserRole) for item in self.gate_list.selectedItems()]
        dialog = LoopEditor(self._document, selected=selected, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self._commit(dialog.result_document)

    def edit_loop(self, loop_id):
        if self._running:
            return
        row = next((l for l in self._document.get('loops', []) if l['id'] == loop_id), None)
        if row is None:
            return
        dialog = LoopEditor(self._document, loop=row, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self._commit(dialog.result_document)

    def delete_loop(self, loop_id):
        if self._running or not loop_id:
            return
        document = self.document()
        document['loops'] = [row for row in document.get('loops', []) if row['id'] != loop_id]
        self._commit(document)

    def _preview_changed(self, *_unused):
        if not self._loading:
            self.preview_changed.emit(point_document(self._document, max(0, self.preview_combo.currentIndex())))

    def edit_baselines(self):
        if self._running:
            return
        dialog = BaselineEditor(self._document, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self._commit(dialog.result_document)

    def _shots_changed(self, value):
        if not self._loading:
            document = self.document()
            document['shots'] = value
            self._commit(document)

    def _gate_context_menu(self, position):
        item = self.gate_list.itemAt(position)
        if item is None or self._running:
            return
        self.gate_list.setCurrentItem(item)
        menu = QtWidgets.QMenu(self)
        edit = menu.addAction('Edit')
        delete = menu.addAction('Delete')
        selected = menu.exec_(self.gate_list.viewport().mapToGlobal(position))
        if selected == edit:
            self.edit_gate(item.data(QtCore.Qt.UserRole))
        elif selected == delete:
            self.delete_gate(item.data(QtCore.Qt.UserRole))

    def set_running(self, running):
        self._running = bool(running)
        self.edit_controls.setEnabled(not running)
        self.run_button.setEnabled(not running and bool(self._document['gates']))
        self.stop_button.setEnabled(running)

    def set_status(self, text):
        self.status_label.setText(str(text))


class _CircuitGraphicsView(QtWidgets.QGraphicsView):
    edit_requested = QtCore.pyqtSignal(str)
    delete_requested = QtCore.pyqtSignal(str)
    selection_changed = QtCore.pyqtSignal(str)
    loop_edit_requested = QtCore.pyqtSignal(str)
    loop_delete_requested = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QtWidgets.QGraphicsScene(self))
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
        self.setMinimumSize(220, 220)

    def gate_at(self, position):
        for item in self.items(position):
            gate_id = item.data(0)
            if gate_id:
                return str(gate_id)
        return None

    def _show_gate_menu(self, gate_id, global_position):
        menu = QtWidgets.QMenu(self)
        edit = menu.addAction('Edit')
        delete = menu.addAction('Delete')
        action = menu.exec_(global_position)
        if action == edit:
            self.edit_requested.emit(gate_id)
        elif action == delete:
            self.delete_requested.emit(gate_id)

    def contextMenuEvent(self, event):
        gate_id = self.gate_at(event.pos())
        if gate_id:
            self.selection_changed.emit(gate_id)
            self._show_gate_menu(gate_id, event.globalPos())
            event.accept()
        else:
            loop_id = next((item.data(1) for item in self.items(event.pos()) if item.data(1)), None)
            if loop_id:
                menu = QtWidgets.QMenu(self)
                edit, delete = menu.addAction('Edit Loop'), menu.addAction('Remove Loop')
                action = menu.exec_(event.globalPos())
                if action == edit:
                    self.loop_edit_requested.emit(loop_id)
                elif action == delete:
                    self.loop_delete_requested.emit(loop_id)
                event.accept()
            else:
                event.ignore()

    def mouseDoubleClickEvent(self, event):
        gate_id = self.gate_at(event.pos())
        if gate_id and event.button() == QtCore.Qt.LeftButton:
            self.edit_requested.emit(gate_id)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        gate_id = self.gate_at(event.pos())
        if gate_id:
            self.selection_changed.emit(gate_id)
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        # Ctrl+wheel zooms; ordinary wheel retains predictable scrolling.
        if event.modifiers() & QtCore.Qt.ControlModifier:
            factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
            if .15 < self.transform().m11() * factor < 10.:
                self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)


class QuantumCircuitView(QtWidgets.QWidget):
    edit_requested = QtCore.pyqtSignal(str)
    delete_requested = QtCore.pyqtSignal(str)
    selection_changed = QtCore.pyqtSignal(str)
    loop_edit_requested = QtCore.pyqtSignal(str)
    loop_delete_requested = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._document = default_document()
        self._first_render = True
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        controls = QtWidgets.QHBoxLayout()
        self.summary_label = QtWidgets.QLabel()
        self.summary_label.setToolTip(
            'Requested digital output and acquisition timing. Run validates the loaded timing profile.\n'
            'Analog cable / RFDC delays are not calibrated by this editor.\n'
            'Apply RF attenuation / filter settings using the existing Front Panel Update.')
        controls.addWidget(self.summary_label, 1)
        for label, callback in (('−', lambda: self.graphics_view.scale(1 / 1.2, 1 / 1.2)),
                                ('+', lambda: self.graphics_view.scale(1.2, 1.2)),
                                ('Fit', self.fit_view)):
            button = QtWidgets.QPushButton(label)
            button.setMaximumWidth(48)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addLayout(controls)
        self.graphics_view = _CircuitGraphicsView()
        self.graphics_view.edit_requested.connect(self.edit_requested)
        self.graphics_view.delete_requested.connect(self.delete_requested)
        self.graphics_view.selection_changed.connect(self.selection_changed)
        self.graphics_view.loop_edit_requested.connect(self.loop_edit_requested)
        self.graphics_view.loop_delete_requested.connect(self.loop_delete_requested)
        layout.addWidget(self.graphics_view, 1)
        hint = QtWidgets.QLabel('Right-click a gate to edit or delete · Ctrl + wheel to zoom')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.set_document(self._document)

    def set_document(self, document):
        self._document = validate_document(document)
        self._draw()
        if self._first_render:
            self.fit_view()

    def fit_view(self):
        rect = self.graphics_view.scene().sceneRect()
        if rect.isEmpty():
            return
        # Preserve legible labels in narrow docks; horizontal scrolling is preferable
        # to shrinking a complete circuit until the labels cannot be read.
        fit_scale = min(self.graphics_view.viewport().width() / rect.width(),
                        self.graphics_view.viewport().height() / rect.height())
        fit_scale = max(.65, min(1.2, fit_scale * .96))
        self.graphics_view.resetTransform()
        self.graphics_view.scale(fit_scale, fit_scale)
        self.graphics_view.centerOn(rect.center())

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_render:
            self.fit_view()
            self._first_render = False

    def _draw(self):
        scene = self.graphics_view.scene()
        scene.clear()
        palette = self.palette()
        foreground = palette.color(QtGui.QPalette.Text)
        background = palette.color(QtGui.QPalette.Base)
        scene.setBackgroundBrush(background)
        timeline = build_timeline(self._document)
        duration = max(1., timeline['duration_us'])
        x0, x1 = 130., 130. + max(1000., len(timeline['gates']) * 48.)
        x = lambda time: x0 + float(time) / duration * (x1 - x0)
        font = QtGui.QFont(self.font())
        font.setPointSizeF(11.)
        small_font = QtGui.QFont(font)
        small_font.setPointSizeF(9.)
        reference_color = QtGui.QColor(foreground)
        reference_color.setAlpha(120)
        reference_pen = QtGui.QPen(reference_color, 1.)
        reference_pen.setCosmetic(True)
        text_items = []

        def text(label, xpos, ypos, color=foreground, small=False, gate_id=None):
            item = scene.addSimpleText(str(label), small_font if small else font)
            item.setBrush(QtGui.QBrush(color))
            item.setPos(xpos, ypos)
            if gate_id:
                item.setData(0, timeline.get('gate_origins', {}).get(gate_id, gate_id))
            text_items.append(item)
            return item

        def mark(item, gate_id, tooltip=''):
            item.setData(0, timeline.get('gate_origins', {}).get(gate_id, gate_id))
            item.setToolTip(tooltip)
            return item

        def zero_line(ypos, label):
            line = scene.addLine(x0, ypos, x1, ypos, reference_pen)
            line.setZValue(-.5)
            marker = text(label, x1 + 8., 0., reference_color, small=True)
            marker.setY(ypos - marker.boundingRect().height() / 2.)

        y = 60. if timeline.get('loops') else 32.
        lane_count = len(timeline['awg']) + len(timeline['rf']) + bool(timeline['acquisition'])
        if lane_count:
            title = text('Requested digital output and acquisition timing', 12., 2.)
            title.setToolTip(self.summary_label.toolTip())
        for lane_index, lane in enumerate(timeline['awg']):
            channel = lane['channel']
            color = QtGui.QColor(AWG_COLORS[lane_index % len(AWG_COLORS)])
            points = lane['points']
            values = [p[1] for p in points] or [0.]
            low, high = min(values), max(values)
            # Keep the real 0 mV reference in each lane, even for a waveform
            # that stays entirely above or below zero.
            scale_low, scale_high = min(low, 0.), max(high, 0.)
            span = max(scale_high - scale_low, 1.)
            mid = (scale_high + scale_low) / 2
            voltage_y = lambda voltage: y + 39. - (voltage - mid) / span * 46.
            text(f'AWG {channel}', 12., y + 10., color)
            text(f'{low:g} … {high:g} mV', 12., y + 34., color, small=True)
            zero_line(voltage_y(0.), '0 mV')
            path = QtGui.QPainterPath()
            if points:
                path.moveTo(x(points[0][0]), voltage_y(points[0][1]))
                for time, voltage in points[1:]:
                    path.lineTo(x(time), voltage_y(voltage))
            scene.addPath(path, QtGui.QPen(color, 2.))
            for event in lane['events']:
                rect = scene.addRect(x(event['start_us']), y + 8., max(8., x(event['end_us']) - x(event['start_us'])),
                                     54., QtGui.QPen(QtCore.Qt.NoPen), QtGui.QBrush(QtCore.Qt.transparent))
                mark(rect, event['gate_id'],
                     f"AWG {channel}: {event['start_mv']:g} → {event['target_mv']:g} mV\n"
                     f"{event['mode'].title()} {event['value_mv']:g} mV · Ramp {event['ramp_us']:g} µs")
            y += 83.
        for lane in timeline['rf']:
            text(f"RF {lane['channel']}", 12., y + 17.)
            zero_line(y + 56., '0')
            for event in lane['events']:
                color = QtGui.QColor('#4879bf')
                rect = scene.addRect(x(event['start_us']), y + 17.,
                                     max(4., x(event['end_us']) - x(event['start_us'])), 39.,
                                     QtGui.QPen(color.darker(130)), QtGui.QBrush(color))
                mark(rect, event['gate_id'],
                     f"RF {lane['channel']}: {event['start_us']:g}–{event['end_us']:g} µs\n"
                     f"{event['frequency_mhz']:g} MHz · Gain {event['gain']} · {event['phase_deg']:g}°")
            y += 74.
        if timeline['acquisition']:
            text('Acquisition', 12., y + 17.)
            zero_line(y + 56., '0')
            for event in timeline['acquisition']:
                color = QtGui.QColor('#26958e')
                rect = scene.addRect(x(event['start_us']), y + 17.,
                                     max(4., x(event['end_us']) - x(event['start_us'])), 39.,
                                     QtGui.QPen(color.darker(125)), QtGui.QBrush(color))
                mark(rect, event['gate_id'], f"{event['start_us']:g}–{event['end_us']:g} µs")
            y += 74.
        if lane_count:
            y += 16.
        else:
            text('Add AWG or RF settings to a gate to see its waveforms.', x0, y, small=True)
            y += 48.
        text('Circuit', 12., y)
        y += 42.
        qubit_y = {q['id']: y + i * 86. for i, q in enumerate(self._document['qubits'])}
        for qubit in self._document['qubits']:
            center_y = qubit_y[qubit['id']]
            text(qubit['name'], 12., center_y - 12.)
            scene.addLine(x0, center_y, x1, center_y, QtGui.QPen(foreground, 2.))
        for gate in timeline['gates']:
            ys = [qubit_y[q] for q in gate['qubits']]
            left, right = x(gate['start_us']), x(gate['start_us'] + gate['duration_us'])
            center_x = (left + right) / 2.
            tooltip = f"{gate['name']}: {gate['start_us']:g}–{gate['start_us'] + gate['duration_us']:g} µs"
            if gate['name'].upper() in ('CNOT', 'CZ') and len(ys) == 2:
                mark(scene.addLine(center_x, min(ys), center_x, max(ys), QtGui.QPen(foreground, 2.)), gate['id'], tooltip)
                mark(scene.addEllipse(center_x - 7., ys[0] - 7., 14., 14., QtGui.QPen(foreground),
                                      QtGui.QBrush(foreground)), gate['id'], tooltip)
                if gate['name'].upper() == 'CNOT':
                    mark(scene.addEllipse(center_x - 17., ys[1] - 17., 34., 34., QtGui.QPen(foreground, 2.),
                                          QtGui.QBrush(background)), gate['id'], tooltip)
                    mark(scene.addLine(center_x - 17., ys[1], center_x + 17., ys[1], QtGui.QPen(foreground, 2.)), gate['id'], tooltip)
                    mark(scene.addLine(center_x, ys[1] - 17., center_x, ys[1] + 17., QtGui.QPen(foreground, 2.)), gate['id'], tooltip)
                else:
                    mark(scene.addEllipse(center_x - 7., ys[1] - 7., 14., 14., QtGui.QPen(foreground),
                                          QtGui.QBrush(foreground)), gate['id'], tooltip)
                hit = scene.addRect(left, min(ys) - 28., max(right - left, 10.), max(ys) - min(ys) + 56.,
                                    QtGui.QPen(QtCore.Qt.NoPen), QtGui.QBrush(QtCore.Qt.transparent))
                mark(hit, gate['id'], tooltip)
            else:
                width = max(25., right - left - 8.)
                # Only fill boxes over selected adjacent wires. A q1/q3 gate
                # must not cover q2 or hide a simultaneous independent q2 gate.
                groups = []
                for wire_y in sorted(ys):
                    if groups and wire_y - groups[-1][-1] < 87.:
                        groups[-1].append(wire_y)
                    else:
                        groups.append([wire_y])
                if len(groups) > 1:
                    connector = scene.addLine(center_x, min(ys), center_x, max(ys), QtGui.QPen(foreground, 1.5))
                    mark(connector, gate['id'], tooltip)
                    connector.setZValue(-.25)
                for group in groups:
                    top, height = min(group) - 27., max(group) - min(group) + 54.
                    rect = scene.addRect(center_x - width / 2., top, width, height,
                                         QtGui.QPen(foreground, 1.5), QtGui.QBrush(background))
                    mark(rect, gate['id'], tooltip)
                    label = text(gate['name'], 0., 0., gate_id=gate['id'])
                    if label.boundingRect().width() > width - 8.:
                        metrics = QtGui.QFontMetrics(font)
                        label.setText(metrics.elidedText(gate['name'], QtCore.Qt.ElideRight, max(15, int(width - 8.))))
                    label.setPos(center_x - label.boundingRect().width() / 2., (min(group) + max(group)) / 2. - 11.)
                    label.setToolTip(tooltip)
        bottom = y + (len(self._document['qubits']) - 1) * 86. + 53.
        for region in timeline.get('loops', []):
            left, right = x(region['start_us']), x(region['end_us'])
            color = QtGui.QColor('#be8500')
            fill = QtGui.QColor('#ffcf55')
            fill.setAlpha(32)
            block = scene.addRect(left, 51., max(6., right - left), bottom - 48.,
                                  QtGui.QPen(color, 1.5), QtGui.QBrush(fill))
            block.setZValue(-2.)
            block.setData(1, region['id'])
            label = text(f"{region['name']} ×{region['count']}" + (' (skipped)' if not region['count'] else ''),
                         left + 4., 28., color, small=True)
            label.setData(1, region['id'])
            label.setToolTip('Right-click to edit or remove this loop. Gates are shown at their expanded times.')
            for repetition in range(1, min(region['count'], 200)):
                pos = x(region['start_us'] + repetition * region['period_us'])
                scene.addLine(pos, 51., pos, bottom, QtGui.QPen(color, .6, QtCore.Qt.DotLine)).setZValue(-1.)
        for index in range(11):
            time = duration * index / 10.
            xpos = x(time)
            scene.addLine(xpos, bottom - 2., xpos, bottom + 3., reference_pen)
            label = text(f'{time:g}', 0., bottom + 8., small=True)
            label.setPos(xpos - label.boundingRect().width() / 2., bottom + 8.)
        text('Time (µs)', (x0 + x1) / 2. - 34., bottom + 31., small=True)
        if not self._document['gates']:
            text('Add a gate from the left panel to begin.', x0 + 80., bottom + 66.)
            bottom += 42.
        scene.setSceneRect(0., 0., x1 + 76., bottom + 70.)
        self.summary_label.setText(f"{len(self._document['qubits'])} qubit{'s' if len(self._document['qubits']) != 1 else ''}"
                                   f" · {len(timeline['gates'])} gate instances · {timeline['duration_us']:g} µs")
