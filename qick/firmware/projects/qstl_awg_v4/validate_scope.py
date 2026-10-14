"""Protect the prior generator algorithms and unchanged timing constraints."""
import argparse
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=ROOT/'analysis_results/awg_tuning_v4'

def validate():
    paths=json.loads((OUT/'protected_v3_sources.json').read_text())
    for name,digest in paths.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Protected v3 source changed: '+name)
    for name in ('timing.xdc','ios.xdc','bd_2023-1.tcl'):
        if (HERE/name).read_bytes()!=(HERE.parent/'qstl_awg_v3'/name).read_bytes():
            raise RuntimeError('Original v3 file changed: '+name)
    return {'passed':True,'protected_files':len(paths)}

def validate_functional():
    result=validate()
    gate=json.loads((OUT/'prebuild_gate.json').read_text())
    if not gate.get('complete'):raise RuntimeError('Incomplete v4 functional evidence')
    if len(gate.get('cases',[]))!=5 or gate.get('selected_area_bits')!=48:
        raise RuntimeError('Missing v4 validation cases')
    for group in ('source_hashes','evidence_hashes'):
        if not gate.get(group):raise RuntimeError('Missing bound evidence: '+group)
        for name,digest in gate[group].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Evidence changed: '+name)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--require-functional',action='store_true');args=p.parse_args()
    result=validate_functional() if args.require_functional else validate()
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
