"""Read-only production preservation audit; each result has a fresh path."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GUI = Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')
REPO = Path('C:/GIT_Workspace/QSTL_QICK')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=('before', 'after'))
    args = ap.parse_args()
    out = HERE / (args.mode + '.json')
    assert not out.exists(), 'Do not overwrite prior evidence'
    previous = read(ROOT / 'software_followup/scope_after_tests.json')
    paths = set(map(Path, previous['source_hashes']))
    paths.update(map(Path, read(ROOT / 'protected_before.json')))
    paths.update(GUI.glob('*.json'))
    for ext in ('*.bit', '*.hwh', '*.xsa', '*.xdc'):
        paths.update((REPO / 'qick/firmware').rglob(ext))
    publication = ROOT / 'local_firmware_package_20261015/result.json'
    authorized_additions = {}
    if args.mode == 'after' and publication.is_file():
        published = read(publication)
        assert published['passed'] and published['published_local']
        assert not published['board_uploaded']
        folder = REPO / 'qick/firmware/projects/qstl_awg_v5'
        expected = {folder / n for n in ('bitstream.bit', 'bitstream.hwh',
                                        'bitstream.xsa', 'build_manifest.json')}
        assert {Path(item['path']) for item in published['files']} == expected
        authorized_additions = {str(Path(item['path'])): item['sha256']
                                for item in published['files']}
        paths.update(expected)
    for name in ('bitstream.bit', 'bitstream.hwh', 'bitstream.xsa',
                 'candidate_manifest.json', 'build_result.txt',
                 'timing_summary_postroute.rpt', 'bus_skew_postroute.rpt'):
        paths.add(Path('F:/Vivado_Output/a5full1') / name)
    missing = [str(p) for p in sorted(paths) if not p.is_file()]
    assert not missing, missing
    current = {str(p): sha(p) for p in sorted(paths)}
    prior_differences = [p for p,h in previous['source_hashes'].items()
                         if current.get(str(Path(p))) != h]
    assert not prior_differences, prior_differences
    differences = []
    if args.mode == 'after':
        before = read(HERE / 'before.json')['files']
        assert not (set(before) & set(authorized_additions)), 'Only new files authorized'
        assert all(current.get(p) == h for p,h in authorized_additions.items())
        differences = [p for p in sorted(set(before) | set(current))
                       if before.get(p) != current.get(p)
                       and not (p not in before and p in authorized_additions
                                and current.get(p) == authorized_additions[p])]
    result = dict(passed=not differences, mode=args.mode,
                  checked=datetime.datetime.now().astimezone().isoformat(),
                  files=current, file_count=len(current), differences=differences,
                  prior_verified_production_python_count=len(previous['source_hashes']),
                  prior_verified_python_differences=prior_differences,
                  authorized_new_local_firmware_files=authorized_additions)
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('passed','file_count','differences')}))
    assert not differences, differences


if __name__ == '__main__':
    main()
