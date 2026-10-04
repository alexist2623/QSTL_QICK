"""Render the implemented Qt controls and compiled timing view without hardware."""
import argparse
import os
from pathlib import Path
import sys

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--gui',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    sys.path.insert(0,str(args.gui/'DCWaveformGeneratorGUI'))
    from PyQt5 import QtGui, QtWidgets, QtTest
    from qick.sim import QickSim
    from test_dc_readout_timing import execute
    from dc_waveform_core import PulseSequence
    import DCWaveform_Generator as gui
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    app.setFont(QtGui.QFont('Segoe UI',10))
    app.setStyle('Fusion')
    panel=gui.RfReadoutPanel(PulseSequence(10.,initial_duration_ns=6000.),time_unit='us')
    panel.setChecked(True)
    panel.frequency_mhz.setValue(0.)
    panel.samples.setValue(12)
    panel.dc_compensation_timing.setCurrentIndex(1)
    panel.resize(840,1050)
    panel.show()
    QtTest.QTest.qWait(150)
    panel.grab().save(str(args.out/'rf_readout_controls.png'))
    p,_=execute('overlap_readout',sweep='hold')
    dialog=gui.QickAssemblyDialog(dict(assembly=p.asm(),program=p,
        instruction_count=len(p.prog_list),machine_word_count=len(p.binprog)))
    dialog.resize(1060,860)
    dialog.tabs.setCurrentIndex(1)
    dialog.timing_point.setValue(11)
    dialog.show()
    app.processEvents()
    dialog.grab().save(str(args.out/'compiled_timing_preview.png'))
    panel.close()
    dialog.close()
    print(args.out)

if __name__=='__main__': main()
