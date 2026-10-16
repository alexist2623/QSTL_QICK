"""Strict independent post-run audit and lossless evidence archive; no simulation."""
from datetime import datetime, timezone
import csv
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
E = HERE.parent
ROOT = Path('C:/GIT_Workspace/QSTL_QICK')
OLD = ROOT/'analysis_results/awg_tuning_v5/expanded_gui_rtl_20261015/matrix21/reporting/aggregate.py'
spec = importlib.util.spec_from_file_location('previous_matrix_audit', OLD)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
read, sha, artifact = audit.read, audit.sha, audit.artifact


def fine_audit():
    state = read(E/'fine/status.json')
    assert state['complete'] and state['stage'] == 'passed'
    assert len(state['cases']) == 1
    prepared = read(E/'fine/prepared.json')
    assert len(prepared['cases']) == 1
    case = prepared['cases'][0]
    folder = Path(case['folder'])
    result = read(folder/'result.json')
    assert result['passed'] and result == state['cases'][0]
    assert case['points'] == 4 and case['repetitions'] == 2
    for key in ('command_value_errors','command_timing_errors','sum_lane_oracle_errors'):
        assert result[key] == 0
    for source, digest in prepared['source_hashes'].items():
        assert sha(source) == digest, ('fine source', source)
    for source, digest in prepared['template_sources'].items():
        assert sha(source) == digest, ('fine template', source)
    for name, digest in case['inputs'].items():
        assert sha(folder/name) == digest, ('fine input', name)
    assert sha(E/'fine/run.py') == state['helper_sha256'] == result['helper_sha256']
    cfg = read(folder/'configured_soccfg.json')
    assert sha(cfg['validation_candidate_hwh']) == cfg['validation_candidate_hwh_sha256']
    assert len(cfg['validation_routes']) == 6
    for route in cfg['validation_routes']:
        values = route['route']
        assert values['output_sum_version'] == 2 and values['output_sum_awg_delay_cycles'] == 13
        assert values['post_output_latency_cycles'] == 2 and cfg['gens'][route['channel']]['output_latency_cycles'] == 31
    for source in prepared['cached_sg_v6_source_equivalence']:
        assert source['equal_after_namespace_and_comment_removal']
        assert sha(source['source']) == source['source_sha256']
        assert sha(source['cached_source']) == source['cached_sha256']
    wanted = read(folder/'gui_input.json')['rf_outputs']
    entered = read(folder/'gui_committed.json')['rf_outputs']
    runtime = read(folder/'gui_runtime_specs.json')
    assert len(wanted) == len(entered) == len(runtime) == 3
    for original, actual in zip(wanted, runtime):
        for key in ('gen_ch','segment_name','delay_us','gain','phase_degrees','frequency_mhz','fine_duration','require_within_segment'):
            assert original[key] == actual[key], ('fine requested/runtime', key)
        assert actual['delay_us'] == .1
    assert all(c['pipeline_after_tproc_samples'] == 32*16 and c['unexpected_nonzero_samples'] == 0 for c in result['checks'])
    for check in result['checks']:
        expected = [n for n in range(94,98) for _ in range(2)] if check['channel'] == 0 else [97]*8
        assert [b['samples'] for b in check['bursts']] == expected
        assert [b['exact_active_sample_count'] for b in check['bursts']] == expected
        assert all(b['frequency_mhz'] == 0 and b['gain'] == 4000 and b['phase_degrees'] == 0 for b in check['bursts'])
        assert sha(folder/f"fine_{check['channel']}.csv") == check['csv_sha256']
    sums = re.findall(r'OUTPUT_SUM_RESULT suffix=(\d+) samples=(\d+)', (folder/'run_console.log').read_text())
    assert len(sums) == 3 and {int(s) for s,n in sums} == {4,5,6}, sums
    assert all(int(n) > 0 for s,n in sums)
    assert all(result['final_dac_lane_checks'][str(s)] > 0 for s in (4,5,6))
    return dict(case=case['name'],folder=str(folder),points=4,shots=8,commands=result['commands'],
        requested_samples=[94,95,96,97], three_pair_bursts=24, explicit_fixture_offset_us=.1,
        checks=result['checks'],sum_lane_checks=sum(int(n) for s,n in sums),
        physical_lane_checks=sum(result['final_dac_lane_checks'].values()),
        source_hashes=prepared['source_hashes'],template_sources=prepared['template_sources'],
        input_hashes=case['inputs'],source_count=len(prepared['source_hashes']),
        gui_entry='Actual MainWindow JSON loading, then QTest keyboard commit of RF0 fine-duration start/stop/count, followed by Run Experiment arguments and fresh production compilation.',
        envelope_load=prepared['envelope_load'], envelope_arrays=case['envelopes'],
        fine_resolution_ns=1000/4800., command_start_grid_ns=1000/300.,
        status='passed',analog_measurement=False,board_access=False)


def archive_file(path, destination):
    original_sha = sha(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    compressed = path.suffix.lower() in ('.csv','.log')
    if compressed:
        destination = destination.with_name(destination.name+'.gz')
        assert not destination.exists(), destination
        with path.open('rb') as source, destination.open('wb') as raw:
            with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as target:
                shutil.copyfileobj(source,target,1024*1024)
        restored = hashlib.sha256(); size = 0; rows = 0
        with gzip.open(destination,'rb') as stream:
            for line in stream:
                restored.update(line); size += len(line); rows += 1
        assert restored.hexdigest() == original_sha and size == path.stat().st_size
    else:
        assert not destination.exists(), destination
        shutil.copy2(path,destination)
        assert sha(destination) == original_sha
        size = path.stat().st_size; rows = None
    assert destination.stat().st_size < 50*1024**2, ('Git artifact too large',destination)
    return dict(original=str(path),original_sha256=original_sha,original_bytes=size,
        archive=str(destination),archive_sha256=sha(destination),archive_bytes=destination.stat().st_size,
        compression='gzip lossless' if compressed else 'none',reload_integrity_passed=True,
        original_line_count=rows,data_rows=(rows-1 if path.suffix=='.csv' else None),original_retained=True)


def main():
    assert not (HERE/'result.json').exists(), 'Do not replace a completed audit'
    controller_exits = read(HERE/'controller_exits.json')
    assert controller_exits['coarse']['exit_code'] == controller_exits['fine']['exit_code'] == 0
    assert controller_exits['active_xsim_processes'] == []
    state = read(E/'coarse_status.json')
    assert state['complete'] and state['passed']
    assert set(state['cases']) == {'hold_fixed_time','ramp_fixed_time','rf_frequency'}
    audit.EXPECTED_POINTS = {name:4 for name in state['cases']}
    rows=[]
    for name, case in state['cases'].items():
        run=dict(case,rf_delay_us=case['rf_offset_us'])
        row=audit.audit_passed(name,dict(selected='original',original=run))
        row['status']='passed'
        rows.append(row)
    rows.append(fine_audit())
    allowed={'.json','.csv','.hex','.txt','.asm','.sv','.svh','.v','.py','.log','.png','.prj','.tcl'}
    archived=[]
    for row in rows:
        folder=Path(row['folder'])
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix.lower() in allowed:
                archived.append(archive_file(path,E/'archive'/row['case']/path.name))
    # Preserve the fine input template actually compiled; its directory is not a Vivado cache.
    for path in sorted((Path(read(E/'fine/prepared.json')['build'])/'template').iterdir()):
        if path.is_file() and path.suffix.lower() in allowed:
            archived.append(archive_file(path,E/'archive/fine_template'/path.name))
    for path in sorted(E.glob('*.log')):
        archived.append(archive_file(path,E/'archive/controllers'/path.name))
    for path in (E/'coarse_status.json',E/'fine/status.json',E/'fine/prepared.json',E/'adapter_provenance.json',HERE/'controller_exits.json'):
        archived.append(archive_file(path,E/'archive/controllers'/(path.parent.name+'_'+path.name)))
    manifest=dict(passed=True,files=archived,numeric_files=sum(Path(r['original']).suffix=='.csv' for r in archived),
        original_bytes=sum(r['original_bytes'] for r in archived),archive_bytes=sum(r['archive_bytes'] for r in archived),
        original_deletion=False,all_reload_integrity_passed=True,
        numeric_scope='Every recorded fabric word/lane across the complete execution, including all points/repetitions and baseline regions. Simulation output only; no oscilloscope data.')
    (HERE/'archive_manifest.json').write_text(json.dumps(manifest,indent=2))
    result=dict(passed=True,created=datetime.now(timezone.utc).isoformat(),cases=rows,
        case_count=len(rows),points=sum(r['points'] for r in rows),shots=sum(r['shots'] for r in rows),
        commands=sum(r['commands'] for r in rows),sum_lane_checks=sum(r['sum_lane_checks'] for r in rows),
        final_dac_lane_checks=sum(r['physical_lane_checks'] for r in rows),
        executed_matrix_target_checks=sum(r.get('executed_matrix_target_checks',0) for r in rows),
        failures=[],fresh_compilation=True,old_pmem_replayed=False,board_access=False,analog_measurement=False,
        controller_exits=controller_exits,
        production_changes=False,rtl_changes=False,archive=artifact(HERE/'archive_manifest.json'),
        postprocessor=artifact(Path(__file__)),reused_read_only_audit=artifact(OLD),
        scope='Three fresh GUI modal matrix/axis cases and one fresh GUI fine-duration case -> tProcessor/TMUX -> actual AWG-v3/SG-v6 -> v5 sum-v2 -> final DAC register slices. 100ns RF offset explicitly requested. No exact simultaneous-start claim.',
        limitations=['No physical DAC/oscilloscope measurements or analog fidelity claim.',
            'RC/IIR digital recurrence and area checks are not an analog board model.',
            'These are representative arithmetic sweeps, not native logarithmic sweep support.',
            'Future arithmetic fine-DMEM compression/grouped GUI sweep TODOs were not implemented.'])
    (HERE/'result.json').write_text(json.dumps(result,indent=2))
    summary=dict(complete=True,passed=True,
        cases=[dict(name=r['case'],shots=r['shots'],points=r['points'],command_value_errors=0,
            command_timing_errors=0,sum_lane_checks=r['sum_lane_checks'],
            final_dac_lane_checks=r['physical_lane_checks']) for r in rows],
        totals={k:result[k] for k in ('case_count','points','shots','commands','sum_lane_checks',
            'final_dac_lane_checks','executed_matrix_target_checks')},
        archive_verified=True,failed_attempts=[],source_hashes_match=True,
        detail=artifact(HERE/'result.json'),archive_manifest=artifact(HERE/'archive_manifest.json'),
        plots={name:artifact(HERE/name) for name in ('fine_94_97_rtl.png','matrix_hold_final_dac_rtl.png')},
        measured_physical=False,scope=result['scope'])
    (HERE/'summary.json').write_text(json.dumps(summary,indent=2))
    lines=['# Fresh representative GUI to v5 RTL tests','',
        'All four fresh executions passed. This report covers observed digital simulation output, not physical board/scope measurements.','',
        '| Case | Points | Repetitions | Commands | Final DAC lane checks |','|---|---:|---:|---:|---:|']
    for row in rows: lines.append(f"| {row['case']} | {row['points']} | 2 | {row['commands']} | {row['physical_lane_checks']} |")
    lines += ['',f"Total: {result['points']} points, {result['shots']} shots, {result['commands']} observed tProcessor commands; {result['sum_lane_checks']} sum-lane checks and {result['final_dac_lane_checks']} final-DAC-lane checks.",'',
        'The first three cases enter the nonidentity 3x3 matrix and AWG sweep controls through actual Qt dialogs; RF settings are loaded through MainWindow settings. Fresh MainWindow Run Experiment input is compiled, and GUI/generated PMEM/DMEM match byte for byte. Independent C@V/integer-increment targets match the executed SET payload on all three ports. Raw AWG, IIR recurrence, DC area/reset, RF and sum/final slices are checked.', '',
        'The exact grids are HOLD duration 1.0/1.9us x virtual AWG0 voltage 5/15mV; RAMP duration 0.1/0.4us x 5/15mV; RF0 frequency 180/225MHz x 5/15mV. Each Cartesian grid has four points and two repetitions. The last two RF ports remain at 190MHz in the coarse cases. Matrix coefficients and unequal 800/400/800mV channel scales are retained in independent_matrix_oracle.json.','',
        'The fine case loads actual MainWindow settings and commits RF0 duration start/stop/count through Qt keyboard input: 94, 95, 96, 97 DAC samples, each twice. RF2/RF4 remain 97 samples. All three use 0MHz/gain4000 for unambiguous exact active-window checks. Requested sample count is the independent width oracle; start time is checked against compiled/model command time plus the measured tProcessor offset and the established 32-cycle path. Real host AXI/AXIS transactions load the SG-v6 envelope BRAM; no hierarchical memory injection is used. Fine length spacing is 0.208333ns while command starts remain on the 3.333333ns fabric grid.','',
        'Offscreen Qt screenshots may omit text due to rendering limitations. Values are verified from committed settings, actual runtime specifications and PMEM/DMEM, not by reading screenshot labels. The two reporting PNGs are plots of numeric digital RTL traces.','',
        'RF +100ns offset is an explicit test input in all four cases. Exact simultaneous AWG/RF start is outside this test request. This is a new compilation and new RTL execution, not replay of previous PMEM results.','',
        f"All {manifest['numeric_files']} numeric trace files are archived losslessly, with original hashes, byte/row counts and decompressed hash verification. Originals remain at the external execution folders. See archive_manifest.json for per-file paths and hashes.",'',
        'Initial failures: none. Controller logs, source/input fingerprints and static source hashes are retained. Mutable log/status hashes recorded at intermediate case completion are historical observations, not current source gates.','',
        'No production Python/RTL/XDC/user settings, firmware, board or live GUI process was changed. No new synthesis was run. Native logarithmic sweep, grouped sweep lifecycle and fine-DMEM compression remain future TODO work.','']
    (HERE/'REPORT.md').write_text('\n'.join(lines),encoding='utf8')
    print(json.dumps({k:result[k] for k in ('passed','case_count','points','shots','commands','sum_lane_checks','final_dac_lane_checks','executed_matrix_target_checks')}))


if __name__=='__main__': main()
