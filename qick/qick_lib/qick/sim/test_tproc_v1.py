"""Tests for qick.sim.tproc_v1."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from qick.asm_v1 import QickProgram  # noqa: E402
from qick.sim.tproc_v1 import TProcV1Sim  # noqa: E402


class TestTProcV1Sim(unittest.TestCase):
    def test_instruction_handler_coverage(self):
        self.assertEqual(TProcV1Sim.missing_instruction_handlers(QickProgram.instructions.keys()), [])

    def test_output_event_generation(self):
        prog = [
            {"name": "regwi", "args": (0, 1, 0x11)},
            {"name": "regwi", "args": (0, 2, 0x22)},
            {"name": "regwi", "args": (0, 3, 0x33)},
            {"name": "regwi", "args": (0, 4, 0x44)},
            {"name": "regwi", "args": (0, 5, 0x55)},
            {"name": "regwi", "args": (0, 6, 20)},
            {"name": "set", "args": (1, 0, 1, 2, 3, 4, 5, 6)},
            {"name": "end", "args": ()},
        ]

        sim = TProcV1Sim().run(prog)

        self.assertEqual(len(sim.output_events), 1)
        self.assertEqual(sim.output_events[0].cycle, 20)
        self.assertEqual(sim.output_events[0].tproc_ch, 1)
        self.assertEqual(sim.output_events[0].word & 0xFFFFFFFF, 0x11)


if __name__ == "__main__":
    unittest.main()
