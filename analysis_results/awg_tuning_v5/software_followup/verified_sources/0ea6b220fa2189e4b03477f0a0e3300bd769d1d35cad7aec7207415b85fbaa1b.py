"""Real tProcessor execution of preloaded sample-width RF hardware sweeps."""
from dataclasses import replace

import numpy as np
import pytest
import qick.sim  # noqa: F401
from qick.awg_tuning import TProcV1BehaviorModel
from qick_fine_tune_sweep import FineTuneSequence, RfPulseConfig
from qick_rf_fine_duration import ending_patterns, plan_duration, samples_from_us
from test_qick_fine_tune_sweep import _shared_tmux_soccfg


def execute(first, last=None, count=1, *, outer=1, gain=2000, fine=True,
            freq_sweep=False, pulses=None, reps=2, segment_mode='fixed'):
    cfg = _shared_tmux_soccfg()
    cfg['gens'][0]['f_dds'] = 4800.
    seq = FineTuneSequence(('awg_0',)).add_set('gate', .01, 400_000)
    if outer > 1:
        seq.add_amplitude_sweep('gate', 'awg_0', .01, .02, outer)
    if last is not None:
        seq.add_rf_duration_sweep('gate', 0, first/4800., last/4800., count,
                                 segment_length_mode=segment_mode, sequence_fabric_mhz=300.)
    if freq_sweep:
        seq.add_rf_frequency_sweep('gate', 0, 10., 20., 2)
    rf = RfPulseConfig(0, 'gate', max(3, (first+15)//16), gain,
                      freq_mhz=10., phase_degrees=45., delay_tproc_cycles=30,
                      fine_duration=fine, duration_samples=first if fine else None)
    program = seq.make_program(cfg, awg_channels=(1,), rf_pulses=pulses or (rf,),
                               repetitions_per_sweep=reps, compile_validation_mode='boundary')
    program.compile()
    model = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(model)
    model.run(program, max_steps=1_000_000)
    assert not model.timing_conflicts
    events = [e for e in model.output_events if (e.word >> 152) & 255 == 0]
    return program, events


def active_samples(program, events):
    memory = np.zeros(16384, dtype=np.int16)
    for envelope in program.envelopes[0]['envs'].values():
        start = envelope['addr']
        memory[start:start+len(envelope['data'])] = envelope['data'][:, 0]
    traces = []
    for event in events:
        mode = (event.word >> 128) & 0xffffffff
        length = mode & 65535
        selection = (mode >> 16) & 3
        if selection == 1:
            data = np.full(length*16, 32766, dtype=np.int16)
        else:
            address = ((event.word >> 64) & 0xffffffff)*16
            data = memory[address:address+length*16]
        traces.append((event.cycle, np.count_nonzero(data), selection, (event.word >> 96) & 65535))
    return traces


@pytest.mark.parametrize('samples', list(range(1, 96)) + [96, 97, 111, 112, 48000, 48001, 480015])
def test_fixed_all_short_lengths_and_long_tail(samples):
    program, events = execute(samples, reps=1)
    plan = plan_duration(samples)
    actual = active_samples(program, events)
    assert sum(item[1] for item in actual) == samples
    assert len(actual) == 1 + plan.long
    assert len(program.envelopes[0]['envs']) == 16
    assert sum(len(v['data']) for v in program.envelopes[0]['envs'].values()) == 2048
    if plan.long:
        assert actual[1][0]-actual[0][0] == plan.tail_offset
        assert [item[3] for item in actual] == [2000, 4000]
    else:
        assert actual[0][3] == 4000


@pytest.mark.parametrize('first,last,count', [(48000,48015,16), (95,110,16), (110,95,16), (1,96,96)])
def test_hardware_sweep_pattern_selection_and_outer_reset(first, last, count):
    program, events = execute(first, last, count, outer=2)
    decoded = active_samples(program, events)
    expected = list(np.rint(np.linspace(first,last,count)).astype(int))
    cursor = 0
    for samples in expected*2:
        for _ in range(2):
            commands = 1+plan_duration(samples).long
            assert sum(item[1] for item in decoded[cursor:cursor+commands]) == samples
            cursor += commands
    assert cursor == len(decoded)
    table = [t for t in program._rf_point_tables if t.get('fine_row')]
    assert len(table)==1 and len(table[0]['values'])==count*6
    assert len(program.envelopes[0]['envs'])==16


def test_no_pmem_unrolling_and_frequency_cross_axis():
    small, _ = execute(48000,48015,16, freq_sweep=True)
    large, _ = execute(48000,48099,100, freq_sweep=True)
    assert len(small.binprog) == len(large.binprog)
    assert len(large._runtime_dmem_words) == 100*6+2


@pytest.mark.parametrize('gain', [16384,-16384,32766])
def test_gain_out_of_preservable_range_rejected(gain):
    with pytest.raises(ValueError, match='16383'):
        execute(97,gain=gain)


def test_fractional_extension_rejected_without_changing_awg_timing():
    with pytest.raises(ValueError, match='fixed segment'):
        execute(100,115,16,segment_mode='extend_by_rf_duration')


def test_integer_sample_conversion_is_ceiling_without_float_extra_sample():
    assert [samples_from_us(n/4800.,300) for n in range(1,97)] == list(range(1,97))
    assert samples_from_us(1.001/4800.,300)==2


def test_nine_decimal_gui_serialization_preserves_all_sample_endings():
    assert [samples_from_us(round(n/4800.,9),300) for n in range(1,113)]==list(range(1,113))
    points=np.linspace(round(81/4800.,9),round(112/4800.,9),32)
    assert [samples_from_us(value,300) for value in points]==list(range(81,113))
    assert samples_from_us(32/4800.+0.6e-9,300)==33
    assert samples_from_us(32/4800.+0.4e-9,300)==32


@pytest.mark.parametrize('swept', [False, True])
def test_overlap_readout_dc_waits_for_masked_tail_after_hold(swept):
    from test_dc_readout_timing import fixture, signed
    cfg, seq, ddr, _ = fixture('overlap_readout', rc=False)
    if swept:
        seq.add_rf_duration_sweep('measure', 2, 97/4800., 160/4800., 2,
                                 sequence_fabric_mhz=300.)
    rf = RfPulseConfig(2, 'measure', 7, 1000, delay_tproc_cycles=1198,
                      require_within_segment=False, fine_duration=True, duration_samples=97)
    program = seq.make_program(cfg, awg_channels=(0, 1), ddr_readout=ddr, rf_pulse=rf,
                               repetitions_per_sweep=2, compile_validation_mode='boundary')
    program.compile()
    model = TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(model)
    model.run(program, max_steps=1_000_000)
    assert not model.timing_conflicts
    barrier = next(m for m in program._capture_compensation_models
                   if m['key'] == ('capture_compensation', 'rf_end_0'))
    final_busy = max(row['busy_end'] for row in program._fine_rf_rows[0]['details'])
    final_busy += program.aux_timing.get('rf_0_output_latency', 0)
    assert barrier['base'] == final_busy
    assert not any(barrier['axis_deltas'])
    readouts = [event for event in model.output_events if event.tproc_ch == 2]
    for shot, readout in enumerate(readouts):
        stop = readouts[shot+1].cycle if shot+1 < len(readouts) else float('inf')
        comps = [event for event in model.output_events
                 if event.tproc_ch == 0 and readout.cycle <= event.cycle < stop
                 and not event.word & (1 << 149) and signed(event.word) < 0]
        assert len(comps) == 1
        assert comps[0].cycle >= readout.cycle + final_busy


def test_fine_tail_checks_shared_port_spacing_to_compensation_pre_zero():
    cfg = _shared_tmux_soccfg()
    seq = FineTuneSequence(('awg_0',)).add_set('gate', .01, 100)
    seq.set_bias_t_compensation(mode='fixed_time', fixed_duration_cycles=100)
    rf = RfPulseConfig(0, 'gate', 7, 1000, delay_tproc_cycles=95,
                      require_within_segment=False, fine_duration=True, duration_samples=97)
    with pytest.raises(ValueError, match='3 clocks'):
        seq.make_program(cfg, awg_channels=(1,), rf_pulse=rf)


def test_many_composite_events_do_not_emit_unused_startup_register_writes():
    pulses = tuple(RfPulseConfig(0, 'gate', 7, 1000, delay_tproc_cycles=30+100*i,
                                event_id=f'fine_{i}', fine_duration=True, duration_samples=97)
                   for i in range(33))
    program, events = execute(97, pulses=pulses, reps=1)
    assert len(events) == 66
    one, _ = execute(97, reps=1)
    def startup(prog):
        end = next(i for i, instruction in enumerate(prog.prog_list)
                   if instruction.get('label') == 'FINE_TUNE_POINT')
        return prog.prog_list[:end]
    assert startup(program) == startup(one)


def test_short_family_emits_no_phantom_tail_instructions():
    program, _ = execute(81, 95, 15, reps=1)
    assert not any('ending pattern' in item.get('comment', '')
                   or 'tail complete' in item.get('comment', '')
                   or 'no second command' in item.get('comment', '')
                   for item in program.prog_list)


def test_long_hardware_sweep_tail_reuses_carrier_and_exact_row_registers():
    program, _ = execute(96, 112, 17, reps=1, freq_sweep=True)
    tail = next(i for i, item in enumerate(program.prog_list)
                if item.get('comment') == 'fine RF ending pattern')
    assert program.prog_list[tail-1]['comment'] == 'compensate product envelope scaling'
    tail_instruction = program.prog_list[tail]
    registers = program._gen_regmap
    assert tail_instruction['args'][-2:] == (registers[(0, 'mode2')][1], registers[(0, 'addr2')][1])


@pytest.mark.parametrize('gain', [-16383, -4000, 4000, 16383])
def test_product_quantization_exhaustive_signed_dds_codes(gain):
    # signal_gen.v: envelope product takes bits[31:16], final gain bits[30:15].
    # Q=0, so floor(signed DDS*32766/2**16) is the product's real component.
    dds = np.arange(-32768, 32768, dtype=np.int64)
    direct = (dds*gain) >> 15
    masked = (((dds*32766) >> 16)*(2*gain)) >> 15
    assert int(np.max(np.abs(masked-direct))) == 1
    assert np.all((-32768 <= masked) & (masked <= 32767))


def test_nonstandard_envelope_scaling_is_rejected():
    cfg = _shared_tmux_soccfg()
    cfg['gens'][0]['maxv'] = 32000
    seq = FineTuneSequence(('awg_0',)).add_set('gate', .01, 100)
    rf = RfPulseConfig(0, 'gate', 7, 1000, delay_tproc_cycles=30,
                      fine_duration=True, duration_samples=97)
    with pytest.raises(ValueError, match='32766'):
        seq.make_program(cfg, awg_channels=(1,), rf_pulse=rf)


@pytest.mark.parametrize('has_dds', [False, None])
def test_generator_without_confirmed_dds_is_rejected(has_dds):
    cfg = _shared_tmux_soccfg()
    cfg['gens'][0]['has_dds'] = has_dds
    seq = FineTuneSequence(('awg_0',)).add_set('gate', .01, 100)
    rf = RfPulseConfig(0, 'gate', 7, 1000, delay_tproc_cycles=30,
                      fine_duration=True, duration_samples=97)
    with pytest.raises(ValueError, match='has_dds=True'):
        seq.make_program(cfg, awg_channels=(1,), rf_pulse=rf)


def test_readout_control_shared_port_collision_is_rejected():
    from qick_fine_tune_sweep import ReadoutConfig
    from test_qick_fine_tune_sweep import _avg_soccfg
    cfg = _shared_tmux_soccfg()
    cfg['readouts'] = _avg_soccfg(1)['readouts']
    cfg['readouts'][0].update(tproc_ctrl=0, trigger_port=7)
    seq = FineTuneSequence(('awg_0',)).add_set('gate', .01, 100)
    rf = RfPulseConfig(0, 'gate', 7, 1000, delay_tproc_cycles=95,
                      require_within_segment=False, fine_duration=True, duration_samples=97)
    with pytest.raises(ValueError, match='3 clocks'):
        seq.make_program(cfg, awg_channels=(1,), rf_pulse=rf,
                         readout=ReadoutConfig(0, 10, at_segment='gate'))


def test_calibrated_gain_and_frequency_cross_product_are_loaded_for_both_parts():
    cfg = _shared_tmux_soccfg()
    seq = FineTuneSequence(('awg_0',)).add_set('gate', .01, 10000)
    seq.add_rf_duration_sweep('gate',0,97/4800.,99/4800.,3,sequence_fabric_mhz=300.)
    seq.add_rf_frequency_sweep('gate',0,10.,20.,2)
    rf = RfPulseConfig(0,'gate',7,100,delay_tproc_cycles=30,fine_duration=True,duration_samples=97,
                      sweep_gain_codes=(100,300),sweep_gain_shape=(2,1))
    program = seq.make_program(cfg,awg_channels=(1,),rf_pulse=rf,repetitions_per_sweep=2)
    program.compile()
    model=TProcV1BehaviorModel(strict=True)
    program.load_runtime_dmem_into_model(model)
    model.run(program)
    events=[e for e in model.output_events if (e.word>>152)&255==0]
    expected=[]
    for _ in range(3):
        for gain in (100,300):
            expected.extend([gain,2*gain]*2)
    assert [(e.word>>96)&65535 for e in events]==expected
    assert all(a.word&0xffffffff==b.word&0xffffffff for a,b in zip(events[::2],events[1::2]))


def test_swept_preceding_duration_moves_composite_start_with_exact_carry():
    cfg = _shared_tmux_soccfg()
    seq=FineTuneSequence(('awg_0',)).add_set('gate',.01,10000)
    seq.add_rf_duration_sweep('gate',0,95/4800.,110/4800.,16,
                              parameter_name='pi',sequence_fabric_mhz=300.)
    a=RfPulseConfig(0,'gate',6,1000,event_id='a',delay_tproc_cycles=30,
                   fine_duration=True,duration_samples=95,duration_parameter='pi')
    b=RfPulseConfig(0,'gate',3,1000,event_id='b',delay_tproc_cycles=66,
                   fine_duration=True,duration_samples=15,preceding_duration_parameters=('pi',))
    p=seq.make_program(cfg,awg_channels=(1,),rf_pulses=(a,b),repetitions_per_sweep=1)
    p.compile(); model=TProcV1BehaviorModel(strict=True)
    p.load_runtime_dmem_into_model(model); model.run(p)
    events=[e for e in model.output_events if (e.word>>152)&255==0]
    cursor=0
    for n in range(95,111):
        count=1+plan_duration(n).long
        shot=events[cursor:cursor+count+1]
        assert shot[-1].cycle-shot[0].cycle==36+(n+15)//16-6
        cursor+=count+1
    assert cursor==len(events)


def test_padding_overlap_and_shared_port_reordering_are_rejected():
    a=RfPulseConfig(0,'gate',3,1000,event_id='a',delay_tproc_cycles=30,
                   fine_duration=True,duration_samples=1)
    b=replace(a,event_id='b',delay_tproc_cycles=31)
    with pytest.raises(ValueError,match='overlap|3 clocks'):
        execute(1,pulses=(a,b))
    b=replace(a,event_id='b',delay_tproc_cycles=40)
    with pytest.raises(ValueError,match='order|overlap|3 clocks'):
        execute(97,1000,2,pulses=(replace(a,duration_samples=97),b))


def test_periodic_plateau_always_ends_on_its_three_clock_word_boundary():
    for q in (65539,65540,90000,90001,90002):
        for remainder in range(16):
            plan=plan_duration(q*16+remainder)
            assert plan.periodic_plateau
            assert plan.tail_offset%3==0
            assert plan.tail_offset*16+(5-plan.address_offset_words)*16+remainder==plan.samples


def test_summary_distinguishes_active_samples_and_padded_busy_time():
    p,_=execute(1)
    value=p.summary()['rf_fine_duration'][0]
    assert value['actual_duration_us']==(1/4800.,)
    assert value['busy_cycles']==(3,)
    assert value['pattern_count']==16


@pytest.mark.parametrize('samples',[90000*16+1,90001*16+15,90002*16+7])
def test_very_long_periodic_plateau_uses_exact_timed_tail(samples):
    p, events=execute(samples,reps=1)
    assert len(events)==2
    assert (events[0].word>>146)&1==1
    plateau_cycles=events[1].cycle-events[0].cycle
    assert plateau_cycles%3==0
    tail=active_samples(p,events[1:])[0][1]
    assert plateau_cycles*16+tail==samples


def test_calibrated_gain_above_limit_rejected_before_loading():
    rf=RfPulseConfig(0,'gate',7,100,fine_duration=True,duration_samples=97,
                    sweep_gain_codes=(16384,),sweep_gain_shape=(1,1))
    with pytest.raises(ValueError,match='16383'):
        execute(97,pulses=(rf,))
