"""Verify readout spillover against executed tProcessor commands."""
import pytest
from qick.sim import QickSim  # noqa: F401
from qick.awg_tuning import TProcV1BehaviorModel
from qick_fine_tune_sweep import FineTuneSequence, DdrFirReadoutConfig
from test_qick_fine_tune_sweep import _fir_soccfg, _command_word
from test_rc_precompensation import upgraded


@pytest.mark.parametrize('dc,rc', [(False, False), (True, False), (False, True), (True, True)])
@pytest.mark.parametrize('last_segment', [False, True])
def test_capture_crosses_segments_without_stretching_the_waveform(dc, rc, last_segment):
    seq = FineTuneSequence(('awg_0',))
    for name, voltage in [('a', .01), ('b', .02), ('c', .03)]:
        seq.add_set(name, voltage, 3000)  # Each requested segment is 10 us.
    if dc:
        seq.set_bias_t_compensation(.1)
    if rc:
        seq.set_rc_compensation(1000.)
    ddr = DdrFirReadoutConfig(0, 2 if last_segment else 1,
                            'c' if last_segment else 'a', margin_input_samples=0)
    prog = seq.make_program(upgraded(_fir_soccfg(fir_rate_profile='50_ksps', ddr_trigger_port=2)),
                            awg_channels=(0,), repetitions_per_sweep=2,
                            recovery_tproc_cycles=0, ddr_readout=ddr)
    model = TProcV1BehaviorModel(strict=True)
    prog.load_runtime_dmem_into_model(model)
    model.run(prog)
    assert not model.timing_conflicts
    assert all(b-a == 3000 for a,b in zip(prog.timing['segment_starts'], prog.timing['segment_ends']))
    capture_start = prog.aux_timing['ddr_trigger_time']
    capture_end = prog.aux_timing['ddr_capture_end']
    assert capture_end - capture_start == (12000 if last_segment else 6000)
    assert prog.timing['point_end'] == max(prog.timing['segment_ends'][-1], capture_end)
    events = [e for e in model.output_events if e.tproc_ch == 0]
    words = [_command_word(commands[0]) for commands in prog.compiled_points[0].segment_commands]
    starts = [e for e in events if e.word == words[0]]
    assert len(starts) == 2
    for word, offset in zip(words, (0,3000,6000)):
        assert [e.cycle-starts[i].cycle for i,e in enumerate(e for e in events if e.word == word)] == [offset,offset]
    # The next repetition never starts before the whole acquisition window ends.
    assert starts[1].cycle-starts[0].cycle >= capture_end-prog.timing['segment_starts'][0]
    zeros = [e for e in events if e.word & 0xffffffff == 0 and not e.word & (1 << 149)]
    if dc or rc:
        assert any(e.cycle == starts[0].cycle + 9000 for e in zeros)
        if dc:
            negatives = [e for e in events if e.word & (1 << 31)]
            assert negatives[0].cycle-starts[0].cycle >= capture_end-prog.timing['segment_starts'][0]
    else:
        assert not zeros  # The last requested SET remains until the next SET.
