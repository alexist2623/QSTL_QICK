"""GUI editors for the autonomous square DDS and external output markers."""
from dataclasses import asdict
from PyQt5 import QtCore, QtWidgets
try:
    from .qick_square_output import SquareOutputSelector
    from .qick_front_panel import QickFrontPanelCanvas, digital_trigger_outputs
except ImportError:
    from qick_square_output import SquareOutputSelector
    from qick_front_panel import QickFrontPanelCanvas, digital_trigger_outputs
try:
    from .qick_square_dds import SquarePulseConfig, SquarePulseSweep, OutputTriggerConfig, attach_square_settings, decode_square_outputs
except ImportError:
    from qick_square_dds import SquarePulseConfig, SquarePulseSweep, OutputTriggerConfig, attach_square_settings, decode_square_outputs


def spin(value, suffix, minimum=0, maximum=1e6, decimals=6):
    widget=QtWidgets.QDoubleSpinBox()
    widget.setRange(minimum,maximum); widget.setDecimals(decimals)
    widget.setSuffix(suffix); widget.setValue(value)
    widget.setKeyboardTracking(False)
    return widget


class SquarePulsePanel(QtWidgets.QWidget):
    changed=QtCore.pyqtSignal()
    front_panel_requested=QtCore.pyqtSignal(object)
    remove_requested=QtCore.pyqtSignal(object)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.ports_panel = None
        layout=QtWidgets.QVBoxLayout(self)
        header = QtWidgets.QHBoxLayout()
        self.title = QtWidgets.QLabel("SquarePulse output")
        self.title.setWordWrap(True)
        self.remove_button = QtWidgets.QPushButton("Remove port")
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        header.addWidget(self.title); header.addStretch(1); header.addWidget(self.remove_button)
        layout.addLayout(header)
        self.enabled=QtWidgets.QCheckBox("Enable SquarePulse during AWG experiment")
        self.status=QtWidgets.QLabel("Identify QICK to discover SquarePulse outputs.")
        self.status.setWordWrap(True)
        layout.addWidget(self.enabled); layout.addWidget(self.status)
        self.output_selector=SquareOutputSelector(self, channel=7, compact=True)
        self.channel=self.output_selector.channel
        self.output_selector.requested.connect(lambda: self.front_panel_requested.emit(self))
        layout.addWidget(self.output_selector)
        self.mute_on_finish=QtWidgets.QCheckBox("Mute SquarePulse when experiment finishes")
        self.mute_on_finish.setChecked(True)
        self.mute_on_finish.setToolTip("Unchecked: keep the final frequency, amplitude and phase running after successful completion. Stop/cancel and errors still mute output.")
        self.mute_on_finish.toggled.connect(self.changed)
        layout.addWidget(self.mute_on_finish)
        note=QtWidgets.QLabel("Continuous 50% duty output, ±amplitude. Output full scale follows this DAC current in the shared Front Panel. "
            "Frequency and amplitude updates preserve accumulated phase. Phase sets an offset. "
            "Sweeps run in tProcessor hardware loops. Uncheck mute to keep output running after completion.")
        note.setWordWrap(True); layout.addWidget(note)
        self.rows={}
        for name,label,value,suffix,minimum in (
            ('frequency','Frequency',0.04,' MHz',0),
            ('amplitude','Peak amplitude',10,' mV',0),
            ('phase','Phase offset',0,' deg',-1e6)):
            group=QtWidgets.QGroupBox(label); row=QtWidgets.QGridLayout(group)
            fixed=spin(value,suffix,minimum); start=spin(value,suffix,minimum); stop=spin(value,suffix,minimum)
            sweep=QtWidgets.QCheckBox("Hardware sweep")
            count=QtWidgets.QSpinBox(); count.setRange(1,1000000); count.setValue(11)
            row.addWidget(QtWidgets.QLabel("Value"),0,0); row.addWidget(fixed,0,1); row.addWidget(sweep,0,2)
            for col,text,widget in ((0,'Start',start),(2,'Stop',stop),(4,'Points',count)):
                row.addWidget(QtWidgets.QLabel(text),1,col); row.addWidget(widget,1,col+1)
            self.rows[name]=dict(value=fixed,sweep=sweep,start=start,stop=stop,count=count)
            for widget in (start,stop,count): widget.setEnabled(False)
            sweep.toggled.connect(lambda checked,items=(fixed,start,stop,count): self._toggle_sweep(checked,items))
            for widget in (fixed,start,stop,count): widget.valueChanged.connect(self.changed)
            sweep.toggled.connect(self.changed)
            layout.addWidget(group)
        self.enabled.toggled.connect(self.changed); self.channel.valueChanged.connect(self.changed)
        layout.addStretch(1)
        self._available_channels=None

    @staticmethod
    def _toggle_sweep(checked,items):
        items[0].setEnabled(not checked)
        for item in items[1:]: item.setEnabled(checked)

    def set_configuration(self,configuration):
        selected = self.channel.value() if self.output_selector._explicit_channel else None
        self.output_selector.set_configuration(configuration)
        if selected is not None:
            self.output_selector.load_channel(selected)
        channels=tuple(getattr(configuration,'square_pulse_channels',()))
        self._available_channels=channels
        self.enabled.setEnabled(self.channel.value() in channels)
        if channels:
            if self.channel.value() not in channels:
                self.enabled.setChecked(False)
                self.status.setText("Saved output is unavailable. Click the front panel to select a connected SquarePulse IP.")
            else:
                self.status.setText("Click the front panel to select a connected SquarePulse output.")
        else:
            self.enabled.setChecked(False)
            self.status.setText("This firmware has no SquarePulse IP. Existing AWG and RF features remain available.")

    def settings_dict(self):
        return dict(enabled=self.enabled.isChecked(),gen_ch=self.channel.value(),
                    mute_on_finish=self.mute_on_finish.isChecked(),
                    parameters={name:{key:(widget.isChecked() if key=='sweep' else widget.value())
                                      for key,widget in row.items()} for name,row in self.rows.items()})

    def load_settings(self,settings):
        settings=settings or {}
        self.output_selector.load_channel(int(settings.get('gen_ch',7)), explicit=bool(settings))
        self.mute_on_finish.setChecked(settings.get('mute_on_finish',True))
        supported = self._available_channels is None or bool(self._available_channels)
        self.enabled.setChecked(bool(settings.get('enabled',False)) and supported)
        for name,row in self.rows.items():
            for key,value in settings.get('parameters',{}).get(name,{}).items():
                if key not in row: continue
                if key=='sweep': row[key].setChecked(bool(value))
                else: row[key].setValue(value)

    def attach_to_sequence(self,sequence,full_scale_mv,trigger):
        if not self.enabled.isChecked():
            return attach_square_settings(sequence,trigger=trigger)
        ch=self.channel.value()
        if self._available_channels is not None and ch not in self._available_channels:
            raise ValueError("Select a SquarePulse generator from the identified firmware")
        configs, axes = decode_square_outputs(self.settings_dict(), full_scale_mv)
        return attach_square_settings(sequence,configs,axes,trigger,follow_experiment_rc=True)

    def sweep_specs(self):
        if not self.enabled.isChecked(): return ()
        ch=self.channel.value()
        return tuple(SquarePulseSweep(name,row['start'].value(),row['stop'].value(),row['count'].value(),ch,
                                   output_name=f"square{ch}",segment_name=name)
                   for name,row in self.rows.items() if row['sweep'].isChecked())

    def allowed_output_channels(self, configuration):
        allowed = self.output_selector.allowed_channels(configuration)
        if self.ports_panel is not None:
            used = {panel.channel.value() for panel in self.ports_panel._panels if panel is not self}
            allowed = allowed - used
        return allowed

    def front_panel_values(self):
        return dict(output_ch=self.channel.value(), output_nqz=1)

    def apply_front_panel_settings(self, values):
        if int(values["output_ch"]) not in self.allowed_output_channels(self.output_selector.configuration):
            raise ValueError("Select a supported square-wave output not assigned to another port")
        self.output_selector.apply(values)
        self.enabled.setEnabled(True)
        self.status.setText("Click the front panel to select a connected SquarePulse output.")


class SquarePulsePortsPanel(QtWidgets.QWidget):
    """Independent output editors sharing the Experiment RC configuration."""
    changed = QtCore.pyqtSignal()
    front_panel_requested = QtCore.pyqtSignal(object)
    MAX_PORTS = 16

    def __init__(self, parent=None):
        super().__init__(parent)
        self._panels = []
        self._configuration = None
        layout = QtWidgets.QVBoxLayout(self)
        self.rc_status = QtWidgets.QLabel()
        self.rc_status.setWordWrap(True)
        layout.addWidget(self.rc_status)
        self._scroll = QtWidgets.QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._content = QtWidgets.QWidget(self._scroll)
        self._content_layout = QtWidgets.QVBoxLayout(self._content)
        self._content_layout.addStretch(1)
        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll, 1)
        self.add_button = QtWidgets.QPushButton("Add SquarePulse Port")
        self.add_button.clicked.connect(lambda: self.add_port())
        layout.addWidget(self.add_button)
        self.availability = QtWidgets.QLabel()
        self.availability.setWordWrap(True)
        layout.addWidget(self.availability)
        self.set_rc_compensation(False, 1000.0)
        self.add_port()

    # Preserve the single-output editor API for saved integrations.
    @property
    def enabled(self): return self._panels[0].enabled
    @property
    def channel(self): return self._panels[0].channel
    @property
    def rows(self): return self._panels[0].rows
    @property
    def mute_on_finish(self): return self._panels[0].mute_on_finish
    @property
    def output_selector(self): return self._panels[0].output_selector

    def allowed_output_channels(self, configuration):
        return self._panels[0].allowed_output_channels(configuration)

    def front_panel_values(self): return self._panels[0].front_panel_values()
    def apply_front_panel_settings(self, values): self._panels[0].apply_front_panel_settings(values)

    def panel_for_channel(self, channel):
        return next(panel for panel in self._panels if panel.channel.value() == channel)

    def active_channels(self):
        return tuple(panel.channel.value() for panel in self._panels if panel.enabled.isChecked())

    def _unused_channels(self):
        used = {panel.channel.value() for panel in self._panels}
        return sorted(set(getattr(self._configuration, 'square_pulse_channels', ())) - used)

    def add_port(self, *, settings=None):
        if len(self._panels) >= self.MAX_PORTS:
            return None
        unused = self._unused_channels()
        if settings is None and self._configuration is not None and not unused:
            return None
        panel = SquarePulsePanel(self)
        panel.ports_panel = self
        if settings is not None:
            panel.load_settings(settings)
        elif unused:
            panel.output_selector.load_channel(unused[0])
        elif self._panels:
            panel.output_selector.load_channel(next(ch for ch in range(256)
                if ch not in {item.channel.value() for item in self._panels}))
        if self._configuration is not None:
            panel.set_configuration(self._configuration)
        self._panels.append(panel)
        self._content_layout.insertWidget(self._content_layout.count() - 1, panel)
        panel.changed.connect(self._ports_changed)
        panel.remove_requested.connect(self.remove_port)
        panel.front_panel_requested.connect(self.front_panel_requested.emit)
        self._ports_changed()
        return panel

    def remove_port(self, panel):
        if panel not in self._panels:
            return
        self._panels.remove(panel)
        self._content_layout.removeWidget(panel)
        panel.hide(); panel.deleteLater()
        self._ports_changed()

    def _ports_changed(self):
        for index, panel in enumerate(self._panels):
            config = self._configuration
            port = next((port for port in getattr(config, 'outputs', ())
                         if panel.channel.value() in port.qick_channels), None)
            location = f"{port.label} | " if port is not None else ""
            panel.title.setText(f"SquarePulse port {index + 1} | {location}Generator {panel.channel.value()}")
            if config is not None and hasattr(config, 'outputs'):
                allowed = panel.allowed_output_channels(config)
                panel.output_selector.preview.set_disabled_outputs(
                    port.panel_index for port in config.outputs if not set(port.qick_channels) & allowed)
        known = self._configuration is not None
        self.add_button.setEnabled(len(self._panels) < self.MAX_PORTS and known and bool(self._unused_channels()))
        self.availability.setText(
            "Identify QICK to add connected SquarePulse ports." if not known else
            f"{len(getattr(self._configuration, 'square_pulse_channels', ()))} SquarePulse IP output(s) detected. "
            "Only unused SquarePulse outputs can be added.")
        self.changed.emit()

    def set_configuration(self, configuration):
        self._configuration = configuration
        with QtCore.QSignalBlocker(self):
            used = set()
            channels = set(getattr(configuration, 'square_pulse_channels', ()))
            for panel in self._panels:
                if not panel.output_selector._explicit_channel and channels - used:
                    panel.output_selector.load_channel(min(channels - used))
                original = panel.channel.value()
                panel.set_configuration(configuration)
                # A saved missing output must never silently select another DAC.
                panel.output_selector.load_channel(original)
                if original not in channels or original in used:
                    panel.enabled.setChecked(False)
                panel.enabled.setEnabled(original in channels and original not in used)
                used.add(original)
        self._ports_changed()

    def set_rc_compensation(self, enabled, tau_us):
        self.rc_status.setText(
            f"RC compensation: enabled, tau = {tau_us:g} us (shared with Experiment)."
            if enabled else "RC compensation: disabled in Experiment.")

    def settings_dict(self):
        entries = [panel.settings_dict() for panel in self._panels]
        return entries[0] if len(entries) == 1 else {"outputs": entries}

    def load_settings(self, settings):
        entries = (settings or {}).get("outputs", [settings or {}])
        if not isinstance(entries, (list, tuple)) or len(entries) > self.MAX_PORTS:
            raise ValueError("SquarePulse outputs must be a list of at most 16 ports")
        with QtCore.QSignalBlocker(self):
            for panel in tuple(self._panels):
                self.remove_port(panel)
            for entry in entries:
                self.add_port(settings=entry)
            if self._configuration is not None:
                self.set_configuration(self._configuration)
        self._ports_changed()

    def sweep_specs(self):
        return tuple(axis for panel in self._panels for axis in panel.sweep_specs())

    def attach_to_sequence(self, sequence, full_scale_mv, trigger):
        for panel in self._panels:
            if panel.enabled.isChecked():
                panel.output_selector.validate()
        configs, axes = decode_square_outputs(self.settings_dict(), full_scale_mv)
        return attach_square_settings(sequence, configs, axes, trigger, follow_experiment_rc=True)


class TriggeringPanel(QtWidgets.QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self._configuration = None
        self._available_pins = None
        self._io_to_pin = {}
        self._saved_pin = 0
        self._selected_name = None
        layout=QtWidgets.QFormLayout(self)
        self.enabled=QtWidgets.QCheckBox("Enable external output trigger")
        self.enabled.setEnabled(False)
        self.canvas = QickFrontPanelCanvas(self)
        self.canvas.set_scope("io")
        self.canvas.setMinimumSize(330, 122)
        self.canvas.setMaximumHeight(200)
        self.canvas.port_clicked.connect(self._select_sma)
        self.pin = QtWidgets.QComboBox()
        self.pin.setPlaceholderText("Identify QICK, then select a connected SMA")
        self.pin.setEnabled(False)
        self.pin.currentIndexChanged.connect(self._selection_changed)
        self.scope=QtWidgets.QComboBox()
        self.scope.addItem("Each repetition loop","loop"); self.scope.addItem("Entire experiment","experiment")
        self.edge=QtWidgets.QComboBox()
        for label,value in (("Start","start"),("End","end"),("Start and end","both")): self.edge.addItem(label,value)
        self.width=spin(1.0,' µs',0.001,1e6,6)
        self.status=QtWidgets.QLabel("Identify QICK to discover connected trigger outputs. Gray SMAs cannot be selected.")
        self.status.setWordWrap(True)
        for label,widget in (("",self.enabled),("",self.canvas),("Output SMA",self.pin),("Scope",self.scope),
                             ("Boundary",self.edge),("Width",self.width),("",self.status)):
            layout.addRow(label,widget)

    def config(self):
        pin = self.pin.currentData()
        valid = self._available_pins is None or pin in self._io_to_pin.values()
        return OutputTriggerConfig(self.enabled.isChecked() and valid,
                                   self._saved_pin if pin is None else pin,
                                   self.scope.currentData(),self.edge.currentData(),self.width.value())

    def settings_dict(self): return asdict(self.config())

    def load_settings(self,settings):
        config=OutputTriggerConfig(**(settings or {}))
        self._saved_pin = config.pin
        self._selected_name = None
        self.pin.setCurrentIndex(self.pin.findData(config.pin))
        self._selection_changed()
        supported = self._available_pins is None or config.pin in self._io_to_pin.values()
        self.enabled.setChecked(config.enabled and supported)
        self.scope.setCurrentIndex(self.scope.findData(config.scope)); self.edge.setCurrentIndex(self.edge.findData(config.edge))
        self.width.setValue(config.width_us)

    def set_configuration(self,configuration):
        self._configuration = configuration
        self._available_pins = tuple(getattr(configuration, 'output_trigger_pins', ()))
        self._io_to_pin = digital_trigger_outputs(configuration)
        self.canvas.set_configuration(configuration)
        preferred = self._saved_pin
        if self._selected_name is not None:
            # Keep the same physical output even if output_pins is reordered.
            preferred = next((pin for pin in self._io_to_pin.values()
                              if self._available_pins[pin] == self._selected_name), None)
        blocker = QtCore.QSignalBlocker(self.pin)
        self.pin.clear()
        for sma, pin in sorted(self._io_to_pin.items()):
            self.pin.addItem(f"IO{sma} — {self._available_pins[pin]} (QICK pin {pin})", pin)
        self.pin.setCurrentIndex(self.pin.findData(preferred))
        del blocker
        self.pin.setEnabled(bool(self._io_to_pin))
        self.pin.setPlaceholderText("Select a connected SMA" if self._io_to_pin else "No connected trigger SMA")
        self._selection_changed()

    def _select_sma(self, direction, sma):
        if direction == "io" and sma in self._io_to_pin:
            self.pin.setCurrentIndex(self.pin.findData(self._io_to_pin[sma]))

    def _selection_changed(self, *_args):
        pin = self.pin.currentData()
        sma = next((sma for sma, index in self._io_to_pin.items() if index == pin), None)
        self.canvas.set_selected("io", sma)
        self.enabled.setEnabled(sma is not None)
        if sma is not None:
            self._saved_pin = pin
            self._selected_name = self._available_pins[pin]
            self.status.setText(f"Selected: IO{sma} → {self._selected_name}. "
                                "Gray SMAs have no connected trigger output in this firmware.")
        elif self._available_pins is not None:
            self.enabled.setChecked(False)
            self.status.setText(
                "The saved output is unavailable. Select a connected DIGITAL I/O SMA."
                if self._io_to_pin else "No DIGITAL I/O SMA is connected to a supported tProcessor trigger output in this firmware."
            )
