"""Publish only a timing-closed v4 XSA whose RTL and GUI evidence still match."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import zipfile
from check_hwh import validate as validate_topology
from validate_scope import validate_functional

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


def record(path):
    return dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    p=argparse.ArgumentParser();p.add_argument('build',type=Path);a=p.parse_args();build=a.build.resolve()
    validate_functional()
    assert not build.is_relative_to(ROOT) and not build.is_relative_to(ROOT.parent/'PulseGenerator')
    assert (build/'qstl_awg_v4.xpr').is_file()
    spec=importlib.util.spec_from_file_location('v3_publisher_checks',HERE.parent/'qstl_awg_v3/publish_build.py')
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    read_pairs=lambda path:dict(line.split('=',1) for line in path.read_text().splitlines() if '=' in line)
    conditions=read_pairs(build/'build_conditions.txt')
    assert conditions['launch_jobs']=='4' and conditions['general.maxThreads']=='5'
    constraints=legacy.validate_build_constraints(build,HERE,conditions)
    result=read_pairs(build/'build_result.txt')
    assert result['timing_closed']=='YES' and 'Complete' in result['implementation_status']
    assert float(result['setup_wns_ns'])>=0 and float(result['hold_whs_ns'])>=0
    summary=(build/'timing_summary_postroute.rpt').read_text()
    assert 'All user specified timing constraints are met.' in summary
    for check in ('no_clock','unconstrained_internal_endpoints'):
        assert re.search(r'checking '+check+r' \(0\)',summary)
    skew=re.findall(r'Slack\s*\((MET|VIOLATED)\)\s*:\s*([-\d.]+)ns',(build/'bus_skew_postroute.rpt').read_text())
    assert skew and all(state=='MET' and float(slack)>=0 for state,slack in skew)
    with zipfile.ZipFile(build/'bitstream.xsa') as archive:
        bits=[n for n in archive.namelist() if n.endswith('.bit')]
        hwhs=[n for n in archive.namelist() if Path(n).name=='d_1.hwh']
        assert len(bits)==len(hwhs)==1
        bit=archive.read(bits[0]);hwh=archive.read(hwhs[0])
    assert (build/'bitstream.hwh').read_bytes()==hwh
    hardware=legacy.validate_hwh(hwh)
    topology=validate_topology(build/'bitstream.hwh')
    hardware.update(awg_output_latency_cycles=18,output_sum_pipeline_cycles=2,rf_output_latency_cycles=31)
    generated=build/'qstl_awg_v4.gen'
    for ip in ('axis_awg_tuning_v3','axis_square_pulse_v1','axis_output_sum_v1'):
        for source in (ROOT/'qick/firmware/ip'/ip/'src').glob('*.sv'):
            if source.name.startswith('tb_'):continue
            copies=list(generated.rglob(source.name))
            assert copies and all(p.read_bytes()==source.read_bytes() for p in copies),source
    # Every guard above runs before changing repository firmware artifacts.
    (HERE/'bitstream.bit').write_bytes(bit);(HERE/'bitstream.hwh').write_bytes(hwh)
    shutil.copy2(build/'bitstream.xsa',HERE/'bitstream.xsa')
    reports=HERE/'validation_reports';reports.mkdir(exist_ok=True)
    for name in ('build_result.txt','build_conditions.txt','timing_summary_postroute.rpt','timing_paths_postroute.rpt',
                 'bus_skew_postroute.rpt','route_status_postroute.rpt','utilization_postroute.rpt','drc_postroute.rpt'):
        shutil.copy2(build/name,reports/name)
    manifest=dict(published_utc=datetime.now(timezone.utc).isoformat(),build=str(build),conditions=conditions,
                  timing=result,constraints=constraints,hardware=hardware,topology=topology,
                  xsa_members=dict(bit=bits[0],hwh=hwhs[0]),
                  functional_gate=record(ROOT/'analysis_results/awg_tuning_v4/prebuild_gate.json'),
                  artifacts=[record(HERE/n) for n in ('bitstream.bit','bitstream.hwh','bitstream.xsa')])
    (HERE/'build_manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({'published':str(HERE),'timing':result},indent=2))


if __name__=='__main__':main()
