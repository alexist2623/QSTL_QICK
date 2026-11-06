"""Board-local lease for cooperative, measurement-free tProcessor output."""
import math
import threading
import time
import uuid


class OutputForeverController:
    STOP_ADDR = 2
    DONE_ADDR = 3

    def __init__(self, soc):
        self.soc = soc
        self.lock = threading.RLock()
        self.session = None

    def check_idle(self, require_capture_idle=False):
        with self.lock:
            if self.session is not None and self.session['state'] != 'stopped':
                raise RuntimeError('An output session is active or cleanup is incomplete')
            if require_capture_idle:
                capture = getattr(self.soc, 'ddr4_buf', None)
                if capture is not None:
                    if not capture.cfg.get('supports_abort', False):
                        raise RuntimeError('Output forever requires the v8 DDR capture driver')
                    status = capture.abort_status()
                    if status['busy'] or status['armed'] or status['pending']:
                        raise RuntimeError('Finish or cancel the active DDR capture before Run forever')
        return True

    def begin(self, awg_channels, lease_seconds=2.0):
        lease = float(lease_seconds)
        if not math.isfinite(lease) or not 0.5 <= lease <= 5.0:
            raise ValueError('Output lease must be 0.5..5 seconds')
        channels = tuple(int(ch) for ch in awg_channels)
        if not channels or len(set(channels)) != len(channels):
            raise ValueError('Output session requires distinct AWG channels')
        if self.soc.TPROC_VERSION != 1:
            raise ValueError('Output forever requires tProcessor v1')
        for ch in channels:
            if self.soc.gens[ch].cfg.get('output_clip_version') != 1:
                raise ValueError('Output forever requires v8 AWG firmware/driver')
        with self.lock:
            self.check_idle(require_capture_idle=True)
            self.soc.tproc.single_write(addr=self.STOP_ADDR, data=0)
            self.soc.tproc.single_write(addr=self.DONE_ADDR, data=0)
            self.session = dict(token=uuid.uuid4().hex, state='running', reason='',
                                deadline=time.monotonic()+lease, lease=lease,
                                channels=channels, error='')
            thread = threading.Thread(target=self._watch, args=(self.session,), daemon=True,
                                      name='qick-output-lease')
            thread.start()
            return self.status(self.session['token'])

    def _session(self, token):
        if self.session is None or token != self.session['token']:
            raise ValueError('Unknown output-only session token')
        return self.session

    def status(self, token):
        with self.lock:
            s = self._session(token)
            return {key: s[key] for key in ('token', 'state', 'reason', 'error')}

    def renew(self, token):
        with self.lock:
            s = self._session(token)
            if s['state'] == 'running':
                s['deadline'] = time.monotonic()+s['lease']
            return self.status(token)

    def stop(self, token, timeout=35.0):
        timeout = float(timeout)
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('Stop timeout must be positive and finite')
        with self.lock:
            s = self._session(token)
            if s['state'] == 'running':
                s['state'] = 'stopping'
                s['reason'] = 'user_stop'
                s['deadline'] = 0.0
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            status = self.status(token)
            if status['state'] == 'stopped':
                return status
            if status['state'] == 'error':
                raise RuntimeError('Output-only cleanup incomplete: '+status['error'])
            time.sleep(0.02)
        raise TimeoutError('Output-only cleanup incomplete: board stop acknowledgement timed out')

    def _watch(self, session):
        try:
            while True:
                with self.lock:
                    if time.monotonic() >= session['deadline']:
                        session['state'] = 'stopping'
                        session['reason'] = session['reason'] or 'host_lease_expired'
                        break
                time.sleep(0.05)
            self.soc.tproc.single_write(addr=self.STOP_ADDR, data=1)
            deadline = time.monotonic()+30.0
            while int(self.soc.tproc.single_read(addr=self.DONE_ADDR)) != 1:
                if time.monotonic() >= deadline:
                    raise TimeoutError('sequence did not reach its zero-output stop epilogue')
                time.sleep(0.02)
            self.soc.start_src('internal')
            self.soc.stop_tproc()
            for ch in session['channels']:
                gen = self.soc.gens[ch]
                status = gen.get_status(decode=True)
                if gen.get_current() != 0 or not status['idle'] or status['axi_override_pending']:
                    raise RuntimeError(f'AWG {ch} did not acknowledge zero/idle: {status}')
            with self.lock:
                session['state'] = 'stopped'
        except Exception as exc:
            # Do not claim a clean stop. Lock the session against another start.
            # The v8 clamp prevents late AWG commands from restoring a nonzero level.
            errors = [str(exc)]
            try:
                self.soc.start_src('internal')
                self.soc.stop_tproc()
            except Exception as stop_error:
                errors.append(f'producer stop: {stop_error}')
            for ch in session['channels']:
                try:
                    self.soc.gens[ch].set_output_limits(0, 0, True)
                except Exception as clamp_error:
                    errors.append(f'AWG {ch} clamp: {clamp_error}')
            with self.lock:
                session['state'] = 'error'
                session['error'] = '; '.join(errors)
