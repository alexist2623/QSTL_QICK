"""Preserve the exact postbuild software only after the final scope audit."""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    before = read(HERE / 'scope_before_tests.json')
    after = read(HERE / 'scope_after_tests.json')
    rtl = read(HERE / 'gui_rtl/reporting/result.json')
    assert before['passed'] and after['passed']
    assert before['source_hashes'] == after['source_hashes'], 'Production source changed during validation'
    assert rtl['complete'] and rtl['executed_supported_cases_passed']
    assert not rtl['exact_zero_offset_supported']
    destination = HERE / 'verified_sources'
    assert not destination.exists(), 'Keep existing evidence; use a new archive if needed'
    sources = {r['path']: r['after'] for r in after['authorized_existing_changes']}
    sources.update(after['authorized_additions'])
    assert len(sources) == 16
    payloads = []
    for source, digest in sorted(sources.items()):
        data = Path(source).read_bytes()
        assert sha(data) == digest
        payloads.append((source, digest, data))
    destination.mkdir()
    records = []
    for source, digest, data in payloads:
        target = destination / (digest + '.py')
        if not target.exists():
            target.write_bytes(data)
        assert sha(target.read_bytes()) == digest
        records.append(dict(source=source, snapshot=str(target), sha256=digest, bytes=len(data)))
    result = dict(complete=True, created=datetime.datetime.now().astimezone().isoformat(),
                  production_unchanged_during_validation=True,
                  full_production_file_count=len(after['source_hashes']),
                  modified_or_added_files=records,
                  final_scope_sha256=sha((HERE / 'scope_after_tests.json').read_bytes()),
                  rtl_result_sha256=sha((HERE / 'gui_rtl/reporting/result.json').read_bytes()),
                  exact_zero_offset_supported=False, board_actions=False)
    (destination / 'manifest.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(dict(complete=True, archived_files=len(records),
                         full_production_file_count=result['full_production_file_count'])))


if __name__ == '__main__':
    main()
