"""Wide-step AWG sweeps, signed immediate boundaries and legacy coexistence."""
import pytest
from qick.sim import QickSim
from qick.awg_tuning import TProcV1BehaviorModel
from qick_fine_tune_sweep import FineTuneSequence, _ramp_step, _pack_command_words
from test_qick_fine_tune_sweep import _mock_soccfg, _expected_words
from test_square_awg_exclusion import window


def v2_config(n=2):
    cfg=_mock_soccfg(n)
    for gen in cfg['gens']:
        gen.update(type='axis_awg_tuning_v2',step_width=32,frac=18)
    return cfg


@pytest.mark.parametrize('reverse',[False,True])
def test_full_range_one_clock(reverse):
    cfg=v2_config(1); a,b=(-32768,32764) if not reverse else (32764,-32768)
    samples,step=_ramp_step(cfg['gens'][0],a,b,1,'fast')
    assert samples==16 and abs(step)==1145254707
    assert _pack_command_words(cfg['gens'][0],b,samples,step,2)[3]==step&0xffffffff
    with pytest.raises(ValueError,match='24 bits'):
        _ramp_step(_mock_soccfg(1)['gens'][0],a,b,1,'fast')


@pytest.mark.parametrize('count',[2,20])
@pytest.mark.parametrize('duration_sweep',[False,True])
def test_wide_signed_step_axis_rewind(count,duration_sweep):
    seq=FineTuneSequence(('awg_0','awg_1'))
    seq.add_set('start',(0.,0.),120)
    seq.add_ramp('fast',1)
    seq.add_set('gate',(-.9,.9),180)
    seq.add_ramp('back',1)
    seq.add_set('zero',(0.,0.),250)
    seq.add_amplitude_sweep('gate','awg_0',-.9,.9,count)
    seq.add_amplitude_sweep('gate','awg_1',.9,-.9,count)
    if duration_sweep:
        seq.add_ramp_duration_sweep('fast',1/300,5/300,3)
    program=seq.make_program(v2_config(),awg_channels=(0,1),repetitions_per_sweep=2)
    program.compile()
    model=TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(model)
    model.run(program,max_steps=4000000)
    assert not model.timing_conflicts
    assert [event.word for event in model.output_events]==_expected_words(program)
    steps=[c.step for p in program.compiled_points for commands in p.segment_commands
           for c in commands if c.kind=='ramp']
    assert min(steps)<-(1<<24) and max(steps)>(1<<24)
    for instruction in program.prog_list:
        if instruction['name']=='mathi':
            assert -(1<<30)<=instruction['args'][4]<(1<<30)


def test_mixed_legacy_and_v2_commands_share_tprocessor_page():
    cfg=_mock_soccfg()
    cfg['gens'][1].update(type='axis_awg_tuning_v2',step_width=32,frac=18)
    seq=FineTuneSequence(('awg_0','awg_1'))
    seq.add_set('start',(-.1,-.1),120)
    seq.add_ramp('ramp',24)
    seq.add_set('gate',(.1,.1),120)
    seq.add_amplitude_sweep('gate','awg_0',-.2,.2,5)
    seq.add_amplitude_sweep('gate','awg_1',-.2,.2,5)
    program=seq.make_program(cfg,awg_channels=(0,1),repetitions_per_sweep=2)
    program.compile()
    model=TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(model)
    model.run(program)
    assert [e.word for e in model.output_events]==_expected_words(program)
    assert program._gen_mgrs[0].STEP_WIDTH==24
    assert program._gen_mgrs[1].STEP_WIDTH==32


def test_gui_v2_port_selection_in_awg_and_stability(window):
    from test_square_awg_exclusion import firmware
    from dataclasses import replace
    original=firmware()
    outputs=tuple(replace(port,block_paths=tuple(path.replace('axis_awg_tuning_v1','axis_awg_tuning_v2')
                  for path in port.block_paths)) for port in original.outputs)
    config=replace(original,outputs=outputs)
    window._on_qick_configuration_identified(config)
    # Exercise the actual front-panel selection slots, not just name matching.
    window._multi_ctrl.apply_front_panel_settings({'output_ch':3})
    window._stability_panel.x_axis.apply_front_panel_settings({'output_ch':1})
    window._stability_panel.y_axis.apply_front_panel_settings({'output_ch':3})
    args=window._stability_run_arguments(save=False)
    channels=dict(zip(args['sequence'].output_names,args['awg_channels']))
    assert channels[args['stability_config'].x_axis.output_name]==1
    assert channels[args['stability_config'].y_axis.output_name]==3


@pytest.mark.parametrize('count', [20, 200])
@pytest.mark.parametrize('version', [1, 2])
def test_incremental_voltage_grid_dc_and_ramp_with_independent_dac_scales(count, version):
    import numpy as np
    from fractions import Fraction
    from test_qick_fine_tune_sweep import _independent_awg_soccfg
    cfg = _independent_awg_soccfg(2)
    for gen in cfg['gens']:
        gen.update(rc_precomp_version=1, output_latency_cycles=11)
        if version == 2:
            gen.update(type='axis_awg_tuning_v2', step_width=32, frac=18)
    seq = FineTuneSequence(('x', 'y'))
    seq.set_voltage_scales(800., (800., 400.))
    seq.add_set('gate', (0., 0.), 300)
    seq.add_ramp('return', 30)
    seq.add_set('zero', (0., 0.), 500)
    seq.add_amplitude_sweep('gate', 'x', 5/800, 15/800, count)
    seq.add_amplitude_sweep('gate', 'y', 15/800, 5/800, count)
    seq.set_bias_t_compensation(mode='fixed_time', fixed_duration_cycles=600)
    seq.set_rc_compensation(300.)
    program = seq.make_program(cfg, awg_channels=(0, 1), compile_validation_mode='boundary')
    assert len(program._compile_validation_point_indices) == 4
    assert len(program._requested_points_cache) == 4
    assert not program._runtime_dmem_words
    assert program.summary()['voltage_grid_policy'] == 'constant_quantized_increment'
    axes = (np.linspace(5., 15., count), np.linspace(15., 5., count))
    for output, full_scale in enumerate((800., 400.)):
        def rounded(value, quantum=1):
            units = Fraction(value) / quantum
            return (1 if units >= 0 else -1) * int(abs(units) + Fraction(1, 2)) * quantum
        endpoints = [int(round(v * 32768 / full_scale / 4)) * 4
                     for v in (axes[output][0], axes[output][-1])]
        delta = rounded(Fraction(endpoints[1] - endpoints[0], count-1), 4)
        steps = [int(Fraction(-v * (1 << (18 if version == 2 else 16)), 30*16-1))
                 for v in endpoints]
        step_delta = rounded(Fraction(steps[1]-steps[0], count-1))
        comp_base = rounded(Fraction(-endpoints[0]*315, 600), 4)
        comp_end = rounded(Fraction(-(endpoints[0]+delta*(count-1))*315, 600), 4)
        comp_delta = rounded(Fraction(comp_end-comp_base, count-1), 4)
        for coordinate, requested_mv in enumerate(axes[output]):
            expected_code = endpoints[0] + coordinate*delta
            expected_step = steps[0] + coordinate*step_delta
            expected_comp = comp_base + coordinate*comp_delta
            for other in (0, count//2, count-1):
                point = coordinate * count + other if output == 0 else other * count + coordinate
                assert program._sweep_model_value(program._sweep_models[(0, output, 0, 'target')], point) == expected_code
                assert program._sweep_model_value(program._sweep_models[(1, output, 0, 'step')], point) == expected_step
                assert program._sweep_model_value(program._bias_t_fields[output], point) == expected_comp
            # Constant DAC-code increments can drift; v2 changes ramp precision,
            # not SET-code resolution. Bound and expose, rather than hide, drift.
            assert abs(expected_code * full_scale / 32768 - requested_mv) <= (count+1)*full_scale/16384


def test_200_by_200_voltage_loop_adds_and_rewinds_constant_increments():
    """Execute every loop iteration in the tProcessor instruction model.

    This is a software check; the separate production RTL grid is 20 by 20.
    Expected levels use a once-rounded increment and each DAC scale.
    """
    import numpy as np
    from test_qick_fine_tune_sweep import _independent_awg_soccfg
    cfg = _independent_awg_soccfg(2)
    for gen in cfg['gens']:
        gen.update(type='axis_awg_tuning_v2', step_width=32, frac=18,
                   rc_precomp_version=1, output_latency_cycles=11)
    seq = FineTuneSequence(('x', 'y'))
    seq.set_voltage_scales(800., (800., 400.))
    seq.add_set('gate', (0., 0.), 300)
    seq.add_set('zero', (0., 0.), 500)
    seq.add_amplitude_sweep('gate', 'x', 5/800, 15/800, 200)
    seq.add_amplitude_sweep('gate', 'y', 15/800, 5/800, 200)
    seq.set_bias_t_compensation(mode='fixed_time', fixed_duration_cycles=600)
    seq.set_rc_compensation(300.)
    program = seq.make_program(cfg, awg_channels=(0, 1), repetitions_per_sweep=2,
                               compile_validation_mode='boundary')
    program.compile()
    model = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(model)
    model.run(program, max_steps=12000000)
    assert not model.timing_conflicts
    actual = ([], [])
    for output in range(2):
        words = [int(e.word) for e in model.output_events if (e.word >> 152) & 255 == output]
        resets = [i for i,w in enumerate(words) if w & (1 << 149)]
        assert len(resets)==80001
        for start,stop in zip(resets,resets[1:]):
            word = next(w for w in words[start+1:stop] if (w >> 144) & 3 == 1)
            target = word & 0xffffffff
            actual[output].append(target if target < (1 << 31) else target-(1 << 32))
    x_codes = 204 + np.arange(200)*4
    y_codes = 1228 - np.arange(200)*4
    assert actual[0] == np.repeat(x_codes, 200 * 2).tolist()
    assert actual[1] == np.tile(np.repeat(y_codes, 2), 200).tolist()
    assert not program._runtime_dmem_words
