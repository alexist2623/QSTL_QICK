"""New GUI host coordinates -> real v4 RTL inputs; no board connection."""
import csv
import gc
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
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
    from dc_waveform_core import QickRfCompositeItemSpec, QickRfDurationParameterSpec, QickRfPulseSpec
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
        rf_specs.append(spec)
    data['rf_outputs'] = [dict(asdict(spec), enabled=True) for spec in rf_specs]
    (BUILD / 'gui_input.json').write_text(json.dumps(data, indent=2), encoding='utf8')
    window._load_settings_json(BUILD / 'gui_input.json')
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
            tau_us=specs[0].delay_parameters[0].duration_us,
            pi_us=specs[0].duration_parameters[0].duration_us,
            rf_events=[[asdict(event) for event in spec.pulse_events] for spec in specs],
            inputs={name: sha(out / name) for name in ('pmem.hex', 'dmem.txt')})
        cases.append(case)
        result = FineTuneDdrResult(np.asarray([0.]), np.zeros((1, 2, 1, 2), dtype=np.int32),
                                  reserved_physical_words=128, sweep_axes=(), sweep_shape=(1,))
        return program, result, {'outputs': []}

    original = runtime._execute_qick_sequence_once
    runtime._execute_qick_sequence_once = compile_point
    try:
        runtime.execute_qick_sequence(None, cfg, args['sequence'],
            awg_channels=args['awg_channels'], repetitions_per_sweep=args['repetitions_per_sweep'],
            rf_specs=args['rf_specs'], readout_spec=args['readout_spec'], tproc_mhz=300.,
            sequence_fabric_mhz=300., compile_validation_mode='boundary')
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
    assert len(cases) == 6
    template = BUILD / 'template'
    template.mkdir()
    for name in ('rc_bd.v', 'rc_wrapper.v', 'tb_rc_gui.sv', 'sources.prj'):
        text = (BASE / name).read_text().replace(BASE.as_posix(), template.as_posix())
        (template / name).write_text(text)
    for path in BASE.glob('planned_area_*.hex'):
        shutil.copy2(path, template / path.name)
    sim = BUILD / 'sim'
    (sim / 'xsim.dir').mkdir(parents=True)
    shutil.copytree(SHARED / 'xsim.dir/xil_defaultlib', sim / 'xsim.dir/xil_defaultlib')
    shutil.copy2(SHARED / 'xsim.ini', sim / 'xsim.ini')
    libs = list(dict.fromkeys(re.findall(r'-L (\w+)', (SHARED / 'elaborate.bat').read_text())))
    rtl_sources = {path: sha(path) for path in re.findall(r'"([^"]+)"', (template / 'sources.prj').read_text())}
    report = dict(build=str(BUILD), cases=cases, libraries=libs,
        source_hashes=sources, rtl_source_hashes=rtl_sources, helper_sha256=sha(__file__),
        gui_input_sha256=sha(BUILD / 'gui_input.json'),
        flow='actual MainWindow -> _experiment_run_arguments -> execute_qick_sequence host coordinates -> real QICK compiler',
        board_access=False, rtl_version='existing v4', shared_library_writes=False)
    (BUILD / 'prepared.json').write_text(json.dumps(report, indent=2))
    (HERE / 'prepared.json').write_text(json.dumps(report, indent=2))
    print(f'PREPARED six GUI host coordinates in {BUILD}', flush=True)


if __name__ == '__main__':
    main()
