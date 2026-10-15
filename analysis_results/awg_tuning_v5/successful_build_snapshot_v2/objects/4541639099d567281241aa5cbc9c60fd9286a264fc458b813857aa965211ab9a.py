"""Independent DC/RC checkboxes, with migration of the saved Bias-T settings.

The saved ``enabled/type`` pair is retained for existing experiment files:
dc, filter (now FPGA RC), and dc_rc. It is only a serialization format;
the sequence stores DC and RC in independent configuration objects.
"""
from PyQt5 import QtCore, QtWidgets


class CompensationGroup(QtWidgets.QGroupBox):
    def __init__(self, *args):
        super().__init__(*args)
        self._compensation_enabled = False
        self.selector = None

    def setCheckable(self, _value):
        # There is no master switch; the two visible checkboxes are independent.
        super().setCheckable(False)

    def isChecked(self):
        return self._compensation_enabled

    def setChecked(self, enabled):
        changed = self._compensation_enabled != bool(enabled)
        self._compensation_enabled = bool(enabled)
        if self.selector is not None:
            self.selector._restore_checkboxes()
            self.selector.currentIndexChanged.emit(self.selector.currentIndex())
        if changed:
            self.toggled.emit(bool(enabled))


class CompensationSelector(QtWidgets.QWidget):
    currentIndexChanged = QtCore.pyqtSignal(int)
    _modes = ("dc", "filter", "dc_rc")

    def __init__(self, group):
        super().__init__(group)
        self.group = group
        group.selector = self
        self._mode = "dc"
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.dc_checkbox = QtWidgets.QCheckBox("DC compensation", self)
        self.rc_checkbox = QtWidgets.QCheckBox("RC compensation", self)
        self.rc_checkbox.setToolTip(
            "Continuous FPGA compensation; requires RC-capable firmware. "
            "Waveform Plot can show the target and the RC-corrected DAC estimate. "
            "The compensated DAC voltage must stay within the output range.")
        layout.addWidget(self.dc_checkbox)
        layout.addWidget(self.rc_checkbox)
        self._restore_checkboxes()
        self.dc_checkbox.toggled.connect(self._checkboxes_changed)
        self.rc_checkbox.toggled.connect(self._checkboxes_changed)

    def addItem(self, _label, _data):
        """Accept old form construction; all three modes are built in."""

    def findData(self, mode):
        return self._modes.index(mode) if mode in self._modes else -1

    def currentData(self):
        return self._mode

    def currentIndex(self):
        return self.findData(self._mode)

    def setCurrentIndex(self, index):
        if not 0 <= index < len(self._modes):
            raise ValueError("Invalid DC/RC compensation selection")
        self._mode = self._modes[index]
        self._restore_checkboxes()
        self.currentIndexChanged.emit(index)

    def _restore_checkboxes(self):
        blockers = [QtCore.QSignalBlocker(self.dc_checkbox), QtCore.QSignalBlocker(self.rc_checkbox)]
        self.dc_checkbox.setChecked(self.group.isChecked() and self._mode in ("dc", "dc_rc"))
        self.rc_checkbox.setChecked(self.group.isChecked() and self._mode in ("filter", "dc_rc"))
        del blockers

    def _checkboxes_changed(self):
        dc, rc = self.dc_checkbox.isChecked(), self.rc_checkbox.isChecked()
        if dc or rc:
            self._mode = "dc_rc" if dc and rc else ("dc" if dc else "filter")
        self.group._compensation_enabled = dc or rc
        self.currentIndexChanged.emit(self.currentIndex())
        self.group.toggled.emit(dc or rc)
