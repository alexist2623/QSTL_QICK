"""Run display regressions in an owned offscreen Qt process, never the user's GUI."""
import gc
import sys
import traceback
from qick.sim import QickSim  # Desktop-only bootstrap; no board connection.
from PyQt5 import QtCore, QtGui, QtWidgets, sip
import pytest
import DCWaveform_Generator as gui
from dc_waveform_widgets import WaveformPlotWidget, RfPulseTimelineWidget, TracePlotWidget


def main():
    errors = []
    def record_exception(kind, value, tb):
        errors.append(''.join(traceback.format_exception(kind, value, tb)))
        traceback.print_exception(kind, value, tb, file=sys.stderr)
    sys.excepthook = record_exception
    app = QtWidgets.QApplication([])
    font_id = QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    assert font_id >= 0
    app.setFont(QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(font_id)[0], 9))
    app.setQuitOnLastWindowClosed(False)
    code = pytest.main(sys.argv[1:])
    windows = [w for w in app.topLevelWidgets() if isinstance(
        w, (gui.MainWindow, WaveformPlotWidget, RfPulseTimelineWidget, TracePlotWidget))]
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
