"""Offline independent raw/native-ROI review of the first >20mV HOLD failure."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = HERE / 'main_failure_review_v2.json'
    if out.exists():
        raise FileExistsError('Preserve original review')
    label = 'rising_dac4_fixed_voltage_tau20'
    analysis = HERE / f'analysis_{label}_01'
    prepared = HERE / f'offline_{label}'
    capture = HERE / f'run_{label}_01/scope_capture'
    paths = [Path(__file__), analysis / 'all_20000_holds.csv', analysis / 'fixed_offsets.json',
             analysis / 'alignment.json', analysis / 'results.json', prepared / 'expected_points.json.gz',
             capture / 'capture.json', capture / 'ch1.ieee_block.bin.gz']
    hashes = {str(p): sha(p) for p in paths}
    metadata = json.loads((capture / 'capture.json').read_text())['channels']['1']
    pre = metadata['preamble']
    block = gzip.decompress((capture / 'ch1.ieee_block.bin.gz').read_bytes())
    assert hashlib.sha256(block).hexdigest() == metadata['archive']['raw_sha256']
    begin = 2 + int(chr(block[1])); size = int(block[2:begin]); payload = block[begin:begin + size]
    assert hashlib.sha256(payload).hexdigest() == metadata['payload_sha256']
    codes = np.frombuffer(payload, dtype='<u2')
    assert len(codes) == pre['points']
    times = (np.arange(len(codes)) - pre['x_reference']) * pre['x_increment'] + pre['x_origin']
    raw_mv = ((codes.astype(float) - pre['y_reference']) * pre['y_increment'] + pre['y_origin']) * 1000.
    offsets = json.loads((analysis / 'fixed_offsets.json').read_text())
    offset_mv = offsets['1']['median_mv']
    alignment = json.loads((analysis / 'alignment.json').read_text())['single_time_offset_s']
    expected = json.loads(gzip.decompress((prepared / 'expected_points.json.gz').read_bytes()))
    with (analysis / 'all_20000_holds.csv').open(newline='') as stream:
        failed = [r for r in csv.DictReader(stream) if r['primary_pass'] == 'False']
    checks = []
    for row in failed:
        assert row['scope_channel'] == '1' and row['active_output'] == 'True'
        point = int(row['point']); duration_index, voltage_index = divmod(point, 100)
        requested_mv = -400. + 800. * voltage_index / 99.
        requested_rise_us = .01 + .99 * duration_index / 99.
        assert abs(requested_mv - float(row['requested_mv'])) < 1e-10
        assert abs(requested_rise_us - float(row['requested_rise_us'])) < 1e-12
        output = expected['points'][point]['outputs'][0]
        hold_start = output['hold_digital_output_us'] * 1e-6 + alignment
        hold_end = output['hold_end_digital_output_us'] * 1e-6 + alignment
        assert abs(hold_start - float(row['hold_start_scope_s'])) < 1e-15
        assert abs(hold_end - hold_start - 10e-6) < 1e-12
        lo, hi = hold_start + 2.5e-6, hold_end - 2.5e-6
        start = int(np.searchsorted(times, lo)); stop = int(np.searchsorted(times, hi, side='right'))
        assert start == int(row['roi_start_index']) and stop == int(row['roi_stop_index_exclusive'])
        corrected = raw_mv[start:stop] - offset_mv
        elapsed_us = (times[start:stop] - hold_start) * 1e6
        ideal = requested_mv * (1. + (requested_rise_us / 2. + elapsed_us) / 20.)
        residual = float(np.median(corrected - ideal))
        assert abs(residual - float(row['primary_median_error_mv'])) < 1e-8
        assert abs(residual) > 15. and len(corrected) >= 10
        checks.append(dict(point=point, duration_index=duration_index, voltage_index=voltage_index,
                           requested_mv=requested_mv, requested_rise_us=requested_rise_us,
                           raw_adc_codes=codes[start:stop].astype(int).tolist(),
                           corrected_native_mv=corrected.tolist(), ideal_native_mv=ideal.tolist(),
                           elapsed_native_us=elapsed_us.tolist(), recomputed_median_error_mv=residual,
                           samples=len(corrected)))
    summary = json.loads((analysis / 'results.json').read_text())
    assert len(checks) == summary['active_primary_counts']['FAIL'] == 15
    worst = max(checks, key=lambda r: abs(r['recomputed_median_error_mv']))
    assert abs(abs(worst['recomputed_median_error_mv']) - summary['maximum_primary_median_error_mv']) < 1e-8
    assert all(sha(Path(p)) == value for p, value in hashes.items())
    result = dict(passed=True, physical_access=False, reviewed_condition=label, reviewed_failures=len(checks),
                  worst_failure=worst, fixed_offset_mv=offset_mv,
                  observed_code_increment_gcd=int(np.gcd.reduce(np.diff(np.unique(codes.astype(np.int64))))),
                  vertical_native_step_mv=pre['y_increment'] * int(np.gcd.reduce(np.diff(np.unique(codes.astype(np.int64))))) * 1000.,
                  previous_review_note='Original v1 arithmetic checks are unchanged. Its diagnostic vertical step incorrectly assumed 512 code counts; this version derives the actual 256-count increment from raw data. Original JSON and source are preserved.',
                  conclusion='Independent raw decoding and explicitly requested voltage/rise formula reproduce all 15 HOLD FAILs, including the >20mV case; native ROI indices and units match.',
                  limitations='This verifies analysis arithmetic only; it does not identify analog/noise/DAC/compiler root cause or change the 15mV criterion.',
                  input_hashes_unchanged=True, input_hashes=hashes, checks=checks)
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('checks', 'input_hashes')}, indent=2))


if __name__ == '__main__':
    main()
