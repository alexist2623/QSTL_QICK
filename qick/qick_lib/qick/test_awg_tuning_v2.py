"""V2 driver/assembly ABI boundaries; no board is needed."""
from qick.sim import QickSim  # installs desktop PYNQ stubs
from qick.awg_tuning import AxisAwgTuningV1, AxisAwgTuningV2
import pytest


def driver(cls):
    version = 2 if cls is AxisAwgTuningV2 else 1
    return cls(dict(type=f'QICK:QICK:axis_awg_tuning_v{version}:1.0',
                    fullpath=f'axis_awg_tuning_v{version}_0',
                    parameters=dict(N_PTS='16', B='16', CMD_WIDTH='160')))


@pytest.mark.parametrize('step', [-(1 << 31), -(1 << 30)-1, -1, 0, 1, (1 << 31)-1])
def test_full_word_signed_round_trip(step):
    dut=driver(AxisAwgTuningV2)
    word=dut.pack_cmd(target=32764,duration=16,step=step,opcode=dut.OP_RAMP)
    assert dut.cmd_to_words(word)[3] == step & 0xffffffff
    assert dut.format_cmd(word)['step'] == step
    assert dut.format_cmd(word)['step_ignored_high'] == 0


def test_full_scale_single_fabric_cycle_and_legacy_rejection():
    new=driver(AxisAwgTuningV2); old=driver(AxisAwgTuningV1)
    assert new['frac']==18 and new['step_width']==32
    assert new.calc_step(-32768,32764,1)==1145254707
    assert new.calc_step(32764,-32768,1)==-1145254707
    assert old['frac']==16 and old['step_width']==24
    with pytest.raises(ValueError):old.calc_step(-32768,32764,1)
    for step in (-(1<<31)-1,1<<31):
        with pytest.raises(ValueError):new.pack_cmd(step=step)


def test_reject_wrong_v2_format():
    for bad in ({'FRAC':'16'}, {'STEP_WIDTH':'24'}):
        with pytest.raises(ValueError):
            AxisAwgTuningV2(dict(type='QICK:QICK:axis_awg_tuning_v2:1.0',
                               fullpath='awg',parameters=bad))


def test_public_simulator_uses_hwh_width_and_precision(tmp_path):
    from qick.sim.test_qick_sim import make_awg_hwh
    from qick.awg_tuning import TimedCommandEvent
    hwh = tmp_path / 'mini.hwh'
    bit = tmp_path / 'mini.bit'
    bit.write_bytes(b'simulation placeholder')
    make_awg_hwh(hwh)
    hwh.write_text(hwh.read_text().replace('axis_awg_tuning_v1', 'axis_awg_tuning_v2')
        .replace('NAME="FRAC" VALUE="16"', 'NAME="FRAC" VALUE="18"')
        .replace('NAME="STEP_WIDTH" VALUE="24"', 'NAME="STEP_WIDTH" VALUE="32"'))
    sim = QickSim(bit)
    gen = sim.gens[0]
    assert isinstance(gen, AxisAwgTuningV2)
    model = sim._model_for_gen(gen, 0)
    result = model.run(70, [
        TimedCommandEvent(10, gen.pack_cmd(target=-32768, opcode=1)),
        TimedCommandEvent(30, gen.pack_cmd(target=32764, duration=16, step=1145254707, opcode=2))])
    expected = [((-32768 * (1 << 18) + 1145254707 * i) >> 18) & ~3 for i in range(15)] + [32764]
    assert result.lane_samples[35].tolist() == expected


def test_public_simulator_preloads_program_sweep_dmem(tmp_path):
    from qick.sim.test_qick_sim import make_awg_hwh
    from types import SimpleNamespace
    hwh = tmp_path / 'mini.hwh'
    bit = tmp_path / 'mini.bit'
    bit.write_bytes(b'simulation placeholder')
    make_awg_hwh(hwh)
    sim = QickSim(bit)
    words = sim.gens[0].cmd_to_words(sim.gens[0].pack_cmd(target=0, opcode=1))
    instructions = [{'name': 'regwi', 'args': (0, i+1, word)} for i, word in enumerate(words)]
    instructions += [
        {'name': 'memri', 'args': (0, 1, 16)},
        {'name': 'regwi', 'args': (0, 6, 50)},
        {'name': 'set', 'args': (0, 0, 1, 2, 3, 4, 5, 6)},
        {'name': 'end', 'args': ()}]
    program = SimpleNamespace(prog_list=instructions,
        load_runtime_dmem_into_model=lambda model: model.dmem.update({16: 1232}))
    result = sim.simulate_program(program, cycles=65)
    assert (result.channel_results['lane_samples']['gen0'][55] == 1232).all()
