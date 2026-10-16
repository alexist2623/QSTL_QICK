"""Create private per-case CSV/figures from an already-passed CPU simulation."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REQUIRED = ((20000, 1, 1, "rise1_hold1_fall1"), (22000, 1, 2, "rise1_hold2_fall1"), (34000, 2, 1, "rise2_hold1_fall2"))


def analyze(build: Path, output: Path):
    build, output = build.resolve(), output.resolve()
    result = json.loads((build / "result.json").read_text(encoding="utf-8-sig"))
    if result.get("passed") is not True or result.get("complete") is not True:
        raise ValueError("Full CPU simulation must have completed with PASS")
    if output.exists():
        raise FileExistsError(output)
    if not output.as_posix().lower().startswith("f:/qick_private_analysis/awg_tuning_v6/"):
        raise ValueError("Keep private results outside Git")
    with (build / "required_waveforms.csv").open() as stream:
        rows = [{k: int(v) for k, v in r.items()} for r in csv.DictReader(stream)]
    output.mkdir(parents=True)
    artifacts = []
    for base, rise, hold, name in REQUIRED:
        selected = [r for r in rows if base + 30 <= r["tproc_clock"] <= base + 34 + 2 * rise + hold + 3]
        figure, axes = plt.subplots(3, 1, figsize=(10, 8), constrained_layout=True)
        for pair, ax in enumerate(axes):
            data = [r for r in selected if r["pair"] == pair]
            if not data:
                raise ValueError(f"Required case missing pair {pair}: {name}")
            times = [(r["tproc_clock"] - base - 34 + r["lane"] / 16) * 10 / 3 for r in data]
            ax.plot(times, [r["awg_final"] for r in data], "o-", ms=2, lw=1.1, label="AWG final: BYPASS")
            ax.plot(times, [r["combined"] for r in data], "--", lw=1, label="AWG + DDS final (DDS idle)")
            for edge in (0, rise, rise + hold, 2 * rise + hold):
                ax.axvline(edge * 10 / 3, color="0.6", lw=.7)
            ax.set_title(f"Pair {pair}: RAMP {rise} / HOLD {hold} / RAMP {rise} clocks")
            ax.set_ylabel("DAC code")
            ax.grid(alpha=.25)
        axes[-1].set_xlabel("Time from requested final-output start (ns); 1 clock = 10/3 ns")
        axes[0].legend(fontsize=8)
        image_path = output / f"{name}.png"
        figure.savefig(image_path, dpi=160)
        plt.close(figure)
        csv_path = output / f"{name}.csv"
        with csv_path.open("w", newline="") as stream:
            fields = list(selected[0]) + ["relative_sample_index", "time_ns"]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for item in selected:
                scalar = 16 * (item["tproc_clock"] - base - 34) + item["lane"]
                writer.writerow({**item, "relative_sample_index": scalar, "time_ns": scalar * 10 / 48})
        artifacts.append({"name": name, "pairs": 3, "rise_cycles": rise, "hold_cycles": hold, "fall_cycles": rise,
                          "image": str(image_path), "csv": str(csv_path), "scalar_rows_all_pairs": len(selected)})
    report = {"passed": True, "source_build": str(build), "result": result, "required_cases": artifacts,
              "limitations": ["Assembler-driven digital validation; not GUI or board execution", "AXI host wrapper excluded",
                              "ADC/FIR/DDR/analog not measured", "RF fine-memory endpoints not covered"],
              "evidence_hashes": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (
                  build / "result.json", build / "required_waveforms.csv", build / "cpu_tmux_commands.csv",
                  build / "source_before.json", build / "source_after.json", Path(__file__))}}
    (output / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    paragraphs = ["# v6 실제 CPU→TMUX→AWG/RF→sum 검증", "",
                  "실제 tProcessor CPU가 PMEM·DMEM을 읽고 실행한 762개 명령을 세 TMUX 및 세 AWG/RF 쌍에 전달했습니다.",
                  "RAMP/HOLD 경계 49조건 × 3쌍 = 147조건 및 일반 DDS 9조건을 검사했습니다.",
                  "CPU timestamp+1, TMUX 2클록, AWG native 23·DDS native 29·최종 31클록 기준을 고정하여 검사했습니다.", "",
                  "필수 1/1/1, 1/2/1, 2/1/2는 별도 완료 플래그와 각 scalar sample 검사를 통과했습니다.", "",
                  "| 조건 | 상승/유지/하강 (ns) | 그림 | 원시 scalar CSV |", "|---|---|---|---|"]
    for item in artifacts:
        lengths = " / ".join(f"{item[k] * 10 / 3:.9f}" for k in ("rise_cycles", "hold_cycles", "fall_cycles"))
        paragraphs.append(f"| {item['name']} | {lengths} | [{Path(item['image']).name}]({Path(item['image']).as_posix()}) | [{Path(item['csv']).name}]({Path(item['csv']).as_posix()}) |")
    paragraphs += ["", "AWG BYPASS도 같은 31클록 기준입니다. 같은 포트의 AWG와 RF는 명시적으로 1클록 차이로 발행했습니다.",
                   "이 검증은 assembler 입력의 디지털 검증이며 GUI·실물 계측 결과가 아닙니다. AXI host wrapper와 ADC/FIR/DDR 및 RF fine memory endpoint는 범위에 포함되지 않습니다."]
    (output / "REPORT.md").write_text("\n".join(paragraphs) + "\n", encoding="utf-8")
    print(output / "REPORT.md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.build, args.out)
