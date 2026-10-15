from pathlib import Path
from qick.sim import QickSim
from PyQt5 import QtCore,QtGui,QtWidgets,sip
import DCWaveform_Generator as gui
from test_rf_t2_integration import load_composite
app=QtWidgets.QApplication([])
i=QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
app.setFont(QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(i)[0],9))
window=gui.MainWindow();window.resize(1500,1000)
panel=load_composite(window,pi_sweep=True)
window.show();app.processEvents()
window._waveform_point_index.setValue(5);window._fit_view();app.processEvents()
base=Path(__file__).parent
editor=gui.RfPulsePortPanel(window._pulse[0],0,time_unit='us')
editor.load_settings(panel.settings_dict());editor.resize(1200,editor.sizeHint().height());editor.show();app.processEvents()
for group in editor.findChildren(QtWidgets.QGroupBox):
 if group.title().startswith('T2'):
  group.grab().save(str(base/'t2_controls.png'))
editor.delay_parameter_table.grab().save(str(base/'tau_variables.png'))
timeline=window._rf_timelines[0]
timeline.resize(1100,160);timeline.setXRange(-100,5000,padding=0);app.processEvents()
timeline.grab().save(str(base/'composite_preview.png'))
editor.close();editor.deleteLater();window.close();window.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete)
app.processEvents();QtCore.QTimer.singleShot(0,app.quit);app.exec_();sip.delete(app)
print('RENDER_PASS')
