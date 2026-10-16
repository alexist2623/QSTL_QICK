"""Fresh process reconstruction of a GUI-prepared high-resolution fixed point."""
from pathlib import Path
import argparse
import json
import sys
import hashlib

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepared',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();directory=(HERE/args.prepared).resolve();output=(HERE/args.output).resolve()
    if directory.parent!=HERE or output.parent!=HERE or output.exists():raise ValueError('Use a preserved bundle and fresh root-level audit JSON')
    from prepare_highres import reconstruct_prepared
    sys.path.insert(0,str(HERE/'model_review'))
    from command_expectation import output_model
    reconstructed=reconstruct_prepared(directory)
    e=reconstructed['expected_points'];m=reconstructed['manifest']
    assert len(e['points'])==m['points']==1
    assert m['sweep_shape']==[1] and e['logical_coordinate_shape']==[1,1]
    rows=[]
    for o in e['points'][0]['outputs']:
        model=output_model(o)
        assert not model.metadata_step_mismatches
        assert model.waveform.area==0
        assert model.at_program_us(o['dc_zero_reset_bound_us']+1)['expected_direct_dac_mv']==0
        assert o['requested_mv']==(m['start_mv'] if o['active'] else 0)
        rows.append(dict(scope_channel=o['axis']+1,requested_mv=o['requested_mv'],compiled_mv=o['quantized_mv'],
            requested_rise_us=o['requested_rise_us'],requested_fall_us=o['requested_fall_us'],
            compiled_rise_us=o['compiled_rise_us'],compiled_fall_us=o['compiled_fall_us'],
            exact_model_area_zero=True,exact_model_final_rc_zero=True,metadata_matches_actual_commands=True))
    result=dict(passed=True,prepared_bundle=directory.name,actual_gui_compile_artifact_hashes_match=True,
        fresh_reconstructed_pmem_dmem_exact=True,helper_sha256=m['helper_sha256'],points=1,
        source_unchanged=True,physical_execution=False,outputs=rows,
        audit_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with output.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(result,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
