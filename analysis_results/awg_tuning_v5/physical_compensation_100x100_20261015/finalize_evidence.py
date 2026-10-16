"""Independent count/hash audit and campaign report; no instrument access."""
import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
def read(path): return json.loads(path.read_text(encoding='utf8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,value): path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf8')

def main():
    status=read(HERE/'physical_campaign_status.json')
    assert status['complete'] and len(status['cases'])==12
    rows=[]; raw_bytes=gzip_bytes=0; source_count=0
    for case in status['cases']:
        label=case['label']; bundle=HERE/case['prepared']; run=HERE/case['run']
        analysis=HERE/f'analysis_{label}_01'
        result=read(analysis/'results.json'); measured=read(run/'status.json')
        manifest=read(bundle/'manifest.json'); ana_manifest=read(analysis/'manifest.json')
        assert measured['acquisition_success'] and measured['sweep_completed']
        assert measured['cleanup_zero'] and measured['scope_restore']['passed']
        assert not measured['production_sources_changed']
        assert result['integrity_passed'] and result['input_hashes_unchanged']
        assert result['capture_id']==measured['capture_id']
        for name,digest in manifest['files'].items(): assert sha(bundle/name)==digest
        for name,item in ana_manifest['files'].items(): assert sha(analysis/name)==item['sha256']
        sources=read(bundle/'source_before.json'); source_count=len(sources)
        assert all(sha(Path(p))==h for p,h in sources.items())
        assert read(run/'live_current_before.json')==read(run/'live_current_after.json')
        with (analysis/'all_20000_holds.csv').open(newline='',encoding='utf8') as stream:
            holds=list(csv.DictReader(stream))
        assert len(holds)==20000
        assert {(int(r['point']),int(r['scope_channel'])) for r in holds}=={(p,ch) for p in range(10000) for ch in (1,2)}
        counter=Counter(); point_failed=set(); channel_failed=Counter()
        for h in holds:
            assert h['roi_valid']=='True' and int(h['samples'])>=10
            passed=abs(float(h['primary_median_error_mv']))<=15.
            assert passed==(h['primary_pass']=='True')
            counter['PASS' if passed else 'FAIL']+=1
            if not passed:
                point_failed.add(int(h['point']));channel_failed[h['scope_channel']]+=1
        assert counter['PASS']==result['primary_channel_counts']['PASS']
        assert counter['FAIL']==result['primary_channel_counts']['FAIL']
        assert len(point_failed)==result['primary_point_counts']['FAIL']
        capture=read(run/'scope_capture/capture.json')
        for channel in capture['channels'].values():
            archive=channel['archive']; path=run/'scope_capture'/Path(archive['path']).name
            assert sha(path)==archive['gzip_sha256']
            raw=gzip.decompress(path.read_bytes())
            assert hashlib.sha256(raw).hexdigest()==archive['raw_sha256']
            assert len(raw)==archive['raw_bytes'] and not any(channel['special_codes'].values())
            raw_bytes+=len(raw);gzip_bytes+=path.stat().st_size
        dc=result['dc_diagnostics']
        for field in ('central_compensation','post_dc_zero'):
            assert sum(dc[field].values())==20000
        row=dict(label=label,mode=result['mode'],tau_us=result['rc_tau_us'],dc_time_us=result['dc_time_us'],
                 main_pass_points=10000-len(point_failed),main_fail_points=len(point_failed),
                 main_pass_channels=counter['PASS'],main_fail_channels=counter['FAIL'],
                 ch1_fail=channel_failed['1'],ch2_fail=channel_failed['2'],
                 max_error_mv=result['maximum_primary_median_error_mv'],
                 dc_counts=dc['central_compensation'],post_dc_zero_counts=dc['post_dc_zero'],
                 final_zero_passed=all(r['passed'] for r in dc['final_zero'].values()),
                 capture_id=result['capture_id'],analysis=analysis.name)
        rows.append(row)
    overall=dict(physical_cases=12,physical_points=120000,main_channel_measurements=240000,
        acquisition_integrity_passed=True,independent_csv_and_hash_audit_passed=True,
        main_pass_points=sum(r['main_pass_points'] for r in rows),main_fail_points=sum(r['main_fail_points'] for r in rows),
        main_fail_channels=sum(r['main_fail_channels'] for r in rows),
        max_primary_error_mv=max(r['max_error_mv'] for r in rows),
        dc_counts={k:sum(r['dc_counts'][k] for r in rows) for k in ('PASS','FAIL','INCOMPLETE')},
        post_dc_zero_counts={k:sum(r['post_dc_zero_counts'][k] for r in rows) for k in ('PASS','FAIL','INCOMPLETE')},
        final_zero_all_passed=all(r['final_zero_passed'] for r in rows),
        source_files_unchanged=source_count,raw_ieee_bytes=raw_bytes,lossless_gzip_bytes=gzip_bytes,
        all_requested_waveform_checks_passed=all(r['main_fail_points']==0 and r['dc_counts']['FAIL']==0 and
          r['dc_counts']['INCOMPLETE']==0 and r['post_dc_zero_counts']['FAIL']==0 and
          r['post_dc_zero_counts']['INCOMPLETE']==0 and r['final_zero_passed'] for r in rows),
        cases=rows)
    dump(HERE/'results.json',overall)
    text=['# DC·RC 보상 100×100 실물 sweep 결과','',
      '**12조건·120,000점 출력 및 취득을 완료했습니다. 모든 취득/명령/기록 무결성 검사는 PASS이며, 15 mV 전압 기준은 전체 PASS가 아닙니다.**','',
      'DAC4(AWG generator1)→CH1, DAC5(generator3)→CH2에서 두 축 각각 −300~+300mV 100점, identity matrix를 사용했습니다. 각 점은 10µs zero → 1µs RAMP → 10µs HOLD → 1µs RAMP → 10µs zero 및 하드웨어 DC 보상입니다. RC τ=10/20/30µs 각각에 DC 고정 전압300mV 또는 고정 시간10/20/30µs를 조합했습니다.',
      '',f'주 HOLD 판정은 **120,000점 중 PASS {overall["main_pass_points"]:,}, FAIL {overall["main_fail_points"]:,}**입니다. 두 채널 중 하나라도 실패하면 그 점은 FAIL입니다. 총240,000개 채널 측정 중 FAIL {overall["main_fail_channels"]:,}, 최대 절대 중앙구간 오차 {overall["max_primary_error_mv"]:.6f}mV입니다.','',
      '|RC τ(µs)|DC 모드|주 HOLD 실패점 /10,000|CH1 실패|CH2 실패|최대 오차(mV)|파형|',
      '|---:|---|---:|---:|---:|---:|---|']
    for r in rows:
        dcname='고정 전압 300mV' if r['mode']=='fixed_voltage' else f'고정 시간 {r["dc_time_us"]:g}µs'
        text.append(f'|{r["tau_us"]:g}|{dcname}|{r["main_fail_points"]:,}|{r["ch1_fail"]:,}|{r["ch2_fail"]:,}|{r["max_error_mv"]:.3f}|[파형]({r["analysis"]}/representative_waveforms.png)|')
    text+=['','## 비교 기준과 검증 범위','',
      '이전 시험과 같은 DAC 직접 연결로 해석했습니다. 외부 RC/bias-tee 회로 통과 여부는 답변을 받지 못했으므로 외부 회로의 보상 성능을 검증했다고 주장하지 않습니다. RC가 켜진 DAC 출력은 요청 HOLD 전압에 적분 보상 기울기가 더해집니다. 따라서 평평한 요청 전압과 직접 비교하지 않고, 요청 V에 대한 이상적 RC 출력 V×[1+(0.5µs+HOLD 경과시간)/τ]를 기준으로 중앙5µs의 median(실측−기대값)을 판정했습니다.',
      '각 capture의 출력 시작 전 0V 구간에서 채널별 offset 하나만 구해 모든 점에 동일 적용했습니다. 절대 median 오차가 15mV를 초과하면 FAIL, 15mV 이하면 PASS입니다. 점별 offset·gain 보정·시간 이동은 하지 않았습니다. 실제 fixed-point 명령의 RC 기대값은 별도 진단 열에 저장했고, GUI 요청 전압의 양자화 오차를 숨기기 위해 기준을 바꾸지 않았습니다.',
      '실제 GUI 입력 → 생산 컴파일러의 PMEM/DMEM → 기존 보드의 유한 10,000점 실행 → 두 채널 SINGLE 취득 경로입니다. GUI RunWorker의 ADC/FIR/DDR/QCoDeS 경로 또는 새 RTL 시뮬레이션을 수행했다고 주장하지 않습니다. 모든 프로그램의 완료 counter는10,000/10,000이고, 각 실행 후 RC OFF+RESET·DC DISABLE·0V 정리 및 원래 scope 설정/STOP 상태 복원을 확인했습니다.',
      '', '## DC 보상과 종료 구간','',
      'DC 보상 중앙구간은 실제 컴파일 명령으로 만든 정수 면적·RC 기대값과 별도로 비교했습니다. 주 HOLD 판정에 섞어 숨기지 않습니다.',
      f'- DC 중앙구간: {overall["dc_counts"]}',f'- DC 뒤 zero 구간: {overall["post_dc_zero_counts"]}',
      f'- 전체 sweep 종료 뒤 zero: 모든 채널 PASS={overall["final_zero_all_passed"]}',
      '고정 전압 보상은 요청 면적이 작을 때 약0.1µs까지 짧아집니다. 이번 500ns 샘플 간격으로 충분한 표본을 얻지 못한 구간은 INCOMPLETE이며 PASS로 합산하지 않았습니다. 정확한 펄스 폭·면적 적분·아날로그 외부 RC 상태는 별도 고해상도 측정이 필요합니다. 내부 면적/overflow 레지스터는 현재 RPC로 관측하지 않았으며, 마지막 상태만으로 모든 shot의 내부 overflow0을 주장하지 않습니다.',
      '', '## 원시 자료와 보존','',
      f'두 채널 원시 IEEE block 총 {raw_bytes:,}bytes를 {gzip_bytes:,}bytes로 무손실 gzip 저장했습니다. 해제 후 원본 SHA256을 모두 대조했습니다. 각 capture의 preamble·설정·UUID·샘플과 모든 점 CSV/파형 그림을 보존했습니다. 기록 간격500ns, main HOLD 중앙5µs에최소10samples입니다. 이번1.6V scope range에서 관측된 수직code 간격은 약6.69456mV이며 gain fitting으로 제거하지 않았습니다.',
      f'생산 Python {source_count}파일 해시는 변경되지 않았습니다. 펌웨어/서버/RTL/사용자 JSON을 수정하지 않았습니다. 기존 범위0..400 및−400..400 준비증거와 검사기 초기 오류는 그대로 보존했습니다. −400..400·τ10의범위초과는 최종−300..300 시험 실패와 구분합니다. 준비용 normalized JSON 검사/step 부가 metadata 수정은 생산코드 변경이 아니며, 최종12개 bundle은 정정된 검증기로 새로 생성했습니다.',
      '', '- [전체 집계 및 독립 검산](results.json)', '- [측정 조건](campaign_plan.json)',
      '- [실제 실행 완료 기록](physical_campaign_status.json)',
      '- [독립 정수 RC 모델 및 검산](model_review/)',
      '- 각 analysis 폴더: all_20000_holds.csv, all_10000_point_verdicts.csv, DC/zero CSV, full_record.png, primary_error_maps.png, representative_waveforms.png',
      '', 'Git commit/push는 이 증거 및 보고서만 대상으로 합니다.']
    (HERE/'REPORT.md').write_text('\n'.join(text)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in overall.items() if k!='cases'},indent=2))

if __name__=='__main__': main()
