"""Integrate separately frozen fullframe and representative results, no devices."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    assert not (HERE/'results.json').exists() and not (HERE/'REPORT.md').exists()
    full_dir=HERE/'fullframe_summary_01'
    fm=read(full_dir/'manifest.json')
    assert fm['audit_passed'] and fm['source_hashes_unchanged']
    for name,record in fm['files'].items():
        assert (full_dir/name).stat().st_size==record['bytes']
        assert sha(full_dir/name)==record['sha256']
    full=read(full_dir/'results.json')
    assert full['acquisition_and_analysis_integrity_passed'] and full['independent_csv_and_hash_audit_passed']
    assert (full['requested_conditions'],full['physical_conditions'],full['range_rejected_not_run'],full['physical_points'])==(48,32,16,320000)
    assert full['preparation_review']['complete'] and full['preparation_review']['comparison_audit_passed']
    hm=read(HERE/'highres_campaign_status.json');assert hm['complete'] and len(hm['cases'])==24
    scope_review=read(HERE/'highres_input_scope_review.json')
    assert scope_review['status']=='passed' and scope_review['representative_count']==24
    assert sha(HERE/'highres_preparation_resume_status.json')==scope_review['preparation_status_sha256']
    high=[];raw_total=gzip_total=0
    for case in hm['cases']:
        out=HERE/case['analysis'];run=HERE/case['run'];bundle=HERE/case['prepared']
        result=read(out/'results.json');status=read(run/'status.json')
        assert result['integrity_passed'] and result['source_run']==run.name and result['prepared_bundle']==bundle.name
        assert result['capture_id']==status['capture_id'] and status['acquisition_success'] and status['scope_restore']['passed'] and status['cleanup_zero']
        for name,record in read(out/'manifest.json')['files'].items(): assert sha(out/name)==record['sha256']
        for name,digest in read(bundle/'manifest.json')['files'].items(): assert sha(bundle/name)==digest
        capture=read(run/'scope_capture/capture.json')
        for info in capture['channels'].values():
            archive=info['archive'];path=run/'scope_capture'/Path(archive['path']).name
            assert sha(path)==archive['gzip_sha256'];raw_total+=archive['raw_bytes'];gzip_total+=archive['gzip_bytes']
        high.append(dict(label=case['label'],prepared=case['prepared'],run=case['run'],analysis=case['analysis'],capture_id=result['capture_id'],active_channel=result['active_channel'],swept_ramp=result['swept_ramp'],requested_duration_us=result['requested_swept_duration_us'],requested_voltage_mv=result['requested_voltage_mv'],sample_intervals_s=result['channel_sample_intervals_s'],ramps=result['ramps'],hold=result['hold'],dc=result['dc_central_half'],precision_timing_pass=None))
    expected={(direction,dac,duration,v) for direction in ('rising','falling') for dac in (1,2) for duration in (.01,.5,1.) for v in (-400.,400.)}
    assert {(r['swept_ramp'],r['active_channel'],r['requested_duration_us'],r['requested_voltage_mv']) for r in high}==expected
    ramp_rows=[r for c in high for r in c['ramps']]
    assert len(ramp_rows)==48 and all(r['valid'] for r in ramp_rows)
    high_stats=dict(ramp_windows=48,ramp_median_over_15mv=sum(not r['median_within_15mv'] for r in ramp_rows),
        ramp_native_samples=sum(r['samples'] for r in ramp_rows),ramp_samples_over_15mv=sum(r['samples_abs_error_over_15mv'] for r in ramp_rows),
        maximum_ramp_native_sample_residual_mv=max(r['max_abs_residual_mv'] for r in ramp_rows))
    transient_dir=HERE/'review_highres_rising_dac4_duration10ns_negative_01'
    for name,record in read(transient_dir/'manifest.json')['files'].items():
        assert sha(transient_dir/name)==record['sha256']
    transient=read(transient_dir/'results.json')
    assert transient['complete'] and transient['raw_reconstruction_verified'] and transient['no_refit']
    timing_review=read(HERE/'highres_timing_review_01/diagnostic_summary.json')
    assert timing_review['input_hashes_unchanged'] and timing_review['verdict_unchanged']
    merged=dict(representative_timing_review=timing_review,fullframe=full,representative_high_resolution=dict(acquisitions=24,integrity_passed=True,precision_timing_pass=None,full_grid_ramp_shape_coverage=False,diagnostics=high_stats,cases=high,raw_ieee_bytes=raw_total,lossless_gzip_bytes=gzip_total),first_10ns_post_ramp_transient=transient,all_requested_checks_passed=False,production_modified=False)
    (HERE/'results.json').write_text(json.dumps(merged,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    text=['# DC·RC + RAMP duration × voltage 실물 검증 결과','',
      f'요청한 **10ns~1µs RAMP duration 100점 × −400~+400mV 전압 100점**을 검사했습니다. 요청 {full["requested_conditions"]}조건 중 {full["physical_conditions"]}조건·{full["physical_points"]:,}점을 실제 출력·취득했고, {full["range_rejected_not_run"]}조건은 RC 출력 한도 검사에서 거부되어 출력하지 않았습니다. **전체 PASS는 아닙니다.**','',
      '상승·하강 RAMP와 DAC4·DAC5를 각각 분리하여 identity matrix와 100×100 크기를 유지했습니다. 반대 RAMP는 1µs, 반대 DAC는 0V, HOLD는 10µs입니다. RC τ 10/20/30µs × DC 고정 300mV 또는 고정 10/20/30µs의 12조합을 유지했습니다.','',
      '|측정 구간|PASS|FAIL|미판정|', '|---|---:|---:|---:|',
      *[f'|{label}|{full[key]["PASS"]:,}|{full[key]["FAIL"]:,}|{full[key]["INCOMPLETE"]:,}|' for label,key in [('활성 출력 HOLD','active_primary_counts'),('비활성 출력 0V','inactive_zero_counts'),('활성 DC 보상','dc_counts'),('두 출력 DC 뒤 0V','post_dc_zero_counts')]], '',
      f'주 HOLD의 최대 중앙구간 절대 오차는 **{full["maximum_primary_error_mv"]:.6f}mV**입니다. 종료 뒤 두 출력의 0V 복귀는 모든 조건에서 통과했습니다. DC 미판정 {full["dc_counts"]["INCOMPLETE"]:,}건은 짧은 보상 구간에 native 표본이 3개 미만이어서 평가하지 못한 경우입니다. PASS에 포함하지 않았습니다.', '',
      '각 capture의 시작 전 baseline offset 하나만 빼고, 중앙구간 median 오차의 절대값이 15mV를 초과하면 FAIL입니다. 모든 순간 샘플의 ±15mV 보장을 뜻하지 않습니다. RC 선보상 출력은 요청 전압에 적분 기울기가 더해지므로 각 점의 요청 상승시간을 포함한 RC 기대값과 비교했습니다. 요청값과 실제 양자화된 값은 별도로 저장하고 판정 기준을 실제값으로 바꾸지 않았습니다.','',
      '## 고해상도 대표 파형','',
      'RC 20µs/DC 고정 10µs에서 10ns·500ns·1µs 및 ±400mV, 두 DAC/두 방향 24조건을 별도 1점 GUI 설정으로 컴파일하고 취득했습니다. 각 채널의 원래 시간축을 보존했습니다. HOLD/모델 잔차와 RAMP의 10–90% 폭을 기록했지만, 아날로그 경로 보정이나 정밀 시간 허용오차 판정은 하지 않았습니다. 첫 edge에 대한 전체 시간 정렬은 케이블/시작 지연을 제거하므로 절대 출력 지연 측정도 아닙니다.','',
      '이 대표 파형은 전체 10,000점 명령열과 동일한 프로그램의 취득이 아닙니다. 단일점 반올림은 register-add sweep 끝값과 다를 수 있습니다. 전체 sweep의 500ns 기록으로 모든 10ns RAMP 모양을 검증했다고 주장하지 않습니다.','',
      f'대표 파형의 상승·하강 RAMP 총 48구간 중 중앙값 잔차가 15mV를 넘는 구간은 {high_stats["ramp_median_over_15mv"]}개입니다. 그러나 native 표본 {high_stats["ramp_native_samples"]:,}개 중 {high_stats["ramp_samples_over_15mv"]:,}개가 15mV를 초과하고, RAMP 구간 내 최대 순간 잔차는 {high_stats["maximum_ramp_native_sample_residual_mv"]:.3f}mV입니다. 구간 median과 순간 파형 오차를 구분해야 합니다.','',
      '이 399.051mV는 기존 시간 정렬을 유지한 모델 잔차이며, 순수한 진폭 결함의 크기로 해석할 수 없습니다. DAC5의 +400mV·10ns 하강 대표 파형을 독립 검토한 결과 실제 빠른 하강 구간이 존재했고, 10–90% 폭 후보는 7.078~7.378ns였습니다. 첫 1µs 상승 파형의 200mV crossing 후보 범위가 54.335ns여서, 기존 기준의 약 41ns 하강 시각 차이는 그 정렬 불확실성 안에 있습니다. 명령의 7클록 시작 지연·3클록 RAMP·다음 SET 간격은 서로 일치했습니다. 이 자료만으로 RTL 지연 결함을 확정하지 않으며, 기존 잔차와 미판정은 그대로 보존합니다. [명령·원시 파형 독립 검토](highres_timing_review_01/diagnostic_summary.json)','',
      'DAC4의 −400mV·10ns 상승 RAMP 직후 100ns를 별도 검토했습니다. 종료 뒤 10.138ns의 실제 offset 보정 전압은 −482.008mV, 모델 대비 잔차는 **−81.758mV**였습니다. 해당 1,000표본 중 334개가 15mV를 초과합니다. 이 과도응답은 RAMP 내부 및 HOLD 중앙구간 통계 밖에 있으므로 별도로 기록합니다. 정착시간/정밀 시간 PASS는 판정하지 않았습니다. [과도응답 원시 재검토](review_highres_rising_dac4_duration10ns_negative_01/results.json) · [파형](review_highres_rising_dac4_duration10ns_negative_01/post_ramp_100ns.png)','',
      '|방향|DAC|요청 길이(ns)|전압(mV)|native 간격(ns)|분석|','|---|---:|---:|---:|---:|---|']
    for r in high:
        dt=max(r['sample_intervals_s'].values())*1e9
        text.append(f'|{r["swept_ramp"]}|{r["active_channel"]+3}|{r["requested_duration_us"]*1000:g}|{r["requested_voltage_mv"]:g}|{dt:g}|[결과]({r["analysis"]}/results.json)|')
    text+=['','## 증거 및 한계','',
      f'전체 및 대표 raw IEEE block 총 {full["raw_ieee_bytes"]+raw_total:,}bytes를 무손실 gzip {full["lossless_gzip_bytes"]+gzip_total:,}bytes로 저장했습니다. 요청한 파형 PNG, 각 point CSV, PMEM/DMEM, 원시자료, 설정백업 및 hash를 보존했습니다.',
      f'생산 Python {full["unchanged_production_source_files"]}파일 해시는 변경되지 않았습니다. 각 실행의 카운터·출력 정리·오실로스코프 복원을 확인했습니다. 기존 v5 보드를 사용했으며 새 합성·펌웨어 교체·서버 재시작·사용자 GUI 종료·사용자 JSON 수정은 하지 않았습니다.',
      '실제 GUI 입력 → 생산 컴파일러 → 현재 보드의 유한 프로그램 → 오실로스코프 경로입니다. RunWorker의 ADC/FIR/DDR/QCoDeS 취득이나 새 RTL 시뮬레이션을 이 검사로 대체하지 않습니다. 외부 RC 회로·정밀 아날로그 면적·모든 shot 내부 overflow는 검증하지 않았습니다.',
      '전체 sweep 준비 1조건은 모든 검사/manifest 저장 뒤 SIP 종료 접근 위반이 발생했습니다. 원본을 보존하고 종료 방식만 수정한 새 준비가 exit0이며 ASM/PMEM/DMEM·압축 해제 기대값·모델·GUI 입력이 동일함을 별도 감사했습니다. 기존 25개 성공 검사는 재사용하고 미실행 조건만 재개했습니다.',
      '초기 고해상도 준비의 Qt 접근 위반은 컴파일/장비 출력 전 발생했습니다. 원인 미확정 상태로 원본 폴더·로그·helper를 보존하고 고정 duration 입력을 실제 GUI에서 읽는 검토된 별도 시도로 준비했습니다. 해당 실패와 물리 측정 FAIL은 분리했습니다.', '',
      '- [전체100×100 상세판정](fullframe_summary_01/REPORT.md)',
      '- [전체집계 및 대표결과](results.json)',
      '- [실물실행 상태](physical_campaign_status.json)',
      '- [고해상도 실행상태](highres_campaign_status.json)',
      '- [첫DC/zero실패 raw독립검토](first_capture_failure_review.json)',
      '- 각analysis폴더에 full_record.png / representative_waveforms.png / primary_error_maps.png, highres폴더에 RAMP진단그림이 있습니다.','']
    (HERE/'REPORT.md').write_text('\n'.join(text),encoding='utf8')
    print(json.dumps(dict(main_conditions=full['physical_conditions'],main_points=full['physical_points'],highres_captures=24,all_requested_passed=False),indent=2))
if __name__=='__main__':main()
