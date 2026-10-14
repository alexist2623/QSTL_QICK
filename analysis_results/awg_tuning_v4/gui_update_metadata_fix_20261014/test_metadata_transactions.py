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
    monkeypatch.setattr(remote,'live',lambda r,require=False:{'stopped':True})
    monkeypatch.setattr(remote.importlib.util,'find_spec',lambda n:SimpleNamespace(origin=str(package/'__init__.py')))
    monkeypatch.setattr(remote.site,'getsitepackages',lambda:[str(site)])
    monkeypatch.setattr(remote.site,'getusersitepackages',lambda:str(tmp_path/'unused-site'))
    contract=remote.installation_contract(library)
    def stage(*, contract_change=None, extra=None, version=VERSION, format=2):
        remote.main(dict(request,action='reserve'))
        stage=root/'.qick_gui_updates'/request['release']
        files={'qick_lib/qick/__init__.py':b'VALUE = "after"\n',
               'qick_lib/qick/new_module.py':b'NEW = True\n',
               'qick_lib/qick/VERSION':(version+'\n').encode(),
               'firmware/bitstream.bit':b'new bit','firmware/bitstream.hwh':b'new hwh'}
        files.update(extra or {})
        manifest={'format':format,'library_scope':'qick-package-only',
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
    assert (f.package/'new_module.py').exists() and not (f.package/'obsolete.py').exists()
    assert hashes(f.metadata)==old_metadata and hashes(f.site)==old_site
    assert f.metadata.stat().st_ino==metadata_inode
    assert (f.library/'keep_me.txt').read_text()=='unrelated library-root file'
    assert f.run('rollback')['state']=='rolled_back_restart_required'
    assert hashes(f.package)==old_package and hashes(f.metadata)==old_metadata and hashes(f.site)==old_site
    assert f.imported_value()=='before '+VERSION


def test_failed_hwh_replace_restores_original_package_and_metadata(fixture,monkeypatch):
    f=fixture; before=hashes(f.library); site_before=hashes(f.site)
    stage=f.stage();f.run('prepare'); original=remote.os.replace
    source=stage/'payload/firmware/bitstream.hwh'
    def fail_hwh(src,dst):
        if Path(src)==source:raise OSError('injected HWH rename failure')
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
