"""Simulation result containers and RFDC-facing output helpers."""

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .virtual_hw import install_pynq_stubs

install_pynq_stubs()

from qick.awg_tuning import CommandEvent, TimingConflict  # noqa: E402


def _sign_extend(value, bits):
    mask = (1 << int(bits)) - 1
    sign = 1 << (int(bits) - 1)
    value = int(value) & mask
    if value & sign:
        return value - (1 << int(bits))
    return value


def packed_words_to_lanes(words, n_lanes, bits=16, signed=True):
    """Convert RFDC packed words into ``(cycles, lanes)`` sample arrays."""
    words = np.asarray(words, dtype=object)
    lanes = np.zeros((len(words), int(n_lanes)), dtype=np.int64)
    mask = (1 << int(bits)) - 1
    for cycle, word in enumerate(words):
        word = int(word)
        for lane in range(int(n_lanes)):
            sample = (word >> (lane * int(bits))) & mask
            lanes[cycle, lane] = _sign_extend(sample, bits) if signed else sample
    return lanes


def lanes_to_sample_times(num_words, n_lanes, fs_mhz):
    """Return a ``(num_words, n_lanes)`` time axis in us for DAC samples."""
    sample_index = np.arange(int(num_words) * int(n_lanes), dtype=np.float64)
    if float(fs_mhz) <= 0:
        return np.zeros((int(num_words), int(n_lanes)), dtype=np.float64)
    return (sample_index / float(fs_mhz)).reshape((int(num_words), int(n_lanes)))


@dataclass
class RfdcOutput:
    """RFDC-facing packed/lane samples for one DAC input stream.

    The samples are digital words at the RFDC AXIS boundary. They do not model
    RFDC analog reconstruction, interpolation filters, or mixer spurs.
    """

    name: str
    dac: str
    source_path: str
    source_type: str
    packed_words: np.ndarray
    lane_samples: np.ndarray
    tvalid: np.ndarray
    n_lanes: int
    bits: int = 16
    dac_fs_mhz: float = 6144.0
    fabric_clk_mhz: float = 384.0
    tproc_clk_mhz: float = 250.0
    metadata: dict = field(default_factory=dict)

    @property
    def sample_times_us(self):
        return lanes_to_sample_times(len(self.packed_words), self.n_lanes, self.dac_fs_mhz)

    @property
    def fabric_times_us(self):
        if float(self.fabric_clk_mhz) <= 0:
            return np.zeros(len(self.packed_words), dtype=np.float64)
        return np.arange(len(self.packed_words), dtype=np.float64) / float(self.fabric_clk_mhz)

    def flattened_samples(self, samples=None, valid_only=False):
        lanes = np.asarray(self.lane_samples)
        valid = np.asarray(self.tvalid, dtype=bool)
        if valid_only:
            lanes = lanes[valid]
        flat = lanes.reshape(-1)
        if samples is not None:
            flat = flat[:int(samples)]
        return flat

    def flattened_times_us(self, samples=None, valid_only=False):
        times = self.sample_times_us
        valid = np.asarray(self.tvalid, dtype=bool)
        if valid_only:
            times = times[valid]
        flat = times.reshape(-1)
        if samples is not None:
            flat = flat[:int(samples)]
        return flat


@dataclass
class WaveformResult:
    """Output waveform and command log from hardware-free QICK simulation."""

    packed_words: np.ndarray
    lane_samples: np.ndarray
    command_events: list
    accepted_commands: list
    dropped_commands: list
    timing_conflicts: list
    channels: list = None
    channel_results: dict = None
    unsupported_ips: list = field(default_factory=list)
    unsupported_instructions: list = field(default_factory=list)
    unsupported_modes: list = field(default_factory=list)
    ip_events: list = field(default_factory=list)
    outputs: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        """Return a JSON-like dictionary with arrays converted to lists."""
        return {
            "packed_words": np.asarray(self.packed_words, dtype=object).tolist(),
            "lane_samples": np.asarray(self.lane_samples).tolist(),
            "command_events": [event.__dict__.copy() for event in self.command_events],
            "accepted_commands": [event.__dict__.copy() for event in self.accepted_commands],
            "dropped_commands": [event.__dict__.copy() for event in self.dropped_commands],
            "timing_conflicts": [event.__dict__.copy() for event in self.timing_conflicts],
            "channels": None if self.channels is None else list(self.channels),
            "unsupported_ips": list(self.unsupported_ips),
            "unsupported_instructions": list(self.unsupported_instructions),
            "unsupported_modes": list(self.unsupported_modes),
            "ip_events": [dict(event) for event in self.ip_events],
            "outputs": {
                name: {
                    "dac": out.dac,
                    "source_path": out.source_path,
                    "source_type": out.source_type,
                    "n_lanes": out.n_lanes,
                    "dac_fs_mhz": out.dac_fs_mhz,
                    "fabric_clk_mhz": out.fabric_clk_mhz,
                    "tproc_clk_mhz": out.tproc_clk_mhz,
                    "metadata": dict(out.metadata),
                }
                for name, out in self.outputs.items()
            },
            "metadata": dict(self.metadata),
        }

    def summary(self):
        """Return a compact count summary for tests and reports."""
        return {
            "cycles": int(np.asarray(self.packed_words).shape[0]) if self.packed_words is not None else 0,
            "commands": len(self.command_events),
            "accepted": len(self.accepted_commands),
            "dropped": len(self.dropped_commands),
            "timing_conflicts": len(self.timing_conflicts),
            "unsupported_ips": len(self.unsupported_ips),
            "unsupported_instructions": len(self.unsupported_instructions),
            "unsupported_modes": len(self.unsupported_modes),
            "ip_events": len(self.ip_events),
            "outputs": len(self.outputs),
        }

    def _resolve_output(self, name_or_dac):
        key = str(name_or_dac)
        if key in self.outputs:
            return self.outputs[key]
        matches = [out for out in self.outputs.values() if str(out.dac) == key]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise KeyError("no RFDC output named or mapped to %r" % (name_or_dac,))
        raise KeyError("multiple RFDC outputs match DAC %r; use the source name" % (name_or_dac,))

    def get_output_samples(self, name_or_dac, samples=None, valid_only=False):
        """Return lane-flattened samples for an output source name or DAC id."""
        return self._resolve_output(name_or_dac).flattened_samples(samples=samples, valid_only=valid_only)

    def get_output_words(self, name_or_dac, valid_only=False):
        """Return packed RFDC words for an output source name or DAC id."""
        out = self._resolve_output(name_or_dac)
        if valid_only:
            return np.asarray(out.packed_words, dtype=object)[np.asarray(out.tvalid, dtype=bool)]
        return np.asarray(out.packed_words, dtype=object)

    def plot_output(self, name_or_dac, samples=None, show=True, save=None, valid_only=False, ax=None):
        """Plot one lane-flattened RFDC-facing output versus DAC sample time."""
        try:
            import matplotlib.pyplot as plt
        except ImportError as exc:
            raise RuntimeError("matplotlib is required for RFDC output plotting") from exc

        out = self._resolve_output(name_or_dac)
        y = out.flattened_samples(samples=samples, valid_only=valid_only)
        x = out.flattened_times_us(samples=samples, valid_only=valid_only)
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 4))
        else:
            fig = ax.figure
        ax.plot(x, y, linewidth=1.2, label="%s DAC %s" % (out.name, out.dac))
        ax.set_xlabel("time (us)")
        ax.set_ylabel("RFDC digital sample")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
        fig.tight_layout()
        if save is not None:
            fig.savefig(save, dpi=150)
        if show:
            plt.show()
        return fig, ax

    def plot_dac(self, dac, samples=None, show=True, save=None, valid_only=False, ax=None):
        """Plot a DAC output by RFDC DAC id, such as ``'10'``."""
        return self.plot_output(dac, samples=samples, show=show, save=save, valid_only=valid_only, ax=ax)

    def plot_outputs(self, samples=None, channels=None, dac=None, overlay=False, show=True, save=None, valid_only=False):
        """Plot lane-flattened RFDC-facing outputs.

        Parameters use MHz-derived time axes configured on ``QickSim``.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError as exc:
            raise RuntimeError("matplotlib is required for RFDC output plotting") from exc

        names = list(self.outputs)
        if channels is not None:
            wanted = set(str(ch) for ch in channels)
            names = [name for name in names if name in wanted or self.outputs[name].dac in wanted]
        if dac is not None:
            wanted_dacs = {str(dac)} if isinstance(dac, (str, int)) else set(str(x) for x in dac)
            names = [name for name in names if self.outputs[name].dac in wanted_dacs]
        if not names:
            raise KeyError("no RFDC outputs match the requested filters")

        if overlay:
            fig, axes = plt.subplots(1, 1, figsize=(11, 4))
            axes = [axes]
        else:
            fig, axes = plt.subplots(len(names), 1, figsize=(11, max(3, 2.6 * len(names))), squeeze=False)
            axes = list(axes[:, 0])

        for idx, name in enumerate(names):
            out = self.outputs[name]
            ax = axes[0] if overlay else axes[idx]
            ax.plot(
                out.flattened_times_us(samples=samples, valid_only=valid_only),
                out.flattened_samples(samples=samples, valid_only=valid_only),
                linewidth=1.1,
                label="%s DAC %s" % (name, out.dac),
            )
            ax.set_ylabel("sample")
            ax.grid(True, alpha=0.3)
            ax.legend(loc="best")
        axes[-1].set_xlabel("time (us)")
        fig.tight_layout()
        if save is not None:
            fig.savefig(save, dpi=150)
        if show:
            plt.show()
        return fig, axes

    @staticmethod
    def _hex_word(word):
        return "0x%x" % int(word)

    @staticmethod
    def _safe_csv_path(path, overwrite):
        path = Path(path)
        if path.exists() and not overwrite:
            raise FileExistsError("refusing to overwrite existing CSV file: %s" % path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def to_csv(self, prefix, overwrite=False):
        """Write packed-word, lane-sample, and event CSV files.

        If RFDC outputs are present, files are emitted per output source using
        ``<prefix>_<source>_packed.csv`` and ``<prefix>_<source>_lanes.csv``.
        """
        prefix = Path(prefix)
        paths = {"packed": [], "lanes": [], "events": None}

        outputs = self.outputs
        if outputs:
            for name, out in outputs.items():
                safe_name = name.replace("/", "_")
                packed_path = self._safe_csv_path(prefix.with_name(prefix.name + "_" + safe_name + "_packed.csv"), overwrite)
                lane_path = self._safe_csv_path(prefix.with_name(prefix.name + "_" + safe_name + "_lanes.csv"), overwrite)
                with packed_path.open("w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["cycle", "word_index", "tvalid", "tready", "tdata_hex"])
                    writer.writeheader()
                    for cycle, word in enumerate(out.packed_words):
                        writer.writerow({
                            "cycle": cycle,
                            "word_index": cycle,
                            "tvalid": int(bool(out.tvalid[cycle])),
                            "tready": 1,
                            "tdata_hex": self._hex_word(word),
                        })
                with lane_path.open("w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["sample_index", "slow_word", "lane", "time_us", "value"])
                    writer.writeheader()
                    sample_index = 0
                    times = out.sample_times_us
                    for cycle in range(out.lane_samples.shape[0]):
                        for lane in range(out.n_lanes):
                            writer.writerow({
                                "sample_index": sample_index,
                                "slow_word": cycle,
                                "lane": lane,
                                "time_us": "%.12g" % float(times[cycle, lane]),
                                "value": int(out.lane_samples[cycle, lane]),
                            })
                            sample_index += 1
                paths["packed"].append(packed_path)
                paths["lanes"].append(lane_path)
        else:
            packed_path = self._safe_csv_path(prefix.with_name(prefix.name + "_packed.csv"), overwrite)
            lane_path = self._safe_csv_path(prefix.with_name(prefix.name + "_lanes.csv"), overwrite)
            packed = np.asarray(self.packed_words, dtype=object)
            lanes = np.asarray(self.lane_samples)
            with packed_path.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["cycle", "word_index", "tvalid", "tready", "tdata_hex"])
                writer.writeheader()
                for cycle, word in enumerate(packed.reshape(-1)):
                    writer.writerow({"cycle": cycle, "word_index": cycle, "tvalid": 1, "tready": 1, "tdata_hex": self._hex_word(word)})
            with lane_path.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["sample_index", "slow_word", "lane", "time_us", "value"])
                writer.writeheader()
                flat = lanes.reshape((-1, lanes.shape[-1])) if lanes.size else np.zeros((0, 0))
                for cycle in range(flat.shape[0]):
                    for lane in range(flat.shape[1]):
                        writer.writerow({"sample_index": cycle * flat.shape[1] + lane, "slow_word": cycle, "lane": lane, "time_us": "", "value": int(flat[cycle, lane])})
            paths["packed"].append(packed_path)
            paths["lanes"].append(lane_path)

        events_path = self._safe_csv_path(prefix.with_name(prefix.name + "_events.csv"), overwrite)
        with events_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["path", "label", "setting_cycle", "output_cycle", "delay_cycles", "detail"])
            writer.writeheader()
            for event in self.command_events:
                setting_cycle = event.decoded.get("source_cycle", event.cycle)
                output_cycle = event.output_cycle if event.output_cycle is not None else event.cycle
                writer.writerow({
                    "path": "gen%d" % event.channel,
                    "label": event.label or event.decoded.get("op", "cmd"),
                    "setting_cycle": setting_cycle,
                    "output_cycle": output_cycle,
                    "delay_cycles": output_cycle - setting_cycle,
                    "detail": event.reason or event.decoded.get("op", "cmd"),
                })
        paths["events"] = events_path
        return paths


SimulationResult = WaveformResult


__all__ = [
    "WaveformResult",
    "SimulationResult",
    "RfdcOutput",
    "packed_words_to_lanes",
    "lanes_to_sample_times",
]
