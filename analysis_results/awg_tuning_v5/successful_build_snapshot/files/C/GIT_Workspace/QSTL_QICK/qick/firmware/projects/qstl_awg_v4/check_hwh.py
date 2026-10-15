"""Check generated topology with the same metadata parser used on the board."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET
from qick.sim import QickSim  # desktop dependency stubs only
from qick.ip import QickMetadata
from qick.output_sum import output_sum_config, apply_output_sum_config


def validate(path):
    root=ET.parse(path).getroot()
    meta=QickMetadata(SimpleNamespace(parser=SimpleNamespace(root=root)))
    pairs=[]
    for awg, rf, sl, dac in ((4,0,8,'10'),(5,1,10,'11'),(6,3,11,'12'),
                             (8,None,13,'20'),(9,None,14,'21'),(10,None,15,'22'),(11,None,16,'23')):
        name=f'axis_awg_tuning_v3_{awg}'
        route=output_sum_config(meta,name)
        assert route['output_sum_block']==f'axis_output_sum_{awg}'
        assert route['output_sum_bypass']==(rf is None)
        assert route['output_sum_awg']==name
        assert route['output_sum_rf']==(None if rf is None else f'axis_signal_gen_v6_{rf}')
        assert meta.trace_forward(name,'m_axis',['usp_rf_data_converter'])[:2]==('usp_rf_data_converter_0',f's{dac}_axis')
        assert meta.get_fclk(route['output_sum_block'],'aclk')==300
        assert int(meta.get_param(name,'DC_AREA_BITS'))==48
        assert int(meta.get_param(f'axis_register_slice_{sl}','N'))==10
        cfg={'output_latency_cycles':16}
        apply_output_sum_config(cfg,route)
        apply_output_sum_config(cfg,route)
        assert cfg['output_latency_cycles']==18
        if rf is not None:
            rf_name=f'axis_signal_gen_v6_{rf}'
            rf_route=output_sum_config(meta,rf_name)
            assert rf_route['output_sum_role']=='rf'
            assert meta.trace_forward(rf_name,'m_axis',['usp_rf_data_converter'])[:2]==('usp_rf_data_converter_0',f's{dac}_axis')
            # Other zero-tied sinks are on the same scalar net as this source.
            assert ['sum_zero_word','dout'] in meta.trace_sig(f'axis_register_slice_{rf}','s_axis_tdata')
        pairs.append(dict(awg=name,rf=route['output_sum_rf'],dac=dac,route=route))
    assert output_sum_config(meta,'axis_signal_gen_v6_2')=={}
    assert output_sum_config(meta,'axis_square_pulse_v1_0')=={}
    return dict(passed=True,hwh=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),pairs=pairs,
                awg_latency=18,clock_mhz=300)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('hwh',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();result=validate(a.hwh);a.out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
