"""Run the existing phase-storage assertions with an owned Qt lifecycle."""
import gc
from pathlib import Path
import sys
import traceback
from qick.sim import QickSim  # noqa: F401
from PyQt5 import QtCore, QtWidgets, sip
import pytest
import DCWaveform_Generator as gui


def main():
    errors = []
    def record_exception(kind, value, tb):
        errors.append(str(value))
        traceback.print_exception(kind, value, tb, file=sys.stderr)
    sys.excepthook = record_exception
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    code = pytest.main([sys.argv[1], '-q', '-s', '-p', 'no:cacheprovider', '--basetemp', sys.argv[2]])
    # Qt also lists internal popups in topLevelWidgets; those belong to their
    # owning controls and must not be independently destroyed a second time.
    windows = [w for w in app.topLevelWidgets() if isinstance(w, gui.MainWindow)]
    for window in windows:
        window.close()
        window.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    app.processEvents()
    windows.clear()
    if 'window' in locals():
        del window
    gc.collect()
    QtCore.QTimer.singleShot(0, app.quit)
    app.exec_()
    sip.delete(app)
    if errors:
        print('QT_CALLBACK_ERRORS:', errors, flush=True)
        return 1
    print('QT_EXPLICIT_TEARDOWN_COMPLETE', flush=True)
    return int(code)


if __name__ == '__main__':
    raise SystemExit(main())
