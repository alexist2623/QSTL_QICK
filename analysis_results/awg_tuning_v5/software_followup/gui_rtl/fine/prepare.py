"""Actual staged GUI -> PMEM/DMEM/envelopes; preparation only, no simulator/board."""
from dataclasses import asdict, replace
import gc
import json
import os
from pathlib import Path
import sys
import traceback

from harness import BASE, ROOT, prepare as prepare_harness, sha

HERE = Path(__file__).resolve().parent
GUI = Path(os.environ.get('QICK_FINE_GUI', 'C:\\GIT_Workspace\\PulseGenerator\\DCWaveformGeneratorGUI'))
BUILD = Path(os.environ.get('QICK_FINE_RTL_BUILD', 'F:/Vivado_Output/a5post_fine_rtl1'))


def pack_envelopes(program, output):
    import numpy as np
    loaded = {}
    for channel in (0, 2, 4):
        envs = program.envelopes[channel]['envs']
        length = max((entry['addr'] + len(entry['data']) for entry in envs.values()), default=0)
        assert length <= 16384
        data = np.zeros((length, 2), dtype=np.int16)
        for entry in envs.values():
            data[entry['addr']:entry['addr']+len(entry['data'])] = entry['data']
        words = [(int(i)&65535) | ((int(q)&65535)<<16) for i, q in data]
        path = output / f'envelope_{channel}.hex'
        path.write_text(''.join(f'{word:08x}\n' for word in words))
        loaded[channel] = dict(samples=length, sha256=sha(path),
                               envelopes={name: dict(addr=e['addr'], samples=len(e['data']))
                                          for name, e in envs.items()})
    return loaded


def expected_bursts(program, specs, model, repetitions):
    """Independent requested sample counts, with actual compiler command time.

    This does not use ending_patterns, plan_duration, or fine point-table rows.
    The RTL command stream is separately compared against the tProc model.
    """
    import numpy as np
    from qick_fine_tune_sweep import RfDurationSweep, RfFrequencySweep
    expected = {spec.gen_ch: [] for spec in specs}
    axes = program.sequence.sweep_axes
    shape = program.sequence.sweep_shape
    for point in range(program.sequence.sweep_point_count):
        coordinate = np.unravel_index(point, shape)
        for repetition in range(repetitions):
            for spec in specs:
                for event in spec.pulse_events:
                    duration, frequency = event.duration_us, event.frequency_mhz
                    for index, axis in enumerate(axes):
                        if not hasattr(axis, 'gen_ch') or axis.gen_ch != spec.gen_ch:
                            continue
                        if isinstance(axis, RfDurationSweep) and axis.parameter_name == event.duration_parameter:
                            duration = axis.points[coordinate[index]]
                        if isinstance(axis, RfFrequencySweep) and axis.parameter_name == event.frequency_parameter:
                            frequency = axis.points[coordinate[index]]
                    samples = round(duration * 4800.)
                    assert abs(duration*4800.-samples) < 1e-5, (duration, samples)
                    expected[spec.gen_ch].append(dict(point=point, repetition=repetition,
                        name=event.name, samples=samples, frequency_mhz=frequency,
                        gain=event.gain, phase_degrees=event.phase_degrees))
    for channel, bursts in expected.items():
        port = int(program.soccfg['gens'][channel]['tproc_ch'])
        # Real hardware shares each RF/AWG pair's tProc port through TMUX.
        tmux = int(program.soccfg['gens'][channel]['tmux_ch'])
        commands = [e for e in model.output_events if e.tproc_ch == port
                    and ((e.word >> 152) & 255) == tmux]
        cursor = 0
        for burst in bursts:
            command = commands[cursor]
            burst['command_cycle'] = command.cycle
            burst['frequency_register'] = command.word & 0xffffffff
            burst['phase_register'] = (command.word >> 32) & 0xffffffff
            assert burst['frequency_register'] == (round(burst['frequency_mhz']*2**32/4800.) & 0xffffffff), burst
            assert burst['phase_register'] == (round(burst['phase_degrees']*2**32/360.) & 0xffffffff), burst
            assert not ((command.word >> 148) & 1), 'Absolute DDS phase must retain phrst=0'
            assert ((command.word >> 147) & 1) == 1, 'RF must return to zero'
            cursor += 1 if burst['samples'] < 96 else 2
        assert cursor == len(commands), (channel, cursor, len(commands))
    return expected


def main():
    BUILD.mkdir(exist_ok=False)
    sys.path.insert(0, str(GUI))
    sys.path.insert(0, str(ROOT / 'qick/firmware/ip/axis_output_sum_v1/validation'))
    import qick.sim
    from qick import QickConfig
    from qick.awg_tuning import TProcV1BehaviorModel
    from PyQt5 import QtCore, QtGui, QtWidgets, sip
    import DCWaveform_Generator as gui
    import qick_qcodes_experiment as runtime
    from dc_waveform_core import (QickRfCompositeItemSpec, QickRfDurationParameterSpec,
                                  QickRfFrequencyParameterSpec, QickRfPulseSpec)
    from qick_front_panel import identify_qick_front_panel
    sys.path.insert(0,str(HERE.parent))
    import extension_v5 as gui_rtl_extension

    sources = {str(p): sha(p) for p in list(GUI.glob('*.py')) +
               list((ROOT / 'qick/qick_lib/qick').rglob('*.py'))}
    cfg = QickConfig(json.loads((ROOT / 'qick/firmware/projects/qstl_gui_rtl_sim/soccfg.json').read_text()))
    for gen in cfg['gens']:
        if gen['type'] in ('axis_awg_tuning_v1', 'axis_square_pulse_v1'):
            gen.update(rc_precomp_version=1, output_latency_cycles=11)
        if gen['type'] == 'axis_square_pulse_v1':
            gen['command_latency_cycles'] = 15
        if gen['type'] == 'axis_awg_tuning_v1':
            gen.update(type='axis_awg_tuning_v3', frac=18, step_width=32,
                       dc_area_version=1, dc_area_bits=48, output_latency_cycles=16, dc_start_cycles=17)
    gui_rtl_extension.configure(cfg)
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QtGui.QFont('Segoe UI', 9))
    errors = []
    def on_error(kind, value, tb):
        errors.append(''.join(traceback.format_exception(kind, value, tb)))
        traceback.print_exception(kind, value, tb)
    sys.excepthook = on_error
    base = json.loads((BASE / 'gui_input.json').read_text())
    cases = []
    # Each RF/AWG pair separately traverses all 16 remainders and 95/96.
    # Only one duration/frequency pair sweeps per fixture, avoiding accidental
    # 32**3 Cartesian expansion while still driving all three RF/AWG pairs.
    fixtures = [(f'remainders_ch{channel}', channel, 81, 112, 32, (0., 190.), 4000)
                for channel in (0, 2, 4)]
    fixtures += [('composite_short',None,1,97,1,(0.,),4000),
                 ('short_1_to_31',None,1,31,1,(0.,),4000),
                 ('short_carrier_1_to_31',None,49,4801,1,(0.,),4000),
                 ('phase_offsets',None,4801,4801,1,(0.,),4000),
                 ('long_pair',None,48001,480001,1,(0.,),4000),
                 ('long_periodic',None,1440001,1440033,1,(0.,),4000)]
    fixtures += [(f'fixed_{samples}', None, samples, samples, 1, (0.,), gain)
                 for samples, gain in [(1,4000),(15,4000),(16,4000),(17,4000),
                    (47,4000),(48,4000),(49,4000),(95,4000),(96,4000),(97,4000),
                    (48001,4000),(480001,4000),
                    (1440001,4000),(1440017,4000),(1440033,4000),
                    (97,-4000),(97,16383)]]
    # A gain suffix prevents fixed97 positive/negative/boundary evidence collisions.
    fixtures = [(f'{name}_gain{gain}', active, first, last, count, frequencies, gain)
                for name, active, first, last, count, frequencies, gain in fixtures]
    if os.environ.get('QICK_FINE_SMOKE'):
        fixtures = [fixture for fixture in fixtures if fixture[1] is None and
                    fixture[2] in (1,15,16,17,95,96,97) and fixture[-1] == 4000]
    if os.environ.get('QICK_FINE_SCENARIO') == 'compact':
        fixtures = [fixture for fixture in fixtures if fixture[0].startswith(('composite_short','phase_offsets'))]
    if os.environ.get('QICK_FINE_SCENARIO') == 'full':
        fixtures = [fixture for fixture in fixtures if fixture[0].startswith(('remainders','long_pair','long_periodic'))]
    if os.environ.get('QICK_FINE_SCENARIO') == 'short_all':
        fixtures = [fixture for fixture in fixtures if fixture[0].startswith('short_1_to_31')]
    if os.environ.get('QICK_FINE_SCENARIO') == 'short_carrier':
        fixtures = [fixture for fixture in fixtures if fixture[0].startswith('short_carrier_1_to_31')]
    if os.environ.get('QICK_FINE_SCENARIO') == 'verification':
        fixtures = [fixture for fixture in fixtures if fixture[0].startswith(
            ('composite_short','phase_offsets','remainders','long_pair','long_periodic',
             'short_1_to_31','short_carrier_1_to_31'))]
    if os.environ.get('QICK_FINE_SCENARIO')=='v5':
        fixtures=[f for f in fixtures if f[0].startswith(('remainders','short_1_to_31','short_carrier_1_to_31'))]
    try:
        for name, active, first, last, count, frequencies, gain in fixtures:
            output = BUILD / name
            output.mkdir()
            data = json.loads(json.dumps(base))
            hold_ns = max(1000., (last/4800.+.3)*1000.)
            if name.startswith(('composite_short','phase_offsets')):
                hold_ns = 5000.
            if name.startswith('short_1_to_31'):
                hold_ns = 10000.
            if name.startswith('short_carrier_1_to_31'):
                hold_ns = 12000.
            if name.startswith('long_pair'):
                hold_ns = 111000.
            for awg in data['awg']['outputs']:
                awg['time_ns'] = [0., 100., 200., 200.+hold_ns, 300.+hold_ns, 400.+hold_ns]
            data['qick']['bias_t_compensation']['enabled'] = False
            specs = []
            for channel in (0,2,4):
                swept = channel == active
                n = first if active is None or swept else 97
                if name.startswith('long_periodic'):
                    n = 1440001 + 16*(channel//2)
                spec = QickRfPulseSpec(channel, 'set_1', .1, n/4800., 0., gain, 0., 0.,
                    pulse_mode='composite', fine_duration=True,
                    frequency_parameters=(QickRfFrequencyParameterSpec('f0', 0.,
                        swept and len(frequencies)>1, frequencies[0], frequencies[-1], len(frequencies)),),
                    duration_parameters=(QickRfDurationParameterSpec('d0', n/4800.,
                        swept, first/4800., last/4800., count),),
                    composite_items=(QickRfCompositeItemSpec('pulse','rf',n/4800.,
                        'f0',gain,0.,duration_parameter='d0'),))
                if name.startswith(('composite_short','phase_offsets','long_pair','short_1_to_31','short_carrier_1_to_31')):
                    requested = ([(value,4000,0.,'f0') for value in (1,15,16,17,47,48,49,95,97)]
                                 + [(97,-4000,0.,'f0'),(97,16383,0.,'f0')]
                                 if name.startswith('composite_short') else
                                 [(49,4000,0.,'f0'),(4801,4000,0.,'f1'),
                                  (4801,4000,37.,'f1'),(4801,4000,-63.,'f1')])
                    if name.startswith('long_pair'):
                        requested = [(48001,4000,0.,'f0'),(480001,4000,0.,'f0')]
                    if name.startswith('short_1_to_31'):
                        requested = [(samples,4000,0.,'f0') for samples in range(1,32)]
                    if name.startswith('short_carrier_1_to_31'):
                        requested = [(49,4000,0.,'f0'),(4801,4000,37.,'f1')]
                        requested += [(samples,4000,37.,'f1') for samples in range(1,32)]
                    items = []
                    durations = []
                    for item_index,(samples,item_gain,phase,freq_name) in enumerate(requested):
                        parameter = f'd{item_index}'
                        durations.append(QickRfDurationParameterSpec(parameter,samples/4800.))
                        items.append(QickRfCompositeItemSpec('pulse',f'rf_{item_index}',samples/4800.,
                            freq_name,item_gain,phase,duration_parameter=parameter))
                        gap = .25 if name.startswith(('short_1_to_31','short_carrier_1_to_31')) else .1
                        items.append(QickRfCompositeItemSpec('delay',f'gap_{item_index}',gap))
                    spec = replace(spec,frequency_parameters=(QickRfFrequencyParameterSpec('f0',0.),
                        QickRfFrequencyParameterSpec('f1',190.)),duration_parameters=tuple(durations),
                        composite_items=tuple(items))
                specs.append(spec)
            data['rf_outputs'] = [dict(asdict(spec), enabled=True) for spec in specs]
            input_path = output / 'gui_input.json'
            input_path.write_text(json.dumps(data, indent=2))
            window = gui.MainWindow()
            window._on_qick_configuration_identified(replace(identify_qick_front_panel(cfg),
                dac_current_settings=data['qick']['dac_current_settings']))
            window._load_settings_json(input_path)
            app.processEvents()
            args = window._experiment_run_arguments(require_readout=False, require_run_config=False)
            actual = tuple(args['rf_specs'])
            assert len(actual) == 3 and all(spec.fine_duration for spec in actual)
            for wanted, found in zip(specs, actual):
                for e1, e2 in zip(wanted.pulse_events, found.pulse_events):
                    assert round(e1.duration_us*4800.) == round(e2.duration_us*4800.), (e1,e2)
                assert len(found.sweep_axes) == len(wanted.sweep_axes)
                for a,b in zip(found.sweep_axes,wanted.sweep_axes):
                    assert (a.axis_kind,a.parameter_name,a.count) == (b.axis_kind,b.parameter_name,b.count)
                    if a.axis_kind == 'rf_duration':
                        assert (round(a.start*4800.),round(a.stop*4800.)) == (round(b.start*4800.),round(b.stop*4800.))
                    else:
                        assert (a.start,a.stop) == (b.start,b.stop)
            (output / 'gui_runtime_specs.json').write_text(json.dumps([asdict(s) for s in actual], indent=2))
            program = runtime.build_qick_program(cfg, args['sequence'],
                awg_channels=args['awg_channels'], repetitions_per_sweep=2,
                rf_specs=actual, readout_spec=args['readout_spec'],
                tproc_mhz=300., compile_validation_mode='boundary')
            program.compile()
            (output / 'pmem.hex').write_text(''.join(f'{int(word):016x}\n' for word in program.binprog))
            (output / 'program.asm').write_text(program.asm())
            (output / 'dmem.txt').write_text(''.join(f'{program._runtime_dmem_base+i:08x} {int(word)&0xffffffff:08x}\n'
                for i, word in enumerate(program._runtime_dmem_words)))
            envelope_info = pack_envelopes(program, output)
            model = TProcV1BehaviorModel(strict=True)
            program.load_runtime_dmem_into_model(model)
            model.run(program, max_steps=1000000)
            assert not model.timing_conflicts, model.timing_conflicts
            events = [dict(cycle=e.cycle, port=e.tproc_ch, word=f'{e.word:040x}') for e in model.output_events]
            events += [dict(cycle=e['cycle'], port=e['port'], word=f'{e["word"]:040x}') for e in model.output_pin_events]
            bursts = expected_bursts(program, actual, model, 2)
            cycles = max(e['cycle'] for e in events) + 2000
            (output / 'expected.json').write_text(json.dumps(dict(events=events, bursts=bursts), indent=2))
            cases.append(dict(name=name, folder=str(output), cycles=cycles, expected_bursts=bursts,
                envelopes=envelope_info, sweep_shape=program.sequence.sweep_shape,
                points=program.sequence.sweep_point_count, repetitions=2,
                inputs={p.name:sha(p) for p in output.iterdir() if p.is_file()}))
            print(f'PREPARED {name} points={program.sequence.sweep_point_count} cycles={cycles}', flush=True)
            window.close();window.deleteLater()
            app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete);app.processEvents()
            del window
            gc.collect()
        assert not errors, errors
        info = prepare_harness(BUILD, copy_libraries=False)
        report = dict(build=str(BUILD), cases=cases, source_hashes=sources,
            helper_sha256=sha(__file__), flow='actual staged MainWindow -> experiment arguments -> actual QICK compiler',
            **info)
        (BUILD/'prepared.json').write_text(json.dumps(report, indent=2))
        (HERE/'prepared.json').write_text(json.dumps(report, indent=2))
    finally:
        for window in app.topLevelWidgets():
            window.close();window.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete);app.processEvents()
        QtCore.QTimer.singleShot(0, app.quit);app.exec_();sip.delete(app)


if __name__ == '__main__':
    main()
