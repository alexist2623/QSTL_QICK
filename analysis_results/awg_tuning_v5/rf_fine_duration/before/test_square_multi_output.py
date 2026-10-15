"""Multiple physical square DDS ports, shared RC settings and real compiler words."""
from dataclasses import replace
from itertools import product
from types import SimpleNamespace

import pytest
from qick.sim import QickSim  # Install desktop simulation driver stubs.
from qick.awg_tuning import TProcV1BehaviorModel
from qick.square_pulse import square_words
from dc_waveform_core import generate_qick_program_code, QickDdrReadoutSpec
from qick_fine_tune_sweep import FineTuneSequence
from qick_square_dds import (SquarePulseConfig, SquarePulseSweep, attach_square_settings,
                             decode_square_outputs)
from test_qick_square_dds import configuration
from test_rc_precompensation import upgraded
from test_square_awg_exclusion import window, firmware


def multi_firmware():
    return replace(firmware(), square_pulse_channels=(5, 7),
                   awg_tuning_channels=(1, 3, 8, 9, 10, 11))


def multi_configuration():
    cfg = upgraded(configuration())
    cfg['gens'].append(dict(cfg['gens'][1], tmux_ch=3, dac='12'))
    return cfg


@pytest.mark.parametrize('rc', [False, True])
def test_two_ports_have_independent_cartesian_words_and_mute(rc):
    cfg = multi_configuration()
    configs = (SquarePulseConfig(1, full_scale_mv=400, mute_on_finish=False),
               SquarePulseConfig(2, full_scale_mv=1280, mute_on_finish=True))
    # Same parameter on two different outputs must remain independent.
    axes = (SquarePulseSweep('amplitude', 5, 15, 20, 1, output_name='square1'),
            SquarePulseSweep('amplitude', 20, 40, 20, 2, output_name='square2'))
    seq = FineTuneSequence(('x',)).add_set('hold', 0., 300)
    seq.set_rc_compensation(300., enabled=rc)
    attach_square_settings(seq, configs, axes, follow_experiment_rc=True)
    prog = seq.make_program(cfg, awg_channels=(0,), repetitions_per_sweep=2)
    prog.compile()
    model = TProcV1BehaviorModel(strict=True)
    prog.load_runtime_dmem_into_model(model); model.run(prog)
    for index, config in enumerate(prog.square_pulse_configs):
        gen = cfg['gens'][config.gen_ch]
        actual = [event.word for event in model.output_events if event.word >> 152 == gen['tmux_ch']]
        expected = []
        for point in product(*(axis.points for axis in axes)):
            gain = config.word('amplitude', point[index], gen)
            words = square_words(config.word('frequency', .04, gen), 0, gain,
                                 tmux_ch=gen['tmux_ch'], rc_enable=rc,
                                 rc_increment=config.rc_step(gain, gen))
            expected.extend([sum(word << (32*i) for i, word in enumerate(words))] * 2)
        assert actual[:800] == expected
        assert len(actual) == 800 + int(config.mute_on_finish)
        if config.mute_on_finish:
            assert actual[-1] & (1 << 128) == 0
        assert config.rc_enabled == rc
        assert config.rc_tau_us == (300. if rc else 1000.)
    assert not model.timing_conflicts
    assert model.dmem[prog.COUNTER_ADDR] == 800


def test_ports_add_remove_firmware_restrictions_and_roundtrip(window, tmp_path):
    panel = window._square_dds_panel
    assert not panel.add_button.isEnabled()
    window._on_qick_configuration_identified(multi_firmware())
    first = panel._panels[0]
    assert first.channel.value() == 5 and panel.add_button.isEnabled()
    second = panel.add_port()
    assert second.channel.value() == 7
    assert not panel.add_button.isEnabled() and panel.add_port() is None
    assert first.allowed_output_channels(multi_firmware()) == {5}
    assert second.allowed_output_channels(multi_firmware()) == {7}
    with pytest.raises(ValueError, match='another port'):
        second.apply_front_panel_settings({'output_ch': 5})
    for output in (first, second):
        output.enabled.setChecked(True)
        assert output.output_selector.controls.isHidden()
        assert output.output_selector.description.isHidden()
        assert not hasattr(output, 'rc_enabled')
    first.rows['phase']['value'].setValue(90)
    second.rows['phase']['value'].setValue(180)
    second.mute_on_finish.setChecked(False)
    original = panel.settings_dict()
    path = window._save_settings_json(tmp_path/'multi_square')
    panel.remove_port(second)
    assert panel.add_button.isEnabled()
    window._load_settings_json(path)
    assert panel.settings_dict() == original
    window._show_qick_front_panel('output', panel._panels[1])
    assert window._qick_front_panel.output_channel.currentData() == 7
    for output in tuple(panel._panels):
        panel.remove_port(output)
    args = window._experiment_run_arguments(require_readout=False, require_run_config=False)
    assert args['sequence'].square_pulse_configs == ()
    assert panel.add_button.isEnabled()


@pytest.mark.parametrize('rc', [False, True])
def test_experiment_rc_overrides_legacy_port_settings_live_and_export(window, rc):
    window._on_qick_configuration_identified(multi_firmware())
    panel = window._square_dds_panel
    legacy = {'outputs': [dict(enabled=True, gen_ch=ch, rc_enabled=not rc, rc_tau_us=10.)
                          for ch in (5, 7)]}
    panel.load_settings(legacy)
    exp = window._experiment_panel
    exp.bias_t_filter_tau_us.setValue(300.)
    exp.bias_t_type.rc_checkbox.setChecked(rc)
    seq = window._experiment_run_arguments(require_readout=False, require_run_config=False)['sequence']
    assert len(seq.square_pulse_configs) == 2
    for config in seq.square_pulse_configs:
        assert config.rc_enabled == rc
        if rc:
            assert config.rc_tau_us == seq.rc_compensation.tau_us == 300.
    assert ('tau = 300' if rc else 'disabled') in panel.rc_status.text()
    code = generate_qick_program_code(window._pulse, awg_channels=(1,),
        square_pulse_settings=legacy, square_full_scale_mv={5: 400., 7: 1280.},
        bias_t_compensation_enabled=rc, bias_t_compensation_type='filter', bias_t_filter_tau_us=300.)
    namespace = {}; exec(code, namespace)
    generated = namespace['build_sequence']()
    assert [config.full_scale_mv for config in generated.square_pulse_configs] == [400., 1280.]
    assert all(config.rc_enabled == rc for config in generated.square_pulse_configs)
    assert not rc or all(config.rc_tau_us == 300. for config in generated.square_pulse_configs)


@pytest.mark.parametrize('outcome', ['success', 'fail', 'cancel'])
def test_all_ports_cleanup_independent_of_mute_after_failure(monkeypatch, outcome):
    import qick_qcodes_experiment as module
    calls = []
    cancelled = False
    soc = SimpleNamespace(rfb_set_gen_dc=lambda ch: calls.append(('dc', ch)),
                          stop_square_pulse=lambda ch: calls.append(('stop', ch)))
    def acquire(*args, **kwargs):
        nonlocal cancelled
        calls.append(('acquire',))
        cancelled = outcome == 'cancel'
        if outcome == 'fail': raise RuntimeError('capture failed')
        return 'result'
    def cancel_check():
        if cancelled: raise module.ExperimentCancelled('cancelled')
    monkeypatch.setattr(module, 'configure_rf_readout', lambda *args: {})
    monkeypatch.setattr(module, 'build_qick_program', lambda *args, **kwargs:
                        SimpleNamespace(acquire_fir_ddr=acquire))
    sequence = SimpleNamespace(square_pulse_configs=(SquarePulseConfig(5, mute_on_finish=False),
                               SquarePulseConfig(7)), sweep_point_count=1)
    def run():
        return module._execute_qick_sequence_once(soc, {}, sequence, awg_channels=(1,),
            repetitions_per_sweep=1, rf_specs=(), readout_spec=QickDdrReadoutSpec(0, 'measure', 0, 2),
            cancel_check=cancel_check)
    if outcome == 'success':
        assert run()[1] == 'result'
    else:
        with pytest.raises((RuntimeError, module.ExperimentCancelled)): run()
    assert calls == [('dc', 5), ('dc', 7), ('acquire',)] + (
        [('stop', 7)] if outcome == 'success' else [('stop', 5), ('stop', 7)])


def test_duplicates_rejected_and_missing_saved_channel_not_reassigned(window):
    with pytest.raises(ValueError, match='unique'):
        decode_square_outputs({'outputs': [dict(enabled=True, gen_ch=7)] * 2})
    window._on_qick_configuration_identified(firmware())
    panel = window._square_dds_panel
    panel.load_settings({'outputs': [dict(enabled=True, gen_ch=5), dict(enabled=True, gen_ch=7)]})
    assert [output.channel.value() for output in panel._panels] == [5, 7]
    assert panel.active_channels() == (7,)


def test_live_current_scales_and_sweep_edits_are_per_port(window):
    from test_dac_current import records
    current = records((20000, 20000, 32000))
    current['12'] = dict(current['13'], converter_id='12', channels=[5], current_ua=10000)
    window._on_qick_configuration_identified(replace(multi_firmware(), dac_current_settings=current))
    panel = window._square_dds_panel
    second = panel.add_port()
    for output in panel._panels:
        output.enabled.setChecked(True)
        output.rows['amplitude']['sweep'].setChecked(True)
    axis = second.sweep_specs()[0]
    window._update_sweep_parameter(axis, 15, 25, 20)
    assert panel._panels[0].rows['amplitude']['start'].value() == 10
    assert second.rows['amplitude']['start'].value() == 15
    seq = window._experiment_run_arguments(require_readout=False, require_run_config=False)['sequence']
    assert [config.full_scale_mv for config in seq.square_pulse_configs] == [400., 1280.]
    assert set(seq.dac_current_settings) == {'10', '12', '13'}
    window._remove_sweep_parameter(second.sweep_specs()[0])
    assert panel._panels[0].rows['amplitude']['sweep'].isChecked()
    assert not second.rows['amplitude']['sweep'].isChecked()
    code = generate_qick_program_code(window._pulse, awg_channels=(1,),
        square_pulse_settings=panel.settings_dict(), square_full_scale_mv={5:400., 7:1280.},
        square_current_settings=window._dac_current_state.snapshot((5, 7)))
    ns = {}; exec(code, ns)
    assert set(ns['build_sequence']().dac_current_settings) == {'12', '13'}
    window._dac_current_state.update({**current, '12': dict(current['12'], current_ua=20000)})
    seq = window._experiment_run_arguments(require_readout=False, require_run_config=False)['sequence']
    assert [config.full_scale_mv for config in seq.square_pulse_configs] == [800., 1280.]


@pytest.mark.parametrize('fail', [False, True])
def test_exported_runner_routes_and_stops_each_port(window, fail):
    settings = {'outputs': [dict(enabled=True, gen_ch=5, mute_on_finish=False),
                            dict(enabled=True, gen_ch=7, mute_on_finish=True)]}
    code = generate_qick_program_code(window._pulse, awg_channels=(1,), square_pulse_settings=settings)
    ns = {}; exec(code, ns)
    configs, _ = decode_square_outputs(settings)
    calls = []
    def run(*args, **kwargs):
        calls.append(('run',))
        if fail: raise RuntimeError('failed run')
    program = SimpleNamespace(square_pulse_configs=configs, run_rounds=run)
    ns.update(build_program=lambda _: program, configure_rf_chain=lambda _: None,
              configure_readout_chain=lambda _: None)
    soc = SimpleNamespace(rfb_set_gen_dc=lambda ch: calls.append(('dc', ch)),
                          stop_square_pulse=lambda ch: calls.append(('stop', ch)))
    if fail:
        with pytest.raises(RuntimeError, match='failed run'): ns['run_experiment'](soc, None)
    else:
        ns['run_experiment'](soc, None)
    assert calls == [('dc',5), ('dc',7), ('run',)] + (
        [('stop',5), ('stop',7)] if fail else [('stop',7)])
