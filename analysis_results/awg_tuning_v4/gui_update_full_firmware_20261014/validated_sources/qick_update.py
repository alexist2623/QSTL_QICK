"""Explicit, user-triggered QICK library/firmware deployment operations.

Importing this module performs no network, package installation, or device I/O.
Paramiko is an optional dependency, imported only by an SSH action.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import shlex
import stat
import tempfile
import uuid
import xml.etree.ElementTree as ET
import zipfile

try:
    from .qick_update_remote import installation_contract
except ImportError:
    from qick_update_remote import installation_contract


@dataclass(frozen=True)
class UpdateConnection:
    host: str
    username: str = 'root'
    port: int = 22
    password: str = field(default='', repr=False)
    remote_repo: str = '/home/QSTL_QICK'
    python: str = '/usr/local/share/pynq-venv/bin/python3'
    remote_bit: str = 'qick/firmware/projects/qstl_awg_v4/bitstream.bit'
    ns_port: int = 8888
    proxy_name: str = 'myqick'

    def request(self, action, **kwargs):
        if not self.host.strip() or not self.username.strip():
            raise ValueError('Host and SSH user are required.')
        if not 1 <= self.port <= 65535 or not 1 <= self.ns_port <= 65535:
            raise ValueError('Port must be between 1 and 65535.')
        if not PurePosixPath(self.python).is_absolute():
            raise ValueError('Board Python must be an absolute Linux path.')
        result = {key: getattr(self, key) for key in (
            'host', 'remote_repo', 'remote_bit', 'ns_port', 'proxy_name')}
        result.update(action=action, **kwargs)
        return result


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def source_hashes(root):
    result = {}
    for p in sorted(root.rglob('*')):
        if '__pycache__' in p.parts or p.suffix in ('.pyc', '.pyo'):
            continue
        if p.is_symlink():
            raise ValueError('Symlink in update library: ' + str(p))
        if p.is_file() and (p.suffix == '.py' or p.name == 'VERSION'):
            result[p.relative_to(root).as_posix()] = sha(p)
    return result


def repository_root(path):
    path = Path(path).resolve()
    if path.name == 'qick' and (path / 'qick_lib/qick/__init__.py').is_file():
        return path.parent
    return path


def firmware_versions(repo):
    """List local BIT/HWH pairs without connecting to the board or loading firmware."""
    folder = repository_root(repo) / 'qick/firmware'
    versions = []
    for bit in sorted(folder.rglob('*.bit')):
        hwh = bit.with_suffix('.hwh')
        if not hwh.is_file() or bit.is_symlink() or hwh.is_symlink():
            continue
        if bit.resolve() != bit or hwh.resolve() != hwh:
            continue
        relative = bit.relative_to(folder).as_posix()
        label = relative.removeprefix('projects/')
        if bit.name == 'bitstream.bit':
            label = str(PurePosixPath(label).parent)
        versions.append({'label': label, 'bit': relative,
                         'has_manifest': (bit.parent / 'build_manifest.json').is_file()})
    return versions


def review_package(repo, manifest_path=None, *, active_firmware=None):
    """Read-only local review. Never invoke repository scripts or pip."""
    repo = repository_root(repo)
    firmware = repo / 'qick/firmware'
    if active_firmware is None:
        active_firmware = ((Path(manifest_path).resolve().parent / 'bitstream.bit')
                           .relative_to(firmware).as_posix() if manifest_path else
                           'projects/qstl_awg_v4/bitstream.bit')
    relative = PurePosixPath(active_firmware)
    if relative.is_absolute() or '..' in relative.parts or relative.suffix != '.bit' or '\\' in active_firmware:
        raise ValueError('Select a BIT/HWH pair inside qick/firmware.')
    bit = firmware.joinpath(*relative.parts)
    hwh_path = bit.with_suffix('.hwh')
    if any(p.resolve() != p or not p.is_file() for p in (bit, hwh_path)):
        raise ValueError('Selected BIT/HWH pair is missing or contains a symlink.')
    manifest_path = Path(manifest_path).resolve() if manifest_path else bit.parent / 'build_manifest.json'
    if manifest_path.parent != bit.parent:
        raise ValueError('Build manifest must belong to the selected firmware folder.')
    library = repo / 'qick/qick_lib'
    package = library / 'qick'
    if not (package / '__init__.py').is_file():
        raise ValueError('Select a QSTL_QICK repository containing qick/qick_lib/qick.')
    build = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.is_file() else {}
    timing = build.get('timing', build.get('build_result', {}))
    if build and timing.get('timing_closed') != 'YES':
        raise ValueError('The firmware manifest does not report timing closure.')
    topology = build.get('topology', {})
    if 'qstl_awg_v4' in relative.parts and (topology.get('passed') is not True or not topology.get('pairs')):
        raise ValueError('A validated v4 output-routing manifest is required.')
    if build:
        records = {PureWindowsPath(v['path']).name: v for v in build['artifacts']}
        for p in (bit, hwh_path, bit.with_suffix('.xsa')):
            expected = records.get(p.name, {})
            if not p.is_file() or p.stat().st_size != expected.get('bytes') or sha(p) != expected.get('sha256'):
                raise ValueError('Firmware does not match build_manifest.json: ' + p.name)
        with zipfile.ZipFile(bit.with_suffix('.xsa')) as z:
            for p in (bit, hwh_path):
                matched = False
                for member in z.namelist():
                    if not member.endswith(p.suffix):
                        continue
                    h = hashlib.sha256()
                    with z.open(member) as f:
                        for block in iter(lambda: f.read(1024 * 1024), b''):
                            h.update(block)
                    matched = matched or h.hexdigest() == records[p.name]['sha256']
                if not matched:
                    raise ValueError('BIT/HWH are not the pair from the recorded XSA.')
    hwh = ET.parse(hwh_path).getroot()
    timestamp = hwh.attrib.get('TIMESTAMP')
    if not timestamp:
        raise ValueError('HWH firmware timestamp is missing.')
    spec = importlib.util.find_spec('qick')
    loaded = Path(spec.origin).parent if spec and spec.origin else None
    local_sources = source_hashes(package)
    if not loaded or source_hashes(loaded) != local_sources:
        raise ValueError('The GUI Python environment is not using this QICK library. '
                         'Install/select the matching local library and restart the GUI first.')
    files = {}
    contract = installation_contract(library)
    for p in sorted(package.rglob('*')):
        if '__pycache__' in p.parts or p.suffix in ('.pyc', '.pyo') or any(
                part.endswith('.egg-info') for part in p.parts):
            continue
        if p.is_symlink():
            raise ValueError('Symlink in qick_lib: ' + str(p))
        if p.is_file():
            files['qick_lib/' + p.relative_to(library).as_posix()] = p
    firmware_files = {}
    for p in sorted(firmware.rglob('*')):
        if '__pycache__' in p.parts or p.suffix in ('.pyc', '.pyo'):
            continue
        if p.is_symlink():
            raise ValueError('Symlink in firmware directory: ' + str(p))
        if p.is_file():
            firmware_files['firmware/' + p.relative_to(firmware).as_posix()] = p
    files.update(firmware_files)
    hashes = {name: {'bytes': p.stat().st_size, 'sha256': sha(p)} for name, p in files.items()}
    pairs = []
    for pair in topology.get('pairs', []):
        pairs.append({'fullpath': pair['awg'], 'type': 'axis_awg_tuning_v3', 'dac': pair['dac'],
                      'output_sum_block': pair['route']['output_sum_block'],
                      'output_sum_role': 'awg'})
        if pair['rf']:
            pairs.append({'fullpath': pair['rf'], 'type': 'axis_signal_gen_v6', 'dac': pair['dac'],
                          'output_sum_block': pair['route']['output_sum_block'],
                          'output_sum_role': 'rf'})
    data = {'format': 4, 'library_scope': 'qick-package-only',
            'firmware_scope': 'entire-directory', 'active_firmware': active_firmware,
            'launcher_update': 'existing-pyro-cli-bitfile-only',
            'installation_contract': contract,
            'library_version': (package / 'VERSION').read_text().strip(),
            'firmware_timestamp': timestamp, 'generators': pairs,
            'build_manifest_sha256': sha(manifest_path) if build else None,
            'firmware_validation': 'build_manifest_and_xsa' if build else 'file_pair_only',
            'files': hashes,
            'library_source_hashes': local_sources}
    identity = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    return {'repo': str(repo), 'manifest_path': str(manifest_path), 'identity': identity,
            'manifest': data, 'files': {k: str(v) for k, v in files.items()},
            'total_bytes': sum(v['bytes'] for v in hashes.values()),
            'file_count': len(files), 'setup_wns_ns': timing.get('setup_wns_ns'),
            'firmware_file_count': len(firmware_files),
            'firmware_bytes': sum(p.stat().st_size for p in firmware_files.values()),
            'hold_whs_ns': timing.get('hold_whs_ns')}


class BoardUpdater:
    def __init__(self, connection, progress=None):
        self.connection = connection
        self.progress = progress or (lambda text: None)
        self.client = None

    def __enter__(self):
        try:
            import paramiko
        except ImportError as exc:
            raise RuntimeError('SSH updates require Paramiko in the GUI environment. '
                               'Install requirements-updater.txt before using SSH actions.') from exc
        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        known = Path.home() / '.ssh/known_hosts'
        if known.is_file():
            self.client.load_host_keys(str(known))
        self.client.set_missing_host_key_policy(paramiko.RejectPolicy())
        try:
            self.client.connect(self.connection.host, port=self.connection.port,
                                username=self.connection.username,
                                password=self.connection.password or None,
                                look_for_keys=True, allow_agent=True,
                                timeout=10, auth_timeout=15, banner_timeout=10)
        except Exception:
            self.client.close()
            raise
        self.progress('SSH connected; host key verified against known_hosts.')
        return self

    def __exit__(self, *_args):
        if self.client:
            self.client.close()

    def remote(self, action, **kwargs):
        request = self.connection.request(action, **kwargs)
        encoded = base64.b64encode(json.dumps(request).encode()).decode('ascii')
        helper = Path(__file__).with_name('qick_update_remote.py').read_text(encoding='utf-8-sig')
        command = ' '.join(shlex.quote(v) for v in (self.connection.python, '-c', helper, encoded))
        stdin, stdout, stderr = self.client.exec_command(command, timeout=600)
        stdin.close()
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        status = stdout.channel.recv_exit_status()
        try:
            result = json.loads(output.strip().splitlines()[-1])
        except (ValueError, IndexError) as exc:
            raise RuntimeError('Board helper returned no valid result. ' + error[-1500:]) from exc
        if status != 0 or not result.get('ok'):
            raise RuntimeError(result.get('error', error or 'Board update failed.'))
        return result['result']

    def inspect(self):
        return self.remote('inspect')

    def list_directories(self, path):
        """Read one directory on demand; never create a directory while browsing."""
        requested = PurePosixPath(path)
        if not requested.is_absolute() or '..' in requested.parts:
            raise ValueError('Enter an absolute Linux folder path.')
        if path != '/' and requested.parts[1] not in ('home', 'root'):
            raise ValueError('Browse below /home or /root.')
        with self.client.open_sftp() as sftp:
            sftp.get_channel().settimeout(20)
            resolved = sftp.normalize(path)
            if resolved != requested.as_posix():
                raise ValueError('Choose a real directory, not a symbolic link.')
            directories = []
            for entry in sftp.listdir_attr(resolved):
                if stat.S_ISDIR(entry.st_mode):
                    if resolved != '/' or entry.filename in ('home', 'root'):
                        directories.append(entry.filename)
            return {'path': resolved, 'directories': sorted(directories)}

    def prepare(self, reviewed):
        current = review_package(reviewed['repo'], reviewed['manifest_path'],
                                 active_firmware=reviewed['manifest']['active_firmware'])
        if current['identity'] != reviewed['identity']:
            raise ValueError('Local package changed after review. Review it again.')
        info = self.inspect()
        expected_import = info['repository'] + '/qick/qick_lib/qick/__init__.py'
        if info['qick_import_path'] != expected_import:
            raise ValueError('Board Python imports another QICK library: ' + str(info['qick_import_path']))
        if info.get('installation_contract') != current['manifest']['installation_contract']:
            raise ValueError('Board installation metadata differs from the local package. '
                             'A separate editable reinstall is required before a file update.')
        if info['free_bytes'] < current['total_bytes'] * 3 + 256 * 1024 * 1024:
            raise ValueError('Insufficient board disk space for staging and backups.')
        release = uuid.uuid4().hex
        remote_stage = self.remote('reserve', release=release)['stage']
        with tempfile.TemporaryDirectory(prefix='qick-update-') as folder:
            folder = Path(folder)
            archive = folder / 'payload.zip'
            manifest = folder / 'manifest.json'
            manifest.write_text(json.dumps(current['manifest'], indent=2), encoding='utf-8')
            self.progress('Packaging the QICK library and entire firmware folder.')
            with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as z:
                for name, source in current['files'].items():
                    if sha(source) != current['manifest']['files'][name]['sha256']:
                        raise ValueError('Local source changed while packaging: ' + name)
                    z.write(source, name)
            with self.client.open_sftp() as sftp:
                sftp.get_channel().settimeout(60)
                total = manifest.stat().st_size + archive.stat().st_size
                sent = 0
                for source, name in ((manifest, 'manifest.json'), (archive, 'payload.zip')):
                    offset = sent
                    def transferred(current, _size, offset=offset):
                        self.progress({'phase': 'upload', 'completed': offset + current,
                                       'total': total, 'text': 'Uploading library and entire firmware folder'})
                    sftp.put(str(source), remote_stage + '/' + name, callback=transferred)
                    sent += source.stat().st_size
            self.progress({'phase': 'verify_upload', 'text': 'Checking uploaded files and preparing the server BIT path'})
            result = self.remote('prepare', release=release, archive_sha256=sha(archive))
        result.update(identity=current['identity'], manifest=current['manifest'])
        return result

    def update(self, reviewed, server_stopped=False):
        """One explicit UI action, with manual stop confirmation and retained backups."""
        self.remote('check_stopped', server_stopped=server_stopped)
        self.progress({'phase': 'prepare', 'text': 'Checking board paths and packaging all files'})
        prepared = self.prepare(reviewed)
        self.progress({'phase': 'apply', 'text': 'Backing up and replacing the library and firmware folder'})
        result = self.apply(prepared['release'], server_stopped=server_stopped)
        result.update(launcher_patch=prepared['launcher_patch'],
                      backup_directory=prepared.get('stage'))
        return result

    def apply(self, release, server_stopped=False):
        return self.remote('apply', release=release, server_stopped=server_stopped)

    def rollback(self, release, server_stopped=False):
        return self.remote('rollback', release=release, server_stopped=server_stopped)

    def verify(self, release):
        # Optional read-only RPC uses the GUI's Pyro4, never the SSH account's site-packages.
        import Pyro4
        Pyro4.config.COMMTIMEOUT = 4
        Pyro4.config.SERIALIZER = 'pickle'
        Pyro4.config.PICKLE_PROTOCOL_VERSION = 4
        with Pyro4.locateNS(host=self.connection.host, port=self.connection.ns_port) as ns:
            uri = ns.lookup(self.connection.proxy_name)
        with Pyro4.Proxy(uri) as soc:
            cfg = soc.get_cfg()
        identity = {'host': uri.host, 'port': uri.port,
                    'config': {key: cfg.get(key) for key in ('board', 'sw_version', 'fw_timestamp')}}
        identity['config']['gens'] = [{key: g.get(key) for key in (
            'fullpath', 'type', 'dac', 'output_sum_block', 'output_sum_role')}
            for g in cfg.get('gens', [])]
        return self.remote('verify', release=release, runtime_identity=identity)
