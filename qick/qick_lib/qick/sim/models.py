"""Behavior models for QICK simulation.

The public user API is :class:`qick.sim.QickSim`. These model classes are kept
internal so tests and advanced debugging can exercise individual IP behavior.
"""

import math

import numpy as np

from .exceptions import UnsupportedModeError
from .results import RfdcOutput, WaveformResult, packed_words_to_lanes
from .virtual_hw import install_pynq_stubs

install_pynq_stubs()

from qick.awg_tuning import (  # noqa: E402
    AwgTuningBehaviorModel as _AwgTuningBehaviorModel,
    AxisAvgBufferV13BehaviorModel as _AxisAvgBufferV13BehaviorModel,
    AxisBroadcasterBehaviorModel as _AxisBroadcasterBehaviorModel,
    AxisClockConverterBehaviorModel as _AxisClockConverterBehaviorModel,
    AxisDynReadoutV1BehaviorModel as _AxisDynReadoutV1BehaviorModel,
    AxisRegisterSliceBehaviorModel as _AxisRegisterSliceBehaviorModel,
    AxisSignalGenV6BehaviorModel as _AxisSignalGenV6BehaviorModel,
    AxisSwitchBehaviorModel as _AxisSwitchBehaviorModel,
    AxisTmuxV1BehaviorModel as _AxisTmuxV1BehaviorModel,
    CommandEvent,
    RfdcAdcSourceModel,
    TimedCommandEvent,
)


class AxisAwgTuningBehaviorModel(_AwgTuningBehaviorModel):
    """qick.sim wrapper for the AWG tuning behavior model."""


class AxisTmuxV1BehaviorModel(_AxisTmuxV1BehaviorModel):
    """qick.sim wrapper for the axis_tmux_v1 behavior model."""


class AxisRegisterSliceBehaviorModel(_AxisRegisterSliceBehaviorModel):
    """qick.sim wrapper for AXIS register slices."""


class AxisRegisterSliceNbBehaviorModel(_AxisRegisterSliceBehaviorModel):
    """qick.sim wrapper for QICK non-blocking AXIS register slices."""


class AxisSwitchBehaviorModel(_AxisSwitchBehaviorModel):
    """qick.sim wrapper for AXIS switches."""


class AxisBroadcasterBehaviorModel(_AxisBroadcasterBehaviorModel):
    """qick.sim wrapper for AXIS broadcasters."""


class AxisClockConverterBehaviorModel(_AxisClockConverterBehaviorModel):
    """qick.sim wrapper for AXIS clock converters."""


class RfdcDacSinkModel:
    """Collect RFDC-facing packed words and lane samples for one DAC input."""

    def __init__(self, name, dac, source_path, source_type, n_lanes=16, bits=16,
                 dac_fs_mhz=6144.0, fabric_clk_mhz=384.0, tproc_clk_mhz=250.0,
                 metadata=None):
        self.name = str(name)
        self.dac = str(dac)
        self.source_path = str(source_path)
        self.source_type = str(source_type)
        self.n_lanes = int(n_lanes)
        self.bits = int(bits)
        self.dac_fs_mhz = float(dac_fs_mhz)
        self.fabric_clk_mhz = float(fabric_clk_mhz)
        self.tproc_clk_mhz = float(tproc_clk_mhz)
        self.metadata = {} if metadata is None else dict(metadata)

    def collect(self, packed_words, tvalid=None):
        packed_words = np.asarray(packed_words, dtype=object)
        if tvalid is None:
            tvalid = np.ones(len(packed_words), dtype=bool)
        else:
            tvalid = np.asarray(tvalid, dtype=bool)
        lanes = packed_words_to_lanes(packed_words, self.n_lanes, bits=self.bits, signed=True)
        return RfdcOutput(
            name=self.name,
            dac=self.dac,
            source_path=self.source_path,
            source_type=self.source_type,
            packed_words=packed_words,
            lane_samples=lanes,
            tvalid=tvalid,
            n_lanes=self.n_lanes,
            bits=self.bits,
            dac_fs_mhz=self.dac_fs_mhz,
            fabric_clk_mhz=self.fabric_clk_mhz,
            tproc_clk_mhz=self.tproc_clk_mhz,
            metadata=dict(self.metadata),
        )


class AxisSignalGenV6BehaviorModel(_AxisSignalGenV6BehaviorModel):
    """Approximate RFDC-facing model for ``axis_signal_gen_v6``.

    The DDS path is deterministic and phase/frequency correct at the command
    level, but it is not a bit-exact model of the Xilinx DDS Compiler.
    """

    def __init__(self, n_dds=16, b=16, strict=True, latency=0, name="axis_signal_gen_v6",
                 channel=0, memory=None):
        super().__init__(n_dds=n_dds, b=b, strict=strict, latency=latency, name=name)
        self.channel = int(channel)
        self.memory = {} if memory is None else dict(memory)
        self._valid_cycles = set()
        self._steady_zero = True

    @staticmethod
    def _s16(value):
        return _AwgTuningBehaviorModel._sign_extend(value, 16)

    @staticmethod
    def _clip16(value):
        return max(-(1 << 15), min((1 << 15) - 1, int(value)))

    @staticmethod
    def _gain_mul(source, gain):
        product = int(source) * int(gain)
        # RTL uses prodg_y_full_real_r[30 -: 16], equivalent to signed >> 15
        # for the modeled 16x16 product range.
        return AxisSignalGenV6BehaviorModel._clip16(product >> 15)

    def load_memory(self, words, addr=0):
        for offset, word in enumerate(np.asarray(words).reshape(-1)):
            word = int(word)
            i_val = self._s16(word & 0xFFFF)
            q_val = self._s16((word >> 16) & 0xFFFF)
            self.memory[int(addr) + offset] = (i_val, q_val)

    def _dds_iq(self, decoded, sample_index):
        phase_word = (int(decoded["phase"]) + int(decoded["freq"]) * int(sample_index)) & 0xFFFFFFFF
        angle = (phase_word / float(1 << 32)) * 2.0 * math.pi
        i_val = self._clip16(int(round(math.cos(angle) * ((1 << 15) - 1))))
        q_val = self._clip16(int(round(math.sin(angle) * ((1 << 15) - 1))))
        return i_val, q_val

    def _memory_iq(self, decoded, sample_index):
        addr = int(decoded["addr"]) + int(sample_index)
        return self.memory.get(addr, (0, 0))

    def _source_sample(self, decoded, sample_index):
        outsel = int(decoded["outsel"])
        dds_i, dds_q = self._dds_iq(decoded, sample_index)
        mem_i, mem_q = self._memory_iq(decoded, sample_index)
        if outsel == 0:
            source = ((dds_i * mem_i) - (dds_q * mem_q)) >> 15
        elif outsel == 1:
            source = dds_i
        elif outsel == 2:
            source = mem_i
        elif outsel == 3:
            source = 0
        else:
            source = 0
        return self._gain_mul(source, decoded["gain"])

    def _pack_samples(self, samples):
        word = 0
        mask = (1 << self.b) - 1
        for idx, sample in enumerate(samples):
            word |= (int(sample) & mask) << (idx * self.b)
        return word

    def accept_command(self, cycle, cmd, label=None):
        decoded = self.decode_command(cmd)
        event = CommandEvent(
            cycle=int(cycle),
            channel=self.channel,
            raw_command=int(cmd),
            decoded=decoded,
            label=label,
            output_cycle=int(cycle) + self.latency,
        )
        self.command_events.append(event)

        if decoded["mode"]:
            msg = "%s periodic mode is not modeled bit-exactly" % self.name
            self.unsupported_modes.append(msg)
            if self.strict:
                raise UnsupportedModeError(msg)

        nsamp_words = max(1, int(decoded["nsamp"]))
        self._steady_zero = bool(decoded["stdysel"])
        for word_idx in range(nsamp_words):
            samples = [
                self._source_sample(decoded, word_idx * self.n_dds + lane)
                for lane in range(self.n_dds)
            ]
            out_cycle = int(cycle) + self.latency + word_idx
            self._outputs[out_cycle] = self._pack_samples(samples)
            self._valid_cycles.add(out_cycle)
        return event

    def step(self, cycle):
        cycle = int(cycle)
        if cycle in self._outputs:
            self._last_word = self._outputs[cycle]
            return self._last_word
        return 0 if self._steady_zero else self._last_word

    def run(self, cycles, events=None):
        events = [] if events is None else list(events)
        by_cycle = {}
        for event in events:
            by_cycle.setdefault(int(event.cycle), []).append(event)
        packed = []
        lane_model = _AwgTuningBehaviorModel(n_pts=self.n_dds, b=self.b)
        lanes = []
        for cycle in range(int(cycles)):
            for event in by_cycle.get(cycle, []):
                self.accept_command(cycle, event.word, event.label)
            word = self.step(cycle)
            packed.append(word)
            lanes.append(lane_model.unpack_lanes(word))
        return WaveformResult(
            packed_words=np.array(packed, dtype=object),
            lane_samples=np.array(lanes, dtype=np.int64),
            command_events=list(self.command_events),
            accepted_commands=list(self.command_events),
            dropped_commands=[],
            timing_conflicts=[],
            unsupported_modes=list(self.unsupported_modes),
            channels=[self.channel],
        )


class AxisDynReadoutV1BehaviorModel(_AxisDynReadoutV1BehaviorModel):
    """qick.sim wrapper for axis_dyn_readout_v1 behavior."""


class AxisAvgBufferV13BehaviorModel(_AxisAvgBufferV13BehaviorModel):
    """qick.sim wrapper for axis_avg_buffer v1.3 behavior."""

__all__ = [
    "TimedCommandEvent",
    "AxisAwgTuningBehaviorModel",
    "AxisTmuxV1BehaviorModel",
    "AxisRegisterSliceBehaviorModel",
    "AxisRegisterSliceNbBehaviorModel",
    "AxisSwitchBehaviorModel",
    "AxisBroadcasterBehaviorModel",
    "AxisClockConverterBehaviorModel",
    "RfdcDacSinkModel",
    "RfdcAdcSourceModel",
    "AxisSignalGenV6BehaviorModel",
    "AxisDynReadoutV1BehaviorModel",
    "AxisAvgBufferV13BehaviorModel",
]
