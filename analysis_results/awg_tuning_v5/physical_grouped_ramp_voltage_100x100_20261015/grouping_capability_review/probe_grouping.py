"""Tiny, instrument-free capability probe; never materializes the 100^4 grid."""
from pathlib import Path
import hashlib
import json
import socket
import sys


def deny_network(*args, **kwargs):
    raise RuntimeError('Instrument/network access prohibited by this probe')


socket.create_connection = deny_network
socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
root = Path(__file__).resolve().parent
production = Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')
paths = [production / name for name in (
    'DCWaveform_Generator.py', 'dc_waveform_core.py', 'qick_fine_tune_sweep.py',
    'test_qick_fine_tune_sweep.py', 'test_awg_tuning_v2.py',
    'ramp_sweep_test.json', 'short_ramp_test.json',
)]


def hashes():
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


before = hashes()
from qick_fine_tune_sweep import FineTuneSequence, RampDurationSweep
from dc_waveform_core import QickRampRateSweepSpec, QickSweepSpec

sequence = FineTuneSequence(('awg_0', 'awg_1'))
sequence.add_set('set_0', (0., 0.), 3000)
sequence.add_ramp('ramp_0_to_1', 300)
sequence.add_set('set_1', (0., 0.), 3000)
sequence.add_ramp('ramp_1_to_2', 300)
sequence.add_set('set_2', (0., 0.), 3000)
full_scale_mv = 801.48
specs = (
    QickRampRateSweepSpec('ramp_0_to_1', .01, 1., 2),
    QickRampRateSweepSpec('ramp_1_to_2', .01, 1., 2),
    QickSweepSpec('set_1', 'awg_0', -300/full_scale_mv, 300/full_scale_mv, 2),
    QickSweepSpec('set_1', 'awg_1', -300/full_scale_mv, 300/full_scale_mv, 2),
)
for spec in specs:
    if isinstance(spec, QickRampRateSweepSpec):
        sequence.add_ramp_duration_sweep(spec.segment_name, spec.start, spec.stop, spec.count)
    else:
        sequence.add_amplitude_sweep(spec.segment_name, spec.output_name,
                                     spec.start, spec.stop, spec.count)
assert sequence.sweep_shape == (2, 2, 2, 2)
assert sequence.sweep_point_count == 16
coordinates = [list(sequence.sweep_coordinate(i)) for i in range(16)]
assert any(row[0] != row[1] for row in coordinates)
assert any(row[2] != row[3] for row in coordinates)
duration_axis = RampDurationSweep('ramp_0_to_1', .01, 1., 100, 300.)
assert duration_axis.duration_cycles_points == tuple(range(3, 301, 3))
assert duration_axis.output_name == 'all_awg_outputs'
after = hashes()
assert before == after
result = {
    'status': 'passed_capability_probe_grouping_unsupported',
    'scope': 'Read current model only, using GUI-accepted dataclass schemas. No Qt GUI, hardware compilation, TProc simulation, instruments, or network.',
    'probe_shape': list(sequence.sweep_shape), 'probe_points': sequence.sweep_point_count,
    'probe_coordinates': coordinates,
    'desired_grouped_probe_shape': [2, 2], 'desired_grouped_probe_points': 4,
    'requested_count_per_axis': 100,
    'current_ungrouped_shape_if_applied': [100, 100, 100, 100],
    'current_ungrouped_points_arithmetic_only': 100**4,
    'requested_grouped_shape_unsupported': [100, 100],
    'requested_grouped_points': 10000,
    'no_100million_grid_created_or_compiled': True,
    'duration_axis_all_outputs': duration_axis.output_name,
    'duration_cycles_100points': list(duration_axis.duration_cycles_points),
    'duration_scope': '3 through 300 cycles in steps of 3 at 300MHz; coordinate validation only, not analog timing proof.',
    'before_source_sha256': before, 'after_source_sha256': after,
    'sources_unchanged': True,
    'probe_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
out = root / 'results.json'
with out.open('x', encoding='utf-8') as handle:
    json.dump(result, handle, indent=2)
print(json.dumps({key: result[key] for key in (
    'status', 'probe_shape', 'probe_points', 'current_ungrouped_points_arithmetic_only',
    'sources_unchanged', 'no_100million_grid_created_or_compiled')}))
