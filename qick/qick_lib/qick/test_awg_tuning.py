"""Pure-Python tests for qick.awg_tuning.

These tests stub the minimal PYNQ symbol needed to import SocIP, so they do not
require a board or a PYNQ installation.
"""
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

from qick.awg_tuning import AxisAwgTuningV1


def make_driver():
    return AxisAwgTuningV1({
        "type": "QICK:QICK:axis_awg_tuning_v1:1.0",
        "fullpath": "axis_awg_tuning_v1_0",
        "parameters": {
            "N_DDS": "4",
            "B": "16",
            "FRAC": "16",
            "CMD_WIDTH": "160",
        },
    })


class TestAxisAwgTuningV1(unittest.TestCase):
    def test_signed_field_and_round_trip_packing(self):
        drv = make_driver()
        cmd = drv.pack_cmd(
            target=-1,
            start=123,
            duration=5,
            step=-7,
            opcode=drv.OP_RAMP,
            hold_zero=True,
            clear=True,
        )

        self.assertEqual(drv.cmd_to_words(cmd), [
            0xFFFFFFFF,
            0x0000007B,
            0x00000005,
            0x00FFFFF9,
            0x00160000,
        ])
        decoded = drv.format_cmd(cmd)
        self.assertEqual(decoded["opcode"], drv.OP_RAMP)
        self.assertEqual(decoded["op"], "ramp")
        self.assertEqual(decoded["target"], -1)
        self.assertEqual(decoded["reserved_start"], 123)
        self.assertEqual(decoded["start_ignored"], 123)
        self.assertEqual(decoded["duration"], 5)
        self.assertEqual(decoded["step"], -7)
        self.assertTrue(decoded["hold_zero"])
        self.assertTrue(decoded["clear"])

    def test_opcode_helpers(self):
        drv = make_driver()
        self.assertEqual(drv.format_cmd(drv.nop_cmd())["opcode"], drv.OP_NOP)
        self.assertEqual(drv.format_cmd(drv.set_cmd(1234))["opcode"], drv.OP_SET)
        with self.assertRaises(NotImplementedError):
            drv.idle_cmd(6)

        drv.reset_cache(1234, valid=True)
        ramp = drv.ramp_cmd(2000, 24)
        decoded = drv.format_cmd(ramp)
        self.assertEqual(decoded["opcode"], drv.OP_RAMP)
        self.assertEqual(decoded["reserved_start"], 0)
        self.assertEqual(decoded["duration"], 24 * drv["n_pts"])
        self.assertEqual(decoded["step"], drv.calc_step(1234, 2000, 24))

    def test_step_calculation_truncates_toward_zero(self):
        drv = make_driver()
        npts = drv["n_pts"]

        one_cycle_num = (1100 - 1000) << drv["frac"]
        self.assertEqual(drv.calc_step(1000, 1100, 1), one_cycle_num // (npts - 1))

        pos_num = (2000 - 1000) << drv["frac"]
        self.assertEqual(drv.calc_step(1000, 2000, 24), pos_num // (24 * npts - 1))

        neg_num = (-2000 - 2000) << drv["frac"]
        expected = -(abs(neg_num) // (64 * npts - 1))
        self.assertEqual(drv.calc_step(2000, -2000, 64), expected)
        self.assertNotEqual(expected, neg_num // (64 * npts - 1))

    def test_sequence_updates_cache_and_uses_current_start(self):
        drv = make_driver()
        drv.reset_cache(0, valid=True)
        cmds = drv.make_sequence([
            {"op": "set", "value": 1000},
            {"op": "ramp", "target": 2000, "duration": 24},
            {"op": "ramp", "target": -1000, "duration": 25},
        ])

        first_ramp = drv.format_cmd(cmds[1])
        self.assertEqual(first_ramp["reserved_start"], 0)
        self.assertEqual(first_ramp["step"], drv.calc_step(1000, 2000, 24))
        self.assertEqual(drv.last_ramp_start, 2000)

        second_ramp = drv.format_cmd(cmds[2])
        self.assertEqual(second_ramp["reserved_start"], 0)
        self.assertEqual(second_ramp["step"], drv.calc_step(2000, -1000, 25))
        self.assertEqual(drv.current_value, -1000)
        self.assertTrue(drv.current_valid)

    def test_explicit_ramp_step_is_allowed(self):
        drv = make_driver()
        drv.reset_cache(1000, valid=True)
        cmds = drv.make_sequence([
            {"op": "ramp", "target": 2000, "duration": 24, "step": 12345},
        ])

        decoded = drv.format_cmd(cmds[0])
        self.assertEqual(decoded["step"], 12345)
        self.assertEqual(drv.last_ramp_step, 12345)

    def test_range_validation(self):
        drv = make_driver()
        with self.assertRaises(ValueError):
            drv.pack_cmd(target=2**31)
        with self.assertRaises(ValueError):
            drv.pack_cmd(duration=-1)
        with self.assertRaises(ValueError):
            drv.pack_cmd(step=-(2**31) - 1)


if __name__ == "__main__":
    unittest.main()
