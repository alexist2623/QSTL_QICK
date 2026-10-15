"""Bind executed inputs to a freshly compiled final source revision by bytes."""
import argparse
import json
from pathlib import Path

from harness import sha

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--final',type=Path,required=True)
    parser.add_argument('--reference',type=Path,action='append',required=True)
    parser.add_argument('--output',type=Path,default=HERE/'final_recompile_equivalence.json')
    args = parser.parse_args()
    final = json.loads(args.final.read_text())
    target = {case['name']:case for case in final['cases']}
    records = []
    for path in args.reference:
        reference = json.loads(path.read_text())
        for before in reference['cases']:
            after = target[before['name']]
            # All serialized GUI/runtime inputs, commands and envelope samples
            # must match, not merely the output timeline or a simulator model.
            assert before['inputs'].keys() == after['inputs'].keys()
            hashes = {}
            for name in before['inputs']:
                old = Path(before['folder'])/name
                new = Path(after['folder'])/name
                assert sha(old) == before['inputs'][name], (old,'changed since preparation')
                assert sha(new) == after['inputs'][name], (new,'changed since preparation')
                assert old.read_bytes() == new.read_bytes(), (before['name'],name,'bytes differ')
                hashes[name] = sha(new)
            records.append(dict(name=before['name'],reference_manifest=str(path),
                reference_manifest_sha256=sha(path),reference_source_hashes=reference['source_hashes'],
                original_folder=before['folder'],final_folder=after['folder'],identical_inputs=hashes))
    result = dict(passed=True,checked_cases=len(records),cases=records,
                  final_manifest=str(args.final),final_manifest_sha256=sha(args.final),
                  final_source_hashes=final['source_hashes'],helper_sha256=sha(__file__))
    args.output.write_text(json.dumps(result,indent=2))
    print(f'PASS: {len(records)} freshly compiled cases are byte-identical to the original inputs')


if __name__ == '__main__':
    main()
