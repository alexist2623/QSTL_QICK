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
                    full_scales_mv, output_dir):
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
        if scale <= 400.:
            raise ValueError('400 mV endpoint needs headroom below full scale')
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
            times = [0., 10000., 11000., 1011000., 1012000., 1022000.]
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
                        for editor, value in ((dialog.start,0.),(dialog.stop,400.),(dialog.count,3)):
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
            actual = window._settings_to_dict()
            dump(destination/'gui_input.json', actual)
            assert window.grab().save(str(destination/'gui.png'))
            args = window._experiment_run_arguments(require_readout=False,require_run_config=False)
            sequence = args['sequence']
            assert args['readout_spec'] is None and not args['rf_specs']
            assert tuple(args['awg_channels']) == channels and sequence.sweep_point_count == 9
            assert sequence.bias_t_compensation is None and sequence.rc_compensation is None
            np.testing.assert_array_equal(sequence.cross_capacitance,np.eye(2))
            np.testing.assert_allclose(sequence.output_full_scales_mv,scales,rtol=0,atol=1e-9)
            assert [s.kind for s in sequence.segments] == ['set','ramp','set','ramp','set']
            assert [s.duration_cycles for s in sequence.segments] == [3000,300,300000,300,3000]
            dump(destination/'gui_arguments.json', dict(awg_channels=channels,repetitions_per_sweep=1,
                readout_spec=None,rf_specs=[],sequence_recipe=runtime.build_awg_waveform_recipe(
                    sequence,fabric_mhz=300.,full_scale_mv=window._qick_full_scale_mv),
                scope='MainWindow input -> argument builder -> compiler -> scope-only program.run; NO RunWorker/ADC/DDR/QCoDeS execution'))
            program = runtime.build_qick_program(cfg,sequence,awg_channels=channels,
                repetitions_per_sweep=1,rf_specs=(),readout_spec=None,tproc_mhz=300.,compile_validation_mode='full')
            program.compile()

            # Recovery uses the same selected channels/current protection, no sweeps.
            zero_seed = dict(actual)
            zero_seed['awg'] = dict(outputs=[dict(time_ns=[0.,10000.],voltage_mv=[0.,0.],
                voltage_bounds_mv=[-s,s],segment_names=['set_0']) for s in scales],cross_capacitance=np.eye(2).tolist(),sweeps=[])
            dump(destination/'zero_gui_input.json',zero_seed)
            window._load_settings_json(destination/'zero_gui_input.json'); app.processEvents()
            zero_args = window._experiment_run_arguments(require_readout=False,require_run_config=False)
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
                model.run(compiled,max_steps=1000000)
                assert model.ended and not model.timing_conflicts and not model.unsupported_instructions
                events = [dict(cycle=e.cycle,port=e.tproc_ch,word=f'{e.word:040x}') for e in model.output_events]
                dump(destination/f'{name}_model.json',dict(events=events,ended=True))
                (destination/f'{name}.asm').write_text(compiled.asm(),encoding='utf8')
                (destination/f'{name}.pmem').write_text(''.join(f'{int(w):016x}\n' for w in compiled.binprog),encoding='ascii')
                words = getattr(compiled,'_runtime_dmem_words',())
                base = getattr(compiled,'_runtime_dmem_base',None)
                dump(destination/f'{name}.dmem.json',dict(base=base,words=[int(w) for w in words]))
                models[name] = model

            expected = []
            per_axis = []
            for axis,(channel,scale) in enumerate(zip(channels,scales)):
                gen = cfg['gens'][channel]
                events = [e for e in models['sweep'].output_events
                          if e.tproc_ch == gen['tproc_ch'] and (e.word>>152)&255 == gen['tmux_ch']
                          and (e.word>>144)&15 in (1,2)]
                assert len(events)==46 and events[0].word&0xffffffff==0
                events=events[1:]
                first=0; last=round(400./scale*8192)*4
                delta=round((last-first)/2/4)*4
                for point in range(9):
                    shot=events[point*5:(point+1)*5]
                    coordinate=(point//3,point%3)[axis]
                    target=first+coordinate*delta
                    assert [e.word&0xffffffff for e in shot]==[0,target,target,0,0]
                    assert ((shot[1].word>>64)&((1<<23)-1))==4800
                    assert ((shot[3].word>>64)&((1<<23)-1))==4800
                zeros=[e for e in models['zero_recovery'].output_events if e.tproc_ch==gen['tproc_ch'] and (e.word>>152)&255==gen['tmux_ch'] and (e.word>>144)&15 in(1,2)]
                assert zeros and all(e.word&0xffffffff==0 for e in zeros)
                per_axis.append(events)
            for point in range(9):
                axes=[]
                for axis,(channel,scale) in enumerate(zip(channels,scales)):
                    shot=per_axis[axis][point*5:(point+1)*5]
                    hold=shot[2]; zero=shot[4]
                    latency=int(cfg['gens'][channel]['output_latency_cycles'])
                    code=hold.word&0xffffffff
                    axes.append(dict(**mapping[axis],requested_mv=200.*((point//3,point%3)[axis]),
                        dac_code=code,quantized_mv=code/32768.*scale,
                        hold_command_cycle=hold.cycle,hold_digital_output_us=(hold.cycle+latency)/300.,
                        hold_end_digital_output_us=(hold.cycle+latency+300000)/300.,
                        final_zero_digital_output_us=(zero.cycle+latency)/300.,
                        sequence_start_command_us=shot[0].cycle/300.))
                expected.append(dict(point_index=point,axis_indices=[point//3,point%3],outputs=axes))
            dump(destination/'expected_points.json',dict(points=expected,identity_matrix=True,
                reference='Digital output estimate from actual compiled command cycles plus HWH latency; analog latency is not asserted.',
                plateau_duration_us=1000.,scope_record_recommendation_ms=12.,
                last_output_zero_us=max(a['final_zero_digital_output_us'] for p in expected for a in p['outputs'])))
            if errors: raise AssertionError(errors)
            assert {p:sha(p) for p in sources}==sources
            dump(destination/'source_after.json',sources)
            manifest=dict(status='offline_prepared',mapping=mapping,points=9,
                paired_dds_idle_channels=paired,physical_execution=False,
                production_sources_unchanged=True,board_config_sha256=sha(board_config),
                current_settings_sha256=sha(current_settings),helper_sha256=sha(__file__),
                files={p.name:sha(p) for p in destination.iterdir() if p.is_file()})
            dump(destination/'manifest.json',manifest)
            return dict(program=program,zero_program=zero_program,idle_program=idle_program,
                        soccfg=cfg,manifest=manifest,output_dir=destination)
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


def main():
    parser=argparse.ArgumentParser()
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
