"""Short offline regressions for final-summary condition and artifact binding."""
import copy
import gzip
import hashlib
import json
from pathlib import Path

import finalize_evidence as finalizer


def main():
    here = Path(__file__).resolve().parent
    label = 'rising_dac4_fixed_time10_tau20'
    physical = finalizer.read(here / 'physical_campaign_status.json')
    analyzed = finalizer.read(here / 'analysis_campaign_status.json')
    case = next(c for c in physical['cases'] if c['label'] == label)
    acase = next(c for c in analyzed['cases'] if c['label'] == label)
    manifest = finalizer.read(here / case['prepared'] / 'manifest.json')
    with gzip.open(here / case['prepared'] / 'expected_points.json.gz', 'rt', encoding='utf8') as stream:
        expected = json.load(stream)
    expected.pop('points')  # This selfcheck tests metadata binding, not waveform math.
    measured = finalizer.read(here / case['run'] / 'status.json')
    result = finalizer.read(here / acase['analysis'] / 'results.json')
    values = [case, acase, manifest, expected, measured, result]
    finalizer.check_artifact_bindings(*values)
    mutations = [
        (0, 'label', 'falling_dac4_fixed_time10_tau20'),
        (1, 'prepared', 'offline_other'), (1, 'run', 'run_other'),
        (1, 'analysis', 'analysis_other'),
        (2, 'active_axis', 1), (2, 'requested_range_mv', [-300., 300.]),
        (2, 'dc_time_us', 20.), (2, 'hold_us', 100.),
        (3, 'rc_tau_us', 30.), (3, 'identity_matrix', False),
        (3, 'sweep_shape', [10, 1000]), (3, 'duration_count', 10),
        (3, 'requested_ramp_range_us', [.1, 1.]),
        (4, 'prepared_bundle', 'offline_other'), (4, 'high_resolution', True),
        (5, 'source_run', 'run_other'), (5, 'mode', 'fixed_voltage'),
        (5, 'requested_range_mv', [-300., 300.]),
    ]
    rejected = []
    for index, key, value in mutations:
        changed = copy.deepcopy(values)
        changed[index][key] = value
        try:
            finalizer.check_artifact_bindings(*changed)
        except AssertionError:
            rejected.append(dict(artifact_index=index, key=key, altered_value=value))
        else:
            raise AssertionError(f'Unrejected mutation: {index}/{key}/{value}')
    condition_checks = 0
    for direction in ('rising', 'falling'):
        for dac in (4, 5):
            for tau in (10, 20, 30):
                for dc in ('fixed_voltage', 'fixed_time10', 'fixed_time20', 'fixed_time30'):
                    name = f'{direction}_dac{dac}_{dc}_tau{tau}'
                    condition = finalizer.condition_from_label(name)
                    synthetic = dict(manifest)
                    synthetic.update(swept_ramp=direction, active_axis=dac - 4,
                                     tau_us=float(tau), mode=condition['mode'],
                                     dc_time_us=condition['dc_time_us'], dc_voltage_mv=300.)
                    finalizer.check_condition(synthetic, condition, tau_key='tau_us', shape=True, hold_key='hold_us')
                    condition_checks += 1
    result = dict(passed=True, actual_completed_case=label,
                  actual_metadata_binding_passed=True, synthetic_conditions=condition_checks,
                  mutations_rejected=len(rejected), mutation_details=rejected,
                  limitation='Metadata binding only; no new measurement or waveform computation.',
                  source_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in (Path(__file__), Path(finalizer.__file__))})
    finalizer.dump(here / 'finalizer_selfcheck_v2.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
