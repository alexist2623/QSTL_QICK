"""Simulation result containers and RFDC-facing output helpers."""
# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

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
    dac_fs_mhz: float = 300.0
    fabric_clk_mhz: float = 300.0
    tproc_clk_mhz: float = 300.0
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
        self._annotate_pulse_segments(ax, out, samples=samples, valid_only=valid_only)
        self._annotate_plot_window(ax, out, samples=samples, valid_only=valid_only)
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
            if not overlay:
                self._annotate_pulse_segments(ax, out, samples=samples, valid_only=valid_only)
                self._annotate_plot_window(ax, out, samples=samples, valid_only=valid_only)
        if overlay:
            self._annotate_pulse_segments(axes[0], [self.outputs[name] for name in names], samples=samples, valid_only=valid_only)
            self._annotate_overlay_window(axes[0], [self.outputs[name] for name in names], samples=samples, valid_only=valid_only)
        axes[-1].set_xlabel("time (us)")
        fig.tight_layout()
        if save is not None:
            fig.savefig(save, dpi=150)
        if show:
            plt.show()
        return fig, axes

    @staticmethod
    def _format_time_us(value):
        return "%.6g" % float(value)

    def _plot_window_info(self, out, samples=None, valid_only=False):
        times = out.flattened_times_us(samples=samples, valid_only=valid_only)
        sample_count = int(len(times))
        if sample_count == 0:
            return {
                "samples": 0,
                "cycle_start": None,
                "cycle_stop": None,
                "cycles": 0,
                "time_start_us": None,
                "time_stop_us": None,
                "time_span_us": 0.0,
            }

        word_count = int((sample_count + int(out.n_lanes) - 1) // int(out.n_lanes))
        if valid_only:
            word_indices = np.flatnonzero(np.asarray(out.tvalid, dtype=bool))
        else:
            word_indices = np.arange(len(out.packed_words), dtype=np.int64)
        word_indices = word_indices[:word_count]
        cycle_start = int(word_indices[0]) if len(word_indices) else None
        cycle_stop = int(word_indices[-1]) if len(word_indices) else None
        time_start = float(times[0])
        time_stop = float(times[-1])

        return {
            "samples": sample_count,
            "cycle_start": cycle_start,
            "cycle_stop": cycle_stop,
            "cycles": word_count,
            "time_start_us": time_start,
            "time_stop_us": time_stop,
            "time_span_us": max(0.0, time_stop - time_start),
        }

    def _plot_window_label(self, out, samples=None, valid_only=False, include_name=False):
        info = self._plot_window_info(out, samples=samples, valid_only=valid_only)
        prefix = "%s DAC %s: " % (out.name, out.dac) if include_name else ""
        if info["samples"] == 0:
            return prefix + "samples=0, fabric cycles=0, time=0 us"

        cycle_start = info["cycle_start"]
        cycle_stop = info["cycle_stop"]
        cycle_range = "%d-%d" % (cycle_start, cycle_stop) if cycle_start is not None else "n/a"
        return (
            prefix
            + "samples=%d, fabric cycles=%s (%d), time=%s-%s us (span %s us)"
            % (
                info["samples"],
                cycle_range,
                info["cycles"],
                self._format_time_us(info["time_start_us"]),
                self._format_time_us(info["time_stop_us"]),
                self._format_time_us(info["time_span_us"]),
            )
        )

    def _annotate_plot_window(self, ax, out, samples=None, valid_only=False):
        ax.text(
            0.01,
            0.98,
            self._plot_window_label(out, samples=samples, valid_only=valid_only),
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=9,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "0.7", "alpha": 0.85},
        )

    def _annotate_overlay_window(self, ax, outputs, samples=None, valid_only=False):
        label = "\n".join(
            self._plot_window_label(out, samples=samples, valid_only=valid_only, include_name=True)
            for out in outputs
        )
        ax.text(
            0.01,
            0.98,
            label,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "0.7", "alpha": 0.85},
        )

    def _output_events(self, out):
        gen_index = out.metadata.get("gen_index")
        if gen_index is None:
            return []
        events = [
            event
            for event in self.accepted_commands
            if getattr(event, "channel", None) is not None and int(event.channel) == int(gen_index)
        ]
        return sorted(events, key=lambda event: int(event.output_cycle if event.output_cycle is not None else event.cycle))

    @staticmethod
    def _event_kind(event):
        decoded = getattr(event, "decoded", {}) or {}
        if "op" in decoded:
            return str(decoded.get("op"))
        if "nsamp" in decoded:
            return "pulse"
        return "command"

    @staticmethod
    def _event_words(event, fallback_words):
        decoded = getattr(event, "decoded", {}) or {}
        if "n_output_words" in decoded:
            return max(1, int(decoded["n_output_words"]))
        if "nsamp" in decoded:
            return max(1, int(decoded["nsamp"]))
        if fallback_words is not None:
            return max(1, int(fallback_words))
        return 1

    def _visible_word_range(self, out, samples=None, valid_only=False):
        info = self._plot_window_info(out, samples=samples, valid_only=valid_only)
        if info["cycle_start"] is None or info["cycle_stop"] is None:
            return None
        return int(info["cycle_start"]), int(info["cycle_stop"])

    def _event_segments_for_output(self, out, samples=None, valid_only=False):
        visible = self._visible_word_range(out, samples=samples, valid_only=valid_only)
        if visible is None:
            return []
        visible_start, visible_stop = visible
        events = self._output_events(out)
        segments = []
        for idx, event in enumerate(events):
            start = int(event.output_cycle if event.output_cycle is not None else event.cycle)
            next_start = None
            if idx + 1 < len(events):
                next_event = events[idx + 1]
                next_start = int(next_event.output_cycle if next_event.output_cycle is not None else next_event.cycle)

            fallback_words = None
            if self._event_kind(event) in {"set", "idle", "nop", "command"}:
                if next_start is not None and next_start > start:
                    fallback_words = next_start - start
                else:
                    fallback_words = visible_stop - start + 1

            words = self._event_words(event, fallback_words=fallback_words)
            stop = start + words - 1
            clipped_start = max(start, visible_start)
            clipped_stop = min(stop, visible_stop)
            if clipped_stop < clipped_start:
                continue

            x0 = self._word_sample_time_us(out, clipped_start)
            x1 = self._word_sample_time_us(out, clipped_stop + 1)
            if x1 <= x0:
                x1 = self._word_sample_time_us(out, clipped_stop) + self._sample_period_us(out)

            segment = {
                "index": len(segments) + 1,
                "event": event,
                "kind": self._event_kind(event),
                "cycle_start": clipped_start,
                "cycle_stop": clipped_stop,
                "cycles": clipped_stop - clipped_start + 1,
                "x0": x0,
                "x1": x1,
                "time_start_us": x0,
                "time_stop_us": x1,
            }
            segments.append(segment)
        return segments

    @staticmethod
    def _sample_period_us(out):
        if float(out.dac_fs_mhz) <= 0:
            return 0.0
        return 1.0 / float(out.dac_fs_mhz)

    def _word_sample_time_us(self, out, word_index):
        if float(out.dac_fs_mhz) <= 0:
            return 0.0
        return (int(word_index) * int(out.n_lanes)) / float(out.dac_fs_mhz)

    def _pulse_segment_label(self, segment, include_name=None):
        event = segment["event"]
        label = getattr(event, "label", None)
        kind = segment["kind"]
        name = ("%s " % include_name) if include_name else ""
        title = label if label else kind
        return (
            "%spulse %d: %s\ncycles=%d-%d (%d)\ntime=%s-%s us"
            % (
                name,
                segment["index"],
                title,
                segment["cycle_start"],
                segment["cycle_stop"],
                segment["cycles"],
                self._format_time_us(segment["time_start_us"]),
                self._format_time_us(segment["time_stop_us"]),
            )
        )

    def _annotate_pulse_segments(self, ax, outputs, samples=None, valid_only=False):
        if not isinstance(outputs, (list, tuple)):
            outputs = [outputs]
        colors = ["#dbeafe", "#dcfce7", "#fef3c7", "#fce7f3", "#ede9fe", "#e0f2fe"]
        total_segments = []
        for out_idx, out in enumerate(outputs):
            for segment in self._event_segments_for_output(out, samples=samples, valid_only=valid_only):
                segment["out"] = out
                segment["color"] = colors[(segment["index"] + out_idx - 1) % len(colors)]
                total_segments.append(segment)
        if not total_segments:
            return

        y_positions = [0.86, 0.72, 0.58]
        for idx, segment in enumerate(total_segments):
            ax.axvspan(segment["x0"], segment["x1"], color=segment["color"], alpha=0.28, linewidth=0)
            x_mid = (segment["x0"] + segment["x1"]) / 2.0
            include_name = segment["out"].name if len(outputs) > 1 else None
            ax.text(
                x_mid,
                y_positions[idx % len(y_positions)],
                self._pulse_segment_label(segment, include_name=include_name),
                transform=ax.get_xaxis_transform(),
                ha="center",
                va="top",
                fontsize=8,
                bbox={
                    "boxstyle": "round,pad=0.25",
                    "facecolor": "white",
                    "edgecolor": "0.65",
                    "alpha": 0.82,
                },
            )

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
