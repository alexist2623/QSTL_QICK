"""Compare real GUI preview compilation with the runtime acquisition boundary."""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import socket
import sys

ROOT = Path('C:/GIT_Workspace/QSTL_QICK')
HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('--profile', choices=('v4', 'v5'), required=True)
args = ap.parse_args()
def forbid(*a, **k):
    raise AssertionError('No network/board operation is allowed')
socket.create_connection = forbid
socket.socket.connect = forbid
from qick.sim import QickSim
from qick import QickConfig
from PyQt5 import QtCore, QtGui, QtWidgets, sip
import DCWaveform_Generator as gui
import qick_qcodes_experiment as runtime
from qick_front_panel import identify_qick_front_panel

cfg = QickConfig(json.loads((ROOT/'qick/firmware/projects/qstl_gui_rtl_sim/soccfg.json').read_text()))
for gen in cfg['gens']:
    if gen['type'] == 'axis_awg_tuning_v1':
        gen.update(type='axis_awg_tuning_v3', frac=18, step_width=32,
                   dc_area_version=1, dc_area_bits=48, output_latency_cycles=16,
                   dc_start_cycles=17, rc_precomp_version=1)
    if gen['type'] == 'axis_square_pulse_v1':
        gen.update(rc_precomp_version=1, output_latency_cycles=11, command_latency_cycles=15)
if args.profile == 'v5':
    sys.path.insert(0, str(ROOT/'analysis_results/awg_tuning_v5/software_followup/gui_rtl'))
    from extension_v5 import configure
else:
    sys.path.insert(0, str(ROOT/'qick/firmware/ip/axis_output_sum_v1/validation'))
    from gui_rtl_extension import configure
configure(cfg)

def digest(data):
    return hashlib.sha256(data).hexdigest()
def program_artifacts(program):
    program.compile()
    envelope = {}
    for ch, bank in enumerate(program.envelopes):
        for name, entry in bank['envs'].items():
            values = entry['data']
            envelope[f'{ch}/{name}'] = dict(addr=int(entry['addr']), shape=list(values.shape),
                dtype=str(values.dtype), sha256=digest(values.tobytes()))
    words = [int(v) for v in program.binprog]
    dmem = [int(v) for v in program._runtime_dmem_words]
    return dict(assembly_sha256=digest(program.asm().encode()),
        instructions=len(program.prog_list), pmem_words=words,
        dmem_base=program._runtime_dmem_base, dmem_words=dmem, envelopes=envelope)

app = QtWidgets.QApplication([])
app.setFont(QtGui.QFont('Segoe UI', 9))
app.setQuitOnLastWindowClosed(False)
window = gui.MainWindow()
window._on_qick_configuration_identified(identify_qick_front_panel(cfg))
settings = Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI/awg_rf_test.json')
window._load_settings_json(settings)
show_args = window._experiment_run_arguments(require_readout=False, require_run_config=False)
run_args = window._experiment_run_arguments()
common = ('sequence', 'awg_channels', 'repetitions_per_sweep', 'rf_specs', 'readout_spec', 'compile_validation_mode')
show_kwargs = {k: show_args[k] for k in common}
show_kwargs['tproc_mhz'] = window._qick_tproc_mhz
show_results, errors = [], []
gui.connect_qick = lambda connection: (None, cfg)
worker = gui.QickProgramWorker(show_args['connection_config'], show_kwargs)
worker.finished.connect(show_results.append)
worker.failed.connect(errors.append)
worker.run()
assert not errors and len(show_results) == 1, errors
show_proof = program_artifacts(show_results[0]['program'])

class CapturedBeforeAcquisition(Exception):
    pass
class NoBoard:
    def __getattr__(self, name):
        raise AssertionError('Unexpected board access: ' + name)
captured = []
real_builder = runtime.build_qick_program
def build_and_capture(*a, **k):
    program = real_builder(*a, **k)
    def capture(soc, **acquire_kwargs):
        captured.append(program_artifacts(program))
        raise CapturedBeforeAcquisition()
    program.acquire_fir_ddr = capture
    return program
runtime.build_qick_program = build_and_capture
runtime.configure_rf_readout = lambda soc, spec: {}
run_kwargs = {k: run_args[k] for k in common if k != 'sequence'}
run_kwargs['tproc_mhz'] = run_args['gui_settings']['qick']['tproc_mhz']
try:
    runtime.execute_qick_sequence(NoBoard(), cfg, run_args['sequence'], **run_kwargs)
except CapturedBeforeAcquisition:
    pass
assert len(captured) == 1
run_proof = captured[0]
assert show_proof == run_proof, 'Show and runtime acquisition-boundary data differ'
result = dict(passed=True, profile=args.profile, settings=str(settings),
    settings_sha256=digest(settings.read_bytes()), assembly_equal=True,
    pmem_equal=True, runtime_dmem_equal=True, envelopes_equal=True,
    rf_host_sweep_axes=len(runtime._rf_software_sweep_bindings(run_args['rf_specs'])),
    proof=show_proof, board_connected=False, hardware_run=False,
    scope='Actual GUI/Show worker and normal runtime path; local config, readout setup stub, stopped at acquire_fir_ddr entry')
window.close()
window.deleteLater()
worker.deleteLater()
app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
del window, worker
gc.collect()
QtCore.QTimer.singleShot(0, app.quit)
app.exec_()
sip.delete(app)
out = HERE/f'show_run_equal_{args.profile}.json'
assert not out.exists(), 'Preserve prior evidence'
out.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k != 'proof'}))
