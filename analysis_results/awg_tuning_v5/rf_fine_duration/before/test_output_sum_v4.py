"""v4 physical-output timing and shared-DAC regressions (no hardware writes)."""
from dataclasses import replace
import pytest
from qick.sim import QickSim  # desktop driver imports
from qick.awg_tuning import TProcV1BehaviorModel
from qick.output_sum import apply_output_sum_config, validate_shared_dac_config
from test_qick_fine_tune_sweep import _shared_tmux_soccfg
from qick_fine_tune_sweep import FineTuneSequence, RfPulseConfig
from qick_qcodes_experiment import build_runtime_rf_pulses, configure_rf_output
from dc_waveform_core import QickRfPulseSpec


def configuration(v4=True):
    cfg=_shared_tmux_soccfg()
    cfg['gens'][1].update(type='axis_awg_tuning_v3',frac=18,step_width=32,
        rc_precomp_version=1,dc_area_version=1,dc_area_bits=48,dc_start_cycles=17,output_latency_cycles=16)
    if v4:
        for ch,role in ((0,'rf'),(1,'awg')):
            apply_output_sum_config(cfg['gens'][ch],dict(output_sum_version=1,
                output_sum_role=role,post_output_latency_cycles=2))
            cfg['gens'][ch]['dac']='10'
    return cfg


@pytest.mark.parametrize('delay',[0,30,60])
@pytest.mark.parametrize('sweep',[False,True])
def test_coincident_samples_and_offsets_with_hold_sweep(delay,sweep):
    cfg=configuration()
    seq=FineTuneSequence(('x',)).add_set('hold',(.02,),300).add_set('zero',(0.,),200)
    if sweep:seq.add_hold_duration_sweep('hold',1.,2.,100)
    p=seq.make_program(cfg,awg_channels=(1,),repetitions_per_sweep=2,
        rf_pulse=RfPulseConfig(0,'hold',30,2000,delay_tproc_cycles=delay,freq_mhz=1.))
    p.compile()
    model=TProcV1BehaviorModel(strict=True);p.load_runtime_dmem_into_model(model);model.run(p)
    awg=[e for e in model.output_events if (e.word>>152)&255==1 and (e.word>>144)&3==1 and e.word&0xffffffff]
    rf=[e for e in model.output_events if (e.word>>152)&255==0 and (e.word>>96)&0xffffffff]
    assert len(awg)==len(rf)==(200 if sweep else 2)
    assert all(r.cycle+44==a.cycle+31+delay for r,a in zip(rf,awg))
    assert not model.timing_conflicts


@pytest.mark.parametrize('delay',[11,12,13,14,15])
def test_v4_does_not_silently_shift_unschedulable_rf(delay):
    seq=FineTuneSequence(('x',)).add_set('hold',(.02,),300)
    with pytest.raises(ValueError,match='v4 RF command conflicts'):
        seq.make_program(configuration(),awg_channels=(1,),
            rf_pulse=RfPulseConfig(0,'hold',30,2000,delay_tproc_cycles=delay,freq_mhz=1.))


def test_legacy_rf_timestamp_convention_is_unchanged():
    seq=FineTuneSequence(('x',)).add_set('hold',(.02,),300)
    p=seq.make_program(configuration(False),awg_channels=(1,),
        rf_pulse=RfPulseConfig(0,'hold',30,2000,freq_mhz=1.))
    assert p.aux_timing['rf_start']==16


@pytest.mark.parametrize('nqz,mixer',[(2,None),(1,1.)])
def test_shared_dac_requires_baseband(nqz,mixer):
    with pytest.raises(ValueError,match='shared baseband'):
        validate_shared_dac_config(configuration()['gens'][0],nqz,mixer)
    validate_shared_dac_config(configuration(False)['gens'][0],nqz,mixer)


def test_routing_updates_latency_once():
    cfg={'output_latency_cycles':16}
    route=dict(output_sum_version=1,output_sum_role='awg',post_output_latency_cycles=2)
    for _ in range(3):apply_output_sum_config(cfg,route)
    assert cfg['output_latency_cycles']==18


@pytest.mark.parametrize('change',[dict(power_calibration_enabled=True,power_calibration_database_path='old_rf.db'),dict(att1_db=2.),dict(filter_type='lowpass')])
def test_old_rf_calibration_and_controls_are_rejected(change):
    spec=replace(QickRfPulseSpec(0,'hold',0.,.1,1.,2000,0.,0.),**change)
    with pytest.raises(ValueError,match='v4 RF generator'):
        build_runtime_rf_pulses(configuration(),[spec])


def test_output_setup_uses_the_shared_dc_connector():
    class Soc:
        def get_cfg(self):return configuration()
        def rfb_set_gen_dc(self,ch):self.channel=ch
    soc=Soc()
    configure_rf_output(soc,QickRfPulseSpec(0,'hold',0.,.1,1.,2000,0.,0.))
    assert soc.channel==0
