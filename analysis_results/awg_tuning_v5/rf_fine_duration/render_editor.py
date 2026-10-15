"""Render one owned offscreen RF editor, without live GUI or hardware access."""
import gc
import json
from pathlib import Path

from qick.sim import QickSim  # Existing desktop bootstrap; no hardware object.
from PyQt5 import QtCore, QtGui, QtWidgets, sip
import DCWaveform_Generator as gui
from dc_waveform_core import PulseSequence


app = QtWidgets.QApplication([])
app.setQuitOnLastWindowClosed(False)
font_id = QtGui.QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
app.setFont(QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(font_id)[0], 10))
panel = gui.RfPulsePortPanel(PulseSequence(initial_duration_ns=1000), 0,
                            default_gen_ch=0, time_unit="ns")
panel.load_settings({**gui.DEFAULT_RF_OUTPUT_SETTINGS,
                     "enabled": True, "fine_duration": True,
                     "duration_us": 81 / 4800,
                     "duration_sweep_enabled": True,
                     "duration_sweep_start_us": 81 / 4800,
                     "duration_sweep_stop_us": 112 / 4800,
                     "duration_sweep_count": 32,
                     "frequency_mhz": 190.0, "gain": 4000})
panel.set_generator_timings([{"f_fabric": 300.0, "samps_per_clk": 16}])
panel.setWindowTitle("Staged RF duration editor — offline rendering")
panel.resize(1150, panel.sizeHint().height())
panel.show()
app.processEvents()
panel.resize(1150, panel.sizeHint().height())
app.processEvents()
output = Path(__file__).with_name("editor_preview.png")
assert panel.grab().save(str(output))
assert panel.configured_spec().sweep_axes[0].count == 32
layout = {name: {"visible": widget.isVisible(), "x": widget.x(), "y": widget.y(),
                 "width": widget.width(), "height": widget.height()}
          for name, widget in [("fine_duration", panel.fine_duration),
                               ("duration", panel.duration),
                               ("sweep_start", panel.duration_sweep_start),
                               ("sweep_stop", panel.duration_sweep_stop),
                               ("sweep_count", panel.duration_sweep_count)]}
Path(__file__).with_name("editor_preview.json").write_text(json.dumps({
    "source": gui.__file__, "size": [panel.width(), panel.height()],
    "settings": panel.settings_dict(), "layout": layout,
    "tooltip": panel.fine_duration.toolTip(), "board_access": False,
    "live_gui_access": False}, indent=2))
print(output, flush=True)
print(json.dumps(layout), flush=True)
panel.close()
panel.deleteLater()
app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
del panel
gc.collect()
QtCore.QTimer.singleShot(0, app.quit)
app.exec_()
sip.delete(app)
print("QT_EXPLICIT_TEARDOWN_COMPLETE", flush=True)
