"""Prove final GUI changes preserve all six already-executed hardware inputs."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def differences(before, after, path=''):
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(set(before) | set(after)):
            if key not in before:
                result.append(dict(path=path+'/'+key, added=after[key]))
            elif key not in after:
                result.append(dict(path=path+'/'+key, removed=before[key]))
            else:
                result.extend(differences(before[key], after[key], path+'/'+key))
        return result
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [item for index, (old, new) in enumerate(zip(before, after))
                for item in differences(old, new, path+f'/{index}')]
    return [] if before == after else [dict(path=path, before=before, after=after)]


def main():
    before = json.loads((HERE/'prepared.json').read_text())
    after = json.loads((HERE/'final_recompiled.json').read_text())
    assert len(before['cases']) == len(after['cases']) == 6
    cases = []
    for old, new in zip(before['cases'], after['cases']):
        hashes = {}
        for name in ('pmem.hex', 'dmem.txt', 'program.asm', 'expected.json'):
            old_hash, new_hash = sha(Path(old['folder'])/name), sha(Path(new['folder'])/name)
            assert old_hash == new_hash, (old['folder'], name)
            hashes[name] = old_hash
        assert old['rf_events'] == new['rf_events'], 'Emitted RF event changed'
        assert old['tau_us'] == new['tau_us'] and old['pi_us'] == new['pi_us']
        old_specs = json.loads((Path(old['folder'])/'rf_specs.json').read_text())
        new_specs = json.loads((Path(new['folder'])/'rf_specs.json').read_text())
        cases.append(dict(passed=True, original=old['folder'], recompiled=new['folder'],
                          exact_input_hashes=hashes, exact_emitted_rf_events=True,
                          serialized_metadata_changes=differences(old_specs, new_specs)))
    for path, expected in after['source_hashes'].items():
        assert sha(path) == expected, ('source changed after compile', path)
    result = dict(passed=True, cases=cases, source_hashes=after['source_hashes'],
        original_preparation_sha256=sha(HERE/'prepared.json'),
        final_preparation_sha256=sha(HERE/'final_recompiled.json'),
        helper_sha256=sha(__file__),
        claim='Exact PMEM/DMEM/ASM/expected commands and emitted RF events; additive/default metadata changes itemized')
    (HERE/'final_source_input_equivalence_named.json').write_text(json.dumps(result, indent=2))
    print('PASS final six-coordinate input equivalence: PMEM/DMEM/ASM/expected commands and RF events exact')


if __name__ == '__main__':
    main()
