"""Prepare original compiler17 nine-point CPMG plus explicit RF-offset RTL.

Uses real MainWindow, production builders and isolated existing vendor models.
No simulation is started by this module.
"""
import gc
import inspect
import json
from pathlib import Path
import sys
import time
from dataclasses import asdict
import audit as a
from audit import np,QtCore,QtGui,QtWidgets,QtTest,sip

HERE=a.HERE;BUILD=Path('F:/Vivado_Output/a5compiler2')
FINE=a.EXT/'fine'
sys.path.insert(0,str(FINE))
import harness
from extension_v5 import extra_monitor


def program_files(p,folder):
    p.compile()
    (folder/'pmem.hex').write_text(''.join(f'{int(v):016x}\n' for v in p.binprog))
    (folder/'dmem.txt').write_text(''.join(f'{p._runtime_dmem_base+i:08x} {int(v)&0xffffffff:08x}\n' for i,v in enumerate(p._runtime_dmem_words)))
    (folder/'program.asm').write_text(p.asm())
    for ch in (0,2,4):
        envs=p.envelopes[ch]['envs'];count=max((v['addr']+len(v['data']) for v in envs.values()),default=0);words=[0]*count
        for entry in envs.values():
            for i,(iv,qv) in enumerate(entry['data']):words[entry['addr']+i]=(int(iv)&65535)|((int(qv)&65535)<<16)
        (folder/f'envelope_{ch}.hex').write_text(''.join(f'{v:08x}\n' for v in words))
    from qick.awg_tuning import TProcV1BehaviorModel
    model=TProcV1BehaviorModel(strict=True);p.load_runtime_dmem_into_model(model);model.run(p,max_steps=10000000)
    assert not model.timing_conflicts
    events=[dict(cycle=e.cycle,port=e.tproc_ch,word=f'{e.word:040x}') for e in model.output_events]
    events += [dict(cycle=e['cycle'],port=e['port'],word=f'{e["word"]:040x}') for e in model.output_pin_events]
    cycles=max(e['cycle'] for e in events)+2500
    a.save(folder/'expected.json',dict(events=events,sequence_summary=p.summary(),cycles=cycles))
    return cycles,model


def add_monitors(template):
    path=template/'tb_rc_gui.sv';text=path.read_text()
    # The reused scaffold observes ports 0,1,2,3,7. Quantum also configures ports 4–6.
    blocks=[]
    for port in (4,5,6):
        blocks.append(f'''always @(posedge clk_300000000) if(resetn && dut.sim_bd_i.axis_tproc64x32_x8_0.m{port+1}_axis_tvalid)
 $fwrite(events_file,"%0d,%0d,{port},%040h\\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m{port+1}_axis_tdata);''')
    for suffix in (4,5,6):
        cell=f'dut.sim_bd_i.axis_awg_tuning_v1_{suffix}'
        blocks.append(f'''awg_v2_raw_checker #(.CHANNEL({suffix})) compiler_raw_{suffix} (
 .clk(clk_300000000),.rstn(resetn),.command_valid({cell}.s_axis_tvalid),
 .command({cell}.s_axis_tdata),.raw_samples({cell}.core_samples));
 final begin
  if({cell}.area_enabled && ({cell}.area_sum!==0 || {cell}.area_fault))
   $fatal(1,"Compiler17 area residual/fault suffix={suffix}");
  $display("COMPILER17_AREA suffix={suffix} shots=%0d residual=%0d enabled=%0d fault=%0d",
   {cell}.area_completed_shots,$signed({cell}.area_sum),{cell}.area_enabled,{cell}.area_fault);
 end''')
    text=text.replace('endmodule','\n'.join(blocks)+'\nendmodule')
    text=extra_monitor(text)
    path.write_text(text)


def main():
    assert not BUILD.exists(),'Use a new isolated folder; preserve previous evidence'
    BUILD.mkdir()
    app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False);app.setFont(QtGui.QFont('Segoe UI',10))
    errors=[];sys.excepthook=lambda *args:errors.append(''.join(a.traceback.format_exception(*args)))
    original=json.loads((HERE/'inventory.json').read_text());assert original['complete']
    assert all(a.sha(p)==h for p,h in original['source_hashes'].items())
    cases=[];rejected=[]
    names=[f'cpmg_n{n}_tau{tau}ns' for n,tau in ((1,200),(1,400),(2,200),(2,400))]
    try:
        for name in names:
            source=HERE/name;old=json.loads((source/'request.json').read_text())
            variant=name if name=='quantum_n0' else name+'_rf100ns'
            out=BUILD/variant;out.mkdir()
            w=a.gui.MainWindow();w._on_qick_configuration_identified(a.identify_qick_front_panel(a.configuration()));w._load_settings_json(source/'gui_input.json');app.processEvents()
            try:
                if old['kind']=='quantum':
                    from quantum_circuit_execution import build_circuit_execution
                    from quantum_circuit_model import build_timeline
                    runtime=w._quantum_circuit_run_arguments();keys=set(inspect.signature(build_circuit_execution).parameters)-{'document','soccfg'}
                    document=runtime['document'];execution=build_circuit_execution(document,a.configuration(),**{k:v for k,v in runtime.items() if k in keys})
                    p=execution.program;a.save(out/'timeline.json',build_timeline(execution.document));a.save(out/'gui_runtime.json',runtime)
                    np.testing.assert_array_equal(execution.sequence.cross_capacitance,np.eye(2))
                    description='Original Quantum Loop n=0 through actual MainWindow; no virtual matrix inheritance; no RF pulses'
                    rf_specs=[]
                else:
                    for panel in w._rf_ports_panel._panels[:3]:
                        values=panel.settings_dict();values['delay_us']=float(values['delay_us'])+.1;panel.load_settings(values)
                    runtime=w._experiment_run_arguments(require_readout=False,require_run_config=False)
                    specs=runtime['rf_specs'];bindings=a._rf_software_sweep_bindings(specs)
                    rf_specs=a._rf_specs_at_software_coordinate(specs,bindings,[old['n'],old['tau']])
                    seq=a._sequence_at_rf_software_coordinate(runtime['sequence'],rf_specs,fabric_mhz=300.)
                    np.testing.assert_array_equal(seq.cross_capacitance,a.MATRIX)
                    requested=[.1+old['tau']*(i+.5)+i*.1 for i in range(old['n'])]
                    np.testing.assert_allclose([v.delay_us for v in rf_specs[0].pulse_events],requested,atol=1e-12,rtol=0)
                    p=a.build_qick_program(a.configuration(),seq,awg_channels=runtime['awg_channels'],repetitions_per_sweep=2,rf_specs=rf_specs,compile_validation_mode='boundary',tproc_mhz=300.)
                    a.save(out/'gui_runtime_specs.json',specs);a.save(out/'concrete_specs.json',rf_specs)
                    description='Explicit validation variant: +100 ns RF outer HOLD offset on all three RF controls; original CPMG internal spacing and original rejection preserved'
                a.save(out/'gui_input.json',w._settings_to_dict());a.save(out/'request.json',dict(original_case=old,variant=description,original_folder=str(source)))
                cycles,model=program_files(p,out)
                if old['kind']=='quantum':
                    assert (out/'pmem.hex').read_bytes()==(source/'pmem.hex').read_bytes()
                    assert (out/'dmem.txt').read_bytes()==(source/'dmem.txt').read_bytes()
                shots=p.sequence.sweep_point_count*2
                rf_commands=[]
                for ch in (0,2,4):
                    port=p.soccfg['gens'][ch]['tproc_ch']
                    values=[dict(cycle=e.cycle,word=f'{e.word:040x}') for e in model.output_events if e.tproc_ch==port and (e.word>>152)&255==0 and (e.word>>96)&0xffffffff]
                    rf_commands.append(dict(channel=ch,port=port,commands=values))
                a.save(out/'rf_expected.json',rf_commands)
                record=dict(name=variant,folder=str(out),cycles=cycles,points=p.sequence.sweep_point_count,repetitions=2,shots=shots,
                    original_case=name,explicit_offset_variant=old['kind']!='quantum',request_description=description,
                    expected_area_shots=[shots,shots,0 if old['kind']=='quantum' else shots],
                    expected_rf_counts=[len(r['commands']) for r in rf_commands],inputs={p.name:a.sha(p) for p in out.iterdir() if p.is_file()})
                cases.append(record);print('PREPARED',variant,'shots',shots,'rf',record['expected_rf_counts'],'cycles',cycles,flush=True)
            except BaseException as exc:
                item=dict(name=variant,outcome='rejected',error=str(exc),traceback=a.traceback.format_exc());a.save(out/'rejection.json',item);rejected.append(item);print('REJECTED',variant,str(exc),flush=True)
            QtTest.QTest.qWait(300);w.close();w.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents();del w;gc.collect();assert not errors,errors
        info=harness.prepare(BUILD,copy_libraries=True);add_monitors(BUILD/'template')
        info['template_sources']={str(p):a.sha(p) for p in (BUILD/'template').iterdir() if p.is_file()}
        source_paths=[Path(__file__),Path(a.__file__),Path(harness.__file__),a.EXT/'extension_v5.py',a.ROOT/'qick/firmware/ip/axis_awg_tuning_v2/validation/awg_v2_raw_checker.sv',a.ROOT/'qick/firmware/ip/axis_output_sum_v2/src/axis_output_sum_v2.sv']
        evidence=dict(complete=True,prepared_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'),build=str(BUILD),cases=cases,rejected_variants=rejected,
            source_hashes=original['source_hashes'],helper_hashes={str(p):a.sha(p) for p in source_paths},actual_rtl_execution=False,**info)
        a.save(HERE/'prepared_cpmg.json',evidence);a.save(BUILD/'prepared.json',evidence)
    finally:
        for w in app.topLevelWidgets():w.close();w.deleteLater()
        app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents();QtCore.QTimer.singleShot(0,app.quit);app.exec_();sip.delete(app)
        print('QT_EXPLICIT_TEARDOWN_COMPLETE',flush=True)

if __name__=='__main__':main()
