"""Pure-Python ASM v1 tests for axis_awg_tuning_v1 integration."""
# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

import sys
import types
import unittest
from pathlib import Path

import numpy as np


class _DefaultIP:
    bindto = []

    def __init__(self, description):
        self.description = description


def _install_pynq_stub():
    pynq = types.ModuleType("pynq")
    overlay = types.ModuleType("pynq.overlay")
    buffer = types.ModuleType("pynq.buffer")
    overlay.DefaultIP = _DefaultIP
    buffer.allocate = lambda shape, dtype=None, **kwargs: np.zeros(shape, dtype=dtype)
    sys.modules.setdefault("pynq", pynq)
    sys.modules.setdefault("pynq.overlay", overlay)
    sys.modules.setdefault("pynq.buffer", buffer)


_install_pynq_stub()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qick.asm_v1 import AwgTuningGenManager, QickProgram
from qick.awg_tuning import AxisAwgTuningV1
from qick.qick_asm import QickConfig


def make_soccfg(tmux_ch=None):
    gen = {
        "type": "axis_awg_tuning_v1",
        "gen_type": "awg_tuning",
        "tproc_ch": 0,
        "f_fabric": 100.0,
        "n_pts": 16,
        "samps_per_clk": 16,
        "frac": 16,
        "cmd_width": 160,
        "step_width": 24,
        "duration_width": 23,
        "fixed_width": 48,
        "dac_invalid_lsb": 2,
        "maxv": 32764,
        "minv": -32768,
        "ramp_startup_latency_cycles": 7,
        "ramp_guard_cycles": 1,
        "has_mixer": False,
        "has_dds": False,
        "b_dds": 32,
        "b_phase": 32,
        "dac": "00",
        "interpolation": 1,
    }
    if tmux_ch is not None:
        gen["tmux_ch"] = tmux_ch
    return QickConfig({
        "sw_version": "test",
        "tprocs": [{"type": "axis_tproc64x32_x8", "f_time": 100.0}],
        "gens": [gen],
        "readouts": [],
    })


def make_prog(tmux_ch=None):
    return QickProgram(make_soccfg(tmux_ch=tmux_ch))


class TestAwgTuningAsmV1(unittest.TestCase):
    def test_manager_register_allocation(self):
        prog = make_prog()
        mgr = prog._gen_mgrs[0]
        self.assertIsInstance(mgr, AwgTuningGenManager)
        self.assertEqual(
            mgr.PULSE_REGISTERS,
            ["target", "reserved_start", "duration", "step", "control", "t"],
        )
        for name in mgr.PULSE_REGISTERS:
            self.assertIn((0, name), prog._gen_regmap)

    def test_awg_set_registers(self):
        prog = make_prog()
        prog.set_pulse_registers(0, style="awg_set", value=1234, duration=160)
        mgr = prog._gen_mgrs[0]

        self.assertIsNotNone(mgr.next_pulse)
        self.assertEqual(len(mgr.next_pulse["regs"]), 1)
        self.assertEqual(len(mgr.next_pulse["regs"][0]), 5)
        self.assertEqual(mgr.next_pulse["length"], 10)
        self.assertEqual(mgr.last_cmd & 0xFFFFFFFF, 1234)
        self.assertEqual((mgr.last_cmd >> 64) & ((1 << 23) - 1), 0)
        self.assertEqual((mgr.last_cmd >> 144) & 0b11, AxisAwgTuningV1.OP_SET)

    def test_awg_ramp_registers_and_timestamp_length(self):
        prog = make_prog()
        prog.set_pulse_registers(0, style="awg_set", value=1000, duration=160)
        prog.set_pulse_registers(0, style="awg_ramp", target=4000, duration=160)
        mgr = prog._gen_mgrs[0]

        expected_step = ((4000 - 1000) << 16) // (160 - 1)
        self.assertEqual((mgr.last_cmd >> 144) & 0b11, AxisAwgTuningV1.OP_RAMP)
        self.assertEqual((mgr.last_cmd >> 64) & ((1 << 23) - 1), 160)
        self.assertEqual(AxisAwgTuningV1._from_signed_field(mgr.last_cmd >> 96, 24), expected_step)
        self.assertEqual(mgr.next_pulse["length"], 18)
        self.assertEqual(mgr.current_value, 4000)
        self.assertTrue(mgr.current_valid)

    def test_tmux_injection_preserves_opcode(self):
        prog = make_prog(tmux_ch=1)
        prog.set_pulse_registers(0, style="awg_set", value=1234, duration=160)
        mgr = prog._gen_mgrs[0]

        self.assertEqual(mgr.last_cmd_words[4] >> 24, 1)
        self.assertEqual((mgr.last_cmd >> 144) & 0b11, AxisAwgTuningV1.OP_SET)

    def test_pulse_emits_standard_set_instruction(self):
        prog = make_prog()
        prog.set_pulse_registers(0, style="awg_set", value=1234, duration=160)
        mgr = prog._gen_mgrs[0]
        regs = tuple(mgr.next_pulse["regs"][0])
        rp, r_t = prog._gen_regmap[(0, "t")]

        prog.pulse(0, t=25)
        set_insts = [inst for inst in prog.prog_list if inst["name"] == "set"]
        self.assertEqual(len(set_insts), 1)
        self.assertEqual(set_insts[0]["args"], (0, rp, *regs, r_t))

    def test_timestamp_auto_uses_awg_lengths(self):
        prog = make_prog()
        prog.awg_set(0, value=1000, duration=160, t="auto")
        self.assertEqual(prog.get_timestamp(gen_ch=0), 10)
        prog.awg_ramp(0, target=2000, duration=160, t="auto")
        self.assertEqual(prog.get_timestamp(gen_ch=0), 28)

    def test_reject_standard_styles_and_envelopes(self):
        prog = make_prog()
        with self.assertRaisesRegex(RuntimeError, "does not support const/arb/flat_top"):
            prog.set_pulse_registers(0, style="const", freq=0, phase=0, gain=0, length=16)
        with self.assertRaisesRegex(RuntimeError, "does not have waveform memory"):
            prog.add_pulse(0, "bad", idata=np.zeros(16, dtype=np.int16))


if __name__ == "__main__":
    unittest.main()
