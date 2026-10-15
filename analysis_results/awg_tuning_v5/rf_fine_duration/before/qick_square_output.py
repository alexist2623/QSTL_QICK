"""Shared physical-port selector for continuous square-wave editors."""
from PyQt5 import QtCore, QtWidgets
try:
    from .qick_front_panel import QickFrontPanelPreview, square_pulse_output_channels
except ImportError:
    from qick_front_panel import QickFrontPanelPreview, square_pulse_output_channels


class SquareOutputSelector(QtWidgets.QWidget):
    requested = QtCore.pyqtSignal()
    changed = QtCore.pyqtSignal()

    def __init__(self, parent=None, *, channel=0, compact=False):
        super().__init__(parent)
        self.configuration = None
        self._explicit_channel = False
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.preview = QickFrontPanelPreview(self)
        self.preview.set_scope("output")
        self.preview.activated.connect(self.requested)
        layout.addWidget(self.preview)
        self.description = QtWidgets.QLabel("Identify QICK and select a SquarePulse output.")
        self.description.setWordWrap(True)
        layout.addWidget(self.description)
        self.controls = QtWidgets.QWidget(self)
        row = QtWidgets.QHBoxLayout(self.controls)
        row.setContentsMargins(0, 0, 0, 0)
        self.button = QtWidgets.QPushButton("Select output on QICK front panel")
        self.button.clicked.connect(self.requested)
        row.addWidget(self.button)
        self.channel = QtWidgets.QSpinBox()
        self.channel.setRange(0, 255)
        self.channel.setValue(channel)
        self.channel.setReadOnly(True)
        self.channel.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        row.addWidget(QtWidgets.QLabel("Generator"))
        row.addWidget(self.channel)
        layout.addWidget(self.controls)
        self.description.setVisible(not compact)
        self.controls.setVisible(not compact)
        self.channel.valueChanged.connect(self._refresh)
        self.channel.valueChanged.connect(self.changed)

    def allowed_channels(self, configuration):
        return square_pulse_output_channels(configuration)

    def set_configuration(self, configuration):
        first = self.configuration is None
        self.configuration = configuration
        allowed = self.allowed_channels(configuration)
        square = sorted(square_pulse_output_channels(configuration))
        if allowed and (self.channel.value() not in allowed
                        or (first and not self._explicit_channel)):
            self.channel.setValue((square or sorted(allowed))[0])
        if hasattr(configuration, "outputs"):
            self.preview.set_configuration(configuration)
            self.preview.set_disabled_outputs(
                p.panel_index for p in configuration.outputs
                if not set(p.qick_channels) & allowed)
        self._refresh()

    def load_channel(self, channel, *, explicit=True):
        self._explicit_channel = explicit
        self.channel.setValue(int(channel))
        self._refresh()

    def validate(self):
        channel = self.channel.value()
        if self.configuration is not None and channel not in self.allowed_channels(self.configuration):
            raise ValueError("Select a supported square-wave output from the identified firmware")
        return channel

    def apply(self, values):
        channel = int(values["output_ch"])
        if self.configuration is None or channel not in self.allowed_channels(self.configuration):
            raise ValueError("Select a supported square-wave output from the identified firmware")
        self.load_channel(channel)

    def _refresh(self):
        config = self.configuration
        if config is None:
            return
        channel = self.channel.value()
        allowed = self.allowed_channels(config)
        if channel not in allowed:
            self.description.setText("No compatible output selected in this firmware.")
            return
        port = next((p for p in getattr(config, "outputs", ()) if channel in p.qick_channels), None)
        if port is not None:
            self.preview.set_channels(output_ch=channel)
        location = f"{port.label} | {port.board_label} | " if port else ""
        self.description.setText(f"{location}QICK generator {channel} | SquarePulse IP")
