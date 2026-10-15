"""Transaction tests in disposable folders. No board/network access."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import zipfile
import pytest
import qick_update_remote as remote

VERSION = '0.2.357'

def hashes(path):
    return {p.relative_to(path).as_posix():p.read_bytes() for p in path.rglob('*') if p.is_file()}

@pytest.fixture
def fixture(tmp_path, monkeypatch):
    root = (tmp_path/'board'/'QSTL_QICK').resolve()
    library=root/'qick/qick_lib'; package=library/'qick'; package.mkdir(parents=True)
    (package/'__init__.py').write_text('VALUE = "before"\n')
    (package/'VERSION').write_text(VERSION+'\n')
    (package/'pyro_cli.py').write_bytes(b'# Board settings retained\r\nstart_server(ns_port=8888, iface="eth0", bitfile="/old/v2.bit")  # keep me\r\n')
    (package/'obsolete.py').write_text('OLD = True\n')
    metadata=library/'qick.egg-info'; metadata.mkdir()
    (metadata/'PKG-INFO').write_text('Metadata-Version: 2.1\nName: qick\nVersion: '+VERSION+'\nRequires-Python: >=3.6, <4\n')
    (metadata/'requires.txt').write_text('numpy\ntqdm\n')
    (metadata/'top_level.txt').write_text('qick\n')
    (metadata/'SOURCES.txt').write_text('old manifest intentionally retained\n')
    (library/'keep_me.txt').write_text('unrelated library-root file')
    site=tmp_path/'site-packages'; site.mkdir()
    (site/'qick.egg-link').write_text(str(library)+'\n../\n')
    (site/'easy-install.pth').write_text(str(library)+'\n')
    bit=root/'qick/firmware/test/bitstream.bit';bit.parent.mkdir(parents=True)
    bit.write_bytes(b'old bit');bit.with_suffix('.hwh').write_bytes(b'old hwh')
    request={'remote_repo':str(root),'remote_bit':'qick/firmware/test/bitstream.bit',
             'release':'1'*32,'server_stopped':True}
    monkeypatch.setattr(remote,'root_path',lambda r: root)
    monkeypatch.setattr(remote,'server_processes',lambda:[])
    monkeypatch.setattr(remote.importlib.util,'find_spec',lambda n:SimpleNamespace(origin=str(package/'__init__.py')))
    monkeypatch.setattr(remote.site,'getsitepackages',lambda:[str(site)])
    monkeypatch.setattr(remote.site,'getusersitepackages',lambda:str(tmp_path/'unused-site'))
    contract=remote.installation_contract(library)
    def stage(*, contract_change=None, extra=None, version=VERSION, format=4):
        remote.main(dict(request,action='reserve'))
        stage=root/'.qick_gui_updates'/request['release']
        files={'qick_lib/qick/__init__.py':b'VALUE = "after"\n',
               'qick_lib/qick/new_module.py':b'NEW = True\n',
               'qick_lib/qick/pyro_cli.py':b'start_server(ns_port=9999, bitfile="/local/default.bit")\n',
               'qick_lib/qick/VERSION':(version+'\n').encode(),
               'firmware/test/bitstream.bit':b'new bit','firmware/test/bitstream.hwh':b'new hwh',
               'firmware/other/bitstream.bit':b'other bit', 'firmware/other/bitstream.hwh':b'other hwh',
               'firmware/ip/rtl/logic.v':b'module logic; endmodule'}
        files.update(extra or {})
        manifest={'format':format,'library_scope':'qick-package-only',
                  'launcher_update':'existing-pyro-cli-bitfile-only',
                  'firmware_scope':'entire-directory','active_firmware':'test/bitstream.bit',
                  'library_version':VERSION,'installation_contract':dict(contract),
                  'files':{k:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for k,v in files.items()}}
        if contract_change:manifest['installation_contract'].update(contract_change)
        (stage/'manifest.json').write_text(json.dumps(manifest))
        with zipfile.ZipFile(stage/'payload.zip','w') as archive:
            for name,data in files.items():archive.writestr(name,data)
        request['archive_sha256']=remote.digest(stage/'payload.zip')
        return stage
    def run(action):return remote.main(dict(request,action=action))
    def imported_value():
        code='import site,sys;site.addsitedir(sys.argv[1]);import qick;from importlib.metadata import version;print(qick.VALUE+" "+version("qick"))'
        completed=subprocess.run([sys.executable,'-B','-S','-c',code,str(site)],
            capture_output=True,text=True,check=True,env=dict(os.environ,PYTHONPATH=''))
        return completed.stdout.strip()
    return SimpleNamespace(root=root,library=library,package=package,metadata=metadata,site=site,
        bit=bit,stage=stage,run=run,request=request,imported_value=imported_value)


def test_apply_rollback_preserves_editable_installation(fixture):
    f=fixture; old_package=hashes(f.package); old_metadata=hashes(f.metadata); old_site=hashes(f.site)
    metadata_inode=f.metadata.stat().st_ino; assert f.imported_value()=='before '+VERSION
    stage=f.stage();f.run('prepare')
    journal=json.loads((stage/'journal.json').read_text())
    assert journal['targets'][0]==str(f.package)
    assert f.run('apply')['state']=='files_updated_restart_required'
    assert f.imported_value()=='after '+VERSION
    launcher=(f.package/'pyro_cli.py').read_bytes()
    expected,previous=remote.rewrite_pyro_cli(old_package['pyro_cli.py'],str(f.bit))
    assert launcher==expected and previous=='/old/v2.bit'
    called=[]
    exec(compile(launcher,'fixture_launcher','exec'),{'start_server':lambda **kwargs:called.append(kwargs)})
    assert called==[{'ns_port':8888,'iface':'eth0','bitfile':str(f.bit)}]
    assert (f.package/'new_module.py').exists() and not (f.package/'obsolete.py').exists()
    assert hashes(f.metadata)==old_metadata and hashes(f.site)==old_site
    assert f.metadata.stat().st_ino==metadata_inode
    assert (f.library/'keep_me.txt').read_text()=='unrelated library-root file'
    assert f.run('rollback')['state']=='rolled_back_restart_required'
    assert hashes(f.package)==old_package and hashes(f.metadata)==old_metadata and hashes(f.site)==old_site
    assert f.imported_value()=='before '+VERSION


def test_failed_firmware_replace_restores_original_package_and_metadata(fixture,monkeypatch):
    f=fixture; before=hashes(f.library); site_before=hashes(f.site)
    stage=f.stage();f.run('prepare'); original=remote.os.replace
    source=stage/'payload/firmware'
    def fail_hwh(src,dst):
        if Path(src)==source:raise OSError('injected firmware rename failure')
        return original(src,dst)
    monkeypatch.setattr(remote.os,'replace',fail_hwh)
    with pytest.raises(RuntimeError,match='original files restored'):f.run('apply')
    assert hashes(f.library)==before and hashes(f.site)==site_before
    assert f.bit.read_bytes()==b'old bit' and f.bit.with_suffix('.hwh').read_bytes()==b'old hwh'
    assert json.loads((stage/'journal.json').read_text())['state']=='failed_restored_files'
    assert f.imported_value()=='before '+VERSION

@pytest.mark.parametrize('change',[{'version':'9.9'},{'requirements':['different-dependency']}])
def test_installation_contract_change_rejected_before_extract(fixture,change):
    f=fixture;before=hashes(f.library);stage=f.stage(contract_change=change)
    with pytest.raises(ValueError,match='separate editable reinstall'):f.run('prepare')
    assert not (stage/'payload').exists() and hashes(f.library)==before


def test_metadata_tampering_after_prepare_refused(fixture):
    f=fixture;stage=f.stage();f.run('prepare');before=hashes(f.package)
    (f.metadata/'SOURCES.txt').write_text('external metadata edit')
    with pytest.raises(ValueError,match='installation changed'):f.run('apply')
    assert hashes(f.package)==before and not (stage/'backup').exists()


def test_editable_link_retarget_after_prepare_refused(fixture):
    f=fixture;f.stage();f.run('prepare');before=hashes(f.package)
    (f.site/'qick.egg-link').write_text(str(f.root/'elsewhere')+'\n')
    with pytest.raises(ValueError,match='another repository'):f.run('apply')
    assert hashes(f.package)==before


def test_old_whole_library_manifest_refused(fixture):
    f=fixture;stage=f.stage(format=1)
    with pytest.raises(ValueError,match='predates installation-metadata'):f.run('prepare')
    assert not (stage/'payload').exists()


def test_payload_cannot_overwrite_installation_metadata(fixture):
    f=fixture;stage=f.stage(extra={'qick_lib/qick.egg-info/PKG-INFO':b'wrong'})
    with pytest.raises(ValueError,match='only the QICK package'):f.run('prepare')
    assert not (stage/'payload').exists()


def test_payload_version_mismatch_refused(fixture):
    f=fixture;before=hashes(f.library);f.stage(version='9.9')
    with pytest.raises(ValueError,match='Payload version differs'):f.run('prepare')
    assert hashes(f.library)==before


def test_missing_metadata_refused(fixture):
    f=fixture;(f.metadata/'PKG-INFO').rename(f.metadata/'PKG-INFO.saved')
    with pytest.raises(FileNotFoundError):remote.installation_contract(f.library)


def test_existing_source_metadata_mismatch_refused(fixture):
    f=fixture;(f.package/'VERSION').write_text('9.9')
    with pytest.raises(ValueError,match='source version and installed metadata differ'):
        remote.installation_contract(f.library)


@pytest.mark.parametrize('newline', ['\n', '\r\n', '\r\r\n'])
def test_launcher_rewrite_preserves_all_other_bytes(newline):
    original = ('# 경로는 여기만 변경' + newline
                + 'start_server(label="한글", bitfile="/old.bit", iface="eth0") # same' + newline).encode()
    destination = "/home/QSTL_QICK/qick/firmware/quote' and space/bitstream.bit"
    changed, before = remote.rewrite_pyro_cli(original, destination)
    assert before == '/old.bit'
    assert changed == original.replace(b'"/old.bit"', repr(destination).encode())
    calls = []
    exec(compile(changed, '<fixture>', 'exec'), {'start_server': lambda **kw: calls.append(kw)})
    assert calls[0]['bitfile'] == destination
    assert calls[0]['label'] == '한글' and calls[0]['iface'] == 'eth0'


@pytest.mark.parametrize('source', [
    b'# start_server(bitfile="/comment.bit")\n',
    b'start_server(bitfile="/a.bit")\nstart_server(bitfile="/b.bit")\n',
    b'start_server(bitfile=selected_path)\n',
    b'start_server(bitfile=make_path())\n',
    b'start_server(bitfile=None)\n',
    b'start_server()\n',
])
def test_ambiguous_or_dynamic_launcher_is_not_guessed(source):
    with pytest.raises(ValueError):
        remote.rewrite_pyro_cli(source, '/new.bit')


def test_launcher_rewrite_does_not_execute_source():
    original = b'raise RuntimeError("MUST NOT EXECUTE")\nstart_server(bitfile="/old.bit")\n'
    changed, _ = remote.rewrite_pyro_cli(original, '/new.bit')
    assert b'raise RuntimeError("MUST NOT EXECUTE")' in changed


def test_launcher_multiline_literal_and_utf8_bom():
    original = b'\xef\xbb\xbfstart_server(\n  bitfile=("/old/"\n           "file.bit"),\n)\n'
    changed, before = remote.rewrite_pyro_cli(original, '/new.bit')
    assert before == '/old/file.bit'
    assert changed == b"\xef\xbb\xbfstart_server(\n  bitfile=('/new.bit'),\n)\n"


def test_board_launcher_changed_after_prepare_refuses_apply(fixture):
    f=fixture;f.stage();f.run('prepare')
    (f.package/'pyro_cli.py').write_text('start_server(bitfile="/external.bit")\n')
    with pytest.raises(ValueError,match='Live files changed'):f.run('apply')
    assert f.bit.read_bytes()==b'old bit'


def test_staged_launcher_tampering_refuses_apply(fixture):
    f=fixture;stage=f.stage();f.run('prepare');before=hashes(f.library)
    (stage/'payload/qick_lib/qick/pyro_cli.py').write_text('start_server(bitfile="/wrong.bit")\n')
    with pytest.raises(ValueError,match='launcher hash mismatch'):f.run('apply')
    assert hashes(f.library)==before and f.bit.read_bytes()==b'old bit'


def test_launcher_original_snapshot_tampering_refuses_apply(fixture):
    f=fixture;stage=f.stage();f.run('prepare');before=hashes(f.library)
    (stage/'launcher_before.py').write_text('start_server(bitfile="/wrong.bit")\n')
    with pytest.raises(ValueError,match='Original board launcher hash changed'):f.run('apply')
    assert hashes(f.library)==before


def test_unsupported_board_launcher_refuses_prepare_without_live_changes(fixture):
    f=fixture;f.stage()
    (f.package/'pyro_cli.py').write_text('start_server(bitfile=dynamic_path)\n')
    before=hashes(f.library)
    with pytest.raises(ValueError,match='single string literal'):f.run('prepare')
    assert hashes(f.library)==before and f.bit.read_bytes()==b'old bit'


def test_format2_transaction_requires_new_prepare(fixture):
    f=fixture;stage=f.stage(format=2)
    with pytest.raises(ValueError,match='launcher path synchronization'):f.run('prepare')
    assert not (stage/'payload').exists()


def test_whole_firmware_backup_update_restore(fixture):
    f = fixture
    firmware = f.root / 'qick/firmware'
    (firmware / 'board_only.txt').write_text('preserve in backup')
    before = hashes(firmware)
    stage = f.stage()
    f.run('prepare')
    f.run('apply')
    assert hashes(stage / 'backup/1') == before
    assert hashes(firmware) == {
        'test/bitstream.bit': b'new bit', 'test/bitstream.hwh': b'new hwh',
        'other/bitstream.bit': b'other bit', 'other/bitstream.hwh': b'other hwh',
        'ip/rtl/logic.v': b'module logic; endmodule'}
    f.run('rollback')
    assert hashes(firmware) == before


def test_files_update_never_imports_pyro(fixture, monkeypatch):
    import builtins
    original = builtins.__import__
    def no_pyro(name, *args, **kwargs):
        if name.startswith(('Pyro4', 'qick')):
            raise AssertionError('File update attempted a runtime import: ' + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', no_pyro)
    f = fixture
    info = f.run('inspect')
    assert not info['runtime']['queried']
    f.run('check_stopped')
    f.stage()
    f.run('prepare')
    f.run('apply')
    f.run('rollback')


def test_server_stop_confirmation_required(fixture):
    f = fixture
    f.request['server_stopped'] = False
    with pytest.raises(ValueError, match='Confirm'):
        f.run('check_stopped')
    f.stage()
    f.run('prepare')
    before = hashes(f.root / 'qick')
    with pytest.raises(ValueError, match='Confirm'):
        f.run('apply')
    assert hashes(f.root / 'qick') == before


def test_running_server_blocks_apply(fixture, monkeypatch):
    f = fixture
    f.stage()
    f.run('prepare')
    before = hashes(f.root / 'qick')
    monkeypatch.setattr(remote, 'server_processes', lambda: [{'pid':123}])
    with pytest.raises(ValueError, match='123'):
        f.run('apply')
    assert hashes(f.root / 'qick') == before


def test_server_process_detection(tmp_path):
    commands = {
        910001: ['python3', '-m', 'qick.pyro_cli'],
        910002: ['python3', '/home/repo/qick/pyro_cli.py'],
        910003: ['python3', '-c', 'import qick.pyro; qick.pyro.start_server()'],
        910004: ['python3', '-c', 'import qick.pyro; qick.pyro.start_nameserver()'],
        910005: ['python3', '-c', 'print("a read only check")'],
        910006: ['bash', '-c', 'python3 -m qick.pyro_cli'],
        910007: ['python3', '/home/pyro_service.py'],
    }
    for pid, args in commands.items():
        folder = tmp_path / str(pid)
        folder.mkdir()
        (folder / 'cmdline').write_bytes(('\0'.join(args) + '\0').encode())
    assert {item['pid'] for item in remote.server_processes(tmp_path)} == {910001, 910002, 910003, 910007}


def test_selected_firmware_drives_launcher(fixture):
    f = fixture
    stage = f.stage()
    manifest_path = stage / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['active_firmware'] = 'other/bitstream.bit'
    manifest_path.write_text(json.dumps(manifest))
    f.request['remote_bit'] = 'qick/firmware/other/bitstream.bit'
    f.run('prepare')
    f.run('apply')
    calls = []
    exec(compile((f.package / 'pyro_cli.py').read_bytes(), '<fixture>', 'exec'),
         {'start_server': lambda **kw: calls.append(kw)})
    assert calls[0]['bitfile'] == str(f.root / 'qick/firmware/other/bitstream.bit')
    assert f.bit.read_bytes() == b'new bit'


def test_selection_cannot_change_after_review(fixture):
    f = fixture
    f.stage()
    f.request['remote_bit'] = 'qick/firmware/other/bitstream.bit'
    with pytest.raises(ValueError, match='reviewed firmware'):
        f.run('prepare')


def test_other_firmware_tamper_rejected(fixture):
    f = fixture
    stage = f.stage()
    f.run('prepare')
    before = hashes(f.root / 'qick')
    (stage / 'payload/firmware/other/bitstream.bit').write_bytes(b'tampered')
    with pytest.raises(ValueError, match='hash mismatch'):
        f.run('apply')
    assert hashes(f.root / 'qick') == before


def test_format3_transaction_requires_new_prepare(fixture):
    f = fixture
    stage = f.stage(format=3)
    with pytest.raises(ValueError):
        f.run('prepare')
    assert not (stage / 'payload').exists()
