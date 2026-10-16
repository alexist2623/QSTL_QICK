"""Independent raw decoding/ROI audit of the first capture's diagnostic FAILs."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'model_review'))
from command_expectation import output_model


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = HERE / 'first_capture_failure_review.json'
    if target.exists():
        raise FileExistsError('Preserve review evidence')
    prepared = HERE / 'offline_rising_dac4_fixed_time10_tau20'
    analysis = HERE / 'analysis_rising_dac4_fixed_time10_tau20_01'
    capture = HERE / 'run_rising_dac4_fixed_time10_tau20_01/scope_capture'
    paths = [Path(__file__), prepared / 'expected_points.json.gz', capture / 'capture.json',
             analysis / 'fixed_offsets.json', analysis / 'alignment.json',
             analysis / 'all_20000_dc_windows.csv', analysis / 'all_20000_post_dc_zero_windows.csv',
             HERE / 'model_review/command_expectation.py', HERE / 'model_review/compact_expectation.py']
    paths += [capture / f'ch{ch}.ieee_block.bin.gz' for ch in (1, 2)]
    hashes = {str(p): sha(p) for p in paths}
    meta = json.loads((capture / 'capture.json').read_text())
    offsets = json.loads((analysis / 'fixed_offsets.json').read_text())
    alignment = json.loads((analysis / 'alignment.json').read_text())['single_time_offset_s']
    expected = json.loads(gzip.decompress((prepared / 'expected_points.json.gz').read_bytes()))
    arrays = {}
    for ch in ('1', '2'):
        record = meta['channels'][ch]; pre = record['preamble']
        block = gzip.decompress((capture / f'ch{ch}.ieee_block.bin.gz').read_bytes())
        assert hashlib.sha256(block).hexdigest() == record['archive']['raw_sha256']
        start = 2 + int(chr(block[1])); size = int(block[2:start])
        payload = block[start:start + size]
        assert hashlib.sha256(payload).hexdigest() == record['payload_sha256']
        codes = np.frombuffer(payload, dtype='<u2')
        assert len(codes) == pre['points']
        time = (np.arange(len(codes)) - pre['x_reference']) * pre['x_increment'] + pre['x_origin']
        measured_mv = ((codes.astype(float) - pre['y_reference']) * pre['y_increment'] + pre['y_origin']) * 1000.
        arrays[ch] = time, measured_mv - offsets[ch]['median_mv']
    checks = []
    for filename in ('all_20000_dc_windows.csv', 'all_20000_post_dc_zero_windows.csv'):
        with (analysis / filename).open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            if row['passed'] != 'False':
                continue
            point = int(row['point']); axis = int(row['scope_channel']) - 1
            output = expected['points'][point]['outputs'][axis]
            model = output_model(output)
            time, measured = arrays[row['scope_channel']]
            lo, hi = float(row['roi_start_scope_s']), float(row['roi_end_scope_s'])
            begin = int(np.searchsorted(time, lo)); end = int(np.searchsorted(time, hi, side='right'))
            assert begin == int(row['roi_start_index']) and end == int(row['roi_stop_index_exclusive'])
            program_us = (time[begin:end] - alignment) * 1e6
            exact = np.array([model.at_program_us(t)['expected_direct_dac_mv'] for t in program_us])
            actual = measured[begin:end]
            residual = float(np.median(actual - exact))
            assert abs(residual - float(row['median_error_mv'])) < 1e-9
            assert abs(residual) > 15.
            if row['kind'] == 'dc_central_half':
                left_margin = float(program_us.min() - output['dc_start_digital_output_us'])
                right_margin = float(output['dc_end_digital_output_us'] - program_us.max())
                assert left_margin >= 2.5 and right_margin >= 2.5
            else:
                left_margin = float(program_us.min() - output['dc_zero_reset_bound_us'])
                right_margin = None
                assert left_margin >= 1. and np.all(exact == 0.)
            checks.append(dict(kind=row['kind'], point=point, scope_channel=axis + 1,
                samples=end - begin, corrected_native_mv=actual.tolist(), exact_expected_native_mv=exact.tolist(),
                recomputed_median_error_mv=residual, roi_duration_us=(hi - lo) * 1e6,
                left_boundary_margin_us=left_margin, right_boundary_margin_us=right_margin))
    assert len(checks) == 10
    assert all(sha(Path(p)) == h for p, h in hashes.items())
    result = dict(passed=True, physical_access=False, reviewed_fail_windows=len(checks),
        conclusion='Raw decode, fixed offset, native ROI indices and per-sample expected values reproduce all diagnostic FAILs; no criterion changed.',
        limitations='2us post-DC windows contain only four native samples. Global alignment is not a precision timing fit. This review does not identify a hardware/noise/gain root cause.',
        input_hashes_unchanged=True, input_hashes=hashes, checks=checks)
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('checks', 'input_hashes')}, indent=2))


if __name__ == '__main__':
    main()
