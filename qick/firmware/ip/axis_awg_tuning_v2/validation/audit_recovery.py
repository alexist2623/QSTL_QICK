"""Check completed source/build artifacts after an interrupted Windows build."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import zipfile


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True,
                                   encoding='utf-8', stderr=subprocess.STDOUT).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--gui', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[5]
    project = repo / 'qick/firmware/projects/qstl_awg_v2'
    build = args.build.resolve()
    result = dict(line.split('=', 1) for line in (build / 'build_result.txt').read_text().splitlines()
                  if '=' in line)
    assert result['timing_closed'] == 'YES', result
    repositories = []
    sources = set()
    for root in (repo, args.gui.resolve()):
        fsck = git(root, 'fsck', '--full', '--no-reflogs')
        repositories.append(dict(path=root.as_posix(), branch=git(root, 'branch', '--show-current'),
                                 head=git(root, 'rev-parse', 'HEAD'), fsck_output=fsck))
        sources.update(root / name for name in git(root, 'diff', '--name-only', 'HEAD').splitlines())
        sources.add(root / ('qick/qick_lib/qick/test_awg_tuning_v2.py' if root == repo
                           else 'DCWaveformGeneratorGUI/test_awg_tuning_v2.py'))
    sources.update((repo / 'qick/firmware/ip/axis_awg_tuning_v2').rglob('*'))
    sources.update(project.glob('*'))
    source_records = []
    for path in sorted(sources):
        if not path.is_file() or path.suffix not in ('.py', '.sv', '.v', '.tcl', '.xdc', '.xml', '.md'):
            continue
        data = path.read_bytes()
        assert data and b'\0' not in data, path
        text = data.decode('utf-8-sig')
        if path.suffix == '.py':
            ast.parse(text, filename=str(path))
        elif path.suffix == '.xml':
            ET.fromstring(text)
        source_records.append(dict(path=path.as_posix(), bytes=len(data),
                                   sha256=hashlib.sha256(data).hexdigest()))
    ET.parse(build / 'qstl_awg_v2.xpr')
    ET.parse(project / 'bitstream.hwh')
    checkpoints = []
    for path in sorted((build / 'qstl_awg_v2.runs').rglob('*.dcp')):
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None, path
        checkpoints.append(dict(path=path.relative_to(build).as_posix(), bytes=path.stat().st_size))
    assert checkpoints, 'No completed design checkpoints'
    manifest = json.loads((project / 'build_manifest.json').read_text())
    with zipfile.ZipFile(project / 'bitstream.xsa') as archive:
        assert archive.testzip() is None
        for suffix in ('.bit', '.hwh'):
            assert archive.read(manifest['xsa_members'][suffix][0]) == (project / ('bitstream' + suffix)).read_bytes()
    for artifact in manifest['artifacts']:
        data = (project / artifact['path']).read_bytes()
        assert len(data) == artifact['bytes']
        assert hashlib.sha256(data).hexdigest() == artifact['sha256']
    report = dict(status='passed', checked_utc=datetime.now(timezone.utc).isoformat(),
                  repositories=repositories, source_files=source_records,
                  xpr_and_hwh_xml='passed', dcp_crc='passed', checkpoints=checkpoints,
                  xsa_crc_and_extracted_member_equality='passed',
                  artifact_manifest_hashes='passed', build_result=result,
                  build_bytes=sum(p.stat().st_size for p in build.rglob('*') if p.is_file()),
                  limitations='Readability, syntax, CRC and regression checks; no pre-crash hash exists for every uncommitted file.')
    args.out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='passed', sources=len(source_records), checkpoints=len(checkpoints),
                         output=args.out.as_posix()), indent=2))


if __name__ == '__main__':
    main()
