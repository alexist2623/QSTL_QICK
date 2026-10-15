"""Freeze the completed, unmodified v5 build before authorized software work."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import zipfile

HERE = Path(__file__).resolve().parent
BUILD = Path('F:/Vivado_Output/a5full1')
DEST = HERE/'successful_build_snapshot_v2'

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    state = read(HERE/'workflow_status.json')
    candidate = read(BUILD/'candidate_manifest.json')
    gate = read(HERE/'prebuild_gate.json')
    assert state['complete'] and state['stage'] == 'timing_passed_candidate_not_deployed'
    assert state['build_exit_code'] == 0 and state['build_result']['timing_closed'] == 'YES'
    assert candidate['passed'] and not candidate['deployed'] and gate['passed']
    gate_log = (HERE/'postbuild_gate.log').read_bytes()
    gate_log_text = gate_log.decode('utf-16' if gate_log.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    assert 'V5_FUNCTIONAL_GATE_PASS' in gate_log_text
    assert candidate['output_sum_blocks'] == 7 and candidate['awg_delay_cycles'] == 13
    assert candidate['pipeline_cycles'] == 2 and candidate['clock_hz'] == 300000000
    for name, entry in candidate['artifacts'].items():
        assert sha(entry['path']) == entry['sha256'].lower()
        assert entry['sha256'] == state['artifacts'][name]['sha256']
    with zipfile.ZipFile(BUILD/'bitstream.xsa') as archive:
        for ext, member in (('bit','bitstream.bit'),('hwh','d_1.hwh')):
            assert member in archive.namelist()
            assert hashlib.sha256(archive.read(member)).hexdigest() == sha(BUILD/f'bitstream.{ext}')
    compiler = read(HERE/'compiler_equivalence.json')
    sources = set(read(HERE/'protected_before.json')) | set(compiler['source_hashes']) | set(gate['v5_sources'])
    for path, digest in compiler['source_hashes'].items():
        assert sha(path) == digest.lower(), path
    for path, digest in gate['v5_sources'].items():
        assert sha(path) == digest.lower(), path
    files = {p for p in HERE.iterdir() if p.is_file()}
    files |= {Path(p) for p in sources}
    files |= {p for p in BUILD.iterdir() if p.is_file() and p.suffix.lower() in {'.json','.txt','.rpt','.bit','.hwh','.xsa'}}
    files |= {Path('F:/Vivado_Output/a5full1_build.log'), Path('F:/Vivado_Output/a5full1_vivado.log')}
    for build in ('a5sum2','a5native3','a5ramp2','a5rc48','a5reg1'):
        folder = Path('F:/Vivado_Output')/build
        files |= {p for p in folder.rglob('*.json') if 'pytest_temp' not in p.parts}
    for case in read(HERE/'replays_status.json')['cases'].values():
        files |= {p for p in Path(case['build']).glob('*.json')}
    files |= set((HERE/'selected48').glob('*.json'))
    files |= set((HERE/'selected48').glob('*.png'))
    assert not DEST.exists(), 'Snapshot already exists; never overwrite it'
    DEST.mkdir()
    entries=[]
    for source in sorted(files):
        assert source.is_file(), source
        digest=sha(source)
        target = DEST/'objects'/(digest+source.suffix.lower())
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            shutil.copy2(source,target)
        assert sha(target)==digest
        entries.append(dict(source=str(source),snapshot=str(target),sha256=digest,bytes=source.stat().st_size))
    result=dict(complete=True,created=datetime.datetime.now().astimezone().isoformat(),
                workflow=state,candidate=candidate,files=entries,
                gate_verified=gate['verified'],
                note='Original successful build/source snapshot. prebuild_gate.json contains final postbuild gate verification. The initial partial snapshot hit Windows path length and is retained; v2 uses content-addressed short paths. Later software evidence must be separate.')
    (DEST/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(f'FROZEN_SUCCESS files={len(entries)} artifacts_verified=true source_hashes_verified=true')

if __name__=='__main__':
    main()
