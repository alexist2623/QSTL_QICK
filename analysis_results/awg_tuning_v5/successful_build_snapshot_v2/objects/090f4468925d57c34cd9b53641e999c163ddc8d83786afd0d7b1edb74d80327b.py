"""DAC readback, shared GUI state, and voltage-preserving compilation."""
from dataclasses import replace
from types import SimpleNamespace
import numpy as np
import pytest
from qick.dac_current import DacCurrentControl
from qick_dac_current import full_scale_mv, verify_current_settings
from dc_waveform_core import PulseSequence, QickSweepSpec, build_qick_sequence, generate_qick_program_code
from test_square_awg_exclusion import window, firmware


class Block:
    DACCompMode = 0
    OutputCurr = 20000
    def __init__(self):
        self.writes = []
    def SetDACVOP(self, current):
        self.writes.append(current)
        self.OutputCurr = current - current % 25


class Soc(DacCurrentControl, dict):
    def __init__(self):
        super().__init__(gens=[dict(dac='00', type='axis_awg_tuning_v1'),
                               dict(dac='01', type='axis_signal_gen_v6'),
                               dict(dac='02', type='axis_square_pulse_v1')])
        self.rf = SimpleNamespace(cfg={'ip_type': 2},
                                  dac_tiles=[SimpleNamespace(blocks=[Block() for _ in range(4)])])


def records(currents=(10000, 32000, 20000)):
    return {dac: dict(converter_id=dac, channels=[ch], dc_output=True,
                     current_ua=current, adjustable=True, reason='')
            for dac, ch, current in zip(('10', '11', '13'), (1, 3, 7), currents)}


def test_server_ip_restriction_actual_readback_and_shared_dac():
    soc = Soc()
    assert soc.set_dac_current('00', 10013)['00']['current_ua'] == 10000
    assert soc.get_dac_current_settings()['00']['full_scale_mv'] == 400
    with pytest.raises(ValueError, match='RF'):
        soc.set_dac_current('01', 16000)
    assert not soc.rf.dac_tiles[0].blocks[1].writes
    soc['gens'].append(dict(dac='00', type='axis_signal_gen_v6'))
    with pytest.raises(ValueError, match='RF'):
        soc.set_dac_current('00', 20000)


def test_server_does_not_enable_legacy_mode_or_accept_invalid_current():
    soc = Soc()
    for value in (0, 33000, float('nan'), 10000.5):
        with pytest.raises(ValueError):
            soc.set_dac_current('00', value)
    soc.rf.dac_tiles[0].blocks[0].DACCompMode = 1
    with pytest.raises(ValueError, match='VOP'):
        soc.set_dac_current('00', 12000)
    assert not soc.rf.dac_tiles[0].blocks[0].writes


def test_stale_current_blocks_execution():
    soc = Soc()
    expected = soc.get_dac_current_settings()
    verify_current_settings(soc, {'00': expected['00']})
    soc.set_dac_current('00', 10000)
    with pytest.raises(RuntimeError, match='changed'):
        verify_current_settings(soc, {'00': expected['00']})


def test_gui_shared_current_preserves_mv_and_square_scale(window):
    window._add_port()
    window._pulse[0].v[:] = 100
    window._pulse[1].v[:] = -100
    window._sweep_specs = [QickSweepSpec('set_0', 'awg_0', 50/800, 100/800, 3)]
    window._on_qick_configuration_identified(replace(firmware(), dac_current_settings=records()))
    assert window._qick_full_scale_mv == 1280
    assert window._sweep_specs[0].start * 1280 == 50
    args = window._experiment_run_arguments(require_readout=False, require_run_config=False)
    seq = args['sequence']
    assert seq.output_full_scales_mv == (400., 1280.)
    assert seq.amplitudes_at(0, 0) == pytest.approx((50/400, -100/1280))
    panel = window._qick_front_panel
    panel.set_scope('output')
    panel._select_port('output', 4)
    assert panel.output_current_ma.isEnabled()
    assert '400' in panel.output_full_scale.text()
    panel._select_port('output', 0)
    assert not panel.output_current_ma.isEnabled()
    window._square_wave_panel.gen_ch.setValue(7)
    assert window._square_wave_panel.full_scale_mv.value() == 800
    assert window._experiment_panel.full_scale_mv.isHidden()
    assert window._square_wave_panel.full_scale_mv.isHidden()
    saved = window._settings_to_dict()
    window._apply_decoded_settings(window._decode_settings(saved))
    assert window._dac_current_state.scale(1) == 400
    assert window._dac_current_state.scale(3) == 1280


def test_stability_and_saved_physical_voltages_use_per_channel_current(window):
    from qick_qcodes_experiment import build_awg_vertex_record
    window._on_qick_configuration_identified(replace(firmware(), dac_current_settings=records()))
    panel=window._stability_panel
    for axis, channel in ((panel.x_axis,1),(panel.y_axis,3)):
        axis.apply_front_panel_settings({'output_ch':channel})
        axis.start_mv.setValue(100);axis.stop_mv.setValue(200);axis.points.setValue(3)
    args=window._stability_run_arguments(save=False)
    seq=args['sequence']
    assert seq.output_full_scales_mv == (400,1280)
    np.testing.assert_allclose(np.asarray(seq.amplitudes_at(0,0))*[400,1280],[100,100])
    record=build_awg_vertex_record(seq,point_index=0,fabric_mhz=300,full_scale_mv=1280)
    assert record['physical_values_mv']['awg_0'][0] == pytest.approx(100)
    assert record['physical_values_mv']['gen_3'][0] == pytest.approx(100)


def test_larger_current_allows_voltage_above_old_800mv_and_lower_current_rejects(window):
    window._on_qick_configuration_identified(replace(firmware(),dac_current_settings=records((32000,10000,20000))))
    window._pulse[0].v[:]=1000
    seq=window._experiment_run_arguments(require_readout=False,require_run_config=False)['sequence']
    assert seq.amplitudes_at(0,0)[0] == pytest.approx(1000/1280)
    window._on_qick_configuration_identified(replace(firmware(),dac_current_settings=records((10000,32000,20000))))
    with pytest.raises(ValueError,match='amplitude'):
        seq=window._experiment_run_arguments(require_readout=False,require_run_config=False)['sequence']
        seq.amplitudes_at(0,0)


def test_apply_current_by_clicking_front_panel_from_multiple_tabs(window, monkeypatch):
    """Use the real GUI worker and server setter, replacing only the RFDC device."""
    import DCWaveform_Generator as gui
    from PyQt5 import QtTest, QtCore
    soc=Soc()
    config=firmware()
    soc['gens']=[{} for _ in range(12)]
    for port in config.outputs:
        for ch in port.qick_channels:
            soc['gens'][ch]=dict(dac=port.converter_id,
                type='axis_square_pulse_v1' if ch==7 else
                     'axis_awg_tuning_v1' if ch in config.awg_tuning_channels else 'axis_signal_gen_v6')
    soc.rf.dac_tiles=[SimpleNamespace(blocks=[Block() for _ in range(4)]) for _ in range(3)]
    monkeypatch.setattr(gui, 'connect_qick', lambda _: (soc, {}))
    monkeypatch.setattr(gui, 'identify_qick_front_panel', lambda _: config)
    window._on_qick_configuration_identified(replace(config,dac_current_settings=soc.get_dac_current_settings()))
    window._sweep_specs=[QickSweepSpec('set_0','awg_0',50/800,100/800,3)]
    for editor,voltage,tau in ((window._experiment_panel,70,300),
                               (window._stability_panel,80,500)):
        editor.bias_t_type.dc_checkbox.setChecked(True)
        editor.bias_t_type.rc_checkbox.setChecked(True)
        editor.bias_t_compensation_mv.setValue(voltage)
        editor.bias_t_filter_tau_us.setValue(tau)
    panel=window._qick_front_panel
    expected={'10':20000,'11':20000}
    for target,dac,current in ((window._multi_ctrl,'10',10000),
                                (window._stability_panel.x_axis,'10',32000),
                                (window._multi_ctrl,'11',16000),
                                (window._multi_ctrl,'10',12000)):
        window._show_qick_front_panel('output',target)
        panel._select_port('output',4*int(dac[0])+int(dac[1]))
        panel.output_current_ma.setValue(current/1000)
        QtTest.QTest.mouseClick(panel.output_current_apply,QtCore.Qt.LeftButton)
        timer=QtCore.QElapsedTimer();timer.start()
        while window._experiment_thread is not None and timer.elapsed()<5000:
            QtTest.QTest.qWait(10)
        assert window._experiment_thread is None
        expected[dac]=current
        assert panel.output_current_ma.value()==pytest.approx(current/1000)
        assert window._qick_awg_channels==(1,)
        for converter,value in expected.items():
            tile,block=map(int,converter)
            assert soc.rf.dac_tiles[tile].blocks[block].OutputCurr==value
            assert window._dac_current_state.records[converter]['current_ua']==value
        assert window._sweep_specs[0].start*window._qick_full_scale_mv==pytest.approx(50)
        assert window._experiment_panel._map_sweep_specs[0].start*window._qick_full_scale_mv==pytest.approx(50)
        for editor,voltage,tau in ((window._experiment_panel,70,300),
                                   (window._stability_panel,80,500)):
            assert editor.bias_t_type.currentData()=='dc_rc'
            assert editor.bias_t_compensation_mv.value()==voltage
            assert editor.bias_t_filter_tau_us.value()==tau
    assert soc.rf.dac_tiles[1].blocks[0].writes==[10000,32000,12000]
    assert soc.rf.dac_tiles[1].blocks[1].writes==[16000]
    assert all(not block.writes for tile in (soc.rf.dac_tiles[0],soc.rf.dac_tiles[2]) for block in tile.blocks)
    assert not soc.rf.dac_tiles[1].blocks[2].writes
    assert not soc.rf.dac_tiles[1].blocks[3].writes
    # Reopening the other tab reads the same converter, rather than a tab-local copy.
    window._show_qick_front_panel('output',window._stability_panel.x_axis)
    panel._select_port('output',4)
    assert panel.output_current_ma.value()==12
    window._qick_front_panel_dialog.close()


@pytest.mark.parametrize('scales', [(800, 800), (400, 1280), (1280, 400)])
@pytest.mark.parametrize('dc_mode', ['fixed_voltage', 'fixed_time'])
def test_channel_scaling_crosscap_sweep_compensation_export(scales, dc_mode):
    pulses=[]
    for voltage in (100., -50.):
        p=PulseSequence();p.t=np.array([0., 1000.]);p.v=np.array([voltage, voltage]);pulses.append(p)
    args=dict(output_names=('awg_0','awg_1'), full_scale_mv=800,
              output_full_scales_mv=scales, cross_capacitance=((1,.2),(-.1,1)),
              sweeps=(QickSweepSpec('set_0','awg_0',100/800,200/800,3),),
              bias_t_compensation_enabled=True,bias_t_compensation_type='dc',
              bias_t_compensation_voltage_mv=200,bias_t_compensation_mode=dc_mode,
              bias_t_compensation_duration_us=2.)
    seq=build_qick_sequence(pulses,**args)
    for point in range(3):
        expected=np.array(((100+50*point)-10, -50-.1*(100+50*point)))
        np.testing.assert_allclose(np.array(seq.amplitudes_at(point,0))*scales, expected)
        for output, comp in enumerate(seq.bias_t_compensation_preview(point)):
            if dc_mode=='fixed_voltage':
                assert abs(comp.target_amplitude*scales[output]) == pytest.approx(200)
    code=generate_qick_program_code(pulses,awg_channels=(0,1),**args)
    ns={};exec(code,ns)
    exported=ns['build_sequence']()
    assert exported.output_full_scales_mv == tuple(scales)
    np.testing.assert_allclose(exported.amplitudes_at(2,0),seq.amplitudes_at(2,0))


@pytest.mark.parametrize('scales', [(400.,1280.),(1280.,400.)])
@pytest.mark.parametrize('mode', ['fixed_voltage','fixed_time'])
def test_compiled_dc_area_and_rc_coefficient_against_independent_voltage_math(scales,mode):
    from test_rc_precompensation import upgraded
    from test_qick_fine_tune_sweep import _independent_awg_soccfg
    from qick.awg_tuning import TProcV1BehaviorModel
    pulses=[]
    for multiplier in (1.,-.5):
        p=PulseSequence();p.t=np.array([0.,1000.,2000.,3000.])
        p.v=np.array([100.,100.,-50.,-50.])*multiplier;pulses.append(p)
    seq=build_qick_sequence(pulses,full_scale_mv=1280,output_full_scales_mv=scales,
        sweeps=(QickSweepSpec('set_0','awg_0',100/1280,200/1280,3),
                QickSweepSpec('set_0','awg_1',-50/1280,-100/1280,3)),
        bias_t_compensation_enabled=True,bias_t_compensation_type='dc_rc',
        bias_t_compensation_mode=mode,bias_t_compensation_voltage_mv=200,
        bias_t_compensation_duration_us=2,bias_t_filter_tau_us=300)
    prog=seq.make_program(upgraded(_independent_awg_soccfg()),awg_channels=(0,1),
                          repetitions_per_sweep=2,compile_validation_mode='full')
    model=TProcV1BehaviorModel(strict=True);prog.load_runtime_dmem_into_model(model);model.run(prog)
    assert not model.timing_conflicts
    configs=[e for e in model.output_events if e.word & (1<<149)]
    # Tau and scalar clock determine the coefficient, independently of current.
    expected_coefficient=round(2**48/(2*300*4800))
    assert all((e.word & 0xffffffff)==expected_coefficient for e in configs)
    assert len(configs)==2*(9*2+1)
    for point in range(9):
        x,y=np.unravel_index(point,(3,3))
        starts=(100+50*x,-50-25*y);stops=(-50,25)
        for channel,scale in enumerate(scales):
            area=1.5*(starts[channel]+stops[channel])  # mV us: hold + linear ramp + hold.
            field=next(f for f in prog._bias_t_fields if f['output_index']==channel)
            if mode=='fixed_time':
                actual_mv=prog._bias_t_target_code_actual[point,channel]*scale/32768
                assert actual_mv==pytest.approx(-area/2,abs=scale/8192/2)
                assert field['fixed_duration_tproc_cycles']/300==2
            else:
                code=field['negative_code'] if area>0 else field['positive_code']
                assert abs(code*scale/32768)==pytest.approx(200,abs=scale/8192/2)
                bits=field['duration_frac_bits']
                duration=(abs(int(prog._bias_t_duration_q_actual[point,channel]))+(1<<(bits-1)))>>bits
                assert duration/300==pytest.approx(abs(area)/200,abs=.5/300+1e-10)
