"""Pure-Python tests for the qstl_awg_tuning project behavior simulator."""

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

from qick.awg_tuning import (  # noqa: E402
    AxisAvgBufferV13BehaviorModel,
    AxisBroadcasterBehaviorModel,
    AxisClockConverterBehaviorModel,
    AxisDynReadoutV1BehaviorModel,
    AxisRegisterSliceBehaviorModel,
    AxisSignalGenV6BehaviorModel,
    AxisSwitchBehaviorModel,
    AxisTmuxV1BehaviorModel,
    QstlAwgTuningProjectSimulator,
    RfdcAdcSourceModel,
    TimedCommandEvent,
    UnsupportedModeError,
)


def pack_iq(i_val, q_val):
    return (int(i_val) & 0xFFFF) | ((int(q_val) & 0xFFFF) << 16)


def make_siggen_dds_cmd(tmux_select=0, gain=1000, nsamp=32, freq=0, phase=0):
    cmd = 0
    cmd |= int(freq) & 0xFFFFFFFF
    cmd |= (int(phase) & 0xFFFFFFFF) << 32
    cmd |= (int(gain) & 0xFFFF) << 96
    cmd |= (int(nsamp) & 0xFFFF) << 128
    cmd |= 1 << 144
    cmd |= (int(tmux_select) & 0xFF) << 152
    return cmd


def make_awg_set_cmd(tmux_select=4, target=1000):
    cmd = int(target) & 0xFFFFFFFF
    cmd |= 1 << 144
    cmd |= (int(tmux_select) & 0xFF) << 152
    return cmd


class TestQstlAwgTuningProjectSimulator(unittest.TestCase):
    def test_bd_topology_validation_has_expected_modeled_ips(self):
        bd_path = Path(__file__).resolve().parents[2] / "firmware" / "projects" / "qstl_awg_tuning" / "bd_2023-1.tcl"
        sim = QstlAwgTuningProjectSimulator.from_bd_tcl(bd_path, strict=True)
        report = sim.validate_bd()

        self.assertEqual(report["unsupported_ips"], [])
        for name in (
            "axis_tproc64x32_x8",
            "axis_tmux_v1",
            "axis_signal_gen_v6",
            "axis_awg_tuning_v1",
            "axis_dyn_readout_v1",
            "axis_avg_buffer",
            "axis_register_slice",
            "axis_broadcaster",
            "axis_clock_converter",
            "axis_switch",
        ):
            self.assertGreater(report["modeled_hits"][name], 0, name)

    def test_axis_plumbing_blocks_have_explicit_latency_or_routing(self):
        event = TimedCommandEvent(cycle=10, word=4 << 152, label="pipe")

        tmux_event = AxisTmuxV1BehaviorModel(latency=2).route(event)
        self.assertEqual(tmux_event.cycle, 12)
        self.assertEqual(tmux_event.tmux_ch, 4)
        self.assertEqual(tmux_event.channel, 4)

        reg_event = AxisRegisterSliceBehaviorModel(latency=1).route(tmux_event)
        self.assertEqual(reg_event.cycle, 13)
        self.assertEqual(reg_event.route_latency, 3)

        clk_event = AxisClockConverterBehaviorModel(latency=2).route(reg_event)
        self.assertEqual(clk_event.cycle, 15)
        self.assertEqual(clk_event.route_latency, 5)

        copies = AxisBroadcasterBehaviorModel(outputs=3, latency=1).route(event)
        self.assertEqual([copy.channel for copy in copies], [0, 1, 2])
        self.assertEqual([copy.cycle for copy in copies], [11, 11, 11])

        switched = AxisSwitchBehaviorModel(selection={2: 7}, latency=1).route(event, input_port=2)
        self.assertEqual(switched.channel, 7)
        self.assertEqual(switched.cycle, 11)

    def test_signal_gen_dds_mode_and_unsupported_modes(self):
        model = AxisSignalGenV6BehaviorModel(n_dds=4)
        cmd = make_siggen_dds_cmd(gain=1200, nsamp=8, freq=0)
        result = model.run(5, [TimedCommandEvent(cycle=1, word=cmd, label="dds")])

        self.assertEqual(len(result.accepted_commands), 1)
        self.assertTrue(np.all(result.lane_samples[1] == 1200))
        self.assertTrue(np.all(result.lane_samples[2] == 1200))

        product_mode_cmd = cmd & ~(0x3 << 144)
        with self.assertRaises(UnsupportedModeError):
            AxisSignalGenV6BehaviorModel(n_dds=4, strict=True).accept_command(0, product_mode_cmd)

    def test_dyn_readout_and_avg_buffer_capture(self):
        adc = RfdcAdcSourceModel(samples=[
            [1, 2, 3, 4],
            [5, 6, 7, 8],
            [9, 10, 11, 12],
        ], n_lanes=4)
        readout = AxisDynReadoutV1BehaviorModel(n_dds=4, adc_source=adc)
        readout_cmd = 3 << 64
        readout.accept_command(20, readout_cmd, label="readout")

        self.assertEqual(len(readout.captured), 3)
        self.assertEqual(readout.captured[0]["sample"], [1, 2, 3, 4])

        avg = AxisAvgBufferV13BehaviorModel(accum_len=2)
        feedback = avg.capture(30, [
            pack_iq(1, -2),
            pack_iq(3, 4),
            pack_iq(-5, 6),
        ])

        self.assertEqual(avg.raw_buffer, [pack_iq(1, -2), pack_iq(3, 4), pack_iq(-5, 6)])
        first_i = feedback[0].word & ((1 << 64) - 1)
        first_q = (feedback[0].word >> 64) & ((1 << 64) - 1)
        second_i = feedback[1].word & ((1 << 64) - 1)
        self.assertEqual(first_i, 4)
        self.assertEqual(first_q, 2)
        self.assertEqual(second_i, ((-5) & ((1 << 64) - 1)))

    def test_qstl_tmux_dispatches_signal_gen_and_awg_commands(self):
        sim = QstlAwgTuningProjectSimulator(strict=True)
        events = [
            TimedCommandEvent(cycle=5, word=make_siggen_dds_cmd(tmux_select=1), label="siggen1"),
            TimedCommandEvent(cycle=8, word=make_awg_set_cmd(tmux_select=4, target=1000), label="awg4"),
        ]
        result = sim.run_events(events, cycles=20)

        self.assertEqual(result.unsupported_ips, [])
        self.assertEqual(result.unsupported_modes, [])
        paths = [event["path"] for event in result.ip_events]
        self.assertIn("axis_signal_gen_v6_1", paths)
        self.assertIn("axis_awg_tuning_v1_4", paths)

        siggen1 = result.channel_results["lane_samples"]["siggen1"]
        awg0 = result.channel_results["lane_samples"]["awg0"]
        self.assertTrue(np.all(siggen1[7] == 1000))
        self.assertTrue(np.all(awg0[10] == 1000))


if __name__ == "__main__":
    unittest.main()
