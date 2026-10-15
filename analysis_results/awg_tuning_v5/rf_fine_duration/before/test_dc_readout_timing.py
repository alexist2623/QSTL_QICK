"""FIR/DC ordering verified against executed tProcessor output commands."""
import os
import numpy as np
import pytest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from qick.sim import QickSim  # desktop hardware stubs
from qick.awg_tuning import TProcV1BehaviorModel
from qick_fine_tune_sweep import FineTuneSequence, DdrFirReadoutConfig, RfPulseConfig
from test_qick_fine_tune_sweep import _fir_soccfg, _independent_awg_soccfg, _shared_tmux_soccfg
from test_iq64_format import iq64_config


def fixture(policy, mode='fixed_time', rc=True, samples=12, sweep='none', zero=False,
            profile='1_msps', marker=False):
    cfg = _fir_soccfg(fir_rate_profile='50_ksps', ddr_trigger_port=7)
    # Same continuous-filter DDR scheduling as the 1 MSPS FPGA-delay firmware.
    cfg['ddr4_buf'].update(iq64_config()['ddr4_buf'], fir_output_fs_mhz=1.)
    if profile != '1_msps':
        cfg['ddr4_buf'] = _fir_soccfg(fir_rate_profile=profile, ddr_trigger_port=7)['ddr4_buf']
    cfg['gens'] = _independent_awg_soccfg(2)['gens']
    for gen in cfg['gens']:
        gen.update(type='axis_awg_tuning_v2', frac=18, step_width=32,
                   rc_precomp_version=1, output_latency_cycles=11)
    cfg['readouts'][0]['tproc_ctrl'] = 2
    cfg['gens'].append(dict(_shared_tmux_soccfg()['gens'][0], tproc_ch=3))
    seq = FineTuneSequence(('a', 'b')).add_set('lead', (0., 0.), 600)
    seq.add_ramp('ramp', 300).add_set('measure', (0., 0.) if zero else (.01, -.02), 1200)
    seq.set_bias_t_compensation(mode=mode, fixed_duration_cycles=600, amplitude=.04)
    if rc:
        seq.set_rc_compensation(300.)
    if marker:
        from qick_square_dds import OutputTriggerConfig
        cfg['tprocs'][0]['output_pins'] = [('output', 7, 6, 'SPARE1_1V8')]
        seq.output_trigger_config = OutputTriggerConfig(enabled=True, pin=0, edge='both', width_us=80.)
    rf = None
    if sweep != 'none':
        seq.add_amplitude_sweep('measure', 'a', .01, .02, 4)
        if sweep == 'voltage':
            seq.add_amplitude_sweep('measure', 'b', -.02, -.01, 3)
        elif sweep == 'ramp':
            seq.add_ramp_duration_sweep('ramp', start_us=1., stop_us=2., count=3, sequence_fabric_mhz=300.)
        elif sweep == 'hold':
            seq.add_hold_duration_sweep('measure', start_us=4., stop_us=6., count=3, sequence_fabric_mhz=300.)
        elif sweep == 'rf':
            seq.add_rf_duration_sweep('measure', 2, 1., 2., 3,
                                     segment_length_mode='extend_by_rf_duration', sequence_fabric_mhz=300.)
            rf = RfPulseConfig(2, 'measure', 300, 1000, freq_mhz=190.)
    ddr = DdrFirReadoutConfig(0, samples, 'measure', margin_input_samples=0,
                             dc_compensation_timing=policy)
    return cfg, seq, ddr, rf


def execute(policy, **kwargs):
    cfg, seq, ddr, rf = fixture(policy, **kwargs)
    p = seq.make_program(cfg, awg_channels=(0, 1), ddr_readout=ddr, rf_pulse=rf,
                         repetitions_per_sweep=2, compile_validation_mode='boundary')
    p.compile()
    m = TProcV1BehaviorModel(strict=True)
    p.load_runtime_dmem_into_model(m)
    m.run(p, max_steps=2_000_000)
    assert not m.timing_conflicts
    return p, m


def signed(word):
    v = word & 0xffffffff
    return v - 2**32 if v >= 2**31 else v


@pytest.mark.parametrize('policy', ['after_readout', 'overlap_readout'])
@pytest.mark.parametrize('mode', ['fixed_time', 'fixed_voltage'])
@pytest.mark.parametrize('rc', [False, True])
@pytest.mark.parametrize('samples', [1, 4, 6, 12])
def test_capture_boundaries_and_repeats(policy, mode, rc, samples):
    p, m = execute(policy, mode=mode, rc=rc, samples=samples)
    readouts = [e for e in m.output_events if e.tproc_ch == 2]
    assert len(readouts) == 2
    capture_offset = p.aux_timing['ddr_capture_end']
    for index, ro in enumerate(readouts):
        limit = readouts[index+1].cycle if index+1 < len(readouts) else float('inf')
        capture_end = ro.cycle + capture_offset
        wave_end = ro.cycle + p.timing['segment_ends'][-1]
        for ch in (0, 1):
            ev = [e for e in m.output_events if e.tproc_ch == ch and ro.cycle <= e.cycle < limit]
            ordinary = [e for e in ev if not e.word & (1 << 149)]
            comps = [e for e in ordinary if (signed(e.word) < 0 if ch == 0 else signed(e.word) > 0)]
            assert len(comps) == 1
            comp = comps[0]
            preview = p.fir_dc_timing_preview(0)['dc_outputs'][ch]
            assert preview['command_start_us']*p.tproc_mhz == pytest.approx(comp.cycle-ro.cycle)
            assert comp.cycle >= wave_end
            if policy == 'after_readout':
                assert comp.cycle >= capture_end
            else:
                expected = wave_end + max(p._channel_slots.values()) + p.bias_t_simultaneous_start_lead_cycles
                expected += p.sequence.bias_t_compensation.inter_output_gap_cycles
                assert comp.cycle == expected
                if samples >= 6:
                    assert comp.cycle < capture_end
            stops = [e for e in ordinary if e.cycle > comp.cycle and signed(e.word) == 0]
            assert stops
            resets = [e for e in ev if e.word & (1 << 149)]
            if rc:
                assert resets and resets[-1].cycle >= max(stops[0].cycle, capture_end)
        if index+1 < len(readouts):
            assert limit > capture_end


@pytest.mark.parametrize('mode', ['fixed_time', 'fixed_voltage'])
@pytest.mark.parametrize('sweep', ['voltage', 'ramp', 'hold', 'rf'])
def test_swept_end_and_capture_registers_follow_both_axes(mode, sweep):
    p, m = execute('overlap_readout', mode=mode, sweep=sweep)
    readouts = [e for e in m.output_events if e.tproc_ch == 2]
    assert len(readouts) == 24
    starts = []
    for shot, ro in enumerate(readouts):
        point = shot // 2
        end = readouts[shot+1].cycle if shot+1 < len(readouts) else float('inf')
        wave_duration = sum(p.sequence.segment_duration_cycles_at(point, i)
                            for i in range(len(p.sequence.segments)))
        wave_end = ro.cycle + p.timing['segment_starts'][0] + wave_duration + 1  # RAMP guard
        # Readout commands are at reference zero in continuous FIR mode.
        capture = p._capture_compensation_models[-1]
        capture_end = ro.cycle + p._sweep_model_value(capture, point)
        comps = [e for e in m.output_events if e.tproc_ch == 0 and ro.cycle <= e.cycle < end
                 and not e.word & (1 << 149) and signed(e.word) < 0]
        assert len(comps) == 1
        expected = wave_end + max(p._channel_slots.values()) + p.bias_t_simultaneous_start_lead_cycles
        expected += p.sequence.bias_t_compensation.inter_output_gap_cycles
        assert comps[0].cycle == expected
        assert comps[0].cycle < capture_end < end
        starts.append(comps[0].cycle - ro.cycle)
    assert np.array_equal(np.array(starts)[::2], np.array(starts)[1::2])
    assert m.dmem[p.COUNTER_ADDR] == 24


@pytest.mark.parametrize('mode', ['fixed_time', 'fixed_voltage'])
def test_zero_area_still_waits_for_capture(mode):
    p, m = execute('overlap_readout', mode=mode, zero=True)
    readouts = [e for e in m.output_events if e.tproc_ch == 2]
    assert readouts[1].cycle-readouts[0].cycle >= p.aux_timing['ddr_capture_end']
    assert all(signed(e.word) == 0 for e in m.output_events
               if e.tproc_ch in (0, 1) and not e.word & (1 << 149))


def test_default_and_invalid_policy():
    assert DdrFirReadoutConfig(0, 1, 'pulse').dc_compensation_timing == 'after_readout'
    with pytest.raises(ValueError, match='dc_compensation_timing'):
        DdrFirReadoutConfig(0, 1, 'pulse', dc_compensation_timing='unknown')


@pytest.mark.parametrize('profile', ['50_ksps', '1_msps'])
@pytest.mark.parametrize('policy', ['after_readout', 'overlap_readout'])
def test_profiles_and_long_shared_marker(profile, policy):
    p, m = execute(policy, profile=profile, marker=True, sweep='hold')
    assert m.dmem[p.COUNTER_ADDR] == 24
    for point in range(p.sequence.sweep_point_count):
        preview = p.fir_dc_timing_preview(point)
        assert preview['stored_samples'] == 12
        assert preview['dc_outputs'][0]['command_start_us'] > 80


@pytest.mark.parametrize('policy', ['after_readout', 'overlap_readout'])
def test_gui_serialization_runtime_export_and_timing_preview(policy):
    from PyQt5 import QtWidgets
    import DCWaveform_Generator as gui
    from dc_waveform_core import PulseSequence, generate_qick_program_code
    from qick_qcodes_experiment import build_runtime_ddr_readout
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    pulse = PulseSequence(100., initial_duration_ns=6000.)
    panel = gui.RfReadoutPanel(pulse, time_unit='us')
    panel.setChecked(True)
    panel.dc_compensation_timing.setCurrentIndex(panel.dc_compensation_timing.findData(policy))
    settings = panel.settings_dict()
    assert settings['dc_compensation_timing'] == policy
    restored = gui.RfReadoutPanel(pulse, time_unit='us')
    restored.load_settings(settings)
    assert restored.configured_spec().dc_compensation_timing == policy
    cfg, _, _, _ = fixture(policy)
    spec = restored.configured_spec()
    assert build_runtime_ddr_readout(cfg, spec).dc_compensation_timing == policy
    code = generate_qick_program_code([pulse, pulse], awg_channels=(0,1),
                                      ddr_readout_spec=spec, fabric_mhz=300., tproc_mhz=300.)
    namespace = {}
    exec(code, namespace)
    exported = namespace['build_program'](cfg)
    assert exported.ddr_readout_config.dc_compensation_timing == policy
    p, _ = execute(policy, sweep='hold')
    assert p.summary()['dc_compensation_timing'] == policy
    dialog = gui.QickAssemblyDialog({'assembly':p.asm(), 'program':p})
    dialog.timing_point.setValue(11)
    assert 'DDR storage' in dialog.timing_text.toPlainText()
    assert p.fir_dc_timing_preview(11)['point_index'] == 11
    old_settings = dict(settings)
    old_settings.pop('dc_compensation_timing')
    restored.load_settings(old_settings)
    assert restored.configured_spec().dc_compensation_timing == 'after_readout'
    for widget in (dialog, restored, panel):
        widget.close()
    app.processEvents()


@pytest.mark.parametrize('delay_fields', [dict(fpga_trigger_delay_samples=9000),
                                        dict(fpga_trigger_delay_us=35.)])
def test_export_preserves_custom_firmware_capture_delay(delay_fields):
    from dc_waveform_core import PulseSequence, QickDdrReadoutSpec, generate_qick_program_code
    from qick_qcodes_experiment import build_runtime_ddr_readout
    pulse = PulseSequence(10., initial_duration_ns=6000.)
    spec = QickDdrReadoutSpec(0, 'set_0', 0., 12, dc_compensation_timing='overlap_readout', **delay_fields)
    cfg, _, _, _ = fixture('overlap_readout')
    code = generate_qick_program_code([pulse,pulse], awg_channels=(0,1), ddr_readout_spec=spec,
                                      fabric_mhz=300., tproc_mhz=300.)
    ns = {}
    exec(code, ns)
    assert ns['build_ddr_readout'](cfg) == build_runtime_ddr_readout(cfg, spec)


def test_option_has_no_effect_without_dc_compensation():
    programs = []
    for policy in ('after_readout', 'overlap_readout'):
        cfg, seq, ddr, _ = fixture(policy)
        seq.bias_t_compensation = None
        p = seq.make_program(cfg, awg_channels=(0,1), ddr_readout=ddr)
        programs.append(p.compile())
        assert p.fir_dc_timing_preview()['dc_outputs'] == []
    assert programs[0] == programs[1]


def test_main_window_settings_file_roundtrip(tmp_path):
    from PyQt5 import QtWidgets
    import DCWaveform_Generator as gui
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window=gui.MainWindow()
    panel=window._rf_readout_panel
    panel.dc_compensation_timing.setCurrentIndex(1)
    path=window._save_settings_json(tmp_path/'fir_dc.json')
    panel.dc_compensation_timing.setCurrentIndex(0)
    window._load_settings_json(path)
    assert panel.configured_spec().dc_compensation_timing=='overlap_readout'
    assert window._settings_to_dict()['rf_readout']['dc_compensation_timing']=='overlap_readout'
    window.close()
    window.deleteLater()
    from PyQt5 import QtCore
    app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    app.processEvents()
