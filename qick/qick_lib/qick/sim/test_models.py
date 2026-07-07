"""Tests for qick.sim behavior models."""
# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from qick.sim.exceptions import UnsupportedModeError  # noqa: E402
from qick.sim.models import (  # noqa: E402
    AxisAvgBufferV13BehaviorModel,
    AxisAwgTuningBehaviorModel,
    AxisDynReadoutV1BehaviorModel,
    AxisSignalGenV6BehaviorModel,
    AxisTmuxV1BehaviorModel,
    RfdcAdcSourceModel,
    TimedCommandEvent,
)


def pack_iq(i_val, q_val):
    return (int(i_val) & 0xFFFF) | ((int(q_val) & 0xFFFF) << 16)


class TestModels(unittest.TestCase):
    def test_tmux_select_and_latency(self):
        event = TimedCommandEvent(cycle=10, word=5 << 152, tproc_ch=0)
        routed = AxisTmuxV1BehaviorModel().route(event)

        self.assertEqual(routed.tmux_ch, 5)
        self.assertEqual(routed.channel, 5)
        self.assertEqual(routed.cycle, 12)

    def test_awg_set_ramp_drop_and_final_hold(self):
        model = AxisAwgTuningBehaviorModel(n_pts=4, extra_y_pipe_stages=1)
        set_cmd = (1 << 144) | 1000
        ramp_cmd = (2 << 144) | 2000 | (8 << 64)
        result = model.run(32, [
            TimedCommandEvent(cycle=2, word=set_cmd),
            TimedCommandEvent(cycle=4, word=ramp_cmd),
            TimedCommandEvent(cycle=5, word=set_cmd),
        ])

        self.assertEqual(len(result.accepted_commands), 2)
        self.assertEqual(len(result.dropped_commands), 1)
        self.assertTrue(np.all(result.lane_samples[2] == 1000))
        self.assertTrue(np.all(result.lane_samples[4 + model.ramp_startup_latency_cycles + 2] == 2000))

    def test_signalgen_supported_and_unsupported_modes(self):
        cmd = (1000 << 96) | (8 << 128) | (1 << 144)
        model = AxisSignalGenV6BehaviorModel(n_dds=4)
        result = model.run(4, [TimedCommandEvent(cycle=1, word=cmd)])

        self.assertTrue(np.all(np.isfinite(result.lane_samples[1])))
        self.assertTrue(np.all(result.lane_samples[1] != 0))

        with self.assertRaises(UnsupportedModeError):
            AxisSignalGenV6BehaviorModel(n_dds=4, strict=True).accept_command(0, cmd | (1 << 146))

    def test_readout_and_avg_buffer(self):
        adc = RfdcAdcSourceModel(samples=[[1, 2], [3, 4]], n_lanes=2)
        readout = AxisDynReadoutV1BehaviorModel(n_dds=2, adc_source=adc)
        readout.accept_command(0, 2 << 64)
        self.assertEqual(len(readout.captured), 2)
        self.assertEqual(readout.captured[1]["sample"], [3, 4])

        avg = AxisAvgBufferV13BehaviorModel(accum_len=2)
        feedback = avg.capture(5, [pack_iq(1, 2), pack_iq(3, -4)])
        self.assertEqual(len(avg.raw_buffer), 2)
        self.assertEqual(len(avg.avg_memory), 1)
        self.assertEqual(feedback[0].word & ((1 << 64) - 1), 4)


if __name__ == "__main__":
    unittest.main()
