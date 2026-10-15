"""Add the already built v5 package locally; never connect to a board."""
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timezone
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile

from qick.sim import QickSim  # desktop imports only
from qick.ip import QickMetadata
from qick.output_sum import output_sum_config, apply_output_sum_config
import qick_update as update

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
REPO = Path('C:/GIT_Workspace/QSTL_QICK')
BUILD = Path('F:/Vivado_Output/a5full1')
DEST = REPO/'qick/firmware/projects/qstl_awg_v5'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def record(path):
    return dict(path=str(path), bytes=path.stat().st_size, sha256=update.sha(path))


def pairs(path):
    return dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)


def main():
    workflow = read(EVIDENCE/'workflow_status.json')
    candidate = read(BUILD/'candidate_manifest.json')
    software = read(EVIDENCE/'software_followup/status.json')
    scope = read(EVIDENCE/'software_followup/scope_after_tests.json')
    assert workflow['complete'] and workflow['build_exit_code'] == 0
    assert candidate['passed'] and software['complete'] and scope['passed']
    assert all(update.sha(Path(p)) == h for p,h in scope['source_hashes'].items())
    timing = pairs(BUILD/'build_result.txt')
    conditions = pairs(BUILD/'build_conditions.txt')
    assert conditions['project']=='qstl_awg_v5' and conditions['launch_jobs']=='4'
    assert conditions['general.maxThreads']=='5' and conditions['vivado_version']=='2023.1'
    summary=(BUILD/'timing_summary_postroute.rpt').read_text()
    assert 'All user specified timing constraints are met.' in summary
    assert re.search(r'checking no_clock \(0\)',summary)
    assert re.search(r'checking unconstrained_internal_endpoints \(0\)',summary)
    skew=re.findall(r'Slack\s*\((MET|VIOLATED)\)\s*:\s*([-\d.]+)ns',(BUILD/'bus_skew_postroute.rpt').read_text())
    assert len(skew)==14 and all(s=='MET' and float(n)>=0 for s,n in skew)
    for name,entry in candidate['artifacts'].items():
        source=BUILD/name
        assert source.stat().st_size==entry['bytes'] and update.sha(source)==entry['sha256'].lower()
    with zipfile.ZipFile(BUILD/'bitstream.xsa') as z:
        bits=[n for n in z.namelist() if n.endswith('.bit')]
        hwhs=[n for n in z.namelist() if Path(n).name=='d_1.hwh']
        assert len(bits)==len(hwhs)==1
        assert z.read(bits[0])==(BUILD/'bitstream.bit').read_bytes()
        assert z.read(hwhs[0])==(BUILD/'bitstream.hwh').read_bytes()
    xml=ET.parse(BUILD/'bitstream.hwh').getroot()
    meta=QickMetadata(SimpleNamespace(parser=SimpleNamespace(root=xml)))
    topology=dict(passed=True,hwh=str(DEST/'bitstream.hwh'),
                  sha256=update.sha(BUILD/'bitstream.hwh'),pairs=[],
                  awg_latency=31,rf_latency=31,clock_mhz=300)
    for awg_id,rf_id,dac in ((4,0,'10'),(5,1,'11'),(6,3,'12'),
                            (8,None,'20'),(9,None,'21'),(10,None,'22'),(11,None,'23')):
        awg=f'axis_awg_tuning_v3_{awg_id}'
        route=output_sum_config(meta,awg)
        assert route['output_sum_version']==2 and route['output_sum_awg_delay_cycles']==13
        assert meta.trace_forward(awg,'m_axis',['usp_rf_data_converter'])[:2]==('usp_rf_data_converter_0',f's{dac}_axis')
        cfg={'output_latency_cycles':16};apply_output_sum_config(cfg,route)
        assert cfg['output_latency_cycles']==31
        topology['pairs'].append(dict(awg=awg,rf=route['output_sum_rf'],dac=dac,route=route))
    update._v5_hardware_review(xml,topology,update.sha(BUILD/'bitstream.hwh'))
    constraints=[]
    for name in ('timing.xdc','ios.xdc'):
        source=DEST/name;snapshot=BUILD/'constraints'/name
        assert source.read_bytes()==snapshot.read_bytes()
        constraints.append(dict(name=name,source=str(source),snapshot=str(snapshot),sha256=update.sha(source),bytes=source.stat().st_size))
    manifest=dict(published_utc=datetime.now(timezone.utc).isoformat(),
                  publication_scope='local firmware repository only',board_deployed=False,
                  build=str(BUILD),conditions=conditions,timing=timing,constraints=constraints,
                  topology=topology,xsa_members=dict(bit=bits[0],hwh=hwhs[0]),
                  functional_gate=record(EVIDENCE/'prebuild_gate.json'),
                  software_integration=dict(complete=True,python_v5_timing_profile=True,
                      evidence=record(EVIDENCE/'software_followup/gui_rtl/reporting/result.json'),
                      sources=record(EVIDENCE/'software_followup/verified_sources/manifest.json')),
                  additional_validation=dict(status='running',scope='Virtual matrix21, compiler17, composite7 requested on2026-10-15',
                      evidence_directory=str(EVIDENCE/'expanded_gui_rtl_20261015')),
                  limitations=dict(exact_shared_port_zero_offset_supported=False,
                      second_command_lateness_cycles=3,board_analog_measured=False),
                  artifacts=[dict(path=str(DEST/name),bytes=entry['bytes'],sha256=entry['sha256'].lower())
                             for name,entry in candidate['artifacts'].items()])
    update._v5_build_review(manifest,DEST/'build_manifest.json')
    assert not (DEST/'build_manifest.json').exists(), 'Do not overwrite an existing package'
    for name in ('bitstream.bit','bitstream.hwh','bitstream.xsa'):
        assert not (DEST/name).exists(), f'Existing firmware: {name}'
    for name in ('bitstream.bit','bitstream.hwh','bitstream.xsa'):
        shutil.copy2(BUILD/name,DEST/name)
        assert update.sha(DEST/name)==candidate['artifacts'][name]['sha256'].lower()
    (DEST/'build_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    versions=update.firmware_versions(REPO)
    visible=[v for v in versions if v['label']=='qstl_awg_v5']
    assert len(visible)==1 and visible[0]['has_manifest']
    reviewed=update.review_package(REPO,active_firmware='projects/qstl_awg_v5/bitstream.bit')
    assert reviewed['manifest']['v5_hardware_validation']['passed']
    result=dict(passed=True,published_local=True,board_uploaded=False,visible=visible,
                files=[record(DEST/n) for n in ('bitstream.bit','bitstream.hwh','bitstream.xsa','build_manifest.json')],
                gui_package_review=dict(identity=reviewed['identity'],file_count=reviewed['file_count'],
                    setup_wns_ns=reviewed['setup_wns_ns'],hold_whs_ns=reviewed['hold_whs_ns'],
                    hardware=reviewed['manifest']['v5_hardware_validation']))
    (HERE/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('passed','published_local','board_uploaded','visible')}))


if __name__=='__main__':main()
