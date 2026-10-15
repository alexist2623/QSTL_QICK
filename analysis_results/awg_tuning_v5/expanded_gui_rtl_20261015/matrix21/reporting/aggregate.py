"""Audit fresh matrix21 evidence; original and explicit-offset results stay separate."""
from datetime import datetime, timezone
import copy
import csv
import hashlib
import itertools
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
E = HERE.parent
ROOT = Path('C:/GIT_Workspace/QSTL_QICK')
GUI = Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')
MATRIX = [[1., .23, -.11], [-.17, 1., .07], [.12, -.09, 1.]]
EXPECTED_POINTS = {
    'hold_fixed_time': 9, 'hold_fixed_voltage_descending': 9,
    'ramp_fixed_time': 4, 'ramp_fixed_voltage_descending': 4,
    'rf_duration_fixed': 4, 'rf_duration_extend': 4, 'rf_frequency': 4,
    'two_voltage_axes': 9, 'two_voltage_axes_reversed': 9,
    'rc_only': 4, 'dc_only': 4, 'compensation_off': 4,
    'square_frequency': 4, 'square_amplitude': 4, 'square_phase': 4,
    'cpmg_n1_tau200ns': 2, 'cpmg_n1_tau400ns': 2,
    'cpmg_n2_tau200ns': 2, 'cpmg_n2_tau400ns': 2,
    'cpmg_named_frequency': 4, 'cpmg_named_duration': 4,
}

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def artifact(p):
    return {'path': str(p), 'sha256': sha(p)}

def audit_saved_gui_grid(folder, direct, oracle):
    """Check saved GUI axes/order/directions against the existing oracle grid.

    This supplements, rather than replaces, its independent numeric C@V oracle.
    Software N/tau coordinates are selected before this hardware grid and are
    deliberately not added as extra hardware axes.
    """
    saved = read(folder / 'gui_input.json')
    assert saved['awg']['cross_capacitance'] == oracle['matrix'] == MATRIX
    axes = saved['awg']['sweeps']
    entered = [dict(kind=a['axis_kind'], output=a['output_name'], start=a['start'], stop=a['stop'], count=a['count']) for a in axes]
    assert entered == direct['axes'], 'Saved GUI axis order differs from modal input evidence'
    dims = [dict(source=f"awg.sweeps[{i}]", kind=a['axis_kind'], output=a['output_name'], start=a['start'], stop=a['stop'], count=a['count']) for i, a in enumerate(axes)]
    for i, rf in enumerate(saved['rf_outputs']):
        if not rf['enabled']:
            continue
        if rf['pulse_mode'] == 'single':
            for kind, unit in [('duration', 'us'), ('frequency', 'mhz')]:
                if rf[f'{kind}_sweep_enabled']:
                    dims.append(dict(source=f'rf_outputs[{i}].{kind}_sweep', kind='rf_' + kind,
                        start=rf[f'{kind}_sweep_start_{unit}'], stop=rf[f'{kind}_sweep_stop_{unit}'], count=rf[f'{kind}_sweep_count']))
        else:
            for kind in ['frequency', 'duration']:
                for param in rf[f'{kind}_parameters']:
                    if param['sweep_enabled']:
                        unit = 'mhz' if kind == 'frequency' else 'us'
                        dims.append(dict(source=f"rf_outputs[{i}].{kind}_parameters.{param['name']}", kind='rf_' + kind,
                            start=param[f'sweep_start_{unit}'], stop=param[f'sweep_stop_{unit}'], count=param['sweep_count']))
    if saved['square_pulse']['enabled']:
        for name, param in saved['square_pulse']['parameters'].items():
            if param['sweep']:
                dims.append(dict(source='square_pulse.parameters.' + name, kind='square_' + name,
                    start=param['start'], stop=param['stop'], count=param['count']))
    indices = list(itertools.product(*(range(d['count']) for d in dims)))
    assert [list(x) for x in indices] == [p['indices'] for p in oracle['points']], 'Saved GUI Cartesian coordinates differ'
    assert len(dims) == len(oracle['axis_deltas'])
    base = [output['voltage_mv'][0] for output in saved['awg']['outputs']]
    for dim, delta in zip(dims, oracle['axis_deltas']):
        if dim['kind'] != 'amplitude':
            assert delta == [0, 0, 0], (dim, 'non-voltage axis changes matrix target')
            continue
        column = int(dim['output'].split('_')[-1])
        base[column] = dim['start'] * 800
        for row, increment in enumerate(delta):
            direction = MATRIX[row][column] * (dim['stop'] - dim['start'])
            assert (increment > 0) - (increment < 0) == (direction > 0) - (direction < 0), (dim, row, 'sweep direction differs')
    assert all(abs(a - b) <= 1e-12 for a, b in zip(base, oracle['base_virtual_mv'])), 'Saved GUI initial virtual voltages differ'
    return dict(status='passed', source=artifact(folder / 'gui_input.json'), dimensions=dims,
        cartesian_coordinates_checked=len(indices), direction_checks=len(dims) * 3,
        initial_virtual_mv=base, scope='Saved modal axes, order, counts, directions and Cartesian coordinates; existing numeric C@V oracle remains separate.')

def audit_passed(name, case):
    selected = case['selected']
    run = case[selected]
    folder = Path(run['folder'])
    assert run['prepare']['exit_code'] == run['rtl']['exit_code'] == 0
    result = read(folder / 'result.json')
    assert result['validation_status'] == 'passed'
    assert result['command_value_mismatches'] == result['command_timing_mismatches'] == 0
    assert result['matrix_direct_gui_input'] is True
    assert result['cross_capacitance'] == MATRIX
    assert len(result['exact_awg_results']) == len(result['raw_awg_results']) == 3
    assert result['points'] == EXPECTED_POINTS[name] and result['repetitions'] == 2
    prepared = read(folder / 'prepared.json')
    assert prepared['shots'] == result['points'] * result['repetitions']
    current_python = {str(p.resolve()) for p in GUI.glob('*.py')} | {str(p.resolve()) for p in (ROOT / 'qick/qick_lib/qick').rglob('*.py')}
    recorded_python = {p for p in prepared['program_source_hashes'] if Path(p).parent == GUI or (ROOT / 'qick/qick_lib/qick') in Path(p).parents}
    assert recorded_python == current_python, (name, 'production Python file set changed')
    for source, digest in prepared['program_source_hashes'].items():
        assert sha(source) == digest, (name, 'program source changed', source)
    sources = re.findall(r'^sv \w+ "([^"]+)"', (folder / 'sources.prj').read_text(), re.M)
    fp = hashlib.sha256()
    for source in [*sources, folder / 'pmem.hex', folder / 'dmem.txt']:
        fp.update(Path(source).read_bytes())
    assert fp.hexdigest() == prepared['fingerprint'], (name, 'RTL/input fingerprint')
    match = read(folder / 'gui_widget_match.json')
    assert match['pmem_equal'] and match['dmem_equal'] and match['gui_sequence_unmodified']
    assert match['sequence_mutations'] == []
    assert sha(folder / 'pmem.hex') == sha(folder / 'gui_widget_pmem.hex')
    direct = read(folder / 'gui_direct_input.json')
    assert direct['matrix'] == MATRIX and direct['no_sequence_mutation']
    assert direct['method'].startswith('QTest keyboard')
    oracle = read(folder / 'independent_matrix_oracle.json')
    assert oracle['passed'] and oracle['matrix'] == MATRIX
    assert len(oracle['points']) == result['points']
    assert oracle['scales_mv'] == [800., 400., 800.]
    saved_gui_grid = audit_saved_gui_grid(folder, direct, oracle)
    # Link the independent C@V/increment oracle directly to observed tProcessor
    # output words, not only to the compiler's internal sweep model. RF gen2
    # remains one simple pulse per shot even in the RF gen0 CPMG cases; its
    # explicit base delay identifies the HOLD SET on all three independent ports.
    with (folder / 'rtl_events.csv').open() as stream:
        observed = [dict(cycle=int(r['cycle']), port=int(r['port']), word=int(r['word'], 16)) for r in csv.DictReader(stream)]
    rf_anchor = [r for r in observed if r['port'] == 1 and (r['word'] >> 152) & 255 == 0 and (r['word'] >> 96) & 0xffffffff]
    assert len(rf_anchor) == prepared['shots'], (name, 'RF gen2 anchor count')
    first_hold_sets = [r for r in observed if (r['word'] >> 152) & 255 == 1 and (r['word'] >> 144) & 3 == 1]
    delay_cycles = round(run['rf_delay_us'] * 300)
    executed_targets = []
    for shot, anchor in enumerate(rf_anchor):
        point = shot // result['repetitions']
        target_cycle = anchor['cycle'] - delay_cycles
        target_codes = []
        for port in range(3):
            found = [r for r in first_hold_sets if r['port'] == port and r['cycle'] == target_cycle]
            assert len(found) == 1, (name, shot, port, 'missing observed HOLD SET')
            code = found[0]['word'] & 0xffffffff
            code = code - 2**32 if code >= 2**31 else code
            assert code == oracle['points'][point]['target_codes'][port], (name, shot, port, 'executed C@V target differs')
            target_codes.append(code)
        executed_targets.append(dict(shot=shot, point=point, observed_tproc_cycle=target_cycle, observed_set_target_codes=target_codes))
    if name in ('rc_only', 'compensation_off'):
        assert result['hardware_area_results'] == [] and len(result['rc_only_results']) == 3
        assert all('dc_execute=0' in item for item in result['rc_only_results'])
        if name == 'compensation_off':
            assert all('mode=OFF' in item and 'rc_enable=0' in item for item in result['rc_only_results'])
        else:
            assert all(f"rc_resets={prepared['shots'] + 1}" in item and f"zero_checks={prepared['shots'] + 1}" in item for item in result['rc_only_results'])
    else:
        assert len(result['hardware_area_results']) == 3
        assert all(f"shots={prepared['shots']} " in item and f"reset_checks={prepared['shots']} " in item and item.endswith('residual=0') for item in result['hardware_area_results'])
    metadata = read(folder / 'v5_route_metadata.json')
    cfg = read(folder / 'configured_soccfg.json')
    assert sha(metadata['hwh']) == metadata['hwh_sha256'] == cfg['validation_candidate_hwh_sha256']
    assert len(metadata['routes']) == 6
    for route in metadata['routes']:
        values = route['route']
        assert values['output_sum_version'] == 2 and values['output_sum_awg_delay_cycles'] == 13
        assert values['post_output_latency_cycles'] == 2 and not values['output_sum_bypass']
        assert cfg['gens'][route['channel']]['output_latency_cycles'] == 31
    sums = result['output_sum']
    assert sums['awg_delay_cycles'] == 13 and sums['combiner_pipeline_cycles'] == 2
    assert sums['output_register_cycles'] == 10 and sums['board_measurement'] is False
    assert len(sums['pairs']) == len(sums['sample_oracles']) == 3
    assert {p['suffix'] for p in sums['pairs']} == {4, 5, 6}
    assert {int(p[0]) for p in sums['sample_oracles']} == {4, 5, 6}
    assert all(p['physical_sample_checks'] > 0 for p in sums['pairs'])
    assert all(int(n) > 0 for _, n in sums['sample_oracles'])
    for pair in sums['pairs']:
        if name.startswith('cpmg_'):
            assert pair['width_errors'] == 0 and pair['command_to_sum_input_cycles'] == 32
        else:
            assert pair['unexpected_rf_pulses'] == 0
            assert all(m['requested_timing_error_cycles'] == 0 for m in pair['measurements'])
    rf = result['rf_measurements']
    assert rf['width_mismatch_pulses'] == rf['width_error_max_cycles'] == 0
    if name.startswith('square_'):
        assert len(result['square_oracle']) == 1
    # The inherited finish() also hashed live control/log files. Those entries
    # describe bytes observed at case completion, not a stable final source gate.
    static = {p: h for p, h in result['test_source_sha256'].items() if Path(p).suffix in ('.py', '.svh')}
    assert static and all(sha(p) == h for p, h in static.items())
    temporal = {p: h for p, h in result['test_source_sha256'].items() if p not in static}
    if selected == 'rf100ns':
        original = Path(case['original']['folder'])
        before = read(original / 'gui_input.json')
        after = read(folder / 'gui_input.json')
        modified = copy.deepcopy(before)
        assert len(modified['rf_outputs']) == len(after['rf_outputs']) == 3
        for old_rf, new_rf in zip(modified['rf_outputs'], after['rf_outputs']):
            assert old_rf['delay_us'] == 0 and new_rf['delay_us'] == .1
            old_rf['delay_us'] = .1
        assert modified == after, (name, 'unexpected GUI fixture change')
        rejection = read(original / 'gui_rejection.json')
        assert 'shared tProcessor port' in rejection['error'] and rejection['guard_modified'] is False
        assert case['original']['prepare']['exit_code'] != 0
    evidence_names = ['prepared.json', 'result.json', 'gui_input.json', 'gui_direct_input.json', 'gui_widget_match.json',
        'gui_widget_pmem.hex', 'pmem.hex', 'dmem.txt', 'independent_matrix_oracle.json', 'configured_soccfg.json',
        'v5_route_metadata.json', 'output_sum_result.json', 'sources.prj', 'tb_rc_gui.sv', 'xsim.log', 'matrix_input.png']
    evidence_names += [p.name for p in folder.glob('*.csv')]
    evidence_names += [p.name for p in folder.glob('planned_area_*.hex')]
    evidence_names += ['expected.json', 'gui_export.py', 'gui_fixture_adapter.py', 'program.asm', 'options.txt',
        'rc_bd.v', 'rc_wrapper.v', 'xvlog.log', 'xelab.log', 'gui_software_point.json', 'rf_measurements.json']
    evidence = {n: artifact(folder / n) for n in sorted(set(evidence_names)) if (folder / n).exists()}
    return dict(case=name, selected=selected, original_request_passed=selected == 'original',
        explicit_fixture_offset_us=run['rf_delay_us'], folder=str(folder), points=result['points'],
        shots=prepared['shots'], commands=result['commands'], raw_awg_results=result['raw_awg_results'],
        voltage_grid_policy=result['voltage_grid_policy'], compiled_target_error_codes=result['compiled_target_error_codes'],
        compiled_step_error_units=result['compiled_step_error_units'],
        compiler_model_matrix_target_checks=result['points'] * 3,
        saved_gui_grid_audit=saved_gui_grid,
        executed_matrix_target_checks=prepared['shots'] * 3, executed_matrix_targets=executed_targets,
        executed_matrix_payload_audit=dict(applicable=True, status='passed',
            method='Independent saved C@V/increment oracle vs observed rtl_events.csv HOLD SET payload; RF gen2 one-pulse-per-shot anchor minus explicit RF base delay.',
            comparisons=prepared['shots'] * 3, expected=artifact(folder / 'independent_matrix_oracle.json'), observed=artifact(folder / 'rtl_events.csv')),
        exact_awg_results=result['exact_awg_results'], hardware_area_results=result['hardware_area_results'],
        rc_only_results=result['rc_only_results'], reset_results=result['reset_results'], analog_results=result['analog_results'],
        rf_measurements=rf, square_oracle=result.get('square_oracle'),
        sum_lane_checks=sum(int(n) for _, n in sums['sample_oracles']),
        physical_lane_checks=sum(p['physical_sample_checks'] for p in sums['pairs']),
        cpmg_delay_checks=sums.get('cpmg_delay_checks', 0), source_count=len(prepared['program_source_hashes']),
        source_hashes=prepared['program_source_hashes'], source_fingerprint=prepared['fingerprint'],
        static_test_source_hashes=static, temporal_hash_entries_at_case_end=temporal, evidence=evidence)

def main():
    state = read(E / 'status.json')
    assert state['execution_complete'] and set(state['cases']) == set(EXPECTED_POINTS), 'Controller is not finished'
    rows = []
    failures = []
    originals = []
    for name, case in state['cases'].items():
        original = case['original']
        originals.append(dict(case=name, exit_code=original['prepare']['exit_code'],
            folder=original['folder'], rejection=original.get('rejection'),
            log=artifact(original['prepare']['log']), requested_delay_us=original['rf_delay_us'],
            evidence={n: artifact(Path(original['folder']) / n) for n in ['gui_input.json', 'gui_direct_input.json', 'gui_rejection.json', 'gui_fixture_adapter.py'] if (Path(original['folder']) / n).exists()}))
        if case['state'] != 'passed':
            failures.append(dict(case=name, state=case['state'], details=case))
            continue
        rows.append(audit_passed(name, case))
    plot = read(HERE / 'plot_provenance_v2.json')
    assert all(sha(p) == digest for p, digest in plot['sources'].items())
    assert sha(plot['figure']['path']) == plot['figure']['sha256']
    assert sha(plot['matrix_dialog']['path']) == plot['matrix_dialog']['sha256']
    result = dict(execution_complete=True, all_selected_cases_passed=not failures and len(rows) == 21,
        original_requests_all_passed=all(r['original_request_passed'] for r in rows) and len(rows) == 21,
        finished_utc=datetime.now(timezone.utc).isoformat(), controller=artifact(E / 'status.json'),
        reporting_script=artifact(Path(__file__).resolve()),
        original_accepted_count=sum(r['original_request_passed'] for r in rows),
        original_passed_count=sum(r['original_request_passed'] for r in rows),
        original_gui_accepted_count=sum(o['exit_code'] == 0 for o in originals),
        original_rejected_count=sum(o['exit_code'] != 0 and 'shared tProcessor port' in (o['rejection'] or {}).get('error', '') for o in originals),
        original_prepare_error_count=sum(o['exit_code'] != 0 and 'shared tProcessor port' not in (o['rejection'] or {}).get('error', '') for o in originals),
        explicit_offset_variant_passed_count=sum(not r['original_request_passed'] for r in rows),
        passed_case_count=len(rows), failed_case_count=len(failures), points=sum(r['points'] for r in rows),
        shots=sum(r['shots'] for r in rows), commands=sum(r['commands'] for r in rows),
        sum_lane_checks=sum(r['sum_lane_checks'] for r in rows),
        physical_lane_checks=sum(r['physical_lane_checks'] for r in rows),
        executed_matrix_target_checks=sum(r['executed_matrix_target_checks'] for r in rows),
        compiler_model_matrix_target_checks=sum(r['compiler_model_matrix_target_checks'] for r in rows),
        saved_gui_grid_coordinates_checked=sum(r['saved_gui_grid_audit']['cartesian_coordinates_checked'] for r in rows),
        executed_matrix_audit_applicability={name: 'performed_passed' if any(r['case'] == name for r in rows) else 'not_performed_due_to_failed_selected_execution' for name in state['cases']},
        originals=originals, cases=rows, failures=failures, figures=plot,
        scope=['Actual modal keyboard matrix and AWG sweep inputs, current MainWindow Run Experiment compiler.',
            'Actual production CPMG software coordinate selector for N/tau; named RF frequency/duration retain hardware sweeps.',
            'Independent C@V and integer increment oracle; PMEM/DMEM match; actual tProcessor/TMUX/AWG/DDS/IIR/v5 sum/final digital output.',
            'Explicit +100ns variants change only three RF base-delay fields; rejected original requests remain rejected.'],
        limitations=['No solution or PASS claim for exact simultaneous shared-port AWG/RF commands.',
            'No board analog/ADC-FIR arithmetic measurement, new synthesis, upload or firmware replacement.',
            'analog_results is the inherited hypothetical analog-RC diagnostic for two AWGs and Square, not hardware measurement or the third AWG error. Its fixed-waveform analog bound does not apply to these sweeps; all three actual digital IIR recurrences remain exact PASS gates.',
            'RF waveform-fit latency is measured on the retained RF diagnostic branch; final v5 DAC checks use the separate sum-v2 and final-slice monitors. It is not the native generator latency value.',
            'Inherited test_source_sha256 non-code entries are snapshots of live files at each case end; final stable gate uses prepared.program_source_hashes, static test sources, RTL/input fingerprint and final evidence hashes.',
            'DDS area/clipping after AWG IIR is outside existing DC area compensation.'])
    dest = HERE / 'result.json'
    assert not dest.exists(), 'Preserve existing aggregate'
    dest.write_text(json.dumps(result, indent=2), encoding='utf-8')
    lines = ['# Current v5 Virtual matrix × sweep GUI → RTL results', '',
        f"Fresh selected executions: {len(rows)}/21 PASS. Original unmodified requests passed: {result['original_accepted_count']}; original requests rejected: {result['original_rejected_count']}; explicitly labelled +100ns variants passed: {result['explicit_offset_variant_passed_count']}.", '',
        'Original requests and explicit-offset variants are separate results. No production timing guard or requested original timing was changed.', '',
        '| Case | Original request | Actual RTL input/result | Points × repeats |', '|---|---|---|---|']
    by = {r['case']: r for r in rows}
    for name, case in state['cases'].items():
        if name in by:
            r = by[name]
            lines.append(f"| {name} | {'accepted' if r['original_request_passed'] else 'shared-port rejection preserved'} | {'original PASS' if r['original_request_passed'] else 'explicit RF +100ns PASS'} | {r['points']} × {r['shots']//r['points']} |")
        else:
            lines.append(f"| {name} | see original log | {case['state']} | — |")
    lines += ['', f"Executed totals: {result['points']} points, {result['shots']} shots, {result['commands']} commands; {result['sum_lane_checks']:,} v5 sum lane checks and {result['physical_lane_checks']:,} final digital output lane checks.", '',
        f"The saved GUI axes, order, counts and directions match all {result['saved_gui_grid_coordinates_checked']} Cartesian coordinates of the independent oracle. The independent C×V/increment oracle has {result['compiler_model_matrix_target_checks']} compiler-model target comparisons. A separate post-execution audit directly checks {result['executed_matrix_target_checks']} actual RTL HOLD SET payloads (each shot × three ports), including repetition and axis rewind. Per-case applicability, counts and observed values are in result.json.", '',
        'The matrix and AWG axes were entered through real modal widgets. Actual MainWindow compiler PMEM/DMEM were matched before the RTL execution. CPMG N/τ coordinates use the existing production software-point selector; named frequency/duration use the hardware parameter sweep path. All three AWG/RF pairs, raw AWG, IIR, area/reset or bypass, v5 delay/sum and final register slices are checked; Square cases retain the original independent Square oracle. Matrix targets follow the existing constant quantized increment policy; PASS means that policy matches the independent oracle, not that ideal analog voltages are free of quantization error.', '',
        'The +100ns variant is authorized diagnostic coverage of matrix/sweep behavior. Its saved GUI input differs from the rejected original only in the three RF base-delay values. It does not turn the original exact-start request into a PASS.', '',
        'Stable provenance is rechecked against prepared source hashes and exact RTL/PMEM/DMEM fingerprint. The inherited result also includes hashes of live controller/status files observed at individual case end; those temporal entries are preserved and are not presented as final source gates.', '',
        '[Machine-readable results, original rejections, all paths and SHA256](result.json) · [Actual matrix dialog](matrix_v5_actual_dialog.png) · [Actual final v5 DAC trace, all three pairs](matrix_v5_actual_trace_v2.png)', '',
        'No board analog measurement, ADC/FIR arithmetic validation, synthesis, upload or firmware replacement. DDS area/clipping after AWG IIR remains outside existing DC area compensation.']
    (HERE / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('all_selected_cases_passed', 'original_requests_all_passed', 'original_accepted_count', 'original_rejected_count', 'explicit_offset_variant_passed_count', 'points', 'shots', 'commands', 'physical_lane_checks')}))

if __name__ == '__main__':
    main()
