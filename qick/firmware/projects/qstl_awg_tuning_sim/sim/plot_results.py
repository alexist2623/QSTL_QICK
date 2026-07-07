#!/usr/bin/env python3
"""Plot qstl_awg_tuning_sim CSV outputs, including command-to-output latency."""
# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def read_x16(path: Path) -> tuple[list[int], list[int], list[int], list[int]]:
    rows = read_rows(path)
    sample_index = [int(row["sample_index"]) for row in rows]
    slow_word = [int(row["slow_word"]) for row in rows]
    lane = [int(row["lane"]) for row in rows]
    value = [int(row["value"]) for row in rows]
    return sample_index, slow_word, lane, value


def read_cycle_map(path: Path) -> dict[int, int]:
    return {
        int(row["word_index"]): int(row["cycle"])
        for row in read_rows(path)
    }


def cycle_x(slow_word: list[int], lane: list[int], cycle_map: dict[int, int]) -> list[float]:
    return [cycle_map[word] + lane_i / 16.0 for word, lane_i in zip(slow_word, lane)]


def event_rows(path: Path, stream: str) -> list[dict[str, str]]:
    return [row for row in read_rows(path) if row["path"] == stream]


def annotate_events(ax, events: list[dict[str, str]], y_values: list[int]) -> None:
    if not events:
        return

    y_min = min(y_values)
    y_max = max(y_values)
    span = max(1, y_max - y_min)
    y_levels = [y_max - span * frac for frac in (0.08, 0.18, 0.28, 0.38, 0.48)]

    for idx, row in enumerate(events):
        setting = int(row["setting_cycle"])
        output = int(row["output_cycle"])
        delay = int(row["delay_cycles"])
        label = row["label"]
        y = y_levels[idx % len(y_levels)]

        ax.axvline(setting, color="#d99000", linestyle="--", linewidth=1.0, alpha=0.75)
        ax.axvline(output, color="#c62828", linestyle="-", linewidth=1.0, alpha=0.75)

        if delay == 0:
            ax.text(output + 0.15, y, f"{label}: 0 cyc", fontsize=7, color="#5b3b00")
        else:
            ax.annotate(
                "",
                xy=(output, y),
                xytext=(setting, y),
                arrowprops={"arrowstyle": "<->", "color": "#5b3b00", "linewidth": 1.0},
            )
            ax.text(
                (setting + output) / 2.0,
                y,
                f"{label}: {delay} cyc",
                fontsize=7,
                ha="center",
                va="bottom",
                color="#5b3b00",
            )


def plot_sample_index(out_dir: Path, awg, siggen) -> None:
    awg_sample, _, _, awg_value = awg
    sig_sample, _, _, sig_value = siggen

    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=False)
    axes[0].plot(awg_sample, awg_value, linewidth=1.4, color="#1f77b4")
    axes[0].set_title("axis_awg_tuning_v1_4 x16 serialized output")
    axes[0].set_xlabel("sample_index")
    axes[0].set_ylabel("sample")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(sig_sample, sig_value, linewidth=1.4, color="#2ca02c")
    axes[1].set_title("real axis_signal_gen_v6_0 DDS-only x16 output, fout=25 MHz")
    axes[1].set_xlabel("sample_index")
    axes[1].set_ylabel("sample")
    axes[1].grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_dir / "qstl_awg_tuning_sim_x16_plot.png", dpi=150)
    plt.close(fig)


def plot_latency(out_dir: Path, awg, siggen, awg_cycles, siggen_cycles, events_path: Path) -> None:
    _, awg_words, awg_lanes, awg_value = awg
    _, sig_words, sig_lanes, sig_value = siggen
    awg_x = cycle_x(awg_words, awg_lanes, awg_cycles)
    sig_x = cycle_x(sig_words, sig_lanes, siggen_cycles)

    awg_events = event_rows(events_path, "awg")
    sig_events = event_rows(events_path, "siggen")

    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=False)
    axes[0].plot(awg_x, awg_value, linewidth=1.3, color="#1f77b4")
    axes[0].set_title("AWG command-to-output latency")
    axes[0].set_xlabel("aclk cycle, lane fraction")
    axes[0].set_ylabel("sample")
    axes[0].grid(True, alpha=0.3)
    annotate_events(axes[0], awg_events, awg_value)

    axes[1].plot(sig_x, sig_value, linewidth=1.3, color="#2ca02c")
    axes[1].set_title("axis_signal_gen_v6 s1_axis command-to-first-output latency")
    axes[1].set_xlabel("aclk cycle, lane fraction")
    axes[1].set_ylabel("sample")
    axes[1].grid(True, alpha=0.3)
    annotate_events(axes[1], sig_events, sig_value)

    for ax, events, x_vals in ((axes[0], awg_events, awg_x), (axes[1], sig_events, sig_x)):
        if events and x_vals:
            event_cycles = [int(row["setting_cycle"]) for row in events] + [int(row["output_cycle"]) for row in events]
            ax.set_xlim(min(min(x_vals), min(event_cycles)) - 2, max(max(x_vals), max(event_cycles)) + 2)

    fig.tight_layout()
    fig.savefig(out_dir / "qstl_awg_tuning_sim_latency_plot.png", dpi=150)
    plt.close(fig)


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    awg = read_x16(out_dir / "qstl_awg_tuning_sim_awg_x16.csv")
    siggen = read_x16(out_dir / "qstl_awg_tuning_sim_siggen_x16.csv")
    awg_cycles = read_cycle_map(out_dir / "qstl_awg_tuning_sim_awg_packed.csv")
    siggen_cycles = read_cycle_map(out_dir / "qstl_awg_tuning_sim_siggen_packed.csv")
    events_path = out_dir / "qstl_awg_tuning_sim_events.csv"

    plot_sample_index(out_dir, awg, siggen)
    plot_latency(out_dir, awg, siggen, awg_cycles, siggen_cycles, events_path)
    print(out_dir / "qstl_awg_tuning_sim_x16_plot.png")
    print(out_dir / "qstl_awg_tuning_sim_latency_plot.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
