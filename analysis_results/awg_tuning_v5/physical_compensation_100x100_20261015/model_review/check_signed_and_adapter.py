"""Small independent scalar checks for signed code/DC/RC and saved commands."""
import hashlib
import json
from pathlib import Path

from compact_expectation import Run, Waveform, clamp, compensation_runs
from command_expectation import output_model

ROOT = Path(__file__).resolve().parent
records = []
scalar_checks = 0
for tau in (10., 20., 30.):
    coefficient = round(2**48 / (2 * tau * 4800))
    for sign in (-1, 1):
        # Both slopes, signed half-code positions, forced final sample,
        # zero gaps, and both compensation polarities are present.
        start = sign * 16000
        body = [Run(16), Run(257, kind='ramp', start_transport=0,
                           target_transport=start, step=round(start * 2**18 / 257)),
                Run(480, code=start // 4),
                Run(257, kind='ramp', start_transport=start,
                    target_transport=0, step=round(-start * 2**18 / 257)), Run(32)]
        first = Waveform(body)
        assert (first.area > 0) == (sign > 0)
        for mode in ('fixed_voltage', 'fixed_time'):
            dc = compensation_runs(first.area, **({'amplitude_transport': 12000}
                                   if mode == 'fixed_voltage' else {'words': 100}))
            wave = Waveform(body + dc + [Run(32)])
            assert wave.area == 0
            previous = integral = 0
            for n in range(wave.samples):
                x = wave.raw_at(n) * 4
                integral += coefficient * (x + previous)
                previous = x
                expected = clamp(((x << 48) + integral + (1 << 49)) >> 50)
                assert wave.rc_effective_at(n, coefficient) == expected
                scalar_checks += 1
            assert integral == 0
            records.append(dict(tau_us=tau, sign=sign, mode=mode,
                coefficient=coefficient, pre_dc_area=first.area,
                dc_effective_code_runs=[(r.count, r.code) for r in dc],
                residual_area=wave.area, final_integral_q48=integral))

# Direct negative tie behavior mirrors RTL arithmetic shift and ties-to-+inf.
assert ((-(1 << 49) + (1 << 49)) >> 50) == 0
assert ((-3 * (1 << 49) + (1 << 49)) >> 50) == -1
assert (((1 << 49) + (1 << 49)) >> 50) == 1

source = ROOT.parent / 'offline_fixed_voltage' / 'expected_points.json'
export = json.loads(source.read_text(encoding='utf8'))
adapter_checks = []
for point in (0, 1, 99, 100, 5050, 9999):
    for output in export['points'][point]['outputs']:
        model = output_model(output)
        # The early tau100 unipolar preparation has a decoded-step metadata
        # bug. Retain/report it; the authoritative 160-bit words are correct.
        time = (output['hold_digital_output_us'] + output['hold_end_digital_output_us']) / 2
        value = model.at_program_us(time)
        index = value['relative_scalar_index']
        previous = integral = 0
        for n in range(index + 1):
            x = model.waveform.raw_at(n) * 4
            integral += model.coefficient * (x + previous)
            previous = x
        scalar = clamp(((x << 48) + integral + (1 << 49)) >> 50)
        assert scalar == value['rc_dac_code']
        adapter_checks.append(dict(point=point, axis=output['axis'],
            actual_word_area=model.pre_dc_area, scalar_recurrence_code=scalar,
            compact_result=value, metadata_step_mismatches=model.metadata_step_mismatches))

result = dict(passed=True, physical_execution=False, signed_conditions=records,
              direct_scalar_checks=scalar_checks, actual_command_adapter_checks=adapter_checks,
              original_fixture='Early unipolar tau100 prep only; not current user bipolar tau10/20/30 physical validation',
              metadata_decode_bug_preserved=True,
              source_expected_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              model_source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (ROOT/'compact_expectation.py', ROOT/'command_expectation.py', Path(__file__))})
destination = ROOT / 'signed_and_adapter_checks.json'
if destination.exists():
    raise FileExistsError(destination)
destination.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
print(json.dumps(dict(passed=True, signed_conditions=len(records), scalar_checks=scalar_checks,
                     actual_command_adapter_checks=len(adapter_checks),
                     metadata_mismatch_records=sum(bool(x['metadata_step_mismatches']) for x in adapter_checks)), indent=2))
