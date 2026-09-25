"""Render actual Qt compensation widgets without connecting to a board."""
import argparse
import json
from pathlib import Path
import sys


def main():
    p=argparse.ArgumentParser();p.add_argument('--gui',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(a.gui/'DCWaveformGeneratorGUI'))
    from qick.sim import QickSim
    from PyQt5 import QtCore,QtGui,QtWidgets
    from DCWaveform_Generator import MainWindow
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    for font in ('segoeui.ttf','segoeuib.ttf'):
        QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+font)
    app.setFont(QtGui.QFont('Segoe UI',10));app.setStyle('Fusion')
    window=MainWindow();window.resize(2000,1200);window.show();app.processEvents()
    for name,panel in (('awg',window._experiment_panel),('stability',window._stability_panel)):
        panel.bias_t_type.dc_checkbox.setChecked(True)
        panel.bias_t_type.rc_checkbox.setChecked(True)
        panel.bias_t_filter_tau_us.setValue(1000.)
        if name=='stability':window._control_tabs.setCurrentWidget(panel)
        app.processEvents()
        panel.bias_t_group.grab().save(str(a.output/f'{name}_dc_rc_controls.png'))
    square=window._square_dds_panel
    square.rc_enabled.setChecked(True);square.rc_tau_us.setValue(1000.)
    square.enabled.setChecked(True)
    window._control_tabs.setCurrentWidget(window._awg_tuning_page)
    window._awg_tuning_tabs.setCurrentWidget(window._square_dds_scroll)
    app.processEvents();square.grab().save(str(a.output/'square_rc_controls.png'))
    window.close();window.deleteLater()
    app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents()
    (a.output/'gui_capture.json').write_text(json.dumps(dict(source='Actual Qt widgets, offscreen rendering',live_hardware=False),indent=2))


if __name__=='__main__':main()
