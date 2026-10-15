"""Capture exact rejected command clocks/profile without changing scheduling."""
from pathlib import Path
import json
import gc
from PyQt5 import QtCore,QtGui,QtWidgets,QtTest,sip
import test_coverage as tests
from run_case import EVIDENCE,folder

if __name__=='__main__':
    app=QtWidgets.QApplication([])
    QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    app.setFont(QtGui.QFont('Segoe UI',10));app.setQuitOnLastWindowClosed(False)
    results={}
    for label,invoke in [('udd_n2_tau200ns',lambda w:tests.test_matrix_with_gui_predefined_n_tau_all_software_points(w,'udd',(2,.2))),
                         ('quantum_rf_loop_n1',lambda w:tests.test_quantum_loop_uses_physical_channels_not_awg_matrix(w,1))]:
        window=tests.gui.MainWindow()
        window._on_qick_configuration_identified(tests.identify_qick_front_panel(tests.configuration()))
        window._load_settings_json(folder('hold_fixed_time')/'gui_input.json')
        try:
            invoke(window)
            raise AssertionError('Expected the recorded rejection to reproduce')
        except ValueError as exc:
            details=dict(error=str(exc),frames=[])
            tb=exc.__traceback__
            while tb:
                frame=tb.tb_frame;loc=frame.f_locals
                if frame.f_code.co_name=='_build_aux_timing':
                    details['shared_port']=dict(port=loc['rf_port'],requested_rf_start=loc['requested_start'],
                        rf_command_clock=loc['rf_start'],rf_latency=loc['latency'],
                        conflicting_awg_command_clocks=sorted(t for t in loc['occupied'] if abs(t-loc['rf_start'])<3),
                        required_command_spacing=3)
                if frame.f_code.co_name=='_rf_latencies':
                    details['latency_profile']=dict(awg_profile=loc['awg_profile'],
                        actual_awg_latency=[loc['gens'][ch]['output_latency_cycles'] for ch in loc['awg_channels']],
                        required_awg_latency=16,rf=dict(loc['cfg']))
                details['frames'].append(dict(file=frame.f_code.co_filename,line=tb.tb_lineno,function=frame.f_code.co_name))
                tb=tb.tb_next
            results[label]=details
            (EVIDENCE/(label+'_gui_input.json')).write_text(json.dumps(window._settings_to_dict(),indent=2),encoding='utf8')
        finally:
            QtTest.QTest.qWait(250);window.close();window.deleteLater()
            app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents()
            del window;gc.collect()
    (EVIDENCE/'failure_diagnostics.json').write_text(json.dumps(results,indent=2),encoding='utf8')
    print(json.dumps({k:{a:b for a,b in v.items() if a!='frames'} for k,v in results.items()},indent=2))
    sip.delete(app)
