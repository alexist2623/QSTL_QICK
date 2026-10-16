"""Independent CSV/hash audit of the 48 requested full-frame conditions.

No hardware calls. Does not aggregate high-resolution representative captures.
Writes a fresh summary directory only; never overwrites original evidence.
"""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
KEYS = ('PASS', 'FAIL', 'INCOMPLETE')


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def csv_read(path):
    with path.open(newline='', encoding='utf8') as stream:
        return list(csv.DictReader(stream))


def counts(rows, key, error_key, minimum):
    result = Counter()
    for row in rows:
        value = row[key]
        assert value in ('True', 'False', '')
        if value == '':
            result['INCOMPLETE'] += 1
            assert row[error_key] == ''
        else:
            assert int(row['samples']) >= minimum
            passed = abs(float(row[error_key])) <= 15.
            assert passed == (value == 'True')
            result['PASS' if passed else 'FAIL'] += 1
    return {k: result[k] for k in KEYS}


def check_identities(rows, count=20000):
    assert len(rows) == count
    assert {(int(r['point']), int(r['scope_channel'])) for r in rows} == {(p, ch) for p in range(10000) for ch in (1, 2)}


def condition_from_label(label):
    match = re.fullmatch(r'(rising|falling)_dac(4|5)_(fixed_voltage|fixed_time(10|20|30))_tau(10|20|30)', label)
    assert match, label
    direction, dac, dc, dc_time, tau = match.groups()
    return dict(swept_ramp=direction, active_axis=int(dac) - 4,
                mode='fixed_voltage' if dc == 'fixed_voltage' else 'fixed_time',
                tau_us=float(tau), dc_time_us=float(dc_time) if dc_time else None)


def check_condition(record, condition, *, tau_key, shape=False, hold_key=None):
    """Bind artifact metadata to its requested label, independent of file names."""
    for key in ('swept_ramp', 'active_axis', 'mode'):
        assert record[key] == condition[key], (key, record[key], condition[key])
    assert record[tau_key] == condition['tau_us']
    if condition['mode'] == 'fixed_voltage':
        assert record['dc_voltage_mv'] == 300.
    else:
        assert record['dc_time_us'] == condition['dc_time_us']
    if hold_key is not None:
        assert record[hold_key] == 10.
    if shape:
        assert record['duration_count'] == record['voltage_count'] == 100
        assert record['sweep_shape'] == [100, 100]
        assert record['requested_range_mv'] == [-400., 400.]
        assert record['requested_ramp_range_us'] == [.01, 1.]
        assert record['duration_range_us'] == [.01, 1.]


def check_artifact_bindings(case, analysis_case, manifest, expected, measured, result):
    label = case['label']; condition = condition_from_label(label)
    assert case['prepared'] == analysis_case['prepared'] == f'offline_{label}'
    assert case['run'] == analysis_case['run'] == result['source_run']
    assert case['run'].startswith(f'run_{label}_')
    assert analysis_case['analysis'].startswith(f'analysis_{label}_')
    assert result['prepared_bundle'] == measured['prepared_bundle'] == case['prepared']
    check_condition(manifest, condition, tau_key='tau_us', shape=True, hold_key='hold_us')
    check_condition(expected, condition, tau_key='rc_tau_us', shape=True, hold_key='plateau_duration_us')
    check_condition(result, condition, tau_key='rc_tau_us')
    assert manifest['points'] == expected['point_count'] == 10000
    assert expected['identity_matrix'] is True
    assert result['requested_range_mv'] == [-400., 400.]
    assert result['requested_ramp_range_us'] == [.01, 1.]
    for key in ('swept_ramp', 'active_axis', 'mode'):
        assert measured[key] == condition[key]
    assert measured['rc_tau_us'] == condition['tau_us'] and measured['high_resolution'] is False


def audit_preparation(expected_labels, protect):
    """Preserve the original SIP failure and require the reviewed identical retry."""
    names = ('preparation_batch_status.json', 'preparation_resume_status.json',
             'preparation_merged_status.json', 'preparation_resume_retry_comparison.json',
             'preparation_qt_failure_review.json', 'preparation_qt_failure_windows_event.json')
    old, resume, merged, comparison, review, event = [read(HERE / name) for name in names]
    for name in names:
        protect(HERE / name)
    assert old['complete'] is False and old['status'] == 'stopped_after_unexpected_failure'
    assert old['offline_prepared'] == resume['reused_exit0_count'] == 25
    assert resume['complete'] is True and resume['status'] == 'finished' and merged == resume
    assert resume['reviewed_retry_count'] == 1 and resume['pending_at_start'] == 22
    assert resume['physical_execution'] is False
    assert resume['frozen_original_status_sha256'] == sha(HERE / names[0])
    assert resume['retry_comparison_sha256'] == sha(HERE / names[3])
    assert resume['helper_sha256'] == sha(HERE / 'prepare_main_resume.py')
    protect(HERE / 'prepare_main_resume.py')
    assert len(resume['cases']) == 48 and {c['label'] for c in resume['cases']} == expected_labels
    prepared = {c['label']: c for c in resume['cases']}
    old_cases = {c['label']: c for c in old['cases']}
    retry_label = 'rising_dac5_fixed_voltage_tau30'
    assert comparison['case'] == review['case'] == retry_label
    assert old_cases[retry_label]['status'] == 'unexpected_failure'
    retry_case = prepared[retry_label]
    assert retry_case['original_attempt_status'] == 'unexpected_failure'
    assert retry_case['exit_code'] == comparison['retry_exit_code'] == 0
    assert comparison['status'] == 'passed' and comparison['original_preserved'] is True
    assert comparison['physical_execution'] is False
    assert all(comparison[key] is True for key in ('all_pmem_dmem_identical',
        'uncompressed_expected_points_identical', 'uncompressed_model_events_identical'))
    assert review['complete_artifacts_hash_valid'] and review['model_ended'] and review['all_dc_residuals_zero']
    assert review['windows_fault_module'] == 'sip.cp312-win_amd64.pyd'
    assert review['windows_exception'] == '0xc0000005'
    assert 'sip.cp312-win_amd64.pyd' in event['Message'] and '0xc0000005' in event['Message']
    original = Path(comparison['original_directory']).resolve()
    retry = Path(comparison['retry_directory']).resolve()
    assert original == (HERE / f'offline_{retry_label}').resolve()
    assert retry.parent == HERE and retry.name == f'offline_{retry_label}_retry01'
    assert Path(retry_case['output_dir']).resolve() == original
    assert Path(retry_case['successful_preparation_output_dir']).resolve() == retry
    for folder, helper_key in ((original, 'original_helper_sha256'), (retry, 'retry_helper_sha256')):
        manifest = read(folder / 'manifest.json'); protect(folder / 'manifest.json')
        assert manifest['helper_sha256'] == comparison[helper_key]
        for filename, digest in manifest['files'].items():
            assert sha(folder / filename) == digest
            protect(folder / filename)
    required = {f'{base}.{suffix}' for base in ('sweep', 'zero_recovery', 'paired_dds_idle')
                for suffix in ('asm', 'pmem', 'dmem.json')}
    required |= {'expected_points.json.gz', 'sweep_model.json.gz', 'gui_input.json',
                 'gui_arguments.json', 'zero_gui_input.json', 'source_before.json',
                 'source_after.json', 'compiler_compensation.json', 'preparation_summary.json'}
    assert required <= set(comparison['files'])
    for filename, item in comparison['files'].items():
        if filename.endswith('.gz'):
            assert item['uncompressed_identical'] is True
            for folder in (original, retry):
                data = gzip.decompress((folder / filename).read_bytes())
                assert hashlib.sha256(data).hexdigest() == item['uncompressed_sha256']
                assert len(data) == item['uncompressed_bytes']
                del data
        else:
            assert item['identical'] is True
            assert sha(original / filename) == sha(retry / filename) == item['sha256']
    for label, case in prepared.items():
        assert Path(case['output_dir']).resolve() == (HERE / f'offline_{label}').resolve()
        if case['status'] == 'offline_prepared':
            assert case['exit_code'] == 0
        else:
            assert case['status'] == 'range_rejected_not_executed' and case['exit_code'] == 1
            assert condition_from_label(label)['tau_us'] == 10.
        if old_cases[label]['status'] == 'offline_prepared':
            assert case['reused_verified_exit0_bundle'] is True and old_cases[label]['exit_code'] == 0
    assert sum(c['status'] == 'offline_prepared' for c in prepared.values()) == resume['offline_prepared'] == 32
    assert sum(c['status'] == 'range_rejected_not_executed' for c in prepared.values()) == resume['range_rejected'] == 16
    return dict(complete=True, original_batch_complete=False, original_failure_case=retry_label,
                original_failure='SIP 0xc0000005 after completed model/artifact checks',
                original_exit0_reused=25, reviewed_identical_retry_exit0=1, resumed_pending_cases=22,
                offline_prepared=32, range_rejected_not_executed=16,
                comparison_audit_passed=True, comparison=names[3], merged_status=names[2]), prepared


def audit_campaign():
    physical = read(HERE / 'physical_campaign_status.json')
    analyzed = read(HERE / 'analysis_campaign_status.json')
    assert physical['complete'] and analyzed['complete'] and analyzed['source_hashes_unchanged']
    expected_labels = {f'{direction}_dac{dac}_{dc}_tau{tau}' for direction in ('rising', 'falling')
                       for dac in (4, 5) for tau in (10, 20, 30)
                       for dc in ('fixed_voltage', 'fixed_time10', 'fixed_time20', 'fixed_time30')}
    assert len(physical['cases']) == len(analyzed['cases']) == 48
    assert {r['label'] for r in physical['cases']} == {r['label'] for r in analyzed['cases']} == expected_labels
    analysis_cases = {r['label']: r for r in analyzed['cases']}
    rows, rejected = [], []
    sources, capture_ids = {}, set()
    raw_bytes = gzip_bytes = 0
    input_hashes = {}

    def protect(path):
        input_hashes[str(path)] = sha(path)

    for path in (HERE / 'physical_campaign_status.json', HERE / 'analysis_campaign_status.json', Path(__file__)):
        protect(path)
    preparation, prepared_cases = audit_preparation(expected_labels, protect)
    for case in physical['cases']:
        label = case['label']; bundle = HERE / case['prepared']; analysis_case = analysis_cases[label]
        assert bundle.parent == HERE
        condition = condition_from_label(label)
        assert case['prepared'] == analysis_case['prepared'] == f'offline_{label}'
        before = read(bundle / 'source_before.json')
        protect(bundle / 'source_before.json')
        for path, digest in before.items():
            if path in sources:
                assert sources[path] == digest
            else:
                assert sha(Path(path)) == digest, path
                sources[path] = digest
        if case['status'] == 'range_rejected_not_run':
            assert prepared_cases[label]['status'] == 'range_rejected_not_executed'
            assert analysis_case['status'] == 'range_rejected_not_run'
            failure_path = bundle / 'preparation_failure.json'; failure = read(failure_path); protect(failure_path)
            check_condition(failure, condition, tau_key='tau_us', shape=True, hold_key='hold_us')
            assert failure['physical_execution'] is False
            error = failure['error']
            assert 'RC' in error and ('range' in error.lower() or 'limit' in error.lower())
            assert case['physical_execution'] is False and analysis_case['physical_execution'] is False
            rejected.append(dict(label=label, status='range_rejected_not_run', error=error, prepared=bundle.name))
            continue
        assert case['status'] == 'acquired' and analysis_case['status'] == 'analyzed'
        assert prepared_cases[label]['status'] == 'offline_prepared'
        run = HERE / case['run']; analysis = HERE / analysis_case['analysis']
        assert run.parent == analysis.parent == HERE
        result = read(analysis / 'results.json'); measured = read(run / 'status.json')
        manifest = read(bundle / 'manifest.json')
        with gzip.open(bundle / 'expected_points.json.gz', 'rt', encoding='utf8') as stream:
            expected = json.load(stream)
        check_artifact_bindings(case, analysis_case, manifest, expected, measured, result)
        del expected
        protect(run / 'status.json')
        assert measured['acquisition_success'] and measured['sweep_completed'] and measured['cleanup_zero']
        assert measured['scope_restore']['passed'] and not measured['production_sources_changed']
        progress = [e for e in measured['events'] if e['name'] in ('voltage_sweep', 'ramp_voltage_sweep')]
        assert len(progress) == 1 and progress[0]['progress'][-1] == [10000, 10000]
        assert result['analysis_complete'] and result['integrity_passed'] and result['input_hashes_unchanged']
        assert result['failure_threshold_mv'] == 15. and result['new_hardware_execution'] is False
        assert result['capture_id'] == measured['capture_id'] == analysis_case['capture_id']
        assert result['capture_id'] not in capture_ids
        capture_ids.add(result['capture_id'])
        for folder in (bundle, analysis):
            manifest_path = folder / 'manifest.json'; protect(manifest_path)
            for name, item in read(manifest_path)['files'].items():
                digest = item['sha256'] if isinstance(item, dict) else item
                assert sha(folder / name) == digest, str(folder / name)
        for path, digest in read(analysis / 'input_hashes.json').items():
            assert sha(Path(path)) == digest, path
            input_hashes[path] = digest
        assert read(run / 'live_current_before.json') == read(run / 'live_current_after.json')
        holds = csv_read(analysis / 'all_20000_holds.csv'); check_identities(holds)
        assert all(r['roi_valid'] == 'True' and abs((float(r['roi_end_scope_s']) - float(r['roi_start_scope_s'])) * 1e6 - 5) < 1e-6 for r in holds)
        active = [r for r in holds if r['active_output'] == 'True']
        inactive = [r for r in holds if r['active_output'] == 'False']
        assert len(active) == len(inactive) == 10000
        assert all(float(r['requested_mv']) == 0. for r in inactive)
        active_counts = counts(active, 'primary_pass', 'primary_median_error_mv', 10)
        inactive_counts = counts(inactive, 'primary_pass', 'primary_median_error_mv', 10)
        assert active_counts == result['active_primary_counts'] and inactive_counts == result['inactive_zero_counts']
        assert counts(holds, 'primary_pass', 'primary_median_error_mv', 10) == result['primary_channel_counts']
        assert counts(holds, 'compiled_pass', 'compiled_median_error_mv', 10) == result['compiled_channel_counts']
        failed_points = {int(r['point']) for r in holds if r['primary_pass'] == 'False'}
        assert len(failed_points) == result['primary_point_counts']['FAIL']
        verdict_rows = csv_read(analysis / 'all_10000_point_verdicts.csv')
        assert len(verdict_rows) == 10000
        assert {int(r['point']) for r in verdict_rows if r['primary_verdict'] == 'FAIL'} == failed_points
        dc_rows = csv_read(analysis / 'all_20000_dc_windows.csv'); check_identities(dc_rows)
        applicable = [r for r in dc_rows if r['compensation_applicable'] == 'True']
        skipped = [r for r in dc_rows if r['compensation_applicable'] == 'False']
        assert len(applicable) == len(skipped) == 10000 and all(r['passed'] == '' and r['note'].startswith('N/A:') for r in skipped)
        dc_counts = counts(applicable, 'passed', 'median_error_mv', 3)
        assert dc_counts == result['dc_diagnostics']['central_compensation']
        assert result['dc_diagnostics']['inactive_compensation_not_applicable'] == len(skipped)
        zero_rows = csv_read(analysis / 'all_20000_post_dc_zero_windows.csv'); check_identities(zero_rows)
        zero_counts = counts(zero_rows, 'passed', 'median_error_mv', 3)
        assert zero_counts == result['dc_diagnostics']['post_dc_zero']
        align = csv_read(analysis / 'row_alignment.csv')
        assert len(align) == len({r['matched_crossing_index'] for r in align}) == 100
        assert all(abs(float(r['residual_us'])) < 2. for r in align)
        capture = read(run / 'scope_capture/capture.json')
        assert capture['same_acquisition'] and capture['capture_id'] == result['capture_id']
        for channel in capture['channels'].values():
            archive = channel['archive']; path = run / 'scope_capture' / Path(archive['path']).name
            assert sha(path) == archive['gzip_sha256']
            raw = gzip.decompress(path.read_bytes())
            assert hashlib.sha256(raw).hexdigest() == archive['raw_sha256'] and len(raw) == archive['raw_bytes']
            digits = int(chr(raw[1])); begin = 2 + digits; size = int(raw[2:begin])
            assert hashlib.sha256(raw[begin:begin + size]).hexdigest() == channel['payload_sha256']
            assert not any(channel['special_codes'].values()) and channel['preamble']['x_increment'] <= 5e-7
            raw_bytes += len(raw); gzip_bytes += path.stat().st_size
        rows.append(dict(label=label, active_axis=result['active_axis'], swept_ramp=result['swept_ramp'], mode=result['mode'],
            tau_us=result['rc_tau_us'], dc_time_us=result['dc_time_us'], active_counts=active_counts, inactive_counts=inactive_counts,
            primary_point_pass=10000 - len(failed_points), primary_point_fail=len(failed_points),
            max_primary_error_mv=result['maximum_primary_median_error_mv'], dc_counts=dc_counts,
            inactive_dc_not_applicable=len(skipped), post_dc_zero_counts=zero_counts,
            final_zero_passed=all(r['valid'] and r['passed'] is True for r in result['dc_diagnostics']['final_zero'].values()),
            maximum_row_residual_us=max(abs(float(r['residual_us'])) for r in align),
            capture_id=result['capture_id'], analysis=analysis.name))
    assert len(rows) + len(rejected) == 48
    assert all(sha(Path(p)) == h for p, h in sources.items())
    assert all(sha(Path(p)) == h for p, h in input_hashes.items())
    total = lambda field: {k: sum(r[field][k] for r in rows) for k in KEYS}
    complete_waveforms = all(r['primary_point_fail'] == 0 and all(r[field]['FAIL'] == r[field]['INCOMPLETE'] == 0
                             for field in ('active_counts', 'inactive_counts', 'dc_counts', 'post_dc_zero_counts'))
                             and r['final_zero_passed'] for r in rows)
    result = dict(requested_conditions=48, range_rejected_not_run=len(rejected), physical_conditions=len(rows),
        physical_points=len(rows) * 10000, acquired_channel_windows=len(rows) * 20000,
        acquisition_and_analysis_integrity_passed=True, independent_csv_and_hash_audit_passed=True,
        active_primary_counts=total('active_counts'), inactive_zero_counts=total('inactive_counts'),
        primary_point_pass=sum(r['primary_point_pass'] for r in rows), primary_point_fail=sum(r['primary_point_fail'] for r in rows),
        maximum_primary_error_mv=max((r['max_primary_error_mv'] for r in rows), default=None),
        dc_counts=total('dc_counts'), inactive_dc_not_applicable=sum(r['inactive_dc_not_applicable'] for r in rows),
        post_dc_zero_counts=total('post_dc_zero_counts'), final_zero_all_passed=all(r['final_zero_passed'] for r in rows),
        all_acquired_waveform_checks_passed=complete_waveforms,
        all_requested_waveform_checks_passed=not rejected and complete_waveforms,
        unchanged_production_source_files=len(sources), raw_ieee_bytes=raw_bytes, lossless_gzip_bytes=gzip_bytes,
        high_resolution_included=False, cases=rows, rejected_conditions=rejected)
    result['preparation_review'] = preparation
    return result, input_hashes


def report(result):
    r = result
    text = ['# RAMP duration × 전압 100×100 실물 검증', '',
        f'요청 {r["requested_conditions"]}조건 중 {r["range_rejected_not_run"]}조건은 RC 출력 범위 검사에서 거부되어 실행하지 않았고, {r["physical_conditions"]}조건·{r["physical_points"]:,}점을 취득했습니다. 실행한 자료의 취득·분석·해시 무결성은 확인했습니다. 범위 거부와 측정 FAIL/미해결이 있으므로 요청 전체를 PASS로 표시하지 않습니다.', '',
        'DAC4(AWG1)→CH1, DAC5(AWG3)→CH2를 연결하고 한 출력만 활성화하며 반대 출력은 0V로 유지했습니다. 상승 또는 하강 RAMP 중 하나만 10ns~1µs 100점으로 sweep하고 다른 RAMP는 1µs로 고정했습니다. 전압은 −400~+400mV 100점이며 duration이 바깥 축, 전압이 안쪽 축입니다. HOLD10µs, identity matrix, RC τ10/20/30µs, DC 고정300mV 또는 고정10/20/30µs 조건입니다.', '',
        f'- 활성 출력 주 HOLD: {r["active_primary_counts"]}',
        f'- 비활성 출력 0V 유지: {r["inactive_zero_counts"]}',
        f'- 점 단위: PASS {r["primary_point_pass"]:,}, FAIL {r["primary_point_fail"]:,}; 어느 채널이라도 실패하면 해당 점은 FAIL입니다.',
        f'- 최대 중앙구간 절대 median 오차: {r["maximum_primary_error_mv"]:.6f}mV', '',
        '|RAMP|활성 DAC|RC τ(µs)|DC 모드|활성 HOLD FAIL|비활성 zero FAIL|DC FAIL / 미해결|파형|',
        '|---|---:|---:|---|---:|---:|---:|---|']
    for row in r['cases']:
        dc = '300mV 고정' if row['mode'] == 'fixed_voltage' else f'{row["dc_time_us"]:g}µs 고정'
        text.append(f'|{row["swept_ramp"]}|{row["active_axis"]+4}|{row["tau_us"]:g}|{dc}|{row["active_counts"]["FAIL"]:,}|{row["inactive_counts"]["FAIL"]:,}|{row["dc_counts"]["FAIL"]:,} / {row["dc_counts"]["INCOMPLETE"]:,}|[파형](../{row["analysis"]}/representative_waveforms.png)|')
    text += ['', '## 판정 기준과 한계', '',
        'DAC 직접 연결로 해석한 RC 선보상 기대값은 V요청×[1+(요청 상승RAMP 길이/2+HOLD 경과시간)/τ]입니다. 각 점의 상승 길이를 사용하며 실제 컴파일된 HOLD 시각을 기준으로 중앙5µs를 선택합니다. 1µs 상승에만 해당하는 0.5µs 항을 모든 점에 재사용하지 않습니다. 하강 sweep은 상승1µs를 그대로 사용합니다.',
        '출력 전 baseline에서 채널별 offset 하나만 정해 모든 점에 고정 적용하고 median(실측−기대값)의 절대값이15mV를 초과하면 FAIL입니다. gain·점별offset·점별시간 fitting은 없습니다. 이는 모든 샘플/전체 파형의 ±15mV 보장을 뜻하지 않습니다. 실제 정수 명령·RC 기대값은 별도 진단이며 요청 전압·길이 기준을 대체하지 않습니다.',
        '활성 채널의 첫 −200mV 하강 crossing으로 전체 기록에 시간 offset 하나를 적용하고, 실제 명령 시각으로100개 duration 행의 첫 edge를 검증했습니다. 각 행에 서로 다른 관측 edge가 대응하고 잔차는2µs 미만이어야 합니다. 전압·duration에 따라 변하는 point 간격을 고정 주기로 가정하지 않습니다.',
        '기록 간격은500ns 이하이고 중앙5µs에 최소10 native samples를 요구합니다. 이 전체 sweep 기록으로10ns RAMP 모양이나 정밀 길이를 인증하지 않습니다. 정렬 잔차·수직 양자화·아날로그 대역폭은 제거하지 않았으므로 FAIL 원인을 바로 RTL/DAC gain으로 단정할 수 없습니다. 별도 high-resolution 대표 측정은 이 집계에 포함하지 않았습니다.', '',
        '## DC 보상 및 zero', '',
        f'활성 출력 DC 중앙구간: {r["dc_counts"]}. 비활성 출력 DC {r["inactive_dc_not_applicable"]:,}구간은 면적0·zero-valued 명령으로 N/A이며 보상 pulse 성공 수에 포함하지 않았습니다. 비활성 출력은 주 HOLD와 DC 뒤 zero로 별도 검사했습니다.',
        f'DC 뒤 zero: {r["post_dc_zero_counts"]}. 전체 종료 뒤 두 채널 zero 모두 PASS={r["final_zero_all_passed"]}.',
        '활성 DC 구간에서 native 표본이3개 미만이면 INCOMPLETE로 남겼으며 PASS로 합산하지 않았습니다. 보상 구간의 정밀 폭·아날로그 면적 적분·외부 RC 회로 상태·모든 shot의 내부 overflow를 측정한 것은 아닙니다.', '',
        '## 준비 단계 최초 실패와 검토된 재실행', '',
        '최초 준비 batch는 25조건 exit0 뒤 rising_dac5_fixed_voltage_tau30의 모델·파일 작성이 끝난 후 SIP 0xc0000005 접근 위반으로 종료됐습니다. 최초 complete=false 및 Windows 오류 기록을 보존했습니다. 독립 CLI 종료 처리만 적용한 새 검증 helper로 같은 조건을 다시 실행하여 exit0을 확인하고, ASM/PMEM/DMEM·압축 해제 기대값/모델·GUI/컴파일러 자료가 원본과 동일함을 해시로 재검사했습니다.',
        '기존 exit0 25조건은 재실행하지 않았으며 검토된 재실행1조건과 남은22조건 재개 결과를 별도로 합쳤습니다. 최종 준비 결과는32조건 준비 완료·16조건 RC 범위 거부입니다. 최초 오류를 물리 측정 FAIL과 섞거나 원래부터 exit0였다고 표시하지 않습니다.',
        '- [원본 준비 상태](../preparation_batch_status.json), [재실행 대조](../preparation_resume_retry_comparison.json), [병합 준비 상태](../preparation_merged_status.json)', '',
        '## 보존 및 실행 범위', '',
        f'전체 두 채널 raw IEEE block {r["raw_ieee_bytes"]:,}bytes를 무손실 gzip {r["lossless_gzip_bytes"]:,}bytes로 보존하고 압축 해제 SHA256과 payload SHA256을 재대조했습니다. 생산 소스 {r["unchanged_production_source_files"]}파일 해시, 실행 전후 DAC current, 완료 counter, zero 정리 및 scope 복원을 확인했습니다.',
        '실제 GUI 설정 → 생산 컴파일러 → 기존 v5 하드웨어 → 두 채널 SINGLE 취득 경로입니다. 실물 실행은 run_physical.py가 수행했고 이 집계기는 보존된 자료를 오프라인 분석했습니다. 새 합성·펌웨어 교체·생산 코드 수정은 없었습니다. GUI RunWorker의 ADC/FIR/DDR/QCoDeS 경로 또는 새 RTL 시뮬레이션 PASS로 표현하지 않습니다.', '',
        '- [독립 집계](results.json)', '- [검토 입력 해시](input_hashes.json)',
        '- [전체 물리 실행 기록](../physical_campaign_status.json)', '- [전체 분석 기록](../analysis_campaign_status.json)', '',
        '## 범위 거부: 물리 실행 없음', '']
    text += [f'- {row["label"]}: `{row["error"]}`' for row in r['rejected_conditions']]
    return '\n'.join(text) + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='fullframe_summary_01')
    args = parser.parse_args()
    out = (HERE / args.output).resolve()
    if out.parent != HERE or out.exists():
        raise ValueError('Use a fresh direct-child summary directory')
    result, inputs = audit_campaign()
    out.mkdir()
    dump(out / 'results.json', result); dump(out / 'input_hashes.json', inputs)
    (out / 'REPORT.md').write_text(report(result), encoding='utf8')
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    dump(out / 'manifest.json', dict(audit_passed=True, source_hashes_unchanged=True,
        files={p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in out.iterdir() if p.is_file()}))
    print(json.dumps({k: v for k, v in result.items() if k not in ('cases', 'rejected_conditions')}, indent=2))


if __name__ == '__main__':
    main()
