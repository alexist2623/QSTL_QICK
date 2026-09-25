"""Check copied IP parameters and retained interface connectivity against HWH."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument('project',type=Path);a=p.parse_args()
    meta=json.loads((HERE/'topology.json').read_text())
    source=ET.parse(HERE.parent/'qstl_awg_tuning_fir_1msps_iq64_sq_pulse/bitstream.hwh')
    generated=ET.parse(a.project/'qstl_gui_rtl_sim.gen/sources_1/bd/sim_bd/hw_handoff/sim_bd.hwh')
    old={m.get('FULLNAME').strip('/'):m for m in source.findall('.//MODULE')}
    new={m.get('FULLNAME').strip('/'):m for m in generated.findall('.//MODULE')}
    differences=[];checked=0
    oldnets={};newnets={}
    for name,cell in meta['cells'].items():
        original=old[cell['source_path']];copy=new[name]
        op={x.get('NAME'):x.get('VALUE') for x in original.findall('./PARAMETERS/PARAMETER')}
        np={x.get('NAME'):x.get('VALUE') for x in copy.findall('./PARAMETERS/PARAMETER')}
        for key,value in op.items():
            if key in {'Component_Name','C_COMPONENT_NAME'} or key.startswith('EDK_'):continue
            if key in np:
                checked+=1
                if np[key]!=value:differences.append(dict(cell=name,parameter=key,production=value,simulation=np[key]))
        for module,nets in [(original,oldnets),(copy,newnets)]:
            for bus in module.findall('./BUSINTERFACES/BUSINTERFACE'):
                net=bus.get('BUSNAME')
                if net and net!='__NOC__':nets.setdefault(net,set()).add(name+'/'+bus.get('NAME'))
    oldpairs={frozenset(v) for v in oldnets.values() if len(v)>1}
    newpairs={frozenset(v) for v in newnets.values() if len(v)>1}
    topology_missing=[sorted(v) for v in oldpairs-newpairs]
    topology_extra=[sorted(v) for v in newpairs-oldpairs]
    functional=[d for d in differences if d['parameter'] not in {'C_BASEADDR','C_HIGHADDR'}]
    forbidden=[dict(name=name,type=m.get('MODTYPE')) for name,m in new.items()
               if m.get('MODTYPE') in {'usp_rf_data_converter','zynq_ultra_ps_e','processing_system7'}]
    result=dict(passed=not(functional or topology_missing or topology_extra or forbidden),
                rfdc_or_arm_ps_cells=forbidden,
                cells=len(meta['cells']),parameters_checked=checked,
                functional_parameter_differences=functional,
                parameter_differences=differences,retained_bus_nets=len(oldpairs),
                missing_connections=topology_missing,extra_connections=topology_extra)
    (HERE/'topology_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['passed']:raise SystemExit(1)


if __name__=='__main__':main()
