"""Version-specific GUI and compiler behavior with v5 delayed AWG output."""
from dataclasses import replace
import pytest
from qick.sim import QickSim  # noqa: F401 - desktop driver bootstrap
from qick.output_sum import apply_output_sum_config
from qick.awg_tuning import TProcV1BehaviorModel
from qick_fine_tune_sweep import FineTuneSequence, RfPulseConfig
from qick_qcodes_experiment import build_runtime_rf_pulses
from dc_waveform_core import QickRfPulseSpec
from qick_front_panel import identify_qick_front_panel
from test_output_sum_v4 import configuration as base_configuration
from test_shared_dac_awg_selection import window  # noqa: F401 - owned Qt fixture
from test_qick_front_panel import _live_config


def configuration():
    cfg=base_configuration(False)
    for channel,role in ((0,'rf'),(1,'awg')):
        apply_output_sum_config(cfg['gens'][channel],dict(output_sum_version=2,
            output_sum_role=role,post_output_latency_cycles=2,
            output_sum_awg_delay_cycles=13))
        cfg['gens'][channel]['dac']='10'
    return cfg


@pytest.mark.parametrize('delay',[0,1,2])
def test_equal_latency_does_not_hide_shared_port_conflicts(delay):
    seq=FineTuneSequence(('x',)).add_set('hold',(.02,),300)
    with pytest.raises(ValueError,match='v5 RF command conflicts'):
        seq.make_program(configuration(),awg_channels=(1,),
            rf_pulse=RfPulseConfig(0,'hold',30,2000,delay_tproc_cycles=delay,freq_mhz=1.))


@pytest.mark.parametrize('delay',[3,30,60])
@pytest.mark.parametrize('sweep',[False,True])
def test_v5_keeps_requested_offset_and_equal_physical_latency(delay,sweep):
    cfg=configuration()
    assert cfg['gens'][0]['output_latency_cycles']==cfg['gens'][1]['output_latency_cycles']==31
    seq=FineTuneSequence(('x',)).add_set('hold',(.02,),300).add_set('zero',(0.,),200)
    if sweep: seq.add_hold_duration_sweep('hold',1.,2.,3)
    program=seq.make_program(cfg,awg_channels=(1,),repetitions_per_sweep=2,
        rf_pulse=RfPulseConfig(0,'hold',30,2000,delay_tproc_cycles=delay,freq_mhz=1.))
    program.compile()
    model=TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(model)
    model.run(program)
    awg=[e for e in model.output_events if (e.word>>152)&255==1 and (e.word>>144)&3==1 and e.word&0xffffffff]
    rf=[e for e in model.output_events if (e.word>>152)&255==0 and (e.word>>96)&0xffffffff]
    assert len(awg)==len(rf)==(6 if sweep else 2)
    assert all(r.cycle==a.cycle+delay for r,a in zip(rf,awg))
    assert not model.timing_conflicts


@pytest.mark.parametrize('change',[
    dict(power_calibration_enabled=True,power_calibration_database_path='old_rf.db'),
    dict(att1_db=2.),dict(filter_type='lowpass')])
def test_v5_still_rejects_dedicated_rf_connector_controls(change):
    spec=replace(QickRfPulseSpec(0,'hold',0.,.1,1.,2000,0.,0.),**change)
    with pytest.raises(ValueError,match='v5 RF generator'):
        build_runtime_rf_pulses(configuration(),[spec])


@pytest.mark.parametrize('version',[1,2])
@pytest.mark.parametrize('pair',range(3))
def test_front_panel_selects_awg_on_each_versioned_shared_dac(window,version,pair):
    cfg=_live_config()
    cfg['gens']=[]
    for index in range(3):
        for kind,role in (('axis_signal_gen_v6','rf'),('axis_awg_tuning_v3','awg')):
            cfg['gens'].append(dict(dac=f'1{index}',fullpath=f'{kind}_{index}',type=kind,
                output_sum_version=version,output_sum_role=role,output_sum_bypass=False))
    panel_cfg=identify_qick_front_panel(cfg)
    assert all(p.baseband_only and p.summed_output for p in panel_cfg.outputs[4:7])
    window._on_qick_configuration_identified(panel_cfg)
    window._show_qick_front_panel('output',window._multi_ctrl)
    panel=window._qick_front_panel
    panel.canvas.select_port('output',4+pair)
    assert panel.output_channel.count()==1
    assert panel.selected_settings()['output_ch']==2*pair+1
    assert not panel.output_nqz.isEnabled()
    assert panel.output_nqz.value()==1
    assert not panel.output_att1_db.isEnabled()
    assert not panel.output_filter_type.isEnabled()
    assert 'AWG + RF sum' in panel.summary.text()


@pytest.mark.parametrize('version',[1,2])
def test_bypass_awg_ports_remain_baseband_without_rf_sum_label(version):
    cfg=_live_config()
    cfg['gens']=[dict(dac='00',type='axis_awg_tuning_v3',fullpath='awg',
        output_sum_version=version,output_sum_role='awg',output_sum_bypass=True)]
    output=identify_qick_front_panel(cfg).outputs[0]
    assert output.baseband_only and not output.summed_output
