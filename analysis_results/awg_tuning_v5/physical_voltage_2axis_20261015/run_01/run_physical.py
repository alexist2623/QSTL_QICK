"""Explicit, finite, scope-only physical test. No firmware/server/source changes."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent

def save(path, value):
    path.write_text(json.dumps(value, indent=2, default=str), encoding='utf-8')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (HERE / args.output).resolve()
    if out.parent != HERE or out.exists():
        raise ValueError('Use a fresh direct child evidence directory')
    out.mkdir()
    from prepare_program import reconstruct_prepared
    from scope_capture import ScopeCapture, save_capture
    import Pyro4
    import pyvisa
    prepared = reconstruct_prepared(HERE / 'offline_prepared_retry1')
    for name in ('prepare_program.py', 'scope_capture.py', 'run_physical.py'):
        (out / name).write_bytes((HERE / name).read_bytes())
    status = dict(started_utc=datetime.now(timezone.utc).isoformat(),
                  physical_output_started=False, sweep_completed=False,
                  capture_saved=False, cleanup_zero=False, events=[])
    def event(name, **kw):
        row = dict(utc=datetime.now(timezone.utc).isoformat(), name=name, **kw)
        status['events'].append(row)
        save(out / 'status.json', status)
        print(json.dumps(row), flush=True)
    def bounded_run(program, soc, name):
        deadline = time.monotonic() + 5.0
        progress = []
        def cancel():
            if time.monotonic() > deadline:
                raise TimeoutError(f'{name}: tProcessor counter deadline')
        def callback(done, total):
            progress.append([int(done), int(total)])
        program._run_rounds_with_counter_progress(soc, callback,
            poll_interval_seconds=.005, cancel_check=cancel)
        if not progress or progress[-1][0] != progress[-1][1]:
            raise RuntimeError(f'{name}: incomplete loop counter {progress}')
        event(name, progress=progress)
        return progress
    soc = scope = rm = cap = None
    failure = None
    try:
        Pyro4.config.SERIALIZER = 'pickle'
        Pyro4.config.PICKLE_PROTOCOL_VERSION = 4
        Pyro4.config.COMMTIMEOUT = 3
        ns = Pyro4.locateNS(host='192.168.2.99', port=8888)
        soc = Pyro4.Proxy(ns.lookup('myqick'))
        soc._pyroTimeout = 3
        cfg = soc.get_cfg()
        original = json.loads((HERE/'offline_prepared_retry1/board_config_snapshot.json').read_text())
        if cfg != original:
            save(out/'changed_board_config.json', cfg)
            raise RuntimeError('Live board config changed since GUI compilation')
        from qick_dac_current import verify_current_settings
        verify_current_settings(soc, prepared['program'].sequence.dac_current_settings)
        save(out/'live_current_before.json', soc.get_dac_current_settings())
        event('live_board_verified', awg_generators=[1,3], panel_dacs=[4,5], scope_channels=[1,2])
        rm = pyvisa.ResourceManager()
        scope = rm.open_resource('USB0::0x0957::0x1780::MY60101437::INSTR')
        scope.timeout = 5000
        scope.write_termination = '\n'
        scope.read_termination = '\n'
        cap = ScopeCapture(scope)
        cap.preflight()
        cap.archive_backup(out/'scope_backup')
        cap.configure(time_range_s=.012, time_position_s=.004,
            channel_range_v={1:1.6,2:1.6},channel_offset_v={1:.2,2:.2},
            trigger_channel=2,trigger_level_v=.1,waveform_points=10_000_000)
        # Prepare only the paired DDS paths and selected AWGs before scope arm.
        # No declare_gen in these objects, so no RFDC current/Nyquist/mixer writes.
        assert not prepared['idle_program'].gen_chs
        assert not prepared['program'].gen_chs and not prepared['program'].ro_chs
        status['physical_output_started'] = True
        prepared['idle_program'].run(soc)
        time.sleep(.05)  # finite 0.667 us idle program has ended before reloading
        event('paired_dds_idle', generators=[0,2], gain=0)
        bounded_run(prepared['zero_program'], soc, 'initial_awg_zero')
        time.sleep(.05)
        cap.arm(timeout_s=5)
        event('scope_armed', capture_id=cap.capture_id)
        counter = bounded_run(prepared['program'], soc, 'voltage_sweep')
        if counter[-1] != [9,9]:
            raise RuntimeError(f'Expected 9 physical points, got {counter[-1]}')
        status['sweep_completed'] = True
        record = cap.wait_and_read(timeout_s=5)
        metadata = save_capture(record, out/'scope_capture')
        status['capture_saved'] = True
        status['capture_id'] = record['capture_id']
        status['channel_points'] = {ch:row['preamble']['points'] for ch,row in metadata['channels'].items()}
        status['special_codes'] = {ch:row['special_codes'] for ch,row in metadata['channels'].items()}
        event('capture_saved', points=status['channel_points'], special_codes=status['special_codes'])
    except BaseException as exc:
        failure = exc
        status['error'] = repr(exc)
        (out/'error.txt').write_text(traceback.format_exc(), encoding='utf-8')
        event('failed', error=repr(exc))
    finally:
        if soc is not None and status['physical_output_started']:
            try:
                # Emergency reset only if main execution failed; then explicit
                # selected-AWG zero. stop_tproc alone would leave output levels.
                if not status['sweep_completed']:
                    soc.stop_tproc()
                bounded_run(prepared['zero_program'], soc, 'final_awg_zero')
                status['cleanup_zero'] = True
            except BaseException as exc:
                status['cleanup_error'] = repr(exc)
                failure = failure or exc
        if cap is not None:
            try:
                cap.restore()
            except BaseException as exc:
                status['scope_restore_error'] = repr(exc)
                failure = failure or exc
            status['scope_restore'] = cap.restore_result
            save(out/'scope_events.json', cap.events)
            save(out/'scope_configured.json', cap.configured_readback)
        if soc is not None:
            try:
                save(out/'live_current_after.json', soc.get_dac_current_settings())
            finally:
                soc._pyroRelease()
        if scope is not None: scope.close()
        if rm is not None: rm.close()
        before = json.loads((HERE/'offline_prepared_retry1/source_before.json').read_text())
        changed = [p for p,h in before.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
        status['production_sources_changed'] = changed
        status['finished_utc'] = datetime.now(timezone.utc).isoformat()
        status['acquisition_success'] = bool(not failure and not changed and status['capture_saved'] and status['cleanup_zero'])
        save(out/'status.json', status)
        print(json.dumps(status, indent=2), flush=True)
    return 1 if failure or not status['acquisition_success'] else 0

if __name__=='__main__':
    raise SystemExit(main())
