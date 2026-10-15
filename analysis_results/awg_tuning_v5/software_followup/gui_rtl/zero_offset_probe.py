"""Actual GUI negative test: exact requested HOLD/RF timestamp is not moved."""
from dataclasses import asdict,replace
import gc
import json
from pathlib import Path
import sys
import traceback
from extension_v5 import configure,source_hashes

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
GUI=ROOT.parent/'PulseGenerator/DCWaveformGeneratorGUI'
BASE=Path('F:/Vivado_Output/a3sim1/rc_precomp_repeat_reset_hold_duration_2x2_v4_all_20261014_exact10us_hold1_output_sum_awg_v3')

def main():
    sys.path.insert(0,str(GUI))
    import qick.sim
    from qick import QickConfig
    from PyQt5 import QtCore,QtGui,QtWidgets,sip
    import DCWaveform_Generator as gui
    from qick_front_panel import identify_qick_front_panel
    from qick_qcodes_experiment import build_qick_program
    cfg=QickConfig(json.loads((ROOT/'qick/firmware/projects/qstl_gui_rtl_sim/soccfg.json').read_text()))
    for gen in cfg['gens']:
        if gen['type'] in ('axis_awg_tuning_v1','axis_square_pulse_v1'):gen.update(rc_precomp_version=1,output_latency_cycles=11)
        if gen['type']=='axis_square_pulse_v1':gen['command_latency_cycles']=15
        if gen['type']=='axis_awg_tuning_v1':gen.update(type='axis_awg_tuning_v3',frac=18,step_width=32,dc_area_version=1,dc_area_bits=48,output_latency_cycles=16,dc_start_cycles=17)
    configure(cfg)
    app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False);app.setFont(QtGui.QFont('Segoe UI',9))
    results=[];errors=[]
    sys.excepthook=lambda *args:errors.append(''.join(traceback.format_exception(*args)))
    out=HERE/'zero_offset';out.mkdir(exist_ok=False)
    try:
        for hold in (1,2):
            for channels in ((0,),(2,),(4,),(0,2,4)):
                data=json.loads((BASE/'gui_input.json').read_text())
                data['rf_outputs']=[dict(spec,enabled=spec['gen_ch'] in channels,segment_name=f'set_{hold}',delay_us=0.,duration_us=10.) for spec in data['rf_outputs']]
                path=out/f'hold{hold}_channels{"_".join(map(str,channels))}.json';path.write_text(json.dumps(data,indent=2))
                window=gui.MainWindow();window._on_qick_configuration_identified(replace(identify_qick_front_panel(cfg),dac_current_settings=data['qick']['dac_current_settings']))
                window._load_settings_json(path);app.processEvents()
                args=window._experiment_run_arguments(require_readout=False,require_run_config=False)
                assert {s.gen_ch for s in args['rf_specs']}==set(channels)
                assert all(s.delay_us==0. and s.duration_us==10. for s in args['rf_specs'])
                error=None
                try:
                    p=build_qick_program(cfg,**{key:args[key] for key in ('sequence','awg_channels','repetitions_per_sweep','rf_specs','readout_spec','compile_validation_mode')},tproc_mhz=300.)
                    p.compile()
                except ValueError as exc:error=str(exc)
                assert error and ('spacing' in error.lower() or 'shared' in error.lower()),error
                results.append(dict(hold=hold,channels=channels,requested_rf_offset_us=0.,duration_us=10.,error=error,
                    expected_rejection=True,source='real MainWindow settings → experiment arguments → production build_qick_program',guard_modified=False))
                window.close();window.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents();del window;gc.collect()
        assert not errors,errors
        (out/'result.json').write_text(json.dumps(dict(passed=True,cases=results,source_hashes=source_hashes(GUI.parent),
            conclusion='The current GUI compiler rejects exact zero-offset shared-port HOLD/RF; no timing was silently moved.'),indent=2))
    finally:
        for window in app.topLevelWidgets():window.close();window.deleteLater()
        app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents();QtCore.QTimer.singleShot(0,app.quit);app.exec_();sip.delete(app)

if __name__=='__main__':main()
