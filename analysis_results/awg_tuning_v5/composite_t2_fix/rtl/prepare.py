"""New GUI host coordinates -> real v4 RTL inputs; no board connection."""
import csv
import gc
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import traceback
from dataclasses import asdict, replace
from types import SimpleNamespace

ROOT = Path('C:/GIT_Workspace/QSTL_QICK')
GUI = ROOT.parent / 'PulseGenerator/DCWaveformGeneratorGUI'
HERE = Path(__file__).resolve().parent
BUILD = Path(os.environ.get('QICK_T2_RTL_BUILD', 'F:/Vivado_Output/a5t2gui1'))
BASE = Path('F:/Vivado_Output/a3sim1/rc_precomp_repeat_reset_hold_duration_2x2_v4_all_20261014_exact10us_hold1_output_sum_awg_v3')
SHARED = Path('F:/Vivado_Output/a3sim1/qstl_gui_rtl_sim.sim/sim_1/behav/xsim')
SCENARIO = os.environ.get('QICK_T2_SCENARIO', 'custom_sweep')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    BUILD.mkdir(exist_ok=False)
    sys.path.insert(0, str(GUI))
    sys.path.insert(0, str(ROOT / 'qick/firmware/ip/axis_output_sum_v1/validation'))
    import qick.sim
    from qick import QickConfig
    from qick.awg_tuning import TProcV1BehaviorModel
    from PyQt5 import QtCore, QtGui, QtWidgets, sip
    import numpy as np
    import DCWaveform_Generator as gui
    import qick_qcodes_experiment as runtime
    from dc_waveform_core import (QickRfCompositeItemSpec, QickRfDurationParameterSpec,
        QickRfPulseSpec, QickRfAmplitudeParameterSpec, QickRfPhaseParameterSpec)
    from qick_fine_tune_sweep import FineTuneDdrResult
    from qick_front_panel import identify_qick_front_panel
    import gui_rtl_extension

    source_files = list(GUI.glob('*.py')) + list((ROOT / 'qick/qick_lib/qick').rglob('*.py'))
    sources = {str(path): sha(path) for path in source_files}
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
    errors = []
    def on_error(kind, value, tb):
        errors.append(''.join(traceback.format_exception(kind, value, tb)))
        traceback.print_exception(kind, value, tb)
    sys.excepthook = on_error
    app = QtWidgets.QApplication([])
    font_id = QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    app.setFont(QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(font_id)[0], 9))
    app.setQuitOnLastWindowClosed(False)
    window = gui.MainWindow()
    data = json.loads((BASE / 'gui_input.json').read_text())
    currents = data['qick']['dac_current_settings']
    window._on_qick_configuration_identified(replace(identify_qick_front_panel(cfg), dac_current_settings=currents))
    rf_specs = []
    calibration_path = BUILD / 'synthetic_known_calibration.db'
    if SCENARIO == 'hahn_calibration':
        # Synthetic known reference, not an instrument measurement. At 190 MHz
        # and zero attenuation, -10 dBm is independently specified as gain3000.
        with sqlite3.connect(calibration_path) as connection:
            connection.executescript('''
                CREATE TABLE experiments (exp_id INTEGER PRIMARY KEY, name TEXT, sample_name TEXT);
                CREATE TABLE runs (run_id INTEGER PRIMARY KEY, exp_id INTEGER, result_table_name TEXT,
                    is_completed INTEGER, Attenuation TEXT, Calibration_Config TEXT);
                CREATE TABLE layouts (layout_id INTEGER PRIMARY KEY, run_id INTEGER, parameter TEXT,
                    label TEXT, unit TEXT, inferred_from TEXT);
                CREATE TABLE reference (id INTEGER PRIMARY KEY, gain REAL, freq REAL, pwr REAL);
                INSERT INTO experiments VALUES (1, 'synthetic known mapping', 'RF_Out_190MHz');
                INSERT INTO runs VALUES (1, 1, 'reference', 1, '{"att1": 0, "att2": 0}', NULL);
                INSERT INTO layouts VALUES (1, 1, 'freq', 'freq', 'MHz', '');
            ''')
            rows = [(gain, frequency, power) for frequency in (180., 190., 200.)
                    for gain, power in ((1500., -16.020599913279625),
                                        (3000., -10.), (6000., -3.979400086720376))]
            connection.executemany('INSERT INTO reference (gain, freq, pwr) VALUES (?, ?, ?)', rows)
            connection.execute('UPDATE runs SET Calibration_Config = ? WHERE run_id = 1',
                (json.dumps({'configuration': {'nqz': 1, 'output_filter_type': 'bypass',
                   'output_filter_cutoff_ghz': 2.5, 'output_filter_bandwidth_ghz': 1.0}}),))
    for channel in (0, 2, 4):
        spec = QickRfPulseSpec(channel, 'set_1', .1, .2, 190., 2000, 0., 0., pulse_mode='composite',
            frequency_parameters=({'name': 'f0', 'frequency_mhz': 190.},),
            duration_parameters=(QickRfDurationParameterSpec('pi', .2, channel == 0, .2, .4, 2),),
            delay_parameters=(QickRfDurationParameterSpec('tau', 1., channel == 0, 1., 3., 3),),
            composite_items=(QickRfCompositeItemSpec('delay', 'tau_a', 1., delay_parameter='tau'),
                QickRfCompositeItemSpec('pulse', 'pi', .2, 'f0', 2000, 0., duration_parameter='pi'),
                QickRfCompositeItemSpec('delay', 'tau_b', 1., delay_parameter='tau')),
            t2_initial_pi2=True, t2_final_pi2=True, t2_duration_parameter='pi',
            t2_frequency_parameter='f0', t2_gain=2000,
            t2_initial_phase_degrees=90., t2_final_phase_degrees=-90.)
        if SCENARIO in ('hahn_manual', 'hahn_calibration'):
            calibrated = SCENARIO == 'hahn_calibration'
            amplitude = -10. if calibrated else 1500.
            body_amplitude = -16.0206 if calibrated else 750.
            phase = 90. if calibrated else 0.
            body_phase = 0. if calibrated else 90.
            spec = replace(spec,
                frequency_parameters=({'name': 'f0', 'frequency_mhz': 70.},
                                      {'name': 'f_all', 'frequency_mhz': 190.}),
                duration_parameters=(QickRfDurationParameterSpec('pi', .4),),
                delay_parameters=(), predefined_template='hahn_echo',
                predefined_n=1, predefined_tau_us=4.,
                predefined_frequency_parameter='f_all', predefined_duration_parameter='pi',
                predefined_gain=1000, global_frequency_parameter='', global_gain=None,
                amplitude_parameters=(QickRfAmplitudeParameterSpec('a0', amplitude,
                    channel == 0, amplitude, amplitude, 1),
                    QickRfAmplitudeParameterSpec('a1', body_amplitude,
                    channel == 0, body_amplitude, body_amplitude, 1)),
                phase_parameters=(QickRfPhaseParameterSpec('p0', phase,
                    channel == 0, phase, phase, 1),
                    QickRfPhaseParameterSpec('p1', body_phase,
                    channel == 0, body_phase, body_phase, 1)),
                global_amplitude_mode='calibration' if calibrated else 'manual',
                global_amplitude_parameter='', predefined_amplitude_parameter='a1',
                predefined_phase_parameter='p1', t2_amplitude_parameter='a0',
                t2_frequency_parameter='f_all',
                t2_initial_phase_parameter='p0', t2_final_phase_parameter='p0',
                global_calibration_database_path=str(calibration_path) if calibrated else '',
                global_calibration_run_id=1 if calibrated else 0)
        elif SCENARIO != 'custom_sweep':
            raise ValueError(f'Unknown scenario: {SCENARIO}')
        rf_specs.append(spec)
    loaded_specs = rf_specs
    if SCENARIO.startswith('hahn_'):
        loaded_specs = [replace(spec, global_amplitude_mode='manual', global_gain=2000,
            global_amplitude_parameter='', amplitude_parameters=(QickRfAmplitudeParameterSpec('a0', 1500.),
                QickRfAmplitudeParameterSpec('a1', 750.))) for spec in rf_specs]
    data['rf_outputs'] = [dict(asdict(spec), enabled=True) for spec in loaded_specs]
    (BUILD / 'gui_input.json').write_text(json.dumps(data, indent=2), encoding='utf8')
    window._load_settings_json(BUILD / 'gui_input.json')
    if SCENARIO.startswith('hahn_'):
        converted = []
        custom_specs = []
        for channel, wanted in zip((0, 2, 4), rf_specs):
            panel = next(panel for panel in window._rf_ports_panel._panels
                         if panel.configured_spec().gen_ch == channel)
            before = panel.configured_spec()
            assert before.predefined_template == 'hahn_echo'
            assert [item.kind for item in before.composite_items] == ['delay', 'pulse', 'delay']
            assert [item.duration_us for item in before.composite_items if item.kind == 'delay'] == [2., 2.]
            panel.predefined_template.setCurrentIndex(panel.predefined_template.findData('custom'))
            app.processEvents()
            after = panel.configured_spec()
            assert after.predefined_template == 'custom'
            assert after.pulse_events == before.pulse_events, 'Hahn -> Custom changed emitted events'
            target = replace(wanted, predefined_template='custom')
            panel.load_settings(dict(asdict(target), enabled=True))
            app.processEvents()
            custom_specs.append(target)
            converted.append(dict(before=asdict(before), after=asdict(after), requested_custom=asdict(target)))
        rf_specs = custom_specs
        (BUILD / 'hahn_to_custom_gui.json').write_text(json.dumps(converted, indent=2))
        (BUILD / 'custom_requested_rf_specs.json').write_text(json.dumps([asdict(spec) for spec in custom_specs], indent=2))
    args = window._experiment_run_arguments(require_readout=False, require_run_config=False)
    actual_specs = tuple(args['rf_specs'])
    (BUILD / 'gui_runtime_specs.json').write_text(json.dumps([asdict(spec) for spec in actual_specs], indent=2))
    changes = [{key: [asdict(requested)[key], asdict(actual)[key]]
                for key in asdict(requested) if asdict(requested)[key] != asdict(actual)[key]}
               for requested, actual in zip(rf_specs, actual_specs)]
    (BUILD / 'gui_normalization.json').write_text(json.dumps(changes, indent=2))
    assert len(actual_specs) == len(rf_specs)
    for actual, requested in zip(actual_specs, rf_specs):
        assert actual.pulse_events == requested.pulse_events, 'GUI changed requested RF events'
        assert actual.software_sweep_axes == requested.software_sweep_axes, 'GUI changed host sweep axes'
        assert actual.sweep_axes == requested.sweep_axes, 'GUI changed hardware sweep axes'
    assert not args['sequence'].sweep_axes, 'This fixture expects host axes only'
    window.resize(1600, 1000)
    window.show()
    app.processEvents()
    window.grab().save(str(BUILD / 'gui_input.png'))
    cases = []

    def compile_point(_soc, _cfg, sequence, **kwargs):
        point = len(cases)
        out = BUILD / f'point_{point}'
        out.mkdir()
        specs = kwargs['rf_specs']
        assert all(not spec.software_sweep_axes for spec in specs)
        program = runtime.build_qick_program(cfg, sequence, awg_channels=kwargs['awg_channels'],
            repetitions_per_sweep=kwargs['repetitions_per_sweep'], rf_specs=specs,
            readout_spec=kwargs['readout_spec'], tproc_mhz=300., compile_validation_mode='boundary')
        program.compile()
        runtime_pulses = runtime.build_runtime_rf_pulses(cfg, specs, tproc_mhz=300.)
        (out / 'runtime_rf_pulses.json').write_text(json.dumps([asdict(pulse) for pulse in runtime_pulses], indent=2))
        if SCENARIO.startswith('hahn_'):
            wanted_gains = [3000, 1500, 3000] if SCENARIO == 'hahn_calibration' else [1500, 750, 1500]
            wanted_phases = [90., 0., 90.] if SCENARIO == 'hahn_calibration' else [0., 90., 0.]
            assert len(runtime_pulses) == 9
            assert [pulse.gain for pulse in runtime_pulses] == wanted_gains * 3
            assert [pulse.phase_degrees for pulse in runtime_pulses] == wanted_phases * 3
            assert all(pulse.freq_mhz == 190. for pulse in runtime_pulses)
        (out / 'pmem.hex').write_text(''.join(f'{int(word):016x}\n' for word in program.binprog))
        (out / 'program.asm').write_text(program.asm())
        (out / 'dmem.txt').write_text(''.join(f'{program._runtime_dmem_base+i:08x} {int(word)&0xffffffff:08x}\n'
            for i, word in enumerate(program._runtime_dmem_words)))
        (out / 'rf_specs.json').write_text(json.dumps([asdict(spec) for spec in specs], indent=2))
        model = TProcV1BehaviorModel(strict=True)
        program.load_runtime_dmem_into_model(model)
        model.run(program, max_steps=100000)
        assert not model.timing_conflicts
        events = [dict(cycle=e.cycle, port=e.tproc_ch, word=f'{e.word:040x}') for e in model.output_events]
        events += [dict(cycle=e['cycle'], port=e['port'], word=f'{e["word"]:040x}') for e in model.output_pin_events]
        cycles = max(event['cycle'] for event in events) + 2000
        (out / 'expected.json').write_text(json.dumps(dict(events=events, cycles=cycles), indent=2))
        case = dict(folder=str(out), cycles=cycles, shots=2,
            tau_us=(specs[0].predefined_tau_us if SCENARIO.startswith('hahn_')
                    else specs[0].delay_parameters[0].duration_us),
            pi_us=specs[0].duration_parameters[0].duration_us,
            rf_events=[[asdict(event) for event in spec.pulse_events] for spec in specs],
            expected_runtime_gains=([3000, 1500, 3000] if SCENARIO == 'hahn_calibration' else
                                    [1500, 750, 1500] if SCENARIO == 'hahn_manual' else [2000]*3),
            inputs={name: sha(out / name) for name in ('pmem.hex', 'dmem.txt')})
        cases.append(case)
        result = FineTuneDdrResult(np.asarray([0.]), np.zeros((1, 2, 1, 2), dtype=np.int32),
                                  reserved_physical_words=128, sweep_axes=(), sweep_shape=(1,))
        return program, result, {'outputs': []}

    original = runtime._execute_qick_sequence_once
    runtime._execute_qick_sequence_once = compile_point
    calibration_rejections = []
    try:
        if SCENARIO == 'hahn_calibration':
            for spec in actual_specs:
                try:
                    runtime.build_runtime_rf_pulses(cfg, (spec,), tproc_mhz=300.)
                except ValueError as exc:
                    assert 'RF connector power calibration cannot be used' in str(exc)
                    calibration_rejections.append(dict(gen_ch=spec.gen_ch, error=str(exc)))
                else:
                    raise AssertionError('Summed-output calibration guard did not reject')
        try:
            runtime.execute_qick_sequence(None, cfg, args['sequence'],
                awg_channels=args['awg_channels'], repetitions_per_sweep=args['repetitions_per_sweep'],
                rf_specs=args['rf_specs'], readout_spec=args['readout_spec'], tproc_mhz=300.,
                sequence_fabric_mhz=300., compile_validation_mode='boundary')
        except ValueError as exc:
            if SCENARIO != 'hahn_calibration' or 'RF connector power calibration cannot be used' not in str(exc):
                raise
            calibration_rejections.append(dict(stage='actual Run Experiment runtime host loop', error=str(exc)))
    finally:
        runtime._execute_qick_sequence_once = original
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
        app.processEvents()
        del window
        gc.collect()
        QtCore.QTimer.singleShot(0, app.quit)
        app.exec_()
        sip.delete(app)
    assert not errors, errors
    if SCENARIO == 'hahn_calibration':
        assert len(calibration_rejections) == 4 and not cases
        report = dict(passed=True, expected_rejection=True, build=str(BUILD),
            errors=calibration_rejections, source_hashes=sources,
            helper_sha256=sha(__file__), simulation_run=False, board_access=False,
            reason='RF connector calibration is unsupported on summed AWG physical outputs; production guard preserved')
        (HERE / 'calibration_guard.json').write_text(json.dumps(report, indent=2))
        print('PASS expected calibration rejection: all3summedpaths and actualGUI runtime; no RTL cal run', flush=True)
        return
    assert len(cases) == (1 if SCENARIO.startswith('hahn_') else 6)
    template = BUILD / 'template'
    template.mkdir()
    for name in ('rc_bd.v', 'rc_wrapper.v', 'tb_rc_gui.sv', 'sources.prj'):
        text = (BASE / name).read_text().replace(BASE.as_posix(), template.as_posix())
        (template / name).write_text(text)
    for path in BASE.glob('planned_area_*.hex'):
        shutil.copy2(path, template / path.name)
    if not os.environ.get('QICK_T2_COMPILE_ONLY'):
        sim = BUILD / 'sim'
        (sim / 'xsim.dir').mkdir(parents=True)
        shutil.copytree(SHARED / 'xsim.dir/xil_defaultlib', sim / 'xsim.dir/xil_defaultlib')
        shutil.copy2(SHARED / 'xsim.ini', sim / 'xsim.ini')
    libs = list(dict.fromkeys(re.findall(r'-L (\w+)', (SHARED / 'elaborate.bat').read_text())))
    rtl_sources = {path: sha(path) for path in re.findall(r'"([^"]+)"', (template / 'sources.prj').read_text())}
    report = dict(build=str(BUILD), cases=cases, libraries=libs,
        scenario=SCENARIO,
        source_hashes=sources, rtl_source_hashes=rtl_sources, helper_sha256=sha(__file__),
        gui_input_sha256=sha(BUILD / 'gui_input.json'),
        flow='actual MainWindow -> _experiment_run_arguments -> execute_qick_sequence host coordinates -> real QICK compiler',
        board_access=False, rtl_version='existing v4', shared_library_writes=False)
    (BUILD / 'prepared.json').write_text(json.dumps(report, indent=2))
    (HERE / os.environ.get('QICK_T2_PREPARED_NAME', 'prepared.json')).write_text(json.dumps(report, indent=2))
    print(f'PREPARED {len(cases)} GUI coordinates ({SCENARIO}) in {BUILD}', flush=True)


if __name__ == '__main__':
    try:
        main()
    finally:
        # A failed input/preflight assertion must preserve its original error
        # without an unrelated Qt shutdown access violation.
        from PyQt5 import QtCore, QtWidgets, sip
        remaining_app = QtWidgets.QApplication.instance()
        if remaining_app is not None:
            for remaining_window in remaining_app.topLevelWidgets():
                remaining_window.close()
                remaining_window.deleteLater()
            remaining_app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
            remaining_app.processEvents()
            QtCore.QTimer.singleShot(0, remaining_app.quit)
            remaining_app.exec_()
            sip.delete(remaining_app)
