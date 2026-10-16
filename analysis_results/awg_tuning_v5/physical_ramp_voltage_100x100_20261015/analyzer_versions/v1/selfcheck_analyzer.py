"""Short synthetic/offline regression for the new duration-axis analyzer.

Never opens a physical instrument. Does not claim a physical measurement.
Expected requested voltages are constructed independently of analyzer helpers.
"""
from copy import deepcopy
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import socket

import numpy as np

HERE = Path(__file__).resolve().parent


def deny_network(*args, **kwargs):
    raise RuntimeError('Analyzer selfcheck is offline only')


socket.create_connection = socket.socket.connect = socket.socket.connect_ex = deny_network
import analyze_physical as analyzer


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ZeroReference:
    def at_program_us(self, value):
        # Deliberately distinct from primary: catches accidental substitution.
        return {'expected_direct_dac_mv': 0.}


def make_output(voltage, rise, fall, tau, axis):
    cmd = dict(cycle=0, duration_samples=0, transport_target=0, step_signed=0)
    commands = [dict(cmd) for _ in range(6)]
    commands[1]['duration_samples'] = round(rise * 4800)
    commands[3]['duration_samples'] = round(fall * 4800)
    return dict(panel_dac=axis + 4, awg_gen=axis * 2 + 1, requested_mv=voltage,
                requested_rise_us=rise, requested_fall_us=fall,
                hold_digital_output_us=20., hold_end_digital_output_us=30.,
                quantized_mv=voltage, dac_code=round(voltage * 32768 / 801.48),
                rc_tau_us=tau, rc_coefficient=round(2**48 / (2 * tau * 4800)),
                commands=commands, pre_dc_area_effective_code_samples=0,
                dc_runs_effective14=[[16, 0]])


def fixture(active, swept):
    points = []
    for row in range(100):
        duration = (row + 1) / 100.
        rise, fall = (duration, 1.) if swept == 'rising' else (1., duration)
        for column in range(100):
            voltage = -400. + 800. * column / 99.
            outputs = [make_output(voltage if axis == active else 0., rise, fall, 20., axis) for axis in (0, 1)]
            points.append(dict(point_index=row * 100 + column, axis_indices=[row, column], outputs=outputs))
    return dict(points=points, active_axis=active, swept_ramp=swept,
                requested_ramp_range_us=[.01, 1.], requested_range_mv=[-400., 400.],
                plateau_duration_us=10., axis_count=100, rc_tau_us=20.)


def rejected(call):
    try:
        call()
    except (AssertionError, ValueError, KeyError):
        return
    raise AssertionError('Invalid evidence was accepted')


def main():
    target = HERE / 'analyzer_selfcheck.json'
    if target.exists():
        raise FileExistsError('Preserve prior selfcheck evidence; use a new script/result for a retry')
    source_paths = [Path(__file__), HERE / 'analyze_physical.py',
                    HERE / 'model_review/compact_expectation.py', HERE / 'model_review/command_expectation.py']
    hashes = {str(p): sha(p) for p in source_paths}
    schema_cases = 0
    for active in (0, 1):
        for swept in ('rising', 'falling'):
            expected = fixture(active, swept)
            assert analyzer.validate_expected(expected) == active
            schema_cases += 1
    invalid_cases = 0
    for field, value in [('requested_rise_us', .5), ('requested_mv', 1.), ('dac_code', 4)]:
        expected = fixture(0, 'falling')
        expected['points'][0]['outputs'][1][field] = value
        rejected(lambda: analyzer.validate_expected(expected))
        invalid_cases += 1
    expected = fixture(0, 'rising')
    expected['points'][100]['axis_indices'] = [0, 1]
    rejected(lambda: analyzer.validate_expected(expected)); invalid_cases += 1

    # Half-cycle-offset native sample times avoid accidental endpoint inclusion.
    times = np.arange(200, dtype=float) * .5e-6 - 20.25e-6
    offset, alignment = -23.25, .3e-6
    rows_checked = 0
    for tau in (10., 20., 30.):
        for row in range(100):
            rise = (row + 1) / 100.
            for voltage in (-400., 0., 400.):
                output = make_output(voltage, rise, 1., tau, 0)
                program_us = (times - alignment) * 1e6
                independent_reference = voltage + voltage * (.5 * rise + program_us - 20.) / tau
                for residual, passed in ((14.9, True), (-14.9, True), (15.1, False), (-15.1, False)):
                    channel = dict(time=times, voltage=(offset + independent_reference + residual) / 1000.)
                    result = analyzer.roi_row(channel, output, ZeroReference(), row * 100, 0, offset, alignment, 0)
                    assert result['roi_valid'] and result['samples'] == 10
                    assert math.isclose((result['roi_end_scope_s'] - result['roi_start_scope_s']) * 1e6, 5., abs_tol=1e-9)
                    assert math.isclose(result['primary_median_error_mv'], residual, abs_tol=1e-9)
                    assert result['primary_pass'] == passed
                    if voltage:
                        assert result['compiled_pass'] is False
                    rows_checked += 1
    output = make_output(0., .01, 1., 10., 1)
    channel = dict(time=times, voltage=np.full_like(times, (offset + 2.) / 1000.))
    zero = analyzer.roi_row(channel, output, ZeroReference(), 0, 1, offset, alignment, 0)
    assert zero['reference_kind'] == 'inactive_zero' and not zero['active_output'] and zero['primary_pass']
    short = analyzer.diagnostic_row(channel, ZeroReference(), 0, 1, 'dc_central_half', 20., 20.1, offset, alignment)
    assert not short['valid'] and short['passed'] is None
    assert analyzer.verdict_counts([short], 'passed') == dict(PASS=0, FAIL=0, INCOMPLETE=1)
    counts = analyzer.verdict_counts([{'passed': True}, {'passed': False}, {'passed': None}], 'passed')
    assert counts == dict(PASS=1, FAIL=1, INCOMPLETE=1)

    # Independently recorded old capture tests decode/anchor compatibility only;
    # it is never relabelled as a new RAMP-sweep physical run.
    prior = HERE.parent / 'physical_compensation_100x100_20261015'
    capture_folder = prior / 'run_fixed_voltage_tau10_01/scope_capture'
    capture = json.loads((capture_folder / 'capture.json').read_text())
    decoded = analyzer.load_channel(capture_folder, capture['channels']['2'])
    assert decoded['preamble']['x_increment'] == 5e-7 and not decoded['invalid'].any()
    prior_expected = analyzer.read(prior / 'offline_range300_fixed_voltage_tau10/expected_points.json.gz')
    original = prior_expected['points'][0]['outputs'][1]
    model = analyzer.output_model(original)
    crossing = analyzer.model_anchor_us(original, model)
    before, after = model.at_program_us(crossing - 1 / 4800.), model.at_program_us(crossing)
    assert before['expected_direct_dac_mv'] > -200. >= after['expected_direct_dac_mv']
    assert all(sha(p) == h for p, h in hashes.items())
    result = dict(passed=True, new_physical_measurement=False, network_access=False,
                  full_expected_schema_cases=schema_cases, rejected_bad_metadata_cases=invalid_cases,
                  synthetic_native_roi_checks=rows_checked, inactive_zero_checked=True,
                  unresolved_short_dc_remains_incomplete=True, primary_not_replaced_by_compiled=True,
                  prior_capture_decode_and_anchor_only=True, input_hashes=hashes,
                  limitations='Synthetic analyzer regression plus old capture decode only; no new physical sweep, timing accuracy, or RAMP shape validation')
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
