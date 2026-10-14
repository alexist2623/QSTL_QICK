"""Offline updater UI and version-selection checks; board operations are fakes."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import time
import zipfile

import pytest
from PyQt5 import QtCore, QtWidgets
import qick_update as update
import qick_update_dialog as ui


@pytest.fixture(scope='module')
def app():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


@pytest.fixture
def repo(tmp_path, monkeypatch):
    repo = tmp_path / 'QSTL_QICK'
    library = repo / 'qick/qick_lib'
    package = library / 'qick'
    package.mkdir(parents=True)
    (package / '__init__.py').write_text('# fixture\n')
    (package / 'VERSION').write_text('0.2.357\n')
    (package / 'pyro_cli.py').write_text('start_server(bitfile="old.bit")\n')
    metadata = library / 'qick.egg-info'
    metadata.mkdir()
    (metadata / 'PKG-INFO').write_text('Name: qick\nVersion: 0.2.357\nRequires-Python: >=3.6, <4\n')
    (metadata / 'requires.txt').write_text('numpy\n')
    firmware = repo / 'qick/firmware'
    for version in ('qstl_awg_v2', 'qstl_awg_v3'):
        folder = firmware / 'projects' / version
        folder.mkdir(parents=True)
        (folder / 'bitstream.bit').write_bytes(version.encode())
        (folder / 'bitstream.hwh').write_text('<SYSTEM TIMESTAMP="test timestamp"/>')
    (firmware / 'unpaired.bit').write_bytes(b'missing hwh')
    (firmware / '__pycache__').mkdir()
    (firmware / '__pycache__/not-source.pyc').write_bytes(b'cache')
    monkeypatch.setattr(update.importlib.util, 'find_spec', lambda _: SimpleNamespace(origin=str(package / '__init__.py')))
    return repo


def test_discovery_normalizes_qick_and_ignores_unpaired(repo):
    versions = update.firmware_versions(repo)
    assert versions == update.firmware_versions(repo / 'qick')
    assert [v['label'] for v in versions] == ['qstl_awg_v2', 'qstl_awg_v3']


def test_review_selected_version_copies_whole_firmware(repo):
    active = 'projects/qstl_awg_v2/bitstream.bit'
    reviewed = update.review_package(repo / 'qick', active_firmware=active)
    manifest = reviewed['manifest']
    assert manifest['format'] == 4
    assert manifest['active_firmware'] == active
    assert manifest['firmware_validation'] == 'file_pair_only'
    assert 'firmware/projects/qstl_awg_v3/bitstream.bit' in reviewed['files']
    assert 'firmware/unpaired.bit' in reviewed['files']
    assert not any('__pycache__' in p or '.egg-info' in p for p in reviewed['files'])


@pytest.mark.parametrize('schema', ['old', 'v3', 'v4'])
def test_build_manifest_schemas_and_xsa_pair(repo, schema):
    folder = repo / 'qick/firmware/projects/qstl_awg_v3'
    if schema == 'v4':
        folder.rename(folder.with_name('qstl_awg_v4'))
        folder = folder.with_name('qstl_awg_v4')
    with zipfile.ZipFile(folder / 'bitstream.xsa', 'w') as z:
        z.write(folder / 'bitstream.bit', 'generated.bit')
        z.write(folder / 'bitstream.hwh', 'd_1.hwh')
    artifacts = [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': update.sha(p)}
                 for p in folder.iterdir() if p.suffix in ('.bit', '.hwh', '.xsa')]
    build = {'artifacts': artifacts,
             'timing' if schema == 'v4' else 'build_result': {'timing_closed': 'YES'}}
    if schema == 'v4':
        build['topology'] = {'passed': True, 'pairs': [
            {'awg': 'awg', 'rf': 'rf', 'dac': '00', 'route': {'output_sum_block': 'sum'}}]}
        build['xsa_members'] = {'bit': 'generated.bit', 'hwh': 'd_1.hwh'}
    elif schema == 'v3':
        build['xsa_members'] = {'.bit': ['generated.bit'], '.hwh': ['d_1.hwh']}
    (folder / 'build_manifest.json').write_text(json.dumps(build))
    selected = 'projects/' + folder.name + '/bitstream.bit'
    assert update.review_package(repo, active_firmware=selected)['manifest']['firmware_validation'] == 'build_manifest_and_xsa'
    (folder / 'bitstream.bit').write_bytes(b'tampered')
    with pytest.raises(ValueError, match='does not match'):
        update.review_package(repo, active_firmware=selected)


@pytest.mark.parametrize('selected', ['../escape.bit', '/absolute.bit', 'projects\\escape.bit', 'projects/missing.bit'])
def test_invalid_firmware_selection_refused(repo, selected):
    with pytest.raises(ValueError):
        update.review_package(repo, active_firmware=selected)


def test_v4_requires_successful_topology(repo):
    source = repo / 'qick/firmware/projects/qstl_awg_v3'
    source.rename(source.with_name('qstl_awg_v4'))
    with pytest.raises(ValueError, match='validated v4'):
        update.review_package(repo, active_firmware='projects/qstl_awg_v4/bitstream.bit')


@pytest.fixture
def dialog(app, repo):
    dialog = ui.QickUpdateDialog()
    dialog.repo.setText(str(repo))
    dialog._scan_timer.stop()
    dialog._load_versions()
    yield dialog
    assert not dialog._busy
    dialog.close()
    dialog.deleteLater()
    app.processEvents()


def test_dialog_has_one_update_action_and_selected_path(dialog):
    labels = [b.text() for b in dialog.findChildren(QtWidgets.QPushButton)]
    assert labels == ['Browse…', 'Browse board…', 'Update']
    dialog.firmware.setCurrentIndex(1)
    dialog.remote_repo.setText('/home/QSTL_QICK/qick')
    assert dialog._connection().remote_bit == 'qick/firmware/projects/qstl_awg_v3/bitstream.bit'
    assert '/home/QSTL_QICK/qick/firmware/projects/qstl_awg_v3/bitstream.bit' in dialog.path_summary.text()


@pytest.mark.parametrize('confirm', [False, True])
def test_update_requires_explicit_server_and_experiment_confirmation(dialog, monkeypatch, confirm):
    called, seen = [], []
    monkeypatch.setattr(dialog, '_start_update', lambda: called.append('update'))
    def answer():
        box = QtWidgets.QApplication.activeModalWidget()
        assert isinstance(box, ui.UpdateConfirmationDialog)
        seen.append(True)
        assert box.cancel.isDefault()
        assert not box.confirm.isEnabled()
        box.server_stopped.setChecked(True)
        assert not box.confirm.isEnabled()
        box.experiments_stopped.setChecked(True)
        assert box.confirm.isEnabled()
        if confirm:
            box.confirm.click()
        else:
            box.cancel.click()
    QtCore.QTimer.singleShot(10, answer)
    dialog.update_button.click()
    assert seen == [True]
    assert called == (['update'] if confirm else [])


def test_busy_experiment_cannot_start_update(dialog, monkeypatch):
    dialog._is_busy = lambda: True
    monkeypatch.setattr(dialog, '_start_update', lambda: pytest.fail('must not start'))
    dialog.update_button.click()
    assert 'current experiment' in dialog.status.text()


def test_transfer_progress_is_bytes_and_phase_specific(dialog):
    dialog._progress({'phase': 'upload', 'completed': 25, 'total': 100, 'text': 'Upload'})
    assert dialog.progress_bar.value() == 25
    assert dialog.progress_bar.format() == 'Upload %p%'
    dialog._progress({'phase': 'apply', 'text': 'Back up and replace'})
    assert dialog.progress_bar.maximum() == 0 and dialog._applying


@pytest.mark.parametrize('failure', [None, 'upload', 'apply'])
def test_worker_update_success_and_failure_signals(dialog, app, monkeypatch, failure):
    calls, changed = [], []
    class FakeUpdater:
        def __init__(self, connection, progress):
            self.connection, self.progress = connection, progress
        def __enter__(self):
            calls.append(self.connection.remote_bit)
            return self
        def __exit__(self, *args):
            pass
        def update(self, reviewed, server_stopped=False):
            assert server_stopped
            assert reviewed['manifest']['active_firmware'] == 'projects/qstl_awg_v2/bitstream.bit'
            self.progress({'phase': 'upload', 'text': 'Uploading', 'completed': 5, 'total': 10})
            if failure == 'upload':
                raise RuntimeError('test upload failure')
            self.progress({'phase': 'apply', 'text': 'Backing up and replacing'})
            if failure == 'apply':
                raise RuntimeError('test apply failure')
            return {'state': 'files_updated_restart_required', 'backup_directory': '/fake/backup'}
    monkeypatch.setattr(ui, 'BoardUpdater', FakeUpdater)
    monkeypatch.setattr(QtWidgets.QMessageBox, 'warning', lambda *args: None)
    dialog.board_changed.connect(changed.append)
    dialog._start_update()  # The confirmation is covered separately above.
    assert not dialog.update_button.isEnabled()
    deadline = time.monotonic() + 10
    while dialog._busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert not dialog._busy
    assert calls == ['qick/firmware/projects/qstl_awg_v2/bitstream.bit']
    assert changed == (['files_updated_restart_required'] if failure is None else
                       ['unknown_after_failure'] if failure == 'apply' else [])
    if failure is None:
        assert dialog.progress_bar.value() == 100
        assert 'manually' in dialog.status.text()


def test_one_action_sequence_checks_stop_before_prepare(monkeypatch):
    updater = update.BoardUpdater(update.UpdateConnection('fake'))
    actions = []
    monkeypatch.setattr(updater, 'remote', lambda action, **kwargs: actions.append((action, kwargs)))
    monkeypatch.setattr(updater, 'prepare', lambda reviewed: (
        actions.append(('prepare', reviewed)) or {'release': 'test', 'launcher_patch': {}, 'stage': '/backup'}))
    monkeypatch.setattr(updater, 'apply', lambda release, **kw: (
        actions.append(('apply', kw)) or {'state': 'files_updated_restart_required'}))
    updater.update({'fixture': True}, server_stopped=True)
    assert [a[0] for a in actions] == ['check_stopped', 'prepare', 'apply']
    assert actions[0][1]['server_stopped'] is True
