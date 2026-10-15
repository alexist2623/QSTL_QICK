"""Recompile saved real UI inputs, independently audit C@V and RF offsets.

Validation-only supplement: no xsim, production edits, or board access.
"""
import gc
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
import time
from dataclasses import asdict
import audit as a
from audit import QtCore,QtGui,QtWidgets,QtTest,sip,np
from dc_waveform_core import QickRfPulseSpec
from support import matrix_oracle

HERE=a.HERE
OUT=HERE/'semantic_audit'


def main():
    assert not OUT.exists()
    OUT.mkdir()
    sources=json.loads((HERE/'inventory.json').read_text())['source_hashes']
    assert all(a.sha(p)==h for p,h in sources.items())
    preparations=[json.loads((HERE/n).read_text()) for n in ('prepared.json','prepared_cpmg.json')]
    app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False);app.setFont(QtGui.QFont('Segoe UI',10))
    rows=[]
    try:
        for prepared in preparations:
            for case in prepared['cases']:
                source=Path(case['folder']);out=OUT/case['name'];out.mkdir()
                request=json.loads((source/'request.json').read_text())['original_case']
                w=a.gui.MainWindow();w._on_qick_configuration_identified(a.identify_qick_front_panel(a.configuration()))
                w._load_settings_json(source/'gui_input.json');app.processEvents()
                evidence=dict(name=case['name'],source=str(source),original_case=case['original_case'],explicit_offset_variant=case['explicit_offset_variant'])
                if request['kind']=='quantum':
                    from quantum_circuit_execution import build_circuit_execution
                    runtime=w._quantum_circuit_run_arguments();keys=set(inspect.signature(build_circuit_execution).parameters)-{'document','soccfg'}
                    execution=build_circuit_execution(runtime['document'],a.configuration(),**{k:v for k,v in runtime.items() if k in keys})
                    p=execution.program
                    np.testing.assert_array_equal(execution.sequence.cross_capacitance,np.eye(2))
                    evidence.update(quantum_inherits_awg_matrix=False,identity_matrix=True)
                else:
                    runtime=w._experiment_run_arguments(require_readout=False,require_run_config=False)
                    specs=runtime['rf_specs'];bindings=a._rf_software_sweep_bindings(specs)
                    coords=a._software_sweep_coordinates(bindings)
                    np.testing.assert_array_equal(coords,[[1,.2],[1,.4],[2,.2],[2,.4]])
                    actual=a._rf_specs_at_software_coordinate(specs,bindings,[request['n'],request['tau']])
                    original=[QickRfPulseSpec(**v) for v in json.loads((HERE/case['original_case']/'concrete_specs.json').read_text())]
                    offsets=[]
                    for before,after in zip(original,actual):
                        assert len(before.pulse_events)==len(after.pulse_events)
                        for b,e in zip(before.pulse_events,after.pulse_events):
                            old=asdict(b);new=asdict(e);delta=new.pop('delay_us')-old.pop('delay_us')
                            assert old==new,(case['name'],old,new)
                            np.testing.assert_allclose(delta,.1,atol=1e-12,rtol=0)
                            offsets.append(dict(channel=after.gen_ch,event=e.event_id,offset_us=delta))
                    seq=a._sequence_at_rf_software_coordinate(runtime['sequence'],actual,fabric_mhz=300.)
                    p=a.build_qick_program(a.configuration(),seq,awg_channels=runtime['awg_channels'],repetitions_per_sweep=2,rf_specs=actual,compile_validation_mode='boundary',tproc_mhz=300.)
                    p.compile()
                    settings=json.loads((source/'gui_input.json').read_text())
                    pulses=[SimpleNamespace(v=np.asarray(v['voltage_mv'])) for v in settings['awg']['outputs']]
                    matrix=np.asarray(settings['awg']['cross_capacitance']);np.testing.assert_array_equal(matrix,a.MATRIX)
                    matrix_oracle(p,pulses,seq.sweep_axes,matrix,[800,400,800],out)
                    assert p.sequence.sweep_point_count==9
                    evidence.update(points=9,matrix_target_comparisons=27,pulse_event_changes=offsets,internal_event_fields_equal=True)
                p.compile()
                pmem=''.join(f'{int(v):016x}\n' for v in p.binprog)
                dmem=''.join(f'{p._runtime_dmem_base+i:08x} {int(v)&0xffffffff:08x}\n' for i,v in enumerate(p._runtime_dmem_words))
                assert pmem==(source/'pmem.hex').read_text()
                assert dmem==(source/'dmem.txt').read_text()
                evidence.update(passed=True,pmem_equal=True,dmem_equal=True)
                a.save(out/'result.json',evidence);rows.append(evidence)
                print('PASS',case['name'],flush=True)
                QtTest.QTest.qWait(300);w.close();w.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents();del w;gc.collect()
        assert all(a.sha(p)==h for p,h in sources.items())
        a.save(OUT/'result.json',dict(passed=True,finished=time.strftime('%Y-%m-%dT%H:%M:%S%z'),cases=rows,source_hashes=sources,
            audit_script_sha256=a.sha(__file__),matrix_oracle_sha256=a.sha(a.OLD/'support.py'),actual_rtl_execution=False,board_access=False))
    finally:
        for w in app.topLevelWidgets():w.close();w.deleteLater()
        app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents();QtCore.QTimer.singleShot(0,app.quit);app.exec_();sip.delete(app)
        print('QT_EXPLICIT_TEARDOWN_COMPLETE',flush=True)


if __name__=='__main__':main()
