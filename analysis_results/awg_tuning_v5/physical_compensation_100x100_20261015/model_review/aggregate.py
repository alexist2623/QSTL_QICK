"""Seal the twelve completed command-model reviews without rerunning them."""
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parent
target=root/'all_12_bundle_results.json'
if target.exists():raise FileExistsError(target)
names=[f'{mode}_tau{tau}' for tau in (10,20,30)
       for mode in ('fixed_voltage','fixed_time10','fixed_time20','fixed_time30')]
records=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name in names:
    file=root/name/'results.json'
    data=json.loads(file.read_text(encoding='utf8'))
    assert data['passed'] and data['outputs_checked']==20000
    assert data['area_matches']==data['zero_residuals']==data['zero_final_rc_codes']==20000
    assert data['metadata_step_mismatches']==0
    assert all(sha(Path(p))==digest for p,digest in data['source_hashes'].items())
    manifest=json.loads((file.parent/'manifest.json').read_text())
    assert all(sha(file.parent/name)==digest for name,digest in manifest.items())
    records.append(dict(name=name,result_sha256=sha(file),
        mode=data['mode'],rc_tau_us=data['rc_tau_us'],dc_time_us=data['dc_time_us'],
        outputs=data['outputs_checked'],sampled_rc_mv_bounds=data['sampled_rc_mv_bounds'],
        compiler_range_mv=data['production_range_bounds_mv'],frame_us=data['frame_zero_bound_us'],
        midpoint_ideal_vs_compiled_max_mv=data['maximum_abs_compiled_vs_requested_ideal_midpoint_mv']))
result=dict(passed=True,physical_execution=False,conditions=12,
    independent_exact_command_area_checks=240000,exact_zero_residuals=240000,
    exact_final_rc_zero_checks=240000,metadata_decode_mismatches=0,
    maximum_expected_frame_us=max(r['frame_us'] for r in records),
    results=records,
    source_hashes={p.name:sha(p) for p in (root/'compact_expectation.py',root/'command_expectation.py',root/'validate_bundle.py',Path(__file__))},
    limits=['These checks do not constitute new RTL execution or physical measurement PASS.',
            'RC boundaries and midpoints are sampled diagnostics; full scalar range remains bounded by the separately retained compiler conservative gate.',
            'Exact compiled voltage is diagnostic; primary physical accuracy must retain the separately declared GUI requested ideal reference.',
            'External analog RC capacitor state and instrument uncertainty are not included.'])
target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
lines=['# 최종 12조건 command-model 독립검토','',
       '12조건 × 10,000점 × 2출력 = 240,000개 출력의 실제 명령 기반 면적, 보상 잔여0, RC 종료0을 독립 compact 정수 모델로 확인했습니다. 모두 PASS이며 이는 새 RTL 실행이나 물리 측정 PASS가 아닙니다.',
       '', '|조건|출력 검사|샘플링한 RC 범위(mV)|전체 종료 bound(ms)|', '|---|---:|---:|---:|']
for r in records:
    low,high=r['sampled_rc_mv_bounds']
    lines.append(f'|{r["name"]}|{r["outputs"]}|{low:.6f} .. {high:.6f}|{r["frame_us"]/1000:.6f}|')
lines += ['', '모든 실제160-bit command의 step metadata와 bits127:96 해석이 일치했습니다. 각 파일의 입력·helper·결과 해시를 다시 대조했습니다. 0.425604~0.625604초 범위의 각 기록과 전후 idle이 capture에 들어가야 합니다.',
          '', 'RC 구간 경계·중점 검사는 진단입니다. 모든 scalar sample의 clipping 검사를 새로 실행한 것으로 과장하지 않으며, 생산 컴파일러의 보수적 range gate도 별도로 보존합니다. GUI 요청 이상파형과 실제 양자화된 명령파형은 물리 분석에서 구분해야 합니다.',
          '', '[상세 집계](all_12_bundle_results.json) · [모델과 소스 근거](MODEL_REVIEW.md)']
(root/'BUNDLE_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
manifest={str(p.relative_to(root)):dict(bytes=p.stat().st_size,sha256=sha(p))
          for p in root.rglob('*') if p.is_file() and p.name!='FINAL_MANIFEST.json' and '__pycache__' not in p.parts}
(root/'FINAL_MANIFEST.json').write_text(json.dumps(dict(complete=True,physical_execution=False,files=manifest),indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(conditions=12,outputs=240000,all_passed=True,result_sha256=sha(target)),indent=2))
