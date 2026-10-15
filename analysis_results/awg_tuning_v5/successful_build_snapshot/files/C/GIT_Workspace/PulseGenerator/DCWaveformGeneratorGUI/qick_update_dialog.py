"""QICK update dialog. No connection or deployment occurs when it is opened."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from PyQt5 import QtCore, QtWidgets

try:
    from .qick_update import BoardUpdater, UpdateConnection, review_package, repository_root, firmware_versions
except ImportError:
    from qick_update import BoardUpdater, UpdateConnection, review_package, repository_root, firmware_versions


class _Worker(QtCore.QObject):
    progress = QtCore.pyqtSignal(object)
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


class UpdateConfirmationDialog(QtWidgets.QDialog):
    """Both stop conditions must be confirmed for each Update click."""

    def __init__(self, host, firmware, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Confirm server and experiment status')
        self.setMinimumWidth(540)
        layout = QtWidgets.QVBoxLayout(self)
        text = QtWidgets.QLabel(
            'Make sure the QICK server is stopped and no experiment or output is running.')
        text.setWordWrap(True)
        layout.addWidget(text)
        self.server_stopped = QtWidgets.QCheckBox('The QICK server is stopped.')
        self.experiments_stopped = QtWidgets.QCheckBox(
            'No experiment or output is running, including notebooks and other clients.')
        layout.addWidget(self.server_stopped)
        layout.addWidget(self.experiments_stopped)
        details = QtWidgets.QLabel(
            'Board: ' + host + '\nFirmware: ' + firmware + '\n\n'
            'The library and entire firmware folder will be backed up and updated.\n'
            'Start QICK manually after completion.')
        details.setWordWrap(True)
        layout.addWidget(details)
        self.buttons = QtWidgets.QDialogButtonBox()
        self.confirm = self.buttons.addButton('Confirmed — Update', QtWidgets.QDialogButtonBox.AcceptRole)
        self.cancel = self.buttons.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.confirm.setAutoDefault(False)
        self.cancel.setDefault(True)
        self.confirm.setEnabled(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        for checkbox in (self.server_stopped, self.experiments_stopped):
            checkbox.toggled.connect(lambda: self.confirm.setEnabled(
                self.server_stopped.isChecked() and self.experiments_stopped.isChecked()))

    def accept(self):
        if self.server_stopped.isChecked() and self.experiments_stopped.isChecked():
            super().accept()


class QickUpdateDialog(QtWidgets.QDialog):
    """One explicit Update action; opening the dialog performs only local discovery."""
    board_changed = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, *, host='192.168.2.99', ns_port=8888,
                 proxy_name='myqick', is_busy=None):
        super().__init__(parent)
        self.setWindowTitle('QICK Library and Firmware Update')
        self.setModal(True)
        self.resize(880, 650)
        self._is_busy = is_busy or (lambda: False)
        self._thread = self._worker = None
        self._busy = self._applying = False
        self._last_result = None
        self._last_phase = None
        self._ns_port, self._proxy_name = ns_port, proxy_name
        layout = QtWidgets.QVBoxLayout(self)
        notice = QtWidgets.QLabel(
            'Update the QICK library and entire firmware folder. Installation metadata and '
            'editable links are retained. Select the firmware to use when you next start QICK. '
            'The server is not started or stopped by this window.')
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
        form.addRow('Local QSTL_QICK or qick', self._browse_row(self.repo))
        self.remote_repo = QtWidgets.QLineEdit('/home/QSTL_QICK')
        form.addRow('Board QSTL_QICK or qick', self._browse_row(self.remote_repo, remote=True))
        self.firmware = QtWidgets.QComboBox()
        self.firmware.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.firmware.setMinimumContentsLength(30)
        form.addRow('Firmware version', self.firmware)
        self.python = QtWidgets.QLineEdit('/usr/local/share/pynq-venv/bin/python3')
        form.addRow('Board Python', self.python)
        self.path_summary = QtWidgets.QLabel()
        self.path_summary.setWordWrap(True)
        self.path_summary.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        form.addRow('Update destination', self.path_summary)
        layout.addWidget(self.inputs)
        self.update_button = QtWidgets.QPushButton('Update')
        self.update_button.setAutoDefault(False)
        layout.addWidget(self.update_button)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat('%p%')
        layout.addWidget(self.progress_bar)
        self.status = QtWidgets.QLabel('Ready — no board connection or update has been run.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.details = QtWidgets.QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText('Update progress and backup location appear here.')
        layout.addWidget(self.details, 1)
        self._scan_timer = QtCore.QTimer(self)
        self._scan_timer.setSingleShot(True)
        self._scan_timer.setInterval(250)
        self._scan_timer.timeout.connect(self._load_versions)
        self.repo.textChanged.connect(lambda: self._scan_timer.start())
        self.repo.textChanged.connect(self._invalidate_versions)
        self.firmware.currentIndexChanged.connect(self._refresh)
        self.remote_repo.textChanged.connect(self._refresh)
        self.update_button.clicked.connect(self._confirm_update)
        self._load_versions()

    def _browse_row(self, edit, remote=False):
        widget = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(edit)
        button = QtWidgets.QPushButton('Browse board…' if remote else 'Browse…')
        button.setAutoDefault(False)
        row.addWidget(button)
        def choose():
            if self._busy or self._is_busy():
                return
            if remote:
                dialog = RemoteDirectoryDialog(self._connection(), edit.text().strip(), self)
                accepted = dialog.exec_() == QtWidgets.QDialog.Accepted
                selected = dialog.selected_path if accepted else None
                dialog.deleteLater()
            else:
                selected = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select QSTL_QICK or qick', edit.text())
            if selected:
                edit.setText(selected)
        button.clicked.connect(choose)
        return widget

    def _invalidate_versions(self):
        self.firmware.clear()
        self._refresh()

    def _load_versions(self):
        previous = self.firmware.currentData()
        self.firmware.blockSignals(True)
        self.firmware.clear()
        try:
            versions = firmware_versions(self.repo.text().strip())
            for entry in versions:
                self.firmware.addItem(entry['label'], entry['bit'])
                self.firmware.setItemData(self.firmware.count() - 1,
                    entry['bit'] + (' — build manifest available' if entry['has_manifest']
                                    else ' — no build manifest; file pair checks only'), QtCore.Qt.ToolTipRole)
            preferred = previous or 'projects/qstl_awg_v4/bitstream.bit'
            index = self.firmware.findData(preferred)
            self.firmware.setCurrentIndex(index if index >= 0 else 0)
            if not versions:
                self.status.setText('No matching BIT/HWH pairs found in the local qick/firmware folder.')
            else:
                self.status.setText(f'{len(versions)} firmware versions found. Select a version, then click Update.')
        except (OSError, ValueError) as exc:
            self.status.setText('Cannot read local firmware versions: ' + str(exc))
        finally:
            self.firmware.blockSignals(False)
        self._refresh()

    def _connection(self):
        relative = self.firmware.currentData() or 'projects/qstl_awg_v4/bitstream.bit'
        return UpdateConnection(host=self.host.text().strip(), username=self.user.text().strip(),
            port=self.port.value(), password=self.password.text(), remote_repo=self.remote_repo.text().strip(),
            python=self.python.text().strip(), remote_bit='qick/firmware/' + relative,
            ns_port=self._ns_port, proxy_name=self._proxy_name)

    def _refresh(self, *_):
        root = PurePosixPath(self.remote_repo.text().strip())
        if root.name == 'qick':
            root = root.parent
        active = self.firmware.currentData()
        self.path_summary.setText(str(root / 'qick/qick_lib/qick') + '\n'
            + str(root / 'qick/firmware') + ' (entire folder)\n'
            + 'pyro_cli.py → ' + (str(root / 'qick/firmware' / active) if active else '(select firmware)'))
        self.inputs.setEnabled(not self._busy)
        self.update_button.setEnabled(not self._busy and active is not None)

    def _confirm_update(self):
        if self._busy or self._is_busy():
            self.status.setText('Wait for the current experiment or QICK task to finish.')
            return
        if not self.firmware.currentData():
            return
        box = UpdateConfirmationDialog(self.host.text().strip(), self.firmware.currentText(), self)
        accepted = box.exec_() == QtWidgets.QDialog.Accepted
        box.deleteLater()
        if accepted:
            self._start_update()

    def _start_update(self):
        if self._busy or self._is_busy() or not self.firmware.currentData():
            return
        connection = self._connection()
        repo, active = self.repo.text().strip(), self.firmware.currentData()
        def task(progress):
            progress({'phase': 'review', 'text': 'Checking local library and firmware files'})
            reviewed = review_package(repo, active_firmware=active)
            validation = reviewed['manifest']['firmware_validation']
            progress(f"Selected firmware: {active}; validation: {validation}; "
                     f"{reviewed['file_count']} files, {reviewed['total_bytes'] / 1048576:.1f} MiB")
            with BoardUpdater(connection, progress) as updater:
                return updater.update(reviewed, server_stopped=True)
        self._busy, self._applying, self._last_result, self._last_phase = True, False, None, None
        self.details.clear()
        self._progress({'phase': 'review', 'text': 'Checking local library and firmware files'})
        self._refresh()
        self._thread = QtCore.QThread(self)
        self._worker = _Worker(task)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._progress)
        self._worker.finished.connect(self._finished)
        self._worker.failed.connect(self._failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._idle)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _progress(self, message):
        if not isinstance(message, dict):
            self.details.appendPlainText(str(message))
            self.status.setText(str(message))
            return
        phase = message['phase']
        text = message['text']
        if phase == 'apply':
            self._applying = True
        if phase == 'upload':
            total = max(1, message['total'])
            completed = message['completed']
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(min(100, int(completed * 100 / total)))
            self.progress_bar.setFormat('Upload %p%')
            text += f' — {completed / 1048576:.1f} / {total / 1048576:.1f} MiB'
        else:
            self.progress_bar.setRange(0, 0)
        self.status.setText(text)
        if phase != self._last_phase:
            self.details.appendPlainText(text)
        self._last_phase = phase

    def _finished(self, result):
        self._last_result = result
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat('Complete')
        self.status.setText('Files updated. Start the QICK server manually, then restart this GUI and reconnect.')
        self.details.appendPlainText(json.dumps(result, indent=2))
        self.board_changed.emit(result['state'])

    def _failed(self, message):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat('Failed')
        self.status.setText('Update failed — see details below.')
        self.details.appendPlainText('ERROR: ' + message)
        if self._applying:
            self.board_changed.emit('unknown_after_failure')

    def _idle(self):
        self._thread = self._worker = None
        self._busy = False
        self._refresh()

    def reject(self):
        if not self._busy:
            self.password.clear()
            super().reject()

    def closeEvent(self, event):
        if self._busy:
            event.ignore()
        else:
            self.password.clear()
            super().closeEvent(event)
