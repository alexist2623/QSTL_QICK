"""Small current-feature offline GUI/compile/tProcessor-model regression.

No production edits, board connection, upload, scope, or ADC acquisition.
All output records are explicitly intended references or digital model commands.
"""
from dataclasses import asdict, replace
from fractions import Fraction
import gc
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import socket
import sys
import time
import traceback
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path('C:/GIT_Workspace/QSTL_QICK')
GUI = Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')
BASE = Path('F:/Vivado_Output/a3sim1/rc_precomp_repeat_reset_hold_duration_2x2_v4_all_20261014_exact10us_hold1_output_sum_awg_v3/gui_input.json')
MATRIX = np.array([[1., .23, -.11], [-.17, 1., .07], [.12, -.09, 1.]])
LEVELS = np.array([[5.,20.,-10.], [-7.,-30.,15.], [3.,12.,-6.]])
GRID = np.logspace(-1,2,10)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False,
        default=lambda x: x.tolist() if hasattr(x,'tolist') else asdict(x)), encoding='utf8')
def ceil_clock(value, rate=300.):
    v = value*rate
    return max(1, round(v) if math.isclose(v,round(v),abs_tol=1e-8,rel_tol=1e-12) else math.ceil(v))
def signed(value,bits=32): return value-(1<<bits) if value & (1<<(bits-1)) else value
def code(mv): return max(-32768,min(32764,round(mv/800.*8192)*4))
def forbid(*a,**kw): raise AssertionError('Offline runner must not access a board/network')


def cases():
    out=[]
    for kind in ('hold','ramp'):
        for index,duration in enumerate(GRID):
            out.append(dict(name=f'log_{kind}_{index:02d}',kind=kind,duration=float(duration),matrix=index%2==1,reps=1))
    out += [dict(name=f'set_only_{mode}',kind='set',matrix=mode=='mixed',reps=2) for mode in ('identity','mixed')]
    out += [dict(name=f'voltage_{name}',kind='voltage',matrix=True,reps=2,count=count,start=start,stop=stop)
            for name,start,stop,count in (('ascending',-20.,20.,3),('descending',20.,-20.,3),('n1',-20.,-20.,1))]
    out += [dict(name='rf_frequency_digital',kind='frequency',matrix=True,reps=2)]
    for fine in (False,True):
        for extent,last in (('inside',.5),('crossing',2.5),('beyond_final',6.)):
            for require in (True,False):
                out.append(dict(name=f'rf_{"fine" if fine else "coarse"}_{extent}_{require}',
                    kind='rf_duration',matrix=True,reps=2,fine=fine,extent=extent,require=require,
                    first=.1,last=last,expected_rejection=require and extent!='inside'))
    assert len(out)==38
    return out


def configure_cfg():
    from qick import QickConfig
    cfg=QickConfig(json.loads((ROOT/'qick/firmware/projects/qstl_gui_rtl_sim/soccfg.json').read_text()))
    for gen in cfg['gens']:
        if gen['type'] in ('axis_awg_tuning_v1','axis_square_pulse_v1'):
            gen.update(rc_precomp_version=1,output_latency_cycles=11)
        if gen['type']=='axis_square_pulse_v1': gen['command_latency_cycles']=15
        if gen['type']=='axis_awg_tuning_v1':
            gen.update(type='axis_awg_tuning_v3',frac=18,step_width=32,dc_area_version=1,
                       dc_area_bits=48,output_latency_cycles=16,dc_start_cycles=17)
    path=ROOT/'analysis_results/awg_tuning_v5/software_followup/gui_rtl/extension_v5.py'
    spec=importlib.util.spec_from_file_location('simple_v5_route',path)
    ext=importlib.util.module_from_spec(spec);spec.loader.exec_module(ext);ext.configure(cfg)
    dump(HERE/'hardware_metadata_stub.json',dict(origin='offline sim configuration with actual candidate HWH output-route metadata; NOT discovered from a board',
        config=cfg._cfg,helper=str(path),helper_sha256=sha(path)))
    return cfg


def main():
    sys.path.insert(0,str(GUI))
    import qick.sim
    from qick.awg_tuning import TProcV1BehaviorModel
    from PyQt5 import QtCore,QtGui,QtTest,QtWidgets,sip
    import DCWaveform_Generator as gui
    import qick_qcodes_experiment as runtime
    from dc_waveform_core import QickRfPulseSpec
    from qick_front_panel import identify_qick_front_panel
    socket.create_connection=forbid;socket.socket.connect=forbid;socket.socket.connect_ex=forbid
    sources={str(p):sha(p) for p in list(GUI.glob('*.py'))+list((ROOT/'qick/qick_lib/qick').rglob('*.py'))}
    user_json={str(p):sha(p) for p in GUI.glob('*.json')}
    dump(HERE/'source_hashes_before.json',sources)
    dump(HERE/'plan.json',dict(cases=cases(),duration_grid_us=GRID,planned_cases=38,
        expected_negative_cases=4,scope='offline actual Qt input + production compiler + tProcessor instruction model',
        unavailable=['sweep grouping','register-arithmetic fine-duration implementation'],
        not_performed=['live GUI Run worker','upload','physical board identification','scope waveforms','analog RF frequency/timing','ADC/FIR acquisition']))
    cfg=configure_cfg()
    app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False)
    QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf');app.setFont(QtGui.QFont('Segoe UI',9));app.setStyle('Fusion')
    errors=[]
    sys.excepthook=lambda kind,value,tb:errors.append(''.join(traceback.format_exception(kind,value,tb)))
    results=[]

    def reveal(widget):
        child=widget
        while child.parentWidget() is not None:
            parent=child.parentWidget()
            if isinstance(parent,QtWidgets.QStackedWidget) and isinstance(parent.parentWidget(),QtWidgets.QTabWidget):
                tabs=parent.parentWidget();index=tabs.indexOf(child)
                if index>=0:
                    QtTest.QTest.mouseClick(tabs.tabBar(),QtCore.Qt.LeftButton,pos=tabs.tabBar().tabRect(index).center())
            child=parent
        parent=widget.parentWidget()
        while parent is not None:
            if isinstance(parent,QtWidgets.QScrollArea):parent.ensureWidgetVisible(widget)
            parent=parent.parentWidget()
        app.processEvents()

    def spin(widget,value):
        reveal(widget)
        QtTest.QTest.mouseClick(widget,QtCore.Qt.LeftButton)
        widget.selectAll();QtTest.QTest.keyClicks(widget,format(value,'.12g'))
        QtTest.QTest.keyClick(widget,QtCore.Qt.Key_Tab);app.processEvents()
        assert math.isclose(widget.value(),value,abs_tol=1e-8,rel_tol=1e-9),(widget.value(),value)

    def check(widget,enabled):
        reveal(widget)
        if widget.isChecked()!=enabled: QtTest.QTest.mouseClick(widget,QtCore.Qt.LeftButton,pos=QtCore.QPoint(8,widget.height()//2))
        assert widget.isChecked()==enabled

    def modal(action,edit):
        def apply():
            d=app.activeModalWidget()
            try:
                edit(d)
                QtTest.QTest.mouseClick(d.findChild(QtWidgets.QDialogButtonBox).button(QtWidgets.QDialogButtonBox.Ok),QtCore.Qt.LeftButton)
            except Exception:
                errors.append(traceback.format_exc());d.reject()
        QtCore.QTimer.singleShot(25,apply);action();assert not errors,errors

    def table_value(window,port,row,col,value):
        print(f'INPUT table port={port} row={row} col={col} value={value}',flush=True)
        table=window._multi_ctrl._ctrl_pannels[port].table
        item=table.item(row,col);table.scrollToItem(item)
        pos=table.visualItemRect(item).center()
        QtTest.QTest.mouseClick(table.viewport(),QtCore.Qt.LeftButton,pos=pos)
        QtTest.QTest.mouseDClick(table.viewport(),QtCore.Qt.LeftButton,pos=pos)
        editor=app.focusWidget()
        assert isinstance(editor,QtWidgets.QLineEdit),(port,row,col,type(editor))
        editor.selectAll();QtTest.QTest.keyClicks(editor,format(value,'.12g'))
        QtTest.QTest.keyClick(editor,QtCore.Qt.Key_Return);app.processEvents()

    try:
        selected=[case for case in cases() if len(sys.argv)==1 or case['name'] in sys.argv[1:]]
        assert selected
        for case in selected:
            folder=HERE/case['name'];attempt=1
            while folder.exists():
                attempt+=1;folder=HERE/f'{case["name"]}_attempt{attempt:02d}'
            folder.mkdir(exist_ok=False)
            dump(folder/'request.json',case)
            (folder/'runner_snapshot.py').write_bytes(Path(__file__).read_bytes())
            if case['kind']=='set':
                result=dict(name=case['name'],status='unavailable',model_executed=False,
                    reason='Exact zero-time SET transitions cannot be represented: production PulseSequence requires strictly increasing times and positive incoming ramp duration.',
                    fault_evidence=['set_only_mixed','set_only_mixed_attempt02','smoke3.log','smoke_set.log'],
                    limitation='Mixed-matrix input attempts faulted while showing the production invalid-edit QMessageBox. Identity variant not executed because the same zero-ramp input is unsupported.')
                dump(folder/'result.json',result);results.append(result);continue
            window=gui.MainWindow();started=time.time()
            try:
                seed=json.loads(BASE.read_text());seed['awg']['cross_capacitance']=np.eye(3).tolist();seed['awg']['sweeps']=[]
                for channel,output in enumerate(seed['awg']['outputs']):
                    output['time_ns']=[0.,1000.,2000.,4000.,5000.,6000.]
                    output['voltage_mv']=[0.,0.,0.,0.,0.,0.]
                seed['qick']['bias_t_compensation']['enabled']=False
                seed['qick']['repetitions_per_sweep']=case['reps']
                seed['rf_readout']['enabled']=False;seed['square_pulse']['enabled']=False;seed['output_trigger']['enabled']=False
                rf_on=case['kind'] in ('frequency','rf_duration')
                seed['rf_outputs']=[dict(asdict(QickRfPulseSpec(ch,'set_1',.1,.1,0.,1000+index*1000,0.,0.,output_board_type='DC_Out')),enabled=rf_on)
                    for index,ch in enumerate((0,2,4))]
                dump(folder/'seed.json',seed)
                window._on_qick_configuration_identified(replace(identify_qick_front_panel(cfg),dac_current_settings=seed['qick']['dac_current_settings']))
                window._load_settings_json(folder/'seed.json');window.resize(1600,1000);window.show();app.processEvents()
                # Real item editors commit the three independent output levels.
                for port in range(3):
                    for row in range(3):table_value(window,port,row,4,float(LEVELS[port,row]))
                ramp=0. if case['kind']=='set' else case.get('duration',1.) if case['kind']=='ramp' else 1.
                hold=case.get('duration',2.) if case['kind']=='hold' else 2.
                last_ramp=0. if case['kind']=='set' else 1.
                requested_times_ns=np.array([0.,1.,1.+ramp,1.+ramp+hold,
                    1.+ramp+hold+last_ramp,2.+ramp+hold+last_ramp])*1000.
                for port in range(3):
                    table_value(window,port,1,2,ramp)
                    table_value(window,port,1,3,hold)
                    table_value(window,port,2,2,0. if case['kind']=='set' else 1.)
                matrix=MATRIX if case['matrix'] else np.eye(3)
                def matrix_edit(d):
                    assert isinstance(d,gui.CrossCapacitanceDialog)
                    for row in range(3):
                        for col in range(3):
                            if row!=col:spin(d._editors[row][col],matrix[row,col])
                    np.testing.assert_array_equal(d.matrix(),matrix)
                    assert d.grab().save(str(folder/'matrix_dialog.png'))
                modal(window._configure_cross_capacitance,matrix_edit)
                if case['kind']=='voltage':
                    def sweep_edit(d):
                        spin(d.start,case['start']);spin(d.stop,case['stop']);spin(d.count,case['count'])
                        assert d.grab().save(str(folder/'voltage_sweep_dialog.png'))
                    modal(lambda:window._configure_segment_sweep(0,1),sweep_edit)
                rf_panel=window._rf_ports_panel._panels[0]
                if case['kind']=='frequency':
                    spin(rf_panel.duration,.5);spin(rf_panel.frequency_mhz,80.)
                    spin(rf_panel.frequency_sweep_start_mhz,80.);spin(rf_panel.frequency_sweep_stop_mhz,120.);spin(rf_panel.frequency_sweep_count,3)
                    check(rf_panel.frequency_sweep_enabled,True)
                if case['kind']=='rf_duration':
                    check(rf_panel.fine_duration,case['fine'])
                    check(rf_panel.require_within,case['require'])
                    spin(rf_panel.duration_sweep_start,case['first']);spin(rf_panel.duration_sweep_stop,case['last']);spin(rf_panel.duration_sweep_count,3)
                    check(rf_panel.duration_sweep_enabled,True)
                actual=window._settings_to_dict();dump(folder/'gui_input.json',actual)
                assert window.grab().save(str(folder/'gui.png'))
                inputs=[]
                for port,pulse in enumerate(window._pulse):
                    np.testing.assert_allclose(pulse.v[::2],LEVELS[port],rtol=0,atol=1e-10)
                    np.testing.assert_allclose(pulse.t,requested_times_ns,rtol=0,atol=1e-6)
                    inputs.append(dict(port=port,requested_ramp_us=ramp,requested_hold_us=hold,time_ns=pulse.t.tolist(),virtual_mv=pulse.v.tolist()))
                dump(folder/'committed_waveforms.json',inputs)
                # Archive requested analytic piecewise references even when compilation rejects.
                points=case.get('count',3 if rf_on else 1)
                refs=[]
                for point in range(points):
                    levels=LEVELS.copy()
                    if case['kind']=='voltage':levels[0,1]=np.linspace(case['start'],case['stop'],points)[point]
                    physical=matrix@levels
                    refs.append(dict(point=point,repetitions=case['reps'],virtual_mv=levels.tolist(),physical_mv=physical.tolist(),
                        requested_times_ns=requested_times_ns.tolist(),gui_committed_times_ns=inputs[0]['time_ns'],
                        ideal_physical_vertices_mv=np.repeat(physical,2,axis=1).tolist(),
                        reference_plane='piecewise ideal requested DAC output; no analog filter/calibration',
                        frequency_mhz=float(np.linspace(80,120,points)[point]) if case['kind']=='frequency' else 0.,
                        rf_duration_us=float(np.linspace(case['first'],case['last'],points)[point]) if case['kind']=='rf_duration' else .5 if case['kind']=='frequency' else None))
                dump(folder/'analytic_reference.json',dict(matrix=matrix,scales_mv=[800.,800.,800.],points=refs,
                    notes='Independent C @ V; numerical piecewise vertices define each complete requested waveform. Repetition references explicitly share the same immutable record.'))
                try:
                    args=window._experiment_run_arguments(require_readout=False,require_run_config=False)
                    dump(folder/'runtime_rf_specs.json',[asdict(s) for s in args['rf_specs']])
                    program=runtime.build_qick_program(cfg,args['sequence'],awg_channels=args['awg_channels'],repetitions_per_sweep=args['repetitions_per_sweep'],
                        rf_specs=args['rf_specs'],readout_spec=args['readout_spec'],tproc_mhz=300.,compile_validation_mode='full')
                    program.compile()
                except Exception as exc:
                    (folder/'compile_error.txt').write_text(traceback.format_exc(),encoding='utf8')
                    message=str(exc)
                    expected=bool(case.get('expected_rejection')) and ('segment' in message.lower() or 'hold' in message.lower())
                    result=dict(name=case['name'],status='expected_rejection' if expected else 'unexpected_rejection',error=message,expected_negative=bool(case.get('expected_rejection')),references=len(refs),model_executed=False)
                    dump(folder/'result.json',result);results.append(result);print(result,flush=True);continue
                if case.get('expected_rejection'):raise AssertionError('Expected later-point HOLD bound violation was accepted')
                assert program.sequence.sweep_point_count==points,(program.sequence.sweep_point_count,points)
                (folder/'pmem.hex').write_text(''.join(f'{int(w):016x}\n' for w in program.binprog))
                (folder/'program.asm').write_text(program.asm())
                (folder/'dmem.txt').write_text(''.join(f'{program._runtime_dmem_base+i:08x} {int(w)&0xffffffff:08x}\n' for i,w in enumerate(program._runtime_dmem_words)))
                if hasattr(program,'_fine_rf_rows'):dump(folder/'fine_rows.json',program._fine_rf_rows)
                model=TProcV1BehaviorModel(strict=True);program.load_runtime_dmem_into_model(model);model.run(program,max_steps=1000000)
                assert model.ended and not model.timing_conflicts and not model.unsupported_instructions
                events=[dict(cycle=e.cycle,port=e.tproc_ch,word=f'{e.word:040x}') for e in model.output_events]
                dump(folder/'model_commands.json',dict(events=events,pin_events=model.output_pin_events,dmem={str(k):v for k,v in model.dmem.items()},
                    layer='tProcessor instruction execution; not sampled analog/DAC measurements'))
                segment_kinds=[s.kind for s in program.sequence.segments]
                expected_kinds=['set','set','set'] if case['kind']=='set' else ['set','ramp','set','ramp','set']
                assert segment_kinds==expected_kinds,(case['name'],segment_kinds,expected_kinds)
                nseg=len(segment_kinds);shots=points*case['reps'];observed=[]
                for port in range(3):
                    awg=[e for e in model.output_events if e.tproc_ch==port and ((e.word>>152)&255)==1 and ((e.word>>144)&15) in (1,2)]
                    assert len(awg)==shots*nseg+1,(case['name'],port,len(awg),shots*nseg+1)
                    assert ((awg[0].word>>144)&15)==1 and signed(awg[0].word&0xffffffff)==0
                    awg=awg[1:]
                    for shot in range(shots):
                        point=shot//case['reps'];rep=shot%case['reps'];entries=awg[shot*nseg:(shot+1)*nseg]
                        set_index=0
                        for segment,(kind,e) in enumerate(zip(segment_kinds,entries)):
                            level_index=set_index if kind=='set' else set_index
                            target=code(refs[point]['physical_mv'][port][level_index])
                            if case['kind']=='voltage' and level_index==1:
                                first=code((matrix@np.array([case['start'],LEVELS[1,1],LEVELS[2,1]]))[port])
                                last=code((matrix@np.array([case['stop'],LEVELS[1,1],LEVELS[2,1]]))[port])
                                f=Fraction(last-first,max(1,points-1)*4);delta=(1 if f>=0 else -1)*int(abs(f)+Fraction(1,2))*4
                                target=first+point*delta
                            actual_target=signed(e.word&0xffffffff)
                            assert actual_target==target,(case['name'],port,shot,segment,actual_target,target)
                            duration_samples=(e.word>>64)&((1<<23)-1)
                            if kind=='ramp':
                                intended=ramp if set_index==1 else 1.
                                assert duration_samples==ceil_clock(intended)*16,(duration_samples,intended)
                            if kind=='set':set_index+=1
                            observed.append(dict(point=point,repetition=rep,port=port,segment=segment,kind=kind,cycle=e.cycle,
                                target_code=actual_target,expected_target_code=target,duration_samples=duration_samples,
                                observed_from='executed tProcessor output word',reference='independent C@V + documented DAC/constant-increment rounding'))
                        sets=[e for k,e in zip(segment_kinds,entries) if k=='set']
                        if case['kind']=='hold':
                            # SET1 -> RAMP1 command compensates existing seven-cycle ramp startup.
                            ramp_after=entries[segment_kinds.index('ramp',segment_kinds.index('ramp')+1)]
                            assert ramp_after.cycle-sets[1].cycle==ceil_clock(hold)-7,(case['name'],ramp_after.cycle-sets[1].cycle,hold)
                dump(folder/'model_awg_checks.json',dict(passed=True,observed=observed))
                rf_checks=[]
                for index,spec in enumerate(args['rf_specs']):
                    channel=spec.gen_ch;port=cfg['gens'][channel]['tproc_ch'];tmux=cfg['gens'][channel]['tmux_ch']
                    rf=[e for e in model.output_events if e.tproc_ch==port and ((e.word>>152)&255)==tmux]
                    cursor=0
                    for point in range(points):
                        duration=(refs[point]['rf_duration_us'] if index==0 else spec.duration_us)
                        freq=refs[point]['frequency_mhz'] if index==0 and case['kind']=='frequency' else spec.frequency_mhz
                        nsamples=ceil_clock(duration,4800.)
                        for rep in range(case['reps']):
                            e=rf[cursor];cursor+=1
                            observed_freq=e.word&0xffffffff;expected_freq=round(freq/4800.*2**32)&0xffffffff
                            assert observed_freq==expected_freq,(case['name'],observed_freq,expected_freq)
                            mode=(e.word>>128)&0xffff;gain=signed((e.word>>96)&0xffffffff)
                            if spec.fine_duration:
                                assert gain==spec.gain*(1 if nsamples>=96 else 2)
                                if nsamples>=96:cursor+=1
                            else:
                                assert mode==ceil_clock(duration),(case['name'],mode,duration)
                                assert gain==spec.gain
                            rf_checks.append(dict(point=point,repetition=rep,gen_ch=channel,command_cycle=e.cycle,
                                requested_duration_us=duration,expected_active_samples=nsamples if spec.fine_duration else ceil_clock(duration)*16,
                                fine=spec.fine_duration,requested_frequency_mhz=freq,frequency_register=observed_freq,
                                quantized_frequency_mhz=observed_freq*4800./2**32,gain=spec.gain,
                                active_width_measured=False,layer='digital command comparison only'))
                    assert cursor==len(rf),(case['name'],channel,cursor,len(rf))
                dump(folder/'model_rf_checks.json',dict(passed=True,checks=rf_checks,frequency_scope_measurement=False))
                dump(folder/'expected.json',dict(events=events,bursts=rf_checks,cycles=max(e['cycle'] for e in events)+2000))
                result=dict(name=case['name'],status='passed',layer='actual GUI -> production compiler -> tProcessor model',
                    points=points,repetitions=case['reps'],shots=shots,model_commands=len(events),awg_checks=len(observed),rf_checks=len(rf_checks),
                    requested_duration_us=case.get('duration'),quantized_duration_cycles=ceil_clock(case['duration']) if 'duration' in case else None,
                    pmem_words=len(program.binprog),dmem_words=len(program._runtime_dmem_words),elapsed_seconds=time.time()-started,
                    artifacts={p.name:sha(p) for p in folder.iterdir() if p.is_file()})
                dump(folder/'result.json',result);results.append(result);print(f'PASS {case["name"]} points={points} shots={shots}',flush=True)
            except Exception as exc:
                (folder/'runner_error.txt').write_text(traceback.format_exc(),encoding='utf8')
                result=dict(name=case['name'],status='failed',error=repr(exc));dump(folder/'result.json',result);results.append(result);print(result,flush=True)
            finally:
                window.close();window.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents();del window;gc.collect()
            dump(HERE/'progress.json',results)
        assert {path:sha(path) for path in sources}==sources
        assert {str(p):sha(p) for p in GUI.glob('*.json')}==user_json
        dump(HERE/'results.json',dict(complete=True,cases=results,source_hashes_unchanged=True,user_json_unchanged=True,
            helper_sha256=sha(__file__),qt_errors=errors,scope='offline compile/model only; source/board/RTL untouched',
            status_counts={s:sum(r['status']==s for r in results) for s in sorted({r['status'] for r in results})}))
    finally:
        QtCore.QTimer.singleShot(0,app.quit);app.exec_();sip.delete(app)


if __name__=='__main__':main()
