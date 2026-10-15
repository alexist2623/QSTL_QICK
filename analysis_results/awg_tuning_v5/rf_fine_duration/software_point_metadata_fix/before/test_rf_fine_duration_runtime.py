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
