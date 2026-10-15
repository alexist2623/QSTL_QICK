"""Open an isolated offscreen updater and inspect its local firmware list."""
from pathlib import Path
import gc
import json
import socket

from qick.sim import QickSim  # Existing desktop metadata bootstrap; no board.
from PyQt5 import QtCore, QtWidgets, sip
import qick_update_dialog as ui


def forbidden(*args, **kwargs):
    raise AssertionError('Board/network access is forbidden in local discovery')


socket.create_connection = forbidden
socket.socket.connect = forbidden
ui.BoardUpdater.__enter__ = forbidden
app = QtWidgets.QApplication([])
app.setQuitOnLastWindowClosed(False)
dialog = ui.QickUpdateDialog()
dialog.repo.setText('C:/GIT_Workspace/QSTL_QICK')
dialog._scan_timer.stop()
dialog._load_versions()
rows = [dict(label=dialog.firmware.itemText(i), bit=dialog.firmware.itemData(i))
        for i in range(dialog.firmware.count())]
matches = [r for r in rows if r['label'] == 'qstl_awg_v5']
assert matches == [dict(label='qstl_awg_v5', bit='projects/qstl_awg_v5/bitstream.bit')], matches
assert not dialog._busy and dialog._thread is None
result = dict(passed=True, actual_dialog=True, board_connected=False,
              update_clicked=False, visible=matches, version_count=len(rows))
dialog.close()
dialog.deleteLater()
app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
del dialog
gc.collect()
QtCore.QTimer.singleShot(0, app.quit)
app.exec_()
sip.delete(app)
result['explicit_qt_teardown'] = True
out = Path(__file__).with_name('gui_discovery.json')
assert not out.exists(), 'Preserve prior evidence'
out.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
