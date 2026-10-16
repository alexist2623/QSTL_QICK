"""Build real MainWindow settings through the Run Experiment compiler path.

No board connection or hardware write is performed. All inputs and the resulting
PMEM are retained so the GUI path can be matched to the actual RTL snapshot.
"""
import gc
import json
from dataclasses import asdict, replace

def build_from_widgets(cfg, pulses, axes, rf_specs, options, out):
    from PyQt5 import QtCore, QtGui, QtWidgets, sip
    import DCWaveform_Generator as gui
    from qick_front_panel import identify_qick_front_panel
    from qick_qcodes_experiment import build_qick_program
    from dc_waveform_core import QickDdrReadoutSpec
    existing_app=QtWidgets.QApplication.instance()
    app=existing_app or QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    app.setFont(QtGui.QFont('Segoe UI',10))
    app.setStyle('Fusion')
    window=gui.MainWindow()
    currents={}
    summed=bool(getattr(options,'output_sum',False))
    awg_channels=(1,3,5) if summed else (1,3)
    channels=(1,3,5,7) if summed else (1,3,7)
    current_values=(*options.dac_current_ma[:2],20.,options.dac_current_ma[2]) if summed else options.dac_current_ma
    for channel,ma in zip(channels,current_values):
        dac=cfg['gens'][channel]['dac']
        currents[dac]=dict(converter_id=dac,channels=[channel],dc_output=True,
            current_ua=int(ma*1000),adjustable=True,reason='RTL input fixture')
    panel_cfg=replace(identify_qick_front_panel(cfg),dac_current_settings=currents)
    window._on_qick_configuration_identified(panel_cfg)
    data=window._settings_to_dict()
    data['awg']['outputs']=[p.to_dict() for p in pulses]
    data['awg']['cross_capacitance']=np.eye(3).tolist()
    data['awg']['sweeps']=[]
    data['qick'].update(fabric_mhz=300.,tproc_mhz=300.,full_scale_mv=800.,
        awg_channels=list(awg_channels),repetitions_per_sweep=2,compile_validation_mode='boundary',
        dac_current_settings=currents)
    rc_only=bool(getattr(options,'rc_only',False))
    data['qick']['bias_t_compensation']=dict(enabled=options.virtual_case['compensation']!='off',type=options.virtual_case['compensation'] if options.virtual_case['compensation']!='off' else 'dc',mode=options.dc_mode,
        voltage_mv=options.dc_voltage_mv,duration_us=1.,filter_tau_us=10.)
    data['rf_outputs']=[dict(asdict(s),enabled=True) for s in (rf_specs or ())]
    if options.dc_readout_policy:
        readout=QickDdrReadoutSpec(0,'set_0',0.,options.stored_fir_samples,
            margin_input_samples=0,dc_compensation_timing=options.dc_readout_policy)
        data['rf_readout']=dict(asdict(readout),enabled=True)
    data['square_pulse']=options.virtual_square if options.virtual_case['square'] else dict(enabled=False)
    data['output_trigger'].update(enabled=not options.no_aux,pin=0,scope='loop',edge='both',width_us=.1)
    path=out/'gui_input.json'
    path.write_text(json.dumps(data,indent=2),encoding='utf-8')
    window._load_settings_json(path)
    input_widgets(window,app,axes,options,out)
    (out/'gui_input.json').write_text(json.dumps(window._settings_to_dict(),indent=2),encoding='utf8')
    try:
        runtime=window._experiment_run_arguments(require_readout=bool(options.dc_readout_policy),
                                                require_run_config=False)
        if options.reverse_axes:
            runtime['sequence'].sweeps.reverse()
        program=build_qick_program(cfg,**{key:runtime[key] for key in (
            'sequence','awg_channels','repetitions_per_sweep','rf_specs','readout_spec','compile_validation_mode')},
            tproc_mhz=300.)
        program.compile()
    except Exception as exc:
        (out/'gui_rejection.json').write_text(json.dumps(dict(error=repr(exc),source='Actual MainWindow Run Experiment compiler',guard_modified=False),indent=2))
        window.close();window.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents()
        QtCore.QTimer.singleShot(0,app.quit);app.exec_();del window;gc.collect()
        if existing_app is None:sip.delete(app)
        raise
    window.resize(1550,950)
    window.show()
    app.processEvents()
    window.grab().save(str(out/'gui_input.png'))
    window._experiment_panel.bias_t_group.grab().save(str(out/'gui_dc_controls.png'))
    dialog=gui.QickAssemblyDialog({'assembly':program.asm(),'program':program,
        'instruction_count':len(program.prog_list),'machine_word_count':len(program.binprog)})
    dialog.resize(1200,850)
    dialog.tabs.setCurrentIndex(1)
    dialog.show()
    app.processEvents()
    dialog.grab().save(str(out/'gui_compiled_timing.png'))
    dialog.close()
    dialog.deleteLater()
    (out/'gui_widget_pmem.hex').write_text(''.join(f'{int(w):016x}\n' for w in program.binprog))
    window.close()
    window.deleteLater()
    app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete)
    app.processEvents()
    QtCore.QTimer.singleShot(0,app.quit)
    app.exec_()
    # Match the real GUI main() lifecycle. Restored editor/plot callbacks form
    # reference cycles; collect their wrappers while Qt is still alive, then
    # destroy our owned application before Python tears down module globals.
    del dialog, window
    gc.collect()
    if existing_app is None:
        sip.delete(app)
    return program
