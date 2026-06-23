"""Draw axis_awg_tuning_v1 RAMP pipeline timing diagrams.

The diagrams are generated from the current branch semantics:

* The implemented RTL has only IDLE_ST and RAMP_ST.
* The implemented RTL uses the command step field in bits 127:96.
* The old calc_ramp_step() divider path is not present in the current RTL.
* The implemented RAMP path has command/product/add-saturate/word pipeline
  registers and a four-cycle command-to-first-ramp-word latency.

Run from the repository root:

    python qick/firmware/ip/axis_awg_tuning_v1/doc/draw_awg_tuning_pipeline.py

or from this doc directory:

    python draw_awg_tuning_pipeline.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


DOC_DIR = Path(__file__).resolve().parent


COLORS = {
    "reg": "#d9ecff",
    "wire": "#fff4cc",
    "state": "#dff3df",
    "out": "#eadcff",
    "hold": "#eeeeee",
    "warn": "#ffd6d6",
    "note": "#f8f8f8",
    "proposed": "#d8f5ef",
}


def draw_box(
    ax,
    x: float,
    y: float,
    text: str,
    *,
    width: float = 0.92,
    height: float = 0.72,
    facecolor: str = COLORS["reg"],
    edgecolor: str = "#333333",
    fontsize: int = 8,
    linewidth: float = 1.0,
    alpha: float = 1.0,
) -> None:
    """Draw a rounded timing box centered on x/y."""
    box = FancyBboxPatch(
        (x - width / 2.0, y - height / 2.0),
        width,
        height,
        boxstyle="round,pad=0.035,rounding_size=0.04",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=linewidth,
        alpha=alpha,
    )
    ax.add_patch(box)
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize, wrap=True)


def draw_arrow(
    ax,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    color: str = "#444444",
    text: str | None = None,
    fontsize: int = 8,
    linestyle: str = "-",
    linewidth: float = 1.4,
    rad: float = 0.0,
) -> None:
    """Draw an arrow, optionally with a label near the midpoint."""
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops={
            "arrowstyle": "->",
            "color": color,
            "linewidth": linewidth,
            "linestyle": linestyle,
            "connectionstyle": f"arc3,rad={rad}",
            "shrinkA": 8,
            "shrinkB": 8,
        },
    )
    if text:
        ax.text(
            (x0 + x1) / 2.0,
            (y0 + y1) / 2.0 + 0.16,
            text,
            ha="center",
            va="bottom",
            fontsize=fontsize,
            color=color,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.75, "pad": 1.0},
        )


def setup_axes(ax, title: str, columns: list[str], rows: list[str]) -> dict[str, int]:
    """Create common clock-cycle axes and return row y positions."""
    y_pos = {row: len(rows) - i for i, row in enumerate(rows)}
    ax.set_title(title, fontsize=17, fontweight="bold", pad=18)

    for x, label in enumerate(columns):
        ax.text(x, len(rows) + 1.15, label, ha="center", va="bottom", fontsize=11, fontweight="bold")
        ax.axvline(x, color="#cccccc", linewidth=0.8, zorder=0)

    for row, y in y_pos.items():
        ax.text(-1.05, y, row, ha="right", va="center", fontsize=10, fontweight="bold")
        ax.axhline(y, color="#eeeeee", linewidth=0.8, zorder=0)

    ax.set_xlim(-1.25, len(columns) - 0.35)
    ax.set_ylim(0.25, len(rows) + 1.65)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_frame_on(False)
    return y_pos


def save_figure(fig, stem: str) -> None:
    """Save PNG and SVG output with deterministic layout."""
    for suffix in (".png", ".svg"):
        fig.savefig(DOC_DIR / f"{stem}{suffix}", dpi=180, bbox_inches="tight")


def add_note(ax, x: float, y: float, lines: Iterable[str], *, color: str = COLORS["note"]) -> None:
    text = "\n".join(lines)
    draw_box(
        ax,
        x,
        y,
        text,
        width=2.65,
        height=1.05 + 0.18 * text.count("\n"),
        facecolor=color,
        fontsize=8,
        linewidth=0.9,
    )


def draw_current_pipeline() -> None:
    """Draw the implemented current RTL in the original proposed-style layout."""
    columns = [
        "C0\nIDLE hold",
        "C1\nRAMP cmd\naccepted",
        "C2\nproducts",
        "C3\nadd/sat",
        "C4\npack word",
        "C5\nfirst word",
        "C6\nnext word",
    ]
    rows = [
        "state",
        "command fields",
        "ramp_pipe_*_r",
        "ramp_product_pipe_r",
        "ramp_sum_sat_pipe_r",
        "ramp_word_pipe_r",
        "m_axis_tdata",
        "ramp_base_index_r",
    ]

    fig, ax = plt.subplots(figsize=(18, 8.8))
    y = setup_axes(
        ax,
        "Current implemented proposed-style pipeline",
        columns,
        rows,
    )
    ax.set_xlim(-1.25, len(columns) + 1.15)

    draw_box(ax, 0, y["state"], "IDLE_ST", facecolor=COLORS["state"])
    draw_box(ax, 1, y["state"], "IDLE_ST\n-> RAMP_ST", facecolor=COLORS["state"])
    draw_box(ax, 2, y["state"], "RAMP_ST", facecolor=COLORS["state"])
    draw_box(ax, 3, y["state"], "RAMP_ST", facecolor=COLORS["state"])
    draw_box(ax, 4, y["state"], "RAMP_ST", facecolor=COLORS["state"])
    draw_box(ax, 5, y["state"], "RAMP_ST", facecolor=COLORS["state"])
    draw_box(ax, 6, y["state"], "RAMP_ST", facecolor=COLORS["state"])

    draw_box(ax, 0, y["command fields"], "no cmd\nhold output", facecolor=COLORS["hold"])
    draw_box(
        ax,
        1,
        y["command fields"],
        "OP_RAMP\n target=cmd[31:0]\n duration=cmd[95:64]\n step=cmd[127:96]\n start=current",
        facecolor=COLORS["wire"],
        fontsize=7,
    )

    draw_box(
        ax,
        1,
        y["ramp_pipe_*_r"],
        "<= current,\ntarget, step,\nduration,\nbase=0",
        facecolor=COLORS["proposed"],
        fontsize=7,
    )
    draw_box(ax, 2, y["ramp_product_pipe_r"], "<= step *\nindex lanes\nbase=0", facecolor=COLORS["proposed"])
    draw_box(ax, 3, y["ramp_sum_sat_pipe_r"], "<= start +\nproduct,\nsaturate", facecolor=COLORS["proposed"])
    draw_box(ax, 4, y["ramp_word_pipe_r"], "<= packed\nN_PTS word", facecolor=COLORS["proposed"])

    draw_box(ax, 0, y["m_axis_tdata"], "hold_word", facecolor=COLORS["out"])
    draw_box(ax, 1, y["m_axis_tdata"], "hold_word\n(no direct\nramp word)", facecolor=COLORS["out"], fontsize=7)
    draw_box(ax, 2, y["m_axis_tdata"], "hold_word\npipeline fill", facecolor=COLORS["out"])
    draw_box(ax, 3, y["m_axis_tdata"], "hold_word", facecolor=COLORS["out"])
    draw_box(ax, 4, y["m_axis_tdata"], "hold_word", facecolor=COLORS["out"])
    draw_box(ax, 5, y["m_axis_tdata"], "<= ramp_word_pipe_r\nbase=0", facecolor=COLORS["out"], fontsize=7)
    draw_box(ax, 6, y["m_axis_tdata"], "<= ramp_word_pipe_r\nbase=N_PTS", facecolor=COLORS["out"], fontsize=7)

    draw_box(ax, 1, y["ramp_base_index_r"], "<= 0", facecolor=COLORS["reg"])
    draw_box(ax, 2, y["ramp_base_index_r"], "<= pipe base\n0", facecolor=COLORS["reg"])
    draw_box(ax, 3, y["ramp_base_index_r"], "<= pipe base\nN_PTS", facecolor=COLORS["reg"])
    draw_box(ax, 4, y["ramp_base_index_r"], "<= pipe base\n2*N_PTS", facecolor=COLORS["reg"])
    draw_box(ax, 5, y["ramp_base_index_r"], "N_PTS", facecolor=COLORS["reg"])
    draw_box(ax, 6, y["ramp_base_index_r"], "2*N_PTS", facecolor=COLORS["reg"])

    draw_arrow(ax, 1, y["command fields"], 1, y["ramp_pipe_*_r"])
    draw_arrow(ax, 1, y["ramp_pipe_*_r"], 2, y["ramp_product_pipe_r"], rad=-0.18)
    draw_arrow(ax, 2, y["ramp_product_pipe_r"], 3, y["ramp_sum_sat_pipe_r"], rad=-0.18)
    draw_arrow(ax, 3, y["ramp_sum_sat_pipe_r"], 4, y["ramp_word_pipe_r"], rad=-0.18)
    draw_arrow(ax, 4, y["ramp_word_pipe_r"], 5, y["m_axis_tdata"], rad=-0.18)

    add_note(
        ax,
        5.8,
        y["command fields"] - 0.15,
        [
            "Current RTL:",
            "- proposed-style path is now implemented",
            "- product/add-saturate/word registers",
            "- no divider",
            "- step comes from cmd[127:96]",
            "- first ramp word after 4-cycle latency",
        ],
        color="#f4fff8",
    )

    save_figure(fig, "awg_tuning_current_pipeline")
    plt.close(fig)


def draw_proposed_pipeline() -> None:
    """Draw the original proposed deeper register-only pipeline concept."""
    columns = [
        "C0\nIDLE hold",
        "C1\nRAMP cmd\naccepted",
        "C2\nproducts",
        "C3\nadd/sat",
        "C4\npack word",
        "C5\nfirst word",
        "C6\nnext word",
    ]
    rows = [
        "state",
        "command fields",
        "ramp_cmd_pipe_r",
        "ramp_product_pipe_r",
        "ramp_sum_sat_pipe_r",
        "ramp_word_pipe_r",
        "m_axis_tdata",
        "ramp_base_index_r",
    ]

    fig, ax = plt.subplots(figsize=(18, 8.8))
    y = setup_axes(
        ax,
        "Proposed register-only deeper lane pipeline, no new FSM states",
        columns,
        rows,
    )
    ax.set_xlim(-1.25, len(columns) + 1.25)

    draw_box(ax, 0, y["state"], "IDLE_ST", facecolor=COLORS["state"])
    draw_box(ax, 1, y["state"], "IDLE_ST\n-> RAMP_ST", facecolor=COLORS["state"])
    for x in range(2, 7):
        draw_box(ax, x, y["state"], "RAMP_ST", facecolor=COLORS["state"])

    draw_box(ax, 1, y["command fields"], "target,\nduration,\nstep,\nstart=current", facecolor=COLORS["wire"])
    draw_box(ax, 1, y["ramp_cmd_pipe_r"], "<= command\nbase=0", facecolor=COLORS["proposed"])
    draw_box(ax, 2, y["ramp_product_pipe_r"], "<= step *\nindex lanes", facecolor=COLORS["proposed"])
    draw_box(ax, 3, y["ramp_sum_sat_pipe_r"], "<= start +\nproduct,\nsaturate", facecolor=COLORS["proposed"])
    draw_box(ax, 4, y["ramp_word_pipe_r"], "<= packed\nN_PTS word", facecolor=COLORS["proposed"])
    draw_box(ax, 5, y["m_axis_tdata"], "<= ramp_word\nbase=0", facecolor=COLORS["out"])
    draw_box(ax, 6, y["m_axis_tdata"], "<= ramp_word\nbase=N_PTS", facecolor=COLORS["out"])

    draw_box(ax, 0, y["m_axis_tdata"], "hold_word", facecolor=COLORS["out"])
    draw_box(ax, 1, y["m_axis_tdata"], "hold_word", facecolor=COLORS["out"])
    draw_box(ax, 2, y["m_axis_tdata"], "hold_word", facecolor=COLORS["out"])
    draw_box(ax, 3, y["m_axis_tdata"], "hold_word", facecolor=COLORS["out"])
    draw_box(ax, 4, y["m_axis_tdata"], "hold_word", facecolor=COLORS["out"])

    draw_box(ax, 1, y["ramp_base_index_r"], "0", facecolor=COLORS["reg"])
    draw_box(ax, 2, y["ramp_base_index_r"], "0", facecolor=COLORS["reg"])
    draw_box(ax, 3, y["ramp_base_index_r"], "0", facecolor=COLORS["reg"])
    draw_box(ax, 4, y["ramp_base_index_r"], "0 -> N_PTS", facecolor=COLORS["reg"])
    draw_box(ax, 5, y["ramp_base_index_r"], "N_PTS", facecolor=COLORS["reg"])
    draw_box(ax, 6, y["ramp_base_index_r"], "2*N_PTS", facecolor=COLORS["reg"])

    draw_arrow(ax, 1, y["command fields"], 1, y["ramp_cmd_pipe_r"])
    draw_arrow(ax, 1, y["ramp_cmd_pipe_r"], 2, y["ramp_product_pipe_r"], rad=-0.18)
    draw_arrow(ax, 2, y["ramp_product_pipe_r"], 3, y["ramp_sum_sat_pipe_r"], rad=-0.18)
    draw_arrow(ax, 3, y["ramp_sum_sat_pipe_r"], 4, y["ramp_word_pipe_r"], rad=-0.18)
    draw_arrow(ax, 4, y["ramp_word_pipe_r"], 5, y["m_axis_tdata"], rad=-0.18)

    add_note(
        ax,
        7.25,
        y["command fields"] - 0.15,
        [
            "Concept only:",
            "- keeps IDLE_ST/RAMP_ST",
            "- adds only valid/register stages",
            "- no divider",
            "- longer startup latency",
            "- not claimed implemented here",
        ],
        color="#f4fff8",
    )

    save_figure(fig, "awg_tuning_proposed_pipeline")
    plt.close(fig)


def main() -> None:
    draw_current_pipeline()
    draw_proposed_pipeline()
    for name in (
        "awg_tuning_current_pipeline.png",
        "awg_tuning_current_pipeline.svg",
        "awg_tuning_proposed_pipeline.png",
        "awg_tuning_proposed_pipeline.svg",
    ):
        path = DOC_DIR / name
        print(f"wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
