"""Plot the already-asserted three required CPU/TMUX waveforms; no hardware."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot(build: Path):
    result = json.loads((build / "result.json").read_text(encoding="utf-8-sig"))
    if not result["passed"] or not result["complete"]:
        raise ValueError("A completed, passing full-CPU simulation is required")
    with (build / "required_waveforms.csv").open() as stream:
        rows = [{k: int(v) for k, v in r.items()} for r in csv.DictReader(stream)]
    definitions = [(20000, 1, 1, "rise1_hold1_fall1"), (22000, 1, 2, "rise1_hold2_fall1"), (34000, 2, 1, "rise2_hold1_fall2")]
    fig, axes = plt.subplots(3, 3, figsize=(15, 10), constrained_layout=True)
    for row_index, (base, rise, hold, name) in enumerate(definitions):
        for pair in range(3):
            selected = [r for r in rows if r["pair"] == pair and base + 30 <= r["tproc_clock"] <= base + 34 + 2 * rise + hold + 3]
            if not selected:
                raise ValueError(f"Missing required representative samples: {name}, pair {pair}")
            times = [(r["tproc_clock"] - base - 34 + r["lane"] / 16) * 10 / 3 for r in selected]
            ax = axes[row_index, pair]
            ax.plot(times, [r["awg_final"] for r in selected], label="AWG final (bypass)", lw=1.4)
            ax.plot(times, [r["combined"] for r in selected], "--", label="AWG + DDS final", lw=1)
            for boundary in (0, rise * 10 / 3, (rise + hold) * 10 / 3, (2 * rise + hold) * 10 / 3):
                ax.axvline(boundary, color="0.7", lw=.6)
            ax.set_title(f"{name}, pair {pair}")
            ax.set_xlabel("Time from requested output start (ns)")
            ax.set_ylabel("DAC code")
            ax.grid(alpha=.25)
            if row_index == 0 and pair == 0:
                ax.legend(fontsize=8)
    path = build / "required_waveforms.png"
    if path.exists():
        raise FileExistsError(path)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    plot(parser.parse_args().build)
