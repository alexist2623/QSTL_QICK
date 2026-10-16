"""Aggregate the twelve immutable offline analyses; no instrument access."""
from pathlib import Path
import csv
import hashlib
import json

HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text(encoding='utf8'))


def write_csv(p, rows):
    with p.open('x', newline='', encoding='utf8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def main():
    destination = HERE / 'all_condition_summary.json'
    if destination.exists():
        raise FileExistsError(destination)
    rows, failure_rows, proof_hashes, issues, source_hashes = [], [], {}, [], {}
    totals = {group: dict(PASS=0, FAIL=0, INCOMPLETE=0) for group in ('primary_channels', 'primary_points', 'compiled_channels', 'dc_central', 'post_dc_zero')}
    for tau in (10, 20, 30):
        for mode in ('fixed_voltage', 'fixed_time10', 'fixed_time20', 'fixed_time30'):
            label = f'{mode}_tau{tau}'
            folder = HERE / f'analysis_{label}_01'
            result = read(folder / 'results.json'); manifest = read(folder / 'manifest.json')
            capture_status = read(HERE / f'run_{label}_01/status.json')
            assert result['rc_tau_us'] == tau and result['requested_range_mv'] == [-300., 300.]
            assert result['failure_threshold_mv'] == 15. and result['analysis_complete']
            assert sum(result['primary_channel_counts'].values()) == 20000
            assert sum(result['primary_point_counts'].values()) == 10000
            assert capture_status['acquisition_success'] and capture_status['sweep_completed'] and capture_status['cleanup_zero']
            for name, item in manifest['files'].items():
                if sha(folder / name) != item['sha256']:
                    issues.append(f'{label}: changed derived file {name}')
            for name in ('analyze_physical.py', 'command_expectation.py', 'compact_expectation.py'):
                digest = sha(folder / name)
                source_hashes.setdefault(name, set()).add(digest)
            if not result['integrity_passed']:
                issues.append(f'{label}: {result["integrity_issues"]}')
            groups = dict(primary_channels=result['primary_channel_counts'], primary_points=result['primary_point_counts'],
                compiled_channels=result['compiled_channel_counts'], dc_central=result['dc_diagnostics']['central_compensation'],
                post_dc_zero=result['dc_diagnostics']['post_dc_zero'])
            for group, counts in groups.items():
                for verdict, number in counts.items():
                    totals[group][verdict] += number
            row = dict(condition=label, tau_us=tau, dc_mode=result['mode'], dc_time_us=result['dc_time_us'],
                dc_voltage_mv=result['dc_voltage_mv'], integrity_passed=result['integrity_passed'],
                primary_pass=groups['primary_channels']['PASS'], primary_fail=groups['primary_channels']['FAIL'],
                primary_incomplete=groups['primary_channels']['INCOMPLETE'], point_pass=groups['primary_points']['PASS'], point_fail=groups['primary_points']['FAIL'],
                compiled_fail=groups['compiled_channels']['FAIL'], dc_central_fail=groups['dc_central']['FAIL'],
                dc_central_unresolved=groups['dc_central']['INCOMPLETE'], post_dc_zero_fail=groups['post_dc_zero']['FAIL'],
                post_dc_zero_unresolved=groups['post_dc_zero']['INCOMPLETE'],
                primary_max_error_mv=result['maximum_primary_median_error_mv'], compiled_max_error_mv=result['maximum_compiled_median_error_mv'],
                ch1_offset_mv=result['fixed_offsets_mv']['1'], ch2_offset_mv=result['fixed_offsets_mv']['2'],
                single_time_offset_s=result['single_time_offset_s'],
                row_alignment_max_residual_us=read(folder / 'alignment.json')['maximum_row_residual_us'],
                final_zero_ch1_pass=result['dc_diagnostics']['final_zero']['1']['passed'],
                final_zero_ch2_pass=result['dc_diagnostics']['final_zero']['2']['passed'],
                result_path=str(folder / 'results.json'))
            rows.append(row)
            with (folder / 'all_20000_holds.csv').open(newline='', encoding='utf8') as stream:
                for sample in csv.DictReader(stream):
                    if sample['primary_pass'] == 'False':
                        failure_rows.append(dict(condition=label, point=int(sample['point']), scope_channel=int(sample['scope_channel']),
                            axis0=int(sample['axis0']), axis1=int(sample['axis1']), requested_mv=float(sample['requested_mv']),
                            compiled_nominal_mv=float(sample['compiled_nominal_mv']), primary_median_error_mv=float(sample['primary_median_error_mv']),
                            compiled_median_error_mv=float(sample['compiled_median_error_mv'])))
            for p in (folder / 'results.json', folder / 'manifest.json', HERE / f'run_{label}_01/status.json'):
                proof_hashes[str(p)] = sha(p)
    if any(len(values) != 1 for values in source_hashes.values()):
        issues.append('The twelve analyses did not use identical analyzer/helper sources')
    assert len(rows) == 12 and len(failure_rows) == totals['primary_channels']['FAIL']
    summary = dict(complete=True, physical_conditions=12, hardware_points=120000, channel_hold_observations=240000,
        integrity_passed=not issues, integrity_issues=issues, new_hardware_execution=False,
        primary_criterion='abs(median(measured - fixed baseline offset - GUI-requested ideal RC)) >15mV FAIL; <=15mV PASS',
        requested_range_mv=[-300, 300], hold_us=10, rc_tau_us=[10, 20, 30], dc_fixed_voltage_mv=300, dc_fixed_time_us=[10, 20, 30],
        all_primary_passed=not issues and totals['primary_channels']['FAIL'] == totals['primary_channels']['INCOMPLETE'] == 0,
        all_diagnostic_checks_resolved_and_passed=not issues and all(c['FAIL'] == c['INCOMPLETE'] == 0 for c in totals.values())
            and all(r['final_zero_ch1_pass'] and r['final_zero_ch2_pass'] for r in rows),
        totals=totals, conditions=rows, maximum_primary_median_error_mv=max(r['primary_max_error_mv'] for r in rows),
        maximum_row_alignment_residual_us=max(r['row_alignment_max_residual_us'] for r in rows),
        analyzer_source_hashes={k: sorted(v) for k, v in source_hashes.items()}, proof_sha256=proof_hashes,
        limitations=['Scope raw data remains in each run capture folder; this is offline aggregation, not another acquisition.',
            'Short fixed-voltage DC tails remain unresolved where central ROI contains fewer than three native samples.',
            'Primary GUI-requested ideal RC and exact compiled RC diagnostics are separate; quantization error is not removed.',
            'No per-point gain/time/offset fit, calibrated accuracy certification or precise duration/internal-area measurement.'])
    write_csv(HERE / 'all_condition_summary.csv', rows)
    if failure_rows:
        write_csv(HERE / 'all_primary_failures.csv', failure_rows)
    destination.write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps(dict(integrity_passed=summary['integrity_passed'], totals=totals,
        maximum_primary_median_error_mv=summary['maximum_primary_median_error_mv']), indent=2))


if __name__ == '__main__':
    main()
