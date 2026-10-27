"""Explicit unsupported combinations and composite/loop compiler coverage.

These are GUI/compiler tests, not Verilog or board measurements. Actual
Verilog evidence is produced separately by run_batch.py.
"""
from dataclasses import replace
from pathlib import Path
import gc
import json
import inspect
import numpy as np
import pytest
from qick.sim import QickSim
from qick import QickConfig
from PyQt5 import QtCore,QtGui,QtWidgets,QtTest,sip
import DCWaveform_Generator as gui
from qick_front_panel import identify_qick_front_panel
from dc_waveform_core import QickRfPulseSpec,QickRfFrequencyParameterSpec,QickRfDurationParameterSpec
from qick_qcodes_experiment import (build_runtime_rf_pulses,build_qick_program,
    _rf_software_sweep_bindings,_software_sweep_coordinates,
    _rf_specs_at_software_coordinate,_sequence_at_rf_software_coordinate)
from cases import MATRIX
from run_case import ROOT,EVIDENCE,folder
import sys
sys.path.insert(0, str(Path(gui.__file__).resolve().parent / 'test'))
sys.path.insert(0,str((Path(__file__).resolve().parents[6] / 'firmware/ip/axis_output_sum_v1/validation/virtual_gate').parent))
from gui_rtl_extension import configure

@pytest.fixture(scope='session')
def app():
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    app.setFont(QtGui.QFont('Segoe UI',10))
    yield app
    app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents()
    gc.collect();sip.delete(app)

def configuration():
    cfg=QickConfig(json.loads((ROOT/'qick/firmware/projects/qstl_gui_rtl_sim/soccfg.json').read_text()))
    for g in cfg['gens']:
        if g['type']=='axis_awg_tuning_v1':
            g.update(type='axis_awg_tuning_v3',frac=18,step_width=32,dc_area_version=1,dc_area_bits=48,
                     output_latency_cycles=16,dc_start_cycles=17,rc_precomp_version=1)
        if g['type']=='axis_square_pulse_v1':g.update(rc_precomp_version=1,output_latency_cycles=11,command_latency_cycles=15)
    configure(cfg)
    return cfg

@pytest.fixture
def window(app):
    w=gui.MainWindow()
    w._on_qick_configuration_identified(identify_qick_front_panel(configuration()))
    w._load_settings_json(folder('hold_fixed_time')/'gui_input.json')
    yield w
    QtTest.QTest.qWait(250)  # Let existing delayed scroll callbacks finish before deletion.
    w.close();w.deleteLater()
    app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents();gc.collect()

@pytest.mark.parametrize('channel',[0,2,4])
@pytest.mark.parametrize('power_sweep',[False,True])
def test_summed_rf_power_is_rejected_from_gui_spec(window,channel,power_sweep):
    panel=window._rf_ports_panel._panels[channel//2]
    values=panel.settings_dict()
    values.update(enabled=True,power_calibration_enabled=True,power_sweep_enabled=power_sweep,
        power_calibration_database_path=str(EVIDENCE/'unused_calibration.db'),power_calibration_run_id=1)
    panel.load_settings(values)
    spec=panel.configured_spec()
    assert spec.gen_ch==channel and spec.power_calibration_enabled
    with pytest.raises(ValueError,match='summed into the AWG physical output'):
        build_runtime_rf_pulses(configuration(),(spec,),tproc_mhz=300.)

@pytest.mark.parametrize('template',['cpmg','udd'])
@pytest.mark.parametrize('selected_coordinate',[(1,.2),(1,.4),(2,.2),(2,.4)])
def test_matrix_with_gui_predefined_n_tau_all_software_points(window,template,selected_coordinate):
    from dataclasses import asdict
    panel=window._rf_ports_panel._panels[0]
    values=panel.settings_dict()
    values.update(pulse_mode='composite',predefined_template=template,predefined_gain=2000,
        predefined_n=1,predefined_tau_us=.2,predefined_n_sweep_enabled=True,
        predefined_n_sweep_start=1,predefined_n_sweep_stop=2,predefined_n_sweep_count=2,
        predefined_tau_sweep_enabled=True,predefined_tau_sweep_start_us=.2,
        predefined_tau_sweep_stop_us=.4,predefined_tau_sweep_count=2,
        predefined_frequency_parameter='f0',predefined_duration_parameter='d0',
        frequency_parameters=[asdict(QickRfFrequencyParameterSpec('f0',190.))],
        duration_parameters=[asdict(QickRfDurationParameterSpec('d0',.1))],segment_length_mode='fixed')
    panel.load_settings(values)
    runtime=window._experiment_run_arguments(require_readout=False,require_run_config=False)
    np.testing.assert_array_equal(runtime['sequence'].cross_capacitance,MATRIX)
    specs=runtime['rf_specs'];bindings=_rf_software_sweep_bindings(specs)
    coordinates=_software_sweep_coordinates(bindings)
    assert coordinates.tolist()==[[1.,.2],[1.,.4],[2.,.2],[2.,.4]]
    results=[]
    for coordinate in [selected_coordinate]:
        n,tau=int(coordinate[0]),float(coordinate[1])
        concrete=_rf_specs_at_software_coordinate(specs,bindings,coordinate)
        seq=_sequence_at_rf_software_coordinate(runtime['sequence'],concrete,fabric_mhz=300.)
        program=build_qick_program(configuration(),seq,awg_channels=runtime['awg_channels'],
            repetitions_per_sweep=2,rf_specs=concrete,compile_validation_mode='boundary',tproc_mhz=300.)
        program.compile()
        np.testing.assert_array_equal(seq.cross_capacitance,MATRIX)
        events=concrete[0].pulse_events
        assert len(events)==n
        free=[tau*(i+.5) for i in range(n)] if template=='cpmg' else [tau*np.sin(np.pi*(i+1)/(2*n+2))**2 for i in range(n)]
        np.testing.assert_allclose([e.delay_us for e in events],[v+i*.1 for i,v in enumerate(free)],rtol=0,atol=1e-12)
        assert [e.duration_us for e in events]==[.1]*n
        results.append(dict(n=n,tau_us=tau,rf_delays_us=[e.delay_us for e in events],pmem_words=len(program.binprog)))
    (EVIDENCE/f'{template}_n{selected_coordinate[0]}_tau{selected_coordinate[1]}_software.json').write_text(json.dumps(results,indent=2))

@pytest.mark.parametrize('n',[0,1,3])
def test_quantum_loop_uses_physical_channels_not_awg_matrix(window,n):
    from quantum_circuit_execution import build_circuit_execution
    from test_quantum_circuit_loops import loop_document
    document=loop_document(n)
    window._quantum_circuit_panel.load_document(document)
    readout=window._rf_readout_panel.settings_dict()
    readout.update(enabled=True,segment_name='set_0')
    window._rf_readout_panel.load_settings(readout)
    runtime=window._quantum_circuit_run_arguments()
    np.testing.assert_array_equal(runtime['gui_settings']['awg']['cross_capacitance'],MATRIX)
    keys=set(inspect.signature(build_circuit_execution).parameters)-{'document','soccfg'}
    execution=build_circuit_execution(document,configuration(),**{k:v for k,v in runtime.items() if k in keys})
    execution.program.compile()
    np.testing.assert_array_equal(execution.sequence.cross_capacitance,np.eye(2))
    from quantum_circuit_model import build_timeline
    timeline=build_timeline(execution.document)
    assert timeline['awg'][0]['points'][-1][1]==10+n
    assert timeline['awg'][1]['points'][-1][1]==-10-n
    # Explicit characterization: there is no matrix argument in this product path.
    assert 'cross_capacitance' not in keys
