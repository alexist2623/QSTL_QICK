"""Seal completed evidence and stage exactly those byte-identical files.

Invoked only after the physical campaign, all analysis, and independent review
have ended. Does not commit or push. Runtime __pycache__ is not evidence.
"""
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
REPO=Path('C:/GIT_Workspace/QSTL_QICK')
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=REPO).strip(), 'Existing staged changes must be preserved separately'
target=HERE/'ARCHIVE_MANIFEST.json'
assert not target.exists(), 'Never replace an earlier archive manifest'
files=sorted(p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
entries={p.relative_to(HERE).as_posix():dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files}
target.write_text(json.dumps(dict(scope='Final and superseded evidence preserved; no production changes',
    completed_physical_cases=12,files=entries),indent=2)+'\n',encoding='utf8')
files.append(target)
paths=[p.relative_to(REPO).as_posix() for p in files]
subprocess.run(['git','add','-f','--pathspec-from-file=-','--pathspec-file-nul'],cwd=REPO,
    input=b'\0'.join(p.encode('utf8') for p in paths)+b'\0',check=True)
staged=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=REPO).decode('utf8').split('\0')
assert set(staged)-{''}==set(paths)
index={}
for row in subprocess.check_output(['git','ls-files','--stage','-z','--',HERE.relative_to(REPO).as_posix()],cwd=REPO).decode('utf8').split('\0'):
    if not row:continue
    metadata,path=row.split('\t',1)
    mode,digest,stage=metadata.split()
    assert stage=='0';index[path]=digest
for p,name in zip(files,paths):
    data=p.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==index[name],name
print(json.dumps(dict(staged_files=len(files),all_staged_bytes_equal_disk=True,
    archived_files=len(entries),archived_bytes=sum(v['bytes'] for v in entries.values()),
    archive_manifest_sha256=hashlib.sha256(target.read_bytes()).hexdigest()),indent=2))
