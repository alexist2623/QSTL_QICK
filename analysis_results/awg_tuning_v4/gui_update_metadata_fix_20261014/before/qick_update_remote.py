"""Board helper for explicitly requested GUI file updates (Python 3.8+).

Imports do not connect or change files. The helper never starts/stops QICK,
constructs QickSoc, downloads an overlay, installs packages, or emits pulses.
"""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import time
import zipfile


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, data):
    tmp = path.with_suffix('.writing')
    tmp.write_text(json.dumps(data, indent=2), encoding='utf-8')
    os.replace(str(tmp), str(path))


def root_path(request):
    supplied = Path(request['remote_repo'])
    if not supplied.is_absolute() or '..' in supplied.parts or len(supplied.parts) < 3:
        raise ValueError('Choose an absolute repository below /home or /root.')
    if supplied.parts[1] not in ('home', 'root'):
        raise ValueError('Repository must be below /home or /root.')
    root = supplied.resolve(strict=True)
    if root != supplied or not (root / 'qick/qick_lib/qick/__init__.py').is_file():
        raise ValueError('Expected a real QSTL_QICK repository, not a symlink.')
    child(root, 'qick/qick_lib')
    return root


def child(root, relative):
    rel = PurePosixPath(relative)
    if rel.is_absolute() or not rel.parts or '..' in rel.parts:
        raise ValueError('Invalid relative path.')
    p = root.joinpath(*rel.parts)
    if p.resolve() != p or root not in p.parents:
        raise ValueError('Path escapes the repository or contains a symlink.')
    return p


def transaction(root, request):
    release = request['release']
    if not re.fullmatch(r'[0-9a-f]{32}', release):
        raise ValueError('Invalid update ID.')
    return child(root, '.qick_gui_updates/' + release)


def live(request, require=False):
    """Read Pyro configuration; distinguish stopped endpoint from an unknown error."""
    import Pyro4
    import psutil
    Pyro4.config.COMMTIMEOUT = 4
    Pyro4.config.SERIALIZER = 'pickle'
    Pyro4.config.PICKLE_PROTOCOL_VERSION = 4
    # A working nameserver is required. Its absence cannot prove QICK is stopped.
    with Pyro4.locateNS(host=request['host'], port=int(request['ns_port'])) as ns:
        try:
            uri = ns.lookup(request['proxy_name'])
        except Pyro4.errors.NamingError:
            if require:
                raise ValueError('The selected QICK name is not registered.')
            return {'reachable': False, 'stopped': True, 'reason': 'QICK name not registered'}
    addresses = {'127.0.0.1', 'localhost', '::1'}
    addresses.update(a.address for values in psutil.net_if_addrs().values() for a in values)
    if uri.host not in addresses:
        raise ValueError('Nameserver points to a different host; select the local board endpoint.')
    listeners = [c for c in psutil.net_connections(kind='tcp')
                 if c.status == psutil.CONN_LISTEN and c.laddr.port == uri.port]
    if not listeners:
        if require:
            raise ValueError('QICK is stopped. Restart it manually with the selected BIT first.')
        return {'reachable': False, 'stopped': True, 'reason': 'No local QICK listener'}
    with Pyro4.Proxy(uri) as soc:
        cfg = soc.get_cfg()
    owners = {c.pid for c in listeners if c.pid}
    process = psutil.Process(next(iter(owners))) if len(owners) == 1 else None
    return {'reachable': True, 'stopped': False, 'board': cfg.get('board'),
            'sw_version': cfg.get('sw_version'), 'fw_timestamp': cfg.get('fw_timestamp'),
            'pid': process.pid if process else None,
            'process_started': process.create_time() if process else None,
            'python_executable': process.exe() if process else None,
            'generators': [{key: g.get(key) for key in (
                'fullpath', 'type', 'dac', 'output_sum_block', 'output_sum_role')}
                for g in cfg.get('gens', [])]}


def stopped(request):
    if not request.get('server_stopped'):
        raise ValueError('Confirm that all outputs and the QICK server have been stopped.')
    config = live(request)
    if not config.get('stopped'):
        raise ValueError('The QICK server still runs. Stop it before changing files.')


def tree_hashes(path):
    if path.is_symlink():
        raise ValueError('Symlink target is not supported.')
    if not path.exists():
        return None
    if path.is_file():
        return {'file': digest(path)}
    result = {}
    for p in sorted(path.rglob('*')):
        if p.is_symlink():
            raise ValueError('Library contains a symlink: ' + str(p))
        if '__pycache__' in p.parts or p.suffix in ('.pyc', '.pyo'):
            continue
        if p.is_file():
            result[p.relative_to(path).as_posix()] = digest(p)
    return result


def check_payload(stage, manifest):
    payload = stage / 'payload'
    actual = {p.relative_to(payload).as_posix() for p in payload.rglob('*') if p.is_file()}
    if actual != set(manifest['files']):
        raise ValueError('Payload file list differs from the reviewed manifest.')
    for name, info in manifest['files'].items():
        p = child(payload, name)
        if p.stat().st_size != info['bytes'] or digest(p) != info['sha256']:
            raise ValueError('Payload hash mismatch: ' + name)
    for p in (payload / 'qick_lib').rglob('*.py'):
        compile(p.read_bytes(), str(p), 'exec')  # In memory; never import the payload.


def targets(root, request):
    bit = child(root, request['remote_bit'])
    if not request['remote_bit'].startswith('qick/firmware/') or bit.suffix != '.bit':
        raise ValueError('Firmware target must be a .bit below qick/firmware/.')
    hwh = child(root, PurePosixPath(request['remote_bit']).with_suffix('.hwh').as_posix())
    return [child(root, 'qick/qick_lib'), bit, hwh]


def verify_runtime(request, manifest, installed_at):
    cfg = live(request, require=True)
    if cfg['board'] != 'ZCU216':
        raise ValueError('Connected board is not ZCU216.')
    if cfg['fw_timestamp'] != manifest['firmware_timestamp']:
        raise ValueError('Running firmware does not match the selected HWH timestamp.')
    if cfg['sw_version'] != manifest['library_version']:
        raise ValueError('Running QICK library version differs from the selected library.')
    if not cfg['process_started'] or cfg['process_started'] <= installed_at:
        raise ValueError('Restart the QICK Python process after the file update (including notebook kernels).')
    if os.path.realpath(cfg['python_executable']) != os.path.realpath(sys.executable):
        raise ValueError('QICK server uses a different Python interpreter from Board Python.')
    actual = {g['fullpath']: g for g in cfg['generators']}
    for expected in manifest['generators']:
        if actual.get(expected['fullpath']) != expected:
            raise ValueError('Running generator/DAC/sum routing differs: ' + expected['fullpath'])
    # Other unchanged RF/Square outputs also exist; the manifest lists the seven AWG paths.
    return cfg


def restore_files(stage, journal):
    """Restore an attempted replacement, retaining displaced files and all evidence."""
    paths = [Path(p) for p in journal['targets']]
    for index, target in enumerate(paths):
        backup = child(stage, 'backup/' + str(index))
        if backup.exists():
            if tree_hashes(backup) != journal['before'][index]:
                raise ValueError('Backup hash mismatch; recovery requires inspection.')
        elif journal['before'][index] is not None and tree_hashes(target) != journal['before'][index]:
            raise ValueError('Original file unavailable; recovery requires inspection.')
    retired = stage / ('retired_' + str(time.time_ns()))
    retired.mkdir()
    for index in reversed(range(len(paths))):
        target, backup = paths[index], stage / 'backup' / str(index)
        if backup.exists():
            if target.exists():
                os.replace(str(target), str(retired / str(index)))
            os.replace(str(backup), str(target))
        elif journal['before'][index] is None and target.exists():
            os.replace(str(target), str(retired / str(index)))
    if [tree_hashes(p) for p in paths] != journal['before']:
        raise ValueError('Restored file hashes differ; inspect before restarting QICK.')


def inspect(request, root):
    spec = importlib.util.find_spec('qick')
    records = []
    parent = child(root, '.qick_gui_updates')
    if parent.is_dir():
        for p in sorted(parent.glob('*/journal.json')):
            if not re.fullmatch(r'[0-9a-f]{32}', p.parent.name):
                continue
            path = child(root, p.relative_to(root).as_posix())
            data = json.loads(path.read_text())
            manifest_path = child(root, (p.parent / 'manifest.json').relative_to(root).as_posix())
            if digest(manifest_path) != data['manifest_sha256']:
                raise ValueError('Transaction manifest changed: ' + p.parent.name)
            package = json.loads(manifest_path.read_text())
            records.append({'release': p.parent.name, 'state': data.get('state'),
                            'firmware': data.get('remote_bit'),
                            'identity': hashlib.sha256(json.dumps(package, sort_keys=True).encode()).hexdigest(),
                            'library_version': package['library_version'],
                            'firmware_timestamp': package['firmware_timestamp']})
    try:
        runtime = live(request)
    except Exception as exc:
        runtime = {'reachable': None, 'stopped': False, 'reason': str(exc)}
    return {'repository': str(root), 'python': sys.executable,
            'python_version': sys.version.split()[0], 'qick_import_path': spec.origin if spec else None,
            'free_bytes': shutil.disk_usage(str(root)).free, 'runtime': runtime,
            'transactions': records, 'update_lock_exists': (root / '.qick_gui_update.lock').exists()}


def main(request):
    root = root_path(request)
    action = request['action']
    if action == 'inspect':
        return inspect(request, root)
    stage = transaction(root, request)
    if action == 'reserve':
        stage.mkdir(parents=True, exist_ok=False)
        return {'stage': str(stage)}
    if action == 'prepare':
        manifest = json.loads((stage / 'manifest.json').read_text())
        archive = stage / 'payload.zip'
        if digest(archive) != request['archive_sha256']:
            raise ValueError('Transferred archive hash does not match.')
        dest = child(stage, 'payload')
        dest.mkdir(exist_ok=False)
        with zipfile.ZipFile(str(archive)) as z:
            names = z.namelist()
            if len(names) != len(set(names)) or set(names) != set(manifest['files']):
                raise ValueError('Archive entries differ from manifest.')
            for member in z.infolist():
                expected = manifest['files'][member.filename]
                if member.file_size != expected['bytes'] or member.is_dir():
                    raise ValueError('Unexpected archive entry.')
                out = child(dest, member.filename)
                out.parent.mkdir(parents=True, exist_ok=True)
                with z.open(member) as source, out.open('xb') as sink:
                    shutil.copyfileobj(source, sink, 1024 * 1024)
        check_payload(stage, manifest)
        paths = targets(root, request)
        journal = {'state': 'prepared', 'remote_repo': str(root), 'remote_bit': request['remote_bit'],
                   'targets': [str(p) for p in paths], 'before': [tree_hashes(p) for p in paths],
                   'manifest_sha256': digest(stage / 'manifest.json'), 'installed': []}
        save(stage / 'journal.json', journal)
        return {'release': request['release'], 'state': 'prepared',
                'firmware': request['remote_bit'], 'files': len(manifest['files'])}
    journal = json.loads((stage / 'journal.json').read_text())
    manifest = json.loads((stage / 'manifest.json').read_text())
    if digest(stage / 'manifest.json') != journal['manifest_sha256']:
        raise ValueError('Prepared manifest was changed.')
    paths = targets(root, request)
    if [str(p) for p in paths] != journal['targets']:
        raise ValueError('Target changed after preparation.')
    # The same mutex protects verification and replacement from concurrent GUI actions.
    if action not in ('verify', 'apply', 'rollback'):
        raise ValueError('Unsupported action.')
    lock = child(root, '.qick_gui_update.lock')
    lock.mkdir(exist_ok=False)
    try:
        if action == 'verify':
            if journal['state'] not in ('files_updated_restart_required', 'applied'):
                raise ValueError('This transaction has not been installed.')
            if [tree_hashes(p) for p in paths] != journal['after']:
                raise ValueError('Installed files changed since the update.')
            cfg = verify_runtime(request, manifest, journal['installed_at'])
            journal.update(state='applied', runtime=cfg)
            save(stage / 'journal.json', journal)
            return {'state': 'applied', 'runtime': cfg, 'release': request['release']}
        allowed = ('prepared',) if action == 'apply' else ('applied', 'files_updated_restart_required')
        if journal['state'] not in allowed:
            raise ValueError('Transaction is not in the required state: ' + journal['state'])
        expected = journal['before'] if action == 'apply' else journal['after']
        if [tree_hashes(p) for p in paths] != expected:
            raise ValueError('Live files changed. Inspect and prepare a new transaction.')
        stopped(request)
        if action == 'rollback':
            journal['state'] = 'rolling_back'
            save(stage / 'journal.json', journal)
            restore_files(stage, journal)
            journal['state'] = 'rolled_back_restart_required'
            save(stage / 'journal.json', journal)
            return {'state': journal['state'], 'release': request['release']}
        check_payload(stage, manifest)
        (stage / 'backup').mkdir(exist_ok=False)
        sources = [stage / 'payload/qick_lib', stage / 'payload/firmware/bitstream.bit',
                   stage / 'payload/firmware/bitstream.hwh']
        after_expected = [tree_hashes(p) for p in sources]
        journal['state'] = 'applying'
        save(stage / 'journal.json', journal)
        try:
            for index, (source, target) in enumerate(zip(sources, paths)):
                target.parent.mkdir(parents=True, exist_ok=True)
                journal['installing_index'] = index
                save(stage / 'journal.json', journal)
                if target.exists():
                    os.replace(str(target), str(stage / 'backup' / str(index)))
                os.replace(str(source), str(target))
                journal['installed'].append(index)
                save(stage / 'journal.json', journal)
            after = [tree_hashes(p) for p in paths]
            if after != after_expected:
                raise ValueError('Installed file hash mismatch.')
            journal.update(state='files_updated_restart_required', after=after, installed_at=time.time())
            save(stage / 'journal.json', journal)
            return {'state': journal['state'], 'release': request['release']}
        except Exception as exc:
            try:
                stopped(request)
                restore_files(stage, journal)
            except Exception as restore_error:
                journal.update(state='recovery_required', error=str(exc), recovery_error=str(restore_error))
                save(stage / 'journal.json', journal)
                raise RuntimeError('Update interrupted; inspect the retained transaction before restarting QICK. '
                                   + str(restore_error)) from exc
            journal.update(state='failed_restored_files', error=str(exc))
            save(stage / 'journal.json', journal)
            raise RuntimeError('Update failed; original files restored. QICK remains stopped. ' + str(exc)) from exc
    finally:
        # Remove only this process's empty mutex, never payloads/backups/evidence.
        lock.rmdir()


if __name__ == '__main__':
    try:
        req = json.loads(base64.b64decode(sys.argv[1]).decode('utf-8'))
        print(json.dumps({'ok': True, 'result': main(req)}))
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc), 'type': type(exc).__name__}))
        sys.exit(1)
