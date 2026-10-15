"""GUI spec to RF sample-length conversion; no board connection."""
from dataclasses import asdict, replace

import pytest
import qick.sim
import qick_qcodes_experiment as runtime
from dc_waveform_core import (
    QickRfPulseSpec, QickRfCompositeItemSpec, QickRfDurationParameterSpec,
    QickRfFrequencyParameterSpec,
)
from test_qick_fine_tune_sweep import _shared_tmux_soccfg


def spec(**kwargs):
    values = dict(gen_ch=0, segment_name='hold', delay_us=.1,
                  duration_us=49 / 4800, frequency_mhz=50., gain=1000,
                  att1_db=0., att2_db=0., fine_duration=True)
    values.update(kwargs)
    return QickRfPulseSpec(**values)


@pytest.mark.parametrize('samples', [1, 15, 16, 17, 47, 48, 49, 63, 64,
                                   65, 95, 96, 97, 48001, 480001])
def test_runtime_retains_each_requested_sample(samples):
    cfg = _shared_tmux_soccfg()
    pulse, = runtime.build_runtime_rf_pulses(cfg, (spec(duration_us=samples / 4800),))
    assert pulse.fine_duration is True
    assert pulse.duration_samples == samples
    assert pulse.length_cycles == (samples + 15) // 16
    assert pulse.gain == 1000  # Doubling belongs only to the product command.
    assert pulse.delay_tproc_cycles == 30


def test_runtime_derives_sample_clock_from_metadata():
    cfg = _shared_tmux_soccfg()
    cfg['gens'][0]['f_fabric'] = 250.
    pulse, = runtime.build_runtime_rf_pulses(cfg, (spec(duration_us=49 / 4000),))
    assert pulse.duration_samples == 49


@pytest.mark.parametrize('samples', range(1, 113))
def test_runtime_retains_sample_count_after_editor_decimal_roundtrip(samples):
    duration = round(samples / 4800, 9)
    pulse, = runtime.build_runtime_rf_pulses(_shared_tmux_soccfg(),
                                           (spec(duration_us=duration),))
    assert pulse.duration_samples == samples
    assert pulse.length_cycles == (samples + 15) // 16


def test_nonfine_runtime_keeps_existing_clock_quantization():
    pulse, = runtime.build_runtime_rf_pulses(_shared_tmux_soccfg(),
                                           (spec(fine_duration=False),))
    assert pulse.fine_duration is False
    assert pulse.duration_samples is None
    assert pulse.length_cycles == 4


@pytest.mark.parametrize('gain', [-32768, -16384, 16384, 32767])
def test_runtime_rejects_gain_that_cannot_preserve_amplitude(gain):
    with pytest.raises(ValueError, match='16383'):
        runtime.build_runtime_rf_pulses(_shared_tmux_soccfg(), (spec(gain=gain),))


@pytest.mark.parametrize('kind,samples', [('axis_sg_int4_v1', 4),
                                       ('axis_signal_gen_v6', 8)])
def test_runtime_rejects_unsupported_envelope_geometry(kind, samples):
    cfg = _shared_tmux_soccfg()
    cfg['gens'][0].update(type=kind, samps_per_clk=samples)
    with pytest.raises(ValueError, match='axis_signal_gen_v6'):
        runtime.build_runtime_rf_pulses(cfg, (spec(),))


def test_fine_duration_sweep_keeps_hardware_axis_and_first_exact_sample():
    requested = spec(duration_sweep_enabled=True,
                     duration_sweep_start_us=49 / 4800,
                     duration_sweep_stop_us=80 / 4800, duration_sweep_count=32)
    pulse, = runtime.build_runtime_rf_pulses(_shared_tmux_soccfg(), (requested,))
    assert pulse.duration_samples == 49
    assert not requested.software_sweep_axes
    axis, = requested.sweep_axes
    assert axis.axis_kind == 'rf_duration'
    assert axis.count == 32
    assert asdict(requested)['fine_duration'] is True


def test_custom_pulses_retain_distinct_exact_sample_lengths():
    requested = spec(pulse_mode='composite',
        frequency_parameters=(QickRfFrequencyParameterSpec('f0', 50.),),
        duration_parameters=(QickRfDurationParameterSpec('d0', 49 / 4800),
                             QickRfDurationParameterSpec('d1', 65 / 4800)),
        composite_items=(
            QickRfCompositeItemSpec('pulse', 'a', 49 / 4800, 'f0', 1000,
                                   duration_parameter='d0'),
            QickRfCompositeItemSpec('delay', 'gap', .1),
            QickRfCompositeItemSpec('pulse', 'b', 65 / 4800, 'f0', 1000,
                                   duration_parameter='d1')))
    pulses = runtime.build_runtime_rf_pulses(_shared_tmux_soccfg(), (requested,))
    assert [p.duration_samples for p in pulses] == [49, 65]
    assert all(p.fine_duration for p in pulses)


def test_fine_short_envelope_padding_rejects_overlapping_next_command():
    pulse, = runtime.build_runtime_rf_pulses(_shared_tmux_soccfg(),
                                           (spec(duration_us=1 / 4800),))
    second = replace(pulse, delay_tproc_cycles=pulse.delay_tproc_cycles + 2,
                     pulse_name='next')
    with pytest.raises(ValueError, match='overlaps'):
        runtime._validate_composite_rf_intervals((pulse, second),
                                                 gen_mhz=300., tproc_mhz=300.)
    runtime._validate_composite_rf_intervals(
        (pulse, replace(second, delay_tproc_cycles=pulse.delay_tproc_cycles + 3)),
        gen_mhz=300., tproc_mhz=300.)


def _compile_host_t2_bundle(monkeypatch, *, fine=True):
    """Compile every real host point; replace only acquisition, never the compiler."""
    import numpy as np
    from dc_waveform_core import QickDdrReadoutSpec, QickRfDelayParameterSpec
    from qick_fine_tune_sweep import FineTuneDdrResult, FineTuneSequence

    requested = spec(
        fine_duration=fine, pulse_mode='composite',
        frequency_parameters=(QickRfFrequencyParameterSpec('f0', 50.),),
        duration_parameters=(QickRfDurationParameterSpec(
            'pi', 962 / 4800, True, 962 / 4800, 1026 / 4800, 3),),
        delay_parameters=(QickRfDelayParameterSpec('tau', .1, True, .1, .2, 2),),
        composite_items=(
            QickRfCompositeItemSpec('delay', 'before', .1, delay_parameter='tau'),
            QickRfCompositeItemSpec('pulse', 'pi', 962 / 4800, 'f0', 1000,
                                   duration_parameter='pi'),
            QickRfCompositeItemSpec('delay', 'after', .1, delay_parameter='tau')),
        t2_initial_pi2=True, t2_final_pi2=True, t2_duration_parameter='pi',
        t2_frequency_parameter='f0', t2_gain=1000)
    cfg = _shared_tmux_soccfg()
    cfg['gens'][0]['f_dds'] = 4800.
    sequence = FineTuneSequence(('awg_0',)).add_set('hold', .01, 6000)

    def compile_without_acquisition(_soc, soccfg, concrete_sequence, **kwargs):
        pulses = runtime.build_runtime_rf_pulses(soccfg, kwargs['rf_specs'])
        program = concrete_sequence.make_program(
            soccfg, awg_channels=kwargs['awg_channels'], rf_pulses=pulses,
            repetitions_per_sweep=kwargs['repetitions_per_sweep'])
        program.compile()
        result = FineTuneDdrResult(
            sweep_points=np.empty((1, 0)), iq=np.ones((1, 1, 1, 2), dtype=np.int32),
            reserved_physical_words=128, sweep_axes=(), sweep_shape=())
        return program, result, {'outputs': []}

    monkeypatch.setattr(runtime, '_execute_qick_sequence_once', compile_without_acquisition)
    bundle, result, settings = runtime.execute_qick_sequence(
        object(), cfg, sequence, awg_channels=(1,), repetitions_per_sweep=1,
        rf_specs=(requested,), readout_spec=QickDdrReadoutSpec(0, 'hold', 0., 1))
    assert isinstance(bundle, runtime.SoftwareSweepProgramBundle)
    return requested, bundle, result, settings


def test_fine_host_t2_bundle_records_every_coordinate_and_realized_sample_count(monkeypatch):
    requested, bundle, _result, _settings = _compile_host_t2_bundle(monkeypatch)
    assert [axis.axis_kind for axis in requested.software_sweep_axes] == [
        'rf_delay', 'rf_t2_duration']
    assert len(bundle.programs) == 6
    summary = bundle.summary()
    points = summary['rf_fine_duration_software_points']
    assert len(points) == 6
    for index, (point, program) in enumerate(zip(points, bundle.programs)):
        pi_samples = (962, 994, 1026)[index % 3]
        assert point['software_point_index'] == index
        assert point['software_coordinate'] == bundle.sweep_coordinates[index].tolist()
        assert point['rf_fine_duration'] == program.summary()['rf_fine_duration']
        assert [entry['duration_samples'] for entry in point['rf_fine_duration']] == [
            (pi_samples // 2,), (pi_samples,), (pi_samples // 2,)]
        assert [entry['actual_duration_us'][0] for entry in point['rf_fine_duration']] == pytest.approx(
            [pi_samples / 9600, pi_samples / 4800, pi_samples / 9600])
    assert summary['rf_fine_duration'] == points[-1]['rf_fine_duration']
    assert summary['rf_fine_duration_scope'] == {
        'scope': 'last_software_point', 'software_point_index': 5,
        'software_coordinate': bundle.sweep_coordinates[-1].tolist(),
        'all_points_key': 'rf_fine_duration_software_points'}


def test_fine_host_t2_sample_metadata_survives_qcodes_json_storage(monkeypatch, tmp_path):
    import json

    requested, bundle, result, settings = _compile_host_t2_bundle(monkeypatch)
    summary = bundle.summary()
    dataset, rows = runtime.store_qick_result(
        result, run_config=runtime.QcodesRunConfig(str(tmp_path / 'fine_host.db')),
        connection_config=runtime.QickConnectionConfig('not-connected', 8888, 'qick'),
        program_summary=summary, gui_settings={'rf_outputs': [asdict(requested)]},
        rf_settings=settings)
    try:
        saved = json.loads(dataset.get_metadata('qick_experiment_json'))
        assert rows == 6
        assert saved['program_summary'] == json.loads(runtime._json_text(summary))
        points = saved['program_summary']['rf_fine_duration_software_points']
        assert [point['rf_fine_duration'][0]['duration_samples'][0] for point in points] == [
            481, 497, 513, 481, 497, 513]
        assert [point['software_coordinate'] for point in points] == bundle.sweep_coordinates.tolist()
        assert saved['program_summary']['rf_fine_duration_scope']['software_point_index'] == 5
        assert saved['gui_settings']['rf_outputs'][0]['fine_duration'] is True
    finally:
        dataset.conn.close()


def test_coarse_host_bundle_keeps_legacy_summary_exactly(monkeypatch):
    _requested, bundle, _result, _settings = _compile_host_t2_bundle(monkeypatch, fine=False)
    expected = dict(bundle.programs[-1].summary())
    expected.update({
        'software_sweep_program_count': len(bundle.programs),
        'software_sweep_axes': [asdict(axis) for axis in bundle.sweep_axes],
        'software_sweep_coordinates': bundle.sweep_coordinates.tolist(),
        'software_sweep_execution': 'one tProcessor compile/acquisition per RF software point'})
    assert bundle.summary() == expected
    assert not any(key.startswith('rf_fine_duration') for key in bundle.summary())
