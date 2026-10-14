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


def review_package(repo, manifest_path):
    """Read-only local review. Never invoke repository scripts or pip."""
    repo, manifest_path = Path(repo).resolve(), Path(manifest_path).resolve()
    library = repo / 'qick/qick_lib'
    package = library / 'qick'
    if not (package / '__init__.py').is_file():
        raise ValueError('Select a QSTL_QICK repository containing qick/qick_lib/qick.')
    build = json.loads(manifest_path.read_text(encoding='utf-8'))
    timing = build.get('timing', {})
    if timing.get('timing_closed') != 'YES':
        raise ValueError('The firmware manifest does not report timing closure.')
    topology = build.get('topology', {})
    if topology.get('passed') is not True or not topology.get('pairs'):
        raise ValueError('A validated v4 output-routing manifest is required.')
    records = {PureWindowsPath(v['path']).name: v for v in build['artifacts']}
    artifacts = {}
    for name in ('bitstream.bit', 'bitstream.hwh', 'bitstream.xsa'):
        p = manifest_path.parent / name
        expected = records.get(name, {})
        if not p.is_file() or p.stat().st_size != expected.get('bytes') or sha(p) != expected.get('sha256'):
            raise ValueError('Firmware does not match build_manifest.json: ' + name)
        artifacts[name] = p
    with zipfile.ZipFile(artifacts['bitstream.xsa']) as z:
        for kind in ('bit', 'hwh'):
            member = build['xsa_members'][kind]
            h = hashlib.sha256()
            with z.open(member) as f:
                for block in iter(lambda: f.read(1024 * 1024), b''):
                    h.update(block)
            if h.hexdigest() != records['bitstream.' + kind]['sha256']:
                raise ValueError('BIT/HWH are not the pair from the recorded XSA.')
    hwh = ET.parse(artifacts['bitstream.hwh']).getroot()
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
    for p in sorted(library.rglob('*')):
        if '__pycache__' in p.parts or p.suffix in ('.pyc', '.pyo') or any(
                part.endswith('.egg-info') for part in p.parts):
            continue
        if p.is_symlink():
            raise ValueError('Symlink in qick_lib: ' + str(p))
        if p.is_file():
            files['qick_lib/' + p.relative_to(library).as_posix()] = p
    files.update({'firmware/' + name: artifacts[name] for name in ('bitstream.bit', 'bitstream.hwh')})
    hashes = {name: {'bytes': p.stat().st_size, 'sha256': sha(p)} for name, p in files.items()}
    pairs = []
    for pair in topology['pairs']:
        pairs.append({'fullpath': pair['awg'], 'type': 'axis_awg_tuning_v3', 'dac': pair['dac'],
                      'output_sum_block': pair['route']['output_sum_block'],
                      'output_sum_role': 'awg'})
        if pair['rf']:
            pairs.append({'fullpath': pair['rf'], 'type': 'axis_signal_gen_v6', 'dac': pair['dac'],
                          'output_sum_block': pair['route']['output_sum_block'],
                          'output_sum_role': 'rf'})
    data = {'format': 1, 'library_version': (package / 'VERSION').read_text().strip(),
            'firmware_timestamp': timestamp, 'generators': pairs,
            'build_manifest_sha256': sha(manifest_path), 'files': hashes,
            'library_source_hashes': local_sources}
    identity = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    return {'repo': str(repo), 'manifest_path': str(manifest_path), 'identity': identity,
            'manifest': data, 'files': {k: str(v) for k, v in files.items()},
            'total_bytes': sum(v['bytes'] for v in hashes.values()),
            'file_count': len(files), 'setup_wns_ns': timing.get('setup_wns_ns'),
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
        current = review_package(reviewed['repo'], reviewed['manifest_path'])
        if current['identity'] != reviewed['identity']:
            raise ValueError('Local package changed after review. Review it again.')
        info = self.inspect()
        expected_import = info['repository'] + '/qick/qick_lib/qick/__init__.py'
        if info['qick_import_path'] != expected_import:
            raise ValueError('Board Python imports another QICK library: ' + str(info['qick_import_path']))
        if info['free_bytes'] < current['total_bytes'] * 3 + 256 * 1024 * 1024:
            raise ValueError('Insufficient board disk space for staging and backups.')
        release = uuid.uuid4().hex
        remote_stage = self.remote('reserve', release=release)['stage']
        with tempfile.TemporaryDirectory(prefix='qick-update-') as folder:
            folder = Path(folder)
            archive = folder / 'payload.zip'
            manifest = folder / 'manifest.json'
            manifest.write_text(json.dumps(current['manifest'], indent=2), encoding='utf-8')
            self.progress('Packaging the reviewed library and matching BIT/HWH.')
            with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as z:
                for name, source in current['files'].items():
                    if sha(source) != current['manifest']['files'][name]['sha256']:
                        raise ValueError('Local source changed while packaging: ' + name)
                    z.write(source, name)
            with self.client.open_sftp() as sftp:
                sftp.get_channel().settimeout(60)
                self.progress('Uploading staged payload. Running files are unchanged.')
                sftp.put(str(manifest), remote_stage + '/manifest.json')
                sftp.put(str(archive), remote_stage + '/payload.zip')
            result = self.remote('prepare', release=release, archive_sha256=sha(archive))
        result.update(identity=current['identity'], manifest=current['manifest'])
        return result

    def apply(self, release, server_stopped=False):
        return self.remote('apply', release=release, server_stopped=server_stopped)

    def rollback(self, release, server_stopped=False):
        return self.remote('rollback', release=release, server_stopped=server_stopped)

    def verify(self, release):
        return self.remote('verify', release=release)
