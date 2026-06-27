"""Pure-Python tests for trigger-aligned DDR packer support."""

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

from qick.drivers.readout import AxisBufferDdrV1  # noqa: E402
from qick.ip import QickMetadata  # noqa: E402


def make_metadata(modtypes, bus_map, params=None):
    metadata = object.__new__(QickMetadata)
    metadata.modinfo = {
        name: {
            "type": modtype,
            "version": "1.0",
            "revision": 0,
            "params": (params or {}).get(name, {}),
        }
        for name, modtype in modtypes.items()
    }

    def trace_bus(blockname, portname):
        return bus_map.get((blockname, portname), [])

    metadata.trace_bus = trace_bus
    return metadata


def make_ddr_helper(burst_len=128):
    ddr = object.__new__(AxisBufferDdrV1)
    ddr._cfg = {"burst_len": burst_len}
    return ddr


class TestTriggeredPackMetadata(unittest.TestCase):
    def test_trace_back_treats_triggered_pack_as_pass_through(self):
        metadata = make_metadata(
            {
                "ddr": "axis_buffer_ddr_v1",
                "clk": "axis_clock_converter",
                "pack": "axis_triggered_pack_32to256_v1",
                "sw": "axis_switch",
            },
            {
                ("ddr", "s_axis"): [("clk", "M_AXIS")],
                ("clk", "S_AXIS"): [("pack", "M_AXIS")],
                ("pack", "S_AXIS"): [("sw", "M00_AXIS")],
            },
        )

        self.assertEqual(
            metadata.trace_back("ddr", "s_axis", ["axis_switch"]),
            ("sw", "M00_AXIS", "axis_switch"),
        )

    def test_trace_forward_treats_triggered_pack_as_pass_through(self):
        metadata = make_metadata(
            {
                "ro": "axis_dyn_readout_v1",
                "pack": "axis_triggered_pack_32to256_v1",
                "ddr": "axis_buffer_ddr_v1",
            },
            {
                ("ro", "m_axis"): [("pack", "S_AXIS")],
                ("pack", "M_AXIS"): [("ddr", "s_axis")],
            },
        )

        self.assertEqual(
            metadata.trace_forward("ro", "m_axis", ["axis_buffer_ddr_v1"]),
            ("ddr", "s_axis", "axis_buffer_ddr_v1"),
        )


class TestAxisBufferDdrSampleHelpers(unittest.TestCase):
    def test_bursts_for_samples_uses_32bit_sample_burst_alignment(self):
        ddr = make_ddr_helper(burst_len=128)

        self.assertEqual(ddr.samples_per_burst(), 128)
        self.assertEqual(ddr.bursts_for_samples(128), 1)
        self.assertEqual(ddr.bursts_for_samples(256), 2)

        with self.assertRaises(ValueError):
            ddr.bursts_for_samples(127)

    def test_arm_samples_calls_existing_arm_with_burst_count(self):
        ddr = make_ddr_helper(burst_len=128)
        calls = []

        def fake_arm(self, nt, force_overwrite=False):
            calls.append((nt, force_overwrite))

        ddr.arm = types.MethodType(fake_arm, ddr)

        self.assertEqual(ddr.arm_samples(256, force_overwrite=True), 2)
        self.assertEqual(calls, [(2, True)])


if __name__ == "__main__":
    unittest.main()
