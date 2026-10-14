"""QICK update dialog. No connection or deployment occurs when it is opened."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from PyQt5 import QtCore, QtWidgets

try:
    from .qick_update import BoardUpdater, UpdateConnection, review_package
except ImportError:
    from qick_update import BoardUpdater, UpdateConnection, review_package


class _Worker(QtCore.QObject):
    progress = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, task):
        super().__init__()
        self.task = task

    @QtCore.pyqtSlot()
    def run(self):
        try:
            self.finished.emit(self.task(self.progress.emit))
        except Exception as exc:
            self.failed.emit(str(exc))


class RemoteDirectoryDialog(QtWidgets.QDialog):
    """One-folder-at-a-time SFTP browser opened by an explicit Browse action."""

    def __init__(self, connection, initial, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Select folder on ' + connection.host)
        self.resize(640, 470)
        self.connection = connection
        self.selected_path = None
        self._thread = self._worker = None
        self._busy = False
        self._loaded_path = None
        layout = QtWidgets.QVBoxLayout(self)
        row = QtWidgets.QHBoxLayout()
        self.path = QtWidgets.QLineEdit(initial)
        self.go = QtWidgets.QPushButton('Open')
        self.up = QtWidgets.QPushButton('Up')
        row.addWidget(self.path, 1)
        row.addWidget(self.go)
        row.addWidget(self.up)
        layout.addLayout(row)
        self.folders = QtWidgets.QListWidget()
        layout.addWidget(self.folders, 1)
        self.status = QtWidgets.QLabel('Only folder names are read; no files are changed.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.choose = QtWidgets.QPushButton('Select current folder')
        self.cancel = QtWidgets.QPushButton('Cancel')
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.choose)
        row.addWidget(self.cancel)
        layout.addLayout(row)
        self.go.clicked.connect(self._load)
        self.path.returnPressed.connect(self._load)
        self.path.textChanged.connect(lambda: self.choose.setEnabled(False))
        self.up.clicked.connect(self._up)
        self.folders.itemDoubleClicked.connect(self._enter)
        self.choose.clicked.connect(self._choose)
        self.cancel.clicked.connect(self.reject)
        self.choose.setEnabled(False)
        QtCore.QTimer.singleShot(0, self._load)

    def _up(self):
        self.path.setText(str(PurePosixPath(self.path.text()).parent))
        self._load()

    def _enter(self, item):
        self.path.setText(str(PurePosixPath(self._loaded_path) / item.text()))
        self._load()

    def _load(self):
        if self._busy:
            return
        path = self.path.text().strip()
        self._loaded_path = None
        self._busy = True
        self.choose.setEnabled(False)
        for widget in (self.path, self.go, self.up, self.folders, self.cancel):
            widget.setEnabled(False)
        self.status.setText('Reading board folders…')
        def task(progress):
            with BoardUpdater(self.connection, progress) as updater:
                return updater.list_directories(path)
        self._thread = QtCore.QThread(self)
        self._worker = _Worker(task)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._loaded)
        self._worker.failed.connect(self.status.setText)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._idle)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _loaded(self, result):
        self._loaded_path = result['path']
        self.path.setText(self._loaded_path)
        self.folders.clear()
        self.folders.addItems(result['directories'])
        self.status.setText('Double-click a subfolder, or select the current folder.')

    def _idle(self):
        self._thread = self._worker = None
        self._busy = False
        for widget in (self.path, self.go, self.up, self.folders, self.cancel):
            widget.setEnabled(True)
        self.choose.setEnabled(self._loaded_path not in (None, '/'))

    def _choose(self):
        if not self._busy and self._loaded_path == self.path.text().strip():
            self.selected_path = self._loaded_path
            self.accept()

    def reject(self):
        if not self._busy:
            super().reject()

    def closeEvent(self, event):
        if self._busy:
            event.ignore()
        else:
            super().closeEvent(event)


class QickUpdateDialog(QtWidgets.QDialog):
    """Modal maintenance UI; the main experiment window stays disabled."""
    board_changed = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, *, host='192.168.2.99', ns_port=8888,
                 proxy_name='myqick', is_busy=None):
        super().__init__(parent)
        self.setWindowTitle('QICK Library and Firmware Update')
        self.setModal(True)
        self.resize(880, 830)
        self._is_busy = is_busy or (lambda: False)
        self._thread = self._worker = None
        self._review = self._prepared = None
        self._action = None
        self._last_result = None
        self._ns_port, self._proxy_name = ns_port, proxy_name
        self._busy = False
        layout = QtWidgets.QVBoxLayout(self)
        notice = QtWidgets.QLabel(
            'Update the board QICK library and its matching BIT/HWH together. '
            'Opening this window does not connect, transfer files, or restart QICK. '
            'Experiment settings and results are not included in the update.')
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.inputs = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(self.inputs)
        form.setContentsMargins(0, 0, 0, 0)
        self.host = QtWidgets.QLineEdit(host)
        self.user = QtWidgets.QLineEdit('root')
        self.port = QtWidgets.QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(22)
        connection_row = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(connection_row)
        row.setContentsMargins(0, 0, 0, 0)
        for title, widget in [('Host', self.host), ('User', self.user), ('Port', self.port)]:
            row.addWidget(QtWidgets.QLabel(title))
            row.addWidget(widget)
        form.addRow('SSH connection', connection_row)
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password.setPlaceholderText('Not saved; leave blank to use an SSH key')
        form.addRow('Password', self.password)
        default_repo = Path(__file__).resolve().parents[2] / 'QSTL_QICK'
        self.repo = QtWidgets.QLineEdit(str(default_repo))
        self.manifest = QtWidgets.QLineEdit(str(default_repo / 'qick/firmware/projects/qstl_awg_v4/build_manifest.json'))
        form.addRow('Local QSTL_QICK', self._browse_row(self.repo, directory=True))
        form.addRow('Firmware build manifest', self._browse_row(self.manifest))
        self.remote_repo = QtWidgets.QLineEdit('/home/QSTL_QICK')
        self.remote_bit = QtWidgets.QLineEdit('qick/firmware/projects/qstl_awg_v4/bitstream.bit')
        self.python = QtWidgets.QLineEdit('/usr/local/share/pynq-venv/bin/python3')
        form.addRow('Board repository', self._remote_browse_row(self.remote_repo))
        form.addRow('BIT path within repository', self._remote_browse_row(self.remote_bit, firmware=True))
        form.addRow('Board Python', self.python)
        path_note = QtWidgets.QLabel(
            'The HWH uses the same folder and filename stem as the BIT. The board launcher '
            'must load this exact BIT path. The updater does not rewrite notebook cells or launch commands.')
        path_note.setWordWrap(True)
        form.addRow(path_note)
        self.outputs_stopped = QtWidgets.QCheckBox('Experiments and outputs are stopped, including other clients.')
        self.server_stopped = QtWidgets.QCheckBox('The QICK server is stopped; I will restart it manually after the update.')
        form.addRow(self.outputs_stopped)
        form.addRow(self.server_stopped)
        self.transactions = QtWidgets.QComboBox()
        self.transactions.addItem('Inspect board to list retained backups', None)
        form.addRow('Prepared update / backup', self.transactions)
        self.path_summary = QtWidgets.QLabel()
        self.path_summary.setWordWrap(True)
        self.path_summary.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        form.addRow('Source → destination', self.path_summary)
        layout.addWidget(self.inputs)
        buttons = QtWidgets.QGridLayout()
        self.inspect_button = QtWidgets.QPushButton('1. Inspect board')
        self.review_button = QtWidgets.QPushButton('2. Review local package')
        self.prepare_button = QtWidgets.QPushButton('3. Upload and verify staging')
        self.apply_button = QtWidgets.QPushButton('4. Apply prepared update…')
        self.verify_button = QtWidgets.QPushButton('Verify running firmware')
        self.rollback_button = QtWidgets.QPushButton('Restore selected backup…')
        self.buttons = [self.inspect_button, self.review_button, self.prepare_button,
                        self.apply_button, self.verify_button, self.rollback_button]
        for index, button in enumerate(self.buttons):
            buttons.addWidget(button, index // 3, index % 3)
        layout.addLayout(buttons)
        self.status = QtWidgets.QLabel('Ready — no actions have been run.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.details = QtWidgets.QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText('Package review, progress, and board results appear here. Passwords are not logged.')
        layout.addWidget(self.details, 1)
        self.close_button = QtWidgets.QPushButton('Close')
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(self.close_button, alignment=QtCore.Qt.AlignRight)
        self.inspect_button.clicked.connect(lambda: self._start('inspect'))
        self.review_button.clicked.connect(lambda: self._start('review'))
        self.prepare_button.clicked.connect(lambda: self._start('prepare'))
        self.apply_button.clicked.connect(lambda: self._confirm('apply'))
        self.verify_button.clicked.connect(lambda: self._start('verify'))
        self.rollback_button.clicked.connect(lambda: self._confirm('rollback'))
        self.repo.textChanged.connect(self._local_changed)
        self.manifest.textChanged.connect(self._local_changed)
        for entry in (self.host, self.user, self.remote_repo, self.remote_bit, self.python):
            entry.textChanged.connect(self._connection_changed)
        self.port.valueChanged.connect(self._connection_changed)
        self.outputs_stopped.toggled.connect(self._refresh)
        self.server_stopped.toggled.connect(self._refresh)
        self.transactions.currentIndexChanged.connect(self._select_transaction)
        self._refresh()

    def _browse_row(self, edit, directory=False):
        widget = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(edit)
        button = QtWidgets.QPushButton('Browse…')
        row.addWidget(button)
        def choose():
            if directory:
                selected = QtWidgets.QFileDialog.getExistingDirectory(self, 'QSTL_QICK repository', edit.text())
            else:
                selected, _ = QtWidgets.QFileDialog.getOpenFileName(
                    self, 'Validated firmware manifest', edit.text(), 'Build manifest (build_manifest.json)')
            if selected:
                edit.setText(selected)
        button.clicked.connect(choose)
        return widget

    def _connection(self):
        return UpdateConnection(host=self.host.text().strip(), username=self.user.text().strip(),
            port=self.port.value(), password=self.password.text(), remote_repo=self.remote_repo.text().strip(),
            python=self.python.text().strip(), remote_bit=self.remote_bit.text().strip(),
            ns_port=self._ns_port, proxy_name=self._proxy_name)

    def _remote_browse_row(self, edit, firmware=False):
        widget = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(edit)
        button = QtWidgets.QPushButton('Browse board…')
        row.addWidget(button)
        def browse():
            if self._busy or self._is_busy():
                return
            root = PurePosixPath(self.remote_repo.text().strip())
            bit = PurePosixPath(self.remote_bit.text().strip())
            initial = str(root / 'qick/firmware') if firmware else str(root)
            dialog = RemoteDirectoryDialog(self._connection(), initial, self)
            accepted = dialog.exec_() == QtWidgets.QDialog.Accepted
            selected_path = dialog.selected_path
            dialog.deleteLater()
            if not accepted:
                return
            selected = PurePosixPath(selected_path)
            if firmware:
                try:
                    selected.relative_to(root / 'qick/firmware')
                    relative = selected.relative_to(root) / (bit.name or 'bitstream.bit')
                except ValueError:
                    QtWidgets.QMessageBox.warning(self, 'Invalid folder',
                        'Select a folder below the board repository qick/firmware directory.')
                    return
                edit.setText(str(relative))
            else:
                edit.setText(str(selected))
        button.clicked.connect(browse)
        return widget

    def _local_changed(self, *_):
        self._review = self._prepared = None
        self._refresh()

    def _connection_changed(self, *_):
        self._prepared = None
        self.outputs_stopped.setChecked(False)
        self.server_stopped.setChecked(False)
        self.transactions.blockSignals(True)
        self.transactions.clear()
        self.transactions.addItem('Inspect board again after changing the target', None)
        self.transactions.blockSignals(False)
        self._refresh()

    def _select_transaction(self, *_):
        item = self.transactions.currentData()
        self._prepared = item
        if item:
            self.remote_bit.blockSignals(True)
            self.remote_bit.setText(item['firmware'])
            self.remote_bit.blockSignals(False)
            self.details.appendPlainText('Selected board transaction:\n' + json.dumps(item, indent=2))
        self._refresh()

    def _refresh(self, *_):
        root = PurePosixPath(self.remote_repo.text().strip())
        bit = root / (self.remote_bit.text().strip() or 'bitstream.bit')
        hwh = bit.with_suffix('.hwh') if bit.name else '(select a BIT filename)'
        local_fw = Path(self.manifest.text()).parent
        self.path_summary.setText(
            str(Path(self.repo.text()) / 'qick/qick_lib') + ' → ' + str(root / 'qick/qick_lib')
            + '\n' + str(local_fw / 'bitstream.bit') + ' → ' + str(bit)
            + '\n' + str(local_fw / 'bitstream.hwh') + ' → ' + str(hwh))
        self.inputs.setEnabled(not self._busy)
        for button in self.buttons:
            button.setEnabled(not self._busy)
        self.close_button.setEnabled(not self._busy)
        self.prepare_button.setEnabled(not self._busy and self._review is not None)
        state = self._prepared.get('state') if self._prepared else None
        confirmed = self.outputs_stopped.isChecked() and self.server_stopped.isChecked()
        matched = (self._prepared is not None and self._review is not None
                   and self._prepared.get('identity') == self._review['identity'])
        self.apply_button.setEnabled(not self._busy and state == 'prepared' and confirmed and matched)
        installed = state in ('applied', 'files_updated_restart_required')
        self.verify_button.setEnabled(not self._busy and installed)
        self.rollback_button.setEnabled(not self._busy and installed and confirmed)

    def _confirm(self, action):
        if not self._prepared or not self.outputs_stopped.isChecked():
            return
        if action == 'apply' and (not self._review or
                self._prepared.get('identity') != self._review['identity']):
            QtWidgets.QMessageBox.warning(self, 'Review required',
                'Review the same local package as the selected prepared transaction first.')
            return
        verb = 'Replace the board library and BIT/HWH' if action == 'apply' else 'Restore the retained board library and BIT/HWH'
        restart = ('Files will be changed only. Restart the QICK Python process manually with the selected BIT, '
                   'then verify it here. Restart this GUI before using outputs again.')
        source = (self.path_summary.text() if action == 'apply' else
                  'Source: retained backup for transaction ' + self._prepared['release']
                  + '\nTarget: ' + self.remote_repo.text().strip() + '/qick/qick_lib and '
                  + self.remote_bit.text().strip() + ' + matching HWH')
        text = (verb + '?\n\nTarget: ' + self.host.text().strip() + '\nRepository: ' + self.remote_repo.text().strip()
                + '\n' + source + '\nTransaction: ' + self._prepared['release']
                + '\n\n' + restart + '\nPrevious files and transaction evidence are retained. Experiments are not resumed automatically.')
        if QtWidgets.QMessageBox.question(self, 'Confirm board update', text,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            self._start(action)

    def _start(self, action):
        if self._busy or self._is_busy():
            QtWidgets.QMessageBox.information(self, 'QICK busy', 'Wait for the current experiment or QICK task to finish.')
            return
        connection = self._connection()
        repo, manifest = self.repo.text(), self.manifest.text()
        reviewed, prepared = self._review, self._prepared
        stopped = self.server_stopped.isChecked()
        def task(progress):
            if action == 'review':
                progress('Reviewing local hashes, the BIT/HWH/XSA pair, and the GUI library.')
                return review_package(repo, manifest)
            with BoardUpdater(connection, progress) as updater:
                if action == 'inspect':
                    return updater.inspect()
                if action == 'prepare':
                    return updater.prepare(reviewed)
                if action == 'apply':
                    return updater.apply(prepared['release'], stopped)
                if action == 'rollback':
                    return updater.rollback(prepared['release'], stopped)
                return updater.verify(prepared['release'])
        self._busy, self._action, self._last_result = True, action, None
        self._refresh()
        self.status.setText(action.capitalize() + ' in progress…')
        self._thread = QtCore.QThread(self)
        self._worker = _Worker(task)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.details.appendPlainText)
        self._worker.finished.connect(self._finished)
        self._worker.failed.connect(self._failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._idle)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _finished(self, result):
        self._last_result = result
        if self._action == 'review':
            self._review = result
            m = result['manifest']
            summary = {k: result[k] for k in ('repo', 'manifest_path', 'file_count', 'total_bytes', 'identity', 'setup_wns_ns', 'hold_whs_ns')}
            summary.update(library_version=m['library_version'], firmware_timestamp=m['firmware_timestamp'])
            self.details.appendPlainText(json.dumps(summary, indent=2))
            self.status.setText('Local package reviewed. Nothing has been transferred.')
        elif self._action == 'inspect':
            self.details.appendPlainText(json.dumps(result, indent=2))
            self.transactions.blockSignals(True)
            self.transactions.clear()
            self.transactions.addItem('Select a transaction to verify or restore', None)
            for item in result['transactions']:
                self.transactions.addItem(item['release'][:12] + ' — ' + item['state'], item)
            self.transactions.blockSignals(False)
            self._prepared = None
            self.status.setText('Board inspected. No files or output settings changed.')
        else:
            if self._action == 'prepare':
                self._prepared = result
            elif self._prepared:
                self._prepared.update(result)
            self.details.appendPlainText(json.dumps({k: v for k, v in result.items() if k != 'manifest'}, indent=2))
            state = result['state']
            messages = {
                'prepared': 'Upload verified. Live library and firmware are unchanged. Review Apply to install.',
                'files_updated_restart_required': 'Files updated; FPGA application is NOT verified. Restart QICK with the selected BIT, then click Verify running firmware.',
                'applied': 'Files and running firmware identity verified. Restart this GUI before using outputs. No output or analog test was run.',
                'rolled_back_restart_required': 'Previous files restored. Restart QICK manually, then restart this GUI before using outputs.',
            }
            self.status.setText(messages.get(state, state))
            if self._action in ('apply', 'rollback', 'verify'):
                self.outputs_stopped.setChecked(False)
                self.server_stopped.setChecked(False)
                self.board_changed.emit(state)

    def _failed(self, message):
        self.status.setText('Failed — inspect the details and board state before another update.')
        self.details.appendPlainText('ERROR: ' + message)
        if self._action in ('apply', 'rollback'):
            self._prepared = None
            self.board_changed.emit('unknown_after_failure')
        QtWidgets.QMessageBox.warning(self, 'QICK update failed', message)

    def _idle(self):
        self._thread = self._worker = None
        self._busy = False
        self._refresh()

    def reject(self):
        if self._busy:
            return
        self.password.clear()
        super().reject()

    def closeEvent(self, event):
        if self._busy:
            event.ignore()
            return
        self.password.clear()
        super().closeEvent(event)
