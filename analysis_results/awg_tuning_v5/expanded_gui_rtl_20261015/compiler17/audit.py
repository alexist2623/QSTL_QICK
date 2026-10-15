"""Fresh real-MainWindow inventory of the original 17 compiler combinations.

Validation only. Never connects to a board or modifies production files.
Original requests are kept separate from explicitly labelled offset variants.
"""
from dataclasses import asdict, is_dataclass
import gc
import hashlib
import inspect
import json
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
GUI = ROOT.parent / 'PulseGenerator/DCWaveformGeneratorGUI'
OLD = ROOT / 'qick/firmware/ip/axis_output_sum_v1/validation/virtual_gate'
EXT = ROOT / 'analysis_results/awg_tuning_v5/software_followup/gui_rtl'
sys.path[:0] = [str(EXT), str(GUI), str(OLD)]
import numpy as np
import qick.sim
from qick import QickConfig
from PyQt5 import QtCore, QtGui, QtWidgets, QtTest, sip
import DCWaveform_Generator as gui
from qick_front_panel import identify_qick_front_panel
from dc_waveform_core import QickRfFrequencyParameterSpec, QickRfDurationParameterSpec
from qick_qcodes_experiment import (build_runtime_rf_pulses, build_qick_program,
    _rf_software_sweep_bindings, _software_sweep_coordinates,
    _rf_specs_at_software_coordinate, _sequence_at_rf_software_coordinate)
from cases import MATRIX
from run_case import folder
from extension_v5 import configure


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def serial(value):
    if is_dataclass(value): return serial(asdict(value))
    if isinstance(value, dict): return {str(k): serial(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)): return [serial(v) for v in value]
    if isinstance(value, np.ndarray): return value.tolist()
    if isinstance(value, np.generic): return value.item()
    if isinstance(value, Path): return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None: return value
    return repr(value)


def save(path, value):
    path.write_text(json.dumps(serial(value), indent=2), encoding='utf-8')


def configuration():
    cfg = QickConfig(json.loads((ROOT/'qick/firmware/projects/qstl_gui_rtl_sim/soccfg.json').read_text()))
    for g in cfg['gens']:
        if g['type'] == 'axis_awg_tuning_v1':
            g.update(type='axis_awg_tuning_v3',frac=18,step_width=32,dc_area_version=1,
                dc_area_bits=48,output_latency_cycles=16,dc_start_cycles=17,rc_precomp_version=1)
        if g['type'] == 'axis_square_pulse_v1':
            g.update(rc_precomp_version=1,output_latency_cycles=11,command_latency_cycles=15)
    configure(cfg)
    return cfg


def write_program(program, out):
    program.compile()
    (out/'pmem.hex').write_text(''.join(f'{int(w):016x}\n' for w in program.binprog))
    words=getattr(program, '_runtime_dmem_words', ())
    base=getattr(program, '_runtime_dmem_base', 0)
    (out/'dmem.txt').write_text(''.join(f'{base+i:08x} {int(w)&0xffffffff:08x}\n' for i,w in enumerate(words)))
    from qick.awg_tuning import TProcV1BehaviorModel
    model=TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(model)
    model.run(program, max_steps=10000000)
    assert not model.timing_conflicts
    save(out/'expected_commands.json', [dict(cycle=e.cycle,tproc_ch=e.tproc_ch,word=hex(e.word)) for e in model.output_events])
    return dict(pmem_words=len(program.binprog), command_count=len(model.output_events),
        pmem_sha256=sha(out/'pmem.hex'), dmem_sha256=sha(out/'dmem.txt'))


def main():
    assert not (HERE/'inventory.json').exists(), 'Keep previous audit evidence immutable'
    app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False);app.setFont(QtGui.QFont('Segoe UI',10))
    qt_errors=[]
    sys.excepthook=lambda *args: qt_errors.append(''.join(traceback.format_exception(*args)))
    cfg=configuration();save(HERE/'configured_soccfg.json',cfg._cfg)
    baseline=folder('hold_fixed_time')/'gui_input.json'
    sources={str(p):sha(p) for p in [*GUI.glob('*.py'),*(ROOT/'qick/qick_lib/qick').rglob('*.py'),
        Path(__file__),EXT/'extension_v5.py',Path(cfg['validation_candidate_hwh']),OLD/'test_coverage.py',baseline]}
    save(HERE/'source_hashes_before.json',sources)
    definitions=[]
    for sweep in (False,True):
        for ch in (0,2,4): definitions.append(dict(name=f'calibration_ch{ch}_sweep{int(sweep)}',kind='calibration',channel=ch,power_sweep=sweep))
    for n,tau in ((1,.2),(1,.4),(2,.2),(2,.4)):
        for template in ('cpmg','udd'): definitions.append(dict(name=f'{template}_n{n}_tau{round(tau*1000)}ns',kind='composite',template=template,n=n,tau=tau))
    for n in (0,1,3): definitions.append(dict(name=f'quantum_n{n}',kind='quantum',n=n))
    results=[]
    try:
        for definition in definitions:
            out=HERE/definition['name'];out.mkdir();save(out/'request.json',definition)
            w=gui.MainWindow();w._on_qick_configuration_identified(identify_qick_front_panel(configuration()));w._load_settings_json(baseline);app.processEvents()
            record=dict(**definition,path=str(out),actual_mainwindow=True,board_access=False)
            try:
                if definition['kind']=='calibration':
                    panel=w._rf_ports_panel._panels[definition['channel']//2]
                    values=panel.settings_dict();values.update(enabled=True,power_calibration_enabled=True,
                        power_sweep_enabled=definition['power_sweep'],power_calibration_database_path=str(HERE/'unused_calibration.db'),power_calibration_run_id=1)
                    panel.load_settings(values);spec=panel.configured_spec();save(out/'gui_input.json',w._settings_to_dict());save(out/'gui_runtime_spec.json',spec)
                    assert spec.gen_ch==definition['channel'] and spec.power_calibration_enabled
                    build_runtime_rf_pulses(configuration(),(spec,),tproc_mhz=300.)
                    record.update(outcome='unexpected_acceptance',expected_rejection=True)
                elif definition['kind']=='composite':
                    panel=w._rf_ports_panel._panels[0];values=panel.settings_dict()
                    values.update(pulse_mode='composite',predefined_template=definition['template'],predefined_gain=2000,
                        predefined_n=1,predefined_tau_us=.2,predefined_n_sweep_enabled=True,
                        predefined_n_sweep_start=1,predefined_n_sweep_stop=2,predefined_n_sweep_count=2,
                        predefined_tau_sweep_enabled=True,predefined_tau_sweep_start_us=.2,
                        predefined_tau_sweep_stop_us=.4,predefined_tau_sweep_count=2,
                        predefined_frequency_parameter='f0',predefined_duration_parameter='d0',
                        frequency_parameters=[asdict(QickRfFrequencyParameterSpec('f0',190.))],
                        duration_parameters=[asdict(QickRfDurationParameterSpec('d0',.1))],segment_length_mode='fixed')
                    panel.load_settings(values);save(out/'gui_input.json',w._settings_to_dict())
                    runtime=w._experiment_run_arguments(require_readout=False,require_run_config=False)
                    np.testing.assert_array_equal(runtime['sequence'].cross_capacitance,MATRIX)
                    specs=runtime['rf_specs'];save(out/'gui_runtime_specs.json',specs)
                    bindings=_rf_software_sweep_bindings(specs);coordinates=_software_sweep_coordinates(bindings)
                    save(out/'software_sweep.json',dict(bindings=bindings,coordinates=coordinates,selected=[definition['n'],definition['tau']]))
                    np.testing.assert_array_equal(coordinates,[[1.,.2],[1.,.4],[2.,.2],[2.,.4]])
                    concrete=_rf_specs_at_software_coordinate(specs,bindings,[definition['n'],definition['tau']])
                    seq=_sequence_at_rf_software_coordinate(runtime['sequence'],concrete,fabric_mhz=300.)
                    save(out/'concrete_specs.json',concrete)
                    p=build_qick_program(configuration(),seq,awg_channels=runtime['awg_channels'],repetitions_per_sweep=2,
                        rf_specs=concrete,compile_validation_mode='boundary',tproc_mhz=300.)
                    record.update(outcome='compiled',program=write_program(p,out),actual_rtl_required=True)
                else:
                    from quantum_circuit_execution import build_circuit_execution
                    from quantum_circuit_model import build_timeline
                    from test_quantum_circuit_loops import loop_document
                    document=loop_document(definition['n']);w._quantum_circuit_panel.load_document(document)
                    readout=w._rf_readout_panel.settings_dict();readout.update(enabled=True,segment_name='set_0');w._rf_readout_panel.load_settings(readout)
                    save(out/'gui_input.json',w._settings_to_dict());runtime=w._quantum_circuit_run_arguments()
                    save(out/'gui_runtime.json',runtime);save(out/'document.json',document)
                    np.testing.assert_array_equal(runtime['gui_settings']['awg']['cross_capacitance'],MATRIX)
                    keys=set(inspect.signature(build_circuit_execution).parameters)-{'document','soccfg'}
                    execution=build_circuit_execution(document,configuration(),**{k:v for k,v in runtime.items() if k in keys})
                    np.testing.assert_array_equal(execution.sequence.cross_capacitance,np.eye(2));assert 'cross_capacitance' not in keys
                    timeline=build_timeline(execution.document);save(out/'timeline.json',timeline)
                    assert timeline['awg'][0]['points'][-1][1]==10+definition['n'] and timeline['awg'][1]['points'][-1][1]==-10-definition['n']
                    record.update(outcome='compiled',program=write_program(execution.program,out),actual_rtl_required=True,quantum_inherits_awg_matrix=False)
            except BaseException as exc:
                record.update(outcome='rejected',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
                if definition['kind']=='calibration':
                    record['expected_rejection']=isinstance(exc,ValueError) and 'summed into the AWG physical output' in str(exc)
            save(out/'classification.json',record);results.append(record)
            print(definition['name'],record['outcome'],record.get('error',''),flush=True)
            QtTest.QTest.qWait(300);w.close();w.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents();del w;gc.collect()
            assert not qt_errors,qt_errors
        assert all(sha(p)==h for p,h in sources.items()),'Source changed during audit'
        save(HERE/'inventory.json',dict(complete=True,finished=time.strftime('%Y-%m-%dT%H:%M:%S%z'),cases=results,
            original_case_count=17,source_hashes=sources,qt_errors=qt_errors,board_access=False,actual_rtl_execution=False))
    finally:
        for w in app.topLevelWidgets():w.close();w.deleteLater()
        app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents();QtCore.QTimer.singleShot(0,app.quit);app.exec_();sip.delete(app)
        print('QT_EXPLICIT_TEARDOWN_COMPLETE',flush=True)

if __name__=='__main__':main()
