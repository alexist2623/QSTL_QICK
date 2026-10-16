"""Create or verify the lossless basic-case evidence inventory before committing."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / 'archive_manifest.json'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inventory():
    files = []
    for path in sorted(HERE.rglob('*')):
        if not path.is_file() or path == MANIFEST or '__pycache__' in path.parts:
            continue
        if path.suffix in {'.pyc', '.pyo'}:
            continue
        if path.stat().st_size > 95 * 1024 * 1024:
            raise ValueError('Archive file needs lossless splitting before Git push: ' + str(path))
        row = {'path': path.relative_to(HERE).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)}
        if path.suffix == '.json':
            json.loads(path.read_text(encoding='utf-8-sig'))
            row['json_reloaded'] = True
        elif path.suffix == '.npz':
            import numpy as np
            with np.load(path, allow_pickle=False) as archive:
                row['arrays'] = {name: {'shape': list(archive[name].shape),
                                        'dtype': str(archive[name].dtype)}
                                 for name in archive.files}
            row['npz_reloaded'] = True
        elif path.suffix == '.npy':
            import numpy as np
            values = np.load(path, allow_pickle=False)
            row.update(npy_reloaded=True, shape=list(values.shape), dtype=str(values.dtype))
        elif path.suffix == '.gz':
            h = hashlib.sha256()
            size = 0
            lines = 0
            with gzip.open(path, 'rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    h.update(block)
                    size += len(block)
                    lines += block.count(b'\n')
            row.update(gzip_reloaded=True, uncompressed_bytes=size,
                       uncompressed_sha256=h.hexdigest(), newline_count=lines)
        files.append(row)
    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['create', 'verify'])
    args = parser.parse_args()
    files = inventory()
    if args.action == 'create':
        if MANIFEST.exists():
            raise FileExistsError('Existing manifest must not be overwritten')
        MANIFEST.write_text(json.dumps({'files': files, 'file_count': len(files),
            'total_bytes': sum(f['bytes'] for f in files),
            'scope': 'Digital validation evidence only; no physical measurements'}, indent=2) + '\n', encoding='utf-8')
    else:
        expected = json.loads(MANIFEST.read_text(encoding='utf-8'))['files']
        if files != expected:
            old, new = ({r['path']: r for r in rows} for rows in (expected, files))
            changed = [name for name in sorted(set(old) | set(new)) if old.get(name) != new.get(name)]
            raise ValueError('Archive changed after inventory: ' + repr(changed))
    print(json.dumps({'action': args.action, 'passed': True, 'files': len(files),
                      'total_bytes': sum(f['bytes'] for f in files),
                      'gzip_files': sum(f.get('gzip_reloaded', False) for f in files)}))


if __name__ == '__main__':
    main()
