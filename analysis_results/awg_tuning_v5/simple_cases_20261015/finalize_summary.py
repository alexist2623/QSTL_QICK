"""Aggregate the completed checks without hiding unsupported or failed cases."""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(relative):
    return json.loads((HERE / relative).read_text(encoding='utf-8'))


def main():
    destination = HERE / 'results.json'
    if destination.exists():
        raise FileExistsError('Preserve existing aggregate')
    software = read('software_regression/pytest_results.json')
    software_run = read('software_regression/run_finished.json')
    gui = read('gui_cases/batch_status.json')
    rtl = read('rtl/reporting/summary.json')
    protected = read('preservation_audit.json')
    assert gui['complete'] and len(gui['cases']) == 38
    assert all(case['exit_code'] == 0 for case in gui['cases'])
    counts = dict(Counter(case['result']['status'] for case in gui['cases']))
    assert counts == gui['status_counts']
    assert software_run['process_returncode'] == software['pytest_exitstatus'] == 0
    assert software['counts'] == {'passed': 110, 'failed': 0, 'skipped': 0, 'not_run': 0}
    assert rtl['complete'] and rtl['passed'] and rtl['archive_verified'] and rtl['source_hashes_match']
    assert protected['unchanged']
    result = {
        'complete': True,
        'validation_status': 'completed_with_findings',
        'all_requested_features_passed': False,
        'software': {'unique_tests': software['unique_collected'], 'counts': software['counts']},
        'gui': {'planned_cases': 38, 'status_counts': counts,
                'layer': 'offscreen actual Qt -> production compiler -> instruction model',
                'cases': [{'name': c['name'], 'status': c['result']['status'], 'folder': c['folder'],
                           'error': c['result'].get('error'), 'reason': c['result'].get('reason')}
                          for c in gui['cases']]},
        'rtl': rtl,
        'preservation': protected,
        'physical_board_or_scope_measurement': False,
        'production_modified': False,
        'unimplemented_todo_features': ['register-arithmetic RF duration sweep', 'grouped parameter sweeps'],
        'deferred': ['physical board/scope Run-worker validation and complete measured waveform archive',
                     'analog timing, frequency, voltage calibration and ADC/FIR arithmetic',
                     'scope trigger/transfer timeout and live hardware cancellation recovery'],
        'coverage_limit': 'Ten log-grid HOLD and ten log-grid RAMP GUI/model cases; RF has twelve boundary/containment cases and one frequency case. This is not the complete future physical TODO campaign.'
    }
    destination.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'complete': True, 'gui': counts, 'software': software['counts'],
                      'rtl': rtl['totals'], 'protected_files': protected['files']}))


if __name__ == '__main__':
    main()
