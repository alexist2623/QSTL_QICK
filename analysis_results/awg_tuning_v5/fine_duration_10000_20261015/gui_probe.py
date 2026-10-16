"""Offline actual MainWindow fine-duration compile capacity probe; no RTL/board."""
from dataclasses import asdict, replace
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = Path('C:/GIT_Workspace/QSTL_QICK')
GUI = Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')
BASE = Path('F:/Vivado_Output/a3sim1/rc_precomp_repeat_reset_hold_duration_2x2_v4_all_20261014_exact10us_hold1_output_sum_awg_v3/gui_input.json')
MATRIX = [[1., .23, -.11], [-.17, 1., .07], [.12, -.09, 1.]]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf8')


def forbidden(*args, **kwargs):
    raise AssertionError('This compile probe must not connect to a board/network')


def main():
    socket.create_connection = forbidden
    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    sys.path.insert(0, str(GUI))
    import qick.sim
    from qick import QickConfig
    from PyQt5 import QtCore, QtGui, QtTest, QtWidgets, sip
    import DCWaveform_Generator as gui
    import qick_qcodes_experiment as runtime
    from dc_waveform_core import QickRfPulseSpec
    from qick_front_panel import identify_qick_front_panel
    helper_path = ROOT / 'analysis_results/awg_tuning_v5/software_followup/gui_rtl/extension_v5.py'
    module_spec = importlib.util.spec_from_file_location('fine_capacity_v5_routes', helper_path)
    helper = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(helper)
    sources = {str(p): sha(p) for p in list(GUI.glob('*.py')) + list((ROOT/'qick/qick_lib/qick').rglob('*.py'))}
    user_json = {str(p): sha(p) for p in GUI.glob('*.json')}
    dump(HERE/'source_hashes_before.json', sources)
    cfg = QickConfig(json.loads((ROOT/'qick/firmware/projects/qstl_gui_rtl_sim/soccfg.json').read_text()))
    for gen in cfg['gens']:
        if gen['type'] in ('axis_awg_tuning_v1', 'axis_square_pulse_v1'):
            gen.update(rc_precomp_version=1, output_latency_cycles=11)
        if gen['type'] == 'axis_square_pulse_v1':
            gen['command_latency_cycles'] = 15
        if gen['type'] == 'axis_awg_tuning_v1':
            gen.update(type='axis_awg_tuning_v3', frac=18, step_width=32,
                       dc_area_version=1, dc_area_bits=48, output_latency_cycles=16, dc_start_cycles=17)
    helper.configure(cfg)
    dump(HERE/'soccfg.json', cfg._cfg)
    dump(HERE/'candidate_routes.json', dict(hwh=cfg['validation_candidate_hwh'],
        hwh_sha256=cfg['validation_candidate_hwh_sha256'], routes=cfg['validation_routes'],
        helper=str(helper_path), helper_sha256=sha(helper_path)))
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    app.setFont(QtGui.QFont('Segoe UI', 9))
    app.setStyle('Fusion')
    errors = []
    sys.excepthook = lambda kind, value, tb: errors.append(''.join(traceback.format_exception(kind, value, tb)))
    window = gui.MainWindow()
    cases = []
    began = time.time()
    try:
        data = json.loads(BASE.read_text())
        for output in data['awg']['outputs']:
            output['time_ns'] = [0., 100., 200., 10200., 10300., 10400.]
        data['awg']['sweeps'] = []
        data['awg']['cross_capacitance'] = MATRIX
        data['qick']['bias_t_compensation']['enabled'] = False
        data['qick']['repetitions_per_sweep'] = 1
        data['qick']['compile_validation_mode'] = 'boundary'
        data['rf_readout']['enabled'] = False
        data['square_pulse']['enabled'] = False
        data['output_trigger']['enabled'] = False
        data['rf_outputs'] = [dict(asdict(QickRfPulseSpec(
            channel, 'set_1', .1, samples/4800., 0., gain, 0., 0.,
            fine_duration=True, output_board_type='DC_Out')), enabled=True)
            for channel, samples, gain in ((0, 1, 1000), (2, 97, 2000), (4, 31, 3000))]
        dump(HERE/'gui_seed.json', data)
        window._on_qick_configuration_identified(replace(identify_qick_front_panel(cfg),
            dac_current_settings=data['qick']['dac_current_settings']))
        window._load_settings_json(HERE/'gui_seed.json')
        app.processEvents()
        panel = window._rf_ports_panel._panels[0]
        panel.set_time_unit('us')

        def set_value(widget, value):
            widget.setFocus(); widget.selectAll()
            QtTest.QTest.keyClicks(widget, format(value, '.12g'))
            QtTest.QTest.keyClick(widget, QtCore.Qt.Key_Tab)

        for name, points, last in (('points_10000', 10000, 10000), ('points_100', 100, 100), ('points_2', 2, 100)):
            out = HERE/name
            out.mkdir(exist_ok=False)
            panel.fine_duration.setChecked(True)
            panel.duration_sweep_enabled.setChecked(True)
            set_value(panel.duration_sweep_start, 1/4800.)
            set_value(panel.duration_sweep_stop, last/4800.)
            set_value(panel.duration_sweep_count, points)
            app.processEvents()
            dump(out/'gui_input.json', window._settings_to_dict())
            args = window._experiment_run_arguments(require_readout=False, require_run_config=False)
            specs = args['rf_specs']
            assert args['repetitions_per_sweep'] == 1
            assert len(specs) == 3 and all(s.fine_duration for s in specs)
            assert specs[0].duration_sweep_count == points
            assert round(specs[0].duration_sweep_start_us*4800.) == 1
            assert round(specs[0].duration_sweep_stop_us*4800.) == last
            assert all(not s.duration_sweep_enabled for s in specs[1:])
            assert all(s.delay_us == .1 for s in specs)
            assert not window._sweep_specs
            dump(out/'runtime_rf_specs.json', [asdict(s) for s in specs])
            case = dict(name=name, points=points, first_sample=1, last_sample=last,
                requested_step_samples=(last-1)/(points-1), folder=str(out),
                gui_count=specs[0].duration_sweep_count, repeated_per_point=1,
                dmem_capacity_words=cfg['tprocs'][0]['dmem_size'], began=time.time())
            print(f'COMPILE {name}: actual GUI count={points}', flush=True)
            try:
                program = runtime.build_qick_program(cfg, args['sequence'],
                    awg_channels=args['awg_channels'], repetitions_per_sweep=args['repetitions_per_sweep'],
                    rf_specs=specs, readout_spec=args['readout_spec'], tproc_mhz=300.,
                    compile_validation_mode=args['compile_validation_mode'])
                program.compile()
            except Exception as exc:
                trace = traceback.format_exc()
                (out/'compile_error.txt').write_text(trace, encoding='utf8')
                case.update(compiled=False, error_type=type(exc).__name__, error=str(exc),
                    elapsed_seconds=time.time()-case['began'])
                cases.append(case)
                dump(out/'result.json', case)
                print(f'REJECTED {name}: {type(exc).__name__}: {exc}', flush=True)
                if points != 10000:
                    raise
                continue
            assert program.sequence.sweep_point_count == points
            assert tuple(program.sequence.sweep_shape) == (points,)
            assert len(program._runtime_dmem_words) == points*6
            (out/'program.asm').write_text(program.asm(), encoding='utf8')
            (out/'pmem.hex').write_text(''.join(f'{int(w):016x}\n' for w in program.binprog), encoding='utf8')
            (out/'dmem.txt').write_text(''.join(f'{program._runtime_dmem_base+i:08x} {int(w)&0xffffffff:08x}\n'
                for i,w in enumerate(program._runtime_dmem_words)), encoding='utf8')
            dump(out/'fine_table.json', {str(k):v for k,v in program._fine_rf_rows.items()})
            summary = program.summary()
            dump(out/'memory_summary.json', {key:value for key,value in summary.items()
                if any(token in key for token in ('memory', 'dmem', 'pmem', 'table', 'instruction'))})
            case.update(compiled=True, pmem_words=len(program.binprog),
                asm_instructions=len(program.prog_list), dmem_words=len(program._runtime_dmem_words),
                dmem_start=program._runtime_dmem_base, dmem_end=program._runtime_dmem_last_address,
                sweep_shape=program.sequence.sweep_shape,
                envelope_samples={str(ch):program.envelopes[ch]['next_addr'] for ch in (0,2,4)},
                elapsed_seconds=time.time()-case['began'])
            if points == 100:
                (out/'program_numbered.asm').write_text(''.join(
                    f'{index:4d}  {line}\n' for index,line in enumerate(program.asm().splitlines(),1)), encoding='utf8')
                info = program._fine_rf_rows[0]
                dump(out/'selected_dmem_rows.json', dict(
                    row_width_words=6, table_base=program._runtime_dmem_base,
                    columns=['start_cycle','first_mode','envelope_address','tail_mode','tail_cycle','long_enabled'],
                    rows=[dict(point=index, sample_count=index+1,
                        dmem_address=program._runtime_dmem_base+6*index,
                        words=list(info['rows'][index]), details=info['details'][index])
                        for index in (0,1,2,94,95,99)]))
                window.resize(1600, 1000); window.show(); app.processEvents()
                assert window.grab().save(str(out/'gui.png'))
            case['artifact_hashes'] = {p.name:sha(p) for p in out.iterdir() if p.is_file()}
            cases.append(case)
            dump(out/'result.json', case)
            print(f'COMPILED {name}: PMEM={case["pmem_words"]} DMEM={case["dmem_words"]}', flush=True)
        assert not errors, errors
        assert not cases[0]['compiled']
        assert 'memory' in cases[0]['error'].lower() or 'dmem' in cases[0]['error'].lower(), cases[0]
        assert all(case['compiled'] for case in cases[1:])
        source_after = {path:sha(path) for path in sources}
        assert source_after == sources
        assert {str(p):sha(p) for p in GUI.glob('*.json')} == user_json
        dump(HERE/'results.json', dict(complete=True, passed=True, cases=cases,
            flow='actual MainWindow settings -> _experiment_run_arguments -> runtime.build_qick_program -> compile',
            hardware_sweep_only=True, software_host_loop=False, rtl_executed=False,
            board_accessed=False, existing_gui_controlled=False, user_json_unchanged=True,
            source_hashes_unchanged=True, source_hashes=sources, helper_sha256=sha(__file__),
            elapsed_seconds=time.time()-began,
            limitations='Compile capacity probe only; no new RTL or analog validation. 2-point comparison has endpoints 1 and 100 samples, while 100-point comparison includes every integer sample.'))
    finally:
        window.close(); window.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete); app.processEvents()
        del window
        gc.collect()
        QtCore.QTimer.singleShot(0, app.quit); app.exec_(); sip.delete(app)


if __name__ == '__main__':
    main()
