"""Read-only live SFTP navigation through the production Qt browse buttons."""
import os, sys, json, time, hashlib, importlib.metadata
from pathlib import Path
from datetime import datetime, timezone
from PyQt5 import QtCore, QtWidgets, QtTest, QtGui
from qick_update import BoardUpdater
from qick_update_dialog import QickUpdateDialog, RemoteDirectoryDialog

OUT = Path(__file__).resolve().parent
result = {'started_utc': datetime.now(timezone.utc).isoformat(), 'passed': False,
          'python': sys.version, 'paramiko': importlib.metadata.version('paramiko'),
          'host': '192.168.2.99', 'gui_mode': 'Qt offscreen; production dialog and live SSH/SFTP',
          'directory_reads': [], 'checks': [], 'upload_executed': False,
          'board_file_replacement_executed': False, 'firmware_download_executed': False}
original_list = BoardUpdater.list_directories

def read_directories(self, path):
    value = original_list(self, path)
    result['directory_reads'].append(value)
    return value

def forbid_mutation(*args, **kwargs):
    raise AssertionError('Deployment actions are outside this browse-only test')

BoardUpdater.list_directories = read_directories
for method in ('prepare', 'apply', 'rollback', 'verify', 'remote'):
    setattr(BoardUpdater, method, forbid_mutation)
app = QtWidgets.QApplication([])
font_id = QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
assert font_id >= 0
families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
app.setFont(QtGui.QFont(families[0], 10))
result['render_font'] = families[0]
app.setQuitOnLastWindowClosed(False)
window = QickUpdateDialog()
window.password.setText(os.environ.pop('QICK_BROWSE_TEST_PASSWORD'))
window.show()
app.processEvents()


def drive(button, operations):
    timer = QtCore.QTimer()
    timer.setInterval(40)
    started = time.monotonic()
    errors = []
    index = 0

    def tick():
        nonlocal index
        dialog = app.activeModalWidget()
        if not isinstance(dialog, RemoteDirectoryDialog):
            return
        if time.monotonic() - started > 75:
            errors.append('Browse timed out: ' + dialog.status.text())
        if dialog._busy:
            return
        if errors:
            timer.stop()
            dialog.reject()
            return
        try:
            action, value = operations[index]
            if action == 'check':
                assert dialog._loaded_path == value, (dialog._loaded_path, value, dialog.status.text())
                assert dialog.choose.isEnabled()
                result['checks'].append('loaded ' + value)
            elif action == 'up':
                QtTest.QTest.mouseClick(dialog.up, QtCore.Qt.LeftButton)
            elif action == 'enter':
                matches = dialog.folders.findItems(value, QtCore.Qt.MatchExactly)
                assert len(matches) == 1, value
                item = matches[0]
                dialog.folders.scrollToItem(item)
                point = dialog.folders.visualItemRect(item).center()
                QtTest.QTest.mouseClick(dialog.folders.viewport(), QtCore.Qt.LeftButton, pos=point)
                QtTest.QTest.mouseDClick(dialog.folders.viewport(), QtCore.Qt.LeftButton, pos=point)
            elif action == 'open':
                dialog.path.setText(value)
                assert not dialog.choose.isEnabled()
                QtTest.QTest.mouseClick(dialog.go, QtCore.Qt.LeftButton)
            elif action == 'error':
                assert dialog._loaded_path is None and not dialog.choose.isEnabled()
                result['checks'].append('nonexistent path rejected; selection disabled')
            elif action == 'image':
                assert dialog.grab().save(str(OUT / value))
            elif action == 'select':
                assert dialog._loaded_path == value
                QtTest.QTest.mouseClick(dialog.choose, QtCore.Qt.LeftButton)
                result['checks'].append('selected ' + value)
                timer.stop()
            index += 1
        except Exception as exc:
            errors.append(repr(exc))
            if not dialog._busy:
                timer.stop()
                dialog.reject()

    timer.timeout.connect(tick)
    timer.start()
    QtTest.QTest.mouseClick(button, QtCore.Qt.LeftButton)
    timer.stop()
    assert not errors, errors
    assert index == len(operations), (index, operations)
    app.processEvents()

try:
    repo_button = window.remote_repo.parentWidget().findChild(QtWidgets.QPushButton)
    drive(repo_button, [
        ('check', '/home/QSTL_QICK'), ('up', None), ('check', '/home'),
        ('enter', 'QSTL_QICK'), ('check', '/home/QSTL_QICK'),
        ('open', '/home/__codex_browse_missing_20261014__'), ('error', None),
        ('open', '/home/QSTL_QICK'), ('check', '/home/QSTL_QICK'),
        ('image', 'repository_browser.png'), ('select', '/home/QSTL_QICK')])
    assert window.remote_repo.text() == '/home/QSTL_QICK'
    firmware_button = window.remote_bit.parentWidget().findChild(QtWidgets.QPushButton)
    drive(firmware_button, [
        ('check', '/home/QSTL_QICK/qick/firmware'), ('enter', 'projects'),
        ('check', '/home/QSTL_QICK/qick/firmware/projects'),
        ('image', 'firmware_browser.png'), ('select', '/home/QSTL_QICK/qick/firmware/projects')])
    assert window.remote_bit.text() == 'qick/firmware/projects/bitstream.bit'
    assert '/home/QSTL_QICK/qick/firmware/projects/bitstream.hwh' in window.path_summary.text()
    assert window._review is None and window._prepared is None
    assert not window.prepare_button.isEnabled() and not window.apply_button.isEnabled()
    result['checks'].append('selected BIT/HWH paths reflected in parent dialog; upload/apply remain disabled')
    result['passed'] = True
except Exception as exc:
    result['failure'] = repr(exc)
finally:
    window.password.clear()
    window.close()
    window.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    app.processEvents()
    app.quit()
    result['sources'] = {str(Path(m).resolve()): hashlib.sha256(Path(m).read_bytes()).hexdigest()
        for m in ['C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI/qick_update.py',
                  'C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI/qick_update_dialog.py']}
    result['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (OUT / 'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
sys.exit(0 if result['passed'] else 1)
