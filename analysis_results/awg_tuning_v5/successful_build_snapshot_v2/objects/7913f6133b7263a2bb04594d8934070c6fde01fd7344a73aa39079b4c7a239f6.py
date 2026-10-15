"""Real compiler/GUI regressions for independent FPGA RC and DC area pulses."""
import itertools
import pytest
from qick.sim import QickSim  # noqa: F401
from qick.awg_tuning import TProcV1BehaviorModel
from qick.precompensation import rc_coefficient, square_rc_increment
from qick.square_pulse import square_words
from test_qick_fine_tune_sweep import _mock_soccfg, _independent_awg_soccfg
from test_qick_square_dds import configuration
from qick_fine_tune_sweep import FineTuneSequence
from qick_square_dds import SquarePulseConfig, SquarePulseSweep, attach_square_settings


def upgraded(cfg):
    for gen in cfg['gens']:
        gen.update(rc_precomp_version=1, output_latency_cycles=11)
        if gen['type'] == 'axis_square_pulse_v1':
            gen['command_latency_cycles'] = 15
    return cfg


@pytest.mark.parametrize('dc,rc', list(itertools.product((False, True), repeat=2)))
def test_independent_modes_clear_rc_after_each_repeat(dc, rc):
    cfg = upgraded(_independent_awg_soccfg(2))
    seq = FineTuneSequence(('x', 'y')).add_set('hold', (.02, -.01), 300)
    seq.set_bias_t_compensation(.1, enabled=dc)
    seq.set_rc_compensation(1000., enabled=rc)
    seq.set_amplitude_sweep('hold', 'x', -.02, .02, 3)
    prog = seq.make_program(cfg, awg_channels=(0, 1), repetitions_per_sweep=2)
    prog.compile()
    model = TProcV1BehaviorModel(strict=True)
    prog.load_runtime_dmem_into_model(model)
    model.run(prog)
    configs = [e for e in model.output_events if e.word & (1 << 149)]
    assert len(configs) == 2 * (1 + (6 if rc else 0))
    for event in configs:
        assert bool(event.word & (1 << 146)) == rc
        assert event.word & (1 << 147)
        assert event.word & 0xffffffff == (rc_coefficient(1000., 4800.) if rc else 0)
    assert not model.timing_conflicts
    assert len(prog.compiled_points[0].segment_commands[0]) == 2
    assert prog.timing['segment_starts'][0] == 11
    assert prog.timing['command_times'][0, 0] == 0
    assert (seq.bias_t_compensation is not None) == dc
    assert (seq.rc_compensation is not None) == rc
    for port in (0, 1):
        events = [e for e in model.output_events if e.tproc_ch == port]
        resets = [i for i, e in enumerate(events) if e.word & (1 << 149)]
        for index in resets[1:]:
            previous = events[index - 1]
            assert (previous.word >> 144) & 3 == 1
            assert previous.word & 0xffffffff == 0
            assert events[index].cycle > previous.cycle


def test_old_firmware_rejects_rc_but_runs_dc():
    seq = FineTuneSequence(('x',)).add_set('hold', .1, 300)
    seq.set_bias_t_compensation(.1)
    seq.make_program(_mock_soccfg(1), awg_channels=(0,)).compile()
    seq.set_rc_compensation(100.)
    with pytest.raises(ValueError, match='does not support FPGA RC'):
        seq.make_program(_mock_soccfg(1), awg_channels=(0,))


@pytest.mark.parametrize('dc_mode', [None, 'fixed_time', 'fixed_voltage'])
def test_repeat_reset_preserves_duration_and_amplitude_sweeps(dc_mode):
    cfg = upgraded(_independent_awg_soccfg(1))
    seq = FineTuneSequence(('x',)).add_set('start', -.02, 300)
    seq.add_ramp('ramp', 30).add_set('end', .03, 300)
    seq.add_ramp_duration_sweep('ramp', start_us=.1, stop_us=.2, count=3,
                               sequence_fabric_mhz=300.)
    seq.add_amplitude_sweep('end', 'x', .01, .03, 4)
    seq.set_rc_compensation(10.)
    if dc_mode is not None:
        seq.set_bias_t_compensation(.1, mode=dc_mode,
            fixed_duration_cycles=300 if dc_mode == 'fixed_time' else None)
    runs = []
    for mode in ('full', 'boundary'):
        prog = seq.make_program(cfg, awg_channels=(0,), repetitions_per_sweep=2,
                                recovery_tproc_cycles=0, compile_validation_mode=mode)
        prog.compile()
        model = TProcV1BehaviorModel(strict=True)
        prog.load_runtime_dmem_into_model(model); model.run(prog)
        assert not model.timing_conflicts
        events = model.output_events
        resets = [i for i,e in enumerate(events) if e.word & (1 << 149)]
        assert len(resets) == 25
        for i in resets[1:]:
            assert (events[i-1].word >> 144) & 3 == 1
            assert events[i-1].word & 0xffffffff == 0
            assert events[i].cycle > events[i-1].cycle
        assert prog.summary()['rc_reset_each_repeat'] is True
        # With no SquarePulse or marker, the host still must not see the final
        # acquisition count before the last scheduled reset has reached the IP.
        instructions = prog.prog_list
        wait_index = max(i for i,v in enumerate(instructions) if v['name'] == 'waiti')
        counter_index = max(i for i,v in enumerate(instructions)
                            if v['name'] == 'memwi' and v['args'][2] == prog.COUNTER_ADDR)
        assert wait_index < counter_index
        runs.append([(e.cycle, e.word) for e in events])
    assert runs[0] == runs[1]


def test_rc_repeat_reset_routes_shared_tmux_without_collisions():
    cfg = upgraded(_mock_soccfg(2))
    seq = FineTuneSequence(('x', 'y')).add_set('hold', (.01, -.02), 300)
    seq.set_rc_compensation(10.)
    seq.set_amplitude_sweep('hold', 'x', .01, .02, 3)
    prog = seq.make_program(cfg, awg_channels=(0, 1), repetitions_per_sweep=2,
                            recovery_tproc_cycles=0)
    prog.compile()
    model = TProcV1BehaviorModel(strict=True)
    prog.load_runtime_dmem_into_model(model); model.run(prog)
    assert not model.timing_conflicts
    for tmux in (0, 1):
        events = [e for e in model.output_events if e.word >> 152 == tmux]
        resets = [i for i,e in enumerate(events) if e.word & (1 << 149)]
        assert len(resets) == 7
        for i in resets[1:]:
            assert events[i-1].word & 0xffffffff == 0
            assert events[i].cycle > events[i-1].cycle


def test_ddr_trigger_anchor_includes_bypass_or_rc_output_latency():
    from test_qick_fine_tune_sweep import _fir_soccfg
    from qick_fine_tune_sweep import DdrFirReadoutConfig
    seq=FineTuneSequence(('x',)).add_set('hold', .1, 30000)
    legacy=seq.make_program(_fir_soccfg(fir_rate_profile='50_ksps'),awg_channels=(0,),
        ddr_readout=DdrFirReadoutConfig(0,2,'hold',margin_input_samples=0))
    for enabled in (False, True):
        seq.set_rc_compensation(1000.,enabled=enabled)
        prog=seq.make_program(upgraded(_fir_soccfg(fir_rate_profile='50_ksps')),awg_channels=(0,),
            ddr_readout=DdrFirReadoutConfig(0,2,'hold',margin_input_samples=0))
        assert prog.aux_timing['ddr_trigger_time']==legacy.aux_timing['ddr_trigger_time']+11
        assert prog.timing['command_times']==legacy.timing['command_times']


def test_rc_does_not_rewrite_ramps_or_scale_program_memory_with_sweep_count():
    sizes=[]
    # Constant per-axis increments do not allocate per-point voltage tables.
    for count in (201, 1001):
        seq=FineTuneSequence(('x',)).add_set('a', -.02, 300)
        seq.add_ramp('ramp', 50).add_set('b', .02, 300)
        seq.set_amplitude_sweep('b','x', .01,.03,count)
        cfg=upgraded(_mock_soccfg(1))
        plain=seq.make_program(cfg,awg_channels=(0,))
        seq.set_rc_compensation(1_000_000.)
        compensated=seq.make_program(cfg,awg_channels=(0,))
        assert compensated.compiled_points == plain.compiled_points
        sizes.append(len(compensated.prog_list))
        assert len(compensated.prog_list)<4096
    assert abs(sizes[0]-sizes[1])<=4
    seq.set_amplitude_sweep('b', 'x', .01, .03, 5001)
    large = seq.make_program(cfg, awg_channels=(0,), compile_validation_mode='boundary')
    assert not large._runtime_dmem_words
    assert large.summary()['voltage_grid_policy'] == 'constant_quantized_increment'


def test_square_rc_amplitude_and_frequency_cartesian_words():
    cfg=upgraded(configuration())
    config=SquarePulseConfig(1, rc_enabled=True, rc_tau_us=10., mute_on_finish=False)
    axes=(SquarePulseSweep('amplitude', 0, 600, 10, 1),
          SquarePulseSweep('frequency', .002, .04, 10, 1))
    seq=FineTuneSequence(('x',)).add_set('hold', 0., 300)
    attach_square_settings(seq, config, axes)
    prog=seq.make_program(cfg,awg_channels=(0,),repetitions_per_sweep=2)
    prog.compile()
    model=TProcV1BehaviorModel(strict=True)
    prog.load_runtime_dmem_into_model(model);model.run(prog)
    actual=[e.word for e in model.output_events if e.word >> 152 == 2]
    expected=[]
    for amplitude,frequency in itertools.product(*(a.points for a in axes)):
        gain=config.word('amplitude',amplitude,cfg['gens'][1])
        words=square_words(config.word('frequency',frequency,cfg['gens'][1]),0,gain,
            tmux_ch=2,rc_enable=True,rc_increment=square_rc_increment(gain,10.,4800.))
        expected.extend([sum(w<<(32*i) for i,w in enumerate(words))]*2)
    assert actual==expected
    assert not any(w & (1<<131) for w in actual)
    assert not model.timing_conflicts


def test_awg_and_stability_checkbox_roundtrip_and_export(tmp_path):
    from test_dc_waveform_gui_rf import _application
    import DCWaveform_Generator as gui
    from dc_waveform_core import generate_qick_program_code
    app=_application(); window=gui.MainWindow()
    for panel in (window._experiment_panel, window._stability_panel):
        panel.bias_t_type.dc_checkbox.setChecked(True)
        panel.bias_t_type.rc_checkbox.setChecked(True)
        panel.bias_t_filter_tau_us.setValue(100000.)
        assert panel.bias_t_type.currentData()=='dc_rc'
        assert panel.bias_t_mode.isEnabled()
        assert panel.bias_t_filter_tau_us.isEnabled()
    path=window._save_settings_json(tmp_path/'dc_rc')
    restored=gui.MainWindow();restored._load_settings_json(path)
    for panel in (restored._experiment_panel,restored._stability_panel):
        assert panel.bias_t_type.dc_checkbox.isChecked()
        assert panel.bias_t_type.rc_checkbox.isChecked()
        assert panel.bias_t_filter_tau_us.value()==100000.
        panel.bias_t_type.dc_checkbox.setChecked(False)
        assert panel.bias_t_type.rc_checkbox.isChecked()
        assert panel.bias_t_type.currentData()=='filter'
    code=generate_qick_program_code(window._pulse,awg_channels=(0,),
        bias_t_compensation_enabled=True,bias_t_compensation_type='dc_rc',bias_t_filter_tau_us=100000.)
    ns={};exec(code,ns);seq=ns['build_sequence']()
    assert seq.bias_t_compensation is not None
    assert seq.rc_compensation.tau_us==100000.
    window.close();restored.close();app.processEvents()
