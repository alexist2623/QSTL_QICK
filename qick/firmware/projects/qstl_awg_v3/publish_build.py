"""Publish matching XSA members only after setup and hold timing pass."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile


def file_record(path, root):
    data = path.read_bytes()
    return dict(path=path.relative_to(root).as_posix(), bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest())


def validate_hwh(data):
    root = ET.fromstring(data)
    modules = {m.get('INSTANCE'): m for m in root.iter('MODULE')}
    square = modules['axis_square_pulse_v1_0']
    assert square.get('MODTYPE') == 'axis_square_pulse_v1'
    assert 'axis_awg_tuning_v3_7' not in modules
    params = lambda m: {p.get('NAME'): p.get('VALUE') for p in m.findall('PARAMETERS/PARAMETER')}
    bus = lambda m, name: m.find(f"BUSINTERFACES/BUSINTERFACE[@NAME='{name}']").get('BUSNAME')
    tproc = next(m for m in modules.values() if m.get('MODTYPE') == 'axis_tproc64x32_x8')
    fabric_port = tproc.find("PORTS/PORT[@NAME='aclk']")
    assert fabric_port.get('CLKFREQUENCY') == '300000000'
    fabric_net = fabric_port.get('SIGNAME')
    assert fabric_net
    def common_clock(module, port):
        clock = module.find(f"PORTS/PORT[@NAME='{port}']")
        assert clock.get('CLKFREQUENCY') == '300000000'
        assert clock.get('SIGNAME') == fabric_net
    assert params(square)['N_PTS'] == '16'
    assert params(square)['RC_PRECOMP_VERSION'] == '1'
    for module in modules.values():
        if module.get('MODTYPE') == 'axis_awg_tuning_v3':
            assert params(module)['RC_PRECOMP_VERSION'] == '1'
            assert params(module)['STEP_WIDTH'] == '32'
            assert params(module)['FRAC'] == '18'
            assert params(module)['DC_AREA_VERSION'] == '1'
            assert params(module)['DC_AREA_BITS'] == '48'
            assert params(module)['EXTRA_Y_PIPE_STAGES'] == '3'
            assert params(module)['N_PTS'] == params(module)['B'] == '16'
            common_clock(module, 'aclk')
    common_clock(square, 'aclk')
    output_slice = modules['axis_register_slice_12']
    assert bus(square, 'm_axis') == bus(output_slice, 's_axis')
    rfdc = next(m for m in modules.values() if m.get('MODTYPE') == 'usp_rf_data_converter')
    assert bus(output_slice, 'm_axis') == bus(rfdc, 's13_axis')
    fir = next(m for m in modules.values() if m.get('MODTYPE') == 'axis_fir_decim_300to1_v2')
    ddr = next(m for m in modules.values() if m.get('MODTYPE') == 'axis_buffer_ddr_sample_v3')
    common_clock(fir, 'aclk')
    common_clock(ddr, 's_axis_aclk')
    for key, value in dict(DECIM0='10', DECIM1='10', DECIM2='3', ACC_WIDTH='69',
                           OUT_WIDTH='64', OUTPUT_SCALE_LOG2='46').items():
        assert params(fir)[key] == value
    for key, value in dict(IQ_COMPONENT_BITS='64', S_AXIS_DATA_WIDTH='128',
                           IQ_SCALE_LOG2='46', DEFAULT_TRIGGER_DELAY_CYCLES='8712').items():
        assert params(ddr)[key] == value
    assert sum(m.get('MODTYPE') == 'axis_awg_tuning_v3' for m in modules.values()) == 7
    return dict(square_dac='13', square_fabric_clock_hz=300000000, samples_per_clock=16,
                awg_ip_version=3, dc_area_bits=48, dc_area_version=1,
                tproc_fabric_clock_hz=300000000, common_fabric_clock_net=fabric_net,
                awg_ramp_startup_cycles=7,
                awg_output_latency_cycles=16, dc_start_cycles=17, awg_step_bits=32, awg_step_fraction_bits=18,
                square_scalar_sample_rate_hz=4800000000, nominal_gen_ch=7,
                iq_component_bits=64, fir_decimation=300, trigger_delay_cycles=8712,
                rc_precomp_version=1, rc_output_latency_cycles=11,
                rc_fraction_bits=48, rc_accumulator_bits=72,
                square_command_latency_cycles=15)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def validate_rtl_source_manifest(path, repo):
    manifest=json.loads(path.read_text())
    sources=manifest['repository_sources']
    expected={p.relative_to(repo).as_posix() for p in
              (repo/'qick/firmware/ip/axis_awg_tuning_v3/src').glob('*.sv')
              if not p.name.startswith('tb_')}
    expected.add('qick/firmware/ip/axis_square_pulse_v1/src/square_rc_precomp.sv')
    if not expected.issubset({record['path'] for record in sources}):
        raise RuntimeError('System RTL evidence does not identify every production AWG/Square RC source')
    for record in sources:
        source=repo/record['path']
        if hashlib.sha256(source.read_bytes()).hexdigest()!=record['sha256']:
            raise RuntimeError(f'System RTL evidence is stale: {record["path"]}')
    return file_record(path,repo)


def validate_functional_evidence(repo):
    """A timing-closed bitstream also needs completed GUI/RTL evidence."""
    sys.path.insert(0, str(repo/'qick/firmware/ip/axis_awg_tuning_v3/validation'))
    from legacy_logic_guard import validate
    validate(repo)
    validation = repo/'analysis_results/awg_tuning_v3'
    regular_path = validation/'regular_validation/status.json'
    regular_sources_path = validation/'regular_validation/source_hashes.json'
    regular = json.loads(regular_path.read_text())
    if not regular['complete'] or regular['selected_width'] != 48 or regular['changed_sources_or_user_settings']:
        raise RuntimeError('Regular software/selected-48 RTL regressions have not passed')
    required_checks = {'legacy_before', 'legacy_after', 'legacy_outputs', 'tb_dc_area',
                       'tb_dc_boundaries', 'tb_width_awg', 'tb_dc_faults', 'tb_set_saturation'}
    regular_sources = json.loads(regular_sources_path.read_text())
    for source in regular_sources:
        path = Path(source)
        if path.name.startswith('test_') and path.suffix == '.py':
            group = 'gui' if path.parent.name == 'DCWaveformGeneratorGUI' else 'qick'
            required_checks.add(group+'_'+path.parent.name+'_'+path.stem)
    if not required_checks.issubset(regular['stages']):
        raise RuntimeError('Regular RTL checks are missing')
    if any(s['state'] != 'passed' or s['exit_code'] != 0 for s in regular['stages'].values()):
        raise RuntimeError('A regular validation stage failed')
    for source, expected_hash in regular_sources.items():
        if Path(source).suffix == '.json':
            continue  # User settings preservation was checked at regression completion.
        if hashlib.sha256(Path(source).read_bytes()).hexdigest() != expected_hash:
            raise RuntimeError(f'Regular validation source is stale: {source}')
    width_path = validation/'selected48_validation/width_results.json'
    width_manifest_path = validation/'selected48_validation/rtl_source_manifest.json'
    system_path = validation/'system_validation/status.json'
    widths = json.loads(width_path.read_text())
    system = json.loads(system_path.read_text())
    replay_path = validation/'compiler_replay2/result.json'
    replay_sources_path = validation/'compiler_replay2/source_hashes.json'
    replay = json.loads(replay_path.read_text())
    assert replay['complete'] and not replay['simulator_started']
    assert set(replay['cases']) == {Path(case['folder']).name for case in system['cases'].values()}
    for source, expected_hash in json.loads(replay_sources_path.read_text()).items():
        if hashlib.sha256(Path(source).read_bytes()).hexdigest() != expected_hash:
            raise RuntimeError(f'GUI/compiler replay source is stale: {source}')
    if not widths['complete'] or not system['complete'] or len(system['cases']) != 4:
        raise RuntimeError('GUI -> actual RTL and width comparison must finish before firmware publication')
    assert widths['selected_width'] == 48 and set(widths['widths']) == {'48'}
    for bits in ('48',):
        result = widths['widths'][bits]
        assert result['completed_shots'] == 200 and result['overflow_points'] == 0
        assert result['max_cumulative_effective_code_samples'] == 0
        assert result['max_residual_effective_code_samples'] == 0
        assert result['max_collection_error_without_overflow'] == 0
    width_sources = json.loads(width_manifest_path.read_text())['repository_sources']
    required_width_sources = {'qick/firmware/ip/axis_awg_tuning_v3/src/v3_awg_dc_area.sv',
                              'qick/firmware/ip/axis_awg_tuning_v3/src/v3_awg_rc_precomp.sv'}
    assert required_width_sources.issubset({record['path'] for record in width_sources})
    for record in width_sources:
        if hashlib.sha256((repo/record['path']).read_bytes()).hexdigest() != record['sha256']:
            raise RuntimeError(f'Width-comparison RTL evidence is stale: {record["path"]}')
    tail_path = validation/'unit_validation/timing_tail_production/result.json'
    tail = json.loads(tail_path.read_text())
    assert tail['passed'], 'Output timing/rounding regression must pass'
    required_tail_sources = {str((repo/path).resolve()) for path in (
        'qick/firmware/ip/axis_awg_tuning_v3/src/v3_awg_tuning_ctrl.sv',
        'qick/firmware/ip/axis_square_pulse_v1/src/square_rc_precomp.sv')}
    assert required_tail_sources.issubset({str(Path(path).resolve()) for path in tail['sources']})
    for source, expected_hash in tail['sources'].items():
        if hashlib.sha256(Path(source).read_bytes()).hexdigest() != expected_hash:
            raise RuntimeError(f'Output timing/rounding evidence is stale: {source}')
    evidence = [width_path, width_manifest_path, system_path, tail_path, regular_path, regular_sources_path,
                replay_path, replay_sources_path]
    direct_gui_modes=set()
    for name,case in system['cases'].items():
        folder = validation/'system_validation'/Path(case['folder']).name
        binding = replay['cases'][folder.name]
        assert binding['export_equal']
        for file, key in (('pmem.hex','pmem_sha256'), ('dmem.txt','dmem_sha256'), ('gui_export.py','export_sha256')):
            assert hashlib.sha256((folder/file).read_bytes()).hexdigest() == binding[key]
        if name.startswith('GUI ') or name.startswith('Reversed axes'):
            assert binding['gui_widgets_replayed']
            assert hashlib.sha256((folder/'gui_input.json').read_bytes()).hexdigest() == binding['gui_input_sha256']
        manifest_path=validation/'system_validation'/Path(case['folder']).name/'rtl_source_manifest.json'
        validate_rtl_source_manifest(manifest_path,repo)
        evidence.append(manifest_path)
        result = case['result']
        assert case['state'] == result['validation_status'] == 'passed'
        assert result['awg_ip_version'] == 3
        assert (result['points'], result['repetitions']) == (100, 2)
        assert result['command_value_mismatches'] == result['command_timing_mismatches'] == 0
        if result['sweep_case']:
            match_path = validation/'system_validation'/Path(case['folder']).name/'gui_widget_match.json'
            match = json.loads(match_path.read_text())
            assert match['pmem_equal'] and match['dmem_equal']
            if name.startswith('GUI '):
                assert match['gui_sequence_unmodified'] and not match['sequence_mutations']
                direct_gui_modes.add(result['dc_mode'])
            evidence.append(match_path)
    assert direct_gui_modes == {'fixed_voltage', 'fixed_time'}
    return [file_record(path, repo) for path in evidence]


def validate_build_constraints(build, project, conditions):
    """Bind the routed project's actual XDC files to the successful v2 baseline."""
    expected_hashes = {
        'timing.xdc': '9f9d68f0d1d9e69d9c236606d65781e5c1f5eed4b1672a24daebfb670e0bacfb',
        'ios.xdc': '5435d174456af7c2156207ad1571fb56aec6ea1264efea73f9a42a11623430a7',
    }
    xpr = ET.parse(build/(project.name+'.xpr')).getroot()
    fileset = xpr.find(".//FileSet[@Name='constrs_1']")
    if fileset is None:
        raise RuntimeError('Built project has no constraint fileset')
    used_files = set()
    for entry in fileset.findall('File'):
        raw = entry.get('Path', '').replace('$PPRDIR', build.as_posix())
        if not raw or '$' in raw:
            raise RuntimeError(f'Unresolved project constraint path: {raw}')
        path = Path(raw)
        path = (path if path.is_absolute() else build/path).resolve()
        used_in = {attr.get('Val') for attr in entry.findall("FileInfo/Attr[@Name='UsedIn']")}
        if not {'synthesis', 'implementation'}.issubset(used_in):
            raise RuntimeError(f'Constraint is not enabled in both build stages: {path}')
        used_files.add(path)
    snapshots = {(build/'constraints'/name).resolve() for name in expected_hashes}
    if used_files != snapshots:
        raise RuntimeError('Built project must use exactly the original build-local XDC snapshots')
    records = []
    for name, expected in expected_hashes.items():
        original = project/name
        reference = project.parent/'qstl_awg_v2'/name
        snapshot = build/'constraints'/name
        data = snapshot.read_bytes()
        if data != original.read_bytes() or data != reference.read_bytes():
            raise RuntimeError(f'Built/original v2/v3 constraints differ: {name}')
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError(f'Constraints differ from the successful v2 baseline: {name}')
        for label, path in (('source', original), ('snapshot', snapshot)):
            prefix = f'constraint.{name}.{label}'
            recorded_path = conditions.get(prefix+'_path')
            if (not recorded_path or Path(recorded_path).resolve() != path.resolve()
                    or conditions.get(prefix+'_sha256') != expected):
                raise RuntimeError(f'Missing or stale build constraint provenance: {name}/{label}')
        records.append(dict(name=name, source=str(original), snapshot=str(snapshot),
                            bytes=len(data), sha256=expected))
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build_dir', type=Path)
    parser.add_argument('--gui-dir', type=Path)
    args=parser.parse_args()
    project=Path(__file__).resolve().parent
    repo=project.parents[3]
    build=args.build_dir.resolve()
    functional_evidence=validate_functional_evidence(repo)
    gui_repo = args.gui_dir.resolve() if args.gui_dir else (repo.parent/'PulseGenerator').resolve()
    if (any(build.is_relative_to(root) for root in (repo, gui_repo))
            or not (build/(project.name+'.xpr')).is_file()):
        raise RuntimeError('The build must be a separate project outside both Git repositories')
    conditions=dict(line.split('=',1) for line in (build/'build_conditions.txt').read_text().splitlines() if '=' in line)
    if conditions.get('launch_jobs') != '4' or conditions.get('general.maxThreads') != '5':
        raise RuntimeError('Expected user-requested jobs=4 and previous maxThreads=5')
    constraint_evidence = validate_build_constraints(build, project, conditions)
    result=dict(line.split('=',1) for line in (build/'build_result.txt').read_text().splitlines() if '=' in line)
    if result.get('timing_closed') != 'YES' or any(float(result[key]) < 0 for key in ('setup_wns_ns','hold_whs_ns')):
        raise RuntimeError('Refusing to publish a build that did not close setup and hold timing')
    if 'Complete' not in result.get('implementation_status',''):
        raise RuntimeError('Implementation has not completed')
    timing_report=(build/'timing_summary_postroute.rpt').read_text()
    if 'All user specified timing constraints are met.' not in timing_report:
        raise RuntimeError('Routed timing report must pass, including pulse-width checks')
    for check in ('no_clock', 'unconstrained_internal_endpoints'):
        if not re.search(r'checking '+check+r' \(0\)', timing_report):
            raise RuntimeError(f'Routed timing report contains {check} endpoints')
    skew_report=(build/'bus_skew_postroute.rpt').read_text()
    skew_results=re.findall(r'Slack\s*\((MET|VIOLATED)\)\s*:\s*([-\d.]+)ns', skew_report)
    if not skew_results or any(state!='MET' or float(slack)<0 for state,slack in skew_results):
        raise RuntimeError('All bus-skew constraints must pass before publication')
    with zipfile.ZipFile(build/'bitstream.xsa') as archive:
        members={suffix:[name for name in archive.namelist() if name.endswith(suffix)] for suffix in ('.bit','.hwh')}
        # SmartConnect and the DDR MicroBlaze also export subsystem HWH files.
        # The overlay must use the complete top-level block-design handoff.
        top_hwh=[name for name in members['.hwh'] if Path(name).name=='d_1.hwh']
        if len(members['.bit'])!=1 or len(top_hwh)!=1:
            raise RuntimeError(f'Ambiguous XSA members: {members}')
        selected_members={'.bit':members['.bit'],'.hwh':top_hwh}
        bit=archive.read(selected_members['.bit'][0]); hwh=archive.read(top_hwh[0])
    hardware=validate_hwh(hwh)
    # Verify that the generated project used the current new-IP RTL.
    generated=build/(project.name+'.gen')
    for ip in ('axis_square_pulse_v1','axis_awg_tuning_v3'):
        for source in (repo/'qick/firmware/ip'/ip/'src').glob('*.sv'):
            if source.name.startswith('tb_'): continue
            copies=list(generated.rglob(source.name))
            if not copies or any(p.read_bytes()!=source.read_bytes() for p in copies):
                raise RuntimeError(f'Generated RTL differs from current source: {source.name}')
    (project/'bitstream.bit').write_bytes(bit)
    (project/'bitstream.hwh').write_bytes(hwh)
    shutil.copy2(build/'bitstream.xsa',project/'bitstream.xsa')
    reports=project/'validation_reports'; reports.mkdir(exist_ok=True)
    for name in ('build_conditions.txt','build_result.txt','timing_summary_postroute.rpt','timing_paths_postroute.rpt',
                 'utilization_postroute.rpt','utilization_hierarchical_postroute.rpt',
                 'route_status_postroute.rpt','drc_postroute.rpt','methodology_postroute.rpt',
                 'square_dds_timing_postroute.rpt','bus_skew_postroute.rpt'):
        shutil.copy2(build/name,reports/name)
    constraint_reports=reports/'constraints'; constraint_reports.mkdir(exist_ok=True)
    for record in constraint_evidence:
        shutil.copy2(record['snapshot'], constraint_reports/record['name'])
    shutil.copy2(build/(project.name+'.runs')/'impl_1/d_1_wrapper_io_placed.rpt',
                 reports/'io_placed.rpt')
    sources=[]
    for directory in ('axis_awg_tuning_v3','axis_square_pulse_v1','axis_fir_decim_300to1_v2','axis_buffer_ddr_sample_v3'):
        sources.extend(p for p in (repo/'qick/firmware/ip'/directory).rglob('*')
                       if p.is_file() and p.suffix in ('.sv','.v','.xml','.tcl','.vh'))
    sources.extend(project.glob('*.tcl')); sources.extend(project.glob('*.xdc'))
    sources.append(Path(__file__).resolve())
    sources.extend(repo/'qick/qick_lib/qick'/name for name in
                   ('square_pulse.py','awg_tuning.py','dc_area.py','precompensation.py','asm_v1.py','qick.py','qick_asm.py','sim/qick_sim.py'))
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),vivado='2023.1',
                  part='xczu49dr-ffvf1760-2-e',build_directory=build.as_posix(),
                  qick_branch=git(repo,'branch','--show-current'),qick_base_commit=git(repo,'rev-parse','HEAD'),
                  build_result=result,build_conditions=conditions,constraint_sources=constraint_evidence,
                  hardware=hardware,xsa_members=selected_members,
                  functional_evidence=functional_evidence,
                  bus_skew_constraints=len(skew_results),
                  minimum_bus_skew_slack_ns=min(float(slack) for _,slack in skew_results),
                  xsa_all_hwh_members=members['.hwh'],
                  xsa_contains_matching_bitstream=True,xsa_contains_matching_hwh=True,
                  artifacts=[file_record(project/name,project) for name in ('bitstream.bit','bitstream.hwh','bitstream.xsa')],
                  qick_sources=[file_record(p,repo) for p in sorted(set(sources))])
    if args.gui_dir:
        gui=args.gui_dir.resolve()
        manifest.update(gui_branch=git(gui,'branch','--show-current'),gui_base_commit=git(gui,'rev-parse','HEAD'))
        manifest['gui_sources']=[file_record(p,gui) for p in sorted((gui/'DCWaveformGeneratorGUI').glob('*.py'))]
    (project/'build_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(published=project.as_posix(),hardware=hardware,timing=result),indent=2))


if __name__=='__main__':
    main()
