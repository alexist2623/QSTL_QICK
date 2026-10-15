"""Board helper for explicitly requested GUI file updates (Python 3.8+).

Imports do not connect or change files. The helper never starts/stops QICK,
constructs QickSoc, downloads an overlay, installs packages, or emits pulses.
"""
import base64
import ast
from email.parser import Parser
import hashlib
import importlib.util
import json
import io
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import site
import sys
import time
import tokenize
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
    if root != supplied:
        raise ValueError('Choose a real directory, not a symlink.')
    if root.name == 'qick' and (root / 'qick_lib/qick/__init__.py').is_file():
        root = root.parent
    if not (root / 'qick/qick_lib/qick/__init__.py').is_file():
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


def server_processes(proc_root=Path('/proc')):
    """Recognize standard QICK launchers; custom kernels still need user confirmation."""
    if not proc_root.is_dir():
        raise ValueError('Cannot inspect board process list.')
    active = []
    for process in proc_root.iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        try:
            args = process.joinpath('cmdline').read_bytes().decode(errors='replace').split('\0')
        except (FileNotFoundError, ProcessLookupError):
            continue
        if not args or not args[0]:
            continue
        command = Path(args[0]).name
        if 'python' not in command and command not in ('pyro_cli.py', 'pyro_service.py'):
            continue
        standard = any(a == 'qick.pyro_cli' or Path(a).name in ('pyro_cli.py', 'pyro_service.py')
                       for a in args if a and '\n' not in a)
        inline = '-c' in args and any(re.search(r'(?<![\w])(?:qick\.pyro\.)?start_server\s*\(', a)
                                      for a in args[args.index('-c') + 1:args.index('-c') + 2])
        if standard or inline:
            active.append({'pid': int(process.name), 'kind': 'QICK server launcher'})
    return active


def live(request, require=False):
    """Optional runtime identity was read by the PC; inspect its board process locally."""
    import psutil
    identity = request.get('runtime_identity')
    if not isinstance(identity, dict):
        raise ValueError('Use the optional PC runtime verification after manually restarting QICK.')
    cfg = identity['config']
    port = int(identity['port'])
    if not 1 <= port <= 65535:
        raise ValueError('Invalid QICK listener port.')
    addresses = {'127.0.0.1', 'localhost', '::1'}
    addresses.update(a.address for values in psutil.net_if_addrs().values() for a in values)
    if identity['host'] not in addresses:
        raise ValueError('Nameserver points to a different host; select the local board endpoint.')
    listeners = [c for c in psutil.net_connections(kind='tcp')
                 if c.status == psutil.CONN_LISTEN and c.laddr.port == port]
    if not listeners:
        if require:
            raise ValueError('QICK is stopped. Restart it manually with the selected BIT first.')
        return {'reachable': False, 'stopped': True, 'reason': 'No local QICK listener'}
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
    active = server_processes()
    if active:
        raise ValueError('A QICK server launcher still runs. Stop it before changing files. PIDs: '
                         + ', '.join(str(p['pid']) for p in active))


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


def installation_contract(library):
    """Read installed editable metadata; never regenerate it from another PC."""
    metadata = child(library, 'qick.egg-info')
    if not metadata.is_dir():
        raise ValueError('Expected qick.egg-info for the existing editable installation. '
                         'Install QICK separately before using the file updater.')
    tree_hashes(metadata)  # Reject links anywhere inside the retained metadata.
    pkg = Parser().parsestr((metadata / 'PKG-INFO').read_text(encoding='utf-8'))
    version = (library / 'qick/VERSION').read_text(encoding='utf-8').strip()
    if pkg.get('Name') != 'qick' or pkg.get('Version') != version:
        raise ValueError('QICK source version and installed metadata differ. '
                         'Refresh the editable installation separately.')
    def lines(name):
        path = metadata / name
        return [line.strip() for line in path.read_text(encoding='utf-8').splitlines()
                if line.strip()] if path.is_file() else []
    return {'name': 'qick', 'version': version,
            'requires_python': (pkg.get('Requires-Python') or '').strip(),
            'requirements': lines('requires.txt'), 'top_level': lines('top_level.txt'),
            'entry_points': lines('entry_points.txt')}


def installation_state(root, expected):
    library = child(root, 'qick/qick_lib')
    contract = installation_contract(library)
    if contract != expected:
        raise ValueError('QICK version or installation requirements changed. '
                         'A separate editable reinstall is required; file update refused.')
    spec = importlib.util.find_spec('qick')
    if not spec or Path(spec.origin).resolve() != library / 'qick/__init__.py':
        raise ValueError('Board Python no longer imports the selected QICK repository.')
    links = {}
    for directory in site.getsitepackages() + [site.getusersitepackages()]:
        link = Path(directory) / 'qick.egg-link'
        if link.is_file():
            entries = link.read_text(encoding='utf-8').splitlines()
            if not entries or (link.parent / entries[0]).resolve() != library:
                raise ValueError('Editable QICK link points to another repository.')
            links[str(link)] = digest(link)
    return {'contract': contract, 'egg_info': tree_hashes(library / 'qick.egg-info'),
            'egg_links': links}


def rewrite_pyro_cli(data, bitfile):
    """Replace one literal start_server(bitfile=...) without running the launcher."""
    encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
    text = data.decode(encoding)
    tree = ast.parse(text)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == 'start_server']
    if len(calls) != 1:
        raise ValueError('pyro_cli.py must contain exactly one start_server call.')
    arguments = [k.value for k in calls[0].keywords if k.arg == 'bitfile']
    if len(arguments) != 1 or not isinstance(arguments[0], ast.Constant) or not isinstance(arguments[0].value, str):
        raise ValueError('pyro_cli.py bitfile must be a single string literal; update refused.')
    value = arguments[0]
    # AST columns count UTF-8 bytes. Preserve the original encoding, comments and
    # line endings (including the existing board's CR/CRLF combinations).
    lines = re.findall(r'[^\r\n]*(?:\r\n|\r|\n|$)', text)
    def offset(row, column):
        prefix = lines[row - 1].encode('utf-8')[:column].decode('utf-8')
        return sum(len(line) for line in lines[:row - 1]) + len(prefix)
    start = offset(value.lineno, value.col_offset)
    end = offset(value.end_lineno, value.end_col_offset)
    changed = (text[:start] + repr(bitfile) + text[end:]).encode(encoding)
    compile(changed, 'pyro_cli.py', 'exec')  # Syntax only; no imports or outputs.
    return changed, value.value


def prepare_launcher(stage, package, bitfile):
    original = child(package, 'pyro_cli.py').read_bytes()
    changed, previous = rewrite_pyro_cli(original, str(bitfile))
    (stage / 'launcher_before.py').write_bytes(original)
    (stage / 'payload/qick_lib/qick/pyro_cli.py').write_bytes(changed)
    return {'relative': 'qick_lib/qick/pyro_cli.py', 'before_bitfile': previous,
            'after_bitfile': str(bitfile),
            'before_sha256': hashlib.sha256(original).hexdigest(),
            'after_sha256': hashlib.sha256(changed).hexdigest()}


def check_launcher(stage, patch, bitfile, original_package_hashes):
    if patch['relative'] != 'qick_lib/qick/pyro_cli.py' or patch['after_bitfile'] != str(bitfile):
        raise ValueError('Prepared launcher BIT path differs from the firmware target.')
    original = (stage / 'launcher_before.py').read_bytes()
    if (hashlib.sha256(original).hexdigest() != patch['before_sha256']
            or original_package_hashes.get('pyro_cli.py') != patch['before_sha256']):
        raise ValueError('Original board launcher hash changed.')
    changed, previous = rewrite_pyro_cli(original, str(bitfile))
    if previous != patch['before_bitfile'] or hashlib.sha256(changed).hexdigest() != patch['after_sha256']:
        raise ValueError('Prepared launcher modification changed.')
    return changed


def validate_manifest(manifest):
    if (manifest.get('format') != 4 or manifest.get('library_scope') != 'qick-package-only'
            or manifest.get('launcher_update') != 'existing-pyro-cli-bitfile-only'
            or manifest.get('firmware_scope') != 'entire-directory'):
        raise ValueError('This package predates installation-metadata preservation. '
                         'Review and prepare a new package with launcher path synchronization.')
    if not isinstance(manifest.get('installation_contract'), dict):
        raise ValueError('Missing editable-installation metadata contract.')
    names = set(manifest['files'])
    bit = PurePosixPath(manifest['active_firmware'])
    if bit.is_absolute() or '..' in bit.parts or bit.suffix != '.bit':
        raise ValueError('Invalid active firmware path.')
    required = {'qick_lib/qick/__init__.py', 'qick_lib/qick/VERSION', 'qick_lib/qick/pyro_cli.py',
                'firmware/' + str(bit), 'firmware/' + str(bit.with_suffix('.hwh'))}
    if not required <= names or any(
            not name.startswith(('qick_lib/qick/', 'firmware/')) for name in names):
        raise ValueError('Payload must contain only the QICK package and firmware directory.')


def check_payload(stage, manifest, launcher=None):
    validate_manifest(manifest)
    payload = stage / 'payload'
    actual = {p.relative_to(payload).as_posix() for p in payload.rglob('*') if p.is_file()}
    if actual != set(manifest['files']):
        raise ValueError('Payload file list differs from the reviewed manifest.')
    for name, info in manifest['files'].items():
        p = child(payload, name)
        if launcher and name == launcher['relative']:
            if digest(p) != launcher['after_sha256']:
                raise ValueError('Prepared launcher hash mismatch.')
            continue
        if p.stat().st_size != info['bytes'] or digest(p) != info['sha256']:
            raise ValueError('Payload hash mismatch: ' + name)
    version = (payload / 'qick_lib/qick/VERSION').read_text(encoding='utf-8').strip()
    if version != manifest['library_version'] or version != manifest['installation_contract']['version']:
        raise ValueError('Payload version differs from the retained installation metadata.')
    for p in (payload / 'qick_lib').rglob('*.py'):
        compile(p.read_bytes(), str(p), 'exec')  # In memory; never import the payload.


def targets(root, request):
    bit = child(root, request['remote_bit'])
    if not request['remote_bit'].startswith('qick/firmware/') or bit.suffix != '.bit':
        raise ValueError('Firmware target must be a .bit below qick/firmware/.')
    hwh = child(root, PurePosixPath(request['remote_bit']).with_suffix('.hwh').as_posix())
    return [child(root, 'qick/qick_lib/qick'), child(root, 'qick/firmware')]


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
                            'launcher_patch': data.get('launcher_patch'),
                            'firmware': data.get('remote_bit'),
                            'identity': hashlib.sha256(json.dumps(package, sort_keys=True).encode()).hexdigest(),
                            'library_version': package['library_version'],
                            'firmware_timestamp': package['firmware_timestamp']})
    runtime = {'queried': False, 'known_server_processes': server_processes(),
               'manual_stop_confirmation_required': True,
               'note': 'File updates use SSH only. Runtime firmware verification is optional.'}
    return {'repository': str(root), 'python': sys.executable,
            'python_version': sys.version.split()[0], 'qick_import_path': spec.origin if spec else None,
            'installation_contract': installation_contract(child(root, 'qick/qick_lib')),
            'free_bytes': shutil.disk_usage(str(root)).free, 'runtime': runtime,
            'transactions': records, 'update_lock_exists': (root / '.qick_gui_update.lock').exists()}


def main(request):
    root = root_path(request)
    action = request['action']
    if action == 'inspect':
        return inspect(request, root)
    if action == 'check_stopped':
        stopped(request)
        return {'manual_confirmation_received': True, 'known_server_processes': []}
    stage = transaction(root, request)
    if action == 'reserve':
        stage.mkdir(parents=True, exist_ok=False)
        return {'stage': str(stage)}
    if action == 'prepare':
        manifest = json.loads((stage / 'manifest.json').read_text())
        validate_manifest(manifest)
        retained_installation = installation_state(root, manifest['installation_contract'])
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
        active = child(root, request['remote_bit'])
        if request['remote_bit'] != 'qick/firmware/' + manifest['active_firmware']:
            raise ValueError('Launcher target must match the reviewed firmware project.')
        launcher = prepare_launcher(stage, paths[0], active)
        journal = {'state': 'prepared', 'remote_repo': str(root), 'remote_bit': request['remote_bit'],
                   'targets': [str(p) for p in paths], 'before': [tree_hashes(p) for p in paths],
                   'launcher_patch': launcher,
                   'retained_installation': retained_installation,
                   'manifest_sha256': digest(stage / 'manifest.json'), 'installed': []}
        save(stage / 'journal.json', journal)
        return {'release': request['release'], 'state': 'prepared',
                'stage': str(stage),
                'launcher_patch': launcher,
                'firmware': request['remote_bit'], 'files': len(manifest['files'])}
    journal = json.loads((stage / 'journal.json').read_text())
    manifest = json.loads((stage / 'manifest.json').read_text())
    validate_manifest(manifest)
    if digest(stage / 'manifest.json') != journal['manifest_sha256']:
        raise ValueError('Prepared manifest was changed.')
    paths = targets(root, request)
    if [str(p) for p in paths] != journal['targets']:
        raise ValueError('Target changed after preparation.')
    if request['remote_bit'] != 'qick/firmware/' + manifest['active_firmware']:
        raise ValueError('Launcher target differs from the reviewed firmware project.')
    launcher_bytes = check_launcher(stage, journal['launcher_patch'], child(root, request['remote_bit']), journal['before'][0])
    # The same mutex protects verification and replacement from concurrent GUI actions.
    if action not in ('verify', 'apply', 'rollback'):
        raise ValueError('Unsupported action.')
    lock = child(root, '.qick_gui_update.lock')
    lock.mkdir(exist_ok=False)
    try:
        if installation_state(root, manifest['installation_contract']) != journal['retained_installation']:
            raise ValueError('Editable installation changed after preparation. Prepare again.')
        if action == 'verify':
            if journal['state'] not in ('files_updated_restart_required', 'applied'):
                raise ValueError('This transaction has not been installed.')
            if [tree_hashes(p) for p in paths] != journal['after']:
                raise ValueError('Installed files changed since the update.')
            if child(paths[0], 'pyro_cli.py').read_bytes() != launcher_bytes:
                raise ValueError('Installed launcher differs from the selected BIT path.')
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
            if installation_state(root, manifest['installation_contract']) != journal['retained_installation']:
                raise ValueError('Editable installation changed during restore.')
            journal['state'] = 'rolled_back_restart_required'
            save(stage / 'journal.json', journal)
            return {'state': journal['state'], 'release': request['release']}
        check_payload(stage, manifest, journal['launcher_patch'])
        if (stage / 'payload/qick_lib/qick/pyro_cli.py').read_bytes() != launcher_bytes:
            raise ValueError('Prepared launcher differs from the selected BIT path.')
        (stage / 'backup').mkdir(exist_ok=False)
        sources = [stage / 'payload/qick_lib/qick', stage / 'payload/firmware']
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
            if installation_state(root, manifest['installation_contract']) != journal['retained_installation']:
                raise ValueError('Editable installation changed during update.')
            journal.update(state='files_updated_restart_required', after=after, installed_at=time.time())
            save(stage / 'journal.json', journal)
            return {'state': journal['state'], 'release': request['release']}
        except Exception as exc:
            try:
                stopped(request)
                restore_files(stage, journal)
                if installation_state(root, manifest['installation_contract']) != journal['retained_installation']:
                    raise ValueError('Editable installation changed during recovery.')
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
