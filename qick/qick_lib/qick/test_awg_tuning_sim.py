"""Pure-Python tests for the axis_awg_tuning_v1 behavior simulator."""

import sys
import tempfile
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
    AwgTuningBehaviorModel,
    AxisAwgTuningV1,
    TimedCommandEvent,
    TProcTimedEventSimulator,
)


def make_driver(n_pts=4, extra_y_pipe_stages=1):
    return AxisAwgTuningV1({
        "type": "QICK:QICK:axis_awg_tuning_v1:1.0",
        "fullpath": "axis_awg_tuning_v1_0",
        "parameters": {
            "N_PTS": str(n_pts),
            "B": "16",
            "FRAC": "16",
            "CMD_WIDTH": "160",
            "STEP_WIDTH": "24",
            "DURATION_WIDTH": "23",
            "EXTRA_Y_PIPE_STAGES": str(extra_y_pipe_stages),
        },
    })


def independent_clip(value, b=16, invalid_lsb=2):
    maxv = ((1 << (b - 1)) - 1) & ~((1 << invalid_lsb) - 1)
    minv = -(1 << (b - 1))
    value = max(minv, min(maxv, int(value)))
    return value & ~((1 << invalid_lsb) - 1)


def independent_pack(samples, b=16):
    word = 0
    mask = (1 << b) - 1
    for lane, sample in enumerate(samples):
        word |= (int(sample) & mask) << (lane * b)
    return word


def independent_expected_ramp_word(start, target, duration, step, base_index, n_pts=4, frac=16):
    duration = 1 if duration == 0 else duration
    samples = []
    for lane in range(n_pts):
        sample_index = base_index + lane
        if duration <= 1 or sample_index >= duration - 1:
            sample = independent_clip(target)
        else:
            fixed_value = (int(start) << frac) + int(step) * sample_index
            sample = independent_clip(fixed_value >> frac)
        samples.append(sample)
    return independent_pack(samples)


class TestAwgTuningBehaviorModel(unittest.TestCase):
    def test_set_waveform(self):
        drv = make_driver()
        model = AwgTuningBehaviorModel(n_pts=4, extra_y_pipe_stages=1)
        cmd = drv.set_cmd(1000)

        result = model.run(10, [TimedCommandEvent(cycle=5, word=cmd, label="set 1000")])

        self.assertEqual(len(result.accepted_commands), 1)
        self.assertEqual(result.accepted_commands[0].cycle, 5)
        self.assertTrue(np.all(result.lane_samples[5] == 1000))
        self.assertTrue(np.all(result.lane_samples[6] == 1000))
        self.assertEqual(model.current_value, 1000)

    def test_set_hold_zero(self):
        drv = make_driver()
        model = AwgTuningBehaviorModel(n_pts=4, extra_y_pipe_stages=1)
        cmd = drv.set_cmd(1000, hold_zero=True)

        result = model.run(8, [TimedCommandEvent(cycle=3, word=cmd, label="set zero hold")])

        self.assertTrue(np.all(result.lane_samples[3] == 1000))
        self.assertTrue(np.all(result.lane_samples[4] == 0))
        self.assertEqual(model.current_value, 0)

    def test_ramp_waveform(self):
        drv = make_driver()
        drv.reset_cache(0, valid=True)
        model = AwgTuningBehaviorModel(n_pts=4, extra_y_pipe_stages=1)
        cmd = drv.ramp_cmd(1600, 17)
        decoded = drv.format_cmd(cmd)
        start_cycle = 5
        first_cycle = start_cycle + model.ramp_startup_latency_cycles
        n_words = (17 + model.n_pts - 1) // model.n_pts

        result = model.run(25, [TimedCommandEvent(cycle=start_cycle, word=cmd, label="ramp 1600")])

        for word_idx in range(n_words):
            base_index = word_idx * model.n_pts
            expected = model.unpack_lanes(
                model.expected_ramp_word(0, 1600, 17, decoded["step"], base_index)
            )
            self.assertEqual(result.lane_samples[first_cycle + word_idx].tolist(), expected)
        self.assertTrue(np.all(result.lane_samples[first_cycle + n_words] == 1600))
        self.assertEqual(model.current_value, 1600)

    def test_negative_ramp_and_invalid_requested_short_case(self):
        drv = make_driver()
        with self.assertRaises(ValueError):
            drv.calc_step(2000, -2000, 24)

        drv.reset_cache(2000, valid=True)
        model = AwgTuningBehaviorModel(n_pts=4, extra_y_pipe_stages=1)
        set_cmd = drv.set_cmd(2000)
        drv.reset_cache(2000, valid=True)
        ramp_cmd = drv.ramp_cmd(-2000, 64)
        decoded = drv.format_cmd(ramp_cmd)
        numerator = (-2000 - 2000) << drv["frac"]
        self.assertEqual(decoded["step"], -(abs(numerator) // 63))
        self.assertNotEqual(decoded["step"], numerator // 63)

        result = model.run(30, [
            TimedCommandEvent(cycle=1, word=set_cmd, label="set 2000"),
            TimedCommandEvent(cycle=2, word=ramp_cmd, label="ramp -2000"),
        ])

        first_cycle = 2 + model.ramp_startup_latency_cycles
        expected = model.unpack_lanes(model.expected_ramp_word(2000, -2000, 64, decoded["step"], 0))
        self.assertEqual(result.lane_samples[first_cycle].tolist(), expected)

    def test_duration_zero_normalizes_to_one(self):
        drv = make_driver()
        drv.reset_cache(0, valid=True)
        model = AwgTuningBehaviorModel(n_pts=4, extra_y_pipe_stages=1)
        cmd = drv.ramp_cmd(1234, 0)
        start_cycle = 3
        first_cycle = start_cycle + model.ramp_startup_latency_cycles

        result = model.run(15, [TimedCommandEvent(cycle=start_cycle, word=cmd, label="duration 0")])

        self.assertTrue(np.all(result.lane_samples[first_cycle] == independent_clip(1234)))
        self.assertTrue(np.all(result.lane_samples[first_cycle + 1] == independent_clip(1234)))
        self.assertEqual(result.accepted_commands[0].decoded["effective_duration"], 1)

    def test_dropped_command_during_ramp(self):
        drv = make_driver()
        drv.reset_cache(0, valid=True)
        ramp_cmd = drv.ramp_cmd(1600, 64)
        set_cmd = drv.set_cmd(3000)
        model = AwgTuningBehaviorModel(n_pts=4, extra_y_pipe_stages=1)

        result = model.run(20, [
            TimedCommandEvent(cycle=10, word=ramp_cmd, label="long ramp"),
            TimedCommandEvent(cycle=11, word=set_cmd, label="dropped set"),
        ])

        self.assertEqual(len(result.dropped_commands), 1)
        self.assertEqual(result.dropped_commands[0].cycle, 11)
        self.assertEqual(result.dropped_commands[0].reason, "dropped_during_ramp")
        self.assertTrue(np.all(result.lane_samples[11] == 0))

    def test_tmux_routing_latency(self):
        drv = make_driver()
        cmd = drv.set_cmd(1000)
        sim = TProcTimedEventSimulator(num_channels=2, n_pts=4, extra_y_pipe_stages=1)

        result = sim.run(25, [
            TimedCommandEvent(cycle=20, word=cmd, tmux_ch=1, label="tmux set ch1"),
        ])

        self.assertEqual(len(result.channel_results[1].accepted_commands), 1)
        event = result.channel_results[1].accepted_commands[0]
        self.assertEqual(event.cycle, 22)
        self.assertEqual(event.decoded["source_cycle"], 20)
        self.assertEqual(event.decoded["route_latency"], 2)
        self.assertEqual(len(result.channel_results[0].accepted_commands), 0)
        self.assertTrue(np.all(result.lane_samples[22, 1] == 1000))

    def test_no_tmux_direct_event_has_no_delay(self):
        drv = make_driver()
        cmd = drv.set_cmd(1000)
        sim = TProcTimedEventSimulator(num_channels=1, n_pts=4, extra_y_pipe_stages=1)

        result = sim.run(10, [TimedCommandEvent(cycle=5, word=cmd, channel=0, label="direct")])

        self.assertEqual(result.accepted_commands[0].cycle, 5)
        self.assertTrue(np.all(result.lane_samples[5] == 1000))

    def test_packed_word_lane_conversion(self):
        model = AwgTuningBehaviorModel(n_pts=16)
        samples = [-4, 0, 4, -8] + [i * 4 for i in range(12)]
        word = model.pack_lanes(samples)
        self.assertEqual(model.unpack_lanes(word), samples)

    def test_expected_ramp_word_matches_independent_formula(self):
        model = AwgTuningBehaviorModel(n_pts=4, extra_y_pipe_stages=3)
        cases = [
            (0, 1600, 17, 6168094, 0),
            (0, 1600, 17, 6168094, 16),
            (2000, -2000, 64, -4161015, 20),
            (1000, 1234, 0, 0, 0),
        ]
        for start, target, duration, step, base in cases:
            self.assertEqual(
                model.expected_ramp_word(start, target, duration, step, base),
                independent_expected_ramp_word(start, target, duration, step, base),
            )

    def test_from_program_subset_extracts_awg_set(self):
        drv = make_driver()
        cmd = drv.set_cmd(1000)
        words = drv.cmd_to_words(cmd)
        words[4] |= 1 << 24
        prog = types.SimpleNamespace(prog_list=[
            {"name": "regwi", "args": (0, 26, words[0])},
            {"name": "regwi", "args": (0, 27, words[1])},
            {"name": "regwi", "args": (0, 28, words[2])},
            {"name": "regwi", "args": (0, 29, words[3])},
            {"name": "regwi", "args": (0, 30, words[4])},
            {"name": "regwi", "args": (0, 31, 20)},
            {"name": "set", "args": (1, 0, 26, 27, 28, 29, 30, 31)},
        ])

        sim = TProcTimedEventSimulator.from_program(
            prog,
            {"gens": [{}, {}]},
            cycles=25,
            n_pts=4,
            extra_y_pipe_stages=1,
        )
        result = sim.run()

        event = result.channel_results[1].accepted_commands[0]
        self.assertEqual(event.cycle, 22)
        self.assertEqual(event.decoded["source_cycle"], 20)
        self.assertEqual(event.decoded["route_latency"], 2)
        self.assertTrue(np.all(result.lane_samples[22, 1] == 1000))

    def test_csv_export_writes_expected_files(self):
        drv = make_driver()
        cmd = drv.set_cmd(1000)
        model = AwgTuningBehaviorModel(n_pts=4, extra_y_pipe_stages=1)
        result = model.run(8, [TimedCommandEvent(cycle=2, word=cmd, label="csv set")])

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = result.to_csv(Path(tmpdir) / "awg_model")
            for path in paths.values():
                self.assertTrue(path.exists())
                self.assertGreater(path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
