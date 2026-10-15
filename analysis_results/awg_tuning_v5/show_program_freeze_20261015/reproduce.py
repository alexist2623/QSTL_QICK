"""Diagnose Show QICK Program with a private GUI and local hardware metadata."""
from pathlib import Path
import argparse
import faulthandler
import gc
import hashlib
import json
import os
import socket
import sys
import threading
import time

ROOT = Path('C:/GIT_Workspace/QSTL_QICK')
HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('--profile', choices=('v4', 'v5'), default='v5')
ap.add_argument('--settings', default='C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI/awg_rf_test.json')
args = ap.parse_args()
faulthandler.enable()
faulthandler.dump_traceback_later(20, repeat=True)
started = time.monotonic()
records = []
def log(stage, **kw):
    row = dict(stage=stage, elapsed=time.monotonic()-started, **kw)
    records.append(row)
    print(json.dumps(row), flush=True)
def forbidden(*a, **k):
    raise AssertionError('Network access is forbidden in the isolated reproduction')
socket.create_connection = forbidden
socket.socket.connect = forbidden
def watchdog():
    time.sleep(65)
    log('watchdog_timeout')
    faulthandler.dump_traceback()
    os._exit(124)
threading.Thread(target=watchdog, daemon=True).start()

log('imports_begin')
from qick.sim import QickSim
from qick import QickConfig
from PyQt5 import QtCore, QtGui, QtWidgets, sip
import DCWaveform_Generator as gui
cfg = json.loads((ROOT/'qick/firmware/projects/qstl_gui_rtl_sim/soccfg.json').read_text())
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
soccfg = QickConfig(cfg)
def connect_local(connection):
    log('connect_substituted_local_metadata', profile=args.profile)
    return None, soccfg
gui.connect_qick = connect_local
for name in ('_experiment_run_arguments', '_on_qick_program_ready', '_on_qick_program_failed'):
    original = getattr(gui.MainWindow, name)
    def wrapper(self, *a, _fn=original, _name=name, **k):
        log(_name+'_begin')
        result = _fn(self, *a, **k)
        log(_name+'_end')
        return result
    setattr(gui.MainWindow, name, wrapper)
build = gui.build_qick_program
def build_logged(*a, **k):
    log('build_begin')
    program = build(*a, **k)
    log('build_end', instructions=len(program.prog_list))
    preview = program.fir_dc_timing_preview
    def preview_logged(*pa, **pk):
        log('fir_dc_timing_preview_begin')
        result = preview(*pa, **pk)
        log('fir_dc_timing_preview_end')
        return result
    program.fir_dc_timing_preview = preview_logged
    return program
gui.build_qick_program = build_logged
app = QtWidgets.QApplication([])
app.setQuitOnLastWindowClosed(False)
app.setFont(QtGui.QFont('Segoe UI', 9))
sys.excepthook = lambda *ex: (log('unhandled_exception'), sys.__excepthook__(*ex))
log('window_begin')
window = gui.MainWindow()
from qick_front_panel import identify_qick_front_panel
window._on_qick_configuration_identified(identify_qick_front_panel(soccfg))
log('settings_begin', path=args.settings)
settings = Path(args.settings)
window._load_settings_json(settings)
log('settings_end')
beats = [0]
dialogs = []
def poll():
    beats[0] += 1
    dialog = app.activeModalWidget()
    if dialog is not None and dialog is not window:
        title = dialog.windowTitle()
        if title not in dialogs:
            dialogs.append(title)
            log('modal_ready', title=title)
        dialog.reject()
    if dialogs and window._experiment_thread is None:
        app.quit()
timer = QtCore.QTimer()
timer.timeout.connect(poll)
timer.start(50)
QtCore.QTimer.singleShot(0, window._experiment_panel.show_program_button.click)
log('click_scheduled')
app.exec_()
log('event_loop_finished', heartbeats=beats[0], dialogs=dialogs)
timer.stop()
window.close()
window.deleteLater()
app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
del window
gc.collect()
sip.delete(app)
faulthandler.cancel_dump_traceback_later()
out = HERE/f'reproduction_{args.profile}.json'
assert not out.exists(), 'Preserve prior evidence'
out.write_text(json.dumps(dict(profile=args.profile, settings=str(settings),
    settings_sha256=hashlib.sha256(settings.read_bytes()).hexdigest(),
    board_connected=False, production_modified=False, records=records), indent=2), encoding='utf-8')
log('clean_exit')
