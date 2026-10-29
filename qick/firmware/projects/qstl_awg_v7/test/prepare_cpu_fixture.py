"""Prepare a full-CPU digital fixture; never opens hardware or changes drivers."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "qick/qick_lib"))
from qick.asm_v1 import QickProgram

BOUNDARIES = (1, 2, 3, 4, 7, 8, 10)
REQUIRED = {(1, 1): "rise1_hold1_fall1", (1, 2): "rise1_hold2_fall1", (2, 1): "rise2_hold1_fall2"}


def awg_set(value: int) -> int:
    return (1 << 152) | (1 << 144) | (value & 0xFFFFFFFF)


def awg_ramp(start: int, target: int, words: int) -> int:
    samples = 16 * words
    # Choose the signed fixed-point slope before seeing any RTL output.
    step = ((target - start) << 18) // (samples - 1)
    assert -(1 << 31) <= step < (1 << 31)
    return (1 << 152) | (2 << 144) | ((step & 0xFFFFFFFF) << 96) | (samples << 64) | (target & 0xFFFFFFFF)


def rf_dds(gain: int, words: int) -> int:
    # TMUX 0; DDS-only, phase reset, frequency=phase=0, zero after pulse.
    return (1 << 148) | (1 << 147) | (1 << 144) | (words << 128) | ((gain & 0xFFFF) << 96)


def prepare(destination: Path) -> dict:
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(f"A fresh fixture directory is required: {destination}")
    if not str(destination).replace("\\", "/").lower().startswith("f:/qick_private_analysis/awg_tuning_v7/"):
        raise ValueError("Fixture results belong under F:/QICK_Private_Analysis/awg_tuning_v7")
    events, cases = [], []

    def add(t, pair, word, label):
        events.append({"timestamp": t, "port": pair, "word_hex": f"{word:040x}", "label": label})

    # Separate same-port SET/RF commands by exactly one clock. Never pretend
    # that two words on one port arrived simultaneously.
    for trial, width in enumerate((8, 16, 31)):
        base = 10000 + trial * 2000
        for pair, target in enumerate((4096, 8192, -4096)):
            add(base, pair, awg_set(target), f"rf{trial}_awg_on")
            add(base + 1, pair, rf_dds(4096 * (pair + 1), width), f"rf{trial}_rf_on_offset1")
            add(base + width, pair, awg_set(0), f"rf{trial}_awg_off")

    for rise in BOUNDARIES:
        for hold in BOUNDARIES:
            case_id = len(cases)
            base = 20000 + case_id * 2000
            name = REQUIRED.get((rise, hold), f"rise{rise}_hold{hold}_fall{rise}")
            cases.append({"index": case_id, "name": name, "required": (rise, hold) in REQUIRED,
                          "rise_cycles": rise, "hold_cycles": hold, "fall_cycles": rise,
                          "rise_samples": rise * 16, "fall_samples": rise * 16,
                          "timestamp": base, "pairs": [0, 1, 2]})
            for pair, target in enumerate((4096, 8192, -4096)):
                for t, word, phase in (
                    (base - 10, awg_set(0), "reset"),
                    (base, awg_ramp(0, target, rise), "rise"),
                    (base + rise, awg_set(target), "hold"),
                    (base + rise + hold, awg_ramp(target, 0, rise), "fall"),
                    (base + 2 * rise + hold, awg_set(0), "zero"),
                ):
                    add(t, pair, word, f"{name}_{phase}")
    events.sort(key=lambda e: (e["timestamp"], e["port"]))
    assert len({(e["timestamp"], e["port"]) for e in events}) == len(events)
    cfg = {"gens": [], "readouts": [], "tprocs": [{"type": "axis_tproc64x32_x8", "f_time": 300.0,
            "pmem_size": 8192, "dmem_size": 4096}], "refclk_freq": 100.0}
    program = QickProgram(cfg)
    dmem = []
    program.regwi(0, 7, 0x1234567)
    program.memwi(0, 7, 4094)
    for event in events:
        word = int(event["word_hex"], 16)
        for lane in range(5):
            dmem.append((word >> (32 * lane)) & 0xFFFFFFFF)
            program.memri(0, lane + 1, len(dmem) - 1)
        program.regwi(0, 6, event["timestamp"])
        program.set(event["port"], 0, 1, 2, 3, 4, 5, 6)
    stop_time = max(e["timestamp"] for e in events) + 300
    program.waiti(0, stop_time)
    program.regwi(0, 7, 0x7654321)
    program.memwi(0, 7, 4095)
    program.end()
    program.compile()
    pmem = program.binprog
    assert len(pmem) <= 8192 and len(dmem) < 4094
    destination.mkdir(parents=True)
    (destination / "pmem.hex").write_text("".join(f"{word:016x}\n" for word in pmem), encoding="ascii")
    (destination / "dmem.hex").write_text("".join(f"{word:08x}\n" for word in dmem), encoding="ascii")
    (destination / "expected_events.hex").write_text("".join(
        f"{(e['timestamp'] << 168) | (e['port'] << 160) | int(e['word_hex'], 16):050x}\n" for e in events), encoding="ascii")
    (destination / "fixture_meta.hex").write_text("".join(f"{x:08x}\n" for x in (len(events), stop_time, len(pmem), len(dmem), len(cases))), encoding="ascii")
    (destination / "program.asm").write_text(program.asm(), encoding="utf-8")
    result = {"schema": 1, "scope": "real tproc64x32_x8 CPU core with synchronous PMEM/DMEM; AXI host wrapper excluded",
              "clock_MHz": 300, "samples_per_clock": 16, "cases": cases, "events": events,
              "awg_native_latency_cycles": 27, "dds_native_latency_cycles": 29,
              "sum_awg_delay_cycles": 2, "sum_pipeline_cycles": 2, "final_native_latency_cycles": 31,
              "cpu_timestamp_to_downstream_sample_cycles": 1, "tmux_transport_cycles": 2,
              "ordinary_rf_width_cycles": [8, 16, 31], "rf_same_port_offset_cycles": 1,
              "pmem_words": len(pmem), "dmem_words": len(dmem), "stop_timestamp": stop_time,
              "fine_rf_memory_endpoints": "not covered by this CPU fixture",
              "sources": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (
                  Path(__file__), REPO / "qick/qick_lib/qick/asm_v1.py", REPO / "qick/qick_lib/qick/qick_asm.py")}}
    (destination / "fixture.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return {"fixture": str(destination), "cases": len(cases), "pair_cases": 3 * len(cases),
            "events": len(events), "pmem_words": len(pmem), "dmem_words": len(dmem), "required": list(REQUIRED.values())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    print(json.dumps(prepare(parser.parse_args().out), indent=2))
