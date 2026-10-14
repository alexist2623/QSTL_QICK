"""Offscreen UI evidence. Update confirmation is cancelled; no network allowed."""
from pathlib import Path
import json
from PyQt5 import QtCore, QtGui, QtWidgets
import qick_update_dialog as ui

out = Path(__file__).resolve().parent
app = QtWidgets.QApplication([])
QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
app.setFont(QtGui.QFont('Segoe UI', 10))

class NoNetwork:
    def __init__(self, *args, **kwargs):
        raise AssertionError('No board connection is permitted in this capture')

ui.BoardUpdater = NoNetwork
dialog = ui.QickUpdateDialog()
dialog.show()
app.processEvents()
dialog.grab().save(str(out / 'update_dialog.png'))
dialog.firmware.showPopup()
app.processEvents()
popup = app.activePopupWidget()
assert popup
popup.grab().save(str(out / 'firmware_versions.png'))
dialog.firmware.hidePopup()
checks = []

def cancel_confirmation():
    box = app.activeModalWidget()
    assert isinstance(box, ui.UpdateConfirmationDialog)
    checks.append({'server_checked': box.server_stopped.isChecked(), 'experiments_checked': box.experiments_stopped.isChecked(), 'confirm_enabled': box.confirm.isEnabled()})
    assert box.cancel.isDefault() and not box.confirm.isEnabled()
    box.grab().save(str(out / 'server_confirmation.png'))
    box.cancel.click()

QtCore.QTimer.singleShot(100, cancel_confirmation)
dialog.update_button.click()
assert checks and not dialog._busy and dialog._last_result is None
(out / 'ui_capture.json').write_text(json.dumps({
    'firmware_count': dialog.firmware.count(), 'selected': dialog.firmware.currentData(),
    'checks': checks, 'update_executed': False, 'network_allowed': False}, indent=2), encoding='utf-8')
dialog.close()
dialog.deleteLater()
app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
