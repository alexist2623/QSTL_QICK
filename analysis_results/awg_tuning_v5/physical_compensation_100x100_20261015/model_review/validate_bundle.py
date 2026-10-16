"""Exact command/area checks for a completed preparation; no hardware access."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

from command_expectation import load_expected, output_model


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    destination=args.output.resolve()
    if destination.parent!=root or destination.exists():
        raise ValueError('Use a fresh direct child under model_review')
    destination.mkdir()
    started=time.perf_counter()
    bundle=args.bundle.resolve()
    expected_path=bundle/'expected_points.json.gz'
    if not expected_path.exists():expected_path=bundle/'expected_points.json'
    sources=[expected_path,bundle/'manifest.json',bundle/'preparation_summary.json',
             root/'command_expectation.py',root/'compact_expectation.py',Path(__file__).resolve()]
    hashes={str(p):sha(p) for p in sources}
    expected=load_expected(expected_path)
    summary=json.loads((bundle/'preparation_summary.json').read_text(encoding='utf8'))
    assert expected['point_count']==10000 and len(expected['points'])==10000
    assert expected['requested_range_mv']==[-300.,300.]
    records=[]
    min_code=8191;max_code=-8192;sample_checks=0;peak_area=0;zero_count=0
    for point in expected['points']:
        index=point['point_index'];assert point['axis_indices']==[index//100,index%100]
        assert len(point['outputs'])==2
        for axis,out in enumerate(point['outputs']):
            assert abs(out['requested_mv']-(-300+600*point['axis_indices'][axis]/99))<1e-9
            model=output_model(out)
            assert not model.metadata_step_mismatches,model.metadata_step_mismatches
            assert model.coefficient==round(2**48/(2*out['rc_tau_us']*4800))
            assert model.waveform.area==0
            peak_area=max(peak_area,abs(model.pre_dc_area))
            assert abs(model.pre_dc_area)<2**47
            # These critical-point checks are not a full scalar-range proof.
            # The compiler's independently retained conservative range bounds
            # remain the full-domain preflight. Check every run boundary and
            # midpoint to catch ordering/sign/RC-domain mistakes cheaply.
            samples=set();previous_end=0
            for end in model.waveform.ends:
                samples.update((previous_end,(previous_end+end-1)//2,end-1))
                previous_end=end
            codes=[model.waveform.rc_effective_at(n,model.coefficient) for n in sorted(samples)]
            sample_checks+=len(codes);min_code=min(min_code,*codes);max_code=max(max_code,*codes)
            assert all(-8192<c<8191 for c in codes),'Sampled RC output hits a saturation endpoint'
            final_index=model.waveform.samples-1
            assert model.waveform.raw_at(final_index)==0
            assert model.waveform.rc_effective_at(final_index,model.coefficient)==0
            zero_count+=1
            center=(out['hold_digital_output_us']+out['hold_end_digital_output_us'])/2
            center_result=model.at_program_us(center)
            # Requested ideal midpoint is diagnostic only: 1us requested ramp,
            # followed by the middle of requested 10us HOLD. Primary physical
            # analysis owns its separately declared ideal waveform timing.
            requested_ideal_center=out['requested_mv']*(1+(0.5+5)/out['rc_tau_us'])
            records.append(dict(point=index,axis=axis,area_effective_samples=model.pre_dc_area,
                residual_area=0,dc_words=out['dc_duration_cycles'],final_rc_code=0,
                sampled_min_mv=min(codes)*out['full_scale_mv']/8192,
                sampled_max_mv=max(codes)*out['full_scale_mv']/8192,
                requested_mv=out['requested_mv'],quantized_mv=out['quantized_mv'],
                exact_compiled_hold_center_mv=center_result['expected_direct_dac_mv'],
                requested_ideal_hold_center_mv=requested_ideal_center,
                midpoint_difference_mv=center_result['expected_direct_dac_mv']-requested_ideal_center))
    assert len(records)==20000 and zero_count==20000
    assert all(sha(Path(p))==digest for p,digest in hashes.items())
    with (destination/'all_output_checks.json.gz').open('wb') as file:
        with gzip.GzipFile(fileobj=file,mode='wb',mtime=0) as stream:
            stream.write(json.dumps(records,separators=(',',':')).encode())
    result=dict(passed=True,physical_execution=False,bundle=str(bundle),
        points=10000,outputs_checked=len(records),area_matches=20000,zero_residuals=20000,
        zero_final_rc_codes=zero_count,metadata_step_mismatches=0,
        sampled_rc_code_checks=sample_checks,sampled_rc_code_bounds=[min_code,max_code],
        sampled_rc_mv_bounds=[min(r['sampled_min_mv'] for r in records),max(r['sampled_max_mv'] for r in records)],
        maximum_absolute_pre_dc_area=peak_area,production_range_bounds_mv=summary['global_rc_bounds_mv'],
        maximum_abs_compiled_vs_requested_ideal_midpoint_mv=max(abs(r['midpoint_difference_mv']) for r in records),
        requested_range_mv=expected['requested_range_mv'],mode=expected['mode'],rc_tau_us=expected['rc_tau_us'],
        dc_time_us=expected.get('dc_time_us'),dc_voltage_mv=expected.get('dc_voltage_mv'),
        frame_zero_bound_us=expected['last_output_zero_bound_us'],
        elapsed_s=time.perf_counter()-started,input_hashes_unchanged=True,source_hashes=hashes,
        limitations=['Command arithmetic/compact digital expectation only; not a new RTL or physical test.',
            'RC range sample boundaries/midpoints are diagnostics; compiler conservative bounds retain full-domain role.',
            'Requested ideal midpoint uses nominal 1us ramp+10us HOLD; it does not substitute for the primary physical requested reference.',
            'External analog RC capacitor and instrument uncertainty are not modeled.'])
    (destination/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    (destination/'manifest.json').write_text(json.dumps({p.name:sha(p) for p in destination.iterdir() if p.is_file()},indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('passed','outputs_checked','sampled_rc_mv_bounds','maximum_abs_compiled_vs_requested_ideal_midpoint_mv','frame_zero_bound_us','elapsed_s')},indent=2))


if __name__=='__main__':main()
