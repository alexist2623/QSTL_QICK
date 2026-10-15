"""Independent signed-16-bit DDS carrier/gain/relative-phase checks from RTL CSV."""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def wrap(degrees):
    return (degrees + 180.) % 360. - 180.


def check_case(case):
    results = []
    out = Path(case['case'])
    for path_index, path in enumerate(case['rf_checks']):
        source = out / f"physical_{path['suffix']}.csv"
        blocks = path['blocks']
        events = path['expected_events']
        samples = [[] for _ in blocks]
        with source.open() as stream:
            for row in csv.DictReader(stream):
                cycle = int(row['cycle'])
                for index, (start, end) in enumerate(blocks):
                    if start <= cycle < end:
                        word = int(row['rf'], 16)
                        samples[index].extend((((word >> (16*lane)) & 65535) + 32768) % 65536 - 32768
                                              for lane in range(16))
        fitted = []
        for index, ((start, end), values) in enumerate(zip(blocks, samples)):
            event = events[index % len(events)]
            expected_gain = float(case.get('expected_runtime_gains', [event['gain']]*3)[index % len(events)])
            assert expected_gain > 0, 'This new-feature fixture uses positive nonzero gain'
            frequency = float(event['frequency_mhz'])
            data = np.asarray(values, dtype=float)
            time_us = np.arange(len(data)) / 4800.
            basis = np.column_stack([np.sin(2*np.pi*frequency*time_us),
                                     np.cos(2*np.pi*frequency*time_us), np.ones(len(data))])
            coefficients = np.linalg.lstsq(basis, data, rcond=None)[0]
            amplitude = float(np.hypot(*coefficients[:2]))
            rms = float(np.sqrt(np.mean((basis @ coefficients - data)**2)))
            # DDS and multiplication truncate integer samples. These bounds are
            # measured in signed DAC codes, not a tolerance on pulse timing.
            assert abs(amplitude - expected_gain) < 2., (source, index, amplitude, expected_gain)
            assert rms < 1.2, (source, index, frequency, rms)
            absolute_phase = float(wrap(np.degrees(np.arctan2(coefficients[1], coefficients[0]))
                                        - 360*frequency*start/300.))
            fitted.append(dict(index=index, samples=len(values), frequency_mhz=frequency,
                               gain=expected_gain, fitted_amplitude=amplitude, rms_codes=rms,
                               time_referenced_phase_degrees=absolute_phase,
                               requested_phase_degrees=event['phase_degrees']))
        for repetition in range(2):
            shot = fitted[repetition*len(events):(repetition+1)*len(events)]
            reference = shot[0]
            assert all(item['frequency_mhz'] == reference['frequency_mhz'] for item in shot)
            for item in shot:
                error = wrap(item['time_referenced_phase_degrees'] - reference['time_referenced_phase_degrees']
                             - item['requested_phase_degrees'] + reference['requested_phase_degrees'])
                assert abs(error) < .05, (source, item, error)
                item['relative_phase_error_degrees'] = error
        results.append(dict(suffix=path['suffix'], bursts=fitted,
                            csv_sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    return dict(passed=True, case=str(out), paths=results,
                meaning='DDS components before sum; phase offsets against continuous carrier time reference',
                maximum_amplitude_error_codes=2., maximum_carrier_fit_rms_codes=1.2,
                maximum_relative_phase_error_degrees=.05)


if __name__ == '__main__':
    here = Path(__file__).resolve().parent
    state = json.loads((here / 'status.json').read_text())
    assert state['complete'] and state['stage'] == 'passed'
    cases = [check_case(case) for case in state['cases']]
    extra_file = here / 'hahn_status.json'
    if extra_file.exists():
        extra = json.loads(extra_file.read_text())
        assert extra['complete'] and extra['stage'] == 'passed'
        cases.extend(check_case(case) for case in extra['cases'])
    result = dict(passed=True, cases=cases, helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (here / 'carrier_checks.json').write_text(json.dumps(result, indent=2))
    print(f'PASS carrier frequency/gain/relative phase: {len(cases)} programs, '
          f'{sum(len(path["bursts"]) for case in cases for path in case["paths"])} DDS bursts')
