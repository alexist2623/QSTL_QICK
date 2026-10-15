"""Completion choice is respected; cancellation and errors always mute."""
from types import SimpleNamespace
import pytest
import qick_qcodes_experiment as module
from qick_square_dds import SquarePulseConfig
from dc_waveform_core import QickDdrReadoutSpec


@pytest.mark.parametrize('outcome',['success','fail','cancel'])
@pytest.mark.parametrize('mute',[False,True])
def test_acquisition_cleanup_honors_mute_only_on_success(monkeypatch,outcome,mute):
    calls=[]
    cancelled=[False]
    soc=SimpleNamespace(rfb_set_gen_dc=lambda ch:calls.append(('dc',ch)),
                        stop_square_pulse=lambda ch:calls.append(('stop',ch)))
    def acquire(*args,**kwargs):
        calls.append(('acquire',7))
        if outcome=='fail': raise RuntimeError('capture failed')
        if outcome=='cancel': cancelled[0]=True
        return 'result'
    program=SimpleNamespace(acquire_fir_ddr=acquire)
    monkeypatch.setattr(module,'configure_rf_readout',lambda *args:{})
    monkeypatch.setattr(module,'build_qick_program',lambda *args,**kwargs:program)
    sequence=SimpleNamespace(square_pulse_config=SquarePulseConfig(7,mute_on_finish=mute),sweep_point_count=1)
    def check_cancel():
        if cancelled[0]:
            raise module.ExperimentCancelled('test cancellation')
    def run():
        return module._execute_qick_sequence_once(soc,{},sequence,awg_channels=(1,),
            repetitions_per_sweep=1,rf_specs=(),readout_spec=QickDdrReadoutSpec(0,'measure',0,2),
            cancel_check=check_cancel)
    if outcome=='fail':
        with pytest.raises(RuntimeError,match='capture failed'): run()
    elif outcome=='cancel':
        with pytest.raises(module.ExperimentCancelled): run()
    else:
        assert run()[1]=='result'
    assert calls==[('dc',7),('acquire',7)]+([('stop',7)] if mute or outcome!='success' else [])
