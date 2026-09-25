"""Render the real Qt controls using saved firmware routing; no board connection."""
import argparse
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument('--gui',type=Path,required=True);a=p.parse_args()
    sys.path.insert(0,str(a.gui/'DCWaveformGeneratorGUI'))
    from qick.sim import QickSim
    from PyQt5 import QtCore,QtGui,QtTest,QtWidgets
    from DCWaveform_Generator import MainWindow
    from qick_front_panel import identify_qick_front_panel
    cfg=json.loads((HERE/'soccfg.json').read_text())
    # Stored HWH provides the routing; card identity is a display fixture.
    cfg['extra_description']=[f'DAC slot {i}: DC Out card has ports [{4*i}, {4*i+1}, {4*i+2}, {4*i+3}]' for i in range(4)]
    cfg['extra_description'] += [f'ADC slot {i}: DC In card has ports [{2*i}, {2*i+1}]' for i in range(4)]
    directory=a.gui/'output/square_output_controls';directory.mkdir(parents=True,exist_ok=True)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    # The Windows offscreen Qt backend does not enumerate system fonts.
    for name in ('segoeui.ttf','segoeuib.ttf','arial.ttf','arialbd.ttf'):
        assert QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)>=0
    app.setFont(QtGui.QFont('Segoe UI',10))
    app.setStyle('Fusion')
    window=MainWindow()
    window._on_qick_configuration_identified(identify_qick_front_panel(cfg))
    window._control_tabs.setMinimumWidth(1000)
    window.resize(2200,1250);window.show()
    panel=window._square_wave_panel
    panel.frequency_hz.setValue(2000);panel.amplitude_mv.setValue(20);panel.phase_deg.setValue(45)
    window._control_tabs.setCurrentWidget(panel)
    QtTest.QTest.qWait(150)
    window._control_tabs.grab().save(str(directory/'square_wave_tab.png'))
    window._control_tabs.setCurrentWidget(window._awg_tuning_page)
    window._awg_tuning_tabs.setCurrentWidget(window._square_dds_scroll)
    square=window._square_dds_panel
    square.enabled.setChecked(True);square.mute_on_finish.setChecked(False)
    square.rows['frequency']['value'].setValue(.002)
    square.rows['amplitude']['sweep'].setChecked(True)
    square.rows['amplitude']['start'].setValue(10);square.rows['amplitude']['stop'].setValue(20)
    square.rows['amplitude']['count'].setValue(2);square.rows['phase']['value'].setValue(45)
    QtTest.QTest.qWait(150)
    window._control_tabs.grab().save(str(directory/'awg_squarepulse_tab.png'))
    window._show_qick_front_panel('output',panel)
    QtTest.QTest.qWait(150)
    window._qick_front_panel_dialog.grab().save(str(directory/'port_selector.png'))
    (directory/'capture_metadata.json').write_text(json.dumps(dict(
        source='Actual Qt widgets rendered offscreen',routing='saved production HWH-derived soccfg.json',
        daughter_cards='DC card display fixture; not live hardware identification'),indent=2)+'\n')
    window._qick_front_panel_dialog.close();window.close();window.deleteLater()
    app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents()
    print(directory)


if __name__=='__main__':main()
