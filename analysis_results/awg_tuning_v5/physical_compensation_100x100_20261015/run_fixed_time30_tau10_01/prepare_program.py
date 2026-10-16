"""Offline actual-GUI preparation for the separately authorized scope test.

This module NEVER connects to or writes an instrument. ``prepare_program``
returns compiled objects for a separate, reviewed physical runner. The normal
program follows MainWindow input -> normal argument builder -> current compiler,
but bypasses the Run worker/ADC/DDR/QCoDeS acquisition path by explicit design.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass, replace
import gc
import gzip
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import sys
import traceback

ROOT = Path('C:/GIT_Workspace/QSTL_QICK')
GUI = Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')
HERE = Path(__file__).resolve().parent
AXIS_COUNT = 100
POINT_COUNT = AXIS_COUNT ** 2


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    def encode(obj):
        if hasattr(obj, 'tolist'):
            return obj.tolist()
        if is_dataclass(obj):
            return asdict(obj)
        if isinstance(obj, Path):
            return str(obj)
        raise TypeError(type(obj).__name__)
    if str(path).endswith('.gz'):
        with gzip.open(path,'wt',encoding='utf8',compresslevel=6) as stream:
            json.dump(value,stream,indent=2,default=encode)
    else:
        Path(path).write_text(json.dumps(value, indent=2, default=encode), encoding='utf8')


@contextmanager
def offline_only():
    originals = socket.create_connection, socket.socket.connect, socket.socket.connect_ex
    def deny(*args, **kwargs):
        raise RuntimeError('Preparation must not access a physical instrument or network')
    socket.create_connection = socket.socket.connect = socket.socket.connect_ex = deny
    try:
        yield
    finally:
        socket.create_connection, socket.socket.connect, socket.socket.connect_ex = originals


def prepare_program(*, board_config, current_settings, gen_channels,
                    full_scales_mv, output_dir, mode, hold_us, dc_time_us, tau_us,
                    start_mv, stop_mv, dc_voltage_mv, preflight_only=False):
    """Compile the verified two-generator mapping; no defaults imply wiring.

    Required scales must agree with supplied read-only live DAC current records.
    ``output_dir`` must be a new directory inside this evidence folder. All
    instrument operations remain the responsibility of the separate caller.
    """
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
    sys.path.insert(0, str(GUI))
    import numpy as np
    import qick.sim  # Desktop bootstrap only; no SoC instantiation.
    from qick import QickConfig
    from qick.asm_v1 import QickProgram
    from qick.awg_tuning import TProcV1BehaviorModel
    from PyQt5 import QtCore, QtTest, QtWidgets, sip
    import DCWaveform_Generator as gui
    import qick_qcodes_experiment as runtime
    from qick_front_panel import identify_qick_front_panel, awg_tuning_output_channels
    from qick_dac_current import full_scale_mv

    for value,name in ((hold_us,'hold_us'),(dc_time_us,'dc_time_us'),(tau_us,'tau_us'),(dc_voltage_mv,'dc_voltage_mv')):
        if not math.isfinite(value) or value<=0: raise ValueError(name+' must be finite and positive')
    if not math.isfinite(start_mv) or not math.isfinite(stop_mv) or start_mv>=stop_mv:
        raise ValueError('Require finite increasing start_mv/stop_mv')
    if mode not in ('fixed_voltage','fixed_time'):
        raise ValueError('Choose one authorized DC mode')
    destination = Path(output_dir).resolve()
    if destination.parent != HERE.resolve():
        raise ValueError('Use a new direct child directory of the evidence folder')
    if destination.exists():
        raise FileExistsError(destination)
    channels = tuple(map(int, gen_channels))
    scales = tuple(map(float, full_scales_mv))
    if len(channels) != 2 or len(set(channels)) != 2 or len(scales) != 2:
        raise ValueError('Exactly two distinct AWG channels and two verified scales are required')
    cfg = QickConfig(json.loads(Path(board_config).read_text(encoding='utf8')))
    currents = json.loads(Path(current_settings).read_text(encoding='utf8'))
    front = replace(identify_qick_front_panel(cfg), dac_current_settings=currents)
    if not set(channels) <= awg_tuning_output_channels(front):
        raise ValueError('Selected generators are not live-metadata AWG tuning channels')
    mapping = []
    for axis, (channel, scale) in enumerate(zip(channels, scales)):
        gen = cfg['gens'][channel]
        dac = str(gen['dac'])
        record = currents[dac]
        if not record['dc_output'] or channel not in record['channels']:
            raise ValueError('Selected DAC/current record does not match the AWG route')
        if not math.isclose(full_scale_mv(record['current_ua']), scale, abs_tol=1e-9):
            raise ValueError('Requested full scale differs from the recorded DAC current')
        if scale <= max(abs(start_mv),abs(stop_mv)):
            raise ValueError('Requested endpoints need headroom below full scale')
        paired = [i for i, item in enumerate(cfg['gens'])
                  if item.get('dac') == dac and item.get('type') == 'axis_signal_gen_v6']
        mapping.append(dict(axis=axis, output_name=f'awg_{axis}', awg_gen=channel,
                            dac=dac, panel_dac=4*int(dac[0])+int(dac[1]),
                            full_scale_mv=scale, current_ua=record['current_ua'],
                            paired_rf_generators=paired, tproc_ch=gen['tproc_ch'],
                            tmux_ch=gen['tmux_ch']))
    destination.mkdir()
    sources = {str(p): sha(p) for p in list(GUI.glob('*.py'))
               + list((ROOT/'qick/qick_lib/qick').rglob('*.py'))}
    dump(destination/'source_before.json', sources)
    dump(destination/'mapping.json', mapping)
    dump(destination/'board_config_snapshot.json', cfg._cfg)
    dump(destination/'dac_current_snapshot.json', currents)
    (destination/'prepare_program_snapshot.py').write_bytes(Path(__file__).read_bytes())
    errors = []
    previous_hook = sys.excepthook
    sys.excepthook = lambda kind, value, tb: errors.append(''.join(traceback.format_exception(kind, value, tb)))
    app = None
    window = None
    try:
        with offline_only():
            if QtWidgets.QApplication.instance() is not None:
                raise RuntimeError('Prepare in an isolated process, not an existing GUI process')
            app = QtWidgets.QApplication([])
            app.setQuitOnLastWindowClosed(False)
            app.setStyle('Fusion')
            window = gui.MainWindow()
            seed = window._settings_to_dict()
            times = [0.,10000.,11000.,11000.+hold_us*1000.,12000.+hold_us*1000.,22000.+hold_us*1000.]
            seed['display']['time_unit'] = 'us'
            seed['awg'] = dict(outputs=[dict(time_ns=times, voltage_mv=[0.]*6,
                voltage_bounds_mv=[-scale,scale],segment_names=['set_0','set_1','set_2']) for scale in scales],
                cross_capacitance=np.eye(2).tolist(), sweeps=[])
            seed['qick'].update(awg_channels=list(channels),full_scale_mv=max(800.,*scales),
                fabric_mhz=300.,tproc_mhz=300.,repetitions_per_sweep=1,
                dac_current_settings=currents,compile_validation_mode='full')
            seed['qick']['bias_t_compensation']['enabled'] = False
            seed['rf_outputs'] = []
            seed['rf_readout']['enabled'] = False
            seed['square_pulse']['enabled'] = False
            seed['output_trigger']['enabled'] = False
            dump(destination/'gui_seed.json', seed)
            window._on_qick_configuration_identified(front)
            window._load_settings_json(destination/'gui_seed.json')
            window.resize(1600,1000); window.show(); app.processEvents()

            # Each axis is committed through the real modal GUI sweep editor.
            for port in range(2):
                def edit_dialog(port=port):
                    dialog = app.activeModalWidget()
                    try:
                        for editor, value in ((dialog.start,start_mv),(dialog.stop,stop_mv),(dialog.count,AXIS_COUNT)):
                            editor.setFocus(); editor.selectAll()
                            QtTest.QTest.keyClicks(editor,format(value,'.12g'))
                            QtTest.QTest.keyClick(editor,QtCore.Qt.Key_Tab)
                            assert math.isclose(editor.value(),value,abs_tol=1e-9)
                        assert dialog.grab().save(str(destination/f'axis_{port}_dialog.png'))
                        QtTest.QTest.mouseClick(dialog.findChild(QtWidgets.QDialogButtonBox).button(QtWidgets.QDialogButtonBox.Ok),QtCore.Qt.LeftButton)
                    except Exception:
                        errors.append(traceback.format_exc()); dialog.reject()
                QtCore.QTimer.singleShot(30,edit_dialog)
                window._configure_segment_sweep(port,1)
                if errors: raise AssertionError(errors)
            # Enable both independent compensation controls through actual widgets.
            panel = window._experiment_panel
            for checkbox in (panel.bias_t_type.dc_checkbox, panel.bias_t_type.rc_checkbox):
                if not checkbox.isChecked():
                    checkbox.setFocus(); QtTest.QTest.keyClick(checkbox,QtCore.Qt.Key_Space)
                assert checkbox.isChecked()
            panel.bias_t_mode.setFocus()
            QtTest.QTest.keyClick(panel.bias_t_mode,QtCore.Qt.Key_Home)
            if mode == 'fixed_time': QtTest.QTest.keyClick(panel.bias_t_mode,QtCore.Qt.Key_Down)
            assert panel.bias_t_mode.currentData() == mode
            editors=[(panel.bias_t_filter_tau_us,tau_us)]
            editors.append((panel.bias_t_compensation_mv,dc_voltage_mv) if mode=='fixed_voltage'
                           else (panel.bias_t_duration_us,dc_time_us))
            for editor,value in editors:
                assert editor.isEnabled()
                editor.setFocus();editor.selectAll();QtTest.QTest.keyClicks(editor,format(value,'.12g'))
                QtTest.QTest.keyClick(editor,QtCore.Qt.Key_Tab)
                assert math.isclose(editor.value(),value,abs_tol=1e-9)
            assert panel.bias_t_group.isChecked() and panel.bias_t_type.currentData()=='dc_rc'
            assert panel.bias_t_group.grab().save(str(destination/'compensation_panel.png'))
            actual = window._settings_to_dict()
            dump(destination/'gui_input.json', actual)
            assert window.grab().save(str(destination/'gui.png'))
            args = window._experiment_run_arguments(require_readout=False,require_run_config=False)
            sequence = args['sequence']
            assert args['readout_spec'] is None and not args['rf_specs']
            assert tuple(args['awg_channels']) == channels and sequence.sweep_point_count == POINT_COUNT
            assert sequence.bias_t_compensation is not None and sequence.rc_compensation is not None
            assert sequence.bias_t_compensation.mode==mode and sequence.rc_compensation.tau_us==tau_us
            assert actual['qick']['bias_t_compensation']['type']=='dc_rc'
            for a in actual['awg']['sweeps']:
                # GUI JSON stores amplitude in the common normalized scale, not mV.
                assert math.isclose(a['start']*actual['qick']['full_scale_mv'],start_mv,abs_tol=1e-9)
                assert math.isclose(a['stop']*actual['qick']['full_scale_mv'],stop_mv,abs_tol=1e-9)
            assert tuple(sequence.sweep_shape)==(AXIS_COUNT,AXIS_COUNT)
            assert [axis.count for axis in sequence.sweep_axes]==[AXIS_COUNT,AXIS_COUNT]
            assert [axis.output_name for axis in sequence.sweep_axes]==['awg_0','awg_1']
            np.testing.assert_array_equal(sequence.cross_capacitance,np.eye(2))
            np.testing.assert_allclose(sequence.output_full_scales_mv,scales,rtol=0,atol=1e-9)
            assert [s.kind for s in sequence.segments] == ['set','ramp','set','ramp','set']
            assert [s.duration_cycles for s in sequence.segments] == [3000,300,round(hold_us*300),300,3000]
            dump(destination/'gui_arguments.json', dict(awg_channels=channels,repetitions_per_sweep=1,
                readout_spec=None,rf_specs=[],sequence_recipe=runtime.build_awg_waveform_recipe(
                    sequence,fabric_mhz=300.,full_scale_mv=window._qick_full_scale_mv),
                scope='MainWindow input -> argument builder -> compiler -> scope-only program.run; NO RunWorker/ADC/DDR/QCoDeS execution'))
            program = runtime.build_qick_program(cfg,sequence,awg_channels=channels,
                repetitions_per_sweep=1,rf_specs=(),readout_spec=None,tproc_mhz=300.,compile_validation_mode='full')
            program.compile()
            range_records=[dict(**row,
                minimum_mv=row['minimum_normalized']*scales[channels.index(row['gen_ch'])],
                maximum_mv=row['maximum_normalized']*scales[channels.index(row['gen_ch'])])
                for row in program.rc_output_range_validation]
            preflight=dict(status='preflight_accepted',mode=mode,hold_us=hold_us,
                dc_time_us=dc_time_us,tau_us=tau_us,start_mv=start_mv,stop_mv=stop_mv,
                dc_voltage_mv=dc_voltage_mv,points=POINT_COUNT,pmem_words=len(program.binprog),
                rc_output_range_validation=range_records,
                global_rc_bounds_mv=[min(r['minimum_mv'] for r in range_records),max(r['maximum_mv'] for r in range_records)],
                helper_sha256=sha(__file__),physical_execution=False)
            dump(destination/'preflight.json',preflight)
            if preflight_only:
                assert {p:sha(p) for p in sources}==sources
                dump(destination/'source_after.json',sources)
                return dict(manifest=preflight,output_dir=destination)

            # Recovery uses the same selected channels/current protection, no sweeps.
            zero_seed = deepcopy(actual)
            zero_seed['qick']['bias_t_compensation']['enabled']=False
            assert actual['qick']['bias_t_compensation']['enabled']
            zero_seed['awg'] = dict(outputs=[dict(time_ns=[0.,10000.],voltage_mv=[0.,0.],
                voltage_bounds_mv=[-s,s],segment_names=['set_0']) for s in scales],cross_capacitance=np.eye(2).tolist(),sweeps=[])
            dump(destination/'zero_gui_input.json',zero_seed)
            window._load_settings_json(destination/'zero_gui_input.json'); app.processEvents()
            zero_args = window._experiment_run_arguments(require_readout=False,require_run_config=False)
            assert zero_args['sequence'].bias_t_compensation is None and zero_args['sequence'].rc_compensation is None
            zero_program = runtime.build_qick_program(cfg,zero_args['sequence'],awg_channels=channels,
                repetitions_per_sweep=1,rf_specs=(),readout_spec=None,tproc_mhz=300.,compile_validation_mode='full')
            zero_program.compile()

            # Optional, explicit paired-DDS idle program. No declare_gen -> no RFDC
            # mixer/Nyquist/current reconfiguration. Only selected shared-DAC DDSs.
            paired = tuple(sorted({rf for row in mapping for rf in row['paired_rf_generators']}))
            idle_program = QickProgram(cfg)
            for index, channel in enumerate(paired):
                idle_program.set_pulse_registers(ch=channel,style='const',freq=0,phase=0,gain=0,
                    length=3,mode='oneshot',stdysel='zero')
                idle_program.pulse(ch=channel,t=100+index*4)
            idle_program.waiti(0,200)
            idle_program.end()
            idle_program.compile()
            assert not idle_program.gen_chs

            models = {}
            for name, compiled in (('sweep',program),('zero_recovery',zero_program),('paired_dds_idle',idle_program)):
                model = TProcV1BehaviorModel(strict=True)
                if hasattr(compiled,'load_runtime_dmem_into_model'):
                    compiled.load_runtime_dmem_into_model(model)
                model.run(compiled,max_steps=10000000)
                assert model.ended and not model.timing_conflicts and not model.unsupported_instructions
                events = [dict(cycle=e.cycle,port=e.tproc_ch,word=f'{e.word:040x}') for e in model.output_events]
                dump(destination/(f'{name}_model.json.gz' if name=='sweep' else f'{name}_model.json'),dict(events=events,ended=True))
                (destination/f'{name}.asm').write_text(compiled.asm(),encoding='utf8')
                (destination/f'{name}.pmem').write_text(''.join(f'{int(w):016x}\n' for w in compiled.binprog),encoding='ascii')
                words = getattr(compiled,'_runtime_dmem_words',())
                base = getattr(compiled,'_runtime_dmem_base',None)
                dump(destination/f'{name}.dmem.json',dict(base=base,words=[int(w) for w in words]))
                models[name] = model

            from qick_dc_area import point_plan
            from qick.dc_area import DC_START_CYCLES, AREA_PIPELINE_CYCLES, DC_ZERO_RESET_CYCLES
            from qick.precompensation import rc_coefficient
            from qick_rc_validation import interval_extrema
            assert program._hardware_dc_area
            dump(destination/'compiler_compensation.json',dict(mode=mode,
                dc_settings=program._hardware_dc_settings,deadline_cycles=program._hardware_dc_deadline,
                validation=program.hardware_dc_validation,rc_validation=program.rc_output_range_validation,
                net_area_bounds=program._hardware_dc_net_bounds,
                note='Planning bounds from current production compiler; not a new scalar RTL execution.'))
            expected=[]; axis_shots=[]; controls=[]
            for axis,(channel,scale) in enumerate(zip(channels,scales)):
                gen=cfg['gens'][channel]
                ev=[e for e in models['sweep'].output_events
                    if e.tproc_ch==gen['tproc_ch'] and (e.word>>152)&255==gen['tmux_ch']]
                dc=[e for e in ev if (e.word>>150)&1 and ((e.word>>146)&3) in (1,2)]
                rc=[e for e in ev if (e.word>>149)&1]
                arm=[e for e in ev if (e.word>>150)&1 and ((e.word>>146)&3)==0]
                assert len(dc)==POINT_COUNT and len(rc)==1 and len(arm)==1
                assert ((rc[0].word>>146)&3)==3 # enable and reset
                assert rc[0].word&0xffffffff==rc_coefficient(tau_us,4800.)
                assert all(((e.word>>146)&3)==(1 if mode=='fixed_voltage' else 2) for e in dc)
                zero_ev=[e for e in models['zero_recovery'].output_events
                    if e.tproc_ch==gen['tproc_ch'] and (e.word>>152)&255==gen['tmux_ch']]
                assert any((e.word>>150)&1 and ((e.word>>146)&3)==3 for e in zero_ev)
                assert any((e.word>>149)&1 and ((e.word>>146)&3)==2 and e.word&0xffffffff==0 for e in zero_ev)
                assert all(e.word&0xffffffff==0 for e in zero_ev if ((e.word>>144)&15) in (1,2))
                raw=[e for e in ev if ((e.word>>144)&15) in (1,2)]
                shots=[]; cursor=0
                first=round(start_mv/scale*8192)*4
                last=round(stop_mv/scale*8192)*4
                delta=int(Fraction(last-first,(AXIS_COUNT-1)*4)+Fraction(1,2))*4
                for point,comp in enumerate(dc):
                    group=[]
                    while cursor<len(raw) and raw[cursor].cycle<comp.cycle:
                        group.append(raw[cursor]);cursor+=1
                    if point==0:
                        assert group[0].word&0xffffffff==0
                        group=group[1:] # initialization zero
                    # Five requested segments, followed by the compiler's mandatory pre-DC zero.
                    assert len(group)==6,(point,len(group))
                    coord=(point//AXIS_COUNT,point%AXIS_COUNT)[axis]
                    target=first+coord*delta
                    decoded=[(e.word&0xffffffff)-(1<<32) if e.word&(1<<31) else e.word&0xffffffff for e in group]
                    assert decoded==[0,target,target,0,0,0]
                    assert [((e.word>>144)&15) for e in group]==[1,2,1,2,1,1]
                    assert ((group[1].word>>64)&((1<<23)-1))==4800
                    assert ((group[3].word>>64)&((1<<23)-1))==4800
                    plan=point_plan(program,point,axis)
                    assert plan['residual']==0
                    assert plan['area']+sum(n*v for n,v in plan['runs'])==0
                    if mode=='fixed_time': assert plan['words']==round(dc_time_us*300)
                    shots.append((group,comp,plan))
                assert cursor==len(raw)
                controls.append(dict(axis=axis,rc_enable_reset_cycle=rc[0].cycle,
                    coefficient=rc[0].word&0xffffffff,dc_arm_cycle=arm[0].cycle,
                    dc_commands=len(dc),rc_commands=len(rc),
                    reset_policy='Hardware DC completion clears area and IIR after final zero; no software per-shot RC command.',
                    cleanup_rc_disabled_reset=True,cleanup_dc_disabled=True))
                axis_shots.append(shots)
            bounds=[]
            for point in range(POINT_COUNT):
                axes=[]
                for axis,(channel,scale) in enumerate(zip(channels,scales)):
                    group,comp,plan=axis_shots[axis][point]
                    hold=group[2];zero=group[4]
                    latency=int(cfg['gens'][channel]['output_latency_cycles'])
                    dc_latency=DC_START_CYCLES+latency-AREA_PIPELINE_CYCLES
                    coeff=rc_coefficient(tau_us,4800.); invtau=2*coeff*4800./(1<<48)
                    intervals=list(plan['intervals'])+[(0.,0.,0.,0.)]
                    intervals.extend((v/8192,v/8192,n/4800.,0.) for n,v in plan['runs'])
                    intervals.append((0.,0.,0.,0.))
                    low,high=interval_extrema(intervals,invtau)
                    peak=max(abs(v) for interval in intervals for v in interval[:2])
                    margin=.5/8192+peak*invtau*(len(intervals)*2/300.+1/4800.)
                    low,high=(low-margin)*scale,(high+margin)*scale
                    assert -scale<low<scale and -scale<high<scale
                    bounds.append((low,high))
                    rawcode=(hold.word&0xffffffff)-(1<<32) if hold.word&(1<<31) else hold.word&0xffffffff
                    commands=[dict(cycle=e.cycle,opcode=(e.word>>144)&15,
                        transport_target=(e.word&0xffffffff)-(1<<32) if e.word&(1<<31) else e.word&0xffffffff,step_signed=((e.word>>96)&0xffffffff)-(1<<32) if (e.word>>127)&1 else (e.word>>96)&0xffffffff,
                        duration_samples=(e.word>>64)&((1<<23)-1),word=f'{e.word:040x}') for e in group]
                    axes.append(dict(**mapping[axis],requested_mv=start_mv+(stop_mv-start_mv)/(AXIS_COUNT-1)*((point//AXIS_COUNT,point%AXIS_COUNT)[axis]),
                        dac_code=rawcode,quantized_mv=rawcode/32768.*scale,
                        hold_command_cycle=hold.cycle,hold_digital_output_us=(hold.cycle+latency)/300.,
                        hold_end_digital_output_us=(hold.cycle+latency+round(hold_us*300))/300.,
                        final_user_zero_digital_output_us=(zero.cycle+latency)/300.,
                        sequence_start_command_us=group[0].cycle/300.,commands=commands,
                        pre_dc_area_effective_code_samples=plan['area'],dc_runs_effective14=list(plan['runs']),
                        dc_command_cycle=comp.cycle,dc_command_word=f'{comp.word:040x}',
                        dc_start_digital_output_us=(comp.cycle+dc_latency)/300.,
                        dc_end_digital_output_us=(comp.cycle+dc_latency+plan['words'])/300.,
                        dc_duration_cycles=plan['words'],dc_duration_us=plan['words']/300.,
                        dc_residual_area=plan['residual'],
                        dc_zero_reset_bound_us=(comp.cycle+dc_latency+plan['words']+DC_ZERO_RESET_CYCLES)/300.,
                        rc_dac_bounds_mv=[low,high],rc_tau_us=tau_us,rc_coefficient=coeff))
                expected.append(dict(point_index=point,axis_indices=[point//AXIS_COUNT,point%AXIS_COUNT],outputs=axes))
            starts=[p['outputs'][0]['hold_command_cycle'] for p in expected]
            spacings=sorted(set(b-a for a,b in zip(starts,starts[1:])))
            final=max(a['dc_zero_reset_bound_us'] for p in expected for a in p['outputs'])
            dump(destination/'expected_points.json.gz',dict(points=expected,identity_matrix=True,axis_count=AXIS_COUNT,point_count=POINT_COUNT,
                requested_range_mv=[start_mv,stop_mv],mode=mode,dc_voltage_mv=dc_voltage_mv if mode=='fixed_voltage' else None,dc_time_us=dc_time_us if mode=='fixed_time' else None,
                rc_tau_us=tau_us,controls=controls,point_spacing_cycles=spacings,
                coordinate_order='axis0 outer, axis1 fastest; see requested_range_mv',
                quantization='constant transport code increments after endpoint and increment rounding; compare exported per-point quantized values',
                reference='Actual compiled TProc commands plus current production hardware DC planning ledger. The command model does not execute scalar area/IIR RTL. RC bounds are planning estimates, not measured analog values.',
                rc_input_reference='For direct DAC measurement compare RC DAC estimate, not a flat nominal plateau. External RC network changes the appropriate physical reference.',
                plateau_duration_us=hold_us,last_output_zero_bound_us=final,
                global_rc_bounds_mv=[min(v[0] for v in bounds),max(v[1] for v in bounds)],
                scope_record_recommendation_ms=math.ceil((final/1000.*1.2)/100)*100,
                hardware_dc_wait_policy='All shots reserve the same conservative worst-case completion slot; fixed-voltage active compensation duration varies by measured area.'))
            dump(destination/'preparation_summary.json',dict(mode=mode,points=POINT_COUNT,
                pmem_words=len(program.binprog),zero_pmem_words=len(zero_program.binprog),idle_pmem_words=len(idle_program.binprog),
                dmem_words=len(getattr(program,'_runtime_dmem_words',())),point_spacing_cycles=spacings,
                final_zero_bound_us=final,global_rc_bounds_mv=[min(v[0] for v in bounds),max(v[1] for v in bounds)],
                hardware_dc_deadline_cycles=program._hardware_dc_deadline,controls=controls,
                requested_range_mv=[start_mv,stop_mv],actual_range_mv=[expected[0]['outputs'][0]['quantized_mv'],expected[-1]['outputs'][0]['quantized_mv']],
                effective_code_area_range=[min(a['pre_dc_area_effective_code_samples'] for p in expected for a in p['outputs']),max(a['pre_dc_area_effective_code_samples'] for p in expected for a in p['outputs'])],
                dc_duration_cycles_range=[min(a['dc_duration_cycles'] for p in expected for a in p['outputs']),max(a['dc_duration_cycles'] for p in expected for a in p['outputs'])]))
            if errors: raise AssertionError(errors)
            assert {p:sha(p) for p in sources}==sources
            dump(destination/'source_after.json',sources)
            manifest=dict(status='offline_prepared',mapping=mapping,points=POINT_COUNT,axis_count=AXIS_COUNT,mode=mode,hold_us=hold_us,dc_time_us=dc_time_us,tau_us=tau_us,dc_voltage_mv=dc_voltage_mv,start_mv=start_mv,stop_mv=stop_mv,
                paired_dds_idle_channels=paired,physical_execution=False,
                production_sources_unchanged=True,board_config_sha256=sha(board_config),
                current_settings_sha256=sha(current_settings),helper_sha256=sha(__file__),
                files={p.name:sha(p) for p in destination.iterdir() if p.is_file()})
            dump(destination/'manifest.json',manifest)
            return dict(program=program,zero_program=zero_program,idle_program=idle_program,
                        soccfg=cfg,manifest=manifest,output_dir=destination)
    except BaseException as exc:
        dump(destination/'preparation_failure.json',dict(status='preparation_rejected',
            error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),
            mode=mode,hold_us=hold_us,dc_time_us=dc_time_us,tau_us=tau_us,start_mv=start_mv,stop_mv=stop_mv,
            dc_voltage_mv=dc_voltage_mv,physical_execution=False,helper_sha256=sha(__file__)))
        raise
    finally:
        if window is not None:
            # Drain scheduled layout callbacks before destroying their targets.
            QtTest.QTest.qWait(100)
            window.close();window.deleteLater()
        if app is not None:
            app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete)
            app.processEvents()
            window=None
            gc.collect()
            QtCore.QTimer.singleShot(0,app.quit);app.exec_();sip.delete(app)
        sys.excepthook=previous_hook


def reconstruct_prepared(directory):
    """Rebuild trusted local artifacts without QApplication or any I/O to a board.

    The returned programs must match the previously GUI-compiled PMEM exactly.
    No source or output file is written. Caller handles timeout, instrument
    setup/restore, verified wiring, and explicit selected-output zero cleanup.
    """
    sys.path.insert(0,str(GUI))
    import qick.sim
    from qick import QickConfig
    from qick.asm_v1 import QickProgram
    from dc_waveform_core import PulseSequence, QickSweepSpec, build_qick_sequence
    import qick_qcodes_experiment as runtime
    directory=Path(directory).resolve()
    manifest=json.loads((directory/'manifest.json').read_text())
    if manifest['status']!='offline_prepared' or manifest['physical_execution']:
        raise ValueError('Not a trusted offline-prepared bundle')
    for name,digest in manifest['files'].items():
        if sha(directory/name)!=digest:
            raise ValueError(f'Prepared artifact changed: {name}')
    sources=json.loads((directory/'source_before.json').read_text())
    for path,digest in sources.items():
        if sha(path)!=digest:
            raise ValueError(f'Production source changed: {path}')
    cfg=QickConfig(json.loads((directory/'board_config_snapshot.json').read_text()))
    channels=tuple(row['awg_gen'] for row in manifest['mapping'])
    scales=tuple(row['full_scale_mv'] for row in manifest['mapping'])
    currents=json.loads((directory/'dac_current_snapshot.json').read_text())
    outputs=tuple(f'awg_{i}' for i in range(2))
    rebuilt={}
    with offline_only():
        for name,filename in (('sweep','gui_input.json'),('zero_recovery','zero_gui_input.json')):
            settings=json.loads((directory/filename).read_text())
            assert tuple(settings['qick']['awg_channels'])==channels
            comp=settings['qick']['bias_t_compensation']
            assert comp['enabled']==(name=='sweep')
            if name=='sweep': assert comp['type']=='dc_rc' and comp['filter_tau_us']==manifest.get('tau_us',100.) and comp['mode']==manifest['mode']
            assert not settings['rf_outputs'] and not settings['rf_readout']['enabled']
            assert not settings['square_pulse']['enabled'] and not settings['output_trigger']['enabled']
            axes=tuple(QickSweepSpec(**{key:axis[key] for key in ('segment_name','output_name','start','stop','count')})
                       for axis in settings['awg']['sweeps'])
            selected_currents={dac:record for dac,record in currents.items()
                               if set(channels).intersection(record['channels'])}
            sequence=build_qick_sequence(tuple(PulseSequence.from_dict(row) for row in settings['awg']['outputs']),
                output_names=outputs,fabric_mhz=300.,full_scale_mv=settings['qick']['full_scale_mv'],
                output_full_scales_mv=scales,dac_current_settings=selected_currents,
                sweeps=axes or None,cross_capacitance=settings['awg']['cross_capacitance'],
                bias_t_compensation_enabled=comp['enabled'],bias_t_compensation_type=comp['type'],
                bias_t_compensation_voltage_mv=comp['voltage_mv'],bias_t_compensation_mode=comp['mode'],
                bias_t_compensation_duration_us=comp['duration_us'],bias_t_filter_tau_us=comp['filter_tau_us'],rf_pulse_specs=())
            program=runtime.build_qick_program(cfg,sequence,awg_channels=channels,
                repetitions_per_sweep=1,rf_specs=(),readout_spec=None,tproc_mhz=300.,compile_validation_mode='full')
            program.compile();rebuilt[name]=program
        idle=QickProgram(cfg)
        for index,channel in enumerate(manifest['paired_dds_idle_channels']):
            idle.set_pulse_registers(ch=channel,style='const',freq=0,phase=0,gain=0,
                length=3,mode='oneshot',stdysel='zero')
            idle.pulse(ch=channel,t=100+index*4)
        idle.waiti(0,200);idle.end();idle.compile();assert not idle.gen_chs
        rebuilt['paired_dds_idle']=idle
        for name,program in rebuilt.items():
            expected=[int(line,16) for line in (directory/f'{name}.pmem').read_text().splitlines()]
            if [int(word) for word in program.binprog]!=expected:
                raise AssertionError(f'Reconstructed {name} PMEM differs from actual GUI preparation')
            expected_dmem=json.loads((directory/f'{name}.dmem.json').read_text())
            if list(map(int,getattr(program,'_runtime_dmem_words',())))!=expected_dmem['words']:
                raise AssertionError(f'Reconstructed {name} DMEM differs')
    return dict(program=rebuilt['sweep'],zero_program=rebuilt['zero_recovery'],
                idle_program=rebuilt['paired_dds_idle'],soccfg=cfg,manifest=manifest,
                expected_points=(json.load(gzip.open(directory/'expected_points.json.gz','rt',encoding='utf8'))
                    if (directory/'expected_points.json.gz').exists() else json.loads((directory/'expected_points.json').read_text())),
                output_dir=directory)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--preflight-only',action='store_true')
    parser.add_argument('--mode',choices=('fixed_voltage','fixed_time'),required=True)
    for flag in ('hold-us','dc-time-us','tau-us','start-mv','stop-mv','dc-voltage-mv'):
        parser.add_argument('--'+flag,type=float,required=True)
    parser.add_argument('--board-config',type=Path,required=True)
    parser.add_argument('--current-settings',type=Path,required=True)
    parser.add_argument('--gen-channels',type=int,nargs=2,required=True)
    parser.add_argument('--full-scales-mv',type=float,nargs=2,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    result=prepare_program(**vars(args))
    print(json.dumps(result['manifest'],indent=2))


if __name__=='__main__':
    main()
