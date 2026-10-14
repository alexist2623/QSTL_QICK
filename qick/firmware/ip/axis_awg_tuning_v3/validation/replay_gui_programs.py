"""Bind existing RTL PMEM/DMEM to current GUI/compiler sources without running xsim."""
import argparse
from dataclasses import replace
import gc
import hashlib
import json
from pathlib import Path
import sys
import traceback
from report_system_validation import CASES


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def words(program):
    program.compile()
    pmem = ''.join(f'{int(w):016x}\n' for w in program.binprog)
    dmem = ''.join(f'{program._runtime_dmem_base+i:08x} {int(w)&0xffffffff:08x}\n'
                   for i, w in enumerate(program._runtime_dmem_words))
    return pmem, dmem


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--gui', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    repo = Path(__file__).resolve().parents[5]
    sys.path.insert(0, str(a.gui/'DCWaveformGeneratorGUI'))
    from qick.sim import QickSim  # noqa: F401
    from qick import QickConfig
    from qick_qcodes_experiment import build_qick_program
    from qick_front_panel import identify_qick_front_panel
    from PyQt5 import QtCore, QtWidgets, sip
    import DCWaveform_Generator as gui
    files = list((a.gui/'DCWaveformGeneratorGUI').glob('*.py'))
    files += list((repo/'qick/qick_lib/qick').rglob('*.py'))
    files += [Path(__file__), repo/'qick/firmware/projects/qstl_gui_rtl_sim/soccfg.json']
    before = {str(f): sha(f) for f in files}
    a.out.mkdir(parents=True, exist_ok=False)
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    qt_errors = []
    def callback_error(kind, value, tb):
        qt_errors.append(str(value))
        traceback.print_exception(kind, value, tb)
    sys.excepthook = callback_error
    records = {}
    for label, folder in CASES.items():
        source = a.build/folder
        cfg = QickConfig(json.loads((repo/'qick/firmware/projects/qstl_gui_rtl_sim/soccfg.json').read_text()))
        for g in cfg['gens']:
            if g['type'] in ('axis_awg_tuning_v1', 'axis_square_pulse_v1'):
                g.update(rc_precomp_version=1, output_latency_cycles=11)
            if g['type'] == 'axis_square_pulse_v1':
                g['command_latency_cycles'] = 15
            if g['type'] == 'axis_awg_tuning_v1':
                g.update(type='axis_awg_tuning_v3', frac=18, step_width=32, dc_area_version=1,
                         dc_area_bits=48, output_latency_cycles=16, dc_start_cycles=17)
        expected = tuple((source/f).read_text() for f in ('pmem.hex', 'dmem.txt'))
        namespace = {}
        exec(compile((source/'gui_export.py').read_text(), str(source/'gui_export.py'), 'exec'), namespace)
        assert words(namespace['build_program'](cfg)) == expected, label+' export differs'
        record = dict(export_equal=True, pmem_sha256=sha(source/'pmem.hex'), dmem_sha256=sha(source/'dmem.txt'),
                      export_sha256=sha(source/'gui_export.py'), gui_widgets_replayed=False)
        if (source/'gui_input.json').exists():
            data = json.loads((source/'gui_input.json').read_text())
            window = gui.MainWindow()
            panel = replace(identify_qick_front_panel(cfg), dac_current_settings=data['qick']['dac_current_settings'])
            window._on_qick_configuration_identified(panel)
            window._load_settings_json(source/'gui_input.json')
            window._experiment_panel.bias_t_type.dc_checkbox.setChecked(True)
            window._experiment_panel.bias_t_type.rc_checkbox.setChecked(True)
            window._experiment_panel.bias_t_filter_tau_us.setValue(10.)
            runtime = window._experiment_run_arguments(require_readout=True, require_run_config=False)
            match = json.loads((source/'gui_widget_match.json').read_text())
            if match['sequence_mutations']:
                assert match['sequence_mutations'] == ['reverse sweep axes after GUI input']
                runtime['sequence'].sweeps.reverse()
            program = build_qick_program(cfg, **{key:runtime[key] for key in (
                'sequence','awg_channels','repetitions_per_sweep','rf_specs','readout_spec','compile_validation_mode')},
                tproc_mhz=300.)
            assert words(program) == expected, label+' current GUI differs'
            record.update(gui_widgets_replayed=True, gui_input_sha256=sha(source/'gui_input.json'),
                          sequence_mutations=match['sequence_mutations'])
            # Finish deferred selection/layout callbacks while their widgets live.
            app.processEvents()
            window.close()
            window.deleteLater()
            app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
            app.processEvents()
            del window, runtime, program
            gc.collect()
        records[folder] = record
        print(label+': current compiler/GUI PMEM and DMEM match', flush=True)
    QtCore.QTimer.singleShot(0, app.quit)
    app.exec_()
    gc.collect()
    sip.delete(app)
    assert not qt_errors, qt_errors
    assert all(sha(Path(path))==digest for path,digest in before.items())
    (a.out/'source_hashes.json').write_text(json.dumps(before, indent=2), encoding='utf-8')
    (a.out/'result.json').write_text(json.dumps(dict(complete=True, simulator_started=False, cases=records),indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
