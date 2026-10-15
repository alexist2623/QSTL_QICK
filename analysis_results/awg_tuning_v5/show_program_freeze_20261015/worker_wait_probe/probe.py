"""Private offscreen Show path; replace only board connection with a 1 s wait."""
from pathlib import Path
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
GUI = Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')
HERE = Path(__file__).resolve().parent
OUT = HERE / 'result.json'
assert not OUT.exists(), 'Preserve prior evidence'
faulthandler.enable()
faulthandler.dump_traceback_later(20, repeat=False)
start = time.perf_counter()
records = []
beats = []
network_attempts = []
exceptions = []

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

expected = json.loads((ROOT / 'analysis_results/awg_tuning_v5/software_followup/scope_after_tests.json').read_text(encoding='utf-8-sig'))['source_hashes']
assert all(sha(p) == h for p, h in expected.items())
settings = GUI / 'awg_rf_test.json'
settings_hash = sha(settings)

def log(stage, **kw):
    row = dict(stage=stage, elapsed=time.perf_counter() - start,
               thread_id=threading.get_ident(), **kw)
    records.append(row)
    print(json.dumps(row), flush=True)

def forbidden(*args, **kwargs):
    network_attempts.append(repr(args[:1]))
    raise AssertionError('Network access forbidden in private diagnostic')

socket.create_connection = forbidden
socket.socket.connect = forbidden
socket.socket.connect_ex = forbidden

def watchdog():
    time.sleep(30)
    faulthandler.dump_traceback()
    os._exit(124)

threading.Thread(target=watchdog, daemon=True).start()
from qick.sim import QickSim
from qick import QickConfig
from PyQt5 import QtCore, QtGui, QtWidgets, sip
import DCWaveform_Generator as gui

cfg_path = ROOT / 'qick/firmware/projects/qstl_gui_rtl_sim/soccfg.json'
cfg = json.loads(cfg_path.read_text())
for gen in cfg['gens']:
    if gen['type'] == 'axis_awg_tuning_v1':
        gen.update(type='axis_awg_tuning_v3', frac=18, step_width=32,
                   dc_area_version=1, dc_area_bits=48, output_latency_cycles=16,
                   dc_start_cycles=17, rc_precomp_version=1)
    if gen['type'] == 'axis_square_pulse_v1':
        gen.update(rc_precomp_version=1, output_latency_cycles=11,
                   command_latency_cycles=15)
sys.path.insert(0, str(ROOT / 'analysis_results/awg_tuning_v5/software_followup/gui_rtl'))
from extension_v5 import configure
configure(cfg)
soccfg = QickConfig(cfg)
wait_active = threading.Event()
wait_event = threading.Event()

def connect_wait(connection):
    wait_active.set()
    log('worker_wait_begin')
    wait_event.wait(timeout=1.0)
    log('worker_wait_end')
    wait_active.clear()
    return None, soccfg

gui.connect_qick = connect_wait
for name in ('_on_qick_program_ready', '_on_qick_program_failed'):
    original = getattr(gui.MainWindow, name)
    def wrapped(self, *args, _name=name, _original=original, **kwargs):
        log(_name + '_begin')
        if _name.endswith('failed'):
            exceptions.append(str(args))
        value = _original(self, *args, **kwargs)
        log(_name + '_end')
        return value
    setattr(gui.MainWindow, name, wrapped)

original_build = gui.build_qick_program
def build_logged(*args, **kwargs):
    program = original_build(*args, **kwargs)
    log('built', instructions=len(program.prog_list),
        program_type=type(program).__name__,
        is_qobject=isinstance(program, QtCore.QObject),
        soccfg_type=type(program.soccfg).__name__)
    preview = program.fir_dc_timing_preview
    def preview_logged(*a, **k):
        log('preview_begin')
        result = preview(*a, **k)
        log('preview_end')
        return result
    program.fir_dc_timing_preview = preview_logged
    return program
gui.build_qick_program = build_logged

app = QtWidgets.QApplication([])
app.setQuitOnLastWindowClosed(False)
app.setFont(QtGui.QFont('Segoe UI', 9))
main_thread = threading.get_ident()
def exception_hook(*exc):
    exceptions.append(repr(exc))
    sys.__excepthook__(*exc)
sys.excepthook = exception_hook
window = gui.MainWindow()
from qick_front_panel import identify_qick_front_panel
window._on_qick_configuration_identified(identify_qick_front_panel(soccfg))
window._load_settings_json(settings)
modal_start = None
modal_record = None
modal_closed = False

def poll():
    global modal_start, modal_record, modal_closed
    panel = window._experiment_panel
    dialog = app.activeModalWidget()
    beats.append(dict(elapsed=time.perf_counter() - start,
                      thread_id=threading.get_ident(), waiting=wait_active.is_set(),
                      modal=dialog is not None, run_enabled=panel.run_button.isEnabled(),
                      show_enabled=panel.show_program_button.isEnabled(),
                      stop_enabled=panel.stop_button.isEnabled()))
    if dialog is not None and dialog is not window:
        if modal_start is None:
            modal_start = time.perf_counter()
            handle = dialog.windowHandle()
            parent_handle = window.windowHandle()
            modal_record = dict(title=dialog.windowTitle(), visible=dialog.isVisible(),
                                is_modal=dialog.isModal(),
                                parent_is_main_window=dialog.parentWidget() is window,
                                window_modality=int(dialog.windowModality()),
                                main_window_visible=window.isVisible(),
                                dialog_window_handle=handle is not None,
                                main_window_handle=parent_handle is not None,
                                transient_parent_matches_main=(handle.transientParent() == parent_handle
                                                               if handle is not None else None),
                                platform=app.platformName(),
                                geometry=[dialog.x(), dialog.y(), dialog.width(), dialog.height()])
            log('modal_ready', **modal_record)
        if time.perf_counter() - modal_start >= 0.2:
            dialog.reject()
            modal_closed = True
    if modal_closed and window._experiment_thread is None:
        app.quit()

timer = QtCore.QTimer()
timer.timeout.connect(poll)
timer.start(10)
QtCore.QTimer.singleShot(0, window._experiment_panel.show_program_button.click)
log('click_scheduled', main_thread=main_thread)
app.exec_()
timer.stop()
retained_dialogs = [d for d in window.findChildren(gui.QickAssemblyDialog)]
retained_summary = [dict(visible=d.isVisible(), parent_is_main=d.parentWidget() is window,
                         has_timing_program=hasattr(d, '_timing_program'),
                         delete_on_close=d.testAttribute(QtCore.Qt.WA_DeleteOnClose))
                    for d in retained_dialogs]
log('finished', retained_dialogs=retained_summary)
waiting = [r for r in beats if r['waiting']]
modal_beats = [r for r in beats if r['modal']]
begin = next(r for r in records if r['stage'] == 'worker_wait_begin')
end = next(r for r in records if r['stage'] == 'worker_wait_end')
changes = [p for p, h in expected.items() if sha(p) != h]
settings_unchanged = sha(settings) == settings_hash
result = dict(passed=not exceptions and not network_attempts and not changes and settings_unchanged
              and begin['thread_id'] != main_thread and len(waiting) >= 50
              and len(modal_beats) >= 5 and end['elapsed'] - begin['elapsed'] >= 0.95,
              board_access=False, live_gui_control=False, production_changes=changes,
              production_file_count=len(expected), settings_unchanged=settings_unchanged,
              settings_sha256=settings_hash, script_sha256=sha(__file__),
              source_hashes=expected, config_source_sha256=sha(cfg_path),
              simulated_wait_seconds=end['elapsed'] - begin['elapsed'],
              waiting_heartbeat_count=len(waiting),
              waiting_heartbeat_span_seconds=waiting[-1]['elapsed'] - waiting[0]['elapsed'] if waiting else 0,
              waiting_max_heartbeat_gap_seconds=max((b['elapsed'] - a['elapsed']
                  for a, b in zip(waiting, waiting[1:])), default=0),
              waiting_buttons_disabled=all(not r['run_enabled'] and not r['show_enabled']
                  and not r['stop_enabled'] for r in waiting),
              all_heartbeats_on_main_thread=all(r['thread_id'] == main_thread for r in beats),
              modal_heartbeat_count=len(modal_beats), modal=modal_record,
              retained_closed_dialogs=retained_summary, records=records, heartbeats=beats,
              exceptions=exceptions, network_attempts=network_attempts,
              limitations=['Event.wait releases the GIL and is not an actual Pyro transport test.',
                           'Offscreen private MainWindow is not shown; native Win32 focus, remote desktop, and monitor geometry are untested.',
                           'Single retained closed dialog is observed; cumulative leak or actual freeze is not established.',
                           'This does not reproduce or determine the cause of the reported live GUI freeze.'])
OUT.write_text(json.dumps(result, indent=2), encoding='utf-8')
window.close()
window.deleteLater()
app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
del retained_dialogs
del window
gc.collect()
sip.delete(app)
faulthandler.cancel_dump_traceback_later()
print(json.dumps({k: result[k] for k in ('passed', 'simulated_wait_seconds',
      'waiting_heartbeat_count', 'waiting_max_heartbeat_gap_seconds', 'modal_heartbeat_count')}), flush=True)
assert result['passed'], result['exceptions']
