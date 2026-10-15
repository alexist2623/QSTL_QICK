"""Check executed RF words, Cartesian resets and the 16-bit mode boundary."""
import numpy as np
import pytest
from qick.sim import QickSim  # noqa: F401
from qick.awg_tuning import TProcV1BehaviorModel
from qick_fine_tune_sweep import FineTuneSequence, RfPulseConfig
from test_qick_fine_tune_sweep import _shared_tmux_soccfg


def execute(start, stop=None, count=1, *, outer_count=2, mode='fixed', tmux=0):
    cfg = _shared_tmux_soccfg()
    cfg['gens'][0]['tmux_ch'] = tmux
    seq = FineTuneSequence(('awg_0',)).add_set('gate', .01, 400_000)
    seq.add_amplitude_sweep('gate', 'awg_0', .01, .02, outer_count)
    if stop is not None:
        seq.add_rf_duration_sweep('gate', 0, start/300, stop/300, count,
            segment_length_mode=mode, sequence_fabric_mhz=300.)
    rf = RfPulseConfig(0, 'gate', start, 2000, freq_mhz=190., phase_degrees=45.)
    program = seq.make_program(cfg, awg_channels=(1,), rf_pulse=rf,
        repetitions_per_sweep=2, compile_validation_mode='boundary')
    program.compile()
    model = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(model)
    model.run(program, max_steps=1_000_000)
    assert not model.timing_conflicts
    events = [e for e in model.output_events if (e.word >> 152) & 255 == tmux]
    return program, events


@pytest.mark.parametrize('mode', ['fixed', 'extend_by_rf_duration'])
@pytest.mark.parametrize('descending', [False, True])
def test_20x20_duration_words_and_two_repetitions(mode, descending):
    first, last = (125, 30) if descending else (30, 125)
    program, events = execute(first, last, 20, outer_count=20, mode=mode, tmux=2)
    words = np.array([(e.word >> 128) & 65535 for e in events]).reshape(20,20,2)
    expected = np.linspace(first, last, 20, dtype=int)
    assert np.array_equal(words, np.broadcast_to(expected[None,:,None],words.shape))
    assert all((e.word >> 146) & 1 == 0 for e in events)
    assert all((e.word >> 144) & 3 == 1 for e in events)  # DDS output selection.
    assert all((e.word >> 96) & 0xffffffff == 2000 for e in events)
    assert len(program._runtime_dmem_words) == 20  # One axis, not 400 entries.


@pytest.mark.parametrize('length,periodic', [(3,False),(35,False),(65535,False),(65536,True),(300000,True)])
def test_fixed_pulse_threshold(length, periodic):
    program, events = execute(length)
    assert program._rf_runtime[0]['periodic'] is periodic
    if periodic:
        assert len(events)==8
        for start, stop in zip(events[::2],events[1::2]):
            assert (start.word >> 146) & 1 == 1
            assert (start.word >> 128) & 65535 == 3
            assert (stop.word >> 96) & 0xffffffff == 0
            assert stop.cycle-start.cycle==length
    else:
        assert len(events)==4
        assert all((e.word >> 128) & 65535 == length for e in events)


@pytest.mark.parametrize('first,last,periodic', [
    (65534,65535,False),(65535,65534,False),
    (35,65536,True),(65536,35,True),(65535,65536,True),
])
def test_entire_duration_axis_uses_periodic_if_any_point_is_long(first,last,periodic):
    program, events = execute(first,last,2)
    assert program._rf_runtime[0]['periodic'] is periodic
    lengths = [first,first,last,last]*2
    if periodic:
        assert len(events)==16
        assert [b.cycle-a.cycle for a,b in zip(events[::2],events[1::2])]==lengths
        assert all((e.word >> 146) & 1 == 1 for e in events[::2])
    else:
        assert len(events)==8
        assert [(e.word >> 128) & 65535 for e in events]==lengths


def test_count_one_ignores_unexecuted_stop_coordinate():
    program, events = execute(35,70000,1)
    assert not program._rf_runtime[0]['periodic']
    assert all((e.word >> 128) & 65535 == 35 for e in events)


def test_short_duration_below_supported_minimum_is_rejected():
    with pytest.raises(RuntimeError,match='less than 3'):
        execute(3,2,2)
