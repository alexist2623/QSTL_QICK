"""Record source/config/firmware preservation for the basic validation campaign.

Run from QSTL_QICK with qcodes2 Python. This script never imports production GUI
code or connects to instruments. Evidence directories are intentionally excluded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPOS = [Path('C:/GIT_Workspace/QSTL_QICK'), Path('C:/GIT_Workspace/PulseGenerator')]


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args]).decode('utf-8')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def snapshot():
    result = {'utc': datetime.now(timezone.utc).isoformat(), 'repositories': []}
    for root in REPOS:
        paths = git(root, 'ls-files', '-z').split('\0')
        tracked = [p for p in paths if p and not p.startswith('analysis_results/')]
        user_settings = [p for p in git(root, 'ls-files', '--others', '--exclude-standard', '-z').split('\0')
                         if p.startswith('DCWaveformGeneratorGUI/') and p.endswith('.json')]
        files = {}
        for rel in sorted(set(tracked + user_settings)):
            path = root / rel
            files[rel] = {'sha256': digest(path), 'bytes': path.stat().st_size,
                          'tracked': rel in tracked} if path.is_file() else {'missing': True}
        result['repositories'].append({'path': str(root), 'head': git(root, 'rev-parse', 'HEAD').strip(),
                                       'branch': git(root, 'branch', '--show-current').strip(), 'files': files})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['before', 'after'])
    args = parser.parse_args()
    output = HERE / ('sources_' + args.phase + '.json')
    if output.exists():
        raise FileExistsError('Preserve existing evidence: ' + str(output))
    state = snapshot()
    output.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    count = sum(len(r['files']) for r in state['repositories'])
    result = {'files': count, 'snapshot': str(output)}
    if args.phase == 'after':
        before = json.loads((HERE / 'sources_before.json').read_text(encoding='utf-8'))
        differences = []
        for old, new in zip(before['repositories'], state['repositories']):
            for rel in sorted(set(old['files']) | set(new['files'])):
                if old['files'].get(rel) != new['files'].get(rel):
                    differences.append({'repository': new['path'], 'path': rel,
                                        'before': old['files'].get(rel), 'after': new['files'].get(rel)})
            if old['head'] != new['head'] or old['branch'] != new['branch']:
                differences.append({'repository': new['path'], 'revision_changed': True})
        result.update(unchanged=not differences, differences=differences)
        (HERE / 'preservation_audit.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    if result.get('unchanged') is False:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
