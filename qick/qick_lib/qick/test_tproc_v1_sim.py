"""Pure-Python tests for the tProcessor v1 behavior model."""

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

from qick.asm_v1 import QickProgram  # noqa: E402
from qick.awg_tuning import TProcV1BehaviorModel  # noqa: E402


class TestTProcV1BehaviorModel(unittest.TestCase):
    def test_declared_instruction_handlers_exist(self):
        missing = TProcV1BehaviorModel.missing_instruction_handlers(QickProgram.instructions.keys())
        self.assertEqual(missing, [])

    def test_immediate_register_math_bit_and_memory(self):
        prog = [
            {"name": "regwi", "args": (0, 1, 10)},
            {"name": "mathi", "args": (0, 2, 1, "+", 5)},
            {"name": "bitwi", "args": (0, 3, 2, "<<", 1)},
            {"name": "memwi", "args": (0, 3, 4)},
            {"name": "memri", "args": (0, 4, 4)},
            {"name": "end", "args": ()},
        ]
        sim = TProcV1BehaviorModel().run(prog)
        self.assertEqual(sim._read_signed(0, 1), 10)
        self.assertEqual(sim._read_signed(0, 2), 15)
        self.assertEqual(sim._read_signed(0, 3), 30)
        self.assertEqual(sim._read_signed(0, 4), 30)
        self.assertEqual(sim._read_signed(0, 0), 0)

    def test_register_math_bit_memory_and_stack(self):
        prog = [
            {"name": "regwi", "args": (0, 1, 7)},
            {"name": "regwi", "args": (0, 2, 3)},
            {"name": "math", "args": (0, 3, 1, "*", 2)},
            {"name": "bitw", "args": (0, 4, 3, "|", 2)},
            {"name": "regwi", "args": (0, 5, 8)},
            {"name": "memw", "args": (0, 4, 5)},
            {"name": "memr", "args": (0, 6, 5)},
            {"name": "pushi", "args": (0, 6, "+", 2)},
            {"name": "popi", "args": (0, 7)},
            {"name": "end", "args": ()},
        ]
        sim = TProcV1BehaviorModel().run(prog)
        self.assertEqual(sim._read_signed(0, 3), 21)
        self.assertEqual(sim._read_signed(0, 4), 23)
        self.assertEqual(sim._read_signed(0, 6), 23)
        self.assertEqual(sim._read_signed(0, 7), 25)

    def test_loop_condj_and_time_instructions(self):
        prog = [
            {"name": "regwi", "args": (0, 1, 3)},
            {"name": "regwi", "args": (0, 2, 0)},
            {"name": "mathi", "args": (0, 2, 2, "+", 1), "label": "LOOP"},
            {"name": "loopnz", "args": (0, 1, "LOOP")},
            {"name": "regwi", "args": (0, 3, 3)},
            {"name": "condj", "args": (0, 2, ">=", 3, "SKIP")},
            {"name": "regwi", "args": (0, 4, 99)},
            {"name": "synci", "args": (4,), "label": "SKIP"},
            {"name": "waiti", "args": (0, 10)},
            {"name": "regwi", "args": (0, 5, 12)},
            {"name": "sync", "args": (0, 5)},
            {"name": "wait", "args": (0, 0, 5)},
            {"name": "end", "args": ()},
        ]
        sim = TProcV1BehaviorModel().run(prog)
        self.assertEqual(sim._read_signed(0, 2), 3)
        self.assertEqual(sim._read_signed(0, 4), 0)
        self.assertEqual(sim.current_cycle, 12)

    def test_output_read_and_pin_events(self):
        prog = [
            {"name": "regwi", "args": (0, 1, 0x11)},
            {"name": "regwi", "args": (0, 2, 0x22)},
            {"name": "regwi", "args": (0, 3, 0x33)},
            {"name": "regwi", "args": (0, 4, 0x44)},
            {"name": "regwi", "args": (0, 5, 0x55)},
            {"name": "regwi", "args": (0, 6, 20)},
            {"name": "set", "args": (1, 0, 1, 2, 3, 4, 5, 6)},
            {"name": "seti", "args": (2, 0, 1, 7)},
            {"name": "setbi", "args": (0, 2, 8)},
            {"name": "setb", "args": (0, 3, 6)},
            {"name": "read", "args": (0, 1, "lower", 7)},
            {"name": "end", "args": ()},
        ]
        sim = TProcV1BehaviorModel(input_queues={1: [0x1234]}).run(prog)
        self.assertEqual(len(sim.output_events), 1)
        self.assertEqual(sim.output_events[0].cycle, 20)
        self.assertEqual(sim.output_events[0].tproc_ch, 1)
        self.assertEqual(sim.output_events[0].word & 0xFFFFFFFF, 0x11)
        self.assertEqual(len(sim.output_pin_events), 3)
        self.assertEqual(sim._read_signed(0, 7), 0x1234)


if __name__ == "__main__":
    unittest.main()
