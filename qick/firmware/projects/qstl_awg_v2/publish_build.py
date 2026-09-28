"""Publish matching XSA members only after setup and hold timing pass."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
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
    assert 'axis_awg_tuning_v2_7' not in modules
    params = lambda m: {p.get('NAME'): p.get('VALUE') for p in m.findall('PARAMETERS/PARAMETER')}
    bus = lambda m, name: m.find(f"BUSINTERFACES/BUSINTERFACE[@NAME='{name}']").get('BUSNAME')
    assert params(square)['N_PTS'] == '16'
    assert params(square)['RC_PRECOMP_VERSION'] == '1'
    for module in modules.values():
        if module.get('MODTYPE') == 'axis_awg_tuning_v2':
            assert params(module)['RC_PRECOMP_VERSION'] == '1'
            assert params(module)['STEP_WIDTH'] == '32'
            assert params(module)['FRAC'] == '18'
            assert module.find("PORTS/PORT[@NAME='aclk']").get('CLKFREQUENCY') == '300000000'
    assert square.find("PORTS/PORT[@NAME='aclk']").get('CLKFREQUENCY') == '300000000'
    output_slice = modules['axis_register_slice_12']
    assert bus(square, 'm_axis') == bus(output_slice, 's_axis')
    rfdc = next(m for m in modules.values() if m.get('MODTYPE') == 'usp_rf_data_converter')
    assert bus(output_slice, 'm_axis') == bus(rfdc, 's13_axis')
    fir = next(m for m in modules.values() if m.get('MODTYPE') == 'axis_fir_decim_300to1_v2')
    ddr = next(m for m in modules.values() if m.get('MODTYPE') == 'axis_buffer_ddr_sample_v3')
    for key, value in dict(DECIM0='10', DECIM1='10', DECIM2='3', ACC_WIDTH='69',
                           OUT_WIDTH='64', OUTPUT_SCALE_LOG2='46').items():
        assert params(fir)[key] == value
    for key, value in dict(IQ_COMPONENT_BITS='64', S_AXIS_DATA_WIDTH='128',
                           IQ_SCALE_LOG2='46', DEFAULT_TRIGGER_DELAY_CYCLES='8712').items():
        assert params(ddr)[key] == value
    assert sum(m.get('MODTYPE') == 'axis_awg_tuning_v2' for m in modules.values()) == 7
    return dict(square_dac='13', square_fabric_clock_hz=300000000, samples_per_clock=16,
                awg_ip_version=2, awg_step_bits=32, awg_step_fraction_bits=18,
                square_scalar_sample_rate_hz=4800000000, nominal_gen_ch=7,
                iq_component_bits=64, fir_decimation=300, trigger_delay_cycles=8712,
                rc_precomp_version=1, rc_output_latency_cycles=11,
                rc_fraction_bits=48, rc_accumulator_bits=72,
                square_command_latency_cycles=15)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build_dir', type=Path)
    parser.add_argument('--gui-dir', type=Path)
    args=parser.parse_args()
    project=Path(__file__).resolve().parent
    repo=project.parents[3]
    build=args.build_dir.resolve()
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
    for ip in ('axis_square_pulse_v1','axis_awg_tuning_v2'):
        for source in (repo/'qick/firmware/ip'/ip/'src').glob('*.sv'):
            if source.name.startswith('tb_'): continue
            copies=list(generated.rglob(source.name))
            if not copies or any(p.read_bytes()!=source.read_bytes() for p in copies):
                raise RuntimeError(f'Generated RTL differs from current source: {source.name}')
    (project/'bitstream.bit').write_bytes(bit)
    (project/'bitstream.hwh').write_bytes(hwh)
    shutil.copy2(build/'bitstream.xsa',project/'bitstream.xsa')
    reports=project/'validation_reports'; reports.mkdir(exist_ok=True)
    for name in ('build_result.txt','timing_summary_postroute.rpt','timing_paths_postroute.rpt',
                 'utilization_postroute.rpt','utilization_hierarchical_postroute.rpt',
                 'route_status_postroute.rpt','drc_postroute.rpt','methodology_postroute.rpt',
                 'square_dds_timing_postroute.rpt','bus_skew_postroute.rpt'):
        shutil.copy2(build/name,reports/name)
    shutil.copy2(build/(project.name+'.runs')/'impl_1/d_1_wrapper_io_placed.rpt',
                 reports/'io_placed.rpt')
    sources=[]
    for directory in ('axis_awg_tuning_v2','axis_square_pulse_v1','axis_fir_decim_300to1_v2','axis_buffer_ddr_sample_v3'):
        sources.extend(p for p in (repo/'qick/firmware/ip'/directory).rglob('*')
                       if p.is_file() and p.suffix in ('.sv','.v','.xml','.tcl','.vh'))
    sources.extend(project.glob('*.tcl')); sources.extend(project.glob('*.xdc'))
    sources.append(Path(__file__).resolve())
    sources.extend(repo/'qick/qick_lib/qick'/name for name in
                   ('square_pulse.py','awg_tuning.py','precompensation.py','asm_v1.py','qick.py','qick_asm.py','sim/qick_sim.py'))
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),vivado='2023.1',
                  part='xczu49dr-ffvf1760-2-e',build_directory=build.as_posix(),
                  qick_branch=git(repo,'branch','--show-current'),qick_base_commit=git(repo,'rev-parse','HEAD'),
                  build_result=result,hardware=hardware,xsa_members=selected_members,
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
