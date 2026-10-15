"""Owned offscreen updater checks; no application/board session is touched."""
import gc
import sys
from PyQt5 import QtCore, QtWidgets, sip
import pytest

app = QtWidgets.QApplication([])
app.setQuitOnLastWindowClosed(False)
code = pytest.main(sys.argv[1:])
for widget in app.topLevelWidgets():
    widget.close()
    widget.deleteLater()
app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
gc.collect()
QtCore.QTimer.singleShot(0, app.quit)
app.exec_()
sip.delete(app)
print('QT_EXPLICIT_TEARDOWN_COMPLETE', flush=True)
raise SystemExit(int(code))
